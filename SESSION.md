# Session Primer — Personal AI Life Manager

*Updated: 2026-09-19 (**Build phase 3 reviewed three times — twelve findings, all fixed**). The
§ 14 second-model review came back in three parts: six defects, then five, then one. All are
closed, and the shape is the finding — **each round's defect class was the previous round's fix**:
prose never made mechanism, then mechanisms scoped to the probe that prompted them, then a
mechanism improved in only one of its two homes. None of the 61 checks passing at submission had
caught any of them, because each test was written by the reasoning that wrote the defect. Suites
now 36/23/19 plus 117 from phases 1–2; `qa_sweep` 11/11. **Mike committed the phase as
`12d7dd2`** — tree clean, and this close-out's push carries it offsite. Detail, and the two things
deliberately NOT changed: `archive/PROJECT_LOG.md` § 2026-09-19.*

***Next: Build phase 4 (runner, brief, registry, coherence, wiring; the `_DEFAULT_JOBS` entry is
Red).*** Still owed: **three commits and one deploy** — `0e154b9` (09-09 invitation wording), the
09-10 `tools/` change, and `12d7dd2` (phase 3); the VM is at `b2b1dc7`. Build phases 1–6 deploy
together, so they add nothing to that debt. No Mike-gated session queued; phase 7 becomes one
once phases 3–6 land.

*⛔ **Real calendar guest management is deferred to Mark 2 (Mike, 2026-09-09) — do not re-propose
it against the Mark 1 CalDAV path.** The OAuth route and the 7-day refresh-token wall that makes
it an integration change rather than a patch: `DEV_BACKLOG.md` § Inbox, which holds the
measurement.*

*⚠ **Inviting to N events is N approval cards, and the one-call-per-event rule did not hold on
its first live run** — two of the seven were the same event on the same UID. `logistics.md` now
says to state how many approvals are coming; batching them into one was not built and is a real
change if wanted. Mike's standing rule from 09-07 — auto-invite Iva to external events — sits
untriaged in the Inbox.*

*⚠ **Two items Mike closed as "skip, no backlog item" on 09-05 — do not file them.** The
calendar occurrence-vs-series gap, and the 2:44 check-in's conduct. Both stated in full in
`archive/log/2026-09-05-06-horizon-gate-and-two-guards-that-lied.md`.*

*⚠ **The intake extractor is parked permanently (priced out, not disproven) and teaching
`rules:` tops out at 11/33 — because Mike ruled that a sender is not a category.** Successor is
`[DB-0905-01]`, a research gate reading prior correspondence **as code, never a model judgement**.
**Evidence: `DEV_BACKLOG.md` `[DB-0905-01]` and `archive/backlog_closed_2026-09.md`. Do not
re-derive it here.***

*⚠ **No off-machine backup — Mike declined a date twice; a recorded acceptance of a named risk,
not an unfiled worry. Do not re-raise it.** `VERTEX_CACHE_DISABLED` was flipped ON on the Mac
2026-09-05 (billing export: net **+$0.94**/14d).*

*⛔ **Two settled rulings — do not re-open; both in `ROADMAP.md` § Section 0.** A4 safety testing
is SUSPENDED (before-Alpha is the only clock); ZDR is refused.*

*⚠ **The inversion is decided: Alpha ships on Mark 2 (Mike, 2026-09-02).** Architecture thinking
stays in **`archive/plans/code_dominant_rebuild_notes.md`**; sequencing, gates and cost in
**`archive/plans/mark2_endeavour_plan_2026-09-02.md`**. **The Darwin API key `[DB-0818-04]` was
deferred into Mark 2 by Mike on 09-04** — do not re-propose it as a standalone (M).
**`ROADMAP.md` is deliberately NOT updated and still reads as though A8 is live work** — Mike
handles that and the Mark 1 decommission condition manually. Known, not an oversight.*

*⚠ **Thread expiry is live and owes one observation, not a deploy** — confirm birthdates survive
Metatron's own rewording in `context_audit.jsonl` (fourth field `reworded`); first real expiries
were due ~09-15, status in `[DB-0814-02]`. Also open: B4's max-chain-depth needs the 3-round limit
in code first (`[DB-0804-02]`). **Every dated confirm in `## Now` has now fallen due — the sync's
`⚠ due:` line is the live list, not this paragraph.** Items closed 09-05 and not to be re-raised
are in `archive/backlog_closed_2026-09.md`, which is their only home. **`CLAUDE.md` is 300/300 and this file is AT its ceiling —
the next addition to either MOVES A SECTION OUT, and this file's own count is deliberately not written here because restating it changes it**; **`.claude/rules/deploy.md` is 131/100 and owes a pass.***

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
which model runs which kind of session** (plan/review in Fable, build in Opus; Red never
delegated): [docs/WORKFLOW.md](docs/WORKFLOW.md). None of the three is loaded by
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

**BUILD — the vertical that constructs capabilities. Phases 1–3 of 7 done, 2026-09-18.** Plan:
[archive/plans/build_vertical_plan_2026-09-18.md](archive/plans/build_vertical_plan_2026-09-18.md),
which owns the sequencing, the rulings and the cost — this line is the status, not the record.
Built: `core/build/` (14 modules, +`writer`/`overlay`/`constitution`/`verify`),
`scripts/check_build_registration.py` as `qa_sweep` check 11, `config/modules/build.yaml`, eight
suites (195 checks). **Next is phase 4** — runner, brief, registry, coherence, wiring. Nothing
deploys until phase 6. **Phase 3 is committed (`12d7dd2`), reviewed, and corrected to plan v3.4.**

> **Two things that change what phases 3–6 build, each owned by its own document.**
> **Phase 6 is now a prerequisite for run 1, not a convenience** — every compass question on run
> 1's own gap needs the unbuilt `search_conversations`:
> [build_worked_inquiry_home_care_2026-09-18.md](archive/plans/build_worked_inquiry_home_care_2026-09-18.md).
> And **Mike's § 15 rulings bind phases 3–5**, three of four overturning the proposal:
> [build_librarian_planner_parameters_2026-09-18.md](archive/plans/build_librarian_planner_parameters_2026-09-18.md).
>
> ⚠ **Build's `$2.50` per-job spend limit is a PLACEHOLDER and phase 7 must say so out loud before
> run 1 starts.** `cost.budget_notice()` carries the wording and self-clears once
> `budget.per_job_usd` is set in `config/modules/build.yaml`; **phase 4 owes the two call sites**
> (the runner, before a job's first node, and `build_board.py`'s header). It is a placeholder
> because the § 15 ruling removed the per-question reading ration, leaving this the only bound on
> a run's spend — set it from what run 1 actually costs.

**Four built-and-standing constraints must not be undone** (outbound messaging, `tone_shape`,
obligations-as-data, scheduler maintenance jobs) — **full statements and reasoning:
`archive/PROJECT_LOG.md`**; reference now, not current state.

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
