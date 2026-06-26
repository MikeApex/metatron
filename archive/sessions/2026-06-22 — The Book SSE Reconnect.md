# 2026-06-22 — The Book: SSE Auto-Reconnect

## What was built

**SSE auto-reconnect** (`tools/metatron_monitor.py`)

The `_sse_loop` previously exited permanently on any connection failure, requiring the user to re-select the persona to resume live updates.

Fix: wrapped the connection attempt in a `while True` loop with exponential backoff.

- On successful connection: resets retry delay to 2s, sets status to `● live`
- On any exception: shows `SSE reconnecting in Ns…`, waits, doubles delay (cap 30s)
- On `CancelledError` (intentional shutdown via `l` toggle or quit): `return` immediately — no retry

Column 1 now updates in real time as new conversations arrive, without requiring re-entry of the profile.

## Commit

`23db629` — SSE loop: auto-reconnect with exponential backoff (2s→30s) on disconnect
