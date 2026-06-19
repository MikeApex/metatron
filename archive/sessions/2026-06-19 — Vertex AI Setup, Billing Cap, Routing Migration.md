# Session: Vertex AI Setup, Billing Cap, Routing Migration
*2026-06-18 → 2026-06-19*

---

## What was built / done

### 1. Flash model ID update
- `GEMINI_MODEL` in `core/orchestrator.py` updated: `gemini-3.1-flash-lite-preview` → `gemini-3.1-flash-lite`
- `quick_override` model in `config/modules/routing.yaml` updated to match
- Old preview ID discontinues July 9, 2026

### 2. GCP project setup
- Project: `metatron-ai-499810` (billing linked, Vertex AI API enabled)
- gcloud CLI installed via Homebrew
- Application Default Credentials (ADC) configured via `gcloud auth application-default login`
- Quota project linked: `gcloud auth application-default set-quota-project metatron-ai-499810`

### 3. Billing hard-cap at $20
- Pub/Sub topic created: `billing-cap`
- Cloud Function `stop-billing` deployed (Python 3.11, Gen2, us-central1)
- Budget created and linked to `billing-cap` Pub/Sub topic
- Function service account granted `roles/billing.projectManager`
- When budget hits $20 → Pub/Sub fires → function removes billing account → all API usage stops

### 4. Vertex AI code migration
- `run_session_gemini_grounded()` updated: checks for `GOOGLE_CLOUD_PROJECT` env var; if set, uses `genai.Client(vertexai=True, project=project, location=location)` instead of AI Studio `api_key` path
- `models/` prefix stripped from model name when in Vertex mode (Vertex does not accept this prefix)
- `.env` updated: `GOOGLE_CLOUD_PROJECT=metatron-ai-499810`, `GOOGLE_CLOUD_LOCATION=global`
- Key discovery: Gemini 3.x models on Vertex require `location=global`, not `us-central1`
- Smoke test passed: Research Agent via Vertex returned a valid grounded response

### 5. sys.path fix
- Added `sys.path.insert(0, str(ROOT))` in `core/orchestrator.py` so `tools` module resolves correctly when running `python core/orchestrator.py` from the project root

### 6. routing_cloud.yaml + DEPLOYMENT_MODE toggle
- Created `config/modules/routing_cloud.yaml`: all 14 agents on `gemini-3.1-pro-preview` via Vertex; `local_enabled: false`; no Ollama references
- `core/router.py` updated: `_ROUTING_CONFIG` (module-level constant) replaced with `_routing_config_path()` function evaluated at call time — fixes import-order bug where `DEPLOYMENT_MODE` from `.env` wasn't set when the constant was first read
- `DEPLOYMENT_MODE=cloud` added to `.env` to activate cloud routing by default on this machine

### 7. Repository cleanup
- `.gitignore` expanded: added `.DS_Store`, `android/`, `node_modules/`, `certs_backup/`, `data/audio/`, `data/baselines/`, `data/context.json`, `data/conversations/`, `data/push_subscriptions.json`, `data/voices/`, `data/personas/mike/`, `data/personas/pepys/`, test persona runtime data, `config/personas/mike.md`, `config/personas/mike/`, `archive/sessions/*.txt`, `archive/transcripts/`
- All previously untracked project files committed (108 files): agent configs, tests, tools, plans, session archives, scripts, Capacitor config

### 8. Three git commits
- `b5be14d` — Vertex AI migration (orchestrator, router, routing configs)
- `c912998` — Phase 5 session catchup (agents, logging, server, PWA, tools)
- `ddd75cd` — All previously untracked files + updated .gitignore

---

## Key decisions

- **`DEPLOYMENT_MODE=cloud`** in local `.env` — routes all agents through Vertex Gemini 3.1 Pro from the Mac. Ollama not needed when this is set.
- **`run_session_gemini()` not yet migrated to Vertex** — coordinator/synthesizer/specialists still go through AI Studio OpenAI-compat endpoint. Only `run_session_gemini_grounded()` (research_agent) is on Vertex. This is the main remaining code task for full Vertex migration.
- **Pipeline latency measured: 60–90 seconds** for a simple voice prompt end-to-end on the multi-agent pipeline. All agents on Gemini 3.1 Pro = 3–5 sequential heavy model calls.
- **Vertex billing hard-stop over GCP alerts** — user wanted automated shutdown, not just email notification. Pub/Sub + Cloud Function implementation chosen.
- **Vertex location = `global`** — Gemini 3.x models require this; `us-central1` returns 404 for publisher models.

---

## Open items / next sessions

1. **Migrate `run_session_gemini()` to Vertex native SDK** — same pattern as `run_session_gemini_grounded()`; this completes ZDR coverage for the full pipeline
2. **Efficiency conversation** — prompt written and ready; covers model tiering (Flash for coordinator/synthesizer, Pro for specialists), Diarist fire-and-forget, output compression + action tags, prefix caching, instruction file slimming. See prompt at end of this session.
3. **Android app session** — prompt written and ready; covers VM endpoint update, Tailscale dual-network, always-on, login/profile selection
4. **VM provisioning** — Step 6 of `archive/plans/vertex_setup_prompt_2026-06-17.md` not yet done; Metatron infrastructure hold lifts once VM is provisioned

---

## Files changed this session

- `core/orchestrator.py` — flash model ID, Vertex client in `run_session_gemini_grounded()`, prefix strip, sys.path fix
- `core/router.py` — `_routing_config_path()` function replacing module-level constant
- `config/modules/routing.yaml` — flash model ID
- `config/modules/routing_cloud.yaml` — new
- `.env` — `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `DEPLOYMENT_MODE`
- `.gitignore` — expanded significantly
