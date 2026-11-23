Model: Opus 5.5, high effort — protected-time maths, a privacy guard enforced in code, and three Red rounds; Fable 5.1 reviews the diff before commit.

# Ranking Part B, phase 2 — the conversation at mention, protected time, and "behind"

You are building phase 2 of `archive/plans/ranking_values_plan_2026-11-23.md`. **§ 11 governs the
values, § 10 the design wherever it differs from §§ 4–8, and § 11a records what phase 1 built and
owes.** Each new behaviour ships behind its own flag and runs **in shadow for three days** before
it goes on (R2). The flags are flipped after their own comparison, never in this session.

**Precondition — check it, don't assume it.** Phase 1 is deployed, and the three-morning comparison
has been run (`archive/handoffs/2026-11-23-ranking-phase-1-shadow-comparison-walkthrough.md`). Its
result is recorded in plan § 11a. If `ranking_v2` is still off because the comparison failed, read
which values Mike wanted changed first. Phase 2 builds on v2's order, so a v2 that Mike rejected is
fixed before anything is added on top.

## Read first, in order

1. `SESSION.md`, then `ROADMAP.md` (the mandatory pre-edit context check).
2. The plan: § 2 (B10–B14, B19–B24, B29), §§ 4.5, 4.7–4.10, then **§§ 10, 11 and 11a in full**:
   R5, R6, R7, rows 10–14, and the owed items in § 11a.
3. `archive/plans/ranking_research_2026-11-23_claude-chat.md` §§ 4–7. Cite each value beside it in
   `ranking.yaml`.
4. The code as it is now: `tools/ranking.py`; `tools/day_plan.py` (`_candidates_v2`, `_hard_first`,
   `_fill`, `_may_protect`, `_is_protected`, `_asks`, `render_block`, `after_render`, `_shadow`);
   `tools/subagent.py` `run_subagent`; `tools/profile.py` `WRITABLE`; `tools/obligations.py`
   (`_COST_FIELD_PROPS`, `_PLAN_FIELD_PROPS`); `config/agents/synthesizer.md`; both routing files'
   `synthesizer` grants.

**Other chats commit to `synthesizer.md`, `day_plan.py` and `obligations.py`.** Re-read each file
before editing it, and **`git diff` every file before staging it**.

## Build — phase 2 scope

1. **`protected_v2`** (§ 4.5 as R6 and § 11 rows 10–11 amend it). The intrusion cost acts on the
   protected windows the day shape actually has, keyed by the window's first activity. The cost of
   the k-th intrusion is `base × k^1.5`, with the count decaying on a 3.5-day half-life. Bases come
   from row 10: family 30, rest 18, exercise 12. Sleep and meals stay outside the grid. A task may
   enter only when its cost of delay exceeds the intrusion cost, and never silently: it becomes an
   **`intrusion` ask** carrying a recommendation (B12, B29). Shadow: record each would-be ask in
   the plan's trace. Test it against a severe task due today asking for family time, once and twice
   in a week.
2. **`answer_ask(ask_id, answer: yes|no|other_time, when?)`** (R5) in `tools/day_plan.py`. Red:
   grant it in `routing_cloud.yaml` and `routing.yaml`, and add one `synthesizer.md` sentence.
   Answers come in chat only; an unanswered ask leaves the window protected.
3. **`behind_v2`** (§ 11 rows 12–13). "Behind" means ≥ 3 overdue items, or the top-ranked task
   skipped on 2 of the last 3 days. While behind, the day leads with 1–2 quick wins (≤ 20 minutes
   in all), the first ideally a ≤ 10-minute first step of the hard task. Raise once when a placed
   task is skipped twice or its slack goes below 0. An item is raised at most twice without new
   information, then moves to the weekly list. There are at most 3 system-initiated prompts a day
   from this plan's paths. Shadow first.
4. **Probing at mention** (§ 4.7; B19–B22). One `synthesizer.md` paragraph (Red): infer the record
   from context, and ask at most one question, only when the answer would change the rank or the
   date.
5. **`lookup_public_fact(question)` + `tools/lookup_guard.py`** (R7). The guard is code and always
   runs. It refuses only full personal identifiers; a first name or an organisation passes. It is
   capped per persona per day. Red: the grant and its conduct. **§ 8 Unseen 1: name grounding's
   per-query price beside the cap** — no meter sees it. Test 10 covers "Grace School" with a
   contact named Grace (passes) and "Grace Hopper" as a contact's full name (refused).
6. **Passions** (§ 4.8): add `profile.yaml` `passions` and the `WRITABLE` entry. A stated passion
   lifts `psychological` and `social` by one grade; an inferred one never does. The judge receives
   stated passions only.
7. **Rewards, never named** (§ 4.9, row 14): an `enjoyed` field in `_PLAN_FIELD_PROPS`, placed
   ≤ 15 minutes after an effortful item. Nothing says "reward".
8. **Owed from phase 1 (§ 11a):**
   1. Show the implied promise date to the Synthesizer and in the Tasks section, so it can be seen
      and revised.
   2. Offer undated steps of active goals as advance work.
   3. Design a buffer observation that holds under v2, then switch `buffer.learn.enabled` on.
   4. Apply the 15-minute focus block at placement.
9. **Tests** go in `tests/test_ranking_v2.py`, extending it: plan § 6 tests 6 (behind), 7
   (protected, as amended), 10 and 11, plus each owed item. Keep `tests/test_task_ranking.py`
   21/21 with every new flag off.

**Not in this phase:** the back burner, the weekly conversation, signals, `record_signal` (phase 3).

## Close

1. Spawn a Fable 5.1 diff review and reconcile every finding in a new plan section, § 11b.
2. Commit with a message that leads with what a user would notice. **Do not deploy.**
3. Propose the shadow walkthroughs for `protected_v2` and `behind_v2`, three days each, prepared
   as in phase 1.
4. Write the phase 3 build prompt, model line first.
5. `/archive`.

## Rules that bind this chat

- **Red edits are made in this session, never delegated:** `synthesizer.md` and both routing files.
- Nothing leaves this machine: no Artifact, WebFetch or WebSearch. The lookup path is the one
  sanctioned exit, and only through the code guard.
- All personal data is sensitive-tier; § 4.16 is the privacy basis.
- `config/personas/**` is VM-owned; deploying is Mike's.
- Don't file backlog items Mike didn't ask for. Number every list, and never write a backlog id bare.
