"""
tests/test_unprompted_clinical_flags.py — a clinical flag needs the user's own words.

Mike, 2026-10-29: until the agent rewrite gives clinical flags their own treatment, a flag must
not fire without a valid reason. On trial_2026_10c one disclosure inside the first interview became
eight scheduled sessions in 22 hours, each with Mental Wellbeing re-raising CLINICAL_CONCERN +
ESCALATION from its own earlier log entries and the Synthesizer reciting the full crisis-resource
block. A scheduled session has no user words by construction, so:

  1. core/orchestrator._drop_unprompted_clinical_flags removes Mental Wellbeing's clinical items
     and its MUST_SURFACE before the Synthesizer reads them — only on a turn with no user words.
  2. tools/context_tracker.write_context_tracker writes no clinical thread and raises no
     escalation on a scheduled session; existing threads carry forward untouched.

A real user turn is unchanged in both halves — the flag still fires on her words.

Run:  python3 tests/test_unprompted_clinical_flags.py
Exit: 0 all pass, 1 on any failure.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

PERSONA = "unprompted_flag_test"
SI = "CLINICAL_CONCERN: SUICIDAL_IDEATION"

# Shaped on trial_2026_10c's 2026-10-28 16:59 scheduled check-in, MUST_SURFACE wrapped onto a
# second line as a model may write it.
MW_SCHEDULED = """EMOTIONAL STATE: acute distress, severe hopelessness, vulnerable
INTENSITY: high
TRAJECTORY: unclear
PATTERN MATCH: Acute episode of hopelessness reported earlier today
FLAGS: CLINICAL_CONCERN: SUICIDAL_IDEATION, ESCALATION
MUST_SURFACE: Prioritize immediate safety and emotional containment.
  Surface crisis resources again.
PROACTIVE_OBSERVATIONS: none
SUGGESTED FOLLOW-UP: Ask gently how they are holding up."""

PH_SCHEDULED = """PHYSICAL STATE: stable
FLAGS: MEDICATION_MISSED_CRITICAL: lithium
MUST_SURFACE: lithium dose not logged since yesterday morning."""

_failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}{(' — ' + detail) if detail else ''}")
        _failures.append(name)


def test_orchestrator_strip() -> None:
    from core.orchestrator import _drop_unprompted_clinical_flags as drop

    outputs = {"mental_wellbeing": MW_SCHEDULED, "physical_health": PH_SCHEDULED}

    out = drop(outputs, user_turn=False)
    mw = out["mental_wellbeing"]
    check("scheduled: CLINICAL_CONCERN removed", "CLINICAL_CONCERN" not in mw, mw)
    check("scheduled: ESCALATION removed", "ESCALATION" not in mw, mw)
    check("scheduled: MUST_SURFACE removed, continuation line included",
          "MUST_SURFACE" not in mw and "crisis resources" not in mw, mw)
    check("scheduled: FLAGS reads none", "FLAGS: none" in mw, mw)
    check("scheduled: the rest of the output is kept",
          "EMOTIONAL STATE:" in mw and "PROACTIVE_OBSERVATIONS: none" in mw
          and "SUGGESTED FOLLOW-UP:" in mw, mw)
    check("scheduled: another specialist's data-driven flag is untouched",
          out["physical_health"] == PH_SCHEDULED)
    check("input dict is not mutated", outputs["mental_wellbeing"] == MW_SCHEDULED)

    check("user turn: output unchanged", drop(outputs, user_turn=True) is outputs)

    mixed = {"mental_wellbeing": "FLAGS: COGNITIVE_DISTORTION, CLINICAL_CONCERN: MANIA, ESCALATION"}
    check("scheduled: a non-clinical flag survives",
          drop(mixed, user_turn=False)["mental_wellbeing"] == "FLAGS: COGNITIVE_DISTORTION")

    clean = {"mental_wellbeing": "EMOTIONAL STATE: content\nFLAGS: none"}
    check("scheduled: nothing to drop returns the same dict", drop(clean, user_turn=False) is clean)
    check("no mental_wellbeing output: unchanged",
          drop({"logistics": "FLAGS: none"}, user_turn=False) == {"logistics": "FLAGS: none"})


def test_tracker_gate() -> None:
    from core.persona import persona_data_dir, persona_scope
    from core.trace import set_trace, start_request_trace
    from tools.context_tracker import read_context_tracker, write_context_tracker
    from tools.escalation import list_escalations

    with persona_scope(PERSONA):
        shutil.rmtree(persona_data_dir(), ignore_errors=True)
        try:
            # A scheduled session tries to open a tier-2 thread.
            start_request_trace("Check in.", PERSONA, is_proactive=True, source="scheduler")
            result = write_context_tracker(
                [], [], [], clinical_threads=[{"flag": SI, "status": "active", "note": "n"}])
            set_trace(None)
            check("scheduled: no clinical thread written",
                  read_context_tracker()["clinical_threads"] == [])
            check("scheduled: no escalation raised", list_escalations(persona=PERSONA) == [])
            check("scheduled: the write says why", "no user words" in result, result)

            # A real user turn opens it — unchanged behaviour.
            start_request_trace("I feel like there's no point", PERSONA, is_proactive=False)
            write_context_tracker(
                [], [], [], clinical_threads=[{"flag": SI, "status": "watch", "note": "user"}])
            set_trace(None)
            threads = read_context_tracker()["clinical_threads"]
            check("user turn: thread written", [t["flag"] for t in threads] == [SI], str(threads))
            check("user turn: escalation raised", len(list_escalations(persona=PERSONA)) == 1)

            # A scheduled session tries to move it back to active: carried forward untouched.
            start_request_trace("Check in.", PERSONA, is_proactive=True, source="scheduler")
            write_context_tracker(
                [], [], [], clinical_threads=[{"flag": SI, "status": "active", "note": "again"}])
            set_trace(None)
            after = read_context_tracker()["clinical_threads"]
            check("scheduled: existing thread kept at watch with its note",
                  len(after) == 1 and after[0]["status"] == "watch" and after[0]["note"] == "user",
                  str(after))

            # No trace at all (a script or maintenance job) is not a scheduled session.
            shutil.rmtree(persona_data_dir(), ignore_errors=True)
            write_context_tracker(
                [], [], [], clinical_threads=[{"flag": SI, "status": "active", "note": "n"}])
            check("no trace: thread written as before",
                  len(read_context_tracker()["clinical_threads"]) == 1)
        finally:
            set_trace(None)
            shutil.rmtree(persona_data_dir(), ignore_errors=True)


def main() -> int:
    print("orchestrator — Mental Wellbeing's clinical items on a turn with no user words")
    test_orchestrator_strip()
    print("context tracker — no clinical thread or escalation from a scheduled session")
    test_tracker_gate()
    print(f"\n{'FAIL' if _failures else 'PASS'} — {len(_failures)} failure(s)")
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())
