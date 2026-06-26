# 2026-06-26 — The Book: Call Timing, Token Counts, Load Menu, and Server Fixes

## What was built / changed

### 1. Tool call timing (0ms → float precision)

**Problem:** Tool calls like `write_context_tracker` showed `duration_ms=0` because `int((time.monotonic() - t0) * 1000)` truncates sub-millisecond operations.

**Fix (`core/orchestrator.py` — `dispatch_tool`):**
- Changed `int(...)` → `round(..., 1)` for `duration_ms`.
- `ToolCallRecord.duration_ms` type changed from `int` to `float` (`core/trace.py`).
- The Book (`tools/metatron_monitor.py`) now formats all durations as `:.1f` (e.g. `0.3ms`, `2341.0ms`).

### 2. Token counts per tool call

**Problem:** `ToolCallRecord` had no token fields — token counts were only available at the turn level.

**Changes (`core/trace.py`):**
- Added `input_tokens: int = 0` and `output_tokens: int = 0` to `ToolCallRecord`.
- Both fields serialized to JSONL.
- `record_tool_call()` accepts optional `input_tokens`/`output_tokens` params.

**For `run_subagent` calls (`core/orchestrator.py` — `dispatch_tool`):**
- After a `run_subagent` call completes, `dispatch_tool` looks up the just-created subagent `AgentRecord` in the trace and copies its total tokens into the `ToolCallRecord`.
- The Book Column 3 now shows `→ diarist  1,234in/56out  2,341.0ms` on the collapsible title.
- Regular tool calls show tokens only if non-zero.

### 3. `run_subagent` calls not recorded in Gemini native parallel path

**Problem:** The Coordinator uses `_run_gemini_native_loop`. `run_subagent` is in `_PARALLEL_TOOLS`, dispatched via `ThreadPoolExecutor` — but the Gemini native path did NOT propagate thread-local trace context (`set_trace`, `_set_current_agent`). Worker threads had `rec = None` → `record_tool_call(None, ...)` → early return → no ToolCallRecord created, no subagent record nested.

**Fix (`core/orchestrator.py` — `_run_gemini_native_loop` parallel branch):**
- Now captures `_parent_trace` and `_parent_agent` before the executor.
- Worker closure sets both thread-locals before calling `dispatch_tool`.
- Matches the pattern already in the Anthropic parallel path.
- Also fixed sequential Gemini native path to pass `_turn_num=turn_num` to `dispatch_tool` (was always defaulting to 1).

### 4. Server blocking event loop during pipeline run

**Problem:** `session_stream` iterated `run_pipeline_session_stream` (a sync generator) directly inside `async def sse_generator()`. This blocked the entire uvicorn event loop for 10–30s — no other requests (including `/monitor/personas`) could be served while a query was in flight. `/session` (non-streaming) had the same bug.

**Fix (`core/server.py`):**
- `session_stream`: Moved generator iteration to a thread pool via `loop.run_in_executor(None, _produce)`. The `_produce` function pushes each chunk to an `asyncio.Queue` via `run_coroutine_threadsafe`. The async SSE generator pulls from the queue without blocking the event loop.
- `/session`: Wrapped `run_session(...)` in `await loop.run_in_executor(None, lambda: ...)`.
- `import asyncio` added to server.py imports.

**Latency impact:** None. Generator runs in a pool thread identically to before; the queue round-trip (sub-ms) is invisible against LLM latency.

### 5. Personas not loading on launch (retry logic)

**Problem:** `load_personas()` made a single attempt; if the server wasn't ready at launch, it failed silently with no retry.

**Fix (`tools/metatron_monitor.py`):**
- `load_personas()` now retries up to 4 times with exponential backoff (2s, 4s, 8s delays).
- On total failure: status bar shows "Cannot reach server. Press R to retry."
- `action_refresh` (R key) now calls `load_personas()` when no persona is selected (previously a no-op).

### 6. Freezing on persona switch (SSE race condition)

**Problem:** `load_data()` cancelled the old SSE worker *after* HTTP requests completed. During those requests, the old SSE worker was still live, appending old-persona messages to `self.conversations` and Column 1 while `load_data` was clearing and repopulating — a race that put the UI in a broken state.

**Fix (`tools/metatron_monitor.py`):**
- Moved SSE worker cancel to the *top* of `load_data()`, before HTTP requests.
- Set `self._sse_worker = None` immediately after cancel to prevent double-cancel.
- Reduced `load_data()` HTTP timeout from 30s to 15s.

### 7. Load menu and most-recent-first ordering

**Server (`core/server.py`):**
- `/monitor/conversations` now accepts `since` (ISO datetime string) and `limit` (int). Filters by timestamp, sorts descending, slices to limit.
- `/monitor/traces` same. When `trace_id` is specified, `since`/`limit` are ignored.

**Monitor UI (`tools/metatron_monitor.py`):**
- Added `#load-bar` row below toolbar: `Range: [Last 24h ▼]  Max: [10]  [Load]`
- Range presets: Last 1h / 6h / 24h / 7d / 30d / All time. Default: 24h, 10 messages.
- `_range_hours: int = 24` and `_limit: int = 10` added to `__init__`.
- Load button reads controls, updates state, triggers `load_data()`.
- Enter on the Max input triggers Load.
- `load_data()` computes `since` from `_range_hours` and passes `limit` in query params.
- `_populate_col1` changed to `scroll_home` (newest-first from server → top of list).
- `_append_col1` replaced with `_prepend_col1`: SSE live messages mount before `lst.children[0]` so new arrivals appear at the top.

## Decisions made

- Float precision for tool durations (`round(..., 1)`) rather than microseconds — avoids data model churn while showing sub-ms values.
- Token counts on `run_subagent` titles are read from the subagent `AgentRecord` at dispatch time (UI + trace layer approach), not via a return-value protocol from the tool itself.
- Load menu uses explicit Load button rather than auto-triggering on change — more predictable given that range + limit are two separate controls.

## Deferred

- `_SUBAGENT_DEPTH` env var is process-wide and mutated by parallel `run_subagent` threads — potential race if Coordinator dispatches two subagents simultaneously. Deferred; single-user single-pipeline in practice.
- A8 (full orchestrator refactor) remains next after A7 sign-off.
