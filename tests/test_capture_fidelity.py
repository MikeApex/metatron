"""
tests/test_capture_fidelity.py — capture fidelity (archive/plans/capture_fidelity_plan_2026-11-18.md § 7.1).

No model is called: the extractor (`tools.capture.extract`) and the interviewer's single-agent
run are stubbed, and the spend gate is stubbed so no meter file is touched. The persona tree
(config and data) is a temporary directory.

Run:
    python -m pytest -q tests/test_capture_fidelity.py
    python tests/test_capture_fidelity.py
"""

import inspect
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core import interview, orchestrator, persona as persona_mod  # noqa: E402
from core import trace as trace_mod  # noqa: E402
from tools import analytics, capture, day_shape  # noqa: E402

_tmp = Path(tempfile.mkdtemp(prefix="metatron-capture-"))
P = "cap_test"
P2 = "cap_other"

CFG = {**capture._DEFAULTS, "enabled": True, "holdout_rate": 0.0, "join_bound_s": 2.0}
EXTRACT = {"fn": None}
AGENT_CALLS: list[dict] = []
AGENT_SIDE = {"fn": None}


def _fake_extract(persona, user_input, history, kinds, trace=None):
    cands = EXTRACT["fn"](user_input) if EXTRACT["fn"] else []
    return {"candidates": cands, "rejected": 0, "ok": True, "ms": 5, "tin": 100, "tout": 20}


def _fake_single_agent(agent_name, user_input, persona=None, history=None, **kw):
    AGENT_CALLS.append({"agent": agent_name, "input": user_input})
    if AGENT_SIDE["fn"]:
        AGENT_SIDE["fn"](persona)
    return "ok"


_PATCHES = [
    (persona_mod, "_ROOT", _tmp), (trace_mod, "ROOT", _tmp), (analytics, "ROOT", _tmp),
    (capture, "config", lambda: dict(CFG)),
    (capture, "extract", _fake_extract),
    (orchestrator, "_run_single_agent", _fake_single_agent),
    (orchestrator, "_spend_gate", lambda: None),
]
_SAVED: list = []


def setup_module(module=None):
    for obj, name, value in _PATCHES:
        _SAVED.append((obj, name, getattr(obj, name)))
        setattr(obj, name, value)
    for p in (P, P2):
        cfg = _tmp / "config" / "personas" / p
        cfg.mkdir(parents=True, exist_ok=True)
        (cfg / "goals.yaml").write_text("quarterly: []\n")
        (_tmp / "data" / "personas" / p).mkdir(parents=True, exist_ok=True)


def teardown_module(module=None):
    while _SAVED:
        obj, name, value = _SAVED.pop()
        setattr(obj, name, value)


def _reset(p=P):
    d = _tmp / "data" / "personas" / p
    for f in ("day_shape.yaml",):
        (d / f).unlink(missing_ok=True)
    cap = d / "capture"
    if cap.exists():
        for f in cap.iterdir():
            f.unlink()
    AGENT_CALLS.clear()
    AGENT_SIDE["fn"] = None
    EXTRACT["fn"] = None


def _c(kind, target, proposal, disp="save", say="something plain"):
    clean = capture._validate_shape(target, proposal) if kind == "day_shape" else proposal
    return {"kind": kind, "target": target, "proposal": clean, "disposition": disp,
            "say": say, "quote": "q"}


def _rows(p=P):
    return capture.read_outcomes(p)


WEEKDAYS = ["mon", "tue", "wed", "thu", "fri"]


# --- 1. day-shape matcher ------------------------------------------------------------------------

def test_day_shape_matcher():
    c = _c("day_shape", "meals", {"name": "dinner", "days": WEEKDAYS, "from": "18:00",
                                  "to": "19:00"})
    same = [("set_day_shape", {"section": "meals", "entry": {"name": "dinner", "days": WEEKDAYS,
                                                             "from": "18:00", "to": "19:00"}})]
    seven = [("set_day_shape", {"section": "meals", "entry": {
        "name": "dinner", "days": WEEKDAYS + ["sat", "sun"], "from": "18:00", "to": "19:00"}})]
    assert capture.match(c, same) == "same"
    assert capture.match(c, seven) == "different"
    assert capture.match(c, []) is None
    # The first-version field form: a bare dinner time for every day is a mismatch, not a save.
    assert capture.match(c, [("set_day_shape", {"field": "dinner", "value": "18:00"})]) == "different"
    work = _c("day_shape", "work_end", "17:00")
    assert capture.match(work, [("set_day_shape", {"field": "work_end", "value": "17:00"})]) == "same"


def test_already_held_drops_a_repeat():
    _reset()
    from core.persona import persona_scope
    with persona_scope(P):
        day_shape.set_day_shape(section="travel_mode", entry="transit", evidence="I take the bus")
    c = _c("day_shape", "travel_mode", "transit")
    assert capture.already_held(P, c)
    assert not capture.already_held(P, _c("day_shape", "travel_mode", "driving"))


# --- 2. free-text matcher -----------------------------------------------------------------------

def test_free_text_matcher():
    c = _c("task", "task", "call the dentist about the crown this week")
    assert capture.match(c, [("open_task", {"what": "Call dentist re: crown"})]) == "same"
    assert capture.match(c, [("open_task", {"what": "buy milk"})]) is None
    assert capture.match(c, [("write_persona", {"content": "call the dentist crown"})]) is None
    for writes in ([("open_task", {"what": "Call dentist re: crown"})], []):
        assert capture.match(c, writes) in ("same", None)      # never "different" for free text


# --- 3. validation ------------------------------------------------------------------------------------

def test_validation_and_malformed_output():
    kinds = capture.AGENT_KINDS["synthesizer"]
    assert capture.parse("not json at all", kinds) == ([], 1)
    assert capture.parse("[]", kinds) == ([], 0)
    raw = json.dumps([
        {"kind": "day_shape", "target": "meals", "proposal": {"name": "dinner", "days": ["xyz"]},
         "disposition": "save", "say": "dinner at six", "quote": "q"},           # tool refuses
        {"kind": "day_shape", "target": "work_end", "proposal": "17:00", "disposition": "save",
         "say": "set work_end to five", "quote": "q"},                           # identifier
        {"kind": "task", "target": "task", "proposal": "call the dentist", "disposition": "save",
         "say": "a task to call the dentist", "quote": "q"},
        {"kind": "contact", "target": "x", "proposal": "y", "disposition": "save",
         "say": "not a v1 kind", "quote": "q"},
    ])
    cands, rejected = capture.parse(raw, kinds)
    assert [c["kind"] for c in cands] == ["task"] and rejected == 3


# --- 4. the trial_1029 replay, through the interviewer ----------------------------------------------

TRIAL_EIGHT = [
    _c("day_shape", "day", {"days": WEEKDAYS, "wake": "07:00", "bed": "00:00"},
       say="weekdays they wake at 7 and go to bed at midnight"),
    _c("day_shape", "travel_mode", "transit", say="they get around by public transport"),
    _c("day_shape", "meals", {"name": "dinner", "days": WEEKDAYS, "from": "18:00", "to": "19:00"},
       say="dinner is 6 to 7 on weekdays"),
    _c("day_shape", "location_sharing", "on", say="they share their location"),
    _c("day_shape", "work_start", "09:00", say="work starts at 9"),
    _c("day_shape", "work_end", "17:00", say="work ends at 5 and often runs late"),
    _c("day_shape", "day", {"days": ["sat", "sun"], "wake": "10:00"},
       say="on weekends they sleep in until about 10"),
    _c("day_shape", "windows", None, disp="ask",
       say="whether early afternoon should stay light after they crash out after lunch"),
]
TRIAL_EIGHT[-1]["proposal"] = None      # an ask carries no entry


def _trial_writes(persona):
    from core.persona import persona_scope
    with persona_scope(persona):
        day_shape.set_day_shape(section="day", entry={"days": WEEKDAYS, "wake": "07:00",
                                                      "bed": "00:00"}, evidence="7 till midnight")
        day_shape.set_day_shape(section="travel_mode", entry="transit", evidence="bus")
        day_shape.set_day_shape(section="meals", entry={"name": "dinner",
                                                        "days": WEEKDAYS + ["sat", "sun"],
                                                        "from": "18:00", "to": "19:00"},
                                evidence="dinner 6 to 7")
        day_shape.set_day_shape(section="location_sharing", entry="on", evidence="yes share")


def _wait_pending(p, n, timeout=3.0):
    end = time.time() + timeout
    while time.time() < end:
        cur = capture._read_json(capture._pending_path(p), [])
        if len(cur) >= n:
            return cur
        time.sleep(0.02)
    return capture._read_json(capture._pending_path(p), [])


def test_trial_1029_replay():
    _reset()
    CFG["cap"] = 8
    try:
        EXTRACT["fn"] = lambda text: [dict(c) for c in TRIAL_EIGHT]
        AGENT_SIDE["fn"] = _trial_writes
        interview.run_turn(P, "work is 9-5 but often runs late; weekends I sleep in", [])
        pending = _wait_pending(P, 4)
        lines = {c["say"]: c for c in pending}
        assert "work starts at 9" in lines and "work ends at 5 and often runs late" in lines
        assert "on weekends they sleep in until about 10" in lines
        slump = [c for c in pending if c["disposition"] == "ask"]
        assert len(slump) == 1 and "crash out" in slump[0]["say"]
        dinner = lines["dinner is 6 to 7 on weekdays"]
        assert dinner["_mismatch"] is True and capture._line(dinner).startswith("check:")
        # The five correct saves are silent — four written here, recorded as saved_by_agent.
        saved = [r for r in _rows() if r.get("outcome") == "saved_by_agent"]
        assert len(saved) == 3   # wake/bed, transport, location sharing
        assert all(c["say"] not in lines for c in TRIAL_EIGHT[:2])

        # 8. Shown once: the next turn's coverage block carries the lines, the one after does not.
        EXTRACT["fn"] = None
        AGENT_SIDE["fn"] = None
        interview.run_turn(P, "ok", [])
        assert "Said but not yet saved" in AGENT_CALLS[-1]["input"]
        assert "check: dinner is 6 to 7 on weekdays" in AGENT_CALLS[-1]["input"]
        interview.run_turn(P, "ok again", [])
        assert "Said but not yet saved" not in AGENT_CALLS[-1]["input"]
        assert any(r.get("outcome") == "not_acted" for r in _rows())
    finally:
        CFG["cap"] = 3


def test_proactive_interview_turn_reads_nothing():
    _reset()
    seen = []
    EXTRACT["fn"] = lambda text: seen.append(text) or []
    interview.run_turn(P, interview.OPENING_PROMPT, [], proactive=True)
    time.sleep(0.1)
    assert seen == [] and not _rows()


# --- 5. both pipeline twins wired the same way ----------------------------------------------------

def test_both_twins_carry_capture():
    ns = inspect.getsource(orchestrator.run_pipeline_session)
    st = inspect.getsource(orchestrator._run_pipeline_session_stream_inner)
    for src in (ns, st):
        assert '_capture.start(persona, user_input, history, "synthesizer", _capture_trace)' in src
        assert "has_real_user_turn(user_input, is_proactive, attachments)" in src
        assert "_capture.note_for_synthesizer(persona, capture_job, _capture_trace)" in src
        assert "capture_turn.note" in src
        assert "_capture.defer(capture_turn)" in src
        assert "_capture.after_synthesizer(capture_turn, _capture_trace)" in src
    # The extractor starts before the Coordinator and the note is built after the specialists.
    for src in (ns, st):
        assert src.index("_capture.start(") < src.index('"coordinator", coord_input')
        assert src.index("_dispatch_from_coordinator(") < src.index("note_for_synthesizer(")


def test_extractor_nests_in_the_users_trace():
    """The real extract(), run_session stubbed: inside a pipeline the call is the user turn's."""
    t = trace_mod.start_request_trace("hello", P)
    trace_mod.set_trace(None)
    saved = capture.extract
    capture.extract = _SAVED_EXTRACT
    try:
        calls = []

        def fake_run_session(agent, user_input, **kw):
            calls.append((agent, trace_mod.get_trace() is t, kw.get("bare")))
            return "[]"
        orig = orchestrator.run_session
        orchestrator.run_session = fake_run_session
        try:
            res = capture.extract(P, "I take the bus", None, ("day_shape",), trace=t)
        finally:
            orchestrator.run_session = orig
    finally:
        capture.extract = saved
    assert res["ok"] and calls == [("capture_extractor", True, True)]


def test_owned_extractor_call_is_not_counted_as_a_session():
    """The backfill and the interviewer own their trace: the spend cap is checked, but the
    call must not count toward stop_sessions_per_hour (it would refuse a live interview)."""
    from core import spend_guard
    seen = {"checked": 0}
    saved = (spend_guard.check_before_session, spend_guard.note_session_start,
             orchestrator.run_session, capture.extract)

    def no_note():
        raise AssertionError("an extractor call was counted as a session")
    spend_guard.check_before_session = lambda: seen.__setitem__("checked", seen["checked"] + 1)
    spend_guard.note_session_start = no_note
    orchestrator.run_session = lambda agent, user_input, **kw: "[]"
    capture.extract = _SAVED_EXTRACT
    try:
        res = capture.extract(P, "I take the bus", None, ("day_shape",), trace=None)
    finally:
        (spend_guard.check_before_session, spend_guard.note_session_start,
         orchestrator.run_session, capture.extract) = saved
    assert res["ok"] and seen["checked"] == 1


# --- 6. holdout -----------------------------------------------------------------------------------------

def test_holdout_draw_and_window():
    cfg = {**CFG, "holdout_rate": 0.2, "window_days": 14}
    draws = [capture.is_holdout(f"req{i}", 3, cfg) for i in range(2000)]
    assert 300 < sum(draws) < 500                            # about one in five
    assert capture.is_holdout("req7", 3, cfg) == capture.is_holdout("req7", 3, cfg)
    assert not any(capture.is_holdout(f"req{i}", 14, cfg) for i in range(200))


def test_holdout_turn_shows_nothing_and_records_unprompted():
    _reset()
    job = capture.Job(P, "synthesizer", "r-hold")
    job.result = {"candidates": [_c("task", "task", "call the dentist")], "ok": True,
                  "ms": 1, "tin": 0, "tout": 0}
    job._done.set()
    saved = capture.is_holdout
    capture.is_holdout = lambda *a, **k: True
    try:
        turn = capture.note_for_synthesizer(P, job, None)
    finally:
        capture.is_holdout = saved
    assert turn.holdout and turn.note == ""

    class T:            # a trace whose Synthesizer wrote the task unprompted
        pipeline = [type("A", (), {"turns": [type("U", (), {"tool_calls": [
            trace_mod.ToolCallRecord("open_task", {"what": "Call the dentist"}, "", 0)]})()],
            "subagents": []})()]
    capture.after_synthesizer(turn, T())
    assert [r["outcome"] for r in _rows() if r.get("row") == "candidate"] == ["held_out_saved"]


# --- 7. sign-off ---------------------------------------------------------------------------------------

def test_signoff_holds_for_next_turn():
    _reset()
    job = capture.Job(P, "synthesizer", "r-sign")
    job.result = {"candidates": [_c("task", "task", "book the MOT")], "ok": True, "ms": 1,
                  "tin": 0, "tout": 0}
    job._done.set()
    turn = capture.note_for_synthesizer(P, job, None)
    capture.defer(turn)
    nxt = capture.Job(P, "synthesizer", "r-next")
    nxt.result = {"candidates": [], "ok": True, "ms": 1, "tin": 0, "tout": 0}
    nxt._done.set()
    assert "keep: something plain" in capture.note_for_synthesizer(P, nxt, None).note


# --- 9. lifecycle -----------------------------------------------------------------------------------------

def test_cap_and_expiry():
    _reset()
    capture.add_pending(P, "synthesizer", [_c("task", "task", f"t{i}", say=f"task {i}")
                                           for i in range(5)])
    cur = capture._read_json(capture._pending_path(P), [])
    assert [c["say"] for c in cur] == ["task 2", "task 3", "task 4"]      # newest three kept
    old = (datetime.now() - timedelta(hours=25)).isoformat(timespec="seconds")
    capture._write_json(capture._pending_path(P), [{**cur[0], "created": old}])
    assert capture.take_pending(P, "synthesizer") == []


# --- 10. content-free -----------------------------------------------------------------------------------

def test_outcomes_are_content_free():
    _reset()
    secret = "my sister Priya's wedding in Leeds"
    capture._outcome(P, "synthesizer", "r1", {**_c("task", "task", secret, say=secret),
                                              "quote": secret}, "not_acted", False, 2)
    capture._turn_row(P, "synthesizer", "r1", {"candidates": [1], "ms": 3, "tin": 1, "tout": 1},
                      "ran", False, 2)
    text = (_tmp / "data" / "personas" / P / "capture" / "outcomes.jsonl").read_text()
    assert "Priya" not in text and "Leeds" not in text
    for r in _rows():
        assert set(r) <= capture._ROW_KEYS


# --- 11. analytics and the backfill skip capture's own traces ------------------------------------------

def test_capture_traces_are_not_sessions():
    p = "cap_traces"      # its own persona: other tests' real traces land in P's directory
    (_tmp / "config" / "personas" / p).mkdir(parents=True, exist_ok=True)
    tdir = _tmp / "data" / "personas" / p / "traces"
    tdir.mkdir(parents=True, exist_ok=True)
    day = "2026-11-17"
    rows = [{"trace_id": "a", "user_input": "hi", "is_proactive": False, "source": "ui",
             "pipeline": [{"agent": "coordinator"}, {"agent": "synthesizer"}]},
            {"trace_id": "d", "user_input": "Log user's preference for tea", "is_proactive": False,
             "source": "ui", "pipeline": [{"agent": "diarist"}]},
            {"trace_id": "b", "user_input": "x", "is_proactive": True, "source": "capture",
             "pipeline": []}]
    (tdir / f"{day}.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    out = analytics.rollup_day(day, p)
    # The capture trace is counted as neither kind. (The Diarist's own run IS counted as a user
    # session — A9's existing definition, flagged to Mike 2026-11-18, not changed here.)
    assert out["user_sessions"] == 2 and out.get("proactive_sessions", 0) == 0
    saved = capture._now
    capture._now = lambda: datetime(2026, 11, 18, 9, 0)
    try:
        assert [r["trace_id"] for r, _, _ in capture.user_turns(p, 5)] == ["a"]
    finally:
        capture._now = saved


# --- 12. isolation -----------------------------------------------------------------------------------------

def test_isolation():
    _reset(P)
    _reset(P2)
    capture.add_pending(P, "synthesizer", [_c("task", "task", "only mine")])
    assert capture.take_pending(P2, "synthesizer") == []
    assert len(capture.take_pending(P, "synthesizer")) == 1


# --- 13. no identifiers in either note ----------------------------------------------------------------------

def test_notes_carry_no_identifiers():
    items = [{**c, "_mismatch": False} for c in TRIAL_EIGHT]
    for text in (capture.render_note(items), capture.coverage_lines(items)):
        for ident in capture._SHAPE_TARGETS + tuple(capture.KIND_TOOLS.values()):
            if "_" in ident:
                assert ident not in text, ident


# --- 14. latency -----------------------------------------------------------------------------------------------

def test_slow_extractor_does_not_delay_the_turn():
    _reset()

    def slow(persona, user_input, history, kinds, trace=None):
        time.sleep(0.6)
        return {"candidates": [_c("task", "task", "renew passport", say="renew the passport")],
                "ok": True, "ms": 600, "tin": 0, "tout": 0}
    saved = capture.extract
    capture.extract = slow
    CFG["join_bound_s"] = 0.05
    try:
        job = capture.start(P, "I need to renew my passport", [], "synthesizer")
        t0 = time.monotonic()
        turn = capture.note_for_synthesizer(P, job, None)
        assert time.monotonic() - t0 < 0.4 and turn.note == ""
        pending = _wait_pending(P, 1)
        assert pending and pending[0]["say"] == "renew the passport"
    finally:
        capture.extract = saved
        CFG["join_bound_s"] = 2.0


# --- 15. the saved-record input is readable ---------------------------------------------------------------

def test_saved_record_is_readable_not_a_hash():
    _reset()
    from core.persona import persona_scope
    with persona_scope(P):
        day_shape.set_day_shape(section="travel_mode", entry="transit", evidence="bus")
    text = capture.saved_record_text(P, ("day_shape", "goal"))
    assert "travel_mode" in text and "transit" in text
    assert day_shape.digest(P) not in text


def test_off_means_nothing_runs():
    _reset()
    CFG["enabled"] = False
    try:
        assert capture.start(P, "I take the bus", [], "synthesizer") is None
        interview.run_turn(P, "I take the bus", [])
        assert not _rows()
    finally:
        CFG["enabled"] = True


# --- verify round (plan review NEW 1–4) ----------------------------------------------------------------

def _done_job(rid, cands):
    job = capture.Job(P, "synthesizer", rid)
    job.result = {"candidates": cands, "ok": True, "ms": 1, "tin": 0, "tout": 0}
    job._done.set()
    return job


def test_day_entry_saved_for_the_wrong_days_is_a_mismatch():
    c = _c("day_shape", "day", {"days": WEEKDAYS, "wake": "07:00"})
    every = [("set_day_shape", {"section": "day", "entry": {
        "days": WEEKDAYS + ["sat", "sun"], "wake": "07:00"}})]
    weekend = [("set_day_shape", {"section": "day", "entry": {"days": ["sat", "sun"],
                                                              "wake": "10:00"}})]
    assert capture.match(c, every) == "different"
    assert capture.match(c, weekend) is None           # a different day set is another entry


def test_holdout_leaves_carried_proposals_and_reshows_its_own_misses():
    _reset()
    capture.add_pending(P, "synthesizer", [_c("task", "task", "earlier fact", say="earlier")])
    saved = capture.is_holdout
    capture.is_holdout = lambda *a, **k: True
    try:
        turn = capture.note_for_synthesizer(P, _done_job("r-h2", [
            _c("task", "task", "renew the passport", say="renew the passport")]), None)
    finally:
        capture.is_holdout = saved
    assert [c["say"] for c in turn.shown] == ["renew the passport"]
    capture.after_synthesizer(turn, None)                  # the Synthesizer saved nothing
    assert [r["outcome"] for r in _rows() if r.get("row") == "candidate"] == ["held_out_unsaved"]
    pending = [c["say"] for c in capture._read_json(capture._pending_path(P), [])]
    assert pending == ["earlier", "renew the passport"]    # nothing lost, measured once


def test_a_late_fact_saved_meanwhile_is_not_reshown():
    _reset()
    from core.persona import persona_scope
    capture.add_pending(P, "synthesizer", [_c("day_shape", "travel_mode", "transit",
                                              say="they take the bus")])
    with persona_scope(P):           # the Synthesizer saved it after the join gave up
        day_shape.set_day_shape(section="travel_mode", entry="transit", evidence="bus")
    turn = capture.note_for_synthesizer(P, _done_job("r-late", []), None)
    assert turn.note == ""
    assert [r["outcome"] for r in _rows() if r.get("row") == "candidate"] == ["saved_late"]


def test_backfill_writes_a_baseline_and_report_checks_it():
    _reset()
    p = "cap_base"
    (_tmp / "config" / "personas" / p).mkdir(parents=True, exist_ok=True)
    (_tmp / "config" / "personas" / p / "goals.yaml").write_text("quarterly: []\n")
    tdir = _tmp / "data" / "personas" / p / "traces"
    tdir.mkdir(parents=True, exist_ok=True)
    recs = [{"trace_id": f"t{i}", "user_input": f"I need to do thing {i}", "is_proactive": False,
             "source": "ui", "pipeline": [{"agent": "coordinator"}, {"agent": "synthesizer", "turns": [{"tool_calls": (
                 [{"name": "open_task", "args": {"what": f"do thing {i}"}, "ok": True}]
                 if i % 2 else [])}]}]} for i in range(4)]
    (tdir / "2026-11-17.jsonl").write_text("\n".join(json.dumps(r) for r in recs) + "\n")
    EXTRACT["fn"] = lambda text: [_c("task", "task", text.replace("I need to ", ""),
                                     say="a thing to do")]
    saved = capture._now
    capture._now = lambda: datetime(2026, 11, 18, 9, 0)
    try:
        capture.backfill(p, days=5)
    finally:
        capture._now = saved
    base = json.loads((_tmp / "data" / "personas" / p / "capture" / "baseline.json").read_text())
    assert base["kinds"]["synthesizer/task"] == {"n": 4, "miss_rate": 0.5}
    for i in range(25):
        capture._outcome(p, "synthesizer", f"r{i}", _c("task", "task", "x"),
                         "held_out_unsaved" if i < 2 else "held_out_saved", True, 1)
    rep = capture.report(p)
    assert "vs baseline 50% (bar 12%): pass, n=25" in rep


def test_a_fact_kept_by_another_agent_is_not_a_miss():
    """From mike's backfill: Logistics filed these, just not with the kind's own tool."""
    aisha = _c("task", "task", "Invite Aisha for Thanksgiving dinner",
               say="invite Aisha for Thanksgiving dinner")
    assert capture.match(aisha, [("open_obligation", {
        "what": "Plan Thanksgiving invitation for Aisha", "note": "Plan Thanksgiving invitation"})]) == "same"
    gym = _c("preference", "preference", "Gym workouts should be in the morning or midday, not evenings",
             say="gym in the evenings doesn't work, so mornings or midday")
    assert capture.match(gym, [("write_agent_config", {"key": "gym_schedule_preference",
        "value": "{\"time_of_day\": \"morning_or_midday\", \"evening_prohibited\": true}"})]) == "same"
    assert capture.match(aisha, [("write_log", {"content": {"notes": "invite Aisha Thanksgiving"}})]) is None


def test_rematch_rescores_without_a_model_call():
    p = "cap_rematch"
    (_tmp / "config" / "personas" / p).mkdir(parents=True, exist_ok=True)
    tdir = _tmp / "data" / "personas" / p / "traces"
    tdir.mkdir(parents=True, exist_ok=True)
    user = {"trace_id": "u1", "user_input": "invite Aisha for Thanksgiving", "is_proactive": False,
            "source": "ui", "pipeline": [{"agent": "coordinator"}, {"agent": "logistics", "turns": [
                {"tool_calls": [{"name": "open_obligation", "ok": True,
                                 "args": {"what": "Plan Thanksgiving invitation for Aisha"}}]}]}]}
    diarist = {"trace_id": "d1", "user_input": "Log the Thanksgiving invite", "is_proactive": False,
               "source": "ui", "pipeline": [{"agent": "diarist"}]}
    (tdir / "2026-11-17.jsonl").write_text(json.dumps(user) + "\n" + json.dumps(diarist) + "\n")
    cand = {**_c("task", "task", "Invite Aisha for Thanksgiving dinner",
                 say="invite Aisha for Thanksgiving dinner"), "matcher": "unsaved", "guess": "real"}
    review = _tmp / "data" / "personas" / p / "capture" / "backfill_review_2026-11-18.jsonl"
    review.parent.mkdir(parents=True, exist_ok=True)
    review.write_text("".join(json.dumps({"trace_id": tid, "agent": "synthesizer", "ts": "x",
                                          "user_input": "u", "ok": True,
                                          "candidates": [dict(cand)]}) + "\n"
                              for tid in ("u1", "d1")))
    EXTRACT["fn"] = lambda text: (_ for _ in ()).throw(AssertionError("model called"))
    saved = capture._now
    capture._now = lambda: datetime(2026, 11, 18, 9, 0)
    try:
        out = capture.rematch(p, days=5)
    finally:
        capture._now = saved
        EXTRACT["fn"] = None
    rows = [json.loads(ln) for ln in review.read_text().splitlines()]
    assert "dropped 1" in out and [r["trace_id"] for r in rows] == ["u1"]
    assert rows[0]["candidates"][0]["matcher"] == "saved_elsewhere"


_SAVED_EXTRACT = capture.extract     # the real one, captured before setup_module patches it


if __name__ == "__main__":
    setup_module()
    failed = 0
    try:
        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                try:
                    fn()
                    print(f"PASS {name}")
                except Exception as exc:  # noqa: BLE001
                    failed += 1
                    print(f"FAIL {name}: {exc!r}")
    finally:
        teardown_module()
    sys.exit(1 if failed else 0)
