# A2 — Logging Layer
*Session: 2026-06-13*

## What this session builds

Roadmap item A2 from `archive/plans/phase5_to_future_roadmap_2026-06-10.md`. Adds the quality event logging layer that underlies the self-improvement protocol (Stage 1).

---

## Changes made

### `tools/logger.py`
- Added `write_quality_event()` function — appends timestamped quality events to `data/logs/quality_events.json` (JSON Lines, one event per line)
- Added `WRITE_QUALITY_EVENT_SCHEMA` for orchestrator registration
- Reuses the existing threading-lock pattern from `write_log`
- Event fields: `timestamp`, `session_id`, `event_type`, `source_agent`, `detail`
- Supported event types: `ROUTING_MISS`, `USER_CORRECTION` (extensible)

### `config/agents/synthesizer.md`
- Added explicit instruction: when a `ROUTING_MISS` is detected (signal in the original message that no specialist surfaced), call `write_quality_event` with event_type `ROUTING_MISS`, source_agent = whichever specialist should have caught it, detail = brief description of the missed signal
- Wired alongside the existing context tracker flag (both happen)

### `config/agents/coordinator.md`
- Added implicit correction detection: when the user's message re-states or directly corrects a prior turn ("no, I meant…", "actually…", "wait, that's not right", "that's not what I said", etc.), call `write_quality_event` with event_type `USER_CORRECTION`, source_agent `coordinator`, detail = what the user corrected

### `static/index.html`
- Added a quiet "missed the mark" tap affordance: a small `·` that appears below each assistant message after it renders
- No label, no rating system, no visible methodology (discretion principle)
- Tapping POSTs to `/feedback` and fades the dot

### `core/server.py`
- Added `/feedback` POST endpoint — receives tap from PWA and writes a `USER_CORRECTION` event to `quality_events.json` directly (no orchestrator round-trip needed)

### `core/orchestrator.py`
- Appended `write_quality_event` import and registration to `register_tools()` (last step, file re-read immediately before edit)

---

## Test criteria (from roadmap A2)

1. Run a session containing a correction turn ("no, I meant..."). Verify `USER_CORRECTION` entry in `quality_events.json` with timestamp and session_id.
2. Run a session where Synthesizer skips a specialist whose domain is clearly present. Verify `ROUTING_MISS` entry logged with source_agent and detail.

---

## Test criteria placed for Alpha launch
A2 tests require live model sessions and cannot be run in development. Added to `tests/phase5_testing_plan.md` → **Known gaps (carry forward)** with three explicit pass/fail checks (Coordinator correction detection, Synthesizer routing miss detection, PWA tap). All verify against `data/logs/quality_events.json`.

## Deferred / not in scope
- Reading or querying quality_events.json — Stage 2 (Observer Agent, Phase 6+)
- Any UI that surfaces quality data to the user
