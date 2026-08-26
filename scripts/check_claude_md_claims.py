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
    # `.claude/rules/*.md` are scanned too, from 2026-08-14. When the area rules
    # moved out of CLAUDE.md the claim count fell 36 -> 28: eight paths left
    # coverage along with the prose naming them. The doc-rot class did not move
    # with them -- it followed the text, so the check has to as well, or the
    # split would have quietly bought a smaller number by checking less.
    sources = [ROOT / "CLAUDE.md", *sorted((ROOT / ".claude" / "rules").glob("*.md"))]
    text = "\n".join(p.read_text() for p in sources if p.exists())
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
    # 250 -> 300 on 2026-08-14 (Mike's decision), with the .claude/rules/ split.
    #
    # Anthropic's stated target is 200 and the file landed at 279, NOT the ~180
    # the plan projected: the plan's own keep-list (infrastructure traps, change
    # tiers, terminology, four-tier hierarchy, privacy tiers, design decisions)
    # sums past 200 on its own, and that arithmetic was never done when the
    # target was set. Rather than delete safety-binding content to hit a number
    # -- the ratchet this project's conventions warn against -- the ceiling is
    # set at 300: a hard limit the file is genuinely under, with room to record
    # a new binding rule without the next session having to argue one out first.
    #
    # A ceiling the file permanently violates is the failure mode this codebase
    # documents repeatedly: a standing WARN teaches the reader to skip the
    # output, and then it catches nothing. 300 warns only on real regrowth.
    "CLAUDE.md": 300,
    "SESSION.md": 200,
    # DEV_BACKLOG.md is NOT here -- see ITEM_CEILINGS below. [DB-0810-06]
    # 100 -> 150 on 2026-08-15 (Mike's decision). The file had been over the
    # ceiling continuously since 08-13 (124, then 140, then 147) -- a standing
    # WARN nobody could clear, which is the same "teaches the reader to skip
    # the output" failure the CLAUDE.md note above describes. The five steps
    # plus the collision protocol do not fit in 100 lines; 150 is a limit the
    # file is actually under, so a future WARN means real regrowth.
    ".claude/commands/archive.md": 150,
    ".claude/commands/backlog.md": 200,
    # Path-scoped rule files (added 2026-08-14 with the directory itself).
    #
    # These do NOT load every session -- they inject in full when a file in
    # their area is read. That makes length cheaper than it is in CLAUDE.md,
    # but not free: when the rule fires, the whole file arrives, so a bloated
    # rule file recreates the adherence problem for exactly the sessions doing
    # the highest-stakes work in that area. An earlier draft of the plan said
    # these lines "cost nothing"; that was wrong, and this table is the fix.
    #
    # Each is set just above what the relocation actually measured, following
    # the SESSION_VOLATILE_BUDGET precedent below -- deliberately not set to
    # the measured value, which would make the next honest sentence a failure.
    # agent-files.md is the largest because it absorbed two whole rule classes
    # (the tool-specification rule and One Home Per Rule Class) plus the lifted
    # freeze; that is the merge, not creep.
    ".claude/rules/agent-files.md": 180,
    ".claude/rules/personas.md": 110,
    ".claude/rules/orchestrator.md": 90,
    ".claude/rules/deploy.md": 100,
    ".claude/rules/docs-and-logs.md": 150,
}

# --- 4a. The backlog is bounded by ITEMS, not lines --------------------------
# Mike, 2026-08-15 ([DB-0810-06]), raised while deciding a trim on a 922/450
# file: "a backlog's ceiling should probably be tied to the number of items in
# it, not its line count." Applied 2026-08-18.
#
# The two numbers answer different questions and only one of them is the one
# being asked. Item count is what bounds the WORKLOAD. Line count is what
# pressures a session to cut evidence out of well-documented entries -- and the
# evidence is the expensive half: the standing rule at the top of the file is
# that no item is acted on from its own description, which only works if the
# description carries what was checked and when.
#
# That pressure was measured, not theorised. A 2026-08-18 inventory found the
# growth was not new work arriving but finished work with no exit -- 11 of 43
# items built, deployed and waiting on one ordinary use each -- while every
# verifying sweep wrote MORE prose onto the items it checked. A line ceiling
# reads both of those as the same failure and prescribes trimming for both,
# which fixes neither.
#
# DEV_BACKLOG.md already half-agreed: `## Now`'s real cap has always been its
# 10-item limit, never a line count.
#
# 45 is set above the 2026-08-18 post-sweep count for the same reason every
# other ceiling here is set above its measurement -- a ceiling the file
# permanently violates teaches the reader to skip the output, and then it
# catches nothing.
ITEM_CEILINGS = {
    "DEV_BACKLOG.md": 45,
}


def _backlog_item_count(text: str) -> int:
    """`## Now` + `## Later` entries, counted the way sync_dev_backlog.py counts them.

    Imported rather than reimplemented: that function carries four paragraphs of
    history about the ways this count has been got wrong, and a second copy here
    would drift from it silently.
    """
    sys.path.insert(0, str(ROOT / "scripts"))
    from sync_dev_backlog import count_items

    _inbox, now, later = count_items(text)
    return now + later


def check_ceilings() -> list[str]:
    warnings = []
    for rel, ceiling in CEILINGS.items():
        path = ROOT / rel
        if not path.exists():
            continue
        lines = len(path.read_text().splitlines())
        if lines > ceiling:
            warnings.append(f"{rel}: {lines} lines, ceiling {ceiling}")
    for rel, ceiling in ITEM_CEILINGS.items():
        path = ROOT / rel
        if not path.exists():
            continue
        items = _backlog_item_count(path.read_text())
        if items > ceiling:
            warnings.append(f"{rel}: {items} open items, ceiling {ceiling}")
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

# "## Recent sessions" was removed from SESSION.md on 2026-08-26 — it duplicated
# archive/PROJECT_LOG.md. Left in this tuple deliberately: the check must keep measuring it so
# that recreating the section is caught by the budget rather than passing unnoticed.
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
