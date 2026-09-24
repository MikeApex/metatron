"""
tests/test_build_registry.py — the tracked state, and the dedupe it protects.

Plan section 12, Registry row: a `landed` row within 14 days refuses a
same-fingerprint ticket on the VM; `abandoned` within 72 h likewise; dispatch
counts exclude ticks and the landing day (unchanged).

THE LAST CLAUSE IS WHY THE COUNTING CODE WAS SALVAGED RATHER THAN REWRITTEN.
Both exclusions were bought by a real wrong number on the board: a capability
that landed at 16:00 read `actual 0.0 over 1d`, because the only trace file for
that day held exactly one record — Build's own tick.

Usage:
    python3 tests/test_build_registry.py
"""

import json
import shutil
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.build import registry as R                     # noqa: E402
from core.build import tickets as TK                     # noqa: E402
from tests.support import build_fixtures as F            # noqa: E402
from tests.support.runner import Suite                   # noqa: E402

suite = Suite("build registry")
check = suite.check

_TMP = Path(tempfile.mkdtemp(prefix="build-registry-"))
REGISTRY = _TMP / "registry.yaml"


def _persona_dir() -> Path:
    directory = _TMP / "personas" / F.PERSONA
    (directory / "traces").mkdir(parents=True, exist_ok=True)
    (directory / "build").mkdir(parents=True, exist_ok=True)
    return directory


import core.persona as _persona                          # noqa: E402

_persona.persona_data_dir = lambda persona=None: _persona_dir()   # type: ignore
TK.persona_data_dir = lambda persona=None: _persona_dir()         # type: ignore
R.REGISTRY_PATH = REGISTRY                                        # type: ignore


def _reset() -> None:
    shutil.rmtree(_TMP / "personas", ignore_errors=True)
    _persona_dir()
    REGISTRY.unlink(missing_ok=True)


def _row(status: str, days_ago: int = 0, name: str = "home_care",
         ticket: str = F.JOB_ID) -> dict:
    row = F.registry_row(name, status)
    row["ticket"] = ticket
    row["job_id"] = ticket
    row["at"] = (date.today() - timedelta(days=days_ago)).isoformat()
    return row


def _write(*rows: dict) -> None:
    R.write({"schema": "build_registry/1", "capabilities": list(rows)}, REGISTRY)


def _ticket(fp: str = "", ticket: str = F.JOB_ID) -> None:
    TK.append_row({"job_id": ticket, "mode": "construct", "gap": "the plants",
                   "fingerprint": fp or TK.fingerprint("construct", "the plants")},
                  F.PERSONA)


def _trace(day: date, records: list[dict]) -> None:
    path = _persona_dir() / "traces" / f"{day.isoformat()}.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")


def _turn(agent: str = "home_care") -> dict:
    return {"pipeline": [{"agent": "coordinator",
                          "subagents": [{"agent": agent}]}]}


def _tick_record() -> dict:
    return {"pipeline": [{"agent": "build"}]}


# ---------------------------------------------------------------------------
# The two statuses
# ---------------------------------------------------------------------------

@check("a new row is written `staged` and asserts no wiring")
def _():
    _reset()
    row = R.new_row("home_care", "agent", F.JOB_ID, F.JOB_ID, F.PERSONA,
                    "deferred", 4000)
    assert row["status"] == "staged", row
    assert row["run"]["dispatches_expected_per_day"] is None, (
        "None reads as 'not counted yet'; an ABSENT key would read as 'this row "
        "predates the run line', which is a different and false statement")


@check("mark_landed flips staged -> landed and nothing else does")
def _():
    _reset()
    _write(_row("staged"))
    assert R.mark_landed("home_care", REGISTRY)["status"] == "landed"
    assert R.capability_names(REGISTRY) == {"home_care"}


@check("an abandoned row cannot be landed")
def _():
    _reset()
    _write(_row("abandoned"))
    try:
        R.mark_landed("home_care", REGISTRY)
    except R.RegistryError as exc:
        assert "only a staged row lands" in str(exc), exc
        return
    raise AssertionError("an abandoned row was landed")


@check("capabilities() returns LANDED rows only — a staged row is not live")
def _():
    _reset()
    _write(_row("staged"), _row("landed", name="garden_care", ticket="BLD-0924-02"))
    assert set(R.capabilities(REGISTRY)) == {"garden_care"}


@check("upsert REPLACES rather than appends — this is state, not a log")
def _():
    _reset()
    _write(_row("staged"))
    R.upsert(_row("landed"), REGISTRY)
    assert len(R.rows(REGISTRY)) == 1, (
        "a second row for one capability would appear in Mike's diff as a "
        "duplicate he has to reason about")


# ---------------------------------------------------------------------------
# Dedupe — what the VM reads
# ---------------------------------------------------------------------------

@check("a `landed` row within 14 days REFUSES a same-fingerprint ticket")
def _():
    _reset()
    _write(_row("landed", days_ago=3))
    _ticket()
    dupe = TK.duplicate_of(TK.fingerprint("construct", "the plants"), F.PERSONA)
    assert dupe is not None, "a landed capability answering wrongly is a REPAIR"
    assert "landed 3d ago" in dupe[1], dupe


@check("a `landed` row OUTSIDE 14 days admits the ticket")
def _():
    _reset()
    _write(_row("landed", days_ago=R.DEFAULT_WINDOW_DAYS + 20))
    _ticket()
    assert TK.duplicate_of(TK.fingerprint("construct", "the plants"),
                           F.PERSONA) is None


@check("`abandoned` within 72h refuses; outside it admits")
def _():
    _reset()
    _write(_row("abandoned", days_ago=1))
    _ticket()
    fp = TK.fingerprint("construct", "the plants")
    assert TK.duplicate_of(fp, F.PERSONA) is not None

    _write(_row("abandoned", days_ago=5))
    assert TK.duplicate_of(fp, F.PERSONA) is None, (
        "'Mike closed this without building it' is a judgement that can change; "
        "three days is long enough that the change is a decision, not a retry")


@check("a ticket with NO registry row is open, and refuses its own fingerprint")
def _():
    _reset()
    _write()
    _ticket()
    dupe = TK.duplicate_of(TK.fingerprint("construct", "the plants"), F.PERSONA)
    assert dupe is not None and "not yet decided" in dupe[1], dupe


@check("open_tickets is derived from the registry, with no second status field")
def _():
    _reset()
    _ticket()
    assert set(TK.open_tickets(F.PERSONA)) == {F.JOB_ID}
    _write(_row("landed"))
    assert TK.open_tickets(F.PERSONA) == {}, (
        "there is no second place a ticket's state could be written, so there "
        "is no second place it could be written wrongly")


@check("decided_awaiting_deploy names finding 7's lag rather than hiding it")
def _():
    _reset()
    _write(_row("abandoned"))
    assert TK.decided_awaiting_deploy([F.JOB_ID]) == [F.JOB_ID]
    assert TK.decided_awaiting_deploy(["BLD-0924-99"]) == []


# ---------------------------------------------------------------------------
# Dispatch counting
# ---------------------------------------------------------------------------

@check("dispatch counts walk NESTED subagents, not only the top level")
def _():
    _reset()
    _trace(date.today() - timedelta(days=1), [_turn(), _turn()])
    counts, measured = R.dispatch_counts(F.PERSONA, days=3)
    assert counts["home_care"] == 2, counts
    assert measured == 1, measured


@check("a day holding ONLY Build's own ticks is not a measured day")
def _():
    _reset()
    _trace(date.today() - timedelta(days=1), [_tick_record(), _tick_record()])
    counts, measured = R.dispatch_counts(F.PERSONA, days=3)
    assert measured == 0, (
        "on the day a capability lands the trace file holds exactly one record "
        f"— Build's. Dividing by that gave `actual 0.0 over 1d`: {measured}")
    assert counts["home_care"] == 0


@check("the LANDING DAY itself is excluded via `after`")
def _():
    _reset()
    landing = date.today() - timedelta(days=2)
    _trace(landing, [_turn()])
    _trace(date.today() - timedelta(days=1), [_turn()])
    _counts, measured = R.dispatch_counts(F.PERSONA, days=5,
                                          after=landing.isoformat())
    assert measured == 1, (
        "a capability that landed at 16:00 has no meaningful full-day rate from "
        f"the remaining hours: {measured}")


@check("with no measured day the count is left None, never written as zero")
def _():
    _reset()
    _write(_row("landed"))
    result = R.refresh_run_counts(F.PERSONA, path=REGISTRY)
    assert "left uncounted rather than written as zero" in result, result
    row = R.row_for("home_care", REGISTRY)
    assert row["run"]["dispatches_actual_per_day"] is None, (
        "'we could not count' and 'it never fires' are different facts")


@check("a real day of use fills the run line")
def _():
    _reset()
    _write(_row("landed", days_ago=3))
    for back in (1, 2):
        _trace(date.today() - timedelta(days=back), [_turn(), _turn()])
    R.refresh_run_counts(F.PERSONA, days=5, path=REGISTRY)
    run = R.row_for("home_care", REGISTRY)["run"]
    assert run["dispatches_actual_per_day"] == 2.0, run
    assert run["counted_over_days"] == 2, run


@check("nothing landed means no refresh rows at all")
def _():
    _reset()
    _write()
    assert "nothing landed" in R.refresh_run_counts(F.PERSONA, path=REGISTRY)


@check("the tier review is due at four LEAF capabilities")
def _():
    _reset()
    rows = [_row("landed", name=f"cap_{i}", ticket=f"BLD-0924-0{i}")
            for i in range(1, 5)]
    _write(*rows)
    status = R.tier_status(REGISTRY)
    assert status == {"leaves": 4, "due_at": 4, "due": True}, status


@check("the rendered board carries every row, staged ones included")
def _():
    _reset()
    _write(_row("staged"), _row("landed", name="garden_care", ticket="BLD-0924-02"))
    text = R.render_markdown(REGISTRY)
    assert "`home_care`" in text and "`garden_care`" in text, text
    assert "not counted" in text, text


def _cleanup() -> None:
    shutil.rmtree(_TMP, ignore_errors=True)


try:
    code = suite.report()
finally:
    _cleanup()
sys.exit(code)
