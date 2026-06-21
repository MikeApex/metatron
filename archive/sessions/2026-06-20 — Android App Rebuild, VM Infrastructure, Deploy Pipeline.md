# Session: Android App Rebuild, VM Infrastructure, Deploy Pipeline
*2026-06-20 – 2026-06-21*

---

## What was built / done

### Vertex SDK
- Parallel chat (Chat A) migrated `run_session_gemini()` to native Vertex SDK, then reverted in the latency session due to `thought_signature` bug on parallel tool calls
- Current path: Vertex OpenAI-compat endpoint via `_openai_compat_loop` + `_resolve_gemini_credentials` — still Vertex, not AI Studio
- SESSION.md corrected to reflect reversion

### GCP VM
- `metatron-vm`, `e2-medium` (2 vCPU / 4 GB), Debian 12, `us-central1-a`
- External IP: `35.202.250.80` (unused — Tailscale only)
- Tailscale IP: `100.64.226.49` — phone connects here
- Python 3.11, ffmpeg, 95 deps installed from generated `requirements.txt`
- Repo transferred via `git archive` tar + `gcloud compute scp`
- Vertex credentials: service account `metatron-vertex@metatron-ai-499810.iam.gserviceaccount.com`, key at `~/multi-model-mcp/vertex-key.json`, `GOOGLE_APPLICATION_CREDENTIALS` in `.env`
- systemd: `metatron-server.service` + `metatron-scheduler.service` — both enabled, restart on crash/reboot
- Health confirmed: `curl http://100.64.226.49:8001/health` → `{"status":"ok"}`

### GitHub
- Repo: `github.com/MikeApex/metatron` (private)
- Mac SSH key: `~/.ssh/github_mikeapex`
- VM deploy key: `~/.ssh/github_deploy` (read-only, named `metatron-vm` in GitHub)
- VM set to `git config pull.rebase false`

### Deploy pipeline
- `deploy.sh`: pushes to GitHub → VM pulls → restarts services
- Post-commit hook (`.git/hooks/post-commit`): prints deploy reminder after every commit
- `requirements.txt` generated and committed (95 packages)

### Always-on Mac backup
- Deferred — VM is primary host
- Toggle instructions added to SESSION.md Quick Start and top of `config/modules/routing.yaml`
- Memory saved: proactively remind when switching to `DEPLOYMENT_MODE=local`

### Login/profile screen (`static/index.html`)
- Login screen on first launch; auto-logins on return via `localStorage`
- Persona dropdown: `mike` (User group) + 9 test personas (pepys, danny_park, maya_torres, sarah_chen, arthur_brooks, cal_newport, ryan_holiday, oliver_burkeman, test_a3)
- Password field: UI only, not enforced
- Persona chip in header top-right — tap to return to login and switch
- `sendToServer` passes `persona: currentPersona` in every API call
- `requestMicPermission()` + `initPush()` deferred to post-login

### APK rebuild
- Java 21 installed via Homebrew (required by Capacitor; 17 fails)
- `SERVER` constant updated: `100.70.67.45` → `100.64.226.49`
- New icon: `metatron-mem-1.png` (user-supplied brushwork mem glyph) → `assets/icon-only.png`
- `@capacitor/assets generate` generated icons in all mipmap density folders
- Adaptive icon XMLs removed from `mipmap-anydpi-v26/` — fixes home screen icon caching (Android uses PNG directly)
- Adaptive background color updated to `#0d0d0d`
- `npx cap sync android` + `./gradlew assembleDebug` → BUILD SUCCESSFUL
- APK sideloaded via `python3 -m http.server 8888` on Mac Tailscale IP (`100.70.67.45:8888`)
- Tailscale always-on enabled on phone

---

## Key values

| What | Value |
|---|---|
| VM Tailscale IP | `100.64.226.49` |
| GCP project | `metatron-ai-499810` |
| VM zone | `us-central1-a` |
| GitHub repo | `git@github.com:MikeApex/metatron.git` |
| Deploy command | `./deploy.sh` (from Mac project root) |
| VM SSH | `gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810` |
| APK location | `android/app/build/outputs/apk/debug/app-debug.apk` |
| APK server | `cd android/app/build/outputs/apk/debug && python3 -m http.server 8888` |

---

## Open / next
- **End-to-end app test** — test prompt at `archive/plans/android_test_prompt_2026-06-20.md`
- **Persona data on VM** — `mike` data lives on Mac; Goals Interview needs to be run on VM (D1 item)
- **Kokoro TTS not on VM** — edge-tts fallback active; voice quality differs from Mac
- **Coordinator slimming** — handed to separate chat; target ≤3 turns, ≤40K tokens
- **A7 sign-off** — blocked on B1/Check10/Check12; resume after pipeline stabilises
