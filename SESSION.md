# Session Primer — Personal AI Life Manager

*Updated: 2026-08-15, ninth session — **the correction signal Mike reads at every session start was
measuring itself wrong, twice, and both faults are fixed and deployed.** (1) **93 of 174
`USER_CORRECTION` events carried no information** — the strings "None"/"N/A", which passed the
blank-detail guard because they are not blank. Cause is a *template*: `coordinator.md:88` is a slot
annotated "omit if not applicable", and a model filling a template answers the slot. **The agent
file was deliberately not touched** — the instruction is already correct and already ignored, which
is why the control is Python. (2) **A `×N` was a chain length, not a repeat count**: at threshold
0.15 a chain of Heathrow corrections was reported as "calendar events imply completion ×16".
Threshold 0.45 **plus** correction-boilerplate stopwords — neither alone splits it. **These two,
plus the invented `eva@example.com`, are one root cause: a field that looks required gets filled
with something plausible rather than left out.** `## Now` is 9. Tailnet reachable; SSH IAP-only.*

*CRM got real tooling (worker, merged): **`merge_contacts` with archive-on-merge and a
`merged_into` pointer that reads follow** — the first implementation of that standing rule here —
write-path dedup surfacing near-matches as *evidence*, placeholder-email refusal, and a narrow
third-party guard on `write_profile`. **Registration was not enough**: the tool was in no agent's
`allowed_tools`, so the schema filter hid it — **registered-but-ungranted, the same shape as
`[DB-0810-17](1)`'s built-but-unregistered `read_google_contacts`, twice in one day.** Now granted
and documented.*

*Two process gaps, both found because Mike asked why something was still on screen. **The machine
log had no removal step** — sweep and promote were defined, delete was not, so addressed
signatures kept their ⚠ forever. Rule written; 22 cleared, **109 → 87 entries, 8 ⚠ → 3**, the three
survivors filed. **The fragment filing route miscounted silently** — prose fragments folded in
uncounted and reported `0 inbox` with three items present; `fold_fragments()` now coerces. New
markers `@waiting:`/`@session:`/`@kind:` and a derived **`workable`** count; the `@` sigil is
load-bearing (prose wraps onto a line beginning "session:").*

*Dev-workflow track — **Phase 5 is CLOSED; Phase 4 (ROADMAP split) stays deferred; A7 unchanged by
decision** (features first). The completed detail — the `.claude/rules/` split, Read-only rule
delivery, end-to-end worktree dispatch, the commit-guard fixes, `/archive`'s rescope — moved to
`archive/PROJECT_LOG.md` on 2026-08-15 rather than being trimmed sentence by sentence; it is
settled and nothing re-decides it. ⚠ **The one live divergence:** `docs/CONVENTIONS.md:143` points
here for current Model IDs, but § Model IDs below still reads *updated 2026-07-27*.*

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
| 08-15 | **`/backlog deep` — the correction signal was measuring itself wrong twice over.** 93 of 174 `USER_CORRECTION` events said only "None" (a template slot a model fills rather than omits — the agent file was left alone on purpose), and a `×N` was a *chain length*, not a repeat count: a chain of Heathrow corrections was reported as "calendar events imply completion ×16". Both fixed; historical events filtered at read, never deleted. CRM gained `merge_contacts` (archive-on-merge, first here) — **and being registered was not enough, it was granted to no agent.** Machine log had no *removal* step at all: 22 cleared, 8 ⚠ → 3. `fold_fragments()` was miscounting prose fragments as `0 inbox` | `6e57c73`, `2fa8cd6`, `704e79b`, `214a547`, `19cfd12` — **deployed** |
| 08-15 | **Answer the user in their own language, and stop broadcasting profile detail.** `[DB-0810-15]` shipped as Python post-processing after `filter_output()` — prose-in-`synthesizer.md` and a model-called tool were both rejected, the second because a tool call is an extra turn *through* the expensive model. Bulgarian verified live. Found by verifying the render: Mike's `name` field held a contact correction and rode every prompt; `_PROMPT_EXCLUDED` enforced nothing; `Eva`/`Iva Diamond` were one person and the CRM has no merge tooling. Backlog gained `due:`-marked time-gating | `8a7d1d7`, `f9ffd2a`, `b3ff108` — **deployed** |
| 08-15 | **`/backlog attack` — two clusters merged, and the traces found two live user-facing faults.** `[DB-0810-12]` closed: an unsigned tool-call turn is recorded signature-free, so a Vertex 400 no longer destroys the exchange; the never-checked `blocking_replay` route was real. **New:** the Synthesizer quoted `synthesizer.md` verbatim to Mike (filter tier 4 — exactness, not vocabulary; 237 real responses, one suppression), and a session fired at 00:11 (quiet hours now opt-out, with automatic disturb permission for a user-asked one-off). That exposed `fire_session` reading job settings from `scheduler.yaml` only, so every agent-written job carried no settings at all. `[DB-0814-02]` reworked — grace keys on the user, not the Synthesizer's resend | `5cf0a5e`, `bbda875`, `451f622`, `eb01025` — **deployed** |
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
