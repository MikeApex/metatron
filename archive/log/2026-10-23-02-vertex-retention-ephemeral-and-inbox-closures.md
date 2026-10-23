### 2026-10-23, second (Vertex stops storing conversations at rest, eight days late; four built Inbox entries closed) — this close-out — **nothing to deploy: a GCP-side setting and records only**

**Vertex implicit-cache retention is `EPHEMERAL` again `[DB-0925-01]`.** The item was overdue
(due 10-08) and `@waiting` on Google shipping `retentionConfig`. Probed today: the field is in
both `v1` and `v1beta1` discovery schemas (`RETENTION_TYPE_UNSPECIFIED` / `EPHEMERAL` / `DURABLE`,
unspecified "treated the same as `DURABLE`"), and **the project read `DURABLE`**. So from GA on
10-15 to today, conversation-history prefixes were most likely held at rest for up to 24h each, encrypted and not
used for training. That was the outcome Mike's 09-25 ruling declined. Applied the ruling as filed: PATCH on the global
host with `disableCache:false` + `EPHEMERAL`, operation `done: true`, **GET readback `EPHEMERAL`**.
Implicit caching stays on; explicit `cachedContents` unaffected. The two doc lines the item owed
are written: the Finding 4 row in `archive/security/zdr_terms_evidence_2026-08-20.md` now dates
the "in-memory only" quote as expired 10-15, and `docs/INFRASTRUCTURE.md` § Vertex AI credentials
carries the setting and its read-back command.

**Believed true and wasn't:** that the `⚠ due:` session-start line would get an overdue chore
done. It flagged this item every session from 10-08 and no session acted on it. A `@waiting` item
whose trigger has passed is not re-checked by anything; the line was the only signal and it was
read as background. Not filed: Mike did not ask for a mechanism.

**Inbox closures, with evidence in `archive/backlog_closed_2026-10.md` (new month file):**
offline retention (10-19), both batched-voice-note entries (10-15 17:25 and 20:10), all built in
`54222c0`; and the 10-22 three-part entry. That entry's dated timestamps (`54222c0`) and
transcription errors (`6408b97` + `1243cd4`) parts are built. Its hourly schedule-checking daemon
part is not, and **Mike ruled it removed: managed elsewhere.** Recommended and not taken: file the
daemon to `## Later`, with its standing run cost (24 checks/day) as the first question. Still in
the Inbox and untouched: the 10-15 long-form recorder upload (held: `/transcribe` is one job at a time).
Inbox 20 → 16, Later 31 → 30.

**Carried from the outgoing handoff, unchanged:** VM at `1243cd4`, everything committed deployed.
Open: a possibly phantom "Benny" contact from the 10-15 mishearing (Mike to check); per-user
Whisper vocabulary built but OFF. Build F1 run 1 stopped; next is `claude update` ≥ 2.1.271,
restart, bench test 2 — that window's Inquiry files are still uncommitted in the tree.

