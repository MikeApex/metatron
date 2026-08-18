#!/usr/bin/env python3
"""
Report tools an agent file names that the agent cannot actually call.

Nothing checked this before 2026-08-10, which is how `web_search` survived in a
live instruction file. It does not exist anywhere in the codebase — zero hits in
`core/` and `tools/` — yet `research_agent.md` named it four times and made a
`SOURCES:` field mandatory on every response. An agent told to cite what it
retrieved, given no way to retrieve, and required to cite anyway, invents the
citations. It did, most confidently when the user challenged it.

That is the general shape and it is worth stating plainly: **an instruction that
names a capability the agent does not have is not inert.** The model does not
reply "I lack that tool" — it produces the *output shape* the instruction asks
for, sourced from nothing. Same class as the `logistics`/`write_agent_config`
case in .claude/rules/agent-files.md, where an agent merely *told* about a
tool could still call it because the dispatcher did not check.

**What a finding means, and what it does not.** These files are a specification
written ahead of the tools — deliberately. A named tool that does not exist is
evidence of *designed intent*, so the default response is **build it or grant
it**, and dropping the instruction is the last resort, not the first. This is the
same reading CLAUDE.md applies to `TOOL_DENIED` events. The defect in the
`web_search` case was never that the file aspired to web search; it was that the
aspiration sat in live instruction text with a mandatory-citation rule attached,
so the model filled the gap by inventing. Aspiration is fine. Aspiration the
model cannot distinguish from capability is not.

Four classes:

  0. **planned** — named under a heading that marks it unbuilt ("Phase 6 tools
     (deferred)", "Enhancement backlog", "Future"). Not a defect and never
     affects exit status. Listed so the roadmap stays visible rather than
     silently filtered — this is the build queue.

  1. **named-but-not-built** — named in *live* instruction text, not registered.
     The `web_search` failure. The model reads it as a present capability.
     Fix by building it, or by moving the line into a deferred section so it
     reads as a plan.

  2. **named-but-not-granted** — the tool exists, but the agent's `allowed_tools`
     whitelist omits it, so its schema is never advertised. The agent is told it
     can do something it cannot. Usually fixed by adding the grant. Three
     specialists were found in this state on 2026-08-10 for `search_memory`.

  3. **granted-but-never-named** — the agent holds a tool its instructions never
     mention. Often deliberate (a tool the harness calls on its behalf), so it is
     reported last. A large undocumented grant is worth a least-privilege look,
     not an alarm.

PERSONA FILES ARE SCANNED TOO (added 2026-08-18, `[DB-0810-03]`)
----------------------------------------------------------------
Until 2026-08-18 this script globbed `config/agents/*.md` and nothing else, so a
tool named in a *persona* file was invisible to it. That is not hypothetical:
commit `6913ad7` moved Mike's evening ritual — which instructs a `write_log`
call — out of `config/agents/synthesizer.md` into
`config/personas/mike/evening_ritual.md`. The `write_log` class-2 finding
disappeared from this report between two edits in one session, and **not because
it was fixed**: `synthesizer` still lacks the grant in `routing.yaml` and
`routing_cloud.yaml`, and the call only succeeds because `dispatch_tool()` runs
in warn mode rather than enforce. A guard that goes quiet when instruction text
moves house is worse than no guard, because the silence reads as a fix.

Reverting the move was the wrong fix — per-persona subject files are a pattern
ROADMAP.md § D2 actively encourages, so the blind spot widens with every new one.
The scan was extended instead: `config/personas/*.md` (identity) and
`config/personas/*/*.md` (prime_directive, mission, self_development,
evening_ritual, and whatever is added next) are read with the same evidence rules
as agent files, and globbed rather than enumerated so a new subject file is
covered on the day it is created.

**Attribution.** A persona file has no owning agent in the way an agent file
does, so findings are attributed to every agent that actually receives persona
*instruction* text in its system prompt. That set is read at runtime from
`core.orchestrator._HEAD_LAYER_AGENTS` — the agents routed through
`load_config()`, which is the only loader of persona markdown — rather than
hardcoded here, so adding an agent to the head layer extends this scan with it.
Specialists get `load_goals()` only (YAML data, not instruction text) and are
deliberately not attributed: reporting one persona-file defect against all 14
agents is the 34-false-positives-to-1-real-finding ratio this file's
`_tools_named_in` docstring exists to avoid.

**A zero-file scan is announced, never silent.** `config/personas/mike.md` and
`config/personas/mike/` are gitignored and VM-only (`.gitignore:134-135`), so a
Mac checkout or a worktree cannot see the real files. A clean report there proves
nothing about `mike`, and reporting "None." over an empty scan would reproduce
exactly the failure above. The header states how many persona files were read,
and says so loudly when the answer is zero.

Truth comes from `register_tools()` itself, called rather than parsed — a source
scan would drift from the registry the moment either changed shape.

Stdlib only, so it runs without the venv. Cheap enough to run as a `function:`
scheduler job at zero model tokens, like `daily_rule_audit`.

Usage
-----
    python3 scripts/check_agent_tools.py                 # both routing files
    python3 scripts/check_agent_tools.py --routing cloud # cloud only
    python3 scripts/check_agent_tools.py --agent research_agent
    python3 scripts/check_agent_tools.py --quiet         # findings only
    python3 scripts/check_agent_tools.py --no-personas   # agent files only
    python3 scripts/check_agent_tools.py --personas-root /tmp/fixture   # test hook

Exit status
-----------
    0  nothing named as live that is not built
    1  at least one class-1 finding

Classes 0, 2 and 3 never affect exit status. A planned tool is the build queue
working as intended; a not-granted tool is sometimes a deliberate staging state;
an undocumented grant is a judgement call. Only class 1 says the running system
is telling an agent something untrue about itself.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = ROOT / "config" / "agents"
PERSONAS_DIR = ROOT / "config" / "personas"

# A tool reference: a backticked lower_snake_case identifier, with or WITHOUT a
# call paren.
#
# Requiring the paren is the obvious design and it is wrong. Every one of the four
# `web_search` references in the pre-fix `research_agent.md` was written bare —
# "use `web_search` to cross-reference multiple sources" — so a paren-anchored
# pattern misses the exact defect this script exists to catch. It was written that
# way first, and the acceptance test caught it.
#
# The underscore does the work the paren was supposed to: it separates tool names
# from the prose terms these files backtick constantly (`quick`, `deep`,
# `intensive`). Flag names are uppercase and excluded by the character class.
_TOOL_REF_RE = re.compile(r'`([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\s*(\()?')

# Config keys, filenames and field names that are lower_snake_case but are not
# tools. Without this the report is mostly noise about YAML keys.
_NOT_TOOLS = {
    "allowed_tools", "local_enabled", "fallback_provider", "prime_directive",
    "deployment_mode", "interval_minutes", "medication_profile", "account_email",
    "tone_shape", "private_why", "shareable_what", "delay_minutes", "days_since_rain",
    "grounding_chunks", "web_search_queries", "quality_events", "clinical_threads",
    "disclosure_note", "fire_and_forget", "untrusted_content", "context_tracker",
    "max_iterations", "thought_signature", "system_prompt", "user_input",
    # Added 2026-08-13, when qa_sweep.sh made this script's exit code load-bearing
    # and these four were the entire reason it failed on a clean tree. All are the
    # bullet-leading JSON-key class this file's docstring already predicts:
    # open_threads / follow_ups / held_items are context-tracker FIELD DEFINITIONS
    # in synthesizer.md, and overdue_only is a PARAMETER of list_contacts() in
    # relationships.md. None is a tool; nothing was deleted from an agent file to
    # clear them, which would have been the wrong fix.
    "open_threads", "follow_ups", "held_items", "overdue_only",
}

# Headings under which a named tool is understood to be unbuilt. Matched against
# the nearest preceding markdown heading, case-insensitively.
_DEFERRED_HEADING_WORDS = ("deferred", "future", "enhancement backlog", "not yet built",
                           "phase 6", "phase 7", "backlog")

# A verb of invocation immediately before the reference — "use `web_search`",
# "call `run_subagent`". Evidence that the file is describing a capability rather
# than naming a field.
_INVOCATION_RE = re.compile(
    r'\b(?:use|uses|using|call|calls|calling|invoke|invokes|invoking|dispatch|'
    r'dispatches|run|runs|via|through)\s+(?:the\s+)?$', re.IGNORECASE)

# Everything before the reference is just list-item punctuation — "- ", "* ", "1. ",
# optionally bolded. This is how every tool inventory in these files is written, and
# it is the signal that survives when a tool is named without parens.
_BULLET_LEAD_RE = re.compile(r'^\s*(?:[-*+]|\d+\.)\s+(?:\*\*|__)?$')


@dataclass
class Ref:
    line: int
    called: bool
    is_tool_ref: bool


def _load_registered_tools() -> set[str]:
    """Tool names from register_tools() — the registry, not a guess at it."""
    sys.path.insert(0, str(ROOT))
    from core.orchestrator import register_tools
    schemas, handlers = register_tools()
    return {s["name"] for s in schemas} | set(handlers)


def _load_routing(which: str) -> dict[str, list[str] | None]:
    """agent -> allowed_tools (None = no whitelist = all tools advertised)."""
    import yaml
    name = "routing_cloud.yaml" if which == "cloud" else "routing.yaml"
    path = ROOT / "config" / "modules" / name
    if not path.exists():
        return {}
    cfg = yaml.safe_load(path.read_text()) or {}
    return {a: c.get("allowed_tools") if isinstance(c, dict) else None
            for a, c in (cfg.get("agents") or {}).items()}


# A bolded label used as a section marker, e.g. "**Phase 6 tools (deferred):**".
# These files mark unbuilt-tool sections this way as often as with a `#` heading,
# and looking only at `#` headings reported every deferred Phase 6 tool as a live
# defect — burying the one real finding under three known ones.
_BOLD_LABEL_RE = re.compile(r'^\s*(?:\*\*|__)(.+?)(?:\*\*|__)\s*:?\s*$')


def _heading_at(lines: list[str], idx: int) -> str:
    """Nearest section marker at or above line idx — `#` heading or bold label."""
    for i in range(idx, -1, -1):
        if lines[i].startswith("#"):
            return lines[i].lstrip("# ").strip()
        m = _BOLD_LABEL_RE.match(lines[i])
        if m:
            return m.group(1).strip()
    return ""


def _tools_named_in(path: Path) -> tuple[dict[str, "Ref"], dict[str, "Ref"]]:
    """(live, deferred) → tool name -> Ref(line, called, is_tool_ref).

    `is_tool_ref` is the important field and the reason this is not a simple regex
    sweep. These files are full of lower_snake_case backticked strings that are
    parameter names, JSON keys and flag placeholders — `agent_name`, `all_day`,
    `confirm_token`, `open_threads`. A first version reported 34 of them as missing
    tools alongside the 1 real finding, which is precisely the ratio that teaches a
    reader to skip the report. `rule_audit.py`'s docstring makes the same point about
    re-reporting: an audit nobody reads is not a control.

    So a name counts as a tool reference only on positive evidence, of which any one
    is enough:
      - written as a call, `web_search(...)`
      - leading a list item, which is how every tool inventory in these files is
        written: "- `read_log` — check recent financial entries"
      - preceded by a verb of invocation — "use `web_search`", "call `x`"

    And it is disqualified when followed by a colon, which marks an argument being
    assigned rather than a tool being named: `agent_name: "finance"`.

    Two signals were tried and dropped. "Appears under a heading containing 'tool'"
    matched every parameter name in the tool section's own prose — the descriptions
    of tools are not themselves tools. And the invocation verb alone let
    "Use `agent_name: ...`" through, which is what the colon rule now catches.

    All four pre-fix `web_search` references clear this bar; none of the 34 field
    names do. Evidence is required for class 1 only — classes 2 and 3 test against
    the registry, which cannot produce this kind of false positive.
    """
    lines = path.read_text().splitlines()
    live: dict[str, Ref] = {}
    deferred: dict[str, Ref] = {}
    for n, line in enumerate(lines):
        heading = _heading_at(lines, n).lower()
        deferred_here = any(w in heading for w in _DEFERRED_HEADING_WORDS)
        for m in _TOOL_REF_RE.finditer(line):
            tool = m.group(1)
            if tool in _NOT_TOOLS:
                continue
            called = bool(m.group(2))
            before = line[:m.start()]
            after = line[m.end():]
            assigned = after.lstrip("`").startswith(":")
            invoked = bool(_INVOCATION_RE.search(before))
            bullet_leading = bool(_BULLET_LEAD_RE.match(before))
            ref = Ref(line=n + 1, called=called,
                      is_tool_ref=(not assigned) and (called or bullet_leading or invoked))
            bucket = deferred if deferred_here else live
            prev = bucket.get(tool)
            # Keep the strongest evidence seen for a name, not merely the first.
            if prev is None or (ref.is_tool_ref and not prev.is_tool_ref):
                bucket[tool] = ref
    return live, deferred


def _ref(tool: str, called: bool) -> str:
    return f"`{tool}(...)`" if called else f"`{tool}`"


def _persona_files(personas_root: Path) -> list[Path]:
    """Every persona markdown file that reaches an agent's system prompt.

    Two shapes, both globbed rather than enumerated so a subject file type added
    tomorrow is covered without editing this script:
      config/personas/{name}.md      identity, loaded as "## User"
      config/personas/{name}/*.md    prime_directive, mission, self_development,
                                     evening_ritual, and whatever comes next

    goals.yaml is intentionally excluded — it is structured data reaching every
    agent, not instruction prose, and a tool name inside it would be a value, not
    an instruction.
    """
    if not personas_root.is_dir():
        return []
    return sorted(set(personas_root.glob("*.md")) | set(personas_root.glob("*/*.md")))


def _persona_reading_agents() -> tuple[set[str], str | None]:
    """Agents whose system prompt includes persona instruction text.

    Read from the orchestrator rather than hardcoded, so that adding an agent to
    the head layer extends this scan at the same time. Returns (agents, warning).
    """
    try:
        sys.path.insert(0, str(ROOT))
        from core.orchestrator import _HEAD_LAYER_AGENTS
        agents = set(_HEAD_LAYER_AGENTS)
        if not agents:
            return {"synthesizer"}, ("core.orchestrator._HEAD_LAYER_AGENTS is empty — "
                                     "falling back to {synthesizer}")
        return agents, None
    except Exception as exc:  # noqa: BLE001
        return {"synthesizer"}, (
            f"could not read core.orchestrator._HEAD_LAYER_AGENTS ({type(exc).__name__}: "
            f"{exc}) — falling back to {{synthesizer}}. If the head layer has changed, "
            f"persona findings below are attributed to the wrong agent."
        )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--routing", choices=["cloud", "local", "both"], default="both")
    ap.add_argument("--agent", help="check one agent only")
    ap.add_argument("--quiet", action="store_true", help="findings only, no clean lines")
    ap.add_argument("--no-personas", action="store_true",
                    help="skip config/personas/**.md (agent files only, pre-2026-08-18 behaviour)")
    ap.add_argument("--personas-root", default=None,
                    help="override the persona config root. Exists so the acceptance test "
                         "can point at a fixture: the real mike persona files are gitignored "
                         "and VM-only, so a Mac run cannot exercise this path otherwise.")
    args = ap.parse_args()

    registered = _load_registered_tools()
    routings = ["cloud", "local"] if args.routing == "both" else [args.routing]
    allowed_by_routing = {r: _load_routing(r) for r in routings}

    agent_files = sorted(AGENTS_DIR.glob("*.md"))
    if args.agent:
        agent_files = [f for f in agent_files if f.stem == args.agent]
        if not agent_files:
            print(f"No agent file for '{args.agent}'.")
            return 2

    # Persona files: one file, attributed to every agent that receives persona
    # instruction text. See the module docstring for why the attribution set is
    # read from the orchestrator rather than listed here.
    personas_root = Path(args.personas_root) if args.personas_root else PERSONAS_DIR
    persona_files: list[Path] = [] if args.no_personas else _persona_files(personas_root)
    persona_agents, attribution_warning = _persona_reading_agents()
    if args.agent:
        persona_agents = {a for a in persona_agents if a == args.agent}

    # (path, agent, display_label) — one entry per (file, owning agent) pair.
    scan: list[tuple[Path, str, str]] = [(f, f.stem, f"{f.stem}.md") for f in agent_files]
    for f in persona_files:
        label = str(f.relative_to(personas_root.parent)) if personas_root.parent in f.parents \
            else f.name
        for a in sorted(persona_agents):
            scan.append((f, a, f"{label} [{a}]"))

    nonexistent: list[tuple[str, str, int, bool]] = []
    not_granted: list[tuple[str, str, int, bool, str]] = []
    never_named: list[tuple[str, str, str]] = []
    planned: list[tuple[str, str, int]] = []
    named_by_agent: dict[str, set[str]] = {}

    print("=" * 72)
    print(f"Tool references in {len(agent_files)} agent file(s) and "
          f"{len(persona_files)} persona file(s) vs {len(registered)} registered tools")
    if args.no_personas:
        print("  persona scan: DISABLED by --no-personas")
    elif not persona_files:
        print("  ⚠ PERSONA SCAN READ ZERO FILES — this report says nothing about persona")
        print(f"    files. Looked in: {personas_root}")
        print("    config/personas/mike.md and config/personas/mike/ are gitignored and")
        print("    VM-only (.gitignore:134-135), so a Mac checkout or worktree cannot see")
        print("    them. Closing [DB-0810-03] needs one run on the VM. A clean result here")
        print("    is an empty scan, not a pass.")
    else:
        # Name the personas scanned, not just the count. On a Mac checkout the list
        # will not contain `mike` — his config is gitignored and VM-only — and a
        # reader who cannot see that omission will read this report as covering him.
        scanned = sorted({(f.parent.name if f.parent != personas_root else f.stem)
                          for f in persona_files})
        print(f"  persona scan: {len(persona_files)} file(s) under {personas_root}, "
              f"attributed to {', '.join(sorted(persona_agents)) or '(no agent)'}")
        print(f"    personas seen: {', '.join(scanned)}")
        if "mike" not in scanned:
            print("    ⚠ `mike` NOT among them — config/personas/mike{,.md} is gitignored")
            print("      and VM-only (.gitignore:134-135). This run does not cover the real")
            print("      user's persona files; only a VM run does.")
        if not persona_agents:
            print("  ⚠ no agent receives persona instruction text — findings will be dropped")
    if attribution_warning:
        print(f"  ⚠ {attribution_warning}")
    print("=" * 72 + "\n")

    for path, agent, label in scan:
        live, deferred = _tools_named_in(path)
        named_by_agent.setdefault(agent, set()).update(live)
        named_by_agent[agent].update(deferred)

        for tool, ref in sorted(live.items()):
            if tool not in registered:
                # Evidence gate: without it this class is 97% field names.
                if ref.is_tool_ref:
                    nonexistent.append((label, tool, ref.line, ref.called))
                continue
            for r in routings:
                allowed = allowed_by_routing[r].get(agent)
                if allowed is not None and tool not in allowed:
                    not_granted.append((label, tool, ref.line, ref.called, r))

        for tool, ref in sorted(deferred.items()):
            if tool not in registered:
                planned.append((label, tool, ref.line))

    # Class 3 is per-agent, not per-file: a grant documented in a persona file is
    # documented. Computing it inside the loop would report every head-layer grant
    # once per persona file scanned.
    for agent in sorted({a for _, a, _ in scan}):
        for r in routings:
            allowed = allowed_by_routing[r].get(agent)
            if not allowed:
                continue
            for tool in allowed:
                if tool not in named_by_agent.get(agent, set()):
                    never_named.append((agent, tool, r))

    print("-" * 72)
    print("0. PLANNED — named under a deferred/backlog heading. Not a defect: this is")
    print("   the build queue, shown so it stays visible rather than filtered away.")
    print("-" * 72)
    if planned:
        for label, tool, line in planned:
            print(f"  ○ {label}:{line}  `{tool}`  — specified, not built yet")
    elif not args.quiet:
        print("  None.")

    print("\n" + "-" * 72)
    print("1. NAMED AS LIVE BUT NOT BUILT — described in live instruction text, not")
    print("   registered. The model reads it as a present capability and fills the")
    print("   gap from nothing. Build it, or move the line to a deferred section.")
    print("-" * 72)
    if nonexistent:
        for label, tool, line, called in nonexistent:
            print(f"  ✗ {label}:{line}  {_ref(tool, called)}  — not in register_tools()")
    elif not args.quiet:
        print("  None.")

    print("\n" + "-" * 72)
    print("2. NAMED BUT NOT GRANTED — the tool exists, but this agent's allowed_tools")
    print("   omits it, so its schema is never advertised. Usually: add the grant.")
    print("-" * 72)
    if not_granted:
        for label, tool, line, called, r in not_granted:
            print(f"  ! {label}:{line}  {_ref(tool, called)}  — absent from allowed_tools ({r})")
    elif not args.quiet:
        print("  None.")

    print("\n" + "-" * 72)
    print("3. GRANTED BUT NEVER NAMED — held but undocumented. Often fine; worth a")
    print("   look under least-privilege if the grant is large.")
    print("-" * 72)
    if never_named:
        for agent, tool, r in never_named:
            print(f"  · {agent}  `{tool}`  — granted ({r}), not named in any file it loads")
    elif not args.quiet:
        print("  None.")

    print("\n" + "=" * 72)
    print(f"{len(planned)} planned, {len(nonexistent)} named-as-live-but-unbuilt, "
          f"{len(not_granted)} not-granted, {len(never_named)} undocumented "
          f"— across {len(agent_files)} agent and {len(persona_files)} persona file(s).")
    if not args.no_personas and not persona_files:
        print("Persona files: NONE READ. This run says nothing about them — see the")
        print("warning in the header. Re-run on the VM, where mike's are present.")
    if nonexistent:
        print("Class 1: build the tool, or move the line into a deferred section so")
        print("it reads as a plan. Deleting the instruction is the last resort — the")
        print("aspiration is the design record.")
    print("=" * 72)
    return 1 if nonexistent else 0


if __name__ == "__main__":
    raise SystemExit(main())
