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

Gemini's research thoroughness may surface baseline structures not identified above.
