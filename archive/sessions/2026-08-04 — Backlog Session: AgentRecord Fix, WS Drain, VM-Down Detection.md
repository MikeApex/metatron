# 2026-08-04 — Backlog Session: AgentRecord Fix, WS Drain, VM-Down Detection

**Ask:** pick the most pressing `DEV_BACKLOG.md` items completable in one session.

**Method:** three Explore agents re-verified the strongest candidates against live code before
picking (per the standing verify-before-refile rule). Result: 2 real bugs with confirmed root
causes, 2 already-fixed entries that just never got closed.

---

## Built / fixed

- **`[DB-0803-02]` — proactive check-ins were failing outright.** Root cause:
  `core/router.py:166`, `log_model_error()` was handed a live `AgentRecord` object instead of a
  string at three call sites in `core/orchestrator.py` (:1575, :1676, :1881), because
  `get_current_agent() or "unknown"` short-circuits on the truthy record. `json.dump` then
  crashed, masking the real underlying model failure. One-line fix:
  `"agent": agent.agent if hasattr(agent, "agent") else agent,`.
  Killed `companion_checkin` (×13), `evening_close`, `morning_brief`, `plant_watering_check` —
  18 of 19 scheduler errors in 7 days.

- **`[DB-0803-07]` — deploy.sh's drain gate was decorative.** `/active` only counted the SSE
  path's `_active_streams`; the app talks over WebSocket, which never touched it, so deploys
  always restarted immediately regardless of in-flight conversations. Fixed: WS exchange block
  now holds the same `_active_lock`, counting exchanges not connections.
  **Caught in local testing, not review:** first draft crashed with `UnboundLocalError` —
  needed `global _active_streams` inside `websocket_endpoint()`, same as the SSE generator
  already has. Found by actually running a WS exchange against a local server, not by reading
  the diff.

- **`scripts/sync_dev_backlog.py` — VM running-but-unreachable now distinguishable from
  stopped.** Added `vm_status()` (gcloud instance describe, called only when `fetch_events()`
  already returned empty), folds `⚠ VM running but unreachable` into the one-line session-start
  report.

## Closed, no code needed

- Stale: `synthesizer.md` promising `write_config` for `scheduler.yaml` — superseded by
  `write_schedule` et al. since the 2026-08-03 Phase 4 session.
- Stale: `/metatron-troubleshoot` pre-persona-scoping paths — already fixed by `a763628`.

## Deploy

`10bf194` pushed and deployed — verified HEAD match. As a side effect of the fast-forward, this
also deployed the previously-pending `9361537`→`8ee150f` chain from the 2026-08-05
backlog-trust-repair session, resolving that session's own *"needs `./deploy.sh`"* note.

## Verification chase

Rather than stop at "deploy succeeded," reproduced the exact crashing call on the live VM: real
`RequestTrace`/`AgentRecord` via `core.trace`, then `log_model_error()` with it — same object
type, same code path that was killing the scheduled jobs. No crash; log entry correctly read
`"agent": "coordinator"`. Deleted the synthetic entry from `data/diagnostics/model_errors.json`
afterward.

**Not yet confirmed:** a real scheduled fire completing end-to-end under genuine model-call
variance (only the crash path has been proven dead, not a live success). Filed as
**`[DB-0804-01]`** — three time-gated checks (companion_checkin ~23:03 BST tonight,
morning_brief 07:30 BST tomorrow, one-week error count on 2026-08-11), each with the exact
command and pass condition, deliberately not to be run early.

Rejected: waiting live in-session for the natural fire (too slow); `ScheduleWakeup` (scoped to
`/loop` dynamic pacing, not a general-purpose timer — wrong tool for a one-off wait).

`ec55788` — closes `[DB-0803-02]` with the fix/verification evidence, files `[DB-0804-01]`.
Docs-only, pushed, no deploy needed.

## Deferred / not touched this session

`DB-0803-01` (text doubling, unverified), `DB-0803-03` (memory indexer wrong source),
`DB-0803-06` (`shownIds` eviction, stale line refs), B1/B2 security work, SMTP first-send test.
