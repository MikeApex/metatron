# A1 — Compliance Curve Decision Session
*2026-06-13. Parallel track chat. File ownership: decision document + future_phases.md. Do not edit synthesizer.md, coordinator.md, orchestrator.py, routing.yaml, or constitution.md in this session.*

---

## Purpose

Resolve the compliance curve design before Alpha. Governs A5c (preference activation) and is the foundation for all habit-formation and engagement features (Phase 6 / E4).

## Questions to resolve

1. Which agent calibrates new behavior introduction?
2. What is the ratchet mechanism (step up / step back)?
3. Constitution or Synthesizer-level instruction?
4. Which preferences.yaml settings are safe to activate at A5c?

---

## Status

*Complete — 2026-06-18.*

---

## Decisions made

| Q | Decision |
|---|---|
| Q1 — Calibration ownership | Shared principle across specialists; Synthesizer final integrator |
| Q2 — Ratchet | Cold-start: user-reported. Operating mode: research-gated (Phase 6) |
| Q3 — Architecture level | Synthesizer level only (not Constitution) |
| Q4 — A5c activation | Nothing activates at launch; A5c produces documented plan |

## Research conducted

- Research 1 (compliance science): GPT-5.4, Gemini 2.5 Pro, Claude Sonnet 4.6 (adjudicator; Opus timed out)
- Research 2 (app uptake mechanics): same

## Key findings

- "Bad day" capability is the calibration floor, not best-day or aspiration
- Three user types: novice, restarter, repeat-failer — each needs different starting point and framing
- Confidence check: ≥7/10 general, ≥9/10 for failure-history users (AVE risk)
- Streaks are scaffolding, not foundation — need forgiveness mechanics
- Investment layer (stored personal data/rapport) is the primary long-term moat for this product specifically
- Proactive initiation creates a different habit design problem than standard app UX (tool reaches user, not user reaches tool)

## MCP tool updates (same session)

- `ask_gpt.py` — added o3, o1, o1-mini; added auto-discovery via OpenAI models API; `refresh_models` tool; full model ID passthrough in `set_model`
- `ask_gemini.py` — added auto-discovery via Gemini API; `refresh_models` tool; full model ID passthrough
- `ask_claude.py` — added opus-4-8, fable; increased Opus timeout 120s → 600s; added `refresh_models` tool

## Output artifacts

- Decision document: [`archive/plans/compliance_curve_decision_2026-06-13.md`](../plans/compliance_curve_decision_2026-06-13.md)
- `future_phases.md` — compliance curve block marked RESOLVED
- SESSION.md updated (A1 done)
