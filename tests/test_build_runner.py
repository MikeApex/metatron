"""
tests/test_build_runner.py — the driver: gates, restart, budget, trace, REPAIR.

FOUR OF THE PLAN'S SECTION 12 ROWS LIVE HERE, and each is tested as the claim it
makes rather than as the code it happens to be:

  · RESTART — "a node that finds valid output already present skips its model
    call". Asserted by COUNTING MODEL CALLS, not by checking a return value: the
    claim is about a call not happening, and only a counter can see that.
  · BUDGET — limit 0.01, run a job, and it parks at `awaiting_approval` having
    never reached N10. Asserted by the absence of brief.md, because "never
    started N10" is a fact about a file that does not exist.
  · TRACE CONTRACT — the three agents NESTED under one RequestTrace. The nesting
    half only; the Book-rendering criterion is phase 7's, and this cannot fake
    it.
  · END TO END — request_build -> tick -> board -> brief, with a redacted brief
    at the end of it.

The model is stubbed throughout. The stub does exactly what
core/orchestrator._run_single_agent does around its provider call — push_agent,
record_turn_tokens, pop_agent — so the trace nesting and the cost seam are
exercised for real while no token is bought.

Standalone runner, no pytest, matching tests/ convention.

Usage:
    python3 tests/test_build_runner.py
"""

import json
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import core.build.cost as COST      # noqa: E402
import core.build.jobs as J         # noqa: E402
import core.build.registry as R     # noqa: E402
import core.build.runner as RUN     # noqa: E402
import core.trace as T              # noqa: E402

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


TMP = Path(tempfile.mkdtemp(prefix="build_runner_test_"))
PERSONA = "mike"


def _data_dir(persona=None):
    return TMP / "personas" / (persona or PERSONA)


J.persona_data_dir = _data_dir
R.persona_data_dir = _data_dir

# ---------------------------------------------------------------------------
# THE SUITE MUST NOT TOUCH A LIVE METER. Found the hard way, 2026-09-19.
# ---------------------------------------------------------------------------
#
# The model stub below calls trace.record_turn_tokens() and the runner writes a
# RequestTrace per tick — both on purpose, because that is what makes the cost
# seam and the nesting assertions real rather than simulated. But both of those
# paths end in LIVE state:
#
#   · record_turn_tokens -> spend_guard.record_tokens -> data/diagnostics/
#     spend_YYYY-MM-DD.json. Fake tokens at 40k a call added ~13M tokens and
#     $12.53 to this machine's real daily total and TRIPPED THE $15 DAILY STOP,
#     so check_before_session() then refused every subsequent node — the suite
#     failed 15 of its own tests by spending its own budget, and would have
#     blocked a real local session too.
#   · finish_request_trace -> data/personas/{p}/traces/. 112 fake records landed
#     in the live trace file, which is what turn_referent reads for "the
#     previous turn" and what the analytics rollup derives from.
#
# So all three live writes are redirected here, ONCE, for the whole module. The
# metering that the tests actually assert on is core.build.cost's per-job
# ledger, which already lives in the sandbox.
_spend_calls: list[tuple] = []


def _fake_record_tokens(model, tokens_in, tokens_out, tokens_cached=0):
    _spend_calls.append((model, tokens_in, tokens_out))


def _fake_check_before_session():
    """Never raises. One test drives the blocked path explicitly instead."""
    return None


import core.spend_guard as SG                                      # noqa: E402

SG.record_tokens = _fake_record_tokens
SG.check_before_session = _fake_check_before_session
T._write = lambda data, persona: None


def reset() -> None:
    shutil.rmtree(TMP / "personas", ignore_errors=True)
    J.build_dir(PERSONA).mkdir(parents=True, exist_ok=True)
    CALLS.clear()


def _limit(value: float | None) -> None:
    """Point cost.py at a temp build.yaml carrying (or omitting) a limit."""
    path = TMP / "build.yaml"
    path.write_text("" if value is None else f"budget:\n  per_job_usd: {value}\n")
    COST._CONFIG_PATH = path


# ---------------------------------------------------------------------------
# The model stub
# ---------------------------------------------------------------------------

CALLS: list[str] = []

# Sized so ONE call costs more than the $0.01 limit section 12 names —
# roughly what a real Librarian pass reads. A stub billing a fraction of a
# cent would make the budget test pass by never reaching the tripwire.
TOKENS_IN, TOKENS_OUT = 40_000, 2_000

# Canned outputs, keyed by agent. Each is the shape its node's validator
# demands, minus the header fields code injects — which is the point: if the
# runner stopped injecting them, every one of these would fail validation.
_CANNED = {
    "build_inquiry": {
        "schema": "question_set/1", "mode": "construct", "depth": "standard",
        "request": "nothing owns 'is this household thing overdue'",
        "disposition": "new",
        "disposition_evidence": "logistics owns actions, not standing checks",
        "generalizes_to": "any recurring home obligation with a last-done date",
        "policies_consulted": [], "framing_note": "",
        "declined_to_ask": [],
        # The sources are chosen to exercise all three of settle's outcomes in
        # one run: a behavioural source (residue -> the Librarian), a
        # single_point one, and a question only the user can answer (the [N6]
        # gate). A spine that named only "user" would park every job at
        # needs_interview and no test below would ever reach the Planner.
        "spine": [
            {"id": "q1", "class": "intent", "text": "What is this in service of?",
             "why_it_matters": "it sets the altitude", "blocks": "design",
             "expected_answer_shape": "a sentence", "candidate_sources": ["log"],
             "resolved_by_policy": None},
            {"id": "q2", "class": "surface",
             "text": "What else operates on a watering once it exists?",
             "why_it_matters": "edges nobody enumerates", "blocks": "design",
             "expected_answer_shape": "a list", "candidate_sources": ["wisdom"],
             "resolved_by_policy": None},
            {"id": "q3", "class": "authority",
             "text": "What is decided here versus surfaced?",
             "why_it_matters": "silence must still produce an outcome",
             "blocks": "behaviour", "expected_answer_shape": "a default",
             "candidate_sources": ["user"], "resolved_by_policy": None},
        ],
    },
    # One judgment row per question the residue carried (q1, q2). The
    # code-written block is deliberately ABSENT: N3 owns those fields and N5
    # re-injects them, so a Librarian that supplied them would be overruled.
    "build_librarian": {
        "schema": "answer_ledger/1",
        "rows": [
            {"question_id": "q1", "answerable_by": "judgment",
             "data_kind": "behavioural", "has_what_it_needs": True,
             "decision": "treat a cadence judgement as the capability",
             "decision_options": ["a cadence judgement", "a watering-specific tool"],
             "assumption": "every recurring home obligation has a last-done date",
             "assumption_falsifier": "an obligation logged with no date at all"},
            {"question_id": "q2", "answerable_by": "judgment",
             "data_kind": "behavioural", "has_what_it_needs": True,
             "decision": "read only; no writes to the obligation store",
             "decision_options": ["read only", "read and close the obligation"],
             "assumption": "closing is logistics' job, not this one's",
             "assumption_falsifier": "a user asking it to mark something done"},
        ],
        "interview_items": [], "variable_proposals": [],
        # "n/a" as a reason is REFUSED by the validator — it is null-ish, the
        # same class as the USER_CORRECTION slot that produced "None." ninety
        # times. A real reason is the point of the field.
        "surface_map": [{"entity": "watering", "operation": op,
                         "status": "in_scope" if op == "read" else "not_applicable",
                         "reason": "this capability reads a log and decides; it "
                                   "never mutates the obligation store"}
                        for op in ("create", "read", "update", "delete", "move",
                                   "dedupe", "merge", "expire", "reconcile")],
    },
    "build_planner": {
        "schema": "build_plan/1",
        "capability": {"id": "home_care", "kind": "agent", "one_line": "upkeep",
                       "disposition": "new",
                       "disposition_evidence": "no specialist does cadence judgement",
                       "generalizes_to": "recurring home obligations",
                       "execution_mode": "blocking", "latency_budget_ms": 8000,
                       "replaces": []},
        # "n/a" as a reason is REFUSED by the validator — it is null-ish, the
        # same class as the USER_CORRECTION slot that produced "None." ninety
        # times. A real reason is the point of the field.
        "surface_map": [{"entity": "watering", "operation": op,
                         "status": "in_scope" if op == "read" else "not_applicable",
                         "reason": "this capability reads a log and decides; it "
                                   "never mutates the obligation store"}
                        for op in ("create", "read", "update", "delete", "move",
                                   "dedupe", "merge", "expire", "reconcile")],
        "files": ["data/personas/mike/build/overlay/agents/home_care.md"],
        # An agent plan with no registration item is refused — that is the
        # time_director half-wiring the one-record design exists to end. The
        # grants are what the brief's "what it may read" section reads.
        "registration": [{"kind": "overlay_capability", "name": "home_care",
                          "routing": {"local": {"local": True,
                                                "allowed_tools": ["get_log_window",
                                                                  "get_weather"]},
                                      "cloud": {"model_ref": "logistics",
                                                "allowed_tools": ["get_log_window",
                                                                  "get_weather"]}}}],
        "tests": ["tests/test_home_care.py"],
        "variables": [], "risks": [],
        # Required because a planned file writes under data/. Requirement 3:
        # any new state must be rebuildable, with no retrofit of the ~25
        # existing whole-file writers.
        "state_record": {"rebuild_from": "the day logs it reads; it stores nothing "
                                         "of its own"},
    },
}


def _canned_for(agent_name: str) -> dict:
    """
    The canned artifact, with the Planner's file path pointed at THIS sandbox.

    It has to be resolved at call time: the writer's allow-roots come from the
    patched J.build_dir(), so a path hardcoded at `data/personas/mike/...` is
    refused by the deny list — correctly, because it names the real tree. The
    planner's own dry-run check is what catches that, which is the check doing
    exactly its job.
    """
    canned = _CANNED.get(agent_name, {"advisory": "looks fine"})
    if agent_name == "build_planner" and "capability" in canned:
        overlay = J.build_dir(PERSONA) / "overlay" / "agents" / "home_care.md"
        canned = {**canned, "files": [str(overlay)]}
    return canned


def fake_agent(agent_name, user_input, persona=None, **kwargs):
    """
    Stands in for core/orchestrator._run_single_agent, doing what it does around
    its provider call: push the agent record, report tokens, pop it.

    That is what makes the trace and cost assertions below real rather than
    simulated — the nesting and the metering both run through the live code.
    """
    CALLS.append(agent_name)
    record = T.push_agent(agent_name, "stub", "gemini-3.8-flash")
    try:
        T.record_turn_tokens(record, 1, TOKENS_IN, TOKENS_OUT)
    finally:
        T.pop_agent(record)
    return json.dumps(_canned_for(agent_name))


def install_stub() -> None:
    import core.orchestrator as O
    O._run_single_agent = fake_agent


install_stub()


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------

@check("a filed job lands at `proposed` and the tick will not touch it")
def _():
    reset()
    job_id = J.create("a gap", trigger="test")["job_id"]
    out = RUN.tick(PERSONA)
    assert "nothing runnable" in out, out
    assert J.get(job_id, PERSONA)["state"] == "proposed"
    assert CALLS == [], CALLS


@check("nothing resumes a gate by itself — every gate state stops advance()")
def _():
    for state in sorted(RUN.GATE_STATES - {"proposed"}):
        reset()
        job_id = J.create(f"a gap parked at {state}", trigger="test")["job_id"]
        J.set_state(job_id, "queued", persona=PERSONA)
        J.set_state(job_id, state, persona=PERSONA)
        outcomes = RUN.advance(job_id, PERSONA)
        assert outcomes and outcomes[0].status == "gate", (state, outcomes)
        assert CALLS == [], (state, CALLS)


@check("queue() is the only way off `proposed`, and it refuses a job already moved")
def _():
    reset()
    job_id = J.create("a gap", trigger="test")["job_id"]
    assert "queued" in RUN.queue(job_id, PERSONA)
    assert J.get(job_id, PERSONA)["state"] == "queued"
    assert "not proposed" in RUN.queue(job_id, PERSONA)


@check("[N9] approve refuses anything not at `briefed`; [N13] accept refuses anything not at `verifying`")
def _():
    reset()
    job_id = J.create("a gap", trigger="test")["job_id"]
    J.set_state(job_id, "queued", persona=PERSONA)
    assert "[N9] approves" in RUN.approve(job_id, PERSONA)
    assert "[N13] accepts" in RUN.accept(job_id, PERSONA)


# ---------------------------------------------------------------------------
# Restart — the section 12 row, asserted by counting calls
# ---------------------------------------------------------------------------

@check("a node whose artifact is present SKIPS ITS MODEL CALL — counted, not assumed")
def _():
    reset()
    job_id = J.create("a gap", trigger="test")["job_id"]
    J.set_state(job_id, "queued", persona=PERSONA)
    RUN.run_node(job_id, "N1 manifest", PERSONA)

    first = RUN.run_node(job_id, "N2 inquiry", PERSONA)
    assert first.status == "done", first
    assert CALLS == ["build_inquiry"], CALLS

    second = RUN.run_node(job_id, "N2 inquiry", PERSONA)
    assert second.status == "skipped", second
    assert CALLS == ["build_inquiry"], (
        "the second run called the model again — the resume cursor is not the state")


@check("a resumed job produces no duplicate artifact and no .tmp debris")
def _():
    reset()
    job_id = J.create("a gap", trigger="test")["job_id"]
    J.set_state(job_id, "queued", persona=PERSONA)
    RUN.run_node(job_id, "N1 manifest", PERSONA)
    RUN.run_node(job_id, "N2 inquiry", PERSONA)
    before = sorted(p.name for p in J.job_dir(job_id, PERSONA).iterdir())
    RUN.run_node(job_id, "N2 inquiry", PERSONA)
    after = sorted(p.name for p in J.job_dir(job_id, PERSONA).iterdir())
    assert before == after, (before, after)
    assert not [n for n in after if n.endswith(".tmp")], after


@check("a torn artifact reads as absent, so the node re-runs rather than trusting debris")
def _():
    reset()
    job_id = J.create("a gap", trigger="test")["job_id"]
    J.set_state(job_id, "queued", persona=PERSONA)
    RUN.run_node(job_id, "N1 manifest", PERSONA)
    RUN.run_node(job_id, "N2 inquiry", PERSONA)
    J.artifact_path(job_id, "question_set", PERSONA).write_text('{"spine": [', "utf-8")
    CALLS.clear()
    out = RUN.run_node(job_id, "N2 inquiry", PERSONA)
    assert out.status == "done" and CALLS == ["build_inquiry"], (out, CALLS)


def _age_heartbeat(job_id: str) -> None:
    """Rewrite the job's heartbeat rows into the distant past."""
    path = J.ledger_path(PERSONA)
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    for row in rows:
        if row.get("row_type") == "heartbeat" and row.get("job_id") == job_id:
            row["at"] = "2020-01-01T00:00:00"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")


@check("a stalled RUNNABLE job is re-entered at attempt + 1 by the tick, not by a daemon")
def _():
    reset()
    _limit(100.0)
    try:
        job_id = J.create("a gap", trigger="test")["job_id"]
        J.set_state(job_id, "queued", persona=PERSONA)
        J.heartbeat(job_id, node="N2 inquiry", persona=PERSONA)
        _age_heartbeat(job_id)
        assert job_id in J.stale_jobs(PERSONA)
        RUN.tick(PERSONA)
        assert J.get(job_id, PERSONA)["attempt"] == 2, J.get(job_id, PERSONA)
    finally:
        _limit(None)


@check("a job AT A GATE never accrues a stall attempt — a quiet heartbeat there is a human, not a crash")
def _():
    # Without this, a job waiting at `briefed` for two hours would burn all
    # MAX_ATTEMPTS at one bump per tick and fail because nobody read the brief.
    reset()
    _limit(100.0)
    try:
        job_id = J.create("a gap", trigger="test")["job_id"]
        J.set_state(job_id, "queued", persona=PERSONA)
        J.set_state(job_id, "briefed", persona=PERSONA)
        J.heartbeat(job_id, node="N10 brief", persona=PERSONA)
        _age_heartbeat(job_id)
        assert job_id in J.stale_jobs(PERSONA), "the fixture did not go stale"
        for _ in range(J.MAX_ATTEMPTS + 2):
            RUN.tick(PERSONA)
        job = J.get(job_id, PERSONA)
        assert job["attempt"] == 1, job["attempt"]
        assert job["state"] == "briefed", job["state"]
    finally:
        _limit(None)


# ---------------------------------------------------------------------------
# Budget — the section 12 row
# ---------------------------------------------------------------------------

@check("with the limit at 0.01 a job PARKS at awaiting_approval and never starts N10")
def _():
    reset()
    _limit(0.01)
    try:
        job_id = J.create("a gap", trigger="test")["job_id"]
        J.set_state(job_id, "queued", persona=PERSONA)
        outcomes = RUN.advance(job_id, PERSONA)
        job = J.get(job_id, PERSONA)
        assert job["state"] == "awaiting_approval", (job["state"], outcomes)
        assert any(o.status == "parked" for o in outcomes), outcomes
        # "Never started N10" is a fact about a file that does not exist.
        assert not (J.job_dir(job_id, PERSONA) / "brief.md").exists(), (
            "N10 ran past a tripped budget")
    finally:
        _limit(None)


@check("the spend the job is measured against came through core/trace's seam, not a second meter")
def _():
    reset()
    _limit(10.0)
    try:
        job_id = J.create("a gap", trigger="test")["job_id"]
        J.set_state(job_id, "queued", persona=PERSONA)
        RUN.run_node(job_id, "N1 manifest", PERSONA)
        RUN.run_node(job_id, "N2 inquiry", PERSONA)
        rows = COST.spend_rows(job_id, PERSONA)
        assert len(rows) == 1, rows
        assert rows[0]["tokens_in"] == TOKENS_IN, rows
        assert rows[0]["tokens_out"] == TOKENS_OUT, rows
        assert COST.job_spend(job_id, PERSONA) > 0, rows
    finally:
        _limit(None)


@check("resume() refuses while the job is still over its limit — it cannot become the approval")
def _():
    reset()
    _limit(0.01)
    try:
        job_id = J.create("a gap", trigger="test")["job_id"]
        J.set_state(job_id, "queued", persona=PERSONA)
        RUN.advance(job_id, PERSONA)
        assert "still over budget" in RUN.resume(job_id, PERSONA)
        assert "ON THE VM" in RUN.resume(job_id, PERSONA), (
            "the approval command must say which machine it runs on")
        COST.approve_limit(job_id, 50.0, PERSONA)
        parked_from = J.get(job_id, PERSONA)["resume_to"]
        assert "resumed at" in RUN.resume(job_id, PERSONA)
        # Back to where it was parked FROM, not to a fixed `planning`.
        assert J.get(job_id, PERSONA)["state"] == parked_from, parked_from
        assert J.get(job_id, PERSONA)["state"] not in J.TERMINAL
    finally:
        _limit(None)


@check("the placeholder notice leads a tick, and self-clears once a figure is configured")
def _():
    reset()
    _limit(None)
    job_id = J.create("a gap", trigger="test")["job_id"]
    J.set_state(job_id, "queued", persona=PERSONA)
    assert "PLACEHOLDER" in RUN.tick(PERSONA)
    reset()
    _limit(5.0)
    try:
        job_id = J.create("a gap", trigger="test")["job_id"]
        J.set_state(job_id, "queued", persona=PERSONA)
        assert "PLACEHOLDER" not in RUN.tick(PERSONA)
    finally:
        _limit(None)


@check("the attempt x retry PRODUCT is capped, and counted from durable spend rows")
def _():
    reset()
    _limit(1000.0)
    try:
        job_id = J.create("a gap", trigger="test")["job_id"]
        J.set_state(job_id, "queued", persona=PERSONA)
        # Twelve recorded calls: the cap, reached without this process having
        # counted anything — which is the property a restart must not reset.
        with COST.job_scope(job_id, PERSONA):
            for _ in range(RUN.MAX_MODEL_CALLS_PER_JOB):
                COST.record_job_tokens("gemini-3.8-flash", 10, 10)
        out = RUN.run_node(job_id, "N2 inquiry", PERSONA)
        assert out.status == "failed" and "cap" in out.detail, out
        assert J.get(job_id, PERSONA)["state"] == "failed"
    finally:
        _limit(None)


@check("a capped DAY flags the job blocked and leaves its state alone — blocked is not a state")
def _():
    # The guard is stubbed for the whole module so the suite cannot be stopped
    # by this machine's real daily spend. This is the one test that drives the
    # blocked path, so it is still exercised rather than merely stubbed away.
    reset()
    _limit(100.0)
    saved = SG.check_before_session

    def _capped():
        raise SG.SpendLimitExceeded(
            "Estimated AI spend today is $15.03, at or above the daily limit")

    SG.check_before_session = _capped
    try:
        job_id = J.create("a gap", trigger="test")["job_id"]
        J.set_state(job_id, "queued", persona=PERSONA)
        outcomes = RUN.advance(job_id, PERSONA)
        assert outcomes[-1].status == "blocked", outcomes
        job = J.get(job_id, PERSONA)
        # The STATE is untouched — blocked is a property of a job already
        # counted, never a new state. And the guard's own words never became an
        # agent's output, which is what would have landed them inside a Question
        # Set verbatim.
        assert job["state"] == "queued", job["state"]
        assert job["blocked"] and "spend guard" in job["blocked"], job
        assert CALLS == [], CALLS
    finally:
        SG.check_before_session = saved
        _limit(None)


@check("the block clears on the next node once the guard lets the job through")
def _():
    reset()
    _limit(100.0)
    try:
        job_id = J.create("a gap", trigger="test")["job_id"]
        J.set_state(job_id, "queued", persona=PERSONA)
        J.set_blocked(job_id, "daily spend guard: capped", PERSONA)
        assert J.get(job_id, PERSONA)["blocked"]
        RUN.run_node(job_id, "N1 manifest", PERSONA)
        assert not J.get(job_id, PERSONA)["blocked"], "a stale block survived"
    finally:
        _limit(None)


# ---------------------------------------------------------------------------
# Trace contract — the nesting half
# ---------------------------------------------------------------------------

@check("every tick is ONE request with its agents NESTED — never top-level siblings")
def _():
    reset()
    _limit(100.0)
    captured: list[dict] = []
    real_write = T._write          # the module-level stub, not the live writer
    T._write = lambda data, persona: captured.append(data)
    try:
        job_id = J.create("a gap", trigger="test")["job_id"]
        J.set_state(job_id, "queued", persona=PERSONA)
        RUN.tick(PERSONA)                       # -> inquiry, librarian, [N6]
        ledger = J.read_artifact(job_id, "answer_ledger", PERSONA)
        for item in ledger["interview_items"]:
            RUN.answer_interview(job_id, item["question_id"], "the garden only",
                                 PERSONA)
        RUN.tick(PERSONA)                       # -> planner, review, N10
    finally:
        T._write = real_write
        _limit(None)

    assert len(captured) == 2, f"each tick is one request, got {len(captured)}"
    nested: list[str] = []
    for record in captured:
        pipeline = record["pipeline"]
        assert len(pipeline) == 1, f"agents landed top-level, not nested: {pipeline}"
        assert pipeline[0]["agent"] == RUN.TRACE_ROOT_AGENT, pipeline[0]["agent"]
        assert record["is_proactive"] is True, "a tick is scheduler-initiated"
        nested += [a["agent"] for a in pipeline[0]["subagents"]]

    for agent in ("build_inquiry", "build_librarian", "build_planner"):
        assert agent in nested, (agent, nested)


@check("_SUBAGENT_DEPTH is restored after a tick, including when it was unset")
def _():
    import os
    reset()
    _limit(100.0)
    try:
        os.environ.pop("_SUBAGENT_DEPTH", None)
        RUN.tick(PERSONA)
        assert "_SUBAGENT_DEPTH" not in os.environ, os.environ.get("_SUBAGENT_DEPTH")
        os.environ["_SUBAGENT_DEPTH"] = "0"
        RUN.tick(PERSONA)
        assert os.environ["_SUBAGENT_DEPTH"] == "0", os.environ["_SUBAGENT_DEPTH"]
    finally:
        os.environ.pop("_SUBAGENT_DEPTH", None)
        _limit(None)


@check("an empty queue costs ZERO model calls and writes no trace")
def _():
    reset()
    captured: list[dict] = []
    real_write = T._write          # the module-level stub, not the live writer
    T._write = lambda data, persona: captured.append(data)
    try:
        out = RUN.tick(PERSONA)
    finally:
        T._write = real_write
    assert "nothing runnable" in out, out
    assert CALLS == [] and captured == [], (CALLS, captured)


# ---------------------------------------------------------------------------
# The pipeline, end to end
# ---------------------------------------------------------------------------

@check("END TO END: request_build -> tick -> board -> a redacted brief")
def _():
    reset()
    _limit(100.0)
    try:
        from tools import build as TB
        import core.build.brief as BR

        filed = TB.request_build.__wrapped__(  # noqa: SLF001 - see below
            "nothing owns 'is this household thing overdue'", "test") \
            if hasattr(TB.request_build, "__wrapped__") else \
            TB.request_build("nothing owns 'is this household thing overdue'", "test")
        assert "Filed as" in filed, filed
        job_id = filed.split("Filed as ")[1].split()[0]

        # A filed ticket is not queued work: the first tick must not touch it.
        assert "nothing runnable" in RUN.tick(PERSONA)
        RUN.queue(job_id, PERSONA)

        RUN.tick(PERSONA)
        assert J.get(job_id, PERSONA)["state"] == "needs_interview"
        ledger = J.read_artifact(job_id, "answer_ledger", PERSONA)
        for item in ledger["interview_items"]:
            RUN.answer_interview(job_id, item["question_id"], "the garden only",
                                 PERSONA)

        RUN.tick(PERSONA)
        job = J.get(job_id, PERSONA)
        assert job["state"] == "briefed", (job["state"], job.get("detail"))
        assert CALLS == ["build_inquiry", "build_librarian", "build_planner",
                         "build_planner"], CALLS

        # The board sees it and says what it is waiting for.
        sys.path.insert(0, str(ROOT / "scripts"))
        import build_board
        board = build_board.board(PERSONA)
        assert job_id in board and "read the brief" in board, board

        # The brief exists, is readable and carries the decisions section.
        body = (J.job_dir(job_id, PERSONA) / "brief.md").read_text(encoding="utf-8")
        assert "# Build brief" in body and "## Decisions taken" in body, body[:400]
        assert not BR.findings(body, PERSONA), BR.findings(body, PERSONA)
    finally:
        _limit(None)


@check("the Librarian is SKIPPED when settle left no residue — no call to adjudicate zero")
def _():
    reset()
    _limit(100.0)
    # A spine naming only "user": everything routes to the interview and nothing
    # reaches the Librarian. Calling a model to adjudicate zero questions is the
    # cost the node ordering exists to avoid, so the assertion is a call COUNT.
    saved = dict(_CANNED["build_inquiry"])
    _CANNED["build_inquiry"] = {
        **saved,
        "spine": [{**q, "candidate_sources": ["user"]} for q in saved["spine"]],
    }
    try:
        job_id = J.create("a gap", trigger="test")["job_id"]
        J.set_state(job_id, "queued", persona=PERSONA)
        RUN.advance(job_id, PERSONA)
        assert "build_librarian" not in CALLS, CALLS
        assert J.get(job_id, PERSONA)["state"] == "needs_interview"
        librarian = J.read_artifact(job_id, "librarian", PERSONA)
        assert "no residue" in librarian.get("skipped", ""), librarian
    finally:
        _CANNED["build_inquiry"] = saved
        _limit(None)


@check("interview items park the job, and answering the last one releases it")
def _():
    reset()
    _limit(100.0)
    try:
        job_id = J.create("a gap", trigger="test")["job_id"]
        J.set_state(job_id, "queued", persona=PERSONA)
        RUN.advance(job_id, PERSONA)
        job = J.get(job_id, PERSONA)
        assert job["state"] == "needs_interview", job["state"]

        ledger = J.read_artifact(job_id, "answer_ledger", PERSONA)
        # Only q3 names "user" as its source; q1 and q2 went to the Librarian.
        ids = [i["question_id"] for i in ledger["interview_items"]]
        assert ids == ["q3"], ids
        assert "all items answered" in RUN.answer_interview(job_id, "q3",
                                                            "the garden only", PERSONA)
        assert J.get(job_id, PERSONA)["state"] == "planning"

        # EVERY ROW KEEPS ITS QUESTION ID through the N5 merge. merge_code_block
        # injects only the code-written block, which does not include the id, so
        # a row the Librarian never saw merges ANONYMOUS unless N5 re-asserts it
        # — and an anonymous row cannot be answered, counted or pointed at by a
        # REPAIR. This assertion is the one that caught that.
        ledger = J.read_artifact(job_id, "answer_ledger", PERSONA)
        assert [r.get("question_id") for r in ledger["rows"]] == ["q1", "q2", "q3"], \
            ledger["rows"]
        # The user's words are kept beside the question, not written over it.
        answered = [r for r in ledger["rows"] if r.get("user_answer")]
        assert len(answered) == 1 and answered[0]["question_id"] == "q3", answered
        assert answered[0]["user_answer"] == "the garden only", answered
    finally:
        _limit(None)


@check("an empty interview answer is refused, and an unknown item is not invented")
def _():
    reset()
    _limit(100.0)
    try:
        job_id = J.create("a gap", trigger="test")["job_id"]
        J.set_state(job_id, "queued", persona=PERSONA)
        RUN.advance(job_id, PERSONA)
        assert "not an answer" in RUN.answer_interview(job_id, "q1", "  ", PERSONA)
        assert "no open interview item" in RUN.answer_interview(job_id, "q99", "x",
                                                                PERSONA)
    finally:
        _limit(None)


class _Report:
    def __init__(self, ok):
        self.ok = ok
        self.results = []
        self.failures = [] if ok else [_Check()]

    def summary(self):
        # Matches VerifyReport.summary()'s real shape, which NAMES the failures —
        # a stub that only said "1 FAILED" would let the runner drop the check
        # name and still pass this test.
        if self.ok:
            return "verify: all pass"
        return ("verify: 1 of 1 FAILED — "
                + ", ".join(r.name for r in self.failures))


class _Check:
    name = "agent-tools:overlay"
    ok = False
    output = "home_care.md names send_email"


@check("SELF-REVIEW: approving does not re-run N10 and undo itself")
def _():
    # N10 had no artifact, so advance() never skipped it: approve() set
    # `executing`, the next tick walked the graph from the top, N10 ran again
    # and set the state back to `briefed`. N12 was unreachable and the approval
    # was silently undone every thirty minutes, forever.
    reset()
    _limit(100.0)
    saved = (RUN.writer.apply, RUN._verify)
    RUN.writer.apply = lambda *a, **k: "OK — 1 file(s) written"
    RUN._verify = lambda ctx, tests: _Report(True)
    try:
        job_id = J.create("a gap", trigger="test")["job_id"]
        J.set_state(job_id, "queued", persona=PERSONA)
        RUN.tick(PERSONA)
        ledger = J.read_artifact(job_id, "answer_ledger", PERSONA)
        for item in ledger["interview_items"]:
            RUN.answer_interview(job_id, item["question_id"], "the garden", PERSONA)
        RUN.tick(PERSONA)
        assert J.get(job_id, PERSONA)["state"] == "briefed"

        RUN.approve(job_id, PERSONA)
        assert J.get(job_id, PERSONA)["state"] == "executing"
        RUN.tick(PERSONA)
        state = J.get(job_id, PERSONA)["state"]
        assert state == "verifying", (
            f"the approval was undone — state went back to {state!r}")
    finally:
        RUN.writer.apply, RUN._verify = saved
        _limit(None)


@check("SELF-REVIEW: N14 is never reached by a tick — only by accept()")
def _():
    reset()
    _limit(100.0)
    try:
        job_id = J.create("a gap", trigger="test")["job_id"]
        J.set_state(job_id, "queued", persona=PERSONA)
        J.set_state(job_id, "verifying", persona=PERSONA)
        J.write_artifact(job_id, "build_plan", _canned_for("build_planner"), PERSONA)
        RUN.tick(PERSONA)
        assert J.get(job_id, PERSONA)["state"] == "verifying", (
            "a tick closed a job the user had not accepted")
        assert R.capabilities(PERSONA) == {}
        out = RUN.accept(job_id, PERSONA)
        assert J.get(job_id, PERSONA)["state"] == "landed", out
        assert "home_care" in R.capabilities(PERSONA)
        # And accepting twice cannot register it twice.
        assert "[N13] accepts" in RUN.accept(job_id, PERSONA)
        assert R.capabilities(PERSONA)["home_care"]["version"] == 1
    finally:
        _limit(None)


@check("SELF-REVIEW: the brief's leak check reads the RAW body, not the redacted one")
def _():
    # findings() run on an already-redacted body always reports clean, so the
    # check that tells the runner the structural layer failed could never fire.
    import core.build.brief as BR
    saved = BR.persona_values
    BR.persona_values = lambda persona=None: ["Prudential Apex"]
    try:
        job = {"job_id": "BLD-0919-01", "gap": "a gap at Prudential Apex"}
        raw, redacted = BR.assemble(job, {}, {}, {})
        assert "Prudential Apex" in raw, "assemble() redacted its own raw half"
        assert "Prudential Apex" not in redacted, redacted
        assert BR.findings(raw) == ["Prudential Apex"], BR.findings(raw)
        assert BR.findings(redacted) == [], (
            "this is why the check must read raw — redacted always reports clean")
    finally:
        BR.persona_values = saved


@check("SELF-REVIEW: the context block reads jobs.GATE_STATES without importing the driver")
def _():
    # tools/build.py runs on every user turn through load_recent_context.
    # Importing the runner there would put the writer, registry, settle and
    # probe on the hot path of every ordinary session.
    source = (ROOT / "tools" / "build.py").read_text(encoding="utf-8")
    assert "core.build.runner import GATE_STATES" not in source, source[:0]
    assert "J.GATE_STATES" in source
    assert J.GATE_STATES == RUN.GATE_STATES, "the two copies disagree"


# ---------------------------------------------------------------------------
# N12's failure path
# ---------------------------------------------------------------------------

@check("a failing check REVERTS before the node returns, and the job fails with the check name")
def _():
    reset()
    job_id = J.create("a gap", trigger="test")["job_id"]
    J.set_state(job_id, "queued", persona=PERSONA)
    J.set_state(job_id, "executing", persona=PERSONA)
    J.write_artifact(job_id, "build_plan", _CANNED["build_planner"], PERSONA)

    reverts: list[str] = []
    saved = (RUN.writer.apply, RUN.writer.revert, RUN._verify)
    RUN.writer.apply = lambda *a, **k: "OK — 1 file(s) written"
    RUN.writer.revert = lambda jid, p=None: reverts.append(jid) or \
        f"{jid}: reverted — 1 restored, 0 removed"
    RUN._verify = lambda ctx, tests: _Report(False)
    try:
        out = RUN.run_node(job_id, "N12 apply+verify", PERSONA)
    finally:
        RUN.writer.apply, RUN.writer.revert, RUN._verify = saved

    assert out.status == "failed", out
    assert reverts == [job_id], "nothing was reverted"
    assert "agent-tools:overlay" in out.detail, out.detail
    assert J.get(job_id, PERSONA)["state"] == "failed"


@check("a revert that SKIPPED entries raises the blocked flag — the caller keys on the clause, not the prefix")
def _():
    # The v3.3 correction recorded this for phase 4 specifically: revert()'s
    # summary opens with "reverted —" EVEN WHEN every entry was skipped for
    # failing the path rules. A caller matching the prefix would read a
    # half-applied overlay as a clean undo.
    reset()
    job_id = J.create("a gap", trigger="test")["job_id"]
    J.set_state(job_id, "queued", persona=PERSONA)
    J.set_state(job_id, "executing", persona=PERSONA)
    J.write_artifact(job_id, "build_plan", _CANNED["build_planner"], PERSONA)

    saved = (RUN.writer.apply, RUN.writer.revert, RUN._verify)
    RUN.writer.apply = lambda *a, **k: "OK — 1 file(s) written"
    RUN.writer.revert = lambda jid, p=None: (
        f"{jid}: reverted — 0 restored, 0 removed, 1 SKIPPED (failed the path rules)")
    RUN._verify = lambda ctx, tests: _Report(False)
    try:
        RUN.run_node(job_id, "N12 apply+verify", PERSONA)
    finally:
        RUN.writer.apply, RUN.writer.revert, RUN._verify = saved

    job = J.get(job_id, PERSONA)
    assert job.get("blocked"), "a skipped revert left no flag on the board"
    assert "half-applied" in job["blocked"], job["blocked"]


@check("a plan declaring no files cannot land — there is nothing to verify")
def _():
    reset()
    job_id = J.create("a gap", trigger="test")["job_id"]
    J.set_state(job_id, "queued", persona=PERSONA)
    J.set_state(job_id, "executing", persona=PERSONA)
    J.write_artifact(job_id, "build_plan",
                     {**_CANNED["build_planner"], "files": []}, PERSONA)
    out = RUN.run_node(job_id, "N12 apply+verify", PERSONA)
    assert out.status == "failed" and "no files" in out.detail, out


@check("[N13] refuse reverts, and says so loudly when the revert skipped anything")
def _():
    reset()
    job_id = J.create("a gap", trigger="test")["job_id"]
    J.set_state(job_id, "queued", persona=PERSONA)
    J.set_state(job_id, "verifying", persona=PERSONA)
    saved = RUN.writer.revert
    RUN.writer.revert = lambda jid, p=None: (
        f"{jid}: reverted — 0 restored, 0 removed, 2 SKIPPED (failed the path rules)")
    try:
        out = RUN.refuse(job_id, PERSONA)
    finally:
        RUN.writer.revert = saved
    assert "needs a look" in out, out
    assert J.get(job_id, PERSONA)["state"] == "abandoned"


def _write_event(agent: str, detail: str) -> None:
    logs = _data_dir(PERSONA) / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    with open(logs / "quality_events.json", "a", encoding="utf-8") as handle:
        handle.write(json.dumps({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": "USER_CORRECTION", "source_agent": agent,
            "detail": detail}) + "\n")


# ---------------------------------------------------------------------------
# REVIEW ROUND 1 — the Fable 5.1 phase-4 review, one test per defect
# ---------------------------------------------------------------------------

def _land_one(job_id: str, apply_stub=None) -> None:
    """
    Drive a job to `landed` with the writer and verify stubbed.

    `apply_stub` lets a caller keep its OWN writer stub in place — without it
    this helper replaced the caller's, which is how the first version of the
    D14a test asserted on brief writes it had just stubbed away.
    """
    saved = (RUN.writer.apply, RUN._verify)
    RUN.writer.apply = apply_stub or RUN.writer.apply if apply_stub else (
        lambda *a, **k: "OK — 3 file(s) written")
    RUN._verify = lambda ctx, tests: _Report(True)
    try:
        J.set_state(job_id, "queued", persona=PERSONA)
        RUN.tick(PERSONA)
        ledger = J.read_artifact(job_id, "answer_ledger", PERSONA)
        for item in ledger["interview_items"]:
            RUN.answer_interview(job_id, item["question_id"], "the garden", PERSONA)
        RUN.tick(PERSONA)
        RUN.approve(job_id, PERSONA)
        RUN.tick(PERSONA)
        RUN.accept(job_id, PERSONA)
    finally:
        RUN.writer.apply, RUN._verify = saved


@check("REVIEW D1: refuse() will not touch a LANDED job — the registry and overlay stay agreed")
def _():
    reset()
    _limit(100.0)
    reverts: list[str] = []
    saved = RUN.writer.revert
    RUN.writer.revert = lambda jid, p=None: reverts.append(jid) or f"{jid}: reverted"
    try:
        job_id = J.create("a gap", trigger="test")["job_id"]
        _land_one(job_id)
        assert J.get(job_id, PERSONA)["state"] == "landed"
        out = RUN.refuse(job_id, PERSONA)
        assert "cannot be refused" in out, out
        assert reverts == [], "a landed capability's files were reverted"
        assert J.get(job_id, PERSONA)["state"] == "landed"
        assert "home_care" in R.capabilities(PERSONA)
    finally:
        RUN.writer.revert = saved
        _limit(None)


@check("REVIEW D1: refuse() refuses a mid-pipeline job too — only the two gates admit it")
def _():
    reset()
    _limit(100.0)
    reverts: list[str] = []
    saved = RUN.writer.revert
    RUN.writer.revert = lambda jid, p=None: reverts.append(jid) or f"{jid}: reverted"
    try:
        for state in ("proposed", "queued", "planning"):
            job_id = J.create(f"a gap at {state}", trigger="test")["job_id"]
            if state != "proposed":
                J.set_state(job_id, "queued", persona=PERSONA)
            if state == "planning":
                J.set_state(job_id, "planning", persona=PERSONA)
            out = RUN.refuse(job_id, PERSONA)
            assert "refusing is for a job waiting on you" in out, (state, out)
        assert reverts == [], reverts
        # And it DOES work at both gates.
        for state in sorted(RUN.REFUSABLE_STATES):
            job_id = J.create(f"a gap to refuse at {state}", trigger="t")["job_id"]
            J.set_state(job_id, "queued", persona=PERSONA)
            J.set_state(job_id, state, persona=PERSONA)
            assert "abandoned" in RUN.refuse(job_id, PERSONA)
    finally:
        RUN.writer.revert = saved
        _limit(None)


@check("REVIEW D2: a limit crossed DURING a call parks at awaiting_approval, never fails")
def _():
    # The call that crosses cannot be aborted, so the crossing must be caught
    # after it. Before the post-node gate the crossing surfaced at the Planner's
    # dry-run file check, which read a job-gate refusal as a plan defect and
    # FAILED the job terminally — past the one state that can release it.
    reset()
    # One stub call costs ~$0.0465; a limit above that admits N2, and the call
    # itself takes the job past it.
    _limit(0.02)
    try:
        job_id = J.create("a gap", trigger="test")["job_id"]
        J.set_state(job_id, "queued", persona=PERSONA)
        outcomes = RUN.advance(job_id, PERSONA)
        job = J.get(job_id, PERSONA)
        assert job["state"] == "awaiting_approval", (job["state"], outcomes)
        assert job["state"] not in J.TERMINAL, "a crossing must never be terminal"
        assert any(o.status == "parked" for o in outcomes), outcomes
        # And approve_limit + resume genuinely releases it.
        COST.approve_limit(job_id, 100.0, PERSONA)
        assert "resumed at" in RUN.resume(job_id, PERSONA)
        assert J.get(job_id, PERSONA)["state"] not in J.TERMINAL
    finally:
        _limit(None)


@check("REVIEW D2: a DRY RUN is not budget-gated — it writes nothing and costs nothing")
def _():
    reset()
    _limit(0.001)
    try:
        job_id = J.create("a gap", trigger="test")["job_id"]
        J.set_state(job_id, "queued", persona=PERSONA)
        J.set_state(job_id, "briefed", persona=PERSONA)
        with COST.job_scope(job_id, PERSONA):
            COST.record_job_tokens("gemini-3.8-flash", 900_000, 90_000)
        assert COST.job_spend(job_id, PERSONA) > 0.001, "fixture did not go over"
        edits = [{"path": str(J.job_dir(job_id, PERSONA) / "probe.json"),
                  "content": "{}"}]
        dry = RUN.writer.apply(job_id, None, edits, dry_run=True, persona=PERSONA)
        assert dry.startswith("OK (dry run)"), dry
        wet = RUN.writer.apply(job_id, None, edits, persona=PERSONA)
        assert "tripwire" in wet, wet        # the real write is still gated
    finally:
        _limit(None)


@check("REVIEW D7: a job parked at N12 for the CEILING resumes to executing, not planning")
def _():
    reset()
    _limit(100.0)
    saved = RUN.writer.apply
    RUN.writer.apply = lambda *a, **k: (
        "PARKED — above the ceiling: autonomy.may_create_agent_files is false")
    try:
        job_id = J.create("a gap", trigger="test")["job_id"]
        J.set_state(job_id, "queued", persona=PERSONA)
        J.set_state(job_id, "executing", persona=PERSONA)
        J.write_artifact(job_id, "build_plan", _canned_for("build_planner"), PERSONA)
        out = RUN.run_node(job_id, "N12 apply+verify", PERSONA)
        assert out.status == "parked", out
        assert J.get(job_id, PERSONA)["resume_to"] == "executing", J.get(job_id, PERSONA)
        assert "resumed at executing" in RUN.resume(job_id, PERSONA)
        # `planning` was the old fixed target: every artifact exists, so all
        # nodes skip, N12 wants `executing` and approve() wants `briefed` —
        # the job was unmovable by any command.
        assert J.get(job_id, PERSONA)["state"] == "executing"
    finally:
        RUN.writer.apply = saved
        _limit(None)


@check("REVIEW D7: resume_to is CLEARED by the next transition — no stale target")
def _():
    reset()
    job_id = J.create("a gap", trigger="test")["job_id"]
    J.set_state(job_id, "queued", persona=PERSONA)
    J.set_state(job_id, "awaiting_approval", resume_to="executing", persona=PERSONA)
    assert J.get(job_id, PERSONA)["resume_to"] == "executing"
    J.set_state(job_id, "planning", persona=PERSONA)
    assert J.get(job_id, PERSONA)["resume_to"] is None, "a stale resume_to survived"


@check("REVIEW D8: the fourth correction does NOT file a second REPAIR ticket")
def _():
    reset()
    R.record_landing("BLD-0919-01", _canned_for("build_planner"), [], PERSONA)
    for _ in range(RUN.REPAIR_AT):
        _write_event("home_care", "said the plants were watered on August 4")
    assert len(RUN._repair_scan(PERSONA)) == 1
    # The count used to live in the gap text, which create() fingerprints — so
    # x4 hashed differently, escaped the dedupe and filed a second ticket.
    _write_event("home_care", "said the plants were watered on August 4")
    assert RUN._repair_scan(PERSONA) == [], "x4 filed a duplicate ticket"
    _write_event("home_care", "said the plants were watered on August 4")
    assert RUN._repair_scan(PERSONA) == [], "x5 filed a duplicate ticket"
    repairs = [j for j in J.states(PERSONA).values() if j["mode"] == "repair"]
    assert len(repairs) == 1, repairs


@check("REVIEW D9: expected dispatches is None, never a coordinator-turn count of 0.0")
def _():
    reset()
    _limit(100.0)
    try:
        job_id = J.create("a gap", trigger="test")["job_id"]
        _land_one(job_id)
        run = R.capabilities(PERSONA)["home_care"]["run"]
        assert run["dispatches_expected_per_day"] is None, run
        # 0.0 is the "it never fires" verdict the contract says must not be
        # inferred from an inability to count.
        assert run["dispatches_actual_per_day"] is None, run
    finally:
        _limit(None)


@check("REVIEW D11: a writer CRASH at N12 fails with its own reason, and no sweep runs")
def _():
    reset()
    swept: list[int] = []
    saved = (RUN.writer.apply, RUN._verify, RUN.writer.revert)
    RUN.writer.apply = lambda *a, **k: (
        "BLD-0919-01: writer failed and reverted — OSError: disk full")
    RUN._verify = lambda ctx, tests: swept.append(1) or _Report(True)
    RUN.writer.revert = lambda jid, p=None: f"{jid}: nothing to revert"
    try:
        job_id = J.create("a gap", trigger="test")["job_id"]
        J.set_state(job_id, "queued", persona=PERSONA)
        J.set_state(job_id, "executing", persona=PERSONA)
        J.write_artifact(job_id, "build_plan", _canned_for("build_planner"), PERSONA)
        out = RUN.run_node(job_id, "N12 apply+verify", PERSONA)
        assert out.status == "failed", out
        assert "disk full" in out.detail, out.detail
        assert swept == [], "an 18-check sweep ran against an unapplied overlay"
        assert "disk full" in J.get(job_id, PERSONA)["detail"]
    finally:
        RUN.writer.apply, RUN._verify, RUN.writer.revert = saved


@check("REVIEW D14a: every brief write happens from a WRITABLE state")
def _():
    # The defect was silent by construction: writer.WRITABLE_STATES is
    # {briefed, executing}, _write_brief does not raise, so a brief written
    # after the move to `verifying` or `landed` was simply refused — and the
    # landed brief went on saying `State: briefed` with no Verification
    # section, which is the one thing [N13] exists to read. Asserted on the
    # state AT WRITE TIME, because that is the property; the bytes are the
    # writer suite's business.
    reset()
    _limit(100.0)
    seen: list[tuple[str, str]] = []
    saved = (RUN.writer.apply, RUN._verify)

    def _record(job_id, plan, edits, dry_run=False, persona=None):
        if any(str(e.get("path", "")).endswith("brief.md") for e in edits):
            seen.append((job_id, J.get(job_id, persona)["state"]))
        return "OK — 3 file(s) written"

    RUN.writer.apply = _record
    RUN._verify = lambda ctx, tests: _Report(True)
    try:
        job_id = J.create("a gap", trigger="test")["job_id"]
        _land_one(job_id, apply_stub=_record)
        assert J.get(job_id, PERSONA)["state"] == "landed"
        assert seen, "no brief was written at all"
        bad = [(j, st) for j, st in seen if st not in RUN.writer.WRITABLE_STATES]
        assert not bad, f"brief written from a non-writable state: {bad}"
        # N10, N12-success and N14 — three writes, the last two of which were
        # silently refused before this fix.
        assert len(seen) >= 3, seen
    finally:
        RUN.writer.apply, RUN._verify = saved
        _limit(None)


@check("REVIEW D14a: on a failed landing the brief is written AFTER the revert")
def _():
    # revert() removes brief.md along with everything else the job wrote, so a
    # brief written before it is deleted and the failing check output — the
    # thing the next attempt's brief is supposed to carry — goes with it.
    reset()
    _limit(100.0)
    order: list[str] = []
    saved = (RUN.writer.apply, RUN._verify, RUN.writer.revert)

    def _record(job_id, plan, edits, dry_run=False, persona=None):
        if any(str(e.get("path", "")).endswith("brief.md") for e in edits):
            order.append(f"brief:{J.get(job_id, persona)['state']}")
        else:
            order.append("apply")
        return "OK — 3 file(s) written"

    RUN.writer.apply = _record
    RUN._verify = lambda ctx, tests: _Report(False)
    RUN.writer.revert = lambda jid, p=None: order.append("revert") or f"{jid}: reverted"
    try:
        job_id = J.create("a gap", trigger="test")["job_id"]
        J.set_state(job_id, "queued", persona=PERSONA)
        J.set_state(job_id, "executing", persona=PERSONA)
        J.write_artifact(job_id, "build_plan", _canned_for("build_planner"), PERSONA)
        RUN.run_node(job_id, "N12 apply+verify", PERSONA)
        assert "revert" in order, order
        brief = [i for i, step in enumerate(order) if step.startswith("brief:")]
        assert brief, "no brief was written on the failure path"
        assert brief[-1] > order.index("revert"), (
            f"the brief was written before the revert that deletes it: {order}")
        assert order[brief[-1]] == "brief:executing", order
    finally:
        RUN.writer.apply, RUN._verify, RUN.writer.revert = saved
        _limit(None)


@check("REVIEW D10: two Build events in ONE trace are both written, not deduped")
def _():
    # write_quality_event dedupes by event TYPE per RequestTrace — right for a
    # correction with two legitimate writers, wrong for Build's events, which
    # each carry their own BLD- id. Two request_build calls in one turn recorded
    # one BUILD_PROPOSED; two jobs failing their checks in one tick recorded one
    # BUILD_CHECK_FAILED, so the second capability's revert had no signal at all
    # — in exactly the turn the redundant record was supposed to earn its keep.
    reset()
    import core.persona as PZ
    from tools import logger as LG
    written: list[dict] = []
    saved_dir, saved_logs = PZ.persona_data_dir, LG._logs_dir
    PZ.persona_data_dir = _data_dir
    LG._logs_dir = lambda: _data_dir(PERSONA) / "logs"
    trace = T.start_request_trace("one user turn", PERSONA)
    try:
        for n in (1, 2):
            LG.write_quality_event("BUILD_PROPOSED", "coordinator",
                                   f"BLD-0919-0{n} (construct): gap {n}")
            LG.write_quality_event("BUILD_CHECK_FAILED", "build",
                                   f"BLD-0919-0{n} reverted — agent-tools failed")
        # A type NOT on the exemption list still dedupes — the original guard
        # is intact, not widened.
        LG.write_quality_event("USER_CORRECTION", "home_care", "said August 4")
        LG.write_quality_event("USER_CORRECTION", "home_care", "said August 4 again")
    finally:
        T.set_trace(None)
        PZ.persona_data_dir, LG._logs_dir = saved_dir, saved_logs

    path = _data_dir(PERSONA) / "logs" / "quality_events.json"
    written = [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]
    kinds = [e["event_type"] for e in written]
    assert kinds.count("BUILD_PROPOSED") == 2, kinds
    assert kinds.count("BUILD_CHECK_FAILED") == 2, kinds
    assert kinds.count("USER_CORRECTION") == 1, kinds
    assert LG._NEVER_DEDUPED == {"BUILD_PROPOSED", "BUILD_CHECK_FAILED"}


@check("REVIEW D3: a Diarist-only or tick trace is SKIPPED when attributing a correction")
def _():
    # last_trace() returns whatever was written most recently, and the Diarist
    # is fire-and-forget on its own thread with its own RequestTrace, finished
    # AFTER the turn it followed — so the record on top when a correction
    # arrives is plausibly the Diarist's. REPAIR counts source_agent ∩ registry,
    # so a wrong name never reaches three and the trigger is inert.
    reset()
    directory = _data_dir(PERSONA) / "traces"
    directory.mkdir(parents=True, exist_ok=True)
    today = datetime.now().date().isoformat()
    records = [
        # oldest: the real exchange
        {"is_proactive": False,
         "pipeline": [{"agent": "coordinator",
                       "subagents": [{"agent": "home_care"}]}]},
        # then the Diarist, on its own thread, written afterwards
        {"is_proactive": False, "pipeline": [{"agent": "diarist"}]},
        # then a build_tick, proactive
        {"is_proactive": True,
         "pipeline": [{"agent": "build",
                       "subagents": [{"agent": "build_inquiry"},
                                     {"agent": "build_librarian"}]}]},
    ]
    (directory / f"{today}.jsonl").write_text(
        "\n".join(json.dumps(r) for r in records) + "\n", "utf-8")

    import core.orchestrator as O
    import core.persona as PZ
    saved = PZ.persona_data_dir
    PZ.persona_data_dir = _data_dir
    try:
        blamed = O._corrected_agents(PERSONA)
    finally:
        PZ.persona_data_dir = saved
    assert blamed == ["home_care"], blamed
    for wrong in ("diarist", "build_inquiry", "build_librarian", "build"):
        assert wrong not in blamed, (wrong, blamed)


@check("REVIEW D3: with only non-exchange traces on disk, nothing is attributed")
def _():
    reset()
    directory = _data_dir(PERSONA) / "traces"
    directory.mkdir(parents=True, exist_ok=True)
    today = datetime.now().date().isoformat()
    (directory / f"{today}.jsonl").write_text(
        json.dumps({"is_proactive": True,
                    "pipeline": [{"agent": "build",
                                  "subagents": [{"agent": "build_inquiry"}]}]}) + "\n",
        "utf-8")
    import core.orchestrator as O
    import core.persona as PZ
    saved = PZ.persona_data_dir
    PZ.persona_data_dir = _data_dir
    try:
        assert O._corrected_agents(PERSONA) == [], "a tick was blamed for a correction"
    finally:
        PZ.persona_data_dir = saved


@check("REVIEW D13: the context block names the QUESTIONS, not just the parked job")
def _():
    # There is no brief.md for a parked job — the writer refuses the write from
    # that state, correctly — so the questions lived only in an artifact on disk
    # and [N6] could not be answered in conversation at all.
    reset()
    _limit(100.0)
    import core.persona as PZ
    from tools import build as TB
    saved = PZ.persona_data_dir
    PZ.persona_data_dir = _data_dir
    try:
        job_id = J.create("nothing owns the watering check", trigger="t")["job_id"]
        J.set_state(job_id, "queued", persona=PERSONA)
        RUN.advance(job_id, PERSONA)
        assert J.get(job_id, PERSONA)["state"] == "needs_interview"
        block = TB.context_block(PERSONA)
        assert job_id in block, block
        assert "What is decided here versus surfaced?" in block, block
        assert "`q3`" in block, block
    finally:
        PZ.persona_data_dir = saved
        _limit(None)


@check("REVIEW D12: every command the context block prints binds a persona")
def _():
    reset()
    _limit(0.001)
    import core.persona as PZ
    from tools import build as TB
    saved = PZ.persona_data_dir
    PZ.persona_data_dir = _data_dir
    try:
        job_id = J.create("a gap", trigger="test")["job_id"]
        J.set_state(job_id, "queued", persona=PERSONA)
        RUN.advance(job_id, PERSONA)
        assert J.get(job_id, PERSONA)["state"] == "awaiting_approval"
        block = TB.context_block(PERSONA)
        assert "METATRON_PERSONA=mike" in block, block
        assert "--persona mike" in block, block
        assert "ON THE VM" in block, block
    finally:
        PZ.persona_data_dir = saved
        _limit(None)


@check("REVIEW N1: the landed brief says `landed`, not the state it was written from")
def _():
    # The fix for D14a writes the brief BEFORE the state moves, so the writer
    # admits it — which meant the final document recorded `executing`, the
    # state it was written from, and the landed brief never said landed.
    reset()
    _limit(100.0)
    bodies: list[str] = []
    saved = (RUN.writer.apply, RUN._verify)

    def _record(job_id, plan, edits, dry_run=False, persona=None):
        for edit in edits:
            if str(edit.get("path", "")).endswith("brief.md"):
                bodies.append(edit["content"])
        return "OK — 3 file(s) written"

    RUN.writer.apply = _record
    RUN._verify = lambda ctx, tests: _Report(True)
    try:
        job_id = J.create("a gap", trigger="test")["job_id"]
        _land_one(job_id, apply_stub=_record)
        assert J.get(job_id, PERSONA)["state"] == "landed"
        assert bodies, "no brief was written"
        assert "**State:** landed" in bodies[-1], bodies[-1][:240]
        # And the intermediate ones name the state their own node reached.
        assert any("**State:** verifying" in b for b in bodies), \
            [b.split("**State:**")[1][:12] for b in bodies if "**State:**" in b]
    finally:
        RUN.writer.apply, RUN._verify = saved
        _limit(None)


@check("REVIEW N2: the referent block will not present a build_tick as the previous exchange")
def _():
    # The tick writes its own RequestTrace, so after a tick with work this block
    # opened "The exchange immediately before this one … This was a scheduled
    # run", and the user's "undo that" resolved against Build's own machinery.
    reset()
    import core.persona as PZ
    from tools import turn_referent as TRF
    directory = _data_dir(PERSONA) / "traces"
    directory.mkdir(parents=True, exist_ok=True)
    today = datetime.now().date().isoformat()
    now = datetime.now().isoformat()
    records = [
        {"ts": now, "is_proactive": False, "user_input": "book the table",
         "synth_response": "Booked.",
         "pipeline": [{"agent": "coordinator", "subagents": [{"agent": "logistics"}]}]},
        {"ts": now, "is_proactive": False, "user_input": "",
         "pipeline": [{"agent": "diarist"}]},
        {"ts": now, "is_proactive": True, "user_input": "build_tick: 1 job(s)",
         "pipeline": [{"agent": "build",
                       "subagents": [{"agent": "build_inquiry"}]}]},
    ]
    (directory / f"{today}.jsonl").write_text(
        "\n".join(json.dumps(r) for r in records) + "\n", "utf-8")

    saved = PZ.persona_data_dir
    PZ.persona_data_dir = _data_dir
    try:
        newest = TRF.last_trace(PERSONA)
        assert newest["user_input"].startswith("build_tick"), "fixture order wrong"
        # The newest record is the tick; the newest EXCHANGE is the real turn.
        assert TRF.is_exchange(newest) is False
        assert TRF.is_exchange(records[1]) is False, "a Diarist trace is not an exchange"
        assert TRF.is_exchange(records[0]) is True
        assert TRF.last_exchange(PERSONA)["user_input"] == "book the table"
        block = TRF.context_block(PERSONA)
        assert "book the table" in block, block
        assert "build_tick" not in block, block
        assert "scheduled run" not in block, block
    finally:
        PZ.persona_data_dir = saved


@check("REVIEW N2: attribution and the referent block read ONE definition of an exchange")
def _():
    # They had the rule separately and disagreed — attribution skipped ticks
    # while the referent block still announced one. A rule duplicated in two
    # places holds until one copy is improved.
    import core.orchestrator as O
    source = (ROOT / "core" / "orchestrator.py").read_text(encoding="utf-8")
    assert "last_exchange" in source, "the orchestrator kept its own scan"
    assert "_trace_files" not in source.split("_corrected_agents")[1][:2000], \
        "the orchestrator still walks trace files itself"
    # A SCHEDULED session IS an exchange, and its specialist is attributable —
    # the round-1 fix skipped anything proactive and lost those corrections.
    reset()
    import core.persona as PZ
    from tools import turn_referent as TRF
    directory = _data_dir(PERSONA) / "traces"
    directory.mkdir(parents=True, exist_ok=True)
    today = datetime.now().date().isoformat()
    (directory / f"{today}.jsonl").write_text(json.dumps(
        {"ts": datetime.now().isoformat(), "is_proactive": True,
         "pipeline": [{"agent": "coordinator",
                       "subagents": [{"agent": "home_care"}]}]}) + "\n", "utf-8")
    saved = PZ.persona_data_dir
    PZ.persona_data_dir = _data_dir
    try:
        assert TRF.is_exchange(TRF.last_trace(PERSONA)) is True
        assert O._corrected_agents(PERSONA) == ["home_care"], \
            "a scheduled session's specialist was not attributable"
    finally:
        PZ.persona_data_dir = saved


@check("REVIEW D14b: a question is indexed with its CLASS, not with the persona")
def _():
    reset()
    _limit(100.0)
    indexed: list[dict] = []
    from core.build import index as IDX
    saved = (IDX.available, IDX.add_question)
    IDX.available = lambda: True
    IDX.add_question = lambda text, job_id, question_id="", question_class="", \
        persona=None: indexed.append(
            {"question_id": question_id, "class": question_class, "persona": persona})
    try:
        job_id = J.create("a gap", trigger="test")["job_id"]
        J.set_state(job_id, "queued", persona=PERSONA)
        RUN.run_node(job_id, "N1 manifest", PERSONA)
        RUN.run_node(job_id, "N2 inquiry", PERSONA)
        assert len(indexed) == 3, indexed
        assert [i["class"] for i in indexed] == ["intent", "surface", "authority"], indexed
        assert all(i["persona"] == PERSONA for i in indexed), indexed
        assert all(i["class"] != PERSONA for i in indexed), "persona landed in the class slot"
    finally:
        IDX.available, IDX.add_question = saved
        _limit(None)


@check("REVIEW D14c: the dry-run rejection does not claim a retry that never ran")
def _():
    reset()
    _limit(100.0)
    saved = RUN.writer.apply
    RUN.writer.apply = lambda *a, **k: "REFUSED — 1 path problem(s): nope"
    try:
        job_id = J.create("a gap", trigger="test")["job_id"]
        J.set_state(job_id, "queued", persona=PERSONA)
        for node in ("N1 manifest", "N2 inquiry", "N3 settle", "N4 librarian",
                     "N5 merge"):
            RUN.run_node(job_id, node, PERSONA)
        ledger = J.read_artifact(job_id, "answer_ledger", PERSONA)
        for item in ledger["interview_items"]:
            RUN.answer_interview(job_id, item["question_id"], "the garden", PERSONA)
        out = RUN.run_node(job_id, "N7 planner", PERSONA)
        assert out.status == "failed", out
        assert "rejected after retry" not in out.detail, out.detail
        assert "N7 planner rejected:" in out.detail, out.detail
    finally:
        RUN.writer.apply = saved
        _limit(None)


# ---------------------------------------------------------------------------
# The REPAIR trigger — counting, not judgement
# ---------------------------------------------------------------------------

@check("a BUILT capability corrected x3 on the same fault files a REPAIR ticket")
def _():
    reset()
    R.record_landing("BLD-0919-01",
                     {"capability": {"id": "home_care", "kind": "agent",
                                     "execution_mode": "blocking",
                                     "latency_budget_ms": 8000}}, [], PERSONA)
    for _ in range(RUN.REPAIR_AT):
        _write_event("home_care", "said the plants were watered on August 4")
    filed = RUN._repair_scan(PERSONA)
    assert len(filed) == 1 and "REPAIR home_care" in filed[0], filed
    repair = [j for j in J.states(PERSONA).values() if j["mode"] == "repair"]
    assert len(repair) == 1 and repair[0]["capability_hint"] == "home_care", repair
    assert repair[0]["state"] == "proposed", "a REPAIR must be triaged like anything else"


@check("two corrections are a coincidence — the bar is three")
def _():
    reset()
    R.record_landing("BLD-0919-01",
                     {"capability": {"id": "home_care", "kind": "agent",
                                     "execution_mode": "blocking",
                                     "latency_budget_ms": 8000}}, [], PERSONA)
    for _ in range(RUN.REPAIR_AT - 1):
        _write_event("home_care", "said the plants were watered on August 4")
    assert RUN._repair_scan(PERSONA) == []


@check("three DIFFERENT faults are not one fault — the signature is what collapses them")
def _():
    reset()
    R.record_landing("BLD-0919-01",
                     {"capability": {"id": "home_care", "kind": "agent",
                                     "execution_mode": "blocking",
                                     "latency_budget_ms": 8000}}, [], PERSONA)
    for detail in ("read the wrong date", "ignored the rainfall",
                   "counted an indoor pot"):
        _write_event("home_care", detail)
    assert RUN._repair_scan(PERSONA) == [], "unrelated faults were welded into one ticket"


@check("a correction against a TRACKED specialist files nothing — only built capabilities repair")
def _():
    reset()
    for _ in range(RUN.REPAIR_AT + 2):
        _write_event("logistics", "booked the wrong day")
    assert RUN._repair_scan(PERSONA) == []


@check("a comma-joined attribution is split — a turn can dispatch more than one specialist")
def _():
    reset()
    R.record_landing("BLD-0919-01",
                     {"capability": {"id": "home_care", "kind": "agent",
                                     "execution_mode": "blocking",
                                     "latency_budget_ms": 8000}}, [], PERSONA)
    for _ in range(RUN.REPAIR_AT):
        _write_event("logistics,home_care", "said the plants were watered on August 4")
    assert len(RUN._repair_scan(PERSONA)) == 1


# ---------------------------------------------------------------------------
# The correction attribution it depends on
# ---------------------------------------------------------------------------

@check("a correction is attributed to the PREVIOUS turn's specialists, not to the coordinator")
def _():
    reset()
    directory = _data_dir(PERSONA) / "traces"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{datetime.now().date().isoformat()}.jsonl").write_text(
        json.dumps({"pipeline": [{"agent": "coordinator", "subagents": [
            {"agent": "home_care"}, {"agent": "logistics"}]}]}) + "\n", "utf-8")

    import core.orchestrator as O
    import core.persona as PZ
    saved = PZ.persona_data_dir
    PZ.persona_data_dir = _data_dir
    try:
        blamed = O._corrected_agents(PERSONA)
    finally:
        PZ.persona_data_dir = saved
    assert blamed == ["home_care", "logistics"], blamed
    assert "coordinator" not in blamed and "synthesizer" not in blamed


@check("no readable previous turn means NO attribution — the caller keeps the old behaviour")
def _():
    reset()
    import core.orchestrator as O
    import core.persona as PZ
    saved = PZ.persona_data_dir
    PZ.persona_data_dir = _data_dir
    try:
        assert O._corrected_agents(PERSONA) == []
    finally:
        PZ.persona_data_dir = saved


def main() -> int:
    for name, ok, detail in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"\n      {detail}" if detail else ""))
    passed = sum(1 for _n, ok, _d in _results if ok)
    print(f"\n{passed}/{len(_results)} passed")
    shutil.rmtree(TMP, ignore_errors=True)
    return 0 if passed == len(_results) else 1


if __name__ == "__main__":
    sys.exit(main())
