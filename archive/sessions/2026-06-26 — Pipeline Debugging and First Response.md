# 2026-06-26 — Pipeline Debugging and First Response

## What this session covered

End-to-end debugging of the Coordinator → Synthesizer pipeline after the Step 6 single-pass Coordinator restructure (implemented 2026-06-24). The pipeline was returning empty responses on all paths (phone, browser, Book). This session traced and fixed three root causes, confirmed the first live response via browser, then began latency planning.

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

## Agent name mismatch (still open)

Coordinator outputs agent names as "Physical Health", "Mental Wellbeing", etc. (title-cased, spaced). The dispatch code calls `load_agent("Physical Health")` which looks for `config/agents/Physical Health.md` (doesn't exist). Actual files are `physical_health.md`, `mental_wellbeing.md`, etc.

Result: any session where MW or PH specialists are dispatched, they silently fail. Diarist still runs (fire-and-forget, name matches). Synthesizer runs without specialist context.

**Fix needed:** Add a name normalization step in `_dispatch_from_coordinator` — either a mapping dict or update coordinator.md to list technical names (underscored). Deferred to latency session.

---

## Latency baseline (current)

Pipeline observed at ~25–45 seconds for conversational sessions, browser. Breakdown:
- Coordinator (single pass, Gemini Pro, no tools): ~5–8s
- Specialists (parallel, Flash-Lite): ~10–15s per active specialist
- Synthesizer (Gemini Pro, write_context_tracker + text): ~10–20s
- Transcription (ffmpeg + faster-whisper base.en, CPU): ~2–5s (voice path only)

Main lever: Coordinator model. It now does a single routing pass with no tools — Flash or Flash-Lite should work. Not yet tested.

---

## Commits this session

- `be68363` — Fix: capture Synthesizer text when emitted alongside tool call in same turn; revert metatron_monitor DEFAULT_SERVER to https
- `3f400aa` — Debug: log native loop turn details (temporary, removed in next commit)
- `1527491` — Fix: don't pass tools=[] to Gemini API — omit tools param when no schemas
- `780623f` — Fix agent instructions: Coordinator format mandate + Synthesizer text+tool ordering

---

## What's next

1. **Agent name normalization** — `_dispatch_from_coordinator` fix so "Physical Health" → `physical_health`
2. **Coordinator model** — test Flash/Flash-Lite for routing pass; Pro is overkill for a single-pass routing directive
3. **Latency reduction** — measure actual component times; consider Coordinator model downgrade, then streaming path for Synthesizer output
4. **Resume A7 gate items** — B1 (red team), Check 10 (agent audits), Check 12 (constitution review) once pipeline is stable
