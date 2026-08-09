# Session Primer — Personal AI Life Manager

*Updated: 2026-08-09 (dev-workflow revamp) — **docs and scripts only, nothing deployed**. The
workflow tooling had become self-feeding: five commands totalling 639 lines, a `DEV_BACKLOG.md`
at 1,658 lines (2.8× the size that triggered the 08-03 context audit, regrown through three
sweeps), and roughly 40% of the preceding week's sessions shipping no product code. Root causes
were structural, not effort: `/archive` filed everything a session noticed and — until 08-09 —
closed nothing; there was no priority dimension, so a plaintext key leak ranked with a stale
docstring; machine-generated tool denials shared an Inbox with Mike's own requests, where five
restatements of one complaint read as five items. **Now:** four commands, `DEV_BACKLOG.md` at
a quarter the size as `Now` (**ranked — Mike decides each item's position as it arrives, against
a recommendation**) / `Later` / `Machine log`, closed items in
`archive/backlog_closed_2026-08.md`, and two bars: *a user would notice, or the roadmap is
blocked* to be filed at all, and **Mike raised it** to enter `Now` — a dev-session find waits in
`Later` until he hits it, credential/data-loss risks excepted. **`docs/WORKFLOW.md` is new and is the manual.** One planned mechanism was
measured and found wrong before shipping: SequenceMatcher dedupe scores real repeats at
0.11–0.42, so it is Dice on content words instead. Next session should confirm the 08-11
`[DB-0804-01]` count and then work `## Now` top-down. Full detail:
[archive/PROJECT_LOG.md](archive/PROJECT_LOG.md).*

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
[docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md). For which command to fire and when:
[docs/WORKFLOW.md](docs/WORKFLOW.md). None of the three is loaded by `/metatron-code`.

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

**Open from the (complete) latency work:** ~~Coordinator slimming~~ **rescoped 2026-08-08 →
`[DB-0808-09]`** (per-specialist turn reduction, `logistics` measured at 8). Full supersession
note: `ROADMAP.md` § D2 latency optimizations.

**Track B2 — all named sub-items now built** (last one, output filter upgrade, `7c70cd9`). Detail: [archive/sessions/2026-08-04 — B1-B4 Security Scoping.md](archive/sessions/2026-08-04%20—%20B1-B4%20Security%20Scoping.md).

**`[DB-0804-01]` still open** — check-ins fixed/deployed (`10bf194`), but no end-to-end
scheduled fire directly observed yet. One-week count due 2026-08-11 — do not check before then.

**Scheduler jobs split two ways (2026-08-08):** silent maintenance jobs register from
`_DEFAULT_JOBS` in `core/scheduler.py` for every persona; jobs with a prompt/notification stay
in per-persona `scheduler.yaml`. **Do not re-add a maintenance job to a persona file.** Reasoning:
`archive/PROJECT_LOG.md`.

**The backlog is the bin for everything outside this roadmap** — restructured 2026-08-09,
**1,658 → ~250 lines** (live counts come from the sync line, not from here). Work it with
**`/backlog`** (`deep` = clustering sweep, `attack` =
parallel prompts; `/backlog-attack` is deleted, it is a mode now). **Which command to fire, and
when: [docs/WORKFLOW.md](docs/WORKFLOW.md).** Three rules: *no item is acted on, or re-filed, on
the strength of its own description* (08-08 proved it three times over); *file only what a user
would notice or what blocks the roadmap*; and *`## Now` is ranked, entry bar is Mike raised it.*

**`[DB-0808-17]`** (A4 clinical hard-fails never run on Flash-Lite) exposes a wording gap in
`ROADMAP.md` § A7 check 8 — routing stays as-is by decision; the test gap is the open item.

---

## Recent sessions

Newest first. Full detail for every entry — and everything older — is in
[archive/PROJECT_LOG.md](archive/PROJECT_LOG.md).

| Date | What | Deployed |
|---|---|---|
| 08-09 | **Dev-workflow revamp** — 5 commands → 4 (`/backlog-attack` folded in as `/backlog attack`); `/archive` 6 steps → 4, no more per-session writeup; `DEV_BACKLOG.md` 1,658 → 246 lines restructured as Now/Later/Machine log with closed items in `archive/backlog_closed_2026-08.md`; sync script routes machine events away from Mike's, collapses repeats to ×N and escalates at ×3; new `docs/WORKFLOW.md`. **Measured, not assumed:** the planned SequenceMatcher dedupe was wrong — real repeats score 0.11–0.42, so it's Dice on content words at 0.15 (5 repeats → 3, zero false merges) | docs/scripts only, no deploy |
| 08-09 | **`/archive` closes backlog items; edit-interruption diagnosis** — step 6 split into 6a close / 6b file / 6c count, with a four-state verdict table and evidence required to close; `/backlog` de-conflicted; tail reminder removed from all 3 files. Found `sync_dev_backlog.py` counts `- **✅` as open (3 items, count inflated). Root-caused the recurring "user cancelled the edit": **⌘S accepts a diff, closing the tab rejects** — not the version skew, extension races, or an Edit-lock, all of which were checked and wrong | `a86dd37` — deployed, VM verified |
| 08-09 | **Billing reconciliation + spend-accounting fixes** — $14 vs Google's $35 traced to three defects: thinking tokens excluded from every Gemini recording site (11.8x undercount, confirmed live); `run_session()` never traced or gated, so scheduler jobs bypassed the daily stop; two independent per-host `spend_guard` ledgers, one never checked (testing was ~half of Aug spend). MW/PH quick-tier routing finding surfaced, not changed — Mike's call, filed as test gap `[DB-0808-17]`. New testing-cost-projection convention; GCP caps raised $70/$150→$100/$175 | `c41baa0` — deployed, verified live |
| 08-08 | **Pollen tool, proactive travel trigger, scheduler defaults** — `get_pollen_forecast` built and verified live (its GPS blocker never applied); `tools/travel_watch.py` gives the TfL/flight tools the automatic caller they lacked; maintenance jobs now register for every persona from code after `daily_calendar_dedup_audit` was found inert for 3 days. (Its "`archive.md` is `Edit`-locked as a loaded skill" conclusion was **wrong** — corrected 08-09) | `8d798a8`, `be1d79e` + VM config; code swept into `7c70cd9` |
| 08-08 | **Memory cross-process race, `MUST_SURFACE` lifecycle, Whisper STT evaluation** — `search_memory` corruption root-caused (a race, not the filed hypothesis) and fixed with `filelock` + atomic writes, self-healing; `clinical_threads` gives clinical flags a `watch` state so they persist without dominating; `small.en` rejected on the VM at RTF 2.23, VAD adopted. A4 gate re-run 6/6 | `7c70cd9`, `08766bb`, `2195fa9` — live-verified |
| 08-08 | **Output filter regex/semantic upgrade, `[CONTEXT]` block repair, end-to-end injection probe** — B2's last sub-item built; malformed context blocks now repaired/salvaged/recorded instead of dropped; new `injection` suite in `run_b1_redteam.py` (3/3 PASS, email row of B1b). Gate: 102 pass / 0 error + 18/18 offline | `7c70cd9` — joint commit with the parallel session (one file, two authors), post-deploy verified live |

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
| Session history | [archive/PROJECT_LOG.md](archive/PROJECT_LOG.md) — one entry per session, newest first (`archive/sessions/` is pre-08-09 only) |
| Which command to fire, and when | [docs/WORKFLOW.md](docs/WORKFLOW.md) |
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
