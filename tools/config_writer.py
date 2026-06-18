"""
tools/config_writer.py — write narrative config files (prime_directive.md, mission.md).

Both files are Sensitive-tier:
- Written with 600 permissions (owner read/write only)
- Never routed to a cloud LLM for analysis
"""

import os
from pathlib import Path

_ROOT = Path(__file__).parent.parent

ALLOWED_FILES = {"prime_directive.md", "mission.md"}


def _config_dir() -> Path:
    persona = os.environ.get("AI_TEST_PERSONA")
    if persona:
        return _ROOT / "config" / "personas" / persona
    return _ROOT / "config"


def write_config(filename: str, content: str) -> str:
    """
    Write a narrative config file.

    Args:
        filename: 'prime_directive.md' or 'mission.md'.
        content: Markdown content to write.

    Returns:
        Confirmation string.
    """
    if filename not in ALLOWED_FILES:
        return f"Error: '{filename}' is not allowed. Permitted: {sorted(ALLOWED_FILES)}"

    path = _config_dir() / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    os.chmod(path, 0o600)
    return f"Written: {path}"


WRITE_CONFIG_SCHEMA = {
    "name": "write_config",
    "description": (
        "Write a narrative config file — prime_directive.md or mission.md. "
        "Use at the end of a goals interview to record the user's terminal values "
        "and current life mission. Both are Sensitive-tier and never leave the local system."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "File to write. Must be 'prime_directive.md' or 'mission.md'.",
                "enum": ["prime_directive.md", "mission.md"],
            },
            "content": {
                "type": "string",
                "description": "Markdown content to write to the file.",
            },
        },
        "required": ["filename", "content"],
    },
}
