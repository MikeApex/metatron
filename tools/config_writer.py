"""
tools/config_writer.py — write narrative config files (prime_directive.md, mission.md).

Both files are Sensitive-tier:
- Written with 600 permissions (owner read/write only)
- Never routed to a cloud LLM for analysis
"""

import os
from datetime import datetime
from pathlib import Path

from core.persona import persona_config_dir

_ROOT = Path(__file__).parent.parent

ALLOWED_FILES = {"prime_directive.md", "mission.md"}


def _config_dir() -> Path:
    return persona_config_dir()


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

    # These are Tier 1 and Tier 2 — terminal values and current life chapter,
    # the least-changed files in the system. The write is a full replacement and
    # the agent holding it runs on every exchange, so a rewrite the user never
    # asked for would otherwise be unrecoverable. Keep the previous version.
    if path.exists():
        previous = path.read_text()
        if previous.strip() and previous != content:
            stamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
            backup = path.with_name(f"{path.stem}.{stamp}{path.suffix}.bak")
            try:
                backup.write_text(previous)
                os.chmod(backup, 0o600)
            except OSError as e:
                # A failed backup must not block a change the user did ask for.
                print(f"[write_config] WARNING: could not back up {path}: {e}")

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
