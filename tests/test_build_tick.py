"""
tests/test_build_tick.py — the REPAIR counter, and the check that it stays wired.

Plan section 12, Tick row: three corrections against a registered capability
file one repair ticket; `scheduler-functions-resolve` fails on a dangling
`_DEFAULT_JOBS` path and passes on the tree (finding 4).

THE TWO HALVES ARE ONE SUITE ON PURPOSE. The REPAIR counter is the only thing
left running on the VM, and the way it dies is not a crash — `fire_function()`
resolves its dotted path inside a try, so a rename just stops it happening,
silently, every thirty minutes. The counter's test and the test that the
counter is still REACHABLE belong together, because the second is the one that
catches the failure the first cannot.

Usage:
    python3 tests/test_build_tick.py
"""

import json
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from core.build import registry as R                     # noqa: E402
from core.build import tick as T                         # noqa: E402
from core.build import tickets as TK                     # noqa: E402
from tests.support import build_fixtures as F            # noqa: E402
from tests.support.runner import Suite, hit              # noqa: E402

import check_scheduler_functions as CSF                   # noqa: E402

suite = Suite("build tick")
check = suite.check

_TMP = Path(tempfile.mkdtemp(prefix="build-tick-"))
REGISTRY = _TMP / "registry.yaml"


def _persona_dir() -> Path:
    directory = _TMP / "personas" / F.PERSONA
    (directory / "logs").mkdir(parents=True, exist_ok=True)
    (directory / "build").mkdir(parents=True, exist_ok=True)
    return directory


# Redirect BOTH homes at the temp tree. `persona_data_dir` is rebound in two
# places deliberately: tickets.py imported the NAME at module load, so patching
# core.persona alone would leave the ticket file resolving to a real persona
# tree — which is the one failure a test suite must never have, since the write
# would look like a real REPAIR ticket.
import core.persona as _persona                                   # noqa: E402

_persona.persona_data_dir = lambda persona=None: _persona_dir()   # type: ignore
TK.persona_data_dir = lambda persona=None: _persona_dir()         # type: ignore
R.REGISTRY_PATH = REGISTRY                                        # type: ignore


def _registry(status: str = "landed") -> None:
    R.write({"schema": "build_registry/1",
             "capabilities": [F.registry_row("home_care", status)]}, REGISTRY)


def _events(count: int, detail: str = "watered the wrong plant",
            agent: str = "home_care", days_ago: int = 1) -> None:
    stamp = (datetime.now(timezone.utc).replace(tzinfo=None)
             - timedelta(days=days_ago)).isoformat() + "Z"
    path = _persona_dir() / "logs" / "quality_events.json"
    path.write_text("\n".join(
        json.dumps({"timestamp": stamp, "event_type": "USER_CORRECTION",
                    "source_agent": agent, "detail": detail})
        for _ in range(count)), encoding="utf-8")


def _reset() -> None:
    shutil.rmtree(_TMP / "personas", ignore_errors=True)
    _persona_dir()
    REGISTRY.unlink(missing_ok=True)


def _signature(event: dict) -> str:
    """Stand-in for sync_dev_backlog.signature — collapses on the detail."""
    return str(event.get("detail", ""))[:40].lower()


T._signature_fn = lambda: _signature                              # type: ignore


# ---------------------------------------------------------------------------
# The REPAIR counter
# ---------------------------------------------------------------------------

@check("THREE corrections against a registered capability file ONE repair ticket")
def _():
    _reset()
    _registry()
    _events(3)
    filed = T.repair_scan(F.PERSONA)
    assert len(filed) == 1, filed
    assert "home_care" in filed[0], filed

    rows = TK.read_rows(F.PERSONA)
    assert len(rows) == 1, rows
    assert rows[0]["mode"] == "repair", rows[0]
    assert rows[0]["capability_hint"] == "home_care", rows[0]


@check("TWO corrections file nothing — one is an accident, two a coincidence")
def _():
    _reset()
    _registry()
    _events(2)
    assert T.repair_scan(F.PERSONA) == []
    assert TK.read_rows(F.PERSONA) == []


@check("a FOURTH correction does not file a second ticket")
def _():
    _reset()
    _registry()
    _events(3)
    T.repair_scan(F.PERSONA)
    _events(4)
    assert T.repair_scan(F.PERSONA) == [], (
        "the count lives in `trigger`, which is NOT fingerprinted — putting it "
        "in the gap would mint a new fingerprint on every correction after the "
        "third and fill max_proposed with one recurring fault")
    assert len(TK.read_rows(F.PERSONA)) == 1


@check("corrections against an UNREGISTERED agent file nothing")
def _():
    _reset()
    _registry()
    _events(3, agent="logistics")
    assert T.repair_scan(F.PERSONA) == [], (
        "only a capability Build made can be repaired by Build — a hand-written "
        "specialist answering wrongly is ordinary development")


@check("corrections older than the window file nothing")
def _():
    _reset()
    _registry()
    _events(3, days_ago=T.REPAIR_WINDOW_DAYS + 2)
    assert T.repair_scan(F.PERSONA) == [], (
        "a fault fixed a month ago must not file a ticket about itself today")


@check("a comma-joined source_agent is split — a turn can dispatch several")
def _():
    _reset()
    _registry()
    _events(3, agent="logistics, home_care")
    assert len(T.repair_scan(F.PERSONA)) == 1, (
        "blaming the first agent alphabetically would be a guess; the "
        "attribution writes them all and the scan reads them all")


@check("the tick returns a plain string and never a notify dict")
def _():
    _reset()
    _registry()
    _events(3)
    result = T.build_tick(F.PERSONA)
    assert isinstance(result, str), type(result)
    assert result.startswith("build_tick:"), result
    assert "notify" not in result.lower(), (
        "nothing in Build reaches the user unreviewed, and a tick that could "
        "notify would be the first thing to do so")


@check("with nothing registered the tick stops before reading anything")
def _():
    _reset()
    R.write({"schema": "build_registry/1", "capabilities": []}, REGISTRY)
    result = T.build_tick(F.PERSONA)
    assert "nothing registered" in result, result


@check("a STAGED row is not repairable — it is not deployed")
def _():
    _reset()
    _registry(status="staged")
    _events(3)
    assert T.repair_scan(F.PERSONA) == [], (
        "a staged row has not reached the VM, so nothing it names is running "
        "and nothing it names can have answered wrongly")


# ---------------------------------------------------------------------------
# scheduler-functions-resolve
# ---------------------------------------------------------------------------

@check("resolve() accepts a live dotted path")
def _():
    assert CSF.resolve("core.build.tick.build_tick") == ""


@check("resolve() FAILS on a dangling module — the fire_function shape")
def _():
    reason = CSF.resolve("core.build.runner_that_went_away.tick")
    assert "cannot import" in reason, reason


@check("resolve() FAILS on a live module with no such attribute")
def _():
    reason = CSF.resolve("core.build.tick.tick_that_was_renamed")
    assert "has no attribute" in reason, reason


@check("resolve() FAILS on a module-level name that is not callable")
def _():
    reason = CSF.resolve("core.build.tick.REPAIR_AT")
    assert "not callable" in reason, reason


@check("the check IMPORTS but never CALLS — a sweep with side effects is not a sweep")
def _():
    source = (ROOT / "scripts" / "check_scheduler_functions.py").read_text()
    assert "fn()" not in source, (
        "several of these jobs write files; calling them on every sweep would "
        "make the sweep a maintenance run")


def _cleanup() -> None:
    shutil.rmtree(_TMP, ignore_errors=True)


try:
    code = suite.report()
finally:
    _cleanup()
sys.exit(code)
