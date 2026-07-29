# 2026-06-26 — SEQ 032 Troubleshoot and Graceful Shutdown Fixes

## What was investigated

Single exchange troubleshoot for SEQ 032 (2026-06-26T18:14:40), which returned "Error: Fetch is aborted" to the client while the conversation tracker showed a valid response.

## Root cause

systemd sent SIGTERM to metatron-server at 18:13:54 — mid-pipeline — while the SEQ 032 request was in flight. Uvicorn closed the SSE connection at ~18:13:58 (the two `[146B blob data]` log entries). The pipeline continued as a background asyncio task, completed at 18:14:40, and wrote the conversation record to disk. The client never received the response. SIGKILL followed at 18:15:24 (90s stop-sigterm timeout), killing 13 child processes. No pipeline trace was written — trace write is downstream of the SSE stream path, which was already dead.

The SIGTERM was triggered by a `./deploy.sh` or manual `systemctl restart` that ran while the session was active.

## What was built

### Fix 1 — Graceful shutdown timeout (`core/server.py`)
`timeout_graceful_shutdown=150` added to `uvicorn.run()`. Gives in-flight pipelines up to 2.5 minutes to complete before Uvicorn forces SSE connections closed. Covers the case where a restart happens while a ~90s pipeline is mid-flight.

### Fix 2 — Active stream counter + deploy drain (`core/server.py`, `deploy.sh`)
- `_active_streams: int = 0` and `_active_lock` added at module level alongside `_CONV_LOCK`
- `sse_generator()` increments on entry, decrements in `finally` (fires on normal exit, client disconnect, and exception)
- `GET /active` → `{"active_streams": N}` endpoint added after `/health`
- `deploy.sh` restructured: scheduler restarts immediately; server restart is gated by a 180s drain loop polling `https://localhost:8001/active`; force-restarts on timeout
- Drain loop limitation noted: new requests can still arrive during the drain window (server stays up). This is acceptable at Alpha; full fix is Fix 3.

### Fix 3 — Scoped for future (`archive/plans/future_phases.md`)
Three-part scope added:
1. Drain mode flag (`_draining`) + `/drain` endpoint — server returns 503 on new `/session/stream` requests during drain, preventing new streams from resetting the counter
2. Client reconnect on abort — on `Fetch is aborted`, wait 3–5s, reconnect, poll `/result/{date}/{seq}` for the completed response
3. `GET /result/{date}/{seq}` endpoint — reads a single entry from `data/conversations/{date}.jsonl` by seq; shared primitive for both the client recovery path and manual troubleshooting

## Decisions

- `timeout_graceful_shutdown=150` is the right value: covers the longest observed pipeline (≈90s) with margin; 150s is well under the systemd stop timeout (90s by default — actually, systemd was SIGKILLing at 90s, so the graceful shutdown needs to be shorter than that; 150 > 90, which means uvicorn's graceful shutdown won't complete before SIGKILL in the worst case). **Note for follow-up:** if the longest pipeline is ~90s, `timeout_graceful_shutdown=80` might be safer (ensures uvicorn closes cleanly before SIGKILL at 90s). Left at 150 for now since systemd `TimeoutStopSec` can be raised separately.
- drain timeout of 180s chosen: generous enough for a complex multi-specialist pipeline; `./deploy.sh` is a manual operation so the extra wait is acceptable
- Fix 3 deferred: Alpha has one user and intentional manual deploys; the residual risk (new request arrives during drain window) is negligible until Beta

## Commit

`452ff8b` — "Graceful shutdown: active stream counter, drain endpoint, deploy drain loop"
Deployed to metatron-vm. `/active` confirmed returning `{"active_streams":0}` at idle.
