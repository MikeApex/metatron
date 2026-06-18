# Plan Review — Prompt for Separate Conversation
*Open this in a new Claude Code session to run the plan review milestone.*

---

## Purpose

All Phase 5 agent reviews are complete (or in progress). Before starting further builds, run a dedicated plan review to ensure Phase 5 remainder, Phase 6, Phase 7, and beyond are correctly structured and sequenced.

This prompt is intentionally run in a separate conversation so it doesn't compete with active agent review work.

---

## Read these first

In order:

1. `CLAUDE.md` — architecture, conventions, terminology
2. `archive/plans/phase5_prompt_2026-05-26.md` — original Phase 5 plan
3. `archive/plans/revision_3_1_snapshot.md` — prior revision snapshot (pre-Phase 5)
4. `archive/plans/future_phases.md` — parked future features (current; includes Observer Agent, Wishes, Environmental Monitoring, Addiction, Cognitive Profiling, User Engagement/Compliance)
5. `archive/plans/phase5_agent_reviews_continuation_2026-06-04.md` — Phase 5 state as of last session
6. `~/.claude/projects/-Users-md-homefolder-Desktop-multi-model-mcp/memory/MEMORY.md` — relevant memory files

---

## Task

Produce a roadmap document at:

```
archive/plans/phase5_to_future_roadmap_2026-06-09.md
```

---

## What the roadmap must cover

### 1. Terminology clarification
The terms "Phase" and "Deliverable" are used inconsistently across planning documents. Define them clearly and apply the definitions consistently throughout the roadmap:
- What is a Phase? What is a Deliverable? Are they nested or sequential?
- Reconcile with how they're used in existing files and arrive at a single convention going forward.

### 2. Phase 5 — remaining work
What is actually left in Phase 5? Agent reviews are wrapping up. What builds, integrations, or decisions remain before Phase 5 is closed?

### 3. Phase 6 — full scope
Based on all planning documents read, what does Phase 6 contain? What are the deliverables, in what order, and what are the dependencies between them?

Candidates currently scattered across documents:
- Deliverable 6: live data tools (weather, news, markets, transit), calendar/email integration, Wishes full build, encryption layer
- Observer Agent + quality feedback loop (Stages 1-3)
- Multi-user coordination (social scheduler)
- Addiction/behavioral health full build
- Cognitive function profiling (Learning & Growth + Mental Wellbeing)
- User Engagement / compliance design conversation
- Compliance audit (financial advice at commercial scale)
- Legal review (Wishes / advance directives)

### 4. Phase 7 and beyond
What belongs in Phase 7 vs. the "parking lot" in future_phases.md? What criteria distinguish Phase 7 scope from "indefinitely deferred"?

### 5. Sequencing and dependencies
For everything in scope through Phase 7:
- What depends on what? List blocking prerequisites in dependency order.
- Are there items currently scheduled that cannot start until something earlier is done?
- Are there items currently deferred that are actually blocking something planned?

### 6. Stale or superseded plan elements
What does the current plan say that is now outdated? What decisions have been made in Phase 5 that should update or retire earlier plan language?

### 7. Pre-Alpha checklist
The Alpha ships at the end of Phase 5 (or early Phase 6). What must be done before it ships?
- Known items: logging layer (Stage 1), compliance curve design discussion, legal/compliance flags
- What else is blocking Alpha?

---

## Output format

Follow the Phase Review Convention from `CLAUDE.md`:

> **[Finding]** — what was learned or decided
> **→ Implication** — what this means for the plan (specific: which section, which decision, which work item is affected)

Produce findings across all categories, then close with the full roadmap structured by phase and deliverable.

---

## Notes

- The compliance curve principle (pre-Alpha discussion required) is documented in `archive/plans/future_phases.md` — ensure it appears in the pre-Alpha checklist.
- Phase vs. Deliverable terminology resolution is the first task — it affects everything that follows.
- Do not begin building anything in this session. This is a review and planning session only.
