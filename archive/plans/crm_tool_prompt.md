# CRM Tool Build — Implementation Prompt
*Use this to open a new Claude Code session for this task.*

---

You are Claude Code building a self-contained feature for a personal AI life manager.
Working directory: ~/Desktop/multi-model-mcp

Read these files before doing anything else:
- `CLAUDE.md` — architecture, conventions, tool pattern
- `config/agents/relationships.md` — the agent that will use these tools
- `tools/logger.py` — reference implementation for a tool module
- `core/orchestrator.py` — where tools are registered (see `register_tools()`)

---

## What this task is

Build `tools/crm.py` — a contact relationship manager that gives the Relationships agent a persistent, structured record of the people in the user's life. Currently the agent uses `write_archive` with category `contacts`, which is too flat for relational tracking.

This is a self-contained build: one new Python file, registration in the orchestrator, and an update to the Relationships agent tools list.

---

## Data model

Contacts live at `data/crm/contacts.json` (a single JSON array). Sensitive-tier: local only.

For persona testing: `data/personas/{persona}/crm/contacts.json`.

Each contact record:

```json
{
  "id": "uuid4-string",
  "name": "Sarah Chen",
  "relationship_type": "friend | family | colleague | romantic | acquaintance | professional | other",
  "relationship_quality": "close | warm | neutral | strained | lost_touch",
  "last_contact": "2026-05-20",
  "contact_frequency_preference": "daily | weekly | monthly | quarterly | as_needed",
  "important_dates": [
    {"label": "birthday", "date": "1988-07-14"},
    {"label": "work anniversary", "date": "2023-03-01"}
  ],
  "tags": ["college", "hiking", "Austin"],
  "notes": "free-text field for anything that doesn't fit the schema",
  "interaction_log": [
    {
      "date": "2026-05-20",
      "type": "in_person | phone | video | message | email | other",
      "summary": "brief note on what was discussed or shared",
      "follow_up": "optional: what was agreed or should be checked on"
    }
  ],
  "created": "2026-05-01",
  "updated": "2026-05-20"
}
```

---

## Functions to build

```python
def write_contact(
    name: str,
    relationship_type: str = "",
    relationship_quality: str = "",
    last_contact: str = "",
    contact_frequency_preference: str = "",
    important_dates: list[dict] | None = None,
    tags: list[str] | None = None,
    notes: str = "",
    contact_id: str = "",  # if provided, update existing; if empty, create new
) -> str:
    """Create or update a contact record. Returns the contact ID."""

def read_contact(contact_id: str = "", name: str = "") -> str:
    """
    Read a single contact record by ID or name (fuzzy match on name).
    Returns JSON string of the contact, or error if not found.
    """

def list_contacts(
    relationship_type: str = "",
    relationship_quality: str = "",
    tag: str = "",
    overdue_only: bool = False,  # contacts past their frequency preference
) -> str:
    """
    List contacts, optionally filtered. Returns JSON array.
    overdue_only: return only contacts where last_contact + frequency_preference < today.
    """

def log_interaction(
    contact_id: str = "",
    name: str = "",  # fuzzy match if no ID
    interaction_type: str = "",
    summary: str = "",
    follow_up: str = "",
    date: str = "",  # defaults to today
) -> str:
    """Append an interaction to a contact's log. Updates last_contact date."""

def search_contacts(query: str) -> str:
    """
    Search contacts by name, tag, notes, or interaction log content.
    Simple substring match across all text fields. Returns JSON array of matches.
    """
```

---

## Implementation notes

- Use `uuid.uuid4()` for new contact IDs
- `_crm_path(persona)` helper — same pattern as `_logs_dir()` in logger.py
- All writes should be atomic: read → modify → write (do not partial-write)
- Add a `threading.Lock` at module level for write safety (same pattern being added to logger.py in a parallel task)
- For `overdue_only` in `list_contacts`: map frequency_preference strings to timedelta (daily=1, weekly=7, monthly=30, quarterly=90, as_needed=None/skip)
- Fuzzy name matching: case-insensitive substring is sufficient for now. If multiple matches, return the closest one and note ambiguity in the result string.
- `important_dates` field: store dates as `MM-DD` strings when year is unknown (birthdays where year wasn't given). Store as `YYYY-MM-DD` when full date is known.

---

## Schemas

Write Anthropic-format tool schemas for all five functions following the pattern in `tools/logger.py`. Name them `WRITE_CONTACT_SCHEMA`, `READ_CONTACT_SCHEMA`, `LIST_CONTACTS_SCHEMA`, `LOG_INTERACTION_SCHEMA`, `SEARCH_CONTACTS_SCHEMA`.

---

## Registration

In `core/orchestrator.py` → `register_tools()`:

```python
from tools.crm import (
    write_contact, read_contact, list_contacts, log_interaction, search_contacts,
    WRITE_CONTACT_SCHEMA, READ_CONTACT_SCHEMA, LIST_CONTACTS_SCHEMA,
    LOG_INTERACTION_SCHEMA, SEARCH_CONTACTS_SCHEMA,
)
```

Add all five schemas to the `schemas` list and all five handlers to the `handlers` dict.

---

## Relationships agent update

In `config/agents/relationships.md`, replace the current tools section with:

```markdown
## Tools available

- `write_contact(name, relationship_type, relationship_quality, last_contact, contact_frequency_preference, important_dates, tags, notes, contact_id)` — create or update a contact record
- `read_contact(contact_id, name)` — retrieve a single contact by ID or name
- `list_contacts(relationship_type, relationship_quality, tag, overdue_only)` — list contacts with optional filters; use `overdue_only=true` to surface who is due for contact
- `log_interaction(contact_id, name, interaction_type, summary, follow_up, date)` — record an interaction and update last_contact date
- `search_contacts(query)` — search across all contact fields
- `search_memory` — find prior mentions and relationship context in logs and journal
- `write_log` — record today's relationship fields
- `write_journal` — for significant relational events
- `read_wisdom` — check known patterns about this user's relational tendencies
```

Also add to the Relationships agent's "What you do" section, step 5: "**Maintain the contact record.** When a person is mentioned, check if they exist in the CRM via `read_contact`. If not, create a record. Log the interaction via `log_interaction`. Check `list_contacts(overdue_only=true)` periodically to surface who the user hasn't been in touch with for a while."

---

## What NOT to do

- Do not build a UI or web interface
- Do not sync with external services (CardDAV is Deliverable 6 — this is the local store it will eventually sync with)
- Do not change the data model of existing tools (write_log, write_archive, etc.)
- Do not add import statements to agent config files — only update the tools list description text
- Do not add auth or encryption — this is handled at the storage tier later (Phase 6, `age` encryption)

---

## Verification

1. In a Python REPL: create two contacts, log an interaction for each, list all contacts, search by tag, retrieve one by name. Confirm the contacts.json file is well-formed.
2. Run `python core/orchestrator.py --input "I just had lunch with my friend Sarah" --agent relationships` and confirm the agent creates/updates a contact record without error.
3. Confirm the orchestrator imports cleanly: `python -c "from core.orchestrator import register_tools; register_tools()"`.
