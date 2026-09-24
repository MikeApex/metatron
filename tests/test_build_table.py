"""
tests/test_build_table.py — the question table is the audit, so it must not lie.

Plan section 12, Question table row: every ledger row appears once; an uncited
question lands in "shaped nothing"; a plan item with no citation lands in
"unsupported"; the acceptance column is empty until N14.

WHY THIS SUITE MATTERS MORE THAN ITS SIZE SUGGESTS. The table is what the
reviewer reads first and what proves ruling 6 held. Its two derived sections are
exactly the ones a model rendering its own table would have an incentive to
leave empty — which is why the renderer is code, and why the thing worth testing
is that the sections FILL when they should.

Usage:
    python3 tests/test_build_table.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.build import table as TBL                      # noqa: E402
from tests.support import build_fixtures as F            # noqa: E402
from tests.support.runner import Suite                   # noqa: E402

suite = Suite("build question table")
check = suite.check

QS, LEDGER, PLAN = F.question_set(), F.answer_ledger(), F.build_plan()


@check("every ledger row appears EXACTLY once")
def _():
    text = TBL.render(QS, LEDGER, PLAN)
    for question in QS["spine"]:
        count = text.count(f"| {question['id']} |")
        assert count == 1, f"{question['id']} appears {count} times"


@check("a ledger holding two rows for one question still renders one line")
def _():
    ledger = F.answer_ledger()
    ledger["rows"].append(F.ledger_row("q2"))
    text = TBL.render(QS, ledger, PLAN)
    assert text.count("| q2 |") == 1, (
        "a duplicate row is a schema defect; the table must not silently double")


@check("an UNCITED question lands in 'shaped nothing'")
def _():
    plan = F.build_plan()
    plan["citations"] = [c for c in plan["citations"] if c["question_id"] != "q2"]
    text = TBL.render(QS, LEDGER, plan)
    section = text.split("### Questions that shaped nothing")[1]
    section = section.split("###")[0]
    assert "`q2`" in section, section


@check("with every question cited, 'shaped nothing' says so rather than going blank")
def _():
    plan = F.build_plan()
    plan["citations"] += [
        {"gate": "capability", "question_id": "q3", "ledger_row": "q3"},
        {"gate": "capability", "question_id": "q5", "ledger_row": "q5"},
    ]
    text = TBL.render(QS, LEDGER, plan)
    section = text.split("### Questions that shaped nothing")[1].split("###")[0]
    assert "none" in section.lower(), section


@check("a plan gate with NO citation lands in 'unsupported'")
def _():
    plan = F.build_plan()
    plan["citations"] = [c for c in plan["citations"] if c["gate"] != "surface_map"]
    unsupported = TBL.uncited_plan_items(plan)
    assert any("surface_map" in item for item in unsupported), unsupported
    assert "`surface_map`" in TBL.render(QS, LEDGER, plan)


@check("the unsupported list reads the plan's OWN gates, not a list in the renderer")
def _():
    from core.build.schemas import PLAN_GATES
    plan = F.build_plan()
    plan["citations"] = []
    unsupported = TBL.uncited_plan_items(plan)
    present = [g for g in PLAN_GATES if plan.get(g)]
    assert len(unsupported) == len(present), (
        f"a gate added to the schema must appear here the day it is added: "
        f"{unsupported} vs {present}")


@check("the acceptance column is EMPTY until N14")
def _():
    text = TBL.render(QS, LEDGER, PLAN)
    header = [line for line in text.splitlines() if line.startswith("| id |")][0]
    assert header.rstrip().endswith("acceptance |"), header
    for question in QS["spine"]:
        row = [ln for ln in text.splitlines() if ln.startswith(f"| {question['id']} |")][0]
        assert row.rstrip().endswith("| — |"), (
            f"acceptance must be empty before N14: {row}")


@check("after N14 the acceptance column carries the result")
def _():
    text = TBL.render(QS, LEDGER, PLAN,
                      acceptance={"by_question": {"q1": "pass on both personas"}})
    row = [ln for ln in text.splitlines() if ln.startswith("| q1 |")][0]
    assert "pass on both personas" in row, row


@check("the location column names a source and a period, and NO sample")
def _():
    text = TBL.render(QS, LEDGER, PLAN)
    row = [ln for ln in text.splitlines() if ln.startswith("| q2 |")][0]
    assert "log" in row and "2026-07-01" in row, row
    assert "watered" not in row.lower(), (
        "the renderer emits only DECLARED fields — a read row must never reach "
        f"a document a reviewer subagent is handed: {row}")


@check("a gap is rendered as the Librarian's own words")
def _():
    text = TBL.render(QS, LEDGER, PLAN)
    row = [ln for ln in text.splitlines() if ln.startswith("| q3 |")][0]
    assert "no entry names WHICH plant" in row, row


@check("the status column is derived, never read from the row")
def _():
    ledger = F.answer_ledger()
    ledger["rows"][1]["status"] = "settled"
    ledger["rows"][1]["verdict"] = "absent"
    ledger["rows"][1]["gap"] = "nothing recorded"
    text = TBL.render(QS, ledger, PLAN)
    row = [ln for ln in text.splitlines() if ln.startswith("| q2 |")][0]
    assert "| missing |" in row, (
        "a model-written status that disagrees with the verdict must lose: " + row)


@check("a pipe in a question's text does not break the table")
def _():
    qs = F.question_set()
    qs["spine"][0]["text"] = "Is it a | or a wall?"
    text = TBL.render(qs, LEDGER, PLAN)
    row = [ln for ln in text.splitlines() if ln.startswith("| q1 |")][0]
    assert "\\|" in row, f"the pipe must be escaped, not dropped: {row}"
    # Nine cells, so ten delimiters. Counting UNESCAPED pipes is the check:
    # an escaped one is content and must not split a cell.
    assert row.replace("\\|", "").count("|") == 10, row


@check("rendering without a plan still produces the inventory half")
def _():
    text = TBL.render(QS, LEDGER, None)
    assert "| q1 |" in text
    assert "### Questions that shaped nothing" in text


suite.exit()
