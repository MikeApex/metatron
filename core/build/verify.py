"""
core/build/verify.py — THE SAME CHECKS, NOT EQUIVALENTS. Twice.

Every check runs once over the tracked tree, exactly as qa_sweep.sh runs it, and
once over the overlay. Nothing here is a reimplementation: this module SHELLS
OUT to the same scripts, with cwd=ROOT, and a check that drifts in qa_sweep.sh
drifts here in the same direction on the same day.

WHY AN OVERLAY PASS IS NEEDED AT ALL. qa_sweep.sh's greps go through
`git ls-files` (scripts/qa_sweep.sh:87-99, :137) and its check scripts glob
`config/agents/*.md` and read the two tracked routing files. **None of them can
see an overlay file — on the VM or on the Mac.** A generated agent could name
`send_email`, contradict a tracked rule, or join a domain that does not exist,
and the sweep would report eleven green checks. So three scripts gained a
`--overlay DIR` flag and check_build_registration.py reads the overlay natively.

THE "SAME CHECKS" CLAIM IS PROVED, NOT ASSERTED — and in TWO parts, because one
equality over the whole invocation could never pass:

  · check_knowledge_domains.py is a standalone script the sweep does not run.
  · Neither the capability's own tests nor test_action_provenance.py are sweep
    checks.

So SHARED_CHECKS (the sweep's ten plus build-registration) must equal the
sweep's set EXACTLY with ':overlay' stripped, ADDED_CHECKS must equal its
declared list exactly, and nothing may be in neither. Equality over a declared
subset still cannot drift, which is the property this design wanted.

ON FAILURE: core/build/writer.revert(), append `→ failed` with the check name
and its output, emit BUILD_CHECK_FAILED, and carry the failing output VERBATIM
into the next attempt's brief. Nothing is ever left half-applied.

Plan: archive/plans/build_vertical_plan_2026-09-18.md Section 6.8
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent

# The sweep's own checks. This set is ASSERTED against a live `qa_sweep.sh
# --verbose` run, so adding a check there and forgetting it here fails the test
# rather than silently narrowing what a landing is verified against.
SHARED_CHECKS: frozenset[str] = frozenset({
    "agent-tools", "confirm-executors", "personas", "rule-overlap",
    "project-log", "py-compile", "backlog-ids", "dev-markers",
    "claude-md-claims", "deploy-lock", "build-registration",
})

# What verify adds on top, and the complete list of it.
ADDED_CHECKS: frozenset[str] = frozenset({
    "knowledge-domains", "capability-tests", "action-provenance",
})

OVERLAY_SUFFIX = ":overlay"
_TIMEOUT = 600

# `--- name (pass) ---` / `--- name (FAIL) ---`, which --verbose prints for
# EVERY check. The one-line summary is not parsed: on failure it lists only the
# failures, so a set built from it would be silently short exactly when it matters.
_SWEEP_LINE_RE = re.compile(r'^--- (\S+) \((pass|FAIL)\) ---$', re.MULTILINE)


@dataclass
class CheckResult:
    name: str
    ok: bool
    output: str = ""

    @property
    def base(self) -> str:
        """The name with ':overlay' stripped — what the equalities compare."""
        return self.name[:-len(OVERLAY_SUFFIX)] if self.name.endswith(OVERLAY_SUFFIX) \
            else self.name


@dataclass
class VerifyReport:
    results: list[CheckResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(r.ok for r in self.results)

    @property
    def failures(self) -> list[CheckResult]:
        return [r for r in self.results if not r.ok]

    def names(self) -> set[str]:
        return {r.name for r in self.results}

    def base_names(self) -> set[str]:
        return {r.base for r in self.results}

    def summary(self) -> str:
        if self.ok:
            return f"verify: {len(self.results)}/{len(self.results)} checks pass"
        failed = ", ".join(r.name for r in self.failures)
        return (f"verify: {len(self.failures)} of {len(self.results)} FAILED — "
                f"{failed}")


def _run(name: str, argv: list[str]) -> CheckResult:
    try:
        proc = subprocess.run(argv, cwd=str(_ROOT), capture_output=True,
                              timeout=_TIMEOUT)
    except (OSError, subprocess.SubprocessError) as exc:
        return CheckResult(name, False, f"could not run {argv}: {exc}")
    out = (proc.stdout + proc.stderr).decode("utf-8", "replace")
    return CheckResult(name, proc.returncode == 0, out)


def _python() -> str:
    venv = _ROOT / ".venv" / "bin" / "python"
    return str(venv) if venv.exists() else "python3"


def sweep_results() -> list[CheckResult]:
    """Every check qa_sweep.sh ran, by name, parsed from its --verbose output."""
    proc = _run("qa-sweep", ["bash", "scripts/qa_sweep.sh", "--verbose"])
    results: list[CheckResult] = []
    for name, verdict in _SWEEP_LINE_RE.findall(proc.output):
        results.append(CheckResult(name, verdict == "pass"))
    if not results:
        # The sweep produced nothing parseable. Treated as a FAILURE rather than
        # an empty pass: "no checks ran" must never read like "no checks failed".
        return [CheckResult("qa-sweep", False,
                            "qa_sweep.sh --verbose produced no check lines:\n"
                            + proc.output)]
    return results


def sweep_check_names() -> set[str]:
    return {r.name for r in sweep_results()}


def run_all(overlay: Path | str | None = None,
            capability_tests: list[str] | None = None) -> VerifyReport:
    """
    The whole verification sweep, in the order Section 6.8 specifies.

      1. check_agent_tools.py      the tracked pre-flight — the fastest check,
                                   and the one most likely to catch a generated
                                   agent's defect, so it runs before the rest
      2. qa_sweep.sh               the ten plus build-registration
      3. the three --overlay passes
      4. the capability's own tests
      5. test_action_provenance.py

    `overlay` may be None, in which case the overlay passes are skipped and the
    report carries only the tracked ones — which is what a REPAIR job with no
    new files needs, and what the name-set test runs against.
    """
    py = _python()
    results: list[CheckResult] = []

    # 1. Tracked pre-flight.
    results.append(_run("agent-tools",
                        [py, "scripts/check_agent_tools.py", "--quiet"]))
    if not results[-1].ok:
        return VerifyReport(results)

    # 2. The sweep. Its own `agent-tools` line is DROPPED, not re-recorded: it
    # is the same check on the same tree as step 1, and two entries under one
    # name would make the set comparison below meaningless.
    results.extend(r for r in sweep_results() if r.name != "agent-tools")

    # 3. The overlay passes.
    if overlay is not None:
        target = str(overlay)
        results.append(_run("agent-tools" + OVERLAY_SUFFIX,
                            [py, "scripts/check_agent_tools.py", "--quiet",
                             "--overlay", target]))
        results.append(_run("rule-overlap" + OVERLAY_SUFFIX,
                            [py, "scripts/check_rule_overlap.py", "--overlay", target]))
        results.append(_run("knowledge-domains" + OVERLAY_SUFFIX,
                            [py, "scripts/check_knowledge_domains.py",
                             "--overlay", target]))
        results.append(_run("build-registration" + OVERLAY_SUFFIX,
                            [py, "scripts/check_build_registration.py",
                             "--overlay", target]))

    # knowledge-domains on the TRACKED tree. The sweep does not run it, which is
    # exactly why it is an ADDED check rather than a shared one.
    results.append(_run("knowledge-domains",
                        [py, "scripts/check_knowledge_domains.py"]))

    # 4. The capability's own tests.
    results.append(_capability_tests(py, capability_tests))

    # 5. Provenance.
    results.append(_run("action-provenance",
                        [py, "tests/test_action_provenance.py"]))
    return VerifyReport(results)


def _capability_tests(py: str, tests: list[str] | None) -> CheckResult:
    """
    The tests the plan declared for this capability.

    An empty list FAILS. A capability lands with tests or it does not land: the
    whole argument for letting a machine build capabilities is that each one
    arrives with its own evidence, and "none declared" is the quietest way for
    that to stop being true.
    """
    if not tests:
        return CheckResult("capability-tests", False,
                           "the plan declared no tests — a capability lands with "
                           "its own evidence or it does not land")
    outputs, ok = [], True
    for test in tests:
        result = _run("capability-tests", [py, test])
        ok = ok and result.ok
        outputs.append(f"--- {test} ({'pass' if result.ok else 'FAIL'}) ---\n"
                       f"{result.output}")
    return CheckResult("capability-tests", ok, "\n".join(outputs))


def assert_same_checks(report: VerifyReport | None = None) -> list[str]:
    """
    The two equalities. Returns findings; empty means the claim holds.

    Proves the claim rather than asserting it — the sweep is actually run and
    its names compared, so this cannot pass on a stale list.
    """
    report = report or run_all()
    findings: list[str] = []

    sweep = sweep_check_names()
    if sweep != set(SHARED_CHECKS):
        missing = sorted(sweep - set(SHARED_CHECKS))
        extra = sorted(set(SHARED_CHECKS) - sweep)
        if missing:
            findings.append(
                f"qa_sweep.sh runs {missing}, which SHARED_CHECKS does not name — "
                "a landing would be verified against fewer checks than the sweep")
        if extra:
            findings.append(
                f"SHARED_CHECKS names {extra}, which qa_sweep.sh no longer runs")

    shared_seen = {r.base for r in report.results if r.base in SHARED_CHECKS}
    if shared_seen != sweep:
        findings.append(
            f"verify ran shared checks {sorted(shared_seen)}, the sweep ran "
            f"{sorted(sweep)}")

    added_seen = {r.base for r in report.results if r.base in ADDED_CHECKS}
    if added_seen != set(ADDED_CHECKS):
        findings.append(
            f"verify ran added checks {sorted(added_seen)}, declared "
            f"{sorted(ADDED_CHECKS)}")

    orphans = sorted(report.base_names() - set(SHARED_CHECKS) - set(ADDED_CHECKS))
    if orphans:
        findings.append(
            f"verify ran {orphans}, which is in neither SHARED_CHECKS nor "
            "ADDED_CHECKS — every check belongs to one declared set")
    return findings
