# Phase 5 — Coordinator/Synthesizer Build — Continuation Prompt
*Use this to open a new Claude Code session to continue this work.*

---

You are Claude Code continuing development of a personal AI life manager.
Working directory: ~/Desktop/multi-model-mcp

Read these files before doing anything else:
- CLAUDE.md (architecture, conventions, terminology)
- archive/sessions/2026-05-28 — Coordinator-Synthesizer Architecture, Agent Reviews.md (full context for decisions made)
- archive/plans/phase5_prompt_2026-05-26.md (overall Phase 5 plan)
- config/agents/coordinator.md (current state — may already be the new Coordinator if build is complete)
- config/agents/synthesizer.md (new file — exists if build is complete)

Also check memory at ~/.claude/projects/-Users-md-homefolder-Desktop-multi-model-mcp/memory/MEMORY.md
and read project_coordinator_synthesizer_architecture.md from that memory directory.

---

## ARCHITECTURE DECIDED — BUILD STATUS

The two-agent head architecture was fully designed in the 2026-05-28 session. Check the session archive and synthesizer.md / coordinator.md to determine what has been built vs. what remains.

### The architecture

**Coordinator (Ears — not user-facing):**
- Holds the running conversation context object
- Loads tiered context at session start: Prime Directive/Mission/Goals (always) + past 24h logs + gap since last Pattern Miner run (high detail) + past week compressed + on-demand beyond
- Receives user input
- Clarifies ambiguity before routing — asks one focused question rather than guessing
- Resolves intent in context of conversation thread
- Constructs specialist directives (message + relevant thread context, not raw input)
- Fans out to specialists in parallel
- Passes full context package to Synthesizer
- NEVER speaks to user
- NEVER sees specialist outputs
- Receives internal note from Synthesizer after each exchange; updates conversation thread

**Synthesizer (Brain + Mouth — user-facing):**
- Receives: context package from Coordinator + specialist outputs directly
- Time Director's prioritization intelligence built in (Time Director retired as standalone)
- Integrates, reasons, determines what to surface
- Multi-round conditional specialist chains (ReAct pattern): reason → act → reason → act → respond
- Default max 3 rounds of follow-up calls; if more needed, flags and explains why
- Can update user mid-chain: "Hang on, I'm checking on this — are you experiencing any other symptoms?"
- quick/deep complexity hint governs chain depth
- Produces: user response + internal note to Coordinator (what was surfaced, what was held, flags)
- Sends internal note to Coordinator for thread continuity

**Pipeline (not nested):**
- Orchestrator manages the handoff — neither agent calls the other as a subagent
- User input → Coordinator pass (routing + context) → specialist fan-out → Synthesizer pass (integration + response) → user
- Specialists return outputs to Synthesizer directly

### Files to build/change

| File | Action | Status |
|---|---|---|
| `config/agents/synthesizer.md` | Create — restructure from old coordinator.md, absorb Time Director | Check |
| `config/agents/coordinator.md` | Replace with new Ears agent | Check |
| `config/agents/time_director.md` | Retire — archive, remove from routing | Check |
| `config/modules/routing.yaml` | Add synthesizer; update coordinator | Check |
| `core/server.py` | Review default agent | Check |
| `core/orchestrator.py` | Pipeline support: two-pass exchange | Check |

---

## SPECIALIST AGENT REVIEWS — STATUS

Agents reviewed/updated this session:
- Learning & Growth ✓ (substantially revised)
- Finance ✓ (list tools added, RESEARCH_NEEDED already present)
- Time Director ✓ (patched; to be retired in build)
- Logistics ✓ (RESEARCH_NEEDED + list tools)
- Physical Health ✓ (role expanded, tools added)
- Work & Vocation ✓ (RESEARCH_NEEDED + list tools)
- Relationships ✓ (RESEARCH_NEEDED + list tools)
- Mental Wellbeing ✓ (RESEARCH_NEEDED + write_journal)
- Recreation & Hobbies ✓ (RESEARCH_NEEDED + list tools)

Still to review against Phase 5 conventions:
- Mental Wellbeing (deeper review — only patched)
- Physical Health (deeper review — only patched)
- Work & Vocation (deeper review)
- Relationships (deeper review)
- Recreation & Hobbies (deeper review)
- Research Agent (review)
- Logistics (deeper review)
- Diarist (check capture-first, check against new architecture)
- Goals Interviewer (check against new architecture)
- Pattern Miner (check against new architecture)

---

## KEY DECISIONS — DO NOT REVISIT

- Two-agent head: Coordinator + Synthesizer. Pipeline. Neither calls the other.
- Time Director: retired, absorbed into Synthesizer
- Subagents report to Synthesizer directly
- 3-round default for Synthesizer chains; flag if more needed
- Coordinator is an LLM agent (not code function) — config-driven routing philosophy
- Semantic routing (FAISS-based) flagged for future, not Phase 5
- Coordinator never speaks to user, never sees specialist outputs
- Synthesizer sends internal note to Coordinator for thread update

---

## WHERE TO START

Check what's been built (synthesizer.md, new coordinator.md) and continue from there.
If starting fresh on the build: begin with synthesizer.md (most complex file), then new coordinator.md, then routing.yaml, then orchestrator.py pipeline changes.
