# 2026-06-04 — Token Budget Logging

## What was built

Added session-level token budget logging to `core/orchestrator.py` to support behavioral audit Probe 7 in `tests/agent_audit_template.md`.

### Changes (all in `core/orchestrator.py`)

1. Added `import logging` and `logger = logging.getLogger(__name__)` at module level.

2. **`run_session_anthropic`**: Added `cumulative_input_tokens = 0` and `turn_num = 0` before the while loop. After each `client.messages.create()` response, increments both counters using `response.usage.input_tokens`. Emits `logger.info("[token_budget] turn=N cumulative_input=N")` each turn; upgrades to `logger.warning("[token_budget] OVER_8K ...")` when cumulative input exceeds 8000.

3. **`_openai_compat_loop`**: Added `cumulative_input_tokens = 0` before the for loop; renamed `for _` to `for turn_num in range(1, max_iterations + 1)`. After each response, accumulates `response.usage.prompt_tokens` (guarded by `if response.usage:` since some compat endpoints omit it). Same log/warn pattern as above. Covers OpenAI, Gemini, and Ollama, which all route through this function.

## Testing coverage confirmed

- `tests/agent_audit_template.md` Probe 7 (lines 96–112): requires cumulative input tokens per turn, 8K Pass threshold. The logging added is the measurement mechanism.
- `tests/phase5_testing_plan.md` line 113: also references cumulative input token logging as a named test item.

## Decisions

- Used `if response.usage:` guard in the OpenAI-compat path because some providers (Ollama) may not return usage data.
- No new files created; no other files touched.

## Deferred

Nothing.
