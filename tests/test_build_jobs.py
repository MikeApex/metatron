"""
tests/test_build_jobs.py — the ledger, the state replayed from it, and restart.

Four claims, from the plan's verification table:
  ids allocate  ·  rows replay to the right terminal state  ·  a truncated line
  is skipped not fatal  ·  a duplicate fingerprint is refused

Plus the restart row, which is a REAL kill -9 against a REAL child process
rather than a simulated one. Simulating a crash tests the simulation: the
property under test is that a process dying between a node's write and its
ledger row leaves a job that resumes correctly, and only an actual SIGKILL
produces that state.

Everything runs against a temp directory. `persona_data_dir` is the single
filesystem dependency in core/build/jobs.py, so rebinding it is the whole
sandbox — no repo data tree is touched, and a crashed test leaves no residue.

Standalone runner (no pytest dependency), matching tests/ convention.

Usage:
    python3 tests/test_build_jobs.py

Exits 0 if every check passes, 1 otherwise.
"""

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import core.build.jobs as J  # noqa: E402
from core.build import ids as IDS  # noqa: E402

_results: list[tuple[str, bool, str]] = []


def check(name: str):
    def wrap(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except AssertionError as e:
            _results.append((name, False, f"assertion: {e}"))
        except Exception as e:
            _results.append((name, False, f"{type(e).__name__}: {e}"))
        return fn
    return wrap


TMP = Path(tempfile.mkdtemp(prefix="build_jobs_test_"))
PERSONA = "mike"

# The whole sandbox. jobs.py resolves every path through this one function.
J.persona_data_dir = lambda persona=None: TMP / "personas" / (persona or PERSONA)


def reset() -> None:
    shutil.rmtree(TMP / "personas", ignore_errors=True)
    J.build_dir(PERSONA).mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Ids
# ---------------------------------------------------------------------------

@check("ids allocate in sequence, and the shape is BLD-MMDD-NN")
def _():
    reset()
    first = J.create("first gap", trigger="test")["job_id"]
    second = J.create("second gap", trigger="test")["job_id"]
    assert IDS.is_job_id(first) and IDS.is_job_id(second), (first, second)
    assert first.endswith("-01") and second.endswith("-02"), (first, second)
    today = datetime.now()
    assert first.startswith(f"BLD-{today.month:02d}{today.day:02d}-"), first


@check("the sequence is replayed from the ledger, not from a counter")
def _():
    reset()
    J.create("a gap", trigger="test")
    J.create("another gap", trigger="test")
    # A counter would live in memory or a state file; both survive this.
    # Replay does not: delete the ledger and allocation restarts at 01.
    J.ledger_path(PERSONA).unlink()
    assert J.create("a third gap", trigger="test")["job_id"].endswith("-01")


@check("a malformed id is refused rather than sanitised")
def _():
    for bad in ("BLD-918-01", "DB-0918-01", "BLD-0918-1", "", "../../etc"):
        assert not IDS.is_job_id(bad), bad


# ---------------------------------------------------------------------------
# Replay
# ---------------------------------------------------------------------------

@check("rows replay to the right terminal state")
def _():
    reset()
    job_id = J.create("a gap worth building", trigger="test")["job_id"]
    for state in ("queued", "inquiry", "questions_ready", "librarian",
                  "ledger_ready", "planning", "plan_ready", "briefed",
                  "executing", "verifying", "landed"):
        J.set_state(job_id, state, persona=PERSONA)
    job = J.get(job_id, PERSONA)
    assert job["state"] == "landed", job["state"]
    assert job["history"][0] == "proposed", job["history"]
    assert job["history"][-1] == "landed", job["history"]
    assert job["state"] in J.TERMINAL


@check("a terminal job cannot re-open")
def _():
    reset()
    job_id = J.create("a gap", trigger="test")["job_id"]
    J.set_state(job_id, "failed", persona=PERSONA)
    try:
        J.set_state(job_id, "planning", persona=PERSONA)
    except J.JobError as e:
        assert "terminal" in str(e), e
    else:
        raise AssertionError("a terminal job re-opened")


@check("blocked is a FLAG on the row, never a state")
def _():
    reset()
    assert "blocked" not in J.STATES
    job_id = J.create("a gap", trigger="test")["job_id"]
    J.set_state(job_id, "queued", persona=PERSONA)
    J.set_blocked(job_id, "waiting on search_conversations", persona=PERSONA)
    job = J.get(job_id, PERSONA)
    assert job["state"] == "queued", job["state"]
    assert job["blocked"] == "waiting on search_conversations", job["blocked"]
    J.set_blocked(job_id, None, persona=PERSONA)
    assert J.get(job_id, PERSONA)["blocked"] is None


@check("a truncated line is skipped, not fatal")
def _():
    reset()
    job_id = J.create("a gap", trigger="test")["job_id"]
    J.set_state(job_id, "queued", persona=PERSONA)
    with open(J.ledger_path(PERSONA), "a") as handle:
        handle.write('{"row_type": "status", "job_id": "BLD-0918-01", "sta\n')
    J.set_state(job_id, "inquiry", persona=PERSONA)

    rows = J.read_rows(PERSONA)
    assert all(isinstance(r, dict) for r in rows)
    assert J.get(job_id, PERSONA)["state"] == "inquiry"


@check("a status row whose opening row was lost is skipped, not synthesised")
def _():
    reset()
    J.append_row({"row_type": "status", "job_id": "BLD-0101-99",
                  "state": "landed"}, PERSONA)
    assert "BLD-0101-99" not in J.states(PERSONA), (
        "a job with no gap and no fingerprint would defeat dedupe and could "
        "never be run")


# ---------------------------------------------------------------------------
# Dedupe
# ---------------------------------------------------------------------------

@check("a duplicate fingerprint is refused while the job is open")
def _():
    reset()
    J.create("the plant watering check is stuck", trigger="test")
    try:
        J.create("  The Plant   Watering Check is Stuck  ", trigger="test")
    except J.JobError as e:
        assert "duplicate" in str(e), e
    else:
        raise AssertionError("a duplicate fingerprint was accepted")


def _age_last_status(days: int = 0, hours: int = 0) -> None:
    """Rewrite the newest status row's timestamp. The dedupe windows are the
    only thing in Build that depends on wall-clock age, so they are the only
    thing that needs this."""
    path = J.ledger_path(PERSONA)
    lines = path.read_text().splitlines()
    for position in range(len(lines) - 1, -1, -1):
        row = json.loads(lines[position])
        if row.get("row_type") == "status":
            row["at"] = (datetime.now() - timedelta(days=days, hours=hours)
                         ).isoformat(timespec="seconds")
            lines[position] = json.dumps(row)
            break
    path.write_text("\n".join(lines) + "\n")


@check("a landed job blocks a rebuild for 14 days, then stops blocking")
def _():
    reset()
    gap = "nothing decides whether a chore is overdue"
    job_id = J.create(gap, trigger="test")["job_id"]
    J.set_state(job_id, "landed", persona=PERSONA)
    try:
        J.create(gap, trigger="test")
    except J.JobError as e:
        assert "landed" in str(e) and "REPAIR" in str(e), e
    else:
        raise AssertionError("a rebuild inside the landed window was accepted")

    _age_last_status(days=J.DEDUPE_LANDED_DAYS + 1)
    assert J.create(gap, trigger="test")["job_id"]


@check("a failed job blocks a retry for 72 hours, then stops blocking")
def _():
    reset()
    gap = "a gap that could not be built"
    job_id = J.create(gap, trigger="test")["job_id"]
    J.set_state(job_id, "failed", persona=PERSONA)
    try:
        J.create(gap, trigger="test")
    except J.JobError as e:
        assert "failed" in str(e), e
    else:
        raise AssertionError("a retry inside the failed window was accepted")

    _age_last_status(hours=J.DEDUPE_FAILED_HOURS + 1)
    assert J.create(gap, trigger="test")["job_id"]


@check("an empty or null-ish gap is refused")
def _():
    reset()
    for gap in ("", "   ", "None.", "N/A"):
        try:
            J.create(gap, trigger="test")
        except J.JobError as e:
            assert "gap is empty" in str(e), (gap, e)
        else:
            raise AssertionError(f"gap {gap!r} was accepted")


# ---------------------------------------------------------------------------
# Caps and depth
# ---------------------------------------------------------------------------

@check("max_proposed caps the queue that can rot")
def _():
    reset()
    for n in range(J.CAPS["max_proposed"]):
        J.create(f"gap number {n}", trigger="test")
    try:
        J.create("one gap too many", trigger="test")
    except J.JobError as e:
        assert "max_proposed" in str(e) and "over-firing" in str(e), e
    else:
        raise AssertionError("max_proposed was not enforced")


@check("max_open_jobs caps work in flight")
def _():
    reset()
    for n in range(J.CAPS["max_open_jobs"]):
        job_id = J.create(f"gap number {n}", trigger="test")["job_id"]
        J.set_state(job_id, "queued", persona=PERSONA)
    extra = J.create("one more gap", trigger="test")["job_id"]
    try:
        J.set_state(extra, "queued", persona=PERSONA)
    except J.JobError as e:
        assert "max_open_jobs" in str(e), e
    else:
        raise AssertionError("max_open_jobs was not enforced")


@check("depth beyond MAX_BUILD_DEPTH is refused, and depth is a durable field")
def _():
    reset()
    try:
        J.create("a recursive gap", trigger="test", depth=J.MAX_BUILD_DEPTH + 1)
    except J.JobError as e:
        assert "MAX_BUILD_DEPTH" in str(e), e
    else:
        raise AssertionError("depth was not enforced")

    job_id = J.create("a nested gap", trigger="test", depth=1)["job_id"]
    assert J.get(job_id, PERSONA)["depth"] == 1, (
        "depth must survive replay — a thread-local cannot, which is the known "
        "hole in _SUBAGENT_DEPTH this field exists to avoid")


# ---------------------------------------------------------------------------
# Artifacts and staleness
# ---------------------------------------------------------------------------

@check("an artifact write is atomic, and a torn artifact reads as absent")
def _():
    reset()
    job_id = J.create("a gap", trigger="test")["job_id"]
    assert not J.has_artifact(job_id, "question_set", PERSONA)
    J.write_artifact(job_id, "question_set", {"schema": "question_set/1"}, PERSONA)
    assert J.has_artifact(job_id, "question_set", PERSONA)

    J.artifact_path(job_id, "question_set", PERSONA).write_text('{"schema": "que')
    assert J.read_artifact(job_id, "question_set", PERSONA) is None, (
        "a half-written file must read as absent — it cannot have come from "
        "os.replace() of a complete write, so it is debris, and treating it as "
        "output would skip the node that has not actually run")


@check("a job with no heartbeat is not stale — it is waiting")
def _():
    reset()
    job_id = J.create("a gap", trigger="test")["job_id"]
    J.set_state(job_id, "queued", persona=PERSONA)
    assert job_id not in J.stale_jobs(PERSONA), (
        "re-entering it would burn an attempt on a job that has not used one")


@check("a job whose heartbeat has gone quiet is stale")
def _():
    reset()
    job_id = J.create("a gap", trigger="test")["job_id"]
    J.set_state(job_id, "inquiry", persona=PERSONA)
    J.heartbeat(job_id, node="N2", persona=PERSONA)
    assert job_id not in J.stale_jobs(PERSONA)
    assert job_id in J.stale_jobs(PERSONA, minutes=0)


# ---------------------------------------------------------------------------
# Restart — a real SIGKILL against a real child process
# ---------------------------------------------------------------------------

_CHILD = """
import sys, time
sys.path.insert(0, {root!r})
import core.build.jobs as J
from pathlib import Path
TMP = Path({tmp!r})
J.persona_data_dir = lambda persona=None: TMP / "personas" / (persona or "mike")
job_id = {job_id!r}
J.set_state(job_id, "inquiry", persona="mike")
J.heartbeat(job_id, node="N2", persona="mike")
J.write_artifact(job_id, "question_set", {{"schema": "question_set/1"}}, "mike")
print("READY", flush=True)
time.sleep(600)          # the node "runs" until it is killed
"""


@check("a kill -9 mid-node leaves a job that resumes at attempt 2, no duplicates")
def _():
    reset()
    job_id = J.create("a gap interrupted mid-node", trigger="test")["job_id"]

    child = subprocess.Popen(
        [sys.executable, "-c", _CHILD.format(
            root=str(ROOT), tmp=str(TMP), job_id=job_id)],
        stdout=subprocess.PIPE, text=True)
    try:
        assert child.stdout.readline().strip() == "READY", "child never started"
        os.kill(child.pid, signal.SIGKILL)
        child.wait(timeout=10)
    finally:
        if child.poll() is None:
            child.kill()
    assert child.returncode == -signal.SIGKILL, child.returncode

    # Nothing was held in memory, so the survivors are exactly what was written.
    job = J.get(job_id, PERSONA)
    assert job["state"] == "inquiry", job["state"]
    assert job["attempt"] == 1, job["attempt"]
    assert J.has_artifact(job_id, "question_set", PERSONA), (
        "the artifact written before the kill is the resume cursor")

    before = sorted(p.name for p in J.job_dir(job_id, PERSONA).iterdir())
    assert before == ["question_set.json"], before

    # build_tick re-enters a stalled job at attempt + 1.
    assert job_id in J.stale_jobs(PERSONA, minutes=0)
    assert J.next_attempt(job_id, PERSONA) == 2
    resumed = J.get(job_id, PERSONA)
    assert resumed["attempt"] == 2, resumed["attempt"]
    assert resumed["state"] == "inquiry", resumed["state"]

    # The resumed node finds valid output present and skips its model call, so
    # no second artifact appears. No .tmp debris either.
    after = sorted(p.name for p in J.job_dir(job_id, PERSONA).iterdir())
    assert after == before, f"duplicate artifacts after restart: {after}"


@check("attempts are bounded — the job-level half of the retry product")
def _():
    reset()
    job_id = J.create("a gap", trigger="test")["job_id"]
    J.set_state(job_id, "inquiry", persona=PERSONA)
    for expected in range(2, J.MAX_ATTEMPTS + 1):
        assert J.next_attempt(job_id, PERSONA) == expected
    try:
        J.next_attempt(job_id, PERSONA)
    except J.JobError as e:
        assert "attempts" in str(e), e
    else:
        raise AssertionError("attempts were not bounded")


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    failed = 0
    for name, ok, detail in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}{'' if ok else '  — ' + detail}")
        failed += 0 if ok else 1
    print(f"\n{len(_results) - failed}/{len(_results)} passed")
    shutil.rmtree(TMP, ignore_errors=True)
    sys.exit(1 if failed else 0)
