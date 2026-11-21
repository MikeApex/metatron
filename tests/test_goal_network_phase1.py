"""
tests/test_goal_network_phase1.py — the goal–task network, phase 1: steps that wait on other steps,
the Red Book scheduled, review finding #5, and stage 1's misses M2/M3.

Plan: archive/plans/goal_task_network_plan_2026-11-18.md — § 10 governs (R1, R2, R5, R7, R9,
R10), § 4.7 answers Fable's A1–A9 from synth_now_next_plan_2026-10-30.md § 10, § 12 M2/M3 as
Mike ruled on 2026-11-18.

EVERY LIVE METER IS STUBBED (the standing rule): CalDAV (`_query_events`, `_get_event_by_uid`),
Google Routes (`get_travel_time`), the day_planner model (`reshuffle_model` off and `_call_model`
refusing), push (`send_one`). No persona data — a temp directory per check. Run it:

    python3 tests/test_goal_network_phase1.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import threading
from datetime import date, datetime, time, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import core.interview as INTV  # noqa: E402
import core.persona as P  # noqa: E402
import core.scheduler as S  # noqa: E402
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

_results: list[tuple[str, bool, str]] = []
_TMP = Path(tempfile.mkdtemp(prefix="goal_network_p1_"))
# The horizon ledger dates by date.today(), so the clock runs on the real date.
TODAY = date.today()
_CLOCK = {"now": datetime.combine(TODAY, time(7, 0))}
O._now = lambda: _CLOCK["now"]
A._get_timezone = lambda: "Europe/London"
_PERSONA = "gn_phase1"
_D3 = (TODAY + timedelta(days=3)).isoformat()

_SHAPE = """\
day: [{days: all, wake: "07:00", bed: "23:00"}]
windows:
  - {activity: family, days: all, from: "17:30", to: "20:30", strength: protected}
travel_mode: transit
"""

_EVENTS: dict = {"v": []}
_UID_LOOKUP: dict = {"v": {"error": "Failed to fetch event: offline"}}
_CALLS = {"routes": 0, "model": 0, "open_plan": 0, "send": 0}


def _query_events(start, end, persona=None, calendars="own"):
    if _EVENTS.get("error"):
        return {"error": _EVENTS["error"]}
    return {"events": json.loads(json.dumps(_EVENTS["v"])), "discovery": "ok"}


CAL._query_events = _query_events
CAL._get_event_by_uid = lambda uid, persona=None: dict(_UID_LOOKUP["v"])


def _route(origin, destination, mode="transit", arrive_by=""):
    _CALLS["routes"] += 1
    return {"journeys": [{"duration_minutes": 20}]}


R.get_travel_time = _route
L.load_zones = lambda persona=None: []
L.current_zone = lambda persona=None: {}


def _no_model(*a, **k):
    _CALLS["model"] += 1
    raise AssertionError("a model call was made")


D._call_model = _no_model
D._quiet_now = lambda persona: False
D._idle_minutes = lambda persona: None
INTV.holds_proactive = lambda persona: False
import core.remote_client as RC  # noqa: E402
_SENT: list = []


def _send_one(persona, text, nudge=False, **k):
    """Push/wake stub — a real call would reach the running server (found the hard way)."""
    _SENT.append(text)
    _CALLS["send"] += 1
    return "ok"


RC.send_one = _send_one
_real_open_plan = O.open_plan


def _counting_open_plan(*a, **k):
    _CALLS["open_plan"] += 1
    return _real_open_plan(*a, **k)


O.open_plan = _counting_open_plan

_FLAGS = {"build": True, "show_in_app": True, "ledger_fields": True, "synth_reads_plan": True,
          "unconfirmed_rule": True, "reshuffle_model": False, "nudges": True,
          "owns_checkins": False, "prep_tasks": True, "horizon_cap": True}


def _ev(uid, title, start, end, location=""):
    return {"uid": uid, "title": title, "start": start, "end": end, "location": location,
            "status": "", "calendars": ["Main"], "calendar_ids": ["/cal/main"], "read_only": False}


def _at(d: date, hm: str) -> str:
    return f"{d.isoformat()}T{hm}:00"


def _fresh(name: str, flags: dict | None = None, extra: dict | None = None) -> Path:
    for th in threading.enumerate():
        if th.name.startswith("day_plan_"):
            th.join(5)
    d = _TMP / name
    (d / "config").mkdir(parents=True, exist_ok=True)
    for mod in (O, D, DS, L, H):
        mod.persona_data_dir = lambda persona=None, _d=d: _d
    DS.persona_config_dir = lambda persona=None, _d=d: _d / "config"
    (d / "config" / "goals.yaml").write_text("quarterly: []\n")
    G._goals_path = lambda _d=d: _d / "config" / "goals.yaml"
    (d / "day_shape.yaml").write_text(_SHAPE)
    C._OVERRIDE = {"flags": {**_FLAGS, **(flags or {})}, **(extra or {})}
    _EVENTS["v"] = []
    _EVENTS.pop("error", None)
    _SENT.clear()
    _UID_LOOKUP["v"] = {"error": "Failed to fetch event: offline"}
    for k in _CALLS:
        _CALLS[k] = 0
    _CLOCK["now"] = datetime.combine(TODAY, time(7, 0))
    O._DAY_STARTS_CACHE.update(key=None)
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
            C._OVERRIDE = None
        return fn
    return deco


def _task(tid: str) -> dict:
    return next(O._norm(t) for t in O._load() if t["id"] == tid)


def _two_step() -> dict:
    """The live check's test project: step 2 needs step 1, both part of step 2's end state."""
    res = O.open_plan([
        {"key": "a", "what": "Find the old passport", "minutes": 15, "part_of": "b",
         "due": TODAY.isoformat()},
        {"key": "b", "what": "Post the renewal form", "needs": ["a"], "minutes": 20,
         "due": (TODAY + timedelta(days=1)).isoformat()},
    ])
    assert res["ok"], res
    return res["ids"]


def _finding(title, day: date, venue="", precursor="", by="", kind="appointment"):
    return {"title": title, "date": day.isoformat(), "venue": venue, "kind": kind,
            "detail": "", "precursor": precursor, "precursor_by": by}


def _tick() -> str:
    D.refresh_snapshot(_PERSONA)
    st = D._load_state(_PERSONA)
    return D._prep_sweep(_PERSONA, st)


# =============================================================================================
# R1 — file locks: two processes, one close each, both kept
# =============================================================================================

_CHILD = textwrap.dedent("""
    import sys
    from datetime import datetime
    from pathlib import Path
    sys.path.insert(0, {root!r})
    import tools.obligations as O
    import tools.horizon as H
    d = Path({d!r})
    O.persona_data_dir = lambda persona=None: d
    H.persona_data_dir = lambda persona=None: d
    H.resolve_persona = lambda persona=None: "race"
    O._now = lambda: datetime(2026, 11, 18, 9, 0)
    O._link_calendar_if_exact = lambda tid: None
    which, n = {which!r}, {n}
    ids = [l.strip() for l in (d / f"ids_{{which}}.txt").read_text().splitlines() if l.strip()]
    for i, tid in enumerate(ids):
        r = O.update_task(tid, "done", evidence=f"{{which}} closes {{i}}")
        assert "done" in r, r
        H.record([{{"title": f"{{which}} finding {{i}}", "date": "", "venue": f"{{which}}-v{{i}}"}}])
""")


@check("R1: two processes closing tasks and filing findings at once — every close and every "
       "finding is kept")
def _():
    d = _fresh("race")
    n = 30
    ids = {"alpha": [], "beta": []}
    for which in ids:
        for i in range(n):
            r = O.open_task(f"{which} unique errand number {i} zq{i}{which}", new_instance=True)
            assert r.startswith("task "), r
            ids[which].append(r.split()[1])
        (d / f"ids_{which}.txt").write_text("\n".join(ids[which]))
    procs = [subprocess.Popen([sys.executable, "-c", _CHILD.format(root=str(ROOT), d=str(d),
                                                                   which=w, n=n)],
                              stderr=subprocess.PIPE) for w in ids]
    for p in procs:
        _out, err = p.communicate(timeout=180)
        assert p.returncode == 0, err.decode()[-800:]
    tasks = {t["id"]: t for t in O._load()}
    done = sum(1 for w in ids for tid in ids[w] if tasks[tid]["status"] == "done")
    assert done == 2 * n, f"{done} of {2 * n} closes kept"
    data = json.loads((d / "horizon" / "ledger.json").read_text())
    assert len(data) == 2 * n, f"{len(data)} of {2 * n} findings kept"


# =============================================================================================
# The network: needs, part_of, blocked (§ 4.1, R7)
# =============================================================================================

@check("R7a: a blocked step is hidden from Today, the planner, the Tasks block, list_tasks, "
       "Accountability and the consult index — and appears once step 1 is done")
def _():
    _fresh("blocked")
    ids = _two_step()
    a, b = ids["a"], ids["b"]
    assert _task(b)["_blocked"] and not _task(a).get("_blocked")
    assert O._view(_task(b), TODAY)["state"] == "blocked"
    today = {i["task_id"] for i in O.today_items()}
    assert a in today and b not in today, today
    cands = {c["task_id"] for c in D._candidates(TODAY, _PERSONA)}
    assert a in cands and b not in cands, cands
    block = O.context_block()
    assert "Find the old passport" in block and "Post the renewal form" not in block, block
    assert "1 later step waiting on an earlier one" in block, block
    listed = O.list_tasks()
    assert "Post the renewal form" not in listed and "1 later step" in listed, listed
    assert all(x["what"] != "Post the renewal form" for x in O.accountability_items())
    assert b not in {x["id"] for x in O.consult_index()}
    plan = D.current(_PERSONA)
    assert b not in {x.get("task_id") for x in plan["blocks"]}, "a blocked step was placed"
    O.update_task(a, "done", evidence="found it in the drawer")
    assert not _task(b).get("_blocked")
    assert b in {i["task_id"] for i in O.today_items(as_of=TODAY + timedelta(days=1))}
    assert "Post the renewal form" in O.list_tasks()


@check("R7a: closing step 1 unblocks step 2 in the same tick — the next plan build places it")
def _():
    _fresh("same_tick")
    ids = _two_step()
    # Step 2 due today too, so the planner would place it the moment it is free.
    O._with_store(None, lambda doc: [t.update(due=TODAY.isoformat()) for t in doc["tasks"]
                                     if t["id"] == ids["b"]])
    D.current(_PERSONA)
    O.update_task(ids["a"], "done", evidence="done")
    plan = D.current(_PERSONA)
    assert ids["b"] in {x.get("task_id") for x in plan["blocks"]}, plan["blocks"]


@check("R7b: the user's own new task is not refused as 'already open' as a hidden step, and "
       "hidden steps do not count toward the soft cap")
def _():
    _fresh("dedupe")
    _two_step()
    r = O.open_task("Post the renewal form")
    assert r.startswith("task "), r
    O._with_store(None, lambda doc: [t.__setitem__("part_of", "goal-x") for t in doc["tasks"]])
    for i in range(O._SOFT_CAP):
        O.open_plan([{"what": f"plan step {i} zz{i}", "part_of": "goal-x", "due": _D3}])
    r = O.open_task("Water the fern by the window")
    assert "NOTE:" not in r, r


@check("R7c: open_plan is all-or-nothing — a cycle, a dangling need or a twin step writes "
       "nothing; a good plan writes every step in one go")
def _():
    _fresh("open_plan")
    before = len(O._load())
    for bad in (
        [{"key": "a", "what": "Step A", "needs": ["b"], "due": _D3},
         {"key": "b", "what": "Step B", "needs": ["a"], "due": _D3}],
        [{"key": "a", "what": "Step A", "due": _D3}, {"key": "b", "what": "Step B", "needs": ["nope"], "due": _D3}],
        [{"key": "a", "what": "Gather the P60", "due": _D3}, {"key": "b", "what": "gather the p60", "due": _D3}],
        [{"key": "a", "what": "Step A", "kind": "habit", "due": _D3}],
        [{"key": "a", "what": "Step A"}],                     # undated (Fable #9)
    ):
        res = O.open_plan(bad)
        assert not res["ok"], (bad, res)
        assert len(O._load()) == before, "a refused plan wrote something"
    res = O.open_plan([{"key": "a", "what": "Gather the P60", "due": _D3},
                       {"key": "b", "what": "Book the accountant", "needs": ["a"], "due": _D3},
                       {"key": "c", "what": "File the return", "needs": ["b"],
                        "due": (TODAY + timedelta(days=30)).isoformat()}])
    assert res["ok"] and len(O._load()) == before + 3, res
    c = _task(res["ids"]["c"])
    assert c["needs"] == [res["ids"]["b"]]


@check("R5: plan steps are missable unless near their end state's deadline; the end state is "
       "vital; a prep is left essential (unset stakes on a deadline)")
def _():
    _fresh("stakes")
    end = (TODAY + timedelta(days=30))
    res = O.open_plan([
        {"key": "far", "what": "Gather documents", "part_of": "end", "due": (end - timedelta(days=20)).isoformat()},
        {"key": "near", "what": "Check the figures", "part_of": "end", "needs": ["far"],
         "due": (end - timedelta(days=1)).isoformat()},
        {"key": "end", "what": "Submit the return", "needs": ["near"], "due": end.isoformat()},
        {"key": "prep", "what": "Pack the bag", "prep_for": {"finding": "x"},
         "due": TODAY.isoformat()},
    ])
    ids = res["ids"]
    assert _task(ids["far"])["stakes"] == "missable"
    assert _task(ids["near"])["stakes"] == "vital"
    assert _task(ids["end"])["stakes"] == "vital"
    assert "stakes" not in _task(ids["prep"]) and O.is_essential(_task(ids["prep"]))


@check("R5: a new step or prep reaching the day is placed by code in a repair — no reshuffle, so "
       "no day_planner call")
def _():
    _fresh("no_reshuffle")
    D.current(_PERSONA)                                    # the first build of the day
    _CLOCK["now"] += timedelta(minutes=5)
    O.open_plan([{"what": "Pack the swim bag", "prep_for": {"finding": "k"},
                  "due": TODAY.isoformat(), "minutes": 15}])
    plan = D.current(_PERSONA)
    assert plan["trigger"] == "repair", (plan["trigger"], plan["reasons"])
    assert "step(s) placed" in plan["reasons"][0], plan["reasons"]
    assert any(x.get("title") == "Pack the swim bag" for x in plan["blocks"])
    O.open_task("Ring the plumber about the leak", due=TODAY.isoformat())
    plan = D.current(_PERSONA)
    assert plan["trigger"] == "reshuffle", "an ordinary task must still reshuffle"
    assert _CALLS["model"] == 0


# =============================================================================================
# R9 — the phase 1 dismissal rule
# =============================================================================================

@check("R9: skipping a required step 1 closes step 2 moot and raises the end state once; "
       "redoing step 1 brings step 2 back, waiting on it")
def _():
    _fresh("r9")
    ids = _two_step()
    r = O.update_task(ids["a"], "skipped", evidence="not bothering with that")
    assert "later step" in r, r
    b = _task(ids["b"])
    assert b["status"] == "moot" and b["evidence"] == O._PREREQ_DISMISSED
    raise_ = O.cascades_to_raise()
    assert len(raise_) == 1 and raise_[0]["end"] == "Post the renewal form", raise_
    plan = D.current(_PERSONA)
    shown: dict = {}
    text = D.render_block(plan, kind="morning_brief", cascades=raise_, shown=shown)
    assert "can't go ahead without" in text and ids["a"] in text, text
    D.after_render(_PERSONA, shown)
    D.note_said("Morning. Your lunch is at one.")
    D.note_said("The renewal form is on your list for tomorrow.")   # named, not asked
    assert O.cascades_to_raise(), "stamped by a reply that never asked it"
    D.after_render(_PERSONA, shown)
    D.note_said("The renewal form can't go out without the old passport — want to redo that step?")
    assert O.cascades_to_raise() == [], "raised twice"
    r = O.update_task(ids["a"], "reopen", evidence="actually, yes, redo it")
    assert "are back" in r, r
    assert _task(ids["b"])["status"] == "open" and _task(ids["b"])["_blocked"]


@check("R9: dismissing an OPTIONAL step unblocks what needs it")
def _():
    _fresh("r9_optional")
    res = O.open_plan([{"key": "a", "what": "Ask a friend for a recommendation", "required": False,
                        "due": _D3},
                       {"key": "b", "what": "Choose an accountant", "needs": ["a"], "due": _D3}])
    O.update_task(res["ids"]["a"], "dismissed", evidence="no need")
    b = _task(res["ids"]["b"])
    assert b["status"] == "open" and not b.get("_blocked")
    assert O.cascades_to_raise() == []


@check("R9: a required prerequisite that goes moot on its own date closes what needs it at the sweep")
def _():
    _fresh("r9_sweep")
    res = O.open_plan([{"key": "a", "what": "Collect the tickets", "due": _D3,
                        "moot_after": (TODAY - timedelta(days=1)).isoformat()},
                       {"key": "b", "what": "Hand the tickets over", "needs": ["a"], "due": _D3}])
    O.sweep()
    assert _task(res["ids"]["a"])["status"] == "moot"
    assert _task(res["ids"]["b"])["status"] == "moot"


# =============================================================================================
# R2 — the Red Book, and Fable's A1–A9
# =============================================================================================

def _redbook(day: date, hm="09:30", venue="Little Acorns Nursery"):
    _EVENTS["v"] = [_ev("u-nursery", "Benny settling-in — Little Acorns", _at(day, hm),
                        _at(day, "10:30"), venue)]
    H.record([_finding("Benny's settling-in session", day, venue,
                       "gather the Red Book and paperwork")])


def _preps() -> list[dict]:
    return [O._norm(t) for t in O._load()
            if str(t.get("source_id") or "").startswith(D._PREP_SOURCE)]


@check("A1: a finding filed the morning of a 09:30 event gives a prep due TODAY, placed BEFORE "
       "the event — not tonight, after it")
def _():
    _fresh("a1")
    _redbook(TODAY)
    _tick()
    [p] = _preps()
    assert p["due"] == TODAY.isoformat() and p["before"] == "09:30", p
    assert p["prep_for"]["uid"] == "u-nursery"
    plan = D.current(_PERSONA)
    blk = next(x for x in plan["blocks"] if x.get("task_id") == p["id"])
    assert blk["end"] <= _at(TODAY, "09:30")[:16], blk


@check("A2/R1: the conversion runs in the scheduler's tick and writes both ledgers under their "
       "file locks — refresh_tick opens the prep and places it in the same tick")
def _():
    _fresh("a2")
    _redbook(TODAY + timedelta(days=1))
    out = D.refresh_tick()
    assert "prep: 1 opened" in out, out
    [p] = _preps()
    row = next(iter(H.rows().values()))
    assert row["prep_task_id"] == p["id"]
    plan = json.loads(D._plan_path(TODAY).read_text())
    assert any(x.get("task_id") == p["id"] for x in plan["blocks"]), "not placed this tick"


@check("A3: flag off closes open preps with a reason and the precursor is said again under "
       "Important; while on, a converted finding is not repeated there")
def _():
    _fresh("a3")
    tomorrow = TODAY + timedelta(days=1)
    _redbook(tomorrow)
    _tick()
    assert H.prep_items(day=tomorrow) == [], "Important repeats a prep the plan carries"
    C._OVERRIDE["flags"]["prep_tasks"] = False
    _tick()
    [p] = _preps()
    assert p["status"] == "moot" and p["evidence"] == D._PREP_OFF, p
    items = H.prep_items(day=tomorrow)
    assert items and "Red Book" in items[0], items


@check("A4/A7: three near-duplicate nursery findings open ONE prep, and every sibling is stamped")
def _():
    _fresh("a4")
    d = TODAY + timedelta(days=1)
    _EVENTS["v"] = [_ev("u-n", "Benny nursery settling-in", _at(d, "09:30"), _at(d, "10:30"))]
    H.record([_finding("Benny's nursery settling-in session", d, "Little Acorns",
                       "gather paperwork, Red Book, birth certificate"),
              _finding("Nursery settling-in session for Benny", d, "Little Acorns Nursery, Leyton",
                       "bring the Red Book and paperwork"),
              _finding("Settling-in session — Benny", d, "", "pack Red Book and paperwork")])
    _tick()
    _tick()
    assert len(_preps()) == 1, [p["what"] for p in _preps()]
    rows = H.rows()
    assert len(rows) == 3 and all(r.get("prep_task_id") == _preps()[0]["id"] for r in rows.values())


@check("A4: an unrelated open nursery task neither suppresses the prep nor is adopted as it")
def _():
    _fresh("a4b")
    O.open_task("Pay the nursery invoice", due=(TODAY + timedelta(days=5)).isoformat())
    _redbook(TODAY + timedelta(days=1))
    _tick()
    assert len(_preps()) == 1


@check("A5: opening a prep costs no reshuffle and no model call")
def _():
    _fresh("a5")
    D.refresh_tick()
    _CLOCK["now"] += timedelta(minutes=5)
    _redbook(TODAY + timedelta(days=1))
    D.refresh_tick()
    plan = json.loads(D._plan_path(TODAY).read_text())
    assert plan["trigger"] != "reshuffle", plan["reasons"]
    assert _CALLS["model"] == 0


@check("A6: a light, screen-free prep may go in family time; a screen prep may not")
def _():
    _fresh("a6")
    d = TODAY + timedelta(days=1)
    busy = _ev("u-work", "Offsite", _at(TODAY, "07:00"), _at(TODAY, "17:30"), "Canary Wharf")
    _EVENTS["v"] = [busy, _ev("u-swim", "Swim gala", _at(d, "09:00"), _at(d, "11:00"), "Leyton Pool"),
                    _ev("u-trip", "School trip", _at(d, "08:30"), _at(d, "15:00"), "Kew Gardens")]
    H.record([_finding("Swim gala", d, "Leyton Pool", "pack the swim bag"),
              _finding("School trip", d, "Kew Gardens", "fill in the online consent form")])
    _tick()
    by = {p["what"]: p for p in _preps()}
    assert by["Pack the swim bag"]["activity"] == "errands"
    assert by["Fill in the online consent form"]["activity"] == "admin"
    plan = D.current(_PERSONA)
    fam = (_at(TODAY, "17:30")[:16], _at(TODAY, "20:30")[:16])
    blocks = {x["title"]: x for x in plan["blocks"] if x["kind"] == "task"}
    swim = blocks["Pack the swim bag"]
    assert fam[0] <= swim["start"] < fam[1] and not swim.get("displaced_protected"), swim
    form = blocks.get("Fill in the online consent form")
    assert form is None or not (fam[0] <= form["start"] < fam[1]) or form.get("displaced_protected"), form


@check("A8: a refused open is stamped on the finding and never retried every five minutes")
def _():
    _fresh("a8")
    d = TODAY + timedelta(days=1)
    _redbook(d)
    key = next(iter(H.rows()))
    sid = D._prep_source(key, "gather the Red Book and paperwork")
    O._with_store(None, lambda doc: doc["tasks"].append(
        {"id": "ob_old", "what": "Old prep", "kind": "deadline", "status": "done",
         "source_id": sid, "closed_at": O._stamp()}))
    _tick()
    assert H.rows()[key].get("prep_refused"), H.rows()[key]
    calls = _CALLS["open_plan"]
    _tick()
    _tick()
    assert _CALLS["open_plan"] == calls, "a refused open was retried"
    assert [p for p in _preps() if p["status"] == "open"] == []


@check("A9: the prep follows its event — moved → due moves; deleted → moot; calendar can't tell "
       "→ unchanged")
def _():
    _fresh("a9")
    d1, d2 = TODAY + timedelta(days=1), TODAY + timedelta(days=2)
    _redbook(d1)
    _tick()
    [p] = _preps()
    assert p["due"] == TODAY.isoformat()
    _EVENTS["v"] = [_ev("u-nursery", "Benny settling-in — Little Acorns", _at(d2, "09:30"),
                        _at(d2, "10:30"))]
    _tick()
    [p] = _preps()
    assert p["due"] == d1.isoformat() and p["moot_after"] == d2.isoformat(), p
    # The calendar cannot be read: the snapshot fails, and nothing is closed.
    _EVENTS["error"] = "CalDAV timeout"
    _tick()
    assert _preps()[0]["status"] == "open", "closed on a calendar it could not read"
    # Moved out of the snapshot's three days: found by the 60-day lookup, and followed.
    _EVENTS.pop("error")
    d10 = TODAY + timedelta(days=10)
    _EVENTS["v"] = [_ev("u-nursery", "Benny settling-in — Little Acorns", _at(d10, "09:30"),
                        _at(d10, "10:30"))]
    st = D._load_state(_PERSONA)
    st["snapshot"]["events"] = []                 # the snapshot no longer holds it
    D._write_json(D._state_path(_PERSONA), st)
    O._with_store(None, lambda doc: [t["prep_for"].update(start=_at(d1, "09:30"))
                                     for t in doc["tasks"] if t.get("prep_for")])
    D._prep_follow(_PERSONA, st, [O._norm(t) for t in O._load()], TODAY)
    p = _preps()[0]
    assert p["status"] == "open" and p["moot_after"] == d10.isoformat(), p
    # Deleted: a good read of every calendar that no longer holds it.
    _EVENTS["v"] = []
    O._with_store(None, lambda doc: [t["prep_for"].update(start=_at(d1, "09:30"))
                                     for t in doc["tasks"] if t.get("prep_for")])
    _tick()
    p = _preps()[0]
    assert p["status"] == "moot" and p["evidence"] == D._PREP_GONE, p


@check("Fable #1: a prep left undone the night before gets 'before <start>' on the event's "
       "morning, and closes once the event has started")
def _():
    _fresh("fable1")
    d1 = TODAY + timedelta(days=1)
    _redbook(d1)
    _tick()
    [p] = _preps()
    assert p["due"] == TODAY.isoformat() and not p.get("before")
    _CLOCK["now"] = datetime.combine(d1, time(7, 0))
    _tick()
    [p] = _preps()
    assert p["due"] == d1.isoformat() and p["before"] == "09:30", p
    _CLOCK["now"] = datetime.combine(d1, time(9, 31))
    _tick()
    p = _preps()[0]
    assert p["status"] == "moot" and p["evidence"] == D._PREP_STARTED, p


@check("R2: a finding from mail with no calendar event becomes a plain dated prep, not followed")
def _():
    _fresh("mail_only")
    d = TODAY + timedelta(days=1)
    H.record([_finding("Passport appointment", d, "HM Passport Office", "print the booking form")])
    _tick()
    [p] = _preps()
    assert p["due"] == TODAY.isoformat() and not p["prep_for"].get("uid"), p
    _UID_LOOKUP["v"] = {"error": "No event found with uid 'x'."}
    _tick()
    assert _preps()[0]["status"] == "open"


@check("R2: precursor_by before the event wins; a far precursor waits for the near window")
def _():
    _fresh("by")
    H.record([_finding("Mover's claim", TODAY + timedelta(days=9), "", "post the claim packet",
                       by=(TODAY + timedelta(days=1)).isoformat(), kind="deadline"),
              _finding("Conference", TODAY + timedelta(days=20), "ExCeL", "book the hotel")])
    _tick()
    [p] = _preps()
    assert p["what"] == "Post the claim packet" and p["due"] == (TODAY + timedelta(days=1)).isoformat()


@check("flag off restores stage 1 — no prep is opened and the precursor stays under Important; "
       "horizon_cap off delivers every finding in the horizon block")
def _():
    _fresh("stage1", flags={"prep_tasks": False, "horizon_cap": False})
    tomorrow = TODAY + timedelta(days=1)
    _redbook(tomorrow)
    _tick()
    D.refresh_tick()
    assert _preps() == []
    assert H.prep_items(day=tomorrow)
    H.record([_finding("Dentist", tomorrow, "Smile Clinic"), _finding("Gig", tomorrow, "Troxy")])
    block = H.context_block()
    assert "Dentist" in block and "Gig" in block and "Benny" in block, block


# =============================================================================================
# R10 — review finding #5: a nudge due near a scheduled session reaches it
# =============================================================================================

_SCHED = {"schedules": {
    "evening_close": {"time": "20:00", "agent": "coordinator"},
    "weekly_pattern_miner": {"time": "19:50", "agent": "pattern_miner",
                             "day": TODAY.strftime("%A").lower()},
}, "interval_near_fixed_minutes": 30}


def _r10_setup(name: str, session_offset_min: int):
    """A prep with a nudge, and a conversational session `session_offset_min` after it."""
    _fresh(name, extra={"shield_jobs": ["evening_close"]})
    O.open_plan([{"what": "Pack the Red Book", "prep_for": {"finding": "k"}, "after": "18:30",
                  "due": TODAY.isoformat(), "minutes": 15, "activity": "errands"}])
    _CLOCK["now"] = datetime.combine(TODAY, time(18, 0))
    plan = D.current(_PERSONA)
    nudge = next(x for x in plan["suggestions"] if x["kind"] == "nudge" and x["title"] == "Pack the Red Book")
    at = D._dt(nudge["at"])
    sched = {"schedules": {"evening_close": {"time": (at + timedelta(minutes=session_offset_min)).strftime("%H:%M"),
                                             "agent": "coordinator"}},
             "interval_near_fixed_minutes": 30}
    S._load_config = lambda persona=None: json.loads(json.dumps(sched))
    return nudge, at


@check("R10: a prep nudge inside a coming session's shield is carried, then reaches that "
       "session under DUE NOW — once")
def _():
    nudge, at = _r10_setup("r10", 10)
    _CLOCK["now"] = at + timedelta(minutes=1)
    out = D.nudge_tick()
    assert "carried by a fixed session" in str(out) and not _SENT, out
    _CLOCK["now"] = at + timedelta(minutes=10)
    plan = D.current(_PERSONA)
    due = D.carried_due_now(_PERSONA, plan)
    assert [x["id"] for x in due] == [nudge["id"]], due
    text = D.render_block(plan, kind="evening_close", due_now=due)
    assert "DUE NOW" in text and "Pack the Red Book" in text.split("DUE NOW")[1], text
    assert D.carried_due_now(_PERSONA, plan) == [], "surfaced twice"


@check("Fable #3: a nudge due just AFTER a session is sent, not carried into the past; a carry "
       "the session never surfaced goes out on its own after the grace")
def _():
    nudge, at = _r10_setup("r10_after", -15)          # the session ran 15 minutes earlier
    _CLOCK["now"] = at + timedelta(minutes=1)
    out = D.nudge_tick()
    assert isinstance(out, dict) and out.get("notify") and len(_SENT) == 1, out
    nudge, at = _r10_setup("r10_skip", 10)
    _CLOCK["now"] = at + timedelta(minutes=1)
    D.nudge_tick()                                     # carried
    _CLOCK["now"] = at + timedelta(minutes=50)         # session skipped; past the grace
    out = D.nudge_tick()
    assert isinstance(out, dict) and out.get("notify") and len(_SENT) == 1, out


@check("R10: any coordinator job shields — one named nowhere (manny_school) included; an analysis "
       "job does not, unless listed in shield_jobs")
def _():
    _fresh("r10b")
    sched = {"schedules": {
        "manny_school": {"time": "16:00", "agent": "coordinator"},
        "weekly_pattern_miner": {"time": "19:50", "agent": "pattern_miner"},
    }, "interval_near_fixed_minutes": 30}
    S._load_config = lambda persona=None: json.loads(json.dumps(sched))
    _CLOCK["now"] = datetime.combine(TODAY, time(15, 45))
    assert "manny_school" in str(D._near_fixed(_PERSONA)), "a coordinator job did not shield"
    _CLOCK["now"] = datetime.combine(TODAY, time(19, 30))
    assert D._near_fixed(_PERSONA) is None, "an analysis job shielded"
    C._OVERRIDE["shield_jobs"] = ["weekly_pattern_miner"]
    assert "weekly_pattern_miner" in str(D._near_fixed(_PERSONA))


# =============================================================================================
# § 12 M3 — a task that slips is raised every day, with how long; the rider said once
# =============================================================================================

@check("M3: a task left undone is raised each day with how long it has slipped and since when, "
       "with dismissal offered — and stops once it is done")
def _():
    _fresh("m3")
    # Dated: an undated one-off is never placed on a day (R4), so it cannot slip from one.
    r = O.open_task("Repot the basement plants", minutes=30, due=TODAY.isoformat())
    tid = r.split()[1]
    day1 = TODAY
    D.refresh_tick()
    assert any(x.get("task_id") == tid for x in D.current(_PERSONA)["blocks"])
    for n in (1, 2):
        _CLOCK["now"] = datetime.combine(day1 + timedelta(days=n), time(7, 0))
        D.refresh_tick()
        slip = D._load_state(_PERSONA)["slips"][tid]
        assert slip["days"] == n and slip["first"] == day1.isoformat(), slip
        text = D.render_block(D.current(_PERSONA), kind="morning_brief")
        assert f"slipped {n} day" in text and "drop it" in text, text
    O.update_task(tid, "done", evidence="repotted them")
    _CLOCK["now"] = datetime.combine(day1 + timedelta(days=3), time(7, 0))
    D.refresh_tick()
    assert tid not in D._load_state(_PERSONA).get("slips", {})
    assert "slipped" not in D.render_block(D.current(_PERSONA), kind="morning_brief")


@check("M3: 'takes your own time' is said once per task, not every day it lands there")
def _():
    _fresh("m3_rider")
    r = O.open_task("File the VAT return", due=TODAY.isoformat(), minutes=60)
    tid = r.split()[1]
    plan = {"version": D._VERSION, "day": TODAY.isoformat(),
            "window": {"wake": _at(TODAY, "07:00")[:16], "bed": _at(TODAY, "23:00")[:16],
                       "wake_source": "stated", "bed_source": "stated"},
            "blocks": [{"id": f"task:{tid}@1800", "kind": "task", "ref": tid, "task_id": tid,
                        "title": "File the VAT return", "start": _at(TODAY, "18:00")[:16],
                        "end": _at(TODAY, "19:00")[:16], "essential": True,
                        "displaced_protected": True, "copy": 0, "stakes": None, "due": None}],
            "suggestions": [], "unplaced": [], "notes": []}
    shown: dict = {}
    text = D.render_block(plan, kind="morning_brief", shown=shown)
    assert "takes the user's own time — say so" in text, text
    assert shown["riders"] == [tid]
    D.after_render(_PERSONA, shown)
    D.note_said("Morning — nothing until ten.")              # not said: still owed
    D.note_said("The VAT return is next, at six.")           # named, not explained (Fable #2)
    assert tid not in (D._load_state(_PERSONA).get("riders") or {})
    D.after_render(_PERSONA, shown)
    D.note_said("The VAT return eats into your evening — it's due today.")
    assert tid in D._load_state(_PERSONA)["riders"]
    _CLOCK["now"] += timedelta(days=1)
    plan2 = {**plan, "day": (TODAY + timedelta(days=1)).isoformat(),
             "blocks": [{**plan["blocks"][0],
                         "start": _at(TODAY + timedelta(days=1), "18:00")[:16],
                         "end": _at(TODAY + timedelta(days=1), "19:00")[:16]}]}
    text2 = D.render_block(plan2, kind="morning_brief")
    assert "say so" not in text2 and "already explained once" in text2, text2
    assert "say why, once" not in text2


# =============================================================================================
# § 12 M2 — new horizon findings share the Important cap
# =============================================================================================

@check("M2: on the brief, new findings share the two-slot Important cap with a vital deadline; "
       "only what is shown is charged, and a held one keeps its offers")
def _():
    _fresh("m2")
    tomorrow = TODAY + timedelta(days=1)
    # Later in the day, so it is neither Now nor Next (those never repeat under Important).
    O.open_task("Tidy the desk drawer", due=TODAY.isoformat(), minutes=30)
    O.open_task("Pay the council tax", due=TODAY.isoformat(), minutes=10, after="15:00",
                stakes="vital")
    H.record([_finding("Echocardiogram", tomorrow, "Royal London"),
              _finding("Aisha's Thanksgiving invitation", tomorrow, "Aisha's"),
              _finding("Teams seminar", tomorrow, "Online")])
    assert H.context_block() == "", "the horizon block must step aside while capped"
    plan = D.current(_PERSONA)
    _CLOCK["now"] = datetime.combine(TODAY, time(7, 1))
    shown: dict = {}
    text = D.render_block(plan, kind="morning_brief", findings=H.new_findings(), shown=shown)
    assert "Pay the council tax" in text
    new_line = next(line for line in text.splitlines() if line.startswith("New —"))
    assert sum(t in new_line for t in ("Echocardiogram", "Aisha", "Teams")) == 1, new_line
    assert len(shown["findings"]) == 1
    D.after_render(_PERSONA, shown)
    offers = {r["item"]["title"]: r.get("offers", 0) for r in H.rows().values()}
    assert sorted(offers.values()) == [0, 0, 1], offers


@check("M2: an ordinary turn carries at most one new finding; a brief with room carries two")
def _():
    _fresh("m2b")
    tomorrow = TODAY + timedelta(days=1)
    H.record([_finding("Dentist", tomorrow, "Smile Clinic"), _finding("Gig", tomorrow, "Troxy"),
              _finding("Book club", tomorrow, "Library")])
    plan = D.current(_PERSONA)

    def count(kind):
        text = D.render_block(plan, kind=kind, findings=H.new_findings())
        line = next((x for x in text.splitlines() if x.startswith("New —")), "")
        return sum(t in line for t in ("Dentist", "Gig", "Book club"))

    assert count(None) == 1
    assert count("morning_brief") == 2


# =============================================================================================
# Fable diff review — the fixes for #2, #4, #5, #6, #7
# =============================================================================================

def _slipped(n_tasks: int) -> list[str]:
    names = ["Repot the fern", "Descale the kettle", "Sharpen the knives", "Oil the hinges"]
    ids = []
    for w in names[:n_tasks]:
        r = O.open_task(w, minutes=20, due=TODAY.isoformat())
        assert r.startswith("task "), r
        ids.append(r.split()[1])
    D.refresh_tick()
    _CLOCK["now"] = datetime.combine(TODAY + timedelta(days=1), time(7, 0))
    D.refresh_tick()
    return ids


@check("Fable #2: slips are asked on the brief and close only, at most two, once a day — and "
       "not for a task the user gave a later day")
def _():
    _fresh("f2")
    ids = _slipped(4)
    plan = D.current(_PERSONA)
    assert "slipped" not in D.render_block(plan, kind=None), "a slip ask on an ordinary turn"
    shown: dict = {}
    text = D.render_block(plan, kind="morning_brief", shown=shown)
    assert text.count("slipped 1 day") == 2 and len(shown["slips"]) == 2, text
    D.after_render(_PERSONA, shown)
    p1 = list(shown["slips"])
    # Live 2026-11-20: offered at the brief, never said. Named without the question doesn't count;
    # the close then offers the NEXT pair, so all four get their turn (Fable live-fix #3).
    D.note_said("Morning Mike — " + _task(p1[0])["what"].lower() + " is first, then the gym.")
    shown2: dict = {}
    text2 = D.render_block(plan, kind="evening_close", shown=shown2)
    p2 = list(shown2["slips"])
    assert set(p2).isdisjoint(p1) and len(p2) == 2, ("no rotation", p1, p2, text2)
    D.after_render(_PERSONA, shown2)
    D.note_said("Two things have slipped a day: " + " and ".join(_task(t)["what"] for t in p2)
                + " — now, or drop them?")
    shown3: dict = {}
    D.render_block(plan, kind="morning_brief", shown=shown3)
    assert shown3["slips"] == p1, ("the unsaid pair comes back", shown3["slips"], p1)
    D.after_render(_PERSONA, shown3)
    D.note_said("Also slipped since yesterday: " + " and ".join(_task(t)["what"] for t in p1) + ".")
    assert "slipped" not in D.render_block(plan, kind="morning_brief"), "asked twice in a day"
    later = TODAY + timedelta(days=5)
    O.update_task(ids[0], "reschedule", new_due=later.isoformat(), evidence="Friday then")
    _CLOCK["now"] = datetime.combine(TODAY + timedelta(days=2), time(7, 0))
    D.refresh_tick()
    shown3: dict = {}
    D.render_block(D.current(_PERSONA), kind="morning_brief", shown=shown3)
    assert ids[0] not in shown3["slips"], "asked about a task given a later day"


@check("Fable #4: a finding dated today is never held behind higher-ranked items; with no plan "
       "block, the horizon block delivers uncapped")
def _():
    _fresh("f4")
    O.open_task("Tidy the desk drawer", due=TODAY.isoformat(), minutes=30)
    O.open_task("Pay the council tax", due=TODAY.isoformat(), minutes=10, after="15:00", stakes="vital")
    O.open_task("Renew the parking permit", due=TODAY.isoformat(), minutes=10, after="16:00",
                stakes="vital")
    H.record([_finding("Show and Tell", TODAY, "Leyton Primary")])
    plan = D.current(_PERSONA)
    text = D.render_block(plan, kind="morning_brief", findings=H.new_findings())
    assert "Show and Tell" in text, text
    assert H.context_block() == ""
    assert "Show and Tell" in H.context_block(uncapped=True)


@check("Fable #5/#6: the redo question is an Ask, counted as asked only once a reply asks it; a "
       "prerequisite that ran out of time is raised too")
def _():
    _fresh("f56")
    ids = _two_step()
    O.update_task(ids["a"], "dismissed", evidence="skip it")
    plan = D.current(_PERSONA)
    shown: dict = {}
    text = D.render_block(plan, kind=None, cascades=O.cascades_to_raise(), shown=shown)
    asks = next(line for line in text.splitlines() if line.startswith("Asks"))
    assert "can't go ahead" in asks, text
    D.after_render(_PERSONA, shown)
    D.note_said("Sure, the dentist is at three.")              # an unrelated reply
    assert O.cascades_to_raise(), "stamped by a reply that did not ask it"
    shown = {}
    D.render_block(plan, kind="morning_brief", cascades=O.cascades_to_raise(), shown=shown)
    D.after_render(_PERSONA, shown)
    D.note_said("Photographing the passport can't happen without finding it first — redo that?")
    assert O.cascades_to_raise() == []
    _fresh("f6")
    res = O.open_plan([{"key": "a", "what": "Collect the tickets", "due": _D3,
                        "moot_after": (TODAY - timedelta(days=1)).isoformat()},
                       {"key": "b", "what": "Hand the tickets over", "needs": ["a"], "due": _D3}])
    O.sweep()
    [c] = O.cascades_to_raise()
    assert c["lapsed"] and c["end"] == "Hand the tickets over"
    text = D.render_block(D.current(_PERSONA), kind="morning_brief", cascades=[c])
    assert "ran out of time" in text, text


@check("Fable #7: rescheduling a dismissed step brings its later steps back; a later step can't "
       "be reopened on its own while its prerequisite is closed")
def _():
    _fresh("f7")
    ids = _two_step()
    O.update_task(ids["a"], "dismissed", evidence="skip it")
    r = O.update_task(ids["b"], "reopen", evidence="actually post it")
    assert r.startswith("error") and ids["a"] in r, r
    assert _task(ids["b"])["status"] == "moot"
    r = O.update_task(ids["a"], "reschedule", new_due=_D3, evidence="do it Friday")
    assert "are back" in r, r
    assert _task(ids["b"])["status"] == "open" and _task(ids["b"])["_blocked"]


# =============================================================================================
# Live data, 2026-11-19 → 21 — the four misses phase 1's first days showed
# =============================================================================================

@check("live A: a prep whose finding has its own 'by' date still gets 'before <start>' on the "
       "event's day (the Bupa code, 11-20)")
def _():
    _fresh("live_a")
    d1 = TODAY + timedelta(days=1)
    _EVENTS["v"] = [_ev("u-bupa", "Appointment — Blackheath Hospital", _at(d1, "15:30"),
                        _at(d1, "16:30"), "Blackheath Hospital")]
    H.record([_finding("Appointment with Circle Health Group", d1, "Blackheath Hospital",
                       "obtain Bupa pre-authorisation code prior to appointment",
                       by=TODAY.isoformat())])
    _tick()
    [p] = _preps()
    assert p["due"] == TODAY.isoformat() and not p.get("before"), p
    _CLOCK["now"] = datetime.combine(d1, time(7, 0))
    _tick()
    [p] = _preps()
    assert p["due"] == d1.isoformat() and p["before"] == "15:30", p


@check("live C: a nudge wake carries no new findings and no redo question, and spends no offer")
def _():
    _fresh("live_c")
    H.record([_finding("Osteopathy follow-up", TODAY + timedelta(days=1), "Greenwich")])
    import core.orchestrator as ORCH
    _two_step()
    O.update_task(next(t["id"] for t in O._load() if t["what"].startswith("Find")), "dismissed",
                  evidence="skip")
    D.current(_PERSONA)
    text = ORCH._day_plan_block(_PERSONA, None, True, nudge=True)
    assert text and "Osteopathy" not in text and "can't go ahead" not in text, text
    assert all((r.get("offers") or 0) == 0 for r in H.rows().values())
    text = ORCH._day_plan_block(_PERSONA, "morning_brief", True)
    assert "Osteopathy" in text and "can't go ahead" in text, text


def _live_d_body(plan, item):
    S._load_config = lambda persona=None: {"schedules": {
        "location_anticipation": {"time": "10:00", "agent": "coordinator"}}}
    _CLOCK["now"] = datetime.combine(TODAY, time(9, 36))
    out = D.nudge_tick()
    assert isinstance(out, dict) and out.get("notify") and len(_SENT) == 1, out
    # One already carried (by the old code) and now 25 minutes late: dropped, not said.
    D._mark(_PERSONA, TODAY.isoformat(), [{**item, "id": "nudge:travel:u-old@0935"}], "carried")
    _CLOCK["now"] = datetime.combine(TODAY, time(10, 0))
    assert D.carried_due_now(_PERSONA, plan, mark=False) == []
    _CLOCK["now"] = datetime.combine(TODAY, time(10, 40))
    out = D.nudge_tick()
    assert len(_SENT) == 1, ("a late 'leave now' went out", out)


@check("live D: a 'leave now' inside a coming session's shield is sent on time, not carried; a "
       "carried one past its moment is dropped, never said late (the 10:00 meeting, 11-20)")
def _():
    _fresh("live_d")
    _CLOCK["now"] = datetime.combine(TODAY, time(9, 0))
    plan = D.current(_PERSONA)
    item = {"id": "nudge:travel:u-mtg@0935", "kind": "nudge", "at": _at(TODAY, "09:35")[:16],
            "ref": f"u-mtg@{_at(TODAY, '10:00')}", "title": "travel to Meeting",
            "why": "leave now — 20 min by transit"}
    plan = {**plan, "suggestions": [item]}
    real_current = D.current
    D.current = lambda *a, **k: plan                    # the hand-made suggestion stands
    try:
        _live_d_body(plan, item)
    finally:
        D.current = real_current


# =============================================================================================

def main() -> int:
    passed = sum(1 for _, ok, _ in _results if ok)
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if not ok:
            print("        " + detail.replace("\n", "\n        "))
    print(f"\n{passed} passed, {len(_results) - passed} failed, {len(_results)} total")
    return 0 if passed == len(_results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
