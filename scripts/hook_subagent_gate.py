#!/usr/bin/env python3
"""SubagentStop gate: a worker may not report done until qa_sweep.sh passes.

WHY THIS IS A HOOK AND NOT AN INSTRUCTION
-----------------------------------------
A worker told "run the checks before reporting" sometimes does not, and then
reports success. That failure is invisible: the diff looks fine, the summary says
it passed, and nothing re-checks. Enforcement has to sit somewhere the worker
cannot skip, which is the hook layer.

WHAT IT BLOCKS, AND WHAT IT DELIBERATELY DOES NOT
-------------------------------------------------
Blocks: a worker finishing with the tree in a statically-broken state -- a syntax
error, a hand-edited PROJECT_LOG.md, an agent file naming a tool that does not
exist, a duplicate backlog ID.

Does NOT block: anything qa_sweep cannot see. py_compile parses but does not
execute; it passed the NameError that crash-looped the scheduler after deploy, and
it passed one in the commit guard. A worker cleared by this gate has cleared a
static check, not a test. The block message says so, because a gate that implies
more assurance than it delivers is worse than no gate.

FAIL-OPEN, DELIBERATELY, IN ONE DIRECTION ONLY
----------------------------------------------
If the sweep cannot RUN -- missing script, timeout, unreadable payload -- this
returns 0 and lets the worker report. A gate that blocks every worker because of
its own breakage would strand real finished work, and the same reasoning already
governs hook_context_gate.py (warn, never block) and sync_dev_backlog.py (never
break a session start). A sweep that runs and FAILS is a different thing entirely,
and that does block.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SWEEP_TIMEOUT_SECONDS = 180
MAX_DETAIL_CHARS = 4000


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0

    # A worker that has already been blocked once and is being asked again would
    # otherwise loop on the same failure forever.
    if payload.get("stop_hook_active"):
        return 0

    root = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()
    sweep = root / "scripts" / "qa_sweep.sh"
    if not sweep.is_file():
        return 0

    try:
        proc = subprocess.run(
            ["bash", str(sweep)],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=SWEEP_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        # See the fail-open note above: the gate's own breakage must not strand
        # a worker's finished work.
        return 0

    if proc.returncode == 0:
        return 0

    detail = (proc.stdout or "") + (proc.stderr or "")
    if len(detail) > MAX_DETAIL_CHARS:
        detail = detail[:MAX_DETAIL_CHARS] + "\n… (truncated — run scripts/qa_sweep.sh for the rest)"

    reason = (
        "SUBAGENT GATE: scripts/qa_sweep.sh failed — you may not report done yet.\n\n"
        f"{detail}\n"
        "Fix what the sweep names, then finish. If a failure is pre-existing and "
        "not yours, say so explicitly in your report rather than silently leaving "
        "it — the coordinator needs to know which it is.\n\n"
        "Note: the sweep is a STATIC check. Passing it does not mean the change "
        "works; py_compile parses without executing. Run what you changed."
    )

    # decision/reason is what SubagentStop understands; the worker is handed the
    # reason and continues rather than stopping.
    print(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
