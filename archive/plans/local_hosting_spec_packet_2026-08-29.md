# Metatron — Local Hosting Spec Packet
*Written 2026-08-29 for a session outside Claude Code with web access. Supersedes the sizing in
`archive/sessions/2026-06-02 — Local Model Architecture, Token Generation, Hardware Analysis.txt`,
which was built on estimates before any production measurement existed.*

> **This file is INTERNAL — do not paste it externally.** It names the project, its agents, its
> privacy rulings and its cost baseline. The scrubbed, numbers-only version for an outside
> session is `archive/plans/hardware_spec_external_2026-08-31.md`.

**Why this file exists:** the hardware question needs current model-leaderboard and chip-spec data.
Claude Code on this project has `WebSearch`/`WebFetch` denied and a May 2026 knowledge cutoff, so it
cannot supply either. Everything below that is *measured* comes from this repo. Everything marked
**[VERIFY]** is the outside session's job.

---

## 1. Mike's constraints (given 2026-08-29)

| # | Constraint |
|---|---|
| 1 | **Hybrid split accepted.** Non-sensitive agents stay on cloud models. Only sensitive agents move local. |
| 2 | **Latency target: parity with the current Vertex build.** Not faster. |
| 3 | **Question is the upper limit.** Spec for Metatron *as it runs today*; the next build will be more efficient, so today's shape is the ceiling, not the floor. |
| 4 | **Always-on, dedicated machine.** A home for Metatron and nothing else. |
| 5 | **Multi-user capable.** One user today; spec so it does not have to be replaced. |
| 6 | Budget is not a constraint at this stage. |

---

## 2. The headline finding — read this before any spec table

**Everything here is measured from 2026-08-29 on the live VM** (`data/personas/mike/traces/2026-08-29.jsonl`,
33 requests, one user, full day, prompt caching live). Mike's ruling: that day is wholly
representative of single-user load. An earlier draft of this packet used an August-wide average and
was wrong in both directions — the system has improved substantially over that window.

**Two facts govern the hardware choice.**

**(a) 76% of input tokens are served from prompt cache.** Day total: 2,232,045 input tokens, of which
1,696,436 were cached. Per-agent hit rates run 79–96% for the specialists. This is recent — it went
live within the last week — and it is the reason latency dropped.

The consequence for hardware is severe and easy to miss: **the prefill load a local box faces depends
entirely on whether its serving stack does prefix caching as well as Vertex does.** For a median
interactive turn:

| | Input tokens to prefill per turn |
|---|---|
| With prefix caching at parity (~76%) | **~19,500** |
| With no prefix caching | **~98,600** |

That is a **5× swing in the governing number.** vLLM automatic prefix caching and llama.cpp's prompt
cache both exist; whether they hold a ~50k-token shared prefix across 17 agents and multiple
concurrent sessions is the question that decides the spec. **Do not accept a hardware recommendation
that has not stated which of those two rows it assumed.**

**(b) It is still a prefill-dominated workload — about 37:1 input to output.** The June 2026 analysis
sized the machine on generation tok/s. Generation volume is trivial; input volume is enormous. Prefill
is compute-bound (FLOPS), decode is memory-bandwidth-bound. Apple Silicon's strength is bandwidth and
capacity; its relative weakness is the compute throughput prefill needs.

One addition since June: **the deep tier emits thinking tokens** — 36,167 across the day, and they
dominate decode on interactive turns (median 1,992 decode tokens on the deep tier, of which most are
thinking). Any candidate reasoning model makes this worse.

---

## 3. Measured workload — 2026-08-29, one user, live

### 3.1 The day in total

| Metric | Measured |
|---|---|
| Requests | **33** (24 user-initiated, 9 proactive/scheduler) |
| Input tokens | **2,232,045** — of which **1,696,436 cached (76.0%)** |
| Output tokens | 25,570 |
| Thinking tokens | 36,167 |
| Per request | 67,638 in / 775 out — **87:1** |
| Request clustering | Bursty: 10:31–10:38 (6 reqs), 13:00–13:28 (12 reqs); otherwise sparse |

### 3.2 Latency — this is the bar

| Class | n | Median | p90 | Max |
|---|---|---|---|---|
| **All requests** | 33 | **21.1 s** | **49.2 s** | 61.5 s |
| **Interactive (≥3 agents)** | 20 | **34.7 s** | **58.5 s** | — |
| Simple (1–2 agents) | 13 | 2.9 s | 11.2 s | — |
| Proactive (scheduler, nobody waiting) | 9 | 36.0 s | 58.5 s | — |

Fan-out distribution: 1 agent (12 reqs), 2 (1), 3 (12), 4 (1), 5 (6), 6 (1).

**Parity target: median 34.7 s and p90 58.5 s on the interactive class.** That is the number a
candidate machine has to hit. It is much softer than "cloud-fast" and anyone speccing without it will
over-buy.

### 3.3 Load split by model tier — the sizing inputs

Deep tier = the five agents on `gemini-3.1-pro-preview`. Fast tier = the twelve on `flash-lite`.
Decode figures include thinking tokens. **Per interactive request** (≥3 agents, n=20):

| Tier | Input (med) | Input (p90) | **Uncached input (med)** | Decode (med) | Decode (p90) |
|---|---|---|---|---|---|
| **Deep** | 49,026 | 86,807 | **12,814** | 1,992 | 4,860 |
| **Fast** | 49,586 | 116,921 | **6,661** | 641 | 1,114 |
| **Combined** | **98,612** | **203,728** | **19,475** | **2,633** | **5,974** |

### 3.4 Per-agent detail

Input/output are totals per dispatch, summed across turns. Duration is wall clock on Vertex.

| Agent | Calls | Med dur | p90 dur | Med in | p90 in | **Max in** | Med out | p90 out | Cache% | Turns med/max |
|---|---|---|---|---|---|---|---|---|---|---|
| coordinator | 21 | 3.3 s | 7.6 s | 10,980 | 11,201 | 11,241 | 301 | 578 | 56.8% | 1/1 |
| synthesizer | 21 | 17.1 s | 24.6 s | 22,809 | 45,253 | 49,026 | 155 | 317 | 73.5% | 1/2 |
| logistics | 13 | 5.4 s | 8.8 s | 42,413 | 70,048 | **106,192** | 325 | 444 | 78.5% | 2/5 |
| diarist | 10 | 2.7 s | 7.0 s | 5,289 | 10,734 | 10,734 | 60 | 236 | 0.0% | 2/4 |
| mental_wellbeing | 9 | 5.8 s | 31.7 s | 25,184 | 39,831 | 39,831 | 374 | 765 | 79.5% | 3/3 |
| physical_health | 8 | 6.0 s | 8.4 s | 19,529 | 37,918 | 37,918 | 276 | 459 | 88.8% | 2/4 |
| relationships | 5 | 6.0 s | 20.6 s | 53,281 | 111,104 | **111,104** | 306 | 846 | 91.7% | 4/8 |
| recreation_hobbies | 2 | 3.6 s | — | 16,235 | — | 16,235 | 250 | — | 96.4% | 2/2 |
| work_vocation | 1 | 17.8 s | — | 37,176 | — | 37,176 | 327 | — | 85.6% | 4/4 |

**Peak single-call context: ~111,000 tokens.** KV cache sizes against that, not the median. Two agents
(relationships, logistics) exceed 100k. The synthesizer — the one on the interactive critical path —
peaks at 49k.

**Note the synthesizer is the latency bottleneck**: 17.1 s median, the largest single contributor to a
turn, on the deep tier, and it cannot be parallelised because it runs last by construction.

### 3.5 What moves local vs. stays cloud

Per Mike's constraint 1 and `config/modules/routing_cloud.yaml`:

**Must run local (sensitive — reads personal logs, journals, contacts, health, finance):**
synthesizer, coordinator, mental_wellbeing, physical_health, relationships, finance, work_vocation,
learning_growth, recreation_hobbies, logistics, diarist, pattern_miner, goals_interviewer,
tone_profiler, intake_extractor, accountability_judge, crm_sweep — **17 agents.**

**Stays cloud:** research_agent only (decontextualized, and needs grounded web search a local model
cannot provide).

Note this is nearly everything. The privacy ruling (`ROADMAP.md` § Section 0) makes almost the whole
pipeline sensitive-tier, so "hybrid" removes one agent from the local load, not half of it.

**Quality tiers the local models must match:**

| Local model tier | Serves | Current cloud equivalent |
|---|---|---|
| **Deep** | synthesizer, mental_wellbeing, physical_health, pattern_miner, goals_interviewer | gemini-3.1-pro-preview |
| **Fast** | coordinator, diarist, logistics, relationships, finance, work_vocation, learning_growth, recreation_hobbies, tone_profiler, intake_extractor, accountability_judge, crm_sweep | gemini-3.1-flash-lite |

**Hard-fail criteria that gate any candidate model** (`ROADMAP.md`, A4/D2): mental_wellbeing clinical
flags `MUST_SURFACE` and `CLINICAL_CONCERN` must fire in every scenario; finance arithmetic must be
100% accurate. A model that misses a clinical flag is not a candidate at any speed.

### 3.6 Background load (nobody waiting, but always-on)

9 of yesterday's 33 requests were proactive/scheduler runs, and they are the *heaviest* class — median
36.0 s, deep-tier input median 66,974. Nightly jobs: pattern_miner, crm_sweep (a full day of
conversation + journal text), accountability_judge, diarist. Plus Whisper STT (`base.en`, per
`core/voice_pipeline.py`) on a dedicated single-worker pool, and FAISS + sentence-transformers
embedding on every memory write. These need not be fast, but must not contend with an interactive
turn — the machine needs headroom, not just capacity.

---

## 4. What the outside session needs to determine

### 4.1 Model selection **[VERIFY]**

Using current open-weight leaderboards (LMArena, Artificial Analysis, LiveBench, EQ-Bench for
conversational voice):

1. **Which open-weight model is at Gemini 3.1 Pro's level?** Report parameter count, architecture
   (dense vs MoE — MoE changes the memory/compute tradeoff fundamentally), and quantized size at
   Q4_K_M and Q8. If nothing open-weight reaches Pro, say so plainly and give the closest, with the
   gap quantified — that gap is the real cost of going local.
2. **Which open-weight model is at Gemini 3.1 Flash-Lite's level?** This tier is 12 of 17 agents and
   is likely satisfied cheaply.
3. **Reasoning/thinking models:** if the Deep-tier candidate emits extended thinking tokens, that
   multiplies decode volume against §3.1's budget. Flag it.

### 4.2 Hardware sizing **[VERIFY]**

Size for the §3 workload at **1, 4 and 10 concurrent users**, and report for each candidate:

1. **Does the serving stack do prefix caching, and how well?** Answer this before anything else — it
   is a 5× swing in the prefill load (§2a). Report measured hit rate on a workload with a large
   shared system prefix and a rotating tail, and whether the cache survives across concurrent
   sessions and across model reload.
2. **Prefill (prompt-processing) throughput, tokens/sec**, for the Deep-tier model at 20k, 50k and
   **110k** context. This is the governing number — measured figures, not marketing.
3. **Decode throughput, tokens/sec**, single stream and batched. Single-stream matters most: the
   pipeline is sequential.
4. **Memory:** weights for **both tiers resident simultaneously** + KV cache at **110k** context ×
   N concurrent sessions + ~15 GB for OS, Whisper STT and FAISS.
5. **Sustained throughput under continuous load**, not burst — this box runs 24/7 and its heaviest
   jobs are the nightly scheduler runs.
6. **Idle and load power draw.**

**Candidate classes to compare:**

- Apple Silicon, current generation **[VERIFY the Aug-2026 lineup — chips and Mac Studio/Pro configs
  released since May 2026 are unknown to the packet author]**. Known reference points: M4 Pro 273
  GB/s, M4 Max 546 GB/s, M3 Ultra 800 GB/s.
- Single NVIDIA datacenter GPU (A100 80GB / H100 80GB / current equivalent).
- Dual H100 NVLink or current equivalent.
- RTX 6000-class workstation card(s).

**The specific comparison that decides it:** Apple unified memory wins on capacity-per-dollar and
power; NVIDIA wins on prefill compute and on *batched* multi-user serving (vLLM continuous batching).
Given a 37:1 input:output ratio, a 110k peak context and a multi-user requirement, the packet author's
expectation is that **NVIDIA wins and the June "Mac Studio" conclusion does not survive contact with
the trace data** — but that expectation rests on pre-May-2026 chip knowledge and must be checked
against current Apple Silicon prefill benchmarks. **If prefix caching reaches Vertex parity the
margin narrows sharply** — 19.5k of prefill in a 34.7 s budget is a far easier target than 98.6k, and
that is the case in which Apple Silicon becomes genuinely viable.

### 4.3 The arithmetic to actually run

For each candidate, compute the median interactive-turn wall clock **twice** — once assuming prefix
caching reaches Vertex parity, once assuming none:

```
per interactive turn (median, measured 2026-08-29):
  prefill, cached at parity  ~19,500 tokens  / (prefill tok/s)
  prefill, no caching        ~98,600 tokens  / (prefill tok/s)
  decode (incl. thinking)     ~2,633 tokens  / (decode tok/s, single stream)
  target                     <= 34.7 s median

at p90:
  prefill ~40,000 cached-parity / ~203,700 uncached ; decode ~5,974 ; target <= 58.5 s
```

**Note the pipeline is sequential**, not parallel: coordinator → specialists → synthesizer. Ollama
queues; batching helps concurrent *users*, not a single user's chain. Aggregate throughput does not
rescue single-user latency.

---

## 5. The lever worth more than hardware

Mike's constraint 3 says the next build will be more efficient. Here is where the remaining efficiency
is. **Two of the four levers in the earlier draft have already been pulled** — caching is live at 76%,
and output volume is down to 775 tokens per request. What is left:

1. **Peak context, not median context.** Relationships hits 111k and logistics 106k on a single call.
   These two agents set the KV cache requirement for the whole machine and are 5× the median. Cutting
   the tail is worth more than cutting the average, because the tail is what you buy memory for.
2. **Specialist turn counts.** Median 2–4, max 8 (relationships). Each turn re-prefills a growing
   context; the cached prefix helps the head of it, not the growth.
3. **Extending cache coverage.** The diarist is at **0%** and the coordinator at **56.8%**, against
   79–96% for the specialists. The coordinator runs on every single request, so its miss rate is
   multiplied by everything.
4. **Per-agent tool schemas** — logistics advertises ~30 of them, in every prompt, every turn, and
   they sit in the cacheable prefix only if prompt assembly puts them there.

**Recommendation to carry into the outside session:** get the spec for today's shape as asked, but
note that item 1 is the one that changes the hardware class. A build that keeps peak context under
~50k can be served by materially cheaper hardware than one that spikes to 111k.

---

## 6. Ready-to-paste prompt for the outside session

> **Model: a frontier model with web search enabled** (Claude with web search, or equivalent). This
> task is entirely dependent on current leaderboard and chip-spec data; a model answering from
> training knowledge will produce a confidently wrong spec.

```
I need a hardware specification for a self-hosted, always-on, single-purpose inference box.
Use current web sources - model leaderboards and vendor spec sheets as of today. Flag
anything you are inferring rather than reading.

WORKLOAD - all figures measured in production on 2026-08-29, one user, full day, 33
requests. Not estimated.

Shape: a personal AI assistant. 17 agents in a SEQUENTIAL pipeline:
coordinator -> 1 to 4 specialists -> synthesizer. Specialists are multi-turn (median 2-4
model calls per dispatch, max 8), with context growing each turn.

Volume, per interactive turn (median / p90):
- Total input tokens processed:      98,600 / 203,700
- Of which served from prompt cache: 76% (this is live and measured, not aspirational)
- UNCACHED input to prefill:         19,500 / 40,000
- Decode tokens generated,
  including thinking tokens:          2,633 / 5,974
- Ratio of input to output: roughly 37 to 1. This is a PREFILL-BOUND workload.

Peak single-call context: 111,000 tokens. Two agents exceed 100k. KV cache must be sized
for that, not for the median.

Day totals for one user: 2,232,045 input tokens (1,696,436 cached), 25,570 output,
36,167 thinking, across 33 requests. Load is bursty - two clusters of 6 and 12 requests
within ~30 minutes each, sparse otherwise.

LATENCY TARGET - current performance on Google Vertex (Gemini 3.1 Pro + Flash-Lite):
- Interactive turns (3+ agents, n=20): median 34.7s, p90 58.5s   <- THIS IS THE TARGET
- Simple turns (1-2 agents, n=13): median 2.9s
- Background scheduler runs (n=9): median 36.0s, nobody waiting
Parity is acceptable. I do not need it faster.
The single largest contributor is the synthesizer at 17.1s median; it runs last and
cannot be parallelised.

MODEL REQUIREMENT - two tiers must be resident and serving concurrently:
- DEEP tier (5 agents): must match Gemini 3.1 Pro. The user-facing conversational voice,
  plus mental-health and physical-health agents with hard safety requirements (specific
  clinical flags must fire in every test scenario; financial arithmetic must be 100%
  accurate). Emits thinking tokens today.
- FAST tier (12 agents): must match Gemini 3.1 Flash-Lite. Routing, closed-schema
  extraction, mechanical writes.

CONSTRAINTS: always on, dedicated to this workload only, 1 user today but spec so it does
not need replacing at 4-10 concurrent users. Budget is not the primary constraint. All
inference for these agents stays on the machine - that is the entire point of the exercise.
Background load: nightly analytical jobs (the heaviest class), Whisper STT base.en, FAISS
plus sentence-transformers embeddings. These must not contend with interactive turns.

DELIVER:

1. PREFIX CACHING FIRST. My 76% cache hit rate is a 5x swing in prefill load (19,500 vs
   98,600 tokens per turn). For each serving stack you consider (vLLM, llama.cpp, SGLang,
   TensorRT-LLM, MLX), tell me: does it do automatic prefix caching, what hit rate is
   realistic on a workload with a large shared system prefix and a rotating tail, does the
   cache survive across concurrent sessions, and does it survive a model reload. Every
   later answer depends on this one.

2. Best current open-weight model at Gemini 3.1 Pro level, and at Flash-Lite level.
   Parameter count, dense or MoE, size at Q4_K_M and Q8. If nothing open-weight reaches
   Pro, say so plainly and quantify the gap - that gap is the real cost of going local.
   State whether the deep-tier candidate emits extended thinking tokens and what that does
   to the decode budget above.

3. Hardware options compared on MEASURED PREFILL throughput at 20k, 50k and 110k context.
   Treat decode tok/s as secondary but report single-stream separately from batched,
   because my pipeline is sequential and batching does not help one user's latency.
   Compare:
   (a) current-generation Apple Silicon, top config - tell me what Apple actually ships
       today including anything announced recently, since I may not have current info;
   (b) single A100 80GB / H100 / current datacenter equivalent;
   (c) dual H100 NVLink or current equivalent;
   (d) RTX 6000-class workstation cards.
   For each: total memory required (weights for BOTH tiers resident + KV cache at 110k x N
   concurrent + ~15GB for OS/Whisper/FAISS), sustained vs burst throughput, idle and load
   power draw.

4. For each candidate, compute median interactive-turn wall clock TWICE - once assuming
   prefix caching reaches parity with what I have today, once assuming none - at 1, 4 and
   10 concurrent users, against the 34.7s target.

5. A recommendation, and the single number that decides it.
```

---

## 7. Cost note

Mike set budget aside for this stage, so no ceiling is proposed. Three figures belong on the record
anyway, per the standing cost rules:

- **Run cost being replaced:** measured 2026-08-29, real use is **~$1.50–2.00/day** on Vertex
  (~$550–730/year), against a measured 2.23M input / 25.6k output tokens that day. Any hardware
  purchase is a privacy decision, not a saving — at that baseline the payback on a serious box is
  measured in years, not months.
- **The 76% cache hit rate is load-bearing on that cost figure too.** Whatever replaces Vertex has to
  reproduce it or the run cost of the *current* path is not the right comparison either.
- **New standing cost created:** an always-on machine draws power 24/7 whether or not anyone talks to
  it. That is a wall-clock-billed cost, invisible to every per-request meter in the project. It needs
  a figure before purchase, not after.
