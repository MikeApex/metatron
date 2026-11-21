# Capture fidelity — notes from labelling mike's backfill (labelled 2026-11-18 → 11-20)

Review file: `data/personas/mike/capture/backfill_review_2026-11-18.jsonl` (VM). Labels:
`labels_2026-11-18.jsonl` beside it, 68 rows (18 precision, 50 recall). Plan:
[capture_fidelity_plan_2026-11-18.md](capture_fidelity_plan_2026-11-18.md).

## Score (`tools.capture --score --persona mike`, 2026-11-20)

| Measure | Result | Minimum | |
|---|---|---|---|
| Precision | 72% (13/18 real; 3 wrong_kind, 2 not_a_fact) | 90% | fail — n=18 is ±~20 pts at this value |
| Recall | 18% (20/50 found-nothing turns held a miss, scaled to 149 such turns) | 80% | fail — ±~14 pts on the miss share; not near the bar |
| Matcher | 100% (no matcher_wrong) | 90% | pass |

**Not switched on.** `enabled` stays false. The interviewer (mode `on`) writes day shape, and two
of the five precision failures are invented day-shape values (P16, P18).

Recall labels were corrected for the backfill's own distortion: the extractor is given today's
record as ALREADY RECORDED and told to skip it, so a fact saved after the turn reads as
"found nothing". Four named misses were held in today's record and flipped to not-missed
(R23 lunch with Iva, R29 Bakhmat follow-up, R38 the same lunch, R42 Benny's vaccination).

## Extractor-rule issues (`config/agents/capture_extractor.md`, Red)

1. **A one-occasion report became a standing day shape** — P16 "slept well last night from
   about 11 to 7" → bed/wake on all seven days. One-off reports are logs.
2. **Invented values** — P18 focus blocks Mon/Wed "from next week": proposed 15:00–17:30; the
   user gave 13:30–18:00 five hours earlier (R45), likely outside the six-message window. Values
   must come from the user's words in the conversation shown, never the record or Metatron's text.
3. **A standing time constraint filed as a preference** — P1 gym "evenings don't work" → day shape.
4. **A task's reason filed as a separate goal** — P9 "upload longer reflections as one audio
   file" is the purpose of P2's voice-recorder task; it belongs in that task.
5. **A habit correction filed as a profile fact** — P15 "it's just stretching … twice a day" was
   merging two duplicate stretching tasks.
6. **Spelled-out name ignored** — P6 proposed "Nepo Tom" though the user spelled N-E-P-O-T-A-M.
7. **Dates and cadence dropped from task proposals** — P8 lost "tomorrow"; P13 lost "mid-March"
   and that it recurs.
8. **Development notes** — P3 (estimate durations instead of asking) is a user preference AND a
   design note for all users, to be actioned outside chat; P4 (backlog note on GPS) is a dev note
   only, not a fact. Rule: list a dev note only where it also states how the user wants Metatron
   to behave for them.
9. **Recall — classes skipped that the kinds cover:** standing arrangements (R21 Friday
   babysitter), durations of regular tasks (R6, R34), "remind me on X" (R15, R20, R40), "from now
   on" preferences (R41 focus time vs admin), work windows (R45). The opening "when in doubt
   whether it is a fact, leave it out" biases hard toward omission.

## Scope — facts with no kind (Mike, 2026-11-20: add; and notice future gaps)

- **Events / appointments:** R5, R31, R32, R36, R45 (GP).
- **Places and household knowledge:** R22 (a restaurant to remember), R39 (out-of-hours GP for
  the kids — Mike: wisdom, or physical health).
- **People:** R7/R41 (which practitioner is which — also a calendar and CRM correction).
- **Corrections to an existing record:** R41, R28, P15.

## Matcher / backfill issues

1. **A Metatron-voiced message counted as a user turn** (R8) — the backfill's turn filter let it
   into the 160 "real user turns".
2. **"Eva" is the transcription of Iva** (R12, R21, R38) — a profile alias would stop records and
   matches treating them as two people.

## Raised in passing, not filed

- **Duplicates across stores are unchecked.** Each store guards itself (task ledger word-match +
  same-message guard; daily calendar duplicate audit; horizon dedupes by key), but nothing
  checks a task against a calendar event, horizon item or wisdom entry. R8's two duplicate pairs
  were caught by hand. File only if Mike asks.

---

## Second pass — the 2026-11-20 re-run (`3f47391`), labelled 2026-11-21

Review file `backfill_review_2026-11-20.jsonl`, labels `labels_2026-11-20.jsonl` (100 precision,
49 recall). 79 of 100 precision and 46 of 50 recall labels were carried from the first pass's
rulings — the same fact, or a rule Mike stated — and Mike ruled the remaining 21 + 4.

**Score: precision 84% (fail, ±~7) · recall 86% (pass) · matcher 96% (pass).** First pass:
72 / 18 / 100.

- **A first re-run was discarded:** relative dates resolved against the run's own day, not the
  message's ("tomorrow" on 10-15 → 11-21). Fixed in `3f47391`; live turns were never affected.
- **Precision's 16 misses:** 9 not-facts (one-occasion logs and states, "do it right now",
  in-progress dev work, completions, an undated "made an appointment") and 7 wrong kinds
  (preferences filed as corrections — the Rowan double-check, the Franklin-virtue changes;
  "goals for next week" that are tasks; "find a pub" filed as a place; a routine duration filed
  as a day-shape entry with invented times).
- **Value errors kept as notes:** Ben's vaccine dated 2026-05-17 instead of 2027; school drop-off
  given invented times 00:00–00:45 on every day.
- **Matcher wrong ×4** — each a fact the first pass's matcher found kept, now worded with fewer
  shared words: Aisha, the quarterly cultural task, refreshing shoes, Ben's vaccine.
- **Dropped from the sample:** recall R8, a development-written housekeeping template pasted
  unedited (placeholders still in it) — not the user's words.

**Mike's notes from this pass (design input, not labels):**

1. A preference about a person ("double-check me next time I schedule with Rowan") belongs on
   that person's contact record, so scheduling is guaranteed to pick it up.
2. **Places** need a GPS entry and a verdict — Clipstone "went, not again"; Bianco 43 "our
   go-to, raise it the next time pizza comes up near home"; 108 Brasserie "try if nearby,
   pricey" — and places visited should be logged as a matter of course.
3. A one-day remark that may be a pattern ("napping between two and four") should be an `ask`
   about regularity, not dropped and not saved with invented days.
4. Health facts can be time-bound: the cardiac monitoring ended 2026-11-19.
5. **Custom logs** — "log this as a separate file: date, time, reason" is a request to create a
   user-defined record; Metatron should also notice when one is needed unasked, and common ones
   should become general fields. A survey (2026-11-21) found no runtime mechanism; the cardiac
   log was built by hand. Planning prompt:
   `archive/handoffs/2026-11-21-custom-logs-and-places-planning-prompt.md`.

## Third pass — `6e8ed5d`, labelled 2026-11-21

Examples in the instructions replaced with invented ones (Mike: the old ones contaminated the
retest, invited surface matching, and put mike's life into every user's prompt). 52 of 100
precision labels carried mechanically from the 11-20 pass (same message, ≥ 50% word overlap),
adjusted where the kind moved the way Mike ruled; the rest from his stated rules. **Precision
87% · recall 90% · matcher 98%** — switched on by Mike's ruling (plan § 10).

- **Recall regressions** from the 11-21 instruction lines: the durations message (stretching,
  groceries, plants, bills), the Fid transfer, the chicken-soup errand, "keep the heart log
  simple" — all found before, empty now. The new "not a fact" lines over-suppress slightly.
- **Goals 1/3:** both misses are a message where the user said "that'll be a goal for next
  week" — the extractor took the user's word over the rule.
- **A fact taken from the previous message** (meals check-ins listed again on the next turn) —
  counted not-a-fact for this message.
