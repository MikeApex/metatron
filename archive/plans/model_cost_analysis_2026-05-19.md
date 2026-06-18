# Model Cost Analysis — May 2026

> Last updated: 2026-05-19. Sources: BenchLM (May 13 2026), PE Collective (April 2026), provider pricing pages. Prices shift — verify before production budgeting.
>
> **Status:** Preliminary estimates. Full analysis deferred until all agents are constructed. Key architectural correction: Diarist is write-only (no output to user — model generates a journal entry written to disk, not a conversational response). Output token estimates for Diarist should use ~400–600 tokens of structured log output, not 1,000 tokens of conversational reply. Diarist is also confirmed for local routing (Ollama) as the primary target — cloud fallback only during development.

---

## Full Pricing Reference

### Anthropic

| Model | Input $/M | Output $/M | Cached input $/M | Context | Best for |
|---|---|---|---|---|---|
| Claude Haiku 4.5 | $1.00 | $5.00 | $0.10 (90% off) | 200K | High-volume short tasks, routing, extraction |
| Claude Sonnet 4.6 | $3.00 | $15.00 | $0.30 (90% off) | 200K | Synthesis, writing, diarist sessions |
| Claude Opus 4.7 | ~$15.00 | ~$75.00 | ~$1.50 (90% off) | 200K | Frontier reasoning; rarely worth the cost |

Caching: manual `cache_control` markup required. Min 1,024 tokens. TTL 5 min default. Write fee = 1.25× base input (you pay a small premium to populate the cache). Read = 10% of base.

### OpenAI

| Model | Input $/M | Output $/M | Cached input $/M | Context | Best for |
|---|---|---|---|---|---|
| GPT-4.1 Nano | $0.02 | $0.08 | $0.01 (50% off) | 128K | Ultra-cheap routing, classification, structured output |
| GPT-4o Mini | $0.15 | $0.60 | $0.075 (50% off) | 128K | Light queries, good instruction following |
| GPT-4.1 Mini | $0.40 | $1.60 | $0.20 (50% off) | 128K | Strong mid-tier; often better than 4o Mini |
| GPT-4o | $2.50 | $10.00 | $1.25 (50% off) | 128K | Multimodal; voice; general flagship |
| GPT-4.1 | $2.00 | $8.00 | $1.00 (50% off) | 1M | Coding, long-context tasks; 1M context |
| o4-mini | $1.10 | $4.40 | $0.55 (50% off) | 200K | Analytical reasoning, pattern detection |
| o3 | $10.00 | $40.00 | $5.00 (50% off) | 200K | Hardest reasoning; high cost |

Caching: automatic for 1,024+ token prefixes. No code change needed. 50% off. Batch API: additional 50% off for async (24hr SLA).

### Google

| Model | Input $/M | Output $/M | Cached input $/M | Context | Best for |
|---|---|---|---|---|---|
| Gemini 2.5 Flash-Lite | $0.10 | $0.40 | $0.05 (50% off) | 1M | Fastest, cheapest; light comprehension |
| Gemini 2.5 Flash | $0.15 | $0.60 | $0.075 (50% off) | 1M | Flash sweet spot; good quality/cost |
| Gemini 3.1 Flash *(current GEMINI_MODEL)* | $0.50 | $3.00 | $0.25 (50% off) | 1M | Current project flash; pricier than 2.5 Flash |
| Gemini 3.1 Pro *(current GEMINI_PRO_MODEL)* | $2.00 | $12.00 | $1.00 (50% off) | 1M | Current project pro; archiving, long-context |

Caching: explicit, 32K minimum token threshold. Configurable TTL. None of the current system prompts hit 32K — Google caching not applicable yet.

### xAI Grok

| Model | Input $/M | Output $/M | Context | Notes |
|---|---|---|---|---|
| Grok 4.1 Fast | $0.20 | $0.50 | 131K | Lowest output price in mid-tier; good for write-heavy tasks |
| Grok 3 Mini | $0.30 | $0.50 | 131K | Cheap output; strong instruction following |
| Grok 4.3 | $1.25 | $2.50 | 131K | Mid-tier flagship; competitive with GPT-4.1 |
| Grok 4.20 | $2.00 | $6.00 | 131K | Higher-end; similar tier to GPT-4o |
| Grok 4 | $3.00 | $15.00 | 131K | Frontier; same price as Sonnet 4.6 |

Caching: available but discount terms not confirmed — verify at x.ai/api. New accounts receive $25 free credits + $150/month via data-sharing program.

### Open-Weight / Third Party

| Model | Input $/M | Output $/M | Context | Notes |
|---|---|---|---|---|
| DeepSeek V3 | $0.14 | $0.28 | 64K | Exceptional value; strong at instruction following and coding |
| qwen3:14b (Ollama, local) | $0 | $0 | 32K | Local compute cost only; no API fee |
| Mistral Large | ~$2.00 | ~$6.00 | 128K | EU data residency; GDPR-compliant |
| Mistral Small | ~$0.10 | ~$0.30 | 128K | EU-residency budget option |

---

## System Prompt Sizes (Actual Project Files)

| Agent | Base config | Agent file | System prompt total |
|---|---|---|---|
| Time Director | ~1,794 tok | ~613 tok | **~2,407 tok** |
| Diarist | ~1,794 tok | ~1,785 tok | **~3,579 tok** |
| Pattern Miner | ~1,794 tok | ~1,667 tok | **~3,461 tok** |
| Goals Interviewer | ~1,794 tok | ~4,171 tok | **~5,965 tok** |

All exceed Anthropic's 1,024-token and OpenAI's 1,024-token caching minimums. None approach Google's 32K minimum.

Base config = constitution (970 tok) + prime directive (95 tok) + mission (109 tok) + goals (624 tok).

---

## Revised Volume Assumptions

User interaction rate: **9–10 per day**, split across two session types:

| Session type | Agent | Frequency | Input tokens | Output tokens | Notes |
|---|---|---|---|---|---|
| **Light check-in** | Time Director | 6/day = **42/week** | 2,600 | 300 | Scheduling query, quick intent parse |
| **Full session** | Diarist | 3/day = **21/week** | 5,500 | 1,000 | Voice reflection, diary capture, memory retrieval |
| **Weekly analysis** | Pattern Miner | 1/week | 8,500 | 2,500 | 7 daily logs + behavioral patterns |
| **Goals interview** | Goals Interviewer | 1/month = **0.25/week** | 10,000 | 4,000 | Multi-turn interview |

Full session input breakdown: system prompt (~3,580 tok) + recent logs context (~1,500 tok) + user voice input (~420 tok).

---

## Weekly Cost Scenarios

### Scenario 0 — Current state (cloud fallbacks, no caching)

All sensitive agents fall back to cloud. No caching enabled.

| Agent | Model | Sessions/week | $/session | $/week |
|---|---|---|---|---|
| Time Director | Sonnet 4.6 | 42 | $0.0123 | **$0.52** |
| Diarist | Sonnet 4.6 | 21 | $0.0315 | **$0.66** |
| Pattern Miner | o3 | 1 | $0.1850 | **$0.19** |
| Goals Interviewer | Sonnet 4.6 | 0.25 | $0.0900 | **$0.02** |
| **Total** | | | | **$1.39/week ≈ $6.00/month** |

### Scenario 1 — Rightsize models only (no caching yet)

Two changes: Time Director → GPT-4.1 Mini, Pattern Miner → o4-mini.

| Agent | Model | Sessions/week | $/session | $/week |
|---|---|---|---|---|
| Time Director | GPT-4.1 Mini | 42 | $0.00152 | **$0.064** |
| Diarist | Sonnet 4.6 | 21 | $0.0315 | **$0.66** |
| Pattern Miner | o4-mini | 1 | $0.0204 | **$0.020** |
| Goals Interviewer | Sonnet 4.6 | 0.25 | $0.0900 | **$0.023** |
| **Total** | | | | **$0.77/week ≈ $3.33/month** |

Diarist is now the dominant cost. The output token problem is acute: 21 sessions × 1,000 output tokens × $15/M = $0.315/week just in output.

### Scenario 2 — Rightsize + Anthropic prompt caching

Add `cache_control` markup to Sonnet 4.6 system prompts. Cache hits on multi-turn sessions reduce the 3,580-token system prompt from $3/M to $0.30/M per hit.

**Important caveat:** Anthropic's TTL is 5 minutes. Caching helps across turns *within* a session, not between separate daily sessions. Assume 4 turns/session average → turns 2–4 get the cache discount.

| Agent | Model | $/session (cached) | $/week |
|---|---|---|---|
| Time Director | GPT-4.1 Mini (auto-cached) | $0.00104 | **$0.044** |
| Diarist | Sonnet 4.6 (turns 2–4 cached) | $0.0248 | **$0.521** |
| Pattern Miner | o4-mini (auto-cached) | $0.0186 | **$0.019** |
| Goals Interviewer | Sonnet 4.6 (cached) | $0.0680 | **$0.017** |
| **Total** | | | **$0.60/week ≈ $2.60/month** |

Caching helps but doesn't solve the core problem: **output tokens are the dominant cost driver for the Diarist**. 21 sessions × 1,000-token diary responses at $15/M = $0.315/week. No caching strategy touches output token pricing.

### Scenario 3 — Rightsize + cache + Diarist model change

The Diarist doesn't need Sonnet 4.6 for *every* session. Quick voice check-ins (morning, midday) don't require the same narrative quality as an evening diary entry. Consider tiering:

- 2/day quick check-ins (midday, morning intention): GPT-4.1 Mini or GPT-4o Mini
- 1/day full diary (evening): Sonnet 4.6

| Session type | Model | Count/week | $/session | $/week |
|---|---|---|---|---|
| Diarist — quick (light input, short response) | GPT-4.1 Mini | 14 | $0.0019 | **$0.027** |
| Diarist — full evening diary | Sonnet 4.6 (cached) | 7 | $0.0248 | **$0.174** |
| Time Director | GPT-4.1 Mini (cached) | 42 | $0.00104 | **$0.044** |
| Pattern Miner | o4-mini | 1 | $0.0186 | **$0.019** |
| Goals Interviewer | Sonnet 4.6 (cached) | 0.25 | $0.0680 | **$0.017** |
| **Total** | | | | **$0.28/week ≈ $1.21/month** |

**80% reduction** from baseline. The once-daily full Sonnet diary session is the right quality threshold; quick check-ins don't justify the output cost.

### Scenario 4 — Ollama enabled (target state)

Sensitive agents (Diarist, Pattern Miner, Goals Interviewer) route local. Only Time Director stays cloud for scheduling reliability.

| Agent | Model | $/week |
|---|---|---|
| Time Director | GPT-4.1 Mini (cached) | $0.044 |
| Diarist | qwen3:14b (local) | $0 |
| Pattern Miner | qwen3:14b (local) | $0 |
| Goals Interviewer | qwen3:14b (local) | $0 |
| **Total** | | **~$0.04/week ≈ $0.19/month** |

Cloud costs become negligible. The limiting factor becomes local inference quality and the speed of qwen3:14b on available hardware.

---

## Cost Driver Summary

At 9–10 interactions/day, the cost structure is:

```
Scenario 0 (current):    $6.00/month  ████████████████████████
Scenario 1 (rightsize):  $3.33/month  █████████████
Scenario 2 (+caching):   $2.60/month  ██████████
Scenario 3 (+tier diary):$1.21/month  ████
Scenario 4 (Ollama):     $0.19/month  █
```

**The output token problem:** At Sonnet 4.6 pricing ($15/M output), a 1,000-token diary entry costs $0.015 in output alone. At 21 sessions/week that's $0.315/week. Caching doesn't help output. The only levers are: (a) shorter responses, (b) cheaper model for non-critical sessions, (c) local inference.

**The frequency multiplier:** Going from 2 interactions/day (original estimate) to 9–10/day multiplies cost ~4×. Model choice matters a lot more at this volume. The difference between Sonnet 4.6 and GPT-4.1 Mini for Time Director is $0.52 vs $0.044/week — a 12× swing.

---

## Model Selection Guide

| Task type | Recommended | Rationale | Avoid |
|---|---|---|---|
| Quick intent parsing (schedule, routing) | GPT-4.1 Mini or GPT-4.1 Nano | 20–50× cheaper than Sonnet; sufficient for structured queries | Sonnet 4.6 (overkill) |
| Voice diary — evening full entry | Sonnet 4.6 | Narrative quality, nuance, FAISS memory integration | GPT-4.1 Mini (quality drop on long-form) |
| Voice diary — quick check-in | GPT-4.1 Mini or GPT-4o Mini | Short exchange, low stakes | Sonnet 4.6 (output token waste) |
| Weekly behavioral analysis | o4-mini | Strong reasoning, 9× cheaper than o3; adequate for pattern spotting | o3 (no quality justification at this task) |
| Hard analysis run (monthly) | o3 | Reserve for genuinely hard reasoning tasks | Using as default |
| Document archiving | Gemini 3.1 Pro | 1M context, good at structured extraction | — |
| Anything sensitive | qwen3:14b (local) | Zero API cost; privacy enforced at routing layer | Any cloud model |
| EU data residency need | Mistral Small/Large | GDPR-compliant infrastructure | All others |
| Extreme budget mode | GPT-4.1 Nano | $0.02/M input; adequate for classification/routing | Long-form generation |

---

## GPT-4o: Where It Fits

GPT-4o ($2.50/M in, $10/M out) is OpenAI's multimodal flagship. Relevant considerations for this project:

- **Voice mode**: GPT-4o has native audio input/output (not text-based Whisper pipeline). If the project moves away from Whisper → text → LLM → TTS toward end-to-end voice, GPT-4o is the primary candidate.
- **Cost**: More expensive than GPT-4.1 ($2.00 vs $2.50) with a smaller context window (128K vs 1M). For text-only API usage, GPT-4.1 is strictly better.
- **Multimodal routing**: If a future agent needs image understanding (scanning a document, reading a whiteboard), GPT-4o is the right call.
- **Current verdict**: Not needed while the voice pipeline stays text-based (Whisper → text → LLM). Re-evaluate in Phase 5 if voice architecture changes.

---

## Caching Implementation Notes

### Anthropic (manual markup)
Add `cache_control` to the system prompt content block in `orchestrator.py`:

```python
# In build_messages() or wherever system prompt is assembled:
{
    "role": "user",
    "content": [
        {
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"}
        },
        {
            "type": "text",
            "text": user_message
        }
    ]
}
```
Write fee: 1.25× base input (so $3.75/M first call). Read fee: $0.30/M. Break-even at 2 turns/session.

### OpenAI (automatic)
No code change. Automatic for any prompt prefix ≥ 1,024 tokens that repeats within the session. The system prompt (2,400–5,900 tokens) qualifies automatically.

### Google (not applicable yet)
Requires 32K minimum. Not triggered by any current system prompt.

---

## Batch API for Pattern Miner

Pattern Miner runs once/week, non-interactively, non-urgently. OpenAI Batch API gives 50% off with 24hr turnaround.

| Model | Standard $/week | Batch $/week |
|---|---|---|
| o4-mini | $0.0204 | $0.0102 |
| o3 | $0.185 | $0.093 |

Implement by submitting the weekly pattern mine as a batch job via OpenAI's `/v1/batches` endpoint. The orchestrator would submit Sunday night, retrieve Monday morning. Negligible real-world impact at this cost level, but a good habit for any future high-volume analytical workloads.

---

## Implementation Priority

**Do first (one-time code change, big impact):**
1. Add `cache_control` markup to Anthropic system prompt in `orchestrator.py` — immediate 30–50% savings on all Sonnet multi-turn sessions
2. Add `cloud_light` provider to `routing.yaml` pointing to GPT-4.1 Mini, route Time Director there — 12× cost reduction on highest-frequency agent
3. Add diarist session-type parameter: quick check-ins use GPT-4.1 Mini, evening diary uses Sonnet 4.6

**Do when Ollama is ready:**
4. Flip `local_enabled: true` — eliminates Diarist and Pattern Miner cloud costs entirely

**Revisit in Phase 5:**
5. Evaluate GPT-4o if voice architecture moves to native audio
6. Benchmark DeepSeek V3 for Diarist quality — at $0.14/$0.28 it could handle diary sessions at ~5% of Sonnet's cost
7. Consider Gemini 2.5 Flash as a cheaper cloud_fast alternative (currently using 3.1 Flash at $0.50/M, vs 2.5 Flash at $0.15/M — 3× cheaper for the same tier)
