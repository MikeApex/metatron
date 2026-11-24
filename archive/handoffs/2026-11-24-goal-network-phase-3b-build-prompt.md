Model: Opus 5.5, high effort — the re-interview is an agent file that questions the user's own goals, and its output is what licenses rolling-wave planning; Fable reviews the diff before commit.

# Goal–task network, phase 3, part B — a large goal talked through properly, satisfaction kept, and `mike`'s goals walked through

You are building **part B** of phase 3 of `archive/plans/goal_task_network_plan_2026-11-18.md`
(§ 5, phase 3). **Part A is built and committed, not deployed** — plan § 17 records what it built,
the rulings it ran on and what it left open. Read § 17 before anything else in the plan.

Each new behaviour ships behind its own flag, **off**. No flag is flipped in this session.

**§ 10 (the review) governs §§ 4–9 wherever they differ; § 17 records part A's deviations.**

## Why part B matters to part A

Mike ruled on 2026-11-24 that **an L goal is planned in waves only after the Goals Interviewer's
full pass** — *"2 questions isn't nearly enough for an L goal."* Part A built the gate:
`tools/goals.py` `vet_goal` writes `vetted.pass: "full"` only when the calling agent (read from the
call trace) is `goals_interviewer`, and `tools/project_plan.py` refuses an L goal without it. **No
code path reaches that today.** Until part B gives the Interviewer a re-interview that ends in
`update_goal vet`, rolling waves are inert for every real goal, and part A's live check cannot
start.

## Read first, in order

1. `SESSION.md`, then `ROADMAP.md` (the mandatory pre-edit context check).
2. The plan: § 2 (G2, G3, G6, G7), § 4.2 (the L row and trigger 3), § 4.6, § 5 phase 3, § 8,
   § 10 (R3, R6), § 11 (`mike`'s live goals), § 17 (part A).
3. `archive/plans/ranking_values_plan_2026-11-23.md` § 4.13 and § 11c: `ranking_signals.jsonl` is
   the ONE signals file; the monthly review reads it; satisfaction rows go there.
4. The code as it is now:
   - `config/agents/goals_interviewer.md` — the whole file; phases 4–5 are the vetting method (§ 3);
   - `tools/goals.py` `vet_goal` — the `pass` marker; it has no `weekly_minutes` parameter yet;
   - `tools/project_plan.py` `_plan_large`, `sweep_unplanned` — what an L goal needs to be planned
     (full pass, weekly time on the goal or the call);
   - `tools/goal_network.py` — the re-vet record and its signal rows (copy their shape);
   - `tools/ranking_review.py` `record_signal`, `append_signals`, `weekly_material`;
   - `core/interview.py` and how an Interviewer session is started today (first interview only —
     re-interviews were never built);
   - `config/agents/synthesizer.md` § A newly stated goal — the L row's short pass and where a hand
     off to the Interviewer would go;
   - both routing files' `goals_interviewer` block (it already holds `update_goal`).

**Other chats commit to `synthesizer.md`, `obligations.py`, `day_plan.py` and the routing files.**
Re-read each file before editing it, **`git diff` every file before staging**, and read
`git diff --cached --stat` on its own before committing.

## Before building — confirm, then put the open questions to Mike

1. **Confirm the state.** Is part A (`<part A's commit>`, plan § 17) deployed? Its three flags
   (`rolling_wave`, `projected_finish`, `revet`) are off either way. Read `SESSION.md`.
2. **Put these to Mike, each with a recommendation, before writing code:**
   - **How a re-interview starts.** Options:
     - (a) **Recommended:** Synth offers it in the turn when a goal is sized L ("this deserves a
       proper talk — shall we do that now, or at a time you pick?") and the user's yes starts an
       Interviewer session on that goal;
     - (b) a scheduled session at a time the user picks;
     - (c) only from the weekly look back.

     Trade-off: (a) is immediate but long for an ordinary turn; (b) costs a job slot (six-job cap).
   - **What the full pass must record** for rolling wave to plan it: the plan says what it
     displaces in a real week (read against the aspirational baseline), why, by when, and what
     "done" means. Recommend: `displaces`, `priority`, `weekly_minutes`, an optional `due`, and a
     one-line `done_means` that the planner receives.
   - **Trigger 3's two questions** (§ 4.2): the one-line anticipated value when a commitment is
     made, and the experienced value after. Which commitments are in a "class with history", and
     how rarely is it asked? This costs user attention — the denominator of the core metric (ROADMAP
     § A9) — so recommend rare and class-gated.

   Build what he rules.

## Build — part B

1. **The re-interview mode (G3)** — `config/agents/goals_interviewer.md` (Amber since 2026-11-24, `10000b5`; still built in the main session, never delegated). One goal, size L,
   at the depth Mike rules. It ends in `update_goal vet` (verdict active / parked with a date /
   declined), which writes `pass: full` because the calling agent is the Interviewer. Add a
   `weekly_minutes` parameter to `vet_goal` and its schema (and `done_means` if ruled) so the plan
   gets its weekly time. Mark it in `## Confidentiality`'s terms: the user never hears "full pass",
   "vetted" or "re-interview".
2. **The hand-off** — wherever Mike rules the re-interview starts. If it is Synth (option a): one
   sentence in `synthesizer.md` § A newly stated goal's L row, and the start path in code. A
   re-vet answer of "let's talk it through properly" may also start one.
3. **Trigger 3, the satisfaction mismatch** — behind its own flag. Rows to `ranking_signals.jsonl`
   (`source: "goal_network"`, kinds `satisfaction_anticipated` / `satisfaction_experienced`), ids
   and counts and the user's own one-liners only. The gap per class is computed by code; it is
   raised, rarely, when the next commitment in that class is proposed, and it feeds that class's
   vetting. Never a second signals file.
4. **The language playbook, if it was not finished in part A's chat** — Mike wants to be involved
   (2026-11-24). Method only, researched through the Research Agent with a decontextualised
   question; `applies_when:` (built in part A) attaches it to any language. It lands only after
   Mike reviews it.
5. **Tests** — extend `tests/test_goal_network_phase3.py` or add `…phase3b.py`: fixture personas
   only, every live meter stubbed. At minimum: an Interviewer vet writes `pass: full` and
   `weekly_minutes`, after which the sweep plans the goal in waves (part A's path, end to end); a
   Synth vet never writes `full`; trigger 3 writes both rows and raises the gap only for a class
   with history, at its cap; each new flag off restores part A exactly. Keep part A's suite 21/21,
   phase 1 38/38, phase 2 36/36, `test_ranking_v2.py` 58/58, `test_task_ranking.py` 21/21 green;
   the known clean-HEAD failures (round-2 F8, `task_ledger_consult`, the multi-user push check)
   stay noted, not fixed.

## The `mike` goals walkthrough (§ 4.6) — prepare it, don't run it

`mike`'s goals are VM-owned persona config (Denied here). Write the walkthrough as a prompt in
`archive/handoffs/`, model line first: prepared steps, Mike live with his Metatron. Each existing
goal is talked through (ids per § 11; `q2` converted; four goals given ids 11-18), plus Bulgarian
`q4` — the L test case — through the new re-interview, which is what makes it plannable in waves.
Include the exact VM read that shows `q4`'s `vetted.pass` became `full` and its plan was queued.

## Close

1. Spawn a Fable diff review; reconcile every finding in a new plan section, § 18.
2. Commit with a message that leads with what a user would notice. **Do not deploy.**
3. Update part A's live-check prompt
   (`archive/handoffs/2026-11-24-goal-network-phase-3a-live-check-prompt.md`) if part B changes
   how Bulgarian becomes plannable.
4. `/archive`.

## Rules that bind this chat

- **Agent-file and routing edits are made in this session, never delegated:** `goals_interviewer.md`,
  `synthesizer.md` (Amber since `10000b5`), and the routing files (still Red) if a grant changes.
- Nothing leaves this machine: no Artifact, WebFetch or WebSearch. Research goes through the
  Research Agent path, decontextualised.
- All goal data is sensitive-tier on the VM path under ROADMAP § Section 0.
- `config/personas/**` is VM-owned; deploying is Mike's.
- Don't file backlog items Mike didn't ask for. Number every list, and never write a backlog id
  bare.
- **Budget** (plan § 8, phase 3's remainder): ~$40–80 build plus ~$15–30 for the Fable review.
  **Run cost:** a re-interview is one Interviewer session per L goal, a few model turns on the
  reasoning tier (~$0.05–0.15 each), rare; trigger 3 is code plus two short questions per
  commitment in a class with history. Name each figure in § 18.
