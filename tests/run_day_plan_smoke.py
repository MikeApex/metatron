"""
tests/run_day_plan_smoke.py — the day planner's Stage B smoke test (archive/plans/
day_planner_plan_2026-10-24.md § 11.3; Mike, F8: "a shorter test just to ensure everything is
working and then use real usage via mike persona as our determinant").

SPENDS REAL MONEY: each run is one Gemini call by the `day_planner` agent. It needs that agent's
file and routing entry (Stage B) to exist. It NEVER writes the plan: it builds today's code plan
in memory, asks the model to refine it N times against the real day, merges and validates each
reply exactly as the live worker would, and prints what it found:

  - validator failures and invented refs per run (pass = none)
  - churn between consecutive runs (pass = ≤ 3 task blocks moved)
  - latency, input / output / thinking tokens per call — thinking is unbounded on this path
    (plan § 5.7), so this is where its real size is first measured

Run on the VM, from the repo root:

    METATRON_LIVE=1 python3 tests/run_day_plan_smoke.py --persona mike --runs 3
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.support.live_gate import require_live  # noqa: E402


def _tokens(trace) -> dict:
    out = {"in": 0, "out": 0, "thinking": 0}
    stack = list(getattr(trace, "pipeline", []) or [])
    while stack:
        rec = stack.pop()
        if getattr(rec, "agent", "") == "day_planner":
            out["in"] += rec.total_input_tokens()
            out["out"] += rec.total_output_tokens()
            out["thinking"] += rec.total_thinking_tokens()
        stack.extend(getattr(rec, "subagents", []) or [])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona", required=True)
    ap.add_argument("--runs", type=int, default=3)
    args = ap.parse_args()

    from core import trace as _tr
    from core.persona import persona_scope
    import tools.day_plan as D

    ok = True
    with persona_scope(args.persona) as persona:
        day, now = D._today(), D._now()
        state = D._load_state(persona)
        events = D._events_for(state, day)
        if not events:
            print("no calendar snapshot for today — refreshing it first")
            D.refresh_snapshot(persona)
            state = D._load_state(persona)
            events = D._events_for(state, day)
        cands = D._candidates(day, persona)
        base = D._build(day, persona, "reshuffle", ["smoke test"], None, now, events, cands,
                        allow_lookup=False)
        print(f"{day}: {len(events)} calendar events, {len(cands)} candidates, code plan "
              f"{sum(1 for b in base['blocks'] if b['kind'] == 'task')} task blocks, "
              f"failures {base['failures'] or 'none'}")
        payload = D._payload(base, cands, now, state)
        refs = {c["ref"] for c in cands}
        prev_starts = None
        for i in range(1, args.runs + 1):
            _tr.start_request_trace(json.dumps(payload)[:200], persona, is_proactive=True,
                                    source="day_plan_smoke")
            t0 = time.monotonic()
            try:
                raw = D._call_model(payload, persona)
                err = ""
            except Exception as exc:  # noqa: BLE001
                raw, err = "", f"{type(exc).__name__}: {exc}"
            secs = time.monotonic() - t0
            toks = _tokens(_tr.get_trace())
            _tr.finish_request_trace(raw or err)
            result = D._extract_json(raw)
            if not isinstance(result, dict) or not isinstance(result.get("placements"), list):
                print(f"run {i}: UNPARSEABLE ({err or raw[:160]!r}) — {secs:.1f}s {toks}")
                ok = False
                continue
            keep = [{"ref": p.get("ref"), "start": str(p.get("start") or "")[:16]}
                    for p in result["placements"] if isinstance(p, dict) and p.get("ref") in refs]
            invented = [p.get("ref") for p in result["placements"]
                        if isinstance(p, dict) and p.get("ref") not in refs]
            dropped = {d.get("ref") for d in result.get("drop") or [] if isinstance(d, dict)}
            plan = D._build(day, persona, "reshuffle", ["smoke"], None, now, events,
                            [c for c in cands if c["ref"] not in dropped], allow_lookup=False,
                            _seed=keep)
            fails = D.validate(plan, events, [c for c in cands if c["ref"] not in dropped],
                               max(D._round_up(now), D._dt(plan["window"]["wake"])))
            starts = {b["ref"]: b["start"] for b in plan["blocks"] if b["kind"] == "task"}
            churn = (sum(1 for r in starts if r in prev_starts and prev_starts[r] != starts[r])
                     if prev_starts is not None else 0)
            prev_starts = starts
            verdict = "PASS" if not fails and not invented and churn <= 3 else "FAIL"
            ok = ok and verdict == "PASS"
            print(f"run {i}: {verdict} — {secs:.1f}s, tokens {toks}, {len(keep)} placements, "
                  f"{len(dropped)} dropped, invented {invented or 'none'}, churn {churn}, "
                  f"failures {fails or 'none'}; note: {str(result.get('note') or '')[:120]!r}")
    print("\nsmoke test " + ("PASSED" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    require_live()
    sys.exit(main())
