"""
tests/test_context_user_text_plumbing.py — the user's turn reaches thread expiry.

Open-thread expiry grants a thread a reprieve only when the USER engages it
(tools/context_tracker.py). That rule is only as good as what the pipeline hands
it, and there are exactly two ways to get it wrong:

  1. Pass nothing, and every thread expires on schedule regardless of the user
     talking about it all week.
  2. Pass the scheduler's prompt on a proactive session, and the system grants
     its own threads a reprieve by talking to itself — which is precisely the
     bug `82d394b` fixed in the repeated-instruction protocol, re-created one
     layer down.

Both are invisible to the context_tracker unit tests, which never see the
pipeline. Run: python3 tests/test_context_user_text_plumbing.py
"""

import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent))

from core import orchestrator  # noqa: E402

_results: list[tuple[bool, str]] = []


def check(label: str, condition: bool) -> None:
    _results.append((condition, label))
    print(f"  {'PASS' if condition else 'FAIL'}  {label}")


def captured_user_text(ctx: dict, user_text) -> object:
    """Call persist_context_block and report the user_text the tracker received."""
    seen = {}

    def _fake_write(**kwargs):
        seen.update(kwargs)
        return "ok"

    with mock.patch("tools.context_tracker.write_context_tracker", _fake_write):
        orchestrator.persist_context_block(ctx, user_text=user_text)
    return seen.get("user_text", "__absent__")


def main() -> int:
    ctx = {"open_threads": ["post-travel recovery"], "patterns": [],
           "follow_ups": [], "held_items": []}

    check("a real user turn is forwarded to the tracker",
          captured_user_text(ctx, "how's the travel recovery going") ==
          "how's the travel recovery going")

    check("None is forwarded as None, not dropped",
          captured_user_text(ctx, None) is None)

    check("user_text is passed by keyword, so ordering cannot silently shift it",
          captured_user_text(ctx, "x") == "x")

    # The two call sites both compute `None if is_proactive else user_input`.
    # Assert that expression is present at both, so a later edit that passes
    # `user_input` unconditionally fails here rather than in production.
    #
    # Anchored on `persist_context_block(` rather than counting the bare
    # expression: since 2026-08-18 `filter_output()`'s echo exemption
    # (`[DB-0808-05]`) uses the identical guard for the identical reason, so an
    # unanchored count reads 4 and this check failed on a change that was
    # correct. Anchoring keeps it measuring the two call sites it names.
    src = (Path(__file__).parent.parent / "core" / "orchestrator.py").read_text()
    guarded = src.count(
        "persist_context_block(_ctx, user_text=None if is_proactive else user_input)")
    check("both pipeline call sites guard on is_proactive", guarded == 2)
    check("the filter's echo exemption is guarded the same way",
          src.count("user_text=None if is_proactive else user_input") >= 4)
    check("no call site passes user_input unguarded",
          "persist_context_block(_ctx, user_text=user_input)" not in src)

    # An empty ctx must still not write — unchanged behaviour.
    wrote = []
    with mock.patch("tools.context_tracker.write_context_tracker",
                    lambda **k: wrote.append(k)):
        orchestrator.persist_context_block(None, user_text="anything")
    check("an absent context block writes nothing", not wrote)

    print()
    failed = [label for ok, label in _results if not ok]
    if failed:
        print(f"{len(failed)} check(s) FAILED:")
        for label in failed:
            print(f"  - {label}")
        return 1
    print("All context user_text plumbing checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
