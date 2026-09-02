# Self-Hosted Inference Box — Workload Specification
*2026-08-31. Prepared for an external session with web access. Contains measurements only —
no project identity, file paths, or internal decisions.*

All figures are measured in production on **2026-08-29**: one user, full day, 33 requests, prompt
caching live. Nothing here is estimated. Items marked **[VERIFY]** are the external session's job.

---

## 1. Workload shape

A personal AI assistant. **17 model-backed agents in a sequential pipeline:**

```
router  →  1 to 4 domain specialists  →  response synthesizer
```

Specialists are multi-turn — median 2–4 model calls per dispatch, max 8 — with context growing on
each turn. The pipeline is **sequential by construction**: the synthesizer runs last and depends on
every specialist's output, so batching improves concurrent-user capacity but does nothing for a
single user's latency.

**Two model tiers must be resident and serving concurrently:**

| Tier | Agents | Quality bar | Character |
|---|---|---|---|
| **Deep** | 5 | Gemini 3.1 Pro | User-facing conversational voice; two agents with hard safety requirements; analytical/statistical work; a structured interview agent |
| **Fast** | 12 | Gemini 3.1 Flash-Lite | Routing directives, closed-schema extraction, mechanical structured writes |

**Hard gates on any candidate model.** Two of the deep-tier agents handle mental-health and
physical-health material. Specified safety flags must fire in **every** test scenario, and numeric
arithmetic in the finance path must be **100%** accurate. A model that misses a safety flag is not a
candidate at any speed.

**Background load, always-on.** Nightly analytical jobs — the heaviest request class measured —
plus Whisper STT (`base.en`) on a dedicated single-worker pool, and FAISS + sentence-transformers
embeddings on every memory write. These need not be fast, but must not contend with an interactive
turn.

---

## 2. The number that governs everything: 76% prompt-cache hit rate

Day total: **2,232,045 input tokens, of which 1,696,436 were served from prompt cache (76.0%).**
Per-agent hit rates run 79–96% for the specialists.

The consequence for hardware sizing:

| Assumption | Input tokens to prefill per interactive turn |
|---|---|
| Prefix caching at parity (~76%) | **~19,500** |
| No prefix caching | **~98,600** |

**A 5× swing in the governing number.** Any hardware recommendation that has not stated which of
these two rows it assumed is not usable.

Cache coverage is uneven and worth reporting: the router sits at **56.8%** and runs on every single
request; one write-only agent is at **0%**; the specialists are at **79–96%**.

---

## 3. Volume

### 3.1 Per interactive turn (≥3 agents, n=20)

Decode figures **include thinking tokens**, which the deep tier emits today.

| Tier | Input (med) | Input (p90) | **Uncached input (med)** | Decode (med) | Decode (p90) |
|---|---|---|---|---|---|
| **Deep** | 49,026 | 86,807 | **12,814** | 1,992 | 4,860 |
| **Fast** | 49,586 | 116,921 | **6,661** | 641 | 1,114 |
| **Combined** | **98,612** | **203,728** | **19,475** | **2,633** | **5,974** |

**Input-to-output ratio ≈ 37:1. This is a prefill-bound workload.** Prefill is compute-bound;
decode is memory-bandwidth-bound. The two candidate hardware families differ on exactly that axis.

### 3.2 Whole day, one user

| Metric | Measured |
|---|---|
| Requests | **33** (24 user-initiated, 9 scheduled/background) |
| Input tokens | **2,232,045** — of which **1,696,436 cached (76.0%)** |
| Output tokens | 25,570 |
| Thinking tokens | 36,167 |
| Mean per request | 67,638 in / 775 out |
| Arrival pattern | **Bursty** — 6 requests inside 7 min, 12 requests inside 28 min, sparse otherwise |

### 3.3 Peak context: 111,000 tokens

| Agent role | Med input | p90 input | **Max input** |
|---|---|---|---|
| Contacts / relationships specialist | 53,281 | 111,104 | **111,104** |
| Scheduling / logistics specialist | 42,413 | 70,048 | **106,192** |
| Response synthesizer | 22,809 | 45,253 | 49,026 |
| Mental-health specialist | 25,184 | 39,831 | 39,831 |
| Work specialist | 37,176 | — | 37,176 |
| Physical-health specialist | 19,529 | 37,918 | 37,918 |
| Recreation specialist | 16,235 | — | 16,235 |
| Router | 10,980 | 11,201 | 11,241 |
| Journaling writer | 5,289 | 10,734 | 10,734 |

**KV cache sizes against 111k, not against the 22k median.** Two agents exceed 100k on a single call.

---

## 4. Latency target

Current performance on Google Vertex (Gemini 3.1 Pro + Flash-Lite):

| Class | n | Median | p90 | Max |
|---|---|---|---|---|
| **Interactive (≥3 agents)** | 20 | **34.7 s** | **58.5 s** | — |
| Simple (1–2 agents) | 13 | 2.9 s | 11.2 s | — |
| Scheduled/background (nobody waiting) | 9 | 36.0 s | 58.5 s | — |
| All requests | 33 | 21.1 s | 49.2 s | 61.5 s |

Fan-out distribution: 1 agent (12 requests), 2 (1), 3 (12), 4 (1), 5 (6), 6 (1).

**Parity is the target — 34.7 s median, 58.5 s p90 on the interactive class. Faster is not required.**

**The single largest contributor is the response synthesizer at 17.1 s median.** It runs last and
cannot be parallelised, so it sets the floor on any turn.

Per-agent wall clock, for reference:

| Agent role | Calls | Med | p90 |
|---|---|---|---|
| Response synthesizer | 21 | 17.1 s | 24.6 s |
| Work specialist | 1 | 17.8 s | — |
| Contacts specialist | 5 | 6.0 s | 20.6 s |
| Physical-health specialist | 8 | 6.0 s | 8.4 s |
| Mental-health specialist | 9 | 5.8 s | 31.7 s |
| Scheduling specialist | 13 | 5.4 s | 8.8 s |
| Recreation specialist | 2 | 3.6 s | — |
| Router | 21 | 3.3 s | 7.6 s |
| Journaling writer | 10 | 2.7 s | 7.0 s |

---

## 5. Constraints

| # | Constraint |
|---|---|
| 1 | **Always on**, dedicated to this workload only — no other use of the machine |
| 2 | **All inference for these 17 agents stays on the machine.** That is the entire point; no cloud fallback is acceptable for them |
| 3 | **1 user today.** Spec so it does not need replacing at **4–10 concurrent users** |
| 4 | **Latency parity** with §4, not improvement |
| 5 | Budget is not the primary constraint at this stage |
| 6 | One additional agent (decontextualized web research with grounded search) stays on a cloud API and is excluded from all sizing above |

---

## 6. What to determine **[VERIFY]**

### 6.1 Prefix caching — answer this first

It is a 5× swing in prefill load (§2). For each serving stack — **vLLM, llama.cpp, SGLang,
TensorRT-LLM, MLX** — report:

1. Does it do automatic prefix caching?
2. Realistic hit rate on a workload with a large shared system prefix and a rotating tail?
3. Does the cache survive across **concurrent sessions**?
4. Does it survive a **model reload / process restart**?

Every later answer depends on this one.

### 6.2 Model selection

1. Best current open-weight model at **Gemini 3.1 Pro** level, and at **Flash-Lite** level. Parameter
   count, dense or MoE, size at Q4_K_M and Q8.
2. **If nothing open-weight reaches Pro, say so plainly and quantify the gap.** That gap is the real
   cost of self-hosting and it should not be buried.
3. Does the deep-tier candidate emit extended thinking tokens, and what does that do to the decode
   budget in §3.1?

### 6.3 Hardware

Compare on **measured prefill throughput at 20k, 50k and 110k context.** Treat decode as secondary,
but report **single-stream separately from batched** — the pipeline is sequential.

Candidates:

- **Current-generation Apple Silicon, top config.** State what Apple actually ships as of today,
  including anything announced recently — the requester may not have current information. Reference
  points from earlier generations: M4 Pro 273 GB/s, M4 Max 546 GB/s, M3 Ultra 800 GB/s.
- **Single NVIDIA datacenter GPU** — A100 80GB / H100 80GB / current equivalent.
- **Dual H100 NVLink** or current equivalent.
- **RTX 6000-class workstation cards.**

For each report: total memory required (**weights for both tiers resident simultaneously** + KV cache
at **110k × N concurrent** + ~15 GB for OS, Whisper and FAISS), sustained vs. burst throughput under
24/7 load, and idle and load power draw.

### 6.4 The arithmetic

For each candidate, compute median interactive-turn wall clock **twice** — once assuming prefix
caching reaches parity with the measured 76%, once assuming none — at **1, 4 and 10 concurrent
users**:

```
per interactive turn (median):
  prefill, cached at parity   ~19,500 tokens  / (prefill tok/s)
  prefill, no caching         ~98,600 tokens  / (prefill tok/s)
  decode (incl. thinking)      ~2,633 tokens  / (decode tok/s, single stream)
  target                      <= 34.7 s

at p90:
  prefill ~40,000 cached-parity / ~203,700 uncached
  decode  ~5,974
  target  <= 58.5 s
```

### 6.5 Deliver

A recommendation, and **the single number that decides it.**

---

## 7. One caution to carry

Apple unified memory wins on capacity-per-dollar and power draw. NVIDIA wins on prefill compute and
on batched multi-user serving. Given a 37:1 input-to-output ratio, a 111k peak context and a
multi-user requirement, the expectation going in is that **NVIDIA wins** — but that expectation rests
on pre-May-2026 chip knowledge and must be checked against current Apple Silicon prefill benchmarks.

**If prefix caching reaches parity, the margin narrows sharply.** 19,500 tokens of prefill in a 34.7 s
budget is a far easier target than 98,600, and that is the case in which Apple Silicon becomes
genuinely viable. Do not collapse the two cases into one recommendation.
