# 2026-06-26 — Pipeline Audit and Research Agent Fix

## What this session covered

Post-deployment pipeline audit across ~2 hours of live traffic (15:28–16:47), followed by deep-dive on exchange #027 (Research Agent failure), and two fixes.

---

## Pipeline audit findings (15:28–16:47)

Pulled server logs, conversation JSONL, and persona trace file. Five distinct exchanges identified across six server restart cycles.

### Bugs confirmed

1. **`tools.ambient` not deployed to VM** — `No module named 'tools.ambient'` on every call. Coordinator and Synthesizer running without live date/time, weather, or market data. Fix: deploy needed.

2. **Output filter false positive (Exchange 3, 15:51)** — Mike said "write_config call" in his message. Synthesizer mentioned `write_config` in its response. `filter_output()` scanned for the substring and suppressed the response with the canned fallback. Mike received "I'm here to help you manage your life" instead of an actual response. Unfixed this session — flagged for later.

3. **Research Agent normalization miss (Exchanges 9, 10, 027)** — Coordinator (Flash-Lite) output `"agent": "Research"` (not `"Research Agent"`) in SPECIALISTS_TO_CALL JSON. `_normalize_agent("Research")` → fallback → `"research"` → `load_agent("research")` → `research.md` not found → PIPELINE warning, specialist silently dropped. **Fixed this session** (see below).

4. **Coordinator system prompt below Vertex cache minimum** — 3395–3699 tokens < 4096 threshold. Every Coordinator call runs uncached. Structural; not fixable without padding the prompt.

5. **Graceful shutdown not working** — every deploy triggers a 90-second SIGKILL cycle. 14+ child processes stranded. Symptom of in-flight pipeline threads not draining. Not fixed this session.

### Latency profile

- 2-specialist session (cold): ~73s coordinator-to-200-OK
- 2-specialist session (warm cache): ~29s
- f&f-only session: ~9s
- 8-turn specialist (thought_signature sequential workaround): adds ~38s

Synthesizer consistently hits `cache_read=10438` (working). MW/PH hit cache on multi-turn calls.

### Concurrent requests

Two `/session/stream` requests hitting simultaneously visible in several windows — token budget warnings interleaved from two pipelines.

---

## Exchange 027 deep-dive

**Message:** "Test #10. What's the date, time, and weather?"
**Failure:** Research Agent silently dropped → Synthesizer streamed "I'm hitting a minor snag pulling the live weather."

### Root cause chain

1. Coordinator (Flash-Lite, fresh server restart, no conversation history) output `"Research"` instead of `"Research Agent"` in SPECIALISTS_TO_CALL JSON
2. `_normalize_agent("Research")` → not in `_AGENT_NAME_MAP` → fallback → `"research"` → `research.md` not found → `[PIPELINE] research failed`
3. Synthesizer received empty specialist outputs, began streaming uncertainty text ("minor snag")
4. Synthesizer then called `run_subagent("research_agent")` as recovery → got successful weather data (36°C, sunny, London heatwave) → but already-streamed "snag" text was committed to client
5. Synthesizer logged `ROUTING_MISS` quality event: "Coordinator called 'research' instead of 'research_agent'"

### Evidence sources

- Server log: `[PIPELINE] research failed: Agent not found: .../research.md` at 16:41:15
- Persona trace (`data/personas/mike/traces/2026-06-26.jsonl`): Coordinator step `output: ""`, Synthesizer subagent shows `run_subagent(agent_name="research_agent")` with full weather result in `result_preview`
- Conversation log (`data/conversations/2026-06-26.jsonl`): `seq=027`, response contains "minor snag" despite recovery succeeding

---

## Fixes applied

### Fix 1 — `core/orchestrator.py`: single-word abbreviations in `_AGENT_NAME_MAP`

Added 9 entries to catch Flash-Lite abbreviations of multi-word agent names:
```python
"research": "research_agent",
"mental": "mental_wellbeing",
"physical": "physical_health",
"work": "work_vocation",
"learning": "learning_growth",
"recreation": "recreation_hobbies",
"goals": "goals_interviewer",
"pattern": "pattern_miner",
"time": "time_director",
```
Single-word agents (relationships, finance, logistics, diarist) already resolve correctly via fallback — not added.

### Fix 2 — `config/agents/coordinator.md`: explicit valid agent names

Added a "Valid `agent` values" line immediately before the format template, listing all 12 agent strings verbatim. Prompt fix reduces the probability of abbreviation; code fix eliminates the consequence. Both kept.

**Pending deploy** — changes committed locally, not yet pushed to VM.

---

## Prompts produced

### Session-opener audit prompt

The prompt that opened this session (in the context header) — good for broad pipeline health checks covering multiple exchanges. Covers latency, routing, Synthesizer quality, common failure patterns.

### Single-exchange troubleshoot prompt

New prompt written this session. Two inputs at top (DATE, SEQ). Single SSH command pulls all three data sources in one round-trip: conversation record → server logs (±3 min window derived from exchange timestamp) → pipeline trace. Checklist covers same failure patterns as session-opener but scoped to one exchange.

---

## Deferred / open

- Deploy the two fixes (`./deploy.sh`)
- `tools.ambient` deploy separately (separate deploy or confirm it's in current HEAD)
- Output filter false positive — `write_config` in `_CONFIDENTIAL_TERMS` needs context-aware suppression or removal from the list
- Graceful shutdown — 90s SIGKILL cycle per deploy; no fix applied
- 8-turn specialist sessions — cause not identified (thought_signature sequential workaround is expected but 8 turns reaching 40K tokens warrants investigation)
