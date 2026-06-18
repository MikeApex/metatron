# A3 — Cold-Start Baselines (Phase 5 / D4)
*Open this in a new Claude Code session. Roadmap item A3 (2026-06-10 roadmap).*
*Parallel-safe: other chats are running simultaneously — see File ownership below.*

---

## Read these first, in order

1. `SESSION.md` — current state
2. `archive/plans/phase5_to_future_roadmap_2026-06-10.md` — Section 0 and item A3
3. `tools/baselines.py` — what exists; extend, don't rewrite
4. `core/memory.py` — the embedding model in use (expected: all-MiniLM-L6-v2, 384-dim — reuse it; do not introduce a second embedding model)
5. `config/agents/pattern_miner.md` — the consumer of these baselines

Do not begin until you've read all five.

---

## Build

Extend `tools/baselines.py` with:

1. `create_semantic_anchor(label, description)` — embeds a canonical state description, stores in `data/baselines/semantic_anchors.json`
2. `write_aspirational_baseline(persona, good_week, hard_week, peak_days, floor_days)` — from Goals Interviewer output
3. `shuffled_null_score(persona, window_days, n_permutations=100)` — permutation baseline for sparse data
4. `score_against_anchors(persona, date_range)` — cosine distance from current centroid to all anchors

Canonical anchors to create: burnout, deep_focus, physical_exhaustion, creative_momentum, social_connection, emotional_depletion, groundedness, anxiety.

Then prepare (do not run) the **truncated Goals Interview** step: a short run-guide section appended to this chat's session archive telling the user how to run it on qwen3:14b (`--provider ollama` — local, like everything touching real user data). Goals-heavy, not mission-level — acceptable for first anchoring. The user runs it in a terminal; its output feeds `write_aspirational_baseline`.

Note: the aspirational baseline produced here is a working draft — it re-runs as A5b after the real Goals Interview. Anchors are dated snapshots, not permanent coordinates.

Privacy note: the truncated interview's output is **real user data** — local only. If any testing in this chat needs realistic goals data on a cloud model, use a persona, never real output (roadmap Section 0, "What the ruling does NOT affect").

## Test (from roadmap A3 — run all three before closing)

1. Verify `create_semantic_anchor` writes all eight canonical anchors to `data/baselines/semantic_anchors.json` with embedding stored.
2. Run `write_aspirational_baseline` with sample/persona interview output. Verify baseline stored with date.
3. Run `score_against_anchors` against a test date range. Verify it returns cosine distances against all anchors.

Unlocks: Pattern Miner cold-start analysis without waiting for months of data accumulation.

---

## File ownership (parallel chats are live)

- **This chat owns:** `tools/baselines.py`, `data/baselines/`
- **`core/orchestrator.py` is owned by the A4+A6 chat.** If any new function must be registered as an agent tool, your only permitted change is appending entries to the `register_tools()` list — make it your **last** step and re-read the file immediately before editing. If a function is dev/CLI-only, don't register it.
- **Do not edit:** `config/agents/*` (A2 chat owns the head-layer files; agent files are post-review), `config/modules/routing.yaml`

## Session close

- Create `archive/sessions/2026-06-11 — A3 Cold-Start Baselines.md` early in the session, per convention.
- SESSION.md update at close: additive only — mark A3 done, do not rewrite other chats' lines.
