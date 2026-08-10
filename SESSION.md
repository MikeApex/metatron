# Session Primer — Personal AI Life Manager

*Updated: 2026-08-10 (`/metatron-troubleshoot` on seq 005 — research_agent grounded-search crash
found, fixed, deployed) — Mike's own multi-feature test (TfL status, Thursday weather, pollen)
failed with a generic "the research tool is returning an error." Root cause: `getattr(gm,
"grounding_chunks", [])` in `run_session_gemini_grounded()` — the `[]` default only covers a
*missing* attribute, but Gemini sometimes sets `grounding_chunks` to `None` explicitly, so
iterating it raised `TypeError`. Broke every grounded Research Agent call that hit that response
shape, both the direct dispatch and the Synthesizer's own `run_subagent` recovery retries.
Reproduced twice on the VM before touching anything; fix verified against Mike's real query before
deploy. One line (`... or []`), committed as `bc1a552`, deployed clean, `metatron-server` restarted
with no crash loop. **Trace-reading note for next time:** the raw trace looked like the Coordinator
or `research_agent` was calling `run_subagent` on itself — it wasn't; `core/trace.py`'s
`pop_agent()` doesn't restore the previous thread-local `current_agent`, so a synchronous nested
`run_subagent` call's tool-record gets misattributed to the child it just finished. Cosmetic only,
not fixed this session. Mike's fuller test list (Google Maps, Flight Status, CRM, Email, Scheduling
duplicates) never generated an exchange to troubleshoot — still needs a live run.
Full detail: [archive/PROJECT_LOG.md](archive/PROJECT_LOG.md).*

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

**Outbound messaging moved to Relationships (2026-08-09, `9eb5ac4`).** Logistics keeps `read_email`
only; Coordinator routes any message-to-a-person to Relationships, which holds three-level
disclosure discretion. **The ZDR clarification is now project-wide** (`ROADMAP.md` § Section 0) —
a new sensitive path needs no separate ruling. Tone-profile pipeline **designed, not built** — plan
at `~/.claude/plans/3-everything-is-on-declarative-kurzweil.md`; unresolved risk is trust laundering.

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

Newest first. Full detail for every entry — and everything older — is in
[archive/PROJECT_LOG.md](archive/PROJECT_LOG.md).

| Date | What | Deployed |
|---|---|---|
| 08-10 | **`/metatron-troubleshoot` seq 005 — research_agent grounded-search crash found and fixed** — `getattr(gm, "grounding_chunks", [])`'s default only covers a missing attribute, not Gemini's None-valued one; broke TfL/weather/pollen and every other grounded query hitting that response shape, both direct dispatch and Synthesizer's `run_subagent` retries. Reproduced on the VM before and after the fix. Also noted (not fixed): `core/trace.py`'s `pop_agent()` doesn't restore the prior thread-local `current_agent`, so nested `run_subagent` tool-call records can misattribute to the child agent in The Book | `bc1a552` — deployed, VM verified, no crash loop |
| 08-10 | **Sonnet cluster closed 9→2; a live WebSocket race found, corrected once, filed** — `[DB-0803-01]` half two fixed by tuning Silero's VAD against all 108 retained audio files (98.07% avg recovered, 0 hallucination markers) rather than disabling it. `[DB-0809-03]` closed with no build — its citation was wrong; the real fix shipped 2026-08-05. `[DB-0809-06]` fixed both causes (catch-up wiped the transcript on reconnect; hidden tabs never checked liveness). `[DB-0808-18]`'s key rotation reached three systems, not one — caught a regression before it shipped (deleting the old `~/.zshrc` export would have broken `ask_gpt` globally). `[DB-0805-02]` closed live against a real phone. **The correction:** doubled text looked install-specific until it recurred 12 minutes later with no install involved — real cause is `ws.close()` not synchronously closing, leaving two sockets briefly live during a reconnect; filed as `[DB-0810-01]`, not fixed, since the two real defenses are a genuine design choice | nine commits, all deployed and verified against the VM + a real phone session |
| 08-09 | **Three premises inverted; a parallel chat's grant shipped inside my commit** — `[DB-0809-04]` sleep over-weighting was **comparability, not availability**: the 08-03 rule's antecedent was false (sleep is 5th of 6 populated fields) so it read as permission; the real cause is that `mood: 'anxious'` cannot be ranked against yesterday and `sleep_hours` can. `[DB-0809-05]` built — obligation store (closure inferred, evidence required) + a reconcile sweep that **never notifies**. `[DB-0809-20]` filed and built: `write_log` merged **shallowly**, so the declared nested schema was actively unsafe — guard before config; **no backfill**, boundary in `pattern_miner.md`. **Incident:** `git add <file>` staged another session's uncommitted `send_email` transfer; deploying it left email sending dead in production until `9eb5ac4`. I had called those commits clean — file-granular check, line-granular collision → `CLAUDE.md` Deploy safety rule 4. `[DB-0803-01]` half two diagnosed: Whisper VAD, not the app | `6330029`, `b9ea29f`, `88b7614`, `9eb5ac4` — all deployed, VM verified |
| 08-09 | **The scheduler was reporting itself as the user** — `[DB-0809-02]` inverted by measurement: all 22 August check-ins were 1–2 sentences, and 4 of the 5 "restatements" were the Synthesizer reading its own scheduler prompt as Mike's voice (`is_proactive` reached only the trace) and firing the repeated-instruction protocol against text he never sent. Fixed in both pipeline copies + a protocol guard. A ≤2-sentence cap was **rejected** — Mike's target is focus, with length as its symptom — so `synthesizer.md` § Scheduled session conduct carries guidance instead; an action awaiting approval is now referred to, never recited. Found a **fourth** copy of the rule in `config/templates/scheduler.yaml`, which seeds every new persona → new `CLAUDE.md` § *Two kinds of preference*. `[DB-0809-06]` diagnosed (catch-up wipes the transcript; hidden tabs never check liveness), `[DB-0809-05]` designed | `82d394b`, `a6d693e` — deployed, VM verified |
| 08-09 | **First `/backlog deep` sweep** — all 8 `## Now` items verified against current code; three premises wrong (`[DB-0809-04]` inverted by measurement — six domains >60% populated, sleep fifth, so it is a Synthesizer interpretation defect not a thin record; `[DB-0805-02]`'s approval UI exists and shipped 3 min before the report; `[DB-0809-12]`'s `2024-*` file does not exist). `[DB-0803-06]` closed (`c4ff279`) — and it had been reported 5 days earlier as `[DB-0803-01]`, unlinked because one entry was symptoms and the other line numbers. New `[DB-0809-18]`: the APK-bundled `index.html` drifts from `static/` silently, which is what made two app items look like code bugs. `## Now` ranked 1–8 | docs only, no deploy |

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
