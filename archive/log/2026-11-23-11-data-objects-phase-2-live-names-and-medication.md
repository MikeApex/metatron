### 2026-11-23, eleventh (the user's own logs, phase 2 — the lists fill themselves; no real details in code; one medication record, checked in code) — `76161b0`, `2ea9b8c`, `35fb231`, `e701a6a`, `704fada`, `388a91c`, `95c3ce7` — **all deployed by Mike (VM at `95c3ce7`)**

**Incoming handoff:** phase 2 of `custom_logs_and_places_plan_2026-11-21.md` from
`archive/handoffs/2026-11-22-data-objects-phase-2-build-prompt.md` (Opus, high). Built and deployed as
`76161b0` the evening before; this entry covers the M4 labelling, the flip, and what followed.

- **The derived writer is ON** (Mike: *"the lists should populate without users constantly giving
  permission"*). Labelled in chat in batches (his choice): 24/30 as first labelled; every miss had a code
  cause and was fixed, and the as-built writer scored 28/28 (plan § 11). Built from his answers: meal
  times (said > "just had" > the user's usual time from the day shape, never later than said; design
  dinner 18:30; "the usual oatmeal" named breakfast from his food facts), one entry per thing (a
  derived mention adds to the note), Podcasts / Gift ideas (linked to the one contact named) /
  Notable experiences templates, `remove_entry`/`restore_entry` (out of view, kept), App development
  backlog entries also file a FEATURE_REQUEST, and the extractor routes tastes/specs/sightings to
  `other` (the new-list detector was starved: 8–10 of 11 probe phrasings now route, 0 of 6 controls).
- **Live checks on mike found three real defects, all fixed:** the Coordinator re-logged the previous
  message's meal (coordinator.md "add" = *this* message only, plus a 30-minute Meals-only twin guard —
  every other event log keeps R20); a Diarist-written meal had no time (the meal rule now runs in
  `archive_write`); YAML read a bare `on` as `True`, which would have left the writer silently OFF
  (caught by a clean-export import check before push, `35fb231`).
- **No real details in code (Mike's rule, CLAUDE.md § Data Privacy).** His final scope, after one
  correction: "Mike" allowed; tests, temp files and persona data exempt; surname, emails, schools and
  real name+place pairs not. ~100 lines in 42 files; replacements chosen so every comment quoting a
  measured name-similarity score stays true (Betty/Matty 0.60, Ada/Ida 0.67, Rebecca/Rebekah 0.71).
  The spent wisdom-migration script deleted. Persona fallbacks traced: none served Mike's data to another
  user; an ownerless push subscription now gets nothing, and a hand-run tool must name its persona.
  **Filed:** scrub dev records + git history before the repo is ever shared (Mike: "not now").
- **Medication — one record, checked in code (D11, unblocks the instructions-to-code build).** A
  read-only "Medication taken today" view over linked habits (`medication` field, refused if the
  profile lacks the name). Mike: "PH and the rest of Metatron work from the same data" — so per
  medicine: a linked medicine's doses live only on its habit; an unlinked one keeps its daily-log entry.
  Physical Health's `MEDICATION_TAKEN:` line is recorded **by code** (his standing preference), and its
  check keys on a code-computed `missed`. Two Fable reviews found 11 then 12 defects (silent unlinked
  medicines, words not matching titles, weekly/twice-daily/skipped false misses, repeats, renames,
  leaks); all fixed. **A4 4/4 PASS live** including the new PH-MED-UNLINKED. Mike's two optional
  supplements wired on the VM.

**Rejected:** a second dose store (two records disagree in a hard-fail domain); fuzzy matching of
medicine names; deriving the backup persona list (it is Mike's 10-27 ruling, and ids are account keys).

**Wrong earlier:** "the Synthesizer falsely claimed adding Lex Fridman" — it wrote a file no list
owned. "Meals go to the daily log" — they were mostly kept nowhere. "`write_log` can just drop
`medications_logged`" — for an unlinked medicine it is the only record.

**Outgoing:** the instructions-to-code build is unblocked; phase 3 (Places) has no prompt yet; the
Tasks block may still nudge a dose skipped from a weekly quota (5-line fix, left).

