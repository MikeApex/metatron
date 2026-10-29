"""
tests/test_task_defer.py — update_task(action="defer"): "don't show me this until Monday"
(Mike, 2026-10-24; ruled 2026-10-29 — a separate action, not a change to reschedule, because
hiding a task and moving its date are different requests).

A deferred task is `dormant` until its day in every surface that lists outstanding work — the
Synthesizer's Tasks block, the Today panel, the day plan's candidates, list_tasks(horizon=
"today"), and the ledger notes on copies in threads and day logs — and comes back on the day.
Refused where hiding would hide a miss. Synthetic data in a temp directory; EVERY LIVE METER IS
STUBBED (CalDAV reads and writes). Run it, do not read it:

    python3 tests/test_task_defer.py
"""
from __future__ import annotations

import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.caldav as CAL  # noqa: E402
import tools.day_plan as D  # noqa: E402
import tools.day_plan_config as C  # noqa: E402
import tools.day_shape as DS  # noqa: E402
import tools.goals as G  # noqa: E402
import tools.location as L  # noqa: E402
import tools.obligations as O  # noqa: E402

_results: list[tuple[str, bool, str]] = []
_TMP = Path(tempfile.mkdtemp(prefix="task_defer_"))
_CLOCK = {"now": datetime(2026, 10, 29, 9, 0, 0)}         # Thursday; Monday is 11-02
O._now = lambda: _CLOCK["now"]

# No calendar, read or write: open_task's exact-title link, a done's ✓, a reschedule's move.
CAL._query_events = lambda *a, **k: {"events": [], "discovery": "ok"}
O._link_calendar_if_exact = lambda task_id: None
O._mark_calendar_done = lambda task: None
O._move_calendar = lambda task, new_due: None
L.load_zones = lambda persona=None: []
L.current_zone = lambda persona=None: {}

_SHAPE = 'day: [{days: all, wake: "07:00", bed: "23:00"}]\n'
_ON = {"flags": {"build": True, "show_in_app": True, "ledger_fields": True}}


def _fresh(name: str) -> Path:
    d = _TMP / name
    (d / "config").mkdir(parents=True, exist_ok=True)
    for mod in (O, D, DS, L):
        mod.persona_data_dir = lambda persona=None, _d=d: _d
    DS.persona_config_dir = lambda persona=None, _d=d: _d / "config"
    (d / "config" / "goals.yaml").write_text("quarterly: []\n")
    G._goals_path = lambda _d=d: _d / "config" / "goals.yaml"
    (d / "day_shape.yaml").write_text(_SHAPE)
    C._OVERRIDE = _ON
    _at(2026, 10, 29)
    return d


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
            C._OVERRIDE = _ON
        return fn
    return deco


def _id(msg: str) -> str:
    assert msg.startswith("task "), msg
    return msg.split()[1]


def _task(tid: str) -> dict:
    return next(t for t in O._load() if t["id"] == tid)


def _now_section() -> str:
    block = O.context_block()
    return block.split("**Now**")[1].split("**")[0] if "**Now**" in block else ""


def _surfaces(tid: str) -> dict:
    """Is the task outstanding on each surface that lists outstanding work, today?"""
    return {"tasks_block": tid in _now_section(),
            "today_panel": any(i["task_id"] == tid for i in O.today_items()),
            "day_plan": any(c["task_id"] == tid for c in D._candidates(O._today(), None)),
            "list_today": tid in O.list_tasks(horizon="today")}


@check("defer hides a task from every outstanding surface until its day, and it comes back then")
def _():
    _fresh("hides")
    # Due Saturday: inside the two-day lead today, so the Tasks block raises it; deferred to its
    # own date (allowed — the day it is due is the day it comes back).
    tid = _id(O.open_task("Return the library books", kind="deadline", due="2026-10-31"))
    _at(2026, 10, 31)
    assert all(_surfaces(tid).values()), _surfaces(tid)
    _at(2026, 10, 29)
    assert _surfaces(tid)["tasks_block"], O.context_block()
    out = O.update_task(tid, "defer", new_due="2026-10-31",
                        evidence="don't show me the books until Saturday")
    assert "deferred until 2026-10-31" in out, out
    for day in (29, 30):
        _at(2026, 10, day)
        assert not any(_surfaces(tid).values()), (day, _surfaces(tid))
        assert "1 not yet eligible" in O.context_block(), O.context_block()
    _at(2026, 10, 31)
    assert all(_surfaces(tid).values()), _surfaces(tid)
    assert "due today" in _now_section(), _now_section()
    t = _task(tid)
    assert t["due"] == "2026-10-31", "defer must not move the date"


@check("an undated task deferred to Monday: out of the Tasks block until Monday, back on it")
def _():
    _fresh("undated")
    tid = _id(O.open_task("Sort the garage shelves", kind="deadline"))
    assert tid in _now_section()
    O.update_task(tid, "defer", new_due="2026-11-02", evidence="leave that until Monday")
    _at(2026, 11, 1)
    assert tid not in _now_section(), O.context_block()
    _at(2026, 11, 2)
    assert tid in _now_section(), O.context_block()


@check("a waiting item past its check-back is held until the deferral day")
def _():
    _fresh("waiting")
    _at(2026, 10, 20)
    tid = _id(O.open_task("Hear back from the builder", kind="waiting", waiting_on="the builder",
                          check_back="2026-10-27"))
    _at(2026, 10, 29)
    assert tid in _now_section()
    assert O.update_task(tid, "defer", new_due="2026-11-02",
                         evidence="chase the builder next week").startswith(tid)
    assert tid not in _now_section() and not any(i["task_id"] == tid for i in O.today_items())
    _at(2026, 11, 2)
    assert tid in _now_section() and any(i["task_id"] == tid for i in O.today_items())


@check("the deferral is recorded in history with the user's words; the listing says so")
def _():
    _fresh("history")
    tid = _id(O.open_task("Book the boiler service", kind="deadline", due="2026-11-10"))
    O.update_task(tid, "defer", new_due="2026-11-02", evidence="not until Monday please")
    t = _task(tid)
    h = t["history"][-1]
    assert h["event"] == "deferred" and h["until"] == "2026-11-02", h
    assert h["reason"] == "not until Monday please" and h["from"] is None, h
    assert t["eligible_from"] == "2026-11-02"
    listing = O.list_tasks()
    assert "deferred until 2026-11-02" in listing, listing
    # Deferred again: the earlier day is kept in the record.
    O.update_task(tid, "defer", new_due="2026-11-04", evidence="make that Wednesday")
    h = _task(tid)["history"][-1]
    assert h["from"] == "2026-11-02" and h["until"] == "2026-11-04", h


@check("a copy of a deferred task in a thread or day log is annotated not outstanding")
def _():
    _fresh("consult")
    tid = _id(O.open_task("Renew the parking permit", kind="deadline", due="2026-11-06"))
    idx = O.consult_index()
    assert O.annotate("renew parking permit", idx).endswith(f"[tracked as task {tid}]")
    O.update_task(tid, "defer", new_due="2026-11-02", evidence="Monday")
    out = O.annotate("renew parking permit", O.consult_index())
    assert "deferred until 2026-11-02 — not outstanding before then" in out, out
    _at(2026, 11, 2)
    assert O.annotate("renew parking permit", O.consult_index()).endswith(
        f"[tracked as task {tid}]")


@check("refused: today, a past day, no date, no evidence — nothing written")
def _():
    _fresh("refused")
    tid = _id(O.open_task("Clean the gutters", kind="deadline"))
    for when in ("2026-10-29", "2026-10-20"):
        out = O.update_task(tid, "defer", new_due=when, evidence="later")
        assert out.startswith("error") and "after today" in out, out
    assert O.update_task(tid, "defer", evidence="later").startswith("error")
    assert O.update_task(tid, "defer", new_due="Monday", evidence="later").startswith("error")
    assert O.update_task(tid, "defer", new_due="2026-11-02").startswith("error")
    t = _task(tid)
    assert "eligible_from" not in t and not t.get("history"), t


@check("refused: past a deadline's own date, past an interval's next due, a habit, a closed task")
def _():
    _fresh("unsafe")
    dl = _id(O.open_task("Submit the expense claim", kind="deadline", due="2026-10-31"))
    out = O.update_task(dl, "defer", new_due="2026-11-02", evidence="Monday")
    assert out.startswith("error") and "2026-10-31" in out and "reschedule" in out, out
    over = _id(O.open_task("Pay the parking fine", kind="deadline", due="2026-10-27"))
    assert O.update_task(over, "defer", new_due="2026-11-02", evidence="x").startswith("error")
    iv = _id(O.open_task("Change the water filter", kind="interval", interval_days=30,
                         last_done="2026-10-01"))
    out = O.update_task(iv, "defer", new_due="2026-11-02", evidence="x")
    assert out.startswith("error") and "2026-10-31" in out, out
    hb = _id(O.open_task("Morning stretch", kind="habit", every="day"))
    out = O.update_task(hb, "defer", new_due="2026-11-02", evidence="x")
    assert out.startswith("error") and "habit" in out, out
    done = _id(O.open_task("Post the parcel", kind="deadline"))
    O.update_task(done, "done", evidence="posted it")
    assert O.update_task(done, "defer", new_due="2026-11-02", evidence="x").startswith("error")
    for t in (dl, over, iv, hb, done):
        assert "eligible_from" not in _task(t), t


@check("reschedule is unchanged: it moves the date, records it, and hides nothing")
def _():
    _fresh("resched")
    tid = _id(O.open_task("Send the insurance form", kind="deadline", due="2026-10-30"))
    out = O.update_task(tid, "reschedule", new_due="2026-10-31", evidence="due Saturday now")
    assert out.startswith(f"{tid} rescheduled to 2026-10-31"), out
    t = _task(tid)
    assert t["due"] == "2026-10-31" and "eligible_from" not in t, t
    assert t["history"][-1]["event"] == "rescheduled", t["history"]
    assert tid in _now_section(), "a rescheduled deadline keeps its lead-time warning"


@check("schema: defer offered with the planner's fields on, with when-to-use text; not offered "
       "or accepted with them off")
def _():
    _fresh("schema")
    _o, u, _l = O.task_schemas()
    assert "defer" in u["input_schema"]["properties"]["action"]["enum"]
    assert "don't show me this until Monday" in u["description"], u["description"]
    assert "defer" in u["input_schema"]["properties"]["new_due"]["description"]
    assert "defer" not in O.UPDATE_TASK_SCHEMA["input_schema"]["properties"]["action"]["enum"]
    C._OVERRIDE = {"flags": {}}
    _o, u, _l = O.task_schemas()
    assert "defer" not in u["input_schema"]["properties"]["action"]["enum"]
    tid = _id(O.open_task("Wash the car", kind="deadline"))
    out = O.update_task(tid, "defer", new_due="2026-11-02", evidence="x")
    assert out.startswith("error") and "defer" not in out.split(", not ")[0], out


def main() -> int:
    passed = sum(1 for _, ok, _ in _results if ok)
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if detail else ""))
    print(f"\n{passed} passed, {len(_results) - passed} failed, {len(_results)} total")
    return 0 if passed == len(_results) else 1


if __name__ == "__main__":
    sys.exit(main())
