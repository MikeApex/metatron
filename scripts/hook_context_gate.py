#!/usr/bin/env python3
"""PreToolUse gate. Two checks, both warn-only, both once per session.

1. **Context** — has this session actually read SESSION.md and ROADMAP.md?
   `CLAUDE.md` § Mandatory Pre-Edit Context Check requires it. That rule has been
   prose since a session edited without reading and every edit had to be reverted
   — prose a session can skim past. This makes the harness say it instead.

2. **Permission mode** — is the mode `settings.json` asks for the one actually in
   force? `defaultMode: "auto"` silently falls back when auto mode isn't available
   to the account or CLI version, and the only symptom is prompts that were
   supposed to stop. A silent fallback is exactly the class of failure this project
   keeps paying for; it should announce itself rather than be inferred from vibes.

**Warns, never blocks.** Refusing an edit to enforce a reading habit would discard
work the user asked for, which is the worse failure. Same posture as
`check_new_rule()` in core/rule_classes.py, and for the same reason.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REQUIRED = ("SESSION.md", "ROADMAP.md")

# Editing these needs no project context — they are notes, not the system.
EXEMPT_DIRS = ("archive/", "tests/fixtures/", ".claude/plans/", "scratchpad/")
EXEMPT_NAMES = ("dummy", ".dev_backlog_seen")


def _already_warned(session_id: str, root: Path, kind: str = "context_gate") -> bool:
    """One warning per session per check. Returns True if we've already fired."""
    marker_dir = root / ".claude" / ".session_state"
    marker = marker_dir / f"{session_id}.{kind}"
    if marker.exists():
        return True
    try:
        marker_dir.mkdir(parents=True, exist_ok=True)
        marker.touch()
    except OSError:
        pass  # can't record it — better to warn twice than to crash an edit
    return False


def _files_read(transcript_path: str) -> set:
    """Basenames this session has called Read on."""
    seen = set()
    if not transcript_path or not os.path.exists(transcript_path):
        return seen
    try:
        with open(transcript_path, errors="ignore") as fh:
            for line in fh:
                # Cheap prefilter — these transcripts reach tens of MB.
                if '"Read"' not in line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                content = (rec.get("message") or {}).get("content")
                if not isinstance(content, list):
                    continue
                for block in content:
                    if (
                        isinstance(block, dict)
                        and block.get("type") == "tool_use"
                        and block.get("name") == "Read"
                    ):
                        path = (block.get("input") or {}).get("file_path", "")
                        if path:
                            seen.add(os.path.basename(path))
    except OSError:
        pass
    return seen


def _configured_mode(root: Path):
    """The defaultMode `.claude/settings.json` asks for, or None."""
    try:
        with open(root / ".claude" / "settings.json") as fh:
            return (json.load(fh).get("permissions") or {}).get("defaultMode")
    except (OSError, ValueError):
        return None


def _mode_warning(payload: dict, root: Path):
    """Warn if the requested permission mode is not the one in force.

    Only fires on a *silent fallback* — configured `auto`, actually running
    `default`. A deliberate switch (plan, acceptEdits, bypassPermissions) is the
    user's choice and is none of this hook's business.
    """
    actual = payload.get("permission_mode")
    if not actual:
        return None  # this event didn't carry the field
    wanted = _configured_mode(root)
    if not wanted or actual == wanted:
        return None

    # Only the silent-fallback shape warrants a warning: the configured mode did
    # not take effect and the session quietly dropped to `default`. Every other
    # mismatch is the user switching modes on purpose (plan, acceptEdits, …) and
    # is none of this hook's business — warning there would misdiagnose the cause
    # and prescribe a fix for a problem that does not exist.
    if actual != "default":
        return None

    if _already_warned(payload.get("session_id", "unknown"), root, "mode_check"):
        return None

    if wanted == "auto":
        remedy = (
            "Auto mode is probably unavailable to this account or CLI version, so "
            "ordinary Bash calls will keep prompting. Fix: switch the mode for this "
            "session, or replace defaultMode with an explicit permissions.allow list "
            "— compound commands are matched per-subcommand, so an allowlist reaches "
            "the same coverage."
        )
    else:
        remedy = (
            "The configured mode did not take effect. Check that this CLI version "
            "supports it, and that no higher-precedence settings file overrides it."
        )
    return (
        "PERMISSION MODE FALLBACK: .claude/settings.json requests defaultMode "
        "'{wanted}' but this session is running '{actual}'. {remedy}"
    ).format(wanted=wanted, actual=actual, remedy=remedy)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0  # malformed input is never a reason to interfere with an edit

    # Both checks run every call and their notes are emitted together. An earlier
    # version returned after the mode warning, which meant a session making exactly
    # one edit under the fallback condition never got the context check at all —
    # the two are independent and must not consume each other.
    notes = []
    root_early = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()
    mode_note = _mode_warning(payload, root_early)
    if mode_note:
        notes.append(mode_note)

    context_note = _context_warning(payload, root_early)
    if context_note:
        notes.append(context_note)

    return _emit(notes)


def _context_warning(payload: dict, root: Path):
    """The pre-edit context check. None when it has nothing to say."""
    target = (payload.get("tool_input") or {}).get("file_path", "")
    if not target:
        return None
    try:
        rel = str(Path(target).resolve().relative_to(root))
    except ValueError:
        return None  # outside the project — not this gate's business

    if os.path.basename(rel) in EXEMPT_NAMES:
        return None
    if any(rel.startswith(d) for d in EXEMPT_DIRS):
        return None

    read = _files_read(payload.get("transcript_path", ""))
    missing = [f for f in REQUIRED if f not in read]
    if not missing:
        return None
    if _already_warned(payload.get("session_id", "unknown"), root):
        return None

    return (
        "PRE-EDIT CONTEXT CHECK: about to edit `{rel}` without having read {missing} "
        "this session. CLAUDE.md requires both before any code, config, or agent-file "
        "edit — current phase, freezes, and file-ownership rules live there. Run "
        "/metatron-code, or state why this edit is exempt. "
        "(Warning only; the edit proceeds. Fires once per session.)"
    ).format(rel=rel, missing=" and ".join(missing))


def _emit(notes) -> int:
    if not notes:
        return 0
    joined = "\n\n".join(notes)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": joined,
        }
    }))
    print("WARN " + joined, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
