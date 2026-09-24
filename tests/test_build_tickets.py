"""
tests/test_build_tickets.py — the VM inbox, its caps, and its id allocation.

Plan section 5. The ticket file is the ONE thing Build still writes on the VM,
and the two properties that matter are that an id cannot collide across a
restart and that a cap refuses rather than warns.

Usage:
    python3 tests/test_build_tickets.py
"""

import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.build import ids as I                          # noqa: E402
from core.build import registry as R                     # noqa: E402
from core.build import tickets as TK                     # noqa: E402
from tests.support import build_fixtures as F            # noqa: E402
from tests.support.runner import Suite                   # noqa: E402

suite = Suite("build tickets")
check = suite.check

_TMP = Path(tempfile.mkdtemp(prefix="build-tickets-"))
REGISTRY = _TMP / "registry.yaml"


def _persona_dir(persona: str = F.PERSONA) -> Path:
    directory = _TMP / "personas" / persona
    (directory / "build").mkdir(parents=True, exist_ok=True)
    return directory


_current = {"persona": F.PERSONA}

import core.persona as _persona                          # noqa: E402

_persona.persona_data_dir = lambda persona=None: _persona_dir(
    persona or _current["persona"])                                # type: ignore
TK.persona_data_dir = lambda persona=None: _persona_dir(
    persona or _current["persona"])                                # type: ignore
R.REGISTRY_PATH = REGISTRY                                          # type: ignore


def _reset() -> None:
    shutil.rmtree(_TMP / "personas", ignore_errors=True)
    _persona_dir()
    R.write({"schema": "build_registry/1", "capabilities": []}, REGISTRY)


def _file(gap: str, **kw) -> dict:
    # `writer` names one of the two VM-side callers file_ticket admits. Supplied
    # here so every OTHER assertion in this suite still exercises what it was
    # written to exercise; the allowlist itself is asserted at the foot of the
    # file rather than by leaving every case unable to file.
    kw.setdefault("writer", "request_build")
    return TK.file_ticket(gap=gap, trigger="test", persona=F.PERSONA, **kw)


TODAY = f"BLD-{date.today().month:02d}{date.today().day:02d}-"


# ---------------------------------------------------------------------------
# Filing
# ---------------------------------------------------------------------------

@check("a ticket files with a dense id and a fingerprint")
def _():
    _reset()
    row = _file("nothing tracks when the plants were watered")
    assert row["job_id"] == TODAY + "01", row
    assert len(row["fingerprint"]) == 16, row
    assert row["mode"] == "construct"


@check("ids are allocated by REPLAYING the file, so a restart cannot collide")
def _():
    _reset()
    _file("gap one")
    _file("gap two")
    # No counter exists to reset — the allocator reads the file every time.
    assert I.next_job_id(F.PERSONA) == TODAY + "03"
    assert [r["job_id"] for r in TK.read_rows(F.PERSONA)] == [TODAY + "01",
                                                              TODAY + "02"]


@check("an empty or null-ish gap is REFUSED, not filed")
def _():
    _reset()
    for gap in ("", "   ", "None", "N/A"):
        try:
            _file(gap)
        except TK.TicketError as exc:
            assert "non-answer" in str(exc) or "empty" in str(exc), exc
            continue
        raise AssertionError(f"{gap!r} was filed — it cannot be deduped or planned")


@check("the same gap twice is refused as a duplicate")
def _():
    _reset()
    _file("the plants")
    try:
        _file("the plants")
    except TK.TicketError as exc:
        assert "duplicate of" in str(exc), exc
        return
    raise AssertionError("a duplicate fingerprint was filed")


@check("the fingerprint is whitespace- and case-insensitive")
def _():
    assert (TK.fingerprint("construct", "The  Plants")
            == TK.fingerprint("construct", "the plants"))
    assert (TK.fingerprint("repair", "the plants")
            != TK.fingerprint("construct", "the plants"))


@check("an unknown mode is refused")
def _():
    _reset()
    try:
        _file("the plants", mode="rebuild")
    except TK.TicketError as exc:
        assert "mode must be" in str(exc), exc
        return
    raise AssertionError("an unknown mode was accepted")


# ---------------------------------------------------------------------------
# Caps
# ---------------------------------------------------------------------------

@check("max_jobs_per_day refuses the fifth ticket of a day")
def _():
    _reset()
    for n in range(TK.caps()["max_jobs_per_day"]):
        _file(f"gap number {n}")
    try:
        _file("one gap too many")
    except TK.TicketError as exc:
        assert "max_jobs_per_day" in str(exc), exc
        return
    raise AssertionError("the daily cap did not refuse")


@check("the caps are read from build.yaml at CALL time, not at import")
def _():
    limits = TK.caps()
    assert limits == {"max_proposed": 12, "max_jobs_per_day": 4}, limits
    import yaml
    cfg = yaml.safe_load((ROOT / "config" / "modules" / "build.yaml")
                         .read_text(encoding="utf-8"))
    assert cfg["caps"] == limits, (
        "a cap cached at import would need a restart to change, and the "
        f"restart is the thing nobody does: {cfg}")


@check("build.yaml carries the API allowance with no consumer")
def _():
    import yaml
    cfg = yaml.safe_load((ROOT / "config" / "modules" / "build.yaml")
                         .read_text(encoding="utf-8"))
    assert cfg["api_allowance_usd_per_step"] == 1.00, cfg
    assert "autonomy" not in cfg, (
        "the overlay's permission dial is retired — a flag describing a "
        "permission system that no longer decides anything is worse than none")


# ---------------------------------------------------------------------------
# Persona qualification
# ---------------------------------------------------------------------------

@check("two personas can mint the SAME id on one day, in separate files")
def _():
    _reset()
    _persona_dir("persona_b")
    a = _file("gap for a")
    b = TK.file_ticket(gap="gap for b", trigger="test", persona="persona_b",
                       writer="request_build")
    assert a["job_id"] == b["job_id"] == TODAY + "01", (a, b)
    assert len(TK.read_rows(F.PERSONA)) == 1
    assert len(TK.read_rows("persona_b")) == 1


@check("the ticket row records which persona filed it")
def _():
    _reset()
    row = _file("the plants")
    assert row["persona"] == F.PERSONA, row


# ---------------------------------------------------------------------------
# Durability
# ---------------------------------------------------------------------------

@check("a torn line is skipped, and the other tickets survive")
def _():
    _reset()
    _file("gap one")
    path = TK.tickets_path(F.PERSONA)
    path.write_text(path.read_text() + '{"job_id": "BLD-0924-99", "gap"\n',
                    encoding="utf-8")
    _file("gap two")
    rows = TK.read_rows(F.PERSONA)
    assert len(rows) == 2, (
        "one torn write during a crash must not take every other ticket down "
        f"with it: {rows}")


@check("the ticket file is written 0600 — it is sensitive tier")
def _():
    _reset()
    _file("the plants")
    mode = TK.tickets_path(F.PERSONA).stat().st_mode & 0o777
    assert mode == 0o600, oct(mode)


@check("id parsing refuses anything that is not BLD-MMDD-NN")
def _():
    assert I.is_job_id("BLD-0924-01")
    for bad in ("BLD-0924-1", "DB-0924-01", "BLD-924-01", "", "BLD-0924-001"):
        assert not I.is_job_id(bad), bad


def _cleanup() -> None:
    shutil.rmtree(_TMP, ignore_errors=True)


# ---------------------------------------------------------------------------
# The ticket inbox is VM state (phase C, review finding 9)
# ---------------------------------------------------------------------------

@check("file_ticket REFUSES a caller that does not name a VM-side writer")
def _():
    _reset()
    try:
        TK.file_ticket(gap="a gap filed from the wrong machine", trigger="test",
                       persona=F.PERSONA)
    except TK.TicketError as exc:
        assert "writer=" in str(exc), exc
        assert "no write path from the Mac" in str(exc), (
            "the refusal must say WHY, not just that the argument is missing: "
            "a ticket filed on the Mac lands in a tree the VM never reads and "
            "mints an id against a stale ledger")
    else:
        raise AssertionError(
            "a ticket filed with no writer was accepted — N14 calling this from "
            "a Build session is exactly the case that must refuse")
    assert not TK.read_rows(F.PERSONA), "the refused ticket was written anyway"


@check("an unknown writer is refused as firmly as a missing one")
def _():
    _reset()
    for bogus in ("", "build_session", "N14", "mike"):
        try:
            TK.file_ticket(gap=f"gap from {bogus}", trigger="test",
                           persona=F.PERSONA, writer=bogus)
        except TK.TicketError:
            continue
        raise AssertionError(f"writer={bogus!r} was accepted")
    assert not TK.read_rows(F.PERSONA)


@check("both VM-side writers are admitted — the allowlist is not a wall")
def _():
    _reset()
    for writer in sorted(TK.TICKET_WRITERS):
        row = TK.file_ticket(gap=f"a real gap from {writer}", trigger="test",
                             persona=F.PERSONA, writer=writer)
        assert row["job_id"].startswith(TODAY), row


try:
    code = suite.report()
finally:
    _cleanup()
sys.exit(code)
