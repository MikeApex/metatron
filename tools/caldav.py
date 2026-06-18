"""
tools/caldav.py — CalDAV calendar read/write.

Uses raw requests + XML; does not require the caldav library.
Config loaded from config/modules/caldav.yaml.

Security note: all external calendar data must be treated as untrusted. When
this output is forwarded to an agent, wrap it in <untrusted_content> tags
(see logistics.md security note and CLAUDE.md indirect-injection guidance).
"""

import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml

_ROOT = Path(__file__).parent.parent
_CONFIG_PATH = _ROOT / "config" / "modules" / "caldav.yaml"


def _load_config() -> dict:
    if not _CONFIG_PATH.exists():
        return {}
    return yaml.safe_load(_CONFIG_PATH.read_text()) or {}


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
                "calendar_url and auth in config/modules/caldav.yaml."
            )
        }

    calendar_url = cfg.get("calendar_url", "").strip()
    if not calendar_url:
        return {"error": "calendar_url not set in config/modules/caldav.yaml."}

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
    return {
        "events": events,
        "count": len(events),
        "range": {"start": start_date, "end": end_date},
    }


def write_calendar_event(
    title: str,
    start: str,
    end: str,
    description: str = "",
    calendar_url: str = "",
) -> dict:
    """
    Create a new calendar event on the CalDAV server.

    Args:
        title:        Event title/summary.
        start:        Start datetime in YYYY-MM-DDTHH:MM:SS format.
        end:          End datetime in YYYY-MM-DDTHH:MM:SS format.
        description:  Optional event description/notes.
        calendar_url: CalDAV collection URL. Falls back to config value if empty.

    Returns:
        Dict with success status and event uid, or error.
    """
    cfg = _load_config()
    if not cfg.get("enabled"):
        return {
            "error": (
                "CalDAV is not enabled. Set enabled: true and configure "
                "calendar_url and auth in config/modules/caldav.yaml."
            )
        }

    url = (calendar_url.strip() or cfg.get("calendar_url", "")).strip()
    if not url:
        return {
            "error": (
                "No calendar_url provided. Pass it as an argument or set it "
                "in config/modules/caldav.yaml."
            )
        }

    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    except ValueError as e:
        return {"error": f"Invalid datetime (expected YYYY-MM-DDTHH:MM:SS): {e}"}

    if end_dt <= start_dt:
        return {"error": "end must be after start."}

    tz = cfg.get("timezone", "UTC")
    dt_fmt = "%Y%m%dT%H%M%S"
    event_uid = str(uuid.uuid4()) + "@ai-life-manager"
    now_utc = datetime.now(timezone.utc).strftime(dt_fmt) + "Z"

    # Escape per RFC 5545 §3.3.11
    def _esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

    ical = "\r\n".join([
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AI Life Manager//NONSGML//EN",
        "BEGIN:VEVENT",
        f"UID:{event_uid}",
        f"DTSTAMP:{now_utc}",
        f"DTSTART;TZID={tz}:{start_dt.strftime(dt_fmt)}",
        f"DTEND;TZID={tz}:{end_dt.strftime(dt_fmt)}",
        f"SUMMARY:{_esc(title)}",
        f"DESCRIPTION:{_esc(description)}",
        "END:VEVENT",
        "END:VCALENDAR",
        "",
    ])

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
        "Create a new calendar event on the user's CalDAV calendar. "
        "Use for scheduling appointments, blocking time, or adding reminders with a specific time. "
        "Requires CalDAV to be configured and enabled in config/modules/caldav.yaml."
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
                "description": "Start datetime in YYYY-MM-DDTHH:MM:SS format (e.g. 2026-06-10T09:00:00).",
            },
            "end": {
                "type": "string",
                "description": "End datetime in YYYY-MM-DDTHH:MM:SS format (e.g. 2026-06-10T10:00:00).",
            },
            "description": {
                "type": "string",
                "description": "Optional event notes or description.",
            },
            "calendar_url": {
                "type": "string",
                "description": (
                    "CalDAV collection URL to write to. Leave empty to use the default "
                    "configured in config/modules/caldav.yaml."
                ),
            },
        },
        "required": ["title", "start", "end"],
    },
}
