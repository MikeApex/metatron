# Session Primer — Personal AI Life Manager

*Updated: 2026-09-02 (**Red session ④ — the verification pass, Mike present.** Four live trace
days read; **seven items closed on evidence** (0822-05/08/10, 0809-02, 0827-01/07, 0809-21 —
the calendar dedupe executed live on the VM, six deletes verified), three held because the
evidence went the other way: **0822-06 reproduced post-fix** (stale hiatus state three ways
across three days — derived-facts line back on the table), **0822-09 failed its first live
test** (interest-level email never surfaced; legs generated one layer down), **0827-09 live
but unexercised** (clean 05:45 no-ops; first real leftover ~09-03/04). Inbox triaged 8 → 0,
the three @session items resolved, intake corpus parked `due: 2026-09-09`, the synthesizer
`source` line **declined forever**. Fragment 2026-09-02-01. Dev-context only — nothing owes a
deploy.)*

***Next: the two final capstone sessions — prompts staged, Mike-bound:**
**⑤ `archive/handoffs/2026-09-02-red-session-five-referent-prompt.md`** (Fable, Red, Mike
present — the `[DB-0826-01]` referent fix; re-run Suite B-hard first, the baseline predates the
fleet migration) and **⑥ `archive/handoffs/2026-09-02-code-session-three-bugs-prompt.md`**
(Opus — `[DB-0829-01]` + `[DB-0902-01]` + `[DB-0902-02]`, the `[DB-0822-06]` derived-facts
rider, the `[DB-0822-09]` surfacing diagnosis). **The capstone closes at ⑥'s end; A4 re-run is
OFF the close path (Mike, 2026-09-02 — before-Alpha unchanged, ROADMAP § 0 pt 8 amended).**
**Un-ruled, surfaced at close:** three items the plan listed and no session claimed —
`[DB-0818-08]` provenance (recommended into ⑥), `[DB-0804-02]` (→ Track B?), `[DB-0808-06]`
(postpone?) — Mike rules in ⑤/⑥; recorded in the capstone tracker's 09-02 amendment.*

*⚠ **Two things found and deliberately NOT fixed — both need Mike's word.** (1) **`quick_override`
reaches the clinical agents on the cloud path.** `core/router.py:98` reads "non-sensitive" as *no
`local: true`*, and `routing_cloud.yaml` marks **nothing** local — so its `:22` comment *"(non-
sensitive agents only)"* excludes nothing, and a `quick` call to `mental_wellbeing`/`physical_health`
runs on the **bulk** model. Pre-existing. Sharper now only because A4 is suspended. (2)
**`./deploy.sh` never commits** — it pushes and the VM pulls, so a "deploy complete" shipped
**nothing** until the work was committed. Say *"owes a commit, then a deploy"* in every handoff.*

*✅ **The capstone plan is the read-first for any backlog work:**
**`archive/plans/capstone_cluster_review_2026-08-27.md`** — clusters, status, and the ruled
close path (its 2026-09-02 update is current state). **National Rail (`[DB-0818-04]`):** Darwin
key is Mike's to register. Geolocation (`[DB-0815-12]`): deployed; zones file + one ping owed.*

*⚠ **Caps are $100/$175.** A heavy testing day tripping the soft cap is the control working;
recovery is a 60s VM start. Numbers live in `docs/INFRASTRUCTURE.md` § Billing protection, the
only copy. (M) still owed: BigQuery billing export, and flip the Mac's `VERTEX_CACHE_DISABLED`
with a measured payoff.*

*⛔ **A4 safety testing is SUSPENDED (Mike, 2026-09-01) and its re-run is OFF the capstone close
path (Mike, 2026-09-02).** The clinical flags are **unverified on 3.7 Flash** and stay so until
the **before-Alpha** run, the only clock left on it — `ROADMAP.md` § Section 0 pt 8, amended.*

*⛔ **ZDR: refused, ruled on, do not re-open** — the whole basis, incl. Amendment 2026-08-28,
is `ROADMAP.md` § Section 0. The `[DB-0818-06]` wisdom-store proposal review still awaits
Mike. CRM sweep: **built and deployed** — first live morning digest still owed as its confirm.*

*✅ **The daily backup is fixed and live-verified** (fragment 2026-08-29-03). **⚠ Still true:
no off-machine copy** — the Restic external-drive job is not installed. Mike's call, unfiled.*

*⚠ **The code-dominant inversion question is live and must be decided before A8 executes**
or A8 is paid for twice. Standing home, three dated rounds:
**`archive/plans/code_dominant_rebuild_notes.md`**.*

***Model split, Mike's call 2026-08-18: plan and review in Fable, build in Opus.*** Red-tier
work is still not delegated at all.

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
`fetch_url`, `read_email`, and the `<untrusted_content>` boundary (2026-08-04)**;
**user-attached photos and documents, new-message alerts, and a waiting indicator (2026-08-20)**.
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
- **Check 10** — agent behavioural audits (12 specialists; Coordinator/Synthesizer via pipeline probes). **Unblocked and runnable** since `[DB-0810-03]`'s grants landed (`bfbdbb5`); unrun. Remaining `@session:` decisions: `DEV_BACKLOG.md` § Later § Decisions.
- **Check 12** — constitution alignment review
- **A5b/A5c** — re-run `write_aspirational_baseline` with A5 mission-level data (A3 baseline is still a placeholder); A5c preference activation recorded "unknown, confirm if needed."

**A9 — Product analytics — FIRST DRAFT BUILT AND DEPLOYED 2026-08-18; review deferred.** Alpha
gate requirement. **The core metric is absorbed work, not engagement.** **Full spec, the five
provisional parts and the `2026-10-01` review date are in [ROADMAP.md](ROADMAP.md) § A9a** — the
single home, not restated here (duplicate copy cut 2026-08-29). `@waiting` on `mike` holding
goals and real data in ongoing use.

**A8 — Pre-Alpha code refactor** — gated on A7. Module extraction from
`core/orchestrator.py` and `core/server.py`. **Full spec, including the regression gate, is in
[ROADMAP.md](ROADMAP.md) § A8** — not restated here, it was a duplicate copy.

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
