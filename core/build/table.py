"""
core/build/table.py — N10. The question table, and the two things it exposes.

Plan: archive/plans/build_vertical_plan_2026-09-24.md section 3 (N10), section 4.

WRITTEN BY CODE, NEVER BY A MODEL, and that is not a style preference. The table
is the audit of whether ruling 6 held — whether every question actually
travelled and whether every plan item actually rests on one. A model asked to
render it would be marking its own homework, and the two derived sections below
are precisely the ones it has an incentive to leave empty.

    QUESTIONS THAT SHAPED NOTHING   asked, answered, cited by no plan item.
    PLAN ITEMS NO QUESTION SUPPORTS  decided by the Planner on its own.

Neither is automatically a defect. A question that shaped nothing may have been
worth asking and answered "no"; a plan item with no citation may be an obvious
consequence. What they are is THE LIST THE REVIEWER READS FIRST, and the reason
the table is rendered BEFORE the review rather than after it (finding 6): the
reviewer is spawned on the brief, and the brief carries this.

THE ACCEPTANCE COLUMN IS EMPTY UNTIL N14. It is rendered a second time after
acceptance, with the result beside each row — so the table is also the record of
which questions the built thing actually answered.
"""

from __future__ import annotations

from core.build.schemas import derive_status


def render(question_set: dict, ledger: dict, plan: dict | None = None,
           acceptance: dict | None = None) -> str:
    """The whole table as markdown. `plan` absent renders the inventory half only."""
    rows = _rows(question_set, ledger, plan, acceptance)
    out = ["## Question table", ""]
    out.append("| id | question | class | verdict | where it is / what it says "
               "| if a user lacks it | status | shaped | acceptance |")
    out.append("|---|---|---|---|---|---|---|---|---|")
    for row in rows:
        out.append(
            f"| {row['id']} | {_cell(row['text'])} | {row['class']} "
            f"| {row['verdict']} | {_cell(row['location'])} "
            f"| {_cell(row['lacks'])} | {row['status']} "
            f"| {_cell(', '.join(row['shaped']))} | {_cell(row['acceptance'])} |")
    if not rows:
        out.append("| *(no questions)* | | | | | | | | |")

    out += ["", "### Questions that shaped nothing", ""]
    orphans = [r for r in rows if not r["shaped"]]
    out += ([f"- `{r['id']}` {r['text']}" for r in orphans] if orphans
            else ["*(none — every question is cited by at least one plan item)*"])

    out += ["", "### Plan items no question supports", ""]
    unsupported = uncited_plan_items(plan, ledger)
    out += ([f"- {item}" for item in unsupported] if unsupported
            else ["*(none — every plan gate carries a citation)*"])
    return "\n".join(out) + "\n"


def _rows(question_set: dict, ledger: dict, plan: dict | None,
          acceptance: dict | None) -> list[dict]:
    """
    EVERY LEDGER ROW APPEARS ONCE. Keyed on the question id, so a ledger holding
    two rows for one question renders one line and the duplicate is a schema
    defect rather than a silently doubled table.
    """
    by_question = {}
    for row in ledger.get("rows") or []:
        if isinstance(row, dict) and row.get("question_id"):
            by_question.setdefault(str(row["question_id"]), row)

    citations = _citations_by_question(plan)
    results = (acceptance or {}).get("by_question") or {}

    out: list[dict] = []
    for question in question_set.get("spine") or []:
        if not isinstance(question, dict):
            continue
        qid = str(question.get("id") or "")
        row = by_question.pop(qid, {})
        out.append({
            "id": qid,
            "text": str(question.get("text") or ""),
            "class": str(question.get("class") or ""),
            "verdict": str(row.get("verdict") or "—"),
            "location": _location(row),
            "lacks": str(row.get("if_user_lacks_it") or "—"),
            "status": derive_status(row) if row else "missing",
            "shaped": citations.get(qid, []),
            "acceptance": str(results.get(qid) or ""),
        })

    # A ledger row whose question is not in the spine. Rendered rather than
    # dropped: it is a defect the validator already names, and showing it is how
    # the reviewer sees the same thing the validator did.
    for qid, row in sorted(by_question.items()):
        out.append({
            "id": qid, "text": "*(no question with this id in the spine)*",
            "class": "—", "verdict": str(row.get("verdict") or "—"),
            "location": _location(row),
            "lacks": str(row.get("if_user_lacks_it") or "—"),
            "status": derive_status(row), "shaped": citations.get(qid, []),
            "acceptance": "",
        })
    return out


def _location(row: dict) -> str:
    """
    Where the answer is, or what it says. NO SAMPLE, NO VALUE.

    The inventory names a source, a form and a period. It does not carry a row
    the Librarian read, and this renderer emits only declared fields — which is
    the structural half of keeping persona content out of a document that goes
    to a reviewer subagent.
    """
    if not row:
        return "—"
    inventory = row.get("inventory") or {}
    parts = []
    if inventory.get("source"):
        parts.append(str(inventory["source"]))
    if inventory.get("form"):
        parts.append(f"({inventory['form']})")
    coverage = inventory.get("coverage") or {}
    if coverage.get("from") and coverage.get("to"):
        parts.append(f"{coverage['from']}→{coverage['to']}")
    gap = inventory.get("gap") or row.get("gap")
    if gap:
        parts.append(f"gap: {gap}")
    if row.get("decision"):
        parts.append(f"decided: {row['decision']}")
    return " ".join(parts) or "—"


def _citations_by_question(plan: dict | None) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for citation in (plan or {}).get("citations") or []:
        if not isinstance(citation, dict):
            continue
        qid = str(citation.get("question_id") or "")
        gate = str(citation.get("gate") or "")
        if qid and gate:
            out.setdefault(qid, []).append(gate)
    return out


def uncited_plan_items(plan: dict | None, ledger: dict | None = None) -> list[str]:
    """
    Plan gates with no citation — the second derived section.

    Reads the plan's own gates rather than a list here, so a gate added to the
    schema appears in this section on the day it is added rather than on the day
    someone remembers to update the renderer.
    """
    from core.build.schemas import PLAN_GATES
    if not plan:
        return []
    cited = {str(c.get("gate") or "") for c in plan.get("citations") or []
             if isinstance(c, dict)}
    return [f"`{gate}` — present in the plan and cited by no question"
            for gate in PLAN_GATES
            if plan.get(gate) not in (None, "", [], {}) and gate not in cited]


def _cell(text: str) -> str:
    """One table cell: pipes escaped, newlines flattened, nothing truncated."""
    return str(text or "—").replace("|", "\\|").replace("\n", " ").strip() or "—"
