#!/usr/bin/env python3
"""PreToolUse deny-lift. Allows Write/Edit on Denied-tier paths ONLY while a
plan-scoped work order is in force.

**Why this exists (Mike, 2026-08-29).** Implementation phases of an approved plan
sometimes touch Denied-tier paths (e.g. `data/personas/**`). The alternative —
temporarily editing the deny list in `.claude/settings.json` — depends on someone
remembering to restore it, and a forgotten restore leaves the deny silently off.
This hook retires that alternative: **the settings deny list is never edited for
a phase.** Instead, at implementation start and with Mike's explicit approval,
the session writes `.claude/deny_lift.json` scoped to that plan, and this hook
returns `permissionDecision: allow` for exactly the listed paths until expiry.

**The lift is written only when Mike says yes**, at plan-implementation time.
A session may not write one on its own initiative — the ask is the gate.

**Self-limiting by construction:**
  - `NEVER_LIFT` paths are refused regardless of the lift file's contents —
    the standing Denied row (constitution, .env, keys, deploy.sh) plus this
    mechanism's own moving parts (settings.json, this script, the lift file),
    so a lift can never widen itself.
  - Expiry is mandatory and capped at MAX_LIFT_DAYS from `created`. An expired
    lift is deleted on sight, so the standing artifact cleans itself up.
  - No lift / invalid lift / no match -> exit silently, and the ordinary deny
    applies. Failing closed is the whole point; never guess.

**Probe before trusting (deploy.md rule):** hook-allow beating a settings deny
was designed from the docs, not measured. Probe in a fresh session (hooks are
snapshotted at session start): write a lift for `data/personas/probe_lift.txt`,
attempt the Write, record which way it went in `.claude/rules/deploy.md`, delete
both files. Until that probe is recorded, treat this mechanism as unverified.
"""
from __future__ import annotations

import fnmatch
import json
import sys
from datetime import date, timedelta
from pathlib import Path

LIFT_NAME = ".claude/deny_lift.json"
MAX_LIFT_DAYS = 7

# Refused regardless of what the lift file says. Keep in sync with the Denied
# row in .claude/settings.json — this list is the subset that is NEVER liftable
# by this mechanism (Mike, 2026-08-29), plus the mechanism's own parts.
NEVER_LIFT = (
    ".env",
    ".env.*",
    "vertex-key.json",
    "config/constitution.md",
    "deploy.sh",
    ".claude/settings.json",
    ".claude/settings.local.json",
    ".claude/deny_lift.json",
    "scripts/hook_deny_lift.py",
)


def _repo_root(target: Path) -> Path | None:
    """Resolve the repo root from the TARGET path (worktree-safe, same reasoning
    as hook_context_gate.py — CLAUDE_PROJECT_DIR is wrong for worktrees)."""
    for parent in [target] + list(target.parents):
        if (parent / ".claude").is_dir() or (parent / ".git").exists():
            return parent
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    raw = (payload.get("tool_input") or {}).get("file_path", "")
    if not raw:
        return 0
    target = Path(raw).expanduser().resolve()

    root = _repo_root(target)
    if root is None:
        return 0
    try:
        rel = target.relative_to(root).as_posix()
    except ValueError:
        return 0

    # The permanent floor: never liftable, no matter the lift file.
    for pat in NEVER_LIFT:
        if rel == pat or fnmatch.fnmatch(rel, pat):
            return 0

    lift_path = root / LIFT_NAME
    if not lift_path.exists():
        return 0
    try:
        lift = json.loads(lift_path.read_text())
        plan = str(lift["plan"])
        created = date.fromisoformat(str(lift["created"]))
        expires = date.fromisoformat(str(lift["expires"]))
        paths = list(lift["paths"])
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        print(f"deny-lift: {LIFT_NAME} is malformed — ignoring it; the deny "
              f"applies as normal.", file=sys.stderr)
        return 0

    today = date.today()
    if today > expires:
        lift_path.unlink(missing_ok=True)
        print(f"deny-lift: lift for '{plan}' expired {expires} — deleted; the "
              f"deny applies as normal.", file=sys.stderr)
        return 0
    if expires > created + timedelta(days=MAX_LIFT_DAYS):
        print(f"deny-lift: lift for '{plan}' claims expiry {expires}, more than "
              f"{MAX_LIFT_DAYS} days past created {created} — ignoring it.",
              file=sys.stderr)
        return 0

    if not any(rel == p or fnmatch.fnmatch(rel, p) for p in paths):
        return 0

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": (
                f"deny-lift: plan '{plan}' (approved by Mike, expires "
                f"{expires}) covers {rel}"
            ),
        }
    }))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # a broken gate must fail CLOSED (no allow), not crash the tool call
        print(f"deny-lift: hook error ({exc}) — no lift applied.", file=sys.stderr)
        sys.exit(0)
