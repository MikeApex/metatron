"""
tests/test_diarist_user_turn_gate.py — [DB-0822-05] the journal records days the user never spoke.

On 2026-08-21 the Diarist fired on 10 of 23 runs and the user was silent in 9 of them: it
journalled the assistant's own monologue, and once filed the scheduler's opening prompt
("Good morning. Open with whatever is most time-sensitive...") as Mike's own words. The
agent-file rule against this predates the incident (`82d394b`, 2026-08-09) and did not hold,
so the refusal is now in the dispatch path.

Two halves are asserted:
  1. has_real_user_turn() — the decision itself.
  2. _dispatch_from_coordinator() — a scheduler-only session dispatches no Diarist, while a
     real user turn still does, and no OTHER specialist is affected by the gate either way.

Pure-Python; run_session is stubbed, so no model is called.

Run:  python3 tests/test_diarist_user_turn_gate.py
Exit: 0 all pass, 1 on any failure.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.orchestrator as orch  # noqa: E402

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{(' — ' + detail) if detail and not cond else ''}")
    if not cond:
        FAILURES.append(name)


SCHEDULER_PROMPT = (
    "Good morning. Open with whatever is most time-sensitive, then check in on sleep."
)

COORD_OUTPUT = """\
SPECIALISTS_TO_CALL:
```json
[
  {"agent": "diarist", "directive": "Journal today's exchange."},
  {"agent": "physical_health", "directive": "Note the run.", "fire_and_forget": true}
]
```
"""


def _dispatch(user_turn: bool) -> list[str]:
    """Dispatch COORD_OUTPUT with the gate in the given state; return agents actually run."""
    called: list[str] = []

    def _fake_run_session(agent_name, user_input, persona=None, complexity=None, **kw):
        called.append(agent_name)
        return f"{agent_name} ok"

    real = orch.run_session
    orch.run_session = _fake_run_session
    try:
        orch._dispatch_from_coordinator(COORD_OUTPUT, user_turn=user_turn)
        # Both specialists here are fire-and-forget, so they run on daemon threads.
        time.sleep(0.3)
    finally:
        orch.run_session = real
    return called


print("has_real_user_turn:")
check("scheduler prompt on a proactive turn is not user speech",
      orch.has_real_user_turn(SCHEDULER_PROMPT, is_proactive=True) is False)
check("a real typed message is user speech",
      orch.has_real_user_turn("slept badly, skipped the run", is_proactive=False) is True)
check("the user's reply to a check-in is user speech (arrives non-proactive)",
      orch.has_real_user_turn("yeah, about six hours", is_proactive=False) is True)
check("empty input with no attachment is not user speech",
      orch.has_real_user_turn("   ", is_proactive=False) is False)
check("an attachment with no words is user speech",
      orch.has_real_user_turn("", is_proactive=False,
                              attachments=[{"filename": "bloods.png"}]) is True)
check("an attachment does not rescue a proactive turn",
      orch.has_real_user_turn("", is_proactive=True,
                              attachments=[{"filename": "bloods.png"}]) is False)

print("\n_dispatch_from_coordinator:")
suppressed = _dispatch(user_turn=False)
check("scheduler-prompt-only session dispatches no Diarist",
      "diarist" not in suppressed, str(suppressed))
check("other specialists still dispatch when the Diarist is suppressed",
      "physical_health" in suppressed, str(suppressed))

allowed = _dispatch(user_turn=True)
check("a real user turn still dispatches the Diarist",
      "diarist" in allowed, str(allowed))
check("the gate is not the default — it must be passed explicitly",
      "diarist" in _dispatch(user_turn=True))

print()
if FAILURES:
    print(f"{len(FAILURES)} failure(s): {', '.join(FAILURES)}")
    sys.exit(1)
print("All Diarist user-turn gate checks passed.")
sys.exit(0)
