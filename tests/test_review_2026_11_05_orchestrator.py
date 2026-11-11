"""
tests/test_review_2026_11_05_orchestrator.py — the orchestrator fixes from the 2026-11-05
whole-codebase review (archive/plans/codebase_review_2026-11-05_fable-5-1.md), builder A of
archive/plans/codebase_review_fixes_plan_2026-11-11.md.

One test (or pair) per finding, each written to fail on `2dd492a`:

  2   a model-API failure logs the agent's NAME, not its record (whose repr carries the
      assembled prompt), and the MODEL_CALL_FAILED quality event is actually written
  3   dispatch_tool drops a model-supplied `persona`, so the bound persona is the one served
  4   record_wisdom_response is advertised to the Synthesizer and records through dispatch;
      the grant guard fails when a granted name has a handler and no schema
  15  the blocking cached path never re-runs a tool when a later round fails
  16  a streamed turn that raises leaves no trace bound to the thread, so the next
      single-agent session on it passes the daily stop
  21  a wisdom proposal from a turn that read mail is filed `observed`, never `stated`

No model call, no network, no file written under data/: every meter a seam ends in is
stubbed (the Vertex client, the compat fallback, router.log_model_error, the quality-event
directory, the trace writer, the wisdom store).

Run:
    python -m pytest -q tests/test_review_2026_11_05_orchestrator.py
    python tests/test_review_2026_11_05_orchestrator.py
"""

import contextlib
import importlib.util
import io
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import core.orchestrator as orch  # noqa: E402
import core.trace as _tr  # noqa: E402
from core.persona import persona_scope, resolve_persona  # noqa: E402

PERSONA = "danny_park"     # tracked synthetic persona; nothing below writes into its tree


# ---------------------------------------------------------------------------
# Finding 2 — _log_api_failure
# ---------------------------------------------------------------------------

def test_api_failure_logs_the_agent_name_and_writes_the_quality_event():
    secret = "ASSEMBLED-PROMPT-TEXT-THAT-MUST-NOT-REACH-THE-JOURNAL"
    records: list[logging.LogRecord] = []
    handler = logging.Handler()
    handler.emit = records.append
    model_errors: list[tuple] = []

    rec = _tr.push_agent("diarist", "gemini", "m", {"agent_file": secret, "config": secret})
    orch.logger.addHandler(handler)
    try:
        with tempfile.TemporaryDirectory() as td, \
                mock.patch("core.router.log_model_error", lambda *a: model_errors.append(a)), \
                mock.patch("tools.logger._logs_dir", lambda: Path(td)):
            # No `agent=` — the four compat call sites pass none, so the current agent is read.
            orch._log_api_failure("openai_compat[vertex]", "m", RuntimeError("429 RESOURCE_EXHAUSTED"))
            events_path = Path(td) / "quality_events.json"
            events = ([json.loads(line) for line in events_path.read_text().splitlines()]
                      if events_path.exists() else [])
    finally:
        orch.logger.removeHandler(handler)
        _tr.pop_agent(rec)

    messages = [r.getMessage() for r in records if "[model_error]" in r.getMessage()]
    assert messages, "no [model_error] line was logged"
    assert secret not in messages[0], "the agent record's repr — the prompt — reached the log"
    assert "agent=diarist" in messages[0], messages[0]
    assert all(secret not in str(a) for a in model_errors)
    assert [e["event_type"] for e in events] == ["MODEL_CALL_FAILED"], events
    assert events[0]["source_agent"] == "diarist"


# ---------------------------------------------------------------------------
# Finding 3 (dispatch half) — a model cannot name whose data a tool touches
# ---------------------------------------------------------------------------

def test_dispatch_drops_a_model_supplied_persona():
    served: list[str] = []

    def get_log_window(days: int = 7, persona: str | None = None) -> str:
        # The real tools resolve exactly like this: an explicit argument beats the binding.
        served.append(resolve_persona(persona))
        return "ok"

    with persona_scope(PERSONA):
        out = orch.dispatch_tool("get_log_window", {"days": 3, "persona": "zz_someone_else"},
                                 {"get_log_window": get_log_window})
    assert out == "ok"
    assert served == [PERSONA], f"tool served {served}, not the bound persona"


def test_dispatch_without_persona_is_unchanged():
    got: list[dict] = []
    with persona_scope(PERSONA):
        orch.dispatch_tool("t", {"days": 3}, {"t": lambda **kw: got.append(kw) or "ok"})
    assert got == [{"days": 3}]


# ---------------------------------------------------------------------------
# Finding 4 — record_wisdom_response is advertised, and the guard knows a handler is not enough
# ---------------------------------------------------------------------------

def _synth_grants() -> list[set]:
    import yaml
    out = []
    for name in ("routing.yaml", "routing_cloud.yaml"):
        cfg = yaml.safe_load((ROOT / "config" / "modules" / name).read_text())
        out.append(set(cfg["agents"]["synthesizer"]["allowed_tools"]))
    return out


def test_record_wisdom_response_is_advertised_to_the_synthesizer():
    import inspect
    schemas, handlers = orch.register_tools()
    by_name = {s["name"]: s for s in schemas}
    assert "record_wisdom_response" in by_name, "no schema — the model is never shown the tool"
    for granted in _synth_grants():
        assert "record_wisdom_response" in granted
        advertised = {s["name"] for s in schemas if s["name"] in granted}
        assert "record_wisdom_response" in advertised
    # The schema describes the handler it is registered beside.
    params = inspect.signature(handlers["record_wisdom_response"]).parameters
    props = by_name["record_wisdom_response"]["input_schema"]["properties"]
    assert set(props) <= set(params), set(props) - set(params)
    required = {n for n, p in params.items() if p.default is inspect.Parameter.empty}
    assert set(by_name["record_wisdom_response"]["input_schema"]["required"]) == required


def test_record_wisdom_response_records_through_dispatch():
    import tools.wisdom as W
    schemas, handlers = orch.register_tools()
    synth_allowed = {s["name"] for s in schemas if s["name"] in _synth_grants()[1]}
    with tempfile.TemporaryDirectory() as td:
        store = Path(td) / "wisdom.json"
        store.write_text(json.dumps([{"key": "late_starter", "value": "starts work late",
                                      "domain": "work", "provenance": "observed",
                                      "user_response": "pending"}]))
        with mock.patch.object(W, "_wisdom_path", lambda: store), \
                mock.patch.object(W, "_lock_path", lambda: Path(td) / "wisdom.lock"):
            out = orch.dispatch_tool(
                "record_wisdom_response",
                {"key": "late_starter", "response": "denied", "pushback": "no, I start at 7"},
                handlers, _allowed=synth_allowed)
        entry = json.loads(store.read_text())[0]
    assert out.startswith("Recorded"), out
    assert entry["user_response"] == "denied"
    assert entry["user_pushback"] == "no, I start at 7"
    assert entry["provenance"] == "observed"


def _run_guard(register_tools=None) -> tuple[int, str]:
    spec = importlib.util.spec_from_file_location(
        "check_agent_tools_under_test", ROOT / "scripts" / "check_agent_tools.py")
    guard = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = guard     # the script's @dataclass resolves its module by name
    try:
        spec.loader.exec_module(guard)
    finally:
        sys.modules.pop(spec.name, None)
    buf = io.StringIO()
    patch = (mock.patch.object(orch, "register_tools", register_tools)
             if register_tools else contextlib.nullcontext())
    with patch, mock.patch.object(sys, "argv", ["check_agent_tools.py", "--quiet"]), \
            contextlib.redirect_stdout(buf):
        code = guard.main()
    return code, buf.getvalue()


def test_guard_fails_on_a_granted_handler_with_no_schema():
    real = orch.register_tools

    def without_schema():
        schemas, handlers = real()
        return [s for s in schemas if s["name"] != "record_wisdom_response"], handlers

    code, out = _run_guard(without_schema)
    assert code == 1, "a granted name with a handler and no schema read as built"
    assert "record_wisdom_response" in out and "handler only, no schema" in out, out[-2000:]


def test_guard_passes_with_the_schema_registered():
    code, out = _run_guard()
    assert code == 0, out[-2000:]


# ---------------------------------------------------------------------------
# Finding 15 — the blocking cached path never replays a tool
# ---------------------------------------------------------------------------

class _FC:
    def __init__(self, name, args):
        self.name, self.args = name, args


class _Part:
    def __init__(self, text=None, function_call=None):
        self.text, self.function_call = text, function_call


class _Resp:
    def __init__(self, parts):
        content = type("C", (), {"parts": parts, "role": "model"})()
        self.candidates = [type("Cand", (), {"content": content, "finish_reason": None})()]
        self.usage_metadata = None


class _FakeClient:
    """Round 1 asks for a write; every later round raises a non-404 API error."""

    def __init__(self, fail_from_round: int):
        self.calls = 0
        self.fail_from_round = fail_from_round
        self.models = self

    def generate_content(self, model, contents, config):
        self.calls += 1
        if self.calls >= self.fail_from_round:
            raise RuntimeError("500 INTERNAL: the backend fell over")
        return _Resp([_Part(function_call=_FC("save_thing", {"x": "dentist at 3"}))])


_SAVE_SCHEMA = {"name": "save_thing", "description": "Save a thing.",
                "input_schema": {"type": "object", "properties": {"x": {"type": "string"}}}}


def _cached_turn(client):
    writes: list[dict] = []
    fallback_calls: list[str] = []
    handlers = {"save_thing": lambda **kw: writes.append(kw) or "saved"}

    def compat_fallback(system_prompt, user_input, tool_schemas, tool_handlers, *a, **k):
        # What the real compat path does: re-run the turn from the top, tools included.
        fallback_calls.append(user_input)
        tool_handlers["save_thing"](x="dentist at 3")
        return "fallback reply"

    with mock.patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"}), \
            mock.patch.object(orch, "_get_vertex_native_client", lambda: client), \
            mock.patch.object(orch, "_get_or_create_vertex_cache", lambda *a, **k: "cachedContents/1"), \
            mock.patch.object(orch, "_refresh_vertex_cache", lambda *a, **k: None), \
            mock.patch.object(orch, "run_session_gemini", compat_fallback), \
            mock.patch("core.router.log_model_error", lambda *a, **k: None):
        out = orch.run_session_gemini_cached("sys", "move the dentist", [_SAVE_SCHEMA], handlers,
                                             model="gemini-test")
    return out, writes, fallback_calls


def test_cached_path_does_not_replay_a_write_after_a_later_round_fails():
    out, writes, fallback_calls = _cached_turn(_FakeClient(fail_from_round=2))
    assert len(writes) == 1, f"the write ran {len(writes)} times"
    assert fallback_calls == [], "the compat fallback re-ran a turn that had already written"
    assert out == orch._NO_REPLY_LINE


def test_cached_path_still_falls_back_when_nothing_ran():
    out, writes, fallback_calls = _cached_turn(_FakeClient(fail_from_round=1))
    assert fallback_calls == ["move the dentist"] and out == "fallback reply"
    assert len(writes) == 1   # the fallback's own, once


# ---------------------------------------------------------------------------
# Finding 16 — a failed streamed turn unbinds its trace
# ---------------------------------------------------------------------------

def test_failed_stream_turn_leaves_no_trace_and_the_next_session_is_gated():
    gate_calls: list[int] = []
    gate_reply = {"msg": None}

    def spend_gate():
        gate_calls.append(1)
        return gate_reply["msg"]

    def both_legs_fail(*a, **k):
        raise RuntimeError("coordinator: native and compat both failed")

    stubs = {
        "_spend_gate": spend_gate,
        "_pending_tokens": lambda *a, **k: set(),
        "_load_coordinator_context": lambda *a, **k: "",
        "session_kind": lambda *a, **k: None,
        "_bind_turn_kind": lambda *a, **k: None,
        "_scheduled_focus_block": lambda *a, **k: "",
        "_name_note": lambda *a, **k: "",
        "_run_single_agent": both_legs_fail,
    }
    _tr.set_trace(None)
    _tr._set_current_agent(None)
    try:
        with contextlib.ExitStack() as stack:
            for name, fn in stubs.items():
                stack.enter_context(mock.patch.object(orch, name, fn))
            stack.enter_context(mock.patch.object(_tr, "finish_request_trace", lambda *a: None))

            raised = False
            try:
                list(orch.run_pipeline_session_stream("hello", persona=PERSONA))
            except RuntimeError:
                raised = True
            assert raised, "the stub failure did not propagate"
            assert _tr.get_trace() is None, "the failed turn's trace is still bound to the thread"
            assert _tr.get_current_agent() is None

            gate_calls.clear()
            gate_reply["msg"] = "STOPPED FOR TODAY"
            out = orch.run_session("pattern_miner", "weekly review", persona=PERSONA)
            assert gate_calls, "the next session on this thread skipped _spend_gate()"
            assert out == "STOPPED FOR TODAY"
    finally:
        _tr.set_trace(None)
        _tr._set_current_agent(None)


# ---------------------------------------------------------------------------
# Finding 21 — mail- or page-derived proposals are never filed as stated
# ---------------------------------------------------------------------------

_PROPOSAL = ('Booked. WISDOM_PROPOSAL: {"key": "gym_mornings", "value": "trains at 6am", '
             '"domain": "fitness", "provenance": "stated"}')


def _file_one(tool_called: str | None, agent: str = "logistics") -> list[dict]:
    written: list[dict] = []
    _tr.start_request_trace("hello", PERSONA)
    try:
        rec = _tr.push_agent(agent, "gemini", "m")
        if tool_called:
            _tr.record_tool_call(rec, 1, tool_called, {}, "From: someone@example.com ...", 1.0)
        _tr.pop_agent(rec)
        with mock.patch("tools.wisdom.write_wisdom",
                        lambda **kw: written.append(kw) or "Recorded."), \
                mock.patch.object(orch, "_reroute_refused_complaint", lambda *a, **k: None):
            cleaned = orch._file_wisdom_proposals({agent: _PROPOSAL}, persona=PERSONA)
    finally:
        _tr.set_trace(None)
        _tr._set_current_agent(None)
    assert cleaned == {agent: "Booked."}
    return written


def test_proposal_from_a_turn_that_read_mail_is_filed_observed():
    # read_intake_queue (mail subjects/snippets) and read_calendar (invite text by outsiders)
    # added after the 2026-11-11 Fable code review.
    for tool in ("read_email", "fetch_url", "fetch_rendered", "read_intake_queue", "read_calendar"):
        written = _file_one(tool)
        assert [w["provenance"] for w in written] == ["observed"], (tool, written)


def test_proposal_from_the_research_agent_is_filed_observed():
    # Its grounded search happens inside the model call: no tool call to see.
    written = _file_one(None, agent="research_agent")
    assert [w["provenance"] for w in written] == ["observed"], written


def test_proposal_from_an_ordinary_turn_keeps_its_provenance():
    written = _file_one("read_wisdom")
    assert [w["provenance"] for w in written] == ["stated"]


if __name__ == "__main__":
    failures = []
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except Exception as exc:
                failures.append((name, exc))
                print(f"  FAIL  {name}: {exc!r}")
    print(f"\n{len(failures)} failed" if failures else "\nall passed")
    sys.exit(1 if failures else 0)
