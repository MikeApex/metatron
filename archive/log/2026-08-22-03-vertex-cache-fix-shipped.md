### 2026-08-22 (Vertex cache fix built, deployed, and half-proven — Steps 1–4 shipped, 5 partially closed, 6 filed)

**The cache cost plan (`archive/plans/vertex_cache_cost_control_2026-08-20_plan.md`) is now
deployed**: sliding 10-minute TTL refreshed lazily after the response, ownership-tagged caches
(`metatron:{host}:{role}`, no PID) with an own-identity startup sweep and `atexit` trim,
`spend_guard` charging cache storage at grant time and pricing cached reads at the cached rate
via new `tokens_cached` plumbing, and a `VERTEX_CACHE_DISABLED` kill switch (set in the Mac's
`.env`, verified live). Commits `9de2836` (main build, 8 files) and `e5d5037` (reconcile-script
fix) — **both deployed** by Mike on 08-21 ~00:30 UTC. The 9 pre-TTL caches were swept by hand
(`scripts/vertex_cache_admin.py --delete-all`); the project sat at 0 caches mid-morning on
08-22, which is itself evidence the TTL reaps — old code would have left midnight-expiry caches
visible all day.

**Deviations from the Fable plan, both deliberate:** the sweep deletes own-identity caches with
under 5 minutes left, not "within one TTL of now" — under a sliding TTL a live cache is *always*
within one TTL, so the literal rule deletes a same-identity peer's working cache; decayed-below-
the-refresh-margin is the only signal separating a live owner from a dead one. And the sweep
hangs off the native-client singleton on a background thread rather than per-service startup
hooks, keeping every cache concern inside the `_vertex_*` helpers for the A8 move.

**Wrong earlier, corrected in-session (the corrections are the story):**
- **Step 6's first analysis charged cache creation once per session and recommended skipping
  the build. Mike caught it** ("they'll be invoked more than once once they're invoked"):
  `physical_health` = 74 invocations, **10** creations under a 10-min TTL. Amortised, MW+PH are
  worth ~+$0.17/day — more than the deployed head-layer caching earns — and the creation-SKU
  question moves the answer by $0.004/day, i.e. it no longer gates the build. The revised doc
  (`archive/plans/vertex_cache_step6_specialist_caching_2026-08-21.md`) also retracts its claim
  that the plan's 8-turn premise was optimistic — it was *conservative* (24 turns/creation
  measured), and the plan's "positive regardless" conclusion was right all along. Lesson filed
  in the doc: both versions used identical correct rates; one line of clustering arithmetic
  inverted the recommendation.
- **"The pre-TTL caches will self-expire at midnight — deleting is optional"** — they were
  alive at 00:25 with expiry pushed to ~01:00; the manual delete was necessary.
- **"The billing export is not retroactive"** — the resource-level export backfilled to
  June 30.
- The test suite initially wrote ~$0.07 of fake storage into the real spend state (fixed to
  intercept the accrual), and later broke on any machine with the kill switch in `.env`
  (fixed to clear/restore the env var). `rows` is a BigQuery reserved word (`e5d5037`).
- Three specialist prompts sit UNDER the 4,096-token cache floor — the first claim that all
  cleared it measured first-turn input (which includes the Coordinator directive), not the
  cacheable prefix. `physical_health` cached would be 40% padding.

**Step 5 half-closed from the export's backfill:** storage billed **$19.59 against $1.53 of
cached reads since June 30** — caching was net-negative for its whole life, not just the
reconciled days. Storage rates confirmed exact against the SKU catalogue ($4.50 and $1.00 /1M/hr;
cached reads $0.20 and $0.025/M). Export rows end at 08-14, so the creation SKU, refresh
metering, and the under-1.2× closing pass wait for the 08-20/21 rows.

**Everything remaining is one time-gated item: `[DB-0822-01]`** (`due: 2026-08-25`) — (a) run
`scripts/vertex_cost_reconcile.py` when the export passes 08-21, producing the clean-day
evidence `[DB-0820-01]`'s cap revert needs; (b) Step 6 Pro half (one line at
`orchestrator.py:4019`) gated on a full A4 run, since it moves the two clinical-flag agents onto
the native loop. Fable review of the deployed build found three minor, non-blocking items
(registry lock held across network calls; abandoned streams skip the refresh; role detection
keyed on entry-point filename) — noted, none filed.

