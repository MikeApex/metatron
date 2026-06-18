# Codebase Index — Personal AI Life Manager
*Last updated: 2026-06-09. Reference this file at the start of any session to orient without re-reading all files.*

---

## Architecture and Context

| File | Description | Status |
|---|---|---|
| [CLAUDE.md](CLAUDE.md) | Primary developer context — architecture, conventions, terminology, design principles. Read every session. | Current |
| [~/.claude/CLAUDE.md](~/.claude/CLAUDE.md) | Global Claude Code instructions — session logging, commit style, file references, numbered lists, terminal command explanations. | Current |
| [STATUS.md](STATUS.md) | Legacy phase handoff document. **Stale** — says "Phase 3 ready to begin." Superseded by CLAUDE.md + session continuation prompts. Do not rely on it. | Stale |
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
| [core/router.py](core/router.py) | Sensitive routing layer — routes sensitive agents to local LLM; logs fallbacks to `data/logs/routing_fallbacks.json`. `local_enabled` flag in `config/modules/routing.yaml`. |
| [core/server.py](core/server.py) | FastAPI server — `/session` endpoint, PWA serving, Web Push subscriptions, audio upload. Default agent: coordinator. |
| [core/scheduler.py](core/scheduler.py) | Proactive initiation daemon — morning brief (07:30), 90-min companion check-ins, EOD Diarist (20:00), weekly Pattern Miner (Sunday 09:00). |
| [core/memory.py](core/memory.py) | FAISS vector memory — all-MiniLM-L6-v2 (384-dim), embeds log/journal entries on write, semantic search via `search_memory`. |
| [core/voice_pipeline.py](core/voice_pipeline.py) | Voice — faster-Whisper STT + Kokoro/edge-tts/Piper TTS; `run_voice_session()` interactive loop. |
| [core/push.py](core/push.py) | Web Push notification module — VAPID keys, subscription storage, notification dispatch to registered devices. |

---

## Agent Configuration Files (`config/agents/`)

Each file is a Markdown instruction file loaded at runtime by the orchestrator. These files *are* the product — behavior changes require editing them, not code changes.

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
| [config/agents/time_director.md](config/agents/time_director.md) | **Retired.** Prioritization intelligence absorbed into Synthesizer. File archived at `archive/plans/time_director_retired_2026-05-28.md`. | Retired |

---

## Module Configuration (`config/modules/`)

| File | Description |
|---|---|
| [config/modules/routing.yaml](config/modules/routing.yaml) | Model routing assignments per agent + sensitivity tier. `local_enabled: false` — flip to `true` when Ollama running. |
| [config/modules/scheduler.yaml](config/modules/scheduler.yaml) | Scheduler timing, session triggers, proactive initiation rules. |
| [config/modules/caldav.yaml](config/modules/caldav.yaml) | CalDAV server configuration (URL, credentials path, sync settings). |

---

## Templates and Research Archives

| File | Description |
|---|---|
| [config/templates/daily_checkin.md](config/templates/daily_checkin.md) | 4-phase daily check-in template — mood/energy extraction, focus/blockers, log schema. |
| [config/research/goals_interview.md](config/research/goals_interview.md) | Research archive — Motivational Interviewing (MI) methodology that informed the Goals Interviewer design. Reference only, not prescriptive. |

---

## Development Personas (`config/personas/`)

Personas drawn from published diaries, memoirs, and biographies. Used for agent testing and design validation. The `--persona` flag loads a persona at runtime.

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

Each file defines Python functions + JSON schemas. All tools registered in `core/orchestrator.py` → `register_tools()`.

| File | Tools provided |
|---|---|
| [tools/logger.py](tools/logger.py) | `write_log`, `read_log` — daily JSON logs at `data/logs/YYYY-MM-DD.json`; threading lock for parallel writes |
| [tools/goals.py](tools/goals.py) | `read_goals`, `write_goals` — reads/writes `config/goals.yaml` |
| [tools/config_writer.py](tools/config_writer.py) | `write_config` — writes Tier 1-3 config files; restricted to Goals Interviewer and Synthesizer/Logistics |
| [tools/diarist.py](tools/diarist.py) | `write_journal`, `write_archive` — free-form journal entries and life archive (movies, books, experiences) |
| [tools/wisdom.py](tools/wisdom.py) | `read_wisdom`, `write_wisdom` — Life Wisdom Depot; seasonal patterns, personal quirks, recurring events |
| [tools/memory_tool.py](tools/memory_tool.py) | `search_memory` — FAISS semantic search over embedded log/journal history |
| [tools/pattern_miner.py](tools/pattern_miner.py) | `run_pattern_miner`, `write_insight_report` — triggers Pattern Miner analysis; writes reports |
| [tools/baselines.py](tools/baselines.py) | `write_baseline_period`, `read_baseline_periods`, `write_retrospective`, `get_baseline_context` — comparison baselines for Pattern Miner; cold-start extensions pending (Phase 5 / D4) |
| [tools/context_tracker.py](tools/context_tracker.py) | `write_context_tracker`, `read_context_tracker` — persistent session context (open threads, recent signals, flags) |
| [tools/subagent.py](tools/subagent.py) | `run_subagent`, `run_model_conference` — spawns sub-orchestrator sessions; multi-model conference calls |
| [tools/agent_config.py](tools/agent_config.py) | `write_agent_config`, `read_agent_config` — per-specialist persistent state (profile notes, preferences); scoped by agent_name |
| [tools/wishes.py](tools/wishes.py) | `write_wishes`, `read_wishes`, `generate_emergency_card` — Emergency & Legacy store; Synthesizer sole writer; reads deferred to Phase 6 |
| [tools/crm.py](tools/crm.py) | `write_contact`, `read_contact`, `list_contacts`, `log_interaction`, `search_contacts` — Relationships CRM |
| [tools/caldav.py](tools/caldav.py) | `read_calendar`, `write_calendar_event` — CalDAV calendar integration (already built; Phase 6 integration ahead of schedule) |
| [tools/kokoro/speak.py](tools/kokoro/speak.py) | Kokoro TTS wrapper — primary TTS engine (af_heart voice) |
| [tools/kokoro/audition.py](tools/kokoro/audition.py) | Voice audition script — test/compare Kokoro voice options |
| [tools/archive_chats.py](tools/archive_chats.py) | Bulk JSONL export — `python3 tools/archive_chats.py` archives all Claude Code sessions to `archive/transcripts/` |

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
