"""
tests/test_not_connected_integrations.py — a user with no calendar connected reads as "nothing
to do", not as a failure (archive/plans/multi_user_accounts_plan_2026-10-26.md § 4.8, Stage 1.13).

A new user (the second user, first: Iva) starts with no calendar: her caldav.yaml is the template,
`enabled: false`, or absent. Before this, `_query_events` returned an error for that and the day
planner stored it as a failed snapshot with no `fetched_at` — so every tick read the snapshot as
stale and fetched again, and the plan carried a calendar error she could not act on. Pinned here:

  1. `_query_events` returns {"events": [], "connected": False} for an absent config and for
     `enabled: false`; a CONFIGURED calendar that fails is still an error (Mike's path, unchanged).
  2. `read_calendar` says "not connected" — neither an error nor a fake empty day; the write and
     invite paths still fail, because a write to a calendar the user lacks did not happen.
  3. Two `refresh_tick`s store one successful, empty snapshot (`discovery: "not_connected"`, no
     `failed_at`, `ok: true`) and do not re-fetch inside the freshness window — then do after it.
  4. The reshuffle model is called ZERO times on an empty day and its daily counter is untouched;
     with one candidate task it still starts (the model stub is called once).

EVERY LIVE METER IS STUBBED (the standing rule): sockets are blocked outright (DNS and connect —
an attempt is counted and raises), the model (`core.orchestrator.run_session`, reached through
the planner's real `_call_model` path) is a counter, the spend guard is a no-op, Google Routes is a
counter. Persona paths point at a temporary directory per check — no tracked persona is touched.

    python3 tests/test_not_connected_integrations.py        # standalone
    python -m pytest -q tests/test_not_connected_integrations.py
"""
from __future__ import annotations

import json
import socket
import sys
import tempfile
import threading
from contextlib import contextmanager
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

_ROOT = Path(__file__).parent.parent
_TMP = Path(tempfile.mkdtemp(prefix="not_connected_"))
_PERSONA = "zz_not_connected_test"          # exists nowhere; every path it reaches is patched
_MONDAY_8AM = datetime(2026, 10, 26, 8, 0)
_SHAPE = """wake: "07:00"
bed: "23:00"
work_days: [mon, tue, wed, thu, fri]
work_start: "09:00"
work_end: "17:30"
"""
_CALLS: dict = {}


# --- the sandbox -----------------------------------------------------------------------------

class _Patches:
    """setattr with restore — so the suite leaves nothing behind when pytest runs it beside the
    day-plan suites in one process."""

    def __init__(self):
        self._saved: list[tuple[object, str, object]] = []

    def set(self, obj, name, value):
        self._saved.append((obj, name, getattr(obj, name)))
        setattr(obj, name, value)

    def restore(self):
        for obj, name, value in reversed(self._saved):
            setattr(obj, name, value)
        self._saved.clear()


def _blocked(kind):
    def fn(*args, **kwargs):
        _CALLS["network"].append(kind)
        raise OSError(f"network blocked in test ({kind})")
    return fn


def _run_session(*args, **kwargs):
    _CALLS["model"] += 1
    return json.dumps({"placements": [], "drop": [], "note": "stub"})


def _route(*args, **kwargs):
    _CALLS["routes"] += 1
    return {"journeys": [{"duration_minutes": 25}]}


def _join_planner_threads():
    for th in threading.enumerate():
        if th.name.startswith("day_plan_"):
            th.join(5)


@contextmanager
def _sandbox(name: str, caldav_yaml: str | None = None):
    """A throwaway persona under a temp directory, every meter stubbed. `caldav_yaml` None means
    no caldav.yaml at all."""
    import importlib

    import core.orchestrator as ORC
    import core.spend_guard as SG

    # The day-plan suites are standalone scripts that run their checks at IMPORT and replace
    # `tools.caldav._query_events` with a fixture stub for good. Under one pytest process their
    # collection precedes this suite, so the function under test here would be their stub. A
    # reload restores the real module; their checks have already run by then.
    qe = CAL._query_events
    if getattr(getattr(qe, "__code__", None), "co_filename", "") != CAL.__file__:
        importlib.reload(CAL)

    d = _TMP / name
    cfg_dir = d / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    if caldav_yaml is not None:
        (cfg_dir / "caldav.yaml").write_text(caldav_yaml)
    (d / "day_shape.yaml").write_text(_SHAPE)
    (cfg_dir / "goals.yaml").write_text("quarterly: []\n")
    _CALLS.update(network=[], model=0, routes=0, fetch=0)

    p = _Patches()
    data_fn = lambda persona=None, _d=d: _d          # noqa: E731
    cfg_fn = lambda persona=None, _c=cfg_dir: _c     # noqa: E731
    # Every module that bound the persona path functions by name, plus core.persona itself for
    # the lazy `from core.persona import …` inside functions.
    real_data, real_cfg = P.persona_data_dir, P.persona_config_dir
    for mod in list(sys.modules.values()):
        modname = getattr(mod, "__name__", "") or ""
        if not (modname.startswith("tools.") or modname.startswith("core.")):
            continue
        if getattr(mod, "persona_data_dir", None) is real_data:
            p.set(mod, "persona_data_dir", data_fn)
        if getattr(mod, "persona_config_dir", None) is real_cfg:
            p.set(mod, "persona_config_dir", cfg_fn)
    # …and the modules the day-plan suites have already pointed at THEIR temp dirs, which the
    # identity test above no longer recognises when pytest runs everything in one process.
    for mod in (O, D, DS, L):
        p.set(mod, "persona_data_dir", data_fn)
    p.set(CAL, "persona_config_dir", cfg_fn)
    p.set(DS, "persona_config_dir", lambda persona=None, _d=d: _d)   # the shape lives in data
    p.set(G, "_goals_path", lambda _c=cfg_dir: _c / "goals.yaml")
    p.set(O, "_now", lambda: _CALLS["now"])
    p.set(A, "_get_timezone", lambda: "Europe/London")
    p.set(L, "load_zones", lambda persona=None: [])
    p.set(L, "current_zone", lambda persona=None: {})
    p.set(R, "get_travel_time", _route)
    p.set(socket, "getaddrinfo", _blocked("dns"))
    p.set(socket, "create_connection", _blocked("connect"))
    p.set(socket.socket, "connect", _blocked("connect"))
    p.set(ORC, "run_session", _run_session)
    p.set(SG, "check_before_session", lambda: None)
    p.set(D, "_MODEL_CALL", None)     # the real _call_model path, so run_session is what counts
    real_fetch = D._fetch

    def counting_fetch(day, persona):
        _CALLS["fetch"] += 1
        return real_fetch(day, persona)
    p.set(D, "_fetch", counting_fetch)
    CAL._discovery_cache.clear()
    _CALLS["now"] = _MONDAY_8AM
    C._OVERRIDE = {"flags": {"build": True, "ledger_fields": True, "reshuffle_model": True}}
    try:
        with P.persona_scope(_PERSONA):
            yield d
    finally:
        _join_planner_threads()
        C._OVERRIDE = None
        p.restore()


def _template() -> str:
    """The file scripts/new_persona.sh copies for a new user — `enabled: false`."""
    text = (_ROOT / "config" / "templates" / "caldav.yaml").read_text()
    assert "enabled: false" in text, "the template no longer ships disabled — re-read § 4.8"
    return text


_CONFIGURED = """enabled: true
calendar_url: "https://caldav.invalid.example/calendar/dav/someone/events"
auth:
  username: "someone@example.invalid"
  password: "not-a-real-password"
timezone: "Europe/London"
"""


def _log_rows(d: Path) -> list[dict]:
    path = d / "day_plan" / "log.jsonl"
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def _tick() -> str:
    out = D.refresh_tick()
    _join_planner_threads()
    return out


# --- 1. _query_events ------------------------------------------------------------------------

def test_query_events_absent_config_is_not_connected():
    with _sandbox("absent"):
        for mode in ("own", "all"):
            raw = CAL._query_events("2026-10-26", "2026-10-28", calendars=mode)
            assert raw == {"events": [], "connected": False}, (mode, raw)
        assert _CALLS["network"] == [], _CALLS["network"]


def test_query_events_disabled_template_is_not_connected():
    with _sandbox("disabled", caldav_yaml=_template()):
        for mode in ("own", "all"):
            raw = CAL._query_events("2026-10-26", "2026-10-28", calendars=mode)
            assert raw == {"events": [], "connected": False}, (mode, raw)
        assert _CALLS["network"] == [], _CALLS["network"]


def test_configured_calendar_that_fails_is_still_an_error():
    # Mike's path: a real, configured calendar that cannot be reached. The socket guard is the
    # failure — the request is genuinely attempted and refused, in both read modes.
    with _sandbox("configured_failing", caldav_yaml=_CONFIGURED):
        for mode in ("own", "all"):
            raw = CAL._query_events("2026-10-26", "2026-10-28", calendars=mode)
            assert "error" in raw and "connected" not in raw, (mode, raw)
            assert raw["error"].startswith("CalDAV request failed"), (mode, raw)
        assert _CALLS["network"], "the configured path never reached the network guard"
        assert "error" in CAL.read_calendar("2026-10-26", "2026-10-28")


def test_configured_without_url_is_still_an_error():
    # `enabled: true` with no calendar_url is a broken configuration, not an absent one.
    with _sandbox("configured_no_url", caldav_yaml="enabled: true\ncalendar_url: \"\"\n"):
        raw = CAL._query_events("2026-10-26", "2026-10-28")
        assert "error" in raw and "connected" not in raw, raw


# --- 2. read_calendar and the write paths ----------------------------------------------------

def test_read_calendar_says_not_connected_not_an_empty_day():
    with _sandbox("read_calendar", caldav_yaml=_template()):
        out = CAL.read_calendar("2026-10-26", "2026-10-28")
        assert "error" not in out, out
        assert out["connected"] is False, out
        # No event list and no count: `count: 0, events: []` reads as a free day.
        assert "events" not in out and "count" not in out, out
        assert "NOT an empty day" in out["calendar_note"], out


def test_write_and_invite_paths_still_fail():
    with _sandbox("writes", caldav_yaml=_template()):
        assert "error" in CAL.write_calendar_event("Dentist", "2026-10-26T10:00", "2026-10-26T11:00")
        assert "error" in CAL.update_calendar_event("some-uid", title="Dentist")
        assert "error" in CAL.delete_calendar_event("some-uid")
        inv = CAL.find_event_for_invite(title="Dentist", date="2026-10-26")
        assert "error" in inv and "No calendar is connected" in inv["error"], inv
        assert _CALLS["network"] == [], _CALLS["network"]


def test_conflict_check_reads_as_nothing_on_the_calendar():
    # One of the consumers that branch on "error" and otherwise iterate `events`.
    from tools.scheduling import check_calendar_conflicts
    with _sandbox("conflicts"):
        out = check_calendar_conflicts("2026-10-26T10:00", "2026-10-26T11:00", title="Dentist")
        assert "check_error" not in out, out


# --- 3. the day planner's snapshot -----------------------------------------------------------

def test_two_ticks_store_one_successful_empty_snapshot():
    with _sandbox("ticks", caldav_yaml=_template()) as d:
        _tick()
        _CALLS["now"] = _MONDAY_8AM + timedelta(minutes=5)      # the tick cadence
        _tick()
        snap = D._load_state(_PERSONA)["snapshot"]
        assert snap.get("discovery") == "not_connected", snap
        assert snap.get("events") == [] and snap.get("fetched_at"), snap
        assert "failed_at" not in snap and "error" not in snap, snap
        assert _CALLS["fetch"] == 1, f"re-fetched inside the freshness window: {_CALLS['fetch']}"
        rows = [r for r in _log_rows(d) if r["event"] == "snapshot"]
        assert len(rows) == 1 and rows[0]["ok"] is True, rows
        # Outside the window it is fetched again — the normal success cadence, not never.
        limit = float(D._limit("snapshot_max_age_minutes") or 10)
        _CALLS["now"] = _MONDAY_8AM + timedelta(minutes=limit + 1)
        _tick()
        assert _CALLS["fetch"] == 2, _CALLS["fetch"]
        assert _CALLS["network"] == [] and _CALLS["routes"] == 0, _CALLS


def test_current_and_the_plan_build_on_a_not_connected_snapshot():
    with _sandbox("current", caldav_yaml=_template()):
        D.refresh_snapshot(_PERSONA)
        plan = D.current(_PERSONA, reason="test")
        _join_planner_threads()
        assert plan is not None, "no plan built from the day shape alone"
        assert plan["failures"] == [], plan["failures"]
        assert not [b for b in plan["blocks"] if b["kind"] in ("event", "travel")], plan["blocks"]
        assert plan.get("snapshot_at"), plan.get("snapshot_at")
        assert D.render_block(plan) is not None
        # No background refresh was started: the snapshot is fresh.
        assert _CALLS["fetch"] == 1, _CALLS["fetch"]


# --- 4. the reshuffle model call -------------------------------------------------------------

def test_empty_day_makes_no_reshuffle_model_call():
    with _sandbox("reshuffle_empty", caldav_yaml=_template()) as d:
        _tick()
        _CALLS["now"] = _MONDAY_8AM + timedelta(minutes=5)
        _tick()
        assert _CALLS["model"] == 0, f"model called {_CALLS['model']} time(s) on an empty day"
        st = D._load_state(_PERSONA)
        rs = st.get("reshuffle") or {}
        assert not rs.get("inflight") and not rs.get("pending"), rs
        used = ((st.get("counters") or {}).get("2026-10-26") or {}).get("reshuffles", 0)
        assert used == 0, f"a daily reshuffle slot was consumed: {used}"
        rows = [r for r in _log_rows(d) if r["event"] == "reshuffle"]
        assert rows and all(r["outcome"] == "skipped_empty" for r in rows), rows
        assert not D.pending_heads_up(_PERSONA)


def test_a_day_with_a_task_still_reshuffles():
    with _sandbox("reshuffle_task", caldav_yaml=_template()) as d:
        O.open_task("Buy a birthday card", kind="deadline", due="2026-10-26",
                    stakes="missable", minutes=20)
        _tick()
        assert _CALLS["model"] == 1, f"model called {_CALLS['model']} time(s), expected 1"
        st = D._load_state(_PERSONA)
        used = ((st.get("counters") or {}).get("2026-10-26") or {}).get("reshuffles", 0)
        assert used == 1, used
        rows = [r for r in _log_rows(d) if r["event"] == "reshuffle"]
        assert rows and rows[-1]["outcome"] != "skipped_empty", rows


# --- standalone ------------------------------------------------------------------------------

def main() -> int:
    tests = [(n, f) for n, f in list(globals().items())        # definition order
             if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
        except Exception as exc:  # noqa: BLE001
            import traceback
            failed += 1
            print(f"  FAIL  {name}\n        {type(exc).__name__}: {exc}\n"
                  + "".join(traceback.format_exc().splitlines(True)[-4:]))
    print(f"\n{len(tests) - failed} passed, {failed} failed, {len(tests)} total")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
