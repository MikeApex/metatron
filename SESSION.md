# Session Primer — Personal AI Life Manager

*Updated: 2026-08-15, third session. **Deployed — the queue is clear.** `## Now` is **9**, unchanged
in count. **`[DB-0810-13]` (Now #1) is now DIAGNOSED, not built** — read
`archive/plans/db081013_action_provenance_design_2026-08-15.md` before touching it. It is a
**missing-information** failure: specialists' tool calls never reach the Synthesizer, so nothing
could contradict "That's sent." **An agent-file-only fix will test clean and fail in production** —
Mike confirmed the Python provenance track and that the verification is not an LLM task. Binding
order: the Python half deploys before the `synthesizer.md` half is written. **`[DB-0810-12]` (#2)
— instrumentation landed `c8d0c69` and is live; do not close, do not fix.** It needs one live
occurrence: grep the VM journal for `[signature_probe]` ~a week out. `[DB-0809-02]` (#3) still
carries `due: 2026-08-17`. **`[DB-0810-15]` (#6) rescoped by Mike** to a per-persona pair of
*independent* input/output language settings plus translation of surfaced content — text is
unblocked today; voice split out as **`[DB-0815-02]`, `## Later`, low priority**, carrying a
previously-unfiled half (TTS output is hardcoded English in both voices). **`[DB-0815-01]` (#9) is
now only its Bash-write half** — the worktree block is fixed and proven, and chasing it found the
guard **failing open** on any `;` without a leading space. **Two communication rules promoted:**
`.claude/commands/backlog.md` (an id is not a description) and `~/.claude/CLAUDE.md` § Reporting
Level. **A `/backlog deep` sweep of `## Machine log` is still owed.** **Tailnet is INTERMITTENT,
not down**; SSH is **IAP-only** (`gcloud compute ssh --tunnel-through-iap`) — a direct connection
timing out is not an outage.*

*Dev-workflow track — **Phase 5 is CLOSED**, five path-scoped `.claude/rules/*.md` files carry the
area rules, and rule delivery is **Read-only** (Bash `grep` and `Write` do not deliver; a worktree
session does). Full findings:
`archive/log/2026-08-14-12-phase5-closed-instructionsloaded-retired.md`. **Phase 4 (ROADMAP split)
stays deferred.** ⚠ **One divergence still open:** `docs/CONVENTIONS.md:143` points here for live
Model IDs, but § Model IDs below still reads *updated 2026-07-27*. **A7 unchanged by decision** —
features first, Phase closed before Alpha. **Worktree-based parallel dispatch now works end to end**
(score → cluster → verify → dispatch → re-verify → merge → clean up); `hook_commit_guard.py` no
longer blocks it, and its remaining half is in `[DB-0815-01]`. Standing: **`PROJECT_LOG.md` is GENERATED** from
`archive/log/` fragments — write a fragment, never edit it, and a fragment is the collision-safe
half of `/archive` when two windows are live; backlog items go to `.claude/backlog_inbox/`;
`qa_sweep.sh` is free (9 checks, ~3s).*

> **This file is replaced, not appended to.** Each session rewrites the paragraph above and
> updates the state below; the detail goes to [archive/PROJECT_LOG.md](archive/PROJECT_LOG.md).
> **Ceiling: 200 lines, and a 120-line budget on the volatile part** — this paragraph plus
> `## Current state` and `## Recent sessions`, which are the only sections a close-out rewrites.
> Everything below them is reference; leave it closed unless the session made it wrong.
> Both numbers come from `python3 scripts/check_claude_md_claims.py`. Growing a little is fine —
> a new blocker is worth a line; see `.claude/rules/docs-and-logs.md`.

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

**Built, with the constraint that must not be undone** — reasoning for all four:
`archive/PROJECT_LOG.md`.

- **Outbound messaging is Relationships' alone** (`9eb5ac4`); Logistics keeps `read_email`, and
  **Coordinator routes any message-to-a-person to Relationships**, which holds three-level
  disclosure discretion and the communication-style baseline. `send_email`'s `disclosure_note` is
  **outside the confirm fingerprint** — do not move it into `args`. **The ZDR clarification is
  project-wide** (`ROADMAP.md` § Section 0).
- **Tone profiles** deployed, untestable for lack of data (`88957e6`, `3a2bb29`). `tone_shape` is
  accepted by `write_contact` but **deliberately absent from its schema** — only `tone.py` writes
  it, because the source is attacker-writable mail read back as trusted prompt text.
- **Obligations are data, not jobs.** `close_obligation` **requires** evidence; the reconcile
  sweep **never notifies** — it writes candidates, a model session judges.
- **Scheduler jobs split two ways** (08-08): maintenance jobs from `_DEFAULT_JOBS` in
  `core/scheduler.py`; prompt/notification jobs in per-persona `scheduler.yaml`. **Do not re-add a
  maintenance job to a persona file.**

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
| 08-15 | **`/backlog attack` round 2, two clusters** — most of `## Now` is blocked on Mike or a clock, and Now #1 is Red-tier, so it was worked here. [DB-0810-13] diagnosed as missing-information + design; [DB-0810-12] instrumented; [DB-0810-15] rescoped and its voice half split to [DB-0815-02]. **The commit guard was failing OPEN** on any `;` without a leading space — found only by chasing a worker's false block | `6ad3dec`, `ff8f4cc`, `c8d0c69`, `7da7d50`, `c0e2cd8`, `2dfd494` — **deployed** |
| 08-15 | **`/backlog attack`, three clusters.** Two worker worktrees ([DB-0810-09] quality-event registry, [DB-0814-02] `open_threads` timestamp) plus one direct Red-tier fix ([DB-0810-17]a, [DB-0814-01]). Both workers hit `hook_commit_guard.py` failing closed on worktree commits — filed as [DB-0815-01] | `b11e775`, `048e937`, `d40e73c` — deployed |
| 08-15 | **Mike's Franklin ritual leaves `synthesizer.md`** for a new per-persona `evening_ritual.md`, loaded like `self_development.md`. Token-neutral for Mike, a saving for every other persona. First attempt filed it as *design* and was rejected | `6913ad7` — **DEPLOY OWED** |
---

## Useful context to pull as needed

**[CODEBASE_INDEX.md](CODEBASE_INDEX.md) answers "where is X".** It already indexes every agent
file, every tool, `config/modules/routing*.yaml`, `archive/security/`, `tests/`, and
`archive/plans/future_phases.md` — the lookup table that sat here restated eleven of its rows and
was cut on 2026-08-14. The three docs pointers it does not own are in **Read these** above.

One row survived, because no other file carries it:

| Question | Where to look |
|---|---|
| Agent enhancement backlogs | `## Enhancement backlog` at the bottom of each `config/agents/*.md` — **the only copy**; the `DEV_BACKLOG.md` and roadmap mirrors were deleted 2026-08-03 |

---

## Quick start

```bash
cd ~/Desktop/multi-model-mcp && source .venv/bin/activate
python core/server.py --persona mike --port 8001
```

Running on `DEPLOYMENT_MODE=cloud` (Vertex; no Ollama needed). **Everything else** — the
port-8001 kill, running one agent directly, the scheduler daemon, Vertex credentials, the GCP
project, and the sleep/launchd steps that must precede any switch to local Ollama —
[docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md) § Local dev mode.

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
