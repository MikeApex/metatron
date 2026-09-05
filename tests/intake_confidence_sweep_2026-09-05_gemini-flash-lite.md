# Intake extractor — confidence-vs-correctness sweep

**Date:** 2026-09-05 · **Model:** Flash-Lite (`complexity="quick"`, production path, `bare=True`)
**Corpus:** 33 hand-labelled real messages, `tests/intake_fixtures/` (VM copy, gitignored)
**Runs scored:** 5 clean (each its own process — see § Spend guard)
**For:** [DB-0820-03] — the evidence Mike's flip decision needs. Nothing was flipped or set.

---

## The answer first

**The confidence floor cannot open this gate.** The lowest threshold that produces zero
`action_required` false negatives on the worst run is **0.95**, and at 0.95 **85% of the corpus
(28/33) demotes to `unclear`** — the user gets their inbox handed back, which is the failure the
dial exists to avoid. Every threshold cheap enough to be worth having (≤0.90) still lets an
obligation through on the worst run.

**Recommendation: leave `extractor.enabled: false` and leave `confidence_threshold` at 0.**
Self-reported confidence was the chosen lever after "counterargue" was ruled out; on this corpus it
is not a lever. The next move is a different mechanism, not a different number.

---

## The curve

Five clean runs, identical corpus and agent file. Gate = an `action_required` message classified as
anything other than `action_required` or `unclear`. Scored on the **worst** run, never the mean.

| threshold | r1 | r3 | r4 | r5 | r6 | **worst FN** | worst `unclear` | gate |
|---|---|---|---|---|---|---|---|---|
| 0.0 (off) | 1 | 1 | 2 | 1 | 1 | **2** | 0/33 (0%) | fail |
| 0.50 | 1 | 1 | 2 | 1 | 1 | **2** | 0/33 (0%) | fail |
| 0.70 | 1 | 1 | 2 | 1 | 1 | **2** | 0/33 (0%) | fail |
| 0.75 | 1 | 1 | 2 | 1 | 1 | **2** | 2/33 (6%) | fail |
| 0.80 | 1 | 1 | 2 | 1 | 1 | **2** | 2/33 (6%) | fail |
| 0.85 | 0 | 0 | 1 | 0 | 0 | **1** | 17/33 (52%) | fail |
| 0.90 | 0 | 0 | 1 | 0 | 0 | **1** | 18/33 (55%) | fail |
| **0.95** | 0 | 0 | 0 | 0 | 0 | **0** | **28/33 (85%)** | **pass, unaffordable** |
| 1.00 | 0 | 0 | 0 | 0 | 0 | **0** | 30/33 (91%) | pass, unaffordable |

Verification (step 6): re-scoring all five captured runs with the floor applied at 0.95 gives
worst-run FN = 0. The gate passes there and only there. That is a real pass and a useless one.

**Note the top row.** With the floor off, the model says `unclear` **zero times in 33 messages, in
every one of five runs.** Mike's standing objection — *"unclear needs to come up more for this to
have any validity"* — is confirmed exactly: this classifier never declines. The floor is the only
thing that can make it decline, and it can only do so by declining almost everything.

## Why the dial does not work here

The floor demotes by confidence, so it helps only if wrong answers report lower confidence than
right ones. Across 160 model answers:

| | n | mean | median | range |
|---|---|---|---|---|
| correct | 111 | 0.882 | 0.90 | 0.80 – 1.00 |
| wrong | 49 | 0.799 | 0.80 | 0.70 – 0.90 |

There is real separation in aggregate — **no wrong answer ever exceeded 0.90**, and only correct
answers reached 0.95/1.00. That is precisely why 0.95 achieves a perfect gate, and precisely why it
costs everything: 0.80 and 0.90 are where the model puts nearly all its answers, right and wrong
alike (37 correct at 0.80 against 37 wrong at 0.80).

The four `action_required` fixtures, per run:

| fixture | r1 | r3 | r4 | r5 | r6 |
|---|---|---|---|---|---|
| `0c7cc053` | ✓ 0.8 | ✓ 0.8 | ✓ 0.8 | ✓ 0.8 | ✓ 0.8 |
| `a30a3e53` | ✓ 0.8 | ✓ 0.8 | ✓ 0.8 | ✓ 0.8 | ✓ 0.8 |
| `a9b98c3f` | ✓ 0.8 | ✓ 0.8 | **✗ notification 0.9** | ✓ 0.8 | ✓ 0.8 |
| `d98ac74e` | **✗ correspondence 0.8** | ✗ 0.8 | ✗ 0.8 | ✗ 0.8 | ✗ 0.8 |

Two failures, two shapes, neither reachable by a threshold:

1. **`d98ac74e` is wrong in all five runs at exactly 0.80** — the same confidence the two *correct*
   `action_required` calls report in all five runs. No threshold separates them: anything that
   demotes the miss also demotes both hits. This is not variance; it is a message the model reads
   consistently and consistently wrong.
2. **`a9b98c3f` is wrong in 1 run of 5, and is MORE confident when wrong** (0.9) than when right
   (0.8). On this message the signal is inverted, so the floor actively prefers the error.

## Missing confidence now costs nothing — the 39% hole is closed

The `require_confidence` rule (a missing field fails the floor) was sized against a 39% omission
rate measured 2026-09-04, before the production agent file asked for the field.

**Re-measured across 160 clean answers: the field was omitted 0 times.** `effa68a` closed the hole
completely. `require_confidence` therefore contributes **zero** demotions on this corpus and is now
free — keep it on, since it costs nothing and still guards a model that stops complying.

*(An earlier pass of this report put the omission rate at 3%. That was wrong: those four rows came
from the poisoned run described below, where the model was never called. Refusals do not report
confidence, and counting them as omissions overstated the rule's cost.)*

## Code tier, re-measured

**1/33 (3%)** classified without a model — unchanged from the figure believed stale.

The expectation was that forward unwrapping would raise this: `effa68a` reported 18/33 messages are
self-forwards and that five taught sender rules would resolve 9/33. It does not appear here, and
the reason is not the unwrapping — **the fixtures already carry unwrapped senders (19 distinct
senders, the post-unwrap figure), but the persona has no taught sender rules to match them.**
`load_config('mike')` returns `rules: []` on this Mac *and* on the VM, and the eval deliberately
runs with an empty ledger (`ledger={}`) so the corpus scores the rules as shipped rather than one
mailbox's accumulated history.

**So 1/33 is the honest zero-token fraction for the eval, and it does not contradict the unwrapping
work — it measures a different thing.** Confirming 9/33 needs a live-mailbox measurement, not this
runner.

## Spend guard: three runs scored as passes without the model being called

The first sweep was `--runs 5` in one process. The rate guard counts every extractor call as a
pipeline session in an in-process deque and stops at `stop_sessions_per_hour: 60`. 33 fixtures × 5
runs = 165 calls, so:

- run 1 (32 calls) clean;
- run 2 poisoned from its 29th message — calls 61+ refused;
- runs 3–5 refused **entirely**.

`extract()` turns any failure into `unclear` by design. `unclear` counts as a gate pass by design.
The two correct behaviours composed into a runner that **printed `0` gate misses for three runs in
which the model was never called at all** — the best-looking result in the sweep was the one with
no data in it.

**This retro-explains the 2026-09-04 A/B/C observation** that "run 3 of every variant collapsed
identically to 32/33 unclear", attributed then to a transient API failure. It was the guard, and it
was deterministic: run 3 is exactly where a 33-message corpus crosses 60 calls in one process. Any
conclusion drawn from a third-or-later run in that session should be re-examined.

Handled here by discarding runs 2–5 and re-running as five separate single-run processes (the
counter is per-process, so each invocation resets it). **The guard was not lifted and
`config/modules/spend_guard.yaml` was not touched** — it is a safety net and not this runner's to
move.

`tests/run_intake_eval.py` now refuses to score a run it cannot afford: `_guard_state()` checks
headroom before each scored run and returns a distinct **INVALID** status (exit 3) rather than a
clean-looking zero. Invalid runs are excluded from the worst-run gate instead of being averaged
into it.

## Runner changes (both additive)

1. **`--dump-confidence PATH`** (requires `--extractor`) — one JSONL row per model-answered message:
   run, file, category, confidence, domain, important. Makes a threshold sweep cost one set of API
   calls instead of one set per candidate. Rewritten after every run, so a sweep that dies keeps
   what it already paid for.
2. **Spend-guard refusal detection** — described above.

## Caveats

1. **The corpus is 33 messages with 4 `action_required` fixtures.** The gate's entire denominator is
   four messages. One relabelled fixture moves every number in the table.
2. **`bill_statement` is untested** — the corpus contains none, so a whole category is unmeasured in
   both directions.
3. **Run variance is real** — worst 2, best 1 false negatives at threshold 0 across five clean runs,
   consistent with the 1,3,1,1,2 seen on 2026-09-04. One run proves nothing here.
4. **Any earlier result from a run past call 60 of its process is void**, including part of
   2026-09-04's A/B/C data.
5. Thresholds were evaluated at the granularity the model actually emits (0.7, 0.75, 0.8, 0.85, 0.9,
   0.95, 1.0). It reports round numbers; finer thresholds are not meaningful.

## What would move this

Not a threshold. Two candidates the evidence points at:

1. **`d98ac74e` and `a9b98c3f` are two specific messages the model reads wrong**, one of them every
   single time. Reading them and fixing the agent file's category boundaries — `action_required` vs
   `correspondence`, and vs `notification` — attacks the defect rather than filtering its output.
2. **A larger corpus weighted toward `action_required`.** Four positives cannot support a production
   gate whatever the lever.
