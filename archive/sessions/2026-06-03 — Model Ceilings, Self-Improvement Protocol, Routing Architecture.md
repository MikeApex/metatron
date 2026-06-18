# Session: Model Ceilings, Self-Improvement Protocol, Routing Architecture
Date: 2026-06-03

---

## What was covered

Architecture and capability planning session. No code written beyond targeted edits to synthesizer.md and planning documents. Gemini Pro consulted on model tier rankings.

---

## Key decisions and findings

### Search vs. model knowledge token economics
Web search adds large input tokens (prefill — fast, cheap) and often *reduces* output tokens by grounding the model. Net token-efficient vs. hallucinating a longer answer. Optimize by pre-classifying whether a query needs search at all.

### Model capability ceiling framework
Three ceiling types: hard (any model above threshold performs identically), soft (diminishing returns past a threshold), no ceiling yet (frontier capability still visibly pays off). Testing mechanism: run same prompts through tier ladder, score on task-specific rubric, find the elbow. Re-evaluate quarterly.

### Thinking tokens
Output tokens, billed at output rates. Same model throughout — no separate weaker model doing the thinking. The model writes a reasoning scratchpad before the final answer. o1/o3 and Claude extended thinking both follow this pattern.

### Token generation mechanics (plain language)
Input (prefill): all tokens processed in parallel, fast. Output (decode): one token at a time, sequential, memory-bandwidth-bound. This is why output tokens are slow and expensive while long inputs are relatively cheap.

### Chokepoint analysis — Coordinator is the real bottleneck
Synthesizer looks like the bottleneck but Coordinator failure propagates upstream to all specialists simultaneously. Routing miss by Coordinator = all specialists work from wrong input. Coordinator quality is the highest-leverage test investment. Synthesizer sanity-check added to catch gaps specialists miss.

### Per-call sensitivity evaluator — proposed for Phase 6
Python layer (no model call, ~1ms, zero tokens). Two layers: agent-type defaults (ALWAYS_LOCAL set) + directive content scan for cloud-eligible agents. Returns HIGH/MODERATE/CLEAN. Feeds into router override. Deferred to Phase 6 alongside dispatch sanitizer design.

### Dispatch sanitizer — Phase 6 design question
Harder problem: reformulating directives to remove implicit personal signal before cloud dispatch. Design questions: how to validate true decontextualization, information loss tradeoff, model vs. rule-based approach, full audit logging of reformulations.

---

## Model tier rankings

Gemini Pro and Claude both consulted. Key agreement and disagreements:

| Tier | Roles (synthesized) |
|---|---|
| Strongest | Synthesizer (deep sessions), Pattern Miner |
| Strong | Coordinator, Mental Wellbeing, Goals Interviewer, Finance |
| Medium | Physical Health, Work/Vocation, Relationships, Research Agent, Learning/Growth, Recreation/Hobbies |
| Light | Diarist, Logistics |

**Disagreement:** Gemini says Coordinator = Strongest (directive-writing requires frontier). Claude says Strong (70B) — task is constrained by structure; Synthesizer does unconstrained judgment. Ceiling testing will resolve empirically.

**Synthesizer in practice:** Strong (70B) by default; Strongest escalation via COMPLEXITY: deep for clinical signals and major decisions. Pattern Miner is the most economically justified use of frontier: highest analytical demand, batch schedule, low token frequency.

**B-parameter mapping:** Strongest = 200B-400B+; Strong = 65B-130B; Medium = 7B-34B; Light = 1B-7B.

---

## Model ceiling testing plan
Created: [tests/model_ceiling_plan_2026-06-03.md](../tests/model_ceiling_plan_2026-06-03.md)

**Methodology:** Ceiling-finding, not accuracy. Run each prompt through all tiers simultaneously. Where tiers produce equivalent output, lower tier has hit ceiling. Judge (Opus, Option B — evaluates independently) used only for QC on divergent cases, not for ceiling comparison.

**Discrepancy priority:** 1) Critical flags (MUST_SURFACE, CLINICAL_CONCERN), 2) Regular flags + routing equally.

**70B proxy:** Llama 3.3 70B via Groq. Budget-gate Opus/o3 — run only where Strong shows clear gaps. Revisit plan at later development stages.

**Alpha sizing:** max(12, hardware_max). Hardware_max from M5 Max optimized analysis = ~25-40. Target alpha cohort: 25-40 users.

---

## Self-improvement protocol — three stages
Full design in [archive/plans/future_phases.md](future_phases.md) under Self-Improvement Protocol.

**Stage 1 — Logging layer (before alpha, late Phase 5):**
- data/logs/quality_events.json (append-only)
- Synthesizer ROUTING_MISS → write_quality_event (sanity-check instruction already in synthesizer.md)
- Coordinator implicit correction detection
- PWA explicit "missed the mark" tap
- Existing signals (CHAIN_LIMIT_REACHED, PROFILE_GAP, TOOL_NOT_BUILT) wired in

**Stage 2 — Pattern Miner system health (Phase 6 start):**
- Second analysis pass over quality_events.json
- data/logs/system_health_YYYY-MM-DD.json (separate from user insights)
- Surfaces routing miss patterns, miss rate by message type, chain limit clusters, suggested config fixes

**Stage 3 — Observer Agent (Phase 6 ongoing, does not yet exist):**
- Reads system health reports, proposes specific text changes to coordinator.md and agent files
- Outputs data/logs/observer_proposals_YYYY-MM-DD.json
- All proposed changes require developer review before applying
- Full cycle: quality_events → Pattern Miner → system_health → Observer → proposed changes → Claude Code review → applied

---

## Files changed this session

| File | Change |
|---|---|
| `config/agents/synthesizer.md` | Added sanity-check bullet in "Integrating specialist outputs" section |
| `~/.claude/plans/local-model-routing-architecture.md` | Added sensitivity evaluator + dispatch sanitizer to Phase 6; added model tier rankings with Gemini Pro input |
| `archive/plans/future_phases.md` | Replaced brief Observer note with full three-stage Self-Improvement Protocol |
| `archive/plans/phase5_agent_reviews_continuation_2026-06-04.md` | Added BEFORE ALPHA section flagging Stage 1 logging layer as pre-alpha requirement |
| `tests/model_ceiling_plan_2026-06-03.md` | Created ceiling-finding test plan with per-role prompts, methodology, decision framework |
