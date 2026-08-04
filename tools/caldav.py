"""
tools/caldav.py — CalDAV calendar read/write.

Uses raw requests + XML; does not require the caldav library.
Config loaded from config/modules/caldav.yaml.

Security note: all external calendar data is untrusted — the title, description and
location of an invite are written by whoever sent it. `read_calendar` wraps its event
payload in <untrusted_content> tags at the return boundary (tools/untrusted.py).
Implemented 2026-08-04; this docstring described it as a to-do from 2026-08-03, during
which the calendar was live in production unwrapped.
"""

import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import yaml

from core.persona import persona_config_dir
from tools.untrusted import (UNTRUSTED_CONTENT_INSTRUCTION, contains_injection_markers,
                             wrap_untrusted)

_ROOT = Path(__file__).parent.parent


def _config_path(persona: str | None = None) -> Path:
    """Per-persona. Each persona has its own calendar and its own credentials."""
    return persona_config_dir(persona) / "caldav.yaml"


def _load_config(persona: str | None = None) -> dict:
    path = _config_path(persona)
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def _parse_ical_dt(val: str) -> str:
    """Parse iCalendar datetime string to ISO 8601. Returns val unchanged on failure."""
    if not val:
        return ""
    utc = val.endswith("Z")
    clean = val.rstrip("Z")
    for fmt in ("%Y%m%dT%H%M%S", "%Y%m%d"):
        try:
            dt = datetime.strptime(clean, fmt)
            if utc:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except ValueError:
            continue
    return val


def _parse_ical_events(ical_text: str) -> list[dict]:
    """Extract VEVENT blocks from iCalendar text and return as list of raw dicts."""
    lines = ical_text.replace("\r\n", "\n").replace("\r", "\n").splitlines()

    # Unfold continuation lines (RFC 5545: lines starting with space/tab continue previous)
    unfolded: list[str] = []
    for line in lines:
        if line and line[0] in (" ", "\t") and unfolded:
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)

    events = []
    in_event = False
    current: dict[str, str] = {}

    for line in unfolded:
        if line == "BEGIN:VEVENT":
            in_event = True
            current = {}
        elif line == "END:VEVENT":
            if in_event:
                events.append(current)
            in_event = False
            current = {}
        elif in_event and ":" in line:
            key, _, value = line.partition(":")
            base_key = key.split(";")[0].strip()  # strip TZID= and other params
            current[base_key] = value.strip()

    return events


def _format_event(raw: dict) -> dict:
    """Normalize a raw VEVENT dict to a clean structured form."""
    return {
        "uid": raw.get("UID", ""),
        "title": raw.get("SUMMARY", ""),
        "start": _parse_ical_dt(raw.get("DTSTART", "")),
        "end": _parse_ical_dt(raw.get("DTEND", "")),
        "description": raw.get("DESCRIPTION", "").replace("\\n", "\n").replace("\\,", ",").replace("\\;", ";"),
        "location": raw.get("LOCATION", ""),
        "status": raw.get("STATUS", ""),
    }


def read_calendar(start_date: str, end_date: str) -> dict:
    """
    Read calendar events between start_date and end_date (inclusive).

    Args:
        start_date: Start date in YYYY-MM-DD format.
        end_date:   End date in YYYY-MM-DD format.

    Returns:
        Dict with "events" list and "count". Each event has: uid, title,
        start, end, description, location, status.
    """
    cfg = _load_config()
    if not cfg.get("enabled"):
        return {
            "error": (
                "CalDAV is not enabled. Set enabled: true and configure "
                "calendar_url and auth in this persona's caldav.yaml."
            )
        }

    calendar_url = cfg.get("calendar_url", "").strip()
    if not calendar_url:
        return {"error": "calendar_url not set in this persona's caldav.yaml."}

    try:
        start_dt = datetime.fromisoformat(start_date + "T00:00:00").strftime("%Y%m%dT%H%M%SZ")
        end_dt = datetime.fromisoformat(end_date + "T23:59:59").strftime("%Y%m%dT%H%M%SZ")
    except ValueError as e:
        return {"error": f"Invalid date format (expected YYYY-MM-DD): {e}"}

    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<c:calendar-query xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">'
        "<d:prop><d:getetag/><c:calendar-data/></d:prop>"
        "<c:filter>"
        '<c:comp-filter name="VCALENDAR">'
        '<c:comp-filter name="VEVENT">'
        f'<c:time-range start="{start_dt}" end="{end_dt}"/>'
        "</c:comp-filter>"
        "</c:comp-filter>"
        "</c:filter>"
        "</c:calendar-query>"
    )

    auth_cfg = cfg.get("auth", {})
    auth = (auth_cfg.get("username", ""), auth_cfg.get("password", ""))

    try:
        response = requests.request(
            "REPORT",
            calendar_url,
            data=body.encode("utf-8"),
            headers={
                "Content-Type": "application/xml; charset=utf-8",
                "Depth": "1",
            },
            auth=auth,
            timeout=15,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        return {"error": f"CalDAV request failed: {e}"}

    try:
        root = ET.fromstring(response.text)
    except ET.ParseError as e:
        return {"error": f"Failed to parse CalDAV response: {e}"}

    events = []
    for response_el in root.findall(".//{DAV:}response"):
        cal_data_el = response_el.find(
            ".//{urn:ietf:params:xml:ns:caldav}calendar-data"
        )
        if cal_data_el is not None and cal_data_el.text:
            for raw in _parse_ical_events(cal_data_el.text):
                events.append(_format_event(raw))

    events.sort(key=lambda e: e.get("start", ""))

    # Calendar text is written by whoever sent the invite, not by the user. `title`,
    # `description` and `location` are free-text fields an attacker controls outright,
    # so the payload crosses the boundary here — at the tool return, which is the only
    # place that knows the content is external.
    #
    # Wrapped once around the whole list rather than field by field: one boundary is
    # harder to get wrong than 3N of them, and the JSON structure survives inside it, so
    # agents still read titles and times exactly as before.
    import json as _json

    host = ""
    try:
        host = requests.utils.urlparse(url).netloc
    except Exception:
        pass

    rendered = _json.dumps(events, indent=2, ensure_ascii=False)
    markers = contains_injection_markers(rendered)
    result = {
        "count": len(events),
        "range": {"start": start_date, "end": end_date},
        "security_note": UNTRUSTED_CONTENT_INSTRUCTION,
        "events": wrap_untrusted(rendered, source=f"calendar {host}".strip()),
    }
    if markers:
        # Recorded, never blocked: a legitimate invite may well say "disregard my last
        # message". The value is that an attempt leaves a trace instead of passing
        # silently.
        result["injection_markers_detected"] = markers
    return result


def write_calendar_event(
    title: str,
    start: str,
    end: str,
    description: str = "",
    recurrence: str = "",
    alarm_minutes_before: int | None = None,
    all_day: bool = False,
) -> dict:
    """
    Create a new calendar event on the CalDAV server.

    Supports the three kinds of time-bound thing the system distinguishes:

      Appointment — a fixed time you want to be interrupted for.
                    all_day=False, alarm_minutes_before set.
      Deadline    — a day something must happen by, with no particular time.
                    all_day=True, no alarm; the day is surfaced in conversation
                    rather than by an interrupting alert.
      Recurring   — either of the above, repeated, via `recurrence`.

    Args:
        title:        Event title/summary.
        start:        Start datetime YYYY-MM-DDTHH:MM:SS, or YYYY-MM-DD if all_day.
        end:          End datetime YYYY-MM-DDTHH:MM:SS, or YYYY-MM-DD if all_day.
        description:  Optional event description/notes.
        recurrence:   Optional RFC 5545 RRULE body, without the "RRULE:" prefix.
                      e.g. "FREQ=MONTHLY;BYMONTHDAY=15" or "FREQ=WEEKLY;BYDAY=MO".
        alarm_minutes_before: Optional alert, N minutes before start. Omit for
                      deadlines — an all-day event that alarms fires at midnight,
                      which is worse than useless.
        all_day:      True for a date-only event with no clock time.

    Returns:
        Dict with success status and event uid, or error.
    """
    cfg = _load_config()
    if not cfg.get("enabled"):
        return {
            "error": (
                "CalDAV is not enabled. Set enabled: true and configure "
                "calendar_url and auth in this persona's caldav.yaml."
            )
        }

    url = str(cfg.get("calendar_url", "")).strip()
    if not url:
        return {
            "error": (
                "No calendar_url configured. Set it "
                "in config/modules/caldav.yaml."
            )
        }

    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    except ValueError as e:
        expected = "YYYY-MM-DD" if all_day else "YYYY-MM-DDTHH:MM:SS"
        return {"error": f"Invalid datetime (expected {expected}): {e}"}

    if end_dt <= start_dt:
        # An all-day event's DTEND is exclusive per RFC 5545, so a single-day
        # event is start=D, end=D+1. Callers naturally pass the same date twice;
        # accept that and advance the end rather than rejecting it.
        if all_day and end_dt == start_dt:
            end_dt = end_dt + timedelta(days=1)
        else:
            return {"error": "end must be after start."}

    if alarm_minutes_before is not None:
        try:
            alarm_minutes_before = int(alarm_minutes_before)
        except (TypeError, ValueError):
            return {"error": "alarm_minutes_before must be a whole number of minutes."}
        if alarm_minutes_before < 0:
            return {"error": "alarm_minutes_before must be zero or positive."}

    recurrence = (recurrence or "").strip().upper()
    if recurrence.startswith("RRULE:"):
        recurrence = recurrence[len("RRULE:"):]
    if recurrence and not recurrence.startswith("FREQ="):
        return {
            "error": (
                f"recurrence must be an RRULE body starting with FREQ=, got "
                f"'{recurrence}'. Examples: 'FREQ=MONTHLY;BYMONTHDAY=15', "
                f"'FREQ=WEEKLY;BYDAY=MO', 'FREQ=YEARLY'."
            )
        }

    tz = cfg.get("timezone", "UTC")
    dt_fmt = "%Y%m%dT%H%M%S"
    event_uid = str(uuid.uuid4()) + "@ai-life-manager"
    now_utc = datetime.now(timezone.utc).strftime(dt_fmt) + "Z"

    # Escape per RFC 5545 §3.3.11
    def _esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

    # All-day events use DATE values with no timezone; timed events use local
    # times bound to TZID. Mixing the two produces events that display an hour
    # out, or not at all, depending on the client.
    if all_day:
        dtstart = f"DTSTART;VALUE=DATE:{start_dt.strftime('%Y%m%d')}"
        dtend = f"DTEND;VALUE=DATE:{end_dt.strftime('%Y%m%d')}"
    else:
        dtstart = f"DTSTART;TZID={tz}:{start_dt.strftime(dt_fmt)}"
        dtend = f"DTEND;TZID={tz}:{end_dt.strftime(dt_fmt)}"

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AI Life Manager//NONSGML//EN",
        "BEGIN:VEVENT",
        f"UID:{event_uid}",
        f"DTSTAMP:{now_utc}",
        dtstart,
        dtend,
        f"SUMMARY:{_esc(title)}",
        f"DESCRIPTION:{_esc(description)}",
    ]

    # RRULE is structured property data, not text — escaping it would turn the
    # semicolons separating its parts into literal characters and break the rule.
    if recurrence:
        lines.append(f"RRULE:{recurrence}")

    if alarm_minutes_before is not None:
        lines += [
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{_esc(title)}",
            f"TRIGGER:-PT{alarm_minutes_before}M",
            "END:VALARM",
        ]

    lines += ["END:VEVENT", "END:VCALENDAR", ""]
    ical = "\r\n".join(lines)

    event_url = url.rstrip("/") + "/" + event_uid + ".ics"

    auth_cfg = cfg.get("auth", {})
    auth = (auth_cfg.get("username", ""), auth_cfg.get("password", ""))

    try:
        response = requests.put(
            event_url,
            data=ical.encode("utf-8"),
            headers={"Content-Type": "text/calendar; charset=utf-8"},
            auth=auth,
            timeout=15,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        return {"error": f"Failed to write calendar event: {e}"}

    return {
        "success": True,
        "uid": event_uid,
        "title": title,
        "start": start,
        "end": end,
        "url": event_url,
    }


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

READ_CALENDAR_SCHEMA = {
    "name": "read_calendar",
    "description": (
        "Read calendar events between two dates from the user's CalDAV calendar. "
        "Returns a list of events with title, start, end, description, and location. "
        "Requires CalDAV to be configured and enabled in config/modules/caldav.yaml."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "start_date": {
                "type": "string",
                "description": "Start date in YYYY-MM-DD format (inclusive).",
            },
            "end_date": {
                "type": "string",
                "description": "End date in YYYY-MM-DD format (inclusive).",
            },
        },
        "required": ["start_date", "end_date"],
    },
}

WRITE_CALENDAR_EVENT_SCHEMA = {
    "name": "write_calendar_event",
    "description": (
        "Create an event on the user's calendar. Handles one-off and repeating "
        "events, with or without an alert.\n\n"
        "Choose the shape from what the thing actually is:\n"
        "- APPOINTMENT — happens at a set time and should interrupt the user. "
        "Give a start and end time, and set alarm_minutes_before.\n"
        "- DEADLINE — must happen on a given day but has no particular time "
        "(paying a bill, renewing a licence). Set all_day=true and give dates "
        "only. Do NOT set an alarm: an all-day alert fires at midnight, which "
        "helps nobody. The day gets raised in conversation instead.\n"
        "- REPEATING — either of the above with `recurrence` set.\n\n"
        "Worked example — 'strong reminder to pay the credit card on the 15th "
        "of every month': title='Pay credit card bills', start='2026-08-15', "
        "end='2026-08-15', all_day=true, recurrence='FREQ=MONTHLY;BYMONTHDAY=15'."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Event title / summary.",
            },
            "start": {
                "type": "string",
                "description": (
                    "Start. Timed events: YYYY-MM-DDTHH:MM:SS (e.g. 2026-08-10T09:00:00). "
                    "All-day events: YYYY-MM-DD (e.g. 2026-08-15)."
                ),
            },
            "end": {
                "type": "string",
                "description": (
                    "End, same format as start. For a single all-day event pass the "
                    "same date as start."
                ),
            },
            "description": {
                "type": "string",
                "description": "Optional event notes or description.",
            },
            "all_day": {
                "type": "boolean",
                "description": (
                    "True for a date-only event with no clock time. Use for deadlines."
                ),
            },
            "recurrence": {
                "type": "string",
                "description": (
                    "Optional repeat rule, as an RRULE body WITHOUT the 'RRULE:' prefix. "
                    "Common forms: 'FREQ=DAILY'; 'FREQ=WEEKLY;BYDAY=MO' (every Monday); "
                    "'FREQ=MONTHLY;BYMONTHDAY=15' (15th of each month); "
                    "'FREQ=MONTHLY;BYDAY=-1FR' (last Friday); 'FREQ=YEARLY'. "
                    "Add ';COUNT=12' to stop after 12 occurrences, or ';UNTIL=20271231T000000Z' "
                    "to stop on a date. Omit for a one-off event."
                ),
            },
            "alarm_minutes_before": {
                "type": "integer",
                "description": (
                    "Optional alert, this many minutes before the start time "
                    "(e.g. 30 for half an hour before, 1440 for a day before). "
                    "Omit entirely for all-day deadlines."
                ),
            },
        },
        "required": ["title", "start", "end"],
    },
}
