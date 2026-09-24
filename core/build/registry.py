"""
core/build/registry.py — what Build has actually shipped, and what it costs to run.

THE SHIPPED THING IS THE CAPABILITY, NOT THE FACTORY. Every other meter in this
package measures the BUILD: tokens per node, dollars per job, the tripwire. Those
end when the job does. A landed `kind: agent` is a specialist dispatched on every
matching turn, forever, at that turn's model price — and plan section 2 makes the
count growing the explicit goal. So the registry carries a RUN LINE per landed
capability, and scripts/check_build_registration.py fails a `landed` row without
one: a capability whose standing cost nothing meters is the shape of cost this
project's own rules say to name at the moment the parameter is chosen.

THE DISPATCH COUNT COMES FROM THE TRACE FILES, NOT FROM tools/analytics.py.
Plan section 14 said the A9 rollup "already counts dispatch per specialist" and it does
not: rollup_day() walks the trace through _walk_tools(), which counts TOOL names
into `top_tools`. Agent names are written on every AgentRecord (core/trace.py:353),
nested subagents included, and nothing counts them. Counting them here reads the
same files the rollup derives from and leaves A9's schema alone — that schema is
gated on a review dated 2026-10-01 whose first instruction is "do not review this
before there is real data", and adding a field for one number would have started
that review early on exactly the development traffic it says not to use.
(Correction v3.5 C1, plan section 14.)

Content-free, like everything else that counts: agent names, counts and dates. No
question text, no response text, no user content of any kind ever reaches a row.

APPEND-ONLY, REPLAYED — the same shape as jobs.py and for the same reason. There
is no status file. `capabilities()` replays the rows and the last write per
capability wins, so a re-landing after a REPAIR is a new row rather than an edit,
and the version history is the file.

docs/BUILD_REGISTRY.md is generated FROM this file, on the Mac, by
scripts/build_board.py --registry, and Mike commits it (ruling 0.2 — a tracked
file cannot be Build-written). It carries ids, kinds, names, versions and dates:
zero persona content.

Plan: archive/plans/build_vertical_plan_2026-09-18.md section 5, section 14
"""

from __future__ import annotations

import json
import os
import tempfile
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from core.build.jobs import registry_path
from core.persona import persona_data_dir

# How many days back `dispatch_counts()` reads when nothing narrower is asked
# for. Seven because the run line's job is to answer "is this thing actually
# being used", and one day of traces cannot distinguish a quiet Tuesday from a
# capability nothing routes to.
DEFAULT_WINDOW_DAYS = 7

# The tier's due condition (Mike, 2026-09-18): four leaf capabilities landed
# under the Coordinator. Carried here as well as in the plan because the board
# reports the count against it from run 1 onward, and a figure read off a plan
# is a figure that goes stale the session after the plan moves.
TIER_DUE_AT = 4


class RegistryError(RuntimeError):
    """A registry row could not be written."""


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

def _append(row: dict, persona: str | None = None) -> dict:
    """
    One row, appended atomically enough. Copies jobs.append_row's discipline:
    a single open/write/close under the default line-buffering, 0o600, parent
    created. The registry is small and written once per landing, so there is no
    lock here and none is needed — two landings cannot be in flight at once
    (max_open_jobs bounds work in flight, and N12 is single-threaded per tick).
    """
    path = registry_path(persona)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"at": datetime.now().isoformat(timespec="seconds"), **row}
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    os.chmod(path, 0o600)
    return row


def read_rows(persona: str | None = None) -> list[dict]:
    """
    Every well-formed row in written order. A torn line is skipped, not fatal —
    jobs.py's reason carries over verbatim: one bad write during a crash must
    not take every other capability down with it.
    """
    path = registry_path(persona)
    if not path.exists():
        return []
    rows: list[dict] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    for line in text.splitlines():
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


def record_landing(job_id: str, plan: dict, files: list[str],
                   persona: str | None = None,
                   dispatches_expected_per_day: float | None = None) -> dict:
    """
    Register a landed capability. Called by N14, after verification passed.

    The run line is built HERE rather than by the caller, so a landing cannot
    happen without one: check_build_registration.py asserts a `landed` row
    carries `run.execution_mode`, and the only way to be sure that assertion
    never fires is for the same function to write both.

    `dispatches_expected_per_day` is N8's figure, derived in code from how often
    the trigger fired in the traces that filed the gap. None means N8 could not
    tell — recorded as None rather than as 0, because "we could not count" and
    "it never fires" are different facts and the second is a verdict.
    """
    capability = (plan or {}).get("capability") or {}
    cap_id = str(capability.get("id") or "").strip()
    if not cap_id:
        raise RegistryError(
            f"{job_id}: the plan has no capability.id, so nothing can be "
            "registered under a name — refusing rather than inventing one"
        )

    mode = str(capability.get("execution_mode") or "").strip()
    budget = capability.get("latency_budget_ms")
    if not mode or not isinstance(budget, (int, float)):
        raise RegistryError(
            f"{job_id}: capability {cap_id!r} has no execution_mode or no "
            "latency_budget_ms — the run line cannot be written, and a landed "
            "row without one is a capability whose standing cost is unmetered"
        )

    return _append({
        "row_type": "capability",
        "state": "landed",
        "capability": cap_id,
        "job_id": job_id,
        "kind": str(capability.get("kind") or ""),
        "disposition": str(capability.get("disposition") or ""),
        "theme": str(capability.get("theme") or ""),
        "one_line": str(capability.get("one_line") or ""),
        "version": next_version(cap_id, persona),
        "files": sorted(str(f) for f in (files or [])),
        "replaces": [str(r) for r in (capability.get("replaces") or [])],
        # THE COHERENCE PASS'S ONLY VIEW OF WHAT A CAPABILITY CLAIMS. Without
        # it `_surface_of()` found nothing on the registry row and nothing on
        # the overlay record — which has no such field — so the corpus carried
        # `surface: []` for every capability and the OVERLAP detector could
        # never fire. Section 13.7's own falsifiable example, *"both claim
        # `create` on `plant_watering`"*, was the one comparison the pass was
        # structurally unable to make.
        #
        # Triples only: entity, operation, status. The `reason` is model prose
        # about a gap the user filed, and this row is read by render_markdown()
        # into a TRACKED file — so it stays out, the same rule that keeps
        # `one_line` out of the markdown.
        "surface_map": _surface_triples(plan),
        # THE RUN LINE. `dispatches_actual_per_day` is deliberately absent at
        # landing — no day has passed, and writing 0 would read as "nothing
        # routes to it" on the one day that cannot possibly show a dispatch.
        # refresh_run_counts() fills it once a day has closed.
        "run": {
            "execution_mode": mode,
            "latency_budget_ms": int(budget),
            "dispatches_expected_per_day": dispatches_expected_per_day,
            "dispatches_actual_per_day": None,
            "counted_over_days": None,
            "counted_at": None,
        },
    }, persona)


def _surface_triples(plan: dict) -> list[dict]:
    """The comparable part of a plan's surface map — no free text."""
    out = []
    for item in (plan or {}).get("surface_map") or []:
        if isinstance(item, dict) and item.get("entity") and item.get("operation"):
            out.append({"entity": str(item["entity"]),
                        "operation": str(item["operation"]),
                        "status": str(item.get("status") or "")})
    return out


def record_retirement(cap_id: str, job_id: str, reason: str,
                      persona: str | None = None) -> dict:
    """
    A capability that was reverted, superseded or promoted out of the overlay.

    Appended, never an edit to the landing row: the landing happened, and a
    registry that rewrote history could not answer "what was live on the day
    that trace was written".
    """
    return _append({
        "row_type": "capability",
        "state": "retired",
        "capability": str(cap_id),
        "job_id": str(job_id),
        "reason": str(reason or "")[:200],
    }, persona)


def next_version(cap_id: str, persona: str | None = None) -> int:
    """1 for a first landing, n+1 for a re-landing after a REPAIR."""
    seen = [r for r in read_rows(persona)
            if r.get("capability") == cap_id and r.get("state") == "landed"]
    return len(seen) + 1


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

def capabilities(persona: str | None = None,
                 live_only: bool = True) -> dict[str, dict]:
    """
    Capability name -> its latest row. Replayed, newest write wins.

    `live_only` drops anything whose latest row is a retirement — which is what
    the board, the coherence corpus and the tier count all want. Pass False to
    see the whole history's endpoints.
    """
    latest: dict[str, dict] = {}
    for row in read_rows(persona):
        if row.get("row_type") != "capability":
            continue
        name = str(row.get("capability") or "")
        if name:
            latest[name] = row
    if live_only:
        latest = {k: v for k, v in latest.items() if v.get("state") == "landed"}
    return latest


def leaf_count(persona: str | None = None) -> int:
    """
    Landed `kind: agent` capabilities registered directly under the Coordinator.

    This is the number the tier's due condition is read against. A capability
    with a `theme` is registered under a theme router and is NOT a leaf under
    Coord, so it does not count toward it — which is the whole point of the
    condition: four things hanging off Coord is when the routing decision starts
    scaling with capability count.
    """
    return sum(1 for row in capabilities(persona).values()
               if row.get("kind") == "agent" and not row.get("theme"))


def tier_status(persona: str | None = None) -> dict:
    """{'leaves': n, 'due_at': 4, 'due': bool} — what the board prints."""
    leaves = leaf_count(persona)
    return {"leaves": leaves, "due_at": TIER_DUE_AT, "due": leaves >= TIER_DUE_AT}


# ---------------------------------------------------------------------------
# Dispatch counting — from the traces, not from the A9 rollup
# ---------------------------------------------------------------------------

def _trace_files(persona: str | None, days: int) -> list[Path]:
    directory = persona_data_dir(persona) / "traces"
    if not directory.is_dir():
        return []
    today = date.today()
    names = [(today - timedelta(days=i)).isoformat() + ".jsonl"
             for i in range(max(1, days))]
    return [directory / name for name in names if (directory / name).exists()]


def _walk_agents(agents: Any, counter: Counter) -> None:
    """
    Every agent in a serialized pipeline, nested subagents included.

    The same walk core/trace.py:_walk_agents does over live records and
    tools/turn_referent.py:_walk does over written ones — a specialist is one
    level down from the Coordinator, so a top-level-only count would report zero
    for every specialist in the fleet.
    """
    for agent in agents or []:
        if not isinstance(agent, dict):
            continue
        name = str(agent.get("agent") or "")
        if name:
            counter[name] += 1
        _walk_agents(agent.get("subagents"), counter)


def _is_build_tick(record: dict) -> bool:
    """A Build tick's own trace: proactive, rooted at `build`."""
    pipeline = record.get("pipeline") or []
    return bool(pipeline) and str(pipeline[0].get("agent") or "") == "build"


def dispatch_counts(persona: str | None = None,
                    days: int = DEFAULT_WINDOW_DAYS,
                    after: str = "") -> tuple[Counter, int]:
    """
    (agent name -> dispatches, MEASURED days) over the window.

    Counts AGENT names, which no other counter in this repo does. Measured days
    is returned rather than assumed: a window of 7 across a VM stopped for four
    of them is a 3-day sample, and dividing by 7 would report a capability as
    less used than it is.

    TWO KINDS OF DAY DO NOT COUNT, and both were inflating the denominator into
    a figure of 0.0 that read as "nothing routes to it":

      · A DAY CONTAINING ONLY BUILD'S OWN TICKS. The tick writes a RequestTrace
        per run, so on the day a capability lands the trace file exists and
        holds exactly one record — Build's. Dividing by that gave `actual 0.0
        over 1d` on the landing day, which is a tick, not a day of use.
      · THE LANDING DAY ITSELF, via `after`. A capability that landed at 16:00
        cannot have a meaningful full-day rate from the remaining hours, and a
        partial day in the denominator always understates it.

    With no measured day the caller gets 0 and reports None — "we could not
    count" and "it never fires" stay different facts.
    """
    counter: Counter = Counter()
    measured = 0
    for path in _trace_files(persona, days):
        if after and path.stem <= after:
            continue                    # the landing day and anything before it
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        real_day = False
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if not isinstance(record, dict) or _is_build_tick(record):
                continue
            real_day = True
            _walk_agents(record.get("pipeline"), counter)
        if real_day:
            measured += 1
    return counter, measured


def refresh_run_counts(persona: str | None = None,
                       days: int = DEFAULT_WINDOW_DAYS) -> str:
    """
    Fill `dispatches_actual_per_day` on every live capability from the traces.

    Appends one refreshed row per capability rather than editing the landing
    row, keeping the file append-only. Idempotent in the sense that matters: two
    runs on the same day produce two rows with the same figure, and the replay
    reads the later one.

    Silent no-op when there is nothing landed — before the first landing there
    is nothing to count, and a refresh that wrote rows about an empty system
    would make the file's first entries meaningless.
    """
    live = capabilities(persona)
    if not live:
        return "registry: nothing landed — no run counts to refresh"

    refreshed, skipped = 0, 0
    stamp = date.today().isoformat()
    for name, row in sorted(live.items()):
        # PER CAPABILITY, because the window that matters starts the day AFTER
        # it landed. A shared window would put every capability's landing day —
        # a partial day whose trace file often holds only Build's own tick — in
        # its denominator, which is how `actual 0.0 over 1d` was written about a
        # capability nothing had yet had a chance to dispatch.
        landed_on = str(row.get("at", ""))[:10]
        counts, measured = dispatch_counts(persona, days, after=landed_on)
        if measured == 0:
            skipped += 1
            continue                    # leave `None` — not counted yet
        run = dict(row.get("run") or {})
        run["dispatches_actual_per_day"] = round(counts.get(name, 0) / measured, 3)
        run["counted_over_days"] = measured
        run["counted_at"] = stamp
        updated = {k: v for k, v in row.items() if k != "at"}
        updated["run"] = run
        _append(updated, persona)
        refreshed += 1

    if not refreshed:
        return (f"registry: no full day of use since landing — {skipped} count(s) "
                f"left uncounted rather than written as zero")
    return (f"registry: refreshed {refreshed} run count(s)"
            + (f", {skipped} with no full day since landing" if skipped else ""))


# ---------------------------------------------------------------------------
# The tracked board — generated on the Mac, committed by Mike
# ---------------------------------------------------------------------------

def render_markdown(persona: str | None = None) -> str:
    """
    docs/BUILD_REGISTRY.md's body. Ids, kinds, names, versions, dates.

    ZERO PERSONA CONTENT, and that is a hard property rather than a tidiness
    one: this is the only Build artifact that becomes a TRACKED file, so
    anything user-derived here would be committed to git, and the overlay's
    whole reason for living under data/personas/ is that generated capability
    text is Sensitive-tier. `one_line` is excluded for the same reason — it is
    model-written prose about a gap the user filed.
    """
    live = capabilities(persona)
    status = tier_status(persona)
    lines = [
        "# Build registry — what Build has landed",
        "",
        "*Generated by `python3 scripts/build_board.py --registry`. Do not edit by hand.*",
        "",
        "Ids, kinds, versions and dates only — no capability descriptions, no",
        "persona content. The descriptions live in the per-persona registry on the",
        "VM, which is gitignored because generated capability text is Sensitive-tier.",
        "",
        f"**Leaf capabilities under the Coordinator: {status['leaves']} of "
        f"{status['due_at']}.** The tier "
        + ("is DUE." if status["due"] else "becomes due at the fourth."),
        "",
    ]
    if not live:
        lines.append("Nothing has landed yet.")
        return "\n".join(lines) + "\n"

    lines += [
        "| Capability | Kind | Disposition | Theme | v | Mode | Budget | Landed |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name, row in sorted(live.items()):
        run = row.get("run") or {}
        lines.append(
            f"| `{name}` | {row.get('kind', '')} | {row.get('disposition', '')} "
            f"| {row.get('theme') or '—'} | {row.get('version', '')} "
            f"| {run.get('execution_mode', '')} "
            f"| {run.get('latency_budget_ms', '')}ms "
            f"| {str(row.get('at', ''))[:10]} |"
        )
    return "\n".join(lines) + "\n"


def write_markdown(target: Path | str, persona: str | None = None) -> str:
    """Write docs/BUILD_REGISTRY.md. Mac-side; Mike commits it."""
    path = Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = render_markdown(persona)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".",
                                    suffix=".tmp")
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        tmp.write_text(body, encoding="utf-8")
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return f"wrote {path} ({len(body.splitlines())} lines)"
