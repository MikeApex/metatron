# Parallel Chat Launcher — Phase 5 Close
*2026-06-11. One prompt file per simultaneous Claude Code chat. Paste each into its own session.*
*All numbering per `archive/plans/phase5_to_future_roadmap_2026-06-10.md`.*

---

## The seven chats — all can run simultaneously

| # | Prompt file | Roadmap item | Type | Owns (files) |
|---|---|---|---|---|
| 1 | [a1_compliance_curve_prompt_2026-06-11.md](a1_compliance_curve_prompt_2026-06-11.md) | A1 | Design conversation (with you) | decision doc, `future_phases.md` |
| 2 | [a2_logging_layer_prompt_2026-06-11.md](a2_logging_layer_prompt_2026-06-11.md) | A2 (D3) | Build | quality-event tool, `synthesizer.md`, `coordinator.md`, `static/index.html`, `core/server.py` |
| 3 | [a3_cold_start_baselines_prompt_2026-06-11.md](a3_cold_start_baselines_prompt_2026-06-11.md) | A3 (D4) | Build | `tools/baselines.py`, `data/baselines/` |
| 4 | [a4_a6_local_routing_token_budget_prompt_2026-06-11.md](a4_a6_local_routing_token_budget_prompt_2026-06-11.md) | A4 + A6 | Build (combined: both live in the orchestrator) | `core/orchestrator.py`, `routing.yaml`, `tools/subagent.py` |
| 5 | [b1_red_team_prompt_2026-06-11.md](b1_red_team_prompt_2026-06-11.md) | B1 (6A/D3) | Test/probe | `tests/security_redteam_*`, test scripts |
| 6 | [check10_agent_audits_prompt_2026-06-11.md](check10_agent_audits_prompt_2026-06-11.md) | A7 check 10 + check 3 prereq | Audit (8–12 hrs, multi-session) | `tests/agent_audit_*`, `scheduler.yaml` |
| 7 | [check12_constitution_review_prompt_2026-06-11.md](check12_constitution_review_prompt_2026-06-11.md) | A7 check 12 | Read-only review | `archive/constitution_alignment_review_*` |

## Not in this set (sequential by design)

- **A5 Goals Interview (+ A5b, A5c)** — gated on A4's tests passing; you run it yourself in a terminal via [goals_interview_prompt_2026-06-09.md](goals_interview_prompt_2026-06-09.md). A5c additionally wants A1's decision.
- **A7 Phase 5 sign-off** — last, after everything above; runs `tests/phase5_testing_plan.md` checks 1–12.
- **B2–B4** — sequenced on B1's findings.

## Conflict rules baked into the prompts

1. `core/orchestrator.py` belongs to chat 4. Chats 2 and 3 may append one `register_tools()` entry each, as their final step, after a fresh re-read.
2. Head-layer agent files (`synthesizer.md`, `coordinator.md`) belong to chat 2. Chats 1, 6, 7 record proposed edits in their output docs instead of editing.
3. Specialist agent files are frozen post-review — audit/review chats propose, never edit.
4. `config/constitution.md` — no chat edits it, ever.
5. SESSION.md — each chat updates additively at close (its own line only); last chat to close leaves the current state.
6. Chats 5 and 6 run live sessions while chat 4 changes routing — they mark any probe that may be contaminated by concurrent edits and re-run it after the dust settles.

## Suggested order of closing

Chat 4 (A4+A6) closing early unblocks A5 and de-noises chats 5 and 6. Everything else closes in any order.
