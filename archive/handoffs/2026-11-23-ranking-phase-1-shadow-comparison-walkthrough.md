Model: Sonnet 5.5 — a guided reading of a printed table; the judgement is Mike's, the session only prepares, asks and records.

# Ranking Part B, phase 1 — the three-morning shadow comparison (walkthrough)

**Who runs it:** Mike, on the VM, three mornings after the phase 1 deploy. **~5 minutes each.**
**What it decides:** whether `ranking_v2` is switched on — the day ranked by the regret of delay
instead of Part A's score (`archive/plans/ranking_values_plan_2026-11-23.md` § 5, § 7.2 item 2).
**Pass:** Mike prefers the new order on **at least 2 of the 3 mornings**, and on none of them does
an obligation he calls real sit below the cut.

Nothing in this walkthrough changes anything. The report prints to the terminal and writes nothing.

---

## Before morning 1 — once, right after the deploy (2 minutes)

1. Confirm the deploy carries phase 1: on the VM,
   `cd ~/multi-model-mcp && git log --oneline -1` — the commit named "the new ranking runs beside
   the old" (or later).
2. Confirm the judge recorded costs (it runs off the scheduler tick within ~10 minutes of the
   restart, ~2–3 calls for `mike`, ~$0.04):
   `grep '"task_judge"' data/personas/mike/day_plan/log.jsonl | tail -3`
   — pass: `"outcome": "judged"` with `judged` > 0. If `"failed"` or nothing at all after 30
   minutes, stop and bring the line to a session: the comparison would be reading fallbacks.

## Each morning (5 minutes)

1. After the morning brief has arrived (the day has been built at least once since waking):
   ```
   cd ~/multi-model-mcp && .venv/bin/python scripts/ranking_report.py --compare --persona mike
   ```
   It reads the day's first build after waking. `--live` instead computes both orders from the
   ledger as it is right now.
2. Read the two lists:
   - **PART A** — what actually ran your day: the score Part A gave each task.
   - **REGRET OF DELAY** — what the new ranking would have done. **MUST** = on today's list, or
     must start today to be done in time. **ADV** = advance work it would have *suggested* for
     spare room. Per row: `G` (how much missing it would cost, 0–100), `×` (who bears it),
     `shape` and `factor` (how the cost of a day's delay is growing today), `slack` (days to
     spare, after the start-late buffer), `blocks` (attention), `cost` (the cost of one more
     day's delay). A row marked **(fallback)** has no cost record yet — it is read from Part A's
     vital/missable.
   - The last line says whether the new ranking would have **reshuffled** on this build.
3. Answer three questions — say them in a Claude Code session, or jot them anywhere and bring
   them to one:
   1. **Which order is right for today — A, the new one, or neither — and why?** (One sentence is
      enough: *"the new one, because Dad is overdue and the permit isn't"*.)
   2. **Is anything you'd call a real obligation below the cut** — missing from the new list, or
      so low it would not have fitted the day?
   3. **Is any grade wrong?** (A `G`, a bearer, a shape.) A wrong grade is corrected in chat —
      *"the gas bill is a major financial cost, not minor"* — and the Synthesizer records it as
      stated.

## After morning 3 — the decision (a session, ~10 minutes)

Bring the three answers. The session:
1. Records them in the plan, § 11 "Phase 1 built" (append a "Shadow comparison" sub-section).
2. **If the pass holds:** proposes the one-line flip — `ranking_v2: true` in
   `config/modules/day_plan.yaml` — committed for your next deploy. The file is re-read when it
   changes, so it takes effect on the next build after the pull. Revert is the same line, `false`:
   Part A exactly.
3. **If it does not:** each "wrong" morning becomes a named value to change in
   `config/modules/ranking.yaml` (the shadow shows which term moved the task — `G`, the factor,
   the slack, the blocks), and three more mornings follow.

**What the shadow also measures, read by the session, not by you:** how often the new ranking
would have reshuffled (`grep v2_would_reshuffle data/personas/mike/day_plan/log.jsonl`) — the
ancillary cost § 8 asked the shadow to measure before `reshuffle_delta` is trusted.
