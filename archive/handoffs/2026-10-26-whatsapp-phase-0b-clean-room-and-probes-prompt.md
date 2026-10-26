Model: Opus 5.5 — a build session. It must be a FRESH session: its independence from the session that read the GPL source is the whole point of a clean room, not a matter of capability.

# WhatsApp input — Phase 0b (clean-room decrypt) and the Phase 0 phone probes

You are **clean-room session 2** for the WhatsApp input plan. Mike approved the plan on 2026-10-26
("Proceed with Stage 0"). Phase 0a is done: a separate session read the GPLv3+ reference tool and
wrote a facts-only description of WhatsApp's backup format, plus test files. **Your job is to write
our own reader from that description alone, prove it against the test files, then build the
throwaway probe app that answers Phase 0's questions on Mike's phone, and walk Mike through it.**

## ⛔ Clean-room rules — these come before everything else

1. **Do not read, install, download, search for or ask about the source of `wa-crypt-tools`**, or any
   other crypt12/14/15 implementation (GitHub, PyPI, blog code, other repos). Web access is denied in
   this project anyway; do not ask Mike to lift it for this.
2. **Do not open anything in `archive/transcripts/` dated 2026-10-26.** Those transcripts contain the
   reference source that session 1 read. The `archive/log/` fragment and `archive/PROJECT_LOG.md`
   entry for that session hold no code and are safe to read.
3. **Before writing any code, confirm and report:** `.venv/bin/pip show wa-crypt-tools` finds
   nothing, and `grep -rl "wa_crypt_tools" .` (excluding `.venv/`) finds nothing in the repo.
4. Your sources are **only**: `archive/plans/whatsapp_backup_format_2026-10-26.md` (the format),
   `tests/fixtures/whatsapp_backup/` (test files + `expected.json`), and the plan
   `archive/plans/whatsapp_input_plan_2026-10-26.md`. Published standards are fine to rely on from
   your own knowledge (AES-GCM, HKDF/RFC 5869, zlib/RFC 1950, protobuf wire format, SQLite's
   header).
5. If the description is ambiguous, **do not guess from memory of any implementation** — note it,
   make the conservative choice (refuse), and list it in your report.

## Read first

1. Run `/metatron-code`.
2. The plan: § 3 P1–P5 (phone side), § 4 Phases 0a/0b/0 and the exit criteria, § 6 costs, § 7 M1,
   § 8 risks, § 8a legal check L1.
3. The format description, in full — **§ 6 is your checklist and § 8 lists the reference's
   behaviours you must not copy.**
4. `docs/INFRASTRUCTURE.md` § APK — how the app is built (Capacitor 8, hand-written Java in
   `android/app/src/main/java/com/mike/metatron/`, `./gradlew assembleDebug`, sideload).

## Build — Phase 0b (the reader)

- A Java module under `android/app/src/main/java/com/mike/metatron/whatsapp/` that reads a crypt15
  file **as a stream** and produces the SQLite database, exactly per the description: key parsing
  (§ 2), header parsing (§§ 3–4 — a minimal protobuf reader for the four fields is fine; no new
  dependency unless you justify it), HKDF, AES-256-GCM with the 16-byte nonce, MD5 trailer detection,
  zlib, the SQLite header check, write-to-temp-then-rename in `no_backup`, delete on any failure,
  free-space and being-written checks, and the named errors of §§ 6–7.
- **Never log key material, `jidSuffix`, or any decrypted content.**
- **JVM unit tests** (`android/app/src/test/`) that run **every entry in `expected.json`**: each
  "ok" file must decrypt to the stated SHA-256; each refusal must produce the named error (or an
  allowed alternative). Print a coverage table — every row of the description's § 7 against a passing
  test or a stated reason.
- Amber files only (`android/**`, `tests/**`). Nothing under `core/`, `config/` or `tools/` changes in
  this phase.

## Build — Phase 0 probes (a debug build, throwaway except the reader)

One debug screen in the app, reporting **counts and formats only — no message text, no names, no
phone numbers (mask digits as `#`)**. Nothing is sent to the VM.

1. **Key:** a native screen (never the WebView) to enter the 64-digit key; store it wrapped by the
   Android Keystore. **Before storing it, make sure Android's auto-backup cannot copy it** — the
   manifest has `allowBackup="true"` today (plan P4): set it false or exclude the key file.
2. **Backup probe:** request All-files access; find the newest complete backup; decrypt with the
   reader; report message and chat counts, the oldest date, messages per year (history gaps), the
   decrypted size and its ratio to the encrypted size, the time taken, and the schema facts the
   description's § 9 lists as unconfirmed (**names only**).
3. **Listener probe:** a `NotificationListenerService` for `com.whatsapp`. For each notification:
   the **format** of the conversation shortcut ID and of any person key (digits masked), whether it is
   messaging-style, text length, message time — for one-to-one **and** group chats. **Does the chat ID,
   canonicalised through `jid_map`, equal the share-list key form?** (Plan P1, Phase 0 exit.)
4. **Dedup probe:** for messages seen live and then in the next backup — include one Mike edits after
   sending and one long enough to be trimmed — does the message time match? Report match counts only.
5. **Survival:** the listener still delivering after 24 hours with the screen off.
6. **For checkpoint LM:** phone model, Android version, RAM, free storage, whether AICore is present.

## With Mike — M1, a guided walkthrough (~30–45 min of his time)

Prepare the steps before you start: the APK build, sideload, the two permission grants, entering the
key, triggering a WhatsApp backup (Settings → Chats → Chat backup → Back up), reading the probe
screen. **He types the key himself; it never appears in chat.** Explain every terminal command
before asking him to run it (what it does, what the flags mean). The 24-hour survival check reads out
the next day.

## Stop conditions

- **If live notifications carry no chat ID, stop and bring it to Mike** — plan § 4 lists the two
  options; neither is pre-accepted.
- If the real backup will not decrypt with a reader that passes every vector, stop and report — do
  not work around it by consulting any implementation.

## Report, and close

1. The clean-room confirmation (rule 3), the coverage table, the probe results against the Phase 0
   exit criteria, and anything ambiguous you resolved conservatively.
2. **Raise checkpoint LM with Mike** — the tabled local-model question — with the device facts in
   hand, and put the settled ruling in front of him: correspondence is read **as code, never a model
   judgement** (`SESSION.md` § Do not re-open). Record his answer.
3. The clean-room record for legal check L1: this prompt (it is saved at
   `archive/handoffs/2026-10-26-whatsapp-phase-0b-clean-room-and-probes-prompt.md`), your
   transcript, and the coverage results — note them in your `/archive` log fragment.
4. Mike reviews and commits; you do not deploy. Close with `/archive`.

**Budget:** Phase 0b ~1–2M Opus tokens; probes ~1M; Mike ~30–45 minutes plus a one-line check the
next day.
