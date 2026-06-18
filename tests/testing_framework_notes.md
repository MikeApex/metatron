# Testing Framework Notes

*Accumulated methodology notes for the test suite. Updated as new insights emerge.*

---

## Synthetic data and the Pattern Miner oracle problem

**Phase 4, 2026-05-19**

Synthetic data for the Pattern Miner test is generated **without planted correlations**. Field values (sleep hours, energy, mood, writing output, etc.) are drawn from independent random distributions — there is no deliberate "if sleep < 6 then writing_pages is low" logic in the generator.

This is a principled design choice, not a limitation.

The alternative — planting known correlations and verifying the Pattern Miner finds them — creates a circular test: the generator is the oracle, and the Pattern Miner passes by matching the generator's assumptions. This tells us the Pattern Miner can find what we told it to look for. It does not tell us whether it surfaces genuine signal from real data.

**By generating without planted correlations, the generator's own randomness becomes the data.** Any statistical structure the Pattern Miner surfaces is real — an artifact of the random seed and distributional choices, not a planted expectation. The Pattern Miner finding a correlation in random data is either:

1. A genuine random correlation worth noting (most correlations in short-window data are), or
2. A false positive (calibration signal — if the Pattern Miner cries wolf on random data, the confidence thresholds need tuning)

Both outcomes are useful. Case 1 validates the detection mechanism. Case 2 identifies a calibration problem before real data enters the system.

**The Pattern Miner is the oracle, not the generator.**

### Practical implication for test evaluation

When reviewing `phase4_report.md`, do not ask "did it find what we planted?" Ask:

- Is the observation backed by actual evidence from the entries?
- Is the confidence annotation appropriate for the data volume?
- Does a claimed correlation actually appear in the raw logs when you check manually?
- Did the model distinguish between a genuine pattern (multiple entries, consistent signal) and noise (one or two entries that happened to co-occur)?

A finding in random data is not automatically wrong. It is correctly labeled "weak signal" if the confidence annotation is working.

---

## Baseline selection evolution

**Phase 4, 2026-05-19**

Short-scale analyses (7-day, 30-day) run against a larger trailing window for baseline context. This is a practical necessity during the data-sparse early phase. As history accumulates, the optimal baseline shifts:

- **Trailing windows** (current): Simple, works from week one, statistically thin at short scales
- **State-anchored baselines** (~6 months+): FAISS semantic retrieval of similar prior periods — "other weeks that looked like this one" rather than "the prior four weeks"
- **Calendar-anchored** (2+ years): Same period in prior years; event-conditioned periods

Baseline selection logic should be reviewed at the Phase 5 → 6 transition when enough history exists to validate the state-anchored approach.

**Gemini 3.1 Pro poll (baseline strategy) was not completed** — 503 error at time of Phase 4 planning session. Re-run the baseline strategy question in early Phase 5 before the state-anchored baseline is built. Gemini's research depth may surface baseline structures not identified by GPT-4o or Sonnet 4.6.

---

## Cumulative prompt length tracking

**2026-05-27**

Individual agent files are short (300–800 tokens each) and are not the risk. The risk is cumulative prompt size per session: Constitution + Prime Directive + Mission + Goals + agent file + tool schemas + conversation history. This can reach 10K–20K input tokens per turn in a multi-agent Phase 5 session — well past the ~8K threshold where "lost in the middle" attention degradation becomes measurable.

### How to measure reliably

Every API we use returns actual token counts in the response object. Use these, not local estimators:

| Provider | Field |
|---|---|
| Anthropic | `response.usage.input_tokens` + `response.usage.output_tokens` |
| OpenAI | `response.usage.prompt_tokens` + `response.usage.completion_tokens` |
| Gemini | `response.usage_metadata.prompt_token_count` + `candidates_token_count` |
| Ollama | `response.prompt_eval_count` + `response.eval_count` (model-dependent) |

**Implementation target (Phase 5):** The orchestrator should accumulate `input_tokens` per turn and log a session-level total to the session log. A warning log line at >8K cumulative input tokens per turn is sufficient — no UI change required.

### Warning thresholds (current generation models)

| Cumulative input tokens | Signal |
|---|---|
| < 8K | Reliable attention across full prompt |
| 8K–15K | Monitor for instruction dropout; run behavioral audit after config changes |
| 15K–30K | Lost-in-the-middle risk is significant; consider prompt pruning or FAISS retrieval to replace full context loads |
| > 30K | Treat as a design problem, not a tuning problem |

### Practical implication for testing

When running Phase 5 multi-agent scenarios, log cumulative input tokens per session. If any session regularly exceeds 15K, identify which config components are largest and evaluate whether they can be trimmed or conditionally loaded. Do not assume instruction fidelity without a prompt budget check.

---

## 384-dimension embedding ceiling

**Phase 4, 2026-05-19** — deferred to `research/pm_future.md`

all-MiniLM-L6-v2 (384 dimensions) is adequate for Phase 4. The ceiling question arises when:
- Structured numerical data (health metrics, sleep data, biometrics) joins the corpus
- Non-linear correlations become the primary analytical target
- Data volume crosses ~10,000 entries where linear PCA starts missing structure

See `research/pm_future.md` for discussion. Flag for Phase 5/6 transition review.
