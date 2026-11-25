"""
tests/test_goal_walkthrough_fixes.py — what `mike`'s goals walkthrough (2026-11-25) showed, fixed:
a goal on hold comes back, a goal settled now can start later, a talk ends only on the user's own
weekly time and with the realism said, a false "I've put it on hold" is replaced, internal ids stay
out of replies, a habit moves with its goal, and every file loads on the VM's Python.

Plan: archive/plans/goal_task_network_plan_2026-11-18.md § 19 (Mike's rulings 1–7, 2026-11-25).
One check (or more) per row of the build prompt's table; the row number is in each name.

EVERY LIVE METER IS STUBBED: CalDAV, Google Routes, the day_planner and project_planner models,
push, the Goals Interviewer's model, the public lookup, the quality log (captured). No persona
data — a temp directory per check.

    .venv/bin/python tests/test_goal_walkthrough_fixes.py
"""
from __future__ import annotations

import glob
import inspect
import io
import json
import re
import sys
import tempfile
import threading
import tokenize
from datetime import date, datetime, time, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import core.interview as INTV  # noqa: E402
import core.orchestrator as ORCH  # noqa: E402
import core.persona as P  # noqa: E402
import core.remote_client as RC  # noqa: E402
import tools.ambient as A  # noqa: E402
import tools.baselines as B  # noqa: E402
import tools.caldav as CAL  # noqa: E402
import tools.day_plan as D  # noqa: E402
import tools.day_plan_config as C  # noqa: E402
import tools.day_shape as DS  # noqa: E402
import tools.goal_claims as GC  # noqa: E402
import tools.goal_network as GN  # noqa: E402
import tools.goal_talk as GT  # noqa: E402
import tools.goals as G  # noqa: E402
import tools.horizon as H  # noqa: E402
import tools.location as L  # noqa: E402
import tools.logger as LOG  # noqa: E402
import tools.lookup_guard as LG  # noqa: E402
import tools.obligations as O  # noqa: E402
import tools.project_plan as PP  # noqa: E402
import tools.ranking as RK  # noqa: E402
import tools.ranking_review as RR  # noqa: E402
import tools.routing as R  # noqa: E402
import tools.satisfaction as S  # noqa: E402
import tools.turn_context as TC  # noqa: E402

_results: list[tuple[str, bool, str]] = []
_TMP = Path(tempfile.mkdtemp(prefix="goal_walkthrough_fixes_"))
(_TMP / "no_playbooks").mkdir()
PP._PLAYBOOKS = _TMP / "no_playbooks"
TODAY = date.today()
_CLOCK = {"now": datetime.combine(TODAY, time(7, 0))}
O._now = lambda: _CLOCK["now"]
A._get_timezone = lambda: "Europe/London"
_PERSONA = "gw_fixes"
_SHAPE = 'day: [{days: all, wake: "07:00", bed: "23:00"}]\ntravel_mode: transit\n'

CAL._query_events = lambda start, end, persona=None, calendars="own": {"events": [], "discovery": "ok"}
CAL._get_event_by_uid = lambda uid, persona=None: {"error": "Failed to fetch event: offline"}
R.get_travel_time = lambda *a, **k: {"journeys": [{"duration_minutes": 20}]}
L.load_zones = lambda persona=None: []
L.current_zone = lambda persona=None: {}
INTV.holds_proactive = lambda persona: False
D._quiet_now = lambda persona: False
D._idle_minutes = lambda persona: None


def _no_model(*a, **k):
    raise AssertionError("a day_planner model call was made")


D._call_model = _no_model
RC.send_one = lambda persona, text, nudge=False, **k: "ok"
_PLANNER: list = []


def _planner(payload):
    if not _PLANNER:
        raise AssertionError("an unexpected project_planner call")
    return _PLANNER.pop(0)


PP._MODEL_CALL = _planner
_IREPLY: list[str] = []


def _interviewer(agent, message, persona=None, history=None, **k):
    return _IREPLY.pop(0) if _IREPLY else "Where are you with it now?"


ORCH.run_session = _interviewer
ORCH._pending_tokens = lambda persona=None: set()
ORCH._pending_raised_since = lambda before, persona=None: []
ORCH.enforce_pending_receipt = lambda text, pending: text
LG.ask_public = lambda question, persona, source="", max_chars=None: (
    "<untrusted_content>About 300–450 hours from a plateau.</untrusted_content>")
_TURN = {"t": {"user_turn": True}}
TC.current = lambda: _TURN["t"]
_QUALITY: list[tuple] = []
LOG.write_quality_event = lambda event_type, source_agent="", detail="", session_id="": (
    _QUALITY.append((event_type, source_agent, detail)), "ok")[1]

_FLAGS = {"build": True, "show_in_app": True, "ledger_fields": True, "synth_reads_plan": True,
          "unconfirmed_rule": True, "reshuffle_model": False, "nudges": False,
          "owns_checkins": False, "prep_tasks": True, "horizon_cap": True, "project_planner": True,
          "ranking_signals": True, "goal_talk": True}


def _d(n: int) -> str:
    return (TODAY + timedelta(days=n)).isoformat()


def _join() -> None:
    for th in threading.enumerate():
        if th.name.startswith("day_plan_"):
            th.join(10)


def _fresh(name: str, goals: str, flags: dict | None = None) -> Path:
    _join()
    d = _TMP / name
    if d.exists():
        import shutil
        shutil.rmtree(d)            # a check's talk state never leaks into the next
    (d / "config").mkdir(parents=True, exist_ok=True)
    for mod in (O, D, DS, L, H, RR, S, B):
        mod.persona_data_dir = lambda persona=None, _d=d: _d
    P.persona_data_dir = lambda persona=None, _d=d: _d
    DS.persona_config_dir = lambda persona=None, _d=d: _d / "config"
    (d / "config" / "goals.yaml").write_text(goals)
    G._goals_path = lambda _d=d: (P.resolve_persona(None), _d / "config" / "goals.yaml")[1]
    G._calling_agent = lambda: "synthesizer"
    (d / "day_shape.yaml").write_text(_SHAPE)
    C._OVERRIDE = {"flags": {**_FLAGS, **(flags or {})}}
    RK._OVERRIDE = {}
    _PLANNER.clear()
    _IREPLY.clear()
    _QUALITY.clear()
    _TURN["t"] = {"user_turn": True}
    _CLOCK["now"] = datetime.combine(TODAY, time(7, 0))
    O._DAY_STARTS_CACHE.update(key=None)
    O._GOAL_CACHE.update(key=None)
    return d


def check(name: str):
    def deco(fn):
        try:
            with P.persona_scope(_PERSONA):
                fn()
            _results.append((name, True, ""))
        except Exception as exc:  # noqa: BLE001
            import traceback
            _results.append((name, False, f"{type(exc).__name__}: {exc}\n"
                             + "".join(traceback.format_exc().splitlines(True)[-6:])))
        finally:
            _join()
            C._OVERRIDE = None
            RK._OVERRIDE = None
        return fn
    return deco


def _goal(gid: str) -> dict:
    O._GOAL_CACHE.update(key=None)
    return O._goal_index()[gid]


def _view() -> str:
    return G.prompt_view(G.read_goals())


def _set_today(n: int) -> None:
    _CLOCK["now"] = datetime.combine(TODAY + timedelta(days=n), time(7, 0))


# The 11-25 shape, generic: a weekly exercise goal and a strength goal, a large language goal with
# its daily practice under it, a vocational course to look into later, a dated obligation.
_GOALS = (
    "long: []\n"
    "quarterly:\n"
    "- {id: q4, title: Become better at speaking Bulgarian, status: active, size: L,"
    " vetted: {date: '" + TODAY.isoformat() + "', depth: L, pass: short, priority: normal,"
    " displaces: focus time}}\n"
    "- {id: q5, title: File UK taxes by Dec 31, status: active, size: M, kind: obligation,"
    " due: '" + _d(36) + "', vetted: {date: '" + TODAY.isoformat() + "', priority: high}}\n"
    "weekly:\n"
    "- {id: w1, title: Investigate Lewisham College bricklaying courses, status: active}\n"
    "- {id: w4, title: Purpose-Driven Exercise, status: active}\n"
    "- {id: w5, title: Strength and Flexibility Training, status: active}\n"
    "daily:\n"
    "- {id: d1, title: Bulgarian Vocabulary, status: active, parent_goal: q4}\n")


# =============================================================================================
# #1 — a parked goal comes back (ruling 1)
# =============================================================================================

@check("#1 a parked goal is one line under 'On hold' with its date and note — never in the current "
       "YAML — and on its date moves to 'Back on the list today' until a reply names it, once")
def _():
    _fresh("p1", _GOALS)
    out = G.update_goal("vet", goal_id="w1", verdict="parked", revisit_on=_d(30),
                        hold_note="courses start in September")
    assert "parked until" in out, out
    v = _view()
    cur = v.split("### ")[0]
    assert "bricklaying" not in cur, "never a current goal"
    assert "- w1: Investigate Lewisham College bricklaying courses — until " + _d(30) + \
        " — courses start in September" in v.split("### On hold")[1], v
    assert "Back on the list today" not in v
    _set_today(30)
    v = _view()
    assert "### Back on the list today" in v and "take it up, give it a new date, or let it go" in v
    assert "w1: Investigate Lewisham" in v.split("### Back on the list today")[1].split("###")[0]
    assert G.raised_in("Lunch is at one.") == [], "a reply that does not name it stamps nothing"
    assert G.raised_in("The bricklaying courses are back on your list today — still keen?") == ["w1"]
    v = _view()
    assert "Back on the list today" not in v and "leave it unless they bring it up" in v, v
    assert G.raised_in("Bricklaying again!") == [], "asked once"


@check("#1 taking a parked goal up again clears its date and note; a large one not yet talked "
       "through gets a fresh talk task and one offer")
def _():
    _fresh("p1_back", _GOALS)
    G.update_goal("vet", goal_id="q4", verdict="parked", revisit_on=_d(50), hold_note="after the holidays")
    tasks = [t for t in O._load() if str(t.get("source_id") or "") == "goal_talk:q4"]
    assert all(t["status"] != "open" for t in tasks), "parking closed the talk task"
    out = G.update_goal("update", goal_id="q4", status="active")
    g = _goal("q4")
    assert g["status"] == "active" and not {"revisit_on", "hold_note", "revisit_raised"} & set(g), g
    assert "deserves a proper talk" in out, out
    open_ = [t for t in O._load() if str(t.get("source_id") or "") == "goal_talk:q4"
             and t.get("status") == "open"]
    assert len(open_) == 1, open_


@check("#1 a goal is put on hold only with a day to look at it again")
def _():
    _fresh("p1_nodate", _GOALS)
    out = G.update_goal("update", goal_id="w4", status="parked")
    assert out.startswith("Error: a goal on hold needs the day") and "starts_on" in out, out
    assert _goal("w4")["status"] == "active"


# =============================================================================================
# #2 / #6 — on hold until X: taken on, starting later (rulings 2 and 3)
# =============================================================================================

@check("#2 'on hold until mid-January' = starts_on: listed under 'Starting later' with its note, out "
       "of the current YAML, its open tasks named (not hidden), no weekly-time gap, no re-check")
def _():
    _fresh("p2", _GOALS, flags={"revet": True})
    O.open_task("Find a personal trainer", kind="deadline", goal_id="w5")
    out = G.update_goal("update", goal_id="w5", starts_on=_d(51), hold_note="stretching only until then")
    assert "starts on " + _d(51) in out and "nothing is planned" in out, out
    assert "Find a personal trainer" in out and "defer" in out, "its task is named, not hidden"
    g = _goal("w5")
    assert g["status"] == "active" and g["starts_on"] == _d(51)
    v = _view()
    assert "Strength and Flexibility" not in v.split("### ")[0]
    later = v.split("### Taken on, starting later")[1].split("###")[0]
    assert "- w5: Strength and Flexibility Training — starts " + _d(51) + \
        " — stretching only until then" in later, v
    assert not any(x["id"] == "w5" for x in D.allocation_gaps(_PERSONA)), "its weekly time is not due"
    assert any(x["id"] == "w4" for x in D.allocation_gaps(_PERSONA))
    assert not G.live(g) and G.not_started(g)
    GN.revet_daily(_PERSONA, TODAY + timedelta(days=50))
    assert "w5" not in (PP._load(_PERSONA).get("revet") or {}), "not re-checked before its day"


@check("#2 from its day it runs again: current, named once under 'Back from today', and the hold's "
       "note goes when the reply names it")
def _():
    _fresh("p2_start", _GOALS)
    G.update_goal("update", goal_id="w4", starts_on=_d(51), hold_note="stretching only")
    _set_today(51)
    v = _view()
    assert "Purpose-Driven Exercise" in v.split("### ")[0], "current again"
    assert "### Back from today" in v and "w4: Purpose-Driven Exercise" in v.split("### Back from today")[1]
    assert G.raised_in("Exercise is back on from today.") == ["w4"]
    g = _goal("w4")
    assert g["start_said"] and "hold_note" not in g, g
    assert "Back from today" not in _view()


@check("#6 an M goal starting later is not planned before its day — by plan_project or the sweep — "
       "and the sweep plans it on the first tick on or after")
def _():
    goals = _GOALS.replace("due: '" + _d(36) + "'", "due: '" + _d(80) + "', starts_on: '" + _d(20) + "'")
    _fresh("p6_m", goals)
    out = PP.plan_project("q5", size="M")
    assert out.startswith("error:") and "starts on " + _d(20) in out, out
    assert PP.sweep_unplanned(_PERSONA) == 0
    _set_today(20)
    O._GOAL_CACHE.update(key=None)
    assert PP.sweep_unplanned(_PERSONA) == 1 and PP._load(_PERSONA)["requests"]["q5"]["status"] == "queued"


@check("#6 / Stage 2: a large goal talked through to 'active, starts 15 Jan' keeps its full pass and "
       "is NOT planned in waves before that day, even with rolling_wave on; it is from that day")
def _():
    _fresh("p6_l", _GOALS, flags={"rolling_wave": True})
    G.update_goal("talk", goal_id="q4")
    _IREPLY.append("At two hours a week that is about three to four years — does that work?")
    for msg in ("Two hours a week", "Mornings during the nap", "Yes I want it", "It starts mid-January"):
        GT.run_turn(_PERSONA, msg, [])
    G._calling_agent = lambda: "goals_interviewer"
    out = G.update_goal("vet", goal_id="q4", verdict="active", size="L", priority="normal",
                        displaces="focus time", weekly_minutes=120, done_means="Generally conversant",
                        starting_point="Plateaued", effort_hours="300-450", starts_on=_d(51))
    g = _goal("q4")
    assert g["vetted"]["pass"] == "full" and g["starts_on"] == _d(51), (out, g)
    assert "starts on " + _d(51) in out and "planned out of sight" in out, out
    PP.sweep_unplanned(_PERSONA)
    assert "q4" not in PP._load(_PERSONA)["requests"], "not planned before its day"
    _set_today(51)
    O._GOAL_CACHE.update(key=None)
    PP.sweep_unplanned(_PERSONA)
    assert PP._load(_PERSONA)["requests"]["q4"]["size"] == "L", "planned in waves from its day"


@check("#6 starts_on is for a goal taken on now — a parked verdict with one is refused")
def _():
    _fresh("p6_refuse", _GOALS)
    out = G.update_goal("vet", goal_id="w4", verdict="parked", revisit_on=_d(9), starts_on=_d(9))
    assert out.startswith("Error: `starts_on` is for a goal taken on now"), out


@check("#2 a goal starting later fires no finish alert (Stage 1's reads stay unambiguous)")
def _():
    _fresh("p2_finish", _GOALS, flags={"projected_finish": True})
    st = PP._load(_PERSONA)
    st["requests"]["q5"] = {"status": "planned", "size": "M", "ids": [], "deadline": _d(10)}
    PP._save(_PERSONA, st) if hasattr(PP, "_save") else None
    G.update_goal("update", goal_id="q5", starts_on=_d(40))
    assert GN.finish_daily(_PERSONA, TODAY) == 0


# =============================================================================================
# #3 / #4 — the talk ends only on the user's own weekly time, with the realism said (rulings 5, 5b)
# =============================================================================================

def _talk(goals: str = _GOALS) -> None:
    _fresh("talk", goals)
    G._calling_agent = lambda: "synthesizer"
    assert G.update_goal("talk", goal_id="q4").startswith("Started")


@check("#3 the Interviewer's own proposal (11-25: '120 to 150 minutes', Mike gave no figure) is "
       "never recorded as the user's weekly time")
def _():
    _talk()
    _IREPLY.append("That puts you at about 2 to 2.5 hours (120 to 150 minutes) a week.")
    GT.run_turn(_PERSONA, "Mornings would be best, during the nap a few weekdays and Saturday", [])
    GT.run_turn(_PERSONA, "They'd come out of Metatron and admin time", [])
    G._calling_agent = lambda: "goals_interviewer"
    out = G.update_goal("update", goal_id="q4", weekly_minutes=120)
    assert out.startswith("Error: that weekly time is a suggestion, not their figure"), out
    assert "weekly_minutes" not in _goal("q4")
    b = GT.talk_block(_PERSONA, GT.current(_PERSONA))
    assert "minutes a week" in b.split("Still to settle:")[1]


@check("#3 their figure counts: said in words, or a plain yes to ONE figure named, or a bare number "
       "after a 'minutes' question — and a range then a yes does not")
def _():
    _talk()
    G._calling_agent = lambda: "goals_interviewer"
    GT.run_turn(_PERSONA, "I could do 30 minutes three times a week", [])
    assert G.update_goal("update", goal_id="q4", weekly_minutes=90).startswith("Updated")
    _talk()
    G._calling_agent = lambda: "goals_interviewer"
    _IREPLY.append("Shall we say 120 minutes a week?")
    GT.run_turn(_PERSONA, "Where would it come from?", [])
    GT.run_turn(_PERSONA, "Yes, that works", [])
    assert G.update_goal("update", goal_id="q4", weekly_minutes=120).startswith("Updated")
    _talk()
    G._calling_agent = lambda: "goals_interviewer"
    _IREPLY.append("How many minutes a week can you give it?")
    GT.run_turn(_PERSONA, "Why now?", [])
    GT.run_turn(_PERSONA, "150", [])
    assert G.update_goal("update", goal_id="q4", weekly_minutes=150).startswith("Updated")
    _talk()
    G._calling_agent = lambda: "goals_interviewer"
    _IREPLY.append("Somewhere between 120 and 150 minutes a week?")
    GT.run_turn(_PERSONA, "Hm", [])
    GT.run_turn(_PERSONA, "yes", [])
    assert G.update_goal("update", goal_id="q4", weekly_minutes=120).startswith("Error"), \
        "a yes to a range is not a figure"


@check("#3 a figure already on the goal (q4's 120 from 11-25) is confirmed in this talk before the "
       "verdict; the turn minimum still comes first")
def _():
    _talk(_GOALS.replace("size: L,", "size: L, weekly_minutes: 120, done_means: Conversant,"))
    G._calling_agent = lambda: "goals_interviewer"
    args = dict(goal_id="q4", verdict="active", size="L", priority="normal", displaces="focus time")
    assert G.update_goal("vet", **args).startswith("Error: this has hardly been talked through")
    for msg in ("a", "b", "c", "d"):
        GT.run_turn(_PERSONA, msg, [])
    out = G.update_goal("vet", **args)
    assert out.startswith("Error: that weekly time is a suggestion"), out


@check("#4 the verdict waits until the Interviewer has said what their time means in months or "
       "years (11-25: 300–450 h quoted, '3–4 years at this rate' never said)")
def _():
    _talk()
    for msg in ("Two hours a week", "b", "c", "d"):
        GT.run_turn(_PERSONA, msg, [])
    G._calling_agent = lambda: "goals_interviewer"
    args = dict(goal_id="q4", verdict="active", size="L", priority="normal", displaces="focus time",
                weekly_minutes=120, done_means="Conversant", effort_hours="300-450")
    out = G.update_goal("vet", **args)
    assert out.startswith("Error: before the verdict, put plainly") and "At 120 minutes a week" in out, out
    G.update_goal("update", goal_id="q4", weekly_minutes=120, effort_hours="300-450")
    b = GT.talk_block(_PERSONA, GT.current(_PERSONA))
    assert "Not yet said to them" in b and "Arithmetic (code): At 120 minutes a week" in b, b
    _IREPLY.append("At two hours a week, that's roughly three to four years. Does that sit right?")
    GT.run_turn(_PERSONA, "go on", [])
    assert "taken on" in G.update_goal("vet", **args)


@check("#3 / 5b parking a talk needs no weekly time, says what is still open, and keeps what was "
       "settled")
def _():
    _talk()
    G._calling_agent = lambda: "goals_interviewer"
    GT.run_turn(_PERSONA, "I want it but not now", [])
    G.update_goal("update", goal_id="q4", done_means="Generally conversant")
    out = G.update_goal("vet", goal_id="q4", verdict="parked", revisit_on=_d(51))
    assert "parked until" in out and "Still open for when it comes back:" in out, out
    assert "minutes a week" in out.split("Still open")[1]
    assert _goal("q4")["done_means"] == "Generally conversant"


# =============================================================================================
# #2 / #5 — a false goal claim is replaced (ruling 4)
# =============================================================================================

_ON_HOLD_037 = ("Mike, I have set the deadline to execute the Prudential decisions for December 15, "
                "and put purposeful exercise and heavy lifting on hold until Maria returns in "
                "mid-January, leaving stretching as your active physical baseline.\n\nWith workouts "
                "paused until then, should we defer the search for a personal trainer?")
_ON_HOLD_032 = ("That was my oversight on the workouts. I have corrected the standing records: "
                "purposeful exercise (W4) and heavy lifting (W5) are completely on hold until "
                "mid-January. Between now and then, your physical routine is strictly stretching.")


@check("#2 seq 037 and 032: 'put exercise on hold' with no goal changed is replaced — that sentence "
       "only, the question after it kept — and logged with the sentence")
def _():
    _fresh("claim", _GOALS)
    before = GC.snapshot(_PERSONA)
    out = GC.amend(_ON_HOLD_037, before, _PERSONA)
    assert out.startswith("I haven't actually put \"Purpose-Driven Exercise\" on hold on your goals "
                          "yet — shall I do that now?"), out
    assert "Prudential" not in out.split("\n\n")[0], "the claim is about exercise, not Prudential"
    assert out.endswith("should we defer the search for a personal trainer?")
    assert _QUALITY and _QUALITY[-1][0] == "FALSE_GOAL_CLAIM" and "on hold" in _QUALITY[-1][2]
    out = GC.amend(_ON_HOLD_032, before, _PERSONA)
    assert "\"Purpose-Driven Exercise\" and \"Strength and Flexibility Training\" on hold" in out, out
    assert out.startswith("That was my oversight") and out.endswith("strictly stretching.")
    assert "(W4)" not in out


@check("#2 the same claim after the change was really made is left alone; so are offers, questions "
       "and log writes")
def _():
    _fresh("claim_true", _GOALS)
    before = GC.snapshot(_PERSONA)
    G.update_goal("update", goal_id="w4", starts_on=_d(51))
    text = "I've put purposeful exercise on hold until mid-January."
    assert GC.amend(text, before, _PERSONA) == text
    before = GC.snapshot(_PERSONA)
    for t in ("Shall I put purposeful exercise on hold until January?",
              "Should exercise go on hold until Maria is back?",
              "I have updated your books log with those reading contexts.",
              "I have recorded those training windows: exercise fits Monday afternoons."):
        assert GC.amend(t, before, _PERSONA) == t, t
    assert not _QUALITY


@check("#2 a sentence naming two goals, one of them really on hold, is kept (precision over recall)")
def _():
    _fresh("claim_partial", _GOALS)
    before = GC.snapshot(_PERSONA)
    G.update_goal("update", goal_id="w4", starts_on=_d(51))
    t = "I've put purposeful exercise and strength training on hold until January."
    assert GC.amend(t, before, _PERSONA) == t


@check("#5 seq 026: 'we have talked it out fully… everything is settled' about a large goal with "
       "its weekly time open is replaced by what is open, said once")
def _():
    _fresh("settled", _GOALS.replace("size: L,", "size: L, done_means: Conversant, starting_point: Plateaued,"))
    G.update_goal("talk", goal_id="q4")
    before = GC.snapshot(_PERSONA)
    text = ("Yes, Mike, we have talked it out fully.\n\nEverything needed to define the goal is "
            "settled and on record:\n- Scope: listening.\n\nWhen we bring it back we won't need "
            "to re-litigate the trade-offs.")
    out = GC.amend(text, before, _PERSONA)
    first = out.split("\n\n")[0]
    assert first.startswith("Not quite — still open on \"Become better at speaking Bulgarian\":"), out
    assert "the minutes a week you'll give it" in first
    assert out.count("Not quite") == 1 and "re-litigate" not in out and "- Scope: listening." in out


@check("#2 the check is wired into both Synth paths after the pending receipt, and into the "
       "Interviewer's talk turns")
def _():
    for fn in (ORCH.run_pipeline_session, ORCH._run_pipeline_session_stream_inner):
        src = inspect.getsource(fn)
        assert "_goals_before = _goal_snapshot(persona)" in src and "_amend_goal_claims(" in src
        assert "_goal_after_reply(" in src
        assert src.index("enforce_pending_receipt(") < src.index("_amend_goal_claims(")
    assert "amend(reply, goals_before" in inspect.getsource(GT.run_turn)


@check("Fable S1: true sentences about tasks, routines, workouts, reminders and other things are "
       "never replaced, even when they share a word with a goal")
def _():
    _fresh("s1", _GOALS)
    before = GC.snapshot(_PERSONA)
    for t in ("I've marked the dentist call as done.",
              "I have marked your strength workout as done for today.",
              "I've paused your morning routine until Monday.",
              "I've paused the exercise reminders until Monday.",
              "I've deferred the boiler service task to next Friday.",
              "Your flight has been deferred by two hours.",
              "I've changed the reminder time; your goals are unchanged.",
              "I've set everything else aside for now — what you're feeling matters most.",
              "We've paused the planning for tonight; rest.",
              "I have not put exercise on hold.",
              "You told me you've paused the taxes work; I have updated the task."):
        assert GC.amend(t, before, _PERSONA) == t, t
    assert not [q for q in _QUALITY if q[0] == "FALSE_GOAL_CLAIM"], _QUALITY


@check("Fable S2/S3: a hold is checked against the goal's STATE — a true recap the next turn, and "
       "the day a hold ends ('on hold until today', 'starts again today'), are kept")
def _():
    _fresh("s2", _GOALS)
    G.update_goal("vet", goal_id="q4", verdict="parked", revisit_on=_d(50))
    G.update_goal("update", goal_id="w5", starts_on=_d(3))
    before = GC.snapshot(_PERSONA)                    # a later turn: nothing changes in it
    for t in ("Bulgarian has been parked until mid-January, as we agreed.",
              "Strength training is on hold until Saturday."):
        assert GC.amend(t, before, _PERSONA) == t, t
    _set_today(3)
    t = "Strength and flexibility training has been on hold and starts again today."
    assert GC.amend(t, GC.snapshot(_PERSONA), _PERSONA) == t


@check("Fable S6: a note written while the goal stays current does not make 'on hold' true")
def _():
    _fresh("s6", _GOALS)
    before = GC.snapshot(_PERSONA)
    G.update_goal("update", goal_id="w4", context="on hold until mid-January")
    out = GC.amend("I have corrected the standing records: purposeful exercise is on hold.",
                   before, _PERSONA)
    assert out.startswith("I haven't actually put \"Purpose-Driven Exercise\" on hold"), out


@check("Fable S4: a reply that merely mentions the goal's word does not spend its one 'it's back' "
       "question; one that speaks of its return does")
def _():
    _fresh("s4", _GOALS)
    G.update_goal("vet", goal_id="w4", verdict="parked", revisit_on=_d(5))
    _set_today(5)
    assert G.raised_in("Logged: 30 minutes of exercise this morning.") == []
    assert G.raised_in("Purpose-driven exercise is back on the list today — take it up again?") == ["w4"]


@check("Fable S5: 'all settled' about something else, after a talk parked with fields open, is left; "
       "a talk weeks old is not what 'talked it out fully' is about")
def _():
    _fresh("s5", _GOALS)
    G.update_goal("talk", goal_id="q4")
    G._calling_agent = lambda: "goals_interviewer"
    G.update_goal("vet", goal_id="q4", verdict="parked", revisit_on=_d(50))
    before = GC.snapshot(_PERSONA)
    for t in ("The dinner plan is all settled.", "Your taxes are fully settled with HMRC.",
              "Nothing left to decide on the trip."):
        assert GC.amend(t, before, _PERSONA) == t, t
    assert GC.amend("We have talked it out fully.", before, _PERSONA).startswith("Not quite")
    real = GT._now
    GT._now = lambda: real() + timedelta(hours=4)      # the talk's own (UTC) clock
    try:
        assert GC.amend("We have talked it out fully.", before, _PERSONA) == \
            "We have talked it out fully."
    finally:
        GT._now = real


@check("Fable S7: the latest word wins — 'start it now' (starts_on today) lifts a later start, and a "
       "goal taken up from parked is not left behind an old start date")
def _():
    _fresh("s7", _GOALS)
    G.update_goal("update", goal_id="w4", starts_on=_d(51), hold_note="stretching only")
    out = G.update_goal("update", goal_id="w4", starts_on="today")
    g = _goal("w4")
    assert not G.not_started(g) and "hold_note" not in g, (out, g)
    G.update_goal("update", goal_id="w5", starts_on=_d(60))
    G.update_goal("vet", goal_id="w5", verdict="parked", revisit_on=_d(9))
    G.update_goal("update", goal_id="w5", status="active")
    assert not G.not_started(_goal("w5")) and "starts_on" not in _goal("w5")
    assert "starts_on \"today\"" in G.prompt_view({"weekly": [{"id": "w9", "title": "X",
                                                               "starts_on": _d(9)}]})


@check("Fable L1/L2/L3/L4: a yes to one figure counts beside the total hours; '2 hours a week over 3 "
       "days' is 120; a turned-down or hedged figure is not theirs; the rate needs a pace")
def _():
    c = {"last_reply": "Shall we say 120 minutes a week? At that rate the 300 to 450 hours is "
                       "roughly three to four years."}
    GT._note_user_turn(c, "Yes, that works")
    assert c["their_minutes"] == [[120, 120]], c
    assert GT.weekly_figures("I can do 2 hours a week over 3 days") == [(120, 120)]
    assert GT.weekly_figures("20 minutes a day, five days a week") == [(100, 100)]
    assert GT.weekly_figures("1h30 a week") == [(90, 90)]
    assert GT.weekly_figures("no, 150 minutes is too much") == []
    assert GT.weekly_figures("I can't do 150, maybe 90 minutes") == [(90, 90)]
    for t in ("Good question, I'm not sure", "ok but can we talk about exams first",
              "fine, whatever, though honestly less"):
        c = {"last_reply": "Shall we say 120 minutes a week?"}
        GT._note_user_turn(c, t)
        assert "their_minutes" not in c, t
    c = {"last_reply": "How many minutes a week?"}
    GT._note_user_turn(c, "I was born in 1985")
    assert "their_minutes" not in c
    assert not GT._says_rate("You've been at it for two years. What would a good week look like?")
    assert GT._says_rate("At this pace you'd reach it in about three and a half years.")


@check("Fable L5/L6: a replacement keeps its bullet and bold and is not cut at 'Jan.'; ids next to "
       "ordinary labels stay; nothing else in the reply is reformatted")
def _():
    _fresh("l5", _GOALS)
    before = GC.snapshot(_PERSONA)
    out = GC.amend("I've put exercise on hold until Jan. 15.\n\n**I've parked purposeful exercise.**",
                   before, _PERSONA)
    assert "15." not in out and out.count("I haven't actually put") == 1, out
    t = "Plan:\n  - sub item\n    - deeper  item at 9 :30 (Week 4 (W4))"
    assert GC.amend(t, before, _PERSONA) == t
    assert GC.amend("For goal q4: speak daily.", before, _PERSONA) == "For goal q4: speak daily."


@check("verify N1: only Metatron's own claim counts — advice, third-party news, history, a "
       "hypothetical, a podcast, a purchase, and 'I haven't…' are all kept")
def _():
    _fresh("n1", _GOALS)
    before = GC.snapshot(_PERSONA)
    for t in ("The college says its bricklaying courses are on hold until spring.",
              "You could put exercise on hold until January and keep stretching.",
              "When exercise was on hold last spring, your sleep suffered.",
              "Many people find strength work gets parked over the holidays.",
              "I've paused the Bulgarian podcast at minute 12.",
              "The exercise bike purchase is on hold until payday.",
              "I've parked that thought about college for later in our chat.",
              "I haven't put exercise on hold.",
              "I've marked today's Bulgarian vocabulary done — nice streak on that goal."):
        assert GC.amend(t, before, _PERSONA) == t, t


@check("verify N2/N3: a sentence ending in a number still ends; an old or just-lifted start date "
       "never makes a new 'on hold' true")
def _():
    _fresh("n2", _GOALS)
    before = GC.snapshot(_PERSONA)
    out = GC.amend("See you at 9.30. I've put exercise on hold until Jan. 15. OK.", before, _PERSONA)
    assert out.startswith("See you at 9.30. I haven't actually put") and out.endswith(" OK."), out
    G.update_goal("update", goal_id="w4", starts_on=_d(5))
    _set_today(40)
    out = GC.amend("I've put purposeful exercise on hold until September.", GC.snapshot(_PERSONA), _PERSONA)
    assert out.startswith("I haven't actually put"), "a start date 35 days gone is not a hold"
    _set_today(0)
    G.update_goal("update", goal_id="w5", starts_on="today")
    out = GC.amend("I've put strength training on hold again until February.",
                   GC.snapshot(_PERSONA), _PERSONA)
    assert out.startswith("I haven't actually put"), out


@check("verify N4/N5: '(W4) and heavy lifting (W5)' loses both codes; a logging sentence with a "
       "return word does not spend the goal's one ask")
def _():
    _fresh("n4", _GOALS)
    before = GC.snapshot(_PERSONA)
    assert GC.amend("Purposeful exercise (W4) and heavy lifting (W5) are next.", before, _PERSONA) \
        == "Purposeful exercise and heavy lifting are next."
    assert GC.amend("Lifting (W5) stays as is.", before, _PERSONA) == "Lifting (W5) stays as is."
    G.update_goal("vet", goal_id="w4", verdict="parked", revisit_on=_d(2))
    _set_today(2)
    assert G.raised_in("Back at it: 30 minutes of exercise logged again.") == []


@check("verify N6/N7: a cap is their figure, a long spoken yes counts, the yes answers the figure "
       "in the question; a question pairing a pace and a duration is not the rate said")
def _():
    assert GT.weekly_figures("I can't do more than 2 hours a week") == [(120, 120)]
    assert GT.weekly_figures("no more than 90 minutes a week") == [(90, 90)]
    assert GT.weekly_figures("I'd like to do 2 hours too") == [(120, 120)]
    for t in ("Yes that works for me, let's do it", "Sure, let's go with that for now",
              "Yeah I think that's about right honestly"):
        c = {"last_reply": "Shall we say 120 minutes a week?"}
        GT._note_user_turn(c, t)
        assert c.get("their_minutes") == [[120, 120]], t
    c = {"last_reply": "You said 90 minutes a week felt tight. Shall we say 120 minutes a week?"}
    GT._note_user_turn(c, "yes")
    assert c.get("their_minutes") == [[120, 120]], c
    assert not GT._says_rate("Over the next 6 months, how many hours a week could you give it?")
    assert GT._says_rate("At two hours a week, the 300 hours is a long road. So about 3 to 4 years, then.")


# =============================================================================================
# #7 — internal ids out of user text
# =============================================================================================

@check("#7 goal codes in a reference shape and task ids come out; 'Q4 results' and unknown codes stay")
def _():
    _fresh("ids", _GOALS)
    O.open_task("Gather documents and organise records", kind="deadline")
    tid = next(t["id"] for t in O._load() if t.get("what") == "Gather documents and organise records")
    before = GC.snapshot(_PERSONA)
    cases = {
        "The most sensible next focus is your UK tax filing (Q5). It is due soon.":
            "The most sensible next focus is your UK tax filing. It is due soon.",
        "Next on the list is goal q5: File UK taxes.": "Next on the list is File UK taxes.",
        "Training: purposeful exercise and strength (W4, W5) and the bricklaying courses (W1).":
            "Training: purposeful exercise and strength and the bricklaying courses.",
        "Purposeful exercise (W4/W5) is anchored to care blocks.":
            "Purposeful exercise is anchored to care blocks.",
        f"The next task is gathering documents (`{tid}`). Then file.":
            "The next task is gathering documents. Then file.",
        f"Start with {tid} on Friday.": "Start with \"Gather documents and organise records\" on Friday.",
        "Your Q4 results are in, and Q9 (W8) is not a goal of yours.":
            "Your Q4 results are in, and Q9 (W8) is not a goal of yours.",
    }
    for t, want in cases.items():
        got = GC.amend(t, before, _PERSONA)
        assert got == want, (t, got)


# =============================================================================================
# #8 — a habit moves with its goal
# =============================================================================================

@check("#8 a practice under a goal (d1 under q4) is never sized L or vetted as a large goal of its "
       "own, and is never given its own talk task")
def _():
    _fresh("child", _GOALS)
    out = G.update_goal("vet", goal_id="d1", verdict="parked", size="L", revisit_on=_d(51))
    assert out.startswith("Error:") and "practice under \"Become better at speaking Bulgarian\"" in out
    assert G.update_goal("update", goal_id="d1", size="L").startswith("Error:")
    assert _goal("d1")["status"] == "active"
    assert not GT._wants_talk({**_goal("d1"), "size": "L"})


@check("#8 parking the goal parks its practice with it; taking it up brings the practice back (an "
       "old L on it dropped); both results name the other")
def _():
    _fresh("child_follow", _GOALS.replace("parent_goal: q4}", "parent_goal: q4, size: L}"))
    out = G.update_goal("vet", goal_id="q4", verdict="parked", revisit_on=_d(51))
    assert "Its practice — Bulgarian Vocabulary — goes with it" in out, out
    d1 = _goal("d1")
    assert d1["status"] == "parked" and d1["parked_with"] == "q4" and d1["revisit_on"] == _d(51)
    out = G.update_goal("update", goal_id="q4", status="active")
    d1 = _goal("d1")
    assert d1["status"] == "active" and "size" not in d1 and "revisit_on" not in d1, d1
    assert "Bulgarian Vocabulary" in out, out
    out = G.update_goal("update", goal_id="d1", context="15 minutes with flashcards")
    assert "practice under \"Become better at speaking Bulgarian\"" in out, "raised from either side"


@check("#8 11-25's shape: a practice parked on its own with the same date as its goal comes back "
       "with it; a goal starting later takes its practice's start with it")
def _():
    goals = _GOALS.replace("status: active, size: L,", "status: parked, revisit_on: '" + _d(51) + "', size: L,") \
        .replace("status: active, parent_goal: q4}", "status: parked, revisit_on: '" + _d(51) + "', parent_goal: q4, size: L}")
    _fresh("child_1125", goals)
    G.update_goal("update", goal_id="q4", status="active", starts_on=_d(51))
    d1 = _goal("d1")
    assert d1["status"] == "active" and "size" not in d1, d1
    G.update_goal("update", goal_id="q4", starts_on=_d(60))
    assert _goal("d1")["starts_on"] == _d(60)
    b = GT.talk_block(_PERSONA, {"goal_id": "q4"})
    assert "Its practice" in b and "Bulgarian Vocabulary" in b


# =============================================================================================
# #9 — one question per goal: measured, not rewritten (ruling 6)
# =============================================================================================

@check("#9 a goal turn asking two questions is counted in the quality log; the reply is untouched; "
       "a non-goal turn is not counted")
def _():
    _fresh("q9", _GOALS)
    text = ("To get the parameters on file:\n- Which policies are under review?\n"
            "- What decisions need to be made?")
    GC.after_reply(text, _PERSONA, {"read_goals", "update_goal"})
    assert _QUALITY and _QUALITY[-1][0] == "GOAL_TURN_MULTI_QUESTION" and "2 questions" in _QUALITY[-1][2]
    _QUALITY.clear()
    GC.after_reply(text, _PERSONA, {"list_tasks"})
    GC.after_reply("Which policy is first?", _PERSONA, {"update_goal"})
    assert not _QUALITY


# =============================================================================================
# ruling 7 — every file loads on the VM's Python (3.11)
# =============================================================================================

def _py311_violations(path: str) -> list[str]:
    """F-string forms Python 3.12 allows and 3.11 refuses — a backslash or a comment inside {…},
    a quote inside {…} the same as the enclosing one. `ast.parse(feature_version=(3, 11))` does
    not catch these on a newer interpreter (measured 2026-11-25), so they are found by token."""
    bad = []
    src = Path(path).read_text(encoding="utf-8")
    stack: list[str] = []
    for t in tokenize.generate_tokens(io.StringIO(src).readline):
        if t.type == tokenize.FSTRING_START:
            q = re.sub(r"^[a-zA-Z]*", "", t.string)
            if stack and q[0] == stack[-1][0]:
                bad.append(f"{path}:{t.start[0]}: nested f-string reuses the enclosing quote")
            stack.append(q)
        elif t.type == tokenize.FSTRING_END:
            if stack:
                stack.pop()
        elif stack and t.type == tokenize.FSTRING_MIDDLE and len(stack) >= 2 and "\\" in t.string:
            bad.append(f"{path}:{t.start[0]}: backslash inside an f-string expression")
        elif stack and t.type == tokenize.STRING:
            if "\\" in t.string:
                bad.append(f"{path}:{t.start[0]}: backslash inside an f-string expression")
            if re.sub(r"^[a-zA-Z]*", "", t.string)[0] == stack[-1][0]:
                bad.append(f"{path}:{t.start[0]}: string inside an f-string reuses its quote")
        elif stack and t.type == tokenize.COMMENT:
            bad.append(f"{path}:{t.start[0]}: comment inside an f-string expression")
    return bad


@check("ruling 7: no file in core/, tools/, scripts/ or tests/ uses f-string syntax the VM's "
       "Python 3.11 refuses (three such lines kept calendar reconcile, the calendar audit and the "
       "travel check from loading on the VM since 11-11) — and the scan catches the original line")
def _():
    if not hasattr(tokenize, "FSTRING_START"):
        return                              # a 3.11 interpreter refuses these files itself
    files = [f for pat in ("core/**/*.py", "tools/**/*.py", "scripts/*.py", "tests/*.py")
             for f in glob.glob(str(ROOT / pat), recursive=True)
             if "/venv/" not in f and "site-packages" not in f]
    bad = [v for f in files for v in _py311_violations(f)]
    assert not bad, "\n".join(bad)
    probe = _TMP / "probe.py"
    probe.write_text("x = (\"a\"\n     f\"({re.sub(r'https?://\\S+', '<url>', str(e))})\")\n")
    assert _py311_violations(str(probe)), "the 11-11 line is caught"


# =============================================================================================

if __name__ == "__main__":
    passed = sum(1 for _, ok, _ in _results if ok)
    for name, ok, err in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if not ok:
            print("        " + err.replace("\n", "\n        "))
    print(f"\n{passed} passed, {len(_results) - passed} failed, {len(_results)} total")
    sys.exit(0 if passed == len(_results) else 1)
