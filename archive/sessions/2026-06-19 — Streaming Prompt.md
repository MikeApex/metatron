# 2026-06-19 — Streaming Prompt

## What This Session Is

Adding server-sent-event (SSE) streaming from the Synthesizer to the PWA so the user hears the first words within 2–3s instead of waiting ~12s for full generation.

## Scope

- Synthesizer output only — Coordinator and specialist calls remain blocking
- All four providers covered: Gemini/Vertex, OpenAI, Ollama (via `_openai_compat_stream`), Anthropic (via `_anthropic_stream`)
- Existing `/session` endpoint unchanged
- PWA client changes deferred to a follow-up session

## Files Changed

- `core/orchestrator.py` — new functions: `_openai_compat_stream()`, `_anthropic_stream()`, `_resolve_gemini_credentials()`, `run_pipeline_session_stream()`
- `core/server.py` — new endpoint: `POST /session/stream` (SSE, `text/event-stream`)
- `archive/plans/phase5_to_future_roadmap_2026-06-10.md` — added streaming provider coverage note and pre-Alpha filter-buffer review item

## Key Decisions

1. **filter_output() + streaming:** Live-stream chunks to client, buffer simultaneously, run filter after final chunk. If filter hits: send `[RETRACT]` so client discards received text. Accepted because filter hits are rare and this is the only option that achieves latency goal. Pre-Alpha review item added to roadmap.

2. **Anthropic streaming:** All turns use `client.messages.stream()`. Text is buffered per turn but not yielded. On `stop_reason == "tool_use"`: handle tools, continue loop (don't yield). On `stop_reason == "end_turn"`: yield buffered text chunks.

3. **"Gemini only" clarification:** The streaming implementation is provider-agnostic. The "Gemini only" framing referred to the current Synthesizer routing in `routing.yaml`. If routing changes, streaming follows automatically. `# STREAMING NOTE` guard comment added at the dispatch point in `run_pipeline_session_stream()`.

## SSE Protocol

```
data: {chunk}\n\n       ← live text chunk
data: [DONE]\n\n        ← filter passed, commit to TTS/UI
data: [RETRACT]\n\n     ← filter caught something, discard
data: [ERROR] …\n\n     ← server exception
```

## PWA Client (deferred)

Use `fetch` + `response.body.getReader()` (not `EventSource` — GET-only). Feed chunks to `SpeechSynthesisUtterance` in sentence-sized pieces. On `[DONE]`: commit. On `[RETRACT]`: `speechSynthesis.cancel()` + fallback.

## What Was Discovered Mid-Implementation

`run_session_gemini()` was already refactored (M status, pre-existing) to use `_run_gemini_native_loop` (native genai SDK) rather than `_openai_compat_loop`. The OpenAI-compat credential helpers (`_get_vertex_bearer_token`, `_vertex_openai_base_url`, `_vertex_model_name`) still exist and are used by the new `_resolve_gemini_credentials()` to route Synthesizer streaming through the Vertex OpenAI-compat endpoint.

## Functions Added

| File | Function | Description |
|---|---|---|
| `core/orchestrator.py` | `_openai_compat_stream()` | Streaming agentic loop for Gemini/OpenAI/Ollama; yields text chunks, handles tool-call turns blocking |
| `core/orchestrator.py` | `_anthropic_stream()` | Streaming loop for Anthropic; streams every turn, only yields text in the final non-tool turn |
| `core/orchestrator.py` | `_resolve_gemini_credentials()` | Returns `(api_key, base_url, model_name)` for Gemini OpenAI-compat endpoint (Vertex or AI Studio) |
| `core/orchestrator.py` | `run_pipeline_session_stream()` | Coordinator blocking → Synthesizer streaming; yields text chunks then `[DONE]` or `[RETRACT]` |
| `core/server.py` | `POST /session/stream` | SSE endpoint; `text/event-stream`; coordinator-only; falls back to blocking if `NotImplementedError` |

## To Verify

```bash
python core/server.py --provider gemini
curl -N -X POST https://mikes-macbook-air.tail0acc5d.ts.net:8000/session/stream \
  -H "Content-Type: application/json" \
  -d '{"input": "What should I focus on today?", "agent": "coordinator"}'
```

Expect: chunks arrive progressively, `[DONE]` at end, first chunk within ~2s.

## HF Token

`HF_TOKEN` (read-only) added to `.env`. HuggingFace Hub unauthenticated warning during model weight loading — suppressed by token.

## Vertex thought_signature bug — resolved (continued session)

**Root cause:** Vertex AI's OpenAI-compat endpoint embeds `thought_signature` in each tool call's `extra_content.google` field. When the model makes N parallel function calls in one turn, only tc0 gets a cryptographically valid signature. The other calls have no signature. Vertex validates signatures on all prior assistant messages and rejects the multi-turn request with a 400.

**What was tried:**
1. Native SDK `model_copy` to propagate tc0's signature to tc1+ — Vertex validates per-call cryptographically, same-signature-on-all fails
2. Stripping all signatures — Vertex requires them when it generated signed calls
3. `include_thoughts=True` in native SDK — doesn't affect per-call signing
4. `parallel_tool_calls=False` — Vertex ignores this parameter entirely
5. Synthetic multi-call dict messages without `extra_content` — Vertex validates ALL assistant messages with tool calls, not just its own
6. Synthetic single-call dict messages per tool — Vertex still validates and rejects unsigned calls

**Fix that works:** When the model returns N parallel tool calls, use `message.model_copy(update={"tool_calls": [tc0]})`. This keeps the full Vertex message object (with all internal SDK metadata including tc0's valid `extra_content`), but removes tc1+ from the tool_calls list. Execute only tc0. The model re-calls tc1+ individually on subsequent turns; individual calls always have valid signatures.

**Architecture change:** `run_session_gemini` now routes through `_openai_compat_loop` (Vertex OpenAI-compat endpoint) instead of `_run_gemini_native_loop` (native genai SDK). The native SDK path exposed thought_signature as a Pydantic field; the OpenAI-compat path hides it inside `extra_content` where we can manage it.

**Cost:** N parallel calls → N sequential turns. Coordinator latency increases proportionally to how many parallel calls it makes per turn. Each tool call that was dropped adds one API round-trip. This is the price of the Vertex bug.

**Location in code:** `_openai_compat_loop` → `else` branch when `len(message.tool_calls) > 1`.

## Status

- **SSE streaming:** complete, confirmed working (Anthropic path tested live)
- **Vertex thought_signature bug:** fixed — no 400 errors in testing; sequential fallback confirmed functional to turn=6+
- **PWA client-side SSE:** deferred to follow-up session
- **HF_TOKEN:** read-only token added to `.env` ✓
