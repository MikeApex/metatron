Model: Opus 5.5 to build (agent files and `core/orchestrator.py` are touched, and the judgement is the work, so nothing is delegated); Fable 5.2 for the diff review and the verify pass.

# The goals walkthrough's misses — fixed, then Bulgarian talked through again, then part A's live check

**Where this comes from.** `mike`'s goals walkthrough ran on 2026-11-25
(`archive/handoffs/2026-11-24-goal-network-mike-goals-walkthrough-prompt.md`). Every goal was gone
through and the Bulgarian talk ran. **But `q4` was not made plannable**: Mike parked it until
2027-01-15 (when Maria is back as a conversation partner), so it has no full pass, and **part A's
live check Stage 2 is blocked**. Mike's parking was a real choice. The misses are in what Metatron
did around it, and Mike wants them fixed before Bulgarian is talked through again "to complete the
assessment".

**The evidence** is in the VM's `data/personas/mike/conversations/2026-11-25.jsonl`, seqs 011–037,
read 11-25 by SSH (`gcloud compute ssh metatron-vm --zone=us-central1-a
--project=metatron-ai-499810 --tunnel-through-iap --command='cd ~/multi-model-mcp && .venv/bin/python -' < script.py`
— read-only). Re-read it yourself and don't trust this summary. `config/personas/**` and
`data/personas/**` are VM-owned and Denied here; nothing is written to them from the Mac.

## Read first

1. `SESSION.md`, `ROADMAP.md` (the pre-edit check; `core/orchestrator.py` carries the A8 refactor
   claim — check that nothing you touch is about to move).
2. Plan `archive/plans/goal_task_network_plan_2026-11-18.md` §§ 17–18 (parts A and B as built).
3. The log fragment for the 11-25 walkthrough in `archive/log/` (written at that session's close).
4. The files: `tools/goals.py` (`vet_goal`, `prompt_view`, `update_goal`), `tools/goal_talk.py`
   (`_gone`, `realism`, the GOAL TALK block), `tools/goal_network.py`, `core/orchestrator.py`
   (`_PERSISTENCE_CLAIM_PATTERNS` ~L8672, `find_persistence_claims`, `_COMPLETION_CLAIM_RES`
   ~L2164 and `enforce_pending_receipt`), `config/agents/synthesizer.md` § goals,
   `config/agents/goals_interviewer.md` § Talking one goal through.

## What a user saw, and what was found in the code

| # | What Mike saw (seq) | Found |
|---|---|---|
| 1 | **"When we bring it back in mid-January" — nothing will.** Bulgarian parked to 2027-01-15, bricklaying (`w1`) to 2027-06-01 (seqs 025, 030) | `revisit_on` is **written** (`goals.py:238`) and **read by nothing**. `prompt_view` drops parked goals from every prompt, so after parking a goal is invisible until someone remembers it |
| 2 | **Exercise "on hold until mid-January" — said twice, recorded neither time** (seqs 032, 037: "I have corrected the standing records", "put purposeful exercise and heavy lifting on hold") | `w4`, `w5` still `active`, no context, no date (read 11-25 after seq 037). The persistence-claim check is **log-only** and its patterns match neither phrasing. There is no "on hold" status: parked + `revisit_on` is the only representation |
| 3 | **The talk ended after 3 of Mike's messages, with the weekly time never agreed** (seqs 021–025; Interviewer proposed 120–150 min, Mike never said a figure) | `min_user_turns` (4) gates only `active`; `parked` closes at any count. `weekly_minutes: 120` was recorded from the Interviewer's own proposal |
| 4 | **The realism point never landed**: 300–450 h quoted, but never "at ~2 h a week that's 3–4 years"; no stages named | `realism()` exists and its line is in the block. The Interviewer did not say it, and nothing requires it to before a verdict |
| 5 | **Synth then said "we have talked it out fully… weekly load settled… we won't need to re-litigate"** (seq 026) | An over-claim about settled fields. Same class as #2 |
| 6 | **Bulgarian can't be finished now and started later**, which is what Mike wants | There's no start date on a goal. An `active` + `full` goal is planned in waves as soon as `rolling_wave` is on |
| 7 | **Internal ids shown**: "goal q5", "(Q5)", "W1", "W4/W5", and a raw task id `ob_261121_ec921f` (seqs 016–018, 027–031) | `filter_output()` catches tool/agent names, not goal codes or task ids |
| 8 | **The daily vocabulary habit was sized L and parked** with Bulgarian (`d1`: `size: L`, `weekly_minutes: 135`) | `d1` is the practice under `q4` (`parent_goal: q4`), not a goal to vet. Nothing stops a vet of a child habit |
| 9 | **Two questions at once** on taxes and Prudential (seqs 016, 017) | The synthesizer's goal walk-through asks "at most one question" in prose only |
| 10 | **"I did what I could on that, but couldn't finish the reply"** (seq 015) | Not diagnosed. Run `/metatron-troubleshoot` 2026-11-25 seq 015 first, and fix only if the cause is in scope |

**Settled in the app on 11-25 (no build needed):** the Prudential execution task exists, due
2026-12-15 (`ob_261125_e066f3`). Every weekly goal was accounted for (Mike). The exercise hold
(#2) **still has to be recorded**. It's done in the app after this build, so the fix is exercised
(§ After the build, step 2).

## Rulings to get from Mike before any code

Put each one as options plus a trade-off plus a recommendation. Don't punt.
1. **How a parked goal comes back (#1).** Recommended: from its `revisit_on` day, the goal shows in
   Synth's goals view under a "back today" line, and Synth asks once whether to take it up, re-date
   it or let it go. For an L goal whose talk task is done, a fresh talk task opens that day.
   Alternative: a task on the date (cheaper, but a task can be skipped and the goal stays invisible).
2. **A goal settled now but started later (#6).** Recommended: a `starts_on` date on the goal. An
   `active` goal with `starts_on` in the future keeps its full pass, isn't planned, isn't counted
   as slipping and isn't re-vetted until that day. Then part A plans it on the first tick on or
   after. This is what lets Bulgarian be completed now and begin 2027-01-15.
3. **An "on hold" (#2).** Recommended: no new status. "On hold until X" is `parked` with
   `revisit_on: X`, which #1 then brings back. Check that this is how Mike reads "on hold".
4. **The false "recorded" claim (#2, #5).** Recommended: on a goal turn, a claim that a goal was
   changed with no goal write in the turn's trace is **replaced**, not logged. Tell the user it
   wasn't done and offer to do it. Put it in `_COMPLETION_CLAIM_RES`'s enforcing path, scoped to
   goal claims only, because the log-only path's precision-over-recall reasoning (the note above
   `_PERSISTENCE_CLAIM_PATTERNS`) still holds everywhere else. Mike called false action claims
   "unacceptable" (`[DB-0815-11]`).

## The build

1. **Parked goals come back** (ruling 1), in code, in the daily sweep. It's a date compare, with
   no model call.
2. **`starts_on`** (ruling 2): `goals.py` editable fields, `vet_goal`, the planner sweep and part A's
   triggers all honour it. The talk can record it.
3. **A talk can't end without the user's own weekly time (#3, #4).** `parked` and `active` from a
   talk both need `weekly_minutes` that the user stated or agreed to, not only proposed. Decide
   with Mike how code tells the difference (e.g. the Interviewer records `weekly_minutes_from: user`,
   checked against the user's turns). `realism()`'s years-at-this-rate line must have been said in
   the talk before a verdict, checked in code against the Interviewer's turns. A parked talk with
   fields still open says what's open and keeps them for the next talk.
4. **Goal claims enforced** (ruling 4). Add patterns for this session's two misses ("put … on hold",
   "corrected the (standing) records", "parked … until") and "we have talked it out fully"-style
   claims about settled fields.
5. **Ids out of user text (#7)**: goal codes (`[qwdl]\d+` in a goal context) and task ids
   (`ob_\d{6}_[0-9a-f]{6}`) stripped or replaced by the title in `filter_output()`'s path. Check the
   false-positive risk on ordinary text ("Q4 results", "W1 postcode") and scope accordingly.
6. **A child habit isn't vetted as a goal (#8)**: `vet_goal` on a goal with `parent_goal` refuses
   `size L`, and parks only with its parent, unless the user asks for that habit by name.
7. **One question per goal (#9)**: a rule a check can decide → code if it can be checked cheaply
   (count question marks in a goal-walk turn?). Otherwise one sentence in `synthesizer.md`. Say which and why.
8. **Seq 015 (#10)**: troubleshoot first, then fix it or file it, with Mike.

**Agent files** (`synthesizer.md`, `goals_interviewer.md`) are Amber since 11-24 and **never
delegated**: make those edits yourself. Keep each to the lines the code changes require.
`core/router.py`, `core/persona.py`, `core/scheduler.py` and `core/spend_guard.py` are Red. If a fix needs one, ask first.

**Tests:** a new `tests/test_goal_walkthrough_fixes.py` with one check per row above, using fixture
personas and stubbed models. Re-run part A, part B, phases 1–2, `test_ranking_v2.py` and
`test_task_ranking.py`. Known clean-HEAD failures stay unchanged (plan § 18 lists them).

**Fable 5.2 diff review, then verify.** Spawn a fresh Fable 5.2 agent (Agent tool, `model:
fable`) with the diff and the table above. Give it **not your conclusions**: ask what will break
and what a user would see. Check every finding against the code, then fix or rebut it with
evidence. Then a Fable verify pass on the fixes, because a fix can introduce a new miss (it did
in part A: verify N1). Record the table in a new plan § 19.

## After the build — Mike deploys, then the walkthrough is finished

1. Mike runs `./deploy.sh`. Confirm VM HEAD over SSH.
2. **In the app, Mike re-says the exercise hold** ("exercise and strength training on hold until
   mid-January, stretching only"). Read `w4`/`w5`: `parked`, `revisit_on` in mid-January. If Synth
   claims it without writing it, ruling 4's replacement should show instead.
3. **Bulgarian, resurrected and completed.** Mike says something like *"Let's pick Bulgarian back up
   and finish talking it through — it still starts mid-January."* Synth sets `q4` back to `active`
   (a parked goal cannot hold a talk: `goal_talk._gone`) and offers the talk. Then run the original
   walkthrough's **step 3 pass list**. In particular: the weekly time is agreed by Mike, the
   years-at-this-rate line is said, and the verdict is `active` with `starts_on: 2027-01-15` (or
   Mike's date). `d1` comes back to active as the practice, not as an L goal.
4. **Step 4 read** (the original prompt's script, plus `starts_on` and `revisit_on`). Pass:
   `size: L`, `vetted.pass: full` by `goals_interviewer`, `weekly_minutes` and `done_means` set,
   `starts_on` set, `talk now: None`, last talk `verdict: active` from `playbook`, log rows
   `GOAL_TALK_START` → `GOAL_TALK_DONE`.

## Part A's live check — so it doesn't get lost

`archive/handoffs/2026-11-24-goal-network-phase-3a-live-check-prompt.md`.
- **Stage 1** (projected finish + re-vet on existing goals) **doesn't depend on any of this** and
  can run any time since part A was deployed (11-25). If it hasn't started by the time this build
  deploys, put the two flips (`projected_finish: true`, `revet: true`) to Mike for the **same
  deploy**, and hand Stage 1 on as the next session. Check this build's goal changes (`starts_on`,
  parked-goal return) don't make Stage 1's reads ambiguous. A parked or not-yet-started goal must
  not fire a re-vet.
- **Stage 2** (Bulgarian in waves) is unblocked by step 4 above. Its "next tick" check changes:
  with `starts_on: 2027-01-15`, flipping `rolling_wave` must **not** plan `q4` before that day. That
  is a pass in itself (and a check for this build). The waves themselves are read from 01-15. Edit
  the live-check prompt's Stage 2 to say so, in this session.
- Make both appear in `SESSION.md`'s **Next** at `/archive`, in order: this build → the
  Bulgarian completion → Stage 1 (if not already running) → Stage 2 from 01-15.

## Costs

- **Build:** Opus 5.5, ~$40–80. The Fable review and verify, ~$15–25.
- **Run:** the parked-goal return and `starts_on` are date compares in the daily sweep, so no
  model calls. The goal-claim replacement is a regex over replies already produced. A replaced
  reply costs nothing extra (it's a fixed sentence). The id strip is code.
- **Ancillary:** two optional fields per goal. A replaced reply is a worse turn for the user when
  the pattern is wrong, which is why it's scoped to goal claims.
- **Unseen:** a false positive of the goal-claim replacement is only visible in the quality log.
  Have it log every replacement with the sentence, and read that log at Stage 1's first weekly review.
- **What persists:** nothing new billed by time.

## Close

1. A log fragment (`archive/log/`): rulings, what was built, the Fable table, and the step 2–4 passes or
   fails with what was read and when.
2. `/archive`.
