# Check 10 — Agent Behavioral Audits (+ Scheduler Cadences)
*Open this in a new Claude Code session. Phase 5 sign-off check 10 prep (2026-06-10 roadmap, A7 table), plus the check 3 scheduler prerequisite. Largest Phase 5 testing task (est. 8–12 hours) — expect to span multiple sessions; this prompt covers kickoff and any continuation.*
*Parallel-safe: other chats are running simultaneously — see File ownership below.*

---

## Read these first, in order

1. `SESSION.md` — current state
2. `archive/plans/phase5_to_future_roadmap_2026-06-10.md` — A7 check 10 and check 3
3. `tests/agent_audit_template.md` — the instrument (7 probes per agent, incl. a 15–20 turn conversation)
4. `config/modules/routing.yaml` — routing tiers (defines your batching)
5. `config/modules/scheduler.yaml` — current cadence coverage (three agents only)

Do not begin until you've read all five.

---

## Task 1 — Behavioral audits, batched by routing tier

**Roster: the 12 specialists** — diarist, pattern_miner, goals_interviewer, mental_wellbeing, physical_health, work_vocation, relationships, learning_growth, finance, recreation_hobbies, research_agent, logistics. (Not Coordinator/Synthesizer — they get separate pipeline-level probes; propose those probes as a deliverable of this chat. Not Time Director — retired, no testing.)

**Batch 1 — local-tier agents**, run with `--provider ollama` so results reflect the actual runtime model (qwen3:14b). **Batch 2 — cloud-path agents** (research_agent and any still cloud-routed when you run) on their assigned models.

Per agent: run all 7 template probes, record results in `tests/agent_audit_{agent}_2026-06-11_{model}.md`. Any **Fail blocks deployment** — log it prominently; Conditionals need a documented resolution plan.

Probe 5 (sensitive data routing signal) note: if the A4 chat (local routing enforcement) hasn't landed when you audit, `--provider ollama` still gives a runtime-accurate session, but automatic-routing verification is pending — mark probe 5 "pending A4" rather than Pass, and re-verify after A4 lands.

Privacy note: no real user data exists yet (pre-A5). Probe content uses personas/synthetic data — unrestricted.

## Task 2 — Scheduler cadences (check 3 prerequisite)

`scheduler.yaml` covers coordinator, pattern_miner, physical_health only, but sign-off check 3 requires per-specialist proactivity. For each of the 12 specialists: either add a cadence entry to `config/modules/scheduler.yaml` (respect quiet hours; choose notification channel deliberately) or document it as **conversation-only** (no proactive trigger) with a one-line reason. Silence fails the check; either explicit answer passes. Record the full disposition table in your session archive — check 3 cites it.

## Output

1. One audit record per agent: `tests/agent_audit_{agent}_2026-06-11_{model}.md`
2. A summary table (agent × probe results) in the session archive, with all Fails and Conditionals listed first
3. Proposed Coordinator/Synthesizer pipeline-level probe set (for a follow-up session)
4. `scheduler.yaml` cadence additions + the conversation-only disposition table

---

## File ownership (parallel chats are live)

- **This chat owns:** `tests/agent_audit_*` records, `config/modules/scheduler.yaml`
- **Read-only on agent files** — they just completed their review passes. If a probe failure traces to an instruction-file defect, record the proposed fix in the audit record; do not edit the agent file (the head-layer files are owned by the A2 chat; the rest are frozen post-review pending user approval).
- **Do not edit:** `core/orchestrator.py`, `config/modules/routing.yaml` (A4+A6 chat), `tools/*`

## Session close

- Create `archive/sessions/2026-06-11 — Agent Behavioral Audits.md` early in the session, per convention (continuation sessions: same file, append).
- SESSION.md update at close: additive only — record audited count (n/12) and any Fails, do not rewrite other chats' lines.
