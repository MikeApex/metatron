"""
tests/test_whole_person_sessions.py — the scheduled morning brief and day close always hear
from Mental Wellbeing and Physical Health, and those two record nothing from a turn with no
user words (Stage 2 #2, D4 + S6, D-S2-2, review S5/L9, build-time amendments 1 and 4).

`_run_single_agent` is stubbed; no model is called.

Run:  python3 tests/test_whole_person_sessions.py   (or pytest)
"""

from __future__ import annotations

import inspect
import sys
import tempfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.orchestrator as orch  # noqa: E402
import core.trace as _tr  # noqa: E402
from core.actions import action_provenance_block  # noqa: E402
from core.persona import current_persona, persona_scope  # noqa: E402
from tools import turn_context as _turn  # noqa: E402


def _coord(specs: str = "[]") -> str:
    return f"RESOLVED_INTENT: x\nSPECIALISTS_TO_CALL:\n```json\n{specs}\n```\n"


def _dispatch(coord: str, session, outputs: dict | None = None, persona=None,
              user_turn: bool = False):
    calls: list[dict] = []

    def _fake(agent_name, directive, persona=None, provider=None, attachments=None,
              complexity=None, **kw):
        calls.append({"agent": agent_name, "directive": directive, "mode": complexity,
                      "persona": persona, "bound": current_persona()})
        return (outputs or {}).get(agent_name, f"{agent_name} ok")

    with mock.patch.object(orch, "_run_single_agent", _fake):
        out = orch._dispatch_from_coordinator(coord, persona=persona, user_turn=user_turn,
                                              session=session)
    return {c["agent"]: c for c in calls}, out


MW_TONE = orch._whole_person_directive("mental_wellbeing", "morning_brief")
PH_SCAN = orch._whole_person_directive("physical_health", "morning_brief")


def test_directives_are_fixed_and_generic():
    assert "Give tone context only" in MW_TONE and "Raise no clinical history" in MW_TONE
    assert "proactive scan" in PH_SCAN
    for d in (MW_TONE, PH_SCAN):
        assert "Scheduled morning brief" in d and "do not call write_log" in d
    assert "Scheduled day close" in orch._whole_person_directive("physical_health",
                                                                   "evening_close")


def test_case1_empty_list_on_brief_adds_both():
    calls, _ = _dispatch(_coord(), "morning_brief")
    assert set(calls) == {"mental_wellbeing", "physical_health"}
    # Amendment 4: Mental Wellbeing quick (tone only), Physical Health deep.
    assert calls["mental_wellbeing"]["mode"] == "quick"
    assert calls["physical_health"]["mode"] == "deep"
    assert calls["mental_wellbeing"]["directive"] == MW_TONE
    assert calls["physical_health"]["directive"] == PH_SCAN


def test_case1b_listed_mental_wellbeing_directive_replaced():
    coord = _coord('[{"agent": "Mental Wellbeing", "mode": "deep", '
                   '"directive": "Ask about the disclosure from last week."}]')
    calls, _ = _dispatch(coord, "morning_brief")
    assert calls["mental_wellbeing"]["directive"] == MW_TONE
    assert calls["mental_wellbeing"]["mode"] == "quick"


def test_case2_listed_physical_health_kept_mode_forced():
    coord = _coord('[{"agent": "Physical Health", "mode": "quick", '
                   '"directive": "Check the knee."}]')
    calls, _ = _dispatch(coord, "morning_brief")
    assert list(calls).count("physical_health") == 1
    assert calls["physical_health"]["mode"] == "deep"
    # Review 3(a): the kept directive carries the same "nothing is kept" line.
    assert calls["physical_health"]["directive"] == "Check the knee.\n\n" + orch._NOTHING_KEPT_LINE


def test_review5_user_turn_matching_brief_prompt_keeps_normal_directive():
    coord = _coord('[{"agent": "Mental Wellbeing", "mode": "deep", '
                   '"directive": "The user says they slept badly; read their mood."}]')
    calls, _ = _dispatch(coord, "morning_brief", user_turn=True)
    assert set(calls) == {"mental_wellbeing"}             # nothing added on a user turn
    assert calls["mental_wellbeing"]["directive"] == \
        "The user says they slept badly; read their mood."
    assert calls["mental_wellbeing"]["mode"] == "deep"


def test_case3_evening_close_same():
    calls, _ = _dispatch(_coord(), "evening_close")
    assert set(calls) == {"mental_wellbeing", "physical_health"}
    assert "Scheduled day close" in calls["mental_wellbeing"]["directive"]


def test_case4_5_6_other_sessions_add_nothing():
    for session in (None, "companion_checkin"):
        calls, _ = _dispatch(_coord('[{"agent": "logistics", "directive": "d"}]'), session)
        assert set(calls) == {"logistics"}, session
    # A nudge passes session=None and the package lists nothing.
    calls, _ = _dispatch(orch._NUDGE_PACKAGE, None)
    assert calls == {}


def _guard_call(agent: str, name: str, user_turn: bool | None):
    handled: list = []
    handlers = {name: lambda **kw: handled.append(kw) or "written"}
    rec = _tr.AgentRecord(agent=agent, provider="", model="")
    if user_turn is None:
        result = orch.dispatch_tool(name, {"content": "x"}, handlers, _agent_rec=rec)
    else:
        with _turn.turn_scope(user_turn=user_turn):
            result = orch.dispatch_tool(name, {"content": "x"}, handlers, _agent_rec=rec)
    return result, handled, rec


def test_case7_guard_refuses_mental_wellbeing_write_log():
    result, handled, rec = _guard_call("mental_wellbeing", "write_log", False)
    assert result.startswith("Error: not recorded —")
    assert handled == []
    tc = rec.turns[0].tool_calls[0]
    assert tc.name == "write_log" and tc.ok is False
    # Amendment 1 + review 3(b): the ACTIONS block shows it as not done — as a designed
    # refusal, not a failure — and it is not reported upward as a failed tool call.
    trace = _tr.RequestTrace("x", None)
    trace.pipeline.append(rec)
    block = action_provenance_block(trace)
    assert "write_log — not recorded (scheduled session)" in block, block
    assert "ATTEMPTED AND FAILED" not in block and "completed" not in block
    assert orch._failed_tool_calls(rec) == []


def test_review3b_real_failure_still_reported_beside_refusal():
    _, _, rec = _guard_call("mental_wellbeing", "write_log", False)
    _tr.record_tool_call(rec, 1, "write_agent_config", {}, "Error: disk full", 1.0, ok=False)
    assert orch._failed_tool_calls(rec) == ["- write_agent_config: Error: disk full"]


def test_review4_fire_and_forget_followup_keeps_no_words_state():
    import threading
    import tools.logger as logger_mod
    from tools.subagent import run_subagent
    done = threading.Event()
    seen: dict = {}

    def _fake_run_session(agent_name, user_input="", persona=None, complexity=None, **kw):
        try:
            seen["proactive"] = kw.get("proactive")
            handled: list = []
            rec = _tr.AgentRecord(agent=agent_name, provider="", model="")
            seen["write"] = orch.dispatch_tool("write_log", {"content": "x"},
                                               {"write_log": lambda **k: handled.append(k)},
                                               _agent_rec=rec)
            seen["handled"] = handled
            logger_mod.write_quality_event("ROUTING_MISS", agent_name, "missed something")
            seen["turn_after"] = _turn.current()
        finally:
            done.set()
        return "ok"

    with tempfile.TemporaryDirectory() as tmp, \
            mock.patch.object(logger_mod, "_logs_dir", return_value=Path(tmp)), \
            mock.patch.object(orch, "run_session", _fake_run_session), \
            _turn.turn_scope(user_turn=False):
        out = run_subagent("physical_health", "scan", fire_and_forget=True)
        assert done.wait(5)
        events = (Path(tmp) / "quality_events.json").read_text().splitlines()
    assert out == "physical_health: dispatched (async)"
    assert seen["write"].startswith("Error: not recorded —") and seen["handled"] == []
    assert seen["proactive"] is True
    assert len(events) == 1 and '"scheduled": true' in events[0]


def test_review4_user_turn_fire_and_forget_unchanged():
    import threading
    from tools.subagent import run_subagent
    done = threading.Event()
    seen: dict = {}

    def _fake_run_session(agent_name, user_input="", persona=None, complexity=None, **kw):
        seen["turn"] = _turn.current()
        seen["proactive"] = kw.get("proactive")
        done.set()
        return "ok"

    with mock.patch.object(orch, "run_session", _fake_run_session), \
            _turn.turn_scope(user_turn=True):
        run_subagent("physical_health", "scan", fire_and_forget=True)
        assert done.wait(5)
    assert seen["turn"] is None and seen["proactive"] is None


def test_case8_guard_covers_physical_health_whole_set():
    for name in sorted(orch._NO_WORDS_REFUSED_WRITES):
        result, handled, _ = _guard_call("physical_health", name, False)
        assert result.startswith("Error: not recorded —") and handled == [], name
    assert orch._NO_WORDS_REFUSED_WRITES == {"write_log", "write_journal", "write_archive",
                                             "write_profile", "write_wisdom"}
    # Working notes stay allowed.
    result, handled, _ = _guard_call("physical_health", "write_agent_config", False)
    assert handled and result == "written"


def test_case9_user_turn_calls_handler():
    result, handled, _ = _guard_call("mental_wellbeing", "write_log", True)
    assert handled and result == "written"


def test_case10_other_agents_unaffected():
    result, handled, _ = _guard_call("logistics", "write_log", False)
    assert handled and result == "written"


def test_case11_no_turn_proactive_trace_calls_handler():
    _tr.start_request_trace("weekly physical review", None, is_proactive=True)
    try:
        result, handled, _ = _guard_call("physical_health", "write_log", None)
    finally:
        _tr.set_trace(None)
    assert handled and result == "written"


def test_case12_end_to_end_flags():
    outputs = {"mental_wellbeing": "TONE: steady\nFLAGS: CLINICAL_CONCERN: TEST, MOOD_LOW",
               "physical_health": "SCAN: ok\nFLAGS: MEDICATION_MISSED_CRITICAL"}
    _, out = _dispatch(_coord(), "morning_brief", outputs=outputs)
    out = orch._drop_unprompted_clinical_flags(out, user_turn=False)
    assert "CLINICAL_CONCERN" not in out["mental_wellbeing"]
    assert "MEDICATION_MISSED_CRITICAL" in out["physical_health"]


def test_case13_both_twins_pass_session():
    for fn in (orch.run_pipeline_session, orch._run_pipeline_session_stream_inner):
        src = inspect.getsource(fn)
        assert "data_turn=data_turn, user_text=user_input, session=kind, clarify=clarify," \
            in src, fn.__name__


def test_case14_second_persona():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        prompts = {"zz_a": "Good morning from the first fixture persona, time to plan the day.",
                   "zz_b": "Rise and shine second fixture persona, here is the brief for today."}
        for p, prompt in prompts.items():
            (root / p).mkdir()
            (root / p / "scheduler.yaml").write_text(
                f'schedules:\n  morning_brief:\n    prompt: "{prompt}"\n')
            (root / p / f"marker_{p}.txt").write_text(p)
        seen: list[str] = []

        def _cfg_dir(persona=None):
            seen.append(persona)
            return root / persona

        from core.persona import persona_data_dir
        b_data = persona_data_dir("zz_b")
        existed = b_data.exists()
        try:
            with mock.patch.object(orch, "persona_config_dir", _cfg_dir):
                kind = orch.session_kind(prompts["zz_b"], "zz_b")
                assert kind == "morning_brief"
                with persona_scope("zz_b"):
                    calls, _ = _dispatch(_coord(), kind, persona="zz_b")
                assert orch.session_kind(prompts["zz_a"], "zz_b") is None
        finally:
            if not existed:
                import shutil
                shutil.rmtree(b_data, ignore_errors=True)
        assert "zz_a" not in seen
    assert set(calls) == {"mental_wellbeing", "physical_health"}
    for c in calls.values():
        assert c["persona"] == "zz_b" and c["bound"] == "zz_b"


def test_a4_disclosure_fixture_offline():
    """The A4 MW-NO-REPLAY scenario, exercised OFFLINE (no live A4 run this stage): the runner
    sends the real directive on a no-words turn, judges by absence, and the seed cleans up."""
    sys.path.insert(0, str(Path(__file__).parent))
    import run_a4_safety as A4
    scenario = next(s for s in A4.CLINICAL if s["id"] == "MW-NO-REPLAY")
    seen: list[dict] = []

    def _fake(agent, prompt, persona=None, provider=None, complexity=None, **kw):
        seen.append({"prompt": prompt, "complexity": complexity,
                     "user_turn": (_turn.current() or {}).get("user_turn")})
        return reply

    with mock.patch.object(orch, "_run_single_agent", _fake):
        reply = "TONE: steady and engaged in recent entries.\nFLAGS: none"
        clean = A4.run_one(scenario, "zz_a4_offline", None)
        reply = f"Last time you mentioned the {A4.DISCLOSURE_MARKERS[0]}.\nFLAGS: MUST_SURFACE"
        dirty = A4.run_one(scenario, "zz_a4_offline", None)
    assert clean["verdict"] == "PASS", clean["checks"]
    assert dirty["verdict"] == "FAIL"
    assert seen[0]["prompt"] == orch._whole_person_directive("mental_wellbeing", "morning_brief")
    assert seen[0]["complexity"] == "quick" and seen[0]["user_turn"] is False

    with tempfile.TemporaryDirectory() as tmp:
        with mock.patch("core.persona.persona_data_dir", lambda *a, **k: Path(tmp)):
            seeded = A4.seed_disclosure_fixture("zz_a4_offline")
            assert seeded[0].exists() and A4.DISCLOSURE_MARKERS[0] in seeded[0].read_text()
            A4.clear_disclosure_fixture(seeded)
            assert not seeded[0].exists()


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
