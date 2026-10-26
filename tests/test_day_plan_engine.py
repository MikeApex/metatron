"""
tests/test_day_plan_engine.py — the day planner's engine (tools/day_plan.py), against a
synthetic day. Plan: archive/plans/day_planner_plan_2026-10-24.md § 11.1.

EVERY LIVE METER IS STUBBED (the standing rule): CalDAV (`_query_events`), Google Routes
(`get_travel_time`), the model (`_MODEL_CALL`), the server (`send_one`). No persona data — a temp
directory per check. Run it, do not read it:

    python3 tests/test_day_plan_engine.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import threading
import time as _t
from datetime import date, datetime, timedelta
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
_TMP = Path(tempfile.mkdtemp(prefix="day_plan_engine_"))
_CLOCK = {"now": datetime(2026, 10, 26, 8, 0)}
O._now = lambda: _CLOCK["now"]
A._get_timezone = lambda: "Europe/London"
_PERSONA = "dp_test"

_GOALS = """quarterly:
- id: q1
  title: Ship the Apex migration
  status: active
  essential: true
- id: q2
  title: Learn the guitar
  status: active
"""
_SHAPE = """wake: "07:00"
bed: "23:00"
work_days: [mon, tue, wed, thu, fri]
work_start: "09:00"
work_end: "17:30"
focus: ["09:00-11:30"]
personal: ["19:30-21:00"]
"""

# The day: Monday 26 October 2026.
_EVENTS = [
    {"uid": "u-standup", "title": "Stand-up", "start": "2026-10-26T10:00:00",
     "end": "2026-10-26T10:30:00", "location": "https://meet.google.com/abc-defg", "status": ""},
    {"uid": "u-lunch", "title": "Lunch", "start": "2026-10-26T12:30:00",
     "end": "2026-10-26T13:15:00", "location": "", "status": ""},
    {"uid": "u-physio", "title": "Physio", "start": "2026-10-26T14:00:00",
     "end": "2026-10-26T15:00:00", "location": "12 Harley St, London", "status": ""},
    {"uid": "u-sync", "title": "Team sync", "start": "2026-09-07T16:00:00",
     "end": "2026-09-07T16:30:00", "location": "", "status": "",
     "occurs_in_range": ["2026-10-26T16:00:00"]},
    {"uid": "u-hol", "title": "Bank holiday (test)", "start": "2026-10-26T00:00:00",
     "end": "2026-10-27T00:00:00", "location": "", "status": ""},
    {"uid": "u-gone", "title": "Cancelled thing", "start": "2026-10-26T18:00:00",
     "end": "2026-10-26T18:30:00", "location": "", "status": "CANCELLED"},
]
_CALLS = {"caldav": 0, "caldav_threads": [], "routes": 0, "send": []}


def _query_events(start, end, persona=None, calendars="own"):
    _CALLS["caldav"] += 1
    _CALLS["caldav_threads"].append(threading.current_thread().name)
    _t.sleep(_CALLS.get("caldav_delay", 0))
    return {"events": json.loads(json.dumps(_EVENTS_NOW["v"]))}


_EVENTS_NOW = {"v": _EVENTS}
CAL._query_events = _query_events


def _route(origin, destination, mode="transit", arrive_by=""):
    _CALLS["routes"] += 1
    return {"journeys": [{"duration_minutes": 25}]}


R.get_travel_time = _route
L.load_zones = lambda persona=None: [{"name": "home", "lat": 51.5, "lon": -0.12, "radius_m": 100},
                                     {"name": "gym", "lat": 51.51, "lon": -0.1, "radius_m": 80}]
L.current_zone = lambda persona=None: {"zone": "home", "entered_at": "2026-10-25T21:00:00"}


def _fresh(name: str) -> Path:
    # A background refresh started by the previous check must finish before the store moves
    # under it, or it writes that check's plan into this one's directory.
    for th in threading.enumerate():
        if th.name.startswith("day_plan_"):
            th.join(5)
    d = _TMP / name
    (d / "config").mkdir(parents=True, exist_ok=True)
    for mod in (O, D, DS, L):
        mod.persona_data_dir = lambda persona=None, _d=d: _d
    DS.persona_config_dir = lambda persona=None, _d=d: _d / "config"
    (d / "config" / "goals.yaml").write_text(_GOALS)
    G._goals_path = lambda _d=d: _d / "config" / "goals.yaml"
    (d / "day_shape.yaml").write_text(_SHAPE)
    C._OVERRIDE = {"flags": {"ledger_fields": True}}   # the fixtures use the planner's fields
    D._MODEL_CALL = None
    _EVENTS_NOW["v"] = _EVENTS
    _CALLS.update(caldav=0, caldav_threads=[], routes=0, send=[], caldav_delay=0)
    _CLOCK["now"] = datetime(2026, 10, 26, 8, 0)
    return d


def _flags(**on):
    C._OVERRIDE = {"flags": {"build": True, "show_in_app": True, "ledger_fields": True, **on}}


def _tasks():
    ids = {}
    ids["runbook"] = O.open_task("Draft migration runbook", kind="deadline", due="2026-10-26",
                                 goal_id="q1", domain="work", minutes=90, minutes_source="stated")
    ids["card"] = O.open_task("Buy a birthday card", kind="deadline", due="2026-10-26",
                              stakes="missable", minutes=20)
    ids["meds"] = O.open_task("Take the tablets", kind="habit", every="day", times=2, minutes=5)
    ids["gym"] = O.open_task("Gym", kind="habit", every="week", times=3,
                             on_days=["mon", "wed", "fri"], minutes=60, zone="gym")
    ids["wait"] = O.open_task("Reply from Bupa", kind="waiting", waiting_on="Bupa")
    return {k: v.split()[1] for k, v in ids.items()}


def _ready(name: str):
    d = _fresh(name)
    ids = _tasks()
    D.refresh_snapshot(_PERSONA)
    _CALLS["caldav"] = 0
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
            D._MODEL_CALL = None
        return fn
    return deco


def _blocks(plan, kind=None):
    return [b for b in plan["blocks"] if kind is None or b["kind"] == kind]


def _hm(s):
    return s[11:16]


# --- the build -------------------------------------------------------------------------------

@check("a fixture day builds clean: events in place, travel before the located one, no failures")
def _():
    d, ids = _ready("build")
    plan = D.current(_PERSONA)
    assert plan and plan["failures"] == [], plan and plan["failures"]
    ev = {b["title"]: b for b in _blocks(plan, "event")}
    assert _hm(ev["Stand-up"]["start"]) == "10:00" and _hm(ev["Physio"]["start"]) == "14:00"
    assert "Team sync" in ev and _hm(ev["Team sync"]["start"]) == "16:00"   # recurring, on its day
    assert "Bank holiday (test)" not in ev and "Cancelled thing" not in ev  # all-day, cancelled
    assert [b["title"] for b in _blocks(plan, "own")] == ["Lunch"]
    tr = {b["id"].split(":")[0]: b for b in _blocks(plan, "travel")}
    assert set(tr) == {"travel", "travel_home"}, tr
    assert tr["travel"]["end"].endswith("14:00") and _hm(tr["travel"]["start"]) == "13:25", tr
    # Home again after physio — nothing located follows within two hours (S-5).
    assert _hm(tr["travel_home"]["start"]) == "15:00" and _hm(tr["travel_home"]["end"]) == "15:25", tr
    assert not any(b["title"] == "lunch" for b in _blocks(plan, "meal"))   # the calendar has one
    assert any(b["title"] == "breakfast" for b in _blocks(plan, "meal"))


@check("the fill: vital work in the work window, missable kept out of protected time, two doses ≥3 h apart")
def _():
    d, ids = _ready("fill")
    plan = D.current(_PERSONA)
    tasks = {}
    for b in _blocks(plan, "task"):
        tasks.setdefault(b["task_id"], []).append(b)
    rb = tasks[ids["runbook"]][0]
    assert "09:00" <= _hm(rb["start"]) and _hm(rb["end"]) <= "17:30", rb
    card = tasks[ids["card"]][0]
    assert not ("19:30" <= _hm(card["start"]) < "21:00"), card
    doses = sorted(_hm(b["start"]) for b in tasks[ids["meds"]])
    assert len(doses) == 2, doses
    a, b = (datetime.strptime(x, "%H:%M") for x in doses)
    assert b - a >= timedelta(hours=3), doses
    assert ids["wait"] not in tasks                         # someone else's move, never placed
    assert plan["unplaced"] == [] or all(u["reason"] for u in plan["unplaced"])


@check("suggestions: a leave-now nudge for travel; nudges and checks for essential blocks only")
def _():
    d, ids = _ready("suggest")
    plan = D.current(_PERSONA)
    sug = plan["suggestions"]
    assert any(s["kind"] == "nudge" and s["at"].endswith("13:25") and "leave" in s["why"]
               for s in sug), sug
    checked = {s["ref"].split("@")[0] for s in sug if s["kind"] == "check"}
    assert ids["runbook"] in checked and ids["meds"] in checked, checked
    assert ids["card"] not in checked and ids["gym"] not in checked, checked


@check("the plan file holds digests and scores, never task state (R1-3)")
def _():
    d, ids = _ready("no_copy")
    D.current(_PERSONA)
    raw = (d / "day_plan" / "plan_2026-10-26.json").read_text()
    plan = json.loads(raw)
    for ref, val in plan["digests"]["tasks"].items():
        assert isinstance(val, list) and len(val) == 2 and isinstance(val[1], int), val
    for b in _blocks(plan, "task"):
        assert "status" not in b and "evidence" not in b and "done" not in b, b


# --- the gate --------------------------------------------------------------------------------

@check("the gate: nothing changed → the stored plan; done/length/note → repair; added/priority → reshuffle")
def _():
    d, ids = _ready("gate")
    p1 = D.current(_PERSONA)
    p2 = D.current(_PERSONA)
    assert p2["built_at"] == p1["built_at"]                              # none
    O.update_task(ids["card"], "set_minutes", minutes=25, minutes_source="stated")
    p3 = D.current(_PERSONA)
    assert p3["trigger"] == "repair", (p3["trigger"], p3["reasons"])
    O.update_task(ids["card"], "done", evidence="bought it")
    p4 = D.current(_PERSONA)
    assert p4["trigger"] == "repair", (p4["trigger"], p4["reasons"])
    O.open_task("Book the boiler service", kind="deadline", due="2026-10-26", minutes=10)
    p5 = D.current(_PERSONA)
    assert p5["trigger"] == "reshuffle", (p5["trigger"], p5["reasons"])
    O.update_task(ids["gym"], "set_priority", priority="high", priority_source="stated")
    p6 = D.current(_PERSONA)
    assert p6["trigger"] == "reshuffle", (p6["trigger"], p6["reasons"])
    assert p6["failures"] == [], p6["failures"]


@check("a moved calendar event is a repair; the stand-up moving keeps the other placements")
def _():
    d, ids = _ready("moved")
    p1 = D.current(_PERSONA)
    before = {b["ref"]: b["start"] for b in _blocks(p1, "task")}
    moved = json.loads(json.dumps(_EVENTS))
    moved[0]["start"], moved[0]["end"] = "2026-10-26T15:30:00", "2026-10-26T16:00:00"
    _EVENTS_NOW["v"] = moved
    D.refresh_snapshot(_PERSONA)
    p2 = D.current(_PERSONA)
    assert p2["trigger"] == "repair" and p2["failures"] == [], (p2["trigger"], p2["failures"])
    after = {b["ref"]: b["start"] for b in _blocks(p2, "task")}
    kept = sum(1 for r in before if after.get(r) == before[r])
    assert kept >= len(before) - 2, (before, after)


@check("time passing: earlier blocks become history; an essential block passing undone reshuffles once")
def _():
    d, ids = _ready("passing")
    p1 = D.current(_PERSONA)
    first = sorted(_blocks(p1, "task"), key=lambda b: b["start"])[0]
    _CLOCK["now"] = datetime.fromisoformat(first["end"]) + timedelta(minutes=1)
    D.refresh_snapshot(_PERSONA)
    p2 = D.current(_PERSONA)
    hist = [b for b in p2["blocks"] if b.get("history")]
    assert any(b["id"] == first["id"] for b in hist), hist
    if first.get("essential"):
        assert p2["trigger"] == "reshuffle", p2["trigger"]
        p3 = D.current(_PERSONA)
        assert p3["built_at"] == p2["built_at"] or p3["trigger"] != "reshuffle"


@check("a midnight-crossing day keeps its post-midnight blocks through V5 (R1-7)")
def _():
    d = _fresh("midnight")
    (d / "day_shape.yaml").write_text('wake: "10:00"\nbed: "02:30"\n')
    _CLOCK["now"] = datetime(2026, 10, 26, 12, 0)
    O.update_task("settings", "day_starts", note="04:00")
    O.open_task("Write the essay", kind="deadline", due="2026-10-26", minutes=30)
    _EVENTS_NOW["v"] = []
    D.refresh_snapshot(_PERSONA)
    _CLOCK["now"] = datetime(2026, 10, 27, 0, 45)
    plan = D.current(_PERSONA)
    assert plan["day"] == "2026-10-26", plan["day"]
    assert plan["window"]["bed"] == "2026-10-27T02:30", plan["window"]
    assert plan["failures"] == [], plan["failures"]
    # Placed after midnight, before the 01:30 wind-down (a deadline never goes in wind-down).
    late = [b for b in _blocks(plan, "task") if b["start"] >= "2026-10-27T00:45"]
    assert late and all(b["end"] <= "2026-10-27T01:30" for b in late), _blocks(plan, "task")


# --- where a network call may run (R1-8, V1-N1, V2-N1) ----------------------------------------

@check("a stale read starts ONE background refresh, returns without waiting, and the snapshot lands")
def _():
    d = _fresh("stale")
    _tasks()                       # opening a deadline makes the ledger's own calendar-link read
    _CALLS.update(caldav=0, caldav_threads=[])
    _CALLS["caldav_delay"] = 0.3
    t0 = _t.monotonic()
    D.current(_PERSONA, for_reply=True)
    D.current(_PERSONA, for_reply=True)                      # second stale read: starts nothing
    elapsed = _t.monotonic() - t0
    assert elapsed < 0.25, f"the read waited {elapsed:.2f}s on the calendar"
    for _ in range(100):
        if (D._load_state(_PERSONA).get("snapshot") or {}).get("events"):
            break
        _t.sleep(0.05)
    snap = D._load_state(_PERSONA).get("snapshot") or {}
    assert snap.get("events"), "the background refresh never landed (unbound worker?)"
    assert _CALLS["caldav"] == 1, _CALLS["caldav"]
    assert all(n.startswith("day_plan_") for n in _CALLS["caldav_threads"]), _CALLS["caldav_threads"]


@check("a reply turn that wrote nothing makes zero synchronous CalDAV calls")
def _():
    d, ids = _ready("no_sync")
    D.current(_PERSONA)
    _CLOCK["now"] = datetime(2026, 10, 26, 8, 30)          # snapshot now 30 min old: stale
    main = threading.current_thread().name
    _CALLS["caldav_threads"] = []
    D.current(_PERSONA, for_reply=True)
    assert main not in _CALLS["caldav_threads"], _CALLS["caldav_threads"]


@check("a turn that wrote the calendar re-fetches inside the 3 s box")
def _():
    d, ids = _ready("boxed")
    D.current(_PERSONA)
    from tools import turn_context as T
    with T.turn_scope(user_turn=True):
        D.note_calendar_write(_PERSONA)
        moved = json.loads(json.dumps(_EVENTS))
        moved[2]["start"], moved[2]["end"] = "2026-10-26T15:00:00", "2026-10-26T16:00:00"
        _EVENTS_NOW["v"] = moved
        plan = D.current(_PERSONA, for_reply=True)
    phys = next(b for b in _blocks(plan, "event") if b["title"] == "Physio")
    assert _hm(phys["start"]) == "15:00", phys


@check("with the lock held elsewhere, a reply repair returns in <200 ms+ and writes nothing")
def _():
    d, ids = _ready("lock")
    p1 = D.current(_PERSONA)
    O.update_task(ids["card"], "set_minutes", minutes=25, minutes_source="stated")
    import fcntl
    fh = open(d / "day_plan" / ".lock", "a+")
    fcntl.flock(fh, fcntl.LOCK_EX)
    try:
        holder = {}

        def other():
            t0 = _t.monotonic()
            holder["plan"] = D.current(_PERSONA, for_reply=True)
            holder["s"] = _t.monotonic() - t0
        th = threading.Thread(target=lambda: P.persona_scope(_PERSONA).__enter__() and other())
        th.start()
        th.join(5)
        assert holder.get("s") is not None and holder["s"] < 0.6, holder.get("s")
        on_disk = json.loads((d / "day_plan" / "plan_2026-10-26.json").read_text())
        assert on_disk["built_at"] == p1["built_at"]          # nothing written
    finally:
        fcntl.flock(fh, fcntl.LOCK_UN)
        fh.close()


@check("travel lookups are cached, capped per day, and never made on the reply path")
def _():
    d, ids = _ready("travel")
    D.current(_PERSONA)                                     # background-shaped build: may look up
    n = _CALLS["routes"]
    assert n == 2, n                                        # to physio, and home again
    D._read_json(D._travel_path(_PERSONA), {})
    m, est = D._travel_minutes("a", "b", "transit", datetime(2026, 10, 26, 14), _PERSONA, False)
    assert est and _CALLS["routes"] == n                    # reply path: assumed, no call
    C._OVERRIDE = {"limits": {"travel_lookups_per_day": 1}}
    m, est = D._travel_minutes("c", "d", "transit", datetime(2026, 10, 26, 15), _PERSONA, True)
    assert est and _CALLS["routes"] == n, (_CALLS["routes"], est)   # capped


@check("routing: a naive arrive_by is read in the persona's timezone and sent as UTC")
def _():
    from tools.routing import _utc_rfc3339
    assert _utc_rfc3339(datetime(2026, 10, 24, 16, 15)) == "2026-10-24T15:15:00Z"   # BST
    assert _utc_rfc3339(datetime(2026, 11, 2, 16, 15)) == "2026-11-02T16:15:00Z"    # GMT


# --- the model reshuffle (Stage B code, injected model) ----------------------------------------

def _model_ready(name):
    d, ids = _ready(name)
    _flags(reshuffle_model=True)
    plan = D.current(_PERSONA)
    st = D._load_state(_PERSONA)
    st.setdefault("reshuffle", {})["pending"] = {"day": "2026-10-26", "reason": ["test"]}
    D._write_json(D._state_path(_PERSONA), st)
    return d, ids, plan


def _run_worker():
    assert D.start_reshuffle(_PERSONA)
    for th in threading.enumerate():
        if th.name == "day_plan_reshuffle":
            th.join(5)


@check("a valid model reply is merged onto the current skeleton, validated and applied")
def _():
    d, ids, plan = _model_ready("model_ok")
    gym = next(b for b in _blocks(plan, "task") if b["task_id"] == ids["gym"])
    D._MODEL_CALL = lambda payload: json.dumps({"placements": [
        {"ref": gym["ref"], "start": "2026-10-26T17:30", "end": "2026-10-26T18:30"}],
        "drop": [], "note": "gym after work"})
    _run_worker()
    p = json.loads((d / "day_plan" / "plan_2026-10-26.json").read_text())
    assert p["mode"] == "model" and p["failures"] == [], (p["mode"], p["failures"])
    g = next(b for b in _blocks(p, "task") if b["task_id"] == ids["gym"])
    assert _hm(g["start"]) == "17:30", g
    rows = [json.loads(x) for x in (d / "day_plan" / "log.jsonl").read_text().splitlines()]
    assert any(r["event"] == "reshuffle" and r["outcome"] == "applied" for r in rows)


@check("an unparseable, invented-ref or refused model reply leaves the code plan standing")
def _():
    for case, fn in (("junk", lambda p: "I think the day looks fine!"),
                     ("invented", lambda p: json.dumps({"placements": [
                         {"ref": "ob_999999_ffffff@2026-10-26", "start": "2026-10-26T18:00",
                          "end": "2026-10-26T19:00"}]})),
                     ("refused", lambda p: (_ for _ in ()).throw(RuntimeError("spend cap")))):
        d, ids, plan = _model_ready(f"model_{case}")
        D._MODEL_CALL = fn
        _run_worker()
        p = json.loads((d / "day_plan" / "plan_2026-10-26.json").read_text())
        assert p["mode"] == "code", (case, p["mode"])
        st = D._load_state(_PERSONA)
        assert not (st.get("reshuffle") or {}).get("inflight"), (case, st.get("reshuffle"))


@check("the JSON extractor takes the first balanced object, nested and with braces in strings")
def _():
    raw = 'Here: {"placements": [{"ref": "a", "start": "x"}], "note": "use {care}"} trailing {'
    obj = D._extract_json(raw)
    assert obj and obj["placements"][0]["ref"] == "a" and obj["note"] == "use {care}", obj


# --- rendering and the app view --------------------------------------------------------------

@check("the plan block shows the whole day with live statuses, within ~1,000 tokens")
def _():
    d, ids = _ready("render")
    D.current(_PERSONA)
    meds_block = next(b for b in _blocks(D.current(_PERSONA), "task") if b["task_id"] == ids["meds"])
    _CLOCK["now"] = datetime.fromisoformat(meds_block["end"]) + timedelta(minutes=2)
    O.update_task(ids["meds"], "done", evidence="took them")
    D.refresh_snapshot(_PERSONA)
    plan = D.current(_PERSONA)
    text = D.render_block(plan, kind="evening_close", heads_up=True)
    assert "TODAY'S PLAN" in text and "Earlier:" in text and "Now (" in text, text
    assert "Take the tablets" in text and "✓" in text, text
    assert "Physio (calendar)" in text and "leave for Physio" in text, text
    assert "fuller rework" in text, text
    assert len(text) <= 4000, len(text)
    plan["notes"] = ["Planning meeting now overlaps Write the report, already under way"]
    assert "Notes: Planning meeting now overlaps" in D.render_block(plan), "notes not rendered"


@check("today_view: off with show_in_app off; rows with statuses and no ids when on")
def _():
    d, ids = _ready("view")
    C._OVERRIDE = {"flags": {"show_in_app": False, "ledger_fields": True}}
    assert D.today_view(_PERSONA) == {}
    C._OVERRIDE = {"flags": {"ledger_fields": True}}
    v = D.today_view(_PERSONA)
    assert v["blocks"] and v["calendar_read"], v
    assert not any("`" in r["title"] or "ob_" in r["title"] for r in v["blocks"]), v["blocks"]


# --- nudges ----------------------------------------------------------------------------------

def _stub_send(reply: str):
    import core.remote_client as RC

    def send(persona, text, server=None, provider=None, insecure=True, timeout=600.0,
             nudge=False):
        _CALLS["send"].append({"text": text, "nudge": nudge})
        return reply
    RC.send_one = send


def _no_gates():
    D._quiet_now = lambda persona: False
    D._idle_minutes = lambda persona: 500.0
    D._near_fixed = lambda persona: None


@check("nudge_tick: off unless flagged; batches due items into ONE wake; held → no notify")
def _():
    d, ids = _ready("nudge_hold")
    _no_gates()
    assert D.nudge_tick() == "nudges: off"
    _flags(nudges=True)
    plan = D.current(_PERSONA)
    travel = next(s for s in plan["suggestions"] if "leave" in s["why"])
    _CLOCK["now"] = datetime.fromisoformat(travel["at"]) + timedelta(minutes=1)
    _stub_send("   ")
    out = D.nudge_tick()
    assert isinstance(out, str) and "held" in out, out
    assert len(_CALLS["send"]) == 1 and _CALLS["send"][0]["nudge"] is True, _CALLS["send"]
    assert "[HOLD]" in _CALLS["send"][0]["text"]
    assert D.nudge_tick() == "nudges: nothing due"           # handled once


@check("nudge_tick: a spoken nudge returns a notify dict; quiet hours, live chat and the shield hold it")
def _():
    d, ids = _ready("nudge_send")
    _flags(nudges=True)
    plan = D.current(_PERSONA)
    travel = next(s for s in plan["suggestions"] if "leave" in s["why"])
    _CLOCK["now"] = datetime.fromisoformat(travel["at"]) + timedelta(minutes=1)
    _stub_send("Time to head to physio — about 25 minutes on transit.")
    D._quiet_now = lambda persona: True
    assert D.nudge_tick() == "nudges: quiet hours"
    D._quiet_now = lambda persona: False
    D._idle_minutes = lambda persona: 3.0
    assert "mid-conversation" in D.nudge_tick()
    D._idle_minutes = lambda persona: 500.0
    D._near_fixed = lambda persona: "lands 7m from fixed job 'morning_brief'"
    assert "carried" in D.nudge_tick()
    _fresh_state = D._load_state(_PERSONA)
    _fresh_state["handled"] = {}
    D._write_json(D._state_path(_PERSONA), _fresh_state)
    D._near_fixed = lambda persona: None
    out = D.nudge_tick()
    assert isinstance(out, dict) and out["notify"] and "physio" in out["body"], out


@check("empty-day check-in: only with owns_checkins, after 3 h idle, ≤3 a day, today's prompt")
def _():
    d = _fresh("checkin")
    _EVENTS_NOW["v"] = []
    D.refresh_snapshot(_PERSONA)
    _no_gates()
    _flags(nudges=True)
    _stub_send("How's the day going?")
    assert D.nudge_tick() == "nudges: nothing due"           # owns_checkins off
    _flags(nudges=True, owns_checkins=True)
    out = D.nudge_tick()
    assert isinstance(out, dict), out
    assert _CALLS["send"][-1]["nudge"] is False             # today's check-in, full pipeline
    assert D.nudge_tick() == "nudges: nothing due"           # < 3 h since the last
    D._idle_minutes = lambda persona: 60.0
    _CLOCK["now"] += timedelta(hours=4)
    assert D.nudge_tick() == "nudges: nothing due"           # idle too short


# --- the Fable diff review's findings (archive/plans/fable_review_day_planner_stage_a_2026-10-24.md)

def _one_task_day(name, **task):
    d = _fresh(name)
    _EVENTS_NOW["v"] = [e for e in _EVENTS if e["uid"] in ("u-standup",)]
    D.refresh_snapshot(_PERSONA)
    _CALLS.update(caldav=0, routes=0, send=[])
    tid = O.open_task(**task).split()[1]
    return d, tid


@check("S-1: a task under way stays put — one block, at its own time — and its nudge and check each wake once")
def _():
    d, tid = _one_task_day("s1", what="File the VAT return", kind="deadline", due="2026-10-26",
                           minutes=30, minutes_source="stated")
    _no_gates()
    _flags(nudges=True)
    plan = D.current(_PERSONA)
    first = [b for b in _blocks(plan, "task") if b["task_id"] == tid]
    assert len(first) == 1 and first[0]["essential"], first
    start, end = (datetime.fromisoformat(first[0][k]) for k in ("start", "end"))
    _stub_send("Time for the VAT return.")
    _CLOCK["now"] = start + timedelta(minutes=1)
    out1 = D.nudge_tick()
    plan = D.current(_PERSONA)
    now_blocks = [b for b in _blocks(plan, "task") if b["task_id"] == tid]
    assert len(now_blocks) == 1 and now_blocks[0]["start"] == first[0]["start"], now_blocks
    assert isinstance(out1, dict), out1                   # the start nudge woke once
    _CLOCK["now"] = end + timedelta(minutes=1)
    _stub_send("Did the VAT return get filed?")
    out2 = D.nudge_tick()
    assert isinstance(out2, dict) and "check" in _CALLS["send"][-1]["text"], (out2, _CALLS["send"])
    _CLOCK["now"] = end + timedelta(minutes=10)
    assert D.nudge_tick() == "nudges: nothing due"        # each asked once
    assert len(_CALLS["send"]) == 2, _CALLS["send"]


@check("N1, as Mike ruled 2026-10-26: an unconfirmed essential task stays on the plan all morning "
       "— shown once, at its latest time — and wakes twice: one nudge, one check")
def _():
    d, tid = _one_task_day("n1", what="File the VAT return", kind="deadline", due="2026-10-26",
                           minutes=30, minutes_source="stated")
    _no_gates()
    _flags(nudges=True)
    _stub_send("A word about the VAT return.")
    _CLOCK["now"] = datetime(2026, 10, 26, 8, 0)
    D.current(_PERSONA)
    while _CLOCK["now"] < datetime(2026, 10, 26, 12, 0):
        _CLOCK["now"] += timedelta(minutes=5)
        D.refresh_snapshot(_PERSONA)
        D.nudge_tick()
    plan = D.current(_PERSONA)
    blocks = [b for b in _blocks(plan, "task") if b["task_id"] == tid]
    # Still on the plan at noon — it has not expired.
    assert any(not b.get("history") and b["end"] > "2026-10-26T12:00" for b in blocks), \
        [b["start"] for b in blocks]
    shown = [r for r in D.today_view(_PERSONA)["blocks"] if r["title"] == "File the VAT return"]
    assert len(shown) == 1 and not shown[0]["past"], shown          # no trail of past rows
    kinds = [("check" if "check:" in c["text"] else "nudge") for c in _CALLS["send"]]
    assert kinds.count("check") == 1 and kinds.count("nudge") == 1, kinds


@check("S-2: a twice-daily medicine keeps its second dose after the first is recorded, and never plans a third")
def _():
    d, tid = _one_task_day("s2", what="Take the tablets", kind="habit", every="day", times=2,
                           minutes=5)
    plan = D.current(_PERSONA)
    doses = sorted(b["start"] for b in _blocks(plan, "task") if b["task_id"] == tid)
    assert len(doses) == 2, doses
    first_end = datetime.fromisoformat(doses[0]) + timedelta(minutes=5)
    # Recorded: the second dose is still planned, the first shows done.
    _CLOCK["now"] = first_end + timedelta(minutes=2)
    O.update_task(tid, "done", evidence="took them")
    plan = D.current(_PERSONA)
    blocks = sorted((b for b in _blocks(plan, "task") if b["task_id"] == tid), key=lambda b: b["start"])
    assert len(blocks) == 2 and blocks[0].get("history") and not blocks[1].get("history"), blocks
    assert D._status_of(blocks[0]["ref"], blocks[0]["copy"]) == "done"
    assert D._status_of(blocks[1]["ref"], blocks[1]["copy"]) == "open"
    # Not recorded (a fresh day of it): two doses stay two blocks, never three.
    d, tid2 = _one_task_day("s2b", what="Take the tablets", kind="habit", every="day", times=2,
                            minutes=5)
    plan = D.current(_PERSONA)
    first = min(b["start"] for b in _blocks(plan, "task") if b["task_id"] == tid2)
    _CLOCK["now"] = datetime.fromisoformat(first) + timedelta(minutes=7)
    plan = D.current(_PERSONA)
    n = [b for b in _blocks(plan, "task") if b["task_id"] == tid2]
    assert len(n) == 2, n


@check("S-3: a break never lands on a meeting, and a late-evening build passes V7")
def _():
    d = _fresh("s3")
    _EVENTS_NOW["v"] = [{"uid": "u-m", "title": "Planning meeting", "start": "2026-10-26T10:30:00",
                         "end": "2026-10-26T11:00:00", "location": "", "status": ""}]
    D.refresh_snapshot(_PERSONA)
    _CLOCK["now"] = datetime(2026, 10, 26, 9, 0)
    O.open_task("Write the report", kind="deadline", due="2026-10-26", domain="work", minutes=90,
                minutes_source="stated")
    plan = D.current(_PERSONA)
    meeting = (datetime(2026, 10, 26, 10, 30), datetime(2026, 10, 26, 11, 0))
    for b in _blocks(plan, "break"):
        s, e = datetime.fromisoformat(b["start"]), datetime.fromisoformat(b["end"])
        assert not (s < meeting[1] and meeting[0] < e), b
    assert plan["failures"] == [], plan["failures"]
    _CLOCK["now"] = datetime(2026, 10, 26, 23, 30)          # after bed
    O.open_task("Pay the fine", kind="deadline", due="2026-10-25", minutes=10)
    plan = D.current(_PERSONA)
    assert not [f for f in plan["failures"] if f.startswith("V7")], plan["failures"]


@check("S-6: the Today panel poll never looks a route up; S-7a: a forced replan keeps its force")
def _():
    d, ids = _ready("s6")
    D._write_json(D._travel_path(_PERSONA), {})
    _CALLS["routes"] = 0
    D.today_view(_PERSONA)
    assert _CALLS["routes"] == 0, _CALLS["routes"]
    _flags(reshuffle_model=True)
    D.current(_PERSONA)
    D.request_replan("my afternoon fell through")
    D.current(_PERSONA)
    pend = (D._load_state(_PERSONA).get("reshuffle") or {}).get("pending") or {}
    assert pend.get("force") is True, pend


@check("S-7b: the rhythm offer reads the conversations once a day and never waits on the lock")
def _():
    import fcntl
    d = _fresh("s7b")
    conv = d / "conversations"
    conv.mkdir()
    for i in range(10):
        day = date(2026, 10, 26) - timedelta(days=i)
        (conv / f"{day.isoformat()}.jsonl").write_text(json.dumps(
            {"ts": f"{day.isoformat()}T01:20:00", "proactive": False, "user": "x"}) + "\n")
    assert D.rhythm_offer(_PERSONA) is not None
    (conv / "2026-10-26.jsonl").unlink()                    # cached for the day: not re-read
    assert D.rhythm_offer(_PERSONA) is not None
    (d / "day_plan").mkdir(exist_ok=True)
    fh = open(d / "day_plan" / ".lock", "a+")
    fcntl.flock(fh, fcntl.LOCK_EX)
    try:
        t0 = _t.monotonic()
        holder = {}
        th = threading.Thread(target=lambda: (P.persona_scope(_PERSONA).__enter__(),
                                              holder.update(r=D.rhythm_offer(_PERSONA, mark=True))))
        th.start()
        th.join(5)
        assert (_t.monotonic() - t0) < 1.0, _t.monotonic() - t0
    finally:
        fcntl.flock(fh, fcntl.LOCK_UN)
        fh.close()


# --- location evidence (plan § 5.9, R1-4, R1-5, V1-N2) --------------------------------------

def _transitions(d, rows):
    (d / "location_transitions.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))


@check("an arrival in the task's zone during its block files ONE card, says where not how long, and answers the check")
def _():
    d, ids = _ready("evidence")
    O.update_task(ids["gym"], "set_priority", priority="high", priority_source="stated")  # essential → has a check
    plan = D.current(_PERSONA)
    gym = next(b for b in _blocks(plan, "task") if b["task_id"] == ids["gym"])
    arrive = datetime.fromisoformat(gym["start"]) - timedelta(minutes=10)
    # A client stamp arrives as UTC "Z" (stored verbatim); 26 Oct is GMT, so local == UTC.
    _transitions(d, [{"zone": "gym", "entered_at": arrive.strftime("%Y-%m-%dT%H:%M:%S") + "Z"}])
    _CLOCK["now"] = datetime.fromisoformat(gym["end"]) + timedelta(minutes=5)
    D.refresh_snapshot(_PERSONA)
    plan = D.current(_PERSONA)                       # a background-shaped build may file
    props = [p for p in O.pending_proposals() if p.get("source") == "location"]
    assert len(props) == 1 and "gym" in props[0]["basis"], props
    assert "minute" not in props[0]["basis"] and "hour" not in props[0]["basis"], props[0]["basis"]
    assert not any(x["kind"] == "check" and x["ref"].startswith(ids["gym"])
                   for x in plan["suggestions"]), plan["suggestions"]
    D.current(_PERSONA)                              # a second build files nothing more
    assert len([p for p in O.pending_proposals() if p.get("source") == "location"]) == 1


@check("no arrival in the window → no card and the check stays; the reply path never files")
def _():
    d, ids = _ready("no_evidence")
    O.update_task(ids["gym"], "set_priority", priority="high", priority_source="stated")
    plan = D.current(_PERSONA)
    gym = next(b for b in _blocks(plan, "task") if b["task_id"] == ids["gym"])
    _transitions(d, [{"zone": "gym", "entered_at": "2026-10-26T06:00:00"}])   # hours before
    plan = D.current(_PERSONA, reason="moved", for_reply=False)
    assert not [p for p in O.pending_proposals() if p.get("source") == "location"]
    _transitions(d, [{"zone": "gym",
                      "entered_at": (datetime.fromisoformat(gym["start"])).isoformat()}])
    O.update_task(ids["gym"], "set_minutes", minutes=65, minutes_source="stated")  # force a repair
    D.current(_PERSONA, for_reply=True)
    assert not [p for p in O.pending_proposals() if p.get("source") == "location"], "reply path filed"


@check("accepting a location card closes the habit's occurrence for that day, as location evidence")
def _():
    d, ids = _ready("accept")
    tid = ids["gym"]
    ok = O.add_proposal(f"{tid}@2026-W44", basis="You were at the gym at 18:05.",
                        source="location", key="gym@2026-10-26", on_date="2026-10-26")
    assert ok and not O.add_proposal(f"{tid}@2026-W44", basis="again", source="location",
                                     key="gym@2026-10-26", on_date="2026-10-26")
    pid = next(p["proposal_id"] for p in O.pending_proposals() if p.get("source") == "location")
    out = O.resolve_proposal(pid, True)
    assert "1 of 3" in out, out
    t = next(x for x in O._load() if x["id"] == tid)
    occ = t["occurrences"]["2026-W44"]
    assert occ["completions"][-1]["evidence"].startswith("location evidence"), occ


@check("a correspondence proposal with no source still files, shows and closes exactly as before")
def _():
    d, ids = _ready("corr")
    assert O.add_proposal(ids["card"], "env-1", "receipt", received="2026-10-26")
    p = next(x for x in O.pending_proposals() if x["envelope_id"] == "env-1")
    assert p["source"] == "correspondence", p
    assert "correspondence evidence" in O.resolve_proposal(p["proposal_id"], True) or \
        next(x for x in O._load() if x["id"] == ids["card"])["evidence"].startswith("correspondence")
    assert not O.add_proposal(ids["gym"], "env-2", "receipt")          # habits: still refused


# --- the evening, the rhythm, goal time, housekeeping ----------------------------------------

@check("tomorrow's draft is built in the evening only, code-only, and shown on the evening close")
def _():
    d, ids = _ready("draft")
    assert D.tomorrow_draft(_PERSONA, build=True) is None
    _CLOCK["now"] = datetime(2026, 10, 26, 19, 30)
    dr = D.tomorrow_draft(_PERSONA, build=True)
    assert dr and dr["draft"] and dr["day"] == "2026-10-27", dr and dr["day"]
    _CLOCK["now"] = datetime(2026, 10, 27, 8, 0)
    p = D.current(_PERSONA)
    assert p["day"] == "2026-10-27" and not p["draft"], (p["day"], p["draft"])


@check("rhythm: active after midnight on ≥9 of 14 days offers once a fortnight; never with a boundary set")
def _():
    d = _fresh("rhythm")
    conv = d / "conversations"
    conv.mkdir()
    for i in range(10):
        day = date(2026, 10, 26) - timedelta(days=i)
        (conv / f"{day.isoformat()}.jsonl").write_text(json.dumps(
            {"ts": f"{day.isoformat()}T01:20:00", "proactive": False, "user": "x"}) + "\n")
    offer = D.rhythm_offer(_PERSONA, mark=True)
    assert offer and "01:30" in offer, offer
    assert D.rhythm_offer(_PERSONA) is None                 # offered: quiet for a fortnight
    st = D._load_state(_PERSONA)
    st.pop("rhythm_offered")
    D._write_json(D._state_path(_PERSONA), st)
    O.update_task("settings", "day_starts", note="02:00")
    assert D.rhythm_offer(_PERSONA) is None


@check("allocation gaps: goals with no linked habit, and goals changed since their time was set")
def _():
    d, ids = _ready("alloc")
    gaps = {g["id"]: g for g in D.allocation_gaps(_PERSONA)}
    assert set(gaps) == {"q1", "q2"}, gaps
    O.update_task(ids["gym"], "link_goal", goal_id="q2")
    gaps = {g["id"]: g for g in D.allocation_gaps(_PERSONA)}
    assert "q2" not in gaps, gaps
    G.update_goal("update", goal_id="q2", context="now twice a week")
    gaps = {g["id"]: g for g in D.allocation_gaps(_PERSONA)}
    assert gaps.get("q2", {}).get("changed"), gaps


@check("prune drops plan files past retention and log rows past 90 days")
def _():
    d, ids = _ready("prune")
    D.current(_PERSONA)
    old = d / "day_plan" / "plan_2026-10-01.json"
    old.write_text("{}")
    with open(d / "day_plan" / "log.jsonl", "a") as fh:
        fh.write(json.dumps({"at": "2026-06-01T09:00:00", "event": "build"}) + "\n")
    n = D.prune(_PERSONA)
    assert not old.exists() and n >= 2, n
    assert "2026-06-01" not in (d / "day_plan" / "log.jsonl").read_text()


def main() -> int:
    passed = sum(1 for _, ok, _ in _results if ok)
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if detail else ""))
    print(f"\n{passed} passed, {len(_results) - passed} failed, {len(_results)} total")
    return 0 if passed == len(_results) else 1


if __name__ == "__main__":
    sys.exit(main())
