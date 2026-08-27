"""
tools/logger.py — first working tool.

Provides write_log() and read_log() for storing and retrieving daily check-in records.
All logs are stored locally in data/logs/YYYY-MM-DD.json — Sensitive-tier from day one.
"""

import json
import os
import re
import threading
from datetime import date, datetime
from pathlib import Path

from core.persona import PersonaError, persona_data_dir, persona_scope, resolve_persona
from core.background import run_background


# [DB-0815-09] A model asked to fill a slot in a structured output template answers the slot
# rather than deleting it, so "no correction happened" arrives as the word "None" instead of an
# absent line. These are the forms actually observed in 93 of 174 live USER_CORRECTION events on
# 2026-08-15 — not a speculative list. Bracketed variants are included because the Coordinator
# wraps its non-answers: "[N/A - the user's message is a shift in intent, not a correction]".
#
# Deliberately NOT a substring match. "None of the medication was taken" is a real correction and
# must survive; this compares the whole stripped value, and the long-bracketed form is caught by
# the prefix rule below rather than by widening the set.
_NULL_ISH = {
    "none", "n/a", "na", "null", "nil", "nothing", "no correction", "not applicable",
    "no corrections", "-", "--", "—", "[none]", "[n/a]", "()", "[]",
}


# [DB-0827-07] The same template failure one slot along. Where [DB-0815-09] saw the slot
# answered with the word "None", 33 live events since 2026-08-18 have a detail that is
# exactly `CLARIFICATION_NEEDED:` — the model filled the USER_CORRECTION slot with the
# label of the template line next to it and no content at all. A bare label is a fragment
# of the output format, never something that happened, so it is a non-answer in the same
# sense as "N/A".
#
# The match is deliberately narrow: ALL-CAPS word (underscores, hyphens or single spaces
# between words) followed by a colon, and it is only null-ish if what FOLLOWS the colon is
# empty or itself null-ish. "CLARIFICATION_NEEDED: which Bill?" is real signal and survives.
_TEMPLATE_LABEL_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:[ _-][A-Z0-9]+)*\s*:(.*)$", re.DOTALL)


def _null_value(text: str) -> bool:
    """The scalar half of is_null_ish(): is this value itself a non-answer?"""
    stripped = (text or "").strip().strip("[](){}\"'").strip().rstrip(".!?").strip().lower()
    if not stripped:
        return True
    if stripped in _NULL_ISH:
        return True
    # "[N/A - the user's message is a shift in intent, not a correction of a past error.]"
    return any(stripped.startswith(f"{tag} -") or stripped.startswith(f"{tag} —")
               for tag in ("n/a", "na", "none"))


def is_null_ish(text: str) -> bool:
    """
    True when `text` is a model's way of saying "this field does not apply".

    Whole-value comparison after stripping surrounding brackets, quotes and terminal
    punctuation — never a substring test, so a genuine correction that merely begins with
    the word "none" is unaffected. The one prefix rule covers the observed bracketed
    explanation form ("[N/A - ...]"), which is a non-answer of arbitrary length.

    Also true for a bare template label with nothing behind it — `CLARIFICATION_NEEDED:` —
    which is the same template-filling reflex leaving a piece of the output format in the
    payload. A label WITH content after the colon is kept, label and all: the label is
    part of what the model meant, and stripping it would rewrite the record.
    """
    if _null_value(text):
        return True
    match = _TEMPLATE_LABEL_RE.match((text or "").strip().strip("[](){}\"'").strip())
    return bool(match) and _null_value(match.group(1))

_WRITE_LOG_LOCK = threading.Lock()
_WRITE_QUALITY_EVENT_LOCK = threading.Lock()

_ROOT = Path(__file__).parent.parent


def _logs_dir() -> Path:
    return persona_data_dir() / "logs"


def _deep_merge(base: dict, incoming: dict) -> dict:
    """
    Merge `incoming` into `base`, recursing into nested dicts.

    This used to be `base.update(incoming)`, which is correct for the flat top-level keys
    the log accumulated in practice and silently destructive for the nested blocks the
    specialists actually declare. Physical Health writing `{"health": {"sleep_hours": 7.5,
    "sleep_quality": "good"}}` in the morning and `{"health": {"energy": "low"}}` in the
    evening ended the day with `health` holding energy alone — the morning's two fields
    replaced wholesale, no error, no trace.

    That is very likely part of why nothing ever adopted the nested shape: across 70 log
    files the `health` and `wellbeing` blocks appear in 4, while flat `mood`/`energy`/`focus`
    appear in ~60. A flat scalar survives `update()`; a nested sibling does not. So this
    function is the guard that has to exist *before* anything encourages nested writes —
    doing it the other way round would have converted a schema mismatch into data loss.
    (`[DB-0809-20]`.)

    Lists are replaced rather than concatenated. `tasks_completed` and `medications_logged`
    are restatements of the day's state, not append-only feeds — merging them would
    duplicate every entry on the second write of the day.
    """
    out = dict(base)
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


# [DB-0822-06] Per-field write times, kept in one flat map at the top of the log rather than
# by wrapping each value as {"value": ..., "at": ...}.
#
# The wrapping shape was rejected: it changes what every existing reader sees — read_log,
# get_log_window, tools/analytics.py, the memory index — and it invalidates every log file
# already on the VM, all at once, for a benefit that is purely additive. A sidecar key is
# ignored by anything that does not know about it, so a file written before this shipped
# reads exactly as it did, and no migration runs anywhere.
#
# The map is DERIVED, never model-supplied. A specialist that can write its own timestamp can
# claim a stale field is fresh, which is the failure this exists to catch, so an incoming
# `_written_at` is discarded rather than merged (same discipline as _thread_tier in
# tools/context_tracker.py).
_WRITTEN_AT_KEY = "_written_at"


def _leaf_paths(node: dict, prefix: str = "") -> list[str]:
    """
    Dotted path of every leaf value in `node` — "notes", "health.energy".

    Nested dicts recurse so siblings are stamped independently: the whole reason
    _deep_merge exists is that a morning write of `health.sleep_hours` and an evening write
    of `health.energy` are two separate assertions, and a single stamp on `health` would
    re-date the morning's field every evening. Lists are leaves — _deep_merge replaces them
    wholesale, so the list is one assertion.

    `date` and the map itself are skipped at the top level: neither is something a person
    told us.
    """
    paths: list[str] = []
    for key, value in node.items():
        if not prefix and key in (_WRITTEN_AT_KEY, "date"):
            continue
        path = f"{prefix}{key}"
        if isinstance(value, dict) and value:
            paths.extend(_leaf_paths(value, f"{path}."))
        else:
            paths.append(path)
    return paths


def write_log(content: dict | None = None, log_date: str = "") -> str:
    """
    Write a daily log entry to data/logs/YYYY-MM-DD.json.

    Args:
        log_date: Date string in YYYY-MM-DD format. Defaults to today if empty.
        content: Dictionary of log fields (mood, energy, focus, tasks, etc.)

    Returns:
        Confirmation string with the path written.
    """
    if content is None:
        content = {}
    elif isinstance(content, str):
        content = {"notes": content}
    elif not isinstance(content, dict):
        content = {}
    else:
        content = dict(content)

    # A write time the model chose is not evidence of when anything was written. Discarded
    # before the merge, so a forged map can never displace the real one — see _WRITTEN_AT_KEY.
    content.pop(_WRITTEN_AT_KEY, None)

    if not log_date:
        log_date = date.today().isoformat()
    else:
        # [DB-0809-12]: a specialist computing "today" itself, rather than reading the
        # clock line every directive carries, has invented a wrong year before — a
        # credit-card reminder landed in a log dated 2025-05-22, fourteen months in the
        # past, on 2026-08-02. Nine such files accumulated silently before anyone
        # noticed. No legitimate write needs a date this far from the real clock: a
        # session crossing midnight or backfilling a missed day explains ±1, nothing
        # explains ±1 year. Refused rather than warned — unlike a near-duplicate
        # obligation or an over-cap write, there is no reading of a year-old log_date
        # that this would wrongly block.
        try:
            parsed = date.fromisoformat(log_date)
        except ValueError:
            return (f"Error: log_date {log_date!r} is not a valid YYYY-MM-DD date. "
                    f"Omit it to default to today.")
        drift_days = abs((parsed - date.today()).days)
        if drift_days > 7:
            return (f"Error: log_date {log_date!r} is {drift_days} days from today "
                    f"({date.today().isoformat()}) — refused as a likely hallucinated "
                    f"date rather than a real backdate. Use the date from your clock "
                    f"line, or omit log_date to default to today.")

    logs_dir = _logs_dir()
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"{log_date}.json"

    with _WRITE_LOG_LOCK:
        existing = {}
        if log_path.exists():
            with open(log_path) as f:
                existing = json.load(f)
        # Stamps carried from the file, then overwritten only for the paths THIS write
        # touches. An untouched field keeps the time it was actually asserted, which is the
        # whole point: on 2026-08-27 the 07:14 run resolved the Teams link and the 10:00 run
        # still called it missing, because a merged day-file has one date and no way to say
        # that one field in it was three hours old and another three minutes.
        stamps = dict(existing.get(_WRITTEN_AT_KEY) or {})
        now_iso = datetime.now().isoformat(timespec="seconds")
        for path in _leaf_paths(content):
            stamps[path] = now_iso

        existing = _deep_merge(existing, content)
        existing["date"] = log_date
        if stamps:
            existing[_WRITTEN_AT_KEY] = stamps
        with open(log_path, "w") as f:
            json.dump(existing, f, indent=2)
        os.chmod(log_path, 0o600)

    # Embedding costs ~150-200ms on the VM and nothing reads its result, but it
    # ran inline here — inside tool dispatch, on the user's critical path.
    # Persona is resolved on THIS thread (so a failure still surfaces, and so
    # fail-closed behaviour is preserved) and re-bound inside the worker, which
    # has no thread-local identity of its own.
    _persona = resolve_persona()
    # The stamp map is excluded from what gets embedded: it is bookkeeping, and a block of
    # ISO timestamps in the indexed text is noise a semantic search has to see past.
    _payload = json.dumps({k: v for k, v in existing.items() if k != _WRITTEN_AT_KEY})

    def _index() -> None:
        from core.memory import index_entry
        with persona_scope(_persona):
            index_entry(text=_payload, source="log", entry_date=log_date)

    run_background(_index, f"index log {log_date}")

    return f"Log written to {log_path}"


def read_log(log_date: str = "") -> dict:
    """
    Read a daily log entry from data/logs/YYYY-MM-DD.json.

    Args:
        log_date: Date string in YYYY-MM-DD format. Defaults to today if empty.

    Returns:
        Log contents as a dictionary, or empty dict if no log exists.
    """
    if not log_date:
        log_date = date.today().isoformat()

    log_path = _logs_dir() / f"{log_date}.json"

    if not log_path.exists():
        return {}

    with open(log_path) as f:
        return json.load(f)


def write_quality_event(
    event_type: str,
    source_agent: str = "",
    detail: str = "",
    session_id: str = "",
) -> str:
    """
    Append a quality event to data/logs/quality_events.json (JSON Lines format).

    Args:
        event_type: ROUTING_MISS | USER_CORRECTION (or any future type)
        source_agent: Which agent emitted or missed the signal
        detail: Brief description of what was missed or corrected. Required in
            practice despite the empty default kept for signature compatibility —
            see the ValueError below.
        session_id: Any string identifying the current session (date/time or short ID)

    Raises:
        ValueError: if `detail` is blank **or null-ish**. A quality event with no
            detail cannot be attributed to anything downstream —
            `scripts/sync_dev_backlog.py` reads these into a human-facing backlog,
            and an empty entry there is worse than a missing one. A sample of
            USER_CORRECTION events found ~70% with `detail: None` before this guard
            existed (2026-08-10), all written by a caller that skipped the parameter
            the schema never required.

            **Widened 2026-08-15 from "blank" to "blank or null-ish", because the
            2026-08-10 guard did not hold.** A live count that day: 93 of 174
            USER_CORRECTION events still carried no information — but as the literal
            strings "None", "None.", "N/A", "[N/A - the user's message is a shift in
            intent, not a correction of a past error.]". Those are not blank, so they
            passed the guard, reached the backlog, and collapsed into a single
            `None. ×90` entry that became the loudest signature in Mike's
            session-start line, crowding out the real ones.

            **The cause is a template, not a careless caller.**
            `config/agents/coordinator.md:88` carries `USER_CORRECTION:` as a slot in
            a fixed output block, annotated "omit if not applicable" — and a model
            filling a structured template answers the slot rather than deleting it.
            That instruction is already correct and is already ignored, which is
            precisely why the control belongs here in Python and not in the agent
            file. Same class as the invented `eva@example.com` that `tools/crm.py`
            now refuses: **a field that looks required gets filled with something
            plausible rather than left out.**

    Returns:
        Confirmation string.
    """
    detail = (detail or "").strip()
    if not detail:
        raise ValueError(
            f"write_quality_event({event_type!r}): detail is required and cannot be "
            "blank — pass a real description of what happened, not the empty default."
        )
    if is_null_ish(detail):
        raise ValueError(
            f"write_quality_event({event_type!r}): detail {detail!r} carries no "
            "information — this is the 'no correction happened' case, so do not "
            "write an event at all. See is_null_ish()."
        )

    logs_dir = _logs_dir()
    logs_dir.mkdir(parents=True, exist_ok=True)
    events_path = logs_dir / "quality_events.json"

    event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "session_id": session_id,
        "event_type": event_type,
        "source_agent": source_agent,
        "detail": detail,
    }

    with _WRITE_QUALITY_EVENT_LOCK:
        with open(events_path, "a") as f:
            f.write(json.dumps(event) + "\n")
        os.chmod(events_path, 0o600)

    return f"Quality event logged: {event_type}"


# Tool schemas — registered with the Claude API in orchestrator.register_tools()

WRITE_LOG_SCHEMA = {
    "name": "write_log",
    "description": (
        "Save a daily log entry. Use this after a check-in to record how the day went. "
        "Merges with any existing entry for that date, including inside nested blocks, "
        "so writing twice in one day is safe.\n\n"
        "RECORD BOTH A COMPARABLE VALUE AND THE REAL WORDS. Days have to be rankable "
        "against each other or nothing can be read as a trend: 'anxious' and 'mixed' sit "
        "on no scale, while sleep hours do — which is why sleep ends up explaining "
        "everything. So put the coarse value in the field that has a fixed set, and the "
        "specific description in `notes` beside it. Never flatten the description away, "
        "and never invent a value the user did not give: if they said 'shattered', that is "
        "energy `low` plus notes 'shattered', not a number they never stated.\n\n"
        "Shape: `wellbeing` = {mood: low|neutral|positive|mixed, intensity: "
        "low|moderate|high, trajectory: rising|stable|declining|unclear, stress: "
        "low|moderate|high, notes: free text}. `health` = {sleep_hours: number, "
        "sleep_quality: good|fair|poor, energy: low|moderate|high, food_logged: bool, "
        "exercise: {type, duration_minutes, intensity_rpe}, symptoms, medical_notes}. "
        "Top level also takes `focus`, `blockers`, `wins`, `tasks_completed`, `notes`. "
        "Your own agent file's `## Data written` section is authoritative for your domain."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "log_date": {
                "type": "string",
                "description": "Date in YYYY-MM-DD format. Leave empty for today.",
            },
            "content": {
                "type": "object",
                "description": (
                    "Log fields to record, in the shape described above — domain values "
                    "inside their `wellbeing` / `health` block, using the fixed vocabulary, "
                    "with the specific wording in the `notes` beside them. Top level takes "
                    "focus, blockers, wins, tasks_completed, notes."
                ),
                "additionalProperties": True,
            },
        },
        "required": ["content"],
    },
}

READ_LOG_SCHEMA = {
    "name": "read_log",
    "description": "Read a daily log entry for a given date.",
    "input_schema": {
        "type": "object",
        "properties": {
            "log_date": {
                "type": "string",
                "description": "Date in YYYY-MM-DD format. Leave empty for today.",
            },
        },
        "required": [],
    },
}

WRITE_QUALITY_EVENT_SCHEMA = {
    "name": "write_quality_event",
    "description": (
        "Log a quality event for the self-improvement protocol. "
        "Use event_type ROUTING_MISS when the original message carried a signal no specialist surfaced. "
        "Use event_type USER_CORRECTION when the user re-states or corrects a prior turn. "
        "`detail` is required and rejected if blank — a quality event nobody can read back is worse "
        "than no event at all."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "event_type": {
                "type": "string",
                "description": "ROUTING_MISS or USER_CORRECTION",
            },
            "source_agent": {
                "type": "string",
                "description": "Which agent emitted or missed the signal (e.g. 'synthesizer', 'mental_wellbeing')",
            },
            "detail": {
                "type": "string",
                "description": (
                    "What actually happened, specifically — for a USER_CORRECTION, name what was "
                    "wrong and what the user said instead, not just 'user corrected something'. "
                    "Required — the call is rejected if this is blank."
                ),
            },
            "session_id": {
                "type": "string",
                "description": "Any string identifying this session — use the date/time or a short ID",
            },
        },
        "required": ["event_type", "detail"],
    },
}
