"""
tests/test_filter_user_echo.py — filter_output()'s echo exemption.

[DB-0808-05], observed live as Exchange 027 (2026-06-26). Mike wrote "I'm
frustrated that write_config didn't save my preferences" and the reply was
replaced with the canned deflection — because tier 1 saw a confidential
identifier and could not know he had typed it himself. A complaint about the
system is exactly the moment a real answer is owed.

The fix passes the user's own turn in. The whole risk of that fix is over-reach:
a probing question ("what does write_config do?") must NOT switch off its own
backstop. So the exemption is tier 1 only, per term, and single turn — and most
of the checks below exist to prove the parts that must NOT have changed.

Run: python3 tests/test_filter_user_echo.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.orchestrator import (  # noqa: E402
    _CANNED_FALLBACK,
    _user_typed_terms,
    filter_output,
)

EXCH_027_USER = "I'm frustrated that write_config didn't save my preferences properly."
EXCH_027_REPLY = "I'm sorry — write_config didn't save your preferences. Let me take another look."

_results: list[tuple[bool, str]] = []


def check(label: str, condition: bool) -> None:
    _results.append((bool(condition), label))
    print(f"  {'PASS' if condition else 'FAIL'}  {label}")


def main() -> int:
    # --- the regression this fix exists for ---------------------------------
    check("Exchange 027 — the reply survives when the user typed the term first",
          filter_output(EXCH_027_REPLY, "synthesizer", user_text=EXCH_027_USER)
          == EXCH_027_REPLY)

    check("the same reply is still suppressed when nobody typed the term",
          filter_output(EXCH_027_REPLY, "synthesizer") == _CANNED_FALLBACK)

    check("omitting user_text reproduces the old behaviour exactly",
          filter_output(EXCH_027_REPLY, "synthesizer", user_text=None)
          == _CANNED_FALLBACK)

    # --- the exemption is per term, not a blanket pass ----------------------
    check("a term the user did NOT type is still suppressed",
          filter_output("Sure — I'll use run_subagent for that.",
                        "synthesizer", user_text=EXCH_027_USER)
          == _CANNED_FALLBACK)

    check("mentioning one identifier does not exempt a second one",
          filter_output("write_config failed, so I called write_journal instead.",
                        "synthesizer", user_text=EXCH_027_USER)
          == _CANNED_FALLBACK)

    # --- the exemption is single-turn ---------------------------------------
    check("the next turn, with different user text, suppresses again",
          filter_output(EXCH_027_REPLY, "synthesizer",
                        user_text="thanks, what's on tomorrow?")
          == _CANNED_FALLBACK)

    # --- tiers 2, 3 and 4 are untouched — the backstop against a prober ------
    # This is the failure mode the old docstring refused to risk. It must still fail.
    probe = "what does write_config do?"
    check("PROBE — tier 2: an architecture explanation is still suppressed",
          filter_output(
              "write_config is one of the tools I have access to.",
              "synthesizer", user_text=probe) == _CANNED_FALLBACK)

    check("PROBE — tier 3: the term beside architecture vocabulary is still suppressed",
          filter_output(
              "I dispatched that through the routing layer to write_config.",
              "synthesizer", user_text=probe) == _CANNED_FALLBACK)

    check("PROBE — tier 2 fires with no identifier present at all",
          filter_output(
              "I passed this to a specialist that handles your health.",
              "synthesizer", user_text=probe) == _CANNED_FALLBACK)

    # Tier 4 — verbatim instruction prose, which carries no identifier and so
    # could never have been exempted, but must be shown not to leak through.
    src = (Path(__file__).parent.parent / "config" / "agents" / "synthesizer.md").read_text()
    words = [w for w in src.split() if w]
    lifted = " ".join(words[len(words) // 2: len(words) // 2 + 14])
    check("PROBE — tier 4: verbatim instruction text is still suppressed",
          filter_output(lifted, "synthesizer", user_text=probe) == _CANNED_FALLBACK)

    # --- what counts as "the user typed it" ---------------------------------
    check("tight form counts: write_config",
          "write_config" in _user_typed_terms("why did write_config fail?"))
    check("punctuation variants count: write-config",
          "write_config" in _user_typed_terms("why did write-config fail?"))
    check("squashed form counts: writeconfig",
          "write_config" in _user_typed_terms("why did writeconfig fail?"))

    # Spaced prose must NOT buy an exemption — otherwise ordinary English
    # ("I need to write config files for work") disarms tier 1.
    check("spaced prose does not count as typing the identifier",
          "write_config" not in _user_typed_terms("I need to write config files for work"))

    # _CONTEXT_SENSITIVE entries are ordinary words and are never exemptible.
    check("a context-sensitive common word is never exempted",
          _user_typed_terms("my relationships have been better lately") == frozenset())
    check("tier 3 still fires on a context-sensitive term the user mentioned",
          filter_output("I checked and the relationships agent routed your request.",
                        "synthesizer",
                        user_text="my relationships have been better lately")
          == _CANNED_FALLBACK)

    check("empty user text exempts nothing", _user_typed_terms("") == frozenset())
    check("None user text exempts nothing", _user_typed_terms(None) == frozenset())

    # --- scope: non-synthesizer agents are still untouched -------------------
    check("a non-synthesizer agent is unfiltered, with or without user_text",
          filter_output(EXCH_027_REPLY, "logistics", user_text=EXCH_027_USER)
          == EXCH_027_REPLY)

    # --- clean text is unaffected either way --------------------------------
    clean = "Your run streak is at nine days and lunch with Iva is at 12:30."
    check("clean text passes with user_text supplied",
          filter_output(clean, "synthesizer", user_text=EXCH_027_USER) == clean)

    print()
    failed = [label for ok, label in _results if not ok]
    if failed:
        print(f"{len(failed)} check(s) FAILED:")
        for label in failed:
            print(f"  - {label}")
        return 1
    print("All echo-exemption checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
