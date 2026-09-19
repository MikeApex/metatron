"""
core/build/writer.py — the choke point. Everything Build writes goes through here.

`apply(job_id, plan, edits, dry_run=False)` and `revert(job_id)`. Refusals return
explanatory strings, never raise — house style, and the reason matters here: a
refusal is a normal outcome of a ceiling working, not an error condition.

THE RULE THE WHOLE DESIGN TURNS ON: **Build never writes a tracked file.**
Landing is an overlay. Generated capabilities live in a VM-owned, gitignored,
backed-up directory and the runtime loads them through four seams
(core/build/overlay.py). That holds MECHANICALLY rather than by convention —
rule (b) below refuses any path in `git ls-files`.

WHY THE OVERLAY LIVES UNDER data/personas/{p}/ AND NOT IN A NEW TOP-LEVEL DIR.
Three reasons, in order of weight:

  1. The compiled agent text is persona-derived — the ledger it is built from is
     drawn from the corpus — so it is Sensitive-tier content and belongs inside
     the persona tree, not in a global directory that happens to be gitignored.
  2. data/personas/*/ is already gitignored (.gitignore:148) and already inside
     scripts/metatron-backup.sh's tar list. The overlay therefore needs NO new
     ignore rule and NO new backup entry — two lists that could drift are two
     lists not added.
  3. The seams resolve the persona from thread scope.

config/personas/{p}/ was the reviewed alternative and was rejected only because
it sits on this file's own deny list.

WHAT THIS FILE IS NOT. It is not a policy engine and it does not decide what
SHOULD be built — the Planner does that. It decides what MAY be written, and it
answers that question the same way every time regardless of who is asking, which
is the only property that makes it a choke point rather than a suggestion.

Plan: archive/plans/build_vertical_plan_2026-09-18.md § 6
"""

from __future__ import annotations

import base64
import fnmatch
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent.parent


class WriterError(RuntimeError):
    """
    A gate could not be EVALUATED. Distinct from a refusal, which is an ordinary
    string return — this means the writer does not know the answer, and every
    caller treats not knowing as a refusal.
    """


# The git invocation, as a module global so a test can point it at a binary that
# does not exist and exercise the REAL refusal path rather than a stubbed one.
_GIT: list[str] = ["git", "ls-files", "-z"]
_GIT_TIMEOUT = 30


# ---------------------------------------------------------------------------
# 3. The grant ALLOWLIST — hardcoded, enumerated by grant, not by holder
# ---------------------------------------------------------------------------
#
# THIS IS THE WHOLE OF WHAT A GENERATED CAPABILITY MAY HOLD. A grant not below
# is refused at every ceiling whether or not anything names it as dangerous.
#
# It is an allowlist and not a deny list because a deny list cannot enclose a
# tool surface where the mutators are named for what they do rather than for the
# verb `write`. An earlier draft said "refuse every `write_*`" and these eight
# all fell straight through it: merge_contacts, unmerge_contacts,
# import_contacts_file, apply_crm_proposals, teach_intake, record_wisdom_response,
# log_interaction, create_semantic_anchor. Enumerating what is allowed fails
# closed as the tool surface grows; enumerating what is forbidden fails open.
#
# WHERE THE LINE SITS, stated as documentation and NOT as the mechanism: the
# refused set sends or moves the user's words, money or calendar (send_email,
# send_calendar_invite, write/update/delete_calendar_event), fetches arbitrary
# content (fetch_url, fetch_rendered), dispatches (run_subagent,
# run_model_conference), or rewrites standing state (write_agent_config,
# write_config, write_persona, write_schedule, open/close/reopen_obligation,
# record_horizon_item, write_goals, update_goal, and the eight above).

READ_SET: frozenset[str] = frozenset({
    # The corpus
    "read_log", "get_log_window", "read_journal", "search_memory", "read_wisdom",
    "read_goals", "read_archive",
    # Calendar and contacts — READ only; every mutator is refused
    "read_calendar", "check_calendar_conflicts",
    "read_contact", "list_contacts", "search_contacts",
    # Inbound and standing state, read side
    "read_email", "read_intake_queue", "list_obligations", "read_context_tracker",
    "read_profile", "read_agent_config", "read_recent_insights", "list_schedules",
    # The baseline readers. Deliberately the two literal readers and not
    # score_against_anchors / shuffled_null_score, which are analysis entry
    # points on the A5b path; granting one to a generated capability is a
    # decision somebody should make out loud, not an allowlist default.
    "read_baseline_periods", "get_baseline_context",
    # Six outbound feeds. They leave the machine, which is why they are named
    # individually rather than swept in: each carries no user-authored content
    # and no identifier beyond a city, line or flight number.
    "get_weather", "get_environmental_snapshot", "get_tfl_status",
    "get_flight_status", "get_travel_time", "get_regional_transit_info",
    # The SEVENTH outbound read, and the justification above does not cover it.
    # find_places sends a free-text query. Its own reason: the query is a place
    # description the capability composes from the request — the same exposure
    # `logistics` already carries under the ROADMAP.md Section 0 ruling — and it
    # is on the read side because it mutates nothing. A generated capability
    # that wants it must list it in the plan's risks[], which N8b reads and the
    # approval brief shows Mike.
    "find_places",
    # The two read tools plan Section 9 specifies and phase 6 builds. Named here
    # from day one on this project's own rule that a tool named in an agent file
    # is a SPECIFICATION. unregistered_grants() below reports them until they
    # land, so a typo in this set cannot hide among them.
    "search_conversations", "read_journal_range",
})

# Permitted, and the only writes that are: the Diarist path. These record what
# happened; they do not move anything in the user's world.
LOGGING_GRANTS: frozenset[str] = frozenset({
    "write_log", "write_journal", "write_quality_event",
})

ALLOWED_GRANTS: frozenset[str] = READ_SET | LOGGING_GRANTS

# Grants that are correct and not yet built. Anything else missing from the live
# register_tools() is a typo, and a typo in an allowlist grants nothing while
# looking like it grants something.
PENDING_GRANTS: frozenset[str] = frozenset({
    "search_conversations", "read_journal_range",
})


# GRANTS THAT CARRY A CONDITION. The allowlist says a tool MAY be held; these
# say what else must be true first.
#
# find_places is the seventh outbound read and the reason the blanket
# justification for the other six does not cover it: they send a city, a line or
# a flight number, and it sends a FREE-TEXT QUERY the capability composes from
# the request. The plan's answer was that a capability wanting it "must list it
# in risks[], which N8b reads and the brief shows Mike" — and nothing enforced
# that, so the one grant whose exposure depends on a human seeing it was handed
# out as silently as any other. The condition is now a refusal.
CONDITIONAL_GRANTS: dict[str, str] = {
    "find_places": (
        "sends a free-text query the capability composes off the machine, so the "
        "plan must name it in risks[] where the approval brief shows it to Mike"
    ),
}


def unregistered_grants() -> list[str]:
    """
    Allowlist names the live register_tools() does not provide, minus the two
    that are specified-but-unbuilt. Empty is the healthy state.

    Asserted by scripts/check_build_registration.py, so the allowlist tracks the
    tool surface as it grows instead of silently drifting behind it.
    """
    try:
        from core.orchestrator import register_tools
        schemas, handlers = register_tools()
        live = {s["name"] for s in schemas} | set(handlers)
    except Exception:
        return []
    return sorted((ALLOWED_GRANTS - PENDING_GRANTS) - live)


# ---------------------------------------------------------------------------
# 2(a). The deny list — HARDCODED
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

# data/personas/** is denied EXCEPT under this job's directory and the overlay
# and policies roots — which is the carve-out the allow-roots then re-state. The
# two rules are deliberately not merged: (a) is belt and (c) is braces, and a
# mistake in either leaves the other holding.
_PERSONA_DATA_PREFIX = "data/personas/"


# ---------------------------------------------------------------------------
# 4. The ceiling
# ---------------------------------------------------------------------------

_CONFIG_PATH = _ROOT / "config" / "modules" / "build.yaml"

# HARDCODED FLOOR. config/modules/build.yaml may LOWER this, never raise it.
MAX_AGENT_LINES = 220
REQUIRED_SECTIONS: tuple[str, ...] = ("Role", "Scope", "Output format", "Confidentiality")

# States in which a real write is allowed. dry_run is exempt: the Planner calls
# apply(dry_run=True) as its own file-path check, at plan time, and that call is
# the whole reason the validator and the enforcer cannot drift.
WRITABLE_STATES: frozenset[str] = frozenset({"briefed", "executing"})


def _config() -> dict:
    if not _CONFIG_PATH.exists():
        return {}
    try:
        import yaml
        return yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def may_create_agent_files() -> bool:
    return bool((_config().get("autonomy") or {}).get("may_create_agent_files", False))


def max_agent_lines() -> int:
    """The configured limit, clamped to the hardcoded floor. Never above it."""
    value = (_config().get("agent_construction") or {}).get("max_lines")
    try:
        configured = int(value)
    except (TypeError, ValueError):
        return MAX_AGENT_LINES
    return min(configured, MAX_AGENT_LINES)


def required_sections() -> tuple[str, ...]:
    value = (_config().get("agent_construction") or {}).get("required_sections")
    if not isinstance(value, list) or not value:
        return REQUIRED_SECTIONS
    return tuple(str(v) for v in value)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def allow_roots(job_id: str, persona: str | None = None) -> list[Path]:
    """
    The three directories a write may land in, and nowhere else.

    The plan calls these "two roots" — the job directory and the overlay tree —
    and lists policies/ as a third line beside them. Enumerated as three here
    because that is what the code has to check, and a comment is cheaper than a
    reader wondering which of two roots policies/ is inside.
    """
    from core.build import jobs as J
    return [
        J.job_dir(job_id, persona),
        J.build_dir(persona) / "overlay",
        J.build_dir(persona) / "policies",
    ]


def overlay_dir(persona: str | None = None) -> Path:
    from core.build import jobs as J
    return J.build_dir(persona) / "overlay"


def _rel(path: Path) -> str:
    """Repo-relative POSIX string when the path is inside the tree, else absolute."""
    try:
        return path.resolve().relative_to(_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _tracked_paths() -> set[str] | None:
    """
    Every path in `git ls-files`, or None when git could not be asked.

    None is NOT an empty set. A rule that cannot be evaluated is not a rule, so
    apply() refuses everything on None rather than treating "no tracked files"
    as "nothing is tracked".
    """
    try:
        proc = subprocess.run(_GIT, cwd=str(_ROOT), capture_output=True,
                              timeout=_GIT_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return {p for p in proc.stdout.decode("utf-8", "replace").split("\0") if p}


def _is_denied(rel: str, roots: list[Path]) -> str:
    """Rule (a). Returns the reason, or "" when the path is not on the deny list."""
    for prefix in DENY_PREFIXES:
        if rel.startswith(prefix):
            return f"deny list: {prefix}**"
    if rel in DENY_EXACT:
        return f"deny list: {rel}"
    for pattern in DENY_GLOBS:
        if fnmatch.fnmatch(rel, pattern):
            return f"deny list: {pattern}"
    if rel.startswith(_PERSONA_DATA_PREFIX):
        target = (_ROOT / rel).resolve()
        if not any(_within(target, root) for root in roots):
            return (f"deny list: {_PERSONA_DATA_PREFIX}** outside this job's "
                    "directory and the overlay/policies roots")
    return ""


def _within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def check_path(path: Path | str, job_id: str, persona: str | None = None,
               tracked: set[str] | None = None) -> str:
    """
    The three path rules, IN THIS ORDER. Returns "" when the path may be written,
    else the refusal reason.

    (a) the deny list          — hardcoded, above
    (b) anything git tracks    — the rule that makes "never a tracked file" hold
    (c) the allow-roots        — anything outside them is refused even if (a)
                                 and (b) pass

    (b) is belt and (c) is braces. Neither is redundant: (b) is what stops a new
    tracked file nobody thought to deny, and (c) is what stops an UNTRACKED file
    anywhere in the tree — a new script, a new config — which (b) cannot see.
    """
    target = Path(path)
    if not target.is_absolute():
        target = _ROOT / target
    rel = _rel(target)
    roots = allow_roots(job_id, persona)

    denied = _is_denied(rel, roots)
    if denied:
        return f"{rel}: refused by {denied}"

    if tracked is None:
        return (f"{rel}: refused — `git ls-files` could not be evaluated, and a "
                "rule that cannot be evaluated is not a rule")
    if rel in tracked:
        return (f"{rel}: refused — the path is tracked by git. Build never "
                "writes a tracked file; a capability reaches the tracked tree "
                "only through the promotion path, as a diff Mike commits")

    if not any(_within(target, root) for root in roots):
        return (f"{rel}: refused — outside the allow-roots "
                f"({', '.join(_rel(r) for r in roots)})")

    # THE JOURNAL IS NOT AN ARTIFACT. It sits inside the job directory, which is
    # an allow-root, so it read as ordinary writable space — and it is the one
    # file whose contents revert() treats as instructions. Anything able to write
    # it could name any path on the machine and have revert() act on it.
    # CASE-INSENSITIVELY, AND BY INODE WHERE THE FILE EXISTS. The rule was a
    # case-sensitive string test, and the development filesystem is
    # case-insensitive: `Undo.jsonl` passed it and is the SAME FILE as the
    # journal. revert() refuses paths outside the allow-roots now, so a forged
    # journal can no longer reach a tracked file — but it could still restore
    # arbitrary bytes into another capability's overlay agent file, bypassing
    # every content gate. The name test is what holds on ext4, where `Undo.jsonl`
    # really is a different file; the inode test is what holds on APFS.
    lowered = target.name.lower()
    if lowered.startswith("undo.") and lowered.endswith(".jsonl"):
        return (f"{rel}: refused — the undo journal is written only by the "
                "writer itself. It is the input revert() obeys, so a plan that "
                "could edit it could choose what revert() writes")
    journal = undo_path(job_id, persona)
    if target.exists() and journal.exists():
        try:
            if os.path.samefile(target, journal):
                return (f"{rel}: refused — it is the same file as the undo "
                        "journal on this filesystem, whatever it is named")
        except OSError:
            pass
    return ""


# ---------------------------------------------------------------------------
# 7. Staging and undo — the journal is the ONLY undo
# ---------------------------------------------------------------------------
#
# NEW MACHINERY WITH NO PRIOR ART, and flagged as such (plan Section 13.6). v2
# had a git worktree beside this; v3 removes it, so the journal must be tested
# harder rather than less — the sha256 round-trip in tests/test_build_writer.py
# runs over every file kind the writer produces.
#
# The journal itself is never journaled. It is append-only, fsynced per line,
# and written directly — recording it in itself is an infinite regress, and a
# revert that had to restore its own log first would have no log to read.

_UNDO_NAME = "undo.jsonl"


def undo_path(job_id: str, persona: str | None = None) -> Path:
    from core.build import jobs as J
    return J.job_dir(job_id, persona) / _UNDO_NAME


def _journal(job_id: str, target: Path, persona: str | None = None) -> None:
    """
    Record what `target` was before it is touched. Called before the first byte.

    `bytes_before` is base64 rather than text because a byte-identical restore
    is the guarantee, and a file this writer did not create may not be valid
    UTF-8. sha256_before is kept beside it so revert() can VERIFY the restore
    rather than assume it.
    """
    existed = target.exists()
    raw = target.read_bytes() if existed else b""
    entry = {
        "path": str(target),
        "rel": _rel(target),
        "existed": existed,
        "sha256_before": hashlib.sha256(raw).hexdigest() if existed else "",
        "size_before": len(raw),
        "bytes_before": base64.b64encode(raw).decode("ascii") if existed else "",
    }
    path = undo_path(job_id, persona)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _write_atomic(target: Path, content: str) -> None:
    """Temp file in the same directory, then os.replace(). Never a partial file."""
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(target.parent), prefix=target.name + ".",
                                    suffix=".tmp")
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        tmp.write_text(content, encoding="utf-8")
        os.chmod(tmp, 0o600)
        os.replace(tmp, target)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def revert(job_id: str, persona: str | None = None) -> str:
    """
    Undo everything this job wrote, in reverse order. Byte-identical or nothing.

    Called by three different outcomes and deliberately by all three: a [N13]
    refusal, a failing verification check, and `abandoned`. NOTHING IS EVER LEFT
    HALF-APPLIED — that is the property the whole landing design rests on, and
    it is why a failed check reverts before the node returns rather than leaving
    the overlay for someone to tidy.

    The journal is renamed rather than deleted once replayed, so a second revert
    is a no-op and the record of what was undone survives for the board.
    """
    path = undo_path(job_id, persona)
    if not path.exists():
        return f"{job_id}: nothing to revert — no undo journal"

    entries: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            # A torn final line is the crash this exists for. Skipping it loses
            # the LAST write, which is also the one most likely never to have
            # happened — the journal is written before the bytes.
            continue
        if isinstance(entry, dict):
            entries.append(entry)

    # THE SAME THREE RULES apply() USES, BEFORE ANYTHING IS RESTORED.
    #
    # revert() was a write primitive with NO path rules: it replayed whatever the
    # journal named. The journal is a file, inside an allow-root, and its entries
    # are paths — so the undo mechanism was a way around the deny list, the
    # tracked-path rule and the allow-roots at once. An entry that would not pass
    # apply() is logged and skipped, never replayed.
    #
    # Fail-closed when git cannot be asked: check_path() refuses everything, so a
    # revert that cannot verify its paths does nothing and says so. Leaving an
    # overlay half-applied is recoverable; writing an unchecked path is not.
    tracked = _tracked_paths()
    restored, removed, failed, skipped = 0, 0, [], []
    for entry in reversed(entries):
        target = Path(entry.get("path", ""))
        why = check_path(target, job_id, persona, tracked)
        if why:
            skipped.append(why)
            continue
        if not entry.get("existed"):
            if target.exists():
                try:
                    target.unlink()
                    removed += 1
                except OSError as exc:
                    failed.append(f"{_rel(target)}: {exc}")
            continue
        try:
            raw = base64.b64decode(entry.get("bytes_before") or "")
        except Exception:
            failed.append(f"{_rel(target)}: undo entry is not decodable")
            continue
        digest = hashlib.sha256(raw).hexdigest()
        if digest != entry.get("sha256_before"):
            failed.append(f"{_rel(target)}: undo entry fails its own checksum")
            continue
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(dir=str(target.parent),
                                            prefix=target.name + ".", suffix=".tmp")
            os.close(fd)
            tmp = Path(tmp_name)
            tmp.write_bytes(raw)
            os.chmod(tmp, 0o600)
            os.replace(tmp, target)
            restored += 1
        except OSError as exc:
            failed.append(f"{_rel(target)}: {exc}")

    if not failed and not skipped:
        from datetime import datetime
        stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        try:
            path.rename(path.with_name(f"undo.reverted.{stamp}.jsonl"))
        except OSError:
            pass

    summary = f"{job_id}: reverted — {restored} restored, {removed} removed"
    if skipped:
        summary += f", {len(skipped)} SKIPPED (failed the path rules)"
        for why in skipped:
            import logging
            logging.getLogger(__name__).warning("[writer] revert skipped %s", why)
    if failed:
        return summary + f", {len(failed)} FAILED:\n  - " + "\n  - ".join(failed)
    return summary


# ---------------------------------------------------------------------------
# Content gates
# ---------------------------------------------------------------------------

def _load_check_agent_tools():
    """
    scripts/check_agent_tools.py as a module — imported, never reimplemented.

    The allowlist trap (.claude/rules/agent-files.md) is why this gate exists at
    all: `allowed_tools` filters tool SCHEMAS, not dispatch_tool(), so a
    generated agent merely TOLD about a tool could still call it. Running the
    same regex and the same evidence gate the tracked-tree check already runs is
    the point — a second implementation here would drift from it and the drift
    would be invisible.
    """
    import importlib.util
    import sys as _sys
    path = _ROOT / "scripts" / "check_agent_tools.py"
    spec = importlib.util.spec_from_file_location("_build_check_agent_tools", path)
    if spec is None or spec.loader is None:
        raise WriterError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    # Registered BEFORE exec_module: @dataclass resolves its own module through
    # sys.modules, and a module absent from it raises inside dataclasses rather
    # than anywhere that names the real cause.
    _sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        _sys.modules.pop(spec.name, None)
        raise WriterError(f"cannot load {path}: {type(exc).__name__}: {exc}") from exc
    return module


def tools_named_in_text(text: str) -> set[str]:
    """
    Tool names a generated agent file references. TWO scans, unioned.

    SCAN 1 is check_agent_tools.py's own, run through the imported module so
    the tracked-tree semantics are inherited exactly and cannot drift.

    SCAN 2 exists because scan 1's EVIDENCE GATE has a documented blind spot,
    and inheriting it into a security gate would inherit the hole with it. That
    gate requires a call paren, a bullet lead, or an invocation verb immediately
    before the reference — because tracked agent files are full of backticked
    JSON keys and field names, and an ungated version reported 34 of those
    beside 1 real finding. So a file saying:

        Call `get_log_window` for what was logged and
        `send_email` to tell them about it.

    names `send_email` in a position scan 1 cannot see: the verb is on the line
    above. On a tracked file that is a tolerable miss. Here it is not, because
    `allowed_tools` filters SCHEMAS and not dispatch_tool() — an agent merely
    TOLD about a tool can still call it (.claude/rules/agent-files.md), which is
    proven live: `logistics` called `write_agent_config` three times without the
    grant and the dispatcher executed each one.

    Scan 2 drops the evidence gate and keys on something stronger instead: the
    token must be a name register_tools() ACTUALLY REGISTERS. That is why it
    does not reintroduce the false-positive problem — `open_threads`,
    `precursor_by` and `overdue_only` are field names, not registered tools, so
    they cannot match however they are punctuated.
    """
    module = _load_check_agent_tools()
    fd, tmp_name = tempfile.mkstemp(suffix=".md")
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        tmp.write_text(text, encoding="utf-8")
        live, _deferred = module._tools_named_in(tmp)
        named = {name for name, ref in live.items() if ref.is_tool_ref}
    finally:
        tmp.unlink(missing_ok=True)
    return named | _registered_names_in(text)


def _registered_names_in(text: str) -> set[str]:
    """Scan 2: backticked identifiers that are real registered tool names."""
    import re
    try:
        from core.orchestrator import register_tools
        schemas, handlers = register_tools()
        live = {s["name"] for s in schemas} | set(handlers)
    except Exception as exc:
        raise WriterError(f"register_tools() unavailable: {exc}") from exc
    # WHOLE WORD, BACKTICKED OR NOT. Both scans required backticks, so
    # `send_email` written as ordinary prose — "send_email the household" —
    # passed every gate. A model writing an instruction file has no reason to
    # backtick consistently, and the grant is about what the agent is TOLD it
    # can do, not about how the telling is punctuated.
    #
    # Matching bare words is safe here precisely because the candidate set is
    # the live registry: every registered name is snake_case and none is an
    # English word, so this cannot fire on prose the way an ungated pattern
    # over "anything that looks like a tool" would.
    found: set[str] = set()
    for name in live:
        if re.search(rf'(?<![\w]){re.escape(name)}(?![\w])', text or ""):
            found.add(name)
    return found


def check_agent_text(text: str, granted: list[str] | None = None) -> list[str]:
    """
    The ceiling and the grant, over generated agent text. Returns defects.

    SIZE AND SKELETON ARE HARDCODED because this is where the compliance
    evidence points: six of six of Mike's 2026-08-21 complaints were rules
    already written in synthesizer.md and ignored, while every rule moved to
    Python held on first contact. An agent file that grows without bound is an
    agent that stops following its own instructions — so the limit belongs in
    code, not in a style note.
    """
    defects: list[str] = []
    limit = max_agent_lines()
    lines = text.splitlines()
    if len(lines) > limit:
        defects.append(
            f"agent file is {len(lines)} lines, over the {limit}-line limit"
        )
    headings = {
        line.lstrip("# ").strip().lower()
        for line in lines if line.startswith("#")
    }
    for section in required_sections():
        if section.lower() not in headings:
            defects.append(f"agent file has no '## {section}' section")

    if granted is not None:
        allowed = set(granted)
        try:
            named = tools_named_in_text(text)
        except WriterError as exc:
            # FAIL CLOSED. The same reasoning as the git rule: a gate that
            # cannot be evaluated is not a gate, and this one guards a file
            # that could otherwise name send_email.
            return defects + [f"the tool-naming gate could not be run: {exc}"]
        outside = sorted(named - allowed)
        if outside:
            defects.append(
                f"agent file names {outside}, outside its own grant — a tool "
                "named in an agent file is read by the model as a present "
                "capability, and dispatch_tool() does not check the whitelist"
            )
    return defects


def _kind_of(rel_to_root: Path, roots: list[Path]) -> str:
    """
    What a path IS, inferred from where it lands. The path is the kind.

    Inferred rather than declared by the caller so a plan cannot label bytes one
    thing and land them somewhere that means another.
    """
    job_root, overlay_root, policies_root = roots
    if _within(rel_to_root, overlay_root):
        tail = rel_to_root.resolve().relative_to(overlay_root.resolve()).as_posix()
        if tail.startswith("agents/") and tail.endswith(".md"):
            return "agent_file"
        if tail.startswith("capabilities/") and tail.endswith(".yaml"):
            return "capability_record"
        return ""
    if _within(rel_to_root, policies_root):
        return "policy" if rel_to_root.suffix == ".json" else ""
    if _within(rel_to_root, job_root):
        return "artifact"
    return ""


def tracked_agent_names() -> set[str]:
    """
    The THREE sets a generated name must not collide with, unioned.

    routing.yaml's agents, routing_cloud.yaml's agents, and the stems of
    config/agents/*.md. The union is load-bearing, not belt-and-braces: a
    routing-only check passes `time_director`, which has an agent file and no
    routing entry — and a record by that name would then be split across the
    seams, seam 1 loading the tracked prose and seam 2 the overlay's tools.
    """
    names: set[str] = set()
    agents_dir = _ROOT / "config" / "agents"
    if agents_dir.is_dir():
        names |= {p.stem for p in agents_dir.glob("*.md")}
    try:
        import yaml
        for fname in ("routing.yaml", "routing_cloud.yaml"):
            path = _ROOT / "config" / "modules" / fname
            if path.exists():
                cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                names |= set((cfg.get("agents") or {}).keys())
    except Exception:
        pass
    return names


def reserved_display_names() -> set[str]:
    """
    Every display string the Coordinator already answers with, lowercased.

    Three sources, because a display name can collide through any of them: the
    name map's keys (what the model might say), its values (what those resolve
    to), and the closed valid-name list in coordinator.md (what the model is
    told to copy). Read from _ROOT so a fixture repo can exercise the rule.
    """
    reserved: set[str] = set()
    try:
        from core.orchestrator import _AGENT_NAME_MAP, _valid_names_re
        reserved |= {k.lower() for k in _AGENT_NAME_MAP}
        reserved |= {v.lower() for v in _AGENT_NAME_MAP.values()}
        path = _ROOT / "config" / "agents" / "coordinator.md"
        if path.exists():
            match = _valid_names_re().search(path.read_text(encoding="utf-8"))
            if match:
                import re as _re
                reserved |= {d.lower()
                             for d in _re.findall(r'`"([^"]+)"`', match.group(2))}
    except Exception:
        return reserved
    return reserved


def model_ref_names() -> set[str]:
    """
    Agents present in BOTH routing files — the only valid targets for a model_ref.

    A ref present in one file resolves under one DEPLOYMENT_MODE and vanishes
    under the other, which is exactly the split the single-record shape exists
    to make impossible. Intersection, not union, for that reason.
    """
    try:
        import yaml
    except Exception:
        return set()
    sets: list[set[str]] = []
    for fname in ("routing.yaml", "routing_cloud.yaml"):
        path = _ROOT / "config" / "modules" / fname
        if not path.exists():
            return set()
        try:
            cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            return set()
        sets.append(set((cfg.get("agents") or {}).keys()))
    return set.intersection(*sets) if sets else set()


def peer_displays(persona: str | None = None,
                  exclude: set[str] | None = None) -> dict[str, str]:
    """
    name -> display_name for every capability ALREADY in this persona's overlay.

    `exclude` drops the records this apply() is itself writing, so a record
    being updated in place is not compared against its own previous version.
    Read straight from disk rather than through core/build/overlay.py: that
    module filters and caches, and a uniqueness check wants everything that is
    actually there.
    """
    out: dict[str, str] = {}
    try:
        import yaml
    except Exception:
        return out
    directory = overlay_dir(persona) / "capabilities"
    if not directory.is_dir():
        return out
    for path in sorted(directory.glob("*.yaml")):
        if exclude and path.stem in exclude:
            continue
        try:
            record = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(record, dict) and record.get("name"):
            out[str(record["name"])] = str(record.get("display_name") or "")
    return out


def _known_domains() -> set[str]:
    try:
        from tools.wisdom import DOMAINS, OVERFLOW_DOMAIN
        return set(DOMAINS) | {OVERFLOW_DOMAIN}
    except Exception:
        return set()


def _job_gate(job_id: str, dry_run: bool, persona: str | None) -> str:
    """1. Exists, correct state, budget untripped, attempts remaining."""
    from core.build import jobs as J
    job = J.get(job_id, persona)
    if job is None:
        return f"{job_id}: no such job"
    if not dry_run and job["state"] not in WRITABLE_STATES:
        return (f"{job_id}: state is {job['state']!r} — a write is allowed only "
                f"from {sorted(WRITABLE_STATES)}")
    if int(job.get("attempt", 1)) > J.MAX_ATTEMPTS:
        return f"{job_id}: all {J.MAX_ATTEMPTS} attempts used"
    try:
        from core.build import cost
        spend, limit = cost.job_spend(job_id, persona), cost.job_limit(job_id, persona)
        if spend > limit:
            return (f"{job_id}: spent ${spend:.2f} against a ${limit:.2f} limit — "
                    "the limit is a tripwire, not a tolerance band")
    except Exception:
        # Metering unavailable is not a licence to write. Same direction as
        # every other gate here: not knowing counts as a refusal.
        return f"{job_id}: spend could not be read, so the budget gate cannot pass"
    return ""


def apply(job_id: str, plan: dict | None, edits: list[dict],
          dry_run: bool = False, persona: str | None = None) -> str:
    """
    Land a job's edits, or explain why not. NEVER RAISES — refusals are strings.

    `edits` is a list of {"path": ..., "content": ...}. The KIND of each edit is
    inferred from where it lands rather than declared by the caller, so a plan
    cannot label bytes one thing and write them somewhere that means another.

    The Planner calls this with dry_run=True as its own file-path check — the
    enforcer itself, not a copy of its rules, which is the only way the
    validator and the enforcer cannot drift.

    Gate order matters and is the order below. Everything is validated before
    ANY byte is written, so a refusal never leaves a half-applied overlay.
    """
    from core.build import jobs as J
    from core.persona import PersonaError
    try:
        return _apply(job_id, plan, edits, dry_run, persona)
    except PersonaError as exc:
        # THE ASYMMETRY WITH THE READ SIDE IS DELIBERATE. overlay.load_overlay()
        # catches PersonaError and returns {} — letting it propagate there would
        # make a TRACKED agent's routing raise where it does not today, which is
        # a change to the Red-tier path rather than an inheritance. Here, on the
        # write side, there is no tracked behaviour to preserve and no safe
        # default: a write with no persona in scope has no correct destination.
        return (f"REFUSED — {job_id}: no persona in scope, so there is no tree "
                f"to write into ({exc})")
    except Exception as exc:  # pragma: no cover — the last resort, by design
        try:
            if not dry_run:
                revert(job_id, persona)
                J.set_state(job_id, "failed", detail=f"writer raised: {exc}",
                            persona=persona)
        except Exception:
            pass
        return f"{job_id}: writer failed and reverted — {type(exc).__name__}: {exc}"


def _apply(job_id: str, plan: dict | None, edits: list[dict],
           dry_run: bool, persona: str | None) -> str:
    from core.build import jobs as J
    from core.build import schemas

    refused = _job_gate(job_id, dry_run, persona)
    if refused:
        return f"REFUSED — {refused}"

    if not isinstance(edits, list) or not edits:
        return f"REFUSED — {job_id}: no edits"

    roots = allow_roots(job_id, persona)
    tracked = _tracked_paths()

    # --- 2. Path rules, all three, for every edit -----------------------
    resolved: list[tuple[Path, str, str]] = []
    problems: list[str] = []
    for position, edit in enumerate(edits, start=1):
        if not isinstance(edit, dict) or "path" not in edit:
            problems.append(f"edit[{position}] has no path")
            continue
        content = edit.get("content")
        if not isinstance(content, str):
            problems.append(f"edit[{position}] content is not text")
            continue
        target = Path(edit["path"])
        if not target.is_absolute():
            target = _ROOT / target
        why = check_path(target, job_id, persona, tracked)
        if why:
            problems.append(why)
            continue
        kind = _kind_of(target, roots)
        if not kind:
            problems.append(
                f"{_rel(target)}: refused — inside an allow-root but not a shape "
                "the writer recognises (overlay/agents/*.md, "
                "overlay/capabilities/*.yaml, policies/*.json, or a job artifact)"
            )
            continue
        resolved.append((target, content, kind))

    if problems:
        return "REFUSED — " + f"{len(problems)} path problem(s):\n  - " + \
               "\n  - ".join(problems)

    # --- 4. Ceiling -----------------------------------------------------
    # An edit ABOVE the ceiling is never dropped. It parks as an approval
    # request, which is the difference between a ceiling and a wall.
    agent_edits = [e for e in resolved if e[2] == "agent_file"]
    if agent_edits and not may_create_agent_files():
        if not dry_run:
            J.set_state(job_id, "awaiting_approval",
                        detail="agent-file creation is above the ceiling "
                               "(autonomy.may_create_agent_files: false)",
                        persona=persona)
        return ("PARKED — above the ceiling: autonomy.may_create_agent_files is "
                "false, so the agent file is an approval request rather than a "
                "write. Nothing was dropped; raise the flag on the VM to proceed.")

    # --- 5. Shape gate + 6. content gates -------------------------------
    defects = _content_defects(resolved, persona, plan)
    if defects:
        return "REFUSED — " + f"{len(defects)} defect(s):\n  - " + "\n  - ".join(defects)

    if dry_run:
        kinds = ", ".join(sorted({k for _, _, k in resolved}))
        return (f"OK (dry run) — {job_id}: {len(resolved)} edit(s) would be "
                f"written [{kinds}]; no bytes touched")

    # --- 7. Journal, then write -----------------------------------------
    # The journal entry for a file goes down BEFORE that file's bytes, per
    # file. A crash between the two leaves an entry saying the file did not
    # exist, and revert() then deletes nothing — which is correct.
    written: list[str] = []
    for target, content, _kind in resolved:
        _journal(job_id, target, persona)
        _write_atomic(target, content)
        written.append(_rel(target))

    J.heartbeat(job_id, node="writer.apply", persona=persona)
    return (f"OK — {job_id}: {len(written)} file(s) written\n  - " +
            "\n  - ".join(written))


def _conditional_defects(record: dict, plan: dict | None) -> list[str]:
    """
    A grant that carries a condition is refused until the condition is met.

    The condition for find_places is that the PLAN names it in risks[], because
    that is what puts it in front of Mike in the approval brief. Checked against
    the plan rather than the record so the record cannot satisfy its own
    condition — a capability vouching for itself is not a review.
    """
    granted = ((record.get("routing") or {}).get("local") or {}).get("allowed_tools")
    if not isinstance(granted, list):
        return []
    risks = (plan or {}).get("risks") or []
    named = " ".join(str(r) for r in risks) if isinstance(risks, list) else ""
    out: list[str] = []
    for tool in sorted(set(str(g) for g in granted) & set(CONDITIONAL_GRANTS)):
        if tool not in named:
            out.append(
                f"the grant {tool!r} is conditional and its condition is unmet — "
                f"{CONDITIONAL_GRANTS[tool]}. plan.risks[] "
                + ("does not name it" if plan else "is unavailable: no plan was passed")
            )
    return out


def _content_defects(resolved: list[tuple[Path, str, str]],
                     persona: str | None, plan: dict | None = None) -> list[str]:
    """
    The shape gate, the constitution and the grant, over what is about to land.

    Records and agent files are checked AGAINST EACH OTHER, not only
    individually: the record carries agent_sha256 and the seams load the two
    through different paths, so a record and a file that disagree would produce
    exactly the half-wired state one record exists to prevent.
    """
    from core.build import schemas

    defects: list[str] = []
    agent_text: dict[str, str] = {}
    records: list[tuple[Path, dict]] = []

    for target, content, kind in resolved:
        if kind == "agent_file":
            agent_text[target.stem] = content
        elif kind == "capability_record":
            try:
                import yaml
                parsed = yaml.safe_load(content)
            except Exception as exc:
                defects.append(f"{_rel(target)}: not parseable as YAML — {exc}")
                continue
            if not isinstance(parsed, dict):
                defects.append(f"{_rel(target)}: record is not a mapping")
                continue
            if parsed.get("name") != target.stem:
                defects.append(
                    f"{_rel(target)}: record name {parsed.get('name')!r} does "
                    f"not match its filename stem {target.stem!r}"
                )
            records.append((target, parsed))
        elif kind == "policy":
            try:
                parsed = json.loads(content)
            except ValueError as exc:
                defects.append(f"{_rel(target)}: not parseable as JSON — {exc}")
                continue
            if not isinstance(parsed, dict) or not parsed.get("id"):
                defects.append(f"{_rel(target)}: policy has no id")

    tracked_names = tracked_agent_names()
    for target, record in records:
        # PEERS = what is already in the overlay, minus the records this call is
        # writing, PLUS the other records in this call. Both halves are needed:
        # two capabilities landing in one apply() must be checked against each
        # other, and a record being updated must not collide with its own old
        # copy.
        landing = {str(r.get("name") or "") for _t, r in records}
        peers = peer_displays(persona, exclude=landing)
        peers.update({str(r.get("name") or ""): str(r.get("display_name") or "")
                      for _t, r in records})

        found = schemas.validate_overlay_capability(
            record, tracked_names=tracked_names, read_set=ALLOWED_GRANTS,
            known_domains=_known_domains(),
            reserved_display=reserved_display_names(),
            model_ref_names=model_ref_names(),
            peer_displays=peers)
        defects.extend(f"{_rel(target)}: {d}" for d in found)
        defects.extend(f"{_rel(target)}: {d}"
                       for d in _conditional_defects(record, plan))

        name = str(record.get("name") or "")
        text = agent_text.get(name)
        if text is None:
            defects.append(
                f"{_rel(target)}: no agent file for {name!r} in the same apply() "
                "— the record and the file it names land together or not at all"
            )
            continue
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if digest != str(record.get("agent_sha256", "")).lower():
            defects.append(
                f"{_rel(target)}: agent_sha256 does not match the agent file in "
                "this call — the two are loaded by different seams and must not "
                "be able to disagree"
            )

        # ONE call, not two. constitution.check() composes check_agent_text()
        # in, so the ceiling and the constitution are a single entry point and a
        # size defect cannot be reported twice by two callers that both own it.
        try:
            from core.build import constitution
            defects.extend(
                f"agents/{name}.md: {d}" for d in constitution.check(text, record)
            )
        except WriterError as exc:
            defects.append(f"agents/{name}.md: generation gate unavailable — {exc}")

    for name in agent_text:
        if not any(r.get("name") == name for _t, r in records):
            defects.append(
                f"agents/{name}.md: no capability record in the same apply() — "
                "an agent file without one is the half-wired state (time_director) "
                "that one required record exists to end"
            )
    return defects
