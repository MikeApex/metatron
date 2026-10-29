### 2026-10-29 (`/backlog verify` on `## Now`: two items closed on live evidence, one rescoped, one answered) — `DEV_BACKLOG.md`, `archive/backlog_closed_2026-10.md` — **no code or config changed; nothing to deploy**

**Incoming handoff:** unchanged from 2026-10-28 (Stage 5 owed checks, Stage C held for one
deploy + APK, reply latency next). This session did not touch any of it.

**What ran.** `## Now` had four items. All were verified in this window rather than fanned out to
workers. Three of them close only on VM evidence (traces, quality events, the confirmation
ledger), which a worker can't reach. A worker's ~30k briefing floor would also have cost more
than the whole check. The VM was read through `/monitor/file` with `sync_dev_backlog`'s token
helper. No workers were spawned, so there is nothing for `worker_ledger.py`.

**Closed (Mike):**
- **A declined email was logged as sent `[DB-0829-01]`.** The case it was waiting for arrived on
  10-25: a thank-you email to Nopadon, gated and then declined at 12:03. The Diarist's directive
  carried the system PENDING block and it logged *"proposed … awaiting user approval"*. The day
  log has no "sent" entry. The reply half was not exercised, because that turn's reply was the
  stall fallback.
- **Stale day-counts `[DB-0822-06]`.** `derived_facts()` is live with correct arithmetic: on 09-08
  it corrected "33/35 days since" to 35/36. No reply ever read a count back, so the exact confirm
  never happened. Closed on the mechanism plus eight weeks with no report. Reopen on recurrence.

**Rescoped (Mike): the routing-miss log `[DB-0902-01]`.** Its close condition was never met in any
week. More importantly, the premise had moved on. **114 of 145** `ROUTING_MISS` events since 09-04
are the Coordinator flagging scheduler-opened sessions, the same fault as the ×10 machine-log
signature. Only ~15–25 are the success-descriptions the item was filed about. Rejected: widening
`asserts_routing_success()` for "correctly routed" / "handled appropriately". That covers ~15% of
the noise and would close an item about the wrong thing. The open question now is whether
scheduled prompts are mishandled or merely misfiled. Answer that from traces before choosing code
or `coordinator.md`.

**Answered, still open: a lecture stated as confirmed while the calendar was failing to load
`[DB-0910-02]`.** The fix is in code, not wording. The Synthesizer receives no signal that a read
failed: `core/actions.py` excludes reads by design, and nothing else reports a CalDAV 401 or mail
auth failure. The fix is a read-failure provenance line, built the same way as
`action_provenance_block`. Amber, no agent file.

**Noted, not filed:** the 10-25 12:03 reply stall is a data point for the 10-31 Vertex-stall
check. On 09-07 a model-written watering count was itself one day off (08-03 vs 08-04).

