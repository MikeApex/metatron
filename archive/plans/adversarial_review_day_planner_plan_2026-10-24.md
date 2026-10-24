*Adversarial review of `archive/plans/day_planner_plan_2026-10-24.md`*
*Model: Fable (adversarial-reviewer) · Effort: high · Date: 2026-10-24*

## STRUCTURAL

1. [§ 10 Stage A, § 4.1, § 6.4] [tools/obligations.py:UPDATE_TASK_SCHEMA, config/modules/routing_cloud.yaml:81 synthesizer allowed_tools, tools/goals.py:_EDITABLE]
Wrong: Stage A ships new `update_task` actions/params and `update_goal.essential` on schemas already granted to synthesizer, finance and logistics while the conduct module (A10) is inactive, so "Deployed, Stage A changes nothing Synth sees or does" is false on the plan's own terms.
Fails: the schema description enumerates actions inside Synth's prompt, so during the watch days Synth can write `stakes`, `priority`, `goal_id` and goal `essential` into the live ledger and `goals.yaml` with no guidance on when, and those fields are exactly what `is_essential`, checks and missed-vs-unconfirmed later key on.
Costs: model-authored priority/stakes/essential data accumulates in Mike's live stores before any conduct exists and silently sets the Stage B behaviour the flags are meant to introduce deliberately — high.

2. [§ 7.2 step 4, § 6.1, § 6.6] [core/orchestrator.py:_close_turn_bookkeeping, tools/context_tracker.py:close_scheduled_run, core/orchestrator.py:_scheduled_focus_block]
Wrong: binding `kind="day_plan_nudge"` on every nudge wake makes `_close_turn_bookkeeping` call `close_scheduled_run`, which overwrites the single `scheduled_runs.last` slot shared by all scheduled kinds.
Fails: the next `morning_brief` or `evening_close` computes `nothing_new` against the nudge's stamp, and in any quiet gap receives `_QUIET_CHECKIN_DIRECTIVE` ("Do not re-open the day, do not re-list what is already open") in the same prompt as the plan block's "say what to do now and next".
Costs: the morning proposal Q2 depends on and the evening one-line ask of § 6.6 are demoted to a light check-in on exactly the days nudges fired, with no test in § 11 that would show it — high.

3. [§ 5.6, § 4.3, § 2 row 1] [tools/day_plan.py (new); tools/obligations.py:_with_store is the sole task store]
Wrong: the gate is specified as comparing a stored hash with a fresh hash, but its none/repair/reshuffle table requires knowing which input changed and how (a task done vs. a task opened vs. a priority change), which a hash cannot yield.
Fails: either `plan_YYYY-MM-DD.json` must store the prior candidates' status, done-count, priority and stakes to diff against — a copy of task state Mike's "no additional copy" decision forbids — or the gate collapses to rebuild-on-any-change and every ledger write becomes a reshuffle request against the 12/day cap.
Costs: the cheap-check mechanism Mike asked for is unbuildable as written and the builder resolves it at the keyboard, most likely by quietly storing task state — medium.

## LOCAL

4. [§ 5.9, § 1.4] [tools/location.py:record_transition, tools/location.py:record_position]
Wrong: "the transitions log showing the user in that zone for ≥ half its minutes around the block" requires presence duration, but the log stores only `(zone, entered_at)` on a zone change, written only when the app pings on a message or tap — the plan's own § 1.4 says only arrival is stored.
Fails: one ping from the gym at 18:05 followed by the next ping from home at 21:00 reads as three hours at the gym regardless of when the user left, so the rule is satisfied by any visit of any length.
Costs: checks are suppressed and "Mark done?" proposals filed on evidence that does not exist, the inverse of Q8's "no assumptions" — high.

5. [§ 5.9] [tools/obligations.py:add_proposal, tools/obligations.py:resolve_proposal, core/server.py:_proposals_for_display]
Wrong: the "existing proposal path, generalised to a `source` of `location`" refuses habits (`kind not in _ONE_OFF` returns without writing), dedupes and hashes on `envelope_id`, closes with the hard-coded `_CORRESPONDENCE_EVIDENCE`, and the app resolves display fields through `tools.intake.read_records`.
Fails: the canonical zone task — the gym, a weekly habit — cannot receive a location proposal through this path at all, and a one-off that can would show a blank sender/subject card and be closed as correspondence evidence.
Costs: the location-evidence feature is inert for the task kind it was designed around until the ledger's proposal model is reworked, which A2 does not scope — high.

6. [§ 7.1, § 7.3] [core/scheduler.py:_near_fixed_job_blocks, core/scheduler.py:_DEFAULT_JOBS]
Wrong: `day_plan_nudge` is a function job, and `_near_fixed_job_blocks` returns None whenever `"agent"` is absent from the job config, so the 30-minute shield around fixed sessions never applies to nudge wakes.
Fails: a nudge can wake Synth at 07:23 ahead of the 07:30 brief; the plan's only guard is "last message < 10 min ago", which the user's silence does not trigger.
Costs: the [DB-0822-07] back-to-back-conversation incident returns on nudge days, and each such wake also stamps the slot in finding 2 — medium.

7. [§ 5.3, § 5.5 V5, § 4.1 day boundary, § 5.10] [tools/obligations.py:_today, core/scheduler.py:time_in_quiet_hours]
Wrong: the waking window `[max(now, wake), bed]` "on the ledger day" and V5 "inside the waking window and not in the past" are stated for a same-date window, while the day-boundary and rhythm features exist precisely for users whose bed and `day_starts` fall after midnight (the fallback quiet hours already span midnight).
Fails: a bed of 01:30 placed on the ledger date precedes wake, so the window is empty or V5 rejects every post-midnight block.
Costs: the Q13 case the day boundary was built for yields no plan after midnight, discovered in live use rather than by the 01:30 test, which pins only the ledger key — medium.

8. [§ 11.2, § 10 Stage A flags, § 5.1 snapshot age] [core/orchestrator.py:_run_pipeline_session_stream_inner, core/scheduler.py:_register_schedules]
Wrong: "Reply latency unchanged; no new call on a turn that wrote no calendar" is a Stage A acceptance criterion, but `synth_reads_plan` is off in Stage A so nothing from the planner is on the reply path, and Stage B step 5 flips it with no latency criterion at all.
Fails: the criterion cannot fail when measured, and the no-network-call claim itself holds only while the sequential scheduler loop keeps the snapshot under 10 minutes old — a tick carrying a model reshuffle plus a multi-calendar CalDAV read can lag past that.
Costs: the first time the tick lags, a full CalDAV REPORT runs inside the user's reply and Mike finds it, not a test — medium.

## VERIFY — 2026-10-24 (round 1 revision)

1. CLOSED — [core/orchestrator.py:register_tools called at :5354 and :6841 per agent call; :3598-3599 `tool_key` hashes names only] schemas are rebuilt on every call, so a live `ledger_fields` flag can keep the new actions out of what Synth sees, and the byte-identity test is falsifiable.
2. CLOSED — [core/orchestrator.py:_close_turn_bookkeeping `if kind:` → close_scheduled_run; tools/obligations.py:1474-1475 `hide_raised` keys on `user_turn`] `kind=None` skips both the stamp and `_scheduled_focus_block`, and the ledger hold-back still applies on a proactive turn, so nothing the nudge needs is lost.
3. CLOSED — [tools/obligations.py:_load is the only source read at classification time] per-ref digests plus a derived score cannot be rendered as task state, and the repair/reshuffle split is decided against the live ledger.
4. CLOSED — [tools/location.py:record_transition stores `entered_at` on change only; dedupe at :227-228] the rule now claims only an arrival inside the window, and the dedupe makes it under-fire (arrival before the window is not re-recorded), which is the safe direction.
5. CLOSED — [tools/obligations.py:add_proposal:1768 kind check, :1771-1773 envelope key; core/server.py:_proposals_for_display; static/index.html:renderProposal:3826-3828] all four blockers are named and reworked in A2b; the slip clause opens a new sequencing gap (NEW 2).
6. CLOSED — [core/scheduler.py:_near_fixed_job_blocks:308-309] the extraction and the `carried` path are specified with a Stage B test; `near_fixed_session` lands in the same Red session as the jobs that need it.
7. CLOSED — [core/scheduler.py:time_in_quiet_hours handles `start > end`; the 22:00/07:00 fallback matches the `bed ≤ wake` roll rule] windows are datetimes anchored on the ledger day and V5 is rewritten against them.
8. PARTIAL (new shape) — [core/scheduler.py:1071 `schedule.run_pending()`; tools/caldav.py:_query_events is the only fetch] the reply-path and criterion halves close, but the fix removed every Stage A snapshot producer (NEW 1).

### NEW — STRUCTURAL

1. [§ 5.1 snapshot age, § 7.1, § 9, § 11.2] [core/scheduler.py:_DEFAULT_JOBS (Red, registered Stage B), tools/caldav.py:_query_events]
Wrong: the revision moved all calendar fetching to the Stage B refresh tick and the post-write 3 s re-fetch, while `/plan/today` "renders the stored plan after a gate check — no rebuild per poll", so in Stage A no component ever fetches the snapshot.
Fails: `_DEFAULT_JOBS` is Red and ships in Stage B, so the Stage A plan is built over an empty snapshot and § 11.2's "meetings in place, travel before located ones" cannot be observed.
Costs: the few-days Stage A watch either shows a calendar-less plan or the builder adds a fetch on the poll path ad hoc, redrawing the "reply path never fetches" boundary without a stated rule or test — high.

### NEW — LOCAL

2. [§ 5.9 "A2b may slip to Stage B … until it lands, location evidence only suppresses the check", § 10 step 5] [tools/obligations.py:_finalize_periods:1993 records `missed` for an essential habit with `done < target`]
Wrong: check suppression on location evidence ships with the engine, but the compensating proposal (A2b) may land after `nudges` flips, and nothing orders the two.
Fails: an essential located task the user did do gets neither a check nor a "Mark done?" card, and the period end records it `missed` unless the user volunteers it.
Costs: silent wrong `missed` records on exactly the tasks the location feature was meant to credit — the Q8 "no assumptions" failure — medium.

3. [§ 7.1 "Reshuffles run off the scheduler loop", § 4.3 lock] [core/orchestrator.py:_openai_compat_loop (:4756 per-call timeout, 8 iterations); tools/day_plan.py (new) `fcntl.flock` on `day_plan/.lock`]
Wrong: the reshuffle worker is "one at a time, guarded by the plan lock", which reads as the flock held across a 20–60 s model call — and an abandoned hung thread still holds it for up to 180 s.
Fails: `fcntl.flock` blocks, so the server's synchronous turn-time repair waits on the worker's lock inside the user's reply.
Costs: the reply-path stall R1-8 was raised to prevent, arriving precisely when a reshuffle is in flight — medium.

## VERIFY — 2026-10-24 (round 2 revision)

8. CLOSED — [core/server.py:tasks_today → `asyncio.to_thread(_task_call, …)`; core/orchestrator.py:4144 `_DEFAULT_CALL_TIMEOUT_S = 300`] the Stage A producer now exists on the poll path, the reply path never waits on a REPORT, and the lock is never held across the 300 s-bounded model call, so the new shape from Verify 1 is resolved.

V1-N1. CLOSED — [core/server.py:tasks_today / _task_call; tools/caldav.py:_query_events (requests + ThreadPoolExecutor, safe on a worker thread)] rule 1 gives Stage A a producer driven by the 30-second poll and makes the same rule govern Stage B; per-process single-flight can double-fetch across server and scheduler, but a duplicate REPORT is free and both writes are atomic.

V1-N2. CLOSED — [tools/obligations.py:add_proposal returns `added["ok"]` False whenever it writes nothing, :1764-1780] "suppress only when the proposal was filed" is enforceable by that return value, so an essential located task always gets a check or a card.

V1-N3. CLOSED — [core/orchestrator.py:4144 `_DEFAULT_CALL_TIMEOUT_S = 300`; :4756 `_openai_compat_loop` client timeout] the lock covers file I/O only, single-flight is the `reshuffle_inflight {gen}` marker, a superseded worker discards, and the reply path's `LOCK_NB` within 200 ms bounds the turn-time cost.

### NEW — STRUCTURAL
none

### NEW — LOCAL

1. [§ 5.1 rule 1 "one worker thread … never awaited"] [core/server.py:_task_call binds `persona_scope` on the request's worker thread only; core/persona.py:resolve_persona fails closed]
Wrong: the rule-1 background refresh is a new thread spawned from inside the poll handler's bound thread, and the plan states `persona_scope` binding for the reshuffle worker (§ 7.1) but not for this one, while identity is thread-local and does not propagate to a spawned thread.
Fails: an unbound worker raises `PersonaError` on its first `persona_data_dir()` call, the daemon thread dies with a log line, and the snapshot is never written — the "reading your calendar…" plan stays calendar-less on every poll.
Costs: in Stage A the sole snapshot producer fails silently and the few-days watch runs over an empty calendar until someone reads the server log; rule 3's "starts exactly one refresh and returns" test passes regardless, so only a test asserting the snapshot lands afterwards would catch it — medium.

## VERIFY — 2026-10-24 (round 3 revision)

V2-N1. CLOSED — [core/persona.py:_state = threading.local() (:64); core/persona.py:resolve_persona (:143) reads the spawning thread's binding; core/persona.py:persona_scope (:191) binds "on this thread" and restores on raise; core/persona.py:persona_data_dir (:248) fails closed] resolving the name on the spawning thread and binding inside the worker as its first act is exactly what the thread-local design requires, the single `_spawn_bound` helper covers both the refresh and reshuffle workers, and rule 3's test now asserts the snapshot lands on disk rather than that a refresh started, so an unbound worker would fail the test rather than die silently.

### NEW — STRUCTURAL
none

### NEW — LOCAL
none
