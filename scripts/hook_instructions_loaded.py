#!/usr/bin/env python3
"""InstructionsLoaded logger — DISPOSABLE INSTRUMENTATION, Phase 5 only.

**Retirement condition, stated up front because the standing rule in
`.claude/rules/deploy.md` requires it: unregister this hook and delete this file
once Phase 5's two open questions are answered.** They are:

  1. Does a **Grep-tool** survey trigger `path_glob_match`? Bash `grep` was shown
     on 2026-08-14 not to, and a `Write` to a governed path was shown not to
     either — but the Grep tool itself could not be tested, because that session
     had no Grep tool. `/backlog attack` workers and Explore agents survey by
     grep, so this decides whether the thinnest-context sessions get rules.
  2. Do rules load in a **worktree** session? The rule files are present on disk
     there (verified), but delivery could not be observed from the main tree —
     `.claude/rules/` is discovered at session start, so it needs a session
     actually started in the worktree.

Both need a session other than the one asking, which is the whole reason this
exists: it is the only instrument that sees the *injection*.
`scripts/audit_context_load.py` reconstructs Read calls from the JSONL, so it
sees the trigger but never the load or its reason.

A permanent seventh hook logging every instruction load forever is exactly the
machinery class the context-system plan exists to reduce. Kill it on schedule.

**NOT REGISTERED YET — this file is inert until a `hooks.InstructionsLoaded`
block is added to `.claude/settings.json` (deferred 2026-08-14).** Register with
NO matcher: the matcher filters on load reason, and the reasons are exactly what
is being measured, so filtering would presuppose the answer.

    "InstructionsLoaded": [
      {"hooks": [{"type": "command",
                  "command": "python3 \"$CLAUDE_PROJECT_DIR/scripts/hook_instructions_loaded.py\"",
                  "timeout": 10}]}
    ]

Do not try to put an explanatory `_comment_*` key beside it. `settings.json`
accepts those only inside `permissions`; under `hooks` and at the root the CLI
validator rejects them and reverts the edit (measured 2026-08-14, twice). That is
why this rationale lives here.

`InstructionsLoaded` is a real event, confirmed against the docs on 2026-08-14
rather than assumed — the same settings file records `defaultMode: "auto"` being
accepted by the parser and then silently never honoured. Its load reasons are
`session_start`, `nested_traversal`, `path_glob_match`, `include`, `compact`.

Writes one JSON line per load to `.claude/instructions_loaded.jsonl`, which is
gitignored by the existing `.claude/*` rule. Never blocks; always exits 0.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

LOG_NAME = ".claude/instructions_loaded.jsonl"


def project_root() -> Path:
    """Prefer the harness-supplied root; fall back to git, then cwd.

    A worktree is one of the two things this hook exists to observe, and
    CLAUDE_PROJECT_DIR points at the main tree there — the same trap
    hook_context_gate.py hit on 2026-08-14. So git is consulted from the cwd
    first and only then the env var, which inverts the usual order deliberately.
    """
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True, timeout=5,
        )
        root = out.stdout.strip()
        if root:
            return Path(root)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass

    env_root = os.environ.get("CLAUDE_PROJECT_DIR")
    return Path(env_root) if env_root else Path.cwd()


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0

    # The whole payload is recorded rather than named fields. The docs do not
    # specify InstructionsLoaded's event-specific keys (which file, which
    # reason), and an instrument that guesses a key name reports "no data" for a
    # working mechanism — the failure mode this phase is investigating.
    record = {
        "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
        "cwd": os.getcwd(),
        "payload": payload,
    }

    try:
        log_path = project_root() / LOG_NAME
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a") as fh:
            fh.write(json.dumps(record) + "\n")
    except OSError:
        # Instrumentation must never be the reason a session fails.
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
