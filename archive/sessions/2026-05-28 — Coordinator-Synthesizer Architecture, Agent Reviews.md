# 2026-05-28 — Coordinator-Synthesizer Architecture, Agent Reviews

## What happened

---

### Agent reviews completed or updated

#### Learning & Growth — substantially revised

The original file was too consumption-focused ("books read" model). Key changes:

- **Role reframed**: domain is consuming, doing, building, AND experiencing with intent to grow. Experiential learning explicit: fixing a gasket, exploring a neighborhood, visiting a museum.
- **Language learning overstepped** in first revision (was an example, not a flagship) — corrected to "one example among many."
- **Active learning partnership** section added: study plans, lifetime learning roadmap, active engagement (review/discuss/encode), materials development. Learning science (retrieval practice, spaced repetition, deliberate practice) as an informing framework, not a prescribed methodology.
- **Skill goal management** framed like fitness goals: frequency targets, streak tracking, maintenance windows.
- **Flags** substantially expanded: PRACTICE_GAP, GOAL_DRIFT, CONSUMING_NOT_DOING, HIGH_MOMENTUM, MILESTONE_REACHED, RECURRING_THEME, EXPERIENCE_LOGGED.
- **Data categories** expanded: `skills`, `experiences`, `creative_output` added. `media` context-dependent (learning vs entertainment).
- Spaced repetition removed from backlog, folded into learning science paragraph.

#### RESEARCH_NEEDED flag — applied to all agents

Earlier versions incorrectly said "use the Research Agent" in specialist files. Architecturally wrong: specialists can't call each other. Correct pattern established:

- Specialists flag `RESEARCH_NEEDED: [specific question]` in their structured output
- Coordinator routes to Research Agent
- Applied consistently to: Learning & Growth, Physical Health, Work & Vocation, Relationships, Mental Wellbeing, Recreation & Hobbies, Finance, Logistics, Time Director

#### List management — applied to all agents

`write_archive` / `read_archive` explicitly described as persistent list storage in every agent's tools section. `write_config` added where plan/roadmap storage makes sense. Examples given per agent (reading lists, watchlists, travel destinations, shopping lists, contacts, supplement lists, etc.).

Shopping list management and travel itinerary management removed from Logistics backlog — supported now via archive/config tools.

#### Physical Health — role expanded

"No advice" framing removed. Agent is now explicitly an active advisor: builds workout plans, sleep protocols, dietary approaches. "Not a medical professional" disclaimer retained for clinical/diagnostic limits.

#### Finance — tools updated

`write_archive` (portfolio watchlist, bills, accounts) and `write_config` (budget plans, financial plans) added to tools.

#### Time Director — patched

Confidentiality section added (was missing — predates specialist architecture). `RESEARCH_NEEDED` note and `write_config` added to tools.

#### Mental Wellbeing — `write_journal` added to tools (was missing).

#### Gemini MCP default

`ask_gemini.py` updated: `DEFAULT_MODEL` changed from `gemini-2.5-flash` to `gemini-3.1-pro-preview`. `set_model` docstring updated to reflect new default.

---

### Head architecture — full redesign discussion

This was the primary work of the session. The existing Coordinator + Time Director architecture was examined and found to be architecturally inconsistent. A full redesign was worked out.

#### Three functional roles identified at the head level

1. **User communication and social parsing** — receiving/interpreting input, delivering responses with appropriate tone
2. **Technical routing and agent management** — deciding which specialists to call, fanning out, collecting results
3. **Integration and reasoning** — synthesizing specialist outputs, applying user context and values, determining direction

#### Multi-model consultation

Prompt sent to Gemini (Flash), Gemini Pro (3.1), and GPT-4o asking: one, two, or three agents for these three roles?

**All three models recommended two agents.** Gemini Pro's framing was sharpest: "What should we do?" (Orchestrator: input parsing + routing) vs. "What does it all mean and how do we say it?" (Synthesizer: integration + response formulation).

Key insight: routing is not separable from intent parsing — they're the same cognitive act. Pairing them in one agent is more coherent than separating them.

#### Architecture settled: Coordinator + Synthesizer

- **Coordinator** (Ears): receives user input, maintains conversation context, resolves intent, decides which specialists to call, fans out in parallel, passes full context package to Synthesizer. Does NOT receive specialist outputs. Does NOT speak to user.
- **Synthesizer** (Brain + Mouth): receives context package from Coordinator + specialist outputs directly, integrates and reasons, formulates and delivers user response. Handles Time Director's prioritization intelligence (built in, not a separate agent).

**Time Director** integrated into Synthesizer — prioritization and direction intelligence lives inside Synthesizer's core reasoning. Time Director as a standalone file to be retired.

#### Pipeline, not nested

Neither agent calls the other as a subagent. The orchestrator manages the handoff as a pipeline:
1. Coordinator pass: intake, context resolution, routing decision + specialist fan-out
2. Specialist outputs + Coordinator context package delivered to Synthesizer
3. Synthesizer integrates and responds to user
4. Synthesizer sends internal note back to Coordinator for thread update

No return trip through Coordinator. Coordinator never sees specialist outputs. Synthesizer never appears as a subagent of Coordinator.

#### Code function vs. LLM agent for Coordinator

Polled Gemini Pro and GPT-4o. Both recommended LLM agent over code function. Key reason: the config-driven design philosophy ("if changing behavior requires a code change, that's a design failure") — routing rules in a config file are editable; routing rules in Python are not.

**Semantic routing via embeddings** noted as a future optimization:
- Write 2-3 sentence specialist descriptions in config
- Embed at startup using existing FAISS infrastructure
- Route by cosine similarity — config-driven, semantically aware, near-zero cost
- Handles "which specialists to call" but not "what to pass them"
- Flagged for future development, not Phase 5 work

#### Context management design

**What Coordinator passes to specialists**: not raw input. Coordinator contextualizes each specialist call — current message + relevant conversation thread + specific directive for that domain.

**Trailing chain problem**: "Yes, I'd like to discuss this further" is meaningless without prior context. Coordinator holds the conversation thread and resolves ambiguous references before routing. Should ask for clarification rather than guess.

**Tiered working memory** (session-start loading):

| Tier | Content | Detail |
|---|---|---|
| Always | Prime Directive, Mission, Goals | Full |
| Past 24h | Daily logs + gap since last Pattern Miner run | High detail |
| Past week | Compressed key events, flags | Medium |
| Beyond | Pattern Miner trend summaries | Low |
| On-demand | Specific topics via search_memory | Full |

Session-start query once; targeted queries on cache miss mid-session. 24h detailed + week compressed is the right working window — users reference freely within a session, minimally context the previous day, almost always re-introduce beyond that.

Running context object maintained live during session: `user_baseline`, `conversation_thread` (per-exchange entries), `active_threads` (open topics with flags).

**Subagents report to Synthesizer directly** — not back to Coordinator. Avoids telephone problem. Context flows from Coordinator to both specialists (as directives) and Synthesizer (as full context package) in parallel.

**Internal note from Synthesizer to Coordinator**: what was surfaced to user, what was held, flags to track for next exchange, what follow-up specialist calls were made. Coordinator updates conversation thread from this note, not from the user-facing response.

#### Synthesizer's multi-round chains (ReAct pattern)

Synthesizer can make conditional sequential specialist calls based on what initial outputs reveal. This is not rare — it's the normal behavior for multi-domain situations.

Example: "I have a sore throat" → Physical_Health (initial) → reveals possible allergies → Research (pollen count) → high pollen confirmed → Logistics (add allergy medicine to grocery list). Each call is conditional on the previous result.

**Governor: quick/deep complexity hint**
- `quick`: respond with initial specialist outputs, no follow-up chains
- `deep`: follow the chain as far as the problem warrants

**Default: 3 rounds maximum.** If Synthesizer needs more after 3 rounds, it flags this explicitly and explains why — catchable in user testing.

**Mid-chain user updates**: Synthesizer can and should update the user during long chains: "Hang on, I'm checking on this and we'll come back to it in a moment. Are you experiencing any other symptoms?" Keeps the user informed without leaving them in silence.

---

## Key decisions

- **Two-agent head**: Coordinator (context + routing) + Synthesizer (integration + response). Pipeline, not nested.
- **Time Director integrates into Synthesizer** — not a separate specialist. Prioritization intelligence is part of Synthesizer's core reasoning.
- **Subagents report to Synthesizer directly** — Coordinator never sees specialist outputs.
- **Coordinator passes full context package to Synthesizer** — original message + resolved intent + conversation thread. No telephone problem.
- **3-round default** for Synthesizer follow-up chains. Flag + explain if more needed.
- **Synthesizer can update user mid-chain** ("Hang on, checking on this...").
- **Semantic routing** noted as future optimization (FAISS-based, config-driven). Not Phase 5 work.
- **Tiered context loading** at session start: 24h high detail + week compressed. Infrastructure exists; loader not yet built.

---

## What has NOT been built yet (next session)

The architectural decisions above are fully settled but not yet implemented in files. Next session:

1. Rename `coordinator.md` → `synthesizer.md` (keep integration logic, communication guidance; absorb Time Director's prioritization intelligence; reframe as non-routing agent; add multi-round chain behavior, 3-round limit, mid-chain user update pattern)
2. Create new `coordinator.md` (Ears): context management, tiered session-start loading, intent resolution with clarify-don't-assume directive, routing logic + specialist directory, produces context package for Synthesizer, receives internal note from Synthesizer)
3. Retire `time_director.md` (content absorbed into Synthesizer)
4. Update `core/server.py` — TBD: may need to stay as `coordinator` depending on pipeline implementation
5. Update `config/modules/routing.yaml` — add synthesizer
6. Update `core/orchestrator.py` — pipeline support (two-pass exchange: Coordinator pass → Synthesizer pass)
7. Continue specialist agent reviews: Mental Wellbeing, Physical Health, Work & Vocation, Relationships, Recreation & Hobbies, Research Agent, Logistics

---

## Files changed this session

- `config/agents/learning_growth.md` — substantially revised (see above)
- `config/agents/physical_health.md` — role expanded, RESEARCH_NEEDED + list tools added
- `config/agents/work_vocation.md` — RESEARCH_NEEDED + list tools added
- `config/agents/relationships.md` — RESEARCH_NEEDED + list tools added
- `config/agents/mental_wellbeing.md` — RESEARCH_NEEDED + write_journal added
- `config/agents/recreation_hobbies.md` — RESEARCH_NEEDED + list tools added
- `config/agents/finance.md` — list tools (write_archive, write_config) added
- `config/agents/time_director.md` — Confidentiality section added, RESEARCH_NEEDED + write_config added
- `config/agents/logistics.md` — RESEARCH_NEEDED + list tools added, backlog items moved to core
- `~/.claude/mcp_servers/ask_gemini.py` — DEFAULT_MODEL changed to gemini-3.1-pro-preview
- `archive/plans/coordinator_backup_2026-05-28.md` — created (backup of coordinator.md before refactor)
