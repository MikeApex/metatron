"""
tools/agent_config.py — agent-owned persistent state storage.

Each specialist agent gets its own namespace in
data/personas/{persona}/config/{agent_name}.json.
This is user-data config space — not system config. Agents store structured
preferences, plans, and state here (workout plans, budget structures, coping
protocols, active skill goals, etc.).

System config (prime_directive.md, mission.md, scheduler.yaml) is managed
by tools/config_writer.py — separate tool, separate scope.

All data is Sensitive-tier: local only, never cloud-routed.
"""

import json
import os
from pathlib import Path

from core.persona import persona_data_dir


def _agent_config_dir() -> Path:
    """Per-persona agent state. Health and finance state must never cross personas."""
    return persona_data_dir() / "config"


# Keys an agent may READ but never WRITE, as (agent_name, key) pairs.
#
# WHY: a safety flag must not be able to author the data it classifies from.
# physical_health.md:106 requires MEDICATION_MISSED_CRITICAL to be classified from the stored
# medication profile and "never from the agent's judgment" — but on 2026-08-05 the agent was
# granted write_agent_config, which without this guard would let it write the profile, then
# read it back as authority, and grade its own homework. The 2026-08-04 workaround was to deny
# write_agent_config outright; that cost the agent an ordinary config store every other
# specialist has, so the narrow guard replaced the blanket denial.
#
# Enforced here in Python rather than in the instruction file, per CLAUDE.md: being told is not
# being prevented. logistics was told it lacked write_agent_config and called it anyway, three
# times in production.
#
# The profile is seeded out-of-band — by the user, or by tests/run_a4_safety.py's fixture.
_GUARDED_KEYS: set[tuple[str, str]] = {
    ("physical_health", "medication_profile"),
}


def write_agent_config(agent_name: str, key: str, value: str, confirm_token: str = "") -> str | dict:
    """
    Write a key-value entry to this agent's persistent config store.

    Merges with existing data — does not overwrite the whole file.
    Value is stored as a string; for structured data, pass JSON-encoded string.

    Ordinary keys write immediately, as before — gating every routine specialist write
    (workout plans, budget structures) behind approval would make the tool unusable.

    The (agent, key) pairs in _GUARDED_KEYS are different: this is data a safety flag
    classifies from, so the agent that reads it must not also be the one that wrote it.
    Until 2026-08-05 that meant an outright refusal, which cost the agent an ordinary
    config store over one specific value. Routed through the confirm gate instead: the
    user can see the proposed change and approve it out of band, same mechanism as
    send_email — "gate it rather than granting or refusing outright" (DB-0805-01).

    Args:
        agent_name: Name of the calling agent (e.g. 'physical_health', 'finance').
        key: Config key to set (e.g. 'active_workout_plan', 'budget_structure').
        value: Value to store. Use JSON encoding for structured objects.
        confirm_token: For guarded keys only — the token from a PENDING_CONFIRMATION
            response, after the user has approved it. Omit otherwise.

    Returns:
        Confirmation string once written, or a PENDING_CONFIRMATION dict for a guarded key.
    """
    if (agent_name, key) in _GUARDED_KEYS:
        from tools.confirm import consume, request

        args = {"agent_name": agent_name, "key": key, "value": value}
        ok, reason = consume(confirm_token or None, "write_agent_config", args)
        if not ok:
            if confirm_token:
                return f"Error: not written. {reason}"
            preview = value if len(value) <= 400 else value[:400] + " […]"
            return request(
                "write_agent_config", args,
                description=(
                    f"{agent_name} wants to update '{key}', a value a safety flag "
                    f"classifies from:\n\n{preview}"
                ),
            )

    config_dir = _agent_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / f"{agent_name}.json"

    existing: dict = {}
    if config_path.exists():
        try:
            existing = json.loads(config_path.read_text())
        except json.JSONDecodeError:
            existing = {}

    existing[key] = value
    config_path.write_text(json.dumps(existing, indent=2))
    os.chmod(config_path, 0o600)
    return f"Saved {key} to {agent_name} config."


def read_agent_config(agent_name: str, key: str = "") -> str:
    """
    Read from this agent's persistent config store.

    Args:
        agent_name: Name of the calling agent.
        key: Specific key to retrieve. If empty, returns the full config as JSON.

    Returns:
        Value string, full JSON config, or a not-found message.
    """
    config_path = _agent_config_dir() / f"{agent_name}.json"

    if not config_path.exists():
        return f"No config found for {agent_name}."

    try:
        data = json.loads(config_path.read_text())
    except json.JSONDecodeError:
        return f"Config for {agent_name} exists but could not be parsed."

    if not key:
        return json.dumps(data, indent=2)

    if key not in data:
        return f"Key '{key}' not found in {agent_name} config."

    return str(data[key])


WRITE_AGENT_CONFIG_SCHEMA = {
    "name": "write_agent_config",
    "description": (
        "Write a key-value entry to this agent's persistent config store at "
        "data/config/{agent_name}.json. Use this to persist structured state: "
        "workout plans, budget structures, coping protocols, active skill goals, "
        "medication profiles, user preferences, or any structured data this agent "
        "manages across sessions. Merges with existing data — safe to call repeatedly. "
        "For structured values (objects, lists), pass a JSON-encoded string. "
        "Sensitive-tier: local only. A small set of keys (e.g. physical_health's "
        "medication_profile) are guarded: the first call returns PENDING_CONFIRMATION "
        "instead of writing, and needs a second call with confirm_token after the user "
        "approves it in the app. Ordinary keys write immediately, as always."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {
                "type": "string",
                "description": (
                    "Name of the calling agent. Use the snake_case agent identifier: "
                    "physical_health, mental_wellbeing, finance, learning_growth, "
                    "work_vocation, relationships, recreation_hobbies, logistics."
                ),
            },
            "key": {
                "type": "string",
                "description": (
                    "Config key to set. Examples: 'active_workout_plan', "
                    "'budget_structure', 'medication_profile', 'coping_protocols', "
                    "'active_skill_goals', 'cessation_program'."
                ),
            },
            "value": {
                "type": "string",
                "description": (
                    "Value to store. For structured data (objects, lists), "
                    "pass a JSON-encoded string."
                ),
            },
            "confirm_token": {
                "type": "string",
                "description": (
                    "Only needed for guarded keys (e.g. medication_profile): the token "
                    "from the PENDING_CONFIRMATION response, after the user has approved "
                    "it. Omit for ordinary keys and on the first call for a guarded one."
                ),
            },
        },
        "required": ["agent_name", "key", "value"],
    },
}

READ_AGENT_CONFIG_SCHEMA = {
    "name": "read_agent_config",
    "description": (
        "Read from this agent's persistent config store at "
        "data/config/{agent_name}.json. Returns a specific key's value, "
        "or the full config as JSON if no key is provided. "
        "Use at session start to load active plans, goals, and preferences "
        "this agent has previously stored."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {
                "type": "string",
                "description": "Name of the calling agent (snake_case).",
            },
            "key": {
                "type": "string",
                "description": (
                    "Specific key to retrieve. If omitted or empty, "
                    "returns the full config as JSON."
                ),
            },
        },
        "required": ["agent_name"],
    },
}
