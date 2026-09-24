"""
core/build/gates.py — what guards the output now.

Plan: archive/plans/build_vertical_plan_2026-09-24.md section 6.

The writer's LANDING job is gone with the overlay (ruling 4). Its CONTENT job
survives here, and so does its deny list — because path rules do not care who
writes (finding 3).

WHY THE DENY LIST IS STILL CODE, WHEN THE HARNESS HAS ONE. Two reasons, and
either alone would be enough:

  · THE HARNESS'S RULES ARE `./`-ANCHORED and do not reach `../metatron-wt-*`.
    The implementer works in a worktree. Every deny rule in
    .claude/settings.json is therefore inert for the exact session this gate
    exists to bound.
  · `git status` CANNOT SEE A GITIGNORED PATH, and the credentials and the
    persona trees are gitignored. A porcelain-only gate is blind to precisely
    the files whose protection matters most.

So the driver applies this list to the worktree through FOUR CHANNELS
(section 3 N12), and this module provides each one's primitive:

  (a) `git status --porcelain -uall` in the worktree — tracked and untracked.
      `-uall` because without it git collapses untracked files in a new
      directory to one `dir/` entry that matches neither `files[]` nor the deny
      list; the commit guard recorded that lesson and it cost a false park on
      the first capability that adds a package.
  (b) a recursive hash of an ENUMERATED list of deny-list paths inside the
      worktree, before N11 and after.
  (c) the same hash over the MAIN TREE's credential files and the main
      repository's `.git/hooks/`, `.git/config` and `.git/info/`.
  (d) the main tree's dirty-path set before and after — a relative-path write
      that missed the sandbox lands there.

NEVER A WILDCARD OVER `.claude/` (verify round 3). The harness's own hooks write
markers into `.claude/.session_state/` and `.claude/.session_edits/` on the
implementer's behalf, so a wildcard would refuse every build at its first edit.
The enumeration below names the five `.claude` entries that are actually denied
and nothing dot-prefixed.

THE SAME EXEMPTION IS NEEDED IN CHANNEL (a), AND ROUND 3 ONLY FIXED (b). A
marker is not in `files[]`, so channel (a)'s "every changed path is in the
implementer's half" rule refuses it on its own account — a different channel
reaching the identical wrong answer. In THIS repository `.gitignore` carries
`.claude/*`, so the porcelain never reports one and the hole is currently
invisible; that is an ignore rule holding up a security property, which is
exactly the kind of coupling that breaks silently when somebody tidies a
`.gitignore`. HARNESS_MARKERS below makes the exemption explicit, so channel
(a) is correct whether or not the ignore rule survives.

CHANNELS (b) AND (c) DETECT; THEY NEVER RESTORE (verify round 5). This module
holds no write path into `.git/`, the credential files or the persona trees, in
either tree. On a delta the driver refuses, names the paths, and stops. What to
do about a planted hook is Mike's hand, with the path in front of him.
"""

from __future__ import annotations

import fnmatch
import hashlib
import re
import subprocess
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent

_GIT_TIMEOUT = 20


class GateError(RuntimeError):
    """A gate could not be evaluated. NOT the same as a gate that refused."""


# ---------------------------------------------------------------------------
# The deny list — HARDCODED, salvaged verbatim from writer.py:189-209
# ---------------------------------------------------------------------------
#
# Every entry is either Tier 0, the VM's own identity, a Red-tier runtime path,
# or Build's own machinery. The last two matter most:
#
#   core/build/**             Build may not edit itself.
#   config/modules/build.yaml Build may not raise its own ceiling.
#
# Without those, the ceiling is config and anything that edits config can raise
# it. scripts/check_build_registration.py asserts this list still names them, so
# a later "simplification" fails the sweep rather than quietly widening the grant.

DENY_PREFIXES: tuple[str, ...] = (
    "config/personas/",
    "core/build/",
    ".git/",
)

DENY_EXACT: frozenset[str] = frozenset({
    "config/constitution.md",
    "deploy.sh",
    ".claude/settings.json",
    "core/router.py",
    "core/persona.py",
    "core/spend_guard.py",
    "core/scheduler.py",
    "config/modules/build.yaml",
})

DENY_GLOBS: tuple[str, ...] = (
    ".env*",
    "*/.env*",
    "*key*.json",
    "*/*key*.json",
)

# data/personas/** is denied outright now. Under v3 it carried a carve-out for
# the job directory and the overlay, both of which lived inside a persona tree;
# the job directory moved to data/build/ (section 5) and the overlay is retired,
# so the carve-out has nothing left to except and the rule is the simpler one.
_PERSONA_DATA_PREFIX = "data/personas/"

# WHAT CHANNEL (b) HASHES INSIDE THE WORKTREE. An enumerated list, never a
# wildcard — see the module header. `.git` is the pointer FILE a worktree
# carries, which is the one deny-list path no other channel can see: it points
# into the main repository's common directory, so a hook written through it runs
# under Mike's own commit at N13 (verify round 4).
WORKTREE_HASHED: tuple[str, ...] = (
    ".env",
    ".env.local",
    "vertex-key.json",
    "certs",
    "config/personas",
    "data/personas",
    ".claude/settings.json",
    ".claude/settings.local.json",
    ".claude/agents",
    ".claude/commands",
    ".claude/rules",
    ".git",
)

# WHAT CHANNEL (c) HASHES IN THE MAIN TREE. The credentials, as the belt in case
# a link-back exists that the --sandbox flag missed; and the main repository's
# hook path, which the sandbox flag CANNOT remove because a worktree cannot
# exist without its .git pointer.
MAIN_TREE_HASHED: tuple[str, ...] = (
    ".env",
    "vertex-key.json",
    "certs",
    ".claude/settings.json",
    ".claude/settings.local.json",
    ".git/hooks",
    ".git/config",
    ".git/info",
)


# Paths the HARNESS writes on the implementer's behalf. Exempt from channel
# (a)'s files[] rule and absent from channel (b)'s hash list — see the header.
# Everything dot-prefixed under .claude/ and nothing else: the five real
# .claude deny entries above are all undotted, so the two rules cannot overlap.
HARNESS_MARKERS: tuple[str, ...] = (
    ".claude/.session_state/",
    ".claude/.session_edits/",
)


def is_harness_marker(rel: str) -> bool:
    return str(rel or "").startswith(HARNESS_MARKERS)


def is_denied(rel: str) -> str:
    """The refusal reason for a repo-relative path, or "" when it is allowed."""
    rel = str(rel or "").strip()
    if not rel:
        return ""
    for prefix in DENY_PREFIXES:
        if rel.startswith(prefix):
            return f"deny list: {prefix}**"
    if rel in DENY_EXACT:
        return f"deny list: {rel}"
    for pattern in DENY_GLOBS:
        if fnmatch.fnmatch(rel, pattern):
            return f"deny list: {pattern}"
    if rel.startswith(_PERSONA_DATA_PREFIX):
        return f"deny list: {_PERSONA_DATA_PREFIX}**"
    return ""


# ---------------------------------------------------------------------------
# Channel (a) and (d) — the porcelain
# ---------------------------------------------------------------------------

def porcelain(tree: Path) -> list[str]:
    """
    Every changed path in `tree`, tracked and untracked, one entry per FILE.

    `-uall` is not optional (cold verify NEW 2). Without it git collapses the
    untracked files in a new directory into a single `dir/` entry, which matches
    neither a `files[]` path nor a deny-list pattern — so the first capability
    that adds a package (`tools/<cap>/__init__.py`) would park as `tools/<cap>/`
    while an actual escape into a new directory would go unseen.
    """
    proc = _git(tree, "status", "--porcelain", "-uall")
    out: list[str] = []
    for line in proc.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        # A rename reads "old -> new"; the new path is the one that exists.
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        out.append(path.strip('"'))
    return sorted(set(out))


def dirty_paths(tree: Path) -> set[str]:
    """Channel (d)'s snapshot of the MAIN tree, taken before and after N11."""
    return set(porcelain(tree))


def _git(tree: Path, *args: str) -> str:
    try:
        proc = subprocess.run(["git", *args], cwd=str(tree),
                              capture_output=True, text=True, timeout=_GIT_TIMEOUT)
    except (OSError, subprocess.SubprocessError) as exc:
        raise GateError(f"git {' '.join(args)} in {tree}: {exc}") from exc
    if proc.returncode != 0:
        raise GateError(f"git {' '.join(args)} in {tree}: {proc.stderr.strip()}")
    return proc.stdout


# ---------------------------------------------------------------------------
# Channels (b) and (c) — the hashes
# ---------------------------------------------------------------------------

def hash_paths(tree: Path, entries: tuple[str, ...]) -> dict[str, str]:
    """
    {entry -> digest} over an ENUMERATED list. Absent entries hash to "absent".

    "absent" is a real value, not a skip: a `--sandbox` worktree has no `.env`
    at all, and a later state where one EXISTS is exactly the delta this is
    watching for. Skipping absent entries would make creating a credential file
    invisible, which is the more dangerous direction.
    """
    out: dict[str, str] = {}
    for entry in entries:
        target = tree / entry
        if not target.exists():
            out[entry] = "absent"
        elif target.is_dir():
            out[entry] = _hash_dir(target)
        else:
            out[entry] = _hash_file(target)
    return out


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
    except OSError as exc:
        return f"unreadable:{type(exc).__name__}"
    return digest.hexdigest()


def _hash_dir(root: Path) -> str:
    """Recursive, name-and-content, sorted — so the digest is order-independent."""
    digest = hashlib.sha256()
    try:
        for path in sorted(root.rglob("*")):
            if path.is_dir():
                continue
            digest.update(str(path.relative_to(root)).encode("utf-8"))
            digest.update(_hash_file(path).encode("utf-8"))
    except OSError as exc:
        return f"unreadable:{type(exc).__name__}"
    return digest.hexdigest()


def hash_delta(before: dict[str, str], after: dict[str, str]) -> list[str]:
    """Entries whose digest moved. Empty is the healthy state."""
    return sorted(k for k in set(before) | set(after)
                  if before.get(k) != after.get(k))


# ---------------------------------------------------------------------------
# The four-channel verdict
# ---------------------------------------------------------------------------

def check_channels(worktree_before: dict[str, str], worktree_after: dict[str, str],
                   main_before: dict[str, str], main_after: dict[str, str],
                   worktree_changed: list[str],
                   main_dirty_before: set[str], main_dirty_after: set[str],
                   implementer_files: set[str]) -> tuple[list[str], list[str]]:
    """
    (refusals, notes). A non-empty refusal list parks the job.

    The asymmetry in channel (d) is deliberate and is the whole of cold read 4:
    a path newly dirty in the MAIN tree that is in the implementer's half of
    `files[]` is the signature of a relative-path write that missed the sandbox,
    and it refuses. Any OTHER newly dirty path is another chat's work in a tree
    two windows share — it is REPORTED beside the result and never refused,
    because the gate attributes by dirtiness and cannot tell whose fault it is.
    """
    refusals: list[str] = []
    notes: list[str] = []

    for entry in hash_delta(worktree_before, worktree_after):
        refusals.append(
            f"channel (b): {entry} changed inside the worktree — it is on the "
            "deny list, and git status cannot see it")

    for entry in hash_delta(main_before, main_after):
        refusals.append(
            f"channel (c): {entry} changed in the MAIN tree — nothing in a "
            "sandbox worktree has any business reaching it")

    for rel in worktree_changed:
        if is_harness_marker(rel):
            continue
        reason = is_denied(rel)
        if reason:
            refusals.append(f"channel (a): {rel} — {reason}")
        elif rel not in implementer_files:
            refusals.append(
                f"channel (a): {rel} is not in the implementer's half of "
                "files[] — the plan names every file, and this is not one")

    newly_dirty = main_dirty_after - main_dirty_before
    for rel in sorted(newly_dirty):
        if rel in implementer_files:
            refusals.append(
                f"channel (d): {rel} became dirty in the MAIN tree and is in "
                "files[] — a subagent's cwd stays pinned to the main tree, so "
                "this is a relative-path write that missed the sandbox")
        else:
            notes.append(
                f"channel (d): {rel} became dirty in the main tree while this "
                "job ran. Not in files[], so not Build's — reported, not refused")

    return refusals, notes


# ---------------------------------------------------------------------------
# Content gates — the writer's other half
# ---------------------------------------------------------------------------

# Letters, digits, spaces and an ampersand. Nothing else, because this string is
# spliced into the Coordinator's closed valid-name list — so a backtick, a quote
# or a newline in it rewrites the sentence the Coordinator is reading rather than
# merely looking odd. Underscores are refused too: a display name is a human
# string, and one that looks like an identifier invites exactly the confusion
# between the two names this separates.
_DISPLAY_NAME_RE = re.compile(r"^[A-Za-z0-9 &]+$")
_AGENT_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{2,31}$")


def _collapse(text: str) -> str:
    """
    The COMPARISON FORM of a display name: internal whitespace collapsed to one
    space, ends trimmed, case folded by the caller.

    `Mental  Wellbeing` passed every check it should have failed: it satisfies
    the charset, normalises to `mental__wellbeing` which is not a tracked agent,
    and lowercases to a string the reserved set does not contain — so it spliced
    into the closed valid-name list one space away from the real entry, on a
    model whose own map comment records that it cannot reliably copy that list.
    Every display-name comparison runs on this form.
    """
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _resolve_display(display: str) -> str:
    """The agent name a display string dispatches to, via the Coordinator's own map."""
    collapsed = _collapse(display)
    try:
        from core.orchestrator import normalize_agent_name
        return normalize_agent_name(collapsed)
    except Exception:
        return collapsed.lower().replace(" & ", "_").replace(" and ", "_") \
                        .replace(" ", "_")


def tracked_names() -> set[str]:
    """Agent names in EITHER routing file or config/agents/*.md — the three sets."""
    import yaml
    names = {p.stem for p in (_ROOT / "config" / "agents").glob("*.md")}
    for fname in ("routing.yaml", "routing_cloud.yaml"):
        path = _ROOT / "config" / "modules" / fname
        if path.exists():
            try:
                cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except Exception:
                continue
            names |= set((cfg.get("agents") or {}).keys())
    return names


def reserved_display_names() -> set[str]:
    """Display names the Coordinator already knows — its map and its closed list."""
    try:
        from core.orchestrator import _AGENT_NAME_MAP
        return set(_AGENT_NAME_MAP) | set(_AGENT_NAME_MAP.values())
    except Exception:
        return set()


def check_names(name: str, display_name: str,
                peers: dict[str, str] | None = None) -> list[str]:
    """
    The name-collision gate. `peers` is name -> display_name for other landed
    capabilities, so the SECOND generated capability cannot capture the first
    one's dispatch — the case the first version of this check missed.
    """
    defects: list[str] = []
    if not _AGENT_NAME_RE.match(str(name or "")):
        defects.append(f"name {name!r} must match {_AGENT_NAME_RE.pattern}")
    elif name in tracked_names():
        defects.append(
            f"name {name!r} is already a tracked agent — a generated capability "
            "may never shadow one")

    display = _collapse(display_name)
    if not _DISPLAY_NAME_RE.match(display):
        defects.append(
            f"display_name {display_name!r} must match "
            f"{_DISPLAY_NAME_RE.pattern} — it is spliced into a quoted item in "
            "the Coordinator's closed list, so punctuation rewrites the sentence")
        return defects

    lowered = display.casefold()
    resolved = _resolve_display(display)
    if resolved in tracked_names():
        defects.append(
            f"display_name {display_name!r} resolves to tracked agent "
            f"{resolved!r} — the Coordinator would dispatch that agent instead")
        return defects

    reserved = reserved_display_names()
    if lowered in {_collapse(r).casefold() for r in reserved} or resolved in reserved:
        defects.append(
            f"display_name {display_name!r} is already a name the Coordinator "
            "knows — it is in the name map or the closed valid-name list, or "
            "differs from one only by whitespace or case")
        return defects

    for peer_name, peer_display in (peers or {}).items():
        if peer_name == name:
            continue
        if _collapse(peer_display).casefold() == lowered:
            defects.append(
                f"display_name {display_name!r} duplicates the display name of "
                f"{peer_name!r} — the closed list would carry the same string "
                "twice and the name map would keep one winner, by sort order")
            return defects
        if resolved == peer_name:
            defects.append(
                f"display_name {display_name!r} resolves to {peer_name!r} — it "
                "would capture that capability's dispatch")
            return defects
    return defects


def registered_tools() -> set[str]:
    """Every handler name the live register_tools() provides."""
    try:
        from core.orchestrator import register_tools
        schemas, handlers = register_tools()
        return {s["name"] for s in schemas} | set(handlers)
    except Exception:
        return set()


def registered_names_in(text: str) -> set[str]:
    """Registered tool names appearing in `text` as BARE WORDS."""
    live = registered_tools()
    if not live:
        return set()
    words = set(re.findall(r"[a-z_][a-z0-9_]*", str(text or "").lower()))
    return words & live


def check_told_not_granted(agent_text: str, granted: list[str]) -> list[str]:
    """
    The agent file names no tool outside its grant.

    Bare-word scan against the LIVE register_tools() set, not against a list
    here — an allowlist that drifts behind the tool surface grants nothing while
    looking like it grants something, which is how a typo hides.
    """
    named = registered_names_in(agent_text)
    outside = sorted(named - set(granted or []))
    if not outside:
        return []
    return [
        f"the agent file names {tool!r}, which is not in its grant — an "
        "instruction to use a tool the agent does not have produces a silent "
        "refusal at the moment the user needs it"
        for tool in outside
    ]


def check_grants_declared(granted: list[str], read_set: set[str],
                          risks: list) -> list[str]:
    """
    Grants outside the read set are LISTED, not refused (section 6, softened).

    A refusal list was the right control for an UNATTENDED landing, which is
    what v3 had. Mike's approval at [N9] is the control now — so what this gate
    enforces is that he is actually shown the grant: a routing grant outside the
    read set that is absent from the plan's `risks[]` fails, because a risk
    nobody wrote down is a risk nobody approved.
    """
    risk_text = " ".join(str(r) for r in (risks or [])).lower()
    return [
        f"routing grants {tool!r}, which is outside the Librarian's read set, "
        "and no risks[] entry names it — the grant is fine, being unshown is not"
        for tool in sorted(set(granted or []) - set(read_set or set()))
        if tool.lower() not in risk_text
    ]


def check_record_fields(record: dict) -> list[str]:
    """
    `directory_entry`, `unavailable_consequence` and `display_name`, scanned for
    confidential identifiers against the LIVE registry.

    Scanned WHOLE, unlike an agent file where identifiers are checked only
    inside quoted spans. These three are short, and every one of them is prompt
    text the Coordinator or the Synthesizer reads — there is no legitimate
    reason for a tool name to appear anywhere in one. A record could otherwise
    carry the leak its agent file was refused for.
    """
    defects: list[str] = []
    fields = (
        ("display_name", record.get("display_name")),
        ("directory_entry", (record.get("coordinator") or {}).get("directory_entry")
         if isinstance(record.get("coordinator"), dict)
         else record.get("directory_entry")),
        ("unavailable_consequence", record.get("unavailable_consequence")),
    )
    try:
        from core.orchestrator import _ALWAYS_CONFIDENTIAL, _ARCH_NARRATION_RES
    except Exception:
        return ["the record narration gate could not load the live term lists"]

    for label, value in fields:
        text = str(value or "").strip()
        if not text:
            continue
        low = text.lower()
        leaked = next((t for t in _ALWAYS_CONFIDENTIAL if t in low), None)
        if not leaked:
            hits = registered_names_in(text)
            leaked = sorted(hits)[0] if hits else None
        if leaked:
            defects.append(
                f"{label} contains the confidential identifier {leaked!r} — this "
                "field is prompt text, so the leak ships with the capability")
            continue
        for pattern in _ARCH_NARRATION_RES:
            match = pattern.search(text)
            if match:
                defects.append(
                    f"{label} carries architecture narration ({match.group(0)!r})")
                break
    return defects

# ---------------------------------------------------------------------------
# The ceiling
# ---------------------------------------------------------------------------
#
# A HARDCODED FLOOR. config/modules/build.yaml may LOWER these, never raise
# them — a config that could raise the limit would be a ceiling Build's own
# output could argue its way past, and config/modules/build.yaml is on the deny
# list above for exactly that reason.
#
# Why the size limit is in code at all: six of six of Mike's 2026-08-21
# complaints were rules already written in synthesizer.md and ignored, while
# every rule moved to Python held on first contact. An agent file that grows
# without bound is an agent that stops following its own instructions.

MAX_AGENT_LINES = 220
REQUIRED_SECTIONS: tuple[str, ...] = ("Role", "Scope", "Output format",
                                      "Confidentiality")

_CONFIG_PATH = _ROOT / "config" / "modules" / "build.yaml"


def _config() -> dict:
    if not _CONFIG_PATH.exists():
        return {}
    try:
        import yaml
        return yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def max_agent_lines() -> int:
    """The configured limit, clamped to the hardcoded floor. Never above it."""
    value = (_config().get("agent_construction") or {}).get("max_lines")
    try:
        return min(int(value), MAX_AGENT_LINES)
    except (TypeError, ValueError):
        return MAX_AGENT_LINES


def required_sections() -> tuple[str, ...]:
    value = (_config().get("agent_construction") or {}).get("required_sections")
    if not isinstance(value, list) or not value:
        return REQUIRED_SECTIONS
    return tuple(str(v) for v in value)


def check_agent_text(text: str, granted: list[str] | None = None) -> list[str]:
    """
    The ceiling and the grant, over generated agent text. Returns defects.

    `Confidentiality` is the section that is a security control rather than a
    style rule: it is the INSTRUCTION-layer half of the two-layer architecture,
    and filter_output() is only the backstop. A generated agent without it
    narrates its own tooling.
    """
    defects: list[str] = []
    limit = max_agent_lines()
    lines = text.splitlines()
    if len(lines) > limit:
        defects.append(
            f"agent file is {len(lines)} lines, over the {limit}-line limit")
    headings = {line.lstrip("# ").strip().lower()
                for line in lines if line.startswith("#")}
    for section in required_sections():
        if section.lower() not in headings:
            defects.append(f"agent file has no '## {section}' section")

    if granted is not None:
        if not registered_tools():
            # FAIL CLOSED. A gate that cannot be evaluated is not a gate, and
            # this one guards a file that could otherwise name send_email.
            return defects + [
                "the tool-naming gate could not be run: register_tools() "
                "returned nothing"]
        defects.extend(check_told_not_granted(text, granted))
    return defects



# ---------------------------------------------------------------------------
# The tier gate — a standing judgement over a history is not bulk-tier work
# ---------------------------------------------------------------------------
#
# WHAT IT REFUSES. A capability whose plan reads a `kind: history` ledger row,
# or decides any `judgment` row, routed to the BULK tier in routing_cloud.yaml.
#
# WHY, AND WHAT IT IS NOT. It is not a privacy control: everything routes to
# Vertex Gemini under Mike's 2026-08-26 ruling and the `mike` persona is kept
# deliberately thin. The cost it guards is JUDGEMENT VARIANCE on a standing
# judgement over a history — and this project has that measured, not assumed.
# ROADMAP § D2 records `relationships`, on the bulk tier and commented "no
# clinical stakes", handed near-match evidence twice on the same class of case
# four minutes apart: it surfaced a duplicate, then asserted there was not one.
# Same model, same evidence, opposite answers.
#
# THAT IS VARIANCE, NOT A CEILING, WHICH IS WHY IT NEEDS A GATE AND NOT A TEST.
# A ceiling shows up on the first clean run; variance does not show up on any
# single run, so acceptance passing proves nothing about it. Only refusing the
# configuration can.
#
# AND IT IS RUN 1's OWN SHAPE. `home_care` — the plant-watering gap — is a
# last-done date derived from a log, which is exactly a standing judgement over
# a history. § 3 names the Coordinator's recorded failure on that request as
# doing the arithmetic itself from stale context. An under-tiered `home_care`
# reproduces the defect it was built to remove, with routing parity, the agent
# file, the registry row and the constitution check all green — one model name
# on one line the only thing wrong.
#
# WHAT THIS REPLACES. v3's constitution check asserted that an overlay record's
# `routing.cloud.model_ref` named a SENSITIVE tracked agent. § 8 retires
# `model_ref`, so that check went out with the overlay and nothing replaced it.
# This is narrower — it is about capability, not tier inheritance — and it is
# the half that has measured evidence behind it.
#
# ────────────────────────────────────────────────────────────────────────────
# DELIBERATELY NOT BUILT: THE LOCAL-MODE HALF. Mike's call, 2026-09-24.
#
# THE RULE THAT IS MISSING, stated so whoever returns local routing finds it:
# a generated `routing.yaml` entry that omits `local: true` would read personal
# data and route to Vertex in the one deployment mode whose entire point is
# that it does not. Parity checking cannot catch it — `check_build_registration`
# compares the two files' TOOL GRANTS, and the two files legitimately differ on
# provider, model and the `local` flag, so a missing flag reads as an ordinary
# difference.
#
# WHY IT IS NOT BUILT: `DEPLOYMENT_MODE=cloud`, Ollama is not in use, and
# everything routes through Gemini. An assertion about `routing.yaml`'s local
# flag today is a control for a path nobody runs, and a control nobody exercises
# is one that rots without anyone noticing.
#
# WHAT WOULD MAKE IT LIVE AGAIN: any return to `DEPLOYMENT_MODE=local`, or a
# second deployment that uses it. The assertion to add at that point is "a
# generated entry in routing.yaml whose plan reads any persona data carries
# `local: true`", beside the tier check below and run at the same N13 gate.
# ────────────────────────────────────────────────────────────────────────────

# Ledger-row kinds that make a capability's work a standing judgement.
#
# `history` because deriving a last-done date, a cadence or a running total
# from a log IS the judgement. `judgment` because the row says so itself — it
# carries decision_options and an assumption, which is the shape of a call
# somebody has to get right rather than a fact to look up.
JUDGEMENT_KINDS: frozenset[str] = frozenset({"history", "judgment"})


def _strip_model_prefix(model: str) -> str:
    """
    `models/gemini-3.5-flash-lite` and `gemini-3.5-flash-lite` are one model.

    AI Studio uses the `models/` prefix and Vertex drops it; the orchestrator
    strips it automatically when GOOGLE_CLOUD_PROJECT is set. Comparing the raw
    strings would make the gate depend on which spelling a routing file happened
    to use, which is a distinction with no meaning here.
    """
    return str(model or "").strip().removeprefix("models/")


def bulk_tier_model(routing_path: Path | None = None) -> str:
    """
    The bulk-tier model id, READ FROM THE ROUTING FILE'S OWN `quick_override`.

    NEVER A LITERAL, and this is the constraint that matters most in this
    function. Model ids in this project have a half-life of days — the
    reasoning tier moved 3.7 → 3.8 across six slots in three days in September
    2026 — and CLAUDE.md § Infrastructure traps names writing down a
    short-half-life value as its own defect class. A hardcoded id here would
    stop matching within the week and the gate would pass everything, silently,
    which is the worst way for a gate to fail.

    `quick_override` is the right anchor rather than a separate constant
    because it is what the RUNNING SYSTEM already means by "the fast tier":
    core/router.py resolves `complexity: quick` through it. So the gate and the
    router cannot disagree about which tier a model is on.

    Returns "" when it cannot be read, and the caller treats that as "cannot
    evaluate" rather than "not bulk".
    """
    path = routing_path or (_ROOT / "config" / "modules" / "routing_cloud.yaml")
    try:
        import yaml
        cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return ""
    return _strip_model_prefix((cfg.get("quick_override") or {}).get("model") or "")


def _entry_model(name: str, routing_path: Path | None = None) -> str:
    path = routing_path or (_ROOT / "config" / "modules" / "routing_cloud.yaml")
    try:
        import yaml
        cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return ""
    entry = (cfg.get("agents") or {}).get(name)
    if not isinstance(entry, dict):
        return ""
    return _strip_model_prefix(entry.get("model") or "")


def judgement_rows(plan: dict, ledger: dict) -> list[str]:
    """
    The ledger rows that make this capability a standing judgement.

    Two routes in, because they are different claims. A `judgment` row is one
    the capability DECIDES. A `history` row reached through
    `information_sources[]` is one it READS and then reasons over — and that
    second route is the one the plant-watering shape travels, where nothing in
    the plan says "judgement" anywhere.
    """
    by_id = {str(r.get("question_id")): r for r in (ledger.get("rows") or [])
             if isinstance(r, dict)}
    hits: list[str] = []

    for row in ledger.get("rows") or []:
        if isinstance(row, dict) and _text_kind(row) == "judgment":
            hits.append(f"{row.get('question_id')} (a judgment row it decides)")

    for source in plan.get("information_sources") or []:
        if not isinstance(source, dict):
            continue
        row = by_id.get(str(source.get("row_id")))
        if row is not None and _text_kind(row) == "history":
            hits.append(
                f"{source.get('row_id')} (a history it reads through "
                f"`{source.get('tool')}`)")
    return sorted(set(hits))


def _text_kind(row: dict) -> str:
    return str(row.get("kind") or "").strip().lower()


def check_tier(plan: dict, ledger: dict,
               routing_path: Path | None = None) -> list[str]:
    """
    RUN AT N13, NEVER N12 — the same reasoning as cold read 2.

    The routing entry is Red and is written by the main session AFTER the patch
    lands. At N12 the sandbox worktree holds no entry at all, so this gate would
    read "" for the model, find no match, and pass vacuously on every capability
    — a gate that always passes being strictly worse than no gate, because it
    reads as coverage.

    Returns defects. Empty means the tier is adequate, or the capability does no
    standing judgement, or the tier could not be resolved (which is reported as
    a defect in its own right rather than waved through).
    """
    name = str((plan.get("capability") or {}).get("id") or "")
    if not name:
        return ["the plan names no capability id, so its routing entry cannot be found"]

    reasons = judgement_rows(plan, ledger)
    if not reasons:
        return []

    bulk = bulk_tier_model(routing_path)
    if not bulk:
        # FAIL CLOSED. A gate that cannot be evaluated is not a gate, and this
        # one guards against a failure mode no test run can see.
        return ["the bulk tier could not be resolved from routing_cloud.yaml's "
                "`quick_override` — the tier gate cannot be evaluated, and a "
                "standing judgement is waiting on it"]

    entry = _entry_model(name, routing_path)
    if not entry:
        return [f"{name} has no entry in routing_cloud.yaml, so its tier cannot "
                "be checked — the wiring gate should have caught this first"]

    if entry != bulk:
        return []

    return [
        f"{name} routes to the BULK tier ({entry}) and does standing judgement "
        f"over: {'; '.join(reasons)}. That is judgement variance, not a ceiling "
        "— `relationships` on this tier gave opposite answers to the same class "
        "of evidence four minutes apart (ROADMAP § D2), and no single clean "
        "acceptance run can see it. Put it on the reasoning tier, or say in the "
        "plan's risks[] why this capability is the exception."
    ]
