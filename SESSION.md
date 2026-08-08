# Session Primer — Personal AI Life Manager

*Updated: 2026-08-08 (pollen tool, proactive travel trigger, scheduler defaults) — **deployed
`8d798a8` / `be1d79e`; items 2–4's code was swept into another window's `7c70cd9` before it could
be committed here**. `get_pollen_forecast` built and **verified live** — and its GPS blocker never
applied: a city name geocodes through the path air quality already uses, so `[DB-0807-02]` had
Pollen inheriting Places' blocker for nothing. The travel trigger is wired (`tools/travel_watch.py`
+ `daily_travel_check`), giving `get_tfl_status`/`get_flight_status` the automatic caller they
never had. **Mike's question "shouldn't the dedup be active for every user?" found the session's
biggest thing:** the scheduler template is copied once at persona creation and never re-synced, so
`daily_calendar_dedup_audit` had been inert in production for three days. Maintenance jobs now
register from `_DEFAULT_JOBS` for every persona; its first real run found 7 duplicate pairs.
**The `/archive` guard is still not written** — `archive.md` is `Edit`-locked while `/archive` is
a loaded skill (`[DB-0808-13]`), and `[DB-0805-05]` fired three times live this session. Carried
forward: `[DB-0804-01]` due 2026-08-11; A7 blocked on checks 10/12 and B1b; `[DB-0806-03]`/`-04`
open. Full detail: [archive/PROJECT_LOG.md](archive/PROJECT_LOG.md).*

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

- **B1** — red team + automated security tests. **B1a passed**; re-run 2026-08-08 after the
  filter upgrade — **102 pass, 0 error** (`tests/security_redteam_2026-08-08.md`). **B1b: the
  email row is covered** (`injection` suite, 3/3 vs `danny_park`) but **not closed** — calendar,
  web page and CardDAV rows untouched, still gated on Track E. That suite needs an
  ordinary-life persona; reasoning in `PROJECT_LOG.md`.
- **Check 10** — agent behavioural audits (12 specialists; Coordinator/Synthesizer via pipeline probes)
- **Check 12** — constitution alignment review

> **✅ Pre-sign-off gate FULLY CLEARED on the cloud path — 2026-08-05** (6/6 + pipeline 3/3).
> Clears the regression gate, **not A7** — checks 10/12 and B1 remain open. Local/Ollama re-run
> is dormant by user decision; the privacy ruling is unchanged. Detail: `PROJECT_LOG.md`.

Two loose ends inside the gate, both discrete checklist items so they don't get skipped:

- **A5b** — re-run `write_aspirational_baseline` with the A5 mission-level data (A3 baseline is still a placeholder). **A5c** — preference activation status recorded as "unknown, confirm if needed."

**A8 — Pre-Alpha code refactor** — gated on A7. Module extraction from
`core/orchestrator.py` and `core/server.py`. **Full spec, including the regression gate, is in
[ROADMAP.md](ROADMAP.md) § A8** — not restated here, it was a duplicate copy.

**Open from the (complete) latency work:** ~~Coordinator slimming~~ — **rescoped 2026-08-08 and
now `[DB-0808-09]`.** The Coordinator runs 1 turn, not the 6–7 the plan assumed; the cost is
per-specialist internal turns (`logistics` at 8). The static plan carries a dated supersession
note; the live item leads with a measurement sweep and sets no target until one exists.

**Track B2 — all named sub-items now built.** PoLP allowlist enforced, both confirm-gates,
CORS, `run_session_anthropic`'s iteration limit, `run_model_conference` scoping, and the output
filter upgrade (the last one, `7c70cd9`). Wave 1/Wave 2 split and any residual gaps:
[archive/sessions/2026-08-04 — B1-B4 Security Scoping.md](archive/sessions/2026-08-04%20—%20B1-B4%20Security%20Scoping.md).

**`[DB-0804-01]` still open** — proactive check-ins are fixed and deployed (`10bf194`,
[archive/PROJECT_LOG.md](archive/PROJECT_LOG.md) has the root cause), but a genuine scheduled
fire completing end-to-end still hasn't been directly observed. One-week count due
2026-08-11 — do not check before then.

**Scheduler jobs now split two ways (2026-08-08).** Silent maintenance jobs register from
`_DEFAULT_JOBS` in `core/scheduler.py` for **every** persona — a new one is live everywhere on
deploy. Jobs with a prompt or a notification are preferences and stay in per-persona
`scheduler.yaml`; `check_personas.py` warns when those drift from the template. **Do not re-add a
maintenance job to a persona file** — that pins it to a stale copy, which is the bug this fixed.

**The backlog is the bin for everything outside this roadmap.** Work it with **`/backlog`**; use
**`/backlog-attack`** for a scored, clustered attack plan. **48 open, 6 untriaged, 0 new.**
The one rule: *no item is acted on, or re-filed, on the strength of its own description* — 08-08
proved it three times over. Two clusters found stale premises (an item half-fixed two days
earlier; `[DB-0803-03]`'s stated root cause wrong after five days as "confirmed"), and this
session found `[DB-0807-02]` carrying a blocker that had never applied to half of it.

---

## Recent sessions

Newest first. Full detail for every entry — and everything older — is in
[archive/PROJECT_LOG.md](archive/PROJECT_LOG.md).

| Date | What | Deployed |
|---|---|---|
| 08-08 | **Pollen tool, proactive travel trigger, scheduler defaults** — `get_pollen_forecast` built and verified live (its GPS blocker never applied); `tools/travel_watch.py` gives the TfL/flight tools the automatic caller they lacked; maintenance jobs now register for every persona from code after `daily_calendar_dedup_audit` was found inert for 3 days. `/archive` guard blocked — `archive.md` is `Edit`-locked as a loaded skill | `8d798a8`, `be1d79e` + VM config; code swept into `7c70cd9` |
| 08-08 | **Memory cross-process race, `MUST_SURFACE` lifecycle, Whisper STT evaluation** — `search_memory` corruption root-caused (a race, not the filed hypothesis) and fixed with `filelock` + atomic writes, self-healing; `clinical_threads` gives clinical flags a `watch` state so they persist without dominating; `small.en` rejected on the VM at RTF 2.23, VAD adopted. A4 gate re-run 6/6 | `7c70cd9`, `08766bb`, `2195fa9` — live-verified |
| 08-08 | **Output filter regex/semantic upgrade, `[CONTEXT]` block repair, end-to-end injection probe** — B2's last sub-item built; malformed context blocks now repaired/salvaged/recorded instead of dropped; new `injection` suite in `run_b1_redteam.py` (3/3 PASS, email row of B1b). Gate: 102 pass / 0 error + 18/18 offline | `7c70cd9` — joint commit with the parallel session (one file, two authors), post-deploy verified live |
| 08-08 | **New `/backlog-attack` command** — scores `DEV_BACKLOG.md`'s open items and clusters the top ones into 3 non-overlapping single-session prompts; kept separate from `/backlog`; not yet run | docs-only, no deploy |
| 08-08 | **Travel/routing tools, Google API onboarding, CRM hardening** — `get_tfl_status`/`get_flight_status`/`get_travel_time` (Google Maps default router) built; Google Contacts OAuth built then reversed same day for a simpler local fix (`write_contact` guardrail, vCard import, `write_profile` confirm-gate); Places/Pollen researched not built | `c4ff279` |
| 08-06 | **Billing investigation + region latency analysis** — Compute Engine "no billing since Aug 4" traced to GCE report lag (VM confirmed running, no cap fired); europe-west1 vs us-central1 priced live (+10% compute, ~$2.60/mo, ~200–280ms/turn saved); investigation only, [DB-0806-03]/[DB-0806-04] filed | investigation only, no deploy |
| 08-05 | **Backlog quick-bucket sweep, first SMTP send, APK rebuild, dictated-email fix** — 44→32 open; first real email ever sent; APK content-verified; check-ins-fire-through-silence and browser-live-refresh both resolved by explicit decision/verification | `2c097b3`, `a08e38a` |
| 08-05 | **ROADMAP.md gap closed, `/archive` gets a sixth step** — B1a's completion had never reached `ROADMAP.md`; added a ✅ status note there and a new mandatory roadmap-check step to `.claude/commands/archive.md` | docs-only, no deploy |

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
