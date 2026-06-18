# A1 — Compliance Curve Design Conversation
*Open this in a new Claude Code session. Roadmap item A1 (2026-06-10 roadmap). This is a conversation, not a build task.*
*Parallel-safe: other chats are running simultaneously — see File ownership below.*

---

## Read these first, in order

1. `SESSION.md` — current state
2. `archive/plans/phase5_to_future_roadmap_2026-06-10.md` — Section 0 and item A1
3. `config/constitution.md` — Tier 0 (READ-ONLY — never edit without explicit user instruction)
4. `config/agents/synthesizer.md` — current behavior-introduction posture
5. `config/preferences.yaml` — the proactive settings this decision governs
6. `archive/plans/future_phases.md` — engagement/compliance items parked there

Do not begin until you've read all six.

---

## Purpose

Resolve the compliance curve design before Alpha. This decision governs A5c (which proactive preferences are safe to activate) and is the foundation for all habit-formation and engagement features (Phase 6 / E4).

Design principle to apply: **stay behind the compliance curve.** Introduce new behaviors at the level the user can actually execute, then build from there. "Run 500m" before "run 5k." The goal is a successful first rep, not the right rep.

---

## Questions to resolve (work through these with the user — this is an interview/discussion, not a monologue)

1. Which agent calibrates new behavior introduction — Synthesizer as gatekeeper? per-specialist? a shared principle across all agents?
2. What is the ratchet mechanism — how does the system step up difficulty, and how does it step back when compliance fails?
3. Does the Constitution need a statement on this, or is it a Synthesizer-level instruction? (Default to Synthesizer-level — Constitution edits require explicit user instruction.)
4. Given the answers above: which `config/preferences.yaml` settings are safe to activate at Alpha (A5c)?

Contribute your own recommendation on each question, then discuss. Number all options and recommendations.

---

## Output

1. Decision document: append to `archive/plans/future_phases.md` or create `archive/plans/compliance_curve_decision_2026-06-11.md` — record the decision, the rationale, and the A5c activation guidance.
2. If the decision assigns ownership to a specific agent: **record the exact proposed instruction text in the decision doc — do not edit the agent file in this chat** (see File ownership).

Test criterion (from roadmap A1): decision documented; downstream agent-file edit queued with exact text.

---

## File ownership (parallel chats are live)

- **This chat owns:** the decision document; `archive/plans/future_phases.md`
- **Do not edit:** `config/agents/synthesizer.md` or `config/agents/coordinator.md` (owned by the A2 Logging Layer chat); `core/orchestrator.py`, `config/modules/routing.yaml` (owned by the A4+A6 chat); `config/constitution.md` (never)
- Apply queued agent-file edits in a follow-up after the A2 chat closes.

## Session close

- Create `archive/sessions/2026-06-11 — A1 Compliance Curve Decision.md` early in the session, per convention.
- SESSION.md update at close: additive only — mark A1 done, do not rewrite other chats' lines.
