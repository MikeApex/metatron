"""
core/build/verify.py — THE SAME CHECKS, NOT EQUIVALENTS.

Plan: archive/plans/build_vertical_plan_2026-09-24.md section 3 (N12, N13).

Nothing here is a reimplementation: this module SHELLS OUT to the same scripts
the sweep runs, with cwd set to whichever tree is being checked, so a check that
drifts in qa_sweep.sh drifts here in the same direction on the same day.

TWO TREES, TWO DIFFERENT SETS, AND THE SPLIT IS THE WHOLE DESIGN (cold read 2).

  N12, IN THE SANDBOX WORKTREE — CODE CHECKS ONLY. The capability's own tests, a
  py-compile over files[], and the full sweep. What it deliberately does NOT run
  is the content gates on the agent file or check_build_registration.py: the
  agent file, the routing entries and the Coordinator lines are Red and are NOT
  IN THAT TREE BY DESIGN. A registration check there would fail on wiring that
  is correctly absent.

  N13, IN THE MAIN TREE — THE WIRING GATE. After the patch and the Red half are
  both in, the capability-scoped checks run where both halves exist. This is the
  ONLY point in the pipeline where the routing entries, the Coordinator lines,
  the agent file and the code are in one tree before a commit — so it is the
  only point the `time_director` shape (an agent file and a consequence line
  with no routing entry) can be caught by a check rather than by a reader.

SCOPED, NOT WHOLESALE (round 3, NEW 2). The wiring gate runs the
CAPABILITY-SCOPED checks — the registration checker for this capability,
`check_agent_tools.py --agent <name>`, a py-compile over files[]. The full sweep
runs too and is reported BESIDE the manifest as ADVISORY: an unrelated red
another chat left in a shared tree is named, never withholds, because the gate
attributes by dirtiness and cannot tell whose fault it is —
hook_subagent_gate.py's own recorded limit.

THE SIXTH GATE IS THE TIER GATE, and it is here rather than at N12 for the
same reason: it reads the routing entry, which is Red and does not exist in the
sandbox. A capability that does standing judgement over a history on the bulk
tier is refused — see core/build/gates.check_tier() for the measured precedent.

WHY --agent AND NOT THE HOOK. `check_agent_tools.py --agent <name>` is the
script's own scoping flag. The diff-scoped behaviour belongs to the PostToolUse
hook `hook_agent_tools.py`, which exits 0 by design and therefore cannot gate
anything (verify round 4).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent

CHECK_TIMEOUT = 600


@dataclass
class CheckResult:
    name: str
    ok: bool
    output: str = ""

    @property
    def line(self) -> str:
        return f"{self.name} {'ok' if self.ok else 'FAIL'}"


@dataclass
class Report:
    results: list[CheckResult] = field(default_factory=list)
    advisory: list[CheckResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """ADVISORY RESULTS DO NOT COUNT. That is what advisory means here."""
        return all(r.ok for r in self.results)

    @property
    def failures(self) -> list[CheckResult]:
        return [r for r in self.results if not r.ok]

    @property
    def advisory_failures(self) -> list[CheckResult]:
        return [r for r in self.advisory if not r.ok]

    def summary(self) -> str:
        lines = [", ".join(r.line for r in self.results) or "no checks ran"]
        for result in self.advisory_failures:
            lines.append(
                f"advisory: {result.name} is red in this tree. Reported, not "
                "withheld — the gate attributes by dirtiness and cannot tell "
                "whose it is.")
        return " | ".join(lines)


def _run(name: str, args: list[str], tree: Path) -> CheckResult:
    try:
        proc = subprocess.run(args, cwd=str(tree), capture_output=True,
                              text=True, timeout=CHECK_TIMEOUT)
    except (OSError, subprocess.SubprocessError) as exc:
        # FAIL CLOSED. A check that could not be run is not a check that passed.
        return CheckResult(name, False, f"could not run: {exc}")
    return CheckResult(name, proc.returncode == 0,
                       (proc.stdout + proc.stderr).strip())


def _python(tree: Path) -> str:
    venv = tree / ".venv" / "bin" / "python"
    return str(venv) if venv.exists() else "python3"


# ---------------------------------------------------------------------------
# N12 — the sandbox worktree. Code checks only.
# ---------------------------------------------------------------------------

def code_checks(worktree: Path, files: list[str],
                tests: list[str]) -> Report:
    """
    The capability's own tests, a py-compile over files[], then the full sweep.

    The sweep is a REAL check here, not advisory: this is Build's own sandbox,
    nobody else is in it, so a red sweep is Build's.
    """
    report = Report()
    python = _python(worktree)

    compilable = [f for f in files if f.endswith(".py")]
    if compilable:
        report.results.append(
            _run("py-compile", [python, "-m", "py_compile", *compilable], worktree))

    for test in tests:
        report.results.append(_run(f"test:{Path(test).name}",
                                   [python, test], worktree))

    report.results.append(
        _run("qa_sweep", ["bash", str(worktree / "scripts" / "qa_sweep.sh")],
             worktree))
    return report


# ---------------------------------------------------------------------------
# N13 — the main tree. The wiring gate.
# ---------------------------------------------------------------------------

def wiring_gate(main_tree: Path, capability: str, files: list[str]) -> Report:
    """
    The capability-scoped checks, plus the sweep as advisory.

    A red here PARKS THE JOB, nothing is staged, and the driver prints the
    failing check and the exact per-file revert line. A red in the ADVISORY
    sweep does neither: it is named beside the manifest and the manifest is
    still printed.
    """
    report = Report()
    python = _python(main_tree)

    report.results.append(_run(
        "build-registration",
        [python, "scripts/check_build_registration.py", "--capability", capability],
        main_tree))
    report.results.append(_run(
        "agent-tools",
        [python, "scripts/check_agent_tools.py", "--agent", capability],
        main_tree))

    compilable = [f for f in files if f.endswith(".py")]
    if compilable:
        report.results.append(
            _run("py-compile", [python, "-m", "py_compile", *compilable], main_tree))

    report.advisory.append(
        _run("qa_sweep", ["bash", str(main_tree / "scripts" / "qa_sweep.sh")],
             main_tree))
    return report


def content_gate(agent_text: str, record: dict, granted: list[str],
                 read_set: set[str], risks: list,
                 peers: dict[str, str] | None = None,
                 plan: dict | None = None, ledger: dict | None = None) -> list[str]:
    """
    The content gates over the generated agent file, its record and its TIER.

    ALL OF THEM RUN AT N13 RATHER THAN N12, for one reason: every input they
    read is Red. The agent file is not in the sandbox worktree, and neither is
    the routing entry the tier gate reads — so at N12 the tier gate would find
    no entry, match nothing, and pass on every capability. A gate that always
    passes is worse than no gate, because it reads as coverage.

    `plan` and `ledger` are optional only so a caller checking prose alone can
    omit them; the driver always has both by N13 and always passes them.
    """
    from core.build import constitution, gates

    defects: list[str] = []
    defects += constitution.check(agent_text, record)
    defects += gates.check_names(str(record.get("name") or ""),
                                 str(record.get("display_name") or ""), peers)
    defects += gates.check_grants_declared(granted, read_set, risks)
    if plan is not None and ledger is not None:
        defects += gates.check_tier(plan, ledger)
    return defects
