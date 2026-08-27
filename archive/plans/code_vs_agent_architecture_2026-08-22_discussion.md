# Code-dominant architecture — the "built backwards?" discussion (2026-08-22)

> **Continued in [code_dominant_rebuild_notes.md](code_dominant_rebuild_notes.md)** — the running
> notebook for this thread (opened 2026-08-27). This file stays as the dated record of round one.

**Status: preliminary discussion, no decision by Mike.** This document is the consultable record
of a design conversation between Mike and Claude Code (Opus 5), anticipating a version-1/alpha
refactoring. It bears directly on the queued `@session` decision **"where code should replace
model judgment"** (`DEV_BACKLOG.md` § Later § Decisions) and on **A8 sequencing**. Verbatim
exchange: `archive/transcripts/2026-08-22 — Metatron — Load Project Context…`.

---

## The question Mike posed

Metatron today is **detailed agents and little code** — 14 rich instruction files on a thin
harness. The observed symptoms: responses that are repetitive, often off-topic, or overwhelmed
with information-gathering at the expense of the user experience. Has it been built backwards?
Should Metatron be rebuilt **code-dominant** — goals mapped procedurally, with agents/models used
for *discrete judgment gates* — while complex agents like the Synthesizer continue to exist?

## The evidence exhibit

Mike ran a prompt against Opus (outside Claude Code): an experienced personal assistant, day one,
near-perfect knowledge of the boss via files, handling a barbecue-invitation RSVP. Two rounds:

1. **First response** — a competent tactical procedure: validate the email (the date doesn't
   resolve — Aug 22 2026 is a Saturday), research identity/relationship, check feasibility,
   choose among five outcomes, escalate one framed decision with a default, execute, log.
2. **Mike's critique** — narrow and tactical; "a filter, not a compass"; default-attend if no
   blockers; no reflection on life goals, opportunity cost, or the greater context.
3. **Amended response** — the spine inverts: intent before feasibility. Season of life,
   stated-vs-revealed preferences, portfolio view (decide at the margin, not per-invitation),
   empty calendar space as the scarcest asset, asymmetric regret / closing windows,
   proportionality of the decision process itself, and a **standing allocation policy** built
   once so that individual invitations become near-automatic outputs.

Mike's observation: **the innate model inertia is toward the reactive** — the compass layer only
appeared under pressure.

## Claude's analysis (recommendation: yes to the inversion)

1. **The transcript decomposes into almost no model judgment.** Mechanical checks (date
   arithmetic, provenance, duplication, travel math) are code. Retrieval (who is Mary,
   reciprocity ledger, who's in the room) is CRM/FAISS/calendar queries. The genuine judgments
   are few, narrow, and arrive with computed evidence attached — small gate calls with
   constrained outputs. Only the final decision-note synthesis looks like a current Metatron
   agent. The response's quality came from the **enforced ordering of the spine** — which prose
   instruction files cannot enforce; a procedure carried in prose is re-decided every turn, which
   is where repetition/flooding comes from. The D2 judgement-consistency note is the sharp form:
   same model, same evidence, opposite answers four minutes apart.
2. **The reactive inertia is structural, not a prompt defect.** The compass layer requires
   **standing computed state** — invitation base rates, weekend inventory, relationship
   trajectories, the allocation policy. No per-turn model call can know "this is the fourth
   Sunday obligation this month" unless something computed and stored it. You cannot prompt your
   way to a compass; you compute one and hand it to a gate. Raw material exists
   (`tools/analytics.py`, Pattern Miner, traces); nothing derives allocation state from it.
3. **The project has been voting for this all year, one incident at a time:** privacy enforced in
   Python not prompts; `filter_output` as the only control on deliberation leaks; the CRM
   confirmation gate (Steven/Stephen variance); `tone_shape` removed from the schema rather than
   instructed against; scheduler maintenance as `function:` jobs; and **intake** — swept hourly,
   classified in Python, queued per domain, model tier double-gated off — already the target
   architecture in miniature, and it works.
4. **The founding-principle tension, named:** "config files are the product; if changing behavior
   requires a code change, that is a design failure" *sounds* repealed by this. It isn't, if the
   split is drawn as: **code owns** control flow, ordering, mechanical validation, retrieval,
   computed state, escalation routing; **config owns** the policy — gate prompts, thresholds,
   allocation rules, automatic-yes/no lists, what escalates, the Synthesizer's voice. Today the
   principle is honored in form and defeated in practice (behavior change = edit a 6–7k-token
   file and hope). Small config-defined gates make config edits targeted and testable — a
   restoration, not a repeal. **Either way the Key Design Decisions list must be amended
   explicitly, not drifted past.**
5. **Costs (baseline: 27.9M input tokens / 26 days, median 26.5k input per turn).** Decomposition
   trades few huge calls for many small Flash-tier gates with near-empty context; most turns skip
   most gates (the transcript's proportionality point — thirty-second triage against a standing
   rule, depth only when triage says so). Expected net input tokens **down** — an estimate to be
   measured in a pilot, not asserted. **Latency is the real risk**: serial gates stack
   round-trips, and `coordinator`'s existing blocker is already latency.
6. **The honest risk: brittleness at the long tail.** Hand-coded spines fail on unrecognized
   shapes; the fat agent's generality is what currently absorbs them. Mitigation is
   architectural: **code handles recognized shapes; the fallback for unrecognized input is the
   current agent path**, not an error — which also makes migration incremental, carving
   procedures out of agents one domain at a time.

## Recommendations as given

1. **Yes to the inversion**, at the point-4 split. Synthesizer stays a real agent; the
   Coordinator is the first candidate to become mostly code (routing is closer to classification
   than judgment; intake proved the shape).
2. **Decide this before A8 executes.** A8's config/providers/tools extraction is useful under
   either future, but the orchestrator-pipeline internals it would tidy are what this rewrites —
   sequence the decision first or pay for A8 twice.
3. **Pilot one domain, don't decide wholesale.** The invitation/RSVP flow is the natural pilot —
   the Opus transcript is effectively its spec, and it exercises mechanical gates, CRM retrieval,
   a judgment gate, an escalation note, and Synthesizer voice. Measure tokens, latency, and
   whether the flooding symptom goes away.
4. **The compass layer is a separate build regardless of the verdict** — computed allocation
   state feeding gates; no agent-file change can deliver it.

## Open question left with Mike

**When a gate's evidence is thin or conflicting: ask Mike, or decide-with-default** as the
transcript's assistant does ("if I don't hear by Friday noon, I do X")? Decide-with-default plus
one framed escalation is a larger autonomy grant than anything currently live — and it is the
parameter that determines whether Metatron feels like an assistant or a questionnaire.
