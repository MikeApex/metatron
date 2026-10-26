# Session Primer — Personal AI Life Manager

*Updated: 2026-10-26, sixth. **VM at `e5b895c`, all deployed.** **"Over and out" no longer drops
what the message asked** (`e5b895c`): the Synthesizer is skipped only for a bare sign-off; a
request, an answer, a question, a reported completion or more than 8 words runs it, with a
one-line reply. **Live check owed:** Mike's next real "…, over and out" request gets a one-line
confirmation and is done (log § 10-26, sixth). **Virtue review paused** to 2027-01-26 (`4e16f3c`)
— day-after check 10-27: no catch-up at 07:30, no virtues at 20:00. Replies no longer cut or blank
(8,192 ceiling; the thinking budget is a target, not a cap) — `[DB-1026-01]`, due 10-29.
(Silent-mic APK `24d5c24`: sideload if not yet done.) **Next:
`archive/handoffs/2026-10-27-day-planner-watch-2-and-stage-b-prompt.md`** — watch day 2 (Tue
10-27), then Stage B with Mike; its § 4 adds task durations (never asked — 0 of 59 stated) and
records that the gym habit is retired and the Sunday trash event is 19:00–19:10. **Stage B lands
second on both routing files and `synthesizer.md` — keep the `pause_routine` grants and line.**
The 10-25 ritual-pause handoff is fully consumed. **Still owed:** Mike's calendar live check
(week of 9 Nov — John Ball once, shared events present); the "Benny" contact may be a phantom
(new evidence he is real: continuation prompt § 3.6); `[DB-0901-02]`, due 12-15.*

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
| **The graph is four layers** (Mike, 09-24): Coord → ~12 category agents, which route only → tier-3 agent → Synthesizer. `request_build` granted to the eight, `run_subagent` not; the 16 class-3 advisories are the rollout marker | `archive/PROJECT_LOG.md` § 2026-09-24 |

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
[archive/PROJECT_LOG.md](archive/PROJECT_LOG.md). Everything committed is deployed (VM `e5b895c`).

### In progress / next

**A7 — Phase 5 sign-off — BLOCKED on B1 alone.** A1–A6 complete, B2 built, B1a passing. Checks 10
and 12 SKIPPED, A8 CANCELLED (Mike, 09-02 — both fold into Mark 2; `ROADMAP.md` § A8 still reads
as live and Mike updates that manually — do not start it). Left: B1b's calendar, web-page and
CardDAV rows (gated on Track E), A5b/A5c, `[DB-0804-02]`. **[ROADMAP.md](ROADMAP.md) § Track A/B
owns the per-item detail and the standing evidence.**

**DAY PLANNER — Stage A + round 2 deployed 2026-10-26; watch day 2, then Stage B, owed.** Synth
runs the user's day from a plan code keeps current. Built: the engine; ledger fields (goal link,
priority, stakes, zone, activity, monthly days — hidden until Stage B); the dynamic day shape
(`tools/day_shape.py`, design defaults in `config/modules/day_shape.yaml`, setup command); event
triage; the Plan section; nudge mode; every Synth-facing switch off. Stage B (one Red session):
agent file, routing, `answer_event` registration + grants, Synth/Coordinator/interviewer lines,
scheduler jobs, then the flags — nudges a day later; plus task durations made a code-raised ask
(handoff § 4, Mike 10-26). **Open decision D1 (Mike):** the APK has no
push, so nudges arrive only while the app is alive; recommendation native notifications as Stage
C. Plan: [day_planner_plan_2026-10-24.md](archive/plans/day_planner_plan_2026-10-24.md) — § 18 is
round 2.

**WHATSAPP INPUT — approved 10-26; Phase 0a done; next 0b + phone probes in a FRESH session**
(`archive/handoffs/2026-10-26-whatsapp-phase-0b-clean-room-and-probes-prompt.md` — the clean room:
never open the 10-26 WhatsApp transcripts, which hold GPL source). Then LM → second-user build →
Phases 1–3 ([plan](archive/plans/whatsapp_input_plan_2026-10-26.md)). Mike owes: delete the `/private/tmp` reference copy.

**A9 — built and deployed 2026-08-18; `@waiting` on real use, review `2026-10-01`.** Spec, the
five provisional parts and the date: [ROADMAP.md](ROADMAP.md) § A9a, the single home.

**BUILD — the vertical that constructs capabilities. v4.12; every phase committed, E deployed 09-25,
F1 run 1 started and stopped.** **The defect is not what it was thought to be:** *"the Coordinator
will not file a shape-2 gap"* is incompletely diagnosed — a daily `plant_watering_check` job and
Logistics' catch-all directory entry both already claim the class, so two config files conflict
(`archive/PROJECT_LOG.md` § 2026-09-26). The under-filing fixture
`config/modules/routing_cloud.yaml:66` asserts exists **still does not exist**. **Live surface:**
`core/build/` (17 files), **353 checks across fourteen suites**, six content gates including the
**tier gate** — which refuses a capability making a standing judgement over a history on the bulk
tier — the read doors, and `/build` taking every step from `core/build/driver.py` so it can hand out
none the driver refuses. Plan:
[build_vertical_plan_2026-09-24.md](archive/plans/build_vertical_plan_2026-09-24.md) — rulings,
sequencing, cost, kept/changed/deleted. Per-phase prompts, including E's deploy checklist:
[build_v4_phase_prompts_2026-09-24.md](archive/plans/build_v4_phase_prompts_2026-09-24.md).
*Unchanged since 09-26; development, not execution (Mike): he starts, approves, commits, deploys.*
F1 run 1's two defects (Inquiry named a retired agent; no path back from an artifact that validates
but is wrong): `archive/handoffs/2026-09-26-build-phase-F1.md`. **Next: `claude update` to ≥
2.1.271, restart, bench test 2** (`archive/plans/inquiry_rewrite_2026-09-26.md`) — **`omitClaudeMd:
true` is SILENTLY IGNORED below 2.1.271**, the one way bench test 2 could measure nothing.

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
