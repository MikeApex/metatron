# Phase 5 — Agent Reviews Continuation — Prompt
*Use this to open a new Claude Code session to continue this work.*

---

You are Claude Code continuing development of a personal AI life manager.
Working directory: ~/Desktop/multi-model-mcp

Read these files before doing anything else:
- `CLAUDE.md` — architecture, conventions, terminology
- `archive/sessions/2026-06-02 — Phase 5 Agent Reviews, Proactive Architecture, Physical Health Additions.md` — full context for this session's decisions
- `archive/plans/phase5_coordinator_synthesizer_prompt_2026-05-28.md` — prior session context
- `archive/plans/phase5_prompt_2026-05-26.md` — overall Phase 5 plan

Also check memory at `~/.claude/projects/-Users-md-homefolder-Desktop-multi-model-mcp/memory/MEMORY.md` and read any memory files that seem relevant.

---

## CURRENT STATE

The two-agent head architecture (Coordinator + Synthesizer) is fully built and tested. All agent Coordinator→Synthesizer and Time Director reference sweeps are complete. The pipeline (`run_pipeline_session`) is implemented and working.

### Files in good shape
- `config/agents/coordinator.md` ✓
- `config/agents/synthesizer.md` ✓ (with Proactive Anticipation section)
- `config/agents/diarist.md` ✓ (rewritten as write-only data router)
- `config/agents/mental_wellbeing.md` ✓ (full rewrite — proactive scan, Big Five, clinical flags, trajectory values, MUST_SURFACE)
- `config/agents/pattern_miner.md` ✓
- `config/agents/goals_interviewer.md` ✓
- `config/agents/learning_growth.md` ✓ (substantially revised 05-28)
- `config/agents/finance.md` ✓ (substantially revised 05-27)
- `config/agents/time_director.md` — tombstoned/retired
- `config/modules/routing.yaml` ✓
- `config/preferences.yaml` ✓ (created this session — opt-in settings and expenditure threshold)
- `core/orchestrator.py` ✓ (pipeline built; parallel calls in progress in a separate instance)
- `tools/subagent.py` ✓ (time_director removed from schema)

### Agent reviews still needed (deeper content pass)
These were patched for Phase 5 conventions but not fully reviewed for content quality, completeness, and new requirements:

1. **Physical Health** — partially reviewed this session. Additions made: proactive scan, medication flags (required/optional), MUST_SURFACE, Wishes in backlog. Still needs: exertion/workout tracking expansion, nutritional macro/micro tracking, daylight/sun tracking with Vitamin D flag, outdoor/nature time, medication profile model (three-value: required | as_needed | optional). Also: the other instance's suggestion to update medication criticality from `required: true/false` to `required | as_needed | optional`.

2. **Work & Vocation** — first-pass only

3. **Relationships** — first-pass only; also needs CRM tool integration once `tools/crm.py` is built (prompt at `archive/plans/crm_tool_prompt.md`)

4. **Recreation & Hobbies** — first-pass only; needs service/volunteering as a tracked category

5. **Research Agent** — first-pass only; lightest file, likely needs least work

6. **Logistics** — first-pass only

---

## DELIVERABLE 6 ITEMS (confirmed scope additions)

These are confirmed to be in scope for Deliverable 6 (Integrations). Add them to the Deliverable 6 section when the Phase 5 → 6 planning document is written.

- **Emergency & Legacy (Wishes) full build** — shell in `tools/wishes.py` is done. Full build: interview flow (Physical Health interviews for advance directive + medical POA; Mental Wellbeing for custody, last wishes, digital estate), `age` encryption, emergency card delivery, legal review (Phase 6.75). User-facing name: "Emergency & Legacy".
- **Environmental snapshot tool** — `get_environmental_snapshot(location, date)` via wttr.in. Daily weather, AQI, UV index written to health log. Used by Physical Health for daylight/Vitamin D tracking and by Pattern Miner for correlation.
- **Nutritional data integration** — formal app/device import (Apple Health, MyFitnessPal) for automated macro/micro tracking. Estimation-from-description and brand lookup via Research Agent are already available pre-Deliverable 6.

---

## DECIDED BUT NOT YET BUILT

These decisions are confirmed. Execute them:

### 1. write_agent_config / read_agent_config tool pair

Build `tools/agent_config.py` with:
- `write_agent_config(agent_name, key, value)` — writes to `data/config/{agent_name}.json`; creates file if missing; merges with existing
- `read_agent_config(agent_name, key="")` — reads from `data/config/{agent_name}.json`; returns full config if no key, or specific value if key provided

Scope: user-data config space for agent-owned persistent state. NOT system config. Examples of what agents store here: Physical Health stores its active workout plan; Finance stores budget structure; Mental Wellbeing stores coping protocols; Learning stores its active skill goals and study plans.

`write_config` stays as-is for Goals Interviewer (writes to `config/goals.yaml` etc.) and for Synthesizer's scheduler entries. `write_agent_config` is the new universal tool for agent-owned state.

Register both in `core/orchestrator.py` → `register_tools()`.

Add both tools to the tools list in every specialist agent file: mental_wellbeing.md, physical_health.md, work_vocation.md, relationships.md, learning_growth.md, recreation_hobbies.md, finance.md, research_agent.md, logistics.md.

### 2. Wishes module shell

Build `tools/wishes.py` with:
- `write_wishes(section, content)` — writes to a named section of `data/wishes/wishes.json`. Sections: emergency_contacts, medical_poa, advance_directive, legal_documents, last_will, custody_designations, digital_estate, notes.
- `read_wishes(section="")` — reads all wishes or a specific section
- `generate_emergency_card()` — outputs a minimal plain-text summary for first responders: emergency contacts, medical POA name, key advance directive notes (e.g. DNR status), primary care physician

Data lives at `data/wishes/wishes.json`. Sensitive-tier: local only, never cloud-routed. Encryption deferred with the broader encryption work (Phase 6, `age`).

Register in `core/orchestrator.py`.

Add a `## Wishes` section to `config/agents/physical_health.md` tools list (read access) and a note to `config/agents/synthesizer.md` tools list (emergency surfacing access).

User-facing name for this feature: "Life Admin" or "Emergency & Legacy" — never "Wishes" in user-facing copy.

Flag for Phase 6.75 legal review: jurisdiction-specific obligations around advance directives and emergency information.

### 3. Proactive scan scheduling

The proactive scans in Mental Wellbeing and Physical Health only run when those agents are called. If the Coordinator routes a logistics message and doesn't call MW or PH, their scans don't run.

Fix: **two-pronged approach.**

**Part A — Standing calls in Coordinator:**
Add a `STANDING_CALLS` concept to `config/agents/coordinator.md`. Mental Wellbeing and Physical Health are always called, every session, regardless of message content. They are lightweight observations (not deep analysis) and their proactive scans ensure nothing critical is missed.

Add to coordinator.md under a new section before the Specialist Directory:

> **Standing calls:** Regardless of the user's message, always call Mental Wellbeing and Physical Health on every exchange. These agents run lightweight proactive scans and log contextual data independently of routing decisions. Do not skip them even when the message appears unrelated to health or emotional state.

**Part B — Scheduled standalone sessions:**
Add entries to `config/modules/scheduler.yaml`:
- Daily morning Mental Wellbeing pulse (separate from morning brief)
- Weekly Physical Health review

These give both agents a dedicated window for deeper scanning independent of the conversational pipeline.

---

## NEW CONCEPTS TO REGISTER AND DESIGN (not yet built)

These were surfaced in the last session. For each, decide where it lives, note it in the right agent's backlog, and flag any that need architectural decisions before building.

**Physical Health additions:**
- Exertion/workout tracking: richer schema — type, duration, intensity (RPE 1-10), muscle groups, cardio vs. strength, recovery state
- Nutritional tracking: move beyond `food_logged: true/false` to macro/micro tracking — protein, carbs, fat, fiber, sodium/salt, sugar; profile-flagged vitamins (D, B12, iron, calcium)
- Daylight/sun: time outdoors, weather/cloud cover, season + latitude for UV intensity, Vitamin D synthesis flag. Note: requires location data (GPS opt-in)
- Nature time: time in natural environments as distinct signal from time outdoors generally
- Environmental snapshot: daily record of weather, AQI, UV index, temperature at user's location — written to log for Pattern Miner correlation. Requires location + wttr.in (Deliverable 6 tool, already planned)

**Mental Wellbeing / cross-domain:**
- Service/volunteering: community engagement, good works, acts of service — tracked as a category in Recreation & Hobbies; Mental Wellbeing receives meaning/purpose cross-signal. Synthesizer proactive nudge category (e.g. "pick up 10 pieces of trash today" micro-engagement prompt). Note which agent owns it before building.
- Addiction and behavioral health: internal flag for compulsive/destructive behavioral patterns; vice tracking as opt-in data metrics (alcohol, tobacco/nicotine, substances, gambling, screen time); cessation program support for "I'd like to quit smoking/drinking" — measurable, motivating, strong product feature. Lives in Physical Health (substance use) with Mental Wellbeing cross-signal (compulsive patterns). Sensitive-tier.

**Learning & Growth:**
- Cognitive function profiling: executive function (planning, attention, inhibition), working memory, processing speed — same gradual naturalistic questioning approach as Big Five. Enhancement backlog item.
- Motivation modulation: how this user's motivation works and how it pairs with executive function for action

---

## ARCHITECTURAL QUESTION FOR EARLY IN SESSION

**Proactive scans — standing calls vs. scheduling:** The above proposes both. Confirm this is the right approach before writing coordinator.md changes. Standing calls (every exchange, lightweight) cover real-time continuity; scheduled sessions cover deeper weekly/daily sweeps. Are there concerns about always calling MW and PH on every single exchange (cost, latency)? With parallel subagent dispatch now implemented, latency impact is minimized.

---

## PLAN REVIEW MILESTONE

At the close of this deliverable (agent reviews complete), conduct a dedicated plan review session before starting any further builds. The purpose: ensure the remainder of Phase 5, Phase 6, Phase 7, and future phases are structured correctly and sequenced appropriately. Things that may need shuffling:

- Deliverable 6 scope (integrations) — now includes Emergency & Legacy full build, environmental snapshot, nutritional integration
- Phase 6 — needs a clean definition distinct from the Deliverable numbering within Phase 5
- Future phases — environmental monitoring, cognitive profiling, Observer agent, behavioral health full build (see `archive/plans/future_phases.md`)
- Anything surfaced during agent reviews that affects sequencing (e.g., addiction tracking implicit/explicit split, wishes read access design)

**This review produces a new plan snapshot document** at `archive/plans/phase5_to_future_roadmap_{date}.md`. It is not a code session — it is a planning session. Open it with the session archive, this prompt, and `archive/plans/future_phases.md`.

---

## WHERE TO START

1. Execute the three "decided but not yet built" items: write_agent_config/read_agent_config, Wishes shell, proactive scan scheduling. These are unambiguous — do them first.

2. Physical Health deep review: apply the medication criticality update (required | as_needed | optional), exertion schema, nutritional tracking additions, daylight/nature tracking notes.

3. Work through remaining agent reviews in order: Work & Vocation, Relationships, Recreation & Hobbies, Research Agent, Logistics.

4. Register new concepts in the right agent backlogs as you review each one.

---

## PARALLEL TASKS (if another instance is available)

- `archive/plans/crm_tool_prompt.md` — build tools/crm.py. Self-contained, no decisions needed.
- `archive/plans/parallel_subagent_calls_prompt.md` — parallelize subagent dispatch. May already be complete; check before starting.
