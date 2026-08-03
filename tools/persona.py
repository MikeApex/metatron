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


def write_persona(section: str, content: str) -> str:
    """
    Add or replace a named section in the user's persona config file.

    If the section already exists, its content is replaced. If it does not
    exist, it is appended. Use for durable preferences that should persist
    across all sessions — not for session-level context (use write_context_tracker
    for that).

    Args:
        section: Section heading, e.g. "Interaction Preferences".
        content: Full content for the section as a markdown-formatted string.
                 Use bullet points for lists of preferences.

    Returns:
        Confirmation string.
    """
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

    confirmation = f"Persona updated: '{section}' written to {path.name}"

    warning = _redundancy_warning(text, content)
    return confirmation + warning if warning else confirmation


def _redundancy_warning(previous: str, content: str) -> str:
    """Flag newly-added preferences that restate a rule already in force.

    Warns; never blocks. The write has already happened by the time this runs,
    deliberately: refusing to record something the user actually said, in order
    to keep the file tidy, loses their words — a far worse failure than a
    duplicate line. It costs no model call and no extra turn, just regex over
    the config files, so it is safe on a write path.

    Catches only what this tool writes. Rules added by hand in a development
    session are invisible here, which is how the 2026-08-03 duplicates arose;
    `tools/rule_audit.py` sweeps for those.
    """
    try:
        from core.rule_classes import check_new_rule

        existing = {ln.strip().lstrip("-* ").strip()
                    for ln in previous.splitlines() if ln.strip().startswith(("-", "*"))}
        added = [ln.strip().lstrip("-* ").strip()
                 for ln in content.splitlines()
                 if ln.strip().startswith(("-", "*"))
                 and ln.strip().lstrip("-* ").strip() not in existing]

        notes = []
        for rule in added:
            for cls, other, _score in check_new_rule(rule, limit=1):
                notes.append(f'"{rule[:70]}" overlaps an existing {cls} rule')
                break
        if not notes:
            return ""

        return (
            "\n\nNOTE — this may already be covered: " + "; ".join(notes) + ". "
            "If the user is restating something you were already told, the "
            "instruction you hold is not working; that is a change to record, "
            "not a preference to store twice. Tell them you already have it and "
            "that it plainly isn't showing, and record an "
            "INSTRUCTION_CHANGE_REQUEST rather than leaving two copies."
        )
    except Exception:
        # A tidiness check must never break a write that already succeeded.
        return ""


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
        "Existing section content is replaced; new sections are appended."
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
