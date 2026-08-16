#!/usr/bin/env python3
"""
The knowledge-layer routing gate — Pass A and Pass B, which only mean anything together.

Pass A (retrieval): a message answerable from a standing fact loads that subject and the fact
reaches the response. Pass B (counter-test): a message that RECORDS something still dispatches
the specialist. A run where A passes and B fails has not fixed over-dispatch — it has traded it
for under-dispatch, which is the worse failure and the only one a user notices as data going
missing. Neither result is reportable alone.

WHAT PASS A DELIBERATELY DOES NOT ASSERT, measured 2026-08-16: that the specialist is skipped.
The plan's founding example wanted "thinking about changing up breakfast" to reach the stored
breakfast fact with NO physical_health dispatch. It does reach the fact — but PH is dispatched
anyway, on two runs, the second after an explicit worked example was added to coordinator.md
and then reverted for changing nothing. The Coordinator is not misbehaving: coordinator.md's
advice-and-suggestions rule mandates dispatch, and that rule is deliberately left dominant
because over-dispatch costs tokens while under-dispatch loses a user's record. Asserting the
skip here would mean tuning the routing until this gate goes green, in the one direction the
counter-test exists to prevent. The value delivered is retrieval, and retrieval is what is
gated. Re-open this only with a way to prove Pass B survives the change.

Drives run_pipeline_session_stream() — the path the server actually uses — rather than the
non-streaming variant, because a feature wired into one and not the other is live in tests and
dead in production.

Usage:
    python tests/run_knowledge_routing.py [--persona danny_park]

Requires a persona whose wisdom store has entries on the `domain` axis; a store still on the
legacy `category` field renders no manifest and the Coordinator has nothing to select.
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import orchestrator as orch  # noqa: E402
from core.persona import persona_scope  # noqa: E402
from tools.wisdom import domains_present  # noqa: E402

CASES = [
    {
        "name": "Pass A — the stored fact reaches the answer",
        "message": "thinking about changing up breakfast",
        "expect_domains": ["food"],
        # Any-of, not all-of: the point is that the response is grounded in something on file
        # rather than generic breakfast advice, and which fact it leans on is the model's call.
        # An exact-phrase assertion would fail on paraphrase and prove nothing about grounding.
        "expect_reply_any": ["egg", "toast", "v60", "coffee", "lunch", "8:30"],
        "why": "answerable from a fact already on file; the fact must actually be used",
    },
    {
        "name": "Pass B — counter-test, record still dispatches",
        "message": "log what I ate today - two eggs, toast, and a big bowl of pasta at 9pm",
        "expect_agent_present": "physical_health",
        "why": "a record; loading knowledge must never replace logging it",
    },
]


def _dispatched(coord_output: str) -> list[str]:
    """Agent names the Coordinator asked for, normalised the way dispatch normalises them."""
    match = re.search(r'SPECIALISTS_TO_CALL:\s*```json\s*(.*?)```', coord_output, re.DOTALL)
    if not match:
        match = re.search(r'SPECIALISTS_TO_CALL:\s*(\[.*?\])', coord_output, re.DOTALL)
    if not match:
        return []
    try:
        specs = json.loads(match.group(1).strip())
    except json.JSONDecodeError:
        return []
    # _dispatch_from_coordinator keeps its alias map function-local, so this repeats only the
    # generic fallback — enough for the two agent names this gate asserts on.
    lowered = [str(s.get("agent", "")).lower() for s in specs if isinstance(s, dict)]
    return [n.replace(" & ", "_").replace(" and ", "_").replace(" ", "_") for n in lowered]


def run_case(case: dict, persona: str) -> bool:
    print(f"\n{'=' * 78}\n{case['name']}\n  message: {case['message']!r}\n  why    : {case['why']}\n{'=' * 78}")

    captured: dict = {}
    real_resolve = orch._resolve_knowledge

    def _spy(coord_output, persona=None):
        captured["coord"] = coord_output
        entries = real_resolve(coord_output, persona=persona)
        captured["entries"] = entries
        return entries

    orch._resolve_knowledge = _spy
    try:
        reply = "".join(
            chunk for chunk in orch.run_pipeline_session_stream(case["message"], persona=persona)
            if chunk not in ("[DONE]", "[RETRACT]")
        )
    finally:
        orch._resolve_knowledge = real_resolve

    coord = captured.get("coord", "")
    entries = captured.get("entries", [])
    requested = re.search(r'KNOWLEDGE_TO_LOAD:\s*(?:```json\s*)?(\[.*?\])', coord, re.DOTALL)
    agents = _dispatched(coord)

    print(f"\n  KNOWLEDGE_TO_LOAD : {requested.group(1).strip() if requested else '(absent)'}")
    print(f"  entries fetched   : {[e.get('key') for e in entries]}")
    print(f"  specialists called: {agents or '(none)'}")
    print(f"\n  reply: {reply.strip()[:400]}")

    ok = True
    for domain in case.get("expect_domains", []):
        hit = any(e.get("domain") == domain for e in entries)
        print(f"\n  [{'PASS' if hit else 'FAIL'}] '{domain}' knowledge was loaded")
        ok &= hit
    if case.get("expect_reply_any"):
        markers = [m for m in case["expect_reply_any"] if m in reply.lower()]
        hit = bool(markers)
        print(f"  [{'PASS' if hit else 'FAIL'}] a stored fact reached the reply {markers or ''}")
        ok &= hit
    if case.get("expect_agent_present"):
        agent = case["expect_agent_present"]
        hit = agent in agents
        print(f"  [{'PASS' if hit else 'FAIL'}] '{agent}' WAS dispatched")
        ok &= hit
    return ok


# The gate needs standing facts to retrieve, and `data/personas/*/` is gitignored — so a
# fixture seeded by hand does not travel with this file and the test silently degrades to
# meaningless on any other machine, including the VM. It seeds itself instead.
_FIXTURE = [
    ("standard_breakfast", "Two eggs and toast most weekdays, eaten standing up before the 8:30 pipeline call.", "food", "stated"),
    ("coffee_ritual", "Grinds and brews a V60 by hand every morning — the one habit kept from the coffee business. Will not drink drip.", "food", "stated"),
    ("skips_lunch_on_call_days", "Tends to skip lunch entirely on heavy call days and eat a large late dinner.", "food", "observed"),
    ("evening_walk_with_dog", "Walks the dog around the lake most evenings; it is the reliable movement in the week.", "fitness", "stated"),
    ("late_sleeper_after_travel", "Sleep runs late and broken for two or three nights after any work trip.", "sleep", "observed"),
]


def seed(persona: str) -> None:
    """Write the fixture if this persona has no `food` knowledge yet. Never for a real user."""
    from tools.wisdom import write_wisdom

    if persona == "mike":
        raise SystemExit("refusing to seed 'mike' — that store is a real person's data, VM-owned")

    with persona_scope(persona):
        if "food" in domains_present():
            return
        print(f"seeding knowledge fixture into '{persona}' (no `food` subject on file)")
        for key, value, domain, provenance in _FIXTURE:
            write_wisdom(key, value, domain=domain, provenance=provenance)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--persona", default="danny_park")
    parser.add_argument("--no-seed", action="store_true",
                        help="fail instead of seeding when the store has no `food` subject")
    args = parser.parse_args()

    if not args.no_seed:
        seed(args.persona)

    with persona_scope(args.persona):
        present = domains_present()
    print(f"persona: {args.persona}\nsubjects on file: {present or '(NONE — store empty or still on the legacy `category` axis; this gate cannot mean anything)'}")
    if not present:
        return 1

    results = [(case["name"], run_case(case, args.persona)) for case in CASES]

    print(f"\n{'=' * 78}")
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    passed = all(ok for _, ok in results)
    print(f"{'=' * 78}\n{'GATE PASS' if passed else 'GATE FAIL'} — both cases must pass; A alone proves nothing.")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
