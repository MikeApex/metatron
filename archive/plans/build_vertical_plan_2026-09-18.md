# Build — the vertical that constructs Metatron's capabilities

*Plan v3.1, 2026-09-18. Supersedes v2 (2026-09-17, `~/.claude/plans/mossy-noodling-valiant.md`)
after the adversarial review at
`archive/plans/build_vertical_plan_review_2026-09-18_fable-5-1.md` and Mike's rulings in its
§ 0; amended in place from v3 after the scoped Opus 5 review at
`archive/plans/build_vertical_plan_v3_review_2026-09-18_opus-5.md`. On approval this is saved as
`archive/plans/build_vertical_plan_2026-09-18.md` — the current filename is harness-generated.
Every code claim was re-checked against the working tree at `7bca654`.*

**What changed from v3.6 to v3.7.** The phase-4 review's **Part 2 re-check** re-ran all ten
round-1 probes unchanged and confirmed **all fourteen closed, nothing reopened.** Three items
were left open, and all three are now fixed: the landed brief recorded the state it was written
from rather than the one it reached; `turn_referent`'s referent block still presented a
`build_tick` as *"the exchange immediately before this one"*; and a landing-day run count divided
by a day that held only Build's own tick. Touched: § 3 (the exchange rule), § 12 (one assertion
each on the end-to-end and run-ledger rows), § 14 (the measured-day rule). **The shape is the
round-3 shape again, and it is worth saying so:** two of the three are *a rule that existed in one
place and not the other* — attribution learned to skip a tick while the referent block did not,
and the brief learned which state it could be written from but not which state to report.

**What changed from v3.5 to v3.6.** The phase-4 second-model review
(`archive/plans/build_phase4_runner_review_2026-09-19_fable-5.md`, Fable 5.1, ten probes that RAN
the runner rather than reading it) returned **fourteen defects; all fourteen fixed.** Touched:
§ 3 (a fifth probe state and the live-feed rule), § 5 (`resume_to` on the ledger), § 7 (the
post-node budget gate), § 8 (the park/fail correction), § 12 (one assertion per defect on the
runner, probe, coherence and jobs rows), § 14 (the run line's expected figure is now `None`).
**Their common shape is the third distinct one this plan has produced** — round 1 was prose never
made mechanism, round 2 mechanisms scoped to their probe, round 3 a mechanism improved in one of
two homes. **These are mechanisms that were never EXERCISED**: a refusal path with no state
guard, a park that could not be resumed, a parse the prompt never produced, a brief write refused
every time, a probe table whose arguments fitted no signature. Each read correctly and had never
once run. *The review's method is why — every finding came from running the code.*

**What changed from v3.4 to v3.5.** Three corrections agreed with Mike on 2026-09-19, before
phase 4 was written. Each is recorded in the section whose prose was wrong rather than collected
in one place: § 14 and § 12's run-ledger row (the dispatch count does not come from the A9
rollup), § 8 (an over-budget job is approved on the VM, never through a confirm card), and § 10
plus § 16's phase-5 line (the Coordinator's `request_build` grant had no owner). Their common
shape is worth naming, because it is not the shape of any of the three phase-3 rounds: **each is
a claim this plan made about a file nobody had opened.** Nothing else moved.

**What changed from v3.3 to v3.4.** One finding from the review's Part 3: seam 3 resolved a
display name without the whitespace collapse the schema applies, so the two stopped agreeing on
exactly the rule the v3.3 round added. Fixed in `core/build/overlay.py` alone by importing the
schema's normalisation rather than restating it. Touched: § 6 (a third correction entry) and
§ 12 (one assertion on the overlay-seam row). Nothing else moved.

**What changed from v3.2 to v3.3.** Five more from the review's Part 2 re-check — four defects
the first round's fixes introduced or left beside them, and one observation that the sweep's
independent re-assertion was narrower than the writer's. Same files, no new ones. Touched: § 6
(a second corrections blockquote beside the first) and § 12 (one new assertion per item on the
same three rows). Their shape differs from the first six and the plan says so: those were prose
never made mechanism; these are mechanisms scoped to the case that prompted them.

**What changed from v3.1 to v3.2.** Six defects from the phase 3 second-model review, all
confirmed and all fixed in `core/build/writer.py`, `core/build/schemas.py` and the seams — no new
files. Touched: § 6 (the six recorded as corrections, in the blockquote convention § 8 already
uses) and § 12 (one new assertion per defect, on the writer, overlay-seam and constitution rows).
Their common shape is worth the plan carrying: each was a place where this document stated a rule
in prose and the implementation honoured the prose exactly. Nothing else moved.

**What changed from v3 to v3.1.** All seven Opus findings and its three verification notes are
adopted as written, with two decisions fixed by Mike: seam 3 rewrites the Coordinator's
valid-name paragraph at prompt assembly and the re-cache per landing is accepted (finding 3);
the ledger carries one run line per landed capability and the tier becomes due at four leaf
capabilities (finding 7). Touched: § 4 (name collision over three sets; generated names go to
the sentence-gated filter list), § 6 (the grant list is an allowlist; seam 3 and seam 4
re-specified; `PersonaError` handled as a stated decision; the same-checks claim split;
`find_places` given its own reason), § 10 (the index is not in the backup; seam wording),
§ 12 (one new assertion per finding, plus a run-ledger row), § 14 (Run and Ancillary), § 16
(the tier's due condition). Nothing else moved; § 11 in particular is as v3 left it.

**What changed from v2, so the diff can be read in one pass.** Rewritten: § 4 registration
matrix and variable homes, § 6 (writer targets, grant list, shape gate, undo, same-checks),
§ 10, § 11, § 12's writer, same-checks, latency and landing rows, § 14 phases 3 and 7 with the
Run and Unseen paragraphs. Untouched, per the review's salvage map: § 2, § 3's rule and node
graph up to N10, § 4's three artifacts, § 5, § 7, § 8, § 9, § 13, § 15. Seven further spots
carry the findings adopted as written and nothing else — each is marked `[v3]` in place:
§ 3's trigger and REPAIR paragraphs (finding 6, option-1 settlements), § 3's graph after N10
(N11 removed), § 4's dedupe clause (finding 8), § 5's registry line (ruling 0.2 — a tracked
file cannot be Build-written), § 7's rung-1 table (finding 9), § 9's closing paragraphs
(finding 8, the needs_tool briefs), § 14's zero-idle sentence (finding 7), § 16's phase lines.
**§ 13 is verbatim by instruction**: items 6, 8, 10 and 13 defend v2 mechanisms — the
worktree, the executing session, run 2 as `venue_finder` — that v3 removes. Read them as the
record of the attacks; the v3 counters are § 6.7, § 6.8 and § 11.

---

## 0. Rulings this version is built on (Mike, 2026-09-18)

1. **All of Build runs on the VM.** Every node, the writer, verification, the ledger and the
   board's data. The Mac holds development, the two read-only board scripts, and the
   `needs_tool` builds Mike does by ordinary development.
2. **Landing is the overlay.** Generated capabilities live in a VM-owned, gitignored,
   backed-up directory and the runtime loads them through four seams (§ 6.5). **Build never
   writes a tracked file** — the writer refuses any path in `git ls-files` above its hardcoded
   deny list, which is what makes this hold mechanically rather than by convention.
3. **What leaves v1 with option 1.** `split` and `extend` are deferred behind a promotion path
   (gate stated in § 11, not designed). `kind: tool`, `function_job`, `check` — and
   `context_block`, which the ruling did not name but which is Python for the same reason —
   need code, nothing on the VM writes code, so they go out as `needs_tool` briefs Mike
   implements on the Mac. The N11 Claude Code session is removed: the Planner produces the
   agent-file text and the overlay record, the writer applies them.
4. **The first real run is re-chosen** (§ 11): `new`, config-only, agent-kind, over existing
   read tools, against a gap Mike filed himself twice on 2026-09-08.
5. Findings 6–9 of the review are adopted as written; § 2's local settlements are adopted
   unless a section below says otherwise.

---

## 1. Context — why this is being built

Metatron's capability surface is fixed by hand. The Coordinator chooses among twelve specialists
named as a literal string list in [`coordinator.md:84-85`](config/agents/coordinator.md); each exists
because Mike opened a Claude Code session and made it exist. When something arrives that fits none
of them, a `ROUTING_MISS` quality event is written,
[`sync_dev_backlog.py`](scripts/sync_dev_backlog.py) files it into `DEV_BACKLOG.md` § Machine log,
and it waits for a human. **That signal already exists, already accumulates, and has no consumer.**

Build is the consumer. It takes a gap and returns a capability, moving Mike from author to approver.
It also replaces the planned Mark 2 rebuild: the same outcome, in place and incrementally, so the
transition does not have to be endured. Mark 2 is not referenced further in this plan; the four
requirements worth keeping from it are stated below on their own merits.

**Two modes, one loop.**
- **CONSTRUCT** — a gap has no capability; build one.
- **REPAIR** — a Build-made capability failed; Inquiry diagnoses it as *the question that wasn't
  asked*, and Librarian/Implementation fold the answer back in. A failure is a gap in the question
  set, not a bug report.

**Four standing requirements, carried on their own merits.**
1. **Trace contract.** Every Build run and every generated capability emits to `core/trace.py` with
   correct nested attribution, timing, tokens and cost, so The Book renders it.
2. **Coherence review.** Periodically, a pass reads everything Build has produced *as a set* and
   reports drift, overlap, contradiction and orphans. The failure it guards against — *a collection
   of individually sensible files that together say something nobody chose* — is an incremental
   builder's characteristic failure, not an edge case.
3. **Rebuildable state.** Any new state a generated capability introduces must be rebuildable from
   an append-only record or by recomputation. No retrofit of the ~25 existing whole-file writers.
4. **Constitution alignment at generation time**, mechanically — a system that writes its own agents
   is the strongest case for not deferring this to review.

---

## 2. Three constraints that shape everything

**Altitude is the first constraint, and getting it wrong is Build's characteristic failure.** A
request arrives as an instance; the capability that answers it should usually be the class. An
invitation needing an RSVP is not a request for an `rsvp_tool` — it is one entry point into
scheduling and time-allocation. A Build that builds what was literally asked for produces a drawer of
narrow tools that each work and together answer nothing, which is the same failure the coherence
review guards against, arriving one run earlier.

So **every Question Set carries a mandatory altitude answer**, and it is a **four-way disposition**,
not a specific-versus-general dial:

| `disposition` | The need is really… | Evidence required |
|---|---|---|
| `extend` | a fix or addition inside a tool that already exists | which capability, and why it belongs there rather than beside it |
| `new` | a genuinely novel capability | what existing capability was checked and why it does not cover this |
| `split` | a reason to break an existing tool into parts | which tool is doing too much, and the seam |
| `policy` | not a tool at all — a standing decision framework | what class of request it retires |

**`split` is the disposition that does most of the work**, and it is the mechanism behind
decomposing the twelve broad specialists: *the cheapest source of a real gap is removing a capability
from something that currently over-reaches.* `venue_finder` is a split of `logistics`, not a new
tool, and classifying it correctly is what keeps the registry honest about where capability came
from.

`new` carries the highest burden of proof precisely because it is the disposition a model reaches for
by default — it is the one that matches the literal shape of the request.

**Latency is the second constraint, and it binds the whole infrastructure.** A capability that makes a
conversation wait is worse than no capability. Three consequences, enforced as a declared field
rather than a convention:

| `execution_mode` | Meaning | Machinery |
|---|---|---|
| `blocking` | Runs inside the turn; must be fast | existing parallel fan-out |
| `deferred` | Dispatches, Synth says *"I'm looking into that — it'll be a moment"*, result arrives on a later turn | `context_block()` delivery, the horizon-ledger pattern |
| `background` | Never returns to a conversation | `fire_and_forget`, scheduler `function:` jobs |

**Every generated capability declares its mode and an expected latency budget.** Anything blocking
that exceeds the budget is rejected by the planner and re-planned as `deferred`. `deferred` is the
mode that makes narrow capabilities affordable at all — it decouples capability count from turn
latency.

**Tiering is the third constraint — the target architecture, not an optimisation.** Narrow
capabilities registered directly
under Coord scale the routing decision linearly with capability count — against a model chosen for
speed, reading a literal string list it must copy character-for-character, whose misses are already
a recorded, escalating failure class. It degrades well before "hundreds."

```
Coord ──► theme router (owns a domain, fans out, aggregates) ──► specialist (narrow, one job)
```

**A new capability registers with its theme router, not with Coord**, so Coord's list stays small and
stable permanently. **`request_build` is granted at both levels** — Coord files a gap when nothing
owns the request; a theme router files one when nothing *in its domain* owns it. The router-level
trigger is the higher-signal one, because the router knows the domain.

*Blocker this surfaces:* `run_subagent` is granted only to the Synthesizer and its depth guard
refuses at depth ≥ 1 ([`tools/subagent.py:38-46`](tools/subagent.py)), so a theme router calling a
specialist is blocked today. **The guard must become depth-aware rather than binary.** Scheduled with
the tier, not before.

> **Sequencing decision (Mike, 2026-09-17): leaf first, tier second.** Prove the registration matrix
> end to end on one small capability with an explicit gap and an explicit Coord instruction; then
> build the tier. Accepted cost: capabilities built before the tier are re-registered under a router
> when it lands — a mechanical change, and cheaper than trusting an unproven pipeline with a
> structural one.

---

## 3. The rule that generates the node graph

> A node is an **agent** only if its output is a judgment no deterministic procedure can produce,
> *and* its input can be made complete enough that the judgment is the only thing left. Everything
> upstream (assembly, retrieval, probing, condensing, counting, costing) and downstream (validation,
> partitioning, id assignment, file writing) is **code**.

The repo already voted for this. [`core/actions.py:1-30`](core/actions.py): *"Python generates it
from what the runtime observed, so it is evidence rather than a claim. No model is asked whether an
action happened."* The Build restatement: **no model is asked whether the data exists.**

Three artifacts, three agents. Agent count == artifact count is the rule's result, and it is the
answer to "why this many nodes."

```
 request_build (tool, granted to Coord AND theme routers)
        │                    ┌─────── HUMAN GATES ───────┐
        ▼                    │ N6 interview  N9 approve  N13 land │
 N0 intake ─► N1 manifest ─► N2 INQUIRY ─► N3 probe+condense ─► N4 LIBRARIAN
   (code)       (code)        (agent)           (code)            (agent)
                                                                     │
 N5 settle ◄─────────────────────────────────────────────────────────┘
  (code) ─► [N6] ─► N7 PLANNER ─► N8 cost ─► N8b review ─► [N9] ─► N10 brief
                     (agent)      (code)      (advisory)            (code)
                                                        │
                            N12 apply + verify (code)   [v3: N11 removed — the writer
                                                        │      applies what the Planner produced]
                                              [N13] ─► N14 close (code)

 N1r dossier (code, REPAIR only)        NC coherence (agent, periodic)
```

**N3 is the highest-value node and the one a shallow version omits**, and it does two jobs:

- **Probe.** The Librarian's hardest field is *"is this data available?"* A model asked that answers
  from its impression of what tools exist. Code answers exactly: resolve the manifest id → run a
  **code-chosen** read call → count rows. With N3, `data_available` is evidence; without it the whole
  ledger is a claim. This is `core/trace.py`'s `is_grounded()` lesson one layer up — *"we asked and
  nothing came back"* is a different state from *"this never retrieves."*
- **Condense.** A Librarian that can only fetch a named key is a lookup service. Research means range
  reads over 61 journal files and 44 days of conversation, distilled. Code fetches the range; a cheap
  local pass condenses to evidence; the Librarian adjudicates over evidence. **The expensive judgment
  stays on a small input while still seeing everything.**

**N8b is an advisory model pass** reviewing the drafted plan before Implementation begins, plus the
constitution read. Advisory, never blocking — a model judging its own output is the grade-your-own-
homework pattern; § 6.5(a)–(c) are the enforcement.

**N10 and N12 after option 1 `[v3]`.** N10 writes the approval brief Mike reads at [N9] and, for
every ledger row at `status: needs_tool`, a `needs_tool` brief (§ 4, § 11). N12 is one code node:
`writer.apply()` lands the Planner's agent-file text and overlay record, `verify.run_all()` runs
the sweep's checks over the tracked tree *and* the overlay, and a failing check calls `revert()`
before the node returns — so [N13] is Mike's acceptance of a capability that is already live in
the overlay, and a refusal at [N13] is a `revert()` too. No node writes a tracked file.

### How Build is triggered

`request_build(gap, trigger, mode)` — a registered tool that files a row and returns in milliseconds.
**Coord never speaks to a Build agent.** A scheduler tick later picks the ticket up, and *that*
process runs Inquiry → Librarian → Planner. Reasoning: specialist dispatch is synchronous inside one
user turn; a Build run is minutes and dollars, so a name in the valid-agent list would be a lie about
its cost.

Tickets land in `proposed`, not `queued`; Mike triages. **The redundancy record until Build is
proven `[v3]`** (Mike, 2026-09-17, mechanism re-chosen under ruling 0.1) is a `BUILD_PROPOSED`
quality event written beside the ticket: the VM has no write path to `DEV_BACKLOG.md`, but
`sync_dev_backlog.py:fetch_events` already pulls quality events over `/monitor/file`, so the event
reaches § Inbox on the next sync with one label added to its event map. Two records until one
earns trust — the second one carried by a path that already exists.

> **`[v3.7]` What counts as "the previous turn" has ONE definition, in
> `tools/turn_referent.is_exchange()`: a trace with a `coordinator` in its pipeline.** Two things
> write their own `RequestTrace` and are not turns — a `build_tick`, and the **Diarist**, which is
> fire-and-forget on its own thread and finishes AFTER the turn it followed, so it is routinely
> the newest record on disk when the next turn arrives. Both readers of that file use this rule:
> the correction attribution below, and `context_block()`, which had its own idea and announced a
> tick as *"the exchange immediately before this one"*. **A scheduled session passes** — it runs
> the full pipeline, and its specialist is what a user's next turn corrects.

**REPAIR is filed by code — and the signal it counts is now code-written too `[v3]`, finding 6.**
`write_quality_event(source_agent=…)` is model-filled today, and only the Coordinator and
Synthesizer hold the grant, so a capability answering wrongly emits nothing by itself. So: when
a turn carries a user correction, the orchestrator attributes the correction event to the
specialist(s) that ran on the **previous** turn — which `tools/turn_referent.py` already reads
from the trace — rather than to whichever head-layer agent noticed it. `build_tick` (not the Mac
sync script) imports `signature()` from `scripts/sync_dev_backlog.py`, collapses one recurring
fault to one signature per capability, and at **×3** for a capability in the Build registry files
a REPAIR ticket carrying the signature, the matching traces, and that capability's original
Question Set and Answer Ledger. No model decides this — it is counting. Run 2 in § 11 files its
REPAIR by hand from the board, because run 2 tests the dossier; the trigger is a separate, later
test.

---

## 4. The three artifacts

All carry `schema`, `job_id`, an upstream fingerprint, `generated_at`. Validators in
`core/build/schemas.py`.

### QuestionSet — an ordered spine, not a list

*Calibrated against the RSVP transcript (`archive/plans/inquiry_reference_rsvp_2026-09-17.md`), whose
turn-2 → turn-4 delta under the critique "you built a filter, not a compass" is the specification for
this artifact.*

```
mode, request, depth, disposition, disposition_evidence, generalizes_to,
manifest_fingerprint, policies_consulted[], framing_note,
spine[] (ORDERED), declined_to_ask[]

Question: id, text, class, why_it_matters, blocks: design|behaviour|neither,
          expected_answer_shape, candidate_sources[], resolved_by_policy: str|null
```

**Step 0 — proportionality. Inquiry decides its own depth before asking anything.**

| `depth` | When | Shape |
|---|---|---|
| `triage` | a standing policy already covers this class of request | resolve against policy; 0–3 questions; no Librarian pass |
| `standard` | ordinary new capability | the full spine, one pass |
| `deep` | irreversible, cross-cutting, or precedent-setting | full spine + explicit alternatives + escalation note |

This is the transcript's own closing discipline — *"if I run this depth of analysis on everything,
I've become another thing consuming his scarce resource."* It is simultaneously the compass rule and
the cost control, which is why it is step 0 and not a config knob.

**The spine is ordered, and the order is the design.** Turn 4's amended decision spine puts
feasibility **fourth**; turn 2's put it first, and that single inversion is the difference between the
two answers.

| # | class | Asks |
|---|---|---|
| 1 | `integrity` | What on the face of this request does not cohere? (*"August 22 2026 is a Saturday"*) |
| 2 | `intent` | What is this in service of? What has the user said they want more and less of? Where do stated and revealed preferences diverge? |
| 3 | `cost` | What does acting consume that nothing meters — empty time, attention, social energy, a reciprocity obligation that outlives the act? What is the base rate and the marginal value at that rate? |
| 4 | `asymmetry` | Is anything here irreversible or closing? Regret in **both** directions? |
| 5 | `feasibility` | Can it be done, at what cost to what surrounds it? |
| 6 | `surface` | What else operates on this once it exists — move, delete, dedupe, merge, expire, reconcile? What will this reasonably also be asked to do? What breaks if it exists and nothing else changes? |
| 7 | `minimum_version` | What captures most of the value at a fraction of the cost? |
| 8 | `authority` | What is decided here versus surfaced — and what is the **stated default so that silence still produces an outcome**? |

**Hard constraints.** `disposition` set with non-empty evidence · `spine` ordered by class index · **no `feasibility`
question may precede an `intent` question** · ≥1 `intent` · ≥1 `surface` · ≥1 `authority` at
`depth != triage` · dense unique ids · `candidate_sources ⊆ manifest_ids ∪ {"user"}` · token-set
dedupe, becoming semantic dedupe against every question ever asked once Build's own index exists
(§ 9) `[v3]`.

**The ordering constraint is the one to defend.** *"Don't build a filter, build a compass"* is prose,
and this repo has a long record of prose being ignored where a mechanism would have held — the
canonical case is [`tools/logger.py:411`](tools/logger.py)'s docstring: a `USER_CORRECTION:` slot
annotated *"omit if not applicable"* produced 93 of 174 events reading `"None."`, because **a model
filling a structured template answers the slot rather than deleting it.** A tag saying `kind:
orienting` has exactly that shape — it is a slot to fill. **Position cannot be faked**: a question
placed before feasibility had to be thought of first.

**Two stances inherited by generated capabilities, stated in their agent files.**
- **Neutral is not a pass.** Absence of a blocker is not a reason to act; the burden of proof sits on
  action. A capability that does nothing when nothing blocks is a filter.
- **Empty capacity is not available capacity.** Unstructured time, unspent attention and unclaimed
  budget are assets to defend, not gaps to fill.

**Inquiry asks freely — cost is in adjudicating, not asking.** Soft ceiling ~25; the prompt says
plainly that a large set is fine and a short one is also fine. N3 settles everything already
answerable — **first against standing policies, then against data** — and only the residue reaches
the Librarian. **This gets cheaper by construction**: every policy a prior run produced retires a
class of question permanently, which is the real mechanism behind questions arriving pre-answered.

### AnswerLedger

```
rows[] (one per question), interview_items[], variable_proposals[], surface_map
LedgerRow:
  model-written:  answerable_by: data|judgment · data_kind: single_point|behavioural|none
  CODE-written:   data_available · evidence[{source, tool, probe, rows, sample_ok}] ·
                  condensed_from (n records)
  judgment:       has_what_it_needs · decision · decision_options[≥2] · assumption ·
                  assumption_falsifier
  home:           data_home · variable_scope: all_personas|this_persona|query_only · variable_name
  CODE-derived:   status: settled|needs_interview|needs_tool
```

**Model values in the code-written block are stripped before validation and re-injected from N3.**

Hard: one row per question · judgment ⟹ decision + ≥2 options + assumption · `variable_name` valid
**and not already declared** in the target file · `data_home` resolves.

**Declared-variable homes — rewritten under option 1 and finding 3.** Two of v2's three homes
sat on the writer's own deny list (`config/personas/**`) and the third is a tracked file. So a
declared variable is never file-written by Build. It is declared through the write path that
already exists for that home, or it becomes a brief:

| `variable_scope` | Home | Declared by | v1 |
|---|---|---|---|
| `this_persona` | `config/personas/{p}/profile.yaml` | the existing `write_profile` tool (`tools/profile.py:217`), called by N12 with the ledger's value, through its confirm gate | live |
| `query_only` | the wisdom store | the existing `write_wisdom` tool (`tools/wisdom.py:549`), filed under an existing domain with `provenance: build:{job_id}` | live |
| `all_personas` | `config/templates/profile.yaml` — **tracked** | nobody on the VM; the row parks the job at `needs_interview` and N10 emits a promotion brief Mike applies on the Mac | brief only |

`variable_name` uniqueness is checked against the live home by reading it (`read_profile`,
`read_wisdom`), not against a Mac copy. **A declared variable may be a scalar, an array, a list,
a table or a record set** — `type: string|number|boolean|enum|list|object|table|record_set`, with a
shape declaration for the multi-item forms; the multi-item forms are `query_only` in v1 because
`profile.yaml` fields are scalars.

**`status: needs_tool` is how Build builds its own substrate.** The known Librarian gaps (§ 9) will be
hit on run 1 and are expected, not failures.

### BuildPlan

```
capability{id, kind, one_line, replaces[], execution_mode, latency_budget_ms, theme,
           disposition, disposition_evidence, generalizes_to}
disposition: extend | new | split | policy      ← from the Question Set, § 2
kind: tool | agent | policy | function_job | context_block | check
surface_map[]                       ← REQUIRED
policy{}                            ← REQUIRED when kind == policy
files[] · registration[] · tests[] · acceptance{} · variables[] · state_record{} · risks[]
estimate{}                          (CODE-written at N8; model values stripped)
```

**`kind: policy` is a first-class output, and often the right one.** The RSVP transcript's own
conclusion — *"the actual first-day deliverable is not an RSVP; it's the beginning of a standing
allocation policy"* — is the general case. A policy is a stored decision framework plus the fast
triage path that consumes it:

```
policy{id, domain, applies_to, standing_commitments[], automatic_yes[], automatic_no[],
       budget{unit, period, limit}, escalation_threshold, default_on_silence,
       review_date, authored_with_user: bool}
```
Policies live under `data/personas/{p}/build/policies/` `[v3]` — persona-scoped, gitignored,
backed up, inside the writer's allow-roots — and **enter the capability manifest**, so N3 resolves
against them before touching data.

**What a policy is actually for: capabilities that improve with use.** A tool that consults an
accumulating policy gets better at its job the more often it runs — the policy is where the
corrections, the standing commitments and the automatic yeses and noes accrete. Making Inquiry
cheaper and `depth: triage` possible is a **side effect** of that, not the purpose. A capability
without a policy behind it performs identically on its thousandth run as on its first, which for
anything exercising judgment is a defect.

A policy carries a `review_date` for the same reason every threshold in this project does — a number
standing in for judgment needs an owner and a re-check date.

**`disposition_evidence` is required for every disposition**, per the table in § 2, and
*"it is what was asked for"* fails validation for `new`.

---

### The ledger compiles into the capability

**The Answer Ledger is not build-time scaffolding that gets discarded — it is the specification of
the capability's runtime behaviour.** This is the property that makes the whole design affordable
under the latency constraint.

| Ledger field | Becomes, in the built capability |
|---|---|
| `data_home` | a resolved data binding — the tool knows where to look, with no discovery step |
| `evidence[].tool` + `probe` | the actual read call it issues |
| `decision` + `decision_options` | a decision gate with its branches already enumerated |
| `assumption` + `assumption_falsifier` | what it re-checks, and what would tell it it is wrong |
| `variable_name` / `variable_scope` | the declared field it reads or writes |
| `surface_map` | which operations it implements and which it must refuse cleanly |

So the expensive part — working out what to ask, where the data lives, and what the discrete decision
is — happens **once, at build time, at whatever depth the request deserved**. At runtime the
capability executes a resolved plan against bound data. **That is how a narrow capability performs
deep analysis inside a latency budget**, and it is why `depth: deep` at build time does not translate
into a slow tool. It also means a capability can implement a policy directly rather than reasoning
its way to one on every call.

Corollary for REPAIR: when a capability behaves wrongly, the ledger row that produced the faulty gate
is **identifiable** — which is what makes *"the question that wasn't asked"* a diagnosable claim
rather than a metaphor.

**The surface map is a required section and it closes a real gap.** Librarian surfaces questions to
*answer*; nothing enumerated the **processes that must exist and their edges**. Scheduling is the
worked example: a calendar entry needs delete, move, dedupe and reconcile, not just create — and none
of those arise from asking "what do I need to know?"

```
surface_map[]: {entity, operation, status: in_scope|deferred|not_applicable, reason|ticket}
operations: create · read · update · delete · move · dedupe · merge · expire · reconcile
```
**Nothing may be silently absent** — every operation is listed with a disposition. Deferred needs a
ticket; not-applicable needs a reason. This is the anti-drift mechanism at capability level,
complementing the coherence review at system level.

### The registration matrix — rewritten for the overlay

Registration is no longer a checklist of edits to tracked files. It is **one record**, written by
the writer into the overlay, that the four load seams (§ 6.5) read. The matrix is the record's
required fields, validated by `schemas.py` and re-validated by `check_build_registration.py`.

**Which kinds and dispositions the writer accepts in v1:**

| `kind` | v1 | Lands as |
|---|---|---|
| `agent` | yes, `disposition: new` only | overlay agent file + overlay capability record |
| `policy` | yes | a policy record under `build/policies/` + a manifest entry |
| `tool` · `function_job` · `check` · `context_block` | **no — needs code** | a `needs_tool` brief (N10); the job parks at `briefed` until Mike's build lands and the ticket is re-run |
| any kind with `disposition: extend` or `split` | **no — needs a tracked-file edit** | parks at `plan_ready` with a promotion brief; unlocked by the § 11 promotion gate |

**`kind: agent` — the overlay capability record**, `overlay/capabilities/{name}.yaml`:

```yaml
schema: overlay_capability/1
name: home_care                    # ^[a-z][a-z0-9_]{2,31}$ · ∉ routing.yaml ∪ routing_cloud.yaml ∪ config/agents/*.md stems
display_name: "Home Care"          # what the Coordinator copies character-for-character
job_id: BLD-0925-01 · version: 1 · generated_at · agent_file: agents/home_care.md · agent_sha256
routing:                           # BOTH entries, one record — parity is a schema property
  local: {local: true, allowed_tools: [...]}
  cloud: {provider: gemini, model_ref: mental_wellbeing, allowed_tools: [...]}
coordinator:
  directory_entry: |               # the § Specialist directory paragraph, same shape as coordinator.md's
    **Home Care**
    Call when: ...
unavailable_consequence: "their household upkeep and what is due around the home"
confidential_names: [home_care]    # appended to _CONTEXT_SENSITIVE at filter time — never _ALWAYS_CONFIDENTIAL
knowledge_domains: [home]          # ⊆ tools/wisdom.py DOMAINS; adds this agent to those domains
execution_mode: blocking · latency_budget_ms: 8000
```

Four fields carry a reason. **`confidential_names` go to the sentence-gated list, not the
unconditional one** (Opus finding 1): `_ALWAYS_CONFIDENTIAL` is for identifiers *"impossible in
natural prose"* and one substring hit replaces the whole reply with the canned fallback — and
its matcher joins tokens across up to four punctuation characters or none, so `home_care`
suppresses *"your home-care tasks"* and a single-word name like `garden` suppresses every
reply containing that word. `_CONTEXT_SENSITIVE` (`core/orchestrator.py:1415`) fires only inside
a sentence carrying architecture vocabulary, which is exactly the mechanism for a name that is
also English, and it is already built and tested. **`model_ref`, not a model id:** model ids have a short half-life
here — the reasoning tier moved twice in four days this month (`SESSION.md` § Model IDs) — and a
generated record pinning one would strand the capability on a retired id with nobody editing
it; seam 2 resolves the ref to the named tracked agent's live model at load time. **`allowed_tools`
identical in both entries and both ⊆ the read set** (§ 6.3) — and the agent file may name only
tools in that list, which is `check_agent_tools.py`'s existing class check run over the overlay.
**`name` must not collide with any tracked name in any of three places** — the agents in
`routing.yaml`, the agents in `routing_cloud.yaml`, and the stems of `config/agents/*.md` — and
`check_build_registration.py` re-asserts the same three-set rule (Opus finding 5). The routing
files alone are not enough: `time_director` and `goals_interview_reference` have agent files and
no routing entry, so a record named `time_director` would pass a routing-only check and then be
split across the seams — seam 1 loads the **tracked** prose, seam 2 merges the **overlay's**
tools and model — which is precisely the half-wiring cited above. Tracked wins in every seam, so
a collision would land a record nothing ever loads whole; the writer refuses it up front.

**`kind: policy` — the policy record** is the `policy{}` block above plus `job_id`, `version`, and
`retires_question_classes[]`; it needs no seam, because only Build's own N3 reads it.

**Live evidence that humans do not complete this checklist reliably:**
`config/agents/time_director.md` exists, `_AGENT_NAME_MAP` maps to it,
`_UNAVAILABLE_CONSEQUENCE` carries a line for it — and it appears in **neither** routing file nor the
Coordinator's name list. Anything naming it raises at
[`core/router.py:112-117`](core/router.py). A half-wired agent is in the tree today. One record
with required fields is the answer to that class of defect, not a longer checklist.

`state_record` is required whenever any planned file writes under `data/`, enforcing requirement 3
without retrofitting anything.

---

## 5. The job record and the board

**Id:** `BLD-MMDD-NN`, deliberately the shape of `DB-MMDD-NN`. Sequence allocated by replaying
today's rows under a lock, so collision across a restart is structurally impossible.

```
data/personas/{p}/build/ledger.jsonl     append-only, replayed — the state
data/personas/{p}/build/registry.jsonl   capability id -> files, job, theme, version
data/personas/{p}/build/jobs/BLD-.../    request · manifest · question_set · evidence ·
                                         answer_ledger · build_plan · brief · verification · undo
docs/BUILD_REGISTRY.md                   tracked — generated on the MAC by build_board.py --registry
                                         from registry.jsonl (ids, kinds, names, versions, dates —
                                         zero persona content); Mike commits it [v3, ruling 0.2]
```
Copies [`tools/crm_sweep.py:276-297`](tools/crm_sweep.py) exactly — status reconstructed by replaying
rows, no separate status file, malformed line skipped not fatal. Its reason carries over: *"a status
file that disagreed with the ledger would be worse than no status file."*

**States:** `proposed → queued → inquiry → questions_ready → librarian → ledger_ready →
[needs_interview] → planning → plan_ready → [awaiting_approval] → briefed → executing → verifying →
landed | failed`. Terminal: `landed`, `failed`, `abandoned`, `superseded`. **`blocked` is a flag on
the row, not a state** — `DEV_BACKLOG.md`'s `@waiting:` convention, which that file calls *"a property
of items already counted, never a new section."*

**Restart survival:** no in-memory state. **The state is the resume cursor** — every node is
idempotent, writing `<artifact>.json.tmp` then `os.replace()`, and a node finding a valid output
already present skips the model call. A 30-minute `build_tick` re-enters jobs whose heartbeat exceeds
45 minutes at `attempt += 1`.

**Dedupe:** `sha256(mode|_norm(gap)|capability_hint)`, refused against any non-terminal job, a
`landed` job inside **14 days**, a `failed` job inside **72 hours**. Both chosen, not defaulted.

**Depth:** a durable ledger field, `MAX_BUILD_DEPTH = 2`. Strictly better than `_SUBAGENT_DEPTH`,
whose known hole is that `_dispatch_from_coordinator` never sets it — a ledger field cannot be lost
across threads or processes.

**Caps:** `max_open_jobs: 3 · max_proposed: 12 · max_jobs_per_day: 4 · max_build_depth: 2`.

**Two surfaces for Mike, because he uses both.** `tools.build.context_block()` added to the
`_block_source` tuple at [`core/orchestrator.py:1049`](core/orchestrator.py) for conversational
surfacing; and `scripts/build_board.py` + `scripts/build_brief.py` for working Build directly from
Claude Code, which is the primary interface during bootstrap.

---

## 6. The choke-point writer — `core/build/writer.py`

`apply(job_id, plan, edits, dry_run=False)` and `revert(job_id)`. Refusals return explanatory strings,
never raise — house style. **Everything it writes lands under two roots and nowhere else:**

```
data/personas/{p}/build/jobs/{job_id}/     artifacts, brief, undo journal
data/personas/{p}/build/overlay/           agents/{name}.md · capabilities/{name}.yaml
data/personas/{p}/build/policies/          policy records
ledger.jsonl · registry.jsonl              append-only, own appender, never through apply()
```

**Why the overlay is under `data/personas/{p}/` and not a new top-level directory.** Three
reasons, in order of weight. The compiled agent text is persona-derived — the ledger it is built
from is drawn from the corpus — so it is Sensitive-tier content and belongs inside the persona
tree, not in a global directory that happens to be gitignored. `data/personas/*/` is already
gitignored (`.gitignore` § personas) and already in `scripts/metatron-backup.sh:83`'s tar list,
so the overlay needs **no new ignore rule and no new backup entry** — two lists that could drift
are two lists not added. And the seams resolve the persona from thread scope through
`resolve_persona()` — with one decision stated as the decision it is (Opus finding 6):
**`load_overlay()` catches `PersonaError` and returns `{}`.** `resolve_persona()` raises when
nothing is bound (`core/persona.py:183-187`), neither `load_agent(name)` nor `_load_routing()`
takes a persona, and `resolve_model()` is called today with none bound
(`tests/test_a4_complexity_threading.py:107-108`) — so letting the error propagate would make a
tracked agent's routing raise where it does not, and that is a change to the Red-tier path, not
an inheritance. No persona in scope → no overlay; every tracked behaviour exactly as before.
`config/personas/{p}/` was the review's cited pattern and was
rejected only because it sits on the writer's own deny list and finding 3 kept it there.

> **Corrections recorded deliberately — v3.2, 2026-09-19, after the phase 3 second-model
> review.** Six defects, all confirmed and all fixed in the writer, `schemas.py` and the seams.
> Each is recorded here for the same reason § 8's correction is: the spec was followed and the
> spec was what was wrong, so a session reading only the prose above would rebuild the defect.
>
> 1. **The undo journal was a way around all three path rules.** `revert()` replayed whatever the
>    journal named, and the journal is a file inside an allow-root — so anything able to write one
>    entry could name any path on the machine and have `revert()` act on it. § 6.7's *"the journal
>    is the only undo"* described the mechanism and never said the journal is not itself an
>    artifact. **Now:** `apply()` refuses any `undo.*.jsonl` under the job directory, and
>    `revert()` runs `check_path()` on every entry before restoring — allow-roots only, never a
>    tracked path, never a deny-list path; an entry that fails is logged and skipped. Fail-closed
>    when `git` cannot be asked: a revert that cannot verify its paths does nothing and says so.
>
> 2. **`name` was checked against three sets and `display_name` against none.** But `display_name`
>    is the string the Coordinator copies and the string seam 3 splices into the closed valid-name
>    list, and it resolves to an agent name through `_normalize_agent()`'s generic fallback whether
>    or not anything registered it. A record displaying `"Mental Wellbeing"` put a duplicate in
>    that list and pointed its directory entry at a tracked agent — shadowing through the one field
>    the collision rule did not cover. **Now:** refused at schema time when the normalised display
>    name matches a tracked agent, a `_AGENT_NAME_MAP` key or value, or a display string in
>    `coordinator.md`'s closed list; seam 3 skips such an addition independently, so schema and
>    seam agree. `_AGENT_NAME_MAP` moved to module scope to make both checks possible — and
>    callers now take a copy, which also closes a cross-persona leak the in-function literal had.
>
> 3. **Both tool scans required backticks.** `send_email` written as ordinary prose passed every
>    gate. § 6.3's *"the same regex `check_agent_tools.py` already runs"* is what carried the
>    limitation in. **Now:** the writer's scan matches any live `register_tools()` name as a bare
>    whole word, backticked or not — safe precisely because the candidate set is the live registry,
>    where every name is snake_case and none is an English word.
>    **`scripts/check_agent_tools.py` is deliberately unchanged and still shares the gap**: on a
>    tracked file the evidence gate is what keeps 34 field names out of the report, and that trade
>    is right there and wrong only here.
>
> 4. **The narration scan read the agent file only.** Three record fields are prompt text too —
>    `display_name` and `coordinator.directory_entry` are spliced into the Coordinator's system
>    prompt by seam 3, and `unavailable_consequence` reaches the Synthesizer by seam 4 — and none
>    was scanned, so a record could carry the leak its agent file was refused for. **Now:** all
>    three are scanned whole (not only inside quoted spans, as the agent file is — these fields are
>    short and entirely prompt-facing), and `display_name` is restricted to letters, digits, spaces
>    and `&`, because it lands inside a quoted item in a closed list where a backtick or a newline
>    rewrites the sentence rather than merely looking odd.
>
> 5. **`model_ref` governed the model and never the provider.** The record always carried a
>    `provider`, and seam 2 merged it with `setdefault`, so the record's value always won: a
>    capability could name a sensible tracked agent for its model and still route itself to another
>    vendor, with every individual field reading correctly. **Now:** a `provider` on the record is
>    refused at schema time; seam 2 discards any it finds and takes provider *and* model from the
>    tracked agent. A `model_ref` must also name an agent present in **both** routing files — one
>    present in only one resolves under one `DEPLOYMENT_MODE` and vanishes under the other, which
>    is the split the single-record shape exists to make impossible.
>
> 6. **`find_places`'s condition was prose.** § 6.3 says a capability wanting it *"must list it in
>    `risks[]`, which N8b reads and the brief shows Mike"* — and nothing enforced that, so the one
>    outbound grant whose exposure depends on a human seeing it was handed out as silently as any
>    other. **Now:** `apply()` reads the plan, and a conditional grant with no matching `risks[]`
>    entry naming it is refused. Checked against the plan and not the record, so a capability
>    cannot vouch for itself.
>
> **What the six have in common, which is the finding above the findings:** every one is a place
> where the plan stated a rule in prose and the implementation honoured the prose exactly. The
> rules that held were the ones already expressed as a mechanism. That is this project's own
> standing lesson — *six of six of Mike's 2026-08-21 complaints were rules already written in
> `synthesizer.md` and ignored, while every rule moved to Python held on first contact* — arriving
> one layer up, in a plan rather than an agent file.

> **Corrections recorded deliberately — v3.3, 2026-09-19, after the review's Part 2 re-check.**
> The six above were confirmed closed. Five more were found BESIDE them — four introduced or
> left by the fixes themselves, one an observation about the second line. Recorded here for the
> same reason: the prose was followed and the prose was incomplete.
>
> **The shape they share, and it is not the shape the first six shared.** Those six were prose
> that was never made mechanism. These five are mechanisms that were made, and scoped to the
> case that prompted them. Defect 2 stopped a generated capability capturing a TRACKED agent's
> dispatch and said nothing about a second generated capability capturing the first one's.
> Defect 4 scanned record fields against the static confidential list, not the live registry the
> sibling gate reads. Both closed the reported case exactly. **A fix scoped to its probe is the
> characteristic second-round defect, and the second landed capability — § 11's bootstrap
> sequence — is where the first of them arrives.**
>
> **N1. One generated capability could capture another's dispatch.** Display-name uniqueness was
> checked against tracked names and the closed list, not against other overlay records. Two
> capabilities displaying `Home Care` both landed: `coordinator_additions()` returned the string
> twice and the name map kept one winner, chosen by sort order. A capability displaying `Garden`
> beside one named `garden` captured it outright. **Now:** refused at schema time against every
> peer record's display AND every peer record's name, with peers computed from the overlay on
> disk plus the other records in the same `apply()`; seam 3 drops a duplicate independently
> through one `accepted_displays()` filter that both halves of the seam read, so the closed list
> and the name map cannot disagree about which capabilities exist. First wins by sorted name, so
> the outcome is stable across a restart.
>
> **N2. A look-alike of a tracked display name landed.** `Mental  Wellbeing` — two spaces —
> satisfies the charset, normalises to `mental__wellbeing` which is not tracked, and lowercases
> to a string the reserved set does not hold. It spliced into the closed list one space from the
> real entry, on the model whose own map comment records that it cannot reliably copy that list.
> **Now:** every display-name comparison runs on a collapsed, case-folded form, so a name
> differing from a reserved one only by whitespace or case is refused.
>
> **N3. The two identifier gates read different sets.** `_check_record_fields()` matched
> `_ALWAYS_CONFIDENTIAL`, which carries 37 of the 78 registered tool names — so
> `unavailable_consequence: "their send_email digest"` landed in prompt text while the
> agent-file grant gate refused the same token. § 12's *"a confidential identifier in
> `unavailable_consequence` must fail"* held for `routing.yaml` and failed for a tool name, which
> is the canonical confidential identifier. **Now:** the record-field gate reads the live
> `register_tools()` set through the same `_registered_names_in()` the grant gate uses, in
> addition to the static list.
>
> **N4. The journal rule was case-sensitive on a case-insensitive filesystem.** `Undo.jsonl`
> passed `check_path()` and is the same inode as the journal on APFS. `revert()`'s new path rules
> stop a forged journal reaching a tracked or denied file, so the blast radius was already
> bounded — but it could still restore arbitrary bytes into another capability's overlay agent
> file, bypassing every content gate. Not reachable on the VM, where ext4 makes it a different
> file; recorded because **the tests run on the Mac and a fixture-green result would not have
> shown it.** **Now:** the name test is case-insensitive, and where both files exist the paths are
> compared by inode.
>
> **Observation 2 — the second line looked for less than the first.**
> `scripts/check_build_registration.py` called the validator with `tracked_names` alone, so the
> sweep re-asserted the three-set `name` rule and neither of the rules added for N-round defects
> 2 and 5. Independent re-assertion is that script's entire job, and a narrower one is a false
> reassurance. **Now:** it passes `reserved_display`, `model_ref_names` and `peer_displays`, so
> every rule the writer enforces at write time is checked again against what is actually on disk.
>
> **Two things the review raised that are NOT changed, both deliberate.**
> `revert()`'s summary still opens with `reverted —` even when every entry was skipped; the
> `SKIPPED` clause is the signal, and phase 4 is where a caller will read it — noted here so that
> caller keys on the clause rather than the prefix. And `scripts/check_agent_tools.py` still
> requires backticks on the tracked tree, by the standing decision that its evidence gate is what
> keeps 34 field names out of that report; the writer's bare-word scan is the only line for bare
> names, and a hand-placed overlay file is not re-checked for them.

> **Correction recorded deliberately — v3.4, 2026-09-19, after the review's Part 3 re-check.**
> The five above were confirmed closed. **One finding, and it is the same fault the v3.3 round
> was written to remove, surviving in the last place nobody re-read.**
>
> **P3-1. Seam 3 resolved a display name without collapsing its whitespace.** The schema
> collapses before every display-name comparison — that WAS the N2 fix — and
> `_resolves_to_tracked()` kept resolving the raw string. So a hand-placed record displaying
> `Mental  Wellbeing` normalised to `mental__wellbeing`, missed the tracked set, and was
> surfaced into the closed valid-name list beside the real entry. **Now:** the seam imports the
> schema's own `_collapse` and `_resolve_display` through one `_display_helpers()` pair, so
> there is a single definition of the normalisation behind both checks rather than two that
> agree until one is edited.
>
> **Why it is worth a correction entry despite its reach.** The writer refuses such a record
> (N2) and the sweep's overlay pass flags it (observation 2), so this needed BOTH existing lines
> bypassed to matter. What makes it worth recording is not the exposure: it is that seam and
> schema agreeing *independently* is the property this whole correction sequence set out to
> establish, and the fix that established it in the validator did not reach the seam that was
> supposed to be checking the validator. **A rule duplicated in two places is a rule that holds
> until one copy is improved** — which is why the fix is a shared import and not a second
> collapse call.
>
> **The sequence, stated once so the shape is legible:** round one was prose never made
> mechanism; round two was mechanisms scoped to the probe that prompted them; round three was a
> mechanism improved in one of its two homes. Each round's defect class is the previous round's
> fix, examined one level closer.

> **Corrections recorded deliberately — v3.6, 2026-09-19, after the phase 4 review.**
> Fourteen findings, all confirmed by a reviewer who RAN the runner, all fixed. Grouped by what
> each one broke; the full probe evidence is in
> `archive/plans/build_phase4_runner_review_2026-09-19_fable-5.md`.
>
> **The shape, and it is a new one.** Every defect here is a mechanism that was **never
> exercised**. Round 1 was prose never made mechanism; round 2, mechanisms scoped to the probe
> that prompted them; round 3, a mechanism improved in only one of its two homes. These read
> correctly and had never once run — which is precisely what a review that executes finds and a
> review that reads cannot.
>
> **THE ONE THAT COULD HAVE DESTROYED WORK.**
>
> **D1. `refuse()` reverted ANY job, including a landed one.** `approve()` and `accept()` both
> checked state; `refuse()` checked nothing. `build_board.py --refuse` with a mistyped id deleted
> a live capability's overlay files while the registry went on saying `landed` — an orphan the
> coherence pass would report, and no way back: the files were new, so the undo journal holds no
> `bytes_before`. **The one irreversible board command was the one without a guard.** Now: only
> `briefed` and `verifying` — the two gates where a refusal means something — and a terminal job
> is refused by name.
>
> **THE TWO THAT MADE A GATE UNREACHABLE.**
>
> **D2. A job crossing its limit DURING a call was failed terminally, not parked.** Pre-node
> refuses to start; nothing caught what the call itself crossed. The crossing surfaced at the
> Planner's `writer.apply(dry_run=True)` file check, whose job gate refuses on spend; the planner
> read that as a plan defect and rung 3 failed the job — past `awaiting_approval`, the one state
> that exists to let Mike raise the limit, leaving `cost.approve_limit()` nothing to release.
> **With the $2.50 placeholder this was the likeliest way run 1's budget question got answered.**
> Now: a **post-node** budget gate parks what the call crossed, and a dry run is not budget-gated
> at all — it writes nothing and costs nothing.
>
> **D7. A job parked above the ceiling could not be resumed.** `resume()` sent every job to
> `planning`; a job parked at N12 came back with every artifact present, skipped every node, and
> stalled — N12 runs from `executing`, `approve()` wants `briefed`. The `PARKED` message's *"raise
> the flag on the VM to proceed"* led nowhere without ledger surgery. Now: parking records
> `resume_to` on the status row and `resume()` returns there; a later transition clears it, so a
> stale target cannot send a second resume to the wrong node.
>
> **THE FOUR THAT MADE A MECHANISM INERT.**
>
> **D3. Correction attribution blamed whatever wrote the newest trace.** `last_trace()` returns
> the most recent record, and the **Diarist** is fire-and-forget on its own thread with its own
> `RequestTrace`, finished *after* the turn it followed — so the record on top when a correction
> arrives is plausibly the Diarist's, or a `build_tick`'s. REPAIR counts `source_agent ∩
> registry`, so a mis-attributed correction never reaches three and **the trigger this
> attribution exists to feed was inert.** Now: scan back for the newest record that is not
> proactive and carries a `coordinator` — the only shape a real exchange has.
>
> **D6. The coherence model pass dropped every well-formed reply.** The prompt asked for a JSON
> list; `repair_json` — built for context blocks, which are objects — extracts the first `{…}`
> from a list and returned the first *finding* as a dict, so `.get("findings")` was None and every
> reply was rejected as *"findings is not a list"* with `model_ran: True` beside it. The board
> read as a review that ran and found nothing. Now: the prompt asks for an object AND both shapes
> parse, because a parser must not depend on a model following a format instruction.
>
> **D8. REPAIR filed a fresh ticket for every correction after the third.** The gap text embedded
> the count, and `create()` fingerprints the gap — so ×4 hashed differently, escaped the dedupe
> and filed again. Nine more corrections fill `max_proposed` with one fault. Now: the gap is the
> fault; the count is evidence and lives in `trigger`, which is not fingerprinted.
>
> **D13. [N6] was unreachable in conversation.** The context block named the job and the gap but
> not the **questions**, and a parked job has no `brief.md` — the writer refuses that write by
> design. The questions existed only in an artifact on disk. Now the block carries them.
>
> **THE THREE ABOUT SAYING WHAT HAPPENED.**
>
> **D11. A writer crash read as a successful apply.** `apply()`'s exception path returns
> `"{job_id}: writer failed and reverted — …"`, which starts with neither `PARKED` nor `REFUSED`,
> so N12 ran the full 18-check sweep against an overlay that was never applied and put
> `capability-tests FAILED` on the board while *"disk full"* went nowhere. Now N12 **checks for
> the success prefix** rather than matching known failures — a whitelist of one cannot be outgrown
> by a new failure mode.
>
> **D9. The run line's expected figure was the Coordinator's turns per day**, identical for every
> capability regardless of what filed it, and `0.0` on a fresh persona — the *"it never fires"*
> verdict its own docstring forbids inferring from an inability to count. Now `None`, and the
> figure is owed to whatever phase gives a trigger an identity. The **actual** count is measured
> from day one and is the number that matters.
>
> **D14c.** `_reject` said *"rejected after retry"* on the dry-run path, where no retry ran.
>
> **THE THREE THAT WERE NEVER WRITTEN AT ALL.**
>
> **D5. Coherence could not see a surface map, so its overlap detector never fired.**
> `record_landing()` wrote none and the overlay record has no such field, so the corpus carried
> `surface: []` for everything — and § 13.7's own falsifiable example, *"both claim `create` on
> `plant_watering`"*, was the one comparison the pass was structurally unable to make. Now the
> registry row carries `{entity, operation, status}` triples; the model's `reason` prose stays
> out, because that row is rendered into a **tracked** file.
>
> **D10. Two Build events in one trace collapsed to one.** `write_quality_event` dedupes by event
> type per trace — right for a correction with two legitimate writers, wrong for events carrying
> their own job id. Two jobs failing in one tick recorded one `BUILD_CHECK_FAILED`, so the second
> capability's revert had no signal **in exactly the turn the redundant record was meant to earn
> its keep.** Now both Build types are exempt by name; the original guard is intact, not widened.
>
> **D14a. Every brief write after N10 was silently refused.** `WRITABLE_STATES` is
> `{briefed, executing}` and each call site set the new state first, so the landed brief still
> said `State: briefed` with no Verification section — the one thing [N13] reads — and a revert
> deleted it along with the failing output the next attempt was supposed to carry. Now the brief
> is written **before** the state moves and **after** any revert. **`_write_partial_brief` was
> removed rather than fixed**: every one of its three call sites parked the job first, so it could
> never once have succeeded. Widening the writer's gate for a convenience was the alternative and
> was rejected — what carries a parked job's reason is the context block and `--show`, both of
> which read live and cannot go stale.
>
> **D4 IS NOT ONE ENTRY. IT IS TWELVE, AND THAT IS THE FINDING.** The review reported that `log`
> — the primary corpus — probed as `error` on every question, because `{"days": 14}` fits no
> signature of `get_log_window(start_date, end_date, …)`. Fixing that one entry would have been
> the round-2 mistake exactly. A test that **binds every source's fixed arguments against its
> handler's real signature** found eleven more: `memory`, `archive`, `calendar`, `email`,
> `intake_queue`, `agent_config` and five outbound feeds. Nearly half the table.
>
> The five that needed a real-world argument — a flight number, an origin, a city — led somewhere
> the plan had not looked. **Probing a live feed is wrong three ways, and the first costs money:**
> it makes a real third-party call per question, every job, during Inquiry, which § 14 never
> priced; there is no honest code-written default for its argument, and `find_places` would send
> the invented string outbound; and *"is there a corpus here"* has no meaning for a source whose
> answer exists only when asked. So the seven outbound reads are declared `live: True` and **are
> never called by a probe** — a fifth state, reported as its own thing so it can never read as
> `no_data`, which would mean "there is nothing there" about a source that answers every time.
> Availability for a live feed **is** its registration.
>
> **D12. Every documented VM command failed with `PersonaError`** unless `METATRON_PERSONA`
> happened to be in the shell — including the ssh one-liners in C2 above, where a traceback is the
> least useful possible output. Both scripts now resolve the persona first and say what to pass;
> every usage example, and the context block's own command, carries `--persona`.
>
> **D14b.** `_index_questions` passed the persona into `add_question`'s `question_class` slot, so
> every indexed question carried `class: "mike"` under the scheduler and the whole write was
> logged as *"skipped: No persona resolved"* from the board. Keywords now.

> **Corrections recorded deliberately — v3.7, 2026-09-19, after the review's Part 2 re-check.**
> The fourteen above were confirmed closed and nothing that held was reopened. Three items were
> left open; all three are fixed, and **two of them are the round-3 shape: a rule that reached one
> of its two homes.**
>
> **N1. The landed brief said `executing`.** The v3.6 fix for D14a writes the brief BEFORE the
> state moves, because `writer.WRITABLE_STATES` is `{briefed, executing}` and a write after the
> move is refused. That made the write succeed and left the document recording the state it was
> written FROM — so a capability that landed had a final brief saying `executing`, and the one
> document [N13] and any later reader open never said what happened. The fix learned *which state
> it could be written from* and not *which state to report*. **Now:** `_write_brief(as_state=…)`
> — each site names the outcome it is about to set, and the brief describes the outcome of the
> node that wrote it.
>
> **N2. The referent block still presented a `build_tick` as the previous exchange.** D3 taught
> `_corrected_agents()` to skip a tick and a Diarist trace; `tools/turn_referent.context_block()`
> — the OTHER reader of the same trace file, and the one that goes into every user turn's context
> — was never told. After a tick with work it opened *"The exchange immediately before this one …
> This was a scheduled run — the user did not speak in it"*, so a short referring turn resolved
> against Build's own machinery. Not a phase-4 file; **the tick's trace is phase 4's**, so the
> fix is.
>
> **Now there is ONE definition and both read it.** `turn_referent.is_exchange()` — *a record
> with a `coordinator` in its pipeline* — plus `last_exchange()`, which scans back to the newest
> one. The orchestrator's own copy of that scan is deleted. The test is a Coordinator because
> every real turn runs one and nothing else does: a tick is rooted at `build`, and the Diarist is
> fire-and-forget on its own thread with its own trace, finished AFTER the turn it followed,
> which is why it is so often the record on top.
>
> **A scheduled session IS an exchange, and that is a second fix inside the first.** The round-1
> version skipped anything `is_proactive`, so a correction of a specialist a *scheduled* session
> dispatched fell back to `coordinator` and was lost — the review recorded that as "by design",
> and it was not. A scheduled session runs the full pipeline; its specialist is exactly what the
> user's next turn corrects.
>
> **N3. A landing-day run count divided by a day that was a tick.** On the day a capability lands
> the trace file exists **because the tick that landed it wrote one**, so `refresh_run_counts`
> found "one day" and wrote `actual 0.0 over 1d` — the "it never fires" verdict § 14's own
> contract forbids inferring from an inability to count, about a capability nothing had yet had a
> chance to dispatch. **Now two kinds of day do not count:** a day holding only Build's own ticks,
> and the landing day itself, which is partial and always understates. The window is computed
> **per capability** from its own landing date, and with no measured day the figure stays `None`.

**1. Job gate** — exists, correct state, budget untripped, attempts remaining.

**2. Path rules — three, in this order, all HARDCODED.**

*(a) The deny list, unchanged from v2:*
```
config/constitution.md · config/personas/** · data/personas/** (outside this job's dir and the
overlay/policies roots) · .env* · *key*.json · deploy.sh · .claude/settings.json
core/router.py · core/persona.py · core/spend_guard.py · core/scheduler.py
core/build/**             ← Build may not edit itself
config/modules/build.yaml ← Build may not raise its own ceiling
.git/**
```
*(b) The derived rule that makes option 1 hold:* **any path in `git ls-files` is refused.**
Computed once per `apply()` with `cwd=ROOT` on the VM checkout; if `git` is unavailable the
writer refuses everything, because a rule that cannot be evaluated is not a rule. A path that
is untracked today and tracked after a later deploy cannot arise for the two roots — both are
gitignored by `data/personas/*/`, and `check_build_registration.py` asserts that ignore line
exists so a later `.gitignore` edit fails the sweep.

*(c) The allow-roots:* anything not under the two roots is refused even if (a) and (b) pass.
(b) is belt and (c) is braces; a mistake in either leaves the other holding.

**3. Grant ALLOWLIST — HARDCODED, enumerated by grant, not by holder** (finding 10; restated as
an allowlist after Opus finding 2). **The read set below is the whole of what a generated
capability may hold.** A grant not in it is refused at every ceiling whether or not anything
names it as dangerous. The REFUSED line is documentation of *where the line is and why* — it is
not the enforcement, and it has no catch-all, because a deny list cannot enclose a tool surface
where the mutators are named for what they do rather than for the verb `write`:
`merge_contacts`, `unmerge_contacts`, `import_contacts_file`, `apply_crm_proposals`,
`teach_intake`, `record_wisdom_response`, `log_interaction`, `create_semantic_anchor` all fell
through v3's *"every `write_*`"* rule. The allowlist is asserted against the live
`register_tools()` handler names (§ 12), so it tracks the surface as it grows.

```
REFUSED  (why the line sits where it does — not the mechanism)
         sends or moves the user's words, money or calendar: send_email · send_calendar_invite ·
         write_calendar_event · update_calendar_event · delete_calendar_event
         fetches arbitrary content: fetch_url · fetch_rendered
         dispatches: run_subagent · run_model_conference
         rewrites standing state: write_agent_config · write_config · write_persona ·
         write_schedule · delete_schedule · open/close/reopen_obligation · record_horizon_item ·
         write_goals · update_goal · merge_wisdom_entries · teach_intake · apply_crm_proposals ·
         merge_contacts · unmerge_contacts · import_contacts_file · log_interaction ·
         record_wisdom_response · create_semantic_anchor — and anything else not below
READ SET read_log · get_log_window · read_journal · search_memory · read_wisdom · read_goals ·
         read_archive · read_calendar · check_calendar_conflicts · read_contact · list_contacts ·
         search_contacts · read_email · read_intake_queue · list_obligations · read_context_tracker ·
         read_profile · read_agent_config · read_recent_insights · list_schedules ·
         get_weather · get_environmental_snapshot · get_tfl_status · get_flight_status ·
         get_travel_time · get_regional_transit_info · find_places · the baseline readers ·
         (§ 9) search_conversations · read_journal_range
LOGGING  write_log · write_journal · write_quality_event — permitted; the Diarist path
```
The six `get_*` feeds leave the machine but carry no user-authored content and no
identifier beyond a city, line or flight number, which is why they sit with the reads.
**`find_places` is the seventh outbound read and that justification does not cover it** — it
sends a free-text query (Opus note 2). Its own reason: the query is a place description the
capability composes from the request, the same exposure `logistics` already carries under the
§ Section 0 ruling, and it is on the read side because it mutates nothing; a generated
capability that wants it must list it in `risks[]`, which N8b reads and the brief shows Mike.
The writes above carry Mike's words or move his money and calendar, which is the line.
**The allowlist trap still applies** (`.claude/rules/agent-files.md`): `allowed_tools` filters
schemas, not `dispatch_tool()`, so a generated agent *told* about a tool could still call it.
The writer therefore also refuses an agent file that names any tool outside its own grant —
the same regex `check_agent_tools.py` already runs, over the overlay (§ 6.8).

**4. Ceiling** — `config/modules/build.yaml`:
```yaml
autonomy:
  ceiling: "generated_registration"   # generated_registration | amber | red
  may_create_agent_files: false       # v1 default — raised BY HAND for the bootstrap runs (§ 11)
agent_construction:
  max_lines: 220                      # hardcoded floor; config may lower, never raise
  required_sections: [Role, Scope, Output format, Confidentiality]
```
An edit above the ceiling is **never dropped — it parks as an approval request.** That is the
difference between a ceiling and a wall, and it is what makes the ceiling expandable later.
Finding 4's surviving rule: the bootstrap runs execute with `may_create_agent_files: true` set by
Mike on the VM for the duration; v1 defaults apply from the first post-bootstrap run, and whether
to leave it raised is a decision Mike makes at the end of § 11 with three runs of evidence.

**Size limit and construction skeleton are hardcoded** because this is where the compliance evidence
points: six of six of Mike's 2026-08-21 complaints were rules already written in `synthesizer.md` and
ignored, while every rule moved to Python held on first contact. An agent file that grows without
bound is an agent that stops following its own instructions — so the limit belongs in code, not in a
style note.

**5. Shape gate — parity is now a schema property, and the four seams are what it feeds.** v2
demanded `routing_local` and `routing_cloud` in the same `apply()` call; v3 puts both in one
record, so a record missing either entry does not validate and cannot be written at all. The
evidence that convention alone does not hold is still `routing.yaml` itself: the 2026-07-27 diarist
fix landed `write_log`/`write_wisdom` in the cloud file and missed the local one, silently losing
both under `DEPLOYMENT_MODE=local`.

**The four load seams** — ordinary deployed code, built in phase 3, each a fallback that runs
only when the tracked source has no answer, so a tracked agent can never be shadowed and a
broken overlay record cannot take down a tracked one (the seams **fail open to "no overlay"**,
logged; the writer and verify are the fail-closed half). One loader,
`core/build/overlay.py:load_overlay(persona) -> dict[name, record]`, mtime-cached per process,
serves all four:

| # | Seam | Today | Change | Tier |
|---|---|---|---|---|
| 1 | `load_agent(name)` — [`core/orchestrator.py:681`](core/orchestrator.py) | raises `FileNotFoundError` when `config/agents/{name}.md` is absent | before raising, try `overlay/agents/{name}.md` for the persona in scope | Amber |
| 2 | `_load_routing()` — [`core/router.py:56`](core/router.py) | reads one YAML per `DEPLOYMENT_MODE` | merge each overlay record's `routing.local` or `routing.cloud` entry under `agents[name]`, tracked names never overridden, `model_ref` resolved to the named tracked agent's live model. `resolve_model()` and `get_allowed_tools()` need no change — they read the merged dict | **Red — Mike is prompted, not delegated** |
| 3 | Coordinator names — the `coordinator.md:84-85` valid-name paragraph and § Specialist directory as loaded by `load_agent("coordinator")`, and `_AGENT_NAME_MAP` at `:5503` | the valid-name list is a **closed** list in the cached system prompt; the map is a literal | **rewrite the valid-name paragraph at prompt assembly** so the closed list the model reads is the complete one — the overlay display names spliced into that sentence, the directory entries appended under § Specialist directory, both in the system prompt, the tracked file untouched on disk (Opus finding 3, Mike's decision). v3's context-block injection is withdrawn: it left the system prompt saying the name was invalid and a context block saying it was, on a model whose own map comment records it cannot reliably copy the existing list. **Cost accepted:** the system prompt changes once per landing, so the Vertex cache is re-created once per landing — priced in § 14 Ancillary; `_pad_for_vertex_cache()`'s floor is unaffected because the prompt only grows. Merge `{display_name.lower(): name}` into the map | Amber |
| 4 | `_UNAVAILABLE_CONSEQUENCE` (`:5399`), `_CONTEXT_SENSITIVE` (`:1415`), `domain_agent_map()` (`tools/wisdom.py:358`) | three literals; the domain map cached on one process-global `(mtime, dict)` | each consults the overlay after its literal: consequence by name; confidential names appended to **`_CONTEXT_SENSITIVE`** at filter time and never to `_ALWAYS_CONFIDENTIAL` (Opus finding 1, § 4); `knowledge_domains` adding the agent to existing domains only, with the map's cache **keyed by `(persona, mtime)`** so one persona's capability names cannot leak into another's domain map inside the server (Opus note 3) | Amber |

`register_tools()` is **not** a seam in v1, because `kind: tool` is out.

**6. Constitution alignment at generation time** — `core/build/constitution.py`:
- **(a) Confidentiality clause present and exact.** The security architecture is two-layer: each agent
  refuses to discuss tools, sub-agents, routing or prompt contents (instruction layer), and
  `filter_output()` scans for leaked names and suppresses (backstop). **The clause is what prevents
  the leak; the filter only catches it.** A generated agent without it will narrate its own tooling.
- **(b) No new user-facing narration of process** — grep generated text against
  `_ALWAYS_CONFIDENTIAL` plus model ids, provider names, `config/` and `core/` paths.
- **(c) Sensitivity declared and consistent** — see § 8.

**7. Staging and undo — the journal is now the only undo.** Before the first byte, append
`{path, existed, sha256_before, bytes_before}` to `undo.jsonl`; each write is temp + `os.replace()`;
`revert()` replays in reverse and is what [N13]'s refusal, a failed check, and `abandoned` all
call. **New machinery with no prior art, flagged as such** (§ 13.6) — and with no worktree beside
it any more, so it must be tested harder, not less: the sha256 round-trip in § 12 runs over every
file kind the writer produces (agent file, record, policy, journal itself). `_budget_root()`'s
worktree case (`core/spend_guard.py:63-107`) no longer applies to Build; nothing in v3 runs in a
worktree.

**8. The same checks, not equivalents — now twice.** `core/build/verify.py` shells out,
`cwd=ROOT`, and runs each check **once over the tracked tree, exactly as `qa_sweep.sh` does, and
once over the overlay**. The tracked pass is unchanged. The overlay pass exists because
`qa_sweep.sh`'s greps go through `git ls-files` (`scripts/qa_sweep.sh:87-99`, `:137`) and its
check scripts glob `config/agents/*.md` and read the two tracked routing files — **none of them
can see an overlay file, on the VM or on the Mac.** So three scripts gain one flag,
`--overlay DIR` (`check_agent_tools.py`, `check_knowledge_domains.py`, `check_rule_overlap.py`:
read overlay agents and the merged routing view instead of the tracked ones), and
`check_build_registration.py` reads the overlay natively. Order: `check_agent_tools.py` →
`qa_sweep.sh` (the 10 + build-registration) → the three `--overlay` passes → the capability's
tests → `test_action_provenance.py`. **No check is reimplemented in `core/build/`.** § 12 verifies
this by diffing check-name sets rather than asserting it — **in two parts, because one equality
over the whole invocation could never pass** (Opus finding 4): `check_knowledge_domains.py` is a
standalone script the sweep does not run, and neither the capability's tests nor
`test_action_provenance.py` are sweep checks. So `verify.py` declares `SHARED_CHECKS` — the
sweep's ten plus `build-registration` — and `ADDED_CHECKS` (`knowledge-domains`,
`capability-tests`, `action-provenance`). The shared names, `:overlay` stripped, must equal the
sweep's set **exactly**; the added names must equal the declared list exactly; nothing may be in
neither. Equality over a declared subset still cannot drift, which is the property v3 wanted.

**9. On failure** — `revert()`, append `→ failed` with the check name and its output, emit
`BUILD_CHECK_FAILED`, carry the failing output **verbatim** into the next attempt's brief.
**Nothing is ever left half-applied.**

---

## 7. Validation and retry

```
RUNG 0  STRUCTURAL REPAIR  free — import core.orchestrator._repair_context_json() verbatim
RUNG 1  FIELD COERCION     free — closed enums collapse toward the SAFE value:      [v3, finding 9]
                             class unknown          -> the question moves to declined_to_ask[]
                                                       with the defect noted (no safe class exists)
                             disposition unknown    -> new         (highest burden of proof)
                             answerable_by unknown  -> judgment    (forces has_what_it_needs)
                             variable_scope unknown -> query_only  (declares nothing)
                             execution_mode unknown -> deferred    (never blocks a turn)
                           Never coerce a VALUE — only a category, only downward in permissiveness.
RUNG 2  TARGETED RETRY     one call, max 1 per node. The retry prompt is the rejected artifact plus
                           a machine-written defect list naming each failed constraint.
RUNG 3  REJECT             -> failed with the defect list; park on the board.
```

**Why the retry is affordable here.** The repo's stated reason for having none
([`core/orchestrator.py:2186-2194`](core/orchestrator.py)) is *latency on a live user turn*. Build has
no user waiting — it is tick-driven. Cost is one extra call, capped, charged to the job budget.
*If this reasoning is wrong, drop rung 2 and keep 0/1/3* — the design still functions.

**The planner's file-path check calls `writer.apply(dry_run=True)` — the enforcer itself, not a copy
of its rules.** The only way validator and enforcer cannot drift.

---

## 8. Budget, routing, privacy

**Budget — three parts, no multiplier.** A default limit per job; if the N8 estimate exceeds it, the
job parks at `awaiting_approval` and asks (see the correction below — **not** via
`tools/confirm.py`); **the run hard-stops the moment the limit — default or approved — is
exceeded.** A tripwire, not a tolerance band.

> **Correction recorded deliberately — v3.5, 2026-09-19, before phase 4 was written.**
>
> **C2. The over-budget ask does not go through `tools/confirm.py`** (Mike's amendment,
> 2026-09-19). Three reasons, in order of weight.
>
> A confirm card needs a matching entry in `tools/confirm.py`'s `_EXECUTORS` map or
> `POST /confirm` answers *"Nothing here knows how to carry out …"*. That is `[DB-0815-03]`
> precisely: from 2026-08-05 to 08-15 the gate refused correctly and **completed nothing**,
> every approved action expiring unperformed while the user believed it had happened. The
> `confirm-executors` sweep check exists because of it.
>
> **The widening is the real objection.** An executor entry would make *raising Build's own
> per-job spend limit* a one-tap action in the app — in a design whose hardcoded deny list
> names `config/modules/build.yaml` for the sole purpose of ensuring Build cannot raise its
> own ceiling. Approving more money by tap is the same act one layer out.
>
> And `tools/confirm.py` is absent from § 10's Modified list, which is stated as the complete
> file map.
>
> **Now, and the location is load-bearing.** The job parks at `awaiting_approval`;
> **`tools.build.context_block()` surfaces it conversationally**, which is the Build surface
> § 5 already specifies and needs no new mechanism; and the approval is
> `core.build.cost.approve_limit()` **run on the VM over ssh**.
>
> **Never from the Mac board.** Under ruling 0.1 the ledger lives on the VM, and
> `scripts/build_board.py` reads it through a **read-only fetch** — a board that could approve
> would need a write path into the VM's persona tree, which is exactly what the Mac
> deliberately does not have. `build_board.py`'s usage text carries the ssh command, so it is
> found in the same place the parked job is seen; a command documented only here would be
> looked for on the machine the board is running on.

Metering seam: `core.build.cost.record_job_tokens(...)` inside `record_turn_tokens()` at
[`core/trace.py:278-286`](core/trace.py), a no-op unless a job is bound on the thread. **Prices
through `spend_guard.estimate_usd()`** — the same function the global guard uses, so the two meters
cannot disagree about what a token costs. A second pricing table is rejected on the repo's own
evidence: `spend_guard.py`'s header records that its docstring said `$70/$150` through two raises and
a revert.

Enforced **pre-node AND post-node** in `run_node()` `[v3.6]`. Pre-node refuses to start a node past
the limit; **post-node parks what the call itself crossed**, since a call in flight cannot be
aborted. That pair is what makes *"overshoots by at most one node"* true. With only the pre-node
half the crossing surfaced at whatever next read spend — in practice the Planner's dry-run file
check — which the planner read as a plan defect and FAILED the job terminally, past
`awaiting_approval`, the one state that exists to release it. A **dry run is not budget-gated at
all**: it writes nothing and costs nothing. `run_node()` must also call
`check_before_session()` itself and map `SpendLimitExceeded` → `blocked`, or on a capped day
`_spend_gate()` returns *"I've paused myself for now…"* **as the agent's output**, landing verbatim
inside a Question Set.

**Sensitive tier by default.** CLAUDE.md has two tiers — Open (no personal context) and Sensitive
(goals, logs, health, finances, prime directive, mission). Semi-sensitive was collapsed because
`shareable_what` plus behaviour reconstructs `private_why`. **A generated capability is Sensitive
unless it can demonstrate it never touches persona data** — fail-closed, matching `resolve_model()`.

Build's own agents qualify: Librarian reads the corpus; Inquiry in REPAIR carries verbatim messages;
Planner sees a ledger derived from the corpus. They are configured **exactly as every other sensitive
specialist** — `local: true` in `routing.yaml`, a Vertex model in `routing_cloud.yaml`, as
`mental_wellbeing` and `physical_health` already are. This is the ZDR amendment, which CLAUDE.md's
2026-08-09 clarification makes the project-wide default for the single-user phase.

> **Correction recorded deliberately.** The design pass proposed `local: true` in *both* files. That
> would raise at [`router.py:79-94`](core/router.py) on the VM and leave Build unable to run where the
> persona data lives. Applying a stricter rule to Build than to the medication classifier would have
> been an unrequested privacy ruling smuggled in as a config default.

`build_librarian` gets **read tools only**. The other three get `allowed_tools: []`.

---

## 9. Librarian's substrate — what exists and what is missing

**Exists (~25 tools):** `search_memory`, `read_journal`, `read_log`, `get_log_window`, `read_wisdom`,
`read_goals`, `read_archive`, `read_calendar`, `read_contact`/`list_contacts`/`search_contacts`,
`read_email`, `read_intake_queue`, `list_obligations`, `read_context_tracker`, `read_profile`,
`read_agent_config`, `read_recent_insights`, baselines.

**Missing — and these are the difference between lookup and research:**

| Gap | Why it blocks research |
|---|---|
| No conversation search | `conversations/*.jsonl` is the richest verbatim record — 44 days — reachable only by exact filename from two internal callers |
| `read_journal` takes one date | 61 journal files; "how does Mike talk about work stress" means 61 calls or nothing |
| Wisdom is keyed lookup only | no free-text search over values |
| No readers for horizon / analytics / accountability / traces | push-only via context blocks |
| **No FAISS reindex path** | see below |

**FAISS, in detail, because it gates the question-dedupe design.**
[`core/memory.py`](core/memory.py) is an `IndexFlatIP` over 384-dim MiniLM vectors with a parallel
`metadata.json`. Two defects: it is **append-only with no rebuild path anywhere in the repo**, so a
deleted journal entry keeps its vector forever and widening what gets embedded can never be applied
retroactively; and **every `write_log` re-embeds the whole day**, so a day edited ten times sits in
the index ten times and skews similarity toward heavily-edited days.

**Build gets its own index `[v3]`, finding 8.** Encoding questions with FAISS is still the right
idea, but not in *that* index: `search_memory(query, k)` has no source filter and is granted to
eleven specialists, so questions stored there would come back as recalled memories, and the
reindex would make it retroactive. So `core/build/index.py` keeps a separate `IndexFlatIP` under
`data/personas/{p}/build/index/`, same encoder, holding only Build's questions and policy
`applies_to` text — two uses, deduping Inquiry's questions against every question ever asked, and
letting the probe resolve a policy semantically rather than by exact key. **The reindex path is
no longer a prerequisite for anything in this plan**; it leaves § 16's phase list and stays a
defect worth fixing on its own merits.

**The first two gaps are `needs_tool` briefs Mike builds first `[v3]`** — ordinary development on
the Mac, before the run that needs them (§ 11): `search_conversations(query, since, k)` over
`conversations/*.jsonl`, and `read_journal_range(start, end, max_entries)` with the shape of
`get_log_window`. Both are read tools, both enter the read set in § 6.3, and both are named in
`build_librarian.md` from day one — a tool named in an agent file is a specification.

---

## 10. Files

**New:** `core/build/{__init__,ids,jobs,schemas,manifest,probe,condense,settle,policy,index,cost,brief,
writer,overlay,verify,constitution,runner,coherence,registry}.py` · `tools/build.py` (the only
agent-callable surface) · `tools/search_conversations.py` and the `read_journal_range` function
in `tools/diarist.py` (the two § 9 briefs — Mike's builds, listed here so the file map is
complete) · `config/agents/build_{inquiry,librarian,planner,coherence}.md` ·
`config/modules/build.yaml` · `scripts/{check_build_registration,build_board,build_brief}.py` ·
`tests/test_build_*.py` including `test_build_spine.py`, `test_build_overlay.py` (the four seams)
and `test_build_writer.py` · `tests/fixtures/inquiry_rsvp_2026-09-17.md` (the verbatim pass/fail
pair — a fixture, never shipped to a model; its abstract lives in `build_inquiry.md`, see § 15)

**Runtime-owned, never in git (VM only; in the existing backup tar except where noted):**
```
data/personas/{p}/build/ledger.jsonl · registry.jsonl · jobs/BLD-*/ · policies/
data/personas/{p}/build/overlay/agents/{name}.md · overlay/capabilities/{name}.yaml
data/personas/{p}/build/index/        NOT backed up — metatron-backup.sh:78 excludes *.faiss
                                      deliberately; rebuilt from jobs/*/question_set (Opus note 1)
```

`core/build/policy.py` stores and resolves standing policies and is what `depth: triage` reads. It is
the component that makes Inquiry cheaper over time, so it is not optional. `core/build/overlay.py`
is the one loader behind the four seams (§ 6.5).

**`core/build/`, not a top-level `build/` — coverage, not aesthetics.** `qa_sweep.sh`'s py_compile
check greps `^(core|tools|scripts)/`, CLAUDE.md's rules index globs `core/**`, and the tier table
names `core/` paths. A new top-level directory silently escapes all three on day one. Sequestration is
real but comes from the hardcoded deny list, which holds wherever the code lives.

**Modified (all by ordinary development, deployed by Mike — none by Build):**
- both routing files — the four Build agents, strict parity, plus the two new read tools on
  `build_librarian`, **plus `request_build` on `coordinator`'s `allowed_tools` in both files**
  (`[v3.5]` C3 below — this grant had no owner until 2026-09-19, and without it the tool is
  registered and unaskable)
- `core/orchestrator.py` — `register_tools()` ×3 (`request_build`, `search_conversations`,
  `read_journal_range`), `_block_source` +1 line, `_ALWAYS_CONFIDENTIAL` (the four Build agents'
  own names — tracked underscore identifiers, so the unconditional list is right for *them*),
  seams 1, 3 and 4 (seam 4 extends `_CONTEXT_SENSITIVE` at filter time, never
  `_ALWAYS_CONFIDENTIAL`), and the code-written correction attribution (§ 3)
- `core/router.py` — seam 2 only. **Red tier: prompts every time, not delegated**
- `tools/wisdom.py` — `domain_agent_map()` consults the overlay, cache keyed by persona (seam 4)
- `core/actions.py` · `coordinator.md` (§ Tools available — `request_build` only; the valid-name
  paragraph is **not edited on disk** — seam 3 rewrites it at prompt assembly, so the tracked
  file keeps its tracked list and the model reads the complete one) · `synthesizer.md` + grants
  (`answer_interview_item`)
- `core/scheduler.py` `_DEFAULT_JOBS` — one `build_tick` entry, carrying the REPAIR hook. **Red
  tier, this prompts, that is the control working**
- `scripts/qa_sweep.sh` (check 11, `build-registration`) · `scripts/check_agent_tools.py`,
  `check_knowledge_domains.py`, `check_rule_overlap.py` (`--overlay DIR`)
- `scripts/sync_dev_backlog.py` — one event label, `BUILD_PROPOSED`; the REPAIR hook is **not**
  here any more
- `CODEBASE_INDEX.md`, `docs/CONVENTIONS.md`, `.claude/rules/orchestrator.md`

**No change:** `knowledge_domains.yaml` (Build agents are never Coordinator-dispatched;
generated agents reach it through seam 4, not by editing it) · `.claude/settings.json` ·
`.gitignore` and `scripts/metatron-backup.sh` (the overlay's directory is already covered by
both — § 6) · `deploy.sh` · **`tools/confirm.py`** (`[v3.5]` C2, § 8 — no card, no executor
entry).

> **Correction recorded deliberately — v3.5, 2026-09-19, before phase 4 was written.**
>
> **C3. Nothing in this plan granted `request_build` to the Coordinator.** § 2 states the tool
> is granted at Coord level and at theme-router level, and the `coordinator.md` bullet above
> adds the § Tools available line — but the routing bullet named the four Build agents and the
> Librarian's two read tools and stopped. `allowed_tools` is what filters the schemas an agent
> is offered, so as written `request_build` would have been **registered and unaskable**: the
> `c840415` lesson (*"a registered tool that cannot be asked stops looking like an empty
> one"*) one layer along, and the `time_director` half-wiring in the other direction —
> instruction present, grant absent.
>
> **Now:** the grant is named in the routing bullet above and on § 16's phase 5 line. **Phase
> 5, not phase 4** (Mike, 2026-09-19): the `coordinator.md` line and the grant must land in the
> same change, and phase 5 is where both routing files are opened anyway. Phase 4 registers the
> handler and classifies it; nothing can call it until phase 5, and nothing is deployed until
> phase 6, so the gap is inert rather than latent.

---

## 11. Bootstrap

**Under option 1 the cheapest grist is no longer removal** — removing a capability from a
specialist is an `extend`/`split` edit to a tracked file, which Build cannot make. It is a
scheduled prompt the Coordinator already fails to route: a gap that exists, recurs, and has an
owner on the board. The three runs below use the VM, the `mike` persona, and
`may_create_agent_files: true` set by hand for their duration (§ 6.4).

**Before run 1 — two `needs_tool` briefs Mike builds on the Mac** (§ 9): `search_conversations`
and `read_journal_range`. The Librarian's first research question — *how does Mike record a
watering, and where* — is unanswerable without them: the record is in day logs and
conversation, across weeks, and `read_journal` takes one date. Ordinary development, deployed
with phases 1–5; not Build work.

**Run 1 — `home_care` (`kind: agent`, `disposition: new`, `execution_mode: blocking`), a leaf
under Coord.** The gap, in Mike's words and the machine's: on 2026-09-08 he filed twice that the
plant-watering check *"remained stuck on August 4"* while his logged waterings went unread, and
that it never looked at London rainfall (`DEV_BACKLOG.md` § Inbox, `2026-09-08T08:53`, `08:54`);
the machine log carries three runs of the scheduled plant-watering prompt **after** that filing —
09-11, 09-14, 09-15 — where the Coordinator dispatched **no specialist**, and the 09-11 entry
shows it doing the arithmetic itself from *"Last watered Aug 4"*. Nobody
owns *"is this household thing overdue, given what was logged and what the weather did"* — the
class is a **cadence judgement over a last-done date**, and no specialist performs it for any
obligation. `generalizes_to`: every recurring home obligation with a last-done date and an
interval. Config-only and entirely over existing read tools: `get_log_window` (the logged
waterings — recomputed at read time, never stored, the `derived_facts()` principle from
`[DB-0822-06]`), `read_wisdom` (the `home` domain already holds `plant_watering_threshold` and
`plant_care_hot_weather`), `get_weather` (live `days_since_rain`, granted to Logistics today),
`list_schedules`, `search_memory`. Registers under `home` in `knowledge_domains`.

*Disposition evidence, stated now because a reviewer will call this an `extend` of Logistics:*
Logistics lists watering as an obligation *type* (`logistics.md:41`) and holds the tools, but
owns actions — calendar, email, bookings — not a standing check that reads a log and decides;
on none of the three recorded runs did the Coordinator route the prompt to it at all, so there is
no evidence Logistics performs this judgement and evidence that nothing does.
`extend` is also deferred behind promotion, so the honest v1 shape is a leaf, and it is the first
candidate to fold under Logistics when the tier lands (run 4+) — the re-registration cost § 2
already accepts.
*Acceptance (VM, `mike`, Mike present):* fire the `water_plants_check` prompt, and separately send
*"did I water the plants recently?"* → the trace shows `home_care` dispatched with
`get_log_window` and `get_weather` called, no other specialist; the reply states days since the
**latest logged** watering, which must equal the newest watering entry in that log window, and
the rainfall verdict from `days_since_rain`; both inside the declared budget. Fail: any answer
naming August 4, or a specialist other than `home_care` and the Diarist.
*Need met:* logged waterings — met; weather — met; Mike's rule that rain counts as watering —
met if the `home` wisdom entries carry it, otherwise an `interview_item`, which is the mechanism
working.

**Run 2 — a deliberately induced REPAIR on run 1.** Ship `home_care` with one question knowingly
unasked (*"indoor plants too, or only the garden?"* — the rainfall verdict is wrong for one of
them). Let it answer wrongly once, then **file the REPAIR by hand from `build_board.py`**
(finding 6: run 2 tests the dossier, not the trigger). **REPAIR has no prior art anywhere in the
repo**; the only way to know the dossier carries enough is to run one, and doing it deliberately
on a one-day-old fully recorded capability is the cheapest possible first. The code-written
correction trigger (§ 3) is tested separately, after run 2, by letting a real correction land.

**Run 3 — `kind: policy`, `depth: triage`.** The standing rule Mike stated on 2026-09-12 — business
correspondence waits for Monday rather than being raised at the weekend (`DEV_BACKLOG.md` § Inbox,
`2026-09-12T08:53`) — is a policy, not a tool: `applies_to` business senders, `automatic_no` at the
weekend, `default_on_silence` Monday morning, `review_date` set. It exercises the policy record,
the manifest entry, and the path § 4 says makes Inquiry cheaper: the run after it that touches the
same class must resolve at `depth: triage` with ≤3 questions and no Librarian pass.
*Acceptance:* a second `request_build` in the same class replays to `triage` in the ledger; no
Librarian node ran.

**Run 4+ — the tier.** Convert `logistics` to a theme router, re-register `home_care` beneath it,
make the depth guard depth-aware, grant `request_build` at router level. Then continue.

**The promotion gate — stated, not designed.** `split` and `extend` unlock when a promotion path
exists and has been used once: a Mac-side command copies one overlay capability into the tracked
tree as a reviewable diff, Mike commits and deploys it, the overlay copy retires on that deploy,
and the promoted capability survives the next `git pull` without conflict. Until one capability
has crossed that path, no Build run may produce a plan whose disposition needs a tracked-file
edit; the writer's `git ls-files` rule is what enforces the wait.

**Phase 7 is a walkthrough session, not a list.** Every step above that only Mike can take —
raising the ceiling on the VM, deploying, watching the acceptance, filing run 2's REPAIR,
deciding the ceiling default afterwards — is an (M) item, so § 16 schedules phase 7 as one
guided session with the steps prepared in advance and Mike executing live.

---

## 12. Verification

| Piece | Command | Proves |
|---|---|---|
| Schemas | `python3 tests/test_build_schemas.py` | Each validator rejects its malformation: a feasibility question before an intent one; a `disposition` of `new` whose evidence does not name the capability checked; empty `disposition_evidence`; zero surface; zero authority at `depth != triage`; judgment row with one option; a `variable_name` already declared; an agent plan missing a registration item; a `surface_map` with an unlisted operation |
| **The compass rule** | `python3 tests/test_build_spine.py` | The reference transcript's **turn-2 answer fails validation and its turn-4 answer passes.** A real pair, produced before the rule existed — the strongest available evidence that the constraint discriminates rather than merely fires |
| Job record | `python3 tests/test_build_jobs.py` | ids allocate; rows replay to the right terminal state; truncated line skipped; duplicate fingerprint refused. **`[v3.6]` D7:** `resume_to` rides the status row, survives a replay, and is CLEARED by the next transition that sets none — a stale target would send a second resume to the wrong node |
| Restart | create job → `kill -9` mid-node → restart → print `states('mike')` | Resumes at `attempt: 2`, no duplicate artifacts |
| **Manifest privacy** | `python3 tests/test_build_manifest.py` | Greps the manifest for every string value in `profile.yaml`, fails on any hit — **the privacy proof for Inquiry** |
| Probe honesty | `python3 tests/test_build_probe.py` | Empty journal → `data_available: false, rows: 0`, not an exception. **`[v3.6]` D4:** EVERY manifest source's fixed arguments are bound against its handler's real signature — the review found `log` carrying `{"days": 14}` against `get_log_window(start_date, end_date)`, and binding them all found **eleven more**, nearly half the table. Separately, a live feed is never CALLED by a probe: the handlers are replaced with one that raises, and all seven return `state: live` instead |
| **Writer** `[v3]` | `python3 tests/test_build_writer.py` | Every path in a fixture repo's `git ls-files` refused at **all three** ceilings, including one that is *also* under an allow-root; every deny-list path refused; a path outside both allow-roots refused; a record with one routing entry refused; an agent file naming a tool outside its grant refused; every § 6.3 refused grant refused at all ceilings; `revert()` restores byte-identical by sha256 for agent file, record, policy and journal; with `git` unavailable, `apply()` refuses everything. **`[v3.1]` Allowlist complement (Opus finding 2):** for every handler name the live `register_tools()` registers that is not in the read set — `teach_intake`, `apply_crm_proposals`, `merge_contacts` among them — a record granting it is refused **even though no refused list names it**, so the test tracks the surface as it grows. **`[v3.1]` Name collision over three sets (finding 5):** a record named `time_director` — agent file present, no routing entry — is refused, as is one matching a `routing.yaml`-only or `routing_cloud.yaml`-only name. **`[v3.1]` Common-word names (finding 1):** a record named `garden` lands, and `filter_output()` then passes *"I watered the garden this morning"* untouched while still suppressing *"the garden agent's routing.yaml entry"*; a record named `home_care` leaves *"your home-care tasks are up to date"* untouched. **`[v3.2]` The four writer-side review defects (§ 6):** an edit whose path is the job's own undo journal is refused, and a forged journal entry naming a deny-listed path is skipped by `revert()` rather than replayed — asserted by appending one to a real journal and checking the path is still absent afterwards; a `display_name` of `"Mental Wellbeing"`, `"Time Director"`, `"Research"`, `"Logistics"` or `"Pattern Miner"` is refused; `send_email` written as bare prose with no backticks is refused; a record setting `routing.cloud.provider` is refused, as is a `model_ref` present in only one routing file; and `find_places` is refused unless the PLAN's `risks[]` names it — with a risks entry that does not name it also refused, so the check cannot pass on a vague one. **`[v3.3]` Part 2 (§ 6):** a second record displaying a landed record's display name is refused, as is one whose display resolves to another record's NAME (`Garden` beside a capability named `garden`); `Mental  Wellbeing`, `Time  Director` and `MENTAL  WELLBEING` are refused as whitespace/case look-alikes of a reserved name; and `Undo.jsonl`, `UNDO.JSONL` and `Undo.JSONL` are all refused with the journal left byte-identical |
| **Overlay seams** `[v3]` | `python3 tests/test_build_overlay.py` | A fixture record under a fixture persona: `load_agent` returns the overlay file only when no tracked file of that name exists; `resolve_model` returns the `model_ref` agent's live model and the record's `allowed_tools`; a tracked name in a record is ignored; consequence and domain map see the record; a malformed record is logged and skipped with every tracked agent still loading. **`[v3.1]` Seam 3 (finding 3):** the assembled Coordinator **system prompt**'s valid-name sentence contains the overlay display name exactly once inside the existing closed list, § Specialist directory carries the entry, no separate `## Additional specialists` block exists anywhere in the prompt, and `coordinator.md`'s sha256 is unchanged after assembly. **`[v3.1]` `PersonaError` (finding 6):** with no persona bound, `load_overlay()` returns `{}`, `load_agent` of a tracked name still succeeds, and `resolve_model()` of a tracked agent still succeeds — the existing `tests/test_a4_complexity_threading.py` run unchanged is the regression gate. **`[v3.1]` Persona-keyed cache (note 3):** two fixture personas with different overlay records — the domain map served to each carries only its own capability names, in either order of first call. **`[v3.2]` The two seam-side review defects (§ 6):** a hand-written record displaying `"Mental Wellbeing"` — bypassing the writer, which refuses it — adds NO duplicate to the assembled prompt's valid-name line and does not enter the name map, so schema and seam agree independently; and a record that sets its own `provider` is served the tracked agent's provider by `resolve_model()`, not its own. **`[v3.3]` Part 2 (§ 6):** two hand-placed records sharing a display name put that string into the assembled prompt's valid-name line exactly ONCE and leave one entry in the name map, so the closed list can never carry a duplicate whatever reached the overlay. **`[v3.4]` Part 3 (§ 6):** a hand-placed record displaying `Mental  Wellbeing`, `Mental & Wellbeing`, `Mental and Wellbeing`, `  Mental Wellbeing  `, `MENTAL WELLBEING` or `Time  Director` is surfaced by NEITHER half of seam 3 and leaves the assembled Coordinator prompt **byte-identical** to the no-overlay baseline — asserted against the baseline rather than by string absence, because the padded form strips to a string already in the closed list as the tracked entry |
| **"Same checks" claim** `[v3]` | `qa_sweep.sh --verbose` vs `core.build.verify.run_all()`, diff the name sets with `:overlay` stripped | **`[v3.1]` Two equalities, not one (finding 4):** verify's `SHARED_CHECKS` names must equal the sweep's set **exactly** — the ten plus `build-registration`; verify's remaining names must equal its declared `ADDED_CHECKS` exactly (`knowledge-domains`, `capability-tests`, `action-provenance`); a name in neither fails. **Proves** it rather than asserting it, over a subset that cannot drift. Second assertion: on a tree with an overlay present, `qa_sweep.sh` reports **zero** overlay files (it cannot see them) and `run_all()`'s overlay pass reports each one |
| **Run ledger** `[v3.1]` | after run 1 lands: `python3 scripts/build_board.py --persona mike --run-cost` | The ledger's `landed` row for `home_care` carries one run line — `execution_mode`, `latency_budget_ms`, expected dispatches/day written by N8 from the trigger's observed frequency — **`[v3.6]` D9: `None` until something can actually count a trigger.** The first version returned the Coordinator's turns per day as a proxy, which is the same figure for every capability regardless of what filed it, and `0.0` on a fresh persona — the "it never fires" verdict its own contract forbids inferring from an inability to count. Phase 4 has no trigger signature; the figure is owed to whatever phase gives a trigger an identity, and the ACTUAL count is measured from day one — and the actual dispatch count once a day has passed — counted from the TRACE FILES, not from the A9 rollup, which counts tool names and never agent names (`[v3.5]` C1, § 14); the board shows **1 of 4** leaf capabilities under the Coordinator against the tier's due condition (finding 7, § 14, § 16). A landed capability with no run line fails `check_build_registration.py`. **`[v3.7]` N3:** neither the LANDING DAY nor a day holding only Build's own ticks counts toward the denominator — the landing day's trace file exists because the tick that landed it wrote one, and dividing by it produced `actual 0.0 over 1d` about a capability nothing had yet had a chance to dispatch. The window is per capability, from its own landing date; with no measured day the figure stays `None` |
| Constitution | run `constitution.check` on a generated agent with `## Confidentiality` deleted, and on one over `max_lines` | Both must fail. **`[v3.2]` The record-field defect (§ 6):** narration in `coordinator.directory_entry`, a confidential identifier in `unavailable_consequence`, and a provider name in `display_name` must each fail and must each NAME THE FIELD in the defect — the three fields reach a prompt and none was scanned. Plus the charset: `Home/Care`, ``Home`Care``, `Home\nCare`, `Home_Care` and `Home<Care>` refused; `Home Care`, `Work & Vocation` and `Zone 2` accepted. **`[v3.3]` Part 2 (§ 6):** `send_email`, `read_email` and `merge_contacts` in `unavailable_consequence` each fail naming the field — none is on the static list, and all three are live registered tools; and `check_build_registration.py --overlay` exits 1 on a hand-placed record carrying a whitespace look-alike display name and a `model_ref` in neither routing file, which the sweep passed while it called the validator with `tracked_names` alone |
| Budget | set the limit to `0.01`, run a job | Parks at `awaiting_approval`, never starts N10; ledger spend reconciles against the day's trace. **`[v3.6]` D2:** a limit crossed DURING a call parks and is never terminal, and `approve_limit` + `resume` genuinely releases it; a dry run is not budget-gated while the real write still is. **D1:** `refuse()` will not touch a landed or mid-pipeline job — asserted by counting `revert()` calls, which must be zero |
| **Trace contract** | run one job → `python3 tools/metatron_monitor.py` | Renders in The Book with the three agents **nested**. Open The Book — rendering is the criterion, not the JSONL |
| Latency `[v3]` | run 1's acceptance with timing assertions | Blocking capability stays inside its declared budget; a `deferred` one returns immediately and lands via `context_block` on a later turn |
| End to end | `request_build(...)` → `tick('mike')` → `build_board.py --persona mike` → `build_brief.py BLD-... --persona mike` | A readable, redacted brief with no raw persona values. **`[v3.6]`:** **D14a** every brief write happens from a state `writer.WRITABLE_STATES` admits, and on a failed landing the brief is written AFTER the revert that deletes it; **D11** a writer crash fails with its own reason and runs NO sweep; **D3** a Diarist-only or tick trace is skipped when attributing a correction; **D13** the context block names the interview QUESTIONS; **D12** every command it prints binds a persona; **D10** two Build events in one trace are both written while `USER_CORRECTION` still dedupes; **D8** the fourth correction files no second REPAIR ticket; **D9** the expected dispatch figure is `None`, never `0.0`; **D14b** a question indexes with its class; **D14c** the dry-run rejection claims no retry. **`[v3.7]`:** **N1** the landed brief says `landed`, not the state it was written from; **N2** the referent block never presents a `build_tick` as the previous exchange, both readers share `is_exchange()`, and a SCHEDULED session's specialist is attributable |
| **Landing** `[v3]` | on the VM after run 1: `git status --porcelain` → `git diff --stat` → `./deploy.sh` (Mike) → acceptance again | **`git status` is clean and `git diff` is empty — Build wrote no tracked file; the deploy pulls with no conflict; `home_care` still answers after it.** Build never writes a tracked file; Mike promotes |

---

## 13. Risks an adversarial reviewer will attack

1. **"Unbounded question sets plus a retry is a cost hole."** Retry capped at 1/node; the hard stop is
   the approved limit; the pre-node gate refuses when tripped. *Partial concession:* job-level
   `max_attempts` and node-level retry **multiply** — cap the product explicitly in `run_node()`.
2. **"The ceiling is config; anything that edits config can raise it."** `config/modules/build.yaml`
   and `core/build/**` are on the **hardcoded** deny list, as are all outbound grants and the agent
   size floor. The ceiling is raised only by a human editing a file Build cannot reach, and
   `check_build_registration.py` asserts the deny list so a later "simplification" fails the sweep.
3. **"The probe runs read tools with model-chosen arguments — injection into the corpus."**
   `candidate_sources` is validated against the manifest id list and `probe.py` maps an id to a
   **fixed, code-written call**. The model names a source; **code chooses the call.**
4. **"You built a second backlog, and `DEV_BACKLOG.md` is 161KB of evidence that backlogs rot."**
   *Partial concession.* Rows here reach terminal states by **running**, not by being read. The part
   that can rot is `proposed`, capped at 12. **Honest concession:** a full stale `proposed` queue after
   a month means gap detection is over-firing, and the fix is narrowing the trigger, not raising the
   cap. Double-filing to `DEV_BACKLOG` during bootstrap is deliberate redundancy, not duplication.
5. **"Leaf-first means you will re-register everything when the tier lands."** Conceded and chosen.
   Re-registration is mechanical; trusting an unproven pipeline with a structural change is not.
6. **"The undo journal is new machinery with no prior art, and must never fail."** **Concession, and
   the piece to review hardest.** Written before the first byte; temp + `os.replace`; `revert()`
   tested by sha256 round-trip; the executing session uses a worktree instead. v1 blast radius is new
   files plus shape-validated inserts.
7. **"The coherence review is expensive and unfalsifiable."** Corpus is code-assembled and small — one
   liners, file lists, registration rows, surface maps, not source. Output constrained to a closed enum
   (`drift`, `overlap`, `contradiction`, `orphan`), each finding **required** to name two capability
   ids and the artifact where they collide. A finding that cannot name two ids is rejected.
8. **"A redacted brief means the executing session guesses."** Real tension. The brief carries
   decisions and assumptions — which is what a spec is — and names a synthetic fixture persona the
   session can read. Where a test needs a real value, `acceptance.missing_data` names the interview
   item and the job parks. Missing data is a work item, not a blocker.
9. **"`request_build` on Flash-Lite will file garbage."** Real. Fingerprint dedupe; `proposed` not
   `queued`; cap of 12; `gap` validated by `is_null_ish` exactly as `write_quality_event` does — the
   precedent being the slot that produced `"None." ×90`. *Concession:* if the first runs show
   over-firing, move the grant up a level.
10. **"A generated agent file bypasses the Red-tier prompt."** Real. The harness `ask` is a control on
    *Claude Code sessions* and was never in scope for runtime writes; the equivalent control is the
    writer's ceiling. *Concession:* a genuine widening, which is why `may_create_agent_files` defaults
    `false`.
11. **"Latency claims are asserted, not measured."** Fair until run 2. The mitigation is that
    `execution_mode` defaults to `deferred` on any coercion, so the failure direction is a slower
    answer rather than a stalled conversation.
12. **"The altitude rule turns every request into a module, so Build never ships anything."** The
    sharpest attack on the new constraint, and a real tension: generalising is unboundedly expensive
    and the RSVP transcript itself warns against over-applying its own framework. Three counters.
    `depth: triage` resolves most requests against an existing policy without generalising at all.
    The disposition is four-way, and **`extend` and `split` both produce small builds** — only `new`
    trends large, and `new` carries the highest burden of proof for exactly that reason. And the
    `replaces[]` field plus the coherence review make an over-narrow build visible later, whereas an
    over-broad one is expensive immediately. **The rule is asymmetric on purpose: it costs a sentence
    of evidence to build narrow, and a whole run to discover you built narrow by accident.**
13. **"Run 2 builds `venue_finder`, which is exactly the narrow tool your altitude rule exists to
    prevent."** Caught deliberately, and it is the rule working. Run 2's `disposition` is **`split`** —
    logistics is doing too much and the bolded venue exception inside its Coordinator directory entry
    is the seam — with `generalizes_to` = *place and venue selection within logistics*. That is the
    honest classification, not a workaround: a split is small by construction and its evidence is
    checkable against the file it carves from. If that evidence could not be written honestly, run 2
    would be the wrong run.

---

## 14. Cost

| Phase | Contents | Model | Est. |
|---|---|---|---|
| 1 | ids, jobs, schemas, **spine validator + transcript fixture** + tests | **Opus 5** | $10–16 |
| 2 | manifest, probe, **condense**, settle, **policy**, **Build's own index**, cost + tests | Opus 5 | $14–21 |
| — | **In-chat worked Inquiry + Librarian/Planner interview** (§ 15) | Opus 5 | $2–4 |
| 3 `[v3]` | **writer (path rules, grant list, ceiling, journal), the four overlay seams, constitution, verify with its overlay pass, the three `--overlay` flags, `check_build_registration`** + tests — the safety surface **and** the landing surface, because what the writer writes only matters if the seams load it and verify sees it | **Opus 5**, seam 2 (`core/router.py`, Red) written in the main session and not delegated; whole phase reviewed by **Fable 5** | $18–26 |
| 4 | runner, brief, registry, coherence; scheduler + orchestrator wiring, the correction attribution | Opus 5 | $10–15 |
| 5 | the four agent files | **Fable 5** | $5–9 |
| 6 `[v3]` | the two `needs_tool` briefs — `search_conversations`, `read_journal_range` — with tests and grants; Mike's builds, ordinary development | Opus 5 | $4–7 |
| 7 `[v3]` | **Bootstrap runs 1–3 as one walkthrough session on the VM**: Mike raises the ceiling, deploys, runs acceptance for `home_care`, files run 2's REPAIR from the board, runs the policy job, decides the ceiling default. Model spend is the three jobs' Build calls plus the acceptance turns | Opus 5 (the session); the runs themselves bill to Vertex through `spend_guard` | $8–14 |
| | **Total** | | **$71–112** |

**Split execution and review on phase 3 only** — the writer is the one component where a defect is
unrecoverable rather than merely wrong, and the seams are now in the same phase for the same
reason. Elsewhere a review pass would not earn its cost.

**Run `[v3]`, finding 7.** `build_tick` is a `function:` job: every 30 minutes it replays the ledger,
and with an empty queue it returns at **zero tokens and milliseconds of CPU**. With work it runs
**Inquiry → probe → Librarian → Planner in one tick as one request** — three agents nested under
one `RequestTrace`, which is the only way `core/trace.py` nests at all — and the per-node atomic
artifacts remain the resume cursor, so a crash mid-tick resumes at the node that had not written.
Total is exactly (nodes run) × (per-node cost) — no idle burn, no standing charge. **Two things
that persist between calls, priced:** the overlay and the job directories grow by kilobytes per
job and are deleted by `revert()`/`abandoned`, owned by the persona tree's existing backup; Build's
index adds ~1.5 KB per question (384 floats) and is rebuilt from the job artifacts if lost. No
meter reports either and none is needed at this size; the day one is, the ledger row count is the
proxy.

**The product, not only the factory `[v3.1]`, Opus finding 7.** The shipped thing is the
capability: each landed `kind: agent` is a specialist dispatched on every matching turn, forever,
at that turn's model price, and § 2 makes the count growing the explicit goal. So **the ledger
carries one run line per landed capability** — `execution_mode`, `latency_budget_ms`, expected
dispatches/day (code-written at N8 from how often the trigger fired in the traces that filed
the gap), and the actual dispatch count per day, counted from the trace files `[v3.5]` over
**measured days only** `[v3.7]` — neither the landing day nor a day holding only Build's own
ticks counts, because both produce a rate of 0.0 about a capability that has had no chance to
be dispatched. Both fields exist already; this is the meter nothing had
wired. **The tier stops being "Later" and becomes due when four leaf capabilities have landed
under the Coordinator** (Mike, 2026-09-18) — the board reports the count against that figure
from run 1 onward, and § 16 carries the same condition.

> **Correction recorded deliberately — v3.5, 2026-09-19, before phase 4 was written.**
>
> **C1. `tools/analytics.py` does not count dispatch per specialist, and the paragraph above
> says it does.** `rollup_day()` walks the trace through `_walk_tools()`, which counts TOOL
> names into `top_tools`. Agent names are in the trace record (`core/trace.py:353` writes
> `"agent"` on every `AgentRecord`, nested subagents included) and **nothing counts them.** So
> *"both fields exist already; this is the meter nothing had wired"* was half right:
> `execution_mode` and `latency_budget_ms` do exist on the record, and the dispatch count
> existed only as a sentence.
>
> **Now:** `core/build/registry.py` counts dispatches from the trace files directly — the same
> files `rollup_day()` derives from, walking the same nesting, counting agent names instead of
> tool names. Content-free either way, so nothing about the privacy tier changes.
>
> **The A9 rollup is untouched** (Mike, 2026-09-19), and the reason is worth keeping because
> the additive change looks free. `ROADMAP.md` § A9a gates that schema on a review dated
> **2026-10-01** whose first instruction is *"do not review this before there is real data"* —
> the 2026-08-18 baseline is mostly development traffic and tuning against it would bake in the
> wrong shape. A session that wanted one number would have started that review early, on
> exactly the traffic the review says not to use.

**Ancillary.** `build/` grows per job (KB, not MB). Rung-2 retry adds at most one call per boundary.
Dedupe windows exist partly to stop re-paying for work already done. Seam 2 adds one small YAML
read to every `resolve_model()` call — the routing file is already re-read per call, so this is
the same order of cost, not a new one. **Seam 3 re-caches the Coordinator once per landing
`[v3.1]`:** rewriting the valid-name paragraph changes the cached system prompt, so the Vertex
cache for `coordinator` is created afresh on the first turn after each landing — one cache
creation (input tokens at the cache-write rate) per capability, never per turn, and never for
`synthesizer`, whose prompt seam 3 does not touch. Accepted by Mike in exchange for the model
reading one complete closed list instead of a closed list and a contradicting context block.

**Unseen `[v3]`.** With N11 gone there is no Claude Code session executing briefs, so the one
cost `spend_guard` could not see is gone with it. What replaces it is smaller and honest: every
`needs_tool` brief is a Mac-side build Mike pays for in development time, metered by nothing —
`scripts/worker_ledger.py` measures worker cost from transcripts but nothing meters development
spend per week. **Not in scope; named so it is not mistaken for zero.**

**Model:** build in **Opus 5**, agent files and the phase-3 review in **Fable 5**. Red-tier work —
seam 2 in `core/router.py`, the `_DEFAULT_JOBS` entry in `core/scheduler.py` — is written in the
main session and not delegated to a subagent.

---

## 15. The reference transcript — abstract and verbatim have different jobs

**In hand (2026-09-17):** the RSVP reasoning transcript. It is used **two ways, deliberately kept
apart**, because the failure modes of the two uses are opposite.

| Form | Where it lives | Job |
|---|---|---|
| **Abstract** — the spine, the eight classes, the two stances, the disposition table | `config/agents/build_inquiry.md` | the operating rule the model reads. Short, token-disciplined, no narrative |
| **Verbatim** — the full two-turn transcript | `tests/fixtures/inquiry_rsvp_2026-09-17.md` | a regression fixture. **Never shipped to a model at runtime** |

**The verbatim transcript does not go in the agent file**, and that is the answer to the concern. Agent
files are token-sensitive by explicit project rule, and there is direct evidence here that instruction
length degrades adherence — the whole compliance argument in the rebuild notes. A long narrative
example inside the file the model must obey would compete with the rule it illustrates.

**But it must not be reduced to the abstract either.** Its evidentiary value is that it is a real
**pass/fail pair produced before the rule existed**: turn 2 must fail validation (feasibility-first,
no `intent` class, no disposition) and turn 4 must pass. An abstract cannot fail a validator. Discard
the verbatim and the compass rule becomes an assertion again.

> **Named weakness: n = 1.** A validator tuned until one pair sorts correctly may be fitted to that
> pair rather than to the principle, and the domain is narrow — a single social invitation.
> Mitigation, and the reason this is acceptable rather than merely admitted: **every Inquiry run
> produces another pair** — its question set, plus whatever a later REPAIR or coherence pass says was
> missing from it. The fixture set grows from real runs and is never manufactured. If the second and
> third real pairs need the validator loosened to pass, that is the signal the rule was overfit, and
> it arrives early and cheaply.

It also names the two canonical REPAIR signatures — the blind spots turn 4 admits it had:
**jointly-held resources** (treating a shared asset as the principal's alone) and **process
proportionality** (spending more deciding than the decision is worth). When a Build-made capability
fails, these are the first two classes Inquiry should test against.

**Still to do in chat, before phase 2 closes:**
1. **A worked Inquiry run by hand** on a real Metatron gap — the cheapest check that the spine's
   shape is right. A schema that survives one real pass is worth more than one that survives review.
2. **The Librarian/Planner prompt-parameter interview**, after the manifest and probe exist, so it is
   grounded in what the Librarian can actually see rather than in speculation.

---

## 16. Execution order

```
Phase 1  ids · jobs · schemas · spine validator + the transcript fixture
           ← the artifacts become real, and the compass rule is testable on day one
Phase 2  manifest · probe · condense · settle · policy · Build's own index · cost      [v3]
   ↳ worked in-chat Inquiry run; then the Librarian/Planner interview
Phase 3  writer · the four overlay seams · constitution · verify (+ overlay pass)      [v3]
           ← reviewed with a second model; seam 2 is Red and is written, not delegated
Phase 4  runner · brief · registry · coherence · wiring · correction attribution      [v3]
Phase 5  the four agent files, written against the reference transcript
           + BOTH routing files: the four Build agents at strict parity, the two read
             tools on build_librarian, and request_build on coordinator's allowed_tools
             — the grant that had no owner until 2026-09-19        [v3.5, C3 in § 10]
Phase 6  the two needs_tool briefs: search_conversations · read_journal_range         [v3]
           ← Mike's builds; the FAISS reindex is no longer here (finding 8)
   ↳ ./deploy.sh — Mike; phases 1–6 reach the VM as one deploy
Phase 7  bootstrap runs 1–3 as one walkthrough session on the VM, Mike present         [v3]
Later    the tier: logistics as theme router, depth-aware guard, request_build at router level
           ← DUE, not merely later, once FOUR leaf capabilities have landed under the
             Coordinator (Mike, 2026-09-18); the board counts toward it from run 1     [v3.1]
         the promotion path (§ 11 gate) — the unlock for split and extend
         the FAISS reindex, on its own merits
```
Phases 1–6 land nothing user-visible. The first thing Mike sees is phase 7 run 1.

**Phase 1 is deliberately front-loaded with the spine validator** rather than leaving it to phase 5
with the agent files. The transcript gives a real pass/fail pair now, and a rule that can be tested
before the agent that must obey it exists is a rule that cannot be quietly relaxed to make the agent
work.
