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
> token cache floor, one strict scheduler per user. You only learn you
> needed them afterwards. Everything here fails *loudly*: you notice the moment
> you need it, and you come and find it.

History and reasoning live in [archive/PROJECT_LOG.md](../archive/PROJECT_LOG.md).

---

## systemd unit files (verbatim)

All services run as user `md-homefolder`, load env from `.env`, and restart
automatically on crash. Day-to-day commands: § Service management below.

> **One server, and one scheduler per user (2026-10-28, second-user build).** The
> server serves every user; each request is bound to its user by its token. Each
> user's scheduler is its own `metatron-scheduler@<persona>` instance, started by
> `scripts/accounts.py approve` (§ Accounts below) — `mike`'s included. **Every unit
> is strict: no `METATRON_PERSONA_STRICT=0`, no fallback.** An unscoped persona lookup
> in the server raises; in a scheduler it resolves to that unit's own persona, never
> to another user. `.env` must never set `METATRON_PERSONA`, `METATRON_PERSONA_STRICT`,
> `METATRON_PERSONA_FALLBACK` or `METATRON_NO_LOCAL_MODELS` — `EnvironmentFile=`
> overrides `Environment=`, so a persona there would make every scheduler that user.
>
> *Until 2026-10-28 this section showed `STRICT=0` + `FALLBACK=mike` on both units; the
> live units had already dropped them (Mike, on the VM, 2026-10-27).*

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
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=/home/md-homefolder/multi-model-mcp/.env

[Install]
WantedBy=multi-user.target
```

Plus a drop-in, `/etc/systemd/system/metatron-server.service.d/host.conf`:
`[Service]` / `Environment=METATRON_HOST=vm` (2026-09-24 — the host marker the VM-only Build write
gate is to key on; confirm with `systemctl show metatron-server -p Environment`). A rebuild must
recreate it. The scheduler's copy is in its unit text below — the old scheduler drop-in
directory does not apply to `@` instances.

`--persona mike` on the server no longer means "serve unnamed requests as mike" — a request
that names no user is refused. It remains for CLI and dev use.

**`/etc/systemd/system/metatron-scheduler@.service`** — the source is
[infra/systemd/metatron-scheduler@.service](../infra/systemd/metatron-scheduler@.service) (its
comments carry the reasons); install with
`sudo cp infra/systemd/metatron-scheduler@.service /etc/systemd/system/ && sudo systemctl daemon-reload`.
```ini
[Unit]
Description=Metatron Scheduler Daemon (%i)
After=network.target metatron-server.service

[Service]
Type=simple
User=md-homefolder
WorkingDirectory=/home/md-homefolder/multi-model-mcp
ExecStart=/home/md-homefolder/multi-model-mcp/.venv/bin/python core/scheduler.py --persona %i
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1
Environment=METATRON_HOST=vm
Environment=METATRON_PERSONA=%i
Environment=METATRON_NO_LOCAL_MODELS=1
EnvironmentFile=/home/md-homefolder/multi-model-mcp/.env

[Install]
WantedBy=multi-user.target
```

- **`METATRON_NO_LOCAL_MODELS=1` is in the unit only, never `.env`** — `.env` reaches the server,
  which must load the models. With it, a scheduler never loads the embedder (~0.9 GB a user):
  its sessions and memory indexing run on the server (`/internal/session`, `/internal/index`,
  `/internal/search`), and a path that would load a model raises in the scheduler's log instead.
- **Two schedulers for one user would fire every job twice.** At start a scheduler takes
  `data/personas/<p>/logs/scheduler.lock` and scans `/proc` for any other scheduler for `<p>`
  that does not hold it (the retired single unit never took the lock). Either refusing exits 1
  with `REFUSING TO START` in the journal; `RestartSec=10` keeps systemd retrying under its start
  limit, so it comes up on its own once the other process is gone.

**Migration from the single unit (once, Stage 4 of the second-user build).** The order is the
protection — the retired unit's process has no lock:
1. Install the template (above); `sudo systemctl daemon-reload`. Then
   `sudo systemctl restart 'metatron-scheduler@*'; echo $?` must print `0` with no instance
   loaded — `deploy.sh` runs that line under `set -e`, so a non-zero here would abort the deploy
   after its `git pull` and before the server restart. If it is not `0`, stop and fix that first.
2. `./deploy.sh` (it restarts `'metatron-scheduler@*'` — nothing is loaded yet, so no instance).
   `deploy.sh` no longer restarts the old unit, so **it is still running the pre-lock code** — the
   exact process the `/proc` scan exists for. Until step 3 its coordinator sessions fail: it mints
   old-format tokens the restarted server refuses, logged as 401s in
   `data/personas/mike/logs/scheduler_errors.json` — expected, not a fault to chase. Minutes;
   keep steps 2–6 together.
2a. The `/proc` scan, for real: `sudo systemctl start metatron-scheduler@mike`, then
   `sudo journalctl -u metatron-scheduler@mike -n 5` shows `REFUSING TO START … a scheduler without
   the instance lock is already running (pid …)`; then `sudo systemctl stop metatron-scheduler@mike`
   to end its retry loop.
3. `sudo systemctl disable --now metatron-scheduler`
4. `mkdir -p ~/retired-units && sudo mv /etc/systemd/system/metatron-scheduler.service /etc/systemd/system/metatron-scheduler.service.d ~/retired-units/ && sudo systemctl daemon-reload`
   (the `.service.d` drop-in holding `METATRON_HOST=vm` goes with it — the template carries it now)
   — **retired, not masked**: `mask` refuses while a real unit file occupies the path, and
   retiring it makes anything still naming the old unit fail "not found" instead of starting a
   lock-less duplicate.
5. `ps -eo pid,args | grep '[s]cheduler.py'` — **no** scheduler for `mike`.
6. `sudo systemctl enable --now metatron-scheduler@mike`; `ps` again — **exactly one**;
   `systemctl show metatron-scheduler@mike -p Environment` lists `METATRON_HOST=vm`,
   `METATRON_PERSONA=mike` and `METATRON_NO_LOCAL_MODELS=1`.
7. Check: `cd ~/multi-model-mcp && .venv/bin/python core/scheduler.py --persona mike` exits 1 on
   the lock; `sudo systemctl restart metatron-scheduler` reports the unit not found.

### Scheduler job config — `day:` vs `days:` drive different layers

Found 2026-09-03, cost a session an hour to derive, and shipped a weekly clinical-review
job inert twice before it was caught. `config/templates/scheduler.yaml` jobs can carry
two different-looking keys and they are not redundant:

| Key | Read by | When | Expects |
|---|---|---|---|
| `day:` (singular) | `_register_schedules` in `core/scheduler.py` | Once, at daemon start — takes the weekly branch when `"time" in job and "day" in job`, and calls `schedule.every().<day>.at(t)` | A full lowercase day name (`sunday`), because it becomes a `schedule` library attribute (`schedule.every().sunday`) |
| `days:` (plural) | `_is_active_day`, via `_gates_block`, on **every** firing attempt | Compares against `datetime.now().strftime("%A").lower()` | A full lowercase day name, or one of `daily` / `weekdays` / `weekend` |

**A job needs both, and a plausible abbreviation is a silent, permanent no-op:**

- Only `days:` set → the job **registers daily** (no weekly branch taken) and the firing
  gate then narrows it to the named day(s) — fires weekly, but from a daily registration.
- Only `day:` set → the job **registers weekly** but the firing gate defaults `days` to
  `"daily"`, so the gate is open every day the job happens to be checked — in practice
  still weekly, because registration only ever invokes it on `day`.
- `days: sun` (or any abbreviation) → matches `strftime("%A").lower()` on **no day,
  ever**. This is exactly how `weekly_clinical_review` shipped inert twice: `day:
  sunday` was correct, `days: sun` was not, and nothing errored — the job registered,
  the gate silently declined to fire it, every week.

**Rule of thumb:** a weekly job in this file sets `day:` for registration; add `days:`
only if you also want the firing gate to double-check the day (redundant but harmless
when both are spelled out identically and in full). A job that should run daily needs
neither — `time:` alone registers `schedule.every().day.at(t)`, and the gate's `days`
default (`"daily"`) already passes every day.

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
memory or from another file.** They have been raised four times and lowered once.
**Within this section, the table below is the only copy of the numbers** — the
sub-headings under § Hard cap and § Soft cap deliberately no longer name an amount,
because they carried the $70/$150 values for three weeks after the table said
$150/$250.

| Tier | Amount | Fires | Action | Recovery |
|---|---|---|---|---|
| **Soft** | $100 | `budget-soft-cap` → `stop-vm` | stops `metatron-vm` | `gcloud compute instances start`, ~60s |
| **Hard** | $175 | `billing-cap` → `stop-billing` | disables project billing | **days** — runbook below |

> **✅ Reverted to $100/$175 on 2026-09-01 at the September reset, as planned — closes
> `[DB-0820-01]`.** Confirmed live by `gcloud billing budgets list` after the change.
> **The soft cap was lowered first**, so the intermediate state was $100/$250 rather than
> $150/$175 — see the gap rule below; it applies to the order of a *reduction* too, not
> just to choosing the numbers.
>
> The reconciliation the revert was conditional on came in and supported it: five
> consecutive post-deploy days at billed ÷ estimated 1.02×–1.17× (`[DB-0822-01]`,
> 2026-08-27), and a 2026-08-29 breakdown showing **real `mike`-persona use at
> ~$1.50–2.00/day** with the alarming 08-27/08-28 totals (~$9.5/~$8.7) driven by
> development test suites, not the product — one hour of A4 + red-team runs cost $6.47.
> **So the cap pressure is test runs, and $100/$175 has ample headroom for the product.**
> A heavy testing day can still trip the soft cap; that is the control working, and the
> recovery is a 60-second VM start.
>
> **The history below is kept because it is the reasoning, not the numbers.**
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

Budget history: $20 → $30 (2026-07-27) → $40 (2026-07-30) → restructured to $70 soft / $150 hard (2026-07-31) → $100/$175 (2026-08-09) → $150/$250 (2026-08-20, temporary) → back to $100/$175 (2026-09-01).

**Hard cap (disables billing, last resort) — amount in the table above:**

- **Budget resource:** "Metatron & Multi-Model Budget" on billing account `013F3D-66B5CD-955A3A`, monthly, calendar-period, notifying via Pub/Sub
- **Pub/Sub topic:** `billing-cap` in project `metatron-ai-499810`
- **Budget alert:** fires whenever cost exceeds the budget, publishes `{costAmount, budgetAmount}` to `billing-cap` topic — not just once on first crossing; GCP re-evaluates and re-notifies repeatedly while spend stays over budget
- **Cloud Function:** `stop-billing` (Python 3.11, Gen2, `us-central1`)
  - Trigger: Pub/Sub message on `billing-cap`
  - Action: if `costAmount > budgetAmount` **and no manual override is active**, calls `cloudbilling.disable_project_billing()` on the project
  - Retry policy: `RETRY_POLICY_DO_NOT_RETRY`
  - Source tracked at... *(not yet in the repo — currently only deployed; add under `infra/stop-billing/` if it needs another change. `infra/stop-vm/` shows the pattern.)*

**Soft cap (stops the VM, the normal control) — amount in the table above:**

- **Budget resource:** "Metatron Soft Cap (stops VM)" on the same billing account, monthly, calendar-period, scoped to project `211460608583`
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
| Implicit-cache retention (`cacheConfig`) | **`EPHEMERAL` — set 2026-10-23, durable default declined** (Mike's ruling 2026-09-25). From 2026-10-15 Google stores implicit-cache prefixes — conversation history and personal context included — at rest for ≤24h unless this is set; the project read `DURABLE` until the 23rd. Implicit caching stays **on** (`disableCache: false`), so the discount is kept. Explicit `cachedContents` is unaffected. **No meter reports this setting** (it costs nothing) — check by reading it: `curl -s -H "Authorization: Bearer $(gcloud auth application-default print-access-token)" https://aiplatform.googleapis.com/v1/projects/metatron-ai-499810/cacheConfig` should show `"retentionType": "EPHEMERAL"`. Unspecified counts as `DURABLE`. |
| Abuse-monitoring exception (ZDR) | **REFUSED by Google, 2026-08-26. Not in force, and not obtainable on this account as it stands. Do not write "verified ZDR" anywhere.** What governs instead: prompts logged **only on classifier-flagged traffic, ≤90 days, never used for training** — the 2026-08-21 finding, unchanged and still accurate. **Mike ruled the same day that the `mike` persona keeps running on Vertex under those terms, gating what he shares personally** (reasoning and its single-user expiry: `ROADMAP.md` § Section 0, *RESOLVED 2026-08-26*). Re-applying would need a changed account shape, not a re-submission. *Prior state, kept for the trail:* **Requested 2026-08-22, decision pending — NOT in force until granted.** Google's opt-out form submitted from `diamond.mike@gmail.com` for project number `211460608583`; declared as an individual developer (no entity), single internal user, sensitive domain = therapy/wellness/companionship. Google states review takes ~2 weeks, plus ~5–7 business days to allowlist if approved — so expect a decision by ~2026-09-05. Answers as submitted: `archive/security/zdr_optout_form_answers_2026-08-21.md`; eligibility evidence and terms quotes: `archive/security/zdr_terms_evidence_2026-08-20.md`. Default until then, unchanged: prompts logged only on classifier-flagged traffic, ≤90 days, never for training. **Re-check: the approval/rejection email to that account is the only evidence — `gcloud` reports no status. Update this row on the decision; this row is the authority, and until it says granted, no other doc's claim counts.** |

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

# Android push (FCM) — § Push notifications (FCM)
FCM_PROJECT_ID=<the push-only Firebase project's id>
# FCM_CREDENTIALS=/home/md-homefolder/multi-model-mcp/fcm-sender-key.json   # only once off Vertex
```

On Mac for local dev, `OPENAI_API_KEY` is also exported from `~/.zprofile` as a fallback.

**Never in `.env`:** `METATRON_PERSONA`, `METATRON_PERSONA_STRICT`, `METATRON_PERSONA_FALLBACK`,
`METATRON_NO_LOCAL_MODELS`. They are per-process and belong in a unit — `.env` reaches every
process, and `EnvironmentFile=` overrides the unit's own `Environment=` (§ systemd unit files).

> **Account convention (2026-08-03):** all `mike` persona integrations — calendar, mail, push — use the purpose-built account **`diamond.mike.mt@gmail.com`**, not the owner's personal address. Recorded in `config/personas/mike/profile.yaml` as `account_email`. Historical archives predating this are left as written.

---

## Push notifications (FCM)

The Android app is woken by Firebase Cloud Messaging (day planner Stage C, 2026-10-28). The VM
sends a **data-only ping carrying a random message id and nothing else**; the app fetches the
text from the VM over Tailscale with its sign-in (`core/push.py`, `GET /push/message/{id}`).
Sends and the phone's fetches are logged per persona, content-free, in
`data/personas/{p}/push_log.jsonl` — **the fetch is the delivery signal; no meter reports FCM.**

| Property | Value |
|---|---|
| Firebase project | **a separate, push-only project** (`FCM_PROJECT_ID`), free Spark plan, no billing, Analytics off. **Firebase is NOT added to `metatron-ai-499810`, deliberately** — adding Firebase to a project is irreversible short of deleting the project, which here means the VM (Mike, 2026-10-28) |
| Android app | `com.mike.metatron`, debug-cert SHA-1 `C3:EA:24:BD:61:72:FF:F5:F2:A3:92:CC:BC:A6:A9:3D:68:0B:43:45` (this Mac's `~/.android/debug.keystore`) |
| `google-services.json` | `android/app/`, gitignored by name; holds the app's API key, restricted to the package + SHA-1 above |
| Sender identity (now) | the VM's default credential — `metatron-vertex@…` — granted `roles/firebasecloudmessaging.admin` **in the push project** (cross-project grant; no second key) |
| Sender identity (off Vertex) | `FCM_CREDENTIALS=` a key for a service account inside the push project, FCM role only. Set it **before** retiring the Vertex account or its key — otherwise every send fails (`failed` in `push_log.jsonl`) |
| What reaches Google | the ping (an id), the push token / installation id, the SDK's version heartbeat. Delivery metrics and Analytics are pinned off in the manifest (`fac4c4c`) |
| Remove it | delete the push project; the app falls back to "open the app" with no channel; nothing in `metatron-ai-499810` changes |

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

**Sideload to phone. The APK is always served at `http://100.70.67.45:8888/app-debug.apk`**
(Mike's standing rule, 2026-09-03) — the Mac's Tailscale address, port 8888, that filename.
Copy the built APK to a staging directory and serve **only that directory**:

```bash
mkdir -p /tmp/metatron-apk
cp ~/Desktop/multi-model-mcp/android/app/build/outputs/apk/debug/app-debug.apk /tmp/metatron-apk/
cd /tmp/metatron-apk && python3 -m http.server 8888 --bind 100.70.67.45
# Then on the phone browser: http://100.70.67.45:8888/app-debug.apk
```

Phone must have "Install from unknown sources" enabled for the browser, and Tailscale up.
Installing over an existing build keeps the login — same app ID.

**Signing in (since the second-user build, 2026-10-28):** a typed username and password — no
persona dropdown. Mike signs in as `mike` (or any test persona) with the existing server
password; an account user signs in with their own, after creating the account from *Create an
account* and being approved (§ Accounts). Tokens changed format, so **every device signs in once
after the deploy that ships this**, and the APK built before it cannot sign in at all until the
rebuilt one is sideloaded — the web app works throughout.

> **Two deliberate departures from what this said before 2026-09-03, both of which shipped
> real exposure.** The old steps were `cd ~/Desktop/multi-model-mcp && python3 -m http.server
> 8888`, with no `--bind`.
>
> 1. **Serve the staging directory, never the repo root.** From the repo root that command
>    publishes `.env`, `vertex-key.json`, `data/personas/mike/**` and every archive to anyone
>    who can reach the port — Denied-tier files handed out by a Green-tier convenience step.
> 2. **`--bind` to the Tailscale address, never the default.** Without it the server listens on
>    every interface, so the whole local network is served, not the tailnet. The bind is what
>    makes "phone connects via Tailscale" true rather than merely intended.
>
> The IP is recorded here as an exception to *do not record values with a short half-life* —
> it is a **Tailscale** address, stable for the life of the tailnet node, not the VM's
> reassigning external IP. If it ever moves, `tailscale status` is the lookup.

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
- Write `metatron-server.service` and `metatron-scheduler@.service` (text above) to `/etc/systemd/system/`
- `sudo systemctl daemon-reload && sudo systemctl enable --now metatron-server metatron-scheduler@mike`
- Then one `sudo systemctl enable --now metatron-scheduler@<persona>` per active account (`scripts/accounts.py list`)
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
                            │  metatron-scheduler@<persona>.service (one per user)
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

## TLS certificate — renewal, and the outage it caused

The VM serves HTTPS on 8001 from `certs/server.crt` + `certs/server.key`, a Let's
Encrypt cert issued through `tailscale cert` for `metatron-vm.tail0acc5d.ts.net`.
**Certs are read at startup**, so a new file on disk changes nothing until
`metatron-server` restarts.

**Renewal is automatic since 2026-09-19.** `metatron-cert-renew.timer` runs daily at
04:30 (±30min jitter) → `scripts/renew_cert.sh`, which re-runs `tailscale cert`,
fixes ownership, and **restarts the server only if the cert file actually changed**.
On ~89 days in 90 it is a no-op that logs one line and touches nothing.

```bash
systemctl list-timers metatron-cert-renew.timer   # when it next runs
sudo systemctl start metatron-cert-renew.service  # force a check now
sudo journalctl -u metatron-cert-renew.service -n 20
```

> **⚠ The 2026-09-19 outage, because the symptoms point away from the cause.**
> The cert was minted by hand on 2026-06-21 with nothing scheduled to renew it. It
> expired at 12:23 UTC on 2026-09-19 and **every client stopped working at once —
> phone and desktop — while the server was entirely healthy**: 29 days uptime,
> `NRestarts=0`, and a full pipeline turn served twenty minutes earlier.
>
> **The three obvious checks all say "healthy", which is what makes this expensive
> to find.** `ping` succeeds, `tailscale status` is green, both services are
> `active`, and **`curl -k` returns a clean `401`** — because `-k` skips exactly the
> validation that has failed.
>
> **The one diagnostic that discriminates is `curl` WITHOUT `-k`:**
> ```bash
> curl -sv https://metatron-vm.tail0acc5d.ts.net:8001/health   # no -k
> echo | openssl s_client -connect metatron-vm.tail0acc5d.ts.net:8001 \
>   -servername metatron-vm.tail0acc5d.ts.net 2>/dev/null | openssl x509 -noout -dates
> ```
> A browser and the Android WebView both validate the cert, so "works from curl,
> dead from every client" is the signature of a cert problem and almost nothing else.
>
> **If you ever renew by hand, `chown` afterwards.** `tailscale cert` under `sudo`
> writes both files root-owned with the key at 600 — valid, and unreadable by the
> service user, so the server dies on its next restart holding a perfectly good
> cert. `scripts/renew_cert.sh` does this; a manual run must too.

---

## Service management

```bash
sudo systemctl status metatron-server 'metatron-scheduler@*'
sudo systemctl restart metatron-server 'metatron-scheduler@*'
sudo journalctl -u metatron-server -f
sudo journalctl -u metatron-scheduler@mike -f      # one user's scheduler
sudo journalctl -u 'metatron-scheduler@*' -f       # every user's
```

All units are enabled at boot, so nothing needs restarting after a VM resume.
Unit files verbatim: § systemd unit files above.

### Accounts — approving a user

Account changes run **on the VM, over SSH — never over HTTP** (no server route can approve,
disable or reset anyone). Mike says "approve <name>" in a Claude Code chat; the chat runs:

```bash
gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 \
  --tunnel-through-iap --command="cd ~/multi-model-mcp && .venv/bin/python scripts/accounts.py approve <name>"
```

| Command | Does |
|---|---|
| `list` | every account and its status, never a hash |
| `approve <u>` | pending only: creates the persona on the VM, writes `interview/state.json: not_started` (the first interview opens at her first sign-in; proactive sessions hold until it is finished or paused), copies the sign-up permission into `consents.json`, `enable --now metatron-scheduler@<u>`. Create-only and idempotent — re-run it to finish a step that failed |
| `reject <u>` / `disable <u>` | status changes and her tokens are revoked; `disable` also stops her scheduler. Nothing is deleted |
| `enable <u>` | re-admits a disabled user; touches nothing in her persona |
| `reset-password <u>` | prints a one-time temporary password for Mike to pass on |
| `seed-consent <u> --scopes … --evidence …` | records permissions given outside the app (used once, for `mike`, before the second-user deploy) |

A pending request shows on the session-start backlog line as `· N account(s) awaiting approval`.

### Counting a runtime signature from the Mac (no SSH session)

A one-shot round trip, for checking whether a claimed runtime behaviour — *"fails on every
scheduler job"*, *"fires twice a day"* — is actually in the logs. This is the query
`/backlog verify` sends here, because workers cannot SSH and a runtime claim cannot be settled
by reading code:

```bash
gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 \
  --tunnel-through-iap --command="sudo journalctl -u metatron-server -u 'metatron-scheduler@*' \
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
metatron-vm` → `git pull origin main` → CPU-only PyTorch from PyTorch's own index, in its own
step, then any `nvidia-*` packages uninstalled (the VM has no GPU; the CUDA build was 2.7 GB of
disk and ~169 MB resident) → `pip install -q -r requirements.txt` →
`sudo systemctl restart 'metatron-scheduler@*'` → drain, then restart `metatron-server`.

`.git/hooks/post-commit` prints a reminder to deploy. It does **not** auto-deploy
— deployment is always manual.

> **`./deploy.sh` never commits — it pushes what is already committed, and the VM pulls
> that.** So running it with work still in the working tree reports "deploy complete" and
> ships **nothing**. This has happened. The phrasing that prevents it is *"owes a commit,
> then a deploy"* — say that in any handoff or close-out, never "owes a deploy" alone.
> *(Carried in `SESSION.md`'s handoff paragraph in every session from 2026-08-29 until
> 2026-09-03, when the primer crossed its volatile-lines budget and this moved to the file
> that owns deploy detail. It is a permanent property of the script, not session state.)*

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
