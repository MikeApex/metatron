#!/usr/bin/env python3
"""
scripts/session_shape_baseline.py — Stage 2's before/after figures, read-only (2026-11-23).

ONE-OFF, NOT STANDING MACHINERY. It is deleted in the commit that records the #4 decision
(whether the [CONTEXT] block moves to a function call). Plan:
archive/plans/instructions_to_code_stage2_session_shape_plan_2026-11-23.md § 1 #4 and M7.

Reads a persona's traces (data/personas/<p>/traces/YYYY-MM-DD.jsonl) and quality events
(data/personas/<p>/logs/quality_events.json) for a date window and prints, per persona:

  1. [CONTEXT] block health per Synthesizer reply — clean / repaired:<how> / partial salvage /
     unrecoverable / absent — beside the CONTEXT_BLOCK_UNPARSED event count (#4's number).
  2. Synthesizer tool rounds per reply, the share reaching _SYNTH_MAX_ROUNDS, CHAIN_LIMIT_REACHED
     events, run_subagent and write_quality_event tool calls per reply (#10, M11 baselines).
  3. M7's shadow figures from `annotations.clarification`; for traces written before that
     existed, the Coordinator's own CLARIFICATION_NEEDED line is parsed instead.
  4. Mental Wellbeing / Physical Health presence on scheduled morning-brief and day-close runs
     (#2's before-figure).

Counts and value shapes only — never the clarification text, which can carry names, and the
saved report lands in the repo. Writes nothing. Zero model tokens.

Usage (on the VM, read-only):
    python3 scripts/session_shape_baseline.py --persona mike --since 2026-11-16 --until 2026-11-23
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_SCHEDULED_KINDS = ("morning_brief", "evening_close")
_WHOLE_PERSON = ("mental_wellbeing", "physical_health")


def _walk(agents):
    for a in agents or []:
        yield a
        yield from _walk(a.get("subagents"))


def _days(since: date, until: date):
    d = since
    while d <= until:
        yield d
        d += timedelta(days=1)


def _read_traces(root: Path, persona: str, since: date, until: date) -> list[dict]:
    out = []
    tdir = root / "data" / "personas" / persona / "traces"
    for d in _days(since, until):
        p = tdir / f"{d.isoformat()}.jsonl"
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict):
                out.append(rec)
    return out


def _read_events(root: Path, persona: str, since: date, until: date) -> list[dict]:
    p = root / "data" / "personas" / persona / "logs" / "quality_events.json"
    if not p.exists():
        return []
    lo, hi = since.isoformat(), (until + timedelta(days=1)).isoformat()
    out = []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if isinstance(e, dict) and lo <= str(e.get("timestamp", ""))[:10] < hi:
            out.append(e)
    return out


def block_health(synth: dict) -> str:
    """One Synthesizer record's [CONTEXT] block, classified."""
    from core.orchestrator import _CONTEXT_CLOSE, _CONTEXT_OPEN, _repair_context_json
    texts = [t.get("output_text") or "" for t in synth.get("turns") or []]
    text = next((t for t in reversed(texts) if _CONTEXT_OPEN in t), None)
    if text is None:
        joined = "".join(texts)
        text = joined if _CONTEXT_OPEN in joined else None
    if text is None:
        return "absent"
    raw = text[text.index(_CONTEXT_OPEN) + len(_CONTEXT_OPEN):]
    if _CONTEXT_CLOSE in raw:
        raw = raw[:raw.index(_CONTEXT_CLOSE)]
    parsed, how = _repair_context_json(raw)
    if parsed is None:
        return "unrecoverable"
    if how == "clean":
        return "clean"
    if how.startswith("partial salvage"):
        return "partial salvage"
    return f"repaired:{how}"


def _clarification(trace: dict) -> dict | None:
    """The shadow annotation, or one rebuilt from the Coordinator's output (pre-deploy)."""
    ann = (trace.get("annotations") or {}).get("clarification")
    if ann:
        return ann
    from core.orchestrator import _clarification_line, _clarification_shape
    for a in _walk(trace.get("pipeline")):
        if a.get("agent") != "coordinator":
            continue
        text = "".join(t.get("output_text") or "" for t in a.get("turns") or [])
        value = _clarification_line(text)
        if value is not None:
            return {"value_shape": _clarification_shape(value), "chars": len(value),
                    "user_turn": not trace.get("is_proactive"), "would_hold": None,
                    "synth_redispatched": None, "fallback": True}
    return None


def report(root: Path, persona: str, since: date, until: date) -> str:
    traces = _read_traces(root, persona, since, until)
    events = _read_events(root, persona, since, until)
    from core.orchestrator import _SYNTH_MAX_ROUNDS

    health: Counter = Counter()
    rounds: list[int] = []
    subagent_calls = qe_calls = at_cap = 0
    clar_shapes: Counter = Counter()
    user_turns = clar_pass = 0
    hold_sizes: list[int] = []
    redispatched = measured = fallback = 0
    sched_runs: Counter = Counter()
    sched_present: Counter = Counter()

    for tr in traces:
        synths = [a for a in _walk(tr.get("pipeline")) if a.get("agent") == "synthesizer"]
        for s in synths[:1]:
            health[block_health(s)] += 1
            tool_turns = [t for t in s.get("turns") or [] if t.get("tool_calls")]
            rounds.append(len(tool_turns))
            at_cap += len(tool_turns) >= _SYNTH_MAX_ROUNDS
            for t in tool_turns:
                for c in t["tool_calls"]:
                    subagent_calls += c.get("name") == "run_subagent"
                    qe_calls += c.get("name") == "write_quality_event"
        if not tr.get("is_proactive"):
            user_turns += 1
        ann = _clarification(tr)
        if ann:
            clar_shapes[ann.get("value_shape")] += 1
            fallback += bool(ann.get("fallback"))
            if ann.get("user_turn") and ann.get("value_shape") == "free text":
                clar_pass += 1
            if ann.get("would_hold") is not None and ann.get("value_shape") == "free text":
                measured += 1
                hold_sizes.append(len(ann["would_hold"]))
                redispatched += bool(ann.get("synth_redispatched"))
        if tr.get("is_proactive"):
            try:
                from core.orchestrator import session_kind
                kind = session_kind(tr.get("user_input") or "", persona)
            except Exception:  # noqa: BLE001 — a persona without a scheduler file
                kind = None
            if kind in _SCHEDULED_KINDS:
                sched_runs[kind] += 1
                names = {a.get("agent") for a in _walk(tr.get("pipeline"))}
                for agent in _WHOLE_PERSON:
                    sched_present[(kind, agent)] += agent in names

    ev = Counter(e.get("event_type") for e in events)
    n = len(rounds)
    lines = [f"## {persona} — {since.isoformat()} to {until.isoformat()}",
             f"traces: {len(traces)}  synthesizer replies: {n}", "",
             "### 1. [CONTEXT] block health"]
    for k in sorted(health):
        lines.append(f"- {k}: {health[k]}")
    lossy = health["partial salvage"] + health["unrecoverable"]
    lines.append(f"- lossy (partial salvage + unrecoverable): {lossy} of {n}"
                 + (f" ({100 * lossy / n:.1f}%)" if n else ""))
    lines.append(f"- CONTEXT_BLOCK_UNPARSED events: {ev['CONTEXT_BLOCK_UNPARSED']}")
    lines += ["", "### 2. Synthesizer tool rounds"]
    lines.append(f"- mean tool rounds per reply: {sum(rounds) / n:.2f}" if n else "- no replies")
    lines.append(f"- replies reaching {_SYNTH_MAX_ROUNDS} rounds: {at_cap}")
    lines.append(f"- CHAIN_LIMIT_REACHED events: {ev['CHAIN_LIMIT_REACHED']}")
    lines.append(f"- run_subagent calls per reply: {subagent_calls / n:.2f}" if n else "")
    lines.append(f"- write_quality_event calls per reply: {qe_calls / n:.2f}" if n else "")
    lines.append(f"- ROUTING_MISS events: {ev['ROUTING_MISS']} "
                 f"(tagged scheduled: {sum(1 for e in events if e.get('scheduled'))})")
    lines += ["", "### 3. CLARIFICATION_NEEDED (M7 shadow)"]
    lines.append(f"- user turns: {user_turns}; passing the parser: {clar_pass}"
                 + (f" ({100 * clar_pass / user_turns:.1f}%)" if user_turns else ""))
    for k in sorted(s for s in clar_shapes if s):
        lines.append(f"- shape {k}: {clar_shapes[k]}")
    lines.append(f"- read from the Coordinator output (pre-annotation): {fallback}")
    if hold_sizes:
        lines.append(f"- mean would_hold size: {sum(hold_sizes) / len(hold_sizes):.2f}")
        lines.append(f"- with synth_redispatched non-empty: {redispatched} of {measured}")
    lines += ["", "### 4. Whole-person presence on scheduled sessions"]
    for kind in _SCHEDULED_KINDS:
        lines.append(f"- {kind}: {sched_runs[kind]} runs; "
                     + ", ".join(f"{a} {sched_present[(kind, a)]}" for a in _WHOLE_PERSON))
    return "\n".join(x for x in lines if x is not None) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--persona", action="append", required=True)
    ap.add_argument("--since", required=True, type=date.fromisoformat)
    ap.add_argument("--until", default=date.today().isoformat(), type=date.fromisoformat)
    ap.add_argument("--root", default=str(ROOT), help="repo root (tests only)")
    args = ap.parse_args(argv)
    for p in args.persona:
        print(report(Path(args.root), p, args.since, args.until))
    return 0


if __name__ == "__main__":
    sys.exit(main())
