# Session Archive — GCP Billing Investigation, Cache Padding Fix, and Pause/Resume Tooling

## What happened

Started as a walkthrough of the GCP billing breakdown ($18 at 14 days into the month, project barely used) and ended up covering three separate pieces of work: a Vertex AI cache bug fix, VM pause/resume tooling, and a live incident in the project's own billing safety net.

## 1. Billing breakdown explained

Walked through what each line item (Vertex AI, Compute Engine, Cloud Run Functions, Networking) actually represents, and diagnosed why cost was accruing despite "no active use":

- **`metatron-scheduler.service`** fires proactive agent sessions roughly every 90 minutes regardless of user activity — the real source of the Vertex AI spend.
- **Vertex prompt caching was silently failing on every single call.** Logs showed `[vertex_cache] creation failed (400 INVALID_ARGUMENT: cached content is of 4051 tokens. Minimum is 4096.)` repeating for days — every scheduler tick was paying full uncached price.
- **Compute Engine** was billing simply because `metatron-vm` runs 24/7.

## 2. Vertex cache padding fix

Root cause: the June 24 token-reduction work (Steps 2–5, see that session archive) shrank Coordinator/Synthesizer system prompts enough that at least one context variant landed at 4051 tokens — 45 tokens under Vertex's 4096-token cache-creation floor. Below that floor Vertex rejects `CachedContent` creation outright (not a soft degradation), so every call ran uncached.

- Added `_pad_for_vertex_cache()` in `core/orchestrator.py` — estimates token count (~4 chars/token), pads with clearly-marked inert filler up to 4096+200 tokens margin when short. Only applied to the copy sent to `caches.create()`; uncached/compat paths keep the original prompt.
- Confirmed only one call site (`_get_or_create_vertex_cache`), used only by `coordinator` and `synthesizer` (`_HEAD_LAYER_AGENTS` / `_ROUTING_LAYER_AGENTS`) — fix covers every agent that touches the cached path.
- Checked for other caching mechanisms needing the same fix: found a dormant Anthropic `cache_control: ephemeral` path (`run_session_anthropic`, `_anthropic_stream`) — not live in production (`routing_cloud.yaml` routes everything to Gemini), and Anthropic's floor (1024t) fails silently rather than erroring, so it doesn't need the same urgency. Noted in `SESSION.md` as a monitoring item if Anthropic routing ever comes back.
- **Verified live in production:** triggered a real `coordinator` session on the VM with INFO logging — confirmed `POST .../cachedContents → 200 OK`, `[vertex_cache] created`, and the very next turn reading `cache_read=12281` tokens from cache.

## 3. VM pause/resume tooling

Added `scripts/metatron-pause.sh` and `scripts/metatron-resume.sh` (stop/start `metatron-vm` via `gcloud compute instances`) so the VM doesn't run 24/7 during dev downtime. Both systemd services auto-start on boot, no manual restart needed.

## 4. Billing safety-net incident (unplanned)

Attempting to test `metatron-pause.sh` revealed the project's $20 monthly budget cap had already tripped and fully unlinked the billing account (`billingEnabled: false`, `billingAccountName: ''`) — the `stop-billing` Cloud Function working as designed.

Investigation (via Cloud Logging, since most `gcloud` calls were blocked without billing) found:

- **Legitimate first trip:** 2026-07-15 ~01:56 UTC, cost crossed $20.10 — correct behavior.
- **User raised the budget to $30 in the Console** to unblock testing — correct budget resource confirmed via direct Billing Budget REST API call (`billingbudgets.googleapis.com`, enabled for this purpose).
- **But GCP's budget-notification pipeline took 10+ minutes to fully stop sending stale notifications** still carrying the old `budgetAmount: 20.0`. Each stale notification re-disabled billing immediately after every relink attempt — including during a live `gcloud functions deploy`, which failed outright because the deploy window (60–120s) was longer than the gap between re-disable events.
- **Fix — deployed a new `stop-billing` revision** (source pulled from GCS, patched, redeployed) that checks a manual-override marker (`gs://metatron-billing-state/override.json`, new bucket) before disabling. If an unexpired override is present, it logs and skips instead of disabling.
- **`metatron-resume.sh` updated**: checks billing status first; only alerts, sets a 4-hour override, and relinks if it finds billing actually disabled. A routine resume where billing was never touched skips that path entirely — confirmed this matches the user's stated model ("override only fires in the recovery case, not preemptively on every resume").
- **New script:** `scripts/metatron-billing-override.sh [hours]` — standalone, manual-only trigger for the marker.
- Confirmed the override is inert unless cost actually exceeds budget (checked first in the function's logic) — and if cost does genuinely exceed budget during an active override window, the auto-stop is fully suspended (GCP's own budget alert emails remain as an independent backstop, unaffected by the override).
- Mid-fix, also hit and fixed a separate issue: manually reattaching the Pub/Sub push subscription (needed to safely redeploy without fighting the retry loop) initially omitted the OIDC token audience, causing 401s on every delivery — fixed by matching the original `pushConfig` exactly.
- Also discovered and worked around: Tailscale's DNS relay (`100.100.100.100`) came up unhealthy after the VM's stop/start cycle, silently blocking all outbound DNS (not just tailnet traffic) since Tailscale had taken over system DNS resolution — blocked the live cache-fix test until `sudo tailscale set --accept-dns=false` was run. Root cause not identified; documented as a known issue in `CLAUDE.md`.

## Decisions made

- Budget cap raised from $20 → $30/month.
- Manual billing override is deliberately **not** automatic on every resume — only triggers when `metatron-resume.sh` detects billing is actually disabled, matching the user's "recovery-only" model.
- BigQuery billing export **not** set up — user is fine with the estimate-quality spend visibility currently available (last-known cost from `stop-billing` logs, refreshed multiple times daily) rather than real-time.

## Deferred / follow-up

- `stop-billing`'s source (`main.py`) is deployed but **not yet added to the repo** — currently lives only as a deployed Cloud Function revision plus a local scratch copy. Worth adding under something like `infra/stop-billing/` if it needs another change.
- Root cause of the Tailscale DNS relay going unhealthy after VM restart not identified — workaround documented, but may recur.
- `core/orchestrator.py`'s `ANTHROPIC_MODEL` version bump and the new "Mandatory Pre-Edit Context Check" section in `CLAUDE.md` were made by a parallel session during this one — left untouched/uncommitted by this session, not this session's work.

## Files changed (this session, committed)

- `core/orchestrator.py` — `_pad_for_vertex_cache()` (commit `20977ba`)
- `scripts/metatron-pause.sh`, `scripts/metatron-resume.sh` (new, commit `20977ba`; resume logic updated in `e9c06c2`)
- `scripts/metatron-billing-override.sh` (new, commit `e9c06c2`)
- `CLAUDE.md` — Pausing/Resuming section, Billing Protection section update, Tailscale DNS known-issue note (commits `20977ba`, `e9c06c2`)
- `SESSION.md` — session summary entry + cache-padding monitoring note (commit `37ce30e`)
- GCP-side (not in repo): `stop-billing` Cloud Function redeployed (revision `stop-billing-00002-mog`), new bucket `gs://metatron-billing-state`, budget raised to $30

## Deployed

`./deploy.sh` run — pushed and confirmed live on the VM. `origin/main` and the VM are both on `814e6c3` (includes this session's `e9c06c2` and `37ce30e`, plus a routing fix committed by the parallel session shortly before deploy). Health check `{"status":"ok"}`, both `metatron-server` and `metatron-scheduler` `active`. The cache-padding fix (`20977ba`) was already live from earlier manual testing this session.

## Note on parallel-session commit hygiene

`CLAUDE.md`, `SESSION.md`, `core/orchestrator.py`, and `archive/plans/phase5_to_future_roadmap_2026-06-10.md` all had uncommitted edits from a separate, still-open parallel session mixed into the working tree throughout this session (a model-ID bump, a new "Mandatory Pre-Edit Context Check" rule, and a reverted data-management-gaps implementation attempt). Left those untouched and uncommitted per instruction — did not bundle them into this session's commits. For `SESSION.md` specifically, reconstructed the target commit content from `git show HEAD:SESSION.md` plus only this session's two additions, committed that, then restored the full working-tree file (with the other session's edits intact) byte-for-byte. `core/orchestrator.py`, `CLAUDE.md`'s pre-edit-check section, and the roadmap file remain uncommitted, owned by that other session.
