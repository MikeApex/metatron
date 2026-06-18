# 2026-06-10 — Roadmap Critical Review and Redraft

## What this session did

1. **Critical review** of `archive/plans/phase5_to_future_roadmap_2026-06-09.md` — 30 findings across internal contradictions, missing prerequisites, sequencing errors, scope gaps, ⚠ planning-note resolutions, and overall-arc issues. Verified against the codebase: testing plans, `routing.yaml`, `preferences.yaml`, `scheduler.yaml`, orchestrator function inventory, tools and agents directories, and memory files.
2. **User rulings** in response to the review:
   - **Sensitive data NEVER through cloud models** — binding, no fallbacks, no deferrals.
   - Circular dependency (E3 vs. Phase 6/7 gates): resolution delegated to Claude Code's judgment.
   - Time Director: retired, requires no testing.
   - "Redraft according to your judgment."
3. **Redraft produced:** `archive/plans/phase5_to_future_roadmap_2026-06-10.md` — supersedes the 2026-06-09 draft in full (original preserved).
4. **Testing plans amended:** `tests/phase5_testing_plan.md` (Time Director removed, local routing mandatory, check 7 rewritten for the privacy ruling, full 12-check sign-off), `tests/phase6_testing_plan.md` (stale 6-month data prerequisite retired), `tests/security_testing_plan.md` (Phase 6.5 → 6A title, prerequisites corrected, dated backlog filename).
5. **SESSION.md updated** to the new roadmap, new Track A numbering, and resolved decisions.

## Key review findings (full list in the chat; headline items)

- **Privacy contradiction at Alpha (biggest):** old plan deferred `local_enabled` to Phase 6/D1 while A3 populated real Tier 1–3 data consumed by the cloud Synthesizer every session — contradicting the 2026-05-14 "Ollama before any real data" decision. → Resolved by ruling: new A4 (local routing enforcement) before the Goals Interview.
- **Circular dependency:** Phase 6 close required E1–E5; E3b potentially gated on a 12-user cohort (post-Phase 7); Phase 7 required Phase 6 close. → Resolved: E3 gates nothing; Stage 2 single-user; Stage 3 automated mode gated on multi-user cohort.
- Stale Phase 5 testing plan (Time Director check, inverted goals-interview prerequisite, incomplete sign-off list) → amended.
- "Seven tracks"/Track G ghost; D1 test depending on D2 keys; `data/wishes/` + `data/baselines/` missing from D2 encryption scope; B2 Tailscale-ACL auth invalidated by D1's Android app (→ shared secret); E1 start ambiguity (→ hard-gated on B2); o3 Pattern Miner test vs. 6A timing (→ retired entirely under the ruling); A6 token logging missing `run_session_gemini`; scheduler cadences missing for most specialists (→ check 3 prerequisite); audit count 13 → 12; "12B" → qwen3:14b; voice/Android design conversation missing (→ E4 item 5); Alpha undefined (→ defined in Section 3); identifiability threshold spike added (F0).

## Major consequences of the privacy ruling (worked into the redraft)

- Head layer (Coordinator + Synthesizer) re-tiered local — it carries Tier 1–3 + specialist outputs every session.
- Learning & Growth, Recreation & Hobbies, Logistics re-tiered local (personal logs; Logistics will consume email/calendar at E1).
- Cloud survives only for decontextualized work: Research Agent, `quick_override` generic lookups, model conference on generic questions.
- Sensitive agents fail closed: Ollama down = hard error; cloud `fallback_provider` entries removed at A4 (current routing.yaml is stale until A4 implements this).
- Safety hard-fails (Mental Wellbeing clinical flags, Finance arithmetic) run on qwen3:14b at A4 — Alpha does not ship on a local model that misses clinical flags.
- Named risk: local model quality is now the dominant Alpha UX factor; D1 evaluates a hardware-enabled upgrade.

## Follow-up (2026-06-11, same chat)

- User confirmed development testing must be unimpeded: clarified in roadmap Section 0 and the privacy memory — the ruling protects real user data only; personas, Reddit diaries/public corpora, and persona-run goals interviews may use cloud models freely. The truncated interview (A3) stays local because it interviews the real user.
- **Parallel chat prompts created** for simultaneous development: launcher at `archive/plans/parallel_chats_index_2026-06-11.md`; seven prompt files (A1, A2, A3, A4+A6, B1, check 10 audits + scheduler cadences, check 12 constitution review), each with read-first list, build/test criteria from the roadmap, and file-ownership rules to prevent cross-chat clobbering (`core/orchestrator.py` → A4+A6 chat; head-layer agent files → A2 chat; specialist agent files frozen post-review; constitution never edited).

## Deferred / open items

- A4 implementation (routing.yaml re-tier + orchestrator fail-closed + quick_override guard) — planned, not built this session.
- Consolidation of duplicate `archive/security/security_backlog.md` into the dated file — assigned to B3.
- `STATUS.md` retirement — still pending (carried in Section 5 of the roadmap).
- Pre-aggregation privacy layer for external Pattern Miner analytics (`research/pm_future.md`) — post-MVP research.
