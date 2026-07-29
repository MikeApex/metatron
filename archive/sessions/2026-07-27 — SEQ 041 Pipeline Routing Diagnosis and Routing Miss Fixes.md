# SEQ 041 Pipeline Routing Diagnosis and Routing Miss Fixes
**Date:** 2026-07-27
**Type:** Diagnostic + bug fix

---

## What was investigated

Full diagnostic of SEQ 041 (2026-06-26T22:01:05) — user said "I'm not sure. Do you have some suggestions?" as a follow-up to a Bulgarian vocabulary goal discussion. Response was generic language-learning advice rather than personalized output grounded in learning history.

Used the single-exchange troubleshoot script (DATE=2026-06-26, SEQ=041) to pull conversation record, server logs, and pipeline trace from the VM.

---

## Root causes identified

### 1. Coordinator routing miss
The Coordinator dispatched zero specialists for the exchange — SPECIALISTS_TO_CALL was effectively empty. "I'm not sure. Do you have some suggestions?" was classified as a low-complexity conversational follow-up to an existing thread. The Bulgarian vocabulary goal was in the context tracker, but the Coordinator did not re-route to Learning & Growth.

Evidence: Synthesizer context package had only 4 sections — `agent_file`, `config`, `recent_context`, `conversation_history` — no specialist output at all.

### 2. Synthesizer catch failure
The Synthesizer has a mandatory sanity-check rule: if the original message carries a signal that no specialist surfaced, call `run_subagent` before responding. It did not fire. The Synthesizer responded from general knowledge (generic 10–15 min/day framing, generic modality question) rather than consulting Learning's data: skill goal records, prior Bulgarian engagement history, read_agent_config output.

### 3. Trace timestamp mismatch (diagnostic tooling, not a runtime bug)
The troubleshoot script reported "no trace found" for SEQ 041. Root cause: trace timestamp = pipeline *start* (22:00:48); conversation record timestamp = pipeline *completion* (22:01:05). When these straddle a minute boundary, the `[:16]` minute-prefix match fails. The 22:00 trace IS SEQ 041's trace.

---

## Diarist evaluation

### Does it fire twice?
No — once per exchange. The log window for SEQ 041 covered both SEQ 040 and SEQ 041, each with their own Diarist run, producing what looked like duplicate warning pairs.

### Three OVER_8K turns explained
The three warnings in the server log come from two different agents:
- `turn=2 cumulative=8551` and `turn=3 cumulative=13223` → Diarist (fire-and-forget daemon thread)
- `turn=1 cumulative=11873` → Synthesizer (logged when API call *returns*, not when it starts)

The Diarist's 3-turn pattern is caused by the Vertex `thought_signature` bug: when the model returns parallel tool calls (`write_journal` + `write_archive`), only tc0 (write_journal) is signed. The orchestrator sends tc0 only; the model re-calls tc1 (write_archive) on turn 2; turn 3 is the CAPTURED summary response. This is sequential execution of what should be a single parallel turn.

### Latency impact
Zero. Diarist runs in `threading.Thread(daemon=True)` — fire-and-forget. User response returns when Synthesizer finishes; Diarist runs entirely in background.

### No fix needed for 3-turn pattern
Fixing the Vertex parallel tool call bug would require redesigning the tool call execution path in the orchestrator — significant code change for no user-facing benefit. Not worth it for a background agent at Flash-Lite rates.

---

## Fixes implemented and deployed

All four changes committed as `814e6c3`, deployed to VM via `./deploy.sh`.

### 1. `config/agents/coordinator.md`
Added routing rule under step 4 of intent resolution:
> Advice/suggestion requests must route to the relevant domain specialist even when COMPLEXITY is `quick`. "Do you have suggestions?" about a named domain topic is a domain query, not a social exchange.

### 2. `config/agents/synthesizer.md`
Added domain query catch-up immediately after the existing Logistics catch in "Integrating specialist outputs":
> If ORIGINAL_MESSAGE asks for advice, suggestions, recommendations, or a plan about a topic falling within any specialist's domain — and no output from that specialist is present — call `run_subagent` before responding. Covers all 8 domains. Log ROUTING_MISS + call write_quality_event.

This generalizes the pattern rather than making it Learning-specific.

### 3. `core/orchestrator.py` (line 1659)
Diarist added to bare-mode set alongside `research_agent`. Strips goals.yaml from Diarist's system prompt — saves ~500–1000 tokens per turn across the 3-turn run. Diarist is directive-driven; it has no use for goals.yaml.

### 4. `config/modules/routing_cloud.yaml`
`write_log` and `write_wisdom` added to Diarist's `allowed_tools` alongside `write_journal` and `write_archive`. Previously the Diarist couldn't call `write_log` for structured daily data, forcing it to overuse `write_journal`.

---

## Decisions / deferred

- Trace script ±2-minute window fix: deferred (diagnostic tooling only, low priority)
- The three-turn Vertex parallel tool call pattern: no fix needed (no user impact, background agent)
- Token budget growth in long sessions: not a problem today, revisit if per-turn latency degrades
