# WhatsApp Phase 2 — the phone posts messages to the VM: build plan (2026-11-23, clean-room)

*Opus 5.5, written from `archive/handoffs/2026-11-23-whatsapp-phase-2-phone-build-prompt.md`. A
delta on the input plan (`whatsapp_input_plan_2026-10-26.md` § 3 P1–P5), the Phase 1 contract
(`whatsapp_phase1_build_plan_2026-11-23.md` §§ 2.1–2.2) and the reader review
(`whatsapp_phone_reader_review_2026-11-23_fable-5-2.md` §§ 3–5). Where this file and the input plan
disagree, this file governs Phase 2. **Status: revised after Fable's adversarial review (2
structural, 5 local — `archive/plans/adversarial_review_whatsapp_phase2_build_plan_2026-11-23.md`;
each closed in place, marked "review N"); two verify rounds — round 1 found 2 partial and 4 new
("verify N", "verify new N"), round 2 closed all six with nothing new. Mike ruled all five decisions (§ 5). Then go-ahead on the todo list (§ 7). Nothing is built.***

**Step 0 passed (11-23 17:12–17:14):** 9 of 9 increments decode on the rebuilt probe, windows 547 and
362 unchanged, copies deleted; the message-type count is in the review file § 5 and drives
decision 5.

---

## 0. What the user gets

Once Phase 2 is sideloaded **and** M4 switches the channel on for `mike`:

1. **He picks which chats Metatron may see**, on the phone, from a list of his chats sorted by
   recent activity — groups by subject, one-to-ones by his own contact name. Nobody is shared until
   ticked (W1).
2. **A message in a shared chat reaches Metatron within seconds** (live, from the notification), and
   **again each night from the backup**, which fills in what the notification lacked: the group
   sender, a long message's full text, an edit.
3. **His own replies are noticed** — as markers only, never their text — so an answered question is
   not raised again.
4. **He is told when the link breaks:** WhatsApp has stopped backing up; the text has disappeared
   from the backups (a WhatsApp format change); the key or the pairing has been refused; a nightly
   file is unreadable. Each in words, never silently.
5. **He can mark "this should have come up"** on a message Metatron missed, by sharing it from
   WhatsApp to Metatron — the only measure of misses now M2 is gone.

**Need met:** fully for the input half (messages in, misses measurable). Alerts (P6), the WhatsApp
cards and the red-team rows stay Phase 3. **One APK for every user (decision 1):** nothing is
switched on or asked for until the VM reports that user's WhatsApp consent — so Iva's install
shows none of it until M7, then works without a reinstall.

---

## 1. Checked against the code and recent work

| Premise in the input plan / prompt | Now | Consequence |
|---|---|---|
| "Java makes no HTTP calls today" (P5) | **Stale.** `PushStore` (`android/…/PushStore.java:148`) already makes authenticated HTTPS calls with the server URL and session token the page hands over via `Metatron.setPushAuth` (`MainActivity.java:296`) on every start | P5 reuses it to **pair**: native code calls `POST /whatsapp/device/pair` itself, so the device token never passes through the WebView |
| `allowBackup="true"` (P4) | **Done** 10-30 — `false`, with the reason in the manifest | nothing to do |
| WorkManager (P3) | Not a dependency; not in the Gradle cache (the build runs `--offline`) | **JobScheduler** instead — the platform API WorkManager wraps on API 23+; no new dependency, no download |
| A Robolectric test for `FullBackupMessages` (finding 16) | Robolectric is not cached either, and downloads a ~150 MB Android jar on first run | an **on-device self-test** on a synthetic database the app writes itself, plus a plain-Java test of the row mapping — § 3.9 |
| The live path numbers received messages by arrival (prompt) | the reader's ordinal counts **every** received row, including rows the listener never sees (type 90: 1,537 received, never text, never in an increment) | a same-second pair of a type-90 row and a text gives the two paths different ordinals → the VM's clash rule re-keys → a **duplicate fact, never a lost one**. Rare; **counted** each night (§ 3.5) rather than redesigned |
| An edited message re-sent as `message` | the VM (`tools/intake_whatsapp.py:681-690`) treats a same-key `message` with a different fingerprint as a **clash** and ingests it as a second fact | the phone must send changed text as **`update`** — the sent-hash list (§ 3.4) is what makes that possible |
| The VM re-checks cheaply | `handle_events` translates and screens **every** shared-chat event **before** its duplicate check (`:646-650`) | re-sending 8 days nightly would re-translate 8 days nightly. The phone's hash list skipping unchanged copies is what keeps the VM's cost flat — a requirement, not an optimisation |
| `waprobe` is throwaway (its manifest says so) | Mike's phone runs it; Phase 2 needs the same two grants | decision 1 |

**Killed by the check:** a native HTTP client from scratch; a JS-bridge hand-over of the device token;
WorkManager; Robolectric.

---

## 2. The reader additions (`src/main/…/whatsapp/`, finding 6 and finding 11)

1. **Message type.** `FullBackupMessages` reads `message_type`; `SchemaCheck.REQUIRED` gains
   `message.message_type` and `chat._id`. `WaMessage` gains `type` (`-1` when unknown) and
   `hasContent` (`null` from a full backup; from an increment, whether `info.2` was present).
   `BackupCombiner.combine` keeps the base's `type` when an increment replaces a row.
2. **A reply rule, in one place:** `ReplyRule.isReply(WaMessage)` — from-me, and `type` in the
   allowed set {0, 1, 2, 3, 4, 9} (decision 5, ruled) when the type is known; when it is not (a row new in an increment),
   `hasContent`. **A type not in the set is not a reply** — an unknown kind errs toward re-asking.
3. **The schema check inside the read.** `FullBackupMessages.read` reads the schema (names only —
   the code moves from `ProbeBackup` to main) and calls `SchemaCheck.require` before any query, so a
   renamed column is `schema_changed`, never an SQLite crash.
4. **Public canonicalisation:** `BackupCombiner.canonicalise` and a `Canon` view become public.
5. **The chat list for P1** — `ChatList.read(database)` plus `fold(increments)`: per chat its canonical
   id, kind, group subject, the hidden id's `lid_display_name` (shown on the phone only, marked as
   the person's own WhatsApp name), and its last message time; folded through the increments'
   `chat`, `jid`, `jid_map` and `lid_display_name` deltas.
6. **"Gained a link tonight":** `Combined.newLinks` — hidden ids that canonicalise differently after
   the fold than before it. Drives the share list's migration and the contract's `merges`.
7. **Group senders for P1's `senders` map:** canonical sender ids seen in each shared group over the
   window — from the messages themselves, so no participants table is assumed.

---

## 3. The phone — design per item

### 3.1 One owner for the nightly read (finding 1)

`NightlyRead.run(ctx, cursorSeconds, shareList)` is the only caller of the decrypt in the app:
locate the live set → `requireComplete` → decrypt the base → schema check → read since
`cursor − overlap` → read each increment → combine (allowlist = shared canonical chats) → **delete
the decrypted copy in `finally` → destroy the key in `finally`**.

- **Work folder:** `no_backup/wa_work/`, holding nothing else. The key lives in `no_backup/wa_key/`
  so a sweep can never take it.
- **One run at a time:** a process-wide lock (`ReentrantLock`) plus a file lock on
  `no_backup/wa_work.lock`.
- **Sweep the whole folder** — every file in it, not names — (a) at process start, from a new
  `MetatronApp.onCreate` (`Application` subclass, registered in the manifest), with `tryLock`; (b)
  at the start of each run, under the lock. **Never from a screen.**
- **Test:** a run killed after decrypt — simulated by leaving a decrypted copy, `-journal`, `-wal`
  and `.partial` in the folder and constructing a fresh `NightlyRead` — leaves the folder empty
  after the start-up sweep.

### 3.2 The nightly job (P3)

**JobScheduler**, one one-shot job scheduled at a time:
- earliest **03:00** (WhatsApp writes at 02:00, format description § 12); prefers **charging**; override
  deadline **06:00**, after which it runs without the constraint;
- on finish it schedules the next night; `being_written`, `no_backup_found` and an `IOException`
  reschedule **+30 min, at most 6 times**, then wait for the next night (review § 2.9);
- **app opened and no successful run for 26 h → run now** (covers a force-stop, which cancels jobs);
- persisted across reboot — needs `RECEIVE_BOOT_COMPLETED` (normal tier).

**Per run:** ask the VM for the cursor (`GET /device/whatsapp/cursor`; `null` → now − 90 days,
W6) → `NightlyRead` → **post the share list, with tonight's senders** (§ 3.9; after the read, so a
member who first wrote tonight is named tonight — verify 6) → build events (§ 3.4) → post in
batches → post the run report (decision 4) → raise or clear notices (§ 3.6).

**A dry run before the channel first opens (review 4; bounded by verify new 3).** When the cursor
call answers 403 `consented_off` — consent recorded, the channel not yet on (§ 4.0) — the job reads,
combines and builds the events and the run report — from now − 90 days — but **posts nothing and
writes nothing to the sent-hash list**. Dry runs happen **only before the channel has ever been
open on this install, and only on the user's tap** ("Dry run now"), or nightly for **7 nights after
that tap**, then they stop until tapped again. **Once the channel has been open, any later 403 stops
all reading:** the job is cancelled, the listener disabled, and nothing is decrypted again until
the channel reopens — so switching the channel off stops collection on the phone as well as the VM
(Phase 1 ruling C). The screen shows
what it *would* send: messages, updates, reply markers, per chat count, and the report's counts and
notices. This is the pre-M4 check: the read, the reply rule, the counts and the notices all meet
real data before anything reaches the VM, and the first night after M4 is compared against the
last dry run.

**Batches (review 3).** At most **100 events and 256 KiB** per post (the VM caps 500 and 512 KiB);
the events client has a **120 s read timeout**, separate from `PushStore`'s 8 s, because the VM
translates and screens every event before its duplicate check (~0.1 s a Bulgarian message). A text
over 4,000 characters is sent as its first 4,000, and **that** is what is hashed, so it is not
re-sent nightly. A 413 or a timeout halves the batch and retries once; a second failure ends the
run for tonight (the keys stay unrecorded, so tomorrow sends them). A per-event `rejected` is
recorded as sent with its reason — never retried — and counted in the run report. The 90-day
first run is ~54 posts.

**The cursor moves per batch (verify new 4).** Events go oldest first, and each batch the VM accepts
carries `cursor` = the newest second in it, sent only while every earlier batch of the run was
accepted. A job the system stops mid-backfill returns "reschedule" from `onStopJob` and resumes
within minutes from the advanced cursor; its read starts at cursor − 8 days, which the sent-hash
list covers, so nothing earlier is re-sent or re-translated.

**Nothing is recorded as sent unless the VM took it (review 1).** A batch whose reply shows
`dropped_not_shared > 0` records **none** of its keys, re-posts the share list and retries once; if
the drop repeats, the run ends with the notice "Your chosen chats are out of step with Metatron"
(§ 3.6).

### 3.3 Read from the cursor minus an overlap (finding 2)

The read starts **8 days** before the VM's cursor (decision 2) — longer than the ~6 days between
full backups, so a message filled in or delivered late within a set is read again. The cursor
posted back is the newest second delivered, never earlier than the last one (the VM stores what it
is sent, `:742`).

### 3.4 The sent-hash list — what was sent, by key (finding 2)

`no_backup/wa_state/sent.json`: per message key `chat|second|ordinal` → **an HMAC-SHA256 of the text
and, separately, of the sender id, under a per-install random salt** (16 and 8 bytes; the sender
hash is empty when the event went without one), and the second it was sent. **Never the text, never
the sender.** Written by both paths. The text hash alone is what § 3.11 looks up.

For each combined message in a shared chat:
- **received, with text:** key absent → `message`; present with both hashes the same → **skipped**;
  either hash different → **`update`**. **So a group message that arrived live without a sender is
  sent again as an `update` the night the backup supplies one** (review 2) — `revise` is the only
  VM path that rewrites a fact's sender;
- **received, no text:** skipped (W4 — text only);
- **from me and `ReplyRule.isReply`:** a `reply_marker` `{chat, time}`, once per key (hash of `""`).

**Pruned** to keys whose second is within overlap + 1 day of the newest cursor, at each run and on
each live write. **Replaces** the 72-hour text-length list (P2), which missed equal-length edits
(10-30). A live post that fails is **not** recorded, so the backup sends it.

### 3.5 The night's counts (findings 3, 4, 9, 10)

One `RunReport`, code-written, counts and codes only:
- `backup_written` — `IncrementSet.newestWriteMs()`, when **WhatsApp** wrote the set; and the full
  backup's write time;
- received rows read **across all chats** and how many had text — per source (base window,
  increments); `withoutKeyId`, `withoutChat`, `textUndecodable`, `baseKeyCollisions`, deletions
  listed;
- what was posted: messages, updates, reply markers, skipped as unchanged;
- **same-second groups of two or more received rows in shared chats** — the measure of § 1's
  ordinal limit;
- the refusal, if any, as `error.code` (§ 3.7).

### 3.6 The notices (findings 3, 4, 9)

| Condition | Raised when | Cleared when |
|---|---|---|
| **WhatsApp has stopped backing up** | `backup_written` older than **52 h**, or the full backup older than **8 days** (decision 2) | a newer write |
| **WhatsApp changed how it stores messages** | ≥ 20 received rows read and **none** with text | a run with text |
| **The nightly read is refused** | any refusal other than the retry-later three | the next clean run |
| **WhatsApp link needs re-pairing** | the VM answers 401 on `/device/*` | a successful pairing |
| **Your chosen chats are out of step with Metatron** | a share-list post refused or failed twice, or events dropped as not shared after a re-post (review 1) | a share-list post the VM accepts |
| **WhatsApp link is off** / **needs your consent** | the VM answers 403 `consented_off` / anything else (§ 4.0) | — (screen only, no notification) |

Each notice is raised **once per onset**, not nightly (decision 3 for where).

### 3.7 Codes, never messages (finding 13)

Every `BackupError` met by the job or the screens is reported as `error.code` and shown as its
code-written `userText`. `getMessage()` never reaches a notification, a screen, a post or a log.
A static test greps the Phase 2 sources for `getMessage()` outside the reader's own refusal tests.

### 3.8 P4 — the key, P5 — the device token

- **Key screen**, native (`WhatsAppActivity`), with the probe's protections: password-type field, no
  suggestions, no autofill, `FLAG_SECURE`, wiped on save. `KeyVault` is `ProbeKeyVault` moved to
  main, its file in `no_backup/wa_key/`. **Mike's existing key is not migrated** — he re-enters it
  once (one step at the sideload).
- **Pairing:** the screen's "Pair this phone" button → native `POST /whatsapp/device/pair` with the
  session token `PushStore` already holds → the `d1.` token, stored wrapped by its own Keystore alias,
  never shown, never sent to the page.
- **`DeviceClient`:** every `/device/*` call; **refuses any non-`https://` server URL in code** (the
  network config permits cleartext for the WebView's local mode, so the guard is in the client); 401
  → re-pairing notice; 403 → as § 4.0 and § 3.6 (`consented_off`, else no consent).
- **"Turn off WhatsApp link"** on the screen: revokes the device on the VM, deletes key, token,
  share list, sent-hash list and salt, cancels the job, disables the listener.

### 3.9 P1 — the share list

The screen lists chats from the last nightly read's `ChatList` (an on-demand read if none yet),
newest activity first, with a search box. One-to-ones are named from **Android contacts**
(`READ_CONTACTS`, runtime-requested) by phone number; otherwise "Unknown contact" with the
person's own WhatsApp name in small grey text. Groups by subject (untrusted, set by any member).

- Stored on the phone (`no_backup/wa_state/share.json`): canonical chat id, kind, label, and for
  groups the `senders` map — the user's own contact names only.
- **Posted whole** to `POST /device/whatsapp/share-list` on each change **and on every run, after
  the read** (reviews 1 and 6) — with `merges` on a `newLinks` night, and with each group's `senders`
  map rebuilt from that night's senders and the current contacts, so a new member or a newly saved
  contact is named the same night. Posting the same list again is harmless: the VM replaces
  its copy whole, and nothing is removed. A one-to-one whose label is not from contacts goes with
  label `""` — **a WhatsApp display name never leaves the phone.**
- **An unattended post never shrinks the list from lost state (verify new 2).** The nightly
  re-post sends only a list that carries **the user's own save on this install** and reads cleanly
  — including a pending un-tick, which is the user's save being retried. A missing or unreadable
  `share.json`, or one never saved by the user, means **no share-list post and no events** that
  night, and the screen asks the user to choose chats; **an empty list is posted only at the
  moment of the user's own tap**, never on a retry. After a reinstall the screen says
  "Metatron keeps your previous choices until you save a new list — saving replaces them".
- **The phone keeps which version the VM last accepted.** Until a post is accepted — the channel is
  off, the phone is offline, the VM refuses — the screen shows "not yet sent to Metatron", and the
  next run, change or app open re-posts.
- **Un-ticking a chat** is a purge on the VM at once (Phase 1, W3). The screen says so before it
  posts, and says "removed from Metatron" **only after the VM's reply** shows it; until then the
  un-tick is held as a pending removal and re-posted, and the chat's events are already dropped on
  the phone.

### 3.10 P2 — the live feed

A `NotificationListenerService` for `com.whatsapp`, **disabled in the manifest and enabled at run
time** only while the channel is open (§ 3.12):
- skips group-summary notifications (20 of 26 posts, 10-30); chat id from the conversation
  shortcut, canonicalised through the phone's stored link map; **no chat id → nothing sent**; not
  shared → dropped on the phone;
- a one-to-one under a hidden id the map does not link → held for the backup (P1);
- each messaging-style message: time floored to the second; ordinal by arrival among that chat's
  received messages in that second, kept stable across re-posts by looking the hash up in the
  sent-hash list; sender `""` (no person key observed, 10-30);
- posted only while the VM has accepted the current share-list version; **a post whose reply
  drops or rejects it records nothing** (verify 1), so the backup sends it;
- posted at once; on failure, retried in memory for 10 minutes, then left to the backup. **No
  message text is ever queued on disk.**

### 3.11 "This should have come up" (Mike, 11-23: "Build it in")

An Android **share target** for `text/plain`, "Should have come up", enabled only with the listener
(§ 3.12). The user long-presses a message in WhatsApp → Share → Metatron.
- The phone hashes the shared text and looks it up in the sent-hash list by its text hash.
  **One match** → posts `{keys: [k]}`; **several** (a short "ok" sent in many chats, review 7) →
  posts up to the 5 newest with `ambiguous: true`, and the VM records the outcome of each but counts
  the flag once, under "ambiguous"; more than 5 → `{keys: [], ambiguous_over: n}`; **none** →
  `{keys: []}` (never sent: an unshared chat, older than the window, or WhatsApp's shared text
  differs from the message — *unverified until the first real share; read in the walkthrough*).
- **The text is never posted or stored.** A toast confirms.
- The VM records, per flag, what happened to that key: never received, held back, recorded as
  which category, surfaced or not — and a report prints those counts (decision 4). 90-day expiry.

### 3.12 One APK for every user, switched on by consent (decision 1 — Mike: "This should work for all potential users")

The ordinary `debug` build carries Phase 2 for everyone: the main manifest declares the listener,
`MANAGE_EXTERNAL_STORAGE`, `READ_CONTACTS`, `RECEIVE_BOOT_COMPLETED` and the share target. **What
the user's consent switches on, and nothing before it:**
- **pairing is the first step** (it works with the channel off, Phase 1 § 2.1); the cursor call
  then answers one of three ways (§ 4.0): **`no_consent`** → the screen says "WhatsApp needs your
  consent first" and **nothing else is offered** — no key, no grant, no job; **`consented_off`** —
  consent recorded, the channel not yet on → key, All-files access, contacts and the share list are
  offered, and the job runs **dry** (§ 3.2); **open** → everything;
- the **listener** and the **share target** are `android:enabled="false"` in the manifest and are
  enabled at run time (`setComponentEnabledSetting`) only when the channel is **open**; disabled
  again on any 403, a 401 or "Turn off";
- **All-files access and contacts are never requested without the consent record**, and only at
  the user's own tap in the WhatsApp screen; the job is scheduled only after that.

So a user without consent — Iva until M7 — has the capability in her APK and **nothing active**:
no listener, no grant, no job, no screen beyond "WhatsApp link: not set up". At M7 she pairs and
grants in the same app, no reinstall. **Two checks stand behind that:** the phone's runtime gate,
and the VM's consent gate refusing every `/device/whatsapp/*` call.

**The probe screen stays out of this APK.** `waprobe` remains Mike's re-measuring build, now `debug`
plus the probe screen; it declares the same permission, so moving between the two keeps All-files
access. Mike's phone moves to `debug` at the sideload.

---

## 4. VM changes (decision 4) — `tools/intake_whatsapp.py`, `core/server.py`, tests

Decision 4 ruled (a), Mike 11-23:
0. **The closed gate says which gate** (needed by § 3.12 and the dry run): `ChannelOff` carries
   **`consented_off`** when the user's `whatsapp` consent record exists and intake or the stanza is
   off, else `no_consent`; the 403's detail carries it. **The phone treats every 403 that is not
   exactly `consented_off` as no consent** — today's bare `channel_off` included — so the APK fails
   closed against a VM that predates this change (verify new 1). Today every closed gate reads `channel_off`
   (`tools/intake_whatsapp.py:_require_open`), so the phone could not tell "not consented" from
   "consented, not switched on".
1. `POST /device/whatsapp/run` `{report}` — the § 3.5 counts, validated to a fixed set of integer and
   code fields, **no free text**; stored as the latest report in `whatsapp_state.json` (overwritten).
2. `context_lines` gains one code-written line when the latest report is older than **52 h**, or
   says text is gone, or names a refusal — "WhatsApp messages have not reached Metatron since …".
   That is the only check that survives the phone's job dying. **Raised once per onset (review 5):**
   the state keeps the onset it was raised for and when it was delivered, in the pattern of the
   existing line's `delivered_at` (30-minute delivery window, then not again for that onset).
   **Cleared** by a newer report with none of the three conditions. **Revoking the last device and
   `delete-all` delete the stored report**, so a deliberate "Turn off" raises nothing.
3. `POST /device/whatsapp/missed` `{keys: [...], ambiguous?, ambiguous_over?}` →
   `intake/whatsapp_missed.jsonl` row: when, the keys, and what the VM did with each. 90-day expiry
   with the facts. `python -m tools.intake_whatsapp --missed-report --persona p` prints counts only,
   ambiguous flags apart.
4. Tests in `tests/test_intake_whatsapp.py`; Phase 1's 35 stay green. **Deploys with M4** (Mike,
   M5) — **and before the Phase 2 APK reaches any phone.** Against an older VM the APK still fails
   closed (§ 4.0), but offers nothing until the deploy.

---

## 5. Decisions for Mike

**Ruled by Mike, 2026-11-23** — 1: *"This should work for all potential users."*; 2, 3, 4: *"as rec"*.

| # | Ruling | Options that were put |
|---|---|---|
| 1 | **One APK for every user, switched on by consent** (§ 3.12) — read from Mike's answer as option (b) | (a) a separate `whatsapp` build for Mike, `debug` for Iva — recommended then, rejected: it serves Mike only; (b) one APK, nothing active until consent; (c) keep shipping `waprobe` |
| 2 | **Overlap 8 days; stale at 52 h, or the full backup older than 8 days** | the prompt's 36–48 h would false-alarm after every quiet night — WhatsApp skips a night with no changes (§ 12) |
| 3 | **Both:** a native notification once per onset, and a standing line in the WhatsApp screen | notification only (swiped away); screen only (never opened) |
| 4 | **(a) Extend the VM** (§ 4): +0.3–0.5M tokens, one deploy, ≈ $0 to run; the only check that survives the phone's job dying, and the only way a missed flag says why | (b) phone only — $0, no deploy, silent when the job never runs, misses a bare count |

**5. Which of your own messages count as a reply — RULED, Mike 11-23: "yes"** (put as one plain
question; he could not answer it in type numbers, rightly — they carry no meaning in a clean room):

> When you answer someone in WhatsApp with something other than typed text — a photo, a voice
> note, a document — should Metatron treat their question as answered?

- **Yes — RULED** → types **0, 1, 2, 3, 4, 9** from a full backup; from an increment, a row
  with a content block. The rule comes from the counts: each of these types is **both sent and
  received** and carries content. It matches what V6 already does — any real message from the user
  in the chat after the question clears it; nothing reads whether it answers. Cost: something sent
  in that chat that is not an answer clears the question.
- **No** → type **0** and increment rows with text only. Cost: an answer by photo or voice note is
  re-raised once after 24 h (W8), visibly.
- **Either way excluded:** **7** (6,063 rows, never once received, 221 in no chat — written by the
  phone itself), **90** (never text, never in an increment), **15 and 99** (no content block in
  increments), every rare or one-sided type, and any type not seen before.

---

## 6. Files and tiers

**Nothing Red, nothing Denied.** `core/scheduler.py` untouched.

| Area | Files | Tier |
|---|---|---|
| Reader | `android/…/whatsapp/{WaMessage,FullBackupMessages,SchemaCheck,BackupCombiner,IncrementReader}.java`; new `ReplyRule`, `ChatList` | Amber (app source) |
| Phone | new `android/…/whatsapp/{NightlyRead,NightlyJob,SentHashes,RunReport,Notices,KeyVault,DeviceClient,ShareList,WhatsAppActivity,WaListener,MissedShareActivity}.java`; new `MetatronApp.java`; `MainActivity.java` (one bridge method: open the WhatsApp screen) | Amber |
| Build | `android/app/src/main/AndroidManifest.xml` (the declarations, components disabled); `android/app/build.gradle` (`waprobe` = `debug` + the probe screen) | Amber |
| Page | `static/index.html` — one menu entry opening the native WhatsApp screen, for a signed-in user in the app | Amber |
| Tests | `android/app/src/test/…`, `src/testWhatsapp/…`; `tests/test_intake_whatsapp.py` | Green |
| VM (decision 4a) | `tools/intake_whatsapp.py`, `core/server.py` (two routes) | Amber |

---

## 7. Todo list — build order (nothing starts before Mike's go-ahead)

**Session A — the backup path, end to end** (~3.3–5.0M Opus):
1. Reader additions § 2, with tests (plain Java; the SQL half in the on-device self-test).
2. `NightlyRead` with lock and sweep § 3.1, `SentHashes` § 3.4, `RunReport` § 3.5 — tests incl. the
   kill test, the prune, skip / update / message, a write failure mid-decrypt, `deleteDecrypted` and
   the side files.
3. Manifest gating § 3.12; `MetatronApp`; `KeyVault`, `DeviceClient`, pairing § 3.8.
4. `ChatList` → share-list screen and post § 3.9.
5. `NightlyJob` § 3.2–3.3; notices § 3.6; codes-only § 3.7 with its static test.
6. VM: the named gate (§ 4.0), run report, stale line and missed endpoint § 4, with tests.
7. On-device self-test (synthetic database: `FullBackupMessages`, schema check, the reply rule).
8. Fable diff review; fix; full test run; build the `debug` APK; commit (no push of others' files).

**Session B — live and misses** (~1.1–1.7M Opus):
9. `WaListener` § 3.10, gated enable; tests on synthetic notifications.
10. "Should have come up" share target § 3.11.
11. Fable diff review; fix; APK; commit.

**Then (M5, a walkthrough with Mike, ~40 min), in this order:**
1. **Deploy** session A's VM change (§ 4; harmless with the channel off).
2. **Seed `mike`'s consent only** — `scripts/accounts.py seed-consent mike --scopes whatsapp
   --evidence "Mike W10, 2026-10-26"` — leaving the stanza off. The gate now answers `consented_off`,
   not `no_consent`.
3. **Sideload** the `debug` APK; pair; enter the key; grant All-files access and contacts; tick
   chats (M3); tap the self-test.
4. **Read the dry run** (§ 3.2) — tapped at once and again the next morning after the 03:00 job:
   would-send counts per chat, the reply markers, the run report, any notice. **Nothing has reached
   the VM.**
5. **Then the rest of M4** — the stanza on and the translation model check — and the first real
   night is compared with the last dry run.

**Why this seam, not the prompt's** ("P4–P5 and the nightly job first; the live feed and share list
second"): the nightly job posts only shared chats, so without P1 it has nothing to send — and with
the dry run (review 4) session A's whole path meets real data before anything is posted.

---

## 8. Costs

**Build.** Session A ~3.3–5.0M, session B ~1.1–1.7M Opus 5.5 (together 4.4–6.7M, inside the
prompt's 5–8M); Fable 5.2 plan review ~0.2–0.3M, two diff reviews ~0.4–0.7M. **Model:** Opus 5.5
high to build (native Android, state across two paths, privacy edges); Fable 5.2 for the reviews.
Workers may build the Amber chunks; the lead reviews each before the next.

**Mike.** 20–30 min on § 5; ~30 min walkthrough after session A; ~10 min after B; the deploy in M4.

**Run.** **$0 on the phone** — one ~1 s decrypt a night (36 MB, measured), on charge when it can;
the listener costs one HTTPS post per shared message. **VM: unchanged from Phase 1** while the
channel is off; once on, the sent-hash list means the VM translates and screens only new or changed
messages, not 8 days a night.

**Ancillary.** A ~36 MB transient decrypt (swept); the nightly post of reply markers and changes;
one JobScheduler entry.

**Unseen — no meter reports these:**
1. **A force-stop cancels the job** and Android says nothing. Covered by the 26-h app-open rerun and,
   with 4a, the VM's stale line; with 4b, by nothing while the app stays closed.
2. **A reinstall loses the sent-hash list and salt:** the first run re-sends 8 days — unchanged ones
   are duplicates the VM drops, an edited one becomes a second fact (clash rule). Bounded to once.
3. **Ordinal mismatch** between paths (§ 1): duplicates, counted nightly.
4. **The key opens every chat** (input plan § 6, Unseen 4) — unchanged; the decrypt now runs every
   night unattended, so the sweep and `finally` are the protection.

**Things that persist between runs** — unit, what deletes it, restart, meter:

| What | Size / unit | Deleted by | On crash / restart / reinstall | Meter |
|---|---|---|---|---|
| Sent-hash list + salt | ~120 B per key; shared chats over 9 days ≈ a few hundred keys → **tens of KB** | pruned by age each run and each live write; "Turn off"; uninstall | survives restart; lost on reinstall (Unseen 2) | its entry count on the WhatsApp screen |
| Share list + link map | ~1 KB per shared chat | un-tick; "Turn off"; uninstall | survives | the screen lists it |
| Wrapped backup key | 60 B + one Keystore alias | "Remove key"; "Turn off"; uninstall | survives | "key stored" on the screen |
| Device token | ~100 B + one Keystore alias; VM registry row | "Turn off" (revokes on the VM); VM expiry after 30 days unused | survives; an orphan on the VM expires itself | VM `last_used` |
| Job schedule | one persisted job | "Turn off"; uninstall; **force-stop** | rescheduled at boot and on app open | last run time on the screen |
| Last run report | < 1 KB, overwritten | "Turn off" | survives | the screen; the VM (4a) |
| Decrypted copy | ~36 MB, one run's life | `finally`; the sweeps | swept at next process start | none — hence the kill test |
| VM missed flags (4a) | a few hundred B each | 90-day expiry; channel purge | — | `--missed-report` |

---

## 9. Not this build

Phase 3 (P6 alerts, the cards, B1b red-team rows), M4, Iva's switch-on (M7), media (W4), replying
on the user's behalf (§ 9 of the input plan).
