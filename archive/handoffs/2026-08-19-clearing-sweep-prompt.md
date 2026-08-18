# Next session — the clearing sweep

**This session removes items. It is not a build session.** Paste the block below into a fresh
session. Read `archive/plans/backlog_inventory_2026-08-18.md` first — it is every open item in
plain language, grouped by what would close it, and it is the map for this run.

**Two halves, in this order.** The interactive testing goes first, because it is what actually
empties the largest group, and because Mike has to be present for it.

---

```
/metatron-code

This is a CLEARING session. The goal is a shorter DEV_BACKLOG.md, not more code. Success is
measured in items REMOVED, and the count is reported at the end against the count at the start.

Read archive/plans/backlog_inventory_2026-08-18.md first — every open item in plain language,
grouped by what it would take to close each one. NOTE: it was written at 43 open items; four have
since been closed (the A4 Flash-Lite run, the drop-off inference, the calendar write path, the
Synthesizer deliberation leak). Current state at the time of writing: 41 open (2 Now + 39 Later),
6 untriaged in Inbox, 1,290 lines. Re-run scripts/sync_dev_backlog.py for live counts.

The standing rules for this session, all Mike's, 2026-08-18:

  * A closed item is DELETED from DEV_BACKLOG.md. Its evidence goes to
    archive/backlog_closed_2026-08.md. Notes ABOUT a closed item never stay in the backlog.
  * A sweep that verifies an item must SHORTEN it or REMOVE it. Never lengthen it. Adding
    verification prose to items is the growth mechanism this session exists to reverse.
  * Do not ask permission for work already authorised. Write junk data if a test needs it,
    then remove it and PROVE the removal by re-querying. A deletion claim is not evidence.
  * Confirmation happens in the session that makes the fix. If it genuinely cannot, time-gate
    it with a date, never leave it open-ended.

## PART 1 — Interactive testing, with Mike present

Ten items are finished, deployed code waiting on one ordinary use each — a quarter of the backlog
and the single biggest reason the file grows. Most can be cleared in one sitting. (It was eleven;
the calendar write path was closed 2026-08-18 by running a live test rather than waiting for a
scheduling conversation — that is the pattern to repeat here.)

Ask Mike to drive a normal conversation while you watch what closes. Give him the list of things
to do, in his words, not yours — he should not have to know which item each one closes:

  1. Disconnect and reconnect the app mid-answer.       (doubled answers on reconnect)
  2. Correct a contact's name, then check his profile is untouched.
                                                        (contact corrections corrupting his identity)
  3. Mention a person whose name is close to someone already stored, and resolve it.
                                                        (duplicate contact records / merge tool)
  4. Set the response language to Bulgarian, ask one question, look at the script on screen.
                                                        (Latin letters instead of Cyrillic)
  5. Dictate something and watch the transcription readout.
  6. Any exchange that uses a tool successfully, then one that fails — watch the monitoring view.
                                                        (The Book's newest fields)

For each: if it passes, DELETE the item and write the evidence to the closed file in the same
move. If it fails, that is a real defect with fresh evidence — rewrite the item to say what was
seen, and do not let it revert to "awaiting a live turn".

Two of the ten cannot be closed this way and should be handled explicitly rather than skipped:
  * Tone profiles have never read a real mailbox — needs Mike to point it at one.
  * Usage measurement is deliberately deferred until there is real data. TIME-GATE it with a
    date; do not leave it open-ended.

## PART 2 — The full sweep, item by item

Go through every remaining item in DEV_BACKLOG.md. Exactly one of three outcomes each. No item
may end the pass unchanged.

  (a) REMOVE — already fixed, no longer true, too small to ever be picked up, or a note-to-self
      that is not Metatron work. Evidence to the closed file, item deleted. When in doubt about
      something a user would never notice, remove it: it can always be re-filed if it recurs,
      and archive/backlog_closed_2026-08.md is checked before re-filing.

  (b) DO IT NOW — small enough to finish in this session. Then remove it. Several housekeeping
      items are minutes of work and have sat for a fortnight.

  (c) DECIDE, then file as UNBUILT — a real capability that does not exist. Unbuilt work is
      allowed to sit; that is not what makes the file grow. Compress it to its plain-language
      problem and what it would take, and move on.

Push every DECISION item to Mike as a single batch at the end, each with a recommendation, not a
question. Do not leave the session with a decision unasked.

Specific guidance where the inventory already reached a verdict:

  * The 39 tool-grant decisions are NOT this session. They are judgement per grant and need their
    own run. Leave the item, do not expand it.
  * Housekeeping is 13 items and is where removal should bite hardest. Ask of each: would Mike
    ever notice this? If no, remove it.
  * The six untriaged machine-written entries: read each as a SYMPTOM, never as a diagnosis.
    Three have now named a real problem and guessed its cause wrongly. Open the code before
    filing any of them.
  * Two items are about the backlog file itself (line-count ceilings that stopped tracking cost;
    the Inbox that accumulated notes recording it had been emptied). Fix both here — they are the
    subject of this session.

## Finish

  * Report: items at start, items at end, and what moved. Nothing else leads.
  * DEV_BACKLOG.md is 1,290 lines against a 450 ceiling. Report the line count too.
  * Run /archive.
```

---

## What this session must NOT do

- **Build the National Rail integration.** It is the largest genuinely-unbuilt item and it wants a
  real session with an API key and a quota decision. Leave it.
- **Work the 39 tool grants.** Red tier, judgement per grant, needs its own run.
- **Re-verify items that were verified on 2026-08-18** — the calendar write path, the contact
  disambiguation fix, the Synthesizer deliberation filter, the persona-file tool-grant guard. All
  four were closed by running something. Their evidence is in `archive/backlog_closed_2026-08.md`.
- **Add verification prose to an item.** If a check produces prose, the prose goes to the closed
  file with the item, or the item gets shorter. Those are the only two outcomes.
