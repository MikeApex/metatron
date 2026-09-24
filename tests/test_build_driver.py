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


# ---------------------------------------------------------------------------
# THE SEND-BACK IS A STEP THE DRIVER HANDS OUT (phase C, review finding 1)
#
# Phase A had no code path for it at all: with a plan version, brief.md and
# review.json on disk the walk offered [N9] — the approval gate — on a plan the
# review had just rejected. The transition lived only in prose, which is the
# thing the control layer was salvaged into Python to prevent.
# ---------------------------------------------------------------------------

def _through_review(versions: int = 1) -> None:
    _fresh()
    J.write_artifact(JOB, "question_set", F.question_set(), PERSONA)
    J.write_artifact(JOB, "answer_ledger", F.answer_ledger(), PERSONA)
    J.write_artifact(JOB, "ledger_check", {"interview_items": []}, PERSONA)
    for _n in range(versions):
        J.write_plan(JOB, F.build_plan(), PERSONA)
    J.write_text(JOB, "brief.md", "# brief\n", PERSONA)
    J.write_artifact(JOB, "review", {"structural": [{"title": "x"}]}, PERSONA)


@check("without a send-back the driver offers [N9] on a REJECTED plan")
def _():
    _through_review()
    assert D.next_step(JOB, PERSONA).node == "N9", (
        "this is the phase-A behaviour the send-back exists to correct, and it "
        "is asserted so the correction cannot be quietly undone")


@check("send_back() rewinds the cursor and the DRIVER then names N7")
def _():
    _through_review()
    step = D.send_back(JOB, PERSONA, ["a broken sequence"])
    assert step.node == "N7" and step.kind == "agent", step
    assert step.agent == "build-planner", step
    assert not J.artifact_path(JOB, "brief.md", PERSONA).exists()
    assert not J.has_artifact(JOB, "review", PERSONA)
    assert D.rejections(JOB, PERSONA) == 1


@check("N7 is NOT done while a plan is outstanding against a rejection")
def _():
    _through_review()
    assert D.next_step(JOB, PERSONA).node == "N9"
    D.send_back(JOB, PERSONA, ["x"])
    assert D.next_step(JOB, PERSONA).node == "N7", "one version, one rejection"
    J.write_plan(JOB, F.build_plan(), PERSONA)
    assert D.next_step(JOB, PERSONA).node == "N10", "two versions, one rejection"


@check("the SECOND send-back parks BEFORE a planner is named or anything deleted")
def _():
    _through_review(versions=2)
    D.record(JOB, D.Step("N8", "agent"), "rejected", ["first"], PERSONA)
    step = D.send_back(JOB, PERSONA, ["second"])
    assert step.kind == "parked", step
    assert J.artifact_path(JOB, "brief.md", PERSONA).exists(), (
        "a parked job keeps its brief — that is the moment someone has to read "
        "it, and deleting first would spend a planner call past the bound")
    assert len(J.plan_versions(JOB, PERSONA)) == 2, (
        "no v3 was written: the bound fired before the planner ran")


@check("a send-back plan that FAILS validation is bounded like any other node")
def _():
    _through_review()
    D.send_back(JOB, PERSONA, ["x"])
    step = D.next_step(JOB, PERSONA)
    assert step.node == "N7"
    D.record(JOB, step, "failed", ["spine is not ordered"], PERSONA)
    again = D.next_step(JOB, PERSONA)
    assert again.node == "N7" and again.attempt == 2, again
    D.record(JOB, again, "failed", ["still not ordered"], PERSONA)
    assert D.next_step(JOB, PERSONA).kind == "parked", (
        "the re-plan gets ONE retry like every other subagent node — phase C's "
        "first attempt left it the only node with no per-node bound")


# ---------------------------------------------------------------------------
# THE DURABLE PARK (phase C, review finding 2)
# ---------------------------------------------------------------------------

@check("park() outranks every other state and survives a restart")
def _():
    _fresh()
    D.park(JOB, "N11", "a channel refused the worktree", PERSONA,
           paths=["channel (b): .env changed"])
    step = D.next_step(JOB, PERSONA)
    assert step.kind == "parked" and step.node == "N11", step
    assert "channel refused" in step.detail, step
    assert step.defects == ["channel (b): .env changed"], step

    for name in ("core.build.driver", "core.build.jobs"):
        sys.modules.pop(name, None)
    jobs2 = importlib.import_module("core.build.jobs")
    jobs2.jobs_root = lambda: _TMP / "jobs"              # type: ignore[assignment]
    driver2 = importlib.import_module("core.build.driver")
    assert driver2.next_step(JOB, PERSONA).kind == "parked", (
        "a boundary violation that only stopped the session would be retried "
        "by the next one")
    globals()["J"] = jobs2
    globals()["D"] = driver2


@check("only unpark() clears a park — no node outcome does")
def _():
    _fresh()
    D.park(JOB, "N11", "refused", PERSONA)
    J.write_artifact(JOB, "question_set", F.question_set(), PERSONA)
    assert D.next_step(JOB, PERSONA).kind == "parked", (
        "progress elsewhere must not clear a boundary violation")
    assert D.unpark(JOB, PERSONA) is True
    assert D.next_step(JOB, PERSONA).kind != "parked"


# ---------------------------------------------------------------------------
# begin() — which nodes cost an attempt row (phase C, review finding 6)
# ---------------------------------------------------------------------------

@check("begin() records a SUBAGENT node and nothing else")
def _():
    _fresh()
    D.begin(JOB, D.Step("N2", "agent", agent="build-inquiry"), PERSONA)
    D.begin(JOB, D.Step("N5", "code"), PERSONA)
    D.begin(JOB, D.Step("N9", "gate"), PERSONA)
    rows = J.attempts(JOB, PERSONA)
    assert [r["node"] for r in rows] == ["N2"], (
        "a started row at every node spends 9 of 16 before anything fails, and "
        "a recorded gate lets re-entering [N9] park a healthy job: " + str(rows))


@check("a whole construct job with one send-back and two retries stays under the cap")
def _():
    _fresh()
    for node in ("N2", "N4", "N7", "N8", "N11"):
        D.begin(JOB, D.Step(node, "agent"), PERSONA)
    for node in ("N7", "N8"):
        D.begin(JOB, D.Step(node, "agent"), PERSONA)
    for node in ("N2", "N11"):
        J.record_attempt(JOB, node, 1, "failed", ["x"], PERSONA)
        D.begin(JOB, D.Step(node, "agent", attempt=2), PERSONA)
    total = len(J.attempts(JOB, PERSONA))
    assert total < D.MAX_ATTEMPTS_PER_JOB, (
        f"{total} rows of {D.MAX_ATTEMPTS_PER_JOB} — a legitimate job must not "
        "park at the retry product cap")


# ---------------------------------------------------------------------------
# land() — one landing rule per node, in code (phase C, review finding 3)
# ---------------------------------------------------------------------------

@check("land() sends N7 through write_plan, which is what the counter globs")
def _():
    _fresh()
    J.write_artifact(JOB, "question_set", F.question_set(), PERSONA)
    J.write_artifact(JOB, "answer_ledger", F.answer_ledger(), PERSONA)
    J.write_artifact(JOB, "ledger_check", {"interview_items": []}, PERSONA)
    step = D.next_step(JOB, PERSONA)
    assert step.node == "N7"
    artifact, defects = D.land(
        JOB, step, F.build_plan(), PERSONA, upstream=F.answer_ledger(),
        red_paths=F.red_paths(), question_ids=F.question_ids())
    assert not defects, defects
    assert [p.name for p in J.plan_versions(JOB, PERSONA)] == ["build_plan.v1.json"], (
        "a plain write_artifact lands build_plan.json, which plan_versions() "
        "does not glob — so N7 reads as never-done and the send-back counter "
        "counts nothing")
    assert D.next_step(JOB, PERSONA).node == "N10"


@check("land() records the defects on a failure, so the retry carries them")
def _():
    _fresh()
    step = D.next_step(JOB, PERSONA)
    bad = F.question_set()
    bad["spine"] = list(reversed(bad["spine"]))
    artifact, defects = D.land(JOB, step, bad, PERSONA, upstream={},
                               known_capabilities=F.CAPABILITIES)
    assert artifact is None and defects, defects
    assert D.next_step(JOB, PERSONA).defects == defects


@check("land() writes a CODE node's artifact without touching a validator")
def _():
    _fresh()
    J.write_artifact(JOB, "question_set", F.question_set(), PERSONA)
    J.write_artifact(JOB, "answer_ledger", F.answer_ledger(), PERSONA)
    step = D.next_step(JOB, PERSONA)
    assert step.node == "N5"
    _artifact, defects = D.land(JOB, step, {"interview_items": []}, PERSONA)
    assert not defects
    assert J.has_artifact(JOB, "ledger_check", PERSONA), (
        "climb() has three validators and raises KeyError on any other kind, "
        "so a code node must never go through it")


@check("land() writes brief and patch as TEXT, under the names the cursor reads")
def _():
    _fresh()
    D.land(JOB, D.Step("N10", "code", artifact="brief"), "# a brief\n", PERSONA)
    D.land(JOB, D.Step("N11", "agent", artifact="implementation"),
           "diff --git a/x b/x\n", PERSONA)
    assert J.artifact_path(JOB, "brief.md", PERSONA).exists()
    assert J.artifact_path(JOB, "implementation.patch", PERSONA).exists()


# ---------------------------------------------------------------------------
# tree_split — one repository, two checkouts (phase C, review finding 10)
# ---------------------------------------------------------------------------

@check("two roots sharing ONE git common dir are refused as a split landing")
def _():
    real_root = D._ROOT
    try:
        # A second path inside this same repository stands in for the real
        # case — /build run from `metatron-wt-*` while the landing targets the
        # main tree. What tree_split() actually compares is the git COMMON DIR,
        # which two worktrees of one repo share and two unrelated repos do not,
        # so this exercises the branch that fires there.
        D._ROOT = Path(ROOT) / "core"                         # type: ignore
        refusals = D.tree_split(Path(ROOT))
    finally:
        D._ROOT = real_root                                   # type: ignore
    assert refusals and "two checkouts of one repository" in refusals[0], refusals


@check("the LIVE worktree case refuses, when this suite is run from one")
def _():
    main = Path("/Users/md-homefolder/Desktop/multi-model-mcp")
    if not main.exists() or main.resolve() == D._ROOT:
        return          # running in the main tree; the check above covers the branch
    refusals = D.tree_split(main)
    assert refusals, (
        "this suite is running from a worktree of that repo, so a landing into "
        "it would split the job store from the patch and must refuse")


@check("a landing into an UNRELATED repository is not refused — a fixture tree")
def _():
    unrelated = _TMP / "unrelated"
    unrelated.mkdir(exist_ok=True)
    import subprocess
    subprocess.run(["git", "init", "-q"], cwd=str(unrelated), capture_output=True)
    assert D.tree_split(unrelated) == [], (
        "every landing suite uses a temp git repo as its main tree; refusing "
        "those would make this check impossible to test and it would be removed")


@check("the same tree is never a split")
def _():
    assert D.tree_split(D._ROOT) == []


# ---------------------------------------------------------------------------
# finish_landing — the N13 sequence, in one call (phase C, review finding 4)
# ---------------------------------------------------------------------------

@check("finish_landing runs the CONTENT gate, not only the wiring checks")
def _():
    import core.build.verify as V
    seen = {}

    def fake_wiring(main_tree, capability, files):
        seen["wiring"] = capability
        return V.Report(results=[V.CheckResult("build-registration", True)])

    def fake_content(plan, ledger, agent_text):
        seen["content"] = agent_text
        return []

    import core.build.registry as R
    real = (V.wiring_gate, V.content_gate_for, R.mark_landed)
    V.wiring_gate, V.content_gate_for = fake_wiring, fake_content
    R.mark_landed = lambda name, path=None: {"name": name, "status": "landed"}
    try:
        _fresh()
        ok, lines = D.finish_landing(JOB, Path(ROOT), F.build_plan(), {},
                                     "# agent\n", PERSONA)
    finally:
        V.wiring_gate, V.content_gate_for, R.mark_landed = real

    assert ok, lines
    assert seen.get("wiring") == "home_care", seen
    assert seen.get("content") == "# agent\n", (
        "the content gate is the one a four-step prose sequence loses — it is "
        "last, it reads inputs nothing else needs, and skipping it looks "
        "exactly like passing it")
    assert lines and lines[0].startswith("git add "), lines


@check("a red gate PARKS the landing and prints the revert, never the manifest")
def _():
    import core.build.verify as V
    import core.build.registry as R
    real = (V.wiring_gate, V.content_gate_for, R.mark_landed)
    V.wiring_gate = lambda m, c, f: V.Report(
        results=[V.CheckResult("build-registration", False, "no routing entry")])
    V.content_gate_for = lambda p, l, a: []
    R.mark_landed = lambda name, path=None: {"name": name, "status": "landed"}
    try:
        _fresh()
        ok, lines = D.finish_landing(JOB, Path(ROOT), F.build_plan(), {},
                                     "# agent\n", PERSONA)
    finally:
        V.wiring_gate, V.content_gate_for, R.mark_landed = real

    assert not ok
    assert not any(l.startswith("git add ") for l in lines), (
        "a staging manifest printed beside a red gate is the time_director "
        f"shape reaching a commit: {lines}")
    assert any("git checkout HEAD --" in l for l in lines), lines
    assert D.next_step(JOB, PERSONA).kind == "parked"


def _cleanup() -> None:
    shutil.rmtree(_TMP, ignore_errors=True)


_cleanup()
suite.exit()
