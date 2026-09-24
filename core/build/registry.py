"""
core/build/registry.py — the TRACKED state. config/build/registry.yaml.

Plan: archive/plans/build_vertical_plan_2026-09-24.md sections 4, 5.

ONE ROW PER CAPABILITY, COMMITTED WITH IT. That is the whole reason this file
is tracked rather than persona-scoped state: the capability and the fact that it
exists arrive on the VM in the same deploy, so nothing can ever be running that
the registry does not know about, and nothing can be in the registry that is not
deployed. Every disagreement the two-state-homes risk (section 13.8) names is
closed by that one property.

TWO STATUSES, AND THE SPLIT IS LOAD-BEARING (cold read 2).

  staged   written by the IMPLEMENTER, in the sandbox worktree, at N11.
  landed   flipped by the MAIN SESSION at N13, once the Red half is in the tree.

`scripts/check_build_registration.py` asserts routing parity, the Coordinator
directory entry, the agent file and the knowledge domain ONLY FOR `landed`
ROWS. That is how ONE script passes in a sandbox that by design holds no wiring
and fails in a main tree that is missing some. Without the split the same script
would have to be either too weak for the main tree or impossible in the sandbox.

THE RUN LINE IS NOT DECORATION. The shipped thing is the capability, not the
factory: a landed agent is dispatched on every matching turn, forever, at that
turn's model price. A landed row with no run line is a capability whose standing
cost nothing meters, which is precisely the class CLAUDE.md § Costs calls
"Unseen". `expected` and `actual` start None and are filled from the traces.

YAML, not JSONL, and tracked, so Mike reads it in the same diff as the code.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent.parent

REGISTRY_PATH = _ROOT / "config" / "build" / "registry.yaml"

STATUSES: tuple[str, ...] = ("staged", "landed", "abandoned", "retired")

# Rows whose wiring must exist in the tree. `staged` is deliberately absent.
WIRED_STATUSES: frozenset[str] = frozenset({"landed"})

DEFAULT_WINDOW_DAYS = 7

# The tier review is due at four LEAF capabilities — four things the Coordinator
# must choose between before a second routing layer earns its latency.
TIER_DUE_AT = 4


class RegistryError(RuntimeError):
    """The registry could not be read or written."""


# ---------------------------------------------------------------------------
# IO
# ---------------------------------------------------------------------------

def _load(path: Path | None = None) -> dict:
    import yaml
    target = path or REGISTRY_PATH
    if not target.exists():
        return {"schema": "build_registry/1", "capabilities": []}
    try:
        parsed = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise RegistryError(f"{target}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise RegistryError(f"{target}: not a mapping")
    parsed.setdefault("capabilities", [])
    return parsed


def rows(path: Path | None = None) -> list[dict]:
    """Every capability row. Order is the file's order, which is landing order."""
    return [r for r in _load(path).get("capabilities") or [] if isinstance(r, dict)]


def row_for(name: str, path: Path | None = None) -> dict | None:
    for row in rows(path):
        if str(row.get("name")) == str(name):
            return row
    return None


def rows_by_ticket(path: Path | None = None) -> dict[str, tuple[str, str]]:
    """
    ticket id -> (status, timestamp). What tickets.duplicate_of() deduplicates
    against, and the only thing the VM reads from this file.
    """
    out: dict[str, tuple[str, str]] = {}
    for row in rows(path):
        ticket = str(row.get("ticket") or "")
        if ticket:
            out[ticket] = (str(row.get("status") or ""), str(row.get("at") or ""))
    return out


def write(document: dict, path: Path | None = None) -> Path:
    """
    Write the whole document. TRACKED, so no atomic dance and no 0600: this is
    a file Mike reads in a diff, and a mode nobody else in config/ carries would
    be noise that outlives the reason for it.
    """
    import yaml
    target = path or REGISTRY_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        yaml.safe_dump(document, sort_keys=False, allow_unicode=True,
                       default_flow_style=False),
        encoding="utf-8")
    return target


def upsert(row: dict, path: Path | None = None) -> dict:
    """
    Insert or replace one capability row by name.

    REPLACE, not append. The VM's ticket file is append-only because it is a
    log; this is STATE, it is tracked, and a second row for the same capability
    would show up in Mike's diff as a duplicate he has to reason about.
    """
    name = str(row.get("name") or "")
    if not name:
        raise RegistryError("a registry row needs a name")
    status = str(row.get("status") or "")
    if status not in STATUSES:
        raise RegistryError(f"status must be one of {list(STATUSES)}, got {status!r}")

    document = _load(path)
    existing = document.get("capabilities") or []
    replaced = False
    out = []
    for current in existing:
        if isinstance(current, dict) and str(current.get("name")) == name:
            out.append(row)
            replaced = True
        else:
            out.append(current)
    if not replaced:
        out.append(row)
    document["capabilities"] = out
    write(document, path)
    return row


def new_row(name: str, kind: str, ticket: str, job_id: str, persona: str,
            execution_mode: str, latency_budget_ms: int,
            status: str = "staged", version: int = 1) -> dict:
    """
    A fresh row, with the run line present and EMPTY.

    `expected` and `actual` are None from the start rather than absent. An
    absent key reads as "this row predates the run line"; an explicit None reads
    as "nothing has been counted yet", which is the true statement and the one
    check_build_registration.py can assert.
    """
    return {
        "name": name,
        "kind": kind,
        "ticket": ticket,
        "job_id": job_id,
        "persona": persona,
        "version": int(version),
        "status": status,
        "at": date.today().isoformat(),
        "acceptance": None,
        "run": {
            "execution_mode": execution_mode,
            "latency_budget_ms": int(latency_budget_ms),
            "dispatches_expected_per_day": None,
            "dispatches_actual_per_day": None,
            "counted_over_days": None,
            "counted_at": None,
        },
    }


def mark_landed(name: str, path: Path | None = None) -> dict:
    """
    `staged` -> `landed`. THE MAIN SESSION'S CALL, at N13, and only there.

    This is the moment the registration checker starts asserting wiring for
    this capability — so it must not happen until the Red half is in the same
    tree, which is exactly what N13 is.
    """
    row = row_for(name, path)
    if row is None:
        raise RegistryError(f"no registry row for {name!r}")
    if row.get("status") not in {"staged", "landed"}:
        raise RegistryError(
            f"{name} is {row.get('status')!r} — only a staged row lands")
    updated = {**row, "status": "landed", "at": date.today().isoformat()}
    return upsert(updated, path)


def mark_abandoned(ticket: str, reason: str, persona: str,
                   path: Path | None = None) -> dict:
    """
    A ticket Mike closed without building. Carries the reason, because an
    abandoned row with no reason is indistinguishable from a lost one.
    """
    return upsert({
        "name": f"abandoned_{ticket.lower().replace('-', '_')}",
        "kind": "none",
        "ticket": ticket,
        "job_id": ticket,
        "persona": persona,
        "version": 0,
        "status": "abandoned",
        "at": date.today().isoformat(),
        "reason": str(reason or "").strip() or "no reason recorded",
        "acceptance": None,
        "run": None,
    }, path)


# ---------------------------------------------------------------------------
# Reading the set
# ---------------------------------------------------------------------------

def capabilities(path: Path | None = None,
                 statuses: frozenset[str] = WIRED_STATUSES) -> dict[str, dict]:
    """Live capability rows by name. `landed` only, unless asked otherwise."""
    return {str(r["name"]): r for r in rows(path)
            if str(r.get("status")) in statuses and r.get("name")}


def capability_names(path: Path | None = None) -> set[str]:
    return set(capabilities(path))


def leaf_count(path: Path | None = None) -> int:
    """Landed capabilities the Coordinator must choose between."""
    return sum(1 for r in capabilities(path).values()
               if str(r.get("kind")) in {"agent", "tool"})


def tier_status(path: Path | None = None) -> dict:
    count = leaf_count(path)
    return {"leaves": count, "due_at": TIER_DUE_AT, "due": count >= TIER_DUE_AT}


def next_version(name: str, path: Path | None = None) -> int:
    row = row_for(name, path)
    return int(row.get("version", 0)) + 1 if row else 1


# ---------------------------------------------------------------------------
# Dispatch counting — from the traces, not from the A9 rollup
# ---------------------------------------------------------------------------
#
# SALVAGED IN BEHAVIOUR from the v3 registry: the walk, the two kinds of day
# that do not count, and the None-not-zero rule are unchanged, because all three
# were bought by a real wrong number on the board.

def _trace_files(persona: str | None, days: int) -> list[Path]:
    from core.persona import persona_data_dir
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
                       days: int = DEFAULT_WINDOW_DAYS,
                       path: Path | None = None) -> str:
    """
    Fill `dispatches_actual_per_day` on every landed capability from the traces.

    Rewrites the row in place — the registry is tracked state, not a log, and
    an append would show Mike a second row for the same capability.

    Silent no-op when nothing has landed: before the first landing there is
    nothing to count, and a refresh that wrote rows about an empty system would
    make the file's first entries meaningless.
    """
    live = capabilities(path)
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
        counts, measured = dispatch_counts(persona, days,
                                           after=str(row.get("at", ""))[:10])
        if measured == 0:
            skipped += 1
            continue                    # leave None — not counted yet
        run = dict(row.get("run") or {})
        run["dispatches_actual_per_day"] = round(counts.get(name, 0) / measured, 3)
        run["counted_over_days"] = measured
        run["counted_at"] = stamp
        upsert({**row, "run": run}, path)
        refreshed += 1

    if not refreshed:
        return (f"registry: no full day of use since landing — {skipped} count(s) "
                f"left uncounted rather than written as zero")
    return (f"registry: refreshed {refreshed} run count(s)"
            + (f", {skipped} with no full day since landing" if skipped else ""))


# ---------------------------------------------------------------------------
# The tracked board
# ---------------------------------------------------------------------------

def render_markdown(path: Path | None = None) -> str:
    """docs/BUILD_REGISTRY.md, generated. One table, no prose beyond the header."""
    lines = [
        "# Build registry — what Build has made",
        "",
        "*Generated from `config/build/registry.yaml`. Do not edit by hand — the",
        "sweep rewrites it.*",
        "",
        "| Capability | Kind | Status | v | Ticket | Landed | Acceptance | Run |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in rows(path):
        run = row.get("run") or {}
        actual = run.get("dispatches_actual_per_day")
        run_cell = (f"{run.get('execution_mode', '?')}, "
                    f"{'not counted' if actual is None else f'{actual}/day'}"
                    ) if run else "—"
        lines.append(
            f"| `{row.get('name', '?')}` | {row.get('kind', '?')} "
            f"| {row.get('status', '?')} | {row.get('version', '?')} "
            f"| {row.get('ticket', '?')} | {row.get('at', '?')} "
            f"| {row.get('acceptance') or '—'} | {run_cell} |")
    if len(lines) == 7:
        lines.append("| *(nothing yet)* | | | | | | | |")
    return "\n".join(lines) + "\n"


def write_markdown(target: Path | str | None = None,
                   path: Path | None = None) -> str:
    out = Path(target) if target else (_ROOT / "docs" / "BUILD_REGISTRY.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    text = render_markdown(path)
    out.write_text(text, encoding="utf-8")
    return text
