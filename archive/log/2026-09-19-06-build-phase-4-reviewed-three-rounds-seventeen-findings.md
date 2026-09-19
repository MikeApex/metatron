### 2026-09-19 (Build phase 4 reviewed three rounds — seventeen findings, and a review that RAN the code)

Continues the `2026-09-19-04` fragment, which built phase 4 and closed its own five defects. The
§ 14 second-model review then ran in Fable 5.1 across **three rounds: fourteen findings, then
three, then none.** All seventeen fixed. Suites grew 281 → 336 checks (runner 38→59, registry
15→18, coherence 19→24, probe 38→41, jobs 20→21, `test_turn_referent.py` 16→22); `qa_sweep`
11/11 throughout. **Phase 4 is complete.** Still uncommitted, by instruction.

**The method is the finding, and it is why this round differs from phase 3's.** Phase 3's reviewer
read the code and probed the writer's fixture. This one **ran the runner** — ten probes driving
real jobs to `landed` through the real writer and the real 18-check sweep, then re-running every
probe unchanged after each fix round. What it found could not have been read:

- **Round 1 (fourteen) — mechanisms that had never been EXERCISED.** Not prose without mechanism
  (round 1 of phase 3), not mechanisms scoped to their probe (round 2), not a mechanism improved
  in one of two homes (round 3). These read correctly and had never once run. `refuse()` had no
  state guard, so the one irreversible board command would delete a live capability. A job
  crossing its budget mid-call was FAILED terminally, past the one state that exists to release
  it. A job parked above the ceiling could not be resumed by any command. The coherence model
  pass rejected every well-formed reply while reporting `model_ran: True`. Every brief write after
  N10 was silently refused. `_write_partial_brief` could never have succeeded at any of its three
  call sites — removed rather than fixed.
- **Round 2 (three) — the round-3 shape, returning.** Two were a rule that reached one of its two
  homes: the brief learned which state it could be written *from* and not which to *report*, so a
  landed capability's final document said `executing`; and correction attribution learned to skip
  a `build_tick` while `turn_referent`'s referent block — the other reader of the same file, on
  every user turn — still announced one as *"the exchange immediately before this one."*
- **Round 3 (none).** Everything held.

**D4 is the one worth carrying forward: the review reported one entry, the fix found twelve.**
`log` — the primary corpus — probed as `error` because `{"days": 14}` fits no signature of
`get_log_window(start_date, end_date)`. Fixing that entry alone would have been phase 3's round-2
mistake exactly. A test that **binds every source's fixed arguments against its handler's real
signature** found eleven more, nearly half the table. **The general lesson: when a review reports
an instance, write the test that enumerates the class.**

That led somewhere the plan had not looked. Five of the twelve needed a real-world argument — a
flight number, an origin, a city — which surfaced an **unpriced cost**: probing a live feed makes
a real third-party API call per question, every job, during Inquiry. § 14 never carried it. So the
seven outbound reads are declared `live: True` and are **never called by a probe**: availability
for a live feed *is* its registration, reported as a fifth probe state so it can never read as
`no_data` — "there is nothing there" about a source that answers every time it is asked.

**Decisions and their reasons.**
- **`turn_referent.is_exchange()` is the single definition of "a turn the user could be
  correcting"** — a trace carrying a `coordinator` — and both readers import it. The
  orchestrator's own copy of that scan is deleted. Rejected: fixing the referent block separately,
  which is the duplicated-rule trap phase 3 round 3 already paid for.
- **A scheduled session IS an exchange, for both readers.** The round-1 fix skipped anything
  `is_proactive`, so a correction of a specialist a *scheduled* session dispatched fell back to
  `coordinator` and was lost. The reviewer recorded that as "by design"; it was not. A scheduled
  session runs the full pipeline and the user can correct what it said.
- **A dry run is not budget-gated** (`writer._job_gate`). It writes nothing and costs nothing, and
  gating it is what turned a mid-call budget crossing into a terminal failure.
- **The landing day never counts toward a run rate**, nor does a day holding only Build's own
  ticks. Both produce `0.0` about a capability that has had no chance to be dispatched, and the
  window is now computed per capability from its own landing date.
- **`_expected_dispatches` returns `None`, not a proxy.** The Coordinator's turns per day is the
  same figure for every capability regardless of what filed it. The figure is owed to whatever
  phase gives a trigger an identity; the ACTUAL count is measured from day one and is the number
  that matters.

**Believed true earlier and wrong, and it is mine.** The phase-4 close-out report and the
`2026-09-19-04` fragment both said *"my test suite spent real money."* **No money was spent and no
API call was made.** The stub is a pure function; `spend_guard.record_tokens()` is local
bookkeeping — a price-table lookup and a JSON write. What broke was the METER, not the bank: fake
tokens wrote $12.53 into this Mac's daily ledger and tripped its $15 stop, so local sessions were
paused until the file was moved aside. The VM was never contacted. The compressed phrasing named
a cost that did not occur, which is the wrong direction to be wrong in; `0ae250b`'s commit message
carries it and cannot be rewritten, so this is the correction of record.

**Two items left open, both owned elsewhere and both already placed:**
`answer_interview_item` is granted to no agent — **phase 5's routing files**, which plan v3.5 C3
already put on § 16's phase-5 line. And The Book's rendering of a tick trace is **phase 7's
acceptance criterion**, which this session could not have run.

**Plan is at v3.7** — correction blockquotes for v3.6 (the fourteen) and v3.7 (the three) beside
v3.2–v3.5, with § 3, § 5, § 8, § 12 and § 14 updated inline.

**Not mine, in this tree:** a parallel chat's headset/APK work — `.gitignore`, `android/**`,
`core/{server,trace}.py`, `docs/INFRASTRUCTURE.md`, `scripts/{check_apk_sync.sh,renew_cert.sh}`,
`static/index.html`, `tests/test_turn_source_marker.py`. `git diff` each before staging.

**Commits: none** — phase 4 and the plan's corrections stay uncommitted by instruction.
**Deployed: NO.** One change worth knowing at deploy time: `tools/turn_referent.py` is not a
phase-4 file and changes behaviour on **every ordinary user turn**, so it ships with phase 4
rather than independently.
