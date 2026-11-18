"""
tests/run_goal_network_fixtures.py — the goal–task network, phase 1, across the seven fixture
personas (archive/plans/goal_task_network_plan_2026-11-18.md § 6).

Each persona's goals are copied into a temp directory (nothing under data/personas/ or
config/personas/ is written), seeded with a Red Book-like prep (an event tomorrow at 09:30 whose
finding says what to gather first) and a two-step task, and run through three simulated days of
scheduler ticks. Asserted every tick: only the step that can be done now is ever visible, a blocked
step is never placed, the prep is placed before its event, and step 2 appears once step 1 is done.

EVERY LIVE METER IS STUBBED: CalDAV, Google Routes, the day_planner model (any call fails the
run), push. Phase 1 calls no model of its own, so there is no METATRON_LIVE pass here; that
arrives with the project planner in phase 2.

    python3 tests/run_goal_network_fixtures.py
"""
from __future__ import annotations

import json
import shutil
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
import tools.routing as R  # noqa: E402

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
_SHAPE = """\
day: [{days: all, wake: "07:00", bed: "23:00"}]
windows:
  - {activity: family, days: all, from: "17:30", to: "20:30", strength: protected}
"""
_FLAGS = {"build": True, "show_in_app": True, "ledger_fields": True, "synth_reads_plan": True,
          "unconfirmed_rule": True, "reshuffle_model": False, "nudges": False,
          "owns_checkins": False, "prep_tasks": True, "horizon_cap": True}


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
    if _MODEL["calls"]:
        errors.append(f"{_MODEL['calls']} model call(s)")
    return errors


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
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
