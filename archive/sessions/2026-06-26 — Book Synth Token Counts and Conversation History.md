# 2026-06-26 — Book: Synth Token Counts and Conversation History

## What was fixed

Two bugs in The Book monitor, both shipped in commit `e1a12d2`.

---

### Bug 1 — Synth token counts showing 0

**Root cause:** `_openai_compat_stream` only recorded token counts from a trailing usage-only chunk (where `chunk.choices` is empty), which is the standard OpenAI streaming pattern. Vertex AI's Gemini Flash-Lite embeds usage data in the final *content* chunk (the one with `finish_reason="stop"`, choices non-empty) rather than in a separate trailing chunk. So `_tr.record_turn_tokens` was never called for Synth.

**Fix** (`core/orchestrator.py`): Added a second capture path inside the chunk loop that fires when `choice.finish_reason` is set and `chunk.usage` is present. Guarded by `_usage_recorded` flag to prevent double-counting if both patterns arrive. Token budget logging wired in to the new path as well.

**Result:** Confirmed working — Synth tokens now appear in Column 2.

---

### Bug 2 — Conversation history not visible in Column 3

**Root cause:** In `run_pipeline_session_stream`, `recent_history = list(history[-10:])` was correctly passed to `_openai_compat_stream` (the model received it), but was NOT stored in `context_sections` of the Synth trace record. The Book's "Recent Context" collapsible showed only `load_recent_context()` (the ambient text file), not the actual conversation turns.

**Fix** (`core/orchestrator.py`): Before `_tr.push_agent("synthesizer", ...)`, serialize `recent_history` as a `USER: / ASSISTANT:` formatted string and add it to `context_sections` as `"conversation_history"`.

**Fix** (`tools/metatron_monitor.py`): Added `"conversation_history"` to the context sections loop in `_populate_col3`, displayed as "Conversation History (fed to Synth)".

**Result:** Confirmed working after second exchange in session (first message after service restart has no prior history — expected; second message shows the first exchange in the collapsible).

---

## Key detail: service restart clears history

`_session_history` is in-memory in `core/server.py`. On service restart (e.g., after deploy), it's cleared. The first message in a new session has no history to show — this is correct behavior, not a bug. The `conversation_history` collapsible only appears when there's at least one prior exchange in the current server session.

---

## Files changed

- `core/orchestrator.py` — both fixes
- `tools/metatron_monitor.py` — Column 3 display

## Deploy

`./deploy.sh` → commit `e1a12d2` → VM pulled, services restarted.
