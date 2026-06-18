# Security Backlog
*Deferred security items. Updated at the start of each phase. Addressed in full during Phase 6.5.*

Format: item, risk level (High/Medium/Low), status, deferred from.

---

## High

| Item | Risk | Status | Deferred from |
|---|---|---|---|
| Indirect prompt injection defense — wrap all external tool returns (email, calendar, web, contacts) in `<untrusted_content>` tags; instruct agents to treat content inside as data, never instructions | High | Deferred | Phase 5 / Deliverable 6 |
| Confused deputy mitigation — enforce in `core/orchestrator.py` that sub-agent text output is never parsed or executed as a tool call by the orchestrator or other agents | High | Deferred | Phase 5 |
| Human-in-the-loop confirmation for Finance tool executions — any tool that writes financial data should pause for explicit user confirmation, bypassing the LLM entirely | High | Deferred | Phase 5 |

## Medium

| Item | Risk | Status | Deferred from |
|---|---|---|---|
| Output filter hardening — replace keyword matching in `filter_output()` with a semantic classifier or regex-plus-embedding approach; current implementation can be bypassed by paraphrasing | Medium | Deferred | Phase 5 |
| Dynamic tool injection (Principle of Least Privilege) — only inject the tool schemas relevant to the current agent session, rather than all 25 tools in every session | Medium | Deferred | Phase 5 |
| Tool schema abstraction — consider abstracting internal tool names in schemas so agents see functional descriptions rather than implementation names (e.g. `log_emotional_state` not `write_log`) | Medium | Deferred | Phase 5 |
| Observer write sandbox — when Observer agent gains ability to write config files, ensure writes go through a review queue, not directly to the live config | Medium | Deferred | Phase 5 |
| Audit logging of tool calls — log every tool invocation (agent, tool name, timestamp, not content) for forensic use | Medium | Deferred | Phase 5 |

## Low

| Item | Risk | Status | Deferred from |
|---|---|---|---|
| Rate limiting on PWA endpoint — prevent brute-force probing of the `/session` API | Low | Deferred | Phase 2 |
| Full OWASP LLM Top 10 audit against live system | Low | Deferred | Phase 5 |
| Formal penetration test by external party | Low | Deferred | Phase 5 (pre-public release) |

---

*Last updated: 2026-05-27*
