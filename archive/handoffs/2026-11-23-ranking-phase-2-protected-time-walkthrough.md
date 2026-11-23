Model: Sonnet 5.5 — a guided reading of a printed table; the judgement is Mike's, the session only prepares, asks and records.

# Ranking Part B, phase 2 — protected time in shadow, three days (walkthrough)

**Who runs it:** Mike, on the VM, on three days after the phase 2 deploy (`e134948` or later).
**~3 minutes a day**, in the evening, after the day's protected windows have passed.
**What it decides:** whether `protected_v2` is switched on. Once on, a task gets into family time,
rest or exercise only if letting it slip would cost more than the intrusion does, and only after
you say yes. Today's rule lets any essential task in when nothing else fits, and says why.
(`archive/plans/ranking_values_plan_2026-11-23.md` § 4.5, § 11 rows 10–11, § 11b.)
**Pass:** on each day something took protected time, you agree with what the shadow says it would
have done — *asked* you, or *kept it out* — and no question it would have asked is one you'd call
needless.

**It can only flip together with, or after, `ranking_v2`** (it reads that ranking's cost of delay).
Nothing in this walkthrough changes anything. The report prints to the terminal and writes nothing.

---

## Before day 1 — once, right after the deploy (1 minute)

1. On the VM: `cd ~/multi-model-mcp && git log --oneline -1` — the commit beginning "Nothing you
   see changes yet: family time, rest and exercise…" (or later).

## Each evening (3 minutes)

1. ```
   cd ~/multi-model-mcp && .venv/bin/python scripts/ranking_report.py --protected --persona mike
   ```
   (`--day YYYY-MM-DD` for an earlier day; 14 days are kept.)
2. Read the **SHADOW** rows — one per task today's rule placed in protected time:
   - the window's class (family / rest / own / exercise) and **k**, how many recent intrusions
     into that kind of time it counts (1 = none recent; they fade by half every 3½ days);
   - **intrusion** — what giving up that time costs; **delay** — what the task's delay costs;
   - **→ ask** — the new rule would have asked you first (and what it would have suggested), or
     **→ keep_out** — it would have kept the task out and asked nothing.
   No rows means nothing took protected time today. That is a day with nothing to judge, not a
   failure. Carry on until three days have rows, or a week has passed.
3. Answer two questions, and say them in a Claude Code session or jot them down for one:
   1. **For each row: was the shadow right** to ask, or to keep it out? *"Right — I'd have said
      yes to the tax return"* / *"Wrong — that call could have waited, keep it out."*
   2. **Would any question have been needless or badly timed?** (It would arrive as a nudge an
      hour before the window, and on the brief's Asks line.)

## After day 3 — the decision (a session, ~10 minutes)

Bring the answers. The session:
1. Records them in the plan, § 11b (append a "Protected-time shadow" sub-section).
2. **If the pass holds and `ranking_v2` is on (or flips with it):** proposes the one-line flip,
   `protected_v2: true` in `config/modules/day_plan.yaml`, committed for your next deploy. Revert
   is the same line set to `false`, which gives today's rule exactly.
3. **If it does not:** each wrong row becomes a named value in `config/modules/ranking.yaml`
   `protected`: a class's base, the exponent, or the half-life. Three more days follow.

**What the session also reads, not you:** `trace.protected` in
`data/personas/mike/day_plan/ranking_state.json` has the same rows by task. Once the flag acts,
`trace.intrusions` has every question and its decision.
