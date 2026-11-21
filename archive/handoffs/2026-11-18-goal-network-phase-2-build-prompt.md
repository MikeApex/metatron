Model: Opus 5.5 builds; Fable 5.1 reviews the diff before commit (docs/WORKFLOW.md, Mike 2026-09-24). Red edits are made in this session, never delegated — this phase has several.

# Goal–task network, phase 2: a goal or obligation stated in chat is checked, planned out of sight, and fed one step at a time — build it

Run `/metatron-code` first.

## Step 0 — phase 1's state, and what runs alongside you

Phase 1 (`98f158f`, deployed 2026-11-18) and its live-data fixes (`52a1c8b`, deployed 2026-11-21 —
plan § 14) are built and live. Three live days and a replay on a copy of `mike`'s data cleared
checks 2–4 and finding #5. **One check is still running in a separate chat, read-only:** a prep
following a moved event (a Boots passport-photo appointment, 22 Nov 14:00, fed in by email so
Logistics files the finding). **Do not wait for it.** If that chat finds a defect it hands it to
you instead of editing `tools/` in parallel — fix it in its own commit when it arrives. Still owed
live after that: Synth actually asking the R9 "redo it?" question at a brief.

**One gap found 2026-11-21, in scope here** (it is phase 2's intake): a precursor the user *states
in chat* ("I need to bring my old passport to tomorrow's appointment") becomes a plain `open_task`
with no link to the event, so it does not follow a move and is not a prep. And a prep later opened
from a finding about the same event is a second task, because `_prep_sweep`'s duplicate check
(`_open_duplicate` → `_same_commitment`) only catches near-identical wording. Design both out in
this phase: a task opened about a calendar event the snapshot holds carries `prep_for` (code links
it by date + title tokens, as `_match_event` does); and `_prep_sweep` adopts an open task already
linked to the same event uid instead of opening a twin. Test both.

## What Mike wants from this phase (plan § 1, § 5 phase 2)

Mike states a mid-sized obligation in chat ("I need to file my UK taxes by the end of December").
Synth checks it in the turn — is it feasible by the date, where does it rank against what is open,
one confirmation — and it is planned unseen into small dated steps. Mike then only ever sees the next
step, on a day with room for it.

## Read first, in this order

1. `archive/plans/goal_task_network_plan_2026-11-18.md` — the whole plan. **§ 10 governs §§ 4–8.**
   Phase 2 is § 10's closing paragraph: **R3** (Synth sizes S/M/L in the turn; a planner estimate
   one size larger sends it back for vetting first), **R6** (goals reach prompts through one filter;
   `proposed` goals only under a "being considered" heading; parked/declined never; `update_goal` from
   Synth defaults to `proposed` in code; `HORIZONS` gains `long`), **R8** (`plan_project` only
   queues; the planner runs as a scheduler-tick worker with single-flight per end state, a daily cap,
   a minimum gap and a locked write through `open_plan`), **R4** (every step `flexible` with a
   required `due` and an `eligible_from`). Plus § 4.2 S/M vetting, § 4.3, § 4.4 (ONE playbook:
   taxes), § 4.6 schema, the "verified goal with no plan" sweep (generalising `allocation_gaps`).
   § 11: open tax tasks are ADOPTED into a plan (`part_of` on existing ids) — a small addition to
   `open_plan`. § 13 is what phase 1 built and what its review changed.
2. `tools/obligations.py` `open_plan`, `_annotate_network`, `cascades_to_raise`; `tools/day_plan.py`
   `_reshuffle_worker` / `start_reshuffle` (the worker pattern R8 copies) — read the current code,
   not the plan's description of it.
3. `config/agents/day_planner.md` — the no-tools agent the project planner is modelled on.

## Before building: questions for Mike, one message

1. **Phase 2's live test (§ 11, recommended there):** Prudential (insurance review and decisions)
   as the end-to-end live test, with the tax steps opened now as ordinary tasks and adopted into a
   plan once phase 2 lands — or taxes as the test? Recommend Prudential: the tax deadline is ~6
   weeks out and should not wait on this build.
2. **The taxes playbook** is researched by the Research Agent (cloud, decontextualised — no personal
   context in the question) and **Mike reviews it before it lands** (§ 4.4). Confirm he wants to
   review it in this session or a later one.
3. Confirm the **Red edits** below before starting them.

## Red edits this phase prompts for (§ 7)

`config/agents/project_planner.md` (new; no tools, like `day_planner`); `config/agents/synthesizer.md`
(goal from chat → `proposed`; size it; vet S/M in the turn or hand off L; `plan_project`,
`read_plan`); `config/agents/coordinator.md` (`NEW_GOAL` answers reach the goal record, not only
agent notes); both routing files (the new agent on the reasoning tier — the routing file is the
authority for the model id; grants for `plan_project`, `read_plan`). **Not** `goals_interviewer.md`
(re-interview is phase 3). `core/scheduler.py` only if the planner worker cannot live in
`refresh_tick` — stop and ask. Check the 4,096-token Vertex cache floor for the Synthesizer after its
edit (CLAUDE.md § Infrastructure traps 6).

## Not in phase 2

L-goal vetting and the Interviewer re-interview, rolling wave, re-vetting triggers, projected-finish
alerts, the language playbook, the `mike` goals walkthrough (all phase 3). Runtime-authored
playbooks (need a § 0 ruling). Build.

## Tests

- **Unit:** every § 6 item for phase 2 — vetting depth by size; `proposed` goals never decomposed and
  shown only as "being considered"; validator rejects oversized steps, undated steps and dates past
  the deadline; a size-up sends the goal back for vetting and writes nothing; the planner worker's
  four controls (single-flight, cap, gap, locked write); a refused plan is all-or-nothing; adoption of
  open tasks into a plan; the sweep finds a verified goal with no plan.
- **Fixture-persona runner:** extend `tests/run_goal_network_fixtures.py` so each of the seven
  personas also gets an M item through the queued planner, model stubbed; plus one opt-in
  `METATRON_LIVE=1` pass for the planner's real output (the only live meter this phase adds).
- **Existing suites green:** `tests/test_goal_network_phase1.py`, `tests/test_day_plan_*`,
  `tests/test_task_ledger*`, `tests/test_horizon_ledger.py`, `tests/test_synth_module_injection.py`,
  `scripts/check_agent_tools.py`, then `./scripts/qa_sweep.sh`. Two suites already fail on HEAD for
  date reasons (`test_task_ledger_consult` "later dated event", `test_day_plan_round2` F8) — not
  regressions; leave them unless Mike asks.

## Then

1. **Fable 5.1 diff review** (`adversarial-reviewer`, `model: fable`) of the full diff against the
   plan; verify and reconcile every finding; record it as a § 15 table in the plan, as §§ 13–14 did.
2. Commit. `git diff` each file before staging; other sessions' uncommitted work sits in this tree
   (`android/`, `.claude/agents/build-inquiry.md`, `.gitignore`,
   `archive/plans/inquiry_rewrite_2026-09-26.md`, `archive/handoffs/2026-09-24-build-phase-*.patch`).
3. **Deploying is Mike's** (`./deploy.sh` is Denied). Give him the live check as concrete example
   tasks: state Prudential (or taxes) in chat → vetted in the turn → "it's planned" said once next
   turn → only the first step on Today → step 2 appears after step 1.
4. `/archive`.

## Constraints that bind this work

- A test that exercises a real seam stubs every live meter — **including push (`core.remote_client.send_one`)**:
  phase 1's R10 test reached the live server through it before it was stubbed.
- A live gate run dirties tracked `data/personas/danny_park/…` fixtures; `git checkout HEAD --` them.
- Don't file backlog items Mike didn't ask for.
- `config/personas/mike/**` is VM-owned; change it only at Mike's explicit instruction, backup first.
- **Budget (plan § 8):** ~2 Opus sessions, ~$60–120 build. **Run:** one reasoning-tier call per new
  M item and per re-plan, capped per persona per day (default 6, config) — name the figure beside
  the cap when you set it. **Unseen:** tasks the user never asked for (bounded: nothing unvetted is
  decomposed); a wrong playbook replicates to every user (bounded: Mike reviews each).
