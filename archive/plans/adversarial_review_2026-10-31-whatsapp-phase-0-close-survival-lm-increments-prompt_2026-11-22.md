Plan reviewed: `archive/handoffs/2026-10-31-whatsapp-phase-0-close-survival-lm-increments-prompt.md`
Model: Fable · Effort: medium · Date: 2026-11-22

## STRUCTURAL

1. [§ "Do these first" item 2, Increments option (a); § "Then — what is left of the build"] [/Users/md-homefolder/Desktop/multi-model-mcp/archive/plans/whatsapp_backup_format_2026-10-26.md § 7 Variants, § 3 "No-trailer form"; /Users/md-homefolder/Desktop/multi-model-mcp/android/app/src/main/java/com/mike/metatron/whatsapp/BackupLocator.java:DATED]
Wrong: Option (a) assumes a session that reads the reference can describe the increment files and "how an increment relates to the full backup", but nothing in the repo shows the reference covers increments at all — the format description, which was held to listing every variant the reference handles, has no increment row.
Fails: The reference is a container decryptor, so what an increment contains and how it combines with a full backup is database behaviour its source may not hold, and the 0a′ session has no other source (web access denied, real increment files exist only on the phone, and the probe can only open what `BackupLocator.newest` selects).
Costs: Mike rules for (a) on an option that may not exist, ~1–1.5M tokens and the reader extension are queued ahead of Phase 1 behind a session that can return nothing, and the fallback is then option (b) by default rather than by ruling — medium.

## LOCAL

2. [§ "Clean-room rules" 1–3; § item 2 "(this one may do it later only if it never reads the reference)"] [/Users/md-homefolder/Desktop/multi-model-mcp/archive/plans/whatsapp_backup_format_2026-10-26.md § 11; /Users/md-homefolder/Desktop/multi-model-mcp/SESSION.md "Mike owes: delete the `/private/tmp` reference copy"]
Wrong: The clean-room rules fence off only the transcripts dated 2026-10-26, while the plan creates a second reference-reading session (0a′) whose transcript will carry a later date, and it drops the still-open obligation to delete the reference copy left under `/private/tmp`.
Fails: A session that follows rules 1–3 to the letter can still open 0a′'s transcript or log entry, or meet the scratch copy, and then write the increment reader that the plan explicitly lets it build.
Costs: The clean-room record (legal check L1) for an APK about to be handed to a second person is broken in a way that cannot be undone after the code is written — speculative.

3. [§ item 2, Increments option (b) "accepting ~a week's lag"] [/Users/md-homefolder/Desktop/multi-model-mcp/archive/plans/whatsapp_input_plan_2026-10-26.md § 3 P2 "72-hour list", V6, § 6 "The 72-hour sent-key list"; /Users/md-homefolder/Desktop/multi-model-mcp/android/app/src/waprobe/java/com/mike/metatron/whatsapp/ProbeStore.java:KEEP_MS]
Wrong: Option (b) is put to Mike as a week's delay, but the design it would run on pairs a live message with its backup copy through a list that keeps keys for only 72 hours, and the "~weekly" cadence itself rests on a single unforced full backup (10-22).
Fails: A backup copy arriving after its key has aged out is no longer sent as an update and the VM's `seen` set drops it as a duplicate, so group messages (which carry no sender live) never get one, edits never apply, and answered questions re-surface because reply markers arrive only with the backup.
Costs: The ruling is taken on a mispriced alternative, and if (a) falls through the build inherits permanent loss rather than lag for most group traffic — medium.

4. [§ item 1 "Pass" / "Fail"] [/Users/md-homefolder/Desktop/multi-model-mcp/android/app/src/waprobe/java/com/mike/metatron/whatsapp/ProbeListener.java:onListenerDisconnected; /Users/md-homefolder/Desktop/multi-model-mcp/android/app/src/waprobe/java/com/mike/metatron/whatsapp/ProbeReport.java:survival; /Users/md-homefolder/Desktop/multi-model-mcp/android/app/build.gradle:waprobe (same app ID)]
Wrong: The survival pass criteria cannot fail on the evidence the report holds, because a silent overnight hour reads the same whether no message arrived or the listener was dead.
Fails: A process killed by the battery manager writes no "disconnected" mark, the probe shares its app ID and process with Metatron so ordinary use or a day-planner push revives it before the read, and "despite messages" depends on Mike reconstructing by hand which unmuted chats received messages while the screen was off.
Costs: The real-time notification (W5/P6) is approved and built in Phase 3 on a pass that measured nothing, and the gap surfaces only in Phase 4 as missed alerts — medium.

## VERIFY — 2026-11-22 (round 1, same reviewer; revision claimed to close 1–4)

1. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/android/app/src/waprobe/java/com/mike/metatron/whatsapp/ProbeBackup.java:run → `BackupDecryptor.decrypt(f, key, out, …)`] the decrypt path takes any `File`, so the new item 2 can try an increment on the phone without touching `BackupLocator.newest`, the ruling is now sequenced after that result, and the narrowed 0a′ stops on "does the reference handle increments at all".

2. NEW SHAPE — [/Users/md-homefolder/Desktop/multi-model-mcp/archive/handoffs/2026-10-31-whatsapp-phase-0-close-survival-lm-increments-prompt.md rule 2; /Users/md-homefolder/Desktop/multi-model-mcp/archive/PROJECT_LOG.md] the widened fence identifies a reference-reading session by its fragment title, but transcript filenames are derived by the archive script rather than chosen (the plan's own example, `2026-10-26 — pasted_content id=7fdd Model Opus 5.5 — a build session.md`, names no topic), so a transcript cannot be classified without opening it, and `archive/PROJECT_LOG.md` — generated from those same fragments — is not fenced at all; the `/private/tmp` half is closed by step 0 and rule 4.

3. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/archive/plans/whatsapp_input_plan_2026-10-26.md § 3 P2, § 6 "The 72-hour sent-key list"] option (b) now states the loss the 72-hour pairing list produces (no group sender, no edit updates, answered questions re-surfacing) and marks the full-backup cadence as one sample, which matches the design it would run on.

4. NEW SHAPE — [/Users/md-homefolder/Desktop/multi-model-mcp/android/app/src/waprobe/java/com/mike/metatron/whatsapp/ProbeReport.java:survival, :listener] the planted-message test can now fail in principle, but its pass line ("an event for that chat whose post time is within ~2 minutes") cannot be read off the report as built: it prints only first/last event, longest gap, 48 hourly buckets and masked ID formats, with no per-event or per-chat times, so the only usable evidence is the `last event` line if nothing else arrives first; the one probe change that would show delivery time directly is conditional and is built in item 2, after item 1 has already run, and `post` is `sbn.getPostTime()` (`ProbeStore.record`), which is when WhatsApp posted, not when the listener received.

## NEW

none

## VERIFY — 2026-11-22 (round 2; revision claimed to close the two NEW SHAPE verdicts, 2 and 4)

2. NEW SHAPE — [/Users/md-homefolder/Desktop/multi-model-mcp/scripts/hook_context_gate.py:_log_hits, HISTORY_HEADER] the allowlist now covers everything the session opens itself (transcripts, fragments, `PROJECT_LOG.md`) and rule 4 no longer collides with the scratchpad, but the write-time hook pushes `archive/log/` excerpts for any file being edited without the session opening anything: recording the LM ruling in `/Users/md-homefolder/Desktop/multi-model-mcp/archive/plans/whatsapp_input_plan_2026-10-26.md` will be briefed with session 1's closed fragment `2026-10-26-04-whatsapp-input-explored-planned-phase-0a.md`, which names that file, and a later clean build session editing the reader would be briefed the same way with any 0a′ fragment.

4. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/android/app/src/waprobe/java/com/mike/metatron/whatsapp/ProbeListener.java:onNotificationPosted; /Users/md-homefolder/Desktop/multi-model-mcp/android/app/src/waprobe/java/com/mike/metatron/whatsapp/ProbeStore.java:record, toJson, fromJson, Event.{post,group,style,summary}] the probe update is now item 1, ahead of the survival test, every field the new per-event line needs exists or is a one-line addition at the named symbols, and the pass line reads receipt time (`rx`) against the noted send time, so a dead or late listener now fails visibly; the masked chat id will be identical for every one-to-one chat (`ProbeMask.format`), which the pass line already allows for by matching on type and time.

## NEW

1. [§ item 1 "Unit-test what can be tested on the Mac (the report's line format, `rx` round-trip, the increment filename match)"; § "State of the code" test command] [/Users/md-homefolder/Desktop/multi-model-mcp/android/app/build.gradle:buildTypes.waprobe; /Users/md-homefolder/Desktop/multi-model-mcp/android/app/src/waprobe/java/com/mike/metatron/whatsapp/ProbeStore.java:toJson; /Users/md-homefolder/Desktop/multi-model-mcp/android/app/src/test/java/com/mike/metatron/whatsapp/MiniJson.java; /Users/md-homefolder/Desktop/multi-model-mcp/.gitignore:128-135]
Wrong: The new unit tests target classes that exist only in the `waprobe` source set and serialise through Android's `org.json`, while the plan's only test command is `testDebugUnitTest` and the only admitted test folder is `src/test/`.
Fails: A test in `src/test/` that references `ProbeStore` or `ProbeReport` does not compile for the debug variant, which takes the existing 19 reader tests down with it, and `org.json` is a throwing stub on the JVM (the reason the existing tests carry their own `MiniJson`), so the `rx` round-trip cannot run as written; a `src/testWaprobe/` folder would avoid the first problem but is ignored by `.gitignore`.
Costs: The session either breaks the reader's test run that serves as the clean-room coverage evidence, or ships the probe change untested and learns the report is wrong only after Mike's overnight test — medium.

## VERIFY — 2026-11-22 (round 3; revision claimed to close 2 and round-2 NEW 1)

2. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/scripts/hook_context_gate.py:_log_hits (sole caller at line 461; hook runs as a fresh process per `Write|Edit` per /Users/md-homefolder/Desktop/multi-model-mcp/.claude/settings.json)] `_log_hits` is the only path that pushes `archive/log/` text into a session, the fence takes effect on the very next edit, and the one edit made before it exists is clean because session 1's fragment `2026-10-26-04-whatsapp-input-explored-planned-phase-0a.md` names neither the hook file nor `.gitignore`.

NEW 1. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/android/app/build.gradle:buildTypes.waprobe; /Users/md-homefolder/Desktop/multi-model-mcp/.gitignore:113-135] a `waprobe` build type gives a `src/testWaprobe/` unit-test source set and a `testWaprobeUnitTest` task that also compiles `src/test/`, the debug variant never sees the probe tests so the 19 reader tests are untouched, the folder needs exactly the one `.gitignore` admission the plan names (nothing exists there yet), and the `org.json` round-trip is moved to a phone check that runs before the overnight test.

## NEW

1. [§ item 1, first bullet "Change `_log_hits` to skip any fragment (and any `_history.md` section) that mentions WhatsApp unless…"] [/Users/md-homefolder/Desktop/multi-model-mcp/scripts/hook_context_gate.py:_log_hits; /Users/md-homefolder/Desktop/multi-model-mcp/archive/log/2026-11-11-01-review-fixes-high-and-medium.md:13; also `2026-11-05-01-whole-codebase-review-run-and-verified.md`, `2026-11-04-01-whole-codebase-review-prompt.md`, `2026-10-26-06-over-and-out-no-longer-drops-requests.md`]
Wrong: The fence is a permanent change to a hook every session in every area runs, and it drops a whole fragment on any mention of WhatsApp, without listing which existing fragments that removes.
Fails: Four fragments that have nothing to do with the reader mention WhatsApp once in passing (the 11-11 one only to say an APK rebuild went through the uncommitted WhatsApp tree), so their decision history — including the whole-codebase review and its High/Medium fixes across `core/` and `tools/` — stops appearing in the edit-time briefing for every file and every future session, and any later close-out that names WhatsApp in passing disappears the same way.
Costs: The mechanism that stops sessions re-making decided or reverted changes goes quiet for the project's most heavily ruled files, silently and with no end date, to protect one feature's clean room — high.

## VERIFY — 2026-11-22 (round 4; revision claimed to close round-3 NEW 1)

NEW 1 (round 3). CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/scripts/hook_context_gate.py:_log_hits; /Users/md-homefolder/Desktop/multi-model-mcp/archive/log/2026-10-26-04-whatsapp-input-explored-planned-phase-0a.md] the fence is now keyed on one filename plus a first-heading marker, so the four passing-mention fragments (11-04, 11-05, 11-11, 10-26-06) stay in every briefing; `2026-10-26-04` is the only existing fragment a clean session must not be briefed with — of the six fragments that mention WhatsApp it is the sole reference-reading one, `2026-10-30-02` is the clean session's own, the 11-04 fragment's single hit only names the reader and clean room as out of the review's scope, `_history.md` is frozen at 2026-08-13 and earlier (`scripts/build_project_log.py:HISTORY`) so it holds no WhatsApp section and never will, and every fragment opens with its `### ` heading on line 1, which is what the heading check reads.

## NEW

none
