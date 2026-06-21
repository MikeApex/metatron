# Session: VM Provisioning, GitHub, Deploy Pipeline
*2026-06-20*

---

## What was built / done

### 1. Vertex SDK migration confirmed
- `run_session_gemini()` migrated to native Vertex SDK by a parallel chat (Chat A)
- Subsequently reverted in the latency session due to Vertex `thought_signature` bug on parallel tool calls
- Current state: all Gemini agents use `_openai_compat_loop` via Vertex OpenAI-compat endpoint — still Vertex, not AI Studio
- SESSION.md updated to reflect both the migration and the reversion

### 2. GCP VM provisioned
- Instance: `metatron-vm`, `e2-medium` (2 vCPU / 4 GB), Debian 12, `us-central1-a`
- External IP: `35.202.250.80` (not used — Tailscale is the only access path)
- Python 3.11, ffmpeg, all 95 dependencies installed
- Repo transferred via `git archive` tar + `gcloud compute scp`
- `.env` transferred separately via `gcloud compute scp`

### 3. Vertex credentials on VM
- Service account `metatron-vertex@metatron-ai-499810.iam.gserviceaccount.com` created
- Granted `roles/aiplatform.user`
- Key downloaded and copied to VM at `~/multi-model-mcp/vertex-key.json`
- `GOOGLE_APPLICATION_CREDENTIALS` added to `.env` on VM

### 4. Tailscale on VM
- Installed and joined tailnet
- **VM Tailscale IP: `100.64.226.49`** — this is the new `SERVER` address for the APK
- Health check confirmed: `curl http://100.64.226.49:8001/health` → `{"status":"ok"}`

### 5. systemd services
- `metatron-server.service` — runs `core/server.py --persona mike --port 8001`, restarts on crash
- `metatron-scheduler.service` — runs `core/scheduler.py`, restarts on crash
- Both enabled (start on reboot), both confirmed `active (running)`

### 6. GitHub repo
- Account: `MikeApex` (SSH key `~/.ssh/github_mikeapex`)
- Repo: `github.com/MikeApex/metatron` (private)
- 672 objects pushed from Mac
- VM has deploy key `metatron-vm` (read-only) at `~/.ssh/github_deploy`
- VM can pull: `cd ~/multi-model-mcp && git pull origin main` confirmed working

### 7. Deploy pipeline
- `deploy.sh` in project root: pushes to GitHub, then SSHes to VM to pull + restart services
- Post-commit hook at `.git/hooks/post-commit`: prints reminder to run `./deploy.sh` after every commit
- `git config pull.rebase false` set on VM to avoid divergent branch errors

---

## Also completed (continuation of same session)

### Login/profile screen
- Added to `static/index.html` — shows on first launch, auto-logins on return via `localStorage`
- Persona dropdown: `mike` (User group) + all test personas (pepys, danny_park, maya_torres, sarah_chen, arthur_brooks, cal_newport, ryan_holiday, oliver_burkeman, test_a3)
- Password field: present in UI, not enforced
- Persona chip in header top-right — tap to return to login screen and switch persona
- `sendToServer` now passes `persona: currentPersona` in every API call
- `requestMicPermission()` and `initPush()` only called after login

### APK rebuild
- Java 21 installed via Homebrew (Capacitor requires 21, not 17)
- `SERVER` constant updated to VM Tailscale IP `100.64.226.49`
- `assets/icon-only.png` placed from `metatron-mem-1.png` (user-supplied)
- `@capacitor/assets generate` run — icons generated in all mipmap density folders
- Adaptive icon XMLs removed from `mipmap-anydpi-v26/` — Android falls back to PNG directly (fixes home screen icon not updating)
- Adaptive icon background color updated to `#0d0d0d` in `values/ic_launcher_background.xml`
- `npx cap sync android` + `./gradlew assembleDebug` → BUILD SUCCESSFUL
- APK sideloaded via `python3 -m http.server 8888` on Mac Tailscale IP — confirmed working on phone

### Always-on Mac backup
- Deferred — VM is primary host, Mac not needed
- Toggle instructions added to SESSION.md Quick Start and `config/modules/routing.yaml` header
- Memory saved: proactively remind when switching to local/Ollama mode

---

## Key values to remember

| What | Value |
|---|---|
| VM Tailscale IP | `100.64.226.49` |
| VM external IP | `35.202.250.80` (unused — don't open firewall) |
| GCP project | `metatron-ai-499810` |
| VM zone | `us-central1-a` |
| GitHub repo | `git@github.com:MikeApex/metatron.git` |
| Deploy command | `./deploy.sh` (from Mac project root) |
| VM SSH | `gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810` |

---

## Files changed / created this session

- `deploy.sh` — new; Mac→GitHub→VM deploy pipeline
- `.git/hooks/post-commit` — new; deploy reminder after every commit
- `requirements.txt` — generated from venv (95 packages); now committed
- VM: `/etc/systemd/system/metatron-server.service`
- VM: `/etc/systemd/system/metatron-scheduler.service`
- VM: `~/multi-model-mcp/.env` (includes `GOOGLE_APPLICATION_CREDENTIALS`)
