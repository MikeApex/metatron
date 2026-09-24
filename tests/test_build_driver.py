"""
tests/test_build_driver.py — the control layer's bounds hold across a restart.

Plan section 12, Driver row: a node that fails validation is retried exactly
once, then the job parks; a second review send-back parks; a job at a gate state
yields no step; a job whose N2 and N4 artifacts exist resumes at N7 with no step
for either; THE COUNTS ARE RE-DERIVED FROM attempts.jsonl AFTER THE PROCESS IS
RESTARTED, including a failed node that wrote no artifact (finding 1, verify
residual 1).

THE RESTART IS THE POINT, AND IT IS WHY THIS SUITE USES A REAL DIRECTORY rather
than mocks. A retry counter that lives in a process is a counter that resets on
exactly the crash that makes a job expensive. Every assertion below therefore
runs `next_step()` cold — no state carried, nothing but the files on disk — and
the "after a restart" checks re-import the module to prove it.

Usage:
    python3 tests/test_build_driver.py
"""

import importlib
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.build import driver as D                       # noqa: E402
from core.build import jobs as J                         # noqa: E402
from tests.support import build_fixtures as F            # noqa: E402
from tests.support.runner import Suite                   # noqa: E402

suite = Suite("build driver")
check = suite.check

JOB = F.JOB_ID
PERSONA = F.PERSONA

_TMP = Path(tempfile.mkdtemp(prefix="build-driver-"))


def _redirect() -> None:
    """Point the job root at a temp directory. Restored by _cleanup()."""
    J.jobs_root = lambda: _TMP / "jobs"                  # type: ignore[assignment]


def _fresh() -> None:
    """A job directory with nothing in it — the state at `/build BLD-…`."""
    target = _TMP / "jobs"
    if target.exists():
        shutil.rmtree(target)
    J.ensure(JOB, PERSONA)


_redirect()


# ---------------------------------------------------------------------------
# The cursor
# ---------------------------------------------------------------------------

@check("a fresh job's first step is N2 Inquiry")
def _():
    _fresh()
    step = D.next_step(JOB, PERSONA)
    assert step.node == "N2", step
    assert step.kind == "agent" and step.agent == "build-inquiry", step


@check("N1r is skipped on a construct job and named first on a repair")
def _():
    _fresh()
    assert D.next_step(JOB, PERSONA, mode="construct").node == "N2"
    assert D.next_step(JOB, PERSONA, mode="repair").node == "N1r"


@check("a job whose N2 and N4 artifacts exist resumes at N7, with no step for either")
def _():
    _fresh()
    J.write_artifact(JOB, "question_set", F.question_set(), PERSONA)
    J.write_artifact(JOB, "answer_ledger", F.answer_ledger(), PERSONA)
    J.write_artifact(JOB, "ledger_check", {"interview_items": []}, PERSONA)
    step = D.next_step(JOB, PERSONA)
    assert step.node == "N7", (
        "the artifact IS the cursor — a node whose output is on disk must not be "
        f"named again: {step}")


@check("an artifact that does not parse is debris, and its node runs again")
def _():
    _fresh()
    J.ensure(JOB, PERSONA)
    J.artifact_path(JOB, "question_set", PERSONA).write_text("{ truncated",
                                                             encoding="utf-8")
    assert D.next_step(JOB, PERSONA).node == "N2", (
        "a half-written file cannot have come from os.replace() of a complete "
        "write, so it is debris and not a cursor")


# ---------------------------------------------------------------------------
# The gates
# ---------------------------------------------------------------------------

@check("a job at a gate state yields NO step — only the gate")
def _():
    _fresh()
    J.write_artifact(JOB, "question_set", F.question_set(), PERSONA)
    J.write_artifact(JOB, "answer_ledger", F.answer_ledger(), PERSONA)
    J.write_artifact(JOB, "ledger_check",
                     {"interview_items": [{"question_id": "q1"}]}, PERSONA)
    step = D.next_step(JOB, PERSONA)
    assert step.node == "N6" and step.kind == "gate", step
    assert step.is_gate and "in chat" in step.detail, step


@check("answering the interview clears the gate and N7 is named")
def _():
    _fresh()
    J.write_artifact(JOB, "question_set", F.question_set(), PERSONA)
    J.write_artifact(JOB, "answer_ledger", F.answer_ledger(), PERSONA)
    J.write_artifact(JOB, "ledger_check",
                     {"interview_items": [{"question_id": "q1"}],
                      "answered": True}, PERSONA)
    assert D.next_step(JOB, PERSONA).node == "N7"


@check("a written brief with no approval parks at [N9] and names no node")
def _():
    _fresh()
    J.write_artifact(JOB, "question_set", F.question_set(), PERSONA)
    J.write_artifact(JOB, "answer_ledger", F.answer_ledger(), PERSONA)
    J.write_artifact(JOB, "ledger_check", {"interview_items": []}, PERSONA)
    J.write_plan(JOB, F.build_plan(), PERSONA)
    J.write_text(JOB, "brief.md", "# brief", PERSONA)
    J.write_artifact(JOB, "review", {"structural": [], "local": []}, PERSONA)
    step = D.next_step(JOB, PERSONA)
    assert step.node == "N9" and step.kind == "gate", step


# ---------------------------------------------------------------------------
# One retry per node, counted from the durable rows
# ---------------------------------------------------------------------------

@check("a node that fails validation is retried EXACTLY ONCE")
def _():
    _fresh()
    first = D.next_step(JOB, PERSONA)
    assert first.attempt == 1, first
    D.record(JOB, first, "failed", ["spine is not ordered by class index"], PERSONA)

    second = D.next_step(JOB, PERSONA)
    assert second.node == "N2" and second.attempt == 2, second
    assert second.defects == ["spine is not ordered by class index"], (
        "rung 2's retry carries the DEFECT LIST, not a re-ask: " + str(second))


@check("the SECOND failure parks the job, and says one retry is the bound")
def _():
    _fresh()
    for _n in range(2):
        step = D.next_step(JOB, PERSONA)
        D.record(JOB, step, "failed", ["spine is not ordered"], PERSONA)
    step = D.next_step(JOB, PERSONA)
    assert step.kind == "parked", step
    assert "one retry per node is the bound" in step.detail, step
    assert step.defects, "a parked job must carry the defects that parked it"


@check("THE COUNTS SURVIVE A RESTART — re-imported cold, the park still holds")
def _():
    _fresh()
    for _n in range(2):
        step = D.next_step(JOB, PERSONA)
        D.record(JOB, step, "failed", ["spine is not ordered"], PERSONA)

    # The actual restart: drop both modules and re-import, so nothing in this
    # process could be remembering the count.
    for name in ("core.build.driver", "core.build.jobs"):
        sys.modules.pop(name, None)
    jobs2 = importlib.import_module("core.build.jobs")
    jobs2.jobs_root = lambda: _TMP / "jobs"              # type: ignore[assignment]
    driver2 = importlib.import_module("core.build.driver")

    step = driver2.next_step(JOB, PERSONA)
    assert step.kind == "parked", (
        "the park was held in memory, not on disk — a lost session would reset "
        f"it and the bound would be unbounded: {step}")
    # Restore this module's view for the remaining checks.
    globals()["J"] = jobs2
    globals()["D"] = driver2


@check("A FAILED NODE THAT WROTE NO ARTIFACT STILL COUNTS")
def _():
    _fresh()
    step = D.next_step(JOB, PERSONA)
    D.record(JOB, step, "failed", ["unparseable JSON"], PERSONA)
    assert not J.has_artifact(JOB, "question_set", PERSONA), (
        "this check is only meaningful if the node really wrote nothing")
    assert J.attempts_for(JOB, "N2", PERSONA) == 1, (
        "the artifacts alone cannot see this attempt — which is exactly why "
        "attempts.jsonl exists (finding 1)")
    assert D.next_step(JOB, PERSONA).attempt == 2


@check("the attempt row is written BEFORE the step runs, so a crash counts")
def _():
    _fresh()
    step = D.next_step(JOB, PERSONA)
    row = D.record(JOB, step, "started", None, PERSONA)
    assert row["outcome"] == "started", row
    assert J.attempts_for(JOB, "N2", PERSONA) == 1, (
        "recording after the fact would make a crash free, and a crash loop "
        "free forever")


# ---------------------------------------------------------------------------
# The review's one send-back
# ---------------------------------------------------------------------------

def _plan_through_review(versions: int) -> None:
    _fresh()
    J.write_artifact(JOB, "question_set", F.question_set(), PERSONA)
    J.write_artifact(JOB, "answer_ledger", F.answer_ledger(), PERSONA)
    J.write_artifact(JOB, "ledger_check", {"interview_items": []}, PERSONA)
    for _n in range(versions):
        J.write_plan(JOB, F.build_plan(), PERSONA)


@check("one send-back is allowed — v2 is written and the graph continues")
def _():
    _plan_through_review(2)
    assert len(J.plan_versions(JOB, PERSONA)) == 2
    step = D.next_step(JOB, PERSONA)
    assert step.node == "N10", (
        "after a send-back the graph goes back through the table and the "
        f"review, not straight to the implementer: {step}")


@check("a SECOND send-back parks the job for Mike")
def _():
    _plan_through_review(3)
    step = D.next_step(JOB, PERSONA)
    assert step.kind == "parked", step
    assert "sent the plan back" in step.detail, step


@check("the send-back count is the plan files on disk, with no counter anywhere")
def _():
    _plan_through_review(2)
    names = [p.name for p in J.plan_versions(JOB, PERSONA)]
    assert names == ["build_plan.v1.json", "build_plan.v2.json"], names
    assert J.next_plan_name(JOB, PERSONA) == "build_plan.v3.json"


# ---------------------------------------------------------------------------
# The retry product cap
# ---------------------------------------------------------------------------

@check("the retry PRODUCT is capped from the durable rows")
def _():
    _fresh()
    step = D.next_step(JOB, PERSONA)
    for _n in range(D.MAX_ATTEMPTS_PER_JOB):
        J.record_attempt(JOB, "N2", 1, "failed", [], PERSONA)
    parked = D.next_step(JOB, PERSONA)
    assert parked.kind == "parked", parked
    assert "retry product cap" in parked.detail, parked


# ---------------------------------------------------------------------------
# What the driver will never do
# ---------------------------------------------------------------------------

@check("the driver issues NO staging verb in a worktree")
def _():
    issued = D.git_log(Path("."))
    for verb in ("add", "commit", "stash"):
        assert verb not in issued, (
            f"{verb!r} in a worktree would fire hook_commit_guard's watched "
            f"verbs, whichever process ran it: {issued}")


@check("the staging manifest names explicit paths, never `git add .`")
def _():
    manifest = D.staging_manifest(["tools/home_care.py", "config/agents/home_care.md"])
    assert manifest.startswith("git add tools/home_care.py"), manifest
    assert " ." not in manifest and "-A" not in manifest, manifest


@check("patch_paths() reads the patch, not the tree")
def _():
    patch = (
        "diff --git a/tools/home_care.py b/tools/home_care.py\n"
        "--- a/tools/home_care.py\n+++ b/tools/home_care.py\n"
        "diff --git a/dev/null b/tests/test_home_care.py\n"
        "--- /dev/null\n+++ b/tests/test_home_care.py\n")
    assert D.patch_paths(patch) == {"tools/home_care.py",
                                    "tests/test_home_care.py"}


def _cleanup() -> None:
    shutil.rmtree(_TMP, ignore_errors=True)


_cleanup()
suite.exit()
