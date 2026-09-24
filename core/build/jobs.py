"""
core/build/jobs.py — the job record, and the state replayed from it.

There is no status file. Current state is reconstructed by replaying an
append-only ledger, copying tools/crm_sweep.py:276-297 exactly, and its reason
carries over verbatim: *"a status file that disagreed with the ledger would be
worse than no status file."* A malformed line is skipped, never fatal — one
torn write must not cost the other jobs.

RESTART SURVIVAL — the property the whole design turns on.

There is no in-memory state anywhere in Build. **The state IS the resume
cursor.** Every node is idempotent: it writes `<artifact>.json.tmp` then
`os.replace()`, and a node that finds a valid output already present skips its
model call. So a process killed mid-node loses at most the node in flight, and
the tick that follows re-enters the job at the node that had not written.

`build_tick` re-enters a job whose heartbeat exceeds STALE_MINUTES at
`attempt += 1`. Jobs stay resumable across a crash, a redeploy and a VM restart
without a lock file, a queue, or a daemon holding anything open.

DEPTH is a durable ledger field, not a thread-local. This is strictly better
than core/orchestrator's `_SUBAGENT_DEPTH`, whose known hole is that
`_dispatch_from_coordinator` never sets it: a ledger field cannot be lost
across threads or processes.

Sensitive-tier: everything here lives under data/personas/{p}/, which is
gitignored and inside the existing backup tar.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from core.persona import persona_data_dir

# ---------------------------------------------------------------------------
# States
# ---------------------------------------------------------------------------
#
# `blocked` is deliberately NOT here. It is a FLAG on the row, following
# DEV_BACKLOG.md's `@waiting:` convention, which that file describes as
# "a property of items already counted, never a new section." A blocked job is
# still in whatever state it reached; making blocked a state would lose that.

STATES: tuple[str, ...] = (
    "proposed",          # filed by request_build; Mike triages. Never auto-queued.
    "queued",
    "inquiry",
    "questions_ready",
    "librarian",
    "ledger_ready",
    "needs_interview",   # an interview item must be answered before planning
    "planning",
    "plan_ready",
    "awaiting_approval", # over budget, or above the writer's autonomy ceiling
    "briefed",
    "executing",
    "verifying",
    "landed",
    "failed",
    "abandoned",
    "superseded",
)

TERMINAL: frozenset[str] = frozenset({"landed", "failed", "abandoned", "superseded"})

# States where a job is WAITING FOR A HUMAN. The tick walks past every one of
# them and nothing in Build clears one by itself — that is what makes them
# gates rather than delays.
#
# Here beside STATES rather than in runner.py, for two reasons. It is a property
# of the state machine, not of the driver: "which states mean a person has to
# act" is the same question as "what are the states". And tools/build.py's
# context_block reads it on EVERY user turn through load_recent_context —
# importing the whole runner (and with it the writer, the registry, settle and
# the probe) to learn five strings would put the entire Build vertical on the
# hot path of every ordinary session.
#
#   proposed           Mike triages. request_build NEVER auto-queues.
#   needs_interview    [N6] only the user can answer these questions.
#   awaiting_approval  over budget, or above the writer's autonomy ceiling.
#   briefed            [N9] the brief is written and Mike has not approved it.
#   verifying          [N13] live in the overlay and verified; accept or refuse.
GATE_STATES: frozenset[str] = frozenset({
    "proposed", "needs_interview", "awaiting_approval", "briefed", "verifying",
})

# Ordinary forward progression. Not enforced as a state machine — a node may
# park a job at needs_interview or awaiting_approval from several points — but
# recorded so the board can show how far a job got.
PROGRESSION: tuple[str, ...] = (
    "proposed", "queued", "inquiry", "questions_ready", "librarian",
    "ledger_ready", "planning", "plan_ready", "briefed", "executing",
    "verifying", "landed",
)

CAPS: dict[str, int] = {
    "max_open_jobs": 3,
    "max_proposed": 12,
    "max_jobs_per_day": 4,
    "max_build_depth": 2,
}

MAX_BUILD_DEPTH = CAPS["max_build_depth"]

# Job-level attempts and node-level retries MULTIPLY (plan section 13.1), so the
# product is what actually bounds spend. run_node() caps the product; this is
# the job-level half of it.
MAX_ATTEMPTS = 3

# A build_tick runs every 30 minutes; 45 leaves one tick of slack before a job
# is treated as stalled, so an ordinary long node is not re-entered underneath
# itself.
STALE_MINUTES = 45

# Both windows chosen, not defaulted. A landed capability should not be rebuilt
# from the same gap for a fortnight — long enough for a REPAIR to be the right
# instrument instead. A failed job re-opens after three days, because the usual
# reason a build fails is a missing tool, and that is a Mac-side fix measured in
# days.
DEDUPE_LANDED_DAYS = 14
DEDUPE_FAILED_HOURS = 72

MODES: frozenset[str] = frozenset({"construct", "repair"})


class JobError(RuntimeError):
    """A job could not be created or advanced."""


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def build_dir(persona: str | None = None) -> Path:
    """data/personas/{p}/build/ — the root of everything Build owns."""
    return persona_data_dir(persona) / "build"


def ledger_path(persona: str | None = None) -> Path:
    return build_dir(persona) / "ledger.jsonl"


def registry_path(persona: str | None = None) -> Path:
    return build_dir(persona) / "registry.jsonl"


def jobs_dir(persona: str | None = None) -> Path:
    return build_dir(persona) / "jobs"


def job_dir(job_id: str, persona: str | None = None) -> Path:
    from core.build.ids import is_job_id
    if not is_job_id(job_id):
        raise JobError(f"Not a Build job id: {job_id!r}")
    return jobs_dir(persona) / job_id


def artifact_path(job_id: str, name: str, persona: str | None = None) -> Path:
    """
    One artifact file inside a job directory.

    `name` is checked rather than sanitised — a name needing cleaning is a bug
    in the caller, and quietly rewriting it would mask that.
    """
    if not re.match(r"^[a-z][a-z0-9_]{0,39}$", str(name or "")):
        raise JobError(f"Invalid artifact name {name!r}")
    return job_dir(job_id, persona) / f"{name}.json"


# ---------------------------------------------------------------------------
# Ledger IO
# ---------------------------------------------------------------------------

def read_rows(persona: str | None = None) -> list[dict]:
    """
    Every well-formed row, in written order.

    A truncated or malformed line is skipped, not fatal. A single torn write
    during a crash must not make the whole ledger unreadable, which would take
    every other job down with it.
    """
    path = ledger_path(persona)
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


def append_row(row: dict, persona: str | None = None) -> dict:
    """
    Append one row. The ledger is the only mutable state Build has.

    Opened in append mode and flushed per line: concurrent appends of a single
    short line are atomic on POSIX, and the replay skips anything torn.
    """
    path = ledger_path(persona)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"at": _now(), **row}
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return row


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Replay
# ---------------------------------------------------------------------------

def states(persona: str | None = None) -> dict[str, dict]:
    """
    Current state per job id, reconstructed by replay.

    Row kinds:
      job      the opening row — mode, gap, fingerprint, depth, trigger
      status   a state transition, optionally carrying a detail
      flag     sets or clears `blocked` without changing state
      heartbeat  liveness from a running node
    """
    current: dict[str, dict] = {}
    for row in read_rows(persona):
        job_id = row.get("job_id")
        if not job_id:
            continue
        kind = row.get("row_type", "job")

        if kind == "job":
            current[job_id] = {
                **row,
                "state": row.get("state", "proposed"),
                "attempt": int(row.get("attempt", 1) or 1),
                "blocked": None,
                "history": [row.get("state", "proposed")],
            }
            continue

        job = current.get(job_id)
        if job is None:
            # A status for a job whose opening row was lost to a torn write.
            # Skipped rather than synthesised: a job with no gap and no
            # fingerprint would defeat dedupe and could never be run.
            continue

        if kind == "status":
            state = row.get("state")
            if state in STATES:
                job["state"] = state
                job["history"].append(state)
                job["updated_at"] = row.get("at", "")
                if row.get("detail"):
                    job["detail"] = row["detail"]
                if row.get("attempt") is not None:
                    job["attempt"] = int(row["attempt"])
                # Carried on the job so resume() can read it, and CLEARED on
                # any transition that does not set one — a stale resume_to
                # from an earlier park would send a later resume to the wrong
                # node, which is the failure it exists to prevent.
                job["resume_to"] = row.get("resume_to") or None
        elif kind == "flag":
            job["blocked"] = row.get("blocked") or None
        elif kind == "heartbeat":
            job["heartbeat"] = row.get("at", "")
            if row.get("node"):
                job["node"] = row["node"]
    return current


def get(job_id: str, persona: str | None = None) -> dict | None:
    return states(persona).get(job_id)


def open_jobs(persona: str | None = None) -> dict[str, dict]:
    """Jobs past triage and not yet terminal — what the caps count."""
    return {
        jid: job for jid, job in states(persona).items()
        if job["state"] not in TERMINAL and job["state"] != "proposed"
    }


def proposed_jobs(persona: str | None = None) -> dict[str, dict]:
    return {
        jid: job for jid, job in states(persona).items()
        if job["state"] == "proposed"
    }


def stale_jobs(persona: str | None = None, minutes: int = STALE_MINUTES) -> dict[str, dict]:
    """
    Open jobs whose heartbeat has gone quiet — what build_tick re-enters.

    A job with no heartbeat at all has never started a node, so it is not
    stale; it is waiting, and re-entering it would burn an attempt on a job
    that has not used one.
    """
    cutoff = datetime.now() - timedelta(minutes=minutes)
    out: dict[str, dict] = {}
    for jid, job in open_jobs(persona).items():
        beat = job.get("heartbeat")
        if not beat:
            continue
        try:
            when = datetime.fromisoformat(beat)
        except ValueError:
            continue
        if when < cutoff:
            out[jid] = job
    return out


# ---------------------------------------------------------------------------
# Fingerprints and dedupe
# ---------------------------------------------------------------------------

def _norm(text: str) -> str:
    """Whitespace-collapsed, case-folded. Same shape as crm_sweep._norm."""
    return re.sub(r"\s+", " ", str(text or "")).strip().casefold()


def fingerprint(mode: str, gap: str, capability_hint: str = "") -> str:
    payload = f"{_norm(mode)}|{_norm(gap)}|{_norm(capability_hint)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def duplicate_of(fp: str, persona: str | None = None) -> tuple[str, str] | None:
    """
    (job_id, reason) when `fp` is refused, else None.

    Three windows, each chosen rather than defaulted:
      - any NON-TERMINAL job: the work is already in flight
      - a `landed` job inside 14 days: a landed capability that is answering
        wrongly is a REPAIR, not a second CONSTRUCT
      - a `failed` job inside 72 hours: the usual cause of a failure is a
        missing tool, which is a Mac-side build measured in days
    """
    now = datetime.now()
    for job_id, job in states(persona).items():
        if job.get("fingerprint") != fp:
            continue
        state = job["state"]
        if state not in TERMINAL:
            return job_id, f"already open at {state}"
        stamp = job.get("updated_at") or job.get("at") or ""
        try:
            when = datetime.fromisoformat(stamp)
        except ValueError:
            continue
        if state == "landed" and now - when < timedelta(days=DEDUPE_LANDED_DAYS):
            age = (now - when).days
            return job_id, (
                f"landed {age}d ago (within the {DEDUPE_LANDED_DAYS}d window) — "
                "a landed capability answering wrongly is a REPAIR, not a rebuild"
            )
        if state == "failed" and now - when < timedelta(hours=DEDUPE_FAILED_HOURS):
            hours = int((now - when).total_seconds() // 3600)
            return job_id, (
                f"failed {hours}h ago (within the {DEDUPE_FAILED_HOURS}h window)"
            )
    return None


# ---------------------------------------------------------------------------
# Creating and advancing
# ---------------------------------------------------------------------------

def create(gap: str, trigger: str, mode: str = "construct",
           capability_hint: str = "", depth: int = 0,
           persona: str | None = None, state: str = "proposed") -> dict:
    """
    File a job. Returns the opening row.

    Lands in `proposed`, never `queued` — Mike triages. A gap filed by a fast
    routing model is a candidate, not an instruction.

    Refusals raise JobError with the reason in the message; request_build turns
    that into an explanatory string rather than an exception, house style.
    """
    from core.build.ids import next_job_id

    mode = _norm(mode)
    if mode not in MODES:
        raise JobError(f"mode must be one of {sorted(MODES)}, got {mode!r}")

    # Validated exactly as write_quality_event validates its own fields — the
    # precedent being the USER_CORRECTION slot that produced "None." 93 times.
    from tools.logger import is_null_ish
    if not str(gap or "").strip() or is_null_ish(gap):
        raise JobError(
            "gap is empty or a non-answer — a job with no gap cannot be "
            "deduped, planned or verified"
        )

    if depth > MAX_BUILD_DEPTH:
        raise JobError(
            f"depth {depth} exceeds MAX_BUILD_DEPTH={MAX_BUILD_DEPTH}"
        )

    fp = fingerprint(mode, gap, capability_hint)
    dupe = duplicate_of(fp, persona)
    if dupe:
        raise JobError(f"duplicate of {dupe[0]} — {dupe[1]}")

    if state == "proposed":
        if len(proposed_jobs(persona)) >= CAPS["max_proposed"]:
            raise JobError(
                f"max_proposed={CAPS['max_proposed']} reached. A full proposed "
                "queue means gap detection is over-firing; the fix is narrowing "
                "the trigger, not raising the cap."
            )
    else:
        _check_open_caps(persona)

    job_id = next_job_id(persona)
    job_dir(job_id, persona).mkdir(parents=True, exist_ok=True)
    return append_row({
        "row_type": "job",
        "job_id": job_id,
        "state": state,
        "mode": mode,
        "gap": str(gap).strip(),
        "capability_hint": str(capability_hint or "").strip(),
        "trigger": str(trigger or "").strip(),
        "fingerprint": fp,
        "depth": int(depth),
        "attempt": 1,
    }, persona)


def _check_open_caps(persona: str | None = None) -> None:
    if len(open_jobs(persona)) >= CAPS["max_open_jobs"]:
        raise JobError(f"max_open_jobs={CAPS['max_open_jobs']} reached")
    today = date_prefix()
    started = sum(
        1 for job in states(persona).values()
        if str(job.get("job_id", "")).startswith(today)
        and job["state"] != "proposed"
    )
    if started >= CAPS["max_jobs_per_day"]:
        raise JobError(f"max_jobs_per_day={CAPS['max_jobs_per_day']} reached")


def date_prefix() -> str:
    from datetime import date as _date
    day = _date.today()
    return f"BLD-{day.month:02d}{day.day:02d}-"


def set_state(job_id: str, state: str, detail: str = "",
              attempt: int | None = None, resume_to: str | None = None,
              persona: str | None = None) -> dict:
    if state not in STATES:
        raise JobError(f"Unknown state {state!r}")
    job = get(job_id, persona)
    if job is None:
        raise JobError(f"No such job: {job_id}")
    if job["state"] in TERMINAL and state not in TERMINAL:
        raise JobError(
            f"{job_id} is terminal at {job['state']} — it cannot re-open. "
            "File a new job, or a REPAIR against the capability it landed."
        )
    if state == "queued" and job["state"] == "proposed":
        _check_open_caps(persona)
    row: dict[str, Any] = {"row_type": "status", "job_id": job_id, "state": state}
    if detail:
        row["detail"] = str(detail)
    if attempt is not None:
        row["attempt"] = int(attempt)
    # WHERE A PARK RETURNS TO. A job parked at `awaiting_approval` has to go
    # back to the state it was parked FROM, and only the parker knows which
    # that is: resume() used to send every job to `planning`, so one parked at
    # N12 (over the autonomy ceiling) came back with every artifact already
    # present, skipped every node, and stalled — N12 wants `executing` and
    # approve() wants `briefed`, so neither command could move it and the
    # PARKED message's "raise the flag on the VM to proceed" led nowhere
    # without editing the ledger by hand.
    if resume_to:
        row["resume_to"] = str(resume_to)
    return append_row(row, persona)


def set_blocked(job_id: str, reason: str | None, persona: str | None = None) -> dict:
    """Set or clear the blocked flag. State is untouched — blocked is a property."""
    return append_row({
        "row_type": "flag", "job_id": job_id, "blocked": reason or None,
    }, persona)


def heartbeat(job_id: str, node: str = "", persona: str | None = None) -> dict:
    return append_row({
        "row_type": "heartbeat", "job_id": job_id, "node": str(node or ""),
    }, persona)


def next_attempt(job_id: str, persona: str | None = None) -> int:
    """
    Re-enter a stalled job at attempt + 1. Returns the new attempt number.

    Raises when attempts are exhausted — the job is failed by the caller, which
    is what puts the reason on the board rather than losing it here.
    """
    job = get(job_id, persona)
    if job is None:
        raise JobError(f"No such job: {job_id}")
    nxt = int(job.get("attempt", 1)) + 1
    if nxt > MAX_ATTEMPTS:
        raise JobError(
            f"{job_id} has used all {MAX_ATTEMPTS} attempts"
        )
    set_state(job_id, job["state"], detail=f"re-entered after stall", attempt=nxt,
              persona=persona)
    return nxt


# ---------------------------------------------------------------------------
# Artifacts — the resume cursor
# ---------------------------------------------------------------------------

def write_artifact(job_id: str, name: str, payload: dict,
                   persona: str | None = None) -> Path:
    """
    Write one artifact atomically: temp file in the same directory, then
    os.replace(). A reader sees the whole old file or the whole new one, never
    a half-written prefix — which is what lets read_artifact() be trusted as a
    "this node already ran" signal after a kill -9.
    """
    path = artifact_path(job_id, name, persona)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".",
                                    suffix=".tmp")
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                       encoding="utf-8")
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return path


def read_artifact(job_id: str, name: str,
                  persona: str | None = None) -> dict | None:
    """
    The artifact if present and parseable, else None.

    None means "this node has not produced valid output", which is exactly the
    condition for running it. A present-but-unparseable file returns None too:
    it cannot have come from os.replace() of a complete write, so it is debris.
    """
    path = artifact_path(job_id, name, persona)
    if not path.exists():
        return None
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    return parsed if isinstance(parsed, dict) else None


def has_artifact(job_id: str, name: str, persona: str | None = None) -> bool:
    return read_artifact(job_id, name, persona) is not None
