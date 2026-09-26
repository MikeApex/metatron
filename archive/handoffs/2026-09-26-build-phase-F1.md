# Phase F1 — bootstrap run 1, `plant_watering`, Mike present throughout

*Started 2026-09-26. **Live, being written as the run proceeds** — a crash mid-session must not
lose the record. Dated 09-26, not the 09-25 the prompt assumed: the prompt was written the day
before the run. **Titled `plant_watering`, not the `home_care` of plan § 11** — Mike re-scoped it
mid-run; reasoning below. The live job is `BLD-0926-02`.*

**Model:** Opus 5, main session. Subagents declare their own models (plan § 7).

---

## Step 1 — the trigger: HAND-FILED, and the live attempt was not made

**Two tickets were filed. The first was mis-specified and is abandoned; the second is the live
job.** Both were hand-filed on the VM by a direct `request_build` call inside
`persona_scope("mike")`, and both wrote their ticket row and their `BUILD_PROPOSED` quality event
correctly — so the plumbing was exercised twice and held twice.

### `BLD-0926-01` — ABANDONED, mis-specified at filing

Filed 11:22:33, fingerprint `d573fe497c2f912a`, `capability_hint: home_care`. Its gap was written
as the whole of household upkeep:

> Household upkeep has no purpose-built owner: nothing records which recurring home tasks exist,
> when each was last done, or which are due now, so a question about when a plant was last watered
> is answered by improvising from recent context, which has given wrong last-done dates repeatedly.

**Mike stopped it before any node ran** and re-scoped (below). Abandoned via
`build_board.py --abandon` with that reason, which wrote **the first row ever to
`config/build/registry.yaml`** — so the dedupe/refusal path in `core/build/registry.py` now has a
row to refuse against, which it never had before this run. The row is uncommitted and the ticket
stays open on the VM until a deploy carries it.

Nothing was built against it. One `attempts.jsonl` row exists for its N2 (`D.begin`, bookkeeping
only — no subagent was spawned, no model call).

### `BLD-0926-02` — the live job

Filed 11:29:37, fingerprint `8370008669610345`, `capability_hint: plant_watering`.

> **gap:** The user asked to be reminded when the plants at home need watering, and nothing does
> that.
>
> **trigger:** phase F1 run 1, hand-filed; user asked for a reminder to water the plants at home

### Why the re-scope, and why the gap text is deliberately naive

Mike's instruction: narrow it to *a tool to determine when the plants at home need to be watered*.
A `home_care` cluster may come later and is explicitly not this run's concern.

**The gap text carries none of the diagnosis in this document.** No mention of the existing daily
job, the wrong last-done dates, or a future cluster. His constraint was *"we're assuming the user
requested a reminder for watering plants at home — that's as far as Build knows."* N2 Inquiry works
in a vacuum and sees only the gap, the trigger and the mode; feeding it a conclusion would
contaminate the question set, which is the one artifact whose value depends on not having been
told the answer.

### The capability is named `plant_watering`, not `home_care` — and that is architectural

Plan § 11 says run 1 builds `home_care`. It does not. Mike's call, with the reason recorded
because § 11 and § 14 both name `home_care`: in the four-layer graph (Coord → ~12 category agents
→ tier-3 agent → Synthesizer), **`home_care` is the shape of a CATEGORY agent that routes, and
this capability is a tier-3 leaf that does the work.** Naming the leaf for its job means a later
`home_care` category is a new file plus a routing line, not a rename of this one across two
routing files, an agent file and a registry row.

### No verbatim question exists, because none was asked

Mike's call: skip the live trigger attempt and hand-file. The prompt asked for the verbatim
question that worked, as the first known-good should-file case for the fixture the plan owes.
**There is none to record.** The reason it was skipped is below, and it is not "we forgot".

### Mike's intent for run 1 is narrower and better-posed than the prompt's

The prompt framed run 1's trigger as a test of whether the Coordinator files an *unowned* gap.
Mike's actual goal (stated this session): **build a purpose-built, callable plant-watering
capability that supersedes the existing improvised mechanism post hoc.** He noted that removing
Logistics first, so nothing could claim the class, would land in the same place — so it was not
worth doing. That is the right read: the project's own record says the Coordinator doing the
arithmetic itself from stale context *is* the failure, so the existing mechanism is the thing to
replace, not an owner that makes the gap illegitimate.

### Finding before the trigger: the fig question was a contaminated probe

Raised before anything was filed, and it bears on how Phase E's seventh probe should be read.
Two config facts give the Coordinator a legible reason to believe plant watering is already
covered:

1. **A daily `plant_watering_check` scheduled job exists**, created by an agent on
   2026-08-05, running on `coordinator`, described as *"Daily check for plant watering needs based
   on temperature and last watered date."* It performs that standing judgement every day. The logs
   show it doing so — *"43 days elapsed since Aug 4, 2026. Current temperature is 18°C with recent
   rainfall…"* (log window 2026-06-28 → 09-26, entry 51).
2. **Logistics' directory entry claims the whole class** — *"if something needs to happen in the
   world, Logistics owns it"*, plus *"any user-defined recurring habit or practice that should be
   tracked or prompted"*. `config/agents/logistics.md:41` names *"weekly (watering plants, grocery
   run)"* explicitly.

So filing shape 1 ("its class appears in no entry of the specialist directory") **cannot fire for
household upkeep at all**, and shape 2 ("a standing judgement over a history that no specialist
actually performs") asks the Coordinator to rule against a job it is itself running daily.

**Consequence for the record:** Phase E's conclusion — that the Coordinator's refusal to file on
the fig question is a judgement defect and "the vertical's premise" failing — is at minimum
incompletely diagnosed. A conflict between two config files is a sufficient explanation, and it
would not be fixed by anything done to `coordinator.md`'s procedure placement (which 4f0a6c3
already tried, with no change in behaviour — consistent with this reading).

**Also measured:** plant watering is the *only* household-upkeep task with real history in the
logs across the 90-day window. Everything else is a one-off (a chimney/fireplace service on
Sept 21) or absent. So the prompt's step-1 requirement — a household task with a history — was
only satisfiable by the contaminated family.

### The old daily job is removed BY HAND after the capability lands — Mike's call

If the new capability lands while `plant_watering_check` is still enabled, two things perform the
same job: the new tool answering properly, and the old daily job still improvising on its own
schedule. That is a one-home-per-rule-class collision, and it could pass acceptance while the old
job keeps producing wrong answers nightly.

**Mike's decision: remove it manually once the new tool is built** — deliberately not in the
plan's `registration[]` block. This is also forced rather than merely preferred:
`plant_watering_check` is an **agent-created** schedule (created 2026-08-05) living in the persona
data tree, which is Denied tier, so no Build node and no session could remove it. It was always
going to be his hand.

**Open item for whoever closes this run: the removal is not done yet.** It is the one thing that
makes the capability's answer the only answer.

---

## § 12 rows — status

| Row | Status |
|---|---|
| **Trigger** — `check_agent_tools.py --agent coordinator` | ✅ **closed.** 0 planned, 0 named-as-live-but-unbuilt, 0 not-granted, 0 undocumented, across 1 agent and 12 persona files. `request_build` named and granted, neither class flagged. |
| **Trigger** — a live Coordinator turn ending in `request_build` | ⛔ **OPEN, not attempted.** Mike's call. No verbatim should-file case recorded. |
| **End-to-end**, first arrow (`request_build` on the VM → …) | ⛔ **OPEN as the prompt defines it.** Precisely: `request_build` *did* run on the VM and wrote a correct ticket and event — the mechanism half executed. What did not happen is the **Coordinator originating the call**. |
| all other End-to-end clauses | pending — run in progress |
| **Under-filing** (`tests/fixtures/build_trigger_requests.yaml`) | ⛔ **OPEN and not closed by this run.** The fixture does not exist. Proceeding without it is Mike's recorded decision, not an oversight. `config/modules/routing_cloud.yaml:66` asserts it exists; that comment is wrong and known to be wrong. |

---

## Inquiry — PASSED the validator, 24 questions, 0 defects

Artifact: `data/build/jobs/mike/BLD-0926-02/question_set.json`. Code added only `job_id`,
`generated_at`, `upstream_fingerprint`; nothing was added to any question.

**What it was handed, in full:** three lines — `mode`, the gap, the trigger — plus its own
definition file. Nothing else.

**Its verdict: `disposition: extend`, not `new`.** It argues against building a plant-watering
capability at all: *"a plant-watering specialist would generalise to nothing, which is the
narrow-tool failure."* It wants a generic recurring-upkeep item with a persisted last-done date and
a confirmation, and named the next four requests of the same shape unprompted — bin day, filter
change, pet medication, smoke-alarm batteries. It reached this **from a vacuum, with no knowledge of
the `home_care` cluster plan**, which is the altitude rule working as designed.

It caveated it honestly: if no recurring-upkeep item type exists anywhere, the disposition becomes
`new` *"at the household-upkeep class level, never at the plant level."* The Librarian is what
resolves that.

### Minor finding on the output

1. **Two internal cross-references are wrong**, in `declined_to_ask`: *"which q15 settles"* about
   per-item vs single cadence (q15 is the sensitive-tier question; the cadence questions are q2 and
   q16), and *"q17 asks only whether a household inventory is sensitive-tier"* (q17 is
   reconciliation; q15 is the tier question). It renumbered and the back-references did not follow.
   **The validator does not check cross-references**, so nothing would have caught this.

---

## ⚠ DEFECT 1 — Inquiry invented an architectural owner, and nothing could catch it

**Confirmed by a source audit of the live agent** (its context intact, artifact already landed —
the audit could not alter it). Its answers were verified independently against the two files it
named; both quotes are exact.

**The claim.** Check 2 of the three supporting `disposition: extend` reads: *"the scheduler daemon
invoking orchestrator sessions, with the Time Director as the agent that owns time-anchored
prompting, is the stated architecture."*

**Time Director has been RETIRED since 2026-05-28.** `config/agents/time_director.md` line 1: *"Time
Director Agent — RETIRED. Prioritization intelligence absorbed into the Synthesizer. This file is
inactive."* It is in **neither** routing file, so `resolve_model("time_director")` would raise and it
cannot be dispatched. **It is literally the `time_director` shape** — an agent file with no routing
entry — that this plan's own wiring gate exists to catch (§ 3 N13, § 12 Registration check).

**Where the string came from — two auto-injected documents, no tool call.** The audit confirms
Inquiry made **zero** tool calls before producing the artifact: no reads, no greps, no bash. It
never opened `config/agents/` and never confirmed a Time Director file exists.

- `CLAUDE.md:140` — the Terminology table, where "Time Director" appears as an *example of a naming
  convention*, with no description of its role.
- **`MEMORY.md`** — *"Coordinator (ears/routing/context) + Synthesizer (integration/response, **Time
  Director built in**); **not yet implemented**"*. **This is the aggravating source.** The only line
  anywhere that says anything functional about Time Director says the pipeline it sits in is not
  built. So the evidence was not merely absent — it was **contradicted**.

**It owns the error without hedging**, quoted because the plain admission is the useful artifact:
*"No text stated it. I inferred it from the name. I inflated a name into a role — that is the plain
answer."*

**A second invention in the same clause**, which this document missed on first read and the audit
surfaced: *"emitting a user-facing prompt on a cadence is already its job"* is also unsourced. The
`CLAUDE.md:295` line says a scheduler daemon invokes orchestrator sessions — nothing about
user-facing output. So one clause welded **two** inferences to one real fact and labelled the
composite *"the stated architecture."*

### Why nothing caught it, and the fix

**The ban on inventing sources is enforced as a FIELD ban, and the offence was committed in prose.**
Inquiry's own words: *"My brief forbids `candidate_sources` precisely so invented leads cannot be
followed. I complied with the field ban and then committed the same offence in prose, in a free-text
field nothing validates. 'Is the stated architecture' is a source claim wearing different clothes.
The ban caught the shape and missed the substance."*

So this broke **no rule it was given**, and the validator — which enforces the rules it was given —
passed it correctly. **The failure is a missing instruction, not a disobedient model.**

**The vacuum is not clean, and the surface is wider than `CLAUDE.md`.** The audit's exhaustive source
list: global `~/.claude/CLAUDE.md`, project `CLAUDE.md` (full text), **`MEMORY.md`** (full bullet
list), a git-status snapshot (branch, modified/untracked paths including this handoff's filename, and
five commit subjects), and an environment block. All auto-injected. Its own process finding: *"I was
told I see no manifest, and then three project documents were auto-injected describing the
architecture, agent names and design decisions… it defeated [the vacuum] in exactly the place the
design predicted — the disposition, which is the one field where naming an existing owner is
load-bearing."*

**The fix is NOT cutting off the injected context.** `CLAUDE.md:295` is what produced q14 — nothing
owns the last-watered date — the most useful question in the set. The problem is asserting an
unverified part of it **as fact in the field that carries the verdict.**

**Proposed fix (not applied during the run — Mike's call):** a paragraph in
`.claude/agents/build-inquiry.md` mirroring the existing source ban — it may read architecture
description, but must never cite a named agent, tool or module as existing, routed, or owning
anything; where it needs to know what exists, that belongs **in the spine as a question for the
Librarian**, never in `disposition_evidence` as an assertion. That file carries **no `ask` or `deny`
rule** in `.claude/settings.json` (only `config/agents/*.md` does), so the edit is ungated.

### What survives the audit

**The `extend` direction does not rest on Time Director at all.** It rests on the request's own
content: a watering interval is a parameter, not a behaviour, and a plant-specific path generalises
to nothing. That reasoning is intact, and **none of the 24 questions depends on the false clause.**
What died is the claim to have identified the existing owner.

Inquiry's own statement of what check 2 should have said: *"no owner verified; the
scheduler-invokes-sessions line suggests a scheduled path exists, and whether any agent owns
cadence-based user-facing prompts is unchecked and must be checked before build."*

---

## ⚠ DEFECT 2 — the graph has no path back from a clean-but-wrong artifact

**Structural, and more consequential than defect 1.** The one retry per stage fires only on
**validation defects**. `send_back` exists only for the review (review → Planner). Position is
derived from `_artifact_done()`, i.e. whether the artifact file exists on disk. There is no
`rewind`, `reset`, `discard` or `redo` in `core/build/driver.py`.

So an artifact that **validates cleanly but is substantively wrong** is a one-way door. The only
routes back are:

1. **Hand-delete the artifact file** — off-piste state manipulation, and precisely what
   `.claude/commands/build.md` warns against (*"if you find yourself about to hold a rule in your
   head — don't re-spawn, delete this first — that is a defect in the code, not a step for you"*).
2. **Abandon the ticket and re-file** — but the registry's dedupe refuses a same-fingerprint ticket,
   and an identical gap produces an identical fingerprint. Varying the gap text to get past it would
   change Inquiry's input and destroy the comparison.

**Why this run proceeded anyway rather than forcing a route back**, recorded so the decision is
legible: the false clause is **inert downstream**. The Librarian builds one inventory row per
question and no question mentions Time Director. The Planner holds `Read`/`Grep`/`Glob` and its
`files[]` and `information_sources` are validated against the real tree — a routing entry for a
retired agent fails `check_agent_tools.py` and the wiring gate. The adversarial reviewer's entire
job is finding a plan resting on a wrong premise. **The structurally vulnerable stage is specifically
the one with no tools**, which bounds the exposure narrowly.

---

### Correction to this document's own earlier reporting

An earlier summary of q9 given to Mike in chat said *"the plants are Iva's too."* **Inquiry named
no person.** Its wording is *"someone else in the home"*, and its reply contains zero proper names —
verified by grep. The name came from this session's own reading of the 90-day log window while
hunting for household history, and leaked into a paraphrase of a clean artifact. Recorded because
the direction of the error matters: a summariser adding persona detail to a vacuum artifact is the
failure the vacuum exists to prevent, even when the artifact itself is clean.

The source of the shared-asset idea is `.claude/agents/build-inquiry.md:151` — its own instructions
tell it to test *"jointly-held resources — a shared asset treated as the principal's alone"* first.
Applied to the words "plants at home". No data involved.

## STOPPED after Inquiry — Mike's call, 2026-09-26

**The run is halted, not parked or failed.** Mike stopped it to revise Inquiry's instructions
(the defect-1 fix plus other changes he has in mind) before any further stage runs. The
`build-inquiry.md` fix proposed above was **deliberately not applied** — he is batching it with
those other changes.

### Exactly where it stands

| | |
|---|---|
| Live job | `BLD-0926-02`, persona `mike`, mode `construct` |
| Artifacts on disk | `ticket.json`, `question_set.json`, `attempts.jsonl` |
| Driver's next step | Librarian, attempt 1 — **not begun**, no attempt row spent |
| Worktree | none created; implementation was never reached |
| Model calls spent | one subagent (Inquiry), ~40k tokens including the source audit |

**Repository state — nothing needs unwinding:**

- `config/build/registry.yaml` — **new, untracked.** Holds the single `abandoned` row for
  `BLD-0926-01`. Uncommitted, so the VM still shows both tickets as `proposed` until a deploy
  carries it.
- `archive/handoffs/2026-09-26-build-phase-F1.md` — this file, new, untracked.
- `DEV_BACKLOG.md` — modified by the session-start sync, not by this run.
- `data/build/` is gitignored, so the job store is invisible to git by design.

### ⚠ The constraint to carry into the Inquiry revision

**Revising `build-inquiry.md` does not let this job re-run Inquiry.** Defect 2 is the blocker:
the driver derives position from artifacts on disk, and `question_set.json` exists, so the next
step will remain the Librarian no matter what the instructions say. Re-running Inquiry under new
instructions therefore needs one of:

1. **Hand-delete `data/build/jobs/mike/BLD-0926-02/question_set.json`** — works, but is the
   off-piste state manipulation the command file names as a code defect rather than a step.
2. **Abandon `BLD-0926-02` and file a third ticket** — supported verbs only, but the registry
   dedupe refuses a same-fingerprint ticket, so the gap text would have to change, which changes
   Inquiry's input and destroys the comparison against this artifact.
3. **Build the rewind** — add a supported way to discard a clean-but-wrong artifact and rewind the
   cursor. This is the fix defect 2 actually asks for, and run 1 is what surfaced the need.

**Decide this before revising the instructions**, not after — otherwise the revision lands with no
way to exercise it on this job.

## Librarian onward

*(filled as the driver names each stage)*

## Parks

*(none yet)*

## Registry row

*(pending N13)*
