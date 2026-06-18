# 2026-06-04 — Parallelization Planning, Side Quest Windows

## What happened

Full project review to map parallel work across separate Claude Code instances. Context: behavioral audits are the long-running main work; user wanted side quests for other windows.

---

## Project state at session start

- Phases 0–4 complete
- Phase 5 in progress: all agent instruction files written (Coordinator, Synthesizer, 9 specialists), core pipeline built, parallel subagent dispatch implemented, scheduler operational
- Coordinator and Synthesizer behavioral audits complete
- Specialist tool files: most specialists use existing shared tools (write_log, search_memory, write_journal, write_archive, crm.py, agent_config.py) — no new tool files needed for most
- Goals interview not yet run against real user (gates Phase 5 Check 6)

---

## Window assignments decided

**Window A (main):** Behavioral audits — working through the 9 Phase 5 specialists using `tests/agent_audit_template.md`. Coordinator and Synthesizer already done.

**Window B:** Token budget logging in `core/orchestrator.py` — add cumulative input token tracking per turn, warn at >8K. Needed for audit Probe 7. Edit orchestrator.py only.

**Window C:** Tool gap analysis (read each specialist agent file, check against registered tools, build only what's genuinely missing) + CalDAV integration (`tools/caldav.py` — read_calendar, write_calendar_event). Register any new tools in orchestrator.py at the end.

**Window D:** Security foundation documents — `archive/security/threat_model_2026-06-04.md` (OWASP LLM Top 10 + MITRE ATLAS mapped to this system) and `archive/security/security_backlog_2026-06-04.md` (all deferred security items collected). Write to archive/security/ only.

---

## Key clarification

Side quest windows produce **inputs to future checks only** — they do not close or mark done any plan item. Check 3 (intent loops), Check 7 (model selection testing), and the full Phase 6.5 security process still require explicit attention and testing steps after the side quest work is complete. Nothing is scratched from the list by running these windows.

---

## Audit queue (Phase 5 specialists, as of session end)

Work & Vocation in progress in separate window. Remaining: mental_wellbeing, physical_health, relationships, finance, learning_growth, recreation_hobbies, research_agent, logistics. Exact completion count unknown — user tracking separately.

---

## Files changed this session

None — planning session only.
