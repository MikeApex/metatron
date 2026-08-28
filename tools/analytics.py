"""
tools/analytics.py — product analytics rollup (ROADMAP.md § A9).

WHY THIS EXISTS, AND WHY THE SHAPE IS WHAT IT IS
Mike, 2026-08-18: *"We want to be able to measure and quantify usage FROM THE
START."* That is a sequencing constraint. Alpha is defined as the moment data
accumulation begins, so instrumentation added afterwards permanently loses the
weeks that matter most. Collection already existed (core/trace.py records the
agent path, per-turn tokens, every tool call, and is_proactive); what did not
exist was anything durable. Traces are per-day and prunable, so nothing was
actually answerable from them.

THE CORE METRIC IS ABSORBED WORK, NOT ENGAGEMENT — and this inverts the usual reading.
Asked to name one "core action", Mike rejected the framing: *"The more items that
Metatron handled where the user didn't have to is the core metric... A user should
go through life seamlessly and NOT need to open their phone nearly as often."*

So sessions and user turns are **attention costs, the denominator** — not value.
A rollup treating rising engagement as success would measure the opposite of the
product thesis. The headline is absorbed actions per unit of user attention.

WHAT COUNTS AS ABSORBED (_WORLD_AFFECTING below): a tool call with a real-world
effect the user would otherwise have performed. Internal bookkeeping — write_log,
write_journal, write_wisdom, context-tracker writes — is the system talking to
itself; counting it would inflate the headline with housekeeping. Reads never count.

AUTONOMY TIERS, and an honest limit. T3 (autonomous) is a world-affecting call in
a proactive-origin trace: it cost the user nothing. Everything else is currently
"user present". **T2 (user approved via the confirm gate) cannot yet be separated
from T1 (user directed)**, because ToolCallRecord carries no confirm marker — see
`absorbed_user_present` and [DB-0818-03]. That split is not faked here; a field
that looks precise and isn't is worse than a field that admits its resolution.

EVERY ROW IS COUNTS-ONLY AND CONTENT-FREE. No question text, no response text, no
names, no free text of any kind — only counts, durations, ids and dates. This is
not politeness: § Section 0 forbids personal data leaving the box, and an
eventual *opt-in* aggregate upload for an alpha cohort is only a small gated build
if the schema was content-free from the first line. Otherwise it is a migration
against data that cannot be re-derived.

ROWS ARE APPEND-ONLY AND KEPT FOREVER. Never windowed, compacted or overwritten.
They are a few hundred bytes each and they are the entire asset. cohort_day is the
field that cannot be reconstructed later, which is why first_use is pinned once in
a state file rather than recomputed from whatever traces still happen to exist.
"""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Real-world effects the user would otherwise have done themselves. Deliberately
# short: every addition raises the headline metric, so it is a decision, not a tidy-up.
_WORLD_AFFECTING = {
    "send_email",
    "write_calendar_event", "update_calendar_event", "delete_calendar_event",
    "write_schedule", "delete_schedule",
    "open_obligation", "close_obligation", "reopen_obligation",
    "import_contacts_file",
}

# Named explicitly rather than inferred, so that adding a bookkeeping tool later
# cannot silently start counting as absorbed work.
_INTERNAL = {
    "write_log", "write_journal", "write_wisdom", "write_context_tracker",
    "write_quality_event", "write_archive", "write_agent_config", "write_profile",
    "write_persona", "write_goals", "update_goal", "write_config",
}


def _persona_dir(persona: str) -> Path:
    return ROOT / "data" / "personas" / persona


def _analytics_dir(persona: str) -> Path:
    d = _persona_dir(persona) / "analytics"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _first_use(persona: str) -> str:
    """
    The cohort anchor. Pinned once and never recomputed — deriving it from surviving
    traces would silently move it forward every time an old file is pruned, which
    would quietly destroy every retention curve built on it.
    """
    state = _analytics_dir(persona) / "cohort.json"
    if state.exists():
        try:
            return json.loads(state.read_text())["first_use"]
        except (ValueError, KeyError):
            pass
    traces = sorted((_persona_dir(persona) / "traces").glob("*.jsonl"))
    first = traces[0].stem if traces else date.today().isoformat()
    state.write_text(json.dumps({"first_use": first, "pinned_on": date.today().isoformat()}, indent=2))
    return first


def _walk_tools(agents, tools: Counter, failures: Counter) -> None:
    for a in agents or []:
        for turn in a.get("turns") or []:
            for call in turn.get("tool_calls") or []:
                name = call.get("name")
                tools[name] += 1
                if not call.get("ok", True):
                    failures[name] += 1
        _walk_tools(a.get("subagents"), tools, failures)


def rollup_day(day: str, persona: str) -> dict | None:
    """Build one content-free daily row from that day's traces. None if no traces."""
    tf = _persona_dir(persona) / "traces" / f"{day}.jsonl"
    if not tf.exists():
        return None

    tools, failures = Counter(), Counter()
    sessions = user_sessions = proactive_sessions = 0
    absorbed_t3 = absorbed_user_present = 0
    tokens_in = tokens_out = 0
    wall_ms = user_wall_ms = 0

    for line in tf.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue

        sessions += 1
        proactive = bool(rec.get("is_proactive"))
        dur = int(rec.get("duration_ms") or 0)
        wall_ms += dur
        if proactive:
            proactive_sessions += 1
        else:
            user_sessions += 1
            user_wall_ms += dur

        before = sum(tools.values())
        t_before = Counter(tools)
        _walk_tools(rec.get("pipeline"), tools, failures)
        # world-affecting calls added by this record
        added = tools - t_before
        world = sum(c for n, c in added.items() if n in _WORLD_AFFECTING)
        if proactive:
            absorbed_t3 += world
        else:
            absorbed_user_present += world

        for a in rec.get("pipeline") or []:
            for turn in a.get("turns") or []:
                tokens_in += int(turn.get("input_tokens") or 0)
                tokens_out += int(turn.get("output_tokens") or 0)

    absorbed_total = absorbed_t3 + absorbed_user_present
    first = _first_use(persona)
    cohort_day = (date.fromisoformat(day) - date.fromisoformat(first)).days

    # DB-0827-09 Accountability Index — content-free counts only (no intention
    # text, no names, no dates beyond `day` itself). tools/accountability.py
    # owns the join logic and the content-free discipline; this rollup only
    # asks for the day's counts. Never raises — an accountability read failure
    # must not take down the whole analytics row, matching rollup_yesterday's
    # own never-crash-the-daemon discipline.
    try:
        from tools.accountability import daily_accountability_counts
        acct = daily_accountability_counts(day, persona, root=ROOT)
    except Exception:
        acct = {"intentions_stated": 0, "intentions_resolved_fulfilled": 0,
                "intentions_resolved_unfulfilled": 0, "intentions_resolved_indeterminate": 0}

    return {
        # --- cohort anchor: the fields that cannot be reconstructed later ---
        "date": day,
        "user_id": persona,
        "first_use": first,
        "cohort_day": cohort_day,
        # --- absorbed work: the headline ---
        "absorbed_total": absorbed_total,
        "absorbed_t3_autonomous": absorbed_t3,
        "absorbed_user_present": absorbed_user_present,  # T1+T2; see module docstring
        "absorbed_per_user_session": round(absorbed_total / user_sessions, 3) if user_sessions else None,
        "absorbed_per_user_minute": round(absorbed_total / (user_wall_ms / 60000), 3) if user_wall_ms else None,
        # --- attention: the DENOMINATOR, not a success measure ---
        "sessions": sessions,
        "user_sessions": user_sessions,
        "proactive_sessions": proactive_sessions,
        "user_wall_ms": user_wall_ms,
        "wall_ms": wall_ms,
        # --- breadth and reliability ---
        "tool_calls": sum(tools.values()),
        "tools_used": len(tools),
        "tool_failures": sum(failures.values()),
        "top_tools": dict(tools.most_common(15)),
        "failed_tools": dict(failures),
        # --- accountability (DB-0827-09): counts only, re-derivable from data/personas/*/logs ---
        "intentions_stated": acct["intentions_stated"],
        "intentions_resolved_fulfilled": acct["intentions_resolved_fulfilled"],
        "intentions_resolved_unfulfilled": acct["intentions_resolved_unfulfilled"],
        "intentions_resolved_indeterminate": acct["intentions_resolved_indeterminate"],
        # --- cost: gross margin, not performance telemetry ---
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
    }


def write_rollup(day: str, persona: str) -> str:
    """Append one row. Idempotent per (date, user): a rerun replaces that day only."""
    row = rollup_day(day, persona)
    if row is None:
        return f"analytics: no traces for {day}"
    path = _analytics_dir(persona) / "daily.jsonl"
    kept = []
    if path.exists():
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if not (r.get("date") == day and r.get("user_id") == persona):
                kept.append(r)
    kept.append(row)
    kept.sort(key=lambda r: r.get("date", ""))
    tmp = path.with_suffix(".tmp")
    tmp.write_text("\n".join(json.dumps(r) for r in kept) + "\n")
    tmp.replace(path)
    return (f"analytics {day}: absorbed {row['absorbed_total']} "
            f"(T3 {row['absorbed_t3_autonomous']}), {row['user_sessions']} user sessions, "
            f"cohort day {row['cohort_day']}")


def backfill(persona: str) -> str:
    """Roll up every day with traces. Safe to rerun — write_rollup replaces per day."""
    tdir = _persona_dir(persona) / "traces"
    days = sorted(p.stem for p in tdir.glob("*.jsonl")) if tdir.exists() else []
    for d in days:
        write_rollup(d, persona)
    return f"analytics: backfilled {len(days)} days for {persona}"


def rollup_yesterday() -> str:
    """
    Scheduler entry point. Takes no arguments; persona comes from the scope, matching
    tools/rule_audit.audit_rules.

    Never raises. This runs unattended in a daemon, and an analytics job that
    crash-loops the scheduler would cost far more than the measurement is worth —
    the same reasoning rule_audit records. Yesterday rather than today, so the day
    it rolls up is closed.
    """
    try:
        from core.persona import resolve_persona
        persona = resolve_persona(None)
        return write_rollup((date.today() - timedelta(days=1)).isoformat(), persona)
    except Exception as exc:  # noqa: BLE001 - unattended daemon, see docstring
        return f"analytics: rollup skipped ({type(exc).__name__}: {exc})"


def report(persona: str, days: int = 28) -> str:
    """The weekly table. Deliberately not a dashboard — a dashboard postpones answers."""
    path = _analytics_dir(persona) / "daily.jsonl"
    if not path.exists():
        return "analytics: no rollup yet — run with --backfill"
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()][-days:]
    if not rows:
        return "analytics: no rows"

    out = [f"{'date':11} {'coh':>4} {'absorb':>7} {'T3':>4} {'usess':>6} {'/sess':>6} {'tools':>6} {'fail':>5}"]
    for r in rows:
        ps = r.get("absorbed_per_user_session")
        out.append(f"{r['date']:11} {r.get('cohort_day',0):>4} {r.get('absorbed_total',0):>7} "
                   f"{r.get('absorbed_t3_autonomous',0):>4} {r.get('user_sessions',0):>6} "
                   f"{(f'{ps:.2f}' if ps is not None else '-'):>6} "
                   f"{r.get('tool_calls',0):>6} {r.get('tool_failures',0):>5}")

    absorbed = sum(r.get("absorbed_total", 0) for r in rows)
    t3 = sum(r.get("absorbed_t3_autonomous", 0) for r in rows)
    usess = sum(r.get("user_sessions", 0) for r in rows)
    active = sum(1 for r in rows if r.get("sessions"))
    tin = sum(r.get("tokens_in", 0) for r in rows)
    tout = sum(r.get("tokens_out", 0) for r in rows)
    out += [
        "",
        f"{len(rows)} days, {active} active.",
        f"ABSORBED {absorbed} ({t3} fully autonomous) — the headline: work the user did not do.",
        f"ATTENTION {usess} user sessions — the denominator. Falling while absorbed rises is the goal.",
        f"per user session: {absorbed/usess:.2f}" if usess else "per user session: n/a",
        f"tokens {tin:,} in / {tout:,} out over {active} active days"
        + (f" — {(tin+tout)/active:,.0f}/active day" if active else ""),
    ]
    return "\n".join(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="A9 product analytics rollup")
    ap.add_argument("--persona", default=os.environ.get("METATRON_PERSONA", "mike"))
    ap.add_argument("--backfill", action="store_true", help="roll up every day that has traces")
    ap.add_argument("--day", help="roll up one day (YYYY-MM-DD); default yesterday")
    ap.add_argument("--report", action="store_true", help="print the table")
    ap.add_argument("--days", type=int, default=28)
    a = ap.parse_args()
    if a.backfill:
        print(backfill(a.persona))
    elif a.day or not a.report:
        print(write_rollup(a.day or (date.today() - timedelta(days=1)).isoformat(), a.persona))
    if a.report:
        print(report(a.persona, a.days))
