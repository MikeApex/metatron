#!/usr/bin/env python3
"""Test the claims `CLAUDE.md` and `.claude/settings.json` make about themselves.

`[DB-0809-11]` ("docs record values the system changes underneath them and
nothing checks") merged with `[H8].1` (permission-rule liveness), which the
harness backlog says to build as one thing. `deploy.sh`'s `EXPECTED_SHA`
assertion is the model: state the claim, then assert it.

**`[H8].1` could not be built as written, and the reason matters.** It specified
matching the string *"is not matched by file permission checks"* out of
`claude config list`. **There is no `config` subcommand** -- not in the native
install (2.1.226) nor the npm-global one (2.1.170) still on this machine. The
CLI parses `claude config list` as a *prompt* and spends a nested agent turn
answering it, which is how this was found: by running it. So the item's premise
was retired before it was ever built, and a check written to that spec would
have grepped an agent's prose for a string no tool emits -- passing forever.

The finding underneath it is untouched: `Write(path)` deny rules were silently
ignored while `Edit(path)` matched, leaving Tier 0 `constitution.md` reachable.
That was proven on a decoy probe, not by the string. So this script keeps the
goal (a script enforces the rule, not memory) and replaces the mechanism with a
static shape linter over `settings.json`, which needs no CLI at all.

Zero model tokens, stdlib only. Exit 1 on any failed claim.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Tools whose rules match file edits. `Edit(path)` covers every file-editing
# tool including Write; a `Write(path)` rule matches nothing and is worse than
# absent, because it reads as protection. Deleted from settings.json on
# 2026-08-13 -- this check is what stops the next well-intentioned re-add.
FILE_EDIT_TOOL = "Edit"
DEAD_FILE_TOOLS = ("Write", "MultiEdit", "NotebookEdit", "Update")

# Paths CLAUDE.md names that are **correctly absent on the Mac**. The VM owns
# live persona config: these are gitignored and deliberately not deployed, and
# a Mac copy is the exact thing that gets pushed by mistake. Flagging them
# would train the reader to ignore a report whose loudest finding is by design.
VM_ONLY_PREFIXES = ("config/personas/mike", "data/personas/")

failures: list[str] = []
checked = 0


def claim(description: str, ok: bool, detail: str = "") -> None:
    """Record one executable claim and whether it still holds."""
    global checked
    checked += 1
    if not ok:
        failures.append(f"{description}\n    {detail}" if detail else description)


# --- 1. Permission-rule liveness --------------------------------------------
# The class `[H8].1` exists to close: a rule that parses cleanly and then never
# matches anything.


def check_permissions() -> None:
    path = ROOT / ".claude" / "settings.json"
    try:
        settings = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        claim("`.claude/settings.json` parses", False, str(exc))
        return
    claim("`.claude/settings.json` parses", True)

    perms = settings.get("permissions") or {}
    rules = [
        (tier, rule)
        for tier in ("allow", "ask", "deny")
        for rule in (perms.get(tier) or [])
    ]

    # 1a. No file-edit rule uses a tool that does not match file edits.
    dead = [
        f"{tier}: {rule}"
        for tier, rule in rules
        if any(rule.startswith(f"{t}(") for t in DEAD_FILE_TOOLS)
    ]
    claim(
        f"no permission rule uses a non-matching file tool "
        f"({'/'.join(DEAD_FILE_TOOLS)} -- use {FILE_EDIT_TOOL})",
        not dead,
        "; ".join(dead),
    )

    # 1b. Every bare-executable Bash rule has a wildcard sibling.
    # `Bash(./deploy.sh)` was an exact-match rule, so `./deploy.sh --anything`
    # escaped the Red tier entirely. An exact rule on a bare executable is
    # legitimate only when a ` *` variant sits beside it covering arguments.
    #
    # **Scoped to bare executables (no spaces) deliberately.** The unscoped
    # version flagged `Bash(git checkout .)`, where the `.` *is* the argument
    # and a `git checkout . *` sibling would be meaningless -- the noise class
    # that teaches a reader to skip the report.
    bash_rules = {
        rule[len("Bash(") : -1]
        for tier, rule in rules
        if rule.startswith("Bash(") and rule.endswith(")")
    }
    unguarded = sorted(
        cmd
        for cmd in bash_rules
        if "*" not in cmd and " " not in cmd and f"{cmd} *" not in bash_rules
    )
    claim(
        "every exact Bash rule has a `<cmd> *` sibling covering its arguments",
        not unguarded,
        "; ".join(unguarded),
    )

    # 1c. Rules are well-formed `Tool(arg)` or a bare tool name. A typo'd rule
    # is the same silent no-op as a wrong tool.
    malformed = [
        f"{tier}: {rule}"
        for tier, rule in rules
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(\(.*\))?", rule)
    ]
    claim("every permission rule is well-formed", not malformed, "; ".join(malformed))

    # 1d. The Denied tier still covers what CLAUDE.md says it covers. These are
    # the paths the prose calls blocked; if one is dropped, the prose goes
    # stale silently and keeps being believed.
    required_deny = (
        "Edit(./config/constitution.md)",
        "Edit(./config/personas/mike.md)",
        "Edit(./data/personas/**)",
        "Read(./.env)",
    )
    deny = set(perms.get("deny") or [])
    missing = [r for r in required_deny if r not in deny]
    claim(
        "the Denied tier still covers constitution / mike persona / persona data / .env",
        not missing,
        "; ".join(missing),
    )


# --- 2. Hooks point at files that exist --------------------------------------
# A hook whose script is gone fails silently on every invocation. Found live:
# `.claude/show_phase_progress.py` reads `STATUS.md`, which has not existed for
# months, so that Stop hook has been a no-op for the life of the file.


def check_hooks() -> None:
    for name in ("settings.json", "settings.local.json"):
        path = ROOT / ".claude" / name
        if not path.exists():
            continue
        try:
            settings = json.loads(path.read_text())
        except ValueError as exc:
            claim(f"`.claude/{name}` parses", False, str(exc))
            continue

        for event, entries in (settings.get("hooks") or {}).items():
            for entry in entries:
                for hook in entry.get("hooks") or []:
                    command = hook.get("command", "")
                    match = re.search(r"([\w./$-]*\.(?:py|sh))", command)
                    if not match:
                        continue
                    target = match.group(1).strip('"')
                    target = target.replace("$CLAUDE_PROJECT_DIR", str(ROOT))
                    # Absolute and root-relative paths must both resolve, and
                    # an earlier version mangled the absolute case by stripping
                    # its leading slash -- reporting two live hooks as missing.
                    resolved = (
                        Path(target)
                        if target.startswith("/")
                        else ROOT / target.lstrip("./")
                    )
                    claim(
                        f"{name} {event} hook target `{target}` exists",
                        resolved.exists(),
                        f"referenced by {event} in .claude/{name}",
                    )


# --- 3. Paths CLAUDE.md names still exist ------------------------------------
# The doc-rot class. CLAUDE.md names scripts, modules and config files in
# backticks as if they are live; when one is renamed the prose keeps pointing
# at the old name and the next session follows it.


def check_named_paths() -> None:
    text = (ROOT / "CLAUDE.md").read_text()
    # Only paths with a directory component and a known code/config extension.
    # A bare `deploy.sh` in prose is ambiguous; `scripts/qa_sweep.sh` is not.
    candidates = set(
        re.findall(r"`([\w./-]+/[\w.-]+\.(?:py|sh|yaml|yml|md|json))`", text)
    )
    for rel in sorted(candidates):
        if "{" in rel or "*" in rel:
            continue  # a template like config/personas/{name}.md, not a path
        if re.search(r"YYYY|MM-DD|_MM\b", rel):
            continue  # a dated filename pattern, e.g. archive/backlog_closed_YYYY-MM.md
        if any(rel.startswith(p) for p in VM_ONLY_PREFIXES):
            continue  # see VM_ONLY_PREFIXES -- absent on the Mac by design
        claim(f"`{rel}` (named in CLAUDE.md) exists", (ROOT / rel).exists())


# --- 4. Line ceilings CLAUDE.md states ---------------------------------------
# The ceilings are stated as numbers in prose, which is exactly the
# short-half-life value `[DB-0809-11]` is about. Assert them instead.
# Crossing one is a signal to move something out, not a build failure -- so
# these WARN rather than fail, matching how the prose describes them.

CEILINGS = {
    "CLAUDE.md": 250,
    "SESSION.md": 200,
    "DEV_BACKLOG.md": 450,
    ".claude/commands/archive.md": 100,
    ".claude/commands/backlog.md": 200,
}


def check_ceilings() -> list[str]:
    warnings = []
    for rel, ceiling in CEILINGS.items():
        path = ROOT / rel
        if not path.exists():
            continue
        lines = len(path.read_text().splitlines())
        if lines > ceiling:
            warnings.append(f"{rel}: {lines} lines, ceiling {ceiling}")
    warnings.extend(check_session_volatile())
    return warnings


# --- 4b. SESSION.md's volatile half ------------------------------------------
# The 200-line ceiling measures the wrong thing on its own. SESSION.md sat at
# 195-205 lines for twenty consecutive commits (08-10 -> 08-14) -- not stable,
# but pinned: every session paid to argue one line out so it could put one line
# in. The static sections are not what grows, so a whole-file number cannot say
# whether the primer is healthy or merely full.
#
# These headings are rewritten or re-decided every session; everything else is
# reference that should be read on demand. A heading that disappears is not an
# error -- the budget is only ever advisory.

SESSION_VOLATILE_HEADINGS = ("## Current state", "## Recent sessions")

# Set to 120 on 2026-08-14, just above the 105 measured immediately after the
# dedup pass that introduced this check. Deliberately NOT set to the measured
# value: a budget that warns on the day it ships is one a reader learns to skip,
# which is the failure mode that keeps check_agent_tools.py out of the quality
# stream. It should fire on real accumulation, not on arrival.
SESSION_VOLATILE_BUDGET = 120


def check_session_volatile() -> list[str]:
    path = ROOT / "SESSION.md"
    if not path.exists():
        return []
    lines = path.read_text().splitlines()

    # The handoff paragraph is everything above the first `---`, which is the
    # densest and most-rewritten part of the file.
    handoff = len(lines)
    for i, line in enumerate(lines):
        if line.strip() == "---":
            handoff = i
            break

    volatile = handoff
    in_section = False
    for line in lines:
        if line.startswith("## "):
            in_section = any(line.startswith(h) for h in SESSION_VOLATILE_HEADINGS)
        if in_section:
            volatile += 1

    if volatile > SESSION_VOLATILE_BUDGET:
        return [
            f"SESSION.md volatile sections: {volatile} lines "
            f"(handoff {handoff} + {'/'.join(SESSION_VOLATILE_HEADINGS)}), "
            f"budget {SESSION_VOLATILE_BUDGET} — move a section out, do not trim a sentence"
        ]
    return []


def main() -> int:
    check_permissions()
    check_hooks()
    check_named_paths()
    warnings = check_ceilings()

    if warnings:
        print("WARN — line ceilings crossed (move something out; not a failure):")
        for w in warnings:
            print(f"  {w}")
        print()

    if failures:
        print(f"claude-md-claims: {len(failures)} of {checked} claims FAILED\n")
        for f in failures:
            print(f"  ✗ {f}")
        return 1

    print(f"claude-md-claims: {checked}/{checked} claims hold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
