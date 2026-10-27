"""
tools/day_plan.py — the day planner: a plan for the user's day that code keeps current, so the
Synthesizer can say what to do now and next instead of re-deriving it every turn.

WHY THIS EXISTS
---------------
Mike, 2026-10-24: "Metatron's primary mission via Synth is telling the user what to do at any
given moment." Until this, nothing held a plan: the morning brief proposed a sequence that lived
only in that one reply, and the Synthesizer could not even see the calendar. Plan, decisions and
the Fable review (twelve findings, all closed): archive/plans/day_planner_plan_2026-10-24.md.

THREE OWNERS, NO COPIES
-----------------------
The task ledger (tools/obligations.py) owns what must be done and whether it was. The calendar
owns commitments. This module owns WHEN — and only that. A plan block carries a ref (a ledger
occurrence id, a calendar uid, or a generated id like `meal:lunch`) and a time; its status is read
from the ledger when the plan is rendered, never stored. The plan keeps, per ref, an opaque
digest and the score it was placed with — enough for the gate to see *what* changed (review
R1-3), and nothing that could be read back as task state or re-raise a closed task.

WHAT CODE DOES, AND WHAT A MODEL DOES
-------------------------------------
"Code does as much as possible" (Mike, Q11). Code builds the skeleton (calendar events, travel,
meals, wind-down, protected time), scores the tasks, fills the free time, validates every plan,
repairs it as the day moves, and derives the nudge and check suggestions. A model (the
`day_planner` agent, Stage B) only refines the fill on a reshuffle — and its output is validated
by the same code; any failure keeps the code plan.

THE GATE
--------
Every read recomputes the digests and classifies the difference against the LIVE ledger: nothing
changed → the stored plan; timing moved or a task was done → a code repair; the day's contents or
what matters changed → a reshuffle (code now; model-refined once `reshuffle_model` is on, off the
reply path).

WHERE A NETWORK CALL MAY RUN (review R1-8, V1-N1)
-------------------------------------------------
1. A background calendar refresh, single-flight, started by any read that finds the snapshot
   stale — never awaited.
2. A synchronous fetch, boxed at 3 s, only after Metatron itself wrote the calendar this turn.
3. Nowhere else. A reply or a poll never waits on a CalDAV REPORT or a route lookup.

Every thread this module starts binds the persona first (`_spawn_bound`, review V2-N1).

Files: data/personas/{p}/day_plan/ — plan_YYYY-MM-DD.json, state.json, log.jsonl,
travel_cache.json. Written by code only, 0600, under an fcntl lock held for file I/O only.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import logging
import os
import re
import threading
import time as _time
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from pathlib import Path

from core.persona import persona_data_dir, persona_scope, resolve_persona

logger = logging.getLogger(__name__)

_VERSION = 1


# --- config, clock ---------------------------------------------------------------------------

def _cfg():
    from tools import day_plan_config as C
    return C


def _flag(name: str) -> bool:
    try:
        return _cfg().flag(name)
    except Exception:  # noqa: BLE001
        return False


def _limit(name: str):
    return _cfg().limit(name)


def _O():
    import tools.obligations as O
    return O


def _now() -> datetime:
    """The ledger's clock — persona-local, naive. One clock for the ledger and the plan, so a
    test that moves one moves both."""
    return _O()._now()


def _today() -> date:
    return _O()._today()


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M")


def _dt(value) -> datetime | None:
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


# --- files and the lock ----------------------------------------------------------------------

def _dir(persona: str | None = None) -> Path:
    return persona_data_dir(persona) / "day_plan"


def _plan_path(day: date, persona: str | None = None) -> Path:
    return _dir(persona) / f"plan_{day.isoformat()}.json"


def _state_path(persona: str | None = None) -> Path:
    return _dir(persona) / "state.json"


def _log_path(persona: str | None = None) -> Path:
    return _dir(persona) / "log.jsonl"


def _travel_path(persona: str | None = None) -> Path:
    return _dir(persona) / "travel_cache.json"


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp{os.getpid()}.{threading.get_ident()}")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1, default=str))
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, path)


@contextmanager
def _locked(persona: str | None = None, wait_ms: int | None = None):
    """The plan lock, across processes (the server repairs at turn time, the scheduler ticks).
    Held for file I/O only — never across a network or model call (review V1-N3).

    `wait_ms=None` blocks; otherwise it tries for that long and yields False if it could not get
    the lock, so the reply path can render the stored plan and write nothing."""
    d = _dir(persona)
    d.mkdir(parents=True, exist_ok=True)
    fh = open(d / ".lock", "a+")
    got = False
    try:
        if wait_ms is None:
            fcntl.flock(fh, fcntl.LOCK_EX)
            got = True
        else:
            deadline = _time.monotonic() + wait_ms / 1000.0
            while True:
                try:
                    fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    got = True
                    break
                except OSError:
                    if _time.monotonic() >= deadline:
                        break
                    _time.sleep(0.01)
        yield got
    finally:
        if got:
            try:
                fcntl.flock(fh, fcntl.LOCK_UN)
            except OSError:
                pass
        fh.close()


def _load_state(persona: str | None = None) -> dict:
    s = _read_json(_state_path(persona), {})
    return s if isinstance(s, dict) else {}


def _log(event: str, persona: str | None = None, **fields) -> None:
    """One content-free row: ids, counts, timings — never task words."""
    row = {"at": _now().isoformat(timespec="seconds"), "event": event, **fields}
    try:
        path = _log_path(persona)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as fh:
            fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        os.chmod(path, 0o600)
    except Exception:  # noqa: BLE001 — the log never breaks a plan
        pass


# --- threads ---------------------------------------------------------------------------------

def _spawn_bound(fn, *args, name: str = "worker") -> threading.Thread:
    """Start `fn(*args)` on a daemon thread bound to the CALLER's persona (review V2-N1).

    Identity is thread-local and fail-closed (core/persona.py), so it is resolved here, on the
    spawning thread, and bound inside the worker as its first act. A failure is logged to the
    plan log, not only to the server's — a dead refresh must be visible where the plan is."""
    persona = resolve_persona(None)

    def run():
        with persona_scope(persona):
            try:
                fn(*args)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"[day_plan] {name} failed: {exc}")
                _log(f"{name}_failed", error=type(exc).__name__)

    t = threading.Thread(target=run, name=f"day_plan_{name}", daemon=True)
    t.start()
    return t


# --- the calendar snapshot -------------------------------------------------------------------

_REFRESHING: set[str] = set()
_REFRESH_LOCK = threading.Lock()

# A meeting link is not a place anyone travels to.
_ONLINE_RE = re.compile(r"https?://|zoom|teams\.microsoft|meet\.google|webex|whereby|"
                        r"microsoft teams|google meet|\bonline\b|\bvirtual\b", re.IGNORECASE)
# "Lunch with Victoria" is an appointment with someone, not the user's own lunch break (R2-7).
_WITH_RE = re.compile(r"\bwith\s+\S", re.IGNORECASE)


def _ignore_titles() -> list[str]:
    try:
        import yaml
        path = Path(__file__).resolve().parent.parent / "config" / "modules" / \
            "calendar_reconcile.yaml"
        data = yaml.safe_load(path.read_text()) or {}
        return [str(x).strip().lower() for x in data.get("ignore_titles") or [] if str(x).strip()]
    except Exception:  # noqa: BLE001
        return ["lunch", "commute", "focus time", "break", "travel"]


def _normalise(events: list[dict]) -> list[dict]:
    """Calendar rows → one instance per occurrence: local-naive start/end, all-day flag, whether
    it is the user's own block (a calendar "Lunch" or "Focus time") and whether it is somewhere
    to travel to. Cancelled events are dropped."""
    from tools.scheduling import _instances, _is_all_day, _parse_dt
    own_words = _ignore_titles()
    out = []
    for ev in events or []:
        if str(ev.get("status") or "").upper() == "CANCELLED":
            continue
        for inst in _instances(ev):
            start, end = _parse_dt(inst.get("start", "")), _parse_dt(inst.get("end", ""))
            if start is None:
                continue
            if end is None or end <= start:
                end = start + timedelta(minutes=30)
            title = str(inst.get("title") or "").strip()
            low = title.lower()
            all_day = _is_all_day(inst) or (start.time() == time(0, 0)
                                            and end - start >= timedelta(hours=23))
            # iCalendar TEXT escapes commas and semicolons ("The Ledger Building\, West India
            # Quay"); a route lookup wants the address as written.
            loc = re.sub(r"\\([,;\\])", r"\1", str(inst.get("location") or "")).replace("\\n", ", ").strip()
            place = loc if loc and not _ONLINE_RE.search(loc) else ""
            # The user's own block only on its plain title — never one with a place or another
            # person in it (R2-7: "Lunch with Victoria" was read as a lunch break and got no travel).
            own = None if (place or _WITH_RE.search(title)) else next(
                (w for w in own_words if w and (low == w or low.startswith(w + " ")
                                                or low.startswith(w + " — "))), None)
            out.append({
                "uid": str(inst.get("uid") or ""),
                "key": f"{inst.get('uid')}@{start.isoformat()}",
                "title": title, "start": start.isoformat(), "end": end.isoformat(),
                "location": place, "all_day": bool(all_day), "own": own,
                "read_only": bool(inst.get("read_only")),
                # Which calendars it is on, by collection id and by name (R2-5, review N1).
                "calendars": [str(c) for c in inst.get("calendars") or []],
                "calendar_ids": [str(c) for c in inst.get("calendar_ids") or []],
            })
    out.sort(key=lambda e: e["start"])
    return out


def _fetch(day: date, persona: str | None) -> dict:
    """One CalDAV read of today and tomorrow (and the day after, for an evening draft that runs
    past midnight), every calendar the account exposes — read-only. Plan § 5.1: the planner is
    the one unattended reader whose whole job is the real day, so it widens deliberately."""
    from tools.caldav import _query_events
    raw = _query_events(day.isoformat(), (day + timedelta(days=2)).isoformat(),
                        persona=persona, calendars="all")
    if not isinstance(raw, dict) or raw.get("error"):
        return {"error": str((raw or {}).get("error") or "no response")[:200]}
    # Whether every calendar was looked for: only then can one be "new since setup" (review N1).
    return {"events": _normalise(raw.get("events") or []),
            "discovery": str(raw.get("discovery") or "ok")[:80]}


def refresh_snapshot(persona: str | None = None) -> dict:
    """Fetch and store the snapshot. Runs off the reply path (a background thread or a tick)."""
    persona = resolve_persona(persona)
    day = _today()
    t0 = _time.monotonic()
    got = _fetch(day, persona)
    with _locked(persona):
        state = _load_state(persona)
        snap = state.get("snapshot") or {}
        if got.get("error"):
            snap.update(error=got["error"], failed_at=_now().isoformat(timespec="seconds"))
        else:
            snap = {"fetched_at": _now().isoformat(timespec="seconds"), "day": day.isoformat(),
                    "events": got["events"], "discovery": got.get("discovery", "ok")}
        state["snapshot"] = snap
        state.pop("calendar_dirty", None)
        _write_json(_state_path(persona), state)
    _log("snapshot", persona, ok=not got.get("error"),
         events=len(got.get("events") or []), ms=int((_time.monotonic() - t0) * 1000))
    return got


def _snapshot_age_minutes(state: dict) -> float | None:
    at = _dt((state.get("snapshot") or {}).get("fetched_at"))
    if at is None:
        return None
    return (_now() - at).total_seconds() / 60.0


def _refresh_in_background(persona: str) -> bool:
    """Single-flight per process: a second stale read while one refresh runs starts nothing.
    Afterwards the plan is rebuilt so the next read finds it current."""
    with _REFRESH_LOCK:
        if persona in _REFRESHING:
            return False
        _REFRESHING.add(persona)

    def work():
        try:
            refresh_snapshot(persona)
            current(persona, reason="calendar refreshed")
        finally:
            with _REFRESH_LOCK:
                _REFRESHING.discard(persona)

    try:
        with persona_scope(persona):
            _spawn_bound(work, name="refresh")
    except Exception:  # noqa: BLE001
        with _REFRESH_LOCK:
            _REFRESHING.discard(persona)
        return False
    return True


def note_calendar_write(persona: str | None = None) -> None:
    """Called by tools/caldav.py after Metatron wrote, moved or deleted an event. Marks this turn
    (so the reply's plan re-fetches inside the 3 s box) and the state (so the next tick does)."""
    try:
        from tools.turn_context import current as _turn
        turn = _turn()
        if turn is not None:
            turn["calendar_written"] = True
    except Exception:  # noqa: BLE001
        pass
    try:
        p = resolve_persona(persona)
        with _locked(p, wait_ms=200) as got:
            if got:
                state = _load_state(p)
                state["calendar_dirty"] = True
                _write_json(_state_path(p), state)
    except Exception:  # noqa: BLE001
        pass


def _calendar_written_this_turn() -> bool:
    try:
        from tools.turn_context import current as _turn
        turn = _turn()
        return bool(turn and turn.get("calendar_written"))
    except Exception:  # noqa: BLE001
        return False


def _boxed_fetch(persona: str) -> bool:
    """The one synchronous fetch (rule 2): after a calendar write this turn, boxed. On timeout
    the background refresh is left running and the stale snapshot is used."""
    done = threading.Event()

    def work():
        try:
            refresh_snapshot(persona)
        finally:
            done.set()

    with persona_scope(persona):
        _spawn_bound(work, name="boxed_fetch")
    return done.wait(timeout=float(_limit("calendar_fetch_timeout_seconds") or 3))


# --- location and travel ---------------------------------------------------------------------

def _zone_coords(name: str, persona: str | None) -> str | None:
    try:
        from tools.location import load_zones
        for z in load_zones(persona):
            if str(z.get("name") or "").strip().lower() == name.lower():
                return f"{float(z['lat'])},{float(z['lon'])}"
    except Exception:  # noqa: BLE001
        pass
    return None


def _local_stamp(value) -> datetime | None:
    """A transitions-log stamp as local-naive. Client stamps arrive as UTC 'Z' strings stored
    verbatim, server stamps as local-naive (tools/location.py) — both are normalised here."""
    dt = _dt(str(value or "").replace("Z", "+00:00"))
    if dt is None:
        return None
    if dt.tzinfo is not None:
        try:
            from zoneinfo import ZoneInfo
            from tools.ambient import _get_timezone
            tz = _get_timezone()
            dt = dt.astimezone(ZoneInfo(tz)) if tz else dt.astimezone()
        except Exception:  # noqa: BLE001
            dt = dt.astimezone()
        dt = dt.replace(tzinfo=None)
    return dt


def _start_point(persona: str | None, day: date) -> tuple[str | None, str]:
    """Where the day starts from: the zone the user is in if they arrived there today, else
    home, else nowhere known."""
    try:
        from tools.location import current_zone
        cz = current_zone(persona) or {}
        entered = _local_stamp(cz.get("entered_at"))
        if cz.get("zone") and cz["zone"] != "away" and entered and entered.date() >= day:
            coords = _zone_coords(cz["zone"], persona)
            if coords:
                return coords, cz["zone"]
    except Exception:  # noqa: BLE001
        pass
    home = _zone_coords("home", persona)
    return (home, "home") if home else (None, "")


def _travel_minutes(origin: str, dest: str, mode: str, arrive: datetime,
                    persona: str | None, allow_lookup: bool) -> tuple[int, bool]:
    """(minutes, estimated). Cached per (origin, destination, mode, date, hour) and capped per
    day — Google Routes is billed per request and no spend meter sees it (plan § 12). A lookup
    happens only off the reply path (`allow_lookup`)."""
    assumed = int(_limit("travel_assumed_minutes") or 30)
    key = f"{origin}|{dest}|{mode}|{arrive.date().isoformat()}|{arrive.hour:02d}"
    cache = _read_json(_travel_path(persona), {})
    hit = (cache.get("entries") or {}).get(key)
    if hit is not None:
        return int(hit["minutes"]), bool(hit.get("estimated"))
    if not allow_lookup:
        return assumed, True
    day_key = _today().isoformat()
    counts = cache.get("counts") or {}
    if int(counts.get(day_key, 0)) >= int(_limit("travel_lookups_per_day") or 60):
        return assumed, True
    from tools.routing import get_travel_time
    route = get_travel_time(origin, dest, mode=mode, arrive_by=arrive.strftime("%Y-%m-%dT%H:%M"))
    counts[day_key] = int(counts.get(day_key, 0)) + 1
    journeys = (route or {}).get("journeys") or []
    minutes, estimated = (int(journeys[0]["duration_minutes"]), False) if journeys else (assumed, True)
    entries = {k: v for k, v in (cache.get("entries") or {}).items()
               if k.split("|")[3] >= day_key}      # entries expire at the day boundary
    entries[key] = {"minutes": minutes, "estimated": estimated}
    try:
        with _locked(persona):
            _write_json(_travel_path(persona), {"entries": entries,
                                                "counts": {day_key: counts[day_key]}})
    except Exception:  # noqa: BLE001
        pass
    _log("travel_lookup", persona, ok=not estimated)
    return minutes, estimated


# --- candidates and the score (plan § 5.2) ---------------------------------------------------

def _digest(*parts) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:12]


def _score(t: dict, v: dict, today: date, goals: dict, w: dict) -> int:
    O = _O()
    pri = t.get("priority")
    if pri in (w.get("priority") or {}):
        base = int(w["priority"][pri])
    else:
        g = goals.get(str(t.get("goal_id") or ""))
        base = int((w.get("goal") or {}).get(
            "essential" if g and g.get("essential") is True else ("linked" if g else "none"), 15))
    dyn = 0
    kind, state = t.get("kind"), v.get("state")
    if kind == "deadline":
        due = O._d(t.get("due"))
        vital = t.get("stakes") != "missable"
        table = w.get("vital" if vital else "missable") or {}
        if state == "lapsed":
            dyn += int(table.get("lapsed", 0))
        elif due and due < today:
            dyn += int(table.get("overdue", 0))
        elif due and due == today:
            dyn += int(table.get("due_today", 0))
        elif due and due == today + timedelta(days=1):
            dyn += int(table.get("due_tomorrow", 0))
        elif due:
            dyn += int(table.get("in_lead", 0))
    elif kind == "habit" and O._month_window(t):
        # A monthly habit with days of the month is a recurring deadline (review F4): overdue
        # after its last day, due on it.
        table = w.get("vital" if t.get("stakes") != "missable" else "missable") or {}
        if state == "overdue":
            dyn += int(table.get("overdue", 0))
        elif state == "due_today" and v.get("sort", (9,))[0] == 1:
            dyn += int(table.get("due_today", 0))
        else:
            dyn += int((w.get("habit") or {}).get("planned_day", 0))
    elif kind == "habit":
        hw = w.get("habit") or {}
        q = v.get("quota") or {}
        if (t.get("every") or "day") == "day":
            dyn += int(hw.get("daily", 0))
        if q.get("planned"):
            dyn += int(hw.get("planned_day", 0))
        if q.get("at_risk"):
            dyn += int(hw.get("at_risk", 0))
    elif kind == "interval" and state in ("due_today", "overdue"):
        dyn += int(w.get("interval_due", 0))
    if O._MEDICATION_RE.search(f"{t.get('what', '')} {t.get('note', '')}"):
        dyn += int(w.get("medication", 0))
    return base + dyn


def _candidates(today: date, persona: str | None) -> list[dict]:
    """What may be placed today: what the user's Today list shows — overdue, due today, today's
    habits, a weekly or monthly quota on a planned day or its last chance — plus lapsed one-offs
    (placed low). Never `waiting` — someone else's move.

    The Today list's own rule, `_on_todays_list`, and not the head layer's wider Now (round 2,
    R2-3): on 10-25 the two-day lead put two tasks due Monday on Sunday's plan, and undated ones
    beside them. Mike: "these are FOR Monday … Metatron should focus attention on the present."
    One definition of today for the list and the plan, so they cannot disagree."""
    from tools.day_shape import activity_of, shape_for
    O = _O()
    goals = O._goal_index()
    w = _cfg().score_weights()
    default_minutes = int(_limit("default_task_minutes") or 30)
    shape = shape_for(today, persona)
    out = []
    for raw in O._load(persona):
        t = O._norm(raw)
        if t.get("status") != "open" or t.get("kind") == "waiting":
            continue
        v = O._view(t, today)
        # "in_window": any day up to its date (Mike, 2026-10-27) — a candidate every day of its
        # window, placed only where there is room, and a must-do only on its last day.
        if not ((v.get("actionable") and O._on_todays_list(t, v))
                or v.get("state") in ("lapsed", "in_window")):
            continue
        activity, attrs = activity_of(t, shape)
        target = O._habit_target(t) if t.get("kind") == "habit" else 1
        copies = 1
        if t.get("kind") == "habit" and (t.get("every") or "day") == "day":
            occ = (t.get("occurrences") or {}).get(O._period("day", today)[0]) or {}
            copies = max(1, target - int(occ.get("done") or 0))
        g = goals.get(str(t.get("goal_id") or "")) or {}
        score = _score(t, v, today, goals, w)
        out.append({
            "ref": v["occ"], "task_id": t["id"], "what": t["what"], "kind": t.get("kind"),
            "domain": str(t.get("domain") or "").lower(), "state": v.get("state"),
            "minutes": int(t.get("minutes") or default_minutes),
            "length_known": bool(t.get("minutes")),
            "essential": O.is_essential(t, goals) and v.get("state") != "in_window",
            "stakes": t.get("stakes"), "after": t.get("after"),
            "vital": ((t.get("kind") == "deadline" or bool(O._month_window(t)))
                      and t.get("stakes") != "missable"),
            "due": t.get("due"), "zone": t.get("zone"), "copies": copies,
            # What kind of activity it is, and what that needs (plan § 18.3): where it may go.
            "activity": activity, "device": bool(attrs.get("device")),
            "heavy": attrs.get("concentration") == "heavy", "solo": bool(attrs.get("solo")),
            "attrs": attrs,
            # A daily habit done more than once a day (a medicine twice a day): each dose is its
            # own block, and `copies` is how many are still unrecorded (review S-2).
            "multi": t.get("kind") == "habit" and (t.get("every") or "day") == "day" and target > 1,
            "goal": {k: g.get(k) for k in ("title", "shareable_what") if g.get(k)},
            "score": score,
            "digest": _digest(t.get("status"), v.get("state"), v.get("text"), t.get("due"),
                              t.get("minutes"), t.get("priority"), t.get("stakes"),
                              t.get("goal_id"), t.get("zone"), activity),
        })
    out.sort(key=lambda c: (-c["score"], str(c.get("due") or "9999"), c["minutes"]))
    return out


# --- the timeline ----------------------------------------------------------------------------
# Placement works on a 5-minute grid from the plan's start to bedtime: simple to reason about,
# exact enough for a day, and it makes "is this run of time free and allowed?" one list scan.

_SLOT = 5
_TASKLIKE = ("task", "break")
_HARD = ("event", "own", "travel", "meal", "task", "break")


def _round_up(dt: datetime) -> datetime:
    dt = dt.replace(second=0, microsecond=0)
    extra = (-dt.minute) % _SLOT
    return dt + timedelta(minutes=extra)


class _Grid:
    def __init__(self, start: datetime, end: datetime):
        self.start = start
        self.n = max(0, int((end - start).total_seconds() // 60) // _SLOT)
        self.busy = [False] * self.n          # hard blocks: events, travel, meals, tasks
        self.task_gap = [False] * self.n      # transitions/breaks: closed to tasks only
        self.task_run = [False] * self.n      # slots holding a task (for the break rule)

    def idx(self, dt: datetime) -> int:
        return int((dt - self.start).total_seconds() // 60) // _SLOT

    def at(self, i: int) -> datetime:
        return self.start + timedelta(minutes=i * _SLOT)

    def mark(self, s: datetime, e: datetime, arr: list) -> None:
        a, b = max(0, self.idx(s)), min(self.n, -(-int((e - self.start).total_seconds() // 60) // _SLOT))
        for i in range(a, b):
            arr[i] = True

    def mask(self, windows: list[tuple[datetime, datetime]]) -> list[bool]:
        m = [False] * self.n
        for s, e in windows:
            self.mark(s, e, m)
        return m


def _windows_of(blocks: list[dict], kind: str) -> list[tuple[datetime, datetime]]:
    return [(_dt(b["start"]), _dt(b["end"])) for b in blocks if b["kind"] == kind]


# --- what an event means for the user (plan § 18.3, R2-5) ------------------------------------

_EVENT_ANSWERS = ("there", "needs_me", "someone_else", "noise")
_MEAL_WORDS = {"breakfast": ("breakfast", "brunch"), "lunch": ("lunch", "brunch"),
               "dinner": ("dinner", "supper")}


def _answers_path(persona: str | None = None) -> Path:
    return _dir(persona) / "event_answers.json"


def _event_answers(persona: str | None = None) -> dict:
    """The user's answers about events: `occurrences` keyed uid@start and `series` keyed uid —
    two maps, because every occurrence of a series shares its uid (review F1). Read in round 2;
    written by `answer_event` once Stage B grants it."""
    data = _read_json(_answers_path(persona), {})
    return data if isinstance(data, dict) else {}


def _discovery_ok(persona: str | None = None) -> bool:
    snap = _load_state(persona).get("snapshot") or {}
    return str(snap.get("discovery") or "ok") == "ok"


def _rule_matches(rule: dict, title: str) -> bool:
    low = title.lower()
    return any(re.search(r"\b" + re.escape(str(w).lower()) + r"\b", low)
               for w in rule.get("match") or [])


def _calendar_role(e: dict, shape: dict, discovery_ok: bool) -> str:
    """mine / family / feed / new. The calendar Metatron writes is always the user's; with no
    roster yet, every calendar is (D1). A calendar the roster has never seen is new — but only on
    a poll whose discovery succeeded, or one PROPFIND hiccup would blank the day (review N1).
    An event on several calendars takes its most-owned role."""
    if not e.get("read_only", False):
        return "mine"
    roster = shape.get("calendars") or {}
    if not roster:
        return "mine"
    ids = e.get("calendar_ids") or []
    roles = [roster[i]["role"] for i in ids if i in roster]
    if not roles:
        return "new" if (ids and discovery_ok) else "mine"
    return next(r for r in ("mine", "family", "feed") if r in roles)


def _triage(e: dict, shape: dict, answers: dict, discovery_ok: bool) -> dict:
    """there / needs_me / someone_else / noise — or `ask` (not known yet) or `new` (its calendar
    is new). Most specific first (review F3): the user's answer about this occurrence, then about
    the series, then a standing rule, then the calendar's role."""
    for store, key in (("occurrences", e["key"]), ("series", e["uid"])):
        a = (answers.get(store) or {}).get(key)
        if isinstance(a, dict) and a.get("answer") in _EVENT_ANSWERS:
            return {"answer": a["answer"], "duty": a.get("duty"), "load": a.get("load") or "full",
                    "source": "answer"}
    for rule in shape.get("event_rules") or []:
        if _rule_matches(rule, e["title"]):
            return {"answer": rule["answer"], "duty": rule.get("duty"),
                    "load": rule.get("load") or "full", "source": "rule"}
    role = _calendar_role(e, shape, discovery_ok)
    return {"answer": {"mine": "there", "family": "ask", "feed": "noise", "new": "new"}[role],
            "load": "full", "source": "calendar"}


def _is_protected(b: dict) -> bool:
    """A region that keeps out what does not fit: a protected window, an unanswered family event
    held for family-compatible tasks (F6), a duty that is family time (childcare)."""
    return b["kind"] in ("protected", "hold") or (b["kind"] == "duty" and bool(b.get("activities")))


def _is_hard(b: dict) -> bool:
    """A block that closes its time to tasks and meals."""
    k = b["kind"]
    if k in ("event", "own"):
        return not b.get("partial")
    if k == "duty":
        return not b.get("activities")
    return k in ("travel", "meal", "task", "break", "routine")


def _clip(s: datetime, e: datetime, spans: list[tuple[datetime, datetime]]) -> list[tuple]:
    out = []
    for a, b in spans:
        lo, hi = max(s, a), min(e, b)
        if lo < hi:
            out.append((lo, hi))
    return out


# --- the skeleton (plan § 5.3, § 18) ---------------------------------------------------------

def _skeleton(day: date, shape: dict, events: list[dict], persona: str | None,
              allow_lookup: bool, plan_start: datetime | None = None,
              answers: dict | None = None, discovery_ok: bool = True
              ) -> tuple[list[dict], list[str], dict]:
    """Events as their triage says, routines, travel, wind-down, protected windows and meals for
    ledger day `day`. Returns (blocks, notes, extra) — extra carries the event keys deliberately
    not shown (`hidden`: noise, a calendar's own focus block) and held back (`held_back`, by
    calendar: a calendar new since setup), so the validator can account for every event, and any
    windows the calendar itself supplied. A meal whose window has closed by `plan_start` is not
    placed — the plan does not claim a lunch nobody recorded (Q8: no assumptions)."""
    from tools.day_shape import OWN_TIME, anchor, window_for
    wake_dt, bed_dt = window_for(day, shape=shape)
    blocks: list[dict] = []
    notes: list[str] = []
    extra: dict = {"hidden": [], "held_back": {}, "windows": []}
    covered: dict[str, datetime] = {}         # meal → when what stands in for it ends
    answers = answers or {}
    family_allows = (shape.get("window_allows") or {}).get("family")
    duties = shape.get("duties") or {}

    def span(a: time, b: time) -> tuple[datetime, datetime]:
        s, e = anchor(day, a, shape["wake"]), anchor(day, b, shape["wake"])
        return s, (e if e > s else e + timedelta(days=1))

    children = [span(a, b) for a, b in shape.get("children_home") or []]

    for e in events:
        s, en = _dt(e["start"]), _dt(e["end"])
        if e.get("all_day") or s is None or en is None or en <= wake_dt or s >= bed_dt:
            continue
        own = e.get("own")
        if own == "focus time":
            extra["windows"].append({"activities": ["focus"], "start": s, "end": en,
                                     "strength": "preferred", "condition": None})
            extra["hidden"].append(e["key"])
            continue
        tri = _triage(e, shape, answers, discovery_ok)
        ans = tri["answer"]
        base = {"ref": e["uid"], "key": e["key"], "title": e["title"], "start": _iso(s),
                "end": _iso(en), "location": e.get("location") or "",
                "calendar": (e.get("calendars") or [""])[0], "triage": tri["source"]}
        if ans == "noise":
            extra["hidden"].append(e["key"])
            continue
        if ans == "new":
            extra["held_back"].setdefault(base["calendar"] or "a new calendar", []).append(e["key"])
            continue
        if ans == "someone_else":
            blocks.append({**base, "id": f"context:{e['key']}", "kind": "context"})
            continue
        if ans == "ask":
            # Not known yet whether it needs the user: its time is held for what may share family
            # time, so no screen work or heavy concentration lands on what may be childcare —
            # neither a false commitment nor false free time (review F6).
            blocks.append({**base, "id": f"hold:{e['key']}", "kind": "hold",
                           "activities": ["family"], "allows": family_allows})
            continue
        if ans == "needs_me":
            duty = str(tri.get("duty") or "needed").strip().lower()
            as_family = (duties.get(duty) or {}).get("as") == "family"
            spans = _clip(s, en, children) if (as_family and children) else [(s, en)]
            if not spans:
                blocks.append({**base, "id": f"context:{e['key']}", "kind": "context",
                               "note": f"no {duty} needed then"})
                continue
            for a, b in spans:
                blk = {**base, "id": f"duty:{e['key']}@{a:%H%M}", "kind": "duty", "duty": duty,
                       "start": _iso(a), "end": _iso(b)}
                if as_family:
                    blk.update(activities=["family"], allows=family_allows)
                blocks.append(blk)
            continue
        blk = {**base, "id": f"event:{e['key']}", "kind": "own" if own else "event"}
        if tri.get("load") == "partial":
            blk["partial"] = True
        blocks.append(blk)
        low = e["title"].lower()
        for meal, words in _MEAL_WORDS.items():
            if own == meal or any(w in low for w in words):
                covered[meal] = max(covered.get(meal, en), en)

    # Routines: a standing block on no calendar. Only something the user is at — a *there*
    # event or a duty — takes its place that day (review F7).
    for r in shape.get("routines") or []:
        s, en = span(r["start"], r["end"])
        if en <= wake_dt or s >= bed_dt:
            continue
        if any(b["kind"] in ("event", "own", "duty") and _dt(b["start"]) < en and s < _dt(b["end"])
               for b in blocks):
            continue
        rid = re.sub(r"[^a-z0-9]+", "-", r["what"].lower()).strip("-") or "routine"
        blocks.append({"id": f"routine:{rid}", "kind": "routine", "ref": f"routine:{rid}",
                       "key": f"routine:{rid}@{_iso(s)}", "title": r["what"], "start": _iso(s),
                       "end": _iso(en), "location": r.get("place") or ""})
        if r.get("covers"):
            covered[r["covers"]] = max(covered.get(r["covers"], en), en)

    # Travel: from wherever the user was last expected to be, to each located event or routine —
    # and home again after one when nothing located follows within two hours (plan § 5.3; Fable
    # diff review S-5: without the way back, a task could start the minute physio ended).
    origin, _name = _start_point(persona, day)
    home = _zone_coords("home", persona)
    prev = origin
    buf = int(shape["departure_buffer_minutes"])
    located = sorted((b for b in blocks if b["kind"] in ("event", "routine")
                      and (b.get("location") or "").strip()), key=lambda b: b["start"])
    for i, b in enumerate(located):
        loc = b["location"].strip()
        if prev and prev.strip().lower() != loc.lower():
            arrive = _dt(b["start"])
            mins, est = _travel_minutes(prev, loc, shape["travel_mode"], arrive, persona,
                                        allow_lookup)
            blocks.append({"id": f"travel:{b['key']}", "kind": "travel", "ref": b["ref"],
                           "for": b["id"], "title": f"travel to {b['title']}",
                           "start": _iso(arrive - timedelta(minutes=mins + buf)),
                           "end": _iso(arrive),
                           "travel": {"minutes": mins, "estimated": est,
                                      "mode": shape["travel_mode"], "buffer": buf}})
        elif not prev:
            notes.append(f"no known starting point for travel to {b['title']}")
        prev = loc
        nxt = located[i + 1] if i + 1 < len(located) else None
        if home and loc.lower() != home and (
                nxt is None or _dt(nxt["start"]) - _dt(b["end"]) >= timedelta(hours=2)):
            leave = _dt(b["end"])
            mins, est = _travel_minutes(loc, home, shape["travel_mode"],
                                        leave + timedelta(minutes=30), persona, allow_lookup)
            blocks.append({"id": f"travel_home:{b['key']}", "kind": "travel", "ref": b["ref"],
                           "for": b["id"], "title": f"travel home from {b['title']}",
                           "start": _iso(leave), "end": _iso(leave + timedelta(minutes=mins)),
                           "travel": {"minutes": mins, "estimated": est,
                                      "mode": shape["travel_mode"], "buffer": 0}})
            prev = home

    wd = int(shape["wind_down_minutes"])
    blocks.append({"id": "wind_down", "kind": "wind_down", "title": "wind down",
                   "start": _iso(bed_dt - timedelta(minutes=wd)), "end": _iso(bed_dt)})

    # Protected windows: kept clear of what does not fit there, not kept empty (ruling 10).
    for w in shape.get("windows") or []:
        if w["strength"] != "protected":
            continue
        s, en = span(w["start"], w["end"])
        name = w["activities"][0]
        blocks.append({"id": f"protected:{name}:{w['start'].strftime('%H%M')}", "kind": "protected",
                       "title": "the user's own time" if name == OWN_TIME else f"{name} time",
                       "start": _iso(s), "end": _iso(en), "activities": list(w["activities"]),
                       "allows": w.get("allows")})

    # Meals: at their stated time, sliding later within their range, else earlier; with no stated
    # time, in the largest free stretch around the middle of the window. A regular meal is never
    # dropped without a word (Mike, 10-25): with no gap it becomes a question at its time.
    grid = _Grid(wake_dt, bed_dt)
    for b in blocks:
        if _is_hard(b):
            grid.mark(_dt(b["start"]), _dt(b["end"]), grid.busy)
    # Where a meal lands inside an event that may itself be the meal — one not yet answered, or
    # one the user is only partly at (the playdate: "that should be asked of the user") — it asks.
    soft = [b for b in blocks if b["kind"] == "hold" or (b["kind"] == "event" and b.get("partial"))]
    meal_end = dict(covered)
    for m in shape["meals"]:
        name = m["name"]
        if name in covered:
            continue
        minutes = int(m["minutes"])
        if m.get("when"):
            first = meal_end.get(m["when"]["meal"])
            ends_by = datetime.combine(day, time.fromisoformat(m["when"]["ends_by"]))
            if first is None or first > ends_by:
                continue
        lo, hi = anchor(day, m["earliest"], shape["wake"]), anchor(day, m["latest"], shape["wake"])
        if hi <= lo:
            hi += timedelta(days=1)
        target = anchor(day, m["target"], shape["wake"]) if m.get("target") else None
        if plan_start is not None:
            if hi <= plan_start + timedelta(minutes=minutes):
                continue
            lo = max(lo, plan_start)
            if target is not None and target < plan_start:
                target = _round_up(plan_start)
        n = max(1, minutes // _SLOT)
        a, z = max(0, grid.idx(lo)), min(grid.n, grid.idx(hi))

        def free(i: int) -> bool:
            return a <= i and i + n <= z and not any(grid.busy[k] for k in range(i, i + n))

        start_i = None
        if target is not None:
            t_i = grid.idx(_round_up(target))
            start_i = next((i for i in list(range(t_i, z - n + 1)) + list(range(t_i - 1, a - 1, -1))
                            if free(i)), None)
        else:
            runs, i = [], a
            while i < z:
                if grid.busy[i]:
                    i += 1
                    continue
                j = i
                while j < z and not grid.busy[j]:
                    j += 1
                if j - i >= n:
                    runs.append((i, j))
                i = j
            if runs:
                i, j = max(runs, key=lambda r: r[1] - r[0])
                start_i = min(max(i, (a + z) // 2 - n // 2), j - n)
        if start_i is None:
            when = _round_up(target or lo + (hi - lo) / 2)
            cover = next((b for b in blocks if _is_hard(b) and b["kind"] != "travel"
                          and _dt(b["start"]) <= when < _dt(b["end"])), None)
            # Worded for any event: a picnic may be lunch, a GMAT session is not.
            why = (f"{cover['title']} covers it — eat during it, or when?" if cover
                   else f"no gap between {lo:%H:%M} and {hi:%H:%M} — when?")
            blocks.append({"id": f"ask:meal:{name}", "kind": "ask", "title": name, "ask": why,
                           "start": _iso(when), "end": _iso(when + timedelta(minutes=minutes))})
            continue
        s = grid.at(start_i)
        e = s + timedelta(minutes=minutes)
        grid.mark(s, e, grid.busy)
        blk = {"id": f"meal:{name}", "kind": "meal", "title": name, "start": _iso(s), "end": _iso(e)}
        # The event the meal sits most inside — the playdate spanning lunch, not the vote that
        # ends a quarter of an hour into it.
        under = max((b for b in soft if _dt(b["start"]) < e and s < _dt(b["end"])),
                    key=lambda b: min(e, _dt(b["end"])) - max(s, _dt(b["start"])), default=None)
        if under:
            blk["ask"] = f"during {under['title']} — is that also {name}?"
            blk["under"] = under["id"]      # the panel shows the ask on that event's row
        blocks.append(blk)
        meal_end[name] = e

    for cal, keys in extra["held_back"].items():
        notes.insert(0, f"New calendar “{cal}” ({len(keys)} event{'s' if len(keys) != 1 else ''} "
                        f"today) — not planned until the user says what it is: theirs, family, "
                        f"or a feed")
    return blocks, notes, extra


# --- the fill (plan § 5.4, § 18) -------------------------------------------------------------

def _may_protect(c: dict) -> bool:
    """The life-quality rule: a missable item never takes the user's protected time; an essential
    one may, when nothing else fits — and the block says so."""
    return bool(c.get("essential"))


def _fill(cands: list[dict], blocks: list[dict], shape: dict, plan_start: datetime,
          bed_dt: datetime, extra_windows: list[dict] | None, keep: list[dict], day: date
          ) -> tuple[list[dict], list[dict]]:
    """Each task into its kind of time (plan § 18.3): a protected region admits only what its
    filter matches; a strong window is the only place its activity goes; a preferred one is tried
    first; time belonging to another activity, or under a partly-attended event, is used last."""
    from tools.day_shape import admits, anchor
    grid = _Grid(plan_start, bed_dt)
    for b in blocks:
        if _is_hard(b) and _dt(b["end"]) > plan_start:
            grid.mark(_dt(b["start"]), _dt(b["end"]), grid.busy)
    regions = [(grid.mask([(_dt(b["start"]), _dt(b["end"]))]), b.get("activities") or [],
                b.get("allows")) for b in blocks if _is_protected(b)]
    any_region = [any(r[0][k] for r in regions) for k in range(grid.n)]
    wind = grid.mask(_windows_of(blocks, "wind_down"))
    partial = grid.mask([(_dt(b["start"]), _dt(b["end"])) for b in blocks
                         if b["kind"] == "event" and b.get("partial")])
    excludes = set(shape.get("wind_down_excludes") or [])

    wins = []
    for w in list(shape.get("windows") or []) + list(extra_windows or []):
        if w["strength"] == "protected":
            continue
        s, e = w["start"], w["end"]
        s = s if isinstance(s, datetime) else anchor(day, s, shape["wake"])
        e = e if isinstance(e, datetime) else anchor(day, e, shape["wake"])
        if e <= s:
            e += timedelta(days=1)
        wins.append({**w, "s": s, "e": e, "mask": grid.mask([(s, e)])})

    def union(masks: list[list[bool]]) -> list[bool] | None:
        if not masks:
            return None
        return [any(m[k] for m in masks) for k in range(grid.n)]

    def both(a: list[bool] | None, b: list[bool] | None) -> list[bool] | None:
        if a is None or b is None:
            return a if b is None else b
        return [x and y for x, y in zip(a, b)]

    profiles: dict[tuple, dict] = {}

    def profile(c: dict) -> dict:
        attrs = c.get("attrs") or {"device": c["device"],
                                   "concentration": "heavy" if c["heavy"] else "light"}
        key = (c["activity"], json.dumps(attrs, sort_keys=True))
        if key not in profiles:
            rej = [False] * grid.n
            for mask, acts, allows in regions:
                if c["activity"] in acts or admits(allows, attrs):
                    continue
                for k in range(grid.n):
                    if mask[k]:
                        rej[k] = True
            mine = [w for w in wins if c["activity"] in w["activities"]]
            pref = union([w["mask"] for w in mine if w["strength"] == "preferred"])
            strong = union([w["mask"] for w in mine if w["strength"] == "strong"])
            other = union([w["mask"] for w in wins if c["activity"] not in w["activities"]])
            avoid = union([m for m in (other, partial) if m is not None])
            tiers = []
            if pref is not None:
                tiers.append((both(pref, strong), avoid))
            tiers += [(strong, avoid), (strong, partial), (strong, None)]
            profiles[key] = {"rej": rej, "tiers": tiers, "strong": strong,
                             "conds": [w for w in mine if w.get("condition")]}
        return profiles[key]

    trans = max(0, int(shape["transition_minutes"]) // _SLOT)
    brk = max(1, int(shape["break_minutes"]) // _SLOT)
    brk_after = max(1, int(shape["break_after_minutes"]) // _SLOT)

    placed: list[dict] = []
    unplaced: list[dict] = []
    counts: dict[str, int] = {}

    def put(c: dict, i: int, n: int, displaced: bool, copy: int) -> None:
        s = grid.at(i)
        e = s + timedelta(minutes=c["minutes"])
        grid.mark(s, e, grid.busy)
        grid.mark(s, e, grid.task_run)
        # The run of back-to-back work this task ends: task slots joined only by transition
        # slots. A break is a hard block (busy), so it ends a run — the walk stops at it.
        j = i + n
        run, k = 0, j - 1
        while k >= 0 and (grid.task_run[k] or (grid.task_gap[k] and not grid.busy[k])):
            run += 1 if grid.task_run[k] else 0
            k -= 1
        room = (j + brk <= grid.n
                and not any(grid.busy[g] or any_region[g] for g in range(j, j + brk)))
        if run >= brk_after and room:
            # Only where the time is free (Fable diff review S-3: a break once landed on a
            # meeting). A meeting straight after the run is itself the pause.
            bs = grid.at(j)
            be = bs + timedelta(minutes=brk * _SLOT)
            grid.mark(bs, be, grid.busy)
            placed.append({"id": f"break:{_iso(bs)}", "kind": "break", "title": "break",
                           "start": _iso(bs), "end": _iso(be)})
        else:
            for g in range(j, min(grid.n, j + trans)):
                grid.task_gap[g] = True
        cond = next((w["condition"] for w in profile(c)["conds"] if w["s"] < e and s < w["e"]), None)
        placed.append({"id": f"task:{c['ref']}@{s:%H%M}", "kind": "task", "ref": c["ref"],
                       "task_id": c["task_id"], "title": c["what"], "start": _iso(s),
                       "end": _iso(e), "essential": c["essential"], "score": c["score"],
                       "length_known": c["length_known"], "copy": copy,
                       "activity": c["activity"],
                       **({"condition": cond} if cond else {}),
                       **({"displaced_protected": True} if displaced else {})})
        counts[c["ref"]] = counts.get(c["ref"], 0) + 1

    def free_run(i: int, n: int, c: dict, allow_protected: bool, need: list | None,
                 avoid: list | None) -> bool:
        if i + n > grid.n:
            return False
        rej = profile(c)["rej"]
        for k in range(i, i + n):
            if grid.busy[k] or grid.task_gap[k]:
                return False
            if rej[k] and not allow_protected:
                return False
            if wind[k] and (c["kind"] == "deadline" or c["activity"] in excludes):
                return False
            if need is not None and not need[k]:
                return False
            if avoid is not None and avoid[k]:
                return False
        return True

    by_ref = {c["ref"]: c for c in cands}
    placed_starts: dict[str, list[datetime]] = {}
    # Kept placements first: a repair keeps what still fits where it was (plan § 5.6, § 5.8).
    for kb in keep:
        c = by_ref.get(kb.get("ref"))
        if not c:
            continue
        s = _dt(kb["start"])
        if s is None or s < plan_start:
            continue
        i, n = grid.idx(s), max(1, -(-c["minutes"] // _SLOT))
        if i < _after_idx(c, grid, day, shape):
            continue
        # A kept slot must still be the right kind of time: a task whose activity has an
        # only-here window (strong) is released from a slot outside it, and placed again. Found
        # live 2026-10-27: "Look up swim lessons" placed at 21:30 while it read as exercise kept
        # that slot after it became admin, with admin hours free at 16:05.
        strong = profile(c)["strong"]
        if strong is not None and not kb.get("displaced_protected") and \
                not all(strong[k] for k in range(i, min(grid.n, i + max(1, -(-c["minutes"] // _SLOT))))):
            continue
        if counts.get(c["ref"], 0) < c["copies"] and free_run(i, n, c, kb.get("displaced_protected", False), None, None):
            put(c, i, n, bool(kb.get("displaced_protected")), counts.get(c["ref"], 0))
            placed_starts.setdefault(c["ref"], []).append(s)

    for c in cands:
        n = max(1, -(-c["minutes"] // _SLOT))
        prof = profile(c)
        while counts.get(c["ref"], 0) < c["copies"]:
            copy = counts.get(c["ref"], 0)
            min_i = _after_idx(c, grid, day, shape)
            earlier = [_dt(x) for x in c.get("prior") or []] + placed_starts.get(c["ref"], [])
            if earlier and c.get("multi"):
                # Another dose later in the day: at least three hours after the last one.
                min_i = max(min_i, grid.idx(max(earlier) + timedelta(hours=3)))
            tiers = list(prof["tiers"])
            if prof["strong"] is not None and c["essential"]:
                tiers.append((None, None))      # outside its strong window, before protected time
            spot = None
            for need, avoid in tiers:
                spot = next((i for i in range(min_i, grid.n)
                             if free_run(i, n, c, False, need, avoid)), None)
                if spot is not None:
                    break
            displaced = False
            if spot is None and _may_protect(c):
                spot = next((i for i in range(min_i, grid.n)
                             if free_run(i, n, c, True, None, None)), None)
                displaced = spot is not None and any(prof["rej"][k] for k in range(spot, spot + n))
            if spot is None:
                unplaced.append({"ref": c["ref"], "title": c["what"],
                                 "reason": "no room" if grid.n else "outside waking hours",
                                 "essential": c["essential"], "vital": c["vital"]})
                break
            put(c, spot, n, displaced, copy)
            placed_starts.setdefault(c["ref"], []).append(grid.at(spot))
    return placed, unplaced


def _after_time(c: dict, day: date, shape: dict) -> datetime | None:
    """The earliest a candidate may start ("after 4 pm"), as a datetime on its ledger day."""
    if not c.get("after"):
        return None
    try:
        from tools.day_shape import anchor
        return anchor(day, datetime.strptime(str(c["after"]), "%H:%M").time(), shape["wake"])
    except (ValueError, KeyError):
        return None


def _after_idx(c: dict, grid, day: date, shape: dict) -> int:
    at = _after_time(c, day, shape)
    if not at:
        return 0
    i = max(0, grid.idx(at))
    return i + 1 if grid.at(i) < at else i


# --- the validator (plan § 5.5) --------------------------------------------------------------

def validate(plan: dict, events: list[dict], cands: list[dict], plan_start: datetime) -> list[str]:
    """Hard-rule failures as 'V<n>: detail' strings. Empty means the plan stands."""
    fails: list[str] = []
    wake_dt, bed_dt = _dt(plan["window"]["wake"]), _dt(plan["window"]["bed"])
    blocks = plan.get("blocks") or []
    ref_ok = {c["ref"] for c in cands}
    by_ref = {c["ref"]: c for c in cands}
    live = [b for b in blocks if not b.get("history")]
    solid = [b for b in live if _is_hard(b)]
    for i, a in enumerate(solid):
        for b in solid[i + 1:]:
            # Commitments may overlap each other — the calendar is the user's; the plan only
            # never puts its own blocks on top of them.
            if {a["kind"], b["kind"]} <= {"event", "own", "routine", "duty"} \
                    or "travel" in (a["kind"], b["kind"]):
                continue
            # A block already under way is the user's present (Fable verify N2): an event moved
            # onto it is an interruption to note, not a plan to reject.
            if a.get("in_progress") or b.get("in_progress"):
                continue
            if _dt(a["start"]) < _dt(b["end"]) and _dt(b["start"]) < _dt(a["end"]):
                fails.append(f"V1: {a['id']} overlaps {b['id']}")
    # V2 (R2-13): every timed event is accounted for, at its time, in its triaged form — a block
    # (there, own, a duty), a context row, a "?" hold, or deliberately not shown (noise, a
    # calendar's focus block, a calendar new since setup).
    have: dict = {}
    for b in blocks:
        if b["kind"] in ("event", "own", "context", "hold", "duty") and b.get("key"):
            have.setdefault(b["key"], b)
    unshown = set(plan.get("hidden") or []) | {
        k for keys in (plan.get("held_back") or {}).values() for k in keys}
    for e in events:
        s, en = _dt(e["start"]), _dt(e["end"])
        if e.get("all_day") or not s or en <= wake_dt or s >= bed_dt or e["key"] in unshown:
            continue
        b = have.get(e["key"])
        if b is None:
            fails.append(f"V2: event {e['key']} missing")
        elif b["kind"] != "duty" and (b["start"] != _iso(s) or b["end"] != _iso(en)):
            fails.append(f"V2: event {e['key']} moved")
    from tools.day_shape import admits
    regions = [(_dt(b["start"]), _dt(b["end"]), b.get("activities") or [], b.get("allows"))
               for b in blocks if _is_protected(b)]
    seen: dict[str, int] = {}
    for b in live:
        if b["kind"] != "task":
            continue
        if b.get("ref") not in ref_ok:
            fails.append(f"V3: unknown ref {b.get('ref')}")
            continue
        c = by_ref[b["ref"]]
        s, en = _dt(b["start"]), _dt(b["end"])
        under_way = bool(b.get("in_progress"))     # placed earlier, started already: as it was
        if not under_way and (en - s) < timedelta(minutes=c["minutes"]):
            fails.append(f"V4: {b['ref']} shorter than its {c['minutes']} min")
        if (not under_way and s < plan_start - timedelta(minutes=1)) or s < wake_dt or en > bed_dt:
            fails.append(f"V5: {b['ref']} outside the waking window or in the past")
        # V6 (R2-13): protected time admits what fits there — its own activity and what its
        # filter matches; anything else only when essential and nothing else fitted.
        attrs = c.get("attrs") or {"device": c.get("device", False),
                                   "concentration": "heavy" if c.get("heavy") else "light"}
        for p0, p1, acts, allows in regions:
            if s < p1 and p0 < en and not (c.get("activity") in acts or admits(allows, attrs)) \
                    and not c["essential"]:
                fails.append(f"V6: {b['ref']} in protected time it does not fit")
                break
        if c.get("after") and not under_way:
            try:
                earliest = datetime.combine(date.fromisoformat(plan["day"]),
                                            datetime.strptime(str(c["after"]), "%H:%M").time())
                if s < earliest:
                    fails.append(f"V10: {b['ref']} before its earliest time {c['after']}")
            except (ValueError, KeyError):
                pass
        seen[b["ref"]] = seen.get(b["ref"], 0) + 1
        if seen[b["ref"]] > max(c["copies"], 1):
            fails.append(f"V9: {b['ref']} placed {seen[b['ref']]} times")
    today = plan_start.date()
    # Any reported reason counts — "outside waking hours" after bedtime included (S-3).
    unplaced = {u["ref"] for u in plan.get("unplaced") or [] if u.get("reason")}
    history = {b.get("ref") for b in blocks if b.get("history")}
    for c in cands:
        due = _O()._d(c.get("due"))
        if c["vital"] and due and due <= today and c["ref"] not in seen \
                and c["ref"] not in unplaced and c["ref"] not in history:
            fails.append(f"V7: vital {c['ref']} neither placed nor reported unplaceable")
    for b in live:
        if b["kind"] == "travel":
            tr = b.get("travel") or {}
            if (_dt(b["end"]) - _dt(b["start"])) < timedelta(minutes=int(tr.get("minutes", 0))):
                fails.append(f"V8: {b['id']} shorter than the journey")
    return fails


# --- suggestions (plan § 5.9) ----------------------------------------------------------------

def _suggestions(blocks: list[dict]) -> list[dict]:
    """Derived in code; the Synthesizer decides which to act on (Mike, R2)."""
    out = []
    # One completion check per task per day — per dose for a dose habit (Fable verify N1): a
    # block placed again after an unconfirmed one keeps its start nudge, not a second check.
    checked: set[tuple] = set()
    for b in sorted(blocks, key=lambda x: x["start"]):
        s, e = _dt(b["start"]), _dt(b["end"])
        key = (b.get("ref"), b.get("copy", 0))
        if b["kind"] == "task" and b.get("essential"):
            if key in checked:
                # Moved after its time passed unconfirmed: it stays on the plan, quietly — the
                # first block's nudge and check were the day's two wakes for it.
                b = {**b, "_no_check": True, "_no_nudge": True}
            checked.add(key)
        if b.get("history"):
            # An ended essential block still owes its check (Fable diff review S-1) — the tick's
            # handled list makes sure it is asked once.
            if b["kind"] == "task" and b.get("essential") and not b.get("_no_check"):
                out.append({"id": f"check:{b['ref']}#{b.get('copy', 0)}@{e:%H%M}",
                            "kind": "check", "at": _iso(e), "ref": b["ref"],
                            "copy": b.get("copy", 0), "title": b["title"],
                            "why": "essential — did it happen?"})
            continue
        if b["kind"] == "travel" and not b["id"].startswith("travel_home:"):
            out.append({"id": f"nudge:{b['id']}@{s:%H%M}", "kind": "nudge", "at": _iso(s),
                        "ref": b.get("ref"), "title": b["title"],
                        "why": f"leave now — {b['travel']['minutes']} min by {b['travel']['mode']}"})
        elif b["kind"] == "task" and (b.get("essential") or b.get("displaced_protected")):
            if b.get("_no_nudge"):
                continue
            out.append({"id": f"nudge:{b['ref']}#{b.get('copy', 0)}@{s:%H%M}", "kind": "nudge",
                        "at": _iso(s), "ref": b["ref"], "copy": b.get("copy", 0),
                        "title": b["title"],
                        "why": "it takes the user's own time" if b.get("displaced_protected")
                        else "essential, starting now"})
            if b.get("essential") and not b.get("_no_check"):
                out.append({"id": f"check:{b['ref']}#{b.get('copy', 0)}@{e:%H%M}",
                            "kind": "check", "at": _iso(e), "ref": b["ref"],
                            "copy": b.get("copy", 0),
                            "title": b["title"], "why": "essential — did it happen?"})
    out.sort(key=lambda x: x["at"])
    return out


# --- the gate and the build (plan § 5.6) -----------------------------------------------------

def _event_digests(events: list[dict], day: date) -> dict:
    lo = datetime.combine(day, time(0, 0))
    hi = lo + timedelta(days=2)
    return {e["key"]: _digest(e["start"], e["end"], e["location"], e["title"])
            for e in events if _dt(e["start"]) and lo <= _dt(e["start"]) < hi}


def _zone_now(persona: str | None) -> str:
    try:
        from tools.location import current_zone
        return str((current_zone(persona) or {}).get("zone") or "")
    except Exception:  # noqa: BLE001
        return ""


def _classify(prev: dict | None, day: date, now: datetime, cands: list[dict], events: list[dict],
              shape_digest: str, zone: str, state: dict) -> tuple[str, list[str]]:
    """none / repair / reshuffle, with reasons — classified against the LIVE ledger."""
    if not prev or prev.get("version") != _VERSION or prev.get("day") != day.isoformat():
        return "reshuffle", ["first build of the day"]
    if prev.get("draft"):
        return "reshuffle", ["first build of the day (from last night's draft)"]
    req = ((state.get("reshuffle") or {}).get("requested") or {})
    if req and req.get("day") == day.isoformat():
        return "reshuffle", [f"requested: {req.get('reason', '')}"[:80]]
    reasons, mode = [], "none"
    delta = int((_cfg().score_weights() or {}).get("reshuffle_delta", 10))
    stored = (prev.get("digests") or {}).get("tasks") or {}
    fresh = {c["ref"]: (c["digest"], c["score"]) for c in cands}
    history = {b.get("ref") for b in prev.get("blocks") or [] if b.get("history")}
    added = [r for r in fresh if r not in stored and r not in history]
    if added:
        return "reshuffle", [f"{len(added)} task(s) added"]
    for ref, (dg, sc) in fresh.items():
        if ref in stored and stored[ref][0] != dg:
            if abs(int(sc) - int(stored[ref][1])) >= delta:
                return "reshuffle", [f"what matters changed ({ref})"]
            mode, reasons = "repair", reasons + [f"task changed ({ref})"]
    if any(r not in fresh for r in stored):
        mode, reasons = "repair", reasons + ["a task left the day"]
    if (prev.get("digests") or {}).get("events") != _event_digests(events, day):
        mode, reasons = "repair", reasons + ["calendar changed"]
    if (prev.get("digests") or {}).get("shape") != shape_digest:
        mode, reasons = "repair", reasons + ["day shape changed"]
    if (prev.get("digests") or {}).get("answers") != _digest(_event_answers()):
        mode, reasons = "repair", reasons + ["an event was answered"]
    if (prev.get("digests") or {}).get("zone") != zone:
        mode, reasons = "repair", reasons + ["place changed"]
    built = _dt(prev.get("built_at")) or now
    passed_ids = set(prev.get("passed") or [])
    for b in prev.get("blocks") or []:
        if b.get("history") or b["kind"] not in ("task", "event", "travel", "meal", "routine",
                                                 "duty"):
            continue
        s, e = _dt(b["start"]), _dt(b["end"])
        if built < s <= now or built < e <= now:
            mode = "repair" if mode == "none" else mode
            if "time moved" not in reasons:
                reasons.append("time moved")
        if (b["kind"] == "task" and b.get("essential") and e <= now and b["id"] not in passed_ids
                and not _ref_done(b.get("ref"), b.get("copy", 0))):
            # Only the first missed block of a task: its one re-placement (see _build) has been
            # made by then, so a second miss is a repair — it must not spend the model cap.
            earlier = [x for x in prev.get("blocks") or [] if x is not b and x.get("history")
                       and x.get("ref") == b.get("ref") and x.get("copy", 0) == b.get("copy", 0)]
            if not earlier:
                return "reshuffle", ["an essential block passed with no word"]
            mode = "repair" if mode == "none" else mode
    return mode, reasons


def _doses_done(ref: str | None) -> int:
    """How many times a habit occurrence is recorded done (a dose habit's count)."""
    tid, _, period = str(ref or "").partition("@")
    O = _O()
    t = next((O._norm(x) for x in O._load() if x.get("id") == tid), None)
    if not t or t.get("kind") != "habit" or not period:
        return 0
    return int(((t.get("occurrences") or {}).get(period) or {}).get("done") or 0)


def _ref_done(ref: str | None, copy: int = 0) -> bool:
    return _status_of(ref, copy) in ("done", "skipped", "closed")


def _status_of(ref: str | None, copy: int = 0) -> str:
    """A task block's status, read from the ledger now — the plan never stores it."""
    if not ref:
        return ""
    O = _O()
    tid, _, period = str(ref).partition("@")
    t = next((O._norm(x) for x in O._load() if x.get("id") == tid), None)
    if t is None:
        return "closed"
    if t.get("status") in O._TERMINAL:
        return "done" if t.get("status") == "done" else "closed"
    kind = t.get("kind")
    if kind == "habit" and period:
        occ = (t.get("occurrences") or {}).get(period) or {}
        if occ.get("skipped"):
            return "skipped"
        return "done" if int(occ.get("done") or 0) > copy else "open"
    if kind == "interval":
        last = O._d(t.get("last_done"))
        return "done" if last and last >= O._today() else "open"
    return "open"


def _build(day: date, persona: str, mode: str, reasons: list[str], prev: dict | None,
           now: datetime, events: list[dict], cands: list[dict], allow_lookup: bool,
           draft: bool = False, _seed: list[dict] | None = None) -> dict:
    from tools.day_shape import digest as shape_digest_fn
    from tools.day_shape import shape_for, window_for
    shape = shape_for(day, persona)
    wake_dt, bed_dt = window_for(day, shape=shape)
    plan_start = wake_dt if draft else max(_round_up(now), wake_dt)
    answers = _event_answers(persona)
    skeleton, notes, extra = _skeleton(day, shape, events, persona, allow_lookup, plan_start,
                                       answers=answers, discovery_ok=_discovery_ok(persona))

    history, inprog, keep = [], [], []
    passed = set(prev.get("passed") or []) if prev else set()
    if prev and prev.get("day") == day.isoformat() and not prev.get("draft"):
        for b in prev.get("blocks") or []:
            if b["kind"] not in ("task", "meal", "break"):
                continue
            s, e = _dt(b["start"]), _dt(b["end"])
            if e <= now:
                # Over — and only then (Fable diff review S-1: a block that had merely STARTED
                # used to become history, so the task under way was placed again later, and
                # its nudge and check moved with it on every read and never fired).
                history.append({**b, "history": True})
                if b["kind"] == "task":
                    passed.add(b["id"])
            elif s < plan_start:
                # Under way: it stays exactly where it is, and is not placed again.
                inprog.append({k: v for k, v in b.items() if k != "history"} | {"in_progress": True})
            elif mode == "repair" or (s - now) <= timedelta(minutes=int(_limit("frozen_minutes") or 20)):
                keep.append(b)
    if _seed is not None:
        # A model reshuffle: its placements are the seeds, kept wherever they fit (§ 5.7).
        keep = list(_seed)
    # A meal already eaten, or under way, is not placed again.
    eaten = {b["id"] for b in history + inprog if b["kind"] == "meal"}
    skeleton = [b for b in skeleton if b["id"] not in eaten]
    # How many more of each ref to place today (Fable diff review S-1, S-2):
    #  - a dose habit: the doses still unrecorded, less the blocks today already holding one
    #    (an ended block nobody confirmed still holds its dose — the check asks — so a missed
    #    record never plans a third dose of a twice-a-day medicine);
    #  - anything else: nothing while a block of it is under way; once every block of it has
    #    ended, one more only if it is essential and nothing records it done.
    placeable = []
    for c in cands:
        hist = [b for b in history if b["kind"] == "task" and b.get("ref") == c["ref"]]
        prog = [b for b in inprog if b["kind"] == "task" and b.get("ref") == c["ref"]]
        if c.get("multi"):
            unconfirmed = [b for b in hist if _status_of(b["ref"], b.get("copy", 0)) == "open"]
            more = c["copies"] - len(unconfirmed) - len(prog)
        elif prog:
            more = 0
        elif hist:
            # An essential task stays on the plan until it is done or the user drops it (Mike,
            # 2026-10-26: "should not expire after one re-placement. Metatron should check whether
            # they were done and keep them on or work with user to decide to remove them"). What
            # Fable verify N1 found — eight blocks and eight wakes by noon — is bounded where the
            # wakes are made instead: one start nudge and one check per task a day
            # (_suggestions), and one past row per task on the panel (_listed).
            more = 1 if (c["essential"] and not _ref_done(c["ref"])) else 0
        else:
            more = c["copies"]
        if more > 0:
            placeable.append({**c, "copies": more, "prior": [b["start"] for b in hist + prog]})
    placed, unplaced = _fill(placeable, skeleton + history + inprog, shape, plan_start, bed_dt,
                             extra["windows"], keep, day)
    # A kept slot never outranks what matters more (Mike, 2026-10-27: "important things happen
    # first and don't get bumped in favor of less important things"). Kept placements go in
    # before anything new, so a nice-to-have placed this morning could leave a task due today
    # with no room. When an essential item did not fit, fill again keeping only what starts
    # within the frozen window or matters at least as much; take it if more essentials fit.
    need = [u for u in unplaced if u.get("essential")]
    if need and keep:
        by_ref = {c["ref"]: c for c in placeable}
        floor = max(by_ref[u["ref"]]["score"] for u in need if u["ref"] in by_ref)
        frozen_cut = now + timedelta(minutes=int(_limit("frozen_minutes") or 20))
        slim = [kb for kb in keep if (_dt(kb["start"]) or now) <= frozen_cut
                or (kb.get("ref") in by_ref and (by_ref[kb["ref"]]["essential"]
                                                 or by_ref[kb["ref"]]["score"] >= floor))]
        if len(slim) < len(keep):
            placed2, unplaced2 = _fill(placeable, skeleton + history + inprog, shape, plan_start,
                                       bed_dt, extra["windows"], slim, day)
            if sum(1 for u in unplaced2 if u.get("essential")) < len(need):
                placed, unplaced = placed2, unplaced2
    # "Not placed" is for what needs a decision today (R2-9): an essential item that did not
    # fit. A non-essential leftover — a second stretching with no room — drops quietly; the log
    # and a model reshuffle still see it.
    dropped = [u["ref"] for u in unplaced if not u.get("essential")]
    unplaced = [u for u in unplaced if u.get("essential")]
    blocks = sorted(skeleton + history + inprog + placed, key=lambda b: (b["start"], b["kind"]))
    # A dose block's `copy` is its place in the day's order of that ref's blocks — the i-th
    # block is done once i+1 doses are recorded. Anything else is one task: copy 0.
    multi = {c["ref"] for c in cands if c.get("multi")}
    # Doses recorded with no block of today's plan behind them (done before the plan placed one)
    # come first in the count — or the dose still to do read as done (found live 2026-10-26: the
    # second stretch showed ✓ because the first was recorded off-plan).
    offset = {ref: max(0, _doses_done(ref) - sum(1 for b in history if b.get("ref") == ref))
              for ref in multi}
    order: dict[str, int] = {}
    for b in blocks:
        if b["kind"] == "task":
            if b.get("ref") in multi:
                b["copy"] = offset.get(b["ref"], 0) + order.get(b["ref"], 0)
                order[b["ref"]] = order.get(b["ref"], 0) + 1
            else:
                b["copy"] = 0
    plan = {
        "version": _VERSION, "day": day.isoformat(), "draft": draft,
        "built_at": now.isoformat(timespec="seconds"), "mode": "code", "trigger": mode,
        "reasons": reasons[:5],
        "window": {"wake": _iso(wake_dt), "bed": _iso(bed_dt),
                   "wake_source": shape["wake_source"], "bed_source": shape["bed_source"]},
        "blocks": blocks, "unplaced": unplaced, "dropped": dropped, "notes": notes,
        "passed": sorted(passed),
        # Event keys deliberately not shown, so the validator can account for every event.
        "hidden": extra["hidden"], "held_back": extra["held_back"],
        "digests": {"tasks": {c["ref"]: [c["digest"], c["score"]] for c in cands},
                    "events": _event_digests(events, day),
                    "shape": shape_digest_fn(persona), "zone": _zone_now(persona),
                    "answers": _digest(answers)},
    }
    for b in inprog:
        s0, e0 = _dt(b["start"]), _dt(b["end"])
        for x in skeleton:
            if _is_hard(x) and x["kind"] in ("event", "own", "routine", "duty") \
                    and _dt(x["start"]) < e0 and s0 < _dt(x["end"]):
                notes.append(f"{x['title']} now overlaps {b['title']}, already under way")
    plan["suggestions"] = _suggestions(blocks)
    # Location evidence answers a check only once its "Mark done?" card exists — the two ship
    # together or not at all (review V1-N2). A card is filed only off the reply path.
    answered = _location_evidence(plan, cands, persona, file=allow_lookup)
    if answered:
        plan["suggestions"] = [x for x in plan["suggestions"]
                               if not (x["kind"] == "check" and x.get("ref") in answered)]
        for b in plan["blocks"]:
            if b["kind"] == "task" and b.get("ref") in answered:
                b["evidence"] = "location"
    plan["failures"] = validate(plan, events, cands, plan_start)
    return plan


def _location_evidence(plan: dict, cands: list[dict], persona: str, file: bool) -> set[str]:
    """Refs whose completion check is answered by a location card (plan § 5.9).

    Evidence is PRESENCE, never duration (review R1-4): the transitions log keeps only
    (zone, entered_at) on a change, so the rule is an arrival in the task's zone inside
    [block start − 60 min, block end], and the card says exactly that and no more."""
    zone_by_ref = {c["ref"]: c["zone"] for c in cands if c.get("zone")}
    if not zone_by_ref:
        return set()
    try:
        from tools.location import _read_transitions
        arrivals = [(str(r.get("zone") or "").lower(), _local_stamp(r.get("entered_at")))
                    for r in _read_transitions(persona)]
    except Exception:  # noqa: BLE001
        return set()
    O = _O()
    out: set[str] = set()
    for b in plan.get("blocks") or []:
        ref = b.get("ref")
        if b["kind"] != "task" or ref not in zone_by_ref or ref in out:
            continue
        zone = zone_by_ref[ref]
        s, e = _dt(b["start"]), _dt(b["end"])
        hit = next((w for z, w in arrivals
                    if z == zone and w and s - timedelta(minutes=60) <= w <= e), None)
        if hit is None:
            continue
        key = f"{zone}@{plan['day']}"
        try:
            if O.has_proposal(ref, key, persona) or (file and O.add_proposal(
                    ref, basis=f"You were at the {zone} at {hit:%H:%M}.", persona=persona,
                    source="location", key=key, on_date=hit.date().isoformat())):
                out.add(ref)
        except Exception:  # noqa: BLE001
            continue
    return out


def _churn(prev: dict | None, plan: dict) -> dict:
    if not prev:
        return {"moved": 0, "added": len([b for b in plan["blocks"] if b["kind"] == "task"]),
                "dropped": 0}
    old = {b["id"]: b["start"] for b in prev.get("blocks") or [] if b["kind"] == "task"}
    new = {b["id"]: b["start"] for b in plan["blocks"] if b["kind"] == "task"}
    return {"moved": sum(1 for k in new if k in old and old[k] != new[k]),
            "added": sum(1 for k in new if k not in old),
            "dropped": sum(1 for k in old if k not in new)}


def _events_for(state: dict, day: date) -> list[dict]:
    snap = state.get("snapshot") or {}
    sd = _O()._d(snap.get("day"))
    if not sd or not (sd <= day <= sd + timedelta(days=2)):
        return []
    return snap.get("events") or []


def current(persona: str | None = None, reason: str = "", for_reply: bool = False) -> dict | None:
    """The plan for the ledger day, rebuilt only if the gate says so. Never fetches the calendar
    synchronously except after a calendar write this turn (boxed); never blocks a reply on the
    lock. Returns None when the planner is off or nothing could be built."""
    if not _flag("build"):
        return None
    persona = resolve_persona(persona)
    with persona_scope(persona):
        day, now = _today(), _now()
        state = _load_state(persona)
        age = _snapshot_age_minutes(state)
        snap_day = _O()._d((state.get("snapshot") or {}).get("day"))
        failed = _dt((state.get("snapshot") or {}).get("failed_at"))
        backoff = bool(failed and (now - failed) < timedelta(minutes=5))
        stale = not backoff and (age is None or age > float(_limit("snapshot_max_age_minutes") or 10)
                                 or bool(state.get("calendar_dirty")) or snap_day != day)
        if for_reply and _calendar_written_this_turn():
            _boxed_fetch(persona)
            state = _load_state(persona)
        elif stale:
            _refresh_in_background(persona)
        events = _events_for(state, day)
        prev = _read_json(_plan_path(day, persona), None)
        cands = _candidates(day, persona)
        from tools.day_shape import digest as shape_digest_fn
        mode, reasons = _classify(prev, day, now, cands, events, shape_digest_fn(persona),
                                  _zone_now(persona), state)
        if mode == "none":
            return prev
        t0 = _time.monotonic()
        # Built with NO lock held: a background build may look routes up, and the lock is for
        # file I/O only (review V1-N3). The write is optimistic — a plan written meanwhile by
        # someone else that is newer than ours wins, and ours is dropped.
        plan = _build(day, persona, mode, reasons, prev, now, events, cands,
                      allow_lookup=not for_reply)
        plan["snapshot_at"] = (state.get("snapshot") or {}).get("fetched_at")
        wait = int(_limit("reply_lock_ms") or 200) if for_reply else None
        with _locked(persona, wait_ms=wait) as got:
            if not got:
                return plan            # rendered, never written: the reply does not wait
            on_disk = _read_json(_plan_path(day, persona), None)
            if (on_disk and on_disk.get("day") == plan["day"]
                    and str(on_disk.get("built_at") or "") > plan["built_at"]):
                return on_disk
            _write_json(_plan_path(day, persona), plan)
            st = _load_state(persona)
            if mode == "reshuffle":
                rs = st.setdefault("reshuffle", {})
                req = rs.get("requested") or {}
                forced = bool(req.get("force")) and req.get("day") == day.isoformat()
                if req.get("day") == day.isoformat():
                    rs["requested"] = None
                if _flag("reshuffle_model"):
                    # `force` survives to the worker (Fable diff review S-7a): a request_replan
                    # inside the 15-minute gap still gets its model rework.
                    rs["pending"] = {"day": day.isoformat(), "reason": reasons[:1],
                                     "at": now.isoformat(timespec="seconds"), "force": forced}
                _write_json(_state_path(persona), st)
        _log("build", persona, trigger=mode, reason=(reasons or [""])[0][:60],
             reply=for_reply, failures=len(plan["failures"]),
             fail_rules=sorted({f.split(":")[0] for f in plan["failures"]}),
             placed=sum(1 for b in plan["blocks"] if b["kind"] == "task" and not b.get("history")),
             unplaced=len(plan["unplaced"]), **_churn(prev, plan),
             ms=int((_time.monotonic() - t0) * 1000))
        return plan


def request_reshuffle(reason: str, persona: str | None = None, force: bool = False) -> str:
    """Ask for a reshuffle of the rest of today. The next read rebuilds in code; with the model
    on, the tick refines it off the reply path."""
    persona = resolve_persona(persona)
    with persona_scope(persona):
        day = _today()
        with _locked(persona):
            st = _load_state(persona)
            st.setdefault("reshuffle", {})["requested"] = {
                "day": day.isoformat(), "reason": str(reason or "")[:120], "force": bool(force),
                "at": _now().isoformat(timespec="seconds")}
            _write_json(_state_path(persona), st)
    _log("reshuffle_requested", persona, force=force)
    return "noted — the rest of today will be reworked within a few minutes"


# --- rendering -------------------------------------------------------------------------------

def _hm(value) -> str:
    dt = _dt(value)
    return dt.strftime("%H:%M") if dt else "?"


def _label(b: dict) -> str:
    """A block as the Synthesizer reads it."""
    k = b["kind"]
    if k == "event":
        return f"{b['title']} (calendar{', partly attending' if b.get('partial') else ''})"
    if k == "routine":
        return f"{b['title']} (routine)"
    if k == "duty":
        return f"{b.get('duty', 'needed')} — {b['title']} (the user is needed)"
    if k == "hold":
        return (f"? {b['title']} `{b.get('key')}` — on the {b.get('calendar') or 'shared'} "
                f"calendar; not yet known whether it needs the user — ask once, record the answer "
                f"with answer_event (time held from screen and heavy work)")
    if k == "context":
        return f"{b['title']} — someone else's, nothing for the user" + (
            f" ({b['note']})" if b.get("note") else "")
    if k in ("meal", "ask") and b.get("ask"):
        return f"{b['title']} — {b['ask']}"
    if k == "travel":
        tr = b.get("travel") or {}
        est = ", estimated" if tr.get("estimated") else ""
        if b["id"].startswith("travel_home:"):
            return (f"home from {b['title'][len('travel home from '):]} "
                    f"({tr.get('minutes')} min by {tr.get('mode')}{est})")
        return f"leave for {b['title'][len('travel to '):]} ({tr.get('minutes')} min by {tr.get('mode')}{est})"
    if k == "task":
        bits = [b["title"], f"`{b['ref']}`"]
        if b.get("essential"):
            bits.append("essential")
        if b.get("displaced_protected"):
            bits.append("takes the user's own time — say so")
        if b.get("condition"):
            bits.append(f"only {b['condition']} — ask")
        if not b.get("length_known", True):
            bits.append("length unknown")
        return " — ".join(bits)
    return b["title"]


def _panel_title(b: dict) -> str:
    """A block as the user reads it in the Today panel (the testing view, Q1)."""
    k = b["kind"]
    if k == "hold":
        return f"{b['title']} — anything needed from you?"
    if k == "context":
        return f"{b['title']} (not yours)"
    if k == "duty":
        return f"{b.get('duty', 'needed')}: {b['title']}"
    if k in ("meal", "ask") and b.get("ask"):
        return f"{b['title']} — {b['ask']}"
    if k == "task":
        return b["title"] + (f" ({b['condition']}?)" if b.get("condition") else "")
    if k in ("event", "own", "routine"):
        return b["title"]
    return _label(b)


def _task_status_text(b: dict, now: datetime) -> str:
    st = _status_of(b.get("ref"), b.get("copy", 0))
    if st == "done":
        return " ✓"
    if st == "skipped":
        return " (skipped)"
    if st == "closed":
        return " (no longer tracked)"
    if _dt(b["end"]) <= now:
        return " — no word yet" if b.get("essential") else " — unconfirmed"
    return ""


def _listed(plan: dict) -> list[dict]:
    """The blocks a reader sees. A task moved after its time passed unconfirmed shows once — at
    its latest time — not as a trail of "no word yet" rows."""
    blocks = [b for b in plan.get("blocks") or [] if b["kind"] not in ("protected", "wind_down")]
    latest: dict[tuple, str] = {}
    for b in blocks:
        if b["kind"] == "task":
            k = (b.get("ref"), b.get("copy", 0))
            latest[k] = max(latest.get(k, ""), b["start"])
    return [b for b in blocks if not (b["kind"] == "task" and b.get("history")
                                      and b["start"] < latest[(b.get("ref"), b.get("copy", 0))]
                                      and _status_of(b.get("ref"), b.get("copy", 0)) == "open")]


def render_block(plan: dict | None, kind: str | None = None, due_now: list[dict] | None = None,
                 heads_up: bool = False, offer_rhythm: str | None = None,
                 allocation_gaps: list[dict] | None = None, tomorrow: dict | None = None,
                 ask_length: str | None = None) -> str:
    """The Synthesizer's view of the whole day (Mike, R2: "the whole day, including
    completed/missed items"). Statuses are read from the ledger now. Target ≤ ~1,000 tokens."""
    if not plan:
        return ""
    now = _now()
    out = ["TODAY'S PLAN — kept by code from the calendar, the tasks and the user's day shape. "
           "Authoritative for timing; whether a task is done comes from the Tasks section. "
           "Running the day is yours: say what to do now and next."]
    w = plan.get("window") or {}
    if "stated" not in (w.get("wake_source"), w.get("bed_source")):
        out.append(f"(Waking hours {_hm(w.get('wake'))}–{_hm(w.get('bed'))} are assumed, not "
                   f"stated — ask once, when it fits.)")
    snap = _dt(plan.get("snapshot_at"))
    if snap is None:
        out.append("(The calendar has not been read yet — events may be missing.)")
    elif (now - snap) > timedelta(minutes=float(_limit("snapshot_max_age_minutes") or 10) + 5):
        out.append(f"(Calendar as of {snap:%H:%M}.)")
    blocks = _listed(plan)
    earlier, now_b, nxt, later = [], None, [], []
    for b in blocks:
        s, e = _dt(b["start"]), _dt(b["end"])
        text = f"{_hm(b['start'])} {_label(b)}" + (_task_status_text(b, now) if b["kind"] == "task" else "")
        if e <= now:
            earlier.append(text)
        elif s <= now < e and now_b is None and b["kind"] != "break":
            now_b = f"{_label(b)} (until {_hm(b['end'])})" + (
                _task_status_text(b, now) if b["kind"] == "task" else "")
        elif len(nxt) < 2 and s > now:
            nxt.append(text)
        elif s > now:
            later.append(text)
    if earlier:
        out.append("Earlier: " + " · ".join(earlier[-8:]))
    out.append(f"Now ({now:%H:%M}): " + (now_b or "nothing planned"))
    if nxt:
        out.append("Next: " + " → ".join(nxt))
    if later:
        out.append("Later: " + " · ".join(later))
    own = [f"{b['title']} {_hm(b['start'])}–{_hm(b['end'])}" for b in plan.get("blocks") or []
           if b["kind"] == "protected" and _dt(b["end"]) > now]
    if own:
        out.append("Protected — only what fits there (family time: light tasks with no screen): "
                   + ", ".join(own))
    if plan.get("unplaced"):
        out.append("Not placed: " + "; ".join(
            f"{u['title']} ({u['reason']})" for u in plan["unplaced"][:5]))
    if plan.get("notes"):
        # What the build could not resolve — no room for a meal, no starting point for travel,
        # a meeting moved onto something under way (Fable verify N2). Shown, never acted on.
        out.append("Notes: " + "; ".join(plan["notes"][:3]))
    proposals = rule_proposals()
    if proposals:
        out.append("Standing answers the user's own answers suggest — offer ONE, once; record it "
                   "with set_day_shape(event_rules) only on their yes: " + "; ".join(proposals[:2]))
    soon = [x for x in plan.get("suggestions") or []
            if now - timedelta(minutes=5) <= _dt(x["at"]) <= now + timedelta(hours=3)]
    if soon:
        out.append("Suggested (yours to decide): " + " · ".join(
            f"{_hm(x['at'])} {x['kind']} — {x['title']}: {x['why']}" for x in soon[:6]))
    if kind == "evening_close":
        unconf = [f"{b['title']} `{b['ref']}`" for b in plan.get("blocks") or []
                  if b["kind"] == "task" and not b.get("essential") and _dt(b["end"]) <= now
                  and _status_of(b.get("ref"), b.get("copy", 0)) == "open"]
        if unconf:
            out.append("Unconfirmed today (non-essential) — ask about these in ONE line, once; "
                       "record what the user says; leave the rest: " + "; ".join(unconf))
    if tomorrow:
        tb = [f"{_hm(b['start'])} {_label(b)}" for b in _listed(tomorrow)
              if b["kind"] in ("event", "task", "travel")]
        if tb:
            out.append("Tomorrow (draft): " + " · ".join(tb[:10]))
    if allocation_gaps:
        out.append("Goals with no standing time this week — consult whoever owns the domain, "
                   "propose time, record it as a habit task linked to the goal: " + "; ".join(
                       f"{g['title']} ({g['id']}{', changed since its time was set' if g.get('changed') else ''})"
                       for g in allocation_gaps[:5]))
    if offer_rhythm:
        out.append(offer_rhythm)
    if ask_length:
        out.append(ask_length)
    if heads_up:
        out.append("[A fuller rework of the rest of today is under way — if it bears on your "
                   "answer, say so in one line, in everyday words.]")
    if due_now:
        out.append("DUE NOW: " + " · ".join(
            f"{_hm(x['at'])} {x['kind']} — {x['title']}: {x['why']}" for x in due_now))
    return "\n".join(out)


def today_view(persona: str | None = None) -> dict:
    """For the app's Today panel while testing (Q1 (c)); {} when `show_in_app` is off."""
    if not _flag("show_in_app"):
        return {}
    # Reply semantics on the poll (Fable diff review S-6): no route lookup and no wait on the
    # lock — the background refresh does both, and the next poll has the result.
    plan = current(persona, reason="app", for_reply=True)
    if not plan:
        return {"blocks": [], "building": True}
    now = _now()
    rows = []
    listed = _listed(plan)
    # A meal asked about inside an event is one question on that event's row, not a second row
    # (watch day 2: "Marta and kids over for dinner" read as two entries).
    ids = {b.get("id") for b in listed}
    folded: dict[str, list[dict]] = {}
    for b in listed:
        if b["kind"] == "meal" and b.get("under") in ids:
            folded.setdefault(b["under"], []).append(b)
    for b in listed:
        if b["kind"] == "meal" and b.get("under") in folded:
            continue
        st = ""
        if b["kind"] == "task":
            st = _status_of(b.get("ref"), b.get("copy", 0))
            if st == "open" and _dt(b["end"]) <= now:
                st = "no word yet" if b.get("essential") else "unconfirmed"
        title = _panel_title(b).replace(f" — `{b.get('ref')}`", "").replace(f"`{b.get('ref')}`", "")
        for meal in folded.get(b.get("id"), []):
            title += f" · is that also {meal['title']} ({_hm(meal['start'])})?"
        rows.append({"start": _hm(b["start"]), "end": _hm(b["end"]), "kind": b["kind"],
                     "title": title,
                     "status": st, "past": _dt(b["end"]) <= now,
                     "now": _dt(b["start"]) <= now < _dt(b["end"])})
    return {"day": plan["day"], "built_at": plan.get("built_at"), "blocks": rows,
            "unplaced": [u["title"] for u in plan.get("unplaced") or []],
            "notes": list(plan.get("notes") or [])[:3],
            "calendar_read": bool(plan.get("snapshot_at"))}


# --- tomorrow, rhythm, goal time (plan § 5.10) -----------------------------------------------

def _evening_start(persona: str | None) -> time:
    try:
        import yaml
        from core.persona import persona_config_dir
        cfg = yaml.safe_load((persona_config_dir(persona) / "scheduler.yaml").read_text()) or {}
        t = ((cfg.get("schedules") or {}).get("evening_close") or {}).get("time")
        if t:
            return datetime.strptime(str(t), "%H:%M").time()
    except Exception:  # noqa: BLE001
        pass
    return time(19, 0)


def tomorrow_draft(persona: str | None = None, build: bool = False) -> dict | None:
    """Tomorrow, code-only, in the evening window. `build` makes it if missing or stale (> 2 h);
    the tick does that, never a reply."""
    persona = resolve_persona(persona)
    day = _today() + timedelta(days=1)
    path = _plan_path(day, persona)
    have = _read_json(path, None)
    now = _now()
    if not build:
        return have if have and have.get("draft") else None
    if now.time() < _evening_start(persona) and now.date() == _today():
        return have
    if have and have.get("draft") and (now - (_dt(have.get("built_at")) or now)) < timedelta(hours=2):
        return have
    if have and not have.get("draft"):
        return have
    state = _load_state(persona)
    plan = _build(day, persona, "reshuffle", ["evening draft"], None, now, _events_for(state, day),
                  _candidates(day, persona), allow_lookup=True, draft=True)
    with _locked(persona):
        _write_json(path, plan)
    _log("draft", persona, placed=sum(1 for b in plan["blocks"] if b["kind"] == "task"))
    return plan


def rhythm_offer(persona: str | None = None, mark: bool = False) -> str | None:
    """Q13: when the user's day visibly runs past midnight, offer once a fortnight to move the
    boundary. Code observes; Synth asks; only the user's yes changes it."""
    persona = resolve_persona(persona)
    O = _O()
    if O._day_starts(persona):
        return None
    state = _load_state(persona)
    last = _O()._d(state.get("rhythm_offered"))
    today = _today()
    if last and (today - last).days < 14:
        return None
    # Read the conversations once a day, not on every turn, and mark without blocking — this
    # runs on the reply path (Fable diff review S-7b).
    cached = state.get("rhythm") or {}
    if cached.get("day") == today.isoformat():
        offer = cached.get("offer")
        if offer and mark:
            _mark_rhythm(persona, today)
        return offer
    offer = _rhythm_compute(persona, today)
    with _locked(persona, wait_ms=int(_limit("reply_lock_ms") or 200)) as got:
        if got:
            st = _load_state(persona)
            st["rhythm"] = {"day": today.isoformat(), "offer": offer}
            _write_json(_state_path(persona), st)
    if offer and mark:
        _mark_rhythm(persona, today)
    return offer


def length_ask(persona: str | None, plan: dict | None, mark: bool = False) -> str | None:
    """The one task on today's plan whose length nobody has given, named for the Synthesizer to
    ask about in passing — code-raised, because the instruction alone never fired (10-24 to
    10-26: 0 of 59 tasks carried a length the user stated, and nothing was asked). Each task is
    named once, ever; at most `length_asks_per_day` a day. `mark` records it as asked."""
    if not plan:
        return None
    persona = resolve_persona(persona)
    state = _load_state(persona)
    asked = state.get("length_asked") or {}
    today = _today().isoformat()
    if sum(1 for d in asked.values() if d == today) >= int(_limit("length_asks_per_day") or 2):
        return None
    now = _now()
    pick = next((b for b in sorted(plan.get("blocks") or [], key=lambda b: b["start"])
                 if b["kind"] == "task" and not b.get("length_known", True)
                 and not b.get("history") and _dt(b["end"]) > now
                 and b.get("task_id") and b["task_id"] not in asked), None)
    if not pick:
        return None
    if mark:
        with _locked(persona, wait_ms=int(_limit("reply_lock_ms") or 200)) as got:
            if got:
                st = _load_state(persona)
                st.setdefault("length_asked", {})[pick["task_id"]] = today
                _write_json(_state_path(persona), st)
    return (f"No length on file for {pick['title']} `{pick['task_id']}` — ask once, in passing, "
            f"how long it usually takes, and record their answer with set_minutes as stated. "
            f"Ask about no other task's length this turn.")


def _mark_rhythm(persona: str, today: date) -> None:
    with _locked(persona, wait_ms=int(_limit("reply_lock_ms") or 200)) as got:
        if got:
            st = _load_state(persona)
            st["rhythm_offered"] = today.isoformat()
            _write_json(_state_path(persona), st)


def _rhythm_compute(persona: str, today: date) -> str | None:
    late: dict[str, datetime] = {}
    conv = persona_data_dir(persona) / "conversations"
    for i in range(1, 15):
        d = today - timedelta(days=i - 1)
        path = conv / f"{d.isoformat()}.jsonl"
        try:
            lines = path.read_text().splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            ts = _dt(row.get("ts"))
            if row.get("proactive") or ts is None or ts.hour >= 5:
                continue
            key = (ts.date() - timedelta(days=1)).isoformat()
            if key not in late or ts > late[key]:
                late[key] = ts
    if len(late) < 9:
        return None
    mins = sorted(t.hour * 60 + t.minute for t in late.values())
    typical = mins[len(mins) // 2]
    end = f"{(typical // 30 + 1) * 30 // 60:02d}:{(typical // 30 + 1) * 30 % 60:02d}"
    return (f"The user's day seems to run past midnight (active after midnight on {len(late)} of "
            f"the last 14 days, usually until about {end}). Offer once, lightly, to end their "
            f"day later — update_task(task_id=\"settings\", action=\"day_starts\") on their yes.")


def allocation_gaps(persona: str | None = None) -> list[dict]:
    """Active goals with no habit task linked to them, or whose record changed since their time
    was set (Q6/F5) — for the weekly review."""
    O = _O()
    goals = O._goal_index()
    linked: dict[str, list[str]] = {}
    for t in O._load(persona):
        t = O._norm(t)
        if t.get("status") == "open" and t.get("kind") == "habit" and t.get("goal_id"):
            linked.setdefault(str(t["goal_id"]), []).append(str(t.get("goal_hash") or ""))
    out = []
    for gid, g in goals.items():
        if str(g.get("status") or "active") not in ("active", "at_risk", "not_started"):
            continue
        hashes = linked.get(gid)
        if not hashes:
            out.append({"id": gid, "title": g.get("title") or gid})
        elif O._goal_hash(g) not in hashes:
            out.append({"id": gid, "title": g.get("title") or gid, "changed": True})
    return out


# --- housekeeping ----------------------------------------------------------------------------

def prune(persona: str | None = None) -> int:
    """Plan files past retention, log rows past 90 days. Run once a day by the tick."""
    persona = resolve_persona(persona)
    today = _today()
    keep_days = int(_limit("plan_retention_days") or 3)
    removed = 0
    d = _dir(persona)
    for p in d.glob("plan_*.json") if d.exists() else []:
        day = _O()._d(p.stem[len("plan_"):])
        if day and (today - day).days > keep_days:
            try:
                p.unlink()
                removed += 1
            except OSError:
                pass
    cutoff = (today - timedelta(days=int(_limit("log_retention_days") or 90))).isoformat()
    path = _log_path(persona)
    with _locked(persona):
        try:
            rows = path.read_text().splitlines()
        except OSError:
            rows = []
        kept = [r for r in rows if r[8:18] >= cutoff or not r.startswith('{"at": "')]
        if len(kept) != len(rows):
            tmp = path.with_name(path.name + ".tmp")
            tmp.write_text("\n".join(kept) + ("\n" if kept else ""))
            os.chmod(tmp, 0o600)
            os.replace(tmp, path)
            removed += len(rows) - len(kept)
    return removed


# --- the reshuffle model (plan § 5.7) — Stage B ----------------------------------------------

_JSON_START = re.compile(r"\{")

# Tests inject a callable(payload: dict) -> str here; production calls the day_planner agent.
_MODEL_CALL = None


def _extract_json(raw: str) -> dict | None:
    """The first balanced JSON object in `raw` — not intake_extract's non-greedy `\\{.*?\\}`,
    which breaks on the nested object this contract returns."""
    if not raw:
        return None
    for m in _JSON_START.finditer(raw):
        depth, in_str, esc = 0, False, False
        for j in range(m.start(), len(raw)):
            ch = raw[j]
            if in_str:
                esc = (ch == "\\") and not esc
                if ch == '"' and not esc:
                    in_str = False
                if ch != "\\":
                    esc = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(raw[m.start():j + 1])
                        return obj if isinstance(obj, dict) else None
                    except ValueError:
                        break
    return None


def _payload(plan: dict, cands: list[dict], now: datetime, state: dict) -> dict:
    from tools.untrusted import wrap_untrusted
    # Protected windows and "?" holds carry what they admit (R2-11): the model may place only a
    # task whose activity is theirs or matches the filter there, as the validator checks.
    fixed = [{"start": b["start"], "end": b["end"], "kind": b["kind"],
              "title": wrap_untrusted(b["title"], source="calendar")
              if b["kind"] in ("event", "own", "hold", "duty") else b["title"],
              **({"admits": {"activities": b.get("activities") or [], "filter": b.get("allows")}}
                 if _is_protected(b) else {}),
              **({"partly": True} if b.get("partial") else {})}
             for b in plan["blocks"] if b["kind"] in ("event", "own", "travel", "meal", "protected",
                                                    "wind_down", "routine", "duty", "hold")
             and _dt(b["end"]) > now]
    try:
        from tools.ambient import _get_timezone
        tz = _get_timezone() or ""
    except Exception:  # noqa: BLE001
        tz = ""
    impacts = ((state.get("impact") or {}).get(plan["day"]) or [])[-3:]
    return {
        "today": plan["day"], "now": _iso(now), "timezone": tz, "window": plan["window"],
        "fixed": fixed,
        "candidates": [{k: c.get(k) for k in ("ref", "what", "minutes", "score", "essential",
                                               "stakes", "due", "domain", "goal", "copies",
                                               "activity", "device", "heavy", "solo", "after")}
                       for c in cands],
        "current_plan": [{"ref": b["ref"], "start": b["start"], "end": b["end"]}
                         for b in plan["blocks"] if b["kind"] == "task" and not b.get("history")],
        "user_notes": [i.get("text", "")[:200] for i in impacts],
    }


def _call_model(payload: dict, persona: str) -> str:
    if _MODEL_CALL is not None:
        return _MODEL_CALL(payload)
    from core.spend_guard import check_before_session
    check_before_session()                    # raises SpendLimitExceeded — caught by the caller
    from core.orchestrator import run_session
    # bare=True gives the agent no clock, so the payload carries today, now and the timezone.
    # NOT complexity="quick": that would route it to the bulk tier (core/router.py).
    return run_session("day_planner", json.dumps(payload, ensure_ascii=False), persona=persona,
                       bare=True, proactive=True)


def start_reshuffle(persona: str | None = None) -> bool:
    """Start the model reshuffle on a worker, single-flight by marker (review V1-N3): the lock is
    held only to copy inputs and write the marker; the model call runs with no lock."""
    persona = resolve_persona(persona)
    if not _flag("reshuffle_model"):
        return False
    with persona_scope(persona):
        day, now = _today(), _now()
        stale_s = int(_limit("reshuffle_stale_seconds") or 180)
        with _locked(persona):
            st = _load_state(persona)
            rs = st.setdefault("reshuffle", {})
            pend = rs.get("pending") or {}
            if pend.get("day") != day.isoformat():
                return False
            inflight = rs.get("inflight") or {}
            started = _dt(inflight.get("started_at"))
            if started and (now - started).total_seconds() < stale_s:
                return False
            counters = st.setdefault("counters", {}).setdefault(day.isoformat(), {})
            if int(counters.get("reshuffles", 0)) >= int(_limit("reshuffles_per_day") or 12):
                rs["pending"] = None
                _write_json(_state_path(persona), st)
                _log("reshuffle_capped", persona)
                return False
            last = _dt(rs.get("last_model_at"))
            gap = int(_limit("reshuffle_gap_minutes") or 15)
            if last and (now - last) < timedelta(minutes=gap) and not pend.get("force"):
                return False
            gen = int(rs.get("gen") or 0) + 1
            rs.update(gen=gen, inflight={"gen": gen, "started_at": now.isoformat(timespec="seconds")},
                      pending=None)
            counters["reshuffles"] = int(counters.get("reshuffles", 0)) + 1
            _write_json(_state_path(persona), st)
            plan = _read_json(_plan_path(day, persona), None)
        if not plan:
            return False
        cands = _candidates(day, persona)
        payload = _payload(plan, cands, now, st)
        _spawn_bound(_reshuffle_worker, persona, gen, payload, name="reshuffle")
        return True


def _reshuffle_worker(persona: str, gen: int, payload: dict) -> None:
    t0 = _time.monotonic()
    outcome, conflicts = "failed", 0
    try:
        try:
            raw = _call_model(payload, persona)
        except Exception as exc:  # noqa: BLE001 — a spend refusal or a dead call: the code plan stands
            raw, outcome = "", f"call_failed:{type(exc).__name__}"
        result = _extract_json(raw)
        if not isinstance(result, dict) or not isinstance(result.get("placements"), list):
            if outcome == "failed":
                outcome = "unparseable"
            return
        day, now = _today(), _now()
        state = _load_state(persona)
        prev = _read_json(_plan_path(day, persona), None)
        events = _events_for(state, day)
        cands = _candidates(day, persona)
        refs = {c["ref"] for c in cands}
        keep = [{"ref": p.get("ref"), "start": str(p.get("start") or "")[:16]}
                for p in result["placements"] if isinstance(p, dict) and p.get("ref") in refs]
        invented = sum(1 for p in result["placements"]
                       if isinstance(p, dict) and p.get("ref") not in refs)
        dropped = {d.get("ref"): str(d.get("reason") or "")[:80] for d in result.get("drop") or []
                   if isinstance(d, dict)}
        # Merge: the model's placements are kept where they fit on the CURRENT skeleton; code
        # fills anything it left out, unless it chose to drop it.
        plan = _build_from(day, persona, prev, now, events,
                           [c for c in cands if c["ref"] not in dropped], keep)
        placed_refs = {b["ref"] for b in plan["blocks"] if b["kind"] == "task" and not b.get("history")}
        kept_at = {(b["ref"], b["start"]) for b in plan["blocks"] if b["kind"] == "task"}
        conflicts = invented + sum(1 for k in keep if (k["ref"], k["start"]) not in kept_at)
        for ref, why in dropped.items():
            if ref in refs and ref not in placed_refs:
                c = next((x for x in cands if x["ref"] == ref), {})
                if c.get("essential"):
                    plan["unplaced"].append({"ref": ref, "title": c.get("what", ref),
                                             "reason": why or "left out", "essential": True,
                                             "vital": bool(c.get("vital"))})
                else:
                    plan.setdefault("dropped", []).append(ref)       # R2-9: no "Not placed" row
        plan["failures"] = validate(plan, events, cands, max(_round_up(now), _dt(plan["window"]["wake"])))
        # V3 applies to the model's own reply: a ref it invented rejects the whole refinement,
        # and so does a reply most of whose placements did not fit the current day.
        if plan["failures"] or invented or (keep and conflicts * 2 > len(keep)):
            outcome = "rejected"
            return
        plan["mode"] = "model"
        with _locked(persona):
            st = _load_state(persona)
            rs = st.setdefault("reshuffle", {})
            if int(rs.get("gen") or 0) != gen:
                outcome = "superseded"
                return
            _write_json(_plan_path(day, persona), plan)
            rs["inflight"] = None
            rs["last_model_at"] = now.isoformat(timespec="seconds")
            _write_json(_state_path(persona), st)
        outcome = "applied"
    finally:
        if outcome != "applied":
            try:
                with _locked(persona):
                    st = _load_state(persona)
                    rs = st.setdefault("reshuffle", {})
                    if int(rs.get("gen") or 0) == gen:
                        rs["inflight"] = None
                        _write_json(_state_path(persona), st)
            except Exception:  # noqa: BLE001
                pass
        _log("reshuffle", persona, outcome=outcome, conflicts=conflicts,
             ms=int((_time.monotonic() - t0) * 1000))


def _build_from(day: date, persona: str, prev: dict | None, now: datetime, events: list[dict],
                cands: list[dict], keep: list[dict]) -> dict:
    """A code build whose placements are seeded with `keep` (the model's), on today's skeleton."""
    seeded = dict(prev or {})
    plan = _build(day, persona, "reshuffle", ["model refinement"], seeded, now, events, cands,
                  allow_lookup=True, _seed=keep)
    return plan


# --- the ticks (Stage B registers them in core/scheduler.py) ---------------------------------

def refresh_tick() -> str:
    """Every 5 minutes, silent: snapshot, gate, repair, a requested reshuffle (off the loop),
    tomorrow's draft in the evening, the ledger sweep on a day change, pruning once a day."""
    if not _flag("build"):
        return "day plan: off"
    persona = resolve_persona(None)
    state = _load_state(persona)
    age = _snapshot_age_minutes(state)
    if age is None or age > float(_limit("snapshot_max_age_minutes") or 10) or state.get("calendar_dirty"):
        refresh_snapshot(persona)
    today = _today()
    notes = []
    if state.get("last_day") != today.isoformat():
        try:
            notes.append(_O().sweep(persona))
        except Exception as exc:  # noqa: BLE001
            notes.append(f"sweep failed: {type(exc).__name__}")
        with _locked(persona):
            st = _load_state(persona)
            st["last_day"] = today.isoformat()
            _write_json(_state_path(persona), st)
    plan = current(persona, reason="tick")
    started = start_reshuffle(persona)
    tomorrow_draft(persona, build=True)
    if state.get("pruned_on") != today.isoformat():
        prune(persona)
        with _locked(persona):
            st = _load_state(persona)
            st["pruned_on"] = today.isoformat()
            _write_json(_state_path(persona), st)
    return (f"day plan: {(plan or {}).get('trigger', 'none')}"
            + ("; model reshuffle started" if started else "")
            + (f"; {'; '.join(notes)}" if notes else ""))


def _quiet_now(persona: str) -> bool:
    try:
        from core.scheduler import _load_config, time_in_quiet_hours
        return time_in_quiet_hours(_load_config(persona), _now().time())
    except Exception:  # noqa: BLE001
        return False


def _idle_minutes(persona: str) -> float | None:
    try:
        from core.scheduler import _minutes_since_last_user_message
        return _minutes_since_last_user_message(persona)
    except Exception:  # noqa: BLE001
        return None


def _near_fixed(persona: str) -> str | None:
    """The fixed-session shield (review R1-6): `core.scheduler.near_fixed_session`, the scan the
    scheduler's own check-ins yield by, read at the planner's clock."""
    try:
        from core import scheduler as S
        fn = getattr(S, "near_fixed_session", None)
        return fn(S._load_config(persona), _now()) if fn else None
    except Exception:  # noqa: BLE001
        return None


def _checkin_prompt(persona: str) -> str:
    try:
        from core.scheduler import _load_config
        for name in (_cfg().load().get("replaces_jobs") or []):
            job = (_load_config(persona).get("schedules") or {}).get(name) or {}
            if job.get("prompt"):
                return str(job["prompt"])
    except Exception:  # noqa: BLE001
        pass
    return "Check in."


def nudge_tick() -> str | dict:
    """Every 5 minutes: wake the Synthesizer for what the plan marks due, batched into one wake
    (F2), or — on a day with nothing left planned — a check-in after a lag (Q3/F6). Gates quiet
    hours itself (the intake_sweep precedent) and never speaks over a live conversation."""
    if not (_flag("build") and _flag("nudges")):
        return "nudges: off"
    persona = resolve_persona(None)
    if _quiet_now(persona):
        return "nudges: quiet hours"
    idle = _idle_minutes(persona)
    if idle is not None and idle < 10:
        return "nudges: user is mid-conversation"
    plan = current(persona, reason="nudge tick")
    if not plan:
        return "nudges: no plan"
    now = _now()
    day = plan["day"]
    state = _load_state(persona)
    handled = (state.get("handled") or {}).get(day) or {}
    due = [x for x in plan.get("suggestions") or []
           if x["id"] not in handled and _dt(x["at"]) <= now <= _dt(x["at"]) + timedelta(minutes=20)
           and not (x["kind"] == "check" and _ref_done(x.get("ref"), x.get("copy", 0)))]
    shield = _near_fixed(persona)
    if due and shield:
        _mark(persona, day, due, "carried")
        return f"nudges: {len(due)} carried by a fixed session ({shield})"
    text, outcome, what = "", "", ""
    if due:
        directive = ("DAY PLAN — due now. " + " ".join(
            f"({i}) {_hm(x['at'])} {x['kind']}: {x['title']} — {x['why']}."
            for i, x in enumerate(due, 1))
            + " Decide what, if anything, is worth saying to the user now. If nothing is, reply "
              "with exactly [HOLD] and nothing else.")
        from core.remote_client import send_one
        text = send_one(persona, directive, nudge=True)
        outcome, what = ("sent" if text.strip() else "held"), "nudge"
        _mark(persona, day, due, outcome)
    elif _flag("owns_checkins") and _empty_day(plan, now) and _checkin_due(state, day, now, idle):
        from core.remote_client import send_one
        text = send_one(persona, _checkin_prompt(persona))
        outcome, what = ("sent" if text.strip() else "empty"), "checkin"
        with _locked(persona):
            st = _load_state(persona)
            ci = st.setdefault("checkins", {}).setdefault(day, [])
            ci.append(now.isoformat(timespec="seconds"))
            _write_json(_state_path(persona), st)
    if not what:
        return "nudges: nothing due"
    _log(what, persona, outcome=outcome, items=len(due))
    if text.strip():
        return {"notify": True, "title": "Metatron", "body": text, "summary": f"{what} {outcome}"}
    return f"nudges: {what} {outcome}"


def _mark(persona: str, day: str, items: list[dict], outcome: str) -> None:
    with _locked(persona):
        st = _load_state(persona)
        h = st.setdefault("handled", {})
        for k in [k for k in h if k < (_today() - timedelta(days=2)).isoformat()]:
            h.pop(k, None)
        h.setdefault(day, {}).update({x["id"]: {"outcome": outcome,
                                                "at": _now().isoformat(timespec="seconds")}
                                      for x in items})
        _write_json(_state_path(persona), st)


def _empty_day(plan: dict, now: datetime) -> bool:
    return not any(b["kind"] in ("task", "event") and _dt(b["end"]) > now
                   for b in plan.get("blocks") or [])


def _checkin_due(state: dict, day: str, now: datetime, idle: float | None) -> bool:
    """F6 — today's numbers: idle ≥ 180 min, ≥ 180 min since the last, at most 3 a day."""
    stamps = [_dt(x) for x in ((state.get("checkins") or {}).get(day) or [])]
    stamps = [s for s in stamps if s]
    if len(stamps) >= 3:
        return False
    if stamps and (now - max(stamps)) < timedelta(minutes=180):
        return False
    return idle is None or idle >= 180


def note_schedule_impact(level: str, text: str, persona: str | None = None) -> None:
    """The Coordinator's SCHEDULE_IMPACT line (Stage B): minor is noted for the next reshuffle's
    input; major requests one now."""
    level = str(level or "").strip().lower()
    if level not in ("minor", "major") or not _flag("build"):
        return
    persona = resolve_persona(persona)
    with persona_scope(persona):
        day = _today().isoformat()
        with _locked(persona):
            st = _load_state(persona)
            st.setdefault("impact", {})
            st["impact"] = {k: v for k, v in st["impact"].items() if k >= day}
            st["impact"].setdefault(day, []).append(
                {"level": level, "text": str(text or "")[:200],
                 "at": _now().isoformat(timespec="seconds")})
            st["impact"][day] = st["impact"][day][-5:]
            _write_json(_state_path(persona), st)
    if level == "major":
        request_reshuffle("the user's day changed", persona)


def pending_heads_up(persona: str | None = None) -> bool:
    """Is a fuller rework requested or running? For the testing-phase heads-up (Q10)."""
    st = _load_state(resolve_persona(persona))
    rs = st.get("reshuffle") or {}
    day = _today().isoformat()
    return bool(((rs.get("requested") or {}).get("day") == day)
                or ((rs.get("pending") or {}).get("day") == day) or rs.get("inflight"))


# --- tools ------------------------------------------------------------------------------------

def answer_event(event: str, answer: str, evidence: str = "", scope: str = "series",
                 duty: str | None = None, load: str | None = None) -> str:
    """Record what a calendar event means for the user, on their word (plan § 18.3): there,
    needs_me (with the duty — childcare, a lift), someone_else, or noise. `scope` "series" covers
    every occurrence of a repeating event; "this_one" only the one named (review F1). Built in
    round 2, granted in Stage B."""
    answer = str(answer or "").strip().lower()
    if answer not in _EVENT_ANSWERS:
        return f"error: `answer` must be one of {', '.join(_EVENT_ANSWERS)}. Nothing was written."
    scope = str(scope or "series").strip().lower()
    if scope not in ("series", "this_one"):
        return "error: `scope` is series or this_one. Nothing was written."
    try:
        from tools.turn_context import current as _turn
        turn = _turn()
    except Exception:  # noqa: BLE001
        turn = None
    if turn is not None and not turn.get("user_turn"):
        return ("error: not recorded — what an event means for the user changes only on their "
                "own word, and this turn has nothing from them. Nothing was changed.")
    evidence = str(evidence or "").strip()
    if not evidence:
        return "error: `evidence` is required — quote what the user said. Nothing was written."
    key = str(event or "").strip()
    persona = resolve_persona(None)
    state = _load_state(persona)
    known = {e["key"]: e for e in (state.get("snapshot") or {}).get("events") or []}
    ev = known.get(key) or next((e for e in known.values() if e["uid"] == key), None)
    if ev is None:
        return (f"error: no event {key!r} in today's or tomorrow's calendar — use the id the plan "
                f"shows in backticks. Nothing was written.")
    rec = {"answer": answer, "at": _now().isoformat(timespec="seconds"),
           "evidence": evidence[:200], "title": ev["title"][:120]}
    if duty and answer == "needs_me":
        rec["duty"] = str(duty).strip().lower()[:40]
    if load in ("full", "partial"):
        rec["load"] = load
    with _locked(persona):
        data = _event_answers(persona)
        store = data.setdefault("occurrences" if scope == "this_one" else "series", {})
        store[ev["key"] if scope == "this_one" else ev["uid"]] = rec
        _write_json(_answers_path(persona), data)
    _log("event_answered", persona, answer=answer, scope=scope)
    what = {"there": "the user is there", "needs_me": f"the user is needed ({rec.get('duty', 'help')})",
            "someone_else": "someone else's, nothing for the user", "noise": "not shown"}[answer]
    return (f"recorded: {ev['title']} — {what}"
            f"{', every time' if scope == 'series' else ', this once'}. The plan follows.")


ANSWER_EVENT_SCHEMA = {
    "name": "answer_event",
    "description": (
        "Record what one of the user's calendar events means for them, when THEY say it: there "
        "(they attend), needs_me (it puts a duty on them — childcare while their partner is out, "
        "a lift), someone_else (another person's, nothing for them), or noise (a promotion, not "
        "for them). Their day is planned around it from then on. Only on their own word — quote "
        "it as evidence. `event` is the id the plan shows in backticks."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "event": {"type": "string", "description": "The event id from the plan."},
            "answer": {"type": "string", "enum": list(_EVENT_ANSWERS)},
            "duty": {"type": "string", "description": "needs_me only: what — childcare, a lift."},
            "load": {"type": "string", "enum": ["full", "partial"],
                     "description": "there only: partial when they are only partly taken up "
                                    "(a playdate where they still got an hour of work done)."},
            "scope": {"type": "string", "enum": ["series", "this_one"],
                      "description": "series (default): every occurrence; this_one: only this one."},
            "evidence": {"type": "string", "description": "The user's words that say it."},
        },
        "required": ["event", "answer", "evidence"],
    },
}


_STOP = {"the", "and", "for", "with", "from", "into", "over", "time", "tbc", "day", "week"}


def rule_proposals(persona: str | None = None) -> list[str]:
    """When three answers about DIFFERENT events agree and their titles share a word, a standing
    rule is offered — as a proposal for the user, never applied on inference (Q4/F7)."""
    data = _event_answers(persona)
    groups: dict[tuple, list[str]] = {}
    for store in ("series", "occurrences"):
        for key, rec in (data.get(store) or {}).items():
            if isinstance(rec, dict) and rec.get("title"):
                uid = key.rsplit("@", 1)[0] if store == "occurrences" else key
                g = groups.setdefault((rec.get("answer"), rec.get("duty") or ""), [])
                if uid not in [u for u, _ in g]:
                    g.append((uid, rec["title"]))
    try:
        from tools.day_shape import read_shape
        ruled = {str(w).lower() for r in read_shape(persona).get("event_rules") or []
                 if isinstance(r, dict) for w in r.get("match") or []}
    except Exception:  # noqa: BLE001
        ruled = set()
    out = []
    for (answer, duty), items in groups.items():
        if len(items) < 3:
            continue
        words = [set(w for w in re.findall(r"[a-z][a-z']{2,}", t.lower()) if w not in _STOP)
                 for _, t in items]
        common = sorted(set.intersection(*words) - ruled)
        if common:
            out.append(f"events with “{common[0]}” → {answer}{f' ({duty})' if duty else ''} "
                       f"(answered so {len(items)} times)")
    return out


def request_replan(reason: str = "") -> str:
    """Synth's tool for the extraordinary case: ask for the rest of today to be reworked."""
    if not _flag("build"):
        return "the day plan is not running"
    return request_reshuffle(reason or "asked by the Synthesizer", force=True)


REQUEST_REPLAN_SCHEMA = {
    "name": "request_replan",
    "description": (
        "Ask for the rest of today to be reworked, now. Only for the extraordinary case — "
        "something has changed the user's day that the plan cannot see (they are unwell, the "
        "afternoon fell through, plans changed by phone). Ordinary changes — a task done, an "
        "event moved — are picked up on their own. The rework lands within a few minutes."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"reason": {"type": "string",
                                  "description": "What changed, in a few words."}},
        "required": ["reason"],
    },
}
