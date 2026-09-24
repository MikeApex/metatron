#!/usr/bin/env python3
"""
Assert that every capability Build landed is actually WIRED. Check 11 of qa_sweep.sh.

WHAT THIS RETIRES (the standing rule on new harness scripts, .claude/rules/deploy.md):
the manual registration checklist. A new specialist has historically had to be
added by hand to two routing files, the Coordinator's valid-name list, its
Specialist directory, `_AGENT_NAME_MAP`, `_UNAVAILABLE_CONSEQUENCE` and
`knowledge_domains.yaml` — and the live evidence that nobody completes that
reliably is in the tree right now: `time_director` has an agent file, a name-map
entry and a consequence line, and appears in NEITHER routing file nor the
Coordinator's list. One registry row with required fields replaces the
checklist; this script is what stops the row's guarantees being quietly removed.

REWRITTEN FOR v4.11 (plan section 10, finding 5). Build no longer lands an
overlay — it produces ORDINARY TRACKED FILES that Mike commits, so every
assertion below reads the tracked tree rather than a persona-scoped overlay
directory. The `--overlay` flag is gone with the thing it pointed at.

THE ONE RULE THAT MAKES ONE SCRIPT WORK IN TWO TREES (cold read 2):

    WIRING IS ASSERTED ONLY FOR `landed` ROWS.

The implementer writes its registry row `status: staged`, in a sandbox worktree
that by design holds NO wiring — no routing entry, no agent file, no Coordinator
line, because all of those are Red and belong to the main session. So a `staged`
row passes here and the sandbox's sweep is green. The main session flips the row
to `landed` at N13, once the Red half is in the same tree, and from that moment
the same script fails on exactly the gaps the sandbox was right not to have.

Six assertions, each with the specific failure it exists to catch:

  1. THE DENY LIST STILL NAMES ITSELF. `core/build/**` and
     `config/modules/build.yaml` are on core/build/gates.py's hardcoded deny
     list, which is the only reason "the ceiling is config, and anything that
     edits config can raise it" is not true here. A later simplification that
     drops either turns the ceiling into a suggestion, silently.

  2. THE GITIGNORE LINE STILL EXISTS. `data/build/` holds the job artifacts —
     the answer ledger, with verbatim interview answers. If that line goes they
     become committable, and they are Sensitive tier.

  3. ROUTING PARITY. A landed capability appears in BOTH routing files with the
     same tool grant. One file only is the half-wired state with a worse
     failure mode than none, because it works in one deployment mode.

  4. THE COORDINATOR KNOWS THE NAME. Its closed valid-name list carries the
     display name and its Specialist directory carries an entry. A name absent
     from that sentence is a name the model has been TOLD is invalid.

  5. THE KNOWLEDGE DOMAIN RESOLVES. A domain named by a landed row must exist
     in knowledge_domains.yaml and list the capability.

  6. A LANDED CAPABILITY CARRIES A RUN LINE. The shipped thing is the
     capability, not the factory: each landed agent is dispatched on every
     matching turn, forever, at that turn's model price. A landed row with no
     run line is a capability whose standing cost nothing meters.

Stdlib plus PyYAML. Zero model tokens. Exit 1 on any finding.

Usage:
    python3 scripts/check_build_registration.py
    python3 scripts/check_build_registration.py --capability home_care
    python3 scripts/check_build_registration.py --registry path/to/registry.yaml
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Entries that must remain on the deny list. Not the whole list — the ones whose
# removal would be invisible and consequential.
REQUIRED_DENY = {
    "exact": {"config/constitution.md", "deploy.sh", ".claude/settings.json",
              "core/router.py", "core/persona.py", "core/spend_guard.py",
              "core/scheduler.py", "config/modules/build.yaml"},
    "prefix": {"config/personas/", "core/build/", ".git/"},
}

# data/build/ is the JOB directory — the ledger with verbatim interview answers.
# It is the one new ignore line the v4 design needs (plan section 10).
REQUIRED_GITIGNORE = "data/build/"

ROUTING_FILES = ("routing.yaml", "routing_cloud.yaml")

_VALID_NAMES_RE = re.compile(
    r'^\*\*Valid `"agent"` values\*\*[^\n]*:\s*\n([^\n]+)$', re.MULTILINE)
_DIRECTORY_HEADING = "## Specialist directory"


def _findings_deny_list() -> list[str]:
    from core.build import gates
    out = []
    for path in sorted(REQUIRED_DENY["exact"] - set(gates.DENY_EXACT)):
        out.append(f"gates.DENY_EXACT no longer names {path!r}")
    for prefix in sorted(REQUIRED_DENY["prefix"] - set(gates.DENY_PREFIXES)):
        out.append(f"gates.DENY_PREFIXES no longer names {prefix!r}")
    if not any("key" in g for g in gates.DENY_GLOBS):
        out.append("gates.DENY_GLOBS no longer refuses *key*.json")
    if not any(".env" in g for g in gates.DENY_GLOBS):
        out.append("gates.DENY_GLOBS no longer refuses .env*")
    return out


def _findings_gitignore() -> list[str]:
    path = ROOT / ".gitignore"
    if not path.exists():
        return ["no .gitignore — the job directory's only ignore cover is gone"]
    lines = {ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()}
    if REQUIRED_GITIGNORE not in lines:
        return [f".gitignore no longer carries {REQUIRED_GITIGNORE!r} — the job "
                "artifacts become committable, and the answer ledger carries "
                "verbatim interview answers"]
    return []


def _routing() -> dict[str, dict]:
    """{filename: {agent: entry}} for both routing files. Missing file = {}."""
    import yaml
    out: dict[str, dict] = {}
    for fname in ROUTING_FILES:
        path = ROOT / "config" / "modules" / fname
        agents: dict = {}
        if path.exists():
            try:
                cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                agents = (cfg.get("agents") or {})
            except Exception as exc:
                agents = {"__error__": str(exc)}
        out[fname] = agents
    return out


def _findings_routing(name: str, routing: dict[str, dict]) -> list[str]:
    """Assertion 3. Present in BOTH, with the same grant."""
    out: list[str] = []
    present = [f for f in ROUTING_FILES if name in (routing.get(f) or {})]
    missing = [f for f in ROUTING_FILES if f not in present]
    if missing and present:
        out.append(
            f"{name}: landed and present in {present[0]} but NOT in "
            f"{', '.join(missing)} — this is the time_director shape: it works "
            "in one deployment mode and raises in the other")
        return out
    if not present:
        out.append(
            f"{name}: landed with no entry in either routing file — anything "
            "naming it raises in core/router.py's name resolution")
        return out

    grants = {f: sorted((routing[f][name] or {}).get("allowed_tools") or [])
              for f in ROUTING_FILES}
    if grants[ROUTING_FILES[0]] != grants[ROUTING_FILES[1]]:
        only_a = set(grants[ROUTING_FILES[0]]) - set(grants[ROUTING_FILES[1]])
        only_b = set(grants[ROUTING_FILES[1]]) - set(grants[ROUTING_FILES[0]])
        out.append(
            f"{name}: tool grants differ between the routing files — "
            f"{ROUTING_FILES[0]} only: {sorted(only_a) or '—'}; "
            f"{ROUTING_FILES[1]} only: {sorted(only_b) or '—'}. The capability "
            "would have different powers depending on DEPLOYMENT_MODE")
    return out


def _findings_coordinator(name: str, display: str) -> list[str]:
    """Assertion 4. The closed list and the directory."""
    path = ROOT / "config" / "agents" / "coordinator.md"
    if not path.exists():
        return [f"{name}: config/agents/coordinator.md not found"]
    text = path.read_text(encoding="utf-8")
    out: list[str] = []

    match = _VALID_NAMES_RE.search(text)
    if not match:
        out.append("the Coordinator's closed valid-name list was not found — the "
                   "anchor this check and the registration both depend on has moved")
    elif display and display not in match.group(1):
        out.append(
            f"{name}: {display!r} is not in the Coordinator's closed valid-name "
            "list — the model has been told, character for character, that this "
            "name is invalid")

    if _DIRECTORY_HEADING not in text:
        out.append(f"'{_DIRECTORY_HEADING}' not found in coordinator.md")
    else:
        start = text.index(_DIRECTORY_HEADING)
        nxt = re.search(r"^## ", text[start + len(_DIRECTORY_HEADING):], re.MULTILINE)
        end = start + len(_DIRECTORY_HEADING) + (nxt.start() if nxt else len(text))
        if display and display not in text[start:end]:
            out.append(
                f"{name}: no Specialist directory entry for {display!r} — the "
                "Coordinator has the name and nothing telling it when to choose it")
    return out


def _findings_knowledge(name: str, domain: str) -> list[str]:
    """Assertion 5."""
    if not domain:
        return []
    import yaml
    path = ROOT / "config" / "modules" / "knowledge_domains.yaml"
    if not path.exists():
        return [f"{name}: names domain {domain!r} and knowledge_domains.yaml is absent"]
    try:
        cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        return [f"knowledge_domains.yaml is unreadable: {exc}"]
    domains = cfg.get("domains") or {}
    if domain not in domains:
        return [f"{name}: names knowledge domain {domain!r}, which does not exist"]
    if name not in (domains[domain] or []):
        return [f"{name}: domain {domain!r} exists and does not list {name!r} — the "
                "fetched entries would reach every agent but this one"]
    return []


def _findings_agent_file(name: str, kind: str) -> list[str]:
    if kind != "agent":
        return []
    if not (ROOT / "config" / "agents" / f"{name}.md").exists():
        return [f"{name}: landed as an agent with no config/agents/{name}.md — "
                "load_agent() raises FileNotFoundError on the first dispatch"]
    return []


def _findings_run_line(name: str, row: dict) -> list[str]:
    """Assertion 6."""
    run = row.get("run")
    if not isinstance(run, dict) or not run.get("execution_mode"):
        return [f"{name}: landed with no run line — its standing cost is unmetered, "
                "which is the 'Unseen' cost class CLAUDE.md names"]
    if "dispatches_expected_per_day" not in run or "dispatches_actual_per_day" not in run:
        return [f"{name}: run line carries no expected/actual fields — an absent key "
                "reads as 'this row predates the run line'; None reads as 'not "
                "counted yet', which is the true statement"]
    return []


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--capability", default=None,
                    help="check one capability only — what the driver runs at N13")
    ap.add_argument("--registry", default=None,
                    help="check a registry file other than config/build/registry.yaml")
    args = ap.parse_args()

    findings: list[str] = []
    findings += _findings_deny_list()
    findings += _findings_gitignore()

    from core.build import registry as R
    registry_path = Path(args.registry) if args.registry else None

    try:
        all_rows = R.rows(registry_path)
    except Exception as exc:
        print(f"  ! registry unreadable: {exc}")
        print("\nbuild-registration: 1 finding — registry unreadable.")
        return 1

    rows = [r for r in all_rows if str(r.get("status")) in R.WIRED_STATUSES]
    if args.capability:
        rows = [r for r in rows if str(r.get("name")) == args.capability]
        staged = [r for r in all_rows if str(r.get("name")) == args.capability
                  and str(r.get("status")) == "staged"]
        if not rows and not staged:
            print(f"  ! no registry row for capability {args.capability!r}")
            print("\nbuild-registration: 1 finding — no such capability.")
            return 1

    routing = _routing()
    for row in rows:
        name = str(row.get("name") or "")
        display = str(row.get("display_name") or "")
        findings += _findings_routing(name, routing)
        findings += _findings_coordinator(name, display)
        findings += _findings_knowledge(name, str(row.get("knowledge_domain") or ""))
        findings += _findings_agent_file(name, str(row.get("kind") or ""))
        findings += _findings_run_line(name, row)

    try:
        from core.build import constitution
        drift = constitution.canonical_drift()
        if drift:
            findings.append(drift)
    except Exception as exc:
        findings.append(f"constitution gate unavailable: {exc}")

    for finding in findings:
        print(f"  ! {finding}")
    staged_count = sum(1 for r in all_rows if str(r.get("status")) == "staged")
    scope = (f"{len(rows)} landed row(s) checked, {staged_count} staged row(s) "
             f"not checked for wiring — that is the rule, not an omission")
    print(f"\nbuild-registration: {len(findings)} finding(s) — {scope}.")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
