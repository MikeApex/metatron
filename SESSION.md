# Session Primer — Personal AI Life Manager

*Updated: 2026-08-18 — **the knowledge layer is wired, deployed, and its plan is closed.** Steps
4–12 of `~/.claude/plans/to-be-clear-we-modular-knuth.md` shipped (`360b843`, `d128130`,
`7cb9ebd`, `2a51f46`): a derived manifest naming which subjects are on file, `KNOWLEDGE_TO_LOAD`
pre-fetch in **both** pipeline paths, `WISDOM_PROPOSAL` parsed in Python, grants in parity, and
`config/modules/knowledge_domains.yaml` as the only coupling between subjects and the roster.
Step 10 ran on the VM: Mike's `health_notes` is now `standard_breakfast`/`food`, out of every
head-layer prompt, and `health_notes` is retired from `tools/profile.py`. **A4 pipeline 3/3
after.** Gate: `tests/run_knowledge_routing.py` (self-seeding, refuses `mike`).*

*⚠ **The zero-specialist path does not fire, by decision.** "Thinking about changing up
breakfast" reaches the stored fact but still dispatches Physical Health — twice, the second time
after a worked example that changed nothing and was reverted. `coordinator.md:48` mandates
dispatch for advice and is **deliberately left dominant**: over-dispatch costs tokens,
under-dispatch loses a user's record. Pass A now gates retrieval, not the skip. Reopen only with
a way to prove Pass B survives the change — reasoning is in the test docstring.*

*Two things the next session should not re-derive. **A key-based duplicate check is not
evidence** — step 10's dry run reported no collision while the same fact sat under
`oatmeal_formula`; `find_related_wisdom()` exists because of it, and **semantic similarity was
measured and rejected** (0.484 duplicate vs 0.479 nuance — indistinguishable). **The Mac and VM
persona stores diverge silently**: `sarah_chen` held 38 entries on the Mac and 1 on the VM. Both
migrated; the Mac's 38 → 19 after consolidating a 20-entry deflection cluster.*

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
| 08-18 | **Knowledge layering wired, deployed, plan closed.** Steps 4–12: derived manifest, `KNOWLEDGE_TO_LOAD` pre-fetch in both pipeline paths, `WISDOM_PROPOSAL` parsed in Python, grants in parity, seven agents that were instructed to read the store and granted nothing. Step 10 run on the VM; `health_notes` retired. **The zero-specialist path was abandoned rather than tuned for** — the counter-test exists to stop exactly that trade. Found by running it: two turns wrote an *intention* as standing fact; a key-based duplicate check missed a placeholder holding the same fact; Mac and VM `sarah_chen` stores had diverged 38 vs 1 | `360b843`, `d128130`, `7cb9ebd`, `2a51f46` — **deployed, A4 3/3** |
| 08-15 | **Knowledge layering phase 1 — the wisdom store gains a subject axis.** The store already existed and was almost unreachable: six agent files instruct `read_wisdom` and are not granted it, and `write_wisdom` silently coerced unknown categories, so every Big Five entry MW ever wrote was misfiled. `category` → `domain` + `provenance`; alias map with a *measured* fuzzy cutoff; refusal never terminal, because the Diarist writes from a discarded-output thread. Found while building: **no lock on a read-modify-write** (40 concurrent writes kept 2), and **`vertex-key.json` neither tracked nor gitignored**. Migration heuristics failed on live data ("eat" inside "weather"), so all 59 entries were assigned by hand — which found 24 that do not belong in the store, including the placeholder `oatmeal_formula` | `13134bc`, `a35acfa` — **deployed + migration applied** |
| 08-15 | **Bulgarian speech-in benchmarked, held indefinitely.** `WHISPER_MODEL_SIZE=base.en` is English-only, cannot emit Cyrillic; `base` (multilingual) gets right script at 46.4% WER, `small` gets 27.6% WER but near-real-time RTF (0.967) on the single-worker pool. Neither clears the bar — Mike's call to hold `[DB-0815-02](a)` in `## Later` indefinitely | none — benchmark + backlog note only, **not deployed** |
| 08-15 | **`/backlog deep` — the correction signal was measuring itself wrong twice over.** 93 of 174 `USER_CORRECTION` events said only "None" (a template slot a model fills rather than omits — the agent file was left alone on purpose), and a `×N` was a *chain length*, not a repeat count: a chain of Heathrow corrections was reported as "calendar events imply completion ×16". Both fixed; historical events filtered at read, never deleted. CRM gained `merge_contacts` (archive-on-merge, first here) — **and being registered was not enough, it was granted to no agent.** Machine log had no *removal* step at all: 22 cleared, 8 ⚠ → 3. `fold_fragments()` was miscounting prose fragments as `0 inbox` | `6e57c73`, `2fa8cd6`, `704e79b`, `214a547`, `19cfd12` — **deployed** |
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
