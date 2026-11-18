Plan reviewed: archive/plans/capture_fidelity_plan_2026-11-18.md
Reviewer: adversarial-reviewer · model Fable · effort medium · 2026-11-18

## STRUCTURAL

1. [§ 4.1 ordinary turns, § 4.4 state 1, § 4.6 miss rate, § 5.3 row 2, § 9 decision 2] [config/modules/routing_cloud.yaml:synthesizer `allowed_tools`; core/orchestrator.py:run_pipeline_session lines 7230–7289]
Wrong: On ordinary turns the writer of every v1 fact type except specialist-held `open_task`/`write_profile` is the Synthesizer, which runs after the join, so the comparison is made before the writer has had its turn and `saved_by_agent` is structurally unreachable for Synthesizer-owned kinds.
Fails: Every candidate becomes a CAPTURE NOTE, so the live "miss rate — candidates the writer did not save unprompted" has no unprompted condition to measure against the backfill baseline, and the accept rate that decision 2 hinges on cannot separate "saved because of the note" from "would have saved anyway."
Costs: The plan's own pass criterion (live ≤ half of baseline) and the agent-rewrite decision it feeds are both computed from a quantity the design makes unobservable, so the build ships and the question it was built to answer stays open — high.

2. [§ 4.1 interviews, § 6 step 6, § 8 Unseen 2] [core/interview.py:run_turn; core/orchestrator.py:run_session `_owns_trace`; core/trace.py:finish_request_trace]
Wrong: Step 6 has the extractor thread "carry the request's trace" and post-reply code "compare against this turn's tool calls," but `run_turn` never holds a trace — `run_session` creates it on entry and `finish_request_trace` sets the thread-local to `None` before control returns.
Fails: A thread started in `run_turn` finds no trace to carry and `run_session("capture_extractor")` opens its own non-proactive trace instead, while the post-reply `_trace_tool_names()` read returns an empty set; making `run_turn` own the trace also silences `run_session`'s spend gate, which only fires when it owns the trace.
Costs: The interviewer half — the half Iva's interview is meant to exercise — compares against nothing and reports every fact as unsaved, and the fix moves trace and spend-gate ownership into `core/interview.py` rather than patching one line — high.

## LOCAL

3. [§ 5.1, § 6 step 4, § 7.2] [tools/analytics.py:rollup_day line 142; core/orchestrator.py:run_session lines 7847–7849; tools/accountability.py:_judge]
Wrong: The backfill and eval call the extractor through `run_session` with no parent trace and no `proactive=True`, so each of the ~1,000 calls writes its own `is_proactive: False` row into `data/personas/mike/traces/<today>.jsonl`.
Fails: A9's rollup counts every non-proactive trace as a user session (≈1,000 for that day, permanently in the asset rows), and the extractor's own rows now sit in the file the plan defines as "every real user turn from the traces," so a later `--backfill` or `--report` re-ingests them as user turns.
Costs: The baseline the before/after comparison rests on is contaminated by its own measurement run, and A9's cohort-day denominator carries a one-day spike nothing in the plan enumerates — high.

4. [§ 4.2 input item 3, § 4.4 "already in the stored record"] [tools/day_shape.py:digest line 434]
Wrong: `day_shape.digest()` returns a 16-character SHA-256 of the shape, not a readable account of what is saved.
Fails: The extractor is handed a hash where the plan expects content, so the "a fact the user repeats is not a miss" rule has nothing to match against for day shape, and the § 5.1 baseline over-reports misses in exactly the kind the known case is about.
Costs: The backfill precision/miss figures for day shape are wrong until someone notices the input is opaque, and § 5.3's thresholds get argued against bad numbers — high.

5. [§ 4.2 "validated by the tool's own validator … and so on", § 6 step 1] [tools/day_shape.py:_validate_entry, _validate; tools/obligations.py:open_task; tools/goals.py:update_goal; tools/persona.py:write_persona; tools/profile.py:write_profile]
Wrong: Only `day_shape` exposes a validator separable from its write; the other four v1 tools validate inline inside the writing function, and `write_profile` additionally returns a `PENDING_CONFIRMATION` dict for contact-field changes.
Fails: "Validation through each tool's own validator" for task, goal, preference and profile kinds means either refactoring four tools to split validate from write or re-implementing their rules in `tools/capture.py`, where they drift — the one-clause step hides the actual work.
Costs: Either four tool files join the change set unplanned, or the note can propose what the tool refuses, which § 4.2 says it never will — medium.

6. [§ 4.4 states 1–2, § 4.5 `accepted` vs `edited`] [core/trace.py:ToolCallRecord `args`; tools/obligations.py:open_task `what`; tools/persona.py:write_persona `content`]
Wrong: "Arguments match the proposal on days and value" is well-defined for HH:MM and day sets but is string comparison between two model phrasings for task titles, goal text, persona prose and profile `other` entries, and the plan gives no rule for it.
Fails: Whatever equality the code picks decides whether a specialist's or interviewer's write registers as `saved_by_agent`, `mismatch_shown`, `accepted` or `edited` for four of the five kinds, so the mismatch and accept figures for those kinds are artefacts of an unstated matcher.
Costs: The § 5.3 accept + edit rate and the "mismatch catches" column carry noise the report cannot distinguish from signal for every kind except day shape — medium.

## VERIFY — 2026-11-18 (against the revised plan and the built code)

1. CLOSED — [tools/capture.py:is_holdout, note_for_synthesizer, _resolve, summarise] A seeded 1-in-5 draw inside `window_days` suppresses the note and records `held_out_saved`/`held_out_unsaved` after the Synthesizer, so the unprompted miss rate is observed from live traffic.
2. CLOSED — [core/interview.py:run_turn; tools/capture.py:snapshot, writes_from_snapshots, after_interview_turn] `run_turn` snapshots `read_shape` and goal titles before `run_session` and diffs after it; trace and spend-gate ownership in `run_session` are untouched.
3. CLOSED — [tools/capture.py:extract; tools/analytics.py:rollup_day line 142; tools/capture.py:user_turns] Parentless extractor calls run `_spend_gate()` then own a trace with `is_proactive=True, source="capture"`; `rollup_day` `continue`s on that source before `sessions += 1`, and `user_turns` skips it.
4. CLOSED — [tools/capture.py:saved_record_text, _shape] The extractor's ALREADY RECORDED block is built from `read_shape()` entries rendered as JSON lines plus titles/keys; `digest()` is not referenced.
5. CLOSED — [tools/capture.py:_validate_candidate, _validate_shape] Only `kind == "day_shape"` passes through `day_shape._validate_entry`/`_validate`; the other four kinds are reduced to a plain sentence and no tool file is refactored.
6. CLOSED — [tools/capture.py:match, _loose_key, _days_overlap, _time_match, text_overlap] Day shape is matched on section + day-stripped `_entry_key` + day overlap with a cross-form time fallback; free text on ≥ `match_overlap` content-word overlap with no mismatch state.

### NEW

1. [plan § 4.1 holdout, § 4.5 "Shown once", § 4.6 miss rate] [tools/capture.py:note_for_synthesizer lines 852–863; after_synthesizer; take_pending]
Wrong: On a holdout turn `carried = take_pending(...)` still removes earlier-turn proposals (sign-off deferrals, late results) from `pending.json`, puts them into `SynthTurn.shown` with `note == ""`, and `_resolve` then records them as `held_out_*` with no re-pend.
Fails: One in five eligible turns during the window silently discards proposals that were never shown to any agent, and those same proposals — whose user words were on a previous turn — enter the holdout denominator as `held_out_unsaved`.
Costs: Facts the design promised to surface vanish for a fifth of the window, and the live miss rate the § 5.3 gate turns on is inflated by candidates the Synthesizer had no chance to save unprompted — high.

2. [plan § 4.4 rule 1 "days differ → mismatch", § 7.1 test 1] [tools/capture.py:_loose_key; tools/day_shape.py:_entry_key line 651]
Wrong: `_entry_key("day", e)` returns `tuple(e["days"])` — a flat tuple of day strings — so `_loose_key`'s filter (which strips only *nested* tuple/list parts) strips nothing, and two `day` entries with different day sets never share a loose key.
Fails: For the `day` section the `continue` fires before `_days_overlap`/`_shape_equal`, `found` stays `None`, and `_time_match` skips same-section list writes, so a wake/bed entry saved for the wrong days is reported as unsaved, never as a mismatch; the next-turn `keep:` line then adds a second `day` entry under a different key instead of correcting the first.
Costs: The "saved for every day; they described weekends" case that § 1 names is undetectable as a mismatch for the section most likely to produce it, and the correction path leaves two conflicting entries in `day_shape.yaml` — high.

3. [plan § 4.4 "already held … dropped silently", § 4.5 carry-over] [tools/capture.py:note_for_synthesizer line 853 (`carried`); Job.wait/late callback lines 843–850; _triage]
Wrong: Carried proposals bypass `already_held` at show time, and the `late` callback triages against `writes=[]` and a record read at callback time — which can precede the Synthesizer's write on the very turn the fact was given.
Fails: A fact the Synthesizer saved after the 0.5 s join bound elapsed is pended as unsaved and shown next turn as "not yet kept"; `open_task` has `_open_duplicate`, but `update_goal add` and `write_persona` have no equivalent, so the agent is instructed to re-save what it already saved.
Costs: Duplicate goals and preference lines on the turns where the extractor was merely slow, plus `not_acted`/`accepted` rows that misdescribe what happened — medium.

4. [plan § 5.1 "the 'before' it is compared with", § 5.3 live miss ≤ ¼ of baseline, § 4.6 "beside its benchmark … marked pass or fail"] [tools/capture.py:backfill, score, report; config/modules/capture.yaml:`minimums.miss_rate_reduction`]
Wrong: Nothing computes the backfill baseline miss rate — `backfill()` prints turn and candidate counts, `score()` reports precision/recall/matcher only, and `report()` compares against `benchmark.miss_rate_max`, which is `null` until typed in by hand.
Fails: The gate that decides whether capture worked (`miss_rate_reduction: 0.75`) has no numerator source in the tool; it is derived by hand from the per-candidate `matcher` field in the review file, and `report()` never evaluates it.
Costs: The central pass/fail of § 5.3 is a manual calculation the code neither records nor checks, so it can be mis-derived or skipped without any output saying so — medium.

## VERIFY 2 — 2026-11-18 (the four NEW findings, against the code)

1. CLOSED — [tools/capture.py:note_for_synthesizer lines 879–884; after_synthesizer lines 904–909] On a holdout turn `carried = []` and `take_pending` is not called, so earlier proposals stay in `pending.json`; after the Synthesizer, fresh candidates not matched by this turn's writes are re-pended, so a holdout records `held_out_*` once and shows the miss on the next non-holdout turn.
2. CLOSED — [tools/capture.py:_loose_key lines 644–646; tools/day_shape.py:_entry_key line 651] A key that is a flat tuple of day names returns `()`, so two `day` entries reach `_days_overlap`/`_shape_equal`; weekdays-vs-all-days yields `"different"`, weekdays-vs-weekend yields `None`, as `test_day_entry_saved_for_the_wrong_days_is_a_mismatch` asserts.
3. CLOSED — [tools/capture.py:_still_missing; note_for_synthesizer `late` lines 866–877; take_for_interview lines 928–929] Carried proposals are re-checked against this turn's pre-Synthesizer writes and the stored record at show time and logged `saved_late` when found; the late callback pends raw candidates (declined logged) rather than triaging against `writes=[]`; the interview path applies the same re-check before the coverage block is built.
4. CLOSED — [tools/capture.py:backfill lines 1118–1132; report lines 1016–1041; _live_n; _DEFAULTS["minimums"]; config line 141] `backfill()` tallies saved/different/unsaved per `agent/kind` (held-now and declined excluded, matching live triage) into `capture/baseline.json`; `report()` prints pass/FAIL against `baseline × (1 − miss_rate_reduction)` only when `_live_n ≥ 20`; the minimums are merged from `_DEFAULTS` so a `capture.yaml` lacking them cannot lower the bar.

### NEW

none
