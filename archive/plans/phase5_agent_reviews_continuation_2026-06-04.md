# Phase 5 — Agent Reviews Continuation
*Open this in the next Claude Code session to continue where we left off.*

---

## How to start

Read these before doing anything:
- `CLAUDE.md` — architecture, conventions, terminology
- `archive/sessions/2026-06-04 — Agent Reviews, WV Deep Pass, Proactive Scans, Synthesizer Integration.md` — full context for decisions made in this session
- `archive/plans/phase5_agent_reviews_prompt_2026-06-02.md` — prior continuation prompt (now partially superseded but still useful for overall Phase 5 state)
- `~/.claude/projects/-Users-md-homefolder-Desktop-multi-model-mcp/memory/MEMORY.md` — check relevant memory files

---

## CURRENT STATE

### Agent reviews — status

All agents have been reviewed at least once. Deep passes (full structural + content review) completed on:

- `coordinator.md` ✓
- `synthesizer.md` ✓ (updated this session — conflicting signals, overcommitment, Voss/Socratic)
- `diarist.md` ✓
- `mental_wellbeing.md` ✓ (full rewrite — proactive scan, Big Five, clinical flags, cross-signals)
- `pattern_miner.md` ✓
- `goals_interviewer.md` ✓ (schema moved to reference file; 300 → 230 lines)
- `learning_growth.md` ✓ (proactive scan added; cognitive function + motivation backlog)
- `finance.md` ✓ (proactive scan, Work-Finance boundary)
- `physical_health.md` ✓ (medication criticality, exertion schema, nutrition, daylight backlog)
- `work_vocation.md` ✓ (deep pass this session — identity/vocation, flow as diagnostic signal, career coaching, NEGOTIATION_OPPORTUNITY, entrepreneurship backlog)
- `relationships.md` ✓ (CRM protocol, proactive scan, CONTACT_INCOMPLETE flag)
- `recreation_hobbies.md` ✓ (service/volunteering as first-class category, proactive scan)
- `research_agent.md` ✓ (light pass)
- `logistics.md` ✓ (write_config scope clarified, injection security note)
- `time_director.md` — tombstoned/retired

### Agents that could still benefit from a deeper pass

These received content improvements but haven't had the same systematic deep pass as MW, PH, and W&V:

1. **Relationships** — CRM protocol added this session; but baseline areas are still generic boilerplate (same copy as all other agents). The relationship domain has unique depth: attachment styles, communication patterns, social energy profiling. Candidate for deep pass.
2. **Recreation & Hobbies** — service/volunteering category added; proactive scan added. Still fairly thin on profile building and what "good leisure" looks like for different personality types.
3. **Finance** — proactive scan and boundary note added. The actual advisory content (investment philosophy, debt prioritization, tax awareness) could be richer.
4. **Learning & Growth** — proactive scan and cognitive function backlog added. The "doing and experiencing" dimension of learning is well-framed; the practice-tracking mechanism could be more explicit.
5. **Logistics** — functional but minimal. May not need a deep pass given its execution-focused role.

---

## BUILT THIS SESSION (confirmed working)

- `tools/agent_config.py` — `write_agent_config` / `read_agent_config` (35 tools total registered)
- `tools/wishes.py` — `write_wishes`, `read_wishes`, `generate_emergency_card` (shell; Synthesizer is sole writer; reads deferred to Phase 6)
- `config/agents/goals_interview_reference.md` — output schema and domain list extracted from goals_interviewer.md
- `archive/plans/future_phases.md` — environmental monitoring, Wishes full build, addiction, cognitive profiling, Observer agent, User Engagement/compliance design
- `archive/plans/phase5_agent_reviews_prompt_2026-06-02.md` — updated with DELIVERABLE 6 ITEMS and PLAN REVIEW MILESTONE sections

---

## BEFORE ALPHA — Logging layer (Stage 1 of self-improvement protocol)

Must be in place before first alpha session. See `archive/plans/future_phases.md` → Self-Improvement Protocol for full three-stage design.

**What to build before alpha:**
- `write_quality_event` tool (append to `data/logs/quality_events.json`)
- `config/agents/coordinator.md` — add implicit correction detection (flag when user re-states or corrects prior response)
- PWA — single "missed the mark" tap → appends `USER_CORRECTION` event
- Synthesizer `ROUTING_MISS` flag (already in `synthesizer.md`) wired to `write_quality_event`

Stages 2 (Pattern Miner system health) and 3 (Observer Agent) are Phase 6. Observer does not yet exist.

---

## PLAN REVIEW MILESTONE — schedule this soon

At the close of all agent reviews, run a dedicated plan review session before starting further builds. Purpose: ensure Phase 5 remainder, Phase 6, Phase 7, and future phases are correctly structured and sequenced.

Input documents:
- `archive/plans/phase5_prompt_2026-05-26.md` — original Phase 5 plan
- `archive/plans/future_phases.md` — parked future features
- `archive/plans/revision_3_1_snapshot.md` — prior revision notes

Output: `archive/plans/phase5_to_future_roadmap_{date}.md`

Note: clarify Phase vs. Deliverable terminology in this session — currently ambiguous across files.

---

## OPEN DESIGN QUESTIONS

These were surfaced in the last session and not yet resolved:

1. **Vitamin D flag — inference vs. explicit.** Do you want the Vitamin D flag based on modeled sun exposure (requires GPS + weather pipeline) or only when the user explicitly reports sun time? The inference model is more useful; the explicit model can be added now with zero infrastructure.

2. **Wishes read access design.** Deferred to Phase 6. Structural + legal question: which sections are readable, by whom, under what conditions. See `archive/plans/future_phases.md` for full scope.

3. **User Engagement / compliance design.** Added to `future_phases.md`. Needs a dedicated design conversation before building. Key question: what constitutes a "reward" in this tool's context?

---

## KEY ARCHITECTURAL DECISIONS FROM THIS SESSION

For context in the next session:

- **Wishes access model:** Synthesizer is sole writer. Subagents surface via `PROFILE_GAP`; no agent reads or writes wishes store directly. Read access deferred to Phase 6 (legal + structural design needed).
- **Proactive scans:** Now present in all data-holding specialist agents (MW, PH, W&V, Relationships, Recreation, Finance, Learning). Logistics excluded by design (execution-focused). Research Agent excluded by design (decontextualized).
- **Standing calls removed:** MW and PH are NOT called on every exchange. Instead: called on morning brief and evening close sessions (coordinator routes whole-person sessions). Weekly PH review remains in scheduler.
- **Overcommitment:** Synthesizer watches for this system-wide across all domains, not just when individual agents flag it.
- **CRM:** Relationships writes and reads directly. Unlike Wishes — operational data, not sensitive documents.
- **write_config scope:** Only Goals Interviewer (goals.yaml, mission.md, prime_directive.md) and Synthesizer/Logistics (scheduler.yaml entries) may use `write_config`. All specialists use `write_agent_config` for their own persistent state.
- **config/voice.md:** Planned for Phase 6+. Two reference points: Chris Voss (tactical empathy, calibrated questions, mirror) and Socratic method (surface insight for user to own the conclusion and initiate action). See `synthesizer.md` and `revision_3_1_snapshot.md` for the full planning note.

---

## WHERE TO START

**Option A — Continue agent deep passes:**
Relationships is the strongest candidate for the next deep pass. It has a full CRM tool set, a proactive scan, and a CONTACT_INCOMPLETE flag — but the profile-building section is still generic. The relational domain is rich enough (attachment, communication style, social energy) to warrant the same treatment W&V got.

**Option B — Run the plan review:**
If all agent content feels solid enough, go straight to the plan review milestone and produce the roadmap document. This unblocks knowing what Deliverable 6 actually contains before any more builds happen.

Recommended: Option A (Relationships deep pass), then immediately segue to the plan review while the session is warm.
