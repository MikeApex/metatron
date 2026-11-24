### 2026-11-24, second (goal network phase 3 part A built — large goals planned in waves once talked through in full, finish dates watched, slipping goals asked about in the weekly look back; all switched off) — `12c8463` — **committed, NOT deployed**

**Incoming handoff:** `archive/handoffs/2026-11-23-goal-network-phase-3a-build-prompt.md` — consumed, except the language playbook (deferred, below). Previous handoff paragraph: ranking phase 3 deploy-ready (`e2578d6` + `bbd3897`), next on this line was this build.

**State confirmed before building:** ranking phase 3 IS deployed — `ranking_signals.jsonl` on the VM has rows from 11-23 23:28. `q4` could not be read (`config/personas/**` is refused over `/monitor/file`); not needed for the build. `mike`'s day-plan state shows nine tasks at 8 slip days and one tax step at 3 — the evidence trigger 1 will read.

**Mike's rulings:**
1. Re-vet lands in the weekly look back, one goal a week (option a) — *"As rec, but let's move the cap on the weekly to 5 questions."* `weekly.questions_max` 2 → 5 (it was 2 since the ranking's Fable #7; the ranking cap test now pins 2 to test the mechanism).
2. *"Wait for full pass. 2 questions isn't nearly enough for an L goal."* Recommended was planning after Synth's short pass; explained in chat first (what L is; that the choice is a lasting rule, not timing). Consequence: rolling waves are inert for every real goal until part B's re-interview writes `vetted.pass: full` — and `rolling_wave` must not be flipped before part B.
3. Language playbook left to the end, with Mike — then a new chat (this chat's context too large). No dependency missed: the matcher (`applies_when`) is built and tested on a stand-in.

**What changed for a user (once flipped):** a large goal gets its next milestone as small steps and later ones as outlines; each planned goal's likely finish is said once when it passes the date, with the new date and one fix; a goal whose steps slip on 4 of 7 days, or an L goal at 2/6 weeks then quarterly, is asked about once in the weekly review as a question.

**Design choices made in-session:** milestone outlines on the plan record (`projects.json`), not hidden ledger rows — the phase 1 review's R7 leak class (dedupe, soft cap, judge, back burner, slips) cannot reach them; *rejected:* the prompt's "part_of row marked milestone", for that reason. A milestone closed with nothing done is stalled, not expanded. Obligations never asked whether wanted. New module `tools/goal_network.py`; config in a `goal_network:` block of `day_plan.yaml`.

**Fable 5.2 diff review: 6 structural + 11 local, all reproduced or reasoned, all fixed;** the verify pass found 4 more (one introduced by a fix), fixed. The ones that mattered: projected finish would have re-alerted an untouched late plan every 4 days with an absurd minutes demand (S4), told a user two steps into an L goal that it had slipped months (S1 — milestone minutes include practice, step minutes don't), and stamped an alert said on "we can look at the garden later" (S2); a re-plan could erase an L goal's milestone map (S5a); a "keep" answer pushed the next check-in out by most of a year (S6); the L2 fix over-corrected and silenced every alert on a default pace (verify N1). Table in plan § 17.

**Believed true earlier that turned out wrong:** the slip record's `{first, days, last}` was read as a run of consecutive days — it is a count; it now keeps its recent dates. "Not yet" was assumed to leave a ledger trace — it leaves none; the tap log now carries the task id.

**Tests:** phase 3 41/41; phase 1 38/38, phase 2 36/36, ranking_v2 58/58, task_ranking 21/21, fixtures 7/7, QA 12/12. Clean-HEAD failures unchanged (round-2 F8, `task_ledger_consult`, multi-user push `KeyError`). Live planner pass on a fixture L goal (`METATRON_LIVE_WAVE=1`, ~$0.05): five outcome milestones, six steps, then a seven-step expansion — valid.

**Written:** part B's prompt (`archive/handoffs/2026-11-24-goal-network-phase-3b-build-prompt.md`; opens with three rulings for Mike), part A's two-stage live check (`…-phase-3a-live-check-prompt.md`), the playbook prompt (`…-language-playbook-prompt.md`).

**Concurrent:** another window committed `10000b5`…`3afc077` during the build (agent files Red → Amber; stage 4 prefetch/counters); no overlap with this build's files. `archive/plans/instructions_to_code_stage4_evidence_plan_2026-11-23.md` and the old build patches are another window's, left unstaged.

