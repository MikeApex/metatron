# 2026-06-26 — The Book: Load Menu, Ordering, and SSE Backfill Fix

## What was built / changed

### 1. Load menu: Max entries changed from Input to Select

**Problem:** The `Input` widget for max entries was not editable in practice. User wanted a dropdown.

**Fix (`tools/metatron_monitor.py`):**
- Replaced `Input("10", id="limit-input")` with `Select([(10, 20, 50, All)], id="limit-select")`.
- CSS updated: `#limit-input` → `#limit-select`, width 6 → 10.
- `load_btn_pressed` updated to read from `#limit-select` instead of `#limit-input`.
- `_limit = 0` now means "All" — no `limit` param sent to server.
- `limit_submitted` handler (Input.Submitted on the old input) removed.

### 2. SSE backfill destroying ordering and defeating filter

**Root cause (the actual bug):** The `/monitor/stream` SSE endpoint replays all trace lines from the beginning of the file on every new connection (`seen = {}`). After `load_data()` returns 10 filtered entries via HTTP, the SSE loop connects and immediately dumps all historical traces. The client dedup check (`if not any(...)`) only blocked traces already in the 10 HTTP-loaded entries — everything older slipped through and was prepended to the top of Column 1. Result: old conversations appeared randomly at the top, destroying ordering, and making the filter look like it had done nothing.

**Fix — server (`core/server.py`):**
- `/monitor/stream` now accepts a `since` query param (ISO datetime string).
- On the initial scan only (`first_pass = True`), traces older than `since_dt` are skipped (not emitted). Their file positions are still counted so they are not re-sent later. After the first pass, all new traces are emitted normally.

**Fix — monitor (`tools/metatron_monitor.py`):**
- `self._sse_since: str = ""` added to `__init__`.
- At the top of `load_data()`, `self._sse_since = datetime.now().isoformat()` is recorded before the HTTP fetch.
- `_sse_loop()` now takes a `since: str` argument and passes it to the SSE endpoint as `?since=...`.
- `load_data()` passes `self._sse_since` when starting the SSE worker.

### 3. Deploy workflow fix

**Problem:** Changes from the previous session were never committed. `deploy.sh` is a git-push-based deploy; uncommitted changes are silently not deployed. This meant the VM was running old code with no `since`/`limit` support on `/monitor/conversations` and `/monitor/traces`, making the filter appear broken.

**Lesson recorded in memory:** After any change, check whether it needs committing + deploying; note which files go to VM vs. run locally.

### 4. Client-side sort as defensive measure

`_populate_col1()` now sorts `self.conversations` by `ts` descending before rendering, so ordering is correct even if the server sends data in a different order.

## Root cause summary

Three compounding issues:
1. Changes weren't committed → VM didn't have `since`/`limit` filtering → all conversations returned regardless of filter settings.
2. After deploy, the SSE backfill bug caused old conversations to prepend to the top, making the filter look broken even after it was fixed.
3. The `Input` widget for max entries was not usable; replaced with a `Select` dropdown.

## Decisions made

- SSE `since` cutoff is set at `load_data()` start time (not at SSE connect time). This means any conversation that started after the HTTP fetch but before SSE connects could be missed in a race, but this is an acceptable edge case for a single-user tool.
- "All" in the Max dropdown maps to `_limit = 0` → no `limit` param sent → server returns everything.

## Deferred

- Nothing new deferred. Existing deferrals unchanged.
