Model: Opus 5.5, high — this session is the lead: it briefs workers, integrates, reviews and commits. Workers run on Opus 5.5 (native Android, state across two paths, privacy edges); the two diff reviews run on Fable. Nothing here is Red, so every build chunk may be delegated.

# WhatsApp Phase 2 — build driver (clean-room, concurrent workers)

**What this session is for.** Build the plan Mike approved on 2026-11-23 — `archive/plans/whatsapp_phase2_build_plan_2026-11-23.md` — **with as much work running concurrently as the dependencies allow** (Mike: "delegated workers so it can run as much concurrent work as possible"). The lead stays light: it briefs, reviews each worker's diff, integrates, runs the tests, and commits. It stops at commit; **nothing deploys and nothing is pushed except this session's own commit** (an APK sideload and the VM deploy are Mike's, in the walkthrough).

**The plan governs.** Its § 5 holds Mike's five rulings (one APK switched on by consent; overlap 8 days, stale at 52 h or full backup > 8 days; notices both as a notification and on the screen; extend the VM; replies by photo, voice note or document count — types {0, 1, 2, 3, 4, 9}, increment rows with a content block). Its review (`archive/plans/adversarial_review_whatsapp_phase2_build_plan_2026-11-23.md`, 7 findings + 2 verify rounds, all closed) is part of the spec: every "review N" / "verify N" / "verify new N" mark in the plan is a requirement with a reason. **Do not re-open a ruling or a closed finding.**

## ⛔ Rules that bind this session and every worker (copy them into every brief verbatim)

1. **Clean room.** Open nothing in `archive/transcripts/`. In `archive/log/` and `archive/PROJECT_LOG.md`, read only `2026-10-30-02-…` and fragments whose first heading says "clean-room". Look at nothing under `/private/tmp` outside your own scratchpad, and nothing in `~/Downloads`. No web. No outside crypt implementation or reference WhatsApp reader, and **no field meaning taken from memory of any published schema** — the type set {0, 1, 2, 3, 4, 9} is from Mike's counts, not from meaning; never comment what a type number "is".
2. **No message text, contact name or phone number** enters this conversation, a worker's report, a test, a comment or a log. Tests plant made-up values and assert they never appear in any output.
3. **No real person's details in code, comments or config** (CLAUDE.md § Data Privacy Tiers). Generic names only.
4. **Tiers.** Nothing Red is expected; `core/scheduler.py` is not touched. `config/personas/mike/**` and `./deploy.sh` are Denied. Workers commit nothing, push nothing, deploy nothing.
5. **Two windows share this tree.** The lead `git diff`s every file before staging, reads `git diff --cached --stat` alone before committing, and stages only this session's files.
6. **The build is offline** (`./gradlew --offline`): **no new Gradle dependency** — WorkManager and Robolectric are deliberately not used (plan § 1). JobScheduler; the on-device self-test.
7. **Codes, never messages:** no `getMessage()` of a `BackupException` reaches a screen, notification, post or log (plan § 3.7).
8. This session's log fragment is titled "clean-room". Never put the other phrase in a clean-room fragment's first heading: the write-time briefing fails closed.

## Read first (lead only; workers get what their brief names)

1. `SESSION.md` — the WhatsApp paragraph. `ROADMAP.md` § Section 0.
2. **The plan**, all of it. Then the review file.
3. `android/app/src/main/java/com/mike/metatron/whatsapp/` (the reader), `PushStore.java`, `MainActivity.java`, `src/main/AndroidManifest.xml`, `android/app/build.gradle`; `tools/intake_whatsapp.py`, the `/device/*` and `/whatsapp/*` routes in `core/server.py`.
4. Baseline: `cd android && ./gradlew --offline testDebugUnitTest testWaprobeUnitTest` — **42 and 92 tests, 0 failures** (92 includes `ProbeTypesTest`, built 11-23); `.venv/bin/python -m pytest tests/test_intake_whatsapp.py -q` — **35 passed**.

## How the work is split — three waves, workers in parallel within a wave

**Every worker:** `Agent`, `subagent_type: general-purpose`, `model: opus`, **`isolation: "worktree"`**, background. Each brief carries: the rules above verbatim; the plan path and the exact §§ it builds; **the files it owns** (it edits no other file — if it needs one, it stops and reports); the **interface contract** below for anything another worker builds; the tests it must add and leave green; "report: files changed, tests added and their counts, anything you could not do — no message content". Launch every worker of a wave **in one message** so they run concurrently. The lead reviews each returned diff before merging it into the main tree, in the order listed, and re-runs the suites after each merge.

### The interface contract (fix it in every brief, so parallel workers agree)

- `WaMessage` gains `public final int type` (`-1` unknown) and `public final Boolean hasContent` (`null` from a full backup).
- `ReplyRule.isReply(WaMessage)`; `ReplyRule.ALLOWED = {0, 1, 2, 3, 4, 9}`.
- `SentHashes` — `Entry lookup(String key)`, `List<String> keysForText(byte[] textHash)`, `void record(String key, byte[] textHash, byte[] senderHash, long second)`, `byte[] textHash(String)`, `byte[] senderHash(String)` (empty for `""`), `void prune(long newestCursorSeconds)`, `int size()`; file `no_backup/wa_state/sent.json`, salt `no_backup/wa_state/salt.bin`.
- `RunReport` — the plan § 3.5 fields, `toJson()` with integer and code fields only.
- `DeviceClient` — `Result get(String path)`, `Result post(String path, JSONObject body, int readTimeoutMs)`; `Result{int status; JSONObject body; String detail}`; refuses non-`https://`; the 403 detail is the gate word (`consented_off`, else treated as no consent — plan § 4.0).
- `Gate.state(ctx)` → `NO_CONSENT | CONSENTED_OFF | OPEN | UNPAIRED`, and `Gate.everOpened(ctx)`.
- `Notices.raise(ctx, Notice)` / `Notices.clear(ctx, Notice)`, once per onset (plan § 3.6).
- Manifest component names, declared once by W3 (disabled): `.whatsapp.WaListener`, `.whatsapp.MissedShareActivity`, `.whatsapp.WhatsAppActivity`, `.whatsapp.ShareListActivity`, `.whatsapp.NightlyJob` (JobService), `.MetatronApp`.
- VM wire: `POST /device/whatsapp/run {report}`, `POST /device/whatsapp/missed {keys, ambiguous?, ambiguous_over?}`, the 403 detail `consented_off` / `no_consent` (plan § 4).

### Wave 1 — four workers at once (no dependencies between them)

| Worker | Builds (plan §) | Owns |
|---|---|---|
| **W1 Reader** | § 2 items 1–7: type and `hasContent`, `ReplyRule`, schema check inside `FullBackupMessages.read` (schema-reading code moved from `ProbeBackup` to main), public canonicalise, `ChatList` with `fold`, `Combined.newLinks`, group senders. Plain-Java tests; the SQL half is left for W9's self-test. **Updates the probe callers it breaks** (`src/waprobe/` compiles, its 92 tests stay green). | `src/main/…/whatsapp/{WaMessage,FullBackupMessages,SchemaCheck,BackupCombiner,IncrementReader,ReplyRule,ChatList}.java`, their tests, minimal probe call-site fixes |
| **W2 VM** | § 4 items 0–4: the named gate, run report, stale line once per onset with clear and delete-on-revoke/delete-all, missed endpoint and `--missed-report`. Phase 1's 35 tests stay green. | `tools/intake_whatsapp.py`, `core/server.py` (the `/device/whatsapp/*` routes and `_whatsapp_call` only), `tests/test_intake_whatsapp.py` |
| **W3 Platform** | § 3.8 (`KeyVault`, `DeviceClient`, pairing via `PushStore`'s session token, "Turn off"), § 3.12 (manifest declarations with every component disabled, `Gate`, `MetatronApp` with the process-start sweep stub calling W4's/W5's sweep through one static method), § 3.6 `Notices`, § 3.7's static test, `WhatsAppActivity` (status, key, pair, gate states, the dry-run button wired to a stub), the one page menu entry and bridge method, `waprobe` = `debug` + the probe screen. | `src/main/AndroidManifest.xml`, `android/app/build.gradle`, `src/waprobe/AndroidManifest.xml`, `MainActivity.java`, `static/index.html` (one entry), new `MetatronApp`, `whatsapp/{KeyVault,DeviceClient,Gate,Notices,WhatsAppActivity}.java`, their tests |
| **W4 State** | § 3.4 `SentHashes` (two hashes, prune, salt), § 3.5 `RunReport`, the § 3.1 work-folder sweep and lock as `WorkFolder` (plain Java against a directory, so the kill test runs on the JVM), the skip / update / message / reply-marker **decision** as a pure function `EventPlan.build(combined, sentHashes, shareList)`. Tests: the kill test, prune, each decision branch incl. a live group copy without sender → `update`, 4,000-char truncation hashed as sent. | `whatsapp/{SentHashes,RunReport,WorkFolder,EventPlan}.java`, their tests |

### Wave 2 — after wave 1 is merged and green; four workers at once

| Worker | Builds | Owns |
|---|---|---|
| **W5 Nightly** | § 3.1 `NightlyRead` (uses `WorkFolder`), § 3.2–3.3 `NightlyJob` (JobScheduler, 03:00/06:00, retry rules, 26-h app-open rerun, boot), the per-run order (read → share list → events → report → notices), batches (100 / 256 KiB / 120 s, halving), per-batch cursor, nothing recorded unless accepted, the dry run and its bounds (plan § 3.2, verify new 3). | `whatsapp/{NightlyRead,NightlyJob,Poster}.java`, tests with a fake `DeviceClient` |
| **W6 Share list** | § 3.9: `ShareListActivity` (chats by recent activity, search, contacts lookup, the person's own WhatsApp name in grey for unknowns), `ShareList` store with the user's-save mark, accepted-version tracking, pending removal, the never-from-lost-state rule (verify new 2), the post builder with `senders` and `merges`. | `whatsapp/{ShareList,ShareListActivity}.java`, tests |
| **W7 Live** *(plan's session B)* | § 3.10 `WaListener`: summary skip, chat id from the shortcut, canonicalise via the stored link map, unmapped one-to-one held, ordinal by arrival kept stable through `SentHashes`, posts only while the share list is accepted, drop/reject records nothing, in-memory retry only. Tests on synthetic notification data. | `whatsapp/{WaListener,LiveEvents}.java`, tests |
| **W8 Missed** *(plan's session B)* | § 3.11 `MissedShareActivity`: hash lookup, one / several (≤ 5, `ambiguous`) / over 5 / none, post, toast; the text never posted or stored. | `whatsapp/MissedShareActivity.java`, tests |

### Wave 3 — the lead, with one worker

- **W9 Self-test** (worker): an on-device self-test in `WhatsAppActivity`'s debug section — writes a synthetic database with the planted schema, runs `FullBackupMessages.read`, the schema check (one renamed column → `schema_changed`) and `ReplyRule`, deletes it, shows pass/fail counts only.
- **Lead integration:** wire `MetatronApp`'s sweep, the dry-run button and the job to W5; full suites; `npx cap sync android`; `./gradlew --offline assembleDebug assembleWaprobe`; `./scripts/check_apk_sync.sh`.
- **Fable diff review** of the whole diff — `Agent`, `subagent_type: codebase-reviewer` or `general-purpose`, `model: fable`, read-only, given the plan, the review file and the diff, asked "what breaks, leaks or loses a message"; fix what it confirms; re-run.

**If the budget or context runs short,** stop at the end of wave 2's W5 + W6 merge (the plan's session A seam: the backup path end to end, with the dry run) — commit that, and write the next prompt for W7–W9 in full.

## Output

1. The build, committed — this session's files only, after the Fable review. **Nothing deployed; push only this commit.**
2. APKs built and their sha256 recorded: `debug` (everyone's) and `waprobe` (Mike's re-measuring build). **Not served** — the walkthrough serves them.
3. The walkthrough prompt for Mike (plan § 7 "Then (M5…)"): deploy the VM change → seed `mike`'s consent only → sideload `debug`, pair, key, grants, tick chats, self-test → read the dry run (tapped, and next morning) → then the rest of M4. With the pass line for each step.
4. Close-out: a log fragment titled "clean-room"; the input plan § 4 note; `/archive`.

## Budget

- **Build:** ~4.4–6.7M Opus 5.5 across workers (wave 1 ~1.8–2.6M, wave 2 ~2.0–3.1M, wave 3 ~0.4–0.6M), plus the lead's ~0.5–0.8M for briefing, review and integration; Fable diff review ~0.4–0.7M. Concurrency shortens wall-clock, not tokens.
- **Mike:** none during the build; ~40 min for the walkthrough afterwards, plus the deploy.
- **Run:** $0 on the phone; the VM unchanged until M4 (the changes are behind the closed gate).
- **Persistent state** — as plan § 8's table; no worker adds a store that is not in it.

**Not this session:** Phase 3 (P6 alerts, the cards, the B1b red-team rows), M4 itself, Iva's switch-on (M7).
