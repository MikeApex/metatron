"""
tests/test_goal_network_phase3.py — the goal–task network, phase 3 part A: a large goal planned one
milestone at a time, a planned goal's likely finish watched, and a goal asked about again when its
steps keep slipping or it reaches a checkpoint.

Plan: archive/plans/goal_task_network_plan_2026-11-18.md — § 4.2 (re-vet triggers 1–2), § 4.3
(rolling wave), § 4.5 (projected finish), § 10 (governs), § 17 (this build, Mike's rulings
2026-11-24: an L goal is planned only after the Goals Interviewer's full pass; the re-vet lands in
the weekly look back, one goal a week; the look back's question cap is 5).

EVERY LIVE METER IS STUBBED (the standing rule): CalDAV (`_query_events`, `_get_event_by_uid`),
Google Routes, the day_planner model (refusing), the project_planner model (`_MODEL_CALL`, a
counting stub), push (`core.remote_client.send_one`), the Accountability Index's stored verdicts.
No persona data — a temp directory per check.

    .venv/bin/python tests/test_goal_network_phase3.py
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
import tools.accountability as ACC  # noqa: E402
import tools.ambient as A  # noqa: E402
import tools.caldav as CAL  # noqa: E402
import tools.day_plan as D  # noqa: E402
import tools.day_plan_config as C  # noqa: E402
import tools.day_shape as DS  # noqa: E402
import tools.goal_network as GN  # noqa: E402
import tools.goals as G  # noqa: E402
import tools.horizon as H  # noqa: E402
import tools.location as L  # noqa: E402
import tools.obligations as O  # noqa: E402
import tools.project_plan as PP  # noqa: E402
import tools.ranking as RK  # noqa: E402
import tools.ranking_review as RR  # noqa: E402
import tools.routing as R  # noqa: E402

_results: list[tuple[str, bool, str]] = []
_TMP = Path(tempfile.mkdtemp(prefix="goal_network_p3_"))
TODAY = date.today()
_CLOCK = {"now": datetime.combine(TODAY, time(7, 0))}
O._now = lambda: _CLOCK["now"]
A._get_timezone = lambda: "Europe/London"
_PERSONA = "gn_phase3"

_SHAPE = 'day: [{days: all, wake: "07:00", bed: "23:00"}]\ntravel_mode: transit\n'
_CALLS = {"day_model": 0, "planner": 0, "send": 0}
_VERDICTS: dict = {"v": {}}

CAL._query_events = lambda start, end, persona=None, calendars="own": {"events": [], "discovery": "ok"}
CAL._get_event_by_uid = lambda uid, persona=None: {"error": "Failed to fetch event: offline"}
R.get_travel_time = lambda *a, **k: {"journeys": [{"duration_minutes": 20}]}
L.load_zones = lambda persona=None: []
L.current_zone = lambda persona=None: {}
INTV.holds_proactive = lambda persona: False
D._quiet_now = lambda persona: False
D._idle_minutes = lambda persona: None
ACC.read_gate_verdicts = lambda persona, **k: _VERDICTS["v"]


def _no_day_model(*a, **k):
    _CALLS["day_model"] += 1
    raise AssertionError("a day_planner model call was made")


D._call_model = _no_day_model


def _send_one(persona, text, nudge=False, **k):
    _CALLS["send"] += 1
    return "ok"


RC.send_one = _send_one

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

# Phase 2 as deployed, plus whatever a check turns on. The three new flags are off unless named.
_FLAGS = {"build": True, "show_in_app": True, "ledger_fields": True, "synth_reads_plan": True,
          "unconfirmed_rule": True, "reshuffle_model": False, "nudges": False,
          "owns_checkins": False, "prep_tasks": True, "horizon_cap": True, "project_planner": True}
_ALL3 = {"rolling_wave": True, "projected_finish": True, "revet": True}


def _d(n: int) -> str:
    return (TODAY + timedelta(days=n)).isoformat()


def _join() -> None:
    for th in threading.enumerate():
        if th.name.startswith("day_plan_"):
            th.join(10)


def _fresh(name: str, flags: dict | None = None, goals: str = "quarterly: []\n",
           limits: dict | None = None) -> Path:
    _join()
    d = _TMP / name
    (d / "config").mkdir(parents=True, exist_ok=True)
    for mod in (O, D, DS, L, H, RR):
        mod.persona_data_dir = lambda persona=None, _d=d: _d
    DS.persona_config_dir = lambda persona=None, _d=d: _d / "config"
    (d / "config" / "goals.yaml").write_text(goals)
    G._goals_path = lambda _d=d: _d / "config" / "goals.yaml"
    G._calling_agent = lambda: ""
    (d / "day_shape.yaml").write_text(_SHAPE)
    C._OVERRIDE = {"flags": {**_FLAGS, **(flags or {})}, **({"limits": limits} if limits else {})}
    RK._OVERRIDE = {}
    _REPLIES.clear()
    _PAYLOADS.clear()
    _VERDICTS["v"] = {}
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


def _later(minutes: int) -> None:
    _CLOCK["now"] = _CLOCK["now"] + timedelta(minutes=minutes)


def _run_planner() -> bool:
    started = PP.start_planning(_PERSONA)
    _join()
    return started


def _req(end_id: str) -> dict:
    return PP._load(_PERSONA)["requests"].get(end_id) or {}


def _rows(end_id: str) -> list[dict]:
    return [O._norm(t) for t in O._load() if t.get("part_of") == end_id]


def _signals() -> list[dict]:
    return [r for r in RR.read_signals(_PERSONA) if r.get("source") == "goal_network"]


# A large goal the Goals Interviewer has talked through in full (what part B will write).
_L_GOAL = ("long:\n- id: l1\n  title: Speak Bulgarian at a conversational level\n  status: active\n"
           "  size: L\n  weekly_minutes: 180\n  vetted: {{date: '{v}', depth: L, pass: {p}, "
           "priority: high, displaces: evening TV}}\nquarterly: []\n")


def _l_goal(pass_: str = "full", vetted_days_ago: int = 0) -> str:
    return _L_GOAL.format(v=_d(-vetted_days_ago), p=pass_)


def _first_wave() -> str:
    """Three milestones (the first broken into three steps) — what the planner returns for L."""
    ms = [{"key": "m1", "what": "Order a coffee and introduce yourself", "minutes": 600,
           "eligible_from": _d(0), "due": _d(28)},
          {"key": "m2", "what": "Hold a ten-minute conversation about your day", "minutes": 900,
           "eligible_from": _d(28), "due": _d(70)},
          {"key": "m3", "what": "Follow a short news item and talk about it", "minutes": 900,
           "eligible_from": _d(70), "due": _d(140)}]
    steps = [{"key": "a", "what": "Book a first lesson with a tutor", "minutes": 20,
              "eligible_from": _d(0), "due": _d(5), "needs": []},
             {"key": "b", "what": "Learn the phrases for ordering at a cafe", "minutes": 45,
              "eligible_from": _d(1), "due": _d(14), "needs": ["a"]},
             {"key": "c", "what": "Order a coffee in Bulgarian with your tutor", "minutes": 30,
              "eligible_from": _d(7), "due": _d(26), "needs": ["b"]}]
    return json.dumps({"size": "L", "milestones": ms, "steps": steps, "note": "ok"})


def _expansion(payload: dict) -> str:
    """Two steps inside whatever window the payload gives the milestone."""
    w = payload["wave"]["milestone"]
    return json.dumps({"size": "L", "steps": [
        {"key": "x", "what": "Write ten sentences about your day", "minutes": 40,
         "eligible_from": w["eligible_from"], "due": w["due"], "needs": []},
        {"key": "y", "what": "Talk through your day with your tutor", "minutes": 30,
         "eligible_from": w["eligible_from"], "due": w["due"], "needs": ["x"]}], "note": "ok"})


def _planned_l(name: str, flags: dict | None = None, limits: dict | None = None) -> Path:
    d = _fresh(name, {**_ALL3, **(flags or {})}, goals=_l_goal(), limits=limits)
    out = PP.plan_project("l1", size="L")
    assert out.startswith("Queued"), out
    _REPLIES.append(_first_wave())
    assert _run_planner()
    assert _req("l1")["status"] == "planned", _req("l1")
    return d


# =============================================================================================
# Rolling wave (§ 4.3, § 17)
# =============================================================================================

@check("rolling wave: only the next milestone's steps exist as rows; later milestones are outlines "
       "on the plan record — never on the task list, never placed; the whole map still shows them")
def _():
    _planned_l("wave_rows")
    rows = _rows("l1")
    assert len(rows) == 3 and {r["what"] for r in rows} >= {"Book a first lesson with a tutor"}, rows
    assert all(r["goal_id"] == "l1" and r["flexible"] for r in rows)
    assert not any("conversation about your day" in str(t.get("what")) for t in O._load())
    ms = _req("l1")["milestones"]
    assert [m["status"] for m in ms] == ["current", "pending", "pending"], ms
    assert _PAYLOADS[0]["wave"]["mode"] == "first" and _PAYLOADS[0]["weekly_minutes"] == 180
    D.refresh_tick()
    plan = json.loads(D._plan_path(TODAY).read_text())
    placed = {b.get("task_id") for b in plan.get("blocks") or [] if b.get("task_id")}
    assert placed <= {t["id"] for t in O._load()}, "only real rows are ever placed"
    m = PP.read_plan("l1")
    assert "later: Hold a ten-minute conversation" in m and "an outline" in m, m


@check("rolling wave: an L goal is planned only after the Interviewer's FULL pass (Mike 11-24); "
       "the short pass is refused, and so is an L goal with no weekly time")
def _():
    _fresh("wave_short", _ALL3, goals=_l_goal(pass_="short"))
    out = PP.plan_project("l1", size="L")
    assert "talked through properly" in out and "Nothing was queued" in out, out
    assert not _req("l1") and _CALLS["planner"] == 0
    _fresh("wave_noweekly", _ALL3, goals=_l_goal().replace("  weekly_minutes: 180\n", ""))
    out = PP.plan_project("l1", size="L")
    assert out.startswith("error") and "weekly_minutes" in out, out
    assert PP.plan_project("l1", size="L", weekly_minutes=120).startswith("Queued")


@check("rolling wave: the full-pass marker is written only when the Goals Interviewer vets, and a "
       "later re-vet that keeps the goal never lowers it")
def _():
    _fresh("wave_marker", _ALL3, goals="long:\n- {id: l1, title: Run a marathon, status: proposed}\n")
    G._calling_agent = lambda: "synthesizer"
    assert "taken on" in G.update_goal("vet", goal_id="l1", verdict="active", size="L",
                                       priority="normal", displaces="Saturday lie-ins")
    assert _goal("l1")["vetted"]["pass"] == "short"
    G._calling_agent = lambda: "goals_interviewer"
    G.update_goal("vet", goal_id="l1", verdict="active", size="L", priority="high", displaces="x")
    assert _goal("l1")["vetted"]["pass"] == "full"
    G._calling_agent = lambda: "synthesizer"
    G.update_goal("vet", goal_id="l1", verdict="active", size="L", priority="high", displaces="x")
    assert _goal("l1")["vetted"]["pass"] == "full", _goal("l1")


@check("rolling wave: closing the last step of a milestone queues ONE expansion, run under the "
       "daily cap; its steps land inside the milestone's window and nobody is told")
def _():
    _planned_l("wave_expand", limits={"project_plans_per_day": 2})
    ids = _req("l1")["ids"]
    for tid in ids[:2]:
        assert PP.advance_waves(_PERSONA) == 0           # steps still open: nothing moves
        O.update_task(tid, "done", evidence="did it")
    assert PP.advance_waves(_PERSONA) == 0
    O.update_task(ids[2], "done", evidence="ordered the coffee")
    assert PP.advance_waves(_PERSONA) == 1
    assert PP.advance_waves(_PERSONA) == 0, "queued once, not once per tick"
    r = _req("l1")
    assert r["status"] == "queued" and r["expand"] == "m2"
    assert [m["status"] for m in r["milestones"]] == ["done", "pending", "pending"]
    _later(15)                                           # past the planner's minimum gap
    _REPLIES.append(_expansion)
    assert _run_planner()
    p = _PAYLOADS[-1]["wave"]
    assert p["mode"] == "expand" and p["milestone"]["due"] == _d(70) and p["done"] and p["later"]
    r = _req("l1")
    assert r["status"] == "planned" and r["said"] == "silent" and len(r["waves"]) == 2, r
    new = [t for t in _rows("l1") if t["status"] == "open"]
    assert len(new) == 2 and all(_d(28) <= t["eligible_from"] and t["due"] <= _d(70) for t in new)
    assert not [n for n in PP.notices(_PERSONA) if n["status"] != "late"], "an expansion is silent"
    # The cap holds: m2's steps done, m3 queued, but today's two calls are spent.
    for t in sorted(new, key=lambda t: t["what"], reverse=True):
        O.update_task(t["id"], "done", evidence="done")
    assert PP.advance_waves(_PERSONA) == 1
    _later(15)
    assert not _run_planner() and _req("l1")["status"] == "queued", "the daily cap holds"


@check("rolling wave: a milestone whose steps all closed with none done is stalled — nothing more "
       "is expanded; the re-vet asks about it, and keeping the goal brings fresh steps")
def _():
    _planned_l("wave_stall", flags={"weekly_priorities": True})
    for tid in _req("l1")["ids"]:
        O.update_task(tid, "dismissed", evidence="not now")
    assert PP.advance_waves(_PERSONA) == 0
    r = _req("l1")
    assert r["milestones"][0]["status"] == "stalled" and r["status"] == "planned", r
    assert GN.revet_daily(_PERSONA, TODAY) == 1
    assert GN.revet_daily(_PERSONA, TODAY) == 0, "once per stall"
    block = RR.weekly_block(_PERSONA, "weekly_review", weekly=True)
    assert "GOAL CHECK" in block and "nothing more has been planned" in block, block
    assert RR.note_said("None of the Bulgarian steps happened lately — does it still fit, or "
                        "shall we set it aside?", _PERSONA) == 1
    G._calling_agent = lambda: "synthesizer"
    G.update_goal("vet", goal_id="l1", verdict="active", size="L", priority="high",
                  displaces="evening TV")
    r = _req("l1")
    assert r["status"] == "queued" and r["expand"] == "m1" and r["by"] == "revet", r
    assert _goal("l1")["vetted"]["pass"] == "full"


@check("rolling wave: the validator — an outline needs a window but has no 90-minute cap; steps "
       "outside the first milestone's window are refused; a first wave with no milestones is refused")
def _():
    _fresh("wave_validate", _ALL3, goals=_l_goal())
    PP.plan_project("l1", size="L")
    req = _req("l1")
    payload = PP._payload(req, _PERSONA)
    good = json.loads(_first_wave())
    size, steps, errs, ms = PP._check(json.dumps(good), req, payload)
    assert not errs and len(ms) == 3 and ms[1]["minutes"] == 900, errs
    bad = json.loads(_first_wave())
    bad["milestones"][1].pop("due")
    assert any("m2" in e and "required" in e for e in PP._check(json.dumps(bad), req, payload)[2])
    bad = json.loads(_first_wave())
    bad["steps"][2]["due"] = _d(40)                     # past m1's due (day 28)
    assert any("after the deadline" in e for e in PP._check(json.dumps(bad), req, payload)[2])
    bad = json.loads(_first_wave())
    bad.pop("milestones")
    assert any("milestones" in e for e in PP._check(json.dumps(bad), req, payload)[2])
    bad = json.loads(_first_wave())
    bad["milestones"][2]["due"] = _d(400)               # past the 365-day horizon
    assert any("m3" in e for e in PP._check(json.dumps(bad), req, payload)[2])


# =============================================================================================
# Projected finish (§ 4.5)
# =============================================================================================

_M_GOAL = ("quarterly:\n- id: q1\n  title: Renew the passport\n  status: active\n  size: M\n"
           "  due: '{due}'\n  vetted: {{date: '{v}', depth: M, priority: high}}\n")


def _m_plan(name: str, minutes: list[int], due_days: int = 14, weekly: int = 60,
            flags: dict | None = None) -> Path:
    """A planned M goal: a chain of steps with the given minutes, at `weekly` minutes a week."""
    d = _fresh(name, {**_ALL3, **(flags or {})}, goals=_M_GOAL.format(due=_d(due_days), v=_d(0)))
    assert PP.plan_project("q1", size="M", weekly_minutes=weekly).startswith("Queued")
    steps = [{"key": f"k{i}", "what": w, "minutes": m, "eligible_from": _d(0),
              "due": _d(due_days - 1), "needs": [f"k{i - 1}"] if i else []}
             for i, (w, m) in enumerate(zip(["Fill in the renewal form online", "Get two photos taken",
                                             "Post the old passport", "Book the counter check",
                                             "Collect the new passport"], minutes))]
    _REPLIES.append(json.dumps({"size": "M", "steps": steps, "note": "ok"}))
    assert _run_planner() and _req("q1")["status"] == "planned"
    return d


@check("projected finish: crossing the goal's date alerts ONCE, as Important with the new date and "
       "one fix; a second tick — the same day or the next — does not alert again")
def _():
    _m_plan("finish_cross", [90, 90, 90, 90, 90], due_days=14, weekly=60)   # 450 min at 60/week
    assert GN.finish_daily(_PERSONA, TODAY) == 1
    assert GN.finish_daily(_PERSONA, TODAY) == 0
    assert GN.finish_daily(_PERSONA, TODAY + timedelta(days=1)) == 0
    late = [n for n in PP.notices(_PERSONA) if n["status"] == "late"]
    assert len(late) == 1 and late[0]["target"] == _d(14) and late[0]["projected"] > _d(14), late
    assert "more minutes a week" in late[0]["fix"], late[0]
    D.refresh_tick()
    plan = json.loads(D._plan_path(TODAY).read_text())
    shown: dict = {}
    text = D.render_block(plan, kind="morning_brief", projects=PP.notices(_PERSONA), shown=shown)
    assert "Important — the finish date has moved" in text and "Renew the passport" in text, text
    assert "late:q1" in shown.get("projects", [])
    PP.mark_offered(shown["projects"], _PERSONA)
    assert PP.note_said("Morning! Lovely day.", _PERSONA) == 0
    assert PP.note_said("At this pace the passport renewal will finish later than the 14th — "
                        "another hour a week on it would keep the date.", _PERSONA) == 1
    assert not [n for n in PP.notices(_PERSONA) if n["status"] == "late"], "said once"
    assert GN.finish_daily(_PERSONA, TODAY + timedelta(days=2)) == 0, "still late, not slipped more"


@check("projected finish: once said, it is said again only when it slips later by more than the "
       "margin; back on time re-arms silently, and a new crossing is said")
def _():
    _m_plan("finish_rearm", [90, 90, 90, 90, 90], due_days=14, weekly=60)
    assert GN.finish_daily(_PERSONA, TODAY) == 1
    st = PP._load(_PERSONA)
    GN.mark_late_said(st["requests"]["q1"], "x")
    PP._save(st, _PERSONA)
    first = _req("q1")["finish"]["baseline"]
    extra = O.open_plan([{"key": "z", "what": "Fetch the counter-signed form", "minutes": 20,
                          "due": _d(13), "eligible_from": _d(0), "flexible": True,
                          "part_of": "q1", "goal_id": "q1"}])
    assert extra["ok"]
    assert GN.finish_daily(_PERSONA, TODAY) == 0, "20 more minutes is inside the 3-day margin"
    extra = O.open_plan([{"key": "z", "what": "Request the guarantor countersignature",
                          "minutes": 90, "due": _d(13), "eligible_from": _d(0), "flexible": True,
                          "part_of": "q1", "goal_id": "q1"}])
    assert extra["ok"], extra
    assert GN.finish_daily(_PERSONA, TODAY) == 1
    al = _req("q1")["finish"]["alert"]
    assert al["kind"] == "moved" and al["projected"] > first, al
    # Back on time: all but one step dropped (dismissed, so the pace stays the stated one — done
    # steps would replace it with the pace kept) — silent, re-armed.
    keep = "Fill in the renewal form online"
    O._with_store(_PERSONA, lambda doc: [x.update(status="dismissed", closed_at=_d(0) + "T08:00:00")
                                         for x in doc["tasks"] if x.get("part_of") == "q1"
                                         and x["status"] == "open" and x["what"] != keep])
    assert GN.finish_daily(_PERSONA, TODAY + timedelta(days=1)) == 0
    assert _req("q1")["finish"]["late"] is False
    for w in ("Redo the application photo", "Chase the embassy letter", "Scan the birth record",
              "Notarise the consent declaration", "Courier the bundle abroad"):
        res = O.open_plan([{"key": "v", "what": w, "minutes": 90, "due": _d(13),
                            "eligible_from": _d(1), "flexible": True, "part_of": "q1",
                            "goal_id": "q1"}])
        assert res["ok"], res
    assert GN.finish_daily(_PERSONA, TODAY + timedelta(days=1)) == 1
    assert _req("q1")["finish"]["alert"]["kind"] == "crossed"


@check("projected finish: an L goal with no date of its own is said only when it slips more than "
       "14 days later than the date last set")
def _():
    _planned_l("finish_l")
    assert GN.finish_daily(_PERSONA, TODAY) == 0
    base = _req("l1")["finish"]["baseline"]
    st = PP._load(_PERSONA)
    st["requests"]["l1"]["weekly_minutes"] = 150                # a little less time a week
    PP._save(st, _PERSONA)
    assert GN.finish_daily(_PERSONA, TODAY) == 0, "inside the 14-day margin"
    st = PP._load(_PERSONA)
    st["requests"]["l1"]["weekly_minutes"] = 60                 # a lot less
    PP._save(st, _PERSONA)
    assert GN.finish_daily(_PERSONA, TODAY) == 1
    n = [x for x in PP.notices(_PERSONA) if x["status"] == "late"][0]
    assert n["target"] is None and n["baseline"] == base
    assert "later than" in GN.render_late(n) and "more minutes a week" in n["fix"], n


@check("projected finish: the pace actually kept replaces the stated weekly time once two steps "
       "are done")
def _():
    _m_plan("finish_pace", [30, 30], due_days=20, weekly=120)
    assert GN.finish_daily(_PERSONA, TODAY) == 0
    f = _req("q1")["finish"]
    assert f["late"] is False and f["baseline"], f
    # The user gives it far less time than they said: the pace actually kept takes over once two
    # steps are done. Here, two tiny steps closed over three weeks.
    rows = _rows("q1")
    r = PP._load(_PERSONA)["requests"]["q1"]
    rate, src, n = GN.pace(r, rows, TODAY)
    assert src == "stated" and rate == 120
    for t in rows:
        t.update(status="done", closed_at=(TODAY - timedelta(days=1)).isoformat() + "T12:00:00")
    r["waves"] = [{"at": (TODAY - timedelta(days=21)).isoformat() + "T09:00:00"}]
    rate, src, n = GN.pace(r, rows, TODAY)
    assert src == "actual" and n == 2 and round(rate) == 20, (rate, src)


@check("projected finish: an obligation whose waiting alone runs past its date gets a date, not "
       "'more minutes a week'")
def _():
    _m_plan("finish_floor", [30, 30], due_days=14, weekly=120)

    def apply(doc):
        for t in doc["tasks"]:
            if t.get("part_of") == "q1" and t["what"].startswith("Get two"):
                t["eligible_from"] = _d(20)               # a document arrives in three weeks
                t["due"] = _d(25)
    O._with_store(_PERSONA, apply)
    assert GN.finish_daily(_PERSONA, TODAY) == 1
    al = _req("q1")["finish"]["alert"]
    assert al["fix"].startswith("moving the date to") and "waiting alone" in al["fix"], al


# =============================================================================================
# Re-vet (§ 4.2) — trigger 1 (non-compliance) and trigger 2 (time)
# =============================================================================================

_PLANTS = ("quarterly:\n- id: q1\n  title: Look after the house plants\n  status: active\n"
           "  size: M\n  vetted: {date: '2026-11-01', depth: M, priority: normal}\n")


def _plants_step() -> str:
    res = O.open_plan([{"key": "a", "what": "Repot the two basement plants", "due": _d(10),
                        "eligible_from": _d(-10), "flexible": True, "part_of": "q1",
                        "goal_id": "q1", "minutes": 30}])
    assert res["ok"], res
    return res["ids"]["a"]


def _slips(tid: str, days: int, last_ago: int = 1) -> None:
    with D._locked(_PERSONA):
        st = D._load_state(_PERSONA)
        st["slips"] = {tid: {"first": _d(-last_ago - days + 1), "days": days, "last": _d(-last_ago)}}
        D._write_json(D._state_path(_PERSONA), st)


@check("trigger 1, the worked example (§ 4.2): repotting the basement plants proposed on four "
       "mornings in a week and not done fires one re-vet; three do not; it fires once")
def _():
    _fresh("t1_plants", _ALL3, goals=_PLANTS)
    tid = _plants_step()
    _slips(tid, 3)
    assert GN.revet_daily(_PERSONA, TODAY) == 0, "three days is not four"
    _slips(tid, 4)
    assert GN.revet_daily(_PERSONA, TODAY) == 1
    f = PP._load(_PERSONA)["revet"]["q1"]["fires"][0]
    assert f["trigger"] == "noncompliance" and f["days"] == 4 and f["window"] == 7, f
    assert GN.revet_daily(_PERSONA, TODAY) == 0
    assert GN.revet_daily(_PERSONA, TODAY + timedelta(days=3)) == 0, "quiet while unanswered"


@check("trigger 1 counts 'not yet' taps (the tap log now carries the task id), dismissals and an "
       "unfulfilled matching intention — distinct days, not events")
def _():
    _fresh("t1_mixed", _ALL3, goals=_PLANTS)
    tid = _plants_step()
    D.remind_later(tid, 30, _PERSONA)
    D.remind_later(tid, 60, _PERSONA)                   # the same day twice counts once
    rows = [json.loads(x) for x in D._log_path(_PERSONA).read_text().splitlines()]
    assert any(r.get("event") == "remind_requested" and r.get("ref") == tid for r in rows)
    _slips(tid, 2, last_ago=2)                           # days -3, -2
    _VERDICTS["v"] = {"k": {"verdict": "unfulfilled", "window_end": _d(-1),
                            "intention": "repot the basement plants this week"}}
    days = GN.noncompliance(_PERSONA, "q1", _goal("q1"), [O._norm(t) for t in O._load()],
                            D._load_state(_PERSONA)["slips"], TODAY - timedelta(days=6), TODAY)
    assert days == {TODAY, TODAY - timedelta(days=1), TODAY - timedelta(days=2),
                    TODAY - timedelta(days=3)}, days
    assert GN.revet_daily(_PERSONA, TODAY) == 1


@check("trigger 2: an L goal is asked about at 2 weeks, 6 weeks, then each quarter — once each; a "
       "goal already past two checkpoints is asked only the latest")
def _():
    _fresh("t2_checks", _ALL3, goals=_l_goal(vetted_days_ago=14))
    assert GN.revet_daily(_PERSONA, TODAY) == 1
    assert GN.revet_daily(_PERSONA, TODAY + timedelta(days=1)) == 0
    assert GN.revet_daily(_PERSONA, TODAY + timedelta(days=28)) == 1          # day 42
    assert GN.revet_daily(_PERSONA, TODAY + timedelta(days=28 + 90)) == 0     # day 132
    assert GN.revet_daily(_PERSONA, TODAY + timedelta(days=28 + 91)) == 1     # day 133
    keys = [f["key"].split(":")[1] for f in PP._load(_PERSONA)["revet"]["l1"]["fires"]]
    assert keys == ["d14", "d42", "d133"], keys
    _fresh("t2_late", _ALL3, goals=_l_goal(vetted_days_ago=50))
    assert GN.revet_daily(_PERSONA, TODAY) == 1
    assert [f["key"] for f in PP._load(_PERSONA)["revet"]["l1"]["fires"]] == [f"{_d(-50)}:d42"]


@check("an obligation is never asked whether it is wanted: no trigger 2, and trigger 1 asks only "
       "about its date and what would help")
def _():
    goals = _l_goal(vetted_days_ago=14).replace("  size: L\n", "  size: L\n  kind: obligation\n")
    _fresh("t_obligation", {**_ALL3, "weekly_priorities": True}, goals=goals)
    assert GN.revet_daily(_PERSONA, TODAY) == 0, "no time checkpoint for an obligation"
    res = O.open_plan([{"key": "a", "what": "Gather the payslips", "due": _d(10), "flexible": True,
                        "eligible_from": _d(-10), "part_of": "l1", "goal_id": "l1"}])
    _slips(res["ids"]["a"], 5)
    assert GN.revet_daily(_PERSONA, TODAY) == 1
    line = GN.weekly_revet(_PERSONA, TODAY)[0][1]
    assert "never ask whether they want it" in line and "date still works" in line, line


@check("the re-vet lands in the weekly look back (Mike 11-24): one goal a week, as a question; said "
       "→ `revet_asked`, answered with update_goal vet → `revet_answer`, both in ranking_signals")
def _():
    goals = _l_goal(vetted_days_ago=14) + (
        "weekly:\n- id: w1\n  title: Swim twice a week\n  status: active\n  size: L\n"
        f"  vetted: {{date: '{_d(-14)}', depth: L, priority: normal, displaces: x}}\n")
    _fresh("t_weekly", {**_ALL3, "weekly_priorities": True, "ranking_signals": True}, goals=goals)
    assert GN.revet_daily(_PERSONA, TODAY) == 2
    block = RR.weekly_block(_PERSONA, "weekly_review", weekly=True)
    assert block.count("GOAL CHECK") == 1 and "never a verdict" in block, block
    assert ("Bulgarian" in block) != ("Swim" in block), "one goal a week"
    assert RR.note_said("Two weeks into the Bulgarian — how is it going, still worth the time?",
                        _PERSONA) == 1
    rows = _signals()
    assert [r["kind"] for r in rows] == ["revet_asked"] and rows[0]["goal_id"] == "l1", rows
    assert rows[0]["trigger"] == "time" and rows[0]["checkpoint"] == f"{_d(-14)}:d14"
    assert "Swim" not in RR.weekly_block(_PERSONA, "weekly_review", weekly=True), \
        "a second goal waits a week"
    assert GN.weekly_revet(_PERSONA, TODAY + timedelta(days=7)), "and comes the next week"
    G._calling_agent = lambda: "synthesizer"
    G.update_goal("vet", goal_id="l1", verdict="parked", revisit_on=_d(60))
    rows = _signals()
    assert rows[-1]["kind"] == "revet_answer" and rows[-1]["verdict"] == "parked", rows
    assert set(rows[-1]) >= {"at", "day", "source", "goal_id", "trigger", "asked_on"}
    assert not any(isinstance(v, str) and "Bulgarian" in v for r in rows for v in r.values()), \
        "ids and counts only, never the goal's words"


@check("the weekly cap: re-vet questions count inside `questions_max`, which ships at 5 (Mike "
       "11-24); a goal being re-vetted replaces a guarded question about one of its own tasks")
def _():
    assert RK._DEFAULTS["weekly"]["questions_max"] == 5
    _fresh("t_dedupe", {**_ALL3, "weekly_priorities": True}, goals=_PLANTS)
    tid = _plants_step()
    _slips(tid, 4)
    GN.revet_daily(_PERSONA, TODAY)
    st = RK.load_state(_PERSONA)
    st.setdefault("trace", {})[TODAY.isoformat()] = {"back_burner": {"guarded": [
        {"task_id": tid, "silent": 30, "why": "goal"}]}}
    RK.save_state(st, _PERSONA)
    C._OVERRIDE["flags"]["back_burner"] = True
    m = RR.weekly_material(_PERSONA, TODAY, RK.load_state(_PERSONA))
    kinds = [k for k, _, _ in m["slipping"]]
    assert kinds == ["revet"], m["slipping"]


@check("a goal step is never back-burner parked (ranking § 11c): it is excluded before any reading")
def _():
    _fresh("t_backburner", _ALL3, goals=_PLANTS)
    tid = _plants_step()
    t = O._norm(O._find(O._load(None), tid))
    assert RR._excluded(t, TODAY + timedelta(days=40), {tid: t}, set()) is True


# =============================================================================================
# The language playbook's attachment (§ 4.4, phase 2's F10) — the playbook itself lands later,
# with Mike (2026-11-24); a stand-in proves the matching
# =============================================================================================

@check("playbook: `applies_when` needs a word from every group — 'speaking Bulgarian' matches a "
       "language playbook with no Bulgarian file; 'public speaking' and 'Bulgarian taxes' do not")
def _():
    d = _fresh("playbook_match")
    pb = d / "playbooks"
    pb.mkdir(exist_ok=True)
    (pb / "language_learning.md").write_text(
        "# Stand-in\n\napplies_when: speak, speaking, learn, learning, fluent, conversational | "
        "bulgarian, spanish, french, japanese\n\n## Stages\n1. Method only.\n")
    saved = PP._PLAYBOOKS
    PP._PLAYBOOKS = pb
    try:
        assert PP._playbook("Become better at speaking Bulgarian")
        assert PP._playbook("Learn Spanish")
        assert PP._playbook("Practise public speaking") is None
        assert PP._playbook("Sort out the Bulgarian taxes") is None
        assert PP._playbook("Learn Python") is None
    finally:
        PP._PLAYBOOKS = saved
    assert "Self Assessment" in (PP._playbook("File UK taxes") or "")    # phase 2's still attaches


# =============================================================================================
# Each flag off restores phase 2 exactly
# =============================================================================================

@check("flags off: an L goal is refused as before, no wave moves, no finish is projected, no re-vet "
       "fires, the look back carries no goal check, and L goals are not swept")
def _():
    _fresh("off", goals=_l_goal(vetted_days_ago=14))
    out = PP.plan_project("l1", size="L")
    assert out == ("A large goal is talked through properly before it is planned — not yet. It "
                   "stays as being considered. Nothing was queued."), out
    assert PP.sweep_unplanned(_PERSONA) == 0 and not _req("l1")
    assert PP.advance_waves(_PERSONA) == 0
    assert GN.finish_daily(_PERSONA, TODAY) == 0 and GN.revet_daily(_PERSONA, TODAY) == 0
    assert "revet" not in PP._load(_PERSONA)
    C._OVERRIDE["flags"]["weekly_priorities"] = True
    assert "GOAL CHECK" not in RR.weekly_block(_PERSONA, "weekly_review", weekly=True)
    # A pending alert written while the flag was on is not shown once it is off.
    st = PP._load(_PERSONA)
    st["requests"]["x"] = {"id": "x", "status": "planned", "title": "X",
                           "finish": {"alert": {"projected": _d(9), "target": _d(5), "fix": "f"}}}
    PP._save(st, _PERSONA)
    assert not [n for n in PP.notices(_PERSONA) if n["status"] == "late"]


@check("flags on: the sweep plans a fully-vetted L goal once, and an L goal keeps its weekly time "
       "(allocation gaps) while planned")
def _():
    _fresh("sweep_l", _ALL3, goals=_l_goal())
    assert PP.sweep_unplanned(_PERSONA) == 1 and _req("l1")["size"] == "L"
    assert PP.sweep_unplanned(_PERSONA) == 0
    _REPLIES.append(_first_wave())
    assert _run_planner()
    assert any(g["id"] == "l1" for g in D.allocation_gaps(_PERSONA))


# =============================================================================================
# Fable diff review, 2026-11-24 — one check per finding (plan § 17)
# =============================================================================================

@check("review S1: an L plan whose first steps are done is never read as months behind — its pace "
       "is the weekly time given, not step minutes")
def _():
    _planned_l("rv_s1")
    assert GN.finish_daily(_PERSONA, TODAY) == 0
    for tid in _req("l1")["ids"][:2]:
        O.update_task(tid, "done", evidence="did it")
    assert GN.finish_daily(_PERSONA, TODAY + timedelta(days=1)) == 0
    last = _req("l1")["finish"]["last"]
    assert last["pace_source"] == "stated" and last["pace"] == 180, last


def _late_m(name: str, flags: dict | None = None) -> None:
    _m_plan(name, [90, 90, 90, 90, 90], due_days=14, weekly=60, flags=flags)
    assert GN.finish_daily(_PERSONA, TODAY) == 1


def _offer_late() -> None:
    PP.mark_offered(["late:q1"], _PERSONA)


@check("review S2: a finish alert is said only inside the offer window, naming the goal and "
       "carrying the date or the fix — 'we can look at the garden later' never counts")
def _():
    _late_m("rv_s2")
    _offer_late()
    _later(26 * 60)
    assert PP.note_said("Sure — we can look at the garden later.", _PERSONA) == 0
    assert PP.note_said("The passport renewal will now finish on the 20th.", _PERSONA) == 0, \
        "outside the window"
    _offer_late()
    assert PP.note_said("It'll be ready later than planned, sorry.", _PERSONA) == 0, "no name"
    for stray in ("The passport form is next — maybe tonight?",
                  "Shall we decide on the passport photos?",
                  "I'll mark the passport form as started."):       # verify pass N2
        assert PP.note_said(stray, _PERSONA) == 0, stray
    new = O._d(_req("q1")["finish"]["alert"]["projected"])
    assert PP.note_said(f"Your passport renewal is behind — it's heading for {new:%B} {new.day}.",
                        _PERSONA) == 1


@check("verify N1: an M plan with no weekly time and nothing done is said once its date passes, "
       "or a step passes its own date — with a new date as the fix, no pace claim")
def _():
    _fresh("vn1", _ALL3, goals=_M_GOAL.format(due=_d(14), v=_d(0)))
    assert PP.plan_project("q1", size="M").startswith("Queued")
    steps = [{"key": f"k{i}", "what": w, "minutes": 90, "eligible_from": _d(0), "due": _d(6 + i),
              "needs": []} for i, w in enumerate(["Fill in the renewal form online",
                                                  "Get two photos taken", "Post the old passport"])]
    _REPLIES.append(json.dumps({"size": "M", "steps": steps, "note": "ok"}))
    assert _run_planner()
    assert GN.finish_daily(_PERSONA, TODAY) == 0
    assert GN.finish_daily(_PERSONA, TODAY + timedelta(days=7)) == 1, "a step is past its date"
    al = _req("q1")["finish"]["alert"]
    assert al["fix"].startswith("setting a new date") and "a week" not in al["fix"], al
    assert GN.finish_daily(_PERSONA, TODAY + timedelta(days=20)) == 0, "said once"


@check("verify N3: planning an L goal in the minutes after its milestone's last step closed plans "
       "the NEXT milestone, never the finished one again")
def _():
    _planned_l("vn3")
    for tid in _req("l1")["ids"]:
        O.update_task(tid, "done", evidence="did it")
    out = PP.plan_project("l1", size="L")                  # before any tick has run
    assert out.startswith("Queued"), out
    r = _req("l1")
    assert r["expand"] == "m2" and r["milestones"][0]["status"] == "done", r


@check("review S3: moving the goal's date — the alert's own advice — stops the alert")
def _():
    _late_m("rv_s3")
    G._calling_agent = lambda: "synthesizer"
    G.update_goal("update", goal_id="q1", due=_d(120))
    assert GN.finish_daily(_PERSONA, TODAY + timedelta(days=1)) == 0
    f = _req("q1")["finish"]
    assert f["late"] is False and "alert" not in f and _req("q1")["deadline"] == _d(120), f
    assert not [n for n in PP.notices(_PERSONA) if n["status"] == "late"]


@check("review S4: a late plan left untouched is not re-alerted as days pass; more work is, at most "
       "twice a crossing; an implausible need becomes 'move the date'")
def _():
    _late_m("rv_s4")
    st = PP._load(_PERSONA)
    GN.mark_late_said(st["requests"]["q1"], "x")
    PP._save(st, _PERSONA)
    for n in (4, 8, 12, 20, 40):
        assert GN.finish_daily(_PERSONA, TODAY + timedelta(days=n)) == 0, f"day +{n}"
    raised = 0
    for i, w in enumerate(("Find the old certificate", "Ring the passport office",
                           "Collect the witness signature")):
        O.open_plan([{"key": "e", "what": w, "minutes": 90, "due": _d(13), "eligible_from": _d(0),
                      "flexible": True, "part_of": "q1", "goal_id": "q1"}])
        raised += GN.finish_daily(_PERSONA, TODAY + timedelta(days=41 + i))
        st = PP._load(_PERSONA)
        GN.mark_late_said(st["requests"]["q1"], "x")
        PP._save(st, _PERSONA)
    assert raised == 2, raised
    p = {"projected": _d(60), "floor": _d(1), "target": _d(14), "remaining_minutes": 5000,
         "pace": 60, "pace_source": "stated"}
    assert GN._fix(p, TODAY, None).startswith("moving the date"), "10+ hours a week is not a fix"


@check("review S5a: planning an L goal again after a stall keeps its milestone map and plans the "
       "stalled stage — never a fresh first wave")
def _():
    _planned_l("rv_s5a", limits={"project_plans_per_day": 6})
    for tid in _req("l1")["ids"]:
        O.update_task(tid, "done", evidence="did it")
    PP.advance_waves(_PERSONA)
    _later(15)
    _REPLIES.append(_expansion)
    assert _run_planner()
    for tid in _req("l1")["ids"]:
        O.update_task(tid, "dismissed", evidence="not now")
    PP.advance_waves(_PERSONA)
    assert [m["status"] for m in _req("l1")["milestones"]] == ["done", "stalled", "pending"]
    out = PP.plan_project("l1", size="L")
    assert out.startswith("Queued") and "next part" in out, out
    r = _req("l1")
    assert r["expand"] == "m2" and len(r["milestones"]) == 3 and len(r["waves"]) == 2, r


@check("review S5b: a failed expansion is tried again the next day, keeping the map; after three it "
       "is said as the next stage, not as the whole goal")
def _():
    _planned_l("rv_s5b", limits={"project_plans_per_day": 10})
    for tid in _req("l1")["ids"]:
        O.update_task(tid, "done", evidence="did it")
    PP.advance_waves(_PERSONA)
    for day in range(3):
        _CLOCK["now"] = datetime.combine(TODAY + timedelta(days=day), time(9, 0)) + timedelta(hours=1)
        _REPLIES.extend(['{"size": "L", "steps": []}', '{"size": "L", "steps": []}'])
        assert _run_planner(), day
    r = _req("l1")
    assert r["status"] == "needs_plan" and r["wave_failed"] == "m2" and r["milestones"], r
    line = PP.render(PP.notices(_PERSONA))[0]
    assert "next stage" in line and "conversation about your day" in line, line


@check("review S6: answering 'keep' at two weeks does not push the six-week check out — the clock "
       "runs from when the goal was taken on")
def _():
    goals = "long:\n- {id: l1, title: Speak Bulgarian, status: proposed}\n"
    _fresh("rv_s6", {**_ALL3, "weekly_priorities": True, "ranking_signals": True}, goals=goals)
    G._calling_agent = lambda: "synthesizer"
    G.update_goal("vet", goal_id="l1", verdict="active", size="L", priority="high", displaces="TV")
    taken = _goal("l1")["taken_on"]
    _CLOCK["now"] = datetime.combine(TODAY + timedelta(days=14), time(9, 0))
    assert GN.revet_daily(_PERSONA, TODAY + timedelta(days=14)) == 1
    RR.weekly_block(_PERSONA, "weekly_review", weekly=True)
    assert RR.note_said("How is the Bulgarian going — still worth it?", _PERSONA) == 1
    G.update_goal("vet", goal_id="l1", verdict="active", size="L", priority="high", displaces="TV")
    assert _goal("l1")["taken_on"] == taken, "a keep does not move the anchor"
    assert GN.revet_daily(_PERSONA, TODAY + timedelta(days=41)) == 0
    assert GN.revet_daily(_PERSONA, TODAY + timedelta(days=42)) == 1, "day 42 from taking it on"


@check("review L1: back on time withdraws an unsaid alert; a new crossing is shown afresh even after "
       "an earlier one went unsaid three times")
def _():
    _late_m("rv_l1")
    for _ in range(3):
        _offer_late()
    assert not [n for n in PP.notices(_PERSONA) if n["status"] == "late"], "let go after 3"
    keep = "Fill in the renewal form online"
    O._with_store(_PERSONA, lambda doc: [x.update(status="dismissed", closed_at=_d(0) + "T08:00:00")
                                         for x in doc["tasks"] if x.get("part_of") == "q1"
                                         and x["status"] == "open" and x["what"] != keep])
    assert GN.finish_daily(_PERSONA, TODAY + timedelta(days=1)) == 0
    assert "alert" not in _req("q1")["finish"]
    for w in ("Redo the application photo", "Chase the embassy letter", "Scan the birth record",
              "Notarise the consent declaration", "Courier the bundle abroad"):
        O.open_plan([{"key": "v", "what": w, "minutes": 90, "due": _d(13), "eligible_from": _d(1),
                      "flexible": True, "part_of": "q1", "goal_id": "q1"}])
    assert GN.finish_daily(_PERSONA, TODAY + timedelta(days=2)) == 1
    assert [n for n in PP.notices(_PERSONA) if n["status"] == "late"], "the new crossing shows"


@check("review L2: with no weekly time given and nothing done, nothing is said (no made-up pace); a "
       "fix never asks for more minutes when none are needed")
def _():
    _fresh("rv_l2", _ALL3, goals=_M_GOAL.format(due=_d(14), v=_d(0)))
    assert PP.plan_project("q1", size="M").startswith("Queued")
    steps = [{"key": f"k{i}", "what": w, "minutes": 90, "eligible_from": _d(0), "due": _d(13),
              "needs": []} for i, w in enumerate(["Fill in the renewal form online",
                                                  "Get two photos taken", "Post the old passport",
                                                  "Book the counter check", "Collect it"])]
    _REPLIES.append(json.dumps({"size": "M", "steps": steps, "note": "ok"}))
    assert _run_planner()
    assert GN.finish_daily(_PERSONA, TODAY) == 0
    assert _req("q1")["finish"]["last"]["pace_source"] == "default"
    p = {"projected": _d(20), "floor": _d(1), "target": _d(14), "remaining_minutes": 60,
         "pace": 300, "pace_source": "stated"}
    assert GN._fix(p, TODAY, None).startswith("moving the date")


@check("review L3: parking an L goal and taking it on again plans its milestone afresh — no 'none "
       "of its steps got done' question, and the full pass survives the park")
def _():
    _planned_l("rv_l3")
    G._calling_agent = lambda: "synthesizer"
    G.update_goal("vet", goal_id="l1", verdict="parked", revisit_on=_d(30))
    assert _goal("l1")["vetted"]["pass"] == "full"
    assert PP.advance_waves(_PERSONA) == 0, "parked: nothing moves"
    G.update_goal("vet", goal_id="l1", verdict="active", size="L", priority="high", displaces="TV")
    assert PP.advance_waves(_PERSONA) == 1
    r = _req("l1")
    assert r["status"] == "queued" and r["expand"] == "m1" and r["milestones"][0]["status"] != "stalled"
    assert GN.revet_daily(_PERSONA, TODAY) == 0


@check("review L4: a milestone's steps may not start before the milestone does")
def _():
    _planned_l("rv_l4")
    st = PP._load(_PERSONA)
    req = {**st["requests"]["l1"], "expand": "m2"}
    payload = PP._payload(req, _PERSONA)
    early = json.dumps({"size": "L", "steps": [{"key": "x", "what": "Write ten sentences",
                                                "minutes": 30, "eligible_from": _d(0),
                                                "due": _d(1), "needs": []}]})
    errs = PP._check(early, req, payload)[2]
    assert any("before its milestone starts" in e for e in errs), errs


@check("review L5 + L11: the basement plants through the day planner's own slip record — four "
       "planned-and-missed days fire; one recent slip plus three old ones never reads as four")
def _():
    _fresh("rv_l5", _ALL3, goals=_PLANTS)
    tid = _plants_step()
    # As the tick runs it: each morning records the day before (the planner keeps 3 days of plans).
    for n in range(4, 0, -1):
        day = TODAY - timedelta(days=n)
        D._write_json(D._plan_path(day, _PERSONA), {"blocks": [{"kind": "task", "task_id": tid}]})
        assert D._record_slips(_PERSONA, day + timedelta(days=1)) == 1
    s = D._load_state(_PERSONA)["slips"][tid]
    assert len(s["recent"]) == 4, s
    assert GN.revet_daily(_PERSONA, TODAY) == 1
    assert GN._slip_days({"first": _d(-40), "days": 4, "last": _d(-1)}) == {TODAY - timedelta(days=1)}


@check("review L6: a goal marked at_risk or not_started is asked about too")
def _():
    _fresh("rv_l6", _ALL3, goals=_PLANTS.replace("status: active", "status: at_risk"))
    _slips(_plants_step(), 5)
    assert GN.revet_daily(_PERSONA, TODAY) == 1


@check("review L7: a weekly review that renders the look back on several turns counts once")
def _():
    _fresh("rv_l7", {**_ALL3, "weekly_priorities": True}, goals=_l_goal(vetted_days_ago=14))
    GN.revet_daily(_PERSONA, TODAY)
    for _ in range(4):
        assert "GOAL CHECK" in RR.weekly_block(_PERSONA, "weekly_review", weekly=True)
    assert PP._load(_PERSONA)["revet"]["l1"]["fires"][0]["shows"] == 1


@check("review L8: no re-vet signal rows with ranking_signals off")
def _():
    _fresh("rv_l8", {**_ALL3, "weekly_priorities": True, "ranking_signals": False},
           goals=_l_goal(vetted_days_ago=14))
    GN.revet_daily(_PERSONA, TODAY)
    RR.weekly_block(_PERSONA, "weekly_review", weekly=True)
    assert RR.note_said("How is the Bulgarian going — still worth it?", _PERSONA) == 1
    assert not _signals()


@check("review L9: flags off — an L goal with steps is skipped by allocation gaps as in phase 2, "
       "and an Interviewer L vet writes 'short', not 'full'")
def _():
    _fresh("rv_l9", goals="long:\n- {id: l1, title: Run a marathon, status: proposed}\n")
    G._calling_agent = lambda: "goals_interviewer"
    G.update_goal("vet", goal_id="l1", verdict="active", size="L", priority="high", displaces="x")
    assert _goal("l1")["vetted"]["pass"] == "short"
    O.open_plan([{"key": "a", "what": "Buy running shoes", "due": _d(5), "flexible": True,
                  "eligible_from": _d(0), "part_of": "l1", "goal_id": "l1"}])
    assert not any(g["id"] == "l1" for g in D.allocation_gaps(_PERSONA))


@check("review L10: an obligation's re-vet is answered by a new date, and that is recorded")
def _():
    goals = _PLANTS.replace("  size: M\n", "  size: M\n  kind: obligation\n  due: '%s'\n" % _d(20))
    _fresh("rv_l10", {**_ALL3, "weekly_priorities": True, "ranking_signals": True}, goals=goals)
    _slips(_plants_step(), 5)
    GN.revet_daily(_PERSONA, TODAY)
    RR.weekly_block(_PERSONA, "weekly_review", weekly=True)
    assert RR.note_said("Is the date for the house plants still right, or would a later one help?",
                        _PERSONA) == 1
    G._calling_agent = lambda: "synthesizer"
    G.update_goal("update", goal_id="q1", due=_d(40))
    rows = _signals()
    assert rows[-1]["kind"] == "revet_answer" and rows[-1]["verdict"] == "date_changed", rows


@check("playbook: an `applies_when` entry with a space is matched as a phrase")
def _():
    d = _fresh("playbook_phrase")
    pb = d / "playbooks"
    pb.mkdir(exist_ok=True)
    (pb / "lang.md").write_text("applies_when: learn, learning | sign language, bulgarian\n")
    saved = PP._PLAYBOOKS
    PP._PLAYBOOKS = pb
    try:
        assert PP._playbook("Learn sign language")
        assert PP._playbook("Learn to sign the language form") is None
    finally:
        PP._PLAYBOOKS = saved


def main() -> int:
    width = max(len(n) for n, _, _ in _results) if _results else 0
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
