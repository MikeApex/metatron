"""
tests/test_build_brief.py — N8's output contract, which crossed three layers
with nothing converting.

THE DEFECT THIS SUITE EXISTS FOR (cold review, 2026-09-24). Three files
disagreed about what a review finding is:

  · `.claude/agents/adversarial-reviewer.md` emits MARKDOWN — `Wrong:` /
    `Fails:` / `Costs:` prose under `## STRUCTURAL` and `## LOCAL`.
  · `.claude/commands/build.md` read `f["wrong"]` off each finding.
  · `brief.append_review()` renders `finding['title']` and `finding['detail']`.

So the first structural finding at N8 either raised `TypeError` on the index or
wrote `**?** —` into the brief — at the one node the send-back bound depends on.
`adversarial-reviewer` is the SIXTH subagent `/build` spawns and the only one
Build does not own, which is why it is the only contract that crosses layers and
why it was the one left out of scope.

THE FIXTURES ARE THE THREE REAL REVIEWS OF THIS COMMAND, on disk in
archive/plans/. A handwritten sample would be a sample of what I think the
reviewer emits; these are what it actually emitted, including the wrapped
`Costs:` lines and the non-contiguous global ranking.

Usage:
    python3 tests/test_build_brief.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.build import brief as B                       # noqa: E402
from core.build import driver as D                      # noqa: E402
from tests.support.runner import Suite                  # noqa: E402

suite = Suite("build brief")
check = suite.check

REVIEWS = sorted(
    (ROOT / "archive" / "plans").glob("adversarial_review_build_command_*.md"))


def _round(n: int) -> str:
    return next(p for p in REVIEWS if p.name.endswith(f"_r{n}.md")).read_text()


# ---------------------------------------------------------------------------
# The fixtures are real
# ---------------------------------------------------------------------------

@check("the three real review reports are on disk — this suite is not hypothetical")
def _():
    assert len(REVIEWS) == 3, [p.name for p in REVIEWS]
    for n in (1, 2, 3):
        assert "Wrong:" in _round(n) or "CLOSED" in _round(n), n


# ---------------------------------------------------------------------------
# The parse
# ---------------------------------------------------------------------------

@check("round 1 parses into 4 structural and 6 local findings")
def _():
    review = B.parse_review(_round(1))
    assert len(review["structural"]) == 4, review["structural"]
    assert len(review["local"]) == 6, [f["rank"] for f in review["local"]]


@check("the GLOBAL rank is preserved across both blocks, non-contiguously")
def _():
    review = B.parse_review(_round(1))
    assert [f["rank"] for f in review["structural"]] == [1, 2, 3, 4]
    assert [f["rank"] for f in review["local"]] == [5, 6, 7, 8, 9, 10], (
        "the agent definition keeps one ranking across the two blocks; "
        "renumbering within a block would lose which finding does most damage")


@check("every finding carries the three sentences, verbatim")
def _():
    first = B.parse_review(_round(1))["structural"][0]
    assert first["wrong"].startswith("The command delegates the review's send-back")
    assert first["fails"].startswith("After a structural finding")
    assert first["costs"].startswith("The one bounded send-back")
    assert first["confidence"] == "high", first


@check("a WRAPPED Costs line is joined, not truncated at the newline")
def _():
    costs = B.parse_review(_round(1))["local"][1]["costs"]
    assert costs.endswith("high."), costs
    assert "hand-editing" in costs, (
        "the reviewer wraps its sentences; a line-at-a-time parse loses the "
        f"back half of every one: {costs}")


@check("the reference line is kept and does not become the finding text")
def _():
    first = B.parse_review(_round(1))["structural"][0]
    assert "driver.py:next_step" in first["refs"], first["refs"]
    assert "driver.py" not in first["wrong"], (
        "the path list is location, not the claim")


# ---------------------------------------------------------------------------
# What each of the three consumers needs
# ---------------------------------------------------------------------------

@check("brief.append_review renders a real title and detail, never `**?** —`")
def _():
    review = B.parse_review(_round(1))
    text = B.append_review("# brief\n", review)
    assert "**?**" not in text, (
        "this is the pre-fix rendering: append_review reads finding['title'], "
        "which raw markdown does not have")
    assert "1. **The command delegates the review's send-back" in text, text[:600]
    assert "## Adversarial review" in text
    assert text.index("### Structural") < text.index("### Local")


@check("driver.defect_lines turns findings into the send-back's defect list")
def _():
    review = B.parse_review(_round(1))
    lines = D.defect_lines(review["structural"])
    assert len(lines) == 4, lines
    assert all(isinstance(line, str) and line for line in lines), lines
    assert lines[0].startswith("The command delegates"), lines[0]


@check("defect_lines still accepts plain strings — the old callers are not broken")
def _():
    assert D.defect_lines(["a defect", "another"]) == ["a defect", "another"]
    assert D.defect_lines(None) == []
    assert D.defect_lines([{"title": "only a title"}]) == ["only a title"]


@check("THE WHOLE N8 PATH RUNS on a real report without an index or a KeyError")
def _():
    review = B.parse_review(_round(1))
    B.write.__doc__                      # the write is exercised by the driver suite
    text = B.append_review("# brief\n", review)
    defects = D.defect_lines(review["structural"])
    assert text and defects, (text[:80], defects[:1])


# ---------------------------------------------------------------------------
# Shapes that are not the happy path
# ---------------------------------------------------------------------------

@check("an empty block parses to an empty list, not a phantom finding")
def _():
    review = B.parse_review(
        "## STRUCTURAL\n\nnone\n\n## LOCAL\n\n1. [x]\nWrong: a thing.\n")
    assert review["structural"] == [], review["structural"]
    assert len(review["local"]) == 1


@check("the VERDICT escape hatch becomes one structural finding")
def _():
    review = B.parse_review(
        "VERDICT: More than ten significant defects. The plan fails as a whole "
        "and should be rebuilt rather than patched. Largest structural cause: "
        "the control layer is described, not built.")
    assert review["verdict"].startswith("More than ten"), review
    assert len(review["structural"]) == 1, review
    assert D.defect_lines(review["structural"])[0].startswith("More than ten")


@check("a report in NO known format is KEPT whole rather than lost or raised")
def _():
    review = B.parse_review("the reviewer said something else entirely")
    assert review["structural"] == [] and review["local"] == []
    assert review["unparsed"] == "the reviewer said something else entirely", (
        "a review is evidence; a format change must not silently discard it")


@check("a dict passes through untouched — a replayed artifact is not re-parsed")
def _():
    already = {"schema": B.REVIEW_SCHEMA, "structural": [], "local": []}
    assert B.parse_review(already) is already


@check("a verify round's ## NEW block is treated as structural")
def _():
    review = B.parse_review(_round(2))
    assert len(review["structural"]) == 2, (
        "round 2's two NEW findings go back to the Planner like any structural "
        f"one: {[f['rank'] for f in review['structural']]}")
    assert review["structural"][0]["wrong"].startswith("The driver is asked only")


@check("a fenced report is unwrapped before parsing")
def _():
    fenced = "```\n## STRUCTURAL\n\n1. [x]\nWrong: a thing.\n```"
    assert len(B.parse_review(fenced)["structural"]) == 1


suite.exit()
