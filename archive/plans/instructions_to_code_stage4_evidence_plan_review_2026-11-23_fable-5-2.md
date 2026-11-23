# Fable 5.2 adversarial review — stage4 evidence plan (2026-11-23)

*Verbatim reviewer output; the driver's dispositions are in `instructions_to_code_plan_review_stop_2026-11-23.md`.*

## STRUCTURAL

1. [§1 #9 gates 3–4; §4 4f; §6 live check 6] [/Users/md-homefolder/Desktop/multi-model-mcp/tests/run_a4_safety.py:run_one (:480–486); /Users/md-homefolder/Desktop/multi-model-mcp/core/orchestrator.py:_dispatch_from_coordinator; /Users/md-homefolder/Desktop/multi-model-mcp/archive/plans/instructions_to_code_stage3_hard_fail_plan_2026-11-23.md §1.6]
Wrong: The A4 clinical-quick suite that gates quick-mode wiring calls `_run_single_agent(agent, prompt, complexity=...)` directly, while the plan injects the `mode: quick` directive prefix only inside `_dispatch_from_coordinator`.
Fails: The before and after runs send the specialist byte-identical input with no `mode: quick` text (the pipeline suite refuses `--complexity` and lets the Coordinator pick the mode), so the gate passes whether or not Physical Health or Mental Wellbeing still fire flags under the quick instruction.
Costs: Quick mode reaches about 93% of dispatches with `MUST_SURFACE` / `CLINICAL_CONCERN` / `MEDICATION_MISSED_CRITICAL` behaviour never exercised under it, while the record says the D6 gate passed — high.

5. [§1 #14 counter table `CESSATION_STREAK` row; §4 4b "Read Stage 3's landed counter (M17) first"; §5.3] [/Users/md-homefolder/Desktop/multi-model-mcp/archive/plans/instructions_to_code_stage3_hard_fail_plan_2026-11-23.md §1.7]
Wrong: The plan treats M17 as a slot Stage 3 fills, but Stage 3's plan says "moves to Stage 4, as one of #14's counters. Not built here."
Fails: 4b waits to adopt a landed counter that no stage builds, and the plan has no fields, source (`health.substances_logged.type`), wording constraint ("never N days clean") or closing-round edit for `physical_health.md` `CESSATION_SUPPORT`, all of which Stage 3 hands to it.
Costs: An in-scope miss (driver: 18 of 19) ships unbuilt with both plans recording it as the other's, or the builder improvises it without the absence-is-not-abstinence constraint — high.

6. [§1 M14 with DECISION 4-7(a); §1 #22 "4 s budget per read", "prefetch must never widen a grant"; DECISION 4-2(b)] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/caldav.py:read_calendar (:1066), update_calendar_event (:1498–1505, :1582–1588, :1606), _note_plan_write (:1610); /Users/md-homefolder/Desktop/multi-model-mcp/tools/data_objects.py:914]
Wrong: 4d turns `read_calendar` into a writer after 4a has made it run by code on every Logistics dispatch and, under 4-2(b), speculatively on every turn, and the plan never reconciles the two.
Fails: Each read with a FAILED event does up to two fetch, conflict-query and PUT cycles (15 s timeout each) inside a 4 s uncancellable prefetch thread; every re-check that fails again appends another "[Automated note…]" to the already-annotated description and calls `note_calendar_write()`; and the write fires for any caller of `read_calendar`, including the data-object reader, whatever its grants.
Costs: Unattended, repeated writes to the user's real calendar on turns unrelated to it, with event descriptions growing per read and prefetch timing out exactly when such events exist — medium.

## LOCAL

2. [§1 #6 "append it to each **blocking** specialist's directive", headline "to each blocking specialist", test 1 "every blocking directive carries them"] [/Users/md-homefolder/Desktop/multi-model-mcp/core/orchestrator.py:_dispatch_from_coordinator blocking loop (:7082–7112), _run_single_agent research branch (:5798–5805); /Users/md-homefolder/Desktop/multi-model-mcp/config/agents/coordinator.md:229–230]
Wrong: `PROACTIVE_FLAGS` and the Pattern Miner headline go to every blocking specialist, and the Research Agent is a blocking specialist that the Coordinator file calls "decontextualized and cloud-routable".
Fails: Personal signals drawn from logs and the pattern report are appended to a directive that runs on `run_session_gemini_grounded`, where the model turns its prompt into web searches.
Costs: Breaks the decontextualization requirement that every Section 0 amendment lists as unchanged, on an outbound path that cannot be recalled — high.

3. [§1 #22 "Every read goes through the registered handler…", wiring "records it as `context_sections["prefetch"]`"] [/Users/md-homefolder/Desktop/multi-model-mcp/core/orchestrator.py:_UNTRUSTED_READ_TOOLS (:6482), _file_wisdom_proposals (:6523–6529, :6559–6561), dispatch_tool → record_tool_call (:3005)]
Wrong: Prefetch puts `read_calendar` content in front of Logistics without a tool-call record, and the untrusted-read taint is derived only from tool-call records in the trace.
Fails: `read_untrusted` stays False on a turn whose specialist input contains invite text written by outsiders, so a `WISDOM_PROPOSAL` from that turn is filed with its claimed `stated` provenance instead of being forced to `observed`.
Costs: Text an outside sender put in a calendar invite can be filed at once as bare user fact rendered in every later prompt, bypassing the control added for 11-05 review finding 21 — high.

4. [§0 finding 6 "It then got the tools-off final round"; §1 #20 "covers a run that exhausts its rounds, because the tools-off final reply **is** the report text"; "The 8-round limit is left as it is"] [/Users/md-homefolder/Desktop/multi-model-mcp/core/orchestrator.py:_openai_compat_loop (:5257–5258), run_session_gemini (:3935), _CACHED_SPECIALISTS (:5661), _openai_compat_stream (:5625); /Users/md-homefolder/Desktop/multi-model-mcp/core/server.py:2181]
Wrong: The scheduled Pattern Miner runs the non-streaming `_openai_compat_loop`, which has no tools-off final round; that round exists only in the streaming and native loops.
Fails: On exhaustion the loop returns `messages[-1].get("content")`, the eighth tool call's raw result, so the code-written report parses a tool-result blob and stores it as `{"notes": …}` under today's date.
Costs: In the 12-of-12 measured failure case the Coordinator's "most recent Pattern Miner report" becomes a tool-result dump replacing the last real report, and the headline never appears — high.

7. [§1 #14 Timing "computed after the blocking specialists return, from a re-read of today's log", `FOOD_NOT_LOGGED` row, "a flag listed here stands even if no specialist raised it"; test 4; §6 live check 2] [/Users/md-homefolder/Desktop/multi-model-mcp/core/orchestrator.py:_dispatch_from_coordinator fire-and-forget start (:7133–7190); /Users/md-homefolder/Desktop/multi-model-mcp/tools/data_objects.py:632–634; /Users/md-homefolder/Desktop/multi-model-mcp/config/agents/diarist.md:48]
Wrong: `FOOD_NOT_LOGGED` reads only `health.food_logged` in the day log, while meals are mostly written by the Diarist to the `meals` data object and the Diarist does not start until the blocking specialists have returned.
Fails: The post-return re-read runs before the Diarist's same-turn write and never consults the meals log, so code raises a flag declared to stand regardless, on any Physical Health dispatch after the cut-off, including each evening close Stage 2 adds.
Costs: The user is told they have not mentioned eating on days their meals are recorded, the same-turn contradiction (review S3) the timing section claims to close — medium.

8. [§1 #12 Candidates / Exact resolution / Ambiguity; Risks; test 3] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/heard_names.py:_NOT_NAMES (:67–82, written for capitalised mid-sentence words only), :311]
Wrong: Candidates are "tokens and phrases" matched case-insensitively and sentence-initially against first, last and nicknames of 988 contacts, filtered only by a stoplist with no ordinary words that are also names.
Fails: Words like "will", "mark", "bill", "rose", or a shared surname, resolve to contacts, filling the three-record cap with strangers or emitting "matches N contacts — ask which" for a word that was never a name.
Costs: Relationships opens with wrong people's records and an instruction to ask a spurious disambiguation question, and test 3 passes only because no fixture contact is named "Tomorrow" — medium.

9. [§1 M4 "eventually raised or consciously dropped, instead of vanishing"; Mechanism "On write, carry `held_since` forward"; tests 1–4] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/context_tracker.py:write_context_tracker (:1526 `"held_items": held_items or []`); /Users/md-homefolder/Desktop/multi-model-mcp/core/orchestrator.py:persist_context_block (:2767)]
Wrong: The plan stamps and renders held items but keeps replace semantics, under which a `[CONTEXT]` block lacking the key writes an empty list.
Fails: Any Synthesizer turn that omits `held_items` (a partial-salvage block, a short reply) erases every item and its `held_since`, and no listed test covers an omitted key.
Costs: Held items still vanish silently, now after the closing round (C24) has told the Synthesizer code tracks how long each has been held — medium.

10. [§1 M13 "the builder must read `_deep_merge`'s list semantics"; tests 1–4] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/logger.py:_deep_merge (:187–198)]
Wrong: The append-versus-replace decision for the code-written `logistics` lists is left to the builder, although `_deep_merge` replaces lists wholesale.
Fails: Each Logistics run's code write of `events_scheduled` / `reminders_set` / `horizon_items` replaces the lists from earlier runs the same day and overwrites, or is overwritten by, the model's own restating write until the closing round; no test runs twice in one day.
Costs: The day's Logistics log keeps only the last run's actions, losing the action record M13 exists to make reliable — medium.
