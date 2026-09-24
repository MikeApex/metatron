"""
core/build/tickets.py — the VM's inbox, and nothing more.

Plan: archive/plans/build_vertical_plan_2026-09-24.md section 5.

THE VM HOLDS AN INBOX; THE TRACKED REGISTRY HOLDS THE STATE. That split is the
answer to "two state homes will disagree" (section 13.8): a ticket has exactly
ONE state here — `open` — from the moment `request_build` files it until the
deployed registry carries its row. There is no `queued`, no `planning`, no
`landed` on this side, because the Mac is where a job lives and the VM has no
way to learn what happened to it except by being deployed.

WHAT THAT BUYS, AND WHAT IT COSTS (finding 7). A ticket decided on the Mac stays
open here until the next deploy, so its fingerprint is refused the whole time —
nothing is re-filed while Mike is mid-build. A capability and its `landed`
registry row reach the VM in the SAME deploy by construction, so REPAIR
eligibility can never lag the capability it counts for. What genuinely lags is
`abandoned`: until the deploy that carries the row, the ticket still counts
toward `max_proposed`. That is bounded by the cap, and scripts/build_board.py
prints "N decided, awaiting deploy" beside the open count so the cost is
visible rather than read as gaps still waiting.

NO WRITE PATH FROM THE MAC EXISTS OR IS ADDED. This file is written only by
code running on the VM: `request_build` (tools/build.py) and the REPAIR counter
(core/build/tick.py). The Mac reads a FETCHED COPY through the existing
read-only monitor route.

Sensitive-tier: data/personas/{p}/build/, gitignored, inside the backup tar.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

from core.persona import persona_data_dir

MODES: frozenset[str] = frozenset({"construct", "repair"})

# Filing caps. Both bound what the VM may ACCUMULATE, not what Mike may build —
# the Mac has no cap, because the bound there is the session he is sitting in.
#
# max_proposed is the one that matters: a full inbox means gap detection is
# over-firing, and section 13.9's concession stands — the fix is narrowing the
# trigger, not raising the cap.
_CAP_DEFAULTS: dict[str, int] = {
    "max_proposed": 12,
    "max_jobs_per_day": 4,
}


def caps() -> dict[str, int]:
    """
    The caps, from config/modules/build.yaml, falling back to the defaults.

    READ AT CALL TIME, not at import. A cap cached at import would be the one
    the scheduler process started with, so raising it would need a restart and
    the restart would be the thing nobody did.

    config/modules/build.yaml is on the deny list in gates.py, so Build cannot
    edit it: the only hand that raises a cap is Mike's. That is what makes a
    configurable cap a cap rather than a suggestion.
    """
    from pathlib import Path as _Path
    path = _Path(__file__).resolve().parent.parent.parent / "config" / "modules" / "build.yaml"
    out = dict(_CAP_DEFAULTS)
    if not path.exists():
        return out
    try:
        import yaml
        cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return out
    for key in out:
        value = (cfg.get("caps") or {}).get(key)
        if isinstance(value, int) and value > 0:
            out[key] = value
    return out

# Both windows chosen, not defaulted. A landed capability should not be rebuilt
# from the same gap for a fortnight — long enough for a REPAIR to be the right
# instrument instead. An abandoned ticket re-opens after three days, because
# "Mike closed this without building it" is a judgement that can change, and
# three days is long enough that the change is a decision rather than a retry.
DEDUPE_LANDED_DAYS = 14
DEDUPE_ABANDONED_HOURS = 72


class TicketError(RuntimeError):
    """A ticket could not be filed."""


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def build_dir(persona: str | None = None) -> Path:
    """data/personas/{p}/build/ — everything the VM side of Build owns."""
    return persona_data_dir(persona) / "build"


def tickets_path(persona: str | None = None) -> Path:
    return build_dir(persona) / "tickets.jsonl"


# ---------------------------------------------------------------------------
# IO
# ---------------------------------------------------------------------------

def read_rows(persona: str | None = None) -> list[dict]:
    """
    Every well-formed row, in written order.

    A truncated or malformed line is skipped, not fatal. One torn write during
    a crash must not make the whole inbox unreadable, which would take every
    other ticket down with it — tools/crm_sweep.py's rule, verbatim.
    """
    path = tickets_path(persona)
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
        if isinstance(row, dict) and row.get("job_id"):
            rows.append(row)
    return rows


def append_row(row: dict, persona: str | None = None) -> dict:
    """
    Append one ticket. Opened in append mode and fsynced: a concurrent append of
    a single short line is atomic on POSIX, and the replay skips anything torn.
    """
    path = tickets_path(persona)
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


def tickets(persona: str | None = None) -> dict[str, dict]:
    """Every ticket by id. The last row for an id wins, though nothing rewrites one."""
    out: dict[str, dict] = {}
    for row in read_rows(persona):
        out[str(row["job_id"])] = row
    return out


# ---------------------------------------------------------------------------
# Fingerprints and dedupe
# ---------------------------------------------------------------------------

def _norm(text: str) -> str:
    """Whitespace-collapsed, case-folded. Same shape as crm_sweep._norm."""
    return re.sub(r"\s+", " ", str(text or "")).strip().casefold()


def fingerprint(mode: str, gap: str, capability_hint: str = "") -> str:
    return hashlib.sha256(
        f"{_norm(mode)}|{_norm(gap)}|{_norm(capability_hint)}".encode("utf-8")
    ).hexdigest()[:16]


def duplicate_of(fp: str, persona: str | None = None) -> tuple[str, str] | None:
    """
    (job_id, reason) when `fp` is refused, else None.

    THREE WINDOWS, AND THE FIRST IS WHY THE INBOX NEEDS NO SECOND STATE:

      · an OPEN ticket here — the work is filed and has not come back yet, and
        it stays open across the whole build because only a deploy closes it.
      · a `landed` registry row inside 14 days — a landed capability answering
        wrongly is a REPAIR, not a second CONSTRUCT.
      · an `abandoned` registry row inside 72 hours.

    The registry is read from the DEPLOYED tracked file, which is the same copy
    the running capability came from — so the dedupe window and the capability
    it protects can never be out of step.
    """
    now = datetime.now()
    landed_at: dict[str, tuple[str, str]] = {}
    try:
        from core.build.registry import rows_by_ticket
        landed_at = rows_by_ticket()
    except Exception:
        landed_at = {}

    for job_id, row in tickets(persona).items():
        if row.get("fingerprint") != fp:
            continue
        state, stamp = landed_at.get(job_id, ("", ""))
        if not state:
            return job_id, "already filed and not yet decided"
        try:
            when = datetime.fromisoformat(stamp)
        except ValueError:
            continue
        if state == "landed" and now - when < timedelta(days=DEDUPE_LANDED_DAYS):
            return job_id, (
                f"landed {(now - when).days}d ago (within the "
                f"{DEDUPE_LANDED_DAYS}d window) — a landed capability answering "
                "wrongly is a REPAIR, not a rebuild")
        if state == "abandoned" and now - when < timedelta(hours=DEDUPE_ABANDONED_HOURS):
            hours = int((now - when).total_seconds() // 3600)
            return job_id, (
                f"abandoned {hours}h ago (within the "
                f"{DEDUPE_ABANDONED_HOURS}h window)")
    return None


# ---------------------------------------------------------------------------
# Filing
# ---------------------------------------------------------------------------

# The two callers that legitimately write a ticket, and both run ON THE VM:
# `request_build` (the Coordinator's tool) and the REPAIR counter in tick.py.
#
# WHY THIS IS A NAMED ALLOWLIST AND NOT A MACHINE CHECK. The ticket file lives
# under `data/personas/{p}/build/`, which exists in both checkouts, and nothing
# in-process distinguishes the Mac from the VM — DEPLOYMENT_MODE is `cloud` on
# both. So a Build session on the Mac calling this would append to a Mac-local
# persona tree the VM never sees, minting an id against a stale ledger that can
# collide with the VM's next allocation, and the board would never list it.
#
# The allowlist cannot stop a caller that lies. What it does is convert a silent
# wrong-machine write into an explicit refusal naming the rule, which is the
# same standard `.claude/rules/agent-files.md` applies to a named tool. A true
# machine-level gate needs an env marker set by the systemd units — a deploy
# change, and Mike's to make.
TICKET_WRITERS: frozenset[str] = frozenset({"request_build", "repair_scan"})


def file_ticket(gap: str, trigger: str, mode: str = "construct",
                capability_hint: str = "", persona: str | None = None,
                writer: str = "") -> dict:
    """
    File one ticket. Returns the row. VM-SIDE ONLY — see TICKET_WRITERS.

    Refusals raise TicketError with the reason in the message; request_build
    turns that into an explanatory string rather than an exception, house style,
    so a duplicate reads as information and not as a tool error the model then
    narrates to the user.
    """
    from core.build.ids import next_job_id

    if writer not in TICKET_WRITERS:
        raise TicketError(
            f"file_ticket needs writer= one of {sorted(TICKET_WRITERS)}, got "
            f"{writer!r}. The ticket inbox is VM state and there is no write "
            "path from the Mac to it: a ticket filed here lands in a local "
            "persona tree the VM never reads, with an id allocated against a "
            "stale ledger. A failed acceptance is REPORTED and recorded on the "
            "registry row; REPAIR is filed on the VM by the correction counter.")

    mode = _norm(mode)
    if mode not in MODES:
        raise TicketError(f"mode must be one of {sorted(MODES)}, got {mode!r}")

    # Validated exactly as write_quality_event validates its own fields — the
    # precedent being the USER_CORRECTION slot that produced "None." 93 times.
    from tools.logger import is_null_ish
    if not str(gap or "").strip() or is_null_ish(gap):
        raise TicketError(
            "gap is empty or a non-answer — a ticket with no gap cannot be "
            "deduped, planned or verified")

    fp = fingerprint(mode, gap, capability_hint)
    dupe = duplicate_of(fp, persona)
    if dupe:
        raise TicketError(f"duplicate of {dupe[0]} — {dupe[1]}")

    limits = caps()
    if len(open_tickets(persona)) >= limits["max_proposed"]:
        raise TicketError(
            f"max_proposed={limits['max_proposed']} reached. A full inbox means "
            "gap detection is over-firing; the fix is narrowing the trigger, "
            "not raising the cap.")

    today = date_prefix()
    if sum(1 for j in tickets(persona) if j.startswith(today)) >= limits["max_jobs_per_day"]:
        raise TicketError(f"max_jobs_per_day={limits['max_jobs_per_day']} reached")

    return append_row({
        "job_id": next_job_id(persona),
        "mode": mode,
        "gap": str(gap).strip(),
        "capability_hint": str(capability_hint or "").strip(),
        "trigger": str(trigger or "").strip(),
        "fingerprint": fp,
        "persona": persona or _resolved_persona(),
    }, persona)


def _resolved_persona() -> str:
    """The persona this process is bound to, for the row's own record."""
    try:
        from core.persona import resolve_persona
        return str(resolve_persona() or "")
    except Exception:
        return ""


def date_prefix(when: datetime | None = None) -> str:
    day = (when or datetime.now()).date()
    return f"BLD-{day.month:02d}{day.day:02d}-"


def open_tickets(persona: str | None = None) -> dict[str, dict]:
    """
    Tickets with no deployed registry row. THE ONLY STATE THIS SIDE HAS.

    Reading the registry rather than a status field here is the whole design:
    there is no second place a ticket's state could be written, so there is no
    second place it could be written wrongly.
    """
    try:
        from core.build.registry import rows_by_ticket
        decided = set(rows_by_ticket())
    except Exception:
        decided = set()
    return {jid: row for jid, row in tickets(persona).items() if jid not in decided}


def decided_awaiting_deploy(open_ids: list[str]) -> list[str]:
    """
    Of the ticket ids the VM still reports OPEN, the ones the working tree has
    already decided — finding 7's named lag, made visible instead of inferred.

    Takes the VM's open list as an argument rather than reading it, because the
    join is between two machines: `open_ids` comes from the fetched ticket file
    and the registry read here is the WORKING TREE's, which carries rows Mike
    has committed but not yet deployed. On the VM itself the two registries are
    the same file and this is always empty, which is correct.
    """
    try:
        from core.build.registry import rows_by_ticket
        decided = set(rows_by_ticket())
    except Exception:
        return []
    return sorted(set(str(i) for i in open_ids) & decided)
