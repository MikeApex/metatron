"""
tests/test_false_action_claim.py — [DB-0815-11] the system claims actions it never took.

Third confirmed instance, 2026-08-21: a run opened "I have made a note to open sessions
exactly that way going forward. I've logged the instruction change so it sticks" and the
trace held no config write of any kind.

This covers the DETECTION half only — the policy question (may write_persona self-apply?)
is not settled here, and check_false_action_claims() never modifies a response. Three
directions are asserted: claim without a write is flagged, claim with a matching write is
not, and ordinary language is not read as a claim.

Pure-Python; write_quality_event is stubbed, so nothing is written and no model is called.

Run:  python3 tests/test_false_action_claim.py
Exit: 0 all pass, 1 on any failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.orchestrator as orch  # noqa: E402
import tools.logger as logger_mod  # noqa: E402

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{(' — ' + detail) if detail and not cond else ''}")
    if not cond:
        FAILURES.append(name)


THE_INCIDENT = (
    "I have made a note to open sessions exactly that way going forward. "
    "I've logged the instruction change so it sticks."
)

CLAIMS = [
    THE_INCIDENT,
    "Right — I've made a note of that.",
    "I've updated your goals to match.",
    "That's logged.",
    "I've saved it against the Thursday entry.",
    "I'll make a note of that for next time.",
]

NOT_CLAIMS = [
    "You logged eight hours on Tuesday, which is your best this week.",
    "Worth writing that down somewhere before it slips.",
    "I'll keep that in mind while we plan the week.",
    "The Teams link is still missing from the invite.",
    "Noted — the Prudential deadline is the 14th.",   # acknowledgement, not persistence
    "Shall I make a note of that?",
]

# The events check_false_action_claims() would write, captured rather than written.
events: list[tuple] = []


def _fake_write_quality_event(event_type, source_agent="", detail="", session_id=""):
    events.append((event_type, source_agent, detail))
    return "stubbed"


logger_mod.write_quality_event = _fake_write_quality_event


print("find_persistence_claims — a claim is a claim:")
for text in CLAIMS:
    check(f"flags {text[:52]!r}", bool(orch.find_persistence_claims(text)))

print("\nfind_persistence_claims — ordinary language is not:")
for text in NOT_CLAIMS:
    found = orch.find_persistence_claims(text)
    check(f"ignores {text[:52]!r}", not found, str(found))

print("\ncheck_false_action_claims — the cross-check against real tool calls:")
events.clear()
flagged = orch.check_false_action_claims(THE_INCIDENT, tool_names=set())
check("claim with no tool call is flagged", len(flagged) == 2, str(flagged))
check("one quality event per claiming sentence", len(events) == 2, str(events))
check("event type and source are right",
      all(e[0] == "FALSE_ACTION_CLAIM" and e[1] == "synthesizer" for e in events), str(events))
check("the detail is the claiming sentence",
      events and "made a note" in events[0][2], str(events[:1]))

events.clear()
check("claim with a matching write is not flagged",
      orch.check_false_action_claims(THE_INCIDENT, tool_names={"write_persona"}) == [])
check("...and writes no event", not events)

events.clear()
check("a read-only tool call does not clear a claim",
      len(orch.check_false_action_claims(THE_INCIDENT, tool_names={"read_log", "get_weather"})) == 2)

events.clear()
check("a response with no claim is never flagged",
      orch.check_false_action_claims(
          "You logged eight hours on Tuesday. The Teams link is still missing.",
          tool_names=set()) == [])
check("...and writes no event", not events)

print("\nwrite-family classification:")
for name in ["write_log", "write_persona", "update_goal", "merge_contacts",
             "close_obligation", "send_email", "delete_calendar_event"]:
    check(f"{name} counts as a write", orch._is_write_tool(name))
for name in ["read_log", "get_weather", "search_memory", "list_contacts",
             "check_calendar_conflicts"]:
    check(f"{name} does not", not orch._is_write_tool(name))

print()
if FAILURES:
    print(f"{len(FAILURES)} failure(s): {', '.join(FAILURES)}")
    sys.exit(1)
print("All false-action-claim detection checks passed.")
sys.exit(0)
