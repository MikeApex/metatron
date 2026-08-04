# Session Primer — Personal AI Life Manager

*Updated: 2026-08-04 (backlog triage, A4 gate, VM outage) — **The A4 clinical-flag gate is CLEARED on the cloud path, 6/6** (`tests/run_a4_safety.py`, report `tests/a4_safety_rerun_2026-08-04_gemini.md`) — the suites are scripted now, not manual prose. **The bigger find was not the gate:** `physical_health` had never been granted `read_agent_config`, so `MEDICATION_MISSED_CRITICAL` — which must classify from the stored medication profile, never inference — was **structurally unfireable in production.** Granted; `write_agent_config` deliberately not. **Nothing deployed, deliberately:** the server now fails closed without `METATRON_AUTH_PASSWORD` and the VM does not have it (verified) — deploying stops production rather than updating it. **`deploy.sh:54` checks the Mac's `.env`, not the VM's**, and today's run passed that guard and pushed; only a 4-hour VM outage (guest lost all networking while GCE said `RUNNING`, root cause unknown, recovered by stop/start) stopped the pull. Two gate pieces remain before A7: a **pipeline probe** (a flag can fire in MW and still be held at the Synthesizer) and the local/Ollama run.*

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

> **✅ Pre-sign-off gate CLEARED on the cloud path 2026-08-04 — 6/6.**
> `python tests/run_a4_safety.py --persona sarah_chen --provider gemini`. Two pieces still open:
> (1) **pipeline probe** — specialists were tested in isolation, and a flag can fire in Mental
> Wellbeing yet still be *held* at the Synthesizer, which is the real user-facing failure;
> (2) **local path** — `--provider ollama` for like-for-like against the A4 baseline.

Two loose ends inside the gate, both discrete checklist items so they don't get skipped:

- **A5b** — re-run `write_aspirational_baseline` with the A5 mission-level data; the A3 baseline is still a placeholder.
- **A5c** — preference activation status recorded as "unknown, confirm if needed."

**A8 — Pre-Alpha code refactor** — gated on A7. Full module extraction:
`core/orchestrator.py` (~1,870 lines, 5 concerns) → `core/config.py` + `core/providers.py` +
`core/tools.py` + slimmed orchestrator; `core/server.py` → split monitoring into
`core/monitor_api.py`. Remove the COORD PACKAGE debug print. Regression gate: A4 clinical-flag
scenarios + server startup + full pipeline session + The Book SSE.

**Open from the (complete) latency work:** Coordinator slimming — **re-scope against measured
data first.** The Coordinator runs 1 turn, not the 7 the roadmap assumes (`logistics` measured
at 8). See `DEV_BACKLOG.md`.

---

## Recent sessions

Newest first. Full detail for every entry — and everything older — is in
[archive/PROJECT_LOG.md](archive/PROJECT_LOG.md).

| Date | What | Deployed |
|---|---|---|
| 08-04 | **A4 safety gate cleared 6/6** (scripted); `physical_health` `read_agent_config` grant — `MEDICATION_MISSED_CRITICAL` was unfireable; persona trees gitignored; **4h VM outage** recovered | **no — blocked** |
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

---

## ⚠ Deploys are blocked — read before `./deploy.sh`

`core/server.py` fails closed without `METATRON_AUTH_PASSWORD`; `.env` is gitignored and **the
VM does not have it (verified 2026-08-04)** — deploying stops production rather than updating
it. **The preflight guard will not save you:** `deploy.sh:54` greps the *Mac's* `.env` while
saying "the VM's". Append the variable to the VM's `.env` (never scp over it — it holds values
the Mac's does not); the abort text prints the command. Waiting on this: the `physical_health`
`read_agent_config` grant, so `MEDICATION_MISSED_CRITICAL` is dead in production until it ships.

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
