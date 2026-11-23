### 2026-11-23, seventh (ranking Part B — Mike interviewed on what should outweigh what; the regret-of-delay plan written, Fable-reviewed, every finding reconciled; phase 1 build prompt and a research prompt ready) — no code; **nothing deployed**

**Incoming handoff:** `archive/handoffs/2026-11-22-ranking-part-b-interview-prompt.md` (from the
11-22 handoff paragraph: *"Next: Ranking Part B — interview Mike, then plan … Rulings 6–8 wait for
its phase 1; no back-burner review exists yet"*).

**Done:**
- An eight-topic interview with Mike (his order: costs first, then urgency, protected time,
  passions, probing, climb, back burner and reconciliation, signals). Rulings B1–B32 are in
  `archive/plans/ranking_values_plan_2026-11-23.md` § 2, all design (no personal deviations).
- **The central ruling:** rank by **the regret of delay**. What one more day of not doing it would
  cost, weighed against the other uses of that time. Costs accrue in shapes, and neglect is
  convex. Mike's example: *"$30 for a day's delay might be ok, $30*365 days vs not speaking to Dad
  for a year is unacceptable. There's the convexity."*
- The plan: four shapes (step, accruing, neglect, cliff); cost dimensions with a floor and
  compounding; who bears the cost; attention blocks; protected time with a convex intrusion cost,
  asked about first; passions; a probe at mention, with a look-up first; a start-late buffer; a
  30-day back burner; a weekly priorities conversation; signals with a monthly review. It is in
  three phases, each shadowed and live-checked.
- Fable adversarial review (medium): 9 findings, all accepted, reconciled in plan § 10.
  `archive/plans/adversarial_review_ranking_values_plan_2026-11-23.md`.
- Prompts: `archive/handoffs/2026-11-23-ranking-research-prompt.md`, which Mike runs in a regular
  Claude chat (ten topics, no personal detail), and
  `archive/handoffs/2026-11-23-ranking-part-b-phase-1-build-prompt.md` (Opus, high).

**Options rejected:**
- **Multiplying or adding urgency and importance** — Mike rejected the framing. A task's rank is
  the slope of its cost curve today, which neither formula captures.
- **Reserved time for everything important but not urgent** — kept only for building goals.
  Relationships and upkeep rise on their own neglect curves.
- **Learning a contact's cadence from history** — *"history does not show desire but habit"*, so
  Metatron asks, and history only informs the question.
- **Lifting the WebSearch deny for the research** — Mike runs it himself in regular Claude instead.
- **Place-and-say for intrusions into the user's own time** — Mike ruled ask first, always.

**Believed true, wrong (caught by the review, checked against the code):**
- **Part A's "deadlines climb" moves only flexible tasks.** `_candidates` admits today's list,
  `lapsed` and `in_window`, so a non-flexible deadline first appears on its due day. Mike ruled
  more broadly (R3): a task that must start today counts as today's; when room remains, advance
  work and goal steps are suggested; unfilled time is labelled as deliberate. This amends the
  10-24/25 "one definition of today".
- **Look-ups are decontextualised by instruction only.** No code checks what a Research Agent
  query carries, so the plan builds a dedicated tool, `lookup_public_fact`, with a code guard.
- **`answer_event` cannot carry a yes/no on a task**, so the intrusion ask needs a new tool,
  `answer_ask`.
- The draft's derived `stakes` would have overwritten Part A's stored values, so flag-off would
  not have been Part A. Fixed: the cost record never writes `stakes`.

**Scope call put to Mike, no objection:** no task enters sleep (the planner has no slots there).
B11's emergency example is delivery, not ranking.

**Mike-gated next:** the research run; after phase 1 deploys, a three-morning shadow comparison
(plan § 7.2), proposed as a walkthrough.

