# SEQ 041 Single Exchange Troubleshoot
**Date:** 2026-06-26  
**Session type:** Diagnostic — single exchange deep-dive

---

## What was investigated

Pipeline diagnostic on SEQ 041 (2026-06-26T22:01:05). User: "I'm not sure. Do you have some suggestions?" — continuation of a Bulgarian vocabulary goal discussion (SEQ 040 established the goal wasn't in active data).

## Findings

### 1. Response quality — Pass
Synthesizer produced a coherent, contextually appropriate response: suggested 10–15 min/day Bulgarian practice split into flashcard + listening blocks, and asked the user's preferred learning modality. No hedging, no failure indicators.

### 2. Trace timestamp mismatch — Diagnostic tooling bug
Trace ts = pipeline *start* (22:00:48); conversation record ts = pipeline *completion* (22:01:05). When start and end straddle a minute boundary, the `[:16]` minute-match fails. The `2026-06-26T22:00` trace IS SEQ 041's trace — script false-negatives on "no trace found." Fix: use ±2-minute window search, not exact minute prefix match.

### 3. Token budget growth — Operational concern (not failure)
Coordinator running 3 internal turns: cumulative_input 5518 → 8551 → 13223 tokens. At SEQ 041 (41 exchanges into the session), conversation history is driving context growth. Synthesizer input: 11,873 tokens. OVER_8K warnings are alerts, not errors — pipeline completed fine. Will worsen as conversation lengthens.

### 4. Trace coverage gap — Instrumentation gap
Trace records `turn=1 in=5518` for coordinator but server logs show 3 actual turns (OVER_8K at turns 2 and 3). Multi-turn tool-calling sequences within a coordinator run are not captured in the trace. Turn 1 token counts in the trace understate actual token consumption.

### 5. Vertex cache — Known non-failure
System prompt at 3655 tokens; Vertex minimum is 4096. Will fail on every exchange until system prompt grows past threshold. Not functional — running uncached works.

### 6. No security suppression, no pipeline failures
No `[SECURITY] Output filter` events, no `[PIPELINE] X failed: Agent not found`, no ambient load failures, no diarist failures in the window.

## Decisions / deferred

- Trace script ±2-minute window fix: deferred (diagnostic tooling, low priority)
- Token budget growth: expected for long sessions; no action yet — revisit if per-turn latency degrades
- Vertex cache: no action; resolves automatically if system prompt grows
