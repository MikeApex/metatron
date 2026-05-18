"""
tools/goals.py — read and write goals.yaml.

Goals are Sensitive-tier from day one:
- Written with 600 permissions (owner read/write only)
- Never routed to a cloud LLM for analysis (Phase 3+: local LLM only)
- The `private_why` field is the user's underlying motivation — it must never
  leave this system. The `shareable_what` field is the instrumental behavior
  and may be summarized for cloud LLM advice in Phase 3+.

Structure:
    quarterly:   90-day goals
    weekly:      weekly priorities (link to quarterly via parent_goal)
    daily:       today's focus items (link to weekly via parent_goal)
"""

import os
from pathlib import Path

import yaml

_ROOT = Path(__file__).parent.parent


def _goals_path() -> Path:
    persona = os.environ.get("AI_TEST_PERSONA")
    if persona:
        return _ROOT / "config" / "personas" / persona / "goals.yaml"
    return _ROOT / "config" / "goals.yaml"


def read_goals() -> dict:
    """
    Read the current goals file.

    Returns:
        Parsed goals as a dict, or empty dict if no goals file exists yet.
    """
    goals_path = _goals_path()
    if not goals_path.exists():
        return {}

    with open(goals_path) as f:
        data = yaml.safe_load(f)

    return data or {}


def write_goals(content: dict) -> str:
    """
    Write goals to config/goals.yaml with 600 permissions.

    Merges top-level keys with any existing content (quarterly, weekly, daily).
    A key present in content replaces the existing value entirely — use this
    to update one horizon at a time without stomping the others.

    Args:
        content: Dict with one or more of: quarterly, weekly, daily.

    Returns:
        Confirmation string.
    """
    existing = read_goals()
    existing.update(content)

    goals_path = _goals_path()
    goals_path.parent.mkdir(parents=True, exist_ok=True)

    with open(goals_path, "w") as f:
        yaml.dump(existing, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    os.chmod(goals_path, 0o600)

    return f"Goals written to {goals_path}"


# Tool schemas — registered in orchestrator.register_tools()

READ_GOALS_SCHEMA = {
    "name": "read_goals",
    "description": (
        "Read the user's current goals (quarterly, weekly, daily). "
        "Use this at the start of a session to ground direction in the user's stated priorities."
    ),
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

WRITE_GOALS_SCHEMA = {
    "name": "write_goals",
    "description": (
        "Write or update goals. Pass a dict with one or more horizon keys "
        "(quarterly, weekly, daily). Each key replaces the existing value for that horizon. "
        "Each goal should include: title, private_why (sensitive — motivation), "
        "shareable_what (semi-sensitive — instrumental behavior), status, and optionally "
        "due (YYYY-MM-DD) and parent_goal (id of the parent goal)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "content": {
                "type": "object",
                "description": (
                    "Goals to write. Keys: quarterly, weekly, and/or daily. "
                    "Each is a list of goal objects."
                ),
            },
        },
        "required": ["content"],
    },
}
