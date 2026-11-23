"""
tests/test_clarification_hold.py — a turn the Coordinator marks ambiguous is MEASURED (shadow),
and held only once the figures say it is safe; Mental Wellbeing and Physical Health are never
held (Stage 2 M7, D-S2-4 shadow first, review S1/S2).

Shadow is what ships: code records what it would hold on the trace and changes nothing. The
live paths are exercised with `_CLARIFY_HOLD_LIVE` patched True.

`_run_single_agent` and tools.data_objects are stubbed; no model is called.

Run:  python3 tests/test_clarification_hold.py   (or pytest)
"""

from __future__ import annotations

import inspect
import json
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.orchestrator as orch  # noqa: E402
import core.trace as _tr  # noqa: E402
import tools.logger as logger_mod  # noqa: E402
from tools import turn_context as _turn  # noqa: E402

VALUE = "Ella or Bella — which one?"

FIVE = ('[{"agent": "relationships", "directive": "d"}, {"agent": "logistics", "directive": "d"},'
        ' {"agent": "finance", "directive": "d"}, {"agent": "mental_wellbeing", "directive": "d"},'
        ' {"agent": "physical_health", "directive": "d"}]')


def _coord(clarify: str | None = VALUE, specs: str = FIVE, data_objects: bool = True) -> str:
    out = "RESOLVED_INTENT: x\n"
    if clarify is not None:
        out += f"CLARIFICATION_NEEDED: {clarify}\n"
    if data_objects:
        out += 'DATA_OBJECTS: [{"name": "Reading list", "act": "add"}]\n'
    return out + f"SPECIALISTS_TO_CALL:\n```json\n{specs}\n```\n"


@contextmanager
def data_objects_stub():
    import tools.data_objects as DO
    marks: list[str] = []
    obj = {"id": "obj1", "name": "Reading list", "status": "active", "store": "archive"}
    with mock.patch.object(DO, "resolve", lambda name: obj), \
            mock.patch.object(DO, "read_only", lambda o: False), \
            mock.patch.object(DO, "public", lambda o: dict(o)), \
            mock.patch.object(DO, "fields_of", lambda o: {}), \
            mock.patch.object(DO, "mark_pending", lambda oid: marks.append(oid) or "tok1"), \
            mock.patch.object(DO, "close_match", lambda name: None):
        yield marks


@contextmanager
def bound_trace():
    t = _tr.start_request_trace("x", None)
    try:
        yield t
    finally:
        _tr.set_trace(None)
        _tr._set_current_agent(None)


def _dispatch(coord: str, clarify, outputs: dict | None = None):
    ran: list[str] = []

    def _fake(agent_name, directive, *a, **k):
        ran.append(agent_name)
        return (outputs or {}).get(agent_name, f"{agent_name} ok")

    with mock.patch.object(orch, "_run_single_agent", _fake):
        out = orch._dispatch_from_coordinator(coord, user_turn=True, clarify=clarify)
    return sorted(ran), out


def test_case1_parser():
    for v in ("none", "N/A", "[if applicable — what needs clarifying]", "No clarification needed",
              "Not needed", "Nothing to clarify"):
        assert orch._clarification_needed(_coord(v)) is None, v
    assert orch._clarification_needed(_coord(VALUE)) == VALUE
    assert orch._clarification_needed(_coord(None)) is None
    assert orch._clarification_shape("Not needed") == "negation"
    assert orch._clarification_shape("[if applicable]") == "bracket"
    assert orch._clarification_shape("none") == "null-ish"


def test_case2_shadow_changes_nothing_and_records():
    assert orch._CLARIFY_HOLD_LIVE is False
    coord = _coord()
    with bound_trace() as t, data_objects_stub() as marks, _turn.turn_scope(user_turn=True):
        clarify = orch._clarify_begin(coord)
        assert clarify == VALUE and "clarify_hold" not in _turn.current()
        data_turn = orch._resolve_data_objects(coord, persona="zz_clarify_test", user_turn=True, hold_writes=False)
        orch._clarify_shadow_record(coord, data_turn, True)
        ran, _ = _dispatch(coord, clarify)
        ann = t.annotations["clarification"]
    assert ran == ["finance", "logistics", "mental_wellbeing", "physical_health",
                   "relationships"]
    assert marks == ["obj1"]                              # the add still marks pending
    assert orch._clarify_note(clarify) == ""              # Synthesizer input byte-identical
    assert ann["would_hold"] == ["diarist", "finance", "logistics", "relationships"]
    assert ann["would_skip_writes"] == ["add"]
    assert ann["value_shape"] == "free text" and ann["chars"] == len(VALUE)
    assert VALUE not in json.dumps(ann) and "Ella" not in json.dumps(ann)


def test_case3_shadow_rejected_value_recorded():
    coord = _coord("Not needed")
    with bound_trace() as t:
        orch._clarify_shadow_record(coord, None, True)
        ann = t.annotations["clarification"]
    assert ann["value_shape"] == "negation" and ann["would_hold"] == []


def test_case3b_no_line_no_annotation():
    with bound_trace() as t:
        orch._clarify_shadow_record(_coord(None), None, True)
        assert t.annotations == {}


def test_case4_synth_redispatched():
    coord = _coord(data_objects=False)
    with bound_trace() as t:
        orch._clarify_shadow_record(coord, None, True)
        synth = _tr.AgentRecord(agent="synthesizer", provider="", model="")
        t.pipeline.append(synth)
        _tr.record_tool_call(synth, 1, "run_subagent", {"agent_name": "logistics"}, "ok", 1.0)
        _tr.record_tool_call(synth, 1, "run_subagent", {"agent_name": "physical_health"}, "ok", 1)
        orch._clarify_shadow_finish()
        assert t.annotations["clarification"]["synth_redispatched"] == ["logistics"]


def test_case5_live_paths():
    coord = _coord()
    with mock.patch.object(orch, "_CLARIFY_HOLD_LIVE", True), data_objects_stub() as marks, \
            _turn.turn_scope(user_turn=True):
        clarify = orch._clarify_begin(coord)
        assert _turn.current()["clarify_hold"] is True
        ran, _ = _dispatch(coord, clarify)
        assert ran == ["mental_wellbeing", "physical_health"]
        orch._resolve_data_objects(coord, persona="zz_clarify_test", user_turn=True, hold_writes=True)
        assert marks == []

        synth = _tr.AgentRecord(agent="synthesizer", provider="", model="")
        handled: list = []
        handlers = {"run_subagent": lambda agent_name="", **k: handled.append(agent_name) or "ok",
                    "update_task": lambda **k: handled.append("update_task") or "ok"}
        r1 = orch.dispatch_tool("run_subagent", {"agent_name": "relationships"}, handlers,
                                _agent_rec=synth)
        r2 = orch.dispatch_tool("update_task", {"task_id": "t1"}, handlers, _agent_rec=synth)
        r3 = orch.dispatch_tool("run_subagent", {"agent_name": "physical_health"}, handlers,
                                _agent_rec=synth)
        assert r1.startswith("Error: not recorded —") and r2.startswith("Error: not recorded —")
        assert r3 == "ok" and handled == ["physical_health"]
        assert [tc.ok for tc in synth.turns[0].tool_calls] == [False, False, True]

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(logger_mod, "_logs_dir", return_value=Path(tmp)):
            orch._persist_routing_miss({"agent": "logistics", "detail": "missed the trip"})
            assert not (Path(tmp) / "quality_events.json").exists()
        note = orch._clarify_note(clarify)
        assert note.startswith("\n\nCLARIFICATION NEEDED (from code)") and VALUE in note


def test_case6_medication_flag_survives_both_modes():
    outputs = {"physical_health": "FLAGS: MEDICATION_MISSED_CRITICAL"}
    coord = _coord(data_objects=False)
    for live in (False, True):
        with mock.patch.object(orch, "_CLARIFY_HOLD_LIVE", live):
            _, out = _dispatch(coord, VALUE, outputs=outputs)
            out = orch._drop_unprompted_clinical_flags(out, user_turn=True)
        assert "MEDICATION_MISSED_CRITICAL" in out["physical_health"], live


def test_case7_both_twins_wired():
    assert "_clarification_needed(coord_output)" in inspect.getsource(orch._clarify_begin)
    for fn in (orch.run_pipeline_session, orch._run_pipeline_session_stream_inner):
        src = inspect.getsource(fn)
        assert "clarify = _clarify_begin(coord_output, nudge)" in src, fn.__name__
        assert "clarify=clarify," in src and "_clarify_shadow_record(coord_output" in src
        assert "synthesizer_input += _clarify_note(clarify)" in src
        assert "_clarify_shadow_finish()" in src
        assert "hold_writes=bool(clarify) and _CLARIFY_HOLD_LIVE" in src


def test_case8_serialize_annotations_only_when_set():
    t = _tr.RequestTrace("x", None)
    assert "annotations" not in _tr._serialize(t, 1)
    t.annotations["clarification"] = {"value_shape": "free text"}
    assert _tr._serialize(t, 1)["annotations"] == {"clarification": {"value_shape": "free text"}}


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except Exception as exc:  # noqa: BLE001
                failures += 1
                print(f"  FAIL  {name} — {type(exc).__name__}: {exc}")
    print(f"\n{'all passed' if not failures else f'{failures} failed'}")
    sys.exit(1 if failures else 0)
