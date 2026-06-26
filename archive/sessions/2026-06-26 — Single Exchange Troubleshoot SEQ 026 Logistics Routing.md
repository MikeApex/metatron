# 2026-06-26 — Single Exchange Troubleshoot: SEQ 026 Logistics Routing

## What we investigated

Troubleshot why SEQ 026 (2026-06-26T16:28:23, "Delayed until Monday at 5:30.") did not trigger a scheduling action. User expected Logistics to be dispatched; it was not.

## Data pull findings

**Conversation record:** Response was "Got it. I'll keep that on the radar for Monday evening." — social acknowledgment, no action taken.

**Server logs:** Server restarted at 16:25:47 just before the exchange. `[vertex_cache] creation failed` (3395 tokens < 4096 minimum) — not a functional failure. No `[PIPELINE]` errors for this exchange.

**Pipeline trace:** Matched at ts=2026-06-26T16:27:46. Coordinator: Flash-Lite, 1 turn, 5578 input tokens, 261 output, 3173ms — dispatched zero specialists. Synthesizer: Pro, 19192ms, called `write_context_tracker` with follow-up "Check in on Miss Ruby conference outcome on Monday evening." Synthesizer token tracking showed `in=0 out=0` for this exchange (pre-fix bug).

## Root cause

**Coordinator:** "Delayed until Monday at 5:30." has no subject and none of the Logistics signal words in coordinator.md. The Coordinator correctly parsed the message but had no rule to match it as a scheduling/deferral action. SPECIALISTS_TO_CALL was empty. Synthesizer absorbed it conversationally.

**Synthesizer:** Had `write_config` in its allowlist but the instruction scoped it to habits/recurring sessions — not one-off deferrals. No catch-up rule for missed Logistics routing existed.

**Architecture clarification:** There is no "Scheduler agent." Scheduling actions go through Logistics (`write_calendar_event`) for one-off events/deferrals, and through Synthesizer's `write_config` for recurring proactive session entries (habits, morning briefs). These are distinct and were conflated in the initial analysis.

## Synthesizer token tracking

Confirmed broken (in=0 out=0) on exchanges before ~17:05 on 2026-06-26. Working correctly from 17:05 onwards — last three exchanges of the day showed proper counts (12k–13k input tokens). No code change needed; confirmed fixed by a prior deploy.

## Changes made

### 1. `config/agents/coordinator.md` — Logistics routing broadened
Added to the Logistics specialist entry:
- Explicit "also call when user defers or postpones anything to a named time" rule with the SEQ 026 pattern as an example
- Deferral/rescheduling signal words: delayed, postponed, rescheduled, moved to, pushed to, bumped, put off, defer, reschedule, changed to, updated to
- Temporal commitment triggers: tomorrow, next week, this weekend, next month, end of month/week, next year, by [day name], on [day name], [day] at [time], [month] [date]

Commit: `e477c76`

### 2. `tools/subagent.py` — Remove Diarist from Synthesizer's run_subagent schema
Diarist is always dispatched fire-and-forget by the Coordinator; Synthesizer has no use case for calling it directly. Removed from both the tool description and the `agent_name` options list. Updated `fire_and_forget` description to be generic rather than Diarist-specific.

Confirmed: Coordinator dispatches Diarist via `_dispatch_from_coordinator` (text parsing, not tool calls), hardcoded as fire_and_forget. Schema change has no effect on Coordinator behaviour.

Commit: `5f21800`

### 3. `config/agents/synthesizer.md` — write_config scope + Logistics catch-up rule
Two targeted edits:
- `write_config` tool description clarified: for recurring proactive sessions only (habits, standing check-ins). Explicit "do not use for one-off events or deferrals — those are Logistics" note added.
- Sanity-check section: added scheduling/deferral catch-up rule — if `ORIGINAL_MESSAGE` contains a temporal commitment signal and no Logistics output was provided, call `run_subagent("logistics", ...)` before responding, then log `ROUTING_MISS: Logistics` and call `write_quality_event`.

Commit: `5a7c6ff`

## Decisions made

- Pattern Miner and Goals Interviewer should NOT be added to Synthesizer's callable agents. PM runs on schedule via scheduler.py; Goals Interviewer is first-instance onboarding only. Neither belongs in real-time Synthesizer chains.
- Coordinator model upgrade (Flash-Lite → Flash/Pro) is not the right fix for routing misses. The problem is missing rules, not capability. Instructions are cheaper and more reliable for pattern-matching routing signals.
- Synthesizer as a second router is architecturally wrong for analysis/research agents. The catch-up path (Logistics only) is appropriate because it's an action completion, not a routing decision.

## Open items

- **Test the Coordinator fix** — send a deferral message through the app and verify Logistics appears in the pipeline trace.
- **Verify `write_calendar_event`** — confirm the tool actually writes to a real calendar integration and isn't just logging to a flat file. If it's hollow, the scheduling gap is not fully closed end-to-end.
