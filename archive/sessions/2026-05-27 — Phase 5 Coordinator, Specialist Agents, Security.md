# 2026-05-27 — Phase 5: Coordinator Build, Specialist Agents, Security Architecture

## What happened

### Deliverable 1 complete — Persona config support
Extended `--persona` flag in `core/orchestrator.py` → `load_config()` to load persona-specific Tier 1-3 files when a persona subdirectory exists. When `--persona ryan_holiday` is set, loads `config/personas/ryan_holiday/prime_directive.md`, `mission.md`, `goals.yaml` in addition to the character file. Verified with smoke test: Ryan Holiday persona loads Bastrop/bookstore/Stoic framing from correct files.

### Coordinator architecture — design decisions locked

After extended design conversation:
- **Coordinator** is the only user-facing agent. Specialists never speak to the user directly.
- **Flat architecture** — no agent-to-agent communication. Coordinator fans out to specialists in parallel, collects results, integrates, responds.
- **Central data lake** — no per-agent silos. All specialists read/write to the same `data/` store with their own field namespaces in the daily log.
- **Each specialist writes its own interpreted fields** (mood, sleep_hours, work.output, etc.) rather than raw data through the Diarist alone.
- **Coordinator uses intent-based routing** (option a) — specialist directory in coordinator.md describes each domain; Sonnet decides who to call. No hard lookup table.

### Tools built

**`tools/subagent.py`:**
- `run_subagent(agent_name, message, complexity)` — spawns a specialist session, inherits current persona from env
- `run_model_conference(message, models, agent_name)` — queries same message across multiple model tiers (`cloud_fast`, `cloud_deep`, `cloud_analytical`), returns all responses for Coordinator synthesis
- Both registered in `orchestrator.register_tools()` — 25 tools total

**Complexity routing** (`core/router.py`):
- `resolve_model(agent, complexity)` — `"quick"` → `cloud_fast`, `"deep"` → agent's configured tier
- Tier names in instruction files; model names only in `routing.yaml`. Agent files never reference specific models.

**`core/server.py`** — default agent changed from `time_director` to `coordinator`.

### `config/agents/coordinator.md` built

Key sections:
- Confidentiality (non-negotiable, canned refusal response)
- Onboarding and domain baseline interviews — Coordinator manages sequencing, reads user type (front-loader vs. avoidant), interviews are multi-session and never fully stop
- How you work — parallel fan-out, integration, multi-round consultation pattern
- Full specialist directory with signal words for each domain
- Cross-domain routing examples (anticipatory routing)
- `run_subagent` and `run_model_conference` documented with guidance on when to use each

### All 9 specialist agent files built (first pass)

`config/agents/`: mental_wellbeing.md, physical_health.md, work_vocation.md, relationships.md, learning_growth.md, recreation_hobbies.md, finance.md, research_agent.md, logistics.md

Each file contains: Confidentiality section, Capture first directive, Ongoing interview and profile building section, Role, What you do, Output format (structured block → Coordinator), Flag types, Data written, Tools available, Enhancement backlog.

**`config/modules/routing.yaml`** updated with all 9 agents. Sensitive agents (mental_wellbeing, physical_health, work_vocation, relationships, finance) target local with cloud_deep fallback. Recreation and Logistics target cloud_fast. Research Agent targets cloud_deep.

### Security architecture

**Research pass** — queried Gemini 3.1 Pro and GPT-4o alongside Claude's own assessment. Key findings:
- Architecture is the primary defense; instructions are secondary
- Defense in depth: instruction layer + code layer
- Indirect prompt injection (external data sources) is the highest-priority risk once Deliverable 6 integrations land
- Confused deputy attack is a real risk in multi-agent systems

**Instruction layer** — `## Confidentiality` section added to all 11 agent files (Coordinator + 9 specialists + existing agents implicitly covered). Canned refusal response: "I'm here to help you manage your life."

**Code layer** — `filter_output()` added to `core/orchestrator.py`:
- Scans all Coordinator responses before returning to user
- Any leaked tool/agent name → suppresses response, returns canned fallback, logs warning
- Sub-agent outputs (internal only) are not filtered

**`CLAUDE.md`** — Security Architecture section added documenting current controls and deferred items.

**`archive/security/security_backlog.md`** — all deferred security items tracked with risk levels.

**`tests/security_testing_plan.md`** — Phase 6.5 testing plan: 7 intent checks covering architectural opacity, indirect injection, cross-agent exfiltration, model-assisted red team (GPT-4o + o3 generate adversarial prompts), output filter, confused deputy, threat model coverage.

**`archive/plans/revision_3_1_snapshot.md`** — Phase 6.5 (Security Module) and Phase 6.75 (Legal & Compliance Audit) added.

### Finance agent redesign (agent review, session 1)

`config/agents/finance.md` substantially rewritten:
- **No-advice constraint removed** — Finance is a full financial companion and advisor for personal use. Legal audit scoped to commercial rollout (Phase 6.75).
- **Capture first** — every transaction of any consequence, every coffee and candy bar
- **Dual-category transactions**: every transaction has `financial_category` (budget math) and `life_domain` (values alignment: relationships, physical_health, learning_growth, recreation_hobbies, work_vocation, lifestyle, essential)
- **Budget status** tracked by both dimensions — Pattern Miner gets alignment signal automatically
- **NEW_HABIT_EXPENSE flag** — fires once when a recurring pattern first appears; notes monthly cost equivalent
- **12 flag types** including BUDGET_OVERSPEND, TAX_FLAG, CASH_DRAG, MARKET_ALERT, RESEARCH_NEEDED, BASELINE_INCOMPLETE
- **Scheduler behavior** — once daily default, adjustable up/down based on Finance Interview profile
- Spending categories are examples, not exhaustive — expand as usage reveals patterns

### Universal changes to all 8 personal specialists

- **Capture first** directive added to all
- **Ongoing interview** section rewritten: interview never stops, early questions establish basics, later questions explore nuance and change. `BASELINE_INCOMPLETE` and `PROFILE_GAP: [question]` flags are the mechanism for Coordinator-managed scheduling.

### Market Intelligence Daemon — architecture note

For commercial scale (Phase 7+), two-tier architecture documented in plan:
- Tier 1 (shared): monitors markets/news on schedule, writes to `data/market/`, zero personal data, fully cloud-routable
- Tier 2 (per-user): reads from shared brief + personal financial data, produces personalized assessment
- No daemon needed for single-user deployment; single daily Scheduler session sufficient

### Observer agent — phasing confirmed
- Alpha: propose-only mode (outputs diff for human review)
- Beta: automated mode enabled once Alpha evidence establishes trust

## Key decisions (summary)

- Coordinator is always the entry point; specialists never face the user
- Flat architecture: no agent-to-agent calls; all routing through Coordinator
- Central data lake, specialist-owned field namespaces
- Complexity hints (`quick`/`deep`) in instruction files; model names only in routing.yaml
- Security: architecture first, instructions second; filter_output() as code-layer catch
- Finance: full advisory, dual-category (financial + life domain), capture everything
- Interview: ongoing, never stops, Coordinator manages scheduling and user-type adaptation
- Dual spending categories bridge Finance to the broader life framework — Pattern Miner signal for values alignment
- Market Intelligence Daemon is a Phase 7+ concern; design schema to be Tier 2-compatible from day one

## Agent review status

- Finance: ✓ reviewed and rewritten this session
- Learning & Growth: open in IDE, next up
- Remaining: Mental Wellbeing, Physical Health, Work & Vocation, Relationships, Recreation & Hobbies, Research Agent, Logistics
- Time Director and Diarist (original agents): not yet reviewed against the new specialist architecture conventions

## Files changed this session

- `core/orchestrator.py` — persona subdirectory config loading, run_subagent/run_model_conference registration, filter_output(), complexity threading
- `core/router.py` — complexity parameter in resolve_model()
- `core/server.py` — default agent → coordinator
- `tools/subagent.py` — created: run_subagent, run_model_conference, both schemas
- `config/agents/coordinator.md` — created
- `config/agents/mental_wellbeing.md` — created
- `config/agents/physical_health.md` — created
- `config/agents/work_vocation.md` — created
- `config/agents/relationships.md` — created
- `config/agents/learning_growth.md` — created
- `config/agents/recreation_hobbies.md` — created
- `config/agents/finance.md` — created, then substantially rewritten
- `config/agents/research_agent.md` — created
- `config/agents/logistics.md` — created
- `config/modules/routing.yaml` — all 9 new agents added
- `CLAUDE.md` — Security Architecture section added
- `archive/plans/revision_3_1_snapshot.md` — Phase 6.5 (Security), Phase 6.75 (Legal/Compliance), Phase 7+ daemon note added
- `tests/phase5_testing_plan.md` — Checks 7–9 added (model selection, complexity routing, conference)
- `tests/security_testing_plan.md` — created
- `archive/security/security_backlog.md` — created
- `archive/plans/phase5_prompt_2026-05-26.md` — (read-only reference, not modified)
