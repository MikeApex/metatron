# Vertex AI Setup — Prompt for Dedicated Chat
*Created: 2026-06-17. Use this to open a fresh chat window for the Vertex/GCP setup session.*

---

## Context for the new chat

This project is a voice-first personal AI life manager built on a Python orchestrator (`core/orchestrator.py`) with a FastAPI server (`core/server.py`) and a PWA front end (`static/index.html`). It currently runs locally on a Mac with Ollama for local model inference and direct Anthropic/Gemini APIs for cloud paths. The goal of this session is to stand up a Google Cloud / Vertex AI environment so the tool can run on a GCP VM using Gemini 3.1 Pro via Vertex AI — initially for testing, potentially as the production path.

Read these files before starting:
1. **[CLAUDE.md](../../CLAUDE.md)** — architecture, conventions, terminology. Pay attention to the provider/model naming conventions.
2. **[SESSION.md](../../SESSION.md)** — current project state, what's built, what's in progress.
3. **[core/orchestrator.py](../../core/orchestrator.py)** — the runtime. Gemini sessions run via `run_session_gemini()` and `run_session_gemini_grounded()`. This is what needs to move to Vertex.
4. **[config/modules/routing.yaml](../../config/modules/routing.yaml)** — current model routing assignments. Gemini model IDs here may be stale (flagged ⚠ in SESSION.md).

---

## What this session should accomplish

Work through the following in order. Don't skip ahead — each step gates the next.

### Step 1 — GCP account and project setup
- Confirm or create a GCP account and billing-enabled project
- Enable the Vertex AI API for the project
- Verify region selection (us-central1 recommended for Gemini model availability; confirm current availability before committing)

### Step 2 — Verify Gemini 3.1 Pro availability on Vertex
- Confirm the current model ID for Gemini 3.1 Pro on Vertex AI (`gemini-3.1-pro-preview` was the last known ID but is flagged as potentially stale)
- Confirm Gemini 3.1 Flash availability and its current model ID
- Update `config/modules/routing.yaml` with verified IDs

### Step 3 — Authentication and credentials
- Create a GCP service account with the minimum required roles for Vertex AI inference (`roles/aiplatform.user` is the target — confirm this is sufficient)
- Generate and download a service account key (JSON)
- Confirm how credentials should be provided to the orchestrator (environment variable `GOOGLE_APPLICATION_CREDENTIALS` pointing to the key file, or Application Default Credentials via `gcloud auth`)
- Do NOT commit the key file to the repo

### Step 4 — Code: switch Gemini sessions from AI Studio to Vertex
The orchestrator currently uses the `google-genai` SDK (`google-genai==2.8.0` installed in `.venv`). The same SDK supports Vertex AI with a different client initialisation. The change should be minimal — swap the client init in `run_session_gemini()` and `run_session_gemini_grounded()` from AI Studio mode to Vertex mode. Confirm the exact SDK call before editing.

Specifically:
- Identify the current client initialisation in `core/orchestrator.py` for Gemini sessions
- Confirm the Vertex AI equivalent (likely `genai.Client(vertexai=True, project=PROJECT_ID, location=REGION)`)
- Make the targeted edit — do not rewrite surrounding code
- Add `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` to the project's `.env` alongside existing keys

### Step 5 — Smoke test
- Run a single Research Agent session through the Vertex path: `python core/orchestrator.py --agent research_agent --provider gemini`
- Confirm the response comes back, model ID in the response matches the Vertex model, and no AI Studio credentials are used
- If grounded search is tested, confirm `run_session_gemini_grounded()` also works via Vertex

### Step 5b — Routing config split
Before the VM exists, create two routing config files so local and VM environments never share a single file that gets manually edited per-environment:

- `config/modules/routing.yaml` — keep as-is for local dev (current Ollama + direct API settings)
- `config/modules/routing_cloud.yaml` — new file, copy of `routing.yaml` with all agents re-pointed to Vertex Gemini 3.1 Pro; remove all `local: true` entries and Ollama references; set `provider: gemini` and `model: gemini-3.1-pro-preview` (verified ID from Step 2) for all agents

Add a `DEPLOYMENT_MODE` environment variable check to orchestrator startup in `core/orchestrator.py` — before routing config is loaded, read `os.environ.get("DEPLOYMENT_MODE", "local")` and load `routing_cloud.yaml` if value is `cloud`, otherwise load `routing.yaml`. This is the only toggle needed; no other code changes per environment. Add `DEPLOYMENT_MODE=cloud` to the VM's `.env` file; local `.env` omits it or sets `local`.

### Step 6 — VM setup (if proceeding beyond testing)
This step is optional for a pure testing run but required if moving toward always-on cloud hosting. Only proceed if Step 5 passes cleanly.

- Provision a `e2-medium` GCP VM (2 vCPU, 4GB RAM — sufficient for the orchestrator; it does no local inference)
- Region: match the Vertex AI region from Step 1
- OS: Debian 12 or Ubuntu 22.04 LTS
- Set up: Python 3.11+, clone repo, install dependencies from `requirements.txt` (or `pip install -r requirements.txt` in a venv)
- Transfer `.env` file securely (do not commit; use `gcloud compute scp` or Secret Manager)
- Confirm the server starts: `python core/server.py` — PWA should be accessible
- Set up a systemd service for `core/server.py` and `core/scheduler.py` so they restart on reboot

### Step 6b — Git-based auto-deploy workflow
Set up a post-push hook so the VM always pulls the latest code automatically whenever you push from your Mac. This removes the manual step of SSHing to the VM and prevents local code from drifting ahead of the VM without noticing.

**On your Mac — create `.git/hooks/post-push`:**
```bash
#!/bin/bash
# Auto-deploy to GCP VM on every push to main
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" = "main" ]; then
  echo "Deploying to VM..."
  gcloud compute ssh <VM_INSTANCE_NAME> --zone=<ZONE> -- \
    "cd ~/multi-model-mcp && git pull origin main && source .venv/bin/activate && pip install -q -r requirements.txt && sudo systemctl restart orchestrator && sudo systemctl restart server"
fi
```
Make it executable: `chmod +x .git/hooks/post-push`

Fill in `<VM_INSTANCE_NAME>` and `<ZONE>` from Step 6. The hook fires automatically on every `git push` to `main` — no manual deploy step required.

**What the VM-side command does:**
1. `git pull origin main` — brings the VM up to the latest commit
2. `pip install -q -r requirements.txt` — picks up any new dependencies
3. `systemctl restart orchestrator` / `restart server` — live-reloads the running services

The hook lives in `.git/hooks/` which is local-only (not committed), so it doesn't affect other contributors. If SSH key auth to the VM is set up (`gcloud compute ssh` uses Application Default Credentials or a stored key), the hook runs silently.

**To verify the setup is working:** after the first push with the hook in place, SSH to the VM and run `git log -1` — it should match your latest local commit hash.

### Step 7 — VPC and networking (if production-grade privacy is required)
Only relevant if this setup is being treated as a privacy-grade deployment rather than a test environment.

- Confirm whether VPC Service Controls are configured (required for "data never leaves Google network" guarantee)
- Set up firewall rules: only allow inbound HTTPS (443) to the VM; close all other ports
- If testing from a phone or remote device, configure the domain or IP and TLS (existing `certs/` setup may need to be redone for the VM's IP)

---

## Key constraints — do not violate

- **Model naming:** always refer to models by full ID (`gemini-3.1-pro-preview`, not "Gemini Pro"). Verify IDs against current Vertex availability before using them in code.
- **Privacy routing:** Vertex is only being used for decontextualized cloud paths (Research Agent, model conferences) under the current privacy ruling. Do not route sensitive agents (coordinator, synthesizer, mental_wellbeing, physical_health, etc.) to Vertex unless the privacy ruling has been explicitly revised. Those agents must remain on Ollama (local) or fail closed.
- **No rewrites:** make targeted edits only. The orchestrator is working; change only what the Vertex switch requires.
- **No co-authored-by in commits.**

---

## Open questions to resolve during the session

1. Does the `google-genai` SDK (v2.8.0, already installed) support Vertex AI, or does it need to be swapped for `google-cloud-aiplatform`? Confirm before touching code.
2. Is `gemini-3.1-pro-preview` the correct model ID on Vertex today, or has it been superseded?
3. Zero Data Retention on Vertex: is ZDR available on the developer/standard tier, or does it require a specific enterprise agreement? Confirm before treating this as a privacy-grade deployment.
4. Does Gemini 3.1 Pro on Vertex support the same grounded search capability currently used in `run_session_gemini_grounded()`?
