# Handoff — coordinator model probe [DB-0820-05] evidence (2026-08-28)

*From the Green/Amber spinoff chat (Fable review, Opus worker). Merged `ec774da`. Evidence
only — no routing file touched; the flip is Red-tier and Mike's. Full report:
[tests/coord_model_probe_2026-08-28_flashlite_vs_pro.md](../../tests/coord_model_probe_2026-08-28_flashlite_vs_pro.md)
(raw JSON beside it; `--report-only` rebuilds without re-spending).*

## The answer, for the Red flip decision

**Pro fixes the referent class, and it costs ~+11 seconds on every reply.**

| Suite | Flash-Lite | Pro |
|---|---|---|
| A — 15 ordinary turns | 15/15 | 15/15 |
| B — 4 referent cases, clean history | 3/4 | 4/4 |
| **B-hard — same 4 with a competing referent, ×3 runs** | **6/12** | **12/12** |
| Mean latency (Suite A, cached path, warm-up excluded) | 1.88s | 12.79s |

Flash-Lite reproduced two live failures 3/3 ("read that back" → Prudential schedule instead
of the just-logged food; "Approved" → wrong pending action). Pro swept all twelve — and on
the first its winning move was raising `CLARIFICATION_NEEDED`, **a rule `coordinator.md`
already states and Flash-Lite simply does not follow**. The latency is thinking tokens
(~1,119/call on a fixed-shape output), not model speed.

**Three options for Mike, with the report's recommendation:**
1. Flip as measured — +11s ahead of every reply on a voice-first product; almost certainly
   intolerable.
2. **Probe Pro with a capped thinking budget first (recommended)** — one more run; the only
   option not already resolved by evidence in hand. Needs a small code change:
   `_run_single_agent` passes `thinking_budget` only for `synthesizer` today.
3. Don't flip; fix the referent class in `coordinator.md` (Red) — the winning behaviour is
   one the agent file already mandates, so this is an adherence fix, same family as the
   `[DB-0822-*]` cluster. Pairs with `[DB-0826-01]`, which stays open either way.

## Method notes that keep the numbers honest

- **Cached path, deliberately diverging from the entry's "uncached" wording** — Mike's 08-28
  run instruction supersedes it; the live coordinator runs cached, and the first call per
  model was an excluded warm-up. Cache use was confirmed (98% of input tokens from cache),
  not assumed.
- Step 0 proved `_get_or_create_vertex_cache` already honours `model_override` (Pro builds
  its own CachedContent; no silent uncached fallback) — **no fix needed for the live flip**.
- Suite B is faithful reproduction, not replay — the verbatim turns live in `mike`'s
  `quality_events.json` on the VM, gitignored. Evidence about the class, not the exact turns.
- The clean Suite B did not discriminate (both models near-swept it); only B-hard, with a
  competing referent restored, measures the failure. Recorded so nobody re-runs the clean
  half and calls it the answer.

## Bonus fix merged with the probe

**Cache hits were invisible in traces** — `record_turn_tokens` accepted `cached_tokens`,
priced it in the spend guard, then dropped it, so no trace or test could tell a hit from a
miss (the exact shape of the 2026-06-24 month-long silent cache failure). `core/trace.py` now
stores and serialises it (`total_cached_tokens()`). Additive; trace/provenance/analytics
suites pass. **VM deploy owed** with the rest of this run's merges.

## Deferred

The capped-thinking-budget probe (option 2) — needs the small `_run_single_agent` change
above, then one re-run of Suite A + B-hard on Pro only.
