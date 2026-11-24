Model: Opus 5.5 — reading live VM state and judging whether a question was asked as a question, not a verdict, is judgement work; nothing here is built.

# Goal–task network phase 3 part A — the live check (§ 5): a goal's finish watched, a re-vet asked, a large goal planned in waves

**Mike-gated: a walkthrough, not a wait** (CLAUDE.md). Mike deploys and flips; you prepare each
step, read the VM (read-only, `/monitor/file` via `scripts/sync_dev_backlog.py`'s token, or Mike
pastes), and judge. Plan: `archive/plans/goal_task_network_plan_2026-11-18.md` § 17.

## Two stages, because rolling waves need part B

Mike ruled (2026-11-24) that **an L goal is planned in waves only after the Goals Interviewer's
full pass**. Part B builds that. So:

- **Stage 1 — after part A is deployed (any time):** projected finish and the re-vet, on goals
  `mike` already has. ~20 min with Mike, then two weekly reviews of watching.
- **Stage 2 — after part B is deployed and `q4` Bulgarian has had its re-interview:** one real L
  goal planned in waves over two weeks, plus a deliberately ignored step that triggers a re-vet.

## Before Stage 1

1. Read `SESSION.md`; confirm the VM carries part A's commit (§ 17 names it). If not, stop: Mike
   deploys first (`./deploy.sh` is his).
2. Confirm on the VM that the three flags are still off and nothing new has been written:
   `data/personas/mike/day_plan/projects.json` has no `revet` key and no `finish` on any request.

## Stage 1 — projected finish and the re-vet

1. **Mike flips two flags** in `config/modules/day_plan.yaml` (`projected_finish: true`,
   `revet: true`), commits and deploys. `rolling_wave` stays off until Stage 2.
2. **Next morning, read** `projects.json`:
   - `q5` (UK taxes) has `finish: {baseline, late, last: {projected, pace, pace_source, …}}`.
   - **Pass:** `last.projected` is on or before 2026-12-30 (the PAYE cut-off the plan was built
     to), or, if after, a `finish.alert` exists AND the morning brief said the new date with one
     fix, once. Check the brief's text in the day's conversation log, and that the next brief did
     not repeat it.
   - Note `pace_source`: `stated`/`default` until two tax steps are done, then `actual`.
3. **Trigger 1, deliberately.** Mike picks one goal step to ignore on purpose — a step of a goal
   that is **not** an obligation (an obligation is asked only about its date; check that separately
   if a tax step is the one slipping). Leave it undone, or tap "Not yet", on 4 of 7 days.
   - Prerequisite: the goal must have a plan step on the day's list. If no non-obligation goal
     has one, say so and use the tax plan to check the obligation wording instead.
   - Read `projects.json` → `revet.<goal id>.fires` daily. **Pass:** one `noncompliance` fire
     the day the fourth day is reached, never a second while unanswered.
4. **The weekly review** (Mike's weekly review day). **Pass, all of:**
   - the review carried ONE goal check, phrased as a question ("how is it going — still worth the
     time?"), never a charge ("you've skipped it four times");
   - for the obligation: no "do you still want it", only the date and what would help;
   - after Mike answers, `ranking_signals.jsonl` has a `revet_asked` row and — if he answered with
     a keep/park/drop — a `revet_answer` row, both `source: goal_network`, ids and counts only.
5. **Trigger 2** fires only for L goals vetted with a date; `mike` has none until Stage 2, so
   expect no `time` fires in Stage 1.

## Stage 2 — Bulgarian in waves (after part B)

1. Confirm `q4` shows `size: L`, `vetted.pass: full`, `weekly_minutes` set (Mike pastes the
   entry — `config/personas/**` is not readable from the Mac).
2. Mike flips `rolling_wave: true`, commits, deploys.
3. **Next tick:** `projects.json` → `requests.q4` is `planned` with `milestones` (first `current`,
   the rest `pending`) and `ids` for the first milestone's steps only. **Pass:** the task list holds
   only those steps (none of the later milestones); the first step appears on a day with room; the
   brief says once that it is planned and names the first step; `read_plan q4` (ask Synth for the
   whole map) lists the later milestones as outlines.
4. **Over two weeks:** steps are fed one at a time; `d1` Bulgarian Vocabulary keeps its own weekly
   time; at day 14 a `time` re-vet fires and the weekly review asks how it is going.
5. **The deliberately ignored step:** Mike ignores one Bulgarian step on 4 of 7 days. **Pass:** a
   `noncompliance` fire, asked in the next weekly review as a question, answer recorded.
6. If every step of the first milestone gets done inside the fortnight: the next milestone's steps
   appear within a tick or two, with no "it's planned" said again (`said: "silent"`).

## Revert

Each flag off restores phase 2 exactly. Re-vet records and finish state stay in `projects.json`
inert. A step already written stays an ordinary task.

## Close

Record each pass/fail in a log fragment (`archive/log/`), with what was read and when. A miss is
fixed in its own build, not here.
