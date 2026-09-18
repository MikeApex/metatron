"""
tests/test_build_spine.py — the compass rule, tested against a real pair.

THE CLAIM UNDER TEST: the spine validator DISCRIMINATES rather than merely
fires. The evidence is that it sorts a pass/fail pair correctly — and that the
pair was produced on 2026-09-17, before the rule existed, so neither half was
written to satisfy it.

Turn 2 of the reference transcript answered the invitation on its own terms:
feasibility second, nothing asking what the boss was for, no altitude answer.
Turn 3's critique named it exactly — "you've framed this narrowly and
tactically... no reflection on broader life goals, opportunity cost, or the
greater context of the boss' life" — and turn 4 rewrote the spine with intent
first and feasibility sixth.

WHY THIS TEST IS IN PHASE 1 AND NOT PHASE 5 WITH THE AGENT FILES. A rule that
can be tested before the agent that must obey it exists is a rule that cannot
quietly be relaxed to make the agent work. The ordering constraint is the one
piece of this design most likely to be softened under delivery pressure, so it
gets its evidence first.

THE FIXTURE IS REQUIRED, NEVER OPTIONAL. If it is missing this test FAILS
rather than skipping. A skipping test is precisely how a compass rule gets
quietly relaxed, which is the failure mode this file exists to prevent.

Standalone runner (no pytest dependency), matching tests/ convention.

Usage:
    python3 tests/test_build_spine.py

Exits 0 if every check passes, 1 otherwise.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.build.schemas import (  # noqa: E402
    CLASS_INDEX, validate_question_set,
)

FIXTURE = ROOT / "tests" / "fixtures" / "inquiry_rsvp_2026-09-17.md"

_results: list[tuple[str, bool, str]] = []


def check(name: str):
    def wrap(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except AssertionError as e:
            _results.append((name, False, f"assertion: {e}"))
        except Exception as e:
            _results.append((name, False, f"{type(e).__name__}: {e}"))
        return fn
    return wrap


_BLOCK_RE = re.compile(r"<!-- fixture: (\w+) -->\s*\n```json\n(.*?)\n```", re.S)


def _load_fixture() -> dict:
    if not FIXTURE.exists():
        raise FileNotFoundError(
            f"{FIXTURE} is missing. The verbatim pass/fail pair is the evidence "
            "that the compass rule discriminates; without it this test proves "
            "nothing and must not be skipped."
        )
    raw = FIXTURE.read_text(encoding="utf-8")
    blocks = {name: json.loads(body) for name, body in _BLOCK_RE.findall(raw)}
    for required in ("turn2", "turn4", "manifest_ids"):
        if required not in blocks:
            raise KeyError(f"fixture block {required!r} not found in {FIXTURE}")
    return blocks


FIX = _load_fixture()
MANIFEST = set(FIX["manifest_ids"])
TURN2, TURN4 = FIX["turn2"], FIX["turn4"]


# ---------------------------------------------------------------------------
# The pair
# ---------------------------------------------------------------------------

@check("turn 2 (the filter) FAILS validation")
def _():
    defects = validate_question_set(TURN2, manifest_ids=MANIFEST)
    assert defects, (
        "turn 2 validated clean — the rule does not discriminate. This is the "
        "single most important assertion in the Build test suite."
    )


@check("turn 4 (the compass) PASSES validation")
def _():
    defects = validate_question_set(TURN4, manifest_ids=MANIFEST)
    assert not defects, (
        "turn 4 should validate clean; defects: " + "; ".join(defects)
    )


# ---------------------------------------------------------------------------
# Turn 2 fails for the RIGHT reasons — three independent grounds.
#
# Asserted separately because "it failed" is worth very little: a validator
# that rejected both turns for a missing header would pass the two checks
# above while discriminating nothing.
# ---------------------------------------------------------------------------

@check("turn 2 fails on spine order — feasibility (class 5) precedes cost (class 3)")
def _():
    defects = validate_question_set(TURN2, manifest_ids=MANIFEST)
    assert any("not ordered by class index" in d for d in defects), defects


@check("turn 2 fails on feasibility-before-intent, named as the inversion it is")
def _():
    defects = validate_question_set(TURN2, manifest_ids=MANIFEST)
    hit = [d for d in defects if "precedes every intent question" in d]
    assert hit, defects
    assert "empty capacity" in hit[0], (
        "the defect message should name the stance that was violated, because "
        "it is what rung 2's retry prompt carries: " + hit[0]
    )


@check("turn 2 fails on having no intent question at all")
def _():
    defects = validate_question_set(TURN2, manifest_ids=MANIFEST)
    assert any("no intent question" in d for d in defects), defects


@check("turn 2 fails on the missing altitude answer")
def _():
    defects = validate_question_set(TURN2, manifest_ids=MANIFEST)
    assert any("disposition must be one of" in d for d in defects), defects
    assert any("disposition_evidence is empty" in d for d in defects), defects


@check("turn 2's three grounds are independent — no single fix rescues it")
def _():
    # Give turn 2 the altitude answer it lacked. The spine is untouched, so the
    # ordering failures must survive: they are what the critique was about.
    patched = {
        **TURN2,
        "disposition": "new",
        "disposition_evidence": (
            "Checked the calendar and the crm; neither performs an allocation "
            "judgement over a stated intent."
        ),
    }
    defects = validate_question_set(patched, manifest_ids=MANIFEST)
    assert any("not ordered by class index" in d for d in defects), defects
    assert any("no intent question" in d for d in defects), defects


# ---------------------------------------------------------------------------
# The ordering constraint is load-bearing, not decorative
# ---------------------------------------------------------------------------

@check("reordering turn 4's spine to put feasibility first breaks it")
def _():
    spine = list(TURN4["spine"])
    feasibility = next(q for q in spine if q["class"] == "feasibility")
    reordered = [feasibility] + [q for q in spine if q is not feasibility]
    for position, question in enumerate(reordered, start=1):
        question = dict(question)
        question["id"] = f"q{position}"
        reordered[position - 1] = question

    defects = validate_question_set(
        {**TURN4, "spine": reordered}, manifest_ids=MANIFEST)
    assert any("precedes every intent question" in d for d in defects), (
        "moving feasibility to the front of a passing set must fail it — "
        "otherwise position is not actually being checked: " + str(defects))


@check("turn 4's class sequence is non-decreasing, and reaches feasibility sixth")
def _():
    sequence = [CLASS_INDEX[q["class"]] for q in TURN4["spine"]]
    assert sequence == sorted(sequence), sequence
    position = next(
        i for i, q in enumerate(TURN4["spine"], start=1)
        if q["class"] == "feasibility")
    assert position == 6, (
        f"feasibility is at position {position}; turn 4 states plainly that "
        "'feasibility doesn't appear until the fourth question' of its own "
        "eight, which is position 6 once the surface question is encoded")


@check("removing turn 4's surface question fails it — and ONLY on that ground")
def _():
    # The fixture documents its one addition (q7, cut from turn 4's body rather
    # than its numbered list). This asserts the claim made there: the addition
    # makes turn 4 a clean pass, it does not decide which turn passes.
    spine = [q for q in TURN4["spine"] if q["class"] != "surface"]
    for position, question in enumerate(spine, start=1):
        question = dict(question)
        question["id"] = f"q{position}"
        spine[position - 1] = question

    defects = validate_question_set({**TURN4, "spine": spine}, manifest_ids=MANIFEST)
    assert len(defects) == 1, f"expected exactly one defect, got {defects}"
    assert "no surface question" in defects[0], defects


# ---------------------------------------------------------------------------
# Provenance — the encoding must stay auditable against the transcript
# ---------------------------------------------------------------------------

@check("every encoded question carries the transcript text it was cut from")
def _():
    for label, artifact in (("turn2", TURN2), ("turn4", TURN4)):
        for question in artifact["spine"]:
            quote = str(question.get("source_quote") or "").strip()
            assert len(quote) > 20, (
                f"{label} {question['id']} has no usable source_quote — the "
                "encoding stops being auditable against the transcript")


@check("the verbatim reference transcript is on disk beside the fixture")
def _():
    reference = ROOT / "archive" / "plans" / "inquiry_reference_rsvp_2026-09-17.md"
    assert reference.exists(), f"{reference} is missing"
    body = reference.read_text(encoding="utf-8")
    assert "I built a filter, not a compass" in body, (
        "the reference does not contain the turn-4 critique the rule is named for")
    assert "The amended decision spine" in body, (
        "the reference does not contain turn 4's rewritten spine")


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    failed = 0
    for name, ok, detail in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}{'' if ok else '  — ' + detail}")
        failed += 0 if ok else 1
    print(f"\n{len(_results) - failed}/{len(_results)} passed")
    sys.exit(1 if failed else 0)
