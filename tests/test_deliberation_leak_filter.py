#!/usr/bin/env python3
"""
Tier 5 of filter_output() — the Synthesizer reading its own thinking aloud.

WHAT THIS IS ABOUT, IN THE USER'S TERMS
---------------------------------------
On 2026-08-12 Mike asked a question and got back the model's working-out instead of an
answer: "Step-by-step reasoning: 1. Analyze what the user is really asking..." — cut off
mid-sentence. Tier 4 was built for that instance because it quoted the instruction file
verbatim. Tier 5 exists because **the general case quotes nothing at all**.

WHY NO UPSTREAM FIX IS POSSIBLE — measured, not assumed (2026-08-18)
-------------------------------------------------------------------
The obvious theory was a plumbing fault: the model sends its private reasoning on a
separate channel and the code accidentally merges it into the reply. **It does not.**
Probing the live Vertex OpenAI-compat endpoint the Synthesizer actually runs on, the
first streamed delta was literally:

    ChoiceDelta(content="**Step-by-Step Reasoning:**\\n\\n1.  **Analyze the User's", ...)

Reasoning arrives in `content`, indistinguishable from the answer. The only extra field
on the stream is an opaque `thought_signature`. `include_thoughts: False` changes
nothing; `thinking_budget: 0` does work but by disabling thinking altogether, which
degrades the one agent that talks to the user — rejected as the wrong trade.

So the filter is not a backstop here. It is the only available control, which is why
this file exists rather than a note saying tier 4 covers it.

THE DESIGN CONSTRAINT THAT SHAPES EVERY TEST BELOW
--------------------------------------------------
Suppression replaces the **entire response** with a canned fallback. A false positive
therefore costs the user their whole answer — a worse outcome than the leak on any
ordinary turn. That is why tier 5 matches only a deliberation header **at the very
start** of a response, and why more than half of these cases assert that ordinary
answers survive untouched.

Run: python tests/test_deliberation_leak_filter.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.orchestrator import _CANNED_FALLBACK, filter_output  # noqa: E402

_FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"  PASS  {label}")
    else:
        print(f"  FAIL  {label}" + (f"  — {detail}" if detail else ""))
        _FAILURES.append(label)


def suppressed(text: str, user_text: str | None = None) -> bool:
    return filter_output(text, "synthesizer", user_text=user_text) != text


# --------------------------------------------------------------------------
def test_the_leak_shapes() -> None:
    """A reply that opens by narrating its own reasoning must never reach the user."""
    print("\nThe model's working-out must not be delivered as an answer")

    # The shape actually observed streaming off the live endpoint, 2026-08-18.
    observed = ("**Step-by-Step Reasoning:**\n\n"
                "1.  **Analyze the User's Request:** They have three meetings and a "
                "deadline. I need to weigh which commitments are load-bearing.\n"
                "2.  **Formulate the answer:** Drop the second meeting.\n\n"
                "You should drop the 2pm sync.")
    check("the exact shape captured from the live endpoint", suppressed(observed))

    for label, text in [
        ("lowercase variant", "**Step-by-step Reasoning:**\n1. Weigh it up.\nDrop the 2pm."),
        ("bare, no markdown", "Reasoning: the deadline is external. Drop the 2pm."),
        ("possessive framing", "My thought process:\n- the deadline is fixed"),
        ("markdown heading", "## Analysis:\nThe deadline dominates. Drop the 2pm."),
        ("italic framing", "*Internal deliberation:* which of these is load-bearing?"),
        ("chain of thought", "Chain of thought: first, the deadline."),
        ("thinking it through", "Thinking through: the 2pm is the weakest."),
        ("underscore emphasis", "__Analysis:__ drop the 2pm sync."),
        ("leading whitespace", "\n\n   **Reasoning:** drop the 2pm."),
    ]:
        check(label, suppressed(text))

    # Obfuscation: a zero-width space must not be the difference between
    # suppressed and delivered — the same argument tier 1 already makes.
    check("zero-width character spliced into the header",
          suppressed("**Reason​ing:** drop the 2pm sync."))

    check("suppression returns the canned fallback, not a truncation",
          filter_output("Reasoning: drop the 2pm.", "synthesizer") == _CANNED_FALLBACK)


# --------------------------------------------------------------------------
def test_ordinary_answers_survive() -> None:
    """The expensive failure. A false positive costs the user the whole reply."""
    print("\nOrdinary answers must reach the user untouched")

    for label, text in [
        ("a plain answer",
         "Drop the 2pm sync — it is the only one without a decision attached."),
        ("'Analysis' as a real noun, not a header",
         "Analysis of your spending suggests the subscriptions are the drift."),
        ("a numbered list, which is ordinary",
         "Here are three options:\n1. Drop the 2pm\n2. Shorten the 4pm\n3. Move the deadline"),
        ("'My thought' without the header colon",
         "My thought is that you should keep the 10am and drop the rest."),
        ("'Reasoning' opening a real sentence",
         "Reasoning about this kind of trade-off is what tires you out — drop the 2pm."),
        ("'Step by step' as ordinary advice",
         "Step by step, you can get the deck done before Thursday."),
        ("a bare numbered answer",
         "1. Drop the 2pm.\n2. Keep the 10am.\n3. Tell Priya you will send notes."),
        ("'Thinking through' with no colon",
         "Thinking through your week I would say Tuesday is the crunch."),
        ("an answer that mentions analysis later",
         "Drop the 2pm. Analysis: your calendar is fine after that."),
        ("a question back to the user",
         "Which of the three matters most to you? I would drop the 2pm."),
    ]:
        check(label, not suppressed(text), "wrongly suppressed")


# --------------------------------------------------------------------------
def test_scope_is_the_opening_only() -> None:
    """
    A documented, deliberate limit — asserted so it is a known boundary rather
    than a surprise later.

    Tier 5 fires only on the OPENING of a response. Deliberation buried mid-answer
    is not caught, because the only pattern loose enough to catch it there also
    fires on ordinary prose, and the cost of that is the user's whole reply.
    """
    print("\nScope: the opening only, deliberately")
    mid = ("You should drop the 2pm sync.\n\n"
           "Reasoning: the deadline is external and the meetings are not.")
    check("deliberation mid-answer is NOT caught (known limit, not a bug)",
          not suppressed(mid))


# --------------------------------------------------------------------------
def test_reaches_the_streaming_path() -> None:
    """
    The 2026-08-12 leak was on the streaming path, so tier 5 has to work there.

    That path buffers the full response, splits off the [CONTEXT] block, and filters
    only the visible remainder before emitting [RETRACT] on suppression. This asserts
    the filter still fires on what that path actually hands it — a check worth having,
    because a fix verified only against a whole raw response could miss here.
    """
    print("\nIt must fire on what the streaming path actually filters")
    from core.orchestrator import split_context_block

    complete = ("**Step-by-Step Reasoning:**\n\n1. Weigh the options.\n\nDrop the 2pm.\n"
                "[CONTEXT]\n{\"open_threads\": []}\n[/CONTEXT]")
    visible, ctx = split_context_block(complete)
    check("the context block is split off first", ctx is not None or "[CONTEXT]" not in visible)
    check("and the visible remainder is still suppressed", suppressed(visible))


# --------------------------------------------------------------------------
def test_other_agents_unaffected() -> None:
    """Only the Synthesizer speaks to the user; internal output is not filtered."""
    print("\nInternal agents are not filtered")
    text = "**Reasoning:** the user is asking about their calendar."
    check("the Coordinator's package passes untouched",
          filter_output(text, "coordinator") == text)


if __name__ == "__main__":
    print("Tier 5 — the Synthesizer reading its own thinking aloud")
    print("=" * 62)
    test_the_leak_shapes()
    test_ordinary_answers_survive()
    test_scope_is_the_opening_only()
    test_reaches_the_streaming_path()
    test_other_agents_unaffected()
    print("=" * 62)
    if _FAILURES:
        print(f"FAIL — {len(_FAILURES)} check(s) failed:")
        for f in _FAILURES:
            print(f"  · {f}")
        sys.exit(1)
    print("PASS — all checks passed.")
