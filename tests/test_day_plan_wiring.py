"""
tests/test_day_plan_wiring.py — the day planner where it meets the pipeline and the server
(archive/plans/day_planner_plan_2026-10-24.md § 6, § 7.2, § 11.1).

Pins that both pipeline twins carry the plan block, the schedule-impact parser and nudge mode
("a feature wired into only one of the two is live in tests and dead in production"), then
exercises them: the block is off until its flag, the conduct module rides on the block, the
quiet directive never demotes the two fixed sessions (review R1-2), a nudge skips the
Coordinator and binds no scheduled-run kind, and the server's nudge mode holds and speaks.

Every model call, database write and live meter is stubbed. Run it:

    python3 tests/test_day_plan_wiring.py
"""
from __future__ import annotations

import asyncio
import inspect
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault("METATRON_AUTH_PASSWORD", "test-password-not-the-real-one")

import core.orchestrator as ORC  # noqa: E402
import core.persona as P  # noqa: E402
import tools.day_plan_config as C  # noqa: E402

_results: list[tuple[str, bool, str]] = []
_PERSONA = "dp_wiring"


def check(name: str, cond=None):
    if cond is not None:
        _results.append((name, bool(cond), ""))
        return None

    def deco(fn):
        try:
            with P.persona_scope(_PERSONA):
                fn()
            _results.append((name, True, ""))
        except Exception as exc:  # noqa: BLE001
            _results.append((name, False, f"{type(exc).__name__}: {exc}"))
        finally:
            C._OVERRIDE = None
        return fn
    return deco


# --- source pins: both twins -----------------------------------------------------------------

for label, fn in (("non-streaming", ORC.run_pipeline_session),
                  ("streaming", ORC._run_pipeline_session_stream_inner)):
    body = inspect.getsource(fn)
    check(f"{label} twin builds the plan block after the specialists and puts it in the package",
          "plan_text = _day_plan_block(persona, kind, is_proactive)" in body
          and '+ (f"\\n\\n{plan_text}" if plan_text else "")' in body
          and body.index("_dispatch_from_coordinator") < body.index("_day_plan_block"))
    check(f"{label} twin parses the Coordinator's SCHEDULE_IMPACT line",
          "_handle_schedule_impact(coord_output, persona, is_proactive)" in body)
    check(f"{label} twin skips the Coordinator and specialists on a nudge",
          "_NUDGE_PACKAGE if nudge else" in body
          and "specialist_outputs = {} if nudge else _dispatch_from_coordinator(" in body)
    check(f"{label} twin binds no scheduled-run kind on a nudge (R1-2)",
          "kind = None if nudge else session_kind(user_input, persona)" in body
          and 'focus_block = "" if nudge else _scheduled_focus_block(kind)' in body)

check("the streaming wrapper passes nudge through to the inner generator",
      "attachments=attachments, source=source, nudge=nudge," in inspect.getsource(
          ORC.run_pipeline_session_stream))
_caldav_src = (Path(__file__).parent.parent / "tools" / "caldav.py").read_text()
check("S-4: every calendar write, move and delete tells the planner (the same-reply repair is wired)",
      _caldav_src.count("    _note_plan_write()\n    return") == 3
      and "from tools.day_plan import note_calendar_write" in _caldav_src)
_server_src = (Path(__file__).parent.parent / "core" / "server.py").read_text()
check("the server passes nudge into the pipeline and adds proactive to the message broadcast",
      "source=source, nudge=nudge," in _server_src
      and '"proactive": proactive,\n                        }, exclude=websocket)' in _server_src)


# --- functional ------------------------------------------------------------------------------

@check("the plan block is empty while synth_reads_plan is off")
def _():
    C._OVERRIDE = {"flags": {"synth_reads_plan": False}}
    assert ORC._day_plan_block(_PERSONA, None, False) == ""


@check("the conduct module is injected when — and only when — the plan block is in the package")
def _():
    with_plan = ORC._synth_conditional_sections(None, f"x\n\n{ORC._DAY_PLAN_MARKER} from ...")
    without = ORC._synth_conditional_sections(None, "x")
    assert "day plan" in with_plan.lower() and with_plan != without, with_plan[:200]
    assert "day plan" not in without.lower()


@check("the quiet directive never applies to morning_brief or evening_close (R1-2)")
def _():
    import tools.context_tracker as CT
    real = CT.note_scheduled_run
    CT.note_scheduled_run = lambda kind, at=None: {"nothing_new": True, "hours_since": 2,
                                                  "open_questions": [], "may_reask": []}
    try:
        assert "NOTHING NEW" in ORC._scheduled_focus_block("companion_checkin")
        assert "NOTHING NEW" not in ORC._scheduled_focus_block("evening_close")
        assert "NOTHING NEW" not in ORC._scheduled_focus_block("morning_brief")
    finally:
        CT.note_scheduled_run = real


@check("SCHEDULE_IMPACT: recorded on a user turn (minor and major); never on a scheduled one or for none")
def _():
    import tools.day_plan as D
    seen = []
    real = D.note_schedule_impact
    D.note_schedule_impact = lambda level, text, persona=None: seen.append((level, text))
    try:
        pkg = "USER_STATE: x\nSCHEDULE_IMPACT: major — my afternoon got cancelled\nSPECIALISTS_TO_CALL: []"
        ORC._handle_schedule_impact(pkg, _PERSONA, is_proactive=True)
        ORC._handle_schedule_impact("SCHEDULE_IMPACT: none", _PERSONA, is_proactive=False)
        ORC._handle_schedule_impact(pkg, _PERSONA, is_proactive=False)
        ORC._handle_schedule_impact("SCHEDULE_IMPACT: minor - running 20 min late", _PERSONA, False)
    finally:
        D.note_schedule_impact = real
    assert seen == [("major", "my afternoon got cancelled"), ("minor", "running 20 min late")], seen


@check("a nudge runs the Synthesizer alone and closes the turn with no scheduled-run kind")
def _():
    calls, closed = [], []
    saved = {k: getattr(ORC, k) for k in ("_run_single_agent", "_load_coordinator_context",
                                          "_spend_gate", "persist_context_block",
                                          "_close_turn_bookkeeping", "_pending_tokens")}
    saved_tr = (ORC._tr.start_request_trace, ORC._tr.finish_request_trace)
    ORC._run_single_agent = lambda agent, *a, **k: (calls.append(agent), "[HOLD]")[1]
    ORC._load_coordinator_context = lambda persona=None: ""
    ORC._spend_gate = lambda: None
    ORC.persist_context_block = lambda *a, **k: None
    ORC._close_turn_bookkeeping = lambda visible, ui, pro, kind: closed.append(kind)
    ORC._pending_tokens = lambda persona=None: set()
    ORC._tr.start_request_trace = lambda *a, **k: None
    ORC._tr.finish_request_trace = lambda *a, **k: None
    C._OVERRIDE = {"flags": {"synth_reads_plan": False}}
    try:
        out = ORC.run_pipeline_session("DAY PLAN — due now. (1) 15:30 nudge: leave", persona=_PERSONA,
                                       is_proactive=True, nudge=True)
    finally:
        for k, v in saved.items():
            setattr(ORC, k, v)
        ORC._tr.start_request_trace, ORC._tr.finish_request_trace = saved_tr
    assert calls == ["synthesizer"], calls
    assert closed == [None], closed
    assert out.strip() == "[HOLD]", out


@check("the module's example sentences pass the output filter unchanged (plan § 6.3)")
def _():
    text = (Path(__file__).parent.parent / "config" / "modules" / "synthesizer_day_plan.md").read_text()
    examples = ["Time to head to physio — about 25 minutes on the Tube.",
                "I'll rework the rest of your afternoon around that.",
                "This eats into your evening because the return is due tomorrow.",
                # Round 2 (plan § 18): the one-line ask, the meal question, the rule offer.
                "Your partner's out voting at ten — are you on the kids?",
                "during the playdate — is that also lunch?",
                "You've had the kids every time your partner's been out at a weekend — shall I "
                "assume that from now on?"]
    for ex in examples:
        assert ex in text, ex
        assert ORC.filter_output(ex, "synthesizer") == ex, ex


# --- the server's nudge mode -----------------------------------------------------------------

def _server_case(reply_chunks: list[str]):
    import core.server as S
    from core import auth
    from fastapi.testclient import TestClient
    saves, logs = [], []

    async def _recent(*a, **k):
        return []

    async def _none(*a, **k):
        return None

    async def _save(persona, xid, user, assistant, proactive=False, attachments=None):
        saves.append({"assistant": assistant, "proactive": proactive})
        return 1

    async def _bind(*a, **k):
        return None

    def _fake_stream(*a, **k):
        assert k.get("nudge") is True, k
        for c in reply_chunks:
            yield c
        yield "[DONE]"

    patch = {"_get_recent_exchanges": _recent, "_get_exchange": _none, "_save_exchange": _save,
             "_bind_attachments": _bind, "run_pipeline_session_stream": _fake_stream,
             "_log_conversation": lambda *a, **k: logs.append(a)}
    saved = {k: getattr(S, k) for k in patch}
    for k, v in patch.items():
        setattr(S, k, v)
    S._session_history.pop(_PERSONA, None)
    try:
        client = TestClient(S.app, base_url="https://testserver")
        frames = []
        with client.websocket_connect(f"/ws?persona={_PERSONA}") as ws:
            ws.send_json({"type": "auth", "token": auth.issue_token()})
            assert ws.receive_json()["type"] == "auth_ok"
            assert ws.receive_json()["type"] == "history"
            ws.send_json({"type": "send", "exchange_id": "x1", "input": "DAY PLAN — due now.",
                          "proactive": True, "nudge": True})
            while True:
                f = ws.receive_json()
                if f.get("type") == "ping":
                    continue
                frames.append(f)
                if f.get("type") in ("held", "done", "error", "retract"):
                    break
    finally:
        for k, v in saved.items():
            setattr(S, k, v)
    return frames, saves, logs


@check("server nudge mode: a reply of exactly [HOLD] sends 'held' and records nothing")
def _():
    frames, saves, logs = _server_case(["[HOLD]"])
    assert frames[-1]["type"] == "held", frames
    assert saves == [] and logs == [], (saves, logs)


@check("server nudge mode: a spoken nudge is saved once, as proactive")
def _():
    frames, saves, logs = _server_case(["Time to head ", "to physio."])
    assert frames[-1]["type"] == "done", frames
    assert len(saves) == 1 and saves[0]["proactive"] is True, saves
    assert saves[0]["assistant"] == "Time to head to physio.", saves


def main() -> int:
    passed = sum(1 for _, ok, _ in _results if ok)
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if detail else ""))
    print(f"\n{passed} passed, {len(_results) - passed} failed, {len(_results)} total")
    return 0 if passed == len(_results) else 1


if __name__ == "__main__":
    sys.exit(main())
