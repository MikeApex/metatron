#!/usr/bin/env python3
"""
Assert the invariants Build's landing mechanism rests on. Check 11 of qa_sweep.sh.

WHAT THIS RETIRES (the standing rule on new harness scripts, .claude/rules/deploy.md):
the manual registration checklist. A new specialist has historically had to be
added by hand to two routing files, the Coordinator's valid-name list, its
Specialist directory, `_AGENT_NAME_MAP`, `_UNAVAILABLE_CONSEQUENCE`,
`_ALWAYS_CONFIDENTIAL` and `knowledge_domains.yaml` — and the live evidence that
nobody completes that reliably is in the tree right now: `time_director` has an
agent file, a name-map entry and a consequence line, and appears in NEITHER
routing file nor the Coordinator's list. One record with required fields
replaces the checklist; this script is what stops the record's own guarantees
being quietly removed later.

Six assertions, each with a specific failure it exists to catch:

  1. THE DENY LIST STILL NAMES ITSELF. `core/build/**` and
     `config/modules/build.yaml` are on core/build/writer.py's hardcoded deny
     list, which is the only reason "the ceiling is config, and anything that
     edits config can raise it" is not true here. A later simplification that
     drops either turns the ceiling into a suggestion, silently.

  2. THE GITIGNORE LINE STILL EXISTS. The overlay needs no new ignore rule
     because `data/personas/*/` already covers it. If that line goes, generated
     agent files — Sensitive-tier, persona-derived — become committable.

  3. THE GRANT ALLOWLIST TRACKS THE LIVE TOOL SURFACE. An allowlist entry that
     no longer names a registered tool grants nothing while looking like it
     grants something, which is how a typo hides.

  4. THE THREE-SET NAME RULE, RE-ASSERTED INDEPENDENTLY. Read from the files
     here rather than through core/build/overlay.py, so a defect in that module
     cannot clear its own check.

  5. EVERY OVERLAY RECORD VALIDATES. Read natively — qa_sweep.sh's own greps go
     through `git ls-files` and its check scripts glob `config/agents/*.md`, so
     none of them can see an overlay file at all.

  6. A LANDED CAPABILITY CARRIES A RUN LINE. The shipped thing is the
     capability, not the factory: each landed agent is dispatched on every
     matching turn, forever, at that turn's model price. A landed row with no
     run line is a capability whose standing cost nothing meters.

Stdlib plus PyYAML. Zero model tokens. Exit 1 on any finding.

Usage:
    python3 scripts/check_build_registration.py
    python3 scripts/check_build_registration.py --overlay DIR   # one overlay tree
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Entries that must remain on the writer's deny list. Not the whole list — the
# ones whose removal would be invisible and consequential.
REQUIRED_DENY = {
    "exact": {"config/constitution.md", "deploy.sh", ".claude/settings.json",
              "core/router.py", "core/persona.py", "core/spend_guard.py",
              "core/scheduler.py", "config/modules/build.yaml"},
    "prefix": {"config/personas/", "core/build/", ".git/"},
}

REQUIRED_GITIGNORE = "data/personas/*/"


def _findings_deny_list() -> list[str]:
    from core.build import writer
    out = []
    for path in sorted(REQUIRED_DENY["exact"] - set(writer.DENY_EXACT)):
        out.append(f"writer.DENY_EXACT no longer names {path!r}")
    for prefix in sorted(REQUIRED_DENY["prefix"] - set(writer.DENY_PREFIXES)):
        out.append(f"writer.DENY_PREFIXES no longer names {prefix!r}")
    if not any("key" in g for g in writer.DENY_GLOBS):
        out.append("writer.DENY_GLOBS no longer refuses *key*.json")
    if not any(".env" in g for g in writer.DENY_GLOBS):
        out.append("writer.DENY_GLOBS no longer refuses .env*")
    return out


def _findings_gitignore() -> list[str]:
    path = ROOT / ".gitignore"
    if not path.exists():
        return ["no .gitignore — the overlay's only ignore cover is gone"]
    lines = {ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()}
    if REQUIRED_GITIGNORE not in lines:
        return [f".gitignore no longer carries {REQUIRED_GITIGNORE!r} — generated "
                "agent files become committable, and they are Sensitive tier"]
    return []


def _findings_allowlist() -> list[str]:
    from core.build import writer
    missing = writer.unregistered_grants()
    if missing:
        return [f"allowlist names {m!r}, which register_tools() does not provide"
                for m in missing]
    return []


def _tracked_names() -> set[str]:
    """The three sets, read here rather than imported — assertion 4."""
    import yaml
    names = {p.stem for p in (ROOT / "config" / "agents").glob("*.md")}
    for fname in ("routing.yaml", "routing_cloud.yaml"):
        path = ROOT / "config" / "modules" / fname
        if path.exists():
            cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            names |= set((cfg.get("agents") or {}).keys())
    return names


def _overlay_dirs(explicit: str | None) -> list[Path]:
    if explicit:
        return [Path(explicit)]
    base = ROOT / "data" / "personas"
    if not base.is_dir():
        return []
    return sorted(p / "build" / "overlay" for p in base.iterdir()
                  if (p / "build" / "overlay").is_dir())


def _records_in(overlay: Path) -> dict[str, str]:
    """name -> display_name for every record in an overlay tree."""
    import yaml
    out: dict[str, str] = {}
    for path in sorted((overlay / "capabilities").glob("*.yaml")):
        try:
            record = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(record, dict) and record.get("name"):
            out[str(record["name"])] = str(record.get("display_name") or "")
    return out


def _findings_records(overlay_dirs: list[Path]) -> tuple[list[str], int]:
    import yaml
    from core.build import schemas, writer
    from tools.wisdom import DOMAINS, OVERFLOW_DOMAIN

    tracked = _tracked_names()
    domains = set(DOMAINS) | {OVERFLOW_DOMAIN}
    findings: list[str] = []
    seen = 0

    # THE SECOND LINE HAS TO LOOK FOR THE SAME THINGS THE FIRST DOES.
    #
    # This called the validator with `tracked_names` alone, so it re-asserted
    # the three-set `name` rule and neither of the rules added for the
    # display-name and provider defects — the writer refused both at write time
    # and nothing re-checked a record that arrived any other way. Independent
    # re-assertion is this script's whole job; a narrower one is a false
    # reassurance.
    for overlay in overlay_dirs:
        records = _records_in(overlay)
        for path in sorted((overlay / "capabilities").glob("*.yaml")):
            seen += 1
            label = path.relative_to(ROOT) if ROOT in path.parents else path
            try:
                record = yaml.safe_load(path.read_text(encoding="utf-8"))
            except Exception as exc:
                findings.append(f"{label}: unreadable — {exc}")
                continue
            for defect in schemas.validate_overlay_capability(
                    record, tracked_names=tracked,
                    read_set=writer.ALLOWED_GRANTS, known_domains=domains,
                    reserved_display=writer.reserved_display_names(),
                    model_ref_names=writer.model_ref_names(),
                    peer_displays=records):
                findings.append(f"{label}: {defect}")
            if isinstance(record, dict):
                agent = overlay / str(record.get("agent_file") or "")
                if not agent.exists():
                    findings.append(f"{label}: names {record.get('agent_file')!r}, "
                                    "which is not in the overlay")
    return findings, seen


def _findings_run_lines(overlay_dirs: list[Path]) -> list[str]:
    """
    Assertion 6. A `landed` registry row must carry a run line.

    Silent when no registry exists: before the first landing there is nothing to
    assert, and a check that fails on an empty system is a check people disable.
    """
    findings: list[str] = []
    for overlay in overlay_dirs:
        registry = overlay.parent / "registry.jsonl"
        if not registry.exists():
            continue
        for line in registry.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("state") != "landed":
                continue
            run = row.get("run")
            if not isinstance(run, dict) or not run.get("execution_mode"):
                findings.append(
                    f"registry: {row.get('capability') or row.get('job_id')} is "
                    "landed with no run line — its standing cost is unmetered")
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--overlay", default=None,
                    help="check one overlay tree instead of every persona's")
    args = ap.parse_args()

    findings: list[str] = []
    findings += _findings_deny_list()
    findings += _findings_gitignore()
    findings += _findings_allowlist()

    overlay_dirs = _overlay_dirs(args.overlay)
    record_findings, seen = _findings_records(overlay_dirs)
    findings += record_findings
    findings += _findings_run_lines(overlay_dirs)

    try:
        from core.build import constitution
        drift = constitution.canonical_drift()
        if drift:
            findings.append(drift)
    except Exception as exc:
        findings.append(f"constitution gate unavailable: {exc}")

    for finding in findings:
        print(f"  ! {finding}")
    scope = f"{len(overlay_dirs)} overlay tree(s), {seen} record(s)"
    print(f"\nbuild-registration: {len(findings)} finding(s) — {scope}.")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
