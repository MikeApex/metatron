# Future Phases — Parking Document
*Features that belong after MVP. Not scheduled. Not designed in detail. Parked here so they aren't lost.*

---

## SSE Reconnect + Result Fetch + Drain Gate (Pre-Beta hardening)

**Context:** Fixes 1 and 2 (graceful shutdown timeout + deploy drain loop) were implemented 2026-06-26 and cover Alpha. This Fix 3 is the complete solution for Beta and beyond, when restarts may happen mid-session without a developer controlling both sides.

**Three parts — implement together:**

1. **"No new sessions" drain mode.** When a deploy is in progress, the server should reject new `/session/stream` requests with `503 Service Unavailable` rather than accepting them and risking a mid-pipeline restart. Requires a drain flag (`_draining: bool`) that `/active` also exposes, and a new `/drain` endpoint that sets it. `deploy.sh` calls `/drain` first, then polls `/active` until 0. Client should surface the 503 cleanly rather than showing a generic error.

2. **Client reconnect on abort.** When the client receives a `Fetch is aborted` error (or any SSE connection failure), it should not surface an error immediately. Instead: wait 3–5 seconds, reconnect, and poll a `/result/{date}/{seq}` endpoint for the completed response. The conversation record is already written to disk before the process dies — the client just needs a read path.

3. **`/result/{date}/{seq}` endpoint.** New server endpoint that reads a single entry from `data/conversations/{date}.jsonl` by seq and returns it. Lightweight — no pipeline involved. Client uses this as the recovery path after a reconnect following an abort. Also useful for manual troubleshooting (replaces the current SSH + Python one-liner for simple lookups).

**Why these three go together:** the drain gate prevents the problem; the result fetch recovers from it when prevention fails (crash, SIGKILL, external restart); the `/result` endpoint is the shared primitive both use.

**Prerequisite:** none — can be built independently of other Phase 6 work.

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

## Projects — Discrete Goal Planning and Execution (Phase 6+)

A structured planning and project management feature for large, bounded, real-world goals: home renovation, photo organization, garage cleanout, estate planning, learning a new skill, preparing a major event. These are different from Goals in character — they have a defined start and end, discrete deliverables, and often require domain-specific task decomposition rather than open-ended progress tracking.

**Why it's distinct from Goals:**
Goals (Tier 3) capture ongoing life direction — health, relationships, career growth. Projects capture bounded initiatives with a finish line. A user might have a Goal of "maintain a comfortable, organized home" and a Project of "renovate the kitchen." The Goal persists; the Project completes and archives. Overlap is intentional — Projects should be able to reference and contribute toward Goals, but shouldn't be forced into the Tier 3 goals schema.

**Core feature set:**

- **Project creation interview** — new specialist or Coordinator-initiated flow that captures: what the project is, why it matters, rough scope, hard deadlines or constraints, external dependencies (contractors, other people, budget). Produces a structured project record.
- **Task decomposition** — the system breaks the project into phases or milestones, then into actionable next steps. This is the core planning function: large, vague goals ("renovate the kitchen") become concrete sequences ("measure current cabinets → get 3 contractor quotes → select cabinet style"). Decomposition may be domain-aware (a renovation project looks different from a photo archive project).
- **Progress tracking** — session-to-session continuity. User reports what they've done; the system updates the task list, flags blockers, surfaces the next action.
- **Domain specialization** — some project types benefit from pre-built templates or domain knowledge: home renovation (permits, contractors, material lead times), financial projects (tax season, estate settlement), creative projects (manuscript, album, portfolio). Consider whether specialists should handle their own domains (Physical Health owns a fitness challenge project; Finance owns a tax prep project) or whether a dedicated Projects agent coordinates across domains.
- **Handoff to Goals** — when a project completes something that should become an ongoing habit or life practice, the system should offer to convert the outcome to a Goal. "You've organized your photos — would you like to add a recurring reminder to do this quarterly?"

**Design questions to resolve before building:**

1. **Agent architecture:** Single Projects agent vs. delegating project types to existing specialists with a Projects coordinator on top. The latter avoids building domain knowledge twice but adds routing complexity.
2. **Schema:** How does a project record relate to the goals schema (`config/goals.yaml`)? Separate data structure, or an extension of the existing goal hierarchy? Consider: projects have subtasks, deadlines, blocking dependencies — none of which exist in the current goals schema.
3. **Decomposition engine:** LLM-driven decomposition at creation time vs. incremental decomposition as the project progresses. Incremental is more adaptive but requires more session-to-session state. Large upfront decomposition can overwhelm the user with tasks they're not ready to see.
4. **Duration and scope limits:** How long can a project run? Some home renovations take 18 months. Does the system need a project "health" concept (stalled, active, on-hold, abandoned)?
5. **Coordinator integration:** Projects should surface to the Coordinator when they have active next steps — today's action item from an ongoing renovation project should appear in a regular check-in. How does a project "push" its current action into Coordinator context without bloating the system prompt?

**Related features:** Wishes / Emergency & Legacy (similar structured interview + phased task completion); Compliance Development (project step-up pacing uses the same compliance curve mechanics).

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

---

## Specialty Subagents (Phase 7+ / Design First)

Narrow-scope, task-execution agents for a single transactional or research domain. Unlike the current specialist roster (which covers broad life domains), specialty subagents are activated on-demand for a specific task and return a result that feeds into Logistics, Finance, or another existing specialist.

**Distinction from existing agents:** Logistics coordinates scheduling and reminders. A purchasing agent executes — it compares products, tracks prices, surfaces options with enough detail to make a decision. Finance tracks spending. A flight comparison agent searches, filters, and presents bookable options with trade-offs explained. The depth of domain knowledge and the task-execution orientation distinguish these from the existing roster.

**Candidate list:**

| Agent | Domain | Example tasks | Natural parent specialist |
|---|---|---|---|
| Purchasing | Product research + price tracking | "Find the best noise-canceling headphones under $200"; monitor a wishlist item for price drops | Logistics |
| Flight comparison | Air travel research | Compare routes / prices / times; flag best-value options given stated preferences | Logistics |
| Accommodation | Hotel / rental research | Filter by location, price, amenities; compare against past preferences | Logistics |
| Restaurant / event booking | Local discovery + reservations | Find options matching mood or occasion; make a reservation if authorized | Logistics |
| Rx / pharmacy | Medication logistics | Cost comparison across pharmacies, refill timing, interaction context (non-diagnostic) | Physical Health |
| Job search | Career opportunity scanning | Track relevant postings, compare against vocation profile, surface application timing | Work & Vocation |
| Gift finding | Occasion-aware product search | Find gifts for named contacts using CRM profile data | Relationships |

**Architecture decisions to resolve before building:**

1. **Agent vs. tool set.** For pure search / retrieval tasks a rich tool set registered to the parent specialist may suffice. For tasks requiring judgment across options given personal history — "compare these 5 flights given how I travel" — a dedicated instruction file and `run_subagent` call is warranted. Decide per-agent, not globally.
2. **Authorization model.** Any booking or purchasing capability requires an explicit per-action confirmation gate in Python tool code (not a prompt instruction). No specialty agent commits money or calendar slots without a user-confirmed action step. Design the confirmation UX before any booking capability is live.
3. **Coordinator routing table.** Does the Coordinator route to specialty subagents directly, or does the parent specialist (Logistics) act as an intermediate dispatcher? The latter keeps the Coordinator's routing table from growing with every new micro-agent.
4. **Tool infrastructure.** Most specialty agents need integrations not yet built (E1) — product APIs, flight aggregators, OpenTable, pharmacy APIs. Identify which E1 integrations are prerequisites and which can be deferred.
5. **Privacy.** Search queries for flights, products, and restaurants are low-sensitivity and cloud-safe. If the agent also receives personal context to personalize results (preferences, CRM profile for gift recipient), the decontextualized query goes cloud while the personalization layer stays local — same routing principle as Research Agent. Document per-agent.

**Build prerequisite:** E1 integrations + B2 auth in place. Design conversation required before any instruction files are written — evaluate the agent-vs-tool question first, since the wrong choice adds unnecessary complexity.

---

## Session Agents (Phase 7+ / Design First)

Time-bounded interactive agents for discrete, well-defined goals. Unlike the current specialist roster — which runs within the Coordinator / Synthesizer pipeline on every session — session agents operate as a focused mode: the user enters a session for a specific purpose, the agent works with them directly or through Synthesizer as host, and the session ends with a concrete artifact or outcome.

**Key distinctions from existing agents:**
- **Discrete goal with a defined endpoint.** A language tutor session ends when the user stops or reaches the lesson goal. A trip planning session ends with an itinerary. Normal Coordinator / Synth sessions are open-ended by design.
- **User-facing or Synth-hosted.** Session agents may speak to the user directly (conversational practice, coaching, interactive planning) or feed structured output to Synthesizer (itinerary assembly, workout design). The mode depends on whether real-time back-and-forth with the user is the value.
- **Session artifact.** Most session agents produce something: a completed itinerary, a vocabulary list, a workout plan, a practice transcript. This artifact is the deliverable, distinct from the ongoing logs that normal specialists produce.

**Candidate list:**

| Agent | Goal | Interaction mode | Output artifact |
|---|---|---|---|
| Language tutor | Conversational practice, vocabulary, grammar | User-facing (dialogue) | Session transcript + vocabulary list |
| Trip planner | Build a complete itinerary for a defined trip | Synth-hosted initially, then user-facing refinement | Itinerary → `data/documents/` (E7 Tier 3) |
| Interview coach | Practice for a specific interview type (behavioral, technical, case) | User-facing (role-play) | Feedback summary + study areas |
| Workout designer | Design a training block or single session | Synth-hosted | Workout plan → Physical Health log |
| Meal planner | Plan meals for a week or event | Synth-hosted | Meal plan → Logistics / grocery list |
| Writing coach | Improve a specific piece of writing | User-facing (line-level feedback) | Annotated draft |
| Debate partner | Pressure-test an argument or decision | User-facing (Socratic adversary) | Summary of strongest objections |
| Study session | Learn a specific topic interactively | User-facing (Socratic teaching) | Topic summary + gaps identified |

**Architecture decisions to resolve before building:**

1. **Pipeline integration.** Does a session agent bypass the Coordinator entirely, or does the Coordinator hand off to it? Proposed model: Coordinator detects session intent ("let's practice Spanish"), sets a session mode flag, and Synthesizer routes directly to the session agent for the duration. Normal pipeline resumes on session end. Resolve before any instruction files are written.
2. **Session-scoped state store.** Session agents need to maintain state across turns *within* the session (current lesson, itinerary draft in progress, practice scenario in play). This is distinct from the context tracker, which maintains state *across* sessions. Design the session-scoped state store schema before building.
3. **User-facing vs. Synth-hosted split.** User-facing session agents bypass Synthesizer's synthesis role — the agent speaks directly. This must be an explicit architectural decision, not an accident. For conversational practice (language tutor, interview coach), direct is likely better — Synth as intermediary adds latency without adding value. For planning tasks (trip planner, meal planner), Synth-hosted is fine and keeps the user experience consistent.
4. **Entry and exit protocol.** Define how the user enters and exits session mode without breaking the normal conversation flow. "Start a trip planning session" → session begins. "We're done" / "enough for today" → session ends, artifact saved, Synth acknowledges. The exit must not lose session state if the user disconnects mid-session — artifact is checkpointed, not written only on clean exit.
5. **Artifacts and handoff.** Session artifacts go through the E7 file storage tier model. Trip itinerary → Tier 3 owned (encrypted). Workout plan → Physical Health log. Vocabulary list → Learning & Growth log. Define the handoff to existing specialists per agent before building — avoid a session agent that writes to nowhere and loses its output.
6. **Privacy.** Language tutoring on generic topics is cloud-safe. Trip planning with actual travel dates, companions, and budget is personal context — local model or decontextualized query only. The same session agent may need different routing depending on what context it carries during the session. Document per-agent.

**Design conversation (prerequisite to any build).** Session agents represent a meaningful pipeline addition — a new execution mode, a new state store, a new entry/exit protocol. Run an E4-style design conversation before writing any instruction files.

**Related — Projects feature:** A trip planning session is a bounded Project type (see Projects section above). Evaluate whether session agents are best implemented as a mode within the Projects architecture before designing a separate session pipeline. If Projects ships first, session agents may be a Projects sub-type rather than a parallel architecture.
