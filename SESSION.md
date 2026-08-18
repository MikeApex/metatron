# Session Primer — Personal AI Life Manager

*Updated: 2026-08-18, late — **a verification sweep in which every item that closed, closed by
running something rather than building it.*** Four out: the clinical hard-fails now have a **PASS on
the model tier that actually serves them** (3/3 on Flash-Lite); **double-booking protection got its
first live exercise since it shipped in early August** (9/9 against the real calendar on the VM,
junk events cleaned up and the cleanup *proved* by re-query); the drop-off inference bug was already
fixed and was closed within an hour by testing it; and **the Synthesizer can no longer open a reply
by reading its own thinking aloud**. Two more items were corrected rather than closed — both told a
future session to do something wrong. `## Later` 41 → 39, file 1,294 → **1,290 lines: flat rather
than climbing, for the first time.** **Nothing deployed** — `core/orchestrator.py` and
`tools/crm.py` both changed and need one, as does `f4cc812` from the previous session.*

*⚠ **Content was published off this machine without being asked for, and the guard is now
mechanical.** A full backlog inventory — carrying a real family member's first name — went to a
claude.ai-hosted artifact proactively. **"Starts private" is not "stays on the machine",** and no
tool here can delete an artifact; Mike removed the URL. `Artifact`/`WebFetch`/`WebSearch` are now
**denied** in `.claude/settings.json`, verified by probing rather than assumed. Shareable documents
are **files** in `archive/plans/`. Full entry: `archive/log/2026-08-18-04-*`.*

*⚠ **Why the backlog grows, answered — and it is not that work keeps arriving.** An inventory of all
43 items found **eleven were finished, deployed code waiting on one ordinary use each.** Finished
work has no exit. New binding rules: **confirm a fix in the session that makes it** or time-gate it
with a date; **a closed item is deleted**, its evidence to `archive/backlog_closed_2026-08.md`; a
sweep **shortens or removes, never lengthens**. And **do not ask permission for work already
authorised** — that is what parked the calendar test for a fortnight. Memory:
`feedback-backlog-items-must-exit`.*

*⚠ **Two backlog descriptions were actively dangerous.** The A4-language item instructed a run that
would have **failed a correct response** (the suite matches English words; translation renders
them). And a hypothesis held for days was wrong: the Synthesizer leak is **not** a plumbing fault —
measured live, reasoning arrives inside `content` with no separate channel, so **the output filter
is the only control, not a backstop.***

***Next session is a clearing sweep, not a build:**
`archive/handoffs/2026-08-19-clearing-sweep-prompt.md`. Interactive testing with Mike present to
empty the done-pending-use pile, then item-by-item with exactly one of remove / do-now /
decide-and-file-unbuilt. Map: `archive/plans/backlog_inventory_2026-08-18.md`.*

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

**A9 — Product analytics — FIRST DRAFT BUILT AND DEPLOYED 2026-08-18; review deferred.** Alpha
gate requirement. **The core metric is absorbed work, not engagement** — sessions are the
denominator, so rising engagement is not success. `tools/analytics.py`, 05:40 job, content-free
per-user rows, cohort anchor pinned. **Refinement is `ROADMAP.md` § A9a**, `@waiting` on `mike`
holding goals and real data in ongoing use; the five provisional parts (the world-affecting list,
the un-split T1/T2, COGS, the self-report substitute, per-user collection) are enumerated there.
Tracked as `[DB-0818-03]`.

**A8 — Pre-Alpha code refactor** — gated on A7. Module extraction from
`core/orchestrator.py` and `core/server.py`. **Full spec, including the regression gate, is in
[ROADMAP.md](ROADMAP.md) § A8** — not restated here, it was a duplicate copy.

**Four built-and-standing constraints must not be undone** — outbound messaging is
Relationships' alone; tone profiles ship with `tone_shape` deliberately absent from
`write_contact`'s schema; obligations are data, not jobs; scheduler maintenance jobs live in
`core/scheduler.py`, never a persona file. **Full statements and the reasoning for all four:
`archive/PROJECT_LOG.md`** — they have not changed in three sessions, so they are reference now,
not current state.

**`[DB-0809-02]`** (one unfinished ritual arriving as four scheduled messages) — parked in
`## Later` 2026-08-18 as `@session:`: the mechanism is known (*"raise a thing once" has no memory
that a question was asked and never answered*), the fix shape is Mike's call, and two prior
diagnoses were confidently wrong. Evidence in `DEV_BACKLOG.md`, not here.

**Knowledge layer — what is NOT covered.** A4 passes with `sarah_chen`'s manifest holding one
`work` entry, so the regression **never touches the knowledge path**. Giving it coverage means
health-domain entries on the *VM's* `sarah_chen`, which changes safety-test conditions and is a
decision, not a chore. Filed, not done. Mike's own store still holds intention-shaped entries
(`dietary_analysis_interest`, `lunch_options`) — the class the new write guidance now prevents,
and part of the 24 flagged on 08-15 as not belonging in the fact store.

---

## Recent sessions

Newest first, **one line each** — this is an index, not a summary. Reasoning, rejected options
and corrections live in [archive/PROJECT_LOG.md](archive/PROJECT_LOG.md); a row that starts
restating them is duplicating a file that already holds them better.

| Date | What | Deployed |
|---|---|---|
| 08-18 | **`/backlog deep` + attack round — six Green fixes, and `/archive` now closes what it fixed by accident.** Doubled reply on reconnect; soft deadline dropped first; complaint naming a tool suppressed; nested-call attribution; A4 `--complexity`; persona-file blind spot in the grant guard. **`scripts/backlog_close_scan.py`** replaces step 4's filename grep — it matches the diff's *added lines*, because an incidental closure is one the commit message never mentions (`[DB-0808-16]`, open ten days after being fixed). **Three of my own premises were wrong**: two relayed to a worker from my own verification (deleting them would have dropped every parallel specialist from the trace), and the TfL item's bug does not exist in the code | `0a9e311`, `3a43f62`, `10fc9f6`, `87aad78` — **deployed**; `f4cc812` **not yet** |
| 08-18 | **`/backlog attack` — three clusters, a VM that had been OOM-killing itself, and A9 analytics.** CRM placeholder guard; `contacts_import`; `fetch_rendered` with three memory guards. **Mike's "let Playwright die first" plan was half right** — the kernel kills the *largest* process (the server, proven 08-15 15:02) and SIGKILL returns no message, so the refusal moved *before* launch. VM gained swap, a watchdog and Playwright. **A9 built: absorbed work, not engagement** — 26-day backfill shows 94 absorbed, 10 autonomous, zero before 08-02. **`[DB-0813-02]` was misdiagnosed** (key valid, MCP `env: {}` empty) | `8c7121b`, `6097c44`, `5c3bb3b`, `4d10cbd`, `35499af`, `865c9b6` — **deployed** |
| 08-18 | **Knowledge layering wired, deployed, plan closed.** Steps 4–12: derived manifest, `KNOWLEDGE_TO_LOAD` pre-fetch in both pipeline paths, `WISDOM_PROPOSAL` parsed in Python, grants in parity, seven agents that were instructed to read the store and granted nothing. Step 10 run on the VM; `health_notes` retired. **The zero-specialist path was abandoned rather than tuned for** — the counter-test exists to stop exactly that trade. Found by running it: two turns wrote an *intention* as standing fact; a key-based duplicate check missed a placeholder holding the same fact; Mac and VM `sarah_chen` stores had diverged 38 vs 1 | `360b843`, `d128130`, `7cb9ebd`, `2a51f46` — **deployed, A4 3/3** |
| 08-18 | **A verification sweep where everything that closed, closed by running it.** Clinical hard-fails PASS on the tier that serves them; **double-booking protection's first live run since it shipped** (9/9, real calendar, cleanup proved by re-query); the drop-off bug closed in an hour by testing it — its evidence predated the code it blamed by three days; tier 5 stops the Synthesizer reading its own thinking aloud, **and the plumbing hypothesis was wrong** — reasoning arrives inside `content`, so the filter is the only control. Contact disambiguation solved in-session: the tool no longer picks one of four Bills and writes to him. **⚠ An artifact was published off-machine unasked** — `Artifact`/`WebFetch`/`WebSearch` now denied. `## Later` 41 → 39, file **1,290 lines, down on the session** | **nothing — needs a deploy** |
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
