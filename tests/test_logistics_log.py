"""
tests/test_logistics_log.py — Logistics' own records, kept by code (instructions-to-code Stage 4,
4d: M13, M12's code half, M14).

Plan: archive/plans/instructions_to_code_stage4_evidence_plan_2026-11-23.md § 1 M13 tests 1–6
(M12's are M13's: no `pending_items`), § 1 M14 tests 1–6, build-time amendment 4. Offline: a temp
persona tree, CalDAV and the conflict check stubbed, every calendar write asserted uncalled, no
model, no network.

    python3 tests/test_logistics_log.py
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
os.environ.setdefault("METATRON_AUTH_PASSWORD", "x")

import core.orchestrator as ORC  # noqa: E402
import core.prefetch as PF  # noqa: E402
import core.trace as TR  # noqa: E402
import tools.caldav as CAL  # noqa: E402
import tools.day_plan as DP  # noqa: E402
import tools.logistics_log as LL  # noqa: E402
import tools.scheduling as SCH  # noqa: E402
from support.stage3_fixtures import PERSONA, patched, sandbox  # noqa: E402
from tools import turn_context as T  # noqa: E402
from tools.logger import read_log, write_log  # noqa: E402

_results: list[tuple[str, bool, str]] = []


def check(name):
    def wrap(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except Exception as e:  # noqa: BLE001
            import traceback
            _results.append((name, False, f"{type(e).__name__}: {e}\n{traceback.format_exc()}"))
        return fn
    return wrap


def _rec(agent: str, calls: list[tuple[str, dict, str, bool]]):
    rec = TR.AgentRecord(agent=agent, provider="", model="")
    for name, args, result, ok in calls:
        TR.record_tool_call(rec, 1, name, args, result, 1.0, ok=ok)
    return rec


def _event_ok(uid: str) -> str:
    return json.dumps({"status": "created", "uid": uid, "title": "x"}, indent=2)


def _code_part() -> dict:
    return ((read_log() or {}).get("logistics") or {}).get(LL.SUBKEY) or {}


# --- M13 ---------------------------------------------------------------------------------------

@check("M13.1 two writes and one failed write: only the two are recorded")
def _():
    with sandbox():
        rec = _rec("logistics", [
            ("write_calendar_event", {"title": "Dentist", "start": "2026-11-21T09:00",
                                      "end": "2026-11-21T10:00"}, _event_ok("u-1"), True),
            ("write_schedule", {"name": "bins", "prompt": "Bins out", "at": "2026-11-21T19:00:00"},
             "Scheduled 'bins' — once at 2026-11-21T19:00:00, runs coordinator, "
             "notification push.", True),
            ("write_calendar_event", {"title": "Gym", "start": "2026-11-21T18:00",
                                      "end": "2026-11-21T19:00"},
             json.dumps({"error": "end must be after start."}), False),
            ("record_horizon_item", {"title": "Passport renewal", "date": "2027-01-10"},
             "Not filed: a horizon item needs a non-empty `title`", True)])
        LL.record_run(rec, "EVENTS SCHEDULED: Dentist", user_turn=True)
        part = _code_part()
        ev = part["events_scheduled"]
        assert [(e["title"], e["uid"], e["start"]) for e in ev] == [
            ("Dentist", "u-1", "2026-11-21T09:00")], part
        assert [r["name"] for r in part["reminders_set"]] == ["bins"], part
        assert "horizon_items" not in part, part


@check("M13.2 (M12) no pending_items key is ever written")
def _():
    with sandbox():
        rec = _rec("logistics", [("record_horizon_item", {"title": "Car service", "date":
                                                          "2026-12-01"},
                                  "Filed: Car service. The user has not been told", True)])
        LL.record_run(rec, "PENDING_CONFIRMATION: booking", user_turn=True)
        day = read_log()
        assert "pending_items" not in json.dumps(day), day
        assert [h["title"] for h in _code_part()["horizon_items"]] == ["Car service"]


_COORD = ("EVENTS SCHEDULED: none\nCOORDINATION_OPPORTUNITIES: pick up the parcel near the "
          "dentist\n- the pharmacy is on the same street\nFLAGS: none")


@check("M13.3 a scheduled turn writes no coordination_opportunities (actions still recorded)")
def _():
    with sandbox():
        rec = _rec("logistics", [("write_calendar_event", {"title": "Dentist", "start":
                                                           "2026-11-21T09:00"},
                                  _event_ok("u-1"), True)])
        LL.record_run(rec, _COORD, user_turn=False)
        part = _code_part()
        assert "coordination_opportunities" not in part and part["events_scheduled"], part
        LL.record_run(_rec("logistics", []), _COORD, user_turn=True)
        assert [c["text"] for c in _code_part()["coordination_opportunities"]] == [
            "pick up the parcel near the dentist", "the pharmacy is on the same street"]


@check("M13.4 a non-Logistics agent writes nothing; Logistics through _run_single_agent does, "
       "with the turn's user/scheduled status")
def _():
    def fake(agent_calls):
        def run(system_prompt, user_input, tool_schemas, tool_handlers, **kw):
            rec = TR.get_current_agent()
            for name, args, result in agent_calls:
                TR.record_tool_call(rec, 1, name, args, result, 1.0, ok=True)
            return _COORD
        return run
    calls = [("write_calendar_event", {"title": "Dentist", "start": "2026-11-21T09:00"},
              _event_ok("u-9"))]
    with sandbox():
        with patched([(ORC, "run_session_openai", fake(calls)),
                      (PF, "build", lambda *a, **k: "")]), T.turn_scope(user_turn=True):
            ORC._run_single_agent("relationships", "x", persona=PERSONA, provider="openai")
        assert "logistics" not in (read_log() or {}), read_log()
        with patched([(ORC, "run_session_openai", fake(calls)),
                      (PF, "build", lambda *a, **k: "")]), T.turn_scope(user_turn=False):
            ORC._run_single_agent("logistics", "x", persona=PERSONA, provider="openai")
        part = _code_part()
        assert part["events_scheduled"][0]["uid"] == "u-9", part
        assert "coordination_opportunities" not in part, part
        with patched([(ORC, "run_session_openai", fake([])),
                      (PF, "build", lambda *a, **k: "")]):
            ORC._run_single_agent("logistics", "x", persona=PERSONA, provider="openai")
        assert "coordination_opportunities" not in _code_part(), "no bound turn = not a user turn"


@check("M13.5 two runs in one day with a model write between: recorded_by_code holds both, the "
       "model's own list holds its own")
def _():
    with sandbox():
        LL.record_run(_rec("logistics", [("write_calendar_event", {"title": "Event A", "start":
                                                                   "2026-11-21T09:00"},
                                          _event_ok("u-a"), True)]), "", user_turn=True)
        write_log({"logistics": {"events_scheduled": ["X"]}})
        LL.record_run(_rec("logistics", [("write_calendar_event", {"title": "Event B", "start":
                                                                   "2026-11-22T09:00"},
                                          _event_ok("u-b"), True)]), "", user_turn=True)
        day = read_log()
        assert day["logistics"]["events_scheduled"] == ["X"], day
        assert [e["title"] for e in day["logistics"][LL.SUBKEY]["events_scheduled"]] == [
            "Event A", "Event B"], day
        # A later model write of the same block leaves code's sub-dict alone.
        write_log({"logistics": {"events_scheduled": ["Y"], "notes": "n"}})
        assert len(read_log()["logistics"][LL.SUBKEY]["events_scheduled"]) == 2


@check("M13.6 the same action seen twice is recorded once")
def _():
    with sandbox():
        call = ("update_calendar_event", {"uid": "u-1", "start": "2026-11-21T11:00"},
                _event_ok("u-1"), True)
        LL.record_run(_rec("logistics", [call, call]), "", user_turn=True)
        LL.record_run(_rec("logistics", [call]), "", user_turn=True)
        assert len(_code_part()["events_scheduled"]) == 1, _code_part()
        assert LL.record_run(_rec("logistics", [call]), "", user_turn=True) is None


# --- M14 ---------------------------------------------------------------------------------------

NOW = datetime(2026, 11, 20, 10, 15)


def _calendar_raw(*events):
    return {"events": [dict(e) for e in events], "calendar_url": "https://cal.example.test/a/",
            "calendars_read": ["Home"], "calendars_failed": [], "discovery": "ok"}


_OK = {"uid": "u1", "title": "Dentist", "start": "2026-11-20T15:00", "end": "2026-11-20T16:00",
       "description": "", "location": "", "status": "CONFIRMED", "conflict_check_status": "OK"}
_F1 = {**_OK, "uid": "v1", "title": "[VERIFY] Lunch", "start": "2026-11-20T12:30",
       "end": "2026-11-20T13:30", "conflict_check_status": "FAILED"}
_F2 = {**_F1, "uid": "v2", "start": "2026-11-21T12:30", "end": "2026-11-21T13:30"}
_F3 = {**_F1, "uid": "v3", "start": "2026-11-21T17:30", "end": "2026-11-21T18:30"}
_PAST = {**_F1, "uid": "v0", "start": "2026-11-20T08:00", "end": "2026-11-20T09:00"}


@contextlib.contextmanager
def _calendar(*events):
    """CalDAV read stubbed; every write path a re-check could touch made to fail loudly."""
    checks: list[tuple] = []
    writes: list[str] = []

    def conflicts(start, end, title="", attendees=None, location="", exclude_uid=""):
        checks.append((start, end, exclude_uid))
        return {"conflict_report": f"<untrusted_content>clear {exclude_uid}</untrusted_content>"}

    def no_write(label):
        def f(*a, **k):
            writes.append(label)
            raise AssertionError(f"{label} called by a read")
        return f
    import requests
    pairs = [(CAL, "_query_events", lambda *a, **k: _calendar_raw(*events)),
             (SCH, "check_calendar_conflicts", conflicts), (LL, "_now", lambda: NOW),
             (requests, "put", no_write("CalDAV PUT")),
             (CAL, "update_calendar_event", no_write("update_calendar_event")),
             (CAL, "_note_plan_write", no_write("_note_plan_write")),
             (DP, "note_calendar_write", no_write("note_calendar_write"))]
    with sandbox(), patched(pairs):
        yield checks, writes


def _read(agent: str, trace=None, **inputs):
    t = trace or TR.start_request_trace("u", PERSONA)
    rec = TR.push_agent(agent, "", "")
    try:
        out = ORC.dispatch_tool("read_calendar", inputs or {"start_date": "2026-11-20",
                                                            "end_date": "2026-11-21"},
                                {"read_calendar": CAL.read_calendar}, _agent_rec=rec)
    finally:
        TR.pop_agent(rec)
    return json.loads(out), t


@check("M14.1 Logistics' read_calendar through dispatch_tool: one FAILED future event → one "
       "check, `reverify` attached; the read itself is unchanged")
def _():
    with _calendar(_OK, _F1) as (checks, writes):
        got, t = _read("logistics")
        plain = CAL.read_calendar("2026-11-20", "2026-11-21")
        assert checks == [("2026-11-20T12:30", "2026-11-20T13:30", "v1")], checks
        assert [r["uid"] for r in got["reverify"]] == ["v1"], got
        assert "clear v1" in json.dumps(got["reverify"]) and got["reverify_note"] == \
            LL.REVERIFY_NOTE
        assert {k: v for k, v in got.items() if not k.startswith("reverify")} == \
            json.loads(json.dumps(plain)), "the read is read_calendar's result, plus reverify"
        assert writes == []
        TR.set_trace(None)


@check("M14.2+3 no write anywhere; another agent's read, a prefetch read and a direct "
       "read_calendar() make no check")
def _():
    with _calendar(_OK, _F1) as (checks, writes):
        got, _ = _read("relationships")
        assert "reverify" not in got and checks == [], (got, checks)
        TR.start_request_trace("u", PERSONA)
        block = PF.build("logistics", "plan today", "", PERSONA, now=NOW)
        assert "still unverified" in block and checks == [], (block, checks)
        CAL.read_calendar("2026-11-20", "2026-11-21")
        CAL.read_calendar_rows("2026-11-20", "2026-11-21")
        assert checks == [] and writes == []
        TR.set_trace(None)


@check("M14.4 a second read in the same request reuses `reverify` (still one check); a new "
       "request checks again")
def _():
    with _calendar(_F1) as (checks, writes):
        first, t = _read("logistics")
        second, _ = _read("logistics", trace=t)
        assert len(checks) == 1 and first["reverify"] == second["reverify"], checks
        TR.set_trace(None)
        _read("logistics")
        assert len(checks) == 2 and writes == []
        TR.set_trace(None)


@check("M14.5 at most 2 events are re-checked per read")
def _():
    with _calendar(_F3, _F1, _F2) as (checks, writes):
        got, _ = _read("logistics")
        assert [c[2] for c in checks] == ["v1", "v2"], checks
        assert len(got["reverify"]) == 2 and writes == []
        TR.set_trace(None)


@check("M14.6 a past event is ignored")
def _():
    with _calendar(_PAST, _OK) as (checks, writes):
        got, _ = _read("logistics")
        assert checks == [] and "reverify" not in got and writes == []
        TR.set_trace(None)


@check("M14.7 a calendar error or a not-connected calendar comes back as it was, unchecked")
def _():
    with _calendar() as (checks, writes):
        with patched([(CAL, "_query_events", lambda *a, **k: {"error": "401 Unauthorized"})]):
            got, _ = _read("logistics")
        assert got == {"error": "401 Unauthorized"} and checks == []
        TR.set_trace(None)


if __name__ == "__main__":
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if detail else ""))
    failed = sum(1 for _, ok, _ in _results if not ok)
    print(f"\n{len(_results) - failed} passed, {failed} failed, {len(_results)} total")
    sys.exit(1 if failed else 0)
