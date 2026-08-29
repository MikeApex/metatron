# Hand-forward — the [DB-0822-08] re-measure day, and the decision it feeds (2026-08-29)

*Written by Red session ③ at 11:5x. The measurement could not run in-session: the post-audit
`synthesizer.md` deployed the evening of 2026-08-28 (`6451b51`, with the ritual halves), and a
full scheduled-run day means all of 2026-08-29's runs — the 12:24 and 18:24 email jobs had not
fired when this session did its work. Session ③ deliberately wrote no fix for this item.*

## The measurement (run this first, ~20 minutes, any session on or after 2026-08-30)

One scheduled-run day of `mike` traces against the post-audit + post-ritual-halves deploy:

1. **Proposal adherence ([DB-0822-08]):** for each item raised across the day's scheduled runs,
   did the reply attach a proposed next action ("shall I put time in the calendar for the Apex
   work?", "want me to chase Prudential?") or merely report? Baseline being tested: 2026-08-22
   measured 6-of-9 and 7-of-9 raises with zero proposals. The Proactive Anticipation section
   (`synthesizer.md` § Proactive Anticipation) was untouched by the audit; the file shrank
   ~52.4k → ~41.9k bytes, and length→adherence is the named suspected cause
   (`archive/plans/synthesizer_audit_2026-08-18.md` § 5).
2. **The same day confirms the ritual halves** (`[DB-0809-02]`): the same unanswered question
   appears in at most one run; an empty-delta run reads as a short check-in; only the 20:00
   `evening_close` carries the virtues.
3. **And session ③'s own additions ride the following days:** raised items arriving with a
   coordination check attached will only appear once intake is enabled (see below).

## The decision ([DB-0822-08] `@session:`, Mike's, informed by the measurement)

Fix by instruction, or by an explicit gate. Three options, with a recommendation:

1. **Instruction fix** — strengthen or reposition § Proactive Anticipation. Cheapest, but it is
   the move the item itself warns against: the section already says "mandatory pass … cannot be
   skipped" and was ignored, and every rule added to this file taxes adherence to the rest.
2. **Structural gate** — a code-injected per-scheduled-run directive (the
   `_synth_conditional_sections()` / focus-block pattern that has actually worked in this exact
   family): *every item raised must either arrive with a proposed next action or not be raised*.
   That is Mike's own corollary ("an item that cannot be acted on is not raised; one that can
   arrives with the action attached") stated as evidence the model receives per run, not as one
   more standing rule it can forget. The ritual-halves build is the precedent: "none relies on
   the Synthesizer following an instruction it already had and ignored."
3. **Neither yet** — if the measurement shows the post-audit file now proposes adequately, close
   the fix half on the evidence and write nothing.

**Recommendation: measure first (owed anyway), then option 2 if it still fails.** Option 1 is
recommended against on the item's own reasoning regardless of what the measurement shows.

## Flag, not a blocker — intake is still dark

Session ③'s email-surfacing + coordination-check instructions ([DB-0822-09]) are live at deploy
but exercise only once Mike enables intake on the VM (`enabled: true` in mike's `intake.yaml`
— gates `[DB-0820-03]`/`[DB-0820-04]`). Until then the logistics/recreation intake queues stay
empty and the Synthesizer's inbox-surfacing rule has nothing to surface.
