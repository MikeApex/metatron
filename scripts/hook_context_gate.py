#!/usr/bin/env python3
"""PreToolUse gate. A per-file briefing, plus two warn-only session checks.

**The briefing (added 2026-08-14).** For the specific file about to be written,
emit what this project already knows about it: its recent commits, the decision
history in `archive/log/`, any open `DEV_BACKLOG.md` item naming it, its
permission tier, and the area whose rules govern it. That survey — "what do I
already know about this exact file?" — is precisely the one thin-context edits
skip, and a hook is deterministic where prose in `CLAUDE.md` is advisory. It
costs zero tokens on every session that never touches the file.

The governing-area line is emitted **always**, including for files with no
history, because it is the part that must survive `/compact`: path-scoped rules
are not re-injected afterwards, so a session that read the rules early, compacted,
and edits late has lost them with no second chance.

**Root is resolved from the target path, not `CLAUDE_PROJECT_DIR`.** A worktree at
`../metatron-wt-<slug>` is outside the main tree, so the old `relative_to()` check
returned None and every worktree edit bypassed this gate entirely — meaning
`/backlog attack` workers, the thinnest-context sessions by construction, got no
gate at all. The design goal was inverted for its hardest case.

Two session-level checks, both once per session, kept from the original:

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

import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REQUIRED = ("SESSION.md", "ROADMAP.md")

# Editing these needs no project context — they are notes, not the system.
EXEMPT_DIRS = ("archive/", "tests/fixtures/", ".claude/plans/", "scratchpad/")
EXEMPT_NAMES = ("dummy", ".dev_backlog_seen")

# Documented `additionalContext` cap is 10,000 chars. Stay clear of it: going over
# truncates somewhere arbitrary, which would cut a section mid-sentence.
CAP = 9_500

MAX_COMMITS = 5
MAX_HISTORY = 5          # distinct log headings
EXCERPT_LINES = 5
MAX_BACKLOG = 4

HISTORY_HEADER = ("DECISION HISTORY (archive/log/, newest first — one excerpt per "
                  "session; open the log for the rest):")

# Basenames too common to search the log for on their own — a hit on "utils.py"
# says nothing about the file in front of you. The full relative path is always
# searched regardless.
_GENERIC_BASENAMES = {
    "__init__.py", "README.md", "utils.py", "config.py", "main.py",
    "index.html", "settings.json", "conftest.py", "types.py",
}

# Which area's rules govern a path, and where those rules live *today*.
#
# Phase 3 of the context-system plan would move these into `.claude/rules/*.md`
# with `paths:` frontmatter; it is deferred, and that directory does not exist.
# Naming a file that has never existed is the `config/frameworks.md` failure this
# project already documents, so these point at the live `CLAUDE.md` sections. If
# a `.claude/rules/` file ever claims the path, `_rule_file_for()` finds it and it
# is named alongside.
GOVERNED = (
    (("config/agents/*.md", "config/modules/routing*.yaml", "config/modules/routing*.yml"),
     "agent files and tool grants",
     "CLAUDE.md § 'A tool named in an agent file is a specification' and § One Home "
     "Per Rule Class. A tool named in an agent file is a spec: build it, grant it, or "
     "move it under a deferred heading — deleting the line is the last resort. "
     "scripts/check_agent_tools.py runs automatically after this edit."),

    (("config/constitution.md",),
     "the Tool Constitution (Tier 0)",
     "CLAUDE.md § Four-Tier Goal Hierarchy. Tier 0, shared by every persona, and "
     "Denied in .claude/settings.json — never edited without explicit instruction."),

    (("config/personas/*", "config/personas/**", "core/persona.py"),
     "personas and identity resolution",
     "CLAUDE.md § Personas. The VM owns live persona config — the Mac copy is stale by "
     "construction and pushing it erases what the running system wrote. Identity "
     "resolution is fail-closed; never read METATRON_PERSONA directly."),

    (("core/*.py", "core/**"),
     "the runtime harness",
     "CLAUDE.md § Security Architecture and § Key Design Decisions. core/orchestrator.py "
     "carries the A8 module-split refactor — check whether pending work relocates this "
     "code before adding to it. Behaviour changes belong in config/, not core/."),

    (("tools/*.py", "tools/**"),
     "MCP tool implementations",
     "docs/CONVENTIONS.md § the tool pattern. Sensitive-data routing is enforced here, "
     "in Python — never in prompts."),

    (("scripts/*", "scripts/**", "deploy.sh", ".claude/settings.json", ".claude/hooks/**"),
     "deploy and harness scripts",
     "CLAUDE.md § Deploy safety — four rules bought with real incidents. py_compile cannot "
     "catch a NameError; config never ships before the code that gates it; daemon-reload "
     "before the deploy; git diff every file before staging it."),

    (("CLAUDE.md", "SESSION.md", "ROADMAP.md", "DEV_BACKLOG.md",
      "CODEBASE_INDEX.md", ".claude/commands/*.md"),
     "project records",
     "CLAUDE.md § Which File Holds What. PROJECT_LOG.md is appended and SESSION.md is "
     "replaced; history in the primer is the failure this split exists to prevent. Each "
     "of these files has a line ceiling — see CEILINGS in scripts/check_claude_md_claims.py."),

    (("config/modules/*.yaml", "config/modules/*.yml"),
     "module configuration",
     "CLAUDE.md § Which File Holds What — config/ is the product. docs/CONVENTIONS.md "
     "covers adding a module."),

    (("tests/*", "tests/**"),
     "tests",
     "docs/CONVENTIONS.md § phase review and testing conventions. Domains with named "
     "hard-fail criteria (Finance arithmetic, Mental Wellbeing clinical flags) have a "
     "designated validation path — new tooling goes through it, not around it."),
)


# --- session / file markers ---------------------------------------------------

def _already_warned(session_id: str, root: Path, kind: str = "context_gate") -> bool:
    """Once per session per check. Returns True if we've already fired."""
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


def _briefed(session_id: str, root: Path, rel: str) -> bool:
    """Once per *file* per session — a session editing five files gets five briefings.

    Hashed because a relative path contains separators and would otherwise create
    directories under .session_state.
    """
    digest = hashlib.sha1(rel.encode()).hexdigest()[:16]
    return _already_warned(session_id, root, f"brief.{digest}")


# --- repo resolution ----------------------------------------------------------

def _git(root: Path, *args: str, timeout: int = 8) -> str:
    try:
        out = subprocess.run(["git", "-C", str(root), *args],
                             capture_output=True, text=True, timeout=timeout)
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def _common_dir(where: Path):
    """The shared `.git` directory for `where`'s repo, or None.

    Every worktree of a repository reports the *main* tree's git dir here, which
    is what makes it a reliable identity for "same repository, any tree".
    """
    out = _git(where, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if not out:
        return None
    try:
        return Path(out).resolve()
    except OSError:
        return None


def _repo_root(target: Path):
    """The git root containing `target`, if it belongs to *this* repository.

    Resolved from the target path so worktrees are covered. Membership is checked
    via `--git-common-dir` — an unrelated repo on the same machine is correctly
    not our business.

    Two anchors are accepted: where this script lives, and `CLAUDE_PROJECT_DIR`.
    Either alone is a single point of failure — the script can be invoked from
    outside the tree, and the env var can be absent or point elsewhere — and the
    check only needs one of them to establish identity.
    """
    start = target.parent
    while not start.exists() and start != start.parent:
        start = start.parent          # a Write to a new file in a new directory
    if not start.exists():
        return None

    root = _git(start, "rev-parse", "--show-toplevel")
    if not root:
        return None
    root_path = Path(root).resolve()

    theirs = _common_dir(root_path)
    if theirs is None:
        return None

    anchors = [Path(__file__).resolve().parent.parent]
    env_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_dir:
        anchors.append(Path(env_dir))
    for anchor in anchors:
        try:
            if anchor.exists() and _common_dir(anchor) == theirs:
                return root_path
        except OSError:
            continue
    return None


# --- briefing sections --------------------------------------------------------

def _commits(root: Path, rel: str) -> list[str]:
    out = _git(root, "log", f"-{MAX_COMMITS}", "--format=%ad %s", "--date=short", "--", rel)
    return [ln for ln in out.splitlines() if ln.strip()]


def _search_terms(rel: str) -> list[str]:
    terms = [rel]
    base = os.path.basename(rel)
    if base != rel and base not in _GENERIC_BASENAMES:
        terms.append(base)
    return terms


def _log_hits(root: Path, rel: str) -> list[tuple[str, str, list[str]]]:
    """(source, heading, excerpt-lines) from archive/log/, newest first.

    Fragments are searched before `_history.md` because they are the recent
    sessions; `_history.md` is itself newest-first. One excerpt per heading —
    the heading is the session, and one pointer per session is the useful
    granularity. This is a pointer into the log, not a substitute for reading it.
    """
    log_dir = root / "archive" / "log"
    if not log_dir.is_dir():
        return []

    fragments = sorted((p for p in log_dir.glob("*.md") if not p.name.startswith("_")),
                       reverse=True)
    blob = log_dir / "_history.md"
    sources = fragments + ([blob] if blob.exists() else [])

    terms = _search_terms(rel)
    hits: list[tuple[str, str, list[str]]] = []
    seen_headings: set[tuple[str, str]] = set()

    for src in sources:
        try:
            lines = src.read_text(errors="ignore").splitlines()
        except OSError:
            continue
        for n, line in enumerate(lines):
            if not any(t in line for t in terms):
                continue
            heading = ""
            for i in range(n, -1, -1):
                if lines[i].startswith("### "):
                    heading = lines[i][4:].strip()
                    break
            key = (src.name, heading)
            if key in seen_headings:
                continue
            seen_headings.add(key)
            excerpt = [ln.rstrip() for ln in lines[n:n + EXCERPT_LINES]]
            while excerpt and not excerpt[-1]:
                excerpt.pop()
            hits.append((src.name, heading or "(no heading)", excerpt))
            if len(hits) >= MAX_HISTORY:
                return hits
    return hits


_ITEM_RE = re.compile(r"\[(DB-\d{4}-\d{2})\]")


def _backlog_items(root: Path, rel: str) -> list[str]:
    """Open `## Now` / `## Later` items naming the file. Closed items are elsewhere."""
    path = root / "DEV_BACKLOG.md"
    try:
        lines = path.read_text(errors="ignore").splitlines()
    except OSError:
        return []

    terms = _search_terms(rel)
    out: list[str] = []
    section, item, matched = "", [], False

    def flush():
        nonlocal item, matched
        if matched and item:
            first = item[0].lstrip("- ").strip()
            m = _ITEM_RE.search(" ".join(item))
            tag = m.group(1) if m else "?"
            out.append(f"[{section}] {tag} — {first[:150]}")
        item, matched = [], False

    for line in lines:
        if line.startswith("## "):
            flush()
            section = line[3:].strip()
            continue
        if section not in ("Now", "Later"):
            continue
        if line.startswith("- "):
            flush()
            item = [line]
            matched = any(t in line for t in terms)
        elif item:
            item.append(line)
            if any(t in line for t in terms):
                matched = True
    flush()
    return out[:MAX_BACKLOG]


def _tier(root: Path, rel: str) -> str:
    """Red (ask) / Denied (deny) status for an Edit of this path.

    `.claude/settings.json` is the authority — CLAUDE.md's tier table says so
    explicitly, so this reads it rather than restating it.
    """
    try:
        with open(root / ".claude" / "settings.json") as fh:
            perms = (json.load(fh).get("permissions") or {})
    except (OSError, ValueError):
        return ""

    def hit(rules) -> bool:
        for rule in rules or []:
            if not isinstance(rule, str) or not rule.startswith("Edit("):
                continue
            pat = rule[len("Edit("):].rstrip(")").lstrip("./")
            # fnmatch's `*` crosses `/`, so `**` needs no special handling and a
            # single `*` is slightly over-broad. Over-broad errs toward warning.
            if fnmatch.fnmatch(rel, pat.replace("**", "*")):
                return True
        return False

    if hit(perms.get("deny")):
        return ("DENIED — .claude/settings.json blocks Edit on this path. It must be "
                "lifted explicitly; do not work around it.")
    if hit(perms.get("ask")):
        return "RED — .claude/settings.json prompts on every Edit to this path."
    return ""


def _rule_file_for(root: Path, rel: str) -> str:
    """A `.claude/rules/*.md` whose `paths:` frontmatter claims this path, if any.

    Nothing creates these yet (Phase 3 is deferred). This exists so the briefing
    starts naming them the moment they appear, rather than needing a second edit.
    """
    rules_dir = root / ".claude" / "rules"
    if not rules_dir.is_dir():
        return ""
    for rf in sorted(rules_dir.glob("*.md")):
        try:
            head = rf.read_text(errors="ignore").split("---")[1]
        except (OSError, IndexError):
            continue
        for line in head.splitlines():
            if not line.strip().startswith("paths:"):
                continue
            globs = line.split(":", 1)[1]
            for g in re.findall(r"[\w./*\-]+", globs):
                if fnmatch.fnmatch(rel, g.replace("**", "*")):
                    return f".claude/rules/{rf.name}"
    return ""


def _governing(root: Path, rel: str) -> str:
    for globs, area, where in GOVERNED:
        if any(fnmatch.fnmatch(rel, g.replace("**", "*")) for g in globs):
            rule_file = _rule_file_for(root, rel)
            prefix = f"{area} — governed by {rule_file}. " if rule_file else f"{area}. "
            return prefix + where
    return ""


# --- assembly -----------------------------------------------------------------

def _briefing(root: Path, rel: str, exists: bool) -> str:
    """The per-file survey. Sections are ordered newest/most-binding first, because
    truncation drops from the end — see `_fit()`."""
    blocks: list[str] = []

    tier = _tier(root, rel)
    if tier:
        blocks.append(f"TIER: {tier}")

    gov = _governing(root, rel)
    if gov:
        blocks.append(f"GOVERNED BY: {gov}")

    if not exists:
        blocks.append(
            "NEW FILE: this path does not exist yet, so it has no history. The rules "
            "for its area are above — read them before proceeding. A new file in a "
            "governed area is where those rules matter most.")
        return "\n\n".join(blocks)

    items = _backlog_items(root, rel)
    if items:
        blocks.append("OPEN BACKLOG ITEMS naming this file:\n"
                      + "\n".join(f"  · {i}" for i in items))

    commits = _commits(root, rel)
    if commits:
        blocks.append("RECENT COMMITS:\n" + "\n".join(f"  {c}" for c in commits))

    hits = _log_hits(root, rel)
    if hits:
        # Each excerpt is its own block so `_fit` can shed them one at a time,
        # oldest first. As a single block the whole history disappeared at once,
        # which is not "truncate oldest-first" — it is "lose all of it".
        blocks.append(HISTORY_HEADER)
        for src, heading, excerpt in hits:
            body = "\n".join(f"    {ln}" for ln in excerpt)
            blocks.append(f"  — {heading}  [{src}]\n{body}")
    elif commits:
        blocks.append("DECISION HISTORY: no archive/log/ entry names this file.")

    return "\n\n".join(blocks)


def _fit(header: str, body: str) -> str:
    """Keep the whole message under CAP, dropping the oldest material first.

    Blocks are ordered most-binding/newest first, so trimming from the end takes
    the oldest log excerpt before it takes the tier or the governing rules —
    those two are the parts that must survive.
    """
    blocks = [b for b in body.split("\n\n") if b]
    note = "  … older material truncated to fit the context cap."
    truncated = False

    def size() -> int:
        return len(header) + 2 + len("\n\n".join(blocks)) + (len(note) + 1 if truncated else 0)

    while blocks and size() > CAP:
        blocks.pop()
        truncated = True
        # Never leave the history header standing over nothing.
        if blocks and blocks[-1] == HISTORY_HEADER:
            blocks.pop()

    if not blocks:
        return header
    out = header + "\n\n" + "\n\n".join(blocks)
    if truncated:
        out += "\n" + note
    return out[:CAP]


# --- the two session checks ---------------------------------------------------

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


def _context_warning(payload: dict, root: Path, rel: str):
    """The pre-edit context check. None when it has nothing to say."""
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


# --- entry point --------------------------------------------------------------

def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0  # malformed input is never a reason to interfere with an edit

    target_raw = (payload.get("tool_input") or {}).get("file_path", "")
    if not target_raw:
        return 0
    target = Path(target_raw)
    if not target.is_absolute():
        target = (Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")) / target)
    try:
        target = target.resolve()
    except OSError:
        return 0

    root = _repo_root(target)
    if root is None:
        return 0  # outside this repository — not this gate's business
    try:
        rel = str(target.relative_to(root))
    except ValueError:
        return 0

    if os.path.basename(rel) in EXEMPT_NAMES:
        return 0
    if any(rel.startswith(d) for d in EXEMPT_DIRS):
        return 0

    session_id = payload.get("session_id", "unknown")

    # Both checks run every call and their notes are emitted together. An earlier
    # version returned after the mode warning, which meant a session making exactly
    # one edit under the fallback condition never got the context check at all —
    # the two are independent and must not consume each other.
    notes = []
    mode_note = _mode_warning(payload, root)
    if mode_note:
        notes.append(mode_note)

    context_note = _context_warning(payload, root, rel)
    if context_note:
        notes.append(context_note)

    briefing = ""
    if not _briefed(session_id, root, rel):
        briefing = _briefing(root, rel, target.exists())

    if not notes and not briefing:
        return 0

    header = "FILE BRIEFING — {rel}".format(rel=rel)
    if notes:
        header += "\n\n" + "\n\n".join(notes)
    message = _fit(header, briefing) if briefing else header
    return _emit(message)


def _emit(message: str) -> int:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": message,
        }
    }))
    print("WARN " + message, file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        # A briefing is never worth failing an edit over.
        sys.exit(0)
