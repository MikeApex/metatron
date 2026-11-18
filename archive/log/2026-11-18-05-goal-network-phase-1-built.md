### 2026-11-18, fifth (goal–task network phase 1 built — steps wait on steps, the Red Book scheduled, finding #5, M2/M3) — `tools/{obligations,day_plan,horizon,day_plan_config}.py`, `core/orchestrator.py`, `config/modules/{day_plan.yaml,synthesizer_day_plan.md}`, tests — `98f158f` — **committed, NOT deployed**

**Incoming handoff:** `archive/handoffs/2026-11-18-goal-network-phase-1-build-prompt.md` — consumed.
Opus 5.5 built; Fable 5.1 reviewed the diff. No Red edits (synthesizer.md, routing and
`core/scheduler.py` untouched).

**Mike's rulings this session.** M2 shown with the 11-18 brief example; he asked what "new horizon
findings" are (the Logistics-filed things from mail/calendar not yet told), then said **yes**. Go-ahead
on the 11-step build with "hold Red prompts until absolutely necessary" — none was needed. He
checked mid-build that the plan had been Fable-reviewed: it had (§ 10, §§ 1–9); **§ 11–12 (M2/M3)
had not**, so the diff review was pointed at them.

**What changed, and why.** Plan § 13 has the full table. In short: `needs`/`part_of`/`required` on
tasks, `blocked` derived once per load in `_load_doc` (not passed to ~15 `_view` sites — one
forgotten site would leak, and every reader already goes through the loader); `open_plan`
all-or-nothing; R9 dismissal cascade with raise-once and reopen/reschedule restore; the Red Book
conversion in `refresh_tick` behind `prep_tasks`, linked by a new `prep_for` field — **not
`calendar_uid`, which would have ✓-marked Benny's session when the bag was packed**
(`_mark_calendar_done`); a `before` latest-end constraint in `_fill` for A1; finding #5 via
`shield_jobs:` with the scheduler's scan reused unchanged; M3 slips counted from stored day plans;
M2 findings ranked into Important; fcntl locks on both ledgers (reentrant — `flock` blocks a second
descriptor in the same process).

**Fable diff review: 4 structural + 5 local, all verified and fixed (plan § 13 F1–F9).** The ones
that would have shipped wrong: a prep left undone overnight placed after its event (F1); the shield
is `abs()`, so Mike's own 07:50-after-07:31 example was still dropped (F3); slip questions on
every turn (F2); a same-day finding held until it expired (F4).

**Wrong earlier, corrected here.**
- The first R10 test passed while proving nothing about the after-session case, and the reworked
  one **reached the live server through an unstubbed `send_one`** (rejected: "Persona not found:
  gn_phase1" — nothing delivered, no persona touched). Now stubbed. The standing stub-every-meter
  rule held in intent and failed in fact; push is a meter.
- A plan's end state has no `part_of` but is hidden while blocked, so R7b's "skip part_of rows" left
  the leak open for it; the guard skips blocked rows too.
- Undated one-offs are never placed (R4), so `open_plan` refuses them now rather than in phase 2.

**Tests.** `tests/test_goal_network_phase1.py` 34/34 (A1–A9, R1 two-process race, R7 readers,
R9, R10, M2, M3, each Fable fix); `tests/run_goal_network_fixtures.py` 7/7 personas; existing suites
green except two that **already fail on HEAD** (date-dependent: `test_task_ledger_consult` "later
dated event" — a 3 Nov fixture now past; `test_day_plan_round2` F8); `check_agent_tools` clean;
`qa_sweep` 12/12. Two suites pinned to `horizon_cap: false`, the uncapped path they test.

**Not done / owed:** deploy (Mike); the live checks (SESSION.md); confirm `mike`'s VM fixed-job names
match `shield_jobs` (`morning_brief`, `evening_close`, `location_anticipation`) — a conversational
job under another name would no longer shield.

