"""
tools/crm.py — Contact Relationship Manager.

Provides structured, persistent contact records for the Relationships agent.
Contacts are stored locally in data/crm/contacts.json (sensitive-tier).

For persona testing: data/personas/{persona}/crm/contacts.json.
"""

import json
import os
import threading
import uuid
from datetime import date, timedelta
from pathlib import Path

_CRM_LOCK = threading.Lock()

_ROOT = Path(__file__).parent.parent

# Frequency preference → days before overdue
_FREQUENCY_DAYS: dict[str, int | None] = {
    "daily": 1,
    "weekly": 7,
    "monthly": 30,
    "quarterly": 90,
    "as_needed": None,
}


def _crm_path() -> Path:
    """Return the path to contacts.json, accounting for test persona."""
    persona = os.environ.get("AI_TEST_PERSONA")
    if persona:
        return _ROOT / "data" / "personas" / persona / "crm" / "contacts.json"
    return _ROOT / "data" / "crm" / "contacts.json"


def _load_contacts() -> list[dict]:
    """Read contacts.json; return empty list if file does not exist."""
    path = _crm_path()
    if not path.exists():
        return []
    with open(path) as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def _save_contacts(contacts: list[dict]) -> None:
    """Write contacts list atomically."""
    path = _crm_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(contacts, f, indent=2)
    os.chmod(path, 0o600)


def _find_by_name(contacts: list[dict], name: str) -> list[dict]:
    """Case-insensitive substring match on name field."""
    needle = name.lower()
    return [c for c in contacts if needle in c.get("name", "").lower()]


# ---------------------------------------------------------------------------
# Public tool functions
# ---------------------------------------------------------------------------

def write_contact(
    name: str,
    first_name: str = "",
    last_name: str = "",
    nickname: str = "",
    referred_to_as: list[str] | None = None,
    primary_contact_type: str = "",
    relationship_type: str = "",
    relationship_quality: str = "",
    last_contact: str = "",
    contact_frequency_preference: str = "",
    spouse_name: str = "",
    kids_names: list[str] | None = None,
    education: str = "",
    occupation: str = "",
    employer: str = "",
    how_met: str = "",
    timezone: str = "",
    contact_info: dict | None = None,
    important_dates: list[dict] | None = None,
    tags: list[str] | None = None,
    notes: str = "",
    contact_id: str = "",
) -> str:
    """
    Create or update a contact record.

    If contact_id is provided and matches an existing record, that record is
    updated with any non-empty fields supplied. If contact_id is empty, a new
    contact is created.

    Returns the contact ID (new or existing).
    """
    today = date.today().isoformat()

    # String fields that follow the same update pattern
    _str_fields = [
        ("name", name),
        ("first_name", first_name),
        ("last_name", last_name),
        ("nickname", nickname),
        ("primary_contact_type", primary_contact_type),
        ("relationship_type", relationship_type),
        ("relationship_quality", relationship_quality),
        ("last_contact", last_contact),
        ("contact_frequency_preference", contact_frequency_preference),
        ("spouse_name", spouse_name),
        ("education", education),
        ("occupation", occupation),
        ("employer", employer),
        ("how_met", how_met),
        ("timezone", timezone),
        ("notes", notes),
    ]
    # List/dict fields: update when not None (passing [] or {} clears the field)
    _collection_fields = [
        ("referred_to_as", referred_to_as),
        ("kids_names", kids_names),
        ("contact_info", contact_info),
        ("important_dates", important_dates),
        ("tags", tags),
    ]

    with _CRM_LOCK:
        contacts = _load_contacts()

        if contact_id:
            for contact in contacts:
                if contact.get("id") == contact_id:
                    for field, value in _str_fields:
                        if value:
                            contact[field] = value
                    for field, value in _collection_fields:
                        if value is not None:
                            contact[field] = value
                    contact["updated"] = today
                    _save_contacts(contacts)
                    return contact_id
            return f"Error: no contact found with id '{contact_id}'"

        new_contact: dict = {
            "id": str(uuid.uuid4()),
            "name": name,
            "first_name": first_name,
            "last_name": last_name,
            "nickname": nickname,
            "referred_to_as": referred_to_as if referred_to_as is not None else [],
            "primary_contact_type": primary_contact_type,
            "relationship_type": relationship_type,
            "relationship_quality": relationship_quality,
            "last_contact": last_contact,
            "contact_frequency_preference": contact_frequency_preference,
            "spouse_name": spouse_name,
            "kids_names": kids_names if kids_names is not None else [],
            "education": education,
            "occupation": occupation,
            "employer": employer,
            "how_met": how_met,
            "timezone": timezone,
            "contact_info": contact_info if contact_info is not None else {},
            "important_dates": important_dates if important_dates is not None else [],
            "tags": tags if tags is not None else [],
            "notes": notes,
            "interaction_log": [],
            "created": today,
            "updated": today,
        }
        contacts.append(new_contact)
        _save_contacts(contacts)
        return new_contact["id"]


def read_contact(contact_id: str = "", name: str = "") -> str:
    """
    Read a single contact record by ID or name (fuzzy/case-insensitive match).

    Returns a JSON string of the contact record, or an error string if not found.
    If multiple name matches are found, returns the first and notes the ambiguity.
    """
    contacts = _load_contacts()

    if contact_id:
        for contact in contacts:
            if contact.get("id") == contact_id:
                return json.dumps(contact, indent=2)
        return f"Error: no contact found with id '{contact_id}'"

    if name:
        matches = _find_by_name(contacts, name)
        if not matches:
            return f"Error: no contact found matching name '{name}'"
        result = matches[0].copy()
        if len(matches) > 1:
            result["_ambiguity_note"] = (
                f"Multiple contacts matched '{name}': "
                + ", ".join(m["name"] for m in matches)
                + ". Returned the first match."
            )
        return json.dumps(result, indent=2)

    return "Error: provide either contact_id or name"


def list_contacts(
    relationship_type: str = "",
    relationship_quality: str = "",
    tag: str = "",
    overdue_only: bool = False,
) -> str:
    """
    List contacts with optional filters.

    Filters are ANDed together. overdue_only returns only contacts where
    last_contact + contact_frequency_preference < today (as_needed contacts
    are excluded from overdue logic).

    Returns a JSON array of matching contact records.
    """
    contacts = _load_contacts()
    today = date.today()
    results = []

    for contact in contacts:
        if relationship_type and contact.get("relationship_type") != relationship_type:
            continue
        if relationship_quality and contact.get("relationship_quality") != relationship_quality:
            continue
        if tag and tag not in contact.get("tags", []):
            continue

        if overdue_only:
            freq = contact.get("contact_frequency_preference", "")
            days = _FREQUENCY_DAYS.get(freq)
            if days is None:
                # as_needed — skip from overdue logic
                continue
            last = contact.get("last_contact", "")
            if not last:
                # Never contacted — overdue immediately
                results.append(contact)
                continue
            try:
                last_date = date.fromisoformat(last)
            except ValueError:
                continue
            due_date = last_date + timedelta(days=days)
            if due_date < today:
                results.append(contact)
        else:
            results.append(contact)

    return json.dumps(results, indent=2)


def log_interaction(
    contact_id: str = "",
    name: str = "",
    interaction_type: str = "",
    summary: str = "",
    follow_up: str = "",
    date: str = "",
) -> str:
    """
    Append an interaction entry to a contact's interaction_log.
    Also updates the contact's last_contact date to the interaction date.

    Returns a confirmation string.
    """
    from datetime import date as _date
    interaction_date = date if date else _date.today().isoformat()

    with _CRM_LOCK:
        contacts = _load_contacts()
        today = _date.today().isoformat()

        target = None
        if contact_id:
            for contact in contacts:
                if contact.get("id") == contact_id:
                    target = contact
                    break
            if target is None:
                return f"Error: no contact found with id '{contact_id}'"
        elif name:
            matches = _find_by_name(contacts, name)
            if not matches:
                return f"Error: no contact found matching name '{name}'"
            target = matches[0]
            if len(matches) > 1:
                ambiguity = (
                    f"Multiple contacts matched '{name}': "
                    + ", ".join(m["name"] for m in matches)
                    + ". Logged against the first match."
                )
            else:
                ambiguity = ""
        else:
            return "Error: provide either contact_id or name"

        entry: dict = {
            "date": interaction_date,
            "type": interaction_type,
            "summary": summary,
        }
        if follow_up:
            entry["follow_up"] = follow_up

        if "interaction_log" not in target:
            target["interaction_log"] = []
        target["interaction_log"].append(entry)
        target["last_contact"] = interaction_date
        target["updated"] = today

        _save_contacts(contacts)

    msg = f"Interaction logged for {target['name']} (id: {target['id']})"
    if "ambiguity" in locals() and ambiguity:
        msg += f". Note: {ambiguity}"
    return msg


def search_contacts(query: str) -> str:
    """
    Search contacts by substring match across name, tags, notes,
    and interaction log summaries/follow-ups.

    Returns a JSON array of matching contact records.
    """
    if not query:
        return "Error: query must not be empty"

    needle = query.lower()
    contacts = _load_contacts()
    results = []

    for contact in contacts:
        # Scalar text fields to search
        scalar_fields = [
            "name", "first_name", "last_name", "nickname",
            "spouse_name", "education", "occupation", "employer",
            "how_met", "notes",
        ]
        if any(needle in contact.get(f, "").lower() for f in scalar_fields):
            results.append(contact)
            continue

        # referred_to_as and kids_names (lists of strings)
        if any(needle in s.lower() for s in contact.get("referred_to_as", [])):
            results.append(contact)
            continue
        if any(needle in s.lower() for s in contact.get("kids_names", [])):
            results.append(contact)
            continue

        # tags
        if any(needle in t.lower() for t in contact.get("tags", [])):
            results.append(contact)
            continue

        # contact_info values (email, phone, address, social handles)
        ci = contact.get("contact_info", {})
        ci_text = " ".join(
            str(v) for v in ci.values() if isinstance(v, str)
        )
        social = ci.get("social", {})
        if isinstance(social, dict):
            ci_text += " " + " ".join(social.values())
        if needle in ci_text.lower():
            results.append(contact)
            continue

        # interaction log
        matched = False
        for entry in contact.get("interaction_log", []):
            if needle in entry.get("summary", "").lower():
                matched = True
                break
            if needle in entry.get("follow_up", "").lower():
                matched = True
                break
        if matched:
            results.append(contact)

    return json.dumps(results, indent=2)


# ---------------------------------------------------------------------------
# Tool schemas — registered with the Claude API in orchestrator.register_tools()
# ---------------------------------------------------------------------------

WRITE_CONTACT_SCHEMA = {
    "name": "write_contact",
    "description": (
        "Create or update a contact record in the CRM. "
        "If contact_id is provided, updates that record with the supplied fields. "
        "If contact_id is empty, creates a new contact and returns its ID."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Display name — how the user thinks of this person (e.g. 'Mom', 'Dr. Smith', 'Sarah').",
            },
            "first_name": {"type": "string", "description": "Legal or given first name."},
            "last_name": {"type": "string", "description": "Family name."},
            "nickname": {"type": "string", "description": "What you call them directly."},
            "referred_to_as": {
                "type": "array",
                "description": (
                    "All the ways the user refers to this person in speech — "
                    "e.g. ['Mom', 'my mother', 'my mom']. "
                    "Used to recognize mentions in unstructured text."
                ),
                "items": {"type": "string"},
            },
            "primary_contact_type": {
                "type": "string",
                "description": (
                    "Primary category for how this contact fits into the user's life. "
                    "One of: work_colleague, work_client, work_vendor, friend, family, "
                    "romantic_partner, acquaintance, service_provider, other. "
                    "Use relationship_type for the relational quality; use this field "
                    "for the functional category."
                ),
            },
            "relationship_type": {
                "type": "string",
                "description": (
                    "Category of relationship. "
                    "One of: friend, family, colleague, romantic, acquaintance, professional, other."
                ),
            },
            "relationship_quality": {
                "type": "string",
                "description": (
                    "Current quality of the relationship. "
                    "One of: close, warm, neutral, strained, lost_touch."
                ),
            },
            "last_contact": {
                "type": "string",
                "description": "Date of last contact in YYYY-MM-DD format.",
            },
            "contact_frequency_preference": {
                "type": "string",
                "description": (
                    "How often the user wants to stay in touch. "
                    "One of: daily, weekly, monthly, quarterly, as_needed."
                ),
            },
            "spouse_name": {"type": "string", "description": "Name of spouse or partner."},
            "kids_names": {
                "type": "array",
                "description": "Names of children.",
                "items": {"type": "string"},
            },
            "education": {
                "type": "string",
                "description": "Educational background, free text (e.g. 'Stanford MBA', 'PhD in biology').",
            },
            "occupation": {"type": "string", "description": "Job title or role."},
            "employer": {"type": "string", "description": "Company or organization."},
            "how_met": {"type": "string", "description": "How the user met this person (e.g. 'college roommate', 'intro from Sarah')."},
            "timezone": {
                "type": "string",
                "description": "IANA timezone string (e.g. 'America/Chicago'). Used for outreach timing.",
            },
            "contact_info": {
                "type": "object",
                "description": "Structured contact details.",
                "properties": {
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "address": {"type": "string"},
                    "social": {
                        "type": "object",
                        "description": "Social handles keyed by platform (e.g. {twitter: '@sarah', linkedin: 'sarah-chen'}).",
                    },
                },
            },
            "important_dates": {
                "type": "array",
                "description": (
                    "List of important dates. Each item: {label, date}. "
                    "date is MM-DD when year unknown, YYYY-MM-DD when known."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "date": {"type": "string"},
                    },
                    "required": ["label", "date"],
                },
            },
            "tags": {
                "type": "array",
                "description": "Free-form tags for grouping or searching (e.g. college, hiking, Austin).",
                "items": {"type": "string"},
            },
            "notes": {
                "type": "string",
                "description": "Free-text field for personality, context, and anything that doesn't fit the schema.",
            },
            "contact_id": {
                "type": "string",
                "description": (
                    "ID of an existing contact to update. "
                    "Leave empty to create a new contact."
                ),
            },
        },
        "required": ["name"],
    },
}

READ_CONTACT_SCHEMA = {
    "name": "read_contact",
    "description": (
        "Retrieve a single contact record by ID or name. "
        "Name matching is case-insensitive substring. "
        "If multiple contacts match the name, returns the first and notes ambiguity."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "contact_id": {
                "type": "string",
                "description": "Exact contact ID (UUID). Takes priority over name.",
            },
            "name": {
                "type": "string",
                "description": "Name or partial name to search for.",
            },
        },
        "required": [],
    },
}

LIST_CONTACTS_SCHEMA = {
    "name": "list_contacts",
    "description": (
        "List contacts with optional filters. All filters are ANDed. "
        "Use overdue_only=true to surface contacts who are past their contact frequency preference."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "relationship_type": {
                "type": "string",
                "description": (
                    "Filter by relationship type. "
                    "One of: friend, family, colleague, romantic, acquaintance, professional, other."
                ),
            },
            "relationship_quality": {
                "type": "string",
                "description": (
                    "Filter by relationship quality. "
                    "One of: close, warm, neutral, strained, lost_touch."
                ),
            },
            "tag": {
                "type": "string",
                "description": "Return only contacts that have this exact tag.",
            },
            "overdue_only": {
                "type": "boolean",
                "description": (
                    "If true, return only contacts whose last_contact date plus "
                    "their contact_frequency_preference interval is before today. "
                    "Contacts with as_needed preference are excluded."
                ),
            },
        },
        "required": [],
    },
}

LOG_INTERACTION_SCHEMA = {
    "name": "log_interaction",
    "description": (
        "Record an interaction with a contact. Appends an entry to the contact's "
        "interaction_log and updates their last_contact date."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "contact_id": {
                "type": "string",
                "description": "Exact contact ID. Takes priority over name.",
            },
            "name": {
                "type": "string",
                "description": "Contact name (fuzzy match) — used if contact_id is not provided.",
            },
            "interaction_type": {
                "type": "string",
                "description": (
                    "How they interacted. "
                    "One of: in_person, phone, video, message, email, other."
                ),
            },
            "summary": {
                "type": "string",
                "description": "Brief note on what was discussed or shared.",
            },
            "follow_up": {
                "type": "string",
                "description": "Optional: what was agreed or should be checked on later.",
            },
            "date": {
                "type": "string",
                "description": "Date of the interaction in YYYY-MM-DD format. Defaults to today.",
            },
        },
        "required": [],
    },
}

SEARCH_CONTACTS_SCHEMA = {
    "name": "search_contacts",
    "description": (
        "Search all contacts by substring match across name, tags, notes, "
        "and interaction log entries. Returns a JSON array of matching contacts."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search string — matched case-insensitively across all text fields.",
            },
        },
        "required": ["query"],
    },
}
