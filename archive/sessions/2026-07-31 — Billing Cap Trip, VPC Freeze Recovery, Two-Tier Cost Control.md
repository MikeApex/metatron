# 2026-07-31 — Billing Cap Trip, VPC Freeze Recovery, Two-Tier Cost Control

Spans 2026-07-30 → 2026-07-31. Roughly 26 hours of production downtime, recovered by rebuilding the VM on a new VPC. Cost control restructured afterwards so the same failure cannot repeat.

---

## What happened

`stop-billing` disabled billing on `metatron-ai-499810` at ~$31 spend against a budget already raised to $40. It acted on a stale notification carrying the old $30 figure — the exact propagation-lag scenario the override mechanism was built for, but the override only helps *after* a relink, not before the trip.

Disabling billing froze the project's VPC. Billing was relinked within hours; Google's asynchronous network thaw never ran.

| Time | Event |
|---|---|
| 30 Jul ~11:00 UTC | Billing disabled by `stop-billing`; VM goes offline |
| 30 Jul 13:44 UTC | Billing relinked manually, `billingEnabled: true` |
| 30 Jul – 31 Jul | 100+ `instances start` attempts, all `nic0 is frozen` |
| 31 Jul 08:14 UTC | Billing toggle (support suggestion) — triggered a disk restore, did not fix the network |
| 31 Jul ~13:30 UTC | Support escalated to tech team, 3–5 business day estimate |
| 31 Jul ~14:00 UTC | New VPC created and proven working |
| 31 Jul ~14:45 UTC | VM rebuilt on `metatron-net`, healthy |

---

## Diagnosis

The decisive test was creating a throwaway instance rather than reasoning about the error:

- `instances start` → `UNSUPPORTED_OPERATION: The default network interface [nic0] is frozen`
- `instances create --network=default` → `The resource '.../networks/default' is not ready`

The second error proved the freeze was **network-scoped, not instance-scoped**, which ruled out rebuilding on `default` as a workaround. A later test proved it was scoped to `default` specifically — a new custom VPC accepted a running instance immediately.

Two diagnoses were tested and discarded along the way:

1. **Shared VPC host project blocked** (support's first theory) — disproved: network selfLink is in the same project, `get-host-project` returns `{}`, project is neither host nor service project.
2. **Billing toggle to force resync** (support's second theory) — tried with a 1.7-second disabled window. Triggered a boot-disk `RESTORING` cycle but left the VPC frozen.

---

## Recovery

1. `set-disk-auto-delete --no-auto-delete` — **the boot disk defaulted to `autoDelete: true`**; deleting the instance would have destroyed the data tree, `metatron.db`, the FAISS index, `.env` and `vertex-key.json`
2. Snapshot `metatron-vm-boot-2026-07-30-preunfreeze` (20 GB, READY)
3. Created `metatron-net` / `metatron-subnet` (`10.10.0.0/24`)
4. Verified Tailscale state on a **snapshot copy** mounted read-only on a temporary instance, reporting via serial console (no SSH, no firewall rules): `tailscaled.state` 2750 bytes, `profile-data/`, `certs/` all present
5. Deleted the instance, recreated on `metatron-net` with the same boot disk, machine type, service account + 7 scopes, and `http-server` tag
6. Tailscale reclaimed the node — same `100.64.226.49`, direct connection. No client changes needed.

---

## Cost control restructured

The hard cap was demoted from routine control to firebreak. The distinction is recovery cost, not dollars.

| Tier | Amount | Topic → Function | Action | Recovery |
|---|---|---|---|---|
| Soft | $70 | `budget-soft-cap` → `stop-vm` | Stops `metatron-vm` | ~60s |
| Hard | $150 | `billing-cap` → `stop-billing` | Disables billing | Days |

- **`infra/stop-vm/`** — new Cloud Function, source tracked in-repo. Deployed, `ACTIVE`, tested with an under-budget payload (logged `cost 10.0 within budget 70.0; no action`, VM untouched).
- Skips when already `TERMINATED` — budget alerts re-fire repeatedly while over budget.
- Override check **fails open**: if the GCS check errors, the VM stops anyway. Stopping is cheap; failing to stop is not.
- **`scripts/metatron-vm-override.sh`** — writes `override-vm.json`, a *separate object* from the billing override, so silencing the soft cap cannot silence the hard cap.

Chose an event-driven second budget over daily polling: GCP re-evaluates several times a day, needs no BigQuery export, and reuses proven plumbing.

---

## Bugs found and fixed

1. **`metatron-resume.sh` recovery path had never worked.** It wrote the override *before* relinking billing — but the override marker lives in a GCS bucket inside the disabled project, so the write always returned `403 ... billing account for the owning project is disabled`, and `set -e` aborted before the relink. Order reversed.
2. **`deploy.sh` would have broken silently after the rebuild.** `metatron-net` has no public SSH ingress. Added `--tunnel-through-iap` to `deploy.sh` and `metatron-resume.sh`; verified with a real deploy.
3. **Budget documented as $30 when it was $40.** Corrected, then superseded by the restructure.

---

## Also done

- Check-in cadence 90 → 180 minutes (`config/personas/mike/scheduler.yaml`, gitignored — copied to VM by hand, scheduler restarted)
- `CLAUDE.md`: two-tier billing section, the incident writeup, ordered recovery runbook with commands, new VPC/firewall rows, IAP requirement

Commit `571f9bc`, deployed.

---

## Deferred

1. **`default` network is still frozen.** Support case left open deliberately. Anything assuming `default` exists will fail in this project.
2. **`stop-billing` source still not in the repo** — only deployed. `infra/stop-vm/` shows the pattern. Its absence is how it drifted out of sync with the budget in the first place.
3. **No fast cost signal.** GCP spend data lags hours, so neither cap catches a runaway retry loop. In-process call/token accounting in the Orchestrator is the only layer that could react in seconds. Not built.
4. **APK sideload** — still outstanding from the previous session; installed build predates all client fixes.
5. **Tailscale client/daemon version skew on the Mac** (`1.96.4` vs `1.98.5`) — plausible source of the intermittent DNS failure seen during recovery.

---

## Notes for next time

- **Test scope before theorising.** One throwaway `e2-micro` settled in ninety seconds what an hour of reading error messages had not.
- **Check `autoDelete` before deleting any instance.** It defaulted to `true` here.
- **A snapshot inside the affected project is not independent protection** against project-level teardown, only against instance deletion.
- **`caffeinate -i` does not survive a closed lid** — the overnight watcher lost ~9 hours to Mac sleep.
