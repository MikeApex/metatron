"""
tests/run_goal_network_fixtures.py — the goal–task network, phase 1, across the seven fixture
personas (archive/plans/goal_task_network_plan_2026-11-18.md § 6).

Each persona's goals are copied into a temp directory (nothing under data/personas/ or
config/personas/ is written), seeded with a Red Book-like prep (an event tomorrow at 09:30 whose
finding says what to gather first) and a two-step task, and run through three simulated days of
scheduler ticks. Asserted every tick: only the step that can be done now is ever visible, a blocked
step is never placed, the prep is placed before its event, and step 2 appears once step 1 is done.

PHASE 2 (2026-11-21): each persona also takes on an M obligation ("File UK taxes", vetted in
the turn as Synth does), queued with plan_project and planned by the project planner off the
tick, its model stubbed. Asserted across simulated days: the steps are flexible and dated, only
the step that can be done now is ever on Today, a waiting step is never placed, and each step
appears once the one before it is done — by the deadline.

EVERY LIVE METER IS STUBBED: CalDAV, Google Routes, the day_planner model (any call fails the
run), the project_planner model (a stub), push. The one live meter this phase adds — the project
planner's real output — runs only with METATRON_LIVE=1, once, on danny_park's copy, and is judged
by the same validator code applies in production (~$0.02).

    python3 tests/run_goal_network_fixtures.py
    METATRON_LIVE=1 python3 tests/run_goal_network_fixtures.py
"""
from __future__ import annotations

import json
import os
import shutil
import threading
import sys
import tempfile
from datetime import date, datetime, time, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import core.interview as INTV  # noqa: E402
import core.persona as P  # noqa: E402
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
import core.remote_client as RC  # noqa: E402

PERSONAS = ("danny_park", "sarah_chen", "maya_torres", "arthur_brooks", "cal_newport",
            "oliver_burkeman", "ryan_holiday")
TODAY = date.today()                       # the horizon ledger dates by date.today()
_CLOCK = {"now": datetime.combine(TODAY, time(7, 0))}
O._now = lambda: _CLOCK["now"]
A._get_timezone = lambda: "Europe/London"
_EVENTS: dict = {"v": []}
_MODEL = {"calls": 0}
CAL._query_events = lambda s, e, persona=None, calendars="own": {
    "events": json.loads(json.dumps(_EVENTS["v"])), "discovery": "ok"}
CAL._get_event_by_uid = lambda uid, persona=None: {"error": "Failed to fetch event: stubbed"}
R.get_travel_time = lambda *a, **k: {"journeys": [{"duration_minutes": 20}]}
L.load_zones = lambda persona=None: []
L.current_zone = lambda persona=None: {}
INTV.holds_proactive = lambda persona: False


def _no_model(*a, **k):
    _MODEL["calls"] += 1
    raise AssertionError("model call")


D._call_model = _no_model
RC.send_one = lambda *a, **k: "ok"                     # push — a real call reaches the server
_PLANNER = {"calls": 0}
_STEPS = ("Download the payroll summary", "Collect bank interest figures",
          "Enter income online", "Submit and save the receipt")


def _stub_planner(payload):
    _PLANNER["calls"] += 1
    today = date.fromisoformat(payload["today"])
    steps = [{"key": f"k{i}", "what": w, "minutes": 30,
              "eligible_from": (today + timedelta(days=2 * i)).isoformat(),
              "due": (today + timedelta(days=2 * i + 3)).isoformat(),
              "needs": [f"k{i - 1}"] if i else []} for i, w in enumerate(_STEPS)]
    return json.dumps({"size": "M", "steps": steps, "note": "stub"})


PP._MODEL_CALL = _stub_planner
_SHAPE = """\
day: [{days: all, wake: "07:00", bed: "23:00"}]
windows:
  - {activity: family, days: all, from: "17:30", to: "20:30", strength: protected}
"""
_FLAGS = {"build": True, "show_in_app": True, "ledger_fields": True, "synth_reads_plan": True,
          "unconfirmed_rule": True, "reshuffle_model": False, "nudges": False,
          "owns_checkins": False, "prep_tasks": True, "horizon_cap": True,
          "project_planner": True}


def _setup(persona: str, base: Path) -> Path:
    d = base / persona
    (d / "config").mkdir(parents=True)
    src = ROOT / "config" / "personas" / persona / "goals.yaml"
    goals = d / "config" / "goals.yaml"
    if src.exists():
        shutil.copy(src, goals)
    else:
        goals.write_text("quarterly: []\n")
    for mod in (O, D, DS, L, H):
        mod.persona_data_dir = lambda persona=None, _d=d: _d
    DS.persona_config_dir = lambda persona=None, _d=d: _d / "config"
    G._goals_path = lambda _g=goals: _g
    (d / "day_shape.yaml").write_text(_SHAPE)
    C._OVERRIDE = {"flags": dict(_FLAGS)}
    O._DAY_STARTS_CACHE.update(key=None)
    O._GOAL_CACHE.update(key=None)
    return d


def _leaks(day: date) -> list[str]:
    """Every blocked step any reader shows — the user's Today, the head layer's Tasks block, or
    list_tasks. Must always be empty."""
    block = O.context_block(as_of=day)
    listed = O.list_tasks()
    today = {i["task_id"] for i in O.today_items(as_of=day)}
    return [t["what"] for t in O._load() if t.get("_blocked")
            and (t["id"] in today or t["what"] in block or t["what"] in listed)]


def _on_today(day: date) -> set[str]:
    return {i["task_id"] for i in O.today_items(as_of=day)}


def run_one(persona: str, base: Path) -> list[str]:
    errors: list[str] = []
    _setup(persona, base)
    _CLOCK["now"] = datetime.combine(TODAY, time(7, 0))
    t1 = TODAY + timedelta(days=1)
    _EVENTS["v"] = [{"uid": f"u-{persona}", "title": "Settling-in session — Little Acorns",
                     "start": f"{t1}T09:30:00", "end": f"{t1}T10:30:00",
                     "location": "Little Acorns Nursery", "status": "", "calendars": ["Main"],
                     "calendar_ids": ["/cal/main"], "read_only": False}]
    H.record([{"title": "Settling-in session", "date": t1.isoformat(),
               "venue": "Little Acorns Nursery", "kind": "appointment", "detail": "",
               "precursor": "gather the Red Book and paperwork", "precursor_by": ""}])
    plan = O.open_plan([
        {"key": "a", "what": "Find the old passport", "minutes": 15, "part_of": "b",
         "due": TODAY.isoformat()},
        {"key": "b", "what": "Post the renewal form", "needs": ["a"], "minutes": 20,
         "due": t1.isoformat()},
    ])
    if not plan.get("ok"):
        return [f"open_plan refused: {plan}"]
    a, b = plan["ids"]["a"], plan["ids"]["b"]

    def tick(at: datetime, expect_today: set[str]) -> dict | None:
        _CLOCK["now"] = at
        D.refresh_tick()
        day_plan = json.loads(D._plan_path(at.date()).read_text())
        placed = {x.get("task_id") for x in day_plan["blocks"] if x.get("kind") == "task"}
        for t in O._load():
            if t.get("_blocked") and t["id"] in placed:
                errors.append(f"{at:%m-%d %H:%M}: blocked step {t['what']!r} was placed")
        leaked = _leaks(at.date())
        if leaked:
            errors.append(f"{at:%m-%d %H:%M}: a blocked step is visible: {leaked}")
        steps_today = _on_today(at.date()) & {a, b}
        if steps_today != expect_today:
            errors.append(f"{at:%m-%d %H:%M}: steps on Today {sorted(steps_today)} != "
                          f"{sorted(expect_today)}")
        return day_plan

    day0 = tick(datetime.combine(TODAY, time(7, 0)), {a})
    preps = [t for t in O._load() if str(t.get("source_id") or "").startswith(D._PREP_SOURCE)]
    if len(preps) != 1:
        errors.append(f"expected one prep, found {len(preps)}")
    else:
        prep = preps[0]
        blk = next((x for x in day0["blocks"] if x.get("task_id") == prep["id"]), None)
        if prep.get("due") != TODAY.isoformat() or blk is None:
            errors.append(f"prep not placed the evening before: due {prep.get('due')}, block {blk}")
        elif blk["end"] > f"{t1}T09:30":
            errors.append("prep placed after its event")
    O.update_task(a, "done", evidence="found it")
    tick(datetime.combine(TODAY, time(12, 0)), set())          # b is due tomorrow: not on Today
    if preps:
        O.update_task(preps[0]["id"], "done", evidence="packed it")
    tick(datetime.combine(t1, time(7, 0)), {b})
    O.update_task(b, "done", evidence="posted")
    tick(datetime.combine(t1 + timedelta(days=1), time(7, 0)), set())
    errors += run_m_item(persona)
    if _MODEL["calls"]:
        errors.append(f"{_MODEL['calls']} model call(s)")
    return errors


def _join() -> None:
    for th in threading.enumerate():
        if th.name.startswith("day_plan_"):
            th.join(10)


def run_m_item(persona: str) -> list[str]:
    """Phase 2 on this persona: an M obligation stated, vetted, queued, planned off the tick, and
    fed one step at a time over simulated days."""
    errors: list[str] = []
    start = datetime.combine(TODAY + timedelta(days=3), time(7, 0))
    _CLOCK["now"] = start
    _EVENTS["v"] = []
    G._calling_agent = lambda: "synthesizer"
    out = G.update_goal("add", horizon="quarterly", title="File UK taxes",
                        due=(start.date() + timedelta(days=30)).isoformat(), kind="obligation")
    gid = out.split()[3] if "being considered" in out else None
    if not gid:
        return [f"goal not recorded as considered: {out}"]
    vet = G.update_goal("vet", goal_id=gid, verdict="active", size="M", priority="ahead of the rest")
    G._calling_agent = lambda: ""
    O._GOAL_CACHE.update(key=None)
    if "taken on" not in vet:
        return [f"vet refused: {vet}"]
    calls_before = _PLANNER["calls"]
    q = PP.plan_project(gid)
    if not q.startswith("Queued") or _PLANNER["calls"] != calls_before:
        return [f"plan_project did not only queue: {q}"]
    D.refresh_tick()                       # starts the worker
    _join()
    req = PP._load()["requests"].get(gid) or {}
    if req.get("status") != "planned" or _PLANNER["calls"] != calls_before + 1:
        return [f"not planned: {req}"]
    steps = {t["id"]: O._norm(t) for t in O._load() if t.get("part_of") == gid}
    if len(steps) != len(_STEPS):
        errors.append(f"{len(steps)} steps written, expected {len(_STEPS)}")
    for t in steps.values():
        if not (t.get("flexible") and t.get("due") and t.get("eligible_from")):
            errors.append(f"step {t['what']!r} is not flexible and dated")
    order = sorted(steps.values(), key=lambda t: t["eligible_from"])
    for i, step in enumerate(order):
        at = datetime.combine(O._d(step["eligible_from"]), time(7, 0))
        _CLOCK["now"] = at
        D.refresh_tick()
        _join()
        day_plan = json.loads(D._plan_path(at.date()).read_text())
        placed = {x.get("task_id") for x in day_plan["blocks"] if x.get("kind") == "task"}
        on_today = _on_today(at.date()) & set(steps)
        for t in O._load():
            if t.get("_blocked") and t["id"] in placed:
                errors.append(f"{at:%m-%d}: waiting step {t['what']!r} was placed")
        leaked = _leaks(at.date())
        if leaked:
            errors.append(f"{at:%m-%d}: a waiting step is visible: {leaked}")
        if on_today != {step["id"]}:
            names = sorted(steps[x]["what"] for x in on_today)
            errors.append(f"{at:%m-%d}: Today shows {names}, expected only {step['what']!r}")
        O.update_task(step["id"], "done", evidence="did it")
        if O._d(step["due"]) > O._d(req["deadline"]):
            errors.append(f"step {step['what']!r} is due after the deadline")
    done = [t for t in O._load() if t.get("part_of") == gid and t.get("status") == "done"]
    if len(done) != len(_STEPS):
        errors.append(f"{len(done)} of {len(_STEPS)} steps done at the end")
    return errors


def live_planner_pass(base: Path) -> int:
    """METATRON_LIVE=1: the project planner's REAL output for one M obligation, judged by the
    production validator. The one live meter this phase adds (~$0.02 a call)."""
    persona = "danny_park"
    with P.persona_scope(persona):
        _setup(persona, base / "live")
        _CLOCK["now"] = datetime.combine(TODAY, time(9, 0))
        G._calling_agent = lambda: "synthesizer"
        gid = G.update_goal("add", horizon="quarterly", title="File UK taxes",
                            due=(TODAY + timedelta(days=39)).isoformat(),
                            kind="obligation").split()[3]
        G.update_goal("vet", goal_id=gid, verdict="active", size="M", priority="first")
        G._calling_agent = lambda: ""
        O._GOAL_CACHE.update(key=None)
        PP.plan_project(gid, note="employed, already files online, no accountant")
        req = PP._load()["requests"][gid]
        payload = PP._payload(req, persona)
        PP._MODEL_CALL = None
        try:
            raw = PP._call_model(payload, persona)
        finally:
            PP._MODEL_CALL = _stub_planner
            C._OVERRIDE = None
        size, steps, errs = PP.validate(D._extract_json(raw), req, payload)
        print(f"\nLIVE project planner: size {size}, {len(steps)} steps, "
              f"{'VALID' if not errs else 'INVALID'}")
        for st in steps:
            print(f"    {st['ef']} → {st['due']}  {st['minutes']:>3} min  {st['what']}"
                  + (f"  (needs {', '.join(st['needs'])})" if st["needs"] else ""))
        for e in errs:
            print(f"    ! {e}")
        return 1 if errs or size != "M" else 0


def main() -> int:
    base = Path(tempfile.mkdtemp(prefix="goal_network_fixtures_"))
    failed = 0
    for persona in PERSONAS:
        with P.persona_scope(persona):
            try:
                errors = run_one(persona, base)
            except Exception as exc:  # noqa: BLE001
                import traceback
                errors = [f"{type(exc).__name__}: {exc}\n" + traceback.format_exc()[-600:]]
            finally:
                C._OVERRIDE = None
        print(f"  {'PASS' if not errors else 'FAIL'}  {persona}")
        for e in errors:
            print(f"        {e}")
        failed += bool(errors)
    print(f"\n{len(PERSONAS) - failed} passed, {failed} failed, {len(PERSONAS)} total")
    if os.environ.get("METATRON_LIVE") == "1":
        failed += live_planner_pass(base)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
