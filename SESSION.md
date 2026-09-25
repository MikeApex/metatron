# Session Primer — Personal AI Life Manager

*Updated: 2026-09-24 (**Build v4 — phases 0, A and B-Red committed**). Build is development, not
execution (Mike): it runs in Claude Code on the Mac on the subscription, Mike starts each build,
approves the plan, commits and deploys; Vertex serves only execution. Plan:
`archive/plans/build_vertical_plan_2026-09-24.md` **v4.11** — it owns the thirteen § 0 rulings, the
sequencing (§ 16), the cost ($65–106) and the kept/changed/deleted list (§ 10). Reasoning, options
rejected, and four things believed true that were not: `archive/PROJECT_LOG.md` § 2026-09-24, third.*

***Phase E is DEPLOYED — the VM ran `7bca654` → `4f0a6c3` on 09-25, 33 commits, 130 files. Build is
live.*** Six probes pass: read door answering five real sources with the live feeds refusing,
`build_tick` resolving, the `--persona mike` turn (**closes A's (M)**), the host marker as a systemd
drop-in, and `request_build`'s plumbing end to end (`BLD-0925-01` plus its `BUILD_PROPOSED` record).
**The seventh fails and it is the vertical's premise:** asked a shape-2 gap — *"when did I last water
the fig?"*, a last-done date nothing performs — the Coordinator answers from context and files
nothing. `4f0a6c3` moved the trigger into the procedure it executes; **deployed, asked again, still no
ticket, so placement was not the cause. It **correctly refuses** when it holds nothing, though — asked
about orchids it had no record of it asked what to track (Mike, 09-25), so the defect is narrow: it
over-reaches only where a partial history exists.** ***Next: phase F1, bootstrap run 1 `home_care`*** —
prompt in `…build_v4_phase_prompts_2026-09-24.md` § Phase F1, scoped to run 1 alone because a first
end-to-end run finds defects, and going ahead **without** § 12's under-filing fixture on Mike's call,
which it records rather than skips. Spend ≈ **$75–100** of $65–106; the rest is outside § 14.*

***Earned three times in one session, and the reason Build cost what it did:* a thing that reads
correctly and has never been run is not known to work — reading it harder will not find it.** The
three instances, and what each cost: `archive/PROJECT_LOG.md` § 2026-09-24, fifth.*

***The graph is four layers now** (Mike, 2026-09-24): Coord → ~12 category agents, which route and
no longer do → tier-3 agent → Synthesizer. Build exists to construct the tier-3 agents; the category
files are emptied by hand at rollout. **The trigger and the guard are already in:** `request_build`
granted to the eight personal specialists in both routing files, `tools/subagent.py` depth-aware
(`MAX_SUBAGENT_DEPTH = 2`). `run_subagent` is **not** granted, and the eight hold the tool with no
filing instruction until rollout — the 16 **class-3** advisories in `check_agent_tools.py` are that
marker. What v3.7 deferred and what phase D corrected: `archive/PROJECT_LOG.md` § 2026-09-24.*

*Headset mode is built, device-tested, committed and **deployed 09-25** — turns now record whether
they began in the UI or from a headset press. Barge-in parked; browser `[DB-0919-01]`. Detail:
`archive/PROJECT_LOG.md` § 2026-09-24 (headset).*

*⚠ **Vertex starts storing every prompt prefix at rest for 24h on 2026-10-15** — conversation history
included — unless the opt-out lands. Mike ruled 09-25: decline it. Google's command cannot run yet
(`retentionConfig` is absent from the live API), so it is a dated chore: `[DB-0925-01]`, due 10-08.*

*Standing rules, each earned twice and both invisible to `qa_sweep`: **a test that exercises a seam
for real must stub every live meter it ends in**, and **a live gate run dirties TRACKED
fixture-persona files** (`data/personas/danny_park/…`) — `git checkout HEAD --` them before
generating a patch.*

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

**BUILD — the vertical that constructs capabilities. v4.12; every phase committed and E DEPLOYED
09-25 (`505b254` … `4f0a6c3`); F left.** **The open defect is judgement, not machinery:** the
Coordinator will not file a shape-2 gap, proven twice on the live VM, and moving the instruction into
its procedure did not change it. **The next step is a measurement, not a prompt** —
`tests/run_b1_redteam.py` already runs live through `run_pipeline_session()`, so a `--suite
build_trigger` with must-file and must-not-file halves is the fixture
`config/modules/routing_cloud.yaml:66` claims exists and never did. Full account:
`archive/PROJECT_LOG.md` § 2026-09-25, second.** Plan:
[archive/plans/build_vertical_plan_2026-09-24.md](archive/plans/build_vertical_plan_2026-09-24.md)
— it owns the rulings, the sequencing, the cost and the kept/changed/deleted list; this line is
the status, not the record. **Live surface:** `core/build/` (17 files), **398 checks across fourteen
suites**, six content gates including the **tier gate** — which refuses a capability making a
standing judgement over a history on the bulk tier — the read doors, and `/build` taking every step
from `core/build/driver.py` so it can hand out none the driver refuses. **What each phase landed, in
detail, and the deleted 19-module package: `archive/PROJECT_LOG.md` § 2026-09-24** (five entries) —
moved out of here 09-25 at the ceiling. Per-phase prompts, including E's deploy checklist:
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
