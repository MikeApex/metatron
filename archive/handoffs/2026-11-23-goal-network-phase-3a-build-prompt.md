Model: Opus 5.5, high effort — large goals touch the planner, the ledger and the weekly review at once, and a re-vet is a model questioning the user's own goal; Fable reviews the diff before commit.

# Goal–task network, phase 3, part A — large goals: planned in waves, finish dates watched, goals re-checked when they stall

You are building **part A** of phase 3 of `archive/plans/goal_task_network_plan_2026-11-18.md`
(§ 5, phase 3).

The plan budgets phase 3 at 2–3 Opus sessions plus one with Mike (§ 8, ~$80–150). This session
builds the parts that are **code and one agent file**. **Part B** — the Goals Interviewer's
re-interview mode (G3), the satisfaction mismatch (re-vet trigger 3) and the `mike` goals
walkthrough — gets its own prompt, which you write at the close.

Each new behaviour ships behind its own flag, **off**. No flag is flipped in this session.

**§ 10 (the review) governs §§ 4–9 wherever they differ.** §§ 13–16 record what phases 1–2 and
ranking Part A built, deviated on and left open.

## Read first, in order

1. `SESSION.md`, then `ROADMAP.md` (the mandatory pre-edit context check).
2. The plan:
   - § 2: G2–G7;
   - § 4.2: the L row and re-vetting triggers 1–2;
   - §§ 4.3 (rolling wave), 4.4 (playbooks), 4.5 (projected finish), 4.6 (goals data);
   - § 5 phase 3;
   - § 8;
   - § 10: R3, R4, R5, R8;
   - § 11 (`mike`'s live goals — Bulgarian `q4` is the L test case);
   - § 15 (phase 2: F3, F4, F6, F7);
   - § 16 (ranking Part A).
3. `archive/plans/ranking_values_plan_2026-11-23.md` § 4.13 and § 11c. Phase 3 of the ranking
   built `data/personas/{p}/ranking_signals.jsonl`. **This plan's satisfaction rows go there, and
   the ranking's monthly review reads them; never a second file** (that is part B, but design part
   A's re-vet rows to the same shape). Also read § 11c's back burner: **a goal step is never
   parked** (`part_of`). A re-vet must not fight the back burner over the same task.
4. The code as it is now:
   - `tools/project_plan.py`: the queue, the worker, `open_plan`, the validator, `notices`/`note_said`;
   - `config/agents/project_planner.md`;
   - `config/playbooks/taxes_uk_self_assessment.md` (the only playbook — the shape to copy);
   - `tools/goals.py`: `HORIZONS` already holds `long`; check what reads it;
   - `tools/obligations.py`: `_goal_index`, `open_plan`, the skip / "not yet" history;
   - `tools/accountability.py` (the Accountability Index — evidence for trigger 1);
   - `tools/day_plan.py` `refresh_tick` (where every sweep lives, § 10 R1);
   - `tools/ranking_review.py` `weekly_material` (the weekly look back — where a re-vet question
     could ride; see build item 3);
   - `config/agents/synthesizer.md` § A newly stated goal;
   - both routing files' `synthesizer` and `project_planner` blocks.

**Other chats commit to `synthesizer.md`, `obligations.py`, `day_plan.py` and the routing files.**
Re-read each file before editing it, **`git diff` every file before staging**, and read
`git diff --cached --stat` on its own before committing.

## Before building — confirm, then put one question to Mike

1. **Confirm the state, don't assume it.**
   - Ranking phase 3 (`e2578d6`, `bbd3897`) is deployed or not; read `SESSION.md`.
   - `q4` Bulgarian exists on the VM with `timeline: long-term`, and `d1` names it as parent
     (§ 11). It is VM-owned persona config, so read it, never write it. A Claude Code session
     reads the VM's `data/` over `/monitor/file`; `config/personas/**` it cannot, so ask Mike to
     paste `q4`'s entry if you need it.
2. **Put one design question to Mike, with a recommendation, before writing code.** What does a
   *re-vet* do when it fires? The plan says "phrased as a question, never a verdict", but not
   where the question lands or how often. Options to lay out:
   - **(a) Recommended:** one line in the weekly look back (`weekly_material`), at most one goal
     a week, using the ranking's weekly question cap. It costs no new interruption, and the user
     already sits down to decide keep / move / drop there.
   - **(b)** A question in the next ordinary turn, once.
   - **(c)** A card in the app.

   Name the trade-off: (a) is slower but never nags (B31); (b) is sooner but is an unasked
   question. Build what he rules.

## Build — part A

1. **Rolling wave for L goals** (§ 4.3), behind flag `rolling_wave`:
   - The planner is asked for the **next milestone in steps** and later milestones as **one
     coarse node each**: a `part_of` row marked `milestone: true`, never placed, never shown.
   - When the last step of a milestone closes, code queues the **expansion** of the next coarse
     node. It goes through the same queue, worker and daily cap (§ 10 R8). Opening a step still
     triggers no reshuffle (R5).
   - Red: `project_planner.md`, for the milestone output shape. Extend the validator: a coarse
     node has no `minutes` cap but needs a window.
   - **Ledger size:** only the next milestone's steps exist as rows (§ 8 Ancillary).
2. **Projected finish** (§ 4.5), behind `projected_finish`:
   - The remaining critical path, from step minutes and the goal's weekly time.
   - When it crosses the goal's date, or moves by more than a size-scaled margin (config, in
     `config/modules/day_plan.yaml` or a new `goal_network` block — pick one home and say why),
     it is **said once** as Important, with the new date and one concrete fix.
   - Durations correct from actual close times; record what you used.
   - One alert per crossing, never one per tick (§ 6).
3. **Re-vet triggers 1 and 2** (§ 4.2), behind `revet`. **Detection is code; only the
   conversation is a model.**
   - **Trigger 1 (non-compliance):** a goal's steps skipped or "not yet" N times in a window, read
     from the ledger history and the Accountability Index. N and the window are config, cited.
     The 11-12 → 11-18 basement-plants evidence (§ 4.2) is the worked example. Make it a test.
   - **Trigger 2 (time):** checkpoints scaled to size; L at about 2 weeks, 6 weeks, then each
     quarter.
   - Each fires **once per checkpoint**. Where it lands is Mike's ruling above.
   - A re-vet's outcome uses `update_goal`'s existing verdicts (`active` / `parked` with a re-ask
     date / `declined`, kept per archive-on-merge). Nothing new is needed unless the ruling asks
     for it.
   - Write one signal row per re-vet asked and per answer, to `ranking_signals.jsonl`
     (`source: "goal_network"`, kinds `revet_asked` / `revet_answer`), so the monthly review sees
     them.
4. **The language playbook** (§ 4.4), `config/playbooks/language_learning.md`:
   - **Method only; no user content, ever.** Researched through the Research Agent with a
     decontextualised question ("best practice for an adult learning a language to conversational
     level"). That is a few cents and not metered; name the figure.
   - **It lands only after Mike reviews it.** Put it to him in this session, or leave it
     uncommitted with a note.
   - Attaching it: `applies_to` phrases matched as whole words (phase 2's F10). "Bulgarian" must
     not need its own playbook.
5. **Tests** — a new `tests/test_goal_network_phase3.py`, fixture personas only, **every live
   meter stubbed** (the planner, push, CalDAV):
   - rolling wave: only the next milestone's steps exist; closing the last step queues one
     expansion, under the cap;
   - projected finish: crossing the date alerts once, and a second tick does not re-alert;
   - trigger 1 on the basement-plants pattern; trigger 2 at its checkpoints, once each;
   - a goal step is never back-burner parked;
   - each new flag off restores phase 2 exactly.

   Keep `tests/test_goal_network_phase1.py` 38/38, `…phase2.py` 36/36, `tests/test_ranking_v2.py`
   58/58 and `tests/test_task_ranking.py` 21/21 green. Note the known clean-HEAD failures (round-2
   F8, `task_ledger_consult`, the multi-user push check) rather than fixing them.

**Not in part A:** the Goals Interviewer re-interview (G3), the satisfaction mismatch (trigger 3),
and the `mike` goals walkthrough (§ 4.6). They are part B.

## Close

1. Spawn a Fable diff review and reconcile every finding in a new plan section, § 17.
2. Commit with a message that leads with what a user would notice. **Do not deploy.**
3. Write **part B's prompt**, `archive/handoffs/<date>-goal-network-phase-3b-build-prompt.md`,
   model line first: the re-interview mode (Red: `goals_interviewer.md`), the satisfaction
   mismatch writing to `ranking_signals.jsonl`, and the walkthrough's preparation.
4. Prepare part A's **live check** (§ 5): one real L goal (Bulgarian) planned in waves over two
   weeks, plus a deliberately ignored step that triggers a re-vet. Put it in `archive/handoffs/`,
   model line first.
5. `/archive`.

## Rules that bind this chat

- **Red edits are made in this session, never delegated:** `project_planner.md`, `synthesizer.md`
  and the routing files if a grant changes.
- Nothing leaves this machine: no Artifact, WebFetch or WebSearch. The playbook's research runs
  through the Research Agent path, decontextualised.
- All goal and task data is sensitive-tier on the VM path under ROADMAP § Section 0. A playbook
  holds method only.
- `config/personas/**` is VM-owned; deploying is Mike's.
- Don't file backlog items Mike didn't ask for. Number every list, and never write a backlog id
  bare.
- **Budget** (plan § 8, phase 3 part A): ~$40–80 build plus ~$15–30 for the Fable review.
  **Run cost:** rolling-wave expansions and re-plans are reasoning-tier planner calls under the
  existing daily cap of 6, a few a month for one L goal; projected finish and re-vet detection are
  code, zero tokens; a re-vet question rides a turn the user already has. Name each figure in § 17.
