"""
core/build/schemas.py — the three artifacts and their validators.

QuestionSet, AnswerLedger, BuildPlan. All three carry `schema`, `job_id`, an
upstream fingerprint and `generated_at`, so any artifact can be traced to the
one it was derived from.

SALVAGED BY COPY from the v3 package (plan v4.11 section 10). What changed is
only what ruling 5 and ruling 7 changed: Inquiry works in a VACUUM, so a
Question Set naming `candidate_sources` or a `manifest_fingerprint` is now a
DEFECT rather than a requirement — it would mean the model saw the corpus. The
ledger became an INVENTORY with two verdicts per row. THE COMPASS-RULE ORDERING
BELOW IS UNCHANGED, DELIBERATELY AND EXACTLY: it is the one piece of this file
that was validated against a real transcript, and the fixture that validates it
(tests/test_build_spine.py) is carried across unmodified.

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

import hashlib
import json
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

# ---------------------------------------------------------------------------
# THE TWO VERDICTS PER ROW (ruling 7). They answer different questions and
# conflating them is the failure the ruling names.
#
#   VERDICTS   what the Librarian found FOR THIS PERSONA.
#   LACKS      what the capability does for a user who HAS NONE OF IT.
#
# A `found` row for Mike says nothing about a persona created tomorrow, and a
# capability built only against what Mike happens to have is a capability that
# breaks on its second user. `if_user_lacks_it` is the second answer, required
# on every row the plan marks as a required input.
# ---------------------------------------------------------------------------
VERDICTS: tuple[str, ...] = ("found", "inadequate", "ask_user", "external", "absent")

# `degrade:` and `refuse:` carry their how/message after the colon; `ask` and
# `n/a` stand alone. Checked by prefix so the payload is free text.
LACKS_BARE: frozenset[str] = frozenset({"ask", "n/a"})
LACKS_PREFIXED: tuple[str, ...] = ("degrade:", "refuse:")

# What KIND of thing the question is asking for. This is the field the ruling-7
# rule keys on: a HISTORY is asked for and then accrues, so it may never be a
# variable; a PROFILE FACT is exactly a variable and must say where it lives.
ROW_KINDS: tuple[str, ...] = ("history", "profile_fact", "external", "judgment")

EXTERNAL_ACCESS: tuple[str, ...] = ("api", "feed", "web")

# Code-derived from the verdict, never written by the model.
ROW_STATUSES: tuple[str, ...] = ("settled", "to_ask", "external_pending", "missing")

_STATUS_FOR_VERDICT: dict[str, str] = {
    "found": "settled",
    "inadequate": "missing",
    "ask_user": "to_ask",
    "external": "external_pending",
    "absent": "missing",
}

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


def artifact_fingerprint(artifact: dict) -> str:
    """
    The digest a downstream artifact carries as `upstream_fingerprint`.

    DISTINCT FROM manifest.fingerprint(), which is not a general artifact digest
    and must not be used as one: it hashes source, capability and policy ids
    only, so every question set and every ledger would hash IDENTICALLY through
    it — an upstream_fingerprint that cannot tell two artifacts apart is worse
    than none, because it looks like provenance.

    The volatile header is excluded so a re-read of the same artifact digests
    the same: `generated_at` is a clock reading, and the two fingerprint fields
    are what this is computing.
    """
    volatile = {"generated_at", "upstream_fingerprint", "manifest_fingerprint"}
    material = {k: v for k, v in (artifact or {}).items() if k not in volatile}
    blob = json.dumps(material, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# QuestionSet
# ---------------------------------------------------------------------------

# Fields Inquiry CANNOT have written, because it never saw the corpus (ruling 5).
# Their PRESENCE is the defect, not their absence: a Question Set carrying one
# is evidence that something showed the model the manifest, which is exactly
# what working in a vacuum means it must not have.
VACUUM_FORBIDDEN: tuple[str, ...] = (
    "candidate_sources", "manifest_fingerprint", "policies_consulted",
)


def validate_question_set(qs: dict,
                          known_capabilities: set[str] | None = None) -> list[str]:
    """
    Return the defect list. Empty means valid.

    `known_capabilities` is the set of tracked specialists — read by CODE from
    config/agents/*.md, never shown to Inquiry as data. It is what a
    `disposition: new` claim is checked against. When None that one check is NOT
    RUN, and that is stated here rather than silently passing.

    `manifest_ids` is GONE as a parameter. It existed to validate
    `candidate_sources`, and under ruling 5 naming a source is the defect.
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

    proposed = _text(qs.get("proposed_depth")).lower()
    if proposed and proposed not in DEPTHS:
        defects.append(
            f"proposed_depth must be one of {list(DEPTHS)}, got "
            f"{qs.get('proposed_depth')!r}"
        )

    # THE VACUUM RULE, ENFORCED RATHER THAN INSTRUCTED (ruling 5). Inquiry sees
    # the gap and nothing about what data exists, so it cannot name a source, a
    # manifest digest or a policy it has consulted. A model that filled one of
    # these invented it — and an invented `candidate_sources` is worse than an
    # empty one, because the Librarian would read it as a lead.
    for field in VACUUM_FORBIDDEN:
        present = qs.get(field)
        if present in (None, "", [], {}):
            continue
        defects.append(
            f"{field} is present — Inquiry works in a vacuum and has seen no "
            "manifest, no corpus and no policy, so this field can only have "
            "been invented (ruling 5)"
        )
        if field == "candidate_sources":
            break

    if not isinstance(qs.get("declined_to_ask", []), list):
        defects.append("declined_to_ask must be a list")

    spine = qs.get("spine")
    if not isinstance(spine, list) or not spine:
        defects.append("spine is empty or not a list")
        return defects

    _check_questions(spine, defects)
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


def _check_questions(spine: list, defects: list[str]) -> None:
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

        # PER-QUESTION VACUUM RULE. The set-level check above catches the
        # header field; this catches the same invention one level down, where
        # a model that has been told not to name sources tends to put them.
        if question.get("candidate_sources"):
            defects.append(
                f"{where} names candidate_sources — Inquiry has seen no "
                "manifest, so a named source is a guess the Librarian would "
                "read as a lead (ruling 5)"
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

# Header fields whose value only CODE can know: the job's own id, and the digest
# over an artifact the model never sees whole. climb(inject=) writes these and
# refuses anything else, so the hatch cannot widen into a way of supplying an
# answer the model was asked for and did not give.
CODE_WRITTEN_HEADER_FIELDS: frozenset[str] = frozenset({
    "job_id", "manifest_fingerprint", "upstream_fingerprint", "generated_at",
})

# `status` is DERIVED FROM `verdict`, never asserted. Two fields that could
# disagree about the same fact is the class of defect the single-ledger rule
# exists to close, and a model asked for both will eventually give two answers.
CODE_WRITTEN_LEDGER_FIELDS: tuple[str, ...] = ("status",)


def strip_code_written(row: dict) -> dict:
    """Drop the fields only code may write. Called before validation, always."""
    return {k: v for k, v in row.items() if k not in CODE_WRITTEN_LEDGER_FIELDS}


def derive_status(row: dict) -> str:
    """The code-derived `status` for one ledger row, from its verdict alone."""
    return _STATUS_FOR_VERDICT.get(_text(row.get("verdict")).lower(), "missing")


def apply_derived_status(ledger: dict) -> dict:
    """`ledger` with every row's `status` rewritten from its verdict."""
    rows = ledger.get("rows")
    if not isinstance(rows, list):
        return ledger
    out = dict(ledger)
    out["rows"] = [
        {**row, "status": derive_status(row)} if isinstance(row, dict) else row
        for row in rows
    ]
    return out


def record_interview_answer(ledger: dict, question_id: str, answer: str,
                            when: str | None = None) -> dict:
    """
    Write [N6]'s answer into its row, in the one shape the rest of the system
    reads. Returns the updated ledger; raises SchemaError on an unknown id.

    THE LEDGER HAS NO `answer` FIELD, and this is the encoding chosen instead.
    An `ask_user` row left as it is carries Mike's answer nowhere the Planner or
    the question table reads, so the answer is invisible to the reviewer at N8
    and to Mike at [N9]; flipped to `found` by hand it needs an inventory block,
    which invites a fabricated one.

    So the inventory is written HERE, by code, and every field of it is true:
    the source IS the user, the form IS an interview, the coverage IS the day it
    was said, and it WAS said once at build time. The answer itself goes in
    `decision`, which is the one field beyond the inventory that
    `table._location()` renders — so the answer reaches the audit that exists to
    show every question travelled.

    A first-class `answer` field rendered by table.py would be cleaner; table.py
    was outside this change's permitted files.
    """
    rows = ledger.get("rows")
    if not isinstance(rows, list):
        raise SchemaError("answer_ledger", ["rows is missing"])
    text = str(answer or "").strip()
    if not text:
        raise SchemaError("answer_ledger", [
            f"the interview answer for {question_id!r} is empty — an unanswered "
            "interview item stays `ask_user`; it is not answered with nothing"])

    day = when or datetime.now().date().isoformat()
    updated, found = [], False
    for row in rows:
        if not isinstance(row, dict) or _text(row.get("question_id")) != question_id:
            updated.append(row)
            continue
        found = True
        updated.append({
            **row,
            "verdict": "found",
            "decision": text,
            "inventory": {
                **(row.get("inventory") or {}),
                "source": "user",
                "form": "interview",
                "coverage": {"from": day, "to": day},
                "completeness": "stated once, by the user, at build time",
                "freshness": day,
            },
        })
    if not found:
        raise SchemaError("answer_ledger", [
            f"no ledger row for {question_id!r} — an interview item must name a "
            "question that travelled"])

    out = dict(ledger)
    out["rows"] = updated
    return apply_derived_status(out)


def open_interview_items(ledger: dict) -> list[str]:
    """Question ids still awaiting the user. What N5 writes to ledger_check."""
    return [_text(row.get("question_id"))
            for row in (ledger.get("rows") or [])
            if isinstance(row, dict)
            and _text(row.get("verdict")).lower() == "ask_user"]


def validate_answer_ledger(ledger: dict, question_ids: list[str] | None = None,
                           declared_variables: set[str] | None = None,
                           required_inputs: set[str] | None = None) -> list[str]:
    """
    Return the defect list. Empty means valid.

    `declared_variables` is read from the LIVE home through a read door, never
    from a Mac copy — a variable name is unique against what is actually
    declared there, not against what a checkout believes is declared.

    `required_inputs` is the set of question ids the plan marks as required.
    It arrives late, because the plan does not exist at N5: the ledger is
    validated once without it, and again at N7 with it, which is what makes
    `if_user_lacks_it` required on exactly the rows that need it.
    """
    defects: list[str] = []
    if not isinstance(ledger, dict):
        return ["answer_ledger is not an object"]

    _common_header(ledger, "answer_ledger", defects)

    rows = ledger.get("rows")
    if not isinstance(rows, list) or not rows:
        defects.append("rows is empty or not a list")
        return defects

    for field in ("interview_items", "variable_proposals", "policies_matched"):
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
        _check_ledger_row(row, where, declared_variables, defects, required_inputs)

    if question_ids is not None:
        expected, got = set(question_ids), set(seen_questions)
        if expected - got:
            defects.append(
                f"no ledger row for questions: {sorted(expected - got)} — EVERY "
                "question travels, settled or not (ruling 6); a question with no "
                "row is one the Planner will never see and never cite")
        if got - expected:
            defects.append(f"ledger rows for unknown questions: {sorted(got - expected)}")
    if len(set(seen_questions)) != len(seen_questions):
        defects.append("more than one row for the same question")

    _check_surface_map(ledger.get("surface_map"), "answer_ledger", defects)
    return defects


def _check_ledger_row(row: dict, where: str, declared_variables: set[str] | None,
                      defects: list[str], required_inputs: set[str] | None = None) -> None:
    """
    One inventory row. TWO VERDICTS, and the rules that hang off each.

    `required_inputs` is the set of question ids the PLAN marks as required
    inputs. `if_user_lacks_it` is mandatory on exactly those rows — demanding it
    everywhere would put a slot in front of a model for rows where the honest
    answer is "this shaped nothing", and tools/logger.py:411's 93 "None." events
    are what a slot with no answer produces.
    """
    question_id = _text(row.get("question_id"))
    verdict = _text(row.get("verdict")).lower()
    if verdict not in VERDICTS:
        defects.append(
            f"{where} verdict must be one of {list(VERDICTS)}, got "
            f"{row.get('verdict')!r} — this is what the Librarian found FOR THIS "
            "PERSONA, and it is not the same question as what a user lacking it "
            "gets (ruling 7)"
        )

    kind = _text(row.get("kind")).lower()
    if kind not in ROW_KINDS:
        defects.append(f"{where} kind must be one of {list(ROW_KINDS)}")

    answerable_by = _text(row.get("answerable_by")).lower()
    if answerable_by not in ANSWERABLE_BY:
        defects.append(f"{where} answerable_by must be one of {list(ANSWERABLE_BY)}")

    data_kind = _text(row.get("data_kind")).lower()
    if data_kind not in DATA_KINDS:
        defects.append(f"{where} data_kind must be one of {list(DATA_KINDS)}")

    _check_inventory(row, where, verdict, defects)
    _check_lacks(row, where, question_id, required_inputs, defects)

    # A HISTORY MAY NEVER BE A VARIABLE (ruling 7). A history is asked for and
    # then ACCRUES — the capability logs it turn by turn. Declaring one as a
    # profile variable freezes a moving quantity into a field somebody has to
    # remember to update, and nothing ever does.
    if kind == "history" and (row.get("variable_scope") or row.get("variable_name")):
        defects.append(
            f"{where} kind: history declares a variable — a history is asked for "
            "and then accrues; it is not a variable (ruling 7)"
        )

    # A PROFILE FACT IS EXACTLY A VARIABLE, so it must say which home.
    if kind == "profile_fact":
        if not _text(row.get("variable_scope")):
            defects.append(
                f"{where} kind: profile_fact has no variable_scope — a stable "
                f"fact must name its home, one of {list(VARIABLE_SCOPES)}"
            )
        if not _text(row.get("variable_name")):
            defects.append(f"{where} kind: profile_fact has no variable_name")

    if kind == "external":
        _check_external(row, where, defects)
    elif any(row.get(f) for f in ("source_name", "access", "on_failure")):
        defects.append(
            f"{where} carries external-row fields but kind is {kind!r} — an "
            "outbound source is declared by kind, so the two cannot disagree"
        )

    if answerable_by == "judgment" or kind == "judgment":
        # A judgment with one option is a decision already made, presented as a
        # choice. Two is the floor for the gate to mean anything at runtime.
        options = row.get("decision_options")
        if not isinstance(options, list) or len(options) < 2:
            defects.append(
                f"{where} a judgment row requires decision_options with "
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

    _check_variable_home(row, where, declared_variables, defects)


def _check_inventory(row: dict, where: str, verdict: str,
                     defects: list[str]) -> None:
    """
    The inventory block: what exists, in what form, over what period, how
    complete, how fresh, and WHAT IS MISSING, in words (ruling 5).

    The `gap` field is the one that earns the block. "How complete" as a
    percentage is a number nobody can act on; "no entries before March, and
    none at all for weekday mornings" is a finding the Planner can design
    around. So the gap is prose and it is REQUIRED on every verdict that is
    not `found` — an `inadequate` row whose gap is empty has recorded a
    complaint rather than a finding.
    """
    inventory = row.get("inventory")
    if verdict == "absent":
        # Nothing exists, so there is nothing to inventory. The gap still has
        # to be stated, and it is stated in the row.
        if _is_blank(row.get("gap")) and not (
                isinstance(inventory, dict) and not _is_blank(inventory.get("gap"))):
            defects.append(
                f"{where} verdict: absent with no gap — 'nothing is recorded' "
                "is the finding, and it has to be written down as one")
        return

    if not isinstance(inventory, dict):
        defects.append(
            f"{where} verdict: {verdict} has no inventory block — the verdict is "
            "the conclusion and the inventory is the evidence for it")
        return

    for field in ("source", "form"):
        if _is_blank(inventory.get(field)):
            defects.append(f"{where} inventory.{field} is empty")

    coverage = inventory.get("coverage")
    if verdict in {"found", "inadequate"}:
        if not isinstance(coverage, dict) or _is_blank(coverage.get("from")) \
                or _is_blank(coverage.get("to")):
            defects.append(
                f"{where} inventory.coverage needs from and to — 'it exists' "
                "without a period is not an inventory")
        for field in ("completeness", "freshness"):
            if _is_blank(inventory.get(field)):
                defects.append(f"{where} inventory.{field} is empty")

    if verdict != "found" and _is_blank(inventory.get("gap")) \
            and _is_blank(row.get("gap")):
        defects.append(
            f"{where} verdict: {verdict} states no gap — what is MISSING, in "
            "words, is the whole finding; without it the Planner has a "
            "complaint rather than something to design around")


def _check_lacks(row: dict, where: str, question_id: str,
                 required_inputs: set[str] | None, defects: list[str]) -> None:
    """The second verdict: what happens for a user who has none of it."""
    raw = _text(row.get("if_user_lacks_it"))
    lowered = raw.lower()
    required = required_inputs is not None and question_id in required_inputs

    if not raw:
        if required:
            defects.append(
                f"{where} is a required input with no if_user_lacks_it — the "
                "capability has no stated behaviour for a user who lacks it, "
                "which is the second verdict ruling 7 requires")
        return

    if lowered in LACKS_BARE:
        return
    for prefix in LACKS_PREFIXED:
        if lowered.startswith(prefix):
            if len(raw) <= len(prefix):
                defects.append(
                    f"{where} if_user_lacks_it is {raw!r} with nothing after the "
                    "colon — 'degrade' and 'refuse' are only meaningful with the "
                    "how or the message attached")
            return
    defects.append(
        f"{where} if_user_lacks_it {raw!r} must be one of "
        f"{sorted(LACKS_BARE)} or start with one of {list(LACKS_PREFIXED)}")


def _check_external(row: dict, where: str, defects: list[str]) -> None:
    """
    An outbound source states its failure behaviour and its privacy side.

    `carries_personal_context` is the section 0 line drawn at record level: the
    plan must say which side of it the query sits on BEFORE Mike approves, not
    after an integration is built. A missing boolean is not "false" — it is a
    question nobody answered, so it is a defect.
    """
    if _is_blank(row.get("source_name")):
        defects.append(f"{where} external row has no source_name")

    access = _text(row.get("access")).lower()
    if access and access not in EXTERNAL_ACCESS:
        defects.append(f"{where} access must be one of {list(EXTERNAL_ACCESS)}")

    if _is_blank(row.get("on_failure")):
        defects.append(
            f"{where} external row has no on_failure — an outbound source that "
            "does not say what happens when it is down has made its own "
            "availability a silent dependency of the capability")

    if not isinstance(row.get("carries_personal_context"), bool):
        defects.append(
            f"{where} carries_personal_context must be a boolean — it decides "
            "which side of the privacy ruling the outbound query sits on, and "
            "an unanswered question is not a 'no'")

    if not isinstance(row.get("key_needed"), bool):
        defects.append(
            f"{where} key_needed must be a boolean — a key is an (M) item and "
            "the plan says so before approval, not after")


def _check_variable_home(row: dict, where: str, declared_variables: set[str] | None,
                         defects: list[str]) -> None:
    """
    Where a declared variable lives, and the ruling-4 consequence of each home.

    SALVAGED. The one rule added in v4: `all_personas` is TWO THINGS, because
    the template reaches no persona that already exists (finding 10 —
    tools/profile.py resolves the persona's own file with no template fallback,
    and config/templates/profile.yaml is read only by new_persona.sh). So the
    tracked template entry alone leaves `mike` without the field forever. The
    plan-level half of that rule is in _check_plan_variables(); this is the
    ledger-level half, which is that the row has to carry the ask path.
    """
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

    if scope == "all_personas" and _text(row.get("if_user_lacks_it")).lower() != "ask":
        defects.append(
            f"{where} declares an all_personas variable without "
            "`if_user_lacks_it: ask` — the tracked template entry reaches only "
            "personas created AFTER it lands, so without the runtime ask path "
            "every persona that exists today, mike included, never gets the "
            "field (finding 10)"
        )

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

# THE DECISION GATES EVERY PLAN HAS TO CITE (ruling 6). A gate is a place the
# plan chose one thing over another; a choice with no question behind it was
# made by the model rather than by the inquiry, and "every question travels" is
# only true if the travelling is checked at the far end.
PLAN_GATES: tuple[str, ...] = (
    "capability", "surface_map", "information_sources", "variables",
)


def validate_build_plan(plan: dict, red_paths: set[str] | None = None,
                        question_ids: set[str] | None = None) -> list[str]:
    """
    Return the defect list. Empty means valid.

    `red_paths` is the Red half of the tier table, resolved from
    .claude/settings.json at N7. A plan that puts a Red path in the
    IMPLEMENTER's half of `files[]` fails HERE, before N11 — finding 2: the
    implementer never touches a Red file, and the cheapest place to establish
    that is before a subagent is spawned at all.

    `question_ids` is the Question Set's ids. Citations are checked against it
    so a plan cannot cite a question that was never asked.
    """
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

    for field in ("files", "registration", "tests", "variables", "risks",
                  "citations", "information_sources", "integrations"):
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
            "defect the registration matrix exists to end"
        )

    _check_record(plan, kind, defects)
    _check_required_inputs(plan, question_ids, defects)
    _check_citations(plan, question_ids, defects)
    _check_files(plan, red_paths, defects)
    _check_information_sources(plan, defects)
    _check_integrations(plan, defects)
    _check_plan_variables(plan, defects)
    _check_state_record(plan, defects)
    return defects


# The fields core/build/verify.content_gate reads. Three are prompt text that
# the Coordinator or the Synthesizer will carry; the fourth is the grant.
RECORD_PROSE_FIELDS: tuple[str, ...] = (
    "display_name", "directory_entry", "unavailable_consequence",
)


def _check_record(plan: dict, kind: str, defects: list[str]) -> None:
    """
    `record{}` — what the content gate reads, and it had no home in this schema.

    Every input content_gate() needs was being assembled by hand at N13 from
    Red prose that had just been typed: the three scanned fields, and
    `routing.allowed_tools`, which is where constitution.check() reads the
    grant from. A record without the last one does not merely skip one check —
    `check_told_not_granted` is passed None and SILENTLY DOES NOT RUN, so a
    generated agent file naming a tool it was never granted passes the gate
    with zero defects.

    Required for `kind: agent` only. A policy or a context_block generates no
    agent file, so there is nothing for these fields to describe.
    """
    if kind != "agent":
        return
    record = plan.get("record")
    if not isinstance(record, dict):
        defects.append(
            "an agent plan has no record{} block — the content gate reads "
            f"{list(RECORD_PROSE_FIELDS)} and routing.allowed_tools from it, and "
            "without it every one of those checks runs on nothing")
        return

    if _is_blank(record.get("name")):
        defects.append("record.name is empty")
    for field in RECORD_PROSE_FIELDS:
        if _is_blank(record.get(field)):
            defects.append(
                f"record.{field} is empty — it is prompt text the content gate "
                "scans, and an empty field is not scanned")

    granted = (record.get("routing") or {}).get("allowed_tools") \
        if isinstance(record.get("routing"), dict) else None
    if not isinstance(granted, list):
        defects.append(
            "record.routing.allowed_tools must be a list — it is where the "
            "told-not-granted scan reads the grant, and when it is absent that "
            "scan is skipped in silence rather than failing")


def _check_required_inputs(plan: dict, question_ids: set[str] | None,
                           defects: list[str]) -> None:
    """
    `required_inputs[]` — the question ids this capability cannot work without.

    The ledger is re-validated against exactly this set at N7, which is what
    makes `if_user_lacks_it` mandatory on those rows and optional elsewhere
    (ruling 7's second verdict). Nothing declared it, so the caller either
    passed None — leaving the rule inert — or invented a proxy that differed
    between sessions.
    """
    required = plan.get("required_inputs")
    if not isinstance(required, list):
        defects.append(
            "required_inputs must be a list of question ids — without it the "
            "ledger's if_user_lacks_it rule is never enforced on any row")
        return
    if question_ids is None:
        return
    unknown = sorted({_text(q) for q in required} - set(question_ids))
    if unknown:
        defects.append(
            f"required_inputs names questions that were never asked: {unknown}")


def required_inputs(plan: dict) -> set[str]:
    """The declared set, as the ledger re-validation wants it."""
    return {_text(q) for q in (plan.get("required_inputs") or []) if _text(q)}


def revalidate_ledger(ledger: dict, plan: dict,
                      question_ids: list[str] | None = None) -> list[str]:
    """
    The N7 re-validation, with `required_inputs` taken FROM THE PLAN.

    One call, so the set cannot be forgotten or guessed at. This is the only
    place `if_user_lacks_it` becomes mandatory, and it is mandatory on exactly
    the rows the plan says it depends on.
    """
    return validate_answer_ledger(ledger, question_ids=question_ids,
                                  required_inputs=required_inputs(plan))


def _check_citations(plan: dict, question_ids: set[str] | None,
                     defects: list[str]) -> None:
    """
    A citation at every decision gate, naming a question id AND a ledger row.

    This is ruling 6's far end. Inquiry's questions are cheap to write and
    cheap to ignore; what makes them load-bearing is that the plan cannot
    declare a capability, a surface, an information source or a variable
    without pointing at the question that produced it. A plan gate with no
    citation fails, which is exactly the assertion section 12 names.
    """
    citations = plan.get("citations")
    if not isinstance(citations, list):
        return                                  # already reported as not-a-list

    cited_gates: set[str] = set()
    for position, citation in enumerate(citations, start=1):
        where = f"citations[{position}]"
        if not isinstance(citation, dict):
            defects.append(f"{where} is not an object")
            continue
        gate = _text(citation.get("gate")).lower()
        if gate not in PLAN_GATES:
            defects.append(f"{where} gate {citation.get('gate')!r} is not one of "
                           f"{list(PLAN_GATES)}")
        else:
            cited_gates.add(gate)
        qid = _text(citation.get("question_id"))
        if not qid:
            defects.append(f"{where} cites no question_id")
        elif question_ids is not None and qid not in question_ids:
            defects.append(
                f"{where} cites {qid!r}, which is not in the Question Set — a "
                "citation to a question nobody asked is worse than none")
        if _is_blank(citation.get("ledger_row")):
            defects.append(
                f"{where} names no ledger_row — a question id alone cites the "
                "asking; the row is what was FOUND, and that is the evidence")

    present_gates = {g for g in PLAN_GATES if plan.get(g) not in (None, "", [], {})}
    for gate in sorted(present_gates - cited_gates):
        defects.append(
            f"decision gate {gate!r} carries no citation — it was decided by the "
            "model rather than by the inquiry (ruling 6)")


def _check_files(plan: dict, red_paths: set[str] | None,
                 defects: list[str]) -> None:
    """
    `files[]`, and the tier split the implementer's half rests on (finding 2).

    Each entry is `{path, half}` where half is `implementer` or `main_session`.
    A RED PATH IN THE IMPLEMENTER'S HALF FAILS HERE — before N11, before a
    subagent exists, which is the cheapest possible place. A Red path in the
    main session's half is correct and expected: that is where the routing
    entries and the agent file go.
    """
    entries = plan.get("files")
    if not isinstance(entries, list):
        return
    seen: set[str] = set()
    for position, entry in enumerate(entries, start=1):
        where = f"files[{position}]"
        path = _text(entry.get("path") if isinstance(entry, dict) else entry)
        if not path:
            defects.append(f"{where} has no path")
            continue
        if path in seen:
            defects.append(f"{where} lists {path!r} twice")
        seen.add(path)
        if path.startswith("/") or ".." in path.split("/"):
            defects.append(
                f"{where} path {path!r} is not repo-relative — an absolute or "
                "climbing path escapes every gate that reads the diff")
        half = _text(entry.get("half") if isinstance(entry, dict) else "").lower()
        if half not in {"implementer", "main_session"}:
            defects.append(
                f"{where} half must be implementer|main_session — the split is "
                "what keeps every Red file in the session where the harness's "
                "ask rules prompt (finding 2)")
            continue
        if half == "implementer" and red_paths and path in red_paths:
            defects.append(
                f"{where} puts the Red path {path!r} in the implementer's half — "
                "the implementer never touches a Red file; that half is the main "
                "session's, where each write prompts Mike (finding 2)")


def _check_information_sources(plan: dict, defects: list[str]) -> None:
    """
    One entry per ledger row the capability READS — and this is the thing that
    becomes the agent file's "where to look" section.

    It carries `if_user_lacks_it` forward from the ledger row rather than
    restating it, because the two going out of step is how a capability ends up
    with a documented degrade path its instructions never mention.
    """
    for position, entry in enumerate(plan.get("information_sources") or [], start=1):
        where = f"information_sources[{position}]"
        if not isinstance(entry, dict):
            defects.append(f"{where} is not an object")
            continue
        for field in ("row_id", "tool", "if_user_lacks_it"):
            if _is_blank(entry.get(field)):
                defects.append(f"{where} {field} is empty")
        if "arguments" in entry and not isinstance(entry["arguments"], dict):
            defects.append(f"{where} arguments must be an object")


def _check_integrations(plan: dict, defects: list[str]) -> None:
    """
    One entry per external row (ruling 5). An outbound source with a key is an
    (M) item, so the plan says so BEFORE approval, not after.
    """
    for position, entry in enumerate(plan.get("integrations") or [], start=1):
        where = f"integrations[{position}]"
        if not isinstance(entry, dict):
            defects.append(f"{where} is not an object")
            continue
        if _is_blank(entry.get("source")):
            defects.append(f"{where} source is empty")
        if not isinstance(entry.get("key_registration_is_m_item"), bool):
            defects.append(
                f"{where} key_registration_is_m_item must be a boolean — an (M) "
                "item that surfaces after approval is one Mike did not agree to")
        for field in ("cost_per_call", "cost_per_month"):
            if entry.get(field) is None:
                defects.append(
                    f"{where} {field} is missing — an integration with no priced "
                    "run cost is a standing charge nobody named (CLAUDE.md Costs)")
        if _is_blank(entry.get("privacy_tier")):
            defects.append(
                f"{where} privacy_tier is empty — the plan must say which side "
                "of the section 0 line the outbound query sits on")


def _check_plan_variables(plan: dict, defects: list[str]) -> None:
    """
    The plan half of the `all_personas` rule (finding 10).

    An `all_personas` variable is TWO things: the tracked template entry, in the
    diff, so future personas start with the field; AND the capability's
    `if_user_lacks_it: ask` path, which creates it through write_profile on
    first use for every persona that exists today. A plan declaring the first
    without the second ships a field `mike` will never have.
    """
    template_paths = {
        _text(e.get("path") if isinstance(e, dict) else e)
        for e in plan.get("files") or []
    }
    for position, variable in enumerate(plan.get("variables") or [], start=1):
        where = f"variables[{position}]"
        if not isinstance(variable, dict):
            defects.append(f"{where} is not an object")
            continue
        scope = _text(variable.get("scope")).lower()
        if scope and scope not in VARIABLE_SCOPES:
            defects.append(f"{where} scope must be one of {list(VARIABLE_SCOPES)}")
        if scope != "all_personas":
            continue
        if _text(variable.get("if_user_lacks_it")).lower() != "ask":
            defects.append(
                f"{where} declares an all_personas variable without "
                "`if_user_lacks_it: ask` — the template reaches no persona that "
                "already exists, so mike would never get the field (finding 10)")
        if not any(p.startswith("config/templates/") for p in template_paths):
            defects.append(
                f"{where} declares an all_personas variable but files[] carries "
                "no config/templates/ entry — the other half of the rule is the "
                "tracked template entry, so future personas start with it")


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
# RUNG 2  TARGETED RETRY     one call, max 1 per node        (core/build/driver.py)
# RUNG 3  REJECT             -> the job parks with the defects (core/build/driver.py)

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


def climb(kind: str, raw: Any, inject: dict | None = None,
          **checks: Any) -> tuple[dict | None, list[str], list[str]]:
    """
    Run rungs 0 and 1, then validate. Returns (artifact, defects, repair_notes).

    A non-empty defect list is what rung 2's retry prompt carries: the rejected
    artifact plus a machine-written list naming each failed constraint.

    `inject` is applied AFTER coercion and BEFORE validation, and exists for one
    narrow class of field: header values only CODE can know. `job_id`,
    `manifest_fingerprint` and `upstream_fingerprint` are all required by the
    validators and none is knowable by the model — asking it to echo a 64-char
    digest would be the `_AGENT_NAME_MAP` problem again, a closed string the
    model's own comment records it cannot copy reliably.

    NEVER USE IT FOR AN ANSWER. It writes the same fields code writes anyway; a
    value injected here is one the model was not asked for, and injecting a
    value it WAS asked for would be inventing the answer, which is the thing
    rung 1 exists to refuse.
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

    if inject and isinstance(obj, dict):
        for field, value in inject.items():
            if field not in CODE_WRITTEN_HEADER_FIELDS:
                # SchemaError takes (kind, defects). Called with one argument
                # here until 2026-09-24, so the guard raised TypeError instead
                # of its own message — the hatch still closed, and the reason it
                # closed was lost. Found by the test that exercises it.
                raise SchemaError("climb", [
                    f"climb(inject=) refuses {field!r}: it is not a header field "
                    f"code owns. Allowed: {sorted(CODE_WRITTEN_HEADER_FIELDS)}"
                ])
            obj[field] = value

    validator = {
        "question_set": validate_question_set,
        "answer_ledger": validate_answer_ledger,
        "build_plan": validate_build_plan,
    }[kind]
    return obj, validator(obj, **checks), notes
