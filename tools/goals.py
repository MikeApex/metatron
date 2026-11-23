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


# `long` sits above quarterly (goal–task network plan § 4.6, § 10 R6): a language is not a
# 90-day goal. Every reader that walks horizons reads this tuple, so a long goal links,
# weights and sweeps like the rest.
HORIZONS = ("long", "quarterly", "weekly", "daily")
_ID_PREFIX = {"long": "l", "quarterly": "q", "weekly": "w", "daily": "d"}

# Goal statuses. `proposed` is a goal stated in chat and not yet vetted; `parked` is "later",
# with a date to re-ask; `declined` is kept, not deleted (archive-on-merge). Only the first
# four reach prompts as current goals; `proposed` reaches them under "being considered";
# `parked` and `declined` never (§ 10 R6, `prompt_view`). Only `active` goals are decomposed.
STATUSES = ("active", "not_started", "at_risk", "completed", "proposed", "parked", "declined")
CURRENT = ("active", "not_started", "at_risk")
_SIZES = ("S", "M", "L")

# Fields an in-conversation edit may set. `private_why` is here because a goal
# added mid-conversation usually arrives with its motivation attached — the
# reason is the part worth capturing, and asking the user to repeat it in a
# formal interview later is how it gets lost.
_EDITABLE = ("title", "private_why", "shareable_what", "status", "due",
             "parent_goal", "context", "essential", "size", "kind", "timeline",
             "open_questions", "revisit_on")


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


def _calling_agent() -> str:
    """The agent whose tool call this is, from the request trace; "" when none is bound (a
    direct call, a test). Read, never trusted from an argument a model fills in."""
    try:
        from core.trace import get_current_agent
        rec = get_current_agent()
        return str(getattr(rec, "agent", "") or "")
    except Exception:  # noqa: BLE001
        return ""


def _find_goal(data: dict, goal_id: str) -> tuple[str, int, dict] | None:
    for h in HORIZONS:
        for i, g in enumerate(data.get(h) or []):
            if isinstance(g, dict) and str(g.get("id", "")) == goal_id:
                return h, i, g
    return None


def _iso(value: str) -> str | None:
    try:
        return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


def _close_steps(goal_id: str, status: str) -> None:
    """A task part_of a goal that is declined, parked or completed is closed with that reason
    (§ 4.1). The ledger owns the write; a failure never blocks the goal change."""
    try:
        from tools.obligations import close_plan_of
        close_plan_of(goal_id, f"its goal was {status}")
    except Exception:  # noqa: BLE001
        pass


_VET_PRIORITIES = ("high", "normal", "low")


def vet_goal(goal_id: str, verdict: str, size: str = "", displaces: str = "", priority: str = "",
             revisit_on: str = "", by: str = "", kind: str = "") -> str:
    """Record a vetting verdict on one goal (§ 4.2, § 10 R3). Depth is the size Synth gave it in
    the turn: S needs nothing beyond the ledger; M needs a date it is feasible by and a priority
    against what is open; L is vetted by the Goals Interviewer's re-interview, which is phase 3 —
    until then an L goal stays `proposed` ("being considered") and is never decomposed."""
    verdict = str(verdict or "").strip().lower()
    if verdict not in ("active", "parked", "declined"):
        return "Error: verdict must be active, parked or declined."
    size = str(size or "").strip().upper()
    data = read_goals()
    hit = _find_goal(data, str(goal_id or "").strip())
    if not hit:
        return f"Error: no goal with id '{goal_id}'."
    h, _i, g = hit
    size = size or str(g.get("size") or "").upper()
    # high | normal | low since 2026-11-22 (ranking § 16): free text ("ahead of the Northwind
    # review", 11-21) was recorded and then ignored by every score. What it ranks above goes in
    # `displaces`.
    priority = str(priority or "").strip().lower()
    if priority and priority not in _VET_PRIORITIES:
        return ("Error: `priority` is high, normal or low — put what it ranks above in "
                "`displaces`. Nothing was changed.")
    kind = str(kind or "").strip().lower()
    if kind and kind not in ("goal", "obligation"):
        return "Error: kind is goal or obligation. Nothing was changed."
    if verdict == "active":
        if size not in _SIZES:
            return ("Error: say how big it is first — size S (one sitting), M (hours to days, one "
                    "end date) or L (recurring time for weeks or more). Nothing was changed.")
        if size == "L":
            # § 4.2's L row: Synth's SHORT pass — what it displaces in a real week and where it
            # ranks — takes it on; the Interviewer's full pass is phase 3. Without this, every
            # recurring goal stated in chat stayed "being considered" for the whole phase 2 → 3
            # interval, where today it becomes current and gets weekly time (Fable diff review #4).
            # An L goal is given weekly time, never steps (plan_project refuses it).
            if not str(displaces or "").strip() or not str(priority or "").strip():
                return ("Error: a goal that needs regular time is taken on only once it is clear "
                        "what it takes that time from in a real week (`displaces`) and where it "
                        "ranks (`priority`). Nothing was changed.")
        if size == "M":
            if not _iso(g.get("due") or ""):
                return ("Error: an M goal is vetted against its date — set `due` first (update_goal "
                        "action=update), then vet. Nothing was changed.")
            if not str(priority or "").strip():
                return ("Error: say where it ranks against what is already open (`priority`). "
                        "Nothing was changed.")
    if verdict == "parked":
        when = _iso(revisit_on)
        if not when:
            return "Error: a parked goal needs `revisit_on` (YYYY-MM-DD), the day to ask again."
        g["revisit_on"] = when
    g["status"] = verdict
    if size in _SIZES:
        g["size"] = size
    if kind:
        g["kind"] = kind
    g["vetted"] = {k: v for k, v in (
        ("date", datetime.now().strftime("%Y-%m-%d")), ("depth", size or None),
        ("displaces", str(displaces or "").strip() or None),
        ("priority", str(priority or "").strip() or None),
        ("by", by or _calling_agent() or None),
        ("pass", "short" if size == "L" and verdict == "active" else None)) if v}
    _write(data)
    if verdict in ("parked", "declined"):
        _close_steps(str(g["id"]), verdict)
    elif verdict == "active":
        # A goal re-vetted at a new priority (or as an obligation) re-weighs its open steps now,
        # not at tomorrow's sweep (ranking § 16). Never blocks the verdict.
        try:
            from tools.obligations import reweigh_plan_steps, _GOAL_CACHE
            _GOAL_CACHE.update(key=None)
            reweigh_plan_steps()
        except Exception:  # noqa: BLE001
            pass
    word = {"active": "taken on", "parked": f"parked until {g.get('revisit_on')}",
            "declined": "declined (kept on record)"}[verdict]
    tail = (" Ask plan_project to break it into steps." if verdict == "active" and size == "M"
            else " It is given regular time each week, not steps." if verdict == "active"
            and size == "L" else "")
    return f"{h} goal {g['id']} {word}.{tail}"


def prompt_view(data: dict) -> str:
    """Goals as every prompt sees them (§ 10 R6) — the one filter. Current goals (active,
    not_started, at_risk; and completed, which the record keeps) as YAML; proposed ones under a
    short "being considered" heading; parked and declined never; `vetted` records never. A goal
    with no status is active, as it has always been read."""
    current: dict = {}
    considered: list[str] = []
    for h in HORIZONS:
        for g in data.get(h) or []:
            if not isinstance(g, dict):
                continue
            status = str(g.get("status") or "active")
            if status in ("parked", "declined"):
                continue
            if status == "proposed":
                considered.append(f"- {g.get('id', '?')}: {g.get('title', '')}"
                                  + (f" (by {g['due']})" if g.get("due") else ""))
                continue
            current.setdefault(h, []).append({k: v for k, v in g.items() if k != "vetted"})
    for k, v in data.items():
        if k not in HORIZONS and k not in current:
            current[k] = v
    out = yaml.dump(current, default_flow_style=False, allow_unicode=True, sort_keys=False).strip() \
        if current else ""
    text = f"```yaml\n{out}\n```" if out else ""
    if considered:
        text += ("\n\n### Being considered (not yet taken on — never treat these as current goals)\n"
                 + "\n".join(considered))
    return text.strip()


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
    essential: bool | str | None = None,
    size: str = "",
    kind: str = "",
    verdict: str = "",
    displaces: str = "",
    priority: str = "",
    revisit_on: str = "",
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
    if action not in ("add", "update", "complete", "remove", "vet"):
        return "Error: action must be one of add, update, complete, remove, vet."
    if action == "vet":
        return vet_goal(goal_id, verdict, size=size, displaces=displaces, priority=priority,
                        revisit_on=revisit_on, kind=kind)

    data = read_goals()
    fields = {k: v for k, v in (
        ("title", title), ("private_why", private_why),
        ("shareable_what", shareable_what), ("status", status), ("due", due),
        ("parent_goal", parent_goal), ("context", context),
    ) if str(v).strip()}
    if fields.get("status") and fields["status"].strip().lower() not in STATUSES:
        return f"Error: status must be one of {', '.join(STATUSES)}."
    if "status" in fields:
        fields["status"] = fields["status"].strip().lower()
    if str(size).strip():
        if str(size).strip().upper() not in _SIZES:
            return "Error: size is S, M or L."
        fields["size"] = str(size).strip().upper()
    if str(kind).strip():
        if str(kind).strip().lower() not in ("goal", "obligation"):
            return "Error: kind is goal or obligation."
        fields["kind"] = str(kind).strip().lower()
    if fields.get("due") and not _iso(fields["due"]):
        return "Error: due is YYYY-MM-DD."
    # § 10 R6: a goal stated in chat is written `proposed`, in code, whatever status the model
    # sent — and only a vetting verdict (action=vet) takes it on. The Goals Interviewer authors
    # vetted goals and keeps its default.
    from_synth = _calling_agent() == "synthesizer"
    if from_synth and action == "update" and fields.get("status") in ("active", "not_started",
                                                                      "at_risk", "parked",
                                                                      "declined"):
        hit = _find_goal(data, str(goal_id).strip())
        if hit and str(hit[2].get("status") or "active") == "proposed":
            return ("Error: a goal being considered is taken on, parked or declined with "
                    "action=vet (it records the verdict). Nothing was changed.")
    # `essential` — "survived trade-off forcing": the goals the day planner protects time for
    # (archive/plans/day_planner_plan_2026-10-24.md § 4.1). Only write_goals could set it before,
    # so the Synthesizer could not mediate goal importance (Mike, F4). A real bool is stored,
    # never the string a model may send.
    if essential is not None and str(essential).strip() != "":
        ess = str(essential).strip().lower()
        if ess not in ("true", "false"):
            return "Error: essential must be true or false."
        fields["essential"] = ess == "true"

    if action == "add":
        if horizon not in HORIZONS:
            return f"Error: horizon must be one of {list(HORIZONS)} to add a goal."
        if "title" not in fields:
            return "Error: title is required to add a goal."
        bucket = data.setdefault(horizon, []) or []
        data[horizon] = bucket
        new = {"id": _next_id(bucket, horizon)}
        new.update(fields)
        if from_synth:
            new["status"] = "proposed"
        new.setdefault("status", "active")
        bucket.append(new)
        _write(data)
        if new["status"] == "proposed":
            return (f"Added {horizon} goal {new['id']} as being considered: {new['title']}. "
                    f"Size it and check it with the user (action=vet) before it is taken on.")
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
                    _close_steps(goal_id, "completed")
                    return f"Completed {h} goal {goal_id}: {g.get('title', '')}"
                if not fields:
                    return (f"Error: nothing to change on {goal_id} — pass at "
                            f"least one of {list(_EDITABLE)}.")
                g.update(fields)
                _write(data)
                if fields.get("status") in ("parked", "declined", "completed"):
                    _close_steps(goal_id, fields["status"])
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
        "goal named is touched.\n\n"
        "A goal added from conversation is recorded as being considered, not taken on. "
        "Use 'vet' to record the verdict once it has been checked with the user: verdict "
        "active (taken on), parked (with revisit_on) or declined (kept on record)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "description": "add | update | complete | remove | vet"},
            "horizon": {"type": "string", "description": "long | quarterly | weekly | daily. Required for add. long = longer than a quarter."},
            "goal_id": {"type": "string", "description": "Id of the goal, e.g. 'd2'. Required for update, complete, remove."},
            "title": {"type": "string", "description": "The goal in one line. Required for add."},
            "private_why": {"type": "string", "description": "The user's underlying motivation, in their own terms. Sensitive — never leaves this system."},
            "shareable_what": {"type": "string", "description": "The instrumental behaviour: what doing this looks like concretely."},
            "status": {"type": "string", "description": "active | not_started | at_risk | completed"},
            "due": {"type": "string", "description": "YYYY-MM-DD, if there is a date."},
            "parent_goal": {"type": "string", "description": "Id of the goal this serves, e.g. a weekly goal under 'q1'."},
            "context": {"type": "string", "description": "Anything worth knowing about how this goal has been going."},
            "size": {"type": "string", "description": "S (one sitting, about an hour) | M (hours to days, one end date) | L (recurring time for weeks or more)."},
            "kind": {"type": "string", "description": "goal | obligation (something that must be done, e.g. filing taxes). Also for vet."},
            "verdict": {"type": "string", "description": "For vet: active | parked | declined."},
            "priority": {"type": "string", "description": "For vet: high | normal | low — how it ranks against what is already open, by what missing it would cost (an obligation like taxes is high even when it serves no goal)."},
            "displaces": {"type": "string", "description": "For vet: what it takes time from, if anything."},
            "revisit_on": {"type": "string", "description": "For vet with verdict parked: YYYY-MM-DD to ask again."},
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
        "(long, quarterly, weekly, daily). Each key replaces the existing value for that horizon. "
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


def goal_schemas() -> tuple[dict, dict]:
    """(read_goals, update_goal) as models should see them. `essential` is added only when the
    day planner's `ledger_fields` flag is on (review R1-1); off, the constants are returned as
    they have always been."""
    try:
        from tools.day_plan_config import flag
        exposed = flag("ledger_fields")
    except Exception:  # noqa: BLE001
        exposed = False
    if not exposed:
        return READ_GOALS_SCHEMA, UPDATE_GOAL_SCHEMA
    import copy
    upd = copy.deepcopy(UPDATE_GOAL_SCHEMA)
    upd["input_schema"]["properties"]["essential"] = {
        "type": "boolean",
        "description": "True for a goal that must not slip — one the user has said matters "
                       "more than the rest. Its tasks are protected when the day is planned.",
    }
    return READ_GOALS_SCHEMA, upd
