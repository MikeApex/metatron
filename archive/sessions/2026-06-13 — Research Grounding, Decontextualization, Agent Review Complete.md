# Session Archive — Research Grounding, Decontextualization, Agent Review Complete
*2026-06-13*

---

## Session scope

Continuation of Phase 5 agent reviews. This session completed the Research Agent config revisions, implemented native Gemini search grounding in the orchestrator, hardened decontextualization across Coordinator and Synthesizer, and confirmed all 14 agent files are complete for Phase 5.

---

## Builds / changes completed

### Flag consistency audit (carried forward from 2026-06-11 session)

- **BASELINE_INCOMPLETE** and **PROFILE_GAP** — added to Flag Types of every specialist agent that referenced them in profile-building prose but not in Flag Types: mental_wellbeing, finance, physical_health, work_vocation, recreation_hobbies, relationships, logistics. learning_growth already had them; research_agent, pattern_miner, goals_interviewer, diarist don't use them.
- **logistics.md** — two fixes:
  - Step 7 used `OPPORTUNITIES_SURFACED` (undefined); corrected to `COORDINATION_OPPORTUNITY` (matching Flag Types)
  - `PENDING_CONFIRMATION` used throughout but not in Flag Types; added to Execution category
- **Not changed:** `PROACTIVE_OBSERVATIONS`, `MUST_SURFACE`, `CROSS_DOMAIN_SIGNAL` are output fields / condition triggers, correct to omit from Flag Types. Coordinator's `CLARIFICATION_NEEDED` and `PROACTIVE_FLAGS` are structural output fields defined in output format and prose.

### config/agents/research_agent.md — deep pass

- **Knowledge currency** — rewritten: use web_search proactively for time-sensitive queries; note inline where verification needed; professional review note where user may act on information. LIVE_DATA_NEEDED reframed as access signal (credential-gated sources not available), not a general uncertainty flag.
- **Scope limits** — rewritten: no hard limits; provide all information; note professional review where it genuinely matters. Don't withhold.
- **Output format** — simplified: rigid three-format structure removed. Research returns what best serves the query at the complexity Synth requested. quick / deep / intensive tiers preserved as Synth-controlled vocabulary.
- **Complexity guidance** — merged into output format section; Synth controls the tier, Research calibrates depth.
- **Flag types** — KNOWLEDGE_CUTOFF removed; LIVE_DATA_NEEDED and SCOPE_LIMIT reframed (SCOPE_LIMIT → PROFESSIONAL_REVIEW).
- **Tools** — web_search moved from "high-priority Phase 6 pre-req" to "build immediately — prerequisite for first real use." DuckDuckGo (`duckduckgo-search` package) identified as no-account starting point.
- **Sources** — always mandatory: step 7 and output format both require SOURCES field. Cross-referencing multiple sources added for consequential claims (medical, legal, financial). Citation sourcing removed from enhancement backlog (now standard behavior).
- **Enhancement backlog** — user-owned knowledge base access added: newspaper/magazine archives, data brokers, financial feeds (Bloomberg, Reuters); credential design to follow Logistics security model.

### config/agents/synthesizer.md — additions

- **Constructing research requests point 1–2** — rewritten to "send the question, not the context": strip identifiers, circumstance, and intent; keep only analytical parameters. Explicit that motivation/reasoning is not a relevant specific for Research.
- **Point 6** — added: Research always returns SOURCES; Synth can surface or use silently; follow-up verification call pattern for high-stakes outputs.
- **Internal flags section** — added: ROUTING_MISS, CHAIN_LIMIT_REACHED, TOOL_NOT_BUILT, ARCHITECTURE_GAP (with structured required fields), HELD.
- **Scope/recency sensitivity note (point 5)** — updated to match new Research framing.

### config/agents/coordinator.md — Research directive

- **Constructing the directive** — added: send the question, not the context. Strip identifiers, circumstance, and intent. Keep analytical parameters. Explicit example showing correct vs. incorrect framing.

### core/orchestrator.py — grounded Gemini search

- **`run_session_gemini_grounded()`** — new function using `google-genai` SDK (v2.8.0, native API). Enables Google Search grounding via `types.Tool(google_search=types.GoogleSearch())`. Extracts source URLs from `grounding_metadata.grounding_chunks`. Always appends `SOURCES:` field (URLs or `training knowledge`). Single-call, no agentic loop — Research Agent calls no tools of its own.
- **`_run_single_agent()`** — routing: when `agent_name == "research_agent"` and `provider == "gemini"`, calls `run_session_gemini_grounded` instead of OpenAI-compat path. All other Gemini agents unchanged.
- **Research system prompt** — stripped to role file only. No constitution, no personal config, no recent logs. Research is the one external-touching node; no internal documents should be accessible to it.
- **`google-genai` v2.8.0** — installed in venv. No requirements.txt exists in project; note for new machine setup.

### Tested

Full pipeline smoke test (Pepys persona): query about US mortgage rates → Coordinator routed to Research → grounded call returned current rates (6.52% Freddie Mac, 6.57% Bankrate, June 2026) with sources → Synthesizer integrated, responded in persona. Live data confirmed.

---

## Key decisions

- **Grounded Gemini over DuckDuckGo** — for Research Agent specifically, native Gemini API with Google Search grounding is the right call. Better quality, uses existing GEMINI_API_KEY, live citations. DuckDuckGo remains the fallback if Research ever routes to a non-Gemini model.
- **Logistics routes through Research via Synth** — Logistics has personal data in system prompt and cannot safely call grounded search directly. `RESEARCH_NEEDED` flag pattern is the correct design.
- **Constitution removed from Research system prompt** — constitution is internal to the tool. The system prompt is passed to Gemini's model layer (not to Google Search directly), but no internal documents should reach the one external-touching node in the system. Synth interprets Research output; Research doesn't need values alignment.
- **Intent stripping is distinct from identifier stripping** — Coordinator and Synthesizer now explicitly strip motivation, circumstance, and intent (not just names/locations) before sending to Research. Synth holds context and interprets Research's output against it. If Research doesn't return what Synth needs, Synth re-calls with a more precise query.

---

## Phase 5 agent review: confirmed complete

All 14 agent files complete (coordinator, synthesizer, diarist, mental_wellbeing, physical_health, work_vocation, relationships, learning_growth, finance, recreation_hobbies, research_agent, logistics, pattern_miner, goals_interviewer).

Remaining Phase 5 work is implementation (A1–A7), not agent review.

---

## Open items carried forward

- **web_search tool** — build immediately before first real Research use. `duckduckgo-search` is the no-account starting point; Gemini grounding is already live for Gemini-routed calls.
- **requirements.txt** — doesn't exist; `google-genai` v2.8.0 should be documented for new machine setup.
- **Phase 5 remaining:** A1 compliance curve, A2 logging layer, A3 cold-start baselines, A4 local routing enforcement, A5 goals interview, A6 token budget logging, A7 sign-off.
