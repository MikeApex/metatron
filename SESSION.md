# Session Primer — Personal AI Life Manager

*Updated: 2026-08-13 (ledger fix, `verify` scoping, harness reconcile). `## Now` is **8**. Live runtime items:
**`[DB-0810-13]` is Now #1 and untouched** — specialists report actions they never took, so
anything the system says it *did* (email, calendar, scheduling) is unverified. **`[DB-0810-12]` is
UNBLOCKED**: four post-`8ae1ff9` occurrences, all `write_quality_event` at position 12 on
`synthesizer`, `loop=openai_compat_stream` — the *streaming* variant, where deltas carry no
`thought_signature`. **Instrument the diverged-replay `else` branch before fixing — the first two
diagnoses were both wrong.** `[DB-0810-05]` is blocked on **data, not code** (mailbox holds 1 Sent
/ 6 Inbox; no contact has enough correspondence to profile). **Blocker for any live test: both
Tailscale clients are off the tailnet**; VM and server healthy.*

*Dev-workflow track — no runtime code changed, nothing deployed. **`[H8]` is built and closed:**
`qa_sweep.sh` is now **9 checks, ~6.6s**, zero tokens, and a `Stop` hook reports real session cost
so no work block estimates its own spend again. **Two remain — `[H7]` and §10b — and `[H7]` goes
first because it cannot be done here**: `ask` auto-approves in a non-interactive session, so
testing it returns the expected null result either way. Run it in **iTerm** (clean control), then
the **VS Code chat panel** (the harness actually under test); the decision table is in the brief.
**§10b run 2 must not start until H7 is settled** — it attempts `./deploy.sh` from both windows,
ungated. Brief:
[`next_session_prompt_2026-08-13b_throughput_10b_and_backlog.md`](archive/plans/next_session_prompt_2026-08-13b_throughput_10b_and_backlog.md).
**20 defects, every one found by running** — the newest four were all *inside the checks built to
catch defects*; the worst was a **false pass**, the deploy-lock check reporting `ok` on two empty
strings that compared equal. **A guard that fails identically on both sides looks like agreement.**
⚠ **Three quantities are called "tokens" here** (`subagent_tokens`, raw, weighted) — §10b's ~165k
is in the first; **never compare across them**. Also: **`claude config list` is not a command** (it
costs a nested agent turn). Harness defects — **one open, ten closed** — in
[`HARNESS_BACKLOG.md`](HARNESS_BACKLOG.md), which retires when `[H7]` lands. Standing:
`PROJECT_LOG.md` is GENERATED from `archive/log/` fragments, backlog items go to
`.claude/backlog_inbox/`, `qa_sweep.sh` is free.*

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

**Outbound messaging is Relationships' alone** (`9eb5ac4`). Logistics keeps `read_email`; Coordinator
routes any message-to-a-person to Relationships, which holds three-level disclosure discretion and
the communication-style baseline. `send_email`'s `disclosure_note` is **outside the confirm
fingerprint** by design — do not move it into `args`. **The ZDR clarification is project-wide**
(`ROADMAP.md` § Section 0).

**Tone profiles deployed and now runnable, but untestable for lack of data** (`88957e6`,
`3a2bb29`) — `tools/tone.py`, `config/agents/tone_profiler.md`, `search_correspondence`,
`tone_shape` on the contact record. `tone_shape` is accepted by `write_contact` but **deliberately
absent from its schema**: only `tone.py` writes it, because the source is attacker-writable mail
and the field is read back as trusted prompt text. The fixed JSON key set reassembled in Python is
that defence — the injection check is only a backstop. **`_imap_quote()` fixed the unquoted
`[Gmail]/Sent Mail` select that had been failing every sent-side query** (the blocker is stated
once, above).

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
| 08-13 | **Code-not-rules: token accounting, a claims smoke test, the deploy-lock invariant.** `[H8]` closed in full; `qa_sweep.sh` 7 → 9 checks. **`[H8].1` was unbuildable as written** — it specified grepping `claude config list`, and **there is no `config` subcommand** in either installed binary (2.1.226 / 2.1.170); the CLI parses it as a *prompt* and spends a nested agent turn. Mechanism replaced with a static shape linter needing no CLI; the finding underneath was always proven on a decoy probe. Merged with `[DB-0809-11]` into `check_claude_md_claims.py`, which on first run found **`config/frameworks.md` has never existed in any commit** (marked planned-not-present) and that `.claude/show_phase_progress.py` reads a long-deleted `STATUS.md` — a silent no-op `Stop` hook, left for Mike. Token hook: **dedup by `requestId` is load-bearing** (41 records = 25 requests; a flat sum overcounts **1.74×**) and a raw total is 98% cache reads at 0.1×, so it reports **weighted input-equivalents**. Deploy-lock check **first reported `ok` on two empty strings** — `BASH_SOURCE` cannot be assigned and `set -u` killed both evals identically; fixed, then made to speak against both regression shapes. Estimated 110k, measured **3,423k weighted / 23,934k raw** — wrong quantity, not wrong arithmetic | *(uncommitted at time of writing)* — **not deployed** |
| 08-13 | **The ledger that measured nothing, `verify` scoping, harness reconcile.** `worker_ledger.py` reported **3 worker runs out of a real 13** — and the committed fix for it had changed nothing, because the diagnosis (too-narrow regex) was wrong: ten completions live in a `tool_result` block at `message.content[].content[].text`, joined by that block's `tool_use_id` *field*, and the code `continue`d past every record with a dict `message` before any regex ran. The briefed expectation of "~40 runs" was also wrong — grep hits on a literal the script's own docs contain. Real: floor 30,023 · median 49,902 · worst 108,792. **The H5 detector's silence was not success** — it could no longer fire; found by dumping a real hook payload. H2 verified live (both trees → one lock path; mutual exclusion holds). `/backlog verify` gained pre-dispatch scoping from measured medians + a checkability screen before splitting; dispatch block de-duplicated into `/fix` § 3, `journalctl` into `INFRASTRUCTURE.md`; ceiling set to **200, not the approved 170** — 170 was estimated before the content existed. `/archive` now asserts its own push, and its first run reported a true failure. §10b deferred; next-session prompt reordered on Mike's challenge | `3fc6489`, `daf314d`, `b4abdde`, `6368311`, `7285d94`, `7147293`, `fa69900` — **not deployed** |
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

**The only list is [CLAUDE.md](CLAUDE.md) → Key Design Decisions.** *(Why this file no longer
carries a second: `archive/PROJECT_LOG.md` § 2026-08-03.)*
