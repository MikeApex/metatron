"""
tools/agent_config.py — agent-owned persistent state storage.

Each specialist agent gets its own namespace in data/config/{agent_name}.json.
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

DATA_CONFIG_DIR = Path(__file__).parent.parent / "data" / "config"


def write_agent_config(agent_name: str, key: str, value: str) -> str:
    """
    Write a key-value entry to this agent's persistent config store.

    Merges with existing data — does not overwrite the whole file.
    Value is stored as a string; for structured data, pass JSON-encoded string.

    Args:
        agent_name: Name of the calling agent (e.g. 'physical_health', 'finance').
        key: Config key to set (e.g. 'active_workout_plan', 'budget_structure').
        value: Value to store. Use JSON encoding for structured objects.

    Returns:
        Confirmation string.
    """
    DATA_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config_path = DATA_CONFIG_DIR / f"{agent_name}.json"

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
    config_path = DATA_CONFIG_DIR / f"{agent_name}.json"

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
        "Sensitive-tier: local only."
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
