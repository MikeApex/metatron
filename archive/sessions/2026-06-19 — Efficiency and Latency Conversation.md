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

## Key decisions / findings (to be updated as conversation progresses)

_In progress_

---

## Files referenced

- `core/orchestrator.py` — run_session_gemini(), run_session_gemini_grounded(), _run_single_agent(), run_pipeline_session()
- `config/modules/routing_cloud.yaml` — current all-Pro assignments
- `core/router.py` — routing resolution logic
- `archive/plans/phase5_to_future_roadmap_2026-06-10.md` — Section 2/D2, Section 4

---

## Deferred / open at close

_To be filled at session close_
