# Check 12 — Constitution Alignment Review
*Open this in a new Claude Code session. Phase 5 sign-off check 12 (2026-06-10 roadmap, A7 table). Read-only review producing one artifact.*
*Parallel-safe: other chats are running simultaneously — see File ownership below.*

---

## Read these first, in order

1. `SESSION.md` — current state
2. `archive/plans/phase5_to_future_roadmap_2026-06-10.md` — A7 check 12
3. `config/constitution.md` — Tier 0, the standard everything is measured against (READ-ONLY, always)
4. `tests/phase5_testing_plan.md` — check 12 criteria (the detailed version)
5. All 12 specialist agent files in `config/agents/` (skip coordinator, synthesizer, time_director, goals_interview_reference for the matrix; include coordinator and synthesizer in the inter-agent contradiction pass)

Do not begin until you've read all of the above.

---

## Task

Produce `archive/constitution_alignment_review_2026-06-11.md` with two parts:

### Part 1 — Alignment matrix (12 specialists × Tier 0 principles)

For each specialist against each constitution principle: **Aligned / Tension / Conflict**, with a quoted line from the agent file for every Tension or Conflict. Flag specifically:
- Values that contradict Tier 0 principles
- Promises that exceed the tool's defined scope
- Framings that violate "hypothesis not verdict" or "output not process" (discretion)

Pass condition: no Conflicts; Tensions resolved by deferring to the constitution, with the resolution noted.

### Part 2 — Inter-agent contradiction pass + precedence order

1. Review all specialist files as a set. Flag any case where two specialists would give conflicting guidance on the same life domain (e.g. Work & Vocation urgency vs. Mental Wellbeing rest; Physical Health caloric restriction while Mental Wellbeing is in active support mode).
2. For the overlap domains — **sleep, addiction, emotional state** at minimum; add any others you find — document a precedence order for which agent's framing wins when the Synthesizer integrates across them. This precedence table is the check 12 deliverable the Synthesizer's synthesis depends on.

Number every finding. A finding without an implication is a summary — state which agent file, which line, and what should change.

---

## File ownership (parallel chats are live)

- **This chat owns:** `archive/constitution_alignment_review_2026-06-11.md` only
- **Strictly read-only on everything else.** Proposed agent-file edits go in the review doc as exact quoted replacements — they are applied in a follow-up after the user reviews and the parallel chats close. `config/constitution.md` is never edited.
- Note: the A2 chat is editing `synthesizer.md`/`coordinator.md` concurrently — read them fresh, and date-stamp which version you reviewed.

## Session close

- Create `archive/sessions/2026-06-11 — Constitution Alignment Review.md` early in the session, per convention.
- SESSION.md update at close: additive only — record Conflict/Tension counts and where the precedence table lives.
