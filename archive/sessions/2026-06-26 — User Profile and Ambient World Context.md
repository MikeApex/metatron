# Session: User Profile and Ambient World Context
*2026-06-26*

## What was built

### `config/profile.yaml` (new)
Stable biographical profile injected into Synthesizer and Coordinator context. Sensitive-tier — loaded only into local-routed agents, never sent to cloud models. Fields: name, home location (city/country/timezone), age or birth_year (auto-computed), occupation, household, health_notes, free-form other list. Filled in for Mike: name Mike, London, United Kingdom, Europe/London. Age/occupation/household left for user to fill in.

Also includes an `ambient:` block with a `markets: true` flag that gates whether financial indices are fetched during ambient refresh.

### `tools/ambient.py` (new)
Three-hour ambient context refresh. Two entry points:

- `refresh_ambient_context()` — called by the scheduler; fetches weather (wttr.in), headlines (BBC + CNN RSS interleaved), and optionally market indices (Yahoo Finance v8 chart endpoint). Writes to `data/ambient_context.json`.
- `load_ambient_context()` — called at context build time; reads the JSON and formats it as a `## Current Context` system-prompt section. Date/time is always live from the system clock (never stale), regardless of when the file was last refreshed.

Weather requires `location.city` to be set in profile.yaml. Markets require `ambient.markets: true`.

**Technical note:** Yahoo Finance v7 quote endpoint now returns 401 (behind auth). v8 chart endpoint (`/v8/finance/chart/{symbol}?range=2d`) is still open. Uses `chartPreviousClose` to compute change percentage. Fetches 7 symbols in parallel via ThreadPoolExecutor: S&P 500, FTSE 100, DAX, Nikkei, Hang Seng, Gold, WTI Oil. Results sorted back to a fixed display order.

Headlines interleave BBC and CNN (4 from each, 8 total). CNN RSS: `http://rss.cnn.com/rss/edition.rss`.

### `core/orchestrator.py` (modified)
- Added `load_profile()` — reads `config/profile.yaml`, formats non-null fields as a `## User Profile` section. Falls back to main profile.yaml if a persona-specific one doesn't exist.
- `load_config()` — profile now appended after goals (both persona and non-persona paths).
- Coordinator path in `_run_single_agent()` — profile injected into system prompt alongside goals. Previously Coordinator had no biographical context.
- `load_recent_context()` — ambient context prepended as the first section, so both Coordinator and Synthesizer always see current date/time and world context.

### `core/scheduler.py` (modified)
Added `function:` job type support. When a job has `function: module.path.fn_name` instead of `agent:`, the scheduler calls the Python function directly (no LLM session). Implemented via `fire_function()`. This is a general mechanism — any maintenance job that doesn't need a model can use it.

### `config/modules/scheduler.yaml` (modified)
Added `ambient_refresh` job: `interval_minutes: 180`, `function: tools.ambient.refresh_ambient_context`, `notification: false`.

## Decisions made

- **Profile in main `config/profile.yaml`, not persona subdirectory** — the scheduler runs without a persona arg, so ambient.py reads the main file. The server runs with `--persona mike`, but `load_profile()` already falls back to the main file if no persona-specific one exists. Main config is the canonical location for the real user.
- **Markets gated on profile flag, not hardcoded** — `ambient.markets: true` in profile.yaml controls whether market fetch runs. Other users' profiles default to no markets without needing code changes.
- **Date/time always live from system clock** — the ambient JSON stores weather and news (which need network fetching), but date/time is never cached. `load_ambient_context()` calls `datetime.now()` every time, so Synthesizer always sees the correct time regardless of refresh staleness.
- **BBC + CNN interleaved** — gives both UK/global perspective (BBC) and US perspective (CNN). 4 headlines each, interleaved alternately.

## Deferred / not built

- Per-persona profile.yaml files in `config/personas/*/` — not needed yet; the main file covers production. Would be needed if multiple real users shared one instance.
- Additional news sources (e.g. Reuters, FT) — easy to add later via the same `_fetch_rss_headlines()` helper.
- User-editable profile via conversation ("set my age to 45") — the `write_config` tool exists and could be wired to profile.yaml, but not done this session.
- Market data for non-market-hours periods (weekends, after-hours) — currently shows last known prices; no special handling.
