### 2026-11-25 (`mike`'s goals walkthrough: every goal gone through, Bulgarian talked through and parked by Mike, ten misses sent to a fix build)

**What changed.** `goal_talk: true` (`367efc6`, deployed by Mike 11-25; VM HEAD read as `367efc6`).
Mike ran the walkthrough (`archive/handoffs/2026-11-24-goal-network-mike-goals-walkthrough-prompt.md`)
live in the app. Claude Code read the VM read-only over IAP SSH (conversation log seqs 011–037,
`goals.yaml`, `goal_talk.json`, `tasks.yaml`, `day_plan/log.jsonl`). No persona file was written
from the Mac.

**Settled per goal (Mike, in the app):** `q2` Metatron work: the draft outcomes were judged largely
met, and the new `done_means` is Family mode live, the Build integration, a Founder's Associate
hired, and first user research. `q3` swim standing. `q1` outings: the 6-week cadence is an annual
average; shows cluster, socialising doesn't. `q5` UK taxes: direct to HMRC, no UK forms. `q6`
Prudential: decisions done, goal completed, and an execution task due **2026-12-15** (Mike;
`ob_261125_e066f3`, made in the app after the walkthrough). `w1` bricklaying parked to 2027-06-01
(courses start Aug/Sep). Reading and films: logs updated, reading kept flexible (Ben's naps first).
US-tax gathering task opened for early January. Every weekly goal was accounted for (Mike).

**Step results.** Step 1 PASS (Mike). Step 2: partly met (misses below). Step 3, the Bulgarian
talk: one-line hand-over and an unprompted Interviewer opening PASS; started from `playbook`; why
now, where now, the week ("comes out of Metatron and exercise") and want-vs-should were all covered;
nothing internal was said; it returned to Synth PASS. Then **Mike chose to park it until
2027-01-15** (Maria back as a conversation partner). Step 4: FAIL on its letter (`verdict: parked`,
no `full` pass, 4 turns, 3 of them Mike's), but it is a faithful record of Mike's choice.
**Part A's live check Stage 2 is blocked** until `q4` is completed.

**Misses (all to one fix build, `archive/handoffs/2026-11-25-goal-walkthrough-misses-fix-build-prompt.md`):**
1. A parked goal never comes back. `revisit_on` is written and read by nothing, and `prompt_view`
   hides parked goals, so the "we'll bring it back in mid-January" Mike was told has nothing behind it.
2. Exercise "on hold until mid-January" was claimed twice (seqs 032, 037) and recorded neither time.
   The persistence-claim check is log-only and its patterns miss both phrasings.
3. The talk parked with the weekly time never agreed by Mike (120 min was the Interviewer's own
   proposal). The years-at-this-rate realism line was never said.
4. Synth over-claimed afterwards: "talked it out fully… weekly load settled".
5. No way to settle a goal now and start it later (no `starts_on`).
6. Goal codes and a raw task id were shown to Mike.
7. `d1` vocabulary was sized L and parked with its parent.
8. Two questions at once (taxes, Prudential).
9. One failed reply (seq 015, undiagnosed).
10. Synth lost its place after Bulgarian (went back to taxes; Healthier Diet was never taken).

**Decisions.** Mike: fix first, then resurrect Bulgarian to complete the assessment, with the start
still mid-January. One build was recommended over several backlog items, because the fixes share
files and the rerun tests them together. Rejected: a Bulgarian talk now with no start date. It would
be planned at once when `rolling_wave` flips, which is not what Mike wants. Rejected: closing the
misses by agent-file prose alone, because the false claims and the hidden parked goals are code-decidable.

**Believed true earlier that turned out wrong.** The walkthrough prompt assumed a parked verdict was
a dead end only for the full pass. It is also a dead end for the goal itself, since nothing re-raises it.
The phase 3b design assumed "saying yes again resumes the same talk", but a *parked goal* can't hold a
talk at all (`goal_talk._gone` ends it), so Synth must re-activate the goal first.

**Next, in order:** the fix build (Opus 5.5, Fable 5.2 review + verify) → Mike deploys → exercise
hold re-said and Bulgarian completed (`active`, `starts_on` 2027-01-15) → part A Stage 1 (any time;
offered for the build's deploy if not started) → Stage 2 from 01-15.

