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
2026-08-07, 17:22: "I thought I already told you that the Rowan transfer was handled.
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
    return doc


def _save_doc(doc: dict, persona: str | None = None) -> None:
    """Atomic write (temp file + replace), 0600, then flush any history rows the change
    produced. The temp-and-replace is what keeps a crash mid-write from leaving half a file
    that the next load would refuse as unreadable."""
    rows = doc.pop("_history", None) or []
    doc.pop("_dirty", None)
    path = _store_path(persona)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
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


def _with_store(persona: str | None, fn):
    """Load, apply `fn(doc)`, save, return fn's result. An unreadable store is preserved and
    nothing is written: overwriting it would replace every task with only this call's."""
    with _LOCK:
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
        with _LOCK:
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
    with _LOCK:
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
        if t.get("status") == "open" and _same_commitment(t.get("what", ""), what):
            return t
    return None


def _open_near(tasks: list[dict], what: str) -> dict | None:
    """An open task sharing two identifying words with `what` (_tokens_match)."""
    new = _task_tokens(what)
    for t in tasks:
        if t.get("status") == "open" and _tokens_match(new, _task_tokens(t.get("what", ""))):
            return t
    return None


def _recent_close_match(tasks: list[dict], what: str, today: date) -> dict | None:
    new = _task_tokens(what)
    for t in tasks:
        if t.get("status") not in _TERMINAL or t.get("kind") not in _ONE_OFF:
            continue
        closed = _stamp_day(t.get("closed_at"))
        if not closed or (today - closed).days > _RECLOSE_WINDOW_DAYS:
            continue
        if _same_commitment(t.get("what", ""), what) or _tokens_match(new, _task_tokens(t["what"])):
            return t
    return None


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
                     text=f"{what} — due today" + (f", after {t['after']}" if t.get("after") else ""))
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
              after: str | None = None) -> str:
    """Record something the user has to do, or is waiting on, so it is tracked until done."""
    what = (what or "").strip()
    if not what:
        return "error: `what` is required — a task with no description cannot be closed later"
    kind = (kind or "deadline").strip().lower()
    if kind not in KINDS:
        return f"error: `kind` must be one of {', '.join(KINDS)}, not {kind!r}. Nothing was written."

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
    if note:
        entry["note"] = note.strip()
    if source_id:
        entry["source_id"] = str(source_id).strip()
    if calendar_uid:
        entry["calendar_uid"] = str(calendar_uid).strip()
    if not _ledger_fields():
        # Not in the schema while the flag is off; a model that guesses one changes nothing.
        goal_id = priority = stakes = zone = activity = None
    plan, err = _plan_fields(kind, goal_id=goal_id or None, priority=priority or None,
                             priority_source=priority_source, stakes=stakes or None,
                             stakes_source=stakes_source, zone=zone or None,
                             activity=activity or None,
                             windowed=bool(_month_window(entry)))
    if err:
        return err
    entry.update({k: v for k, v in plan.items() if v is not None})
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
        open_one_offs = sum(1 for t in tasks if t.get("status") == "open" and t.get("kind") in _ONE_OFF)
        if kind in _ONE_OFF and open_one_offs > _SOFT_CAP:
            msg += (f"\n\nNOTE: {open_one_offs} one-off tasks are now open, past the {_SOFT_CAP} "
                    f"this store is sized for. Written anyway. Several are probably done and "
                    f"unclosed — worth asking about the oldest rather than carrying them all.")
        return msg

    result = _with_store(None, apply)
    if result.startswith("task ") and calendar_uid is None:
        _link_calendar_if_exact(result.split()[1])
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
        doc = yaml.safe_load(path.read_text()) or {}
        for horizon in ("quarterly", "weekly", "daily"):
            for g in doc.get(horizon) or []:
                if isinstance(g, dict) and g.get("id"):
                    index[str(g["id"])] = g
    except Exception:  # noqa: BLE001
        index = {}
    _GOAL_CACHE.update(key=key, index=index)
    return index


def _goal_hash(goal: dict) -> str:
    return hashlib.sha256(json.dumps(goal, sort_keys=True, default=str).encode()).hexdigest()[:12]


def is_essential(t: dict, goals: dict[str, dict] | None = None) -> bool:
    """F10: essential = medication, OR explicitly high priority, OR serving an essential goal, OR a
    deadline whose stakes are not known to be missable (unknown stakes count as vital — a missed
    tax deadline costs more than a lost evening). Derived on every read, never stored."""
    if _MEDICATION_RE.search(f"{t.get('what', '')} {t.get('note', '')}"):
        return True
    if t.get("priority") == "high":
        return True
    gid = t.get("goal_id")
    if gid:
        g = (goals if goals is not None else _goal_index()).get(str(gid))
        if g and g.get("essential") is True:
            return True
    # A monthly habit with a window is a recurring deadline — a bill due by the 15th — so its
    # stakes count exactly as a deadline's do (review F4).
    return ((t.get("kind") == "deadline" or bool(_month_window(t)))
            and t.get("stakes") != "missable")


def _ledger_fields() -> bool:
    try:
        from tools.day_plan_config import flag
        return flag("ledger_fields")
    except Exception:  # noqa: BLE001
        return False


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
                 activity=None) -> tuple[dict, str | None]:
    """Validate the planner's fields. Returns (fields to set, error). An empty string for
    `goal_id`, `zone` or `activity` clears it."""
    out: dict = {}
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
    if kw.get(wanted) is None:
        return f"error: `{wanted}` is required for {action}. Nothing was written."
    tid = _split_id(task_id)
    only = {k: v for k, v in kw.items() if k in (wanted, f"{wanted}_source")}

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
                on_days=None, activity: str | None = None, after: str | None = None) -> str:
    """Record what happened to a tracked task — done, done with a loose end, skipped,
    dismissed, reopen, reschedule, or a new note."""
    action = (action or "").strip().lower()
    # The planner's actions exist only while `ledger_fields` is on (review R1-1; Fable diff
    # review S-8): off, they are neither offered in the schema nor named in this error, nor
    # accepted — a model cannot reach them by guessing.
    actions = ("done", "done_with_followup", "skipped", "dismissed", "reopen", "reschedule",
               "note", "set_minutes") + (_PLAN_ACTIONS if _ledger_fields() else ())
    if action not in actions:
        return f"error: `action` must be one of {', '.join(actions)}, not {action!r}"
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
                               stakes_source=stakes_source, zone=zone, activity=activity)
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
            t[field] = due_iso
            if kind == "deadline" and t.get("calendar_uid"):
                closed_holder["moved"] = (dict(t), due_iso)
            if status in _TERMINAL:
                hist.append({"event": "reopened", "at": _stamp(), "was": status})
                t["status"] = "open"
                for k in ("closed_at", "evidence"):
                    t.pop(k, None)
            return f"{tid} rescheduled to {due_iso}: {_summarise(t)}"

        if action == "reopen":
            if kind == "habit":
                pk = _period(t.get("every", "day"), when)[0]
                occ = (t.get("occurrences") or {}).get(pk) or {}
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
            hist.append({"event": "reopened", "at": _stamp(), "was": status,
                         "closed_at": t.get("closed_at"), "evidence": t.get("evidence"),
                         "reason": evidence})
            t["status"] = "open"
            for k in ("closed_at", "evidence"):
                t.pop(k, None)
            return f"{tid} reopened: {_summarise(t)} ({evidence})"

        if status in _TERMINAL:
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
            return f"{tid} dismissed — no longer tracked: {_summarise(t)}"

        if kind in _ONE_OFF:   # done
            t["status"] = "done"
            t["closed_at"] = (when.isoformat() + "T12:00:00") if on_iso else _stamp()
            t["evidence"] = evidence
            for p in t.get("proposals") or []:
                if p.get("status") == "pending":
                    p["status"] = "superseded"
            doc.setdefault("_history", []).append(_one_off_row(t, "done"))
            closed_holder["task"] = dict(t)
            return f"{tid} done: {_summarise(t)}"

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
        if action == "skipped":
            occ["skipped"] = True
            occ["skip_reason"] = evidence
            return f"{tid}@{pk} skipped — left out of adherence for this {every}"
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
    span = (horizon or "").strip().lower()
    if span:
        if span not in _HORIZON_DAYS:
            return f"error: `horizon` must be one of {', '.join(_HORIZON_DAYS)}, not {horizon!r}"
        open_items = [t for t in open_items if _within_horizon(t, today, _HORIZON_DAYS[span])]
    lines = [f"{len(open_items)} open:"] if open_items else ["nothing open"]
    for t in sorted(open_items, key=lambda t: _view(t, today)["sort"]):
        v = _view(t, today)
        lines.append(f"  {v['occ']}  [{t['kind']}] {t['what']} — {_state_line(t, today)}")
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
        if status == "done":
            ev = str(t.get("evidence") or "").strip().replace("\n", " ")
            tail = f"done {_when(closed, today)}" + (f" (\"{ev[:70]}\")" if ev else "")
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


def context_block(persona: str | None = None, as_of: date | None = None) -> str:
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

    views = [(t, _view(t, today, lead)) for t in tasks]
    now = sorted(((t, v) for t, v in views if v["actionable"]),
                 key=lambda tv: (tv[1]["sort"], _due_sort_key(tv[0])))
    hidden = 0
    shown: list[str] = []
    for t, v in now:
        raised = _raised_today(t, v["occ"], today)
        if raised and hide_raised:
            hidden += 1
            continue
        line = f"- `{v['occ']}` {v['text']}"
        if raised:
            line += f" (already raised today, {raised})"
        shown.append(line)
    extra = max(0, len(shown) - _CONTEXT_MAX)
    shown = shown[:_CONTEXT_MAX]

    recent = _recently_closed(tasks, today)
    pending = [t for t in tasks if t.get("status") == "open"
               and any(p.get("status") == "pending" for p in t.get("proposals") or [])]
    later = {"deadlines further out": 0, "waiting on others": 0, "not yet eligible": 0,
             "recurring, not due today": 0, "past their date, unconfirmed": 0}
    for t, v in views:
        if t.get("status") != "open" or v["actionable"]:
            continue
        if v["state"] == "dormant":
            later["not yet eligible"] += 1
        elif v["state"] == "lapsed":
            later["past their date, unconfirmed"] += 1
        elif t["kind"] == "waiting":
            later["waiting on others"] += 1
        elif t["kind"] == "deadline" and v["state"] == "later":
            later["deadlines further out"] += 1
        elif t["kind"] in ("habit", "interval") and v["state"] in ("later",):
            later["recurring, not due today"] += 1
    singular = {"deadlines further out": "deadline further out"}
    later_text = ", ".join(f"{n} {singular.get(label, label) if n == 1 else label}"
                           for label, n in later.items() if n)

    if not (shown or hidden or recent or pending or later_text):
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
    return "\n".join(lines)


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


def _gate_tokens(text: str, stop: frozenset) -> frozenset:
    return frozenset(_task_tokens(text) - stop)


def _named_by(t: dict, text: str, prev: str, others: list[dict], stop: frozenset,
              today: date) -> tuple[bool, str]:
    """(named, why-not). Named: the task's id or whole wording appears; or a non-negated clause
    shares an identifying token with it AND no other open task is named as well or better by
    that clause; or the message is a short affirmative and the previous reply raised it."""
    low = (text or "").lower()
    if t["id"] in low or (t.get("what") or "").strip().lower() in low:
        return True, ""
    ttoks = _gate_tokens(t.get("what", ""), stop)
    tie = False
    for clause in _CLAUSE_SPLIT_RE.split(low):
        clause = (clause or "").strip()
        if not clause or _NEGATION_RE.search(clause):
            continue
        ctoks = _gate_tokens(clause, stop)
        shared = ctoks & ttoks
        if not shared:
            continue
        rivals = [o for o in others if ctoks & _gate_tokens(o.get("what", ""), stop)]
        if any(len(ctoks & _gate_tokens(o.get("what", ""), stop)) > len(shared) for o in rivals):
            continue                       # the clause names something else better
        if any(ctoks & _gate_tokens(o.get("what", ""), stop) == shared for o in rivals):
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
    if getattr(_USER_ACT, "on", False):
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
    ok, why = _named_by(t, text, turn.get("prev_assistant") or "", others, stop, today)
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
    return (f"error: not recorded — {why}. Ask the user which they mean"
            + (f" (open: {names})" if names else "")
            + ", then record the one they confirm. Nothing was changed.")


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
        if not set(_WORD_RE.findall(clause)) & _DONE_MARKERS:
            continue
        ctoks = _task_tokens(clause)
        for t in tasks:
            if any(t is h for h, _ in hits):
                continue
            if _tokens_match(ctoks, _task_tokens(t["what"]), single_ok=True):
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
        with _LOCK:
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
_PROPOSAL_SOURCES = ("correspondence", "location")
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
        if source == "correspondence" and t.get("kind") not in _ONE_OFF:
            return
        if source == "location" and (t.get("kind") == "waiting" or not key):
            return
        props = t.setdefault("proposals", [])
        if source == "correspondence":
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


def match_envelope(envelope_id: str, thread_id: str = "", sender_address: str = "",
                   sender_display: str = "", subject: str = "", received: str = "",
                   category: str = "", persona: str | None = None) -> int:
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
        if t.get("status") != "open" or t.get("kind") not in _ONE_OFF:
            continue
        if envelope_id == t.get("source_id"):
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
                 reason: str | None = None, followup: str | None = None) -> str:
    """A tap in the app's Today panel. The evidence is the tap itself — the user's own act —
    plus the reason, when the app sent one. An app from before reasons existed sends none and
    still works: "marked in the app" alone is the record, as it was."""
    action = (action or "").strip().lower()
    if action not in ("done", "skipped", "dismissed", "done_with_followup"):
        return f"error: unsupported action {action!r}"
    why = (reason or "").strip()
    evidence = "marked in the app" + (f": {why}" if why else "")
    with _user_act():
        return update_task(task_id, action, evidence=evidence, followup=followup)


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
    for t in _load(persona):
        t = _norm(t)
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
                                else ["done", "done_with_followup", "dismissed"])})
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
            continue
        dates = [str(c.get("on") or c.get("at") or "")[:10]
                 for c in (t.get("completions") or []) + (t.get("recent_completions") or [])]
        for occ in (t.get("occurrences") or {}).values():
            dates += [d.isoformat() for d in _completion_dates(occ)]
        for d in sorted(set(x for x in dates if x)):
            out.append({"what": t["what"], "status": "closed", "closed_at": f"{d}T12:00:00"})
    return out


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
            phrase = ("no longer relevant" if status == "moot"
                      else f"{status} {closed.isoformat()}")
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
                                "reschedule", "note", "set_minutes"]},
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
                 "description": "How much this matters beyond its deadline. Leave unset to take "
                                "it from the goal it serves."},
    "priority_source": {"type": "string", "enum": list(_FIELD_SOURCES),
                        "description": "stated — the user said so; inferred — your judgement. "
                                       "Default inferred; a stated value is never replaced by "
                                       "an inferred one."},
    "stakes": {"type": "string", "enum": list(_STAKES),
               "description": "a deadline, or a monthly habit with days of the month: vital — "
                              "missing it has real consequences (taxes, a bill, a legal date); "
                              "missable — it can slip in favour of the user's day. Unset counts "
                              "as vital."},
    "stakes_source": {"type": "string", "enum": list(_FIELD_SOURCES),
                      "description": "stated or inferred, as for priority_source."},
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
    return open_s, upd, LIST_TASKS_SCHEMA


if __name__ == "__main__":  # manual: python3 -m tools.obligations <persona> [--report [days]]
    import sys
    from core.persona import persona_scope

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    who = args[0] if args else "mike"
    with persona_scope(who):
        if "--report" in sys.argv:
            days = int(args[1]) if len(args) > 1 and args[1].isdigit() else 30
            print(report(who, days))
        else:
            print(list_tasks(include_closed=True))
            print()
            print(context_block() or "(no context block)")
