Model: Opus 5.5 — a short close-out with Mike, plus one small clean-room probe change (the increment test). It must NOT read any crypt implementation: if it does, it can no longer write clean-room code (W9).

# WhatsApp input — close Phase 0: survival test, increment test, two rulings, then Phase 1

> **Revised 2026-11-22 after a Fable adversarial review** —
> `archive/plans/adversarial_review_2026-10-31-whatsapp-phase-0-close-survival-lm-increments-prompt_2026-11-22.md`.
> Its four findings changed: the clean-room fence (now any reference-reading session, any date;
> the `/private/tmp` copy deleted first), the survival read (now a controlled test, because a
> silent night cannot tell a dead listener from no messages), the increments ruling (an increment
> test comes first, because nothing shows the reference covers increments at all), and option (b)
> (re-priced as loss, not lag). The probe has been on the phone since 10-30; nothing in the logs
> shows an `assembleDebug` sideload since — confirm on the phone before relying on it.

Phase 0b and the Phase 0 probes ran on 2026-10-30 (log § 2026-10-30, WhatsApp). The reader
decrypts Mike's real backup on his phone; live notifications identify every chat; the dedup key
matched 5 of 5. **Three things are still open and come first — in this order.**

## ⛔ Clean-room rules — still binding (rules 2 and 4 widened 11-22)

1. Do not read, install, download or search for `wa-crypt-tools` or any other crypt12/14/15
   implementation. Web access stays denied; do not ask Mike to lift it.
2. **An allowlist, not a blocklist.** Transcript names are generated, not chosen, so a
   reference-reading session's transcript cannot be recognised without opening it. Therefore:
   - **Open nothing in `archive/transcripts/`** — no date, no exception. You need none of them.
   - **In `archive/log/` and in `archive/PROJECT_LOG.md`** (generated from those fragments), the
     only WhatsApp entries you may read are **`2026-10-30-02-whatsapp-phase-0b-reader-and-phone-probes`**
     and any later fragment whose title says **"clean-room"**. Every other WhatsApp entry —
     including session 1's `2026-10-26-04-…` and any Phase 0a′ — stays closed. In
     `PROJECT_LOG.md`, search for that fragment's heading and read only its section.
   - **Every WhatsApp session from here on titles its fragment** "clean-room" or
     "reference-reading", so this allowlist keeps working. This one is clean-room.
3. Your sources for format facts are only `archive/plans/whatsapp_backup_format_2026-10-26.md`,
   `tests/fixtures/whatsapp_backup/`, the plan, the allowed log entries, and what the probe reports
   from Mike's phone.
4. **Do not look under `/private/tmp`** outside your own session's scratchpad — the reference copy
   session 1 left there may still exist. Step 0 below has Mike delete it.

## Do these first — the open items

**0. Mike deletes the reference copy (~1 min, before anything else).** On the Mac, delete the
reference copy session 1 left under `/private/tmp` (Mike knows the folder; this session does not
look). Mike confirms it is gone; record that in the log.

**1. Update the probe first — one build serves items 2 and 3 (this session, clean; small).**
The report as built cannot show whether a given message was caught on time: it prints only first /
last event, the longest gap, hourly buckets and masked ID formats, and `post` is
`sbn.getPostTime()` — when WhatsApp posted, not when the listener heard it. All changes are in
`src/waprobe/` only (throwaway); `BackupLocator.newest` stays unchanged.
- **Your FIRST edit of the session — before touching any WhatsApp file or the plan — fences the
  write-time hook.** `scripts/hook_context_gate.py` (`_log_hits`) pushes `archive/log/` excerpts
  into the session whenever a file is edited, without the session opening anything; editing
  `archive/plans/whatsapp_input_plan_2026-10-26.md` would be briefed with session 1's fragment,
  which names it. Change `_log_hits` to skip **only reference-reading fragments**, named
  narrowly: a fixed set holding `2026-10-26-04-whatsapp-input-explored-planned-phase-0a.md`
  (session 1), plus any fragment whose first heading says "reference-reading". **Never skip on a
  mere mention of WhatsApp** — four unrelated fragments mention it in passing (among them the
  whole-codebase review and its High/Medium fixes), and the hook runs for every session in every
  area; a broad match would silently drop their history from every briefing, permanently. Match
  on the filename and the heading line only — never open the excluded fragment to check. Add a
  `tests/` case with synthetic fragments: a fenced name, a "reference-reading" heading, and a
  fragment that mentions WhatsApp in passing and **must still be shown**. Editing the hook file
  itself is safe: session 1's fragment names neither it nor `.gitignore`. Run cost: none — one
  set lookup and one heading check per fragment, inside a hook that already reads every
  fragment.
- **Record receipt time:** in `ProbeListener.onNotificationPosted`, store
  `System.currentTimeMillis()` as `rx` beside `post` (`ProbeStore.record` / `toJson` / `fromJson`;
  old events without `rx` read as unknown).
- **List events in the report:** a new section, every event of the last 72 h, one line each —
  `post HH:MM:SS · rx HH:MM:SS · delay (rx − post) · one-to-one | group | summary · masked chat
  id`. Times and masked ids only; no names, no text, no lengths beyond what is already shown.
- **The increment button** **"5. Try newest increment"** (item 3's test): pick the newest file
  matching `msgstore-increment-N-YYYY-MM-DD.1.db.crypt15` in `BackupLocator.RELATIVE_DIR`, apply
  `requireComplete`, run it through the existing decrypt path (`BackupDecryptor.decrypt` takes any
  `File`), and report **only shapes**: decrypted yes/no (and the `BackupError` if not), bytes
  in/out, the tables present, row counts for `message`/`chat`/`jid`, the min/max message
  timestamp, and how many message ids also appear in the newest full backup. No text, no
  identifiers.
- **Tests — the probe's live in their own source set, never in `src/test/`.** A `src/test/` test
  that names a `waprobe` class breaks the debug variant's compile and takes the 19 reader tests
  (the clean-room coverage evidence) down with it. So: put the event-line formatting and the
  increment filename match in a plain-Java helper in `src/waprobe/` with no Android or `org.json`
  types; test it in `src/testWaprobe/java/com/mike/metatron/whatsapp/`, admitted in `.gitignore`
  beside the existing `!android/app/src/waprobe/` line; run
  `./gradlew :app:testWaprobeUnitTest --tests 'com.mike.metatron.whatsapp.*'`. Then re-run
  `testDebugUnitTest` — 19 must still pass. The `rx` round-trip goes through Android's
  `org.json`, a throwing stub on the JVM, so it is checked **on the phone** instead (next bullet).
- Build `./gradlew assembleWaprobe`; Mike installs it over the current probe (an update keeps
  notification access and the stored events). **Daytime smoke check, before the overnight test
  (~2 min):** someone sends Mike a message while he watches; **Refresh** must show a line for it
  with `rx` filled and a delay of seconds. If not, fix before item 2 — the overnight test would
  otherwise be wasted. First confirm on the phone
  that **WA probe** is still installed — if an `assembleDebug` sideload replaced it, the same
  install restores it, and Mike re-grants notification access (Android 13 "restricted settings").

**2. The survival test — controlled, not a passive read (Mike; one overnight, ~5 min of his time;
after item 1's install).** A passive read cannot fail: a silent night looks the same whether no
message came or the listener was dead; a process the battery manager kills writes no
`disconnected` mark; and the probe shares Metatron's app, so a push or opening the app revives it.
So the test plants a message and checks when the listener heard it.
- Leave battery optimisation at its default (`ON`) — that is what is being measured. Do not
  disable Metatron's pushes: the real listener lives in the same app and will get them too. **Do**
  pick a window that is clean of them.
- The evening before: screen off, phone untouched, Metatron not opened.
- After **at least 4 hours idle**, and **at least 2 hours after the last Metatron push** (the
  morning before Mike picks the phone up suits), someone sends Mike a one-line message in an
  **unmuted one-to-one chat**. They note the send time to the minute.
- Then Mike opens **WA probe** → **Refresh**, **within 72 hours** (events are kept 72 h —
  `ProbeStore.KEEP_MS`), and sends the report to the Mac the way that worked on 10-30:
  long-press → Select all → Share → **Tailscale** → the Mac (lands in `~/Downloads`).
- **Pass:** a one-to-one event at the send time (±2 min) whose `rx` is within ~2 minutes of it.
- **Fail:** no such event, or `rx` only when Mike picked the phone up. Report it; W5's real-time
  notification (P6) depends on this. The usual fix is battery optimisation off for the app —
  Mike's choice, recorded — then repeat the test.

**3. The increment test — before any ruling on increments (Mike runs it, ~5 min).**
Nothing in the repo shows the reference covers increment files at all — the format description has
no increment variant, and how an increment combines with a full backup may be database behaviour no
decryptor's source holds. So a Phase 0a′ session could return nothing. Test first whether the
reader we already have opens one: after a 02:00 increment exists, Mike taps **"5. Try newest
increment"** and sends the report over as in item 2.
- **It decrypts →** the container is the same; no reference session is needed. What is left —
  which increments to read and how they combine — is designed from what the phone shows (does an
  increment hold only rows newer than the last full backup? do ids overlap?), with a fixture built
  from the observed shapes.
- **It does not →** a narrowed Phase 0a′ (item 4, option a).

**4. Two rulings Mike owes — put both, with the recommendation, then record his answers.**

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
  reader ignores them — **as built, P3 would see new messages only after a full backup.** How often
  that is, is unknown: **10-22 is the only unforced full backup on record** — one sample.
  **Put this ruling only after item 3's result** — it decides which (a) is on the table.
  - (a) **Read the increments.** If item 3 decrypted: a clean session extends the reader to pick
    and combine increments from the observed shapes (~0.5–1M tokens) — no reference session. If it
    did not: **a narrowed Phase 0a′** (a session that MAY read the reference, like session 1) whose
    **first and gating question is whether the reference handles increment files at all — if not,
    it stops and reports**, ~0.1–0.2M tokens. Only if it does: the increment layout and naming, how
    an increment relates to the full backup it follows, how to pick the set to read, and one test
    vector per handled variant (~0.5M), then a clean session builds the reader (~0.5–1M).
  - (b) **Full backups only — this is loss, not lag.** The design pairs a live message with its
    backup copy through the phone's sent-key list, kept for **72 hours** (plan P2, § 6;
    `ProbeStore.KEEP_MS`). A backup copy arriving after its key has aged out is not sent as an
    update, and the VM's `seen` set drops it as a duplicate. So for anything older than 72 h at the
    next full backup: **group messages never get a sender, edits never apply, and answered
    questions re-surface** (reply markers arrive only with the backup). Muted chats the listener
    never saw do arrive, late. Making (b) lag rather than loss means keeping keys longer than the
    gap between full backups — that gap is unmeasured (one sample of ~a week) — at a small
    phone-storage cost per kept key (shapes only, no text); price it in the plan if (b) is chosen.
  - **Recommendation (a)** — the nightly path exists to cover exactly what the listener misses, and
    (b) loses most group traffic's senders permanently.
  - On a narrowed 0a′: **write its prompt for a separate session — do not do 0a′ here.** Its log
    fragment's title must say "reference-reading" (clean-room rule 2). The build half then runs in
    a clean session (this one may do it later only if it never reads the reference).

**5. The controlled edit test (Mike, when convenient; optional).** Before: note `distinct
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
  survival — item 2 above.
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

Survival test + increment test → LM and increments rulings → (on (a)) the reader extension, preceded only if the increment test failed by a narrowed 0a′ → **Phase 1, VM side** (V1–V9; ~1–2
sessions, ~3–5M tokens — the second-user build it waited on has landed) → **M2 labelling** →
**Phase 2, phone** (P1–P5; ~2 sessions, ~4–7M) → **Phase 3, alerts and security** (P6, cards, B1b
WhatsApp rows; ~1 session, ~1–2M) → **Phase 4, a week of real use.** Fable diff reviews on 2 and 3.

**Budget for this session:** ~0.4–0.7M Opus tokens (the close-out plus the throwaway increment
button); Mike ~25 minutes over two days (delete the copy, the planted-message test, run the
increment button, two rulings), plus the optional edit test. Run cost: none — the probe is
throwaway and stores 72 h of shapes on the phone only. Close with `/archive`.
