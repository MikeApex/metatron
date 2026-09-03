# Session Primer — Personal AI Life Manager

*Updated: 2026-09-03 (**Session ⑥ ran — three bugs fixed, one rider built, one diagnosis
returned.** Commit `54073b6`, deployed and VM-verified; nothing owes a commit or a deploy.
**A declined email no longer survives in the log as sent `[DB-0829-01]`**; **the miss log no
longer fills with successes `[DB-0902-01]`**; **the two inbox jobs no longer disagree
`[DB-0902-02]`**; **the derived-facts line is built `[DB-0822-06]`**. Three of those corrected
the premise they were filed under, which is the part worth carrying: the false email record came
from the **fire-and-forget Diarist**, dispatched before the specialist that raised the confirm
gate — not from the specialist that watched it; the ROUTING_MISS break is **exactly the 09-01
fleet migration** (19 events before with 0 noise, 15 after with 13, no code change between) and
`coordinator.md` **never defines ROUTING_MISS at all**; the intake queue was **never filled, not
drained**. Suite 67/1, the one failure pre-existing and environmental (passes on the VM).
Evidence and measurements: `archive/sessions/2026-09-03 — Session ⑥ ...md` + the capstone
tracker's dated note.)*

***Next: ⑦ capstone remainder** (Fable — `[DB-0818-08]`, `[DB-0804-02]`'s buildable slice,
`[DB-0808-06]`) and **the (M)-walkthrough** (Fable — corpus labelling due 09-09, wisdom review,
Darwin key, zones+APK+ping, BigQuery, Restic); prompts in `archive/handoffs/2026-09-02-*`. **⑤
and ⑥ are done.** **The capstone closes at ⑦'s end; A4 re-run is OFF the close path**
(before-Alpha unchanged, ROADMAP § 0 pt 8). They still run because they make Mark 1 usable for
however long Mark 2 takes, and Mark 1's traces are Mark 2's regression oracle. CLAUDE.md is at
**307/300** and SESSION.md at **204/200**; the restructure is owed, Mike's call on what moves
out (⑦ checks it).*

*⚠ **The horizon build is live and inert — `[DB-0822-09]` does NOT close.** Both session-⑥ Red
proposals were built and deployed (`a4a9364`, Mike approved). The post-deploy test read as a
pass — Death Cab, Jimmy Carr, the dental appointment and the alumni social all reached Mike,
plus a calendar collision nobody asked for — **but the ledger file does not exist**: they
arrived by the Synthesizer's own compliance, through the same channel that failed on 09-02.
`logistics` **emitted no `HORIZON_ITEMS:` line at all**, returning conversational markdown with
none of its documented output format; on 09-02 the same agent on the same model emitted the
full block. **Format adherence varies run to run.** The Red edit made the schema precise (a
dedupe key cannot be pulled from prose — that part was right) and left the *emission* resting
on the model choosing to fill a template slot. **What closes it: make the relay a tool call**
(`record_horizon_item`) — structured by construction, the codebase's existing answer for relay
that must not be lost. Ledger, dedupe, block and both placement decisions are built and tested;
only the input path changes. Cost: one tool (Green) + a grant in both routing files and one
line in `logistics.md` (Red). **Mike's call — nothing else is owed on this item.**
`[DB-0902-01]`'s definition is live and that afternoon produced no ROUTING_MISS at all; its
week-long clock stands. **Standing fact:** the intake queue is empty by construction until
`[DB-0820-03]`'s corpus labelling runs (due 09-09).*

*⚠ **Found and deliberately NOT fixed — needs Mike's word. `quick_override` reaches the
clinical agents on the cloud path.** `core/router.py:98` reads "non-sensitive" as *no
`local: true`*, and `routing_cloud.yaml` marks **nothing** local — so its `:22` comment *"(non-
sensitive agents only)"* excludes nothing, and a `quick` call to `mental_wellbeing`/`physical_health`
runs on the **bulk** model. Pre-existing. Sharper now only because A4 is suspended.
(`./deploy.sh` never commits → moved 2026-09-03 to `docs/INFRASTRUCTURE.md` § the deploy
pipeline.)*

*✅ **The capstone plan is the read-first for any backlog work:**
**`archive/plans/capstone_cluster_review_2026-08-27.md`** — clusters, status, and the ruled
close path (its 2026-09-02 update is current state). **National Rail (`[DB-0818-04]`):** Darwin
key is Mike's to register. Geolocation (`[DB-0815-12]`): deployed; zones file + one ping owed.*

*⚠ **A tripped soft cap is the control working, not an outage** — recovery is a 60s VM start.
Cap numbers: `docs/INFRASTRUCTURE.md` § Billing protection, the only copy. Both owed (M)s
(BigQuery export, the `VERTEX_CACHE_DISABLED` flip) are items 5 and 7 of the (M)-walkthrough.*

*⛔ **Two rulings that are settled — do not re-open either; both live in `ROADMAP.md` § Section
0.** (1) **A4 safety testing is SUSPENDED** (Mike, 09-01) and its re-run is **off the capstone
close path** (09-02): the clinical flags are **unverified on 3.7 Flash** and stay so until the
**before-Alpha** run, now the only clock on it (pt 8, amended). (2) **ZDR is refused**, incl.
Amendment 2026-08-28. Still owed against these: the `[DB-0818-06]` wisdom-store proposal review
(Mike's), and the CRM sweep's first live morning digest as its confirm (built and deployed).*

*⚠ **No off-machine backup copy** — the daily backup is fixed and live-verified (fragment
2026-08-29-03), but the Restic external-drive job is not installed. Mike's call, unfiled.*

*⚠ **The inversion is decided: Alpha ships on Mark 2 (Mike, 2026-09-02).** Architecture thinking
stays in **`archive/plans/code_dominant_rebuild_notes.md`** (five rounds); sequencing, gates,
buckets and cost in **`archive/plans/mark2_endeavour_plan_2026-09-02.md`**. **`ROADMAP.md` is
deliberately NOT updated and still reads as though A8 is live work** — Mike handles that and the
Mark 1 decommission condition manually. Known, not an oversight.*

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
Coordinator–Synthesizer pipeline; all 14 agent files (deep passes + flag audit complete);
grounded Research search; CRM, Wishes, CalDAV, scheduler-write and profile tools; parallel
subagent dispatch; threat model and security backlog (`archive/security/`); **server auth,
`fetch_url`, `read_email`, and the `<untrusted_content>` boundary (2026-08-04)**;
**user-attached photos and documents, new-message alerts, and a waiting indicator (2026-08-20)**;
**the Coordinator's view of the previous turn (`[DB-0826-01]`) and the session-⑥ record-honesty
fixes — gated actions, the miss log, the inbox split, derived counts (2026-09-03)**.
*Dates and reasoning for all of it: [archive/PROJECT_LOG.md](archive/PROJECT_LOG.md).*

### In progress / next

**A7 — Phase 5 sign-off — BLOCKED.** A1–A6 complete; Track B2 fully built. The 2026-08-05
pre-sign-off gate cleared the *regression* gate on the cloud path (6/6 + pipeline 3/3), **not A7**.
Three checks still open:

- **B1** — red team. **B1a passed** (re-run 2026-08-08 post-filter-upgrade: 102 pass, 0 error,
  `tests/security_redteam_2026-08-08.md`). **B1b not closed** — email row covered (`injection`,
  3/3 vs `danny_park`); calendar, web and CardDAV rows untouched, gated on Track E. **A fifth row,
  attached files, opened and passed its first probe 2026-08-20** — live now, not gated on Track E;
  **one manual case, not a suite**, with its limits stated in
  `archive/security/b1b_attachment_injection_2026-08-20.md`.
- **Check 10** — agent behavioural audits. **SKIPPED by Mike's ruling 2026-09-02** — folds into
  Mark 2. It was the largest Mark-2-invalidated item on the board (8–12 hrs against agent files
  the rebuild discards). Remaining `@session:` decisions: `DEV_BACKLOG.md` § Later § Decisions.
- **Check 12** — constitution alignment review. **SKIPPED by the same ruling** — folds into
  Mark 2, where Tier 0 is unchanged.
- **A5b/A5c** — re-run `write_aspirational_baseline` with A5 mission-level data (A3 baseline is still a placeholder); A5c preference activation recorded "unknown, confirm if needed."

**A9 — Product analytics — FIRST DRAFT BUILT AND DEPLOYED 2026-08-18; review deferred.** Alpha
gate requirement. **The core metric is absorbed work, not engagement.** **Full spec, the five
provisional parts and the `2026-10-01` review date are in [ROADMAP.md](ROADMAP.md) § A9a** — the
single home, not restated here (duplicate copy cut 2026-08-29). `@waiting` on `mike` holding
goals and real data in ongoing use.

**A8 — Pre-Alpha code refactor — CANCELLED (Mike, 2026-09-02).** Refactoring
`core/orchestrator.py` into modules Mark 2 replaces is work paid for twice. **`ROADMAP.md` § A8
still reads as live** — Mike updates it manually. Do not start it.

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
| Gemini | 3.7 Flash (reasoning tier) | `gemini-3.7-flash` | ✓ live 200 on Vertex `global` 2026-09-01. **Replaced `gemini-3.1-pro-preview` — there is no Pro in the fleet.** The Flash and Pro lines desynced; 3.7 Flash outscores 3.1 Pro at a fraction of the cost. Introductory pricing ends 2026-12-31. |

> **Two models look available and are not.** `gemini-3.8-flash` and `gemini-3.5-pro` both return
> `200 GA` from the Vertex **catalogue** endpoint and `404` from `generateContent` on `global`.
> A catalogue listing is not availability — confirm with a live call before wiring any model in.
> `scripts/check_model_availability.py` does both, monthly.

**Vertex note:** AI Studio uses `models/gemini-*` prefix; Vertex drops the prefix. The orchestrator strips it automatically when `GOOGLE_CLOUD_PROJECT` is set.

---

## Key design decisions

**The only list is [CLAUDE.md](CLAUDE.md) → Key Design Decisions.** *(Why this file no longer
carries a second: `archive/PROJECT_LOG.md` § 2026-08-03.)*
