Model: Opus 5.5, high. Plan and build run in Opus (`docs/WORKFLOW.md`); the plan gets a Fable review before any code, and the diff gets one before commit. Nothing here is Red, so the build may be delegated; the plan may not skip Mike.

# WhatsApp Phase 2: the phone posts messages to the VM (clean-room session)

**What this session is for.**
- After Phase 2, a user's shared WhatsApp chats reach Metatron: live as messages arrive, and again each night from the backup. Nothing reaches the VM today — the VM side (Phase 1) is deployed with the channel off.
- Phase 2 is the Metatron app's native side: P1–P5 of the input plan, the "During" items the reader review ruled in, and the "this should have come up" action Mike ruled in on 11-23.
- It is the largest phase (plan § 6: 4–7M tokens, plus about 0.5–0.9M for the review items). **Plan first, show Mike the plan and the todo list, and build only on his go-ahead.**

## ⛔ Rules that bind this session

1. **Clean room:**
   - Open nothing in `archive/transcripts/`.
   - In `archive/log/` and `archive/PROJECT_LOG.md`, read only the WhatsApp entry `2026-10-30-02-…` and fragments whose first heading says **"clean-room"**.
   - Look at nothing under `/private/tmp` outside your scratchpad.
   - **Use no outside crypt implementation or reference WhatsApp reader, no web, and no field meaning taken from memory of any published schema.**
   - This session's log fragment is titled "clean-room". Never put the other phrase in a clean-room fragment's first heading: the write-time briefing fails closed.
2. **No message text, contact name or phone number may enter this conversation.** The probe reports counts and shapes only. Planted values in tests are fine.
3. **No real person's details in code, comments or config** (CLAUDE.md § Data Privacy Tiers). Tests may use made-up values.
4. **Tiers:** `config/agents/*.md` and `core/scheduler.py` are Red; `config/personas/mike/**` and `./deploy.sh` are Denied. None is expected. If the VM needs a change (see "VM changes" below), it is ordinary `core/`/`tools/` work with tests, and Mike deploys.
5. **Two windows share this tree.** `git diff` every file before staging it; read `git diff --cached --stat` before committing; stage only this session's files.
6. **Mike's phone runs only the `waprobe` build.** Whether Phase 2 ships in the ordinary build, and how his phone moves to it, is a decision for the plan (below).

## Read first

1. **`SESSION.md`**: the WhatsApp paragraph. **`ROADMAP.md`**: § Section 0.
2. **The input plan** `archive/plans/whatsapp_input_plan_2026-10-26.md`: § 3 *Phone* (P1–P6), § 4 (every note from "P3 BUILT" on, including the 11-23 rulings and the reader-review note), § 6 *Unseen*, § 7.
3. **The contract** `archive/plans/whatsapp_phase1_build_plan_2026-11-23.md` § 2.1 (the device token and `/device/*`) and § 2.2 (the endpoint schema, the message key, the clash rule).
4. **The reader review** `archive/plans/whatsapp_phone_reader_review_2026-11-23_fable-5-2.md` — all of it. § 2 is what not to re-review; § 4 is Mike's rulings; § 5 is what the reader does now.
5. **The format description** `archive/plans/whatsapp_backup_format_2026-10-26.md` §§ 1, 12.
6. **The code:** `android/app/src/main/java/com/mike/metatron/` (the app as it is, and `whatsapp/`, the reader); `src/waprobe/…/whatsapp/` for how the probe drives the reader, stores the key (`ProbeKeyVault`) and listens (`ProbeListener`); `core/` and `tools/intake_whatsapp.py` for the endpoints Phase 1 built.

## What Phase 2 builds

**From the plan:** P1 the share list; P2 the live feed (a notification listener that drops unshared chats on the phone and never sends an event without a chat id); P3 the nightly job (WorkManager, after WhatsApp's backup); P4 the key screen (native, Keystore-wrapped); P5 native HTTPS and the scoped device token, with a "needs re-pairing" notice when it is refused.

**From the reader review, as ruled (review § 4) — each is a requirement, with its test:**

1. **One owner for the nightly read (finding 1, finding 11).** A main-source entry point that locates the set, checks it is complete, decrypts, runs the schema check, reads, combines, deletes the decrypted copy in `finally`, and destroys the key. It works in a private folder under `no_backup` and **sweeps the whole folder** at process start and at the start of each run, under the same one-run-at-a-time lock the job uses. Never sweep from a screen. Test: a run killed after decrypt leaves an empty folder at the next start.
2. **Read from the cursor minus an overlap, and remember what was sent (finding 2).** The job reads from about 8 days before the VM's cursor. The phone keeps, per message key it has sent from either path, a salted hash of the text — pruned by age to the overlap window, never the text. An unchanged copy is skipped; a changed or newly filled one goes as an `update`. This replaces the 72-hour list's text-length compare. State the standing cost in the plan: size, what prunes it, what deletes it, which meter reports it.
3. **Say when WhatsApp has stopped backing up (finding 3).** Post `IncrementSet.newestWriteMs()` with each run; raise a notice when it is older than about 36–48 hours. The signal is when WhatsApp wrote the file, never when the job last ran.
4. **Say when the text has gone (finding 4).** Post the night's counts (received rows read, how many had text, per source; `withoutKeyId`, `withoutChat`, `textUndecodable`, `baseKeyCollisions`, deletions listed). A run with 20 or more received rows and none with text is raised as a format change.
5. **Reply markers only from real sent messages (finding 6).** Read `message_type` in the full-backup path and add it to the schema check. **(M) One probe tap first:** which from-me types exist, with counts, and whether increments carry a type. Decide the allowed types from that count, with Mike.
6. **Show a refusal to the user (finding 9), by code, never by message (finding 13).** Every `BackupError` the job meets is reported as `error.code` plus the code-written `userText` — never `getMessage()`. `being_written`, `no_backup_found` and an `IOException` mean "retry later", not a fault.
7. **What the reader still lacks (finding 11):** a public way to canonicalise ids; the chat list, group subjects and `lid_display_name` for the share list, folded through the increments; a report of hidden ids that gained a link tonight, driving the share-list migration and the contract's `merges`; the schema check inside the read; `chat._id` on the required list.
8. **Tests the review found missing (finding 16):** `FullBackupMessages` on a real SQLite (on-device or Robolectric); `deleteDecrypted` and the side files; a write failure mid-decrypt.

**The "this should have come up" action** (Mike, 11-23: "Build it in"; input plan § 4, the M2 note): the only measure of misses now M2 is dropped. About 0.3–0.5M tokens.

**The ordinal is the reader's now.** `WaMessage.ordinal` is assigned in `BackupCombiner.combine` (received and from-me rows numbered separately, per canonical chat per whole second, by row id). The live path must number the same way: received messages only, by arrival order within the second. The reader's since-time is whole seconds.

## Decisions the plan must put to Mike — options, trade-off, a recommendation, then ask

1. **Which build carries Phase 2**, and how Mike's phone and Iva's future install differ (the listener and All-files access must not reach a user who has not consented).
2. **The overlap length** (finding 2) and the stale-backup threshold (finding 3).
3. **Where the two notices appear** — a native notification, the app, or both.
4. **Any VM change.** The § 2.2 contract has no field for a run's counts or the backup's write time. Either extend `/device/whatsapp/events` (a VM change, a deploy) or keep the checks on the phone. Name the cost of each.
5. **Reply-marker types**, after the probe count.

## Step 0 — the real-data test of the 11-23 reader changes (a gate: nothing else is built before it passes)

The seven reader changes of 11-23 (review § 5, commit `e2aa904`) have passed their unit tests but have met synthetic files only. Run this as a short walkthrough with Mike at the start of the session (about 15 minutes, two taps).

1. **Before building, confirm the baseline:** `cd android && ./gradlew --offline testDebugUnitTest testWaprobeUnitTest` — 42 and 87 tests, 0 failures.
2. **Add the message-type count to the probe first** (finding 6; `src/waprobe/` only): per `message_type`, how many rows are from-me and how many of those carry text, and whether an increment's messages carry any type. Counts only. This saves a second build and a second install.
3. **Rebuild and serve the probe** (`docs/INFRASTRUCTURE.md` § APK; check the APK hash before serving). Mike installs it. Installing the ordinary debug build over the probe revokes All-files access — it must be the `waprobe` build.
4. **(M) Mike taps button 7, "Read the set (P3 proof)"**, and reads the report back. Counts and refusal codes only — no message content enters the conversation.
   - **Pass:** "every increment decoded: yes" (9 of 9 on 11-23; the number moves as sets rotate); each set's "window to the last increment" line still matches the newest full backup as it did on 11-23 (547 and 362 then); "decrypted copies deleted: yes".
   - **Fail:** any `REFUSED` line. `increment_missing_part` naming a `jid` or `jid_map` row or key points at the 11-23 checks (finding 8) being stricter than real files — read which, loosen only that check, and record it in the review file § 5. `crypt14_end_to_end_off` means a crypt14 file newer than the backup sits in the folder (finding 3) — report it to Mike, do not work round it. `unknown_format` or `increment_format_unknown` on a file that decoded on 11-23 is a fault in finding 7's change.
   - **Also read:** the combine now orders by whole second then row id, so any count that differs from 11-23 by more than new messages is a finding, not noise.
5. **(M) Mike taps the message-type count** and reads it back. It settles decision 5 below.
6. **Record the result** in the review file § 5 and the input plan § 4 before going on. If step 4 fails and the fix is not a one-line loosening, stop and bring it to Mike.

## Output

1. **A plan** `archive/plans/whatsapp_phase2_build_plan_{date}.md`: what the user gets, the design per item, files and tiers, tests, the five decisions, a todo list in build order, and a cost section covering build, run, ancillary and unseen costs. Run `/adversarial-review` on it (Fable) and address the findings before showing Mike.
2. **On Mike's go-ahead, the build**, with a Fable diff review before commit.
3. **Close out:** a log fragment titled "clean-room"; the input plan § 4 note; `/archive`. Commit and push only this session's files. Nothing deploys from this session; an APK sideload and any VM deploy are Mike's (M5).

**Not this session:** Phase 3 (alerts, P6, the red-team rows), M4 (switching the channel on for `mike`), Iva's switch-on (M7).

**Next, after Phase 2:** M4 as a guided session with Mike, then Phase 3.

## Budget

- **Build:** about 5–8M Opus 5.5 tokens across plan, build and tests; about 0.5–1M Fable 5.2 for the plan and diff reviews. If the plan shows it will not fit one session, split at the plan's own seam (P4–P5 and the nightly job first; the live feed and share list second) and say so before starting.
- **Mike:** about 15 minutes for the two probe taps, 20–30 for the plan's decisions, then a sideload.
- **Run:** $0 on the phone. The VM's run cost is unchanged from Phase 1 until M4 switches the channel on.
- **Persistent state:** the sent-hash list, the share list, the wrapped key and the device token on the phone — each with its unit, what deletes it and its meter stated in the plan.
