# Session Archive — write_agent_config, Wishes Shell, Physical Health Additions, Agent Reviews
*2026-06-02*

---

## Context entering this session

Continuation of Phase 5 agent reviews. The two-agent head architecture (Coordinator + Synthesizer) is complete and tested. Prior session produced decisions from two parallel instances; this session synthesized those and began execution.

Reference files:
- `archive/plans/phase5_agent_reviews_prompt_2026-06-02.md` — full continuation prompt with decided/not-yet-built items

---

## Synthesis of parallel instance outputs

The other instance had reviewed the same material and surfaced:

**Proactive posture parallel** — Physical Health and Mental Wellbeing should both carry proactive scanning as a core tenet, phrased in parallel. Hold the Physical Health rewrite until Mental Wellbeing is ready; do both and run a "best of" comparison.

**Medication criticality** — Medications data model needs a three-value `criticality` field: `required | as_needed | optional`. Required = prescribed/non-negotiable (insulin, anticoagulants, psychiatric meds); as_needed = PRN (pain, sleep, anxiety); optional = supplements/vitamins. `MEDICATION_MISSED_CRITICAL` fires only on `required`. The agent's instructions must clarify that classification comes from the prescription record or explicit medical directive — not the agent's judgment. This replaces the previous `required: true/false` boolean.

**Wishes** — Separate module, not folded into Physical Health. Scope: structured document store for emergency contacts, medical POA, advance directive/DNR, legal document locations, last wishes, custody designations, digital estate. Tools: `tools/wishes.py` with `write_wishes`, `read_wishes`, `generate_emergency_card`. Data at `data/wishes/wishes.json`, sensitive-tier, never cloud-routed. Encryption deferred to Phase 6 (`age`). User-facing name: "Life Admin" or "Emergency & Legacy" — never "Wishes" in user-facing copy. Flag for Phase 6.75 legal review (jurisdiction-specific obligations around advance directives).

**write_agent_config / read_agent_config** — Scope writes to `data/config/{agent_name}.json` — user-data config space, not system config. Each agent gets its own namespace. Examples: Physical Health stores active workout plan; Finance stores budget structure; Mental Wellbeing stores coping protocols; Learning stores active skill goals. `write_config` stays for Goals Interviewer + Synthesizer scheduler entries only. User confirmed: execute across all specialist agents.

**Proactive scan scheduling** — Two-pronged: standing calls (Coordinator always calls MW and PH every exchange) + scheduled sessions (daily MW pulse, weekly PH review). Confirmed appropriate given parallel dispatch (latency impact minimized). Standing call instruction goes in `coordinator.md`; scheduled entries go in `scheduler.yaml`.

---

## New physical/health concepts surfaced

**Physical Health additions:**
- **Exertion/workout tracking** — richer schema: type, duration, intensity (RPE 1-10), muscle groups, cardio vs. strength, recovery state
- **Nutritional tracking** — macro/micro: protein, carbs, fat, fiber, sodium/salt, sugar; profile-flagged vitamins (D, B12, iron, calcium). Move beyond `food_logged: true/false`
- **Daylight/sun** — time outdoors, weather/cloud cover, season + latitude for UV intensity, Vitamin D synthesis flag. Requires GPS opt-in (Deliverable 6)
- **Nature time** — time in natural environments as a distinct signal from time outdoors generally (flows to Mental Wellbeing)
- **Environmental snapshot** — daily weather, AQI, UV index, temperature at user's location. Written to log for Pattern Miner correlation. Requires location + wttr.in (Deliverable 6)

**Mental Wellbeing / cross-domain:**
- **Service/volunteering** — community engagement, good works, acts of service. Ownership: Recreation & Hobbies tracks it as a leisure category; Mental Wellbeing receives meaning/purpose cross-signal. Synthesizer owns proactive nudge ("pick up 10 pieces of trash today" micro-engagement prompt). Register in both agents.
- **Addiction and behavioral health** — internal flag for compulsive/destructive behavioral patterns; vice tracking as opt-in data metrics (alcohol, tobacco/nicotine, substances, gambling, screen time); cessation program support. Physical Health owns substance use tracking; Mental Wellbeing receives compulsive pattern cross-signal. Sensitive-tier. Strong product feature for behavior change.

**Learning & Growth:**
- **Cognitive function profiling** — executive function (planning, attention, inhibition), working memory, processing speed. Same gradual naturalistic questioning approach as Big Five. Backlog item.
- **Motivation modulation** — how this user's motivation works and how it pairs with executive function for action. Backlog item.

**Environmental monitoring (deferred):**
- GPS + external databases for climate, events, local context as daily environmental snapshot. Deliverable 6+ alongside other live data tools.

---

## Decisions confirmed and executed this session

1. **tools/agent_config.py** — built. `write_agent_config(agent_name, key, value)` writes to `data/config/{agent_name}.json`; `read_agent_config(agent_name, key="")` reads back. Registered in orchestrator. Added to all specialist agent tool sections.

2. **tools/wishes.py** — built as shell. `write_wishes(section, content)`, `read_wishes(section="")`, `generate_emergency_card()`. Sections: emergency_contacts, medical_poa, advance_directive, legal_documents, last_will, custody_designations, digital_estate, notes. Registered in orchestrator. Physical Health has read access; Synthesizer has emergency surfacing access.

3. **STANDING_CALLS added to coordinator.md** — Mental Wellbeing and Physical Health called on every exchange regardless of message content. Added as a named section before the Specialist Directory.

4. **Scheduled sessions added to scheduler.yaml** — daily Mental Wellbeing pulse (07:15, weekdays) + weekly Physical Health review (Sunday 09:30).

5. **Physical Health deep review** — medication criticality updated to `required | as_needed | optional` three-value model. Exertion/workout schema expanded. Nutritional macro/micro tracking added. Daylight, nature time, environmental snapshot, addiction/behavioral health flagged in backlog.

6. **Agent reviews completed** — Work & Vocation, Relationships, Recreation & Hobbies (service/volunteering added as a category), Research Agent, Logistics. All have write_agent_config/read_agent_config added.

---

## Still pending

- CRM tool integration in Relationships (prompt at `archive/plans/crm_tool_prompt.md` — already built in prior session; may just need confirmation in agent file)
- Full model cost analysis (deferred to Phase 6 start)
- Environmental snapshot tool (Deliverable 6 — wttr.in)
- Cognitive function profiling build-out (Learning & Growth backlog)
- Wishes encryption (Phase 6, `age`)
- Legal review of clinical flagging + Wishes (Phase 6.75)

---

## Opening prompt for next session

Use `archive/plans/phase5_agent_reviews_prompt_2026-06-02.md` and update it, or open with this archive + the continuation prompt as context.
