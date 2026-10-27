"""
tests/test_day_plan_ledger.py — the task ledger's part of the day planner
(archive/plans/day_planner_plan_2026-10-24.md § 4.1): the day boundary, the planner's fields,
`is_essential`, the unconfirmed rule, and the schemas models see. Synthetic data in a temp
directory — no persona data, no live meter. Run it, do not read it:

    python3 tests/test_day_plan_ledger.py
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.day_plan_config as C  # noqa: E402
import tools.goals as G  # noqa: E402
import tools.location as L  # noqa: E402
import tools.obligations as O  # noqa: E402

_results: list[tuple[str, bool, str]] = []
_TMP = Path(tempfile.mkdtemp(prefix="day_plan_ledger_"))
_CLOCK = {"now": datetime(2026, 10, 24, 9, 0, 0)}
O._now = lambda: _CLOCK["now"]

_GOALS = """quarterly:
- id: q1
  title: Ship the Apex migration
  essential: true
- id: q2
  title: Learn the guitar
  essential: false
"""


def _fresh(name: str) -> Path:
    d = _TMP / name
    d.mkdir(parents=True, exist_ok=True)
    O.persona_data_dir = lambda persona=None, _d=d: _d
    (d / "goals.yaml").write_text(_GOALS)
    G._goals_path = lambda _d=d: _d / "goals.yaml"
    L.load_zones = lambda persona=None: [{"name": "gym", "lat": 51.5, "lon": -0.1,
                                         "radius_m": 100}]
    # The planner's ledger fields are exercised as Stage B will run them; the checks that pin
    # Stage A's flag-off behaviour turn the flag off themselves.
    C._OVERRIDE = {"flags": {"ledger_fields": True}}
    return d


# Stage A as shipped — every planner flag off — independent of what config/modules/day_plan.yaml
# says today (its flags were flipped on 2026-10-27; "no override" would now read them).
_SHIPPED: dict = {"flags": {}}


def _flags(**on):
    C._OVERRIDE = {"flags": {"ledger_fields": True, **on}}


def _at(y, m, d, hh=9, mm=0):
    _CLOCK["now"] = datetime(y, m, d, hh, mm, 0)


def check(name: str):
    def deco(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except Exception as exc:  # noqa: BLE001
            _results.append((name, False, f"{type(exc).__name__}: {exc}"))
        finally:
            C._OVERRIDE = _SHIPPED
        return fn
    return deco


def _id(msg: str) -> str:
    assert msg.startswith("task "), msg
    return msg.split()[1]


def _task(tid: str) -> dict:
    return next(t for t in O._load() if t["id"] == tid)


def _turn(user_turn: bool):
    from tools import turn_context as T
    cm = T.turn_scope(user_turn=user_turn)
    turn = cm.__enter__()
    turn.update(close_gate=True, user_text="drop my day boundary to 3" if user_turn else "")
    return cm


def _h(schema: dict) -> str:
    return hashlib.sha256(json.dumps(schema, sort_keys=True, ensure_ascii=False).encode()) \
        .hexdigest()[:16]


# --- The day boundary --------------------------------------------------------------------------

@check("default boundary is midnight: the ledger day is the calendar date, exactly as before")
def _():
    _fresh("default")
    _at(2026, 10, 24, 1, 30)
    assert O._today() == date(2026, 10, 24)
    assert O._day_starts() == O.timedelta(0)


@check("day_starts is set only on task_id 'settings', 00:00–06:00, never from a scheduled turn")
def _():
    _fresh("set")
    assert O.update_task("ob_1", "day_starts", note="04:00").startswith("error:")
    assert O.update_task("settings", "day_starts", note="07:00").startswith("error:")
    assert O.update_task("settings", "day_starts", note="soon").startswith("error:")
    cm = _turn(user_turn=False)
    try:
        assert O.update_task("settings", "day_starts", note="03:00").startswith("error: not recorded")
    finally:
        cm.__exit__(None, None, None)
    cm = _turn(user_turn=True)
    try:
        assert "03:00" in O.update_task("settings", "day_starts", note="3:00")
    finally:
        cm.__exit__(None, None, None)
    assert O._day_starts() == O.timedelta(hours=3)


@check("at 01:30 with day_starts 04:00, 'today' is still yesterday for every date consumer")
def _():
    _fresh("boundary")
    _at(2026, 10, 23, 20, 0)
    O.update_task("settings", "day_starts", note="04:00")
    stretch = _id(O.open_task("Stretching", kind="habit", every="day"))
    bill = _id(O.open_task("Pay the gas bill", kind="deadline", due="2026-10-23"))
    _at(2026, 10, 24, 1, 30)
    assert O._today() == date(2026, 10, 23)
    # A habit done at 01:30 counts for the 23rd's occurrence.
    assert "@2026-10-23" in O.update_task(stretch, "done", evidence="just stretched")
    # A deadline due on the 23rd is due today, not overdue.
    v = O._view(_task(bill), O._today())
    assert v["state"] == "due_today", v
    # A close at 01:30 is recorded for the 23rd.
    O.update_task(bill, "done", evidence="paid it")
    rows = [r for r in O._history_rows() if r.get("task_id") == bill]
    assert rows and rows[-1]["closed_on"] == "2026-10-23", rows
    # The raise stamp written at 01:30 counts as raised "today" (the 23rd).
    O.note_raised("Did you do your stretching?")
    t = _task(stretch)
    occ = O._view(t, O._today())["occ"]
    if (t.get("raised") or {}).get(occ):
        assert O._raised_today(t, occ, O._today())
    # The Tasks block says where the day ends.
    block = O.context_block()
    assert "04:00" in block and "previous day" in block, block


@check("the 00:15 sweep with a 04:00 boundary leaves the day still in progress unrecorded")
def _():
    _fresh("sweep")
    _at(2026, 10, 22, 12, 0)
    O.update_task("settings", "day_starts", note="04:00")
    stretch = _id(O.open_task("Stretching", kind="habit", every="day"))
    _at(2026, 10, 24, 0, 15)    # ledger day = 23rd; the 22nd has ended, the 23rd has not
    O.sweep()
    keys = {r["key"] for r in O._history_rows() if r.get("task_id") == stretch}
    assert f"{stretch}@2026-10-22" in keys, keys
    assert f"{stretch}@2026-10-23" not in keys, keys


# --- The planner's fields -----------------------------------------------------------------------

@check("open_task takes goal_id, priority, stakes and zone, validated, with sources")
def _():
    _fresh("fields")
    tid = _id(O.open_task("Draft migration runbook", kind="deadline", due="2026-10-30",
                          goal_id="q1", priority="high", priority_source="stated",
                          stakes="vital", zone="gym"))
    t = _task(tid)
    assert t["goal_id"] == "q1" and t["goal_hash"] and t["priority"] == "high"
    assert t["priority_source"] == "stated" and t["stakes"] == "vital"
    assert t["stakes_source"] == "inferred" and t["zone"] == "gym"
    assert O.open_task("X", kind="deadline", goal_id="q9").startswith("error: no goal")
    assert O.open_task("Y", kind="habit", every="day", stakes="vital").startswith("error:")
    assert O.open_task("Z", kind="deadline", zone="moon").startswith("error: no zone")
    assert O.open_task("W", kind="deadline", priority="urgent").startswith("error:")


@check("update_task's planner actions: stated beats inferred; empty unlinks; one field only")
def _():
    _fresh("actions")
    tid = _id(O.open_task("Gym three times a week", kind="habit", every="week", times=3))
    assert "q2" in O.update_task(tid, "link_goal", goal_id="q2")
    assert _task(tid)["goal_hash"]
    assert "high" in O.update_task(tid, "set_priority", priority="high", priority_source="stated")
    msg = O.update_task(tid, "set_priority", priority="low", priority_source="inferred")
    assert "keeps the user's own" in msg and _task(tid)["priority"] == "high"
    assert O.update_task(tid, "set_stakes", stakes="vital").startswith("error:")  # a habit
    assert "gym" in O.update_task(tid, "set_zone", zone="Gym")
    assert "cleared" in O.update_task(tid, "link_goal", goal_id="")
    t = _task(tid)
    assert "goal_id" not in t and "goal_hash" not in t and t["zone"] == "gym"
    assert O.update_task(tid, "set_priority").startswith("error:")


@check("is_essential: medication, high priority, essential goal, unknown-stakes deadline")
def _():
    _fresh("essential")
    goals = {"q1": {"essential": True}, "q2": {"essential": False}}
    assert O.is_essential({"kind": "habit", "what": "Take blood pressure pills"}, goals)
    assert O.is_essential({"kind": "habit", "what": "Stretch", "note": "after the inhaler"}, goals)
    assert O.is_essential({"kind": "habit", "what": "Stretch", "priority": "high"}, goals)
    assert O.is_essential({"kind": "habit", "what": "Run", "goal_id": "q1"}, goals)
    assert not O.is_essential({"kind": "habit", "what": "Guitar", "goal_id": "q2"}, goals)
    assert O.is_essential({"kind": "deadline", "what": "File the tax return"}, goals)
    assert not O.is_essential({"kind": "deadline", "what": "Buy a card", "stakes": "missable"},
                              goals)
    assert not O.is_essential({"kind": "habit", "what": "Stretching"}, goals)
    assert not O.is_essential({"kind": "waiting", "what": "Reply from Bupa"}, goals)


# --- The unconfirmed rule (F10) ---------------------------------------------------------------

@check("unconfirmed rule OFF: an unconfirmed habit day is recorded missed, exactly as before")
def _():
    _fresh("rule_off")
    _at(2026, 10, 22, 9, 0)
    stretch = _id(O.open_task("Stretching", kind="habit", every="day"))
    _at(2026, 10, 24, 0, 30)
    O.sweep()
    states = {r["key"]: r["state"] for r in O._history_rows() if r.get("task_id") == stretch}
    assert states.get(f"{stretch}@2026-10-23") == "missed", states


@check("unconfirmed rule ON: non-essential → unconfirmed; essential and medication → missed")
def _():
    _fresh("rule_on")
    _flags(unconfirmed_rule=True)
    _at(2026, 10, 22, 9, 0)
    stretch = _id(O.open_task("Stretching", kind="habit", every="day"))
    run = _id(O.open_task("Morning run", kind="habit", every="day", goal_id="q1"))
    meds = _id(O.open_task("Take the morning tablets", kind="habit", every="day"))
    _at(2026, 10, 24, 0, 30)
    O.sweep()
    st = {r["task_id"]: r["state"] for r in O._history_rows()
          if r.get("key", "").endswith("@2026-10-23")}
    assert st[stretch] == "unconfirmed", st
    assert st[run] == "missed", st
    assert st[meds] == "missed", st
    a = {s["task_id"]: s for s in O.adherence(days=5)}
    assert a[stretch]["unconfirmed"] >= 1 and a[stretch]["missed"] == 0
    assert a[stretch]["rate"] == 0.0     # the rate does not improve by not asking
    counts = O.daily_task_counts("2026-10-23")
    assert counts["tasks_unconfirmed"] >= 1 and counts["tasks_missed"] >= 2, counts


@check("unconfirmed rule ON: a missable deadline past its date is lapsed, never overdue")
def _():
    _fresh("lapsed")
    _flags(unconfirmed_rule=True)
    _at(2026, 10, 20, 9, 0)
    card = _id(O.open_task("Buy a birthday card", kind="deadline", due="2026-10-21",
                           stakes="missable"))
    tax = _id(O.open_task("File the tax return", kind="deadline", due="2026-10-21"))
    _at(2026, 10, 24, 9, 0)
    assert O._view(_task(card), O._today())["state"] == "lapsed"
    assert not O._view(_task(card), O._today())["actionable"]
    assert O._view(_task(tax), O._today())["state"] == "overdue"
    block = O.context_block()
    assert "past their date, unconfirmed" in block and "Buy a birthday card" not in block, block
    assert _task(card)["status"] == "open"     # stays open; only not raised
    C._OVERRIDE = _SHIPPED
    assert O._view(_task(card), O._today())["state"] == "overdue"   # flag off: as before


@check("unconfirmed rule ON: a non-essential quota gets no make-up or at-risk nudge")
def _():
    _fresh("makeup")
    _flags(unconfirmed_rule=True)
    _at(2026, 10, 19, 9, 0)    # Monday
    gym = _id(O.open_task("Gym", kind="habit", every="week", times=3,
                          on_days=["mon", "wed", "fri"]))
    _at(2026, 10, 23, 9, 0)    # Friday: Mon and Wed missed
    v = O._view(_task(gym), O._today())
    assert "made up" not in v["text"] and "stay on target" not in v["text"], v
    assert v["actionable"]     # Friday is still a planned day
    C._OVERRIDE = _SHIPPED
    v = O._view(_task(gym), O._today())
    assert "made up" in v["text"] or "stay on target" in v["text"], v


# --- What models see (review R1-1) ------------------------------------------------------------

@check("flag OFF: the schemas models see are byte-identical to the shipped constants")
def _():
    _fresh("schemas_off")
    C._OVERRIDE = _SHIPPED
    o, u, l = O.task_schemas()
    assert (_h(o), _h(u), _h(l)) == ("0a096897e6448300", "426bcfc2d90b424d",
                                     "fc306ac3d96fa5e1"), (_h(o), _h(u), _h(l))
    r, g = G.goal_schemas()
    assert (_h(r), _h(g)) == ("dd71c3276d1e4b23", "385d3750301ff22e"), (_h(r), _h(g))


@check("flag ON: the planner's actions and fields appear; the constants are not mutated")
def _():
    _fresh("schemas_on")
    _flags(ledger_fields=True)
    o, u, _l = O.task_schemas()
    assert {"goal_id", "priority", "stakes", "zone"} <= set(o["input_schema"]["properties"])
    acts = u["input_schema"]["properties"]["action"]["enum"]
    assert {"link_goal", "set_priority", "set_stakes", "set_zone", "day_starts"} <= set(acts)
    assert "day_starts" not in O.UPDATE_TASK_SCHEMA["input_schema"]["properties"]["action"]["enum"]
    _r, g = G.goal_schemas()
    assert "essential" in g["input_schema"]["properties"]
    assert "essential" not in G.UPDATE_GOAL_SCHEMA["input_schema"]["properties"]


@check("flag OFF: the hidden actions are refused and unnamed, and guessed fields write nothing (S-8)")
def _():
    _fresh("hidden_off")
    C._OVERRIDE = _SHIPPED
    msg = O.update_task("settings", "day_starts", note="03:00")
    allowed = msg.split(", not ")[0]
    assert msg.startswith("error: `action`") and "day_starts" not in allowed \
        and "set_priority" not in allowed, msg
    tid = _id(O.open_task("Pay the gas bill", kind="deadline", priority="high", stakes="missable",
                          goal_id="q1", zone="gym"))
    t = _task(tid)
    assert not any(k in t for k in ("priority", "stakes", "goal_id", "zone")), t
    assert O.update_task(tid, "set_priority", priority="high").startswith("error: `action`")


@check("update_goal sets essential as a real bool")
def _():
    d = _fresh("goal_essential")
    assert "essential" in G.update_goal("update", goal_id="q2", essential="true")
    import yaml
    doc = yaml.safe_load((d / "goals.yaml").read_text())
    assert doc["quarterly"][1]["essential"] is True
    assert G.update_goal("update", goal_id="q2", essential="maybe").startswith("Error")


def main() -> int:
    passed = sum(1 for _, ok, _ in _results if ok)
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if detail else ""))
    print(f"\n{passed} passed, {len(_results) - passed} failed, {len(_results)} total")
    return 0 if passed == len(_results) else 1


if __name__ == "__main__":
    sys.exit(main())
