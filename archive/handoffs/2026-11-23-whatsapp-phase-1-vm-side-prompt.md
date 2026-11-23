Model: Opus 5.5 — a month-old plan to re-anchor against code that has moved, then a multi-file VM build (endpoint auth, intake split, obligations, purge) where the judgement is the work; Red is not expected, so nothing here is delegated except a Fable review of the re-anchored plan.

# WhatsApp Phase 1 — the VM side: receive, screen, extract, surface (clean-room session)

## ⛔ Rules that bind this session

1. **Clean room still binds** (rules 1–4 of `archive/handoffs/2026-10-31-whatsapp-phase-0-close-survival-lm-increments-prompt.md`):
   - Open nothing in `archive/transcripts/`.
   - In `archive/log/` and `archive/PROJECT_LOG.md`, read only the WhatsApp entries `2026-10-30-02-…` and fragments whose first heading says **"clean-room"**.
   - Look at nothing under `/private/tmp` outside your scratchpad.
   - Use no crypt implementation and no web.
   - This session's fragment is titled "clean-room". Never put the other phrase in its first heading: the write-time briefing's match fails closed.
2. **Mandatory pre-edit check.** Read `SESSION.md`, `ROADMAP.md` § Section 0 (the privacy ruling and its amendments, which matter for Iva) and the current state of every file before touching it.
3. **Tiers.**
   - `core/server.py`, `core/auth.py`, `tools/intake.py`, `tools/obligations.py` and the new files are Amber.
   - `core/scheduler.py` and `config/agents/*.md` are Red and **not expected**. If you think you need one, stop and ask.
   - `config/personas/mike/**` is Denied. So is `./deploy.sh`: Mike runs it.
4. **Two windows share this tree.** `git diff` every file before staging, and stage an explicit list.

## Read first

1. Plan `archive/plans/whatsapp_input_plan_2026-10-26.md`:
   - § 3 VM (V1–V9), and the "Tasks" and "Closing proposals" paragraphs;
   - § 3 Phone P2 (the message key) and P3;
   - § 4 Phase 1 and **"P3 BUILT, 11-23"**;
   - § 5 W1–W10, § 6 Costs and § 10 Files.
2. Format description `archive/plans/whatsapp_backup_format_2026-10-26.md` § 12. It defines what the phone will send: the field map, sets, and the gaps the increments leave.
3. Log § 11-23 sixth (`archive/log/2026-11-23-06-whatsapp-reader-extension-p3-clean-room.md`).
4. The phone-side record type the VM will receive: `android/app/src/main/java/com/mike/metatron/whatsapp/WaMessage.java` and `BackupCombiner.java`.

## What changed since the plan was written (10-26), and must change the build

- **Every line number in plan § 3 is a month stale.** For example, `_PROPOSAL_SOURCES` is now at `tools/obligations.py:3199`, not `:2226`, and `sweep()` is at `tools/intake.py:1142`. Re-anchor each one against the code. Don't trust a cited line, and don't trust that a cited function still does what the plan says.
- **The second-user build has landed** (`core/accounts.py`, `core/consent.py`, per-user tokens in `core/auth.py:200`). The device token (P5) and V1's user-from-token are built on top of it, so read how it works now.
- **Iva:** her data carries `mike`'s clearances (ROADMAP § 0, amendment 11-18). Her consent records (`core/consent.py`) still gate each path per user, and W10 needs consent that *explicitly covers WhatsApp*. The channel is **off by default for every user**, and switches on only with both the channel stanza and that user's WhatsApp consent record.
- **The message key needs time in seconds.** Increments carry seconds (§ 12), but the full backup and live notifications carry milliseconds. P2's key (canonical chat + message time + ordinal) must therefore floor to **seconds**, or a live message and its nightly copy from an increment will key differently and both get recorded. The phone builds the key in Phase 2, but the VM's contract and its tests fix the definition now, so write it into the endpoint's schema.
- **Deletions are never applied** (Mike, 11-23). The phone sends no "delete" event. A later copy of a message is an **update** (V4's `revise()`), and that is how withdrawn text disappears.
- **Increments leave out some messages** (§ 12: 55 in two sets, 52 textless, 26 the user's own). They arrive only with the next full backup, about 6 days later. **V6 relies on reply markers**, so first find out what those messages are (step 0).

## Steps

**0. Count what the increments leave out (`src/waprobe/` only; Mike, one tap after 02:00).**
- Add one line to button 7's "only newest" breakdown: the omitted messages' `message_type` distribution (small integers, counts only), split by from-me.
- Rebuild the probe: `npx cap sync android`, then `./gradlew assembleWaprobe`.
- Stage the APK in your scratchpad. Check `tailscale status` shows `jelly-star` online, then serve it as `app-debug.apk` on `100.70.67.45:8888`. **Serve only the waprobe build to Mike's phone:** an `assembleDebug` install over it revokes All-files access.
- Mike taps 7 and sends the report over Taildrop; it lands in `~/Downloads`. The run also covers the **first live set**, which the reader reads through `IncrementSet`.
- **Decide with Mike:** if the omitted from-me messages are a kind a reply can take, V6 needs a stated tolerance (a re-raise up to about 6 days late) or a different signal. Put the options, the trade-off and a recommendation to him. If they aren't, record that and move on.

**1. Re-anchor the plan, then pause (no code yet).**
- For each of V1–V9, write down where it now lands in the code: the function, the current line, and whether the plan's premise still holds.
- Write the result as a dated delta at `archive/plans/whatsapp_phase1_build_plan_2026-MM-DD.md`, with the todo list, the endpoint schema (including the key in seconds) and each test named.
- Run `/adversarial-review` on it (Fable).
- **Show Mike the todo list and wait for his go-ahead** before building.

**2. Build V1–V9** as the plan and the delta say:
- V1: the endpoint trio under `/device/*`, with the device-token verifier in `require_auth`.
- V2, V3 and the WhatsApp index: `tools/intake_whatsapp.py`.
- V4: split `ingest()` out of `sweep()`, and add `revise()`.
- V5: the per-task `"whatsapp"` proposal source.
- V6, V8, V9.
- **V7's cards are Phase 3.** Build only the endpoints Phase 1 needs.
- Add `dateparser` to `requirements.txt`.
- The channel stanza in `config/templates/intake.yaml` is **off**.
- Offline tests go in a new `tests/test_intake_whatsapp.py`, in the `tests/test_intake_pipeline.py` pattern. Cover at least:
  - a device token refused off `/device/*`, and a session token refused on it;
  - the user taken from the token, never the body;
  - the body cap;
  - an event with no chat ID rejected, and a chat not on the share list dropped;
  - a live event and its nightly copy (ms vs s) recorded once;
  - an update replacing the fact;
  - three messages from one sender producing one proposal card, and none after a decline;
  - V6's re-surface once, and a reply marker clearing it;
  - the purge;
  - the 90-day expiry;
  - reply markers never reaching `ingest()`;
  - the channel staying off without the consent record.

  Run `bash scripts/qa_sweep.sh` and the intake suites.

**3. Mike reviews and commits** (guided, area by area). Push, then assert `HEAD` equals `origin/main`. **Deploy is Mike's** (`./deploy.sh` is Denied). With the channel off, a deploy changes nothing a user sees, so it can wait for his next one.

**4. Close.**
- Write a log fragment titled "clean-room".
- Update plan § 4.
- Run `/archive`.
- **Propose M2 as a guided walkthrough session**, with the steps prepared in advance: ~45 min, ~200 received messages labelled on the Mac, numbers only. It must happen before any WhatsApp alert goes live.

**Not this session:**
- Phase 2, the phone: P1 share list, P2 listener, the WorkManager job, P4 key screen, P5 native HTTP. Before Phase 2 wires the reader in, a Fable review of `src/main/…/whatsapp/` is owed (about 0.2M).
- Phase 3: cards, P6, the red-team rows.

**Budget:**
- **Build:** about 3–5M Opus 5.5 tokens (plan § 6), plus about 0.3M for Fable's review of the delta. Step 0 is about 0.05M.
- **Mike:** about 30 min (one tap, the step-0 decision, the todo review, the commit review), plus his deploy.
- **Run:** about $0.01–0.03 a day once switched on (plan § 6: no per-message model calls; facts in Coordinator and Synth context). Nothing while the channel is off.
- **Ancillary:** `dateparser` on the VM.
- **Persistent state this creates:**

  | What | What deletes it | Which meter |
  |---|---|---|
  | the WhatsApp index | expires and purges with its facts | none needed |
  | the per-user cursor | the channel purge | none |
  | device tokens | revocation, and expiry after 30 days unused | their own last-used time; no existing meter reports one |
