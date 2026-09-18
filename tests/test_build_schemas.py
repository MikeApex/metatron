"""
tests/test_build_schemas.py — each validator rejects its own malformation.

The nine rejections named in the plan's verification table, plus the rungs 0
and 1 of the validation ladder.

The method throughout: start from a VALID artifact, introduce exactly one
defect, assert that defect is reported. Asserting on a hand-built broken
artifact proves much less — a validator that rejected everything would pass
that version of this file.

Standalone runner (no pytest dependency), matching tests/ convention.

Usage:
    python3 tests/test_build_schemas.py

Exits 0 if every check passes, 1 otherwise.
"""

import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.build import schemas as S  # noqa: E402

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


def hit(defects: list[str], fragment: str) -> bool:
    return any(fragment in d for d in defects)


MANIFEST = {"log", "journal", "wisdom", "calendar", "weather"}
CAPABILITIES = {"logistics", "physical_health", "relationships", "diarist"}

# ---------------------------------------------------------------------------
# Valid baselines. Each test mutates a deepcopy of one of these.
# ---------------------------------------------------------------------------

def question(qid: str, klass: str, text: str) -> dict:
    return {
        "id": qid, "class": klass, "text": text,
        "why_it_matters": f"because {klass} decides the shape of the answer",
        "blocks": "design",
        "expected_answer_shape": "a short statement",
        "candidate_sources": ["log", "user"],
        "resolved_by_policy": None,
    }


def valid_question_set() -> dict:
    return {
        "schema": "question_set/1",
        "job_id": "BLD-0918-01",
        "generated_at": "2026-09-18T10:00:00",
        "upstream_fingerprint": "abc123",
        "mode": "construct",
        "request": "nothing decides whether a household chore is overdue",
        "depth": "standard",
        "disposition": "new",
        "disposition_evidence": (
            "Checked logistics, which owns actions rather than standing checks, "
            "and physical_health, which does not read the home domain."
        ),
        "generalizes_to": "every recurring home obligation with a last-done date",
        "manifest_fingerprint": "m-001",
        "policies_consulted": [],
        "framing_note": "",
        "declined_to_ask": [],
        "spine": [
            question("q1", "intent", "What is the household trying to keep on top of?"),
            question("q2", "cost", "What does an unnecessary reminder consume?"),
            question("q3", "feasibility", "Can the last-done date be read at all?"),
            question("q4", "surface", "What else operates on an overdue chore?"),
            question("q5", "authority", "Decide or surface, and what on silence?"),
        ],
    }


def valid_answer_ledger() -> dict:
    return {
        "schema": "answer_ledger/1",
        "job_id": "BLD-0918-01",
        "generated_at": "2026-09-18T10:05:00",
        "upstream_fingerprint": "abc123",
        "rows": [
            {
                "question_id": "q1",
                "answerable_by": "data",
                "data_kind": "behavioural",
                "status": "settled",
            },
            {
                "question_id": "q2",
                "answerable_by": "judgment",
                "data_kind": "none",
                "has_what_it_needs": True,
                "decision": "warn only past the interval, never on a schedule",
                "decision_options": ["warn past the interval", "warn on a fixed day"],
                "assumption": "a reminder before the interval elapses is noise",
                "assumption_falsifier": "the user acts on a pre-interval reminder twice",
                "status": "settled",
            },
        ],
        "interview_items": [],
        "variable_proposals": [],
        "surface_map": [
            {"entity": "chore", "operation": op, "status": "in_scope"}
            for op in S.SURFACE_OPERATIONS
        ],
    }


def valid_build_plan() -> dict:
    return {
        "schema": "build_plan/1",
        "job_id": "BLD-0918-01",
        "generated_at": "2026-09-18T10:10:00",
        "upstream_fingerprint": "abc123",
        "capability": {
            "id": "home_care",
            "kind": "agent",
            "one_line": "decides whether a recurring home obligation is overdue",
            "replaces": [],
            "execution_mode": "blocking",
            "latency_budget_ms": 8000,
            "theme": "home",
            "disposition": "new",
            "disposition_evidence": "logistics owns actions, not standing checks",
            "generalizes_to": "every recurring home obligation with a last-done date",
        },
        "surface_map": [
            {"entity": "chore", "operation": op, "status": "in_scope"}
            for op in S.SURFACE_OPERATIONS
        ],
        "files": [],
        "registration": [{"record": "overlay/capabilities/home_care.yaml"}],
        "tests": [],
        "acceptance": {},
        "variables": [],
        "state_record": {},
        "risks": [],
    }


# ---------------------------------------------------------------------------
# Sanity: the baselines are actually valid, or every test below is vacuous
# ---------------------------------------------------------------------------

@check("baseline question set validates clean")
def _():
    defects = S.validate_question_set(
        valid_question_set(), manifest_ids=MANIFEST, known_capabilities=CAPABILITIES)
    assert not defects, defects


@check("baseline answer ledger validates clean")
def _():
    defects = S.validate_answer_ledger(
        valid_answer_ledger(), question_ids=["q1", "q2"])
    assert not defects, defects


@check("baseline build plan validates clean")
def _():
    assert not S.validate_build_plan(valid_build_plan())


# ---------------------------------------------------------------------------
# The nine named rejections
# ---------------------------------------------------------------------------

@check("rejects a feasibility question before an intent one")
def _():
    qs = valid_question_set()
    qs["spine"] = [
        question("q1", "feasibility", "Can the last-done date be read at all?"),
        question("q2", "intent", "What is the household trying to keep on top of?"),
        question("q3", "surface", "What else operates on an overdue chore?"),
        question("q4", "authority", "Decide or surface, and what on silence?"),
    ]
    defects = S.validate_question_set(qs, manifest_ids=MANIFEST)
    assert hit(defects, "precedes every intent question"), defects


@check("rejects disposition: new whose evidence names no capability checked")
def _():
    qs = valid_question_set()
    qs["disposition_evidence"] = "This is a genuinely novel need with no precedent."
    defects = S.validate_question_set(
        qs, manifest_ids=MANIFEST, known_capabilities=CAPABILITIES)
    assert hit(defects, "names no existing capability"), defects


@check("rejects empty disposition_evidence")
def _():
    qs = valid_question_set()
    qs["disposition_evidence"] = ""
    assert hit(S.validate_question_set(qs, manifest_ids=MANIFEST),
               "disposition_evidence is empty")


@check("rejects evidence that merely restates the request")
def _():
    qs = valid_question_set()
    qs["disposition_evidence"] = "It is what was asked for."
    assert hit(S.validate_question_set(qs, manifest_ids=MANIFEST),
               "restates the request")


@check("rejects zero surface questions")
def _():
    qs = valid_question_set()
    qs["spine"] = [q for q in qs["spine"] if q["class"] != "surface"]
    for i, q in enumerate(qs["spine"], start=1):
        q["id"] = f"q{i}"
    assert hit(S.validate_question_set(qs, manifest_ids=MANIFEST),
               "no surface question")


@check("rejects zero authority questions at depth != triage")
def _():
    qs = valid_question_set()
    qs["spine"] = [q for q in qs["spine"] if q["class"] != "authority"]
    for i, q in enumerate(qs["spine"], start=1):
        q["id"] = f"q{i}"
    assert hit(S.validate_question_set(qs, manifest_ids=MANIFEST),
               "no authority question")


@check("allows zero authority questions AT depth: triage")
def _():
    qs = valid_question_set()
    qs["depth"] = "triage"
    qs["spine"] = [
        question("q1", "intent", "What is the household trying to keep on top of?"),
        question("q2", "surface", "What else operates on an overdue chore?"),
    ]
    defects = S.validate_question_set(
        qs, manifest_ids=MANIFEST, known_capabilities=CAPABILITIES)
    assert not defects, defects


@check("rejects a judgment row with one option")
def _():
    ledger = valid_answer_ledger()
    ledger["rows"][1]["decision_options"] = ["warn past the interval"]
    assert hit(S.validate_answer_ledger(ledger, question_ids=["q1", "q2"]),
               "at least 2 entries")


@check("rejects a variable_name already declared in its target home")
def _():
    ledger = valid_answer_ledger()
    ledger["rows"][0].update({
        "variable_name": "plant_watering_threshold",
        "variable_scope": "this_persona",
        "data_home": "config/personas/mike/profile.yaml",
    })
    defects = S.validate_answer_ledger(
        ledger, question_ids=["q1", "q2"],
        declared_variables={"plant_watering_threshold"})
    assert hit(defects, "is already declared"), defects


@check("rejects an agent plan missing a registration item")
def _():
    plan = valid_build_plan()
    plan["registration"] = []
    assert hit(S.validate_build_plan(plan), "no registration item")


@check("rejects a surface_map with an unlisted operation")
def _():
    plan = valid_build_plan()
    plan["surface_map"] = [e for e in plan["surface_map"]
                           if e["operation"] not in ("reconcile", "expire")]
    defects = S.validate_build_plan(plan)
    assert hit(defects, "surface_map does not list"), defects
    assert hit(defects, "reconcile"), defects


# ---------------------------------------------------------------------------
# Further constraints the plan states as hard
# ---------------------------------------------------------------------------

@check("rejects non-dense question ids")
def _():
    qs = valid_question_set()
    qs["spine"][2]["id"] = "q9"
    assert hit(S.validate_question_set(qs, manifest_ids=MANIFEST), "not dense")


@check("rejects a candidate_source outside the manifest")
def _():
    qs = valid_question_set()
    qs["spine"][0]["candidate_sources"] = ["log", "astrology"]
    assert hit(S.validate_question_set(qs, manifest_ids=MANIFEST),
               "not in the manifest")


@check("rejects two questions with the same token set")
def _():
    qs = valid_question_set()
    qs["spine"][3]["text"] = "What is the household trying to keep on top of?"
    qs["spine"][3]["class"] = "surface"
    assert hit(S.validate_question_set(qs, manifest_ids=MANIFEST), "duplicates")


@check("rejects depth: triage carrying more than three questions")
def _():
    qs = valid_question_set()
    qs["depth"] = "triage"
    assert hit(S.validate_question_set(qs, manifest_ids=MANIFEST),
               "at most 3 questions")


@check("rejects a judgment row with no falsifier for its assumption")
def _():
    ledger = valid_answer_ledger()
    ledger["rows"][1]["assumption_falsifier"] = ""
    assert hit(S.validate_answer_ledger(ledger, question_ids=["q1", "q2"]),
               "no falsifier")


@check("rejects a ledger missing a row for a question")
def _():
    ledger = valid_answer_ledger()
    ledger["rows"] = ledger["rows"][:1]
    assert hit(S.validate_answer_ledger(ledger, question_ids=["q1", "q2"]),
               "no ledger row for questions")


@check("rejects a deferred surface entry with no ticket")
def _():
    plan = valid_build_plan()
    plan["surface_map"][3]["status"] = "deferred"
    assert hit(S.validate_build_plan(plan), "deferred needs a ticket")


@check("rejects a plan writing under data/ with no state_record")
def _():
    plan = valid_build_plan()
    plan["files"] = [{"path": "data/personas/mike/home/chores.json", "mode": "write"}]
    assert hit(S.validate_build_plan(plan), "state_record is missing")


@check("rejects kind: policy with no policy block")
def _():
    plan = valid_build_plan()
    plan["capability"]["kind"] = "policy"
    assert hit(S.validate_build_plan(plan), "requires a policy block")


@check("rejects a policy with no review_date")
def _():
    plan = valid_build_plan()
    plan["capability"]["kind"] = "policy"
    plan["policy"] = {
        "id": "weekend_business_correspondence", "domain": "work",
        "applies_to": "business senders", "standing_commitments": [],
        "automatic_yes": [], "automatic_no": ["raise at the weekend"],
        "default_on_silence": "Monday morning", "review_date": "",
        "authored_with_user": True,
    }
    assert hit(S.validate_build_plan(plan), "policy.review_date is empty")


@check("rejects a non-positive latency budget")
def _():
    plan = valid_build_plan()
    plan["capability"]["latency_budget_ms"] = 0
    assert hit(S.validate_build_plan(plan), "latency_budget_ms must be a positive")


# ---------------------------------------------------------------------------
# The validation ladder — rungs 0 and 1
# ---------------------------------------------------------------------------

@check("rung 0 recovers a fenced, comma-trailing payload")
def _():
    raw = '```json\n{"schema": "question_set/1", "mode": "construct",}\n```'
    parsed, how = S.repair_json(raw)
    assert parsed is not None and parsed["mode"] == "construct", (parsed, how)
    assert how != "clean", how


@check("rung 1 collapses each closed enum toward its SAFE value")
def _():
    notes: list[str] = []
    out = S.coerce_fields({
        "disposition": "invention",
        "answerable_by": "lookup",
        "variable_scope": "everywhere",
        "execution_mode": "instant",
    }, notes)
    assert out["disposition"] == "new", out
    assert out["answerable_by"] == "judgment", out
    assert out["variable_scope"] == "query_only", out
    assert out["execution_mode"] == "deferred", out
    assert len(notes) == 4, notes


@check("rung 1 never coerces a VALUE — only a category")
def _():
    out = S.coerce_fields({
        "decision": "warn only past the interval",
        "assumption": "a pre-interval reminder is noise",
        "latency_budget_ms": 8000,
    })
    assert out["decision"] == "warn only past the interval", out
    assert out["latency_budget_ms"] == 8000, out


@check("rung 1 quarantines an unclassed question rather than guessing its class")
def _():
    qs = valid_question_set()
    qs["spine"][2]["class"] = "vibes"
    out, notes = S.quarantine_unclassed_questions(qs)
    assert len(out["spine"]) == 4, out["spine"]
    assert [q["id"] for q in out["spine"]] == ["q1", "q2", "q3", "q4"], out["spine"]
    assert len(out["declined_to_ask"]) == 1, out["declined_to_ask"]
    assert "no safe class exists" in out["declined_to_ask"][0]["reason"]
    assert notes, notes


@check("climb() runs the ladder end to end on a raw string payload")
def _():
    import json
    qs = valid_question_set()
    qs["execution_mode"] = "instant"           # rung 1 fodder
    raw = "```json\n" + json.dumps(qs) + ",\n```"
    artifact, defects, notes = S.climb(
        "question_set", raw, manifest_ids=MANIFEST, known_capabilities=CAPABILITIES)
    assert artifact is not None, (defects, notes)
    assert not defects, defects
    assert artifact["execution_mode"] == "deferred", artifact["execution_mode"]
    assert any("rung 0" in n for n in notes), notes


@check("climb() returns the defect list when the artifact cannot be rescued")
def _():
    import json
    qs = valid_question_set()
    qs["spine"] = [
        question("q1", "feasibility", "Can the last-done date be read at all?"),
        question("q2", "intent", "What is the household trying to keep on top of?"),
    ]
    artifact, defects, _ = S.climb(
        "question_set", json.dumps(qs), manifest_ids=MANIFEST)
    assert artifact is not None
    assert hit(defects, "precedes every intent question"), defects


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    failed = 0
    for name, ok, detail in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}{'' if ok else '  — ' + detail}")
        failed += 0 if ok else 1
    print(f"\n{len(_results) - failed}/{len(_results)} passed")
    sys.exit(1 if failed else 0)
