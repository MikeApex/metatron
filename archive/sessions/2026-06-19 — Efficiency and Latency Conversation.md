# 2026-06-19 — Efficiency and Latency Conversation

**Session type:** Design / planning conversation
**Goal:** Resolve model tiering for routing_cloud.yaml, implementation order for the five efficiency layers, and produce a prioritized list the user agrees with before any build work begins.

---

## Context entering this session

- Baseline measured live: 60–90s end-to-end for a simple voice prompt
- All 14 agents on gemini-3.1-pro-preview in routing_cloud.yaml
- Vertex migration for run_session_gemini_grounded() complete (2026-06-19)
- run_session_gemini() already routes to Vertex via OpenAI-compat when GOOGLE_CLOUD_PROJECT is set (confirmed in code)
- Five efficiency layers identified (from roadmap D2 + new Vertex context)

---

## Key decisions / findings

### Consistency finding
`run_session_gemini()` already routes to Vertex via OpenAI-compat when `GOOGLE_CLOUD_PROJECT` is set — the "open prerequisite" in the session prompt was already complete from the 2026-06-19 Vertex session. What remains is migrating to the native `google-genai` SDK agentic loop (Layer 0, separate chat).

### Model tiering (done)
- coordinator → Flash (routing task, no deep reasoning)
- synthesizer → Pro (user-facing voice, safety flag integration)
- mental_wellbeing, physical_health → Pro (clinical flags, never downgrade)
- pattern_miner, goals_interviewer, research_agent → Pro
- diarist, work_vocation, relationships, finance, learning_growth, recreation_hobbies, logistics → Flash

### Diarist fire-and-forget (done)
- `fire_and_forget: bool = False` added to `run_subagent()` in `tools/subagent.py`
- Schema updated to include `fire_and_forget` field
- `coordinator.md` updated: Diarist always dispatched with `fire_and_forget=true`, excluded from SPECIALIST_OUTPUTS
- Diarist receives Coordinator-packaged context at dispatch time (not Synthesizer output); this is fine — diary entry would be identical either way

### Prefix caching (done)
- `load_recent_context()` output moved from system prompt to user message in `_run_single_agent()`
- System prompt is now stable per agent per session → KV prefix cache can activate across all specialist calls
- User message format: `[Recent context]\n{recent}\n\n---\n\n{user_input}`
- Run A4 clinical-flag hard-fails as acceptance gate before shipping

### Agreed implementation order
0. Native SDK agentic loop migration — separate chat
1. ~~Model tiering~~ — done
2. ~~Diarist fire-and-forget~~ — done
3. ~~Prefix caching~~ — done
4. Streaming (Synthesizer → PWA) — separate chat
5. Output compression (Recreation first, one agent at a time)
6. Instruction file slimming — later

---

## Files referenced

- `core/orchestrator.py` — run_session_gemini(), run_session_gemini_grounded(), _run_single_agent(), run_pipeline_session()
- `config/modules/routing_cloud.yaml` — current all-Pro assignments
- `core/router.py` — routing resolution logic
- `archive/plans/phase5_to_future_roadmap_2026-06-10.md` — Section 2/D2, Section 4

---

## What was built / changed

| File | Change |
|---|---|
| `config/modules/routing_cloud.yaml` | Model tiering: coordinator and 6 specialists → Flash; MW, PH, pattern_miner, goals_interviewer, research_agent, synthesizer → Pro. Added `quick_override` section (Flash). Coordinator reverted to Pro after Flash tool-call reliability failure. |
| `tools/subagent.py` | Added `fire_and_forget: bool = False` to `run_subagent()` — dispatches agent in background thread, returns immediately. Schema updated. Empty string removed from `complexity` enum (native SDK rejects it). |
| `config/agents/coordinator.md` | Diarist dispatch instruction: `fire_and_forget=True`, exclude from SPECIALIST_OUTPUTS. Added CRITICAL block prohibiting fabricated specialist outputs. Tools list updated. |
| `config/agents/recreation_hobbies.md` | Output format changed from labeled text to compact JSON schema. |
| `config/agents/synthesizer.md` | Added note: specialist outputs may be JSON or prose — integrate both. |
| `core/orchestrator.py` | `_run_single_agent()`: recent context moved from system prompt to user message (`augmented_input`) for KV prefix cache activation. Debug print of coordinator package added (dev). |

## Key decisions

- **Coordinator stays on Pro** — Flash skips tool calls on complex routing tasks (confirmed across 3 tests). The 2.4s→4.6s speed difference is not worth fabricated specialist outputs.
- **Fire-and-forget wired in code but coordinator model not using it** — model passes `complexity="quick"` instead. Open issue.
- **Recreation JSON format not followed** — model output prose despite instruction. Needs stronger instruction or different approach.
- **Baseline: 16–20s simple session, 65–74s complex multi-specialist session** — improvement from 60–90s baseline, driven by model tiering and prefix caching.

## Test results

| Test | Time | Notes |
|---|---|---|
| Simple session (run + feeling good) | 20.3s | First baseline after changes |
| Simple session (walk in park) | 16.5s | No specialists dispatched by coordinator |
| Guitar (complex, clinical flags) | 65s | 4 parallel specialists + PH sequential follow-up; correct mania detection |
| Camping (Flash coordinator) | 21s | Flash fabricated specialist outputs — no actual tool calls |
| Camping (Pro coordinator) | 74s | 5-turn coordinator loop; 68K tokens accumulated |

## Final state at session close

**Resolved this session:**
- Fire_and_forget: code-enforced in `tools/subagent.py` — `agent_name == "diarist"` forces `fire_and_forget=True` regardless of model parameter. Confirmed working: diarist excluded from SPECIALIST_OUTPUTS, coordinator doesn't wait for it.
- Recreation JSON: stronger instruction ("Begin with `{` end with `}`") confirmed working. Synthesizer consumed JSON correctly and produced natural response.
- quick_override added to `routing_cloud.yaml` (Flash) — diarist routes to Flash via quick_override path.
- Coordinator reverted to Pro — Flash skips tool calls unreliably (confirmed across 3 tests).
- Coordinator debug print (`--- COORD PACKAGE ---`) kept active in `core/orchestrator.py` for development.

## Open / deferred

1. **Coordinator 6-turn loop / 88K token accumulation** — handed off to new chat (coordinator slimming prompt above). Target: ≤3 turns, ≤40K tokens at coordinator done.
2. **Streaming** — separate chat running.
3. **Native SDK migration** — confirmed working (`gemini-native` in trace).
4. **Output compression for other agents** — Recreation done; Logistics, Work/Vocation next after coordinator slimming confirms the pattern works.
