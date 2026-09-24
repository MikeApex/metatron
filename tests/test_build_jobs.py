"""
tests/test_build_jobs.py — the job directory, and the two guarantees it makes.

Plan section 5. The artifact is the resume cursor, and the write that makes
that trustworthy is atomic: a reader sees the whole old file or the whole new
one, never a half-written prefix.

WHY PERSONA QUALIFICATION IS TESTED HERE AND NOT ONLY IN tickets. Two personas
can mint the same BLD-MMDD-NN on one day (cold read 5). If the JOB directory
were not qualified, the second would resume into the first's artifacts and build
the wrong capability from a cursor that looked entirely valid.

Usage:
    python3 tests/test_build_jobs.py
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.build import jobs as J                         # noqa: E402
from tests.support import build_fixtures as F            # noqa: E402
from tests.support.runner import Suite                   # noqa: E402

suite = Suite("build jobs")
check = suite.check

_TMP = Path(tempfile.mkdtemp(prefix="build-jobs-"))
J.jobs_root = lambda: _TMP / "jobs"                      # type: ignore


def _reset() -> None:
    shutil.rmtree(_TMP / "jobs", ignore_errors=True)
    J.ensure(F.JOB_ID, F.PERSONA)


# ---------------------------------------------------------------------------
# Persona qualification
# ---------------------------------------------------------------------------

@check("the same job id under two personas is two directories")
def _():
    _reset()
    a = J.job_dir(F.JOB_ID, "persona_a")
    b = J.job_dir(F.JOB_ID, "persona_b")
    assert a != b, (a, b)
    assert a.parent.name == "persona_a" and b.parent.name == "persona_b"


@check("no persona resolves to `mike`, never to a shared root")
def _():
    assert J.resolve_persona(None) == "mike"
    assert J.job_dir(F.JOB_ID).parent.name == "mike"


@check("a malformed persona name is REFUSED; only CASE is folded")
def _():
    for bad in ("../escape", "a" * 40, "a/b", "mike.2"):
        try:
            J.resolve_persona(bad)
        except J.JobError:
            continue
        raise AssertionError(f"{bad!r} was accepted — a name with a slash or a "
                             "`..` is not a typo, and rewriting one would put a "
                             "job in a directory its caller did not name")
    assert J.resolve_persona("Mike") == "mike", (
        "case IS folded, and that is the safe direction on a case-insensitive "
        "filesystem: refusing `Mike` while `Mike/` and `mike/` would be one "
        "directory anyway buys nothing")
    assert J.resolve_persona("") == J.resolve_persona(None) == "mike", (
        "an empty string is UNSPECIFIED, the same as no flag — every other "
        "resolver in this repo reads it that way, and a special case here "
        "would be the one place `--persona ''` meant something different")


@check("a malformed job id is refused before any path is built")
def _():
    try:
        J.job_dir("DB-0924-01", F.PERSONA)
    except J.JobError as exc:
        assert "Not a Build job id" in str(exc), exc
        return
    raise AssertionError("a backlog id was accepted as a job id")


# ---------------------------------------------------------------------------
# Artifacts
# ---------------------------------------------------------------------------

@check("an artifact round-trips, and `.json` is appended when absent")
def _():
    _reset()
    path = J.write_artifact(F.JOB_ID, "question_set", F.question_set(), F.PERSONA)
    assert path.name == "question_set.json", path
    assert J.read_artifact(F.JOB_ID, "question_set", F.PERSONA)["job_id"] == F.JOB_ID


@check("a name carrying a KNOWN suffix keeps it — brief.md is not brief.md.json")
def _():
    _reset()
    for name, expected in (("brief.md", "brief.md"),
                           ("implementation.patch", "implementation.patch"),
                           ("build_plan.v1.json", "build_plan.v1.json"),
                           ("answer_ledger", "answer_ledger.json")):
        assert J.artifact_path(F.JOB_ID, name, F.PERSONA).name == expected, name


@check("a VERSIONED plan name keeps its .json — the send-back counter reads it")
def _():
    _reset()
    J.write_plan(F.JOB_ID, F.build_plan(), F.PERSONA)
    J.write_plan(F.JOB_ID, F.build_plan(), F.PERSONA)
    names = [p.name for p in J.plan_versions(F.JOB_ID, F.PERSONA)]
    assert names == ["build_plan.v1.json", "build_plan.v2.json"], (
        "a name written without .json would be invisible to the v* glob, and "
        f"the review's one send-back would be unbounded: {names}")


@check("plan versions sort by NUMBER, not by string — v10 follows v9")
def _():
    _reset()
    for _n in range(11):
        J.write_plan(F.JOB_ID, F.build_plan(), F.PERSONA)
    names = [p.name for p in J.plan_versions(F.JOB_ID, F.PERSONA)]
    assert names[-1] == "build_plan.v11.json", names


@check("an unparseable artifact reads as None — debris, not a cursor")
def _():
    _reset()
    J.artifact_path(F.JOB_ID, "question_set", F.PERSONA).write_text(
        "{ truncated", encoding="utf-8")
    assert J.read_artifact(F.JOB_ID, "question_set", F.PERSONA) is None
    assert not J.has_artifact(F.JOB_ID, "question_set", F.PERSONA)


@check("a JSON list is not a dict, so it does not count as an artifact")
def _():
    _reset()
    J.artifact_path(F.JOB_ID, "question_set", F.PERSONA).write_text(
        "[1, 2, 3]", encoding="utf-8")
    assert J.read_artifact(F.JOB_ID, "question_set", F.PERSONA) is None


@check("the write is ATOMIC — no .tmp survives a completed write")
def _():
    _reset()
    J.write_artifact(F.JOB_ID, "question_set", F.question_set(), F.PERSONA)
    leftovers = list(J.job_dir(F.JOB_ID, F.PERSONA).glob("*.tmp"))
    assert not leftovers, leftovers


@check("artifacts are written 0600 — the ledger carries verbatim answers")
def _():
    _reset()
    path = J.write_artifact(F.JOB_ID, "answer_ledger", F.answer_ledger(), F.PERSONA)
    assert path.stat().st_mode & 0o777 == 0o600, oct(path.stat().st_mode)


@check("an invalid artifact name is refused, never cleaned")
def _():
    for bad in ("../escape", "Question_Set", "", "a/b"):
        try:
            J.artifact_path(F.JOB_ID, bad, F.PERSONA)
        except J.JobError:
            continue
        raise AssertionError(f"{bad!r} was accepted as an artifact name")


# ---------------------------------------------------------------------------
# attempts.jsonl
# ---------------------------------------------------------------------------

@check("attempts accumulate and are counted per node")
def _():
    _reset()
    J.record_attempt(F.JOB_ID, "N2", 1, "failed", ["bad order"], F.PERSONA)
    J.record_attempt(F.JOB_ID, "N2", 2, "done", None, F.PERSONA)
    J.record_attempt(F.JOB_ID, "N4", 1, "done", None, F.PERSONA)
    assert J.attempts_for(F.JOB_ID, "N2", F.PERSONA) == 2
    assert J.attempts_for(F.JOB_ID, "N4", F.PERSONA) == 1
    assert J.failures_for(F.JOB_ID, "N2", F.PERSONA) == 1


@check("the most recent defect list is what a retry carries")
def _():
    _reset()
    J.record_attempt(F.JOB_ID, "N2", 1, "failed", ["first"], F.PERSONA)
    J.record_attempt(F.JOB_ID, "N2", 2, "failed", ["second"], F.PERSONA)
    assert J.last_defects(F.JOB_ID, "N2", F.PERSONA) == ["second"]


@check("a torn attempts line is skipped, and the counts survive")
def _():
    _reset()
    J.record_attempt(F.JOB_ID, "N2", 1, "failed", [], F.PERSONA)
    path = J.attempts_path(F.JOB_ID, F.PERSONA)
    path.write_text(path.read_text() + '{"node": "N4"\n', encoding="utf-8")
    J.record_attempt(F.JOB_ID, "N2", 2, "done", [], F.PERSONA)
    assert J.attempts_for(F.JOB_ID, "N2", F.PERSONA) == 2


@check("known_jobs lists the directories on disk, newest id first")
def _():
    _reset()
    J.ensure("BLD-0924-02", F.PERSONA)
    J.ensure("BLD-0923-01", F.PERSONA)
    assert J.known_jobs(F.PERSONA) == ["BLD-0924-02", F.JOB_ID, "BLD-0923-01"]


@check("the job root is under data/build/, which .gitignore covers")
def _():
    real = Path(__file__).resolve().parent.parent / "data" / "build" / "jobs"
    import importlib
    fresh = importlib.reload(importlib.import_module("core.build.jobs"))
    assert fresh.jobs_root() == real, fresh.jobs_root()
    lines = {ln.strip() for ln in
             (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()}
    assert "data/build/" in lines, (
        "the answer ledger carries verbatim interview answers; without this "
        "line it is committable")
    fresh.jobs_root = lambda: _TMP / "jobs"              # type: ignore


def _cleanup() -> None:
    shutil.rmtree(_TMP, ignore_errors=True)


try:
    code = suite.report()
finally:
    _cleanup()
sys.exit(code)
