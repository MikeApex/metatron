# 2026-06-26 — Refactor Planning and A8

## What was discussed

Conceptual session — no code written. Two threads:

1. **General question: value of refactoring iteratively-built CC projects.** Established that the practice is well-known (refactoring, "second system," technical debt paydown; Kent Beck's "make it work, make it right, make it fast"). Key finding: AI-assisted iterative code accumulates structural debt faster than human-written code because each session solves a local problem without global architectural awareness.

2. **A8 scoped and added to the plan.** Initially added as a Phase 5 cleanup item; user clarified they meant a full program rewrite, not just Phase 5 artifacts.

## Decisions made

**A8 — Pre-Alpha code refactor (full program)** added to the roadmap between A7 and Track B. Alpha gate updated to require A8. Key decisions in scope:

- `core/orchestrator.py` (1870 lines) extracted into 4 modules:
  - `core/config.py` — config loading
  - `core/providers.py` — all `run_session_*` functions, loops, schema converters, Vertex utilities
  - `core/tools.py` — `register_tools()` and `dispatch_tool()`
  - `core/orchestrator.py` — pipeline only (slims significantly)
- `core/server.py` monitoring endpoints extracted to `core/monitor_api.py`
- Remove COORD PACKAGE debug print (`core/orchestrator.py` line 1616)
- Update import paths in server, scheduler, subagent, router

**Latent vs. legacy vs. switch distinction established (important for A8 execution):**
- `run_session_*` functions are active provider switches — stay in `core/providers.py`
- `_run_gemini_native_loop` is the hot path for Vertex cached sessions (`run_session_gemini_cached` calls it) — not dead, stays
- `run_session_gemini_cached` is called at line 1508 for head-layer and routing-layer agents — active
- Actual latent code is minimal; the problem is co-location, not accumulation

**Regression gate for A8:**
1. A4 clinical-flag hard-fail scenarios (MW MUST_SURFACE / CLINICAL_CONCERN, Finance arithmetic)
2. Server startup + `/health` check
3. Full pipeline session end-to-end
4. The Book SSE stream

## Step 6 clarification

User noted Step 6 (Coordinator single-pass) was already done — confirmed via commit `a2f8f10`. Removed from A8 scope accordingly.

## Files changed

- [archive/plans/phase5_to_future_roadmap_2026-06-10.md](../plans/phase5_to_future_roadmap_2026-06-10.md) — A8 added (full scope), Track A renumbering map updated, Alpha gate updated
- [SESSION.md](../../SESSION.md) — A8 entry updated to reflect full-program scope
