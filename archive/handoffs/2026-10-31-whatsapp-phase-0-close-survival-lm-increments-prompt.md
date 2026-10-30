Model: Opus 5.5 — a short close-out with Mike, and possibly the clean-room build half of the increments work. It must NOT read any crypt implementation: if it does, it can no longer write clean-room code (W9).

# WhatsApp input — close Phase 0: survival read, two rulings, then Phase 1

Phase 0b and the Phase 0 probes ran on 2026-10-30 (log § 2026-10-30, WhatsApp). The reader
decrypts Mike's real backup on his phone; live notifications identify every chat; the dedup key
matched 5 of 5. **Three things are still open and come first — in this order.**

## ⛔ Clean-room rules — unchanged, still binding

1. Do not read, install, download or search for `wa-crypt-tools` or any other crypt12/14/15
   implementation. Web access stays denied; do not ask Mike to lift it.
2. **Do not open anything in `archive/transcripts/` dated 2026-10-26.** One of those files is the
   clean session 2's own transcript (`2026-10-26 — pasted_content id=7fdd Model Opus 5.5 — a build
   session.md`) — you do not need it either. The log fragment says everything it holds.
3. Your sources for format facts are only `archive/plans/whatsapp_backup_format_2026-10-26.md`,
   `tests/fixtures/whatsapp_backup/`, and the plan.

## Do these first — the open items

**1. The 24-hour survival read (Mike, any time after 13:22 on 10-31; ~2 min).**
- Phone: open **WA probe** → **Refresh**. The listener was last (re)connected at 10-30 13:22, when
  the second probe build was installed.
- Send the report to the Mac the way that worked on 10-30: long-press → Select all → Share →
  **Tailscale** → the Mac (lands in `~/Downloads`). Read it from there.
- **Pass:** `listener disconnected at: never` (or a disconnect followed by a reconnect), events in
  hours through the night when messages arrived, and `last event` recent. Battery optimisation was
  left at its default (`ON`) deliberately — that is what is being measured.
- **Fail (no events overnight despite messages):** report it; W5's real-time notification (P6)
  depends on this. The usual fix is battery optimisation off for the app — Mike's choice, recorded.

**2. Two rulings Mike owes — put both, with the recommendation, then record his answers.**

- **LM — the tabled local model (plan § 4, checkpoint LM).** Device facts (10-30): Unihertz Jelly
  Star, MediaTek Helio G99 (MT6789), Android 13 (API 33), 8.2 GB RAM, 170 GB free, **AICore not
  installed** — so Gemini Nano is unavailable; only a very small bundled model (~1B) would run, and
  slowly. Put the settled ruling in front of him: correspondence is read **as code, never a model
  judgement** (`SESSION.md` § Do not re-open, `[DB-0905-01]`). **Recommendation: no local model now
  — V2/V3 stay code on the VM; revisit only if M2 (labelling) shows code extraction falls short,
  then choose VM or phone on that evidence.** Record his answer and his reason in the plan (§ 4 LM)
  and the log.
- **Increments — nightly backups are incremental (found 10-30).** At 02:00 each night WhatsApp
  writes only a small `msgstore-increment-N-YYYY-MM-DD.1.db.crypt15` (0.0–0.1 MB); the full
  `msgstore.db.crypt15` was rewritten only on 10-22, on 10-26 (end-to-end backup turned on) and by
  Mike's manual backup on 10-30. The format description does not cover increment files, so the
  reader ignores them — **as built, P3 would see new messages only after a full backup, ~weekly.**
  - (a) **A Phase 0a′ session** (one that MAY read the reference, like session 1) adds the
    increment format and increment test files to the description; then a clean session extends the
    reader. ~0.5M tokens for 0a′ + ~0.5–1M for the build.
  - (b) Full backups only, accepting ~a week's lag on everything the listener misses (muted chats,
    group senders, edits).
  - **Recommendation (a)** — the nightly path exists to cover exactly what the listener misses.
  - On (a): **write the 0a′ prompt for a separate session — do not do 0a′ here.** It must name the
    question precisely: the increment files' layout and naming, how an increment relates to the
    full backup it follows (what it contains, how they combine), how to pick the set to read, and
    one test vector per handled variant. The build half then runs in a clean session (this one may
    do it later only if it never reads the reference).

**3. The controlled edit test (Mike, when convenient; optional).** Before: note `distinct
messages` and `same message re-posted…`. Have someone send a short message, then **edit it to add a
sentence**. After: distinct +1 and re-posted +1 → WhatsApp updates in place; distinct +1, re-posted
+0 → edits are not re-notified; distinct +2 → the edit arrives as its own notification. Then a
manual WhatsApp backup → wait 10 min → **4. Run backup probe**; the dedup lines show whether the
edit's live time and length match the backup.

## What Phase 0 established (for the plan's next revision)

- **Exit criteria:** decrypt on the phone ✅ (0.9 s, 16.4 → 36.4 MB, 2.2×; counts reproduce the
  Mac's plus growth); chat ID live, equal to the share-list key ✅ (4 of 4 resolve; one-to-one
  chats arrive by **hidden ID `@lid`**, all 3 mapped through `jid_map`); dedup key ✅ (5 of 5 exact
  time); group sender live ✗ (no person key, one sample — the backup supplies it, as P2 allows);
  survival — item 1 above.
- **Plan changes owed (Phase 2):** the listener ignores group-summary notifications (20 of 26, they
  carry the latest chat's ID); edit detection by length misses an equal-length edit — use a
  phone-only text hash in the 72-hour list; Android 13+ "restricted settings" blocks the
  notification-access grant for a sideloaded app until allowed — the setup screen must walk the
  user through it; a `chat_history_backup` notification channel marks WhatsApp's backup run (a
  trigger for P3); 5 of 6 message entries carry an address-book contact link — a possible live
  group-sender route, user-controlled, unverified; history effectively starts 2024 (84 messages in
  2017–2023).
- **Schema (names):** text is `message.text_data`; `chat.subject`; `jid.raw_string`/`user`;
  `lid_display_name(lid_row_id, display_name, username)`. `SchemaCheck.REQUIRED` already carries
  them.

## State of the code — uncommitted, Mike reviews and commits

- Reader: `android/app/src/main/java/com/mike/metatron/whatsapp/` (8 files) — stays; P3's core.
- Tests: `android/app/src/test/java/com/mike/metatron/whatsapp/` — 19 pass
  (`./gradlew :app:testDebugUnitTest --tests 'com.mike.metatron.whatsapp.*'`, `JAVA_HOME` = the
  Homebrew openjdk@21); coverage table at `android/app/build/reports/whatsapp_backup_coverage.txt`.
- Probe (throwaway): `android/app/src/waprobe/` + the `waprobe` build type in
  `android/app/build.gradle`; built only by `./gradlew assembleWaprobe`. `assembleDebug` — the APK
  Iva gets — contains none of it.
- `AndroidManifest.xml`: `allowBackup="false"` (P4). `.gitignore`: admits the tests and
  `src/waprobe/`.
- **Mike's phone runs the probe build.** Any later `assembleDebug` sideload replaces it and drops
  the probe. **Removing the probe after Phase 0:** tap "Delete all probe data", turn Notification
  access off, then delete `src/waprobe/` and the build type.

## Then — what is left of the build

LM ruling → (on increments (a)) 0a′ + the reader extension → **Phase 1, VM side** (V1–V9; ~1–2
sessions, ~3–5M tokens — the second-user build it waited on has landed) → **M2 labelling** →
**Phase 2, phone** (P1–P5; ~2 sessions, ~4–7M) → **Phase 3, alerts and security** (P6, cards, B1b
WhatsApp rows; ~1 session, ~1–2M) → **Phase 4, a week of real use.** Fable diff reviews on 2 and 3.

**Budget for this session:** ~0.3–0.5M Opus tokens; Mike ~15 minutes (survival read + two
rulings), plus the optional edit test. Close with `/archive`.
