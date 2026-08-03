"""
tools/profile.py — Capture and read stable biographical facts about the user.

The user gives these in passing, mid-conversation: an email address while asking
for a booking, an occupation while talking about work, a medication while talking
about sleep. Without a home they are lost, or — worse — filed wherever the model
can reach, which on 2026-08-02 meant an email, postal address and phone number
landing in the persona preferences file and riding in every system prompt from
then on.

So the split is deliberate:

    profile.yaml   stable facts about who the user is        <- this module
    {persona}.md   how the user wants to be dealt with       <- tools/persona.py
    context.json   this week's threads and follow-ups        <- tools/context_tracker.py

Reading is a separate tool from writing on purpose. `load_profile()` renders a
short summary into the system prompt for every head-layer call, and contact
details are deliberately excluded from it — a phone number does not need to be
restated to the model on every exchange. Agents that genuinely need one (Logistics
making a booking, Physical Health checking a standing condition) call
`read_profile` at the point of use.

Sensitive-tier, local-only. Written 0600.
"""

import os
from pathlib import Path

import yaml

from core.persona import persona_config_dir

# Only these fields can be written. Not a security boundary — the model is not an
# attacker — but a schema boundary: without it the profile accretes invented keys
# that nothing reads, which is how the persona file filled up with a section no
# code knew about. An unknown field is a signal that something needs designing,
# so it is refused loudly rather than absorbed.
_SCALAR_FIELDS = {
    "name",
    "occupation",
    "household",
    "health_notes",
    "birth_year",
    "age",
}
_CONTACT_FIELDS = {"email", "phone", "address"}
_LOCATION_FIELDS = {"city", "country", "timezone"}

WRITABLE = _SCALAR_FIELDS | _CONTACT_FIELDS | _LOCATION_FIELDS | {"other"}

# Never rendered into the system prompt by load_profile(). Retrieved on demand.
_PROMPT_EXCLUDED = _CONTACT_FIELDS


def _profile_path() -> Path:
    return persona_config_dir() / "profile.yaml"


def _load() -> dict:
    path = _profile_path()
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"profile.yaml is not valid YAML: {e}") from e


def _save(data: dict) -> Path:
    path = _profile_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    os.chmod(path, 0o600)
    return path


def write_profile(field: str, value: str) -> str:
    """
    Record one stable biographical fact about the user.

    Args:
        field: One of the permitted field names (see WRITABLE).
        value: The value to store. For 'other', the entry is appended to a list
               rather than replacing what is already there.

    Returns:
        Confirmation string, or an error naming the permitted fields.
    """
    key = field.strip().lower()
    if key not in WRITABLE:
        return (
            f"Error: '{field}' is not a profile field. "
            f"Permitted: {', '.join(sorted(WRITABLE))}. "
            "Use 'other' for a stable fact that fits none of these. "
            "Interaction preferences — how the user wants to be spoken to — "
            "belong in the persona file instead."
        )

    text = str(value).strip()
    if not text:
        return f"Error: no value given for '{key}'."

    data = _load()

    if key == "other":
        entries = list(data.get("other") or [])
        if text in entries:
            return f"Already recorded in profile: {text}"
        entries.append(text)
        data["other"] = entries
    elif key in _CONTACT_FIELDS:
        contact = dict(data.get("contact") or {})
        contact[key] = text
        data["contact"] = contact
    elif key in _LOCATION_FIELDS:
        loc = dict(data.get("location") or {})
        loc[key] = text
        data["location"] = loc
    elif key in {"age", "birth_year"}:
        try:
            data[key] = int(text)
        except ValueError:
            return f"Error: '{key}' must be a whole number, got '{text}'."
    else:
        data[key] = text

    _save(data)
    where = "contact" if key in _CONTACT_FIELDS else ("location" if key in _LOCATION_FIELDS else key)
    return f"Profile updated: {where}.{key}" if where != key else f"Profile updated: {key}"


def read_profile(field: str = "") -> str:
    """
    Read stored biographical facts, including the ones kept out of the prompt.

    Call this at the point of use — when a booking needs an email address, or a
    health question needs a standing condition — rather than assuming the value
    is already in context. Contact details in particular are never in the prompt.

    Args:
        field: A single field name to read. Omit to get everything on file.

    Returns:
        The value, or a readable summary of the whole profile.
    """
    data = _load()
    if not data:
        return "No profile recorded yet."

    flat: dict[str, str] = {}
    for k, v in data.items():
        if k in {"contact", "location"} and isinstance(v, dict):
            flat.update({ik: str(iv) for ik, iv in v.items() if iv not in (None, "")})
        elif k == "other" and isinstance(v, list):
            for i, item in enumerate(v, 1):
                flat[f"other_{i}"] = str(item)
        elif k == "ambient":
            continue
        elif v not in (None, "", [], {}):
            flat[k] = str(v)

    if field:
        key = field.strip().lower()
        if key in flat:
            return f"{key}: {flat[key]}"
        return f"'{field}' is not recorded in the profile. On file: {', '.join(sorted(flat)) or 'nothing'}."

    return "\n".join(f"{k}: {v}" for k, v in flat.items()) or "No profile recorded yet."


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

WRITE_PROFILE_SCHEMA = {
    "name": "write_profile",
    "description": (
        "Record a stable biographical fact the user has given you — email, phone, "
        "address, occupation, household, health notes, age, or where they live. "
        "Use this whenever the user supplies such a detail in passing, so it is "
        "not lost: they should never have to give you the same detail twice. "
        "This is for facts about who they are. Preferences about how they want to "
        "be spoken to go to the persona file instead, and anything that is only "
        "true this week belongs in the context tracker."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "field": {
                "type": "string",
                "description": "Which fact is being recorded.",
                "enum": sorted(WRITABLE),
            },
            "value": {
                "type": "string",
                "description": (
                    "The value to store, exactly as the user gave it. For 'other', "
                    "a single short sentence stating one stable fact; it is appended "
                    "to the existing list rather than replacing it."
                ),
            },
        },
        "required": ["field", "value"],
    },
}

READ_PROFILE_SCHEMA = {
    "name": "read_profile",
    "description": (
        "Look up a stored fact about the user. Contact details (email, phone, "
        "address) are deliberately not included in your context, so call this when "
        "you actually need one — for a booking, a form, or a message. Omit the "
        "field name to see everything on file. If the value you need is not "
        "recorded, ask the user for it rather than guessing."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "field": {
                "type": "string",
                "description": (
                    "Field to read, e.g. 'email'. Omit to return the whole profile."
                ),
            },
        },
        "required": [],
    },
}
