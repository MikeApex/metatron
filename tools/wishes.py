"""
tools/wishes.py — "Life Admin" / emergency and legacy document store.

Stores structured personal documents for emergency access, incapacitation
planning, and end-of-life preferences. This is a separate module from the
emergency medical record — scope is broader: legal, legacy, and estate.

User-facing name: "Life Admin" or "Emergency & Legacy". Never "Wishes"
in user-facing copy.

Sections:
  emergency_contacts   — people to call; relationship, authority level, phone
  medical_poa          — medical power of attorney: name, contact, document location
  advance_directive    — key directives, DNR status, document location
  legal_documents      — will, trust, safe deposit, executor name + location
  last_will            — funeral, burial, disposition preferences
  custody_designations — children, pets, named guardians
  digital_estate       — accounts, passwords manager location, digital asset notes
  notes                — freeform notes

Sensitive-tier: local only, never cloud-routed.
Encryption: deferred to Phase 6 (age). Flag: Phase 6.75 legal review —
jurisdiction-specific obligations around advance directives and emergency info.
"""

import json
import os
from pathlib import Path

WISHES_DIR = Path(__file__).parent.parent / "data" / "wishes"
WISHES_FILE = WISHES_DIR / "wishes.json"

VALID_SECTIONS = {
    "emergency_contacts",
    "medical_poa",
    "advance_directive",
    "legal_documents",
    "last_will",
    "custody_designations",
    "digital_estate",
    "notes",
}


def _load() -> dict:
    if not WISHES_FILE.exists():
        return {}
    try:
        return json.loads(WISHES_FILE.read_text())
    except json.JSONDecodeError:
        return {}


def _save(data: dict) -> None:
    WISHES_DIR.mkdir(parents=True, exist_ok=True)
    WISHES_FILE.write_text(json.dumps(data, indent=2))
    os.chmod(WISHES_FILE, 0o600)


def write_wishes(section: str, content: str) -> str:
    """
    Write or update a named section of the Life Admin document store.

    Args:
        section: One of the named sections (e.g. 'emergency_contacts').
        content: Content to store in this section. Use structured text or
                 JSON-encoded string for complex data.

    Returns:
        Confirmation string.
    """
    if section not in VALID_SECTIONS:
        return (
            f"Error: '{section}' is not a valid section. "
            f"Valid sections: {sorted(VALID_SECTIONS)}"
        )
    data = _load()
    data[section] = content
    _save(data)
    return f"Saved section '{section}' to Life Admin store."


def read_wishes(section: str = "") -> str:
    """
    Read from the Life Admin document store.

    Args:
        section: Specific section to read. If empty, returns all sections as JSON.

    Returns:
        Section content, full JSON, or not-found message.
    """
    data = _load()

    if not data:
        return "No Life Admin data found."

    if not section:
        return json.dumps(data, indent=2)

    if section not in VALID_SECTIONS:
        return (
            f"Error: '{section}' is not a valid section. "
            f"Valid sections: {sorted(VALID_SECTIONS)}"
        )

    if section not in data:
        return f"Section '{section}' has not been filled in yet."

    return str(data[section])


def generate_emergency_card() -> str:
    """
    Generate a minimal plain-text emergency card for first responders.

    Outputs: emergency contacts, medical POA, key advance directive notes
    (e.g. DNR status), and primary care physician if noted.

    Returns:
        Plain-text emergency card string.
    """
    data = _load()

    if not data:
        return "No Life Admin data on file. No emergency card can be generated."

    lines = ["=== EMERGENCY CARD ===", ""]

    contacts = data.get("emergency_contacts", "")
    if contacts:
        lines.append("EMERGENCY CONTACTS")
        lines.append(str(contacts))
        lines.append("")

    poa = data.get("medical_poa", "")
    if poa:
        lines.append("MEDICAL POWER OF ATTORNEY")
        lines.append(str(poa))
        lines.append("")

    directive = data.get("advance_directive", "")
    if directive:
        lines.append("ADVANCE DIRECTIVE / KEY MEDICAL WISHES")
        lines.append(str(directive))
        lines.append("")

    if len(lines) == 2:
        return "Emergency card is empty — no contacts, POA, or advance directive on file."

    lines.append("=== END ===")
    return "\n".join(lines)


WRITE_WISHES_SCHEMA = {
    "name": "write_wishes",
    "description": (
        "Write or update a named section of the Life Admin document store "
        "(emergency contacts, medical POA, advance directive, legal documents, "
        "last wishes, custody designations, digital estate, notes). "
        "User-facing name for this feature: 'Life Admin' or 'Emergency & Legacy'. "
        "Sensitive-tier: local only, never cloud-routed. "
        "Encryption deferred to Phase 6."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "section": {
                "type": "string",
                "description": "Section to write.",
                "enum": sorted(VALID_SECTIONS),
            },
            "content": {
                "type": "string",
                "description": (
                    "Content for this section. Use plain text or a JSON-encoded "
                    "string for structured data (e.g. a list of contacts with names "
                    "and phone numbers)."
                ),
            },
        },
        "required": ["section", "content"],
    },
}

READ_WISHES_SCHEMA = {
    "name": "read_wishes",
    "description": (
        "Read from the Life Admin document store. Returns a specific section "
        "or the full store as JSON. Use to retrieve emergency contacts, advance "
        "directive status, or any Life Admin content for surfacing to the user "
        "or emergency card generation."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "section": {
                "type": "string",
                "description": (
                    "Section to read. If omitted, returns all sections as JSON."
                ),
                "enum": sorted(VALID_SECTIONS),
            },
        },
        "required": [],
    },
}

GENERATE_EMERGENCY_CARD_SCHEMA = {
    "name": "generate_emergency_card",
    "description": (
        "Generate a minimal plain-text emergency card from the Life Admin store. "
        "Outputs emergency contacts, medical POA name, and key advance directive "
        "notes (e.g. DNR status). Intended for first responder use — concise and "
        "actionable. Returns a plain-text string the user can print or save."
    ),
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}
