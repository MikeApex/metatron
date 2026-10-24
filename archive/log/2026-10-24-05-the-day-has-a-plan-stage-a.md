### 2026-10-24, fifth (the day has a plan — the day planner's Stage A, shown in the Today panel, Synth not yet reading it) — `45739a2` — **committed; Mike deploys and rebuilds the APK after the close-out**

**Outgoing handoff carried:** the ritual-pause session (`archive/handoffs/2026-10-25-ritual-pause-and-ledger-followups-prompt.md`)
stays next in its own window; its undated "user-adjustable day boundary" item was built here.

**The need (Mike):** "Metatron's primary mission via Synth is telling the user what to do at any
given moment" — a hybrid code + agent process that keeps an ideal day current behind the scenes,
a cheap check before any full reshuffle, read by Synth every turn rather than asked for. Measured
first: nothing held a plan (the morning brief's sequence lived in one reply), and Synth could not
see the calendar at all — no calendar block, no calendar grant.

**Decided with Mike over three rounds (plan § 2, all binding):** the plan stores placements only
— ledger ids and calendar uids, never task state, so it cannot become a seventh store that
re-raises done items; priority and deadline stakes (vital / missable, stated / inferred) live on
the task; goal time is ledger habit tasks, informed by specialists once; code does as much as
possible, a model only refines the fill; repair (code, same reply) vs reshuffle (model,
background, with a testing heads-up); Synth gets the whole day and decides nudges and checks;
wake-and-decide nudges with a `[HOLD]` outcome, skipping the Coordinator; non-essential tasks get
no checks and end the day `unconfirmed` (F10); the first interview asks the day-shape questions
and location as an opt-out; Mark 1, now. Wearables deferred (Mike, offline).

**Built (Amber/Green only):** `tools/day_plan.py` (snapshot of every calendar, score, skeleton,
fill on a 5-minute grid, validator, digest-based gate, travel both ways with a cached, capped
Routes counter, suggestions, location evidence as a "Mark done?" card, model-reshuffle worker,
ticks), `tools/day_shape.py`, the ledger's fields, day boundary and unconfirmed rule, the
pipeline's plan block and nudge mode in both twins, the server's hold path, the Plan section,
the location default from the interview. Every Synth-facing part is off by flag
(`config/modules/day_plan.yaml`); Stage B's Red edits are drafted verbatim in
`archive/handoffs/2026-10-24-day-planner-stage-b-prompt.md`.

**Reviews:** the plan, three Fable rounds — twelve findings, all closed
(`archive/plans/adversarial_review_day_planner_plan_2026-10-24.md`); the diff, Fable —
eight defects plus one introduced by a fix, all closed and re-verified
(`archive/plans/fable_review_day_planner_stage_a_2026-10-24.md`).

**Believed true and wasn't:**
- **"Phone check-ins arrive as push."** The APK has no push — no plugin, and Android's WebView
  has no Push API; a scheduled message reaches the phone only over the live socket. Decision D1
  (plan § 14) is Mike's: recommendation, native notifications as a Stage C.
- **"Building while holding the plan lock is fine"** — a route lookup inside the build re-took
  the same `fcntl` lock on a second handle: a self-deadlock. Builds now run unlocked, writes are
  optimistic.
- **"A block that has started is history"** (the diff review's top finding): the task under way
  was placed again on every read, and its nudge and check never fired. Then the fix re-placed an
  unconfirmed essential task every time its block ended — eight blocks and eight wakes by noon.
  Now: history means ended, one re-placement and one check a day.
- **"The same-reply repair is wired"** — `note_calendar_write` had no caller; the test called the
  hook directly and passed. Wired into the three caldav write paths, pinned by source.

**Rejected:** storing priority anywhere but the ledger; a hash-only gate (it says that something
changed, never what — per-ref digests instead); duration-based location evidence (the log stores
only arrivals); a several-day Stage A watch (Mike chose one ordinary day, then Stage B — option 2).

**Found outside the build, not filed:** an amended reply crashes for a persona with no response
language (`core/orchestrator.py:7039`); background model jobs count as A9 user sessions; a
filter-suppressed scheduled turn still pushes a blank "New message".

