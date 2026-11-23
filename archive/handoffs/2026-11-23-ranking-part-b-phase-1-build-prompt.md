Model: Opus 5.5, high effort — the scoring maths and the Red conduct text are judgement-heavy; Fable 5.1 reviews the diff before commit.

# Ranking Part B, phase 1 — rank by the regret of delay, in shadow

You are building phase 1 of `archive/plans/ranking_values_plan_2026-11-23.md`. **§ 11 (research
applied) governs the values and formulas; § 10 governs the design wherever it differs from
§§ 4–8.** Nothing in this phase changes what a user sees until the
`ranking_v2` flag is flipped. The flip is not in this session: it follows Mike's three-morning
comparison.

## Read first, in order

1. `SESSION.md`, then `ROADMAP.md` (the mandatory pre-edit context check).
2. The plan: § 2 (rulings B1–B32), §§ 4.1–4.4, 4.6, 4.10, 4.14–4.16, then **§§ 10 and 11 in
   full** (R1–R9, the amended Red list, Mike's two rulings inside R3 and R9, and the research
   values with Mike's two rulings on them).
3. `archive/plans/adversarial_review_ranking_values_plan_2026-11-23.md`: what the plan got wrong
   once, so the build does not reintroduce it.
4. **The research is in:** `archive/plans/ranking_research_2026-11-23_claude-chat.md`, applied in
   plan § 11 (rows 1–9 are phase 1). Set every `ranking.yaml` value from § 11 and cite the
   report's section beside each one (`# research § 2`). A value the report marks heuristic is
   labelled heuristic. Mike ruled on two of them: **neglect stays convex for kin** (k = 1.5, not
   the report's 1.0), and the back burner is 21 days (phase 3).
5. `archive/plans/goal_task_network_plan_2026-11-18.md` § 16: what Part A built and the 16 Fable
   findings it fixed. `tests/test_task_ranking.py` (18/18) is the proof that flag-off is still
   Part A.
6. The code as it is now, not as the plan quotes it: `tools/day_plan.py` (`_score`, `_ramp`,
   `_candidates`, `_fill`, `_may_protect`, `_asks`, `request_replan`); `tools/obligations.py`
   (`_PLAN_FIELD_PROPS`, `stakes_of`, `is_essential`, `_end_weight`, `_step_weight`,
   `_on_todays_list`, `_view_core`, `open_task`, the `interval` kind); `tools/task_judge.py`;
   `config/agents/task_judge.md`; `tools/crm.py` (`contact_frequency_preference`,
   `last_contact`); `config/modules/day_plan.yaml`.

**Other chats are committing to `config/agents/synthesizer.md`, `tools/obligations.py` and
`tools/day_plan.py`** (lists and dropped-step work landed 2026-11-22/23). Re-read each file before
you edit it, and **`git diff` every file before staging**. Staging by filename does not keep
another session's lines out of your commit.

## Build — phase 1 scope, exactly

1. **`config/modules/ranking.yaml`** (new): every grade, bearer weight, compounding rule, shape
   parameter (`k`, the saturation `M`, the reversibility weight, step residual, accrual rate),
   attention block, start-late buffer, `advance_floor`, `implied_promise_days`, the v2
   `reshuffle_delta` and the score scale. A per-user overlay `config/personas/{p}/ranking.yaml` is
   read and merged if present. **Write no persona file.**
2. **The cost record** (§ 4.1 as amended by R1): `costs`, `bears`, `shape`, `real_due`,
   `costs_source`, `costs_why` in `_PLAN_FIELD_PROPS`, behind a new flag `cost_record`.
   **It never writes `stakes`.** A stated record is never replaced by an inferred one.
3. **The judge's recording pass** (R1): `unrecorded()` selects open tasks with no cost record and
   writes only cost fields, under the judge's existing caps. `config/agents/task_judge.md` (Red)
   returns the record; the field descriptions stay the one home for the judging rule.
4. **`stakes_v2(t)`**, derived on read from the **unweighted** floor; a required plan step stays
   vital. Under `ranking_v2`, `is_essential` reads it; with the flag off, nothing changes.
5. **Importance and cost of delay** (§§ 4.2–4.3 with R4, values and formulas from § 11): the
   ladder; **multiplicative compounding** (§ 11 row 1); the social ×1.5 dimension weight; the
   bearer weight, in `CoD` only, with org ≈ 1.0 for an owner; the four shapes; neglect as
   `G × min(M, (r − 1)^1.5)`. Slack uses the **tiered** start-late buffer, learned by **pooled
   hierarchical shrinkage** (§ 11 row 5) into `data/personas/{p}/day_plan/ranking_state.json`.
   **Attention block:** 5 min between tasks, 15 inside a focus block, and batched small tasks share
   one (row 6).
6. **Candidacy** (R3 and Mike's ruling): (a) the musts are today's list plus must-start-today
   (slack ≤ 0 with the buffer); (b) when room remains, **advance work is suggested**: upcoming
   tasks and the current steps of active goals, by `CoD` per block, above `advance_floor`, never a
   must, never nudged; (c) time left unfilled is labelled as the user's own time. Neglect
   candidacy stays at `next_due`; the curve governs rank after it.
7. **Selection and sequence** (R9, R2): musts placed by absolute `CoD`, the rest by `CoD` per
   attention block. Hard-first only (no "behind" in this phase). Protected time stays Part A's
   `_may_protect`, reading `is_essential`.
8. **Neglect clocks:** `shape: neglect` on `interval` tasks. **The people offer** is one
   `synthesizer.md` paragraph (Red): an intimate contact with a wished frequency is offered once
   as a clock and becomes an interval task on yes, seeded from `last_contact`. History informs
   the question and never sets the cadence (B9).
9. **Implied promise dates** (R8, § 11 row 9): code in `open_task`. `bears: close|others`, no
   `due` → mention + 3 days (quick digital) or 7 days (effortful or physical), `due_source:
   implied`. The people offer suggests § 11 row 8's default cadences, and the user's answer sets
   `T`.
10. **`synthesizer.md` (Red), three sentences beside the paragraph in item 8:** show and correct a
    task's grades on request, via `update_task` (B4); offer advance work as a suggestion, never as
    a must; and override the code's order for the moment through `request_replan(reason)` when
    circumstance dictates (R9, Mike). Keep each short; the file is token-sensitive.
11. **Shadow:** with `ranking_v2` off, every build computes the v2 order beside v1 and writes it
    to the day-plan trace with each task's `G`, shape factor, slack and blocks separately (R4), plus
    whether v2 would have triggered a reshuffle. **`scripts/ranking_report.py --compare --persona
    P`** prints both top tens side by side for a day.
12. **Tests**, `tests/test_ranking_v2.py`, fixture personas, every live meter stubbed:
    1. plan § 6 tests 1–9 and 13, with test 1 as R3 rewords it;
    2. R1: no path writes `stakes` from a record, and flag-off reads are byte-identical;
    3. R9: a two-hour severe task due today beats six ten-minute minors;
    4. R3: a must-start-today task appears; a ten-minute Monday task does not appear on Sunday;
       advance work appears only when the musts leave room, and never below `advance_floor`;
    5. `tests/test_task_ranking.py` 18/18 green with the flag off.

**Not in this phase:** `protected_v2`, `behind_v2`, probing at mention, `lookup_public_fact`,
passions, rewards, the back burner, the weekly conversation, signals.

## Close

1. **Fable diff review.** Spawn a Fable 5.1 reviewer on the diff. Reconcile every finding in a new
   plan section (§ 11, "Phase 1 built"), the way § 16 of the goal network plan did.
2. **Commit** with a message that leads with what a user would notice (here: nothing yet; the new
   ranking runs beside the old for comparison). **Do not deploy** — `./deploy.sh` is Mike's. At
   deploy, `cost_record` goes on (one judge pass, ~$0.04 for `mike`), and `ranking_v2` stays off.
3. **Propose the walkthrough** (plan § 7.2 item 2): three mornings after deploy, ~5 minutes each.
   Mike runs `--compare` on the VM with steps you prepare, and says which order is right and why.
   **The flip needs Mike to prefer v2 on ≥ 2 of 3 mornings, with no obligation he calls real
   below the cut.**
4. **Write the phase 2 build prompt**, model line first.
5. `/archive`.

**Revert:** `ranking_v2` off restores Part A exactly, and `cost_record` off stops recording. Part
A's own revert (§ 16) is unchanged.

## Rules that bind this chat

- **Red edits are made in this session, never delegated:** `task_judge.md`, `synthesizer.md`, and
  the routing files only if the judge's output cap is measured short.
- Nothing leaves this machine: no Artifact, WebFetch or WebSearch. A shareable document is a
  file in `archive/plans/`.
- All personal data is sensitive-tier; the plan's § 4.16 is the privacy basis. Nothing in this
  phase leaves the VM.
- `config/personas/**` is VM-owned: never edit it. Deploying is Mike's.
- Don't file backlog items Mike didn't ask for. Number every list; never write a backlog id bare.
- A Mike-only step gets a proposed walkthrough session, not a line on a list.
