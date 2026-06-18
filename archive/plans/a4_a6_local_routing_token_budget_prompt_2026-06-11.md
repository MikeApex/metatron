# A4 + A6 — Local Routing Enforcement + Token Budget Logging
*Open this in a new Claude Code session. Roadmap items A4 and A6 (2026-06-10 roadmap), combined because both live in `core/orchestrator.py` — this chat is the sole owner of that file.*
*Parallel-safe: other chats are running simultaneously — see File ownership below.*

---

## Read these first, in order

1. `SESSION.md` — current state
2. `archive/plans/phase5_to_future_roadmap_2026-06-10.md` — **Section 0 (binding privacy ruling)**, items A4 and A6
3. `config/modules/routing.yaml` — current assignments (the cloud fallbacks you are about to remove)
4. `core/orchestrator.py` — session loops, routing dispatch, `register_tools()`
5. `tests/model_ceiling_plan_2026-06-03.md` — the two safety hard-fail suites
6. `tests/testing_framework_notes.md` — token thresholds and implementation guidance

Do not begin until you've read all six.

---

## A4 — Local routing enforcement (blocks A5; the privacy ruling made concrete)

Build:

1. `routing.yaml`: `local_enabled: true`
2. Re-tier to `local: true`: **coordinator, synthesizer, learning_growth, recreation_hobbies, logistics** (joining the already-local diarist, pattern_miner, goals_interviewer, mental_wellbeing, physical_health, work_vocation, relationships, finance)
3. **Fail-closed enforcement in `core/orchestrator.py`:** a `local: true` agent with Ollama unavailable raises a hard error — never falls back to a cloud provider. Remove cloud `fallback_provider`/`fallback_model` entries for sensitive agents; `routing_fallbacks.json` becomes an error log, not a fallback log.
4. **`quick_override` guard:** `complexity: quick` must never override a `local: true` agent to Gemini Flash. Sensitivity beats speed.
5. `research_agent` remains cloud (Gemini Pro), decontextualized directives only — no code change needed this chat beyond leaving it non-local.
6. **Safety hard-fails on qwen3:14b:** run the Mental Wellbeing clinical-flag scenarios (`MUST_SURFACE`, `CLINICAL_CONCERN` must fire in every scenario) and the Finance arithmetic scenarios from `tests/model_ceiling_plan_2026-06-03.md` against the local model. **If either suite fails, stop and report — Alpha does not ship on a local model that misses clinical flags; the escalation path is a larger local model, not a cloud fallback.**

Test:

1. Stop Ollama; run a Mental Wellbeing session. Pass: hard error surfaced, zero outbound cloud API calls. Fail: any cloud call.
2. Run a full pipeline session with Ollama up. Pass: every model call hits `localhost:11434` except an explicitly decontextualized Research Agent dispatch.
3. Issue a `complexity: quick` request through a sensitive agent. Pass: routed local, not to Flash.
4. Both safety hard-fail suites pass on qwen3:14b.

Report safety-suite results in the session archive — they are cited in Phase 5 sign-off check 7.

## A6 — Token budget logging

Build: session-level token accumulation in **all three session paths** — `run_session_anthropic`, `_openai_compat_loop` (covers Ollama), and `run_session_gemini`. Log cumulative input tokens per turn to the session log; warning line when a single turn exceeds 8K input tokens.

Fields: Anthropic → `response.usage.input_tokens`; OpenAI-compat (incl. Ollama) → `response.usage.prompt_tokens`; Gemini → `response.usage_metadata.prompt_token_count`.

Test: run a Coordinator + Mental Wellbeing + Diarist session. Pass: token counts appear in session log; no turn exceeds 15K cumulative input tokens; any 8K–15K turn shows a warning line.

---

## File ownership (parallel chats are live)

- **This chat owns:** `core/orchestrator.py`, `config/modules/routing.yaml`, `tools/subagent.py` (if complexity routing lives there)
- The A2 and A3 chats may each append one entry to `register_tools()` as their last step. Before each of your own edits to `orchestrator.py`, re-read the current file state; do not clobber a freshly added registration line.
- **Do not edit:** `config/agents/*` (A2 chat owns the head-layer files), `tools/baselines.py`, `static/index.html`, `core/server.py`

## Session close

- Create `archive/sessions/2026-06-11 — A4 A6 Local Routing and Token Budget.md` early in the session, per convention.
- SESSION.md update at close: additive only — mark A4 and A6 done; note the safety-suite result explicitly. **A5 (Goals Interview) is unblocked the moment A4's tests pass** — say so in SESSION.md so the user can schedule it.
