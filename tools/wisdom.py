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


def find_duplicate_wisdom(category: str = "", threshold: float = 0.85) -> list[dict]:
    """
    Find potentially duplicate wisdom entries using semantic similarity.

    Embeds all entries (optionally filtered by category) and returns groups
    of entries whose cosine similarity exceeds the threshold.

    Args:
        category: If given, only check entries in this category.
        threshold: Cosine similarity above which entries are flagged (default 0.85).

    Returns:
        List of duplicate groups. Each group is a dict:
        { "keys": [key1, key2, ...], "similarity": float, "values": [val1, val2, ...] }
    """
    from sentence_transformers import SentenceTransformer
    import numpy as np

    wisdom_path = _wisdom_path()
    if not wisdom_path.exists():
        return []

    with open(wisdom_path) as f:
        entries: list = json.load(f)

    if category:
        entries = [e for e in entries if e.get("category") == category]

    if len(entries) < 2:
        return []

    model = SentenceTransformer("all-MiniLM-L6-v2")
    texts = [e.get("value", "") for e in entries]
    vecs = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)

    groups = []
    seen = set()
    for i in range(len(entries)):
        if i in seen:
            continue
        cluster_keys = [entries[i]["key"]]
        cluster_vals = [entries[i]["value"]]
        cluster_sims = []
        for j in range(i + 1, len(entries)):
            if j in seen:
                continue
            sim = float(np.dot(vecs[i], vecs[j]))
            if sim >= threshold:
                cluster_keys.append(entries[j]["key"])
                cluster_vals.append(entries[j]["value"])
                cluster_sims.append(sim)
                seen.add(j)
        if len(cluster_keys) > 1:
            seen.add(i)
            groups.append({
                "keys": cluster_keys,
                "similarity": round(min(cluster_sims) if cluster_sims else threshold, 3),
                "values": cluster_vals,
            })

    return groups


def merge_wisdom_entries(keep_key: str, source_keys: list[str], merged_value: str = "") -> str:
    """
    Archive source entries and optionally update the kept entry.

    Source entries are moved to data/personas/{persona}/archive/wisdom/ (or
    data/archive/wisdom/ for the real user) with a 'merged_into' pointer.
    They are never deleted — data storage is cheap; fidelity loss is not.

    Args:
        keep_key:     Key of the entry to keep as the canonical version.
        source_keys:  Keys of duplicate entries to archive.
        merged_value: If given, replace the keep_key entry's value with this
                      consolidated text. Leave empty to keep it unchanged.

    Returns:
        Confirmation string listing what was archived.
    """
    wisdom_path = _wisdom_path()
    if not wisdom_path.exists():
        return "No wisdom file found."

    with open(wisdom_path) as f:
        entries: list = json.load(f)

    # Resolve archive directory (parallel to wisdom/, under archive/)
    persona = os.environ.get("AI_TEST_PERSONA")
    if persona:
        archive_dir = _ROOT / "data" / "personas" / persona / "archive" / "wisdom"
    else:
        archive_dir = _ROOT / "data" / "archive" / "wisdom"
    archive_dir.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    archived = []
    remaining = []

    for entry in entries:
        if entry["key"] in source_keys:
            entry["merged_into"] = keep_key
            entry["archived"] = today
            archive_path = archive_dir / f"{entry['key']}_{today}.json"
            with open(archive_path, "w") as f:
                json.dump(entry, f, indent=2)
            os.chmod(archive_path, 0o600)
            archived.append(entry["key"])
        else:
            if entry["key"] == keep_key and merged_value:
                entry["value"] = merged_value
                entry["updated"] = today
            remaining.append(entry)

    with open(wisdom_path, "w") as f:
        json.dump(remaining, f, indent=2)
    os.chmod(wisdom_path, 0o600)

    return f"Archived {len(archived)} entries → {archive_dir}: {archived}. Kept: '{keep_key}'."


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

FIND_DUPLICATE_WISDOM_SCHEMA = {
    "name": "find_duplicate_wisdom",
    "description": (
        "Find potentially duplicate wisdom entries using semantic similarity. "
        "Run this during pattern analysis to surface near-identical entries that "
        "should be consolidated. Returns groups of entries above the similarity threshold."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": ["patterns", "seasonal", "annual", "preferences", "health", "quirks"],
                "description": "Limit search to this category. Leave empty to check all.",
            },
            "threshold": {
                "type": "number",
                "description": "Cosine similarity threshold (0–1). Default 0.85.",
            },
        },
        "required": [],
    },
}

MERGE_WISDOM_ENTRIES_SCHEMA = {
    "name": "merge_wisdom_entries",
    "description": (
        "Archive duplicate wisdom entries and optionally update the canonical entry. "
        "Source entries are moved to the wisdom archive with a 'merged_into' pointer — "
        "they are never deleted. Call after find_duplicate_wisdom identifies a group."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "keep_key": {
                "type": "string",
                "description": "Key of the entry to keep as the canonical version.",
            },
            "source_keys": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Keys of the duplicate entries to archive.",
            },
            "merged_value": {
                "type": "string",
                "description": (
                    "Optional consolidated text to replace the keep_key entry's value. "
                    "Leave empty to keep the existing value unchanged."
                ),
            },
        },
        "required": ["keep_key", "source_keys"],
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
