# Session Primer — Personal AI Life Manager

*Updated: 2026-08-27, latest (**a second attack run closes the carried-context class** — the
decline re-propose guard, per-field log timestamps, the Bill resolution store, the medication
Red-line spec and the wisdom-store proposal, four workers, all merged — **and deployed by Mike
at close-out**, so the Cluster F confirmations are live now).*

*✅ **The capstone plan is the read-first for any backlog work:**
**`archive/plans/capstone_cluster_review_2026-08-27.md`** — every open item by functional
cluster with tier, estimate and status. Goal (Mike): finish this rendition's core features,
begin full testing; rebuild-adjacent work parked in its Cluster H. **National Rail
(`[DB-0818-04]`) and geolocation (`[DB-0815-12]`) are first-draft features** by his ruling —
the Darwin API key is his to register; the location privacy tier is @session.*

*✅ **Nine builds now merged, each awaiting one live confirmation post-deploy** (`@waiting`,
evidence per item in the backlog): decline path with the re-propose guard `[DB-0827-01]` ·
context age with the intraday per-field half `[DB-0822-06]` (derived-count half retired as
stale-premised) · Bill resolution store `[DB-0818-05]` · Diarist user-turn gate `[DB-0822-05]` ·
empty-label filter `[DB-0827-07]` · false-action-claim detector `[DB-0815-11]` (policy half
@session) · context-audit line `[DB-0814-02]`. Also from the second attack: `[DB-0808-14]`
scoped to a ready Red spec (A4 re-run PASS 3/3) and the `[DB-0818-06]` per-entry proposal
awaiting Mike's review — both specs in `archive/plans/`. `[DB-0826-01]`'s referent class is a
four-instance pattern, workable now.*

*✅ **The synthesizer audit is executed, gated, and deployed** (record + watch list:
`archive/plans/synthesizer_audit_2026-08-18.md` § Execution record; `[DB-0822-10]` closes on
the watch). **Its failures are ADHERENCE, not missing rules — re-measure on one post-deploy
scheduled-run day before fixing `[DB-0822-08]`/`-09` by instruction.***

*⚠ **Intake is still dark until Mike's VM edits** (`enabled: true` in mike's `intake.yaml`;
delete `mike.md`'s six-hour inbox line if present) — gates: `[DB-0820-03]`, `[DB-0820-04]`.*

*⚠ **Caps revert to $100/$175 at the September reset — evidence in** (`[DB-0820-01]`,
`due: 2026-09-01`). The Pro-routing decision `[DB-0820-05]` **absorbed `[DB-0822-01]`'s Step 6
half** (A4-gated), `due: 2026-09-15`. Mike flips the Mac's `VERTEX_CACHE_DISABLED` himself.*

*⛔ **ZDR: refused, ruled on, do not re-open** — `ROADMAP.md` § Section 0 *RESOLVED 2026-08-26*.
The narrower written-basis amendment ruling is now `[DB-0827-08]`, `due: 2026-09-05`. CRM sweep
build still gated on Mike's plan re-review (`[DB-0827-03]`).*

***Next, in the tracker's order:** ① **one** decisions session with Mike — his ruling
2026-08-27: the whole batch in a single chat, not spread across several (includes the 39 tool
grants blocking A7 check 10; the wisdom-store proposal review rides along); ② supervised Red
session in `core/scheduler.py` (`[DB-0822-07]` + `[DB-0808-11]`) — the medication schema edit
(`[DB-0808-14]`, spec ready) fits the same sitting; ③ email-surfacing session (`[DB-0822-09]` +
the re-measure); ④ CRM sweep build (Opus, post-review). Cluster F drains on Mike's ordinary use
(~30 min, plus three new one-shot confirmations from the second attack).*

*⚠ **A v1/alpha architecture question is live: invert to code-dominant, with models as discrete
judgment gates.** Still **no decision**, and it must be **decided before A8 executes** or A8 is
paid for twice. The conversation now has a standing home — append dated rounds to
**`archive/plans/code_dominant_rebuild_notes.md`** (no length limit; Mike, 08-27). Three rounds in:
the 08-22 "built backwards?" discussion; the 08-27 trace audit (392 single-call turns → `[DB-0808-09]`,
`[DB-0827-02]`); and the 08-10 sink-gap chat's parked thinking (that review also refiled the
discarded `ROUTING_MISS` as `[DB-0827-05]`).*

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
- **Check 10** — agent behavioural audits (12 specialists; Coordinator/Synthesizer via pipeline probes)
- **Check 12** — constitution alignment review
- **A5b/A5c** — re-run `write_aspirational_baseline` with A5 mission-level data (A3 baseline is still a placeholder); A5c preference activation recorded "unknown, confirm if needed."

**A9 — Product analytics — FIRST DRAFT BUILT AND DEPLOYED 2026-08-18; review deferred.** Alpha
gate requirement. **The core metric is absorbed work, not engagement** — sessions are the
denominator, so rising engagement is not success. `tools/analytics.py`, 05:40 job, content-free
per-user rows, cohort anchor pinned. **Refinement is `ROADMAP.md` § A9a**, `@waiting` on `mike`
holding goals and real data in ongoing use; the five provisional parts (the world-affecting list,
the un-split T1/T2, COGS, the self-report substitute, per-user collection) are enumerated there,
with a **`2026-10-01` review date** so the condition cannot sit forever. `[DB-0818-03]` was removed
from the backlog 2026-08-18 — § A9a is the single home for the review.

**A8 — Pre-Alpha code refactor** — gated on A7. Module extraction from
`core/orchestrator.py` and `core/server.py`. **Full spec, including the regression gate, is in
[ROADMAP.md](ROADMAP.md) § A8** — not restated here, it was a duplicate copy.

**Four built-and-standing constraints must not be undone** (outbound messaging, `tone_shape`,
obligations-as-data, scheduler maintenance jobs) — **full statements and reasoning:
`archive/PROJECT_LOG.md`**; reference now, not current state.

**Seven decisions are queued and none can be made here** — `@session:` items in
`DEV_BACKLOG.md` § Later § Decisions, which holds the evidence. The one that blocks the roadmap:
`[DB-0810-03]` (39 tool grants) gates A7 check 10.

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

## Model IDs (updated 2026-07-27)

| Provider | Model | ID | Notes |
|---|---|---|---|
| Anthropic | Sonnet 5 (orchestrator fallback) | `claude-sonnet-5` | Only used inside `run_model_conference`'s unused `anthropic` branch — not on the live routing path (cloud/local routing is all Gemini/Ollama). Bumped 2026-07-27 from `claude-sonnet-4-6`. |
| Anthropic | Opus 5 (`ask_claude` MCP alias `opus`) | `claude-opus-5` | Added 2026-07-27 — new Anthropic release, matches Fable-5-tier capability at half price. `opus-4-8`/`opus-4-7` kept as pinned aliases in `~/.claude/mcp_servers/ask_claude.py`. |
| OpenAI | o3 | `o3` | |
| Gemini | Flash-Lite | `gemini-3.1-flash-lite` | ✓ confirmed on Vertex (no `models/` prefix on Vertex) |
| Gemini | Pro | `gemini-3.1-pro-preview` | ✓ confirmed on Vertex |

**Vertex note:** AI Studio uses `models/gemini-*` prefix; Vertex drops the prefix. The orchestrator strips it automatically when `GOOGLE_CLOUD_PROJECT` is set.

---

## Key design decisions

**The only list is [CLAUDE.md](CLAUDE.md) → Key Design Decisions.** *(Why this file no longer
carries a second: `archive/PROJECT_LOG.md` § 2026-08-03.)*
