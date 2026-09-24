"""
core/build/runner.py — the thing that actually walks the node graph.

Phases 1-3 built the artifacts, the evidence and the landing surface. Nothing
drove them. This is the driver: `run_node()` for one step, `advance()` for one
job as far as it can go, `tick()` for every job a persona has in flight.

THE STATE IS THE RESUME CURSOR, and this module is where that stops being a
claim. Every node writes `<artifact>.json` atomically and a node that finds a
valid artifact already present RETURNS WITHOUT CALLING A MODEL. So a process
killed mid-node loses at most the node in flight; the next tick re-enters at the
node that had not written. There is no in-memory state here, no lock file, no
daemon holding anything open — `build_tick` could run from cron and the
behaviour would be identical.

THE GATES ARE STATES, NOT CALLBACKS. A job waiting on a human sits in a state
and the tick walks past it. Five stopping places, each a real decision someone
has to make:

    proposed           Mike triages. request_build NEVER auto-queues.
    needs_interview    [N6] only the user can answer these questions.
    awaiting_approval  over budget, or above the writer's autonomy ceiling.
    briefed            [N9] the brief is written and Mike has not approved it.
    verifying          [N13] it is live in the overlay and verified; accept or refuse.

Nothing here resumes a gate by itself. That is the whole point of a gate, and a
tick that could clear one would make every one of them decorative.

BUDGET IS ENFORCED PRE-NODE AND POST-NODE, AND THAT PAIR IS THE WHOLE TRIPWIRE.
Pre-node refuses to START a node past the limit; post-node parks what the CALL
crossed, because a call already issued cannot be aborted. So a job overshoots by
at most one node and then parks at `awaiting_approval` where Mike can raise the
limit. With only the pre-node half the crossing surfaced later, at whatever next
read spend — in practice the Planner's dry-run file check — and FAILED the job
terminally, past the one state that exists to release it.
The retry product is capped explicitly (plan section 13.1): job-level attempts and
node-level retries MULTIPLY, and the cap is counted from the durable spend rows
so a restart cannot reset it.

OVER BUDGET PARKS; IT DOES NOT ASK THROUGH A CONFIRM CARD (correction v3.5 C2,
plan section 8). The job parks at `awaiting_approval`, `tools/build.py`'s
context_block surfaces it conversationally, and the approval is
`cost.approve_limit()` RUN ON THE VM over ssh — never from the Mac board, which
reads the ledger through a read-only fetch and has no write path into the VM's
persona tree. A confirm card would need an `_EXECUTORS` entry, which is
[DB-0815-03] exactly, and would make raising Build's own spend limit a one-tap
action in a design whose deny list exists to stop Build raising its own ceiling.

Plan: archive/plans/build_vertical_plan_2026-09-18.md section 3, section 7, section 8
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Callable

from core.build import brief as BR
from core.build import cost
from core.build import jobs as J
from core.build import registry as R
from core.build import schemas
from core.build import settle as S
from core.build import writer

logger = logging.getLogger(__name__)

# The four Build agents. Named here rather than discovered, because a typo in an
# agent name is a FileNotFoundError at the moment a job is already running and
# costing money, and a constant is where that is cheapest to see.
AGENT_INQUIRY = "build_inquiry"
AGENT_LIBRARIAN = "build_librarian"
AGENT_PLANNER = "build_planner"
AGENT_REVIEW = "build_planner"          # N8b re-reads its own draft; advisory only

# The root trace record every tick pushes, so the three agents have something to
# nest under. core/trace.py nests a record under `pipeline[0]` when
# _SUBAGENT_DEPTH > 0 and nowhere else, so without a root the three agents would
# render as three unrelated top-level entries in The Book.
TRACE_ROOT_AGENT = "build"

# States the tick will not walk past. Defined in jobs.py beside STATES, because
# "which states mean a human has to act" is a property of the state machine, and
# because tools/build.py reads it on every user turn and must not import this
# module to do so. Re-exported here so `runner.GATE_STATES` still reads.
GATE_STATES = J.GATE_STATES

# THE RETRY PRODUCT CAP (plan section 13.1). Four agent nodes, one rung-2 retry each
# is eight calls; the slack above that is for a job resumed mid-node, where the
# completed nodes are skipped but the interrupted one runs again. Counted from
# cost.spend_rows(), which is one row per real model call and survives a restart
# — a counter held in this process would reset on exactly the crash that makes a
# job expensive.
MAX_MODEL_CALLS_PER_JOB = 12

# Rung 2: one targeted retry per node, never more. The repo's stated reason for
# having no retry at all (core/orchestrator.py:2186-2194) is latency on a live
# user turn; Build is tick-driven with nobody waiting, so one capped retry is
# affordable here and nowhere else.
MAX_NODE_RETRIES = 1


class RunnerError(RuntimeError):
    """A node could not be run at all — not a model failure, a structural one."""


@dataclass
class NodeOutcome:
    node: str
    status: str          # done | skipped | gate | parked | blocked | failed
    detail: str = ""

    @property
    def stop(self) -> bool:
        return self.status in {"gate", "parked", "blocked", "failed"}


@dataclass
class Node:
    name: str
    artifact: str | None
    is_agent: bool
    run: Callable[["Context"], NodeOutcome]


@dataclass
class Context:
    job_id: str
    persona: str | None
    job: dict

    def artifact(self, name: str) -> dict | None:
        return J.read_artifact(self.job_id, name, self.persona)

    def write(self, name: str, payload: dict) -> None:
        J.write_artifact(self.job_id, name, payload, self.persona)


# ---------------------------------------------------------------------------
# Pre-node gates
# ---------------------------------------------------------------------------

def _pre_node(ctx: Context, node: Node) -> NodeOutcome | None:
    """
    Every reason not to start this node. None means go.

    Order matters: the global guard first, because a capped day is a fact about
    the machine rather than about this job, and parking a job for its own budget
    when the whole system is stopped would put the wrong reason on the board.
    """
    from core.spend_guard import SpendLimitExceeded, check_before_session

    try:
        check_before_session()
    except SpendLimitExceeded as exc:
        # `blocked` is a FLAG, not a state — the job stays where it is. Mapping
        # it here is what stops _spend_gate()'s "I've paused myself for now..."
        # arriving as an AGENT'S OUTPUT and landing verbatim inside a Question
        # Set, which is what would happen if the node simply ran.
        J.set_blocked(ctx.job_id, f"daily spend guard: {exc}", ctx.persona)
        return NodeOutcome(node.name, "blocked", f"spend guard: {exc}")
    except Exception as exc:                       # pragma: no cover
        logger.warning("[build] spend guard unavailable: %s", exc)

    if node.is_agent:
        calls = len(cost.spend_rows(ctx.job_id, ctx.persona))
        if calls >= MAX_MODEL_CALLS_PER_JOB:
            J.set_state(ctx.job_id, "failed",
                        detail=(f"{calls} model calls — the attempt x retry product "
                                f"cap of {MAX_MODEL_CALLS_PER_JOB} is reached"),
                        persona=ctx.persona)
            return NodeOutcome(node.name, "failed",
                               f"model-call cap {MAX_MODEL_CALLS_PER_JOB} reached")
        try:
            cost.check_budget(ctx.job_id, ctx.persona)
        except cost.BudgetExceeded as exc:
            J.set_state(ctx.job_id, "awaiting_approval", detail=str(exc),
                        resume_to=ctx.job["state"], persona=ctx.persona)
            return NodeOutcome(node.name, "parked", str(exc))

    return None


def _clear_blocked(ctx: Context) -> None:
    if ctx.job.get("blocked"):
        J.set_blocked(ctx.job_id, None, ctx.persona)


def _post_node(ctx: Context, node: Node, outcome: NodeOutcome) -> NodeOutcome:
    """
    The other half of the tripwire: what the CALL crossed.

    Pre-node refuses to START a node past the limit. Nothing could refuse the
    node in flight — a call already issued cannot be aborted — so a job crosses
    its limit DURING a call, and this is where that is noticed.

    Without it the crossing surfaced at the next thing that happened to read
    spend, which was the Planner's `writer.apply(dry_run=True)` file check: the
    job-gate refused for budget, the planner read a job-gate refusal as a plan
    defect, and rung 3 FAILED the job terminally. `awaiting_approval` — the one
    state whose purpose is to let Mike raise the limit — was never reached, and
    a terminal job has nothing for cost.approve_limit() to release. With the
    $2.50 placeholder that was the likeliest way run 1's budget question got
    answered: by the job dying at the moment the number proved wrong.

    Parking here makes the module header's "overshoots by at most one node"
    literally true, which it was not.
    """
    if not node.is_agent or outcome.status != "done":
        return outcome
    try:
        cost.check_budget(ctx.job_id, ctx.persona)
    except cost.BudgetExceeded as exc:
        J.set_state(ctx.job_id, "awaiting_approval", detail=str(exc),
                    resume_to=ctx.job["state"], persona=ctx.persona)
        return NodeOutcome(node.name, "parked",
                           f"{exc} — the call crossed the limit; raise it on the VM "
                           f"with cost.approve_limit() and resume")
    except Exception:
        pass
    return outcome


# ---------------------------------------------------------------------------
# The model call, with rungs 0-3
# ---------------------------------------------------------------------------

def _ask(agent: str, prompt: str, ctx: Context, node_name: str) -> str:
    """One model call, billed to this job and nested under the tick's trace."""
    from core.orchestrator import _run_single_agent
    with cost.job_scope(ctx.job_id, ctx.persona, node=node_name):
        return _run_single_agent(agent, prompt, persona=ctx.persona)


def _climb(kind: str, agent: str, prompt: str, ctx: Context, node_name: str,
           inject: dict | None = None,
           **checks: Any) -> tuple[dict | None, list[str], list[str]]:
    """
    Rungs 0-3 for one artifact. Returns (artifact, defects, notes).

    Rung 2's retry prompt is the REJECTED ARTIFACT plus a machine-written defect
    list naming each failed constraint — not a re-ask. A model handed "try
    again" produces a different guess; a model handed its own output and the
    named constraint it broke produces a fix.

    `inject` carries the header fields only code can know — the job id and the
    upstream digests. They go in before validation, because every validator
    requires them and no model can produce them.
    """
    raw = _ask(agent, prompt, ctx, node_name)
    artifact, defects, notes = schemas.climb(kind, raw, inject=inject, **checks)
    if not defects:
        return artifact, defects, notes

    for _attempt in range(MAX_NODE_RETRIES):
        defect_list = "\n".join(f"- {d}" for d in defects)
        retry_prompt = (
            f"{prompt}\n\n"
            f"---\n\n"
            f"Your previous answer was REJECTED. It is reproduced below, followed "
            f"by every constraint it failed. Fix exactly those and change nothing "
            f"else.\n\n"
            f"## Your previous answer\n\n{raw}\n\n"
            f"## Constraints it failed\n\n{defect_list}\n"
        )
        raw = _ask(agent, retry_prompt, ctx, node_name)
        artifact, defects, more_notes = schemas.climb(kind, raw, inject=inject, **checks)
        notes.extend(more_notes)
        notes.append(f"rung 2: retried {node_name} against "
                     f"{len(defect_list.splitlines())} defect(s)")
        if not defects:
            break
    return artifact, defects, notes


def _reject(ctx: Context, node: Node, defects: list[str],
            after_retry: bool = True) -> NodeOutcome:
    """
    Rung 3. The defect list goes on the board, verbatim.

    `after_retry` is False on paths that never ran one — the Planner's
    dry-run file check rejects without a second model call, and saying
    "rejected after retry" there described a retry that had not happened,
    which is the board lying about what it cost.
    """
    how = "rejected after retry" if after_retry else "rejected"
    detail = f"{node.name} {how}: " + "; ".join(defects[:5])
    J.set_state(ctx.job_id, "failed", detail=detail[:500], persona=ctx.persona)
    return NodeOutcome(node.name, "failed", detail)


# ---------------------------------------------------------------------------
# The nodes
# ---------------------------------------------------------------------------

def _n1_manifest(ctx: Context) -> NodeOutcome:
    """N1. What data exists, as ids — never as values."""
    from core.build import manifest as M
    payload = M.build(ctx.persona)
    ctx.write("manifest", payload)
    J.set_state(ctx.job_id, "inquiry", detail="manifest built", persona=ctx.persona)
    return NodeOutcome("N1 manifest", "done",
                       f"{len(payload.get('sources') or [])} source(s)")


def _n1r_dossier(ctx: Context) -> NodeOutcome:
    """
    N1r. REPAIR only: what the capability did, and the questions it was built on.

    A failure is a gap in the question set, not a bug report — so the dossier is
    the ORIGINAL Question Set and Answer Ledger beside the traces of the fault.
    Without them Inquiry is diagnosing from the symptom, which is the thing this
    mode exists not to do.
    """
    cap = str(ctx.job.get("capability_hint") or "").strip()
    rows = [r for r in R.read_rows(ctx.persona) if r.get("capability") == cap]
    origin = rows[-1].get("job_id") if rows else ""
    dossier: dict[str, Any] = {
        "schema": "repair_dossier/1",
        "capability": cap,
        "origin_job": origin,
        "signature": str(ctx.job.get("gap") or "")[:200],
        "question_set": J.read_artifact(origin, "question_set", ctx.persona) if origin else None,
        "answer_ledger": J.read_artifact(origin, "answer_ledger", ctx.persona) if origin else None,
    }
    ctx.write("dossier", dossier)
    return NodeOutcome("N1r dossier", "done",
                       f"origin {origin or 'unknown'}"
                       + ("" if dossier["question_set"] else " (no original question set)"))


def _n2_inquiry(ctx: Context) -> NodeOutcome:
    """N2. The Question Set. The compass rule is enforced by the validator, not asked for."""
    from core.build import manifest as M
    manifest = ctx.artifact("manifest") or {}
    dossier = ctx.artifact("dossier")

    fingerprint = M.fingerprint(manifest)
    prompt = _inquiry_prompt(ctx, manifest, dossier)
    artifact, defects, notes = _climb(
        "question_set", AGENT_INQUIRY, prompt, ctx, "N2 inquiry",
        inject={"job_id": ctx.job_id,
                "manifest_fingerprint": fingerprint,
                "upstream_fingerprint": fingerprint,
                "generated_at": schemas.now_stamp()},
        manifest_ids=set(M.source_ids()) | {M.USER_SOURCE},
        known_capabilities=M.capability_names(),
    )
    if defects:
        return _reject(ctx, Node("N2 inquiry", "question_set", True, _n2_inquiry), defects)

    ctx.write("question_set", artifact)
    _index_questions(ctx, artifact)
    J.set_state(ctx.job_id, "questions_ready",
                detail=f"{len(artifact.get('spine') or [])} question(s), "
                       f"depth {artifact.get('depth')}",
                persona=ctx.persona)
    return NodeOutcome("N2 inquiry", "done",
                       f"{len(artifact.get('spine') or [])} question(s)"
                       + (f"; {len(notes)} repair note(s)" if notes else ""))


def _inquiry_prompt(ctx: Context, manifest: dict, dossier: dict | None) -> str:
    mode = str(ctx.job.get("mode") or "construct")
    parts = [
        f"MODE: {mode.upper()}",
        "",
        "## The request",
        "",
        str(ctx.job.get("gap") or ""),
        "",
        f"*Filed by:* {ctx.job.get('trigger') or 'unknown'}",
        "",
    ]
    if dossier:
        parts += [
            "## REPAIR — the capability that failed",
            "",
            f"`{dossier.get('capability')}` answered wrongly. Below is the Question "
            "Set it was built from and the ledger that compiled into its behaviour. "
            "Find the question that was not asked.",
            "",
            "```json",
            _compact(dossier.get("question_set")),
            "```",
            "",
        ]
    parts += [
        "## What the system can see",
        "",
        "Source ids you may name in `candidate_sources`. These are IDS, not values "
        "— nothing here tells you what the data says, and you must not guess.",
        "",
        "```json",
        _compact({"sources": [s.get("id") for s in manifest.get("sources") or []],
                  "capabilities": manifest.get("capabilities"),
                  "policies": [p.get("id") for p in manifest.get("policies") or []]}),
        "```",
        "",
    ]
    return "\n".join(parts)


def _compact(value: Any) -> str:
    import json
    try:
        return json.dumps(value, ensure_ascii=False, indent=2)[:12000]
    except Exception:
        return "{}"


def _index_questions(ctx: Context, question_set: dict) -> None:
    """
    Add this run's questions to Build's own index, never to search_memory.

    Best-effort: the index is a dedupe convenience and a missing FAISS or
    encoder must not fail a job. index.py already degrades to "not available".
    """
    try:
        from core.build import index
        if not index.available():
            return
        for question in question_set.get("spine") or []:
            if isinstance(question, dict) and question.get("text"):
                # KEYWORDS, because add_question's fourth positional is
                # `question_class`, not `persona`. Passed positionally, every
                # indexed question carried `class: "mike"` under the scheduler's
                # scope, and from the board — where nothing is bound — the
                # persona arrived as an empty class while the real persona
                # defaulted to None and the whole index write was logged as
                # "skipped: No persona resolved".
                index.add_question(str(question["text"]), ctx.job_id,
                                   question_id=str(question.get("id") or ""),
                                   question_class=str(question.get("class") or ""),
                                   persona=ctx.persona)
    except Exception as exc:
        logger.warning("[build] question indexing skipped: %s", exc)


def _n3_settle(ctx: Context) -> NodeOutcome:
    """
    N3. Probe, condense, settle — all code. THE NODE A SHALLOW VERSION OMITS.

    No model is asked whether the data exists. The model named a source; code
    chooses the call, runs it and counts the rows, so `data_available` is
    evidence rather than an impression of what tools exist.
    """
    question_set = ctx.artifact("question_set") or {}
    settled = S.settle(question_set, ctx.persona)
    ctx.write("evidence", settled)
    J.set_state(ctx.job_id, "librarian",
                detail=f"{settled['stats']['to_librarian']} to the Librarian, "
                       f"{settled['stats']['settled_by_policy']} by policy, "
                       f"{settled['stats']['settled_by_data']} by data",
                persona=ctx.persona)
    return NodeOutcome("N3 settle", "done", str(settled["stats"]))


def _n4_librarian(ctx: Context) -> NodeOutcome:
    """
    N4. The Librarian adjudicates the residue — and only the residue.

    Skipped entirely at `depth: triage` and whenever settle left nothing: a
    model call to adjudicate zero questions is the cost this whole node ordering
    exists to avoid.
    """
    question_set = ctx.artifact("question_set") or {}
    evidence = ctx.artifact("evidence") or {}
    residue = evidence.get("residue") or []

    if not residue:
        ctx.write("librarian", {"schema": "librarian_rows/1", "rows": [],
                                "skipped": "no residue — everything settled in code"})
        return NodeOutcome("N4 librarian", "skipped",
                           "nothing reached the Librarian")

    prompt = (
        "Adjudicate the questions below. For each, decide whether it is answerable "
        "from DATA or requires JUDGMENT, and where judgment is required give the "
        "decision, at least two options that were open, the assumption behind your "
        "choice, and what would tell you the assumption is wrong.\n\n"
        "The evidence beside each question is what the code actually retrieved. Do "
        "not assert a fact the evidence does not carry.\n\n"
        "## Questions\n\n```json\n"
        + _compact(residue) +
        "\n```\n\n## Evidence\n\n```json\n"
        + _compact([r for r in evidence.get("rows") or []
                    if r.get("question_id") in {q.get("id") for q in residue}]) +
        "\n```\n"
    )
    artifact, defects, notes = _climb(
        "answer_ledger", AGENT_LIBRARIAN, prompt, ctx, "N4 librarian",
        inject={"job_id": ctx.job_id,
                "upstream_fingerprint": schemas.artifact_fingerprint(question_set),
                "generated_at": schemas.now_stamp()},
        question_ids=[str(q.get("id")) for q in residue],
    )
    if defects:
        return _reject(ctx, Node("N4 librarian", "librarian", True, _n4_librarian), defects)
    ctx.write("librarian", artifact)
    return NodeOutcome("N4 librarian", "done",
                       f"{len(artifact.get('rows') or [])} row(s) adjudicated"
                       + (f"; {len(notes)} repair note(s)" if notes else ""))


def _n5_merge(ctx: Context) -> NodeOutcome:
    """
    N5. The full ledger: model rows merged back onto the code-written block.

    THE CODE BLOCK WINS, ALWAYS. schemas.strip_code_written() removes anything
    the model wrote into data_available / evidence / condensed_from / status and
    settle.merge_code_block() re-injects N3's. A model that decided its own
    evidence existed would have defeated the entire probe.
    """
    evidence = ctx.artifact("evidence") or {}
    librarian = ctx.artifact("librarian") or {}
    model_rows = {str(r.get("question_id")): r
                  for r in (librarian.get("rows") or []) if isinstance(r, dict)}

    rows = []
    for code_row in evidence.get("rows") or []:
        question_id = str(code_row.get("question_id") or "")
        merged = S.merge_code_block(model_rows.get(question_id, {}), code_row)
        # THE ID IS RE-ASSERTED FROM THE CODE ROW, AND IT HAS TO BE.
        # merge_code_block() starts from the MODEL's row and overlays only
        # CODE_WRITTEN_LEDGER_FIELDS, which are data_available, evidence,
        # condensed_from and status — `question_id` is in neither set. So a row
        # the Librarian never saw (settled in code, or routed to the interview)
        # merged to an ANONYMOUS row: no id, one row per question broken, and
        # answer_interview() unable to find the row to attach an answer to.
        # Every REPAIR that claims to point at "the question that wasn't asked"
        # rests on this id surviving the merge.
        merged["question_id"] = question_id
        rows.append(merged)

    ledger = {
        "schema": schemas.SCHEMA_VERSIONS["answer_ledger"],
        "job_id": ctx.job_id,
        "generated_at": schemas.now_stamp(),
        # The question set this ledger answers. Written here rather than copied
        # from the Librarian's artifact: the ledger is derived from the FULL
        # spine, not only the residue the Librarian saw.
        "upstream_fingerprint": schemas.artifact_fingerprint(ctx.artifact("question_set") or {}),
        "rows": rows,
        "interview_items": (evidence.get("interview_items") or [])
        + [i for i in (librarian.get("interview_items") or []) if isinstance(i, dict)],
        "variable_proposals": librarian.get("variable_proposals") or [],
        "surface_map": librarian.get("surface_map") or [],
    }
    ctx.write("answer_ledger", ledger)

    if ledger["interview_items"]:
        J.set_state(ctx.job_id, "needs_interview",
                    detail=f"{len(ledger['interview_items'])} item(s) only the user "
                           f"can answer",
                    persona=ctx.persona)
        return NodeOutcome("N5 merge", "gate",
                           f"{len(ledger['interview_items'])} interview item(s)")

    J.set_state(ctx.job_id, "planning", detail=f"{len(rows)} ledger row(s)",
                persona=ctx.persona)
    return NodeOutcome("N5 merge", "done", f"{len(rows)} row(s)")


def _n7_planner(ctx: Context) -> NodeOutcome:
    """
    N7. The Build Plan. Its file-path check is writer.apply(dry_run=True) — the
    enforcer itself, never a copy of its rules, which is the only way the
    validator and the enforcer cannot drift.
    """
    ledger = ctx.artifact("answer_ledger") or {}
    question_set = ctx.artifact("question_set") or {}

    prompt = (
        "Write the Build Plan for this capability. The ledger below is its "
        "specification: each decision becomes a gate with its branches already "
        "enumerated, each data_home becomes a resolved binding, and the surface map "
        "says which operations it implements and which it refuses cleanly.\n\n"
        f"Disposition is `{question_set.get('disposition')}` and the evidence for it "
        "is in the question set. Do not re-open it.\n\n"
        "## Answer Ledger\n\n```json\n" + _compact(ledger) + "\n```\n"
    )
    artifact, defects, notes = _climb(
        "build_plan", AGENT_PLANNER, prompt, ctx, "N7 planner",
        inject={"job_id": ctx.job_id,
                "upstream_fingerprint": schemas.artifact_fingerprint(ledger),
                "generated_at": schemas.now_stamp()},
    )
    if defects:
        return _reject(ctx, Node("N7 planner", "build_plan", True, _n7_planner), defects)

    # The planner's own file-path check, run against the real enforcer.
    edits = _edits_from(artifact, ctx)
    if edits:
        verdict = writer.apply(ctx.job_id, artifact, edits, dry_run=True,
                               persona=ctx.persona)
        artifact["_dry_run"] = verdict
        if verdict.startswith("REFUSED"):
            return _reject(ctx, Node("N7 planner", "build_plan", True, _n7_planner),
                           [f"the writer refuses this plan's files: {verdict}"],
                           after_retry=False)

    ctx.write("build_plan", artifact)
    J.set_state(ctx.job_id, "plan_ready",
                detail=f"{artifact.get('capability', {}).get('kind')} "
                       f"{artifact.get('capability', {}).get('id')}",
                persona=ctx.persona)
    return NodeOutcome("N7 planner", "done",
                       str(artifact.get("capability", {}).get("id"))
                       + (f"; {len(notes)} repair note(s)" if notes else ""))


def _edits_from(plan: dict, ctx: Context) -> list[dict]:
    """
    The plan's `files[]` as writer edits. Content may be empty at dry-run time —
    the path rules are what is being checked, and a path is refused or allowed
    regardless of what would land in it.
    """
    out = []
    for entry in plan.get("files") or []:
        if isinstance(entry, dict) and entry.get("path"):
            out.append({"path": str(entry["path"]),
                        "content": str(entry.get("content") or "")})
        elif isinstance(entry, str) and entry.strip():
            out.append({"path": entry.strip(), "content": ""})
    return out


def _n8_cost(ctx: Context) -> NodeOutcome:
    """
    N8. The estimate, in code. Priced through spend_guard.estimate_usd() — the
    same function the global guard uses, so the two meters cannot disagree about
    what a token costs.
    """
    spent = cost.job_spend(ctx.job_id, ctx.persona)
    limit = cost.job_limit(ctx.job_id, ctx.persona)
    # What remains: N8b's advisory pass and, after approval, no further model
    # calls at all — N10, N12 and N14 are code. So the forward estimate is one
    # agent call priced at this job's own observed average rather than a guess.
    rows = cost.spend_rows(ctx.job_id, ctx.persona)
    per_call = (spent / len(rows)) if rows else 0.0
    estimate = {
        "schema": "build_estimate/1",
        "job_id": ctx.job_id,
        "usd": round(per_call, 6),
        "spent": round(spent, 6),
        "limit": limit,
        "limit_source": cost.limit_source(ctx.job_id, ctx.persona),
        "notice": cost.budget_notice(ctx.job_id, ctx.persona),
        "calls_so_far": len(rows),
        "dispatches_expected_per_day": _expected_dispatches(ctx),
    }
    ctx.write("estimate", estimate)

    if cost.would_exceed(ctx.job_id, estimate["usd"], ctx.persona):
        J.set_state(ctx.job_id, "awaiting_approval",
                    detail=(f"estimate ${estimate['usd']:.4f} on top of "
                            f"${spent:.4f} exceeds the ${limit:.2f} limit"),
                    resume_to="planning", persona=ctx.persona)
        return NodeOutcome("N8 cost", "parked",
                           f"over the ${limit:.2f} limit — approve with "
                           f"cost.approve_limit() on the VM")
    return NodeOutcome("N8 cost", "done",
                       f"${spent:.4f} spent against ${limit:.2f}")


def _expected_dispatches(ctx: Context) -> float | None:
    """
    How often the TRIGGER fired, per day, in the traces that filed this gap —
    and None until something can actually answer that.

    NOT THE COORDINATOR'S TURNS PER DAY. The first version returned
    `counts["coordinator"] / days` as a proxy, which is wrong twice over: it is
    the same figure for every capability regardless of what filed it, so it
    measures how much Mike talks rather than how often this gap arrives; and on
    a persona whose only trace file is the tick's own it computes 0.0 — the
    exact "it never fires" verdict this docstring says must never be inferred
    from an inability to count.

    Phase 4 has no trigger signature to count. A gap arrives as free text from
    `request_build` or as a machine-log signature from the REPAIR scan, and
    neither is matched against the traces that produced it. So the honest value
    is None, the run line says "not counted", and the figure is owed to whatever
    phase gives a trigger an identity. **None is not a gap in the meter — the
    ACTUAL count is measured from day one and is the number that matters.**
    """
    return None


def _n8b_review(ctx: Context) -> NodeOutcome:
    """
    N8b. An advisory read of the drafted plan. NEVER BLOCKING.

    A model judging its own output is the grade-your-own-homework pattern, and
    the enforcement is the constitution gate, the writer's path rules and
    verify. This exists to put a second reading in the brief, not to decide
    anything — so a failure here is recorded and walked past.
    """
    plan = ctx.artifact("build_plan") or {}
    try:
        text = _ask(AGENT_REVIEW,
                    "Read this Build Plan as a reviewer, not its author. Name what it "
                    "gets wrong, what it assumes without evidence, and what it will be "
                    "asked to do that it does not implement. Be brief and concrete. "
                    "You are advisory — nothing you say blocks this plan.\n\n"
                    "```json\n" + _compact(plan) + "\n```\n",
                    ctx, "N8b review")
    except Exception as exc:
        text = f"(advisory review unavailable: {type(exc).__name__}: {exc})"
    ctx.write("review", {"schema": "build_review/1", "advisory": True,
                         "text": str(text)[:8000]})
    return NodeOutcome("N8b review", "done", "advisory")


def _n10_brief(ctx: Context) -> NodeOutcome:
    """
    N10. The approval brief, plus one needs_tool brief per missing tool.

    The state moves to `briefed` BEFORE the write, because `briefed` is one of
    the writer's two writable states and the brief lands through the writer like
    everything else. A brief written past the writer would be the same hole the
    undo journal was: a write primitive inside an allow-root with no path rules.
    """
    J.set_state(ctx.job_id, "briefed", detail="brief written", persona=ctx.persona)
    report = _write_brief(ctx)
    # THE ARTIFACT IS WHAT STOPS N10 RE-RUNNING AFTER APPROVAL, and without it
    # this node was an infinite gate: approve() sets `executing`, the next tick
    # walks the graph from the top, N10 has no artifact so it is never skipped,
    # it runs again and sets the state back to `briefed` — so N12 is never
    # reached and the approval is silently undone every thirty minutes. Every
    # node that changes state needs something on disk saying it ran.
    ctx.write("brief", {
        "schema": "build_brief/1",
        "lines": report.get("lines", 0),
        "needs_tool": report.get("needs_tool") or [],
        "leaked": report.get("leaked") or [],
        "result": report.get("result", ""),
    })
    if report.get("leaked"):
        # A brief that needed masking is a defect in the renderer above the
        # redactor, so it goes on the board rather than being swallowed by a
        # document that now looks clean.
        J.set_blocked(ctx.job_id,
                      f"brief redaction masked {len(report['leaked'])} persona value(s) "
                      f"— the renderer emitted content it should not have",
                      ctx.persona)
    return NodeOutcome("N10 brief", "gate",
                       f"{report.get('lines', 0)} lines"
                       + (f", {len(report['needs_tool'])} needs_tool brief(s)"
                          if report.get("needs_tool") else "")
                       + " — awaiting approval at [N9]")


def _write_brief(ctx: Context, as_state: str = "") -> dict:
    """
    Render and land the brief.

    `as_state` is the state the job is ENTERING. Every write here necessarily
    precedes the state change — writer.WRITABLE_STATES is {briefed, executing},
    so a brief written after the move to `verifying` or `landed` is refused —
    and without it the landed document recorded `executing`, the state it was
    written from, and so never said `landed`.
    """
    return BR.write_briefs(
        ctx.job_id, J.get(ctx.job_id, ctx.persona) or ctx.job,
        ctx.artifact("question_set") or {}, ctx.artifact("answer_ledger") or {},
        ctx.artifact("build_plan") or {}, ctx.artifact("estimate"),
        (ctx.artifact("verification") or {}).get("summary", ""), ctx.persona,
        as_state=as_state,
    )


# THERE IS NO PARTIAL BRIEF, AND THERE CANNOT BE ONE. An earlier version called
# _write_brief() after parking a job at `needs_interview` or
# `awaiting_approval`, so Mike would have a document explaining the park. It
# never once succeeded: writer.WRITABLE_STATES is {briefed, executing}, every
# call site sets the parked state FIRST, and _write_brief does not raise — so
# the write was refused, logged at info, and the function read as working.
#
# Removed rather than fixed, because the two candidate fixes are both worse.
# Widening WRITABLE_STATES changes the writer, which is the security choke
# point, for a convenience. Writing the brief before the state moves would put
# a document on disk claiming a state the job is not in yet.
#
# What actually carries a parked job's reason: tools/build.py's context_block
# (which now names the open interview QUESTIONS, not just the job) and
# `build_board.py --show`, both of which read the ledger live and cannot go
# stale the way a written document would.


def _n12_apply_verify(ctx: Context) -> NodeOutcome:
    """
    N12. Land it, then run every check over the tracked tree AND the overlay.

    A FAILING CHECK REVERTS BEFORE THE NODE RETURNS. Nothing is ever left
    half-applied — that is the property the whole landing design rests on, and
    it is why the revert happens here rather than being left for someone to
    tidy.

    The revert summary is read by its SKIPPED clause, never by its `reverted —`
    prefix: revert() opens with that prefix even when every entry was skipped
    for failing the path rules (recorded in the plan's section 6 v3.3 corrections
    precisely so this caller keys on the right thing).
    """
    plan = ctx.artifact("build_plan") or {}
    edits = _edits_from(plan, ctx)
    if not edits:
        J.set_state(ctx.job_id, "failed",
                    detail="the plan declares no files, so there is nothing to land",
                    persona=ctx.persona)
        return NodeOutcome("N12 apply+verify", "failed", "no files in the plan")

    applied = writer.apply(ctx.job_id, plan, edits, persona=ctx.persona)
    # SUCCESS IS CHECKED FOR, NOT INFERRED FROM THE ABSENCE OF KNOWN FAILURES.
    # apply() returns "OK — …" when it wrote, and everything else is some kind
    # of not-writing. Matching the two failure prefixes instead let a THIRD
    # shape through: the exception path returns "{job_id}: writer failed and
    # reverted — disk full", which starts with neither, so N12 ran the full
    # 18-check sweep against an overlay that was never applied and put
    # "capability-tests FAILED" on the board while the real reason — the writer
    # crashed — was nowhere. A whitelist of one success string cannot be
    # outgrown by a new failure mode.
    if not applied.startswith("OK —"):
        if applied.startswith("PARKED"):
            # `executing` and not `planning`: N12 is the node that parked, and
            # it is the node that must run again once the ceiling is raised.
            J.set_state(ctx.job_id, "awaiting_approval", detail=applied[:300],
                        resume_to="executing", persona=ctx.persona)
            return NodeOutcome("N12 apply+verify", "parked", applied)
        # Everything else — a REFUSED, a writer crash, anything a later version
        # of apply() might return — is a failure, and the string is carried
        # verbatim so the board says what actually happened.
        _write_brief(ctx, as_state="failed")   # while still `executing`
        J.set_state(ctx.job_id, "failed", detail=applied[:500], persona=ctx.persona)
        return NodeOutcome("N12 apply+verify", "failed", applied)

    tests = [str(t) for t in (plan.get("tests") or []) if str(t).strip()]
    report = _verify(ctx, tests)
    ctx.write("verification", {
        "schema": "build_verification/1",
        "ok": report.ok,
        "summary": report.summary(),
        "checks": [{"name": r.name, "ok": r.ok} for r in report.results],
        "failures": [{"name": r.name, "output": r.output[-4000:]}
                     for r in report.failures],
    })

    if not report.ok:
        undone = writer.revert(ctx.job_id, ctx.persona)
        detail = f"{report.summary()} | revert: {undone}"
        if "SKIPPED" in undone:
            # The one case where a failed check leaves something behind: revert
            # refused an entry for failing the path rules. Louder than the check
            # failure itself, because the overlay is now in an unknown state.
            J.set_blocked(ctx.job_id,
                          "revert SKIPPED entries — the overlay may be half-applied "
                          "and needs a human look", ctx.persona)
        _emit_check_failed(ctx, report)
        # AFTER the revert, which deletes brief.md along with everything else
        # this job wrote, and BEFORE the state leaves `executing`. Both halves
        # matter: the brief is the document carrying the failing check output
        # into the next attempt, and losing it is losing the reason.
        _write_brief(ctx, as_state="failed")
        J.set_state(ctx.job_id, "failed", detail=detail[:500], persona=ctx.persona)
        return NodeOutcome("N12 apply+verify", "failed", detail)

    # BEFORE the state leaves `executing`. writer.WRITABLE_STATES is
    # {briefed, executing}, so a brief written after the move to `verifying`
    # was REFUSED — silently, because _write_brief does not raise — and the
    # landed brief went on saying `State: briefed` with no Verification
    # section, which is the one thing [N13] is supposed to read.
    _write_brief(ctx, as_state="verifying")
    J.set_state(ctx.job_id, "verifying",
                detail=f"live in the overlay; {report.summary()}", persona=ctx.persona)
    return NodeOutcome("N12 apply+verify", "gate",
                       f"{report.summary()} — awaiting acceptance at [N13]")


def _verify(ctx: Context, tests: list[str]):
    from core.build import verify
    return verify.run_all(overlay=writer.overlay_dir(ctx.persona),
                          capability_tests=tests)


def _emit_check_failed(ctx: Context, report) -> None:
    """BUILD_CHECK_FAILED, carrying the failing check name for the board."""
    try:
        from core.persona import persona_scope, resolve_persona
        from tools.logger import write_quality_event
        names = ", ".join(r.name for r in report.failures) or "unknown"
        with persona_scope(resolve_persona(ctx.persona)):
            write_quality_event(
                event_type="BUILD_CHECK_FAILED", source_agent="build",
                detail=f"{ctx.job_id} reverted — {names} failed during landing",
            )
    except Exception as exc:
        logger.warning("[build] could not emit BUILD_CHECK_FAILED: %s", exc)


def _n14_close(ctx: Context) -> NodeOutcome:
    """N14. Register what landed, with its run line, and close the job."""
    plan = ctx.artifact("build_plan") or {}
    estimate = ctx.artifact("estimate") or {}
    files = [e["path"] for e in _edits_from(plan, ctx)]
    row = R.record_landing(ctx.job_id, plan, files, ctx.persona,
                           estimate.get("dispatches_expected_per_day"))
    # Before `landed`, for the same reason as N12: `landed` is terminal and not
    # writable, so a brief written after it was refused and the final document
    # never recorded that the capability had landed.
    _write_brief(ctx, as_state="landed")
    J.set_state(ctx.job_id, "landed",
                detail=f"{row['capability']} v{row['version']}", persona=ctx.persona)
    return NodeOutcome("N14 close", "done",
                       f"{row['capability']} v{row['version']} registered")


# ---------------------------------------------------------------------------
# The graph
# ---------------------------------------------------------------------------

NODES: tuple[Node, ...] = (
    Node("N1r dossier", "dossier", False, _n1r_dossier),
    Node("N1 manifest", "manifest", False, _n1_manifest),
    Node("N2 inquiry", "question_set", True, _n2_inquiry),
    Node("N3 settle", "evidence", False, _n3_settle),
    Node("N4 librarian", "librarian", True, _n4_librarian),
    Node("N5 merge", "answer_ledger", False, _n5_merge),
    Node("N7 planner", "build_plan", True, _n7_planner),
    Node("N8 cost", "estimate", False, _n8_cost),
    Node("N8b review", "review", True, _n8b_review),
    Node("N10 brief", "brief", False, _n10_brief),
    Node("N12 apply+verify", "verification", False, _n12_apply_verify),
    Node("N14 close", None, False, _n14_close),
)

_BY_NAME = {node.name: node for node in NODES}

# Nodes that only exist in one mode. N1r is the REPAIR dossier; running it on a
# CONSTRUCT job would write an empty artifact and make the resume cursor lie
# about which node had run.
_MODE_ONLY: dict[str, str] = {"N1r dossier": "repair"}

# Nodes past a human gate: the tick reaches them only once a board command has
# moved the job into the state named here. N12 runs on the next tick after
# approve() sets `executing`.
_AFTER_GATE: dict[str, str] = {
    "N12 apply+verify": "executing",
}

# N14 is never run by advance() at all — accept() calls it directly, because it
# IS the acceptance. Named explicitly rather than given an unreachable state in
# _AFTER_GATE, which is what the first version did: a state string that appears
# in no STATES tuple reads like a typo and is impossible to verify.
_HUMAN_CALLED_ONLY: frozenset[str] = frozenset({"N14 close"})


# ---------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------

def run_node(job_id: str, node_name: str, persona: str | None = None) -> NodeOutcome:
    """
    One node, with every pre-node gate. The unit a test drives.

    Idempotent by construction: a node whose artifact is already present and
    parseable returns `skipped` WITHOUT calling a model. That is what makes a
    kill -9 cost at most one node.
    """
    node = _BY_NAME.get(node_name)
    if node is None:
        raise RunnerError(f"No such node: {node_name!r}")
    job = J.get(job_id, persona)
    if job is None:
        raise RunnerError(f"No such job: {job_id}")
    ctx = Context(job_id, persona, job)

    if node.artifact and ctx.artifact(node.artifact) is not None:
        return NodeOutcome(node.name, "skipped", "artifact already present")

    required_mode = _MODE_ONLY.get(node.name)
    if required_mode and job.get("mode") != required_mode:
        return NodeOutcome(node.name, "skipped", f"{required_mode}-only node")

    blocked = _pre_node(ctx, node)
    if blocked is not None:
        return blocked
    _clear_blocked(ctx)

    J.heartbeat(job_id, node=node.name, persona=persona)
    try:
        return _post_node(ctx, node, node.run(ctx))
    except Exception as exc:
        logger.warning("[build] %s raised in %s: %s", job_id, node.name, exc)
        J.set_state(job_id, "failed",
                    detail=f"{node.name} raised {type(exc).__name__}: {exc}",
                    persona=persona)
        return NodeOutcome(node.name, "failed", f"{type(exc).__name__}: {exc}")


def advance(job_id: str, persona: str | None = None) -> list[NodeOutcome]:
    """
    Walk one job as far as it will go. Stops at a gate, a park or a failure.

    Runs Inquiry -> probe -> Librarian -> Planner in ONE pass as one request,
    which is what makes a tick's whole cost `(nodes run) x (per-node cost)` with
    no idle burn and no standing charge.
    """
    outcomes: list[NodeOutcome] = []
    for node in NODES:
        job = J.get(job_id, persona)
        if job is None:
            break
        state = job["state"]
        if state in J.TERMINAL:
            break
        if node.name in _HUMAN_CALLED_ONLY:
            break
        if state in GATE_STATES and node.name not in _AFTER_GATE:
            outcomes.append(NodeOutcome(node.name, "gate", f"parked at {state}"))
            break
        if node.name in _AFTER_GATE and state != _AFTER_GATE[node.name]:
            break
        outcome = run_node(job_id, node.name, persona)
        outcomes.append(outcome)
        if outcome.stop:
            break
    return outcomes


def tick(persona: str | None = None) -> str:
    """
    One `build_tick`. THE SCHEDULER'S ENTRY POINT.

    With an empty queue this returns at ZERO TOKENS and milliseconds of CPU: it
    replays the ledger, finds nothing runnable, and stops. A function job that
    costs nothing on a quiet day is what makes a 30-minute cadence affordable at
    all.

    Returns a plain string. Deliberately never a `{"notify": ...}` dict —
    nothing in Build reaches the user unreviewed, and a tick that could notify
    would be the first thing to do so.
    """
    try:
        return _tick(persona)
    except Exception as exc:                        # pragma: no cover
        logger.warning("[build] tick failed: %s", exc)
        return f"build_tick: failed — {type(exc).__name__}: {exc}"


# A recurring fault stops being noise and starts being evidence at three: one is
# an accident, two is a coincidence. The same bar sync_dev_backlog.py's
# ESCALATE_AT uses, and deliberately the same number — a capability failing three
# times and a machine signature recurring three times are the same judgement.
REPAIR_AT = 3

# How far back the REPAIR scan reads quality events. Long enough that three
# occurrences of a real fault can accumulate, short enough that a fault fixed a
# month ago cannot file a ticket about itself today.
REPAIR_WINDOW_DAYS = 14


def _repair_scan(persona: str | None) -> list[str]:
    """
    File a REPAIR ticket for any BUILT capability whose fault has recurred x3.

    NO MODEL DECIDES THIS — IT IS COUNTING. Corrections are attributed in code to
    the specialists that ran on the previous turn (core/orchestrator's
    _corrected_agents), signatures come from sync_dev_backlog.signature() so one
    recurring fault collapses to one key, and a capability in the Build registry
    is the only thing that can be repaired. Everything here is comparison.

    The signature function is IMPORTED from the sync script rather than
    reimplemented: two definitions of "is this the same fault" would disagree the
    first time either was improved, and the disagreement would be invisible —
    one side would simply stop reaching three.
    """
    import json
    from collections import Counter
    from datetime import datetime, timedelta

    try:
        signature = _signature_fn()
    except Exception as exc:
        logger.warning("[build] REPAIR scan unavailable: %s", exc)
        return []

    built = set(R.capabilities(persona))
    if not built:
        return []

    # Through jobs.persona_data_dir rather than a fresh import of core.persona:
    # every path in this package resolves through that one name, so the package
    # has ONE place a persona tree is decided. A second import here would have
    # been a second resolution path that agrees until one of them is redirected.
    events_path = J.persona_data_dir(persona) / "logs" / "quality_events.json"
    if not events_path.exists():
        return []

    cutoff = (datetime.utcnow() - timedelta(days=REPAIR_WINDOW_DAYS)).isoformat()
    counts: Counter = Counter()
    examples: dict[str, dict] = {}
    try:
        text = events_path.read_text(encoding="utf-8")
    except OSError:
        return []

    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if str(event.get("timestamp") or "") < cutoff:
            continue
        # source_agent may name several specialists — the correction attribution
        # writes a comma-joined list, because a turn can dispatch more than one
        # and blaming the first alphabetically would be a guess.
        agents = {a.strip() for a in str(event.get("source_agent") or "").split(",")}
        for capability in agents & built:
            key = f"{capability}|{signature(event)}"
            counts[key] += 1
            examples.setdefault(key, event)

    filed: list[str] = []
    for key, count in counts.items():
        if count < REPAIR_AT:
            continue
        capability, signature = key.split("|", 1)
        try:
            row = J.create(
                # THE COUNT IS NOT IN THE GAP, and that is the whole point.
                # `create()` fingerprints mode|gap|capability_hint, so a gap
                # reading "…3 times…" hashed differently from the same fault at
                # 4 — every correction after the third minted a NEW fingerprint,
                # escaped the dedupe and filed another ticket, and nine more
                # would fill max_proposed with one recurring fault. The gap is
                # now the fault; the count is evidence and lives in `trigger`,
                # which is not fingerprinted.
                gap=(f"`{capability}` keeps answering wrongly on the same fault: "
                     f"{examples[key].get('detail', '')}"),
                trigger=(f"build_tick REPAIR scan — {signature} seen x{count} "
                         f"in {REPAIR_WINDOW_DAYS}d"),
                mode="repair", capability_hint=capability, persona=persona,
            )
            filed.append(f"{row['job_id']} (REPAIR {capability} x{count})")
        except J.JobError:
            # Already filed, or the caps are full. Both are correct refusals and
            # neither is worth a line on the board every thirty minutes.
            continue
    return filed


def _signature_fn():
    """
    sync_dev_backlog.signature(), imported. scripts/ is not a package, so the
    path is added here rather than at module import — the runner must load on a
    machine where the scripts directory is absent.
    """
    import sys
    from pathlib import Path
    scripts = Path(__file__).resolve().parent.parent.parent / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from sync_dev_backlog import signature
    return signature


def _tick(persona: str | None) -> str:
    repaired = _repair_scan(persona)
    states = J.states(persona)
    runnable = {job_id: job for job_id, job in states.items()
                if job["state"] not in J.TERMINAL and job["state"] not in GATE_STATES}

    # Re-enter anything that stalled. A heartbeat older than STALE_MINUTES means
    # the process that held it is gone; the artifacts on disk are the cursor, so
    # attempt + 1 re-enters at the node that had not written.
    #
    # ONLY RUNNABLE JOBS. A job at a gate has a quiet heartbeat because it is
    # WAITING FOR A HUMAN, not because anything died — and a gate is exactly
    # where a job sits for days. Bumping its attempt every thirty minutes would
    # exhaust MAX_ATTEMPTS in under two hours and fail a job whose only offence
    # was that nobody had read the brief yet.
    stale = J.stale_jobs(persona)
    revived: list[str] = []
    for job_id in sorted(set(runnable) & set(stale)):
        try:
            J.next_attempt(job_id, persona)
            revived.append(job_id)
            runnable[job_id] = J.get(job_id, persona)
        except J.JobError as exc:
            J.set_state(job_id, "failed", detail=str(exc), persona=persona)
            runnable.pop(job_id, None)

    if not runnable:
        gated = sum(1 for job in states.values() if job["state"] in GATE_STATES)
        filed = f"; filed {', '.join(repaired)}" if repaired else ""
        return (f"build_tick: nothing runnable "
                f"({len(states)} job(s), {gated} at a gate){filed}")

    notice = cost.budget_notice(persona=persona)
    lines: list[str] = []
    if notice:
        lines.append(notice)
    if repaired:
        lines.append(f"REPAIR filed: {', '.join(repaired)}")
    if revived:
        lines.append(f"re-entered after a stall: {', '.join(revived)}")

    with _tick_trace(persona, runnable) as root:
        for job_id in sorted(runnable):
            outcomes = advance(job_id, persona)
            summary = "; ".join(f"{o.node} {o.status}" for o in outcomes) or "no node ran"
            lines.append(f"{job_id}: {summary}")
        root["summary"] = " | ".join(lines)

    return "build_tick: " + (" | ".join(lines) if lines else "nothing to do")


# ---------------------------------------------------------------------------
# Tracing
# ---------------------------------------------------------------------------

class _tick_trace:
    """
    One RequestTrace per tick, with the Build agents NESTED under a root record.

    core/trace.py nests a record under `pipeline[0]` when `_SUBAGENT_DEPTH > 0`
    and in no other way, so a root record plus the env var is what makes The
    Book render Inquiry, Librarian and Planner as one request rather than three
    unrelated top-level entries.

    `_SUBAGENT_DEPTH` is a PROCESS env var, not thread-local. Setting it here
    mirrors what tools/subagent.py already does on the server path, and it is
    safe because build_tick runs inside the scheduler process, which serves no
    user turns. **If Build ever runs inside core/server.py, this is the line
    that breaks it** — a concurrent user request would have its Coordinator
    nested under whatever the tick had pushed.
    """

    _DEPTH = "_SUBAGENT_DEPTH"

    def __init__(self, persona: str | None, runnable: dict):
        self.persona = persona
        self.runnable = runnable
        self.previous: str | None = None
        self.record = None
        self.trace = None
        self.summary: dict = {"summary": ""}

    def __enter__(self) -> dict:
        try:
            from core import trace as T
            self.trace = T.start_request_trace(
                f"build_tick: {len(self.runnable)} job(s)", self.persona,
                is_proactive=True)
            self.record = T.push_agent(TRACE_ROOT_AGENT, "", "")
            self.previous = os.environ.get(self._DEPTH)
            os.environ[self._DEPTH] = "1"
        except Exception as exc:                    # pragma: no cover
            logger.warning("[build] tick tracing unavailable: %s", exc)
        return self.summary

    def __exit__(self, *exc: Any) -> None:
        try:
            from core import trace as T
            if self.previous is None:
                os.environ.pop(self._DEPTH, None)
            else:
                os.environ[self._DEPTH] = self.previous
            if self.record is not None:
                T.pop_agent(self.record)
            if self.trace is not None:
                T.finish_request_trace(self.summary.get("summary", ""))
        except Exception as exc:                    # pragma: no cover
            logger.warning("[build] tick trace close failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# The human gates — board commands, run on the VM
# ---------------------------------------------------------------------------

def queue(job_id: str, persona: str | None = None) -> str:
    """`proposed` -> `queued`. Mike's triage. Nothing else moves a job off proposed."""
    job = J.get(job_id, persona)
    if job is None:
        return f"{job_id}: no such job"
    if job["state"] != "proposed":
        return f"{job_id}: already {job['state']}, not proposed"
    try:
        J.set_state(job_id, "queued", detail="triaged", persona=persona)
    except J.JobError as exc:
        return f"{job_id}: {exc}"
    return f"{job_id}: queued"


def approve(job_id: str, persona: str | None = None) -> str:
    """
    [N9]. `briefed` -> `executing`. The next tick runs N12.

    This is approval to LAND, not approval to spend — an over-budget job parks
    at `awaiting_approval` and is released by cost.approve_limit() followed by
    resume(), which are deliberately two different acts.
    """
    job = J.get(job_id, persona)
    if job is None:
        return f"{job_id}: no such job"
    if job["state"] != "briefed":
        return f"{job_id}: at {job['state']} — [N9] approves a job at `briefed`"
    J.set_state(job_id, "executing", detail="approved at [N9]", persona=persona)
    return f"{job_id}: approved — the next tick lands it and runs the checks"


def accept(job_id: str, persona: str | None = None) -> str:
    """[N13]. `verifying` -> N14 -> `landed`. Accepting something already live."""
    job = J.get(job_id, persona)
    if job is None:
        return f"{job_id}: no such job"
    if job["state"] != "verifying":
        return f"{job_id}: at {job['state']} — [N13] accepts a job at `verifying`"
    J.set_state(job_id, "executing", detail="accepted at [N13]", persona=persona)
    # `executing` is what _AFTER_GATE admits N14 from; set it, then close.
    outcome = run_node(job_id, "N14 close", persona)
    return f"{job_id}: {outcome.status} — {outcome.detail}"


# The only states a refusal means anything from — both are gates where Mike is
# being asked. Anywhere else, "refuse" is a destructive verb with no question
# behind it.
REFUSABLE_STATES: frozenset[str] = frozenset({"briefed", "verifying"})


def refuse(job_id: str, persona: str | None = None) -> str:
    """
    [N13] refused. Reverts everything and abandons the job.

    A refusal is a revert, the same call a failing check makes: the capability
    is already live in the overlay by the time anyone is asked, so "no" has to
    undo something rather than merely decline it.

    STATE-GUARDED, and this is the guard the first version did not have.
    `approve()` and `accept()` both checked their state; `refuse()` reverted
    ANY job, including a `landed` one — so `build_board.py --refuse` with a
    mistyped id deleted a live capability's overlay files while the registry
    went on saying `landed`, leaving an orphan the coherence pass would report
    and no way back: the generated files were new, so the undo journal holds no
    `bytes_before` to restore. The one irreversible board command was the one
    without a guard on it.
    """
    job = J.get(job_id, persona)
    if job is None:
        return f"{job_id}: no such job"
    if job["state"] in J.TERMINAL:
        return (f"{job_id}: is {job['state']} — a terminal job cannot be refused. "
                f"If a LANDED capability should go, that is a retirement, not a "
                f"refusal: nothing here reverts something the registry still "
                f"calls live.")
    if job["state"] not in REFUSABLE_STATES:
        return (f"{job_id}: at {job['state']} — refusing is for a job waiting on "
                f"you at {sorted(REFUSABLE_STATES)}. This one is mid-pipeline; "
                f"nothing has been applied, so there is nothing to refuse.")
    undone = writer.revert(job_id, persona)
    J.set_state(job_id, "abandoned", detail=f"refused at [N13]; {undone}"[:500],
                persona=persona)
    if "SKIPPED" in undone:
        return (f"{job_id}: abandoned, but the revert SKIPPED entries that failed "
                f"the path rules — the overlay needs a look. {undone}")
    return f"{job_id}: abandoned — {undone}"


def resume(job_id: str, persona: str | None = None) -> str:
    """
    Release a job parked at `awaiting_approval`, after the limit was raised or
    the ceiling changed.

    Refuses while the job is still over its limit, so a resume cannot silently
    become the approval it was supposed to follow.
    """
    job = J.get(job_id, persona)
    if job is None:
        return f"{job_id}: no such job"
    if job["state"] != "awaiting_approval":
        return f"{job_id}: at {job['state']}, not awaiting_approval"
    try:
        cost.check_budget(job_id, persona)
    except cost.BudgetExceeded as exc:
        return (f"{job_id}: still over budget — {exc}. Raise it ON THE VM with "
                f"`python3 -c \"from core.build import cost; "
                f"cost.approve_limit('{job_id}', <usd>)\"` (bind the persona first: "
                f"`export METATRON_PERSONA=mike`), then resume again.")
    # BACK TO WHERE IT WAS PARKED FROM, not to a fixed state. `planning` was
    # right only for a budget park before the Planner ran; a job parked at N12
    # for the autonomy ceiling came back to `planning`, found every artifact
    # present, skipped every node and stalled with no command able to move it.
    target = job.get("resume_to") or "planning"
    J.set_state(job_id, target, detail=f"resumed after approval (to {target})",
                persona=persona)
    return f"{job_id}: resumed at {target}"


def answer_interview(job_id: str, question_id: str, answer: str,
                     persona: str | None = None) -> str:
    """
    [N6]. Record one interview answer and release the job when none are left.

    The answer is appended to the ledger row rather than replacing the question:
    a REPAIR that later asks "which question produced this gate" needs both the
    question and what the user said, and an overwrite would lose the first.
    """
    ledger = J.read_artifact(job_id, "answer_ledger", persona)
    if ledger is None:
        return f"{job_id}: no answer ledger yet"
    if not str(answer or "").strip():
        return f"{job_id}: an empty answer is not an answer"

    remaining = []
    matched = False
    for item in ledger.get("interview_items") or []:
        if isinstance(item, dict) and str(item.get("question_id")) == question_id:
            matched = True
            continue
        remaining.append(item)
    if not matched:
        return f"{job_id}: no open interview item {question_id!r}"

    for row in ledger.get("rows") or []:
        if isinstance(row, dict) and str(row.get("question_id")) == question_id:
            row["user_answer"] = str(answer).strip()
            row["status"] = S.SETTLED
            row["settled_by"] = "interview"

    ledger["interview_items"] = remaining
    J.write_artifact(job_id, "answer_ledger", ledger, persona)

    if remaining:
        return f"{job_id}: recorded — {len(remaining)} item(s) still open"
    J.set_state(job_id, "planning", detail="interview complete", persona=persona)
    return f"{job_id}: recorded — all items answered, the next tick plans it"
