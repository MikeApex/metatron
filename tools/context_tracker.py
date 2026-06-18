"""
tools/context_tracker.py — Diarist session context tracker.

Maintains a compact mid-term memory file the Diarist writes at session close
and reads at session start. Bridges short-term (recent logs in system prompt)
and long-term (FAISS) memory.

Stores: open threads, patterns noticed, follow-ups, last session date.
Not a summary — a list of threads to pick up next session.

Sensitive-tier, local-only, 600 permissions. Persona-scoped.
"""

import json
import os
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).parent.parent


def _tracker_path() -> Path:
    persona = os.environ.get("AI_TEST_PERSONA")
    if persona:
        return _ROOT / "data" / "personas" / persona / "context.json"
    return _ROOT / "data" / "context.json"


def read_context_tracker() -> dict:
    """
    Read the session context — open threads, recent patterns, follow-ups,
    held items, and the date of the last session.

    Returns:
        Dict with keys: last_session, open_threads, patterns, follow_ups, held_items.
        Returns empty structure if no tracker file exists yet.
    """
    path = _tracker_path()
    if not path.exists():
        return {
            "last_session": None,
            "open_threads": [],
            "patterns": [],
            "follow_ups": [],
            "held_items": [],
        }
    data = json.load(open(path))
    # Backfill held_items for trackers written before this field existed.
    data.setdefault("held_items", [])
    return data


def write_context_tracker(
    open_threads: list[str],
    patterns: list[str],
    follow_ups: list[str],
    held_items: list[str] | None = None,
) -> str:
    """
    Update the session context at close of each exchange.

    Replaces the current tracker with the updated state. Call after every
    meaningful exchange. Keep entries concise — one sentence each.

    Args:
        open_threads: Unresolved topics to carry forward.
                      E.g. ["bookstore P&L review scheduled for Thursday"].
        patterns:     Recurring observations worth noting.
                      E.g. ["writing stalls when sleep under 6 hours"].
        follow_ups:   Specific questions to ask next exchange or session.
                      E.g. ["ask how the Cato chapter went"].
        held_items:   Things the Synthesizer chose NOT to surface yet but
                      must not lose. Each entry should include WHAT was held
                      and WHY (timing, emotional readiness, relevance).
                      E.g. ["Held: SLEEP_POOR flag — user was already stressed,
                              surface when mood is better"].
                      Held items that age across multiple sessions without
                      surfacing should be escalated, not silently dropped.

    Returns:
        Confirmation string.
    """
    path = _tracker_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    tracker = {
        "last_session": date.today().isoformat(),
        "open_threads": open_threads,
        "patterns": patterns,
        "follow_ups": follow_ups,
        "held_items": held_items or [],
    }

    with open(path, "w") as f:
        json.dump(tracker, f, indent=2)

    os.chmod(path, 0o600)
    return f"Context tracker updated ({path})"


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

READ_CONTEXT_TRACKER_SCHEMA = {
    "name": "read_context_tracker",
    "description": (
        "Read the Diarist's session context from the last session: open threads, "
        "patterns noticed, things to follow up on, and the date of the last session. "
        "Call this at the start of every session to orient yourself before responding."
    ),
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

WRITE_CONTEXT_TRACKER_SCHEMA = {
    "name": "write_context_tracker",
    "description": (
        "Update the session context tracker at the close of a session. "
        "Record open threads (unresolved topics), patterns noticed, and specific "
        "things to follow up on next session. Keep entries brief — one sentence each. "
        "This is your notes-to-self, not a summary for the user."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "open_threads": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Things mentioned that weren't resolved or need follow-up. "
                    "E.g. 'bookstore P&L review coming Thursday', "
                    "'Cato chapter structure still unresolved'."
                ),
            },
            "patterns": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Recurring observations worth noting. "
                    "E.g. 'writing stalls when sleep under 6 hours'."
                ),
            },
            "follow_ups": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Specific questions to ask next session. "
                    "E.g. 'ask how the Cato chapter went'."
                ),
            },
            "held_items": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Things the Synthesizer chose not to surface yet but must not lose. "
                    "Each entry must state WHAT was held and WHY. "
                    "E.g. 'Held: SLEEP_POOR flag — user was already stressed, surface when mood lifts'. "
                    "Items held across multiple sessions without surfacing should be escalated."
                ),
            },
        },
        "required": ["open_threads", "patterns", "follow_ups"],
    },
}
