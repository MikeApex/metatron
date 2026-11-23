### 2026-11-23, eighteenth (ranking Part B phase 3 built — the back burner as a dry run, the weekly review's look back, signals; all switched off) — `e2578d6` — **committed, NOT deployed**

**Incoming handoff:** `archive/handoffs/2026-11-23-ranking-part-b-phase-3-build-prompt.md` (Opus
5.5, high) — consumed. The outgoing primer said *"Next: phase 3"*. Phase 2 and the lookup
switch-on are on the VM; none of phase 2's three walkthroughs has run, and `ranking_v2` is off.

**Wrong earlier — the plan's vehicle for the weekly conversation could not work.** § 4.12 and the
prompt assumed `write_schedule` makes "a weekly conversation at a time the user picks" and that
its turn gets the scheduled-session conduct. In fact:
1. It wrote only an interval or a one-off, and a one-week interval counts from every scheduler
   restart, so it would never fire at this deploy rate.
2. An agent-written job's turn has no session kind, so it gets neither conduct nor material.
3. § 3's survey missed the existing week-ahead weekly review, which rides a brief by Mike's 09-05
   choice because a separate session costs attention.

**Mike ruled option 1:** the priorities conversation rides that weekly review. Rejected: a
separate session (two weekly sessions for anyone with a weekly review, which is the 09-05 cost).
`write_schedule` gained a weekday + time form and `session: weekly_review`, which `session_kind`
recognises, so a user with no weekly review can be offered one.

**Built (plan § 11c):**
- the back burner — trivia silent 21 days, parked a week after a weekly notice, guarded classes
  asked instead; the dry run while `back_burner` is off;
- the weekly material — MOVED, CLASH, SLIPPING with at most 2 questions, ONE CLOCK — with its
  conduct in `synthesizer_scheduled_sessions.md`;
- `update_task keep`;
- the signals file with daily ledger rows, and `record_signal`, which is refused off a user turn;
- `ranking_report --back-burner / --signals`.

Red edits in this session: one `synthesizer.md` bullet and the `record_signal` grant in both
routing files. **"No mention"** means the user's own words, a recorded change, or opening the
task. Metatron's words never count, or the notice would reset the clock it announces.

**Fable's diff review: 11 findings, 8 reproduced.** The two that mattered:
- *"keep that one" had no recorded form*, so the task was parked anyway;
- *unrelated words in a long weekly reply counted as the notice*, so a task could go unannounced.

Both are fixed: the `keep` action, a same-day mention clearing a notice, and a notice needing the
task named and a parking word in one sentence. Also fixed: revival only on the same commitment, a
two-question cap, honest wording in notices-only mode, the offer spent by any "week", quiet-hours
weekly times, re-judges resetting clocks, and signal-day gaps. Accepted, with reasons: the shared
stemmer, a person not in contacts, paraphrase in `record_signal`.

**Phase 2's open items:** the behind lead stays open (no walkthrough yet). The passion double
count was measured on the VM — 23 records, 0 naming a passion, 3 goal-linked — so it is bounded,
and it closes in the passion live check.

**Also:** the phase 2 config test failed on clean HEAD after `129f3fb`; the test was corrected,
and the code's off fallback for the billed lookup was kept on purpose. Tests: `test_ranking_v2`
45 → 58, Part A 21/21, QA sweep 12/12. Walkthroughs written: the dry-run review, the weekly live
check, the first monthly signals review.

