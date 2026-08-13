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

IT MUST SWEEP THE WORKER'S TREE, NOT THE SESSION'S
--------------------------------------------------
CLAUDE_PROJECT_DIR is the tree the SESSION started in. A worker spawned with
isolation="worktree" -- which is what /fix dispatches -- works somewhere else
entirely. Swept against CLAUDE_PROJECT_DIR the gate would pass workers whose
worktree is broken and fail them for the main tree's state, which is worse than
no gate: it reports assurance it does not have. So the payload's cwd wins, and
the env var is only a fallback. Each candidate is checked for qa_sweep.sh before
being used, so a cwd pointing outside any project tree degrades to fail-open
rather than sweeping the wrong thing.

Every run appends one line to the SESSION tree's .claude/.session_state/
subagent_gate.log recording which tree was chosen and why -- because "the gate
ran" and "the gate ran against the right tree" look identical from the outside,
and that is precisely the failure mode being guarded against. See _log for why
the session tree and not the swept one.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SWEEP_TIMEOUT_SECONDS = 180
MAX_DETAIL_CHARS = 4000
# Bound on trees swept in one gate run, so a pile of stale worktrees cannot blow
# the 200s hook timeout. Three concurrent workers is the standing cap, plus the
# session tree.
MAX_TREES = 4


def _candidate_roots(payload: dict) -> list[tuple[str, Path]]:
    """Trees this gate might sweep, best first. See the module docstring."""
    out: list[tuple[str, Path]] = []
    cwd = payload.get("cwd")
    if cwd:
        out.append(("payload.cwd", Path(cwd)))
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        out.append(("CLAUDE_PROJECT_DIR", Path(env)))
    out.append(("process cwd", Path(".")))
    return out


def _resolve_root(payload: dict) -> tuple[str, Path | None]:
    for source, path in _candidate_roots(payload):
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if (resolved / "scripts" / "qa_sweep.sh").is_file():
            return source, resolved
    return "none", None


def _dirty_worktrees(root: Path) -> list[Path]:
    """Registered git worktrees carrying uncommitted work, excluding `root`.

    ASKING GIT BEATS BEING TOLD. A worker cannot persistently cd -- the shell
    resets between calls -- so a worker dispatched into a worktree edits it by
    ABSOLUTE PATH while its payload cwd stays pinned to the main tree. Measured
    2026-08-13: the gate swept the main tree and passed while the worker's real
    change sat unswept in the worktree. Preferring payload.cwd is therefore not
    enough on its own.

    Both dispatch styles register a real git worktree, though -- the harness's
    isolation="worktree" trees under .claude/worktrees/ and new_worktree.sh's
    trees alike -- so `git worktree list` finds the work wherever it went,
    without the worker cooperating and without any ID to correlate.

    KNOWN LIMIT, so a green gate is not over-trusted: this attributes by
    dirtiness, not by authorship. A worktree another window left dirty will be
    swept too, and could block a worker for a fault that is not its own. The
    block message names the tree and tells the worker to say so, which is the
    same stance the sweep already takes on pre-existing failures. Bounded by
    MAX_TREES so a pile of stale worktrees cannot blow the hook's timeout.
    """
    try:
        listing = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=str(root), capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if listing.returncode != 0:
        return []

    out: list[Path] = []
    for line in listing.stdout.splitlines():
        if not line.startswith("worktree "):
            continue
        try:
            path = Path(line[len("worktree "):].strip()).resolve()
        except OSError:
            continue
        if path == root or not (path / "scripts" / "qa_sweep.sh").is_file():
            continue
        try:
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(path), capture_output=True, text=True, timeout=15,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if status.returncode == 0 and status.stdout.strip():
            out.append(path)
    return out[:MAX_TREES]


def _log(line: str) -> None:
    """Best-effort diagnostic. Never interferes with the gate's decision.

    Always written to the SESSION tree, never to the tree just swept. An
    isolation="worktree" worktree is deleted the moment the worker finishes
    without changes, taking its .claude/ with it -- so logging beside the swept
    tree loses exactly the runs where the gate worked and keeps the ones where
    it fell back. Found by running it, not by reading it.
    """
    try:
        base = Path(os.environ.get("CLAUDE_PROJECT_DIR") or ".")
        ledger_dir = base.resolve() / ".claude" / ".session_state"
        ledger_dir.mkdir(parents=True, exist_ok=True)
        with open(ledger_dir / "subagent_gate.log", "a") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0

    # A worker that has already been blocked once and is being asked again would
    # otherwise loop on the same failure forever.
    if payload.get("stop_hook_active"):
        return 0

    source, root = _resolve_root(payload)
    stamp = datetime.now().isoformat(timespec="seconds")
    env_seen = os.environ.get("CLAUDE_PROJECT_DIR") or "(unset)"
    cwd_seen = payload.get("cwd") or "(absent)"

    if root is None:
        _log(f"{stamp}\tNO-SWEEP\tcwd={cwd_seen}\tenv={env_seen}\t"
             "no candidate tree carried scripts/qa_sweep.sh — fail-open")
        return 0

    # The tree the worker reported from, plus anywhere else it may actually have
    # worked. See _dirty_worktrees for why asking git beats being told.
    trees = [(source, root)]
    trees += [("dirty worktree", w) for w in _dirty_worktrees(root)]

    failures: list[tuple[Path, str]] = []
    for tree_source, tree in trees:
        try:
            proc = subprocess.run(
                ["bash", str(tree / "scripts" / "qa_sweep.sh")],
                cwd=str(tree),
                capture_output=True,
                text=True,
                timeout=SWEEP_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            # See the fail-open note above: the gate's own breakage must not
            # strand a worker's finished work.
            _log(f"{stamp}\tSWEEP-ERROR\troot={tree}\tvia={tree_source}\t"
                 f"cwd={cwd_seen}\tenv={env_seen}\t{type(exc).__name__}")
            continue

        _log(f"{stamp}\texit={proc.returncode}\troot={tree}\tvia={tree_source}\t"
             f"cwd={cwd_seen}\tenv={env_seen}")

        if proc.returncode != 0:
            failures.append((tree, (proc.stdout or "") + (proc.stderr or "")))

    if not failures:
        return 0

    detail = "\n".join(
        f"--- {tree} ---\n{text.strip()}" for tree, text in failures
    )
    if len(detail) > MAX_DETAIL_CHARS:
        detail = detail[:MAX_DETAIL_CHARS] + "\n… (truncated — run scripts/qa_sweep.sh for the rest)"

    reason = (
        "SUBAGENT GATE: scripts/qa_sweep.sh failed — you may not report done yet.\n\n"
        f"{detail}\n"
        "Each failure is labelled with the tree it came from. Fix what the sweep "
        "names. If a failure is pre-existing, or is in a tree you never touched — "
        "another window's worktree is swept too when it carries uncommitted work — "
        "say so explicitly in your report rather than silently leaving it. The "
        "coordinator needs to know which it is.\n\n"
        "Note: the sweep is a STATIC check. Passing it does not mean the change "
        "works; py_compile parses without executing. Run what you changed."
    )

    # decision/reason is what SubagentStop understands; the worker is handed the
    # reason and continues rather than stopping.
    print(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
