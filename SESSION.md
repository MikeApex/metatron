# Session Primer — Personal AI Life Manager

*Updated: 2026-08-03 (context-file audit) — **`SESSION.md` was 775 lines; the history now lives in [archive/PROJECT_LOG.md](archive/PROJECT_LOG.md).** Six context files had accreted overlapping jobs with no ownership rule, so the cold-start load had reached ~88k tokens. Dated history, deploy runbooks and the agent-backlog mirror moved out; the standing rules buried in them moved into `CLAUDE.md`; `/archive` became a real command. Immediately before this: `deploy.sh` cried wolf on a good deploy and is fixed — its assertion tested exact HEAD equality, so a parallel window's push made the VM strictly *ahead* and it printed `DEPLOY FAILED … running OLD CODE`, the opposite of true. It now tests **ancestry** with four outcomes (`unverified` / `match` / `ahead` / `failed`) and names the extra commits. **The `ahead` branch is harness-tested only.** Deployed `3492d42`, `c674a91`.*

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

### In progress / next (numbering per 2026-06-10 roadmap — note: renumbered from the 2026-06-09 draft)

**Parallel chats (2026-06-11 batch) — status as of 2026-06-19:** A1, A2, A3, A4+A6 all complete. B1 (red team), Check 10 (agent audits), and Check 12 (constitution review) on hold — see below. See [archive/plans/parallel_chats_index_2026-06-11.md](archive/plans/parallel_chats_index_2026-06-11.md) for prompt files and file-ownership rules.

**Active priority (2026-06-19):** streamline agent flow to reduce response latency — get the tool functionally usable before completing sign-off work. B1/Check10/Check12 resume after latency work stabilises the pipeline.

**Latency work done (2026-06-19):**
- Model tiering: coordinator + 6 specialists → Flash; coordinator reverted to Pro (Flash skips tool calls unreliably); 6 specialists remain on Flash
- Diarist fire-and-forget: code-enforced in `tools/subagent.py` — confirmed working; excluded from SPECIALIST_OUTPUTS
- quick_override added to `routing_cloud.yaml` (Flash) — diarist routes correctly via quick_override path
- Prefix caching: recent context moved to user message in `_run_single_agent()` — system prompt stable per agent
- Output compression: Recreation → compact JSON confirmed working; Logistics / Work/Vocation next
- **Native SDK migration:** reverted — `run_session_gemini` now routes through `_openai_compat_loop` + `_resolve_gemini_credentials` (Vertex OpenAI-compat endpoint). The native genai SDK (`_run_gemini_native_loop`) is retained but unused; migration was abandoned due to an unworkable Vertex thought_signature bug (see below).
- **Streaming:** complete. `POST /session/stream` SSE endpoint live. Anthropic streaming confirmed working. Gemini streaming via `_openai_compat_stream` wired up. PWA client-side SSE consumption deferred.
- **Vertex thought_signature bug — fixed:** When Vertex returns N parallel tool calls, only tc0 gets a cryptographically valid `thought_signature` in `extra_content`. Fix in `_openai_compat_loop`: `message.model_copy(update={"tool_calls": [tc0]})` — trim to single signed call, execute it, let model re-call tc1+ individually. Cost: parallel calls become sequential turns. No 400 errors in testing (turn=6+ confirmed).
- **HF_TOKEN:** read-only token added to `.env` ✓
- Coordinator slimming: handed off to new chat — target ≤3 turns, ≤40K tokens (currently 6 turns, 88K)
- Coord package debug print active in `core/orchestrator.py` (dev — remove before Beta)
- Baseline: 16–20s simple session, 65–74s complex multi-specialist. Was 60–90s.

- ~~**A1** Compliance curve design conversation~~ — **done 2026-06-18.** All four design questions resolved. Shared principle + Synthesizer integrator (Q1); user-reported cold-start, ratchet research-gated (Q2); Synthesizer level only (Q3); nothing activates at A5c, produces plan only (Q4). Decision doc: `archive/plans/compliance_curve_decision_2026-06-13.md`. Agent file edits queued (apply when A2 chat closes). MCP server updates: o3+o1+auto-discovery added to ask_gpt; auto-discovery added to ask_gemini; Opus timeout fixed (600s) in ask_claude.
- ~~**A2** Logging Layer~~ — **done 2026-06-13.** `write_quality_event` in `tools/logger.py`, ROUTING_MISS wired in synthesizer.md, USER_CORRECTION in coordinator.md, PWA tap (`·` dot → `/feedback`). Tests deferred to Alpha launch (`tests/phase5_testing_plan.md` → Known gaps).
- ~~**A3** Cold-start baselines~~ — **done 2026-06-18.** 4 new functions in `tools/baselines.py`: `create_semantic_anchor`, `write_aspirational_baseline`, `shuffled_null_score`, `score_against_anchors`. All 8 canonical anchors written to `data/baselines/semantic_anchors.json`. All 3 roadmap tests pass. Truncated Goals Interview run-guide in `archive/sessions/2026-06-18 — A3 Cold-Start Baselines.md`. A5b re-run pending (after full Goals Interview).
- ~~**A4** Local routing enforcement~~ — **done 2026-06-13.** `local_enabled: true`, fail-closed sensitive routing (no cloud fallbacks), head layer + Learning & Growth + Recreation + Logistics re-tiered local, quick_override guard. MW mania hard-fail: PASS (front-loaded critical instructions). Finance arithmetic: FAIL/deferred D1. Session archive: `2026-06-13 — A4 A6 Local Routing and Token Budget.md`.
- ~~**A5** Goals Interview with real user~~ — **done.** A5b: re-run `write_aspirational_baseline` with existing A5 interview data (replaces A3 placeholder; required for A7 gate — run before A7). A5c preference activation status unknown — confirm if needed. **D1 note:** once VM is provisioned and new features are live, run a fresh Goals Interview + A5b re-run as first-use onboarding on the VM (new D1 item, separate from this A5b).
- ~~**A6** Token budget logging~~ — **done** (all four session paths; 8K warning threshold)
- **A7** Phase 5 sign-off — **blocked** (B1, Check 10, Check 12 on hold pending latency work; A1–A6 all complete). Resume when pipeline is stable.
- **A8** Pre-Alpha code refactor (full program) — **new (added 2026-06-25, scoped 2026-06-26).** Gate: A7 complete. Full module extraction, not just Phase 5 cleanup. `core/orchestrator.py` (1870 lines, 5 concerns) → `core/config.py` + `core/providers.py` + `core/tools.py` + slimmed `core/orchestrator.py`. `core/server.py` → split monitoring endpoints into `core/monitor_api.py`. Remove COORD PACKAGE debug print (line 1616). Update import paths in server, scheduler, subagent, router. Regression gate: A4 clinical-flag scenarios + server startup + full pipeline session + The Book SSE. Note: `run_session_*` functions and `_run_gemini_native_loop` are active switches, not legacy — they stay in `core/providers.py`.
- **B1** Red team — **on hold** (independent of Alpha Gate, but deprioritised — resumes after latency work)
- **Check 10** Agent behavioral audits — **on hold**
- **Check 12** Constitution alignment review — **on hold**

---

## Recent sessions

Newest first. Full detail for every entry — and everything older — is in
[archive/PROJECT_LOG.md](archive/PROJECT_LOG.md).

| Date | What | Deployed |
|---|---|---|
| 08-03 | **Context-file audit** — `SESSION.md` split into this primer + `PROJECT_LOG.md`; `docs/INFRASTRUCTURE.md` created; agent-backlog mirror removed from `DEV_BACKLOG.md`; `/archive` command | docs only |
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
| 07-30 | Client/app audit — the $30 budget was never viable (~$29/mo infrastructure before a single token) | no code |

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
