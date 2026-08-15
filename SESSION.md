# Session Primer — Personal AI Life Manager

*Updated: 2026-08-15, seventh session — **`/backlog attack`, two worker clusters, all merged and
deployed by Mike.** **`[DB-0810-12]` is CLOSED** (`5cf0a5e`): a Vertex 400 on a missing
`thought_signature` no longer destroys the exchange — an unsigned tool-call turn is recorded
signature-free, and the never-checked `blocking_replay` route was real and is closed too. Closed on
Mike's argument that a user-visible recurrence would raise its own ticket; **the residual is that
the fix makes recurrence silent**, so the one check left is his — grep the VM journal for
`[signature_probe]` around 08-29. **Two new user-facing faults were found in the VM traces and
fixed:** the Synthesizer read its own instructions aloud to Mike on 08-12 (filter tier 4,
`bbda875` — a 10-word verbatim span from the agent file or constitution; validated against 237 real
responses, one suppression, the leak itself), and a session fired at 00:11, so **quiet hours are now
opt-out** (`451f622`) with Mike's rule built in: a user-asked one-off in the night gets disturb
permission automatically, an agent-invented job never does. That work exposed a live defect —
`fire_session` read job settings from `scheduler.yaml` only, so **every agent-written job resolved to
`{}`** and could carry no setting to any gate. **`[DB-0814-02]` stays open**: expiry now keys on the
user engaging a thread, not the Synthesizer resending it, but neither grace threshold is measured
against real output. **`[DB-0809-02]` is answered early and inverted — see `## Current state`.**
`## Now` is **7**. **A `/backlog deep` sweep of `## Machine log` is still owed.** **Tailnet is
INTERMITTENT, not down**; SSH is **IAP-only** (`gcloud compute ssh --tunnel-through-iap`) — a direct
connection timing out is not an outage.*

*Dev-workflow track — **Phase 5 is CLOSED**, five path-scoped `.claude/rules/*.md` files carry the
area rules, and rule delivery is **Read-only** (Bash `grep` and `Write` do not deliver; a worktree
session does). Full findings:
`archive/log/2026-08-14-12-phase5-closed-instructionsloaded-retired.md`. **Phase 4 (ROADMAP split)
stays deferred.** ⚠ **One divergence still open:** `docs/CONVENTIONS.md:143` points here for live
Model IDs, but § Model IDs below still reads *updated 2026-07-27*. **A7 unchanged by decision** —
features first, Phase closed before Alpha. **Worktree-based parallel dispatch now works end to end**
(score → cluster → verify → dispatch → re-verify → merge → clean up), and `hook_commit_guard.py` no
longer blocks it or a session's own script — both halves closed 08-15, with a probe suite behind
them. **`/archive`'s own rescope (`859ec3a`) now lives in the command file**, which is authoritative;
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

**`[DB-0809-02]` is answered early, and all three of its hypotheses are wrong.** Mike's "three
repetitive messages" (reported 08-12, about **08-11**) were **four different scheduled jobs** —
`companion_checkin` 16:46, an inbox job 18:13, `companion_checkin` 19:48, `evening_close` 20:00 —
each picking up the unfinished evening ritual and re-asking the same two questions.
`_frame_proactive()` works; `evening_close` is a victim, not the culprit. **The real mechanism:
"raise a thing once" has no memory that a question was asked and never answered.** Rewrite the item
around that rather than running its trace week to `due: 2026-08-17`.

---

## Recent sessions

Newest first, **one line each** — this is an index, not a summary. Reasoning, rejected options
and corrections live in [archive/PROJECT_LOG.md](archive/PROJECT_LOG.md); a row that starts
restating them is duplicating a file that already holds them better.

| Date | What | Deployed |
|---|---|---|
| 08-15 | **`/backlog attack` — two clusters merged, and the traces found two live user-facing faults.** `[DB-0810-12]` closed: an unsigned tool-call turn is recorded signature-free, so a Vertex 400 no longer destroys the exchange; the never-checked `blocking_replay` route was real. **New:** the Synthesizer quoted `synthesizer.md` verbatim to Mike (filter tier 4 — exactness, not vocabulary; 237 real responses, one suppression), and a session fired at 00:11 (quiet hours now opt-out, with automatic disturb permission for a user-asked one-off). That exposed `fire_session` reading job settings from `scheduler.yaml` only, so every agent-written job carried no settings at all. `[DB-0814-02]` reworked — grace keys on the user, not the Synthesizer's resend | `5cf0a5e`, `bbda875`, `451f622`, `eb01025` — **deployed** |
| 08-15 | **Two `/fix` runs: an approved action now runs, and the commit guard learns to attribute.** [DB-0815-03] — `/confirm` executes server-side through the tool's own `consume()`; the item's "no trigger" premise was wrong in a way that mattered, and the four tool schemas needed correcting because they bind harder than the agent file. [DB-0815-01] — the guard checks whether *another* session's manifest claims a file's current hash before blocking, so its own script stops reading as a collision; first-ever probe suite, verified discriminating against the pre-fix guard | `2602e2e` — **deployed + APK**; `c3f2ac8` — local harness |
| 08-15 | **[DB-0810-13] built and closed — action provenance.** Python generates an `ACTIONS` block from the trace into the Synthesizer's input; `core/actions.py` classifies all 71 tools as actions vs reads in one place, with a test that fails when a new tool is in neither set. Verified live before the agent-file half was written, which is what the ordering rule bought. **It then found [DB-0815-03] within the hour** — an approved action is never executed — and the [DB-0810-12] probe was caught dumping the whole system prompt to `journalctl` | `0a3706c`, `cbe7d94`, `1831730`, `b2163fa` — **deployed** |
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
