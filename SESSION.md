# Session Primer — Personal AI Life Manager

*Updated: 2026-08-18, later — **`/backlog attack`: three clusters shipped, and the VM turned out
to have been dying and restarting unnoticed.** Placeholder contact details refused across every
field (`8c7121b`); `tools/contacts_import.py` for CSV/vCard (`5c3bb3b`); `fetch_rendered`, a
read-only headless-browser fetch behind the same boundary as `fetch_url` (`6097c44`). All
registered and granted — **NOT deployed: `./deploy.sh` aborted on the VM and was not re-run; VM sits at `2a51f46`.** Sizing the browser found three `Out of memory:
Killed process` entries — one killed the server itself at 3.6 GB RSS, masked by `Restart=always`.
The VM now has 2 GB swap, a 5-minute watchdog (which caught the existing kill on its first run),
and Playwright proven at **~189 MB** per page against a 700 MB pre-flight refusal. Disk went 76% →
**75% having gained both**. `## Now` is **2 items**.*

*⚠ **Two lessons the next `attack` should carry.** Disjoint file manifests prevent *file*
collisions and nothing else — clusters A and B passed alone and failed 7/17 merged, because one
wrote fixtures the other had just learned to refuse. And **`[DB-0810-17]` re-proposed the Google
Contacts OAuth path Mike reversed on 2026-08-08**: verifying the code claim was not enough, because
a thing removed on purpose and a thing never built look identical in the current tree. Full
narrative: `archive/log/2026-08-18-01-backlog-item-hid-a-reversal.md`.*

*Prior session (parallel window) — **the knowledge layer is wired, deployed, and its plan is
closed**: derived manifest, `KNOWLEDGE_TO_LOAD` pre-fetch in both pipeline paths, `WISDOM_PROPOSAL`
parsed in Python, `health_notes` retired. **The zero-specialist path does not fire, by decision** —
`coordinator.md:48` stays dominant because over-dispatch costs tokens and under-dispatch loses a
user's record. Detail: `archive/PROJECT_LOG.md` § 2026-08-18.*

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

**A9 — Product analytics instrumentation — NEW 2026-08-18, and it is now an Alpha gate
requirement.** Mike: *"measure and quantify usage FROM THE START."* That is sequencing, not a
feature — Section 3 defines Alpha as when accumulation begins, so anything added later leaves the
least-recoverable weeks unmeasured. **Collection largely exists** (`core/trace.py` already records
agent path, per-turn tokens, tool calls, `is_proactive`); what is missing is a question set and a
durable daily rollup. **Spec: [ROADMAP.md](ROADMAP.md) § A9**; tracked as `[DB-0818-03]`, which
opens with a decision, not a build. Independent of A7/A8 — buildable now.

**A8 — Pre-Alpha code refactor** — gated on A7. Module extraction from
`core/orchestrator.py` and `core/server.py`. **Full spec, including the regression gate, is in
[ROADMAP.md](ROADMAP.md) § A8** — not restated here, it was a duplicate copy.

**Four built-and-standing constraints must not be undone** — outbound messaging is
Relationships' alone; tone profiles ship with `tone_shape` deliberately absent from
`write_contact`'s schema; obligations are data, not jobs; scheduler maintenance jobs live in
`core/scheduler.py`, never a persona file. **Full statements and the reasoning for all four:
`archive/PROJECT_LOG.md`** — they have not changed in three sessions, so they are reference now,
not current state.

**`[DB-0808-17]`** (A4 clinical hard-fails never run on Flash-Lite) exposes a wording gap in
`ROADMAP.md` § A7 check 8 — routing stays as-is by decision; the test gap is the open item.

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
| 08-18 | **`/backlog attack` — three clusters, and a VM that had been OOM-killing itself.** CRM placeholder guard widened to phone/address/social/name; `contacts_import` (CSV + vCard); `fetch_rendered` with three memory guards. **Mike's "let Playwright die first" plan was half right** — the kernel kills the *largest* process (the server, proven 08-15 15:02) and SIGKILL returns no message, so the polite refusal had to move *before* launch. VM gained swap, a watchdog and Playwright. **`[DB-0813-02]` was misdiagnosed**: the GPT key was valid, the MCP `env: {}` was empty — a rotation would have closed it and left GPT silent | `8c7121b`, `6097c44`, `5c3bb3b`, `4d10cbd`, `fa4d200`, `35499af`, `b62bb18` — **NOT deployed, deploy aborted** |
| 08-18 | **Knowledge layering wired, deployed, plan closed.** Steps 4–12: derived manifest, `KNOWLEDGE_TO_LOAD` pre-fetch in both pipeline paths, `WISDOM_PROPOSAL` parsed in Python, grants in parity, seven agents that were instructed to read the store and granted nothing. Step 10 run on the VM; `health_notes` retired. **The zero-specialist path was abandoned rather than tuned for** — the counter-test exists to stop exactly that trade. Found by running it: two turns wrote an *intention* as standing fact; a key-based duplicate check missed a placeholder holding the same fact; Mac and VM `sarah_chen` stores had diverged 38 vs 1 | `360b843`, `d128130`, `7cb9ebd`, `2a51f46` — **deployed, A4 3/3** |
| 08-15 | **Knowledge layering phase 1 — the wisdom store gains a subject axis.** The store already existed and was almost unreachable: six agent files instruct `read_wisdom` and are not granted it, and `write_wisdom` silently coerced unknown categories, so every Big Five entry MW ever wrote was misfiled. `category` → `domain` + `provenance`; alias map with a *measured* fuzzy cutoff; refusal never terminal, because the Diarist writes from a discarded-output thread. Found while building: **no lock on a read-modify-write** (40 concurrent writes kept 2), and **`vertex-key.json` neither tracked nor gitignored**. Migration heuristics failed on live data ("eat" inside "weather"), so all 59 entries were assigned by hand — which found 24 that do not belong in the store, including the placeholder `oatmeal_formula` | `13134bc`, `a35acfa` — **deployed + migration applied** |
| 08-15 | **Bulgarian speech-in benchmarked, held indefinitely.** `WHISPER_MODEL_SIZE=base.en` is English-only, cannot emit Cyrillic; `base` (multilingual) gets right script at 46.4% WER, `small` gets 27.6% WER but near-real-time RTF (0.967) on the single-worker pool. Neither clears the bar — Mike's call to hold `[DB-0815-02](a)` in `## Later` indefinitely | none — benchmark + backlog note only, **not deployed** |
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
