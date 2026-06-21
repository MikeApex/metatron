# 2026-06-19 — Native SDK Migration (Gemini)

## What was built

Replaced `run_session_gemini()`'s use of `_openai_compat_loop()` with a native `google-genai` SDK agentic loop. All Gemini agents (coordinator, synthesizer, all specialists) now route through the native SDK instead of the Vertex AI OpenAI-compat endpoint.

## Files changed

- `core/orchestrator.py` — only file touched

## New functions added (all in `core/orchestrator.py`)

| Function | Purpose |
|---|---|
| `_clean_schema_for_gemini(schema)` | Recursively strips empty-string enum values that the Gemini API rejects (affects `run_subagent` `complexity` enum) |
| `_to_gemini_tools(anthropic_schemas)` | Converts Anthropic tool schemas to `types.Tool(function_declarations=[...])` format using `FunctionDeclaration` — accepts raw `input_schema` dict directly |
| `_run_gemini_native_loop(client, model_name, ...)` | Full agentic loop: multi-turn `contents` list, tool dispatch (sequential + parallel via `ThreadPoolExecutor` for `_PARALLEL_TOOLS`), token budget logging, AI_TRACE markers, max_iterations guard, history threading |

## `run_session_gemini()` — what changed

Old: fetched a Vertex bearer token, constructed an OpenAI-compat base URL, called `_openai_compat_loop()`.

New: creates `genai.Client(vertexai=True, ...)` or `genai.Client(api_key=...)` (same pattern as `run_session_gemini_grounded()`), strips `models/` prefix for Vertex, calls `_run_gemini_native_loop()`.

## Unchanged

- `_openai_compat_loop()` — still used by OpenAI and Ollama paths
- `run_session_gemini_grounded()` — Research Agent path untouched
- `filter_output()`, `dispatch_tool()`, `_PARALLEL_TOOLS`, `_trace()`, `_to_openai_tools()`
- Three Vertex helper functions (`_get_vertex_bearer_token`, `_vertex_openai_base_url`, `_vertex_model_name`) — now unused but left in place

## SDK facts confirmed during investigation

- `FunctionDeclaration(parameters=<dict>)` — accepts raw JSON Schema dicts directly; no recursive type conversion needed
- `FunctionCall.args` — plain Python dict
- `Part.from_function_response(*, name, response)` — keyword-only args; `response` takes a `{"result": str}` dict
- `Part.function_call` / `Part.text` — `None` when not set (falsy checks work)
- Empty-string enum values (`""`) — accepted by OpenAI compat layer but rejected by native Gemini API (`INVALID_ARGUMENT`)

## Testing

**Smoke test (single-shot):**
```
AI_TRACE=1 DEPLOYMENT_MODE=cloud python core/orchestrator.py \
  --input "I went for a run this morning and feeling pretty good today."
```
Result: full coordinator pipeline, 3 parallel subagents, synthesizer — all via `gemini-native/` path. Tool dispatch clean. Token budget logging correct. 71s wall clock (7 API calls: coordinator × 3 turns + 3 subagents × 2 turns + synthesizer × 2 turns).

**Interactive history-threading test (two-turn REPL):**
Turn 1: "I had a productive morning — finished the main coding task I was working on."
Turn 2: "What did I just tell you I finished?"
Result: second turn correctly answered from history without specialist calls. History `role` mapping (`"assistant"` → `"model"`) worked correctly.

## Decisions

- Schema conversion: used `FunctionDeclaration(parameters=<raw dict>)` instead of a recursive `types.Schema` converter — SDK handles it internally, simpler and correct
- Empty enum fix: applied in `_clean_schema_for_gemini()` at conversion time rather than modifying `RUN_SUBAGENT_SCHEMA` — keeps Anthropic/OpenAI schemas unaffected
- Old Vertex helper functions left in place (unused) rather than deleted — no risk, avoids noise in diff

## Open items

None from this session. The 20s wall-clock regression target applies to simple single-agent sessions, not the full coordinator pipeline. Native SDK eliminates bearer token fetch + compat translation layer per call; equivalent workloads should be at or below the old compat path.
