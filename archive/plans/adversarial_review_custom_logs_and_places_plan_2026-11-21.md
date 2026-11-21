Plan reviewed: archive/plans/custom_logs_and_places_plan_2026-11-21.md
Reviewer: adversarial-reviewer on Fable, effort medium, 2026-11-21

## STRUCTURAL

1. [§ 3.1 templates, § 3.2, § 3.3] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/diarist.py:write_archive]
Wrong: The plan says categories without a registry entry behave as today "so the ~15 agents already writing the archive are unaffected", but its own templates register `films`, `books`, `music` and `places` for every user from day one, which are exactly the categories those agents write.
Fails: `write_archive` today merges a same-title row (the documented case is a book filed at mention and again at completion), so under `thing+occurrences` that second ungated call becomes a second reading or viewing, and the existing flat rows in `places.json`/`films.json` have no stated conversion.
Costs: Wrong counts and wrong occurrences accumulate in a store the plan rules is never deleted from, starting the day phase 1 ships, from agents whose instructions were not changed — high.

2. [§ 3.7 `places_near` and unnamed spots, § 3.8 feed 2, R24] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/location.py:record_position]
Wrong: `places_near(where = "the last report")` and the 10-minute dwell both need the user's coordinate to outlive one `record_position()` call, and R24 "in exactly these terms" permits storing only a rounded point for a recurring spot after the minimum stay.
Fails: `record_position()` discards the coordinate with its frame and the transitions log holds only `(zone, entered_at)`, so when the user is `away` there is nothing to measure distance from, and a stay cannot be timed without holding the arrival coordinate (in memory, lost on every restart or deploy, or on disk before the stay is proven).
Costs: The build either stores a position the amended ruling does not allow or ships proximity and unnamed-spot detection that silently never fire — high.

3. [§ 3.4 "Asked for", § 3.3 pending marker, R15] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/subagent.py:run_subagent]
Wrong: The reply says "I've started a heart log" / "added to the heart log" before the write exists, and the write is delegated to a bulk-tier model running fire-and-forget.
Fails: A Diarist run that fails, picks `write_archive` instead, or files to the wrong object is reported only by `logger.warning` at `subagent.py:136`, and the pending marker simply expires after 2 minutes with nothing telling the user or the next turn.
Costs: The user is told an entry was logged that was not, in the health log the plan names as its first real object, which R15 says must not happen — medium.

4. [§ 3.4 "Noticed" vs "Derived", § 5 phase 2, R15, R17] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/capture.py:raise_new_categories]
Wrong: The derived writer is held in shadow because the extractor invents values (87% precision), but the noticed-object path creates objects and files entries from the same extractor's `other` output with no gate and at a lower threshold (3, against today's 5 for a developer-only alert).
Fails: The `category` is a free label the extractor writes per fact and is grouped by exact string (the code already carries a volume alert for "categories the model names inconsistently"), and R17's "no reasonable home exists" bar is reduced to a lexical match of that label against object names.
Costs: Unwanted and duplicate objects get created and announced to the user, the failure Mike ranked as "must not happen" — high.

5. [§ 5 phases 1–2, § 3.4, § 3.5]
Wrong: Phase 1's live check ("start a log of …", add three entries, read it back) and its per-agent manifest consume the writer and the `relevant_agents` tagging, both of which are built in phase 2.
Fails: With no Diarist write path and no relevance call in phase 1, either the check cannot run or an unplanned direct-write grant is added to pass it, creating a second write path that § 3.4's latency and pending-marker design does not cover.
Costs: Phase 1 cannot "ship and be checked live" as stated, and the grants made to pass it (Red tier, with Mike) get made twice — high.

6. [§ 5 phases 3–4, § 3.7 unnamed spots, R8] [/Users/md-homefolder/Desktop/multi-model-mcp/core/server.py:location_ping]
Wrong: Unnamed-spot candidates and their question ship in phase 3, but the reports that could establish a stay and three visits arrive only from phase 4's background feed.
Fails: Today a position arrives only when the user sends a message with the ping on or taps share, so two reports ten minutes apart at the same unnamed point, three times, is a matter of chance.
Costs: Phase 3's unnamed-spot feature has no meaningful live check and looks dead until phase 4, contradicting "each phase leaves the next optional" — medium.

## LOCAL

7. [§ 3.1 "Reads go through the common read tool", § 3.3, R27] [/Users/md-homefolder/Desktop/multi-model-mcp/config/modules/routing_cloud.yaml:allowed_tools]
Wrong: `read_data_object` reaches contacts, goals, calendar, profile, every agent's config and the daily log through one grant, and the plan never says the tool enforces `relevant_agents` or the store's own read protections.
Fails: Any agent holding the tool can resolve an alias to a store its allowlist was written to exclude (and `dispatch_tool()` runs ungranted calls in the default warn mode), while calendar and contact content would bypass the `tools/untrusted.py` wrapping their own read tools apply.
Costs: The per-agent grant rulings and ROADMAP B2's cross-agent exfiltration test are undone by one tool — medium.

8. [§ 3.8 feed 1 and "Server", § 4 file list, R23] [/Users/md-homefolder/Desktop/multi-model-mcp/core/server.py:LocationPing; /Users/md-homefolder/Desktop/multi-model-mcp/core/consent.py:APP_SCOPES]
Wrong: The consent refusal is placed inside `record_position()`, but a geofence report of "entered Bianco 43" carries no coordinate and cannot pass through `LocationPing` (required `lat`/`lon`) or that function.
Fails: The geofence feed needs its own endpoint and its own gate, plus a way to push place coordinates to the phone, none of which are listed, and `core/consent.py` (`CURRENT_VERSIONS`, `APP_SCOPES`), where a `location_history` scope must be added for the app to grant it, is absent from § 4.
Costs: The cheaper of the two background feeds ships outside the fail-closed consent gate R23 requires "for every user, `mike` included" — high.

9. [§ 3.7 "Zones stay as they are"] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/day_plan.py:_start_point]
Wrong: Making `zone_for()` match places writes place names into the transitions log, and the plan lists no change to the day planner that reads it.
Fails: `_start_point()` resolves the current zone through `_zone_coords()`, which reads only `load_zones()`, so a user who arrived at a place today falls back silently to `home` as the day's starting point (`tools/obligations.py:2168` reads `load_zones()` the same way).
Costs: Travel times and "leave now" nudges are computed from home while the user is elsewhere, on a feature that is live with every switch on — high.

10. [§ 3.1 registry location, plan's choice] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/diarist.py:read_archive]
Wrong: `archive/_registry.json` sits in the folder where every filename is an archive category.
Fails: `read_archive("_registry")` returns it and `write_archive("_registry", …)` loads and rewrites it (or raises on a dict), from any of the roughly 15 agents holding those grants and from `core/build/manifest.py`'s `read_archive` source.
Costs: The registry every later phase depends on can be read or corrupted by an existing model-callable tool — medium.

## VERIFY — 2026-11-21 (same reviewer, Fable; plan revised with R33, R34 and fixes for 1–10)

1. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/diarist.py:write_archive] The `_identity` merge that absorbs a repeat write is kept for every category, occurrences now come only from an explicit `write_data_object` occurrence write, and flat rows are read as things with no conversion.
2. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/location.py:record_position] R33 is a new ruling permitting one overwritten rounded row, which `record_position()` can write before its frame ends, so `places_near` has a point to measure from when the zone is `away`; the dwell half moved, see NEW 2.
3. NEW SHAPE — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/subagent.py:run_subagent] The silent failure is gone (a post-thread check, one retry, a queued "didn't save" note), but the reply still says "added" before the write exists, the retry is the same bulk-tier model with the same instruction the Diarist already ran on, and the correction reaches the user only if they send another turn.
4. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/capture.py:raise_new_categories] R34 means no object is created without the user's yes, and the home check no longer rests on the label string; exact-string grouping still decides when the threshold of 3 trips, which now only under-detects.
5. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/config/modules/routing_cloud.yaml:diarist] Phase 1 now carries the Diarist write, relevance tagging and the Coordinator resolution its live check consumes, with the grants made once.
6. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/core/server.py:location_ping] Unnamed spots from location reports moved to phase 4 with the feed that supplies them, and phase 3 keeps only the conversation half, which capture's `place` facts can feed today.
7. NEW SHAPE — [/Users/md-homefolder/Desktop/multi-model-mcp/config/modules/routing_cloud.yaml:allowed_tools] The widening is closed for stores that have a read tool (`read_contact`, `read_calendar`, `read_goals`, `read_profile`, `read_log`, `list_tasks`, `read_wisdom`, `read_agent_config` all exist), but the rule now cuts the other way, see NEW 1.
8. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/core/consent.py:APP_SCOPES] The geofence feed gets its own endpoint, both endpoints and the geofence list share one consent check, and `core/consent.py` and `core/server.py` are now in § 4 with the scope added to `CURRENT_VERSIONS` and `APP_SCOPES`.
9. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/day_plan.py:_zone_coords] `known_places()` replaces `load_zones()` in `_zone_coords()`/`_start_point()` and at `tools/obligations.py:2168`, which are all the name-resolving readers outside `tools/location.py`, and test 4 pins the start point.
10. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/diarist.py:_archive_dir] The registry is now `data/personas/{p}/data_objects.json`, outside the folder `read_archive`/`write_archive` resolve categories in, and both refuse `_`-prefixed names.

## NEW

1. [§ 3.3 "The common read tool does not widen", § 3.9, R16] [/Users/md-homefolder/Desktop/multi-model-mcp/config/modules/routing_cloud.yaml:pattern_miner]
Wrong: § 3.9 still gives Pattern Miner "all user data" through the common read tool, but the new rule serves a store only to an agent already holding that store's own read tool, and it is undefined for stores that have none.
Fails: Pattern Miner's allowlist holds `read_wisdom` and no read tool for contacts, calendar, goals, profile, tasks or the archive, while places/zones and day shape have no model-callable read tool at all (`tools/location.py` registers nothing), so those stores are refused to every caller.
Costs: R16 is undelivered at phase 5 and the places object is unreadable through the tool built to read it, unless further Red grants the plan does not list are added — high.

2. [§ 3.7 "Unnamed spots", § 3.8 feed 2, R33] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/location.py:record_position]
Wrong: A candidate is written "only when two reports at the same rounded point span the minimum stay", but the background feed that supplies those reports fires on significant movement.
Fails: A stationary phone sends nothing, so the report that ends a stay comes from a different point, and two fixes at one real spot can round to adjacent ~100 m cells, so the same-point condition is met only by chance.
Costs: Unnamed-spot detection, moved to phase 4 to give it a feed, still rarely or never fires, and Mike's M5 walkthrough has no check that would show it — medium.

3. [§ 3.4 "Noticed — ASK", R34, § 5 phase 2] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/capture.py:raise_new_categories]
Wrong: "Yes → created; 'that's my X list' → alias; no → recorded and not offered again" states the hard part in one clause, with no named mechanism that ties the user's next-turn answer to the pending question or names the agent that acts on it.
Fails: The last question of this shape was recorded by matching signal words in the reply and missed when the Synthesizer phrased it its own way (SESSION.md, the redo question; fixed in `9ad7a6c`), and the yes rate R34 uses to switch to create-and-tell is computed from these same recordings.
Costs: Offers repeat or answers go unrecorded, and the measure Mike will use to turn on unasked creation is unreliable — medium.

## After verify — addressed in the plan, not re-verified (2026-11-21)

3 / NEW 1 / NEW 2 / NEW 3 were revised in the plan the same day (§ 3.3, § 3.4, § 3.7, § 3.9, § 9 M5).
They were not sent for a third round; the phase 1 diff review (Fable) re-checks 3, NEW 1 and NEW 3
against the built code, and the phase 4 diff review re-checks NEW 2.
