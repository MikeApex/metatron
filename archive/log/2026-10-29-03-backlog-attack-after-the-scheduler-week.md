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

**Second half, same session: Mike ruled on the four decisions and they were built** —
`97f9f09`, `226a0c2`, `24b4cb0`, `66b637c`, `8231a86`, `02b1e5b`. Each is **committed but not
yet deployed**; Mike deployed `da3d221` mid-session.
1. **A task can be deferred** (`66b637c`, an Opus worker). It's a separate `defer` action,
   because hiding a task and moving its date are different requests. It uses the existing
   `eligible_from`/dormant state, and every outstanding view already honoured that state
   except the thread and day-log annotations, which are now fixed. It's refused for habits
   (the nightly sweep would count the hidden days as missed) and refused past a deadline's
   own date, rather than warning, because a warning lands in a tool result the user never
   sees. `8231a86` adds one line each to `synthesizer.md` and `logistics.md`. **Open for
   Mike:** `reopen` doesn't bring a deferred task back early.
2. **The check-in wording: the planned fix was wrong, and the real cause was the live
   prompt.** `synthesizer_scheduled_sessions.md:7` has said "when there is genuinely
   nothing, say so in a line and ask what's on" since 08-27, so a rule in `synthesizer.md`
   would have been a second copy. The VM's `companion_checkin` prompt, *"raise it only if
   something matters right now"*, is now sent only on an empty day. `226a0c2` keeps that
   prompt verbatim, because `session_kind()` matches on it, and appends "nothing is
   planned — ask what's going on". That's an Amber change, not the Red one that was
   approved, and Mike was told.
3. **False "set/queued/lined up" claims** (`24b4cb0`, an Opus worker). The new phrasings
   went into the log-only pattern set, not `_COMPLETION_CLAIM_RES`, which rewrites replies.
   A plan row exempts a claim only on a shared title word plus a matching start time. A time
   alone would have exempted the 10-27 incident itself, since its 16:30 row was a return
   trip. The check reuses the plan read that replies already make on every turn, so it adds
   no new cost.
4. **Quiet hours** (`97f9f09`, Red, built here). Mike's ruling: a reminder he asks for
   inside quiet hours fires there only if he approves a card that says so; otherwise it, and
   any agent follow-up, waits until quiet hours end. This reverses the 2026-08-15 automatic
   permission. **A Fable review found that the card broke the reply** (`02b1e5b`): the
   pending-receipt machinery assumes every card gates the whole action, so "that's
   scheduled" was replaced with "nothing has been changed yet", and the Diarist was told
   the reminder wasn't set. Cards in `_PENDING_INFORMATIONAL` are now excluded. Three
   smaller review fixes went in with it:
   - a one-tick window at 22:00 where a follow-up could still be lost;
   - a card headline that read as a question;
   - the decision that a follow-up is due "while awake" is now made once, in the loop.

**Worker costs, estimate vs actual:** the defer worker used 119.0k tokens against ~65k (it
read every outstanding-list surface); the claims worker 95.3k against ~65k; the Fable review
83.2k against ~50k. All three ran over; the build medians in `worker_ledger` are too low for
items that have to survey every caller.

**Close of session.** Mike chose (b): `9e57655` lets `reopen` bring a deferred task back early,
restoring whatever `eligible_from` held before (`tests/test_task_defer.py` 10/10; the new
check fails without the fix). Three more Inbox entries closed as already fixed by other work:
- **Shared calendar invisible:** fixed by `fccbc1e` (10-24, every calendar read). Live
  evidence is the "Shared with Mike" events in the 10-27 plan.
- **Iva's invitations "not dispatched", two entries:** they are sent by email. The
  Google-side remainder is the Mark 2 item.

Inbox 33 → 27 over the session. **Not deployed:** everything after `da3d221`
(`97f9f09`…`9e57655`).

**Deployed by Mike after the close-out.** VM, GitHub and the Mac are all at `976c85e`;
the server and `metatron-scheduler@mike` are active, and `allow_in_quiet_hours` is present on
the VM. The deploy pushed the parallel session's `8dcb290` too, by Mike's action, not this
session's. **Outgoing handoff:**
`archive/handoffs/2026-10-30-backlog-overdue-checks-triage-and-deep-prompt.md` (Opus):
1. overdue checks on the VM;
2. triage of the 10 untriaged Inbox entries;
3. as a carry-on, `/backlog deep` of `## Later`, gated on the 11-05 routing-miss re-count.

