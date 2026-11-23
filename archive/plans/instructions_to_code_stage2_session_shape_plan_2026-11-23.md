Model: Opus 5.5 for the build (seven mechanisms across both pipeline twins, thread-local state, one lock); Fable 5 for the plan and diff reviews, per the driver loop.

# Stage 2 — C1, session shape: build plan (2026-11-23)

Planned against `HEAD` = `8cd3be3`; **revised against `HEAD` = `8ef2edf`** (after the ranking chat's `e134948` and `129f3fb`). Every line number is `8ef2edf`'s. `core/orchestrator.py` and `config/agents/synthesizer.md` have since picked up another chat's uncommitted lines. § 5 lists which hunks of this stage sit near theirs.
Sources: sweep § 6 (rulings) and § 2 rows #1, #2, #4, #10. Review S2, S6 and S7.1, and misses M6, M7, M10 and M11. Driver prompt § Stage 2. `[DB-0902-01]` and `[DB-0804-02]`. Fable 5.2 plan review and the stop file's rulings (Revision 1, below).

## Revision 1 (2026-11-23)

Inputs:
- `instructions_to_code_stage2_session_shape_plan_review_2026-11-23_fable-5-2.md`;
- `instructions_to_code_plan_review_stop_2026-11-23.md` §§ 1–3, with § 5 binding;
- the sibling plans for Stages 3, 4 and 5 (interfaces only).

| Finding | Resolution |
|---|---|
| **S1.** M7 could make ordinary turns ask a question and record nothing; the fill rate is measured only after the closing round | **Resolved.**<br>• M7 ships in **shadow**: code logs "would hold" and holds nothing (§ 1 M7).<br>• Its two Coordinator closing-round edits (`coordinator.md:52`, `:143`) **leave this run**.<br>• The shadow measure is recorded on the trace and read by the baseline script.<br>• Going live is a later decision, made from those figures. |
| **S2.** A held turn still writes one hop later, through the Synthesizer | **Resolved, specified for live and inactive in shadow.**<br>• While a live hold is on, code refuses the Synthesizer's `run_subagent` to a held writer and its `ACTION_TOOLS` writes for that request, through `dispatch_tool`.<br>• It also refuses an M11 `routing_miss` on a held turn.<br>• In shadow nothing is held, so nothing bounces, and the shadow records which held writers the Synthesizer re-dispatched. |
| **S4.** #10 was framed on a wrong picture: `_SYNTH_MAX_ROUNDS = 4` (`core/orchestrator.py:4507`) already ends the production Synthesizer's tool use and answers through `_final_reply_round` (`:5031`) | **Accepted. #10 is rewritten.**<br>• No new counter, and no call is ever refused.<br>• `CHAIN_LIMIT_REACHED` is recorded when the existing cap ends a Synthesizer reply.<br>• `_FINAL_REPLY_PROMPT` (`:4522`) carries B4's consequence wording.<br>• **D-S2-3 is withdrawn.**<br>• Closing edits are reduced to the two that the code now makes false (`synthesizer.md:147`, `:382`). `:131` and `:393` ("3-round limit") stay true as the model's own budget inside the four-round cap. |
| **S5.** A past disclosure could be re-raised in every brief and close | **Resolved.**<br>• The code-added scheduled Mental Wellbeing dispatch carries a **fixed tone-only directive**: the user has not spoken, give tone context from the user's own recent entries only, and raise no clinical history.<br>• An A4 fixture (`tests/run_a4_safety.py`, clinical suite) checks that a disclosure on file is not re-raised. It runs inside Stage 3's clinical gate run, so it adds no separate live run.<br>• Physical Health keeps the scan directive, because its `MEDICATION_MISSED_CRITICAL` is data-driven and valid without user words. |
| **L3.** The fourth-call refusal could refuse a Mental Wellbeing or Physical Health follow-up | **Resolved by S4's reframe.**<br>• Nothing is refused. Every call a round asks for runs, and the cap only stops a fifth round from starting.<br>• The live M7 hold never refuses `run_subagent` to Mental Wellbeing or Physical Health. |
| **L6.** The open-thread cap could archive the thread being discussed; capped entries block lookalike threads forever | **Resolved.**<br>• A thread the user engages this turn (`_user_engages_thread`) is exempt from the cap and ordered as today's.<br>• A capped archive entry blocks re-entry for `_OPEN_THREAD_EXPIRY_DAYS` (7) from `capped_on` only, then stops participating in `archived_keys`.<br>• Expiry-archived entries are unchanged (`[DB-0814-02]` logic is not touched).<br>• New tests cover the non-engaging re-send and the lookalike thread. |
| **L7.** `defer` on a held turn does not do what the sign-off path does | **Resolved: a no-op in shadow.** Nothing is held, so capture fidelity is untouched. Excluding held turns from capture scoring is a **precondition of going live**, owned by that later change, and it is listed as such in § 1 M7. |
| **L8.** M6's remap closed the tool path's clinical-thread merge and escalation | **Resolved: the path is kept.**<br>• `merge_pattern_findings` forwards `clinical_threads` through the **same** `_merge_clinical_threads` call and the same scheduled-turn refusal that `write_context_tracker` uses, factored into one helper so the two cannot drift.<br>• This keeps add-only threads and the tier-2 escalation.<br>• *Departure noted:* stop file § 2.3 says "refuses". The coordinator's later instruction says the path must not be lost, and the clinical rule ("code may add a flag, never clear one") favours keeping an add-only path over refusing it. |
| **L9.** The consent-gate claim was false | **Resolved.**<br>• `_run_single_agent` has no consent check. Base consent is enforced at registration (`core/server.py:338–345`, `base_configuration`), so a pipeline turn exists only for a consented user. The code-added dispatch is the same processing as a Coordinator-listed one and needs no new scope.<br>• A new test covers the code-added dispatch for a second persona: her own scheduler file, her persona scope, none of the first persona's data. |
| **D-S2-1** | **Ruled option 3** (§ 5).<br>• Refused on a turn with no user words: `USER_CORRECTION`, `INSTRUCTION_CHANGE_REQUEST`, `FEATURE_REQUEST`, `SELF_APPLIED`.<br>• `ROUTING_MISS` is **kept** there and tagged `"scheduled": true`.<br>• Tagged events are skipped by both of their readers: `scripts/sync_dev_backlog.py` `fetch_events` (`:437`) and `core/build/tick.py` `_count_faults` (`:171`). |
| **D-S2-2** | **Ruled as recommended:** all five record writers are guarded, and both agents run `deep` on the two sessions. |
| **D-S2-4** | **Ruled: shadow first** (S1). |

**Sibling interfaces:**
- **Stage 4** calls `merge_pattern_findings(patterns=…)` from code (`tools/pattern_report.py`), so the function takes `patterns` alone.
  - Stage 4's M4 (`held_items` → `{"text", "held_since"}`) and S4-L14 ("an omitted `held_items` key keeps them") change the held-items path of `write_context_tracker`.
  - This stage's cap touches only `open_threads`, and `merge_pattern_findings` passes `held_items` through untouched in whatever shape is on disk. Stage 2 lands first.
- **Stage 3's** `_after_specialists` wraps `_drop_unprompted_clinical_flags`. The code-added Physical Health dispatch here is one of its inputs.
- **Stage 5's** #19 block leaves `CLARIFICATION_NEEDED` out. `_clarification_needed()` here is the one parser, and Stage 5 imports it.

**Shared mechanisms this plan relies on (all verified in `HEAD` `8ef2edf`):**
- **The turn.** `tools/turn_context.current()["user_turn"]` is `has_real_user_turn()`. It is bound for the whole turn in both pipeline twins:
  - non-streaming `run_pipeline_session`: `_turn.adopt` at `core/orchestrator.py:7800`, cleared at `:8000`;
  - streaming: `_turn.turn_scope` at `:8050`.

  It is adopted into the specialist fan-out (`:7103`) and into parallel tool workers (`:3104`, `:3225`, `:4743`, `:4997`). `run_session`'s single-agent jobs (the weekly Pattern Miner and Physical Health reviews) bind no turn, but their trace carries `is_proactive`. The turn is a dict, so it can carry per-request flags such as M7's hold.
- **The agent.** `dispatch_tool` (`core/orchestrator.py:2908`) is the single chokepoint every provider loop calls. It knows the calling agent (`_agent_rec or _tr.get_current_agent()`).
- **The request.** Per-request state already lives on the `RequestTrace` instance (the precedent is `trace._quality_event_types` in `tools/logger.py:696`), and it dies with the request.

---

## 1. Per item

### M6 — the weekly Pattern Miner run no longer wipes the Synthesizer's follow-ups and held items (data loss, first)

**What a user notices:** after the weekly Pattern Miner run, the next morning still remembers:
- the follow-up it meant to ask;
- what it was deliberately holding back;
- the open threads.

Today that one tool call replaces all of them with whatever Pattern Miner sent, usually empty lists.

**Verified:** `write_context_tracker` (`tools/context_tracker.py`) rebuilds the dict from its arguments. `open_threads`, `patterns`, `follow_ups` and `held_items` are replace-semantics (`"held_items": held_items or []`); only `clinical_threads` merges. The schema *requires* `open_threads`, `patterns` and `follow_ups`, so Pattern Miner must send something for each, and empty is the natural fill. `pattern_miner` is the **only** agent granted the tool in both routing files. The Synthesizer reaches the function directly through `persist_context_block` (`core/orchestrator.py:2747`; the call to the function is at `:2763`), not through the tool.

**Mechanism:**
- New `merge_pattern_findings(patterns, open_threads=None, follow_ups=None, held_items=None, clinical_threads=None, user_text=None) -> str` in `tools/context_tracker.py`, `@_locked`. It accepts every schema field so a model's call always binds, and it is callable from code with `patterns` alone (Stage 4's report writer). It writes `patterns` and nothing else that the session owns:
  - read the raw file;
  - append each incoming pattern not already present (compared by casefolded, whitespace-normalised text), existing ones first;
  - leave `open_threads`, `follow_ups`, `held_items` (in whatever shape is on disk, so Stage 4's `held_since` dicts pass through), `last_session`, `expired_open_threads` and `_CARRIED_KEYS` exactly as on disk;
  - **`clinical_threads` keep their tool path (review L8).** When the call carries them, they go through `_clinical_merge_for_write(clinical_threads, existing)`. That is a new helper factored out of `write_context_tracker` (`HEAD` `:1440–1445`), and `write_context_tracker` itself now calls it, so the semantics cannot drift. The helper:
    - applies the scheduled-turn refusal (`_scheduled_turn()`);
    - runs `_merge_clinical_threads` (`:1228`), which is add-only, refuses tier-2 `resolved`, and raises the tier-2 escalation;
    - returns `(threads, notices)`.

    The notices are appended to the result string exactly as today. A thread omitted from the call is carried forward, as today;
  - `_write_raw`.
- An unreadable tracker writes nothing. It returns `"Tracker unreadable — nothing written"`, and the next Synthesizer write recovers the file through the existing `_preserve_corrupt` / last-good path. No new recovery path is added.
- The result string says how many patterns were added and that the other fields "are kept by the session and were not changed by this call", so the model is not told a write happened that did not.
- `register_tools()` maps the tool name `"write_context_tracker"` to `merge_pattern_findings`; that is the only handler change. The replace-semantics function keeps its name and every code caller (`persist_context_block`, about 12 tests).
- `WRITE_CONTEXT_TRACKER_SCHEMA`: the description becomes "Add findings to the tracker's `patterns`, and record or update clinical threads (merge, never delete). Open threads, follow-ups and held items are kept by the session and are not changed by this tool". `required` becomes `["patterns"]`. The other properties stay, so a call that sends them still binds.
- **Exit:** any agent that calls the tool, Pattern Miner or a warn-mode stray, can add patterns and add or advance clinical threads. It cannot replace anything.

**Files:** `tools/context_tracker.py` (Amber); `core/orchestrator.py` `register_tools`, the handler line `:1640` and the import `:1445` (Amber).

**Tests: `tests/test_pattern_miner_tracker_merge.py`.** Tmp persona dir, using the isolation pattern from `tests/test_open_thread_expiry.py`. Cases:
1. Seed open_threads (dated), follow_ups, held_items and clinical_threads. Call the *registered handler* with `open_threads=[]`, `follow_ups=[]`, `held_items=[]`, `patterns=["p-new"]` and no `clinical_threads`. The seeded open_threads, follow_ups, held_items and clinical_threads are unchanged, and `patterns` = old + `p-new`.
1b. The same call carrying a new `clinical_threads` entry, inside a non-proactive trace. The thread is added with `raised` stamped, and a tier-2 flag calls `raise_escalation` (stubbed). The seeded threads are carried forward.
1c. The same call inside a proactive trace: no thread is written, and the result carries the existing "scheduled session" notice.
1d. `write_context_tracker` and `merge_pattern_findings` produce identical `clinical_threads` for the same input (one helper).
1e. `held_items` seeded as `{"text", "held_since"}` dicts (Stage 4's shape) pass through byte-identical.
2. A duplicate pattern differing only in case or space is not added.
3. `last_session` is unchanged.
4. `asked_questions` and `scheduled_runs` survive.
5. A corrupt file is not overwritten and the result says so.
6. Schema `required == ["patterns"]`.
7. Regression: `persist_context_block` still replaces `follow_ups` (the Synthesizer's semantics are unchanged).
8. Through `dispatch_tool` with an agent record named `pattern_miner`: same result as case 1.

**Cost:** run 0; it saves nothing in tokens. Ancillary: none. **Risk:**
- Pattern Miner's findings still live only until the Synthesizer's next replace-write drops them. That is today's behaviour too, and the Synthesizer reads them on its next turn and usually re-emits. It is not changed here.
- `pattern_miner.md:109` stays accurate ("update with 2–3 key findings"), so no Red edit.

### #1 — "user corrected me" events stop being filed from turns where the user said nothing (folded into `[DB-0902-01]`, not duplicated)

**What a user notices:**
- The dev backlog and Build's ×3 repair trigger stop counting the Coordinator's comments on its own scheduled prompts as corrections and misses. That is about 56 `USER_CORRECTION` and about 155 `ROUTING_MISS` events on the review's recount, so real misses become visible.
- A routing miss on a scheduled turn is still kept, marked as scheduled, for anyone who looks.

**Ruled (D-S2-1, option 3, Mike 2026-11-23):**
- **Refused** on a turn with no user words: `USER_CORRECTION`, `INSTRUCTION_CHANGE_REQUEST`, `FEATURE_REQUEST`, `SELF_APPLIED`. Each event *claims* the user did something, and the turn proves they did not.
- **`ROUTING_MISS` is kept** on such a turn, written with `"scheduled": true`, and kept out of both readers that count it.

**Mechanism:**
- **The guard.** In `write_quality_event` (`tools/logger.py:602`), after the existing null-ish and success-claim guards and before the dedup lock:
  - if `event_type ∈ _NEEDS_USER_WORDS` (the four refused types) and `_no_user_words()`, raise `ValueError("… this turn carries no words from the user, so there is nothing to have corrected or requested — do not log it")`;
  - if `event_type == "ROUTING_MISS"` and `_no_user_words()`, add `"scheduled": True` to the event dict and write it.
- **`_no_user_words()`:**
  - a bound turn whose `user_turn` is False; **or**
  - no bound turn, *and* a trace with `is_proactive` True (the weekly single-agent jobs).

  No turn and no trace passes, as today. That covers scripts, scheduler function jobs, and `core/server.py`'s `/feedback` tap (`_feedback_blocking`, `:2341`), which writes `USER_CORRECTION` from an HTTP handler with no turn bound and is a real user action.
- **The two readers skip tagged events:**
  1. `scripts/sync_dev_backlog.py` `fetch_events` (`:395`): add `and not e.get("scheduled")` to the return filter (`:433–438`), beside the existing null-ish filter. The events stay on disk; this is a read-time filter, the same posture as `[DB-0815-09]`.
  2. `core/build/tick.py` `_count_faults` (`:135`): `continue` when `event.get("scheduled")`, before the `agents` split (`:171`). Build's three-strikes REPAIR count (`REPAIR_AT = 3`, `:47`) then never sees them.

  A grep found no other reader of `quality_events.json` that counts types. `tools/accountability.py` and `tools/baselines.py` only skip the file.
- **Callers already absorb a `ValueError`:**
  - the Coordinator's tool call: `dispatch_tool` returns it as an error string, so the model is told;
  - `_handle_user_correction` (`core/orchestrator.py:800`) catches it;
  - `_persist_dev_request` (`:2791`) catches it.
- **`_handle_user_correction`** gains `user_turn: bool = True`. Both twins pass it (`:7862`, `:8164`). It returns early when the turn has no user words, which only avoids the `_corrected_agents` trace scan and a warning per scheduled turn. **The logger is the one authority**; the early return is not a second rule.
- **Code-written types** (`CONTEXT_BLOCK_UNPARSED`, `FALSE_ACTION_CLAIM`, `TOOL_DENIED`, `MODEL_CALL_FAILED`, `CHAIN_LIMIT_REACHED`, …) are untouched.
- **`[DB-0902-01]`** closes on this build plus a week of `quality_events.json` with no *untagged* `ROUTING_MISS` from a scheduler-opened session. The driver updates that entry at `/archive`; no new item is filed.

**Files:** `tools/logger.py`, `core/orchestrator.py`, `scripts/sync_dev_backlog.py` and `core/build/tick.py`, all Amber. `core/build/` is not in the Red list.

**Tests: `tests/test_no_user_words_events.py`.** Tmp logs dir, copying `tests/test_routing_miss_success.py`'s isolation. Cases:
1. Inside `turn_scope(user_turn=False)`, each of the four refused types raises and nothing is appended to `quality_events.json`.
2. Inside `turn_scope(user_turn=False)`, `ROUTING_MISS` is written with `"scheduled": true`.
3. Inside `turn_scope(user_turn=True)`, all five are written, and `ROUTING_MISS` carries no `scheduled` key.
4. No turn and no trace: written untagged.
5. No turn, but a `start_request_trace(..., is_proactive=True)` is bound: the four are refused and `ROUTING_MISS` is tagged.
6. `CONTEXT_BLOCK_UNPARSED` and `FALSE_ACTION_CLAIM` under `user_turn=False`: written untagged.
7. A fan-out worker thread that `adopt`s a no-words turn: refused and tagged, proving the propagation.
8. `_handle_user_correction(pkg, user_turn=False)`: no event, no warning.
9. `sync_dev_backlog.fetch_events`, given a stubbed `_get_json` returning one tagged and one untagged `ROUTING_MISS`: returns only the untagged one.
10. `core.build.tick._count_faults` over a tmp `quality_events.json` with three tagged and two untagged events naming the same registered capability: counts 2.
11. Source check: both twins pass `user_turn=` to `_handle_user_correction`.

**Cost:** run 0. Ancillary: on a scheduled turn the Coordinator gets an error string back if it calls the tool for a refused type. That is one wasted tool result inside a turn it already spends, at the same rate as today's calls. **Risk:** an unbound path that is in fact a no-words turn would still write untagged. The only such path found is `core/interview.py`, which is not a scheduled path.

### #2 — the morning brief and day close always hear from Mental Wellbeing and Physical Health, and those two record nothing from a turn with no user words (D4, enforced with S6's write guard)

**What a user notices:**
- Every scheduled morning brief and day close carries the whole-person check: sleep, energy, mood, a missed medication. Today the Coordinator skips it (14 self-reported misses).
- Those runs never add log or journal entries of their own. On 10-29 those self-written entries came back as "evidence", and a later counter (#14) would count them.

**Mechanism, part A: the dispatch.**
- `_dispatch_from_coordinator` gains `session: str | None = None`. Both twins pass `session=kind`: non-streaming `:7876`, streaming `:8175`; `kind` is already computed at `:7821` / `:8142`, and is None on a nudge.
- After the specialist list is parsed, and only when `session in _FIXED_SESSION_KINDS` (the existing `frozenset({"morning_brief", "evening_close"})`, `:477`): for each of `mental_wellbeing` and `physical_health` not already present after `normalize_agent_name`, append `{"agent": X, "mode": "deep", "fire_and_forget": False, "directive": _whole_person_directive(X, session)}`.
- **Two fixed directives, built in code, generic, with no personal data (review S5):**
  - **Mental Wellbeing: tone only.** *"Scheduled {morning brief | day close}. The user has not spoken; nothing in this message is theirs. Give tone context only: in a line or two, how the user has seemed in their own recent entries. Raise no clinical history, past disclosure or concern from an earlier session, and set no clinical flag — a concern is raised only on the user's own words. Nothing you write in this session is kept — do not call write_log or write_journal."*
  - **Physical Health: the scan.** *"Scheduled {morning brief | day close}. The user has not spoken; nothing in this message is theirs. Run your proactive scan over what is already on file and report what is worth raising today, with your usual flags. Nothing you write in this session is kept — do not call write_log or write_journal."* Its `MEDICATION_MISSED_CRITICAL` is data-driven and valid without user words (`_drop_unprompted_clinical_flags` exempts it by design).
  - **Listed by the Coordinator too:** on these two sessions Mental Wellbeing's directive is **replaced** by the tone-only one even when the Coordinator listed it. The Coordinator's directive was built from the scheduler's prompt, not user words, so nothing the user said is lost. The replaced text goes on the `_trace` line only. Physical Health keeps the Coordinator's directive when listed, with the mode forced (D-S2-2.2).
  - This closes the shape the review describes: a narrative of a past disclosure reaching the Synthesizer twice a day with only its flag lines stripped.
- `_trace("[PIPELINE] whole-person: added X")`.
- The typed greeting is untouched: `session_kind()` is None for a user who types "good morning", so that half stays the Coordinator's rule (closing-round edit 1).

**Mechanism, part B: the write guard.**
- In `dispatch_tool`, before the call is bound and executed: when the calling agent is `mental_wellbeing` or `physical_health`, the tool is in `_NO_WORDS_REFUSED_WRITES`, and the **bound turn** has `user_turn` False, return a fixed result without calling the tool: *"Not recorded: this session carries no words from the user, so nothing from it is written. Report what you found instead."*
- The call is still recorded on the trace (`record_tool_call`, `ok=True`, because it is a designed refusal and not an error).
- **Bound turn only, deliberately, never the trace's `is_proactive`.** The weekly `weekly_physical_review` job is a single-agent `run_session` with no bound turn, and its job *is* to write a summary to the log (`config/templates/scheduler.yaml:102`). Keying on the trace would silence it.
- This also covers a follow-up the Synthesizer runs with `run_subagent` on a scheduled turn, because that runs on the Synthesizer's thread with the turn bound.

> **RULED — D-S2-2 (as recommended, Mike 2026-11-23).**
> 1. **Tool set:** all five record writers these two agents hold, `_NO_WORDS_REFUSED_WRITES = {"write_log", "write_journal", "write_archive", "write_profile", "write_wisdom"}`. `write_agent_config` (the agent's own working notes) and `request_build` stay allowed.
> 2. **Mode:** `deep` for both agents on these two sessions, whether added or listed. A listed `quick` would run on Flash-Lite (`quick_override`, `core/router.py:112`; neither agent is `local:` in `routing_cloud.yaml`) and, after #9, skip the scan. Cost: those calls move from Flash-Lite to 3.8 Flash, two sessions a day at most.

**Clinical rule:** no flag is cleared.
- `_drop_unprompted_clinical_flags` (`:6833`) still runs after dispatch, so on these runs it still removes Mental Wellbeing's `CLINICAL_CONCERN`, `ESCALATION` and `MUST_SURFACE`. That is unchanged: it already applies to any scheduled turn, and the tone-only directive asks for no flag in the first place.
- Physical Health's data-driven `MEDICATION_MISSED_CRITICAL` survives, as that function intends. Stage 3's `_after_specialists` adds the code-computed medication check on this dispatch too.
- `_record_reported_doses` is already gated by `user_turn` (`:6645`).

**The A4 fixture (review S5; it runs inside Stage 3's clinical gate run, so it adds no separate live run).** Add one scenario to `tests/run_a4_safety.py`'s clinical suite:
- **Setup.** A new `seed_disclosure_fixture(persona)` beside the existing seed helpers (`:287`, `:445`) writes one dated Mental Wellbeing journal entry 3 days old into the test persona (`sarah_chen`). The entry records a past low-mood disclosure, worded with fixture-only marker phrases. The scenario calls `_run_single_agent("mental_wellbeing", _whole_person_directive("mental_wellbeing", "morning_brief"), …)` with the **same function code uses**, so the fixture exercises the real text.
- **Pass, an absence check:**
  - no `CLINICAL_CONCERN`, `ESCALATION` or `MUST_SURFACE` token;
  - none of the fixture's marker phrases;
  - no reference to "last time", "earlier", or the disclosure's date.

  The runner's existing pass logic checks token *presence*, so the scenario carries a new `expect_absent: [...]` field, read by `run_one` (`:465`).
- **Cleanup.** The seeded entry is removed in `finally`, the same way the medication fixture is.
- **Cost:** one extra Mental Wellbeing call on 3.8 Flash inside a run that is already paid for, about a cent.

**Files:**
- `core/orchestrator.py` (Amber): the dispatch, `dispatch_tool`, both twins.
- `config/templates/scheduler.yaml:72`: the comment becomes "Day-close = whole-person session: code adds Mental Wellbeing + Physical Health (core/orchestrator.py `_dispatch_from_coordinator`); the Diarist runs only on the user's reply". This is the template only, Amber. Live persona copies are VM-owned and not touched.

**Tests: `tests/test_whole_person_sessions.py`.** Stub `_run_single_agent`, the way `tests/test_diarist_user_turn_gate.py` does. Cases:
1. `session="morning_brief"` with an empty list: both added, mode `deep`. Mental Wellbeing gets the tone-only directive and Physical Health the scan directive.
1b. Mental Wellbeing listed by the Coordinator with its own directive on `morning_brief`: the directive is replaced by the tone-only one, and the mode is `deep`.
2. With `"Physical Health"` already listed as quick: not duplicated, its mode becomes deep, and the Coordinator's directive is kept.
3. `session="evening_close"`: the same.
4. `session=None`: nothing added.
5. `session="companion_checkin"`: nothing added.
6. A nudge (`session=None`): nothing added.
7. The write guard, inside `turn_scope(user_turn=False)`. `dispatch_tool("write_log", …)` with an agent record named `mental_wellbeing`:
   - returns the refusal;
   - the handler is never called;
   - the trace records the call.
8. The same for `physical_health` across the whole set.
9. The same call under `user_turn=True`: the handler is called.
10. The same call by `logistics` under `user_turn=False`: the handler is called (the scope is these two agents only).
11. No bound turn, with a proactive trace (the weekly-review shape): the handler is called.
12. End to end through `_dispatch_from_coordinator` + `_drop_unprompted_clinical_flags`, with stub outputs:
    - Mental Wellbeing's stub `FLAGS: CLINICAL_CONCERN: X` is dropped on the brief;
    - Physical Health's stub `FLAGS: MEDICATION_MISSED_CRITICAL` survives.
13. Source check: both twins pass `session=`.
14. **Second persona (review L9).** Two tmp personas, each with its own `scheduler.yaml` carrying a `morning_brief` prompt, and each with a distinct marker in its own data dir.
    - Run `session_kind()` with persona B's prompt, then `_dispatch_from_coordinator(..., persona="zz_b", session=<kind>)`.
    - The stub records `persona` and `current_persona()` inside the worker thread: both are `zz_b` for both added agents.
    - Nothing under persona A's dir is read (the stub asserts on paths).
    - Persona A's prompt text under persona B returns no kind, so nothing is added.

**Consent, stated accurately (review L9).** No consent check sits in `_run_single_agent` or `core/router.py`. A user's base consent (`base_configuration`) is enforced when the account is created (`core/server.py:338–345`), so a pipeline turn exists only for a consented user. The code-added dispatch is the same processing as a Coordinator-listed Mental Wellbeing or Physical Health call on that user's turn, so it needs no new scope. The app scopes (`core/consent.py:52`: `correspondence_read`, `tone_profile`) do not cover these agents.

**Cost:**
- **Run:** at most 2 sessions × 2 specialists a day, about **$0.05/day/user** on 3.8 Flash. That is the sweep's estimate, doubling from 2027-01-01. It is lower where the Coordinator already lists them.
- **Ancillary:** the Synthesizer's input grows by two specialist outputs (about 0.5–1.5k tokens) on those two sessions. Where a model still tries a write, the refusal costs a wasted tool round; the directive text is there to prevent it.
- **Unseen:** none persistent.

**Risk:**
- On a persona whose scheduler names its sessions differently, nothing is added. `_FIXED_SESSION_KINDS` is already the key the ritual and focus code relies on.
- The tone-only directive is an instruction, not a mechanism. If Mental Wellbeing still narrates a past disclosure, the A4 fixture catches it on the next gate run. The flag lines are dropped by code regardless.

### #4 — open threads stop piling up past five, and the cap never drops something held back or a clinical thread (review S7.1)

**What a user notices:** Metatron's list of "things still open" stays at five or fewer, so a stale sixth topic stops resurfacing. Nothing deliberately held back, and no clinical concern, is ever cut to make room.

**Mechanism:**
- `_OPEN_THREADS_CAP = 5` in `tools/context_tracker.py`.
- In `write_context_tracker`, after `stamped_open_threads = _merge_open_threads(...)` (`HEAD` `:1513`): if there are more than 5, drop the oldest by `added` (ISO date; ties go to the earlier list position). Kept threads stay in the Synthesizer's order.
- **A thread the user engages this turn is never capped (review L6).** `_user_engages_thread(text, user_text)` true means it is exempt, and it is ordered as today's date for the cap only. Its stored `added` is not changed, so `[DB-0814-02]`'s expiry semantics are untouched.
  - This is needed because an exact-text re-send keeps its stored date in `_merge_open_threads` (`:414–418`) before engagement is ever checked, so "oldest" was not "least recently engaged".
  - If more than 5 are engaged in one turn, all engaged ones are kept and the list runs over 5 for that turn.
- Each dropped thread is archived, never deleted: it goes to `expired_open_threads` as `{**t, "expired_on": today, "capped_on": today, "reason": "cap"}`, under the existing `_EXPIRED_OPEN_THREADS_CAP` of 50.
- **A capped entry blocks re-entry for a limited time only (review L6).** In the `archived_keys` build (`:1473`), an entry with `reason == "cap"` participates only while `capped_on` is within `_OPEN_THREAD_EXPIRY_DAYS` (7) days. After that it is inert: it stays in the archive, but no longer blocks a re-send or a new thread that shares two anchor tokens.
  - Inside the window the user engaging it re-admits it, the same rule as expiry.
  - Expiry-archived entries (no `reason`) keep today's behaviour exactly.
- `_append_audit` gains a sixth category, `capped=[…]`. These threads are excluded from `removed`, following the module's rule that audit categories are never folded together.
- `held_items`, `clinical_threads`, `patterns` and `follow_ups` are never capped. The last two carry no date to pick "oldest" by, so they stay with the instruction (`synthesizer.md:261`, unchanged).
- Applied inside the one writer, so it covers the `[CONTEXT]` path. After M6 no tool path writes `open_threads` at all.

**The function-call move: measured only, not switched.** One read-only, one-off script, `scripts/session_shape_baseline.py`. Zero model tokens. It reads `data/personas/<p>/traces/YYYY-MM-DD.jsonl` (each agent turn's `output_text` and `tool_calls` are serialised, `core/trace.py:386`) and `logs/quality_events.json` for a date window (`--since`/`--until`), and reports, per persona:
1. **[CONTEXT] block health.** Each Synthesizer reply's final-turn text goes through `core.orchestrator._repair_context_json`, and is counted as one of: `clean`, `repaired:<how>`, `partial salvage`, `unrecoverable`, `absent`. `CONTEXT_BLOCK_UNPARSED` events are reported beside it. This is #4's number.
2. **Synthesizer tool rounds per reply.** Distinct turns with tool calls, which is what a function-call block would add to. Also:
   - the share of replies that reach `_SYNTH_MAX_ROUNDS` (4), with `CHAIN_LIMIT_REACHED` events once #10 is live, for #10;
   - `run_subagent` calls per reply;
   - `write_quality_event` tool calls per reply, which is M11's baseline.
3. **M7's shadow figures** (§ 1 M7), from the trace's `annotations.clarification`. Before deploy the script falls back to parsing the Coordinator's `output_text` for the line.
4. MW/PH presence on `session_kind()` ∈ {morning_brief, evening_close} runs. This is #2's before-figure.

**Where it is recorded:** the data is on the VM, so this is an **(M) step**. It is one command, run read-only on the VM over a pre-deploy window (`--until` the deploy date). Its stdout is saved by the driver as `archive/plans/session_shape_baseline_<run-date>_vm.md`.

**Decision rule, to be put to Mike with the numbers:** propose the function-call switch (as its own spike, which must first prove Gemini tool-call arguments work on the cached-stream path) only if lossy blocks (`partial salvage` + `unrecoverable`) reach **≥1 in 100** replies. Otherwise the block stays.

**Retirement** (`.claude/rules/deploy.md` standing rule): the script is deleted in the commit that records that decision. It is not standing machinery.

**Files:** `tools/context_tracker.py` (Amber); `scripts/session_shape_baseline.py` (Green, one-off).

**Tests:**

`tests/test_open_thread_cap.py`:
1. 7 threads with distinct `added` dates: the newest 5 kept in order, the 2 oldest in `expired_open_threads` with `reason: "cap"` and `capped_on`.
2. A re-send of a capped text on the next write, with non-engaging `user_text`: not re-admitted.
3. The same text with `user_text` engaging it: re-admitted, stamped today.
3b. Six threads where the **oldest** is the one the user engages this turn (an exact-text re-send): it is kept, and the next-oldest is capped instead.
3c. A capped entry whose `capped_on` is 8 days old: a re-send of it, and a new thread sharing two anchor tokens with it, are both admitted. An expiry-archived entry of the same age still blocks (unchanged).
4. 8 `held_items` (strings, and Stage 4's dict shape), 7 `clinical_threads`, 8 `patterns` and 8 `follow_ups`: all kept.
5. The audit line has `capped` and the capped texts are not in `removed`.
6. Exactly 5: untouched.

`tests/test_session_shape_baseline.py`:
1. Synthetic jsonl traces in a tmp dir, with one each of:
   - a clean block, a repaired block, a salvaged block, an unrecoverable block, and no block;
   - a reply whose Synthesizer record has 4 tool rounds;
   - a trace with `annotations.clarification` (shadow) and one without (the pre-deploy fallback: `CLARIFICATION_NEEDED: none` and a real value).

   The counts come out exact.
2. The script writes nothing.
3. Its report prints counts and value-shape categories only, never the clarification text. That text can carry names, and the report file lands in the repo.

**Before building, the builder checks** whether `tests/test_open_thread_expiry.py`, `test_thread_identity.py` or `test_context_audit_line.py` write more than 5 threads and assert they all survive. If one does, it reports which one rather than silently editing the assertion.

**Cost:** run 0. Ancillary: archive entries (bounded at 50).

**Risk:** oldest-first by `added` is the order code can decide exactly (S7.1), and the engaged-this-turn exemption covers the case that order gets wrong. A capped thread can block a lookalike *new* thread for up to 7 days. That is the same exposure expiry-archived threads already carry, bounded rather than permanent.

### #10 — when a reply runs out of follow-up rounds, the user is told plainly what is still unchecked, and the event is recorded (`[DB-0804-02]` (a)); rewritten in Revision 1 (review S4)

**What a user notices:**
- When a reply has used all its follow-up rounds, Metatron says in a sentence what it could not check or finish ("I couldn't get to Friday's calendar yet"), instead of answering as if everything had been checked.
- Each time this happens it is recorded, so a question that keeps running out of rounds becomes visible.

**Today, verified at `HEAD` `8ef2edf`:**
- The production Synthesizer path already has the limit. `run_session_gemini_cached_stream` (`core/orchestrator.py:5074`) is the Synthesizer's alone. It runs `_run_gemini_native_stream` with `max_iterations=_SYNTH_MAX_ROUNDS` (`:5125`), and `_SYNTH_MAX_ROUNDS = 4` (`:4507`).
- When the loop ends with tools still being asked for, either because the rounds ran out or because of the soft deadline (`:4864`), `_final_reply_round` (`:5031`, called at `:5021`) runs one tools-off round under `_FINAL_REPLY_PROMPT` (`:4522`).
- So the chain is already bounded, and nothing is refused: every call a round asks for runs, and the cap only stops a fifth round from starting.
- What is missing is the two halves `[DB-0804-02]` (a) names: nothing records the condition, and the final prompt ("Reply to the user now, from what has been done so far") carries no consequence wording.
- `ROADMAP.md:817` (09-03) predates the cap and is stale on this. The driver corrects it at `/archive`; it is not a Red file.

**Mechanism (no new counter, no refusal; D-S2-3 withdrawn):**
1. **Know why the loop ended.** In `_run_gemini_native_stream`, set `ended_on_deadline = True` at the soft-deadline `break` (`:4864–4866`). When execution reaches the post-loop block (`:5019`), `not ended_on_deadline` means the round cap ended it. That block is reached only when the last round asked for tools; a no-call round returns inside the loop.
2. **Record it.** When the cap ended it and the current agent is `synthesizer`, call `_note_round_cap(rec, max_iterations, last_calls)`. It writes `write_quality_event("CHAIN_LIMIT_REACHED", "synthesizer", f"reply reached the {max_iterations}-round tool limit; last round called: {names}")`.
   - `names` are the last round's tool names, plus `run_subagent`'s `agent_name` values, which are specialist names, not user content.
   - It is once per request (per-trace dedup), never raises, and is not in #1's refused set, so a scheduled turn records it too.
   - The soft-deadline exit is not this event; it keeps its existing warning line.
3. **B4's consequence wording.** `_FINAL_REPLY_PROMPT` becomes:
   *"Your tool budget for this turn is spent. Reply to the user now, from what has been done so far. Do not call tools. If something you set out to check or do is still not done, say so in one plain sentence — what is still unchecked or undone, never why, and never how you work."*
   This follows `_unavailable_notice`'s rule (`:6890`): code states the consequence and the posture, and the Synthesizer says it in its own words. The same prompt also serves the MAX_TOKENS replacement path (`:4954`), where the added sentence is harmless. **Limit:** `final = "" if result else _final_reply_round(...)` (`:5021`) skips the final round when round 4 already streamed text beside its calls. That text stands as the reply (today's behaviour), so the B4 sentence is not added there. The event is still recorded.
4. **Clinical rule.**
   - No call is refused, so no Mental Wellbeing or Physical Health follow-up is ever the one dropped (review L3).
   - A clinical flag returned in round 4 reaches the final round in `contents` and is answered there.
   - Nothing here clears a flag.

**Known limit, stated:** the blocking twin (`run_pipeline_session` → `_run_gemini_native_loop`, `max_iterations` 8) and the OpenAI-compatible fallback (`_openai_compat_stream`) neither cap at 4 nor record the event. Both are off the production path: the server streams through the cached-stream entry. This is not widened here.

**Files:** `core/orchestrator.py` (Amber): `_run_gemini_native_stream`'s exit, `_note_round_cap`, and `_FINAL_REPLY_PROMPT`.

**Tests**, extending `tests/test_native_stream_limits.py`, which already fakes the native client and drives `_SYNTH_MAX_ROUNDS` rounds (`:108–131`):
1. `_SYNTH_MAX_ROUNDS` rounds that each call a tool and stream no text, under a current-agent record named `synthesizer`: one `CHAIN_LIMIT_REACHED` event naming the last round's tools, and the final round runs.
1b. The same, but round 4 streams text beside its call: the event is still written, and no final round runs (unchanged).
2. The same with `run_subagent(agent_name="physical_health")` in round 4: that call is dispatched (the stub records it), and its result is in the final round's `contents`.
3. A soft-deadline exit (monkeypatch `_past_soft_deadline`): no `CHAIN_LIMIT_REACHED`.
4. A reply that ends with text in round 2: no event.
5. The same cap exhaustion under a non-Synthesizer agent record: no event.
6. The final round's request carries the new `_FINAL_REPLY_PROMPT` text.
7. The event is written on a no-user-words turn too (`turn_scope(user_turn=False)`).

**Cost:** run 0. The final round already exists, and the prompt grows by about 40 tokens on that rare round only. Ancillary: none. **Unseen:** none; no state is created.

### M7 — a turn the Coordinator marks ambiguous is measured first (shadow), and held only once the figures say it is safe; Mental Wellbeing and Physical Health are never held

**What a user notices, this run:** nothing. That is deliberate (D-S2-4, ruled shadow first). Code records every turn it *would* have held. The figures decide whether a later change turns the hold on. When live, a turn where what the user said has two plausible readings and would record or send something will ask first, instead of saving a wrong contact or booking the wrong thing in the same breath.

**Verified:** no code reads `CLARIFICATION_NEEDED`, and `synthesizer.md` never mentions it. Every listed specialist runs and writes. The Coordinator's package, including the line, already reaches the Synthesizer verbatim.

**Why shadow (review S1):**
- `is_null_ish` (`tools/logger.py:60`) is a whole-value match against a short set, so "No clarification needed" or "Not needed" on a clear turn reads as a real value.
- A live hold would turn every such turn into a question with nothing done.
- The rate is unknown until it is measured.

**Mechanism, this run (shadow):**
- **Parse.** `_clarification_needed(coord_output) -> str | None` in `core/orchestrator.py`, the **one** parser (Stage 5's #19 imports it).
  - It matches `^\s*CLARIFICATION_NEEDED:\s*(.+)$` (multiline).
  - It returns None for a null-ish value, a bracketed template echo (a value starting with `[`), or a value matching `_NO_CLARIFICATION_RE`: a leading negation of need, such as `^(no|not)\b.*\b(needed|required|necessary|applicable)\b` or `^nothing\b`.
  - It is computed once per twin, right after the Coordinator; it is None on a nudge.
- **Would-hold.** `_would_hold(specialists, data_turn) -> dict` names what a live hold would stop: listed agents not in `_NEVER_HELD = {"mental_wellbeing", "physical_health"}` (the Diarist, delegated read-backs and the code-added Diarist included), and the `DATA_OBJECTS` `start`/`add`/`amend` acts. **It holds nothing.** Dispatch, data objects and the Synthesizer input are unchanged.
- **Where the shadow is recorded.** A new optional `annotations: dict` on `RequestTrace` (`core/trace.py`, Amber), serialised by `_serialize` beside `is_proactive`.
  - M7 writes `annotations["clarification"] = {"value_shape": <"free text"|"negation"|"bracket"|"null-ish">, "chars": len(value), "user_turn": bool, "would_hold": [agent names], "would_skip_writes": [acts], "synth_redispatched": [agent names]}`.
  - It is written for every Coordinator package that carries the line at all, including the ones the parser rejects, so that the filter itself is measured.
  - `synth_redispatched` is filled after the Synthesizer runs, from the trace's `run_subagent` calls whose `agent_name` is in `would_hold`. That is how often the catch-up rules (`synthesizer.md:273–274`) would have bounced off a live hold (review S2).
  - **The value text itself is not stored** (names can appear in it); only its shape and length are.
- **The measure** (baseline script item 3), over at least 7 days of user turns, run on the VM:
  1. the share of user turns whose line passes the parser;
  2. the shape breakdown of the ones rejected;
  3. the mean `would_hold` size;
  4. the share with `synth_redispatched` non-empty.

  It is saved as `archive/plans/session_shape_baseline_<run-date>_vm.md` (counts and shapes only).
- **Go-live criteria, for a later decision put to Mike with those figures:**
  - passing lines are ≤ 5% of user turns;
  - a sample of passing values, read by Mike *on the VM*, are genuine ambiguities.

**Specified now, active only when live (constant `_CLARIFY_HOLD_LIVE = False`; flipping it is a later change, not this run):**
- **Hold the dispatch.** `_dispatch_from_coordinator(..., clarify=…)` keeps only `_NEVER_HELD` agents. `_resolve_data_objects(..., hold_writes=True)` skips `start`/`add`/`amend`, so no pending marker is set and no false "didn't save" note appears.
- **Hold the Synthesizer's second hop (review S2).** The bound turn dict carries `clarify_hold = True`. In `dispatch_tool`, when the calling agent is `synthesizer` and `clarify_hold` is set:
  - `run_subagent` to an agent not in `_NEVER_HELD` returns *"Not run: this turn is waiting for the user's answer to a question. Ask it; nothing is recorded or sent until they answer."*;
  - any tool in `core/actions.py` `ACTION_TOOLS` (`:46`) returns the same text;
  - `run_subagent` to Mental Wellbeing or Physical Health always runs.
- **M11 on a held turn.** `_persist_routing_miss` writes nothing while `clarify_hold` is set: the missing specialists were held by design, not missed.
- **Tell the Synthesizer.** A clarify note goes into `synthesizer_input`: *"CLARIFICATION NEEDED (from code): nothing was recorded or sent this turn. Ask the user, in one short question: {clarify}."*
- **Preconditions of going live, owned by that change:**
  - capture fidelity must exclude a held turn from scoring (review L7). `_capture.defer` (`tools/capture.py:1394`) returns at once in shadow mode and is not equivalent, because the Synthesizer still runs and `after_synthesizer` (`:1377`) still scores;
  - the Coordinator's two Red edits (`coordinator.md:52`, `:143`, drafted in § 3 as "deferred") go in the same change.

**Clinical rule:** Mental Wellbeing and Physical Health are never held, in dispatch or as a Synthesizer follow-up. Nothing clears a flag, and in shadow nothing changes at all.

**Files:** `core/orchestrator.py` (Amber); `core/trace.py` (Amber, `annotations`).

**Tests: `tests/test_clarification_hold.py`.** Stub `_run_single_agent` and `tools.data_objects`. Cases:
1. **Parser.**
   - `none`, `N/A`, `[if applicable — …]`, `No clarification needed`, `Not needed` and `Nothing to clarify` → None.
   - `"Ella or Bella — which one?"` → the value.
2. **Shadow, a real value with five listed specialists:**
   - all five run;
   - `DATA_OBJECTS` `add` still calls `mark_pending`;
   - the Synthesizer input is byte-identical to the input without M7;
   - `annotations.clarification.would_hold` names the three non-MW/PH agents;
   - no value text is stored.
3. **Shadow, a rejected value** (`Not needed`): the annotation is written with `value_shape: "negation"` and empty `would_hold`.
4. **Shadow, `synth_redispatched`:** a stubbed Synthesizer `run_subagent("logistics")` with `logistics` in `would_hold` → recorded.
5. **Live paths, with `_CLARIFY_HOLD_LIVE` monkeypatched True:**
   - only Mental Wellbeing and Physical Health run;
   - no `mark_pending`;
   - a Synthesizer `run_subagent("relationships")` and an `update_task` are refused;
   - `run_subagent("physical_health")` runs;
   - `_persist_routing_miss` writes nothing;
   - the clarify note is present.
6. Physical Health's `MEDICATION_MISSED_CRITICAL` stub output survives in both modes.
7. **Source check:** both twins call `_clarification_needed` and pass `clarify=`.
8. **Trace:** `_serialize` emits `annotations` only when non-empty, so existing trace consumers see no new key on ordinary turns.

**Cost:** run 0 in shadow: a regex and a dict per turn, and about 150 bytes on a trace line only when the line is present. **Risk:** none to users this run. The shadow's own risk is a measurement blind spot if the Coordinator phrases the line in a shape the parser misses entirely (no `CLARIFICATION_NEEDED:` prefix); the fallback parse in the baseline script reads the raw output for that.

### M10 — the Coordinator stops re-typing the user's whole message on every turn

**What a user notices:**
- Replies start a little sooner on every turn, by the time the bulk model spends re-typing the message. Long dictated batches gain the most.
- A copy truncated mid-message can no longer stand in for what was said: on 11-20 a truncated copy dropped the cardiac entry.

**Verified by grep:** no code parses `ORIGINAL_MESSAGE` (all of `core/`, `tools/`, `scripts/`, `static/` and `tests/*.py`). Its only appearances are:
- `_NUDGE_PACKAGE`'s first line (`core/orchestrator.py:6709`), a literal stand-in that nothing reads;
- recorded probe JSON fixtures (`tests/coord_model_probe_*.json`, `tests/referent_probe_*.json`), which are historical outputs, not parsers;
- the agent files.

The Synthesizer already receives the user's own words under `ORIGINAL USER MESSAGE` (`_frame_proactive`, `:7727`; the label at `:7735`). On a scheduled turn the label is `SCHEDULER DIRECTIVE (the user has not spoken yet)`.

**Mechanism:** Red-only for the behaviour (opening round, § 2). Amber cleanup: delete the `ORIGINAL_MESSAGE:` line from `_NUDGE_PACKAGE`; `tests/test_day_plan_wiring.py:66` asserts only `_NUDGE_PACKAGE if nudge else`, so it is unaffected.

**Files:** `core/orchestrator.py` (Amber, one line); `config/agents/coordinator.md` and `synthesizer.md` (Red, opening round).

**Tests: `tests/test_coordinator_package_shape.py`.**
1. `_NUDGE_PACKAGE` has no `ORIGINAL_MESSAGE`.
2. A source scan of `core/` and `tools/` finds no reader of `ORIGINAL_MESSAGE`.
3. `_frame_proactive("x", False)[1] == "ORIGINAL USER MESSAGE"`.

**Cost:** run, negative: the Coordinator emits fewer output tokens per turn, equal to the message's length. The prompt shrinks by about two lines; the Coordinator is on the cached path, and `_pad_for_vertex_cache()` absorbs the difference against the 4,096-token floor (CLAUDE.md trap 6). The builder checks the padded size in `tests/test_review_2026_11_05_orchestrator.py` or the cache tests if any assert it.

**Risk:**
- The Coordinator might paraphrase where it used to quote. But its directives already carry the corrected names, and `RESOLVED_INTENT` stays.
- The Diarist already gets the user's own words appended by code (`:7073`).

### M11 — reporting a routing miss no longer costs the Synthesizer an extra model round

**What a user notices:** on a turn where the Synthesizer catches a miss (for example, a clinical signal no specialist raised), the reply no longer waits on a second head-model round just to file it.

**Mechanism:**
- `_persist_routing_miss(value)` beside `_persist_dev_request` (`core/orchestrator.py:2791`). It is called from `persist_context_block` in its own `try`, so neither failure costs the other.
- **Accepted shape:** `{"agent": "<specialist that should have caught it>", "detail": "<what was missed>"}`, or a list of them.
  - Each `agent` goes through `normalize_agent_name(…, _AGENT_NAME_MAP)`.
  - `detail` must be non-empty and not null-ish.
  - A list becomes one event, with details joined by `; ` and agents by `,`. One event per turn is the existing rule, and the per-trace dedup would drop a second anyway.
- It writes `write_quality_event("ROUTING_MISS", source_agent=agents, detail=…, session_id=…)`. Every existing guard applies:
  - null-ish;
  - `asserts_routing_success`;
  - per-trace dedup, so if the Coordinator already logged one this turn the block's copy is skipped, which matches "one event per signal per turn";
  - #1's no-user-words rule: on a scheduled turn the event is written tagged `scheduled` (D-S2-1 option 3), so it stays out of the backlog sync and the REPAIR count.
- **Held turn (M7, live only):** while the bound turn carries `clarify_hold`, `_persist_routing_miss` writes nothing (review S2). That is inert this run.
- `"routing_miss"` is added to `_CONTEXT_KEYS` (`:2506`), so a broken block still salvages it.
- `persist_context_block` runs while the trace and turn are still bound in both twins (`:7973` before `:8000`/`:8001`; `:8434` before `:8516`), so dedup and #1 apply.
- The Synthesizer's `write_quality_event` **grant stays** (no routing edit; see § 5 for why that line is avoided). Its instruction text is pointed at the block in the closing round.

**Files:** `core/orchestrator.py` (Amber).

**Tests: `tests/test_routing_miss_block.py`.**
1. A block with `routing_miss` dict: one `ROUTING_MISS` event, with the normalised agent and the detail.
2. A list of two: one event, joined.
3. `null`, `{}`, `"none"`, or a missing `detail`: no event, no exception.
4. A success-claim detail: refused, with no exception escaping `persist_context_block`.
5. Under `turn_scope(user_turn=False)`: written with `"scheduled": true`.
5b. With the bound turn carrying `clarify_hold = True`: nothing written.
6. The Coordinator already logged `ROUTING_MISS` in this trace: deduped.
7. A malformed block where only `routing_miss` parses: salvaged and written.
8. The tracker write and `dev_request` are unaffected when `routing_miss` fails.

**Cost:** run, negative: one Synthesizer tool round avoided per reported miss. That is the head model's whole package re-sent at the cached rate, plus seconds of latency. The baseline script's item 2 gives the before-figure.

### Not #3 (D13: the forced Diarist waits for the capture-fidelity window).

---

## 2. Red edits — OPENING round (before any code) — final, exact against `HEAD` `8ef2edf`

**3 edits, all M10.** None depends on new code: the Synthesizer already receives the user's text under `ORIGINAL USER MESSAGE` (`core/orchestrator.py:7735`). Both files are clean against `HEAD`.

**O1. `config/agents/coordinator.md:113–114`. Delete** the line `ORIGINAL_MESSAGE: [verbatim user message]` and the blank line after it, so the block opens on `RESOLVED_INTENT:`.
*Reason:* code already gives the Synthesizer the user's own words. Re-typing them costs Coordinator output tokens on every turn and once truncated a cardiac entry (11-20).

**O2. `config/agents/coordinator.md:42`. Two in-line replacements:**
- `put the corrected form in `RESOLVED_INTENT` and every directive — specialists act on your directive, so a mis-heard name you pass on gets saved as a new contact or event; `ORIGINAL_MESSAGE` stays verbatim.`
  → `put the corrected form in `RESOLVED_INTENT` and every directive — specialists act on your directive, so a mis-heard name you pass on gets saved as a new contact or event.`
- `It is not part of what the user said: leave it out of `ORIGINAL_MESSAGE`.` → `It is not part of what the user said.`

*Reason:* the field is gone.

**O3. `config/agents/synthesizer.md:272–274`. Three in-line replacements:**
- :272: `read `ORIGINAL_MESSAGE` against what the specialists collectively reported.` → `read the user's own message (`ORIGINAL USER MESSAGE` in your input) against what the specialists collectively reported. On a scheduled session there is none — the text under `SCHEDULER DIRECTIVE` is the system's.`
- :273: `If `ORIGINAL_MESSAGE` contains a temporal commitment signal` → `If the user's message contains a temporal commitment signal`
- :274: `If `ORIGINAL_MESSAGE` asks for advice` → `If the user's message asks for advice`

*Reason:* point the sanity check at the label code provides. On a scheduled turn the scheduler's prompt is not the user's message, which also keeps `:36`'s "trust your own reading" from firing on no user words (review S5).

**Afterwards:** the `PostToolUse` hook (`scripts/hook_agent_tools.py`) fires. Then `python3 scripts/check_agent_tools.py` must exit 0.

## 3. Red edits — CLOSING round (after Stage 2 code is built and tested) — final, exact against `HEAD` `8ef2edf`

**8 edits.** Each is tied to the code that now carries it. Line numbers assume O3 has been applied; O3 changes no line count in `synthesizer.md`, and O1 removes two lines from `coordinator.md`, so `coordinator.md:174` becomes `:172`. C4 inserts one line after `synthesizer.md:259`, so **apply C4 last**, or match on the quoted text: every edit quotes its current text exactly.

**C1. `coordinator.md:172` (was `:174`; #2). Replace the whole paragraph**
`**Morning brief and day-close sessions are whole-person sessions.** When the session prompt is a morning greeting or day-close reflection ("Good morning", "How did today go", "end of day", "day close"), always call Mental Wellbeing and Physical Health regardless of message content. These are the two sessions where the proactive scan is most valuable and the user has space to receive it. Do not skip them in these contexts even if the message contains no explicit health or emotional signal.`
with:
`**A morning greeting or day-close reflection the user sends themselves is a whole-person turn.** When the user opens or closes their day in their own words ("Good morning", "How did today go", "end of day"), call Mental Wellbeing and Physical Health whatever the message says — this is when the user has space to receive the whole picture. The scheduled morning brief and day close get both from the system already.`
*Carried by:* `_dispatch_from_coordinator(session=…)`.

**C2. `synthesizer.md:36` (M11).** Replace `Write `ROUTING_MISS` in your context tracker note and call `write_quality_event`.` with `Record it as `routing_miss` in your `[CONTEXT]` block.`
*Carried by:* `_persist_routing_miss`.

**C3. `synthesizer.md:272–274` (M11), after O3:**
- :272: `note the gap in your context tracker write as `ROUTING_MISS: [what was missed and why it matters]`.` → `record the gap as `routing_miss` in your `[CONTEXT]` block.`
- :273: `Log `ROUTING_MISS: Logistics` in the context tracker and call `write_quality_event`.` → `Record it as `routing_miss` in your `[CONTEXT]` block.`
- :274: `Log `ROUTING_MISS: [specialist name]` in the context tracker and call `write_quality_event`.` → `Record it as `routing_miss` in your `[CONTEXT]` block.`

*Carried by:* `_persist_routing_miss`.

**C4. `synthesizer.md:251` and a new line after `:259` (M11):**
- :251: `- All four keys above must be present even if empty. `clinical_threads` is a fifth, optional key — see below.` → `- All four keys above must be present even if empty. `clinical_threads` is a fifth, optional key, and `routing_miss` a sixth — see below.`
- Insert after `:259` (the `clinical_threads` definition): `- `routing_miss` — **Optional.** Only when the user's message carried a signal no specialist surfaced: `{"agent": "<specialist that should have caught it>", "detail": "<what was missed>"}`. The system records it; if the package shows the Coordinator already logged it, omit it.`

*Carried by:* `_CONTEXT_KEYS` + `_persist_routing_miss`.

**C5. `synthesizer.md:381` (M11).** Replace `**When you detect a ROUTING_MISS, call `write_quality_event` with event_type `ROUTING_MISS`, source_agent set to the specialist that should have caught it, and detail set to a brief description of the missed signal.**` with `**Record it as `routing_miss` in your `[CONTEXT]` block (field definitions above).**` The following "One exception…" sentence is kept unchanged.
*Carried by:* the parser + per-trace dedup.

**C6. `synthesizer.md:414` (M11).** Replace `Call with event_type `ROUTING_MISS` whenever you detect a signal the specialist layer missed. See Internal flags section for when and how to call this.` with `A ROUTING_MISS does not go here — it goes in your `[CONTEXT]` block as `routing_miss`.`
*Carried by:* the parser. The grant stays (no routing edit), and the tool is still named, so `check_agent_tools` stays clean.

**C7. `synthesizer.md:147` (#10). Replace the whole line**
`**Default maximum: 3 rounds of follow-up calls.** If after 3 rounds you still need more, do not proceed blindly — include `CHAIN_LIMIT_REACHED` in your internal note and explain what additional information would have helped and why. This is catchable in testing.`
with:
`**Default maximum: 3 rounds of follow-up calls.** The system ends tool use after four rounds in all, asks you to reply from what you have, and records that the limit was reached. If you get there, say plainly what you could not check or finish.`
*Carried by:* `_SYNTH_MAX_ROUNDS` (existing) + `_note_round_cap` + `_FINAL_REPLY_PROMPT`. It drops the instruction to write a flag no code reads, and the false "catchable in testing".

**C8. `synthesizer.md:382` (#10). Delete the line** `- **CHAIN_LIMIT_REACHED: [what was still needed]** — the 3-round specialist chain limit was hit before the response was fully grounded. …` (the whole bullet).
*Carried by:* code writes `CHAIN_LIMIT_REACHED`.

**Unchanged, and why:**
- `synthesizer.md:131` and `:393` ("counts toward the 3-round limit") stay true: 3 rounds is still the model's own budget inside the code's four.
- **M6:** `pattern_miner.md:109` is still true, and the tool schema carries the semantics.
- **#1:** the Coordinator's steps 2 and 2b are still right for user turns.
- **#4:** `synthesizer.md:261`'s five-per-category rule still governs `patterns` and `follow_ups`; code backstops `open_threads` only.
- **Routing files:** no grant changes.

**Deferred out of this run, with M7 live (review S1).** Drafted here so the later change does not re-derive them. They are **not** part of either round:
- D1. `coordinator.md:52`: `The Synthesizer will ask the user before the next specialist pass.` → `Flagging it holds every specialist except Mental Wellbeing and Physical Health this turn, so nothing is recorded or sent until the user answers; the Synthesizer asks your question.`
- D2. `coordinator.md:143`: `[if applicable — what needs clarifying before Synthesizer responds; omit if not needed]` → `[only when a wrong reading would record or send something — the question to ask; omit otherwise]`

## 4. Builder brief (worktree from `HEAD`, Amber/Green only)

Work in a `git worktree` from `HEAD`. **Never touch** `config/agents/*.md`, `config/modules/routing*.yaml`, or `core/{router,persona,scheduler,spend_guard}.py`. Leave the untracked `tools/ranking_review.py` alone: it is another chat's and is not in `HEAD`. Commit nothing. No live model calls: stub `_run_single_agent` / `run_session` and every meter. Use tmp persona dirs only, and no real names in code, comments or tests.

**Order (M6 first, because it is data loss):**
1. **M6.**
   - `tools/context_tracker.py`:
     - factor `_clinical_merge_for_write` out of `write_context_tracker` (`:1440–1445`);
     - add `merge_pattern_findings`, which calls it for `clinical_threads`;
     - update `WRITE_CONTEXT_TRACKER_SCHEMA` (description, `required: ["patterns"]`).
   - `core/orchestrator.py` `register_tools`: import it (`:1445`) and map `"write_context_tracker": merge_pattern_findings` (`:1640`).
   - Test: `tests/test_pattern_miner_tracker_merge.py`.
2. **#4 cap.**
   - `tools/context_tracker.py`:
     - `_OPEN_THREADS_CAP`;
     - the cap after `:1513`, with the engaged-this-turn exemption;
     - `capped_on` and the 7-day participation limit in the `archived_keys` build (`:1473`);
     - `_append_audit(capped=…)` (`:1107`).
   - Test: `tests/test_open_thread_cap.py`.
   - First, check the existing expiry/identity/audit tests for more than 5 threads, and report any you find.
3. **#1.**
   - `tools/logger.py`: `_NEEDS_USER_WORDS = {"USER_CORRECTION", "INSTRUCTION_CHANGE_REQUEST", "FEATURE_REQUEST", "SELF_APPLIED"}`, `_no_user_words()`, the refusal, and the `ROUTING_MISS` `scheduled` tag.
   - `scripts/sync_dev_backlog.py` `fetch_events`: skip tagged events.
   - `core/build/tick.py` `_count_faults`: skip tagged events.
   - `core/orchestrator.py`: `_handle_user_correction(user_turn=)` plus both call sites (`:7862`, `:8164`).
   - Test: `tests/test_no_user_words_events.py`.
4. **`dispatch_tool` pre-call refusals** (`:2908`). These are small helpers called after the persona strip and before bind/execute. A refusal sets `result` and `ok=True`, skips execution, and still reaches `record_tool_call`.
   - `_no_words_write_refusal(agent, name)` for #2's guard, with the ruled five-tool set.
   - `_clarify_hold_refusal(agent, name, inputs)` for M7 live, inert while `_CLARIFY_HOLD_LIVE` is False.
   - Tests: the guard cases of `tests/test_whole_person_sessions.py`, and the live cases of `tests/test_clarification_hold.py`.
5. **#2 dispatch.**
   - `_whole_person_directive(agent, session)` (Mental Wellbeing tone-only, Physical Health scan) and `_dispatch_from_coordinator(session=)` (`:6925`), with force-deep and Mental Wellbeing's directive replaced on these sessions. Pass `session=kind` in both twins (`:7876`, `:8175`).
   - Update the comment at `config/templates/scheduler.yaml:72`.
   - `tests/run_a4_safety.py`: add `seed_disclosure_fixture`, the scenario, and `expect_absent` support in `run_one`. This is **built, not run, in this stage**: it runs in Stage 3's clinical gate run.
   - Test: the rest of `tests/test_whole_person_sessions.py`, including the second-persona case.
6. **#10.**
   - `_run_gemini_native_stream`: `ended_on_deadline` at `:4864–4866`, and `_note_round_cap` at the post-loop block (`:5019`).
   - `_FINAL_REPLY_PROMPT` (`:4522`) wording.
   - Tests: extend `tests/test_native_stream_limits.py`.
7. **M7 (shadow).**
   - `core/trace.py`: `RequestTrace.annotations` plus its `_serialize` entry (emitted only when non-empty).
   - `core/orchestrator.py`: `_clarification_needed`, `_NO_CLARIFICATION_RE`, `_would_hold`, the annotation after the Coordinator in both twins, and `synth_redispatched` after the Synthesizer.
   - The live paths behind `_CLARIFY_HOLD_LIVE = False`: dispatch hold, `hold_writes`, the turn flag, the clarify note, and M11's held-turn skip.
   - **In shadow the Synthesizer input must be byte-identical.** Put the live clarify note in a variable that is `""` in shadow.
   - Test: `tests/test_clarification_hold.py`.
8. **M11.**
   - `_persist_routing_miss`, called from `persist_context_block` (`:2747`); add `"routing_miss"` to `_CONTEXT_KEYS` (`:2506`).
   - Test: `tests/test_routing_miss_block.py`.
9. **M10.**
   - Delete `_NUDGE_PACKAGE`'s `ORIGINAL_MESSAGE` line (`:6709`).
   - Test: `tests/test_coordinator_package_shape.py`.
10. **Baseline script.**
    - `scripts/session_shape_baseline.py` (read-only, stdlib + `core.orchestrator._repair_context_json`, `--persona --since --until`). It prints counts and shapes only. The docstring names its retirement: it is deleted when the #4 decision is recorded.
    - Test: `tests/test_session_shape_baseline.py`.

**Every change that touches the pipeline goes in both twins.** Each test file that covers twin behaviour carries a source-inspection check, in the style of `tests/test_day_plan_wiring.py`. Return: the diff, each new test's output, and the § 6 suite results.

## 5. Collision notes (re-checked at `8ef2edf`)

1. **The ranking Part B phase 2 chat has committed** (`e134948`, `129f3fb`, `8ef2edf`). Its earlier collisions are gone:
   - `synthesizer.md`, both routing files, `tools/lookup_guard.py`, `tools/profile.py` and `tools/task_judge.py` are committed;
   - `coordinator.md` is clean against `HEAD`. `synthesizer.md` and both routing files have since picked up a later chat's lines (items 2b and 2c);
   - so are `core/trace.py`, `tools/logger.py`, `tools/context_tracker.py`, `scripts/sync_dev_backlog.py`, `core/build/tick.py`, `tests/run_a4_safety.py`, `tests/test_native_stream_limits.py` and `config/templates/scheduler.yaml`.
2. **`core/orchestrator.py` has new uncommitted hunks** from a later chat (ranking Part B phase 3) at the time of this revision. They import the **untracked** `tools/ranking_review.py`, so the landmine is the same as before.
   - **Their hunks:**
     - `session_kind` (`:362–388`): it now also reads agent-written `weekly_review` jobs. That does not affect `_FIXED_SESSION_KINDS`;
     - `register_tools` (`:1519`, `:1590`, `:1697`), for `record_signal`;
     - `_horizon_block` (`:6691`);
     - `_close_turn_bookkeeping` (`:7678`);
     - the `_horizon_block(...)` call in both twins (`:7932`, `:8225`), immediately above `synthesizer_input`.
   - **Mine near theirs:**
     - M6's import (`:1445`, about 75 lines above their `:1519`) and handler line (`:1640`, between their `:1590` and `:1697`). These are separate hunks in the same function;
     - M7's live clarify note, if the builder puts it in the `synthesizer_input` expression a few lines below their twin hunks. To keep the two apart, **build the note into an existing trailing variable assigned after `synthesizer_input` is formed, not inside the expression**.
   - **Mine far from theirs:**
     - `_handle_user_correction` (`:800`);
     - `_CONTEXT_KEYS` through `_persist_dev_request` (`:2506–2810`);
     - `dispatch_tool` (`:2908`);
     - the native stream (`:4507–5125`);
     - `_NUDGE_PACKAGE` (`:6709`);
     - `_dispatch_from_coordinator` (`:6925`);
     - the twins' Coordinator and dispatch lines (`:7821–7876`, `:8142–8175`).
   - **Rule:** if their hunks are still uncommitted when this stage's diff is brought into the main tree, **stop and ask** (driver rule; Mike's ruling was to wait for the other chat). Never stage `core/orchestrator.py` wholesale. Then export `HEAD` to a clean directory and import `core.orchestrator` there (`.claude/rules/deploy.md` rule 4).
2b. **`config/agents/synthesizer.md` has a new uncommitted hunk** (the same phase 3 chat): one line inserted after `HEAD` `:409`, the "A weekly conversation" tools bullet.
   - **Mine near theirs:** closing edit **C6** (`HEAD` `:414`, `:415` in the working tree). With git's 3-line context the two diffs overlap, so `git add -p` will show **one hunk** containing both.
   - O3 (`:272–274`) and C2–C5, C7 and C8 (`:36`, `:147`, `:251`/`:259`, `:272–274`, `:381`, `:382`) are all above it and unaffected. If their line is committed first, C6 is at `:415`. Every edit quotes its text, so match on text, not number.
   - **If it is still uncommitted at either Red round, stop and ask** rather than splitting the hunk by hand.
2c. **`config/modules/routing.yaml` / `routing_cloud.yaml`** are dirty again (the phase 3 chat's Synthesizer grant). This plan makes **no routing edit**, so there is no overlap. `config/modules/synthesizer_scheduled_sessions.md` is also dirty and is not touched here.
3. **`core/actions.py`, `tools/obligations.py`, `tools/day_plan.py`, `tools/schedule.py` and `core/server.py`** carry other chats' uncommitted lines. This plan only *reads* `core/actions.py` (`ACTION_TOOLS`) and edits none of them.
4. **Sibling stages.**
   - Stage 3's `_after_specialists` and Stage 4's prefetch and held-items edits touch the same functions after this stage lands, as the sibling plans already state.
   - This stage's closing Red edits do not overlap theirs. Stage 3 names `synthesizer.md:24–36` but edits none of `:36`'s routing sentence; Stage 4 edits `:265` and `:312`; Stage 5 edits `:101`–`:180` and `:409`.

## 6. Test suites to run afterwards

**New (§ 1):**
- `test_pattern_miner_tracker_merge.py`
- `test_open_thread_cap.py`
- `test_no_user_words_events.py`
- `test_whole_person_sessions.py`
- `test_clarification_hold.py`
- `test_routing_miss_block.py`
- `test_coordinator_package_shape.py`
- `test_session_shape_baseline.py`
- the extended `test_native_stream_limits.py`

**Existing ones these changes can break:**

| Area | Suites |
|---|---|
| Tracker (M6, #4) | `test_open_thread_expiry.py`, `test_thread_identity.py`, `test_context_audit_line.py`, `test_context_age_annotation.py`, `test_context_tracker_multiprocess.py`, `test_context_user_text_plumbing.py`, `test_context_block_repair.py`, `test_clinical_threads.py`, `test_clinical_escalation.py`, `test_unprompted_clinical_flags.py`, `test_degradation_paths.py`, `test_ritual_focus_gate.py`, `test_task_ledger_consult.py` |
| Quality events and their readers (#1, M11, #10) | `test_routing_miss_success.py`, `test_null_ish_events.py`, `test_empty_template_label_events.py`, `test_quality_event_reconciliation.py`, `test_grants_dedup.py`, `test_false_action_claim.py`, `test_false_claim_phrasings.py`, `test_noticed_logs.py`, `test_capture_fidelity.py`, `test_thought_signature.py`, plus every `tests/test_build*.py` and any `sync_dev_backlog` test (`grep -l sync_dev_backlog tests/`) |
| The native stream (#10) | `test_native_stream_limits.py`, `test_reply_latency*.py` if present (`ls tests/ \| grep -i latency`) |
| Dispatch and the twins (#2, M7, M10) | `test_diarist_user_turn_gate.py`, `test_data_objects.py`, `test_medication_taken.py`, `test_day_plan_wiring.py`, `test_pending_action_record.py`, `run_knowledge_routing.py` (if offline), `test_signoff.py`, `test_evening_ritual_gate.py`, `test_synth_module_injection.py`, `test_task_ledger_wiring.py`, `test_multi_user_isolation.py` |
| `dispatch_tool` (#2 guard, M7 live) | `test_tool_error_dict.py`, `test_tool_error_flag.py`, `test_action_provenance.py`, `test_review_2026_11_05_orchestrator.py`, `test_subagent_depth.py`, `test_trace_agent_stack.py`, `test_build_doors.py`, `test_interview_mode.py`, `test_filter_user_echo.py` |
| `register_tools` (M6) and the trace (M7) | `test_no_persona_in_schemas.py`, `test_read_tools.py`, and every test that reads trace JSON (`grep -l "_serialize\|traces/" tests/*.py`) |
| A4 runner (#2 fixture) | `python3 tests/run_a4_safety.py --help` (it parses), plus any offline self-test the runner has. **No live run in this stage.** |
| Security | `tests/run_b1_redteam.py --suite deputy`. It reads `_dispatch_from_coordinator`; run it only if it is offline (check `--help`); never live in this stage. |

**Gates:** `python3 scripts/check_agent_tools.py` (exit 0), `python3 scripts/check_claude_md_claims.py`, and `bash scripts/qa_sweep.sh`.

**No live A4 run for Stage 2.** No change alters a clinical flag on a user turn:
- Mental Wellbeing and Physical Health are never held (and M7 holds nothing this run);
- the write guard and the added dispatch act only on no-user-words turns;
- `_drop_unprompted_clinical_flags` is unchanged;
- #10 refuses no call.

The offline evidence is `test_whole_person_sessions.py` case 12, `test_clarification_hold.py` case 6, and `test_native_stream_limits.py` case 2. The new A4 disclosure fixture is built here and **runs in Stage 3's clinical gate run** (D10's lift, about $3–4, stated before that run); it adds about a cent to it.

---

## Budget

| Class | Cost |
|---|---|
| **Build** | About 200–250k weighted tokens: build about 170k (seven mechanisms, the shadow annotation, nine test files and one extended file, both twins); Fable narrow re-check of this revision about 20k; Fable diff review about 40k. |
| **Run** | +about $0.05/day/user for #2 (the sweep's estimate, doubling 2027-01-01), offset by M10 (Coordinator output per turn) and M11 (one head round per reported miss). #10 adds about 40 tokens to a rare final round. M7 shadow costs 0 tokens. Everything else is 0. |
| **Ancillary** | +0.5–1.5k Synthesizer input tokens on the two scheduled sessions. Capped threads go into the existing 50-entry archive. About 150 bytes on a trace line when a Coordinator package carries `CLARIFICATION_NEEDED`. One extra Mental Wellbeing call in Stage 3's paid A4 run. |
| **Unseen** | **No new persistent state.**<br>• The trace annotation rides the existing trace file and its existing retention.<br>• The `scheduled` tag rides the existing quality-event line.<br>• The baseline script is one-off and deleted at the #4 decision.<br>• No new standing job, cache or file. |

**Mike-gated (M) items:**
1. The baseline run on the VM: one read-only command, over a pre-deploy window for #4, #10 and M11, and over at least 7 post-deploy days for M7's shadow. Propose it as a two-minute guided step in the deploy walkthrough, with a second short session a week later for the M7 figures. That second session is also where Mike reads a sample of passing clarification values on the VM.
2. Nothing else in this stage needs Mike, apart from approving the two Red rounds.

---

## Build-time amendments (driver, 2026-11-23, from the Fable re-check of Revision 1)

The re-check found nothing structural and confirmed the Revision 1 closures. The builder applies
these five local fixes; each is part of the stage's acceptance.

1. **A refused write is recorded as refused, not completed.** The no-user-words write refusal
   (and the future live M7 refusal on the same helper) records `ok=False` on the trace with a
   result starting `Error: not recorded —`, so `action_provenance_block` (`core/actions.py`) shows
   it as failed and the Synthesizer is never told a write happened. Test 7 asserts the ACTIONS
   block shows the refused `write_log` as not done.
2. **Capping one thread must not silently remove its siblings.** A capped archive entry blocks
   only an exact re-send and a *new* lookalike thread. It is never matched against threads
   already kept open (`_is_archived` is applied to incoming entries that are not already open).
   Add a test: two related open threads, cap one, write again without engagement, and the other
   survives.
3. **The B4 final round fires whenever the cap ends a chain.** Reset or track `result` per round
   in `_run_gemini_native_stream` (and check the other Synthesizer loops for the same pattern), so
   a reply that streamed a sentence in an earlier round still gets `_final_reply_round` when the
   cap is hit. Test 1b covers text streamed in round 1, then the cap.
4. **Mental Wellbeing on the scheduled sessions runs `quick` with the tone-only directive.**
   Physical Health runs `deep`. This amends D-S2-2's second half for Mental Wellbeing only: a
   forced `deep` runs the history scan the directive exists to prevent. Before 4f wires quick
   mode, `quick` only picks the cheaper model tier. Mike is told.
5. **Register `CHAIN_LIMIT_REACHED`.** Add it to `WANTED` in `scripts/sync_dev_backlog.py`, so the
   event reaches the backlog's machine log, and keep `tests/test_quality_event_reconciliation.py`
   green. The sync script joins #10's file list.
