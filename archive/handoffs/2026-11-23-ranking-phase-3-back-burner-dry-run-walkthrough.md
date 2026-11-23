Model: Sonnet 5.5 — a guided reading of a printed list; the judgement is Mike's, the session only prepares, asks and records.

# Ranking Part B, phase 3 — the back burner's dry run, one week (walkthrough)

**Who runs it:** Mike, on the VM, about a week after the phase 3 deploy (the commit that adds
`tools/ranking_review.py`, or later). **~10 minutes, one sitting.**

**What it decides:** whether the back burner may start parking. Once live:
- Small things nobody has mentioned for 21 days are parked: closed quietly, kept, and back the
  moment they come up again.
- Each one is said once in the weekly conversation the week before.
- Anything about a person, money or legal matters, health, a goal, or more than a small thing is
  never parked. It is asked about once in the weekly conversation instead.

(`archive/plans/ranking_values_plan_2026-11-23.md` § 4.11, § 11 row 15, § 11c.)

**The dry run needs no switch.** With `back_burner: false` (as shipped), the first tick after each
midnight writes what it *would* park to the trace and closes nothing. It also says nothing in any
conversation. The trace keeps 14 days.

**Pass**, all three:
1. Nothing under WOULD BE PARKED is something you would mind losing from view.
2. Nothing you would mind losing is missing from GUARDED.
3. Nothing under GUARDED is a thing you'd rather it parked quietly. That's not a fault, only a
   value to tune.

---

## The sitting (~10 minutes)

1. Check the VM has phase 3:
   ```
   cd ~/multi-model-mcp && git log --oneline -5
   ```
2. Today's reading, then two or three earlier days (any day in the last 14):
   ```
   .venv/bin/python scripts/ranking_report.py --back-burner --persona mike
   .venv/bin/python scripts/ranking_report.py --back-burner --persona mike --day YYYY-MM-DD
   ```
3. Read it:
   - **mode** — should say `dry run`.
   - **WOULD BE PARKED** — small things (worst cost minor, not judged vital) with no date still
     ahead, whose cost of delay is low, nobody has mentioned for 21+ days. "Mentioned" means:
     - you named it in your own words;
     - it was changed (a date, a note, its cost record);
     - or it was just opened.

     Metatron naming it does not count.
   - **CLOSE** — 14–20 days silent. Once live, these are said in the weekly conversation first.
   - **GUARDED** — would never be parked. The bracket gives why: `person`, `obligation`, `health`,
     `goal`, `weight` (more than a small thing, or judged vital), or `contacts unreadable`.
4. Answer the three pass questions, one row at a time if needed.

## After — the decision (the same session)

The session:
1. Records your answers in the plan as a new "§ 11c — dry-run review" sub-section.
2. **If it passes,** proposes in `config/modules/day_plan.yaml`, for your next deploy:
   - **Step 1:** `back_burner: true`, keeping `back_burner_dry_run: true`. The weekly conversation
     starts carrying the notices and guarded lines, but still nothing is parked. Watch one weekly
     conversation, then
   - **Step 2:** `back_burner_dry_run: false`. Parking goes live: each task is parked no sooner
     than 7 days after its notice was said. Within that week you can answer "keep it", give it a
     date, or let it go.

   **Revert:** `back_burner: false`, which is the dry run again. A parked task is brought back by
   mentioning it, or by `update_task … reopen`.
3. **If it fails:** each wrong row becomes a named change:
   - The wait is `back_burner.days` (21) and `notice_days` (14) in `config/modules/ranking.yaml`.
   - The cost floor is `back_burner.cod` (5).
   - A guard that missed something becomes a new guard, in code.

   Another week of dry run follows.
