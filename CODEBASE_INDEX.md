# Codebase Index — Personal AI Life Manager
*Last updated: 2026-09-10 — refreshed after a verification pass found it three months stale
(missing 34 of 51 `tools/*.py` files, 4 of 20 agent files, 9 of 17 `core/*.py` files, and 32+
scripts — essentially the whole hooks/automation layer built since June). Reference this file at
the start of any session to orient without re-reading all files.*

---

## Architecture and Context

| File | Description | Status |
|---|---|---|
| [CLAUDE.md](CLAUDE.md) | Primary developer context — architecture, terminology, design principles, file ownership, change tiers, infrastructure *traps*. Auto-loaded every session. **Slimmed 810 → 507 lines on 2026-08-13**: operational infrastructure detail moved to `docs/INFRASTRUCTURE.md`, module/tool/model-ID recipes to `docs/CONVENTIONS.md`. It holds judgement; the `docs/` files hold reference. | Current |
| [~/.claude/CLAUDE.md](~/.claude/CLAUDE.md) | Global Claude Code instructions — session logging, commit style, file references, numbered lists, terminal command explanations. | Current |
| ~~STATUS.md~~ | **Deleted 2026-08-13.** Retirement had been pending since 2026-06-09, flagged in the roadmap and three sessions. It was worse than stale: its own line 3 told every session to read it while this row said not to — two files in the repo giving opposite instructions about the same file. Recover with `git show HEAD~1:STATUS.md` if ever needed. | Removed |
| [docs/WORKFLOW.md](docs/WORKFLOW.md) | Which dev command to fire, when, and what it costs — decision table, per-command cards, worked example week. Read on demand; not loaded by default. | Current |
| [config/constitution.md](config/constitution.md) | Tier 0 — Tool Constitution. Read-only at runtime. Never edit without explicit user instruction. Loaded into every agent context. | Current |
| [config/prime_directive.md](config/prime_directive.md) | Tier 1 — User terminal values. Blank until Goals Interview runs. Sensitive tier — local only. | Blank |
| [config/mission.md](config/mission.md) | Tier 2 — Current life chapter. Blank until Goals Interview runs. Sensitive tier. | Blank |
| [config/goals.yaml](config/goals.yaml) | Tier 3 — 90-day/weekly/daily goals. Blank until Goals Interview runs. Sensitive tier. | Blank |
| [config/preferences.yaml](config/preferences.yaml) | Proactive action governance — expenditure threshold, social outreach opt-in, bookings opt-in. All null/false until activated post-Goals Interview. | Active |

---

## Runtime Core (`core/`)

| File | Description |
|---|---|
| [core/orchestrator.py](core/orchestrator.py) | Primary runtime brain — config loading, model API calls (4 providers), tool dispatch, REPL, two-pass Coordinator→Synthesizer pipeline (`run_pipeline_session` at line 621), parallel subagent dispatch. The most important file in the repo. |
| [core/persona.py](core/persona.py) | **Persona identity — single source of truth.** `resolve_persona()` (fail-closed), `persona_scope()` (thread-local), `persona_data_dir()` / `persona_config_dir()` / `persona_md()`, name validation. Never read the env var directly. |
| [core/router.py](core/router.py) | Sensitive routing layer — routes sensitive agents to local LLM; logs fallbacks to `data/diagnostics/routing_fallbacks.json`. `local_enabled` flag in `config/modules/routing.yaml`. |
| [core/server.py](core/server.py) | FastAPI server — `/session` endpoint, PWA serving, Web Push subscriptions, audio upload. Default agent: coordinator. |
| [core/scheduler.py](core/scheduler.py) | Proactive initiation daemon — morning brief (07:30), 90-min companion check-ins, EOD Diarist (20:00), weekly Pattern Miner (Sunday 09:00). |
| [core/memory.py](core/memory.py) | FAISS vector memory — all-MiniLM-L6-v2 (384-dim), embeds log/journal entries on write, semantic search via `search_memory`. |
| [core/voice_pipeline.py](core/voice_pipeline.py) | Voice — faster-Whisper STT + Kokoro/edge-tts/Piper TTS; `run_voice_session()` interactive loop. |
| [core/push.py](core/push.py) | Web Push notification module — VAPID keys, subscription storage, notification dispatch to registered devices. |
| [core/trace.py](core/trace.py) | Per-request trace — `RequestTrace`/`AgentRecord`/`ToolCallRecord`, thread-local current-agent tracking, token/retrieval/tool-call recording. Read by `core/spend_guard.py` and `tools/logger.py`; the source `tools/metatron_monitor.py` renders. |
| [core/spend_guard.py](core/spend_guard.py) | Daily runaway-cost protection — per-model rate table, cache-storage accounting, `SpendLimitExceeded`. GCP billing data lags hours behind, so this is the fast-reacting layer. |
| [core/actions.py](core/actions.py) | Classifies which tool calls in a trace are user-visible "actions" vs. reads; `action_provenance_block()` feeds `tools/turn_referent.py`'s "what did I just do" context. |
| [core/rule_classes.py](core/rule_classes.py) | Shared `Rule` dataclass and near-duplicate threshold used by `tools/persona.py` (writing) and `tools/rule_audit.py` (auditing) — one home so the two never compare against different definitions of "duplicate." |
| [core/auth.py](core/auth.py) | Bearer-token auth for the server's `/session` endpoint. Read by `core/server.py`, `core/remote_client.py`, `tools/metatron_monitor.py` (dashboard auth), `scripts/sync_dev_backlog.py`, `scripts/mint_token.py`. |
| [core/attachments.py](core/attachments.py) | User-attached photo/document handling — storage under `persona_data_dir()`, referenced across turns. |
| [core/background.py](core/background.py) | Deferred/async write helper used by `tools/diarist.py` and `tools/logger.py` so a journal or log write doesn't block the turn it was requested on. |
| [core/remote_client.py](core/remote_client.py) | Client for calling the deployed VM server from a local process — used by `core/scheduler.py` and `core/orchestrator.py`. |
| [core/translate.py](core/translate.py) | Language handling — read by `core/server.py` and `core/orchestrator.py`. |

---

## Agent Configuration Files (`config/agents/`)

Each file is a Markdown instruction file loaded at runtime by the orchestrator. These files *are* the product — behavior changes require editing them, not code changes.

**Every agent's enhancement backlog lives in [AGENT_ENHANCEMENTS.md](AGENT_ENHANCEMENTS.md) at the
project root — the only copy** (moved out of these files 2026-08-27 so planned upgrades stop
shipping to the model in every prompt). The Synthesizer's episodic conduct lives in
[config/modules/synthesizer_scheduled_sessions.md](config/modules/synthesizer_scheduled_sessions.md)
and [config/modules/synthesizer_onboarding.md](config/modules/synthesizer_onboarding.md), injected
by `core/orchestrator.py → _synth_conditional_sections()` only on the turns that trigger them.

| File | Role | Notes |
|---|---|---|
| [config/agents/coordinator.md](config/agents/coordinator.md) | Ears — holds conversation context, resolves intent, routes to specialists with contextualized directives. Never speaks to user directly. | Active |
| [config/agents/synthesizer.md](config/agents/synthesizer.md) | Brain + Mouth — receives context package from Coordinator + specialist outputs; integrates; delivers user-facing response. Time Director prioritization built in. | Active |
| [config/agents/diarist.md](config/agents/diarist.md) | Ambient presence — logging, journaling, life archive (movies, books, experiences, ideas). Write-only output to disk. | Active |
| [config/agents/pattern_miner.md](config/agents/pattern_miner.md) | Insight extraction at 7/30/90/365-day scales. Evidence-first format. Runs weekly via scheduler. | Active |
| [config/agents/goals_interviewer.md](config/agents/goals_interviewer.md) | Structured interview — populates prime_directive, mission, goals. Multi-phase dynamic flow. Run with `--provider ollama`. | Active |
| [config/agents/goals_interview_reference.md](config/agents/goals_interview_reference.md) | Output schema and domain list extracted from goals_interviewer.md. Reference only. | Reference |
| [config/agents/mental_wellbeing.md](config/agents/mental_wellbeing.md) | Emotional health, stress, resilience, Big Five profiling, clinical flag protocol (MUST_SURFACE, CLINICAL_CONCERN). | Active |
| [config/agents/physical_health.md](config/agents/physical_health.md) | Diet, sleep, exercise, biometrics, medication, vice logging. Sensitive tier. | Active |
| [config/agents/work_vocation.md](config/agents/work_vocation.md) | Work for income and meaning — projects, career, craft, flow state, vocation identity. | Active |
| [config/agents/relationships.md](config/agents/relationships.md) | People — conversations, conflicts, CRM protocol, CONTACT_INCOMPLETE flag, RESEARCH_AVAILABLE routing. | Active |
| [config/agents/learning_growth.md](config/agents/learning_growth.md) | Books, courses, skills, intellectual life, practice tracking. | Active |
| [config/agents/finance.md](config/agents/finance.md) | Expenses, budget, investments, tax. Sensitive tier. No financial advice at personal-use phase. | Active |
| [config/agents/recreation_hobbies.md](config/agents/recreation_hobbies.md) | Creative pursuits, play, entertainment, rest, service/volunteering. | Active |
| [config/agents/research_agent.md](config/agents/research_agent.md) | Outward-facing — topic monitoring, synthesis. Decontextualized; cloud-routable. | Active |
| [config/agents/logistics.md](config/agents/logistics.md) | Practical coordination — travel, shopping, calendar-adjacent tasks. CalDAV integration live. | Active |
| [config/agents/accountability_judge.md](config/agents/accountability_judge.md) | Bare Flash-Lite call, one leftover intention at a time — did it happen? Fires nightly (`daily_accountability_judgment_gate`, 05:45) via `tools/accountability.run_judgment_gate`. No tool grant (bare dispatch). | Active |
| [config/agents/crm_sweep.md](config/agents/crm_sweep.md) | Reads one closed day of conversation + journal, proposes CRM updates to an append-only ledger — never writes the CRM directly. Fires nightly (05:50) via `tools/crm_sweep.sweep`; off by default per persona. No tool grant. | Active |
| [config/agents/intake_extractor.md](config/agents/intake_extractor.md) | Classifies one inbound message (kind, category, confidence) for the intake pipeline (`tools/intake.py`). **Gated off** — `allowed_tools: []`, held pending an eval pass on the model that actually serves it. | Built, gated |
| [config/agents/tone_profiler.md](config/agents/tone_profiler.md) | Reads a correspondence sample with one contact and describes tone/register for `get_tone_shape`. No tool grant (bare dispatch). | Active |
| [config/agents/time_director.md](config/agents/time_director.md) | **Retired, but still a live file — do not treat as gone.** Self-labelled "RETIRED" at the top, prioritization intelligence absorbed into `synthesizer.md` 2026-05-28, snapshot at `archive/plans/time_director_retired_2026-05-28.md`. Has no entry in `routing.yaml`/`routing_cloud.yaml`, so it cannot be dispatched through the normal agent path — but the name is still referenced in three places in `core/orchestrator.py` (confidentiality list, unavailable-consequence copy, agent-name normalizer) and is the **default `--agent` value in `core/voice_pipeline.py`'s standalone CLI entry point**. Not reachable from any live server path today; worth a cleanup pass on the stale default. (Corrected 2026-09-10 — this row previously said the file was archived-and-gone, which is wrong.) | Retired, file live |

---

## Module Configuration (`config/modules/`)

| File | Description |
|---|---|
| [config/modules/routing.yaml](config/modules/routing.yaml) | Model routing + per-agent `allowed_tools` whitelist, **local** path (`DEPLOYMENT_MODE` unset or `local`). `local_enabled: true` on this Mac; Ollama down = hard fail-closed error, never a cloud fallback for sensitive agents. |
| [config/modules/routing_cloud.yaml](config/modules/routing_cloud.yaml) | Same shape, **cloud** path (`DEPLOYMENT_MODE=cloud`) — used on the VM. All agents route to Vertex Gemini 3.8 Flash / 3.5 Flash-Lite. `core/router.py` picks between the two files by env var; kept in parity by convention, not by code — every grant comment in one references the other. |
| [config/templates/scheduler.yaml](config/templates/scheduler.yaml) | The actual scheduler-config file (the row that used to say `config/modules/scheduler.yaml` pointed at a path that doesn't exist). Provisioning source, copied once per persona by `scripts/new_persona.sh` — a later edit here does NOT reach existing personas, which is why `core/scheduler.py`'s `_DEFAULT_JOBS` dict exists for silent infrastructure jobs that must reach every persona at deploy. |
| [config/modules/calendar_reconcile.yaml](config/modules/calendar_reconcile.yaml) | Calibration knobs for `tools/calendar_reconcile.py`'s "passed events with nothing in the record" check. |
| [config/modules/knowledge_domains.yaml](config/modules/knowledge_domains.yaml) | The one place wisdom-store subjects (`tools/wisdom.py`) couple to the agent roster that reads them — checked by `scripts/check_knowledge_domains.py`. |
| [config/modules/regional_transit.yaml](config/modules/regional_transit.yaml) | Shared library: which cities have a dedicated regional transit-status tool (`tools/regional_transit.py`), infrastructure knowledge not persona-scoped. |
| [config/modules/spend_guard.yaml](config/modules/spend_guard.yaml) | Per-model pricing table and daily runaway-cost thresholds read by `core/spend_guard.py`. |
| [config/modules/synthesizer_onboarding.md](config/modules/synthesizer_onboarding.md) | Domain-baseline interview conduct for the Synthesizer — injected by `core/orchestrator.py → _synth_conditional_sections()` only on onboarding turns. |
| [config/modules/synthesizer_scheduled_sessions.md](config/modules/synthesizer_scheduled_sessions.md) | Conduct for the fixed-point scheduled sessions (morning brief, evening close) — same injection mechanism, injected only on those turns. |
| [config/templates/caldav.yaml](config/templates/caldav.yaml) | CalDAV config — the single home. New personas are provisioned from it; live config is per-persona at `config/personas/{p}/caldav.yaml` (gitignored, VM-owned). **`config/modules/caldav.yaml` is dead** — gitignored, Mac-local, read by nothing, and already drifted; do not edit it. |
| [config/templates/email.yaml](config/templates/email.yaml) | Email defaults for every persona (`check_interval_minutes`). Provisioning source *and* runtime fallback — `tools/mail.py` reads it, because a template alone would reach only personas created after a change. **`config/modules/email.yaml` is also dead** (found 2026-09-10, same pattern as `modules/caldav.yaml`) — `tools/mail.py`'s own docstring says so explicitly ("not `config/modules/email.yaml`, which nothing reads"); it has drifted from the template it duplicates. Do not edit it. |

---

## Templates and Research Archives

| File | Description |
|---|---|
| [config/templates/daily_checkin.md](config/templates/daily_checkin.md) | 4-phase daily check-in template — mood/energy extraction, focus/blockers, log schema. |
| [config/research/goals_interview.md](config/research/goals_interview.md) | Research archive — Motivational Interviewing (MI) methodology that informed the Goals Interviewer design. Reference only, not prescriptive. |

---

## Scripts (`scripts/`)

**Wired into `.claude/settings.json` as hooks** — run automatically by Claude Code, not by the
runtime, and not invoked from the command line in normal use:

| Script | Fires on | Purpose |
|---|---|---|
| [scripts/hook_deny_lift.py](scripts/hook_deny_lift.py) | PreToolUse (Write\|Edit) | Allows Write/Edit on Denied-tier paths only while a plan-scoped work order is in force |
| [scripts/hook_context_gate.py](scripts/hook_context_gate.py) | PreToolUse (Write\|Edit) | Per-file briefing (tier, governing rule, recent commits, log history) plus warn-only checks that `SESSION.md`/`ROADMAP.md` were read this session — the mechanism behind § Mandatory Pre-Edit Context Check in `CLAUDE.md` |
| [scripts/hook_agent_spawn.py](scripts/hook_agent_spawn.py) | PreToolUse (Agent) | Records worker spawn — narration that replaced the ~800 approval prompts removed when subagent tool use stopped requiring confirmation |
| [scripts/hook_commit_guard.py](scripts/hook_commit_guard.py) | PreToolUse (Bash) + PostToolUse (Write\|Edit) | Blocks a commit that would sweep up another session's uncommitted work in a shared tree (the 2026-08-09 incident: session A's `routing*.yaml` edit swept into session B's commit) |
| [scripts/hook_agent_tools.py](scripts/hook_agent_tools.py) | PostToolUse (Write\|Edit) | Runs the agent-tool guard (`check_agent_tools.py`'s checks) whenever an agent file or routing grant changes |
| [scripts/hook_session_tokens.py](scripts/hook_session_tokens.py) | Stop | Reports the session's real billed token total |
| [scripts/hook_subagent_gate.py](scripts/hook_subagent_gate.py) | SubagentStop | A worker may not report done until `qa_sweep.sh` passes |

**Checks / linters** — read-only, run manually or as part of `/backlog`, `/archive`, or a hook above:

| Script | Purpose |
|---|---|
| [scripts/check_personas.py](scripts/check_personas.py) | Drift between identity files, config dirs, and data dirs. Non-zero exit on real breakage. |
| [scripts/check_agent_tools.py](scripts/check_agent_tools.py) | Finds tools an agent file names that it cannot actually call — named-but-not-built, named-but-not-granted, granted-but-never-named. Also scans persona files. |
| [scripts/check_claude_md_claims.py](scripts/check_claude_md_claims.py) | Tests the claims `CLAUDE.md` / `.claude/settings.json` make about themselves (ceilings, permission-rule liveness) — the authority for the `CEILINGS` dict referenced throughout the docs. |
| [scripts/check_confirm_executors.py](scripts/check_confirm_executors.py) | Every confirmation-gated tool call can actually be carried out — checks the request-registry and executor-registry agree. |
| [scripts/check_deploy_lock.sh](scripts/check_deploy_lock.sh) | Asserts the deploy lock directory is shared across worktrees, not computed per-worktree. |
| [scripts/check_knowledge_domains.py](scripts/check_knowledge_domains.py) | Checks `config/modules/knowledge_domains.yaml` against the agent roster and the wisdom-store subjects it couples. |
| [scripts/check_model_availability.py](scripts/check_model_availability.py) | Live-calls each routed Gemini model — catalogue listing is not availability; confirms before wiring a model in or writing one off. Runs weekly. |
| [scripts/check_rule_overlap.py](scripts/check_rule_overlap.py) | Reports behavioural rules stated in more than one place — enforces "one home per rule class." |
| [scripts/check_apk_sync.sh](scripts/check_apk_sync.sh) | Fails loudly if the built APK's bundled `index.html` has drifted from `static/index.html`. |
| [scripts/audit_context_load.py](scripts/audit_context_load.py) | Audits what a Claude Code session actually loaded into context, with evidence. |

**Backlog / docs machinery:**

| Script | Purpose |
|---|---|
| [scripts/sync_dev_backlog.py](scripts/sync_dev_backlog.py) | Pulls change requests and runtime signals from the VM into `DEV_BACKLOG.md`. Runs every session (SessionStart hook + `/metatron-code`'s first step); costs no context. |
| [scripts/backlog_close_scan.py](scripts/backlog_close_scan.py) | Surfaces backlog items this session may have closed, for `/archive`'s close-and-file step. |
| [scripts/build_project_log.py](scripts/build_project_log.py) | Generates `archive/PROJECT_LOG.md` from fragments in `archive/log/` — the log itself is never hand-edited. |

**Persona / worktree provisioning:**

| Script | Purpose |
|---|---|
| [scripts/new_persona.sh](scripts/new_persona.sh) | Provision a persona from `config/templates/`. Validates the name with the same rule the resolver enforces. |
| [scripts/new_worktree.sh](scripts/new_worktree.sh) | Creates an isolated git worktree for parallel work — two windows editing the same tree collide at line granularity. |
| [scripts/rm_worktree.sh](scripts/rm_worktree.sh) | Tears down a worktree created by `new_worktree.sh`. |

**Deploy / VM lifecycle:**

| Script | Purpose |
|---|---|
| [scripts/metatron-pause.sh](scripts/metatron-pause.sh) | Stop `metatron-vm` (cost control while not developing). |
| [scripts/metatron-resume.sh](scripts/metatron-resume.sh) | Start `metatron-vm`, wait for health check, recover billing if disabled. |
| [scripts/metatron-billing-override.sh](scripts/metatron-billing-override.sh) | Set a manual override so `stop-billing` skips disabling billing. |
| [scripts/metatron-vm-override.sh](scripts/metatron-vm-override.sh) | Tells the stop-vm Cloud Function to leave `metatron-vm` running for N hours even over the soft spend cap. |
| [scripts/metatron-backup.sh](scripts/metatron-backup.sh) | Pulls live data off `metatron-vm` onto the MacBook — nothing on the VM is captured by git. |
| [scripts/probe_deploy.sh](scripts/probe_deploy.sh) | Exercises `deploy.sh`'s mutual-exclusion lock without actually deploying. |
| [scripts/vm_add_swap.sh](scripts/vm_add_swap.sh) | Gives the VM a swapfile. |
| [scripts/vm_memory_watch.py](scripts/vm_memory_watch.py) | Alerts when the VM is close to an OOM kill, or has had one. |
| [scripts/qa_sweep.sh](scripts/qa_sweep.sh) | The verification leg as a script — chains checks that used to be fired only by memory, zero model tokens. Gate for `hook_subagent_gate.py`. |

**One-off / migration (run once, kept for reference):**

| Script | Purpose |
|---|---|
| [scripts/migrate_health_notes.py](scripts/migrate_health_notes.py) | Moved `health_notes` out of `profile.yaml` into the wisdom store. |
| [scripts/migrate_wisdom_schema.py](scripts/migrate_wisdom_schema.py) | Migrated `wisdom.json` to the domain/provenance schema. |
| [scripts/import_vcard_contacts.py](scripts/import_vcard_contacts.py) | Bulk-import contacts from a vCard (.vcf) export into the local CRM. |
| [scripts/google_contacts_authorize.py](scripts/google_contacts_authorize.py) | One-time OAuth consent for `tools/google_contacts.py`; the stored token is reused/auto-refreshed after. |
| [scripts/mint_token.py](scripts/mint_token.py) | Prints a short-lived bearer token for the server. Standard library only. |
| [scripts/worker_ledger.py](scripts/worker_ledger.py) | Measures what a `/backlog verify`/`attack` worker actually costs, rather than estimating. |
| [scripts/vertex_cache_admin.py](scripts/vertex_cache_admin.py) | Lists and deletes Vertex context caches. |
| [scripts/vertex_cost_reconcile.py](scripts/vertex_cost_reconcile.py) | Reconciles the BigQuery billing export's cache-cost questions against `spend_guard`. |

---

## Personas (`config/personas/`)

A persona is a user — there is no test-versus-real tier. Every session belongs to exactly one persona and is treated as real. Identity resolves fail-closed through `core/persona.py`; `--persona` is required on both the server and the scheduler. See the Personas section in [CLAUDE.md](CLAUDE.md) for the full layout and rules.

`mike` is the live user. The rest are drawn from published diaries, memoirs, and biographies, or are synthetic, and are used for agent design validation — but they run through exactly the same machinery.

Provision with `./scripts/new_persona.sh <name>`; check consistency with `python scripts/check_personas.py`.

| Persona | Source | Config |
|---|---|---|
| [config/personas/aurelius.md](config/personas/aurelius.md) | Marcus Aurelius | Persona file only |
| [config/personas/nin.md](config/personas/nin.md) | Anaïs Nin | Persona file only |
| [config/personas/pepys.md](config/personas/pepys.md) | Samuel Pepys | Persona file only |
| [config/personas/arthur_brooks.md](config/personas/arthur_brooks.md) | Arthur Brooks | Persona file + goals.yaml |
| [config/personas/cal_newport.md](config/personas/cal_newport.md) | Cal Newport | Persona file + goals.yaml |
| [config/personas/danny_park.md](config/personas/danny_park.md) | Danny Park (synthetic) | Persona file + goals.yaml |
| [config/personas/maya_torres.md](config/personas/maya_torres.md) | Maya Torres (synthetic) | Persona file + goals.yaml |
| [config/personas/oliver_burkeman.md](config/personas/oliver_burkeman.md) | Oliver Burkeman | Persona file + goals.yaml |
| [config/personas/sarah_chen.md](config/personas/sarah_chen.md) | Sarah Chen (synthetic) | Persona file + goals.yaml |
| [config/personas/ryan_holiday.md](config/personas/ryan_holiday.md) | Ryan Holiday | Full Tier 1-3: prime_directive, mission, goals.yaml in `config/personas/ryan_holiday/` |
| [config/personas/mike.md](config/personas/mike.md) | Real user dev persona | goals.yaml in `config/personas/mike/`; used for development testing against real-user context |

---

## Tools (`tools/`)

Each file defines Python functions + JSON schemas. Most are registered in `core/orchestrator.py` →
`register_tools()` and dispatched as LLM-callable schemas, gated per-agent by `allowed_tools` in
`config/modules/routing.yaml`. **A second group is not schema-registered** — called directly by
`core/orchestrator.py` for context-block assembly, by `core/scheduler.py` as function jobs, or by
another tool module one layer removed from the registry. Both groups are real dependencies; only
the first is what an LLM can invoke mid-conversation. 51 files as of 2026-09-10 (up from the ~17
this table covered before this refresh).

### Registered as LLM-callable tool schemas

| File | Tools provided |
|---|---|
| [tools/logger.py](tools/logger.py) | `write_log`, `read_log`, `write_quality_event` — daily JSON logs at `data/logs/YYYY-MM-DD.json`; threading lock for parallel writes |
| [tools/goals.py](tools/goals.py) | `read_goals`, `write_goals`, `update_goal` — reads/writes `config/goals.yaml` |
| [tools/config_writer.py](tools/config_writer.py) | `write_config` — writes Tier 1-3 config files; restricted to Goals Interviewer and Synthesizer/Logistics |
| [tools/diarist.py](tools/diarist.py) | `write_journal`, `read_journal`, `write_archive`, `read_archive` — free-form journal entries and life archive (movies, books, experiences) |
| [tools/wisdom.py](tools/wisdom.py) | `read_wisdom`, `write_wisdom`, `find_duplicate_wisdom`, `merge_wisdom_entries` — Life Wisdom Depot; seasonal patterns, personal quirks, recurring events, domain/provenance schema |
| [tools/memory_tool.py](tools/memory_tool.py) | `search_memory` — FAISS semantic search over embedded log/journal history |
| [tools/pattern_miner.py](tools/pattern_miner.py) | `get_log_window`, `write_insight_report`, `read_recent_insights` — Pattern Miner's window read and report write |
| [tools/baselines.py](tools/baselines.py) | `write_baseline_period`, `read_baseline_periods`, `write_retrospective`, `get_baseline_context`, `create_semantic_anchor`, `write_aspirational_baseline`, `shuffled_null_score`, `score_against_anchors` — comparison baselines for Pattern Miner |
| [tools/context_tracker.py](tools/context_tracker.py) | `write_context_tracker` (registered) — persistent session context (open threads, recent signals, flags); `read_context_tracker` is also called directly by the orchestrator for context assembly |
| [tools/subagent.py](tools/subagent.py) | `run_subagent`, `run_model_conference` — spawns sub-orchestrator sessions; multi-model conference calls |
| [tools/agent_config.py](tools/agent_config.py) | `write_agent_config`, `read_agent_config` — per-specialist persistent state (profile notes, preferences); scoped by agent_name |
| [tools/wishes.py](tools/wishes.py) | `write_wishes`, `read_wishes`, `generate_emergency_card` — Emergency & Legacy store; Synthesizer sole writer |
| [tools/crm.py](tools/crm.py) | `write_contact`, `read_contact`, `list_contacts`, `log_interaction`, `search_contacts`, `merge_contacts`, `unmerge_contacts` — Relationships CRM; also registers a `tools/confirm.py` executor for merge confirmations |
| [tools/caldav.py](tools/caldav.py) | `read_calendar`, `write_calendar_event`, `update_calendar_event`, `delete_calendar_event` — CalDAV calendar integration |
| [tools/profile.py](tools/profile.py) | `write_profile`, `read_profile` — cross-agent profile fields (language, third-party-correction guard) |
| [tools/persona.py](tools/persona.py) | `write_persona` — appends to `config/personas/{p}.md`; imports `core/rule_classes.py`'s duplicate threshold and `tools/rule_audit.py`'s corpus |
| [tools/tone.py](tools/tone.py) | `get_tone_shape` — correspondence-derived tone/register for one contact, backed by `tools/untrusted.py` sanitization |
| [tools/scheduling.py](tools/scheduling.py) | `check_calendar_conflicts` — title-similarity + time-overlap + attendee-overlap conflict detection |
| [tools/ambient.py](tools/ambient.py) | `get_weather`, `get_environmental_snapshot` (registered); `current_clock_line`/`refresh_ambient_context` called directly for context assembly and the `ambient_refresh` scheduled job |
| [tools/pollen.py](tools/pollen.py) | `get_pollen_forecast` — Research agent's decontextualized pollen leg |
| [tools/tfl_status.py](tools/tfl_status.py) | `get_tfl_status` — London transit line status |
| [tools/flights.py](tools/flights.py) | `get_flight_status` |
| [tools/routing.py](tools/routing.py) | `get_travel_time` — Google travel-time endpoint |
| [tools/regional_transit.py](tools/regional_transit.py) | `get_regional_transit_info` |
| [tools/places.py](tools/places.py) | `find_places`, `geocode_place_name` |
| [tools/schedule.py](tools/schedule.py) | `write_schedule`, `list_schedules`, `delete_schedule` — agent-written recurring/one-off jobs, kept in a separate file from the user's `scheduler.yaml` |
| [tools/obligations.py](tools/obligations.py) | `open_obligation`, `close_obligation`, `reopen_obligation`, `list_obligations` |
| [tools/web.py](tools/web.py) | `fetch_url`, `fetch_rendered` — SSRF-guarded fetch + headless-rendered fetch with memory-pressure deprioritization |
| [tools/contacts_import.py](tools/contacts_import.py) | `import_contacts_file`, `import_google_contacts` — vCard/CSV import and Google Contacts import; calls `tools/google_contacts.py` |
| [tools/mail.py](tools/mail.py) | `read_email`, `send_email`, `send_calendar_invite`, `search_correspondence` — IMAP read-only + confirmation-gated send |
| [tools/intake.py](tools/intake.py) | `read_intake_queue`, `teach_intake` (registered); `sweep`/`digest_job` fire as scheduled function jobs; orchestrates `intake_email.py`/`intake_extract.py`/`intake_forward.py` as its adapter/pipeline layer |
| [tools/crm_sweep.py](tools/crm_sweep.py) | `apply_crm_proposals` (registered); `sweep()` itself fires as a nightly scheduled function job, never as an LLM tool call — see § Scheduled jobs |
| [tools/horizon.py](tools/horizon.py) | `record_horizon_item` (registered — Logistics only); `context_block`/`week_block`/`review_block`/`mark_engaged` called directly for context assembly |

### Not schema-registered — called directly, or one layer removed via another tool module

| File | Role |
|---|---|
| [tools/confirm.py](tools/confirm.py) | Confirmation-gate state machine (request/approve/decline/execute) — called directly by `core/server.py` and `core/orchestrator.py`; `tools/crm.py` and `tools/escalation.py` register executors with it |
| [tools/location.py](tools/location.py) | Geofence zones, current-zone tracking, transition history — called directly by `core/server.py`, `core/orchestrator.py`, `tools/confirm.py`; read by `scripts/check_confirm_executors.py` |
| [tools/escalation.py](tools/escalation.py) | Clinical-escalation inbox — `raise_escalation`/`review_clinical_escalations` fires weekly as a scheduled function job (`weekly_clinical_review`); reviewed via `tools/confirm.py` and read by `tools/context_tracker.py` |
| [tools/calendar_audit.py](tools/calendar_audit.py) | `audit_calendar_duplicates` — daily scheduled function job (`daily_calendar_dedup_audit`) |
| [tools/calendar_reconcile.py](tools/calendar_reconcile.py) | `reconcile_check` — daily scheduled function job; `context_block()` also pulled directly by `core/orchestrator.py` |
| [tools/rule_audit.py](tools/rule_audit.py) | `audit_rules` — daily scheduled function job (`daily_rule_audit`); its `NEAR_DUPLICATE` threshold is imported by `tools/persona.py` |
| [tools/travel_watch.py](tools/travel_watch.py) | `travel_check` — daily scheduled function job (06:45); detects delays/cancellations against calendar-derived flight numbers and TfL lines, notifies only on an actual disruption |
| [tools/turn_referent.py](tools/turn_referent.py) | `context_block()` called directly by `core/orchestrator.py` for "what did I just do" context; imports `core/actions.py` |
| [tools/untrusted.py](tools/untrusted.py) | Shared sanitizer (`wrap_untrusted`, `contains_injection_markers`) imported by 9 other tool modules — not itself a tool |
| [tools/google_contacts.py](tools/google_contacts.py) | `read_google_contacts` — called by `tools/contacts_import.py` and the one-time OAuth script `scripts/google_contacts_authorize.py` |
| [tools/intake_email.py](tools/intake_email.py) | Gmail adapter (`fetch`) registered into `tools/intake.py`'s pipeline |
| [tools/intake_extract.py](tools/intake_extract.py) | Per-message extraction, calls `config/agents/intake_extractor.md` — called by `tools/intake.py` |
| [tools/intake_forward.py](tools/intake_forward.py) | Forwarded-mail unwrapping (SPF/DKIM-aware) — called by `tools/intake_email.py` |
| [tools/analytics.py](tools/analytics.py) | `rollup_day`/`rollup_yesterday`/`report` — A9 product analytics; `rollup_yesterday` fires as a daily scheduled function job |
| [tools/accountability.py](tools/accountability.py) | `run_judgment_gate` — nightly scheduled function job backing `config/agents/accountability_judge.md`; also reads calendar/obligation records to resolve intentions |
| [tools/turn_context.py](tools/turn_context.py) | Per-turn scope tracking (`turn_scope`, `adopt`, `new_trigger_since`) — imported directly by `core/orchestrator.py` |
| [tools/metatron_monitor.py](tools/metatron_monitor.py) | Standalone CLI dashboard (`python tools/metatron_monitor.py`) — not tool-registered; imports `core/auth.py` for shared auth-header logic |
| [tools/kokoro/speak.py](tools/kokoro/speak.py) | Kokoro TTS wrapper — primary TTS engine (af_heart voice) |
| [tools/kokoro/audition.py](tools/kokoro/audition.py) | Voice audition script — test/compare Kokoro voice options |
| [tools/gen_icon.py](tools/gen_icon.py) | **Orphaned.** One-off PWA icon generator, run manually once. Zero references anywhere outside `archive/` history — no caller in `core/`, `tools/`, or `scripts/`. |
| `~/.claude/tools/archive_chats.py` | Bulk JSONL export → `archive/transcripts/`. **Lives outside the repo** and auto-detects the project root. The in-repo copy at `tools/archive_chats.py` was a stale ancestor and was deleted 2026-08-03. Invoked by `/archive`. |

---

## Planning Documents (`archive/plans/`)

### Active — read these to understand current state

| File | Description |
|---|---|
| [archive/plans/revision_3_1_snapshot.md](archive/plans/revision_3_1_snapshot.md) | Full project plan Rev 3.1 — architecture, phases 0-7, design principles. Background reference. Some language is stale (see roadmap Section 5). |
| [archive/plans/future_phases.md](archive/plans/future_phases.md) | Parked features — environmental monitoring, Wishes full build, addiction, cognitive profiling, Observer Agent, User Engagement/compliance. Includes Self-Improvement Protocol design (Stages 1-3). |
| [archive/plans/phase5_to_future_roadmap_2026-06-09.md](archive/plans/phase5_to_future_roadmap_2026-06-09.md) | **Primary roadmap document** — execution tracks A–F with embedded test criteria, phase gates, agent backlogs. The plan to execute from Phase 5 close through Phase 7. Start here for forward planning. |
| [archive/plans/phase5_agent_reviews_continuation_2026-06-04.md](archive/plans/phase5_agent_reviews_continuation_2026-06-04.md) | Phase 5 state as of 2026-06-04 — agent review status, built items, open design questions. Most recent phase continuation prompt. |

### Historical — reference only

| File | Description |
|---|---|
| [archive/plans/phase5_prompt_2026-05-26.md](archive/plans/phase5_prompt_2026-05-26.md) | Original Phase 5 deliverable plan. Superseded by phase5_to_future_roadmap for items D6+. |
| [archive/plans/phase5_agent_reviews_prompt_2026-06-02.md](archive/plans/phase5_agent_reviews_prompt_2026-06-02.md) | Phase 5 agent review session opener (June 2). |
| [archive/plans/phase5_agent_review_prompt_2026-05-27.md](archive/plans/phase5_agent_review_prompt_2026-05-27.md) | Earlier Phase 5 agent review prompt. |
| [archive/plans/phase5_coordinator_synthesizer_prompt_2026-05-28.md](archive/plans/phase5_coordinator_synthesizer_prompt_2026-05-28.md) | Coordinator-Synthesizer architecture design session prompt. |
| [archive/plans/coordinator_backup_2026-05-28.md](archive/plans/coordinator_backup_2026-05-28.md) | Coordinator.md backup before Coordinator-Synthesizer redesign. |
| [archive/plans/parallel_subagent_calls_prompt.md](archive/plans/parallel_subagent_calls_prompt.md) | Parallel subagent dispatch implementation prompt (now done). |
| [archive/plans/crm_tool_prompt.md](archive/plans/crm_tool_prompt.md) | CRM tool implementation prompt (now done). |
| [archive/plans/model_cost_analysis_2026-05-19.md](archive/plans/model_cost_analysis_2026-05-19.md) | Preliminary model cost analysis — intentionally incomplete; full pass in Phase 6 / D2. |
| [archive/plans/phase4_snapshot.md](archive/plans/phase4_snapshot.md) | Phase 4 plan archive. |
| [archive/plans/time_director_retired_2026-05-28.md](archive/plans/time_director_retired_2026-05-28.md) | Retired Time Director agent file. |
| [archive/plans/revision_3_1_snapshot.md](archive/plans/revision_3_1_snapshot.md) | Rev 3.1 full plan (already listed above under Active). |
| [archive/plans/revision_1_original.md](archive/plans/revision_1_original.md) | Original project plan (Rev 1). Historical only. |
| [archive/plans/PLAN_revisions_1_2.md](archive/plans/PLAN_revisions_1_2.md) | Revisions 1 and 2 combined. Historical only. |
| [archive/plans/plan_review_prompt_2026-06-09.md](archive/plans/plan_review_prompt_2026-06-09.md) | Prompt that generated the Phase 5→Future roadmap (this session). |

---

## Security Documents (`archive/security/`)

| File | Description | Status |
|---|---|---|
| [archive/security/threat_model_2026-06-04.md](archive/security/threat_model_2026-06-04.md) | System-specific threat model — OWASP LLM Top 10 + MITRE ATLAS mapped to this system's attack surface. Generated 2026-06-04. Phase 6A / D1 ✓ | Done |
| [archive/security/security_backlog_2026-06-04.md](archive/security/security_backlog_2026-06-04.md) | Consolidated security backlog — all deferred items with risk level, status, and dependencies. Phase 6A / D2 ✓ | Done |
| [archive/security/security_backlog.md](archive/security/security_backlog.md) | Earlier version of security backlog (2026-05-27). Superseded by the dated version. | Superseded |

---

## Testing Plans and Methodology (`tests/`)

### Methodology

| File | Description |
|---|---|
| [archive/testing/testing-framework.md](archive/testing/testing-framework.md) | Testing methodology — three evaluation dimensions used across all test suites: tool compliance, argument quality, response behavior. Read before designing new tests. |
| [tests/testing_framework_notes.md](tests/testing_framework_notes.md) | Implementation notes — cumulative prompt length tracking, token thresholds (8K warning, 15K fail), per-provider token count APIs. |
| [tests/agent_audit_template.md](tests/agent_audit_template.md) | Behavioral audit checklist — run against each specialist before deployment; required for Phase 5 sign-off check 10. |

### Phase Testing Plans

| File | Gate | Status |
|---|---|---|
| [tests/phase0_testing_plan.md](tests/phase0_testing_plan.md) | Phase 0 close | Complete |
| [tests/phase1_testing_plan.md](tests/phase1_testing_plan.md) | Phase 1 close | Complete |
| [tests/phase2_testing_plan.md](tests/phase2_testing_plan.md) | Phase 2 close | Complete |
| [tests/phase3_testing_plan.md](tests/phase3_testing_plan.md) | Phase 3 close | Complete |
| [tests/phase4_testing_plan.md](tests/phase4_testing_plan.md) | Phase 4 close | Complete |
| [tests/phase5_testing_plan.md](tests/phase5_testing_plan.md) | Phase 5 sign-off (Alpha gate) | **Pending — not yet run** |
| [tests/phase6_testing_plan.md](tests/phase6_testing_plan.md) | Phase 6 close | Future |
| [tests/phase7_testing_plan.md](tests/phase7_testing_plan.md) | Phase 7 close | Future |
| [tests/security_testing_plan.md](tests/security_testing_plan.md) | Phase 6A sign-off | Future (partial: B1 red team can start now; indirect injection requires E1 integrations live) |
| [tests/model_ceiling_plan_2026-06-03.md](tests/model_ceiling_plan_2026-06-03.md) | Phase 6 / D2 model validation instrument | Future |

### Test Reports and Scripts

| File | Description |
|---|---|
| [tests/phase3_report.md](tests/phase3_report.md) / [_claude](tests/phase3_report_claude.md) / [_gemini](tests/phase3_report_gemini.md) / [_openai](tests/phase3_report_openai.md) | Phase 3 model comparison results |
| [tests/phase4_report_2026-05-19_gpt-4o.md](tests/phase4_report_2026-05-19_gpt-4o.md) | Phase 4 Pattern Miner test — GPT-4o |
| [tests/phase4_report_2026-05-19_models-gemini-3.1-pro-preview.md](tests/phase4_report_2026-05-19_models-gemini-3.1-pro-preview.md) | Phase 4 — Gemini Pro |
| [tests/phase4_report_sonnet-4-6.md](tests/phase4_report_sonnet-4-6.md) | Phase 4 — Sonnet 4.6 |
| [tests/phase4_report_gemini-pro.md](tests/phase4_report_gemini-pro.md) / [_gemini-flash](tests/phase4_report_gemini-flash.md) | Phase 4 — Gemini variants |
| [tests/run_phase3.py](tests/run_phase3.py) / [run_phase4.py](tests/run_phase4.py) | Automated test runners |
| [tests/generate_synthetic_data.py](tests/generate_synthetic_data.py) | Synthetic persona data generator for Pattern Miner testing |

---

## Infrastructure (`scripts/`, `static/`)

| File | Description |
|---|---|
| [scripts/backup.sh](scripts/backup.sh) | Restic backup script |
| [scripts/daily-backup.sh](scripts/daily-backup.sh) | Daily backup wrapper |
| [scripts/backup-setup-passphrase.sh](scripts/backup-setup-passphrase.sh) | Backup passphrase setup |
| [scripts/com.life-manager.backup.plist](scripts/com.life-manager.backup.plist) | launchd plist for scheduled backups |
| [scripts/com.life-manager.daily-backup.plist](scripts/com.life-manager.daily-backup.plist) | launchd plist for daily backup |
| [static/index.html](static/index.html) | Mobile PWA — voice interface, provider/agent selectors, Web Push registration, "missed the mark" tap (pending A1) |
| [static/sw.js](static/sw.js) | Service worker — Web Push notification handling, offline caching |

---

## Research Archive (`research/`)

| File | Description |
|---|---|
| [research/pm_future.md](research/pm_future.md) | Deferred Pattern Miner research — 384-dim ceiling, non-linear correlations, statistical modeling, gamification, large-window retrieval, statistical pre-aggregation as privacy layer. Activates post-Phase 6. Do not build; do not overwrite. |

---

## Memory (`~/.claude/projects/-Users-md-homefolder-Desktop-multi-model-mcp/memory/`)

| File | What it stores |
|---|---|
| [MEMORY.md](~/.claude/projects/-Users-md-homefolder-Desktop-multi-model-mcp/memory/MEMORY.md) | Index of all memory files — loaded automatically into every session. Read first. |
| feedback_*.md | Working preferences — tone, formatting, commit style, tool behaviors. Applied automatically. |
| project_coordinator_synthesizer_architecture.md | Two-agent pipeline design decisions (Coordinator + Synthesizer). |
| project_phase_progress.md | Phase build state (note: 20 days old; verify against current code before relying on). |
| project_model_comparison.md | Phase 3/4 model routing decisions per agent. |
| project_diarist_architecture.md | Diarist design decisions (write-only, Ollama routing). |
| project_local_llm.md | Ollama integration and routing decisions. |
| project_provider_config.md | All 4 providers — models, API key locations, status. |
| Other project_*.md | Observer agent, cost analysis, design review deferred, goals interview ready, future revision topics. |
