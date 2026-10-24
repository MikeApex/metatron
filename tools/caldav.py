"""
tools/caldav.py — CalDAV calendar read/write.

Uses raw requests + XML; does not require the caldav library.
Config loaded from config/personas/{persona}/caldav.yaml — per-persona and gitignored,
resolved through persona_config_dir() below. **Not** config/modules/caldav.yaml, which
nothing reads: that copy is gitignored, Mac-local, and has already drifted (it still
documents the apidata.googleusercontent.com CalDAV endpoint that config/templates/caldav.yaml
records as verified-broken on 2026-08-03 — it requires OAuth 2.0 and 401s on app passwords).
New personas are provisioned from config/templates/caldav.yaml, which is the single home.

Security note: all external calendar data is untrusted — the title, description and
location of an invite are written by whoever sent it. `read_calendar` wraps its event
payload in <untrusted_content> tags at the return boundary (tools/untrusted.py).
Implemented 2026-08-04; this docstring described it as a to-do from 2026-08-03, during
which the calendar was live in production unwrapped.
"""

import logging
import re
import time
import uuid
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse
from zoneinfo import ZoneInfo

import requests
import yaml

from core.persona import persona_config_dir
from tools.untrusted import (UNTRUSTED_CONTENT_INSTRUCTION, contains_injection_markers,
                             wrap_untrusted)

_ROOT = Path(__file__).parent.parent
logger = logging.getLogger(__name__)

# `attendees` is a local label, not an invitation. It is written as the custom
# property X-ATTENDEE-NAMES — names, not addresses — and no standard ATTENDEE
# line is ever emitted, so no CalDAV server sends anybody anything. Returned on
# every write that carries attendees because the schema description is read once
# at call time and the return value is what gets read back at answer time: on
# 2026-09-07 a session reported a person had been invited by Google Calendar on
# the strength of a bare success:true. Sending is `send_email`'s job, behind its
# confirm gate and CRM recipient allowlist; send_calendar_invite (2026-09-07) is the
# tool that actually invites someone, and rides that same gate.
_ATTENDEES_ARE_LABELS_ONLY = (
    "No invitation was sent. Attendee names are recorded on the event as a local "
    "label for conflict and duplicate matching only — nobody has been notified, "
    "and nothing will appear in their calendar. Do not tell the user that anyone "
    "has been invited. To genuinely invite them, use send_calendar_invite — that sends a "
    "real invitation they can accept, and needs the user's approval first."
)

# Returned with every read_calendar result, for the same reason as the note above:
# the return value is what is read back at answer time.
_MULTI_CALENDAR_NOTE = (
    "Events come from every calendar the user's account can see. An event that sits on "
    "more than one calendar is shown once; `calendars` lists where it appears. Events "
    "with read_only true cannot be changed or deleted by this system — that includes "
    "invitations on the user's own account calendar, which are still the user's. Events "
    "with shared true sit only on a calendar someone else shares with the user: they may "
    "be other people's commitments rather than the user's own. Where copies of one event "
    "disagree, `discrepancies` holds the other "
    "values — mention a disagreement that matters (a different start time) rather than "
    "picking one silently."
)


def _config_path(persona: str | None = None) -> Path:
    """Per-persona. Each persona has its own calendar and its own credentials."""
    return persona_config_dir(persona) / "caldav.yaml"


def _load_config(persona: str | None = None) -> dict:
    path = _config_path(persona)
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


# Appended to CalDAV failures that are actually authentication failures (401/403).
#
# Same lesson as tools/mail.py's _credential_remedy, and it has to live in both
# because the two integrations hold the same app-specific password in two separate
# files: changing the Google account password revokes it, and regenerating it in
# the account reaches neither file. On 2026-09-10 caldav.yaml still held the value
# from 2026-08-03 while the account had moved on, and the failure text said only
# "CalDAV request failed: 401" — true, and useless for acting on. `[DB-0910-01]`.
def _safe_config_path(persona: str | None = None) -> str:
    try:
        return str(_config_path(persona))
    except Exception:
        return "this persona's caldav.yaml"


def _credential_remedy(persona: str | None = None) -> str:
    return (
        f" A 401 here almost always means the app-specific password has been revoked, "
        f"which happens automatically whenever the Google account password changes. "
        f"Fixing this takes TWO steps, and the second is the one usually missed: "
        f"(1) generate a new app-specific password in the Google account, then "
        f"(2) write that value into the auth.password line of {_safe_config_path(persona)} "
        f"on the machine running this system. Step 1 alone changes nothing here. "
        f"No restart is needed afterwards — this file is re-read on every call."
    )


def _auth_hint(e: Exception) -> str:
    """The remedy above, but only when the server actually rejected the credentials."""
    status = getattr(getattr(e, "response", None), "status_code", None)
    return _credential_remedy() if status in (401, 403) else ""


def _parse_ical_dt(val: str, tzid: str = "", target_tz: str = "", utc_to_local: bool = False) -> str:
    """Parse iCalendar datetime string to ISO 8601. Returns val unchanged on failure.

    A TZID-qualified time is converted into `target_tz` (the persona's timezone) and
    emitted naive, so a time already in that zone comes out exactly as it always did.
    Until 2026-10-24 the TZID was discarded and a "22:00 Europe/Budapest" read as 22:00
    local — harmless while every event came from this system's own writes, which all
    carry the persona's zone, and wrong the moment another person's calendar is read.

    A UTC ("Z") value stays timezone-aware unless `utc_to_local` is set: the
    single-calendar read has always returned it that way, and its callers are left
    exactly as they were. The multi-calendar read sets it, because mixing aware and
    naive values makes interval comparison raise.
    """
    if not val:
        return ""
    utc = val.endswith("Z")
    clean = val.rstrip("Z")
    for fmt in ("%Y%m%dT%H%M%S", "%Y%m%d"):
        try:
            dt = datetime.strptime(clean, fmt)
        except ValueError:
            continue
        if fmt == "%Y%m%d":
            return dt.isoformat()
        try:
            target = ZoneInfo(target_tz) if target_tz else None
            if utc:
                dt = dt.replace(tzinfo=timezone.utc)
                if utc_to_local and target:
                    dt = dt.astimezone(target).replace(tzinfo=None)
            elif tzid and target and tzid != target_tz:
                dt = dt.replace(tzinfo=ZoneInfo(tzid)).astimezone(target).replace(tzinfo=None)
        except Exception:  # an unknown TZID (e.g. a Windows zone name) is left as written
            pass
        return dt.isoformat()
    return val


def _parse_ical_events(ical_text: str) -> list[dict]:
    """Extract VEVENT blocks from iCalendar text and return as list of raw dicts.

    Lines inside a nested component (VALARM) are skipped: an alarm's own DESCRIPTION
    ("This is an event reminder") used to overwrite the event's. Property parameters
    are kept under "_params" so a TZID survives to _format_event.
    """
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
    nested = 0
    current: dict = {}

    for line in unfolded:
        if line == "BEGIN:VEVENT":
            in_event = True
            nested = 0
            current = {"_params": {}}
        elif line == "END:VEVENT":
            if in_event:
                events.append(current)
            in_event = False
            current = {}
        elif in_event and line.startswith("BEGIN:"):
            nested += 1
        elif in_event and nested and line.startswith("END:"):
            nested -= 1
        elif in_event and not nested and ":" in line:
            key, _, value = line.partition(":")
            parts = key.split(";")
            base_key = parts[0].strip()
            current[base_key] = value.strip()
            current["_params"][base_key] = {
                p.split("=", 1)[0].upper(): p.split("=", 1)[1].strip('"')
                for p in parts[1:] if "=" in p
            }

    return events


def _format_event(raw: dict, target_tz: str = "", utc_to_local: bool = False) -> dict:
    """Normalize a raw VEVENT dict to a clean structured form."""
    attendee_field = raw.get("X-ATTENDEE-NAMES", "")
    params = raw.get("_params") or {}

    def _dt(key: str) -> str:
        return _parse_ical_dt(raw.get(key, ""), (params.get(key) or {}).get("TZID", ""),
                              target_tz, utc_to_local)

    return {
        "uid": raw.get("UID", ""),
        "title": raw.get("SUMMARY", ""),
        "start": _dt("DTSTART"),
        "end": _dt("DTEND"),
        "description": raw.get("DESCRIPTION", "").replace("\\n", "\n").replace("\\,", ",").replace("\\;", ";"),
        "location": raw.get("LOCATION", ""),
        "status": raw.get("STATUS", ""),
        "recurrence": raw.get("RRULE", ""),
        "attendees": [a.strip() for a in attendee_field.split(",") if a.strip()],
        "conflict_check_status": raw.get("X-CONFLICT-CHECK-STATUS", ""),
    }


def _report_raw(calendar_url: str, auth: tuple, start_date: str, end_date: str) -> list[dict]:
    """One CalDAV REPORT against one collection. Raises on transport or parse failure."""
    start_dt = datetime.fromisoformat(start_date + "T00:00:00").strftime("%Y%m%dT%H%M%SZ")
    end_dt = datetime.fromisoformat(end_date + "T23:59:59").strftime("%Y%m%dT%H%M%SZ")
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
    root = ET.fromstring(response.text)
    raws = []
    for response_el in root.findall(".//{DAV:}response"):
        cal_data_el = response_el.find(
            ".//{urn:ietf:params:xml:ns:caldav}calendar-data"
        )
        if cal_data_el is not None and cal_data_el.text:
            raws.extend(_parse_ical_events(cal_data_el.text))
    return raws


# --- Every calendar the account can see (2026-10-24) -------------------------
#
# Until this date the system read exactly one collection, `calendar_url`, so a
# calendar shared with the account was invisible however it was shared. Which
# calendars a Google account exposes over CalDAV is set by the user at
# calendar.google.com/calendar/syncselect — that page, not this file, is the
# include/exclude control. `extra_calendars:` adds collections discovery misses;
# `discover_calendars: false` turns discovery off from config, without a deploy.
#
# Only `read_calendar` and the write-time conflict check (tools/scheduling.py) ask
# for "all". Every unattended job — reconcile, travel watch, accountability,
# location, the duplicate audit, the task ledger's calendar link — keeps reading
# the configured calendar alone, so none of them starts asking about, alerting on
# or scoring against events that belong to someone else, and their uid-keyed
# seen-sets keep the inputs they were built on. Widening any of them is a decision,
# not a default.
#
# "Writable" means the configured calendar_url and nothing else. Google reports a
# write privilege even on its holidays calendar, so the server's privilege set is
# not trusted for this.

_DISCOVERY_TTL_SECONDS = 600  # in-process only: dies with the process, costs nothing to hold
_discovery_cache: dict[tuple, tuple[float, list[dict], str]] = {}

_DAV = "{DAV:}"
_CALDAV_NS = "{urn:ietf:params:xml:ns:caldav}"


def _collection_key(url: str) -> str:
    """Comparable identity of a collection: decoded path, no trailing slash."""
    return unquote(urlparse(url).path).rstrip("/")


def _propfind(url: str, auth: tuple, props: str, depth: str) -> ET.Element:
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">'
        f"<d:prop>{props}</d:prop></d:propfind>"
    )
    response = requests.request(
        "PROPFIND", url, data=body.encode("utf-8"), auth=auth, timeout=15,
        headers={"Content-Type": "application/xml; charset=utf-8", "Depth": depth},
    )
    response.raise_for_status()
    return ET.fromstring(response.text)


def _first_href(root: ET.Element, prop: str) -> str:
    el = root.find(f".//{prop}/{_DAV}href")
    return (el.text or "").strip() if el is not None else ""


def _discover_calendars(cfg: dict, auth: tuple) -> tuple[list[dict], str]:
    """
    RFC 6764/4791 discovery: principal → calendar-home-set → Depth 1 listing.

    The principal is asked for at the configured collection first, then at the
    usual server roots — Google answers only at /calendar/dav/ (probed live
    2026-10-24; the collection itself and /.well-known/caldav return nothing).
    Returns ([{"url", "name"}], status) where status is "ok" or the reason it failed.
    """
    calendar_url = str(cfg.get("calendar_url", "")).strip()
    cache_key = (calendar_url, auth[0])
    hit = _discovery_cache.get(cache_key)
    if hit and time.monotonic() - hit[0] < _DISCOVERY_TTL_SECONDS:
        return hit[1], hit[2]

    calendars: list[dict] = []
    status = "ok"
    try:
        principal = ""
        for start in (calendar_url, urljoin(calendar_url, "/.well-known/caldav"),
                      urljoin(calendar_url, "/calendar/dav/"), urljoin(calendar_url, "/")):
            try:
                principal = _first_href(
                    _propfind(start, auth, "<d:current-user-principal/>", "0"),
                    f"{_DAV}current-user-principal")
            except Exception:
                principal = ""
            if principal:
                break
        if not principal:
            raise RuntimeError("no current-user-principal at the calendar or the server root")
        home = _first_href(
            _propfind(urljoin(calendar_url, principal), auth, "<c:calendar-home-set/>", "0"),
            f"{_CALDAV_NS}calendar-home-set")
        if not home:
            raise RuntimeError("principal has no calendar-home-set")
        listing = _propfind(urljoin(calendar_url, home), auth,
                            "<d:displayname/><d:resourcetype/>", "1")
        for resp in listing.findall(f"{_DAV}response"):
            href_el = resp.find(f"{_DAV}href")
            if href_el is None or not (href_el.text or "").strip():
                continue
            if resp.find(f".//{_DAV}resourcetype/{_CALDAV_NS}calendar") is None:
                continue
            name_el = resp.find(f".//{_DAV}displayname")
            calendars.append({
                "url": urljoin(calendar_url, href_el.text.strip()),
                "name": (name_el.text or "").strip() if name_el is not None else "",
            })
    except Exception as exc:  # noqa: BLE001 — any failure degrades to the configured calendar
        # Not cached: one transient failure must not hide the other calendars for ten minutes.
        logger.warning("[caldav] calendar discovery failed, reading the configured calendar only: %s", exc)
        return [], f"discovery failed: {exc}"

    _discovery_cache[cache_key] = (time.monotonic(), calendars, status)
    return calendars, status


def _calendar_set(cfg: dict, auth: tuple) -> tuple[list[dict], str]:
    """The writable calendar first, then everything discovered or listed, deduped."""
    calendar_url = str(cfg.get("calendar_url", "")).strip()
    if cfg.get("discover_calendars", True) is False:
        discovered, status = [], "off"
    else:
        discovered, status = _discover_calendars(cfg, auth)
    own_key = _collection_key(calendar_url)
    own_name = next((c["name"] for c in discovered
                     if _collection_key(c["url"]) == own_key and c["name"]), "") or "Main calendar"
    result = [{"url": calendar_url, "name": own_name, "writable": True, "mine": True}]
    seen = {own_key}
    # The account's own calendar (on Google, the collection named after the login) is
    # where invitations to the user land. It is not edited here, but it is the user's:
    # "read-only" and "someone else's" are different things.
    account = (auth[0] or "").lower()
    extras = []
    for entry in cfg.get("extra_calendars") or []:
        entry = str(entry).strip()
        if not entry:
            continue
        # A bare Google calendar ID is accepted as well as a full collection URL.
        url = entry if "://" in entry else f"https://www.google.com/calendar/dav/{entry}/events/"
        extras.append({"url": url, "name": ""})
    for cal in discovered + extras:
        key = _collection_key(cal["url"])
        if key in seen:
            continue
        seen.add(key)
        name = cal["name"] or unquote(key.rstrip("/").split("/")[-2] if key.endswith("/events")
                                      else key.rsplit("/", 1)[-1])
        mine = bool(account) and account in [seg.lower() for seg in key.split("/")]
        result.append({"url": cal["url"], "name": name, "writable": False, "mine": mine})
    return result, status


def _merge_title(title: str) -> str:
    return " ".join(re.sub(r"[^\w]+", " ", (title or "").lower()).split())


def _as_local(value: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def _span(ev: dict) -> tuple[datetime, datetime] | None:
    start = _as_local(ev.get("start", ""))
    if start is None:
        return None
    end = _as_local(ev.get("end", "")) or start
    if end <= start:
        end = start + (timedelta(days=1) if ev["_all_day"] else timedelta(minutes=1))
    return start, end


def _same_event(a: dict, b: dict) -> bool:
    """Same (UID, RECURRENCE-ID) — or, for one-offs only, equal titles over overlapping time."""
    if a["uid"] and a["uid"] == b["uid"] and a["_recurrence_id"] == b["_recurrence_id"]:
        return True
    if a["recurrence"] or b["recurrence"] or a["_recurrence_id"] or b["_recurrence_id"]:
        return False
    if not a["_mtitle"] or a["_mtitle"] != b["_mtitle"] or a["_all_day"] != b["_all_day"]:
        return False
    sa, sb = _span(a), _span(b)
    return bool(sa and sb and sa[0] < sb[1] and sa[1] > sb[0])


def _merge_group(group: list[dict]) -> dict:
    """
    One event out of copies on different calendars. The copy on the writable
    calendar wins every field (Mike, 2026-10-24: edits only ever land there, so any
    other winner would show a moved event at its old time). With no writable copy,
    the most recently modified copy wins. Where copies disagree, the losing values
    are listed under `discrepancies` with the calendar they came from — evidence for
    the agent to mention, never silently dropped.
    """
    writable = [e for e in group if e["_writable"]]
    winner = writable[0] if writable else max(
        group, key=lambda e: (e["_last_modified"], -e["_order"]))
    # The uid must not move between runs, so it does not follow the field winner.
    uid_source = writable[0] if writable else min(group, key=lambda e: e["_order"])
    merged = {k: v for k, v in winner.items() if not k.startswith("_")}
    merged["uid"] = uid_source["uid"]
    merged["attendees"] = list(merged.get("attendees") or [])

    discrepancies: dict[str, list] = {}
    for other in group:
        if other is winner:
            continue
        for field in ("title", "start", "end", "location", "status"):
            ov, wv = other.get(field) or "", winner.get(field) or ""
            if ov and wv and ov != wv:
                discrepancies.setdefault(field, []).append({"value": ov, "calendar": other["_calendar"]})
        if not merged.get("location") and other.get("location"):
            merged["location"] = other["location"]
        od = (other.get("description") or "").strip()
        if od and od not in (merged.get("description") or ""):
            merged["description"] = ((merged.get("description") or "").strip() + "\n\n" + od).strip()
        for name in other.get("attendees") or []:
            if name not in merged["attendees"]:
                merged["attendees"].append(name)
        if not merged.get("recurrence") and other.get("recurrence"):
            merged["recurrence"] = other["recurrence"]
    merged["calendars"] = [e["_calendar"] for e in sorted(group, key=lambda e: e["_order"])]
    merged["read_only"] = not writable
    merged["shared"] = not any(e["_mine"] for e in group)
    if discrepancies:
        merged["discrepancies"] = discrepancies
    return merged


def _merge_across_calendars(events: list[dict]) -> list[dict]:
    """
    Group copies of the same event that sit on different calendars. Never merges two
    events from the same calendar — duplicates within one calendar are
    tools/calendar_audit.py's to find, and may be deliberate.
    """
    groups: list[list[dict]] = []
    for ev in sorted(events, key=lambda e: (e["_order"], e.get("start", ""), e["uid"])):
        for group in groups:
            if any(m["_order"] == ev["_order"] for m in group):
                continue
            if any(_same_event(m, ev) for m in group):
                group.append(ev)
                break
        else:
            groups.append([ev])
    return [_merge_group(g) for g in groups]


def _query_events(start_date: str, end_date: str, persona: str | None = None,
                  calendars: str = "own") -> dict:
    """
    Raw CalDAV REPORT query, returning unwrapped structured events.

    Shared by read_calendar (which wraps the result for LLM consumption) and
    tools/scheduling.py (which needs to run interval math and string comparison
    directly against the data — comparing untrusted text in Python is not the
    same thing as handing it to an LLM as instructions, so no wrapping boundary
    applies here). Keeping the REPORT-request/parse logic in one place means
    scheduling.py never re-implements CalDAV querying independently.

    `calendars="own"` (the default) reads the configured calendar only — what every
    caller got before 2026-10-24. `calendars="all"` reads every calendar the account
    exposes and merges the copies of one event into one; each event then also carries
    `calendars`, `read_only`, `shared` and, where copies disagree, `discrepancies`. See the
    block comment above _discover_calendars for who asks for which, and why.

    Returns {"events": [...]} on success, {"error": "..."} on failure. Only the
    configured calendar failing is an error; another calendar failing is reported
    under `calendars_failed`.
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
        datetime.fromisoformat(start_date + "T00:00:00")
        datetime.fromisoformat(end_date + "T23:59:59")
    except ValueError as e:
        return {"error": f"Invalid date format (expected YYYY-MM-DD): {e}"}

    auth_cfg = cfg.get("auth", {})
    auth = (auth_cfg.get("username", ""), auth_cfg.get("password", ""))
    target_tz = str(cfg.get("timezone", "") or "")

    if calendars != "all":
        try:
            raws = _report_raw(calendar_url, auth, start_date, end_date)
        except requests.RequestException as e:
            return {"error": f"CalDAV request failed: {e}{_auth_hint(e)}"}
        except ET.ParseError as e:
            return {"error": f"Failed to parse CalDAV response: {e}"}
        events = [_format_event(raw, target_tz) for raw in raws]
        events.sort(key=lambda e: e.get("start", ""))
        return {"events": events, "calendar_url": calendar_url}

    cal_set, discovery = _calendar_set(cfg, auth)
    with ThreadPoolExecutor(max_workers=min(6, len(cal_set))) as pool:
        futures = [pool.submit(_report_raw, c["url"], auth, start_date, end_date) for c in cal_set]
        outcomes = []
        for fut in futures:
            try:
                outcomes.append((fut.result(), None))
            except Exception as exc:  # noqa: BLE001
                outcomes.append((None, exc))

    own_raws, own_err = outcomes[0]
    if own_err is not None:
        if isinstance(own_err, ET.ParseError):
            return {"error": f"Failed to parse CalDAV response: {own_err}"}
        return {"error": f"CalDAV request failed: {own_err}{_auth_hint(own_err)}"}

    events, read, failed = [], [], []
    for order, (cal, (raws, err)) in enumerate(zip(cal_set, outcomes)):
        if err is not None:
            failed.append(cal["name"])
            logger.warning("[caldav] calendar %r unreadable, skipped: %s", cal["name"], err)
            continue
        read.append(cal["name"])
        for raw in raws:
            ev = _format_event(raw, target_tz, utc_to_local=True)
            ev.update({
                "_order": order,
                "_calendar": cal["name"],
                "_writable": cal["writable"],
                "_mine": cal["mine"],
                "_recurrence_id": raw.get("RECURRENCE-ID", ""),
                "_last_modified": raw.get("LAST-MODIFIED", ""),
                "_all_day": (raw.get("_params", {}).get("DTSTART") or {}).get("VALUE") == "DATE"
                            or len(raw.get("DTSTART", "")) == 8,
                "_mtitle": _merge_title(raw.get("SUMMARY", "")),
            })
            events.append(ev)

    merged = _merge_across_calendars(events)
    merged.sort(key=lambda e: e.get("start", ""))
    return {"events": merged, "calendar_url": calendar_url, "calendars_read": read,
            "calendars_failed": failed, "discovery": discovery}


def _read_only_home(uid: str, cfg: dict, auth: tuple) -> str:
    """Name of the non-writable calendar holding `uid`, or "" — only asked after a 404."""
    try:
        cal_set, _ = _calendar_set(cfg, auth)
        for cal in cal_set[1:]:
            response = requests.get(cal["url"].rstrip("/") + "/" + uid + ".ics", auth=auth, timeout=15)
            if response.status_code == 200 and "BEGIN:VEVENT" in response.text:
                return cal["name"]
    except Exception:  # noqa: BLE001 — falls back to the plain "not found"
        pass
    return ""


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
            elsewhere = _read_only_home(uid, cfg, auth)
            if elsewhere:
                # The name is set by whoever owns that calendar — wrapped, as on the read path.
                return {"error": (
                    "That event is on a calendar this system can read but does not edit "
                    "(named under `calendar`). Nothing was changed. It can only be changed "
                    "in that calendar itself."),
                    "calendar": wrap_untrusted(elsewhere, source="calendar list")}
            return {"error": f"No event found with uid '{uid}'."}
        response.raise_for_status()
    except requests.RequestException as e:
        return {"error": f"Failed to fetch event: {e}{_auth_hint(e)}"}

    raw_events = _parse_ical_events(response.text)
    if not raw_events:
        return {"error": f"Event '{uid}' returned no parseable VEVENT."}

    event = _format_event(raw_events[0], str(cfg.get("timezone", "") or ""))
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
    raw = _query_events(start_date, end_date, calendars="all")
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
        "calendar_note": _MULTI_CALENDAR_NOTE,
    }
    # Calendar names are set by whoever owns each calendar, so they travel wrapped too.
    # A calendar that could not be read is said out loud: an empty day on it is unknown,
    # not free.
    sources = {"read": raw.get("calendars_read", []), "unreadable": raw.get("calendars_failed", [])}
    if raw.get("discovery") not in (None, "ok", "off"):
        sources["discovery"] = raw["discovery"]
    result["calendar_sources"] = wrap_untrusted(_json.dumps(sources, ensure_ascii=False),
                                                source="calendar list")
    # What the task ledger records about these entries, by uid (plan § 5 row 2): written by
    # code from the ledger, so it sits OUTSIDE the untrusted wrapper — it is not calendar
    # text. A deadline entry that is done says so here, series occurrences included.
    try:
        from tools.obligations import calendar_ledger_notes
        notes = calendar_ledger_notes(events)
        if notes:
            result["task_ledger"] = notes
    except Exception:
        pass
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
                      CRM contacts for conflict/duplicate matching. **A label,
                      not an invitation** — no notification is sent to anyone.
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
                "in this persona's caldav.yaml."
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
        return {"error": f"Failed to write calendar event: {e}{_auth_hint(e)}"}

    result = {
        "success": True,
        "uid": event_uid,
        "title": title_to_write,
        "start": start,
        "end": end,
        "url": event_url,
    }
    # The task ledger's calendar link (archive/plans/task_ledger_plan_2026-10-23.md § 5 row 2).
    # An all-day, non-repeating entry whose title and date EXACTLY name an open deadline is
    # linked to it, so closing the task marks this entry ✓ and moving it moves this. Exact or
    # nothing: a merely similar event, once linked, would be retitled by code.
    if all_day and not recurrence:
        try:
            from tools.obligations import link_calendar_exact
            linked = link_calendar_exact(title, str(start)[:10], event_uid)
            if linked:
                result["task_linked"] = linked
        except Exception:
            pass
    if attendees:
        result["attendees_recorded"] = attendees
        result["invitations_sent"] = False
        result["note"] = _ATTENDEES_ARE_LABELS_ONLY
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
        alarm_minutes_before, attendees: Same meaning as write_calendar_event —
                      including that attendees are labels, never invitations.
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
        return {"error": f"Failed to update calendar event: {e}{_auth_hint(e)}"}

    result = {"success": True, "uid": uid, "title": title_to_write, "start": new_start, "end": new_end}
    if new_attendees:
        result["attendees_recorded"] = new_attendees
        result["invitations_sent"] = False
        result["note"] = _ATTENDEES_ARE_LABELS_ONLY
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
        return {"error": f"Failed to delete calendar event: {e}{_auth_hint(e)}"}

    return {"success": True, "uid": uid}


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

READ_CALENDAR_SCHEMA = {
    "name": "read_calendar",
    "description": (
        "Read calendar events between two dates from every calendar the user's account "
        "can see, including calendars shared with them. Returns a list of events with "
        "title, start, end, description, location, the calendars each appears on, and "
        "whether it is read_only (on a calendar this system cannot edit). An event on "
        "several calendars appears once. "
        "Requires CalDAV to be configured and enabled in this persona's caldav.yaml."
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
                    "person, it materially improves duplicate detection. "
                    "THIS DOES NOT INVITE ANYONE: it records a name on the event "
                    "for matching, sends no notification, and puts nothing in "
                    "anyone else's calendar. Never report an attendee as invited."
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
            "attendees": {"type": "array", "items": {"type": "string"}, "description": "New attendee list, if changing. Records names for matching only — invites nobody, notifies nobody."},
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


# --- Invitation support -----------------------------------------------------
#
# Everything below exists so that "invite Iva to the concert" can be honoured.
# Before 2026-09-07 it could not be: `attendees` on a write is a private label
# (see _ATTENDEES_ARE_LABELS_ONLY) and no standard ATTENDEE line was ever
# emitted, so sessions reported invitations that had never been sent.
#
# The chosen route deliberately does NOT put an ATTENDEE line on the stored
# CalDAV event and let the server mail people. That would create an outbound
# message to a third party on the calendar path, around `send_email`'s
# confirmation gate and its CRM recipient allowlist — the single-owner property
# bought on 2026-08-09/10. Instead the invitation is a normal approved email
# carrying a METHOD:REQUEST iCalendar part, sent by tools.mail.send_calendar_invite
# through exactly the gate every other outbound message goes through.


def _escape_ical(s: str) -> str:
    """RFC 5545 text escaping. Module-level twin of the _esc closures above."""
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def find_event_for_invite(uid: str = "", title: str = "", date: str = "") -> dict:
    """
    Resolve the single event an invitation refers to.

    Two ways in, because the agent that owns outbound messaging is
    `relationships`, which holds no calendar tool and so will rarely have a uid
    to hand. Resolving here in Python is the same move `_resolve_attendees()`
    already makes in the other direction — reaching into the CRM on the calendar's
    behalf — and it keeps sending in one place rather than granting a second
    agent the calendar.

    Ambiguity is an error, never a guess: inviting someone to the wrong event is
    not recoverable by the user once the mail has gone.

    Returns the event dict, or {"error": ...} with "candidates" when more than
    one event on `date` matches `title`.
    """
    if uid:
        return _get_event_by_uid(uid)
    if not (title and date):
        return {"error": "Give either uid, or both title and date (YYYY-MM-DD)."}

    # _query_events, not read_calendar: read_calendar wraps its event list into an
    # <untrusted_content> STRING at the return boundary, so `.get("events")` there is
    # text, not rows, and every match below would silently find nothing.
    day = _query_events(date, date)
    if "error" in day:
        return day
    events = day.get("events") or []
    needle = title.strip().lower()
    matches = [e for e in events
               if needle in (e.get("title") or "").lower()
               or (e.get("title") or "").lower() in needle]
    if not matches:
        return {"error": f"No event matching '{title}' on {date}. "
                         f"Events that day: {[e.get('title') for e in events] or 'none'}."}
    if len(matches) > 1:
        return {"error": f"'{title}' on {date} matches {len(matches)} events — say which one.",
                "candidates": [{"uid": e.get("uid"), "title": e.get("title"),
                                "start": e.get("start")} for e in matches]}
    return matches[0]


def build_invite_ics(event: dict, organizer_email: str, attendee_email: str,
                     attendee_name: str = "") -> str:
    """
    Build a METHOD:REQUEST iCalendar payload for `event`.

    METHOD:REQUEST plus a real ATTENDEE line is what makes a mail client show
    Accept/Decline and write the event into the recipient's own calendar. The
    UID is the event's real UID, so a later update or cancellation for the same
    UID supersedes this one in the recipient's calendar rather than duplicating it.

    The event's own title, description and location are used verbatim. For an
    event the user created that is exactly right; for one imported from someone
    else's invitation the text is attacker-writable, which is why the whole
    payload is rendered into the approval preview before anything is sent.
    """
    tz = _load_config().get("timezone", "UTC")
    now_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    def _dt(value: str, is_end: bool = False) -> str:
        # An all-day event has no "T" in its ISO form and takes DATE values.
        if "T" not in (value or ""):
            d = datetime.strptime(value, "%Y-%m-%d")
            prop = "DTEND" if is_end else "DTSTART"
            return f"{prop};VALUE=DATE:{d.strftime('%Y%m%d')}"
        d = datetime.fromisoformat(value)
        prop = "DTEND" if is_end else "DTSTART"
        return f"{prop};TZID={tz}:{d.strftime('%Y%m%dT%H%M%S')}"

    cn = _escape_ical(attendee_name) if attendee_name else attendee_email
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AI Life Manager//NONSGML//EN",
        "METHOD:REQUEST",
        "BEGIN:VEVENT",
        f"UID:{event.get('uid', '')}",
        f"DTSTAMP:{now_utc}",
        _dt(event.get("start", "")),
        _dt(event.get("end", ""), is_end=True),
        f"SUMMARY:{_escape_ical(event.get('title', ''))}",
        f"DESCRIPTION:{_escape_ical(event.get('description', '') or '')}",
        f"LOCATION:{_escape_ical(event.get('location', '') or '')}",
        f"ORGANIZER:mailto:{organizer_email}",
        f"ATTENDEE;CUTYPE=INDIVIDUAL;ROLE=REQ-PARTICIPANT;PARTSTAT=NEEDS-ACTION;"
        f"RSVP=TRUE;CN={cn}:mailto:{attendee_email}",
        "SEQUENCE:0",
        "STATUS:CONFIRMED",
    ]
    if event.get("recurrence"):
        lines.append(f"RRULE:{event['recurrence']}")
    lines += ["END:VEVENT", "END:VCALENDAR", ""]
    return "\r\n".join(lines)
