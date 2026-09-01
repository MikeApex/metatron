# Session Primer — Personal AI Life Manager

*Updated: 2026-09-01 (**a single-item `/fix` session, Mike present.** The spend caps are back
at **$100 soft / $175 hard** on the September reset — `[DB-0820-01]` closed and removed,
evidence in `archive/backlog_closed_2026-09.md`. Both budgets re-read from GCP after the
change; **soft was lowered first** so the gap never narrowed to $25 in passing. Same commit
stopped three live files (`core/spend_guard.py`, `config/modules/spend_guard.yaml`,
`infra/stop-vm/main.py`) restating `$70/$150` — none of them read the numbers, so they now
point at `docs/INFRASTRUCTURE.md`, which is again the only copy. `b33498f`, **not deployed and
nothing owed** — comments only. Session ③'s batch remains deployed and live-verified from
08-29. Fragment 2026-09-01-01.)*

*✅ **The capstone plan is the read-first for any backlog work:**
**`archive/plans/capstone_cluster_review_2026-08-27.md`** — every open item by functional
cluster with tier, estimate and status. Goal (Mike): finish this rendition's core features,
begin full testing; rebuild-adjacent work parked in its Cluster H. **National Rail
(`[DB-0818-04]`) is a first-draft feature** by his ruling — the Darwin API key is his to
register. Geolocation (`[DB-0815-12]`): deployed; zones file + one ping at a zone still owed.*

*⛔ **Decisions are PARKED until capstone close (Mike, 2026-08-29):** the 08-29 Inbox triage
table (8 entries, dispositions proposed), the three `@session` items, and the intake corpus
labelling. **Ruled already:** the three calendar duplicate pairs are real — keep either,
delete the rest; executing closes `[DB-0809-21]`.*

*⚠ **Caps are $100/$175 again (done 2026-09-01).** Expect a heavy testing day to trip the soft
cap — that is the control working, recovery is a 60s VM start. Values live in
`docs/INFRASTRUCTURE.md` § Billing protection, now the only copy. (M) still owed: BigQuery
billing export, and flip the Mac's `VERTEX_CACHE_DISABLED` — with a measured payoff.*

*⛔ **ZDR: refused, ruled on, do not re-open** — the whole basis, incl. Amendment 2026-08-28,
is `ROADMAP.md` § Section 0. The `[DB-0818-06]` wisdom-store proposal review still awaits
Mike. CRM sweep: **built** (`f75a338`, parallel window, gate lifted by Mike) — deployed at
close-out, testing owed.*

*✅ **The daily backup is fixed and live-verified** (fragment 2026-08-29-03). **⚠ Still true:
no off-machine copy** — the Restic external-drive job is not installed. Mike's call, unfiled.*

***Next: Red session ④ — the prompt is written and Mike-bound for review:**
**`archive/handoffs/2026-08-30-red-session-four-prompt.md`** (Fable, on/after 2026-08-30, once
the 20:00 run is in traces). It owns: the `[DB-0822-08]` re-measure + decision, the
clock-gated confirm drain (incl. the **unobserved 18:24/20:00 runs of 08-29** — decline tail,
email surfacing), the parked `synthesizer.md` `source` line, the calendar dedupe, and the
capstone close-out review. Sunday 08-31: the retro half of `[DB-0827-09]`. A7 check 10 is
runnable; check 12 unstarted.*

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
