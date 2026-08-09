"""
tools/logger.py — first working tool.

Provides write_log() and read_log() for storing and retrieving daily check-in records.
All logs are stored locally in data/logs/YYYY-MM-DD.json — Sensitive-tier from day one.
"""

import json
import os
import threading
from datetime import date, datetime
from pathlib import Path

from core.persona import PersonaError, persona_data_dir, persona_scope, resolve_persona
from core.background import run_background

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

    if not log_date:
        log_date = date.today().isoformat()

    logs_dir = _logs_dir()
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"{log_date}.json"

    with _WRITE_LOG_LOCK:
        existing = {}
        if log_path.exists():
            with open(log_path) as f:
                existing = json.load(f)
        existing = _deep_merge(existing, content)
        existing["date"] = log_date
        with open(log_path, "w") as f:
            json.dump(existing, f, indent=2)
        os.chmod(log_path, 0o600)

    # Embedding costs ~150-200ms on the VM and nothing reads its result, but it
    # ran inline here — inside tool dispatch, on the user's critical path.
    # Persona is resolved on THIS thread (so a failure still surfaces, and so
    # fail-closed behaviour is preserved) and re-bound inside the worker, which
    # has no thread-local identity of its own.
    _persona = resolve_persona()
    _payload = json.dumps(existing)

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
        detail: Brief description of what was missed or corrected
        session_id: Any string identifying the current session (date/time or short ID)

    Returns:
        Confirmation string.
    """
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
        "Use event_type USER_CORRECTION when the user re-states or corrects a prior turn."
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
                "description": "Brief description of what was missed or corrected",
            },
            "session_id": {
                "type": "string",
                "description": "Any string identifying this session — use the date/time or a short ID",
            },
        },
        "required": ["event_type"],
    },
}
