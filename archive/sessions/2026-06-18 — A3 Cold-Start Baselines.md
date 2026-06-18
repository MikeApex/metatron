# A3 — Cold-Start Baselines
*2026-06-18. Parallel chat from the 2026-06-11 batch.*

---

## What this session does

Extends `tools/baselines.py` with semantic anchor infrastructure — the scaffolding that lets the Pattern Miner score the user's current state against canonical human experiential states from day one, without months of accumulated data.

File ownership: `tools/baselines.py`, `data/baselines/`. Does not touch `config/agents/` or `config/modules/routing.yaml`.

---

## Built

### New functions in `tools/baselines.py`

**`create_semantic_anchor(label, description)`**
- Embeds a canonical state description using all-MiniLM-L6-v2 (same model as memory.py)
- Stores in `data/baselines/semantic_anchors.json` with label, description, embedding (float32 list), created date
- Not persona-scoped — canonical anchors are universal

**`write_aspirational_baseline(persona, good_week, hard_week, peak_days, floor_days)`**
- Records the user's self-reported aspirational reference points from the Goals Interview
- Stored in `data/baselines/aspirational_baselines.json` (real user) or `data/personas/{persona}/aspirational_baseline.json`
- Includes created date for re-run tracking (A5b updates this after the full Goals Interview)

**`shuffled_null_score(persona, window_days, n_permutations=100)`**
- Permutation baseline for sparse data: randomly samples `window_days`-length windows from the full log history
- Builds a null distribution of anchor similarity scores (mean ± std per anchor)
- Used to distinguish real signal from noise when only weeks of data exist

**`score_against_anchors(persona, date_range)`**
- Reads all log entries in the date range, embeds each, averages to centroid
- Returns cosine similarity to every semantic anchor (0–1, higher = more similar to that state)
- Falls back gracefully if no logs or no anchors exist

### Tool schemas added
All four functions have `_SCHEMA` constants following the existing pattern. Registration in orchestrator deferred to last step.

### Canonical anchors created (8)
burnout, deep_focus, physical_exhaustion, creative_momentum, social_connection, emotional_depletion, groundedness, anxiety

---

## Tests run (all pass)

- Test 1: All 8 canonical anchors written to `data/baselines/semantic_anchors.json` — 384-dim embeddings, permissions 600 ✓
- Test 2: `write_aspirational_baseline` with sample data stored with date, all fields present, permissions 600 ✓
- Test 3: `score_against_anchors` returns cosine distances for all 8 anchors; depleted/burned-out synthetic logs scored highest on anxiety + burnout (semantically correct) ✓

---

## Truncated Goals Interview run-guide

See bottom of this file.

---

## Decisions made in this session

- **A5b split from VM fresh interview:** A5b (required for Alpha gate / A7) runs with existing A5 interview data — does not require a fresh interview. Fresh Goals Interview on VM is a new D1 item (post-Alpha), when new features make re-interviewing worthwhile.
- **Roadmap cross-check confirmed:** placing VM interview as A5b would create a circular dependency (Alpha requires A5b; D1 is post-Alpha). The split resolves it cleanly.

## Deferred / follow-on

- **A5b** — Run `write_aspirational_baseline` with real A5 interview data (config/goals.yaml, config/mission.md, config/prime_directive.md) before A7. The A3 baseline used placeholder sample data; A5b replaces it with real content.
- **VM fresh Goals Interview** — New D1 item. After VM is provisioned and new features are live, run a full Goals Interview + A5b re-run as first-use onboarding on the VM.
- `data/baselines/` is in D2 encryption scope (`age` encryption applied at Phase 6 / D2).

---

## Truncated Goals Interview run-guide

**Purpose:** Produce goals-oriented aspirational baseline data to feed `write_aspirational_baseline`. This is a shorter version of the full Goals Interview — focused on goals/current state, not mission/prime directive. The output is real user data and stays local.

**How to run:**

```bash
cd ~/Desktop/multi-model-mcp
source .venv/bin/activate
ollama serve   # if not already running
python core/orchestrator.py --agent goals_interviewer --provider ollama
```

**What to cover in the truncated session:**

The interviewer will run its normal flow. For the truncated baseline version, steer toward these four questions if the interview doesn't reach them naturally:

1. "Describe a recent week that felt genuinely good — what was happening?"
2. "Describe a week that felt hard or depleted — what was different?"
3. "What does a peak day look like for you? What's happening on your best days?"
4. "What's the floor — a day you want to avoid? What signals tell you you're heading there?"

The answers feed directly into `write_aspirational_baseline`:
- `good_week` ← answer to question 1
- `hard_week` ← answer to question 2
- `peak_days` ← answer to question 3
- `floor_days` ← answer to question 4

**After the session:**

Call `write_aspirational_baseline` with the output:

```python
from tools.baselines import write_aspirational_baseline

write_aspirational_baseline(
    persona="",          # empty string = real user
    good_week="...",     # user's words from question 1
    hard_week="...",     # user's words from question 2
    peak_days="...",     # user's words from question 3
    floor_days="...",    # user's words from question 4
)
```

**Privacy note:** This output is real user data — sensitive tier, local only. Do not paste it into any cloud model. If testing with a cloud model is needed, run the same questions against a persona (`--agent goals_interviewer --provider ollama` with `AI_TEST_PERSONA` set).

**What happens next:** A5b (after the full Goals Interview at A5) re-runs this with mission-level data, updating the baseline file with a new dated entry.
