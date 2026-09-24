# Session Primer — Personal AI Life Manager

*Updated: 2026-09-24 (**Build v4 — Build moves into Claude Code, plan reviewed clean by two
models**). Build is development, not execution (Mike): it runs in Claude Code on the Mac on the
subscription, Mike starts each build, approves the plan, commits and deploys; Vertex serves only
execution. Plan: `archive/plans/build_vertical_plan_2026-09-24.md` **v4.11**, superseding v3.7
and the 09-17 v2 entirely — thirteen rulings in § 0, ten review rounds (Opus ×7, cold Fable ×3)
to a clean pass, both review files beside it. `core/build/` is **rebuilt with salvage**, the
overlay retired. Model rule changed generally: **plan in Opus, review in Fable, build in Opus**
(`docs/WORKFLOW.md`). Reasoning, options rejected and what the reviews overturned:
`archive/PROJECT_LOG.md` § 2026-09-24.*

*⚠ **Phase 4 is UNCOMMITTED in this tree, by instruction** — `core/build/{runner,brief,registry,
coherence}.py`, `tools/build.py`, `scripts/build_{board,brief}.py`, four test files, edits to
`core/{actions,orchestrator,scheduler,build/jobs,build/schemas}.py` + `scripts/sync_dev_backlog.py`,
**the plan's v3.5–v3.7 corrections, and all three review rounds' fixes** (`manifest`, `probe`,
`writer`, `logger`, `turn_referent` among them) — so a fresh clone still reads the plan at v3.4
until Mike commits. **`tools/turn_referent.py` is not a phase-4 file and changes every ordinary
user turn** — the referent block now skips a tick and a Diarist trace; it ships WITH phase 4. **The same tree carries the headset-mode chat's uncommitted changes** (`.gitignore`,
`android/**`, `scripts/{check_apk_sync.sh,renew_cert.sh}`, `tests/test_turn_source_marker.py`,
`DEV_BACKLOG.md`); `git diff` each file before staging. The close-out (this file + the log) went
offsite on its own.*

*⚠ **A test suite wrote into two live meters and tripped the daily spend stop** — fixed, and
`(M)`: **`rm data/personas/mike/traces/2026-09-19.jsonl` on the Mac**, 112 fake records, all of
them this session's. The path is Denied so nothing here can touch it. The spend file was moved
aside and local sessions are unblocked. Rule now in the suite: **a test that exercises a seam for
real must stub every live meter that seam ends in.**

***Next: Build v4 phase 0 — Mike commits the phase-4 tree as the record, then the coordinating
window*** (paste `archive/plans/build_v4_walkthrough_prompt_2026-09-24.md` into a new Opus 5
window, effort xhigh). It writes the per-phase prompts (0, A, B, B-Red, D, C, E, F) for separate
windows. **The two v3 build windows are abandoned** — capture their transcripts, then close. Still
owed: **three commits and one deploy** — `0e154b9` (09-09 invitation wording), the 09-10 `tools/`
change, and `12d7dd2` (phase 3); the VM is at `b2b1dc7`. v4 phases 0–D deploy together at E.*

*Also ready to build, separately: **the headset-button plan** (Opus 5) — cleared by
`/adversarial-review`'s first live use, third `verify` round clean. Hand the build chat the plan
(`~/.claude/plans/for-the-metatron-app-modular-meerkat.md`) and
`archive/plans/adversarial_review_for-the-metatron-app-modular-meerkat_2026-09-19.md` together.*

## ⛔ Do not re-open — settled, with its evidence elsewhere

**This is an INDEX, not the record.** Each line is a ruling a session would otherwise re-derive
or re-propose; the reasoning lives in the file named beside it and is read on demand. Compressed
from eight full paragraphs on 2026-09-19, when the primer crossed both its ceilings and its own
note said the next addition must move a section out — the content did not change, it went back to
the homes each paragraph was already pointing at.

| Settled | Where the reasoning is |
|---|---|
| **Real calendar guest management → Mark 2** (Mike, 09-09). Do not re-propose against the Mark 1 CalDAV path — it is an integration change, not a patch | `DEV_BACKLOG.md` § Inbox, which holds the OAuth route and the 7-day refresh-token measurement |
| **Alpha ships on Mark 2** (Mike, 09-02), and the **Darwin API key `[DB-0818-04]` folded into it** (09-04) — not a standalone (M). `ROADMAP.md` still reads as though A8 is live; **Mike updates that manually, it is not an oversight** | `archive/plans/mark2_endeavour_plan_2026-09-02.md` (sequencing, gates, cost) · `archive/plans/code_dominant_rebuild_notes.md` (architecture) |
| **A4 safety testing SUSPENDED** (before-Alpha is the only clock) and **ZDR refused** | `ROADMAP.md` § Section 0 — both, in full |
| **The intake extractor is parked permanently** (priced out, not disproven); teaching `rules:` tops out at 11/33 because **a sender is not a category** (Mike). Successor `[DB-0905-01]` reads correspondence **as code, never a model judgement** | `DEV_BACKLOG.md` `[DB-0905-01]` · `archive/backlog_closed_2026-09.md`. **Do not re-derive** |
| **No off-machine backup** — Mike declined a date twice. A recorded acceptance of a named risk, not an unfiled worry; **do not re-raise** | this line is the record. `VERTEX_CACHE_DISABLED` ON on the Mac since 09-05 (net **+$0.94**/14d) |
| **Two items closed 09-05 as "skip, no backlog item"** — the calendar occurrence-vs-series gap, and the 2:44 check-in's conduct. **Do not file them** | `archive/log/2026-09-05-06-horizon-gate-and-two-guards-that-lied.md` |
| **Items closed 09-05 are not to be re-raised** | `archive/backlog_closed_2026-09.md`, their only home |

**Open, and each owned by its id — the sync's `⚠ due:` line is the live list, not this table.**
Inviting to N events is N approval cards and the one-call-per-event rule did not hold on its
first live run; `logistics.md` now states how many approvals are coming, batching was not built.
Thread expiry owes **one observation, not a deploy** — birthdates surviving Metatron's own
rewording in `context_audit.jsonl` (`[DB-0814-02]`). B4's max-chain-depth needs the 3-round limit
in code first (`[DB-0804-02]`). Mike's 09-07 auto-invite rule sits untriaged in the Inbox.

**Ceilings owed:** `CLAUDE.md` 300/300 · `.claude/rules/deploy.md` 131/100. This file's own count
is deliberately not written here, because restating it changes it.

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
[docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md). For which command to fire and when — **and
which model runs which kind of session** (plan in Opus, review in Fable, build in Opus — Mike,
2026-09-24; Red never delegated): [docs/WORKFLOW.md](docs/WORKFLOW.md). None of the three is loaded by
`/metatron-code`.

---

## Current state — Phase 5 (close)

**Phase 5 intent:** Coordinator Agent + Specialist Modules

### Built
**The Phase 5 catalogue moved out on 2026-09-18 — it was finished work, and a primer holds state.**
What exists: [CODEBASE_INDEX.md](CODEBASE_INDEX.md). When and why each piece was built:
[archive/PROJECT_LOG.md](archive/PROJECT_LOG.md). Everything through 2026-09-03 is deployed.

### In progress / next

**A7 — Phase 5 sign-off — BLOCKED on B1 alone.** A1–A6 complete, Track B2 built, B1a passing.
**Checks 10 and 12 are SKIPPED and A8 is CANCELLED** (Mike, 2026-09-02 — both fold into Mark 2;
`ROADMAP.md` § A8 still reads as live, Mike updates it manually — do not start it). Genuinely
left: B1b's calendar, web-page and CardDAV rows (gated on Track E), A5b/A5c, and B4's
max-chain-depth `[DB-0804-02]`. **Per-item detail and the standing evidence are in
[ROADMAP.md](ROADMAP.md) § Track A/B, which owns them** — including the attached-files row's
one-case-not-a-suite caveat. This line is the status, not the record.

**A9 — built and deployed 2026-08-18; `@waiting` on real use, review `2026-10-01`.** Spec, the
five provisional parts and the date: [ROADMAP.md](ROADMAP.md) § A9a, the single home.

**BUILD — the vertical that constructs capabilities. v4.11, 2026-09-24, reviewed clean; phase 0
next.** Plan: [archive/plans/build_vertical_plan_2026-09-24.md](archive/plans/build_vertical_plan_2026-09-24.md)
— it owns the rulings, the sequencing (§ 16: 0, A, B, B-Red, D, C, E, F), the cost ($65–106) and
the kept/changed/deleted list for phases 1–4 (§ 10); this line is the status, not the record.
Built under v3 and still in the tree, uncommitted: `core/build/` (19 modules), `tools/build.py`,
`scripts/build_{board,brief}.py`, twelve suites — phase 0 commits them as the record, phase A
salvages what § 10 names and deletes the rest. Nothing deploys until E. The coordinating-window
prompt: [archive/plans/build_v4_walkthrough_prompt_2026-09-24.md](archive/plans/build_v4_walkthrough_prompt_2026-09-24.md).

---

## Useful context to pull as needed

**[CODEBASE_INDEX.md](CODEBASE_INDEX.md) answers "where is X".** It already indexes every agent
file, every tool, `config/modules/routing*.yaml`, `archive/security/`, `tests/`, and
`archive/plans/future_phases.md` — the lookup table that sat here restated eleven of its rows and
was cut on 2026-08-14. The three docs pointers it does not own are in **Read these** above.

One row survived, because no other file carries it:

| Question | Where to look |
|---|---|
| Agent enhancement backlogs | **[AGENT_ENHANCEMENTS.md](AGENT_ENHANCEMENTS.md) at the project root — the only copy**, one section per agent. Moved out of the agent files 2026-08-27 (they were shipping to the model in every prompt); the `DEV_BACKLOG.md` and roadmap mirrors were deleted 2026-08-03. Do not re-add these sections to `config/agents/*.md` |

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

## Model IDs (updated 2026-09-01)

| Provider | Model | ID | Notes |
|---|---|---|---|
| Anthropic | Sonnet 5 (orchestrator fallback) | `claude-sonnet-5` | Only used inside `run_model_conference`'s unused `anthropic` branch — not on the live routing path (cloud/local routing is all Gemini/Ollama). Bumped 2026-07-27 from `claude-sonnet-4-6`. |
| Anthropic | Opus 5 (`ask_claude` MCP alias `opus`) | `claude-opus-5` | Added 2026-07-27 — new Anthropic release, matches Fable-5-tier capability at half price. `opus-4-8`/`opus-4-7` kept as pinned aliases in `~/.claude/mcp_servers/ask_claude.py`. |
| OpenAI | o3 | `o3` | |
| Gemini | Flash-Lite (bulk tier) | `gemini-3.5-flash-lite` | ✓ live 200 on Vertex `global` 2026-09-01 (no `models/` prefix on Vertex). Replaced `gemini-3.1-flash-lite`, which was deprecated. |
| Gemini | 3.8 Flash (reasoning tier) | `gemini-3.8-flash` | ✓ live on Vertex `global` **and** the Developer API, both confirmed by real call 2026-09-04. Replaced `gemini-3.7-flash` across all six reasoning slots. Same price as 3.7; cache floor re-checked and unchanged. |
| Gemini | 3.7 Flash (superseded 2026-09-04) | `gemini-3.7-flash` | No longer routed. Kept in `spend_guard.yaml` pricing so historical traces still reconcile, and pinned as `3.7flash` in the `ask_gemini` MCP. |

> **A catalogue listing is not availability — and "not available" is a dated observation, not a
> standing fact.** `gemini-3.8-flash` returned `200 GA` from the Vertex **catalogue** and `404`
> from `generateContent` on `global` on 2026-09-01; on 2026-09-04 it answered a live call on both
> Vertex and the Developer API, three days later. So confirm with a live call before wiring a
> model in — **and re-confirm before writing one off.** `gemini-3.5-pro` remains catalogue-only.
> `scripts/check_model_availability.py` does both, **weekly** (monthly until 2026-09-04).

**Vertex note:** AI Studio uses `models/gemini-*` prefix; Vertex drops the prefix. The orchestrator strips it automatically when `GOOGLE_CLOUD_PROJECT` is set.

---

## Key design decisions

**The only list is [CLAUDE.md](CLAUDE.md) → Key Design Decisions.** *(Why this file no longer
carries a second: `archive/PROJECT_LOG.md` § 2026-08-03.)*
