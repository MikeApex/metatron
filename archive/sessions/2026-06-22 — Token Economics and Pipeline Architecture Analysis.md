# Session Archive — Token Economics and Pipeline Architecture Analysis
*Date: 2026-06-22*

---

## What this session covered

Analysis of how tokens accumulate through the Coordinator → Specialist → Synthesizer pipeline, with a concrete traced example. No code was changed.

---

## Key finding: ~95,000 input tokens for a 70-token user message

Traced a representative prompt ("stressed at work, not sleeping well, dentist appointment to reschedule, considering freelance project") through the full pipeline.

### Coordinator (3 turns): ~22,000 tokens

Turn breakdown:
- **Turn 1** (context loading: `read_log`, `read_recent_insights`, `read_context_tracker`): 5,870 tokens
- **Turn 2** (specialist dispatch — 6 `run_subagent` calls): 6,920 tokens
- **Turn 3** (producing coord_package after all specialist results return): 9,220 tokens

The Coordinator's messages list accumulates across turns: by Turn 3 it carries the original system (3,200) + tools (2,000) + user message (670) + context tool results (~900) + specialist tool calls (~300) + specialist outputs (~2,000).

### Sub-agents (5 sync + 1 async): ~58,500 tokens

Each specialist is a fresh `run_session()` call with empty messages list. But each one:
- Independently loads the full tool registry (~2,000t for all 30 tools, regardless of which 2–3 it actually uses)
- Independently calls `load_recent_context()` — the same 5 days of logs loaded 6× (~600t each)
- Loads full shared config (constitution + prime_directive + mission + goals, ~1,400t)
- Typically makes 1–2 internal tool calls, adding a Turn 2

Per-specialist average: ~10,000 tokens over 2 turns.

### Synthesizer (2 turns): ~14,790 tokens

- Turn 1: full system (3,900) + all tool schemas (2,000, even though Synthesizer never calls tools in practice) + recent context (600, loaded again) + original message (70) + coord_package (700)
- Turn 2: after mandatory `write_context_tracker` call

---

## Where the same tokens appear multiple times

### 1. Tool schemas — ~34,000 tokens total across 9 invocations
All 30 tool schemas (~2,000 tokens) are paid for every API call. Coordinator uses ~6 tools. Each specialist uses 2–3. Synthesizer uses 3 (and 0 in the streaming path, which the code notes explicitly). None of these agents needs the full 30.

### 2. Shared config — ~23,800 tokens total
Constitution + prime_directive + mission + goals (~1,400 tokens) is re-included in every agent's system prompt. No caching across agents; each invocation pays the full cost. Prompt caching on Anthropic would help within the Coordinator's multi-turn loop (system prompt is stable there), but cross-agent caching isn't possible.

### 3. Recent context — ~4,800 tokens total
The same 5-day log (~600 tokens) is loaded 8 times: Coordinator, each of 6 specialists, and Synthesizer. Each specialist calls `load_recent_context()` independently. The Coordinator already has this context and uses it to write specialist directives — re-loading it in each specialist is redundant.

### Theoretical minimum
If each piece of information were paid once:
- User message: ~70t
- Shared config (once): ~1,400t
- Context loading results: ~900t
- Specialist outputs (5 × ~400t): ~2,000t
- Synthesizer agent file: ~2,500t
- Tooling overhead (minimal): ~500t
- **~7,370 tokens**

Actual: ~95,000 tokens. **~13× overhead.**

---

## Architectural question: should Coordinator or Synthesizer do specialist calls?

Current design:
- **Coordinator**: initial fan-out to all relevant specialists (parallel)
- **Synthesizer**: secondary/conditional chains (ReAct, up to 3 rounds)

User raised: should all specialist calls live in Synthesizer, with Coordinator being a lightweight router only?

The Synthesizer agent file already supports multi-round specialist chains. The Coordinator's value in the current design is (1) parallel initial fan-out and (2) writing context-rich specialist directives — it needs the user's full context (goals, recent logs) to write good directives.

Arguments for moving all specialist calls to Synthesizer:
- Coordinator becomes a cheap single-turn intent classifier — Haiku-tier, no tool schemas, minimal system prompt. Would cost ~1,000 tokens instead of ~22,000.
- Synthesizer already has identical context access; it can write equally good directives.
- Removes the mandatory two full context loads (Coordinator pays for constitution + config + goals; Synthesizer pays again).

Arguments against:
- Coordinator currently does parallel fan-out in one batch; Synthesizer doing all calls would require careful turn structure to preserve parallelism.
- The Coordinator → coord_package → Synthesizer split gives a clean internal separation (routing vs. integration/voice).

---

## Fixes that don't require architectural change (highest leverage)

Three changes to `_run_single_agent()` and tool registration would cut ~95,000t to ~55,000t:

1. **Route tool schemas per agent** — each agent gets only the tools it can call. Coordinator: ~6 tools. Specialists: 2–3 each. Synthesizer: 3–4. Saves roughly 25,000 tokens per interaction.

2. **Pass recent context in the directive, don't reload it** — Coordinator already has recent context; it should include the relevant slice in the message it passes to each specialist. Remove `load_recent_context()` from specialist sessions. Saves ~3,000 tokens.

3. **Strip constitution from specialist system prompts** — constitution is a tool-operating document, not domain knowledge. Specialists need goals.yaml and their own agent file; they don't need the tool constitution or prime_directive. (This mirrors the research_agent pattern, which already strips personal config entirely.) Saves ~5,000 tokens.

---

## Deferred / not decided

- Whether to make Coordinator a lightweight single-turn router (architectural change, not just config)
- Whether specialists need mission + prime_directive or just goals.yaml
- Prompt caching strategy — could further reduce cost within Coordinator's multi-turn loop if system prompt is kept fully stable

---

## Files referenced (no changes made)

- [core/orchestrator.py](../../core/orchestrator.py) — pipeline implementation, `_run_single_agent`, `run_pipeline_session`
- [tools/subagent.py](../../tools/subagent.py) — `run_subagent`, `run_model_conference`
- [config/agents/coordinator.md](../../config/agents/coordinator.md) — Coordinator instructions (context loading, routing, output format)
- [config/agents/synthesizer.md](../../config/agents/synthesizer.md) — Synthesizer instructions (multi-round chains, integration, mandatory `write_context_tracker`)
