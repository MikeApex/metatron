# Fable 5.2 adversarial review — stage2 session shape plan (2026-11-23)

*Verbatim reviewer output; the driver's dispositions are in `instructions_to_code_plan_review_stop_2026-11-23.md`.*

## STRUCTURAL

1. [§1 M7 D-S2-4; §3 closing edits 2–3; §4 step 9; Budget "(M) item"] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/logger.py:29 `_NULL_ISH`, :60 `is_null_ish`; /Users/md-homefolder/Desktop/multi-model-mcp/config/agents/coordinator.md:143]
Wrong: M7 goes live on the claim that the null-ish and bracket filters remove template fills, while the only measurement of the fill rate is built last and run by Mike in the deploy walkthrough, after the closing Red round has already rewritten coordinator.md:52 and :143 to describe the hold.
Fails: `is_null_ish` is a whole-value match against a short set ("none", "n/a", "not applicable", …), so "No clarification needed" or "Not needed" on a clear turn is a real value and holds every specialist but two; and the "one revertable hunk" revert then leaves two committed Red edits describing a hold that no longer exists, with both permitted Red rounds spent.
Costs: ordinary user turns answer with a question and record nothing until someone notices, and undoing it needs a third Red round the ruling does not allow — medium.

2. [§1 M7 mechanism "Tell the Synthesizer", tests 1 and 4; §3 has no closing edit for synthesizer.md:273–274] [/Users/md-homefolder/Desktop/multi-model-mcp/config/agents/synthesizer.md:273–274; /Users/md-homefolder/Desktop/multi-model-mcp/config/modules/routing_cloud.yaml:81 synthesizer `allowed_tools`; /Users/md-homefolder/Desktop/multi-model-mcp/core/orchestrator.py `_dispatch_from_coordinator`]
Wrong: The hold is enforced only at `_dispatch_from_coordinator`; the Synthesizer keeps `run_subagent`, `write_profile`, `write_persona`, `open_task`, `update_task`, `write_wisdom`, `write_schedule` and `amend_data_object`, restrained by one sentence in the clarify note.
Fails: The Synthesizer's standing catch-up rules tell it that when no Logistics or domain-specialist output is in the package it must call `run_subagent` for that specialist "so the action is actually taken" and log a `ROUTING_MISS` — exactly the state the hold creates — and test 1 stubs `_run_single_agent` at dispatch, so it cannot see the re-dispatch.
Costs: the wrong contact or booking M7 exists to prevent is still written one hop later, and every held turn can file a false `ROUTING_MISS` through M11's new key into the stream #1 is cleaning — medium.

4. [§1 #10 "What a user notices", D-S2-3, §3 closing edits 9–11] [/Users/md-homefolder/Desktop/multi-model-mcp/core/orchestrator.py:4507 `_SYNTH_MAX_ROUNDS = 4`, :5125 `max_iterations=_SYNTH_MAX_ROUNDS` in `run_session_gemini_cached_stream`, :5021 `_final_reply_round`, :4522 `_FINAL_REPLY_PROMPT` (working-tree lines; HEAD about 15 lower)]
Wrong: The plan says nothing detects the chain condition and that a rounds limit cannot be made to fire, but the production Synthesizer path already stops at four model rounds and answers from what it has; the plan never mentions it (ROADMAP.md:817, dated 09-03, is stale on this).
Fails: The call counter is laid over an existing round cap, so the new behaviour is to refuse the fourth call inside one batched round that runs today, and `CHAIN_LIMIT_REACHED` is never written when the round cap is what ends the chain.
Costs: Mike is asked to rule calls-versus-rounds on a false description of today's behaviour, and three Red edits reword the Synthesizer's limit to a number that is not the binding one — high.

5. [§1 #2 part A directive "with your usual flags"; "Clinical rule: no flag is cleared"] [/Users/md-homefolder/Desktop/multi-model-mcp/core/orchestrator.py:6817–6860 `_drop_unprompted_clinical_flags`; /Users/md-homefolder/Desktop/multi-model-mcp/config/agents/synthesizer.md:36]
Wrong: The plan forces Mental Wellbeing into every scheduled brief and close with a directive to scan what is on file and report with its usual flags, then relies on a function that strips only the `FLAGS:` items and `MUST_SURFACE:` lines from that output.
Fails: Mental Wellbeing's narrative of a past disclosure reaches the Synthesizer twice a day with the flag lines removed, and the Synthesizer is instructed to trust its own reading of a clinical signal no specialist surfaced — the input shape of the trial_2026_10c incident the strip was written for, which until now arose only when the Coordinator chose to list that agent.
Costs: a past disclosure can be re-raised in every morning brief and day close for any user with clinical history on file, at the +$0.05/day the dispatch costs — speculative.

## LOCAL

3. [§1 #10 mechanism; §4 step 4 `_chain_limit_refusal`] [/Users/md-homefolder/Desktop/multi-model-mcp/config/agents/synthesizer.md:36, :272, :274; /Users/md-homefolder/Desktop/multi-model-mcp/core/orchestrator.py:4983–5015 parallel `run_subagent` workers]
Wrong: The fourth-call refusal counts every Synthesizer `run_subagent` alike, with no exemption for a follow-up to Mental Wellbeing or Physical Health.
Fails: The Synthesizer's clinical and health catch-up is a `run_subagent` call, batched calls run on parallel worker threads, and whichever increments the counter fourth is refused — so the refused call can be the one that would have raised `CLINICAL_CONCERN` or `MEDICATION_MISSED_CRITICAL`.
Costs: a clinical check is skipped on a user turn with nothing vetoing the skip, which the Stage 2 clinical rule forbids, and §6 schedules no A4 run to catch it — medium.

6. [§1 #4 mechanism and Risk "engagement re-stamps `added`"; test 3] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/context_tracker.py:414–418 `_merge_open_threads`, :1486–1489 `filtered_incoming`, :1473 `archived_keys`]
Wrong: The plan assumes oldest-by-`added` means least recently engaged, but an exact-text re-send keeps its stored date before engagement is even checked, and an archived thread is re-admitted only on a write where the user's words match it.
Fails: With six threads the cap can archive the one the user is discussing this turn, the next non-engaging write filters it out again because archive entries are never removed, and every capped entry joins a 50-entry list that blocks any new thread sharing two anchor tokens; test 3 checks only the engaging write.
Costs: live topics drop out of "what is still open" and cannot stay back, on an archive measured as empty in practice until this cap starts filling it — medium.

7. [§1 M7 "Capture fidelity", test 6; §4 step 6 stop condition] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/capture.py:1394–1400 `defer`, :1377–1389 `after_synthesizer`; /Users/md-homefolder/Desktop/multi-model-mcp/core/orchestrator.py:7946 and :7968 (streaming :8239, :8431)]
Wrong: `defer` is specified "exactly as the sign-off skip does", but that path never runs the Synthesizer, and `defer` returns at once when the turn is shadow, which is the live mode for ordinary turns.
Fails: On a held turn the Synthesizer still runs, `after_synthesizer` still resolves the turn's candidates against a trace the hold has emptied of writes, and test 6 asserts only that `defer` was called.
Costs: held turns are scored as capture misses in the measurement D13 is waiting on, or the builder's stop condition fires and M7 leaves the stage — medium.

8. [§1 M6 mechanism "leave … `clinical_threads` … exactly as on disk", schema bullet] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/context_tracker.py:1440–1445, :1277–1283 `raise_escalation`, :1642–1652 `clinical_threads` property; /Users/md-homefolder/Desktop/multi-model-mcp/core/orchestrator.py:1640 handler map (HEAD about :1627)]
Wrong: Remapping the tool to `merge_pattern_findings` removes the tool path's add-only merge of `clinical_threads` and its tier-2 escalation, while the schema keeps the property whose description invites that write.
Fails: Any agent sending `clinical_threads` through the tool on a user turn — Pattern Miner or a warn-mode stray — gets a success-shaped result and the thread and escalation are never recorded.
Costs: one code path that could open a clinical thread is closed by a data-loss fix whose test 1 asserts the field is "unchanged" as the pass condition — speculative.

9. [§1 #2 Risk, second bullet] [/Users/md-homefolder/Desktop/multi-model-mcp/core/orchestrator.py:5668 `_run_single_agent`; /Users/md-homefolder/Desktop/multi-model-mcp/tests/test_consent_enforcement.py:24, :45]
Wrong: The plan says an added dispatch passes through `_run_single_agent`'s existing consent gate, but no consent check exists anywhere in core/orchestrator.py or core/router.py (the string appears only in core/consent.py, server.py, connections.py and accounts.py).
Fails: The builder is told to confirm the gate with a test file that never exercises `_dispatch_from_coordinator`, so the confirmation passes without touching the code-added Mental Wellbeing and Physical Health calls.
Costs: the forced health dispatch for a second user rests on whatever the server door enforces, unverified by this stage — medium.
