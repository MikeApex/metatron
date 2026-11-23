"""
tests/test_ranking_v2.py — ranking Part B, phase 1 (archive/plans/ranking_values_plan_2026-11-23.md):
rank by the regret of delay, in shadow. Plan § 6 tests 1–9 and 13 (test 1 as § 10 R3 rewords it,
tests 5–7 as § 11 and R2 amend them), the R1 / R3 / R9 cases of § 10, the judge's recording pass,
implied promise dates, the people offer and the shadow comparison.

Part A's own suite, tests/test_task_ranking.py, is the proof that flag-off is still Part A — run
it beside this one.

EVERY LIVE METER IS STUBBED (the standing rule): CalDAV, Google Routes, the day_planner and
project_planner models (refusing), the task_judge model (`_MODEL_CALL`, a counting stub), push.
No persona data — a temp directory per check.

    python3 tests/test_ranking_v2.py
"""
from __future__ import annotations

import json
import math
import sys
import tempfile
import threading
from datetime import date, datetime, time, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

import core.interview as INTV  # noqa: E402
import core.persona as P  # noqa: E402
import core.remote_client as RC  # noqa: E402
import tools.ambient as A  # noqa: E402
import tools.caldav as CAL  # noqa: E402
import tools.crm as CRM  # noqa: E402
import tools.day_plan as D  # noqa: E402
import tools.day_plan_config as C  # noqa: E402
import tools.day_shape as DS  # noqa: E402
import tools.goals as G  # noqa: E402
import tools.horizon as H  # noqa: E402
import tools.location as L  # noqa: E402
import tools.obligations as O  # noqa: E402
import tools.project_plan as PP  # noqa: E402
import tools.ranking as RK  # noqa: E402
import tools.routing as R  # noqa: E402
import tools.task_judge as TJ  # noqa: E402

_results: list[tuple[str, bool, str]] = []
_TMP = Path(tempfile.mkdtemp(prefix="ranking_v2_"))
TODAY = date.today()
_CLOCK = {"now": datetime.combine(TODAY, time(7, 0))}
O._now = lambda: _CLOCK["now"]
A._get_timezone = lambda: "Europe/London"
_PERSONA = "ranking_b"

CAL._query_events = lambda *a, **k: {"events": [], "discovery": "ok"}
CAL._get_event_by_uid = lambda uid, persona=None: {"error": "offline"}
R.get_travel_time = lambda *a, **k: {"journeys": [{"duration_minutes": 20}]}
L.load_zones = lambda persona=None: []
L.current_zone = lambda persona=None: {}
INTV.holds_proactive = lambda persona: False
D._quiet_now = lambda persona: False
D._idle_minutes = lambda persona: None
_CALLS = {"day_model": 0, "planner": 0, "judge": 0}


def _refuse(kind):
    def f(*a, **k):
        _CALLS[kind] += 1
        raise AssertionError(f"an unexpected {kind} model call")
    return f


D._call_model = _refuse("day_model")
PP._MODEL_CALL = _refuse("planner")
RC.send_one = lambda *a, **k: "ok"

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
          "task_judge": True, "cost_record": True, "ranking_v2": False}


def _d(n: int) -> str:
    return (TODAY + timedelta(days=n)).isoformat()


def _join() -> None:
    for th in threading.enumerate():
        if th.name.startswith("day_plan_"):
            th.join(10)


def _fresh(name: str, flags: dict | None = None, shape: str | None = None) -> Path:
    _join()
    d = _TMP / name
    (d / "config").mkdir(parents=True, exist_ok=True)
    for mod in (O, D, DS, L, H):
        mod.persona_data_dir = lambda persona=None, _d=d: _d
    DS.persona_config_dir = lambda persona=None, _d=d: _d / "config"
    TJ.persona_config_dir = lambda persona=None, _d=d: _d / "config"
    CRM._crm_path = lambda _d=d: _d / "crm" / "contacts.json"
    (d / "config" / "goals.yaml").write_text("quarterly: []\n")
    (d / "config" / "mission.md").write_text("Raise the children well.\n")
    (d / "config" / "prime_directive.md").write_text("Family first.\n")
    G._goals_path = lambda _d=d: _d / "config" / "goals.yaml"
    G._calling_agent = lambda: ""
    (d / "day_shape.yaml").write_text(shape or 'day: [{days: all, wake: "07:00", bed: "23:00"}]\n')
    C._OVERRIDE = {"flags": {**_FLAGS, **(flags or {})}}
    RK._OVERRIDE = {}
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
                             + "".join(traceback.format_exc().splitlines(True)[-6:])))
        finally:
            _join()
            C._OVERRIDE = None
            RK._OVERRIDE = None
        return fn
    return deco


def _id(out: str) -> str:
    assert not out.startswith("error"), out
    return out.split()[1]


def _task(tid: str) -> dict:
    return O._norm(O._find(O._load(None), tid))


def _assess(t: dict, day: date | None = None) -> dict:
    day = day or TODAY
    v = O._view(t, day)
    return RK.assess(t, v, day, RK.cfg(), on_list=bool(v.get("actionable")
                                                      and O._on_todays_list(t, v)))


def _v2(day: date | None = None) -> list[dict]:
    return D._candidates_v2(day or TODAY, _PERSONA)


def _refs(cands: list[dict]) -> list[str]:
    return [c["task_id"] for c in cands]


def _rec(costs: dict, bears: str = "self", shape: str | None = None, **kw) -> dict:
    out = {"costs": costs, "bears": bears, "costs_source": "stated"}
    if shape:
        out["shape"] = shape
    out.update(kw)
    return out


def _close(a: float, b: float, tol: float = 0.01) -> bool:
    return abs(a - b) <= tol


# --- the config ----------------------------------------------------------------------------------

@check("config: ranking.yaml parses, and the code's defaults equal it (a broken file falls back "
       "to the same values, never to nonsense)")
def _():
    raw = yaml.safe_load((ROOT / "config" / "modules" / "ranking.yaml").read_text())
    merged = RK._merge(RK._DEFAULTS, raw)
    assert merged == RK._DEFAULTS, {k: (raw.get(k), RK._DEFAULTS.get(k)) for k in raw
                                    if raw.get(k) != RK._DEFAULTS.get(k)}
    assert RK._DEFAULTS["shapes"]["neglect_k"] == 1.5          # Mike: kin stays convex
    assert RK._DEFAULTS["dimension_weight"]["social"] == 1.5    # research § 3a


# --- 1. Dad vs the permit (plan § 6 test 1, as R3 rewords it) -------------------------------------

@check("1: Dad at day 21 of a weekly wish outranks the permit due today; at day 2 Dad is not yet "
       "due, so the permit is the only candidate")
def _():
    _fresh("dad")
    dad = _id(O.open_task("Call Dad", kind="interval", interval_days=7, last_done=_d(-21),
                          costs={"social": "severe"}, bears="close", shape="neglect",
                          costs_source="stated"))
    permit = _id(O.open_task("Renew the parking permit", kind="deadline", due=_d(0), minutes=10,
                             costs={"financial": "minor"}, costs_source="stated"))
    order = _refs(_v2())
    assert order[:2] == [dad, permit], order
    a = _assess(_task(dad))
    # G: social severe 0.9 × 1.5 capped at 0.99 → 99; r = 3 → (r − 1)^1.5 = 2.83.
    assert _close(a["G"], 99.0) and _close(a["factor"], 2 ** 1.5, 0.001), a
    O.update_task(dad, "done", evidence="rang him on Sunday", on_date=_d(-2))
    order = _refs(_v2())
    assert order == [permit], order


# --- 2. floor and compounding (§ 6 test 2, § 11 row 1) -------------------------------------------

@check("2: costs combine as 100 × [1 − ∏(1 − s)] — two majors (51) < one severe (90), > a lone "
       "major (30); the total never reaches 100; minors compound a little (19)")
def _():
    c = RK.cfg()
    I = lambda **k: RK.importance(k, c)  # noqa: E731
    assert _close(I(financial="major", legal="major"), 51.0)
    assert I(financial="major", legal="major") < I(financial="severe")
    assert I(financial="major", legal="major") > I(financial="major")
    assert _close(I(financial="severe", legal="major"), 93.0)
    assert _close(I(financial="minor", legal="minor"), 19.0)
    every = I(**{d: "severe" for d in RK.DIMENSIONS})
    assert 99.0 < every <= 100.0, every                         # bounded (rounding to 100)
    # social × 1.5 at an equal grade (§ 11 row 3)
    assert I(social="major") > I(financial="major")
    assert _close(I(social="major"), 45.0)


# --- 3. who bears it (§ 6 test 3, § 11 row 4) -----------------------------------------------------

@check("3: an org-borne major costs less to delay than the same self-borne one; close = self; a "
       "business the user owns weighs as their own")
def _():
    _fresh("bearer")
    ids = {}
    for b in ("self", "close", "org", "own_org", "others"):
        ids[b] = _id(O.open_task(f"File the {b} report", kind="deadline", due=_d(0), minutes=30,
                                 costs={"financial": "major"}, bears=b, costs_source="stated",
                                 new_instance=True))
    cod = {b: _assess(_task(t))["cod"] for b, t in ids.items()}
    assert cod["org"] < cod["self"] and _close(cod["org"], 15.0), cod
    assert cod["close"] == cod["self"] == cod["own_org"], cod
    assert _close(cod["others"], 21.0), cod


# --- 4. the four shapes over a sweep (§ 6 test 4) -------------------------------------------------

@check("4: step / accruing / cliff / neglect give their cost of delay at the exact points")
def _():
    c = RK.cfg()
    base = {"id": "t1", "what": "x", "status": "open", "kind": "deadline", "minutes": 120,
            "costs": {"financial": "major"}, "bears": "self", "costs_source": "stated",
            "created_at": f"{_d(-40)}T09:00:00"}

    def at(shape: str, days_left: int) -> dict:
        t = {**base, "shape": shape, "due": _d(days_left)}
        return RK.assess(t, O._view(t, TODAY), TODAY, c)
    # 120 min, 35% buffer, 120 free minutes a day → needs 1.35 days; the climb runs over 14.
    assert _close(at("step", 20)["factor"], 0.0) and not at("step", 20)["must"]
    assert _close(at("step", 10)["factor"], 1 - 8.65 / 14, 0.001)
    assert _close(at("step", 2)["factor"], 1 - 0.65 / 14, 0.001)
    assert at("step", 1)["must"] and _close(at("step", 1)["factor"], 1.0)
    assert _close(at("step", -3)["factor"], 0.2)                # the cost already landed
    assert _close(at("accruing", -3)["factor"], 1.3)            # 1 + 0.1 × 3
    assert _close(at("cliff", 2)["factor"], 2 * (1 - 0.65 / 14), 0.001)
    assert at("cliff", -1)["factor"] == 0.0 and not at("cliff", -1)["must"]   # moot
    assert _close(at("step", 1)["cod"], 30.0)
    n = {"id": "t2", "what": "Water the garden", "status": "open", "kind": "interval",
         "interval_days": 7, "costs": {"psychological": "major"}, "costs_source": "stated",
         "shape": "neglect", "created_at": f"{_d(-200)}T09:00:00"}
    for since, want in ((7, 0.0), (14, 1.0), (21, 2 ** 1.5), (70, 3.0)):
        t = {**n, "last_done": _d(-since)}
        got = RK.assess(t, O._view(t, TODAY), TODAY, c)["factor"]
        assert _close(got, want, 0.001), (since, got, want)


# --- 5. the attention block (§ 6 test 5 as § 11 row 6 amends it) ----------------------------------

@check("5: a task costs at least one 5-minute block — a 2- and a 5-minute task of equal cost rank "
       "equal, a 10-minute one at half; three 2-minute admin tasks share their blocks")
def _():
    c = RK.cfg()
    blocks = RK.attention_blocks([
        {"ref": "a", "minutes": 2, "activity": "health"},
        {"ref": "b", "minutes": 5, "activity": "household"},
        {"ref": "c", "minutes": 10, "activity": "errands"},
        {"ref": "d", "minutes": 30, "activity": "focus"},
    ], c)
    assert blocks["a"] == blocks["b"] == 1.0 and blocks["c"] == 2.0 and blocks["d"] == 6.0, blocks
    batch = RK.attention_blocks([{"ref": f"x{i}", "minutes": 2, "activity": "admin"}
                                 for i in range(3)], c)
    # Together 6 minutes, more than one block: each pays its share (0.4), not a block of its own.
    assert all(_close(v, 0.4) for v in batch.values()), batch


# --- 6. sequence: hard first (§ 6 test 6; R2 — no "behind" in phase 1) ----------------------------

@check("6: when both fit, the harder thing goes first — a long focus task is placed before a "
       "short chore that ranks above it")
def _():
    _fresh("hardfirst", flags={"ranking_v2": True})
    _CLOCK["now"] = datetime.combine(TODAY, time(10, 0))     # after breakfast, room for both
    chore = _id(O.open_task("Post the card", kind="deadline", due=_d(0), minutes=10,
                            costs={"social": "major"}, costs_source="stated", activity="errands"))
    report = _id(O.open_task("Write the quarterly report", kind="deadline", due=_d(0), minutes=90,
                             costs={"financial": "minor"}, costs_source="stated", activity="focus"))
    cands = _v2()
    assert _refs(cands)[:2] == [chore, report], _refs(cands)    # selection: the chore ranks first
    plan = D.current(_PERSONA)
    starts = {b["task_id"]: b["start"] for b in plan["blocks"] if b["kind"] == "task"}
    assert chore in starts and report in starts, starts
    assert starts[report] < starts[chore], starts


# --- 7. protected time in phase 1 (§ 6 test 7 as R2 rewords it) -----------------------------------

@check("7: under ranking_v2 protected time is still Part A's rule — advance work never enters "
       "it; it is never essential, so never nudged")
def _():
    shape = 'wake: "07:00"\nbed: "23:00"\npersonal: ["08:00-22:00"]\n'
    _fresh("protected", flags={"ranking_v2": True}, shape=shape)
    adv = _id(O.open_task("Draft the grant application", kind="deadline", due=_d(3), minutes=60,
                          costs={"financial": "severe"}, costs_source="stated", activity="focus"))
    cands = _v2()
    c = next(x for x in cands if x["task_id"] == adv)
    assert c.get("advance") and not c["essential"] and not D._may_protect(c), c
    plan = D.current(_PERSONA)
    assert [b for b in plan["blocks"] if b["kind"] == "protected"], plan["blocks"]
    assert not [b for b in plan["blocks"] if b.get("task_id") == adv], "advance work in own time"
    assert not [s for s in plan.get("suggestions") or [] if s.get("ref") == c["ref"]]


# --- 8. derived stakes (§ 6 test 8, R1) -------------------------------------------------------------

@check("8: a Part A task gives the same essential answer with the flag on and off; a recorded "
       "major/severe reads vital and a minor missable under v2; a plan step stays vital whoever "
       "bears it")
def _():
    _fresh("stakes")
    old_v = _id(O.open_task("Pay the gas bill", kind="deadline", due=_d(1), stakes="vital"))
    old_m = _id(O.open_task("Sort the photo albums", kind="deadline", due=_d(1), stakes="missable"))
    minor = _id(O.open_task("Return the library book", kind="deadline", due=_d(1),
                            stakes="vital", costs={"financial": "minor"}, costs_source="stated"))
    off = {t: O.is_essential(_task(t)) for t in (old_v, old_m, minor)}
    C._OVERRIDE["flags"]["ranking_v2"] = True
    on = {t: O.is_essential(_task(t)) for t in (old_v, old_m, minor)}
    assert off[old_v] == on[old_v] is True and off[old_m] == on[old_m] is False, (off, on)
    assert off[minor] is True and on[minor] is False, (off, on)   # its record says minor
    end = _id(O.open_task("Close the company accounts", kind="deadline", due=_d(30),
                          stakes="vital", costs={"legal": "severe"}, bears="org",
                          costs_source="stated"))
    res = O.open_plan([{"key": "a", "what": "Gather the receipts", "due": _d(5),
                        "part_of": end}], _PERSONA)
    step = next(t["id"] for t in O._load(None) if t.get("part_of") == end)
    O.update_task(step, "set_costs", costs={"financial": "minor"}, bears="org",
                  costs_source="stated")
    assert RK.stakes_v2(_task(step)) == "vital" and O.is_essential(_task(step)), res


# --- 9 / R1. flag off is Part A, and nothing writes stakes -----------------------------------------

@check("9 / R1: with ranking_v2 off, a cost record changes nothing Part A reads — the candidates, "
       "their scores and order, the stakes and is_essential are identical before and after")
def _():
    _fresh("flagoff")
    a = _id(O.open_task("Pay the water bill", kind="deadline", due=_d(0), stakes="vital"))
    b = _id(O.open_task("Repot the fern", kind="deadline", due=_d(0), stakes="missable"))
    h = _id(O.open_task("Stretch", kind="habit", every="day"))

    def snap():
        cands = D._candidates(TODAY, _PERSONA)
        return (json.dumps([(c["ref"], c["score"], c["essential"], c["vital"], c["stakes"],
                             c["digest"]) for c in cands]),
                [O.stakes_of(_task(t)) for t in (a, b, h)],
                [O.is_essential(_task(t)) for t in (a, b, h)])
    before = snap()
    O.update_task(a, "set_costs", costs={"financial": "minor"}, costs_source="stated")
    O.update_task(b, "set_costs", costs={"psychological": "severe"}, costs_source="stated")
    O.update_task(h, "set_costs", costs={"health": "major"}, costs_source="stated")
    assert snap() == before


@check("R1: no path writes stakes from a cost record — open_task, set_costs and the judge's "
       "recording pass leave stakes untouched; a stated record is never replaced by an inference")
def _():
    _fresh("nostakes")
    t1 = _id(O.open_task("Book the boiler service", kind="deadline", due=_d(4),
                         costs={"health": "severe"}, costs_source="stated"))
    assert "stakes" not in _task(t1)
    t2 = _id(O.open_task("Renew the passport", kind="deadline", due=_d(9), stakes="missable",
                         stakes_source="stated"))
    O.update_task(t2, "set_costs", costs={"legal": "severe"}, costs_source="stated")
    assert _task(t2)["stakes"] == "missable" and _task(t2)["stakes_source"] == "stated"
    out = O.update_task(t2, "set_costs", costs={"legal": "minor"}, costs_source="inferred")
    assert "keeps the user's own" in out and _task(t2)["costs"] == {"legal": "severe"}, out
    # The judge: t3 judged but unrecorded → only cost fields land; t1 has a record → not offered.
    t3 = _id(O.open_task("Answer the school survey", kind="deadline", due=_d(2), stakes="vital"))
    _JUDGE_REPLIES.append(lambda p: json.dumps({"tasks": [
        {"id": x["id"], "costs": {"social": "minor"}, "bears": "others", "shape": "step",
         "why": "the class rep is waiting", "stakes": "missable", "priority": "low"}
        for x in p["tasks"]]}))
    assert TJ.start_judging(_PERSONA)
    _join()
    # t1 has a record but no stakes: offered for its stakes only; t3 judged, unrecorded: costs only.
    offered = {x["id"]: x.get("want") for x in _JUDGE_PAYLOADS[0]["tasks"]}
    assert offered.get(t1) == ["stakes"] and offered.get(t3) == ["costs"], offered
    assert _task(t1)["costs"] == {"health": "severe"}, _task(t1)
    assert "rules" in _JUDGE_PAYLOADS[0] and "costs" in _JUDGE_PAYLOADS[0]["rules"]
    got = _task(t3)
    assert got["stakes"] == "vital" and got["costs"] == {"social": "minor"}, got
    assert got["costs_source"] == "inferred" and got["bears"] == "others", got


@check("judge: an unjudged task gets stakes AND a record in one pass; with cost_record off the "
       "payload is Part A's (no want, no rules) and only stakes are asked for")
def _():
    _fresh("judgeboth")
    t = _id(O.open_task("Send the council tax form", kind="deadline", due=_d(3)))
    _CLOCK["now"] += timedelta(minutes=5)
    _JUDGE_REPLIES.append(json.dumps({"tasks": [
        {"id": t, "stakes": "vital", "priority": "high", "why": "£80 penalty",
         "costs": {"financial": "major", "legal": "minor"}, "bears": "self", "shape": "accruing"}]}))
    assert TJ.start_judging(_PERSONA)
    _join()
    got = _task(t)
    assert got["stakes"] == "vital" and got["shape"] == "accruing", got
    assert got["costs_why"] == "£80 penalty" and got["stakes_why"] == "£80 penalty", got
    _fresh("judgeoff", flags={"cost_record": False})
    t = _id(O.open_task("Send the council tax form", kind="deadline", due=_d(3)))
    _JUDGE_REPLIES.append(json.dumps({"tasks": [
        {"id": t, "stakes": "vital", "priority": "high", "why": "£80 penalty"}]}))
    assert TJ.start_judging(_PERSONA)
    _join()
    p = _JUDGE_PAYLOADS[0]
    assert "rules" not in p and "want" not in p["tasks"][0], p
    assert "costs_source" not in _task(t)


# --- R9: musts by absolute cost, never against the ratio -------------------------------------------

@check("R9: on a short day, a long severe task due today is placed before six ten-minute minors")
def _():
    _fresh("r9", flags={"ranking_v2": True})
    _CLOCK["now"] = datetime.combine(TODAY, time(19, 55))     # 20:00–22:00 before wind-down
    big = _id(O.open_task("Submit the visa application", kind="deadline", due=_d(0), minutes=90,
                          costs={"legal": "severe"}, costs_source="stated", activity="admin"))
    small = [_id(O.open_task(f"Reply to note {i}", kind="deadline", due=_d(0), minutes=10,
                             costs={"social": "minor"}, costs_source="stated",
                             activity=f"{['errands', 'household', 'personal'][i % 3]}",
                             new_instance=True)) for i in range(6)]
    cands = _v2()
    assert _refs(cands)[0] == big, _refs(cands)
    plan = D.current(_PERSONA)
    placed = {b["task_id"] for b in plan["blocks"] if b["kind"] == "task"}
    assert big in placed, (placed, plan.get("unplaced"))
    assert len(placed & set(small)) < 6


# --- R3: must-start-today, advance work, the floor ---------------------------------------------------

@check("R3: a four-hour task due in two days must start today; a ten-minute MINOR task due "
       "tomorrow does not appear (a minor is never pulled forward); advance work is suggested above the floor and only when there is room")
def _():
    _fresh("r3", flags={"ranking_v2": True})
    long = _id(O.open_task("Paint the spare room", kind="deadline", due=_d(2), minutes=240,
                           costs={"psychological": "major"}, costs_source="stated"))
    quick = _id(O.open_task("Order the printer ink", kind="deadline", due=_d(1), minutes=10,
                            costs={"financial": "minor"}, costs_source="stated"))
    adv = _id(O.open_task("Prepare the grant budget", kind="deadline", due=_d(3), minutes=120,
                          costs={"financial": "severe"}, costs_source="stated"))
    trivia = _id(O.open_task("Sort the spice rack", kind="deadline", due=_d(6), minutes=30,
                             costs={"psychological": "minor"}, costs_source="stated"))
    by = {c["task_id"]: c for c in _v2()}
    assert by[long]["v2"]["must"] and by[long]["v2"]["slack"] < 0, by[long]["v2"]
    assert quick not in by and trivia not in by, sorted(by)
    assert by[adv].get("advance") and by[adv]["v2"]["cod"] >= 3, by[adv]["v2"]
    plan = D.current(_PERSONA)
    placed = {b["task_id"]: b for b in plan["blocks"] if b["kind"] == "task"}
    assert long in placed and adv in placed and placed[adv].get("advance"), sorted(placed)
    # A day with no room: a must fills what is left; the advance work is not placed, silently.
    _CLOCK["now"] = datetime.combine(TODAY, time(20, 55))
    _id(O.open_task("Finish the tax summary", kind="deadline", due=_d(0), minutes=60,
                    costs={"financial": "major"}, costs_source="stated"))
    D.request_reshuffle("test", _PERSONA)
    plan = D.current(_PERSONA)
    placed = {b["task_id"] for b in plan["blocks"] if b["kind"] == "task" and not b.get("history")}
    assert adv not in placed and adv not in {u["ref"] for u in plan["unplaced"]}, plan["unplaced"]


@check("R3: an advance task placed in free time is labelled a suggestion in the Synthesizer's "
       "block; the rest stays the user's own time")
def _():
    _fresh("label", flags={"ranking_v2": True})
    _CLOCK["now"] = datetime.combine(TODAY, time(10, 0))
    _id(O.open_task("Prepare the grant budget", kind="deadline", due=_d(3), minutes=60,
                    costs={"financial": "severe"}, costs_source="stated"))
    plan = D.current(_PERSONA)
    line = D._free_line(plan, _CLOCK["now"], None) or ""
    assert "a suggestion only" in line and "own time" in line, line


# --- implied promise dates (R8, § 11 row 9) ---------------------------------------------------------

@check("implied dates: a promise to someone with no date is due 3 days after it was made when "
       "quick, 7 when effortful; never for the user's own task; nothing is stored")
def _():
    _fresh("implied")
    quick = _id(O.open_task("Send Sam the photos", kind="deadline", minutes=5,
                            costs={"social": "minor"}, bears="close", costs_source="stated"))
    slow = _id(O.open_task("Help Sam move the sofa", kind="deadline", minutes=120,
                           costs={"social": "major"}, bears="others", costs_source="stated"))
    mine = _id(O.open_task("Clear the inbox", kind="deadline", minutes=5,
                           costs={"psychological": "minor"}, costs_source="stated"))
    c = RK.cfg()
    assert RK.implied_due(_task(quick), c) == TODAY + timedelta(days=3)
    assert RK.implied_due(_task(slow), c) == TODAY + timedelta(days=7)
    assert RK.implied_due(_task(mine), c) is None
    assert not _task(quick).get("due")
    _CLOCK["now"] += timedelta(days=3)
    assert _assess(_task(quick), TODAY + timedelta(days=3))["must"]


# --- 13. the start-late buffer (§ 6 test 13 as § 11 row 5 amends it) -------------------------------

@check("13: the buffer is tiered by length; the user's own bias is shrunk 0.43 / 0.71 / 0.83 at "
       "3 / 10 / 20 observations; none means the tier default; a must-start task closed late is "
       "one observation")
def _():
    c = RK.cfg()
    assert RK.tier_buffer(10, c) == 0.0 and RK.tier_buffer(60, c) == 0.35
    assert RK.tier_buffer(600, c) == 0.65 and RK.tier_buffer(None, c) == 0.40
    for n, w in ((3, 0.43), (10, 0.71), (20, 0.83)):
        assert _close(RK.shrink_weight(n, c), w, 0.01), (n, RK.shrink_weight(n, c))
    assert RK.person_bias([], c) == 0.0 and _close(RK.buffer_for(60, c, 0.0), 0.35)
    assert RK.buffer_for(60, c, math.log(2)) > 1.0
    _fresh("learn")
    assert RK.observe({}, [], TODAY, RK.cfg(), {"x": {"must": True, "slack": -1}}) is False  # off
    RK._OVERRIDE = {"buffer": {"learn": {"enabled": True}}}
    c = RK.cfg()
    t = _id(O.open_task("Write the funding report", kind="deadline", due=_d(2), minutes=240,
                        costs={"financial": "major"}, costs_source="stated"))
    st: dict = {}
    assessed = {t: _assess(_task(t))}
    assert RK.observe(st, [_task(t)], TODAY, c, assessed) and t in st["buffer"]["tracking"]
    _CLOCK["now"] += timedelta(days=3)
    O.update_task(t, "done", evidence="sent it")
    tasks = [O._norm(x) for x in O._load(None)]
    RK.observe(st, tasks, TODAY + timedelta(days=3), c, {})
    obs = st["buffer"]["obs"]
    # actual 4 days (since + 3, inclusive) against 2 raw days, less log(1.65) for the long tier
    assert len(obs) == 1 and _close(obs[0], math.log(4 / 2) - math.log(1.65), 0.001), obs


# --- the shadow and the report ---------------------------------------------------------------------

@check("shadow: with ranking_v2 off every build writes the v2 order with G, shape factor, slack and "
       "blocks apart, the log row says whether v2 would have reshuffled, the morning build is kept, "
       "and --compare prints both top tens — while the plan itself is Part A's")
def _():
    d = _fresh("shadow")
    dad = _id(O.open_task("Call Dad", kind="interval", interval_days=7, last_done=_d(-21),
                          costs={"social": "severe"}, bears="close", shape="neglect",
                          costs_source="stated"))
    bill = _id(O.open_task("Pay the card bill", kind="deadline", due=_d(0), stakes="vital"))
    plan = D.current(_PERSONA)
    sh = plan["shadow_v2"]
    assert sh["v2"][0]["task_id"] == dad and {"G", "factor", "slack", "blocks", "cod"} <= set(sh["v2"][0])
    assert any(r["task_id"] == bill and r["recorded"] is False for r in sh["v2"])
    assert [r for r, _s in sh["v1"]] == [c["ref"] for c in D._candidates(TODAY, _PERSONA)][:15]
    assert "_assessed" not in sh
    rows = [json.loads(x) for x in (d / "day_plan" / "log.jsonl").read_text().splitlines()]
    build = [r for r in rows if r["event"] == "build"][-1]
    assert "v2_would_reshuffle" in build and "Call" not in json.dumps(build)
    st = RK.load_state(_PERSONA)
    assert TODAY.isoformat() in st.get("shadow", {}), st.keys()
    # A task added since: v2 would reshuffle.
    _id(O.open_task("Renew the car insurance", kind="deadline", due=_d(0), minutes=20,
                    costs={"financial": "major"}, costs_source="stated"))
    plan2 = D.current(_PERSONA)
    assert plan2["shadow_v2"]["would_reshuffle"], plan2["shadow_v2"]["why"]
    sys.path.insert(0, str(ROOT / "scripts"))
    import ranking_report as RR
    text = RR.compare(_PERSONA, TODAY)
    assert "Call Dad" in text and "PART A" in text and "REGRET OF DELAY" in text, text
    assert "(fallback)" in text and "MUST" in text, text
    live = RR.compare(_PERSONA, TODAY, live=True)
    assert "Renew the car insurance" in live, live


@check("shadow: flag on, no shadow is written and the plan is placed by the v2 order")
def _():
    _fresh("flagon", flags={"ranking_v2": True})
    _id(O.open_task("Pay the card bill", kind="deadline", due=_d(0), stakes="vital"))
    plan = D.current(_PERSONA)
    assert "shadow_v2" not in plan
    assert [b for b in plan["blocks"] if b["kind"] == "task"]


# --- the people offer (§ 4.6, B9) ---------------------------------------------------------------------

@check("people: an intimate contact with a wished frequency is offered a clock once, on a brief, "
       "with v2 on only; showing it spends it; a colleague or a contact with no wish is never "
       "offered")
def _():
    d = _fresh("people", flags={"ranking_v2": True})
    (d / "crm").mkdir(exist_ok=True)
    (d / "crm" / "contacts.json").write_text(json.dumps([
        {"id": "c1", "first_name": "Pat", "relationship_type": "colleague",
         "contact_frequency_preference": "weekly"},
        {"id": "c2", "first_name": "Ann", "relationship_type": "family",
         "contact_frequency_preference": ""},
        {"id": "c3", "first_name": "Dad", "relationship_type": "family",
         "contact_frequency_preference": "weekly", "last_contact": _d(-12)},
    ]))
    plan = D.current(_PERSONA)
    shown: dict = {}
    block = D.render_block(plan, kind="morning_brief", shown=shown)
    assert "Keep in touch" in block and "Dad" in block and "every 7 days" in block, block
    assert "Pat" not in block and "Ann" not in block
    assert shown.get("people") == ["c3"]
    D.after_render(_PERSONA, shown)
    shown2: dict = {}
    assert "Keep in touch" not in D.render_block(plan, kind="morning_brief", shown=shown2)
    C._OVERRIDE["flags"]["ranking_v2"] = False
    (d / "day_plan" / "ranking_state.json").unlink()
    assert "Keep in touch" not in D.render_block(plan, kind="morning_brief", shown={})
    # On yes, the line's task: a neglect clock seeded from the last contact.
    C._OVERRIDE["flags"]["ranking_v2"] = True
    out = O.open_task("Be in touch with Dad", kind="interval", interval_days=7, last_done=_d(-12),
                      shape="neglect", bears="close", costs={"social": "major"},
                      costs_source="stated")
    a = _assess(_task(_id(out)))
    assert a["shape"] == "neglect" and a["factor"] > 0 and a["must"], a


@check("schemas: the cost fields and set_costs are offered only with cost_record on; neglect is "
       "refused on a deadline")
def _():
    _fresh("schemas")
    op, up, _l = O.task_schemas()
    assert "costs" in op["input_schema"]["properties"] and "set_costs" in \
        up["input_schema"]["properties"]["action"]["enum"]
    C._OVERRIDE["flags"]["cost_record"] = False
    op, up, _l = O.task_schemas()
    assert "costs" not in op["input_schema"]["properties"]
    assert "set_costs" not in up["input_schema"]["properties"]["action"]["enum"]
    assert O.update_task("x", "set_costs").startswith("error: `action`")
    C._OVERRIDE["flags"]["cost_record"] = True
    out = O.open_task("Fix the gate", kind="deadline", shape="neglect", costs={"financial": "minor"})
    assert out.startswith("error") and "interval" in out, out


# --- the Fable diff review's fixes (plan § 11, "Phase 1 built") -------------------------------------

@check("review #1: a vital the user STATED stays vital under v2 whatever an inferred record says")
def _():
    _fresh("statedvital", flags={"ranking_v2": True})
    t = _id(O.open_task("Renew the car tax", kind="deadline", due=_d(2), stakes="vital",
                        stakes_source="stated", costs={"financial": "minor"},
                        costs_source="inferred"))
    assert RK.stakes_v2(_task(t)) == "vital" and O.is_essential(_task(t))


@check("review #2/#3: a judge reply with no costs writes no record; a task whose record fails "
       "twice is not offered again, and a garbled reply does not count against it")
def _():
    _fresh("attempts")
    t = _id(O.open_task("Answer the survey", kind="deadline", due=_d(2), stakes="vital"))
    for i in range(2):
        _JUDGE_REPLIES.append(json.dumps({"tasks": [{"id": t, "bears": "family"}]}))
        _CLOCK["now"] += timedelta(minutes=11)
        assert TJ.start_judging(_PERSONA), i
        _join()
        assert not _task(t).get("costs_source"), _task(t)
    _CLOCK["now"] += timedelta(minutes=11)
    assert t not in {x["id"] for x in TJ.unrecorded(_PERSONA)}
    assert not TJ.start_judging(_PERSONA)                       # nothing left to offer
    _fresh("garbled")
    t = _id(O.open_task("Answer the survey", kind="deadline", due=_d(2), stakes="vital"))
    for i in range(2):
        _JUDGE_REPLIES.append("not json at all")
        _CLOCK["now"] += timedelta(minutes=11)
        assert TJ.start_judging(_PERSONA), i
        _join()
    assert t in {x["id"] for x in TJ.unrecorded(_PERSONA)}


@check("review #4: an old undated promise recorded today gets its grace from today, not from the "
       "day it was opened")
def _():
    _fresh("oldpromise")
    _CLOCK["now"] = datetime.combine(TODAY - timedelta(days=60), time(9, 0))
    t = _id(O.open_task("Send Mum the recipe", kind="deadline", minutes=5))
    _CLOCK["now"] = datetime.combine(TODAY, time(9, 0))
    O.update_task(t, "set_costs", costs={"social": "major"}, bears="close")
    assert RK.implied_due(_task(t), RK.cfg()) == TODAY + timedelta(days=3)
    assert not _assess(_task(t))["must"]


@check("review #5/#6: hard-first never puts advance work ahead of a must; advance work is never "
       "an Important candidate, and Now/Next call it a suggestion")
def _():
    _fresh("tiers", flags={"ranking_v2": True})
    _CLOCK["now"] = datetime.combine(TODAY, time(10, 0))
    bill = _id(O.open_task("Pay the gas bill", kind="deadline", due=_d(0), minutes=10,
                           stakes="vital", costs={"financial": "major"}, costs_source="stated"))
    adv = _id(O.open_task("Draft the grant application", kind="deadline", due=_d(3), minutes=90,
                          stakes="vital", costs={"financial": "severe"}, costs_source="stated",
                          activity="focus"))
    plan = D.current(_PERSONA)
    starts = {b["task_id"]: b for b in plan["blocks"] if b["kind"] == "task"}
    assert starts[adv].get("advance") and starts[bill]["start"] < starts[adv]["start"], starts
    imp = D._important(plan["blocks"], TODAY, _CLOCK["now"], set(), [])
    assert not [x for x in imp if adv in x[1]], imp
    _CLOCK["now"] = datetime.combine(TODAY, time(10, 5))
    block = D.render_block(plan, shown={})
    nxt = next((ln for ln in block.splitlines() if ln.startswith(("Now", "Next")) and
                "grant" in ln), "")
    assert "a suggestion only" in nxt, block


@check("review #13: a cliff past its date is never a must, even from today's list")
def _():
    _fresh("cliff", flags={"ranking_v2": True})
    t = _id(O.open_task("Donate to the school fund", kind="deadline", due=_d(-1), stakes="vital",
                        costs={"social": "major"}, shape="cliff", costs_source="stated"))
    a = _assess(_task(t))
    assert not a["must"] and a["cod"] == 0, a
    assert t not in _refs(_v2())


if __name__ == "__main__":
    passed = sum(1 for _, ok, _ in _results if ok)
    for name, ok, err in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if err:
            print("        " + err.replace("\n", "\n        "))
    print(f"\n{passed} passed, {len(_results) - passed} failed, {len(_results)} total")
    sys.exit(0 if passed == len(_results) else 1)
