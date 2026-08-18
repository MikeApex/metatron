#!/usr/bin/env python3
"""Sentence-chunked speech release rule — `_speech_release()`.

**This is a security test, not a formatting test.** Spoken audio cannot be
retracted (see § SECURITY GAP beside `_SPEAK_PREFIX` in core/orchestrator.py),
so the release rule is the only thing standing between a filtered response and
a leak that has already been said out loud. The cases that matter most here are
the negative ones: nothing is released before the lead buffer exists, and
nothing is released after a prefix fails the filter.

No model call, no network — the filter is injected.

    python tests/test_speech_chunking.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.orchestrator import _SPEECH_LEAD_CHARS, _speech_release  # noqa: E402

_PASS = "\033[32mPASS\033[0m"
_FAIL = "\033[31mFAIL\033[0m"
_results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    _results.append((name, ok, detail))
    print(f"  [{_PASS if ok else _FAIL}] {name}" + (f"  — {detail}" if detail and not ok else ""))


def clean(_prefix: str) -> bool:
    return True


def dirty(_prefix: str) -> bool:
    return False


# Long enough that the lead buffer is satisfied for the early sentences.
TAIL = "x" * (_SPEECH_LEAD_CHARS + 20)
TEXT = f"First sentence here. Second one follows! Third one? {TAIL}"


print("\n=== release rule ===")

out, upto, halted = _speech_release(TEXT, 0, final=False, is_clean=clean)
check("releases complete sentences once the lead buffer is satisfied",
      out == ["First sentence here.", "Second one follows!", "Third one?"],
      f"got {out}")
check("cursor advances past what was released", upto > 0, f"upto={upto}")
check("not halted on a clean response", halted is False)

# Nothing may be spoken while the sentence is still the tail of the stream.
short = "Only one sentence so far."
out2, upto2, halted2 = _speech_release(short, 0, final=False, is_clean=clean)
check("LEAD BUFFER: holds a sentence with nothing behind it",
      out2 == [] and upto2 == 0, f"got {out2}")

# ...and is released once the stream ends, since the filter has passed on the whole.
out3, upto3, _ = _speech_release(short, 0, final=True, is_clean=clean)
check("releases the held sentence when final=True",
      out3 == ["Only one sentence so far."], f"got {out3}")

print("\n=== the security-relevant cases ===")

out4, upto4, halted4 = _speech_release(TEXT, 0, final=False, is_clean=dirty)
check("HALTS when the filter rejects the prefix", halted4 is True)
check("releases NOTHING when the filter rejects", out4 == [], f"got {out4}")
check("cursor does NOT advance on a rejected prefix", upto4 == 0, f"upto={upto4}")


def dirty_after_first(prefix: str) -> bool:
    """Clean until the response grows past its first sentence."""
    return prefix.strip().endswith("here.")


out5, upto5, halted5 = _speech_release(TEXT, 0, final=False, is_clean=dirty_after_first)
check("releases only the prefixes that passed, then halts",
      out5 == ["First sentence here."] and halted5 is True, f"got {out5} halted={halted5}")
check("THE RESIDUAL GAP IS REAL AND THIS ASSERTS IT: a sentence cleared before the "
      "response turned dirty has already been released",
      out5 == ["First sentence here."],
      "if this ever returns [] the mitigation got stronger — update the gap note")

print("\n=== reassembly, and the tail contract ===")
WHOLE = "First sentence here. Second one follows! Third one?"
out6, upto6, _ = _speech_release(WHOLE, 0, final=True, is_clean=clean)
check("a fully-terminated response rejoins to the original when joined on a space",
      " ".join(out6).split() == WHOLE.split(), f"got {' '.join(out6)[:60]}...")

# The caller MUST flush what is left, or the last words are never spoken. This is
# the contract the pipeline's explicit tail-release depends on; asserting it here
# means a change to the boundary scan cannot silently swallow the end of a reply.
out7, upto7, _ = _speech_release(TEXT, 0, final=True, is_clean=clean)
check("TAIL CONTRACT: a trailing fragment with no terminal punctuation is NOT released",
      upto7 < len(TEXT) and TAIL not in " ".join(out7),
      f"upto={upto7} len={len(TEXT)}")
check("...so the caller is left something to flush",
      TEXT[upto7:].strip() != "", f"remainder={TEXT[upto7:][:20]!r}")

# An empty or boundary-free response must not spin or emit junk.
for label, txt in (("empty", ""), ("no sentence boundary", "no terminal punctuation here")):
    o, u, h = _speech_release(txt, 0, final=False, is_clean=clean)
    check(f"safe on {label} input", o == [] and h is False, f"got {o}")

failed = [n for n, ok, _ in _results if not ok]
print("\n" + "=" * 62)
print(f"{len(_results) - len(failed)}/{len(_results)} checks pass")
if failed:
    print("GATE FAIL:")
    for n in failed:
        print(f"  - {n}")
    sys.exit(1)
print("GATE PASS")
