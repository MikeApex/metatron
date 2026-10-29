"""
tests/test_false_claim_phrasings.py — a reply says something was set or queued when nothing was.

Two live cases (Mike, raised 2026-10-27, ruled 2026-10-29):
  * 2026-10-25 08:35 — "the Chase and Rowan windows are set to surface…" — nothing written;
  * 2026-10-27 09:59 / 10:00 — "dinner prep queued for 16:30" — no task, event, setting or plan
    row. That day's plan DID have a 16:30 row ("Return trip from Crossharbour") and a 17:30
    dinner calendar event, which is why a bare time match must not clear a claim.

The ruling: widen the phrasings, and do not flag a claim that a real row in today's day plan (or a
pending reminder) backs — since the day planner landed, code schedules things without any write
tool on the trace.

EVERY LIVE METER IS STUBBED: `tools.day_plan.current` and `_load_state` return fixtures, so no
calendar fetch, route lookup or model call can happen; write_quality_event is captured, not
written. No persona data is read or written.

Run:  python3 tests/test_false_claim_phrasings.py
Exit: 0 all pass, 1 on any failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.orchestrator as orch  # noqa: E402
import tools.day_plan as D  # noqa: E402
import tools.logger as logger_mod  # noqa: E402

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{(' — ' + detail) if detail and not cond else ''}")
    if not cond:
        FAILURES.append(name)


events: list[tuple] = []


def _fake_write_quality_event(event_type, source_agent="", detail="", session_id=""):
    events.append((event_type, source_agent, detail))
    return "stubbed"


logger_mod.write_quality_event = _fake_write_quality_event

# --- fixtures: the plan the stubbed day planner returns --------------------------------------

_STATE = {"plan": None, "reminders": [], "raise": False, "reads": 0}


def _block(kind: str, title: str, start: str, end: str) -> dict:
    return {"id": f"{kind}:{title}", "kind": kind, "title": title,
            "start": f"2026-10-27T{start}", "end": f"2026-10-27T{end}"}


# The real 2026-10-27 plan, as far as it bears on the claim: a 16:30 row that is NOT dinner prep,
# and the dinner event at 17:30.
PLAN_1027 = {"day": "2026-10-27", "blocks": [
    _block("travel", "travel home from Crossharbour", "16:30", "17:00"),
    _block("event", "Return trip from Crossharbour", "16:30", "17:00"),
    _block("event", "Dinner with the Okafors", "17:30", "19:00"),
    _block("protected", "the user's own time", "16:00", "18:00"),
]}

# The same day with the row the reply described.
PLAN_WITH_PREP = {"day": "2026-10-27", "blocks": PLAN_1027["blocks"] + [
    _block("task", "Dinner prep", "16:30", "17:00"),
]}


def _current(persona=None, reason="", for_reply=False):
    _STATE["reads"] += 1
    if _STATE["raise"]:
        raise RuntimeError("plan unreadable")
    return _STATE["plan"]


D.current = _current
D._load_state = lambda persona=None: {"reminders": list(_STATE["reminders"])}


def _set(plan=None, reminders=(), raise_=False) -> None:
    _STATE.update({"plan": plan, "reminders": list(reminders), "raise": raise_})
    events.clear()


CHASE_ROWAN = ("Morning. The Chase and Rowan windows are set to surface this afternoon, "
               "so there is nothing to do on them before lunch.")
DINNER_PREP = "Got it — dinner prep queued for 16:30."

# --- 1. the two live replies flag with no write and no backing row ----------------------------

print("the two live replies are claims:")
check("Chase and Rowan 'set to surface' is found", bool(orch.find_persistence_claims(CHASE_ROWAN)))
check("'dinner prep queued for 16:30' is found", bool(orch.find_persistence_claims(DINNER_PREP)))

print("\nflagged with no write tool and no plan row:")
_set(plan=None)
check("Chase and Rowan flags (no plan)",
      len(orch.check_false_action_claims(CHASE_ROWAN, tool_names=set())) == 1, str(events))
check("...one FALSE_ACTION_CLAIM event", [e[0] for e in events] == ["FALSE_ACTION_CLAIM"])
_set(plan=PLAN_1027)
check("dinner prep flags against the real 10-27 plan (16:30 row is another thing)",
      len(orch.check_false_action_claims(DINNER_PREP, tool_names=set())) == 1, str(events))
_set(plan=PLAN_1027)
check("Chase and Rowan flags against a plan with no such row",
      len(orch.check_false_action_claims(CHASE_ROWAN, tool_names=set())) == 1)

# --- 2. a real plan row (or reminder) backs the claim -----------------------------------------

print("\nbacked by today's plan — not flagged:")
_set(plan=PLAN_WITH_PREP)
check("dinner prep at 16:30 with a Dinner prep row at 16:30",
      orch.check_false_action_claims(DINNER_PREP, tool_names=set()) == [], str(events))
check("...and writes no event", not events)
_set(plan=PLAN_WITH_PREP)
check("'4:30 pm' reads as 16:30",
      orch.check_false_action_claims("Dinner prep is queued for 4:30 pm.", tool_names=set()) == [])
_set(plan=PLAN_WITH_PREP)
check("a claim with no time is backed by its title alone",
      orch.check_false_action_claims("Dinner prep is lined up for this afternoon.",
                                     tool_names=set()) == [])
_set(plan=PLAN_WITH_PREP)
check("the right title at the wrong time still flags",
      len(orch.check_false_action_claims("Dinner prep queued for 18:00.", tool_names=set())) == 1)
_set(plan=None, reminders=[{"task_id": "t1", "title": "Call the vet",
                            "at": "2026-10-27T15:00:00"}])
check("a pending reminder backs 'call the vet queued for 15:00'",
      orch.check_false_action_claims("Call the vet is queued for 15:00.", tool_names=set()) == [])
_set(raise_=True)
check("a plan that cannot be read falls back to flagging",
      len(orch.check_false_action_claims(DINNER_PREP, tool_names=set())) == 1)

# --- 3. the existing behaviour is unchanged ---------------------------------------------------

print("\nexisting cases unchanged:")
_set(plan=None)
check("a write tool on the trace still clears a claim",
      orch.check_false_action_claims(DINNER_PREP, tool_names={"write_task"}) == [])
check("'I've added …' still a completion claim",
      any(r.search("I've added it to your calendar.") for r in orch._COMPLETION_CLAIM_RES))
check("'I've made a note' still a persistence claim",
      bool(orch.find_persistence_claims("Right — I've made a note of that.")))
_set(plan=PLAN_WITH_PREP)
_STATE["reads"] = 0
check("a persistence claim is not cleared by a plan row",
      len(orch.check_false_action_claims("I've logged the dinner prep.", tool_names=set())) == 1)
check("...and never reads the day planner", _STATE["reads"] == 0, str(_STATE["reads"]))
check("completion set is untouched by the new phrasings (it replaces replies)",
      not any(r.search(DINNER_PREP) for r in orch._COMPLETION_CLAIM_RES))

# --- 4. ordinary prose is not a claim ---------------------------------------------------------

print("\nordinary prose — not claims:")
for text in [
    "The meeting is set to start at 3.",                      # a calendar fact
    "The match is set to begin at 19:45.",
    "You have three calls lined up back to back after lunch.",
    "Shall I queue dinner prep for 16:30?",
    "There's a queue at the pharmacy most mornings.",
    "Want me to set a reminder for 16:30?",
    "The forecast is set to clear by noon.",
]:
    found = orch.find_persistence_claims(text)
    check(f"ignores {text[:56]!r}", not found, str(found))

print("\nother new phrasings — claims:")
for text in [
    "I've set a reminder for 16:30.",
    "Your reminder is set for the morning.",
    "I've queued the email draft for tonight.",
    "That's lined up for tomorrow.",
    "I've set it to nudge you at 9.",
]:
    check(f"flags {text[:56]!r}", bool(orch.find_persistence_claims(text)))

print()
if FAILURES:
    print(f"{len(FAILURES)} failure(s): {', '.join(FAILURES)}")
    sys.exit(1)
print("All false-claim phrasing checks passed.")
