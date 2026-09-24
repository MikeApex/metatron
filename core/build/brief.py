"""
core/build/brief.py — N10. What Mike reads before he says yes.

TWO DOCUMENTS, DIFFERENT JOBS.

  · THE APPROVAL BRIEF, one per job, read at gate [N9]. It is a SPEC: the
    decisions taken, the options that were open, the assumption behind each and
    what would falsify it, the surface the capability covers and the surface it
    refuses, what it will read, what it will cost. Plan section 13.8's answer to
    "a redacted brief means the executing session guesses" — the brief carries
    decisions and assumptions, which is what a spec is.

  · A needs_tool BRIEF, one per missing tool, for the Mac. Ordinary development
    Mike does himself: nothing on the VM writes code (ruling 0.3). These are how
    Build discovers its own substrate, and on run 1 they are EXPECTED output
    rather than a failure.

REDACTION IS A MECHANISM HERE, NOT A DISCIPLINE — and that is the whole lesson
of the phase 3 review rounds, applied before the defect rather than after it. A
brief is assembled from the Answer Ledger, and the ledger is derived from the
corpus, so "write it carefully" is exactly the shape of rule this project has
watched fail. Two layers, both code:

  1. STRUCTURAL. The renderer emits only declared fields. Evidence appears as
     `tool -> N rows`, never as a sample, never as the probe's arguments, and
     the condensed text never appears at all.
  2. BACKSTOP. `redact()` masks any literal profile value that reached the body
     anyway, and `findings()` reports what it had to mask. A brief that needed
     masking is a defect report about the layer above it, so the runner records
     the finding rather than swallowing a clean-looking document.

The backstop catches literals and cannot catch a paraphrase. Stated because the
opposite claim would be the more comfortable one: a model that describes a
person rather than naming them defeats layer 2 entirely, and layer 1 — emitting
only declared fields — is what actually holds. Layer 2 is the proof that layer 1
worked, which is the only honest description of it.

Plan: archive/plans/build_vertical_plan_2026-09-18.md section 3 (N10), section 13.8
"""

from __future__ import annotations

import re

from typing import Any

MASK = "[redacted]"

# A profile value shorter than this is a word, not an identity — "UK", "he",
# "45". Masking those would shred ordinary prose and teach everyone to ignore
# the mask. The same threshold tests/test_build_manifest.py's profile_values()
# uses for the same reason.
_MIN_MASKABLE = 4


# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------

def persona_values(persona: str | None = None) -> list[str]:
    """
    Every non-trivial literal string in the persona's profile — what must not
    appear in a brief.

    Read from the LIVE profile through the existing read path rather than by
    globbing config/, so it sees what the runtime sees. Returns [] rather than
    raising when no persona is bound: a brief rendered outside a persona scope
    has no persona values to leak, and raising here would make the renderer
    fail in exactly the tests that need it most.
    """
    try:
        from core.persona import persona_scope, resolve_persona
        from tools.profile import _load as _load_profile
        with persona_scope(resolve_persona(persona)):
            data: Any = _load_profile()
    except Exception:
        return []

    out: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, str) and len(node.strip()) >= _MIN_MASKABLE:
            out.append(node.strip())

    walk(data)
    # Longest first, so masking "Iva Diamond" does not leave "Diamond" behind
    # as a fragment of a string already replaced.
    return sorted(set(out), key=len, reverse=True)


def findings(body: str, persona: str | None = None) -> list[str]:
    """Which persona values reached the rendered body. Empty is the pass."""
    return [value for value in persona_values(persona)
            if value and value.lower() in body.lower()]


def redact(body: str, persona: str | None = None) -> str:
    """Mask every literal profile value. Case-insensitive, longest first."""
    for value in persona_values(persona):
        if not value:
            continue
        body = re.sub(re.escape(value), MASK, body, flags=re.IGNORECASE)
    return body


# ---------------------------------------------------------------------------
# Small renderers
# ---------------------------------------------------------------------------

def _text(value: Any) -> str:
    return str(value or "").strip()


def _bullet(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- (none)"


def _evidence_line(row: dict) -> str:
    """
    `tool -> N rows`, and nothing else.

    STRUCTURALLY CONTENT-FREE: the probe's arguments are omitted as well as its
    results, because a search probe's query is composed from the question text
    and the question text is composed from the gap, which is Mike's words.
    """
    parts = []
    for record in row.get("evidence") or []:
        if not isinstance(record, dict):
            continue
        parts.append(f"{_text(record.get('tool')) or '?'} → "
                     f"{int(record.get('rows') or 0)} rows"
                     + ("" if record.get("data_available") else " (nothing)"))
    return "; ".join(parts) if parts else "no source probed"


# ---------------------------------------------------------------------------
# The approval brief
# ---------------------------------------------------------------------------

def approval_brief(job: dict, question_set: dict, ledger: dict, plan: dict,
                   estimate: dict | None = None, verification: str = "",
                   persona: str | None = None) -> str:
    """The document read at gate [N9], REDACTED. See assemble() for the pair."""
    return assemble(job, question_set, ledger, plan, estimate, verification,
                    persona)[1]


def assemble(job: dict, question_set: dict, ledger: dict, plan: dict,
             estimate: dict | None = None, verification: str = "",
             persona: str | None = None) -> tuple[str, str]:
    """
    (raw, redacted). Both, because the leak check needs the raw one.

    THE PAIR IS THE WHOLE POINT, and returning only the redacted body was a
    defect in the first version of this module: `findings()` run on an already
    redacted body ALWAYS reports clean, so the check that was supposed to tell
    the runner the structural layer had failed could never fire. A guard that
    cannot fail looks exactly like a guard that passes.

    Every argument may be partial: a job parked at `needs_interview` has a
    ledger and no plan, and the brief is exactly as useful then — it is what
    tells Mike what the job is waiting on. A renderer that required a complete
    job would produce nothing at the moment a human is being asked to act,
    which is the only moment it exists for.
    """
    job = job or {}
    question_set = question_set or {}
    ledger = ledger or {}
    plan = plan or {}
    capability = plan.get("capability") or {}
    job_id = _text(job.get("job_id"))

    lines: list[str] = [
        f"# Build brief — {job_id}",
        "",
        f"**Mode:** {_text(job.get('mode')) or 'construct'} · "
        f"**State:** {_text(job.get('state'))} · "
        f"**Attempt:** {job.get('attempt', 1)} · "
        f"**Depth:** {_text(question_set.get('depth')) or '—'}",
        "",
        "## The gap",
        "",
        _text(job.get("gap")) or "(no gap recorded)",
        "",
        f"*Filed by:* {_text(job.get('trigger')) or 'unknown'}",
        "",
    ]

    # --- What is proposed -------------------------------------------------
    if capability:
        lines += [
            "## What this builds",
            "",
            f"**`{_text(capability.get('id'))}`** — {_text(capability.get('one_line'))}",
            "",
            f"- **Kind:** {_text(capability.get('kind'))}",
            f"- **Disposition:** {_text(capability.get('disposition'))} — "
            f"{_text(capability.get('disposition_evidence')) or '(no evidence given)'}",
            f"- **Generalises to:** {_text(capability.get('generalizes_to')) or '—'}",
            f"- **Runs:** {_text(capability.get('execution_mode'))}, "
            f"budget {capability.get('latency_budget_ms', '?')}ms",
            f"- **Theme:** {_text(capability.get('theme')) or 'none — a leaf under the Coordinator'}",
            "",
        ]
        replaces = [_text(r) for r in (capability.get("replaces") or [])]
        if replaces:
            lines += [f"- **Replaces:** {', '.join(replaces)}", ""]
    else:
        lines += ["## What this builds", "",
                  "*No plan yet — this job has not reached the Planner.*", ""]

    # --- The decisions ----------------------------------------------------
    # THE HEART OF THE BRIEF. Section 4's "the ledger compiles into the
    # capability": these rows are not build-time scaffolding, they are the
    # capability's runtime behaviour written down, so this is where a wrong
    # capability is cheapest to catch.
    judgments = [r for r in (ledger.get("rows") or [])
                 if isinstance(r, dict) and _text(r.get("decision"))]
    lines += ["## Decisions taken", ""]
    if not judgments:
        lines.append("*No judgment rows — everything settled from policy or data.*")
    for row in judgments:
        options = [_text(o) for o in (row.get("decision_options") or []) if _text(o)]
        lines += [
            f"### {_text(row.get('question_id'))} — {_text(row.get('decision'))}",
            "",
            f"*Options considered:* {'; '.join(options) if options else '(none recorded)'}",
            "",
            f"*Assumption:* {_text(row.get('assumption')) or '(none stated)'}",
            "",
            f"*Falsified by:* {_text(row.get('assumption_falsifier')) or '(nothing stated)'}",
            "",
            f"*Evidence:* {_evidence_line(row)}",
            "",
        ]

    # --- What it touches --------------------------------------------------
    surface = plan.get("surface_map") or []
    if surface:
        lines += ["## Surface — what it does and what it refuses", "",
                  "| Entity | Operation | Status | Why |", "|---|---|---|---|"]
        for item in surface:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"| {_text(item.get('entity'))} | {_text(item.get('operation'))} "
                f"| {_text(item.get('status'))} "
                f"| {_text(item.get('reason')) or _text(item.get('ticket')) or '—'} |")
        lines.append("")

    grants = sorted({_text(t) for entry in (plan.get("registration") or [])
                     if isinstance(entry, dict)
                     for t in (((entry.get("routing") or {}).get("local") or {})
                               .get("allowed_tools") or []) if _text(t)})
    lines += ["## What it may read", "",
              _bullet([f"`{g}`" for g in grants]) if grants
              else "- (no grants declared)", ""]

    files = [_text(f) for f in (plan.get("files") or []) if _text(f)]
    tests = [_text(t) for t in (plan.get("tests") or []) if _text(t)]
    lines += ["## Files it writes", "", _bullet(files), "",
              "## Tests it lands with", "", _bullet(tests), ""]
    if not tests:
        lines += ["> **No tests declared, so this cannot land.** `verify.run_all()` "
                  "fails a capability with an empty test list — a capability arrives "
                  "with its own evidence or it does not arrive.", ""]

    risks = [_text(r) if isinstance(r, str) else _text((r or {}).get("risk"))
             for r in (plan.get("risks") or [])]
    lines += ["## Risks", "", _bullet([r for r in risks if r]), ""]

    # --- What is still owed ------------------------------------------------
    interview = [i for i in (ledger.get("interview_items") or [])
                 if isinstance(i, dict)]
    if interview:
        lines += ["## Waiting on you — interview items", "",
                  "*The job is parked until these are answered. Missing data is a "
                  "work item, not a blocker.*", ""]
        for item in interview:
            lines.append(f"- **{_text(item.get('question_id'))}** "
                         f"{_text(item.get('text'))} — {_text(item.get('why'))}")
        lines.append("")

    tool_gaps = sorted({t for row in (ledger.get("rows") or [])
                        if isinstance(row, dict)
                        for t in (row.get("needs_tool") or [])})
    if tool_gaps:
        lines += ["## Needs a tool that does not exist", "",
                  "*One brief per tool below. These are Mac-side builds — nothing on "
                  "the VM writes code — and on an early run they are expected output, "
                  "not a failure.*", "",
                  _bullet([f"`{t}`" for t in tool_gaps]), ""]

    # --- Cost --------------------------------------------------------------
    lines += ["## Cost", ""]
    if estimate:
        lines += [
            f"- **Estimated:** ${float(estimate.get('usd') or 0.0):.4f}",
            f"- **Spent so far:** ${float(estimate.get('spent') or 0.0):.4f}",
            f"- **Limit in force:** ${float(estimate.get('limit') or 0.0):.2f} "
            f"({_text(estimate.get('limit_source')) or 'unknown'})",
            "",
        ]
        notice = _text(estimate.get("notice"))
        if notice:
            lines += [f"> {notice}", ""]
    else:
        lines += ["*Not estimated yet — the job has not reached N8.*", ""]

    if verification:
        lines += ["## Verification", "", "```", verification.strip(), "```", ""]

    lines += [
        "---",
        "",
        "**Approving lands this in the overlay and runs the full check set against "
        "it.** A failing check reverts everything before the node returns — nothing "
        "is ever left half-applied. Refusing reverts too. No tracked file is written "
        "either way; promotion into the tree is a separate, manual step.",
        "",
    ]

    raw = "\n".join(lines)
    return raw, redact(raw, persona)


# ---------------------------------------------------------------------------
# needs_tool briefs
# ---------------------------------------------------------------------------

def needs_tool_briefs(job: dict, question_set: dict, ledger: dict,
                      persona: str | None = None) -> dict[str, str]:
    """
    tool name -> its brief. One per distinct gap, never one per question.

    Grouped by TOOL rather than by question because the work is one build
    whatever asked for it, and a brief per question would hand Mike the same
    build three times with three different justifications.
    """
    job_id = _text((job or {}).get("job_id"))
    spine = {_text(q.get("id")): q for q in (question_set or {}).get("spine") or []
             if isinstance(q, dict)}

    wanted: dict[str, list[dict]] = {}
    for row in (ledger or {}).get("rows") or []:
        if not isinstance(row, dict):
            continue
        for tool in row.get("needs_tool") or []:
            wanted.setdefault(_text(tool), []).append(row)

    out: dict[str, str] = {}
    for tool, rows in sorted(wanted.items()):
        lines = [
            f"# needs_tool — `{tool}`",
            "",
            f"*Raised by Build job {job_id}. This is ordinary development on the Mac: "
            f"nothing on the VM writes code. The job parks at `briefed` until the tool "
            f"lands and the ticket is re-run.*",
            "",
            "## Why it is needed",
            "",
            f"{len(rows)} question(s) in this job named a source this tool would serve, "
            "and could not be answered without it.",
            "",
        ]
        for row in rows:
            question = spine.get(_text(row.get("question_id"))) or {}
            lines += [
                f"- **{_text(row.get('question_id'))}** "
                f"({_text(question.get('class')) or 'unclassed'}) "
                f"{_text(question.get('text'))}",
                f"  - *Why it matters:* {_text(question.get('why_it_matters')) or '—'}",
                f"  - *Sources named:* "
                f"{', '.join(_text(s) for s in (question.get('candidate_sources') or [])) or '—'}",
                f"  - *Probe said:* {_evidence_line(row)}",
            ]
        lines += [
            "",
            "## What it must be",
            "",
            "- A **read** tool. The grant allowlist is the whole of what a generated "
            "capability may hold, and a new write would have to be argued for "
            "separately.",
            "- Registered in `core/orchestrator.py` → `register_tools()`, classified in "
            "`core/actions.py`, and added to the read set in the plan's section 6.3.",
            "- Named in `config/agents/build_librarian.md` from day one — a tool named "
            "in an agent file is a specification.",
            "",
            "## When it is done",
            "",
            f"Re-run the parked job. The probe resolves the source again and the "
            f"`needs_tool` row settles; nothing about the question set changes.",
            "",
        ]
        out[tool] = redact("\n".join(lines), persona)
    return out


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

def write_briefs(job_id: str, job: dict, question_set: dict, ledger: dict,
                 plan: dict, estimate: dict | None = None,
                 verification: str = "", persona: str | None = None,
                 as_state: str = "") -> dict:
    """
    Render and write every brief this job owes. Returns a report dict.

    Writes THROUGH THE WRITER, not with open(): the job directory is an
    allow-root and the writer is the only thing that knows that. A brief
    written past it would be the same class of hole the undo journal was —
    a write primitive inside an allow-root with no path rules.

    `leaked` is returned rather than raised on. A brief that needed masking is
    a defect in the renderer above it, and the runner records it as a finding;
    failing the job would destroy the document that reports the problem.
    """
    from core.build import writer

    # THE STATE THE JOB IS ENTERING, not the one it is leaving. The brief has to
    # be written while the state is still writable — writer.WRITABLE_STATES is
    # {briefed, executing} — so at N12 and N14 the write necessarily precedes
    # the move, and the document would otherwise record `executing` as the final
    # state of a capability that landed. The brief describes the OUTCOME of the
    # node that wrote it; `as_state` is that outcome.
    if as_state:
        job = {**(job or {}), "state": as_state}

    # The RAW body is what the leak check reads; the redacted one is what lands.
    raw, body = assemble(job, question_set, ledger, plan, estimate,
                         verification, persona)
    leaked = findings(raw, persona)

    edits = [{"path": str(writer.allow_roots(job_id, persona)[0] / "brief.md"),
              "content": body}]
    tool_briefs = needs_tool_briefs(job, question_set, ledger, persona)
    for tool, text in tool_briefs.items():
        edits.append({
            "path": str(writer.allow_roots(job_id, persona)[0]
                        / f"needs_tool_{tool}.md"),
            "content": text,
        })

    result = writer.apply(job_id, plan, edits, persona=persona)
    return {
        "written": not result.startswith(("REFUSED", "PARKED")),
        "result": result,
        "needs_tool": sorted(tool_briefs),
        # Empty is the pass, and the test proves the detector fires by planting
        # a value — a grep that never matches looks identical to a clean body.
        "leaked": leaked,
        "lines": len(body.splitlines()),
    }
