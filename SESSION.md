# Session Primer — Personal AI Life Manager

*Updated: 2026-08-05 (backlog quick-bucket sweep, first SMTP send, APK rebuild, dictated-email
fix) — **Backlog 44 → 32 open**: 11 stale/already-fixed entries closed, 3 real bugs fixed
(`run_a4_safety.py` report-filename collision, `.message` bubble line-wrap, spend-guard pricing
~3.75x low on flash-lite output), one same-day wrong verification corrected (`write_config`
heading dedup — `_titled()` actually lives in `core/orchestrator.py`, not
`tools/config_writer.py`). DB-0803-06 (`shownIds` eviction) re-derived and confirmed real, left
open. **First real email this system has ever sent** — full `send_email` confirm-gate path
exercised live against `mike`. APK rebuilt and content-verified (mtime looked stale, contents
weren't); on-device install still Mike's step. Two decisions by explicit user instruction:
check-ins keep firing through silence (not a bug, closed — the original gate was against
spamming an *active* user, not against reaching out during quiet); browser live-refresh stays
**open** — a related but distinct fix (`ace22c7`, half-open sockets) doesn't cover this entry's
own render-path diagnosis, confirmed before closing anything. Built and deployed: dictated-email
correction (`core/voice_pipeline.py`, snaps a mis-transcribed address to the closest known
contact via `/transcribe`'s new optional `persona` param). Unchanged: `[DB-0804-01]`
scheduled-fire check still pending; A7 blocked on checks 10/12 and B1b.*

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

- **B1** — red team + automated security tests. **B1a done and passed 2026-08-04, 75/75 checks**
  (`tests/security_redteam_2026-08-04.md`, status now also reflected in `ROADMAP.md` §B1).
  **B1b (indirect injection) still open**, gated on Track E.
- **Check 10** — agent behavioural audits (12 specialists; Coordinator/Synthesizer via pipeline probes)
- **Check 12** — constitution alignment review

> **✅ Pre-sign-off gate FULLY CLEARED on the cloud path — 2026-08-05** (single-agent 6/6 +
> pipeline probe 3/3, both against `sarah_chen`/gemini). **Clears the regression gate, not A7
> itself** — checks 10/12 and B1 remain open. Local/Ollama path is **dormant** (2026-08-05, user
> decision — the ZDR-VM path is what's live; the binding privacy ruling itself is unchanged, only
> the local re-run is parked). Full detail: [archive/PROJECT_LOG.md](archive/PROJECT_LOG.md).

Two loose ends inside the gate, both discrete checklist items so they don't get skipped:

- **A5b** — re-run `write_aspirational_baseline` with the A5 mission-level data (A3 baseline is still a placeholder). **A5c** — preference activation status recorded as "unknown, confirm if needed."

**A8 — Pre-Alpha code refactor** — gated on A7. Module extraction from
`core/orchestrator.py` and `core/server.py`. **Full spec, including the regression gate, is in
[ROADMAP.md](ROADMAP.md) § A8** — not restated here, it was a duplicate copy.

**Open from the (complete) latency work:** Coordinator slimming — **re-scope against measured
data first.** The Coordinator runs 1 turn, not the 7 the roadmap assumes (`logistics` measured
at 8). See `DEV_BACKLOG.md`.

**Track B2 — more done than previously believed.** Item 5's decisions A/B/C are **taken and
built**; the per-agent `allowed_tools` whitelist is already *enforced*, not warn-mode
(`core/orchestrator.py:2190-2193`), and `research_agent` now carries the key too
(`allowed_tools: [fetch_url]`, shipped 2026-08-04). Remaining B2 gaps, plus the Wave 1/Wave 2
execution split, are in
[archive/sessions/2026-08-04 — B1-B4 Security Scoping.md](archive/sessions/2026-08-04%20—%20B1-B4%20Security%20Scoping.md).

> **✅ SMTP send path exercised live, 2026-08-05.** Full `send_email` confirm-gate path run
> against `mike` — `request()` → approve → matching `confirm_token` → real Gmail SMTP. First
> mail this system has ever sent. Detail: [archive/PROJECT_LOG.md](archive/PROJECT_LOG.md).

**✅ `[DB-0803-02]` proactive check-ins fixed and deployed 2026-08-04 (`10bf194`), re-verified
live on the VM.** Root cause was `core/router.py:166` handing a live `AgentRecord` to
`log_model_error()`, masking the real failure. **`[DB-0804-01]` remains open** — a genuine
scheduled fire completing end-to-end hasn't been observed yet, only the crash path is proven
dead. Three time-gated checks filed (~23:03 tonight, 07:30 tomorrow, one-week count
2026-08-11) — do not check before those times.

**The backlog is the bin for everything outside this roadmap.** Work it with **`/backlog`**.
Currently **32 open**, down from 44 after a 2026-08-05 quick-bucket sweep. The one rule: *no
item is acted on, or re-filed, on the strength of its own description* — that sweep found a
same-day verification of its own that was wrong (checked the wrong file), corrected in the same
pass.

---

## Recent sessions

Newest first. Full detail for every entry — and everything older — is in
[archive/PROJECT_LOG.md](archive/PROJECT_LOG.md).

| Date | What | Deployed |
|---|---|---|
| 08-05 | **Backlog quick-bucket sweep, first SMTP send, APK rebuild, dictated-email fix** — 44→32 open; first real email ever sent; APK content-verified; check-ins-fire-through-silence and browser-live-refresh both resolved by explicit decision/verification | `2c097b3`, `a08e38a` |
| 08-05 | **ROADMAP.md gap closed, `/archive` gets a sixth step** — B1a's completion had never reached `ROADMAP.md`; added a ✅ status note there and a new mandatory roadmap-check step to `.claude/commands/archive.md` | docs-only, no deploy |
| 08-04 | **B1a red team executed** — new `tests/run_b1_redteam.py`; 9 disclosure categories (15 prompts incl. variants) + output-filter suite (61 checks) + confused-deputy probe, 75/75 PASS; found sticky MUST_SURFACE context contamination on `sarah_chen`, filed not fixed | tests-only, no deploy |
| 08-04 | **B1–B4 security scoping** — Track B split into two waves (B1a/B2-remainder/B4 now, B1b/B3 gated on Track E); found B2 ~60% already done, PoLP allowlist actually enforced not warn-mode; new recurring security-review protocol | scoping only, no deploy |
| 08-05 | **A7 pipeline probe** — `pipeline` suite added to `run_a4_safety.py`, running MW-3/MW-7/PH-MED through the real Coordinator→Synthesizer path; inverted pass condition (substance surfaces, token doesn't); 3/3 PASS live | tests-only, no deploy |
| 08-04 | **Proactive check-ins fixed** — `[DB-0803-02]` root cause (`AgentRecord` handed to `log_model_error`) found and fixed; deploy.sh WS drain fixed; VM-down detection; live-VM re-verification; **`[DB-0804-01]` time-gated checks filed** | `10bf194`, `ec55788` |
| 08-05 | **Backlog trust repair** — counter counted *up* when items closed; sweep found ~⅓ stale; IDs + provenance; nine tool grants; `/backlog` | `10bf194` (fast-forward) |
| 08-04 | **Item 5 built** — out-of-band confirmation gate (`POST /confirm`), `send_email` to contacts, provenance rule; **Research could not fetch and now can** | `15b9a41` |
| 08-04 | **App: transcription readout is dismissable** — height-capped, `✕` + 12s auto-hide. Needs deploy **and APK rebuild** | **no — pending** |

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
