"""
tools/wisdom.py — Life Wisdom Depot.

Stores persistent background knowledge about the user: seasonal patterns,
personal quirks, recurring annual events, evolving preferences.

Separate from logs (episodic) and journal (narrative). Wisdom entries are
stable facts that accumulate over time and get surfaced proactively.

Sensitive-tier, local-only, 600 permissions enforced at write time.
Persona-scoped when AI_TEST_PERSONA is set (dev testing only).
"""

import json
import os
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).parent.parent

WISDOM_CATEGORIES = [
    "patterns",    # How this person works, thinks, performs
    "seasonal",    # Time-of-year notes, annual rhythms
    "annual",      # Recurring events, birthdays, anniversaries, tax season
    "preferences", # Discovered likes/dislikes, what works for them
    "health",      # Physical/mental health patterns and constraints
    "quirks",      # Idiosyncratic personal facts worth remembering
]


def _wisdom_path() -> Path:
    persona = os.environ.get("AI_TEST_PERSONA")
    if persona:
        return _ROOT / "data" / "personas" / persona / "wisdom" / "wisdom.json"
    return _ROOT / "data" / "wisdom" / "wisdom.json"


def read_wisdom(key: str = "") -> list | dict:
    """
    Read wisdom entries.

    Args:
        key: Specific wisdom key to retrieve. If empty, returns all entries.

    Returns:
        A single wisdom entry dict if key is given, or list of all entries.
        Returns empty list if no wisdom file exists.
    """
    wisdom_path = _wisdom_path()
    if not wisdom_path.exists():
        return [] if not key else {}

    with open(wisdom_path) as f:
        entries: list = json.load(f)

    if not key:
        return entries

    for entry in entries:
        if entry.get("key") == key:
            return entry
    return {}


def write_wisdom(key: str, value: str, category: str = "patterns") -> str:
    """
    Write or update a wisdom entry.

    If an entry with the given key already exists, it is updated in place.
    Otherwise a new entry is appended.

    Args:
        key: Short identifier slug (e.g. "morning_creativity", "raspberry_picking").
        value: The wisdom content — what to remember about this pattern or fact.
        category: One of: patterns, seasonal, annual, preferences, health, quirks.
                  Defaults to "patterns".

    Returns:
        Confirmation string.
    """
    if category not in WISDOM_CATEGORIES:
        category = "patterns"

    wisdom_path = _wisdom_path()
    wisdom_path.parent.mkdir(parents=True, exist_ok=True)

    entries: list = []
    if wisdom_path.exists():
        with open(wisdom_path) as f:
            entries = json.load(f)

    today = date.today().isoformat()
    existing_keys = [e["key"] for e in entries]

    if key in existing_keys:
        for entry in entries:
            if entry["key"] == key:
                entry["value"] = value
                entry["category"] = category
                entry["updated"] = today
                break
        action = "updated"
    else:
        entries.append({
            "key": key,
            "category": category,
            "value": value,
            "added": today,
        })
        action = "added"

    with open(wisdom_path, "w") as f:
        json.dump(entries, f, indent=2)

    os.chmod(wisdom_path, 0o600)

    return f"Wisdom entry '{key}' {action} ({wisdom_path})"


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

READ_WISDOM_SCHEMA = {
    "name": "read_wisdom",
    "description": (
        "Read from the Life Wisdom Depot — persistent background knowledge about the user. "
        "Includes seasonal patterns, personal quirks, recurring annual events, and evolving "
        "preferences. Call with no key to retrieve all entries; call with a specific key to "
        "retrieve one. Surface relevant wisdom at the start of sessions to ground responses "
        "in what's already known about this person."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "key": {
                "type": "string",
                "description": "Specific wisdom key to retrieve. Leave empty to get all entries.",
            },
        },
        "required": [],
    },
}

WRITE_WISDOM_SCHEMA = {
    "name": "write_wisdom",
    "description": (
        "Write or update an entry in the Life Wisdom Depot. Use when a new pattern, quirk, "
        "seasonal note, or recurring insight emerges from conversation — something worth "
        "remembering persistently, not just for today. Examples: 'more creative in mornings', "
        "'raspberry picking in late July', 'better at hard conversations after exercise'."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "key": {
                "type": "string",
                "description": (
                    "Short identifier slug for this wisdom entry. Use underscores, no spaces. "
                    "Examples: 'morning_creativity', 'winter_light_sensitivity', 'tax_season_stress'."
                ),
            },
            "value": {
                "type": "string",
                "description": "The wisdom content — what to remember about this pattern or fact.",
            },
            "category": {
                "type": "string",
                "enum": ["patterns", "seasonal", "annual", "preferences", "health", "quirks"],
                "description": (
                    "Category for this entry. "
                    "patterns: how this person works or thinks; "
                    "seasonal: time-of-year rhythms; "
                    "annual: recurring events; "
                    "preferences: likes/dislikes; "
                    "health: physical or mental health patterns; "
                    "quirks: idiosyncratic personal facts."
                ),
            },
        },
        "required": ["key", "value"],
    },
}
