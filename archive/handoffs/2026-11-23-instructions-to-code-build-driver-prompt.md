Model: Opus 5.5, high effort. This is a long driver session that plans, delegates and reviews. The Red agent-file edits are judgement work and stay in this chat; Amber/Green builds go to subagents; every plan and diff gets a Fable review.

# Build driver: agent instructions → code (from the 2026-11-23 sweep)

You are the **driver** for five build stages, run in sequence from this one chat. Mike sets you
going, approves the Red edits when you ask, and otherwise leaves you to finish. **Your job ends at
committed and pushed. It never includes deploying**: `./deploy.sh` is Denied, and the deploy plus
the live checks are a list you hand to Mike.

## Read first, in order (the pre-edit context check applies to every file you touch)

1. `SESSION.md`, then `ROADMAP.md`.
2. `archive/plans/agent_instructions_to_code_sweep_2026-11-23.md`, **§ 6 first**: Mike's rulings,
   which override anything earlier in the document.
3. `archive/plans/agent_instructions_to_code_sweep_review_2026-11-23_fable-5-1.md`, the Fable
   review. Its corrections to #1, #5 and #9 are accepted; the rest of it is input, not ruling.
4. `.claude/rules/agent-files.md`, `.claude/rules/orchestrator.md`, `.claude/rules/deploy.md`,
   `.claude/rules/docs-and-logs.md`.
5. `DEV_BACKLOG.md` entries `[DB-0810-11]`, `[DB-0808-09]`, `[DB-0804-02]`, `[DB-0902-01]`,
   `[DB-1029-09]`.

## Standing rules for the whole run

- **Red is never delegated.** Agent files, routing files and `core/{router,persona,scheduler,spend_guard}.py`
  are edited by you, in this chat, in the main working tree. **There are exactly two Red rounds
  for the whole run** (Mike, 2026-11-23). Before each one, send Mike a push notification (load it
  with `ToolSearch select:PushNotification`): *"Red round N: K edits ready for approval."*
  - **Opening round, before any code:** every Red edit that does not depend on new code.
    - the `read_goals` grant removal (Stage 1);
    - new grants a later stage needs (Learning & Growth's task tools for #15);
    - the § 2b contradiction fixes and the D12 task-length rule;
    - instruction-honesty fixes (#7's false sentence, #24, Recreation's `HORIZON_ITEMS` line
      for #11, the stale Coordinator claim in #6).

    Write the full list of the closing round's edits during Stage 0 planning, so the opening
    round includes nothing that belongs in it.
  - **Closing round, after every stage's code is built and tested:** every edit that deletes an
    instruction the new code now carries. A line deleted before its code exists would leave a
    gap. Until the closing round, an agent carries both the instruction and the code that
    enforces it. That duplicate is harmless: nothing deploys until the end.
  - **After the closing round:** one Fable review of all the Red diffs together, then the tests
    again. If the run stops early, skip the closing round: the earlier commits are still correct
    with the old instructions left in place.
- **Amber/Green code** goes to a `general-purpose` subagent with `isolation: "worktree"`. Brief it
  with the plan section, the exact files, and the tests to write. It commits nothing. You bring its
  diff into the main tree yourself.
- **Two chats share this working tree.** A data-object build runs in another chat. Before staging,
  `git diff` every file. If a file you need carries uncommitted lines you did not write, **stop and
  ask**; never merge over them. Stage by explicit file list only.
- **Every stage runs the same loop:**
  1. Plan, written to `archive/plans/` with a dated, specific name.
  2. Fable plan review: an `adversarial-reviewer` subagent, `model: "fable"`.
  3. Amber build in a worktree.
  4. Note which closing-round Red edits this stage needs; don't make them yet.
  5. Tests: the suites the plan names, plus `python3 scripts/check_agent_tools.py` and
     `python3 scripts/check_claude_md_claims.py`.
  6. Fable diff review: a `codebase-reviewer` subagent, `model: "fable"`.
  7. Fix what it finds.
  8. Commit, then push.

  Commit messages say what a user would notice, with no attribution footer. After each stage,
  run `python3 ~/.claude/tools/archive_chats.py`.
- **Stop and ask Mike** (with a push notification) when:
  - a test still fails after two fix attempts;
  - a review finds a structural defect;
  - a plan needs a decision that § 6 does not make;
  - a file collides with the other chat;
  - spend passes 60% of the budget before Stage 4.

  Otherwise, keep going.
- **Clinical rule, in every stage:** `MUST_SURFACE` / `CLINICAL_CONCERN` / `MEDICATION_MISSED_CRITICAL`
  veto any skip, and code may add a flag but never clear one. Anything touching Finance arithmetic
  or clinical flags goes through `tests/run_a4_safety.py`. Mike lifted the A4 suspension for these
  fixtures (D10): state the expected cost (about $3–4) in chat before each live run.
- **The review's misses are in scope** (Mike, 2026-11-23): 18 of the 19, listed by stage below as
  "M1"–"M19", using the review's MISSES numbering. **Not M15**, the wishes-store read: Mike
  skipped it as 11-05 review #29. Each one gets the same plan review as a sweep finding. A miss
  the plan review finds wrong is dropped and reported, not forced. Do not build anything § 6
  defers.

## The stages

**First, check the data object is live.** Mike holds this run until the data-object project is
finished. Confirm that the "medication taken today" default data object exists, is committed, and
has a reader that code can call. If it is not there, stop and tell Mike; don't build around it.

**Stage 0: rulings into the records** (no code)
- D3: amend "config files are the product; code is infrastructure" in all three copies:
  - `CLAUDE.md` § Key Design Decisions;
  - `.claude/rules/orchestrator.md`;
  - the rebuild notebook.

  Use the wording *"config owns judgement and policy; code owns procedure, evidence and anything
  a rule can decide exactly"*, with one clause of why.
- D2: append a closing round to `archive/plans/code_dominant_rebuild_notes.md` that points to the
  sweep document, and mark the notebook closed.
- D1 is already done. `[DB-0810-11]` was closed on 2026-11-23 into
  `archive/backlog_closed_2026-11.md`, and `temperature` has its own inbox line. Nothing to do.
- CLAUDE.md trap 6: correct "only two agents on the cached path" (eight specialists have been on
  it since 08-28). Keep the edit inside the 300-line ceiling.

**Stage 1: the goals bug** (#5, corrected form). Remove the `read_goals` grant from
`work_vocation` and `finance` in **both** routing files, and the two "call `read_goals`" lines.
Do **not** change `tools/goals.py`: its writers read the raw file and write it back. Test: the
grant parity check passes, and `check_agent_tools` exits 0.

**Stage 2: C1, session shape**
- #1: refuse `USER_CORRECTION` / `INSTRUCTION_CHANGE_REQUEST` when there is no real user turn.
  Read `[DB-0902-01]` first and do not duplicate it.
- #2 with D4's write guard: Mental Wellbeing and Physical Health are added on morning_brief and
  evening_close, through an explicit mode, and write no logs on a turn with no user words. Keep
  the typed-greeting half of the rule.
- #4: the 5-per-key cap. The function-call move is measured only, not switched.
- #10: chain limit in code (`[DB-0804-02]`).
- M6: Pattern Miner's tracker write merges into `patterns` only and never replaces follow-ups or
  held items. **Data loss**, so do it first in this stage.
- M7: `CLARIFICATION_NEEDED` holds the writing specialists. Mental Wellbeing and Physical Health
  are never held.
- M10: drop `ORIGINAL_MESSAGE` from the Coordinator's package, and point the Synthesizer at the
  user's own text.
- M11: a `routing_miss` key in the `[CONTEXT]` block, parsed in code, in place of the tool round.

**Not #3** (D13: wait for capture fidelity).

**Stage 3: C3, the hard-fail domains**
- #8: the medication check.
  - Computed in code from the medication data object.
  - Runs on **every** Physical Health dispatch, in every mode.
  - Runs **after** the specialist returns, so a dose logged in this same turn counts.
  - Code may add the flag; nothing clears it.
  - Needs a per-medication due time or a cut-off hour, so an evening dose isn't flagged at the
    morning brief.
  - It costs no model turn. Test it with fixtures in the A4 runner.
- #13: Finance period totals per category, computed in code, plus fixtures in the A4 runner.
- #18 / D8: a scripted Goals Interviewer safety scenario in the A4 runner. It must be done before
  the second user's first interview.
- M8: a clinical flag without `MUST_SURFACE` gets it added by code, and a missing journal record
  is written by code. Add-only.
- M9: on a turn where the suicide flag fired on the user's own words, code checks that the reply
  carries the configured crisis line. Add-only, never a rewrite of the rest.
- M17: cessation streaks are counted by code, alongside #14.

**Stage 4: C2, evidence handed in**
- **Step 0: measure.** Find a read-only way to see current first-turn tool sequences on the VM:
  `docs/INFRASTRUCTURE.md`, the existing read doors, then the trace tooling. If there is none,
  say so and build anyway, labelled unmeasured.
- Then build:
  - #22: per-agent prefetch into the user message, never the system prefix. Watch the 4,096-token
    cache floor for the Synthesizer and Coordinator.
  - #12: exact-match contact resolution, plus the nickname-prefix signal.
  - #14: domain counters, from the specialist's own log fields, written only on real user turns.
  - #15: skill practice into ledger habits. Add the task-tool grants Learning & Growth lacks; those
    are Red edits.
  - #6: pass `PROACTIVE_FLAGS` and the PM headline into directives.
  - #20: Pattern Miner prefetch, plus M16 (use its granted baseline tools).
  - M1: a "newly captured, confirm in one clause" line for the Synthesizer, built from the
    arguments `write_contact` and `write_profile` actually received.
  - M2: the tone shape handed over with #12's resolved recipient.
  - M3: contacts with an `important_dates` entry in the next N days, handed over with the
    overdue list.
  - M4: each held item stamped with its first-held date and shown as "held N days".
  - M12: pending confirmations kept as ledger `waiting` rows only.
  - M13: code writes Logistics' log entry from the actions that actually ran.
  - M14: `[VERIFY]` events re-checked on the next calendar read.
- **#9 last, and only once #8 and #14 pass:** wire quick mode (code passes `mode: quick` into the
  directive), with Logistics' horizon filing carved out. First re-run the A4 Physical Health
  scenarios on quick, to confirm the medication check still fires. D5: both horizon channels
  stay.

**Stage 5: C4, one channel per signal**
- #7 (instruction honesty only; both channels stay, per D5), #11, #16 (at dispatch, beside #12,
  per the review), #17, #19 with D7 (including `CLARIFICATION_NEEDED`), #21, #23, #24, and #25
  (flag closed venues; don't hide them).
- The § 2b contradictions:
  - b.1: one morning opening;
  - b.2 / D12: **estimate task lengths, update the estimate on evidence, and ask only for an
    unknown task**; one home for the rule;
  - b.3–b.6.
- M5: an append mode for `write_persona`, so saving one preference never re-types the others.
- M18: flight and line checks report only disruptions, plus a throttle for the
  one-request-a-second limit.
- M19: a quality event when the reply contains a listed "enjoy …" phrase. Detection only,
  never a rewrite.

## Final report (in chat, numbered, plus a file in `archive/plans/`)

1. What a user will now notice, stage by stage; what was committed (hashes); what was skipped
   and why.
2. **Mike's deploy list:** the commits, `./deploy.sh`, and for each stage one live check (what to
   do, what to see, pass or fail).
3. Any miss or finding dropped at plan review, and why.
4. Spend against budget.

Then run `/archive`.

## Budget

- **Build:** about 1.8–2.1M weighted input tokens across Stages 0–5. The 18 misses add about
  350–450k to the original estimate:
  - four plans at high, about 100k each;
  - builds about 650k;
  - Fable reviews about 300k;
  - driver overhead.
- **Live gates:** about $3–4 per A4 run, two or three runs.
- **Run (after deploy):**
  - #2 about $0.05/day/user, doubling 2027-01-01;
  - #22 adds a fraction of a cent per specialist call and saves 1–2 turns;
  - everything else about 0.
- **Unseen:** no persistent state created, except Stage 2's chain counter, which lives on the
  request and dies with it.
