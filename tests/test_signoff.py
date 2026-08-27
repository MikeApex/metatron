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

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILURES: {FAILURES}")
    sys.exit(1)
print("all checks pass")
