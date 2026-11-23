### 2026-11-23, ninth (ranking Part B phase 1 built — the regret-of-delay ranking runs beside the old one in shadow, and every task starts recording what a delay would cost) — `05f3110` — **committed, NOT deployed**

**Incoming handoff:** `archive/handoffs/2026-11-23-ranking-part-b-phase-1-build-prompt.md`
(Opus 5.5, high) — consumed. The outgoing primer said *"Next: phase 1, in shadow … the flag flip
waits for Mike's three-morning comparison."*

**Built (plan § 11a has the full list):** `config/modules/ranking.yaml` with every § 11 value cited
to the research; `tools/ranking.py`; the cost record in `tools/obligations.py` behind
`cost_record` (**on** in the committed yaml, so the deploy starts recording); the judge records it
in its existing pass; `_candidates_v2`, hard-first, the shadow and `scripts/ranking_report.py
--compare` in `tools/day_plan.py`; Red edits to `task_judge.md` and `synthesizer.md` made in this
session. Tests: `tests/test_ranking_v2.py` 26/26, Part A's `tests/test_task_ranking.py` 21/21 with
the flag off, and every ledger, planner and judge suite unchanged. The two failures already on
clean HEAD remain: round-2 F8, and `task_ledger_consult`'s 3 November date.

**Decisions taken in the build (Mike approved the list before work began):**
1. Implied promise dates are derived on read, not stored by `open_task`. `bears` usually arrives
   from the judge later, and a stored `due` would show on the Today list before the flip.
2. A fifth bearer, `own_org` (weight 1.0), for a business the user owns.
3. The social × 1.5 weight is capped at a 0.99 share. Social still outranks financial at every
   grade, but the gap narrows at severe (99 vs 90).
4. `free_minutes_per_day: 120` turns a task's length into days (heuristic, measured by the shadow).
5. Stage only this session's hunks. The other window's name scrub committed as `388a91c`
   mid-session, so the separation was moot.

**Believed true earlier, wrong (found by the first test run):** setting the climb window to the
task's own need, as § 4.10 first read, would have put nothing more than a day ahead above the
advance floor. Musts cost their whole weight whatever the window, so it orders advance work only.
It is now the 14-day look-ahead, with `advance_floor` at 10: a minor is never pulled forward.

**Fable 5.1 diff review: 13 findings, reconciled in plan § 11a.**
1. Fixed:
   - a stated vital stays vital under v2
   - a judge reply with no costs writes no record
   - a record that fails twice is not offered again, so one bad task can't spend the daily cap
   - old promises are graced from the day they were recorded, not opened
   - hard-first stays within a tier
   - advance work is never on the Important line
   - the people offer no longer labels a code-chosen grade as stated
   - a moot cliff is never a must
2. Kept or deferred with reasons:
   - **Buffer learning is built but OFF**: in shadow every long task would train "starts late"
   - fractional attention blocks
   - undated goal steps as advance work, and showing the implied date: phase 2
   - **the `request_replan` R9 sentence is live flag-off. Mike: keep (2026-11-23)**

**Rejected:** a separate judge call for cost records. One call with a per-task `want` costs the
same cap and the same output budget (~3k of the 5k ceiling for 25 tasks), and keeps stakes judging
first in each batch.

**Next:** at Mike's next routine deploy, `cost_record` goes live (one judge pass, ~$0.04 for `mike`)
and `ranking_v2` stays off. Then three mornings of
`archive/handoffs/2026-11-23-ranking-phase-1-shadow-comparison-walkthrough.md`. The flip needs v2
preferred on ≥ 2 of 3 mornings, with no real obligation below the cut. Phase 2's prompt is
`archive/handoffs/2026-11-23-ranking-part-b-phase-2-build-prompt.md` (Opus, high).

**After the close-out (same session):** Mike deployed. On the VM at 14:06, `task_judge` recorded
costs for 21 of the 21 tasks offered, in one call, so `cost_record` is live and the shadow reads
real records. **Mike then deferred the three-morning comparison to the backlog so other builds can
go ahead** (`396698d`). It gates only the `ranking_v2` flip, not phase 2. The phase 2 prompt's
precondition was loosened to match: build on whatever `ranking.yaml` holds, since every value is
config. Mornings are kept 14 days, so the comparison can be read in one sitting with `--day`, by
about 2026-12-07.

