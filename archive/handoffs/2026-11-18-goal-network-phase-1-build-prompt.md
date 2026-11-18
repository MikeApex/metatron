Model: Opus 5.5 builds; Fable 5.1 reviews the diff before commit (docs/WORKFLOW.md, Mike 2026-09-24). Red edits are made in this session, never delegated.

# Goal–task network, phase 1: steps that wait on other steps, and the Red Book scheduled — build it

Run `/metatron-code` first.

## What Mike wants from this phase

Every task the user must do lives in one network, where a step can wait on others. The user only
ever sees the step that can be done now. Phase 1 builds that network, and its first real case is
the Red Book: when Logistics files "gather the Red Book and paperwork before Benny's 09:30
session", the prep shows up as a task at a sensible time. Synth nudges it, checks once whether it
happened, and it follows the event if the event moves.

**What the user sees when phase 1 is done:**
1. A prep for a calendar event appears on its own, nudged and checked, and moves when the event
   moves.
2. A two-step task shows step 2 only once step 1 is done. Skipping a required step 1 closes step 2
   and asks once whether to redo it.
3. A nudge due near a scheduled session is no longer dropped.
4. If Mike approves § 12 at the start: Monday's brief gives the week's shape and the one to three
   things to act on, not a day-by-day list. New horizon items count against the two-item
   Important cap. A task carried three days running is asked about once, not proposed again.

## Read first, in this order

1. `archive/plans/goal_task_network_plan_2026-11-18.md` — the whole plan. **§ 10 governs where it
   differs from §§ 4–8.** § 10's closing paragraph lists exactly what phase 1 carries. § 11 covers
   `mike`'s goals (already updated on the VM — do not redo it). § 12 covers stage 1's three misses.
2. `archive/plans/synth_now_next_plan_2026-10-30.md` §§ 9–11 — the Red Book's history and Fable's
   A1–A9, which § 4.7 and § 10 R2 answer.
3. `archive/plans/codebase_review_fixes_plan_2026-11-11.md` line 64 — the recorded design for
   finding #5 (nudges dropped near a fixed session), adopted by § 10 R10.

## Before building: three questions for Mike, one message

1. **§ 12 M1–M3 — ride phase 1, yes or no** (each separately)? Recommended: all three. Each
   touches a file phase 1 already opens.
2. **`q2` "Metatron Mark 2 Transition"** in his goals is obsolete. Complete it, remove it, or
   rewrite it as the Mark 1 work it now stands for? (He makes this change himself, or tells you
   and you do it on the VM the way § 11 was done: back up first.)
3. Confirm the **Red edits** listed below before you start them.

## Scope — phase 1 only (§ 10 closing paragraph)

1. **R1 — file locks first.** `tools/obligations.py` `_with_store` and the horizon ledger's
   save take an `fcntl` lock plus atomic rename (pattern: `tools/day_plan.py:160-186`,
   `core/accounts.py`). Every sweep then lives in the scheduler's `refresh_tick`.
2. **The network fields:** `needs`, `part_of`, `required` (default true), and a `blocked` state
   computed from a per-load id set and passed to `_view` at its ~15 call sites (R7a). Blocked
   hides from Today, `_candidates`, `context_block`, and `list_tasks` by default. User-facing
   dedupe and the soft cap skip `part_of` rows (R7b).
3. **`open_plan(steps)`** — writes a whole plan in one locked write, ids minted first,
   all-or-nothing (R7c). Phase 1 uses it only for the test project and prep tasks. There is no
   project planner in phase 1.
4. **The Red Book conversion (R2):** in the scheduler tick, behind a flag `prep_tasks` in
   `config/modules/day_plan.yaml`.
   - Match each finding to the planner's calendar snapshot by date plus venue/title tokens, and
     store the event's `calendar_uid`.
   - `due` is stored and re-derived each tick: moved event → due moves; deleted event → `moot`;
     unreadable calendar or event outside the snapshot → unchanged. A mail-only finding becomes a
     plain dated prep.
   - Dedupe on `item_key` + normalised precursor, and stamp every sibling.
   - Placement follows A1 and A6 from § 4.7; a refused open is stamped (A8).
   - Turning the flag off closes open prep tasks with a reason, and `prep_items` says them again
     (A3).
5. **R5:** `_classify` does not count a `part_of` or prep task as "added", so code places it and
   no reshuffle runs. Prep tasks are essential (nudge plus check). Project steps are `missable`
   unless they are on the critical path near the deadline.
6. **R9 — the phase 1 dismissal rule:** a dismissed required step closes its dependents `moot`
   and raises the end state once as Important.
7. **R10 — finding #5,** exactly as recorded: carried entries passed as DUE NOW and stamped, plus
   `shield_jobs:` in `day_plan.yaml`. **No change to `core/scheduler.py`.**
8. **§ 12 M1–M3, if Mike approved them.**

**Not in phase 1:** vetting, the project planner agent, `proposed` goals, the goal filter,
playbooks, finish-date alerts (phases 2 and 3).

## Red edits this phase may prompt for

`config/modules/synthesizer_day_plan.md` and `config/modules/synthesizer_scheduled_sessions.md`
are Amber. `config/agents/synthesizer.md` is touched only if the blocked/step conduct cannot live
in the module; Red, and Mike approves at the prompt. **No routing changes in phase 1.**
`core/scheduler.py` is Red: R10 avoids it, and if anything else seems to need it, stop and ask.

## Tests

- **Unit:** every § 6 item that belongs to phase 1, plus:
  - A1–A9 each as its own case
  - a cross-process write race (two processes, one close each, both kept)
  - blocked steps hidden from every reader listed in § 10 R7
  - `open_plan` all-or-nothing
  - the R10 test from the 11-11 plan (a prep nudge inside the evening-close shield reaches the
    20:00 close under DUE NOW)
  - flag off restores stage 1
- **Fixture-persona runner** (§ 6): the seven fixture personas, each seeded with a Red Book-like
  prep and a two-step task. Model calls stubbed.
- **Existing suites green:** `tests/test_day_plan_*`, `tests/test_task_ledger*`,
  `tests/test_horizon_ledger.py`, `tests/test_obligation_due_sort.py`,
  `tests/test_synth_module_injection.py`, `scripts/check_agent_tools.py`, then
  `./scripts/qa_sweep.sh`.

## Then

1. **Fable 5.1 diff review** (`adversarial-reviewer`, `model: fable`) of the full diff against the
   plan. Verify and reconcile every finding before committing.
2. Commit. `git diff` each file before staging. Other sessions' uncommitted work sits in this tree
   (`android/`, `.claude/agents/build-inquiry.md`, `.gitignore`,
   `archive/plans/inquiry_rewrite_2026-09-26.md`, `archive/handoffs/2026-09-24-build-phase-*.patch`).
   Don't stage it.
3. **Deploying is Mike's** (`./deploy.sh` is Denied). Give him the live check:
   - the next real event with a precursor gets a scheduled prep that is nudged, checked, and moves
     if the event is moved
   - a two-step test task, including a Skip on step 1
   - if M1–M3 shipped: the next Monday brief, a morning with new horizon findings, and a task left
     undone three days
4. `/archive`.

## Constraints that bind this work

- A test that exercises a real seam stubs every live meter (CalDAV, Routes, model calls).
- A live gate run dirties the tracked `data/personas/danny_park/…` fixtures; restore them with
  `git checkout HEAD --` them.
- Don't file backlog items Mike didn't ask for.
- Persona config on the VM (`config/personas/mike/**`) is VM-owned. Change it only at Mike's
  explicit instruction, with a backup first.
- Check the 4,096-token Vertex cache floor if any change shrinks the Synthesizer's cached prompt
  (CLAUDE.md § Infrastructure traps 6). The day-plan block is per-turn dynamic context, so it
  should not.
