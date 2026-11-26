# Data objects phase 3 — Places: build plan (2026-11-25)

Phase 3 of `archive/plans/custom_logs_and_places_plan_2026-11-21.md` (§ 3.7, § 5 item 3), from
`archive/handoffs/2026-11-25-data-objects-phase-3-places-build-prompt.md`. Opus 5.5, high. Rulings
R1–R34 stand and are not re-opened. Everything below marked **Mike** was ruled in this session
(2026-11-25/26); the rest is the build's choice, put to the Fable diff review.

## 1. What a user gets

Naming a place ("Bianco 43 — our go-to pizza") saves it: its public position, the verdict and
the occasion it is for. Arriving there counts as arriving home or at the office does, so the day
planner measures travel from where the user actually is. When a meal, an errand or a free slot
comes up near a saved place that fits, the place is mentioned — and so is one the user said to
avoid. A place mentioned three times without being saved gets one question, on a card.

## 2. Mike's rulings (2026-11-25/26)

1. **Ambiguous names — as rec.** Up to 3 results by name + area (no position sent); results more
   than 300 m apart are ambiguous; take the one nearest the stated area, else nearest the home
   zone (computed locally); save `confirmed: false`; the reply names the street once. A visit or
   the user's yes confirms.
2. **`places_near` reaches the Synthesizer by code attachment, not a tool — as rec.** Triggers in
   code: a meal (food or venue turn, or a meal block within the next ~3 h), an errand (an open
   task whose `zone` is a place within ~1 km of where), a free slot (a planning turn with ≥ 60
   free minutes — only `activity`/`any` places). Logistics receives the same block on venue turns.
   **No new tool grants; both routing files are unchanged.**
3. **The "keeps coming up" question — as rec.** Phase 2's shape: 3 mentions in 30 days; a declined
   place waits until its count doubles; names matched by code (name, aliases, 0.85 close match),
   no matcher model. Yes → a place, mentions carried over; no / ignored → kept `hidden`.
4. **Price — as rec.** Mike reads https://developers.google.com/maps/billing-and-pricing/pricing
   at M3 (Places API (New) — Text Search: the SKU the geocode mask lands on, 3 results vs 1, the
   free monthly cap, the opening-hours tier). Until then saved places' hours are "unknown".
   **Read by Mike at M3, 2026-11-26** (pricing list + Text Search (New) reference + usage and
   billing pages):
   - `displayName`, `formattedAddress`, `location` → **Text Search Pro: $32.00 / 1,000** (first
     100,000), **5,000 free a month**. ≈ $0.032 a lookup past the free cap.
   - **3 results vs 1: no difference shown** — billing is per request at the highest SKU the
     field mask reaches; `pageSize` is not said to affect it (inferred, not stated; check one
     request in the billing report if volume ever matters).
   - **Opening hours** (`regularOpeningHours` / `currentOpeningHours`) → **Text Search
     Enterprise: $35.00 / 1,000, 1,000 free a month**; adding either moves the whole request.
   - The old $200 monthly credit ended 2025-02-28; the per-SKU free caps are the allowance.
   - **Run cost at this volume: $0.** A few lookups per user per week sit far inside 5,000 a
     month; the caps are per SKU across the project, shared with Logistics' `find_places` (Pro,
     or Enterprise when it asks for hours) and the zone suggestion (Pro). No meter sees any of it
     — `places_lookup_*` counts in the analytics row are the only record.
5. **Place records are written by code alone — as rec.** The Coordinator emits `PLACES`; code
   creates/updates and geocodes (started in the background at Coordinator parse, ~1.5 s budget
   before the Synthesizer; a late lookup still lands). Model doors into `places`
   (`write_archive`, `write_data_object`) are refused in code.
   **Plus, on conflicting writers (Mike's question):** provenance reconciliation in code at write
   time, generalised once in `archive_write` — § 4.
6. **Task → place — as rec.** The existing task `zone` field accepts any known place. No second
   field.
7. **M3 — as rec, run at the end of this build chat** (not a separate session): the registry
   update, the 13 existing rows geocoded with a per-row dry run, three named places from an
   untracked input file.
8. **Occasion kinds are extendable per persona, like fields (Mike).** The template carries the
   base kinds; a persona's registry entry adds its own. A kind the user uses that is not on their
   list is added by code — never silently mapped onto the nearest base kind.

## 3. The places object

`config/data_objects/places.yaml` — id `places` (the existing category, so `mike`'s 13 rows are
its rows), `store: archive`, `identity: thing+occurrences`.

| Field | Meaning | Writer |
|---|---|---|
| `name` | as the user says it (identity key) | code, from `PLACES` |
| `kind` | restaurant, pharmacy, park … free text | code, from `PLACES` |
| `verdict` | `go_to` \| `try` \| `avoid` \| `none` — **guarded** | code |
| `occasion` | `{kind, what?, near?}`; kind from the persona's list — **guarded** | code |
| `notes` | free text | code |
| `address` | the lookup's public address | code |
| `lat`, `lon`, `radius_m` | the place's public position (never the user's) | code only |
| `source` | said / calendar / list / zone | code |
| `confirmed` | false until a visit or the user's yes | code |
| `private` | out of day-to-day mention; Pattern Miner still sees it (R24) | code / amend |
| `hidden` | a declined "keeps coming up" name | code |
| `occurrences` | visits (`{at, kind: visit}`) and mentions (`{at, kind: mention}`) | code |

Base occasion kinds: `meal, coffee, drinks, shop, errand, activity, any`. A persona's extra kinds
live on its registry entry as `occasion_kinds` (ruling 8).

Zones are **not copied** into `places.json` (R27: `zones.yaml` and its confirm-gated write are
unchanged). `known_places()` presents them as places with `source: zone`.

## 4. Conflicting writers — provenance reconciliation (ruling 5)

A template may mark fields `guarded`. For a guarded field, `archive_write` stores
`{field}_source` (`stated` | `derived`) and applies, in the moment:

1. **same or higher source** → the newer value wins; the old goes to `previous` (a change of mind
   is real);
2. **lower over higher** → never overwrites; held as `pending_{field}` and asked once only if it
   recurs;
3. **two stated values disagreeing in one turn** → neither written; one question.

A changed guarded value is said once, by code, in the next reply ("changed Bianco 43 from go-to
to avoid"). Places mark `verdict` and `occasion`; other logs opt in from their template. Run cost:
bytes per field, no model call.

## 5. Location (R24, R27, R33)

- `zone_for()` also matches coordinate-bearing, non-hidden places; **smallest radius wins** across
  zones and places alike. A place's default radius is 75 m (a venue, not a neighbourhood).
- `known_places(persona)` → `[{name, lat, lon, radius_m, source, private}]`, zones first. **Every
  reader that resolves a place name switches to it:** `day_plan._zone_coords`, `_start_point`
  (via `_zone_coords`) and the obligations `zone` name check.
- `location_last.json` — one row, `{lat, lon, at}`, rounded to 3 decimal places (~110 m N–S),
  overwritten by `record_position()` on every report; mode `600`. Read only by `places_near`.
- An arrival at a place appends a `visit` occurrence and sets `confirmed: true`.
- The module docstring is rewritten to state R24 and R33.

## 6. `places_near(where, occasion)` and mentions

Code only, in `tools/saved_places.py`. *Where* = the current zone/place if arrived today, else
`location_last.json` if fresh (< 3 h), else a planned location (a day-plan block's location,
resolved through `known_places()` or a name geocode). Returns `{name, distance_m, verdict,
occasion, open}` — **never a coordinate**. Filters: occasion kind matches (`any` matches all),
not `private`, not `hidden`, within `near_max_m` (config, 1,500 m), open where hours are known.
**`avoid` places are returned whenever their occasion matches.** A `try` place is only returned
when the occasion is an actual plan (a meal being planned), never on a passing walk.

`place_mentions.jsonl`: one row per raise — `{at, place_id, occasion, response}`; response is
`accepted | declined | none`, read from the next user turn by code (a declining word list, the
same signal approach as the task note). A declined place is not raised again until its verdict
or occasion changes (memory, not a cap — R11).

The attached block (Synthesizer, and Logistics on venue turns):

```
## Saved places near the user (from code)
- Bianco 43 — 400 m — go-to for pizza
- Clipstone — 650 m — AVOID (meal) — mention it only to steer away
```

## 7. "Keeps coming up" (R8, conversation half)

`tools/capture.py`'s `place` kind gains `"name"` (the place's own name as the user said it).
A place fact whose name matches no saved place (name, aliases, close match ≥ 0.85) is counted in
`capture/place_mentions_unsaved.json`. At 3 in 30 days → a held offer raised as a card
(`tools/confirm.py` action `save_place`) at the next real user turn, announced by a line in the
block. Yes → a place (geocoded), mentions carried over; no → `hidden`; ignored → expires, counts
as neither, re-offered when the count doubles.

## 8. Unseen-cost guards

1. A missing `GOOGLE_PLACES_API_KEY` logs a warning once per process and is counted in the
   analytics row (`places_lookup_no_key`).
2. The analytics row carries `places_raised` and `places_saved` per day — counts only, no names —
   so "never fires" is distinguishable from "nothing nearby".

## 9. Files

| Tier | Files |
|---|---|
| Amber/Green, built here | `config/data_objects/places.yaml`, `config/modules/data_objects.yaml` (place limits), `tools/saved_places.py` (new), `tools/location.py`, `tools/places.py` (3-result lookup), `tools/data_objects.py` (guarded fields, `places` model-write refusal, occasion kinds), `tools/diarist.py` (the refusal through `write_archive`), `tools/day_plan.py`, `tools/obligations.py`, `tools/capture.py`, `tools/confirm.py`, `tools/analytics.py`, `core/orchestrator.py`, `ROADMAP.md` § A8, tests |
| Agent files, with Mike line by line, never delegated | `config/agents/coordinator.md` (`PLACES`), `config/agents/synthesizer.md` (raising a place, naming an avoided one, a changed verdict) |
| Denied — Mike runs | M3 on the VM: `scripts/seed_places.py` (tracked; reads real names from an untracked file) |
| Unchanged | `routing.yaml`, `routing_cloud.yaml`, `zones.yaml` and `append_zone` |

**A8:** `_resolve_places()` and `_places_block()` stay in `core/orchestrator.py` beside
`_resolve_data_objects()` / `_data_object_block()`; the logic lives in `tools/saved_places.py`.

## 10. Tests (stub Places, the extractor, FCM, CalDAV)

`tests/test_places_phase3.py`: (1) `zone_for` matches a place; (2) `_start_point` resolves a place
arrived at today, travel measured from it; (3) the obligations `zone` check accepts a place name;
(4) `location_last.json` one row, overwritten, rounded; (5) no coordinate in any prompt-bound
string (the block, `read_data_object`, the card, the capture note, the Coordinator directive
echo); (6) `places_near` filters by occasion and `private`, returns avoid-places, no `try` on a
walk; (7) a declined raise waits for a verdict/occasion change; (8) an ambiguous name saves
`confirmed: false`; (9) three mentions raise the card once, a decline leaves it `hidden`; (10) a
task's place joins in code; plus (11) the guarded-field rule, (12) model writes into `places`
refused, (13) a persona's own occasion kind is added, not mapped.

Regression: `tests/test_data_objects.py`, the capture suite, the day-plan suites,
`tests/test_zone_suggestion.py`, `tests/run_knowledge_routing.py --persona danny_park` (live),
`scripts/check_agent_tools.py`, `bash scripts/qa_sweep.sh`.
