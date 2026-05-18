"""
tools/logger.py — first working tool.

Provides write_log() and read_log() for storing and retrieving daily check-in records.
All logs are stored locally in data/logs/YYYY-MM-DD.json — Sensitive-tier from day one.
"""

import json
import os
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).parent.parent


def _logs_dir() -> Path:
    persona = os.environ.get("AI_TEST_PERSONA")
    if persona:
        return _ROOT / "data" / "personas" / persona / "logs"
    return _ROOT / "data" / "logs"


def write_log(log_date: str, content: dict) -> str:
    """
    Write a daily log entry to data/logs/YYYY-MM-DD.json.

    Args:
        log_date: Date string in YYYY-MM-DD format. Defaults to today if empty.
        content: Dictionary of log fields (mood, energy, focus, tasks, etc.)

    Returns:
        Confirmation string with the path written.
    """
    if not log_date:
        log_date = date.today().isoformat()

    logs_dir = _logs_dir()
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"{log_date}.json"

    # Merge with existing entry if one exists for today
    existing = {}
    if log_path.exists():
        with open(log_path) as f:
            existing = json.load(f)

    existing.update(content)
    existing["date"] = log_date

    with open(log_path, "w") as f:
        json.dump(existing, f, indent=2)

    os.chmod(log_path, 0o600)

    try:
        from core.memory import index_entry
        import json as _json
        index_entry(text=_json.dumps(existing), source="log", entry_date=log_date)
    except Exception:
        pass  # Memory indexing is best-effort; never block a write

    return f"Log written to {log_path}"


def read_log(log_date: str) -> dict:
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


# Tool schemas — registered with the Claude API in orchestrator.register_tools()

WRITE_LOG_SCHEMA = {
    "name": "write_log",
    "description": (
        "Save a daily log entry. Use this after a check-in to record mood, energy, "
        "focus, tasks completed, blockers, and any other relevant fields. "
        "Merges with any existing entry for that date."
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
                    "Log fields to record. Common keys: mood, energy, focus, "
                    "blockers, wins, tasks_completed, notes."
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
