# Session Archive — Token Reduction Architecture and Implementation
*2026-06-24*

---

## What was built / changed

### Planning (pre-execution)
Worked through 5 architectural questions on token reduction before implementing:

1. **Program layer vs. AI for routing** — Hybrid: program layer handles file reads and schema filtering; Coordinator (still AI) handles intent routing and directive assembly.
2. **Two-tier agents (light/heavy)** — One file per specialist with `## Quick mode` and `## Deep mode` sections. Complexity flag in Coordinator directive activates the appropriate section. Instruction depth in quick mode reduces tool calls and output length; system prompt token cost is the same.
3. **Specialist context requirements** — Specialists need goals.yaml + targeted directive from Coordinator only. No constitution, no prime_directive, no independent context reload.
4. **Tool whitelist: constrict first** — Per-agent `allowed_tools` in routing.yaml. ~42 tools → 3–8 schemas per agent. Highest-leverage single change.
5. **Synthesizer scope** — Synthesizer (Pro, always) holds the full stack and integration layer. Proactive scans in deep mode only; cross-domain anticipation scan every exchange.

Additional design decisions resolved in planning:
- **Clinical detection two-layer:** Coordinator does basic overt crisis keyword check (routing-level); Synthesizer does nuanced escalation via run_subagent chains. Building trends caught by daily check-in sessions.
- **Session types as starting states:** Synthesizer evaluates and updates session_type in context_tracker each exchange. Any session can escalate via chain mechanism.
- **Phase 5 status:** A1–A6 complete; A7 blocked on B1 (red team), Check 10, Check 12 — on hold pending latency work stabilization. Two git tags: `v0.5-pre-refactor` (before changes) and `v0.5` (formal Phase 5 close at A7 sign-off).

### Implementation — Steps 1–5 complete

**Step 1: Git tag** — `v0.5-pre-refactor` created before any changes.

**Step 2: Per-agent tool schema whitelists**
- `config/modules/routing_cloud.yaml` — `allowed_tools` added for all agents
- `config/modules/routing.yaml` — same whitelists applied
- `core/router.py` — `ModelConfig.allowed_tools` field added; `get_allowed_tools()` function added; all three return paths in `resolve_model()` populate it
- `core/orchestrator.py` — schema filter in `_run_single_agent()`: only schemas in `allowed_tools` are advertised to the LLM; Python functions stay registered

**Step 3: Strip constitution/prime_directive from specialist system prompts**
- `core/orchestrator.py` — three-branch context loading: bare/research_agent (no context), head layer (full config + recent context), specialists (goals.yaml only)
- `_HEAD_LAYER_AGENTS = {"coordinator", "synthesizer"}` constant added
- `load_goals()` function added — loads only goals.yaml for specialist agents

**Step 4: Context via Coordinator directive**
- Specialists drop independent `load_recent_context()` call
- Context arrives via the Coordinator directive (passed in user_input); no independent reload

**Step 5: Quick/deep behavioral sections — all 8 specialist agent files**
Added `## Quick mode` (gate instruction) and `## Deep mode` (existing content, word-for-word) to:
- `config/agents/mental_wellbeing.md` — Quick mode inserted after `## CRITICAL` section; clinical detection explicitly active in all modes
- `config/agents/physical_health.md`
- `config/agents/work_vocation.md`
- `config/agents/relationships.md`
- `config/agents/finance.md`
- `config/agents/learning_growth.md`
- `config/agents/recreation_hobbies.md`
- `config/agents/logistics.md`

Existing agent language preserved exactly. Quick mode is a gate: extract → flag → log → return. Deep mode is all existing content unchanged.

---

## Deferred

**Step 6 (Coordinator restructure)** — Replace 3-turn multi-turn session with single-pass directive assembly. ~15,000t savings from Coordinator turn accumulation alone. Kept last; do only after Steps 1–5 are stable. This is the one architectural change; all others were config edits + a function filter.

**Post-implementation:** Resume B1 (red team), Check 10 (agent behavioral audits), Check 12 (constitution alignment review) → A7 Phase 5 sign-off → create `v0.5` formal tag.

---

## Token projections (targets, not yet measured)

- Steps 1–5 only: ~30,000t (~3× reduction from current ~95,000t)
- All 6 steps (including Coordinator restructure): ~18,500t (~5× reduction)

---

## Key decisions

- `allowed_tools` whitelist lives in routing.yaml — all routing config in one place; no agent `.md` file parsing changes
- Schema filter removes from API payload only; Python functions stay in `register_tools()` — additive change, fully reversible
- Two git tags rather than one: `v0.5-pre-refactor` (dev snapshot, before changes) and `v0.5` (formal Phase 5 close, at A7 sign-off)
- Mental Wellbeing clinical detection rules (`## CRITICAL`) apply in all modes — quick mode cannot suppress them
- Coordinator model selection (Flash vs Flash-Lite vs Haiku) deferred to testing on representative routing cases
