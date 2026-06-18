# Session Archive: Phase 4 Review + Phase 5 Planning
*2026-05-20*

---

## What We Did

### Architecture audit
- Clarified the Orchestrator's role: Python harness, not an agent. Agents are instruction files loaded into the prompt.
- Identified the MAIN coordinator gap: the tool was designed with a single front-door agent that routes to sub-agents, but no sub-agent dispatch mechanism was ever built or planned as a concrete build item.
- Confirmed the Time Director is a flat agent with no routing capability — it cannot invoke the Diarist or any other specialist.

### Full prerequisites audit (all phases)
Ran a cross-phase audit against the existing codebase. Key gaps found:

| Gap | Introduced | Affects |
|---|---|---|
| MAIN coordinator / sub-agent dispatch never designed | Phase 0 | Phases 3, 4, 5+ |
| Goals interview never run — prime_directive.md and mission.md blank | Phase 1 | Every phase |
| Sensitive routing not enforced (local_enabled=false) | Phase 3 | Phases 3, 4, 5+ |
| PWA stranded at single agent (no way to reach Diarist etc.) | Phase 2 | Phases 3, 4, 5+ |
| CalDAV never planned as a build item | Never | Phase 5 |
| Phase verification criteria requiring future-phase features | Phases 1, 3 | Planning integrity |

### Files created / updated
- `tests/phase0_testing_plan.md` through `tests/phase7_testing_plan.md` — intent-driven testing plans for every phase
- `CLAUDE.md` — added Phase Testing Convention and file naming convention (purpose + date + qualifier)
- `archive/plans/revision_3_1_snapshot.md` — Phase 5 fleshed out: MAIN coordinator as Step 1, goals interview as Step 2, specialist modules as Step 3, CalDAV as Step 4
- `core/server.py` — added `--persona` flag; sessions use `SERVER_PERSONA` env var as default
- `config/personas/*.md` (all 10) — added dev note instructing model to address user by first name
- `config/personas/mike.md` + `config/personas/mike/goals.yaml` — new blank bootstrapped-user persona for testing onboarding without goals interview

### PWA testing
- Server restarted with `--persona pepys`
- Samuel sent a test message requesting a diary entry
- Entry was written to `data/personas/pepys/logs/2026-05-20.json` by the Time Director (structured log, not free-form journal)
- Confirmed gap: entry went to `logs/` not `journal/` — Diarist was never invoked

---

## Phase 5 Plan (as updated)

1. **MAIN coordinator** — `tools/subagent.py` (`run_subagent` tool) + `config/agents/coordinator.md` + wire as default agent in server
2. **Goals interview** — run against real user; populate prime_directive.md, mission.md, goals.yaml
3. **Specialist modules** — order TBD after goals interview + user research session
4. **CalDAV integration** — first module requiring calendar awareness

See `archive/plans/revision_3_1_snapshot.md` for full detail.

---

## Open Questions Carried Forward
- Multi-model plan audit (GPT/Gemini cold read of the plan) — deferred, nice-to-have before Phase 5
- Local LLM routing: must resolve `local_enabled: false` before sensitive specialist modules go into production use
- Gemini 3.1 Pro baseline poll on state-anchored baselines — not completed in Phase 4 (503 error)
