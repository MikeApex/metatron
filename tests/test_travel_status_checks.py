"""
tests/test_travel_status_checks.py — Stage 5 M18: flight and line checks report only
disruptions, and a second flight check never trips the one-request-a-second limit
(archive/plans/instructions_to_code_stage5_one_channel_plan_2026-11-23.md § 1 M18).

`requests.get`, `time.sleep` and `time.monotonic` are stubbed — no network, never a real sleep.

    python3 tests/test_travel_status_checks.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault("METATRON_AUTH_PASSWORD", "x")

import tools.flights as F  # noqa: E402
import tools.tfl_status as TFL  # noqa: E402

_results: list[tuple[str, bool, str]] = []


def check(name: str):
    def deco(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except Exception as exc:  # noqa: BLE001
            import traceback
            _results.append((name, False, f"{type(exc).__name__}: {exc}\n"
                             + "".join(traceback.format_exc().splitlines(True)[-4:])))
        return fn
    return deco


class _Resp:
    def __init__(self, payload, status=200):
        self._p, self.status_code = payload, status
        self.ok = 200 <= status < 300

    def raise_for_status(self):
        return None

    def json(self):
        return self._p


def _line(name, desc, reason=""):
    return {"name": name, "lineStatuses": [{"statusSeverity": 10 if desc == "Good Service" else 6,
                                            "statusSeverityDescription": desc,
                                            "reason": reason}]}


@check("1. a mixed TfL result keeps only the disrupted lines and names the good ones")
def _():
    saved = TFL.requests.get
    TFL.requests.get = lambda url, timeout=None: _Resp([
        _line("DLR", "Good Service"), _line("Victoria", "Severe Delays", "A signal failure"),
        _line("Elizabeth line", "Good Service")])
    try:
        out = TFL.get_tfl_status(["dlr", "victoria", "elizabeth"])
    finally:
        TFL.requests.get = saved
    assert out["lines"] == [{"name": "Victoria", "status": "Severe Delays", "disrupted": True,
                             "detail": "A signal failure"}], out
    assert out["good_service"] == ["DLR", "Elizabeth line"], out


def _leg(sched, actual=""):
    leg = {"airport": {"name": "Heathrow", "iata": "LHR"}, "terminal": "5",
           "scheduledTime": {"local": sched}}
    if actual:
        leg["revisedTime"] = {"local": actual}
    return leg


def _flight(status="Expected", dep=("2026-12-01 10:00", ""), arr=("2026-12-01 12:00", "")):
    return {"number": "XY 100", "airline": {"name": "Example Air"}, "status": status,
            "departure": _leg(*dep), "arrival": _leg(*arr)}


@check("2. is_disrupted (review item 12): the API's own status spellings — Canceled, "
       "CanceledUncertain, Diverted, Delayed with no revised time — and a leg 15+ minutes late "
       "are disruptions; 5 minutes late, early, Expected, EnRoute and Arrived are not; each flight "
       "carries the flag and keeps its details")
def _():
    cases = [
        (_flight(status="Canceled"), True),
        (_flight(status="CanceledUncertain"), True),
        (_flight(status="Cancelled"), True),
        (_flight(status="Diverted"), True),
        (_flight(status="Delayed"), True),                       # no revised time at all
        (_flight(dep=("2026-12-01 10:00", "2026-12-01 10:40")), True),
        (_flight(arr=("2026-12-01 12:00", "2026-12-01 12:15")), True),
        (_flight(dep=("2026-12-01 10:00", "2026-12-01 10:05")), False),
        (_flight(arr=("2026-12-01 12:00", "2026-12-01 11:32")), False),
        (_flight(status="EnRoute"), False),
        (_flight(status="Arrived"), False),
        (_flight(), False),
    ]
    payload = [c[0] for c in cases]
    saved = (F.requests.get, F._api_key, F._throttle)
    F.requests.get = lambda *a, **k: _Resp(payload)
    F._api_key = lambda: "k"
    F._throttle = lambda: None
    try:
        out = F.get_flight_status("XY100")
    finally:
        F.requests.get, F._api_key, F._throttle = saved
    got = [f["disrupted"] for f in out["flights"]]
    assert got == [c[1] for c in cases], list(zip([c[0]["status"] for c in cases], got))
    assert out["flights"][0]["departure"]["terminal"] == "5"     # details are kept




@check("3. two back-to-back flight calls sleep only for the remainder of 1.05 s; a call after "
       "the interval does not sleep")
def _():
    clock = {"t": 100.0}
    slept: list[float] = []
    saved = (F.time.monotonic, F.time.sleep, F.requests.get, F._api_key)
    F.time.monotonic = lambda: clock["t"]

    def _sleep(s):
        slept.append(round(s, 3))
        clock["t"] += s
    F.time.sleep = _sleep
    F.requests.get = lambda *a, **k: _Resp([])
    F._api_key = lambda: "k"
    F._LAST_REQUEST["at"] = None
    try:
        F.get_flight_status("XY100")
        clock["t"] += 0.3
        F.get_flight_status("XY101")
        clock["t"] += 5
        F.get_flight_status("XY102")
    finally:
        F.time.monotonic, F.time.sleep, F.requests.get, F._api_key = saved
        F._LAST_REQUEST["at"] = None
    assert slept == [0.75], slept


@check("travel_watch by behaviour (review item 14): check_travel_events reports the disrupted "
       "flight and the disrupted line only — an on-time flight, a 5-minute slip and Good Service "
       "lines say nothing")
def _():
    import tools.flights as FL
    import tools.tfl_status as TS
    import tools.travel_watch as TW
    flights = {
        "XY1": {"flights": [{"number": "XY 1", "airline": "Example Air", "status": "CanceledUncertain",
                             "departure": {"delay_minutes": 0}, "arrival": {"delay_minutes": 0}}]},
        "XY2": {"flights": [{"number": "XY 2", "airline": "Example Air", "status": "Expected",
                             "departure": {"delay_minutes": 5}, "arrival": {"delay_minutes": 0}}]},
    }
    saved = (FL.get_flight_status, TS.requests.get)
    FL.get_flight_status = lambda n, date="": flights[n]
    TS.requests.get = lambda url, timeout=None: _Resp([
        _line("DLR", "Good Service"), _line("Victoria", "Part Suspended", "Engineering works")])
    try:
        found = TW.check_travel_events([
            {"uid": "e1", "title": "Flight out", "flights": ["XY1", "XY2"], "lines": []},
            {"uid": "e2", "title": "Into town", "flights": [], "lines": ["dlr", "victoria"]}])
    finally:
        FL.get_flight_status, TS.requests.get = saved
    assert [(f["kind"], f["subject"]) for f in found] == [("flight", "XY 1"),
                                                          ("transit", "Victoria")], found




if __name__ == "__main__":
    for name, ok, detail in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
        if detail:
            print("      " + detail.replace("\n", "\n      "))
    passed = sum(1 for _, ok, _ in _results if ok)
    print(f"\n{passed}/{len(_results)} passed")
    sys.exit(0 if passed == len(_results) else 1)
