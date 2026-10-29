### 2026-10-29, third (`/backlog attack`: ten items re-checked against the scheduler and task-ledger week; the day plan now says when the calendar can't be read) — `tools/day_plan.py`, `tests/test_day_plan_calendar_error.py`, `DEV_BACKLOG.md`, `archive/backlog_closed_2026-10.md` — `f10ba3d`, `5a2f4e8` — **committed, not deployed**

**Incoming handoff:** unchanged from § 2026-10-29 second. This session did not touch Stage 5,
the step-2 checks or reply latency.

**Prompt (Mike):** `/backlog attack`, plus a check that the fixes in the backlog are still
relevant after the week's scheduler and task work. ## Now held only two items, so the session
also ran a read-only verify over the eight Inbox/Later items most exposed to the ~20
scheduler, ledger and day-planner commits since 10-21. Three Sonnet workers did it (50.5k,
58.0k and 57.2k tokens against ~60k estimated). Every verdict came with a file:line, and I
re-read the two that carried the most weight.

**Correction, raised by Mike ("some of these seem superseded… explain what I'm missing").**
The first verdict table compared every item against the code and treated `owns_checkins` and
`nudges` as old, settled code. In fact they had been switched on that morning (`3d3524a`), and
all of the items' evidence predated them. Re-read with that in mind:
- **The routing-miss noise from scheduled sessions `[DB-0902-01]`:** most of the 114 events
  came from the fixed `companion_checkin` job, which the plan now suppresses. Cluster B (a
  logger guard) was dropped. The item is now `@waiting` with `due: 2026-11-05` to re-count;
  the guard stays cheap if it's still needed.
- **Plant watering ×2:** closed. On the VM, `plant_watering_check` is gone and has been replaced
  by a ledger interval task (`ob_261024_177765`), and Mike's "it's raining" was recorded as a
  completion. An automatic rain check is not built; I offered to file it and did not.
- **Adjustable day boundary:** closed. It's built and switched on; it needs only a first live
  use.
- **"Dinner prep queued for 16:30": my hypothesis was wrong.** I thought the claim might have
  been backed by the plan. The VM's `plan_2026-10-27.json` has no dinner-prep row, so both
  examples are genuine false claims. The item stays, now with a constraint: the fix must not
  flag a claim that the plan's real reminders back up.

**Built: cluster A, the calendar-down item `[DB-0910-02]`, plan half (`f10ba3d`).** The
planner had made this item worse. The plan block calls itself "authoritative for timing", yet
on a failed calendar read it showed stale events, or an empty day, with no warning. It now
says the calendar couldn't be read and when it was last read. The test has 4 checks, 3 of
which failed on the old code; the day-plan suites still pass 105/105. The Opus worker used
70.3k tokens against ~65k estimated.
**Found, still open:** a CalDAV 401 comes back as an `{"error": …}` dict. The orchestrator turns it into
JSON text, so `_failed_tool_calls` never fires and the trace says `ok: true`. The Logistics
path is therefore still blind. This was recorded in the item as its remaining half rather than
filed separately.

**Red work identified and not done:** keeping a promised follow-up through quiet hours
(`core/scheduler.py`), and the quiet check-in wording (`synthesizer.md`). Both are open in
`DEV_BACKLOG.md`.

**Mike's decisions still open, put to him:**
1. Should deferring a task be its own action?
2. The check-in rule's home.
3. Widen the false-claim phrases and skip the ones the plan backs.
4. Rank the deleted-follow-up bug in ## Now at #1.

