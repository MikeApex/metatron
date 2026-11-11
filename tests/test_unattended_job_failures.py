"""
tests/test_unattended_job_failures.py — a broken connection is not a quiet day.

Review 2026-11-05, finding 6. When the Google app password was revoked, the three unattended
calendar jobs turned `{"error": ...}` from the calendar read into an empty list and returned
their clean-day strings — "no travel found in the next 24h", "no calendar duplicates found",
"no unreferenced passed events" — and mail intake simply went quiet. A cancelled 06:45 flight
would have produced no push, and nothing anywhere said why.

1. Each calendar job, given the error dict, returns a FAILED outcome, not its clean-day string.
2. Two runs the same day write exactly ONE CALENDAR_UNREADABLE event per job, with no URL in it.
3. "No calendar connected" is still not an error — no event, the ordinary string.
4. Intake: failing sweeps put a channel-failure count in context_block; a good sweep clears it.

No network, no model: `_query_events` is replaced in each job module, the intake channel is a
synthetic adapter, and every persona path is a temp dir.

Usage:
    python3 tests/test_unattended_job_failures.py
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.caldav as caldav                       # noqa: E402
import tools.calendar_audit as audit                # noqa: E402
import tools.calendar_reconcile as reconcile        # noqa: E402
import tools.intake as intake                       # noqa: E402
import tools.logger as qlog                         # noqa: E402
import tools.travel_watch as travel                 # noqa: E402

_results: list[tuple[str, bool, str]] = []

ERROR = {"error": ("CalDAV request failed: 401 Client Error: Unauthorized for url: "
                   "https://apidata.googleusercontent.com/caldav/v2/someone%40gmail.com/events")}
NOT_CONNECTED = {"events": [], "connected": False}

# (job module, entry point, source_agent, the clean-day string it used to return)
JOBS = [
    (travel, "travel_check", "travel_watch", "no travel found in the next 24h"),
    (audit, "audit_calendar_duplicates", "calendar_audit", "no calendar duplicates found"),
    (reconcile, "reconcile_check", "calendar_reconcile", "no unreferenced passed events"),
]


def check(name: str):
    def wrap(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except AssertionError as e:
            _results.append((name, False, f"assertion: {e}"))
        except Exception as e:
            _results.append((name, False, f"{type(e).__name__}: {e}"))
        return fn
    return wrap


class _sandbox:
    """Every persona path the jobs and the event writer touch, pointed at one temp dir."""

    def __enter__(self):
        self.root = Path(tempfile.mkdtemp(prefix="job_failures_"))
        here = lambda persona=None: self.root  # noqa: E731
        self._patches = [
            mock.patch.object(caldav, "persona_data_dir", here, create=True),
            mock.patch.object(qlog, "persona_data_dir", here),
            mock.patch.object(travel, "persona_data_dir", here),
            mock.patch.object(audit, "persona_data_dir", here),
            mock.patch.object(reconcile, "persona_data_dir", here),
            mock.patch.object(travel, "resolve_persona", lambda p=None: "probe"),
            mock.patch.object(audit, "resolve_persona", lambda p=None: "probe"),
            mock.patch.object(reconcile, "resolve_persona", lambda p=None: "probe"),
            mock.patch.object(travel, "_usual_lines", lambda p: []),
            mock.patch.object(reconcile, "_config", lambda: dict(reconcile._DEFAULTS)),
        ]
        for p in self._patches:
            p.start()
        return self.root

    def __exit__(self, *exc):
        for p in reversed(self._patches):
            p.stop()
        shutil.rmtree(self.root, ignore_errors=True)


def _events(root: Path, kind: str = "CALENDAR_UNREADABLE") -> list[dict]:
    path = root / "logs" / "quality_events.json"
    if not path.exists():
        return []
    rows = [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]
    return [r for r in rows if r.get("event_type") == kind]


for _mod, _fn, _agent, _clean in JOBS:
    @check(f"{_agent}: an unreadable calendar is a FAILED run, not '{_clean}'")
    def _(mod=_mod, fn=_fn, clean=_clean):
        with _sandbox(), mock.patch.object(mod, "_query_events", lambda *a, **k: dict(ERROR)):
            out = getattr(mod, fn)()
        assert isinstance(out, str), out
        assert out != clean and "FAILED" in out, out

    @check(f"{_agent}: two runs the same day write exactly one event, with no URL in it")
    def _(mod=_mod, fn=_fn, agent=_agent):
        with _sandbox() as root, \
                mock.patch.object(mod, "_query_events", lambda *a, **k: dict(ERROR)):
            getattr(mod, fn)()
            getattr(mod, fn)()
            events = [e for e in _events(root) if e.get("source_agent") == agent]
        assert len(events) == 1, events
        assert "https://" not in events[0]["detail"], events[0]["detail"]
        assert "not a quiet day" in events[0]["detail"], events[0]["detail"]

    @check(f"{_agent}: no calendar connected is still not an error")
    def _(mod=_mod, fn=_fn, clean=_clean):
        with _sandbox() as root, \
                mock.patch.object(mod, "_query_events", lambda *a, **k: dict(NOT_CONNECTED)):
            out = getattr(mod, fn)()
            events = _events(root)
        assert out == clean, out
        assert not events, events


@check("the three jobs each file their own event on the same day")
def _():
    with _sandbox() as root:
        for mod, fn, _agent, _clean in JOBS:
            with mock.patch.object(mod, "_query_events", lambda *a, **k: dict(ERROR)):
                getattr(mod, fn)()
        agents = sorted(e["source_agent"] for e in _events(root))
    assert agents == ["calendar_audit", "calendar_reconcile", "travel_watch"], agents


# --- intake -----------------------------------------------------------------------------

_INTAKE_CFG = {"enabled": True, "channels": {"email": True},
               "categories": {"unclear": {"disposition": "surface", "domain": None}},
               "digest": {}, "rules": [], "ledger": {"enabled": False},
               "limits": {"max_per_sweep": 50, "seen_retention_days": 90}}


class _intake_sandbox:
    def __enter__(self):
        self.root = Path(tempfile.mkdtemp(prefix="intake_health_"))
        self._patches = [
            mock.patch.object(intake, "persona_data_dir", lambda p=None: self.root),
            mock.patch.object(intake, "load_config", lambda p=None: _INTAKE_CFG),
            mock.patch.object(intake, "_in_quiet_hours", lambda p=None: False),
            mock.patch.object(intake, "_load_adapters", lambda cfg: None),
            mock.patch.object(intake, "_ADAPTERS", {}),
        ]
        for p in self._patches:
            p.start()
        return self.root

    def __exit__(self, *exc):
        for p in reversed(self._patches):
            p.stop()
        shutil.rmtree(self.root, ignore_errors=True)


def _broken(limit, skip=None):
    raise RuntimeError("b'[AUTHENTICATIONFAILED] Invalid credentials (Failure)'")


@check("intake: failing sweeps surface a channel-failure count in context_block")
def _():
    with _intake_sandbox():
        intake._ADAPTERS["email"] = _broken
        intake.sweep()
        intake.sweep()
        block = intake.context_block()
    assert "email: 2 sweep(s) in a row failed" in block, block
    assert "AUTHENTICATIONFAILED" not in block, "error text leaked into the head layer's context"


@check("intake: one good sweep clears the failure line")
def _():
    with _intake_sandbox():
        intake._ADAPTERS["email"] = _broken
        intake.sweep()
        intake._ADAPTERS["email"] = lambda limit, skip=None: []
        intake.sweep()
        block = intake.context_block()
    assert "not being read" not in block, block


@check("intake: a failing channel that is then switched off stops being reported")
def _():
    with _intake_sandbox():
        intake._ADAPTERS["email"] = _broken
        intake.sweep()
        with mock.patch.dict(_INTAKE_CFG["channels"], {"email": False}):
            intake.sweep()
            block = intake.context_block()
    assert "not being read" not in block, block


@check("intake: a healthy channel never produces the line")
def _():
    with _intake_sandbox():
        intake._ADAPTERS["email"] = lambda limit, skip=None: []
        intake.sweep()
        block = intake.context_block()
    assert "not being read" not in block, block


# ---------------------------------------------------------------------------

def main() -> int:
    passed = sum(1 for _, ok, _ in _results if ok)
    failed = len(_results) - passed
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if not ok:
            print(f"        {detail}")
    print(f"\n{passed} passed, {failed} failed, {len(_results)} total")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
