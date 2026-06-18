# Session: Local Model Architecture, Token Generation, Hardware Analysis
Date: 2026-06-02

---

## What was covered

A deep-dive brainstorming session on the local model architecture for the life manager. No implementation was done — all decisions recorded for future implementation.

---

## Key decisions and findings

### Privacy flaw identified
The current routing.yaml sends Coordinator (Haiku) and Synthesizer (Sonnet) to cloud APIs. Both agents load all sensitive personal context (Prime Directive, Goals, logs, context tracker, specialist outputs) on every exchange. This is a fundamental privacy failure — local routing of specialists is meaningless if Coordinator and Synthesizer are cloud-routed. **Both must be local.**

### Hard-fail, not cloud fallback
For Coordinator and Synthesizer, the correct behavior when local is unavailable is to raise a hard error and surface a user message ("Local model unavailable — cannot process privately"). Silent cloud fallback is a privacy violation. A `fail_if_local_unavailable` flag is needed in the router.

### 12B / 70B split
- Coordinator → 12B (routing/classification only, speed matters, no depth needed)
- Synthesizer → 70B (user-facing, integrates all data, quality matters)
- All sensitive specialists → 70B
- Cloud agents unchanged (Research, Logistics, Learning, Recreation — no personal context)

### Diarist fire-and-forget
Diarist is write-only and never produces output that Synthesizer needs before responding. It should be dispatched asynchronously, excluded from SPECIALIST_OUTPUTS, and not block the critical path. This alone removes ~30-40s from interactive latency.

### Quick/deep classification + deferred processing
Simple acks ("headed to the gym") don't need synchronous specialist calls. A quick path: Coordinator classifies as `quick`, dispatches all specialists async, Synthesizer responds from context alone in ~5-15 tokens. Deep paths retain full specialist processing. All deferred work drains via background daemon (fits existing scheduler infrastructure).

### Output compression + action tags
Internal specialist outputs (never user-facing) should be compact JSON, not verbose prose:
- Current: 300-500 tokens per specialist
- Compressed: 50-100 tokens per specialist
- 10× reduction in background specialist processing time

Cross-specialist referrals should use structured action tags rather than prose:
`ACTION:logistics:add_item:{"item":"ibuprofen","urgency":"low"}`
`REFER:research:{"query":"..."}` / `SCHEDULE:{...}` / `NOTIFY:push:{...}`

15-40 tokens vs. 80-200 tokens per referral. Parsed by orchestrator, not interpreted by model.

### KV prefix caching
The static system prompt prefix (Constitution + agent instruction + goals) is the same across all calls to a given agent. Moving `load_recent_context()` from the system prompt to the user message makes the system prompt fully static and cacheable. Saves ~2-5s of prefill per call — modest but cumulative.

### Daily Pattern Miner
Running Pattern Miner daily (vs. weekly) keeps Coordinator context compact: 1 day of raw logs + compressed insight digest instead of 5 days of raw JSON. Quality improvement (synthesized signal vs. raw data) matters as much as the token savings.

---

## Full optimization impact — M5 Max 128GB

| Message type | Before | After |
|---|---|---|
| Simple ack | ~40-50s | ~4-6s |
| Moderate (2-3 specialists) | ~80-100s | ~15-18s |
| Complex (4+ specialists) | ~150-180s | ~22-26s |
| Evening close | ~120-150s | ~18-20s |

**User capacity: 25-40 users** with distributed time zones and occasional use patterns. Before optimizations: 5-8 users.

---

## Hardware context

### Memory bandwidth
The hardware governor for token generation speed (not FLOPS, not RAM size). Formula: `tok/s ≈ bandwidth_GB/s ÷ model_size_GB`.
- Apple Silicon UMA: 400-800 GB/s (on-chip, no PCIe overhead)
- NVIDIA VRAM (GDDR6X/HBM): 936-3,350 GB/s (on-card bandwidth, not PCIe)
- PCIe bus: 32-64 GB/s (bottleneck when model spills from VRAM to system RAM)
- System RAM (DDR5): ~100 GB/s (CPU inference only)

### M5 Max 128GB
Both 70B Q4_K_M (~40GB) + 12B Q4_K_M (~7GB) fit comfortably (~47GB of 128GB). Estimated ~45-55 tok/s on 70B.

Two 70Bs + 12B: ~87GB models + overhead = ~95-97GB. Fits but tight. Parallelism benefit (specialists run concurrently) is offset by bandwidth splitting — roughly neutral.

### RTX 3090 (2020-2021 mining workhorse)
- 24GB GDDR6X VRAM, 936 GB/s bandwidth
- Runs 7B-30B models well; cannot fit 70B (40GB required)
- NVLink removed on 30-series consumer cards — two 3090s can't pair properly
- M5 Max is more capable than two 3090s for 70B inference due to unified memory

### H100 NVLink pair (Hetzner co-lo)
- 160GB combined HBM3, ~150-200 tok/s for 70B
- Rental: €3,000-6,000/month; own + co-lo: ~€1,700-4,300/month (amortizing)
- Per-user cost: €60-225/user/month depending on user count and amortization stage
- Economic sense at 20+ users after year 2

---

## Deferred / open questions

- "GPT OSS 120B" — user referenced a model generating tokens exceptionally quickly. Not identified with certainty; likely a MoE architecture. Dense 120B would be slower than 70B; MoE 120B with ~35-40B active params would be competitive. Need original reference to confirm.
- Dynamic public/private routing: Coordinator could sanitize directives before cloud-routed specialist calls. Requires reformulation, not just stripping. Named future feature: dispatch sanitizer.
- Two 70B instances: bandwidth splitting roughly cancels the parallelism gain on M5 Max. Revisit if using a serving layer with finer memory control (llama.cpp server, vLLM).

---

## Files to change (implementation pending explicit direction)

See `/Users/md-homefolder/.claude/plans/1-what-is-the-curious-quilt.md` for the full implementation plan capturing all pending changes.
