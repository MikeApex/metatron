### 2026-11-28 (the 11-26 walkthrough run, mostly by sending as Mike; the day is now ranked by the regret of delay; Metatron reporting actions it did not take filed as Now 4) — `6b96519`, `4fddfb8`, `4442922`, `c23ecf8` + this close-out — **VM at `4442922` (Mike deployed): `ranking_v2` is live**

**Incoming state:** the 11-26 deep sweep was archived (`4cabaef`), and its fixes were already deployed. Mike asked for the walkthrough prompt `[DB-1126-04]`. He then said to spin off agents for whatever needed no one, walk him through the rest, and "send messages as me for testing". The prompt was written to `archive/handoffs/2026-11-28-backlog-walkthrough-db-1126-04-prompt.md`, consumed here, and deleted.

**How it ran.** Four background workers ran, all read-only on the VM:
- **Sonnet, the walkthrough's app steps:** 86k tokens. It sent 11 messages as Mike over the WebSocket using the app's frame (`source: "ui"`, no `proactive`). `send_one()` marks a turn scheduled, so it was not used.
- **Opus, the textless-notification diagnosis:** 95k.
- **Sonnet, the ranking shadow read-out:** 57k.
- **Sonnet, the swim-nudge investigation:** 65k.

**Mike's VM edits (Denied tier, his):**
- Cardiac line removed; `[DB-1113-01]` closed.
- `check_inbox_6h` set to `enabled: false` rather than deleted. It was the only entry in `schedules.yaml`, it was his own 08-10 request, and the hourly `intake_sweep` covers it.
- The stale `logistics.json` `intention_goals` line fixed.
- The wrongly deferred task undone.
- The false contact note cleared.

**Built / decided:**
- **`ranking_v2` ON (Mike: "begin using the new order").** I recommended against it, because the plants are a `cliff` (×2) and lead every morning; Mike overrode.
- `behind_v2` stays off: it read "behind" on every day and never found a quick win that fit.
- Protected time passed (R4 is Mike's "breach only on a cliff deadline"), but it was not switched on.
- **Mike's back-burner ruling:** low-stakes items are never actively dropped; they sink below more important work. This conflicts with `back_burner` parking as designed.
- **Swim fix:** the series was moved to 16:45–18:00 when Logistics was asked outright, and the Friday focus block was cleared (both verified on CalDAV). The miss is specific to a correction stated as a fact: the Coordinator wrote only `write_wisdom`. Filed as `[DB-1128-01]`, Now 3, with a code-detection ask.
- **Textless notifications moved to Later (Mike).** The cause is confirmed: MagicDNS name, a ~6 s give-up, no retry, and only the last failure recorded. The phone settings did not cure it.
- Drop anyway passed.

**The class this run exposed: false receipts** `[DB-1128-02]`, Now 4:
- a defer hit the wrong task while the reply named the asked one;
- `write_contact` cannot clear a field (`tools/crm.py:1296`, `if value:`), and the reply said "cleared" twice;
- an update that succeeded on retry was reported as failed;
- a reschedule of an already-closed step claimed the morning was reworked;
- a quiet-hours reminder was held to 07:00 with no approval card while the reply said 6:45 (`[DB-1029-18]`, card half open).

Ambiguous names are still neither asked about on first mention nor stored (`[DB-0818-05]`).

**Believed wrong, corrected:**
- The swim worker said the series would be recreated; it was edited in place, same uid.
- The walkthrough worker read the `scheduled` tag as failing; the 11-27 20:00 row carries it.
- I briefed a defer test on a test task that had already been dismissed, so a real task was deferred. **Test against tasks confirmed open, never against ones from memory.**
- A plan step that "doesn't show" was in the plan's `dropped` list (a full day), not missing.

**Rejected:** deleting `check_inbox_6h` (it would leave an empty file, an untested state, and it was Mike's own request); plain text in the FCM payload (Section 0).

