# WhatsApp phone reader — review before Phase 2 (2026-11-23, Fable 5.2, clean-room)

**What was reviewed:** the 15 files in `android/app/src/main/java/com/mike/metatron/whatsapp/`, their
tests (`src/test/…/whatsapp/`), and how the probe calls them (`ProbeProofRun`, `ProbeM2Run`,
`ProbeActivity`'s sweep). Read against the input plan § 3 P1–P5 and § 4, the Phase 1 contract
(`whatsapp_phase1_build_plan_2026-11-23.md` § 2.2) and the format description §§ 1, 12.

**The question:** what would break, leak or lose a message once this runs every night with nobody
watching?

**The answer in one paragraph.** The decrypt-and-decode core is sound: nothing found that reads a
damaged, truncated, wrong-key or half-written file as good, nothing that logs message text, and
memory and storage are fine at the sizes measured. **The risks are all at the edge the probe has
been covering by hand.** Deleting the decrypted copy, checking the schema, numbering same-second
messages, and noticing that backups have stopped are each done by probe code or by nobody — the
reader does not own them. And the "messages since the cursor" shape loses a message whose text
turns up after the cursor has passed its time. 16 findings: 4 high, 5 medium, 7 low. None needs a
separate session before the Phase 2 build; seven are small reader changes that should be the
build's first step, before any unattended caller exists.

**Clean-room:** no transcript, no reference implementation, no web, no backup and no message
content were opened. Every claim about WhatsApp's behaviour below that is not in the format
description is marked *unverified*.

**Recommendation key.**
- **Before** — a change to the reader itself, built and tested as step 1 of the Phase 2 build,
  before the nightly job is wired to it.
- **During** — a requirement on what Phase 2 builds around the reader (the job, the posting, the
  phone's own lists).
- **Accept** — leave as is; the reason is stated.

**Rulings:** *pending — Mike rules on each number; rulings are recorded in § 4.*

---

## 1. Findings, by severity

### High

**1. A crash mid-run leaves every chat in plain text on the phone, and nothing in the app removes it.**
- *Where:* `BackupDecryptor.java:162` deletes only the half-written file, and only if the process
  survives to `finally`. `BackupDecryptor.java:167-174` (`deleteDecrypted`) removes one copy by its
  exact name. The delete-on-every-exit and the start-up sweep are probe code
  (`ProbeProofRun.java:45-50`, `ProbeActivity.java:192-198`); `src/main` has neither, and no single
  entry point that decrypts, reads and deletes.
- *What a user would notice:* nothing — a ~36 MB database of all chats (not only shared ones) sits
  in app storage until something deletes it.
- *Scenario:* the nightly job is killed between decrypt and delete (low memory, a reboot, a force
  stop). The process dies, so no `finally` runs. In the main app nothing sweeps; if the job's file
  name ever changes, a sweep by name misses the old one.
- *Second scenario, same cause:* the probe's sweep runs when its screen opens. A sweep that fires
  while a run is in flight deletes the `.partial` file under it, and the run ends in
  `IOException: rename failed` (`BackupDecryptor.java:149`). This is a plausible cause of the one
  undiagnosed `IOException` in the 11-23 P3 log entry — *not confirmed*.
- *Fix direction:* one main-source entry point for "read tonight's set" that owns a private work
  folder, deletes in `finally`, destroys the key, and sweeps **the whole folder** (not named files)
  at process start and at the start of each run, under the same one-run-at-a-time lock the job
  uses. Never sweep from a screen.
- *Recommendation:* **During** — it is P3's own scope; the Phase 2 prompt should state it as a
  requirement with a test (kill after decrypt → next start leaves the folder empty).

**2. A message whose text arrives late never comes up.**
- *Where:* the cursor shape — `FullBackupMessages.java:39` (`timestamp >= since`) and
  `BackupCombiner.java:155` — with the contract's cursor defined as "the newest time now
  delivered" (§ 2.2).
- *What a user would notice:* a message they can read in WhatsApp never reaches Metatron; or a
  question they answered from another device is raised again.
- *Scenario A:* a row exists with no text while WhatsApp waits for the sender's device, and is
  filled in days later under the same key and the same original time (*unverified against the
  backup; ordinary WhatsApp behaviour*). The first night it has no text and is not sent; by the
  time it has text, the cursor is past it.
- *Scenario B:* a message is delivered to the phone after a backup that already holds a
  later-stamped message from another chat. It keeps its send time, so it is below the cursor. The
  live feed catches it only if the chat is unmuted and the listener is up; the user's own messages
  have no live path at all.
- *Fix direction:* the job reads from **the cursor minus an overlap** (about 8 days, longer than
  the ~6 days between full backups) and relies on the deterministic key to drop re-sends. For
  that to be safe the phone must remember what it sent from the backup too — key plus a salted
  hash of the text, for the overlap window — so an unchanged copy is skipped, a filled-in or
  edited one goes as an `update`, and a re-send is never mistaken for a same-second clash. That
  list replaces the 72-hour list's text-length compare, which the 10-30 probe already showed
  misses an equal-length edit. **Cost:** a few tens of KB on the phone, pruned by age, deleted
  with the app's data; a larger nightly post (8 days of shared-chat keys instead of 1); $0 to run.
- *Recommendation:* **During.**

**3. If WhatsApp stops writing backups, or end-to-end backup is switched off, nothing says so.**
- *Where:* `IncrementSet.java:44-45` reads `msgstore.db.crypt15` whenever it exists and never looks
  at its age or at a crypt14 file beside it. `BackupLocator.java:60-61` names
  `crypt14_end_to_end_off` only when **no** crypt15 file is left.
- *What a user would notice:* WhatsApp items simply stop coming up. It reads as a quiet week.
- *Scenario:* the user turns end-to-end backup off, or WhatsApp's own backup starts failing (full
  storage, signed out). The last good crypt15 file stays in the folder (*unverified that WhatsApp
  leaves it*). Each night the job reads it, finds nothing newer than the cursor, and exits clean.
  A "last backup processed" time (plan § 6, Unseen 1) keeps looking fresh, because processing
  succeeded.
- *Fix direction:* the reader refuses `crypt14_end_to_end_off` when a crypt14 file is newer than
  the newest crypt15, and returns the set's newest **write time**. Phase 2 posts that time with
  each run and raises a notice when it is older than about 36–48 hours. The freshness signal must
  be when WhatsApp wrote the file, not when the job last ran.
- *Recommendation:* **Before** for the reader half (small); **During** for the notice.

**4. A WhatsApp update that moves the message text would make every message arrive blank, with no error.**
- *Where:* `IncrementReader.java:351-360` — the text paths are lenient by design: a path that is
  absent or does not decode is "no text". `SchemaCheck.java:25-29` checks that `text_data` exists,
  not that it is still where text lives.
- *What a user would notice:* nothing comes up from WhatsApp; no refusal, no notice.
- *Scenario:* an update renumbers a content field in `messages.bin` while `format_version` stays
  `1.0`, or keeps the `text_data` column but stores text elsewhere. Chat, key, time and row id
  still decode, so no refusal fires. Every message is textless, and textless messages are not sent.
- *Fix direction:* the reader already counts what is needed (`Combined`, `Increment.textUndecodable`,
  `withoutKeyId`, `withoutChat`). Phase 2 posts the night's counts — received messages read, how
  many had text, per source — and a run with a meaningful number of received messages (say 20+)
  and none with text is raised as "WhatsApp changed how it stores messages". Add a base
  key-collision count (finding 10) to the same record.
- *Recommendation:* **During.**

### Medium

**5. Two messages in one chat in the same second can come up twice — and, rarely, one is lost.**
- *Where:* the contract's `ordinal` (§ 2.2) is not produced anywhere in the reader — `WaMessage` has
  no such field. `BackupCombiner.java:158` sorts by milliseconds then row id, but a message new in
  an increment carries `…000` milliseconds, so it sorts **ahead of** a same-second message read
  from the full backup whatever its row id.
- *What a user would notice:* the same WhatsApp message listed twice. In the rare case below, one
  message missing.
- *Scenario (double):* the user's own message and a reply land in the same second. Live, the reply
  is ordinal 0 (the listener sees only received messages). From the backup, numbered over every
  row, it is ordinal 1 — a new key, so a second fact. The same happens if a system line or a
  photo sits in that second, or if a message is numbered once from an increment and later from
  the full backup.
- *Scenario (lost):* two received messages swap ordinals between the two paths and have the same
  text length; the phone's 72-hour list judges the backup copy "unchanged" and skips it.
- *Fix direction:* the reader assigns the ordinal itself, in one tested place: per canonical chat,
  per whole second, over **received** rows only, ordered by row id, computed before the allowlist
  and since filters. The since-time becomes whole seconds in the reader's interface, so a boundary
  can never cut a second in half. Whether system lines sit among received rows needs the
  message type (finding 6). The hash list in finding 2 removes the loss case.
- *Recommendation:* **Before.**

**6. Something that is not a reply may be counted as one, so an unanswered question is never raised again.**
- *Where:* `FullBackupMessages.java:37-39` does not read `message_type`; `WaMessage` cannot carry
  it. Phase 2 sends every from-me row as a reply marker (plan P3).
- *What a user would notice:* a question they never answered drops off, because the awaiting-reply
  backstop (V6) believes they replied.
- *Scenario:* a from-me row that is a system line or a call entry rather than a sent message
  (*unverified — which types are from-me is not counted for anything but type 90*).
- *Fix direction:* read `message_type` in the full-backup path (and require it in `SchemaCheck`);
  decide from the probe's existing per-type summary which from-me types are real sent messages;
  one count to learn whether increments carry a type at all. Until then the Phase 2 job cannot
  tell them apart.
- *Recommendation:* **During**, with a walkthrough tap for the count (M).

**7. A change in WhatsApp's format is reported as "The key doesn't match this backup".**
- *Where:* `BackupDecryptor.java:249` and `IncrementReader.java:105` — any payload that does not
  start as zlib, SQLite or ZIP is `wrong_key`, decided before (or regardless of) the tag check.
- *What a user would notice:* a prompt to re-enter a key that is correct, every night.
- *Scenario:* WhatsApp changes the compression of the payload. The tag would verify, which proves
  the key is right, but the first bytes are unfamiliar.
- *Fix direction:* `wrong_key` only when the tag also fails; tag verifies but the payload is
  unknown → `unknown_format` ("WhatsApp changed its backup format"). In the streaming path this
  means carrying on to the tag with the output discarded.
- *Recommendation:* **Before.**

**8. A renamed column in the nightly files silently un-links hidden ids, and those chats stop arriving.**
- *Where:* `BackupCombiner.java:48-50` — a `jid` row without a text `raw_string` **removes** the id
  rather than refusing. `BackupCombiner.java:55` applies `jid_map` deletions as `lid_row_id`
  values without checking that the header's id field is `lid_row_id`.
- *What a user would notice:* one-to-one chats that WhatsApp keys by hidden id go quiet, with no
  refusal.
- *Scenario:* an update renames `raw_string` in the delta rows. Every changed id is dropped from
  the table, its chats no longer canonicalise to the phone-number id on the share list, and the
  allowlist drops them.
- *Fix direction:* require the `raw_string` key in each `jid` row and the expected id field for
  `jid_map`; refuse `increment_missing_part` otherwise. A present-but-null value may still remove.
- *Recommendation:* **Before.**

**9. One unreadable or missing nightly file stops all backup reading until the next full backup.**
- *Where:* `IncrementSet.java:57-61` and `BackupCombiner.java:120-124` refuse the whole set on a
  gap; any refusal from `IncrementReader.read` does the same in a caller that needs every file.
  `IncrementReader.java:280` also refuses an empty messages file — never observed, so whether a
  night with table changes but no messages produces one is *unverified*.
- *What a user would notice:* for up to ~6 days, no group senders, no muted chats, no reply
  markers — with a notice, if Phase 2 surfaces the refusal.
- *Fix direction (if not accepted):* return the readable prefix (base plus increments 1..j) with
  the gap named beside it; accept an empty messages file when the header counts zero.
- *Recommendation:* **Accept** the all-or-nothing rule for now — it is a named refusal, not a
  silent one, and no gap has been observed in 9 increments — **provided Phase 2 shows it to the
  user.** Revisit the first time it fires.

### Low

**10. Two rows that share a key after canonicalising overwrite each other uncounted.**
`BackupCombiner.java:130`. The format description records key_ids on two rows "told apart by
chat"; if a pair's chats are the same chat under its two ids, one row replaces the other
silently. *Fix direction:* count collisions and report them with finding 4's counts.
**Before** (a counter).

**11. Phase 2 needs things the reader does not offer yet.**
- `BackupCombiner.canonicalise` and `Canon` are package-private (`BackupCombiner.java:74`, `:167`).
- Nothing reads the chat list, group subjects or `lid_display_name` for the share list (P1);
  `Increment` parses those tables' changes but nothing folds them.
- Nothing reports "this hidden id gained a link tonight", which P1's migration and the contract's
  `merges` need. Without it a shared chat silently leaves the allowlist the night its id changes.
- `FullBackupMessages.read` does not run the schema check (`FullBackupMessages.java:31`); the code
  that reads the schema out of the database lives in the probe (`ProbeBackup`). A caller that
  forgets it turns `schema_changed` into an unnamed SQLite crash. `chat._id`, used in the join,
  is not on the required list.
**During** — list them in the Phase 2 prompt.

**12. Memory caps on a nightly file are far above what a phone can hold.**
`IncrementReader.java:40-42`: a file at the 32 MiB inflated cap needs roughly 100–200 MB of heap
across the buffer copies, the ZIP entries and the JSON text — a crash, not the named
`increment_too_large`. Observed files are 0.15 MB. *Fix direction:* lower the inflated cap to
about 8 MiB. Separately, the full-backup inflate has no output cap; it is bounded only by the
10× free-space check against a measured 2.2×. **Before** (a constant) or **Accept**.

**13. Refusal detail text can carry names taken from the file.**
`IncrementReader.java:462` and the `need(...)` calls put entry and file names from `header.json`
into the exception message. They are WhatsApp's own table-file names, not message content, but
they are decrypted content. *Fix direction:* Phase 2 reports `error.code` and never
`getMessage()`; `ProbePayload.maskDigits` is the probe's version of this. **During** (a rule).

**14. Nothing ties a nightly file to the full backup beside it.**
`Increment.creationDateMs` is parsed and unused. If stale increments ever sat beside a new full
backup, older versions would overwrite newer ones. No path to that state was found short of
WhatsApp failing mid-rotation. *Fix direction:* refuse when an increment's creation date predates
the base file's write time, or dates do not rise with N. **Accept**, or **Before** if cheap.

**15. A millisecond time in a nightly file would be multiplied by 1,000.**
`IncrementReader.java:329,347` accept any positive value as seconds. The VM would reject the
result, so it is not silent, but the refusal belongs on the phone. *Fix direction:* refuse a
value ≥ 10¹¹ as `increment_format_unknown`. **Before** (one line).

**16. Tests assert the refusals well; four things Phase 2 depends on are untested.**
- `FullBackupMessages` has no test at all (it needs Android's SQLite); its query, the group-sender
  rule and both "not returned" counts are verified only by counts on one phone.
- `deleteDecrypted` and the side files are never asserted.
- No test for a write failure (storage filling mid-decrypt) or a file growing during the read
  (`BackupDecryptor.java:109,127`) — both paths look right by reading.
- No test at the since boundary, for a base key collision, or for same-second order.
**During** — each fix above lands with its test; add an on-device or Robolectric test for
`FullBackupMessages`.

---

## 2. Checked and fine — do not re-review

1. **Plaintext on disk, the decrypt path itself.** Output goes to `.partial` and is renamed only
   after the tag, the end of the zlib stream and the SQLite header all pass; every refusal and
   I/O error deletes it (`BackupDecryptor.java:157-163`); the tests assert no output and no
   `.partial` after each refusal. Increments never touch disk — container, inflate and ZIP are in
   memory, so there is no temporary ZIP output. `-journal`, `-wal` and `-shm` are deleted with the
   copy. The work folder is `no_backup`, and `allowBackup` is false.
2. **Text in logs.** The reader makes no log calls. `WaMessage.toString` prints a row id only; no
   other class overrides `toString`. No exception message carries message text, a jid, a key or
   the phone-number suffix (header field 4 is skipped unread). JSON errors name a position only.
3. **Named refusals**, each traced: increment gap (`increment_gap`, with the count readable); a
   file still being written (10-minute rule, a 5-second size look, and a second check during the
   read); a missing table or column (`schema_changed`, when the caller runs the check — finding
   11); wrong key (`wrong_key`, with the exception in finding 7); crypt14 (`crypt14_end_to_end_off`
   from the header, with the exception in finding 3); a missing `jid_map` (`schema_changed`);
   truncated (`truncated` or `integrity`). No path returns an empty result in place of a refusal.
4. **GCM.** The 16-byte-IV counter derivation, the 32-bit counter increment, the tag over the
   ciphertext length, and constant-time comparison are correct by reading and cross-checked
   against the platform in `GcmTest`.
5. **Key handling.** The root key and typed characters are wiped; the derived key is destroyed by
   the caller; neither reaches an exception.
6. **Protobuf and JSON decoding.** Bounds are checked before every read; unknown fields are skipped
   by wire type; a group wire type, a zero field number or an over-long varint refuses; JSON depth
   is capped; a duplicate key or ZIP entry name refuses. A message whose key names a different
   chat from its block refuses, so nothing can be filed past the allowlist.
7. **The combine.** Increments apply in N order; later version wins by (canonical chat, from-me,
   key_id); a `jid_map` row that arrives in an increment canonicalises that night's messages and
   the base's alike; deletions are counted and never applied; the full backup's milliseconds are
   kept for a replaced message; the allowlist is applied to canonical ids and an empty one
   returns nothing.
8. **Resources at measured sizes.** The full backup streams through 64 KB buffers (0.9 s, 16.4 →
   36.4 MB on Mike's phone); reading every message since 2017 into memory worked in the probe;
   short storage is refused before any write (`insufficient_space`, tested at the byte).
9. **Rotation races.** A full backup or increment appearing mid-run ends in `being_written`,
   `integrity` or an `IOException` — never a mixed read. Phase 2 should treat `IOException`,
   `being_written` and `no_backup_found` as "retry later", not as a fault.
10. **Deleted-file recovery.** Plain deletion with no overwrite, on storage the platform encrypts
    per file. Accepted as is.

---

## 3. What Phase 2 should carry from this review

For the Phase 2 build prompt (Opus 5.5, high), in build order:

1. **Step 1, reader changes with tests** — findings 3 (reader half), 5, 7, 8, 10, 12, 15, as ruled.
2. **The nightly entry point** — findings 1 and 11: one owner for decrypt, schema check, read,
   delete, key destroy and the folder sweep, under the job's lock.
3. **The cursor with an overlap and the sent-hash list** — finding 2.
4. **The night's counts and the two notices** (backup stale; text gone) — findings 3 and 4.
5. **Message type and reply markers** — finding 6, after one probe count.
6. **Report codes, not messages** — finding 13.

**Estimated added cost** to Phase 2's 4–7M (plan § 6): about 0.5–0.9M Opus tokens for steps 1–6
together. Run cost $0. New persistent state: the sent-hash list only (finding 2).

---

## 4. Rulings (Mike)

**Ruled 2026-11-23: "as rec" — all sixteen as recommended.**

| # | Ruling |
|---|---|
| 1 | During — the nightly entry point owns decrypt, read, delete and the folder sweep |
| 2 | During — cursor minus an overlap, and a sent-hash list on the phone |
| 3 | Before (reader half) and During (the stale-backup notice) |
| 4 | During — the night's counts, and a notice when text is gone |
| 5 | Before — the reader assigns the ordinal |
| 6 | During, after one probe count (M — a tap in the Phase 2 walkthrough) |
| 7 | Before |
| 8 | Before |
| 9 | Accept, provided Phase 2 shows the refusal to the user |
| 10 | Before |
| 11 | During |
| 12 | Before — lower the inflated cap |
| 13 | During — report the code only |
| 14 | Accept |
| 15 | Before |
| 16 | During — each fix lands with its test |

**Also ruled:** the "Before" changes are built from this session rather than waiting for the
Phase 2 build (*"spin off fixing agents from here unless inadvisable"*). Built by one Opus agent,
not several — the seven changes share three files — and reviewed here before commit. The
"During" items cannot be built yet: what they change does not exist until Phase 2.

## 5. Built 11-23 — the seven "Before" changes

Built by one Opus worker, diff reviewed here line by line (Fable). Reader tests 33 → 41, probe
task 79 → 87, 0 failures (`cd android && ./gradlew --offline testDebugUnitTest testWaprobeUnitTest`);
all 14 fixture vectors still pass. Not on any phone: the probe APK was not rebuilt.

| # | What the reader now does |
|---|---|
| 3 | Refuses `crypt14_end_to_end_off` when a crypt14 file is newer than the crypt15 backup; `IncrementSet.newestWriteMs()` returns when WhatsApp last wrote the set |
| 5 | Assigns `WaMessage.ordinal` in `combine`: per canonical chat, per whole second, by row id, received and from-me rows numbered separately, before the allowlist and since filters. `combine` and `FullBackupMessages.read` take the since-time in **whole seconds**. Output is ordered by second, then row id |
| 7 | Unfamiliar first bytes: tag fails → `wrong_key`; tag verifies → `unknown_format` (full backup) or `increment_format_unknown`. A wrong key on a full backup now reads the whole file before refusing (~1 s at 16 MB) |
| 8 | A `jid` row with no `raw_string` key refuses; a null still un-links; `jid` and `jid_map` keyed by any column but `_id` / `lid_row_id` refuse (the `jid` half was the worker's catch, added in review) |
| 10 | `Combined.baseKeyCollisions` |
| 12 | Inflated cap 32 → 8 MiB; entries already read are wiped when the cap is hit mid-ZIP |
| 15 | A message time ≥ 10¹¹ refuses as `increment_format_unknown` |

**Left as it was, deliberately:** a ZIP payload on the full-backup path is still refused at once as
`not_a_message_database`. **Known limit of finding 5's fix:** a received message the increments
leave out renumbers its second when the full backup brings it; the 26 omitted messages counted so
far were all the user's own, which are numbered separately, and finding 2's hash list covers the
rest. The format description § 12 carries the new refusals.

**For the Phase 2 prompt — the probe's proof (button 7) should be tapped once on the rebuilt probe
before the nightly job is wired**, to confirm 9 of 9 increments still decode with the stricter
`jid` checks on real files. That is the one thing these changes have not met: real data.

**MET REAL DATA — 2026-11-23 17:12, Phase 2 Step 0 (clean-room; probe rebuilt with button 9, APK
sha256 `821df61f…5b8f6`).** Button 7 on Mike's phone: **every increment decoded: yes — 9 of 9**
(rotated 11-17 N 1–5, rotated 11-23 N 1–4; no live set yet), **no `REFUSED` line**, decrypted
copies deleted: yes. The combined windows match 11-23 exactly — **547** (11-17 set) and **362**
(11-23 set), in both / text equal 547 and 361 of 362 — so the stricter `jid` checks (finding 8) and
the whole-second order (finding 5) changed no count on real files. One text differs in the 11-23
set: an edit made after its increment was written — the case finding 2's hash list exists for.

**Finding 6's count (button 9, 17:14).** Counts only; the reading is from the numbers, no field
meaning assumed:
- **Increments carry no type field.** No numeric field equals the full backup's `message_type`
  (612 of 612 increment messages matched by row id and key_id). **The content block's field number
  sorts them instead:** in this sample every typed kind with content has its own `1.2.N` (type 0 →
  `{1}`, `{6}` or `{12}`; 1 → `{3}`; 2 → `{8}`; 9 → `{7}`; 92 → `{75}`; 118 → `{102}`); types 7, 15
  and 99 carry **no content block**; type 90 is **never in an increment**.
- **From-me rows in the newest full backup, by type** (rows / with text): 0 — 12,710 / 12,710;
  7 — **6,063 / 105, and type 7 has no received rows at all** (221 belong to no chat); 90 — 1,825 / 0;
  1 — 628 / 89; 2 — 290 / 0; 15 — 49 / 0; 3 — 25 / 0; 99 — 26 / 0; 9 — 17 / 13; 4 — 5 / 5;
  24 — 4 / 4 (no received rows); ≤ 2 each for 11, 13, 16, 20, 81, 116.
- **Which from-me types count as a reply** is decision 5 of the Phase 2 plan, put to Mike there.
