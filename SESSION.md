# Session Primer — Personal AI Life Manager

*Updated: 2026-08-03 (context-file audit, closed) — **cold start is ~88k → ~28k tokens, verified against a live run rather than estimated.** `SESSION.md` split into this primer plus [archive/PROJECT_LOG.md](archive/PROJECT_LOG.md); deploy/recovery detail to [docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md); [ROADMAP.md](ROADMAP.md) is an abridged live copy — **the full plan under `archive/plans/` is static and must never be edited.** `DEV_BACKLOG.md` is no longer autoloaded (still synced every session); read it when working the backlog. `/archive` now carries the close-out ritual. **One thing to act on:** the test run surfaced a pre-sign-off gate at `ROADMAP.md:113` — prefix-caching moved dynamic context out of the system prompt, so **the A4 clinical-flag hard-fails must be re-run before A7 sign-off**. Audit any session's real load with `python3 scripts/audit_context_load.py`. Deployed: nothing — docs only.*

> **This file is replaced, not appended to.** Each session rewrites the paragraph above and
> updates the state below; the detail goes to [archive/PROJECT_LOG.md](archive/PROJECT_LOG.md).
> If this file is growing session over session, detail is landing in the wrong place — see
> `CLAUDE.md` → **Which File Holds What**.

---

## What this is

A voice-first personal AI life manager — a director and companion for a human life, not a scheduler or task manager. Built on a thin Python harness (`core/orchestrator.py`) with all behavior living in editable config files. Config files are the product; code is infrastructure.

---

## Read these before doing anything

1. **[CLAUDE.md](CLAUDE.md)** — architecture, conventions, terminology, design principles. Auto-loaded into every session but read actively on first session.
2. **[ROADMAP.md](ROADMAP.md)** — the current execution plan, abridged to what is still live: the binding privacy ruling, open Track A items (A7/A8), all of Track B (Security) and Track D (Infrastructure), phase gates, and pre-Alpha streaming items. Start here for any planning or build work. The **full** plan — including completed Track A detail and Tracks C/E/F for Phase 6B onward — is the static, never-edited [archive/plans/phase5_to_future_roadmap_2026-06-10.md](archive/plans/phase5_to_future_roadmap_2026-06-10.md); read it before starting work in any area `ROADMAP.md` says it does not carry.
3. **[~/.claude/projects/-Users-md-homefolder-Desktop-multi-model-mcp/memory/MEMORY.md](~/.claude/projects/-Users-md-homefolder-Desktop-multi-model-mcp/memory/MEMORY.md)** — working preferences and project memory index. Read to understand decisions already made and how to collaborate.

If you need to find a specific file, tool, or planning document: **[CODEBASE_INDEX.md](CODEBASE_INDEX.md)**.
For **why** something was built the way it is — reasoning, rejected options, corrections —
[archive/PROJECT_LOG.md](archive/PROJECT_LOG.md). For deploy, recovery or rebuild detail:
[docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md). Neither is loaded by `/metatron-code`.

---

## Current state — Phase 5 (close)

**Phase 5 intent:** Coordinator Agent + Specialist Modules

### Done
- Coordinator-Synthesizer two-pass pipeline (`core/orchestrator.py:621`)
- All 14 specialist agent files (coordinator, synthesizer, diarist, mental_wellbeing, physical_health, work_vocation, relationships, learning_growth, finance, recreation_hobbies, research_agent, logistics, pattern_miner, goals_interviewer) — **all received deep passes**
- **Phase 5 agent review complete (2026-06-13):** All 14 agents done. Flag consistency audit complete. Research Agent extended: grounded Gemini search implemented in orchestrator (`run_session_gemini_grounded`), decontextualization hardened (constitution stripped from Research system prompt, intent/circumstance stripping added to Coord + Synth). `google-genai` v2.8.0 installed in venv.
- CRM tools (`tools/crm.py`), Wishes shell (`tools/wishes.py`), CalDAV (`tools/caldav.py`)
- Parallel subagent dispatch, write_log threading lock, agent_config tool
- Security: threat model + security backlog complete (`archive/security/`)

### In progress / next

**A7 — Phase 5 sign-off — BLOCKED.** A1–A6 all complete (detail in
[archive/PROJECT_LOG.md](archive/PROJECT_LOG.md)). Three checks on hold, deliberately
deprioritised behind latency work:

- **B1** — red team + automated security tests
- **Check 10** — agent behavioural audits (12 specialists; Coordinator/Synthesizer via pipeline probes)
- **Check 12** — constitution alignment review

> **⚠ Named pre-sign-off gate, surfaced 2026-08-03 — [ROADMAP.md](ROADMAP.md):113.** Prefix
> caching moved dynamic context out of the system prompt for *every* agent, so the **A4
> clinical-flag hard-fails (`MUST_SURFACE` / `CLINICAL_CONCERN`) must be re-run against the new
> assembly order before A7 can be signed off.** This is a clinical-safety path with named
> hard-fail criteria — it is not a formality.

Two loose ends inside the gate, both discrete checklist items so they don't get skipped:

- **A5b** — re-run `write_aspirational_baseline` with the A5 mission-level data; the A3 baseline is still a placeholder.
- **A5c** — preference activation status recorded as "unknown, confirm if needed."

**A8 — Pre-Alpha code refactor** — gated on A7. Full module extraction:
`core/orchestrator.py` (~1,870 lines, 5 concerns) → `core/config.py` + `core/providers.py` +
`core/tools.py` + slimmed orchestrator; `core/server.py` → split monitoring into
`core/monitor_api.py`. Remove the COORD PACKAGE debug print. Regression gate: A4 clinical-flag
scenarios + server startup + full pipeline session + The Book SSE.

**Latency work (2026-06-19) — complete.** Baseline 16–20s simple, 65–74s complex, from 60–90s.
Model tiering, Diarist fire-and-forget, prefix caching, streaming, and the Vertex
`thought_signature` fix all landed; full detail in the project log. **Still open from it:**
Coordinator slimming — but **re-scope against measured data first**, the Coordinator runs 1 turn,
not the 7 the roadmap assumes (`logistics` measured at 8). See `DEV_BACKLOG.md`.


---

## Recent sessions

Newest first. Full detail for every entry — and everything older — is in
[archive/PROJECT_LOG.md](archive/PROJECT_LOG.md).

| Date | What | Deployed |
|---|---|---|
| 08-03 | **Context-file audit** — `SESSION.md` 775→170 lines; `PROJECT_LOG.md`, `INFRASTRUCTURE.md`, abridged `ROADMAP.md`, `/archive`, load auditor. Cold start ~88k→~28k tokens | docs only |
| 08-03 | `deploy.sh` verifies by **ancestry**, not HEAD equality — no more false failures when a parallel window pushes | `3492d42`, `c674a91` |
| 08-03 | Outage chat closeout — ✅ `networks/default` **has thawed**, support case closable; external-IP saving **withdrawn** (it is the VM's only egress path) | `48e17da` |
| 08-03 | **Calendar delivers** — CalDAV live with recurrence/alarms/all-day; `get_weather` + `get_environmental_snapshot`; tool permissions in warn mode; VM backup | `cfcd212`, `6865058` |
| 08-03 | Phase 4 scheduler grants · `update_goal` · Tier 1–2 backup | `2f74cd2`, `8e2983f` |
| 08-03 | Check-in restraint (60m quiet / 180m floor) · **VM formally owns persona config** · biographical capture | — |
| 08-03 | **Rule Redundancy** — one home per rule class; write-time warn, daily zero-token audit, on-demand sweep | `0077a63`, `a03ed7e` |
| 08-02 | Synth self-development awareness + `DEV_BACKLOG.md` as the single change-request list | `6601479`, `dc0d85c` |
| 08-02 | SEQ 021 — specialist clock injection, tool-error hints, failure reporting; capability-gap survey | `6601479` |
| 08-02 | Synthesizer timestamp authority (SEQ 008) · recap fix (SEQ 002) · spend guard + rate limiter | `b184d92`, `799aa3f` |
| 07-31 | ⚠ **26-hour outage** — VPC frozen by billing disable; VM rebuilt on `metatron-net`; cost control restructured to $70 soft / $150 hard | `571f9bc` |

---

## Useful context to pull as needed

| Question | Where to look |
|---|---|
| What does each agent do? | `config/agents/` |
| What tools exist and what they do | `tools/` — all registered in `core/orchestrator.py → register_tools()` |
| What's the security posture? | `archive/security/threat_model_2026-06-04.md`, `archive/security/security_backlog_2026-06-04.md` |
| What are the test criteria for this phase? | `tests/phase5_testing_plan.md` |
| What's parked for later phases? | `archive/plans/future_phases.md` |
| Agent enhancement backlogs | `## Enhancement backlog` at the bottom of each `config/agents/*.md` — **the only copy**; the `DEV_BACKLOG.md` and roadmap mirrors were deleted 2026-08-03 |
| Why was this built this way? | [archive/PROJECT_LOG.md](archive/PROJECT_LOG.md) — dated history, reasoning, corrections |
| Deploy / recovery / rebuild detail | [docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md) |
| Session history | `archive/sessions/` — sorted by date |
| Model routing assignments | `config/modules/routing.yaml` |
| How to run the system | See Quick Start below |

---

## Quick start

> **⚠ Switching to local Mac routing (Ollama)?** Two things must be activated first:
> 1. `sudo pmset -a sleep 0 disksleep 0` — prevent Mac sleep
> 2. `launchctl load ~/Library/LaunchAgents/com.metatron.server.plist` — keep server alive (create plist first if not done — see `archive/sessions/2026-06-20 — VM Provisioning, GitHub, Deploy Pipeline.md`)
> Reverse with: `sudo pmset -a sleep 10 disksleep 10` and `launchctl unload ~/Library/LaunchAgents/com.metatron.server.plist`

```bash
cd ~/Desktop/multi-model-mcp
source .venv/bin/activate

# Start the PWA server (Vertex cloud routing — default as of 2026-06-19)
# No Ollama needed — DEPLOYMENT_MODE=cloud in .env routes all agents to Vertex
python core/server.py --persona mike --port 8001

# Kill a stuck server on port 8001 and restart
lsof -ti :8001 | xargs kill -9 && python core/server.py --persona mike --port 8001

# Run a specific agent directly
python core/orchestrator.py --agent research_agent --provider gemini

# Run the scheduler daemon
python core/scheduler.py
```

**Deployment mode:** `DEPLOYMENT_MODE=cloud` is set in `.env` — loads `config/modules/routing_cloud.yaml` (all agents → Vertex Gemini 3.1 Pro). To use local Ollama instead, remove or unset `DEPLOYMENT_MODE`.

**Vertex credentials:** ADC configured via gcloud on this machine. GCP project: `metatron-ai-499810`, location: `global`.

**If using local Ollama:** `ollama serve` at `localhost:11434`, model `qwen3:14b`.

---

## Model IDs (updated 2026-07-27)

| Provider | Model | ID | Notes |
|---|---|---|---|
| Anthropic | Sonnet 5 (orchestrator fallback) | `claude-sonnet-5` | Only used inside `run_model_conference`'s unused `anthropic` branch — not on the live routing path (cloud/local routing is all Gemini/Ollama). Bumped 2026-07-27 from `claude-sonnet-4-6`. |
| Anthropic | Opus 5 (`ask_claude` MCP alias `opus`) | `claude-opus-5` | Added 2026-07-27 — new Anthropic release, matches Fable-5-tier capability at half price. `opus-4-8`/`opus-4-7` kept as pinned aliases in `~/.claude/mcp_servers/ask_claude.py`. |
| OpenAI | o3 | `o3` | |
| Gemini | Flash-Lite | `gemini-3.1-flash-lite` | ✓ confirmed on Vertex (no `models/` prefix on Vertex) |
| Gemini | Pro | `gemini-3.1-pro-preview` | ✓ confirmed on Vertex |
| Ollama | Local 14B | `qwen3:14b` | local only |

**Vertex note:** AI Studio uses `models/gemini-*` prefix; Vertex drops the prefix. The orchestrator strips it automatically when `GOOGLE_CLOUD_PROJECT` is set. Flash-Lite preview ID discontinues July 9 — already updated to non-preview ID.

---

## Key design decisions

**Moved to [CLAUDE.md](CLAUDE.md) → Key Design Decisions.** This file carried a second list
under an almost identical heading, with different contents, so whichever you found first looked
like the whole set. The two unique entries here — the 2026-06-18 ZDR amendment and
archive-on-merge — were merged into that list, which is now the only one.
