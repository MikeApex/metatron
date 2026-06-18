# A2 — Logging Layer (Phase 5 / D3)
*Open this in a new Claude Code session. Roadmap item A2 (2026-06-10 roadmap).*
*Parallel-safe: other chats are running simultaneously — see File ownership below.*

---

## Read these first, in order

1. `SESSION.md` — current state
2. `archive/plans/phase5_to_future_roadmap_2026-06-10.md` — Section 0 and item A2
3. `tools/logger.py` — existing log tool pattern (threading lock included)
4. `config/agents/synthesizer.md` and `config/agents/coordinator.md` — where the flag wiring lands
5. `static/index.html` and `core/server.py` — PWA surface for the tap

Do not begin until you've read all five.

---

## Build

1. `write_quality_event` tool → appends timestamped events to `data/logs/quality_events.json`. Follow the standard tool pattern (function + schema in `tools/`); include the same threading-lock protection as `write_log`. Events carry at minimum: timestamp, session_id, event_type, source_agent, detail.
2. Wire `ROUTING_MISS` flag emission in `config/agents/synthesizer.md` → calls `write_quality_event` when a message with clear domain signal was not routed to a relevant specialist.
3. Add implicit correction detection to `config/agents/coordinator.md` → log `USER_CORRECTION` when the user re-states or corrects a prior turn.
4. PWA: "missed the mark" single tap → appends `USER_CORRECTION` event. No rating system, no friction, no visible methodology (discretion principle — the tap is a quiet affordance, not a feedback feature).
5. Register the tool in `core/orchestrator.py → register_tools()` — see ownership note below before touching this file.

## Test (from roadmap A2 — run both before closing)

1. Run a session containing a correction turn ("no, I meant..."). Verify `USER_CORRECTION` entry in `quality_events.json` with timestamp and session_id.
2. Run a session where Synthesizer skips a specialist whose domain is clearly present (e.g. message containing "exhausted and empty" but no Mental Wellbeing call). Verify `ROUTING_MISS` entry logged with source_agent and detail field.

Unlocks: Self-improvement protocol Stage 1 live from Alpha session one. Misses not logged cannot be recovered retroactively.

---

## File ownership (parallel chats are live)

- **This chat owns:** the new tool file (or `tools/logger.py` extension), `config/agents/synthesizer.md`, `config/agents/coordinator.md`, `static/index.html`, `core/server.py`, `data/logs/quality_events.json`
- **`core/orchestrator.py` is owned by the A4+A6 chat.** Your only permitted change is appending one entry to the `register_tools()` list. Make it your **last** step, re-read the file immediately before editing (it is changing under you), and confine the edit to that list.
- **Do not edit:** `config/modules/routing.yaml`, `tools/baselines.py`, `config/modules/scheduler.yaml`
- The A1 chat may queue an instruction edit for `synthesizer.md` — it will apply after you close; you don't need to coordinate beyond closing cleanly.

## Session close

- Create `archive/sessions/2026-06-11 — A2 Logging Layer.md` early in the session, per convention.
- SESSION.md update at close: additive only — mark A2 done, do not rewrite other chats' lines.
