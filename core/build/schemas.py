"""
core/build/schemas.py — the three artifacts and their validators.

QuestionSet, AnswerLedger, BuildPlan. All three carry `schema`, `job_id`, an
upstream fingerprint and `generated_at`, so any artifact can be traced to the
one it was derived from.

THE COMPASS RULE, AND WHY IT IS POSITION AND NOT A TAG.

The spine is ORDERED, and the order is the design. The reference transcript's
turn-2 spine put feasibility second and never asked what the boss was for; its
turn-4 spine starts with intent and does not reach feasibility until sixth.
That single inversion is the whole delta between "I built a filter" and a
compass.

The obvious cheaper design — a `kind: orienting` tag on each question — was
rejected, and the repo's own evidence is why. tools/logger.py:411 documents a
`USER_CORRECTION:` slot annotated "omit if not applicable" that produced 93 of
174 events reading "None.", because **a model filling a structured template
answers the slot rather than deleting it.** A tag has exactly that shape: it is
a slot to fill. POSITION CANNOT BE FAKED — a question placed before feasibility
had to be thought of first.

WHAT IS DELIBERATELY NOT VALIDATED: quality. Nothing here can tell a good intent
question from a lazy one. What it can tell is that intent was reached for before
feasibility, which is the structural half, and the half that was being lost.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

# ---------------------------------------------------------------------------
# Closed vocabularies
# ---------------------------------------------------------------------------

# ORDER IS SEMANTIC. The index is the sort key the spine is validated against;
# reordering this tuple changes what a valid Question Set looks like.
SPINE_CLASSES: tuple[str, ...] = (
    "integrity",        # 1. What on the face of this request does not cohere?
    "intent",           # 2. What is this in service of? Stated vs revealed?
    "cost",             # 3. What does acting consume that nothing meters?
    "asymmetry",        # 4. Anything irreversible or closing? Regret both ways?
    "feasibility",      # 5. Can it be done, at what cost to what surrounds it?
    "surface",          # 6. What else operates on this once it exists?
    "minimum_version",  # 7. What captures most of the value for a fraction?
    "authority",        # 8. Decided or surfaced — and the default on silence?
)
CLASS_INDEX: dict[str, int] = {name: i + 1 for i, name in enumerate(SPINE_CLASSES)}

DEPTHS: tuple[str, ...] = ("triage", "standard", "deep")
TRIAGE_MAX_QUESTIONS = 3
SOFT_QUESTION_CEILING = 25   # advisory; a large set is fine, cost is in adjudicating

DISPOSITIONS: tuple[str, ...] = ("extend", "new", "split", "policy")
BLOCKS: tuple[str, ...] = ("design", "behaviour", "neither")

ANSWERABLE_BY: tuple[str, ...] = ("data", "judgment")
DATA_KINDS: tuple[str, ...] = ("single_point", "behavioural", "none")
VARIABLE_SCOPES: tuple[str, ...] = ("all_personas", "this_persona", "query_only")
ROW_STATUSES: tuple[str, ...] = ("settled", "needs_interview", "needs_tool")

VARIABLE_TYPES: tuple[str, ...] = (
    "string", "number", "boolean", "enum", "list", "object", "table", "record_set",
)
MULTI_ITEM_TYPES: frozenset[str] = frozenset({"list", "object", "table", "record_set"})

KINDS: tuple[str, ...] = (
    "tool", "agent", "policy", "function_job", "context_block", "check",
)
EXECUTION_MODES: tuple[str, ...] = ("blocking", "deferred", "background")

# Nothing may be silently absent from a surface map — every operation is listed
# with a disposition. This is the anti-drift mechanism at capability level.
SURFACE_OPERATIONS: tuple[str, ...] = (
    "create", "read", "update", "delete", "move", "dedupe", "merge",
    "expire", "reconcile",
)
SURFACE_STATUSES: tuple[str, ...] = ("in_scope", "deferred", "not_applicable")

SCHEMA_VERSIONS: dict[str, str] = {
    "question_set": "question_set/1",
    "answer_ledger": "answer_ledger/1",
    "build_plan": "build_plan/1",
    # Not a model artifact — the writer produces it. It is here because it is
    # the fourth thing with a schema, and one home for schema strings is worth
    # more than a tidy separation between model-written and code-written.
    "overlay_capability": "overlay_capability/1",
}

# `new` is the disposition a model reaches for by default, because it matches
# the literal shape of the request. Evidence that merely restates the request is
# the characteristic non-answer, so it is refused by name.
_EVIDENCE_BOILERPLATE = (
    "it is what was asked for",
    "it is what was requested",
    "this is what the user asked for",
    "this is what was asked",
    "the request asks for it",
    "nothing like this exists",
    "no existing capability covers this",
)

_ID_RE = re.compile(r"^q(\d+)$")
_VARIABLE_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{2,47}$")
_CAPABILITY_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,31}$")
_WORD_RE = re.compile(r"[a-z0-9]+")

# Words carrying no discriminating signal in a question. Token-set dedupe
# without this flags "What does it cost?" and "What is the cost?" as distinct
# while missing genuine restatements.
_STOPWORDS = frozenset("""
a an and are as at be been being but by can could do does did for from has have
had how i if in into is it its of on or should so than that the their then there
these they this those to was we were what when where which who whom why will
with would you your
""".split())


class SchemaError(ValueError):
    """An artifact could not be validated. Carries the machine-written defects."""

    def __init__(self, kind: str, defects: list[str]):
        self.kind = kind
        self.defects = defects
        super().__init__(f"{kind}: {len(defects)} defect(s)\n  - " + "\n  - ".join(defects))


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _text(value: Any) -> str:
    return str(value or "").strip()


def _is_blank(value: Any) -> bool:
    """Empty, or a model's way of saying the field does not apply."""
    text = _text(value)
    if not text:
        return True
    try:
        from tools.logger import is_null_ish
        return bool(is_null_ish(text))
    except Exception:
        return text.lower() in {"none", "n/a", "null", "-"}


def _tokens(text: str) -> frozenset[str]:
    return frozenset(
        w for w in _WORD_RE.findall(str(text or "").lower()) if w not in _STOPWORDS
    )


def _common_header(obj: dict, kind: str, defects: list[str]) -> None:
    """schema, job_id, upstream fingerprint and generated_at — on all three."""
    expected = SCHEMA_VERSIONS[kind]
    if _text(obj.get("schema")) != expected:
        defects.append(f"schema must be {expected!r}, got {obj.get('schema')!r}")
    from core.build.ids import is_job_id
    if not is_job_id(_text(obj.get("job_id"))):
        defects.append(f"job_id {obj.get('job_id')!r} is not a BLD-MMDD-NN id")
    if _is_blank(obj.get("generated_at")):
        defects.append("generated_at is missing")
    if _is_blank(obj.get("upstream_fingerprint")):
        defects.append(
            "upstream_fingerprint is missing — without it an artifact cannot be "
            "traced to the one it was derived from"
        )


def now_stamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# QuestionSet
# ---------------------------------------------------------------------------

def validate_question_set(qs: dict,
                          manifest_ids: set[str] | None = None,
                          known_capabilities: set[str] | None = None) -> list[str]:
    """
    Return the defect list. Empty means valid.

    `manifest_ids` and `known_capabilities` come from N1. When either is None
    the check that depends on it is NOT RUN and that is stated in the docstring
    rather than silently passing: in the live pipeline both are always present,
    because `manifest_fingerprint` is a required field.
    """
    defects: list[str] = []
    if not isinstance(qs, dict):
        return ["question_set is not an object"]

    _common_header(qs, "question_set", defects)

    mode = _text(qs.get("mode")).lower()
    if mode not in {"construct", "repair"}:
        defects.append(f"mode must be construct|repair, got {qs.get('mode')!r}")
    if _is_blank(qs.get("request")):
        defects.append("request is empty")

    depth = _text(qs.get("depth")).lower()
    if depth not in DEPTHS:
        defects.append(f"depth must be one of {list(DEPTHS)}, got {qs.get('depth')!r}")

    _check_disposition(qs, known_capabilities, defects)

    if _is_blank(qs.get("generalizes_to")):
        defects.append(
            "generalizes_to is empty — a capability that generalises to nothing "
            "is the narrow-tool failure the altitude rule exists to catch"
        )
    if _is_blank(qs.get("manifest_fingerprint")):
        defects.append("manifest_fingerprint is missing")
    for field in ("policies_consulted", "declined_to_ask"):
        if not isinstance(qs.get(field, []), list):
            defects.append(f"{field} must be a list")

    spine = qs.get("spine")
    if not isinstance(spine, list) or not spine:
        defects.append("spine is empty or not a list")
        return defects

    _check_questions(spine, manifest_ids, defects)
    _check_spine_order(spine, defects)
    _check_required_classes(spine, depth, defects)
    _check_dedupe(spine, defects)

    if depth == "triage" and len(spine) > TRIAGE_MAX_QUESTIONS:
        defects.append(
            f"depth: triage allows at most {TRIAGE_MAX_QUESTIONS} questions, "
            f"got {len(spine)} — a triage that asks more than three is a "
            "standard run that has not admitted it"
        )
    return defects


def _check_disposition(qs: dict, known_capabilities: set[str] | None,
                       defects: list[str]) -> None:
    disposition = _text(qs.get("disposition")).lower()
    if disposition not in DISPOSITIONS:
        defects.append(
            f"disposition must be one of {list(DISPOSITIONS)}, got "
            f"{qs.get('disposition')!r} — the altitude answer is mandatory"
        )
    evidence = _text(qs.get("disposition_evidence"))
    if _is_blank(evidence):
        defects.append("disposition_evidence is empty")
        return

    lowered = evidence.lower()
    for phrase in _EVIDENCE_BOILERPLATE:
        if phrase in lowered:
            defects.append(
                f"disposition_evidence restates the request ({phrase!r}) rather "
                "than naming what was checked"
            )
            break

    if disposition == "new" and known_capabilities is not None:
        # `new` carries the highest burden of proof: it must name the existing
        # capability that was checked and say why it does not cover this.
        named = {c for c in known_capabilities if c and c.lower() in lowered}
        if not named:
            defects.append(
                "disposition: new — disposition_evidence names no existing "
                "capability that was checked. `new` is the disposition a model "
                "reaches for by default; it carries the highest burden of proof."
            )


def _check_questions(spine: list, manifest_ids: set[str] | None,
                     defects: list[str]) -> None:
    seen_ids: list[int] = []
    for position, question in enumerate(spine, start=1):
        where = f"spine[{position}]"
        if not isinstance(question, dict):
            defects.append(f"{where} is not an object")
            continue

        match = _ID_RE.match(_text(question.get("id")))
        if not match:
            defects.append(f"{where} id {question.get('id')!r} must match q<N>")
        else:
            seen_ids.append(int(match.group(1)))

        if _is_blank(question.get("text")):
            defects.append(f"{where} text is empty")
        if _is_blank(question.get("why_it_matters")):
            defects.append(f"{where} why_it_matters is empty")
        if _is_blank(question.get("expected_answer_shape")):
            defects.append(f"{where} expected_answer_shape is empty")

        klass = _text(question.get("class")).lower()
        if klass not in CLASS_INDEX:
            defects.append(
                f"{where} class {question.get('class')!r} is not one of "
                f"{list(SPINE_CLASSES)}"
            )

        blocks = _text(question.get("blocks")).lower()
        if blocks not in BLOCKS:
            defects.append(f"{where} blocks must be one of {list(BLOCKS)}")

        sources = question.get("candidate_sources", [])
        if not isinstance(sources, list):
            defects.append(f"{where} candidate_sources must be a list")
        elif manifest_ids is not None:
            allowed = set(manifest_ids) | {"user"}
            unknown = [s for s in sources if _text(s) not in allowed]
            if unknown:
                defects.append(
                    f"{where} candidate_sources not in the manifest: {unknown} — "
                    "a source the probe cannot resolve makes data_available a "
                    "claim rather than evidence"
                )

    if seen_ids:
        if len(set(seen_ids)) != len(seen_ids):
            defects.append("question ids are not unique")
        elif sorted(seen_ids) != list(range(1, len(seen_ids) + 1)):
            defects.append(
                f"question ids are not dense — got {sorted(seen_ids)}, "
                f"expected q1..q{len(seen_ids)}"
            )


def _check_spine_order(spine: list, defects: list[str]) -> None:
    """
    The load-bearing constraint. Two checks, because they fail differently.

    The general one — non-decreasing class index — is the design. The specific
    one — no feasibility before intent — is called out separately because it is
    the inversion the reference transcript turns on, and a defect message
    naming it is worth more to the retry than "position 2 is out of order".
    """
    indexed = [
        (position, _text(q.get("class")).lower())
        for position, q in enumerate(spine, start=1)
        if isinstance(q, dict)
    ]
    known = [(p, k) for p, k in indexed if k in CLASS_INDEX]

    previous_index = 0
    previous_class = ""
    for position, klass in known:
        index = CLASS_INDEX[klass]
        if index < previous_index:
            defects.append(
                f"spine is not ordered by class index: {klass} (class "
                f"{index}) at position {position} follows {previous_class} "
                f"(class {previous_index})"
            )
            break
        previous_index, previous_class = index, klass

    first_intent = next((p for p, k in known if k == "intent"), None)
    first_feasibility = next((p for p, k in known if k == "feasibility"), None)
    if first_feasibility is not None and (
        first_intent is None or first_feasibility < first_intent
    ):
        defects.append(
            f"a feasibility question (position {first_feasibility}) precedes "
            f"every intent question — this is the filter-not-compass inversion: "
            "it makes the calendar the arbiter and treats empty capacity as "
            "available capacity"
        )


def _check_required_classes(spine: list, depth: str, defects: list[str]) -> None:
    present = {
        _text(q.get("class")).lower() for q in spine if isinstance(q, dict)
    }
    if "intent" not in present:
        defects.append(
            "no intent question — nothing establishes what this is in service "
            "of, so the answer can only be a filter"
        )
    if "surface" not in present:
        defects.append(
            "no surface question — nothing enumerates what else operates on "
            "this once it exists (move, delete, dedupe, merge, expire, reconcile)"
        )
    if depth != "triage" and "authority" not in present:
        defects.append(
            f"no authority question at depth: {depth or '?'} — nothing states "
            "what is decided here versus surfaced, or the default on silence"
        )


def _check_dedupe(spine: list, defects: list[str]) -> None:
    """Token-set dedupe. Semantic dedupe against every question ever asked
    arrives with Build's own index (core/build/index.py); this is the cheap
    within-set half, and it runs first because it needs no encoder."""
    seen: dict[frozenset[str], str] = {}
    for question in spine:
        if not isinstance(question, dict):
            continue
        tokens = _tokens(question.get("text"))
        if not tokens:
            continue
        if tokens in seen:
            defects.append(
                f"{question.get('id')!r} duplicates {seen[tokens]!r} "
                "(identical token set)"
            )
        else:
            seen[tokens] = _text(question.get("id"))


# ---------------------------------------------------------------------------
# AnswerLedger
# ---------------------------------------------------------------------------

# Written by the model and stripped before validation, then re-injected from N3.
# The Librarian's hardest field is "is this data available?", and a model asked
# that answers from its impression of what tools exist. Code answers exactly.
CODE_WRITTEN_LEDGER_FIELDS: tuple[str, ...] = (
    "data_available", "evidence", "condensed_from", "status",
)


def strip_code_written(row: dict) -> dict:
    """Drop the fields only N3 may write. Called before validation, always."""
    return {k: v for k, v in row.items() if k not in CODE_WRITTEN_LEDGER_FIELDS}


def validate_answer_ledger(ledger: dict, question_ids: list[str] | None = None,
                           declared_variables: set[str] | None = None) -> list[str]:
    """
    Return the defect list. Empty means valid.

    `declared_variables` is read from the LIVE home (read_profile, read_wisdom),
    never from a Mac copy — a variable name is unique against what is actually
    declared there, not against what a checkout believes is declared.
    """
    defects: list[str] = []
    if not isinstance(ledger, dict):
        return ["answer_ledger is not an object"]

    _common_header(ledger, "answer_ledger", defects)

    rows = ledger.get("rows")
    if not isinstance(rows, list) or not rows:
        defects.append("rows is empty or not a list")
        return defects

    for field in ("interview_items", "variable_proposals"):
        if not isinstance(ledger.get(field, []), list):
            defects.append(f"{field} must be a list")

    seen_questions: list[str] = []
    for position, row in enumerate(rows, start=1):
        where = f"rows[{position}]"
        if not isinstance(row, dict):
            defects.append(f"{where} is not an object")
            continue
        question_id = _text(row.get("question_id"))
        if not question_id:
            defects.append(f"{where} question_id is missing")
        else:
            seen_questions.append(question_id)
        _check_ledger_row(row, where, declared_variables, defects)

    if question_ids is not None:
        expected, got = set(question_ids), set(seen_questions)
        if expected - got:
            defects.append(f"no ledger row for questions: {sorted(expected - got)}")
        if got - expected:
            defects.append(f"ledger rows for unknown questions: {sorted(got - expected)}")
    if len(set(seen_questions)) != len(seen_questions):
        defects.append("more than one row for the same question")

    _check_surface_map(ledger.get("surface_map"), "answer_ledger", defects)
    return defects


def _check_ledger_row(row: dict, where: str, declared_variables: set[str] | None,
                      defects: list[str]) -> None:
    answerable_by = _text(row.get("answerable_by")).lower()
    if answerable_by not in ANSWERABLE_BY:
        defects.append(f"{where} answerable_by must be one of {list(ANSWERABLE_BY)}")

    data_kind = _text(row.get("data_kind")).lower()
    if data_kind not in DATA_KINDS:
        defects.append(f"{where} data_kind must be one of {list(DATA_KINDS)}")

    status = _text(row.get("status")).lower()
    if status and status not in ROW_STATUSES:
        defects.append(f"{where} status must be one of {list(ROW_STATUSES)}")

    if answerable_by == "judgment":
        # A judgment with one option is a decision already made, presented as a
        # choice. Two is the floor for the gate to mean anything at runtime.
        options = row.get("decision_options")
        if not isinstance(options, list) or len(options) < 2:
            defects.append(
                f"{where} answerable_by: judgment requires decision_options with "
                f"at least 2 entries, got "
                f"{len(options) if isinstance(options, list) else 'none'}"
            )
        if _is_blank(row.get("decision")):
            defects.append(f"{where} judgment row has no decision")
        if _is_blank(row.get("assumption")):
            defects.append(f"{where} judgment row has no assumption")
        if _is_blank(row.get("assumption_falsifier")):
            defects.append(
                f"{where} assumption has no falsifier — an assumption nothing "
                "can disconfirm is not re-checkable at runtime"
            )
        if not isinstance(row.get("has_what_it_needs"), bool):
            defects.append(f"{where} has_what_it_needs must be a boolean")

    _check_variable_home(row, where, declared_variables, defects)


def _check_variable_home(row: dict, where: str, declared_variables: set[str] | None,
                         defects: list[str]) -> None:
    scope = _text(row.get("variable_scope")).lower()
    name = _text(row.get("variable_name"))
    if not scope and not name:
        return
    if scope and scope not in VARIABLE_SCOPES:
        defects.append(f"{where} variable_scope must be one of {list(VARIABLE_SCOPES)}")
    if name:
        if not _VARIABLE_NAME_RE.match(name):
            defects.append(
                f"{where} variable_name {name!r} must match {_VARIABLE_NAME_RE.pattern}"
            )
        elif declared_variables is not None and name in declared_variables:
            defects.append(
                f"{where} variable_name {name!r} is already declared in its "
                "target home — a second declaration would shadow the first"
            )
        if _is_blank(row.get("data_home")):
            defects.append(f"{where} declares {name!r} but data_home is empty")

    var_type = _text(row.get("variable_type")).lower()
    if var_type:
        if var_type not in VARIABLE_TYPES:
            defects.append(f"{where} variable_type must be one of {list(VARIABLE_TYPES)}")
        elif var_type in MULTI_ITEM_TYPES:
            if _is_blank(row.get("variable_shape")):
                defects.append(
                    f"{where} variable_type {var_type!r} needs a variable_shape "
                    "declaration"
                )
            if scope and scope != "query_only":
                defects.append(
                    f"{where} variable_type {var_type!r} must be query_only in "
                    "v1 — profile.yaml fields are scalars"
                )


# ---------------------------------------------------------------------------
# BuildPlan
# ---------------------------------------------------------------------------

def validate_build_plan(plan: dict) -> list[str]:
    """Return the defect list. Empty means valid."""
    defects: list[str] = []
    if not isinstance(plan, dict):
        return ["build_plan is not an object"]

    _common_header(plan, "build_plan", defects)

    capability = plan.get("capability")
    if not isinstance(capability, dict):
        defects.append("capability block is missing")
        return defects

    kind = _text(capability.get("kind")).lower()
    _check_capability(capability, defects)
    _check_surface_map(plan.get("surface_map"), "build_plan", defects)

    for field in ("files", "registration", "tests", "variables", "risks"):
        if not isinstance(plan.get(field, []), list):
            defects.append(f"{field} must be a list")

    if kind == "policy":
        _check_policy(plan.get("policy"), defects)
    elif plan.get("policy") not in (None, {}):
        defects.append("policy block is only valid when kind == policy")

    if kind == "agent" and not plan.get("registration"):
        defects.append(
            "an agent plan has no registration item — a half-wired agent is "
            "already in the tree today (time_director), which is the class of "
            "defect one required record exists to end"
        )

    _check_state_record(plan, defects)
    return defects


def _check_capability(capability: dict, defects: list[str]) -> None:
    cap_id = _text(capability.get("id"))
    if not _CAPABILITY_ID_RE.match(cap_id):
        defects.append(
            f"capability.id {cap_id!r} must match {_CAPABILITY_ID_RE.pattern}"
        )
    if _text(capability.get("kind")).lower() not in KINDS:
        defects.append(f"capability.kind must be one of {list(KINDS)}")
    if _text(capability.get("disposition")).lower() not in DISPOSITIONS:
        defects.append(f"capability.disposition must be one of {list(DISPOSITIONS)}")
    if _is_blank(capability.get("disposition_evidence")):
        defects.append("capability.disposition_evidence is empty")
    if _is_blank(capability.get("one_line")):
        defects.append("capability.one_line is empty")
    if _is_blank(capability.get("generalizes_to")):
        defects.append("capability.generalizes_to is empty")

    mode = _text(capability.get("execution_mode")).lower()
    if mode not in EXECUTION_MODES:
        defects.append(f"capability.execution_mode must be one of {list(EXECUTION_MODES)}")

    budget = capability.get("latency_budget_ms")
    if not isinstance(budget, (int, float)) or budget <= 0:
        defects.append(
            "capability.latency_budget_ms must be a positive number — a "
            "capability that makes a conversation wait is worse than no capability"
        )
    if not isinstance(capability.get("replaces", []), list):
        defects.append("capability.replaces must be a list")


def _check_surface_map(surface_map: Any, owner: str, defects: list[str]) -> None:
    """
    Every operation listed with a disposition. Nothing may be silently absent.

    Silence is the failure this closes: a calendar entry needs delete, move,
    dedupe and reconcile, and none of those arise from asking "what do I need
    to know?"
    """
    if not isinstance(surface_map, list) or not surface_map:
        defects.append(f"{owner}: surface_map is required and must be a non-empty list")
        return

    covered: set[str] = set()
    for position, entry in enumerate(surface_map, start=1):
        where = f"{owner}.surface_map[{position}]"
        if not isinstance(entry, dict):
            defects.append(f"{where} is not an object")
            continue
        if _is_blank(entry.get("entity")):
            defects.append(f"{where} entity is empty")

        operation = _text(entry.get("operation")).lower()
        if operation not in SURFACE_OPERATIONS:
            defects.append(
                f"{where} operation {entry.get('operation')!r} is not one of "
                f"{list(SURFACE_OPERATIONS)}"
            )
        else:
            covered.add(operation)

        status = _text(entry.get("status")).lower()
        if status not in SURFACE_STATUSES:
            defects.append(f"{where} status must be one of {list(SURFACE_STATUSES)}")
        elif status == "deferred" and _is_blank(entry.get("ticket")):
            defects.append(f"{where} deferred needs a ticket")
        elif status == "not_applicable" and _is_blank(entry.get("reason")):
            defects.append(f"{where} not_applicable needs a reason")

    missing = [op for op in SURFACE_OPERATIONS if op not in covered]
    if missing:
        defects.append(
            f"{owner}: surface_map does not list {missing} — every operation "
            "carries a disposition, because absence is indistinguishable from "
            "an oversight"
        )


def _check_policy(policy: Any, defects: list[str]) -> None:
    if not isinstance(policy, dict):
        defects.append("kind: policy requires a policy block")
        return
    for field in ("id", "domain", "applies_to", "default_on_silence", "review_date"):
        if _is_blank(policy.get(field)):
            defects.append(f"policy.{field} is empty")
    for field in ("standing_commitments", "automatic_yes", "automatic_no"):
        if not isinstance(policy.get(field, []), list):
            defects.append(f"policy.{field} must be a list")
    if not isinstance(policy.get("authored_with_user"), bool):
        defects.append("policy.authored_with_user must be a boolean")

    budget = policy.get("budget")
    if budget is not None:
        if not isinstance(budget, dict):
            defects.append("policy.budget must be an object")
        else:
            for field in ("unit", "period", "limit"):
                if _is_blank(budget.get(field)):
                    defects.append(f"policy.budget.{field} is empty")


def _check_state_record(plan: dict, defects: list[str]) -> None:
    """
    Requirement 3, enforced without retrofitting the ~25 existing whole-file
    writers: any NEW state a generated capability introduces must be
    rebuildable from an append-only record or by recomputation.
    """
    writes_data = any(
        _text(entry.get("path") if isinstance(entry, dict) else entry).startswith("data/")
        and (entry.get("mode") if isinstance(entry, dict) else "write") != "read"
        for entry in plan.get("files", []) or []
    )
    if not writes_data:
        return
    record = plan.get("state_record")
    if not isinstance(record, dict) or not record:
        defects.append(
            "a planned file writes under data/ but state_record is missing — "
            "new state must be rebuildable from an append-only record or by "
            "recomputation"
        )
        return
    if _is_blank(record.get("rebuild_from")):
        defects.append("state_record.rebuild_from is empty")


# ---------------------------------------------------------------------------
# The validation ladder — rungs 0 and 1
# ---------------------------------------------------------------------------
#
# RUNG 0  STRUCTURAL REPAIR  free
# RUNG 1  FIELD COERCION     free
# RUNG 2  TARGETED RETRY     one call, max 1 per node        (core/build/runner.py)
# RUNG 3  REJECT             -> failed with the defect list  (core/build/runner.py)

def repair_json(raw: str) -> tuple[dict | None, str]:
    """
    RUNG 0. The orchestrator's own repair ladder, imported rather than copied.

    Nothing in it guesses at CONTENT: every repair is structural (fences,
    truncation, trailing commas, quote style). Imported lazily because
    core.orchestrator is a heavy module and most callers here never need it.
    """
    from core.orchestrator import _repair_context_json
    return _repair_context_json(raw)


# Each entry: (field, allowed values, the SAFE value, why it is the safe one).
# The safe value is always the one that is LEAST permissive — it forces more
# scrutiny, never less.
_COERCIONS: tuple[tuple[str, tuple[str, ...], str, str], ...] = (
    ("disposition", DISPOSITIONS, "new",
     "new carries the highest burden of proof"),
    ("answerable_by", ANSWERABLE_BY, "judgment",
     "judgment forces has_what_it_needs and a falsifier"),
    ("variable_scope", VARIABLE_SCOPES, "query_only",
     "query_only declares nothing in a shared home"),
    ("execution_mode", EXECUTION_MODES, "deferred",
     "deferred never blocks a turn"),
)


def coerce_fields(obj: Any, notes: list[str] | None = None) -> Any:
    """
    RUNG 1. Collapse unknown values of CLOSED ENUMS toward the safe value.

    NEVER COERCES A VALUE — only a category, and only downward in
    permissiveness. A wrong category costs scrutiny; a coerced value would be
    an invented answer, which is the thing this whole design refuses to do.

    `class` is deliberately absent from _COERCIONS: there is no safe spine
    class. A question whose class cannot be read is moved to declined_to_ask[]
    with the defect noted, because guessing its class would guess its POSITION,
    and position is the compass rule.
    """
    notes = notes if notes is not None else []
    if isinstance(obj, list):
        return [coerce_fields(item, notes) for item in obj]
    if not isinstance(obj, dict):
        return obj

    out = {k: coerce_fields(v, notes) for k, v in obj.items()}
    for field, allowed, safe, why in _COERCIONS:
        if field not in out:
            continue
        value = _text(out[field]).lower()
        if value and value not in allowed:
            notes.append(f"coerced {field}={out[field]!r} -> {safe!r} ({why})")
            out[field] = safe
    return out


def quarantine_unclassed_questions(qs: dict) -> tuple[dict, list[str]]:
    """
    RUNG 1, the class case. A question with an unreadable class leaves the
    spine for declined_to_ask[] with the defect noted.

    This is a demotion, not a repair: the question is recorded as not asked
    rather than asked in a guessed position. Remaining ids are renumbered so
    the density rule still holds.
    """
    notes: list[str] = []
    spine = qs.get("spine")
    if not isinstance(spine, list):
        return qs, notes

    kept, declined = [], list(qs.get("declined_to_ask") or [])
    for question in spine:
        if not isinstance(question, dict):
            continue
        klass = _text(question.get("class")).lower()
        if klass in CLASS_INDEX:
            kept.append(question)
            continue
        declined.append({
            "text": _text(question.get("text")),
            "reason": (
                f"class {question.get('class')!r} is not one of "
                f"{list(SPINE_CLASSES)} — no safe class exists, so the question "
                "was not asked rather than asked in a guessed position"
            ),
        })
        notes.append(f"quarantined {question.get('id')!r}: unreadable class")

    for position, question in enumerate(kept, start=1):
        question["id"] = f"q{position}"

    return {**qs, "spine": kept, "declined_to_ask": declined}, notes


def climb(kind: str, raw: Any, **checks: Any) -> tuple[dict | None, list[str], list[str]]:
    """
    Run rungs 0 and 1, then validate. Returns (artifact, defects, repair_notes).

    A non-empty defect list is what rung 2's retry prompt carries: the rejected
    artifact plus a machine-written list naming each failed constraint.
    """
    notes: list[str] = []
    obj: Any = raw
    if isinstance(raw, str):
        obj, how = repair_json(raw)
        if obj is None:
            return None, ["rung 0: payload is not recoverable as JSON"], notes
        if how != "clean":
            notes.append(f"rung 0: repaired via {how}")

    obj = coerce_fields(obj, notes)
    if kind == "question_set" and isinstance(obj, dict):
        obj, class_notes = quarantine_unclassed_questions(obj)
        notes.extend(class_notes)

    validator = {
        "question_set": validate_question_set,
        "answer_ledger": validate_answer_ledger,
        "build_plan": validate_build_plan,
    }[kind]
    return obj, validator(obj, **checks), notes


# ---------------------------------------------------------------------------
# The overlay capability record — the registration matrix as ONE record
# ---------------------------------------------------------------------------
#
# Registration is not a checklist of edits to tracked files. It is one record,
# written by the writer into the overlay, that the four load seams read.
#
# The live evidence that humans do not complete a checklist reliably is in the
# tree right now: `config/agents/time_director.md` exists, `_AGENT_NAME_MAP`
# maps to it, `_UNAVAILABLE_CONSEQUENCE` carries a line for it — and it appears
# in NEITHER routing file nor the Coordinator's name list. Anything naming it
# raises at core/router.py:112-117. A half-wired agent is in the tree today.
# One record with required fields is the answer to that class of defect; a
# longer checklist is not.

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_AGENT_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{2,31}$")


# Letters, digits, spaces and an ampersand. Nothing else, because this string is
# SPLICED INTO A PROMPT by seam 3 — inside a backticked, quoted item in a closed
# list — so a backtick, a quote or a newline in it rewrites the sentence the
# Coordinator is reading rather than merely looking odd. Underscores are refused
# too: a display name is a human string, and one that looks like an identifier
# invites exactly the confusion between the two names this record separates.
_DISPLAY_NAME_RE = re.compile(r"^[A-Za-z0-9 &]+$")


def validate_overlay_capability(record: dict,
                                tracked_names: set[str] | None = None,
                                read_set: set[str] | None = None,
                                known_domains: set[str] | None = None,
                                reserved_display: set[str] | None = None,
                                model_ref_names: set[str] | None = None,
                                peer_displays: dict[str, str] | None = None) -> list[str]:
    """
    Return the defect list for an overlay capability record. Empty means valid.

    `tracked_names` is the union of THREE sets — the agents in routing.yaml,
    the agents in routing_cloud.yaml, and the stems of config/agents/*.md — and
    the union is load-bearing rather than belt-and-braces. The routing files
    alone are not enough: `time_director` and `goals_interview_reference` have
    agent files and no routing entry, so a record named `time_director` would
    pass a routing-only check and then be split across the seams — seam 1 loads
    the TRACKED prose, seam 2 merges the OVERLAY's tools and model. Tracked
    wins in every seam, so the collision lands a record nothing ever loads
    whole. It is refused up front instead.

    `read_set` is the writer's hardcoded grant allowlist, passed in rather than
    imported so there is exactly one home for it (core/build/writer.py). Both
    routing entries' `allowed_tools` must be identical and both a subset of it.

    Each argument defaults to None meaning "not checked here" — the writer
    always passes all three, and check_build_registration.py re-asserts the
    same three-set rule independently.
    """
    defects: list[str] = []
    if not isinstance(record, dict):
        return ["overlay_capability is not an object"]

    expected = SCHEMA_VERSIONS["overlay_capability"]
    if _text(record.get("schema")) != expected:
        defects.append(f"schema must be {expected!r}, got {record.get('schema')!r}")

    from core.build.ids import is_job_id
    if not is_job_id(_text(record.get("job_id"))):
        defects.append(f"job_id {record.get('job_id')!r} is not a BLD-MMDD-NN id")

    version = record.get("version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        defects.append("version must be a positive integer")
    if _is_blank(record.get("generated_at")):
        defects.append("generated_at is missing")

    name = _text(record.get("name"))
    if not _AGENT_NAME_RE.match(name):
        defects.append(f"name {name!r} must match {_AGENT_NAME_RE.pattern}")
    elif tracked_names is not None and name in tracked_names:
        defects.append(
            f"name {name!r} collides with a tracked agent — a record by that "
            "name would be split across the seams (tracked prose, overlay "
            "tools) and never loaded whole"
        )

    display = _text(record.get("display_name"))
    if not display:
        defects.append("display_name is empty — it is what the Coordinator copies")
    elif not _DISPLAY_NAME_RE.match(display):
        defects.append(
            f"display_name {display!r} must match {_DISPLAY_NAME_RE.pattern} — it "
            "is spliced into a quoted item inside the Coordinator's closed "
            "valid-name list, so punctuation in it rewrites that sentence"
        )
    else:
        defects.extend(_check_display_name(
            display, _text(record.get("name")), tracked_names, reserved_display,
            peer_displays))

    if _text(record.get("agent_file")) != f"agents/{name}.md":
        defects.append(
            f"agent_file must be 'agents/{name}.md', got "
            f"{record.get('agent_file')!r} — the record and the file it names "
            "are loaded by different seams and must not be able to disagree"
        )
    if not _SHA256_RE.match(_text(record.get("agent_sha256")).lower()):
        defects.append("agent_sha256 is not a 64-character hex digest")

    _check_overlay_routing(record, read_set, model_ref_names, defects)

    coordinator = record.get("coordinator")
    if not isinstance(coordinator, dict):
        defects.append("coordinator block is missing")
    else:
        entry = _text(coordinator.get("directory_entry"))
        if not entry:
            defects.append("coordinator.directory_entry is empty")
        elif display and display not in entry:
            defects.append(
                f"coordinator.directory_entry does not name {display!r} — the "
                "directory entry and the valid-name list are spliced into the "
                "same prompt and must agree"
            )

    if _is_blank(record.get("unavailable_consequence")):
        defects.append(
            "unavailable_consequence is empty — an area with no entry degrades "
            "to a bare statement, which is safe but tells the user nothing"
        )

    _check_overlay_confidential(record, name, defects)

    domains = record.get("knowledge_domains", [])
    if not isinstance(domains, list):
        defects.append("knowledge_domains must be a list")
    elif known_domains is not None:
        for domain in domains:
            if _text(domain) not in known_domains:
                defects.append(
                    f"knowledge_domains names {domain!r}, which is not a "
                    "wisdom domain — a capability may join an existing domain, "
                    "never create one"
                )

    mode = _text(record.get("execution_mode")).lower()
    if mode not in EXECUTION_MODES:
        defects.append(f"execution_mode must be one of {list(EXECUTION_MODES)}")
    budget = record.get("latency_budget_ms")
    if not isinstance(budget, (int, float)) or isinstance(budget, bool) or budget <= 0:
        defects.append("latency_budget_ms must be a positive number")

    return defects


def _collapse(text: str) -> str:
    """
    The COMPARISON FORM of a display name: internal whitespace collapsed to one
    space, ends trimmed, case folded by the caller.

    `Mental  Wellbeing` passed every check it should have failed: it satisfies
    the charset, normalises to `mental__wellbeing` which is not a tracked agent,
    and lowercases to a string the reserved set does not contain — so it spliced
    into the closed valid-name list one space away from the real entry, on a
    model whose own map comment records that it cannot reliably copy that list.
    Every display-name comparison now runs on this form.
    """
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _resolve_display(display: str) -> str:
    """The agent name a display string dispatches to, via the Coordinator's own map."""
    collapsed = _collapse(display)
    try:
        from core.orchestrator import normalize_agent_name
        return normalize_agent_name(collapsed)
    except Exception:
        return collapsed.lower().replace(" & ", "_").replace(" and ", "_") \
                        .replace(" ", "_")


def _check_display_name(display: str, own_name: str,
                        tracked_names: set[str] | None,
                        reserved_display: set[str] | None,
                        peer_displays: dict[str, str] | None) -> list[str]:
    """
    Four collisions, in order of severity. Each returns immediately: one clear
    reason is more useful than four restatements of the same string.

    THE NAME RULE WAS NEVER ENOUGH. `name` was checked against three sets and
    `display_name` against none — but display_name is the string the model
    copies and the string seam 3 splices into the closed list, and it resolves
    to an agent name through the generic fallback whether or not anything
    registered it.

    The fourth collision is the one the first fix missed: a second GENERATED
    capability capturing the first one's dispatch. Not tracked shadowing — the
    same mechanism one layer down, arriving on the second landed capability,
    which is exactly the bootstrap sequence in plan Section 11.
    """
    defects: list[str] = []
    collapsed = _collapse(display)
    lowered = collapsed.casefold()
    resolved = _resolve_display(collapsed)

    if tracked_names and resolved in tracked_names:
        return [f"display_name {display!r} resolves to tracked agent {resolved!r} "
                "— the Coordinator would dispatch that agent instead"]

    if reserved_display:
        reserved = {_collapse(r).casefold() for r in reserved_display}
        if lowered in reserved or resolved in reserved_display:
            return [f"display_name {display!r} is already a name the Coordinator "
                    "knows — it is in the name map or the closed valid-name "
                    "list, or differs from one only by whitespace or case"]

    for peer_name, peer_display in (peer_displays or {}).items():
        if peer_name == own_name:
            continue
        if _collapse(peer_display).casefold() == lowered:
            defects.append(
                f"display_name {display!r} duplicates the display name of "
                f"overlay capability {peer_name!r} — the closed valid-name list "
                "would carry the same string twice and the name map would keep "
                "one winner, chosen by sort order"
            )
            return defects
        if resolved == peer_name:
            defects.append(
                f"display_name {display!r} resolves to overlay capability "
                f"{peer_name!r} — it would capture that capability's dispatch"
            )
            return defects
    return defects


def _check_overlay_routing(record: dict, read_set: set[str] | None,
                           model_ref_names: set[str] | None,
                           defects: list[str]) -> None:
    """
    BOTH entries, one record — parity is a schema property, not a convention.

    v2 demanded routing_local and routing_cloud in the same apply() call; a
    record missing either entry does not validate and cannot be written at all.
    The evidence that convention alone does not hold is routing.yaml itself: the
    2026-07-27 diarist fix landed write_log/write_wisdom in the cloud file and
    missed the local one, silently losing both under DEPLOYMENT_MODE=local.
    """
    routing = record.get("routing")
    if not isinstance(routing, dict):
        defects.append("routing block is missing — both entries live in one record")
        return

    local = routing.get("local")
    cloud = routing.get("cloud")
    if not isinstance(local, dict):
        defects.append("routing.local is missing")
    if not isinstance(cloud, dict):
        defects.append("routing.cloud is missing")
    if not isinstance(local, dict) or not isinstance(cloud, dict):
        return

    if local.get("local") is not True:
        defects.append(
            "routing.local.local must be true — a generated capability is "
            "Sensitive unless it can demonstrate it never touches persona data"
        )
    # PROVIDER IS INHERITED, NEVER DECLARED. `model_ref` existed so a record
    # could not pin a stale model id — and a record could still pin a PROVIDER,
    # which seam 2 honoured. That let a record route itself to another vendor
    # entirely while every field in it looked correct. Both halves now come from
    # the tracked agent the ref names.
    if cloud.get("provider") is not None:
        defects.append(
            "routing.cloud.provider is set — provider and model are both "
            "inherited from the agent model_ref names, so that a record cannot "
            "route itself to a vendor nobody chose for it"
        )

    # A model id, not a model ref, is the failure this refuses. Ids have a short
    # half-life here — the reasoning tier moved twice in four days this month —
    # and a generated record pinning one would strand the capability on a
    # retired id with nobody editing it. Seam 2 resolves the ref at load time.
    ref = _text(cloud.get("model_ref"))
    if not ref:
        defects.append("routing.cloud.model_ref is empty")
    elif not _AGENT_NAME_RE.match(ref):
        defects.append(
            f"routing.cloud.model_ref {ref!r} is not an agent name — it must "
            "name a tracked agent whose live model seam 2 resolves, never a "
            "model id, which goes stale with nobody editing this record"
        )
    elif model_ref_names is not None and ref not in model_ref_names:
        defects.append(
            f"routing.cloud.model_ref {ref!r} is not in BOTH routing files — a "
            "ref present in only one resolves under one DEPLOYMENT_MODE and "
            "vanishes under the other, which is the split the one-record shape "
            "exists to make impossible"
        )
    if cloud.get("model") is not None:
        defects.append(
            "routing.cloud.model is set — a record pins a model_ref, never a model"
        )

    local_tools = local.get("allowed_tools")
    cloud_tools = cloud.get("allowed_tools")
    for label, tools in (("local", local_tools), ("cloud", cloud_tools)):
        if not isinstance(tools, list):
            defects.append(f"routing.{label}.allowed_tools must be a list")
    if not isinstance(local_tools, list) or not isinstance(cloud_tools, list):
        return

    if list(local_tools) != list(cloud_tools):
        defects.append(
            "routing.local.allowed_tools and routing.cloud.allowed_tools differ "
            "— the grant is the same grant whichever file serves it, and a "
            "split one is the 2026-07-27 diarist defect"
        )
    if read_set is not None:
        outside = sorted({_text(t) for t in local_tools} - read_set)
        if outside:
            defects.append(
                f"allowed_tools names {outside}, outside the read set — a grant "
                "not on the allowlist is refused whether or not anything names "
                "it as dangerous"
            )


def _check_overlay_confidential(record: dict, name: str, defects: list[str]) -> None:
    """
    confidential_names go to the SENTENCE-GATED list, never the unconditional one.

    _ALWAYS_CONFIDENTIAL is for identifiers "impossible in natural prose", and
    one substring hit replaces the whole reply with the canned fallback — its
    matcher joins tokens across up to four punctuation characters or none, so
    `home_care` there would suppress "your home-care tasks" and a single-word
    name like `garden` would suppress every reply containing that word.
    _CONTEXT_SENSITIVE fires only inside a sentence carrying architecture
    vocabulary, which is exactly the mechanism for a name that is also English.

    The record cannot choose which list it lands on — seam 4 hardcodes that —
    so what is checked here is only that the names are present and include the
    capability's own name, which is the one that would otherwise be missed.
    """
    names = record.get("confidential_names")
    if not isinstance(names, list) or not names:
        defects.append("confidential_names must be a non-empty list")
        return
    flat = {_text(n) for n in names}
    if name and name not in flat:
        defects.append(
            f"confidential_names does not include {name!r} — the capability's "
            "own name is the one the filter must know about"
        )
