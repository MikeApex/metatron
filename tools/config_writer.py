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


def write_config(filename: str, content: str, confirm_token: str = "") -> str | dict:
    """
    Write a narrative config file. Requires the user's explicit approval, given in the app.

    Two-step by design, same mechanism as send_email: the first call returns
    PENDING_CONFIRMATION and writes nothing. These are Tier 1/2 terminal values — the
    least-changed files in the system — so a rewrite the user never asked for must not
    happen silently, per B2's "no agent can permanently modify system behavior without
    explicit user confirmation."

    Args:
        filename: 'prime_directive.md' or 'mission.md'.
        content: Markdown content to write.
        confirm_token: The token from the PENDING_CONFIRMATION response, after the user
            has approved it. Omit on the first call.

    Returns:
        Confirmation string once written, or a PENDING_CONFIRMATION dict.
    """
    from tools.confirm import consume, request

    if filename not in ALLOWED_FILES:
        return f"Error: '{filename}' is not allowed. Permitted: {sorted(ALLOWED_FILES)}"

    args = {"filename": filename, "content": content}
    ok, reason = consume(confirm_token or None, "write_config", args)
    if not ok:
        if confirm_token:
            return f"Error: not written. {reason}"
        preview = content if len(content) <= 400 else content[:400] + " […]"
        return request(
            "write_config", args,
            description=f"Update {filename}:\n\n{preview}",
        )

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
        "and current life mission. Both are Sensitive-tier and never leave the local system. "
        "Requires the user's explicit approval: the first call returns PENDING_CONFIRMATION "
        "and writes nothing — show the user what will change and leave it with them. "
        "Approving it in the app is what writes it; do not call this tool a second time. "
        "Never claim it is written before that."
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
            "confirm_token": {
                "type": "string",
                "description": "Not for you to set. The app supplies this when it carries out an action the user has approved; leave it out of every call you make.",
            },
        },
        "required": ["filename", "content"],
    },
}
