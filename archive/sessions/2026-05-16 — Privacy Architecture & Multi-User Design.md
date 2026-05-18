# Session: Privacy Architecture & Multi-User Design
*2026-05-16 / 2026-05-18*

## What Was Decided

### Privacy tier collapse
The semi-sensitive tier has been eliminated. `shareable_what` is now fully sensitive alongside `private_why`. Empirical testing demonstrated that the privacy boundary between the two tiers does not hold in practice — free-text synthesis from either layer produces HIGH-richness inference by an independent model. Behavioral patterns (avoidance, overwork, relational volatility) carry the inferential load independently of explicit motivations.

Updated in: `CLAUDE.md`, `config/goals.yaml`, `archive/plans/revision_3_1_snapshot.md`.

### Two-tier Orchestrator/Executor architecture — deferred
The group discussion (Sonnet, GPT-4o, Gemini) converged on: build the private model tier first, defer the synthesis/Executor split until a quality gap is demonstrated in practice. If eventually built, Tier 1 output must be a closed enum — never free text. Free-text synthesis is private_why in translation.

### Closed enum viability
Empirically tested. Closed enum directives produced MEDIUM inference richness vs HIGH for free text — a real but partial reduction. Confirmed workable as a privacy mechanism if and when the two-tier architecture is built, but not sufficient alone to make cloud dispatch safe at single-user scale.

### Multi-user architecture — Phase 7
At sufficient user scale, pooled cloud calls provide k-anonymity. The cloud dispatch threshold: *"Is this request attributable to a specific individual within the user pool?"* If yes, decompose further or keep private. If no, dispatch. The threshold scales with user count. Added as Phase 7 in the plan.

### ask_claude MCP server
Fixed and deployed. Two bugs resolved: `--tools ""` invalid flag when web_search=False; unbounded history accumulation causing subprocess timeout. Replaced with thematic conversation management: Haiku generates a topic label on first message, classifies each subsequent call, archives on topic change, restores matching archives. Labels are 3-5 word thematic summaries, not character truncations. Archives persist to disk.

## What Was Tested

**Synthesis leak test (Pepys persona):**
- Test A: 6 directives generated across 3 models × (full context / stripped context)
- Test B: All 6 directives reviewed by 2 inference models (GPT, Gemini)
- Result: Full context = HIGH richness. Stripped context = MEDIUM for GPT/Gemini-generated directives. Claude stripped = HIGH (behavioral patterns alone sufficient). Closed enum = MEDIUM across all inference models.
- Key finding: the inferential surface is the behavioral patterns layer, not private_why specifically.

## Next Step

Get a private LLM running on private hardware. This is the prerequisite for everything that follows — goals interview, sensitive-tier analysis, future multi-user private layer. VPS option (LLaMA 3.3 70B, ~$15-25/month) is viable for early testing before committing to dedicated hardware.

## Open Questions Deferred
- Closed enum schema design (what fields, what value sets)
- Multi-user data model and consent architecture (user research session required before Phase 7)
- arthur_brooks.md persona — opened but not discussed this session
