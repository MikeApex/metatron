# Handoff — intake confidence sweep (2026-09-05)

**What ran.** Pulled the 33-message corpus from the VM (gitignored, still uncommitted), re-ran the
code tier locally, then ran the extractor path **five clean times** with a new per-message
confidence dump and swept thresholds 0.0 → 1.0. Report:
[intake_confidence_sweep_2026-09-05_gemini-flash-lite.md](../../tests/intake_confidence_sweep_2026-09-05_gemini-flash-lite.md).

**Recommendation: do not enable the floor.** The lowest threshold with zero worst-run
`action_required` false negatives is **0.95**, and it demotes **85% of the corpus (28/33)** to
`unclear`. Everything ≤0.90 still silences an obligation on the worst run. One `action_required`
message is misread in all five runs at confidence 0.80 — the same value the correct calls report —
and a second is *more* confident when wrong (0.9) than when right (0.8). Confidence is not the lever.
With the floor off the model says `unclear` **zero times in 33**, confirming Mike's objection that
`unclear` has to come up more before the gate means anything.

**Also measured.** Code tier still resolves **1/33** — not a contradiction of forward unwrapping:
the fixtures already carry unwrapped senders, but persona `mike` has `rules: []` on both machines
and the eval runs with an empty ledger by design. Confidence is now supplied on **100%** of answers
(was 39% omitted), so `require_confidence` costs nothing.

**The one that matters beyond this item.** A `--runs 5` sweep is 165 calls against a 60/hour
in-process spend-guard cap. Runs 3–5 were refused wholesale, every message fell to `unclear`, and
because `unclear` is a gate pass the runner **printed 0 gate misses for three runs the model never
saw**. This also retro-explains 2026-09-04's "run 3 of every variant collapsed to 32/33 unclear" —
the guard, not a transient API failure, so that session's third-run data is void. The runner now
detects the condition and marks such runs INVALID instead of scoring them. Guard not lifted;
`config/` untouched.

**What [DB-0820-03] still needs.** Mike's flip decision, now with evidence pointing at "keep it
off". Two follow-ups: the corpus has 4 `action_required` fixtures and no `bill_statement` at all;
and the two specific messages the model misreads are worth fixing at the agent-file boundary rather
than by filtering output.

**Files touched.** `tests/run_intake_eval.py` (`--dump-confidence` + guard-refusal detection, both
additive), the report above, this handoff. Nothing flipped, nothing deployed, nothing under
`config/` or `core/` changed.
