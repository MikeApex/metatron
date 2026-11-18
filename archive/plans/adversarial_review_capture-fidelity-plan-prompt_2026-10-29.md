Plan reviewed: archive/handoffs/2026-10-29-capture-fidelity-plan-prompt.md (a planning prompt; no plan document existed yet)
Reviewer: adversarial-reviewer · model Fable · effort medium · 2026-10-29

## STRUCTURAL

1. [§ 1 over-save, § 3.1, § 4.4, § 4.7] [tools/day_shape.py:set_day_shape, tools/day_shape.py:SECTIONS]
Wrong: The plan opens as a "what it missed" presence check but its test requires catching the seven-day dinner, a wrong-value save, without ever naming which comparison the extraction is built for.
Fails: Presence-of-fact extraction and per-fact day-set/value extraction are different schemas, different comparisons and different lifecycles (a wrong save is never "cleared when saved"), so the design section, the training-record categories and the test are shaped by a decision the plan defers into § 4.4.
Costs: The extraction schema gets built for one comparison and the other is bolted on or silently dropped, with the costlier failure class (§ 3.1's own words: a wrong save does more harm) the one most likely dropped — medium.

2. [§ 4.7 live check, § 5.4, State on entry] [core/interview.py:11-13, core/server.py:1449 `interview_mode`]
Wrong: "One live check on the VM after deploy" assumes an account in interview mode exists at deploy time, but `state.json` exists only for approved account users (never `mike`), the trial accounts are gone, and Iva's interview ends in `complete`.
Fails: Decision 4 is presented as timing, yet it decides whether the interviewer-scope v1 has any live venue at all: before Iva's interview the first live exercise is her real first interview; after it, no live interview exists without provisioning a new approved account.
Costs: Either a new per-turn model path over a second user's words goes live untested on her one-shot interview, or v1 ships with no live check and the plan's own test clause is unmet — medium.

3. [§ 4.2, § 4.7 replay, State on entry "re-measure"] [scripts/accounts.py:305-308 `shutil.rmtree`, scripts/accounts.py:297-304 `DELETE FROM exchanges`, archive/log/2026-10-29-04-stage-5-closed-flags-formatting-location.md:12-13]
Wrong: The plan says real traces exist for the trial accounts on the VM and orders a replay of the trial_1029 turns and a post-deploy re-measure before sizing, but the trial accounts' data dirs and conversation rows were purged on 2026-10-29 and `mike` has never run in interview mode.
Fails: The only surviving record of the eight facts is three paraphrased phrases in this prompt, so the "measure before sizing" step has no interviewer-mode input until Iva's single interview, and the replay fixture is reconstructed from paraphrase rather than replayed.
Costs: v1 scope is sized from an anecdote the plan itself tells the session not to trust, and the one deterministic regression test is authored, not recovered — high.

5. [§ 1 slump "arguably a window", § 3.5, § 4.7] [tools/day_shape.py:FIELDS, config/agents/goals_interviewer.md:131]
Wrong: § 4.7 requires the replay to fail for all three misses including "crash out after lunch", while § 3.5 forbids pushing the agent to save a thing the user never meant as a standing fact and asks the plan to define what counts as a fact.
Fails: The test pre-decides the fact definition § 3.5 is supposed to produce, so either the definition is bent to make the test pass or the test is red by design.
Costs: The per-field fact definition — the thing that bounds false positives for every later agent — is set by a fixture rather than by the design step — medium.

## LOCAL

4. [§ 4.7 "fails on today's code", § 1 "an instruction alone did not hold"] [core/interview.py:run_turn, core/interview.py:HISTORY_CHAR_BUDGET, core/orchestrator.py:_task_hint_block]
Wrong: With every live meter stubbed, the replay can only show a miss block is emitted, not that the interviewer then saves — and the interviewer already holds the user's words in its full-transcript history, so the plan's premise that re-presenting them in a code block changes behaviour has no falsifiable criterion anywhere in the plan.
Fails: "Fails on today's code" passes the moment any block is produced, `_task_hint_block` is cited as the same shape without any efficacy figure, and the only behavioural check is the live run finding 2 shows may not exist.
Costs: A per-turn model call and its Run cost ship with no measure of whether a shown miss converts to a save, and the "training signal" counts misses the mechanism may not be reducing — medium.
