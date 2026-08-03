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
from datetime import datetime
from pathlib import Path

import yaml

from core.persona import persona_config_dir

_ROOT = Path(__file__).parent.parent


def _goals_path() -> Path:
    return persona_config_dir() / "goals.yaml"


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


HORIZONS = ("quarterly", "weekly", "daily")
_ID_PREFIX = {"quarterly": "q", "weekly": "w", "daily": "d"}

# Fields an in-conversation edit may set. `private_why` is here because a goal
# added mid-conversation usually arrives with its motivation attached — the
# reason is the part worth capturing, and asking the user to repeat it in a
# formal interview later is how it gets lost.
_EDITABLE = ("title", "private_why", "shareable_what", "status", "due",
             "parent_goal", "context")


def _next_id(goals: list, horizon: str) -> str:
    prefix = _ID_PREFIX[horizon]
    used = set()
    for g in goals:
        gid = str(g.get("id", ""))
        if gid.startswith(prefix) and gid[len(prefix):].isdigit():
            used.add(int(gid[len(prefix):]))
    n = 1
    while n in used:
        n += 1
    return f"{prefix}{n}"


def update_goal(
    action: str,
    horizon: str = "",
    goal_id: str = "",
    title: str = "",
    private_why: str = "",
    shareable_what: str = "",
    status: str = "",
    due: str = "",
    parent_goal: str = "",
    context: str = "",
) -> str:
    """
    Add, edit, complete or remove a single goal.

    Separate from `write_goals`, which replaces a whole horizon at once. That
    shape is right for the goals interview, which authors the full set, and
    wrong for everything else: updating one daily goal means resending the
    entire daily list, and any goal left out of that list is silently deleted.
    Goals change continuously — one is finished, one is added — so the ordinary
    path has to be one goal at a time.

    Args:
        action:   add | update | complete | remove.
        horizon:  quarterly | weekly | daily. Required for add; inferred from
                  goal_id otherwise.
        goal_id:  Required for update, complete and remove.
        The rest:  Fields to set. For `update`, only the ones passed change.

    Returns:
        Confirmation, or an explanatory refusal.
    """
    action = str(action).strip().lower()
    if action not in ("add", "update", "complete", "remove"):
        return "Error: action must be one of add, update, complete, remove."

    data = read_goals()
    fields = {k: v for k, v in (
        ("title", title), ("private_why", private_why),
        ("shareable_what", shareable_what), ("status", status), ("due", due),
        ("parent_goal", parent_goal), ("context", context),
    ) if str(v).strip()}

    if action == "add":
        if horizon not in HORIZONS:
            return f"Error: horizon must be one of {list(HORIZONS)} to add a goal."
        if "title" not in fields:
            return "Error: title is required to add a goal."
        bucket = data.setdefault(horizon, []) or []
        data[horizon] = bucket
        new = {"id": _next_id(bucket, horizon)}
        new.update(fields)
        new.setdefault("status", "active")
        bucket.append(new)
        _write(data)
        return f"Added {horizon} goal {new['id']}: {new['title']}"

    if not str(goal_id).strip():
        return f"Error: goal_id is required to {action} a goal. Use read_goals to find it."
    goal_id = str(goal_id).strip()

    # Locate the goal. Searching every horizon rather than trusting the caller's
    # `horizon` means a wrong horizon corrects itself instead of reporting a
    # goal missing that is plainly there.
    for h in HORIZONS:
        bucket = data.get(h) or []
        for i, g in enumerate(bucket):
            if str(g.get("id", "")) == goal_id:
                if action == "remove":
                    bucket.pop(i)
                    _write(data)
                    return (f"Removed {h} goal {goal_id}: {g.get('title', '')}. "
                            f"Use action 'complete' instead when a goal was "
                            f"achieved — that keeps the record.")
                if action == "complete":
                    g["status"] = "completed"
                    g["completed_on"] = datetime.now().strftime("%Y-%m-%d")
                    g.update(fields)
                    _write(data)
                    return f"Completed {h} goal {goal_id}: {g.get('title', '')}"
                if not fields:
                    return (f"Error: nothing to change on {goal_id} — pass at "
                            f"least one of {list(_EDITABLE)}.")
                g.update(fields)
                _write(data)
                return (f"Updated {h} goal {goal_id}: "
                        f"{', '.join(sorted(fields))} changed.")

    known = ", ".join(str(g.get("id", "?")) for h in HORIZONS for g in (data.get(h) or []))
    return f"Error: no goal with id '{goal_id}'. Existing ids: {known or 'none'}."


def _write(data: dict) -> None:
    path = _goals_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    os.chmod(path, 0o600)


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

UPDATE_GOAL_SCHEMA = {
    "name": "update_goal",
    "description": (
        "Add, edit, complete or remove ONE goal. This is the ordinary way goals "
        "change: the user finishes something, adds something, or revises what "
        "they are aiming at, in the middle of a normal conversation.\n\n"
        "Use 'complete' when a goal has been achieved — it keeps the goal on "
        "record with a completion date. Use 'remove' only for a goal that was "
        "abandoned or entered by mistake.\n\n"
        "Call read_goals first to get the goal's id. Nothing outside the one "
        "goal named is touched."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "description": "add | update | complete | remove"},
            "horizon": {"type": "string", "description": "quarterly | weekly | daily. Required for add."},
            "goal_id": {"type": "string", "description": "Id of the goal, e.g. 'd2'. Required for update, complete, remove."},
            "title": {"type": "string", "description": "The goal in one line. Required for add."},
            "private_why": {"type": "string", "description": "The user's underlying motivation, in their own terms. Sensitive — never leaves this system."},
            "shareable_what": {"type": "string", "description": "The instrumental behaviour: what doing this looks like concretely."},
            "status": {"type": "string", "description": "active | not_started | at_risk | completed"},
            "due": {"type": "string", "description": "YYYY-MM-DD, if there is a date."},
            "parent_goal": {"type": "string", "description": "Id of the goal this serves, e.g. a weekly goal under 'q1'."},
            "context": {"type": "string", "description": "Anything worth knowing about how this goal has been going."},
        },
        "required": ["action"],
    },
}

WRITE_GOALS_SCHEMA = {
    "name": "write_goals",
    "description": (
        "Replace one or more whole goal horizons at once. Use ONLY when authoring "
        "a complete set, as at the end of a goals interview — every goal omitted "
        "from a horizon you pass is deleted. To change a single goal, use "
        "update_goal instead.\n\n"
        "Pass a dict with one or more horizon keys "
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
