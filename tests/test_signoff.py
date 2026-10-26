"""
Sign-off detection — "over and out" skips the Synthesizer (2026-08-27).

Tests _is_signoff (fuzzy match, tuned to never false-positive) and _signoff_skip
(the full decision: real user turn, no safety flag in specialist output).
Pure-Python; no model calls.

Run: python tests/test_signoff.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.orchestrator import _is_signoff, _signoff_skip, _levenshtein
try:
    from core.orchestrator import _signoff_note
except ImportError:  # before 2026-10-26: no note existed
    def _signoff_note(*_a, **_k):
        return ""

FAILURES: list[str] = []


def check(name: str, cond: bool) -> None:
    status = "PASS" if cond else "FAIL"
    print(f"  {status}  {name}")
    if not cond:
        FAILURES.append(name)


print("_levenshtein sanity:")
check("identical", _levenshtein("over", "over") == 0)
check("one edit", _levenshtein("ovr", "over") == 1)
check("transposition costs 1 (Damerau)", _levenshtein("adn", "and") == 1)

print("\n_is_signoff — must fire:")
for text in [
    "Over and out",
    "over and out.",
    "OVER AND OUT!",
    "Thanks, that's everything. Over and out",
    "Got the directions, heading there now. Over and out.",
    "over & out",
    "ovr and out",          # one edit in "over"
    "over an out",          # one edit in "and"
    "over and outt",        # one edit in "out"
    "over and ou",          # one edit in "out"
    "over adn out",         # transposition = one Damerau edit
    "oevr and out",         # transposition in "over"
]:
    check(repr(text), _is_signoff(text))

print("\n_is_signoff — must NOT fire:")
for text in [
    "",
    "over",
    "and out",                                    # only two words
    "over and out?",                              # asking about the phrase
    "what does over and out mean?",               # question form
    "down and out",                               # 3 edits in word 1
    "over and above",                             # 3 edits in word 3
    "in and out",                                 # 3 edits in word 1
    "sort it out",                                # unrelated tail
    "over and out was what pilots used to say",   # phrase mid-message, not tail
    "the ball went over and out of the park",     # phrase mid-message
    "I knocked it over and dropped out",          # "dropped" ≥2 edits from "and"... tail is 'dropped out' — word 1 'it' fails
    "adn out over",                               # right words, wrong order
    "Heading out now",
    "It's over, and I'm heading out soon after that",
]:
    check(repr(text), not _is_signoff(text))

print("\n_signoff_skip — the full decision:")
check("skips on clean sign-off", _signoff_skip("--- logistics ---\nnoted.", "Over and out", False))
check("never skips a proactive turn", not _signoff_skip("", "over and out", True))
check("never skips a normal turn", not _signoff_skip("", "what's on today?", False))
check("MUST_SURFACE vetoes the skip",
      not _signoff_skip("--- mental_wellbeing ---\nMUST_SURFACE: ...", "over and out", False))
check("CLINICAL_CONCERN vetoes the skip",
      not _signoff_skip("--- mental_wellbeing ---\nCLINICAL_CONCERN: low mood", "over and out", False))
check("MEDICATION_MISSED_CRITICAL vetoes the skip",
      not _signoff_skip("--- physical_health ---\nMEDICATION_MISSED_CRITICAL", "over and out", False))

# 2026-10-26: a sign-off that carries something runs the Synthesizer (Mike: "Synth shouldn't
# skip when there's something active requested, even with over and out"). The long cases are
# real messages that got the ack and lost what they asked.
print("\n_signoff_skip — a bare sign-off still skips:")
SPEC = "--- diarist ---\nlogged."
for text in [
    "Over and out",
    "Thanks, that's everything. Over and out",
    "Testing. Over and out",
    "Let's wait until I'm back at the desk. Over and out",                 # 08-28, 8 words
    "[Mon, Oct 26 at 10:04 PM] Resting for the night, over and out",       # en-US stamp
    "[Mon 26 Oct, 22:04] Resting for the night, over and out",             # en-GB stamp
    "That's me done for the day. Over and out",
]:
    check(f"skips {text!r}", _signoff_skip(SPEC, text, False))
check("skips when Metatron's last reply asked nothing",
      _signoff_skip(SPEC, "Thanks, over and out", False,
                    history=[{"role": "assistant", "content": "Noted — the plants are done."}]))

print("\n_signoff_skip — a sign-off that asks or reports something does NOT skip:")
LIVE_1026 = ("[Mon, Oct 26 at 9:34 PM] The programmer job to tomorrow with the gym thing we're "
             "going to retire it for now but temporarily and once I pick it up maybe next week I "
             "will decide how many workouts I can fit in.  [Mon, Oct 26 at 10:04 PM] Putting a few "
             "finishing touches on Meditron and then I am resting for the night over and out.")
LIVE_1019 = ("Good idea on the shoes more generally. Sit one for the middle of March because that "
             "should coincide with my next planned trip to the U.S. so I'll put something up when "
             "I'm there. Over and out.")
for name, text in [
    ("the 10-26 22:05 message (gym + job post)", LIVE_1026),
    ("the 10-19 message (a reminder for March)", LIVE_1019),
    ("a short request", "Move the job post to tomorrow, over and out"),
    ("a short request, 'please'", "Please book it, over and out"),
    ("a question before the sign-off", "Is the gym on tomorrow? OK, over and out"),
    ("over the word limit", "Today went fine and the boys were good and dinner was early and "
                            "quiet. Over and out"),
    ("nine words, one over the limit", "Putting the finishing touches on it and then resting. "
                                       "Over and out"),
    # Fable review 2026-10-26: short instructions and answers with no verb from the first list.
    ("'shift'", "Shift the gym to Tuesday over and out"),
    ("'postpone'", "Postpone the gym over and out"),
    ("'wake'", "Wake me at six over and out"),
    ("'make it'", "Make it Tuesday over and out"),
    ("'instead'", "Tomorrow instead over and out"),
    ("'forget'", "Forget the gym thing over and out"),
    ("'scrap'", "Scrap the gym thing over and out"),
    ("a time word", "No gym tomorrow over and out"),
    ("'yes do that'", "Yes do that over and out"),
    ("'go ahead'", "Go ahead over and out"),
    ("'confirmed'", "Confirmed over and out"),
]:
    check(f"runs: {name}", not _signoff_skip(SPEC, text, False))
check("runs: answering a question Metatron's previous reply asked",
      not _signoff_skip(SPEC, "Fine, over and out", False,
                        history=[{"role": "user", "content": "the job post"},
                                 {"role": "assistant", "content": "Shall I move the job post?"}]))
check("runs: the ledger's completion note fired ('gym done')",
      not _signoff_skip(SPEC, "Gym done, over and out", False,
                        task_hint="TASK NOTE: the user's message may report done: ob_x (Gym)"))
check("skips the same words when no task note fired",
      _signoff_skip(SPEC, "Gym done, over and out", False, task_hint=""))

print("\n_signoff_note — the one-line instruction when a sign-off runs the Synthesizer:")
note = _signoff_note(SPEC, LIVE_1026, False)
check("present for a sign-off that carries something", "over and out" in note.lower())
check("tells the Synthesizer to act on it", "everything" in note.lower())
check("absent on a normal turn", _signoff_note(SPEC, "what's on today?", False) == "")
check("absent on a proactive turn", _signoff_note(SPEC, "over and out", True) == "")
check("absent when a safety flag must lead",
      _signoff_note("--- mental_wellbeing ---\nMUST_SURFACE: x", LIVE_1026, False) == "")

print("\nwiring — both pipeline twins:")
SRC = (Path(__file__).parent.parent / "core" / "orchestrator.py").read_text()
check("both twins pass the task note and history into the skip decision",
      SRC.count("_signoff_skip(spec_text, user_input, is_proactive, task_hint, history)") == 2)
check("both twins add the sign-off note to the Synthesizer input",
      SRC.count('(f"\\n\\n{signoff_note}" if signoff_note else "")') == 2)
for twin in ("def run_pipeline_session(", "def _run_pipeline_session_stream_inner("):
    body = SRC[SRC.index(twin):]
    body = body[: body.index("\ndef ", 10)]
    name = twin.split('(')[0][4:]
    check(f"{name}: task note is built before the skip decision",
          body.index("task_hint = _task_hint_block(") < body.index("_signoff_skip("))
    # These two have side effects (an offer charged, a rhythm suggestion stamped) and must
    # not run on a turn the Synthesizer skips.
    check(f"{name}: horizon and day-plan blocks stay after the skip decision",
          body.index("_signoff_skip(") < body.index("_horizon_block(")
          and body.index("_signoff_skip(") < body.index("_day_plan_block("))

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILURES: {FAILURES}")
    sys.exit(1)
print("all checks pass")
