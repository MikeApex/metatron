# Pattern Miner — Future Development Notes

*Created Phase 4 (2026-05-19). Not active until post-Phase 6 roadmap is complete.*

---

## When to revisit this file

At the Phase 5/6 transition, or when any of these conditions are true:
- Structured numerical data (health, sleep, biometrics) joins the corpus
- Data volume exceeds ~10,000 entries
- The Pattern Miner is surfacing too many weak signals and needs better dimensionality
- The state-anchored baseline approach is being built (Phase 5)

---

## 384-dimension embedding ceiling

**all-MiniLM-L6-v2** produces 384-dimensional embeddings optimized for semantic similarity in text. This is well-suited to narrative log and journal entries. Limitations emerge as the system grows:

**What 384 dimensions handles well:**
- Semantic similarity between journal entries and search queries
- Clustering of thematically related entries
- Linear PCA / sparse PCA at hundreds to low thousands of entries

**What may require a richer representation:**
- Numerical and behavioral correlations (sleep hours vs. writing output) — these are weakly encoded in text embeddings; a structured feature vector would capture them more reliably
- Cross-modal analysis: combining text narrative with quantitative health/sleep/biometric data
- Fine-grained emotional distinctions that exceed the semantic resolution of a small embedding model

**Future direction:** Hybrid representation. Text embeddings for narrative entries + structured feature vectors for quantitative data. Joint PCA or multi-view analysis across both. Evaluate when Phase 5 structured data modules (health, sleep, finance) are live.

**Model upgrade path:** all-MiniLM-L6-v2 → sentence-transformers/all-mpnet-base-v2 (768 dims, better quality, ~3× slower) → text-embedding-3-small (OpenAI, 1536 dims, cloud, best quality, not local). Upgrade decision belongs at Phase 6 hardware migration when always-on compute is available.

---

## Non-linear correlation detection

Linear PCA finds directions of maximum variance in the embedding space. It will miss:
- Non-linear manifolds (e.g., cyclical seasonal patterns that wrap around in embedding space)
- Interaction effects (A × B predicts C even when A and B alone do not)
- High-order correlations involving 3+ variables

**Candidate approaches:**
- **UMAP** — non-linear dimensionality reduction, preserves local and global structure. Good for visualization and cluster discovery at larger data volumes. Stochastic — results vary between runs.
- **Kernel PCA** — extends PCA with a kernel function (RBF, polynomial). More interpretable than UMAP but slower.
- **Sparse autoencoder** — learns a compressed representation of the data; useful when the relevant signal is sparse across many dimensions.

These are all Phase 6+ work. Flag for review when data volume and hardware support it.

---

## Composite / learned-optimal baseline selection

Current baseline selection is rule-based: use trailing window at short scales, state-anchored at longer scales. The end state is a learned system that discovers, per user and per pattern type, which baseline structure produces the strongest signal.

**Design sketch:**
- For each insight surfaced, record: which baseline was used, whether the user engaged with the insight (flagged, acted on, referenced in a later session)
- Over time, build a lightweight model (logistic regression or decision tree on baseline features × pattern type → engagement probability)
- Use this to weight baseline selection: baselines that consistently produce engaging insights get promoted
- No separate ML model needed initially — the Diarist context tracker captures engagement signals

**Data requirement:** ~6 months of real usage with engagement tracking before this model has enough signal to be meaningful. Deferred to Phase 7+ unless the simpler heuristic fails in practice.

---

## Gemini 3.1 Pro baseline poll — incomplete

At the Phase 4 planning session (2026-05-19), the baseline strategy question was sent to GPT-4o (responded) and Sonnet 4.6 (responded), but Gemini 3.1 Pro was unavailable (503). Re-run in early Phase 5:

> "We're building a Pattern Miner for a personal life-logging system. Data lives in a FAISS vector index of journal and log entries (all-MiniLM-L6-v2 embeddings, 384 dimensions). The question is about baseline selection — the reference window used to give a short-scale analysis statistical grounding. [Full question text in archive/sessions/2026-05-19 — Phase 4 Plan, Baseline Strategy Poll.md]"

Gemini responded on 2026-05-19 (second attempt, Flash model). Key additions vs. GPT-4o and Sonnet 4.6:

**Life-stage segment baseline:** Compare periods where the user was in a similar life configuration — not just event-conditioned ("after X") but state-defined ("while self-employed", "early parenthood", "living in City X"). Non-contiguous periods sharing a characteristic. Requires user tagging or clustering inference. Meaningful with 3+ years of data.

**Multi-baseline parallel scoring:** For every pattern found, evaluate it against all applicable baselines simultaneously and surface the one with the strongest signal. Removes the guessing problem from baseline selection at the cost of compute. Operationally: score each pattern against trailing window, same-calendar-period, state-anchored — report the highest-signal result with its baseline labeled.

Both are Phase 5/6 work. The progressive unlocking thresholds Gemini provided (3 months / 6-12 months / 1 year / 2-3 years / 3+ years) were incorporated into the Pattern Miner agent instruction file directly.

---

## User-defined baseline periods — exit interviews and time dilation

**Phase 4, 2026-05-19** — tool layer built now; deeper features deferred

The tool layer (`tools/baselines.py`) captures named baseline periods and retrospectives. The deeper design:

**Perfectly fulfilled periods as the gold standard baseline.** The most meaningful comparison isn't "the last 30 days" — it's "those three months where everything was working." Users carry memories of these periods. The baseline interview should include: *"Tell me about a period of your life where you felt genuinely fulfilled — not perfect, but deeply on track. What was happening?"* The system captures this as a named baseline period with a user memory narrative and, if datable, maps it to actual check-in data.

**"Good old days" reframing effect on extremity anchors (2026-05-20).** The "1 in 100" best/worst days anchor (Boundary/Extremity baseline, seeded from interview) is not a fixed reference — it drifts. A day that was a 10 at the time may be retrospectively reframed as less exceptional once newer highs emerge. The reverse is also true: a floor that felt absolute gets revised when later events provide darker contrast. This is not just memory imprecision — it's context-dependence. Current events act as a lens that colors memory of prior events (immediate and historic). The extremity anchors should be treated as dated snapshots with revision timestamps, not permanent coordinates. The retrospective layering mechanism below applies here too: capture the anchor at interview time, re-check at 6 and 12 months. This is also connected to the non-linear distribution of emotional experience — 1s and 10s on a 365-day calendar are sparse and asymmetrically distributed, and the user's memory of which days qualify changes as the frame of reference shifts.

**Exit interviews and retrospective layering.** Human memory of a period changes over time. The late-night drinking was great at the time; less so the next morning; differently understood a year later in the context of a behavior pattern. The system should capture retrospective assessments of the same baseline period at multiple time distances:
- **Immediate** (during/just after): in-the-moment quality score
- **Short-term** (1-4 weeks later): settled assessment
- **Long-term** (6-12 months later): pattern-context reassessment

This creates a time-dilation layer on memory — the system can surface that a user's remembered fulfillment was accurate at the time but revised by later data, or vice versa. A "baseline" that looked good in the moment but was retrospectively assessed as a deterioration period is a flag, not a reference.

Build the retrospective capture tool now (done). The multi-session retrospective interview design is Phase 5 work, dependent on having enough longitudinal data to make the comparison meaningful.

---

## Statistical modeling — deferred deep conversation

**Phase 4, 2026-05-19** — using Gemini's suggested approach (t-tests, ANOVA, Cohen's d, anomaly scoring) for the Phase 4-5 build. The choice of statistical model deserves a dedicated conversation before a production-quality release. Questions to address:
- Are parametric tests (t-test, ANOVA) appropriate for this data? Life-logging data is non-normal, autocorrelated, and sparse.
- Permutation tests as the non-parametric alternative — practical at our data volumes?
- Effect size vs. statistical significance: for a personal tool with N=1, statistical significance is less meaningful than effect size and personal relevance.
- Bayesian approaches: updating a prior belief about a pattern given new data is arguably more natural for this use case than frequentist hypothesis testing.

Flag this for a full working session before Phase 6 (production readiness phase). In the meantime, confidence annotations in the Pattern Miner output serve as the practical proxy for statistical rigor.

---

## Gamification of baseline unlocking — Alpha note

**Phase 4, 2026-05-19** — the progressive unlocking of baseline types (trailing → calendar → state-anchored → life-stage) has natural gamification potential. As history accumulates, new analytical capabilities unlock — "You've now logged 90 days. A new type of analysis is available..." This is an early-engagement driver that becomes especially valuable for multi-user Alpha onboarding.

**Revisit this conversation when preparing for multi-user Alpha testing.** Design the unlocking sequence, the notification mechanism, and the onboarding flow that makes the progression feel earned rather than arbitrary. The unlocking should map to genuine analytical capability improvements, not just time-gating.

---

## Large-window log retrieval — rate limit workaround

**Phase 4, 2026-05-19** — `get_log_window` with a 90-day window (~56 entries) hit the Anthropic cloud rate limit (30k input tokens/minute) on a low-credit tier account. Short-term fix: `max_entries` cap added to `get_log_window`; Pattern Miner can call twice with split windows to cover the full range.

**This is a workaround, not a solution.** The real fix is one of:
- **Local model routing**: Ollama/vLLM has no token rate limits. 90-day and all-time analyses should be scheduled to run locally during off-hours once Ollama is running. This is the primary motivator for completing the sensitive routing toggle (routing.yaml `local_enabled: true`).
- **Chunked retrieval with progressive synthesis**: Pattern Miner pulls 30-day chunks sequentially, synthesizes each, then merges. Adds latency but works on any tier.
- **Structured summary layer**: Instead of passing raw log JSON, pre-aggregate entries into weekly summaries before passing to the model. Reduces tokens by ~10x with modest information loss.

Revisit when either (a) Ollama is running and local routing is active, or (b) the corpus exceeds 180 days and chunked synthesis becomes necessary regardless of tier.

---

## Statistical pre-aggregation as a privacy layer

**Phase 4, 2026-05-19** — The Pattern Miner is both the most analytically demanding agent and the most sensitive-tier. The question: could FAISS matrices be sent to an external model for analysis without leaking content, using the vectors as an opaque representation?

**Why raw vectors don't work:** FAISS embeddings (384-dim floats) can't be read by an LLM — they're not tokens. More critically, they're not actually private: embedding inversion attacks can approximately reconstruct original text from vectors with reasonable accuracy. Sending raw embeddings is leaking sensitive content in a form that looks opaque but isn't.

**The version that does work — statistical pre-aggregation:**

Run FAISS queries and log retrieval entirely locally → extract only aggregate statistical features → send those features to an external model for analytical synthesis.

Instead of: *"Ryan wrote: 'pushing through mud, third day stuck on Cato'"*

Send: *"Sleep: μ=5.1h σ=0.4, writing output: μ=0.3 pages, correlation r=0.82, n=12, baseline deviation: -2.1σ from 30-day mean"*

The external model gets numbers and structure, not diary entries. It can still perform meaningful pattern synthesis without ever seeing raw log content. This is the "structured summary layer" mentioned in the large-window retrieval note above — it's both a token-reduction strategy and a genuine privacy mechanism.

**Practical path:** When the corpus is large enough to justify it (Phase 6+), a local pre-aggregation step would allow capable external models (o3, Gemini Pro) to do the heavy analytical synthesis without routing sensitive text off-device. The FAISS index and raw logs stay local; only sanitised statistics leave. This is a complement to Ollama routing, not a replacement — Ollama remains the primary path; this opens a cloud fallback that doesn't compromise the privacy tier.
