Plan reviewed: archive/plans/ranking_values_plan_2026-11-23.md
Reviewer: adversarial-reviewer, model fable (default), effort medium · 2026-11-23

## STRUCTURAL

1. [§ 4.1 "stakes becomes derived … written on every cost-record write"; § 4.4 "Off = Part A exactly"; § 8 Ancillary 2 "every open task gets a cost record"] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/task_judge.py:unjudged, _write; /Users/md-homefolder/Desktop/multi-model-mcp/tools/obligations.py:_PLAN_FIELD_PROPS, stakes_of, _step_weight, open_plan]
Wrong: The cost record, its schema fields and the derived-`stakes` write all land outside the `ranking_v2` flag, so flag-off is not Part A, and the plan contradicts itself and the code on whether already-judged tasks are re-judged (`unjudged()` selects only rows with no `stakes`; `_write` never replaces a judged one; § 4.1 gives them a fallback mapping while § 8 re-judges them all).
Fails: Once the extended judge and `_PLAN_FIELD_PROPS` ship in phase 1, every cost-record write overwrites the stored `stakes` that `_score`, `is_essential`, `_may_protect` and the close gate read on the v1 path — including user-stated values and the plan-source "steps are never missable" rule (an org-borne major is 30 × 0.5 = 15, below the `major` threshold, so it derives `missable`).
Costs: The shadow comparison's v1 column is no longer Part A, and turning the flag off does not restore the live ledger's previous stakes, so the stated revert path does not exist — high.

2. [§ 4.4 flag; § 5 phase 1 "then the flag flips" vs phase 2 "§ 4.5 … raising and behind"; § 6 tests 6–7] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/day_plan.py:_may_protect, _fill]
Wrong: One flag gates a model whose protected-time rule (§ 4.5), "behind" state and raising arrive in phase 2, yet the flag goes live at the end of phase 1 and phase 1's sequence stage (§ 4.4 stage 2) consumes "behind".
Fails: Between phase 1 live and phase 2, flag-on has no defined protected-time behaviour (`_may_protect` reads `essential`, which now comes from derived stakes, and the intrusion cost does not exist) and no "behind" input; phase 2 code then ships straight into an already-on flag with no shadow.
Costs: The most user-sensitive change — what may enter family time — goes live either undefined or unshadowed on a real user's day — high.

3. [§ 4.3 slack, climb window, "At day 2 of 7 … the permit wins"; § 4.6 "instead of jumping at `next_due`"; § 4.10 "slack < 0"] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/day_plan.py:_candidates; /Users/md-homefolder/Desktop/multi-model-mcp/tools/obligations.py:_on_todays_list, _view_core]
Wrong: The plan treats every dated task and interval as scored and placeable across its climb window, but `_candidates` admits only overdue, due-today, lapsed and `flexible` in-window tasks; an "upcoming" non-flexible deadline and an interval before `next_due` ("later") are never candidates.
Fails: Slack, the start-late buffer and the climb window can only move flexible deadlines; for everything else the task first appears on its due day with `r(s) = 1`, so "needed days" never causes an earlier placement and the neglect curve still jumps at `T`.
Costs: The core of B5/B23 is inert for most tasks unless candidacy is widened, which reopens the recorded "one definition of today" ruling (Mike, 10-24/25) that the plan never mentions — high.

4. [§ 4.2 ladder; § 4.3 shapes table; § 4.4 "scaled to the existing integer range"; § 4.5 bases] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/day_plan.py:_classify (`reshuffle_delta`), _candidates sort]
Wrong: Step, accruing-before-date and cliff `CoD` are bounded by `G` (≤ 90, × 2 for cliff) while neglect `CoD` is unbounded and convex (810 at three missed weeks), and the two are compared directly with each other and with fixed intrusion bases.
Fails: By the plan's own placeholders a severe deadline due today (90) cannot even raise an ask against family time (120), while any major upkeep clock past 2 × T can, and a severe clock past ~2.4 × T clears sleep's 500; no single scale factor maps this range onto the existing ~0–120 integers without flattening the deadlines or saturating `reshuffle_delta`.
Costs: Selection, intrusion and reshuffle all read one number whose shapes are not commensurable, so tuning one path breaks another and the phase 1 shadow cannot isolate which — medium.

## LOCAL

5. [§ 3 "carries the intrusion question — no new channel"; § 4.5 "answered from the app or in chat via `answer_event`"] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/day_plan.py:answer_event, _EVENT_ANSWERS, ANSWER_EVENT_SCHEMA, _asks]
Wrong: `answer_event` records what a calendar event means (`there | needs_me | someone_else | noise`), keyed to an event in the calendar snapshot; it cannot carry a yes/no on a task entering a protected window.
Fails: The call returns an error for any other answer or for a non-event id, and `_asks` only emits holds, meal asks, conditions and essential check-backs, so the intrusion ask has no block kind, no answer tool and no app control.
Costs: B12's ask-first needs a new Synthesizer-facing tool or schema, a routing grant and a client change that the plan's Red list, phases and budget do not contain — high.

6. [§ 4.5 "Each protected window class … sleep 500, family 120, own time 60, meals 40, exercise 40"; § 6 test 7] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/day_plan.py:_fill (`_Grid(plan_start, bed_dt)`), _is_protected, _is_hard]
Wrong: Sleep and meals are not protected windows in the fill: the grid ends at bedtime, so no slot inside sleep exists, and `meal` is a hard block; protected regions carry `activities`/`allows`, not a class.
Fails: The comparison "a task enters only when `CoD > I`" has nothing to act on for two of the five classes, and the 7-day per-class intrusion count has no class key to count against.
Costs: § 4.5's guarantee that "no task enters sleep without passing the same comparison" is vacuous as built, and making it real means reworking the grid and the skeleton — medium.

7. [§ 4.7 "`tools/lookup_guard.py`, applied in `run_subagent` when the target is `research_agent` on this path"; § 4.16; § 6 test 10] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/subagent.py:run_subagent]
Wrong: `run_subagent(agent_name, message, complexity, fire_and_forget)` has no notion of "this path", so the guard and the `lookups_per_day` cap either apply to every `research_agent` dispatch or to none that can be identified.
Fails: Applied to all, it strips or refuses existing research traffic and caps it at 5 a day; applied by caller intent, the model selects whether the privacy check runs; and matching "any contact's name" by string collides with public names (a contact called Grace against "Grace School").
Costs: § 4.16's claim that the only path leaving the boundary is code-checked depends on a distinction the call site cannot make — medium.

8. [§ 5 phase 1 (§ 4.6 people offer, § 4.10 implied dates, "grades visible on request in chat"); phase 3 (§ 4.12–4.13 "each answer is recorded", "Synth on any unprompted remark"); § 7.1] [/Users/md-homefolder/Desktop/multi-model-mcp/config/modules/routing_cloud.yaml:synthesizer.allowed_tools; /Users/md-homefolder/Desktop/multi-model-mcp/config/agents/synthesizer.md]
Wrong: Phases 1 and 3 require the Synthesizer to offer clocks, set implied dates, show and correct grades, and write signal rows, but § 7.1 lists `synthesizer.md` edits for phase 2 only and no tool or grant for recording a signal or an `enjoyed` marker.
Fails: Phase 1's live check and phase 3's signals depend on conduct text and tool grants that no step creates; the Synthesizer's grant holds no tool that writes `ranking_signals.jsonl`.
Costs: Unlisted Red rounds appear mid-build in two phases, and the signals the monthly review reads may never be written — medium.

9. [§ 4.4 stage 1 "rank = `CoD` ÷ attention blocks … the day planner fills by this order"] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/day_plan.py:_candidates sort, _fill placement loop]
Wrong: Dividing by blocks when room is short ranks a two-hour severe task due today (90 ÷ 12 = 7.5) below a ten-minute minor one (10 ÷ 1 = 10).
Fails: `_fill` places in rank order until the grid is full, so short trivia consume the free time first and the long vital task goes unplaced, with § 4.5 then barring it from protected time.
Costs: The outcome Part A removed ("chores above the steps of a real tax plan") returns on exactly the days room is short — medium.
