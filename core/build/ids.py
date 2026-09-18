"""
core/build/ids.py — job identifiers.

`BLD-MMDD-NN`, deliberately the shape of `DB-MMDD-NN` so a Build job reads like
a backlog item at a glance and neither is mistaken for the other.

The sequence is allocated by REPLAYING today's rows under a lock, never by
incrementing a stored counter. A counter is a second source of truth that
disagrees with the ledger the moment a write is lost, and the failure mode is
two jobs sharing an id — which the ledger replay then silently merges into one.
Replaying makes collision across a restart structurally impossible: the ledger
is the only thing that has to survive, and it is append-only.

This is the same reasoning tools/crm_sweep.py records for proposal state:
"a status file that disagreed with the ledger would be worse than no status file."
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from filelock import FileLock

_ID_RE = re.compile(r"^BLD-(\d{2})(\d{2})-(\d{2})$")

# An id is allocated in well under a second; this only trips on a stuck holder.
_LOCK_TIMEOUT = 30

# Two digits of sequence, so 99 jobs in one day. The daily cap is 4
# (jobs.CAPS["max_jobs_per_day"]), so this is ~25x the ceiling rather than a
# limit anything can reach in practice.
_MAX_PER_DAY = 99


class IdError(RuntimeError):
    """An id could not be allocated or parsed."""


def is_job_id(value: str) -> bool:
    """True for a well-formed BLD id. Does not check that the job exists."""
    return bool(_ID_RE.match(str(value or "").strip()))


def parse_job_id(job_id: str) -> tuple[int, int, int]:
    """(month, day, sequence) for a well-formed id, else raise."""
    match = _ID_RE.match(str(job_id or "").strip())
    if not match:
        raise IdError(
            f"Not a Build job id: {job_id!r} — expected BLD-MMDD-NN"
        )
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def _prefix(when: date | None = None) -> str:
    day = when or date.today()
    return f"BLD-{day.month:02d}{day.day:02d}-"


def _lock_for(ledger: Path) -> FileLock:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    return FileLock(str(ledger.parent / ".ids.lock"), timeout=_LOCK_TIMEOUT)


def next_job_id(persona: str | None = None, when: date | None = None) -> str:
    """
    Allocate the next id for today, under a lock, by replaying the ledger.

    The lock covers read-and-decide, not just the write, because two processes
    that both read "the highest today is 03" will both return 04 however
    atomically each of them appends.
    """
    from core.build.jobs import ledger_path, read_rows

    ledger = ledger_path(persona)
    with _lock_for(ledger):
        return _next_unlocked(read_rows(persona), when)


def _next_unlocked(rows: list[dict], when: date | None = None) -> str:
    """The allocation itself, separated so it is testable without the lock."""
    prefix = _prefix(when)
    highest = 0
    for row in rows:
        job_id = str(row.get("job_id") or "")
        if not job_id.startswith(prefix):
            continue
        match = _ID_RE.match(job_id)
        if match:
            highest = max(highest, int(match.group(3)))
    if highest >= _MAX_PER_DAY:
        raise IdError(
            f"{prefix}{_MAX_PER_DAY:02d} already allocated — the two-digit "
            "sequence is exhausted for today. This is ~25x the daily cap, so "
            "reaching it means the cap is not being enforced."
        )
    return f"{prefix}{highest + 1:02d}"
