# Handoff — write_persona approval gate [DB-0815-11] build outcome (2026-08-28)

*From the Green/Amber spinoff chat (Fable review, Opus worker). Merged `75a91d6`. VM deploy
owed (Mike) — `tools/` and `config/preferences.yaml` are VM-side.*

## What the tool now does differently

A preference the tool worked out for itself no longer lands silently in the persona file — it
comes back as an approval card, and nothing is written until the user approves it (same
fingerprinted `consume()` path as `write_config`). A preference the user actually stated
writes straight through as before. On **both** paths, a preference that restates a rule
already in force elsewhere is refused, with the reply naming the file and line that holds it —
the 2026-08-18 duplicate scores 0.857 against `config/templates/scheduler.yaml:21` and is
refused by the new check.

- **Toggle:** `proactive.persona.inferred_write_auto_accept` in
  [config/preferences.yaml](../../config/preferences.yaml), default `false` (gate ON);
  per-persona `config/personas/{p}/preferences.yaml` overrides; read-failure leaves the gate
  on; no tool writes the file, so no model can switch off its own gate.
- **Source classification:** required `source` enum (`user_stated` | `inferred`) on the
  schema; absent or unrecognised → `inferred` (the gated side).
- **Redundancy bar:** `rule_audit.NEAR_DUPLICATE` (0.40), imported, not restated. Weaker
  class-collisions still warn-only (a persona layer may legitimately refine a universal rule).
- Tests: `tests/test_persona_write_gate.py` 19/19; confirm-gate, decline-path, false-claim,
  CRM-merge and provenance suites re-run clean.

## Flags for Mike / later sessions (worker flagged, did not decide)

1. **Refusal now applies to user-stated preferences too** — a deliberate reversal of this
   file's old "warn, never block" rule, justified because the refusal names the existing home
   so nothing the user said is lost. Called out in the module docstring. If that is too
   aggressive, the stated path can revert to warn-only in one place.
2. **The bar is the high one (0.40 near-duplicate), not the audit's 0.12 class floor** — one
   constant to change if Mike wants refusal at the lower bar.
3. **`config/agents/synthesizer.md` (Red) says nothing about `source` or the two-step.** The
   schema carries the instruction, so behaviour is correct without it, but the Red
   email-surfacing session may want an agent-file line — a named tool is a specification.

## Item state

`[DB-0815-11]`'s build-owed half is done; its @waiting detection half (one live
`FALSE_ACTION_CLAIM` or a clean week) is unchanged. Confirmation for this build: after deploy,
have the tool infer a preference → expect the approval card; approve → line lands; then ask it
to record "open sessions with the most time-sensitive commitment" → expect refusal naming
`config/templates/scheduler.yaml:21`.
