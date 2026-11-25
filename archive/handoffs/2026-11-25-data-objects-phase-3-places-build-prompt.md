Model: Opus 5.5, high effort. This phase changes how the day planner finds where the user is and adds a code-raised offer, and it touches the location privacy tier. Synthesizer, Coordinator and routing edits are done with Mike present and never delegated. Review the diff in Fable before deploy.

# The user's own data — phase 3: Places (paste into a fresh chat)

/metatron-code This session **builds phase 3** of
`archive/plans/custom_logs_and_places_plan_2026-11-21.md`: **Places**. When I name a place,
Metatron finds where it is and remembers what it's for and what I think of it. Arriving there
counts the same as arriving home or at school. When a meal or an errand comes up near a place
that fits, Metatron mentions it, including the places I've said to avoid. A place I keep
mentioning without saving gets one question.

Phases 1–2 are live (VM at `95c3ce7` or later). Phase 1: start, add, read back, change and
archive a log. Phase 2: lists are noticed and offered on a card, and the derived writer is ON.
**Phase 2's one-week check is `[DB-1125-01]`, due 12-02. It does not gate this phase** (Mike,
11-25).

## Read first, in order

1. The plan: § 2 (rulings R1–R34; do not re-open them. R7, R10, R11, R13, R15, R24, R25, R27 and
   R33 are this phase's), § 3.7 Places (all of it, **except** the unnamed spots built from
   location reports, which are phase 4), § 3.10, § 4, § 5 phase 3, § 6 test 4 (the parts that
   aren't phase 4), § 7, § 9 M3.
2. `archive/log/2026-11-22-02-custom-logs-phase-1-built-and-live.md` and
   `archive/log/2026-11-23-11-data-objects-phase-2-live-names-and-medication.md`. **These
   lessons bind this phase:**
   - **An instruction does not hold a model.** Every write this phase adds is made by code.
   - **One writer per kind of change.** Creating a log is code's alone, and so are corrections
     from the Synthesizer's path. A place record follows the same rule.
   - **YAML reads a bare `on` as `True`.** Quote every new switch, and import-check a clean
     export before pushing (`35fb231`).
   - **No real details in code** (CLAUDE.md § Data Privacy). Tests, code, comments and agent
     files use invented venue and street names. Mike's real places exist only in persona data,
     seeded by M3.
3. `tools/noticed_logs.py` and its card path. **This is the precedent** for the "place you keep
   mentioning" question.
4. The current state of every file you will touch, not the plan's description of it. Especially:
   - `tools/location.py`: `zone_for`, `record_position`, `load_zones` and the module
     docstring. The docstring is rewritten to state R24 and R33.
   - `tools/places.py`: `geocode_place_name`, `find_places` and `_open_at`.
   - `tools/day_plan.py`: `_zone_coords` and `_start_point`.
   - `tools/obligations.py`: the `load_zones()` name check. The plan said about line 2168, so
     find it, don't trust the number.
   - `tools/data_objects.py`: the templates and `identity: thing+occurrences`.
   - `tools/capture.py`: `KIND_HOMES['place']`.

## Before writing any code

- **Collision check.** Other chats are live in this tree, and the goal network and WhatsApp
  chats have committed recently. Run `git status` and `git log --oneline -15`. Uncommitted files
  belonging to other chats stay unstaged. **Stage and commit in one command**, with a check that
  the index was empty first (`git diff --cached --stat` alone, before committing).
- **Diff the plan against recent work.** For each § 4 file this phase touches, read its commits
  since 2026-11-21 and say in your plan what that check confirmed and what it killed. Since the
  plan was written, `tools/day_plan.py`, `tools/obligations.py` and `synthesizer.md` have all
  changed under the goal network and ranking builds.
- **A8:** name any new orchestrator helper with its A8 destination (`ROADMAP.md` § A8).
- **Put these plan's choices to me before building:**
  1. **An ambiguous name** ("a chemist's chain, plus an area"): take the result nearest the
     stated area, saved with `confirmed: false` until I visit or confirm it. Keep this, or ask
     every time?
  2. **Where `places_near` reaches the Synthesizer:** a tool it calls, or a result code attaches
     when the turn is about a meal, a free slot or an errand? Weigh the cost of each against how
     reliably each fires.
  3. **The "keeps coming up" question:** the same card shape as phase 2's noticed list (three
     mentions in 30 days, a declined place not asked again until its count doubles), or a
     different threshold?
  4. **The Places API price per lookup** is unchecked (plan § 7). WebFetch is Denied here, so
     give me the pricing page to read during M3 and record the figure in the plan.
- Show me the todo list and wait for my go-ahead before executing it.

## Phase 3 scope (plan § 5, item 3)

1. **The places object.** Add a template with `identity: thing+occurrences`. Fields: name, kind,
   **verdict**, **occasion**, notes, public coordinates and radius, source, `confirmed`,
   `private`. Its occurrences are visits and mentions. Coordinates are stored on the place itself
   (the plan's choice), so the in-memory geocode cache only matters for names not yet saved.
2. **Looked up by name when said** (R7). Use `geocode_place_name`, with ambiguity handled per
   choice 1.
3. **Zones are unchanged** (R27). `zones.yaml`, its confirm-gated write and the location tier all
   stay as they are. `zone_for()` additionally matches places that have coordinates. Home,
   school and work are registered as places through their zone entries.
4. **`location.known_places()`** returns zones and coordinate-bearing places together. **All
   three readers switch to it:** `day_plan._zone_coords`, `day_plan._start_point` and the
   obligations name check. Otherwise, when the user arrives somewhere, the planner silently
   starts from `home` and every travel time is wrong.
5. **`location_last.json`** (R33). One row, rounded to about 100 m, overwritten by
   `record_position()` on every report. It is never in a prompt; code returns distances only.
6. **`places_near(where, occasion)`.** Code only, no model call. *Where* is the current zone,
   the last report, or a planned location from the day plan. It returns name, distance, verdict
   and occasion, filtered by occasion, open-now where known, and `private`. **"Avoid" places are
   returned whenever their occasion matches.** `place_mentions.jsonl` records each time a place
   is raised and the user's response. A declined suggestion waits until the place's occasion or
   verdict changes.
7. **Places that keep coming up in conversation.** Capture `place` facts that match no saved
   place, three mentions trigger the question (per choice 3). Named, it becomes a place with its
   mentions carried over. Declined or ignored, it is kept as `hidden`.
8. **Task → place.** A task gains an optional `place` reference, so "you're near the chemist
   and the prescription is ready" is a join done in code (`tools/obligations.py`).
9. **The 08-28 location ruling's amendment** (R24, R33) is stated in `tools/location.py`'s
   docstring, so the code's own account of its tier stays true.
10. **Grants and conduct.** Grant `places_near` and the place reads to the agents that need them,
    in both routing files. `synthesizer.md` gets how to raise a place and when to name an avoided
    one. `coordinator.md` gets anything needed to resolve a place said aloud. **Shown to me line
    by line before each edit; not delegated.**

**Not this phase:** background location, geofences, `POST /location/visit`,
`GET /location/geofences`, the `location_history` consent scope, unnamed spots from location
reports, and `location_candidates.jsonl`. All of that is phase 4. Pattern Miner's grant is
phase 5.

## Tests (plan § 6). Stub every live meter.

Confirm each test fails on HEAD first, wherever it pins a fix.

1. `zone_for` matches a place.
2. **`_start_point()` resolves a place the user arrived at today, not `home`.** Also: travel
   time is measured from that place.
3. The obligations name check accepts a place name.
4. `location_last.json` is one row, overwritten and rounded.
5. **No coordinate appears in any string that reaches a prompt.** Extend the existing location
   tier test to every new path.
6. `places_near` filters by occasion and `private`, and returns avoid-places.
7. A declined suggestion is not raised again until the occasion or verdict changes.
8. An ambiguous name is saved `confirmed: false`.
9. Three conversation mentions raise the question once. A decline leaves the place `hidden`.
10. A task's place joins in code.

Stub the Places API, the capture extractor, FCM and CalDAV. Regression suites:
`tests/test_data_objects.py`, the capture suite, the day-plan suites,
`tests/run_knowledge_routing.py --persona danny_park` (live, a few cents, `METATRON_LIVE=1`),
`scripts/check_agent_tools.py` after the grants, and `bash scripts/qa_sweep.sh`. Afterwards,
`git checkout HEAD --` any tracked `data/personas/danny_park/…` file a live run dirtied.

## Close, which moves the build to the next phase on its own

1. **Fable reviews the diff before deploy.** Ask it to trace a place end to end: said aloud,
   looked up, saved, arrived at (the day planner's start point), raised near a meal, avoided,
   declined. Also ask it to check that no coordinate reaches any prompt.
2. `git diff` every file. Stage and commit in one command, push, then hand me the deploy line.
   `./deploy.sh` is mine.
3. **M3, a guided walkthrough with me** (plan § 9), about 20 minutes. Prepare it before the
   session:
   - Seed `mike`'s three named places on the VM from a prepared script. `data/personas/**` is
     Denied, so I run the script.
   - I read the Places pricing page, and you record the price.
4. **Live check, run by you on the VM, with TEST-marked messages as `mike`:**
   - A place said aloud gains coordinates. **Pass:** the record has coordinates and no
     coordinate appears in any reply.
   - A meal planned near home raises the go-to place. **Pass:** it is named. **Fail:** a
     try-someday place is raised on a walk past it.
   - An avoid-place comes back when its occasion comes up.
   - Arriving at a saved place moves the day planner's start point.
   - Archive every TEST place afterwards.
5. **Write the phase 4 build prompt before closing**, so the build moves on without a separate
   planning session:
   - Use this file as the template, saved as
     `archive/handoffs/YYYY-MM-DD-data-objects-phase-4-background-location-build-prompt.md`.
   - First line: its model. Plan § 8 says Opus, high. Android and a consent gate both apply.
   - Scope: plan § 3.8, the unnamed spots built from location reports (§ 3.7), § 5 item 4, test
     4's phase 4 parts, and **M5** (the walkthrough on the phone).
   - Bind it to what this phase built and learned.
   - **State its gate as the first thing it checks:** the plan builds phase 4 against the
     Android tree only once WhatsApp's work has landed. Today that means WhatsApp Phase 2's
     walkthrough has passed through M4 (`SESSION.md` § WhatsApp). If the gate is not met, the
     session says so and stops.
   - Its own close carries this same step 5, writing the **phase 5 (Pattern Miner) prompt**
     (§ 3.9, § 5 item 5: a Red grant and agent-file change, Opus, short).
   - Phase 5's close carries a final step instead: mark the plan's § 5 complete, and tell me
     the data-objects build is finished.
6. `/archive`. In the `SESSION.md` refresh, the "Next" line names the phase 4 prompt by its full
   path and its gate. **Give me the link to it as the last line of your final message.**

## Cost budget

- **Build:** about 0.6–0.9M Opus tokens (plan § 7). Add about 0.15M Fable for the diff review,
  about 20 minutes of me for M3, and about 0.05M to write the phase 4 prompt.
- **Run, once live:**
  - `places_near`, `known_places` and the mentions logic are code: **$0**.
  - One Places API lookup per new place name. The price is filled in at M3. Expect a few lookups
    per user per week at first, then near zero, because coordinates are stored on the place.
  - The Synthesizer's input grows by the `places_near` result on turns where it appears. That is
    tens of tokens on the reasoning tier, under $0.001 per turn, and only on meal, free-slot or
    errand turns.
- **Persists:**
  - **Place records:** kilobytes per user, kept forever by ruling (R13). Survive a restart. No
    meter, and none is needed at this size.
  - **`place_mentions.jsonl`:** bytes per raise, kept, restart-safe. No meter.
  - **`location_last.json`:** one row per user, overwritten and never appended. It survives a
    restart, which is its purpose (R33). No meter.
  - **The geocode cache:** in memory, emptied by a restart. Only names not yet saved pay for a
    re-lookup.
- **Unseen:**
  1. **If the Places key lapses, lookup by name stops with no error.** The live check's "a place
     said aloud gains coordinates" is the only check. Have it print a warning when the key is
     missing.
  2. **If `places_near` never fires, it looks the same as "nothing nearby".** Count raises per
     day in the analytics row (counts only, no names).
