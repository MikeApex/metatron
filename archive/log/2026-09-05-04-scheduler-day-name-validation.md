### 2026-09-05, fourth (a mistyped scheduler day name stops being silent) — `core/scheduler.py`, `tests/test_scheduler_day_validation.py` (new), `DEV_BACKLOG.md`, `archive/backlog_closed_2026-09.md` — `7118972`, `28c2f21` + this close-out — **deployed by Mike in-session and verified on the VM**

The Red-tier prompt the third session left ready to paste, executed. `days: sun` matched
nothing on any day — `_is_active_day` compares against `strftime("%A").lower()` — so the job
never fired, with no error and nothing in the logs distinguishable from an ordinary "not an
active day" skip. That is how `weekly_clinical_review` shipped inert twice on 2026-09-03. The
doc half closed that day (`764d218`); this is the loud-validation build.

`schedule_key_error()` validates both keys: `days:` (plural, the firing gate, read every
attempt) and `day:` (singular, read once at registration, and it becomes a `schedule` library
attribute so it takes full day names only — there is no `schedule.every().weekdays`). Three
consumers: registration skips the job and logs an ERROR naming job, value and accepted forms;
`_gates_block` refuses it **ahead of** the day gate, so no firing path can report it as an
ordinary skip; `_report_invalid_schedules` re-reads the config hourly from the main loop.

**Decisions, with what was rejected:**

1. **Skip-loudly, not daemon-down** (the prompt's recommendation, confirmed on the code): one
   typo must not take down the other twenty jobs. The cost is that a skipped job is silent
   after its single registration line — which is exactly what this bug already was — so the
   hourly re-report exists to pay it back. **Hourly, not per 30s tick:** 2,880 lines a day is
   its own kind of silence. It re-reads from **disk**, not a registration-time cache, so a typo
   introduced while the daemon runs is caught without a restart; the live config is VM-owned
   and edited there.
2. **The hourly report prints only — it does not append to `scheduler_errors.json`.** Caught in
   my own diff after writing it: that file is a growing JSON array with no rotation, so an
   hourly append would add ~24 entries a day for as long as the typo stood. Registration writes
   the durable record once; journald rotates the rest. A cost decision made by accident in a
   parameter chosen for correctness, which is the standing rule.
3. **`_is_active_day` still refuses abbreviations**, per the item's own reasoning: accepting
   `sun` fixes one spelling and leaves the next mistyped key exactly as silent. It gained only
   **case normalisation** — a gap found while writing the validator: `days: Daily` failed the
   exact-match keyword branch and would have been this identical bug in new clothes.

**Evidence.** `tests/test_scheduler_day_validation.py`, 47 checks, standalone-script style (no
pytest), **confirmed failing on HEAD first**. Covers the bad value refused loudly, every
accepted form still passing, a `day:`-only weekly job registering untouched, agent-written jobs
validated on the same path, non-strings not crashing the validator, and the error repeating on
a second pass. Local: 47/47 plus `test_scheduler_gates.py` 23/23, `test_scheduler_quiet_hours.py`
and eight further scheduler-touching suites green.

**Verified in production, not inferred.** After Mike's deploy I checked the VM over IAP SSH:
registration at 12:14:53 shows **all 21 jobs registered with zero ERROR lines** — no false
positive against the live VM-owned `scheduler.yaml` or its three agent-written jobs, which was
the one thing the local suite could not answer — with `weekly_clinical_review: sunday at 11:00`
present, and the suite runs 47/47 against the deployed code. `[DB-0903-02]` closed and filed.

**Outgoing handoff (carried from `SESSION.md`):** the day's earlier state — thread identity
built, deployed and live; the extractor's direction ruled as teach-`rules:` with the
walkthrough prompt written; the confidence sweep's lever spent — is unchanged by this session.
What this removes from the "next, all Mike" list is item (3), the scheduler validation prompt.

