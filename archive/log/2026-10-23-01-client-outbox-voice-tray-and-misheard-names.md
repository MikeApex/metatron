### 2026-10-23 (the app keeps what you send, holds voice notes for Send, and misheard names reach the Coordinator as notes) — `54222c0`, `6408b97`, `1243cd4` — **all deployed by Mike the same day (VM at `1243cd4`); APK from `54222c0` sideloaded, 4/4 phone checks passed**

Mike asked for client changes he had raised through Metatron on 10-15, 10-19 and 10-22, and the
Inbox had already captured all of them. Plan: `archive/plans/client_voice_reserve_and_outbox_plan_2026-10-23.md`.

1. **The date on every timestamp.**
2. **A voice tray.** The on-screen mic holds snippets until Send, ✕ deletes one, and a batch is
   stamped with each snippet's *recorded* time (Mike).
3. **An outbox.** A message is kept in localStorage from Send until its reply arrives, and resent
   on reconnect.

**The outbox needed a server half.** A resent `send` re-ran the whole pipeline (~26k input tokens),
and `INSERT OR IGNORE` then dropped the duplicate reply, so it was paid for and never seen.
`/ws` now sends `accepted` and is idempotent on `exchange_id`: a resend of an in-flight turn is
acknowledged, a stored one is replayed, a retracted one replays its retract.

**Mike's rulings:**
- Headset turns auto-send, and are never parked in the tray.
- An offline message older than 15 minutes waits for a tap. The pipeline stamps arrival time, so a
  late "remind me in ten minutes" would count from arrival. Headset turns are exempt and get a
  late stamp instead.
- Errors never auto-retry.
- After 3 unanswered sends, a message is held.

**The Fable review found five races; all fixed.**
- Own-exchange frames were keyed on `shownIds`, not the current exchange, so a late reply could
  land under the wrong message and be spoken.
- A send before `auth_ok` signed the user out.
- A server-error transcription retried forever. It is now capped at 5, then waits for a tap.
- Two others: a resend that could spin forever, and a persona switch that stranded the queue.

Phone check 2 surfaced one more: "Sending…" in airplane mode. The fix is `navigator.onLine`.

**Misheard names: `6408b97` then `1243cd4`.** Plan: `archive/plans/heard_names_plan_2026-10-23.md`.
Mike asked whether this was too pedantic for current models. The traces settled it.
- Relationships created a contact "Eva" (for Iva), and Logistics wrote the calendar event
  "Eva & Benny".
- The 05:50 check-in has carried those names daily since 10-16.
- Specialists act only on the Coordinator's directive. So the Coordinator gets the paragraph
  (`coordinator.md` 1b), and the Synthesizer gets the reply-side line.
- On Flash-Lite that corrected places 3/3 and names only 1/3.

Hence the `[Name note]` from `tools/heard_names.py`. It is appended to the Coordinator's input in
both twins and never rewrites the user's words.
- A contact's own name is never noted.
- A nickname or `referred_to_as` name is noted with who it means.
- A past correction is noted, from `crm/misheard_names.json`, a file lookup never reads.
- An unknown name that sounds like a contact is noted as that contact.

**Measured:**
- Flash-Lite, 5 runs per case: correction 5/5, a new person with the same name kept 5/5,
  "Benny is a real person" honoured 5/5, sound-alike 5/5 (wording chosen by A/B), `MISHEARD`
  written 5/5.
- Mike's 68 messages: a note fires on 7%.

**Rejected, with reasons:**
- **Rewriting the transcript with corrections** (the original rule 2). Mike's Bonnie/Johnny
  question showed that a real Bonnie could then never be registered, even by saying so.
- **A `heard_as` field through `write_contact`.** Collections replace, gate replays drop the
  field, and merges drop it.
- **Using `name_resolutions.json`.** Lookup reads it, so it would recreate the trap.
- **A new Coordinator tool.** An output line parsed like `USER_CORRECTION` needs no grant.
- **Upgrading Whisper.** Mike ruled out the latency.
- **The per-user Whisper vocabulary** (hotwords or prompt): built, measured on 7 recordings on
  the VM, and left **off**. Two of seven were 50–80% slower, an invented name ("Ronifer")
  appeared, and "Benny" persisted. The notes already resolve "Eva".
- **Holding long-form audio upload.** `/transcribe` runs one job at a time.

**Believed true, wrong:**
- "The model will back-interpret" was wrong for names.
- My first matcher (0.6 bar plus a prefix rule) would have put a hint on most turns. The review
  measured it.
- "Eva" was not unflagged because the matcher missed it. "Eva" is on Iva's `referred_to_as`, and
  there is a contact named "Benny" (friend). Rule 1 suppressed both.
- A heredoc-written regex turned `\b` into a backspace. A test caught it.

**Found:** two dictated messages were stored cut off ("…look for phonetic"). The VM's saved
transcripts end at the same words, so the text was lost at capture. The cause is still unknown;
the tray makes it visible.

**Carried from the 09-26 handoff, unchanged:** Build F1 run 1 is stopped. Next is
`claude update` ≥ 2.1.271, restart, then bench test 2. That window's Inquiry files are still
uncommitted in the tree.

