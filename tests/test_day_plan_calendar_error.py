"""
tests/test_day_plan_calendar_error.py — the plan block says so when the calendar could not be read
(DB-0910-02). On 2026-09-10 a remembered lecture was stated as today's confirmed commitment while
CalDAV returned 401; the plan block calls itself "authoritative for timing", so a failed read must
not leave it vouching for stale events, or for an empty day.

EVERY LIVE METER IS STUBBED (the standing rule): CalDAV (`_query_events`), Google Routes
(`get_travel_time`), the model (`_MODEL_CALL`). No persona data — a temp directory per check.
Run it, do not read it:

    python3 tests/test_day_plan_calendar_error.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import threading
from datetime import datetime, timedelta
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
_TMP = Path(tempfile.mkdtemp(prefix="day_plan_calerr_"))
_CLOCK = {"now": datetime(2026, 10, 26, 8, 0)}
O._now = lambda: _CLOCK["now"]
A._get_timezone = lambda: "Europe/London"
_PERSONA = "dp_calerr"

_SHAPE = 'wake: "07:00"\nbed: "23:00"\n'
_EVENTS = [{"uid": "u-lecture", "title": "Evening lecture", "start": "2026-10-26T19:30:00",
            "end": "2026-10-26T21:00:00", "location": "", "status": ""}]
_CAL = {"fail": False, "calls": 0}


def _query_events(start, end, persona=None, calendars="own"):
    _CAL["calls"] += 1
    if _CAL["fail"]:
        return {"error": "401 Unauthorized"}
    return {"events": json.loads(json.dumps(_EVENTS))}


CAL._query_events = _query_events
R.get_travel_time = lambda *a, **k: {"journeys": [{"duration_minutes": 25}]}
L.load_zones = lambda persona=None: []
L.current_zone = lambda persona=None: {}

_NOTICE = "Calendar could not be read"


def _fresh(name: str) -> Path:
    for th in threading.enumerate():
        if th.name.startswith("day_plan_"):
            th.join(5)
    d = _TMP / name
    (d / "config").mkdir(parents=True, exist_ok=True)
    for mod in (O, D, DS, L):
        mod.persona_data_dir = lambda persona=None, _d=d: _d
    DS.persona_config_dir = lambda persona=None, _d=d: _d / "config"
    (d / "config" / "goals.yaml").write_text("quarterly: []\n")
    G._goals_path = lambda _d=d: _d / "config" / "goals.yaml"
    (d / "day_shape.yaml").write_text(_SHAPE)
    C._OVERRIDE = {"flags": {"build": True, "ledger_fields": True}}
    D._MODEL_CALL = None
    _CAL.update(fail=False, calls=0)
    _CLOCK["now"] = datetime(2026, 10, 26, 8, 0)
    return d


def _block() -> str:
    return D.render_block(D.current(_PERSONA))


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


@check("a calendar that fails on its first read is flagged — the day is not described as free")
def _():
    _fresh("first_fail")
    _CAL["fail"] = True
    D.refresh_snapshot(_PERSONA)
    text = _block()
    assert _NOTICE in text and "08:00" in text, text
    assert "do not describe the day as free" in text, text
    assert "has not been read yet" not in text, text


@check("a failure after a good read flags the events as from the last good read, not confirmed")
def _():
    _fresh("fail_after_good")
    D.refresh_snapshot(_PERSONA)
    _CLOCK["now"] += timedelta(minutes=3)
    _CAL["fail"] = True
    D.refresh_snapshot(_PERSONA)
    text = _block()
    assert _NOTICE in text and "at 08:03" in text, text
    assert "last good read at 08:00" in text and "do not state them as confirmed" in text, text
    # Still shown — flagged, not hidden. Since 2026-10-30 a later event is in the whole-day read,
    # not the per-turn block (synth_now_next plan § 3.1), and the read carries the same notice.
    full = D.render_full(D.current(_PERSONA))
    assert "Evening lecture" in full and "last good read at 08:00" in full, full


@check("the next successful read clears the notice")
def _():
    _fresh("recovery")
    D.refresh_snapshot(_PERSONA)
    _CLOCK["now"] += timedelta(minutes=3)
    _CAL["fail"] = True
    D.refresh_snapshot(_PERSONA)
    assert _NOTICE in _block()
    _CLOCK["now"] += timedelta(minutes=6)
    _CAL["fail"] = False
    D.refresh_snapshot(_PERSONA)
    text = _block()
    assert _NOTICE not in text, text
    assert not (D._load_state(_PERSONA).get("snapshot") or {}).get("error")


@check("no notice when the last read succeeded")
def _():
    _fresh("ok")
    D.refresh_snapshot(_PERSONA)
    text = _block()
    assert _NOTICE not in text, text
    full = D.render_full(D.current(_PERSONA))
    assert _NOTICE not in full and "Evening lecture" in full, full


def main() -> int:
    passed = sum(1 for _, ok, _ in _results if ok)
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if detail else ""))
    print(f"\n{passed} passed, {len(_results) - passed} failed, {len(_results)} total")
    return 0 if passed == len(_results) else 1


if __name__ == "__main__":
    sys.exit(main())
