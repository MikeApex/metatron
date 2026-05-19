# Phase 3 Complete — Multi-Provider Model Comparison
*2026-05-18 → 2026-05-19*

## What was built

**Three-layer memory architecture**
- Short-term: last 5 days of logs injected into system prompt at session start
- Mid-term: context tracker JSON (open threads, patterns, follow-ups) written by Diarist at close, read at next open
- Long-term: FAISS semantic index (all-MiniLM-L6-v2, local) across all journals and logs

**Diarist agent (full)**
- tools/diarist.py: write/read_journal, write/read_archive (persona-scoped, 600 perms)
- tools/wisdom.py: write/read_wisdom — Life Wisdom Depot, keyed upsert by category
- tools/memory_tool.py: search_memory — delegates to core.memory FAISS index
- tools/context_tracker.py: write/read_context_tracker — mid-term bridge
- tools/logger.py: extended with persona scoping, content coercion (str/None → dict)
- orchestrator: load_recent_context() injects short+mid-term memory; 14 tools registered

**config/agents/diarist.md** — full rewrite
- "Capture before you respond" — explicit write-before-reply rule
- "Everything is loggable" — no category of experience too small, override the in-moment judgment instinct
- Session open protocol: read_context_tracker → read_wisdom → respond
- Session close: write_context_tracker with open threads, patterns, follow-ups

**tests/run_phase3.py** — multi-provider test runner
- Supports --provider openai | gemini | claude | all
- Separate Anthropic capture loop (content blocks vs OpenAI messages)
- o3 max_completion_tokens compatibility
- Per-provider report output: tests/phase3_report_{provider}.md

## Model comparison results

Tested: Gemini 2.5 Flash (benchmark), Gemini 3.1 Pro, o3, Claude Sonnet 4.6, Claude Opus 4.7 (partial — stopped after 6/7 tests, ~$1 cost)

### Runtime sub-agent assignments

| Agent | Model | Rationale |
|---|---|---|
| Diarist | Sonnet 4.6 | Best conversational depth and persona engagement |
| Pattern Miner | o3 | Best analytical synthesis, multi-query search strategy |
| High-capture sessions | Gemini 3.1 Pro | Most thorough multi-destination archiving |
| Fast/fallback | Gemini 2.5 Flash | Reliable, low-latency |

### Standout moments

**Sonnet 4.6 (T2 Holiday):** Quoted Seneca in Latin unprompted — "Omnia, Lucili, aliena sunt, tempus tantum nostrum est" — then connected it to what three mornings stuck on Cato actually feels like. No other model attempted this.

**Sonnet 4.6 (T6 Brooks):** "The column becomes the reason, and then the gym becomes the casualty, and then the column gets done by someone who's sharper and less patient than he would have been. That's a bad trade." Best single response of the test series.

**Sonnet 4.6 (T5 Burkeman):** Read existing log, detected duplicate, declined to write — only model to show this awareness.

**o3 (T1 Holiday):** Proactively wrote write_wisdom for sleep-writing correlation before being asked. T3: named data gaps and asked for word-count per session to quantify "stuck."

**Gemini 3.1 Pro (T1 Holiday):** Only model to archive Liam's turtle as an *experiences* entry. T4: archived Burkeman's realization to *ideas* in addition to journal.

### Dev consultant routing

- Architecture, logic, edge cases → o3
- UX, persona, instruction design → Sonnet 4.6
- Comprehensive research → Gemini 3.1 Pro
- Quick iteration → Gemini 2.5 Flash

### Cost lesson

Opus 4.7 ~$1 for 7 tests (long system prompts × tool loops × 7 scenarios). Reserve for final phase validation only. Sonnet 4.6 is the dev default for Anthropic.

## Bug fixes applied during testing

- write_log: content coercion (str → {"notes": ...}, None → {}), default to None
- write_archive: item coercion (str → {"title": ...}, None → {}), default to None
- read_log, read_journal: added `= ""` defaults to prevent missing-arg errors
- orchestrator/_openai_compat_loop: max_completion_tokens for o3-family models

## What's next — Phase 4

- Pattern Miner sub-agent (o3)
- Proactive initiation scheduler daemon
- Deeper synthetic-data test (weeks of simulated history) planned for end of Phase 4
- Ollama (qwen3:14b) integration for sensitive-data routing — role decision still pending

## Open questions carried forward

- write_log called without content by some models (GPT-4o, o3 in chained session) — writes sparse {"date": ...} records; may need stronger instruction or schema enforcement
- Gemini 3.1 Pro speed: 27 min for 7 tests vs 9 min for o3; worth re-testing when stable release ships
- Wisdom depot deduplication: multiple near-identical gym entries for Brooks from different test rounds (different keys each time); upsert by semantic similarity not key alone
