"""
tests/test_day_plan_round2.py — the day planner's round 2: the dynamic day shape, event triage,
routines, meals that ask, placement by activity, and the monthly window.
Plan: archive/plans/day_planner_plan_2026-10-24.md § 18 (R2-12), review
archive/plans/adversarial_review_day_planner_plan_2026-10-26.md.

The fixture has the SHAPE of 2026-10-25, with synthetic names: overlapping family-calendar events,
a promotion, a weekday lunch routine with a place, a located "Lunch with …", a twice-daily habit,
tasks due tomorrow, an undated one, a monthly bill.

EVERY LIVE METER IS STUBBED (the standing rule): CalDAV (`_query_events`), Google Routes
(`get_travel_time`). No persona data — a temp directory per check. Run it, do not read it:

    python3 tests/test_day_plan_round2.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import threading
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.persona as P  # noqa: E402
import tools.ambient as A  # noqa: E402
import tools.caldav as CAL  # noqa: E402
import tools.day_plan as D  # noqa: E402
import tools.day_plan_config as C  # noqa: E402
import tools.day_shape as DS  # noqa: E402
import tools.goals as G  # noqa: E402
import tools.location as L  # noqa: E402
import tools.obligations as O  # noqa: E402
import tools.routing as R  # noqa: E402

_results: list[tuple[str, bool, str]] = []
_TMP = Path(tempfile.mkdtemp(prefix="day_plan_round2_"))
_CLOCK = {"now": datetime(2026, 10, 27, 7, 0)}           # Tuesday
O._now = lambda: _CLOCK["now"]
A._get_timezone = lambda: "Europe/London"
_PERSONA = "dp_round2"

_SHAPE = """\
day: [{days: all, wake: "07:00", bed: "23:00"}]
windows:
  - {activity: family, days: all, from: "07:00", to: "10:00", strength: protected}
  - {activity: family, days: all, from: "17:30", to: "20:30", strength: protected}
  - {activity: [focus, creative, admin], days: mon-fri, from: "10:00", to: "15:00", strength: preferred}
  - {activity: [focus, creative, admin], days: mon-fri, from: "10:00", to: "17:30", strength: strong}
  - {activity: [focus, creative, admin], days: "sat,sun", from: "10:00", to: "17:30", strength: strong,
     condition: "when free of childcare"}
routines:
  - {what: "Lunch with Alex", days: mon-fri, from: "12:00", to: "13:00", place: "Canary Wharf",
     covers: lunch}
meals:
  - {name: breakfast, at: "08:30"}
  - {name: lunch, at: "12:00", latest: "15:00"}
  - {name: snack, from: "16:00", to: "17:00", when: {meal: lunch, ends_by: "13:30"}}
  - {name: dinner, at: "19:00"}
calendars:
  /cal/mt: {name: Metatron, role: mine}
  /cal/main: {name: Main, role: mine}
  /cal/fam: {name: Family, role: family}
event_rules:
  - {match: [GMAT], answer: there}
  - {match: [admissions], answer: needs_me, duty: childcare}
  - {match: ["happy hour"], answer: noise}
children_home:
  - {days: mon-fri, from: "07:00", to: "08:30"}
  - {days: mon-fri, from: "15:30", to: "19:30"}
  - {days: "sat,sun", from: "07:00", to: "19:30"}
travel_mode: transit
"""


_SHAPE_RULES = [{"match": ["GMAT"], "answer": "there"},
                {"match": ["admissions"], "answer": "needs_me", "duty": "childcare"},
                {"match": ["happy hour"], "answer": "noise"}]


def _ev(uid, title, start, end, cal="fam", location=""):
    names = {"mt": "Metatron", "main": "Main", "fam": "Family", "new": "Book club"}
    return {"uid": uid, "title": title, "start": start, "end": end, "location": location,
            "status": "", "calendars": [names[cal]], "calendar_ids": [f"/cal/{cal}"],
            "read_only": cal != "mt"}


_TUESDAY = [
    _ev("u-promo", "Happy Hour ⚡ promo", "2026-10-27T09:00:00", "2026-10-27T10:00:00", "main"),
    _ev("u-vote", "Alex to vote", "2026-10-27T10:00:00", "2026-10-27T12:15:00"),
    _ev("u-gmat", "GMAT session — Jo", "2026-10-27T14:00:00", "2026-10-27T15:00:00"),
    _ev("u-adm", "Admissions evening", "2026-10-27T16:00:00", "2026-10-27T18:00:00"),
    _ev("u-book", "Book club", "2026-10-27T13:30:00", "2026-10-27T14:00:00", "new"),
    _ev("u-standup", "Standup", "2026-10-27T09:30:00", "2026-10-27T09:45:00", "mt"),
]
_EVENTS = {"v": _TUESDAY, "discovery": "ok"}
_CALLS = {"routes": 0}


def _query_events(start, end, persona=None, calendars="own"):
    return {"events": json.loads(json.dumps(_EVENTS["v"])), "discovery": _EVENTS["discovery"]}


CAL._query_events = _query_events


def _route(origin, destination, mode="transit", arrive_by=""):
    _CALLS["routes"] += 1
    return {"journeys": [{"duration_minutes": 25}]}


R.get_travel_time = _route
L.load_zones = lambda persona=None: [{"name": "home", "lat": 51.5, "lon": -0.12, "radius_m": 100}]
L.current_zone = lambda persona=None: {"zone": "home", "entered_at": "2026-10-26T21:00:00"}


def _fresh(name: str, shape: str = _SHAPE) -> Path:
    for th in threading.enumerate():
        if th.name.startswith("day_plan_"):
            th.join(5)
    d = _TMP / name
    (d / "config").mkdir(parents=True, exist_ok=True)
    for mod in (O, D, DS, L):
        mod.persona_data_dir = lambda persona=None, _d=d: _d
    DS.persona_config_dir = lambda persona=None, _d=d: _d / "config"
    (d / "config" / "goals.yaml").write_text("quarterly: []\n")
    G._goals_path = lambda _d=d: _d / "config" / "goals.yaml"
    (d / "day_shape.yaml").write_text(shape)
    C._OVERRIDE = {"flags": {"build": True, "show_in_app": True, "ledger_fields": True}}
    _EVENTS.update(v=_TUESDAY, discovery="ok")
    _CALLS["routes"] = 0
    _CLOCK["now"] = datetime(2026, 10, 27, 7, 0)
    return d


def _tasks() -> dict:
    ids = {}
    ids["return"] = O.open_task("File the quarterly return", kind="deadline", due="2026-10-27",
                                domain="finance", minutes=60, minutes_source="stated")
    ids["essay"] = O.open_task("Write the essay", kind="deadline", due="2026-10-27",
                               domain="work", minutes=90, minutes_source="stated")
    ids["post"] = O.open_task("Post the job listing", kind="deadline", due="2026-10-28",
                              domain="logistics", minutes=30)
    ids["refund"] = O.open_task("Check the refund status", kind="deadline", domain="finance")
    ids["stretch"] = O.open_task("Stretching", kind="habit", every="day", times=2, minutes=20)
    ids["garage"] = O.open_task("Tidy the garage", kind="habit", every="week", times=1,
                                on_days=["tue"], domain="household", minutes=30)
    ids["bill"] = O.open_task("Pay the card bill", kind="habit", every="month", minutes=10)
    return {k: v.split()[1] for k, v in ids.items()}


def _ready(name: str, shape: str = _SHAPE):
    d = _fresh(name, shape)
    ids = _tasks()
    D.refresh_snapshot(_PERSONA)
    return d, ids


def check(name: str):
    def deco(fn):
        try:
            with P.persona_scope(_PERSONA):
                fn()
            _results.append((name, True, ""))
        except Exception as exc:  # noqa: BLE001
            import traceback
            _results.append((name, False, f"{type(exc).__name__}: {exc}\n"
                             + "".join(traceback.format_exc().splitlines(True)[-4:])))
        finally:
            C._OVERRIDE = None
        return fn
    return deco


def _kind(plan, kind):
    return [b for b in plan["blocks"] if b["kind"] == kind]


def _hm(s):
    return s[11:16]


def _tasks_by(plan, ids):
    out = {}
    for b in _kind(plan, "task"):
        out.setdefault(b["task_id"], []).append(b)
    return out


# --- R2-3: today is what the Today list says it is ------------------------------------------

@check("R2-3: only today's tasks — not one due tomorrow, not an undated one, not a monthly bill "
       "on an ordinary day — and the plan agrees with the Today list")
def _():
    d, ids = _ready("today")
    plan = D.current(_PERSONA)
    assert plan["failures"] == [], plan["failures"]
    refs = {b["task_id"] for b in _kind(plan, "task")}
    assert ids["post"] not in refs and ids["refund"] not in refs and ids["bill"] not in refs, refs
    assert {ids["return"], ids["essay"], ids["stretch"], ids["garage"]} <= refs, refs
    listed = {i["task_id"] for i in O.today_items()}
    assert refs <= listed, (refs, listed)


# --- R2-5: what each event means ------------------------------------------------------------

@check("R2-5/F3: a noise rule fires on the user's own calendar; GMAT is theirs by rule; an "
       "unanswered family event is a hold; admissions is childcare; a new calendar is held back")
def _():
    d, ids = _ready("triage")
    plan = D.current(_PERSONA)
    assert plan["failures"] == [], plan["failures"]
    keys = {b.get("key"): b for b in plan["blocks"] if b.get("key")}
    assert "u-promo@2026-10-27T09:00:00" in plan["hidden"], plan["hidden"]
    assert keys["u-gmat@2026-10-27T14:00:00"]["kind"] == "event"
    assert keys["u-vote@2026-10-27T10:00:00"]["kind"] == "hold"
    duty = keys["u-adm@2026-10-27T16:00:00"]
    assert duty["kind"] == "duty" and duty["duty"] == "childcare" and duty["activities"] == ["family"]
    assert plan["held_back"] == {"Book club": ["u-book@2026-10-27T13:30:00"]}, plan["held_back"]
    assert plan["notes"] and plan["notes"][0].startswith("New calendar “Book club”"), plan["notes"]
    assert keys["u-standup@2026-10-27T09:30:00"]["kind"] == "event"    # the writable one: mine


@check("N1: when discovery failed, no calendar is new — the event is planned as the user's")
def _():
    d, ids = _ready("n1")
    _EVENTS["discovery"] = "discovery failed: timeout"
    D.refresh_snapshot(_PERSONA)
    plan = D.current(_PERSONA)
    assert plan["held_back"] == {}, plan["held_back"]
    book = next(b for b in plan["blocks"] if b.get("key") == "u-book@2026-10-27T13:30:00")
    assert book["kind"] == "event", book


@check("F1: an answer about one occurrence beats the series answer; the series answer covers the rest")
def _():
    _fresh("f1")
    shape = DS.shape_for(date(2026, 10, 27))
    answers = {"series": {"u-swim": {"answer": "someone_else"}},
               "occurrences": {"u-swim@2026-10-27T17:00:00": {"answer": "needs_me",
                                                             "duty": "childcare"}}}
    one = {"uid": "u-swim", "key": "u-swim@2026-10-27T17:00:00", "title": "Swim club",
           "read_only": True, "calendar_ids": ["/cal/fam"]}
    other = dict(one, key="u-swim@2026-11-03T17:00:00")
    assert D._triage(one, shape, answers, True)["answer"] == "needs_me"
    assert D._triage(other, shape, answers, True)["answer"] == "someone_else"


@check("D1: with no roster yet, every calendar is the user's")
def _():
    _fresh("d1", _SHAPE.replace("calendars:\n  /cal/mt: {name: Metatron, role: mine}\n"
                                "  /cal/main: {name: Main, role: mine}\n"
                                "  /cal/fam: {name: Family, role: family}\n", ""))
    shape = DS.shape_for(date(2026, 10, 27))
    assert shape["calendars"] == {}
    ev = {"uid": "u", "key": "u@x", "title": "Alex to vote", "read_only": True,
          "calendar_ids": ["/cal/fam"]}
    assert D._triage(ev, shape, {}, True)["answer"] == "there"


# --- R2-4, F6: placement by activity --------------------------------------------------------

@check("R2-4/F6: admin and focus stay out of family time and off the hold; stretching and a "
       "household task may share family time; admin lands in its strong window")
def _():
    d, ids = _ready("activity")
    plan = D.current(_PERSONA)
    assert plan["failures"] == [], plan["failures"]
    t = _tasks_by(plan, ids)
    ret = t[ids["return"]][0]
    assert "10:00" <= _hm(ret["start"]) and _hm(ret["end"]) <= "17:30", ret
    hold = next(b for b in plan["blocks"] if b["kind"] == "hold")
    for b in t[ids["return"]] + t[ids["essay"]]:
        assert not (b["start"] < hold["end"] and hold["start"] < b["end"]), (b, hold)
        assert not ("07:00" <= _hm(b["start"]) < "10:00") and not ("17:30" <= _hm(b["start"]) < "20:30"), b
    stretch = sorted(_hm(b["start"]) for b in t[ids["stretch"]])
    assert len(stretch) == 2 and stretch[0] < "10:00", stretch        # family time admits it
    assert _hm(t[ids["garage"]][0]["start"]) < "10:00", t[ids["garage"]]


@check("solo: the gym is exercise by its title and stays out of family time; an errand may share it")
def _():
    d, ids = _ready("solo")
    gym = O.open_task("Gym workout session", kind="habit", every="day", domain="physical_health",
                      minutes=60).split()[1]
    errand = O.open_task("Pick up the dry cleaning", kind="deadline", due="2026-10-27",
                         minutes=20, stakes="missable")
    plan = D.current(_PERSONA)
    assert plan["failures"] == [], plan["failures"]
    c = next(c for c in D._candidates(date(2026, 10, 27), _PERSONA) if c["task_id"] == gym)
    assert c["activity"] == "exercise" and c["attrs"].get("solo") is True, c
    # On this crowded day it may not fit at all — then it drops quietly; never into family time.
    for g in (b for b in _kind(plan, "task") if b["task_id"] == gym):
        assert not ("07:00" <= _hm(g["start"]) < "10:00") and not ("17:30" <= _hm(g["start"]) < "20:30"), g
    assert any(b["task_id"] == gym for b in _kind(plan, "task")) or c["ref"] in plan["dropped"]
    raw = D._normalise([{"uid": "u", "title": "Lunch with Victoria", "start": "2026-10-27T12:30:00",
                         "end": "2026-10-27T14:00:00",
                         "location": "The Ledger Building\\, West India Quay\\, London"}])
    assert raw[0]["location"] == "The Ledger Building, West India Quay, London", raw[0]["location"]
    assert errand.startswith("opened") or "ob_" in errand, errand


@check("V6: a screen task forced into family time fails the validator; a light one does not")
def _():
    d, ids = _ready("v6")
    plan = D.current(_PERSONA)
    cands = D._candidates(date(2026, 10, 27), _PERSONA)
    ret = next(c for c in cands if c["task_id"] == ids["return"])
    bad = json.loads(json.dumps(plan))
    bad["blocks"] = [b for b in bad["blocks"] if b.get("ref") != ret["ref"]]
    ret["essential"] = False
    bad["blocks"].append({"id": "task:x", "kind": "task", "ref": ret["ref"], "task_id": ids["return"],
                          "title": "x", "start": "2026-10-27T18:00", "end": "2026-10-27T19:00",
                          "essential": False, "copy": 0})
    fails = D.validate(bad, D._events_for(D._load_state(_PERSONA), date(2026, 10, 27)), cands,
                       datetime(2026, 10, 27, 7, 0))
    assert any(f.startswith("V6") for f in fails), fails
    ok = [f for f in plan["failures"] if f.startswith("V6")]
    assert ok == [], ok


@check("V2: an event missing from the plan in every form fails the validator")
def _():
    d, ids = _ready("v2")
    plan = D.current(_PERSONA)
    cands = D._candidates(date(2026, 10, 27), _PERSONA)
    bad = json.loads(json.dumps(plan))
    bad["blocks"] = [b for b in bad["blocks"] if b.get("key") != "u-vote@2026-10-27T10:00:00"]
    fails = D.validate(bad, D._events_for(D._load_state(_PERSONA), date(2026, 10, 27)), cands,
                       datetime(2026, 10, 27, 7, 0))
    assert any("V2" in f and "u-vote" in f for f in fails), fails


# --- R2-6, F7, R2-7: routines and appointments ----------------------------------------------

@check("R2-6/F7: the weekday lunch routine stands with travel both ways — a hold over noon does "
       "not displace it — and it stands in for lunch")
def _():
    d, ids = _ready("routine")
    plan = D.current(_PERSONA)
    r = _kind(plan, "routine")
    assert len(r) == 1 and _hm(r[0]["start"]) == "12:00", r
    tr = {b["id"].split(":")[0] for b in _kind(plan, "travel") if b.get("ref") == r[0]["ref"]}
    assert tr == {"travel", "travel_home"}, _kind(plan, "travel")
    assert not any(b["title"] == "lunch" for b in _kind(plan, "meal")), _kind(plan, "meal")
    assert any(b["title"] == "snack" for b in _kind(plan, "meal"))      # lunch ended by 13:30


@check("F7: an event the user is at, over the routine, takes its place that day")
def _():
    d, ids = _ready("routine_gives_way")
    _EVENTS["v"] = _TUESDAY + [_ev("u-dent", "Dentist", "2026-10-27T11:45:00",
                                   "2026-10-27T12:30:00", "main", "1 High St")]
    D.refresh_snapshot(_PERSONA)
    plan = D.current(_PERSONA)
    assert _kind(plan, "routine") == [], _kind(plan, "routine")
    assert plan["failures"] == [], plan["failures"]


@check("R2-7: 'Lunch with Victoria' at a place is an appointment — travel there and back, and "
       "it is lunch; a plain 'Lunch break' is still the user's own block")
def _():
    d, ids = _ready("appointment")
    _EVENTS["v"] = [_ev("u-vic", "Lunch with Victoria", "2026-10-27T12:30:00",
                        "2026-10-27T14:00:00", "main", "The Ledger Building, West India Quay"),
                    _ev("u-own", "Lunch break", "2026-10-28T12:00:00", "2026-10-28T12:30:00", "main")]
    D.refresh_snapshot(_PERSONA)
    plan = D.current(_PERSONA)
    vic = next(b for b in plan["blocks"] if b.get("key", "").startswith("u-vic"))
    assert vic["kind"] == "event", vic
    assert {b["id"].split(":")[0] for b in _kind(plan, "travel") if b.get("ref") == "u-vic"} \
        == {"travel", "travel_home"}, _kind(plan, "travel")
    assert not any(b["title"] == "lunch" for b in _kind(plan, "meal"))
    assert _kind(plan, "routine") == []                    # the routine gave way to it
    own = D._normalise([{"uid": "u-own", "title": "Lunch break", "start": "2026-10-28T12:00:00",
                         "end": "2026-10-28T12:30:00", "location": ""}])
    assert own[0]["own"] == "lunch", own


# --- R2-8: meals ----------------------------------------------------------------------------

_SUNDAY_OPEN = []


@check("R2-8: on a free Sunday lunch is at its time and the early-lunch snack follows")
def _():
    d, ids = _ready("sunday_meals")
    _EVENTS["v"] = _SUNDAY_OPEN
    _CLOCK["now"] = datetime(2026, 11, 1, 7, 0)
    D.refresh_snapshot(_PERSONA)
    plan = D.current(_PERSONA)
    meals = {b["title"]: b for b in _kind(plan, "meal")}
    assert _hm(meals["lunch"]["start"]) == "12:00", meals
    assert "snack" in meals and _hm(meals["snack"]["start"]) >= "16:00", meals


@check("R2-8: a meal with no gap is a question at its time, never a 'not placed' note")
def _():
    d, ids = _ready("meal_ask")
    _CLOCK["now"] = datetime(2026, 11, 1, 7, 0)
    _EVENTS["v"] = [_ev("u-picnic", "Family picnic", "2026-11-01T11:00:00",
                        "2026-11-01T15:30:00", "main")]
    D.refresh_snapshot(_PERSONA)
    plan = D.current(_PERSONA)
    ask = [b for b in _kind(plan, "ask") if b["title"] == "lunch"]
    assert ask and "Family picnic" in ask[0]["ask"], _kind(plan, "ask")
    assert not any("lunch" in n for n in plan["notes"]), plan["notes"]
    assert plan["failures"] == [], plan["failures"]


@check("R2-8: lunch inside an unanswered playdate is placed and asked about")
def _():
    d, ids = _ready("meal_hold")
    _CLOCK["now"] = datetime(2026, 11, 1, 7, 0)
    _EVENTS["v"] = [_ev("u-play", "Playdate with Sam", "2026-11-01T11:30:00", "2026-11-01T15:00:00")]
    D.refresh_snapshot(_PERSONA)
    plan = D.current(_PERSONA)
    lunch = next(b for b in _kind(plan, "meal") if b["title"] == "lunch")
    assert "Playdate with Sam" in lunch.get("ask", ""), lunch


# --- R2-9, F8 -------------------------------------------------------------------------------

@check("R2-9: 'Not placed' lists only essential items; a light leftover drops quietly")
def _():
    d, ids = _ready("unplaced")
    # Distinct words, or the ledger rightly folds them into one task as near-duplicates.
    chores = ["Sort the post", "Clean the windows", "Water the plants", "Fold the laundry",
              "Wipe the kitchen", "Hoover upstairs", "Empty the bins", "Polish the shoes",
              "Mend the fence", "Weed the beds", "Wash the car", "Clear the gutters",
              "Paint the shed", "Oil the hinges", "Defrost the freezer", "Descale the kettle",
              "Rake the leaves", "Sweep the patio"]
    for what in chores:                       # eighteen hours of chores in a sixteen-hour day
        O.open_task(what, kind="habit", every="day", minutes=60)
    plan = D.current(_PERSONA)
    assert all(u["essential"] for u in plan["unplaced"]), plan["unplaced"]
    assert plan.get("dropped"), "expected light chores with no room"
    view = D.today_view(_PERSONA)
    assert not set(view["unplaced"]) & set(chores), view["unplaced"]


@check("F8: weekend work carries its condition as a question until a one-day override settles it")
def _():
    d = _fresh("weekend")
    O.open_task("File the quarterly return", kind="deadline", due="2026-11-01", domain="finance",
                minutes=60, minutes_source="stated")
    _EVENTS["v"] = []
    _CLOCK["now"] = datetime(2026, 11, 1, 7, 0)
    D.refresh_snapshot(_PERSONA)
    plan = D.current(_PERSONA)
    ret = _kind(plan, "task")[0]
    assert ret.get("condition") == "when free of childcare", ret
    row = next(r for r in D.today_view(_PERSONA)["blocks"] if r["kind"] == "task")
    assert row["title"].endswith("(when free of childcare?)"), row
    assert DS.set_day_shape("day_overrides", {"what": "admin", "holds": True},
                            evidence="free all day today", date="2026-11-01").startswith("recorded")
    plan2 = D.current(_PERSONA)
    assert plan2["trigger"] == "repair" and not _kind(plan2, "task")[0].get("condition"), plan2["reasons"]


@check("a dose recorded before the plan placed it does not make the dose still to do read as done")
def _():
    d, ids = _ready("dose_offset")
    _CLOCK["now"] = datetime(2026, 10, 27, 11, 0)
    assert O.update_task(f"{ids['stretch']}@2026-10-27", "done",
                         evidence="did my stretches this morning").startswith(ids["stretch"])
    plan = D.current(_PERSONA)
    left = [b for b in _kind(plan, "task") if b["task_id"] == ids["stretch"] and not b.get("history")]
    assert len(left) == 1, left
    assert D._status_of(left[0]["ref"], left[0]["copy"]) == "open", left[0]
    row = next(r for r in D.today_view(_PERSONA)["blocks"] if r["title"] == "Stretching")
    assert row["status"] != "done", row


# --- the panel ------------------------------------------------------------------------------

@check("the panel reads as the user: a hold asks, a duty names itself, someone else's says so")
def _():
    d, ids = _ready("panel")
    view = D.today_view(_PERSONA)
    titles = [r["title"] for r in view["blocks"]]
    assert "Alex to vote — anything needed from you?" in titles, titles
    assert "childcare: Admissions evening" in titles, titles
    assert not any("Happy Hour" in t for t in titles), titles
    assert not any("Book club" == t for t in titles), titles
    assert any("New calendar" in n for n in view["notes"]), view["notes"]


# --- D3, F4, F9: the monthly window ---------------------------------------------------------

def _bill(**kw):
    return O._norm({"id": "ob_bill", "what": "Pay the card bill", "kind": "habit", "every": "month",
                    "on_days": [10, 11, 12, 13, 14, 15], "status": "open", "start": "2026-09-01",
                    **kw})


@check("F4: a windowed monthly habit — nothing before the 10th, planned the 10th–15th, due on "
       "the 15th, overdue after it; essential unless missable")
def _():
    _fresh("window")
    t = _bill()
    v9, v12 = O._view(t, date(2026, 10, 9)), O._view(t, date(2026, 10, 12))
    v15, v16 = O._view(t, date(2026, 10, 15)), O._view(t, date(2026, 10, 16))
    assert not v9["actionable"] and not O._on_todays_list(t, v9), v9
    assert v12["state"] == "due_today" and O._on_todays_list(t, v12), v12
    assert "due today" in v15["text"], v15
    assert v16["state"] == "overdue" and O._on_todays_list(t, v16), v16
    assert O.is_essential(t) and not O.is_essential(_bill(stakes="missable"))
    late = _bill(start="2026-10-24")                      # set up after October's window closed
    assert not O._view(late, date(2026, 10, 25))["actionable"]


@check("F9: monthly days and set_days exist only with ledger_fields on; set_days is the user's "
       "own word only; the reschedule error names only what exists")
def _():
    _fresh("set_days")
    C._OVERRIDE = {"flags": {"ledger_fields": False}}
    out = O.open_task("Pay the card bill", kind="habit", every="month", on_days=["10-15"])
    assert out.startswith("error") and "weekday names" in out, out
    tid = O.open_task("Pay the card bill", kind="habit", every="month").split()[1]
    assert O.update_task(tid, "set_days", on_days=["10-15"], evidence="by the 15th").startswith("error")
    err = O.update_task(tid, "reschedule", new_due="2026-11-10", evidence="x")
    assert "set_days" not in err and "dismiss it and open it again" in err, err
    C._OVERRIDE = {"flags": {"ledger_fields": True}}
    assert "set_days" in O.update_task(tid, "reschedule", new_due="2026-11-10", evidence="x")
    from tools import turn_context as T
    with T.turn_scope(user_turn=False):
        out = O.update_task(tid, "set_days", on_days=["10-15"], evidence="by the 15th")
    assert out.startswith("error: not recorded"), out
    assert O.update_task(tid, "set_days", on_days=["10-15"], evidence="").startswith("error")
    out = O.update_task(tid, "set_days", on_days=["10-15"], evidence="pay it by the 15th")
    assert "the 10th to the 15th" in out, out
    t = next(O._norm(x) for x in O._load() if x["id"] == tid)
    assert t["on_days"] == [10, 11, 12, 13, 14, 15], t


# --- answer_event (built now, granted in Stage B) -------------------------------------------

@check("answer_event: the user's word turns a hold into a childcare duty; a scheduled turn "
       "cannot; three alike answers offer a standing rule, never apply one")
def _():
    d, ids = _ready("answer")
    D.current(_PERSONA)
    from tools import turn_context as T
    with T.turn_scope(user_turn=False):
        out = D.answer_event("u-vote@2026-10-27T10:00:00", "needs_me", evidence="x", duty="childcare")
    assert out.startswith("error: not recorded"), out
    assert D.answer_event("u-nope", "there", evidence="x").startswith("error")
    out = D.answer_event("u-vote@2026-10-27T10:00:00", "needs_me", duty="childcare",
                         evidence="I'll have the kids while Alex votes", scope="this_one")
    assert out.startswith("recorded"), out
    plan = D.current(_PERSONA)
    assert plan["trigger"] == "repair" and "an event was answered" in plan["reasons"], plan["reasons"]
    # A school morning: the children are not home, so the answer needs nothing of the user then
    # ("Childcare is only if the boys aren't at their respective schools and not asleep").
    vote = next(b for b in plan["blocks"] if b.get("key") == "u-vote@2026-10-27T10:00:00")
    assert vote["kind"] == "context" and vote.get("note") == "no childcare needed then", vote
    assert plan["failures"] == [], plan["failures"]
    assert D.rule_proposals() == []
    data = D._event_answers()
    for uid, title in (("u-a", "Alex at the dentist"), ("u-b", "Alex at book club"),
                       ("u-c", "Alex out for drinks")):
        data.setdefault("series", {})[uid] = {"answer": "needs_me", "duty": "childcare",
                                              "title": title}
    D._write_json(D._answers_path(), data)
    props = D.rule_proposals()
    assert props and "“alex”" in props[0] and "childcare" in props[0], props
    assert DS.read_shape().get("event_rules") == _SHAPE_RULES       # proposed, not applied


@check("activity on a task: hidden and ignored with ledger_fields off; validated, and it wins "
       "over the domain, with it on")
def _():
    _fresh("activity_field")
    C._OVERRIDE = {"flags": {"ledger_fields": False}}
    tid = O.open_task("Pay the card bill", kind="deadline", due="2026-10-27",
                      activity="admin").split()[1]
    assert not O._norm(next(t for t in O._load() if t["id"] == tid)).get("activity")
    assert O.update_task(tid, "set_activity", activity="admin").startswith("error")
    C._OVERRIDE = {"flags": {"build": True, "ledger_fields": True}}
    assert O.update_task(tid, "set_activity", activity="nonsense").startswith("error")
    assert "activity set to 'admin'" in O.update_task(tid, "set_activity", activity="admin")
    c = next(c for c in D._candidates(date(2026, 10, 27), _PERSONA) if c["task_id"] == tid)
    assert c["activity"] == "admin" and c["device"] and c["heavy"], c


# --- setup ----------------------------------------------------------------------------------

@check("setup: calendar names resolve to ids, unnamed ones default to the user's, the writable "
       "one is always theirs; an unknown name writes nothing")
def _():
    d = _fresh("setup", shape="")
    cals = [{"id": "/cal/mt", "name": "Metatron", "writable": True},
            {"id": "/cal/main", "name": "Main", "writable": False},
            {"id": "/cal/fam", "name": "Family", "writable": False},
            {"id": "/cal/hol", "name": "Holidays", "writable": False}]
    written, errors = DS.apply_baseline({"calendars": {"Nope": "family"}}, cals)
    assert errors and DS.roster() == {}, (errors, DS.roster())
    written, errors = DS.apply_baseline(
        {"calendars": {"Family": "family", "Metatron": "feed"},
         "day": [{"days": "all", "wake": "07:00", "bed": "23:00"}]}, cals)
    assert errors == [], errors
    assert DS.roster() == {"/cal/mt": {"name": "Metatron", "role": "mine"},
                           "/cal/main": {"name": "Main", "role": "mine"},
                           "/cal/fam": {"name": "Family", "role": "family"},
                           "/cal/hol": {"name": "Holidays", "role": "mine"}}, DS.roster()
    hist = DS.read_shape().get("history") or []
    assert hist and all(h["evidence"] == DS.SETUP_EVIDENCE for h in hist)


@check("set_day_shape: a model's write needs the user's turn and their words; entries are "
       "validated; a preferred and a strong window at the same hour are two entries")
def _():
    _fresh("writer", shape="")
    from tools import turn_context as T
    with T.turn_scope(user_turn=False):
        assert DS.set_day_shape("day", {"wake": "07:00"}, evidence="x").startswith("error: not recorded")
    assert DS.set_day_shape("day", {"wake": "07:00"}, evidence="").startswith("error")
    assert DS.set_day_shape("windows", {"activity": "nonsense", "from": "10:00", "to": "11:00"},
                            evidence="x").startswith("error")
    for strength in ("preferred", "strong"):
        assert DS.set_day_shape("windows", {"activity": "admin", "days": "mon-fri", "from": "10:00",
                                            "to": "15:00" if strength == "preferred" else "17:30",
                                            "strength": strength},
                                evidence="admin by day").startswith("recorded")
    assert len(DS.read_shape()["windows"]) == 2, DS.read_shape()["windows"]
    s = DS.shape_for(date(2026, 10, 27))
    assert {w["strength"] for w in s["windows"]} == {"preferred", "strong"}


def main() -> int:
    for name, ok, why in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if not ok:
            print("        " + why.replace("\n", "\n        "))
    failed = sum(1 for _, ok, _ in _results if not ok)
    print(f"\n{len(_results) - failed} passed, {failed} failed, {len(_results)} total")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
