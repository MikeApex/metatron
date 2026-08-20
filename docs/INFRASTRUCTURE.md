# Infrastructure — deploy, recovery, rebuild

Detail that a coding session does not need, kept out of `CLAUDE.md` so it isn't
paid for on every chat. Nothing here is optional knowledge — it is the knowledge
you need *at a specific moment*, and this file is that moment's home.

**Read this when:**
- You are deploying, or anything about the deploy pipeline is unclear.
- A billing cap has tripped and the VM or the project is down.
- `instances start` reports `nic0 is frozen` after a billing relink.
- You are rebuilding the VM, the VPC, or the whole project from nothing.
- You are rebuilding or sideloading the Android APK.
- You are setting up local Mac / Ollama development, or pausing/resuming the VM.
- You need a systemd unit file, an env var, a service command, or the topology.

> **Scope widened 2026-08-13.** This file previously held only recovery-time
> detail, and `CLAUDE.md` carried a 301-line operational summary *plus* a pointer
> to here — 37% of a file loaded on every session, duplicating a file nobody had
> to load at all. The operational material now lives here in full.
>
> **What deliberately did *not* move: the traps.** `CLAUDE.md` keeps a short
> `Infrastructure traps` block, because those warnings fail *silently* — the
> external IP that looks removable and is the sole egress path, the Vertex 4,096-
> token cache floor, `--persona mike` being load-bearing. You only learn you
> needed them afterwards. Everything here fails *loudly*: you notice the moment
> you need it, and you come and find it.

History and reasoning live in [archive/PROJECT_LOG.md](../archive/PROJECT_LOG.md).

---

## systemd unit files (verbatim)

Both services run as user `md-homefolder`, load env from `.env`, and restart
automatically on crash. Day-to-day commands: § Service management below.

> **`--persona mike` on both units is load-bearing.** Without it the scheduler
> resolves no persona and every scheduled session writes to the global `data/`
> tree while the server writes to `data/personas/mike/`, splitting the user's
> history across two trees (2026-07-28).

**`/etc/systemd/system/metatron-server.service`**
```ini
[Unit]
Description=Metatron FastAPI Server
After=network.target tailscaled.service

[Service]
Type=simple
User=md-homefolder
WorkingDirectory=/home/md-homefolder/multi-model-mcp
ExecStart=/home/md-homefolder/multi-model-mcp/.venv/bin/python core/server.py --persona mike --port 8001
Restart=always
RestartSec=5
Environment=METATRON_PERSONA_STRICT=0
Environment=METATRON_PERSONA_FALLBACK=mike
EnvironmentFile=/home/md-homefolder/multi-model-mcp/.env

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/metatron-scheduler.service`**
```ini
[Unit]
Description=Metatron Scheduler Daemon
After=network.target metatron-server.service

[Service]
Type=simple
User=md-homefolder
WorkingDirectory=/home/md-homefolder/multi-model-mcp
ExecStart=/home/md-homefolder/multi-model-mcp/.venv/bin/python core/scheduler.py --persona mike
Restart=always
RestartSec=10
Environment=METATRON_PERSONA_STRICT=0
Environment=METATRON_PERSONA_FALLBACK=mike
EnvironmentFile=/home/md-homefolder/multi-model-mcp/.env

[Install]
WantedBy=multi-user.target
```


---

## VM spec

| Property | Value |
|---|---|
| Instance name | `metatron-vm` |
| Machine type | `e2-medium` (2 vCPU / 4 GB RAM) |
| OS | Debian 12 |
| Zone | `us-central1-a` |
| GCP project | `metatron-ai-499810` |
| External IP | ephemeral — **changes on every stop/start**, so no literal value is recorded here. Look it up if needed: `gcloud compute instances describe metatron-vm --zone=us-central1-a --project=metatron-ai-499810 --format="value(networkInterfaces[0].accessConfigs[0].natIP)"`. **Nothing connects *to* it — but it is the VM's only route *out*. Do not remove it** (see below) |
| Tailscale IP | `100.64.226.49` (production client address — unchanged across the rebuild) |
| VPC network | `metatron-net` / `metatron-subnet` (`10.10.0.0/24`), internal `10.10.0.4` |
| Firewall | `metatron-net-allow-iap-ssh` — `tcp:22` from `35.235.240.0/20` (IAP range) only; no public ingress |
| OS user | `md-homefolder` |
| Repo path | `~/multi-model-mcp` |
| Python | 3.11 |
| System packages | `python3.11`, `python3.11-venv`, `ffmpeg` |

> The external-IP trap and the do-not-record-ephemeral-values rule live in
> [CLAUDE.md](../CLAUDE.md) § GCP VM — they must fire unprompted, so they are not repeated here.

---

## Billing protection — full mechanism and recovery

**This section is the source of truth for the thresholds — do not quote them from
memory or from another file.** They have been raised four times.

| Tier | Amount | Fires | Action | Recovery |
|---|---|---|---|---|
| **Soft** | $150 | `budget-soft-cap` → `stop-vm` | stops `metatron-vm` | `gcloud compute instances start`, ~60s |
| **Hard** | $250 | `billing-cap` → `stop-billing` | disables project billing | **days** — runbook below |

> **⏳ TEMPORARY — revert both in September (Mike, 2026-08-20).** These are elevated
> to clear a known cost defect, not because the true budget changed. **When the
> September cycle resets, bring them back down** — to $100/$175 unless the
> reconciliation says otherwise. Backlog: `[DB-0820-01]`.
>
> **Raised 2026-08-20 from $100/$175** after the soft cap fired at 10:36 and stopped
> the VM mid-deploy. The trip was real, but the cause was a defect rather than usage:
> Vertex **context-cache storage** — abandoned caches, midnight-UTC expiry instead of
> a TTL, and `spend_guard` blind to storage — costing roughly $100/month
> (`archive/plans/vertex_cache_cost_control_2026-08-20_plan.md`). **Raising the caps
> buys time; that fix removes the cause.**
>
> **The gap between the tiers is the thing to protect, not the absolute numbers.**
> Soft was raised to $150 first, which would have left only **$25** before the hard
> cap — and the hard cap is an *outage*, has already fired **below** its own threshold
> once (2026-07-30, ~$31 against a $40 budget, stale notification), and sits behind
> spend figures that lag by hours. The hard cap was raised in the same pass to keep
> ~$100 of runway. Little real protection is lost: per the note below, **neither cap
> catches a runaway** — `core/spend_guard.py` is the fast path.

Raised from $70/$150 on 2026-08-09 after the Aug 1–8 reconciliation found ~$35 by
day 8 (~$4.38/day) tracking to trip the old soft cap around Aug 16, with roughly
half that window's cost coming from test-suite runs rather than routine use. $30
headroom added to each tier as a buffer. Infrastructure alone is ~$29/mo before a
single token (`e2-medium` 24/7 ~$24.50 + IP ~$3.65 + disk ~$1), so the soft cap
leaves ~$71/mo of real AI headroom.

Overrides are two **separate** GCS markers — `scripts/metatron-vm-override.sh` and
`scripts/metatron-billing-override.sh` — so silencing one never silences the other.

> **Relink billing *before* writing an override.** The marker lives in a bucket
> inside the project being disabled, so writing it while billing is off fails
> `403`. `metatron-resume.sh` had these reversed until 2026-07-30 and aborted under
> `set -e` before the relink — its automatic recovery had never once completed.

Spend figures lag by hours, so neither cap catches a runaway. The fast path is
`core/spend_guard.py`, which sees every call as it happens.

The rest of this section is the mechanism behind those thresholds, plus the
recovery runbook.

> **Why the hard cap was demoted.** On 2026-07-30 `stop-billing` fired at ~$31 against a budget already raised to $40, acting on a stale notification. Disabling billing froze the project's VPC. Billing was relinked within hours, but Google's asynchronous network thaw never ran — 25+ hours later `instances start` still returned `UNSUPPORTED_OPERATION: The default network interface [nic0] is frozen`, and creating any instance on `networks/default` returned `not ready`. Support escalated with a 3–5 business day estimate. Recovery came from building a **new VPC** (`metatron-net`) and rebuilding the VM on it.
>
> **✅ `networks/default` has since thawed — corrected 2026-08-03.** Probe-tested twice: an instance created on `default` came up `RUNNING` on `10.128.0.4`, then was deleted. Google restored it between 07-31 and 08-03, past their own 3–5 business day estimate but without further intervention. Earlier revisions of this warning told future sessions to avoid a network that works. `metatron-vm` stays on `metatron-net` by choice, not necessity — moving back would mean another rebuild for no gain.

Budget history: $20 → $30 (2026-07-27) → $40 (2026-07-30) → restructured to $70 soft / $150 hard (2026-07-31).

**Hard cap ($150 — disables billing, last resort):**

- **Budget resource:** "Metatron & Multi-Model Budget" on billing account `013F3D-66B5CD-955A3A`, `$150` monthly, calendar-period, notifying via Pub/Sub
- **Pub/Sub topic:** `billing-cap` in project `metatron-ai-499810`
- **Budget alert:** fires whenever cost exceeds the budget, publishes `{costAmount, budgetAmount}` to `billing-cap` topic — not just once on first crossing; GCP re-evaluates and re-notifies repeatedly while spend stays over budget
- **Cloud Function:** `stop-billing` (Python 3.11, Gen2, `us-central1`)
  - Trigger: Pub/Sub message on `billing-cap`
  - Action: if `costAmount > budgetAmount` **and no manual override is active**, calls `cloudbilling.disable_project_billing()` on the project
  - Retry policy: `RETRY_POLICY_DO_NOT_RETRY`
  - Source tracked at... *(not yet in the repo — currently only deployed; add under `infra/stop-billing/` if it needs another change. `infra/stop-vm/` shows the pattern.)*

**Soft cap ($70 — stops the VM, the normal control):**

- **Budget resource:** "Metatron Soft Cap (stops VM)" on the same billing account, `$70` monthly, calendar-period, scoped to project `211460608583`
- **Pub/Sub topic:** `budget-soft-cap`
- **Cloud Function:** `stop-vm` (Python 3.11, Gen2, `us-central1`) — source in [`infra/stop-vm/`](../infra/stop-vm/), deploy with `gcloud functions deploy stop-vm --gen2 --runtime=python311 --region=us-central1 --source=. --entry-point=stop_vm --trigger-topic=budget-soft-cap`
  - Action: if `costAmount > budgetAmount`, no override is active, and the instance is not already `TERMINATED`, stops `metatron-vm`
  - The `TERMINATED` check matters: budget alerts re-fire repeatedly while spend stays over, so without it every notification issues a redundant stop
  - Override check **fails open** — if the GCS check errors, the VM is stopped anyway. Stopping is cheap and reversible; failing to stop is the expensive mistake
- **Override:** `gs://metatron-billing-state/override-vm.json`, set via `scripts/metatron-vm-override.sh [hours]` (default 8). A **separate object** from the hard cap's `override.json`, so silencing the soft cap never silences the hard cap
- **Recovery when it fires:** `gcloud compute instances start metatron-vm --zone=us-central1-a --project=metatron-ai-499810`, or `./scripts/metatron-resume.sh`

Note on cost data: GCP spend figures lag by hours, so neither cap reacts at runaway speed. The fastest available signal is in-process API call and token accounting in the Orchestrator — not yet built, and the only layer that could catch a retry loop in seconds.

**Manual override:** `gs://metatron-billing-state/override.json` — if present with an unexpired `until` timestamp, `stop-billing` logs and skips disabling instead of acting. Set via `scripts/metatron-billing-override.sh [hours]`. Exists because after raising the budget in the Console, GCP's notification pipeline took 10+ minutes to stop sending stale notifications carrying the old (lower) budget, each of which would otherwise re-disable billing right after a manual relink. `scripts/metatron-resume.sh` sets a 4-hour override automatically, but only when it finds billing already disabled — never on a routine resume.

If billing gets disabled and `metatron-resume.sh` doesn't recover it, relink manually: `gcloud billing projects link metatron-ai-499810 --billing-account=013F3D-66B5CD-955A3A`, then check the GCP Console under Billing to confirm the budget amount is what you expect before doing anything else.

**Order matters — relink before overriding.** The override marker lives in a bucket *inside the project being disabled*, so writing it while billing is off fails with `403 ... billing account for the owning project is disabled`. Always `gcloud billing projects link ...` first, then run `metatron-billing-override.sh`. `metatron-resume.sh` had these reversed until 2026-07-30 and aborted under `set -e` before reaching the relink, so its automatic recovery path never completed once.

**Recovering from a hard-cap trip — what 2026-07-30 actually taught.** After a relink the VM refuses to start with `nic0 is frozen`. GCE freezes networking when billing is disabled and is *supposed* to thaw it asynchronously. **Do not assume it will.** In this project it never did — 25+ hours, no thaw, support escalation with a 3–5 business day estimate.

Ordered recovery, fastest first:

1. **Relink billing, then set the override** (in that order — see above).
2. **Retry `instances start` for ~30 minutes.** If it thaws, this is where it happens.
3. **Test whether the freeze is network-scoped:** `gcloud compute instances create <probe> --network=default ...`. If that fails with `networks/default ... is not ready`, the VPC is frozen and no amount of retrying the VM will help.
4. **Build a new VPC and rebuild the VM on it.** This is what worked:
   ```bash
   gcloud compute networks create metatron-net --subnet-mode=custom
   gcloud compute networks subnets create metatron-subnet --network=metatron-net \
     --region=us-central1 --range=10.10.0.0/24
   gcloud compute instances set-disk-auto-delete metatron-vm --disk=metatron-vm --no-auto-delete
   gcloud compute disks snapshot metatron-vm --snapshot-names=metatron-vm-boot-<date>
   gcloud compute instances delete metatron-vm --quiet          # disk survives
   gcloud compute instances create metatron-vm --network=metatron-net --subnet=metatron-subnet \
     --disk=name=metatron-vm,device-name=persistent-disk-0,boot=yes,auto-delete=no \
     --machine-type=e2-medium --tags=http-server \
     --service-account=211460608583-compute@developer.gserviceaccount.com --scopes=<original scopes>
   ```
   **Always `set-disk-auto-delete --no-auto-delete` and snapshot before deleting the instance.** The boot disk defaulted to `autoDelete: true`; deleting the instance would have destroyed the entire data tree, `metatron.db`, the FAISS index, `.env` and `vertex-key.json`.

**Why the rebuild is safe for clients:** all client access is over Tailscale, and Tailscale's node identity lives in `/var/lib/tailscale/tailscaled.state` on the boot disk. A rebuilt VM reclaims the same node and the same `100.64.226.49`, so the phone, browser, terminal and Android APK need no changes. Verify before deleting anything by mounting a snapshot copy on a temporary instance and confirming `tailscaled.state` is non-empty.

Separately, GCP re-sends budget notifications carrying the *old* budget for 10+ minutes after a raise — that is what the override covers, and it is a genuine waiting game.

---


---

## Vertex AI credentials

| Property | Value |
|---|---|
| GCP project | `metatron-ai-499810` |
| Location | `global` (required for Gemini 3.x models — `us-central1` does not work) |
| Service account | `metatron-vertex@metatron-ai-499810.iam.gserviceaccount.com` |
| IAM role | `roles/aiplatform.user` |
| Key file on VM | `~/multi-model-mcp/vertex-key.json` (gitignored) |
| `.env` var | `GOOGLE_APPLICATION_CREDENTIALS=/home/md-homefolder/multi-model-mcp/vertex-key.json` |
| Abuse-monitoring exception (ZDR) | **NOT in force** (verified against Google's published terms 2026-08-20). Obtainable on this self-serve account shape via Google's opt-out form; request not yet submitted. Default meanwhile: prompts logged only on classifier-flagged traffic, ≤90 days, never for training. Evidence, quotes, form link and re-check procedure: `archive/security/zdr_terms_evidence_2026-08-20.md`. **Update this row when the request is submitted and again when granted/refused — this row is the authority; if it says not in force, no other doc's claim counts.** |

---

## Environment variables (full listing)


The `.env` file lives at the project root on both the Mac (dev) and the VM. It is gitignored. Transfer to new machines manually via `gcloud compute scp` or similar.

```bash
# API keys — obtain from provider consoles
ANTHROPIC_API_KEY=...          # console.anthropic.com
OPENAI_API_KEY=...             # platform.openai.com/api-keys
GEMINI_API_KEY=...             # aistudio.google.com/apikey (for AI Studio fallback; not used on Vertex path)
HF_TOKEN=...                   # huggingface.co/settings/tokens (read-only token)

# Vertex AI (VM only — local dev uses ADC instead)
GOOGLE_APPLICATION_CREDENTIALS=/home/md-homefolder/multi-model-mcp/vertex-key.json
GOOGLE_CLOUD_PROJECT=metatron-ai-499810
GOOGLE_CLOUD_LOCATION=global

# Deployment mode
DEPLOYMENT_MODE=cloud          # loads routing_cloud.yaml (Vertex); omit or set to "local" for Ollama

# Web Push
VAPID_CLAIMS_SUB=mailto:diamond.mike.mt@gmail.com
```

On Mac for local dev, `OPENAI_API_KEY` is also exported from `~/.zprofile` as a fallback.

> **Account convention (2026-08-03):** all `mike` persona integrations — calendar, mail, push — use the purpose-built account **`diamond.mike.mt@gmail.com`**, not the owner's personal address. Recorded in `config/personas/mike/profile.yaml` as `account_email`. Historical archives predating this are left as written.

---
---

## Android app — build and sideload

The app is a Capacitor 8.4.0 wrapper around `static/index.html`. There is no separate backend bundled in the app — it calls the VM server over Tailscale.

| Property | Value |
|---|---|
| App ID | `com.mike.metatron` |
| App name | `Metatron` |
| Framework | Capacitor 8.4.0 (`@capacitor/android`) |
| Web asset dir | `static/` (the PWA lives here) |
| Server address | `https://metatron-vm.tail0acc5d.ts.net:8001` (Tailscale MagicDNS name, in `static/index.html` — used when the page is opened from `localhost`; otherwise same-origin) |
| Icon source | `assets/icon-only.png` (Phoenician mem glyph, parchment/brown) |
| Icon generation | `npx @capacitor/assets generate` — writes to all `mipmap-*` density folders |

Key config decisions:
- `allowMixedContent: true` and `cleartext: true` remain in `capacitor.config.json` from the earlier HTTP setup. They are no longer relied on — the server serves HTTPS with a publicly trusted Tailscale cert.
- Adaptive icon XMLs removed from `mipmap-anydpi-v26/` — Android uses the PNG directly (fixes home screen icon caching bug).
- Adaptive icon background color: `#0d0d0d` in `android/app/src/main/res/values/ic_launcher_background.xml`.

**Build prerequisites (Mac):**
- Java 21 via Homebrew (`brew install openjdk@21`) — Capacitor requires 21, not 17
- Android SDK (Android Studio or command-line tools)
- Node.js / npm

**Build steps:**
```bash
cd ~/Desktop/multi-model-mcp
npx cap sync android          # syncs web assets + plugins into the Android project
cd android
./gradlew assembleDebug       # outputs APK to app/build/outputs/apk/debug/app-debug.apk
cd ..
./scripts/check_apk_sync.sh   # DB-0809-18: fails loudly if the built APK's bundled
                               # index.html drifted from static/index.html — catches a
                               # skipped sync or a stale, un-rebuilt APK before it ships
```

**Sideload to phone:**
```bash
# Serve the APK from Mac (phone connects to Mac via Tailscale)
cd ~/Desktop/multi-model-mcp
python3 -m http.server 8888
# Then on the phone browser: http://<mac-tailscale-ip>:8888/android/app/build/outputs/apk/debug/app-debug.apk
```
Phone must have "Install from unknown sources" enabled for the browser.

**When to rebuild the APK:** any time `static/index.html` changes the `SERVER` constant, the login flow, or UI structure. Pure server-side changes (agent files, orchestrator logic) do not require a rebuild.

---

## Local dev mode (Mac / Ollama)

When running locally instead of on the VM:

| What | Where | How to find / set |
|---|---|---|
| `DEPLOYMENT_MODE` | `.env` | Remove the line (or set to `local`) — loads `routing.yaml` instead of `routing_cloud.yaml` |
| Ollama | `localhost:11434` | `brew install ollama && ollama pull qwen3:14b && ollama serve` |
| Local LLM model | `config/modules/routing.yaml` → `OLLAMA_MODEL` | `ollama list` to see installed models |
| Prevent Mac sleep | terminal | `sudo pmset -a sleep 0 disksleep 0` (reverse: `sudo pmset -a sleep 10 disksleep 10`) |
| Keep server alive | launchd | `launchctl load ~/Library/LaunchAgents/com.metatron.server.plist` — create plist first (see `archive/sessions/2026-06-20 — VM Provisioning, GitHub, Deploy Pipeline.md`) |
| Whisper model size | `core/voice_pipeline.py` → `WHISPER_MODEL_SIZE` | `"base.en"` (fast), `"small.en"` (accurate), `"medium.en"` (best) |
| TTS voice name | `core/voice_pipeline.py` → `speak()` default arg | `say -v '?'` in terminal; download Premium voices via System Settings → Accessibility → Spoken Content |
| TLS cert (if needed) | `certs/` (gitignored; backed up to `certs_backup/`) | `brew install mkcert && mkcert -install && cd certs && mkcert <local-ip> localhost 127.0.0.1` |

Note: the Mac is no longer the primary host. Local mode is for development and testing only. Tailscale + HTTP transport encryption means TLS certs are not needed for phone access in either mode.

### Running it on the Mac

Moved here from `SESSION.md` § Quick start on 2026-08-14 — the primer keeps the two commands
that get typed daily and points here for the rest, so the reference stops being re-read on
every session that never runs the server.

```bash
cd ~/Desktop/multi-model-mcp
source .venv/bin/activate

# PWA server (Vertex cloud routing — the default; no Ollama needed)
python core/server.py --persona mike --port 8001

# Port 8001 already held? Kill and restart:
lsof -ti :8001 | xargs kill -9 && python core/server.py --persona mike --port 8001

# One agent directly, outside the pipeline
python core/orchestrator.py --agent research_agent --provider gemini

# Scheduler daemon
python core/scheduler.py
```

`--persona` is required on both `core/server.py` and `core/scheduler.py` — identity
resolution is fail-closed and there is no shared fallback path. Which routing file loads:
§ Routing / deployment mode below. Switching to Ollama needs the sleep and launchd steps in
the table above **first**.

---

## Recreate from scratch (ordered checklist)

Follow this order. Each step depends on the ones before it.

**1. GCP project**
- Create project `metatron-ai-499810` (or new name — update `.env` and `routing_cloud.yaml`)
- Enable APIs: Vertex AI, Cloud Functions, Pub/Sub, Cloud Billing, Eventarc
- Link billing account

**2. Billing cap**
- Create Pub/Sub topic `billing-cap`
- Create budget alert at $20, configured to publish to `billing-cap` topic
- Deploy Cloud Function `stop-billing` (Python 3.11, Gen2, Pub/Sub trigger on `billing-cap`)

**3. Vertex AI service account**
- Create service account `metatron-vertex@<project>.iam.gserviceaccount.com`
- Grant `roles/aiplatform.user`
- Download JSON key → save as `vertex-key.json` (do not commit)

**4. GCP VM**
- Create `e2-medium` Debian 12 VM in `us-central1-a`, named `metatron-vm`
- Do not open any firewall ports (Tailscale is the only access path)
- SSH in: `gcloud compute ssh metatron-vm --zone=us-central1-a --project=<project> --tunnel-through-iap`
  — **`--tunnel-through-iap` is not optional.** There is no public ingress on port 22 since the
  2026-07-31 VPC rebuild, and it is also what makes SSH work from a network that blocks outbound
  22 (hotel, café, most public wifi): IAP carries it over 443. Omitting it gives a bare
  `Operation timed out`, which reads as a dead VM — it cost a session on 2026-08-18. `deploy.sh`
  has always passed it; these rebuild notes predated the rebuild and did not.
- Install system packages: `sudo apt install python3.11 python3.11-venv ffmpeg -y`

**5. Tailscale on VM**
- `curl -fsSL https://tailscale.com/install.sh | sh && sudo tailscale up`
- Sign in with the tailnet account — VM joins automatically
- Note the assigned Tailscale IP (update `static/index.html` `SERVER` constant and rebuild APK)

**6. GitHub repo**
- Create private repo `github.com/<account>/metatron`
- On Mac: add SSH key `~/.ssh/github_mikeapex` to GitHub account
- On VM: generate deploy key (`ssh-keygen -t ed25519 -f ~/.ssh/github_deploy`), add public key to repo as read-only deploy key
- VM: `git config --global pull.rebase false`

**7. Repo on VM**
- Option A (from GitHub after step 6): `git clone git@github.com:<account>/metatron.git ~/multi-model-mcp`
- Option B (initial transfer before GitHub exists): `git archive HEAD | gcloud compute scp - metatron-vm:~/repo.tar --zone=us-central1-a --tunnel-through-iap` then extract
- Create `.venv` and install: `python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- Copy `.env` to VM: `gcloud compute scp .env metatron-vm:~/multi-model-mcp/.env --zone=us-central1-a --tunnel-through-iap`
- Copy `vertex-key.json` to VM: same command pattern

**8. systemd services**
- Write both unit files (text above) to `/etc/systemd/system/`
- `sudo systemctl daemon-reload && sudo systemctl enable metatron-server metatron-scheduler && sudo systemctl start metatron-server metatron-scheduler`
- Verify: `curl https://metatron-vm.tail0acc5d.ts.net:8001/health` → `{"status":"ok"}`

**9. Deploy pipeline on Mac**
- Ensure `deploy.sh` is executable: `chmod +x deploy.sh`
- Set `git config pull.rebase false` on VM (step 6 above)
- Test: make a trivial commit, run `./deploy.sh`, confirm services restart

**10. Android app**
- Install Java 21: `brew install openjdk@21`
- Update `SERVER` in `static/index.html` to the VM Tailscale IP
- `npx cap sync android && cd android && ./gradlew assembleDebug`
- Sideload APK via `python3 -m http.server 8888` (see build steps above)

---


## Topology

```
Mac (dev)
  │  git push → github.com/MikeApex/metatron (private)
  │               └── VM pulls via deploy key (read-only SSH)
  └── ./deploy.sh ──► GCP VM (metatron-vm, us-central1-a)
                            │  metatron-server.service (port 8001)
                            │  metatron-scheduler.service
                            ├──► Vertex AI (Gemini 3.1 Pro / Flash-Lite)
                            │      GCP project: metatron-ai-499810
                            └──► Tailscale VPN (IP: 100.64.226.49)
                                      └── Android phone
                                          https://metatron-vm.tail0acc5d.ts.net:8001
```

The VM's external IP is never used for access. All clients arrive over the
Tailscale WireGuard tunnel. The server listens on **HTTPS** 8001 using the
Tailscale-issued cert for `metatron-vm.tail0acc5d.ts.net`, which is publicly
trusted — no CA install on any client. Tailscale would encrypt the transport
regardless; the cert exists so browsers and the Android WebView treat the origin
as secure.

SSH is IAP-only, no public ingress:

```bash
gcloud compute ssh metatron-vm --zone=us-central1-a \
  --project=metatron-ai-499810 --tunnel-through-iap
```

---

## Tailscale

A WireGuard mesh between Mac, VM and phone. It is the sole access path — no
public firewall ports are open on the VM.

| Device | Tailscale hostname / IP |
|---|---|
| Mac | `mikes-macbook-air` |
| VM | `100.64.226.49` |
| Phone | auto-assigned |

New device: install Tailscale, sign in with the same account, it joins
automatically. The VM was added with
`curl -fsSL https://tailscale.com/install.sh | sh && sudo tailscale up`.

> **Known issue — DNS after a resume.** A stop/start has at least once brought up
> Tailscale's DNS relay unhealthy, silently blocking **all** outbound DNS on the
> VM, not just tailnet, because Tailscale had taken over system resolution.
> Symptom: `NameResolutionError` on Google APIs while the metadata server is
> reachable. Check `sudo tailscale status`; fix with
> `sudo tailscale set --accept-dns=false`. Root cause unknown; restarting
> `tailscaled` alone did not fix it.

---

## Service management

```bash
sudo systemctl status metatron-server metatron-scheduler
sudo systemctl restart metatron-server metatron-scheduler
sudo journalctl -u metatron-server -f
sudo journalctl -u metatron-scheduler -f
```

Both units are enabled at boot, so nothing needs restarting after a VM resume.
Unit files verbatim: § systemd unit files above.

### Counting a runtime signature from the Mac (no SSH session)

A one-shot round trip, for checking whether a claimed runtime behaviour — *"fails on every
scheduler job"*, *"fires twice a day"* — is actually in the logs. This is the query
`/backlog verify` sends here, because workers cannot SSH and a runtime claim cannot be settled
by reading code:

```bash
gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 \
  --tunnel-through-iap --command="sudo journalctl -u metatron-server -u metatron-scheduler \
  --since '7 days ago' --no-pager | grep -c 'PATTERN'"
```

**Read the matches, not just the count.** Eleven `[vertex_cache]` warnings once looked like
confirmation of a filed 404 bug and were `NameResolutionError` from an unrelated outage — a
near-miss that would have closed the wrong item with a number attached to it.

---

## Pausing / resuming (cost control while not developing)

```bash
./scripts/metatron-pause.sh     # stops metatron-vm — halts compute + scheduler Vertex spend
./scripts/metatron-resume.sh    # starts it, waits for health check
```

The phone app is unreachable while paused; a stopped VM still incurs a small disk
fee but no compute or Vertex charges. If `metatron-resume.sh` finds billing
*disabled* it relinks and sets an override first; a routine resume skips that
path entirely.

---

## GitHub and the deploy pipeline

| Property | Value |
|---|---|
| GitHub account | `MikeApex` |
| Repo | `github.com/MikeApex/metatron` (private) |
| Mac SSH key | `~/.ssh/github_mikeapex` (push) |
| VM deploy key | `~/.ssh/github_deploy` (read-only pull) |
| VM git config | `pull.rebase false` |

`./deploy.sh` from the Mac: `git push origin main` → `gcloud compute ssh
metatron-vm` → `git pull origin main` → `pip install -q -r requirements.txt` →
`sudo systemctl restart metatron-server metatron-scheduler`.

`.git/hooks/post-commit` prints a reminder to deploy. It does **not** auto-deploy
— deployment is always manual.

---

## Python environment

```bash
cd ~/multi-model-mcp
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` is committed and regenerated from the venv when dependencies
change. **Kokoro TTS has its own isolated venv** at `tools/kokoro/venv/` because
its dependencies conflict with the main environment; `tools/kokoro/speak.py` uses
that interpreter path directly.

---

## Routing / deployment mode

`DEPLOYMENT_MODE` in `.env` decides which routing config loads. Evaluated at call
time in `core/router.py`, not at import, so `.env` load order does not matter.

| `DEPLOYMENT_MODE` | Routing file | Model path |
|---|---|---|
| `cloud` | `config/modules/routing_cloud.yaml` | all agents → Vertex Gemini 3.1 Pro / Flash-Lite |
| `local` or unset | `config/modules/routing.yaml` | sensitive agents → Ollama (qwen3:14b); open agents → cloud |

Current assignments live in those files. Updating model IDs:
[docs/CONVENTIONS.md](CONVENTIONS.md) § Model version maintenance.
