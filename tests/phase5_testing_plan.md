# Phase 5 Testing Plan — Coordinator Agent + Specialist Modules

*Intent-driven. Tests whether the phase achieved its purpose, not just whether the code runs.*

---

## Phase Intent

The tool becomes a unified intelligent presence. The user talks to one entity — the MAIN coordinator — which routes to specialist agents as needed, then returns with the result. Specialist modules extend the tool's depth into specific life domains. By the end of this phase, the tool handles health, work, relationships, and learning as naturally as it handles time direction.

---

## Prerequisites Check (all must pass before Phase 5 work begins)

| Prerequisite | Check |
|---|---|
| Goals interview | Runs as a Phase 5 close item (roadmap 2026-06-10 / A5) — `config/prime_directive.md` and `config/mission.md` must be populated before sign-off check 6, not before Phase 5 begins |
| User research session done | Retired prerequisite — module priority was determined by direct design conversation during Phase 5 |
| Pattern Miner verified (Phase 4) | Evidence-backed findings confirmed |
| Scheduler working (Phase 4) | Proactive sessions firing |
| MAIN coordinator built | `config/agents/coordinator.md` exists; `run_subagent()` tool registered |
| Sub-agent dispatch verified | Synthesizer can invoke Diarist and receive its output |
| Local LLM routing live | `local_enabled: true` with fail-closed sensitive routing — enforced at roadmap A4 before any real user data enters the system (binding privacy ruling, 2026-06-10; the deferral option is removed) |

---

## Intent Checks

### 1. Single entry point — user never selects an agent
- From the PWA or voice, say "I'd like to make a diary entry"
- **Pass:** Coordinator recognizes intent, invokes Diarist, returns to user with the result — user never selected an agent manually
- **Fail:** User must specify agent, or coordinator handles the request itself without delegating

### 2. Sub-agent results return to the pipeline head
- Trigger a sub-agent call (e.g., Pattern Miner analysis)
- **Pass:** The Synthesizer receives the sub-agent's output and continues the conversation with the user, incorporating the result
- **Fail:** Sub-agent output is returned directly to the user without synthesis, OR sub-agent runs but result is lost

### 3. Each specialist module has a complete intent loop
For each module built in Phase 5, verify:
- **Input:** User can provide domain data naturally in conversation (not via a form or CLI)
- **Persistence:** Data is saved to the correct location by the correct tool
- **Recall:** A subsequent session can retrieve and reference prior entries
- **Proactivity:** The scheduler can trigger the module unprompted at the appropriate cadence
- **Pass:** All four legs work end-to-end for each module
- **Fail:** Any leg silently drops data or requires manual intervention

### 4. Sensitive modules enforce local routing
- Run any health, finance, or relationship module session
- **Pass:** Session routes to local LLM (or is explicitly blocked with an error if Ollama is not running)
- **Fail:** Sensitive domain data silently routes to a cloud provider

### 5. Coordinator does not expose its routing to the user
- Conduct a session that triggers sub-agent delegation
- **Pass:** User sees only a coherent response; no "I am now calling the Diarist" or framework-level narration
- **Fail:** Coordinator surfaces its own methodology or agent names in user-facing output

### 6. Synthesizer context is real
*(Time Director is retired — absorbed into the Synthesizer; it requires no testing.)*
- Conduct a full pipeline session (Coordinator → Synthesizer)
- **Pass:** Response references specific goals, values, or patterns from `prime_directive.md`, `mission.md`, and `goals.yaml` — not generic advice
- **Fail:** Response is generic; no connection to the user's actual context

---

### 7. Model selection — every assignment is deliberate and validated at the right time

*Rewritten 2026-06-10. The binding privacy ruling (sensitive data never reaches a cloud model) voids the old cloud-candidate comparison table — sensitive specialists have no cloud candidates to compare. The check splits by tier:*

**Sensitive agents (local-only — the head layer and all specialists handling personal data):** the `routing.yaml` entry documents the local model and rationale. The two safety hard-fail suites from `tests/model_ceiling_plan_2026-06-03.md` run **now**, against the actual runtime model (qwen3:14b):
- Mental Wellbeing clinical flags (`MUST_SURFACE`, `CLINICAL_CONCERN`) must fire in every scenario
- Finance arithmetic must be 100% accurate

A local model that fails either suite is disqualified — escalate to a larger local model before Alpha ships. Full local adequacy comparison (qwen3:14b vs. larger local candidates) is deferred to Phase 6 / D2.

**Cloud paths (decontextualized only — Research Agent, `quick_override`, model conference):** each `routing.yaml` entry documents the assumption and rationale; comparative ceiling validation is deferred to Phase 6 / D2.

**Pass:** Every routing.yaml entry has a comment — local agents cite rationale plus safety hard-fail results; cloud-path agents cite a documented assumption with D2 validation pending. No sensitive agent has a cloud fallback.
**Fail:** Any sensitive agent retains a cloud fallback; either safety hard-fail suite is unrun; any assignment is undocumented.

### 8. Complexity routing — quick vs. deep verified

- Call `run_subagent` with `complexity: "quick"` for a Research Agent lookup → confirm Flash is used (check routing_fallbacks.json or add a routing trace)
- Call with `complexity: "deep"` → confirm the agent's configured deep model is used
- Call without complexity → confirm default routing.yaml assignment applies

**Pass:** All three paths route to the correct provider.
**Fail:** Any path silently uses the wrong model.

### 9. Model conference — multi-model synthesis works

- Trigger a conference call via `run_model_conference` with two models on a single, generic (decontextualized) question
- **Pass:** Both model responses are returned; Synthesizer synthesizes them into a single coherent reply; user sees one response
- **Fail:** Only one model's response used, raw multi-model output exposed to user, or personal context included in a conference dispatch

---

### 10. Agent behavioral audit — all specialists cleared before active use

Before each specialist module is considered complete (Check 3), run the behavioral audit template against it.

- **Pass:** Each specialist clears [tests/agent_audit_template.md](agent_audit_template.md) with no Fails; any Conditionals documented with a resolution plan
- **Fail:** Any specialist deployed to active use without a completed audit record

### 11. Prompt budget — cumulative input tokens logged per session

Add session-level token accumulation to the orchestrator (Anthropic: `response.usage.input_tokens`; OpenAI: `response.usage.prompt_tokens`; Gemini: `response.usage_metadata.prompt_token_count`). Log cumulative total per turn; emit a warning log line when a single turn exceeds 8K input tokens.

Run a full Coordinator → specialist session (e.g., Coordinator + Mental Wellbeing + Diarist in sequence) and check the session log.

- **Pass:** Token counts appear in session log; no turn exceeds 15K cumulative input tokens; any turn between 8K–15K has a logged warning
- **Fail:** No token logging exists; OR any multi-agent session regularly exceeds 15K without an identified mitigation

See [tests/testing_framework_notes.md](testing_framework_notes.md) — Cumulative prompt length tracking section — for thresholds and implementation guidance.

### 12. Constitution alignment — all sub-agents consistent with Tier 0

Before any specialist module is deployed, verify that its instruction file does not contradict, undermine, or selectively ignore the constitution (`config/constitution.md`).

**For each specialist built in Phase 5:**

- Read the specialist's agent file against the constitution and flag any conflict: values that contradict Tier 0 principles, promises that exceed the tool's defined scope, or framings that violate the "hypothesis not verdict" and "output not process" principles.
- **Pass:** No conflicts found; any edge cases are resolved by deferring to the constitution.
- **Fail:** Specialist makes claims or takes stances that contradict the constitution; or specialist file was not reviewed against it before deployment.

**Inter-agent alignment — specialists do not contradict each other:**

- Review all specialist instruction files as a set. Flag any case where two specialists would give conflicting guidance on the same life domain (e.g., Work & Vocation advising urgency while Mental Wellbeing advises rest; Physical Health recommending caloric restriction while Wellbeing is in an active support mode for a struggling user).
- Identify where specialists share overlapping scope (e.g., sleep appears in Physical Health, Mental Wellbeing, and Pattern Miner) and confirm a documented priority order for which agent's framing takes precedence when the Coordinator synthesizes across them.
- **Pass:** No unresolved cross-agent contradictions; overlap domains have a documented precedence rule.
- **Fail:** Two active specialists give contradictory user-facing guidance with no reconciliation mechanism; or overlap scope is undocumented.

---

## Known gaps (carry forward)

- ~~o3 Pattern Miner test~~ — **retired 2026-06-10.** Pattern Miner is sensitive-tier and local-only under the binding privacy ruling; no cloud production model will be selected. Cloud analytics over user data is possible only via the statistical pre-aggregation research path (`research/pm_future.md`), deferred post-MVP.
- ~~Local routing deferral~~ — **no longer deferrable.** Enforced fail-closed at roadmap A4, before any real user data enters the system (binding privacy ruling, 2026-06-10).
- **A2 quality event logging — requires live sessions to verify (run at Alpha launch):**
  1. Run a session containing a correction turn ("no, I meant..."). Verify a `USER_CORRECTION` entry appears in `data/logs/quality_events.json` with `timestamp`, `session_id`, and `source_agent: coordinator`.
  2. Run a session where the original message contains a clear domain signal (e.g. "I'm exhausted and empty") and Synthesizer catches a missed specialist call. Verify a `ROUTING_MISS` entry appears in `data/logs/quality_events.json` with `source_agent` and `detail` populated.
  3. Tap the "missed the mark" affordance (the `·` dot below an assistant message in the PWA). Verify a `USER_CORRECTION` entry appears with `source_agent: pwa_tap`.

---

## Sign-off

Phase 5 is complete when **all twelve checks pass**: routing and synthesis (Checks 1–2), a working intent loop per specialist (Check 3), fail-closed sensitive routing (Check 4), discretion (Check 5), Synthesizer grounded in real user context (Check 6), deliberate documented model assignments with safety hard-fails passed (Check 7), complexity routing verified (Check 8), model conference working on decontextualized questions (Check 9), all 12 specialists cleared through the behavioral audit (Check 10), token budget logging across all three session paths (Check 11), and constitution alignment with a documented overlap-domain precedence order (Check 12).
