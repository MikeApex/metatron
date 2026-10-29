# Closed Backlog Archive — 2026-10

**Items closed in October 2026, with the evidence that closed them.** Rolls monthly;
the previous file is [`backlog_closed_2026-09.md`](backlog_closed_2026-09.md).

**Search this before re-filing anything.** A closed item is removed from
[`../DEV_BACKLOG.md`](../DEV_BACKLOG.md) entirely — this is where its proof lives.

---

## ✅ [DB-0904-02] We were guessing what 3.8 Flash actually costs — the bill now says — closed 2026-10-24

**The evidence:** BigQuery billing export, 2026-09-04 → 10-24, every `Gemini 3.8 Flash` SKU. Gross
list rates per 1M: input **$1.50**, output **$7.50**, cache read **$0.15**, cache storage **$1.00**/hour.
Every SKU carries a `DISCOUNT` credit named **"Gemini 3.8 Flash Price Promotion - 50% off"**, so the
effective rates are **$0.75 / $3.75 / $0.075** — exactly what `spend_guard.yaml` enters. The guard is
right on the three per-token rates. Totals: $44.98 gross, $22.49 credited, **$22.49 net over 50
days (~$0.45/day)**.

**One figure is off, in the safe direction.** The promotion also halves **cache storage**, to a net
$0.50/hour. The guard has $1.00, so it over-reports storage 2x (~$1 over the period). Left as it is
on purpose: it is conservative now, and it is correct the day the promotion ends. The yaml comment
saying storage "does NOT double in 2027" is wrong about the net rate. The *list* rate stays flat,
but the net rate goes $0.50 → $1.00.

**What this did not settle: the promotion's end date.** The billing export does not carry one, and
`WebFetch` is still Denied. The `from: "2027-01-01"` block is still copied from 3.7.
`[DB-0901-02]` (`due: 2026-12-15`) owns that date. The bill will show the change as the credit
disappearing, and you can check it with the same query.

## ✅ [DB-0902-02] Two inbox jobs gave contradictory answers about the same inbox — one of them no longer exists — closed 2026-10-23

**The change:** there is one model inbox job, not two. Mike's housekeeping message of 2026-10-23
deleted `check_inbox_recurring` (the Coordinator/pipeline job, *"summarize any relevant logistics
details"*), which was the half of the 08-30 contradiction that reported "no new messages";
`check_inbox_6h` (Logistics, direct) stays. The built half of this item — the empty-queue answer
that states its reason instead of reading as "the inbox is empty" (`54073b6`, deployed and
VM-verified 2026-09-03) — is untouched and live.

**Why the deletion happened, which is the evidence it was the right one:** the 2026-10-23 audit of
live traces (09-20 → 10-23) found both jobs running every 6h over the same mail and **both minting
obligations, producing twin records** (tax e-file forms, 10-09 11:42 and 17:43). The pipeline job
was the costlier (~140k tokens a run, ~$2.8/month at `spend_guard.yaml` list rates). The task ledger
(`27c570f`) also refuses a second task from the same intake message by source id, so a twin cannot
recur even if a second job is ever added. Record: `archive/PROJECT_LOG.md` § 2026-10-23, third.

**The `@waiting` condition below can no longer be met as written** — it named the pipeline job,
which is gone. Confirmation that the deletion landed is item 1 of
`archive/handoffs/2026-10-24-task-ledger-post-deploy-prompt.md`. Whether `check_inbox_6h` is itself
now redundant with the intake sweep is that handoff's decision 6b, not a reason to keep this open.

### The item as filed

- **12. [DB-0902-02] The two inbox jobs disagree about the same inbox.** 08-30 14:45:03
  (pipeline, *"summarize any relevant logistics details"*) reported **"no new messages"**;
  14:45:29 (direct, *"any actionable items or urgent messages"*) found the Bupa dental
  reminder, the Jimmy Carr booking and the GCP budget alert in the same minute. One of the two
  paths is not reading what the other reads (intake queue vs raw inbox is the obvious suspect —
  intake went live 08-29 13:54). Same-minute contradiction, so timing does not explain it.
  Related but not identical: `[DB-0822-09]`'s failed surfacing half — fixing that without this
  would surface from a channel that sometimes sees nothing.
  @kind: bug
  **✅ BUILT, deployed and VM-verified 2026-09-03 (session ⑥, `54073b6`).** The suspect named
  above was right and the mechanism was not: the queue was **never filled, not drained**.
  `read_intake_queue` does advance a cursor on read, but the cursors file has **never had a
  `logistics` key**. The real cause is that **24 of 25 records in the live intake store carry
  `domain: null` and `category: "unclear"`** — the extractor was off behind `[DB-0820-03]`'s
  eval gate (that item closed 09-05 and the extractor is now parked permanently), the persona
  had zero `rules:`, and `unclear` maps to a null domain. So the queue
  returns zero for **every** domain, permanently, whatever is in the inbox. Nothing in the old
  return value said so, and `"(nothing new for this domain)"` reads as "the inbox is empty".
  The empty answer now states its reason (computed from config and the store) and explicitly
  forbids the sentence Mike heard. `tests/test_intake_queue_empty.py`, 10 checks.
  **Note the coupling: what fills the queue is classification, and that is now partly answered.**
  `[DB-0820-03]` closed 2026-09-05 (`archive/backlog_closed_2026-09.md`) — six taught `rules:`
  took the labelled corpus from 1/33 to 11/33 classified, and the two Prudential rules are the
  first records in the store to carry a non-null domain (`finance`). So the queue can now carry
  something; the remaining 22/33 stay `unclear` with a null domain until `[DB-0905-01]`'s
  research gate exists. This fix stops it lying about being empty; it does not fill it.
  **Diagnosis returned on `[DB-0822-09]`: the surfacing miss is NOT this split** — both 09-02
  runs called `read_email(count=15)`, the same source. See that item.
  @waiting: 2026-09-10 — close on one live pipeline inbox job that no longer reports "no new
  messages" while the inbox has unread mail
  *raised by Mike 2026-09-02 (Red session ④) from the drain read; traces 08-30 14:45 · built 2026-09-03 (session ⑥)*

---

## ✅ [DB-0925-01] Vertex was storing conversation history at rest — durable default declined, now in memory only — closed 2026-10-23

**The change:** implicit-cache prefixes (conversation history and personal context) are held in
volatile memory again, not on durable storage. Implicit caching stays on, so the discount is kept.

**Evidence.** On 2026-10-23 the field existed: the `v1` and `v1beta1` discovery schemas both list
`retentionConfig` with `RETENTION_TYPE_UNSPECIFIED` / `EPHEMERAL` / `DURABLE`, and unspecified is
documented as *"Treated the same as `DURABLE`"*. **The project read `DURABLE` before the change.**
So from GA on 10-15 to 10-23, eight days past the due date, prefixes were most likely stored at rest
for ≤24h each. That is the window Mike's 09-25 ruling meant to prevent. Nothing in it was lost;
it was retained by the vendor longer than intended, under the 24h / encrypted / no-training terms.
PATCH on the global host, `{"disableCache":false,"retentionConfig":{"retentionType":"EPHEMERAL"}}`,
returned operation `6890660811748933632`, `done: true`. **GET readback:
`{"retentionConfig": {"retentionType": "EPHEMERAL"}}`.**

**Doc lines owed by the item, both written:** `archive/security/zdr_terms_evidence_2026-08-20.md`
Finding 4 row (the "in-memory only" quote dated as expired 10-15, with the DURABLE window and the
fix); `docs/INFRASTRUCTURE.md` § Vertex AI credentials (new row: the setting, the date, the
read-back command, and that no meter reports it).

**Why it slipped:** the item was `@waiting` on the field shipping, and nothing re-checks a waiting
item once its trigger date passes. The `⚠ due:` session-start line flagged it every session from
10-08 onward, and no session acted on it.

### The item as filed

- **[DB-0925-01] From 15 October, every Vertex request's prompt prefix — conversation history and
  personal context — is stored at rest for up to 24h by default. Today it is in memory only.
  Decline it.** `due: 2026-10-08` · `@kind: chore`
  @waiting: Google shipping the `retentionConfig` field on the `CacheConfig` resource — absent when
  checked 2026-09-25, ships with GA on 10-15.
  **Google's notice, 2026-09-25:** Durable Caching goes GA on **2026-10-15** and is enabled by
  default for projects with implicit caching on, across Gemini 3.x Pro/Flash and every model
  launched after. Cached data encrypted, project-partitioned, retained **up to 24h**, never used
  for training. `metatron-ai-499810` named as in scope. Mike's decision the same day:
  **opt out to `EPHEMERAL`** — the opt-out preserves today's behaviour, so accepting is the change.
  **Run on the MacBook** (ADC already works; `/opt/homebrew/bin/gcloud`):
  `curl -s -X PATCH -H "Authorization: Bearer $(gcloud auth application-default print-access-token)"
  -H "Content-Type: application/json"
  "https://aiplatform.googleapis.com/v1/projects/metatron-ai-499810/cacheConfig"
  -d '{"name":"projects/metatron-ai-499810/cacheConfig","disableCache":false,"retentionConfig":{"retentionType":"EPHEMERAL"}}'`
  — keeps implicit caching **on**, volatile memory only. Then GET the same URL and confirm
  `retentionConfig.retentionType` reads `EPHEMERAL`: a config that silently did not take is the
  failure mode, and only a read sees it.
  **Two faults in the command as Google emailed it, both fatal as pasted.** The JSON payload sits
  inside double quotes with unescaped double quotes within it, so the shell collapses it; and the
  host is `${LOCATION_ID}-aiplatform.googleapis.com`, while we run `GOOGLE_CLOUD_LOCATION=global`
  and the global host is what answers.
  **2026-09-25 probe — it cannot be run yet, and that is why this is on a clock.** `retentionConfig`
  does not exist on the live API: the published discovery schema for **both** `v1` and `v1beta1`
  lists exactly `name` and `disableCache`, and the PATCH is rejected identically on the global host
  and on `us-central1` / `us-east4` / `europe-west4`. Two things the probe did settle: **the
  credential can write this resource** — a `disableCache: false` PATCH returned a completed
  operation — and **state is unchanged**, still `{"name": "projects/211460608583/cacheConfig"}`, no
  `disableCache`, no retention type pinned, i.e. in scope for the default flip.
  **If the field still is not there by 2026-10-14, that is a decision for Mike, not an automatic
  fallback.** `disableCache: true` works today and closes the window outright, but it kills the
  implicit-cache discount (~$1–2/mo at current volume) and is broader than what he approved. The
  window it buys is ≤24h of prefixes at rest with a vendor already holding his mail and calendar,
  which is why pre-emptively paying for it was not recommended.
  **Closing this owes two doc lines, and the first is the reason the item matters beyond a dollar.**
  `archive/security/zdr_terms_evidence_2026-08-20.md` Finding 4 carries a row quoting Google that
  this cache is *"in-memory only … does not violate zero data retention"* — **that row goes false
  on 10-15 unless the opt-out lands**, and it is evidence the § Section 0 basis rests on. Also
  `docs/INFRASTRUCTURE.md` § Vertex AI credentials: record the date, the retention type and the
  default declined, so no session re-derives this from a vendor email.
  **Not a deploy.** GCP-side project config; nothing in the repo changes and `./deploy.sh` is not
  involved. Explicit caching (`cachedContents`, what `_get_or_create_vertex_cache` manages) is
  unaffected either way — it stores system prompt and tool schemas, never user content, which is
  exactly the distinction 10-15 removes.
---

## ✅ Inbox — the app keeps what you send, and voice notes wait for Send — closed 2026-10-23

Four Inbox entries Mike raised through Metatron, built in `54222c0` (deployed, VM at `1243cd4`,
APK sideloaded, 4/4 phone checks passed — `archive/log/2026-10-23-01-client-outbox-voice-tray-and-misheard-names.md`):

1. *Offline message draft persistence* (`2026-10-19T10:18:27.469395Z`) — the outbox: a message is
   kept in localStorage from Send until its reply arrives and is resent on reconnect, and the
   server's `/ws` is now idempotent on `exchange_id`. `static/index.html` outbox queue (~line 1965).
2. *Batch audio reflection intake* (`2026-10-15T20:10:00.578167Z`) and
3. *Capture intermittent audio, submit as a batch* (`2026-10-15T17:25:13.786914Z`) — the voice
   tray: the on-screen mic holds snippets until Send, and each snippet becomes its own paragraph
   stamped with when it was *recorded*. `#voice-tray`, `static/index.html` § Voice tray. The
   *"grouped by subject if captured in rapid succession"* clause was not built as grouping; each
   snippet stays a distinct paragraph, which Mike's ruling on stamps made the design.
4. *The 10-22 three-part entry* (`2026-10-22T09:09:02.693907Z`) — dated timestamps built in
   `54222c0`, transcription errors handled by the `[Name note]`s (`6408b97` + `1243cd4`). Its
   third part, an *hourly schedule-checking daemon*, is not built; Mike, 2026-10-23: remove the
   entry, it is managed elsewhere.

**Not closed with them:** the 10-15 *long-form recorder file upload* (held — `/transcribe` runs
one job at a time; needs chunked background transcription).

---

## ✅ Check 2026-10-25: the nightly task sweep records yesterday's habits — closed 2026-10-26

Passed, read on the VM 2026-10-26 (`data/personas/mike/task_history.jsonl`, 11 rows):

- **10-24's daily habit:** `ob_261024_df33e1@2026-10-24` (Stretching) — `done`, 2 of 2, `partial: false`.
- **The gym week:** `ob_261024_6694f8@2026-W43` (10-19 → 10-25) — `missed`, 0 of 3, `partial: true`,
  so the week the ledger started part-way through is marked partial, as designed. The weekly grocery
  habit's W43 row reads the same way.
- **Repeat runs append nothing:** the 10-25 and 10-26 sweeps have both run since, and every row's
  `key` is unique — no second row for any 10-24 occurrence.

Origin: the task-ledger post-deploy session, 2026-10-24 (the launch prompt Mike ran asked for each
time-gated check to leave with a date).

## ✅ Check 2026-10-27: the plants come back due exactly 3 days after the last watering — closed 2026-10-27

Passed, read on the VM 2026-10-27 from the day plan's own files (`data/personas/mike/day_plan/`):
watered 10-24 (rain, Mike's word) → the interval task `ob_261024_177765` is on **10-27's** plan
(`ob_261024_177765@2026-10-27`, 09:20) and on **neither** `plan_2026-10-25.json` nor
`plan_2026-10-26.json`. The plan's candidates are the Today list's (`_on_todays_list`, round 2), so
the Today list agrees.

The item as filed: *"Watered (by rain, Mike's word) 10-24 → due 10-27; it must not appear on ✓ Today
on 10-25 or 10-26."* Origin: the task-ledger post-deploy session, 2026-10-24.


## ✅ [DB-0829-01] The log recorded an email as sent while it was still waiting for approval — closed 2026-10-29

Passed on a real gated-then-declined send, read on the VM 2026-10-29. On 2026-10-25, 11:05/12:02,
Mike asked for a thank-you email to Nopadon Wongpakdee. `send_email` returned
`PENDING_CONFIRMATION`, and Mike declined it at 12:03 (`declined_confirmations.json`). The
fire-and-forget Diarist's directive (trace `2026-10-25T12:03:22`) carried the system-generated
*"has NOT happened … record it as proposed and awaiting the user's approval"* block. It logged
*"noted proposed email to Nopadon Wongpakdee awaiting user approval"*. `logs/2026-10-25.json`
contains no record of an email being sent.

**Not exercised:** the user-facing half ("the reply carries only the waiting line"). The reply to
that turn was the stall fallback (*"couldn't finish the reply"*), so the reply made no false
claim but never showed the waiting line either. That half is covered by
`tests/test_pending_action_record.py`. Built `54073b6` (2026-09-03). Filed 2026-08-29 at Mike's
instruction. Closed by Mike, 2026-10-29 (`/backlog verify`).

## ✅ [DB-0822-06] It told Mike stale day-counts ("day three of your hiatus") — closed 2026-10-29

Closed on evidence that the fix runs, without the exact confirm it was waiting for. `derived_facts()`
(`core/orchestrator.py:990`, built `54073b6`) is live and its arithmetic is correct. On
2026-09-08 the block reached real prompts (traces 07:30 and 09:52). It corrected *"33 days
since…"* (written 09-06) to 35, and *"35 days since…"* (written 09-07) to 36. **No reply ever
read a count back**, so the `@waiting: 2026-09-10` condition (a live run reading a dated count
back correctly) never occurred. Nobody has reported the symptom since 2026-09-02. Closed by Mike,
2026-10-29 (`/backlog verify`). **Reopen if a reply states a stale count again.** The
age-annotation and intraday halves (`cbd5ca3`, `4cc9e3e`) shipped earlier and are unchanged.

## ✅ Plant watering stuck on August 4 and blind to rain (two Inbox entries, 2026-09-08) — closed 2026-10-29

Superseded by the task ledger, checked on the VM 2026-10-29 (`/backlog attack`). The fixed
`plant_watering_check` job no longer exists: the VM's live schedule list holds only
`check_inbox_6h`. It was replaced by a ledger interval task, *"Water indoor and garden plants"*
(`ob_261024_177765`, `interval_days: 3`, `data/personas/mike/tasks.yaml`), which counts from
`last_done`. That is the stuck-date fault removed by design (`tools/obligations.py:74`,
`27c570f`). The rain half works through Mike's own word: a completion on 2026-10-24 carries
the evidence *"It's raining today, so consider the plants watered."* **Not built: an automatic
rain check.** `tools/ambient.py` `get_weather` returns `days_since_rain`, but no task or job
reads it. If Mike wants rain to count without telling the tool, that is a new feature request,
not this item. Closed by Mike, 2026-10-29 ("remove any items… completed or rendered irrelevant").

## ✅ Make the day boundary user-adjustable (Inbox, 2026-10-24) — closed 2026-10-29

Built and switched on. Nothing is left to build. The single home is `_ledger_day()` at
`tools/obligations.py:246`, with `_day_starts()` at `:223-237` defaulting to 00:00. It is set
by `update_task(task_id="settings", action="day_starts")` (`:1665`, validated 00:00–06:00 at
`:1403-1420`). That action is gated on `ledger_fields`, which is `true` in
`config/modules/day_plan.yaml:28` since `d38efc7` (2026-10-27). The code default in
`tools/day_plan_config.py:33` stays `False` deliberately, as the fail-safe if the file is missing.
**The first live use is the confirmation:** Mike says when his day starts, `tasks.yaml`
`settings.day_starts` holds it, and a habit ticked at 01:30 counts for the day before. Closed
by Mike, 2026-10-29 (`/backlog attack`).
