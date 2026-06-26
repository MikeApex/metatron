# 2026-06-26 — Pipeline Debugging, First Response, and Latency Work

## What this session covered

Two phases. Phase 1: end-to-end debugging of the Coordinator → Synthesizer pipeline after the Step 6 single-pass Coordinator restructure (implemented 2026-06-24). The pipeline was returning empty responses on all paths (phone, browser, Book). Three root causes traced and fixed; first live response confirmed via browser. Phase 2: latency reduction — agent name normalization, Coordinator model downgrade, Vertex cache fix, trace.py commit, streaming client, and streaming thought_signature fix. Warm-cache second-message latency dropped from ~40s to ~20s.

---

## Bugs found and fixed (in order)

### 1. `allowed_tools: []` → invalid API call (critical, root cause)

`_to_gemini_tools([])` was returning `[types.Tool(function_declarations=[])]` — a Tool object with zero declarations. The Gemini API rejects this, causing the native loop to throw on every Coordinator call (Coordinator has `allowed_tools: []`). The exception fell back to the compat loop, which passed `tools=[]` to the Vertex OpenAI-compat endpoint, which returned `content=None`. Result: Coordinator always returned `""`.

**Fixes:**
- `_to_gemini_tools([])` now returns `[]` for empty input
- Native loop: `_tools_kwarg = {"tools": gemini_tools} if gemini_tools else {}` — omits tools param when empty
- Compat loop: `**({"tools": oai_tools} if oai_tools else {})` — same

### 2. Synthesizer: text+tool_call in same response, text discarded

Gemini can produce text and a function_call in the same response turn. Both loops were only capturing text when `finish_reason != "tool_calls"` — so when the Synthesizer produced a user-facing response alongside `write_context_tracker`, the text was discarded, the tool executed, and the next turn returned nothing.

**Fixes:**
- `_run_gemini_native_loop`: `if text_parts: result = "\n".join(text_parts)` moved before the function_call check — captures text regardless of whether function_calls are also present
- `_openai_compat_loop`: `result = ""` pre-declared; `if message.content: result = message.content` captures text before entering the tool-call branch

### 3. Agent instruction gaps (Coordinator format + Synthesizer ordering)

After fix 1, the Coordinator started producing output but in conversational prose ("Test 4 received.") instead of the SPECIALISTS_TO_CALL structured package. After fix 2, the Synthesizer was still returning empty because it was calling `write_context_tracker` as a standalone tool call with no text, then producing nothing on the next turn.

**Fixes:**
- `config/agents/coordinator.md`: Added hard mandate — "You never produce user-facing responses. Your only output is the structured context package below, every single time, with no exceptions."
- `config/agents/synthesizer.md`: Added ordering rule — "Call `write_context_tracker` and produce your text response in the same output turn — both together, not sequentially. If you receive a tool result after `write_context_tracker`, do NOT produce a follow-up."

**Result:** First live response received via browser after these fixes.

---

## Other fixes this session

- **`tools/metatron_monitor.py` DEFAULT_SERVER**: Reverted `http://` → `https://100.64.226.49:8001` — VM has Tailscale certs (`certs/server.crt`/`server.key`) so the server runs HTTPS. The Book was failing to load personas due to this mismatch.

- **Transcription location**: Confirmed 100% on VM. Phone records WebM/Opus, sends to `/transcribe`, VM runs ffmpeg decode + faster-whisper `base.en` on CPU, returns text. Two sequential HTTP calls (transcribe then session) before pipeline starts.

- **Mac terminal mode**: `python3 -m core.orchestrator --agent coordinator --persona mike` from project root with venv active. Uses Ollama (local routing.yaml, no DEPLOYMENT_MODE=cloud). Works and has good latency (Ollama, no Vertex round-trips). Not production path — useful for local testing.

- **Browser access**: `https://metatron-vm.tail0acc5d.ts.net:8001` — server mounts `static/index.html` at `/`. Full UI available from Mac browser via Tailscale. No APK rebuild needed.

---

## Agent name mismatch — fixed in phase 2

Coordinator outputs agent names as "Physical Health", "Mental Wellbeing", etc. (title-cased, spaced). The dispatch code was looking for `config/agents/Physical Health.md` which doesn't exist.

**Fix:** `_normalize_agent()` in `_dispatch_from_coordinator` — explicit map for multi-word names + generic fallback (`lower().replace(" & ", "_").replace(" ", "_")`). Covers all variants including single-word capitalized names (Logistics, Finance, etc.).

---

## Phase 2 — Latency reduction

### Baseline (before phase 2)
- ~27–45s per conversational session (all paths: phone, browser, curl)
- Every agent call doing double round-trip: native loop failed → compat fallback
- Agent name normalization failures silently dropping MW, PH, Logistics on every session
- Coordinator on Pro (no tools, single-pass — Pro was overkill)
- No streaming — user waited for full pipeline before seeing any text

### Changes made

**1. Agent name normalization** — MW, PH, and all other spaced/titled variants now resolve. Fixed silently-failing specialists on every session.

**2. Coordinator: Pro → Flash-Lite** (`routing_cloud.yaml`) — single-pass routing directive with `allowed_tools: []`. Previous revert reason ("Flash skips tool calls") no longer applies. Saves ~3–5s.

**3. Vertex cache fix** — Cache was created with `system_instruction` only; the native loop then tried to pass `tools` in the same request, which Vertex rejects ("Tool config, tools and system instruction should not be set in the request when using cached content"). Fix: `_get_or_create_vertex_cache` now accepts `tool_schemas` and includes tools in `CreateCachedContentConfig`. Cache key includes tool names. GenerateContentConfig with `cached_content` no longer includes tools or system_instruction. Eliminated the guaranteed native-loop-fail + compat-fallback double round-trip on every tool-bearing agent call.

**4. trace.py committed** — `ToolCallRecord.input_tokens`/`output_tokens` fields and matching `record_tool_call` signature were applied locally but never committed. VM had the old version without these params, which crashed the native loop once the cache fix made it actually run.

**5. Streaming client** (`static/index.html`) — coordinator agent now calls `/session/stream` (SSE) instead of `/session`. Text streams into the assistant bubble word-by-word with a `▍` cursor. TTS fires when `[DONE]` arrives. Non-coordinator agents still use `/session` (blocking). Future TODO: phrase-by-phrase TTS with meaningful pauses between sentences.

**6. Streaming thought_signature fix** — `_openai_compat_stream` was written assuming the Synthesizer never calls tools ("NOTE: Only the Synthesizer uses this function at runtime — it never calls tools"). Now it does (`write_context_tracker`). Stream deltas don't carry Vertex's `thought_signature`, so the reconstructed assistant dict caused a 400 on the next request. Fix: when a streaming turn produces tool calls, replay that turn blocking (`stream=False`) using the pre-turn messages snapshot; apply the same `model_copy()` thought_signature workaround from `_openai_compat_loop`. Streaming text already yielded is correct; replay used only for the signed assistant message.

### Results
- First call (cold cache, 3 specialists): ~55–66s (one-time cache creation overhead)
- Second+ call (warm in-memory cache): **~20s**
- Previously: ~40s every call, no streaming
- Synthesizer now shows `cache_read=12000+` tokens — cache is working
- No more "native loop failed" warnings in VM logs

### Observations from test sessions (Danny Park, Maya Torres, Mike)
- Agent name normalization confirmed working: physical_health, mental_wellbeing dispatching correctly
- Coordinator producing high-quality SPECIALISTS_TO_CALL packages with contextualized directives
- Synthesizer cache hit visible in logs: `cache_read=12005` on turns 1 and 2
- Specialists still running 5–8 tool-call turns — this is the next major latency lever (token reduction Steps 3–5 of plan)
- Constitution already stripped from specialists (confirmed in code — was noted as incomplete in plan doc but was actually done)

---

## Commits (phase 2)

- `ad9081a` — Agent name normalization + Coordinator Flash-Lite downgrade
- `85e0f52` — Vertex cache: bake tools into cache; strip tools from cached request
- `b10806c` — Generic name normalization fallback (fixes Logistics, Finance, etc.)
- `69f75fe` — Commit trace.py changes (missing from git; crashed native loop)
- streaming commits — streaming client + thought_signature fix for streaming tool-call turns

---

## What's next

1. **Specialist token reduction** (plan Steps 3–5) — specialists running 5–8 turns of tool calls; reducing context/tool overhead is the biggest remaining latency lever
2. **Resume A7 gate items** — B1 (red team), Check 10 (agent audits), Check 12 (constitution review) once pipeline is stable
3. **Phrase-by-phrase TTS** — future streaming enhancement; marked with TODO in index.html
