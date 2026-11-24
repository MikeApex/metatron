"""
tools/logistics_log.py — Logistics' own records, kept by code (instructions-to-code Stage 4, 4d:
M13, M12's code half, M14).

Plan: archive/plans/instructions_to_code_stage4_evidence_plan_2026-11-23.md § 1 M12, M13, M14,
with build-time amendment 4 (M14 reads structured rows, never the wrapped string) and DECISIONS
4-6 (actions only on scheduled turns) and 4-7 (no: a read never writes). Called from
core/orchestrator.py: `record_run` after a Logistics run in `_run_single_agent`, and
`read_calendar_reverified` from `dispatch_tool` when Logistics itself calls `read_calendar`.
Never a tool, never in a schema.

What a user notices:
- **M13.** The day's log says what Logistics actually did — the events it put on the calendar,
  the reminders it set, the horizon items it filed — written from the calls that ran, not from
  the model's recollection of them, and kept across every run that day. (Logistics no longer
  needs a model round to write it: measured, it spent one on 57 of 99 calls.)
- **M12.** Nothing here records a "pending" item. Waiting on someone else is a ledger `waiting`
  row, which the ledger raises once at `check_back`; this module writes no `pending_items`.
- **M14.** An event saved while the conflict check was down ([VERIFY]) is re-checked the next
  time Logistics reads that day, and the result is handed to it. The calendar is never written
  by a read: clearing [VERIFY] stays Logistics' own `update_calendar_event`, on the evidence.

The rules, each tested in tests/test_logistics_log.py:
1. Only calls that succeeded are recorded (a failed, refused or unconfirmed one is not).
2. **Append, never replace.** `recorded_by_code` is a code-owned sub-dict the model's own
   `logistics` writes never name; `_deep_merge` recurses into dicts, so it survives them. Code
   reads today's, appends, de-duplicates by (tool, uid or title, start) and writes it back.
3. Action lists are written on any turn — an event that was scheduled is a fact whoever started
   the turn. The prose-derived `coordination_opportunities` only on a real user turn (4-6).
4. M14: at most 2 events per read, future ones only, each checked once per request; only
   `tools.scheduling.check_calendar_conflicts`, which reads and writes nothing.

Cost: M13 one day-log read and write per Logistics run that acted. M14 one local conflict query
(a CalDAV read, ≈1–2 s) per unverified future event, only on a Logistics read while such events
exist. Nothing persists beyond the day file it describes; the re-checked uids die with the
request trace.
"""

from __future__ import annotations

import logging
import re
import threading
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

SUBKEY = "recorded_by_code"
LISTS = ("events_scheduled", "reminders_set", "horizon_items", "coordination_opportunities")
MAX_COORDINATION = 5
_TEXT_CHARS = 300

_WRITE_LOCK = threading.Lock()      # read-append-write of today's sub-dict is one step
_REVERIFY_LOCKS: dict[str, threading.Lock] = {}   # per persona: one user never waits on another
_REVERIFY_LOCKS_GUARD = threading.Lock()


def _reverify_lock() -> threading.Lock:
    """A uid is checked once per request even under parallel reads — under a lock per persona,
    so one user's CalDAV re-check never holds up another's read."""
    from core.persona import current_persona
    key = current_persona() or ""
    with _REVERIFY_LOCKS_GUARD:
        lock = _REVERIFY_LOCKS.get(key)
        if lock is None:
            lock = _REVERIFY_LOCKS[key] = threading.Lock()
        return lock

_UID_RE = re.compile(r'"uid"\s*:\s*"([^"]+)"')


# --- M13: what the run actually did ----------------------------------------------------------

def _succeeded(tc) -> bool:
    from core.actions import designed_refusal
    preview = str(getattr(tc, "result_preview", "") or "").lstrip()
    if getattr(tc, "ok", True) is False or designed_refusal(preview):
        return False
    if preview.startswith(("Error", "error", "Not filed", "Not ")):
        return False
    return "PENDING_CONFIRMATION" not in preview


def _short(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):          # all_day=False is a change worth recording as such
        return "true" if value else "false"
    text = " ".join(str(value).split())
    return text[:_TEXT_CHARS]


def actions_from(agent_rec) -> dict[str, list[dict]]:
    """The run's successful calendar, reminder and horizon calls, from its own trace record."""
    out: dict[str, list[dict]] = {k: [] for k in LISTS[:3]}
    if agent_rec is None:
        return out
    for turn in getattr(agent_rec, "turns", []) or []:
        for tc in turn.tool_calls:
            if not _succeeded(tc):
                continue
            a = tc.args if isinstance(tc.args, dict) else {}
            if tc.name == "write_calendar_event":
                m = _UID_RE.search(str(tc.result_preview or ""))
                out["events_scheduled"].append({
                    "tool": tc.name, "uid": m.group(1) if m else "",
                    "title": _short(a.get("title")), "start": _short(a.get("start"))})
            elif tc.name == "update_calendar_event":
                row = {"tool": tc.name, "uid": _short(a.get("uid"))}
                for k in ("title", "start"):
                    if a.get(k):
                        row[k] = _short(a.get(k))
                # What this update changed — so two different updates to one event are two rows.
                changed = {k: _short(v) for k, v in sorted(a.items())
                           if k != "uid" and v not in (None, "", [], {})}
                if changed:
                    row["changed"] = changed
                out["events_scheduled"].append(row)
            elif tc.name == "write_schedule":
                when = (a.get("at") or (f"{a.get('day')} {a.get('time')}".strip()
                                        if a.get("day") or a.get("time") else "")
                        or (f"every {a.get('interval_minutes')} minutes"
                            if a.get("interval_minutes") else ""))
                out["reminders_set"].append({"tool": tc.name, "name": _short(a.get("name")),
                                             "when": _short(when)})
            elif tc.name == "record_horizon_item":
                out["horizon_items"].append({"tool": tc.name, "title": _short(a.get("title")),
                                             "date": _short(a.get("date"))})
    return out


# A model's way of saying there is nothing is not an opportunity — but only as the WHOLE line:
# "None identified", "None at this time", "Nothing to note", "n/a", "No cross-domain
# opportunities". A line that starts that way and goes on ("None of the errands overlap, but the
# pharmacy is next to the dentist") is an opportunity, and is kept (review of 1c6f39d, item 6).
_NONE_TAIL = (r"(?:\s+(?:identified|found|noted|today|now|for\s+now|at\s+(?:this|the\s+moment|"
              r"present)(?:\s+time)?|this\s+(?:time|turn|session|week)|right\s+now|to\s+"
              r"(?:note|report|flag|coordinate|add|surface)|yet|so\s+far|apparent|currently))*")
_NONE_RE = re.compile(
    r"^(?:none|nothing|nil|n/?a|omit(?:ted)?|-+|no(?:\s+(?:cross[-\s]?domain|coordination|"
    r"new|clear|obvious|relevant))*\s+(?:coordination\s+)?opportunit(?:y|ies)|no)"
    + _NONE_TAIL + r"[\s.!]*$", re.IGNORECASE)


def _is_none(text: str) -> bool:
    t = str(text or "").strip().strip("[]()").strip()
    return not t or bool(_NONE_RE.match(t))


def coordination_from(output: str) -> list[dict]:
    """The `COORDINATION_OPPORTUNITIES:` line (and `- ` lines under it), as written."""
    text = str(output or "")
    if "COORDINATION_OPPORTUNITIES:" not in text:
        return []
    first, _, rest = text.split("COORDINATION_OPPORTUNITIES:", 1)[1].partition("\n")
    items: list[str] = []
    head = first.strip().strip("[]").strip()
    if not _is_none(head):
        items.append(head)
    for raw in rest.splitlines():
        line = raw.strip()
        if not line.startswith("- "):
            break
        body = line[2:].strip()
        if not _is_none(body):
            items.append(body)
    return [{"text": _short(x)} for x in items[:MAX_COORDINATION]]


def _key(list_name: str, row: dict) -> tuple:
    if list_name == "events_scheduled":
        changed = row.get("changed") if isinstance(row.get("changed"), dict) else {}
        return (row.get("tool"), row.get("uid") or str(row.get("title") or "").casefold(),
                row.get("start") or "", tuple(sorted((k, str(v)) for k, v in changed.items())))
    if list_name == "reminders_set":
        return (row.get("tool"), str(row.get("name") or "").casefold(), row.get("when") or "")
    if list_name == "horizon_items":
        return (row.get("tool"), str(row.get("title") or "").casefold(), row.get("date") or "")
    return ("coordination", str(row.get("text") or "").casefold())


def record_run(agent_rec, output: str, user_turn: bool) -> dict | None:
    """Append this Logistics run's actions (and, on a real user turn, its coordination
    opportunities) to today's `logistics.recorded_by_code`. Returns what was written, or None
    when there was nothing new. Never raises."""
    try:
        new = actions_from(agent_rec)
        new["coordination_opportunities"] = coordination_from(output) if user_turn else []
        if not any(new.values()):
            return None
        from tools.logger import read_log, write_log
        stamp = datetime.now().isoformat(timespec="seconds")
        with _WRITE_LOCK:
            day = read_log() or {}
            stored = ((day.get("logistics") or {}) if isinstance(day.get("logistics"), dict)
                      else {}).get(SUBKEY)
            stored = stored if isinstance(stored, dict) else {}
            merged: dict[str, list] = {}
            added = 0
            for name in LISTS:
                rows = [r for r in (stored.get(name) or []) if isinstance(r, dict)]
                keys = {_key(name, r) for r in rows}
                for row in new.get(name) or []:
                    k = _key(name, row)
                    if k in keys:
                        continue
                    keys.add(k)
                    rows.append({**row, "at": stamp})
                    added += 1
                if rows:
                    merged[name] = rows
            if not added:
                return None
            write_log({"logistics": {SUBKEY: merged}})
        return merged
    except Exception as exc:  # noqa: BLE001 — bookkeeping must never fail the run
        logger.warning(f"[logistics_log] run not recorded: {exc}")
        return None


# --- M14: [VERIFY] events re-checked when Logistics reads the calendar -----------------------

MAX_REVERIFY = 2
REVERIFY_NOTE = ("Code re-ran the conflict check for the events below, which were saved while "
                 "the check was down ([VERIFY]); each result is under its uid. Nothing on the "
                 "calendar was changed. If an event is clear, retitle it without [VERIFY] with "
                 "update_calendar_event; if it shows a conflict, judge it like any other.")


def _naive_local(value: str, now: datetime) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(now.tzinfo) if now.tzinfo else dt.astimezone()
        dt = dt.replace(tzinfo=None)
    return dt


def _next_instance(r: dict, now: datetime) -> dict | None:
    """For a repeating event (`occurs_in_range`, tools/caldav.py), the row moved to its next
    occurrence that has not ended — the series' own `start` is when it BEGAN (last month, say),
    which is neither the past test nor the window to check. None when every occurrence in the
    range is over. A one-off row comes back as it is (review of 1c6f39d, item 4)."""
    occs = r.get("occurs_in_range")
    if not isinstance(occs, list):
        return r
    now_naive = now.replace(tzinfo=None)
    s0, e0 = _naive_local(r.get("start") or "", now), _naive_local(r.get("end") or "", now)
    duration = (e0 - s0) if s0 and e0 and e0 > s0 else timedelta(0)
    for occ in sorted(str(o) for o in occs):
        when = _naive_local(occ, now)
        if when is None:
            continue
        if when + duration > now_naive or (not duration and when >= now_naive):
            return {**r, "start": when.isoformat(), "end": (when + duration).isoformat()}
    return None


def _now() -> datetime:
    from tools.ambient import _now_local
    return _now_local()


def read_calendar_reverified(start_date: str, end_date: str) -> dict:
    """`read_calendar`'s exact result from one fetch, plus `reverify` for up to two unverified
    future events in it. Read-only throughout (4-7 = no)."""
    from tools.caldav import read_calendar_rows
    result, rows = read_calendar_rows(start_date, end_date)
    try:
        if not isinstance(result, dict) or "events" not in result:
            return result
        now = _now()
        now_naive = now.replace(tzinfo=None)
        pending = []
        for r in rows:
            if str(r.get("conflict_check_status") or "").upper() != "FAILED":
                continue
            r = _next_instance(r, now)
            if r is None:
                continue
            end = _naive_local(r.get("end") or r.get("start") or "", now)
            if end is None or end <= now_naive:
                continue
            pending.append(r)
        pending.sort(key=lambda r: str(r.get("start") or ""))
        # One per event: a recurring series' occurrences share a uid, and two occurrences of one
        # event must not use up both slots (review of 56cce4f, item 6).
        by_uid, unique = set(), []
        for r in pending:
            uid = str(r.get("uid") or "")
            if uid and uid in by_uid:
                continue
            by_uid.add(uid)
            unique.append(r)
        pending = unique[:MAX_REVERIFY]
        if not pending:
            return result
        from core.trace import get_trace
        from tools.scheduling import check_calendar_conflicts
        trace = get_trace()
        cache: dict = getattr(trace, "reverified", None) if trace is not None else None
        if cache is None:
            cache = {}
        out = []
        with _reverify_lock():
            for r in pending:
                uid = str(r.get("uid") or "")
                ckey = (uid, str(r.get("start") or ""))
                if uid and ckey in cache:
                    check = cache[ckey]
                else:
                    check = check_calendar_conflicts(
                        str(r.get("start") or ""), str(r.get("end") or ""),
                        str(r.get("title") or ""), location=str(r.get("location") or ""),
                        exclude_uid=uid)
                    if uid:
                        cache[ckey] = check
                out.append({"uid": uid, "start": r.get("start"), "end": r.get("end"),
                            "reverify": check})
        result = dict(result)
        result["reverify"] = out
        result["reverify_note"] = REVERIFY_NOTE
        return result
    except Exception as exc:  # noqa: BLE001 — the read itself must still come back
        logger.warning(f"[logistics_log] [VERIFY] re-check skipped: {exc}")
        return result


def is_plain_read_calendar(fn) -> bool:
    """Only the real `tools.caldav.read_calendar` handler is swapped for the re-checking read —
    a stubbed or wrapped handler is called as it is."""
    try:
        from tools import caldav
        return fn is caldav.read_calendar
    except Exception:  # noqa: BLE001
        return False
