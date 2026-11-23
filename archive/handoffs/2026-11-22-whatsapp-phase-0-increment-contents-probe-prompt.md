Model: Opus 5.5 — a small clean-room probe change; it must never read a crypt implementation (W9).

# WhatsApp Phase 0 — what is inside a nightly increment (clean-room probe revision)

**Read first:** `archive/handoffs/2026-10-31-whatsapp-phase-0-close-survival-lm-increments-prompt.md`
— its clean-room rules 1–4 bind this session in full (no reference implementation, no
`archive/transcripts/`, WhatsApp log entries only `2026-10-30-02-…` and fragments titled
"clean-room", nothing under `/private/tmp` outside your own scratchpad). Then the plan's ruling:
`archive/plans/whatsapp_input_plan_2026-10-26.md` § 4, the **INCREMENTS RULED** block (Mike,
2026-11-22: read the increments, clean-room). The hook fence is already in
`scripts/hook_context_gate.py`.

## What the probe showed on 11-22 (shapes only)

- Full backups arrive about every 6 days (11-05, 11-11, 11-17, 02:00); a small increment each night.
- **Live increments carry no date:** `msgstore-increment-N.db.crypt15`. The dated
  `msgstore-increment-N-YYYY-MM-DD.1.db.crypt15` form appears only once the next full backup rotates
  the set. `ProbeLines.INCREMENT` matches only the dated form, so button 5 tested a rotated 11-16
  file and never last night's.
- On that file the reader passed the key and container and refused the payload as
  `not_a_message_database` — `BackupDecryptor.Sink`: either the payload begins `PK\x03\x04` (ZIP,
  in `decide()`), or it inflated and the tag passed but the output is not SQLite (`finish()`).
  The report cannot say which.

## The change — `src/waprobe/` only; the reader's accept/refuse behaviour unchanged

1. **Pick both name forms.** `ProbeLines.INCREMENT` accepts `msgstore-increment-N.db.crypt15` and
   the dated form; newest by modification time, as now. Report the chosen name and how many of each
   form exist. (If a full backup ran overnight, today's newest may be a dated one — fine.)
2. **Say which refusal, and what is inside.** For the chosen increment report: the refusal branch
   (ZIP payload vs inflated-not-SQLite); the payload's first 8 bytes in hex (format magic only);
   **if ZIP** — each entry's name, uncompressed size, and whether it begins with the SQLite header,
   and for a SQLite entry the existing shape report (tables, row counts for `message`/`chat`/`jid`,
   min/max message timestamp, ids also in the newest full backup, ids newer than it); **if inflated
   non-SQLite** — the decompressed size and the first 16 bytes in hex. Open a ZIP with
   `java.util.zip` — a standard format, no reference needed. No text, no identifiers; delete every
   decrypted or extracted copy before returning, as the existing button does.
3. **How the probe gets the bytes is your call,** under one constraint: `src/main/` behaviour does
   not change. If seeing the branch needs a hook in `BackupDecryptor`, keep it package-private and
   behaviour-neutral, and say so in your report. Then
   `./gradlew :app:testDebugUnitTest --tests 'com.mike.metatron.whatsapp.*'` — **19 must still pass**.
4. **Tests:** the filename match for both forms, in `src/testWaprobe/`
   (`./gradlew :app:testWaprobeUnitTest --tests 'com.mike.metatron.whatsapp.*'`), never `src/test/`.
5. `./gradlew assembleWaprobe` (`JAVA_HOME` = Homebrew openjdk@21); tell Mike the APK path. The
   walkthrough session serves it and reads the report.

**Nothing is committed, pushed or deployed.** Close with `/archive`; the log fragment's title says
**"clean-room"**.

**Budget:** ~0.1–0.2M Opus tokens; Mike: one install and one tap (walkthrough session). Run cost:
none — throwaway probe.
