"""
tests/test_instruction_leak_filter.py — filter_output() tier 4.

Built against a real leak, not a hypothetical one. On 2026-08-12T00:14 the
Synthesizer's entire stored response to Mike (711 characters, all of it) was its
own deliberation, quoting `config/agents/synthesizer.md` back at him verbatim and
cut off mid-sentence. Tiers 1-3 passed it correctly by their own logic: they hunt
architecture vocabulary, and instruction prose contains none.

The first test below is that exact string, pulled from the VM conversation record.
If tier 4 is ever weakened, this is the test that fails.

Run: python3 tests/test_instruction_leak_filter.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.orchestrator import (  # noqa: E402
    _CANNED_FALLBACK,
    _INSTRUCTION_NGRAM,
    _instruction_ngrams,
    filter_output,
)

# Verbatim from /monitor/conversations, persona=mike, ts=2026-08-12T00:14:57.759004,
# seq 002. Reproduced exactly, including the truncation mid-sentence.
LEAKED_2026_08_12 = (
    '"A repeated instruction is a failure, not a new one... The scheduled '
    "session's opening text often restates a standing rule *because that is what "
    'it is for*; reading it as the user complaining again is how a rule that was '
    'being followed came to look like the most-ignored request in the system."\n'
    '        So here, the system sent me a prompt: "Check the weather... prompt '
    'him to water them."\n'
    '        I should acknowledge it internally but apply the "Raise a thing '
    'once" rule.\n'
    '        "An open item that you have already surfaced, and the user has '
    'heard, is not raised again in later exchanges... Bring it back only when '
    'something changes".\n'
    "        Wait. The user *hasn't* heard it, because they haven't replied to"
)

_results: list[tuple[bool, str]] = []


def check(label: str, condition: bool) -> None:
    _results.append((condition, label))
    print(f"  {'PASS' if condition else 'FAIL'}  {label}")


def main() -> int:
    # --- the regression this tier exists for --------------------------------
    out = filter_output(LEAKED_2026_08_12, "synthesizer")
    check("the real 2026-08-12 leak is suppressed", out == _CANNED_FALLBACK)

    # --- ordinary responses must survive ------------------------------------
    # These are the false-positive risk: a tier that fires on normal output is
    # worse than no tier, because it replaces real answers with the fallback.
    ordinary = [
        "That's closed out on the credit card. I've also moved the rucking "
        "session to this coming Monday at 7:30 AM.",
        "Good morning. Your main event today is lunch with Iva at 12:30 PM, and "
        "we still need to nail down the step counter setup we left open "
        "yesterday. How did you sleep?",
        "You're right that I keep raising it. I'll stop mentioning the Prudential "
        "email until something actually arrives.",
        "The repetitive evening messages are a bug. That's noted — fixing it "
        "needs a change on my side, outside our conversation.",
    ]
    for i, text in enumerate(ordinary, 1):
        check(f"ordinary response {i} passes unchanged",
              filter_output(text, "synthesizer") == text)

    # --- the mechanism ------------------------------------------------------
    grams = _instruction_ngrams("synthesizer")
    check("synthesizer instructions produce shingles", len(grams) > 100)

    src = (Path(__file__).parent.parent / "config" / "agents" / "synthesizer.md").read_text()
    # A window from the middle of the file, long enough to trip the tier.
    words = [w for w in src.split() if w]
    lifted = " ".join(words[len(words) // 2: len(words) // 2 + _INSTRUCTION_NGRAM + 4])
    check("an arbitrary verbatim span from the agent file is suppressed",
          filter_output(lifted, "synthesizer") == _CANNED_FALLBACK)

    constitution = (Path(__file__).parent.parent / "config" / "constitution.md").read_text()
    cwords = [w for w in constitution.split() if w]
    clifted = " ".join(cwords[len(cwords) // 2: len(cwords) // 2 + _INSTRUCTION_NGRAM + 4])
    check("a verbatim span from the constitution is suppressed",
          filter_output(clifted, "synthesizer") == _CANNED_FALLBACK)

    # A span one word shorter than the threshold must NOT fire — this is what
    # keeps the tier from creeping into ordinary phrase matching.
    short = " ".join(words[len(words) // 2: len(words) // 2 + _INSTRUCTION_NGRAM - 1])
    check("a span below the n-gram threshold does not fire",
          filter_output(short, "synthesizer") != _CANNED_FALLBACK)

    # --- scope --------------------------------------------------------------
    # Non-Synthesizer agents are not filtered at all; unchanged by this tier.
    check("a non-synthesizer agent is untouched",
          filter_output(LEAKED_2026_08_12, "logistics") == LEAKED_2026_08_12)

    # An agent with no instruction file must not raise. It still yields the
    # constitution's shingles — that file is in every agent's context, so
    # covering it is correct, not a leftover.
    missing = _instruction_ngrams("no_such_agent_xyz")
    check("a missing agent file does not raise, and still covers the constitution",
          len(missing) > 100 and missing < grams)
    check("a missing agent file does not suppress",
          filter_output("A perfectly ordinary sentence about lunch plans today.",
                        "no_such_agent_xyz")
          == "A perfectly ordinary sentence about lunch plans today.")

    print()
    failed = [label for ok, label in _results if not ok]
    if failed:
        print(f"{len(failed)} check(s) FAILED:")
        for label in failed:
            print(f"  - {label}")
        return 1
    print("All instruction-leak filter checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
