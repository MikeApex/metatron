# 2026-08-06 — Billing Investigation and Region Latency Analysis

Investigation-only session. No code, config, or roadmap changes — analysis and recommendations
against live GCP state.

## What was asked

1. Why does Compute Engine show no billing from Aug 4 onward, while Vertex AI usage looks
   elevated on Aug 2 and Aug 4?
2. Is us-central1 the right region given the app is used from London — geographically and
   financially?
3. How much of that region latency is actually felt on a single turn — is it a flat ~100ms, or
   does it compound across the multi-agent pipeline?

## Findings

**Billing gap — verified against live `gcloud` state, not the console:**
- `metatron-vm` has been `status: RUNNING` continuously since 2026-08-03 23:47 PDT (the stop/
  start pair at 23:44–23:47 that day is the already-logged 4-hour outage recovery). No stop or
  start operations since. Neither the $70 soft cap nor the $150 hard cap has fired.
- No BigQuery billing export dataset exists (`bq ls` empty) — there is no per-SKU attribution
  available, only the console's report view.
- Conclusion: the Compute Engine gap is almost certainly GCE cost-report lag (GCE line items
  typically finalize 1–3 days behind usage; Vertex AI's metered billing posts same-day), not an
  actual absence of charges. The VM is confirmed running and should be billing normally.
- The Vertex spike on Aug 2 and Aug 4 lines up with real heavy-call activity already documented
  in `PROJECT_LOG.md` for those dates (SEQ 021 + Synth self-development on the 2nd; A4 gate
  rerun, B1a red-team's 75 live cases, and decisions A/B/C testing on the 4th) — plausible, but
  not provably benign without per-SKU data.
- Filed: **[DB-0806-03]** — turn on BigQuery billing export (not retroactive, but closes this
  gap for future anomalies).

**Region pricing — pulled live from the Cloud Billing Catalog API** (not estimated):

| | us-central1 | europe-west1 | europe-west2 (London) |
|---|---|---|---|
| E2 vCPU (on-demand) | $0.022902/hr | $0.025193/hr (**+10.0%**) | $0.028104/hr (**+22.7%**) |
| E2 RAM (on-demand) | $0.003070/GiB-hr | $0.003377/GiB-hr (**+10.0%**) | not pulled |
| Balanced PD, static IP | baseline | identical | identical |

Applied to the current e2-medium 24/7 setup (~$24.50 compute + $3.65 IP + $1 disk ≈ $29.15/mo):
europe-west1 comes to **~$31.75/mo (+$2.60)**. europe-west2 would cost roughly double that
premium for a much smaller further latency win over europe-west1 (Belgium↔London is already
short).

**Latency compounding — traced through the actual code, not assumed:**
- The transatlantic leg is paid **twice per voice turn**, not once: `POST /transcribe`
  (`static/index.html:1119`) is a full round trip for STT, and the WebSocket send
  (`static/index.html:973`) waits for time-to-first-token of the streamed response. On
  us-central1 that's ~260–300ms of pure geography tax per turn; on europe-west1, ~20–30ms.
- The internal Coordinator → specialist(s) → Synthesizer pipeline (`core/orchestrator.py`,
  specialists dispatched in parallel via a thread pool at `:2396`) does **not** multiply this —
  every one of those calls is VM → Vertex AI's `global` endpoint, which stays on Google's
  backbone regardless of which GCP region hosts the VM. Region choice affects only the two
  client-facing edges of a turn, not the number of internal LLM calls.
- Net: moving to europe-west1 saves an estimated ~200–280ms per turn, real but small next to
  the multi-second-to-tens-of-seconds pipeline compute time itself.

Filed: **[DB-0806-04]** — consider the us-central1 → europe-west1 migration, sized out but not
decided or scheduled.

## Decisions made

None — both topics were exploratory. No migration scheduled, no billing export enabled this
session.

## Deferred / not done

- BigQuery billing export not enabled.
- Region migration not scheduled — flagged as "worth doing, not urgent."

## Roadmap

Checked `ROADMAP.md` — neither topic is tracked there. Track D (Infrastructure, post-Alpha)
covers dedicated-hardware migration and encryption, not GCP region choice; region migration
isn't a roadmap-tracked item. No edit made.
