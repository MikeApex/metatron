"""
core/build/cost.py — per-job metering, priced by the guard everything else uses.

THREE PARTS, NO MULTIPLIER (plan section 8). A default limit per job; if the N8
estimate exceeds it the job parks at `awaiting_approval` and asks; and the run
HARD-STOPS the moment the limit — default or approved — is exceeded. A
tripwire, not a tolerance band.

ONE PRICING TABLE, NOT TWO. Prices come from `spend_guard.estimate_usd()`, the
same function the global guard uses, so the two meters cannot disagree about
what a token costs. A second table here was rejected on this repo's own
evidence: spend_guard.py's header records that its docstring said $70/$150
through two raises and a revert. A price written down twice goes stale once.

THE SEAM IS A NO-OP UNLESS A JOB IS BOUND. `record_job_tokens()` is called from
`record_turn_tokens()` in core/trace.py — every provider path already reports
there, so it is the one place that sees every call. With no job on the thread
it returns immediately, which is what makes it safe on the hot path of every
ordinary session.

ENFORCEMENT IS PRE-NODE, AND THIS MODULE IS HONEST ABOUT WHY. `run_node()`
(phase 4) checks before starting a node. Mid-node, a breach can only be
RECORDED: a call already in flight cannot be aborted, and this design does not
pretend otherwise. The consequence is that a job can overshoot by at most one
node, which is the cost of not pretending.

STANDING COST: none. Nothing here creates anything that persists between calls
— no cache, no warm pool, no scheduled job. The per-job spend file grows by a
few hundred bytes per model call and is deleted with the job directory by
revert() or abandonment.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import date
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).parent.parent.parent

# Hardcoded default, used until config/modules/build.yaml exists (phase 3
# creates that file, for the writer's autonomy ceiling). Deliberately a floor
# rather than a guess at the right number: the first three bootstrap runs are
# what will set it, and a limit that trips is a cheap signal while a limit that
# never trips is no signal at all.
DEFAULT_JOB_LIMIT_USD = 2.50

_CONFIG_PATH = _ROOT / "config" / "modules" / "build.yaml"

_state = threading.local()


class BudgetExceeded(RuntimeError):
    """A job has spent past its limit. Carries the figures."""

    def __init__(self, job_id: str, spent: float, limit: float):
        self.job_id, self.spent, self.limit = job_id, spent, limit
        super().__init__(
            f"{job_id} has spent ${spent:.4f} against a ${limit:.2f} limit"
        )


# ---------------------------------------------------------------------------
# Binding a job to the thread
# ---------------------------------------------------------------------------

class job_scope:
    """
    Bind a job for the duration of the block, on this thread.

    Thread-local for the same reason core/persona.py is: Build nodes run on a
    pooled executor thread and a process-global would let a concurrent request
    bill its tokens to someone else's job.
    """

    def __init__(self, job_id: str, persona: str | None = None, node: str = ""):
        self.job_id, self.persona, self.node = job_id, persona, node
        self._previous: tuple | None = None

    def __enter__(self) -> str:
        self._previous = getattr(_state, "job", None)
        _state.job = (self.job_id, self.persona, self.node)
        return self.job_id

    def __exit__(self, *exc: Any) -> None:
        _state.job = self._previous
        return None


def current_job() -> tuple[str, str | None, str] | None:
    """(job_id, persona, node) bound on this thread, or None."""
    return getattr(_state, "job", None)


# ---------------------------------------------------------------------------
# The metering seam
# ---------------------------------------------------------------------------

def record_job_tokens(model: str, tokens_in: int, tokens_out: int,
                      tokens_cached: int = 0) -> None:
    """
    Attribute one model call to the bound job. NO-OP when none is bound.

    Called from core/trace.py's record_turn_tokens(). Never raises: a metering
    failure must not take down a session, and the global guard's own recording
    is unaffected by anything that happens here.
    """
    bound = current_job()
    if bound is None:
        return
    job_id, persona, node = bound
    try:
        from core.spend_guard import estimate_usd
        usd = estimate_usd(model or "", tokens_in or 0, tokens_out or 0,
                           tokens_cached=tokens_cached or 0)
        _append_spend(job_id, persona, {
            "model": model or "", "node": node,
            "tokens_in": int(tokens_in or 0),
            "tokens_out": int(tokens_out or 0),
            "tokens_cached": int(tokens_cached or 0),
            "usd": round(float(usd), 6),
        })
    except Exception:
        pass


def _spend_path(job_id: str, persona: str | None = None) -> Path:
    from core.build.jobs import job_dir
    return job_dir(job_id, persona) / "spend.jsonl"


def _append_spend(job_id: str, persona: str | None, row: dict) -> None:
    from datetime import datetime
    path = _spend_path(job_id, persona)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"at": datetime.now().isoformat(timespec="seconds"), **row}
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Reading and enforcing
# ---------------------------------------------------------------------------

def spend_rows(job_id: str, persona: str | None = None) -> list[dict]:
    """Every recorded call for a job. A malformed line is skipped, not fatal."""
    path = _spend_path(job_id, persona)
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def job_spend(job_id: str, persona: str | None = None) -> float:
    return round(sum(float(r.get("usd") or 0.0) for r in spend_rows(job_id, persona)), 6)


def job_tokens(job_id: str, persona: str | None = None) -> dict:
    rows = spend_rows(job_id, persona)
    return {
        "calls": len(rows),
        "tokens_in": sum(int(r.get("tokens_in") or 0) for r in rows),
        "tokens_out": sum(int(r.get("tokens_out") or 0) for r in rows),
        "tokens_cached": sum(int(r.get("tokens_cached") or 0) for r in rows),
        "usd": job_spend(job_id, persona),
    }


def job_limit(job_id: str = "", persona: str | None = None) -> float:
    """
    The limit in force: an approved per-job override if one exists, else the
    configured default, else DEFAULT_JOB_LIMIT_USD.

    An approved override is recorded on the job's own ledger as a `budget` row,
    so it survives a restart and is visible on the board — an approval held
    only in a process would be lost by exactly the crash that makes a long job
    expensive.
    """
    if job_id:
        approved = approved_limit(job_id, persona)
        if approved is not None:
            return approved
    return _configured_limit()


def _configured_limit() -> float:
    if not _CONFIG_PATH.exists():
        return DEFAULT_JOB_LIMIT_USD
    try:
        import yaml
        cfg = yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8")) or {}
        value = (cfg.get("budget") or {}).get("per_job_usd")
        return float(value) if value is not None else DEFAULT_JOB_LIMIT_USD
    except Exception:
        return DEFAULT_JOB_LIMIT_USD


def approve_limit(job_id: str, limit_usd: float, persona: str | None = None) -> dict:
    """Record an approved per-job limit. Mike's answer to the parked job."""
    from core.build.jobs import append_row
    return append_row({
        "row_type": "budget", "job_id": job_id,
        "limit_usd": round(float(limit_usd), 4),
    }, persona)


def approved_limit(job_id: str, persona: str | None = None) -> float | None:
    from core.build.jobs import read_rows
    found: float | None = None
    for row in read_rows(persona):
        if row.get("row_type") == "budget" and row.get("job_id") == job_id:
            try:
                found = float(row.get("limit_usd"))
            except (TypeError, ValueError):
                continue
    return found


def check_budget(job_id: str, persona: str | None = None) -> None:
    """
    PRE-NODE gate. Raises BudgetExceeded when the job has already spent past
    its limit.

    A tripwire, not a tolerance band: there is no grace multiplier, and the
    check is `>=` against the limit rather than against some fraction of it.
    """
    limit = job_limit(job_id, persona)
    spent = job_spend(job_id, persona)
    if spent >= limit:
        raise BudgetExceeded(job_id, spent, limit)


def would_exceed(job_id: str, estimate_usd_value: float,
                 persona: str | None = None) -> bool:
    """
    True when the N8 estimate takes the job past its limit — the condition that
    parks it at `awaiting_approval` rather than starting the work.
    """
    return (job_spend(job_id, persona) + float(estimate_usd_value or 0.0)) \
        > job_limit(job_id, persona)


def estimate(model: str, tokens_in: int, tokens_out: int,
             tokens_cached: int = 0) -> float:
    """N8's estimator. Same function the guard prices real calls with."""
    from core.spend_guard import estimate_usd
    return round(float(estimate_usd(model or "", tokens_in, tokens_out,
                                    tokens_cached=tokens_cached)), 6)


def day_total(persona: str | None = None, when: date | None = None) -> dict:
    """
    Everything Build spent on a day, across jobs. What the board reports and
    what reconciles against the day's trace.
    """
    from core.build.jobs import jobs_dir
    day = (when or date.today()).isoformat()
    root = jobs_dir(persona)
    total, calls, jobs = 0.0, 0, 0
    if root.is_dir():
        for path in sorted(root.glob("*/spend.jsonl")):
            rows = [r for r in spend_rows(path.parent.name, persona)
                    if str(r.get("at", "")).startswith(day)]
            if not rows:
                continue
            jobs += 1
            calls += len(rows)
            total += sum(float(r.get("usd") or 0.0) for r in rows)
    return {"date": day, "usd": round(total, 6), "calls": calls, "jobs": jobs}
