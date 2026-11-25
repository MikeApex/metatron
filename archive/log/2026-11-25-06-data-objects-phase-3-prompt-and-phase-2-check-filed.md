### 2026-11-25, sixth (the user's own data: phase 3 Places prompt written, set up to move the build through phases 4 and 5 on its own; phase 2's one-week check filed) — no code; this close-out commit only, nothing to deploy

**Incoming handoff:** unchanged from § 11-25 fifth. Mike asked whether the data-objects build
was finished, "including the places phase".

**What was found, checked against code and not taken from the primer:** phases 1–2 of
`archive/plans/custom_logs_and_places_plan_2026-11-21.md` are live. Phases 3 (Places),
4 (background location) and 5 (Pattern Miner) are unbuilt. None of phase 3's names (`known_places`,
`places_near`, `location_last`) exist anywhere in `core/`, `tools/` or `config/`. The existing
`tools/places.py` is the 08-26 venue lookup (opening hours, `geocode_place_name`), which phase 3
builds on. It is not phase 3 work.

**Decisions (Mike):**
- **Phase 3 proceeds without phase 2's one-week check.** Plan § 5 makes each phase leave the next
  optional, and phase 3 serves the plan's second need (places), not the first (logs). The one link
  is that phase 3's "a place you keep mentioning" question asks the same way phase 2's noticed-list
  card does, so a low phase 2 yes rate becomes a tuning input after the build. It doesn't block it.
- **The check is filed as `[DB-1125-01]`**, due 12-02, in Later, Done and deployed. Before today it
  lived only on the `SESSION.md` "Owed" line, which is rewritten at every archive. That is the
  "recorded only in a narrative" loss the global rules warn about.
- **The prompt moves the build forward on its own.** The phase 3 close writes the phase 4 prompt
  and hands Mike its link. Phase 4's close writes phase 5's prompt. Phase 5's close marks plan § 5
  complete and says the data-objects build is finished.

**The phase 3 prompt:** `archive/handoffs/2026-11-25-data-objects-phase-3-places-build-prompt.md`
(Opus 5.5, high). It builds the places object, lookup by name, places in `zone_for`,
`known_places()` with all three readers switched to it (the day planner's start point is the user
impact), `location_last.json`, code-only `places_near` with avoid-places and mention memory,
recurring conversation places, task → place, and the `location.py` docstring amendment. It puts
four plan's choices to Mike before building: an ambiguous name, how `places_near` reaches the
Synthesizer, the keeps-coming-up threshold, and the unchecked Places API price, which he reads at
M3 because WebFetch is Denied.

**Rejected:**
- Starting phase 4 straight after phase 3 without a gate. The plan builds phase 4 against the
  Android tree only after WhatsApp's work lands. The phase 4 prompt checks that first (WhatsApp
  Phase 2 walkthrough through M4) and stops if it isn't met.
- Mike's real venue names in the prompt's tests. Under the no-real-details rule, invented names
  go in code and tests, and the real places exist only in persona data, seeded by M3.

**Wrong earlier:** nothing new. `SESSION.md` already said "phase 3, Places (no prompt yet)"
correctly. The gap was that phase 2's owed check had no backlog home.

**Outgoing:** next for the data-objects build is the phase 3 prompt above, which can run in a fresh
chat now. `[DB-1125-01]` is read on the VM from 12-02.

