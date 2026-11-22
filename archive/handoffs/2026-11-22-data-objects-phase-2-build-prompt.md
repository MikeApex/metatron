Model: Opus 5.5, high effort — capture becomes a detector feeding a confirmation card, and a model-proposed writer touches the user's record; Red files built with Mike present. Review the diff in Fable before deploy.

# The user's own logs — phase 2 build (paste into a fresh chat)

/metatron-code This session **builds phase 2** of
`archive/plans/custom_logs_and_places_plan_2026-11-21.md`: **noticing and promotion**. When I
keep mentioning a kind of thing no log holds, Metatron asks once whether to start one. I can see
across users which logs people invent. And a writer that files entries from ordinary
conversation is built in shadow, scored before it writes anything for real.

Phase 1 is live (VM at `880027c`): start, add, read back, change, archive; one read door; the
relative-reference rule; corrections have one writer.

## Read first, in order

1. The plan: § 2 (rulings R1–R34 — do not re-open them; R5, R21, R28, R29 and R34 are this
   phase's), § 3.4 "Noticed" and "Derived", § 3.5 "Reverse check", § 3.6, § 3.10, § 4, § 5
   phase 2, § 6 tests 3 and 5, § 7, § 9 M4.
2. `archive/PROJECT_LOG.md` § 2026-11-22, second — what phase 1 built and what its live checks
   corrected. **Its lessons bind this phase:**
   - **An instruction does not hold the Diarist.** Three "do not write" holds failed live; each
     was closed in code or by removing a grant. Every write this phase adds is made **by code**
     (an unbound caller), never by asking a model not to.
   - **The Diarist can add to a user's log only when that turn set a live marker for it**
     (`tools/data_objects.py` `write_data_object`). A noticed or derived entry therefore
     cannot go through the Diarist — that is by design, not a gap to route around.
   - **One writer per kind of change.** Creating a log is code's alone; corrections are the
     Synthesizer's alone.
   - Origins in the registry are `asked`, `template`, `existing` (registered stores and
     pre-registry categories) and, from this phase, `noticed`.
3. The current state of every file you will touch — not the plan's description of it.
   Especially `tools/capture.py` (`raise_new_categories`, the `other` route, `KIND_HOMES`,
   `report`), `config/modules/capture.yaml` (the switches), `tools/confirm.py` (`request`, the
   declined store), and the zone suggestion in `tools/location.py` / `tools/places.py` —
   **the precedent for a code-raised card announced on the next reply**.

## Before writing any code

- **Collision check.** Another chat (ranking, the task ledger) is active in this tree, and on
  2026-11-22 it committed while this build's files were staged, sweeping them into its commit
  (`e796ce6`). Run `git status` and `git log --oneline -15`. **Stage and commit in one command**,
  with a check that the index was empty first. Do not build on another chat's uncommitted lines.
- **Diff the plan against recent work.** For each file in § 4 this phase touches, read the commits
  since 2026-11-21 and say in your plan what that check confirmed and what it killed. Phase 1
  changed `tools/data_objects.py`, `core/orchestrator.py`, `tools/capture.py` (`KIND_HOMES` already
  carries `write_data_object` for task, place and health) and the agent files.
- **A8:** any new orchestrator helper is named with its A8 destination (`ROADMAP.md` § A8 lists
  phase 1's seven).
- **Plan's choices to put to me before building** (the plan leaves them open):
  1. **The matcher call** (a candidate category against every log's name, aliases and
     description): reuse the `data_object_tagger` agent, or a new code-only agent? Either way:
     bulk tier, bare dispatch, empty grant, a routing entry in both files (Red).
  2. **How the card is announced:** the zone suggestion's path, or a line in the logs block the
     Synthesizer already receives (`_data_object_block`)?
- Show me the todo list and wait for my go-ahead before executing it.

## Phase 2 scope (plan § 5, item 2)

1. **The detector — ask, never create (R34).** Capture's `other` facts, counted per user per
   category with no model. A category that reaches **3 in 30 days** (config, start there) becomes a
   candidate on the existing per-turn capture stage or `capture_weekly_rollup`. **No new scheduler
   job:** `core/scheduler.py` is Red and the plan avoids it. Run the matcher (above) first: a match
   becomes an **alias proposal** for the existing log, not a new one.
2. **The card.** A survivor becomes `tools/confirm.py` `request("create_data_object", …)`,
   announced on the **next** reply: *"Want me to start a list of the places you've mentioned
   wanting to try?"* **The answer is the card, never the reply's wording:**
   - Yes → `POST /confirm` creates the log server-side (`origin: noticed`) and files the held
     facts in, by code.
   - No → `declined_confirmations.json`. That category is not offered again unless its count
     doubles.
   - Unanswered → the card expires and counts as neither.
   - "That belongs in my X list" is said in conversation and handled by `amend_data_object`
     (alias plus move), which also declines the card.
   - The yes rate is computed from card outcomes only and reported per user. The config stays on
     **ask**; switching to create-and-tell is my call later (R5).
3. **The reverse check.** `scripts/check_data_object_relevance.py`: the relevance call for one
   agent across every persona's registry, run when an agent file is added. Add the step to
   `docs/CONVENTIONS.md` § adding a module.
4. **Promotion (R6, R21, R29).**
   - `tools/analytics.py`'s daily row gains **counts only**: logs per user by origin (asked,
     noticed, template, existing), and fields added. No names; test it against every field.
   - `scripts/data_object_report.py`: VM, developer-only, prints to the terminal, writes nothing
     tracked. It shows every user's invented names, aliases and fields side by side. **A user
     without the recorded consent is excluded by code.**
5. **The derived writer — in shadow (§ 3.4 "Derived", R15).** The capture extractor proposes an
   `entry` against an existing log; code writes it marked `derived`, with its source turn.
   - Built with a shadow switch in `capture.yaml`: **in shadow it records its proposals and writes
     nothing** (test it).
   - It is switched on only after a labelled score (capture's method). The extractor's worst
     measured error is inventing values (87% precision).
   - Its writes are code's, so phase 1's Diarist gate does not apply. Its values follow
     `tools/record_rules.py`, the same as every other writer.
6. **Capture (§ 3.10):** the new `entry` kind in `KIND_HOMES`. `raise_new_categories` keeps its
   developer alert and gains the per-user path above.

**Red files likely in this phase:**
- `config/agents/capture_extractor.md` (the `entry` kind).
- Both routing files, if the matcher is a new agent.
- `synthesizer.md`, only if the announcement needs a conduct line.

**Not delegated.** Each edit is shown to me line by line before it is made.

## Tests (plan § 6) — every live meter stubbed

Test 3's phase 2 parts and test 5, **confirmed failing on HEAD first** where they pin a fix:
1. The detector asks at 3 in 30 days.
2. A description match becomes an alias proposal.
3. A declined category is not re-offered until its count doubles.
4. Yes creates the log with `origin: noticed` and the held facts.
5. The derived writer writes nothing in shadow.
6. The analytics row contains no log name.
7. The report excludes a user without consent.

Stub the matcher and extractor calls, FCM and the Places API. Regression: `tests/test_data_objects.py`
(53 today), the capture suite, `tests/run_knowledge_routing.py --persona danny_park` (live, a few
cents — `METATRON_LIVE=1`), `scripts/check_agent_tools.py`, `bash scripts/qa_sweep.sh`. Afterwards,
`git checkout HEAD --` any tracked `data/personas/danny_park/…` file a live run dirtied.

## Close

1. A Fable review of the diff before deploy. Ask it to trace a card end to end: detection, card,
   yes / no / expired, the held facts filed. Also ask it to check that nothing in this phase writes
   to a user's log except code.
2. `git diff` every file. Stage and commit in one command, push, then hand me the deploy line
   (`./deploy.sh` is mine).
3. **Live check, run by you on the VM** (I asked for that in phase 1), with TEST-marked messages
   as `mike`. The phase 1 driver is in the 11-22 transcript (`archive/transcripts/`).
   - Mention one TEST category three times. **Pass:** the next reply carries the offer, and a card
     exists.
   - Decline it. **Pass:** it is not offered again.
   - Raise another, accept it. **Pass:** the log exists with the held facts, `origin: noticed`.
   - Archive every TEST log afterwards.
4. **M4, a walkthrough with me (plan § 9):** label the derived writer's shadow sample, about 25
   minutes. Prepare the sample and the steps before the session. The writer stays in shadow until
   the score passes.
5. `/archive`.

## Cost budget

- **Build:** ~0.5–0.7M Opus tokens (plan § 7), plus ~0.15M Fable for the diff review and ~25 min
  of Mike for M4.
- **Run, once live:**
  - one bulk-tier matcher call per candidate that crosses the threshold, ~$0.0005 each (a few
    per user per month);
  - the derived writer's extra extractor output, ~50 tokens a turn, ≈ $0.005/day per user, paid
    in shadow too;
  - cards and the report cost no model call.
- **Persists:**
  - **Cards:** bytes per card. They expire like every confirmation; a restart keeps the store. No
    meter.
  - **Declined categories** (`declined_confirmations.json`): bytes per user, never deleted by
    design, restart-safe. No meter.
  - **Shadow proposals:** bytes a turn, kept with capture's outcomes until the score is taken. No
    meter — the capture report is where they are read.
- **Unseen:** a dead detector reads as "no new logs needed". The capture report prints how many
  categories crossed the threshold and how many cards were raised.
