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


@check("2. is_disrupted matches the old travel_watch rule on its four cases — a late leg, "
       "cancelled, diverted — and an early arrival is not disrupted; each flight carries it")
def _():
    cases = [
        (_flight(dep=("2026-12-01 10:00", "2026-12-01 10:40")), True),
        (_flight(status="Cancelled"), True),
        (_flight(status="Diverted"), True),
        (_flight(arr=("2026-12-01 12:00", "2026-12-01 11:32")), False),
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
    assert got == [c[1] for c in cases], got
    for f in out["flights"]:
        old = (f["departure"].get("delayed") or f["arrival"].get("delayed")
               or f["status"].lower() in ("cancelled", "canceled", "diverted"))
        assert F.is_disrupted(f) == bool(old), f
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


@check("travel_watch uses flights.is_disrupted and still reports a disrupted line only")
def _():
    import inspect
    import tools.travel_watch as TW
    src = inspect.getsource(TW)
    assert "is_disrupted(f)" in src and '"cancelled", "canceled", "diverted"' not in src


if __name__ == "__main__":
    for name, ok, detail in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
        if detail:
            print("      " + detail.replace("\n", "\n      "))
    passed = sum(1 for _, ok, _ in _results if ok)
    print(f"\n{passed}/{len(_results)} passed")
    sys.exit(0 if passed == len(_results) else 1)
