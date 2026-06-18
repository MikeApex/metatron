# Session Archive — Agent Reviews, W&V Deep Pass, Proactive Scans, Synthesizer Integration
*2026-06-04*

*Note: verbatim .txt archive should be exported from the session UI per the global CLAUDE.md rule.*

---

## Session scope

Continuation of Phase 5 agent reviews. Entered with most agents reviewed at a first-pass level; this session completed the Work & Vocation deep pass, added proactive scans to the remaining agents, built two new tool modules, and made several architectural refinements.

---

## Builds completed

### tools/agent_config.py
- `write_agent_config(agent_name, key, value)` — writes to `data/config/{agent_name}.json`, merges with existing, 600 permissions
- `read_agent_config(agent_name, key="")` — reads full config or specific key
- Registered in orchestrator (35 total tools)
- Added to all 8 specialist agents' tools sections
- Replaces `write_config` for agent-owned persistent state; `write_config` now scoped to Goals Interviewer + scheduler entries only

### tools/wishes.py
- `write_wishes(section, content)` — 8 named sections
- `read_wishes(section="")` — read all or specific section
- `generate_emergency_card()` — plain-text first-responder card
- Registered in orchestrator
- **Access model:** Synthesizer is sole writer; reads deferred to Phase 6 (legal + structural design needed). No agent reads or writes the store directly — subagents surface data via `PROFILE_GAP` and Synthesizer writes. Logistics accesses emergency contacts through Synthesizer context package, not direct reads.

### config/agents/goals_interview_reference.md
- Output schema (goals.yaml, mission.md, prime_directive.md templates) and Phase 3 domain list extracted from goals_interviewer.md
- goals_interviewer.md reduced from 300 → 230 lines
- File lives at `config/agents/` (not `config/research/` — different type of content)

### archive/plans/future_phases.md
- Parking document for post-MVP features: environmental monitoring, Wishes full build, addiction/behavioral health, cognitive function profiling, User Engagement/compliance design, Observer agent

---

## Architectural decisions

### Wishes access model
Synthesizer is sole writer. No specialist reads or writes the store directly. Physical Health surfaces advance directive and medical POA via `PROFILE_GAP`; Logistics surfaces emergency contact needs via `PENDING_CONFIRMATION`; Mental Wellbeing surfaces personal/legacy topics via `PROFILE_GAP`. All written by Synthesizer. Read access design deferred to Phase 6 — legal jurisdiction questions + structural access control design needed together.

### Proactive scans — scheduling
Standing calls (MW and PH on every exchange) removed. Replaced with:
- Morning brief and evening close sessions: Coordinator explicitly routes to MW and PH for whole-person sessions
- Weekly PH review remains in `scheduler.yaml`
- MW standalone pulse removed (covered by morning brief)

### Overcommitment — system-wide
Synthesizer now watches for aggregate overcommitment across all domains proactively — not waiting for individual agents to flag it. Added as a named pattern in Synthesizer's integration guidance.

### Cross-domain divergence — Synthesizer
New guidance added: honor conscious trade-offs; compare against core goals/values files over time. A "devil's bargain" the user knows they're taking still gets compared against `goals.yaml`, `prime_directive.md`, `mission.md` — surfaced as a long-term question when divergence persists across multiple sessions.

### CRM access model
Relationships writes and reads CRM directly. Intentionally different from Wishes — operational data accumulating through daily use, not sensitive legal documents.

### config/voice.md
Planned for Phase 6+. Two reference points documented in `synthesizer.md` and `revision_3_1_snapshot.md`: (1) Chris Voss — tactical empathy, calibrated questions, mirror, no unsolicited verdicts; (2) Socratic method — ask questions to surface insight in the user so they own the conclusion and initiate action from genuine conviction.

---

## Agent changes this session

### work_vocation.md — deep pass
- **Baseline areas:** identity trap added (role creeping into identity); vocation vs. job distinction refined; flow state history; energy relationship with work
- **Role statement:** flow reframed as a diagnostic signal, not the organizing target; hard aligned work is equally meaningful
- **Cross-domain flow markers:** new section — MW and PH correlates that reinforce or complicate flow findings; `CROSS_DOMAIN_SIGNAL` note added to output
- **Work/Finance boundary:** dedicated section; conflation risk is primarily W&V's concern; salary conversation split by domain angle
- **Proactive scan:** drift, burnout trajectory, momentum reinforcement
- **What you do:** session-start `read_agent_config`, macro/micro spectrum assessment, career coaching for high-stakes situations
- **Output format:** `ENERGY_IN_WORK`, `MUST_SURFACE`, `PROACTIVE_OBSERVATIONS`, `CROSS_DOMAIN_SIGNAL`
- **Flag types:** `CAREER_CRISIS`, `OVERCOMMITMENT`, `FLOW_STATE` (with conditions), `POSITIVE_PATTERN`, `IDENTITY_TRAP`, `NEGOTIATION_OPPORTUNITY`, `MEETING_PREP`, `OFFICE_DYNAMICS`
- **Data schema:** `energy_in_work`, `vocational_alignment`, `career_notes`
- **Enhancement backlog:** Entrepreneurship module added

### finance.md
- Work-Finance boundary section added
- Proactive scan added (spending drift, goal slippage, upcoming obligations, opportunity windows)

### relationships.md
- Proactive scan added (reconnect signal, aging threads, isolation pattern)
- CRM access model section: Relationships writes/reads directly; completeness protocol; new contact onboarding
- `CONTACT_INCOMPLETE` flag added
- Community/service cross-signal note in backlog

### recreation_hobbies.md
- Service/volunteering as first-class category
- Proactive scan added (leisure gap, hobby lapse, service gap, recovery deficit)
- `SERVICE_ACTIVE`, `SERVICE_GAP`, `SERVICE_NUDGE_OPPORTUNITY` flags
- `service_activities` field in log schema

### learning_growth.md
- Proactive scan added; fixed to not privilege reading over other learning goals
- Cognitive function profiling + motivation modulation backlog
- `write_agent_config` / `read_agent_config` added

### mental_wellbeing.md
- Service, nature, and addiction cross-signal notes added to backlog
- Addiction: when patterns emerge, Synthesizer surfaces them as observations (not kept internal)
- `write_agent_config` / `read_agent_config` added

### physical_health.md — full restructure
- Medication criticality: `required | as_needed | optional` three-value model
- New `## Medication profile` section with "classification from profile, not judgment" rule
- Exercise schema: structured object (type, duration_minutes, intensity_rpe, focus, muscle_groups)
- Nutrition: `nutrition_notes` field; four input modes in backlog (estimation, photo, brand lookup, manual)
- Substances: `substances_logged` array; `VICE_LOGGED`, `BEHAVIORAL_PATTERN_CONCERN`, `CESSATION_SUPPORT` flags
- `write_agent_config` / `read_agent_config` added; `write_config` removed
- Backlog: daylight formula explicit, nature time, environmental snapshot pointer, addiction, advance directive contribution (via PROFILE_GAP to Synthesizer)

### synthesizer.md
- Cross-domain divergence guidance: honor conscious trade-offs; compare against core goals/values long-term
- Overcommitment as a system-wide proactive pattern
- `write_wishes` added (sole writer)
- `config/voice.md` planning note updated with Socratic method

### coordinator.md
- Standing calls section removed
- Cross-domain routing section: morning brief and day-close sessions always include MW and PH
- STANDING_CALLS was a temporary design; superseded by scheduler + whole-person session routing

### scheduler.yaml
- `evening_diarist` changed to `evening_close` with `agent: coordinator` (whole-person session)
- `daily_wellbeing_pulse` removed (covered by morning brief)
- `weekly_physical_review` retained (Sunday 09:30)

### logistics.md
- `write_config` scope clarified (scheduler entries only)
- `write_agent_config` / `read_agent_config` added for plan storage
- Emergency contact access via Synthesizer context package (not direct `read_wishes`)
- Indirect prompt injection security note for Deliverable 6 email/calendar integration

### tools/crm.py
- `primary_contact_type` field added: work_colleague, work_client, work_vendor, friend, family, romantic_partner, acquaintance, service_provider, other

### goals_interviewer.md
- Domain list and output schema moved to reference file
- Socratic method pointer (will live in `config/voice.md` when built)

### ~/.claude/CLAUDE.md
- Todo list pause rule added: show user the todo list before executing
- No full rewrites without permission rule added

---

## Open questions carried forward

1. **Vitamin D flag:** inference from modeled exposure (GPS + weather) vs. explicit user report only. Design decision needed before building.
2. **Wishes read access:** Phase 6 design session — legal jurisdiction + structural access control.
3. **User Engagement / compliance design:** dedicated design conversation needed before building. See `future_phases.md`.
4. **Phase vs. Deliverable terminology:** currently ambiguous — clarify in plan review session.

---

## Next session

Open with: `archive/plans/phase5_agent_reviews_continuation_2026-06-04.md`

Recommended next: Relationships deep pass, then immediately segue to the plan review milestone.
