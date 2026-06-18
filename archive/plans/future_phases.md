# Future Phases — Parking Document
*Features that belong after MVP. Not scheduled. Not designed in detail. Parked here so they aren't lost.*

---

## Environmental Monitoring (Phase 7+)

A contextual layer that reconstructs what was going on around the user on any given day.

**Scope:**
- **Weather and climate** — temperature, AQI, UV index, precipitation, cloud cover at user's location. Day-level granularity. Used by Physical Health for daylight/Vitamin D tracking and by Pattern Miner for environmental correlation.
- **Local events and ambient context** — what was happening nearby: noise, public events, civic activity. Harder to source; likely requires location + event database API.
- **News and broader context** — what was happening in the world on that date. National/global headlines. Useful for Pattern Miner when the user's mood or behavior correlates with external events (election stress, market volatility, pandemic context).

**Data sources to evaluate:**
- `wttr.in` — weather, AQI, UV (no key, already planned for Deliverable 6)
- Local events: Eventful, Ticketmaster API, local government event feeds — evaluating needed
- News: RSS feeds (already planned for Research Agent)
- Noise level: no established API — may require passive phone sensor data

**Privacy posture:**
- Requires GPS opt-in (same as daylight tracking)
- All environmental data is stored locally with the daily log
- Never sent to cloud LLMs in combination with personal context

**Dependencies:**
- GPS opt-in flow (user-facing opt-in at setup or first request)
- `get_environmental_snapshot` tool (to be built at Deliverable 6 start)
- Pattern Miner schema extension to correlate health/mood data with environmental fields

**Design question before building:**
Scope decision needed: weather-only (narrow, high-value, easy) vs. full contextual snapshot (broad, harder, much higher complexity). Weather-only can ship as part of Deliverable 6. Full environmental monitoring is a separate initiative.

---

## Wishes / Emergency & Legacy — Full Build (Deliverable 6)

The shell (`tools/wishes.py`) is built. Full build includes:

- **Interview flow** — Physical Health interviews for advance directive and medical POA; Mental Wellbeing interviews for custody designations, last wishes, digital estate, and notes. Both use `PROFILE_GAP` to surface questions naturally; Synthesizer decides when to prompt.
- **Encryption** — `age` encryption for `data/wishes/wishes.json`. Same deferred encryption layer as other sensitive data stores. Design and key management to be decided at Phase 6 start.
- **Emergency card output** — `generate_emergency_card()` already built. User-facing delivery (print, export to PDF, share as contact card) to be designed.
- **Read access design** — deferred to Phase 6. Structural question: which agents can read which sections, under what conditions, via what mechanism. Legal question: jurisdiction-specific obligations around advance directive access, emergency contact disclosure, data retention. These must be designed together before any read access is granted to any agent. Current state: Synthesizer writes only; no reads permitted.
- **Legal review** — Phase 6.75. Full compliance audit. Jurisdiction-specific obligations around advance directives, emergency contact disclosure, and data retention vary significantly. Flag for legal/compliance review before user-facing rollout.
- **Logistics integration** — `read_wishes` already added to Logistics tools for emergency contact lookup during bookings and medical scheduling.
- **User-facing name** — "Emergency & Legacy" (working title).

---

## Addiction and Behavioral Health — Full Build (Phase 6+)

The flag infrastructure (`VICE_LOGGED`, `BEHAVIORAL_PATTERN_CONCERN`, `CESSATION_SUPPORT`) is in place. Full build includes:

- **Opt-in vice tracking** — user explicitly enables tracking for specific behaviors. UI flow needed.
- **Cessation program** — goal-setting, streak tracking, Pattern Miner correlation, Synthesizer support messages.
- **Implicit pattern detection** — Pattern Miner correlation of substance use logs with mood, sleep, and output data. Findings surfaced as observations, not diagnoses.
- **PRN medication intersection** — some PRN medications (sleep, anxiety, pain) overlap with behavioral health patterns. Flag when PRN use is becoming regular.
- **Privacy** — all behavioral health data is sensitive-tier, local only. Pattern Miner receives statistical summaries, not raw records.

---

## Cognitive Function Profiling (Learning & Growth, Phase 6+)

See Learning & Growth enhancement backlog. Naturalistic questioning approach, same as Big Five. Joint initiative with Mental Wellbeing (motivation modulation).

---

## User Engagement — Compliance Development (Phase 6+)

A conversation is needed before building any compliance or habit-formation features. The design principle to explore:

> *Compliance development via immediately actionable directions and subsequent rewards during take up/novelty/placebo phase.*

**Questions to resolve before building:**

- What constitutes a "reward" in this tool's context — and does it belong in the constitution or in a specialist's toolbox?
- At what point does the novelty/placebo effect wear off, and what replaces it? Is the tool designed for that transition?
- How does compliance-oriented framing interact with the constitution's stance on the tool as companion vs. director?
- Which specialist owns this (Mental Wellbeing? Coordinator level?), and does it need its own instruction file?

**Related:** Addiction and Behavioral Health (see above) — streak tracking and cessation support are downstream implementations of the same compliance mechanics.

---

### Compliance curve principle — **RESOLVED 2026-06-18**

*See `archive/plans/compliance_curve_decision_2026-06-13.md` for all decisions and proposed instruction text. File edits queued pending A2 chat close.*

*Original flag:*

The tool will have a systemic compliance problem if it introduces goals or directions that are user-avoidant — activities the user finds aversive, too demanding, or not yet habituated to — before the user is bought in to the behavior. The tool only works insofar as it can direct users toward better choices; a direction that triggers avoidance is worse than no direction.

**The principle:** Stay behind the compliance curve. Introduce new behaviors at a level the user can actually execute, then build from there. Do not start at the optimal level — start at the accessible level.

**Example:** A user wants to run longer distances but has no standing running practice. "Run 5k" on Day 1 is unreasonable even if they are physically capable. "Run 500m" is meaningful, accessible, and if there's a compliance issue it can be worked down further. The goal is a successful first rep — not the right rep.

**Design questions to resolve:**
- Which agent is responsible for calibrating this (Synthesizer? Physical Health? a shared principle across all specialists)?
- How does the tool detect that a user is ready to graduate to a harder target, vs. still fragile on the current one?
- What is the ratchet mechanism — how does it step up, and how does it step back when compliance fails?
- Does the constitution need a statement on this, or is it a Synthesizer-level instruction?

---

## Self-Improvement Protocol (Phase 5 end → Phase 6 ongoing)

Three-stage feedback loop that turns alpha usage misses into config improvements. **Observer Agent (Stage 3) does not yet exist** — this is the full build plan.

---

### Stage 1 — Logging layer (before alpha begins, late Phase 5)

Must be live from session one of alpha. Misses not logged cannot be recovered retroactively.

**What gets logged:**
- `ROUTING_MISS` from Synthesizer — catches gaps between raw message signal and specialist coverage (instruction already in `synthesizer.md`)
- Implicit correction events — Coordinator detects correction-clarification turns ("no, I meant...", re-statement of same intent differently phrased) and logs them as `USER_CORRECTION`
- Explicit user signal — PWA gets a low-friction single tap ("missed the mark") that appends an event; no rating system
- Existing structured signals already emitted by agents: `TOOL_NOT_BUILT`, `CHAIN_LIMIT_REACHED`, `BASELINE_INCOMPLETE`, `PROFILE_GAP`

**Output:** `data/logs/quality_events.json` — append-only, timestamped:
```json
{
  "timestamp": "...",
  "event_type": "ROUTING_MISS | USER_CORRECTION | CHAIN_LIMIT | TOOL_MISSING | ...",
  "source_agent": "synthesizer",
  "detail": "Mental Wellbeing not called; raw message contained 'exhausted and empty'",
  "session_id": "...",
  "message_hash": "..."
}
```

**Files to build:**
- New `write_quality_event` tool (or extend `write_context_tracker`)
- `config/agents/coordinator.md` — add implicit correction detection
- PWA — minimal "missed the mark" tap

---

### Stage 2 — Pattern Miner system health extension (Phase 6 start)

By Phase 6, weeks of alpha data will have accumulated. Pattern Miner adds a second analysis pass over `quality_events.json`. Output is a **separate** system health report — not mixed with user insights, not surfaced to the user.

**Output:** `data/logs/system_health_YYYY-MM-DD.json`

**Analysis covers:**
- Which event types appear most frequently?
- Which message patterns correlate with routing misses? (e.g., positive-framing hedges → Mental Wellbeing systematically missed)
- Which agents generate the most `PROFILE_GAP` flags? (signals baseline interview is needed)
- Recurring `CHAIN_LIMIT_REACHED` on the same topics? (signals a specialist needs deeper tooling)
- User correction clustering by domain or message type?

**Example output section:**
```
routing_miss_rate: 0.12
top_miss_patterns:
  - "positive-framing hedges ('fine but...') → Mental Wellbeing missed (8 instances)"
  - "Finance signals without dollar amounts not routed (3 instances)"
suggested_fixes:
  - "coordinator.md: add 'fine but' to Mental Wellbeing trigger signals"
  - "coordinator.md: add routing note for financial stress without explicit amounts"
chain_limit_clusters:
  - "research_agent on medical topics (4x this week) — consider expanding Physical Health tooling"
```

**Files to build:**
- `config/agents/pattern_miner.md` — system health pass extension
- `tools/pattern_miner.py` — `write_system_health` tool or extension to `write_insight_report`

---

### Stage 3 — Observer Agent + review cycle (Phase 6 ongoing)

Observer reads system health reports and proposes specific config changes. All proposed changes surface to a Claude Code session for developer review. Human approves, rejects, or modifies before anything applies — no autonomous config changes.

**Full feedback cycle:**
```
quality_events.json
    → Pattern Miner system health pass
        → system_health_YYYY-MM-DD.json
            → Observer Agent
                → proposed config changes
                    → Claude Code developer review
                        → approved changes applied to coordinator.md / agent files
```

**Observer Agent design (to build):**
- Reads recent system health reports (last N weeks)
- Reads current `coordinator.md` and relevant agent instruction files
- Proposes specific text edits or new routing signal additions
- Produces `data/logs/observer_proposals_YYYY-MM-DD.json`
- Does NOT apply changes — proposal only

**Agent file:** `config/agents/observer.md` (to be written)
**Tool needs:** `read_system_health`, `read_agent_config` (already exists), `write_observer_proposals`

**Design questions to resolve before building:**
- How many weeks of system health data before Observer has enough signal to make reliable proposals?
- Proposal format: diff-style text edits vs. natural language suggestions vs. structured change objects?
- Should Observer read full `quality_events.json` (individual instances) or only Pattern Miner summaries?
- Cadence: run weekly alongside Pattern Miner, or on-demand?

---

**Alpha sizing note (from hardware analysis, 2026-06-02):**
Minimum alpha cohort for meaningful miss signal: 12 users.
Maximum supported by M5 Max 128GB after token optimizations: ~25-40 users.
Target: `max(12, hardware_max)` — hardware-limited upper bound, signal-floor lower bound.
