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
    attendee_field = raw.get("X-ATTENDEE-NAMES", "")
    return {
        "uid": raw.get("UID", ""),
        "title": raw.get("SUMMARY", ""),
        "start": _parse_ical_dt(raw.get("DTSTART", "")),
        "end": _parse_ical_dt(raw.get("DTEND", "")),
        "description": raw.get("DESCRIPTION", "").replace("\\n", "\n").replace("\\,", ",").replace("\\;", ";"),
        "location": raw.get("LOCATION", ""),
        "status": raw.get("STATUS", ""),
        "recurrence": raw.get("RRULE", ""),
        "attendees": [a.strip() for a in attendee_field.split(",") if a.strip()],
        "conflict_check_status": raw.get("X-CONFLICT-CHECK-STATUS", ""),
    }


def _query_events(start_date: str, end_date: str, persona: str | None = None) -> dict:
    """
    Raw CalDAV REPORT query, returning unwrapped structured events.

    Shared by read_calendar (which wraps the result for LLM consumption) and
    tools/scheduling.py (which needs to run interval math and string comparison
    directly against the data — comparing untrusted text in Python is not the
    same thing as handing it to an LLM as instructions, so no wrapping boundary
    applies here). Keeping the REPORT-request/parse logic in one place means
    scheduling.py never re-implements CalDAV querying independently.

    Returns {"events": [...]} on success, {"error": "..."} on failure.
    """
    cfg = _load_config(persona)
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
    return {"events": events, "calendar_url": calendar_url}


def _get_event_by_uid(uid: str, persona: str | None = None) -> dict:
    """Fetch a single event by UID via direct GET. Returns {"error": ...} on failure."""
    cfg = _load_config(persona)
    if not cfg.get("enabled"):
        return {"error": "CalDAV is not enabled."}
    calendar_url = str(cfg.get("calendar_url", "")).strip()
    if not calendar_url:
        return {"error": "calendar_url not set."}

    event_url = calendar_url.rstrip("/") + "/" + uid + ".ics"
    auth_cfg = cfg.get("auth", {})
    auth = (auth_cfg.get("username", ""), auth_cfg.get("password", ""))

    try:
        response = requests.get(event_url, auth=auth, timeout=15)
        if response.status_code == 404:
            return {"error": f"No event found with uid '{uid}'."}
        response.raise_for_status()
    except requests.RequestException as e:
        return {"error": f"Failed to fetch event: {e}"}

    raw_events = _parse_ical_events(response.text)
    if not raw_events:
        return {"error": f"Event '{uid}' returned no parseable VEVENT."}

    event = _format_event(raw_events[0])
    event["_event_url"] = event_url
    return event


def read_calendar(start_date: str, end_date: str) -> dict:
    """
    Read calendar events between start_date and end_date (inclusive).

    Args:
        start_date: Start date in YYYY-MM-DD format.
        end_date:   End date in YYYY-MM-DD format.

    Returns:
        Dict with "events" list and "count". Each event has: uid, title,
        start, end, description, location, status, recurrence, attendees.
    """
    raw = _query_events(start_date, end_date)
    if "error" in raw:
        return raw

    events = raw["events"]

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
        host = requests.utils.urlparse(raw.get("calendar_url", "")).netloc
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
    attendees: list[str] | None = None,
    override_duplicate: bool = False,
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
        attendees:    Optional list of attendee names, cross-referenced against
                      CRM contacts for conflict/duplicate matching.
        override_duplicate: Set True to create the event anyway when an
                      identical event (same title, same exact time) already
                      exists. Default refuses — see the duplicate_event error.

    A conflict check runs automatically before every write — this is not
    optional and not something you need to call separately first. An exact
    duplicate is refused outright (pass override_duplicate=True for a genuine
    repeat). Anything softer — a near-duplicate, a mismatch against an existing
    recurring series, a tight back-to-back location transition — does not block
    the write, but comes back in the response under "conflict_check" for you to
    weigh and act on. If the check itself fails (calendar unreachable), the
    event is still written so scheduling isn't blocked by an outage, but its
    title is prefixed "[VERIFY]" and it's flagged for re-checking next time
    the calendar is queried.

    Returns:
        Dict with success status, event uid, and conflict_check evidence if any
        was found — or an error (including duplicate_event).
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

    # Mandatory conflict check — not something the agent has to remember to
    # call. Imported here rather than at module level to avoid a circular
    # import (tools.scheduling imports tools.caldav._query_events).
    from tools.scheduling import _compute_conflicts

    conflict_result = _compute_conflicts(start, end, title=title, attendees=attendees, location="")
    conflict_check_failed = "check_error" in conflict_result

    if not conflict_check_failed and conflict_result.get("exact_duplicate") and not override_duplicate:
        # Unambiguous: same normalized title, same exact time range, already on
        # the calendar. No judgment call needed here — refuse outright rather
        # than surface it as evidence, matching the recommended fail-closed
        # policy for the one case where the facts are not in question. Pass
        # override_duplicate=True for the rare case of a genuine second
        # identical meeting.
        dup = conflict_result["exact_duplicate"]
        return {
            "error": "duplicate_event",
            "message": (
                f"An identical event already exists (uid={dup['uid']}, "
                f"'{dup['title']}' at {dup['start']}). Not created. Pass "
                f"override_duplicate=True to create it anyway."
            ),
            "existing_event": dup,
        }

    tz = cfg.get("timezone", "UTC")
    dt_fmt = "%Y%m%dT%H%M%S"
    event_uid = str(uuid.uuid4()) + "@ai-life-manager"
    now_utc = datetime.now(timezone.utc).strftime(dt_fmt) + "Z"

    # Escape per RFC 5545 §3.3.11
    def _esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

    # Decided policy for a failed conflict check: allow the write through
    # rather than blocking on a CalDAV outage, but mark the event unmissably
    # so it's found and re-verified rather than trusted as checked. The title
    # prefix is what a human scanning the calendar sees; the X-property is
    # what a later check_calendar_conflicts call finds programmatically
    # (surfaced as unverified_events).
    if conflict_check_failed:
        title_to_write = f"[VERIFY] {title}"
        description = (
            description
            + f"\n\n[Automated note: conflict check failed at write time "
              f"({now_utc}) — {conflict_result['check_error']}. Please "
              f"re-verify no overlap or duplicate exists.]"
        ).strip()
    else:
        title_to_write = title

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
        f"SUMMARY:{_esc(title_to_write)}",
        f"DESCRIPTION:{_esc(description)}",
        f"X-CONFLICT-CHECK-STATUS:{'FAILED' if conflict_check_failed else 'OK'}",
    ]

    if attendees:
        lines.append(f"X-ATTENDEE-NAMES:{_esc(', '.join(attendees))}")

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

    result = {
        "success": True,
        "uid": event_uid,
        "title": title_to_write,
        "start": start,
        "end": end,
        "url": event_url,
    }
    if conflict_check_failed:
        result["conflict_check"] = {"status": "failed", "reason": conflict_result["check_error"]}
    else:
        # Only surface conflict evidence that isn't already the refused exact-
        # duplicate case above — near-duplicates, series mismatches, tight
        # transitions. Kept out of the response entirely when there's nothing
        # to report, so a clean write still reads as a clean write.
        evidence = {
            k: v for k, v in conflict_result.items()
            if k not in ("exact_duplicate", "overlaps") and v
        }
        if conflict_result.get("overlaps"):
            evidence["overlaps"] = conflict_result["overlaps"]
        if evidence:
            result["conflict_check"] = {"status": "ok", "evidence": evidence}
    return result


def update_calendar_event(
    uid: str,
    title: str | None = None,
    start: str | None = None,
    end: str | None = None,
    description: str | None = None,
    location: str | None = None,
    all_day: bool | None = None,
    recurrence: str | None = None,
    alarm_minutes_before: int | None = None,
    attendees: list[str] | None = None,
) -> dict:
    """
    Modify an existing calendar event. Fetches the current event, applies only
    the fields you pass (omit a field to leave it unchanged), and re-checks for
    conflicts against the new time before writing.

    Use this instead of write_calendar_event whenever the thing already exists
    and you're moving it, retitling it, or correcting a detail — e.g. "the
    meeting moved to 3:30" or resolving a flagged duplicate by updating the
    original instead of creating a second copy.

    Args:
        uid:          UID of the event to update (from a prior read_calendar,
                      write_calendar_event, or check_calendar_conflicts result).
        title, start, end, description, location, all_day, recurrence,
        alarm_minutes_before, attendees: Same meaning as write_calendar_event.
                      Pass only the fields that changed; the rest carry over
                      from the existing event.

    Returns:
        Dict with success status and conflict_check evidence (same shape as
        write_calendar_event), or an error.
    """
    existing = _get_event_by_uid(uid)
    if "error" in existing:
        return existing

    cfg = _load_config()
    url = str(cfg.get("calendar_url", "")).strip()

    new_title = title if title is not None else existing["title"]
    new_start = start if start is not None else existing["start"]
    new_end = end if end is not None else existing["end"]
    new_description = description if description is not None else existing["description"]
    new_location = location if location is not None else existing["location"]
    new_recurrence = recurrence if recurrence is not None else existing.get("recurrence", "")
    new_attendees = attendees if attendees is not None else existing.get("attendees", [])
    new_all_day = all_day if all_day is not None else ("T" not in existing["start"])

    try:
        start_dt = datetime.fromisoformat(new_start)
        end_dt = datetime.fromisoformat(new_end)
    except ValueError as e:
        expected = "YYYY-MM-DD" if new_all_day else "YYYY-MM-DDTHH:MM:SS"
        return {"error": f"Invalid datetime (expected {expected}): {e}"}
    if end_dt <= start_dt:
        if new_all_day and end_dt == start_dt:
            end_dt = end_dt + timedelta(days=1)
        else:
            return {"error": "end must be after start."}

    from tools.scheduling import _compute_conflicts

    conflict_result = _compute_conflicts(
        new_start, new_end, title=new_title, attendees=new_attendees,
        location=new_location, exclude_uid=uid,
    )
    conflict_check_failed = "check_error" in conflict_result

    if not conflict_check_failed and conflict_result.get("exact_duplicate"):
        dup = conflict_result["exact_duplicate"]
        return {
            "error": "duplicate_event",
            "message": (
                f"Updating to this time/title would exactly duplicate an existing "
                f"event (uid={dup['uid']}, '{dup['title']}' at {dup['start']}). "
                f"Not updated."
            ),
            "existing_event": dup,
        }

    tz = cfg.get("timezone", "UTC")
    dt_fmt = "%Y%m%dT%H%M%S"
    now_utc = datetime.now(timezone.utc).strftime(dt_fmt) + "Z"

    def _esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

    title_to_write = f"[VERIFY] {new_title}" if conflict_check_failed else new_title
    if conflict_check_failed:
        new_description = (
            new_description
            + f"\n\n[Automated note: conflict check failed at update time "
              f"({now_utc}) — {conflict_result['check_error']}. Please "
              f"re-verify no overlap or duplicate exists.]"
        ).strip()

    if new_all_day:
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
        f"UID:{uid}",
        f"DTSTAMP:{now_utc}",
        dtstart,
        dtend,
        f"SUMMARY:{_esc(title_to_write)}",
        f"DESCRIPTION:{_esc(new_description)}",
        f"LOCATION:{_esc(new_location)}",
        f"X-CONFLICT-CHECK-STATUS:{'FAILED' if conflict_check_failed else 'OK'}",
    ]
    if new_attendees:
        lines.append(f"X-ATTENDEE-NAMES:{_esc(', '.join(new_attendees))}")
    if new_recurrence:
        lines.append(f"RRULE:{new_recurrence}")
    if alarm_minutes_before is not None:
        lines += [
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{_esc(title_to_write)}",
            f"TRIGGER:-PT{alarm_minutes_before}M",
            "END:VALARM",
        ]
    lines += ["END:VEVENT", "END:VCALENDAR", ""]
    ical = "\r\n".join(lines)

    event_url = existing.get("_event_url") or (url.rstrip("/") + "/" + uid + ".ics")
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
        return {"error": f"Failed to update calendar event: {e}"}

    result = {"success": True, "uid": uid, "title": title_to_write, "start": new_start, "end": new_end}
    if conflict_check_failed:
        result["conflict_check"] = {"status": "failed", "reason": conflict_result["check_error"]}
    else:
        evidence = {k: v for k, v in conflict_result.items() if k not in ("exact_duplicate", "overlaps") and v}
        if conflict_result.get("overlaps"):
            evidence["overlaps"] = conflict_result["overlaps"]
        if evidence:
            result["conflict_check"] = {"status": "ok", "evidence": evidence}
    return result


def delete_calendar_event(uid: str) -> dict:
    """
    Delete a calendar event by UID.

    Args:
        uid: UID of the event to delete.

    Returns:
        Dict with success status, or an error (including "not found").
    """
    existing = _get_event_by_uid(uid)
    if "error" in existing:
        return existing

    cfg = _load_config()
    auth_cfg = cfg.get("auth", {})
    auth = (auth_cfg.get("username", ""), auth_cfg.get("password", ""))
    event_url = existing["_event_url"]

    try:
        response = requests.delete(event_url, auth=auth, timeout=15)
        if response.status_code == 404:
            return {"error": f"No event found with uid '{uid}'."}
        response.raise_for_status()
    except requests.RequestException as e:
        return {"error": f"Failed to delete calendar event: {e}"}

    return {"success": True, "uid": uid}


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
        "end='2026-08-15', all_day=true, recurrence='FREQ=MONTHLY;BYMONTHDAY=15'.\n\n"
        "A conflict check runs automatically before every write. An exact "
        "duplicate (same title, same exact time) is refused — pass "
        "override_duplicate=true only for a genuine second identical meeting. "
        "Anything softer (near-duplicate, recurring-series mismatch, tight "
        "location transition) does not block the write but comes back under "
        "conflict_check in the response for you to weigh."
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
            "attendees": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Optional attendee names, e.g. ['Jonas']. Cross-referenced "
                    "against CRM contacts and used in duplicate/conflict matching — "
                    "include this whenever the event is a meeting with a specific "
                    "person, it materially improves duplicate detection."
                ),
            },
            "override_duplicate": {
                "type": "boolean",
                "description": (
                    "Set true to create the event even though an identical one "
                    "(same title, same exact time) already exists. Default false "
                    "— use only when you've confirmed this is a genuine second "
                    "identical meeting, not a repeat of the same request."
                ),
            },
        },
        "required": ["title", "start", "end"],
    },
}

UPDATE_CALENDAR_EVENT_SCHEMA = {
    "name": "update_calendar_event",
    "description": (
        "Modify an existing calendar event — move it, retitle it, or correct a "
        "detail. Use this instead of write_calendar_event whenever the thing "
        "already exists: 'the meeting moved to 3:30', fixing a misremembered "
        "detail, or resolving a flagged duplicate by updating the original "
        "instead of creating a second copy. Omit any field you're not changing "
        "— it carries over from the existing event. Re-runs the conflict check "
        "against the new time, excluding the event's own prior booking, with "
        "the same exact-duplicate-refused / softer-conflict-surfaced behavior "
        "as write_calendar_event."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "uid": {
                "type": "string",
                "description": "UID of the event to update (from read_calendar, write_calendar_event, or check_calendar_conflicts).",
            },
            "title": {"type": "string", "description": "New title, if changing."},
            "start": {"type": "string", "description": "New start, same format as write_calendar_event, if changing."},
            "end": {"type": "string", "description": "New end, if changing."},
            "description": {"type": "string", "description": "New description, if changing."},
            "location": {"type": "string", "description": "New location, if changing."},
            "all_day": {"type": "boolean", "description": "New all_day flag, if changing."},
            "recurrence": {"type": "string", "description": "New RRULE body, if changing."},
            "alarm_minutes_before": {"type": "integer", "description": "New alarm offset, if changing."},
            "attendees": {"type": "array", "items": {"type": "string"}, "description": "New attendee list, if changing."},
        },
        "required": ["uid"],
    },
}

DELETE_CALENDAR_EVENT_SCHEMA = {
    "name": "delete_calendar_event",
    "description": (
        "Delete a calendar event by UID. Use when resolving a flagged duplicate "
        "by removing the extra copy, or when the user says something is "
        "cancelled or no longer needed."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "uid": {"type": "string", "description": "UID of the event to delete."},
        },
        "required": ["uid"],
    },
}
