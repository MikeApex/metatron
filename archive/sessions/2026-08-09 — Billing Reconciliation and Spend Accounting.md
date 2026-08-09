# Session — Billing Reconciliation and Spend Accounting
**2026-08-09**

## What happened

Started as "poll Google billing, break down cost since Aug 1." Became a full audit of the
spend-accounting layer after the first-pass number ($14) didn't match GCP's console ($35), then
a fix-and-deploy session once the causes were found.

## Investigation

1. **First pass (VM only):** reconstructed ~$14 from `data/diagnostics/spend_*.json` on the VM
   plus a deterministic infra estimate. Google showed $35.
2. **Found the second billing project** (`gen-lang-client-0902235819`, the `ask_gemini` MCP
   target) sharing the same billing account — checked, negligible (188 requests).
3. **Pulled ground truth from Cloud Monitoring** (`aiplatform.googleapis.com/publisher/...`
   metrics) instead of trusting either recorded figure: 20.88M input / 1.10M output actual vs
   11.19M / 178k recorded on the VM. A 6.2x output gap was the biggest flag.
4. **Root-caused three separate defects** (see log entry for full detail): thinking tokens
   excluded from every recording site; `run_session()` (the scheduler's entry point) never
   traced or gated; a second, independent spend-guard ledger on the Mac that the VM
   investigation never saw.
5. **Corrected my own numbers live** when the Mac ledger surfaced — the gap was 2.1x, not 4.7x.
   Mike then asked for a persona breakdown, which showed `sarah_chen` (test suites) at $8.44 —
   nearly matching `mike`'s (production) $8.63.
6. **Verified `push_agent()`'s actual behavior** before claiming calls were "dropped" — they
   weren't dropped from the ledger, only from the Book's trace view. Corrected the plan
   accordingly rather than building an unneeded fix.

## Decisions

- **No Pro→Flash routing changes.** Measured per-agent cost first; Synthesizer is $5.44 of $8.35
  VM spend and correctly pinned to Pro. The real cost levers are prompt size and turn count,
  already scoped as D2 / `[DB-0808-09]`.
- **MW/PH stay on Pro when deep is called for — Mike's explicit call**, keeping the `quick`
  tier reachable for those agents rather than forcing a `never_quick` list. Filed the resulting
  test gap (`[DB-0808-17]`) instead of changing routing.
- **No shared spend-guard state across hosts.** Considered, rejected: no shared filesystem
  between Mac and VM, and a network call inside a fail-open runaway guard was judged the wrong
  trade. Made the split visible (`host` field, named in every alert) instead of solved.
- **Testing must be cost-projected before it runs**, with a $1 approval threshold — new
  standing convention, not a one-off.
- **Soft/hard billing caps raised $70/$150 → $100/$150→$175**, live in GCP, because real spend
  was tracking to trip the old soft cap within the week.

## Built and deployed — `c41baa0`

- `core/orchestrator.py` — thinking-token capture at 5 recording sites; `run_session()` traces
  and gates itself when no caller already did.
- `core/trace.py` — `push_agent()` no longer drops a rootless depth>0 record (recovers Diarist
  into the Book).
- `core/spend_guard.py` — state is host-tagged.
- `config/modules/spend_guard.yaml` — thresholds re-baselined 5/10 → 6/15.
- `docs/CONVENTIONS.md` — new Testing Cost Convention.
- `CLAUDE.md` — Billing Protection table updated to $100/$175.
- `DEV_BACKLOG.md` — `[DB-0808-17]` filed.
- GCP — `billing_export` BigQuery dataset created (Console step to enable the export itself
  still needed); soft/hard budgets updated via `gcloud billing budgets update`.

Deploy verified: VM HEAD matches by ancestry, both services `active`, `/health` responding.

## Verified, not just asserted

- `py_compile` + import/symbol check on all four edited modules.
- Live probe of both Gemini usage-object shapes (OpenAI-compat and native) — confirmed Vertex
  puts reasoning/thinking tokens *outside* the field the code was already reading, on both
  paths. This overturned my initial assumption (that OpenAI-compat nested them inside
  `completion_tokens`) before any code was written against it.
- Live `run_session` call (Flash-Lite) — confirmed a new trace file is written and the gate
  runs, where previously neither happened.
- Live `run_session` call (Pro) — confirmed the specific undercount: 55 tokens recorded, 651
  billed, before the fix; corrected after.

## Deferred / filed

- `[DB-0808-17]` — A4 clinical hard-fails never run on Flash-Lite, the model actually serving
  most MW/PH quick-complexity turns. Also touches A7 check 8's wording (see `ROADMAP.md`).
- BigQuery billing export dataset exists but the export itself needs enabling in the GCP
  Console — no CLI/API path for that step.
- Per-call bounding of the spend gate (currently per-session-start only) — noted as a real gap,
  not proposed as a fix this session; would need a different mechanism.

## Not yet done

Re-query Cloud Monitoring in ~24h to confirm recorded output tokens now track actual billed
tokens rather than sitting far under them, as a live check that the fix holds outside the
verification probes run this session.
