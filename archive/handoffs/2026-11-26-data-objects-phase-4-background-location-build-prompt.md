Model: Opus 5.5, high effort. This phase touches Android, a new consent scope and the location tier's most sensitive amendment (recurring unnamed spots stored as rounded points). The Synthesizer, Coordinator and any routing edits are done with Mike present and never delegated. Review the diff in Fable before deploy.

# The user's own data — phase 4: Background location (paste into a fresh chat)

/metatron-code This session **builds phase 4** of
`archive/plans/custom_logs_and_places_plan_2026-11-21.md`: **background location**. With it
switched on (off by default, per user, behind a consent record), the phone reports arrivals at
the user's saved places by itself, and reports significant moves. A spot the user keeps
stopping at without naming gets one question: "you've been at the same place three Tuesday
evenings — what is it?". The question is described relative to known places and times, never
by reverse lookup.

## FIRST: the gate. Check it before reading anything else

The plan builds phase 4 against the Android tree **only once WhatsApp's work has landed**.
Today that means **WhatsApp Phase 2's walkthrough has passed through M4**. Read `SESSION.md`
§ WhatsApp and the latest WhatsApp log fragment, and check `git log -- android/` for
uncommitted or in-flight WhatsApp work.

**If the gate is not met, say so in one line, say what is still owed (which walkthrough step),
and stop.** Do not plan, do not read further, do not touch `android/`.

## What phase 3 built (VM at the phase 3 commit or later)

Read `archive/log/` fragments for 2026-11-26 (phase 3 built) and the phase 3 build plan
`archive/plans/data_objects_phase3_build_plan_2026-11-25.md`, in full. In short:

- **Places are a data object written only by code.** The `places` template carries
  `writer: code`, and every model door refuses it. The Coordinator's `PLACES` directive is
  resolved by `core/orchestrator.py` `_resolve_places()` into `tools/saved_places.py` `save()`.
  Each place carries a public position (`lat`/`lon`/`radius_m`) from a lookup by name, plus a
  verdict (`go_to|try|avoid|none`), an occasion (`{kind, what?, near?}`, with kinds extendable
  per user) and `confirmed` / `private` / `hidden` flags. Visits and mentions are its
  occurrences.
- **`tools/location.py`:**
  - `known_places()` returns zones plus positioned places; `zone_for()` matches both, smallest
    circle wins.
  - An arrival at a place records a `visit` (`saved_places.record_visit`).
  - `location_last.json` is ONE rounded row (3 decimal places), overwritten by
    `record_position()` (R33).
  - The docstring states R24 and R33. **Phase 4 adds R24's second clause**, recurring unnamed
    spots, so it amends that docstring again.
- **Provenance reconciliation** in `data_objects.archive_write` for a template's `guarded`
  fields: a lower source never overwrites a higher one, and a change is said once.
- **A zone beats a saved place when both match, and a place needs a fix within 100 m**
  (`zone_for`). `mike`'s go-to Bianco 43 is about 50 m from home, inside the home circle, so it
  can never be "arrived at": the 11-26 live check proved it. That is correct, not a defect.
  Phase 4's geofences must respect the same rule: a geofence for a place inside a zone must not
  report an arrival the zone already holds.
- **Opening hours are fetched once, with a place's lookup** (Enterprise SKU: $35 / 1,000, 1,000
  free a month, read by Mike at M3) and stored as `hours`. They are kept out of every read.
- **A hand-run script must load `.env` itself.** The first M3 run wrote every correction and
  looked nothing up, because only the server's unit loads the Places key. The missing-key
  warning is what caught it.
- **`scripts/seed_places.py` is the precedent for a guided data step:** a dry run that shows
  every row as it will be, corrections applied before any lookup, a re-run that is safe, and
  real names only in a `/tmp` file the script refuses to read from inside the repo.
- **The "keeps coming up" card** (`save_place`, `saved_places.take_offer`) is the precedent for
  this phase's unnamed-spot question: same card shape, same declined → hidden, same
  re-offer-at-double with a fresh offer id. The card layer refuses an identical refused
  request, so a new id is needed.

## Lessons that bind this phase (from phases 1–3)

- **An instruction does not hold a model.** Every write this phase adds is made by code. A
  geofence visit is written by the server, never by a model told about it.
- **One writer per kind of change.** Visits come from `record_visit` alone, whether triggered
  by a ping, a geofence or a stay.
- **Coordinates never enter a prompt.** Extend `tests/test_places_phase3.py` check 5's
  coordinate scan to every new string: the unnamed-spot question, the geofence endpoint's
  logs, any card. `location_candidates.jsonl` is never readable by a model.
- **YAML reads a bare `on` as `True`.** Quote every new switch, and import-check a clean export
  before pushing.
- **No real details in code.** Tests, code, comments and agent files use invented venue and
  street names.
- **Stage and commit in one command, with `git diff --cached --stat` checked empty first.**
  Other chats share this tree.

## Read first, in order

1. The plan: § 2 R8, R9, R12, R13, R22, R23, R24, R33; § 3.7 (the unnamed-spots paragraph:
   stay measured at departure, the ~150 m join, 10-minute minimum, 3 visits); § 3.8 all of it;
   § 5 item 4; § 6 test 4's phase 4 parts; § 7; § 9 M5.
2. `core/consent.py` (`CURRENT_VERSIONS`, `APP_SCOPES`, the `correspondence_read` precedent)
   and `config/consent/`.
3. `core/server.py` `POST /location` and `LocationPing`, `tools/location.py`,
   `tools/saved_places.py`.
4. The Android tree's location code and WhatsApp's settings-screen patterns (the switch's home).

## Before writing any code

- **Collision check:** `git status`, `git log --oneline -15`, `git log -- android/`.
- **Diff the plan against recent work:** for each § 4 file this phase touches, read its commits
  since 2026-11-26 and say what that confirmed and what it killed.
- **A8:** name any new orchestrator helper with its A8 destination.
- **Put these plan's choices to Mike before building:**
  1. The two feeds (geofences for known places, plus significant-movement reports), or
     geofences alone at first?
  2. The 10-minute minimum stay and 3 visits: keep them, or shorten them on a test config for
     M5 only?
  3. How many places the phone holds as geofences (plan: nearest ~100), and how often it
     re-fetches.
  4. The consent text `config/consent/location_history_v1.md`: Mike reads and approves it
     word for word.
- Show the todo list and wait for the go-ahead.

## Scope (plan § 5 item 4)

1. **Consent:** the `location_history` scope in `CURRENT_VERSIONS` and `APP_SCOPES`, the
   versioned text, and the per-user record. No record means the server refuses, for every user,
   `mike` included (R23).
2. **One gate, both feeds:** `consent.require(persona, "location_history")` on
   `POST /location` with `background: true`, and on the new `POST /location/visit`
   (`{place_id, event: enter|exit, ts}`, which records the transition by name and carries no
   coordinate).
3. **`GET /location/geofences`:** the public positions and radii of the nearest ~100
   non-private, non-hidden places, behind the same gate.
4. **Android:** OFF by default; switching on shows the consent text; geofences plus
   significant-movement reports; switching off stops reports. Battery-optimisation handling.
5. **Unnamed spots (R8, R24):** `location_candidates.jsonl`, holding a point rounded to
   ~100 m, a count and visit times, never model-readable. A stay is measured at departure (a
   report > ~200 m from `location_last.json`); a visit joins a candidate within ~150 m; at
   3 visits, one question described relative to known places and times. Named → a place, with
   its visits carried over. Declined or ignored → kept, `hidden`.
6. **Unseen cost:** the location report shows the last background report time per user. If
   Android stops reporting, that must not read as "stayed home".
7. **Docstring:** `tools/location.py` states R24's second clause as built.

**Not this phase:** Pattern Miner's grant and visit summary (phase 5).

## Tests (plan § 6 test 4, phase 4 parts). Stub every live meter

Confirm each test fails on HEAD first.
1. Both endpoints and `GET /location/geofences` are refused without the consent record and
   accepted with it, for every user including `mike`.
2. A geofence visit records a transition by name and a `visit` occurrence, with no coordinate
   anywhere.
3. Candidates are rounded, dwell-gated, and joined within ~150 m across rounding cells.
4. Three visits raise the question once; a decline leaves it hidden.
5. No coordinate in any prompt-bound string (extend check 5).

Regressions: `tests/test_places_phase3.py`, `tests/test_location*.py`,
`tests/test_zone_suggestion.py`, `tests/test_data_objects.py`, the day-plan suites,
`tests/run_knowledge_routing.py --persona danny_park` (live, a few cents, `METATRON_LIVE=1`),
`scripts/check_agent_tools.py`, `bash scripts/qa_sweep.sh`. Afterwards,
`git checkout HEAD --` any tracked `data/personas/danny_park/…` file a live run dirtied.

## Close, which moves the build to the next phase on its own

1. **Fable reviews the diff before deploy:** consent gating on every path, stay detection
   (the plan's verify finding NEW 2 was never re-verified), and no coordinate in any prompt.
2. `git diff` every file. Stage and commit in one command, push, then hand Mike the deploy line
   and the APK build. `./deploy.sh` is his.
3. **M5, a guided walkthrough on the phone (plan § 9):** switch on, walk to a known place, see
   the visit logged. Stay 10+ minutes at one unnamed spot on three separate days (shortened
   thresholds on a test config are fine for the first run) and see the question arrive. Switch
   off and confirm reports stop.
4. **Write the phase 5 build prompt before closing:**
   - Use this file as the template, saved as
     `archive/handoffs/YYYY-MM-DD-data-objects-phase-5-pattern-miner-build-prompt.md`.
   - First line: Opus, short. It is a Red grant plus an agent-file change, with Mike.
   - Scope: plan § 3.9 and § 5 item 5. Pattern Miner gets the native read tools (§ 3.3 list),
     `read_data_object`, and a code-built visit summary (visits by place, day and duration,
     never coordinates), and sees `private` entries (R24). Measure its input tokens before and
     after (§ 7 Ancillary).
   - **Its close carries a final step instead of a next prompt:** mark the plan's § 5 complete,
     and tell Mike the data-objects build is finished.
5. `/archive`. In the `SESSION.md` refresh, the "Next" line names the phase 5 prompt by its
   full path. **Give Mike the link to it as the last line of your final message.**

## Cost budget

- **Build:** about 0.5–0.8M Opus tokens (plan § 7), plus about 0.15M Fable for the diff review,
  an APK build, about 0.05M to write the phase 5 prompt, and M5 spread over three days of
  Mike's ordinary movement plus about 20 minutes of guided steps.
- **Run, once live:** background reports cost server CPU only, with no model call per report.
  The geofence list is code. The unnamed-spot question is one card per spot. Phone battery is
  the real cost; measure it during M5.
- **Persists:**
  - **`location_candidates.jsonl`:** bytes per visit, kept forever (R13), restart-safe, no
    meter.
  - **Geofences on the phone:** re-fetched on a significant move. They die with the app's data
    and are deleted when the switch goes off.
- **Unseen:**
  1. **If Android stops reporting, it reads as "stayed home".** The location report's
     last-background-report time is the only check.
  2. **A revoked OS permission silently stops geofences.** The app must say so on its screen.
