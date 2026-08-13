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

*Dev-workflow track — no runtime code changed, nothing deployed. **All phases done except §10b**,
now **deferred with its budget corrected to ~165k** (the plan's 40–60k assumed the flat-32k worker
retired the same day). **Next session runs backlog → H7 → code-not-rules → §10b** — that order is
load-bearing: **run 2 attempts `./deploy.sh` from both windows, and per H7 that is ungated in a
non-interactive session**, so it would really deploy, twice. Brief:
[`next_session_prompt_2026-08-13_throughput_10b.md`](archive/plans/next_session_prompt_2026-08-13_throughput_10b.md).
**16 defects, every one found by running** — the last two both *looked like passes*:
`worker_ledger.py` reported 3 runs out of a real 13 (the records were never where the regex was
looking, so widening it changed nothing), and the H5 detector went silent because it had stopped
being able to fire. **Trust no guard whose silence you have not made speak.** Rules for today:
**never `isolation: "worktree"`** (use `new_worktree.sh`, absolute path); **deploying from a
worktree is now safe** (H2 verified live); **a cold worker costs 50–64k**
(`scripts/worker_ledger.py`, now accurate); **`ask` does not gate here**. Harness defects —
**three open, eight closed** — in [`HARNESS_BACKLOG.md`](HARNESS_BACKLOG.md), which **does not
retire with this build**, each for a stated reason. Standing: `PROJECT_LOG.md` is GENERATED from
`archive/log/` fragments, backlog items go to `.claude/backlog_inbox/`, `qa_sweep.sh` is free.*

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
| 08-13 | **The ledger that measured nothing, `verify` scoping, harness reconcile.** `worker_ledger.py` reported **3 worker runs out of a real 13** — and the committed fix for it had changed nothing, because the diagnosis (too-narrow regex) was wrong: ten completions live in a `tool_result` block at `message.content[].content[].text`, joined by that block's `tool_use_id` *field*, and the code `continue`d past every record with a dict `message` before any regex ran. The briefed expectation of "~40 runs" was also wrong — grep hits on a literal the script's own docs contain. Real: floor 30,023 · median 49,902 · worst 108,792. **The H5 detector's silence was not success** — it could no longer fire; found by dumping a real hook payload. H2 verified live (both trees → one lock path; mutual exclusion holds). `/backlog verify` gained pre-dispatch scoping from measured medians + a checkability screen before splitting; dispatch block de-duplicated into `/fix` § 3, `journalctl` into `INFRASTRUCTURE.md`; ceiling set to **200, not the approved 170** — 170 was estimated before the content existed. `/archive` now asserts its own push, and its first run reported a true failure. §10b deferred; next-session prompt reordered on Mike's challenge | `3fc6489`, `daf314d`, `b4abdde`, `6368311`, `7285d94`, `7147293`, `fa69900` — **not deployed** |
| 08-13 | **The permission matcher, the deploy lock, and a Red tier that never prompted.** `defaultMode: "auto"` parsed cleanly and **never took effect**, so the plan's measured 85–88% prompt reduction had never once been observed; replaced with a blanket `allow` list (Mike's call over a curated one — 201 of 1,185 prompts were unclassifiable compounds, and an enumerated list is incomplete by construction). Five `Write(path)` deny rules were **silently ignored** — only `Edit(path)` matches file edits — leaving Tier 0 `constitution.md` reachable by `Write`; the audit found `Bash(./deploy.sh)` was exact-match, so `./deploy.sh --anything` escaped the Red tier. `deploy.sh`'s lock now shared via `--git-common-dir`, proven by holding it in the main tree while a real worktree's copy refused. **Found in passing and worse than either: `ask` does not gate in this harness — it auto-approves**, so the Red tier is ungated unattended (H7, decision open). Rejected: hunk attribution for shared-tree commits — already killed by the Chorus round; the answer is `new_worktree.sh` | `502e560` — **not deployed** |
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
