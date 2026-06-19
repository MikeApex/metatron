# A1 Compliance Curve — Continuation Session
*2026-06-19. Continuation of the A1 parallel track chat (prior window ran out of context, summarized). This window completed the remaining work.*

---

## What this window covered

The prior window (started 2026-06-13) had resolved Q1–Q4, drafted the decision document skeleton, and set up the MCP model clients. It ran out of context before firing the research queries. This window:

1. **Fired all 6 research queries** — Research 1 (compliance science) and Research 2 (app uptake mechanics) sent to GPT 5.4, Gemini, and Claude. Opus timed out on both; Sonnet 4.6 provided adjudication.
2. **Wrote the decision document** — `archive/plans/compliance_curve_decision_2026-06-13.md` with full research synthesis, adjudicator additions, proposed agent instruction text, and file edits queued.
3. **Updated SESSION.md and future_phases.md** — A1 marked done; compliance curve block marked RESOLVED.
4. **Updated MCP servers:**
   - `ask_gpt.py` — added o3, o1, o1-mini; auto-discovery via OpenAI models API on startup; `refresh_models` tool; full model ID passthrough
   - `ask_gemini.py` — added auto-discovery via Gemini API; `refresh_models` tool; full model ID passthrough; fixed DEFAULT_MODEL back to `gemini-3.1-pro-preview` (had been incorrectly changed to 2.5)
   - `ask_claude.py` — added opus-4-8, fable; increased Opus timeout 120s → 600s; `refresh_models` tool
5. **Re-ran research through o3** — both prompts. o3 added: optimal band quantified (10–25% above current capacity), dual diagnostic check (confidence ≥7 + meaning ≥6), Tiny Habits conditional (only converts with escalation plan), restarter floor (50–70% of former peak), progression gate (≥80% adherence/2 weeks), retention curve numbers.
6. **Re-ran research through Gemini 3.1** — correcting the earlier 2.5 error. 3.1 added: IKEA Effect/meaningful friction in onboarding; emergency reserves as streak alternative (Sharif & Shu 2012); range goals over fixed targets in operating mode; data-as-mirror transition at week 4+.
7. **Source check** — all citations audited. 8 probable hallucinations identified and ⚠-flagged inline (not removed). Bibliography added with confidence ratings (✓ verified / ~ plausible / ⚠ probable hallucination). Key corrections: Breines & Chen 2014 → 2012 PSPB; Locke et al. 1981 meta-analysis stats not verifiable; Turk & Rudolph 2022 unverifiable; Milkman et al. 2021 Nature Comm streaks unverifiable.

---

## Decisions recorded

| Q | Decision |
|---|---|
| Q1 — Calibration ownership | Shared principle across all specialists + Synthesizer as final integrator |
| Q2 — Ratchet | Cold-start: user-reported dual check (confidence ≥7/9, meaning ≥6). Automated ratchet: research-gated Phase 6 |
| Q3 — Architecture level | Synthesizer level only |
| Q4 — A5c activation | Nothing activates at launch; A5c produces documented plan only |

---

## Key research findings (for future reference)

- "Bad-day capability" is the calibration floor, not best-day or aspiration
- Fogg/Locke tension resolved: tiny habit = process goal; challenging aspiration = outcome goal. Both right at different stages
- Tiny Habits achieves high early adherence but only converts to lasting behavior if explicit escalation plan is added
- Confidence check (≥7 novice/restarter, ≥9 failure history) + meaning check (≥6 all users)
- Progression gate: ≥80% adherence over 2 weeks; increase ≤10–20% per step
- Repeat-failer users: 14–21 consecutive successes before first escalation
- Investment layer (stored personal data/rapport) is the primary long-term moat for this product
- Proactive initiation inverts the Hooked model — compliance is about receptivity, not initiation
- AI-novelty curve different from standard app novelty; design for the post-wow utility phase

---

## Files touched this session

- `archive/plans/compliance_curve_decision_2026-06-13.md` — created and fully built out
- `archive/plans/future_phases.md` — compliance curve block marked RESOLVED
- `SESSION.md` — A1 line marked done
- `archive/sessions/2026-06-13 — A1 Compliance Curve Decision.md` — updated to complete status
- `~/.claude/mcp_servers/ask_gpt.py` — o3/o1/o1-mini added, auto-discovery, refresh_models
- `~/.claude/mcp_servers/ask_gemini.py` — auto-discovery, refresh_models, DEFAULT_MODEL fixed to 3.1
- `~/.claude/mcp_servers/ask_claude.py` — opus-4-8/fable added, timeout 600s, refresh_models

---

## File edits still queued (apply in a separate session)

Per file ownership rules, these were not applied in this chat:
- All specialist agent files — add compliance calibration instruction block
- `config/agents/synthesizer.md` — add cross-domain compliance balance instruction
- Exact text for both is in the decision document under "Proposed Agent Instruction Text"
