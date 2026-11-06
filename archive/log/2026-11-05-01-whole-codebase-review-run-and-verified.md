### 2026-11-05 (The whole-codebase review ran, was verified, and the Highs shrank from eleven to six)

The review prompt written on 11-04 ran in a fresh Fable 5.1 session: one lead, eight read-only area reviewers in
a pinned worktree at `bc90ed0`, a lead cross-area pass, then adversarial verification. Report:
`archive/plans/codebase_review_2026-11-05_fable-5-1.md`, 328 lines, 51 ranked findings plus ~30 grouped Lows.
Nothing filed to the backlog — Mike triages with `/backlog`. Not deployed; nothing to deploy.

**What it found, at project granularity.** The harness holds where it was built hard: identity binding at
every thread boundary, the confirmation gate's approve-and-act path, consent withdrawal, byte-identical tool
grants across both routing files. The defects cluster in four places: routing escapes the orchestrator never
refuses (a client-supplied `provider` field, a dead model-conference tool); instruction files describing a
system the loader does not build (tools granted that no file names, a granted tool with no schema, quick-mode
sections code never triggers, flags nothing reads); unattended jobs that report a quiet day once a credential
dies; and single-user machinery under a second user (four schemas with a persona slot, Build tickets keyed
without the persona, developer channels that read any persona). Six High after verification: the journal
prompt leak on API failure, the cross-user persona slot, carried nudges never delivered, calendar edits
destroying alarms and exceptions, a deploy that reports success over a crash loop, and Build's landing gate
refusing every capability. One conditional High: the provider field, decided by whether `OPENAI_API_KEY` is
on the VM.

**Decisions.** (1) The cap was applied in dollars, not the prompt's token translation: the prompt assumed
1-hour cache writes and 2M output tokens, the subagents wrote at 5-minute TTL and output was a third of that, so
the token line read 80% while spend was 30%. (2) Verification ran in Opus 5.5, Mike's offer: the judgement was
the review phase and verification is bounded tracing of cited lines; the pass cost $25 against $154 for the
Fable work and its verdicts carried file:line throughout. (3) Five grouped verifiers instead of eight, after the
session-limit interruption. (4) The lead overrode one verdict — the provider field stays High-if-key-present
rather than Medium — because the control at stake is the ruled path, not whether the caller is the data owner.

**Rejected.** Sequential verification (the limit is a per-window budget, so sequencing changes when it bites,
not whether); waiting for the 08:00 reset before delivering (the report shipped at 05:xx with the reviewers'
verdicts labelled, verification appended after); resuming the five Fable verifiers (they had done orientation
only; fresh Opus spawns were cheaper than re-warming Fable contexts).

**Believed earlier, wrong.** Fourteen 10-29 backlog entries say "not yet deployed" about commits that are in
`ebfe50b`; the primer said `check_day_plan_step2.py` reaches the VM with the next deploy — it is already there,
so the `[DB-1029-01]` check can run now. The lead's own grant-versus-schema diff flagged `record_wisdom_response`
as granted with no schema and the lead dismissed it as a regex miss; Area 7 proved it real. Five reviewer claims
fell on verification: `read_journal` is the Build doors' presence probe, not dead; `CONSULT_NEEDED` has a
generic receiver in `synthesizer.md`; runtime refusal on a missing base consent record was designed out in the
multi-user plan § 4.11; the per-host spend budget is a recorded accepted risk; the Google Contacts trio's dormancy
was recorded at `[DB-0808-01]`'s closure. Two backlog lines are understated: `[DB-1029-10]` is structural
(`write_calendar_event` has no location parameter), `[DB-0810-11]`'s "no dedup" line is stale.

**Operational.** The account's five-hour usage window tripped twice (02:10 and 08:00 London), killing five
reviewers mid-area and then five verifiers; reviewers resumed from their transcripts, verifiers were re-spawned.
Cost $178.90 of $250 (72%). The worktree was created twice from `bc90ed0` and removed twice, clean.

Outgoing primer handoff, carried: Synth now/next (`547c446`) committed not deployed; stage 2 prep-tasks spec
next; Iva's onboarding; `/backlog deep`; WhatsApp Phase 0 close-out; the meals habit still unmade.

**The primer sits exactly at its ceiling after this close-out** (200 lines, volatile part 120). The next
addition must move a section out, not trim a sentence; the Model IDs table to `docs/INFRASTRUCTURE.md` is
the obvious candidate, since `scripts/check_model_availability.py` already owns the live answer.

