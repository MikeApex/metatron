# Session Archive — 2026-06-02
## CRM Tools, Physical Health Design, Wishes Module

---

## CRM Tool Build (`tools/crm.py`)

Parallel prompt from `archive/plans/crm_tool_prompt.md` executed via subagent. Built and verified:

**Five tool functions:**
- `write_contact` — create or update contact records (UUID IDs, atomic writes, threading.Lock)
- `read_contact` — fetch by ID or fuzzy name match
- `list_contacts` — filter by type, quality, tag, or `overdue_only` (frequency → timedelta mapping)
- `log_interaction` — appends to interaction_log, updates last_contact date
- `search_contacts` — substring match across all text fields

**Storage:** `data/crm/contacts.json` (sensitive-tier, chmod 600); persona path support via `AI_TEST_PERSONA` env var.

**Registration:** All five tools imported, schemas and handlers registered in `core/orchestrator.py`; tool names added to `_CONFIDENTIAL_TERMS`.

**Relationships agent:** `config/agents/relationships.md` updated — tools section replaced, step 5 added (check/create contact on mention, log interaction, check overdue).

**Verification passed:** clean import, REPL smoke test (2 contacts, 2 interactions, list/search/read), overdue logic confirmed.

---

## CRM Field Expansion

Added structured fields to `write_contact` and `WRITE_CONTACT_SCHEMA`:

| Field | Type | Notes |
|---|---|---|
| `first_name`, `last_name`, `nickname` | string | Supplementary to `name` (display/relational name stays primary) |
| `referred_to_as` | list[str] | How user refers to person in speech — for contact recognition in unstructured text |
| `spouse_name` | string | |
| `kids_names` | list[str] | |
| `education` | string | Free text |
| `occupation`, `employer` | string | |
| `how_met` | string | |
| `timezone` | string | IANA format |
| `contact_info` | dict | email, phone, address, social handles |

**Update logic refactored** into `_str_fields` / `_collection_fields` loops — one-line cost to add future fields.

**`search_contacts` extended** to cover all new text fields including contact_info values and social handles.

**Design note on field clearing:** String fields cannot be cleared back to `""` via update (falsy values are skipped). List/dict fields can be cleared by passing `[]` or `{}` explicitly (uses `is not None` check). Known gap, not urgent.

**Design note on `referred_to_as`:** Currently populated and searchable. For active contact recognition ("my mom" → Sarah Chen), the Coordinator or orchestrator would need a pre-routing lookup pass against these aliases. Deferred enhancement.

---

## CRM Architecture Notes

**Who calls CRM tools:**
- **Relationships agent** — primary owner. All deliberate writes should go through here so context and interpretation travel with the log entry.
- **Synthesizer** — may call `list_contacts(overdue_only=true)` or `read_contact` directly for proactive outreach decisions. Reads freely; writes should still route through Relationships so flag logic runs.
- **Coordinator** — no reason to touch CRM.

Risk to watch: if Synthesizer logs interactions directly, it bypasses Relationships agent's flag logic (RECONNECT_OPPORTUNITY, CONFLICT_ACTIVE, etc.).

---

## Physical Health Agent — Design Discussion

Current `config/agents/physical_health.md` identified as underbuilt. Key design decisions made:

**Four pillars (orientation, not structure):** fitness/exercise, medical, dietary/nutrition, sleep. No section headers — pillars overlap and the valuable signals are cross-pillar (sleep → hunger → food → exercise chain, etc.). Pillars named in Role section as primary domains; analysis runs freely across them.

**Proactive posture:** When user is healthy, agent is a performance optimizer. When condition is active (temporary/chronic/terminal), shifts to support/management mode. This is a continuum read from context, not an explicit switch. Physical health is the highest-signal input to cognitive function, emotional regulation, motivation, and longevity.

**Parallel with Mental Wellbeing:** Both agents should carry proactive posture as a core tenet, phrased in parallel. Hold Physical Health rewrite until Mental Wellbeing is ready — write both, run "best of" comparison, finalize together.

**Nutrition output — log schema needs expansion:**
```json
"nutrition": {
  "calories_estimated": 1840,
  "protein_g": 95,
  "carbs_g": 210,
  "fat_g": 62,
  "logged_meals": ["oatmeal + blueberries", "chicken salad", "pasta"],
  "pacing": "below_typical | on_track | above_typical",
  "notes": "high carb day, low protein relative to goal"
}
```
Agent estimates from description when no precise data given; flags estimates as approximate. Pacing requires rolling baseline from `read_log` (last 7–14 days).

**Medication tracking — needs `tools/medications.py`:**
- Medications list: name, dose, schedule, prescribing_reason, prescriber, start_date, active
- `criticality: "required | as_needed | optional"` — classifies per prescription/medical directive, not agent judgment
- `MEDICATION_MISSED` flag fires only on `required` medications
- Daily log tracks whether each dose taken and when
- Scheduler integration: Physical Health defines schedule → Scheduler fires reminder → check-in captures confirmation

**Wearables:**
- Integration problem, not an agent design problem (Apple Health HealthKit, Garmin Connect, CGM APIs)
- Design schema now so data has a home: HR, SpO2, body temp, HRV, blood glucose fields in the log
- Agent instructions: when wearable data present, treat as higher-confidence signal than self-report
- Integration build is Phase 6+; schema is ready to receive it

**Emergency medical record:**
- Data model: FHIR-compatible fields (blood type, drug allergies, current medications + doses, active conditions, emergency contacts, PCP)
- Lives in `tools/medical_record.py`, sensitive-tier, local
- Access constraint: must be readable by medical professionals when user can't unlock phone
- Architecture direction: encrypted local blob + QR code linking to server-side record requiring healthcare proxy authentication; device holds encrypted blob but cannot decrypt without external key
- FHIR export (standard bundle) is correct long-term direction for "decrypts on medical systems"
- Phase 6+ build; note as scheduled deliverable, not someday-maybe
- `generate_emergency_summary()` function (plain-text emergency card) can be built now

---

## Wishes / Legacy Module

Proposed as standalone module — distinct from emergency medical record (different audience, timescale, legal weight).

**Scope:**
- Emergency contacts (with relationship and authority level)
- Medical Power of Attorney (name, contact, document location)
- Advanced Directive / DNR (status, key directives, document location)
- Legal document locations (will, trust, safe deposit)
- Last wishes (funeral, burial, disposition)
- Custody designations (children, pets with named guardians)
- Digital estate notes

**Architecture:** `tools/wishes.py` with `write_wishes`, `read_wishes`, `generate_emergency_card`. Not an analytical agent — a secure structured document store. Read access granted to Physical Health and Synthesizer for emergency surfacing.

**Encryption:** same deferred problem as emergency medical record — should share a solution when that's built.

**Naming note:** "Wishes" is clear internally; user-facing name should be something like "Life Admin" or "Emergency & Legacy."

---

## write_config / Agent Config Pattern

**Current state:** `write_config` writes to `config/` — system-level files (goals.yaml, module settings). Appropriate for Goals Interviewer; too broad for every agent.

**Decision:** Introduce `write_agent_config` / `read_agent_config` tool pair scoped to `data/config/{agent_name}.json`. Each agent gets its own namespace for persistent structured preferences and plans. Cannot touch system config.

- `write_config` stays where it is (Goals Interviewer, user-directed goal updates)
- `write_agent_config` becomes the universal tool for agent-owned persistent state
- Add the pair when building out the next tool set

Examples of what agents would store: Physical Health → workout plan; Finance → budget structure; Mental Wellbeing → coping protocol; Relationships → outreach preferences.

---

## Open / Deferred

- Physical Health + Mental Wellbeing rewrites (waiting to do together for parallel proactive posture phrasing)
- `tools/medications.py` build
- `tools/medical_record.py` build
- `tools/wishes.py` build
- `write_agent_config` / `read_agent_config` tool pair
- Wearables integration (Phase 6+)
- Emergency record QR/decryption layer (Phase 6+)
- `referred_to_as` active contact recognition in Coordinator (future enhancement)
