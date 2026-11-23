Model: Sonnet 5.5 — a guided reading of a printed summary; the judgement is Mike's, the session only prepares, asks and records.

# Ranking Part B, phase 2 — "behind" and raising what slips, in shadow, three days (walkthrough)

**Who runs it:** Mike, on the VM, on three mornings after the phase 2 deploy (`e134948` or later).
**~3 minutes each**, after the morning brief.
**What it decides:** whether `behind_v2` is switched on. Once on:
- On a day you are behind (3+ items overdue, or the top task skipped on 2 of the last 3 days), the
  day opens with up to two quick wins (20 minutes in all), the first ideally a small step of the
  hard task.
- A slipping task is raised when skipped twice or when it can no longer be done in time, and at
  most twice without anything new about it. After that it waits for the weekly list.
- At most 3 such prompts a day.

Today's rule asks about every slipped task once a day, every day.
(`archive/plans/ranking_values_plan_2026-11-23.md` § 4.10, § 11 rows 12–13, § 11b.)

**Pass**, on all three mornings:
1. "Behind" matches how the days actually felt.
2. On a behind day, the quick wins named are ones you'd happily start with.
3. The raises it would make are the ones you'd want, and none it drops is one you'd want raised.

**It can only flip together with, or after, `ranking_v2`.** Nothing in this walkthrough changes
anything. The report prints to the terminal and writes nothing.

---

## Each morning (3 minutes)

1. ```
   cd ~/multi-model-mcp && .venv/bin/python scripts/ranking_report.py --behind --persona mike
   ```
2. Read it:
   - **behind: YES / no**, with why: how many are overdue, and how often the top task was skipped.
     The top task is the day's highest-ranked one-off that fits in a day. A dose or a habit is
     never the top task.
   - On a behind day: the **hard task**, and the **quick wins** the day would lead with (noted when
     the first is a step of the hard task).
   - **would raise** — what the new rule would raise today; **to the weekly list** — what has been
     raised twice with nothing new and would wait; **Part A asks instead** — what today's rule
     asked about.
3. Answer three questions:
   1. **Were you behind this morning?** Does "YES / no" match how it felt?
   2. **On a behind day: would you start with those quick wins?** If not, which would you rather?
   3. **Raises: is anything it would drop one you want to hear about, or anything it would raise
      one you don't?**

## After morning 3 — the decision (a session, ~10 minutes)

The session:
1. Records the answers in the plan, § 11b (append a "Behind shadow" sub-section).
2. **Checks one thing you can't see**, needed before the flip: once `behind_v2` acts, a model
   reshuffle's placements can undo the lead (§ 11b, Fable #4). The session reads `behind.led` in
   that day's plan file after the flip, and if the day did not really lead with the quick wins,
   that is fixed before the flag is trusted.
3. **If the pass holds and `ranking_v2` is on (or flips with it):** proposes `behind_v2: true` in
   `config/modules/day_plan.yaml` for your next deploy. Revert is the same line set to `false`,
   which gives today's asks exactly.
4. **If it does not:** each wrong answer becomes a named value in `config/modules/ranking.yaml`
   `behind` / `raise` (the thresholds, the quick-win caps, the twice-without-news cap). Three more
   mornings follow.
