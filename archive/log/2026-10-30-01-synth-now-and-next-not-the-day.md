### 2026-10-30 (the Synthesizer says what to do now and the one thing next, not the whole day) — `547c446` + this close-out — **committed, not deployed**

**Incoming handoff:** none consumed. Mike opened the session from `/metatron-code` with a review
of 10-28 conversations: Synth's schedule rundowns were too detailed. *"Metatron's
responsibility is to ensure you keep on schedule and REMOVE the need to be aware of the
schedule."* The other 10-30 prompts (`/backlog deep`, the attack prompt) are untouched.

**Evidence (VM, mike, 10-28 → 10-30):** the morning brief read out the whole day (10 items on
10-30). The evening close said *"Looking at tomorrow in full…"*. 5 of 7 user-turn replies on
10-28/29 ended with a 3–4 item schedule tail. *"I have estimated 30 minutes… let me know"*
appeared 6× in two days. Day-plan nudges (live since 10-29) were nearly right but added "up next".

**Believed true, wrong:** that this was an instruction gap. `synthesizer_day_plan.md` had said
*"never recite it"* since 10-27 (`9f2eeac`) and it did not hold. Code handed Synth the whole day
every turn (R2, 10-24), and two other instructions demanded rundowns:
`synthesizer_scheduled_sessions.md`'s *"Tomorrow, in full"* and *"2–3 items… propose a
sequence"*, and `horizon.review_block` (Mike's 09-05 *"run through all of tomorrow"*). **A rule
telling a model not to use data it is given is weaker than not giving it the data.**

**Mike's rulings (S1–S6, plan § 2):**
- Brief: now + next + anything important, often nothing.
- Close: tonight, first thing tomorrow, the same threshold. **Supersedes 09-05.**
- User turns: the schedule only when something is new to do, or to announce free time.
- Fix in code; revert if it fails.
- Tasks are suggested in free time, weighed by the user's preferences.
- **R2 is amended**: Synth no longer holds the whole day, and fetches it with `read_day_plan`
  on request.

**Built (`547c446`):**
- `render_block`: Now, one Next, Free, Important (≤ 2, code-ranked, never a calendar event by
  being on it), Asks from the whole day.
- `render_full` + `read_day_plan`, plus three Red edits: the `synthesizer.md` tool line and
  grants in both routing files.
- `horizon.prep_items` replaces `review_block`. **The precursor is the signal, not `detail`**:
  every finding on mike's ledger carries a detail.
- Both conduct modules cut to match. The day-plan module ended ~flat (1,444 → 1,463 words), not
  shorter as planned: the user-turn and estimate rules cost what the cuts saved.

**Reviews:** two Fable rounds, both reconciled in `archive/plans/synth_now_next_plan_2026-10-30.md`
§§ 8 and 10.
- Plan review, 8 findings, all accepted. The biggest: "Important" as first drafted was the Later
  list renamed. The Red Book paperwork lives in horizon findings, so deleting `review_block`
  would have lost it.
- Diff review, 3 bugs, all fixed:
  1. "Tomorrow" read today's events.
  2. Free time was announced inside family time.
  3. The cap cut the prerequisite first.
- Eight suites green, `qa_sweep` 12/12.

**Stage 2 — the planner places the prep as a task (Mike: fold in, at the end; then: new chat, spec
further).** Draft § 9 failed review on three structural findings: same-day prep landing after
the event, two processes writing the horizon ledger, and a revert that didn't revert. There were
six local ones too. **Rejected:** building it this session on the reviewed draft.
**Next:** `archive/handoffs/2026-10-30-prep-tasks-stage-2-spec-prompt.md`.

**Owed:** deploy `547c446` (Mike). Live check: next 07:31 brief, an "I'm home" reply, and the
20:01 close, with no rundowns.

