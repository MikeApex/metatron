# 2026-06-02 — Phase 5: Agent Reviews, Proactive Architecture, Physical Health Additions

---

## What was built and decided

### Proactive anticipation — hardcoded architecture

Designed and wrote a proactive anticipation framework as a non-optional value across the system:

- **Synthesizer** (`config/agents/synthesizer.md`): full `## Proactive Anticipation` section added. Mandatory pass every exchange. Three scan dimensions: pattern signal, inferential signal, temporal optimization. Action tier table (Inform → Act autonomously → Confirm first → Expenditure under/over threshold → Financial → Social outreach). `TOOL_NOT_BUILT` flag for capability gaps. Social outreach modes (as user / as agent on behalf). `config/preferences.yaml` created to hold opt-in settings and user-configurable expenditure threshold + currency.

- **Coordinator** (`config/agents/coordinator.md`): `PROACTIVE_FLAGS` added as a mandatory output field. Proactive scan instruction added to the context-load section — side-product of context loading already happening, no extra calls.

- **Mental Wellbeing** and **Physical Health**: parallel `## Proactive scan` sections added to both, phrased consistently. Structural opener borrowed from Synthesizer ("This is a mandatory pass. It runs every session. It cannot be skipped."). Domain-specific scan dimensions (pattern / temporal / practice-gap for MW; pattern / medication check / trajectory erosion for PH).

### Social outreach model clarified

Tool CAN reach out directly to a social contact, either as the user or as agent on their behalf. Agent-to-agent coordination (Tinder-style mutual match before surfacing) is the Phase 6+ evolution, not a prerequisite. Direct outreach with opt-in is the current mechanism.

### Comprehensive reference sweep

Two sweeps this session:

1. Replace_all of "the Coordinator" → "the Synthesizer" across all specialist files (lowercase only — missed capitalized and bare forms)
2. Full bash sweep covering all remaining patterns: "The Coordinator will/decides/should", "returned to Coordinator)", "Coordinator should", "pass to Coordinator:", "Time Director" in daily_checkin.md and pattern_miner.md. Zero wrong referents remain in non-exempt files.

Exempt files (legitimate Coordinator references preserved): `coordinator.md`, `synthesizer.md`, `diarist.md` ("directive from the Coordinator"), `pattern_miner.md` ("Coordinator loads at session start").

### Time Director retirement completed

`config/agents/time_director.md` — tombstone already present from 05-28 session. `routing.yaml` and `server.py` already clean. Nothing to do.

### Diarist rewritten

`config/agents/diarist.md` fully rewritten as write-only data router. Removed: session start/close, read_context_tracker, read_wisdom, search_memory, all conversational elements. Kept: capture philosophy, what-to-log-where, output format (brief capture summary → Synthesizer), four write tools only. Rationale: Synthesizer owns all user-facing continuity; Diarist is called as a subagent and returns a structured capture summary.

### Pattern Miner output destinations clarified

`write_insight_report` → durable file at `data/[persona]/insights/`, read back via `read_recent_insights` (Coordinator loads at session start for medium-term picture). `write_context_tracker` → hot-path 2-3 item summary for the Coordinator's next session start. Different destinations, different purposes.

### Two-pass pipeline confirmed

Already implemented from 05-27 session. `run_pipeline_session` at line 520 and `run_session` routing to it at line 573. Two minor fixes made: stale `time_director` reference in `RUN_SUBAGENT_SCHEMA`, warning message copy-paste error in `filter_output` ("Coordinator response" → "Synthesizer response"). Pipeline is testable.

Parallel subagent dispatch: prompt document written (`archive/plans/parallel_subagent_calls_prompt.md`), running in a separate instance. Change is ~45 minutes: ThreadPoolExecutor for run_subagent/run_model_conference calls, threading.Lock on write_log to prevent race condition.

### Mental Wellbeing — full rewrite

`config/agents/mental_wellbeing.md` substantially expanded from first-pass. Key additions:
- Role reframed: "psychological mirror" for sustained flourishing, not mood-logger
- Full-spectrum emotional assessment (positive states as data)
- Linguistic/cognitive pattern assessment: explanatory style, absolutist language, locus of control, emotional granularity, cognitive distortions
- Trigger landscape expanded beyond sleep/food: specific people, music/media with emotional memory, seasonal/anniversary effects, social feedback, transitions
- Practice tracking (meditation, journaling, therapy, exercise, social rituals)
- Trajectory: rising / homeostasis / stable / plateaued / declining / unclear. Homeostasis is a positive value — actualized equilibrium, not stagnation. DRIFT_CHECK flag distinguishes chosen homeostasis from passive drift at odds with stated goals.
- Proactive scan section (mandatory every session, parallel to Synthesizer's section)
- MUST_SURFACE field in output format
- Clinical flags (DEPRESSION, MANIA, SUICIDAL_IDEATION, ANXIETY_DISORDER) — internal routing only, never surfaced as labels to user, all flagged for Phase 6.75 legal review. SUICIDAL_IDEATION requires Synthesizer to include professional resource signposting.
- Big Five personality profiling — gradual, one question per session, naturalistic, never announced; responses stored via write_wisdom; dimension estimates inform interpretation of user signals
- PROACTIVE_OBSERVATIONS field added to output format
- write_wisdom added to tools list
- Clinical concern protocol review added to enhancement backlog

### Physical Health — additions

`config/agents/physical_health.md`:
- Proactive scan section added (mandatory, parallel to Mental Wellbeing's section)
- Medication flags: `MEDICATION_MISSED_CRITICAL` (required medications, triggers MUST_SURFACE) and `MEDICATION_MISSED_OPTIONAL` (informational only). Classification from medication profile, not agent judgment. Note: needs update to three-value model (required | as_needed | optional) — see next session.
- `medications_logged` array added to data schema
- MUST_SURFACE and PROACTIVE_OBSERVATIONS added to output format
- Enhancement backlog: Wishes and advance directives added (data design deferred to Deliverable 6+); wearables tagged #wearables

### CRM design decision

Off-the-shelf analysis: Monica HQ is the best fit (purpose-built personal CRM, self-hostable, REST API) but adds infrastructure overhead. CardDAV already Deliverable 6. **Decision: custom local JSON in `data/crm/contacts.json`** as migration target for CardDAV. Prompt at `archive/plans/crm_tool_prompt.md`.

---

## Prompt documents created this session

- `archive/plans/parallel_subagent_calls_prompt.md` — parallelize run_subagent/run_model_conference via ThreadPoolExecutor; threading.Lock on write_log; ~45 min task
- `archive/plans/crm_tool_prompt.md` — build tools/crm.py with five functions, register in orchestrator, update Relationships agent tools list
- `archive/plans/phase5_agent_reviews_prompt_2026-06-02.md` — **continuation prompt for next session** (see below)

---

## Decided but not yet executed

### 1. write_agent_config / read_agent_config tool pair

Agent-owned config namespace scoped to `data/config/{agent_name}/`, separate from system config. `write_config` stays for Goals Interviewer and scheduler entries. Every specialist gets the new pair for persistent state (workout plans, budget structure, coping protocols, skill goals, etc.). Build `tools/agent_config.py`, register in orchestrator, add to all specialist agent files.

### 2. Wishes module

Separate module — not folded into Physical Health. Scope: emergency contacts (with authority level), Medical POA, Advanced Directive/DNR (with key directives), legal document locations, last will and testament, custody designations (children, pets with named guardians), digital estate notes.

Architecture: `tools/wishes.py` with `write_wishes`, `read_wishes`, `generate_emergency_card` (minimal plain-text for first responders). Data at `data/wishes/wishes.json`. Sensitive-tier: local only. Encryption deferred.

User-facing name: "Life Admin" or "Emergency & Legacy" — never "Wishes" in user-facing copy. Flag for Phase 6.75 legal review.

### 3. Proactive scan scheduling

Two-pronged: (a) standing calls in Coordinator — MW and PH always called every exchange regardless of message content; (b) scheduled standalone sessions via scheduler.yaml for daily/weekly deeper scans. Coordinator.md needs a `## Standing calls` section. Scheduler.yaml needs new entries.

---

## New concepts registered — future sessions

**Physical Health:**
- Exertion/workout tracking: richer schema (type, duration, intensity/RPE, muscle groups, recovery state)
- Medication criticality model update: required | as_needed | optional (three-value, replaces boolean)
- Nutritional macro/micro tracking: protein, carbs, fat, fiber, sodium/salt, sugar; profile-flagged vitamins (D, B12, iron, calcium)
- Daylight/sun tracking: time outdoors, weather/cloud cover, season + latitude for UV intensity, Vitamin D flag. GPS opt-in required.
- Nature time: time in natural environments as distinct signal
- Environmental snapshot: daily record (weather, AQI, UV, temp) using location + wttr.in; Pattern Miner correlates with mood/energy/output

**Mental Wellbeing / cross-domain:**
- Service/volunteering: community engagement as integration/meaning marker. Category in Recreation & Hobbies; Mental Wellbeing cross-signal. Synthesizer micro-engagement prompts ("pick up 10 pieces of trash today").
- Addiction and behavioral health: internal flag for compulsive/destructive patterns; vice tracking as opt-in data metrics (alcohol, tobacco/nicotine, substances, gambling, screen time); cessation program support — measurable, motivating, strong product feature. Physical Health primary + Mental Wellbeing cross-signal. Sensitive-tier.

**Learning & Growth:**
- Cognitive function profiling: executive function, working memory, processing speed — same gradual naturalistic questioning as Big Five. Enhancement backlog.
- Motivation modulation: how motivation works for this user, how it pairs with executive function for action.

---

## Remaining agent reviews (not yet deep-reviewed)

1. Physical Health — partially done; needs all additions above
2. Work & Vocation — first-pass only
3. Relationships — first-pass only; + CRM integration
4. Recreation & Hobbies — first-pass only; + service/volunteering category
5. Research Agent — lightest file, likely least work
6. Logistics — first-pass only

---

## Key decisions (standing)

- Coordinator never speaks to user, never sees specialist outputs
- Synthesizer is the only user-facing agent
- Diarist is write-only; no conversational output
- Privacy: all personal context sensitive-tier; cloud LLMs receive only decontextualized queries
- All agent files reference Synthesizer for output routing; Coordinator references correct in coordinator.md, synthesizer.md, diarist.md, pattern_miner.md only
- Time Director retired; direction/prioritization live in Synthesizer
- Proactive posture is a core tenet, phrased in parallel across agents where relevant
- Homeostasis is a positive trajectory value — do not pathologize contentment
