Model: Opus 5.5, effort high. This is a planning session: survey, design and a plan document, then a Fable adversarial review. No code is written here. Plan in Opus, review in Fable (docs/WORKFLOW.md).

# Capture fidelity — "show it what it missed" (paste into a fresh chat)

**Budget:** ~0.4–0.7M Opus tokens for survey and plan, plus ~0.15M Fable for the adversarial
review. Mike: ~20 min to settle the decisions in § 5. **Nothing is built or deployed in this
session.** The deliverable is
`archive/plans/capture_fidelity_plan_2026-10-<dd>.md`, reviewed and with the decisions settled.

---

/metatron-code Plan the capture-fidelity check: a mechanism that compares what a user said with
what an agent actually recorded, shows the agent what it missed on its next turn, and keeps a
content-free record of misses as a training signal for the agent files. Mike, 2026-10-29: *"worth
a build sooner rather than later. It's a useful training tool for whichever agents are using it."*

Read first, in order:
1. `core/interview.py`: `coverage_block()` (~line 228) and how `run_turn()` assembles the
   interviewer's turn. This is the first consumer, and the coverage block is the channel it
   already trusts.
2. `config/agents/goals_interviewer.md`: Phase 1's *Shape of the day* and the `set_day_shape`
   rule, then Phase 8, *Write-back*.
3. `tools/day_shape.py`: `SECTIONS` and `FIELDS` (~line 107). This is the schema a day fact has
   to fit.
4. The existing relatives below, so the new mechanism joins a family instead of founding a
   second one.

## 1. The need — what a user sees today

**A user tells Metatron something about their life and it is acknowledged but not kept.** Nothing
tells them, and nothing tells the agent. The next session plans around a gap the user believes they
filled. Every agent that records what a user says has this failure, and today the only way anyone
finds a miss is a developer reading transcripts by hand.

**The case that surfaced it (trial_1029, 2026-10-29, Stage 5 check 2 of the second-user build).**
In a first interview the user gave eight day-shape facts. The interviewer saved five, each in the
turn it was given: weekday wake 07:00 and bed 00:00, public transport, dinner 18:00–19:00,
location sharing on. It missed three:
- **"Work is 9–5, but often runs late"**, given twice, in two consecutive turns that made no tool
  call at all.
- **Weekend times** ("out later on weekends and sleep in until around 10").
- **The after-lunch energy slump** ("crash out after lunch"), arguably a window.

It also over-saved once: dinner went in for all seven days when the user had described weekdays.
The instruction to save "each fact in the turn they give it" was already in the file, stated
plainly. **An instruction alone did not hold**, and one was added to it the same day (working hours
and weekend times named). Do not count on that having fixed it.

**The general need — not one agent's problem.** Survey these and decide which are in scope for v1
and which later. Each records user-stated facts through a tool:
- **Goals Interviewer:** day shape (`set_day_shape`), goals (`update_goal`), the remembered good
  period (`write_baseline_period`), purpose and guiding star (`write_config`, approval-gated).
- **Synthesizer and specialists in ordinary turns:** tasks and obligations the user mentions
  (`open_task`, `update_task`), preferences (`write_persona`), profile facts (`write_profile`),
  contacts (`write_contact`), day-shape changes said in passing ("I'm free of childcare today",
  `day_overrides`).
- **Diarist / `write_log`:** whether what the user reported doing reaches the day's log.

**And the training half.** A miss is evidence about an *agent file*: which instruction is not
holding, for which kind of fact, how often. Mike wants that visible so the agent files, and the
coming agent rewrite, are improved from measured misses, not anecdotes. Read the
`project_observer_agent` memory (a Phase 6+ meta-agent that proposes instruction-file changes from
usage, human review required). This mechanism is plausibly its first real input. Say whether the
plan should feed it, and how, without building it.

## 2. Relatives already in the code — survey them before designing

The project has several said-versus-recorded checks, each built alone. The plan must say how the
new one relates to each: reuse, extend, or deliberately stay separate, and why.
- **`enforce_pending_receipt()`** (`core/orchestrator.py`) stops a reply claiming an
  approval-gated action is done. That is the *inverse* failure: claimed but not done.
- **`FALSE_ACTION_CLAIM` / `FALSE_COMPLETION_CLAIM`** quality events (commit `24b4cb0`, "a reply
  that says something is set, queued or lined up is logged as a false claim when nothing was
  written"). Also the inverse, and already a content-free miss log.
- **`_task_hint_block()`** (`core/orchestrator.py` ~6996). Code reads the user's words for a task
  being done and hands the Synthesizer a TASK NOTE naming the task id. **This is the same shape as
  "show it what it missed", for one fact type, already live.** Study it closely.
- **`ROUTING_MISS`** (`tools/logger.py`): the Synthesizer reporting a signal no specialist
  surfaced. A model-reported miss with a known reliability problem (`[DB-0902-01]`). Do not
  repeat its failure.
- **The interview coverage block:** a code-built summary of what is saved, which the interviewer
  is told to trust over its memory.

## 3. Constraints that bind the design

1. **One writer.** Mike's steer and the recommendation he accepted: the agent stays the only thing
   that writes the user's record. The check *shows* what was missed; it does not save on the
   agent's behalf. A wrong save (guessed days, guessed firmness) does more harm than a missing one.
   If the plan finds a fact type where code should write directly, argue it explicitly; do not
   drift into it.
2. **Privacy.** The user's words are sensitive-tier. Any extraction model runs on the same
   Vertex path as the agents, under the same per-user consent records (`ROADMAP.md` § Section 0,
   the 2026-10-26 amendment). The *training record* is content-free: counts, field names, agent,
   turn ids, never the user's words or values. The same discipline as A9's rollup
   (`ROADMAP.md` § A9) and the day planner's `log.jsonl`.
3. **Cost is a design axis** (`~/.claude/CLAUDE.md` § Costs). Name the Run cost per turn and per
   day per user, with both users active. Mike's use is ~$1.50–2.00/day, so state the increment as
   a share of that. Name what bounds it: which turns run the check (not proactive turns, which have
   no user words; see `has_real_user_turn`), which agents, and a model tier. If anything persists
   (a cache, a queue), answer the three questions in § Costs at the moment the parameter is set.
4. **Latency.** Reply latency is already an open complaint
   (`archive/handoffs/2026-10-28-reply-latency-defer-thinking-cache-prompt.md`). The check must not
   sit in front of the reply. Decide when it runs: after the turn, feeding the *next* turn, is the
   obvious shape. Say what happens when the user's next message arrives before it finishes.
5. **False positives teach the wrong lesson.** A "miss" the user never meant as a standing fact
   ("I'm so tired today" is not a day-shape window), or one they asked not to be kept, must not
   push the agent to save it. Define what counts as a fact per agent and per field, and how
   "the user said not to" or "the agent asked and is waiting" is recognised.
6. **Volume.** A miss list that grows every turn becomes noise the agent learns to skip, the same
   reason `check_agent_tools.py` and the rule audit report each finding once. Decide how a miss is
   shown once, cleared when saved or dismissed, and capped.
7. **Code over instruction for enforcement.** `CLAUDE.md`: what must hold is enforced in Python.
   The check itself is code; only the *response* to a shown miss is the model's.

## 4. The plan document must contain

1. **The need**, in user terms first (§ 1), with the trial_1029 evidence.
2. **The survey:** each candidate agent and fact type, how it records today, and its observed or
   likely miss rate. Measure where you can: real traces exist for `mike` and the trial accounts
   on the VM, read through the read doors (`scripts/vm_read.py`) or the VM line. Say what was
   measured and what was estimated.
3. **The relatives (§ 2)** and the decision for each.
4. **The design:** where it runs, the extraction (model, prompt shape, schema per fact type), the
   comparison against what was saved, how a miss reaches the agent (per agent: the interviewer's
   coverage block; what for the Synthesizer?), lifecycle (shown once, cleared, capped), and the
   content-free training record with how it is read: a report, an A9 rollup column, or input
   to the Observer.
5. **v1 scope.** Recommend starting with the interviewer's day shape and goals (smallest surface,
   known evidence, Iva's first interview imminent), then name the order for the rest.
6. **Files and tiers**, split per `.claude/settings.json`. Red files (`config/agents/*.md`,
   `routing*.yaml`, `core/{router,persona,scheduler,spend_guard}.py`) are built with Mike present,
   never delegated.
7. **Tests:** synthetic personas, every live meter stubbed (`SESSION.md` standing rule), including
   a replay of the trial_1029 turns that fails on today's code for the three misses and the
   seven-day dinner. Plus one live check on the VM after deploy.
8. **Cost**, all four classes (Build, Run, Ancillary, Unseen), and the model recommendation for
   building.
9. **Decisions for Mike** (§ 5), each with options, trade-off and a recommendation.

Then run `/adversarial-review` on the plan (Fable), fold in the findings, and put the decisions to
Mike.

## 5. Decisions the plan should put to Mike (add any the survey raises)

1. **v1 scope:** interviewer only, or interviewer plus ordinary-turn task capture?
2. **The extraction model's tier**, bulk versus reasoning, priced.
3. **Where the training record surfaces:** a weekly report, an A9 column, the session-start line,
   or held for the Observer.
4. **Whether it ships before Iva's next interview session** or after her first week of use.

## State on entry (2026-10-29)

- VM at or after `3cca677` once Mike deploys this evening. It carries the interviewer edits the
  trial_1029 run prompted: bullets for several questions, one register per turn, working hours
  and weekend times named as facts to save. **Re-measure the miss rate after that deploy before
  sizing the problem.** Some of the 3-in-8 may already be gone.
- The second user, Iva, starts her first interview this weekend
  (`archive/handoffs/` prompt written at the 2026-10-29 `/archive`). Her transcript will be the
  first real evidence after the deploy. Read it if it exists by the time this runs.
- An agent rewrite is coming (Mike, 2026-10-29). Clinical flags get their own treatment there.
  Design this so it survives the rewrite: keyed on tools and fact types, not on today's agent
  file wording.
- Another chat may be working in the tree. `git diff` every file before staging anything, and
  never stage another session's lines.

Close with `/archive`.
