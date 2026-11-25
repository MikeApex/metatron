Model: Opus 5.5. Mike is live in the app and you judge each result against the code. A missed pass here is a design question, not a mechanical one.

# Goal walkthrough fixes: the live tests, then Bulgarian completed, then part A Stage 1's reads

**State.** `26042b1` is deployed (Mike, 2026-11-25; VM HEAD confirmed). Plan
`archive/plans/goal_task_network_plan_2026-11-18.md` § 19 is the record: Mike's rulings 1–7, what
was built, and the Fable review and verify tables. Flags on the VM: `goal_talk`, `projected_finish`
and `revet` ON; `rolling_wave` and `satisfaction_gap` OFF. Synth's goals view was read after the
deploy and shows Bulgarian `q4`, bricklaying `w1` and `d1` (practice for `q4`) under "On hold".

**Read first:** `SESSION.md`; plan § 19; log fragments `archive/log/2026-11-25-04-*` (the
walkthrough) and `-05-*` (this build).

**VM reads are read-only, over SSH:**
`gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 --tunnel-through-iap --command='cd ~/multi-model-mcp && .venv/bin/python -' < script.py`
(the script is written to the session scratchpad). `config/personas/**` and `data/personas/**` are
VM-owned; nothing is written to them from the Mac. Every change happens in the app, by Mike.

## Test 1 — exercise on hold (ruling 3; the 11-25 seqs 032/037 miss)

Mike sends each as its own message and waits for the reply:
1. *"Exercise and strength training are on hold until mid-January when Maria is back; until then it's stretching only."*
2. *"Rename Strength and Flexibility Training to just Strength training. And add a daily goal: stretching, 15 minutes twice a day."*
3. *"The 'Perform morning stretches' task belongs under the new stretching goal, not Bulgarian vocabulary."* (It is linked to `d1` by mistake — `ob_261116_409349`.)
4. *"Delete the fitness note that says workouts are on hold until mid-January — the goals hold that now."* (`write_wisdom` key `training_availability_mid_january`, and `training_availability_constraints`, written at seq 032.)

**Read** `goals.yaml` (`w4`, `w5`, the new daily goal), the task's `goal_id`, and the fitness wisdom.
**Pass:**
- `w4` and `w5` are `active`, with `starts_on` in mid-January (2027-01-15 or Mike's date) and a
  `hold_note` about stretching. **Not** `parked` — Mike's words were "on hold until", which means
  `starts_on` (ruling 3).
- `w5` is titled "Strength training". A daily stretching goal exists. The task points at it.
- The two wisdom keys are gone.
- No goal code or task id appears in any reply.
- If Synth claimed a hold it had not made, the reply read *"I haven't actually put … on hold on
  your goals yet — shall I do that now?"*. Mike's yes then made it. Note whether this happened.
- Synth's view now lists `w4`/`w5` under "Taken on, starting later".
- Synth names the held goal's open task, "Find a personal trainer" (`w5`), and asks whether it
  waits until January. The code lists such tasks and never hides them (plan § 19, Fable S8
  rebuttal), so this question is what keeps the task from nagging.

**If it fails:** if Synth used `parked` instead of `starts_on`, that is the
`synthesizer.md` § A newly stated goal sentence not landing. Note the exact reply. Fixing it is a
one-line change made in the main session.

## Test 2 — Bulgarian brought back and talked through (rulings 1, 2, 5; walkthrough step 3)

Mike says something like *"Let's pick Bulgarian back up and finish talking it through — it still
starts mid-January."*
- Synth sets `q4` back to `active`. Taking a goal up from parked opens a fresh talk task, and Synth
  offers the talk once. Mike says yes. **Read:** `q4` is `active`, with no `revisit_on`; `d1` is
  back `active` as its practice, with no `size: L`; there is an open *Talk through: …* task.
- The talk (Goals Interviewer). **Pass, all of:**
  1. The weekly time recorded is **Mike's own**: a figure he says, or a yes to ONE figure the
     Interviewer names. The 120 on file from 11-25 is not taken as his. If the Interviewer tries,
     the result refuses it, and the next turn asks him.
  2. Before the verdict, the Interviewer says plainly what that time means in months or years
     (e.g. "at two hours a week, that's about three to four years"). Mike can answer: more time, a
     later date, or a smaller "done".
  3. One goal stays in focus. Nothing internal is said, and no ids.
  4. The verdict is `active` with `starts_on` 2027-01-15 (or Mike's date), and the talk hands back
     to Synth.
- If Mike parks it instead, the reply says what is still open. That is a pass for ruling 5b, but
  Stage 2 stays blocked.

## Test 3 — the read (walkthrough step 4, plus this build)

Read `q4`, the talk state (`interview/goal_talk.json`) and `day_plan/log.jsonl`. **Pass:**
- `size: L`;
- `vetted.pass: full`, `by: goals_interviewer`;
- `weekly_minutes`, `done_means` and `starts_on` set;
- no open talk (`talk: None`);
- the last `past` entry has `verdict: active` and `shape.source: playbook`, and its
  `their_minutes` contains the recorded figure, with `realism_said: true`;
- log rows `GOAL_TALK_START` → `GOAL_TALK_DONE`.

Then check the goals view lists Bulgarian under "Taken on, starting later — starts 2027-01-15", and
that `projects.json` has **no** `requests.q4` (it must not be planned before its day, even once
`rolling_wave` is on).

## Test 4 — part A Stage 1 (live since the 11-25 deploy)

Follow `archive/handoffs/2026-11-24-goal-network-phase-3a-live-check-prompt.md` § Stage 1 from
step 2. In short:
- **Next morning:** `projects.json` → `requests.q5` (UK taxes) has a `finish` record. Either it is
  on time, or a `finish.alert` exists and the brief said the new date with one fix, once.
- **Trigger 1 on purpose:** Mike leaves one non-obligation goal step undone, or taps "Not yet", on
  4 of 7 days. One `noncompliance` fire, never a second while unanswered.
- **The weekly review:** one goal check, put as a question, never a charge. For the taxes, only
  the date and what would help. `revet_asked` and `revet_answer` rows appear in
  `ranking_signals.jsonl`.
- **New with this build:** `w4`, `w5` and `q4` (starting later) get **no** re-vet fire and no finish
  alert.

**At the first weekly review, also read** every `FALSE_GOAL_CLAIM` and `GOAL_TURN_MULTI_QUESTION`
quality event since 11-25 (`data/personas/mike/` quality log). For each replacement, decide true or
false positive. A wrong replacement is the risk plan § 19 names, and the quality log is the only
place it shows.

## Then Stage 2, from 2027-01-15

The amended § Stage 2 of the same live-check prompt applies.
- Mike flips `rolling_wave: true` whenever he likes. Step 2a — the next tick plans nothing for `q4`
  before its day — is a check in itself.
- The waves are read from the first tick on or after 01-15. The 14-day re-check counts from
  `starts_on`.

## Anything else that needs doing (decisions for Mike; nothing filed)

1. **Synth lost its place after Bulgarian on 11-25** (fragment 04, miss 10). It went back to taxes,
   and Healthier Diet (`d2`) was never taken. This build did not address it.
   - Recommended: watch whether it recurs in Test 2 now that the talk hands back cleanly.
   - If it does, a small build: the goal walk keeps its own "next goal" pointer in code.
   - Finish the walk through `d2` in this session either way.
2. **The VM's Python upgrade** is its own walkthrough, in § Python upgrade below (Mike, 11-25:
   include it).
3. **Three features are back** after two weeks dead. Check each:
   - the next travel event gets its pre-departure TfL or flight check;
   - the scheduled calendar audit ran (scheduler log);
   - the calendar-reconcile line is gone from the server log.
3a. **Watch for "I did what I could on that, but couldn't finish the reply".** That was seq 015 on
   11-25: a Vertex capacity error after the one retry allowed. If it happens again, the fix is a
   second, slower retry when nothing has been shown or run yet (`core/orchestrator.py`,
   `_run_gemini_native_stream`).
4. **Due from `SESSION.md`, unrelated to goals:**
   - WhatsApp walkthrough step 4b, the morning dry run after 03:00 on 11-26, then M4;
   - the instructions-to-code live checks (both health specialists dispatched in a brief; a Pattern
     Miner report by 11-30);
   - the ranking shadow comparisons by ~12-07;
   - Iva's onboarding walkthrough.

## Python upgrade on the VM — a guided walkthrough (Mike, 11-25: include it)

**Why.** The VM runs Debian's Python 3.11.2 and the Mac runs 3.14. Code that 3.12 accepts and
3.11 refuses (three f-string lines from `968a8a0`) kept calendar reconcile, the travel check and
the calendar audit from loading for two weeks, with nothing visible. The guard test in
`tests/test_goal_walkthrough_fixes.py` catches only that f-string class. Matching the versions
removes the whole class.

**When.** After Tests 1–3, in the same sitting if there is time; otherwise its own sitting. Not
during a scheduled brief window. Mike runs every `sudo` step; Claude Code prepares and reads.

**Read first:** `docs/INFRASTRUCTURE.md` (units, venv, deploy, recovery) and
`.claude/rules/deploy.md` (the four rules). Rule 3 binds here: `daemon-reload` **before** the
restart, never after.

**Plan, to check and finalise with Mike before any step (propose, then go step by step):**
1. **Survey, read-only.**
   - Record the OS and Python: `cat /etc/os-release`, `python3 --version`, `.venv/bin/python --version`.
   - Record what the units run: `systemctl cat metatron-server metatron-scheduler@mike` (their `ExecStart` interpreter path).
   - Freeze the current dependencies to a dated file: `.venv/bin/pip freeze > ~/venv311_freeze_2026-11-26.txt`.
   - Note any package pinned to 3.11 (FAISS, numpy, the Google and Anthropic SDKs).
2. **Choose the route (recommendation: a second venv, old one kept).**
   - Install a standalone 3.12 or 3.13 alongside the system Python (e.g. `uv python install 3.12`; no OS change).
   - Build `~/multi-model-mcp/.venv312` from `requirements*.txt`.
   - Leave `.venv` untouched as the rollback.
   - *Rejected:* a Debian 13 upgrade (a whole-OS change on a live two-user box), and an in-place rebuild of `.venv` (no rollback).
   - Pick 3.12 or 3.13 by what every pinned wheel supports, checked in step 1.
3. **Prove it before switching anything.**
   - With `.venv312`, import every module.
   - Run the QA sweep's compile and `scripts/check_agent_tools.py`, and the walkthrough-fixes suite and part A's suite, all with `.venv312/bin/python`.
   - Start the server on a spare port for one `/health` read, then stop it.
   - Nothing live is touched yet.
4. **Switch, both users at once.**
   - Mike edits each unit's interpreter path (or the drop-in the infra doc names) to `.venv312`.
   - Then `sudo systemctl daemon-reload`, then restart the server and both schedulers.
   - Read: units active, `/health` ok, the next scheduled job runs, no import errors in `journalctl` over 10 minutes.
5. **Rollback, stated before step 4.** Point the units back at `.venv`, `daemon-reload`, restart. Keep `.venv` at least a week.
6. **After.**
   - `deploy.sh`'s install step must use the new venv: check it, and change it in a Mike-approved edit (`deploy.sh` is Denied tier, so Mike edits it or lifts the deny).
   - Add a version check: the Mac and VM major.minor must match, run at deploy or in the QA sweep.
   - Retire the f-string guard in the suite once the versions match. Under the standing rule, it retires with this build.
   - Update `docs/INFRASTRUCTURE.md` § local dev / venv, and `CLAUDE.md` § Coding Conventions if the stated version changes.

**Costs.** *Build:* ~45–60 min of Mike's attended time, a few dollars of Claude Code. *Run:* none
— same VM, same services. *Ancillary:* ~1 GB more disk for the second venv until `.venv` is removed
after a week. *Unseen:* a package that imports but behaves differently on the new version; this
shows only in use, which is why the rollback is kept a week. *What persists:* the old venv, owned by
this walkthrough, deleted on a stated date.

## Close

1. A log fragment in `archive/log/` recording each test's pass or fail, with what was read and when.
2. `/archive`.

## Costs

- **Build:** none. This is a live check: a few reasoning-tier talk turns (~$0.05–0.15) and VM reads.
- **Run, ancillary, persistent:** unchanged from plan § 19.
