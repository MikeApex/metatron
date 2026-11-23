Model: Opus 5.5 — a guided ~40-minute session with Mike (deploy, consent, sideload, the dry run); it reads counts and codes only, and must stay clean-room.

# WhatsApp Phase 2 — the walkthrough: deploy, consent, sideload, the dry run (clean-room, plan § 7 "Then (M5…)")

**What this session is for.** The Phase 2 build is committed (the 11-23 commit whose message begins "WhatsApp Phase 2 built"; find it with `git log --oneline --grep 'WhatsApp Phase 2 built'`; its log fragment is titled "clean-room"); nothing is deployed and nothing has reached a phone. This session takes Mike through the five steps of plan § 7 "Then", in order, each with its pass line. **Stop at the first step that does not pass** and say what it means before going on.

## ⛔ Clean room — binds this session in full

1. Open nothing in `archive/transcripts/`. In `archive/log/` and `archive/PROJECT_LOG.md`, read only `2026-10-30-02-…` and fragments whose first heading says "clean-room". Nothing under `/private/tmp` outside your scratchpad; nothing in `~/Downloads` except a file Mike names for you to read. No web. No crypt implementation, no field meaning from memory of a published schema; never say what a WhatsApp type number "is".
2. **No message text, contact name or phone number** enters this conversation, a log or a file. The screens Mike reads to you carry counts, codes and his own chat labels; if he reads a label aloud, do not write it down.
3. Your log fragment's first heading says "clean-room"; never the other phrase.

## Read first

1. `archive/plans/whatsapp_phase2_build_plan_2026-11-23.md` §§ 0, 3.2 (the dry run), 3.6 (the notices), 3.12 (what consent switches on), § 7 "Then".
2. `archive/plans/whatsapp_phase2_diff_review_2026-11-23_fable-5-2.md` — what the review found and what was changed.
3. `docs/INFRASTRUCTURE.md` § Android app — build and sideload (how the APK is served).

## The steps

### 1. Deploy the VM change (Mike runs it — `./deploy.sh` is Denied to Claude)

The VM side of Phase 2 is harmless with the channel off: the closed gate now names which gate (`consented_off` / `no_consent`), plus the run-report and missed endpoints. It must reach the VM **before** the APK reaches the phone (plan § 4.4).
- Mike, on the **MacBook**: `cd ~/Desktop/multi-model-mcp && ./deploy.sh`.
- **Pass:** then on the **VM**: `cd ~/multi-model-mcp && git log --oneline --grep 'WhatsApp Phase 2 built'` finds the commit, and `.venv/bin/python tests/test_intake_whatsapp.py` ends `49/49 passed`.

### 2. Seed `mike`'s WhatsApp consent only — the stanza stays off

- On the **VM**: `cd ~/multi-model-mcp && .venv/bin/python scripts/accounts.py seed-consent mike --scopes whatsapp --evidence "Mike W10, 2026-10-26"`.
- **Pass:** `.venv/bin/python -c "import tools.intake_whatsapp as W; print(W._consent_granted('mike'), W.channel_open('mike'))"` prints `True False`. **If it prints `True True`, stop** — the stanza is already on, and the phone would go straight to the real run with no dry run.
- **Not Iva.** Her consent is M7; her install stays "WhatsApp link: not set up".

### 3. Sideload `debug`, pair, key, grants, chats, self-test

- **Serve** `android/app/build/outputs/apk/debug/app-debug.apk` the standard way (`docs/INFRASTRUCTURE.md`: staged copy, `http://100.70.67.45:8888/app-debug.apk`). First check `shasum -a 256` begins **`7e512fa285e94536`** — if not, it was rebuilt; say so before serving. Mike installs **over** `waprobe`: same app id, the sign-in stays, and **All-files access is kept** — Phase 2 declares it in `debug` too (§ 3.12). Mike's phone moves to `debug` here; `waprobe` (sha `df037063e82ecb1b`) stays for re-measuring only.
- In the app: ⚙ → **WhatsApp link** (shown only in the app, signed in). **Pass:** the screen says "WhatsApp link: not set up" with **Pair this phone**.
- **Pair this phone.** **Pass:** the screen now shows the key field, All-files access, Contacts, Choose chats, "Dry run now", "Check this phone's reader" and the line "WhatsApp link is off". **If it says "WhatsApp needs your consent first", stop:** step 1 or 2 did not land (the phone reads every 403 that is not exactly `consented_off` as no consent — by design).
- **Enter the 64-digit key** (Mike's existing probe key is not migrated — he re-enters it once). **Pass:** "key stored".
- **All-files access:** **Pass:** shown as held (it should already be). **Contacts:** grant.
- **Check this phone's reader.** **Pass:** exactly "Reader self-test: 26 of 26 passed". Any failed check name → stop and read it out; it names a reader query that does not work on this phone's SQLite.
- **Choose chats** (M3). **Pass:** chats listed newest first; one-to-ones by contact name, unknowns as "Unknown contact" with a grey name; groups by subject. Tick the chosen chats, Save. **Pass:** "not yet sent to Metatron" — expected: the VM refuses the share list until the channel is on. **No "out of step" notification** (a 403 is the gate, not a mismatch).

### 4. Read the dry run — tapped now, and again the next morning

- **Dry run now.** It reads, combines and builds what it would send from the last 90 days, and **posts nothing, records nothing**.
- **Pass (screen, "Last run"):** marked dry; would-send **messages > 0** for the ticked chats, per chat by Mike's labels; reply markers counted; the report's counts — received rows read across all chats, with text > 0 in both the full backup and the increments; `without_key_id`, `without_chat`, `text_undecodable`, `base_key_collisions` small; same-second groups counted; no error.
- **Read for these specifically:**
  1. **An error `increment_missing_part`** → the chat-list fold met a nightly chat row without the column it keys on (W1's open question — unverified on real increments until now). Stop: the fix is in `ChatList.fold`, and nothing posts until it reads.
  2. **"Would warn: WhatsApp changed how it stores messages"** (≥ 20 received rows, none with text) → stop; the reader's text paths no longer match.
  3. **"Would warn: WhatsApp has stopped backing up"** → check WhatsApp's own backup settings (nightly increments on, a full backup within 8 days) before M4.
- **Nothing has reached the VM — Pass:** on the **VM**, `cd ~/multi-model-mcp && .venv/bin/python -c "import tools.intake_whatsapp as W; s=W._load_state('mike'); print('report' if s.get('run_report') else 'no report', len(W._read_jsonl(W._index_path('mike'))), 'indexed', len(s.get('share') or {}), 'shared')"` prints `no report 0 indexed 0 shared` (counts only — it prints no id or text).
- **Next morning** (the 03:00 job; the phone on charge overnight): the screen's "Last run" time is after 03:00 and still marked dry. **Pass:** counts in line with the tap (a night's new messages more). **If no run happened:** the job did not schedule — read the screen's job line; nothing else proceeds until it does.

### 5. Then the rest of M4

The stanza on for `mike` and the translation-model check — as Phase 1's M4 (`archive/plans/whatsapp_phase1_build_plan_2026-11-23.md`) and the input plan. Then:
- **Open the WhatsApp screen once** — that is when the phone sees the channel open, schedules the real job and enables the live listener (**Allow notification access** is offered now; grant it).
- **The first real night is compared with the last dry run:** `posted_messages` ≈ the dry run's would-send messages (plus new ones), `posted_reply_markers` ≈ its markers. On the **VM**: `.venv/bin/python -m tools.intake_whatsapp --missed-report --persona mike` prints counts only.
- **Live check:** a message in a shared one-to-one arrives within seconds. **If it arrives only overnight**, the live path is reading WhatsApp's notification lines as the user's own (W7's conservative rule — when unsure, a line is treated as the user's and left to the backup); note it, and the fix is in `WaListener`'s own-message test, not in the VM.
- **"Should have come up":** long-press a message in a shared chat → Share → **Should have come up** → a toast. Then `--missed-report` counts one flag. Whether WhatsApp's shared text equals the message text is unverified until this first share (§ 3.11).

## Close-out

A log fragment titled "clean-room" (what passed, what stopped, the counts — never content); `/archive`.
