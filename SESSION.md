# Session Primer — Personal AI Life Manager

*Updated: 2026-09-24 (**Build v4 — phases 0, A and B-Red committed**). Build is development, not
execution (Mike): it runs in Claude Code on the Mac on the subscription, Mike starts each build,
approves the plan, commits and deploys; Vertex serves only execution. Plan:
`archive/plans/build_vertical_plan_2026-09-24.md` **v4.11** — it owns the thirteen § 0 rulings, the
sequencing (§ 16), the cost ($65–106) and the kept/changed/deleted list (§ 10). Reasoning, options
rejected, and four things believed true that were not: `archive/PROJECT_LOG.md` § 2026-09-24, third.*

***Next: phases B and D, and they may run SIMULTANEOUSLY*** — they share no file and both branch
from `224e5d4`. Complete, self-contained prompts are in
`archive/plans/build_v4_phase_prompts_2026-09-24.md`; hand a fresh Opus 5 window one and nothing
else. **B** = the read doors (`core/build/doors.py`, `scripts/vm_read.py`, the endpoint on
`core/server.py`; $8–12). **D** = `search_conversations` and `read_journal_range`, ordinary
development ($4–7). Then C (the five subagent definitions and `/build`), its `/adversarial-review`
in Fable, then E. **Nothing deploys until E — and E is 18 commits deep, not Build's**
(`b2b1dc7..HEAD`), so it is a catch-up deploy with Build inside it and its checklist must separate
the two before blaming Build for anything the VM then does. Spend ≈ **$29–42** of $65–106.*

***The graph is four layers now** (Mike, 2026-09-24): Coord → ~12 category agents, which route and
no longer do → tier-3 agent → Synthesizer. Build exists to construct the tier-3 agents; the category
files are emptied by hand at rollout. v3.7 § 2 specified this as "the tier", deferred to four leaf
capabilities — **the trigger and the guard were brought forward**: `request_build` is granted to the
eight personal specialists in both routing files, and `tools/subagent.py` is depth-aware
(`MAX_SUBAGENT_DEPTH = 2`). `run_subagent` is **not** granted yet, and the eight hold the tool with
no filing instruction until rollout — the 16 class-2 advisories in `check_agent_tools.py` are that
marker.*

*(M) **owed at phase E, not before: one pipeline turn on `--persona mike`, on the VM.**
`config/personas/mike*` is VM-only, so that turn cannot run on the Mac in **any** tree — phase A's
handoff said otherwise and was wrong. The `danny_park` substitute passed against the landed main
tree. Also riding E: `0e154b9`, the 09-10 `tools/` change, and `12d7dd2`.*

*⚠ **Headset mode is built, device-tested and committed (`3066d66`, `0b044f9`); one half owes a
deploy.** Hold a bud → "I'm here" → speak → silence sends → reply spoken; works screen-off in a
pocket. **The VM still runs the pre-`source` server**, so turns do not yet record how they
started — `core/{server,trace,orchestrator}.py` ride the next deploy. Hardware overruled the plan
twice: the buds emit play/pause on **hold**, and **the button is dead once the mic is open**
(A2DP → SCO), so silence ends a turn. Barge-in parked; desktop browser `[DB-0919-01]`. Detail:
`archive/PROJECT_LOG.md` § 2026-09-24 (headset).*

*⚠ **The VM's TLS cert expired 09-19 and took every client down while the server stayed healthy.**
Renewal is automated and proven (12 no-op runs). **`curl` WITHOUT `-k` is the diagnostic** — every
other check, `curl -k` included, said healthy. Runbook: `docs/INFRASTRUCTURE.md` § TLS certificate.*

*Standing rule, unpromoted and earned twice: **a test that exercises a seam for real must stub
every live meter that seam ends in** (a suite once tripped the daily spend stop) — and its
sibling, found in phase A: **a live gate run in a worktree dirties TRACKED fixture-persona files**
(`data/personas/danny_park/{context.json,memory/*}`; `.gitignore` does not untrack what was
committed before the rule). Both are invisible to `qa_sweep`; revert before generating a patch.*

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

**Open, each owned by its id — the sync's `⚠ due:` line is the live list, not this file.**
Batched invitations, unbuilt. Thread expiry `[DB-0814-02]`, owes one observation not a deploy.
B4 max-chain-depth `[DB-0804-02]`, needs the 3-round limit in code first. Mike's 09-07
auto-invite rule, untriaged in the Inbox. **Evidence for all four is in `DEV_BACKLOG.md`.**

**Ceilings owed:** run `python3 scripts/check_claude_md_claims.py` — it is the authority, and a
number copied here goes stale the next time anything is edited.

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

**A7 — Phase 5 sign-off — BLOCKED on B1 alone.** A1–A6 complete, B2 built, B1a passing. Checks 10
and 12 SKIPPED, A8 CANCELLED (Mike, 09-02 — both fold into Mark 2; `ROADMAP.md` § A8 still reads
as live and Mike updates that manually — do not start it). Left: B1b's calendar, web-page and
CardDAV rows (gated on Track E), A5b/A5c, `[DB-0804-02]`. **[ROADMAP.md](ROADMAP.md) § Track A/B
owns the per-item detail and the standing evidence.**

**A9 — built and deployed 2026-08-18; `@waiting` on real use, review `2026-10-01`.** Spec, the
five provisional parts and the date: [ROADMAP.md](ROADMAP.md) § A9a, the single home.

**BUILD — the vertical that constructs capabilities. v4.11; phases 0, A and B-Red committed
(`505b254`, `760c260`, `224e5d4`); B and D next and parallel.** Plan:
[archive/plans/build_vertical_plan_2026-09-24.md](archive/plans/build_vertical_plan_2026-09-24.md)
— it owns the rulings, the sequencing, the cost and the kept/changed/deleted list; this line is
the status, not the record. **What exists now:** `core/build/` is 17 files (16 modules +
`__init__`), 236 checks across eleven suites, sweep check 12 (`scheduler-functions-resolve`), a
rewritten `check_build_registration.py`, `--sandbox` on `new_worktree.sh`, six content gates —
the sixth being the **tier gate**, refusing a capability that makes a standing judgement over a
history on the bulk tier — and the trigger: `request_build` on the Coordinator and the eight
category agents, with the filing condition written by request shape in `coordinator.md`. The old
19-module package, its four load seams and eight suites are deleted. Per-phase prompts:
[archive/plans/build_v4_phase_prompts_2026-09-24.md](archive/plans/build_v4_phase_prompts_2026-09-24.md).

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
