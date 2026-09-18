"""
core/build/settle.py — what is already answerable, so only the residue is paid for.

N3, third half. Inquiry asks freely: the cost of this design is in ADJUDICATING
questions, not in asking them. Settle is what keeps that true — it resolves
everything already answerable and passes only the remainder to the Librarian.

THE ORDER IS THE MECHANISM, and it is policies first:

    1. POLICY   a standing decision already covers this class of question.
                Free, and it is the compounding step: every policy a prior run
                produced retires a class of question PERMANENTLY. This is the
                real reason questions arrive pre-answered over time, and why
                `depth: triage` becomes possible at all.

    2. DATA     the probe found rows, and the question is a single_point
                lookup. Answerable from evidence without judgment.

    3. RESIDUE  everything else reaches the Librarian — plus, separately, the
                questions that need a tool that does not exist yet, and the
                ones only the user can answer.

WHAT SETTLE DOES NOT DO: decide anything. A question resolved by policy carries
the policy id; a question resolved by data carries the evidence. Both remain
auditable, and a REPAIR can point at either. The one thing that never happens
here is a model being asked whether the data exists — that is probe.py's job,
and it is code.
"""

from __future__ import annotations

from typing import Any

from core.build import manifest as M
from core.build import policy as P
from core.build import probe as PR

# Statuses a settled row can carry, matching schemas.ROW_STATUSES.
SETTLED = "settled"
NEEDS_INTERVIEW = "needs_interview"
NEEDS_TOOL = "needs_tool"


def settle(question_set: dict, persona: str | None = None) -> dict:
    """
    Returns {rows, residue, interview_items, needs_tool, stats}.

    `rows` are partial Answer Ledger rows carrying only the CODE-WRITTEN block
    — data_available, evidence, condensed_from, status. The Librarian fills the
    model-written fields for the residue and never touches these; schemas.py
    strips any it writes anyway and re-injects from here.
    """
    spine = question_set.get("spine") or []
    rows: list[dict] = []
    residue: list[dict] = []
    interview: list[dict] = []
    tool_gaps: set[str] = set()

    for question in spine:
        if not isinstance(question, dict):
            continue
        row, disposition = _settle_one(question, persona)
        rows.append(row)
        if disposition == "residue":
            residue.append(question)
        elif disposition == NEEDS_INTERVIEW:
            interview.append({
                "question_id": question.get("id", ""),
                "text": question.get("text", ""),
                "why": "only the user can answer this",
            })
        elif disposition == NEEDS_TOOL:
            tool_gaps.update(row.get("needs_tool") or [])

    return {
        "rows": rows,
        "residue": residue,
        "interview_items": interview,
        "needs_tool": sorted(tool_gaps),
        "stats": {
            "asked": len(spine),
            "settled_by_policy": sum(1 for r in rows if r.get("settled_by") == "policy"),
            "settled_by_data": sum(1 for r in rows if r.get("settled_by") == "data"),
            "to_librarian": len(residue),
            "to_interview": len(interview),
            "needs_tool": len(tool_gaps),
        },
    }


def _settle_one(question: dict, persona: str | None) -> tuple[dict, str]:
    question_id = str(question.get("id") or "")
    text = str(question.get("text") or "")
    klass = str(question.get("class") or "")
    sources = [str(s) for s in (question.get("candidate_sources") or [])]

    base = {
        "question_id": question_id,
        "data_available": False,
        "evidence": [],
        "condensed_from": 0,
        "status": SETTLED,
    }

    # 1. Policy. Free, exact where a class is declared retired, and the step
    #    that makes this cheaper on every subsequent run.
    hit = P.resolve(text, klass, persona)
    if hit:
        return {**base, "settled_by": "policy",
                "resolved_by_policy": hit.get("id", ""),
                "policy_match": hit.get("_match", ""),
                "policy_score": round(float(hit.get("_score") or 0.0), 3)}, SETTLED

    # 2. Data. Only sources that are actually in the manifest are probed; the
    #    literal "user" is not a source and resolves to an interview item.
    probeable = [s for s in sources if s != M.USER_SOURCE and M.source(s)]
    user_only = bool(sources) and not probeable

    if not probeable:
        if user_only:
            return {**base, "settled_by": "", "status": NEEDS_INTERVIEW}, NEEDS_INTERVIEW
        return {**base, "settled_by": ""}, "residue"

    records = PR.probe_all(probeable, persona)
    summary = PR.summarise(records)
    row = {
        **base,
        "data_available": summary["data_available"],
        "evidence": records,
        "settled_by": "",
    }

    if summary["needs_tool"]:
        # The known Librarian gaps (plan section 9) land here on run 1 and are
        # EXPECTED. A question whose only source has no tool is how Build
        # discovers its own substrate, not a failure of the question.
        return {**row, "status": NEEDS_TOOL,
                "needs_tool": summary["needs_tool"]}, NEEDS_TOOL

    # A single_point question with rows behind it is answered by the evidence.
    # A behavioural one is not: "how does he talk about work stress" has rows
    # and still needs a judgment over them, which is the Librarian's job.
    if summary["data_available"] and _is_single_point(probeable):
        return {**row, "settled_by": "data",
                "condensed_from": summary["rows_total"]}, SETTLED

    return row, "residue"


def _is_single_point(source_ids: list[str]) -> bool:
    """True when every named source is a lookup rather than a range read."""
    kinds = {(M.source(s) or {}).get("kind") for s in source_ids}
    return bool(kinds) and kinds <= {"single_point"}


def merge_code_block(model_row: dict, code_row: dict) -> dict:
    """
    Re-inject the code-written block over whatever the model wrote.

    Called after the Librarian returns. schemas.strip_code_written() removes
    the model's version before validation; this puts the real one back. The two
    together are what make `data_available` evidence rather than an impression.
    """
    from core.build.schemas import strip_code_written, CODE_WRITTEN_LEDGER_FIELDS
    cleaned = strip_code_written(model_row)
    injected = {k: code_row[k] for k in CODE_WRITTEN_LEDGER_FIELDS if k in code_row}
    return {**cleaned, **injected}
