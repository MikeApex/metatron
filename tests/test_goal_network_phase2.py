"""
tests/test_goal_network_phase2.py — the goal–task network, phase 2: a goal or obligation stated in
chat is recorded as being considered, sized and checked in the turn, queued, planned out of sight
by the project planner in the scheduler's tick, and fed one step at a time.

Plan: archive/plans/goal_task_network_plan_2026-11-18.md — § 10 governs (R3, R4, R6, R8), plus
§ 4.2 S/M, § 4.3, § 4.4, § 4.6, § 11 (adoption), Mike's 2026-11-21 skip ruling (implied done), and
the 2026-11-21 gap (a precursor stated in chat follows its event; a later finding adopts it).

EVERY LIVE METER IS STUBBED (the standing rule): CalDAV (`_query_events`, `_get_event_by_uid`),
Google Routes, the day_planner model (refusing), the project_planner model (`_MODEL_CALL`, a
counting stub), push (`core.remote_client.send_one`). No persona data — a temp directory per check.

    python3 tests/test_goal_network_phase2.py
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
import core.persona as P  # noqa: E402
import core.remote_client as RC  # noqa: E402
import tools.ambient as A  # noqa: E402
import tools.caldav as CAL  # noqa: E402
import tools.day_plan as D  # noqa: E402
import tools.day_plan_config as C  # noqa: E402
import tools.day_shape as DS  # noqa: E402
import tools.goals as G  # noqa: E402
import tools.horizon as H  # noqa: E402
import tools.location as L  # noqa: E402
import tools.obligations as O  # noqa: E402
import tools.project_plan as PP  # noqa: E402
import tools.routing as R  # noqa: E402

_results: list[tuple[str, bool, str]] = []
_TMP = Path(tempfile.mkdtemp(prefix="goal_network_p2_"))
TODAY = date.today()                      # the horizon ledger dates by date.today()
_CLOCK = {"now": datetime.combine(TODAY, time(7, 0))}
O._now = lambda: _CLOCK["now"]
A._get_timezone = lambda: "Europe/London"
_PERSONA = "gn_phase2"

_SHAPE = """\
day: [{days: all, wake: "07:00", bed: "23:00"}]
windows:
  - {activity: family, days: all, from: "17:30", to: "20:30", strength: protected}
travel_mode: transit
"""
_EVENTS: dict = {"v": []}
_CALLS = {"day_model": 0, "planner": 0, "send": 0}


def _query_events(start, end, persona=None, calendars="own"):
    return {"events": json.loads(json.dumps(_EVENTS["v"])), "discovery": "ok"}


CAL._query_events = _query_events
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


def _send_one(persona, text, nudge=False, **k):
    _CALLS["send"] += 1
    return "ok"


RC.send_one = _send_one

# The project planner's model: a queue of replies (str), each call pops one.
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

_FLAGS = {"build": True, "show_in_app": True, "ledger_fields": True, "synth_reads_plan": True,
          "unconfirmed_rule": True, "reshuffle_model": False, "nudges": False,
          "owns_checkins": False, "prep_tasks": True, "horizon_cap": True, "project_planner": True}


def _d(n: int) -> str:
    return (TODAY + timedelta(days=n)).isoformat()


def _ev(uid, title, start, end, location=""):
    return {"uid": uid, "title": title, "start": start, "end": end, "location": location,
            "status": "", "calendars": ["Main"], "calendar_ids": ["/cal/main"], "read_only": False}


def _join() -> None:
    for th in threading.enumerate():
        if th.name.startswith("day_plan_"):
            th.join(10)


def _fresh(name: str, flags: dict | None = None, goals: str = "quarterly: []\n") -> Path:
    _join()
    d = _TMP / name
    (d / "config").mkdir(parents=True, exist_ok=True)
    for mod in (O, D, DS, L, H):
        mod.persona_data_dir = lambda persona=None, _d=d: _d
    DS.persona_config_dir = lambda persona=None, _d=d: _d / "config"
    (d / "config" / "goals.yaml").write_text(goals)
    G._goals_path = lambda _d=d: _d / "config" / "goals.yaml"
    G._calling_agent = lambda: ""
    (d / "day_shape.yaml").write_text(_SHAPE)
    C._OVERRIDE = {"flags": {**_FLAGS, **(flags or {})}}
    _EVENTS["v"] = []
    _REPLIES.clear()
    _PAYLOADS.clear()
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
                             + "".join(traceback.format_exc().splitlines(True)[-5:])))
        finally:
            _join()
            C._OVERRIDE = None
        return fn
    return deco


def _goal(gid: str) -> dict:
    O._GOAL_CACHE.update(key=None)
    return O._goal_index()[gid]


def _vetted_taxes(due_days: int = 30) -> str:
    """A taxes goal stated in chat, recorded as considered, then vetted M — what Synth does."""
    G._calling_agent = lambda: "synthesizer"
    out = G.update_goal("add", horizon="quarterly", title="File UK taxes", due=_d(due_days),
                        kind="obligation")
    assert "being considered" in out, out
    gid = out.split()[3]
    out = G.update_goal("vet", goal_id=gid, verdict="active", size="M", priority="ahead of the bike repair")
    assert "taken on" in out, out
    G._calling_agent = lambda: ""
    return gid


def _steps_reply(n: int = 3, deadline_days: int = 30, size: str = "M", minutes: int = 30,
                 adopt: str | None = None, extra: dict | None = None) -> str:
    """A well-formed planner reply: a chain of n steps, the first startable today."""
    names = ["Download the payroll summary", "Collect bank interest figures", "Enter income online",
             "Check the calculation", "Submit and save the receipt"]
    steps = []
    for i in range(n):
        s = {"key": f"k{i}", "what": names[i], "minutes": minutes,
             "eligible_from": _d(i * 3), "due": _d(min(deadline_days - 2, i * 3 + 5)),
             "needs": [f"k{i - 1}"] if i else []}
        steps.append(s)
    if adopt:
        steps[0]["adopt"] = adopt
    if extra:
        steps[0].update(extra)
    return json.dumps({"size": size, "steps": steps, "note": "ok"})


def _run_planner() -> bool:
    started = PP.start_planning(_PERSONA)
    _join()
    return started


def _req(end_id: str) -> dict:
    return PP._load(_PERSONA)["requests"].get(end_id) or {}


def _steps_of(end_id: str) -> list[dict]:
    return [O._norm(t) for t in O._load() if t.get("part_of") == end_id]


# =============================================================================================
# R6 — goals data and the one filter
# =============================================================================================

@check("R6: a goal Synth adds is written `proposed` in code, whatever status it sends")
def _():
    _fresh("r6_add")
    G._calling_agent = lambda: "synthesizer"
    out = G.update_goal("add", horizon="quarterly", title="Learn to sail", status="active")
    assert "being considered" in out, out
    assert G.read_goals()["quarterly"][0]["status"] == "proposed"
    G._calling_agent = lambda: "goals_interviewer"
    G.update_goal("add", horizon="quarterly", title="Run a 10k")
    assert G.read_goals()["quarterly"][1]["status"] == "active"     # the Interviewer keeps its default


@check("R6: Synth cannot take on a considered goal by `update` — only `vet` records a verdict")
def _():
    _fresh("r6_update")
    G._calling_agent = lambda: "synthesizer"
    gid = G.update_goal("add", horizon="quarterly", title="Learn to sail").split()[3]
    out = G.update_goal("update", goal_id=gid, status="active")
    assert out.startswith("Error") and "vet" in out, out
    assert _goal(gid)["status"] == "proposed"


@check("R3: vetting depth by size — M needs a date and a ranking, L stays considered, parked needs a date")
def _():
    _fresh("r3_depth")
    G._calling_agent = lambda: "synthesizer"
    gid = G.update_goal("add", horizon="quarterly", title="Renew the passport").split()[3]
    assert G.update_goal("vet", goal_id=gid, verdict="active").startswith("Error")         # no size
    assert "set `due`" in G.update_goal("vet", goal_id=gid, verdict="active", size="M")
    G.update_goal("update", goal_id=gid, due=_d(20))
    assert "priority" in G.update_goal("vet", goal_id=gid, verdict="active", size="M")
    assert "taken on" in G.update_goal("vet", goal_id=gid, verdict="active", size="M", priority="high")
    g = _goal(gid)
    assert g["status"] == "active" and g["vetted"]["depth"] == "M" and g["vetted"]["by"] == "synthesizer"
    lid = G.update_goal("add", horizon="long", title="Speak Bulgarian").split()[3]
    assert lid == "l1"
    out = G.update_goal("vet", goal_id=lid, verdict="active", size="L")
    assert out.startswith("Error") and "displaces" in out and _goal(lid)["status"] == "proposed", out
    assert "revisit_on" in G.update_goal("vet", goal_id=lid, verdict="parked")
    assert "parked until" in G.update_goal("vet", goal_id=lid, verdict="parked", revisit_on=_d(60))


@check("R6: the long horizon is read by the goal index (links, weights and sweeps see it)")
def _():
    _fresh("r6_long", goals="long:\n- {id: l1, title: Speak Bulgarian, status: active}\nquarterly: []\n")
    assert "l1" in O._goal_index()


@check("R6: prompts see current goals as YAML, proposed under 'being considered', never parked/declined/vetted")
def _():
    d = _fresh("r6_filter")
    (d / "config" / "goals.yaml").write_text(
        "quarterly:\n"
        "- {id: q1, title: Ship the app, status: active, vetted: {date: '2026-11-21', by: x}}\n"
        "- {id: q2, title: Learn to sail, status: proposed}\n"
        "- {id: q3, title: Buy a boat, status: declined}\n"
        "- {id: q4, title: Write a book, status: parked, revisit_on: '2027-03-01'}\n"
        "weekly:\n- {id: w1, title: Gym three times}\n")
    import core.orchestrator as ORC
    text = ORC._goals_section(d / "config" / "goals.yaml")
    assert "Ship the app" in text and "Gym three times" in text
    assert "Being considered" in text and "q2: Learn to sail" in text
    cur = text.split("Being considered")[0]
    assert "Learn to sail" not in cur
    assert "Buy a boat" not in text and "Write a book" not in text and "vetted" not in text
    assert ORC.load_goals.__doc__ and "Being considered" in ORC._goals_section(d / "config" / "goals.yaml")


@check("§ 4.1: declining a goal closes its open steps with that reason")
def _():
    _fresh("decline_closes")
    gid = _vetted_taxes()
    res = O.open_plan([{"key": "a", "what": "Find the P60", "due": _d(5), "part_of": gid,
                        "flexible": True, "eligible_from": _d(0)}])
    assert res["ok"], res
    G.update_goal("vet", goal_id=gid, verdict="declined")
    t = _steps_of(gid)[0]
    assert t["status"] == "moot" and "declined" in t["evidence"], t


# =============================================================================================
# R8 — plan_project only queues; the worker's four controls
# =============================================================================================

@check("R8/§ 4.2: a proposed goal is never decomposed — plan_project refuses it, and so does open_plan")
def _():
    _fresh("proposed_refused")
    G._calling_agent = lambda: "synthesizer"
    gid = G.update_goal("add", horizon="quarterly", title="File UK taxes", due=_d(30)).split()[3]
    out = PP.plan_project(gid, size="M")
    assert out.startswith("error") and "taken on" in out, out
    res = O.open_plan([{"what": "Find the P60", "due": _d(3), "part_of": gid}])
    assert not res["ok"] and "proposed" in res["error"], res
    assert _CALLS["planner"] == 0 and not _req(gid)


@check("R8: plan_project only queues — no model call in the user's turn; S and L are refused")
def _():
    _fresh("queue_only")
    gid = _vetted_taxes()
    out = PP.plan_project(gid, size="M")
    assert out.startswith("Queued"), out
    assert _CALLS["planner"] == 0 and _req(gid)["status"] == "queued"
    assert "already being planned" in PP.plan_project(gid)
    assert "one task" in PP.plan_project(gid, size="S") or "already" in PP.plan_project(gid, size="S")
    G._calling_agent = lambda: "synthesizer"
    tid = O.open_task("Book a table at Dishoom", due=_d(2))
    assert tid.startswith("task "), tid
    assert "one task" in PP.plan_project(tid.split()[1], size="S")
    assert "not yet" in PP.plan_project(tid.split()[1], size="L")


@check("R8: flag off — plan_project refuses and the tick plans nothing")
def _():
    _fresh("flag_off", flags={"project_planner": False})
    gid = _vetted_taxes()
    assert PP.plan_project(gid).startswith("error")
    assert not PP.start_planning(_PERSONA) and _CALLS["planner"] == 0


@check("R4/R8: the worker writes flexible, dated, part_of steps; only the first is on Today")
def _():
    _fresh("plan_written")
    gid = _vetted_taxes()
    PP.plan_project(gid, note="already files online")
    _REPLIES.append(_steps_reply(3))
    assert _run_planner()
    r = _req(gid)
    assert r["status"] == "planned", r
    steps = _steps_of(gid)
    assert len(steps) == 3
    for s in steps:
        assert s["flexible"] and s["due"] and s["eligible_from"] and s["goal_id"] == gid, s
        assert s["minutes"] == 30 and s["minutes_source"] == "estimated"
    p = _PAYLOADS[0]
    assert p["end_state"]["deadline"] == _d(30) and p["note"] == "already files online"
    assert p["playbook"] and "Self Assessment" in p["playbook"], "the taxes playbook was not matched"
    assert "private_why" not in json.dumps(p)
    D.refresh_tick()
    on_today = {i["task_id"] for i in O.today_items()}
    first = next(s for s in steps if not s.get("needs"))
    assert first["id"] in on_today, (on_today, first)
    assert not (on_today & {s["id"] for s in steps if s.get("needs")}), "a later step is visible"
    assert _CALLS["day_model"] == 0


@check("R8: single flight — a fresh in-flight plan stops a second start; a stale one is retried")
def _():
    _fresh("single_flight")
    gid = _vetted_taxes()
    PP.plan_project(gid)
    with D._locked(_PERSONA):
        st = PP._load(_PERSONA)
        st["requests"][gid].update(status="inflight", started_at=_CLOCK["now"].isoformat(), gen=1)
        PP._save(st, _PERSONA)
    assert not PP.start_planning(_PERSONA)
    _CLOCK["now"] += timedelta(minutes=10)                     # past the stale window
    _REPLIES.append(_steps_reply(2))
    assert _run_planner() and _req(gid)["status"] == "planned"


@check("R8: the daily cap (6) and the minimum gap hold a request queued, with no call")
def _():
    _fresh("cap_gap")
    gid = _vetted_taxes()
    PP.plan_project(gid)
    with D._locked(_PERSONA):
        st = PP._load(_PERSONA)
        st["counters"][TODAY.isoformat()] = 6
        PP._save(st, _PERSONA)
    assert not PP.start_planning(_PERSONA) and _req(gid)["status"] == "queued"
    with D._locked(_PERSONA):
        st = PP._load(_PERSONA)
        st["counters"] = {}
        st["last_model_at"] = (_CLOCK["now"] - timedelta(minutes=5)).isoformat()
        PP._save(st, _PERSONA)
    assert not PP.start_planning(_PERSONA) and _CALLS["planner"] == 0
    _CLOCK["now"] += timedelta(minutes=6)
    _REPLIES.append(_steps_reply(2))
    assert _run_planner()
    assert PP._load(_PERSONA)["counters"][TODAY.isoformat()] == 1


@check("§ 4.3: the validator refuses oversized, undated and past-deadline steps — one re-ask, then 'needs a plan', nothing written")
def _():
    _fresh("validator")
    gid = _vetted_taxes(due_days=20)
    PP.plan_project(gid)
    bad1 = _steps_reply(2, minutes=150)                                         # oversized
    bad2 = json.dumps({"size": "M", "steps": [
        {"key": "a", "what": "Gather documents", "minutes": 30, "eligible_from": _d(0)},  # undated
        {"key": "b", "what": "Submit", "minutes": 20, "eligible_from": _d(1), "due": _d(40),
         "needs": ["a"]}]})                                                     # past the deadline
    _REPLIES.extend([bad1, bad2])
    assert _run_planner()
    r = _req(gid)
    assert r["status"] == "needs_plan", r
    assert _CALLS["planner"] == 2 and "previous_errors" in _PAYLOADS[1]
    assert any("minutes" in e for e in _PAYLOADS[1]["previous_errors"])
    assert not _steps_of(gid), "a refused plan wrote steps"
    assert PP._load(_PERSONA)["counters"][TODAY.isoformat()] == 1     # the retry is not a second slot
    n = PP.notices(_PERSONA)
    assert n and n[0]["status"] == "needs_plan"


@check("R3: a planner estimate one size larger sends it back for vetting and writes nothing")
def _():
    _fresh("size_up")
    gid = _vetted_taxes()
    PP.plan_project(gid)
    _REPLIES.append(_steps_reply(3, size="L"))
    assert _run_planner()
    r = _req(gid)
    assert r["status"] == "resize" and r["planner_size"] == "L", r
    assert not _steps_of(gid) and _CALLS["planner"] == 1
    lines = PP.render(PP.notices(_PERSONA))
    assert lines and "update_goal" in lines[0]


@check("R7c/R8: a refused plan is all-or-nothing — a duplicate pair aborts it and the store is unchanged")
def _():
    _fresh("all_or_nothing")
    gid = _vetted_taxes()
    before = len(O._load())
    res = O.open_plan([
        {"key": "a", "what": "Find the P60 from payroll", "due": _d(3), "part_of": gid},
        {"key": "b", "what": "Find the P60 from payroll", "due": _d(4), "part_of": gid}])
    assert not res["ok"] and len(O._load()) == before
    PP.plan_project(gid)
    dup = json.dumps({"size": "M", "steps": [
        {"key": "a", "what": "Download the P60", "minutes": 20, "eligible_from": _d(0), "due": _d(4)},
        {"key": "b", "what": "Download the P60", "minutes": 20, "eligible_from": _d(1), "due": _d(5)}]})
    _REPLIES.append(dup)
    assert _run_planner()
    assert _req(gid)["status"] == "needs_plan" and not _steps_of(gid)


@check("§ 11: open tax tasks are ADOPTED into the plan — part_of and needs on the existing id, no twin")
def _():
    _fresh("adopt")
    gid = _vetted_taxes()
    tid = O.open_task("Download the P60 for the tax return", due=_d(10)).split()[1]
    other = O.open_task("Repot the basement plants", due=_d(3)).split()[1]
    PP.plan_project(gid)
    _REPLIES.append(lambda p: _steps_reply(3, adopt=tid))
    assert _run_planner()
    offered = {t["id"] for t in _PAYLOADS[0]["open_tasks"]}
    assert tid in offered and other not in offered, offered
    t = next(O._norm(x) for x in O._load() if x["id"] == tid)
    assert t["part_of"] == gid and t["flexible"] and t["eligible_from"] and t["goal_id"] == gid, t
    assert any(h.get("event") == "adopted_into_plan" for h in t.get("history") or [])
    assert len(_steps_of(gid)) == 3                    # two new + the adopted one
    assert not any(x["what"] == "Download the payroll summary" for x in O._load())


@check("§ 11: an obligation's end-state task is adopted as the end — it waits on the last step and keeps its stakes")
def _():
    _fresh("task_end")
    G._calling_agent = lambda: "synthesizer"
    tid = O.open_task("File the 2025-26 tax return", due=_d(30)).split()[1]
    O.update_task(tid, "set_stakes", stakes="vital", stakes_source="stated")
    G._calling_agent = lambda: ""
    assert PP.plan_project(tid, size="M").startswith("Queued")
    _REPLIES.append(_steps_reply(2))
    assert _run_planner() and _req(tid)["status"] == "planned", _req(tid)
    end = next(O._norm(x) for x in O._load() if x["id"] == tid)
    assert end.get("_blocked") and end["stakes"] == "vital", end
    assert len(end["needs"]) == 1


@check("§ 4.3 sweep: a verified goal with no plan is queued once; proposed and already-planned are not")
def _():
    _fresh("sweep")
    gid = _vetted_taxes()
    G._calling_agent = lambda: "synthesizer"
    pid = G.update_goal("add", horizon="quarterly", title="Sell the car", due=_d(40)).split()[3]
    assert PP.sweep_unplanned(_PERSONA) == 1
    assert _req(gid)["status"] == "queued" and not _req(pid)
    assert PP.sweep_unplanned(_PERSONA) == 0                     # once per goal
    gaps = {g["id"] for g in D.allocation_gaps()}
    assert gid not in gaps, "an M goal was raised as needing weekly time"


@check("R8: 'it's planned' is said once — stamped only when a reply names it with plan words")
def _():
    _fresh("said_once")
    gid = _vetted_taxes()
    PP.plan_project(gid)
    _REPLIES.append(_steps_reply(2))
    _run_planner()
    n = PP.notices(_PERSONA)
    assert len(n) == 1 and n[0]["first"] == "Download the payroll summary", n
    PP.mark_offered([gid], _PERSONA)
    assert PP.note_said("Morning! Nice weather today.", _PERSONA) == 0
    assert PP.note_said("Your taxes are planned — the first step is on your list.", _PERSONA) == 1
    assert not PP.notices(_PERSONA)


@check("G4: read_plan gives the whole map on request; list_tasks hides the waiting steps")
def _():
    _fresh("read_plan")
    gid = _vetted_taxes()
    PP.plan_project(gid)
    _REPLIES.append(_steps_reply(3))
    _run_planner()
    full = PP.read_plan(gid)
    assert full.count("\n- ") == 3 and "waits on an earlier step" in full, full
    listed = O.list_tasks()
    assert "Enter income online" not in listed


# =============================================================================================
# Mike's skip ruling (2026-11-21) — a skip may be an accident; a later step done implies the earlier
# =============================================================================================

def _two() -> tuple[str, str]:
    res = O.open_plan([
        {"key": "a", "what": "Find the old passport", "minutes": 15, "part_of": "b", "due": _d(0)},
        {"key": "b", "what": "Post the renewal form", "needs": ["a"], "minutes": 20, "due": _d(1)}])
    assert res["ok"], res
    return res["ids"]["a"], res["ids"]["b"]


@check("Skip ruling: the later step done after its prerequisite was skipped counts both done, and nothing is asked")
def _():
    _fresh("implied_after_skip")
    a, b = _two()
    O.update_task(a, "dismissed", evidence="tapped skip")
    assert next(O._norm(t) for t in O._load() if t["id"] == b)["status"] == "moot"
    assert O.cascades_to_raise()
    out = O.update_task(b, "done", evidence="I posted the renewal form yesterday")
    assert "counted done too" in out, out
    by = {t["id"]: O._norm(t) for t in O._load()}
    assert by[b]["status"] == "done" and by[a]["status"] == "done", by
    assert by[a]["evidence"].startswith("done by implication")
    assert not O.cascades_to_raise(), "the skip question is still raised"


@check("Skip ruling: a hidden later step reported done closes its open prerequisite done; an optional one goes moot")
def _():
    _fresh("implied_open")
    res = O.open_plan([
        {"key": "a", "what": "Find the old passport", "minutes": 15, "part_of": "c", "due": _d(0)},
        {"key": "o", "what": "Photocopy it", "minutes": 5, "part_of": "c", "due": _d(0),
         "required": False},
        {"key": "c", "what": "Post the renewal form", "needs": ["a", "o"], "due": _d(1)}])
    ids = res["ids"]
    O.update_task(ids["c"], "done", evidence="posted it already")
    by = {t["id"]: O._norm(t) for t in O._load()}
    assert by[ids["a"]]["status"] == "done" and by[ids["o"]]["status"] == "moot", by


@check("Skip ruling: the question at the brief asks whether the skip was on purpose")
def _():
    _fresh("intent_question")
    a, b = _two()
    O.update_task(a, "dismissed", evidence="tapped skip")
    D.refresh_tick()
    plan = json.loads(D._plan_path(TODAY).read_text())
    text = D.render_block(plan, kind="morning_brief", cascades=O.cascades_to_raise(), shown={})
    assert "on purpose" in text and f"record `{a}` done" in text and f"`{b}`" in text, text


# =============================================================================================
# The 2026-11-21 gap — a precursor stated in chat follows its event; a later finding adopts it
# =============================================================================================

def _boots(start_day: int = 1, hm: str = "14:00") -> None:
    d = TODAY + timedelta(days=start_day)
    _EVENTS["v"] = [_ev("u-boots", "Passport photo — Boots", f"{d}T{hm}:00", f"{d}T14:30:00",
                        "Boots, High Street")]


@check("Chat prep: 'bring my old passport to tomorrow's appointment' is linked to the event and follows it")
def _():
    _fresh("chat_link")
    _boots(1)
    D.refresh_snapshot(_PERSONA)
    out = O.open_task("Bring my old passport to tomorrow's appointment", due=_d(1))
    assert "linked to Passport photo" in out, out
    tid = out.split()[1]
    t = next(O._norm(x) for x in O._load() if x["id"] == tid)
    assert t["prep_for"]["uid"] == "u-boots" and t["prep_for"].get("chat") and t["due"] == _d(0), t
    _boots(3)                                                   # the appointment moves
    D.refresh_snapshot(_PERSONA)
    D._prep_follow(_PERSONA, D._load_state(_PERSONA), [O._norm(x) for x in O._load()], TODAY)
    t = next(O._norm(x) for x in O._load() if x["id"] == tid)
    assert t["due"] == _d(2) and t["moot_after"] == _d(3), t


@check("Chat prep: a task not about any event is not linked; a kind-of-event word alone does not link")
def _():
    _fresh("chat_nolink")
    _boots(1)
    _EVENTS["v"].append(_ev("u-dent", "Dentist appointment", f"{_d(1)}T09:00:00", f"{_d(1)}T09:30:00"))
    D.refresh_snapshot(_PERSONA)
    assert "linked" not in O.open_task("Buy milk", due=_d(1))
    assert "linked" not in O.open_task("Leave early for the appointment", due=_d(1))


@check("Chat prep: a finding about the same event adopts the chat task instead of opening a twin")
def _():
    _fresh("chat_adopt")
    _boots(1)
    D.refresh_snapshot(_PERSONA)
    tid = O.open_task("Bring my old passport to tomorrow's appointment", due=_d(1)).split()[1]
    H.record([{"title": "Passport photo appointment", "date": _d(1), "venue": "Boots",
               "kind": "appointment", "detail": "",
               "precursor": "bring your old passport and the signed form", "precursor_by": ""}])
    D._prep_sweep(_PERSONA, D._load_state(_PERSONA))
    preps = [t for t in O._load() if (t.get("prep_for") or {}).get("uid") == "u-boots"
             and t.get("status") == "open"]
    assert len(preps) == 1 and preps[0]["id"] == tid, preps
    assert "signed form" in (preps[0].get("note") or ""), preps[0]
    row = next(r for r in H.rows(_PERSONA).values())
    assert row.get("prep_task_id") == tid


@check("Live 11-21: 'dismiss the prep task' names the prep beside a near-identical step; a refusal never explains itself")
def _():
    _fresh("gate_prep")
    _boots(1)
    D.refresh_snapshot(_PERSONA)
    prep = O.open_task("Prepare old passport for the Boots passport photo", due=_d(1)).split()[1]
    assert (next(O._norm(t) for t in O._load() if t["id"] == prep).get("prep_for") or {}).get("uid")
    res = O.open_plan([{"key": "a", "what": "TEST B step 1 - find the old passport", "part_of": "b",
                        "due": _d(1)}, {"key": "b", "what": "TEST B step 2 - post it",
                                        "needs": ["a"], "due": _d(2)}])
    step = res["ids"]["a"]                      # a plan step, as live — never linked to the event
    from tools import turn_context as T
    cm = T.turn_scope(user_turn=True)
    turn = cm.__enter__()
    turn.update(close_gate=True, user_text="dismiss the prep task", prev_assistant="")
    try:
        r = O.update_task(step, "dismissed", evidence="dismiss the prep task")
        assert r.startswith("error: not recorded") and "Never tell them why" in r, r
        r = O.update_task(prep, "dismissed", evidence="dismiss the prep task")
        assert not r.startswith("error"), r
    finally:
        cm.__exit__(None, None, None)


@check("Fable #1: 'I did the skipped step after all' records it done and brings the later steps back — the end stays open")
def _():
    _fresh("f1_skipped_done")
    res = O.open_plan([
        {"key": "a", "what": "Download the P60", "part_of": "c", "due": _d(1)},
        {"key": "b", "what": "Enter the income online", "needs": ["a"], "part_of": "c", "due": _d(3)},
        {"key": "c", "what": "Submit the return", "needs": ["b"], "due": _d(5)}])
    ids = res["ids"]
    O.update_task(ids["a"], "dismissed", evidence="skip")
    out = O.update_task(ids["a"], "done", evidence="I did download the P60 after all")
    assert "are back" in out, out
    by = {t["id"]: O._norm(t) for t in O._load()}
    assert by[ids["a"]]["status"] == "done" and by[ids["b"]]["status"] == "open"
    assert by[ids["c"]]["status"] == "open" and by[ids["c"]].get("_blocked"), by[ids["c"]]
    assert not O.cascades_to_raise()


@check("Fable #2: one shared word does not link a task to an event; one word plus 'to the appointment' does")
def _():
    _fresh("f2_nolink")
    _EVENTS["v"] = [_ev("u-swim", "Manny swim", f"{_d(1)}T16:00:00", f"{_d(1)}T17:00:00", "Leisure centre")]
    D.refresh_snapshot(_PERSONA)
    out = O.open_task("Buy Manny new shoes", due=_d(1))
    assert "linked" not in out, out
    tid = out.split()[1]
    t = next(O._norm(x) for x in O._load() if x["id"] == tid)
    assert t["due"] == _d(1) and not t.get("prep_for") and not t.get("moot_after"), t
    assert "linked to Manny swim" in O.open_task("Take Manny's towel to tomorrow's session", due=_d(1))


@check("Fable #3: after a size-up, vetting it L gives it weekly time; confirming M plans it as M")
def _():
    _fresh("f3_resize")
    gid = _vetted_taxes()
    PP.plan_project(gid)
    _REPLIES.append(_steps_reply(3, size="L"))
    _run_planner()
    assert _req(gid)["status"] == "resize"
    assert "plan_project it again as M" in PP.render(PP.notices(_PERSONA))[0]
    # The user says it really is one job with a date: queued again at M, planned even if the
    # planner still estimates L.
    _CLOCK["now"] += timedelta(minutes=11)
    assert PP.plan_project(gid).startswith("Queued") and _req(gid).get("size_confirmed")
    _REPLIES.append(_steps_reply(3, size="L"))
    _run_planner()
    assert _req(gid)["status"] == "planned" and len(_steps_of(gid)) == 3, _req(gid)
    # Another goal, which the user says is ongoing: vetted L, it gets weekly time, not steps.
    G._calling_agent = lambda: "synthesizer"
    lid = G.update_goal("add", horizon="long", title="Speak Bulgarian").split()[3]
    out = G.update_goal("vet", goal_id=lid, verdict="active", size="L", displaces="two evenings of TV",
                        priority="after the taxes")
    assert "regular time" in out and _goal(lid)["status"] == "active", out
    assert _goal(lid)["vetted"]["pass"] == "short"
    assert "not yet" in PP.plan_project(lid)
    assert lid in {g["id"] for g in D.allocation_gaps()}


@check("Fable #5: what else a finding asked survives the event-day rewrite of the prep's note")
def _():
    _fresh("f5_note")
    _boots(1)
    D.refresh_snapshot(_PERSONA)
    tid = O.open_task("Bring my old passport to tomorrow's appointment", due=_d(1)).split()[1]
    H.record([{"title": "Passport photo appointment", "date": _d(1), "venue": "Boots",
               "kind": "appointment", "detail": "",
               "precursor": "bring your old passport and the signed form", "precursor_by": ""}])
    D._prep_sweep(_PERSONA, D._load_state(_PERSONA))
    _boots(2)                                                    # moved: the note is rewritten
    D.refresh_snapshot(_PERSONA)
    D._prep_follow(_PERSONA, D._load_state(_PERSONA), [O._norm(x) for x in O._load()], TODAY)
    t = next(O._norm(x) for x in O._load() if x["id"] == tid)
    assert t["due"] == _d(1) and "signed form" in t["note"], t


@check("Fable #6: a failed model call is retried after an hour, up to three times, before 'couldn't plan'")
def _():
    _fresh("f6_callfail")
    gid = _vetted_taxes()
    PP.plan_project(gid)

    def boom(p):
        raise RuntimeError("vertex 503")
    for i in range(3):
        _REPLIES.append(boom)
        assert _run_planner(), i
        r = _req(gid)
        if i < 2:
            assert r["status"] == "queued" and r["call_failures"] == i + 1, r
            assert not PP.start_planning(_PERSONA)                  # not before the hour
            _CLOCK["now"] += timedelta(minutes=61)
    assert _req(gid)["status"] == "needs_plan" and _CALLS["planner"] == 3
    assert not _steps_of(gid)


@check("Fable #7: 'it's planned' said without the title's words counts when it is the only notice; repeats stop after three offers")
def _():
    _fresh("f7_said")
    gid = _vetted_taxes()
    PP.plan_project(gid)
    _REPLIES.append(_steps_reply(2))
    _run_planner()
    PP.mark_offered([gid], _PERSONA)
    assert PP.note_said("That's all set up — the first piece will come to you.", _PERSONA) == 1
    _fresh("f7_cap")
    gid = _vetted_taxes()
    PP.plan_project(gid)
    _REPLIES.append(_steps_reply(2))
    _run_planner()
    for _i in range(4):
        PP.mark_offered([gid], _PERSONA)
    assert not PP.notices(_PERSONA), "a notice was offered a fourth time"


@check("Fable #8: an adopted task whose own date falls before its window takes the plan's date")
def _():
    _fresh("f8_adopt_due")
    gid = _vetted_taxes()
    tid = O.open_task("Collect bank interest figures for the tax return", due=_d(2)).split()[1]
    PP.plan_project(gid)

    def reply(p):
        return json.dumps({"size": "M", "steps": [
            {"key": "a", "what": "Download the payroll summary", "minutes": 20,
             "eligible_from": _d(0), "due": _d(4)},
            {"key": "b", "what": "x", "adopt": tid, "minutes": 30, "eligible_from": _d(5),
             "due": _d(9), "needs": ["a"]}]})
    _REPLIES.append(reply)
    _run_planner()
    t = next(O._norm(x) for x in O._load() if x["id"] == tid)
    assert t["due"] == _d(9) and t["eligible_from"] == _d(5), t
    assert any(h.get("reason") == "fitted into its plan" for h in t.get("history") or [])


@check("Fable #9: a worker superseded while it ran writes nothing")
def _():
    _fresh("f9_gen")
    gid = _vetted_taxes()
    PP.plan_project(gid)

    def reply(p):
        with D._locked(_PERSONA):                              # a restart took over meanwhile
            st = PP._load(_PERSONA)
            st["requests"][gid]["gen"] = 99
            PP._save(st, _PERSONA)
        return _steps_reply(2)
    _REPLIES.append(reply)
    _run_planner()
    assert not _steps_of(gid)


@check("Fable #10: the UK tax playbook is not attached to car tax or council tax")
def _():
    _fresh("f10_playbook")
    assert PP._playbook("File UK taxes by Dec 31")
    assert PP._playbook("Self Assessment return for 2025-26")
    assert PP._playbook("Renew the car tax") is None
    assert PP._playbook("Sort out the council tax direct debit") is None


def main() -> int:
    for name, ok, why in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if not ok:
            for line in why.rstrip().splitlines():
                print(f"        {line}")
    failed = sum(1 for _, ok, _ in _results if not ok)
    print(f"\n{len(_results) - failed} passed, {failed} failed, {len(_results)} total")
    if _CALLS["send"]:
        print(f"  (push stub absorbed {_CALLS['send']} send(s))")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
