# WhatsApp local backup format (crypt15) — clean-room description

*Phase 0a of `archive/plans/whatsapp_input_plan_2026-10-26.md` (W9). Written 2026-10-26 by
clean-room **session 1** (Opus 5.5), which read the source of `wa-crypt-tools` 0.1.0 (**GPLv3 or
later**) only in this session's temporary scratch directory under `/private/tmp`, outside the repo
(see § 11 for its removal).*

**This file holds facts about a file format — no code, no copied comments, no identifiers beyond the
format's own field names.** It is the only thing the Phase 0b implementer may use to understand the
format, together with the test vectors in `tests/fixtures/whatsapp_backup/`. **The implementer must
not read, install or fetch `wa-crypt-tools`** — that separation is what keeps the app's licence its
own (legal check L1, plan § 8a).

Sources are marked: **[ref]** = learned from the reference's behaviour; **[device]** = measured on
Mike's real backup 2026-10-26 (counts-only); **[WA]** = WhatsApp behaviour from general knowledge,
**unverified — Phase 0 confirms**; **[std]** = a published standard.

---

## 1. Where the file is, and which one to read

- **[WA]** Android: `/sdcard/Android/media/com.whatsapp/WhatsApp/Databases/`. The current backup is
  `msgstore.db.crypt15`; older ones sit beside it with a date in the name
  (`msgstore-YYYY-MM-DD.1.db.crypt15`). WhatsApp Business uses `com.whatsapp.w4b` and a
  `WhatsApp Business` folder — **out of scope; refuse rather than guess.**
- **[WA]** Reading that folder from another app is expected to need "All files access" on the
  Android versions in play — Phase 0 confirms on Mike's phone.
- **Read the newest *complete* file.** WhatsApp writes its backup overnight; a file modified in the
  last 10 minutes, or whose size changes between two looks 5 seconds apart, is **being written** —
  defer the run, do not read it.

## 2. The key

- **[ref][device]** The 64-digit key WhatsApp shows when the user picks "use 64-digit encryption key"
  is **64 hexadecimal characters** (0–9, a–f; treat case-insensitively) once spaces and any other
  separators are removed. It decodes to the **32-byte root key**. Anything that is not exactly 64 hex
  characters after stripping is `key_format`.
- **[WA]** If the user chose a **password** instead, the key is held by WhatsApp's servers and is
  not available to the user at all. That cannot be detected from the file; it is handled at key entry
  ("choose the 64-digit key option").
- **[ref]** The root key is **not** the AES key. Derive it with **HKDF-SHA256 [std, RFC 5869]**:
  salt = 32 zero bytes, input key material = the root key, info = the ASCII bytes
  `backup encryption`, output length = 32 bytes. (Other info strings exist for Google Drive
  metadata; they are not needed here.)

## 3. File layout

Single-file form — what `msgstore` backups use **[ref]**:

| Offset | Length | Content |
|---|---|---|
| 0 | 1 | **N**, the length in bytes of the header message that follows (so the header is at most 255 bytes) |
| 1 | 0 or 1 | **Optional marker byte `0x01`**, meaning "feature table present". If byte 1 equals `0x01` it is the marker and is **not** counted in N; otherwise the header starts at byte 1. This is unambiguous: a valid header message never begins with `0x01`. |
| 1 or 2 | N | The **header**, a protobuf message (§ 4) |
| next | rest − 32 | **Ciphertext** |
| end − 32 | 16 | **GCM authentication tag** |
| end − 16 | 16 | **MD5** of every byte of the file before it (offset 0 through the end of the tag) |

**No-trailer form [ref]:** the same, without the final MD5 — the last 16 bytes are the tag. The
reference meets it in multi-file backups. **How to tell the two apart:** compute MD5 over all but
the last 16 bytes; if it equals the last 16 bytes, it is the single-file form, otherwise treat the last
16 bytes as the tag. **In both forms the tag must verify** — the MD5 is a checksum, not a substitute.

## 4. The header (protobuf)

Message `BackupPrefix` **[ref]**, field numbers as encoded:

| Field | Type | Meaning |
|---|---|---|
| 1 `key_type` | enum: 0 `WA_PROVIDED`, 1 `HSM_CONTROLLED` | Informational. **Do not branch on it.** |
| 2 `c14_cipher` | message | Present only in **crypt14** files: 1 `cipher_version` bytes, 2 `key_version` bytes, 3 `server_salt` bytes, 4 `google_id` bytes, 5 `IV` bytes |
| 3 `c15_iv` | message | Present in **crypt15** files: 1 `IV` bytes — **16 bytes** |
| 4 `info` | message `BackupExpiry` | 1 `app_version` string; 3 `jidSuffix` string (the **last two digits of the account's phone number** — personal, never log it); 4 `backup_version` integer; 5–39 boolean feature flags |

- Exactly one of fields 2 and 3 is present. **3 → crypt15. 2 → crypt14 → refuse** (end-to-end
  backup is off, and the crypt14 key lives in WhatsApp's private storage). **Neither, or the header
  fails to parse → refuse** (an older crypt12, or an unknown future format).
- **Ignore unknown fields** — a newer WhatsApp may add some.
- **[ref]** Older backups carry fewer feature flags (up to 37 in 2022 files); the flags do not affect
  decryption.

## 5. Encryption and payload

- **[ref][std]** **AES-256-GCM** with the derived key; **nonce = the 16-byte IV** from `c15_iv` (GCM
  accepts a 16-byte nonce — it is not the common 12); **128-bit tag**; **no associated data**. The
  ciphertext covers the whole payload.
- **[ref]** The payload is normally a **zlib stream [std, RFC 1950]** (observed header `0x78 0x01`,
  low compression) wrapping an **SQLite 3 database file**. It can also be an **uncompressed** SQLite
  file (starts `SQLite format 3` followed by a zero byte). A payload starting `PK\x03\x04` is a **ZIP
  archive** — another backup type, not a message database → refuse.
- **Decompression must reach the end of the zlib stream.** If the ciphertext ends first, the file is
  truncated.

## 6. What a correct reader does — the coverage checklist

The plan's eight-point checklist (§ 4 Phase 0a) mapped onto this format:

1. **Variants:** § 7's table.
2. **Integrity:** verify the tag in every case; verify the MD5 when the single-file form is detected.
   **Tell a wrong key from a damaged file by the first decrypted bytes:** with the right key, the
   first block begins `0x78` (zlib), `SQLite format 3` or `PK`; with a wrong key it is noise →
   `wrong_key`. Right key but tag or MD5 failure → `integrity`. Decompression ending early with no
   error → `truncated` (`integrity` is an acceptable report for it).
3. **Key input:** § 2.
4. **Choosing the file:** § 1.
5. **Phone limits:** decrypt and inflate **as a stream**, never the whole file in memory. The GCM tag
   only verifies at the very end, so **write to a temporary file in the app's `no_backup` directory
   and expose nothing until** the tag (and MD5, if present) verify, the zlib stream has ended, and the
   result starts with the SQLite header — then rename; **on any failure, delete the temporary file.**
   **Check free space first.** The decompressed size is not yet measured on a real backup; until
   Phase 0 records the ratio, require free space of at least **10× the encrypted file's size**.
6. **Unknown version:** refuse loudly (`unknown_format`) and feed the freshness check — never return
   an empty result.
7. **Schema drift:** § 8 — check every table and column the app reads, at run time, and refuse
   loudly (`schema_changed`) if one is missing.
8. **Test vectors:** § 9.

## 7. Variants

| Variant | Source | We |
|---|---|---|
| crypt15, single-file form, zlib payload, marker byte present | [ref] the normal case | **handle** |
| crypt15, single-file, **uncompressed** SQLite payload | [ref] | **handle** |
| crypt15, **no-trailer** form | [ref] | **handle** (tag still verified) |
| crypt15 with an **older header** (fewer feature flags, other app/backup version) | [ref] | **handle** |
| crypt15 **without the marker byte** | [ref] | **handle** |
| crypt15 with a **ZIP** payload | [ref] | **refuse** → `not_a_message_database` |
| **crypt14** | [ref] | **refuse** → `crypt14_end_to_end_off` |
| crypt12, or a header that will not parse | [ref] | **refuse** → `unknown_format` |
| **Password-protected** end-to-end backup | [WA] | refuse at key entry (no key exists) |
| WhatsApp **Business** backup | [WA] | out of scope → refuse |
| A file **being written** | [WA] | defer → `being_written` |
| Not enough free space | — | refuse → `insufficient_space` |

## 8. What the reference does that our reader must not

These are where a faithful copy of the reference would be wrong for us — the "gaps" Mike asked to be
covered (2026-10-26):

1. **It carries on after a failed tag check** — it logs an error and **writes the unverified output
   anyway.** Ours refuses and deletes it.
2. **It writes the root key, and the phone-number suffix, to its debug log.** Ours never logs key
   material, `jidSuffix`, or any decrypted content.
3. **It falls back to parsing an unknown header as crypt12 without saying so.** Ours refuses.
4. **It only logs a truncated zlib stream and keeps the partial output.** Ours refuses.
5. **By default it reads the whole file into memory.** Ours streams.
6. **It has no free-space check and no "being written" check.** Ours has both.
7. **It reports a wrong key and a damaged file the same way.** Ours distinguishes them (§ 6.2).

## 9. Schema facts — from Mike's real backup [device]

Measured 2026-10-26 with counts-only queries; names only, no content:

- Tables present: `message`, `chat`, `jid`, `jid_map`, `lid_display_name`, `message_media` and some
  three hundred others.
- `jid_map(lid_row_id INTEGER PRIMARY KEY NOT NULL, jid_row_id INTEGER NOT NULL, sort_id INTEGER)` —
  the full definition.
- Columns the queries used successfully: `message.timestamp` (milliseconds since the epoch),
  `message.from_me`, `message.chat_row_id`, `message.sender_jid_row_id`; `chat.jid_row_id`;
  `jid._id`, `jid.server` (values seen: `s.whatsapp.net`, `lid`, `g.us`, `broadcast`, `newsletter`,
  `bot`, `hosted`, `hosted.lid`, `lid_me`, `status_me`, `temp`).
- **Not yet confirmed** and needed by P1–P3: the text column of `message`, `chat.subject`, the
  columns of `lid_display_name`, and `message_media`'s. Phase 0 confirms them by schema check
  (names only).

## 10. Test vectors — `tests/fixtures/whatsapp_backup/`

Produced 2026-10-26 by **running** the reference's encryptor on a synthetic SQLite database (made-up
numbers, generated text, a "Synthetic test group") — **no real data**. A few were then built by
editing the reference's output as this description says (removing the trailer, removing the marker
byte, flipping one byte, truncating). `expected.json` holds two **throwaway test keys** (A, B), and
for each file either `{"ok": true, "sha256": …, "counts": …}` — the SHA-256 of the exact database the
file must decrypt to, and its row counts — or `{"ok": false, "error": …}`, using the error names in
§§ 6–7. Every entry was checked against the reference before handing over: the six "handle" files
decrypt to the stated hash; the eight refusals fail.

| File | Expect |
|---|---|
| `v01_standard` | ok |
| `v02_standard_large` (≈200 KB, crosses many stream buffers) | ok |
| `v03_uncompressed` | ok |
| `v04_no_trailer` | ok |
| `v05_older_header` | ok |
| `v06_no_feature_flag_byte` | ok |
| `v01_standard` with key B | `wrong_key` |
| `r01_tag_flipped`, `r02_ciphertext_flipped`, `r03_md5_trailer_flipped` | `integrity` |
| `r04_truncated_half` | `truncated` (or `integrity`) |
| `r05_crypt14` | `crypt14_end_to_end_off` |
| `r06_unknown_format` | `unknown_format` |
| `r07_zip_payload` | `not_a_message_database` |

**Acceptance beyond the vectors:** on Mike's phone, his real backup decrypts and reproduces the
2026-10-26 counts — 50,316 messages, 4,603 chats, oldest message 2017-10-23 — allowing for messages
added since.

## 11. The clean-room record

- **Session 1 (this one, 2026-10-26):** read the reference's source; wrote this file and the vectors;
  installed the reference only in this session's temporary scratch directory under `/private/tmp`,
  outside the repo. **Confirmed at hand-over:** the reference is not installed in the project's
  `.venv` (`pip show` finds nothing) and no file in the repo imports it. **Removing the scratch copy
  was not approved in-session** and is left to Mike (or the OS's temporary-file cleanup); it is
  outside the repo either way. Its transcript is in `archive/transcripts/`.
- **Session 2 (Phase 0b):** a fresh session given **only** this file, the vectors, and the plan.
  Before writing anything it confirms the reference is absent (`pip show wa-crypt-tools` fails in the
  project environment, and no copy exists in the repo), and its prompt forbids reading, installing or
  fetching it. Its transcript, its prompt and its coverage results complete the record (L1).
- **Afterwards:** session 1 may run the vectors against session 2's reader as a black box —
  behaviour, never code.
