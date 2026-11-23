Model: Opus 5.5 — clean-room native build against shapes observed on Mike's phone; a field map that is inferred, not given, and a combine rule with real edge cases (edits, deletions, gaps). Never delegate the field-map work to a subagent: the judgement is the work.

# WhatsApp P3 — the reader extension: read the nightly increments and combine them with the full backup (clean-room build)

## ⛔ Clean-room rules — binding in full

Rules 1–4 of `archive/handoffs/2026-10-31-whatsapp-phase-0-close-survival-lm-increments-prompt.md`
bind: no crypt implementation, no web; **open nothing in `archive/transcripts/`**; in
`archive/log/` and `archive/PROJECT_LOG.md` read only the WhatsApp entries
`2026-10-30-02-…` and fragments whose title says **"clean-room"**; nothing under `/private/tmp`
outside your scratchpad. This session's fragment is titled "clean-room".

**Rule 5 (new, for this session): field meanings come from match counts, never from memory.**
`messages.bin` is in the generic protobuf wire format, and public WhatsApp clients publish schema
files for it. Those are reference material under W9. If a field number looks familiar, **do not
use what you remember**: a mapping is adopted only when step 1's counts show it on Mike's data.
Write down, beside each adopted field, the count that justified it.

## Read first

1. Plan `archive/plans/whatsapp_input_plan_2026-10-26.md`: § 3 **P3** (and P2's dedup key), § 4
   **INCREMENTS RULED**, **NEXT ROUND RULED**, and both **Found 11-23** paragraphs. Those
   paragraphs list every observed path and the evidence for each.
2. `archive/plans/whatsapp_backup_format_2026-10-26.md` §§ 1, 5–7, 9 (what the reader handles and
   refuses).
3. Log § 11-23 third (the clean-room fragment for the increment-shapes rounds).
4. The code as committed in `8af5ab6`, plus the probe round on top of it: `src/main/…/whatsapp/`
   (reader), `src/waprobe/…/ProbeShapes.java` (the schema-less wire walker; reuse its varint and
   message tests, do not import probe code into `src/main/`), `ProbeIncrement.java`.

## What is known (shapes only — the plan has the full list)

- A **set** is one full backup plus increments numbered 1..k. Live: `msgstore.db.crypt15` plus
  undated `msgstore-increment-N.db.crypt15`. When the next full backup is written, the set is
  renamed with a date suffix. Increments go by N, not by night (a night can be skipped).
- An increment is a crypt15 container, zlib, and inside it **a ZIP**:
  - `header.json`, with `creation_date` and `added_messages` {count on backup, updated, deleted,
    chunks};
  - `sequences.json`;
  - `messages.bin`;
  - per-table `<table>_modified_N.json` = `{"<table>": [full rows keyed by _id]}`;
  - `<table>_deleted_N.json` / `deletedMessages_N.json` = `{"deleted_ids": [...]}`.

  Row ids share the full backup's id space.
- `messages.bin` is one varint-length-prefixed record. The candidate paths:
  - chat blocks `2` (jid `2.1`), each holding messages `2.2`;
  - each message has a key `2.2.1.1` {jid, 0/1, key_id = 79/79 full-backup key_ids}, a time in
    seconds `2.2.1.3`, a sender candidate `2.2.1.5`, text candidates `2.2.1.2.1` / `2.2.1.2.6.1`,
    and a row-id candidate `2.2.2`.
- **Increments carry changed messages, not only new ones** (times as old as a month).

## Steps

**1. Confirm the field map by counts (`src/waprobe/` only; Mike, one tap).** This is button 5 or a
new button 6. Decode `messages.bin` with the wire walker and match each message to the newest full
backup's `message` row by `key_id`. Report **agreement counts only, per candidate**:
- the 0/1 flag vs `from_me`;
- the time vs `timestamp`/1000;
- the key's jid vs the chat's `jid.raw_string`;
- `2.2.1.5` vs the sender's `raw_string`, for group rows;
- each text candidate vs `text_data`: equal / differs / backup null. A "differs" may be an edit
  and is evidence, not failure;
- `2.2.2` vs `message._id`.

Also match against the set's **own base** full backup (the dated one the set was rotated with),
counting new vs already-present messages. If a live undated increment exists, read that; one
appears after each night's 02:00 run. Also report any message that has a text-like field the
candidates miss: its path and count, never its value. **Values never leave the phone**; tests
plant values and assert they are absent, as `ProbeShapesTest` does. Adopt a field only on clear
agreement, and bring anything ambiguous to Mike before building on it.

**2. Write the facts down before the code.** Add **§ 12 "Increments — observed on device,
clean-room"** to the format description, with its provenance stated as the probe, not a
reference. It must cover the container, the ZIP layout, the JSON shapes, the adopted field map
with its counts, the set and numbering rules, and the refusals.

**3. Build the reader extension in `src/main/` + `src/test/`.** Not the WorkManager job, not
posting, not the cursor endpoint: those are Phase 1 and Phase 2.
- **Reading an increment** is a separate entry point. **The full-backup path's accept and refuse
  behaviour does not change**: it still refuses a ZIP payload, and existing tests prove it.
- An increment is small (~0.1 MB), so it is read in memory under a hard cap. Its messages are
  decoded through the adopted map only; any other field is ignored.
- What the reader returns: header counts, message records {chat jid, key_id, from-me, time ms,
  sender jid (groups), text (if any), row id}, deleted message ids, and the deltas for only the
  tables P1–P3 need (`jid`, `jid_map`, `lid_display_name`, `chat`).
- **Finding the set:** the live full backup plus undated increments in N order. A missing N stops
  the read at the gap, with a named refusal and the count it did read; it never silently skips.
- **Combining:** start from the full backup, apply increments 1..k in order, and key messages by
  `key_id` (a later version wins, which is how edits arrive). Deletions apply. Output is
  platform-free, filtered by a caller-supplied chat allowlist and a since-time (the cursor's
  shape; the cursor itself is P3's VM side).
- **Refusals by name, never an empty result:**
  - an unknown `header.format_version`;
  - a missing required JSON key or wire path;
  - a malformed wire record;
  - over the cap;
  - a gap in N.

  Each new name goes in `BackupError` and in § 12. Keep the key and every decrypted byte out of
  logs and exceptions, as the reader does now.
- **Tests:** build a **synthetic increment fixture from the observed shapes** with your own
  encoder: crypt15 container, zlib, a ZIP of `header.json`, `sequences.json`, a `messages.bin`
  written through the adopted map, `jid_modified_1.json` and `deletedMessages_1.json`. Then cover:
  - the decode;
  - the combine order, including an edit (a later increment changes a text) and a deletion;
  - a gap in N, an unknown format version, a malformed record and the cap;
  - **the full-backup path still refusing the ZIP payload.**

  The 19 reader tests grow and must all pass, with `testDebugUnitTest` green and
  `testWaprobeUnitTest` green.

**4. Prove it on the phone (Mike, one tap).** The probe calls the new reader on the real set and
reports, as counts:
- messages decoded per increment, and how many match the full backup by key_id;
- fields agreeing;
- edits seen;
- deletions applied;
- the combined count since a test since-time;
- `decrypted copies deleted: yes` as the last line.

Pass: every increment in the set decodes, and the agreement counts match step 1.

**5. Mike reviews and commits** (guided, area by area, as on 11-23).
- Stage an explicit list, and `git diff` every tracked file first, because two windows share this
  tree.
- `src/main/` and `src/test/` are the deliverable; `src/waprobe/` stays throwaway but is committed.
- Commit message without attribution lines; push; assert `HEAD` equals `origin/main`.

Then write a log fragment whose first heading says **"clean-room"** and never the other phrase,
because the hook's match fails closed. Update plan § 4 and close with `/archive`.

## Serving the APK

`npx cap sync android` **before** `./gradlew assembleWaprobe`. A skipped sync ships a stale web
page: it happened on 11-23, and `scripts/check_apk_sync.sh` checks only the debug APK, so diff the
waprobe APK's `assets/public/index.html` against `static/index.html` by hand. Stage the APK in your
**scratchpad**, not `/tmp/metatron-apk`: `/tmp` is `/private/tmp`, and rule 4 binds. Serve it as
`app-debug.apk` with `python3 -m http.server 8888 --bind 100.70.67.45`, and give Mike the sha256
prefix. Before telling him to download, check `tailscale status` shows `jelly-star` online. On
11-23 it was offline once, and once the phone fetched an older file and Mike tapped before the
install finished. If a report looks unchanged, compare its `run at` with the server log's download
time.

**Budget:** ~0.5–1M Opus 5.5 tokens (step 1 probe ~0.1M; spec ~0.05M; reader and tests ~0.3–0.6M;
proof and review ~0.1M). Mike ~15 min: two taps and the review. **Run cost: none yet.** The reader
runs on the phone, and nothing new runs on the VM until Phase 1. **Unseen:** none; no new
persistent state on either side.
