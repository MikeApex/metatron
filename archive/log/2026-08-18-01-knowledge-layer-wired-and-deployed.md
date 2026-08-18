### 2026-08-18 (the knowledge layer is wired, deployed, and the plan is closed) — `360b843`, `d128130`, `7cb9ebd`, `2a51f46` — **deployed; step 10 run on the VM**

Phase 1 (2026-08-15) gave the wisdom store a subject axis and migrated Mike's 59 entries.
**Nothing read it.** This session built steps 4–12 of
`~/.claude/plans/to-be-clear-we-modular-knuth.md` and ran the one step that had to wait for a
deploy. Incoming handoff: *"Steps 4–12 are unbuilt and nothing is wired at runtime — no agent
reads by domain, the Synthesizer has no grant, no manifest renders. Until those land the
migration is inert."*

**What shipped.** `config/modules/knowledge_domains.yaml` is the only place subjects and the
agent roster meet, so a roster change edits a map rather than user data. `load_profile()`
renders a ~20-token manifest naming which subjects hold entries — derived by enumeration, so it
cannot drift the way `_PROMPT_EXCLUDED` did. `KNOWLEDGE_TO_LOAD` is parsed in
`_dispatch_from_coordinator()` and fetched into both the Synthesizer input and the directives of
specialists the domain map names; it tolerates absent, malformed **and hallucinated** domains by
intersecting against domains actually present. `WISDOM_PROPOSAL:` is parsed in Python and
stripped before synthesis — never relayed through a model, which is what makes "propose only"
mean anything while `dispatch_tool()` still enforces no allowlist. Seven agents were *instructed*
to read the store and granted nothing, `pattern_miner` among them — told to call
`find_duplicate_wisdom` since Phase 3 while holding no wisdom tool at all.

**Two defects found by running it, not by reading it.** Two pipeline turns wrote near-duplicate
entries recording an *intention* ("wants to change breakfast") as standing fact; the guidance now
separates intentions from habits, and the next run kept a genuine observed pattern while dropping
the intention. Rewriting a pre-migration entry also left the dead `category` field beside the new
`domain`.

**Pass A was abandoned deliberately, and that is the session's main judgement.** The plan wanted
"thinking about changing up breakfast" to reach the stored fact with **no** `physical_health`
dispatch. It reaches the fact; PH is dispatched anyway, on two runs — the second after an
explicit worked example was added to `coordinator.md` and then **reverted for changing nothing**.
The Coordinator is not misbehaving: `coordinator.md:48` mandates dispatch for advice requests and
is deliberately left dominant, because over-dispatch costs tokens while under-dispatch loses a
user's record. **Rejected: tuning routing until the gate went green** — that is the one direction
the counter-test exists to prevent, and Pass B passing today would not prove it survived the
change. `tests/run_knowledge_routing.py` now gates retrieval and keeps the reasoning in its
docstring so it is not rediscovered as a bug.

**Step 10, on the VM.** `health_notes` → `standard_breakfast`, domain `food`, provenance
`stated`. **The dry run reported no collision and was wrong** — it checked for
`standard_breakfast` while the same fact sat under `oatmeal_formula`, an empty placeholder
("[User needs to specify their formula details here]") that would have been left beside the real
entry. Caught by reading the domain, not by the check. `find_related_wisdom()` exists because of
it, and **its design is measured, not assumed**: the incoming value scores 0.484 against the
placeholder it duplicated and 0.479 against "adds 20g walnuts to porridge only on training days",
a distinct fact that must not be touched. Duplicate and nuance are indistinguishable by
embedding, so **semantic similarity was rejected outright** and `find_duplicate_wisdom`'s 0.85
default would have missed the real case. Two precise signals instead — a distinctive word shared
with an existing *key* (exact tokens, so "nuts" ≠ "walnuts"), and an entry reading as a
placeholder. It warns and never merges: a near-duplicate and a genuine refinement cannot be told
apart automatically. A4 pipeline **3/3 PASS** after the migration and again after the follow-ups.

**Believed true earlier, wrong.** (1) *"`deploy.sh` needs `--tunnel-through-iap` adding"* — it has
always passed it; the stale commands were in `docs/INFRASTRUCTURE.md`'s rebuild section, which
predated the 2026-07-31 VPC rebuild, and that is where the failing command came from. (2)
*"Migrating sarah_chen is what makes A4 exercise the knowledge path"* — the Mac and VM stores had
**diverged completely** (38 entries vs **1**), and the VM's single entry is a work-boundary
pattern no clinical scenario touches. Both migrated; A4 knowledge coverage is still absent and is
now a filed item. Her Mac store went 38 → 19: heuristics were unusable (`boundary_enforcement`
and `manic_shift_triggers` → `sleep`, both bipolar entries → `other`), so all 38 were hand
assigned, and a 20-entry deflection cluster was consolidated — `health` 29 → 10, which is what
stops the real clinical entries being buried under a capped read. Nothing deleted; 19 archived
with `merged_into` pointers.

**Also retired:** `health_notes` from `_SCALAR_FIELDS`, `_PROMPT_EXCLUDED`, the prompt render and
the persona template, now that the data has moved. `write_profile`'s unknown-field error
redirects health/diet/sleep/habit facts to `write_wisdom` instead of only refusing.

