### 2026-11-22, second (the user's own logs, phase 1 — built, reviewed by Fable four times, live-checked on mike in four rounds) — `9542e34`, `e796ce6`*, `1fc9256`, `a9b29ae`, `880027c` — **all deployed by Mike (VM at `880027c`); mike seeded on the VM**

**Incoming handoff:** log § 11-21 fourth. The data-objects plan was planned and Fable-reviewed (34 rulings); the phase 1 build prompt was `archive/handoffs/2026-11-21-data-objects-phase-1-build-prompt.md` (Opus, high).

**Built (`9542e34`):**
- `tools/data_objects.py`: registry, seven templates, the read rule, four tools.
- The Coordinator's `DATA_OBJECTS` (start/add/read). Code starts the log, sets a pending marker and pre-fetches reads.
- A verified Diarist write: one retry on the reasoning tier (cloud `retry_model`; none in local mode, for fail-closed), then a push, an event and a next-reply note.
- The per-turn manifest, never in the cached prefix.
- The tagger, `data_object_tagger`, and the grants.
- The VM seed script, which also registers the cardiac log as a health log.

**Mike's decisions:**
1. A Diarist `write_archive` into the right category counts as landed.
2. The Synthesizer reads every log.
3. The retry key lives in routing.
4. A code-only tagger.
5. One read door: `read_data_object` replaced `read_archive` everywhere, Build included.

Fable's diff review found 13 issues; the fixes went in before commit. The worst:
- "Started" contradicted the Synthesizer's no-action line, so code rows now go on the ACTIONS line.
- The wrong write could clear a marker; now only a live Diarist run clears one.
- Sleep and Exercise reads went silent; the holder is now sent to read them back.
- A path traversal predated the build.

A Fable loose-ends pass closed 9 more.

**Live round 1 (Mike typing, a "Frogs" log).** Start, add, read, archive and heart log all passed. Two things it exposed:
- A correction was saved twice.
- "Caught last year" was stored as said.

**Mike's rulings:**
1. An explicit `"amend"` act.
2. A relative-reference rule for every record writer, in one home: `tools/record_rules.py`, appended to six tool schemas; option 2 of 2.
3. A log entry placed only "here" gets one "where?" question (option 1).

Fable's operational review found 13 more issues; all were fixed except two that were accepted:
- an add-only mislabel still rests on the Coordinator;
- "sent" in the user's words adds noise to the quality log.

**Rounds 2–4 (run by Claude Code on the VM as mike, in TEST-marked logs, at Mike's instruction).** Three corrections came out of them:
- **Starting a log filed the request as entry 1.** A model can no longer create a log.
- **The Diarist changed an entry being corrected twice, against explicit holds.** Mike removed its `amend_data_object` grant (`a9b29ae`; first proposed in `1fc9256` and declined).
- **The answer "Greenwich" became a new entry twice.** In `coordinator.md`, an answer is now an amend; in code, the Diarist can add to a log only when that turn set a live marker (`880027c`).

**Wrong earlier:**
1. **"An instruction will hold the Diarist."** Three holds failed live. Each failure was closed in code or by removing a grant. Expect the same of any instruction that forbids a write.
2. **The first place example, "'here' → where the user was", was copied into an entry word for word.** An example must show a real value.
3. **"As is known" let "here" be filled from an earlier turn.** A place is now resolved only from what the user said.

**Accepted limits:**
1. A private log is still pre-fetched when named.
2. Two simultaneous Diarist runs on one log can cross-clear.
3. The 1-row archive `tasks` category is shadowed by the task store, but stays on disk.

**`e796ce6`\* carries this session's amend act and relative-reference rule under the other session's message.** That session committed while these files were staged. The content was verified first; history was not rewritten.

**Outgoing:** phase 1 is live. The four TEST logs are archived; nothing can be deleted by design. Phase 2 (noticed logs) is next per the plan, and has no build prompt yet.

