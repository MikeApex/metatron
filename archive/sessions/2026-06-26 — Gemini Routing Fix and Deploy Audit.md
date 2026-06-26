# 2026-06-26 — Gemini Routing Fix and Deploy Audit

## What happened

Anthropic API credit error appearing in Metatron browser UI. Diagnosed root cause, fixed routing, deployed, and fixed a second bug revealed by live testing.

---

## Root causes found and fixed

### 1. Silent Anthropic fallback in router (primary cause)
**File:** `core/router.py:109`

`resolve_model()` used `agent_cfg.get("provider", "anthropic")` as the default. If any agent name was not listed in `routing_cloud.yaml`, it silently routed to Anthropic instead of raising an error. On the VM with `DEPLOYMENT_MODE=cloud`, this caused an Anthropic API call that failed with a credit balance error.

**Fix:** Unknown agents now raise `RuntimeError` (logged to `data/logs/routing_fallbacks.json`). Known agents with a missing `provider` field default to `"gemini"`.

### 2. Empty string provider bypassing router (secondary cause, found during live test)
**File:** `core/orchestrator.py:1578`, `1885`

The browser sends `provider: ""` (empty string from the "Auto (server routing)" `<option value="">` dropdown). Both `_run_single_agent()` and `run_pipeline_session_stream()` checked `if provider is None` — so empty string slipped through as an unrecognised provider and hit the new RuntimeError.

**Fix:** Both checks changed to `if not provider` so `None` and `""` are treated identically.

### 3. Other defaults cleaned up
- `run_interactive()` default arg: `"anthropic"` → `"gemini"`
- `core/server.py` CLI `--provider` default: `"anthropic"` → `"gemini"`
- `_run_single_agent()` `else` branch (unrecognised provider): now raises `RuntimeError` with a clear message instead of calling Anthropic

---

## Error tracking added

New `log_model_error()` function in `core/router.py` — writes to `data/logs/model_errors.json` with: timestamp, agent, provider, model, error string.

Called from:
- `_openai_compat_loop` — wraps `client.chat.completions.create()` in try/except; logs and re-raises on any API exception
- `run_session_gemini_grounded` — same pattern around `client.models.generate_content()`
- `run_session_gemini_cached` — existing fallback already caught exceptions; now also logs to model_errors.json
- `_run_single_agent` — logs before raising on unrecognised provider
- Synthesizer anthropic streaming branch — logs warning + model_error entry if ever reached (unexpected on VM)

---

## Files deployed

Committed as two commits (`06f85b7`, `e0c57b2`), deployed via `./deploy.sh`:

| File | Change |
|---|---|
| `core/router.py` | Unknown-agent error + `log_model_error()` + `_MODEL_ERROR_LOG` |
| `core/orchestrator.py` | Empty-string provider fix (2 sites); error tracking (4 sites); run_interactive default |
| `core/server.py` | CLI --provider default |
| `config/modules/scheduler.yaml` | `ambient_refresh` schedule (every 180 min) |
| `config/profile.yaml` | New — user biographical profile (name, London, timezone) |
| `tools/ambient.py` | New — deployed to fix "No module named 'tools.ambient'" warning |

---

## Verified working

1. SSH test via `python -m core.orchestrator --agent synthesizer --input "Hello" --persona mike` — trace showed `[ROUTE] synthesizer → gemini/models/gemini-3.1-pro-preview`, no Anthropic calls
2. HTTP POST to `/session` with `persona=mike` — clean response, no Anthropic in VM logs
3. Browser (via Tailscale) — confirmed working after second fix deployed

---

## Observations / follow-up

- **Token budget OVER_8K** on every session — system prompt + goals YAML is large (~12K input tokens). Not a blocker; worth addressing in A8 refactor.
- **Vertex cache below minimum** warning on short prompts — `<4096 tokens` triggers cache creation failure + fallback to uncached. Harmless; logs a WARNING. Worth noting if we ever want caching on quick interactions.
- **Coordinator dispatches "Mental Wellbeing"** (with space and capital M) — `_normalize_agent()` should handle this, but worth monitoring for unknown-agent errors.
