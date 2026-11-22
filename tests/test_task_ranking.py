"""
tests/test_task_ranking.py — ranking, Part A (Mike, 2026-11-22; goal_task_network_plan § 16): every
task is scored; an unjudged one is back burner; the agent that opens a task judges it, and the task
judge judges what it missed against the user's goals and values; required steps of a plan take
their end state's weight; deadlines climb toward their date; the Synthesizer always sees a plan's
current step.

EVERY LIVE METER IS STUBBED (the standing rule): CalDAV, Google Routes, the day_planner model
(refusing), the project_planner and task_judge models (`_MODEL_CALL`, counting stubs), push. No
persona data — a temp directory per check.

    python3 tests/test_task_ranking.py
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
import tools.task_judge as TJ  # noqa: E402

_results: list[tuple[str, bool, str]] = []
_TMP = Path(tempfile.mkdtemp(prefix="task_ranking_"))
TODAY = date.today()
_CLOCK = {"now": datetime.combine(TODAY, time(7, 0))}
O._now = lambda: _CLOCK["now"]
A._get_timezone = lambda: "Europe/London"
_PERSONA = "ranking_a"

CAL._query_events = lambda *a, **k: {"events": [], "discovery": "ok"}
CAL._get_event_by_uid = lambda uid, persona=None: {"error": "offline"}
R.get_travel_time = lambda *a, **k: {"journeys": [{"duration_minutes": 20}]}
L.load_zones = lambda persona=None: []
L.current_zone = lambda persona=None: {}
INTV.holds_proactive = lambda persona: False
D._quiet_now = lambda persona: False
D._idle_minutes = lambda persona: None
_CALLS = {"day_model": 0, "planner": 0, "judge": 0, "send": 0}


def _no_day_model(*a, **k):
    _CALLS["day_model"] += 1
    raise AssertionError("a day_planner model call was made")


D._call_model = _no_day_model
RC.send_one = lambda *a, **k: (_CALLS.__setitem__("send", _CALLS["send"] + 1), "ok")[1]


def _no_planner(payload):
    _CALLS["planner"] += 1
    raise AssertionError("an unexpected project_planner call")


PP._MODEL_CALL = _no_planner

_JUDGE_REPLIES: list = []
_JUDGE_PAYLOADS: list = []


def _judge(payload):
    _CALLS["judge"] += 1
    _JUDGE_PAYLOADS.append(payload)
    if not _JUDGE_REPLIES:
        raise AssertionError("an unexpected task_judge call")
    r = _JUDGE_REPLIES.pop(0)
    return r(payload) if callable(r) else r


TJ._MODEL_CALL = _judge

_FLAGS = {"build": True, "show_in_app": True, "ledger_fields": True, "synth_reads_plan": True,
          "unconfirmed_rule": True, "reshuffle_model": False, "nudges": False,
          "owns_checkins": False, "prep_tasks": True, "horizon_cap": True, "project_planner": True,
          "task_judge": True}


def _d(n: int) -> str:
    return (TODAY + timedelta(days=n)).isoformat()


def _join() -> None:
    for th in threading.enumerate():
        if th.name.startswith("day_plan_"):
            th.join(10)


def _fresh(name: str, flags: dict | None = None, goals: str = "quarterly: []\n",
           score: dict | None = None) -> Path:
    _join()
    d = _TMP / name
    (d / "config").mkdir(parents=True, exist_ok=True)
    for mod in (O, D, DS, L, H):
        mod.persona_data_dir = lambda persona=None, _d=d: _d
    DS.persona_config_dir = lambda persona=None, _d=d: _d / "config"
    TJ.persona_config_dir = lambda persona=None, _d=d: _d / "config"
    (d / "config" / "goals.yaml").write_text(goals)
    (d / "config" / "mission.md").write_text("Raise the boys well; build things that last.\n")
    (d / "config" / "prime_directive.md").write_text("Family first.\n")
    G._goals_path = lambda _d=d: _d / "config" / "goals.yaml"
    G._calling_agent = lambda: ""
    (d / "day_shape.yaml").write_text('day: [{days: all, wake: "07:00", bed: "23:00"}]\n')
    C._OVERRIDE = {"flags": {**_FLAGS, **(flags or {})}, **({"score": score} if score else {})}
    _JUDGE_REPLIES.clear()
    _JUDGE_PAYLOADS.clear()
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


def _id(out: str) -> str:
    return out.split()[1]


def _task(tid: str) -> dict:
    return O._norm(O._find(O._load(None), tid))


def _score(tid: str, day: date | None = None) -> int:
    day = day or TODAY
    t = _task(tid)
    w = C.score_weights()
    return D._score(t, O._view(t, day), day, O._goal_index(), w)


_TAX_GOALS = """\
quarterly:
- id: q5
  title: File UK taxes by Dec 31
  status: active
  due: '{due}'
  kind: obligation
  size: M
  shareable_what: file the self assessment return online
  private_why: SECRET-MOTIVE-NEVER-SENT
  vetted: {{date: '2026-11-21', depth: M, priority: high, by: synthesizer}}
- id: q7
  title: Tidy the loft someday
  status: active
  due: '{due}'
  size: M
  vetted: {{date: '2026-11-21', depth: M, priority: low, by: synthesizer}}
- id: q6
  title: Old free-text vet
  status: active
  due: '{due}'
  size: M
  vetted: {{date: '2026-11-21', depth: M, priority: ahead of Prudential review, by: synthesizer}}
"""


# --- 1. every task is scored; unjudged is back burner -------------------------------------------

@check("1: an UNJUDGED deadline is back burner — not essential, scored as missable, lapsed (not "
       "overdue) past its date; a judged-vital one keeps the old weight")
def _():
    _fresh("unjudged")
    chore = _id(O.open_task("Repot two basement plants", kind="deadline", due=_d(-5)))
    bill = _id(O.open_task("Pay the card bill", kind="deadline", due=_d(-5), stakes="vital"))
    assert not O.is_essential(_task(chore)) and O.is_essential(_task(bill))
    assert O._view(_task(chore), TODAY)["state"] == "lapsed"
    assert O._view(_task(bill), TODAY)["state"] == "overdue"
    assert _score(bill) > _score(chore) + 30, (_score(bill), _score(chore))
    assert "Repot" not in O.context_block() and "Pay the card bill" in O.context_block()


# --- 2. the ramp --------------------------------------------------------------------------------

@check("2: a deadline climbs from the start of its window toward its due-day weight — half-way, "
       "half the weight; a missable one only to its own smaller weight; ramp_days 0 is off")
def _():
    _fresh("ramp", score={"ramp_days": 14})
    vital = _id(O.open_task("Gather the P60", kind="deadline", due=_d(8), eligible_from=_d(0),
                            flexible=True, stakes="vital"))
    light = _id(O.open_task("Buy a nicer folder", kind="deadline", due=_d(8),
                            eligible_from=_d(0), flexible=True, stakes="missable"))
    base_v = _score(vital, TODAY)                    # day 0 of 8: no climb yet (in_lead only)
    half_v = _score(vital, TODAY + timedelta(days=4))
    last_v = _score(vital, TODAY + timedelta(days=7))
    assert half_v - base_v >= 10 and last_v > half_v, (base_v, half_v, last_v)
    assert _score(light, TODAY + timedelta(days=7)) - _score(light, TODAY) <= 10
    # A vital step due in four days now outranks a stale, unjudged chore well before its date.
    chore = _id(O.open_task("Repot two basement plants", kind="deadline", due=_d(-10)))
    assert _score(vital, TODAY + timedelta(days=4)) > _score(chore, TODAY + timedelta(days=4))
    on = _score(vital, TODAY + timedelta(days=4))
    C._OVERRIDE = {"flags": _FLAGS, "score": {"ramp_days": 0}}
    off = _score(vital, TODAY + timedelta(days=4))
    # off: as before 11-22 (in_lead 5); on: the climb, 30·4/8 = 15, replaces it.
    assert off == base_v and on == off + 10, (on, off)


# --- 3. plan steps take their end state's weight ------------------------------------------------

@check("3: required steps of a high-priority obligation are vital and high; an optional step is "
       "missable; a low-priority goal's steps are missable; a stated stakes is never replaced")
def _():
    _fresh("steps", goals=_TAX_GOALS.format(due=_d(30)))
    res = O.open_plan([
        {"key": "a", "what": "Check you can sign in to HMRC", "part_of": "q5", "due": _d(3),
         "eligible_from": _d(0), "flexible": True},
        {"key": "b", "what": "Order a nicer folder", "part_of": "q5", "due": _d(10),
         "required": False, "flexible": True},
        {"key": "c", "what": "Gather the bank statements", "part_of": "q5", "due": _d(12),
         "stakes": "missable", "flexible": True},
    ])
    assert res["ok"], res
    a, b, c = (_task(res["ids"][k]) for k in "abc")
    assert (a["stakes"], a["priority"]) == ("vital", "high"), a
    assert b["stakes"] == "missable" and c["stakes"] == "missable" and c["stakes_source"] == "stated"
    low = O.open_plan([{"key": "x", "what": "Sort the loft boxes", "part_of": "q7", "due": _d(5)}])
    assert _task(low["ids"]["x"])["stakes"] == "missable"
    old = O.open_plan([{"key": "y", "what": "Old plan step", "part_of": "q6", "due": _d(5)}])
    y = _task(old["ids"]["y"])
    assert y["stakes"] == "vital" and not y.get("priority"), y   # free text reads as no priority


@check("3b: the daily reweigh brings steps written under the old rule up to the new one, leaves a "
       "stated value alone, and gives an unstaked code prep vital stakes")
def _():
    _fresh("reweigh", goals=_TAX_GOALS.format(due=_d(30)))
    res = O.open_plan([{"key": "a", "what": "Check you can sign in to HMRC", "part_of": "q5",
                        "due": _d(3)},
                       {"key": "b", "what": "Gather the P60", "part_of": "q5", "due": _d(9),
                        "stakes": "missable"}])
    prep = O.open_plan([{"what": "Pack the Red Book", "prep_for": {"finding": "x"}, "due": _d(0)}])
    a, b, p = res["ids"]["a"], res["ids"]["b"], prep["ids"][next(iter(prep["ids"]))]

    def rewrite(doc):                                # what 11-21's plan wrote
        for t in doc["tasks"]:
            if t["id"] == a:
                t.update(stakes="missable", stakes_source="inferred")
                t.pop("priority", None)
                t.pop("priority_source", None)
            if t["id"] == p:
                t.pop("stakes", None)
                t.pop("stakes_source", None)
    O._with_store(None, rewrite)
    # An ordinary pass: the prep, and `a`'s missing priority — but not R5's `inferred` stakes.
    assert O.reweigh_plan_steps() == 2
    assert (_task(a)["stakes"], _task(a)["priority"]) == ("missable", "high")
    assert O.reweigh_plan_steps(legacy=True) == 1                 # the one-time migration
    assert (_task(a)["stakes"], _task(a)["priority"]) == ("vital", "high")
    assert _task(a)["stakes_source"] == "plan"
    assert _task(b)["stakes"] == "missable"                       # stated: untouched
    assert _task(p)["stakes"] == "vital" and O.is_essential(_task(p))
    assert O.reweigh_plan_steps() == 0                            # idempotent
    # What the Synthesizer records from the user's words is never undone (Fable #2).
    O.update_task(a, "set_stakes", stakes="missable")
    O.update_task(a, "set_priority", priority="low")
    # (the daily pass; `legacy` runs once, on the first tick after the deploy, before any)
    assert O.reweigh_plan_steps() == 0
    assert (_task(a)["stakes"], _task(a)["priority"]) == ("missable", "low")


@check("3c: the tick reweighs once a day — and the first tick after a deploy does it the same day")
def _():
    _fresh("reweigh_tick", goals=_TAX_GOALS.format(due=_d(30)))
    res = O.open_plan([{"key": "a", "what": "Check you can sign in to HMRC", "part_of": "q5",
                        "due": _d(3)}])
    O._with_store(None, lambda doc: [t.update(stakes="missable", stakes_source="inferred")
                                     for t in doc["tasks"]])
    st = D._load_state(_PERSONA)
    st["last_day"] = TODAY.isoformat()                            # the day already started
    D._write_json(D._state_path(_PERSONA), st)
    out = D.refresh_tick()
    assert "1 plan step(s) reweighed" in out, out
    assert _task(res["ids"]["a"])["stakes"] == "vital"
    assert "reweighed" not in D.refresh_tick()


# --- 4. vetting records a priority every score can read -----------------------------------------

@check("4: vet's priority is high, normal or low — free text is refused, nothing changed; kind "
       "obligation is recorded at vet")
def _():
    _fresh("vet")
    G._calling_agent = lambda: "synthesizer"
    out = G.update_goal("add", horizon="quarterly", title="File UK taxes", due=_d(30))
    assert "error" not in out.lower(), out
    gid = next(g for g in O._goal_index() if O._goal_index()[g]["title"] == "File UK taxes")
    bad = G.update_goal("vet", goal_id=gid, verdict="active", size="M",
                        priority="ahead of Prudential review")
    assert bad.startswith("Error") and O._goal_index()[gid]["status"] == "proposed", bad
    ok = G.update_goal("vet", goal_id=gid, verdict="active", size="M", priority="High",
                       displaces="the Prudential review", kind="obligation")
    O._GOAL_CACHE.update(key=None)
    g = O._goal_index()[gid]
    assert "taken on" in ok and g["vetted"]["priority"] == "high" and g["kind"] == "obligation", g
    assert O._goal_priority(g) == "high"


# --- 5. the task judge --------------------------------------------------------------------------

def _verdicts(pairs):
    return lambda payload: json.dumps({"tasks": [
        {"id": t["id"], **pairs.get(t["what"], {"stakes": "missable", "priority": "low",
                                                "why": "nothing much"})}
        for t in payload["tasks"]]})


@check("5: the judge sees only unjudged deadlines — never plan steps, code preps, waiting tasks "
       "or plain habits; a chat task linked to an event is judged; goals go without private_why")
def _():
    _fresh("judge_scope", goals=_TAX_GOALS.format(due=_d(30)))
    plain = _id(O.open_task("Repot two basement plants", kind="deadline", due=_d(-5)))
    _id(O.open_task("Pay the card bill", kind="deadline", due=_d(2), stakes="vital"))
    _id(O.open_task("Reply from Bupa", kind="waiting", waiting_on="Bupa"))
    _id(O.open_task("Stretching", kind="habit", every="day"))
    O.open_plan([{"key": "a", "what": "Check you can sign in", "part_of": "q5", "due": _d(3)}])
    O.open_plan([{"what": "Pack the Red Book", "prep_for": {"finding": "x"}, "due": _d(0)}])
    chat = _id(O.open_task("Buy a card for Sam's party", kind="deadline", due=_d(1)))
    O._with_store(None, lambda doc: [t.update(prep_for={"uid": "u1", "chat": "1"})
                                     for t in doc["tasks"] if t["id"] == chat])
    ids = {t["id"] for t in TJ.unjudged()}
    assert ids == {plain, chat}, ids
    p = TJ._payload(TJ.unjudged(), _PERSONA)
    text = json.dumps(p)
    assert "SECRET-MOTIVE" not in text and "private_why" not in text, text
    assert "Family first" in p["prime_directive"] and "Raise the boys" in p["mission"]
    assert {g["id"] for g in p["goals"]} >= {"q5", "q7"}


@check("5b: a judging pass writes stakes, priority and why in one locked write, with a history row; "
       "never over a priority the user stated, nor a task judged while it ran; bad verdicts dropped")
def _():
    _fresh("judge_write")
    chore = _id(O.open_task("Repot two basement plants", kind="deadline", due=_d(-5)))
    bill = _id(O.open_task("Pay the card bill", kind="deadline", due=_d(-1)))
    mine = _id(O.open_task("Book the boiler service", kind="deadline", due=_d(4),
                           priority="low", priority_source="stated"))
    late = _id(O.open_task("Renew the parking permit", kind="deadline", due=_d(6)))

    def reply(payload):
        # While the call ran, an agent judged `late` itself.
        O.update_task(late, "set_stakes", stakes="missable")
        return json.dumps({"tasks": [
            {"id": chore, "stakes": "missable", "priority": "low", "why": "nothing much"},
            {"id": bill, "stakes": "vital", "priority": "high", "why": "late fee and interest"},
            {"id": mine, "stakes": "vital", "priority": "high", "why": "no hot water"},
            {"id": late, "stakes": "vital", "priority": "high", "why": "a fine"},
            {"id": "ob_invented", "stakes": "vital", "priority": "high"},
            {"id": chore, "stakes": "urgent!!", "priority": "high"}]})
    _JUDGE_REPLIES.append(reply)
    assert TJ.start_judging(_PERSONA) is True
    _join()
    assert _CALLS["judge"] == 1
    b, c, m, lt = (_task(x) for x in (bill, chore, mine, late))
    assert (b["stakes"], b["priority"], b["stakes_why"]) == ("vital", "high", "late fee and interest")
    assert b["history"][-1]["event"] == "judged" and b["history"][-1]["by"] == "task_judge"
    assert (c["stakes"], c["priority"]) == ("missable", "low")
    assert m["stakes"] == "vital" and m["priority"] == "low"      # the user's own priority kept
    assert lt["stakes"] == "missable"                             # judged meanwhile: untouched
    assert O.is_essential(b) and O._view(b, TODAY)["state"] == "overdue"
    assert TJ.unjudged() == []
    assert TJ.start_judging(_PERSONA) is False                    # nothing left: no call


@check("5c: the judge's controls — flag off, single flight, the minimum gap and the daily cap hold "
       "with no call; a failed call is retried on a later tick")
def _():
    _fresh("judge_controls", flags={"task_judge": False})
    t1 = _id(O.open_task("Repot two basement plants", kind="deadline", due=_d(-5)))
    assert TJ.start_judging(_PERSONA) is False and _CALLS["judge"] == 0
    C._OVERRIDE = {"flags": _FLAGS}
    st = TJ._load(_PERSONA)
    st["inflight_at"] = _CLOCK["now"].isoformat(timespec="seconds")
    TJ._save(st, _PERSONA)
    assert TJ.start_judging(_PERSONA) is False                    # single flight
    st = TJ._load(_PERSONA)
    st.pop("inflight_at")
    TJ._save(st, _PERSONA)
    _JUDGE_REPLIES.append(lambda p: (_ for _ in ()).throw(RuntimeError("Vertex 503")))
    assert TJ.start_judging(_PERSONA) is True
    _join()
    assert _task(t1).get("stakes") is None and "inflight_at" not in TJ._load(_PERSONA)
    assert TJ.start_judging(_PERSONA) is False                    # the 10-minute gap
    _CLOCK["now"] += timedelta(minutes=11)
    _JUDGE_REPLIES.append(_verdicts({}))
    assert TJ.start_judging(_PERSONA) is True
    _join()
    assert _task(t1)["stakes"] == "missable"
    _id(O.open_task("Another chore", kind="deadline", due=_d(-2)))
    st = TJ._load(_PERSONA)
    st["counters"][D._today().isoformat()] = 6
    TJ._save(st, _PERSONA)
    _CLOCK["now"] += timedelta(minutes=30)
    assert TJ.start_judging(_PERSONA) is False and _CALLS["judge"] == 2   # the daily cap


@check("5d: the tick starts the judge when an unjudged task exists, off the reply path")
def _():
    _fresh("judge_tick")
    _id(O.open_task("Repot two basement plants", kind="deadline", due=_d(-5)))
    _JUDGE_REPLIES.append(_verdicts({}))
    out = D.refresh_tick()
    assert "task judge started" in out, out
    _join()
    assert TJ.unjudged() == [] and _CALLS["day_model"] == 0


# --- 6. the Synthesizer sees a plan's current step ----------------------------------------------

@check("6: a plan's current step is in the Tasks section even behind six overdue must-dos "
       "(11-22: 'I checked my HMRC sign-in' closed nothing, the step was cut by the cap)")
def _():
    _fresh("context", goals=_TAX_GOALS.format(due=_d(30)))
    for i in range(7):
        O.open_task(f"Overdue must-do number {i}", kind="deadline", due=_d(-3 - i), stakes="vital")
    res = O.open_plan([{"key": "a", "what": "Check you can sign in to your HMRC online account",
                        "part_of": "q5", "due": _d(3), "eligible_from": _d(0), "flexible": True}])
    block = O.context_block()
    assert res["ids"]["a"] in block and "Check you can sign in" in block, block


# --- 7. the judging rule lives in the tool every opener reads -----------------------------------

@check("7: open_task's schema carries the judging rule and stakes_why; a stakes_why is stored; the "
       "flag-off schemas are untouched")
def _():
    _fresh("schema")
    o, u, _l = O.task_schemas()
    props = o["input_schema"]["properties"]
    assert "stakes_why" in props and "stakes_why" in u["input_schema"]["properties"]
    desc = props["stakes"]["description"]
    for word in ("financial", "social", "psychological", "whether or not they serve a goal",
                 "gardener", "back-burner"):
        assert word in desc, word
    tid = _id(O.open_task("File the VAT return", kind="deadline", due=_d(5), stakes="vital",
                          stakes_why="£100 penalty"))
    assert _task(tid)["stakes_why"] == "£100 penalty"
    C._OVERRIDE = {"flags": {**_FLAGS, "ledger_fields": False}}
    o2, _u2, _l2 = O.task_schemas()
    assert o2 is O.OPEN_TASK_SCHEMA and "stakes_why" not in json.dumps(o2)


# --- 8. Fable diff review, 2026-11-22 -----------------------------------------------------------

_NOUNS = ("gutter", "boiler", "passport", "bicycle", "piano", "garden shed", "fridge", "curtains",
          "chimney", "lawnmower", "kayak", "telescope", "aquarium", "sewing machine", "drone",
          "harmonica", "trampoline", "wardrobe", "doorbell", "hammock", "violin", "greenhouse",
          "barbecue", "treadmill", "bookshelf", "skylight", "canoe", "easel", "sundial", "loom",
          "accordion", "birdbath", "chandelier", "dartboard", "espresso machine")


def _goal_index_get(gid):
    O._GOAL_CACHE.update(key=None)
    return O._goal_index()[gid]

@check("F1: a task left unjudged past the grace counts as vital again — a failing judge degrades "
       "to the old rule, never to a hidden bill")
def _():
    _fresh("grace")
    bill = _id(O.open_task("Pay the council tax", kind="deadline", due=_d(-2)))
    assert O._view(_task(bill), TODAY)["state"] == "lapsed"       # awaiting the judge
    _CLOCK["now"] += timedelta(minutes=61)
    assert O.stakes_of(_task(bill)) == "vital" and O.is_essential(_task(bill))
    assert O._view(_task(bill), TODAY)["state"] == "overdue"
    assert "Pay the council tax" in O.context_block()


@check("F1: a FAILED call gives its place in the daily cap back; a reply that judges nothing halves "
       "the next batch (to no fewer than 5), and a pass that lands restores it")
def _():
    _fresh("refund")
    for i in range(30):
        O.open_task(f"Service the {_NOUNS[i]}", kind="deadline", due=_d(-1 - i % 5))
    for i in range(6):
        _JUDGE_REPLIES.append(lambda p: (_ for _ in ()).throw(RuntimeError("Vertex 503")))
        assert TJ.start_judging(_PERSONA) is True, i
        _join()
        _CLOCK["now"] += timedelta(minutes=11)
    assert TJ._load(_PERSONA)["counters"].get(D._today().isoformat(), 0) == 0
    sizes = []
    _JUDGE_REPLIES.append(lambda p: (sizes.append(len(p["tasks"])), "not json at all")[1])
    assert TJ.start_judging(_PERSONA) is True
    _join()
    _CLOCK["now"] += timedelta(minutes=11)
    _JUDGE_REPLIES.append(lambda p: (sizes.append(len(p["tasks"])), _verdicts({})(p))[1])
    assert TJ.start_judging(_PERSONA) is True
    _join()
    assert sizes == [25, 12], sizes
    assert "batch" not in TJ._load(_PERSONA) and len(TJ.unjudged()) == 18


@check("F6: the most urgent go first — an overdue bill opened last is in the first batch of 25")
def _():
    _fresh("urgent_first")
    for i in range(30):
        O.open_task(f"Look into the {_NOUNS[i]}", kind="deadline", due=_d(20 + i))
    bill = _id(O.open_task("Pay the overdue water bill", kind="deadline", due=_d(-3)))
    seen = []
    _JUDGE_REPLIES.append(lambda p: (seen.extend(t["id"] for t in p["tasks"]), _verdicts({})(p))[1])
    assert TJ.start_judging(_PERSONA) is True
    _join()
    assert seen[0] == bill and len(seen) == 25, seen[:3]


@check("F3/F4: an obligation goal is high priority; a task serving a goal takes the goal's priority "
       "and the judge never flattens it; a month-window bill is judged")
def _():
    _fresh("goal_priority", goals=_TAX_GOALS.format(due=_d(30)).replace(
        "  vetted: {date: '2026-11-21', depth: M, priority: high, by: synthesizer}\n", "", 1))
    assert O._goal_priority(_goal_index_get("q5")) == "high"      # kind obligation, no vet priority
    linked = _id(O.open_task("Download the P60", kind="deadline", due=_d(5), goal_id="q5"))
    plain = _id(O.open_task("Buy printer ink", kind="deadline", due=_d(5)))
    bill = _id(O.open_task("Pay the card bill", kind="habit", every="month",
                           on_days=["10-15"]))
    assert {t["id"] for t in TJ.unjudged()} == {linked, plain, bill}
    _JUDGE_REPLIES.append(lambda p: json.dumps({"tasks": [
        {"id": t["id"], "stakes": "vital", "priority": "normal", "why": "x"} for t in p["tasks"]]}))
    assert TJ.start_judging(_PERSONA) is True
    _join()
    assert not _task(linked).get("priority") and _task(plain)["priority"] == "normal"
    assert _task(bill)["stakes"] == "vital"
    assert _score(linked) - _score(plain) == 10, (_score(linked), _score(plain))   # 30 vs 20


@check("F5: steps beyond a plan's allowance and must-dos beyond the cap are both counted in "
       "'+N more', and the list keeps its order")
def _():
    _fresh("cap_count", goals=_TAX_GOALS.format(due=_d(30)))
    for i in range(8):
        O.open_task(f"Pay for the {_NOUNS[i]}", kind="deadline", due=_d(-3 - i), stakes="vital")
    res = O.open_plan([{"key": f"s{i}", "what": f"Fix the {_NOUNS[20 + i]}", "part_of": "q5",
                        "due": _d(3), "eligible_from": _d(0), "flexible": True} for i in range(9)])
    assert res["ok"], res
    block = O.context_block()
    shown_steps = sum(1 for i in range(9) if f"Fix the {_NOUNS[20 + i]}" in block)
    shown_bills = sum(1 for i in range(8) if f"Pay for the {_NOUNS[i]}" in block)
    assert (shown_steps, shown_bills) == (O._STEPS_PER_PLAN, O._CONTEXT_MAX), (shown_steps, shown_bills)
    assert f"+{17 - O._STEPS_PER_PLAN - O._CONTEXT_MAX} more" in block, block
    lines = block.splitlines()
    bills = [i for i, ln in enumerate(lines) if "Pay for the " in ln]
    steps = [i for i, ln in enumerate(lines) if "Fix the " in ln]
    assert max(bills) < min(steps), (bills, steps)        # overdue must-dos before window steps


@check("F7: re-vetting a goal at a new priority re-weighs its open steps at once")
def _():
    _fresh("revet", goals=_TAX_GOALS.format(due=_d(30)))
    res = O.open_plan([{"key": "x", "what": "Sort the loft boxes", "part_of": "q7", "due": _d(5)}])
    x = res["ids"]["x"]
    assert (_task(x)["stakes"], _task(x)["priority"]) == ("missable", "low")
    G._calling_agent = lambda: "synthesizer"
    out = G.update_goal("vet", goal_id="q7", verdict="active", size="M", priority="high")
    assert "taken on" in out, out
    assert (_task(x)["stakes"], _task(x)["priority"]) == ("vital", "high")


@check("live 11-22: 'I checked my HMRC sign-in, it works' closes the sign-in step — a step still "
       "waiting on it ('Log in to HMRC…') is no rival; two steps open at once still tie")
def _():
    _fresh("gate_waiting_rival", goals=_TAX_GOALS.format(due=_d(30)))
    res = O.open_plan([
        {"key": "a", "what": "Check you can sign in to your HMRC online account", "part_of": "q5",
         "due": _d(3), "eligible_from": _d(0), "flexible": True},
        {"key": "b", "what": "Log in to HMRC and complete the tax return tailoring questions",
         "part_of": "q5", "needs": ["a"], "due": _d(10), "flexible": True}])
    a = res["ids"]["a"]
    from tools import turn_context as T
    text = "I checked my HMRC sign-in, it works."
    cm = T.turn_scope(user_turn=True)
    turn = cm.__enter__()
    turn.update(close_gate=True, user_text=text, prev_assistant="")
    try:
        r = O.update_task(a, "done", evidence=text)
        assert not r.startswith("error"), r
        assert _task(a)["status"] == "done"
        # Now step b is open and actionable: a second HMRC step open at once is a real rival.
        c = _id(O.open_task("Ring HMRC about the PAYE code", kind="deadline", due=_d(4),
                            stakes="vital"))
        turn.update(user_text="sorted the HMRC one")
        r = O.update_task(c, "done", evidence="sorted the HMRC one")
        assert r.startswith("error: not recorded"), r
    finally:
        cm.__exit__(None, None, None)


if __name__ == "__main__":
    for name, ok, err in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if not ok:
            print("        " + err.replace("\n", "\n        "))
    passed = sum(1 for _n, ok, _e in _results if ok)
    print(f"\n{passed} passed, {len(_results) - passed} failed, {len(_results)} total")
    sys.exit(0 if passed == len(_results) else 1)
