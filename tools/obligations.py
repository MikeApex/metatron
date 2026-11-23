"""
tools/obligations.py — commitments that stay open until something closes them.

WHY THIS IS DATA AND NOT SCHEDULER JOBS
---------------------------------------
tools/schedule.py § "Why obligations are not jobs" settled this before any of it was
built: twenty obligations each polling themselves daily is ~$15/month and twenty
interruptions. The intended shape is "a small number of sweeps that read all tracked
obligations at once, with individual obligations living as data." `MAX_AGENT_JOBS = 6`
and `MIN_INTERVAL_MINUTES = 360` exist to make the other shape impossible. This file is
the store that position assumed and nobody had written — that absence was the actual gap,
not any missing scheduling capability.

WHAT WENT WRONG WITHOUT IT
--------------------------
2026-08-07, 17:22: "I thought I already told you that the Quinn transfer was handled.
That is completed." Something was re-raising the payroll transfer and nothing could close
it. The nearest existing mechanism was `held_items` in tools/context_tracker.py, which is
ephemeral session state — it forgets, which is the opposite of the requirement.

So the failure to fix is not "we did not remind him enough". It is that **he closed it and
nothing recorded the closure.** That single fact sets three of the decisions below.

CLOSURE IS INFERRED, AND ITS EVIDENCE IS THE USER'S OWN WORDS
-------------------------------------------------------------
Mike's call, 2026-08-09: closure is inferred from conversation, not an explicit user
action — "in a dialogue these things will come up naturally." There is no "mark done"
gesture to perform, because requiring one is what produced the 08-07 failure.

Two consequences the code enforces rather than trusts:

1. **A close requires evidence and stores it verbatim** (`close_obligation` then,
   `update_task` since 2026-10-23). The backlog's own rule is that closed-without-evidence
   is not closed; the same standard applies here, and for
   the same reason — an inferred close with no record of what was inferred from cannot be
   audited or argued with later.
2. **Closing is reversible.** Inference is fallible by construction. Reopening
   exists so a wrong close costs a sentence rather than a lost commitment, and the reopen
   keeps the original close on file instead of erasing it.

WHY NOTHING HERE BLOCKS
-----------------------
Over the cap, `open_task` still writes and warns. This project has settled that
argument once already (`check_new_rule` in core/rule_classes.py warns and never blocks):
refusing a write to keep a file tidy discards something the user actually said, which is
the worse failure. The cap is a signal to the reader, not a gate.

WHAT THIS FILE DOES NOT DO
--------------------------
It does not decide when to raise anything. The store is what a session **may** draw on,
never a list to recite — config/agents/synthesizer.md § Scheduled session conduct owns
that judgement, and the "open on one thing" guidance governs it. An obligation store wired
straight to a notification is the six-times-in-one-day problem rebuilt.

THE LEDGER (2026-10-23) — COMPLETION RECORDED BY CODE, NOT RE-INFERRED BY MODELS
-------------------------------------------------------------------------------
Plan: archive/plans/task_ledger_plan_2026-10-23.md (Fable 5.1 review, three rounds). Measured
on the live store, 09-20 → 10-23: sixteen items were raised after they were done, decided or
moot — about 85 stale raises. Mostly NOT a failure to notice completion: in seven the close was
recorded somewhere and the path that raised the item never consulted it; nothing expired; and
recurring items had no per-occurrence record at all. So this file grew from a store of open
commitments into the single ledger every surface consults. Everything above still holds —
closure is inferred from the user's own words, evidence is required, closing is reversible,
nothing here blocks a write or decides on its own to speak.

Four kinds, one shape. A **task** is the definition; an **occurrence** is one instance with a
stable id `<task_id>@<period>`:
  - `deadline` — one occurrence; overdue until done or dismissed (Mike's default), or `moot`
    after `moot_after` when the thing is event-bound (an RSVP for an evening that has passed).
  - `habit` — one occurrence per period (`every` day/week/month, `times` per period, optional
    `on_days`). A non-daily quota can be made up within its period — Mike: M/W/F gym "is
    really 3x per week".
  - `interval` — every N days counted from when it was last done; the next instance exists
    only once the last is done. The plant-watering job that nagged 27 times from a date frozen
    into its own prompt was this kind written as prose.
  - `waiting` — someone else's move. Never overdue; surfaced once at `check_back`. Mike: these
    mostly expect an update from correspondence, not from the user.

What code owns: occurrences, eligibility, overdue/missed/moot, what reaches the head layer, the
once-a-day raise limit, the possible-completion hint, dedupe, adherence counts. What a model
owns: recognising that the user's words close one particular task. That is the one step code
cannot take without a tap, so it is the only one left to inference.

THE CLOCK. Every date here is the persona-local date (tools/ambient._now_local — the clock line
the models are shown), never bare date.today(): on a UTC VM the two disagree for an hour or more
every evening, and a habit "missed at midnight" has to mean the user's midnight.

THE STORE IS A NEW FILE, AND obligations.yaml IS NEVER WRITTEN AGAIN. v1 records are imported
into tasks.yaml on first load. An in-place migration was the first design and the review killed
it: code from before this change rewrites `{"obligations": [...]}` wholesale on every call, so
one write after a rollback would have erased every v2 task, on a store with no off-machine
backup. Importing instead means a rollback finds the v1 file intact and a roll-forward finds the
v2 file intact — `_remerge_v1` is the rule for anything old code wrote in between.

task_history.jsonl is append-only and never rewritten — the adherence asset, content-free apart
from task ids, keyed by occurrence so a repeated or catch-up sweep appends nothing twice.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import logging
import os
import re
import shutil
import threading
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

from core.persona import persona_data_dir

logger = logging.getLogger(__name__)

# Above this many open at once, every write carries a warning. Not a limit — see the
# module docstring on why nothing here blocks. The number is set where a morning session
# could no longer plausibly hold them all in view, which is the point at which the store
# has stopped being useful and started being a to-do list. Counts one-offs only: a daily
# habit is not a backlog.
_SOFT_CAP = 12

# How many tasks reach the session context block under "Now". Beyond this the block says
# how many more there are rather than listing them, because a long list in front of every
# session is exactly what "open on one thing" is meant to prevent.
_CONTEXT_MAX = 6
# A plan's unblocked steps shown beside that cap, per plan (2026-11-22; Fable diff review #5).
_STEPS_PER_PLAN = 3

# Deadlines this close are listed under "Now"; further out they are a count under "Later".
# Two days covers today, tomorrow and the day after — so the evening close's "tomorrow, in
# full" sees tomorrow's. A session carrying the weekly review widens it to seven, because
# that module says a review repeats the week (synthesizer_scheduled_sessions.md).
_LEAD_DAYS = 2
_REVIEW_LEAD_DAYS = 7

# How long a closed task stays visible under "Closed recently". Long enough to contradict
# the stale log line or thread that would otherwise re-raise it: the copies that re-raised
# the Chase bill after its 10-15 close were all inside three days.
_RECENT_DAYS = 3
_RECENT_MAX = 4

# Re-filing guards. A text match against something closed this recently is far more likely
# the same commitment re-minted from a stale copy (Finance re-opened the Chase bill the
# evening after it was closed) than a new one — the model may assert otherwise with
# `new_instance`. A shared source is a stronger signal than shared words, so its window is
# longer.
_RECLOSE_WINDOW_DAYS = 14
_SOURCE_WINDOW_DAYS = 30

# A waiting item surfaces once at its check-back date; without one, a week after opening.
_DEFAULT_CHECK_BACK_DAYS = 7

# Correspondence proposals nobody acted on are expired by the sweep after this long.
_PROPOSAL_TTL_DAYS = 14

# A sweep after downtime catches up at most this far back.
_SWEEP_CATCHUP_DAYS = 60

# A completion may be recorded against an earlier day this far back ("I went yesterday").
_BACKDATE_DAYS = 7

KINDS = ("deadline", "habit", "interval", "waiting")
_ONE_OFF = ("deadline", "waiting")
_TERMINAL = ("done", "dismissed", "moot")
_WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_EVERY = ("day", "week", "month")

# One lock for the store and the history file. Specialists fan out across threads, and two
# of them closing and opening in the same turn must not interleave a load and a save.
_LOCK = threading.RLock()
# ...and across PROCESSES (goal–task network plan § 10 R1): the server writes the store on user
# turns and taps while the scheduler's tick sweeps it, nudges from it and now opens prep tasks in
# it. An in-process lock alone let a "Done" tap and a tick interleave a load and a save, and the
# later save silently dropped the earlier write. `_store_lock` takes `_LOCK` and then an fcntl
# lock on a sibling file. flock() blocks a SECOND descriptor even inside the same process, so the
# file lock is taken once per outermost entry and nested entries only count depth (`_FLOCKS`,
# guarded by `_LOCK`, which is reentrant). Same pattern as tools/day_plan.py `_locked`.
_FLOCKS: dict[str, list] = {}


class StoreUnreadable(Exception):
    """tasks.yaml exists but cannot be parsed. Write paths refuse rather than overwrite it."""


def _v1_path(persona: str | None = None) -> Path:
    return persona_data_dir(persona) / "obligations.yaml"


def _store_path(persona: str | None = None) -> Path:
    return persona_data_dir(persona) / "tasks.yaml"


def _history_path(persona: str | None = None) -> Path:
    return persona_data_dir(persona) / "task_history.jsonl"


# --- The clock ------------------------------------------------------------------------------
# See THE CLOCK in the module docstring.

def _now() -> datetime:
    try:
        from tools.ambient import _now_local
        return _now_local().replace(tzinfo=None)
    except Exception:
        return datetime.now()


# THE DAY BOUNDARY (archive/plans/reply_latency_plan_2026-10-24.md § 6.4; built by the day
# planner, archive/plans/day_planner_plan_2026-10-24.md § 4.1). A user whose day runs past
# midnight sets `day_starts` ("04:00"); every date in this module is then the date of
# `dt - day_starts`, so 01:30 still belongs to yesterday — the habit is not "missed at midnight"
# while they are still up. It is NOT a shift of the clock: stamps stay true local time, and only
# the question "which day is this?" goes through `_ledger_day`. Default "00:00" — identical to the
# behaviour before it existed. Stored in tasks.yaml under `settings`, set by
# update_task(task_id="settings", action="day_starts", note="04:00").
_DAY_STARTS_MAX = (6, 0)
_DAY_STARTS_CACHE: dict = {"key": None, "value": timedelta(0)}


def _parse_hhmm(raw) -> tuple[int, int] | None:
    m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", str(raw or ""))
    if not m:
        return None
    hh, mm = int(m.group(1)), int(m.group(2))
    if hh > 23 or mm > 59:
        return None
    return hh, mm


def _day_starts(persona: str | None = None) -> timedelta:
    """The persona's day boundary as an offset from midnight. Never raises: an unreadable store
    or a malformed value is midnight, which is the old behaviour."""
    try:
        path = _store_path(persona)
        key = (str(path), path.stat().st_mtime_ns)
    except Exception:  # noqa: BLE001 — no store, or no persona bound: midnight, as before
        return timedelta(0)
    if _DAY_STARTS_CACHE["key"] == key:
        return _DAY_STARTS_CACHE["value"]
    value = timedelta(0)
    try:
        doc = yaml.safe_load(path.read_text()) or {}
        hm = _parse_hhmm(((doc.get("settings") or {}) if isinstance(doc, dict) else {})
                         .get("day_starts"))
        if hm and hm <= _DAY_STARTS_MAX:
            value = timedelta(hours=hm[0], minutes=hm[1])
    except Exception:  # noqa: BLE001
        value = timedelta(0)
    _DAY_STARTS_CACHE.update(key=key, value=value)
    return value


def _ledger_day(dt: datetime, persona: str | None = None) -> date:
    """Which ledger day the moment `dt` belongs to."""
    return (dt - _day_starts(persona)).date()


def _stamp_day(stamp, persona: str | None = None) -> date | None:
    """The ledger day of a stored stamp. A date-only value is that date; a full stamp goes
    through the boundary, so a close recorded at 01:30 counts for the day the user was still in."""
    if isinstance(stamp, datetime):
        return _ledger_day(stamp.replace(tzinfo=None), persona)
    raw = str(stamp or "").strip()
    if len(raw) > 10:
        try:
            return _ledger_day(datetime.fromisoformat(raw).replace(tzinfo=None), persona)
        except ValueError:
            pass
    return _d(raw)


def _today() -> date:
    return _ledger_day(_now())


def _stamp() -> str:
    return _now().isoformat(timespec="seconds")


def _d(value) -> date | None:
    """A stored date, or None. Tolerates date objects — yaml.safe_load turns an unquoted
    2026-10-23 into one."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = str(value or "").strip()
    if len(raw) < 10:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def _iso_arg(name: str, value) -> tuple[str | None, str | None]:
    """(YYYY-MM-DD or None, error or None) for a tool argument that must be a date."""
    raw = str(value or "").strip()
    if not raw:
        return None, None
    if len(raw) != 10 or _d(raw) is None:
        return None, (f"error: `{name}` must be a date in YYYY-MM-DD form, not {raw!r} — "
                      f"put a vague phrase in `note` instead. Nothing was written.")
    return raw, None


# --- The store ------------------------------------------------------------------------------

def _read_yaml(path: Path):
    return yaml.safe_load(path.read_text()) or {}


def _v1_items(persona: str | None = None) -> list[dict]:
    path = _v1_path(persona)
    if not path.exists():
        return []
    try:
        data = _read_yaml(path)
    except Exception:
        return []
    items = data.get("obligations") if isinstance(data, dict) else None
    return [it for it in items if isinstance(it, dict)] if isinstance(items, list) else []


def _from_v1(it: dict) -> dict:
    """One v1 obligation as a v2 deadline task. Ids are kept: they are in conversations,
    closed evidence and Accountability's joins, and a renamed id is a lost reference."""
    opened = str(it.get("opened_at") or "")
    what = str(it.get("what") or "").strip()
    t: dict = {
        "id": str(it.get("id") or _new_id(what)),
        "what": what,
        "kind": "deadline",
        "status": "done" if it.get("status") == "closed" else "open",
        "created_at": opened or None,
        "start": opened[:10] or None,
        "created_by": "import:v1",
    }
    # The v1 schema invited "a short phrase if genuinely vague" in `due`. v2 keeps only a
    # real date there, so a phrase moves into the note rather than being lost or guessed at.
    raw_due = str(it.get("due") or "").strip()
    note = str(it.get("note") or "").strip()
    if raw_due:
        if len(raw_due) == 10 and _d(raw_due):
            t["due"] = raw_due
        else:
            note = (f"{note} " if note else "") + f"(due, as first stated: {raw_due})"
    if note:
        t["note"] = note
    if it.get("domain"):
        t["domain"] = str(it["domain"])
    if t["status"] == "done":
        t["closed_at"] = it.get("closed_at")
        t["evidence"] = it.get("evidence")
    if isinstance(it.get("close_history"), list):
        t["history"] = [{"event": "reopened", **h} for h in it["close_history"]
                        if isinstance(h, dict)]
    return {k: v for k, v in t.items() if v is not None}


def _norm(t: dict) -> dict:
    """Read-time defaults, so a hand-edited or legacy-shaped row never crashes a reader."""
    t = dict(t)
    t["id"] = str(t.get("id") or "")
    t["what"] = str(t.get("what") or "")
    if t.get("kind") not in KINDS:
        t["kind"] = "deadline"
    status = t.get("status") or "open"
    t["status"] = "done" if status == "closed" else status
    return t


# --- The network (archive/plans/goal_task_network_plan_2026-11-18.md § 4.1, § 10 R7/R9) -----
# `needs: [id, …]` — a task cannot start until each is done. `part_of: <task id | goal id>` — the
# end state it serves. `required` (default true) — whether dismissing it stops what needs it.
# `blocked` is DERIVED here, once per load, from the whole store, and attached to each row as
# `_blocked` (never saved — `_save_doc` strips it). Computing it per load rather than inside the
# single-row `_view_core` is review R7a: one row cannot see whether its prerequisites are done,
# and passing a set to ~15 call sites is a set that one forgotten site leaks through. Every
# reader goes through `_load_doc`, so every reader sees the same answer.

def _needs(t: dict) -> list[str]:
    raw = t.get("needs")
    if isinstance(raw, str):
        raw = [raw]
    return [str(x) for x in raw or [] if str(x or "").strip()]


def _satisfies(dep: dict | None) -> bool:
    """Does this prerequisite let what needs it go ahead? Done does. Dismissed or moot does only
    when the step was optional (`required: false`) — a skipped "gather P60" must not silently
    unblock "file the return" (§ 4.5)."""
    if dep is None:
        return False
    status = dep.get("status")
    if status == "done":
        return True
    return status in ("dismissed", "moot") and dep.get("required") is False


def _annotate_network(tasks: list[dict]) -> None:
    by_id = {t.get("id"): t for t in tasks}
    for t in tasks:
        t.pop("_blocked", None)
        t.pop("_blocked_by", None)
        if t.get("status") != "open":
            continue
        waiting = [d for d in _needs(t) if not _satisfies(by_id.get(d))]
        if waiting:
            t["_blocked"] = True
            t["_blocked_by"] = waiting


def _is_step(t: dict) -> bool:
    """A step of a plan, or anything waiting on one: the user-facing duplicate guards and the soft
    cap skip it (R7b) — otherwise the user's own new task is refused as "already open as <a hidden
    step>". A plan's end state carries no `part_of` but is hidden exactly as its steps are while it
    waits, so `_blocked` counts too."""
    return bool(t.get("part_of") or t.get("_blocked"))


def _dependents(tasks: list[dict], tid: str) -> list[dict]:
    """Open tasks that need `tid`, directly or through another open task — breadth first."""
    out, seen, frontier = [], {tid}, [tid]
    while frontier:
        cur = frontier.pop(0)
        for t in tasks:
            if t.get("status") == "open" and t.get("id") not in seen and cur in _needs(t):
                seen.add(t["id"])
                out.append(t)
                frontier.append(t["id"])
    return out


_PREREQ_DISMISSED = "its prerequisite was dismissed"


def _close_dependents(doc: dict, t: dict) -> list[str]:
    """R9, phase 1's dismissal rule. A dismissed REQUIRED step closes everything that needs it
    `moot` — it can't go ahead — and records the cascade on the dismissed step, so the end state is
    raised once as Important ("X can't go ahead without Y — redo it?"). An optional step closes
    nothing: what needs it unblocks. Phase 2 replaces the close with a re-plan."""
    if t.get("required") is False:
        return []
    closed = []
    for dep in _dependents(doc["tasks"], t["id"]):
        dep["status"] = "moot"
        dep["closed_at"] = _stamp()
        dep["evidence"] = _PREREQ_DISMISSED
        dep.setdefault("history", []).append({"event": "closed_by_prerequisite",
                                              "at": _stamp(), "prerequisite": t["id"]})
        doc.setdefault("_history", []).append(_one_off_row(dep, "moot"))
        closed.append(dep["id"])
    if closed:
        t["cascade"] = {"closed": closed, "at": _stamp(), "raised": None}
    return closed


def _stuck_behind(tasks: list[dict], t: dict) -> str | None:
    """Refuse to reopen a step whose required prerequisite is closed and not done: reopened, it
    would sit blocked and invisible forever (Fable diff review #7). The way back is the
    prerequisite — reopening that brings this step back with it."""
    by_id = {x.get("id"): x for x in tasks}
    for d in _needs(t):
        dep = by_id.get(d)
        if dep and dep.get("status") in _TERMINAL and not _satisfies(dep):
            return (f"error: {t['id']} can't be reopened on its own — it needs {d} "
                    f"({dep.get('what')}), which is {dep.get('status')}. Reopen {d} instead; this "
                    f"step comes back with it. Nothing was changed.")
    return None


def _reopen_cascade(doc: dict, t: dict) -> int:
    cascade = t.pop("cascade", None) or {}
    n = 0
    for cid in cascade.get("closed") or []:
        dep = _find(doc["tasks"], cid)
        if dep and dep.get("status") == "moot" and dep.get("evidence") == _PREREQ_DISMISSED:
            dep["status"] = "open"
            dep.setdefault("history", []).append({"event": "reopened", "at": _stamp(),
                                                  "was": "moot", "reason": "prerequisite redone"})
            for k in ("closed_at", "evidence"):
                dep.pop(k, None)
            n += 1
    return n


_IMPLIED = "done by implication"


def _imply_prerequisites(doc: dict, t: dict) -> list[str]:
    """Mike's judgement gate, 2026-11-21: *"If it's clear that the later step couldn't have been
    completed without the earlier one, then both should be considered completed."* A REQUIRED
    prerequisite is exactly that (`required` is what says the later step cannot go ahead
    without it), so when a step is done, every required prerequisite behind it that is not
    done — still open, dismissed, or closed by a dismissal — is closed done too, with that
    reason. An optional one still open is closed moot: what it was for is finished. Whether
    the user really did the later step is the model's judgement (the close gate's); this is
    only what follows from it. Returns the ids changed."""
    by_id = {x.get("id"): x for x in doc["tasks"]}
    changed: list[str] = []
    seen: set = set()
    frontier = list(_needs(t))
    while frontier:
        did = frontier.pop(0)
        if did in seen:
            continue
        seen.add(did)
        dep = by_id.get(did)
        if dep is None or dep.get("status") == "done":
            continue
        optional = dep.get("required") is False
        if optional and dep.get("status") != "open":
            continue
        frontier.extend(_needs(dep))
        was = dep.get("status")
        dep["status"] = "moot" if optional else "done"
        dep["closed_at"] = _stamp()
        dep["evidence"] = (f"no longer needed: {t.get('what')} is done" if optional
                           else f"{_IMPLIED}: {t.get('what')} was done, which could not be "
                                f"done without it")
        dep.setdefault("history", []).append({"event": "closed_by_later_step", "at": _stamp(),
                                              "was": was, "later_step": t.get("id")})
        doc.setdefault("_history", []).append(_one_off_row(dep, dep["status"]))
        if dep.get("cascade"):
            # Its dismissal is undone by the facts: nothing to ask about, and the other steps
            # that dismissal closed come back.
            _reopen_cascade(doc, dep)
        changed.append(did)
    return changed


def cascades_to_raise(persona: str | None = None, as_of: date | None = None) -> list[dict]:
    """Dismissals that closed later steps, not yet put to the user — for the day plan's Important
    list. Each is raised once (`mark_cascade_raised`) and only within a few days of happening."""
    today = as_of or _today()
    tasks = [_norm(t) for t in _load(persona)]
    by_id = {t["id"]: t for t in tasks}
    out = []
    for t in tasks:
        c = t.get("cascade") or {}
        # A prerequisite that went moot by its date stops its plan as surely as a dismissal does,
        # and is raised the same way (Fable diff review #6).
        if t.get("status") not in ("dismissed", "moot") or not c.get("closed") or c.get("raised"):
            continue
        at = _stamp_day(c.get("at"))
        if not at or (today - at).days > _RECENT_DAYS:
            continue
        closed = [by_id[i] for i in c["closed"] if i in by_id]
        # The end state is the closed step nothing else in the cascade needs — the last one.
        needed = {d for x in closed for d in _needs(x)}
        end = next((x for x in reversed(closed) if x["id"] not in needed), closed[-1] if closed else None)
        if end is None:
            continue
        out.append({"id": t["id"], "what": t["what"], "end": end["what"], "end_id": end["id"],
                    "closed": len(closed), "lapsed": t.get("status") == "moot",
                    "later": [(x["id"], x["what"]) for x in closed]})
    return out


def mark_cascade_raised(task_ids: list[str], persona: str | None = None) -> None:
    if not task_ids:
        return

    def apply(doc: dict) -> int:
        n = 0
        for t in doc["tasks"]:
            c = t.get("cascade")
            if t.get("id") in task_ids and isinstance(c, dict) and not c.get("raised"):
                c["raised"] = _stamp()
                n += 1
        return n

    try:
        _with_store(persona, apply)
    except Exception as exc:  # noqa: BLE001 — bookkeeping never breaks a reply
        logger.warning("[tasks] cascade raise not recorded: %s", exc)


# --- Writing a whole plan at once (§ 10 R7c) ---------------------------------------------------

_STEP_FIELDS = ("what", "kind", "due", "eligible_from", "flexible", "after", "before", "minutes",
                "minutes_source", "needs", "part_of", "required", "stakes", "domain", "note",
                "activity", "key", "source_id", "prep_for", "zone", "moot_after", "adopt",
                "goal_id")
# Fields an adopted task takes from the plan (§ 11: open tax tasks adopted into a plan). Its own
# `what`, history and source stay; a `due` it already has is kept unless the plan's is earlier.
_ADOPT_FIELDS = ("needs", "part_of", "eligible_from", "flexible", "goal_id", "required")
# R5's two-day critical margin (only a step that close to its end was vital) was retired
# 2026-11-22 — see _end_weight.


def _goal_priority(goal: dict | None) -> str | None:
    """The priority a goal was taken on at (high/normal/low), or None. `vetted.priority` held free
    text before 2026-11-22 ("ahead of Northwind review"); that reads as no priority."""
    if not goal:
        return None
    p = str((goal.get("vetted") or {}).get("priority") or "").strip().lower()
    if p in _PRIORITIES:
        return p
    # An obligation is high whatever it serves (Mike, 11-22: "Taxes might not align with mission,
    # but still are high priority") — and the 11-21 tax goal's free-text priority reads as none.
    if goal.get("essential") is True or str(goal.get("kind") or "").lower() == "obligation":
        return "high"
    return None


def _end_weight(target: dict | None, goal: dict | None) -> dict:
    """What a plan's steps inherit from the end state they lead to: {"vital", "priority"}.

    Mike, 2026-11-22: "I don't think any of the steps in filing the taxes are missable", and the
    rule is general — every plan, not taxes. Until then (R5) only a step within two days of the
    end was vital and the rest `missable`, so an early required step past its date LAPSED: it sank
    to the bottom of the day and the steps waiting on it stalled, with nothing said (the 11-21 tax
    plan's sign-in check scored 20, last of 15). A required step of something the user took on is
    now vital, unless the end itself was judged missable (a task end) or taken on at low priority
    (a goal end). The cost R5 avoided is named in § 16: a step is essential only on its last day
    and after (inside its window it is not — day_plan `_candidates`), and then each day it stays
    open it can wake the Synthesizer twice (a start nudge and an end check), ~$0.01 a wake."""
    if target is not None:
        return {"vital": target.get("stakes") != "missable", "priority": target.get("priority")}
    pri = _goal_priority(goal)
    return {"vital": pri != "low", "priority": pri}


# A value a step took from its end state carries this source, so the daily reweigh moves only
# what it set itself — never what the user stated, nor what an agent recorded from what they said
# (`set_stakes` / `set_priority`, source inferred; Fable diff review 11-22 #2).
_PLAN_SOURCE = "plan"


def _step_weight(e: dict, w: dict, legacy: bool = False) -> None:
    """Apply an end state's weight to one step. Only a value with no source, or one this function
    set (`plan`), moves; `legacy` also moves the `inferred` values open_plan wrote before 11-22."""
    movable = (None, _PLAN_SOURCE) + (("inferred",) if legacy else ())
    if e.get("stakes_source") in movable:
        vital = w.get("vital") and e.get("required") is not False
        e["stakes"], e["stakes_source"] = ("vital" if vital else "missable"), _PLAN_SOURCE
    if w.get("priority") and e.get("priority_source") in movable:
        e["priority"], e["priority_source"] = w["priority"], _PLAN_SOURCE


def reweigh_plan_steps(persona: str | None = None, legacy: bool = False) -> int:
    """Re-apply _end_weight to every open step's plan-set values — after its end state's weight
    changed (a goal re-vetted, an end task judged). `legacy` (once, on the first tick after the
    11-22 deploy) also moves the `inferred` values open_plan wrote under R5. Code only, idempotent.
    Returns how many steps changed, or the store's error string."""
    def apply(doc: dict) -> int:
        tasks = doc["tasks"]
        by_id = {t["id"]: t for t in tasks}
        goals = _goal_index()
        n = 0
        for t in tasks:
            po = t.get("part_of")
            pf = t.get("prep_for") or {}
            if t.get("status") == "open" and pf and not pf.get("chat") and not t.get("stakes"):
                t["stakes"], t["stakes_source"] = "vital", _PLAN_SOURCE   # a code prep (open_plan)
                n += 1
                continue
            if t.get("status") != "open" or not po or pf:
                continue
            target = by_id.get(po)
            w = _end_weight(target, None if target is not None else goals.get(po))
            before = (t.get("stakes"), t.get("priority"))
            _step_weight(t, w, legacy=legacy)
            if (t.get("stakes"), t.get("priority")) != before:
                n += 1
        return n
    return _with_store(persona, apply)


def _acyclic(edges: dict[str, list[str]]) -> bool:
    state: dict[str, int] = {}

    def visit(n: str) -> bool:
        if state.get(n) == 1:
            return False
        if state.get(n) == 2:
            return True
        state[n] = 1
        for m in edges.get(n, []):
            if m in edges and not visit(m):
                return False
        state[n] = 2
        return True

    return all(visit(n) for n in edges)


def open_plan(steps: list[dict], persona: str | None = None, created_by: str = "plan") -> dict:
    """Write a whole plan in ONE locked write: ids minted first, every step validated, and
    all-or-nothing — a refused step aborts the plan, so no later step is left with a `needs` that
    points nowhere (review R7c, the mid-plan near-match refusal).

    Each step: {key, what, kind="deadline", due?, eligible_from?, flexible?, after?, minutes?,
    needs: [key | existing id], part_of?: key | existing task id | goal id, required=True,
    stakes?, domain?, note?, activity?, source_id?, prep_for?}. Returns
    {"ok": True, "ids": {key: id}} or {"ok": False, "error": "..."}; nothing is written on error.
    Code-only in phase 1 (no tool schema): the test project and prep tasks. The project planner
    that calls it is phase 2.
    """
    if not isinstance(steps, list) or not steps:
        return {"ok": False, "error": "a plan needs at least one step"}
    keys: dict[str, str] = {}
    clean: list[dict] = []
    for i, raw in enumerate(steps):
        if not isinstance(raw, dict):
            return {"ok": False, "error": f"step {i} is not a mapping"}
        unknown = set(raw) - set(_STEP_FIELDS)
        if unknown:
            return {"ok": False, "error": f"step {i}: unknown field(s) {sorted(unknown)}"}
        what = str(raw.get("what") or "").strip()
        if not what:
            return {"ok": False, "error": f"step {i} has no `what`"}
        kind = str(raw.get("kind") or "deadline").strip().lower()
        if kind not in _ONE_OFF:
            return {"ok": False, "error": f"step {i}: a plan step is a one-off, not {kind!r}"}
        key = str(raw.get("key") or f"s{i}")
        if key in keys:
            return {"ok": False, "error": f"two steps share the key {key!r}"}
        adopt = str(raw.get("adopt") or "").strip()
        keys[key] = adopt or _new_id(what)
        entry = {"what": what, "kind": kind, "status": "open"}
        if raw.get("goal_id"):
            entry["goal_id"] = str(raw["goal_id"]).strip()
        for name in ("due", "eligible_from", "moot_after"):
            iso, err = _iso_arg(name, raw.get(name))
            if err:
                return {"ok": False, "error": f"step {i}: {err}"}
            if iso:
                entry[name] = iso
        if not entry.get("due"):
            # An undated one-off is never placed on a day nor shown on Today (§ 10 R4), so a step
            # without a date would unblock and never appear (Fable diff review #9).
            return {"ok": False, "error": f"step {i}: every step needs a `due` (its latest date)"}
        if raw.get("flexible"):
            entry["flexible"] = True
        for name in ("after", "before"):
            if raw.get(name):
                if _parse_hhmm(raw[name]) is None:
                    return {"ok": False, "error": f"step {i}: `{name}` is HH:MM"}
                entry[name] = str(raw[name]).strip()
        if raw.get("minutes") is not None:
            dur, err = _minutes_arg(raw["minutes"], raw.get("minutes_source"))
            if err:
                return {"ok": False, "error": f"step {i}: {err}"}
            entry.update(dur)
        stakes = raw.get("stakes")
        if stakes is not None and stakes not in _STAKES:
            return {"ok": False, "error": f"step {i}: `stakes` is one of {', '.join(_STAKES)}"}
        for name in ("domain", "note", "activity", "source_id", "zone"):
            if raw.get(name):
                entry[name] = str(raw[name]).strip()
        if isinstance(raw.get("prep_for"), dict):
            entry["prep_for"] = {k: str(v) for k, v in raw["prep_for"].items() if v}
        if raw.get("required") is False:
            entry["required"] = False
        clean.append({"key": key, "entry": entry, "needs": _needs(raw),
                      "part_of": str(raw.get("part_of") or "").strip(), "stakes": stakes,
                      "adopt": adopt})
    adopted_ids = [c["adopt"] for c in clean if c["adopt"]]
    if len(set(adopted_ids)) != len(adopted_ids):
        return {"ok": False, "error": "the same task is adopted twice"}

    def apply(doc: dict) -> dict:
        tasks = doc["tasks"]
        existing = {t["id"]: t for t in tasks}
        for c in clean:
            if not c["adopt"]:
                continue
            cur = existing.get(c["adopt"])
            if cur is None or cur.get("status") != "open" or cur.get("kind") not in _ONE_OFF:
                return {"ok": False, "error": f"step {c['key']!r} adopts {c['adopt']!r}, which is "
                                              f"not an open one-off task"}
            po = keys.get(c["part_of"], c["part_of"])
            if cur.get("part_of") and cur.get("part_of") != po:
                return {"ok": False, "error": f"{c['adopt']} is already part of "
                                              f"{cur.get('part_of')}"}
        edges: dict[str, list[str]] = {}
        for c in clean:
            resolved = []
            for n in c["needs"]:
                if n in keys:
                    resolved.append(keys[n])
                elif n in existing and existing[n].get("kind") in _ONE_OFF:
                    resolved.append(n)
                else:
                    return {"ok": False, "error": f"step {c['key']!r} needs {n!r}, which is "
                                                  f"neither a step of this plan nor a one-off task"}
            c["entry"]["needs"] = resolved
            edges[keys[c["key"]]] = resolved
            po = c["part_of"]
            if po:
                po = keys.get(po, po)
                target = existing.get(po)
                if po.startswith("ob_") and po not in existing and po not in keys.values():
                    return {"ok": False, "error": f"step {c['key']!r} is part of {po!r}, which "
                                                  f"does not exist"}
                if target is not None and target.get("status") in _TERMINAL:
                    return {"ok": False, "error": f"step {c['key']!r} is part of {po!r}, which is "
                                                  f"already {target.get('status')}"}
                goal = None if (target is not None or po in keys.values()) else _goal_index().get(po)
                if goal is not None and str(goal.get("status") or "active") not in (
                        "active", "not_started", "at_risk"):
                    # Only a goal that has been taken on is decomposed (§ 4.2) — a proposed one
                    # is still being considered, a parked or declined one is not wanted now.
                    return {"ok": False, "error": f"goal {po!r} is {goal.get('status')} — only a "
                                                  f"goal that has been taken on is planned"}
                c["entry"]["part_of"] = po
        if not _acyclic(edges):
            return {"ok": False, "error": "the steps' `needs` form a cycle"}
        # Duplicate guard per plan (R7b): a step dedupes against its own plan only — the other
        # steps here and open steps already part of the same end state — never the user's tasks.
        for i, c in enumerate(clean):
            what = c["entry"]["what"]
            for other in clean[:i]:
                if _same_commitment(other["entry"]["what"], what):
                    return {"ok": False, "error": f"steps {other['key']!r} and {c['key']!r} are "
                                                  f"the same commitment"}
            po = c["entry"].get("part_of")
            if po:
                twin = next((t for t in tasks if t.get("status") == "open"
                             and t.get("part_of") == po and t.get("id") not in adopted_ids
                             and _same_commitment(t.get("what", ""), what)), None)
                if twin:
                    return {"ok": False, "error": f"step {c['key']!r} is already open in this "
                                                  f"plan as {twin['id']}"}
            sid = c["entry"].get("source_id")
            if sid:
                dup = _source_duplicate(tasks, sid, _today())
                if dup:
                    return {"ok": False, "error": f"already tracked from the same source as "
                                                  f"{dup['id']} ({dup.get('status')})",
                            "duplicate": dup["id"]}
        # Stakes and priority (amended 2026-11-22, ranking § 16): explicit wins; else a step
        # takes its end state's weight — see _step_weight.
        end_w = {}
        for c in clean:
            po = c["entry"].get("part_of")
            target = None
            if po in keys.values():
                target = next(x["entry"] for x in clean if keys[x["key"]] == po)
            elif po in existing:
                target = existing[po]
            goal = (_goal_index().get(po) or {}) if (po and target is None) else None
            end_w[c["key"]] = _end_weight(target, goal)
        stamp, today = _stamp(), _today()
        for c in clean:
            e = c["entry"]
            if c["adopt"]:
                cur = existing[c["adopt"]]
                # An adopted task keeps its what, history, source and a stated stakes; it takes
                # its place in the plan. A due it already has stands unless the plan needs it
                # earlier.
                for name in _ADOPT_FIELDS:
                    if e.get(name) not in (None, [], ""):
                        cur[name] = e[name]
                # Its own earlier date stands only where it still fits the plan: not before the
                # window opens, nor before a step it now needs is due (Fable diff review #8 — a
                # task due 25 Nov given eligible_from 28 Nov sat hidden and came back overdue).
                old, new = _d(cur.get("due")), _d(e.get("due"))
                ef = _d(cur.get("eligible_from"))
                by_key = {keys[x["key"]]: x["entry"] for x in clean}
                need_dues = [_d((by_key.get(n) or existing.get(n) or {}).get("due"))
                             for n in cur.get("needs") or []]
                fits = bool(old and new and old <= new and (not ef or old >= ef)
                            and all(nd is None or old >= nd for nd in need_dues))
                if new and not fits:
                    if old and old != new:
                        cur.setdefault("history", []).append({
                            "event": "rescheduled", "at": stamp, "from": cur.get("due"),
                            "to": e["due"], "reason": "fitted into its plan",
                            "was_overdue": bool(old < today)})
                    cur["due"] = e["due"]
                if not cur.get("minutes") and e.get("minutes"):
                    cur["minutes"], cur["minutes_source"] = e["minutes"], e.get("minutes_source", "estimated")
                # An adopted END STATE (the obligation itself) keeps its stakes — "missable"
                # inferred for a filing deadline would be the wrong way round.
                if cur.get("part_of"):
                    _step_weight(cur, end_w[c["key"]])
                if cur.get("needs") == []:
                    cur.pop("needs")
                cur.setdefault("history", []).append({"event": "adopted_into_plan", "at": stamp,
                                                      "part_of": cur.get("part_of"),
                                                      "by": created_by})
                continue
            if c["stakes"]:
                e["stakes"], e["stakes_source"] = c["stakes"], "stated"
                if e.get("part_of"):
                    _step_weight(e, end_w[c["key"]])      # its priority still comes from the end
            elif e.get("prep_for"):
                # A prep for an event (§ 4.7) was essential because its stakes were left unset and
                # unset counted as vital; since 2026-11-22 unset is back-burner, so it says so.
                e["stakes"], e["stakes_source"] = "vital", _PLAN_SOURCE
            elif not e.get("part_of"):
                e["stakes"], e["stakes_source"] = "vital", _PLAN_SOURCE   # an end state itself
            else:
                _step_weight(e, end_w[c["key"]])
            e["id"] = keys[c["key"]]
            e["created_at"] = stamp
            e["created_by"] = created_by
            e.setdefault("start", today.isoformat())
            if e["needs"] == []:
                e.pop("needs")
        for c in clean:
            if not c["adopt"]:
                tasks.append(c["entry"])
        _annotate_network(tasks)
        return {"ok": True, "ids": dict(keys), "adopted": adopted_ids}

    result = _with_store(persona, apply)
    if isinstance(result, str):            # the store could not be read
        return {"ok": False, "error": result}
    return result


def close_plan_of(end_id: str, reason: str, persona: str | None = None) -> int:
    """Close every open step part_of `end_id` (a goal declined, parked or completed — § 4.1),
    moot with `reason`. A step's own end-state task, if any, is the caller's to close."""
    end_id = str(end_id or "").strip()
    if not end_id:
        return 0
    n = {"v": 0}

    def apply(doc: dict) -> None:
        for t in doc["tasks"]:
            if t.get("status") == "open" and t.get("part_of") == end_id:
                t.update(status="moot", closed_at=_stamp(), evidence=reason)
                t.setdefault("history", []).append({"event": "closed_with_end_state",
                                                    "at": _stamp(), "reason": reason})
                doc.setdefault("_history", []).append(_one_off_row(t, "moot"))
                n["v"] += 1

    if not any(t.get("status") == "open" and t.get("part_of") == end_id for t in _load(persona)):
        return 0
    _with_store(persona, apply)
    return n["v"]


def _remerge_v1(doc: dict, persona: str | None = None) -> None:
    """
    Fold in anything old code wrote to obligations.yaml after the import — the rollback case.

    The rule: v1 may ADD an id v2 has never seen, and may CLOSE an item v2 still has open. It
    can never reopen or overwrite a v2 terminal state. Two consequences, stated so they are not
    rediscovered: a `reopen_obligation` performed on old code during a rollback is dropped here
    (v2's close wins); and an id minted on v1 in that window must pass the open-duplicate guard
    before it is imported, so a twin of a v2-only task is skipped and logged, not added.

    Old code rewrites the whole v1 file on every write, so its mtime is a reliable signal.
    """
    v1 = _v1_path(persona)
    if not v1.exists():
        return
    imp = doc.get("import") or {}
    try:
        mtime = v1.stat().st_mtime
    except OSError:
        return
    if mtime <= float(imp.get("v1_mtime") or 0) + 1e-6:
        return
    by_id = {t["id"]: t for t in doc["tasks"]}
    added = closed = skipped = 0
    for it in _v1_items(persona):
        tid = str(it.get("id") or "")
        current = by_id.get(tid)
        if current is None:
            t = _norm(_from_v1(it))
            if t["status"] == "open" and _open_duplicate(doc["tasks"], t["what"]):
                skipped += 1
                logger.info("[tasks] v1 re-merge skipped %s as a duplicate of an open task", tid)
                continue
            doc["tasks"].append(t)
            by_id[t["id"]] = t
            added += 1
        elif (it.get("status") == "closed" and current.get("status") == "open"
              and current.get("kind") in _ONE_OFF):
            current["status"] = "done"
            current["closed_at"] = it.get("closed_at") or _stamp()
            current["evidence"] = it.get("evidence") or "closed on the previous version"
            doc.setdefault("_history", []).append(_one_off_row(current, "done"))
            closed += 1
    doc["import"] = {**imp, "v1_mtime": mtime, "remerged_at": _stamp(),
                     "remerge": {"added": added, "closed": closed, "skipped": skipped}}
    doc["_dirty"] = True


def _load_doc(persona: str | None = None) -> dict:
    """The v2 document, importing v1 on first load. Raises StoreUnreadable if tasks.yaml
    exists and cannot be parsed — the caller decides whether that is fatal."""
    path = _store_path(persona)
    if path.exists():
        try:
            doc = _read_yaml(path)
        except Exception as exc:
            raise StoreUnreadable(str(exc)) from exc
        if not isinstance(doc, dict) or not isinstance(doc.get("tasks"), list):
            raise StoreUnreadable("tasks.yaml carries no task list")
        doc["tasks"] = [_norm(t) for t in doc["tasks"] if isinstance(t, dict)]
        _remerge_v1(doc, persona)
        _annotate_network(doc["tasks"])
        return doc
    doc: dict = {"version": 2, "tasks": [_norm(_from_v1(it)) for it in _v1_items(persona)]}
    v1 = _v1_path(persona)
    if v1.exists():
        try:
            mtime = v1.stat().st_mtime
        except OSError:
            mtime = 0.0
        doc["import"] = {"at": _stamp(), "v1_mtime": mtime, "count": len(doc["tasks"])}
        doc["_dirty"] = True
    _annotate_network(doc["tasks"])
    return doc


def _save_doc(doc: dict, persona: str | None = None) -> None:
    """Atomic write (temp file + replace), 0600, then flush any history rows the change
    produced. The temp-and-replace is what keeps a crash mid-write from leaving half a file
    that the next load would refuse as unreadable."""
    rows = doc.pop("_history", None) or []
    doc.pop("_dirty", None)
    path = _store_path(persona)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp{os.getpid()}.{threading.get_ident()}")
    for t in doc.get("tasks") or []:
        # Derived per load (`_annotate_network`), never stored: a stored `blocked` would outlive
        # the step that unblocks it.
        if isinstance(t, dict):
            t.pop("_blocked", None)
            t.pop("_blocked_by", None)
    tmp.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, path)
    if rows:
        _append_history(rows, persona)


def _preserve_corrupt(persona: str | None = None) -> None:
    """Keep a copy of an unreadable store before anything could replace it — the context
    tracker's lesson: the next write was what destroyed the evidence."""
    path = _store_path(persona)
    try:
        if path.exists():
            dest = path.with_name(f"{path.name}.corrupt-{_now().strftime('%Y%m%d')}")
            if not dest.exists():
                shutil.copy2(path, dest)
    except OSError:
        pass


@contextmanager
def _store_lock(persona: str | None = None):
    """`_LOCK`, plus an fcntl lock on `tasks.yaml.lock` beside the store — see `_FLOCKS`.
    Reentrant within a thread; exclusive across threads and processes."""
    with _LOCK:
        path = _store_path(persona)
        key = str(path)
        held = _FLOCKS.get(key)
        if held:
            held[1] += 1
            try:
                yield
            finally:
                held[1] -= 1
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        fh = open(path.with_name(path.name + ".lock"), "a+")
        try:
            fcntl.flock(fh, fcntl.LOCK_EX)
            _FLOCKS[key] = [fh, 1]
            try:
                yield
            finally:
                _FLOCKS.pop(key, None)
                try:
                    fcntl.flock(fh, fcntl.LOCK_UN)
                except OSError:
                    pass
        finally:
            fh.close()


def _with_store(persona: str | None, fn):
    """Load, apply `fn(doc)`, save, return fn's result. An unreadable store is preserved and
    nothing is written: overwriting it would replace every task with only this call's."""
    with _store_lock(persona):
        try:
            doc = _load_doc(persona)
        except StoreUnreadable as exc:
            _preserve_corrupt(persona)
            return (f"error: the task store could not be read ({exc}); nothing was written, "
                    f"and the damaged file has been kept for repair.")
        result = fn(doc)
        _save_doc(doc, persona)
        return result


def _load(persona: str | None = None) -> list[dict]:
    """Every task, for readers. Never raises: a corrupt store must not take down the session
    that read it — returning empty loses visibility for one call; raising would break every
    session until fixed. Persists a first-time v1 import so tasks.yaml exists promptly."""
    try:
        with _store_lock(persona):
            doc = _load_doc(persona)
            tasks = [dict(t) for t in doc["tasks"]]
            if doc.get("_dirty"):
                _save_doc(doc, persona)
            return tasks
    except Exception:
        return []


# --- History --------------------------------------------------------------------------------

def _history_rows(persona: str | None = None) -> list[dict]:
    path = _history_path(persona)
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _append_history(rows: list[dict], persona: str | None = None) -> int:
    """Append rows whose key is not already on file. Returns how many were written.
    Idempotency lives here, so a repeated sweep or a re-merged close cannot double-count."""
    with _store_lock(persona):
        keys = {r.get("key") for r in _history_rows(persona)}
        fresh = [r for r in rows if r.get("key") and r["key"] not in keys]
        if not fresh:
            return 0
        path = _history_path(persona)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as fh:
            for r in fresh:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        return len(fresh)


def _one_off_row(t: dict, state: str) -> dict:
    closed_on = (_stamp_day(t.get("closed_at")) or _today()).isoformat()
    due = _d(t.get("due"))
    row = {"key": f"{t['id']}@{closed_on}", "task_id": t["id"], "kind": t.get("kind"),
           "occurrence": t["id"], "state": state, "closed_on": closed_on,
           "recorded_at": _stamp()}
    if t.get("domain"):
        row["domain"] = t["domain"]
    if due:
        row["due"] = due.isoformat()
        row["late"] = bool(state == "done" and _d(closed_on) and _d(closed_on) > due)
    if any(h.get("event") == "rescheduled" for h in t.get("history") or []
           if isinstance(h, dict)):
        row["rescheduled"] = True
    return row


def _new_id(what: str) -> str:
    # Shape is ob_YYMMDD_<6 hex>: readable date up front, collision tail behind it.
    # The digest covers the full second-resolution stamp, not just the date, so two
    # obligations opened the same day with identical text still get distinct ids.
    # A random salt as well since the ledger landed: tests and fan-out threads can open two
    # tasks inside one second, and a shared id would make one of them unreachable.
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    digest = hashlib.sha256(f"{stamp}|{what}|{os.urandom(4).hex()}".encode()).hexdigest()[:6]
    return f"ob_{stamp[2:8]}_{digest}"


# Returning None is a real signal, not a lazy default. `update_task` branches on it to
# produce its "no task with id ..." error, which is what tells a session it has quoted an id that does not exist rather than silently
# doing nothing. Anything that made a miss indistinguishable from a hit — raising, or
# returning an empty dict — would take that message away.
def _find(items: list[dict], obligation_id: str) -> dict | None:
    for it in items:
        if it.get("id") == obligation_id:
            return it
    return None


def _summarise(it: dict) -> str:
    bits = [it.get("what", "?")]
    kind = it.get("kind")
    if kind == "habit":
        times = _habit_target(it)
        mdays = _month_window(it)
        days = (f"the {_ordinal(mdays[0])} to the {_ordinal(mdays[-1])}" if mdays
                else ",".join(str(d) for d in it.get("on_days") or []))
        bits.append(f"{times}× per {it.get('every', 'day')}" + (f" ({days})" if days else ""))
    elif kind == "interval":
        bits.append(f"every {it.get('interval_days')} days")
    elif kind == "waiting" and it.get("waiting_on"):
        bits.append(f"waiting on {it['waiting_on']}")
    if it.get("due"):
        bits.append(f"due {it['due']}")
    if it.get("domain"):
        bits.append(str(it["domain"]))
    return " — ".join(bits)


# --- Matching -------------------------------------------------------------------------------
# The ledger's own matcher, deliberately NOT context_tracker's thread identity. That one was
# tuned for thread-against-thread: its generic list strips "chase" (as in "chase someone up")
# and its stemmer leaves "pay"/"paid" apart, so "paid the Chase bill" shared ONE anchor with
# "Pay Chase bill" — below the two it needs. Found by the plan review before a line was
# written. Here the generic words are the verbs that are the *shape* of a to-do, and the
# object and brand nouns — chase, bill, card, physio, plants — are what identify one.

_WORD_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")

_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "of", "to", "for", "in", "on", "at", "by",
    "with", "from", "into", "onto", "about", "as", "up", "out", "off", "over", "it", "its",
    "this", "that", "these", "those", "there", "here", "is", "are", "was", "were", "be",
    "been", "being", "am", "has", "have", "had", "i", "me", "my", "mine", "we", "our", "us",
    "you", "your", "he", "she", "him", "her", "they", "them", "their", "his", "hers", "so",
    "just", "also", "too", "very", "all", "some", "any", "now", "then", "than", "yes", "no",
    "ok", "okay", "yeah", "yep", "thanks", "thank", "please", "what", "which", "who", "how",
    "when", "where", "why", "can", "could", "would", "should", "will", "shall", "may",
    "might", "must", "not", "dont", "didnt", "im", "ive", "ill", "id", "re", "ll", "ve",
    "still", "yet", "havent", "hasnt", "wont", "cant", "isnt", "wasnt", "really", "maybe",
    "one", "bit", "lot", "got", "get",
}

# Past tenses and participles a suffix rule cannot reach, mapped to the base form.
_IRREGULAR = {
    "paid": "pay", "payment": "pay", "payments": "pay", "sent": "send", "did": "do",
    "done": "do", "doing": "do", "bought": "buy", "got": "get", "gotten": "get",
    "came": "come", "went": "go", "gone": "go", "made": "make", "took": "take",
    "taken": "take", "wrote": "write", "written": "write", "met": "meet", "brought": "bring",
    "told": "tell", "found": "find", "left": "leave", "kept": "keep", "gave": "give",
    "given": "give", "ran": "run", "spoke": "speak", "spoken": "speak", "sold": "sell",
    "saw": "see", "seen": "see", "fed": "feed", "drove": "drive", "driven": "drive",
    "rang": "ring", "rung": "ring", "ate": "eat", "eaten": "eat", "swam": "swim",
    "swum": "swim", "forgot": "forget", "forgotten": "forget", "submitted": "submit",
    "submitting": "submit", "booked": "book", "booking": "book", "bookings": "book",
}

# The to-do verbs and time words. They say what kind of thing a task is, never which one.
_TODO_GENERIC = {
    "pay", "send", "book", "call", "check", "submit", "finish", "do", "make", "get", "buy",
    "sort", "handle", "complete", "arrange", "schedule", "review", "confirm", "follow",
    "remind", "reminder", "need", "go", "take", "set", "plan", "finalise", "finalize",
    "organise", "organize", "fill", "sign", "post", "drop", "pick", "collect", "start",
    "try", "remember", "ask", "tell", "reply", "respond", "email", "update", "look", "see",
    "give", "bring", "come", "put", "keep", "thing", "stuff", "task", "item", "today",
    "tomorrow", "yesterday", "tonight", "morning", "afternoon", "evening", "night", "week",
    "weekend", "month", "year", "later", "soon", "next", "last", "already", "due", "overdue",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "every",
    "daily", "weekly", "monthly", "time", "times", "again",
}

_YEAR_RE = re.compile(r"^(19|20)\d\d$")


def _tstem(w: str) -> str:
    """Strip one regular suffix, consistently on both sides. Producing real words is not the
    point; that "stretches", "stretching" and "stretch" all land on one token is."""
    if w.endswith("ies") and len(w) - 3 >= 3:
        return w[:-3] + "y"
    for suf in ("ing", "ed"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            base = w[: -len(suf)]
            # "shopping"/"shopped" -> "shop", not "shopp"; "billed" keeps its double l.
            if len(base) >= 4 and base[-1] == base[-2] and base[-1] not in "aeiouls":
                base = base[:-1]
            return base
    if w.endswith("es") and len(w) - 2 >= 3 and w[:-2].endswith(("s", "x", "z", "ch", "sh")):
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss") and len(w) - 1 >= 3:
        return w[:-1]
    return w


def _task_tokens(text: str) -> frozenset[str]:
    """The identifying tokens of a task's words, or of a sentence that might be about one."""
    out: set[str] = set()
    for raw in _WORD_RE.findall((text or "").lower()):
        w = raw.replace("'s", "").replace("'", "")
        if not w or w in _STOPWORDS:
            continue
        if w.isdigit():
            # An amount or a house number identifies; a year or a day-of-month does not.
            if len(w) >= 3 and not _YEAR_RE.match(w):
                out.add(w)
            continue
        w = _IRREGULAR.get(w, w)
        # Generic before AND after stemming: "morning" must not survive as "morn".
        if w in _TODO_GENERIC:
            continue
        w = _IRREGULAR.get(_tstem(w), _tstem(w))
        if len(w) < 3 or w in _TODO_GENERIC or w in _STOPWORDS:
            continue
        out.add(w)
    return frozenset(out)


def _tokens_match(text_tokens: frozenset, task_tokens: frozenset,
                  single_ok: bool = False) -> bool:
    """Is this text about this task? Two shared identifying tokens, or identical sets.

    `single_ok` also accepts a task whose WHOLE identity is one token ("Stretching", "Gym")
    when the text shares it. Only the hint and the raise-once stamp use it — a false positive
    there costs one question or one suppressed repeat. Annotating a log or thread never does.
    """
    if not text_tokens or not task_tokens:
        return False
    if text_tokens == task_tokens:
        return True
    if len(text_tokens & task_tokens) >= 2:
        return True
    return bool(single_ok and len(task_tokens) == 1 and task_tokens <= text_tokens)


def _same_commitment(a: str, b: str) -> bool:
    """The open-duplicate guard v1 shipped with (exact, or one containing the other past 12
    characters), plus identical token sets — 'Pay the Chase bill' vs 'Chase bill: pay'."""
    la, lb = (a or "").strip().lower(), (b or "").strip().lower()
    if not la or not lb:
        return False
    if la == lb or (len(la) > 12 and la in lb) or (len(lb) > 12 and lb in la):
        return True
    ta, tb = _task_tokens(la), _task_tokens(lb)
    return bool(ta) and ta == tb


def _open_duplicate(tasks: list[dict], what: str) -> dict | None:
    for t in tasks:
        if t.get("status") == "open" and not _is_step(t) and _same_commitment(t.get("what", ""), what):
            return t
    return None


def _open_near(tasks: list[dict], what: str) -> dict | None:
    """An open task sharing two identifying words with `what` (_tokens_match)."""
    new = _task_tokens(what)
    for t in tasks:
        if (t.get("status") == "open" and not _is_step(t)
                and _tokens_match(new, _task_tokens(t.get("what", "")))):
            return t
    return None


def _recent_close_match(tasks: list[dict], what: str, today: date) -> dict | None:
    new = _task_tokens(what)
    for t in tasks:
        if t.get("status") not in _TERMINAL or t.get("kind") not in _ONE_OFF or _is_step(t):
            continue
        closed = _stamp_day(t.get("closed_at"))
        if not closed or (today - closed).days > _RECLOSE_WINDOW_DAYS:
            continue
        if _same_commitment(t.get("what", ""), what) or _tokens_match(new, _task_tokens(t["what"])):
            return t
    return None


def _is_parked(t: dict) -> bool:
    """Parked by the back burner and still parked: moot, closed the day it was parked. A parked
    task reopened by any path (reopen, reschedule, done after all) and later closed another way
    keeps a stale `back_burner` marker; the closing day tells them apart (Fable diff review #5)."""
    bb = t.get("back_burner") or {}
    return (t.get("status") == "moot" and bool(bb.get("at"))
            and str(t.get("closed_at") or "")[:10] == str(bb.get("at")))


def _parked_match(tasks: list[dict], what: str, kind: str) -> tuple[dict | None, dict | None]:
    """(the parked task `what` is the same commitment as, a parked task it only resembles). A
    one-off only. The same commitment is revived (B26); a resemblance — two words shared — is put
    back to the model to decide, never revived on its own (Fable diff review #4: "a birthday card
    for Mum" must not bring back last year's card for the office)."""
    if kind not in _ONE_OFF:
        return None, None
    new = _task_tokens(what)
    near = None
    for t in tasks:
        if not _is_parked(t) or _is_step(t) or t.get("kind") not in _ONE_OFF:
            continue
        if _same_commitment(t.get("what", ""), what):
            return t, None
        if near is None and _tokens_match(new, _task_tokens(t["what"])):
            near = t
    return None, near


def _revive(t: dict, due: str | None, note: str | None, today: date) -> str:
    """Reopen a parked task on a fresh mention: open again, its history kept and the parking
    recorded in it, mentioned today (so its 21 days start over)."""
    was = t.pop("back_burner", None) or {}
    t["status"] = "open"
    t.pop("closed_at", None)
    t.pop("evidence", None)
    t["mentioned"] = today.isoformat()
    if due and _d(due):
        t["due"] = _d(due).isoformat()
    if note:
        t["note"] = str(note).strip()
    t.setdefault("history", []).append({"event": "reopened", "at": _stamp(), "was": "moot",
                                        "reason": "mentioned again (back burner)",
                                        "parked_on": was.get("at")})
    return (f"task {t['id']} reopened from the back burner (parked {was.get('at') or '?'}): "
            f"{_summarise(t)}. Not filed twice — update_task on {t['id']} for anything else.")


def _source_duplicate(tasks: list[dict], source_id: str, today: date) -> dict | None:
    for t in tasks:
        if not source_id or t.get("source_id") != source_id:
            continue
        if t.get("status") == "open":
            return t
        closed = _stamp_day(t.get("closed_at"))
        if closed and (today - closed).days <= _SOURCE_WINDOW_DAYS:
            return t
    return None


# --- Periods and the derived view -----------------------------------------------------------

def _period(every: str, d: date) -> tuple[str, date, date]:
    """(key, first day, last day) of the period containing d. Weeks are ISO, Monday first."""
    if every == "week":
        start = d - timedelta(days=d.weekday())
        y, w, _ = d.isocalendar()
        return f"{y}-W{w:02d}", start, start + timedelta(days=6)
    if every == "month":
        start = d.replace(day=1)
        end = (start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        return f"{d.year}-{d.month:02d}", start, end
    return d.isoformat(), d, d


def _start(t: dict) -> date | None:
    return _d(t.get("start")) or _d(t.get("created_at"))


def _interval_due(t: dict, today: date) -> date:
    nd = _d(t.get("next_due"))
    if nd:
        return nd
    last = _d(t.get("last_done"))
    n = max(1, int(t.get("interval_days") or 1))
    if last:
        return last + timedelta(days=n)
    return _start(t) or today


def _check_back(t: dict) -> date:
    cb = _d(t.get("check_back")) or _d(t.get("due"))
    if cb:
        return cb
    return (_start(t) or _today()) + timedelta(days=_DEFAULT_CHECK_BACK_DAYS)


def _when(d: date, today: date) -> str:
    delta = (d - today).days
    if delta == 0:
        return "today"
    if delta == 1:
        return "tomorrow"
    if delta == -1:
        return "yesterday"
    return f"{d.isoformat()} ({_WEEKDAYS[d.weekday()].capitalize()})"


def _month_window(t: dict) -> list[int]:
    """A monthly habit's days of the month (the Chase bill: 10–15), sorted, or [] (Mike,
    2026-10-25: "needs to be paid by the 15th and normally I don't want to deal with it until about
    the 10th"). Planned from the first, due by the last, overdue after it (plan § 18, R2-10)."""
    if t.get("every") != "month":
        return []
    out = set()
    for d in t.get("on_days") or []:
        try:
            n = int(d)
        except (TypeError, ValueError):
            continue
        if 1 <= n <= 31:
            out.add(n)
    return sorted(out)


def _ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _habit_target(t: dict) -> int:
    times = t.get("times")
    try:
        times = int(times)
    except (TypeError, ValueError):
        times = 0
    if times < 1:
        times = len(t.get("on_days") or []) if t.get("every") == "week" else 1
    return max(1, times)


def _completion_dates(occ: dict) -> list[date]:
    out = []
    for c in occ.get("completions") or []:
        d = _d((c or {}).get("on") or (c or {}).get("at"))
        if d:
            out.append(d)
    return out


# How long a task takes, so the scheduling build-out can place it in a day (Mike, 2026-10-24:
# "Tasks should have a time amount or inferred/estimated time, so that the scheduling can work
# with them effectively"). `minutes_source` says whose number it is: "stated" by the user, or
# "estimated" by a model until the user corrects it — a guess must never read as a fact.
_MINUTES_SOURCES = ("stated", "estimated")
_MAX_TASK_MINUTES = 24 * 60


def _minutes_arg(minutes, source) -> tuple[dict, str | None]:
    try:
        n = int(round(float(minutes)))
    except (TypeError, ValueError):
        return {}, "error: `minutes` must be a number of minutes. Nothing was written."
    if not 1 <= n <= _MAX_TASK_MINUTES:
        return {}, f"error: `minutes` must be between 1 and {_MAX_TASK_MINUTES}. Nothing was written."
    src = (source or "estimated").strip().lower()
    if src not in _MINUTES_SOURCES:
        return {}, (f"error: `minutes_source` must be one of {', '.join(_MINUTES_SOURCES)}, not "
                    f"{source!r}. Nothing was written.")
    return {"minutes": n, "minutes_source": src}, None


def _minutes_suffix(t: dict) -> str:
    n = t.get("minutes")
    if not n:
        return ""
    return f" (~{n} min" + (", estimated)" if t.get("minutes_source") != "stated" else ")")


def _view(t: dict, today: date, lead_days: int = _LEAD_DAYS) -> dict:
    """What this task is today, with its length appended when one is known."""
    v = _view_core(t, today, lead_days)
    if t.get("status", "open") == "open" and t.get("minutes"):
        v["text"] = v["text"] + _minutes_suffix(t)
    return v


def _view_core(t: dict, today: date, lead_days: int = _LEAD_DAYS) -> dict:
    """
    What this task is today. Pure: computed from the record and the date, nothing stored, so
    the block is right even on a day the sweep never ran.

    Returns {id, occ, kind, state, actionable, sort, text}. `actionable` is "belongs under
    Now"; `state` is one of the stored terminal states or a derived one (dormant, open,
    due_today, overdue, upcoming, later, waiting, waiting_due, satisfied, skipped).
    """
    tid, kind, status = t["id"], t.get("kind", "deadline"), t.get("status", "open")
    what = t.get("what", "?")
    v = {"id": tid, "occ": tid, "kind": kind, "state": status, "actionable": False,
         "sort": (9,), "text": what}
    if status != "open":
        return v
    if t.get("_blocked"):
        # Waiting on an earlier step (§ 4.1): hidden exactly as `dormant` is — not on Today, not
        # a planner candidate, not under Now — until the step it needs is done.
        v["state"] = "blocked"
        return v
    start = _start(t)
    eligible = _d(t.get("eligible_from"))
    if (eligible and eligible > today) or (start and start > today and kind == "habit"):
        v["state"] = "dormant"
        return v
    moot = _d(t.get("moot_after"))
    if kind in _ONE_OFF and moot and today > moot:
        v["state"] = "moot"
        return v

    if kind == "deadline":
        raw_due = str(t.get("due") or "").strip()
        due = _d(raw_due)
        if not raw_due:
            v.update(state="open", actionable=True, sort=(5, 2, what.lower()), text=what)
        elif due is None:
            # A vague due on a legacy row. Any stated urgency outranks none.
            v.update(state="open", actionable=True, sort=(5, 1, raw_due.lower()),
                     text=f"{what} — due {raw_due}")
        elif due < today and _unconfirmed_rule() and not is_essential(t):
            # F10 (Mike, 2026-10-24): a non-essential deadline past its date is never raised as
            # overdue. It stays open — "overdue until done or dismissed" (ledger decision 4) now
            # governs essential deadlines — and the planner may still place it, low.
            v.update(state="lapsed", sort=(8, due.isoformat()),
                     text=f"{what} — past its date ({due.isoformat()}), unconfirmed")
        elif due < today:
            v.update(state="overdue", actionable=True, sort=(0, due.isoformat()),
                     text=f"{what} — overdue since {due.isoformat()}")
        elif due == today:
            v.update(state="due_today", actionable=True, sort=(1, due.isoformat()),
                     text=f"{what} — due today" + (f", after {t['after']}" if t.get("after") else "")
                          + (f", before {t['before']}" if t.get("before") else ""))
        elif t.get("flexible"):
            # Any day up to its date (Mike, 2026-10-27): the planner places it on a day with
            # room, and it is a must-do only on its last day.
            v.update(state="in_window", actionable=True, sort=(3, due.isoformat()),
                     text=f"{what} — any day by {_when(due, today)}"
                          + (f", after {t['after']}" if t.get("after") else ""))
        elif (due - today).days <= lead_days:
            v.update(state="upcoming", actionable=True, sort=(2, due.isoformat()),
                     text=f"{what} — due {_when(due, today)}")
        else:
            v.update(state="later", sort=(8, due.isoformat()),
                     text=f"{what} — due {due.isoformat()}")
        if t.get("domain") and v["actionable"]:
            v["text"] += f" ({t['domain']})"
        return v

    if kind == "waiting":
        cb = _check_back(t)
        who = str(t.get("waiting_on") or "someone else").strip()
        since = start.isoformat() if start else "?"
        if today >= cb:
            v.update(state="waiting_due", actionable=True, sort=(4, cb.isoformat()),
                     text=f"{what} — waiting on {who} since {since}; nothing recorded yet. "
                          f"Someone else's move, not the user's: ask whether it has come, "
                          f"never present it as overdue")
        else:
            v.update(state="waiting", sort=(8, cb.isoformat()),
                     text=f"{what} — waiting on {who}; check back {cb.isoformat()}")
        return v

    if kind == "interval":
        due = _interval_due(t, today)
        n = max(1, int(t.get("interval_days") or 1))
        last = _d(t.get("last_done"))
        last_txt = f"last done {last.isoformat()}" if last else "no completion recorded yet"
        v["occ"] = f"{tid}@{due.isoformat()}"
        if due <= today:
            v.update(state="overdue" if due < today else "due_today", actionable=True,
                     sort=(0 if due < today else 1, due.isoformat()),
                     text=f"{what} — due {'since ' + due.isoformat() if due < today else 'today'}"
                          f" (every {n} days; {last_txt})")
        else:
            v.update(state="later", sort=(8, due.isoformat()),
                     text=f"{what} — next due {due.isoformat()} (every {n} days; {last_txt})")
        return v

    # habit
    every = t.get("every") if t.get("every") in _EVERY else "day"
    target = _habit_target(t)
    pk, ps, pe = _period(every, today)
    occ = (t.get("occurrences") or {}).get(pk) or {}
    done = int(occ.get("done") or 0)
    v["occ"] = f"{tid}@{pk}"
    if occ.get("skipped"):
        v.update(state="skipped", text=f"{what} — skipped this {every}")
        return v
    if done >= target:
        v.update(state="satisfied", text=f"{what} — {done} of {target} this {every}, done")
        return v
    remaining = target - done
    if every == "day":
        label = f"{what} — today" if target == 1 else f"{what} — {done} of {target} today"
        v.update(state="due_today", actionable=True, sort=(3, what.lower()), text=label)
        return v
    mdays = _month_window(t)
    if mdays:
        return _view_month_window(v, t, today, what, mdays, done, target, ps, pe, start)
    days_left = (pe - today).days + 1
    first = max(ps, start) if start else ps
    preferred = [d for d in (t.get("on_days") or []) if d in _WEEKDAYS] if every == "week" else []
    today_wd = _WEEKDAYS[today.weekday()]
    # The first period, when the task started part-way through it, is excluded from adherence
    # (the sweep marks it `partial`), so it must not nag either: a 3x-a-week quota set up on a
    # Saturday read "needed today to stay on target" (2026-10-24).
    partial = bool(start and start > ps)
    # F10: a non-essential quota triggers no make-ups — no "missed day can be made up", no
    # "needed today to stay on target". Its planned days still show; nothing chases the rest.
    no_makeup = _unconfirmed_rule() and not is_essential(t)
    at_risk = remaining >= days_left and not partial and not no_makeup
    planned = False
    notes: list[str] = []
    if preferred:
        elapsed = sum(1 for i in range((today - first).days)
                      if _WEEKDAYS[(first + timedelta(days=i)).weekday()] in preferred)
        behind = done < min(elapsed, target) and not no_makeup
        planned = today_wd in preferred
        actionable = planned or behind or at_risk
        if planned:
            notes.append("today is a planned day")
        if behind:
            notes.append("a missed planned day can be made up today")
    else:
        spacing = max(1, ((pe - ps).days + 1) // target)
        dates = [d for d in _completion_dates(occ) if ps <= d <= pe]
        last = max(dates) if dates else None
        actionable = at_risk or last is None or (today - last).days >= spacing
    if at_risk:
        notes.append("needed today to stay on target")
    text = f"{what} — {done} of {target} this {every}"
    if notes:
        text += "; " + "; ".join(notes)
    v.update(state="due_today" if actionable else "later", actionable=actionable,
             sort=(3, what.lower()), text=text,
             # For the app's waking-day list (today_items), which is narrower than Now.
             quota={"planned": planned, "at_risk": at_risk, "partial": partial})
    return v


def _view_month_window(v: dict, t: dict, today: date, what: str, mdays: list[int], done: int,
                       target: int, ps: date, pe: date, start: date | None) -> dict:
    """A monthly habit with days of the month: nothing before its first day, planned on every day
    of the window, OVERDUE after its last until the month ends (review F4 — without this the Chase
    bill vanished from the 16th). A month the habit was set up after its window had closed owes
    nothing, so it does not nag (the partial-period rule)."""
    n_days = (pe - ps).days + 1
    window = sorted({min(d, n_days) for d in mdays})
    opens, by = ps.replace(day=window[0]), ps.replace(day=window[-1])
    span = f"the {_ordinal(window[0])} to the {_ordinal(window[-1])}"
    late_start = bool(start and start > by)
    if late_start or today < opens:
        v.update(state="later", sort=(8, opens.isoformat()),
                 text=f"{what} — {span} each month" + ("; this month's window had closed when it "
                                                       "was set up" if late_start else ""),
                 quota={"planned": False, "at_risk": False, "partial": late_start})
        return v
    if today > by:
        v.update(state="overdue", actionable=True, sort=(0, by.isoformat()),
                 text=f"{what} — due by the {_ordinal(window[-1])}, nothing recorded this month",
                 quota={"planned": False, "at_risk": False, "partial": False})
        return v
    left = (by - today).days + 1
    at_risk = (target - done) >= left
    text = f"{what} — {done} of {target} this month, {span}"
    if left == 1:
        text += "; due today"
    elif at_risk:
        text += "; needed today to stay on target"
    v.update(state="due_today", actionable=True, sort=(1 if left == 1 else 3, what.lower()),
             text=text, quota={"planned": True, "at_risk": at_risk,
                               "partial": bool(start and start > ps)})
    return v


def _raised_today(t: dict, occ: str, today: date) -> str | None:
    """When this occurrence was raised today, as HH:MM, or None."""
    stamp = str((t.get("raised") or {}).get(occ) or "")
    if stamp and _stamp_day(stamp) == today:
        return stamp[11:16] or "earlier"
    return None


# --- Tools ----------------------------------------------------------------------------------

def _split_id(task_id: str) -> str:
    return (task_id or "").strip().strip("`").split("@", 1)[0]


def _clean_monthdays(parts: list) -> tuple[list[int], str | None]:
    """Days of the month: 10, "15", "10-15", "10th". Sorted, unique, 1–31."""
    out: set[int] = set()
    for raw in parts:
        text = re.sub(r"(st|nd|rd|th)\b", "", str(raw).strip().lower())
        bits = text.split("-")
        try:
            lo, hi = (int(bits[0]), int(bits[-1])) if len(bits) in (1, 2) else (0, 0)
        except ValueError:
            lo = hi = 0
        if not (1 <= lo <= hi <= 31):
            return [], (f"error: a monthly habit's `on_days` are days of the month (\"10\", "
                        f"\"10-15\"), not {raw!r}. Nothing was written.")
        out.update(range(lo, hi + 1))
    return sorted(out), None


def _clean_days(on_days, every: str | None = None) -> tuple[list, str | None]:
    if not on_days:
        return [], None
    if isinstance(on_days, (str, int)):
        on_days = [p for p in re.split(r"[,\s/]+", str(on_days)) if p]
    if every == "month" and _ledger_fields():
        # Days of the month are a planner field (review F9): off, a monthly habit's days are
        # refused exactly as before, so nothing a model guesses changes the ledger.
        return _clean_monthdays(on_days)
    out = []
    for raw in on_days:
        d = str(raw).strip().lower()[:3]
        if d not in _WEEKDAYS:
            return [], (f"error: `on_days` takes weekday names (mon … sun), not {raw!r}. "
                        f"Nothing was written.")
        if d not in out:
            out.append(d)
    return out, None


def open_task(what: str, kind: str = "deadline", due: str | None = None,
              eligible_from: str | None = None, moot_after: str | None = None,
              every: str | None = None, times: int | None = None, on_days=None,
              interval_days: int | None = None, last_done: str | None = None,
              waiting_on: str | None = None, expect_from: str | None = None,
              check_back: str | None = None, domain: str | None = None,
              note: str | None = None, source_id: str | None = None,
              calendar_uid: str | None = None, new_instance: bool = False,
              minutes: int | None = None, minutes_source: str | None = None,
              goal_id: str | None = None, priority: str | None = None,
              priority_source: str | None = None, stakes: str | None = None,
              stakes_source: str | None = None, zone: str | None = None,
              activity: str | None = None, flexible: bool | None = None,
              stakes_why: str | None = None,
              after: str | None = None, done_words=None,
              costs=None, bears: str | None = None, shape: str | None = None,
              real_due: str | None = None, costs_source: str | None = None,
              costs_why: str | None = None, medication: str | None = None,
              enjoyed: bool | None = None, passion: str | None = None) -> str:
    """Record something the user has to do, or is waiting on, so it is tracked until done."""
    what = (what or "").strip()
    if not what:
        return "error: `what` is required — a task with no description cannot be closed later"
    kind = (kind or "deadline").strip().lower()
    if kind not in KINDS:
        return f"error: `kind` must be one of {', '.join(KINDS)}, not {kind!r}. Nothing was written."
    med_name = None
    if str(medication or "").strip():
        # A dose habit is linked to its profile entry by name, checked here — the only marker
        # the medication view reads (see "Medication taken" below). Who may set it is checked
        # first, so a caller outside the health view learns nothing about the profile.
        if not _may_set_link():
            return _LINK_REFUSAL
        if kind != "habit":
            return ("error: `medication` links a habit to the user's medication profile — "
                    f"this is a {kind}. Nothing was written.")
        med_name, err = _medication_link(medication)
        if err:
            return err

    dates = {}
    for name, value in (("due", due), ("eligible_from", eligible_from),
                        ("moot_after", moot_after), ("last_done", last_done),
                        ("check_back", check_back)):
        iso, err = _iso_arg(name, value)
        if err:
            return err
        if iso:
            dates[name] = iso
    days, err = _clean_days(on_days, (every or "").strip().lower() if kind == "habit" else None)
    if err:
        return err

    entry: dict = {"what": what, "kind": kind, "status": "open"}
    words = _clean_done_words(done_words)
    if words and kind in ("habit", "interval"):
        entry["done_words"] = words
    if kind == "habit":
        every = (every or "").strip().lower()
        if every not in _EVERY:
            return ("error: a habit needs `every` — day, week or month (gym three times a week "
                    "is every=week, times=3). Nothing was written.")
        entry["every"] = every
        if times is not None:
            try:
                entry["times"] = max(1, int(times))
            except (TypeError, ValueError):
                return "error: `times` must be a whole number. Nothing was written."
        if days and every in ("week", "month"):
            entry["on_days"] = days
    elif kind == "interval":
        try:
            n = int(interval_days)
        except (TypeError, ValueError):
            n = 0
        if n < 1:
            return ("error: an interval task needs `interval_days` (water the plants every 3 "
                    "days is interval_days=3). Nothing was written.")
        entry["interval_days"] = n
    if kind == "waiting":
        if waiting_on:
            entry["waiting_on"] = waiting_on.strip()
        if expect_from:
            entry["expect_from"] = expect_from.strip()
    for name, iso in dates.items():
        if name == "last_done" and kind != "interval":
            continue
        entry[name] = iso
    if domain:
        entry["domain"] = domain.strip()
    if med_name:
        entry["medication"] = med_name
    if note:
        entry["note"] = note.strip()
    if source_id:
        entry["source_id"] = str(source_id).strip()
    if calendar_uid:
        entry["calendar_uid"] = str(calendar_uid).strip()
    if not _ledger_fields():
        # Not in the schema while the flag is off; a model that guesses one changes nothing.
        goal_id = priority = stakes = zone = activity = enjoyed = None
    plan, err = _plan_fields(kind, goal_id=goal_id or None, priority=priority or None,
                             priority_source=priority_source, stakes=stakes or None,
                             stakes_source=stakes_source, zone=zone or None,
                             activity=activity or None, stakes_why=stakes_why,
                             windowed=bool(_month_window(entry)), enjoyed=enjoyed or None)
    if err:
        return err
    entry.update({k: v for k, v in plan.items() if v is not None})
    if _cost_record():
        # The cost record (ranking § 10 R1) — beside stakes, never writing them.
        rec, err = _cost_fields(kind, costs=costs, bears=bears, shape=shape, real_due=real_due,
                                passion=passion,
                                costs_source=costs_source, costs_why=costs_why)
        if err:
            return err
        entry.update({k: v for k, v in rec.items() if v is not None})
    if _ledger_fields():
        win, err = _window_fields(kind, entry.get("due"), flexible, after)
        if err:
            return err
        entry.update(win)
    if minutes is not None:
        dur, err = _minutes_arg(minutes, minutes_source)
        if err:
            return err
        entry.update(dur)

    def apply(doc: dict) -> str:
        tasks = doc["tasks"]
        today = _today()
        if source_id:
            dup = _source_duplicate(tasks, entry["source_id"], today)
            if dup:
                return (f"already tracked from the same message as {dup['id']} "
                        f"({dup.get('status')}): {_summarise(dup)}. Not filed twice.")
        dup = _open_duplicate(tasks, what)
        if dup:
            return (f"already open as {dup['id']}: {_summarise(dup)}. "
                    f"Not filed twice — update or close that one instead.")
        if med_name:
            clash = _second_link(tasks, med_name)
            if clash:
                return clash
        if not new_instance:
            # Two identifying words shared with an open task — the shape of a correction filed
            # as a new task (2026-10-27: "Mover claims admin" beside "Handle mover claims",
            # "Water plants and consider repotting" beside "Water indoor and garden plants").
            # Softer than the guard above: a genuinely separate task goes through on
            # new_instance. Not for a task opened from a known source (a loose end typed into
            # "Done, but…", an intake item): that one was asked for deliberately.
            near = None if source_id else _open_near(tasks, what)
            if near:
                return (f"this looks like {near['id']}, already open: {_summarise(near)}. "
                        f"Nothing was written. If the user is correcting or adding to that "
                        f"task, use update_task on {near['id']}; if this is genuinely a "
                        f"separate task, call again with new_instance=true.")
        if not new_instance and not source_id:
            # A task parked on the back burner (ranking plan § 4.11, B26) is revived by a fresh
            # mention — reopened, its row and history kept — never filed a second time.
            parked, like = _parked_match(tasks, what, kind)
            if parked:
                return _revive(parked, dates.get("due"), note, today)
            if like:
                return (f"this looks like {like['id']} ({_summarise(like)}), parked on the back "
                        f"burner {(like.get('back_burner') or {}).get('at')}. Nothing was "
                        f"written. If the user means that one, update_task reopen on "
                        f"{like['id']}; if this is genuinely a separate task, call again with "
                        f"new_instance=true.")
        if kind in _ONE_OFF and not new_instance:
            prior = _recent_close_match(tasks, what, today)
            if prior:
                return (f"this looks like {prior['id']} ({_summarise(prior)}), which was "
                        f"{prior.get('status')} on {str(prior.get('closed_at') or '?')[:10]}"
                        + (f" — \"{str(prior.get('evidence'))[:80]}\"" if prior.get('evidence') else "")
                        + ". Not filed again. If this is genuinely a new instance, call again "
                          "with new_instance=true.")
        if source_id:
            entry.update(_resolve_source(entry["source_id"]))
        entry["id"] = _new_id(what)
        entry["created_at"] = _stamp()
        entry.setdefault("start", today.isoformat())
        tasks.append(entry)
        msg = f"task {entry['id']} opened ({kind}): {_summarise(entry)}"
        if med_name:
            n = _import_logged_doses(entry, today)
            if n:
                msg += f"; {n} dose(s) already logged as taken today counted on it"
        open_one_offs = sum(1 for t in tasks if t.get("status") == "open"
                            and t.get("kind") in _ONE_OFF and not _is_step(t))
        if kind in _ONE_OFF and open_one_offs > _SOFT_CAP:
            msg += (f"\n\nNOTE: {open_one_offs} one-off tasks are now open, past the {_SOFT_CAP} "
                    f"this store is sized for. Written anyway. Several are probably done and "
                    f"unclosed — worth asking about the oldest rather than carrying them all.")
        return msg

    result = _with_store(None, apply)
    if result.startswith("task ") and calendar_uid is None:
        _link_calendar_if_exact(result.split()[1])
        if kind == "deadline":
            # A precursor stated in chat ("bring my old passport to tomorrow's appointment") is
            # linked to the event it is about, so it follows the event (goal–task network
            # phase 2, the 2026-11-21 gap). Never fails the open.
            try:
                from tools.day_plan import link_prep_from_chat
                title = link_prep_from_chat(result.split()[1])
                if title:
                    result += f" — linked to {title}; it moves if that event moves"
            except Exception as exc:  # noqa: BLE001
                logger.warning("[tasks] event link skipped: %s", exc)
    return result


def _evidence_arg(evidence) -> str:
    return (evidence or "").strip()


def _set_minutes(task_id: str, minutes, source) -> str:
    """Record or correct how long a task takes. A stated length is never overwritten by an
    estimate — the user's number outranks a model's guess."""
    if minutes is None:
        return "error: `minutes` is required for set_minutes. Nothing was written."
    dur, err = _minutes_arg(minutes, source)
    if err:
        return err
    tid = _split_id(task_id)

    def apply(doc: dict) -> str:
        t = _find(doc["tasks"], tid)
        if t is None:
            return f"error: no task with id {task_id!r}"
        if t.get("minutes_source") == "stated" and dur["minutes_source"] == "estimated":
            return (f"{tid} keeps the user's own figure, {t.get('minutes')} min — an estimate "
                    f"does not replace it")
        t.update(dur)
        return f"{tid} takes ~{dur['minutes']} min ({dur['minutes_source']}): {_summarise(t)}"
    return _with_store(None, apply)


# --- What the day planner reads off a task (archive/plans/day_planner_plan_2026-10-24.md § 4.1) --
# Priority and deadline stakes live HERE, on the task, so there is one place to read them (Mike:
# "perhaps having them in one place with the task ledger makes sense"). Each carries whose number
# it is, exactly as `minutes` does: the user's word ("stated") is never replaced by a model's
# inference. The schema parts that let a model set them are hidden behind the `ledger_fields`
# flag until the Synthesizer's conduct for them exists (review R1-1) — see task_schemas().

# `defer` rides with these although it is not the planner's: the shipped schemas are pinned byte
# for byte while `ledger_fields` is off (tests/test_day_plan_ledger.py), so an action added to
# them would be a change to what every flag-off agent sees. Off, a deferred task still stays
# dormant — `_view` reads `eligible_from` whatever the flag says — so a rollback hides nothing.
_PLAN_ACTIONS = ("link_goal", "set_priority", "set_stakes", "set_zone", "day_starts", "set_days",
                 "set_activity", "set_window", "defer")
_PRIORITIES = ("high", "normal", "low")
_STAKES = ("vital", "missable")
_FIELD_SOURCES = ("stated", "inferred")

# Medication is essential whatever else is true (Mike, F10: "medication always essential"). A
# model is ALSO told to mark it, but a safety property resting only on a model remembering to is
# the 2026-08-04 lesson (a flag no test exercised was structurally unfireable). This net errs
# toward essential: a false positive costs one completion check, a false negative a missed dose
# recorded as merely "unconfirmed".
_MEDICATION_RE = re.compile(
    r"\b(medications?|medicines?|meds|pills?|tablets?|capsules?|doses?|dosage|inhalers?|"
    r"insulin|prescriptions?|antibiotics?|injections?|eye ?drops)\b", re.IGNORECASE)

_GOAL_CACHE: dict = {"key": None, "index": {}}


def _goal_index() -> dict[str, dict]:
    """The persona's goals by id, across horizons. Empty on any failure — a goal that cannot be
    read makes nothing essential, and the deadline and medication rules still apply."""
    try:
        from tools.goals import _goals_path
        path = _goals_path()
        key = (str(path), path.stat().st_mtime_ns)
    except Exception:  # noqa: BLE001
        return {}
    if _GOAL_CACHE["key"] == key:
        return _GOAL_CACHE["index"]
    index: dict[str, dict] = {}
    try:
        from tools.goals import HORIZONS     # gains `long` in phase 2 (§ 10 R6) — read, not copied
        doc = yaml.safe_load(path.read_text()) or {}
        for horizon in HORIZONS:
            for g in doc.get(horizon) or []:
                if isinstance(g, dict) and g.get("id"):
                    index[str(g["id"])] = g
    except Exception:  # noqa: BLE001
        index = {}
    _GOAL_CACHE.update(key=key, index=index)
    return index


def _goal_hash(goal: dict) -> str:
    return hashlib.sha256(json.dumps(goal, sort_keys=True, default=str).encode()).hexdigest()[:12]


# How long a task may stay unjudged before it counts as vital again (Fable diff review 11-22 #1).
# The task judge normally weighs a new task within one tick (~5 min); past this, something is
# wrong — the judge failing, capped or off — and an unweighed task is safer treated as vital
# (F10's original reading) than hidden on the back burner.
_JUDGE_GRACE = timedelta(minutes=60)


def stakes_of(t: dict, now: datetime | None = None) -> str | None:
    """The stakes the ranking reads: the stored value; else, for a task unjudged within the grace
    since it was opened, None (back burner); past the grace, "vital". A row with no `created_at`
    is past the grace."""
    st = t.get("stakes")
    if st:
        return st
    raw = str(t.get("created_at") or "")[:19]
    try:
        opened = datetime.fromisoformat(raw) if raw else None
    except ValueError:
        opened = None
    if opened is not None and (now or _now()) - opened < _JUDGE_GRACE:
        return None
    return "vital"


def is_required_dose(t: dict) -> bool:
    """Is this task a medication dose that must not be missed? The one test `is_essential` and the
    day plan's medication weight share.

    A habit linked to the medication profile is judged by the profile's criticality, never by its
    name (review 2026-11-23: a linked Vitamin D supplement read as essential): `required` → yes;
    `as_needed` / `optional` → no. A link whose criticality cannot be read — the profile is
    unreadable, the entry has no criticality, or the link no longer matches an entry — reads yes:
    in a hard-fail domain an unknown is never quietly demoted. A task with no link keeps the name
    net (`_MEDICATION_RE`), which is all there is for it."""
    if str(t.get("medication") or "").strip():
        crit = _criticality_of(t["medication"])
        return crit not in ("as_needed", "optional")
    return bool(_MEDICATION_RE.search(f"{t.get('what', '')} {t.get('note', '')}"))


def is_essential(t: dict, goals: dict[str, dict] | None = None) -> bool:
    """F10: essential = medication, OR explicitly high priority, OR serving an essential goal, OR a
    deadline judged vital. Derived on every read, never stored.

    AMENDED 2026-11-22 (Mike): "Tasks should be scored always, and if not vital should have a
    weaker score and be relegated to back burner. Many times user will add tasks that aren't
    important and quickly forgotten." Until then UNKNOWN stakes counted as vital (a missed tax
    deadline costs more than a lost evening) — so every chore nobody judged sat overdue at the top
    of the day for weeks, above the steps of a real tax plan. An unjudged task is now back-burner,
    and what keeps F10's tax case safe is that nothing stays unjudged for long: the agent that
    opens a task judges it (open_task's `stakes`), and tools/task_judge.py judges any it missed
    within minutes, against the user's goals and values (ranking plan § 16). If it has not within
    _JUDGE_GRACE, `stakes_of` reads it as vital again — a broken judge degrades to F10, never to a
    hidden bill."""
    if is_required_dose(t):
        return True
    if t.get("priority") == "high":
        return True
    gid = t.get("goal_id")
    if gid:
        g = (goals if goals is not None else _goal_index()).get(str(gid))
        if g and g.get("essential") is True:
            return True
    # A monthly habit with a window is a recurring deadline — a bill due by the 15th — so its
    # stakes count exactly as a deadline's do (review F4). Under `ranking_v2` the stakes are
    # derived from the cost record (ranking § 10 R1); off, Part A's stored stakes, exactly.
    return ((t.get("kind") == "deadline" or bool(_month_window(t)))
            and _stakes_read(t) == "vital")


def _ledger_fields() -> bool:
    try:
        from tools.day_plan_config import flag
        return flag("ledger_fields")
    except Exception:  # noqa: BLE001
        return False


def _back_burner() -> bool:
    """Ranking Part B phase 3: `keep` is offered while the back burner can say "park it"."""
    try:
        from tools.day_plan_config import flag
        return flag("back_burner")
    except Exception:  # noqa: BLE001
        return False


def _keep(task_id: str, evidence: str | None) -> str:
    """update_task(action="keep"): the user wants a task kept as it is — the answer to "shall it
    go on the back burner?" (ranking plan § 4.11). Recorded as a mention, so its 21 days start
    over, and the notice already said no longer counts (Fable diff review #1)."""
    ev = (evidence or "").strip()
    if not ev:
        return "error: keep needs evidence — the user's words. Nothing was written."
    tid = _split_id(task_id)

    def apply(doc: dict) -> str:
        t = _find(doc["tasks"], tid)
        if t is None:
            return f"error: no task with id {task_id!r}"
        if (t.get("status") or "open") != "open":
            return f"{tid} is not open — reopen it instead if the user wants it back"
        t["mentioned"] = _today().isoformat()
        t.setdefault("history", []).append({"event": "kept", "at": _stamp(),
                                            "evidence": ev[:200]})
        return f"{tid} kept as it is: {_summarise(t)}"
    return _with_store(None, apply)


def _cost_record() -> bool:
    """Ranking Part B (§ 10 R1): the cost record may be written and is offered in the schemas.
    Needs `ledger_fields` too — the planner's fields are the record's neighbours."""
    try:
        from tools.day_plan_config import flag
        return flag("cost_record") and flag("ledger_fields")
    except Exception:  # noqa: BLE001
        return False


def _ranking_v2() -> bool:
    try:
        from tools.day_plan_config import flag
        return flag("ranking_v2")
    except Exception:  # noqa: BLE001
        return False


def _stakes_read(t: dict) -> str | None:
    """The stakes every reader of 'is it vital?' uses: Part A's stored stakes (`stakes_of`), or
    under `ranking_v2` the stakes derived from the cost record (`ranking.stakes_v2`, R1)."""
    if _ranking_v2():
        from tools.ranking import stakes_v2
        return stakes_v2(t)
    return stakes_of(t)


def _cost_fields(kind: str, costs=None, bears=None, shape=None, real_due=None,
                 costs_source=None, costs_why=None, passion=None) -> tuple[dict, str | None]:
    """Validate a cost record write. Returns (fields to set, error). Never touches `stakes`.
    `passion` names one of the user's passions the task serves (ranking § 4.8); "" clears it.
    Whether it lifts anything is code's: only a passion the profile marks stated does."""
    out: dict = {}
    if passion is not None:
        out["passion"] = str(passion).strip()[:60] or None
    if costs is not None:
        if isinstance(costs, str):
            try:
                costs = json.loads(costs)
            except ValueError:
                costs = None
        if not isinstance(costs, dict):
            return {}, ("error: `costs` is an object of kind → grade, e.g. {\"financial\": "
                        "\"major\"}. Nothing was written.")
        clean = {}
        for dim, grade in costs.items():
            d, g = str(dim).strip().lower(), str(grade or "").strip().lower()
            if d not in _COST_DIMENSIONS or g not in _COST_GRADES:
                return {}, (f"error: `costs` kinds are {', '.join(_COST_DIMENSIONS)}, each "
                            f"{'/'.join(_COST_GRADES)} — not {dim!r}: {grade!r}. Nothing was "
                            f"written.")
            clean[d] = g
        out["costs"] = clean
    for name, value, allowed in (("bears", bears, _BEARS), ("shape", shape, _SHAPES)):
        if value is not None:
            v = str(value).strip().lower()
            if v not in allowed:
                return {}, (f"error: `{name}` must be one of {', '.join(allowed)}, not {value!r}. "
                            f"Nothing was written.")
            out[name] = v
    if out.get("shape") == "neglect" and kind != "interval":
        return {}, "error: `shape` neglect is for an interval task only. Nothing was written."
    if real_due is not None:
        iso, err = _iso_arg("real_due", real_due)
        if err:
            return {}, err
        out["real_due"] = iso
    if str(costs_why or "").strip():
        out["costs_why"] = str(costs_why).strip()[:120]
    if any(k != "passion" for k in out):
        src, err = _source_arg("costs_source", costs_source)
        if err:
            return {}, err
        out["costs_source"] = src
    return out, None


def _set_costs(task_id: str, **kw) -> str:
    """update_task(action="set_costs"): record or correct the cost record — the fields given
    replace those on file; a stated record is never replaced by an inference (B4)."""
    tid = _split_id(task_id)

    def apply(doc: dict) -> str:
        t = _find(doc["tasks"], tid)
        if t is None:
            return f"error: no task with id {task_id!r}"
        fields, err = _cost_fields(t.get("kind", "deadline"), **kw)
        if err:
            return err
        if not fields:
            return ("error: set_costs needs at least one of costs, bears, shape, real_due, "
                    "costs_why. Nothing was written.")
        if t.get("costs_source") == "stated" and fields.get("costs_source") == "inferred":
            return f"{tid} keeps the user's own cost record — an inference does not replace it"
        for k, v in fields.items():
            if v is None:
                t.pop(k, None)          # `passion` "" clears it
            else:
                t[k] = v
        t.setdefault("history", []).append({"event": "costs_set", "at": _stamp(),
                                            **{k: v for k, v in fields.items()
                                               if k != "costs_why"}})
        return f"{tid} cost record set: {_summarise(t)}"
    return _with_store(None, apply)


def _unconfirmed_rule() -> bool:
    try:
        from tools.day_plan_config import flag
        return flag("unconfirmed_rule")
    except Exception:  # noqa: BLE001
        return False


def _from_user_or_direct() -> bool:
    """The user's own turn, or a direct call with no bound turn. A scheduled run — the system
    talking to itself — may not change a setting the user owns (the close gate's rule)."""
    turn = _turn_info()
    return not turn or bool(turn.get("user_turn"))


def _set_day_starts(task_id: str, value) -> str:
    if _split_id(task_id) != "settings":
        return 'error: day_starts is a setting — call it with task_id="settings". Nothing was written.'
    if not _from_user_or_direct():
        return ("error: not recorded — the user's day boundary changes only on their own word, "
                "and this turn has nothing from them. Nothing was changed.")
    hm = _parse_hhmm(value)
    if not hm or hm > _DAY_STARTS_MAX:
        return ("error: day_starts takes a time between 00:00 and 06:00 in HH:MM form — the hour "
                "the user's day really ends. Nothing was written.")
    text = f"{hm[0]:02d}:{hm[1]:02d}"

    def apply(doc: dict) -> str:
        settings = doc.setdefault("settings", {})
        old = settings.get("day_starts") or "00:00"
        settings["day_starts"] = text
        settings.setdefault("history", []).append(
            {"day_starts": text, "was": old, "at": _stamp()})
        settings["history"] = settings["history"][-20:]
        if text == "00:00":
            return "the user's day now ends at midnight again"
        return f"the user's day now runs {text}–{text}: before {text} it is still the previous day"
    return _with_store(None, apply)


def _source_arg(name: str, value) -> tuple[str | None, str | None]:
    src = (value or "inferred").strip().lower()
    if src not in _FIELD_SOURCES:
        return None, (f"error: `{name}` must be one of {', '.join(_FIELD_SOURCES)}, not "
                      f"{value!r}. Nothing was written.")
    return src, None


def _window_fields(kind: str, due: str | None, flexible, after) -> tuple[dict, str | None]:
    """A one-off the user can do any day up to its date ("sometime next week" — Mike,
    2026-10-27), and the earliest time of day it can start ("after 4 pm"). `eligible_from` is the
    window's first day when given; otherwise it opens now. Returns (fields, error)."""
    out: dict = {}
    if flexible:
        if kind != "deadline" or not due:
            return {}, ("error: `flexible` needs a deadline with `due` — the last day it can "
                        "happen. Nothing was written.")
        out["flexible"] = True
    if after not in (None, ""):
        try:
            out["after"] = datetime.strptime(str(after).strip(), "%H:%M").strftime("%H:%M")
        except ValueError:
            return {}, f"error: `after` must be HH:MM, not {after!r}. Nothing was written."
    return out, None


def _set_window(task_id: str, new_due: str | None, after: str | None, evidence: str | None) -> str:
    """update_task(action="set_window"): any day up to `new_due`, optionally not before `after`."""
    due_iso, err = _iso_arg("new_due", new_due)
    if err:
        return err
    if not due_iso:
        return ("error: `new_due` (YYYY-MM-DD) is required — the last day it can happen. "
                "Nothing was written.")
    win, err = _window_fields("deadline", due_iso, True, after)
    if err:
        return err
    tid = _split_id(task_id)

    def apply(doc: dict) -> str:
        t = _find(doc["tasks"], tid)
        if t is None:
            return f"error: no task with id {task_id!r}"
        if t.get("kind") != "deadline":
            return "error: set_window applies to a one-off task. Nothing was written."
        old = {k: t.get(k) for k in ("due", "flexible", "after")}
        t["due"] = due_iso
        t.update(win)
        t.setdefault("history", []).append({"event": "window_set", "at": _stamp(), "from": old,
                                            "to": {"due": due_iso, **win},
                                            "evidence": (evidence or "")[:200]})
        return f"{tid} any day up to {due_iso}: {_summarise(t)}"
    return _with_store(None, apply)


def _defer(task_id: str, until: str | None, evidence: str | None) -> str:
    """update_task(action="defer"): not outstanding until `until` (Mike, 2026-10-24, ruled
    10-29: "don't show me this until Monday"). A separate action from reschedule because hiding
    a task and moving its date are different requests — a reschedule that also hid would
    swallow a deadline's lead-time warning. It sets `eligible_from`, so the task is `dormant`
    until that day in every view that reads `_view`: no parallel field for a surface to miss.

    Refused where hiding would hide a miss: past a deadline's own date or an interval's next
    due (reschedule moves those), and for a habit, whose periods the sweep would record as
    missed while it was out of sight."""
    until_iso, err = _iso_arg("new_due", until)
    if err:
        return err
    if not until_iso:
        return ("error: `new_due` (YYYY-MM-DD) is required — the day it should come back. "
                "Nothing was written.")
    evidence = _evidence_arg(evidence)
    if not evidence:
        return ("error: `evidence` is required — quote what the user said that asks for this. "
                "A task hidden with no record of why cannot be checked. Nothing was written.")
    tid = _split_id(task_id)

    def apply(doc: dict) -> str:
        t = _find(doc["tasks"], tid)
        if t is None:
            return f"error: no task with id {task_id!r}"
        today = _today()
        when = _d(until_iso)
        if when <= today:
            return (f"error: defer needs a day after today, not {until_iso} — the task is "
                    f"already showing. Nothing was written.")
        status, kind = t.get("status", "open"), t.get("kind", "deadline")
        if status != "open":
            return f"error: {tid} is {status}, not open — there is nothing to defer."
        if kind == "habit":
            return ("error: a habit cannot be deferred — its days would be recorded as missed "
                    "while it was hidden. Record the days the user is skipping with skipped, or "
                    "dismiss it. Nothing was written.")
        due = _d(t.get("due")) if kind == "deadline" else (
            _interval_due(t, today) if kind == "interval" else None)
        if due and when > due:
            return (f"error: {tid} is due {due.isoformat()}; deferring it to {until_iso} would "
                    f"hide it until after its own date. If the date itself has moved, "
                    f"reschedule it first; otherwise defer to {due.isoformat()} at the latest. "
                    f"Nothing was written.")
        t.setdefault("history", []).append({"event": "deferred", "at": _stamp(),
                                            "from": t.get("eligible_from"), "until": until_iso,
                                            "reason": evidence[:200]})
        t["eligible_from"] = until_iso
        return (f"{tid} deferred until {until_iso} — not outstanding before then: "
                f"{_summarise(t)}")
    return _with_store(None, apply)


def _deferred_until(t: dict) -> str | None:
    """The day a deferred task comes back, when its `eligible_from` was set by defer."""
    until = t.get("eligible_from")
    for h in reversed(t.get("history") or []):
        if h.get("event") == "deferred":
            return until if h.get("until") == until else None
    return None


def _plan_fields(kind: str, goal_id=None, priority=None, priority_source=None, stakes=None,
                 stakes_source=None, zone=None, windowed: bool = False,
                 activity=None, stakes_why=None, enjoyed=None) -> tuple[dict, str | None]:
    """Validate the planner's fields. Returns (fields to set, error). An empty string for
    `goal_id`, `zone` or `activity` clears it; `enjoyed` false clears it."""
    out: dict = {}
    if enjoyed is not None:
        # Something the user enjoys (ranking § 4.9): placed soon after an effortful item.
        out["enjoyed"] = True if enjoyed is True or str(enjoyed).strip().lower() == "true" else None
    if activity is not None:
        act = str(activity).strip().lower()
        if act:
            try:
                from tools.day_shape import design
                known = list((design().get("activities") or {}))
            except Exception:  # noqa: BLE001
                known = []
            if act not in known:
                return {}, (f"error: `activity` must be one of {', '.join(known)}, not "
                            f"{activity!r}. Nothing was written.")
            out["activity"] = act
        else:
            out["activity"] = None
    if goal_id is not None:
        gid = str(goal_id).strip()
        if gid:
            goal = _goal_index().get(gid)
            if goal is None:
                known = ", ".join(sorted(_goal_index())) or "none on file"
                return {}, (f"error: no goal with id {gid!r} (goals on file: {known}). "
                            f"Nothing was written.")
            out["goal_id"] = gid
            out["goal_hash"] = _goal_hash(goal)
        else:
            out["goal_id"] = None
    if priority is not None:
        p = str(priority).strip().lower()
        if p not in _PRIORITIES:
            return {}, (f"error: `priority` must be one of {', '.join(_PRIORITIES)}, not "
                        f"{priority!r}. Nothing was written.")
        src, err = _source_arg("priority_source", priority_source)
        if err:
            return {}, err
        out.update(priority=p, priority_source=src)
    if stakes is not None:
        if kind != "deadline" and not windowed:
            return {}, ("error: `stakes` applies to a deadline, or a monthly habit with days of "
                        "the month, only. Nothing was written.")
        st = str(stakes).strip().lower()
        if st not in _STAKES:
            return {}, (f"error: `stakes` must be one of {', '.join(_STAKES)}, not {stakes!r}. "
                        f"Nothing was written.")
        src, err = _source_arg("stakes_source", stakes_source)
        if err:
            return {}, err
        out.update(stakes=st, stakes_source=src)
        if str(stakes_why or "").strip():
            out["stakes_why"] = str(stakes_why).strip()[:120]
    if zone is not None:
        z = str(zone).strip().lower()
        if z:
            try:
                from tools.location import load_zones
                names = {str(zz.get("name") or "").strip().lower() for zz in load_zones()}
            except Exception:  # noqa: BLE001
                names = set()
            if z not in names:
                known = ", ".join(sorted(n for n in names if n)) or "none named yet"
                return {}, (f"error: no zone named {z!r} (zones: {known}). Nothing was written.")
            out["zone"] = z
        else:
            out["zone"] = None
    return out, None


def _set_days(task_id: str, on_days, evidence: str | None) -> str:
    """A habit's days — weekdays for a weekly one, days of the month for a monthly one. On the
    user's own word only, quoted (review F9: a write that changes when a habit is planned is the
    user's, like the day boundary and the shape of their day). Empty clears them."""
    if not _from_user_or_direct():
        return ("error: not recorded — a habit's days change only on the user's own word, and "
                "this turn has nothing from them. Nothing was changed.")
    evidence = _evidence_arg(evidence)
    if not evidence:
        return "error: `evidence` is required — quote what the user said. Nothing was written."
    tid = _split_id(task_id)

    def apply(doc: dict) -> str:
        t = _find(doc["tasks"], tid)
        if t is None:
            return f"error: no task with id {task_id!r}"
        every = t.get("every")
        if t.get("kind") != "habit" or every not in ("week", "month"):
            return ("error: set_days applies to a weekly or monthly habit only. Nothing was "
                    "written.")
        clear = on_days in (None, "", []) or str(on_days).strip().lower() == "none"
        days, err = ([], None) if clear else _clean_days(on_days, every)
        if err:
            return err
        old = t.get("on_days")
        if days:
            t["on_days"] = days
        else:
            t.pop("on_days", None)
        t.setdefault("history", []).append({"event": "days_set", "at": _stamp(), "from": old,
                                            "to": days or None, "evidence": evidence[:200]})
        return f"{tid} days {'set' if days else 'cleared'}: {_summarise(t)}"
    return _with_store(None, apply)


def _set_plan_field(task_id: str, action: str, **kw) -> str:
    wanted = {"link_goal": "goal_id", "set_priority": "priority", "set_stakes": "stakes",
              "set_zone": "zone", "set_activity": "activity"}[action]
    # set_activity also carries `enjoyed` (ranking § 4.9) — what kind of thing it is, and whether
    # the user enjoys it — so either one alone is enough.
    with_enjoyed = action == "set_activity" and kw.get("enjoyed") is not None
    if kw.get(wanted) is None and not with_enjoyed:
        return f"error: `{wanted}` is required for {action}. Nothing was written."
    if kw.get(wanted) is None:
        wanted = "enjoyed"
    tid = _split_id(task_id)
    only = {k: v for k, v in kw.items() if k in (wanted, f"{wanted}_source")
            or (wanted == "stakes" and k == "stakes_why")
            or (with_enjoyed and k in ("activity", "enjoyed") and v is not None)}

    def apply(doc: dict) -> str:
        t = _find(doc["tasks"], tid)
        if t is None:
            return f"error: no task with id {task_id!r}"
        fields, err = _plan_fields(t.get("kind", "deadline"), windowed=bool(_month_window(t)),
                                   **only)
        if err:
            return err
        src_key = f"{wanted}_source"
        if (src_key in fields and t.get(src_key) == "stated"
                and fields.get(src_key) == "inferred"):
            return (f"{tid} keeps the user's own {wanted}, {t.get(wanted)!r} — an inference does "
                    f"not replace it")
        for k, v in fields.items():
            if v is None:
                t.pop(k, None)
                if k == "goal_id":
                    t.pop("goal_hash", None)
            else:
                t[k] = v
        # Linked to a goal, a task takes that goal's priority (`_score`: "leave unset to take it
        # from the goal it serves"). A priority that was only a judgement made before the link —
        # the task judge's, live 2026-11-22: "Find a personal trainer" kept the judge's "normal"
        # after Mike said it is a step of his fitness goal — gives way. The user's own stays.
        if (action == "link_goal" and t.get("goal_id") and t.get("priority")
                and t.get("priority_source") != "stated"):
            t.pop("priority", None)
            t.pop("priority_source", None)
        state = f"set to {t.get(wanted)!r}" if t.get(wanted) else "cleared"
        return f"{tid} {wanted} {state}: {_summarise(t)}"
    return _with_store(None, apply)


def _done_with_followup(task_id: str, evidence: str | None, followup: str | None,
                        on_date: str | None) -> str:
    """Done, but with a loose end (Mike, 2026-10-24: the Thanksgiving invitation was done
    "unsatisfactorily so", with no contact details to send it to — neither done nor dropped).
    The task closes as done, and the loose end becomes a task of its own, so it is tracked
    rather than buried in a note. `source_id` points back at the closed task."""
    loose = (followup or "").strip()
    if not loose:
        return ("error: `followup` is required — what is still left to do, in a few words. "
                "Nothing was written.")
    tid = _split_id(task_id)
    t = _find([_norm(x) for x in _load()], tid)
    if t is None:
        return f"error: no task with id {task_id!r}"
    closed = update_task(task_id, "done", evidence=evidence, on_date=on_date)
    if closed.startswith("error") or " was already " in closed:
        return closed
    opened = open_task(loose, kind="deadline", domain=t.get("domain"), source_id=tid,
                       note=f"Loose end from {tid} ({t.get('what', '')})")
    return f"{closed}\nLoose end tracked: {opened}"


def update_task(task_id: str, action: str, evidence: str | None = None,
                new_due: str | None = None, note: str | None = None,
                on_date: str | None = None, followup: str | None = None,
                minutes: int | None = None, minutes_source: str | None = None,
                goal_id: str | None = None, priority: str | None = None,
                priority_source: str | None = None, stakes: str | None = None,
                stakes_source: str | None = None, zone: str | None = None,
                on_days=None, activity: str | None = None, after: str | None = None,
                stakes_why: str | None = None, costs=None, bears: str | None = None,
                shape: str | None = None, real_due: str | None = None,
                costs_source: str | None = None, costs_why: str | None = None,
                medication: str | None = None, done_words=None,
                enjoyed: bool | None = None, passion: str | None = None) -> str:
    """Record what happened to a tracked task — done, done with a loose end, skipped,
    dismissed, reopen, reschedule, a new note, or a habit's link to a medication."""
    action = (action or "").strip().lower()
    # The planner's actions exist only while `ledger_fields` is on (review R1-1; Fable diff
    # review S-8): off, they are neither offered in the schema nor named in this error, nor
    # accepted — a model cannot reach them by guessing. `set_medication` is not a planner field:
    # the medication view and the missed-dose check read it, so it is always offered.
    actions = ("done", "done_with_followup", "skipped", "dismissed", "reopen", "reschedule",
               "note", "set_minutes", "set_medication") + (
               _PLAN_ACTIONS if _ledger_fields() else ()) + (
               ("set_costs",) if _cost_record() else ()) + (
               ("keep",) if _back_burner() else ())
    if action not in actions:
        return f"error: `action` must be one of {', '.join(actions)}, not {action!r}"
    if action == "set_costs":
        return _set_costs(task_id, costs=costs, bears=bears, shape=shape, real_due=real_due,
                          costs_source=costs_source, costs_why=costs_why, passion=passion)
    if action == "keep":
        return _keep(task_id, evidence)
    if action == "set_medication":
        return _set_medication(task_id, medication, done_words, evidence)
    if action == "done_with_followup":
        return _done_with_followup(task_id, evidence, followup, on_date)
    if action == "set_minutes":
        return _set_minutes(task_id, minutes, minutes_source)
    if action == "day_starts":
        return _set_day_starts(task_id, note if note else evidence)
    if action == "set_days":
        return _set_days(task_id, on_days, evidence)
    if action == "set_window":
        return _set_window(task_id, new_due, after, evidence)
    if action == "defer":
        return _defer(task_id, new_due, evidence)
    if action in _PLAN_ACTIONS:
        return _set_plan_field(task_id, action, goal_id=goal_id, priority=priority,
                               priority_source=priority_source, stakes=stakes,
                               stakes_source=stakes_source, zone=zone, activity=activity,
                               stakes_why=stakes_why, enjoyed=enjoyed)
    evidence = _evidence_arg(evidence)
    if action in ("done", "skipped", "dismissed", "reopen") and not evidence:
        return ("error: `evidence` is required — quote what the user said that shows this. "
                "A change with no record of what prompted it cannot be checked or sensibly "
                "reversed.")
    due_iso, err = _iso_arg("new_due", new_due)
    if err:
        return err
    on_iso, err = _iso_arg("on_date", on_date)
    if err:
        return err
    tid = _split_id(task_id)
    closed_holder: dict = {}

    def apply(doc: dict) -> str:
        t = _find(doc["tasks"], tid)
        if t is None:
            return f"error: no task with id {task_id!r}"
        today = _today()
        when = _d(on_iso) or today
        if when > today or (today - when).days > _BACKDATE_DAYS:
            return (f"error: `on_date` must be within the last {_BACKDATE_DAYS} days, "
                    f"not {on_iso}")
        kind, status = t.get("kind"), t.get("status")
        hist = t.setdefault("history", [])

        if action == "note":
            t["note"] = (note or evidence or "").strip()
            return f"{tid} note updated: {_summarise(t)}"

        if action == "reschedule":
            if not due_iso:
                return "error: `new_due` (YYYY-MM-DD) is required to reschedule"
            if kind == "habit":
                # Name only what exists (review F9): set_days is offered with the planner's
                # fields, and until then the way to new days is a new habit.
                return ("error: a habit has no single date to move — change its days with "
                        "set_days" if _ledger_fields() else
                        "error: a habit has no single date to move — dismiss it and open it "
                        "again with the days the user wants")
            field = {"deadline": "due", "waiting": "check_back", "interval": "next_due"}[kind]
            old = t.get(field) or (_interval_due(t, today).isoformat() if kind == "interval" else None)
            hist.append({"event": "rescheduled", "at": _stamp(), "from": old, "to": due_iso,
                         "reason": evidence or note or "", "was_overdue":
                         bool(_d(old) and _d(old) < today)})
            if status in _TERMINAL:
                stuck = _stuck_behind(doc["tasks"], t)
                if stuck:
                    return stuck
            t[field] = due_iso
            if kind == "deadline" and t.get("calendar_uid"):
                closed_holder["moved"] = (dict(t), due_iso)
            if _d(t.get("moot_after")) and _d(t["moot_after"]) < _d(due_iso):
                t.pop("moot_after", None)      # a new date outlives the old cut-off
            restored = 0
            if status in _TERMINAL:
                hist.append({"event": "reopened", "at": _stamp(), "was": status})
                t["status"] = "open"
                for k in ("closed_at", "evidence"):
                    t.pop(k, None)
                # "Let's do the P60 Friday" brings back what its dismissal closed (Fable #7).
                restored = _reopen_cascade(doc, t)
            return (f"{tid} rescheduled to {due_iso}: {_summarise(t)}"
                    + (f"; {restored} later step(s) it had closed are back, waiting on it"
                       if restored else ""))

        if action == "reopen":
            # Bringing a deferred task back early (Mike, 2026-10-29) — without this a deferral
            # was a one-way door until its day. Restores whatever eligible_from held before.
            until = _deferred_until(t)
            if status == "open" and until and (_d(until) or today) > today:
                prior = next((h.get("from") for h in reversed(hist)
                              if h.get("event") == "deferred"), None)
                hist.append({"event": "undeferred", "at": _stamp(), "was_until": until,
                             "reason": evidence})
                if prior:
                    t["eligible_from"] = prior
                else:
                    t.pop("eligible_from", None)
                return f"{tid} is back now instead of {until}: {_summarise(t)} ({evidence})"
            if kind == "habit":
                pk = _period(t.get("every", "day"), when)[0]
                occ = (t.get("occurrences") or {}).get(pk) or {}
                if t.get("medication") and int(occ.get("skipped_doses") or 0) > 0:
                    # A medication habit's skips are per dose: undo one.
                    occ["skipped_doses"] = int(occ["skipped_doses"]) - 1
                    if int(occ.get("done") or 0) + occ["skipped_doses"] < _habit_target(t):
                        occ.pop("skipped", None)
                        occ.pop("skip_reason", None)
                    return (f"{tid}@{pk}: one skipped dose is no longer skipped "
                            f"({occ['skipped_doses']} skipped)")
                if occ.get("skipped"):
                    occ.pop("skipped", None)
                    occ.pop("skip_reason", None)
                    return f"{tid}@{pk} is no longer marked skipped"
                if int(occ.get("done") or 0) < 1:
                    return f"{tid}@{pk} has no completion to undo"
                occ["done"] = int(occ["done"]) - 1
                if occ.get("completions"):
                    undone = occ["completions"].pop()
                    recent = t.get("recent_completions") or []
                    for i in range(len(recent) - 1, -1, -1):
                        if recent[i].get("on") == (undone or {}).get("on"):
                            recent.pop(i)
                            break
                hist.append({"event": "completion_undone", "at": _stamp(), "occ": pk,
                             "reason": evidence})
                return f"{tid}@{pk} completion undone ({occ['done']} recorded)"
            if kind == "interval":
                return "error: an interval task is never closed — use reschedule to set when it is next due"
            if status not in _TERMINAL:
                return f"{tid} is already open — nothing to reopen"
            stuck = _stuck_behind(doc["tasks"], t)
            if stuck:
                return stuck
            hist.append({"event": "reopened", "at": _stamp(), "was": status,
                         "closed_at": t.get("closed_at"), "evidence": t.get("evidence"),
                         "reason": evidence})
            t["status"] = "open"
            for k in ("closed_at", "evidence"):
                t.pop(k, None)
            # Redoing a dismissed step (R9's "redo it?" answered yes) brings back the steps its
            # dismissal closed — they were closed for that reason and no other.
            restored = _reopen_cascade(doc, t)
            return (f"{tid} reopened: {_summarise(t)} ({evidence})"
                    + (f"; {restored} later step(s) it had closed are back, waiting on it"
                       if restored else ""))

        # A later step closed only because its prerequisite was dismissed can still be reported
        # done — the user did it after all — and then the prerequisite was done too (Mike's
        # judgement gate, `_imply_prerequisites`).
        # And a skipped step that stopped later ones can be reported done itself — "I did
        # download the P60 after all" — which brings those later steps back (Fable diff review
        # #1: recording the END done instead would have closed the whole plan).
        revived = (action == "done" and kind in _ONE_OFF and (
            (status == "moot" and t.get("evidence") == _PREREQ_DISMISSED)
            or (status == "dismissed" and isinstance(t.get("cascade"), dict))))
        if status in _TERMINAL and not revived:
            return (f"{tid} was already {status} at {t.get('closed_at', 'unknown')} — "
                    f"nothing to do, and no second record made.")

        refusal = _close_refusal(t, doc["tasks"], today)
        if refusal:
            return refusal

        if action == "dismissed" or (action == "skipped" and kind in _ONE_OFF):
            # Skipping a one-off is deciding not to do it — the same as dismissing it.
            if kind == "habit":
                _finalize_periods(t, today, doc)
            t["status"] = "dismissed"
            t["closed_at"] = _stamp()
            t["evidence"] = evidence
            doc.setdefault("_history", []).append(_one_off_row(t, "dismissed"))
            cascade = _close_dependents(doc, t)
            if cascade:
                return (f"{tid} dismissed — no longer tracked: {_summarise(t)}. "
                        f"{len(cascade)} later step(s) that could not go ahead without it were "
                        f"closed; the user will be asked once whether to redo it.")
            return f"{tid} dismissed — no longer tracked: {_summarise(t)}"

        if kind in _ONE_OFF:   # done
            t["status"] = "done"
            t["closed_at"] = (when.isoformat() + "T12:00:00") if on_iso else _stamp()
            t["evidence"] = evidence
            for p in t.get("proposals") or []:
                if p.get("status") == "pending":
                    p["status"] = "superseded"
            restored = 0
            if revived:
                t.setdefault("history", []).append({"event": "reopened", "at": _stamp(),
                                                    "was": status, "reason": "done after all"})
                if status == "dismissed":
                    restored = _reopen_cascade(doc, t)       # the later steps it stopped
            doc.setdefault("_history", []).append(_one_off_row(t, "done"))
            closed_holder["task"] = dict(t)
            implied = _imply_prerequisites(doc, t)
            return (f"{tid} done: {_summarise(t)}"
                    + (f"; {len(implied)} earlier step(s) it could not have been done without "
                       f"are counted done too" if implied else "")
                    + (f"; {restored} later step(s) it had stopped are back" if restored else ""))

        if kind == "interval":
            due = _interval_due(t, today)
            state = "done" if action == "done" else "skipped"
            doc.setdefault("_history", []).append({
                "key": f"{tid}@{due.isoformat()}", "task_id": tid, "kind": "interval",
                "occurrence": f"{tid}@{due.isoformat()}", "state": state,
                "due": due.isoformat(), "closed_on": when.isoformat(),
                "late": bool(state == "done" and when > due), "recorded_at": _stamp(),
                **({"domain": t["domain"]} if t.get("domain") else {}),
            })
            t["last_done"] = when.isoformat()
            t.pop("next_due", None)
            if state == "done":
                t.setdefault("completions", []).append({"on": when.isoformat(), "at": _stamp(),
                                                        "evidence": evidence})
                t["completions"] = t["completions"][-10:]
            nxt = _interval_due(t, today)
            return f"{tid} {state} on {when.isoformat()}; next due {nxt.isoformat()}"

        # habit
        every = t.get("every", "day")
        pk, ps, pe = _period(every, when)
        swept = _d(t.get("swept_through"))
        if swept and pe <= swept:
            return (f"error: the {every} of {when.isoformat()} is already recorded — "
                    f"too late to change it")
        occs = t.setdefault("occurrences", {})
        occ = occs.setdefault(pk, {"done": 0, "completions": []})
        linked_med = bool(str(t.get("medication") or "").strip())
        if action == "skipped" and linked_med:
            return _skip_one_dose(t, occ, tid, pk, every, evidence)
        if action == "skipped":
            occ["skipped"] = True
            occ["skip_reason"] = evidence
            return f"{tid}@{pk} skipped — left out of adherence for this {every}"
        if linked_med:
            # A dose counted twice hides a missed one (reviews 2026-11-23).
            repeat = _dose_refusal(t, occ, every, when.isoformat(), evidence)
            if repeat:
                return repeat
        occ["done"] = int(occ.get("done") or 0) + 1
        occ.setdefault("completions", []).append({"on": when.isoformat(), "at": _stamp(),
                                                  "evidence": evidence})
        # Outlives the sweep, which drops ended periods: Accountability's 7-to-9-day windows
        # need the dates after the period that held them has been recorded.
        recent = t.setdefault("recent_completions", [])
        recent.append({"on": when.isoformat()})
        t["recent_completions"] = recent[-40:]
        target = _habit_target(t)
        return f"{tid}@{pk} recorded: {occ['done']} of {target} this {every}"

    result = _with_store(None, apply)
    if closed_holder.get("task"):
        _mark_calendar_done(closed_holder["task"])
    if closed_holder.get("moved"):
        _move_calendar(*closed_holder["moved"])
    return result


def _link_tag(t: dict) -> str:
    """` [medication: Atorvastatin]` for a habit linked to the medication profile, so the
    Synthesizer can see which habit a reported dose belongs on whatever the habit is titled."""
    med = str(t.get("medication") or "").strip()
    return f" [medication: {med}]" if med else ""


def _state_line(t: dict, today: date) -> str:
    v = _view(t, today)
    state = v["state"]
    if t.get("status") in _TERMINAL:
        closed = str(t.get("closed_at") or "?")[:10]
        ev = str(t.get("evidence") or "")[:80]
        return f"{t.get('status')} {closed}" + (f" — {ev}" if ev else "")
    if state == "dormant" and _deferred_until(t):
        return f"deferred until {_deferred_until(t)} — not outstanding before then"
    return {"dormant": f"not yet eligible (from {t.get('eligible_from') or t.get('start')})",
            "moot": f"moot since {t.get('moot_after')} (recorded at the next sweep)"}.get(
        state, v["text"][len(t.get("what", "")):].lstrip(" —") or state)


_HORIZON_DAYS = {"today": 0, "week": 7, "month": 31}


def _within_horizon(t: dict, today: date, days: int) -> bool:
    """For list_tasks(horizon=...): what is actionable now, plus anything dated inside the
    window. Habits are always included past "today" — they recur through any window."""
    v = _view(t, today)
    if days == 0:
        return v["actionable"] and _on_todays_list(t, v)
    if v["actionable"] or t.get("kind") == "habit":
        return True
    field = {"deadline": "due", "waiting": "check_back"}.get(t.get("kind"))
    when = _d(t.get(field)) if field else (_interval_due(t, today) if t.get("kind") == "interval"
                                           else None)
    return bool(when and (when - today).days <= days)


def list_tasks(include_closed: bool = False, horizon: str | None = None) -> str:
    """List tracked tasks with ids and state — all of them, or one horizon (today / week /
    month) when the user asks for a view of a span ("what's on this week")."""
    tasks = [_norm(t) for t in _load()]
    if not tasks:
        return "no tasks tracked"
    today = _today()
    open_items = [t for t in tasks if t.get("status") == "open"]
    # Steps waiting on an earlier step are hidden (§ 4.1 — "the one leak in the hidden layer"):
    # the user is given the step that can be done now, and the map only when they ask for it.
    waiting_steps = sum(1 for t in open_items if t.get("_blocked"))
    open_items = [t for t in open_items if not t.get("_blocked")]
    span = (horizon or "").strip().lower()
    if span:
        if span not in _HORIZON_DAYS:
            return f"error: `horizon` must be one of {', '.join(_HORIZON_DAYS)}, not {horizon!r}"
        open_items = [t for t in open_items if _within_horizon(t, today, _HORIZON_DAYS[span])]
    lines = [f"{len(open_items)} open:"] if open_items else ["nothing open"]
    # The link is shown only to a caller that may set one (Finance and Logistics hold this tool
    # too, and the link names a profile entry — review item 8's no-oracle rule).
    show_link = _may_set_link()
    implied = _implied_dates(open_items)
    for t in sorted(open_items, key=lambda t: _view(t, today)["sort"]):
        v = _view(t, today)
        lines.append(f"  {v['occ']}  [{t['kind']}] {t['what']} — {_state_line(t, today)}"
                     + (f" (no date given — assumed by {implied[t['id']]})"
                        if t["id"] in implied else "")
                     + (_link_tag(t) if show_link else ""))
    if waiting_steps:
        lines.append(f"  (+{waiting_steps} later step{'s' if waiting_steps != 1 else ''} of a "
                     f"plan, waiting on an earlier one — not shown; each appears when it can "
                     f"be done)")
    if include_closed:
        closed = [t for t in tasks if t.get("status") in _TERMINAL]
        lines.append(f"\n{len(closed)} closed:")
        for t in sorted(closed, key=lambda t: str(t.get("closed_at") or ""), reverse=True):
            lines.append(f"  {t['id']}  [{t['kind']}] {t['what']} — {_state_line(t, today)}")
    return "\n".join(lines)


def _due_sort_key(it: dict) -> tuple[int, str]:
    """
    Order by *whether a deadline was stated at all*, then by its value.

    The previous key was `str(due or "9999")` — a sentinel meant to sink undated
    obligations to the bottom. It did the opposite for the vague case: letters sort
    lexically after digits, so "next week" landed below the `"9999"` of an obligation
    with no due date at all, and `_CONTEXT_MAX` truncation dropped the *dated* one
    first. `OPEN_OBLIGATION_SCHEMA` explicitly invites "short phrase if genuinely
    vague", so this was the schema's own documented input hitting a lexical sort.

    Buckets: 0 = parseable ISO date (soonest first), 1 = a due value that is present
    but not a date (the vague phrase), 2 = nothing stated. Any stated urgency outranks
    none, which is the intent the sentinel was reaching for.
    """
    # Falsy `due` is "nothing stated", matching the `due or ...` semantics this key
    # replaces — the bug was the ordering of the buckets, not that test.
    raw = it.get("due")
    due = str(raw).strip() if raw else ""
    if not due:
        return (2, "")
    try:
        datetime.fromisoformat(due)
    except (ValueError, TypeError):
        return (1, due.lower())
    return (0, due)


def _turn_info() -> dict | None:
    """This thread's turn (tools/turn_context), carrying `user_turn`, and — written by both
    pipeline twins once the session kind is known — `kind` and `weekly_review`."""
    try:
        from tools.turn_context import current
        return current()
    except Exception:
        return None


_BLOCK_HEADER = (
    "Tracked in code, and authoritative: what is under Now is outstanding; anything not "
    "listed is done, not yet due, or someone else's move. If a log line or thread above says "
    "otherwise, this list is right. Material you may draw on — not an agenda, and not a list "
    "to read out. When the user's words show one is done, record it with update_task and "
    "their words as evidence; if you cannot tell which one they mean, ask once."
)


def _recently_closed(tasks: list[dict], today: date) -> list[str]:
    """One-offs closed in the last few days, and recurring tasks logged today — each a fact
    the model can see beside the stale copy that would otherwise re-raise it."""
    one_offs = []
    for t in tasks:
        if t.get("status") not in _TERMINAL or t.get("kind") not in _ONE_OFF:
            continue
        closed = _stamp_day(t.get("closed_at"))
        if not closed or (today - closed).days > _RECENT_DAYS or closed > today:
            continue
        status = t["status"]
        casc = t.get("cascade") or {}
        if status in ("dismissed", "skipped") and casc.get("closed") and not casc.get("raised"):
            # Its "on purpose?" question is still owed, under TODAY'S PLAN's asks. Listed here it
            # sat under "do not raise" — and on 11-22 Synth obeyed that over the ask, twice
            # (the redo re-check). The ask is the one instruction about it until it is asked.
            continue
        if status == "done":
            ev = str(t.get("evidence") or "").strip().replace("\n", " ")
            tail = f"done {_when(closed, today)}" + (f" (\"{ev[:70]}\")" if ev else "")
        elif status == "moot" and any(h.get("event") == "closed_by_prerequisite"
                                      for h in t.get("history") or []):
            tail = "stopped — an earlier step it needs was dropped"
        elif _is_parked(t):
            tail = (f"parked {(t.get('back_burner') or {}).get('at') or ''} — nobody mentioned it "
                    f"for {(t.get('back_burner') or {}).get('silent_days')} days; mentioning it "
                    f"again (open_task) brings it back")
        elif status == "moot":
            tail = "no longer relevant — its date passed"
        else:
            tail = f"dismissed {_when(closed, today)}"
        one_offs.append((str(t.get("closed_at") or ""), f"- `{t['id']}` {t['what']} — {tail}"))
    one_offs.sort(reverse=True)
    lines = [line for _, line in one_offs[:_RECENT_MAX]]
    for t in tasks:
        if t.get("status") != "open":
            continue
        if t.get("kind") == "habit":
            every = t.get("every", "day")
            pk = _period(every, today)[0]
            occ = (t.get("occurrences") or {}).get(pk) or {}
            if today in _completion_dates(occ):
                target = _habit_target(t)
                lines.append(f"- `{t['id']}@{pk}` {t['what']} — logged today "
                             f"({int(occ.get('done') or 0)} of {target} this {every})")
        elif t.get("kind") == "interval":
            last = _d(t.get("last_done"))
            if last and (today - last).days <= 1:
                lines.append(f"- `{t['id']}` {t['what']} — done {_when(last, today)}; "
                             f"next due {_interval_due(t, today).isoformat()}")
    return lines


def context_block(persona: str | None = None, as_of: date | None = None,
                  audience: str | None = None) -> str:
    """
    The Tasks section for load_recent_context — no model call, no tool call.

    In the context rather than behind a tool because the point of the store is that
    something outstanding cannot be missed for want of the session thinking to look. It is
    labelled as material to draw on precisely so it does not read as an agenda: see
    config/agents/synthesizer.md § Scheduled session conduct.

    Three things a model used to have to infer are decided here instead:
      - **What is outstanding today** (`_view`): overdue, due, a habit that matters today,
        a waiting item at its check-back. Everything else is a count under Later.
      - **What was already closed** — listed, so a stale log line or thread above is
        contradicted by a fact rather than left to be believed.
      - **What was already raised today.** On a scheduled turn an item raised earlier today
        is held back to a count. Not on a user turn — the user may be asking — and not on the
        evening close or a session carrying the weekly review, whose module says a review
        repeats things deliberately (synthesizer_scheduled_sessions.md). No bound turn hides
        nothing, so an unbound path errs toward visibility.
    """
    try:
        tasks = [_norm(t) for t in _load(persona)]
    except Exception:
        return ""
    if not tasks:
        return ""
    today = as_of or _today()
    turn = _turn_info()
    review = bool(turn and turn.get("weekly_review"))
    lead = _REVIEW_LEAD_DAYS if review else _LEAD_DAYS
    hide_raised = (bool(turn) and not turn.get("user_turn")
                   and turn.get("kind") != "evening_close" and not review)
    # A habit's `[medication: X]` names a profile entry, so it is shown only when the block is
    # built for an agent that may set a link (second review, item 7): load_recent_context passes
    # the receiving agent. The Coordinator also receives this block and is not one; an unknown
    # audience shows nothing.
    show_link = str(audience or "") in _LINK_SETTERS

    views = [(t, _view(t, today, lead)) for t in tasks]
    now = sorted(((t, v) for t, v in views if v["actionable"]),
                 key=lambda tv: (tv[1]["sort"], _due_sort_key(tv[0])))
    hidden = 0
    shown: list[str] = []
    others = 0
    per_plan: dict[str, int] = {}
    extra = 0
    for t, v in now:
        raised = _raised_today(t, v["occ"], today)
        if raised and hide_raised:
            hidden += 1
            continue
        line = f"- `{v['occ']}` {v['text']}" + (_link_tag(t) if show_link else "")
        if raised:
            line += f" (already raised today, {raised})"
        # A plan's current steps have their own allowance beside the cap (2026-11-22): on 11-22
        # "I checked my HMRC sign-in, it works" closed nothing — the step was 7th behind six
        # overdue chores, so the Synthesizer could not see it to close. Up to _STEPS_PER_PLAN per
        # plan, in the list's own order; whatever is cut, of either kind, is counted below.
        po = t.get("part_of")
        if po and per_plan.get(po, 0) < _STEPS_PER_PLAN:
            per_plan[po] = per_plan.get(po, 0) + 1
            shown.append(line)
        elif not po and others < _CONTEXT_MAX:
            others += 1
            shown.append(line)
        else:
            extra += 1

    recent = _recently_closed(tasks, today)
    pending = [t for t in tasks if t.get("status") == "open"
               and any(p.get("status") == "pending" for p in t.get("proposals") or [])]
    later = {"deadlines further out": 0, "waiting on others": 0, "not yet eligible": 0,
             "recurring, not due today": 0, "past their date, unconfirmed": 0,
             "later steps waiting on an earlier one": 0}
    for t, v in views:
        if t.get("status") != "open" or v["actionable"]:
            continue
        if v["state"] == "blocked":
            later["later steps waiting on an earlier one"] += 1
        elif v["state"] == "dormant":
            later["not yet eligible"] += 1
        elif v["state"] == "lapsed":
            later["past their date, unconfirmed"] += 1
        elif t["kind"] == "waiting":
            later["waiting on others"] += 1
        elif t["kind"] == "deadline" and v["state"] == "later":
            later["deadlines further out"] += 1
        elif t["kind"] in ("habit", "interval") and v["state"] in ("later",):
            later["recurring, not due today"] += 1
    singular = {"deadlines further out": "deadline further out",
                "later steps waiting on an earlier one": "later step waiting on an earlier one"}
    later_text = ", ".join(f"{n} {singular.get(label, label) if n == 1 else label}"
                           for label, n in later.items() if n)

    implied = _implied_dates(tasks)
    if not (shown or hidden or recent or pending or later_text or implied):
        return ""
    lines = ["## Tasks", _BLOCK_HEADER]
    boundary = _day_starts(persona)
    if boundary:
        hhmm = f"{boundary.seconds // 3600:02d}:{(boundary.seconds // 60) % 60:02d}"
        lines.append(f"The user's day runs {hhmm}–{hhmm}: before {hhmm} it is still the "
                     f"previous day, and \"today\" here means that day.")
    if shown or hidden:
        lines.append("**Now**")
        lines.extend(shown)
        if extra:
            lines.append(f"- (+{extra} more — `list_tasks` if needed)")
        if hidden:
            lines.append(f"{hidden} more already raised today and not repeated here — bring "
                         f"one back only if the user does, or it has changed.")
    if recent:
        lines.append("**Closed recently — not outstanding; do not raise**")
        lines.extend(recent)
    if pending:
        names = "; ".join(f"`{t['id']}` ({t['what']})" for t in pending[:3])
        lines.append(f"**Waiting for the user's tap:** a close proposed from their "
                     f"correspondence for {names}. Do not record it yourself unless the user "
                     f"confirms it in words.")
    if later_text:
        lines.append(f"**Later:** {later_text} — `list_tasks` for detail.")
    if implied:
        # Ranking Part B (plan § 11a, owed 1): a promise to someone with no date is ranked by an
        # assumed one (B25, R8) — shown, so it can be seen and corrected rather than acted on
        # out of sight.
        by_id = {t["id"]: t for t in tasks}
        rows = sorted(implied.items(), key=lambda kv: kv[1])[:_IMPLIED_MAX]
        lines.append("**Promised with no date — ranked as if due by the date shown** (a quick "
                     "favour 3 days, an effortful one a week). If it comes up, say the date once; "
                     "on the user's own date, reschedule it: " + "; ".join(
                         f"`{tid}` {by_id[tid]['what']} — by {d}" for tid, d in rows))
    return "\n".join(lines)


_IMPLIED_MAX = 3


def _implied_dates(tasks: list[dict]) -> dict[str, str]:
    """{task id: the assumed date} for open, undated promises to someone (ranking.implied_due) —
    under `ranking_v2` only: before the flip the date ranks nothing, so nothing shows it."""
    if not _ranking_v2():
        return {}
    try:
        from tools import ranking as RK
        c = RK.cfg()
    except Exception:  # noqa: BLE001
        return {}
    out = {}
    for t in tasks:
        if t.get("status") != "open":
            continue
        d = RK.implied_due(t, c)
        if d is not None:
            out[t["id"]] = d.isoformat()
    return out


# --- The close gate -------------------------------------------------------------------------
# Live 2026-10-24, check 4d: "I sorted the finance stuff" closed the Schwab review — one of four
# open finance tasks, none of them named. The model still decides what the words mean; this is
# a veto on the write: a close made inside a pipeline turn must be NAMED by the user's words.
# Plan: archive/plans/reply_latency_plan_2026-10-24.md § 12–12a (Fable 5.1: code gate, not a
# model check — a second model opinion is the same failure class with an extra meter).

_USER_ACT = threading.local()


@contextmanager
def _user_act():
    """The user's own act — a tap, an approved card. Outranks any bound turn, so a turn leaked
    onto a worker thread can never gate a tap."""
    prev = getattr(_USER_ACT, "on", False)
    _USER_ACT.on = True
    try:
        yield
    finally:
        _USER_ACT.on = prev


@contextmanager
def _code_act():
    """A record code makes from a parsed specialist line (a dose on Physical Health's
    `MEDICATION_TAKEN:` line — record_reported_doses). The close gate weighs the USER's words
    against a model's choice of task; here no model chose — code matched the profile name
    exactly — so the gate does not apply. Kept apart from `_user_act` so the two never blur."""
    prev = getattr(_USER_ACT, "code", False)
    _USER_ACT.code = True
    try:
        yield
    finally:
        _USER_ACT.code = prev


def _gate_tokens(text: str, stop: frozenset) -> frozenset:
    return frozenset(_task_tokens(text) - stop)


def _alias_tokens(t: dict, stop: frozenset = frozenset()) -> frozenset:
    """The other words a habit answers to besides its title: the medication it is linked to and
    its own done words (review 2026-11-23, item 2 — "took my atorvastatin" was refused against a
    habit titled "Evening tablet", which left the dose unrecorded and the medicine reading missed).
    """
    words = " ".join([str(t.get("medication") or "")] + [str(w) for w in t.get("done_words") or []])
    return _gate_tokens(words, stop) if words.strip() else frozenset()


def _named_by(t: dict, text: str, prev: str, others: list[dict], stop: frozenset,
              today: date) -> tuple[bool, str]:
    """(named, why-not). Named: the task's id or whole wording appears; or a non-negated clause
    shares an identifying token with it AND no other open task is named as well or better by
    that clause; or the message is a short affirmative and the previous reply raised it."""
    low = (text or "").lower()
    if t["id"] in low or (t.get("what") or "").strip().lower() in low:
        return True, ""
    # The linked medicine names the habit only in a clause that is not negated (second review,
    # finding 6: "I haven't taken my atorvastatin yet" passed on the bare name).
    med = " ".join(str(t.get("medication") or "").split()).lower()
    if med and any(med in c and not _NEGATION_RE.search(c)
                   for c in (x.strip() for x in _CLAUSE_SPLIT_RE.split(low)) if c):
        return True, ""

    def toks_of(x: dict) -> frozenset:
        # A prep task answers to "the prep" (live 2026-11-21: "dismiss the prep task" was refused
        # as naming nothing, beside a test step with a near-identical title).
        base = _gate_tokens(x.get("what", ""), stop) | _alias_tokens(x, stop)
        return base | {"prep"} if x.get("prep_for") else base

    ttoks = toks_of(t)
    tie = False
    for clause in _CLAUSE_SPLIT_RE.split(low):
        clause = (clause or "").strip()
        if not clause or _NEGATION_RE.search(clause):
            continue
        ctoks = _gate_tokens(clause, stop)
        shared = ctoks & ttoks
        if not shared:
            continue
        rivals = [o for o in others if ctoks & toks_of(o)]
        if any(len(ctoks & toks_of(o)) > len(shared) for o in rivals):
            continue                       # the clause names something else better
        if any(ctoks & toks_of(o) == shared for o in rivals):
            tie = True                     # "booked the dentist" with two dentist tasks open
            continue
        return True, ""
    if (prev and _AFFIRM_RE.match(text or "") and len((text or "").split()) <= 12
            and not _NEGATION_RE.search(low)):
        ptoks = _task_tokens(prev)
        raised = [o for o in others + [t] if _view(o, today)["actionable"]
                  and _tokens_match(ptoks, _task_tokens(o["what"]), single_ok=True)]
        if 1 <= len(raised) <= 2 and any(o is t for o in raised):
            return True, ""
    return False, ("they could mean more than one task" if tie
                   else "their words don't name this task")


def _close_refusal(t: dict, tasks: list[dict], today: date) -> str | None:
    """None if this close may proceed; otherwise the `error:` the model sees."""
    if getattr(_USER_ACT, "on", False) or getattr(_USER_ACT, "code", False):
        return None
    turn = _turn_info()
    if not turn or not turn.get("close_gate"):
        return None
    text = turn.get("user_text") or ""
    if not text.strip() or not turn.get("user_turn"):
        return ("error: not recorded — only the user's own words, a tap in the app, or an "
                "approved suggestion can mark a task done, and this turn has nothing from the "
                "user. Nothing was changed.")
    others = [o for o in tasks if o is not t and (o.get("status") or "open") == "open"]
    domains = {str(o.get("domain") or "").strip().lower() for o in tasks if o.get("domain")}
    stop = _task_tokens(" ".join(sorted(domains))) if domains else frozenset()
    # Only a task the user could be doing now is a rival (live 2026-11-22): "I checked my HMRC
    # sign-in, it works" tied the sign-in step with "Log in to HMRC and complete the tailoring
    # questions" — a step still WAITING on that sign-in — on the one word "hmrc", and the refusal
    # then listed only the sign-in step, so Synth asked the user to confirm the obvious. A step
    # that is blocked or not yet eligible can still be named and closed itself (the skip ruling).
    # Only those two states are excluded: a task already satisfied today (the plants, watered a
    # clause earlier) still names its own words better than "Buy plant food" does.
    rivals = [o for o in others if _view(o, today)["state"] not in ("blocked", "dormant")]
    ok, why = _named_by(t, text, turn.get("prev_assistant") or "", rivals, stop, today)
    if ok:
        return None
    ctoks = _gate_tokens(text, stop)
    pool = [o for o in others + [t] if _view(o, today)["actionable"]]
    # "the finance stuff": the category the user named is the list to ask from.
    said = _task_tokens(text) & stop
    in_named_domain = [o for o in pool if o.get("domain")
                       and _task_tokens(str(o["domain"])) & said]
    near = [o for o in pool if ctoks & _gate_tokens(o.get("what", ""), stop)]
    same_domain = [o for o in pool if o.get("domain") and o.get("domain") == t.get("domain")]
    listed = (in_named_domain or near or same_domain or pool)[:4]
    names = "; ".join(o["what"] for o in listed)
    # Live 2026-11-21: Synth relayed the reason ("the exact task title wasn't recognized from
    # your phrasing") instead of asking. The reason is for the model; the user gets the question.
    return (f"error: not recorded — {why}. Ask the user which one they mean, naming the likely "
            f"ones in everyday words"
            + (f" (open: {names})" if names else "")
            + ", then record the one they confirm. Never tell them why it was not recorded, and "
              "never mention titles, wording or matching. Nothing was changed.")


# --- The possible-completion hint ------------------------------------------------------------
# Mike's "explicit asks from Synth for ambiguous items": code notices that a user turn may
# report a task done and names the id; the model decides, and asks when it cannot tell.

_DONE_MARKERS = {
    "done", "did", "paid", "sent", "booked", "submitted", "handled", "sorted", "finished",
    "completed", "arrived", "came", "already", "posted", "returned", "filed", "signed",
    "watered", "went", "took", "called", "rang", "emailed", "replied", "renewed",
    "collected", "delivered", "dropped", "picked", "bought", "fixed", "settled",
    "registered", "ordered", "received", "confirmed", "stretched", "exercised", "trained",
    "swam", "attended", "cleared", "cancelled", "canceled", "ticked", "managed",
}
_NEGATION_RE = re.compile(
    r"\b(not|never|no longer|haven'?t|hasn'?t|didn'?t|don'?t|doesn'?t|won'?t|can'?t|"
    r"couldn'?t|wasn'?t|isn'?t|aren'?t|yet to|still need|still needs|still have to|"
    r"still has to|need to|needs to|have to|has to|going to|gonna|i'?ll|we'?ll|will|"
    r"should|must|forgot|forget|remind me)\b")
_CLAUSE_SPLIT_RE = re.compile(r"[.;!?\n]+|,\s*|\s+but\s+|\s+though\s+|\s+although\s+")
_AFFIRM_RE = re.compile(
    r"^\s*(yes|yep|yeah|yup|done|did it|all done|sorted|it'?s done|that'?s done|"
    r"already did|i did|just did|finished|completed|booked|paid|sent|went)\b", re.I)


def _clean_done_words(raw) -> list[str]:
    """A habit's own report words, lower-case single words of 3+ letters, at most eight."""
    if isinstance(raw, str):
        raw = re.split(r"[,\s]+", raw)
    out: list[str] = []
    for w in raw or []:
        w = str(w or "").strip().lower()
        if len(w) >= 3 and w.isalpha() and w not in _STOPWORDS and w not in out:
            out.append(w)
    return out[:8]


def completion_hints(user_text: str, prev_assistant: str | None = None,
                     persona: str | None = None, as_of: date | None = None) -> str:
    """A note for the Synthesizer when the user's turn may report a task done.

    Fires per clause: a clause carrying a completion word and no negation, whose words match
    an open task ("paid the Chase bill" — not "still need to pay Chase"). Or, when the turn is
    a bare affirmative ("yes, done"), against what the previous reply raised. More than three
    candidates is not a hint, it is noise — nothing is said.
    """
    text = (user_text or "").strip()
    if not text:
        return ""
    try:
        tasks = [_norm(t) for t in _load(persona) if (t.get("status") or "open") == "open"]
    except Exception:
        return ""
    if not tasks:
        return ""
    today = as_of or _today()
    hits: list[tuple[dict, str]] = []
    for clause in _CLAUSE_SPLIT_RE.split(text.lower()):
        clause = (clause or "").strip()
        if not clause or _NEGATION_RE.search(clause):
            continue
        cwords = set(_WORD_RE.findall(clause))
        # [DB-1029-03] A habit's own report words count as reporting it, with no "done" word
        # — "for breakfast I had eggs" logs a meal (Mike, 2026-10-29: an unprompted report
        # is a reason not to ask). Only while today's occurrence is still due, so a fourth
        # meal does not over-complete it.
        for t in tasks:
            if (t.get("done_words") and not any(t is h for h, _ in hits)
                    and cwords & set(t["done_words"]) and _view(t, today)["actionable"]):
                hits.append((t, "report"))
        if not cwords & _DONE_MARKERS:
            continue
        ctoks = _task_tokens(clause)
        for t in tasks:
            if any(t is h for h, _ in hits):
                continue
            # A linked habit is named by its medication too ("took my atorvastatin" for a
            # habit titled "Evening tablet") — review 2026-11-23, item 2.
            if (_tokens_match(ctoks, _task_tokens(t["what"]), single_ok=True)
                    or (t.get("medication") and _tokens_match(
                        ctoks, _task_tokens(str(t["medication"])), single_ok=True))):
                hits.append((t, "report"))
    if (not hits and prev_assistant and _AFFIRM_RE.match(text) and len(text.split()) <= 12
            and not _NEGATION_RE.search(text.lower())):
        ptoks = _task_tokens(prev_assistant)
        candidates = [t for t in tasks if _view(t, today)["actionable"]
                      and _tokens_match(ptoks, _task_tokens(t["what"]), single_ok=True)]
        if 1 <= len(candidates) <= 2:
            hits = [(t, "confirm") for t in candidates]
    if not hits or len(hits) > 3:
        return ""
    lines = ["TASK NOTE (from code, about the user's message above):"]
    for t, basis in hits:
        occ = _view(t, today)["occ"]
        if basis == "report":
            lines.append(f"- It may report `{occ}` ({t['what']}) as done. If it does, record it "
                         f"now with update_task(action=\"done\") and their words as evidence. If "
                         f"you cannot tell, ask them once which they mean — do not guess.")
        else:
            lines.append(f"- It may be confirming `{occ}` ({t['what']}), which the previous reply "
                         f"raised. If so, record it with update_task(action=\"done\") and their "
                         f"words; if it is unclear, ask once.")
    return "\n".join(lines)


def note_mentioned(user_text: str, persona: str | None = None, as_of: date | None = None) -> int:
    """Stamp `mentioned` (a day) on each open task the USER's own words name — what the back
    burner reads as a mention (ranking plan § 4.11; tools/ranking_review.py). User turns only:
    Metatron raising a task the user lets pass is not interest in it. Words, never ids. Best
    effort; returns how many were stamped."""
    text = (user_text or "").strip()
    if not text:
        return 0
    utoks = _task_tokens(text)
    if not utoks:
        return 0
    today = (as_of or _today()).isoformat()
    stamped = {"n": 0}

    def apply(doc: dict) -> int:
        for t in doc["tasks"]:
            if (t.get("status") or "open") != "open" or t.get("mentioned") == today:
                continue
            if _tokens_match(utoks, _task_tokens(t.get("what", "")), single_ok=True):
                t["mentioned"] = today
                stamped["n"] += 1
        return stamped["n"]

    try:
        with _store_lock(persona):
            doc = _load_doc(persona)
            apply(doc)
            if stamped["n"] or doc.get("_dirty"):
                _save_doc(doc, persona)
    except Exception as exc:  # noqa: BLE001 — bookkeeping never breaks a delivered reply
        logger.warning("[tasks] mention stamp not recorded: %s", exc)
    return stamped["n"]


def note_raised(reply_text: str, persona: str | None = None, as_of: date | None = None) -> int:
    """Stamp the Now items a delivered reply mentioned, so later scheduled turns today hold
    them back. Called after the reply exists — `_close_turn_bookkeeping` on both pipeline
    twins. Matched on words, never on ids: ids are not supposed to reach the user."""
    reply = (reply_text or "").strip()
    if not reply:
        return 0
    rtoks = _task_tokens(reply)
    if not rtoks:
        return 0
    today = as_of or _today()
    stamped = {"n": 0}

    def apply(doc: dict) -> int:
        for t in doc["tasks"]:
            if t.get("status") != "open":
                continue
            v = _view(t, today)
            if not v["actionable"]:
                continue
            if not _tokens_match(rtoks, _task_tokens(t["what"]), single_ok=True):
                continue
            raised = {k: val for k, val in (t.get("raised") or {}).items()
                      if _stamp_day(val) == today}
            if v["occ"] not in raised:
                raised[v["occ"]] = _stamp()
                stamped["n"] += 1
            t["raised"] = raised
        return stamped["n"]

    try:
        with _store_lock(persona):
            doc = _load_doc(persona)
            apply(doc)
            if stamped["n"] or doc.get("_dirty"):
                _save_doc(doc, persona)
    except Exception as exc:  # noqa: BLE001 — bookkeeping never breaks a delivered reply
        logger.warning("[tasks] raise stamp not recorded: %s", exc)
    return stamped["n"]


# --- Correspondence proposals ----------------------------------------------------------------
# Ids and dates only. The sender and subject of the message are attacker-written; they are
# joined from the intake record at the moment the app asks, shown to the user, and never stored
# here, never written to the conversation, and never put in front of a model.

_CORRESPONDENCE_EVIDENCE = "correspondence evidence, approved in the app"
# Location evidence (the day planner, archive/plans/day_planner_plan_2026-10-24.md § 5.9): the
# user's phone reported arriving at the place a task gets done, during its planned time. It says
# they were THERE — never for how long — so it only ever offers a close; the tap closes it.
_LOCATION_EVIDENCE = "location evidence, approved in the app"
# "whatsapp" (archive/plans/whatsapp_phase1_build_plan_2026-11-23.md § 2.5): ONE card per task,
# ever — keyed by the task, not the message, so a chatty sender parks one card and a decline ends
# WhatsApp proposals for that task for good. Correspondence keys per message, which for a chat
# would park a card per line.
_PROPOSAL_SOURCES = ("correspondence", "location", "whatsapp")
_LOCATION_PROPOSAL_TTL_DAYS = 2


def add_proposal(task_id: str, envelope_id: str = "", basis: str = "", received: str = "",
                 persona: str | None = None, source: str = "correspondence",
                 key: str | None = None, on_date: str | None = None) -> bool:
    """Park a proposed close on an open task. False if one for that evidence already exists.

    `source` "correspondence" (the original shape): one-offs only, keyed by the message's
    envelope id. "location" (review R1-5): any open task but a `waiting` one, a habit or interval
    occurrence included — `task_id` may carry `@period` and `on_date` says which day — keyed by
    `key` ("gym@2026-10-26"), so one arrival offers one card."""
    tid = _split_id(task_id)
    source = source if source in _PROPOSAL_SOURCES else "correspondence"
    added = {"ok": False}

    def apply(doc: dict) -> None:
        t = _find(doc["tasks"], tid)
        if t is None or t.get("status") != "open":
            return
        if source in ("correspondence", "whatsapp") and t.get("kind") not in _ONE_OFF:
            return
        if source == "location" and (t.get("kind") == "waiting" or not key):
            return
        props = t.setdefault("proposals", [])
        if source == "whatsapp":
            if any(p.get("source") == "whatsapp" for p in props):
                return          # pending, accepted or declined: one per task, ever
            wkey = f"whatsapp:{tid}"
            pid = "pr_" + hashlib.sha256(f"{tid}|{wkey}".encode()).hexdigest()[:10]
            props.append({"proposal_id": pid, "source": "whatsapp", "key": wkey,
                          "envelope_id": envelope_id, "basis": str(basis or "")[:40],
                          "received": str(received or "")[:25], "created": _stamp(),
                          "status": "pending"})
        elif source == "correspondence":
            if any(p.get("envelope_id") == envelope_id for p in props):
                return
            pid = "pr_" + hashlib.sha256(f"{tid}|{envelope_id}".encode()).hexdigest()[:10]
            props.append({"proposal_id": pid, "envelope_id": envelope_id, "basis": basis,
                          "received": str(received or "")[:25], "created": _stamp(),
                          "status": "pending"})
        else:
            if any(p.get("source") == "location" and p.get("key") == key for p in props):
                return
            pid = "pr_" + hashlib.sha256(f"{tid}|location|{key}".encode()).hexdigest()[:10]
            props.append({"proposal_id": pid, "source": "location", "key": key,
                          "occurrence": str(task_id).strip(), "on_date": on_date,
                          "basis": str(basis or "")[:120], "created": _stamp(),
                          "status": "pending"})
        added["ok"] = True

    _with_store(persona, apply)
    return added["ok"]


def drop_pending_proposals(envelope_ids: set[str], source: str = "whatsapp",
                           persona: str | None = None) -> int:
    """Remove PENDING proposals of `source` that name one of these envelopes — the WhatsApp purge
    (W3) and the user's opt-in deletion. Answered ones stay: they record a tap the user made."""
    if not envelope_ids:
        return 0
    gone = {"n": 0}

    def apply(doc: dict) -> None:
        for t in doc["tasks"]:
            props = t.get("proposals") or []
            kept = [p for p in props if not (p.get("source") == source
                                              and p.get("status") == "pending"
                                              and p.get("envelope_id") in envelope_ids)]
            if len(kept) != len(props):
                gone["n"] += len(props) - len(kept)
                t["proposals"] = kept

    _with_store(persona, apply)
    return gone["n"]


def has_proposal(task_id: str, key: str, persona: str | None = None) -> bool:
    """Is a location proposal for this evidence already parked (pending or answered)?"""
    tid = _split_id(task_id)
    t = _find([_norm(x) for x in _load(persona)], tid)
    return bool(t and any(p.get("source") == "location" and p.get("key") == key
                          for p in t.get("proposals") or []))


def pending_proposals(persona: str | None = None) -> list[dict]:
    """Pending proposals on open tasks, oldest first: ids, the task's own words, dates."""
    out = []
    for t in _load(persona):
        t = _norm(t)
        if t.get("status") != "open":
            continue
        for p in t.get("proposals") or []:
            if p.get("status") == "pending":
                out.append({"proposal_id": p.get("proposal_id"), "task_id": t["id"],
                            "what": t["what"], "envelope_id": p.get("envelope_id"),
                            "basis": p.get("basis"), "received": p.get("received"),
                            "created": p.get("created"),
                            "source": p.get("source") or "correspondence"})
    out.sort(key=lambda p: str(p.get("created") or ""))
    return out


def resolve_proposal(proposal_id: str, accept: bool, persona: str | None = None) -> str:
    """The user's tap on a proposal. Accept closes the task with content-free evidence;
    decline means that message is never offered again for that task."""
    target: dict = {"task": None, "prop": None}

    def find(doc: dict) -> str:
        for t in doc["tasks"]:
            for p in t.get("proposals") or []:
                if p.get("proposal_id") == proposal_id:
                    if p.get("status") != "pending":
                        return f"error: that suggestion was already {p.get('status')}"
                    p["status"] = "accepted" if accept else "declined"
                    p["resolved_at"] = _stamp()
                    target["task"] = t["id"]
                    target["prop"] = dict(p)
                    return "ok"
        return "error: no such suggestion"

    result = _with_store(persona, find)
    if not result.startswith("ok"):
        return result
    prop = target["prop"] or {}
    if not accept:
        if prop.get("source") == "whatsapp":
            return f"{target['task']} left open; WhatsApp will not suggest closing it again"
        what = "that arrival" if prop.get("source") == "location" else "that message"
        return f"{target['task']} left open; {what} will not be offered again"
    with _user_act():   # the user's tap on the card — never gated by a turn's words
        if prop.get("source") == "location":
            # The occurrence the evidence was for — a habit's period, on the day of the arrival.
            return update_task(prop.get("occurrence") or target["task"], "done",
                               evidence=f"{_LOCATION_EVIDENCE} ({proposal_id})",
                               on_date=prop.get("on_date"))
        return update_task(target["task"], "done",
                           evidence=f"{_CORRESPONDENCE_EVIDENCE} ({proposal_id})")


# What an arriving message must carry for its SUBJECT alone to suggest a close: two of the
# task's identifying words AND one of these. "Your payment was received", "Booking confirmed".
_EVIDENCE_SUBJECT_MARKERS = {
    "received", "receipt", "confirmed", "confirmation", "confirming", "booked", "booking",
    "scheduled", "complete", "completed", "accepted", "approved", "processed", "paid",
    "payment", "thank", "thanks", "submitted", "filed",
}
# "sirva.com" is a domain; "S.A.R." is a name with dots in it.
_DOMAIN_RE = re.compile(r"[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}")
# Mail the intake classifier already judged bulk is never evidence of anything.
_EVIDENCE_SKIP_CATEGORIES = {"promotion", "announcement"}


def _resolve_source(source_id: str, persona: str | None = None) -> dict:
    """The thread and sender of the intake record a task was opened from — stored as match
    keys only, never rendered to a model (they are whatever the sender wrote)."""
    try:
        from tools.intake import read_records
        for row in read_records(persona=persona):
            if row.get("id") == source_id:
                out = {}
                if row.get("thread_id"):
                    out["source_thread"] = str(row["thread_id"])[:300]
                if row.get("sender"):
                    out["source_sender"] = str(row["sender"]).lower()[:200]
                return out
    except Exception as exc:  # noqa: BLE001
        logger.info("[tasks] source %s not resolved: %s", source_id, exc)
    return {}


def _sender_matches(expect: str, address: str, display: str) -> bool:
    expect = (expect or "").strip().lower()
    address = (address or "").strip().lower()
    display = (display or "").strip().lower()
    if not expect:
        return False
    if "@" in expect:
        return address == expect
    if _DOMAIN_RE.fullmatch(expect):
        domain = address.rsplit("@", 1)[-1]
        return domain == expect or domain.endswith("." + expect)
    return bool(expect) and (expect in display or expect.replace(" ", "") in address)


_WA_WORD_RE = re.compile(r"\w+", re.UNICODE)


def _wa_sender_matches(expect: str, address: str, display: str) -> bool:
    """A WhatsApp sender against a task's `expect_from` (phase-1 plan § 2.5, review 1).

    An id (`@` in it — what Phase 3's "Track this" writes) must equal the canonical sender
    exactly. Anything else is what a model wrote ("Anna"), matched against **the user's own
    name** for the sender — the share list's one-to-one label or group senders map, never a
    group subject or a WhatsApp display name — as whole words in order, case-folded: "Anna"
    matches "Anna Petrova", never "Joanna". Not `_sender_matches`: its substring test is how the
    one card a task ever gets would land on the wrong person.
    """
    expect = (expect or "").strip().casefold()
    if not expect:
        return False
    if "@" in expect:
        return (address or "").strip().casefold() == expect
    want = _WA_WORD_RE.findall(expect)
    have = _WA_WORD_RE.findall((display or "").casefold())
    if not want or not have:
        return False
    return any(have[i:i + len(want)] == want for i in range(len(have) - len(want) + 1))


def match_reply_marker(envelope_ids: set[str], marker_time: str,
                       persona: str | None = None) -> int:
    """The user's own reply in a chat, as evidence for a task opened from a message in it.

    `envelope_ids` are that chat's WhatsApp facts that asked something of the user (question,
    request, proposal) — tools/intake_whatsapp.py passes them, so this module never reads the
    index. An open one-off task whose `source_id` is one of them, opened before `marker_time`,
    gets the task's one WhatsApp card. Never a close: replying is not always doing.
    """
    if not envelope_ids or not marker_time:
        return 0
    added = 0
    for t in _load(persona):
        t = _norm(t)
        if (t.get("status") != "open" or t.get("kind") not in _ONE_OFF
                or t.get("source_id") not in envelope_ids):
            continue
        if str(t.get("created_at") or "") >= str(marker_time):
            continue
        if add_proposal(t["id"], t["source_id"], "reply", marker_time[:25], persona=persona,
                        source="whatsapp"):
            added += 1
    return added


def match_envelope(envelope_id: str, thread_id: str = "", sender_address: str = "",
                   sender_display: str = "", subject: str = "", received: str = "",
                   category: str = "", persona: str | None = None, channel: str = "") -> int:
    """
    Called by tools/intake.sweep for each message it processes. A message that answers an
    open deadline or waiting task parks a proposed close for the user to tap — it never closes
    anything itself, and none of the message's text is stored (see add_proposal).

    Three bases, strongest first: the same thread as the message the task came from; a sender
    the waiting task said to expect; or a subject naming the task with a completion word.
    Mike, 2026-10-23: waiting items mostly expect an update from correspondence, not the user.
    """
    if not envelope_id or (category or "").lower() in _EVIDENCE_SKIP_CATEGORIES:
        return 0
    subject_words = set(_WORD_RE.findall((subject or "").lower()))
    subject_tokens = _task_tokens(subject or "")
    added = 0
    for t in _load(persona):
        t = _norm(t)
        if t.get("status") != "open" or t.get("kind") not in _ONE_OFF or t.get("_blocked"):
            continue
        if envelope_id == t.get("source_id"):
            continue
        if channel == "whatsapp":
            # The sender basis only: a chat has no thread (thread_id is empty by design) and its
            # subject is our own fact string, not words of theirs to match a task against.
            if (t.get("expect_from")
                    and _wa_sender_matches(t["expect_from"], sender_address, sender_display)
                    and add_proposal(t["id"], envelope_id, "sender", received, persona=persona,
                                     source="whatsapp")):
                added += 1
            continue
        basis = None
        if thread_id and thread_id == t.get("source_thread"):
            basis = "thread"
        elif t.get("expect_from") and _sender_matches(t["expect_from"], sender_address,
                                                      sender_display):
            basis = "sender"
        elif (subject_words & _EVIDENCE_SUBJECT_MARKERS
              and _tokens_match(subject_tokens, _task_tokens(t["what"]))):
            basis = "subject"
        if basis and add_proposal(t["id"], envelope_id, basis, received, persona=persona):
            added += 1
    return added


def act_from_app(task_id: str, action: str, persona: str | None = None,
                 reason: str | None = None, followup: str | None = None,
                 confirmed: bool = False) -> str:
    """A tap in the app's Today panel. The evidence is the tap itself — the user's own act —
    plus the reason, when the app sent one. An app from before reasons existed sends none and
    still works: "marked in the app" alone is the record, as it was."""
    action = (action or "").strip().lower()
    if action not in ("done", "skipped", "dismissed", "done_with_followup"):
        return f"error: unsupported action {action!r}"
    why = (reason or "").strip()
    evidence = "marked in the app" + (f": {why}" if why else "")
    with _user_act():
        out = update_task(task_id, action, evidence=evidence, followup=followup)
    # The app showed what this drop stops and the user tapped "Drop anyway": the on-purpose
    # question is answered at the tap, so the Synthesizer is not told to ask it later.
    if confirmed and action in ("dismissed", "skipped") and not str(out).startswith("error"):
        mark_cascade_raised([_split_id(task_id)], persona)
    return out


def _on_todays_list(t: dict, v: dict) -> bool:
    """The waking day, and nothing more (Mike, 2026-10-24: "I don't want more than a daily view
    unless otherwise asked for"). Narrower than the head layer's Now, which keeps its two-day
    lead for the evening close: overdue, due today, daily habits, intervals that are due, waiting
    items at check-back — and a weekly or monthly quota only on one of its planned days or when
    today is its last chance. Undated one-offs and quotas on ordinary days stay out; the longer
    view is list_tasks(horizon=...) in conversation."""
    state = v["state"]
    if state in ("overdue", "waiting_due"):
        return True
    if state != "due_today":
        return False          # upcoming, and undated or vague one-offs ("open")
    if t.get("kind") != "habit" or (t.get("every") or "day") == "day":
        return True
    q = v.get("quota") or {}
    return bool(q.get("planned") or q.get("at_risk"))


def _planned_today(persona: str | None, today: date) -> set[str]:
    """Task ids on today's stored plan — read, never built (the panel poll must not wait)."""
    try:
        from tools import day_plan as D
        plan = D._read_json(D._plan_path(today, persona), None) or {}
    except Exception:  # noqa: BLE001 — no plan means nothing flexible is listed today
        return set()
    return {b.get("task_id") for b in plan.get("blocks") or [] if b.get("kind") == "task"}


def today_items(persona: str | None = None, as_of: date | None = None) -> list[dict]:
    """The Now list for the app's Today panel: occurrence id, the task's words, its state.

    Minus `upcoming`. The two-day lead belongs to the head layer (the evening close has to see
    tomorrow); in a list headed "Today" a deadline moved to Monday read as a reschedule that had
    not landed (Mike, 2026-10-24)."""
    today = as_of or _today()
    out = []
    planned = None
    rows = [_norm(x) for x in _load(persona)]
    # What each task would stop if dropped: the open steps that need it (§ 10 R9). The app names
    # them at the tap and asks "Drop anyway?" (Mike, 2026-11-22: a tap can be a slip — settled
    # there, by code, where the Synthesizer's later question went unasked on live turns).
    stops: dict[str, list[str]] = {}
    for d in rows:
        if d.get("status") == "open" and d.get("required") is not False:
            for n in d.get("needs") or []:
                stops.setdefault(n, []).append(d["what"])
    for t in rows:
        v = _view(t, today)
        if not v["actionable"]:
            continue
        if v["state"] == "in_window":
            # Any day up to its date: listed on a day the plan found room for it, so the list
            # and the plan agree and it is not on the list every day of its window.
            if planned is None:
                planned = _planned_today(persona, today)
            if t["id"] not in planned:
                continue
        elif not _on_todays_list(t, v):
            continue
        out.append({"task_id": t["id"], "occurrence": v["occ"], "kind": t["kind"],
                    "what": t["what"], "label": v["text"][len(t["what"]):].lstrip(" —"),
                    "state": v["state"], "sort": list(v["sort"]),
                    "actions": (["done", "skipped"] if t["kind"] in ("habit", "interval")
                                else ["done", "done_with_followup", "dismissed"]),
                    **({"stops": stops[t["id"]][:3]} if stops.get(t["id"]) else {})})
    out.sort(key=lambda i: i["sort"])
    for i in out:
        i.pop("sort", None)
    return out


# --- The nightly sweep -----------------------------------------------------------------------

def _finalize_periods(t: dict, today: date, doc: dict) -> int:
    """Persist every ended habit period since `swept_through` (bounded), then drop it from the
    task. A period that began before the task started is `partial` and excluded from adherence:
    a weekly quota created on a Friday must not record `missed 0/3` for that week."""
    if t.get("kind") != "habit":
        return 0
    every = t.get("every") if t.get("every") in _EVERY else "day"
    target = _habit_target(t)
    unconfirmed_ok = _unconfirmed_rule() and not is_essential(t)
    start = _start(t) or today
    swept = _d(t.get("swept_through"))
    yesterday = today - timedelta(days=1)
    first = max(start, today - timedelta(days=_SWEEP_CATCHUP_DAYS))
    if swept:
        first = max(first, swept + timedelta(days=1))
    if first > yesterday:
        return 0
    occs = t.setdefault("occurrences", {})
    rows = []
    d = first
    last_end = None
    while d <= yesterday:
        pk, ps, pe = _period(every, d)
        if pe > yesterday:
            break
        occ = occs.get(pk) or {}
        done = int(occ.get("done") or 0)
        if occ.get("skipped"):
            state = "skipped"
        elif done >= target:
            state = "done"
        elif unconfirmed_ok:
            # F10: nobody was asked about a non-essential habit, so "missed" would be a guess.
            state = "unconfirmed"
        else:
            state = "missed"
        row = {"key": f"{t['id']}@{pk}", "task_id": t["id"], "kind": "habit",
               "occurrence": f"{t['id']}@{pk}", "state": state,
               "period_start": ps.isoformat(), "period_end": pe.isoformat(),
               "target": target, "done": done, "partial": ps < start,
               "recorded_at": _stamp()}
        if t.get("domain"):
            row["domain"] = t["domain"]
        rows.append(row)
        occs.pop(pk, None)
        last_end = pe
        d = pe + timedelta(days=1)
    if last_end:
        t["swept_through"] = last_end.isoformat()
    if rows:
        doc.setdefault("_history", []).extend(rows)
    return len(rows)


def sweep(persona: str | None = None, as_of: date | None = None) -> str:
    """
    Nightly persistence — `daily_task_sweep` in core/scheduler.py's _DEFAULT_JOBS. Token-free,
    silent, returns a plain string (never a notify dict). Records ended habit periods to
    history, marks event-bound one-offs moot once their date has passed, expires stale
    correspondence proposals and clears yesterday's raise stamps. Nothing it does changes what
    the block shows today — derivation is pure — it only makes the record permanent.
    """
    today = as_of or _today()
    counts = {"periods": 0, "moot": 0, "expired": 0}

    def apply(doc: dict) -> str:
        cutoff = today - timedelta(days=_PROPOSAL_TTL_DAYS)
        for t in doc["tasks"]:
            if t.get("status") != "open":
                continue
            counts["periods"] += _finalize_periods(t, today, doc)
            if t.get("kind") in _ONE_OFF:
                moot = _d(t.get("moot_after"))
                if moot and today > moot:
                    t["status"] = "moot"
                    t["closed_at"] = _stamp()
                    t["evidence"] = f"its date ({moot.isoformat()}) passed"
                    doc.setdefault("_history", []).append(_one_off_row(t, "moot"))
                    counts["moot"] += 1
            loc_cutoff = today - timedelta(days=_LOCATION_PROPOSAL_TTL_DAYS)
            for p in t.get("proposals") or []:
                created = _d(p.get("created"))
                # A location card is about one day's arrival; it goes stale in two.
                limit = loc_cutoff if p.get("source") == "location" else cutoff
                if p.get("status") == "pending" and created and created < limit:
                    p["status"] = "expired"
                    counts["expired"] += 1
            raised = {k: v for k, v in (t.get("raised") or {}).items()
                      if _stamp_day(v) == today}
            if raised:
                t["raised"] = raised
            else:
                t.pop("raised", None)
        # A required prerequisite that went moot on its own (its date passed) stops what needs
        # it exactly as a dismissal does (R9) — otherwise those steps stay blocked forever.
        by_id = {t.get("id"): t for t in doc["tasks"]}
        for t in list(doc["tasks"]):
            if (t.get("status") == "moot" and t.get("required") is not False
                    and not t.get("cascade") and any(
                        t["id"] in _needs(o) and o.get("status") == "open"
                        for o in by_id.values())):
                counts["moot"] += len(_close_dependents(doc, t))
        return (f"task sweep: {counts['periods']} period(s) recorded, {counts['moot']} moot, "
                f"{counts['expired']} suggestion(s) expired")

    return _with_store(persona, apply)


# --- Adherence -------------------------------------------------------------------------------

def adherence(persona: str | None = None, days: int = 30, as_of: date | None = None) -> list[dict]:
    """Per-task adherence over a trailing window, from history only (ended periods, closed
    one-offs). Habits: completions ÷ target, skipped and partial periods excluded from the
    denominator. One-offs: done on time, late, dismissed, moot, rescheduled."""
    today = as_of or _today()
    since = today - timedelta(days=days)
    names = {t["id"]: t["what"] for t in (_norm(x) for x in _load(persona))}
    per: dict[str, dict] = {}
    for r in _history_rows(persona):
        end = _d(r.get("period_end") or r.get("closed_on"))
        if not end or end < since or end > today:
            continue
        s = per.setdefault(r.get("task_id"), {
            "task_id": r.get("task_id"), "kind": r.get("kind"), "what": names.get(r.get("task_id"), "?"),
            "periods": 0, "met": 0, "missed": 0, "unconfirmed": 0, "skipped": 0, "partial": 0,
            "target": 0,
            "completed": 0, "done": 0, "late": 0, "dismissed": 0, "moot": 0, "rescheduled": 0})
        state = r.get("state")
        if r.get("kind") == "habit":
            if r.get("partial"):
                s["partial"] += 1
                continue
            if state == "skipped":
                s["skipped"] += 1
                continue
            target = int(r.get("target") or 0)
            s["periods"] += 1
            s["target"] += target
            s["completed"] += min(int(r.get("done") or 0), target)
            # An unconfirmed period counts against the rate exactly as a missed one does — the
            # rate must not improve by not asking — and is reported under its own name.
            s["met" if state == "done" else (
                "unconfirmed" if state == "unconfirmed" else "missed")] += 1
        else:
            if state in s:
                s[state] += 1
            if r.get("late"):
                s["late"] += 1
            if r.get("rescheduled"):
                s["rescheduled"] += 1
    for s in per.values():
        if s["kind"] == "habit":
            s["rate"] = round(s["completed"] / s["target"], 3) if s["target"] else None
        else:
            s["rate"] = round((s["done"] - s["late"]) / s["done"], 3) if s["done"] else None
    return sorted(per.values(), key=lambda s: (s["kind"] or "", s["what"]))


def daily_task_counts(day: str, persona: str | None = None) -> dict:
    """Content-free counts for ONE day, for tools/analytics.py's A9 row. Counts only — no task
    words, no ids. Re-derivable at any time from task_history.jsonl."""
    out = {"tasks_done": 0, "tasks_missed": 0, "tasks_unconfirmed": 0, "tasks_skipped": 0,
           "tasks_dismissed": 0,
           "tasks_moot": 0, "habit_target": 0, "habit_done": 0, "deadlines_met": 0,
           "deadlines_late": 0}
    for r in _history_rows(persona):
        if r.get("kind") == "habit":
            if r.get("period_end") != day or r.get("partial"):
                continue
            if r.get("state") == "skipped":
                out["tasks_skipped"] += 1
                continue
            target = int(r.get("target") or 0)
            out["habit_target"] += target
            out["habit_done"] += min(int(r.get("done") or 0), target)
            out["tasks_done" if r.get("state") == "done" else (
                "tasks_unconfirmed" if r.get("state") == "unconfirmed" else "tasks_missed")] += 1
            continue
        if r.get("closed_on") != day:
            continue
        state = r.get("state")
        if state == "done":
            out["tasks_done"] += 1
            if r.get("kind") == "deadline" and r.get("due"):
                out["deadlines_late" if r.get("late") else "deadlines_met"] += 1
        elif state == "skipped":
            out["tasks_skipped"] += 1
        elif state == "dismissed":
            out["tasks_dismissed"] += 1
        elif state == "moot":
            out["tasks_moot"] += 1
    return out


def accountability_items(persona: str | None = None) -> list[dict]:
    """Closed work in the shape tools/accountability.py's join reads (`what`, `status:
    closed`, `closed_at`): done one-offs, plus each recorded completion of a recurring task —
    so "go to the gym tomorrow" now resolves from the ledger in code, not the judgment gate."""
    out = []
    for t in _load(persona):
        t = _norm(t)
        if t.get("kind") in _ONE_OFF:
            if t.get("status") == "done":
                closed_at = t.get("closed_at")
                if _day_starts() and _stamp_day(closed_at):
                    # Past-midnight closes join the intention of the day the user was still in.
                    closed_at = f"{_stamp_day(closed_at).isoformat()}T12:00:00"
                out.append({"what": t["what"], "status": "closed", "closed_at": closed_at})
            elif t.get("kind") == "deadline" and t.get("status") == "open" and not t.get("_blocked"):
                # [DB-0827-09] An intention that is still an open task was sent to the
                # free-text judge, which said "indeterminate" while the ledger knew it was not
                # done (2026-10-29 audit). Waiting tasks are left out: waiting on someone
                # else is not the user's failure. `due`/`eligible_from` let the join tell a
                # task not yet due, or deferred by the user, from one that slipped.
                out.append({"what": t["what"], "status": "open",
                            "opened_at": t.get("created_at"), "due": t.get("due"),
                            "eligible_from": t.get("eligible_from")})
            continue
        dates = [str(c.get("on") or c.get("at") or "")[:10]
                 for c in (t.get("completions") or []) + (t.get("recent_completions") or [])]
        for occ in (t.get("occurrences") or {}).values():
            dates += [d.isoformat() for d in _completion_dates(occ)]
        for d in sorted(set(x for x in dates if x)):
            out.append({"what": t["what"], "status": "closed", "closed_at": f"{d}T12:00:00"})
    return out


def same_task(text: str, what: str) -> bool:
    """The ledger's own bar for "this text is about this task" — two shared identifying
    tokens or identical sets, never a single shared word. Used where a match turns into a
    verdict (tools/accountability.py), so it is the strict form: "book dentist" does not
    match "Book flights for the US trip"."""
    return _tokens_match(_task_tokens(text), _task_tokens(what))


def report(persona: str, days: int = 30) -> str:
    rows = adherence(persona, days)
    if not rows:
        return f"no task history in the last {days} days"
    lines = [f"Task adherence, last {days} days", ""]
    for s in rows:
        rate = "—" if s["rate"] is None else f"{s['rate']:.0%}"
        if s["kind"] == "habit":
            lines.append(f"  {rate:>5}  habit     {s['what']}  ({s['completed']}/{s['target']} "
                         f"over {s['periods']} period(s); {s['missed']} missed, "
                         f"{s['skipped']} skipped, {s['partial']} partial)")
        else:
            lines.append(f"  {rate:>5}  {s['kind']:<9} {s['what']}  (done {s['done']}, late "
                         f"{s['late']}, dismissed {s['dismissed']}, moot {s['moot']}, "
                         f"rescheduled {s['rescheduled']})")
    return "\n".join(lines)


# --- Consult points (plan § 5) ---------------------------------------------------------------
# Every other place a to-do can sit — conversation threads, day-log lists, horizon findings,
# reconcile candidates, calendar reads — asks the ledger before it speaks. Two strengths:
#   - LINKED: the copy carries the task id (the model is shown ids and told to include them)
#     or a stored link (a calendar uid). Deterministic, so code may act on it.
#   - MATCHED: two identifying tokens shared, or identical sets — never the single-token
#     relaxation. Annotated, never deleted: a visible note costs a question if it is wrong,
#     where a silent removal would hide a real commitment. Mike asked how aggressive this
#     should be; aggressive only where the link is exact is the answer the review accepted.

_TASK_ID_RE = re.compile(r"\bob_\d{6}_[0-9a-f]{6}\b")

# A copy is checked against tasks closed this recently. Older closes have no copies left in
# context: threads expire at seven days, the day logs shown span five.
_CONSULT_WINDOW_DAYS = 14


def consult_index(persona: str | None = None, as_of: date | None = None) -> list[dict]:
    """Every task a copy elsewhere might be about: open ones, and ones closed recently."""
    today = as_of or _today()
    out = []
    for t in _load(persona):
        t = _norm(t)
        status = t.get("status")
        if status in _TERMINAL:
            closed = _stamp_day(t.get("closed_at"))
            if not closed or (today - closed).days > _CONSULT_WINDOW_DAYS:
                continue
            phrase = ("parked on the back burner" if _is_parked(t)
                      else "no longer relevant" if status == "moot"
                      else f"{status} {closed.isoformat()}")
        elif status == "open" and t.get("_blocked"):
            # A hidden step is not something a copy elsewhere can be about (R7): matching one
            # would let it suppress a horizon finding or annotate a log line the user never saw.
            continue
        elif status == "open":
            # A deferred task's copies elsewhere (a thread, a day log) must not read as
            # outstanding before its day: the user asked not to see it until then.
            until = _deferred_until(t)
            phrase = (f"deferred until {until}" if until and _view(t, today)["state"] == "dormant"
                      else None)
        else:
            continue
        out.append({"id": t["id"], "what": t["what"], "kind": t["kind"],
                    "tokens": _task_tokens(t["what"]), "terminal": status in _TERMINAL,
                    "status": status, "closed_on": _stamp_day(t.get("closed_at")), "phrase": phrase,
                    "calendar_uid": t.get("calendar_uid")})
    return out


_MONTHS = {m: i for i, m in enumerate(
    ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}
_ISO_DATE_RE = re.compile(r"\b(20\d\d)-(\d\d)-(\d\d)\b")
_MONTH_DAY_RE = re.compile(r"\b([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(20\d\d))?\b")
_DAY_MONTH_RE = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3})[a-z]*\.?(?:,?\s+(20\d\d))?\b")


def _dates_after_closure_filter(text: str):
    """The dates a copy names — ISO, "Nov 3, 2026", "3 November" — as a test: does any fall
    after a given close? A yearless date takes the close's year, rolled forward if that puts
    it more than half a year before the close."""
    found: list[tuple[int | None, int, int]] = []
    for y, m, d in _ISO_DATE_RE.findall(text or ""):
        found.append((int(y), int(m), int(d)))
    for mon, d, y in _MONTH_DAY_RE.findall(text or ""):
        if mon.lower() in _MONTHS:
            found.append((int(y) if y else None, _MONTHS[mon.lower()], int(d)))
    for d, mon, y in _DAY_MONTH_RE.findall(text or ""):
        if mon.lower() in _MONTHS:
            found.append((int(y) if y else None, _MONTHS[mon.lower()], int(d)))

    def later(closed_on: date | None) -> bool:
        if not closed_on or not found:
            return False
        for y, m, d in found:
            try:
                when = date(y or closed_on.year, m, d)
                if y is None and (closed_on - when).days > 182:
                    when = date(closed_on.year + 1, m, d)
            except ValueError:
                continue
            if when > closed_on:
                return True
        return False
    return later


def consult(text: str, index: list[dict]) -> dict | None:
    """Is this copy about a tracked task? {"entry": ..., "linked": bool}, or None."""
    if not text or not index:
        return None
    ids = set(_TASK_ID_RE.findall(text))
    if ids:
        for e in index:
            if e["id"] in ids:
                return {"entry": e, "linked": True}
    toks = _task_tokens(text)
    later = _dates_after_closure_filter(text)
    best = None
    for e in index:
        if e["terminal"] and later(e.get("closed_on")):
            # A copy naming a date after the close is a later event, not a stale copy: on
            # 2026-10-24 "Meridian Primary School Visit (Nov 3, 2026)" matched the task
            # "Arrange school visits", done 10-20, and was marked not outstanding.
            continue
        if _tokens_match(toks, e["tokens"]):
            shared = len(toks & e["tokens"])
            if best is None or shared > best[0]:
                best = (shared, e)
    return {"entry": best[1], "linked": False} if best else None


def annotation(hit: dict) -> str:
    e = hit["entry"]
    if e["terminal"]:
        if hit["linked"]:
            return f"[task {e['id']}: {e['phrase']} — not outstanding]"
        return (f"[looks like task {e['id']}, {e['phrase']} — not outstanding unless this is "
                f"something else]")
    if e.get("phrase"):
        return f"[tracked as task {e['id']}, {e['phrase']} — not outstanding before then]"
    return f"[tracked as task {e['id']}]"


def annotate(text: str, index: list[dict]) -> str:
    """The copy with its ledger note appended, or unchanged."""
    hit = consult(text, index)
    return f"{text} {annotation(hit)}" if hit else text


# Day-log lists that hold to-do copies. `tasks_completed` is deliberately absent: it records
# completions, and annotating one "done" says nothing the line does not.
_LOG_LIST_PATHS = (("logistics", "pending_items"), ("logistics", "reminders_set"),
                   ("logistics", "horizon_items"), ("logistics", "events_scheduled"),
                   ("intentions",), ("intention",))


def annotate_log_entry(entry: dict, index: list[dict]) -> dict:
    """A copy of a day log with its to-do list entries annotated. The log on disk is a
    record and is never rewritten; only what the model reads is."""
    if not index or not isinstance(entry, dict):
        return entry
    import copy
    out = copy.deepcopy(entry)
    for path in _LOG_LIST_PATHS:
        parent = out
        for key in path[:-1]:
            parent = parent.get(key) if isinstance(parent, dict) else None
        if not isinstance(parent, dict) or path[-1] not in parent:
            continue
        value = parent[path[-1]]
        if isinstance(value, str):
            parent[path[-1]] = annotate(value, index)
            continue
        if not isinstance(value, list):
            continue
        new = []
        for item in value:
            if isinstance(item, str):
                new.append(annotate(item, index))
            elif isinstance(item, dict):
                text = " ".join(str(item.get(k) or "") for k in
                                ("intention", "title", "detail", "item", "what"))
                hit = consult(text, index)
                if hit:
                    item = {**item, "ledger": annotation(hit)}
                new.append(item)
            else:
                new.append(item)
        parent[path[-1]] = new
    return out


# --- The calendar link (plan § 5 row 2) ------------------------------------------------------
# Best-effort by construction: a calendar failure never fails the change that triggered it.
# Linking happens only on an EXACT match — same date, same normalised title — because a
# merely similar event, once linked, would be retitled by code.

_DONE_MARK = "✓ "
_SAFE_UID_RE = re.compile(r"[A-Za-z0-9@._-]{1,120}")


def _norm_title(text: str) -> str:
    lowered = (text or "").strip().lower().lstrip("✓").strip()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", lowered).split())


def link_calendar_exact(title: str, day: str, uid: str, persona: str | None = None) -> str | None:
    """After an all-day calendar write: link the open deadline it exactly names, if any.
    Returns the task id linked, or None."""
    d, norm = _d(day), _norm_title(title)
    if not d or not norm or not uid:
        return None

    def apply(doc: dict):
        for t in doc["tasks"]:
            if (t.get("status") == "open" and t.get("kind") == "deadline"
                    and not t.get("calendar_uid") and _d(t.get("due")) == d
                    and _norm_title(t.get("what", "")) == norm):
                t["calendar_uid"] = uid
                return t["id"]
        return None

    try:
        result = _with_store(persona, apply)
    except Exception:
        return None
    return result if isinstance(result, str) and result.startswith("ob_") else None


def _link_calendar_if_exact(task_id: str) -> None:
    """After open_task: an existing all-day event on the due date with exactly this title."""
    try:
        t = _find([_norm(x) for x in _load()], task_id)
        if not t or t.get("kind") != "deadline" or not _d(t.get("due")):
            return
        from tools.caldav import _query_events
        due = _d(t["due"]).isoformat()
        raw = _query_events(due, due)
        if not isinstance(raw, dict) or "error" in raw:
            return
        for ev in raw.get("events") or []:
            if (str(ev.get("start") or "")[:10] == due
                    and _norm_title(ev.get("title", "")) == _norm_title(t["what"])
                    and ev.get("uid")):
                uid = ev["uid"]

                def apply(doc: dict) -> None:
                    target = _find(doc["tasks"], task_id)
                    if target is not None and not target.get("calendar_uid"):
                        target["calendar_uid"] = uid

                _with_store(None, apply)
                return
    except Exception as exc:  # noqa: BLE001
        logger.info("[tasks] calendar link skipped for %s: %s", task_id, exc)


def _mark_calendar_done(task: dict) -> None:
    """A linked one-off closed done: prefix its calendar entry with ✓ (Mike, decision 3 —
    the calendar stays the visible repository; it stops being a second source of truth)."""
    uid = task.get("calendar_uid")
    if not uid:
        return
    try:
        from tools.caldav import _get_event_by_uid, update_calendar_event
        ev = _get_event_by_uid(uid)
        title = str((ev or {}).get("title") or "")
        if not title or "error" in (ev or {}) or title.startswith(_DONE_MARK.strip()):
            return
        update_calendar_event(uid, title=_DONE_MARK + title)
    except Exception as exc:  # noqa: BLE001
        logger.info("[tasks] calendar mark skipped for %s: %s", task.get("id"), exc)


def _move_calendar(task: dict, new_due: str) -> None:
    """A linked deadline rescheduled: move its all-day entry with it."""
    uid = task.get("calendar_uid")
    if not uid or not new_due:
        return
    try:
        from tools.caldav import update_calendar_event
        update_calendar_event(uid, start=new_due, end=new_due, all_day=True)
    except Exception as exc:  # noqa: BLE001
        logger.info("[tasks] calendar move skipped for %s: %s", task.get("id"), exc)


def calendar_ledger_notes(events: list[dict], persona: str | None = None) -> list[dict]:
    """For read_calendar: what the ledger says about these events. Linked by uid, or matched
    by title to a one-off — code-written, so it travels outside the untrusted wrapper."""
    index = consult_index(persona)
    if not index:
        return []
    by_uid = {e["calendar_uid"]: e for e in index if e.get("calendar_uid")}
    one_offs = [e for e in index if e["kind"] in _ONE_OFF]
    notes = []
    for ev in events or []:
        uid = str(ev.get("uid") or "")
        # A uid on an invited event is chosen by whoever sent the invite. These notes travel
        # outside the untrusted wrapper, so only a uid with nothing but id characters in it
        # is echoed; anything else could carry an instruction past the boundary.
        if not _SAFE_UID_RE.fullmatch(uid):
            continue
        if uid in by_uid:
            notes.append({"uid": uid, "note": annotation({"entry": by_uid[uid], "linked": True})})
            continue
        hit = consult(str(ev.get("title") or ""), one_offs)
        if hit:
            notes.append({"uid": uid, "note": annotation(hit)})
    return notes


# --- Medication taken: a view over the ledger, never a second store ---------------------------
# Ruling D11 (archive/plans/agent_instructions_to_code_sweep_2026-11-23.md): "medication taken
# today" is a default data object, and the owner chose a READ-ONLY VIEW over the records that
# already exist — one record per dose, nothing new to log. A dose is a habit occurrence marked
# done here; a store that doses are also written into was rejected, because in a hard-fail domain
# two records of one dose can disagree. So this reads the ledger and writes nothing, ever: not
# the store, not the lock file, not the v1 import `_load` would persist.
#
# What the ledger keeps per dose: the day it counts for (`on`) and when it was RECORDED (`at`).
# It does not keep when the dose was taken — "I took it at 8" recorded at noon reads 12:00 — so
# the field is named `recorded_at`, never `taken_at`. After the nightly sweep a past day keeps
# only its count (task_history.jsonl), so `dose_times` says whether the times are still known.
#
# WHICH HABITS ARE MEDICATION: an explicit link, never a name (owner's ruling, 2026-11-23). A
# habit is a dose habit when it carries `medication` — the name of an entry in the stored
# medication_profile, checked against the profile when it is set (open_task's `medication`,
# update_task's `set_medication`) and stored in the profile's own spelling. Nothing is guessed:
# `domain` and `activity` are free text shared with exercise and stretching, and `_MEDICATION_RE`
# is a name net that matches "dog tablets from the vet" and misses every drug named by name.
#
# The profile is the authority on WHAT the user takes (criticality, discontinuation_risk, dose,
# schedule — Physical Health's, behind the confirm gate); the ledger is the authority on what was
# DONE. Each row joins the two. A profile entry no active habit links appears with
# `linked: False`, and for it the daily log's `medications_logged` is the record (see "Unlinked
# medicines" below) — so a required medicine nobody linked is still checked, never silent.

_PROFILE_FIELDS = ("criticality", "discontinuation_risk", "dose", "schedule")


def _profile_medications() -> tuple[list[dict] | None, str]:
    """The stored medication_profile's entries for the bound persona, read from the file (not
    read_agent_config's message strings). ([], "") when there is no profile; (None, why) when
    there is one and it cannot be read — never a guess at what it says."""
    try:
        from tools.agent_config import _agent_config_dir
        path = _agent_config_dir() / "physical_health.json"
        if not path.exists():
            return [], ""
        data = json.loads(path.read_text())
        raw = data.get("medication_profile") if isinstance(data, dict) else None
        if raw is None:
            return [], ""
        if isinstance(raw, str):
            raw = json.loads(raw) if raw.strip() else {}
        meds = raw.get("medications", []) if isinstance(raw, dict) else raw
        if not isinstance(meds, list):
            return None, "it holds no list of medications"
        return [m for m in meds if isinstance(m, dict) and str(m.get("name") or "").strip()], ""
    except Exception:  # noqa: BLE001
        return None, "it could not be parsed"


def _med_key(name) -> str:
    return " ".join(str(name or "").split()).casefold()


def _criticality_of(name) -> str | None:
    """The profile's criticality for a linked medication name; None when the profile cannot be
    read, holds no such entry, or the entry gives none. Callers read None as UNKNOWN."""
    meds, _why = _profile_medications()
    if not meds:
        return None
    hit = next((m for m in meds if _med_key(m["name"]) == _med_key(name)), None)
    crit = str((hit or {}).get("criticality") or "").strip().lower()
    return crit or None


# Who may set or change a habit's `medication` link (review 2026-11-23, item 8): the Synthesizer,
# which records doses, the two health agents, and code with no agent bound. Finance and Logistics
# hold open_task and update_task too; they get one refusal, the same whatever name they gave, so
# the refusal is never an oracle for what the profile holds.
_LINK_SETTERS = frozenset({"synthesizer", "physical_health", "mental_wellbeing"})
_LINK_REFUSAL = ("error: a habit's `medication` link is not set from here — the Synthesizer sets "
                 "it. Open or keep the habit without `medication`. Nothing was written.")


def _may_set_link() -> bool:
    try:
        from tools import data_objects as DO
        agent = DO._caller()
    except Exception:  # noqa: BLE001 — cannot tell who is asking: refuse
        return False
    return not agent or agent in _LINK_SETTERS


def _second_link(tasks: list[dict], name: str, except_id: str | None = None) -> str | None:
    """A refusal when another open habit is already linked to `name` (review item 6): two habits
    on one medicine would split its doses between two counts, and the view would show both."""
    key = _med_key(name)
    other = next((t for t in tasks if t.get("id") != except_id
                  and t.get("kind") == "habit" and t.get("status", "open") == "open"
                  and _med_key(t.get("medication")) == key and key), None)
    if other is None:
        return None
    return (f"error: {name!r} is already linked to {other['id']} ({other.get('what', '?')}). "
            f"One habit per medication — a second daily dose is that habit's `times`, not a "
            f"second habit. Unlink that one first (set_medication with an empty name) if this "
            f"one should carry it instead. Nothing was written.")


def _renamed_to(old_name, new_name) -> bool:
    """Is `new_name` plausibly the profile's new spelling of `old_name` — it starts with it, or
    holds every one of its words ("Atorvastatin" → "Atorvastatin 40mg")? Used only to join or
    relink when EXACTLY ONE profile name qualifies; never to read a name the user said."""
    old, new = _med_key(old_name), _med_key(new_name)
    if not old or not new or old == new:
        return False
    return new.startswith(old) or set(old.split()) <= set(new.split())


def relink_after_profile_write(persona: str | None = None) -> list[str]:
    """After the medication profile is written (tools/agent_config.write_agent_config): an open
    habit whose linked name the profile no longer holds follows the new spelling, when exactly one
    new, unlinked profile name is its rename (`_renamed_to`) and no other broken habit claims the
    same one. Recorded in the habit's history. Returns one line per relink; never raises."""
    try:
        meds, _why = _profile_medications()
        if not meds:
            return []
        names = {_med_key(m["name"]): str(m["name"]).strip() for m in meds}

        def apply(doc: dict) -> list[str]:
            habits = [t for t in doc["tasks"] if t.get("kind") == "habit"
                      and t.get("status", "open") == "open" and str(t.get("medication") or "").strip()]
            held = {_med_key(t["medication"]) for t in habits}
            broken = [t for t in habits if _med_key(t["medication"]) not in names]
            picks: dict[str, list[dict]] = {}
            for t in broken:
                cands = [k for k in names if k not in held and _renamed_to(t["medication"], k)]
                if len(cands) == 1:
                    picks.setdefault(cands[0], []).append(t)
            out = []
            for key, ts in picks.items():
                if len(ts) != 1:
                    continue
                t, new = ts[0], names[key]
                t.setdefault("history", []).append({
                    "event": "medication_relinked", "at": _stamp(), "from": t["medication"],
                    "to": new, "reason": "the medication profile now spells it this way"})
                out.append(f"the habit for {t['medication']!r} now follows its new name {new!r}")
                t["medication"] = new
            return out
        result = _with_store(persona, apply)
        return result if isinstance(result, list) else []
    except Exception as exc:  # noqa: BLE001
        logger.warning("[tasks] medication relink skipped: %s", exc)
        return []


def _import_logged_doses(t: dict, day: date) -> int:
    """When a habit is linked to a medicine (open_task's `medication`, set_medication), the doses
    already logged as taken for it that ledger day become done occurrences on the habit (second
    review, finding 1) — without this, linking at noon erased the morning's logged dose and the
    medicine read missed. Capped at the period's count. Returns how many were imported."""
    logged = _logged_entries(day) or {}
    taken = [e for e in logged.get(_med_key(t.get("medication")), []) if e.get("taken") is True]
    if not taken:
        return 0
    every = t.get("every") if t.get("every") in _EVERY else "day"
    pk = _period(every, day)[0]
    occ = t.setdefault("occurrences", {}).setdefault(pk, {"done": 0, "completions": []})
    room = max(0, _habit_target(t) - int(occ.get("done") or 0))
    n = 0
    for e in taken[:room]:
        occ["done"] = int(occ.get("done") or 0) + 1
        occ.setdefault("completions", []).append({
            "on": day.isoformat(), "at": str(e.get("logged_at") or _stamp()),
            "evidence": "logged as taken in the daily log before the habit was linked",
            "source": "daily_log"})
        t.setdefault("recent_completions", []).append({"on": day.isoformat()})
        n += 1
    t["recent_completions"] = (t.get("recent_completions") or [])[-40:]
    return n


def linked_medication_keys(persona: str | None = None) -> set[str] | None:
    """The medications (as `_med_key`) that an open habit carries a link to — the medicines whose
    doses are recorded in the ledger. None when the store cannot be read: a caller must then treat
    every medicine as unlinked, never as linked (tools/logger.write_log keeps the daily-log entry,
    which is the safe direction — a kept record cannot silence a miss)."""
    try:
        doc = _load_doc(persona)
    except Exception:  # noqa: BLE001
        return None
    return {_med_key(t.get("medication")) for t in doc.get("tasks") or []
            if isinstance(t, dict) and t.get("kind") == "habit"
            and t.get("status", "open") == "open" and str(t.get("medication") or "").strip()}


def _may_see_profile() -> bool:
    """May this caller be shown the profile's names? Only an agent the medication view's read
    rule admits (the health agents and the standing readers), or code. Finance and Logistics
    hold open_task too, and a refusal must not hand them the user's medication list."""
    try:
        from tools import data_objects as DO
        agent = DO._caller()
        return not agent or agent in DO.readers(DO.get("medication_taken") or {"class": "health"})
    except Exception:  # noqa: BLE001
        return False


def _medication_link(raw: str) -> tuple[str | None, str | None]:
    """(the profile's own spelling of `raw`, None), or (None, a refusal the model can act on).
    Matched whole, ignoring case and spacing — never in part."""
    meds, why = _profile_medications()
    if meds is None:
        return None, (f"error: the user's medication profile could not be read ({why}), so "
                      f"`medication` cannot be checked. Nothing was written.")
    if not meds:
        return None, ("error: the user's medication profile names no medications yet, so this "
                      "habit cannot be linked to one. Open or keep the habit without "
                      "`medication`; Physical Health adds the medication to the profile, with "
                      "the user's approval, and the link is made then. Nothing was written.")
    hit = next((m for m in meds if _med_key(m["name"]) == _med_key(raw)), None)
    if hit:
        return str(hit["name"]).strip(), None
    names = (f" It names: {', '.join(str(m['name']).strip() for m in meds)}."
             if _may_see_profile() else "")
    return None, (f"error: {str(raw).strip()!r} is not a medication in the user's stored "
                  f"profile.{names} Give the name exactly as the profile has it, or leave "
                  f"`medication` unset until the profile has it. Nothing was written.")


def _set_medication(task_id: str, medication: str | None, done_words,
                    evidence: str | None) -> str:
    """update_task's `set_medication`: link a habit to a profile medication (an empty string
    unlinks it). The habit's own done words are kept; the caller's are used only when it has
    none — never invented here."""
    if not _may_set_link():
        return _LINK_REFUSAL
    if medication is None:
        return ("error: `medication` is required for set_medication — the name exactly as the "
                "user's medication profile gives it, or an empty string to unlink. Nothing was "
                "written.")
    name = None
    if str(medication).strip():
        name, err = _medication_link(medication)
        if err:
            return err
    words = _clean_done_words(done_words)
    tid = _split_id(task_id)

    def apply(doc: dict) -> str:
        t = _find(doc["tasks"], tid)
        if t is None:
            return f"error: no task with id {task_id!r}"
        if t.get("kind") != "habit":
            return (f"error: only a habit can be linked to a medication — {tid} is a "
                    f"{t.get('kind')}. Nothing was written.")
        if t.get("status", "open") != "open":
            return f"error: {tid} is {t.get('status')}, not open. Nothing was written."
        if name:
            clash = _second_link(doc["tasks"], name, except_id=tid)
            if clash:
                return clash
        was = t.get("medication")
        t.setdefault("history", []).append({
            "event": "medication_linked" if name else "medication_unlinked", "at": _stamp(),
            "name": name or was, **({"reason": evidence.strip()} if evidence else {})})
        note = ""
        if name:
            t["medication"] = name
            n = _import_logged_doses(t, _today()) if _med_key(was) != _med_key(name) else 0
            if n:
                note = f"; {n} dose(s) already logged as taken today counted on it"
        else:
            t.pop("medication", None)
        if words and not t.get("done_words"):
            t["done_words"] = words
        elif words:
            note += "; it keeps the done words it already had"
        state = f"linked to {name!r} in the medication profile" if name else "unlinked"
        return f"{tid} {state}: {_summarise(t)}{note}"
    return _with_store(None, apply)


_REPEAT_DOSE_WINDOW = timedelta(minutes=10)


# Words in the evidence that say how many doses it reports ("took both", "my second one",
# "2 doses"). A fixed list, never inferred: it only ever PERMITS a dose the repeat guard would
# otherwise refuse, and the cap at the period's count still holds.
_DOSE_COUNT_WORDS = {"both": 2, "twice": 2, "second": 2, "two": 2, "third": 3, "three": 3,
                     "thrice": 3, "fourth": 4, "four": 4}
_DOSE_COUNT_RE = re.compile(r"\b(\d{1,2})\s*(?:doses?|pills?|tablets?|capsules?|times)\b")


def _dose_quantity(evidence: str | None) -> int:
    """How many doses the evidence says it reports, or 0 when it names no number."""
    low = str(evidence or "").lower()
    found = [n for w, n in _DOSE_COUNT_WORDS.items() if re.search(rf"\b{w}\b", low)]
    found += [int(m.group(1)) for m in _DOSE_COUNT_RE.finditer(low)]
    return max(found) if found else 0


def _dose_label(t: dict) -> str:
    """The medicine's name for a refusal — only to a caller that may see the link (review item 7:
    Finance and Logistics hold update_task, and a refusal must not name a profile entry)."""
    return str(t.get("medication")) if _may_set_link() else "this medication"


def _dose_refusal(t: dict, occ: dict, every: str, on_iso: str, evidence: str | None) -> str | None:
    """For a linked medication habit only: refuse a "done" that would count more doses than the
    period expects, or that repeats a dose recorded for the SAME day (`on`) of the SAME period in
    the last 10 minutes — a retried call or one report heard twice. Either would read as a dose
    taken and could hide a missed one. A dose for another day (yesterday's, reported now) is never
    a repeat; evidence that quantifies ("both", "two", "2 doses", "second") permits up to that
    many. Other habits keep counting past their target, as before."""
    done, target = int(occ.get("done") or 0), _habit_target(t)
    span = ("today" if on_iso == _today().isoformat() else f"for {on_iso}") \
        if every == "day" else f"this {every}"
    if done >= target:
        return (f"error: already recorded {done} of {target} {span} for {_dose_label(t)} — not "
                f"counted again. If the user says they took an extra dose, that is for Physical "
                f"Health to hear, not a dose to record here. Nothing was changed.")
    if done < _dose_quantity(evidence):
        return None
    now = _now()
    for c in reversed(occ.get("completions") or []):
        if str((c or {}).get("on") or "") != on_iso:
            continue
        try:
            at = datetime.fromisoformat(str((c or {}).get("at") or ""))
        except ValueError:
            continue
        if timedelta(0) <= now - at < _REPEAT_DOSE_WINDOW:
            mins = int((now - at).total_seconds() // 60)
            return (f"error: a dose of {_dose_label(t)} for that day was recorded on this habit "
                    f"{'just now' if mins < 1 else f'{mins} minute(s) ago'} — this reads as the "
                    f"same dose reported twice, so it was not counted again. Do not retry. If the "
                    f"user took more than one, record it with their words saying how many "
                    f"(\"both\", \"two\"). Nothing was changed.")
    return None


def _skip_one_dose(t: dict, occ: dict, tid: str, pk: str, every: str, evidence: str) -> str:
    """update_task "skipped" on a linked medication habit: one DOSE skipped, not the period
    (second review, finding 4 — one skip of a 3-a-week medicine hid the other two). The count is
    `skipped_doses`; the old period-wide `skipped` flag is set only once every dose of the period
    is done or skipped, so the ledger stops asking exactly then. A legacy `skipped: true` with no
    count reads as one."""
    n = int(occ.get("skipped_doses") or (1 if occ.get("skipped") else 0))
    target, done = _habit_target(t), int(occ.get("done") or 0)
    if done + n >= target:
        return (f"error: every dose of {tid}@{pk} is already done or skipped "
                f"({done} done, {n} skipped of {target}). Nothing was changed.")
    occ["skipped_doses"] = n + 1
    occ.setdefault("skip_reasons", []).append(evidence)
    if done + n + 1 >= target:
        occ["skipped"] = True
        occ["skip_reason"] = evidence
    return (f"{tid}@{pk}: one dose skipped ({n + 1} skipped, {done} done of {target} this "
            f"{every}) — left out of adherence")


def _medication_habits(tasks: list[dict]) -> list[dict]:
    """The habits that are medication doses: those carrying a `medication` link — never a habit
    whose name looks like a medicine."""
    return [t for t in tasks if str(t.get("medication") or "").strip()]


def _active_on(t: dict, day: date) -> bool:
    """Was this habit in force on `day` — started by then, and not closed before it."""
    start = _start(t)
    if start and start > day:
        return False
    if t.get("status", "open") in _TERMINAL:
        closed = _stamp_day(t.get("closed_at"))
        return bool(closed and closed > day)
    return True


def _doses_on(t: dict, day: date, history: dict[str, dict]) -> dict:
    """One medication habit's record for `day`: expected, done, and each dose's record."""
    every = t.get("every") if t.get("every") in _EVERY else "day"
    pk, _ps, _pe = _period(every, day)
    occ = (t.get("occurrences") or {}).get(pk)
    row = {"task_id": t["id"], "what": t.get("what", ""), "every": every, "period": pk,
           "expected": _habit_target(t), "done": 0, "skipped": False, "skipped_count": 0,
           "doses": [], "dose_times": "recorded"}
    eligible = _d(t.get("eligible_from"))
    if eligible and eligible > day:
        row["paused_until"] = eligible.isoformat()
    if isinstance(occ, dict):
        row["done"] = max(0, int(occ.get("done") or 0))
        row["skipped"] = bool(occ.get("skipped"))
        # Per dose (second review, finding 4); a legacy period-wide skip with no count is one.
        row["skipped_count"] = max(0, int(occ.get("skipped_doses")
                                          or (1 if occ.get("skipped") else 0)))
        row["doses"] = [{"on": str(c.get("on") or ""), "recorded_at": str(c.get("at") or "")}
                        for c in occ.get("completions") or [] if isinstance(c, dict)]
        return row
    past = history.get(f"{t['id']}@{pk}")
    if past:
        # Swept: the count is on file, the times are not.
        row["done"] = max(0, int(past.get("done") or 0))
        row["skipped"] = past.get("state") == "skipped"
        row["skipped_count"] = 1 if row["skipped"] else 0
        row["dose_times"] = "not_kept" if row["done"] else "recorded"
    return row


# --- When a dose is due (review 2026-11-23, item 3) -------------------------------------------
# `done < expected` flagged a weekly Friday medicine every day from Monday, and the evening dose
# of a twice-daily one from the morning. `due_now` is how many of the period's doses are due by
# now — by the END of `day` for a day already over — and `missed` is `due_now > done`, never for
# an occurrence the user skipped or a habit that is paused. The rules, from what the ledger
# actually knows about a habit (a count per period, an optional earliest time `after`, and for a
# week its planned weekdays or for a month its window of days — never per-dose times):
#
#   - every day, once: due from the day's start (the day boundary, `day_starts`), or from its
#     `after` time when it has one ("evening statin, after 20:00").
#   - every day, N times: the FIRST dose is due by midday (or from `after`, when set); the rest
#     only by the day's end — the ledger cannot say when a later dose was meant, so it never calls
#     one missed while the day is still running. A day that is over owes all N.
#   - every week with planned days: one per planned day reached, up to `times` (a Friday habit
#     on a Tuesday owes 0; on Friday, 1 — from `after` when set).
#   - every week or month as a quota with no days: due only when the doses left can no longer fit
#     in the days left (`times` − days remaining after `day`) — the ledger's own "needed today to
#     stay on target". A first period the habit started part-way through owes nothing, as the
#     ledger's sweep already excludes it from adherence.
#   - every month with a window (the 10th–15th): nothing before the window opens; then the same
#     quota rule against its last day; everything after it.
#
# THE CREATION DAY (second review, finding 1): a habit owes no dose that fell due before it
# existed. On the ledger day it was created, a dose whose due moment is earlier than `created_at`
# is not owed — a once-daily habit (due from the day's start) created at 21:00, or at 09:00, owes
# nothing until the next day; a twice-daily one created at 13:00 owes only its end-of-day dose; a
# Friday habit created on a Friday afternoon owes nothing that Friday. A quota or window habit is
# forgiven the one slot of its creation day. The doses the user DID take that day are not lost to
# this: linking imports the day's logged doses (`_import_logged_doses`), and a dose reported after
# creation is recorded as usual.
_MIDDAY = (12, 0)


def _created_moment(t: dict) -> datetime | None:
    try:
        return datetime.fromisoformat(str(t.get("created_at") or ""))
    except ValueError:
        return None


def _on_ledger_day(day: date, hm: tuple[int, int], boundary: timedelta) -> datetime:
    """The moment HH:MM falls inside the ledger day `day`: a time before the day's start belongs
    to the next calendar date (02:00 on a day that starts at 04:00 is that night, not that
    morning)."""
    offset = timedelta(hours=hm[0], minutes=hm[1])
    moment = datetime.combine(day, datetime.min.time()) + offset
    return moment + timedelta(days=1) if offset < boundary else moment


def _due_now(t: dict, day: date, now: datetime, today: date) -> int:
    """How many of this habit's doses for the period holding `day` are due by now (by the end of
    `day` once it is over). Pure; see the rules above."""
    if day > today:
        return 0
    every = t.get("every") if t.get("every") in _EVERY else "day"
    target = _habit_target(t)
    after = _parse_hhmm(t.get("after"))
    boundary = _day_starts()
    created = _created_moment(t)

    def starts(d: date) -> datetime:
        return datetime.combine(d, datetime.min.time()) + boundary

    def owed(moment: datetime) -> bool:
        """Due by now, and not due before the habit existed."""
        return now >= moment and (created is None or moment >= created)

    if every == "day":
        first = _on_ledger_day(day, after, boundary) if after else (
            _on_ledger_day(day, _MIDDAY, boundary) if target > 1 else starts(day))
        moments = [first] + [starts(day + timedelta(days=1))] * (target - 1)
        return sum(1 for m in moments if owed(m))
    _pk, ps, pe = _period(every, day)
    start = _start(t)
    # A quota or window habit is forgiven the slot of the day it was created on.
    forgive = 1 if created and _ledger_day(created) == day and created > starts(day) else 0
    mdays = _month_window(t)
    if mdays:
        n_days = (pe - ps).days + 1
        window = sorted({min(d, n_days) for d in mdays})
        opens, by = ps.replace(day=window[0]), ps.replace(day=window[-1])
        if (start and start > by) or day < opens:
            return 0
        return max(0, target - max(0, (by - day).days) - forgive)
    preferred = [d for d in (t.get("on_days") or []) if d in _WEEKDAYS] if every == "week" else []
    if preferred:
        first = max(ps, start) if start else ps
        planned = 0
        for i in range((day - first).days + 1):
            d = first + timedelta(days=i)
            moment = _on_ledger_day(d, after, boundary) if after else starts(d)
            if _WEEKDAYS[d.weekday()] in preferred and owed(moment):
                planned += 1
        return min(planned, target)
    if start and start > ps:
        return 0
    return max(0, target - (pe - day).days - forgive)


def _dose_state(t: dict, day: date, row: dict, now: datetime, today: date) -> dict:
    """`due_now`, `paused` and `missed` for a linked row. Paused: not yet eligible on `day` (a
    deferral — the ledger's `dormant`). Missed: more doses due than done plus skipped — skips
    count per dose — and not paused."""
    paused = bool(row.get("paused_until")) or _view(t, day)["state"] == "dormant"
    due = 0 if paused else _due_now(t, day, now, today)
    accounted = int(row.get("done") or 0) + int(row.get("skipped_count") or 0)
    return {"due_now": due, "paused": paused, "missed": bool(due > accounted and not paused)}


# --- Unlinked medicines: the daily log is their only record (review 2026-11-23, item 1) -------
# "One record per dose" is applied per medicine: a medicine with an active linked habit keeps its
# doses in the ledger, and write_log drops its `medications_logged` entries; a medicine with NO
# habit keeps them, because for it that entry is the only record. So an unlinked row carries that
# day's log evidence, and the old rule — required and not logged today, missed — still applies.

def _logged_entries(day: date) -> dict[str, list[dict]] | None:
    """The LEDGER day's `medications_logged` entries, by `_med_key` of their name, from the bound
    persona's daily logs (health.medications_logged, and a misplaced top-level one). {} when there
    are none; None when a log that could hold them cannot be read. A pure file read: no index, no
    write.

    A log file is dated by the machine's calendar, the view by the persona's ledger day (its
    `day_starts` and timezone) — second review, finding 5: a dose logged at 01:30 on a day that
    starts at 04:00 sits in the next date's file but belongs to the day before. So each entry is
    placed by its `logged_at` (stamped by write_log, persona-local), read from the same-date file
    and both neighbours; an entry from before the stamp existed falls back to its file's date."""
    try:
        from tools.logger import _logs_dir
        out: dict[str, list[dict]] = {}
        for offset in (-1, 0, 1):
            file_day = day + timedelta(days=offset)
            path = _logs_dir() / f"{file_day.isoformat()}.json"
            if not path.exists():
                continue
            data = json.loads(path.read_text())
            if not isinstance(data, dict):
                return None
            health = data.get("health") if isinstance(data.get("health"), dict) else {}
            raw = list(health.get("medications_logged") or [])
            raw += list(data.get("medications_logged") or [])
            for e in raw:
                if not (isinstance(e, dict) and str(e.get("name") or "").strip()):
                    continue
                placed = _stamp_day(e.get("logged_at")) if e.get("logged_at") else None
                if (placed or file_day) == day:
                    out.setdefault(_med_key(e["name"]), []).append(e)
        return out
    except Exception:  # noqa: BLE001
        return None


def _unlinked_row(entry: dict, logged: dict[str, list[dict]] | None) -> dict:
    """A profile entry no active habit links on the day. `logged`: True when the day's log holds
    an entry for it not marked `taken: false`; False when it holds none (or only `taken: false`);
    None when the log could not be read. `missed` is the old rule on that evidence — never for
    an `as_needed` medicine, which is taken when needed and so is never due; None when UNKNOWN.
    `needs_link`: a required medicine with no habit — its doses can only be tracked by a link."""
    crit = str(entry.get("criticality") or "").strip().lower()
    entries = None if logged is None else logged.get(_med_key(entry["name"]), [])
    took = None if entries is None else any(e.get("taken") is not False for e in entries)
    missed = False if crit == "as_needed" else (None if took is None else not took)
    return {"medication": str(entry["name"]).strip(), "linked": False, "in_profile": True,
            **{k: entry.get(k) for k in _PROFILE_FIELDS},
            "task_id": None, "expected": None, "done": None, "doses": [],
            "logged": took, "logged_entries": entries if entries is not None else [],
            "due_now": None, "paused": False, "skipped": False, "skipped_count": 0,
            "missed": missed,
            "needs_link": crit == "required", "link_broken": False}


def medication_taken(persona: str | None = None, day: date | None = None) -> dict:
    """What medication was taken on `day` (default: today, on the persona's own clock and day
    boundary): the ledger's linked dose habits, joined to the stored medication profile. Pure
    reads; never raises.

    Returns {"ok": bool, "day": "YYYY-MM-DD", "medications": [row, …], "reason"?: str}.
    Every row carries: medication, linked, in_profile, criticality, discontinuation_risk, dose,
    schedule, task_id, expected, done, doses, due_now, paused, skipped, skipped_count, missed,
    needs_link, link_broken.

    A linked row (an active habit carries the link): task_id, what, every, period, expected
    (the period's doses), done, skipped (the whole period), skipped_count (doses skipped),
    doses: [{on, recorded_at}], dose_times: "recorded" | "not_kept", paused_until?; `due_now` —
    doses due by now (see "When a dose is due", and its creation-day rule); `paused`;
    `missed` = due_now > done + skipped_count, not paused; `link_broken` = the profile no longer
    holds the name (`in_profile` False) — reported, never dropped. When exactly one unlinked
    profile name is its rename, the row is joined to it: `medication` and the profile fields are
    the new entry's, `linked_name` is the habit's old name, `relink_to` the new one.

    An unlinked row (a profile entry no active habit links that day): task_id/expected/done None,
    doses [], due_now None, and that day's daily-log evidence — `logged` (True / False / None when
    the log cannot be read) and `logged_entries`; `missed` = not logged (None when unknown; never
    for `as_needed`); `needs_link` True for a `required` medicine.

    `ok` False means the view could not be computed — no persona, an unreadable store or profile
    — and a caller must read that as UNKNOWN, never as "nothing taken" or "nothing missed"."""
    out: dict = {"ok": False, "day": day.isoformat() if isinstance(day, date) else "",
                 "medications": []}
    try:
        from core.persona import persona_scope, resolve_persona
        p = resolve_persona(persona)
    except Exception:  # noqa: BLE001 — fail closed: no persona, nobody's record
        out["reason"] = "no user is bound to this read"
        return out
    try:
        with persona_scope(p):
            day = day if isinstance(day, date) else _today()
            out["day"] = day.isoformat()
            try:
                doc = _load_doc(p)
            except StoreUnreadable:
                out["reason"] = "the task store could not be read"
                return out
            habits = [t for t in doc.get("tasks") or []
                      if isinstance(t, dict) and t.get("kind") == "habit" and t.get("id")]
            meds, _why = _profile_medications()
            if meds is None:
                out["reason"] = "the medication profile could not be read"
                return out
            profile = {_med_key(m["name"]): m for m in meds}
            history = {str(r.get("key")): r for r in _history_rows(p)
                       if r.get("kind") == "habit" and r.get("key")}
            now, today = _now(), _today()
            rows, linked = [], set()
            for t in _medication_habits(habits):
                if not _active_on(t, day):
                    continue
                key = _med_key(t["medication"])
                entry = profile.get(key)
                linked.add(key)
                row = {"medication": str(t["medication"]).strip(), "linked": True,
                       "in_profile": entry is not None,
                       **{k: (entry or {}).get(k) for k in _PROFILE_FIELDS},
                       **_doses_on(t, day, history)}
                row.update(_dose_state(t, day, row, now, today))
                # A link the profile no longer holds (renamed, removed) is reported, never
                # dropped: its doses may be the only record of a medicine the user still takes.
                row.update(needs_link=False, link_broken=entry is None)
                rows.append(row)
            # A renamed medicine (second review, finding 2): a broken link and exactly one
            # unlinked profile name that is its new spelling are one medicine. The row takes the
            # new entry's profile fields and keeps the habit's doses, so the rename alone never
            # reads as a missed dose; `relink_to` names the profile spelling to link to.
            unlinked = [k for k in profile if k not in linked]
            claims: dict[str, list[dict]] = {}
            for row in rows:
                if row["link_broken"]:
                    cands = [k for k in unlinked if _renamed_to(row["medication"], k)]
                    if len(cands) == 1:
                        claims.setdefault(cands[0], []).append(row)
            for key, claimants in claims.items():
                if len(claimants) != 1:
                    continue
                entry, row = profile[key], claimants[0]
                row.update({k: entry.get(k) for k in _PROFILE_FIELDS})
                row.update(linked_name=row["medication"], medication=str(entry["name"]).strip(),
                           relink_to=str(entry["name"]).strip())
                linked.add(key)
            logged = _logged_entries(day) if any(k not in linked for k in profile) else {}
            for key, entry in profile.items():
                if key not in linked:
                    rows.append(_unlinked_row(entry, logged))
            out["medications"] = rows
            out["ok"] = True
            return out
    except Exception as exc:  # noqa: BLE001 — a view must never take down its caller
        logger.warning("[tasks] medication view unavailable: %s", exc)
        out["medications"] = []
        out["ok"] = False
        out["reason"] = "the medication record could not be read"
        return out


# --- Doses Physical Health reports: recorded by code (second review, A1) ---------------------
# The owner's standing preference is code over agents wherever an agent is not needed. A dose
# Physical Health hears used to reach the ledger only if the Synthesizer called update_task, and
# then only if the close gate found the user's words naming the habit — so a dose PH had already
# identified by its profile name could be refused, and the medicine read missed. Now code reads
# PH's line and records the dose itself.
#
# THE LINE, exactly:   MEDICATION_TAKEN: <name>[ at <time>]; <name>[ at <time>]; …
#   - doses TAKEN only, each by its name exactly as the medication profile gives it;
#   - the line may sit anywhere in PH's output, with list or emphasis marks before the key;
#   - items are split on ";" (a "," or newline does not split — a name never contains ";");
#   - " at <time>" and surrounding quotes, backticks and a trailing full stop are dropped;
#   - "none", "-", "n/a" and empty items are ignored;
#   - a name repeated k times is k doses.
# Parsed tolerantly but NEVER fuzzily: a name counts only when it equals a profile name (case and
# spacing ignored) AND an open habit is linked to it. Anything else is left alone — Physical
# Health's own `medications_logged` write is the record for a medicine with no habit.
_TAKEN_LINE_RE = re.compile(r"^[ \t>*_`#-]*MEDICATION_TAKEN[ \t*_`]*:(?P<items>.*)$",
                            re.IGNORECASE | re.MULTILINE)
_TAKEN_AT_RE = re.compile(r"\s+at\s+\S.*$", re.IGNORECASE)
_TAKEN_NONE = {"", "none", "-", "n/a", "na", "nothing", "omit"}


def parse_medication_taken(text: str) -> list[str]:
    """The names on Physical Health's `MEDICATION_TAKEN:` line(s), one per dose, as written (see
    the format above). Pure; never raises."""
    names: list[str] = []
    for m in _TAKEN_LINE_RE.finditer(str(text or "")):
        for item in m.group("items").split(";"):
            name = _TAKEN_AT_RE.sub("", item.strip()).strip().strip("`'\"*_").rstrip(".").strip()
            if name.casefold() not in _TAKEN_NONE and not name.startswith("["):
                names.append(name)
    return names


def record_reported_doses(text: str, persona: str | None = None) -> list[str]:
    """Record each dose on Physical Health's `MEDICATION_TAKEN:` line on its linked habit — with
    no agent bound, on the persona's ledger day, the line as evidence. Returns one line per
    medicine for the Synthesizer's note ("Atorvastatin (1 of 1 today)", or "… — already recorded,
    not counted again"); [] when nothing was recorded. Never raises."""
    try:
        from core.persona import persona_scope, resolve_persona
        names = parse_medication_taken(text)
        if not names:
            return []
        p = resolve_persona(persona)
        line = next((m.group(0).strip() for m in _TAKEN_LINE_RE.finditer(text)), "")[:300]
        with persona_scope(p):
            meds, _why = _profile_medications()
            profile = {_med_key(m["name"]): str(m["name"]).strip() for m in meds or []}
            habits = {_med_key(t.get("medication")): t for t in _load(p)
                      if t.get("kind") == "habit" and t.get("status", "open") == "open"
                      and str(t.get("medication") or "").strip()}
            counts: dict[str, int] = {}
            for n in names:
                if _med_key(n) in profile and _med_key(n) in habits:
                    counts[_med_key(n)] = counts.get(_med_key(n), 0) + 1
            out = []
            for key, k in counts.items():
                t, shown = habits[key], profile[key]
                evidence = f"Physical Health reported {k} dose{'s' if k != 1 else ''}: {line}"
                result, last_ok = "", ""
                with _code_act():
                    for _ in range(k):
                        result = update_task(t["id"], "done", evidence=evidence)
                        if str(result).startswith("error:"):
                            break
                        last_ok = result
                # The count after the last dose that WAS recorded, when one was.
                m = re.search(r"recorded: (\d+) of (\d+) this (\w+)", str(last_ok or result))
                if m:
                    span = "today" if m.group(3) == "day" else f"this {m.group(3)}"
                    out.append(f"{shown} ({m.group(1)} of {m.group(2)} {span})")
                elif "already recorded" in str(result) or "reported twice" in str(result):
                    out.append(f"{shown} — already recorded, not counted again")
                else:
                    logger.warning("[tasks] reported dose not recorded for %s: %s", shown,
                                   str(result)[:160])
            return out
    except Exception as exc:  # noqa: BLE001 — a dose note must never take down the turn
        logger.warning("[tasks] reported doses not recorded: %s", exc)
        return []


def reported_doses_note(lines: list[str]) -> str:
    """The Synthesizer's line for doses code recorded this turn; "" when none."""
    if not lines:
        return ""
    return ("MEDICATION NOTE (from code): Recorded by code: " + "; ".join(lines) + ". These "
            "doses are already in the record — do not record them again, and never tell the "
            "user a dose was not recorded.")


# --- The ledger's tool surface ---------------------------------------------------------------
# Registered in core/orchestrator.py, classified in core/actions.py, granted to synthesizer,
# finance and logistics in both routing files. They replaced the four v1 tools
# (open/close/reopen/list_obligation(s)) outright on 2026-10-23 — removed, not kept as aliases:
# a replaced mechanism left alongside its replacement is a second way to do one thing.

OPEN_TASK_SCHEMA = {
    "name": "open_task",
    "description": (
        "Record something the user has to do, or is waiting on, so it is tracked until it is "
        "done. Code then decides when it is due, overdue or missed, and shows it in your "
        "context under Tasks — do not also set a reminder for it elsewhere. Kinds: "
        "deadline — a one-off, by a date if there is one (pay a bill, return a form); "
        "habit — repeats per period (stretch daily; gym three times a week, preferably "
        "Mon/Wed/Fri; a medication twice a day); interval — every N days counted from when it "
        "was last done (water the plants every 3 days); waiting — someone else's move the user "
        "is waiting on (a reply, a callback, a delivery). A near-duplicate of an open task, or "
        "something closed in the last two weeks, is refused — if it is genuinely a new "
        "instance, say so with new_instance."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "what": {"type": "string",
                     "description": "The commitment, in words that still make sense in a month. "
                                    "'Pay Chase credit card bill', not 'the bill'."},
            "kind": {"type": "string", "enum": list(KINDS)},
            "done_words": {"type": "array", "items": {"type": "string"},
                           "description": "habit/interval: words that report it done when the "
                                          "user mentions it unprompted, without saying 'done' "
                                          "— a meal-logging habit: breakfast, lunch, dinner, "
                                          "snack, ate. Their unprompted report then counts, so "
                                          "they are not asked for it."},
            "due": {"type": "string",
                    "description": "deadline: YYYY-MM-DD. Leave empty if no date was given; put "
                                   "a vague phrase ('next week') in note."},
            "eligible_from": {"type": "string",
                              "description": "Optional YYYY-MM-DD before which it cannot be "
                                             "done yet; it stays out of view until then."},
            "moot_after": {"type": "string",
                           "description": "Optional YYYY-MM-DD after which it no longer matters "
                                          "at all (an RSVP for an event on that date). Without "
                                          "it, an overdue deadline stays overdue until done or "
                                          "dismissed."},
            "every": {"type": "string", "enum": list(_EVERY),
                      "description": "habit: the period."},
            "times": {"type": "integer",
                      "description": "habit: how many times per period (default 1)."},
            "on_days": {"type": "array", "items": {"type": "string",
                                                   "enum": list(_WEEKDAYS)},
                        "description": "habit, weekly: preferred days. A missed one can be "
                                       "made up later in the week."},
            "interval_days": {"type": "integer",
                              "description": "interval: every how many days."},
            "minutes": {"type": "integer",
                        "description": "How long it takes, in minutes — what lets it be "
                                       "placed in a day. The user's figure if they gave one; "
                                       "otherwise your estimate, with minutes_source "
                                       "'estimated'."},
            "minutes_source": {"type": "string", "enum": list(_MINUTES_SOURCES),
                               "description": "stated — the user said it; estimated — your "
                                              "guess. Default estimated."},
            "last_done": {"type": "string",
                          "description": "interval: YYYY-MM-DD it was last done, if the user "
                                         "said."},
            "waiting_on": {"type": "string",
                           "description": "waiting: who the user is waiting on."},
            "expect_from": {"type": "string",
                            "description": "waiting: the email address, domain or name the "
                                           "update should come from, if known — lets an "
                                           "arriving message offer to close it."},
            "check_back": {"type": "string",
                           "description": "waiting: YYYY-MM-DD to check if nothing has come "
                                          "(default a week)."},
            "domain": {"type": "string",
                       "description": "Optional life domain — finance, logistics, health, work."},
            "medication": {"type": "string",
                           "description": "habit: when the habit is taking a medication, its "
                                          "name exactly as the user's stored medication "
                                          "profile gives it. This is what makes each dose "
                                          "count as taken; a name the profile does not hold is "
                                          "refused, and so is a second habit for a medication "
                                          "that already has one (a second daily dose is "
                                          "`times`). Set by the Synthesizer. Leave unset for "
                                          "any other habit."},
            "note": {"type": "string", "description": "Optional one line of context."},
            "source_id": {"type": "string",
                          "description": "The id of the intake-queue message it came from, when "
                                         "it came from one — the same message cannot file it "
                                         "twice."},
            "calendar_uid": {"type": "string",
                             "description": "The uid of the calendar entry for it, if you made "
                                            "one."},
            "new_instance": {"type": "boolean",
                             "description": "True only when this genuinely repeats something "
                                            "recently closed."},
        },
        "required": ["what", "kind"],
    },
}

UPDATE_TASK_SCHEMA = {
    "name": "update_task",
    "description": (
        "Record what happened to a tracked task. done — the user says it is done: quote their "
        "words as evidence, and do it the moment you hear it rather than waiting to be told "
        "twice. skipped — the user chose not to do this occurrence of a recurring task. "
        "done_with_followup — done, but with a loose end (followup); the loose end is opened "
        "as its own task. set_minutes — how long it takes (minutes, minutes_source). "
        "dismissed — stop tracking it altogether; evidence is the user's "
        "reason. reopen — a close you recorded was wrong. "
        "reschedule — a new date (new_due), keeping the history. note — replace the note. "
        "set_medication — link a habit to the medication it is for (medication: the name "
        "exactly as the user's stored medication profile gives it; an empty string unlinks); "
        "done_words may be given with it when the habit has none. A dose the user reports is "
        "recorded as done on that habit — never in the daily log; a dose past the habit's "
        "count for the period, or the same dose again within 10 minutes, is refused. "
        "For a recurring task, done and skipped apply to the current occurrence, or to "
        "on_date if the user said it was another day."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "task_id": {"type": "string",
                        "description": "The id shown under Tasks, e.g. ob_261023_a1b2c3 or "
                                       "ob_261023_a1b2c3@2026-W43."},
            "action": {"type": "string",
                       "enum": ["done", "done_with_followup", "skipped", "dismissed", "reopen",
                                "reschedule", "note", "set_minutes", "set_medication"]},
            "evidence": {"type": "string",
                         "description": "The user's words that show this. Required for done, "
                                        "done_with_followup, skipped, dismissed and reopen — "
                                        "for dismissed, the reason it is being dropped."},
            "minutes": {"type": "integer",
                        "description": "set_minutes: how long the task takes, in minutes."},
            "minutes_source": {"type": "string", "enum": list(_MINUTES_SOURCES),
                               "description": "set_minutes: stated (the user said) or "
                                              "estimated (your guess). A stated figure is not "
                                              "replaced by an estimate."},
            "followup": {"type": "string",
                         "description": "done_with_followup: what is still left to do, in a few "
                                        "words. It becomes a task of its own."},
            "new_due": {"type": "string", "description": "reschedule: the new YYYY-MM-DD."},
            "note": {"type": "string", "description": "note: the replacement text."},
            "medication": {"type": "string",
                           "description": "set_medication: the medication's name exactly as "
                                          "the user's stored medication profile gives it, or "
                                          "an empty string to unlink. A name the profile does "
                                          "not hold is refused."},
            "done_words": {"type": "array", "items": {"type": "string"},
                           "description": "set_medication: words that report a dose done when "
                                          "the user mentions it unprompted — only words the "
                                          "user uses, and only if the habit has none yet."},
            "on_date": {"type": "string",
                        "description": "Optional YYYY-MM-DD it actually happened, within the "
                                       "last week ('I went yesterday')."},
        },
        "required": ["task_id", "action"],
    },
}

LIST_TASKS_SCHEMA = {
    "name": "list_tasks",
    "description": (
        "List tracked tasks with ids and state. What matters today is already in your context "
        "under Tasks — call this only for ids not shown there, a longer view the user asks for "
        "(horizon), or closed history."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "include_closed": {"type": "boolean",
                               "description": "Include closed tasks and their evidence."},
            "horizon": {"type": "string", "enum": ["today", "week", "month"],
                        "description": "Only what falls in this span — when the user asks "
                                       "what's on today, this week or this month. Omit for "
                                       "everything open."},
        },
        "required": [],
    },
}


# --- The schemas a model sees ---------------------------------------------------------------
# The three constants above are what every agent granted these tools has seen since the ledger
# landed, and with `ledger_fields` off they are returned UNCHANGED — tests pin that byte for byte
# (review R1-1). With it on, the day planner's actions and fields are added. register_tools()
# calls this on every agent call, so a flip is live on the next session.

import copy as _copy  # noqa: E402

_PLAN_FIELD_PROPS = {
    "goal_id": {"type": "string",
                "description": "The id of the goal this serves (q1, w2, d3 — the ids in the goals "
                               "you hold). What it is for sets how much it matters; empty "
                               "string unlinks it."},
    "priority": {"type": "string", "enum": list(_PRIORITIES),
                 "description": "How much this matters beyond its deadline, against the user's "
                                "goals, mission and values — an obligation like taxes is high "
                                "even when it serves no goal. Leave unset to take it from the "
                                "goal it serves."},
    "priority_source": {"type": "string", "enum": list(_FIELD_SOURCES),
                        "description": "stated — the user said so; inferred — your judgement. "
                                       "Default inferred; a stated value is never replaced by "
                                       "an inferred one."},
    "stakes": {"type": "string", "enum": list(_STAKES),
               "description": "a deadline, or a monthly habit with days of the month — ALWAYS set "
                              "it; unset is treated as back-burner. Judge it by what missing it "
                              "would cost this user: financial (a penalty, a fee), legal, health, "
                              "social (someone let down), psychological (it would weigh on them). "
                              "vital — a real cost: taxes, bills, legal dates and the like are "
                              "vital whether or not they serve a goal. missable — little lost if "
                              "it slips. What they care about counts: for a keen gardener, "
                              "repotting the plants can be vital; for most people it is "
                              "missable."},
    "stakes_source": {"type": "string", "enum": list(_FIELD_SOURCES),
                      "description": "stated or inferred, as for priority_source."},
    "stakes_why": {"type": "string",
                   "description": "With stakes: what missing it would cost, in a few words "
                                  "(\"£100 penalty\", \"lets Sam down\", \"nothing much\")."},
    "zone": {"type": "string",
             "description": "A named place where this gets done (\"gym\"), from the zones on "
                            "file — lets arriving there count as a sign it happened. Empty "
                            "string clears it."},
    "activity": {"type": "string",
                 "description": "What kind of thing it is — focus, creative, admin, busy, errands, "
                                "household, personal, health, exercise, family, social, "
                                "entertainment, rest. Decides when in the day it can go (admin and "
                                "focused work stay out of family time). Empty string clears it."},
    "flexible": {"type": "boolean",
                 "description": "A one-off that can happen any day up to `due` (\"sometime next "
                                "week\" — due is the last day of that span; `eligible_from` its "
                                "first, if it cannot start yet). Planned on a day with room; a "
                                "must-do only on its last day."},
    "after": {"type": "string",
              "description": "HH:MM — the earliest time of day it can start (\"after 4 pm\" is "
                             "16:00)."},
    "enjoyed": {"type": "boolean",
                "description": "true when the user enjoys doing it (a walk, a call with a friend, "
                               "a hobby) — it is then placed soon after something effortful. "
                               "With update_task, set by set_activity."},
}

# The cost record (ranking Part B, plan § 4.1 as amended by § 10 R1): what a delay would cost and
# how that cost grows. Beside `stakes`, never instead of it — nothing here writes `stakes`, so
# `ranking_v2` off reads Part A's stakes exactly. These descriptions ARE the judging rule (One Home
# Per Rule Class): config/agents/task_judge.md defers to them, and tools/task_judge.py hands them
# to the judge verbatim. Exposed in the schemas only while `cost_record` is on.
_COST_GRADES = ("minor", "major", "severe")
_COST_DIMENSIONS = ("financial", "legal", "health", "social", "psychological")
_BEARS = ("self", "close", "own_org", "others", "org")
_SHAPES = ("step", "accruing", "neglect", "cliff")

_COST_FIELD_PROPS = {
    "costs": {"type": "object",
              "properties": {d: {"type": "string", "enum": list(_COST_GRADES)}
                             for d in _COST_DIMENSIONS},
              "description": "What letting it slip would cost this user — only the kinds that "
                             "apply, each graded: financial (a fee, a penalty, money lost), legal, "
                             "health, social (someone let down, a relationship worn), psychological "
                             "(it would weigh on them, or they would regret it). minor — a "
                             "nuisance; major — a real loss they would feel for a while; severe — "
                             "lasting harm, hard to undo. Judge against their goals and "
                             "circumstances; a passion it serves is named in `passion` and raises "
                             "the grade by itself — do not raise it for that as well. Taxes, "
                             "bills, legal and official dates and health appointments "
                             "carry a real cost whatever their goals say. A harm that rebounds on "
                             "the user (their job, their reputation) is graded as theirs."},
    "bears": {"type": "string", "enum": list(_BEARS),
              "description": "Who mainly bears that cost: self; close — their partner, children, "
                             "parents, closest friends (weighs as their own); own_org — a business "
                             "they own or run; others — anyone else; org — an employer or "
                             "organisation they do not own."},
    "shape": {"type": "string", "enum": list(_SHAPES),
              "description": "How the cost of putting it off grows: step — lands once, at the date "
                             "(an RSVP, a late fee); accruing — keeps growing after the date "
                             "(interest, a backlog); cliff — after the date it cannot be done at "
                             "all (a closing fund, a plant that dies); neglect — grows the longer "
                             "it goes undone, for upkeep and keeping in touch (an interval task). "
                             "When unsure: step for a dated task, neglect for an interval."},
    "real_due": {"type": "string",
                 "description": "YYYY-MM-DD — the real date behind the stated one, when the two "
                                "differ and it is known (the fund's close, not the day they said "
                                "they would get to it)."},
    "costs_source": {"type": "string", "enum": ["stated", "inferred"],
                     "description": "stated — the user said so; inferred — your judgement. A "
                                    "stated record is never replaced by an inferred one."},
    "passion": {"type": "string",
                "description": "Which of the user's passions this serves, by its name in "
                               "`passions` (\"gardening\") — only one they have; empty when "
                               "none."},
    "costs_why": {"type": "string",
                  "description": "With costs: what the delay would cost, in a few words (\"£100 "
                                 "penalty\", \"Dad goes weeks without a call\")."},
}

# Replaces the shipped `on_days` while the planner's fields are on: a monthly habit can then take
# days of the month (plan § 18, R2-10).
_ON_DAYS_PROP = {
    "type": "array", "items": {"type": "string"},
    "description": "habit, weekly: preferred weekdays (mon … sun) — a missed one can be made up "
                   "later in the week. habit, monthly: the days of the month it belongs in — "
                   "[\"10-15\"] for a bill the user deals with from the 10th and must pay by the "
                   "15th. Planned from the first, due by the last, overdue after it.",
}


def task_schemas() -> tuple[dict, dict, dict]:
    """(open_task, update_task, list_tasks) schemas as models should see them right now."""
    try:
        from tools.day_plan_config import flag
        exposed = flag("ledger_fields")
    except Exception:  # noqa: BLE001
        exposed = False
    if not exposed:
        return OPEN_TASK_SCHEMA, UPDATE_TASK_SCHEMA, LIST_TASKS_SCHEMA
    open_s = _copy.deepcopy(OPEN_TASK_SCHEMA)
    open_s["input_schema"]["properties"].update(_copy.deepcopy(_PLAN_FIELD_PROPS))
    open_s["input_schema"]["properties"]["on_days"] = _copy.deepcopy(_ON_DAYS_PROP)
    # Corrections change the task they are about (Mike, 2026-10-27). In the tool's own words, so
    # every agent that writes tasks reads it — on 10-27 Logistics did the writing, and twice
    # opened a second task beside the one the user was correcting; the rule had lived only in the
    # Synthesizer's day-plan conduct, which Logistics never sees.
    open_s["description"] += (
        " When the user is correcting or adding detail to a task that is already open — a new "
        "time, kind, length, or 'I'll do it later' — that is update_task on the existing one, "
        "never a second task beside it; their Tasks section shows the ids.")
    # A span ("sometime next week") is recordable now: due is its last day, with flexible.
    open_s["input_schema"]["properties"]["due"]["description"] = (
        "deadline: YYYY-MM-DD. For a span (\"sometime next week\", \"by Friday\") the last day "
        "of it, with flexible. Leave empty only when no day or span was given at all — an "
        "undated task is never planned into a day.")
    upd = _copy.deepcopy(UPDATE_TASK_SCHEMA)
    upd["description"] += (
        " link_goal / set_priority / set_stakes / set_zone / set_activity — record what it serves, "
        "how much it matters, whether its deadline is vital or missable, where it gets done, what "
        "kind of thing it is (goal_id, priority, stakes, zone, activity; the first three with "
        "their _source). day_starts — when the user's day "
        "really ends (task_id \"settings\", the time in note, e.g. \"02:00\"); only on their "
        "own word. set_days — a weekly or monthly habit's days (on_days), only on their own "
        "word, quoted in evidence. set_window — a one-off that can happen any day up to new_due "
        "(\"sometime next week\"), optionally not before `after` (HH:MM). defer — the user does "
        "not want to see it until a later day (\"don't show me this until Monday\"): new_due is "
        "the day it comes back, evidence their words; until then it is out of Tasks, the Today "
        "list and the day plan, and its date does not move. reschedule is for when the date "
        "itself moves (\"it's now due Monday\"). Not for a habit, and never past a deadline's "
        "own date — reschedule that first.")
    upd["description"] += (
        " A correction to an open task — its kind (set_activity), length (set_minutes), date "
        "(reschedule) or span (set_window) — is made here, on that task, never by opening a new "
        "one. A monthly bill's or transfer's days ('from the 10th, paid by the 15th') are "
        "set_days with on_days [\"10-15\"] on the habit itself.")
    upd["input_schema"]["properties"]["action"]["enum"] = (
        list(upd["input_schema"]["properties"]["action"]["enum"]) + list(_PLAN_ACTIONS))
    upd["input_schema"]["properties"].update(_copy.deepcopy(_PLAN_FIELD_PROPS))
    upd["input_schema"]["properties"].pop("flexible", None)   # set_window implies it
    upd["input_schema"]["properties"]["on_days"] = _copy.deepcopy(_ON_DAYS_PROP)
    upd["input_schema"]["properties"]["new_due"]["description"] = (
        "reschedule: the new YYYY-MM-DD. set_window: the last day it can happen. defer: the day "
        "it comes back (after today, no later than its due date).")
    if _cost_record():
        open_s["input_schema"]["properties"].update(_copy.deepcopy(_COST_FIELD_PROPS))
        upd["input_schema"]["properties"].update(_copy.deepcopy(_COST_FIELD_PROPS))
        upd["description"] += (
            " set_costs — record or correct what a delay would cost (costs, bears, shape, "
            "real_due, costs_why, costs_source); the fields given replace those on file.")
        upd["input_schema"]["properties"]["action"]["enum"] = (
            list(upd["input_schema"]["properties"]["action"]["enum"]) + ["set_costs"])
    if _back_burner():
        upd["description"] += (
            " keep — the user wants the task kept as it is (their answer to whether it can go "
            "on the back burner); evidence their words.")
        upd["input_schema"]["properties"]["action"]["enum"] = (
            list(upd["input_schema"]["properties"]["action"]["enum"]) + ["keep"])
    return open_s, upd, LIST_TASKS_SCHEMA


if __name__ == "__main__":  # manual: python3 -m tools.obligations <persona> [--report [days]]
    import sys
    from core.persona import persona_scope

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    who = args[0] if args else sys.exit("name the persona: python -m tools.obligations <persona> …")
    with persona_scope(who):
        if "--report" in sys.argv:
            days = int(args[1]) if len(args) > 1 and args[1].isdigit() else 30
            print(report(who, days))
        else:
            print(list_tasks(include_closed=True))
            print()
            print(context_block() or "(no context block)")
