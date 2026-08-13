#!/usr/bin/env python3
"""PreToolUse notice: a subagent is being spawned.

Removing ~800 approval prompts removes the thing that was also acting as the
status display — the pause that made a tool call get read. Narration replaces
it, and narration that depends on the model remembering is not a control. This
hook fires whether or not the spawn was announced in chat.

Never blocks. Purely informational.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

MAX_TASK_CHARS = 140


def _first_line(text: str, limit: int = MAX_TASK_CHARS) -> str:
    line = " ".join((text or "").split())
    return line[: limit - 1] + "…" if len(line) > limit else line


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0

    args = payload.get("tool_input") or {}
    desc = args.get("description") or _first_line(args.get("prompt", "")) or "(no description)"
    model = args.get("model") or "inherited"
    agent = args.get("subagent_type") or "general-purpose"
    isolation = args.get("isolation") or "shared tree"
    background = args.get("run_in_background")
    mode = "background" if background is not False else "foreground"

    line = (
        "WORKER SPAWNED  model={model}  type={agent}  isolation={isolation}  {mode}\n"
        "                task: {desc}"
    ).format(model=model, agent=agent, isolation=isolation, mode=mode, desc=desc)

    # stderr at exit 0 is transcript-mode only and never reaches the model, so
    # the notice would not do the job this hook exists for. additionalContext
    # does. Emit both — the terminal reader and the model see the same line.
    print(line, file=sys.stderr)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": (
                "A worker is being spawned — report it to the user: "
                + " ".join(line.split())
            ),
        }
    }))

    # Append to a per-session ledger so a fan-out can be reconstructed afterwards
    # even if the chat scrolled past it.
    try:
        root = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()
        ledger_dir = root / ".claude" / ".session_state"
        ledger_dir.mkdir(parents=True, exist_ok=True)
        ledger = ledger_dir / f"{payload.get('session_id', 'unknown')}.spawns.log"
        with open(ledger, "a") as fh:
            fh.write("{ts}\t{model}\t{agent}\t{isolation}\t{desc}\n".format(
                ts=datetime.now().isoformat(timespec="seconds"),
                model=model, agent=agent, isolation=isolation, desc=desc,
            ))
    except OSError:
        pass  # a ledger write must never interfere with the spawn

    return 0


if __name__ == "__main__":
    sys.exit(main())
