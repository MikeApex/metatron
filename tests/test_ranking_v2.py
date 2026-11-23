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
    # One deliberate difference: the billed lookup is ON in the file (Mike, 129f3fb) and OFF in
    # the fallback — a broken file must not start a per-query charge (plan § 11b, Fable #1).
    assert raw["lookups"]["enabled"] is True and RK._DEFAULTS["lookups"]["enabled"] is False
    merged["lookups"]["enabled"] = False
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
    c = RK.cfg()
    assert c["buffer"]["learn"]["enabled"] is True                 # on, and inert until the flip
    _CLOCK["now"] = datetime.combine(TODAY - timedelta(days=2), time(9, 0))
    t = _id(O.open_task("Write the funding report", kind="deadline", due=_d(3), minutes=240,
                        costs={"financial": "major"}, costs_source="stated"))
    _CLOCK["now"] = datetime.combine(TODAY, time(9, 0))
    assessed = {t: _assess(_task(t))}
    assert assessed[t]["must"], assessed
    # Owed 3 (§ 11b): never in shadow — the start was not one the user was shown …
    st: dict = {}
    assert RK.observe(st, [_task(t)], TODAY, c, assessed, placed={t}, live=False) is False
    # … never for a task not placed in the plan …
    assert RK.observe(st, [_task(t)], TODAY, c, assessed, placed=set(), live=True) is False
    # … live and placed as a must: tracked from today, the day the user was told to start.
    assert RK.observe(st, [_task(t)], TODAY, c, assessed, placed={t}, live=True)
    assert st["buffer"]["tracking"][t]["since"] == TODAY.isoformat()
    # 240 min over 120 free = 2 raw days; the long tier allots ⌈2 × 1.65⌉ = 4 whole days.
    assert RK.allotted_days(2.0, 0.65) == 4
    # Done on the last allotted day reads 0 — phase 1's measure read +0.19 here (log 4/2 − log 1.65).
    _CLOCK["now"] += timedelta(days=3)
    O.update_task(t, "done", evidence="sent it")
    RK.observe(st, [O._norm(x) for x in O._load(None)], TODAY + timedelta(days=3), c, {},
               live=True)
    assert st["buffer"]["obs"] == [0.0], st["buffer"]
    # Done two days late: log(6 / 4) — the user's own "starts late", learned.
    st2: dict = {}
    _fresh("learn2")
    _CLOCK["now"] = datetime.combine(TODAY - timedelta(days=2), time(9, 0))
    t2 = _id(O.open_task("Write the funding report", kind="deadline", due=_d(3), minutes=240,
                         costs={"financial": "major"}, costs_source="stated"))
    _CLOCK["now"] = datetime.combine(TODAY, time(9, 0))
    # Fable #7: opened today (or due today) it is past its own start — never tracked.
    t3 = _id(O.open_task("Draft the board pack", kind="deadline", due=_d(3), minutes=240,
                         costs={"financial": "major"}, costs_source="stated"))
    assert RK.observe({}, [_task(t3)], TODAY, c, {t3: _assess(_task(t3))}, placed={t3},
                      live=True) is False
    RK.observe(st2, [_task(t2)], TODAY, c, {t2: _assess(_task(t2))}, placed={t2}, live=True)
    _CLOCK["now"] = datetime.combine(TODAY + timedelta(days=5), time(9, 0))
    O.update_task(t2, "done", evidence="sent it")
    RK.observe(st2, [O._norm(x) for x in O._load(None)], TODAY + timedelta(days=5), c, {},
               live=True)
    assert _close(st2["buffer"]["obs"][0], math.log(6 / 4), 0.001), st2["buffer"]


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


# --- PHASE 2 (plan §§ 4.5, 4.9, 4.10, 11 rows 10–14, 11a owed items, 11b) ----------------------------

_EVENING = """\
day: [{days: all, wake: "07:00", bed: "22:00"}]
windows:
  - {activity: family, days: all, from: "19:00", to: "21:00", strength: protected}
"""
_P2 = {"ranking_v2": True, "protected_v2": True}


def _tax(what: str = "Pay the tax bill", due: int = 0, grade: str = "severe") -> str:
    return _id(O.open_task(what, kind="deadline", due=_d(due), minutes=15, stakes="vital",
                           activity="admin", costs={"financial": grade}, costs_source="stated"))


@check("7 (as amended, § 11 rows 10–11): the k-th intrusion costs base × k^1.5, fading on a 3.5-day "
       "half-life — a severe task due today (90) is asked about family time once (30) and a second "
       "time the same week (≈ 85), kept out the third (≈ 156); each class has its own base")
def _():
    _fresh("intrusion_maths")
    c = RK.cfg()
    now = datetime.combine(TODAY, time(19, 0))
    st: dict = {}
    assert RK.intrusion_cost("family", st, now, c) == (30.0, 1.0)
    assert RK.note_intrusion(st, "family", "t1", "protected:family:1900", TODAY, now, c)
    assert not RK.note_intrusion(st, "family", "t1", "protected:family:1900", TODAY, now, c)  # once a day
    second, k = RK.intrusion_cost("family", st, now, c)
    assert k == 2.0 and _close(second, 30 * 2 ** 1.5, 0.01) and second < 90, second
    RK.note_intrusion(st, "family", "t2", "protected:family:1900", TODAY, now, c)
    third, _k = RK.intrusion_cost("family", st, now, c)
    assert third > 90, third                                         # the third is kept out
    # The decay: a week on, two intrusions have faded to a quarter each.
    later, k = RK.intrusion_cost("family", st, now + timedelta(days=7), c)
    assert _close(k, 1.5, 0.001) and _close(later, 30 * 1.5 ** 1.5, 0.01), (k, later)
    # The task being decided is never counted against its own place.
    assert RK.intrusion_k(st, "family", now, c, skip=("t2", TODAY.isoformat())) == 2.0
    # Classes: rest and own time 18, exercise 12, anything else the placeholder 18; holds and a
    # childcare duty are family.
    assert RK.intrusion_cost("exercise", {}, now, c)[0] == 12.0
    assert RK.intrusion_cost("own", {}, now, c)[0] == 18.0 == RK.intrusion_cost("social", {}, now, c)[0]
    assert RK.window_class({"kind": "hold", "activities": ["family"]}) == "family"
    assert RK.window_class({"kind": "duty", "activities": ["family"]}) == "family"
    assert RK.window_class({"kind": "protected", "activities": ["exercise", "rest"]}) == "exercise"


@check("7 live: a severe task due today with only family time left is ASKED, never placed silently; "
       "the question carries a recommendation; answer_ask yes places it and the intrusion is counted; "
       "the second such task the same week is asked again, the third is kept out")
def _():
    _fresh("intrusion_live", flags=_P2, shape=_EVENING)
    _CLOCK["now"] = datetime.combine(TODAY, time(18, 55))
    t = _tax()
    plan = D.current(_PERSONA)
    assert not [b for b in plan["blocks"] if b["kind"] == "task"], "placed silently"
    asks = plan["intrusion_asks"]
    assert len(asks) == 1 and asks[0]["task_id"] == t and asks[0]["recommend"] == "yes", asks
    assert asks[0]["class"] == "family" and asks[0]["cost"] == 30.0 and asks[0]["cod"] == 90.0
    assert any("waiting on the user" in u["reason"] for u in plan["unplaced"]), plan["unplaced"]
    shown: dict = {}
    block = D.render_block(plan, shown=shown)
    assert f"answer_ask `{asks[0]['id']}`" in block and "suggest yes" in block, block
    assert "90" not in block.split("Asks")[1].split("\n")[0], "a cost number reached the model"
    assert shown["prompts"] == [asks[0]["id"]]
    D.after_render(_PERSONA, shown)
    assert asks[0]["id"] in RK.load_state(_PERSONA)["prompts"][TODAY.isoformat()]
    # Refusals: no evidence, an unknown id, another time that is not a later day.
    assert D.answer_ask(asks[0]["id"], "yes").startswith("error: `evidence`")
    assert D.answer_ask("in-nope", "yes", evidence="ok").startswith("error: no open question")
    assert D.answer_ask(asks[0]["id"], "other_time", when=TODAY.isoformat(),
                        evidence="later").startswith("error: `when`")
    out = D.answer_ask(asks[0]["id"], "yes", evidence="yes, do it after dinner")
    assert out.startswith("recorded"), out
    _CLOCK["now"] += timedelta(minutes=1)
    plan = D.current(_PERSONA)
    tb = [b for b in plan["blocks"] if b["kind"] == "task"]
    assert len(tb) == 1 and tb[0]["displaced_protected"] and tb[0]["intrusion"]["class"] == "family", tb
    assert not plan["intrusion_asks"]
    st = RK.load_state(_PERSONA)
    assert [e["task_id"] for e in st["intrusions"]] == [t], st.get("intrusions")
    # The second severe task today: k = 2 → ≈ 84.9 < 90, asked again.
    t2 = _tax("Pay the VAT bill")
    _CLOCK["now"] += timedelta(minutes=1)
    plan = D.current(_PERSONA)
    a2 = [x for x in plan["intrusion_asks"] if x["task_id"] == t2]
    assert a2 and _close(a2[0]["cost"], 84.85, 0.1), plan["intrusion_asks"]
    D.answer_ask(a2[0]["id"], "yes", evidence="fine, that one too")
    _CLOCK["now"] += timedelta(minutes=1)
    plan = D.current(_PERSONA)
    # The third: k = 3 → ≈ 155.9 > 90, kept out — and nothing to ask.
    t3 = _tax("Pay the council tax")
    _CLOCK["now"] += timedelta(minutes=1)
    plan = D.current(_PERSONA)
    assert not [x for x in plan["intrusion_asks"] if x["task_id"] == t3], plan["intrusion_asks"]
    kept = [x for x in plan["intrusions"] if x["task_id"] == t3]
    assert kept and kept[0]["decision"] == "kept_out", plan["intrusions"]
    assert t3 not in {b.get("task_id") for b in plan["blocks"] if b["kind"] == "task"}


@check("7: no — the time stays theirs and the task is not asked again today; another day defers it "
       "to that day; a task due later is recommended for a later day; advance work never asks")
def _():
    _fresh("intrusion_no", flags=_P2, shape=_EVENING)
    _CLOCK["now"] = datetime.combine(TODAY, time(18, 55))
    t = _tax()
    plan = D.current(_PERSONA)
    aid = plan["intrusion_asks"][0]["id"]
    assert D.answer_ask(aid, "no", evidence="no, that's family time").startswith("recorded")
    _CLOCK["now"] += timedelta(minutes=1)
    plan = D.current(_PERSONA)
    assert not plan["intrusion_asks"] and t not in {b.get("task_id") for b in plan["blocks"]}
    assert [x["decision"] for x in plan["intrusions"]] == ["declined"], plan["intrusions"]
    # A must by slack, due in three days: the advice is a later day, no later than its date.
    _fresh("intrusion_later", flags=_P2, shape=_EVENING)
    _CLOCK["now"] = datetime.combine(TODAY, time(18, 55))
    a = {"due": _d(3), "slack": 2.4, "must": True}
    assert RK.intrusion_advice(a, TODAY) == ("other_time", _d(2))
    assert RK.intrusion_advice({"due": _d(0), "slack": 0.0}, TODAY) == ("yes", None)
    t = _tax()
    plan = D.current(_PERSONA)
    aid = plan["intrusion_asks"][0]["id"]
    out = D.answer_ask(aid, "other_time", when=_d(1), evidence="tomorrow")
    # Due today: defer refuses a day past its date — the answer says to reschedule first.
    assert out.startswith("error: not moved"), out
    # Advance work never enters protected time and never asks.
    _fresh("intrusion_adv", flags=_P2, shape=_EVENING)
    _CLOCK["now"] = datetime.combine(TODAY, time(18, 55))
    adv = _tax("Draft the grant application", due=6)
    plan = D.current(_PERSONA)
    assert not plan.get("intrusion_asks") and adv not in {b.get("task_id") for b in plan["blocks"]}


@check("7 shadow: with protected_v2 off, today's rule still places the essential task in family time, "
       "and the trace says protected_v2 would have asked; the report prints it")
def _():
    _fresh("intrusion_shadow", flags={"ranking_v2": False}, shape=_EVENING)
    _CLOCK["now"] = datetime.combine(TODAY, time(18, 55))
    t = _tax()
    plan = D.current(_PERSONA)
    tb = [b for b in plan["blocks"] if b["kind"] == "task"]
    assert tb and tb[0]["displaced_protected"], plan["blocks"]
    assert "intrusion_asks" not in plan
    rows = plan["shadow_protected"]
    assert rows and rows[0]["task_id"] == t and rows[0]["would"] == "ask", rows
    assert RK.load_state(_PERSONA)["trace"][TODAY.isoformat()]["protected"][t]["would"] == "ask"
    # Part A's real displacement counts toward k, so the flip starts honest.
    assert [e["task_id"] for e in RK.load_state(_PERSONA)["intrusions"]] == [t]
    import scripts.ranking_report as RR
    text = RR.trace(_PERSONA, TODAY, "protected")
    assert "Pay the tax bill" in text and "→ ask" in text, text


@check("cap (§ 11 row 13): at most 3 system-started prompts a day; one already admitted shows again "
       "freely")
def _():
    _fresh("cap")
    c = RK.cfg()
    st: dict = {}
    assert RK.admit_prompts(st, TODAY, ["a", "b"], c) == ["a", "b"]
    assert RK.admit_prompts(st, TODAY, ["a", "c", "d"], c) == ["a", "c"]
    assert RK.prompt_room(st, TODAY, c)[1] == 0
    assert RK.admit_prompts(st, TODAY + timedelta(days=1), ["d"], c) == ["d"]   # a new day


@check("6 (§ 11 row 12): behind = ≥ 3 overdue, or the top task skipped on 2 of the last 3 days")
def _():
    _fresh("behind_state")
    c = RK.cfg()
    for w in ("Return the passport form", "Renew the parking permit"):
        _id(O.open_task(w, kind="deadline", due=_d(-2), stakes="vital", stakes_source="stated"))
    tasks = [O._norm(t) for t in O._load(None)]
    assert not RK.behind_state(tasks, TODAY, {}, c)["behind"]
    top = _id(O.open_task("Write the grant bid", kind="deadline", due=_d(4), stakes="vital"))
    tasks = [O._norm(t) for t in O._load(None)]
    st = {"top": {_d(-1): top, _d(-3): top}}
    b = RK.behind_state(tasks, TODAY, st, c)
    assert b["behind"] and b["top_skipped"] == 2 and "skipped 2" in b["why"], b
    _id(O.open_task("Pay the dentist invoice", kind="deadline", due=_d(-1), stakes="vital",
                    stakes_source="stated"))
    tasks = [O._norm(t) for t in O._load(None)]
    b = RK.behind_state(tasks, TODAY, {}, c)
    assert b["behind"] and b["overdue"] == 3 and "3 overdue" in b["why"], b
    # A top task done on its day was not skipped.
    O.update_task(top, "done", evidence="sent")
    assert not RK._skipped_on(_task(top), TODAY)


@check("6 live: while behind, the day leads with the quick wins — a ≤ 10-minute step of the hard task "
       "first, ≤ 20 minutes in all — then the hard task; off, the shadow says so instead")
def _():
    for acting in (True, False):
        flags = {"ranking_v2": True, "behind_v2": acting}
        _fresh(f"behind_live_{acting}", flags=flags)
        _CLOCK["now"] = datetime.combine(TODAY, time(9, 0))
        for w in ("Return the library books", "Renew the parking permit", "Pay the dentist invoice"):
            _id(O.open_task(w, kind="deadline", due=_d(-1), minutes=20, stakes="vital",
                            costs={"financial": "major"}, costs_source="stated"))
        hard = _id(O.open_task("Write the grant bid", kind="deadline", due=_d(0), minutes=120,
                               stakes="vital", activity="focus", costs={"financial": "severe"},
                               costs_source="stated"))
        O.open_plan([{"key": "a", "what": "Open the grant form", "due": _d(0), "minutes": 10,
                      "part_of": hard}], _PERSONA)
        step = next(t["id"] for t in O._load(None) if t.get("part_of") == hard)
        O.update_task(step, "set_costs", costs={"financial": "minor"}, costs_source="stated")
        quick = _id(O.open_task("Reply to the plumber", kind="deadline", due=_d(0), minutes=5,
                                stakes="missable", costs={"social": "minor"}, costs_source="stated"))
        plan = D.current(_PERSONA)
        starts = {b["task_id"]: b["start"] for b in plan["blocks"] if b["kind"] == "task"}
        if acting:
            b = plan["behind"]
            assert b["behind"] and b["hard"] == hard and b["quick_wins"][0] == step, b
            assert b["first_step"] and quick in b["quick_wins"], b
            assert starts[step] < starts[hard] and starts[quick] < starts[hard], starts
            assert "shadow_behind" not in plan
        else:
            sb = plan["shadow_behind"]
            assert sb["behind"] and sb["hard"] == hard and sb["quick_wins"][0] == step, sb
            assert "behind" not in plan
            import scripts.ranking_report as RR
            text = RR.trace(_PERSONA, TODAY, "behind")
            assert "behind: YES" in text and "Open the grant form" in text, text


@check("raise (§ 11 row 13): a task skipped twice is raised; said twice with no news it goes to the "
       "weekly list and is not raised again; new information starts the count again; while behind "
       "only a severe task out of slack is raised")
def _():
    _fresh("raises")
    c = RK.cfg()
    t = _id(O.open_task("Book the boiler service", kind="deadline", due=_d(5), stakes="vital",
                        costs={"financial": "major"}, costs_source="stated"))
    tasks = [O._norm(x) for x in O._load(None)]
    one = {t: {"days": 1, "first": _d(-1)}}
    two = {t: {"days": 2, "first": _d(-2)}}
    assert RK.raise_candidates(tasks, one, {}, TODAY, {}, c, False) == ([], [])
    out, wk = RK.raise_candidates(tasks, two, {}, TODAY, {}, c, False)
    assert out == [(t, "skipped 2 days")] and wk == [], out
    st: dict = {}
    RK.note_raised(st, tasks, [t], TODAY - timedelta(days=2))
    RK.note_raised(st, tasks, [t], TODAY - timedelta(days=1))
    assert st["raises"][t]["n"] == 2
    out, wk = RK.raise_candidates(tasks, two, {}, TODAY, st, c, False)
    assert out == [] and wk == [t], (out, wk)
    RK.to_weekly(st, wk, TODAY)
    assert RK.raise_candidates(tasks, two, {}, TODAY, st, c, False) == ([], [])
    O.update_task(t, "reschedule", new_due=_d(9), evidence="the engineer is busy until then")
    tasks = [O._norm(x) for x in O._load(None)]
    out, _w = RK.raise_candidates(tasks, two, {}, TODAY, st, c, False)
    assert out == [(t, "skipped 2 days")], out                     # news: counting again
    # Behind: the skipped one waits; a severe one out of slack is still raised.
    sev = _id(O.open_task("File the tax return", kind="deadline", due=_d(1), minutes=600,
                          stakes="vital", costs={"legal": "severe"}, costs_source="stated"))
    tasks = [O._norm(x) for x in O._load(None)]
    out, _w = RK.raise_candidates(tasks, two, {sev: "severe"}, TODAY, {}, c, True)
    assert out == [(sev, "its slack has run out")], out
    out, _w = RK.raise_candidates(tasks, two, {sev: "major"}, TODAY, {}, c, True)
    assert out == [], out


@check("raise live: under behind_v2 the brief raises a task skipped twice (not once, as Part A does), "
       "admitted under the day's cap; a reply that says it counts it")
def _():
    _fresh("raise_live", flags={"ranking_v2": True, "behind_v2": True})
    t = _id(O.open_task("Book the boiler service", kind="deadline", due=_d(0), stakes="vital",
                        costs={"financial": "major"}, costs_source="stated"))
    plan = D.current(_PERSONA)
    with D._locked(_PERSONA):
        st = D._load_state(_PERSONA)
        st["slips"] = {t: {"first": _d(-1), "days": 1, "last": _d(-1)}}
        D._write_json(D._state_path(_PERSONA), st)
    shown: dict = {}
    assert "skipped" not in D.render_block(plan, kind="morning_brief", shown=shown)
    assert not shown.get("slips")
    with D._locked(_PERSONA):
        st = D._load_state(_PERSONA)
        st["slips"][t] = {"first": _d(-2), "days": 2, "last": _d(-1)}
        D._write_json(D._state_path(_PERSONA), st)
    shown = {}
    block = D.render_block(plan, kind="morning_brief", shown=shown)
    assert "Book the boiler service" in block and "skipped 2 days" in block, block
    assert f"raise:{t}" in shown["prompts"] and shown["slips"] == [t]
    D.after_render(_PERSONA, shown)
    D.note_said("The boiler service has slipped two days — book it now, or drop it?", _PERSONA)
    assert RK.load_state(_PERSONA)["raises"][t]["n"] == 1


@check("owed 1: a promise with no date shows its assumed date in the Tasks section and list_tasks — "
       "under ranking_v2 only")
def _():
    _fresh("implied_show", flags={"ranking_v2": True})
    t = _id(O.open_task("Send Mum the photos", kind="deadline", minutes=5,
                        costs={"social": "major"}, bears="close", costs_source="stated"))
    want = (TODAY + timedelta(days=3)).isoformat()
    block = O.context_block()
    assert "Promised with no date" in block and f"`{t}` Send Mum the photos — by {want}" in block, block
    assert f"assumed by {want}" in O.list_tasks()
    C._OVERRIDE["flags"]["ranking_v2"] = False
    assert "Promised with no date" not in (O.context_block() or "")
    assert "assumed by" not in O.list_tasks()


@check("owed 2: the current undated step of an active goal is advance work — one per goal, under the "
       "floor (a major step offered, a minor one not); a goal no longer live offers none")
def _():
    d = _fresh("undated_steps", flags={"ranking_v2": True})
    (d / "config" / "goals.yaml").write_text(
        "quarterly:\n  - {id: q1, title: Get fit, status: active}\n"
        "  - {id: q2, title: Learn Spanish, status: active}\n"
        "  - {id: q3, title: Old idea, status: dropped}\n")
    O._GOAL_CACHE.update(key=None)
    a = _id(O.open_task("Find a running club", kind="deadline", goal_id="q1",
                        costs={"health": "major"}, costs_source="stated"))
    _CLOCK["now"] += timedelta(minutes=1)
    _id(O.open_task("Buy running shoes", kind="deadline", goal_id="q1",
                    costs={"health": "major"}, costs_source="stated"))
    _id(O.open_task("Pick a phrasebook", kind="deadline", goal_id="q2",
                    costs={"psychological": "minor"}, costs_source="stated"))
    _id(O.open_task("Sketch the old idea", kind="deadline", goal_id="q3",
                    costs={"psychological": "major"}, costs_source="stated"))
    v2 = _v2()
    assert _refs(v2) == [a], [(c["what"], c["v2"]["cod"]) for c in v2]
    e = v2[0]
    assert e["advance"] and not e["essential"] and e["v2"]["undated_step"] and e["v2"]["cod"] == 15.0


@check("owed 4: a non-focus task placed inside a focus window keeps a 15-minute attention block — "
       "nothing else lands in its refocus time; off, Part A's 5-minute transition")
def _():
    shape = ('day: [{days: all, wake: "07:00", bed: "10:00"}]\nwindows:\n'
             '  - {activity: focus, days: all, from: "07:00", to: "09:00", strength: preferred}\n'
             'meals: []\n')
    for on in (True, False):
        _fresh(f"focus_pad_{on}", flags={"ranking_v2": on}, shape=shape)
        for w in ("Pay the gas bill", "Pay the water bill"):
            _id(O.open_task(w, kind="deadline", due=_d(0), minutes=5, stakes="vital",
                            activity="admin", costs={"financial": "major"}, costs_source="stated"))
        plan = D.current(_PERSONA)
        tb = sorted((b for b in plan["blocks"] if b["kind"] == "task"), key=lambda b: b["start"])
        gap = (D._dt(tb[1]["start"]) - D._dt(tb[0]["start"])).total_seconds() / 60
        if on:
            assert gap >= 15 and tb[0].get("attention_minutes") == 15, tb
        else:
            assert gap == 10 and "attention_minutes" not in tb[0], tb


@check("rewards (§ 4.9, row 14): something the user enjoys goes within 15 minutes after an effortful "
       "task; nothing says reward; off, nothing changes")
def _():
    for on in (True, False):
        _fresh(f"enjoyed_{on}", flags={"ranking_v2": on})
        _CLOCK["now"] = datetime.combine(TODAY, time(9, 0))
        walk = _id(O.open_task("Walk round the park", kind="deadline", due=_d(0), minutes=20,
                               stakes="missable", activity="rest", enjoyed=True,
                               costs={"psychological": "minor"}, costs_source="stated"))
        assert _task(walk).get("enjoyed") is True
        rep = _id(O.open_task("Write the quarterly report", kind="deadline", due=_d(0), minutes=60,
                              stakes="vital", activity="focus", costs={"financial": "major"},
                              costs_source="stated"))
        plan = D.current(_PERSONA)
        b = {x["task_id"]: x for x in plan["blocks"] if x["kind"] == "task"}
        gap = (D._dt(b[walk]["start"]) - D._dt(b[rep]["end"])).total_seconds() / 60
        if on:
            assert 0 <= gap <= 15 and b[walk].get("paired"), (gap, b)
            assert "reward" not in D.render_full(plan).lower() + D.render_block(plan, shown={}).lower()
        else:
            assert "paired" not in b[walk]
    # set_activity carries enjoyed alone, and false clears it.
    out = O.update_task(walk, "set_activity", enjoyed=False)
    assert not out.startswith("error") and "enjoyed" not in _task(walk), out


@check("10 (R7): the lookup guard refuses only full personal identifiers — 'Grace School' passes with "
       "a contact named Grace, 'Grace Hopper' (a contact's full name) is refused, as are an email, a "
       "phone, an address, an account number and, by default, a money or health figure; dates and "
       "organisations pass")
def _():
    import tools.lookup_guard as LG
    d = _fresh("guard")
    (d / "crm").mkdir(exist_ok=True)
    (d / "crm" / "contacts.json").write_text(json.dumps([
        {"id": "c1", "first_name": "Grace", "last_name": "Hopper", "name": "Grace Hopper"}]))
    ok = ["When is the Grace School annual fund deadline?",
          "How long does a UK passport renewal take in December?",
          "Is the council's recycling centre open on 2026-12-26?",
          "What time does Kew Gardens close in winter?"]
    for q in ok:
        assert LG.check(q) is None, (q, LG.check(q))
    bad = {"Gift ideas for Grace Hopper's birthday": "full name",
           "Is grace   hopper on the school board?": "full name",
           "Who owns ann@example.com?": "email",
           "Whose number is 07700 900123?": "phone",
           "Parking near 14 Elm Grove Road": "address",
           "Bus routes to SW1A 1AA": "address",
           "Why was account 12345678 charged?": "account",
           "Is £640 fair for brakes on a 2019 Golf?": "money",
           "Is a resting heart rate of 52 bpm normal?": "health",
           "Is 140/90 high blood pressure?": "health"}
    for q, kind in bad.items():
        why = LG.check(q)
        assert why, q
        if kind in ("full name", "money", "health", "email"):
            assert kind in why, (q, why)
    # Figures pass when the switch is off (Mike's call 2 — one line in ranking.yaml).
    assert LG.check("Is £640 fair for brakes on a 2019 Golf?", refuse_figures=False) is None
    assert LG.check("Gift ideas for Grace Hopper", refuse_figures=False)   # names never pass


@check("10 live: lookup_public_fact asks the Research Agent only through the guard, under the daily "
       "cap, and wraps what comes back as outside content; a refusal sends nothing and costs nothing")
def _():
    import core.orchestrator as ORC
    import core.spend_guard as SG
    import tools.lookup_guard as LG
    _fresh("lookup")
    sent: list = []
    saved = (ORC.run_session, SG.check_before_session)
    ORC.run_session = lambda agent, user_input="", **k: sent.append((agent, user_input)) or "About six weeks."
    SG.check_before_session = lambda: None
    try:
        # Off at deploy (Fable #1): nothing is sent until Mike turns it on.
        assert LG.lookup_public_fact("How long does a passport take?").startswith("not available")
        assert not sent
        RK._OVERRIDE = {"lookups": {"enabled": True}}
        out = LG.lookup_public_fact("Is £640 fair for brakes on a 2019 Golf?")
        assert out.startswith("refused") and "money" in out and not sent, out
        out = LG.lookup_public_fact("How long does a UK passport renewal take?")
        assert sent == [("research_agent", "How long does a UK passport renewal take?")], sent
        assert "<untrusted_content" in out and "About six weeks." in out, out
        for _i in range(4):
            LG.lookup_public_fact("How long does a UK passport renewal take?")
        assert len(sent) == 5
        out = LG.lookup_public_fact("When does the school term start?")
        assert out.startswith("refused") and "lookups are used" in out and len(sent) == 5, out
        # A lookup that never ran gives its place back (Fable #11).
        _fresh("lookup_fail")
        RK._OVERRIDE = {"lookups": {"enabled": True}}
        ORC.run_session = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down"))
        assert LG.lookup_public_fact("How long does a passport take?").startswith("the lookup did not")
        assert RK.load_state(_PERSONA)["lookups"]["n"] == 0
    finally:
        ORC.run_session, SG.check_before_session = saved


@check("11 (§ 4.8): an inferred passion never lifts a grade; a stated one lifts psychological and "
       "social by exactly one step — named on the record, or through the goal it is tied to; a "
       "'stated' passion that the cited mission or goal does not name is kept inferred; the judge "
       "sees stated passions only")
def _():
    import tools.profile as PR
    d = _fresh("passions", flags={"ranking_v2": True})
    PR.persona_config_dir = lambda persona=None, _d=d: _d / "config"
    (d / "config" / "goals.yaml").write_text(
        "quarterly:\n  - {id: q1, title: Grow our own vegetables in the garden, status: active}\n")
    O._GOAL_CACHE.update(key=None)
    (d / "config" / "mission.md").write_text("Make music most weeks; raise the children well.\n")
    import tools.turn_context as TC
    t = _id(O.open_task("Repot the tomato seedlings", kind="deadline", due=_d(0),
                        costs={"psychological": "minor", "financial": "minor"},
                        passion="gardening", costs_source="inferred"))
    base = _assess(_task(t))["G"]
    out = PR.write_profile("passions", "gardening", source="inferred")
    assert "(inferred)" in out, out
    v = [c for c in _v2() if c["task_id"] == t][0]["v2"]
    assert v["G"] == base and "passion" not in v, v                  # inferred never lifts
    out = PR.write_profile("passions", "gardening", source="stated", basis="chat")
    assert "(inferred)" in out and "nothing from the user" in out, out   # no turn: fail-closed
    with TC.turn_scope(True):
        out = PR.write_profile("passions", "gardening", source="stated", basis="chat")
    assert "(stated)" in out, out
    v = [c for c in _v2() if c["task_id"] == t][0]["v2"]
    lifted = RK.importance({"psychological": "major", "financial": "minor"}, RK.cfg())
    assert v["passion"] == "gardening" and v["G"] == lifted, (v, lifted)   # one step, not two
    assert RK.lift({"social": "severe", "financial": "minor"}) == {"social": "severe",
                                                                   "financial": "minor"}
    # Tied to a goal: a task on q1 is lifted with no `passion` on its record.
    out = PR.write_profile("passions", "vegetable growing", source="stated", basis="q1")
    assert "(stated)" in out and PR.stated_passions()[-1]["goals"] == ["q1"], out
    g = _id(O.open_task("Order the seed potatoes", kind="deadline", due=_d(0), goal_id="q1",
                        costs={"social": "minor"}, costs_source="inferred"))
    assert [c for c in _v2() if c["task_id"] == g][0]["v2"].get("passion") == "vegetable growing"
    # The mission names music, not chess: chess stays inferred.
    assert "(stated)" in PR.write_profile("passions", "music", source="stated", basis="mission")
    out = PR.write_profile("passions", "chess", source="stated", basis="mission")
    assert "(inferred)" in out and "does not name" in out, out
    # Fable #6: one shared word is not naming ("chess with the children" vs "raise the children");
    # re-recording a stated passion against a goal that does not name it does not tie it.
    assert "(inferred)" in PR.write_profile("passions", "chess with the children", source="stated",
                                            basis="mission")
    PR.write_profile("passions", "music", source="inferred", basis="q1")
    assert not next(r for r in PR.stated_passions() if r["what"] == "music").get("goals")
    # Fable #12: the user's own stated grade is never lifted.
    u = _id(O.open_task("Tune the guitar", kind="deadline", due=_d(0), passion="music",
                        costs={"psychological": "minor"}, costs_source="stated"))
    assert "passion" not in [c for c in _v2() if c["task_id"] == u][0]["v2"]
    # The judge: stated passions only, and it may name only one of them.
    payload = TJ._payload([_task(t)], _PERSONA, {t: ("costs",)})
    assert set(payload["passions"]) == {"gardening", "vegetable growing", "music"}, payload
    assert "passion" in payload["rules"] and "do not raise it" in payload["rules"]["costs"]
    assert TJ._known_passion("Gardening") == "gardening" and TJ._known_passion("chess") is None


@check("review (phase 2) #2: a daily dose or a multi-day task is never the 'top task' that makes the "
       "user behind; #3: a protected-time question wakes the user, and one past the cap is not "
       "called 'waiting'; #10: tomorrow's draft asks nothing")
def _():
    _fresh("top_behind", flags={"ranking_v2": True})
    dose = _id(O.open_task("Take the morning tablet", kind="habit", every="day", minutes=5,
                           costs={"health": "severe"}, costs_source="stated"))
    long = _id(O.open_task("Write the thesis chapter", kind="deadline", due=_d(1), minutes=600,
                           stakes="vital", costs={"psychological": "major"}, costs_source="stated"))
    bill = _id(O.open_task("Pay the phone bill", kind="deadline", due=_d(0), minutes=10,
                           stakes="vital", costs={"financial": "minor"}, costs_source="stated"))
    assert D._top_for_behind([dose, long, bill], _PERSONA) == bill
    # #3
    _fresh("ask_nudge", flags=_P2, shape=_EVENING)
    _CLOCK["now"] = datetime.combine(TODAY, time(18, 55))
    _tax()
    plan = D.current(_PERSONA)
    aid = plan["intrusion_asks"][0]["id"]
    nud = [x for x in plan["suggestions"] if x["id"] == f"nudge:ask:{aid}"]
    assert nud and nud[0]["kind"] == "nudge" and "answer_ask" in nud[0]["why"], plan["suggestions"]
    with D._locked(_PERSONA):
        st = RK.load_state(_PERSONA)
        st["prompts"] = {TODAY.isoformat(): ["a", "b", "c"]}
        RK.save_state(st, _PERSONA)
    block = D.render_block(plan, shown={})
    assert "answer_ask" not in block and "kept out of family time today" in block, block
    # #10: the draft for tomorrow carries no question nobody can answer yet.
    draft = D._build(TODAY + timedelta(days=1), _PERSONA, "reshuffle", [], None, _CLOCK["now"], [],
                     D._candidates(TODAY + timedelta(days=1), _PERSONA), False, draft=True)
    assert "intrusion_asks" not in draft


@check("review (phase 2) #5/#8: the guard catches a full name with a middle name or initial, "
       "surname first, a partner's name; fails closed when the contacts cannot be read; skips an "
       "organisation; and lets ordinary public numbers through")
def _():
    import tools.lookup_guard as LG
    d = _fresh("guard2")
    (d / "crm").mkdir(exist_ok=True)
    (d / "crm" / "contacts.json").write_text(json.dumps([
        {"id": "c1", "first_name": "Grace", "last_name": "Hopper", "spouse_name": "Vincent Foster"},
        {"id": "c2", "name": "Oak Tree Dental", "relationship_type": "business"}]))
    for q in ("Is Grace M. Hopper on the board?", "Grace Brewster Hopper's office hours",
              "Hopper, Grace — school governor?", "Where does Vincent Foster work?"):
        assert LG.check(q) and "full name" in LG.check(q), q
    for q in ("Is Oak Tree Dental open on Saturdays?", "When does the 2025-2026 school term start?",
              "Is the tip open 0900-1700 on Sundays?", "Form 1040 2025 deadline",
              "What is the 23 kg baggage allowance on easyJet?", "Is 100 ml the liquid limit?",
              "How long to roast a 10 lb turkey?"):
        assert LG.check(q) is None, (q, LG.check(q))
    assert LG.check("Is 80 kg a healthy weight?") == "a health reading"
    assert LG.check("Is a 200 mg dose of ibuprofen safe?") == "a health reading"
    (d / "crm" / "contacts.json").write_text("{not json")
    assert "could not be read" in LG.check("How long does a passport take?")


@check("schemas (phase 2): answer_ask is classified as an action and registered; enjoyed is a plan "
       "field; both phase 2 flags ship off")
def _():
    from core import actions
    assert "answer_ask" in actions.ACTION_TOOLS
    assert "enjoyed" in O._PLAN_FIELD_PROPS
    raw = yaml.safe_load((ROOT / "config" / "modules" / "day_plan.yaml").read_text())
    assert raw["flags"]["protected_v2"] is False and raw["flags"]["behind_v2"] is False
    assert D.ANSWER_ASK_SCHEMA["input_schema"]["required"] == ["ask_id", "answer", "evidence"]


# --- phase 3: the back burner, the weekly conversation, signals (plan §§ 4.11–4.13, § 11c) --------

import tools.ranking_review as RR  # noqa: E402
import tools.schedule as SCH  # noqa: E402
from tools.turn_context import turn_scope  # noqa: E402

_P3 = {"back_burner": True, "back_burner_dry_run": False, "weekly_priorities": True,
       "ranking_signals": True}


def _p3(name: str, flags: dict | None = None) -> Path:
    d = _fresh(name, flags)
    RR.persona_data_dir = lambda persona=None, _d=d: _d
    SCH.persona_data_dir = lambda persona=None, _d=d: _d
    return d


def _age(days: int, *tids: str) -> None:
    """Make tasks look `days` old and untouched since: created then, every history event then."""
    then = (datetime.combine(TODAY, time(9, 0)) - timedelta(days=days)).isoformat(timespec="seconds")

    def apply(doc):
        for t in doc["tasks"]:
            if t["id"] in tids:
                t["created_at"] = then
                t["start"] = then[:10]
                for h in t.get("history") or []:
                    h["at"] = then
    O._with_store(None, apply)


def _at(day: date, hh: int = 7) -> None:
    _CLOCK["now"] = datetime.combine(day, time(hh, 0))


def _bb(day: date | None = None) -> dict:
    st = RK.load_state(_PERSONA)
    return ((st.get("trace") or {}).get((day or TODAY).isoformat()) or {}).get("back_burner") or {}


def _ids(rows) -> set:
    return {r["task_id"] for r in rows or []}


@check("phase 3, plan test 12: a 21-day silent trivia task is parked a week after the weekly "
       "conversation says so (7 days' lead); a person-task, a dated cliff and a legal major never are; a fresh "
       "mention reopens the parked one instead of filing it twice")
def _():
    d = _p3("bb12", _P3)
    (d / "crm").mkdir(exist_ok=True)
    (d / "crm" / "contacts.json").write_text(json.dumps([
        {"id": "c1", "first_name": "Grace", "relationship_type": "friend"}]))
    trivia = _id(O.open_task("Fix the wobbly shelf bracket", costs={"psychological": "minor"}, stakes="missable",
                             costs_source="stated"))
    person = _id(O.open_task("Return Grace's cake tin", costs={"social": "minor"}, stakes="missable",
                             costs_source="stated"))
    cliff = _id(O.open_task("Donate to the library appeal", costs={"psychological": "minor"}, stakes="missable",
                            shape="cliff", real_due=_d(5), costs_source="stated"))
    legal = _id(O.open_task("Renew the parking permit", costs={"legal": "major"},
                            costs_source="stated"))
    _age(30, trivia, person, cliff, legal)
    RR.daily(_PERSONA, TODAY)
    bb = _bb()
    assert trivia in _ids(bb["would_archive"]) and not bb.get("park"), bb
    assert {person: "person", legal: "obligation"} == {
        r["task_id"]: r["why"] for r in bb["guarded"]}, bb["guarded"]
    assert cliff not in _ids(bb["would_archive"]) | _ids(bb["guarded"]) | _ids(bb["would_notice"])
    assert _task(trivia)["status"] == "open", "nothing is parked before it has been said"
    # The weekly conversation carries the notice and the guarded lines; the reply says them.
    block = RR.weekly_block(_PERSONA, "weekly_review", weekly=True)
    assert RR._WEEKLY_MARKER in block and "shelf bracket" in block and "back burner next week" in block
    assert block.index("cake tin") < block.index("shelf bracket"), "guarded first"
    assert "parking permit" in block and "money or legal" in block
    RR.note_said("The wobbly shelf bracket hasn't come up in a month — I'll park it next week "
                 "unless you want it kept. And Grace's cake tin: keep, date it, or drop?")
    # Six days on: not yet — the notice is said the week before.
    _at(TODAY + timedelta(days=6))
    RR.daily(_PERSONA, TODAY + timedelta(days=6))
    assert _task(trivia)["status"] == "open"
    _at(TODAY + timedelta(days=7))
    RR.daily(_PERSONA, TODAY + timedelta(days=7))
    t = _task(trivia)
    assert t["status"] == "moot" and t["back_burner"]["silent_days"] >= 21, t
    assert any(h.get("event") == "back_burner" for h in t["history"])
    for tid in (person, cliff, legal):
        assert _task(tid)["status"] == "open", tid
    # Kept, and visible on request; a fresh mention revives it.
    assert "parked" in O.list_tasks(include_closed=True) or "back burner" in O.list_tasks(
        include_closed=True)
    near = O.open_task("Fix the shelf bracket")
    assert "looks like" in near and trivia in near and "update_task reopen" in near, near
    out = O.open_task("Fix the wobbly shelf bracket")
    assert "reopened from the back burner" in out and trivia in out, out
    t = _task(trivia)
    assert t["status"] == "open" and "back_burner" not in t
    assert t["history"][-1]["event"] == "reopened"
    assert sum(1 for x in O._load(None) if "shelf" in x["what"].lower()) == 1


@check("phase 3: the dry run closes nothing and says nothing — the would-park list is in the "
       "trace and the report; notices-only says it but still parks nothing")
def _():
    _p3("bb_dry", {**_P3, "back_burner": False})
    trivia = _id(O.open_task("Sort the spare buttons tin", costs={"psychological": "minor"}, stakes="missable",
                             costs_source="stated"))
    _age(40, trivia)
    RR.daily(_PERSONA, TODAY)
    bb = _bb()
    assert bb["mode"] == "dry run" and trivia in _ids(bb["would_archive"]), bb
    assert "buttons" not in RR.weekly_block(_PERSONA, "weekly_review", weekly=True)
    import scripts.ranking_report as REP
    assert "Sort the spare buttons tin" in REP.back_burner(_PERSONA, TODAY)
    # Notices only: said in the weekly conversation, still never parked.
    C._OVERRIDE = {"flags": {**_FLAGS, **_P3, "back_burner_dry_run": True}}
    assert "buttons" in RR.weekly_block(_PERSONA, "weekly_review", weekly=True)
    RR.note_said("The spare buttons tin can go on the back burner next week.")
    for n in (7, 10):
        _at(TODAY + timedelta(days=n))
        RR.daily(_PERSONA, TODAY + timedelta(days=n))
    assert _task(trivia)["status"] == "open"
    assert _bb(TODAY + timedelta(days=10))["mode"] == "notices only"


@check("phase 3: what counts as a mention — the user's own words reset the clock; Metatron "
       "naming the task in a reply does not")
def _():
    _p3("bb_mention", _P3)
    a = _id(O.open_task("Descale the kettle", costs={"psychological": "minor"}, stakes="missable",
                        costs_source="stated"))
    b = _id(O.open_task("Label the freezer boxes", costs={"psychological": "minor"}, stakes="missable",
                        costs_source="stated"))
    _age(25, a, b)
    O.note_raised("Shall we descale the kettle and label the freezer boxes today?")
    assert O.note_mentioned("I'll descale the kettle tonight") == 1
    RR.daily(_PERSONA, TODAY)
    bb = _bb()
    assert b in _ids(bb["would_archive"]), bb
    assert a not in _ids(bb["would_archive"]) | _ids(bb["would_notice"]), bb
    # An edit to the task is a mention too (code's own judging is not).
    _at(TODAY + timedelta(days=1))
    O.update_task(b, "note", note="the blue ones")
    RR.daily(_PERSONA, TODAY + timedelta(days=1))
    assert b not in _ids(_bb(TODAY + timedelta(days=1)).get("would_archive")), _bb(TODAY + timedelta(days=1))


@check("phase 3: the weekly list reaches the weekly package — 'keep, reschedule or drop?' items, "
       "through the orchestrator's horizon block on a weekly_review turn, and nowhere else")
def _():
    _p3("weekly_pkg", _P3)
    tid = _id(O.open_task("Repaint the gate", due=_d(-4), costs={"psychological": "minor"}, stakes="missable",
                          costs_source="stated"))
    with D._locked(_PERSONA):
        st = RK.load_state(_PERSONA)
        RK.to_weekly(st, [tid], TODAY)
        RK.save_state(st, _PERSONA)
    import core.orchestrator as ORC
    ORC.persona_data_dir = lambda persona=None, _d=_TMP / "weekly_pkg": _d
    ORC.persona_config_dir = lambda persona=None, _d=_TMP / "weekly_pkg": _d / "config"
    text = ORC._horizon_block(_PERSONA, session="weekly_review", user_turn=True)
    assert RR._WEEKLY_MARKER in text and "Repaint the gate" in text
    assert "keep, reschedule or drop?" in text
    assert RR._WEEKLY_MARKER not in ORC._horizon_block(_PERSONA, session="morning_brief",
                                                        user_turn=True)
    RR.note_said("Repaint the gate — keep it, give it a Saturday, or drop it?")
    assert (RK.load_state(_PERSONA)["weekly"][tid]).get("said") == TODAY.isoformat()
    assert "Repaint the gate" not in RR.weekly_block(_PERSONA, "weekly_review", weekly=True)
    C._OVERRIDE = {"flags": {**_FLAGS, **_P3, "weekly_priorities": False}}
    assert RR.weekly_block(_PERSONA, "weekly_review", weekly=True) == ""


@check("phase 3: a user with no weekly review is offered one once, on their own turn; write_schedule "
       "makes it weekly at their day and time, and the turn it opens is the weekly review")
def _():
    d = _p3("weekly_offer", _P3)
    import core.orchestrator as ORC
    ORC.persona_data_dir = lambda persona=None, _d=d: _d
    ORC.persona_config_dir = lambda persona=None, _d=d: _d / "config"
    RR.persona_data_dir = lambda persona=None, _d=d: _d
    import core.persona as CP
    saved = CP.persona_config_dir
    CP.persona_config_dir = lambda persona=None, _d=d: _d / "config"
    try:
        assert RR.weekly_block(_PERSONA, None, user_turn=False) == "", "never on a wake"
        offer = RR.weekly_block(_PERSONA, None, user_turn=True)
        assert "WEEKLY CONVERSATION" in offer and "write_schedule" in offer
        RR.note_said("Would a short weekly look at what to keep or drop help? Pick a day and time.")
        assert RR.weekly_block(_PERSONA, None, user_turn=True) == "", "offered once"
        assert "day + time" in SCH.write_schedule("weekly_review", "x", interval_minutes=600,
                                                  day="sunday", time="18:00")
        assert "weekday" in SCH.write_schedule("weekly_review", "x", day="sun", time="18:00")
        assert "needs day and time" in SCH.write_schedule("w", "x", interval_minutes=600,
                                                          session="weekly_review")
        prompt = "Time for our weekly look at the week together."
        out = SCH.write_schedule("weekly_review", prompt, day="Sunday", time="18:30",
                                 session="weekly_review", reason="their weekly conversation")
        assert "every sunday at 18:30" in out and "task ledger" not in out, out
        job = yaml.safe_load((d / "schedules.yaml").read_text())["weekly_review"]
        assert (job["day"], job["time"], job["session"], job["one_off"]) == (
            "sunday", "18:30", "weekly_review", False)
        import core.scheduler as SD
        assert SD.schedule_key_error(job) is None
        assert ORC.session_kind(prompt, _PERSONA) == "weekly_review"
        assert ORC.carries_weekly_review("weekly_review", _PERSONA)
        assert RR.has_weekly_review(_PERSONA)
        assert "every sunday at 18:30" in SCH.list_schedules()
    finally:
        CP.persona_config_dir = saved


@check("phase 3: signal rows are appended once a day and never rewritten; record_signal keeps the "
       "user's words on their own turn only")
def _():
    d = _p3("signals", _P3)
    t = _id(O.open_task("Pay the council tax", due=_d(-3), costs={"financial": "major"},
                        costs_source="stated"))
    _age(10, t)
    RR.daily(_PERSONA, TODAY)
    path = d / "ranking_signals.jsonl"
    first = path.read_text()
    rows = [json.loads(x) for x in first.splitlines()]
    kinds = {r["kind"] for r in rows}
    assert kinds == {"completion", "momentum", "missed_obligations", "intrusions", "questions",
                     "overrides"}, kinds
    assert all(r["day"] == (TODAY - timedelta(days=1)).isoformat() for r in rows)
    missed = next(r for r in rows if r["kind"] == "missed_obligations")
    assert missed["n"] == 1 and missed["task_ids"] == [t]
    assert oct(path.stat().st_mode & 0o777) == "0o600"
    RR.daily(_PERSONA, TODAY)
    assert path.read_text() == first, "the same day is never written twice"
    with turn_scope(user_turn=False):
        assert RR.record_signal("regret", "I wish I'd rung my brother").startswith("error")
    assert RR.record_signal("regret", "I wish I'd rung my brother").startswith("error"), \
        "no turn bound: refused"
    with turn_scope(user_turn=True):
        assert RR.record_signal("mood", "fine").startswith("error")
        assert RR.record_signal("regret", "I wish I'd rung my brother", asked=True).startswith(
            "recorded")
    _at(TODAY + timedelta(days=1))
    RR.daily(_PERSONA, TODAY + timedelta(days=1))
    now = path.read_text()
    assert now.startswith(first) and len(now.splitlines()) == len(rows) + 1 + 6, \
        "appended, never rewritten"
    said = [json.loads(x) for x in now.splitlines() if '"source": "user"' in x]
    assert said and said[0]["text"] == "I wish I'd rung my brother" and said[0]["asked"] is True
    import scripts.ranking_report as REP
    rep = REP.signals(_PERSONA, TODAY.strftime("%Y-%m"))
    assert "I wish I'd rung my brother" in rep or (TODAY - timedelta(days=1)).month != TODAY.month
    C._OVERRIDE = {"flags": {**_FLAGS, **_P3, "ranking_signals": False}}
    with turn_scope(user_turn=True):
        assert RR.record_signal("regret", "x").startswith("not recorded")


@check("schemas (phase 3): record_signal is classified as an action, registered and granted to the "
       "Synthesizer in both routing files; the back burner ships as the dry run, the weekly look "
       "back and signals on (Mike, 2026-11-23)")
def _():
    from core import actions
    assert "record_signal" in actions.ACTION_TOOLS
    raw = yaml.safe_load((ROOT / "config" / "modules" / "day_plan.yaml").read_text())
    f = raw["flags"]
    assert (f["back_burner"], f["back_burner_dry_run"], f["weekly_priorities"],
            f["ranking_signals"]) == (False, True, True, True)
    for name in ("routing_cloud.yaml", "routing.yaml"):
        r = yaml.safe_load((ROOT / "config" / "modules" / name).read_text())
        syn = next(v for k, v in (r.get("agents") or r).items() if k == "synthesizer")
        assert "record_signal" in syn["allowed_tools"], name
    assert RR.RECORD_SIGNAL_SCHEMA["input_schema"]["required"] == ["kind", "text"]


@check("review (phase 3) #1/#2: a 'keep' answer, or the user naming the task the same day as the "
       "notice, stops it being parked — and it is said again before any later parking")
def _():
    _p3("bb_keep", _P3)
    a = _id(O.open_task("Oil the squeaky hinge", costs={"psychological": "minor"},
                        stakes="missable", costs_source="stated"))
    b = _id(O.open_task("Recycle the old phone chargers", costs={"psychological": "minor"},
                        stakes="missable", costs_source="stated"))
    _age(30, a, b)
    RR.daily(_PERSONA, TODAY)
    RR.weekly_block(_PERSONA, "weekly_review", weekly=True)
    RR.note_said("Oil the squeaky hinge and recycle the old phone chargers: both go on the back "
                 "burner next week unless you want one kept.")
    seen = RK.load_state(_PERSONA)["back_burner"]["seen"]
    assert seen[a]["noticed"] == seen[b]["noticed"] == TODAY.isoformat()
    # "No, keep that one" — recorded as a keep; and the other named by the user the same day.
    assert "kept as it is" in O.update_task(a, "keep", evidence="no, keep that one")
    O.note_mentioned("I'll recycle the old phone chargers this weekend")
    for n in (7, 21):
        _at(TODAY + timedelta(days=n))
        RR.daily(_PERSONA, TODAY + timedelta(days=n))
    assert _task(a)["status"] == "open" and _task(b)["status"] == "open"
    # At day 21 both are due a FRESH notice — back in the weekly block, never parked unannounced.
    block = RR.weekly_block(_PERSONA, "weekly_review", weekly=True)
    assert "squeaky hinge" in block and "phone chargers" in block, block


@check("review (phase 3) #3: unrelated words in a long weekly reply do not count as the notice; "
       "the notice needs the task named and a parking word in one sentence")
def _():
    _p3("bb_words", _P3)
    t = _id(O.open_task("Renew the library card", costs={"psychological": "minor"},
                        stakes="missable", costs_source="stated"))
    _age(30, t)
    RR.daily(_PERSONA, TODAY)
    RR.weekly_block(_PERSONA, "weekly_review", weekly=True)
    RR.note_said("Thursday the library books are due back, and Saturday is the party — you "
                 "still need a card. Renew the library card is on file.")
    assert "noticed" not in RK.load_state(_PERSONA)["back_burner"]["seen"][t]
    RR.note_said("Renewing the library card can go on the back burner next week, unless you "
                 "want it kept.")
    assert RK.load_state(_PERSONA)["back_burner"]["seen"][t]["noticed"] == TODAY.isoformat()


@check("review (phase 3) #4/#5: only the same commitment is revived — a resemblance is put back "
       "to the model; a parked task reopened another way no longer reads as parked")
def _():
    _p3("bb_revive", _P3)
    old = _id(O.open_task("Buy a birthday card for the office", costs={"social": "minor"},
                          stakes="missable", costs_source="stated"))
    _age(30, old)
    RR._park(_PERSONA, [(old, 30)], TODAY)
    assert O._is_parked(_task(old))
    out = O.open_task("Buy a birthday card for Mum", due=_d(4))
    assert "looks like" in out and "new_instance=true" in out and "Nothing was written" in out
    new = _id(O.open_task("Buy a birthday card for Mum", due=_d(4), new_instance=True))
    assert new != old and _task(old)["status"] == "moot"
    # Reopened by update_task (not by a mention): never "parked" again in what Metatron says.
    O.update_task(old, "reopen", evidence="actually I still need that")
    t = _task(old)
    assert t["status"] == "open" and not O._is_parked(t)
    m = RR.weekly_material(_PERSONA, TODAY, RK.load_state(_PERSONA))
    assert not any("parked" in x for x in m["moved"]), m["moved"]
    # The user's own reschedule is not "what Metatron moved".
    O.update_task(new, "reschedule", new_due=_d(6), evidence="I'll get it Saturday instead")
    m = RR.weekly_material(_PERSONA, TODAY, RK.load_state(_PERSONA))
    assert not any("Saturday instead" in x for x in m["moved"]), m["moved"]


@check("review (phase 3) #7/#10: at most two questions a week, the rest a count by kind; in "
       "notices-only mode nothing is announced as being parked")
def _():
    _p3("bb_cap", _P3)
    ids = [_id(O.open_task(w, costs={"psychological": "major"}, costs_source="stated"))
           for w in ("Learn to juggle", "Frame the holiday photos", "Restring the guitar",
                     "Plant tulip bulbs")]
    small = _id(O.open_task("Tidy the cable box", costs={"psychological": "minor"},
                            stakes="missable", costs_source="stated"))
    _age(30, *ids, small)
    RR.daily(_PERSONA, TODAY)
    block = RR.weekly_block(_PERSONA, "weekly_review", weekly=True)
    assert block.count("keep it, give it a date, or drop it?") == 2, block
    assert "2 more to ask about another week" in block and "cable box" in block
    assert "back burner next week" in block
    C._OVERRIDE = {"flags": {**_FLAGS, **_P3, "back_burner_dry_run": True}}
    with D._locked(_PERSONA):
        st = RK.load_state(_PERSONA)
        st["weekly_offered"] = []
        RK.save_state(st, _PERSONA)
    block = RR.weekly_block(_PERSONA, "weekly_review", weekly=True)
    assert "cable box" in block and "next week" not in block.split("cable box")[1].split(";")[0]


@check("review (phase 3) #8/#9: 'next week' in a reply does not spend the offer, the offer shows "
       "at most once a day; a weekly time inside quiet hours is refused")
def _():
    d = _p3("offer2", _P3)
    import core.persona as CP
    import core.scheduler as SD
    saved, saved_cfg = CP.persona_config_dir, SD._load_config
    CP.persona_config_dir = lambda persona=None, _d=d: _d / "config"
    SD._load_config = lambda persona=None: {"quiet_hours": {"start": "22:00", "end": "07:00"}}
    try:
        assert "WEEKLY CONVERSATION" in RR.weekly_block(_PERSONA, None, user_turn=True)
        RR.note_said("You've got the dentist next week, nothing else pressing.")
        assert not RK.load_state(_PERSONA)["weekly_offer"].get("said")
        assert RR.weekly_block(_PERSONA, None, user_turn=True) == "", "once a day"
        _at(TODAY + timedelta(days=1))
        assert "WEEKLY CONVERSATION" in RR.weekly_block(_PERSONA, None, user_turn=True)
        out = SCH.write_schedule("weekly_review", "Time for our weekly look at the week together.",
                                 day="sunday", time="22:30", session="weekly_review")
        assert out.startswith("Error") and "quiet hours" in out, out
        assert not (d / "schedules.yaml").exists()
    finally:
        CP.persona_config_dir, SD._load_config = saved, saved_cfg


@check("review (phase 3) #11: a re-judge does not start the clock again; signals catch up a "
       "missed day; a scheduled turn's text never counts as the user's mention")
def _():
    d = _p3("bb_misc", _P3)
    t = _id(O.open_task("Wax the old skis", costs={"psychological": "minor"}, stakes="missable",
                        costs_source="inferred"))
    _age(30, t)
    RR.daily(_PERSONA, TODAY)
    assert t in _ids(_bb()["would_archive"])

    def judge(doc):
        for x in doc["tasks"]:
            if x["id"] == t:
                x["costs"] = {"psychological": "minor", "social": "minor"}
                x["stakes"] = "missable"
                x.setdefault("history", []).append({"event": "costs_recorded",
                                                    "at": O._stamp(), "by": "task_judge"})
    O._with_store(None, judge)
    _at(TODAY + timedelta(days=1))
    RR.daily(_PERSONA, TODAY + timedelta(days=1))
    assert t in _ids(_bb(TODAY + timedelta(days=1))["would_archive"])
    # Signals: a day skipped is written on the next run, once.
    _at(TODAY + timedelta(days=3))
    RR.daily(_PERSONA, TODAY + timedelta(days=3))
    days = sorted({json.loads(x)["day"] for x in (d / "ranking_signals.jsonl").read_text().splitlines()})
    assert days == [(TODAY + timedelta(days=n)).isoformat() for n in (-1, 0, 1, 2)], days
    # The turn close: a scheduled turn's prompt is not the user's word.
    import core.orchestrator as ORC
    before = _task(t).get("mentioned")
    ORC._close_turn_bookkeeping("Morning.", "Wax the old skis — check on it", True, None)
    assert _task(t).get("mentioned") == before
    ORC._close_turn_bookkeeping("Sure.", "I'll wax the old skis on Friday", False, None)
    assert _task(t).get("mentioned") == (TODAY + timedelta(days=3)).isoformat()


if __name__ == "__main__":
    passed = sum(1 for _, ok, _ in _results if ok)
    for name, ok, err in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if err:
            print("        " + err.replace("\n", "\n        "))
    print(f"\n{passed} passed, {len(_results) - passed} failed, {len(_results)} total")
    sys.exit(0 if passed == len(_results) else 1)
