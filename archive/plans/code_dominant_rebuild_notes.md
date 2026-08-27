# Code-dominant rebuild — thinking notebook

**Status: thinking only. No decisions, no build.** This is the running note base for the
architecture inversion Mike opened on 2026-08-22 — Metatron rebuilt code-dominant, with models
kept for discrete judgment gates. Each discussion round appends a dated entry; nothing here
authorizes work. **This is an ongoing conversation across the close-out of Metatron v1 (Mike,
2026-08-27): any session that touches the rebuild thinking appends its round here — no length
limit on this file.** **Retirement condition:** when the rebuild is commissioned, this folds into the
refactor plan that commissions it, and this file closes (single-bin rule,
`.claude/rules/docs-and-logs.md`).

Anchors — where this touches the live planning surface:
- Where should code replace model judgment `[DB-0810-11]` — the standing backlog decision this
  notebook feeds; it points back here.
- A8 (pre-Alpha refactor, `ROADMAP.md`) — sequencing constraint: decide the inversion before A8
  executes, or pay for A8 twice.
- "Config files are the product" (`CLAUDE.md` § Key Design Decisions) — the founding principle
  the inversion re-draws; must be amended explicitly, never drifted past.

---

## 2026-08-22 — The opening round: "built backwards?"

Full record: [code_vs_agent_architecture_2026-08-22_discussion.md](code_vs_agent_architecture_2026-08-22_discussion.md)
(kept as the dated snapshot of that round; not duplicated here). One-paragraph abstract:

Mike's question — 14 rich instruction files on a thin harness produce repetitive, off-topic,
information-flooded responses; should goals be mapped procedurally with agents as judgment
gates? Evidence: an Opus barbecue-RSVP transcript whose quality came from an *enforced ordering*
prose files cannot enforce. Claude's recommendation: yes to the inversion — code owns control
flow / ordering / validation / retrieval / computed state, config owns policy; Coordinator is
the first candidate to become mostly code; pilot one domain (invitation/RSVP) rather than decide
wholesale; the compass layer (standing computed allocation state) is a separate build under
either verdict; fallback for unrecognized shapes is the current agent path, making migration
incremental. Open question left with Mike: gates that hit thin evidence — ask, or
decide-with-default?

---

## 2026-08-27 — Round two: what the token audit says about the runtime the rebuild replaces

From the trace-audit chat (Aug 1–8 and Aug 20–27 windows; verbatim in
`archive/transcripts/`, measured tables filed in `[DB-0808-09]`). Four observations that bear
on the inversion, not on incremental tuning:

1. **Specialists never batch tool calls — 392 tool-turns measured, every one single-call — and
   each turn re-sends the full accumulated context.** The multi-turn cost the June plans chased
   in the Coordinator lives in the specialists (2.6–4.2 turns/call). Read architecturally: the
   model is being paid, per turn, to *re-decide a procedure* — which is the same defect the
   08-22 round named in prose-file terms ("a procedure carried in prose is re-decided every
   turn"). The turn structure is the runtime evidence for the inversion.
2. **The common turn shape is already a procedure: predictable reads → one reasoned write →
   final.** First turns are `read_email` / `read_calendar` / `read_log` / `read_intake_queue` —
   exactly what code-side prefetch could supply with zero model turns (Mike's proposal,
   2026-08-27; KNOWLEDGE_TO_LOAD is precedent). The write can't prefetch — its content is the
   reasoning. In rebuild terms: the reads are the procedural spine, the write is the judgment
   gate. The measured shape *is* the target architecture, executed expensively.
3. **Candidate mechanisms, ranked in the chat (unevidenced — diagnose from traces first):**
   instructed batching of independent reads (a trim, ~1 turn); Coordinator/code prefetch of
   predictable reads (the strong one — no extra model turns, cached prefix undisturbed, but
   someone must predict the tool set, and misses still cost a turn); read/write specialist split
   (weakest as stated — same tokens paid under two system prompts plus a dispatch hop; only
   earns if the read half runs much cheaper). Details in `[DB-0808-09]`.
4. **Caching cuts against the context-file pattern, and nobody has adjudicated that.** The
   roadmap's slimming pattern (move domain data out of instruction files, load on demand via
   `read_agent_config`) now costs a *turn* per load — which re-sends the whole prompt — while
   the text it removed would have sat in a *cached* prefix (Synthesizer 75% / Coordinator 64%
   hit rates). `read_agent_config` is in live use (15 calls/wk logistics, 11 physical_health).
   Under a code-dominant rebuild this tension dissolves — domain data becomes computed evidence
   handed to gates, not prompt text — but any *interim* slimming work should check it isn't
   buying turns with cache savings. Flagged for a second-model review in the 08-27 chat; not
   yet run.

Related live threads, tracked in the backlog, not here: unbounded Synthesizer thinking
`[DB-0827-02]`; specialist caching step 6 `[DB-0822-01]`; all-Pro routing `[DB-0820-05]`.

---

## 2026-08-27 — Round three: what the sink-gap session's "Part 2" adds, re-read for the rebuild

Provenance: the 2026-08-10 sink-gap session carried an undiscussed "Part 2" — where should code
replace LLM judgment — written **before** the inversion was on the table, so its fix-the-existing-
Metatron items are dropped here. What survives is the reasoning, plus one piece of evidence the
same session generated on resumption (2026-08-27). Four points:

1. **Prompt-resident judgment creates architectural tensions that are artifacts, and there are
   now two of them.** Part 2's strand B: the Synthesizer spends a full LLM round-trip calling a
   subagent to *check a fact* — a database lookup's job — and the v1 fix (widen the Synthesizer's
   tool allowlist) cuts against head-layer/specialist separation and PoLP in `routing.yaml`.
   Round two's point 4 found the same shape in caching-vs-instruction-slimming. Both tensions
   dissolve under the inversion for the same reason: when code fetches evidence and hands it to a
   gate, "who may read what" becomes a property of a code path, not a prompt surface. **A
   recurring class — v1 design dilemmas that are really symptoms of procedure living in prose —
   is itself an argument the layering is wrong,** and each new instance found should be logged
   against this pattern rather than adjudicated inside v1's terms.

2. **In a model-dominant system, part of the call graph is prose, and static analysis cannot see
   it — now evidenced three times on one pipeline.** Part 2's strand C: `daily_calendar_dedup_audit`
   was correct, tested, committed and deployed, and did nothing for 3 days (per-persona template
   never propagated; fixed structurally in `_DEFAULT_JOBS`), then had its output discarded for 5
   more (the sink allowlist). Neither was a code bug; neither was catchable by unit tests. The
   third instance arrived 17 days later in the same session's resumption: `ROUTING_MISS` was
   declared dead on the strength of a *code grep*, while the emitter was `synthesizer.md`
   instructing a runtime tool call — five events silently dropped, with the reconciliation test
   certifying the drop (`[DB-0827-05]`). **The rebuild-salient reading: you cannot grep for who
   emits an event, calls a tool, or exercises a capability when the caller is an instruction
   file.** A code-dominant runtime makes the call graph greppable and its seams typed and
   testable — this is a concrete, repeatedly-paid cost of the current layering, not an aesthetic
   preference.

3. **The zero-token `function:` scheduler jobs are the inversion already running at the edges.**
   `daily_rule_audit`, `daily_calendar_dedup_audit`, `daily_travel_check`: standing code audits
   that compute evidence deterministically, write it to the event stream, and leave judgment to
   whoever reads it ("this is evidence, not a verdict" is in the audit's own output text). Part 2
   suggested this pattern may *be* the code/agent review protocol rather than its subject. In
   rebuild terms they are the existence proof of the target shape — procedure in code, judgment
   at a gate — and notably their failures (point 2) were all at integration seams, never in the
   computation. The corroboration finding from the same session strengthens it: the calendar
   audit and a `USER_CORRECTION` cluster caught the **same** Heathrow incident independently —
   a computed sensor and a model-reported signal cross-checking is what an evidence layer with
   two sources looks like.

4. **Identity resolution belongs in code, before any model sees the data — and the boundary of
   the inversion is thresholds, not retrieval.** Part 2's strand A plus its parked
   title-normalization item: `_find_by_name`'s substring matching lets "Jon"/"Jonathan"/"Jonathan
   Whitfield" exist as three contacts, and calendar attendees are matched to people by string
   guess. The runtime record shows this is where errors breed: the Eva/Iba correction cluster
   (×4), the Jonas quadruplication, the merge/undo misroute (`[DB-0826-01]`). Rebuild principle:
   entities (contacts, events, obligations) get resolved to stable ids by code, and models reason
   over resolved entities. The counterweight Part 2 also carried: `tools/wisdom.py`'s own testing
   found a fixed similarity threshold picks the wrong partner ~3/5 of the time — **a threshold is
   a judgment smuggled into code.** The inversion moves procedure and resolution into code; a
   borderline match is exactly what stays a judgment gate.

## 2026-08-27 — Round four: the compliance-ceiling experiment moves here, and the first judgment gate got deleted in code

*From the thinking-cap / sign-off session (Fable). Two inputs and one worked example.*

**1. The instruction-size compliance experiment is deferred INTO this conversation — Mike's
call, 2026-08-27: run it against the rebuilt agents, not to fix compliance in v1.** The
experiment was designed and priced for `synthesizer.md` (hold six probed rules constant, vary
surrounding ballast across ~4 file sizes × ~10 trials ≈ 240 turns ≈ $15–20 post-caching), then
deliberately not run: the v1 agents get refactored regardless — ROADMAP § D2's targets and this
notebook's inversion both already prescribe it — so a curve measured against files being
discarded answers nothing durable. What the rebuild should inherit:

- **The deliverable is a design ceiling, not a verdict on one file** — a dose-response curve of
  rule-compliance vs. instruction-file size, measured on our workload. It sets the token budget
  the rebuilt agents are designed against, replacing ROADMAP § D2's targets (specialists
  1,500–2,500; head 3,500–5,000), which are sensible but argued from vendor guidance, not data.
- **The ceiling must be measured on the weakest model that will ever run the agent.** A number
  from gemini-3.1-pro says nothing about qwen3:14b, and local is the north star. The probe
  *suite* is the reusable artifact; the number is re-measured at D1 as part of local-model
  adequacy. Published literature (to the session's knowledge cutoff): no crisp threshold exists;
  degradation tracks the *number of simultaneous constraints* more than raw length, and position
  (early/late beats middle) — both already encoded in D2's ordering principle.
- **The evidence that motivates the whole inversion, restated as data:** six of Mike's six 08-21
  complaints were rules already written in `synthesizer.md`, all ignored — while every rule
  moved to Python this month held on first contact (contact-rename gate, pending-receipt guard,
  research zero-source withholding). The experiment would put a curve under that anecdote;
  the anecdote already points one way.

**2. A worked example of the inversion, shipped 2026-08-27: the "over and out" sign-off.** The
question "must the Synthesizer run when nothing needs saying" — first raised in the 2026-08-18
Synth-economics chat, and the same question the turn audit's 392 single-call turns ask at system
level — got its first concrete answer, and the shape is exactly this notebook's thesis:

- **Detection in code, not model judgment.** The phrase is matched in Python
  (`_is_signoff()`, Damerau distance ≤1/word on the final three tokens, never mid-message,
  never on a question) — routing it through the Coordinator was considered and rejected because
  a Flash-Lite judgment adds two failure modes to a decision a string match makes exactly.
- **The model layer still does the work** (Coordinator + specialists run; the diary write
  lands); only the judgment gate that has nothing to judge — the Pro Synthesizer pass — is
  skipped.
- **The safety boundary is code**: any `MUST_SURFACE` / `CLINICAL_CONCERN` /
  `MEDICATION_MISSED_CRITICAL` in specialist output vetoes the skip in Python
  (`_signoff_skip()`), per the standing rule that a mishandled clinical flag is a hard fail
  regardless of how the turn was classified.
- **Generalisation for the rebuild:** this is one turn-class reclassified from
  "model decides everything" to "code decides the shape, models fill the judgment slots." The
  392 single-call turns are the backlog of candidates. Each reclassification should look like
  this one: deterministic trigger, work preserved, safety veto in code, one fixed-cost exit.

**Also relevant, from the same session:** the Synthesizer thinking cap landed at 4096 as
insurance (`[DB-0827-02]` closed; probe found no tail above 3,930, exposure ~$0.26/day) — which
removes "runaway thinking cost" from the list of problems the rebuild needs to solve, and the
`THINKING_CAP_HIT` quality event will say so if that changes.
