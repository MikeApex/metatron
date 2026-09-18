# Dependency Map — for external flowchart construction

*Generated 2026-09-09. One-off snapshot from live imports, `routing.yaml` tool grants, and
`config/templates/scheduler.yaml` — not a maintained doc (that's
[CODEBASE_INDEX.md](../../CODEBASE_INDEX.md), which answers "where is X" and is edited on demand).
This answers "what depends on what." Re-generate rather than hand-edit if it goes stale.*

Format: a **node list by category**, then an **edge list** (`A → B` = A depends on / calls / loads
B) grouped the same way, then **orphans**. Feed the edge list straight into a graph tool.

---

## 1. Node categories

### 1.1 Entry points
- `core/server.py` — FastAPI server (`/session`, PWA, Web Push, audio upload)
- `core/scheduler.py` — proactive daemon (cron-like, via `schedule` lib)
- `core/orchestrator.py` — REPL / CLI entry, and the shared runtime both entry points call into

### 1.2 Core runtime (`core/`)
`orchestrator.py`, `persona.py`, `router.py`, `memory.py`, `trace.py`, `spend_guard.py`,
`actions.py`, `attachments.py`, `voice_pipeline.py`, `push.py`, `auth.py`, `remote_client.py`,
`translate.py`, `background.py`, `rule_classes.py`

### 1.3 Agent instruction files (`config/agents/*.md`)
Head layer: `coordinator.md`, `synthesizer.md`
Data/analysis: `diarist.md`, `pattern_miner.md`, `crm_sweep.md`, `tone_profiler.md`,
`intake_extractor.md`, `accountability_judge.md`
Personal specialists: `mental_wellbeing.md`, `physical_health.md`, `work_vocation.md`,
`relationships.md`, `finance.md`, `learning_growth.md`, `recreation_hobbies.md`, `logistics.md`
Cloud-only: `research_agent.md`
Setup: `goals_interviewer.md`, `goals_interview_reference.md` (reference only)
Retired (but still a live file — see § 4): `time_director.md` (absorbed into Synthesizer)

### 1.4 Tools (`tools/*.py`)
Grouped by what they touch — see § 3.3 for the full agent→tool grant matrix.

| Group | Files |
|---|---|
| Logs / journal / archive | `logger.py`, `diarist.py` |
| Config-tier writers | `goals.py`, `config_writer.py`, `persona.py`, `profile.py` |
| Memory / wisdom | `memory_tool.py`, `wisdom.py`, `baselines.py`, `pattern_miner.py` |
| Context / session state | `context_tracker.py`, `agent_config.py`, `turn_context.py`, `turn_referent.py` |
| CRM / relationships | `crm.py`, `crm_sweep.py`, `tone.py`, `google_contacts.py`, `contacts_import.py` |
| Calendar | `caldav.py`, `scheduling.py`, `calendar_audit.py`, `calendar_reconcile.py` |
| Mail / intake | `mail.py`, `intake.py`, `intake_email.py`, `intake_extract.py`, `intake_forward.py` |
| Location / travel | `location.py`, `travel_watch.py`, `routing.py`, `regional_transit.py`, `tfl_status.py`, `flights.py`, `places.py` |
| Environment | `ambient.py`, `pollen.py` |
| Obligations / horizon / schedule | `obligations.py`, `horizon.py`, `schedule.py` |
| Wishes / accountability / escalation | `wishes.py`, `accountability.py`, `escalation.py` |
| Confirmation gate | `confirm.py` |
| Web / safety | `web.py`, `untrusted.py`, `rule_audit.py` |
| Sub-orchestration | `subagent.py` |
| Analytics | `analytics.py` |
| Voice | `kokoro/speak.py`, `kokoro/audition.py` |
| Standalone utilities (not tool-registered) | `metatron_monitor.py`, `gen_icon.py` |

### 1.5 Config / data (`config/`)
`constitution.md` (Tier 0), `prime_directive.md` (Tier 1), `mission.md` (Tier 2), `goals.yaml`
(Tier 3), `preferences.yaml`; `modules/routing.yaml` + `modules/routing_cloud.yaml` (agent→model,
agent→tool grants); `modules/scheduler.yaml`… *(actually lives at `config/templates/scheduler.yaml`
— provisioning source, copied once per persona)*; `modules/caldav.yaml` (dead, see § 4);
`modules/email.yaml`, `templates/caldav.yaml`, `templates/email.yaml` (provisioning sources);
`modules/calendar_reconcile.yaml`, `modules/knowledge_domains.yaml`, `modules/regional_transit.yaml`,
`modules/spend_guard.yaml`, `modules/synthesizer_onboarding.md`,
`modules/synthesizer_scheduled_sessions.md`; `personas/*` (13 personas, one live: `mike`)

### 1.6 Scripts / automation (`scripts/`)
Hooks (wired into `.claude/settings.json`): `hook_deny_lift.py`, `hook_context_gate.py`,
`hook_agent_spawn.py`, `hook_commit_guard.py`, `hook_session_tokens.py`, `hook_subagent_gate.py`,
`hook_agent_tools.py`
Checks / linters (manual or CI-style): `check_personas.py`, `check_agent_tools.py`,
`check_claude_md_claims.py`, `check_confirm_executors.py`, `check_deploy_lock.sh`,
`check_knowledge_domains.py`, `check_model_availability.py`, `check_rule_overlap.py`,
`check_apk_sync.sh`, `audit_context_load.py`
Deploy / VM lifecycle: `metatron-pause.sh`, `metatron-resume.sh`, `metatron-billing-override.sh`,
`metatron-vm-override.sh`, `metatron-backup.sh`, `probe_deploy.sh`, `vm_add_swap.sh`,
`vm_memory_watch.py`
Backup: `backup.sh`, `daily-backup.sh`, `backup-setup-passphrase.sh`, two `.plist` launchd files
Backlog / docs machinery: `sync_dev_backlog.py`, `backlog_close_scan.py`, `build_project_log.py`
Persona / worktree provisioning: `new_persona.sh`, `new_worktree.sh`, `rm_worktree.sh`
One-off / migration: `migrate_health_notes.py`, `migrate_wisdom_schema.py`,
`import_vcard_contacts.py`, `google_contacts_authorize.py`, `mint_token.py`, `worker_ledger.py`,
`vertex_cache_admin.py`, `vertex_cost_reconcile.py`, `qa_sweep.sh`

### 1.7 Frontend (`static/`)
`index.html` (PWA), `sw.js` (service worker)

### 1.8 External MCP servers (referenced by this Claude Code session, not by the runtime)
`ask_claude`, `ask_gpt`, `ask_gemini` — registered globally, unrelated to `core/orchestrator.py`'s
own 4-provider routing. Dev-tooling only; not a runtime dependency of the product.

---

## 2. Edge list

### 2.1 Entry points → core runtime
```
core/server.py        → core/orchestrator.py   (run_pipeline_session_stream, run_session)
core/server.py        → core/persona.py        (persona_data_dir)
core/server.py        → core/voice_pipeline.py
core/server.py        → core/push.py
core/server.py        → core/auth.py
core/server.py        → core/translate.py
core/server.py        → core/actions.py
core/server.py        → tools/confirm.py
core/server.py        → tools/location.py
core/scheduler.py     → core/persona.py
core/scheduler.py     → core/push.py
core/scheduler.py     → core/remote_client.py
core/scheduler.py     → tools/accountability.py, tools/analytics.py, tools/calendar_audit.py,
                         tools/calendar_reconcile.py, tools/rule_audit.py  (function jobs, § 3.4)
```

### 2.2 `core/orchestrator.py` → everything (the hub)
```
core/orchestrator.py  → core/persona.py, core/trace.py, core/spend_guard.py, core/actions.py,
                         core/translate.py, core/remote_client.py, core/router.py
core/orchestrator.py  → config/agents/*.md         (loads instruction file per agent_name)
core/orchestrator.py  → config/modules/routing.yaml / routing_cloud.yaml  (via core/router.py)
core/orchestrator.py  → config/constitution.md, prime_directive.md, mission.md, goals.yaml
core/orchestrator.py  → ~30 tools/*.py modules inside register_tools()  (§ 3.1)
core/orchestrator.py  → tools/confirm.py, tools/context_tracker.py, tools/horizon.py,
                         tools/wisdom.py, tools/logger.py, tools/ambient.py, tools/profile.py,
                         tools/pattern_miner.py, tools/calendar_reconcile.py, tools/location.py,
                         tools/accountability.py   (direct calls outside register_tools, for
                         context assembly / prompt injection, not tool dispatch — line ~1046's
                         "_block_source" loop is the single site that pulls in the last three)
```

### 2.3 `core/router.py` (routing layer)
```
core/router.py → config/modules/routing.yaml       (local_enabled: true path)
core/router.py → config/modules/routing_cloud.yaml (cloud path)
core/router.py exposes get_allowed_tools(agent) — consumed by core/orchestrator.py to filter
  tool_schemas per agent, twice: once for specialists (line ~4884), once for the
  Synthesizer specifically (line ~6299, because it dispatches on a second pass)
```

### 2.4 Other core modules

**Correction (2026-09-10 verification pass): the five edges below were recorded backwards in the
first draft** — the earlier text read `core/X.py → caller.py`, when the actual dependency runs
`caller.py → core/X.py` (the caller imports the core module, not the reverse). Fixed here; if the
external flowchart was already built from the 09-09 version, these five arrows need flipping.

```
core/memory.py       → core/persona.py
core/attachments.py  → core/persona.py
core/orchestrator.py → core/trace.py            (correct as drawn in § 2.2)
tools/logger.py       → core/trace.py            (was drawn backwards 09-09)
core/trace.py         → core/spend_guard.py
tools/turn_referent.py → core/actions.py         (was drawn backwards 09-09)
core/server.py, core/remote_client.py, tools/metatron_monitor.py, scripts/sync_dev_backlog.py,
  scripts/mint_token.py → core/auth.py           (was drawn backwards 09-09, and incomplete —
                                                    server.py + remote_client.py were missing)
tools/diarist.py, tools/logger.py → core/background.py   (was drawn backwards 09-09)
tools/persona.py, tools/rule_audit.py → core/rule_classes.py   (was drawn backwards 09-09)
```

Two edges found missing entirely in the first pass:
```
tools/persona.py → tools/rule_audit.py       (imports NEAR_DUPLICATE — one shared threshold)
tools/crm.py     → tools/confirm.py          (registers a confirm executor, same pattern as
                                                tools/escalation.py → tools/confirm.py, already
                                                listed in § 3.2)
tools/contacts_import.py, scripts/google_contacts_authorize.py → tools/google_contacts.py
```

### 2.5 Config-tier data flow
```
config/constitution.md   → loaded into every agent's system prompt (Tier 0, all agents)
config/prime_directive.md, mission.md, goals.yaml → Tiers 1-3, loaded per-persona into
                                                       head-layer agents (coordinator, synthesizer)
config/preferences.yaml  → read by orchestrator for proactive-action governance
config/templates/*.yaml/.md → copied once into config/personas/{p}/ by scripts/new_persona.sh;
                                NOT re-read after provisioning (see § 4, scheduler.yaml drift)
config/modules/routing.yaml / routing_cloud.yaml → core/router.py (model + tool-grant source)
```

### 2.6 Scheduler → tools/agents (scheduled jobs, from `config/templates/scheduler.yaml`)
```
morning_brief            → agent: coordinator     (07:30 weekdays)
companion_checkin        → agent: coordinator     (every 180 min, daily)
evening_close            → agent: coordinator     (20:00 daily) → routes to diarist +
                                                     mental_wellbeing + physical_health
location_anticipation    → agent: coordinator     (10:00 daily)
weekly_pattern_miner     → agent: pattern_miner   (Sun 09:00)
weekly_physical_review   → agent: physical_health (Sun 09:30)
daily_travel_check       → function: tools.travel_watch.travel_check          (06:45 daily)
weekly_clinical_review   → function: tools.escalation.review_clinical_escalations (Sun 11:00)
_DEFAULT_JOBS (in core/scheduler.py, every persona, not in the template — the 09-09 draft listed
3 of these 9 and is corrected here):
  ambient_refresh                 → function: tools.ambient.refresh_ambient_context  (every 180min)
  daily_rule_audit                → function: tools.rule_audit.audit_rules              (05:30)
  daily_calendar_dedup_audit      → function: tools.calendar_audit.audit_calendar_duplicates (05:35)
  daily_calendar_reconcile        → function: tools.calendar_reconcile.reconcile_check     (05:40)
  daily_analytics_rollup          → function: tools.analytics.rollup_yesterday               (05:40)
  daily_accountability_judgment_gate → function: tools.accountability.run_judgment_gate      (05:45)
  crm_sweep (job)                 → function: tools.crm_sweep.sweep                          (05:50)
  intake_sweep                    → function: tools.intake.sweep                    (hourly, 60min)
  intake_digest                   → function: tools.intake.digest_job                (Sun 06:30)
All nine return a plain string (never a notify dict) except daily_travel_check and
weekly_clinical_review in the template above — those two are the only scheduled jobs that can
push a notification on their own; everything else rides the next agent session's context block.
```

### 2.7 Hooks → scripts (`.claude/settings.json`, dev-harness side, not runtime)
```
PreToolUse  (Write|Edit) → hook_deny_lift.py, hook_context_gate.py
PreToolUse  (Agent)      → hook_agent_spawn.py
PreToolUse  (Bash)       → hook_commit_guard.py
PostToolUse (Write|Edit) → hook_agent_tools.py, hook_commit_guard.py
Stop                     → hook_session_tokens.py
SubagentStop              → hook_subagent_gate.py
```

---

## 3. Detail tables (for edge weight / tooltip data)

### 3.1 `register_tools()` — modules imported directly into the tool-schema registry
`logger, goals, config_writer, diarist, wisdom, pattern_miner, baselines, memory_tool,
context_tracker, persona, profile, subagent, crm, tone, agent_config, wishes, caldav, scheduling,
ambient, pollen, tfl_status, flights, routing, regional_transit, places, schedule, obligations,
web, contacts_import, mail, intake, crm_sweep, horizon`

### 3.2 Tool modules NOT in `register_tools()` (called directly, or by another tool module, not
dispatched as an LLM-callable schema)
`confirm.py` (confirmation-gate state machine — called directly by `core/server.py`,
`core/orchestrator.py`, and registers executors from `tools/crm.py` and `tools/escalation.py`),
`horizon.py`/`wisdom.py`/`context_tracker.py`/`ambient.py`/`logger.py` (also called directly for
context-block assembly, in addition to their registered functions), `location.py` (called directly
by `core/server.py`, `core/orchestrator.py`, `tools/confirm.py`, and read by
`scripts/check_confirm_executors.py`), `escalation.py` (scheduler function job + `tools/confirm.py`
+ `tools/context_tracker.py`), `calendar_audit.py`/`calendar_reconcile.py` (scheduler function
jobs — `calendar_reconcile.py` is also pulled directly by `core/orchestrator.py`'s context-block
loop), `rule_audit.py` (scheduler function job, and imported by `tools/persona.py` for its
duplicate-detection threshold), `travel_watch.py` (scheduler function job), `turn_referent.py`
(orchestrator direct call, for "what did I just do" context — and itself imports
`core/actions.py`), `untrusted.py` (imported by 9 other tool modules as a shared sanitizer, not
itself a tool), `google_contacts.py` (called by `tools/contacts_import.py` and by the one-time
OAuth script `scripts/google_contacts_authorize.py`, both one layer removed from the registry),
`intake_email.py`/`intake_extract.py`/`intake_forward.py` (called by `intake.py`'s adapter/
pipeline, one layer removed), `analytics.py` (scheduler-adjacent, called from `core/scheduler.py`'s
`_DEFAULT_JOBS` for the daily rollup — not a live LLM tool)

### 3.3 Agent → tool grants (from `config/modules/routing.yaml`, local path; `routing_cloud.yaml`
kept in parity per its own comments)
```
coordinator        : write_quality_event
synthesizer        : run_subagent, run_model_conference, write_persona, write_profile,
                      read_profile, write_config, write_wishes, read_wishes,
                      generate_emergency_card, write_quality_event, write_schedule,
                      list_schedules, delete_schedule, update_goal, open_obligation,
                      close_obligation, reopen_obligation, list_obligations, read_wisdom,
                      write_wisdom, teach_intake, record_wisdom_response
diarist             : write_journal, write_archive, write_log, write_wisdom
intake_extractor    : (none — gated off pending eval)
accountability_judge: (none — bare dispatch)
crm_sweep           : (none — bare dispatch)
tone_profiler       : (none — bare dispatch)
pattern_miner       : get_log_window, write_insight_report, read_recent_insights,
                      write_baseline_period, read_baseline_periods, write_retrospective,
                      get_baseline_context, create_semantic_anchor, shuffled_null_score,
                      score_against_anchors, read_wisdom, write_wisdom, find_duplicate_wisdom,
                      merge_wisdom_entries, search_memory, write_context_tracker
goals_interviewer   : read_goals, write_goals, write_config, write_retrospective,
                      create_semantic_anchor, write_aspirational_baseline, update_goal,
                      write_baseline_period
mental_wellbeing    : read_log, write_log, write_journal, search_memory, read_agent_config,
                      write_agent_config, read_wisdom, write_wisdom
physical_health     : read_log, write_log, search_memory, read_wisdom, read_profile,
                      write_profile, read_agent_config, write_agent_config, read_archive,
                      write_archive
work_vocation       : read_log, write_log, read_agent_config, write_agent_config, read_profile,
                      write_profile, search_memory, read_wisdom, read_archive, write_archive,
                      read_goals, read_intake_queue
relationships       : read_log, write_log, write_journal, write_contact, read_contact,
                      list_contacts, log_interaction, search_contacts, merge_contacts,
                      unmerge_contacts, import_contacts_file, read_profile, write_profile,
                      send_email, send_calendar_invite, search_memory, get_tone_shape,
                      read_wisdom, read_intake_queue, read_agent_config, write_agent_config,
                      apply_crm_proposals
finance             : read_log, write_log, read_agent_config, write_agent_config, read_profile,
                      write_profile, read_archive, write_archive, read_goals, open_obligation,
                      close_obligation, reopen_obligation, list_obligations, search_memory,
                      read_wisdom, read_intake_queue
learning_growth     : read_log, write_log, search_memory, read_agent_config, write_agent_config,
                      read_wisdom, read_archive, write_archive
recreation_hobbies  : read_log, write_log, read_wisdom, read_intake_queue, find_places,
                      read_archive, write_archive, read_agent_config, write_agent_config,
                      search_memory
logistics           : read_log, write_log, read_calendar, write_calendar_event,
                      update_calendar_event, delete_calendar_event, check_calendar_conflicts,
                      send_calendar_invite, get_weather, get_environmental_snapshot,
                      get_tfl_status, get_flight_status, get_travel_time,
                      get_regional_transit_info, find_places, read_profile, write_profile,
                      write_schedule, list_schedules, delete_schedule, fetch_url,
                      fetch_rendered, read_email, read_agent_config, write_agent_config,
                      search_memory, read_archive, write_archive, open_obligation,
                      close_obligation, reopen_obligation, list_obligations, read_intake_queue,
                      record_horizon_item
research_agent      : fetch_url, fetch_rendered, get_pollen_forecast   (cloud, gemini-3.8-flash,
                      decontextualized only)
```
`allowed_tools` omitted entirely = every registered tool granted (`None` = allow-all in
`core/router.py`). No current agent uses this — `research_agent` used to, was tightened 2026-08-04.

### 3.4 Scheduler function jobs → tool module
See § 2.6. `fire_function()` in `core/scheduler.py` resolves `job["function"]` as a dotted
`module.function` path via `importlib` at fire time — the only place a string in YAML becomes a
live import, so a typo there fails at 06:45, not at daemon start.

---

## 4. Orphaned / dead files and processes

| File | Status | Evidence |
|---|---|---|
| `config/modules/caldav.yaml` | **Dead.** Gitignored, Mac-local, read by nothing, already drifted from the live per-persona config. Documented as dead in `CODEBASE_INDEX.md`. Do not edit. | — |
| `config/agents/time_director.md` | **Correction (2026-09-10): not fully retired — still on disk and still referenced by name.** The 09-09 draft took `CODEBASE_INDEX.md`'s word that this file was archived-and-gone; it is not. The live file at `config/agents/time_director.md` still exists (self-labelled "RETIRED", last touched 2026-05-28) and has no entry in `routing.yaml`/`routing_cloud.yaml`, so it cannot be dispatched through the normal agent path — but the name `time_director` is still live in three places in `core/orchestrator.py` (the confidentiality substring list, the "what becomes unavailable" copy, and the natural-language agent-name normalizer that maps "time"/"time director" → `time_director`) and is the **default** `--agent` value in `core/voice_pipeline.py`'s standalone CLI entry point. None of `core/server.py`'s live request paths pass that default, so it is not reachable from the app today — but running `core/voice_pipeline.py` by hand with no `--agent` flag would target an agent with no routing config. Flag as a stale default to clean up, not as dead weight to delete silently. | this session, direct file read + grep, 2026-09-10 |
| `tools/gen_icon.py` | **Orphaned.** Zero references outside `archive/` history — a one-off PWA icon generator run manually once, no caller in `core/`, `tools/`, or `scripts/`. | grep sweep, this session |
| `config/agents/goals_interview_reference.md` | **Reference only, not loaded at runtime.** Schema/domain-list extract used by whoever edits `goals_interviewer.md`; the orchestrator does not load it into a session. | `CODEBASE_INDEX.md` |
| `archive/plans/*` (all except the two "Active" rows in `CODEBASE_INDEX.md`) | **Historical, never edited, never loaded.** Dated snapshots — background reference only. | `CODEBASE_INDEX.md` § Planning Documents |
| `~/.claude/tools/archive_chats.py` vs deleted `tools/archive_chats.py` | The in-repo copy was a stale ancestor, deleted 2026-08-03 — the only live copy is outside the repo, at `~/.claude/tools/`. Listed so a flowchart doesn't invent an edge to a file that no longer exists. | `CODEBASE_INDEX.md` |
| `docs/CONVENTIONS.md`, `docs/WORKFLOW.md`, `docs/INFRASTRUCTURE.md` | Not "orphaned" but **zero automatic load** — consulted on demand only, no code or hook reads them. Worth marking as leaf/reference nodes with no inbound runtime edge, only human-read edges. | `.claude/rules/docs-and-logs.md` |
| `config/frameworks.md` | **Does not exist — planned only.** `CLAUDE.md` deliberately un-backticks the reference so tooling doesn't treat it as a live path. Do not add a node for it. | `CLAUDE.md` |
| `tools/metatron_monitor.py` | **Not orphaned** — standalone CLI dashboard (`def main()`), imported by `core/auth.py` for shared auth-header logic and run manually, not tool-registered. Flag as a "manual/CLI" node, not dead. | this session |
| `STATUS.md` | **Deleted 2026-08-13**, recoverable via `git show HEAD~1:STATUS.md` if ever needed. Omit from the flowchart entirely — no node. | `CODEBASE_INDEX.md` |

**Caveat on completeness:** `CODEBASE_INDEX.md` itself is stamped "Last updated: 2026-06-09" and
is materially behind current `tools/`/`config/agents/` contents (it lists ~15 tool files; the
directory now holds ~50). This document was built from the *live* filesystem and `routing.yaml`,
not from the stale index — but a routine confirm pass (`grep` each node name against current
`core/`/`tools/` before trusting an edge in the external flowchart) is worth doing before this
snapshot is treated as durable, the same standing rule `DEV_BACKLOG.md` applies to backlog items.
