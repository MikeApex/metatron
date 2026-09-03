### 2026-09-03 (Red session ⑤ — the Coordinator was never shown the previous turn)

Session ⑤ of the staged Mark 1 four, built to the 2026-09-02 handoff: fix the referent class
`[DB-0826-01]` — *"undo that merge"*, *"approved"*, *"now set it back to Iva"* resolving
against the wrong thing, five live instances 08-10 to 08-29. The handoff's opening step was
*re-run Suite B-hard first, the 6/12 baseline predates the fleet migration*. That instruction
is what found the real cause, and it was not the one the item, the probe or the ruling assumed.

**What was believed and was wrong.** The item and the 2026-08-28 probe both held that
Flash-Lite *ignores* a rule `coordinator.md` already states, and that Pro's 12/12 was Pro
following it. The Coordinator was in fact never given the conversation at all: both live call
sites in `core/orchestrator.py` invoked `_run_single_agent("coordinator", ...)` with **no
`history` argument**, and only the Synthesizer received turns. Everything the Coordinator knew
of the recent past came through `load_recent_context()` — ambient facts, open threads, five
days of day-logs — which contains no conversational turn. So *"that merge"* was matched against
the only merge-shaped thing in scope, on 08-26 a Prudential Apex **branch** merge in the logs.
`coordinator.md:129` ("a pronoun without a clear referent") was **unfollowable, not ignored**.

**Why no measurement had caught it.** `tests/run_coord_model_probe.py` has always passed
`history` to the Coordinator, so every figure it ever produced — the 6/12 of 2026-08-28
included — measured a strictly easier condition than production. The probe was answering a
model question on a setup the live pipeline never provided.

**Built (both halves, because the measurement says neither alone is enough).** `_coord_history()`
passes the last six messages — copied, never the caller's list, since every model loop appends
its own turn to what it is handed and would have spliced the raw routing package into the
Synthesizer's conversation. And `tools/turn_referent.py` `context_block()`, registered last in
`load_recent_context`'s plugin loop, stating what the previous turn *did*: the tools that ran,
their objects, and whether each completed, failed, is **still waiting** on the user, or was
**refused**. Tool classification is taken from `core/actions.py` rather than a second prefix
list, so this block and the ACTIONS line the Synthesizer already receives cannot disagree about
what ran. Fails open throughout — deliberately the opposite of `tools/turn_context.py`, which
fails closed because it gates whether a refused action may return; this one only adds evidence,
so a missing or stale trace must leave today's behaviour rather than cost the user a turn.

**Why the block and not history alone.** A transcript is the record of what was *said*. On
08-29 the reply text said the email to Iva was sent; it was pending, and the user then declined
it. Replaying that as fact is the fifth instance. The block reads the confirm ledger instead.

**Numbers** — `gemini-3.5-flash-lite`, Suite B-hard ×3, `tests/run_referent_probe.py`, raw JSON
committed beside it. Referent named correctly: **0/12** with neither half, **6/12** with history
alone, **12/12** with both (24/24 across the day's two full-arm runs). *"Approved."* is the case
that separates them — 0/3 on history alone, where it named *both* pending approvals, which is
precisely the 08-15 live failure, and 3/3 with the block. The 3 residual dispatch misses are
that turn choosing `logistics` over `relationships` with the referent already correct: a
taxonomy disagreement about who owns emailing a landlord, not this class.

**Rejected: editing `config/agents/coordinator.md`.** The handoff allowed Red wording pointing
at the block. Not taken — 12/12 without one, and the block carries its own instruction inline
(the `crm_sweep` precedent), so a second copy in the agent file would break One Home Per Rule
Class. The finding is that the existing rule could not be followed, not that it was worded
badly.

**Rejected: the stated pass condition.** The handoff set *ask-rate on ambiguous referents
rising*. It is 0% in every arm and should be: once the referent is supplied there is nothing to
ask about. Replaced by referent-resolution rate, with ask-rate kept as the secondary — a fix may
buy safety with a clarifying question, never with silence.

**Also corrected:** `tests/run_coord_model_probe.py` gained a `with_history` arm so the
pre-2026-09-03 condition stays re-measurable, and its docstring no longer claims the Coordinator
gets no history, which this session made stale.

A4 did not ride this (suspended, `ROADMAP.md` § 0 pt 8) and `_dispatch_from_coordinator` was not
touched, so its pipeline suite did not either. Gates run: `tests/test_turn_referent.py` 16/16
(new, standalone-script style — the pytest draft was rewritten, pytest is not a declared
dependency and every other test in `tests/` is a plain script), fourteen related standalone
tests all green, and one live end-to-end pipeline run through the edited call site, which routed
*"Undo that merge."* to `relationships` and attempted the unmerge rather than searching
work_vocation for a Prudential project. `tests/test_action_provenance.py` was 9/10 both before
and after — `apply_crm_proposals` unclassified in `core/actions.py`, pre-existing and unrelated
— **filed to the Inbox and then fixed on Mike's instruction in the same session rather than
left there.** One line into `ACTION_TOOLS`, 10/10, evidence in
`archive/backlog_closed_2026-09.md`. It is the third tool to reach the contact store
unclassified after `merge_contacts` and `import_contacts_file` on 08-18, which is the argument
for fixing it on sight rather than queueing it.

**Deployed and live-confirmed the same day, so `[DB-0826-01]` is CLOSED.** Two real user turns against the deployed VM on persona `mike` (not `proactive`, which `send_one` hardcodes and which would have made the block correctly report that the user never spoke): *"Log what I ate today — cereal and milk for breakfast."* → logged, then *"Read that back to me again."* → *"For today's log, I have recorded cereal and milk for breakfast under your nutrition notes."* That is the 08-18 instance verbatim, which used to resolve to the Prudential schedule. Evidence in `archive/backlog_closed_2026-09.md`. Commits `6483e27` (fix), `8caaeb7` (close-out), `cc58a5b` (`apply_crm_proposals`).

**Left open deliberately and not filed:** *"Approved."* still chooses `logistics` over `relationships` on 2 of 3 runs with the referent already correct. It is a taxonomy question about who owns emailing a landlord, not this class, and filing it on probe evidence alone would put an item on the list that no user has yet noticed.

