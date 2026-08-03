"""
tools/persona.py — Write durable user preferences to the persona config file.

Used by the Synthesizer when the user explicitly states a preference about how
they want to interact. Writes to config/personas/{persona}.md so the preference
persists across all future sessions (not just the context tracker window).

Sensitive-tier, local-only.
"""

import os
import re
from pathlib import Path

from core.persona import persona_md

_ROOT = Path(__file__).parent.parent


def _persona_path() -> Path:
    return persona_md()


# The persona file is for *how the user wants to be dealt with*, and nothing else.
# It is loaded into the system prompt of every head-layer call, so anything written
# here is restated to the model on every single exchange for the life of the file.
#
# Left open, this tool becomes the path of least resistance for any durable fact.
# On 2026-08-02 the user gave an email address, postal address and phone number in
# passing while asking for a booking; they were filed here under a freely-invented
# "## Contact Information" heading, and from then on rode in every prompt. They
# belong in profile.yaml, which is structured, and whose contact block is
# deliberately not rendered into the prompt at all.
#
# Enforced here rather than in the agent instructions, per the standing rule that
# data placement is enforced in Python and never in prompts.
_ALLOWED_SECTIONS = {
    "interaction preferences",
    "communication style",
    "boundaries",
}

_REJECTION = (
    "Error: '{section}' is not a permitted persona section. "
    "The persona file holds interaction preferences only — how the user wants to be "
    "spoken to. Permitted sections: {allowed}. "
    "Biographical or contact details (email, phone, address, occupation, household, "
    "health) are not stored here; they belong in the user profile. If the user has "
    "just given you such a detail, tell them plainly that you cannot store it yet "
    "rather than recording it somewhere it does not belong."
)


def write_persona(section: str, content: str) -> str:
    """
    Add or replace a named section in the user's persona config file.

    If the section already exists, its content is replaced. If it does not
    exist, it is appended. Use for durable preferences that should persist
    across all sessions — not for session-level context (use write_context_tracker
    for that).

    Only preference-shaped sections are accepted; see _ALLOWED_SECTIONS.

    Args:
        section: Section heading, e.g. "Interaction Preferences".
        content: Full content for the section as a markdown-formatted string.
                 Use bullet points for lists of preferences.

    Returns:
        Confirmation string, or an error string naming the permitted sections.
    """
    if section.strip().lower().lstrip("# ") not in _ALLOWED_SECTIONS:
        return _REJECTION.format(
            section=section,
            allowed=", ".join(f"'{s.title()}'" for s in sorted(_ALLOWED_SECTIONS)),
        )

    path = _persona_path()
    if not path.exists():
        raise FileNotFoundError(f"Persona file not found: {path}")

    text = path.read_text()

    # Build the replacement block
    new_block = f"## {section}\n\n{content.strip()}\n"

    # Look for an existing section with this heading
    pattern = re.compile(
        rf'^## {re.escape(section)}\n.*?(?=^## |\Z)',
        re.MULTILINE | re.DOTALL,
    )
    if pattern.search(text):
        updated = pattern.sub(new_block, text)
    else:
        updated = text.rstrip('\n') + f"\n\n{new_block}"

    path.write_text(updated)
    os.chmod(path, 0o600)
    return f"Persona updated: '{section}' written to {path.name}"


# ---------------------------------------------------------------------------
# Tool schema
# ---------------------------------------------------------------------------

WRITE_PERSONA_SCHEMA = {
    "name": "write_persona",
    "description": (
        "Write a durable user preference to the persona config file. "
        "Use this when the user explicitly states how they want to interact "
        "or how they want responses shaped — preferences that should persist "
        "indefinitely, not just for this session. "
        "Pass the section name (e.g. 'Interaction Preferences') and the full "
        "updated content for that section as markdown bullet points. "
        "Existing section content is replaced; new sections are appended. "
        "Preferences only — this is not where biographical or contact details "
        "(email, phone, address, occupation, household, health) are stored, and "
        "writes to any other section are rejected."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "section": {
                "type": "string",
                "description": (
                    "Section heading in the persona file. Use existing headings "
                    "when updating (e.g. 'Interaction Preferences'). "
                    "Use a new heading only for genuinely new categories."
                ),
            },
            "content": {
                "type": "string",
                "description": (
                    "Full content for the section as a markdown-formatted string. "
                    "Write bullet points for lists of preferences. "
                    "This replaces the entire section, so include all existing "
                    "preferences when updating — do not write partial updates."
                ),
            },
        },
        "required": ["section", "content"],
    },
}
