Model: Fable 5.2. This is review work, which runs in Fable (`docs/WORKFLOW.md`), and the judgement is the work, so nothing is delegated. Read-only, apart from the review file and the log fragment.

# WhatsApp phone reader: Fable review before Phase 2 (clean-room session)

**What this session is for.**
- Phase 2 puts the phone reader into the Metatron app. That reader is `android/app/src/main/java/com/mike/metatron/whatsapp/`, 15 files.
- In Phase 2, a nightly job on the user's phone reads their WhatsApp backup and posts messages to the VM, unattended.
- Until now only the probe has run this code, with Mike watching.
- The plan makes this review the gate before Phase 2 (`archive/plans/whatsapp_input_plan_2026-10-26.md` § 4, the "P3 BUILT" note): *"Before Phase 2 wires the reader into the app: a Fable review of `src/main/…/whatsapp/` (~0.2M)"*.

**The question:** what would break, leak or lose a message once this runs unattended on a real phone? The output is findings for Mike to rule on, not fixes.

## ⛔ Rules that bind this session

1. **Clean room:**
   - Open nothing in `archive/transcripts/`.
   - In `archive/log/` and `archive/PROJECT_LOG.md`, read only the WhatsApp entry `2026-10-30-02-…` and fragments whose first heading says **"clean-room"**.
   - Look at nothing under `/private/tmp` outside your scratchpad.
   - **Use no outside crypt implementation or reference WhatsApp reader, and no web.** The project's own `src/main/…/whatsapp/` code is the thing being reviewed.
   - This session's log fragment is titled "clean-room". Never put the other phrase in a clean-room fragment's first heading: the write-time briefing fails closed.
2. **No message text, contact name or phone number may enter this conversation.**
   - No backup lives on this Mac, and the probe is not run in this session.
   - Planted values in the tests are fine.
3. **No code edits.**
   - `src/main/…/whatsapp/` is reviewed, not changed. Fixes are ruled by Mike and then built in an Opus session.
   - `config/agents/*.md` and `core/scheduler.py` are Red, and `config/personas/mike/**` and `./deploy.sh` are Denied. None is expected.
4. **Two windows share this tree.** `git diff` every file before staging it, and stage only this session's files.

## Read first

1. **`SESSION.md`**: the WhatsApp paragraph. **`ROADMAP.md`**: § Section 0.
2. **The input plan** `archive/plans/whatsapp_input_plan_2026-10-26.md`:
   - § 3 *Phone*, P1–P5: what Phase 2 builds on top of the reader;
   - § 4, the Phase 1 and Phase 2 notes, including Mike's 11-23 rulings. Deletions are counted, never applied. M2 is dropped and real use is the baseline. A "this should have come up" action is built into Phase 2.
3. **The Phase 1 delta** `archive/plans/whatsapp_phase1_build_plan_2026-11-23.md` § 2.2. This is the contract the phone must meet:
   - time in whole **seconds**, with the VM refusing a millisecond value;
   - `ordinal` assigned by row id from a backup;
   - canonical chat ids;
   - `sender` only for groups;
   - the same-second clash rule.
4. **The format description** `archive/plans/whatsapp_backup_format_2026-10-26.md`: § 1 (write checks) and § 12 (increments).
5. **The code:**
   - all 15 files in `src/main/…/whatsapp/`;
   - the tests `src/test/…/whatsapp/` (`BackupReaderTest`, `IncrementReaderTest`, `GcmTest`, `MiniJson`);
   - how the probe calls the reader: `src/waprobe/…/ProbeProofRun.java` and `ProbeM2Run.java`.

## What to look for, ranked by what unattended running costs

1. **Plaintext left on disk.** Check every path that decrypts:
   - is the copy deleted on every exit, exception and crash;
   - does a crash sweep exist;
   - SQLite side files (`-journal`, `-wal`, `-shm`);
   - temporary inflate or ZIP output.
2. **Text reaching a log, an exception message or a `toString`.**
3. **Refusals: named, never a silent partial read.** Cover:
   - an increment gap;
   - a file still being written;
   - a schema change after a WhatsApp update;
   - a wrong key;
   - a crypt14 file;
   - a missing `jid_map`;
   - a truncated file.
4. **A message lost or doubled against the § 2.2 key:**
   - flooring milliseconds to seconds;
   - an ordinal that stays the same between the live and backup paths;
   - `@lid` → phone-number canonicalisation, including `jid_map` rows that arrive in an increment;
   - the combine replacing by (chat, from-me, key_id);
   - deletions counted, not applied;
   - the since-time boundary.
5. **Resources on a phone:**
   - whole-file reads into memory;
   - backup sizes against the phone's free memory and storage;
   - behaviour when storage is short;
   - anything that assumes the probe's foreground, user-watched run.
6. **Tests.** What is asserted versus only exercised, and any missing test for a failure Phase 2 depends on.
7. **Phase 2 readiness.** Does the reader give everything the nightly job needs, as a public API rather than a probe-only path? (For example, `canonicalise` is package-private.) Is anything Phase 2 needs missing?

## Output

1. **`archive/plans/whatsapp_phone_reader_review_2026-11-24_fable-5-2.md`.** Use the real date if it differs. It holds:
   - **findings ranked by severity**, each with `file:line`, what a user would notice, a concrete failure scenario, and a fix direction (not a patch);
   - a short **"checked and fine"** list, so a later session does not re-review it.
2. **Put the findings to Mike in chat**, numbered, with a recommendation per finding: fix before Phase 2, fix during Phase 2, or accept. **He rules; record the rulings in the review file.**
3. **Close out:**
   - a log fragment titled "clean-room";
   - the input plan § 4: one line saying the review is done, with its count;
   - `/archive`.
   - Commit and push only this session's files.

**Not this session:** fixing anything, Phase 2 itself, M4.

**Next, after Mike's rulings:** the Phase 2 build prompt (Opus 5.5, high). It covers P1–P5, the fixes Mike rules in, and the "this should have come up" action.

## Budget

- **Build:** about 0.2–0.3M Fable 5.2 tokens (the plan says ~0.2M; 15 files plus tests).
- **Mike:** about 10–15 minutes to rule on the findings.
- **Run:** $0. Nothing is deployed and nothing runs.
- **Persistent state:** none. The review file is a document.
