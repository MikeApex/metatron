"""
core/build/tick.py — what the VM still does every thirty minutes, and nothing else.

Plan: archive/plans/build_vertical_plan_2026-09-24.md sections 2, 3 (REPAIR), 10.

THE TICK NO LONGER RUNS A JOB. Under v3 this was the driver: it replayed a
ledger, re-entered stalled jobs and called models. Ruling 1 moved all of that to
the Mac, so what is left on the VM is TWO COUNTS and a registry refresh:

  · THE REPAIR COUNTER. Corrections are attributed IN CODE to the specialists
    that ran on the previous turn; a fault recurring three times in fourteen
    days against a REGISTERED capability files a `repair` ticket.
  · THE DISPATCH COUNTS for the registry's run line — what a landed capability
    actually costs, standing, forever.

NO MODEL DECIDES EITHER — IT IS COUNTING. Signatures come from
sync_dev_backlog.signature() so one recurring fault collapses to one key, and a
capability in the tracked registry is the only thing that can be repaired.
Everything here is comparison.

THE SIGNATURE FUNCTION IS IMPORTED, not reimplemented. Two definitions of "is
this the same fault" would disagree the first time either was improved, and the
disagreement would be invisible — one side would simply stop reaching three.

ZERO TOKENS ON A QUIET DAY. With no registered capability this returns after one
directory check. A function job that costs nothing when there is nothing to do
is what makes a 30-minute cadence affordable at all.

Returns a plain string, deliberately never a `{"notify": ...}` dict: nothing in
Build reaches the user unreviewed, and a tick that could notify would be the
first thing to do so.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# A recurring fault stops being noise and starts being evidence at three: one is
# an accident, two is a coincidence. The same bar sync_dev_backlog.py's
# ESCALATE_AT uses, and deliberately the same number — a capability failing three
# times and a machine signature recurring three times are the same judgement.
REPAIR_AT = 3

# How far back the REPAIR scan reads quality events. Long enough that three
# occurrences of a real fault can accumulate, short enough that a fault fixed a
# month ago cannot file a ticket about itself today.
REPAIR_WINDOW_DAYS = 14


def build_tick(persona: str | None = None) -> str:
    """The scheduler's entry point. `_DEFAULT_JOBS["build_tick"]` names this."""
    try:
        return _tick(persona)
    except Exception as exc:                        # pragma: no cover
        logger.warning("[build] tick failed: %s", exc)
        return f"build_tick: failed — {type(exc).__name__}: {exc}"


def _tick(persona: str | None) -> str:
    from core.build import registry as R

    built = R.capability_names()
    if not built:
        return "build_tick: nothing registered — no capability can be repaired yet"

    filed = repair_scan(persona, built)
    counts = R.refresh_run_counts(persona)

    lines = [f"{len(built)} capability(ies) registered", counts]
    if filed:
        lines.insert(0, f"REPAIR filed: {', '.join(filed)}")
    return "build_tick: " + " | ".join(lines)


def repair_scan(persona: str | None, built: set[str] | None = None) -> list[str]:
    """
    File a REPAIR ticket for any REGISTERED capability whose fault recurred x3.

    Returns the ticket ids filed, which is what the tick puts on its line.
    """
    from core.build import registry as R
    from core.build import tickets as T

    if built is None:
        built = R.capability_names()
    if not built:
        return []

    try:
        signature = _signature_fn()
    except Exception as exc:
        logger.warning("[build] REPAIR scan unavailable: %s", exc)
        return []

    counts, examples = _count_faults(persona, built, signature)

    filed: list[str] = []
    for key, count in counts.items():
        if count < REPAIR_AT:
            continue
        capability, sig = key.split("|", 1)
        try:
            row = T.file_ticket(
                # THE COUNT IS NOT IN THE GAP, and that is the whole point.
                # file_ticket() fingerprints mode|gap|capability_hint, so a gap
                # reading "…3 times…" hashes differently from the same fault at
                # 4 — every correction after the third would mint a NEW
                # fingerprint, escape the dedupe and file another ticket, and
                # nine more would fill max_proposed with one recurring fault.
                # The gap is the fault; the count is evidence and lives in
                # `trigger`, which is not fingerprinted.
                gap=(f"`{capability}` keeps answering wrongly on the same fault: "
                     f"{examples[key].get('detail', '')}"),
                trigger=(f"build_tick REPAIR scan — {sig} seen x{count} "
                         f"in {REPAIR_WINDOW_DAYS}d"),
                mode="repair", capability_hint=capability, persona=persona,
            )
            filed.append(f"{row['job_id']} (REPAIR {capability} x{count})")
        except T.TicketError:
            # Already filed, or the caps are full. Both are correct refusals and
            # neither is worth a line on the board every thirty minutes.
            continue
    return filed


def _count_faults(persona: str | None, built: set[str],
                  signature) -> tuple[Counter, dict[str, dict]]:
    """(capability|signature -> count, one example event per key)."""
    from core.persona import persona_data_dir

    events_path = persona_data_dir(persona) / "logs" / "quality_events.json"
    counts: Counter = Counter()
    examples: dict[str, dict] = {}
    if not events_path.exists():
        return counts, examples

    # NAIVE UTC, and it has to be. The comparison below is a STRING compare
    # against what tools/logger.py writes — `datetime.utcnow().isoformat() +
    # "Z"` — so a timezone-aware cutoff would carry a "+00:00" suffix and sort
    # against a "Z" suffix wrongly. `now(timezone.utc).replace(tzinfo=None)` is
    # the non-deprecated spelling of exactly the old value.
    cutoff = (datetime.now(timezone.utc).replace(tzinfo=None)
              - timedelta(days=REPAIR_WINDOW_DAYS)).isoformat()
    try:
        text = events_path.read_text(encoding="utf-8")
    except OSError:
        return counts, examples

    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if str(event.get("timestamp") or "") < cutoff:
            continue
        # source_agent may name several specialists — the correction attribution
        # writes a comma-joined list, because a turn can dispatch more than one
        # and blaming the first alphabetically would be a guess.
        agents = {a.strip() for a in str(event.get("source_agent") or "").split(",")}
        for capability in agents & built:
            key = f"{capability}|{signature(event)}"
            counts[key] += 1
            examples.setdefault(key, event)
    return counts, examples


def _signature_fn():
    """
    sync_dev_backlog.signature(), imported. scripts/ is not a package, so the
    path is added here rather than at module import — this module must load on a
    machine where the scripts directory is absent.
    """
    import sys
    from pathlib import Path
    scripts = Path(__file__).resolve().parent.parent.parent / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from sync_dev_backlog import signature
    return signature
