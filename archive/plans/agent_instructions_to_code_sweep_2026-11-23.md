# Agent instructions → code: the sweep `[DB-0810-11]` strand (c) never got — 2026-11-23

*Read-only survey (Opus 5.5, high). Nothing was edited, built, deployed or filed. Scope: all 24
`config/agents/*.md` plus the three injected `config/modules/synthesizer_*.md`, each read in full
against the code that loads it (`core/orchestrator.py` `_run_single_agent` / `_dispatch_from_coordinator`)
and its grant in `config/modules/routing_cloud.yaml` (`routing.yaml` is in parity: same 24 grant
counts). Method: the four bins and the silent/loud sort from the handoff
(`archive/handoffs/2026-11-23-agent-instructions-to-code-sweep-prompt.md`), which come from rounds
four and five of `code_dominant_rebuild_notes.md`.*

**Limits on the evidence, stated once.** `scripts/vm_read.py` exposes persona data, not traces, so
no turn-level measurement was possible: every turn count below is the **August** figure from
`[DB-0808-09]` (Aug 20–27), now three months old. Observed evidence comes from the quality events
synced into `DEV_BACKLOG.md § Machine log` (counted 2026-11-23). "Verified in code" means the
mechanism was read and proven, with no observed incident. "Unevidenced" means neither.

---

## 1. Lead — for Mike

**What a user would notice getting better, if the moves here were built:**

1. **The morning brief and evening close actually consider how you are.** Your instructions say
   both sessions always consult Mental Wellbeing and Physical Health. The Coordinator has logged
   itself missing that 14 times. Code knows which session it is and can just send them.
2. **Things you say reach the diary whether or not the Coordinator remembers to send them.** A
   cardiac event in a batched message, an evening's dinner and a film title were all missed
   because the Diarist wasn't listed for that turn.
3. **Advice from work and money stops using goals you have dropped.** Both agents are told to
   re-read the raw goals file, which brings back the declined and parked goals the prompts have
   hidden since 11-21.
4. **A missed critical medication, a sleep run, a budget overspend or a lapsed practice is caught
   by a count, not a model's memory.** These are threshold rules over data the agents write
   themselves ("under 6 h two nights running", "required and not logged today"), and today a
   model works them out afresh each turn.
5. **Replies get faster.** Specialists spend most of their turns on reads that are the same every
   time (their own settings, today's tasks, the people named). Handing those reads over up front
   removes one or two model round-trips from the slowest specialist on most turns. That bears
   directly on the minute-long replies in `[DB-1029-09]`. In money it saves pennies.
6. **Your development backlog stops filling with false complaints.** About 170 of the 544
   "you corrected me" / "I missed a signal" events in the machine log are about scheduled turns
   where you said nothing. They also count towards Build's three-strikes repair trigger.

**How many, and where.** **25 findings to move** (bins A–C), plus **6 places where two files
contradict each other** (§ 2b), which go to One Home Per Rule Class rather than to code. They
cluster in four places:

- **Session shape:** the Coordinator and Synthesizer are asked to decide what code already
  knows: which session this is, whether the user spoke, how many rounds have run.
- **Specialist openings and counters:** Logistics, Relationships, Work & Vocation, Physical Health
  and Learning & Growth.
- **The two hard-fail domains:** Physical Health medication and Finance arithmetic.
- **Flag protocols with no reader, or two readers.**

The **judges are clean**, as expected: `task_judge`, `accountability_judge`, `day_planner`,
`project_planner`, `capture_extractor`, `crm_sweep` and the two data-object agents are already
gate-shaped, and code validates what they return. Only `tone_profiler` has a small finding. The
**day-plan module has already had the move**: asked-once, explained-once and slip tracking are
all in `tools/day_plan.py`.

**One finding is a bug rather than a move:** declined goals coming back through `read_goals`
(#5). It is small enough for `/fix` now, ahead of any cluster.

---

## 2. Ranked findings

Silent first, then by evidence (observed → verified in code → precedent → unevidenced), then by
size of win. **Bins:** A code does it exactly · B stop passing it · C parse the flag. **Tier** per
`.claude/settings.json`: Red = an agent file, a routing file or `core/{router,persona,scheduler,spend_guard}.py`.
Almost every move ends with a Red agent-file edit (removing the instruction code now carries), so
"Red" is stated only where the *mechanism* is Red.

| # | What the user sees | Bin | Where | Evidence | Move shape | Tier | Cost / saving |
|---|---|---|---|---|---|---|---|
| 1 | Dev backlog fills with "user corrected me" events from turns where the user said nothing; they feed Build's ×3 repair trigger | A | [coordinator.md:44](config/agents/coordinator.md#L44), [tools/logger.py:478](tools/logger.py#L478) | **Observed:** ~170 of 544 correction/miss events concern scheduled turns (e.g. "User message was a scheduled quiet check-in…" ×10, ×5, ×5, ×4) | Trigger: `has_real_user_turn()` false. Refuse `USER_CORRECTION` / `INSTRUCTION_CHANGE_REQUEST` in `write_quality_event` and `_handle_user_correction`. Keep `ROUTING_MISS` (some scheduled misses are real, see #2). No safety veto needed. Exit: refused event, log line | Amber | Run: 0. Removes ~⅓ of machine-log volume |
| 2 | Morning brief and evening close never hear from Mental Wellbeing or Physical Health | A | [coordinator.md:174](config/agents/coordinator.md#L174); also `scheduler.yaml` evening_close comment | **Observed:** 14 self-reported misses ("…as mandated by the cross-domain routing rule for morning briefs" ×7, ×3…) | Trigger: `session_kind()` ∈ {morning_brief, evening_close}. Code appends both to `SPECIALISTS_TO_CALL` if absent. The Synthesizer's selectivity still decides what is said. Delete the line | Amber | Run: ≤ 2 sessions × 2 specialists on 3.8 Flash ≈ **$0.05/day/user** (≈ $1.50/mo), doubling 2027-01-01. Decision D4 |
| 3 | Something the user said is never journalled because the Coordinator didn't list the Diarist | A | [coordinator.md:196](config/agents/coordinator.md#L196) ("called in almost every exchange") | **Observed:** 4 signatures (cardiac event in a batched message, day-close dinner, a film title, a status update) | Trigger: every real user turn. Code adds the Diarist, fire-and-forget, if absent, the same way `_dispatch_from_coordinator` already adds it for a log entry. The Diarist's `NOTHING_LOGGED` is the cheap exit | Amber | Run: one Flash-Lite Diarist call on turns currently missed, ≈ $0.002–0.005 each. Silent loss of health records stops |
| 4 | Open threads vanish for a turn when the Synthesizer's context JSON breaks, and the tracker grows past its stated 5-per-category | A | [synthesizer.md:251](config/agents/synthesizer.md#L251), [:261](config/agents/synthesizer.md#L261) | **Observed:** "[CONTEXT] block dropped — no repair succeeded" ×3. **Verified:** `write_context_tracker` enforces no cap | Cap at 5 per key in `persist_context_block` (exact). Separately: move the block to a function call so the API validates the JSON. Gemini tool-call args are schema-checked; whether that combines cleanly with the cached-stream path is **unverified** | Amber | Run: 0. Ancillary: a tool-call block may cost one output round on the Synthesizer, so measure before switching |
| 5 | Work & Vocation and Finance advise against goals the user has declined or parked | B | [work_vocation.md:112](config/agents/work_vocation.md#L112), [finance.md:223](config/agents/finance.md#L223), [tools/goals.py:32](tools/goals.py#L32) | **Verified in code:** `read_goals` returns the raw file; the prompt already carries the filtered `prompt_view` (`_goals_section`, R6, 11-21) | Stop passing it twice. Make `read_goals` return `prompt_view` for every caller except `goals_interviewer`, and drop the "also call `read_goals`" lines (the goals are already in the prompt) | Amber + Red lines | Run: −1 turn on each call that used it. **`/fix`-sized** |
| 6 | Eight "mandatory" proactive scans run on Pattern Miner signals and `PROACTIVE_FLAGS` the specialists never receive | B (inverse) | [mental_wellbeing.md:80](config/agents/mental_wellbeing.md#L80), [physical_health.md:44](config/agents/physical_health.md#L44), [work_vocation.md:80](config/agents/work_vocation.md#L80), [finance.md:70](config/agents/finance.md#L70), [learning_growth.md:50](config/agents/learning_growth.md#L50), [recreation_hobbies.md:51](config/agents/recreation_hobbies.md#L51), [relationships.md:54](config/agents/relationships.md#L54); [coordinator.md:22](config/agents/coordinator.md#L22)–26; [work_vocation.md:63](config/agents/work_vocation.md#L63)–70 | **Verified in code** (11-05 review #32, Low, unfixed; re-read today: dispatch appends only knowledge and data-object blocks). W&V's flow cross-check needs MW/PH outputs it never sees, because all three run in parallel | Either hand the specialists the Coordinator's `PROACTIVE_FLAGS` and the PM headline in the directive (code), or rewrite the scans to what they actually get. Correct the Coordinator's claim that it holds the Prime Directive and Mission | Amber | Run: +~300 tokens per specialist call if passed. Stops the "patterns from nothing" turns |
| 7 | Logistics pays a model round-trip per horizon finding, for a channel code already covers | A | [logistics.md:80](config/agents/logistics.md#L80)–102, [:299](config/agents/logistics.md#L299) | **Verified in code:** `_file_horizon_items` ([orchestrator.py:6534](core/orchestrator.py#L6534)) files every `HORIZON_ITEMS` block. The file's "a finding in the block that you never filed will not reach anyone" is false. Specialists never batch calls (392/392 single-call turns, Aug) | Keep one channel. Decision D5 | Red lines (+ Amber if the tool is dropped) | Run: −1 Flash-Lite turn per finding (≈ $0.002 and ~1–2 s each) |
| 8 | A missed critical medication is only flagged if a model works out "required and not logged today" | A | [physical_health.md:47](config/agents/physical_health.md#L47), [:109](config/agents/physical_health.md#L109), [:134](config/agents/physical_health.md#L134) | **Verified in code:** `context_tracker` reads `medication_profile` for *ranking* but nothing computes the miss. **Precedent:** the flag was structurally unfireable until 08-04 (ROADMAP § A, "a safety flag never exercised by a test is not known to work"). A4 testing suspended | Trigger: every Physical Health dispatch. Code computes `required` − `taken today` from the profile and today's log, and hands the result in as evidence. The model may add a flag but never clear a computed one. Needs a per-medication `due_by` or a cut-off, or a morning brief flags an evening dose | Amber + Red line. **Hard-fail domain**: through `tests/run_a4_safety.py` | Run: 0; −1 read turn. Whether `mike` has a profile is unverified (the read door probes the Coordinator's store only) |
| 9 | Eight specialists' quick-mode sections never trigger; in Logistics the dead text contradicts the horizon rule | A | [logistics.md:14](config/agents/logistics.md#L14) and the same section in 7 files | **Verified in code** (review #25, Low, unfixed): `mode` is taken out of the JSON as the model-tier hint and never reaches the directive text | Either code prefixes `mode: quick` to the directive when the spec says so, with Logistics' horizon filing carved out, or the sections are deleted. Decision D6 | Amber + Red | If wired: the cheapest turn-saver in the set (skips proactive scans on routine turns) |
| 10 | The Synthesizer can chain specialists past its 3-round limit unnoticed; `CHAIN_LIMIT_REACHED` has no reader | A | [synthesizer.md:147](config/agents/synthesizer.md#L147), [:382](config/agents/synthesizer.md#L382) | **Verified**, already tracked: ROADMAP B4, `[DB-0804-02]` ("a build, not wording") | Count `run_subagent` calls per request in code; refuse the 4th with a fixed result the Synthesizer must answer from | Amber | Run: caps the worst-case turn. Cross-reference only; not re-derived here |
| 11 | A concert or plan Recreation spots can be told twice, or lost, because it travels as prose | C | [recreation_hobbies.md:240](config/agents/recreation_hobbies.md#L240) | **Precedent:** the 09-02 Death Cab item lost from specialist prose, which is why `_file_horizon_items` exists. That function already parses *any* specialist's block | Instruct Recreation to emit `HORIZON_ITEMS` (with precursor fields) instead of `follow_up` + `CONSULT_NEEDED: logistics`. No code change | Red line only | Run: 0. Raise-once then covers Recreation's finds |
| 12 | The same person ends up as two or three contacts, because each name is looked up by a separate model call | A | [relationships.md:211](config/agents/relationships.md#L211) | **Precedent:** the Jonas quadruplication, Eva/Iba ×4 (notebook round 3, point 4). `tools/heard_names.py` already matches message names to contacts for the Name note | Trigger: a Relationships dispatch. Code resolves names that match contacts *exactly* (name, nickname, `referred_to_as`) and hands over their records and `list_contacts(overdue_only)`. Near-matches stay the model's, with `write_contact`'s existing evidence. The `Jon`/`Jonathan` prefix signal parked in `[DB-0810-11]` lands here | Amber | Run: −1 to −2 turns on the slowest specialist (4.2 turns/call, Aug) |
| 13 | "On budget" and "overspent" come from a model summing transactions it re-read | A | [finance.md:91](config/agents/finance.md#L91), [:118](config/agents/finance.md#L118)–120, [:132](config/agents/finance.md#L132), [:144](config/agents/finance.md#L144) | Unevidenced: no Finance arithmetic test has run since A4 was suspended. **Named hard-fail domain** | Code computes period totals per category against `budget_structure` from the logs, and the `NEW_HABIT_EXPENSE` first-seen date where categories match. Model interprets | Amber + Red. **Hard-fail**: through the A4 path | Run: 0; −1 read turn |
| 14 | Sleep, energy, exercise and food alerts depend on a model counting nights and days | A | [physical_health.md:101](config/agents/physical_health.md#L101)–108; same shape in [mental_wellbeing.md:153](config/agents/mental_wellbeing.md#L153)–154, [learning_growth.md:102](config/agents/learning_growth.md#L102), [:108](config/agents/learning_growth.md#L108), [recreation_hobbies.md:169](config/agents/recreation_hobbies.md#L169) | Unevidenced as ignored. The 08-21 sleep over-weighting rewrite shows the thresholds matter | Code computes the stated thresholds (`SLEEP_POOR`, `SLEEP_ACUTE`, `SLEEP_MISSING`, `EXERCISE_GAP`, `ENERGY_CRASH`, `FOOD_NOT_LOGGED` after a cut-off hour, `PRACTICE_LAPSE`, `LEISURE_GAP`, `LEARNING_GAP`) from the agent's own log fields over the last 14 days and hands them in as evidence. `SYMPTOM_RECURRENCE` stays judgement. `EXERCISE_GAP`'s "if a goal" condition becomes config | Amber + Red | Run: 0; −1 `read_log` turn per call |
| 15 | Skill-practice streaks are kept by hand, in two stores, as text like `"last_practiced": "today"` | A + One Home | [learning_growth.md:72](config/agents/learning_growth.md#L72), [:153](config/agents/learning_growth.md#L153), [:169](config/agents/learning_growth.md#L169) | Unevidenced. A relative date in a stored record is the exact class `tools/record_rules.py` exists to stop | Skill practice becomes task-ledger `habit` rows (`every`/`times`/`on_days`), which already compute streaks, gaps and made-up days. Drop the streak fields from `write_log` | Red file only | Run: 0 |
| 16 | A message can go to someone who is the subject of a surprise or confidence on file | A (lookup) + D | [relationships.md:107](config/agents/relationships.md#L107)–112 | Unevidenced, **high stakes, silent by definition** ("the failure case is precisely the one nobody thought to flag") | At `send_email` / `send_calendar_invite`, code searches memory, journal, tasks and wisdom for the recipient's name and attaches the hits to the pending step and the approval card. The judgement of whether the draft leaks stays the model's | Amber | Run: one local FAISS search per send; no model tokens |
| 17 | Research queries carry whatever personal detail the head layer forgot to strip, into a grounded web search | A (partial) | [coordinator.md:235](config/agents/coordinator.md#L235), [synthesizer.md:120](config/agents/synthesizer.md#L120), [research_agent.md:16](config/agents/research_agent.md#L16) | Unevidenced. **Already planned**: ROADMAP § 0 item 5, "by code at B2 and E1". No scrub exists in code today | Before any `research_agent` dispatch, code removes exact known identifiers (user's names, contact names, profile address/postcode, employer). Residual decontextualisation stays judgement | Amber | Run: 0. Cross-reference to B2/E1 |
| 18 | A suicide disclosure in the Goals Interview depends on the interviewer alone; no test exercises it | D + test | [goals_interviewer.md:25](config/agents/goals_interviewer.md#L25) | Verified: the interview path (`core/interview.py`) never dispatches Mental Wellbeing and has no clinical veto. Unevidenced as failing | Judgement stays. The gap is the test. Decision D8 | Green (test) | Build: one scripted scenario in the A4 runner |
| 19 | Specialists' requests for a consult, research or a profile question are buried in prose, and several profile questions can reach one turn against "one per session" | C | `CONSULT_NEEDED` in 10 files (e.g. [logistics.md:234](config/agents/logistics.md#L234)); `RESEARCH_NEEDED` in 8; `PROFILE_GAP` in 8 (e.g. [logistics.md:34](config/agents/logistics.md#L34)) | Unevidenced. Review #30 disproved "dead trail" (the Synthesizer reads prose). The residual is that it has to *notice* an unnamed token | Code lifts these lines out of each output into one `FROM THE SPECIALISTS` block at the head of the package, keeping at most one `PROFILE_GAP` per turn. No automatic dispatch (see #10, #17). Decision D7 | Amber | Run: 0 |
| 20 | Pattern Miner's weekly run spends a model turn on each of seven fixed steps | A + B | [pattern_miner.md:97](config/agents/pattern_miner.md#L97)–109, [:54](config/agents/pattern_miner.md#L54)–61, [:120](config/agents/pattern_miner.md#L120) | Unevidenced (weekly, so small) | Code runs steps 1, 2, 3b and 4's duplicate grouping and hands over the results with the data span (which picks the baseline row). Pre-2026-08-09 free-text bands are not passed. Code writes the report and tracker from the output | Amber | Run: several 3.8 Flash turns per week, each re-sending log windows |
| 21 | A one-off pet name, or a third party's name, can end up in the tone profile that shapes drafts | A | [tone_profiler.md:50](config/agents/tone_profiler.md#L50)–53, [:75](config/agents/tone_profiler.md#L75)–77, [:91](config/agents/tone_profiler.md#L91)–95 | Unevidenced | Post-validate against the sample: drop a `pet_names` / `shared_phrases` value with fewer than 5 literal occurrences, any other contact's name, and any name in `names_they_use_for_user` absent from `[them]` lines | Amber | Run: 0 |
| 22 | Replies are slow because every specialist opens with the same reads | A | [logistics.md:176](config/agents/logistics.md#L176), [relationships.md:203](config/agents/relationships.md#L203), [work_vocation.md:108](config/agents/work_vocation.md#L108), [recreation_hobbies.md:116](config/agents/recreation_hobbies.md#L116), [physical_health.md:134](config/agents/physical_health.md#L134), [mental_wellbeing.md:245](config/agents/mental_wellbeing.md#L245) | **Measured (Aug):** 2.6–4.2 turns/call; first turns are predictable reads; 0 of 392 turns batched. Latency is a Now item (`[DB-1029-09]`, median 54 s) | `[DB-0808-09]` option 2. Per agent, a fixed prefetch list (own `read_agent_config`, `list_tasks` for Logistics, intake-queue count, today's/tomorrow's calendar for Logistics), appended to the **user message** so the cached system prefix is untouched. Delete the "call at session start" lines. **Re-measure first:** the August traces are stale | Amber + Red lines | **Not silent: latency.** −1 to −2 turns on the slowest specialist ≈ 2–4 s per reply. Money: pennies (Flash-Lite turn ≈ $0.002). Ancillary: +1–3k uncached input per call ≈ $0.0006 |
| 23 | Finance checks the task list before opening a task, which the ledger already refuses to duplicate | B | [finance.md:79](config/agents/finance.md#L79) | Verified: the ledger refuses a re-file | Drop the pre-check line | Red line | −1 turn when it fires |
| 24 | The Synthesizer is told to ask Research for an `intensive` tier that code doesn't have | dead | [synthesizer.md:123](config/agents/synthesizer.md#L123), [research_agent.md:74](config/agents/research_agent.md#L74)–78 | Verified: complexity is only `quick`/`deep` ([orchestrator.py:6957](core/orchestrator.py#L6957)) | Build the tier or drop the word | Red lines | 0 |
| 25 | A venue suggested for later can be one that is closed then | B | [logistics.md:302](config/agents/logistics.md#L302), [recreation_hobbies.md:245](config/agents/recreation_hobbies.md#L245) | Unevidenced; **loud** (the user finds out at the door) | When `at` is passed, `find_places` omits results with `open_at_time: false` | Amber | 0 |

### 2b. One Home Per Rule Class: contradictions, not moves

1. **The morning brief has two openings.** [synthesizer_scheduled_sessions.md:31](config/modules/synthesizer_scheduled_sessions.md#L31)
   says "How are you feeling this morning?" first; [:7](config/modules/synthesizer_scheduled_sessions.md#L7)
   and the template prompt say open on the one time-sensitive thing. This is review #28 (Low, unfixed).
   **Observed:** "User corrected opening prompt style from abstract/long-form to time-sensitive specific."
2. **Task lengths: ask, or estimate?** [synthesizer.md:395](config/agents/synthesizer.md#L395) and
   [synthesizer_day_plan.md:36](config/modules/synthesizer_day_plan.md#L36) say ask once. Mike said
   ×3 "give me an estimate to approve, don't ask"; the 10-30 log recorded the opposite irritation
   ("I have estimated 30 minutes… let me know" ×6). The rule now lives in the persona, two agent
   texts and `day_plan.md:11`. By "Mike's input is design by default" it belongs in one agent home.
3. **The research decontextualisation rule has two homes**: [coordinator.md:235](config/agents/coordinator.md#L235)
   and [synthesizer.md:117](config/agents/synthesizer.md#L117)–124. One copy belongs with #17.
4. **New goals.** Six specialists are told to "ask two or three questions; never plan on the first
   turn" (e.g. [relationships.md:299](config/agents/relationships.md#L299)). The Synthesizer is told
   that for an M goal it asks none of them ([synthesizer.md:182](config/agents/synthesizer.md#L182)–186).
   For the common case, the questions are generated in order to be discarded.
5. **Recreation is told to output only one JSON object** ([recreation_hobbies.md:138](config/agents/recreation_hobbies.md#L138))
   and also to end with a `WISDOM_PROPOSAL` line (:246).
6. **Finance says "All financial data stays local. No cloud routing"** ([finance.md:28](config/agents/finance.md#L28)).
   That is false under the VM amendment, and it narrates routing to a model.

**Still true, unchanged, and not moves** (the 11-05 Lows wait for the next review by Mike's plan;
listed so nobody re-derives them): `run_model_conference` is still granted and instructed and still
fails every call (#24); the pollen tool is still granted but filed under "Not yet built" (#26);
Finance § Scheduler behavior ([finance.md:103](config/agents/finance.md#L103)–111) describes a
cadence no job runs; Pattern Miner says the Diarist surfaces its findings
([pattern_miner.md:16](config/agents/pattern_miner.md#L16), :84), but the Diarist never speaks;
`time_director.md` is retired but `"time"` still maps to it in `_AGENT_NAME_MAP`.

---

## 3. Per-file notes

**Logistics** (41 KB, 3.6 turns/call). The heaviest A file. Its openings (#22) and its horizon
double channel (#7) are the turn costs; the quick-mode contradiction (#9) is the correctness one.
Calendar conflict checks, ledger due-ness and the raised-once horizon record are already code, and
the file says so accurately. Execution trees, ordering and dependency judgement, and coordination
opportunities stay D.

**Relationships** (36 KB, 4.2 turns/call, the slowest). Per-name lookups and the overdue scan are
#12. The disclosure check's *lookup* is #16. Merge, invite and approval honesty are already code
(the pending-confirmation store and the ACTIONS line). Disclosure judgement, register, tone and
reciprocity reading stay D. `import_contacts_file` is granted and never named.

**Coordinator** (29 KB). #1, #2 and #3 are session shape it is asked to judge but code knows. Its
Prime Directive and Mission claim is stale (#6). Writing the `USER_CORRECTION` line *and* calling
the tool is redundant, because code writes the event from the line; harmless at 1.0 turns/call.
"Always dispatch Diarist fire-and-forget" is already enforced in code and can go. Intent
resolution, clarification, implicit-correction detection and routing stay D.

**Synthesizer** (54 KB, back from 41.9 KB on 08-27). #4, #10 and #24, plus three contradictions in
§ 2b. The ACTIONS line, the scheduled-run focus block, conditional module injection and the
clinical-thread lifecycle are already the move done well. "Raise a thing once" is now carried for
tasks (held to a count), horizon items and day-plan items. The prose rule is the residue for
everything else and needs no code. The growth since 08-27 is mostly the tasks/goals/logs tool
prose (`:395`–`:405`). That is token weight rather than a move to code, so it belongs to a
separate slimming pass that watches the 4,096-token cache floor. Direction, tone, holding and
trade-offs stay D.

**`synthesizer_scheduled_sessions.md`.** The opening contradiction (§ 2b.1). "Missed evening
ritual" (`:36`) is computable (ritual in effect, yesterday's entry absent), but the ritual is
paused for `mike` until 2027-01-26, so it is not worth building now.

**`synthesizer_day_plan.md`.** Already moved: asked-once, explained-once, slip and length-ask
tracking are in `tools/day_plan.py`. Nothing to add.

**`synthesizer_onboarding.md`.** "Track what's been covered so you don't repeat" (`:15`) relies on
model memory. Low value until a second user onboards. `BASELINE_INCOMPLETE` is judged by each
specialist and is the trigger that injects this module. Code could compute "baseline empty" from
the agent's config store; low priority until a second user onboards.

**Mental Wellbeing.** #6 and #14 (`PRACTICE_LAPSE`, `SLEEP_CONCERN`). Clinical detection stays D
and must: code may hand it duration evidence ("low mood logged on 9 of the last 14 days") but
never decide the flag. The "flag → `write_journal`" coupling is partly in code already
(`clinical_threads` requires the user's words). The Big Five "fewest data points" pick is
computable and trivial.

**Physical Health.** The densest A file: #8 and #14. Stating the flags as exact thresholds was the
right call; it is what makes them code-able.

**Work & Vocation** (3.7 turns/call). #5 (the bug) and #6 (the flow cross-check it cannot do).
Everything else is D.

**Finance.** #5, #13 and #23, and a dead § Scheduler behavior. A named hard-fail domain, so #13
goes through the A4 path.

**Learning & Growth.** #14 and #15. A typo at `:76` ("before?intellectual").

**Recreation & Hobbies.** #11 and #25, and the JSON contradiction (§ 2b.5).

**Diarist.** Its dispatch is #3. Its `CAPTURED:` output (`:54`–66) is composed for a reader that
doesn't exist (fire-and-forget output is never read); a trivial token saving. `write_archive`
dedup, listed as untouched in `[DB-0810-11]`, **has been built** (`tools/diarist.py:324`).

**Research Agent.** #17 and #24; pollen still unchanged (#26).

**Pattern Miner.** #20.

**Goals Interviewer and `goals_interview_reference`.** Interviewing is D. #18 is a missing test,
not a move.

**`tone_profiler`.** #21.

**Nothing to move:** `task_judge`, `accountability_judge`, `day_planner`, `project_planner`,
`capture_extractor`, `crm_sweep`, `data_object_matcher`, `data_object_tagger` (gate-shaped; code
validates their output) · `intake_extractor` (parked permanently) · `time_director` (retired).

---

## 4. Build clusters

Each cluster ends with Red agent-file edits that delete the instruction code now carries. Per the
standing rule, Red work is not delegated to a subagent, so every cluster's build session does its
own Red edits with Mike approving the prompts.

**C1 — Code decides the session's shape** (#1, #2, #3, #4 cap, #10). Small, best evidenced, all
in `core/orchestrator.py` and `tools/logger.py`, plus three Coordinator/Synthesizer line deletions.
Do it first: it removes the noise that feeds Build's repair trigger.
*Budget:* plan ~40k · build ~120k · review ~50k (~210k). *Model:* build Opus 5.5; review Fable 5.1.
*Deploy:* yes. *Run:* +≈ $0.05/day/user for #2 (D4); otherwise 0.

**C2 — Hand the specialist its evidence** (#22, #12, #14, #15, #6, #9, #20). The latency cluster,
and `[DB-0808-09]` option 2 made concrete. It should coordinate with the reply-latency build
(`[DB-1029-09]`), whose plan does not cover specialist prefetch. **Step 0 is a fresh trace
measurement** of first-turn tool sequences on the VM, since `[DB-0808-09]`'s own rule is
"diagnose from traces before building" and the August data is three months old.
*Budget:* measure ~40k · plan ~80k · build ~250k · review ~80k (~450k). *Model:* build Opus 5.5;
review Fable 5.1. *Deploy:* yes. *Run:* saves 1–2 turns on most specialist calls (seconds per
reply, pennies per day); adds ≈ $0.0006 of uncached input per call. *Unseen:* none; no state
persists.

**C3 — The two hard-fail domains** (#8, #13, and the #18 test). Code computes the medication miss
and the budget arithmetic; the A4 runner gains fixtures for both, plus the interviewer safety
scenario. **Must go through `tests/run_a4_safety.py`**, which is the designated path. A live gate run
cost ~$3–4 the last time one was run (08-27); that figure is stated before running, as Mike
required then.
*Budget:* plan ~60k · build ~150k · review ~60k (~270k) + one live gate run (~$3–4). *Model:*
Opus 5.5 high for build; Fable 5.1 review. *Deploy:* yes.

**C4 — One channel per signal** (#5 as `/fix` now, #7, #11, #16, #17, #19, #21, #23, #24, #25, and
the § 2b edits). Mostly small and independent. #16 and #17 are the privacy-relevant pair and
could split off if C4 runs long.
*Budget:* plan ~60k · build ~150k · review ~60k (~270k). *Model:* Opus 5.5; Fable 5.1 review.
*Deploy:* yes. *Run:* 0 (#16 adds one local search per send).

---

## 5. Decisions for Mike

**D1 — What happens to "where should code replace model judgment" `[DB-0810-11]`.**
*Options:* (a) close it into this document; (b) keep it open as the standing protocol.
*Trade-off:* an open item with no exit is the failure "backlog items must exit" names. But strand
(c) *is* a protocol, and a protocol needs a home that fires.
*Recommendation:* (a). Close it here, and make the protocol a standing **lens of the next
codebase review**: the four bins and the silent/loud sort as one reviewer area. The item's two
parked residues get homes: `temperature` not plumbed through the providers goes to C3 (its named
beneficiaries are clinical flags and Finance arithmetic), and the nickname-prefix signal goes to
#12 in C2. The `write_archive` dedup strand is already built.

**D2 — The rebuild notebook** (`code_dominant_rebuild_notes.md`).
*Options:* (a) retire it into this document with one closing round; (b) keep appending.
*Trade-off:* its retirement condition ("when the rebuild is commissioned") can no longer fire, so
under the single-bin rule it is a standing second file. Its rounds 4–5 template is now this
document's method.
*Recommendation:* (a). Add a final dated round pointing here and mark it closed. Future
architecture readings for Mark 1 go in the next sweep's document.

**D3 — The founding principle.** `CLAUDE.md` says "Config files are the product; code is
infrastructure", and `.claude/rules/orchestrator.md` says "if a behaviour change requires a code
change, that is a design failure". Every move here shifts behaviour from config into code, and
the notebook says that principle "must be amended explicitly, never drifted past".
*Options:* (a) amend it now to what Mark 1 actually does, roughly *"config owns judgement and
policy; code owns procedure, evidence and anything a rule can decide exactly"*; (b) leave it and
treat each move as a justified exception.
*Trade-off:* (b) is how drift happens: twenty justified exceptions and a principle nobody follows.
(a) is a `CLAUDE.md` edit that changes a Key Design Decision, so it is Mike's to make.
*Recommendation:* (a), before C1 lands.

**D4 — The whole-person rule for the morning brief and evening close.**
*Options:* (a) enforce it in code (#2); (b) delete it, since the now/next brief (10-30) may not
want a health scan.
*Trade-off:* (a) costs ≈ $1.50/user/month (doubling in January) and adds two specialist outputs
to a brief that is meant to be short. The Synthesizer's selectivity is what keeps that short.
(b) is free, but drops a rule written in three places that nobody has withdrawn.
*Recommendation:* (a) for both. The rule has not been withdrawn, and its misses are the
best-evidenced finding here.

**D5 — The two horizon channels in Logistics.**
*Options:* (a) keep the `HORIZON_ITEMS` block (parsed free by code) and drop the per-finding
`record_horizon_item` call; (b) keep the tool and stop parsing the block; (c) keep both.
*Trade-off:* the tool was adopted on 09-03 because a template slot went unwritten. A tool call can
be skipped just as easily, and each one costs a round-trip. The block is also the only channel
that lets other specialists use the ledger (#11).
*Recommendation:* (a), checked for a week through the existing `[HORIZON] … new/known` trace
line before the grant is removed.

**D6 — The eight quick-mode sections.**
*Options:* (a) wire them (code passes `mode: quick` into the directive) with Logistics' horizon
filing carved out; (b) delete them.
*Trade-off:* (a) is one line of code and the cheapest turn-saver available, but it changes eight
specialists' routine-turn behaviour at once. Mental Wellbeing's quick mode keeps the clinical
rules by its own text. (b) is safe and saves nothing.
*Recommendation:* (a), inside C2, after the fresh trace measurement shows how many dispatches
are `quick`.

**D7 — The flags no code reads** (`CONSULT_NEEDED`, `RESEARCH_NEEDED`, `PROFILE_GAP`, and
others).
*Options:* (a) parse them and act (auto-dispatch); (b) collect them into one code-built block for
the Synthesizer, at most one profile question per turn; (c) delete them.
*Trade-off:* (a) needs the chain limit (#10) and the research scrub (#17) in code first, or it
amplifies both. (c) loses a real signal, and review #30 found the Synthesizer does use it.
*Recommendation:* (b) now; revisit (a) after #10 and #17 land.

**D8 — Safety in the Goals Interview.**
*Options:* (a) leave detection to the interviewer and add the missing scripted test; (b) also run
Mental Wellbeing in parallel on interview turns; (c) a code phrase screen that forces the safety
path.
*Trade-off:* (b) costs a 3.8 Flash call per interview turn and adds latency to the fastest path
the system has. (c) is a fuzzy match, the kind the method warns against, though here it only adds
safety and replaces nothing. (a) closes the actual gap: the ROADMAP's own lesson is that a safety
path never exercised by a test is not known to work.
*Recommendation:* (a), in C3.

**D9 — Order.**
*Recommendation:* #5 as `/fix` now → C1 → C2 (with the latency build) → C3 → C4. C3 could move
ahead of C2 if Mike would rather close the hard-fail exposure before speed.

---

## 6. Review and Mike's rulings (2026-11-23)

**Fable review:** [agent_instructions_to_code_sweep_review_2026-11-23_fable-5-1.md](agent_instructions_to_code_sweep_review_2026-11-23_fable-5-1.md)
— 21 of 25 rows confirmed, all six § 2b items hold, 19 misses. Mike: this sweep ran at **medium
effort** (the header's "high" is wrong). Three corrections checked against code and accepted:

1. **#5's fix as worded would delete goals** — `write_goals`/`update_goal` read `read_goals()` and
   write it back (`tools/goals.py:63`, `:162`, `:312`). The fix is to **remove the `read_goals`
   grant** from Work & Vocation and Finance plus the two lines. Red routing edits, no code.
2. **#1 is ~7%, not a third** — of the ~170 scheduled-turn events, ~130 are `ROUTING_MISS` (kept
   by the move) and ~40 `USER_CORRECTION`. It also overlaps `[DB-0902-01]`.
3. **Wiring quick mode (#9) alone would switch off the medication check** on most Physical Health
   calls (58 quick vs 6 deep, `tests/run_a4_safety.py:48`).

**Rulings (Mike):**

- **D1–D9 as recommended**, with the review's amendments adopted in chat: D1 `temperature` gets
  its own line; D3 amend all three copies of the principle; D4 enforce, with a write guard (no logs
  from turns with no user words); D5 keep both channels until a malformed block stops failing
  silently; D7 add `CLARIFICATION_NEEDED`; D8 before the second user's first interview; D9 goals
  fix → C1 without #3 → C3 → C2 with quick mode last → C4.
- **D6, amended by Mike:** *"find a way to get the med check clean while working as quickly as
  possible."* So quick mode is not deleted. The medication check moves out of the model's scan
  into code (#8), runs on **every** Physical Health dispatch whatever the mode, **after** the
  specialist returns, so a dose logged this turn counts. It costs no model turn, and only then is
  quick mode wired.
- **D10 — lift the A4 suspension for C3's fixtures** (~$3–4 a run, stated before each run).
- **D11 — "medication taken today" should be a default data object**, which is being built in a
  separate chat (the user's own logs, phase 2+). #8 reads that object, so #8 waits on it.
- **D12 — estimate task lengths, and update the estimates on evidence**; ask only as a secondary,
  when needed (an unknown task). This rule replaces the "ask once" text in `synthesizer.md:395` and
  `synthesizer_day_plan.md:36`.
- **D13 — wait:** no forced Diarist (#3) until the capture-fidelity measurement reports.
