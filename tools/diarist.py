"""
tools/diarist.py — Diarist module tools.

Provides journal and archive tools for the Diarist agent.

Journal: freeform daily entries (one file per day, multiple entries per file).
Archive: append-only categorized records (books, films, music, experiences, ideas, places, etc.)

All data is Sensitive-tier, local-only, 600 permissions enforced at write time.
Persona-scoped. Every session belongs to exactly one persona.
"""

import json
import os
from datetime import date, datetime
from pathlib import Path

from core.persona import PersonaError, persona_data_dir, persona_scope, resolve_persona
from core.background import run_background

_ROOT = Path(__file__).parent.parent


def _journal_dir() -> Path:
    return persona_data_dir() / "journal"


def _archive_dir() -> Path:
    return persona_data_dir() / "archive"


# ---------------------------------------------------------------------------
# Journal
# ---------------------------------------------------------------------------

def write_journal(text: str, entry_date: str = "", tags: list[str] | None = None) -> str:
    """
    Append a journal entry to the day's journal file.

    Args:
        entry_date: Date in YYYY-MM-DD format. Defaults to today if empty.
        text: Freeform journal text.
        tags: Optional list of tags (e.g. ["health", "reflection"]).

    Returns:
        Confirmation string.
    """
    if not entry_date:
        entry_date = date.today().isoformat()
    else:
        # Same guard, same reasoning, as write_log's log_date check
        # (tools/logger.py, [DB-0809-12]) — and this is why it is here now. On
        # 2026-09-05 the Diarist filed the day's family-day entry to 2026-03-30.
        # write_log refused two hallucinated dates in the same session and the
        # third attempt landed correctly; write_journal had no guard, so the
        # journal entry went 159 days into the past and nothing said so. A
        # backfilled day or a session crossing midnight explains a few days;
        # nothing explains months.
        try:
            parsed = date.fromisoformat(entry_date)
        except ValueError:
            return (f"Error: entry_date {entry_date!r} is not a valid YYYY-MM-DD date. "
                    f"Omit it to default to today.")
        drift_days = abs((parsed - date.today()).days)
        if drift_days > 7:
            return (f"Error: entry_date {entry_date!r} is {drift_days} days from today "
                    f"({date.today().isoformat()}) — refused as a likely hallucinated "
                    f"date rather than a real backdate. Use the date from your clock "
                    f"line, or omit entry_date to default to today.")

    journal_dir = _journal_dir()
    journal_dir.mkdir(parents=True, exist_ok=True)
    journal_path = journal_dir / f"{entry_date}.json"

    existing: dict = {"date": entry_date, "entries": []}
    if journal_path.exists():
        with open(journal_path) as f:
            existing = json.load(f)

    existing["entries"].append({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "text": text,
        "tags": tags or [],
    })

    with open(journal_path, "w") as f:
        json.dump(existing, f, indent=2)

    os.chmod(journal_path, 0o600)

    # See tools/logger.py — same reasoning. Persona resolved here, re-bound in
    # the worker thread, which carries no thread-local identity.
    _persona = resolve_persona()

    def _index() -> None:
        from core.memory import index_entry
        with persona_scope(_persona):
            index_entry(text=text, source="journal", entry_date=entry_date)

    run_background(_index, f"index journal {entry_date}")

    return f"Journal entry written to {journal_path}"


def read_journal(entry_date: str = "") -> dict:
    """
    Read journal entries for a given date.

    Args:
        entry_date: Date in YYYY-MM-DD format. Defaults to today if empty.

    Returns:
        Dict with 'date' and 'entries' list, or empty dict if no entry exists.
    """
    if not entry_date:
        entry_date = date.today().isoformat()

    journal_path = _journal_dir() / f"{entry_date}.json"
    if not journal_path.exists():
        return {}

    with open(journal_path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Archive
# ---------------------------------------------------------------------------

def write_archive(category: str, item: dict | str | None = None) -> str:
    """
    Append an item to a category archive file.

    Args:
        category: Archive category (e.g. "books", "films", "music",
                  "experiences", "ideas", "places"). Lowercase, no spaces.
        item: Dict describing the item. Common fields vary by category:
              books — title, author, status (reading/read/abandoned), notes, rating
              films — title, director, year, notes, rating
              music — title, artist, notes
              experiences — description, date, location, notes
              ideas — text, tags
              places — name, location, visited_date, notes

    Returns:
        Confirmation string.
    """
    if item is None:
        item = {}
    elif isinstance(item, str):
        item = {"title": item}

    category = category.lower().strip().replace(" ", "_")

    archive_dir = _archive_dir()
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"{category}.json"

    existing: list = []
    if archive_path.exists():
        with open(archive_path) as f:
            existing = json.load(f)

    # Dedup ([DB-0810-03] grants ruling, 2026-08-28): five specialists gained write_archive
    # in one pass, and an append-only store with six writers accumulates near-identical rows
    # — the same book filed at mention and again at completion. Identity is the entry's
    # natural key (title/name/text/description, case-insensitive). A match UPDATES the
    # existing row: new non-empty fields win, everything else is kept, nothing is deleted
    # (the archive-on-merge principle). An entry with no identity field appends as before.
    def _identity(d: dict) -> str:
        for k in ("title", "name", "text", "description"):
            v = d.get(k)
            if isinstance(v, str) and v.strip():
                return f"{k}:{v.strip().casefold()}"
        return ""

    key = _identity(item)
    if key:
        for row in existing:
            if isinstance(row, dict) and _identity(row) == key:
                for k, v in item.items():
                    if v not in (None, "", [], {}):
                        row[k] = v
                row["date_updated"] = date.today().isoformat()
                with open(archive_path, "w") as f:
                    json.dump(existing, f, indent=2)
                os.chmod(archive_path, 0o600)
                return (f"Updated the existing {key.split(':', 1)[0]}-matched entry in the "
                        f"{category} archive — fields merged, no duplicate added.")

    item["date_added"] = item.get("date_added") or date.today().isoformat()
    existing.append(item)

    with open(archive_path, "w") as f:
        json.dump(existing, f, indent=2)

    os.chmod(archive_path, 0o600)

    return f"Item added to {category} archive ({archive_path})"


def read_archive(category: str) -> list:
    """
    Read all items in a category archive.

    Args:
        category: Archive category (e.g. "books", "films"). Lowercase.

    Returns:
        List of archive items, or empty list if category doesn't exist.
    """
    category = category.lower().strip().replace(" ", "_")
    archive_path = _archive_dir() / f"{category}.json"

    if not archive_path.exists():
        return []

    with open(archive_path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

WRITE_JOURNAL_SCHEMA = {
    "name": "write_journal",
    "description": (
        "Write a freeform journal entry. Use for reflections, thoughts, observations, "
        "or anything the user wants to record conversationally. Appends to the day's journal "
        "file — multiple entries per day are fine. Different from write_log, which captures "
        "structured check-in data."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "entry_date": {
                "type": "string",
                "description": "Date in YYYY-MM-DD format. Leave empty for today.",
            },
            "text": {
                "type": "string",
                "description": "The journal entry text. Freeform.",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional tags to categorize the entry (e.g. ['health', 'work', 'reflection']).",
            },
        },
        "required": ["text"],
    },
}

READ_JOURNAL_SCHEMA = {
    "name": "read_journal",
    "description": "Read journal entries for a given date.",
    "input_schema": {
        "type": "object",
        "properties": {
            "entry_date": {
                "type": "string",
                "description": "Date in YYYY-MM-DD format. Leave empty for today.",
            },
        },
        "required": [],
    },
}

WRITE_ARCHIVE_SCHEMA = {
    "name": "write_archive",
    "description": (
        "Add an item to the life archive. Use for books read, films watched, music discovered, "
        "experiences had, ideas worth keeping, places visited. Each category is a separate list. "
        "The archive is append-only — a permanent record, not a to-do list."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": (
                    "Archive category. Use one of: books, films, music, experiences, ideas, places. "
                    "Or create a new category with a lowercase, underscore-separated name."
                ),
            },
            "item": {
                "type": "object",
                "description": (
                    "The item to archive. Fields vary by category. "
                    "books: title, author, status, notes, rating. "
                    "films: title, director, year, notes, rating. "
                    "music: title, artist, notes. "
                    "experiences: description, location, notes. "
                    "ideas: text, tags. "
                    "places: name, location, notes."
                ),
                "additionalProperties": True,
            },
        },
        "required": ["category", "item"],
    },
}

READ_ARCHIVE_SCHEMA = {
    "name": "read_archive",
    "description": "Read all items in a life archive category (books, films, experiences, etc.).",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "Archive category to read (e.g. 'books', 'films', 'ideas').",
            },
        },
        "required": ["category"],
    },
}
