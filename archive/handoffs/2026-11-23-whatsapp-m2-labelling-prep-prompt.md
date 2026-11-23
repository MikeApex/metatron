Model: Opus 5.5 — a small probe export plus a Mac scoring script, where the judgement is privacy (Claude must never see a message text) and the pass bar Mike sets; nothing Red, nothing delegated.

# WhatsApp M2 — prepare and run the labelling walkthrough (clean-room session)

**What this session is for.** Before any WhatsApp alert goes live, measure how well Phase 1's code
extraction (`e45c7cd`) decides "this message needs Mike". This session:
1. builds a way to get about 200 recent received messages onto the Mac;
2. builds a script that runs the VM's own screen, translation and fact code on them;
3. guides Mike to label each one in **his own terminal**;
4. records only the numbers.

The plan is `archive/plans/whatsapp_input_plan_2026-10-26.md` § 7 M2 ("~200 recent received
messages, marked 'needs action' yes/no in a local script on the Mac. Texts and labels never leave
the Mac; scoring prints numbers only").

## ⛔ Rules that bind this session

1. **Clean room still binds:**
   - Open nothing in `archive/transcripts/`.
   - In `archive/log/` and `archive/PROJECT_LOG.md`, read only the WhatsApp entries
     `2026-10-30-02-…` and fragments whose first heading says **"clean-room"**.
   - Look at nothing under `/private/tmp` outside your scratchpad.
   - Use no crypt implementation and no web.
   - This session's fragment is titled "clean-room".
2. **Claude never sees a message text, a contact name or a phone number. This is the rule the
   whole design turns on.**
   - Anything a tool call prints enters this conversation, and so Anthropic's API. So **you never
     run the labelling script, never read the export, and never `cat`, `head` or `grep` it.**
   - Mike runs the labelling in a separate terminal window of his own. A `!` command in this chat
     would put the output in context too, so not that either.
   - What comes back to this chat is the script's final summary: counts and rates only, written
     by code that is tested never to print text.
   - Test this with planted values, the way `ProbeProofTest` does.
3. **Mandatory pre-edit check.** Read `SESSION.md` and `ROADMAP.md` § Section 0, and the current
   state of every file before touching it.
4. **Tiers:**
   - `android/app/src/waprobe/**`, `scripts/` (new) and `tests/` are Amber or Green.
   - `src/main/…/whatsapp/` is **not touched**: its Fable review is owed before Phase 2.
   - `config/agents/*.md` and `core/scheduler.py` are Red and not expected.
   - `config/personas/mike/**` and `./deploy.sh` are Denied.
5. **Two windows share this tree.** `git diff` every file before staging; stage hunks, not files,
   when another window's lines share a file (that happened in the last session).

## Read first

1. Plan delta `archive/plans/whatsapp_phase1_build_plan_2026-11-23.md`:
   - § 2.2–2.3 (the facts, the classify rule, one-to-one vs group);
   - § 5 rulings A–D (D: Bulgarian is translated on the VM by a local model; other scripts are
     held back).
2. `tools/intake_whatsapp.py` — `_analyse`, `build_fact`, `screen`, `english_for`. The scoring
   script calls these **directly**, so it measures exactly the shipped code.
3. Format description `archive/plans/whatsapp_backup_format_2026-10-26.md` § 12, and the phone
   reader `android/app/src/main/java/com/mike/metatron/whatsapp/BackupCombiner.java` and
   `FullBackupMessages.java` (read-only).
4. The probe: `android/app/src/waprobe/java/com/mike/metatron/whatsapp/ProbeActivity.java` and
   `ProbeProofRun.java` (button 7, the newest pattern).

## Steps

**1. Decide the transport with Mike, then build it (the probe, `src/waprobe/` only).**

*Recommended:* a probe **button 8, "Export a labelling sample"**.
- It combines the newest full backup with the live set, using the existing reader.
- It takes the last 30 days of **received** messages that have text, and samples about 200 of
  them, stratified: one-to-one against group in the traffic's own proportions, with Cyrillic
  messages included at their own share and at least 30 of them.
- It writes `m2_sample.jsonl` to the app's private directory. Each row holds `n`, `chat_kind`
  (one_to_one / group), `time_s` and `text`, **and no chat id, no sender id, no name**.
- It offers that file through the Android share sheet, and Mike sends it to the Mac by Taildrop.
- The decrypted backup is deleted before the button returns, as every probe button does.

Alternatives to put to him:
- **Chat ids kept, so a chat's context can be seen.** More identifying, and nothing in scoring
  needs it.
- **The phone serves the file on the tailnet.** That's one more listening port.

Rebuild as before:
- `npx cap sync android`, then `./gradlew assembleWaprobe`;
- serve **only the waprobe build** as `app-debug.apk` on `100.70.67.45:8888`, after
  `tailscale status` shows `jelly-star`. An `assembleDebug` install revokes All-files access.

Test the export with planted values: the row shape, the received-only rule, the stratification,
and no id or name in any row.

**2. Build `scripts/whatsapp_m2_label.py` (run by Mike, never by Claude).**

Reads the export from the path Mike gives it. For each message:
- runs `intake_whatsapp._analyse(...)` with a neutral share entry (`label` "Contact"), so the
  sender label is never real;
- shows Mike the text, our verdict (held back / needs you / chat) and the fact string;
- takes **y / n / s(kip)** for "needs action";
- keeps labels in memory and in a resume file in a directory Mike chooses — the label, our
  prediction, the type, the language and whether it was screened. **No text in that file.**

At the end it prints only numbers:
- **misses:** needs action, but we said chat or held it back;
- **false alarms:** we said "needs you", he said no;
- **precision and recall**, split one-to-one against group and English against Bulgarian;
- the screen's hold-back rate, and how many were held back that he labelled as needing action;
- how many were unscreened.

Then it **offers to delete the export and the resume file.** Default yes; Mike decides.

Tests in `tests/test_whatsapp_m2_label.py` (offline, planted texts):
- the summary contains no planted text, label or number;
- the resume file has no text;
- the arithmetic is right on a known set;
- it resumes after Ctrl-C.

The real translation model must be present on the Mac (`data/models/opus-mt-bg-en-ct2`; it was
fetched 11-23). The script refuses with a clear message if it is absent, rather than scoring
Bulgarian as unscreened.

**3. Put the pass bar to Mike before he labels** (options, trade-off, recommendation).
- The intake precedent is **zero `action_required` misses** on its labelled set (`[DB-0820-03]`'s
  eval gate). For chat, a miss is softened by the V6 backstop, but only for one-to-one questions
  and proposals.
- *Suggested for him to weigh:* recall ≥ 90% overall and no miss on a one-to-one proposal with a
  time. Precision ≥ 60%, because a false alarm costs one look, and the channel only surfaces
  facts, never alerts, until Phase 3.

He sets the numbers. Record them before scoring, not after.

**4. The walkthrough (~45 min Mike):**
1. install the probe build, tap 8, Taildrop the file;
2. in his own terminal, run `cd ~/Desktop/multi-model-mcp && .venv/bin/python
   scripts/whatsapp_m2_label.py ~/Downloads/<file>`;
3. label;
4. paste the final summary block into this chat;
5. delete the files.

Claude guides from the step list and sees only the pasted numbers.

**5. Decide and close.**
- **Against the bar:** pass → M4 is next (seed `mike`'s `whatsapp` consent, turn the stanza on,
  `scripts/fetch_whatsapp_translation_model.py` and `--check` on the VM; the steps are in
  `SESSION.md`).
- **A miss pattern** (a type the markers do not catch) → tune `config/templates/whatsapp_screen.yaml`
  and re-score from the resume file. The script should support re-scoring without relabelling.
- **Extraction clearly falls short** → that is the evidence the 11-22 LM ruling named for
  re-opening the local-model question. Put it to Mike; don't decide it.
- Write a log fragment titled "clean-room", record the numbers in plan § 4, run `/archive`.
  Commit and push are Mike's review.

**Not this session:** Phase 2 (the phone), the cards, and switching the channel on. M4 is its own
guided step once M2 passes.

**Budget:**
- **Build:** about 0.6–1M Opus 5.5 tokens (the probe button, the script, the tests).
- **Mike:** about 45–60 min (one install, one tap, labelling about 200 messages, the bar
  decision).
- **Run:** $0, all on the Mac and phone.
- **Persistent state:**

  | What | What deletes it | Which meter |
  |---|---|---|
  | the export on the Mac (plain text, other people's words) | the script's end-of-run delete, default yes | **none — say so to Mike** |
  | the resume file (labels, no text) | the same delete | none |
  | the probe's private copy on the phone | the button deletes it after sharing | none |
