"""
tests/test_goal_network_phase3b.py — the goal–task network, phase 3 part B: a large goal talked
through properly (the talk is the project's first task), realistic from what Metatron already knows
or looks up, ending in the verdict that lets rolling wave plan it; and how much the user looked
forward to something against how it turned out.

Plan: archive/plans/goal_task_network_plan_2026-11-18.md § 18 (this build, Mike's rulings
2026-11-24). Part A: § 17, tests/test_goal_network_phase3.py.

EVERY LIVE METER IS STUBBED (the standing rule): CalDAV, Google Routes, the day_planner model
(refusing), the project_planner model (`_MODEL_CALL`, a counting stub), push, the Goals
Interviewer's model (`core.orchestrator.run_session`, a recording stub), the public lookup
(`tools.lookup_guard.ask_public`, a counting stub). No persona data — a temp directory per check.

    .venv/bin/python tests/test_goal_network_phase3b.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import threading
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
import tools.goal_talk as GT  # noqa: E402
import tools.goals as G  # noqa: E402
import tools.horizon as H  # noqa: E402
import tools.location as L  # noqa: E402
import tools.lookup_guard as LG  # noqa: E402
import tools.obligations as O  # noqa: E402
import tools.project_plan as PP  # noqa: E402
import tools.ranking as RK  # noqa: E402
import tools.ranking_review as RR  # noqa: E402
import tools.routing as R  # noqa: E402
import tools.satisfaction as S  # noqa: E402
import tools.turn_context as TC  # noqa: E402

_results: list[tuple[str, bool, str]] = []
_TMP = Path(tempfile.mkdtemp(prefix="goal_network_p3b_"))
# No real playbook reaches these checks: the no-playbook path is tested with a language goal, and
# config/playbooks/language_learning.md (2026-11-25) would otherwise take it. A check that wants a
# playbook supplies its own directory, as "a yes starts the talk" does.
(_TMP / "no_playbooks").mkdir()
PP._PLAYBOOKS = _TMP / "no_playbooks"
TODAY = date.today()
_CLOCK = {"now": datetime.combine(TODAY, time(7, 0))}
O._now = lambda: _CLOCK["now"]
A._get_timezone = lambda: "Europe/London"
_PERSONA = "gn_phase3b"

_SHAPE = 'day: [{days: all, wake: "07:00", bed: "23:00"}]\ntravel_mode: transit\n'
_CALLS = {"day_model": 0, "planner": 0, "send": 0, "lookup": 0, "interviewer": 0}

CAL._query_events = lambda start, end, persona=None, calendars="own": {"events": [], "discovery": "ok"}
CAL._get_event_by_uid = lambda uid, persona=None: {"error": "Failed to fetch event: offline"}
R.get_travel_time = lambda *a, **k: {"journeys": [{"duration_minutes": 20}]}
L.load_zones = lambda persona=None: []
L.current_zone = lambda persona=None: {}
INTV.holds_proactive = lambda persona: False
D._quiet_now = lambda persona: False
D._idle_minutes = lambda persona: None


def _no_day_model(*a, **k):
    _CALLS["day_model"] += 1
    raise AssertionError("a day_planner model call was made")


D._call_model = _no_day_model
RC.send_one = lambda persona, text, nudge=False, **k: (_CALLS.__setitem__("send", _CALLS["send"] + 1), "ok")[1]

_REPLIES: list = []
_PAYLOADS: list = []


def _planner(payload):
    _CALLS["planner"] += 1
    _PAYLOADS.append(payload)
    if not _REPLIES:
        raise AssertionError("an unexpected project_planner call")
    r = _REPLIES.pop(0)
    return r(payload) if callable(r) else r


PP._MODEL_CALL = _planner

# The Goals Interviewer's model: records what it was given and answers with a fixed line.
_SEEN: list[dict] = []


def _interviewer(agent, message, persona=None, history=None, **k):
    _CALLS["interviewer"] += 1
    _SEEN.append({"agent": agent, "message": message, "history": list(history or [])})
    return "Where are you with it now?"


ORCH.run_session = _interviewer
ORCH._pending_tokens = lambda persona=None: set()
ORCH._pending_raised_since = lambda before, persona=None: []
ORCH.enforce_pending_receipt = lambda text, pending: text

_LOOKUP = {"answer": "<untrusted_content>Stages A1–C1; about 100–150 hours each; 3–5 hours a week; "
                     "people stall at speaking.</untrusted_content>"}


def _ask_public(question, persona, source="lookup_public_fact", max_chars=None):
    _CALLS["lookup"] += 1
    _SEEN.append({"lookup": question, "source": source})
    return _LOOKUP["answer"]


LG.ask_public = _ask_public

_TURN = {"t": {"user_turn": True}}
TC.current = lambda: _TURN["t"]

# Part A as built (rolling wave and the planner on where a check says), plus what a check names.
_FLAGS = {"build": True, "show_in_app": True, "ledger_fields": True, "synth_reads_plan": True,
          "unconfirmed_rule": True, "reshuffle_model": False, "nudges": False,
          "owns_checkins": False, "prep_tasks": True, "horizon_cap": True, "project_planner": True,
          "ranking_signals": True}
_TALK = {"goal_talk": True}
_SAT = {"satisfaction_gap": True}


def _d(n: int) -> str:
    return (TODAY + timedelta(days=n)).isoformat()


def _join() -> None:
    for th in threading.enumerate():
        if th.name.startswith("day_plan_"):
            th.join(10)


def _fresh(name: str, flags: dict | None = None, goals: str = "quarterly: []\n") -> Path:
    _join()
    d = _TMP / name
    (d / "config").mkdir(parents=True, exist_ok=True)
    for mod in (O, D, DS, L, H, RR, S, B):
        mod.persona_data_dir = lambda persona=None, _d=d: _d
    P.persona_data_dir = lambda persona=None, _d=d: _d
    DS.persona_config_dir = lambda persona=None, _d=d: _d / "config"
    (d / "config" / "goals.yaml").write_text(goals)
    # Asserts a persona is bound, as the real path (persona_config_dir) does on the server
    # (Fable S1: a talk turn on an unscoped thread raised PersonaError).
    G._goals_path = lambda _d=d: (P.resolve_persona(None), _d / "config" / "goals.yaml")[1]
    G._calling_agent = lambda: ""
    (d / "day_shape.yaml").write_text(_SHAPE)
    C._OVERRIDE = {"flags": {**_FLAGS, **(flags or {})}}
    RK._OVERRIDE = {}
    _REPLIES.clear()
    _PAYLOADS.clear()
    _SEEN.clear()
    _TURN["t"] = {"user_turn": True}
    _LOOKUP["answer"] = ("<untrusted_content>Stages A1–C1; about 100–150 hours each; 3–5 hours a "
                         "week; people stall at speaking.</untrusted_content>")
    for k in _CALLS:
        _CALLS[k] = 0
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


def _talk_tasks(gid: str = "l1") -> list[dict]:
    return [O._norm(t) for t in O._load() if t.get("source_id") == f"goal_talk:{gid}"]


def _signals() -> list[dict]:
    return [r for r in RR.read_signals(_PERSONA) if r.get("source") == "goal_network"]


def _run_planner() -> bool:
    started = PP.start_planning(_PERSONA)
    _join()
    return started


def _req(end_id: str) -> dict:
    return PP._load(_PERSONA)["requests"].get(end_id) or {}


_PROPOSED_L = "long:\n- {id: l1, title: Speak Bulgarian at a conversational level, status: proposed}\n"
_ACTIVE_SHORT = ("long:\n- id: l1\n  title: Speak Bulgarian at a conversational level\n  status: active\n"
                 "  size: L\n  vetted: {date: '" + TODAY.isoformat() + "', depth: L, pass: short, "
                 "priority: high, displaces: evening TV}\nquarterly: []\n")


def _start_talk(goals: str = _PROPOSED_L, flags: dict | None = None, name: str = "talk") -> Path:
    d = _fresh(name, {**_TALK, **(flags or {})}, goals=goals)
    G._calling_agent = lambda: "synthesizer"
    if "size: L" not in goals:
        out = G.update_goal("update", goal_id="l1", size="L")
        assert "proper talk" in out, out
    out = G.update_goal("talk", goal_id="l1")
    assert out.startswith("Started"), out
    return d


def _talk_turns(n: int = 4) -> None:
    for i in range(n):
        GT.run_turn(_PERSONA, f"answer {i}", [])


def _interviewer_vet(**kw) -> str:
    G._calling_agent = lambda: "goals_interviewer"
    args = dict(goal_id="l1", verdict="active", size="L", priority="high",
                displaces="two evenings of TV", weekly_minutes=180,
                done_means="Hold a half-hour conversation with family without switching to English",
                starting_point="Knows the alphabet and 300 words", effort_hours="300-450")
    args.update(kw)
    return G.update_goal("vet", **args)


# =============================================================================================
# Flags off — part A exactly
# =============================================================================================

@check("flags off: no talk action, no talk task, no offer, the schema and the planner payload are "
       "part A's, nothing is recorded or shown for anticipation, pause is unchanged")
def _():
    _fresh("off", goals=_PROPOSED_L)
    G._calling_agent = lambda: "synthesizer"
    out = G.update_goal("talk", goal_id="l1")
    assert out.startswith("Error: action must be one of add, update, complete, remove, vet."), out
    out = G.update_goal("vet", goal_id="l1", verdict="active", size="L", priority="high",
                        displaces="evening TV")
    assert out == "long goal l1 taken on. It is given regular time each week, not steps.", out
    assert not _talk_tasks() and not GT.current(_PERSONA)
    assert PP.sweep_unplanned(_PERSONA) == 0
    assert not _talk_tasks(), "the sweep opens no talk task while off"
    _, upd = G.goal_schemas()
    props = upd["input_schema"]["properties"]
    assert "weekly_minutes" not in props and "talk" not in props["action"]["description"]
    assert upd["description"] == G.UPDATE_GOAL_SCHEMA["description"]
    # Ignored while off: the talk's fields are not stored on the goal.
    G._calling_agent = lambda: "goals_interviewer"
    G.update_goal("update", goal_id="l1", weekly_minutes=120, done_means="x")
    assert "weekly_minutes" not in _goal("l1") and "done_means" not in _goal("l1")
    assert "done_means" not in PP._end("l1")
    assert S.context_block(_PERSONA) == "" and S.finance_line(_PERSONA) == ""
    assert S.note_expectation("before", "the jacket", "can't wait", 5, cls="purchase").startswith(
        "not recorded")
    assert not _signals()
    assert INTV.pause_interview() == "There is no active interview to pause."
    sch = {x["name"]: x for x in ORCH.register_tools()[0]}
    assert sch["note_expectation"]["description"].startswith(
        "Only on a turn whose context carries an ANTICIPATION AND EXPERIENCE block"), \
        "off, no block exists, so the tool's own description rules it out (Fable S6)"
    assert INTV.pause_schema() is INTV.PAUSE_INTERVIEW_SCHEMA
    assert _CALLS["lookup"] == 0 and _CALLS["interviewer"] == 0


# =============================================================================================
# The talk is the project's first task
# =============================================================================================

@check("sized L by Synth: one talk task under the goal — the project's first task, flexible, dated, "
       "missable — and the result says to offer the talk; sizing again opens no second task")
def _():
    _fresh("task", _TALK, goals=_PROPOSED_L)
    G._calling_agent = lambda: "synthesizer"
    out = G.update_goal("update", goal_id="l1", size="L")
    assert "deserves a proper talk" in out and "update_goal action=talk" in out, out
    tasks = _talk_tasks()
    assert len(tasks) == 1, tasks
    t = tasks[0]
    assert t["part_of"] == "l1" and t["goal_id"] == "l1" and t["flexible"] and t["status"] == "open"
    assert t["due"] == _d(14) and t["eligible_from"] == _d(0) and t["minutes"] == 30
    assert t.get("stakes") == "missable" and t["what"] == "Talk through: Speak Bulgarian at a conversational level"
    out = G.update_goal("update", goal_id="l1", size="L")
    assert len(_talk_tasks()) == 1 and "proper talk" not in out, "offered once (Fable L4)"
    out = G.update_goal("vet", goal_id="l1", verdict="active", size="L", priority="high",
                        displaces="evening TV")
    assert "proper talk" not in out and len(_talk_tasks()) == 1, out
    assert "given regular time each week" in out
    assert _goal("l1")["vetted"]["pass"] == "short"


@check("the talk task is never closed by a tap or a 'done' — only by the talk's verdict; skipping "
       "it still works")
def _():
    _fresh("task_done", _TALK, goals=_ACTIVE_SHORT)
    assert GT.sweep(_PERSONA) == 1
    tid = _talk_tasks()[0]["id"]
    with O._user_act():
        out = O.update_task(tid, "done", evidence="tapped Done")
    assert out.startswith("error: this one is done by talking it through"), out
    assert "update_goal" not in out and "action" not in out, "the app shows this text (Fable L3)"
    assert _talk_tasks()[0]["status"] == "open"
    rows = [i for i in O.today_items() if i["task_id"] == tid]
    assert not rows or rows[0]["actions"] == ["dismissed"], rows
    with O._user_act():
        out = O.update_task(tid, "skipped", evidence="not now")
    assert "dismissed" in out and _talk_tasks()[0]["status"] == "dismissed", out


@check("the daily sweep gives an existing L goal (Bulgarian predates this build) its talk task "
       "once; a skipped one is not reopened behind the user's back")
def _():
    _fresh("sweep", _TALK, goals=_ACTIVE_SHORT)
    assert GT.sweep(_PERSONA) == 1 and len(_talk_tasks()) == 1
    assert GT.sweep(_PERSONA) == 0
    O.update_task(_talk_tasks()[0]["id"], "dismissed", evidence="no")
    assert GT.sweep(_PERSONA) == 0 and not [t for t in _talk_tasks() if t["status"] == "open"]
    # The sweep runs inside the planner's daily sweep.
    _fresh("sweep_hook", _TALK, goals=_ACTIVE_SHORT)
    PP.sweep_unplanned(_PERSONA)
    assert len(_talk_tasks()) == 1


# =============================================================================================
# Starting, the turns, stopping
# =============================================================================================

@check("a yes starts the talk: the next message is the Interviewer's, opened once; a goal that is "
       "not L is refused; the talk starts from the playbook when one applies — no lookup")
def _():
    _start_talk(name="start")
    talk = GT.active(_PERSONA)
    assert talk and talk["goal_id"] == "l1" and GT.needs_opening(_PERSONA)
    assert talk["task_id"] == _talk_tasks()[0]["id"]
    G._calling_agent = lambda: "synthesizer"
    G.update_goal("add", horizon="quarterly", title="Renew the passport", size="M")
    out = G.update_goal("talk", goal_id="q1")
    assert out.startswith("error: only a goal that needs regular time"), out
    d = _TMP / "start"
    pb = d / "playbooks"
    pb.mkdir(exist_ok=True)
    (pb / "lang.md").write_text("applies_when: speak, speaking, learn | bulgarian\n"
                                "# Learning a language\nStages A1 to C1; speaking from week one.\n")
    saved = PP._PLAYBOOKS
    PP._PLAYBOOKS = pb
    try:
        assert GT.claim_opening(_PERSONA) and GT.claim_opening(_PERSONA) is None, "claimed once"
        reply = GT.run_turn(_PERSONA, GT.opening_prompt(_PERSONA), [], proactive=True)
    finally:
        PP._PLAYBOOKS = saved
    assert reply == "Where are you with it now?"
    msg = _SEEN[-1]["message"]
    assert _SEEN[-1]["agent"] == "goals_interviewer" and msg.startswith("GOAL TALK")
    assert "Speak Bulgarian" in msg and "speaking from week one" in msg, msg
    assert _CALLS["lookup"] == 0, "a playbook is the starting shape: no lookup"
    assert not GT.needs_opening(_PERSONA) and GT.current(_PERSONA)["turns"] == 1


@check("no playbook: one guarded lookup of what it realistically takes, at the talk's first turn "
       "only, built from the goal's own words (never private_why); a refused lookup leaves nothing")
def _():
    goals = _PROPOSED_L.replace("status: proposed}", "status: proposed, private_why: SECRET-WHY}")
    _start_talk(goals=goals, name="research")
    GT.run_turn(_PERSONA, "yes let's", [])
    GT.run_turn(_PERSONA, "I know the alphabet", [])
    assert _CALLS["lookup"] == 1, _CALLS
    q = next(s for s in _SEEN if "lookup" in s)
    assert "learning Bulgarian as an adult" in q["lookup"], q
    assert "conversational level" not in q["lookup"] and "SECRET-WHY" not in q["lookup"], \
        "a generic subject from a fixed list, never the user's sentence (Fable S5)"
    assert q["source"] == "goal_talk"
    msg = _SEEN[-1]["message"]
    assert "looked up (outside content" in msg and "people stall at speaking" in msg, msg
    assert GT.last_shape("l1", _PERSONA)["source"] == "research"
    _start_talk(name="research_refused")
    _LOOKUP["answer"] = "refused: the question carries a money amount. Nothing left this device."
    GT.run_turn(_PERSONA, "hi", [])
    assert GT.current(_PERSONA)["shape"] == {"source": "none", "text": ""}
    assert "looked up" not in _SEEN[-1]["message"]


@check("stopping: pause_interview pauses the talk (the first interview untouched), the task stays "
       "open, and saying yes again picks up the same talk; a talk left quiet lapses on its own")
def _():
    _start_talk(name="pause")
    first = GT.current(_PERSONA)["id"]
    G._calling_agent = lambda: "goals_interviewer"
    out = INTV.pause_interview()
    assert out.startswith("Paused. What was recorded is kept"), out
    assert not GT.active(_PERSONA) and GT.current(_PERSONA)["status"] == "paused"
    assert _talk_tasks()[0]["status"] == "open"
    G._calling_agent = lambda: "synthesizer"
    assert G.update_goal("talk", goal_id="l1").startswith("Started")
    assert GT.current(_PERSONA)["id"] == first and GT.needs_opening(_PERSONA)
    # Idle past `idle_hours` (6): the next message goes back to the usual conversation.
    st = json.loads(GT._path(_PERSONA).read_text())
    st["talk"]["updated_at"] = (datetime.now().astimezone() - timedelta(hours=7)).isoformat()
    GT._path(_PERSONA).write_text(json.dumps(st))
    assert GT.active(_PERSONA) is None and GT.current(_PERSONA)["status"] == "paused"


@check("the talk block shows what is recorded, what is still to settle, and code's arithmetic; a "
       "long talk is told to settle and offer to carry on")
def _():
    _start_talk(name="block")
    G._calling_agent = lambda: "goals_interviewer"
    out = G.update_goal("update", goal_id="l1", weekly_minutes=120, effort_hours="200-300",
                        due=_d(364), done_means="Chat with family for half an hour")
    assert "changed" in out, out
    b = GT.talk_block(_PERSONA, GT.current(_PERSONA))
    assert "minutes a week: 120" in b and "what done looks like: Chat with family" in b, b
    assert "Still to settle: where they are now, what it takes that time from, where it ranks" in b
    assert "Arithmetic (code): At 120 minutes a week, about 200–300 hours takes 23 months to " in b
    assert "it needs about 231–346 minutes a week" in b and "Their time does not reach" in b, b
    talk = dict(GT.current(_PERSONA), turns=15)
    assert "This talk is long now" in GT.talk_block(_PERSONA, talk)


@check("arithmetic is code: hours over minutes a week, and what a date needs")
def _():
    line = GT.realism(120, "200-300", _d(364), today=TODAY)
    assert "takes 23 months to 2.9 years" in line and "(52 weeks) it needs about 231–346" in line, line
    assert GT.realism(300, 50, None, today=TODAY).startswith("At 300 minutes a week, about 50 hours takes 2 months")
    assert GT.realism(0, "100", _d(70), today=TODAY) == f"By {_d(70)} (10 weeks) it needs about 600 minutes a week."
    assert GT.realism(120, "", _d(70)) == ""
    assert GT.parse_effort("about 200 to 300 hours") == [200, 300] and GT.parse_effort("x") is None


# =============================================================================================
# The verdict — the full pass rolling wave plans from
# =============================================================================================

@check("the Interviewer's verdict in a talk writes the full pass (rolling wave OFF — the talk alone "
       "licenses it), the weekly time, what done means, where they are and the effort; the talk ends "
       "and its task is closed done by code")
def _():
    _start_talk(name="vet")
    out = _interviewer_vet()
    assert out.startswith("Error: this has hardly been talked through"), out
    _talk_turns()
    out = _interviewer_vet(weekly_minutes=None, done_means="")
    assert out.startswith("Error: before it is taken on") and "weekly_minutes" in out \
        and "done_means" in out, out
    assert _goal("l1")["status"] == "proposed"
    out = _interviewer_vet()
    g = _goal("l1")
    assert g["status"] == "active" and g["vetted"]["pass"] == "full", g
    assert g["weekly_minutes"] == 180 and g["effort_hours"] == [300, 450]
    assert g["done_means"].startswith("Hold a half-hour") and g["starting_point"].startswith("Knows")
    assert "The talk is over" in out and "Arithmetic: At 180 minutes a week" in out, out
    assert "planned out of sight" in out and "not steps" not in out
    assert GT.current(_PERSONA) is None
    past = json.loads(GT._path(_PERSONA).read_text())["past"]
    assert past[-1]["verdict"] == "active" and past[-1]["goal_id"] == "l1"
    t = _talk_tasks()[0]
    assert t["status"] == "done" and "talked through" in t["evidence"], t


@check("Synth's vet never writes the full pass — not even while a talk on that goal is running; "
       "and an Interviewer vet outside a talk stays short while rolling wave is off")
def _():
    _start_talk(name="synth_never")
    G._calling_agent = lambda: "synthesizer"
    G.update_goal("vet", goal_id="l1", verdict="active", size="L", priority="high",
                  displaces="TV", weekly_minutes=180, done_means="chat")
    assert _goal("l1")["vetted"]["pass"] == "short"
    assert GT.current(_PERSONA) is not None, "Synth's vet does not end the Interviewer's talk"
    _fresh("interviewer_no_talk", _TALK, goals=_PROPOSED_L)
    G._calling_agent = lambda: "goals_interviewer"
    G.update_goal("vet", goal_id="l1", verdict="active", size="L", priority="high", displaces="TV")
    assert _goal("l1")["vetted"]["pass"] == "short"


@check("parked at the end of a talk (any time, no minimum): the talk ends and its task closes; the "
       "goal does NOT get the full pass, so a later short pass can never plan it")
def _():
    _start_talk(name="parked")
    out = _interviewer_vet(verdict="parked", revisit_on=_d(60))
    assert "parked until" in out and "The talk is over" in out, out
    assert _goal("l1")["vetted"].get("pass") != "full", "parking never licenses planning (Fable S2)"
    assert _talk_tasks()[0]["status"] == "done" and GT.current(_PERSONA) is None


@check("end to end: after the Interviewer's verdict the daily sweep plans the goal in waves (part "
       "A's path), and the planner is given what the talk settled and what it started from")
def _():
    _start_talk(name="e2e", flags={"rolling_wave": True})
    _talk_turns()                                        # the shape is made: a lookup, no playbook
    _interviewer_vet()
    assert PP.sweep_unplanned(_PERSONA) == 1
    r = _req("l1")
    assert r["status"] == "queued" and r["size"] == "L" and r["weekly_minutes"] == 180, r
    ms = [{"key": "m1", "what": "Order a coffee and introduce yourself", "minutes": 600,
           "eligible_from": _d(0), "due": _d(28)},
          {"key": "m2", "what": "Hold a ten-minute conversation", "minutes": 900,
           "eligible_from": _d(28), "due": _d(70)}]
    steps = [{"key": "a", "what": "Book a first lesson with a tutor", "minutes": 20,
              "eligible_from": _d(0), "due": _d(5), "needs": []}]
    _REPLIES.append(json.dumps({"size": "L", "milestones": ms, "steps": steps, "note": "ok"}))
    assert _run_planner()
    p = _PAYLOADS[-1]
    es = p["end_state"]
    assert es["done_means"].startswith("Hold a half-hour") and es["effort_hours"] == [300, 450]
    assert es["starting_point"].startswith("Knows") and "people stall" in p["researched"], p
    assert p["wave"]["mode"] == "first"
    assert _req("l1")["status"] == "planned"
    assert [t["what"] for t in O._load() if t.get("part_of") == "l1" and t["status"] == "open"] \
        == ["Book a first lesson with a tutor"]
    assert PP.sweep_unplanned(_PERSONA) == 0


# =============================================================================================
# Anticipated vs experienced — trigger 3
# =============================================================================================

def _pair(item: str, cls: str, before: int, after: int, asked: bool = False) -> None:
    out = S.note_expectation("before", item, f"looking forward to {item}", before, cls=cls,
                             asked=asked)
    assert out.startswith("kept (pair "), out
    pid = out.split("pair ")[1].split(")")[0]
    assert S.note_expectation("after", item, f"{item} was ok", after, pair=pid).startswith("kept")


@check("trigger 3 writes both rows to ranking_signals.jsonl (source goal_network) — ids, class, "
       "scores and the user's own words only; only on the user's own turn; never with signals off")
def _():
    _fresh("sat_rows", _SAT)
    out = S.note_expectation("before", "the jacket", "I can't wait for the jacket", 5,
                             cls="purchase", when=_d(-1))
    pid = out.split("pair ")[1].split(")")[0]
    out = S.note_expectation("after", "jacket", "meh, it's fine", 2, cls="purchase")  # by its words
    assert out.startswith("kept"), out
    rows = _signals()
    assert [r["kind"] for r in rows] == ["satisfaction_anticipated", "satisfaction_experienced"]
    assert rows[1]["pair"] == pid and rows[1]["class"] == "purchase" and rows[0]["when"] == _d(-1)
    assert set(rows[0]) == {"at", "day", "source", "score", "item", "text", "asked", "kind",
                            "pair", "class", "when"}, rows[0]
    _TURN["t"] = {"user_turn": False}
    assert S.note_expectation("before", "x", "y", 3, cls="trip").startswith("error: not recorded")
    _fresh("sat_signals_off", {**_SAT, "ranking_signals": False})
    assert S.note_expectation("before", "x", "y", 3, cls="trip").startswith("not recorded")
    assert not _signals()


@check("the gap per class is code; it is evidence to Synth at 3 pairs and a lesson — good or bad — "
       "only at 4 consistent pairs, at most once every 30 days; a class without history gets neither")
def _():
    _fresh("sat_gap", _SAT)
    for i in range(3):
        _pair(f"parcel {i}", "purchase", 4, 2)
    out = S.note_expectation("before", "new headphones", "so excited", 5, cls="purchase")
    assert "For your judgement, not to say: their last 3 purchases" in out, out
    assert "LESSON" not in out
    S.note_expectation("after", "headphones", "disappointing", 2, cls="purchase")
    out = S.note_expectation("before", "a lamp", "really want it", 4, cls="purchase")
    assert "LESSON" in out and "turned out less than they hoped" in out, out
    assert sum(1 for r in _signals() if r["kind"] == "satisfaction_lesson") == 1
    S.note_expectation("after", "lamp", "fine", 2, cls="purchase")
    out = S.note_expectation("before", "a rug", "can't wait", 4, cls="purchase")
    assert "LESSON" not in out, "at most once every 30 days"
    out = S.note_expectation("before", "a run", "dreading it", 1, cls="activity")
    assert "For your judgement" not in out and "LESSON" not in out
    h = S.history(_PERSONA)["purchase"]
    assert h["n"] == 5 and h["consistent"] and h["gap"] < 0, h
    # Good news is a lesson too: dreaded, then enjoyed.
    _fresh("sat_good", _SAT)
    for i in range(4):
        _pair(f"gym {i}", "activity", 2, 4)
    out = S.note_expectation("before", "gym", "ugh", 2, cls="activity")
    assert "turned out better than they expected" in out, out


@check("targeted and rare: asking is offered only for a class a goal names (or an over-budget "
       "purchase, or a gap), at most one question a week; listening is always on; 'how was it?' "
       "comes the day after (a purchase 3 days after); Finance sees how purchases land")
def _():
    goals = "weekly:\n- {id: w4, title: Purpose-Driven Exercise, status: active}\n"
    _fresh("sat_ask", _SAT, goals=goals)
    blk = S.context_block(_PERSONA, user_turn=True)
    assert blk.startswith("ANTICIPATION AND EXPERIENCE — at most one question this week")
    assert "keep it with note_expectation (asked false)" in blk
    assert "activities and exercise (a goal: Purpose-Driven Exercise)" in blk, blk
    assert "purchases" not in blk
    S.note_expectation("before", "Saturday swim", "looking forward to it", 4, cls="activity",
                       when=_d(0), asked=True)
    blk = S.context_block(_PERSONA, user_turn=True)
    assert "may ask" not in blk and "Ask once" not in blk, "the week's one question is used"
    assert "keep it with note_expectation" in blk, "listening stays on"
    # A week later the question is free again, and the swim's "how was it?" is due.
    _CLOCK["now"] = datetime.combine(TODAY + timedelta(days=7), time(9, 0))
    blk = S.context_block(_PERSONA, user_turn=True, today=TODAY + timedelta(days=7))
    assert "Ask once, in passing, how it turned out: \"Saturday swim\"" in blk, blk
    # A purchase (untargeted, unasked) is never followed up; asked, it waits 3 days.
    _fresh("sat_purchase", _SAT)
    S.note_expectation("before", "a kettle", "need it", 3, cls="purchase", when=_d(0))
    assert "Ask once" not in S.context_block(_PERSONA, user_turn=True, today=TODAY + timedelta(days=4))
    _fresh("sat_purchase_asked", _SAT)
    S.note_expectation("before", "a kettle", "need it", 3, cls="purchase", when=_d(0), asked=True)
    assert "Ask once" not in S.context_block(_PERSONA, user_turn=True, today=TODAY + timedelta(days=2))
    assert "Ask once" in S.context_block(_PERSONA, user_turn=True, today=TODAY + timedelta(days=7)), \
        "asked about, so followed up: 3 days on, once the week's question is free"
    # Finance's line from 3 purchase pairs.
    _fresh("sat_finance", _SAT)
    assert S.finance_line(_PERSONA) == ""
    for i in range(3):
        _pair(f"item {i}", "purchase", 5, 2)
    line = S.finance_line(_PERSONA)
    assert line.startswith("HOW PURCHASES LAND") and "looked forward to about 5.0, turned out about 2.0" in line


@check("an ask not taken is dropped after two days")
def _():
    goals = "weekly:\n- {id: w4, title: Purpose-Driven Exercise, status: active}\n"
    _fresh("sat_offer", _SAT, goals=goals)
    S.note_expectation("before", "the class", "can't wait", 5, cls="activity", when=_d(0))
    for n in (1, 2):
        assert "Ask once" in S.context_block(_PERSONA, user_turn=True, today=TODAY + timedelta(days=n))
    assert "Ask once" not in S.context_block(_PERSONA, user_turn=True, today=TODAY + timedelta(days=3))


@check("Fable L7: 'how it turned out' pairs only with the same class, something already happened, "
       "and most of its distinctive words — never one shared word like 'new'; else kept unpaired")
def _():
    _fresh("sat_match", _SAT)
    S.note_expectation("before", "new phone case", "want it", 2, cls="purchase", when=_d(-2))
    S.note_expectation("before", "trip to Sofia", "can't wait", 5, cls="trip", when=_d(30))
    S.note_expectation("after", "the new jacket", "love it", 5, cls="purchase")
    S.note_expectation("after", "trip to Sofia", "great", 5, cls="trip")
    after = [r for r in _signals() if r["kind"] == "satisfaction_experienced"]
    assert [r["pair"] for r in after] == [None, None], after
    assert not S.pairs(_PERSONA)
    assert S.note_expectation("after", "x", "y", 3).startswith("error: `class` is required")


@check("Fable S8/L12 + verify N3: a specific 'how did it turn out?' spends the week's budget by "
       "day on the user's own turns only — scheduled builds stamp nothing — and the standing "
       "'you may ask when one comes up' line spends nothing")
def _():
    goals = "weekly:\n- {id: w4, title: Purpose-Driven Exercise, status: active}\n"
    _fresh("sat_invites", _SAT, goals=goals)
    for n in range(5):                                  # standing line: never spent
        assert "may ask" in S.context_block(_PERSONA, user_turn=True,
                                            today=TODAY + timedelta(days=n))
    assert not S._state(_PERSONA).get("invites")
    S.note_expectation("before", "the class", "can't wait", 5, cls="activity", when=_d(0))
    for _ in range(3):
        S.context_block(_PERSONA, user_turn=False, today=TODAY + timedelta(days=1))
    assert not S._state(_PERSONA).get("invites"), "a scheduled build stamps nothing"
    assert "Ask once" in S.context_block(_PERSONA, user_turn=True, today=TODAY + timedelta(days=1))
    assert "Ask once" in S.context_block(_PERSONA, user_turn=True, today=TODAY + timedelta(days=2))
    blk = S.context_block(_PERSONA, user_turn=True, today=TODAY + timedelta(days=3))
    assert "Ask once" not in blk and "may ask" not in blk, "two days spent: listen only"


@check("Fable S1: a talk turn and its opening prompt work on a thread with NO persona bound (the "
       "server's executor)")
def _():
    _start_talk(name="unscoped")
    out: dict = {}

    def run():
        try:
            out["prompt"] = GT.opening_prompt(_PERSONA)
            out["reply"] = GT.run_turn(_PERSONA, "hello", [])
            out["active"] = GT.active(_PERSONA)
        except Exception as exc:  # noqa: BLE001
            out["err"] = repr(exc)

    th = threading.Thread(target=run)
    th.start()
    th.join(10)
    assert "err" not in out, out
    assert "Speak Bulgarian" in out["prompt"] and out["reply"] == "Where are you with it now?"
    assert out["active"] and _CALLS["interviewer"] == 1


@check("Fable S2: the Interviewer's 'active' in the opening turn is refused — the full pass needs "
       "the user's own words in the talk several times")
def _():
    _start_talk(name="no_opening_vet")
    GT.claim_opening(_PERSONA)
    GT.run_turn(_PERSONA, GT.opening_prompt(_PERSONA), [], proactive=True)
    assert _interviewer_vet().startswith("Error: this has hardly been talked through")
    _talk_turns(3)
    assert _interviewer_vet().startswith("Error: this has hardly been talked through")
    _talk_turns(1)
    assert "taken on" in _interviewer_vet() and _goal("l1")["vetted"]["pass"] == "full"


@check("Fable S3: a talk never starts without the user's own turn, and ends — routing back to the "
       "usual conversation — when its goal is closed, removed or made smaller")
def _():
    _fresh("no_yes", _TALK, goals=_ACTIVE_SHORT)
    G._calling_agent = lambda: "synthesizer"
    _TURN["t"] = {"user_turn": False}
    assert G.update_goal("talk", goal_id="l1").startswith("error: a talk starts only")
    assert GT.current(_PERSONA) is None
    for how in ("declined", "removed", "resized"):
        _start_talk(goals=_ACTIVE_SHORT, name=f"gone_{how}")
        assert GT.active(_PERSONA)
        G._calling_agent = lambda: "synthesizer"
        if how == "declined":
            G.update_goal("vet", goal_id="l1", verdict="declined")
        elif how == "removed":
            G.update_goal("remove", goal_id="l1")
        else:
            G.update_goal("update", goal_id="l1", size="M")
        assert GT.active(_PERSONA) is None and GT.current(_PERSONA) is None, how
        assert not [t for t in _talk_tasks() if t["status"] == "open"], how


@check("Fable S4: the talk task is not a plan step — the goal keeps its weekly time, a slipping talk "
       "task never fires 'is this still wanted?', and a goal resized to M is planned")
def _():
    import tools.goal_network as GN
    _fresh("not_a_step", {**_TALK, "revet": True}, goals=_ACTIVE_SHORT)
    GT.sweep(_PERSONA)
    assert _talk_tasks() and not PP.has_plan("l1", _PERSONA)
    assert not PP._open_steps("l1", _PERSONA) and not PP._adoptable(PP._end("l1"), _PERSONA)
    assert not GN._steps_of("l1", O._load())
    G._calling_agent = lambda: "synthesizer"
    G.update_goal("update", goal_id="l1", size="M", due=_d(40))
    assert not [t for t in _talk_tasks() if t["status"] == "open"]
    assert PP.plan_project("l1", size="M").startswith("Queued")


@check("Fable L2 + S7: a second goal's talk keeps the first one's (same id when resumed), and a "
       "pause with a day brings the talk task back that day")
def _():
    goals = _ACTIVE_SHORT + "- {id: q2, title: Learn the piano, status: active, size: L}\n"
    goals = goals.replace("quarterly: []\n", "quarterly:\n")
    _start_talk(goals=goals, name="two_talks")
    first = GT.current(_PERSONA)["id"]
    G._calling_agent = lambda: "synthesizer"
    assert G.update_goal("talk", goal_id="q2").startswith("Started")
    assert GT.current(_PERSONA)["goal_id"] == "q2"
    G.update_goal("talk", goal_id="l1")
    assert GT.current(_PERSONA)["id"] == first, "picked up where it stood"
    G._calling_agent = lambda: "goals_interviewer"
    out = INTV.pause_interview(resume_on=_d(20))
    assert f"comes back on their list on {_d(20)}" in out, out
    t = _talk_tasks()[0]
    assert t["eligible_from"] == _d(20) and t["due"] >= _d(27), t


@check("Fable L5 + L6: a long lookup keeps its closing tag; effort with separators or years reads "
       "the hours")
def _():
    _start_talk(name="long_lookup")
    _LOOKUP["answer"] = None
    captured = {}

    def ask(question, persona, source="x", max_chars=None):
        captured["max"] = max_chars
        return "<untrusted_content>" + ("x" * 50) + "</untrusted_content>"

    saved = LG.ask_public
    LG.ask_public = ask
    try:
        GT.run_turn(_PERSONA, "hi", [])
    finally:
        LG.ask_public = saved
    assert captured["max"] == GT._SHAPE_MAX
    assert GT.current(_PERSONA)["shape"]["text"].endswith("</untrusted_content>")
    assert GT.parse_effort("10,000 hours") == [10000, 10000]
    assert GT.parse_effort("1,500-2,000") == [1500, 2000]
    assert GT.parse_effort("2 years, roughly 400 hours") == [400, 400]


@check("Fable L9 + L10: flag off, a full-pass L vet reads as part A did; a first interview in "
       "progress is what pause_interview pauses")
def _():
    goals = _ACTIVE_SHORT.replace("pass: short", "pass: full")
    _fresh("l9", goals=goals)
    G._calling_agent = lambda: "synthesizer"
    out = G.update_goal("vet", goal_id="l1", verdict="active", size="L", priority="high",
                        displaces="TV")
    assert out == "long goal l1 taken on. It is given regular time each week, not steps.", out
    _start_talk(name="l10")
    saved, saved_pause = INTV.status, INTV.pause
    INTV.status = lambda persona: "active"
    INTV.pause = lambda persona: True
    try:
        out = INTV.pause_interview()
    finally:
        INTV.status, INTV.pause = saved, saved_pause
    assert out.startswith("Paused. Everything saved so far is kept"), out
    assert GT.active(_PERSONA), "the goal talk was not the one paused"


@check("verify S2: while goal_talk is on, an Interviewer vet of a DIFFERENT L goal mid-talk stays "
       "short, even with rolling wave on")
def _():
    goals = _PROPOSED_L + "- {id: l2, title: Learn the piano, status: proposed}\n"
    _start_talk(goals=goals, flags={"rolling_wave": True}, name="other_goal")
    _talk_turns()
    G._calling_agent = lambda: "goals_interviewer"
    G.update_goal("vet", goal_id="l2", verdict="active", size="L", priority="low",
                  displaces="TV", weekly_minutes=60, done_means="play a piece")
    assert _goal("l2")["vetted"]["pass"] == "short"


@check("verify N1: a lookup subject only where the goal's words make it something to learn")
def _():
    rs = lambda title: GT.research_subject({"title": title})
    assert rs("Become better at speaking Bulgarian").startswith("learning Bulgarian as an adult")
    assert "English" not in rs("Speak Bulgarian at a conversational level")
    assert rs("Learn to play the piano") == "learning to play the piano as an adult beginner"
    assert rs("Run a marathon in spring").startswith("training to run")
    assert rs("Strength and Flexibility Training").startswith("building strength")
    for t in ("Polish my CV and get a new job", "Run my own business", "Read a book a week",
              "Paint the house and fence", "Learn the dress code of formal Latin dance",
              "Swim for the kids"):
        assert rs(t) is None, t


@check("verify N4: an empty or unreadable goals read never ends a talk; goals are written atomically")
def _():
    _start_talk(name="n4")
    path = G._goals_path()
    keep = path.read_text()
    path.write_text("")
    O._GOAL_CACHE.update(key=None)
    assert GT.active(_PERSONA), "unknown is not removed"
    assert GT.sweep(_PERSONA) == 0 and _talk_tasks()[0]["status"] == "open"
    path.write_text(keep)
    O._GOAL_CACHE.update(key=None)
    G._calling_agent = lambda: "goals_interviewer"
    G.update_goal("update", goal_id="l1", context="noted")
    assert not list(path.parent.glob(".goals.*")) and "noted" in path.read_text()


@check("verify N5: a range in another unit, or hours a week, is not the effort")
def _():
    assert GT.parse_effort("3-4 months at 5 hours a week") is None
    assert GT.parse_effort("about 200 to 300 hours") == [200, 300]
    assert GT.parse_effort("200-300") == [200, 300] and GT.parse_effort("~250") == [250, 250]


@check("verify L1: a message sent while the opening was generating is answered with the opening in "
       "its history — one conversation, not two")
def _():
    _start_talk(name="l1_stitch")
    GT.claim_opening(_PERSONA)
    GT.run_turn(_PERSONA, GT.opening_prompt(_PERSONA), [], proactive=True)
    GT.run_turn(_PERSONA, "I know a few hundred words", [])     # history loaded before the opening
    h = _SEEN[-1]["history"]
    assert h and h[-1] == {"role": "assistant", "content": "Where are you with it now?"}, h
    GT.run_turn(_PERSONA, "next", [])
    assert _SEEN[-1]["history"] == [], "stitched once, not on every turn"


def main() -> int:
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if detail:
            for line in detail.splitlines():
                print(f"        {line}")
    passed = sum(1 for _, ok, _ in _results if ok)
    print(f"\n{passed} passed, {len(_results) - passed} failed, {len(_results)} total")
    return 0 if passed == len(_results) else 1


if __name__ == "__main__":
    sys.exit(main())
