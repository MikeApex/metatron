# Session Primer — Personal AI Life Manager

*Updated: 2026-08-10, latest (message-bubble timestamps, web + APK) — added a timestamp under
every user and assistant bubble in `static/index.html`, sourced from the `ts` column the server
already carried but never sent to the client (history/catchup/`message` rows); live/streaming
bubbles stamp with the client's current time since the server has none yet for those. Kept as a
sibling of the bubble, not a child, so the streaming code's repeated `textContent` overwrites
don't clobber it. Deployed (`a65a199`, VM HEAD verified) and confirmed on a rebuilt, sideloaded
APK (`check_apk_sync.sh` passed). Held the commit for a parallel session's build/deploy to land
first; no conflict.
Earlier the same day: **provenance is now authored by Python, never the model** — the grounded
loop strips any model-written `SOURCES:` block and appends its own from what the SDK reports
(`a36d8c2`, deployed). New **`scripts/check_agent_tools.py`** + a `PostToolUse` hook catch
agent-file/tool-registry drift; it already found one, `get_weather` (fixed, `924a66e`).
**Unchanged:** `[DB-0804-01]`'s count is due **08-11 — tomorrow**; `[DB-0810-05]` (IMAP tone
profiling) and `[DB-0810-07]` (Book capture) are still unexercised against live data.*

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

**A7 — Phase 5 sign-off — BLOCKED.** A1–A6 complete; Track B2 fully built. The 2026-08-05
pre-sign-off gate cleared the *regression* gate on the cloud path (6/6 + pipeline 3/3), **not A7**.
Three checks still open:

- **B1** — red team. **B1a passed** (re-run 2026-08-08 post-filter-upgrade: 102 pass, 0 error,
  `tests/security_redteam_2026-08-08.md`). **B1b not closed** — email row covered (`injection`,
  3/3 vs `danny_park`); calendar, web and CardDAV rows untouched, gated on Track E.
- **Check 10** — agent behavioural audits (12 specialists; Coordinator/Synthesizer via pipeline probes)
- **Check 12** — constitution alignment review
- **A5b/A5c** — re-run `write_aspirational_baseline` with A5 mission-level data (A3 baseline is still a placeholder); A5c preference activation recorded "unknown, confirm if needed."

**A8 — Pre-Alpha code refactor** — gated on A7. Module extraction from
`core/orchestrator.py` and `core/server.py`. **Full spec, including the regression gate, is in
[ROADMAP.md](ROADMAP.md) § A8** — not restated here, it was a duplicate copy.

**`[DB-0804-01]` still open** — check-ins fixed/deployed (`10bf194`), but no end-to-end
scheduled fire directly observed yet. One-week count due 2026-08-11 — do not check before then.

**Outbound messaging is Relationships' alone** (`9eb5ac4`). Logistics keeps `read_email`; Coordinator
routes any message-to-a-person to Relationships, which holds three-level disclosure discretion and
the communication-style baseline. `send_email`'s `disclosure_note` is **outside the confirm
fingerprint** by design — do not move it into `args`. **The ZDR clarification is project-wide**
(`ROADMAP.md` § Section 0).

**Tone profiles built, not deployed, never run live** (`88957e6`) — `tools/tone.py`,
`config/agents/tone_profiler.md`, `search_correspondence`, `tone_shape` on the contact record.
`tone_shape` is accepted by `write_contact` but **deliberately absent from its schema**: only
`tone.py` writes it, because the source is attacker-writable mail and the field is read back as
trusted prompt text. The fixed JSON key set reassembled in Python is that defence — the injection
check is only a backstop. Gate is **`[DB-0810-05]`**: the IMAP half is entirely unexercised.

**Obligations are data, not jobs.** `tools/obligations.py` + `data/personas/{p}/obligations.yaml`;
closure is inferred, `close_obligation` **requires** evidence. The reconcile sweep **never
notifies** — it writes candidates; a model session judges.

**Scheduler jobs split two ways (2026-08-08):** silent maintenance jobs register from
`_DEFAULT_JOBS` in `core/scheduler.py` for every persona; jobs with a prompt/notification stay
in per-persona `scheduler.yaml`. **Do not re-add a maintenance job to a persona file.** Reasoning:
`archive/PROJECT_LOG.md`.

**The backlog is the bin for everything outside this roadmap**; live counts come from the sync
line, not here. Work it with **`/backlog`** (`deep` = clustering, `attack` = parallel prompts) —
which command and when: [docs/WORKFLOW.md](docs/WORKFLOW.md); its three rules: `CLAUDE.md`.

**`[DB-0808-17]`** (A4 clinical hard-fails never run on Flash-Lite) exposes a wording gap in
`ROADMAP.md` § A7 check 8 — routing stays as-is by decision; the test gap is the open item.

---

## Recent sessions

Newest first, **one line each** — this is an index, not a summary. Reasoning, rejected options
and corrections live in [archive/PROJECT_LOG.md](archive/PROJECT_LOG.md); a row that starts
restating them is duplicating a file that already holds them better.

| Date | What | Deployed |
|---|---|---|
| 08-10 | **Message-bubble timestamps** — user and assistant bubbles show a time, sourced from the server's existing `ts` column for replayed messages, client clock for live/streaming ones. Verified on webapp and a rebuilt, sideloaded APK | `a65a199` — deployed, VM verified |
| 08-10 | **Research provenance authored by Python, not the model** — strips model-written `SOURCES:`, appends `SOURCES (N retrieved)`/`[RETRIEVAL: NONE]` from the SDK; `grounded` is now retrieval-based and tri-state. Built `check_agent_tools.py` + a `PostToolUse` hook on agent/routing edits; it found `get_weather` granted to Logistics but documented only on Research — weather returned to Logistics | `a36d8c2`…`a3b43c5` (5) — deployed, VM verified |
| 08-10 | **Flight/transit queries routed to an agent with no travel feeds** — Coordinator sent flight status to Research (grant: `fetch_url`, `get_pollen_forecast`); `get_flight_status` is Logistics-only and healthy. Fixed + verified in seq 016. Second, **open** defect found: Research fabricates `SOURCES:` because `web_search` does not exist yet is named 4× and citing is mandatory | `d0774f8` — deployed, verified |
| 08-10 | **The Book: thinking/output text capture, tool-call success/failure, plainspeak resource labels, whole-API-call failures** — closes the gap the same-day token-breakout pass left open; text was never captured, only counts, and Ollama's `<think>` content was being discarded outright. New `/monitor/model_errors` endpoint. Filed `[DB-0810-07]`: unexercised against live data | `ffaf7a7` — deployed, VM verified |
| 08-10 | **Feature feasibility scan** — agent-backlog rollup ranked by impact; photos (needs orchestrator content-block support), Google Drive (echoes the reversed Contacts OAuth build, same Testing/Production token wall), geolocation (already `[DB-0808-04]`, classification settled, mechanics not) | docs/research only, no code |
| 08-10 | **`/archive` commits its own output** — step 5 added: explicit manifest, diff before staging, push for backup, **never deploy**, stop on foreign lines. Step 2 repointed at the top of `PROJECT_LOG.md`; primer compacted off its ceiling. `[DB-0805-05]` hit ×3 | `060f53a`…`3e1ae7b` (6) — docs only, **no deploy needed** |
| 08-10 | **The Book: thinking-token breakout, ungrounded-answer flag** — split Vertex's reasoning tokens out of `output_tokens`; added a `grounded` flag after chat #007 was found answering with **zero tool calls** | `cb9f459` — deployed, VM verified |
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

**Vertex note:** AI Studio uses `models/gemini-*` prefix; Vertex drops the prefix. The orchestrator strips it automatically when `GOOGLE_CLOUD_PROJECT` is set.

---

## Key design decisions

**Moved to [CLAUDE.md](CLAUDE.md) → Key Design Decisions.** This file carried a second list
under an almost identical heading, with different contents, so whichever you found first looked
like the whole set. The two unique entries here — the 2026-06-18 ZDR amendment and
archive-on-merge — were merged into that list, which is now the only one.
