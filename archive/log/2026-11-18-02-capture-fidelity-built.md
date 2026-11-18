### 2026-11-18, second (capture fidelity — planned, built, Fable-cleared, measured on mike; Iva's data given mike's clearances) — `b9703a5`, `908af58`, `a7a3402`, `7decf28`, `f2984df` — **VM at `7decf28` (deployed by Mike); `f2984df` not yet deployed; `capture.yaml` `enabled: false`**

**What it does.** When a user states a fact and no agent keeps it, the agent that should have is
shown it. A bulk-tier `capture_extractor` (code-only, empty grant) reads each real user turn.
Code compares what it found against what the turn wrote, by value: a seven-day dinner against a
weekday one is a mismatch, not a save. Ordinary turns: it runs beside the Coordinator and the
note reaches the Synthesizer's single pass, with no added latency. Interviews: a before/after
record diff, shown on the next turn's coverage block. **The agent stays the only writer** (Mike).
Also built: a content-free outcomes log, a weekly table for the future Observer, a holdout,
`--backfill / --rematch / --label / --score / --eval`, and per-writer `modes`.
Plan `archive/plans/capture_fidelity_plan_2026-11-18.md`.

**Mike's rulings.**
1. v1 covers both writers.
2. The extractor proposes and the agent writes. Whether a capture layer becomes the writer is
   decided at the agent rewrite, from the accept rate.
3. An ambiguous fact is an `ask`.
4. Bulk tier.
5. A weekly report, built for the Observer.
6. Labels are guessed by the tool and corrected by Mike, **in a chat**
   (`archive/handoffs/2026-11-18-capture-labels-in-chat-prompt.md`, next).
7. Thresholds raised to precision 90%, recall 80%, matcher 90%, accept 75%, live miss ≤ ¼ of
   baseline, then benchmarked from measured results.
8. No rehearsal account.
9. Shown once.
10. **Ordinary turns ship in shadow, interviews on.**
11. **Iva's data carries exactly mike's clearances, universally.** Recorded in `ROADMAP.md` § 0
    (amendment 11-18), `CLAUDE.md`, review #11 (ruled, no build), and the routing and
    `crm_sweep` comments.

**Fable, three rounds.** It cleared six plan findings and four build findings. The top one: the
Synthesizer writes after the note, so its unprompted behaviour was unobservable; fixed with a
holdout.

**Believed true and wasn't.**
- **"The planning session can measure the interviewer now."** The trial accounts' data was purged
  10-29, and mike has never run in interview mode. The trial_1029 fixture is authored from
  paraphrase.
- **`_spend_gate()` was a safe gate for the extractor.** It also counts a session against the
  60-an-hour stop, so an interview turn counted twice and the backfill would halt at its 60th
  call. Fixed in `908af58`. I first said this would block the server; the counter is per-process,
  so it could not.
- **The first backfill's ~90% miss rates.** These were my matcher, not the agents. It counted only
  each kind's own tool, but Logistics files tasks as obligations, calendar entries, archive items,
  horizon items and schedules, and the Diarist files preferences as wisdom. 311 of 471
  "user turns" were the Diarist's runs and morning intake jobs. Re-scored with `--rematch`: 160
  real turns, 18 candidates, **15 of 18 already kept**. Live, the old matcher would have pushed
  duplicate saves.
- **The same finding, outside capture.** A9's `user_sessions` counts those Diarist and intake
  traces, roughly a 3× inflation of the attention denominator. Flagged to Mike, not changed, and
  not filed: it is his call under § A9a.

**Rejected.**
- A code-only pre-hint for the interviewer: a second mechanism for no gain at a one-turn lag.
- A 150-day rerun (Mike: the history is thin).
- The reasoning tier, unless the labels fail.

**Process slip.** A `git stash` used for a before/after test also held another window's
uncommitted Android and Build Inquiry work. It was restored byte for byte; don't do it again.

**State for the primer (to fold in at the labelling chat's `/archive`; `SESSION.md` was dirty
from a parallel Mark 2 window, so it was not touched here):**
- Capture fidelity is built. The VM runs `7decf28`; `f2984df` (modes) is undeployed; capture is
  off. The eval on the authored trial turns returned 6/7 exact, the seventh still an ask.
- **Next:** label in chat with the prompt above, then the switch decision and deploy, then the
  live checks, then Iva's interview as the interviewer's first live run.
- At mike's volume (~2.7 real turns/day, one fact per ~9), the live gate cannot be measured; the
  § 5.3 bars apply when a shadow writer is switched on.

