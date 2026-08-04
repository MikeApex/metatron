# Session Primer — Personal AI Life Manager

*Updated: 2026-08-05 (backlog trust repair) — **The backlog never ballooned; the counter was wrong.** `sync_dev_backlog.py` partitioned on a `## Done` heading that had never been written, so struck-through entries counted and **closing an item raised the number**. Fixed — now `N new · N untriaged · N open`, currently **`0 · 0 · 45`**. A verify-before-refile sweep found **about a third of checked items stale**: four closed with evidence, three marked `needs re-derivation`, all survivors given `DB-MMDD-NN` IDs plus who filed them, how, and the origin SEQ. **Biggest find — `AgentRecord is not JSON serializable` is not a logging nuisance: 18 hits in 7 days against 19 total scheduler errors, so proactive check-ins are failing** (`companion_checkin` ×13, **[DB-0803-02]**). Nine tool denials resolved by reading the conversations they occurred in, not the denial text; `physical_health` write granted with `medication_profile` guarded in Python. `/backlog` carries the ritual; `/metatron-code` and `/archive` report the count only. **`9361537` needs `./deploy.sh`.** Carried in from the parallel window and unchanged: the out-of-band confirmation gate and `send_email` are built (`ca993fe`), enforce mode off by decision, SMTP send path still never exercised, APK rebuild pending.*

> **This file is replaced, not appended to.** Each session rewrites the paragraph above and
> updates the state below; the detail goes to [archive/PROJECT_LOG.md](archive/PROJECT_LOG.md).
> **Ceiling: 200 lines.** Growing a little is fine — a new blocker is worth a line. Crossing 200
> means history is accumulating here instead of in the log; see `CLAUDE.md` → **Which File Holds What**.

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

### Built
Coordinator–Synthesizer pipeline; all 14 agent files (deep passes + flag audit complete);
grounded Research search; CRM, Wishes, CalDAV, scheduler-write and profile tools; parallel
subagent dispatch; threat model and security backlog (`archive/security/`); **server auth,
`fetch_url`, `read_email`, and the `<untrusted_content>` boundary (2026-08-04)**.
*Dates and reasoning for all of it: [archive/PROJECT_LOG.md](archive/PROJECT_LOG.md).*

### In progress / next

**A7 — Phase 5 sign-off — BLOCKED.** A1–A6 all complete (detail in
[archive/PROJECT_LOG.md](archive/PROJECT_LOG.md)). Three checks on hold, deliberately
deprioritised behind latency work:

- **B1** — red team + automated security tests
- **Check 10** — agent behavioural audits (12 specialists; Coordinator/Synthesizer via pipeline probes)
- **Check 12** — constitution alignment review

> **✅ Pre-sign-off gate CLEARED on the cloud path 2026-08-04 — 6/6.**
> `python tests/run_a4_safety.py --persona sarah_chen --provider gemini`. **One piece still open:
> the pipeline probe** — specialists were tested in isolation, and a flag can fire in Mental
> Wellbeing yet still be *held* at the Synthesizer, which is the real user-facing failure.
> Scoped and ready to build: add a `pipeline` suite to the existing runner calling
> `run_pipeline_session()`; the pass conditions invert (the *substance* must surface, the flag
> *token* must not). The local-path re-run is **dormant** — see below.

> **Local/Ollama path is DORMANT (2026-08-05, user decision).** The deployment is fully on the
> Vertex VM under the 2026-06-18 ZDR amendment, so `--provider ollama` verifies a path nothing
> uses. `routing.yaml` and the local code stay in place; `ROADMAP.md` §A7 and §0 item 8 are
> annotated, not deleted. **The binding privacy ruling is unchanged** — what is parked is the
> run, not the requirement.

Two loose ends inside the gate, both discrete checklist items so they don't get skipped:

- **A5b** — re-run `write_aspirational_baseline` with the A5 mission-level data; the A3 baseline is still a placeholder.
- **A5c** — preference activation status recorded as "unknown, confirm if needed."

**A8 — Pre-Alpha code refactor** — gated on A7. Module extraction from
`core/orchestrator.py` and `core/server.py`. **Full spec, including the regression gate, is in
[ROADMAP.md](ROADMAP.md) § A8** — not restated here, it was a duplicate copy.

**Open from the (complete) latency work:** Coordinator slimming — **re-scope against measured
data first.** The Coordinator runs 1 turn, not the 7 the roadmap assumes (`logistics` measured
at 8). See `DEV_BACKLOG.md`.

**Track B2 — auth and the confirmation gate are done; enforcement is not.** Item 5's
decisions A/B/C are **taken and built** ([outward_actions_scope_2026-08-04.md](archive/plans/outward_actions_scope_2026-08-04.md)):
nothing outward-facing happens without a tap recorded by `POST /confirm`, and `send_email` is
limited in code to Mike's addresses and saved contacts. Still open in B2: **tool permissions
remain in warn mode by decision** (the 43 grant gaps are the intended build-out), and the same
gate should now be extended to `write_agent_config`/`write_config`, which B2 also requires.

> **The SMTP send path has never been exercised** — every test stops at the gate, so this
> system has not yet sent mail. First real send is also the first test of that code.

**⚠ Proactive check-ins are failing in production — [DB-0803-02].** 18 `AgentRecord is not JSON
serializable` errors in 7 days against **19 total scheduler errors**, so essentially every
scheduler failure is this one; `companion_checkin` accounts for 13. `core/trace.py` is clean
(`_agent_to_dict` has handled it since `c66ed03`), so the failing path is server-side via
`send_one`. **Next step is the server-side traceback, not more code reading.**

**The backlog is trustworthy again, and it is the bin for everything outside this roadmap.**
`0 new · 0 untriaged · 45 open`, every item carrying an ID, who filed it, how, and what was
verified when. Work it with **`/backlog`**. The one rule: *no item is acted on, or re-filed, on
the strength of its own description* — a 2026-08-05 sweep found about a third stale, and one
stale premise produced a well-argued recommendation for the wrong decision.

---

## Recent sessions

Newest first. Full detail for every entry — and everything older — is in
[archive/PROJECT_LOG.md](archive/PROJECT_LOG.md).

| Date | What | Deployed |
|---|---|---|
| 08-05 | **Backlog trust repair** — counter counted *up* when items closed; sweep found ~⅓ stale; IDs + provenance; nine tool grants; `/backlog`; **proactive check-ins found failing** | **no — `9361537` pending** |
| 08-04 | **Item 5 built** — out-of-band confirmation gate (`POST /confirm`), `send_email` to contacts, provenance rule; **Research could not fetch and now can** | `15b9a41` |
| 08-04 | **App: transcription readout is dismissable** — height-capped, `✕` + 12s auto-hide. Needs deploy **and APK rebuild** | **no — pending** |
| 08-04 | **Context second pass** — phase conventions → `docs/CONVENTIONS.md`, prose tightened, memory audit 43→39 files (two were actively wrong). Cold start 28k→26k | docs only |
| 08-04 | **A4 safety gate cleared 6/6** (scripted); `physical_health` `read_agent_config` grant — `MEDICATION_MISSED_CRITICAL` was unfireable; persona trees gitignored; **4h VM outage** recovered | **no — blocked** |
| 08-04 | **Auth live** (cookie+bearer, WS handshake, fail-closed) · `fetch_url` + `read_email` wrapped in `<untrusted_content>` · voice toggle · item 5 scoped | `8e5c47e` |
| 08-03 | **Context-file audit** — `SESSION.md` 775→170 lines; `PROJECT_LOG.md`, `INFRASTRUCTURE.md`, abridged `ROADMAP.md`, `/archive`, load auditor. Cold start ~88k→~28k tokens | docs only |
| 08-03 | `deploy.sh` verifies by **ancestry**, not HEAD equality — no more false failures when a parallel window pushes | `3492d42`, `c674a91` |
| 08-03 | Outage chat closeout — ✅ `networks/default` **has thawed**, support case closable; external-IP saving **withdrawn** (it is the VM's only egress path) | `48e17da` |
| 08-03 | **Calendar delivers** — CalDAV live with recurrence/alarms/all-day; `get_weather` + `get_environmental_snapshot`; tool permissions in warn mode; VM backup | `cfcd212`, `6865058` |
| 08-03 | Phase 4 scheduler grants · `update_goal` · Tier 1–2 backup | `2f74cd2`, `8e2983f` |

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
