# Session Primer — Personal AI Life Manager

*Updated: 2026-08-13 (§10a substrate pre-flight). `## Now` is **8**. Live runtime items:
**`[DB-0810-13]` is Now #1 and untouched** — specialists report actions they never took, so
anything the system says it *did* (email, calendar, scheduling) is unverified. **`[DB-0810-12]` is
UNBLOCKED**: four post-`8ae1ff9` occurrences, all `write_quality_event` at position 12 on
`synthesizer`, `loop=openai_compat_stream` — the *streaming* variant, where deltas carry no
`thought_signature`. **Instrument the diverged-replay `else` branch before fixing — the first two
diagnoses were both wrong.** `[DB-0810-05]` is blocked on **data, not code** (mailbox holds 1 Sent
/ 6 Inbox; no contact has enough correspondence to profile). **Blocker for any live test: both
Tailscale clients are off the tailnet**; VM and server healthy. Closed 08-13: `[DB-0810-14]`,
`[DB-0810-16]`, `[DB-0804-01]` — detail in the log.*

*Dev-workflow track — no runtime code changed, nothing deployed. Phases 0–2, 3a, 3b, 4, 6 done.
**§10 was split**: §10a (substrate) is DONE; **§10b — the full two-window rehearsal — moves to
AFTER phases 5 and 8**, by user decision, so it tests the finished mechanism. **Next: 8, then 5,
then §10b.** §10a found **seven defects, every one only by running**; four
fixed (`8ebc5a4`, `75fee3a`, `b2c310d`), four open. **All of them — fixed and open, with
evidence — are in [`HARNESS_BACKLOG.md`](HARNESS_BACKLOG.md), which is where harness defects now
go instead of `DEV_BACKLOG.md`**, and which is reconciled within this build rather than carried.
The two that change how you work today: **`/fix` no longer uses `isolation: "worktree"`** (it
checked workers out from `origin/main`, 11 commits stale) — it makes a `new_worktree.sh` tree and
passes the absolute path, and the gate now sweeps every dirty git worktree because a worker cannot
persistently `cd`; and **`METATRON_COMMIT_GUARD=off` only started working today**, so any earlier
session that hit a false positive had no way past it. Three standing rules unchanged:
`PROJECT_LOG.md` is GENERATED, backlog items go to `.claude/backlog_inbox/`, `qa_sweep.sh` is
free. **A cold worker costs a flat ~32k before any 1.3–1.5× multiplier** — three probes cost 96k.*

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
`[Gmail]/Sent Mail` select that had been failing every sent-side query;** `[DB-0810-05]` is now
blocked on **data, not code** — the mailbox holds 1 Sent / 6 Inbox, so no contact has enough
correspondence to profile.

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
| 08-13 | **Attention-ping hooks, and the transcript titler that had been mangling names since June** — `~/.claude/alert.sh` + `Notification`/`Stop` hooks, toggled by the marker file `~/.claude/.alerts_off` (`alert` in `.zshrc`): **a shell variable cannot gate a hook**, hooks are subprocesses. `PreToolUse` was the wrong event — it would have pinged on every tool call. `archive_chats.py` was stripping **one of a slash command's five tags**, so caveat boilerplate leaked into titles *and* transcript bodies; titles also took the first user message unconditionally. Both fixed, verified over 109 sessions; 31 of 32 historical transcripts retitled, 1 unrecoverable (JSONL deleted). Hand-renaming a transcript is useless — the script re-derives the name and unlinks the old file | no repo commits — `~/.claude/`, **not deployed** |
| 08-13 | **§10a substrate pre-flight — seven defects, every one only by running** (12 for 12 across this plan). `isolation: "worktree"` checks workers out from **`origin/main`, not local `HEAD`** — 11 commits stale, no `qa_sweep.sh` in their tree, reading rules retired that afternoon; `/fix` now uses `new_worktree.sh` instead. The gate swept the session's tree not the worker's, and its own new ledger logged to the ephemeral worktree — keeping the failures, losing the successes. **`METATRON_COMMIT_GUARD=off` was inoperative**: it blocked, printed the remedy, and blocked the remedy. §10 split — §10b rehearsal moved to after 8 and 5, on Mike's challenge. Rejected: keeping `origin/main` current as a standing habit — it makes worker freshness a reason to publish. New `HARNESS_BACKLOG.md`, reconciled within this build | `8ebc5a4`, `75fee3a`, `b2c310d`, `7d196df`, `6e1fc75` — **not deployed** |
| 08-13 | **Throughput 3a/3b/6/4: worktrees, shared-state fragments, QA sweep, `/fix`** — five components, **five defects that appeared only when run**, all having passed static reasoning first. `PROJECT_LOG.md` became generated from fragments (history frozen verbatim, rebuild proven byte-identical by SHA-256 — the plan's per-entry split was rejected as not mechanically reliable). `qa_sweep` needed three fixes before it was usable, all the same fault: scoped by path not by tracked-ness, incl. a `py_compile` sweep that was really 11,247 files. Rejected: deleting agent-file tool references to clear a check | `ef3499b`, `dd237e1`, `fcac265`, `65b96a5` — **not deployed** |
| 08-13 | **Development throughput: permission policy, three hooks, context diet** — 822 approval prompts measured across 25 sessions, ~19 of them decisions. Two premises I argued from were wrong and the docs corrected both (compound commands *are* matched per-subcommand; a built-in read-only set never prompts in any mode). Commit guard designed twice — hunk fingerprinting has a fatal false negative on a shared tree and **would not have caught the 2026-08-09 incident it was built for**; `/code-review high` then found 9 defects in the blob-hash replacement, all one theme: silent passes on risky paths, noisy blocks on routine ones. `CLAUDE.md` 810 → 507. Rejected: conditional roadmap loading, and adopting GSD/OMC | `0dd3375`, `c94baf5` — **not deployed** (no runtime code) |
| 08-13 | **Coordinator close-out: two workers landed, `[DB-0810-12]` unblocked** — `[DB-0810-14]` closed (trace `8c9d8963`, `get_tfl_status` in-trace, not a plausible answer), `[DB-0810-16]` closed, `[DB-0804-01]` closed (came due 08-11, sat unread 2 days; 18 `AgentRecord` errors/7d → 2). Four post-`8ae1ff9` `thought_signature` 400s attributed `loop=openai_compat_stream` — candidate (a), streaming, deltas carry no signature. Found `tools/caldav.py` naming a dead config file in three strings, one the `read_calendar` schema | `7e0e302`, `4fcc170` — deployed |
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
