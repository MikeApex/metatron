"""
tests/test_build_schemas.py — each validator rejects its own malformation.

Plan section 12, Schemas row: v3's assertions that survive, plus the six the v4
rulings added.

THE METHOD: start from a VALID artifact, introduce EXACTLY ONE defect, assert
that defect is reported. Asserting on a hand-built broken artifact proves much
less — a validator that rejected everything would pass that version of this file.

Usage:
    python3 tests/test_build_schemas.py
"""

import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.build import schemas as S                      # noqa: E402
from tests.support import build_fixtures as F            # noqa: E402
from tests.support.runner import Suite, hit, only        # noqa: E402

suite = Suite("build schemas")
check = suite.check


# ---------------------------------------------------------------------------
# The baselines are valid. Everything below depends on this.
# ---------------------------------------------------------------------------

@check("the valid Question Set validates clean")
def _():
    defects = S.validate_question_set(F.question_set(), F.CAPABILITIES)
    assert not defects, defects


@check("the valid Answer Ledger validates clean")
def _():
    defects = S.validate_answer_ledger(
        F.answer_ledger(), question_ids=sorted(F.question_ids()))
    assert not defects, defects


@check("the valid BuildPlan validates clean")
def _():
    defects = S.validate_build_plan(F.build_plan(), red_paths=F.red_paths(),
                                    question_ids=F.question_ids())
    assert not defects, defects


# ---------------------------------------------------------------------------
# QuestionSet — the vacuum rule (ruling 5)
# ---------------------------------------------------------------------------

@check("a Question Set carrying candidate_sources FAILS")
def _():
    qs = F.question_set()
    qs["spine"][0]["candidate_sources"] = ["log", "user"]
    defects = S.validate_question_set(qs, F.CAPABILITIES)
    assert hit(defects, "candidate_sources"), defects
    assert hit(defects, "has seen no manifest"), (
        "the defect must say WHY — Inquiry has seen no manifest, so a named "
        "source is an invention rather than a stray field: " + str(defects))


@check("a set-level candidate_sources FAILS too, not only a per-question one")
def _():
    qs = F.question_set()
    qs["candidate_sources"] = ["log"]
    assert hit(S.validate_question_set(qs, F.CAPABILITIES), "candidate_sources")


@check("a Question Set carrying manifest_fingerprint FAILS")
def _():
    qs = F.question_set()
    qs["manifest_fingerprint"] = "deadbeef"
    assert hit(S.validate_question_set(qs, F.CAPABILITIES), "manifest_fingerprint")


@check("an EMPTY retired field is not a defect — absence is the healthy state")
def _():
    qs = F.question_set()
    qs["candidate_sources"] = []
    qs["policies_consulted"] = []
    assert not S.validate_question_set(qs, F.CAPABILITIES)


@check("a PLAN whose disposition_evidence restates the request FAILS")
def _():
    # The guard moved here from the Question Set on 2026-09-26 with the claim
    # itself: the Planner holds Read/Grep and the registry, so it is the stage
    # that can name what it actually checked.
    plan = F.build_plan()
    plan["capability"]["disposition_evidence"] = "nothing like this exists"
    assert hit(S.validate_build_plan(plan), "restates the request")


# ---------------------------------------------------------------------------
# AnswerLedger — the two verdicts (ruling 7)
# ---------------------------------------------------------------------------

@check("a `history` row carrying a variable_scope FAILS")
def _():
    ledger = F.answer_ledger()
    ledger["rows"][1]["variable_scope"] = "this_persona"
    ledger["rows"][1]["variable_name"] = "last_watered"
    defects = S.validate_answer_ledger(ledger,
                                       question_ids=sorted(F.question_ids()))
    assert hit(defects, "history declares a variable"), defects
    assert hit(defects, "accrues"), (
        "the defect must say why: a history is asked for and then ACCRUES — "
        "freezing it into a field is what nobody updates: " + str(defects))


@check("a required input with no if_user_lacks_it FAILS")
def _():
    ledger = F.answer_ledger()
    ledger["rows"][1].pop("if_user_lacks_it", None)
    clean = S.validate_answer_ledger(ledger,
                                     question_ids=sorted(F.question_ids()))
    assert not clean, "without required_inputs the rule must not fire at all"

    defects = S.validate_answer_ledger(ledger,
                                       question_ids=sorted(F.question_ids()),
                                       required_inputs={"q2"})
    assert hit(defects, "required input with no if_user_lacks_it"), defects


@check("an `external` row without on_failure FAILS")
def _():
    ledger = F.answer_ledger()
    ledger["rows"][1] = F.ledger_row(
        "q2", kind="external", verdict="external",
        inventory={"source": "openweather", "form": "external:openweather",
                   "gap": "no local record of rainfall"},
        source_name="openweather", access="api", key_needed=True,
        carries_personal_context=False, per_call_cost=0.0)
    defects = S.validate_answer_ledger(ledger,
                                       question_ids=sorted(F.question_ids()))
    assert hit(defects, "no on_failure"), defects


@check("an external row with no carries_personal_context FAILS — not defaults to false")
def _():
    ledger = F.answer_ledger()
    ledger["rows"][1] = F.ledger_row(
        "q2", kind="external", verdict="external",
        inventory={"source": "openweather", "form": "external:openweather",
                   "gap": "no local record of rainfall"},
        source_name="openweather", access="api", key_needed=True,
        on_failure="degrade: skip the rainfall check")
    defects = S.validate_answer_ledger(ledger,
                                       question_ids=sorted(F.question_ids()))
    assert hit(defects, "carries_personal_context"), defects
    assert hit(defects, "not a 'no'"), (
        "an unanswered privacy question must not read as a negative answer: "
        + str(defects))


@check("a non-`found` verdict stating no gap FAILS")
def _():
    ledger = F.answer_ledger()
    ledger["rows"][2]["inventory"]["gap"] = ""
    defects = S.validate_answer_ledger(ledger,
                                       question_ids=sorted(F.question_ids()))
    assert hit(defects, "states no gap"), defects


@check("EVERY question travels — a missing row FAILS, naming the ruling")
def _():
    ledger = F.answer_ledger()
    ledger["rows"] = ledger["rows"][:-1]
    defects = S.validate_answer_ledger(ledger,
                                       question_ids=sorted(F.question_ids()))
    assert hit(defects, "no ledger row for questions"), defects
    assert hit(defects, "EVERY question travels"), defects


@check("status is DERIVED from verdict, never read from the row")
def _():
    row = {"verdict": "ask_user", "status": "settled"}
    assert S.derive_status(row) == "to_ask"
    ledger = S.apply_derived_status({"rows": [row]})
    assert ledger["rows"][0]["status"] == "to_ask"
    assert S.derive_status({"verdict": "external"}) == "external_pending"
    assert S.derive_status({"verdict": "absent"}) == "missing"


@check("a judgment row with one option FAILS — a choice already made")
def _():
    ledger = F.answer_ledger()
    ledger["rows"][0]["decision_options"] = ["a standing commitment"]
    defects = S.validate_answer_ledger(ledger,
                                       question_ids=sorted(F.question_ids()))
    assert hit(defects, "at least 2 entries"), defects


@check("an if_user_lacks_it outside the vocabulary FAILS")
def _():
    ledger = F.answer_ledger()
    ledger["rows"][3]["if_user_lacks_it"] = "figure it out"
    defects = S.validate_answer_ledger(ledger,
                                       question_ids=sorted(F.question_ids()))
    assert hit(defects, "if_user_lacks_it"), defects


@check("`degrade:` with nothing after the colon FAILS")
def _():
    ledger = F.answer_ledger()
    ledger["rows"][3]["if_user_lacks_it"] = "degrade:"
    defects = S.validate_answer_ledger(ledger,
                                       question_ids=sorted(F.question_ids()))
    assert hit(defects, "nothing after the colon"), defects


# ---------------------------------------------------------------------------
# BuildPlan — citations, the tier split, all_personas
# ---------------------------------------------------------------------------

@check("a plan gate without a citation FAILS")
def _():
    plan = F.build_plan()
    plan["citations"] = [c for c in plan["citations"] if c["gate"] != "variables"]
    defects = S.validate_build_plan(plan, red_paths=F.red_paths(),
                                    question_ids=F.question_ids())
    assert hit(defects, "'variables' carries no citation"), defects
    assert hit(defects, "ruling 6"), defects


@check("a citation to a question nobody asked FAILS")
def _():
    plan = F.build_plan()
    plan["citations"][0]["question_id"] = "q99"
    defects = S.validate_build_plan(plan, red_paths=F.red_paths(),
                                    question_ids=F.question_ids())
    assert hit(defects, "not in the Question Set"), defects


@check("a citation with a question id and no ledger row FAILS")
def _():
    plan = F.build_plan()
    plan["citations"][0].pop("ledger_row")
    defects = S.validate_build_plan(plan, red_paths=F.red_paths(),
                                    question_ids=F.question_ids())
    assert hit(defects, "names no ledger_row"), defects


@check("a Red path in the IMPLEMENTER's half FAILS before N11")
def _():
    plan = F.build_plan()
    for entry in plan["files"]:
        if entry["path"] == "config/modules/routing.yaml":
            entry["half"] = "implementer"
    defects = S.validate_build_plan(plan, red_paths=F.red_paths(),
                                    question_ids=F.question_ids())
    assert hit(defects, "Red path"), defects
    assert hit(defects, "implementer never touches"), defects


@check("the SAME Red path in the main session's half is correct and passes")
def _():
    defects = S.validate_build_plan(F.build_plan(), red_paths=F.red_paths(),
                                    question_ids=F.question_ids())
    assert not defects, (
        "config/modules/routing.yaml is Red AND is in files[] — in the main "
        "session's half, which is exactly where it belongs: " + str(defects))


@check("a plan naming config/constitution.md in the implementer's half FAILS")
def _():
    plan = F.build_plan()
    plan["files"].append({"path": "config/constitution.md", "half": "implementer"})
    defects = S.validate_build_plan(plan, red_paths=F.red_paths(),
                                    question_ids=F.question_ids())
    assert hit(defects, "config/constitution.md"), defects


@check("a plan naming .env in the implementer's half FAILS")
def _():
    plan = F.build_plan()
    plan["files"].append({"path": ".env", "half": "implementer"})
    defects = S.validate_build_plan(plan, red_paths=F.red_paths(),
                                    question_ids=F.question_ids())
    assert hit(defects, ".env"), defects


@check("a files[] entry with no half FAILS — the split is not optional")
def _():
    plan = F.build_plan()
    plan["files"].append({"path": "tools/extra.py"})
    defects = S.validate_build_plan(plan, red_paths=F.red_paths(),
                                    question_ids=F.question_ids())
    assert hit(defects, "half must be implementer|main_session"), defects


@check("an absolute or climbing files[] path FAILS")
def _():
    plan = F.build_plan()
    plan["files"].append({"path": "../outside.py", "half": "implementer"})
    defects = S.validate_build_plan(plan, red_paths=F.red_paths(),
                                    question_ids=F.question_ids())
    assert hit(defects, "not repo-relative"), defects


@check("a plan declaring an all_personas variable without an ask path FAILS")
def _():
    plan = F.build_plan()
    plan["variables"] = [{"name": "plant_inventory", "scope": "all_personas",
                          "home": "config/templates/profile.yaml",
                          "if_user_lacks_it": "degrade: skip"}]
    plan["files"].append({"path": "config/templates/profile.yaml",
                          "half": "implementer"})
    defects = S.validate_build_plan(plan, red_paths=F.red_paths(),
                                    question_ids=F.question_ids())
    assert hit(defects, "without `if_user_lacks_it: ask`"), defects
    assert hit(defects, "mike would never get the field"), (
        "the defect must name the consequence — the template reaches only "
        "personas created after it lands: " + str(defects))


@check("an all_personas variable with the ask path and no template file FAILS")
def _():
    plan = F.build_plan()
    plan["variables"] = [{"name": "plant_inventory", "scope": "all_personas",
                          "home": "config/templates/profile.yaml",
                          "if_user_lacks_it": "ask"}]
    defects = S.validate_build_plan(plan, red_paths=F.red_paths(),
                                    question_ids=F.question_ids())
    assert hit(defects, "no config/templates/ entry"), defects


@check("an all_personas LEDGER row without `if_user_lacks_it: ask` FAILS")
def _():
    ledger = F.answer_ledger()
    ledger["rows"][3]["variable_scope"] = "all_personas"
    ledger["rows"][3]["if_user_lacks_it"] = "degrade: skip the check"
    defects = S.validate_answer_ledger(ledger,
                                       question_ids=sorted(F.question_ids()))
    assert hit(defects, "all_personas variable without"), defects


@check("a surface_map missing an operation FAILS, naming the operation")
def _():
    plan = F.build_plan()
    plan["surface_map"] = [s for s in plan["surface_map"]
                           if s["operation"] != "dedupe"]
    defects = S.validate_build_plan(plan, red_paths=F.red_paths(),
                                    question_ids=F.question_ids())
    assert hit(defects, "dedupe"), defects


@check("an integration with no priced run cost FAILS")
def _():
    plan = F.build_plan()
    plan["integrations"] = [{"source": "openweather",
                             "key_registration_is_m_item": True,
                             "privacy_tier": "open"}]
    defects = S.validate_build_plan(plan, red_paths=F.red_paths(),
                                    question_ids=F.question_ids())
    assert hit(defects, "cost_per_call"), defects
    assert hit(defects, "standing charge nobody named"), defects


@check("an agent plan with no registration item FAILS, naming time_director")
def _():
    plan = F.build_plan()
    plan["registration"] = []
    defects = S.validate_build_plan(plan, red_paths=F.red_paths(),
                                    question_ids=F.question_ids())
    assert hit(defects, "time_director"), defects


# ---------------------------------------------------------------------------
# The ladder — rungs 0 and 1
# ---------------------------------------------------------------------------

@check("climb() coerces an unknown enum DOWNWARD in permissiveness, never upward")
def _():
    plan = F.build_plan()
    plan["capability"]["execution_mode"] = "invented"
    artifact, defects, notes = S.climb("build_plan", plan)
    assert artifact["capability"]["execution_mode"] == "deferred", artifact
    assert any("never blocks a turn" in n for n in notes), notes


@check("climb(inject=) refuses a field that is not code-owned")
def _():
    try:
        S.climb("question_set", F.question_set(),
                inject={"generalizes_to": "anything at all"})
    except S.SchemaError as exc:
        assert "refuses" in str(exc), exc
        return
    raise AssertionError("inject= accepted a field the model was asked for")


@check("a question with an unreadable class is QUARANTINED, not guessed")
def _():
    qs = F.question_set()
    qs["spine"][2]["class"] = "vibes"
    artifact, defects, notes = S.climb("question_set", qs,
                                       known_capabilities=F.CAPABILITIES)
    assert len(artifact["spine"]) == 4, artifact["spine"]
    assert artifact["declined_to_ask"], "the question must be recorded as not asked"
    assert [q["id"] for q in artifact["spine"]] == ["q1", "q2", "q3", "q4"], (
        "remaining ids must be renumbered so the density rule still holds")


# ---------------------------------------------------------------------------
# record{} — what the content gate reads (phase C, review finding 4)
#
# Phase A's plan schema had no home for any of this, so at N13 the record was
# hand-assembled from Red prose that had just been typed and `peers` was passed
# empty. The gate ran; it checked almost nothing.
# ---------------------------------------------------------------------------

def _plan(**over) -> dict:
    plan = F.build_plan()
    plan.update(over)
    return plan


def _defects(plan: dict) -> list[str]:
    return S.validate_build_plan(plan, red_paths=F.red_paths(),
                                 question_ids=F.question_ids())


@check("an agent plan with NO record{} fails — the gate would read nothing")
def _():
    plan = _plan()
    plan.pop("record")
    assert hit(_defects(plan), "no record{} block"), _defects(plan)


@check("record.routing.allowed_tools is REQUIRED, because its absence is silent")
def _():
    plan = _plan()
    plan["record"] = {k: v for k, v in plan["record"].items() if k != "routing"}
    assert hit(_defects(plan), "told-not-granted"), (
        "the defect must name the scan that goes missing, not just the field: "
        "constitution.check passes granted=None and check_told_not_granted is "
        "SKIPPED rather than failed")


@check("each scanned prose field of record{} is required on its own")
def _():
    for field in S.RECORD_PROSE_FIELDS:
        plan = _plan()
        plan["record"][field] = ""
        assert hit(_defects(plan), f"record.{field} is empty"), field


@check("a non-agent plan needs no record{} — there is no agent file to describe")
def _():
    plan = _plan()
    plan.pop("record")
    plan["capability"]["kind"] = "tool"
    plan["registration"] = []
    assert not hit(_defects(plan), "record{}"), _defects(plan)


# ---------------------------------------------------------------------------
# required_inputs[] — ruling 7's second verdict (phase C, review finding 7)
# ---------------------------------------------------------------------------

@check("a plan with no required_inputs fails rather than silently disabling the rule")
def _():
    plan = _plan()
    plan.pop("required_inputs")
    assert hit(_defects(plan), "required_inputs must be a list"), _defects(plan)


@check("required_inputs may not name a question that was never asked")
def _():
    plan = _plan(required_inputs=["q2", "q99"])
    assert hit(_defects(plan), "never asked"), _defects(plan)


@check("revalidate_ledger makes if_user_lacks_it mandatory on EXACTLY those rows")
def _():
    ledger = F.answer_ledger()
    for row in ledger["rows"]:
        row.pop("if_user_lacks_it", None)
    ids = sorted(F.question_ids())
    assert not S.validate_answer_ledger(ledger, question_ids=ids), (
        "without a plan the rule is correctly silent")

    plan = _plan(required_inputs=["q2"])
    strict = S.revalidate_ledger(ledger, plan, question_ids=ids)
    assert len(strict) == 1, strict
    assert "if_user_lacks_it" in strict[0], strict
    assert "rows[2]" in strict[0] or "q2" in strict[0], (
        f"the defect must point at the required row, not any row: {strict}")


# ---------------------------------------------------------------------------
# The interview answer has a home (phase C, review finding 5)
# ---------------------------------------------------------------------------

@check("open_interview_items is every ask_user row, derived not asserted")
def _():
    ledger = F.answer_ledger()
    ledger["rows"][0]["verdict"] = "ask_user"
    assert S.open_interview_items(ledger)[0] == ledger["rows"][0]["question_id"]


@check("an interview answer lands as a VALID row that derives `settled`")
def _():
    ledger = F.answer_ledger()
    qid = ledger["rows"][0]["question_id"]
    ledger["rows"][0]["verdict"] = "ask_user"
    answered = S.record_interview_answer(ledger, qid, "Wednesdays, after eight")
    row = answered["rows"][0]
    assert row["verdict"] == "found" and row["status"] == "settled", row
    assert row["decision"] == "Wednesdays, after eight", row
    assert row["inventory"]["source"] == "user", row
    assert row["inventory"]["form"] == "interview", row
    assert row["inventory"]["coverage"]["from"] == row["inventory"]["freshness"]
    assert not S.validate_answer_ledger(
        answered, question_ids=sorted(F.question_ids())), (
        "the answered row must validate — the alternative is a hand-written "
        "inventory, which is how a fabricated one gets in")
    assert not S.open_interview_items(answered), (
        "an answered item must stop being an open interview item")


@check("an EMPTY interview answer is refused — that is not an answer")
def _():
    ledger = F.answer_ledger()
    qid = ledger["rows"][0]["question_id"]
    try:
        S.record_interview_answer(ledger, qid, "   ")
    except S.SchemaError as exc:
        assert "not answered with nothing" in str(exc), exc
    else:
        raise AssertionError("an empty answer was accepted")


@check("an answer for a question that never travelled is refused")
def _():
    try:
        S.record_interview_answer(F.answer_ledger(), "q99", "an answer")
    except S.SchemaError as exc:
        assert "no ledger row" in str(exc), exc
    else:
        raise AssertionError("an answer landed on a question with no row")


suite.exit()
