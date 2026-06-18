# Phase 5 Agent Review — Continuation Prompt
*Use this to open a new Claude Code session for continuing the specialist agent review.*

---

You are Claude Code continuing development of a personal AI life manager.
Working directory: ~/Desktop/multi-model-mcp

Read these files before doing anything else:
- CLAUDE.md (architecture, conventions, terminology — read carefully)
- archive/sessions/2026-05-27 — Phase 5 Coordinator, Specialist Agents, Security.md (this session's work)
- archive/plans/phase5_prompt_2026-05-26.md (full Phase 5 context and deliverable plan)

Also check memory at ~/.claude/projects/-Users-md-homefolder-Desktop-multi-model-mcp/memory/MEMORY.md
and read any memory files that seem relevant.

---

## WHERE WE ARE

Phase 5 is in progress. The Coordinator architecture is built and the 9 specialist agents exist as first-pass skeletons. We are now reviewing each agent one by one — deliberate review with the user reading in the IDE and discussing changes in conversation.

**Coordinator and infrastructure: complete**
- `config/agents/coordinator.md` — full routing logic, interview management, security
- `tools/subagent.py` — `run_subagent` (with complexity hint) and `run_model_conference` built and registered
- `core/router.py` — complexity routing (`quick` → cloud_fast, `deep` → agent's configured tier)
- `core/orchestrator.py` — `filter_output()` security layer, all tools registered (25 total)
- `core/server.py` — default agent is now `coordinator`
- `config/modules/routing.yaml` — all 9 specialists registered

**Security architecture: complete for Phase 5**
- Confidentiality section in every agent file
- `filter_output()` in orchestrator catches leaked terms before user sees them
- `archive/security/security_backlog.md` — deferred items tracked
- `tests/security_testing_plan.md` — Phase 6.5 testing plan written
- Phase 6.5 (Security Module) and Phase 6.75 (Legal/Compliance Audit) added to plan

---

## AGENT REVIEW STATUS

### Done
- **Finance** ✓ — substantially rewritten this session (see session archive for full changes)

### Next up (Learning & Growth was open in IDE at end of last session)
- Learning & Growth
- Mental Wellbeing
- Physical Health
- Work & Vocation
- Relationships
- Recreation & Hobbies
- Research Agent
- Logistics

### Also to review eventually
- Time Director (original agent, predates specialist architecture — check against new conventions)
- Diarist (original agent — check capture-first directive is already there; it is)

---

## REVIEW CONVENTIONS ESTABLISHED

These patterns were established during the Finance review. Apply them to every agent:

**1. Capture first — universal**
Every personal specialist (not Research Agent) has a "Capture first" directive: log every event of consequence, no filtering in the moment, parse later. Already added to all 8 personal specialists.

**2. Ongoing interview — universal**
`BASELINE_INCOMPLETE` flag → Coordinator knows to schedule a domain baseline interview.
`PROFILE_GAP: [question]` → Coordinator decides when to surface it.
The interview never stops — early questions establish basics, later questions explore nuance and change. Coordinator manages scheduling and adapts to user type (front-loader vs. avoidant).

**3. Dual-category pattern (Finance-specific, but consider for others)**
Finance uses two category dimensions per transaction: `financial_category` (budget math) and `life_domain` (values alignment). Consider whether other agents warrant a similar dual-tagging approach for their logged data.

**4. Output format**
Every specialist returns a structured block to the Coordinator (not to the user). The format includes: state assessment, logged items, flags, pattern notes, suggested follow-up. Each specialist's flags should be comprehensive — incomplete flag lists were the main Finance gap.

**5. Advisory scope**
Agents advise within their domain. The "no advice" framing from the original Finance skeleton was wrong. Agents are knowledgeable companions, not passive loggers. They have opinions.

**6. Legal/compliance notes**
Health advice, financial advice, and relationship guidance may have legal implications at commercial scale. Note where applicable; don't constrain personal use.

---

## KEY ARCHITECTURAL DECISIONS (don't re-litigate)

- Coordinator is the only user-facing agent; specialists never speak to the user directly
- Flat architecture: no agent-to-agent calls; all routing through Coordinator
- Central data lake; specialists own their field namespaces in the daily log
- `quick`/`deep` complexity hints in instruction files; model names only in routing.yaml
- Market Intelligence Daemon is Phase 7+ (two-tier: shared market layer + personal Finance layer)
- Observer agent: propose-only in Alpha, automated in Beta

---

## WHERE TO START

Open `config/agents/learning_growth.md` in the IDE. The user will read it and provide feedback. Your job is to:
1. Listen to the feedback
2. Identify what's design-level (update the file) vs. universal (update all relevant agents)
3. Ask focused questions when the architecture implications are unclear
4. Update files after confirming direction

The review is deliberate and unhurried. Work through agents one at a time.
