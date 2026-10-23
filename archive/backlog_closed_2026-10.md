# Closed Backlog Archive — 2026-10

**Items closed in October 2026, with the evidence that closed them.** Rolls monthly;
the previous file is [`backlog_closed_2026-09.md`](backlog_closed_2026-09.md).

**Search this before re-filing anything.** A closed item is removed from
[`../DEV_BACKLOG.md`](../DEV_BACKLOG.md) entirely — this is where its proof lives.

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
