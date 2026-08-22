# Session Primer — Personal AI Life Manager

*Updated: 2026-08-22 (architecture discussion; ZDR opt-out submitted) — **the ZDR opt-out was
submitted 2026-08-22; decision expected by ~2026-09-05** (Google: ~2 weeks + 5–7 business days to
allowlist). **Not in force until granted**; the email to `diamond.mike@gmail.com` is the only
evidence, recorded either way in `docs/INFRASTRUCTURE.md` § Vertex AI credentials, which stays
the authority. Terms and answers as filed: `archive/security/zdr_terms_evidence_2026-08-20.md`,
`…/zdr_optout_form_answers_2026-08-21.md`. **One act still Mike's and it does not wait on
Google:** rule on the proposed § Section 0 amendment — does the sensitive-tier default continue
on the corrected basis (flagged-only logging, ≤90 days, no training) until grant or refusal,
backstop 2026-10-01.*

*⚠ **A parallel window is mid-build on the cache fix**, none of it staged here. Plan:
`archive/plans/vertex_cache_cost_control_2026-08-20_plan.md`, **rewritten by Fable — the 10-minute
TTL is the fix; the orphan sweep is a ~$0.14/day tidy-up, because Vertex reaps at `expire_time`.**
Storage ran ~$3.4–3.9/day against $0.51 of savings, and `spend_guard` read $2.63 against a $6.12
bill while working exactly as designed.*

*⚠ **Intake is still dark until Mike's VM edits** — `enabled: true` in mike's `intake.yaml`, and
delete `mike.md`'s "check inbox every six hours" line if still present. `[DB-0820-03]` holds the
model-tier switch-on gate, `[DB-0820-04]` owes the extractor its own injection row (advances B1b).*

*⚠ **Caps are temporarily $150/$250, back down in September** — `[DB-0820-01]`, `due: 2026-09-01`;
keep ~$100 between tiers (`CLAUDE.md` § Infrastructure traps 3). **`[DB-0815-07]` and `[DB-0810-07]`
remain untested, not passing** — their 08-19 test designs never reached the code they tested.*

***Next:** `[DB-0820-05]` — with storage
fixed, all-Pro routing is **~$3.11/day against today's $6.12**, so the Flash-Lite tiers are worth
revisiting once a clean day is measured; `coordinator` is the only candidate and its blocker is
latency, not money. `175809e` **owes a deploy but changes nothing on the VM**.*

*⚠ **A v1/alpha architecture question is live: invert to code-dominant, with models as discrete
judgment gates.** Preliminary discussion 2026-08-22, **no decision** — Claude recommended the
inversion (Coordinator first candidate; Synthesizer stays a real agent; pilot the
invitation/RSVP flow) and that it be **decided before A8 executes**, or A8 is paid for twice.
This is the vehicle for the queued `@session` decision "where code should replace model
judgment". Consultable record:
`archive/plans/code_vs_agent_architecture_2026-08-22_discussion.md`.*

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

**Seven decisions are queued and none can be made here.** They carry `@session:` in
`DEV_BACKLOG.md` § Later § Decisions, with the evidence — the 39 tool grants (`[DB-0810-03]`,
which blocks A7 check 10), the repeated-ritual fix shape (`[DB-0809-02]`, two prior diagnoses
confidently wrong), whether `write_persona` may self-apply a preference (`[DB-0815-11]`), the
continuous-location privacy tier, what a mailbox "ticket" is, where code should replace model
judgment, and whether to seed clinical-adjacent knowledge into the A4 test persona
(`[DB-0818-07]` — A4 currently passes without the regression ever touching the knowledge path).

---

## Recent sessions

Newest first, **one line each** — this is an index, not a summary. Reasoning, rejected options
and corrections live in [archive/PROJECT_LOG.md](archive/PROJECT_LOG.md); a row that starts
restating them is duplicating a file that already holds them better.

| Date | What | Deployed |
|---|---|---|
| 08-22 | **Was Metatron built backwards? A code-dominant inversion — procedural spine in code, models as discrete judgment gates — was argued for and left with Mike.** Prompted by an Opus barbecue-RSVP exhibit showing model inertia toward the reactive; the "compass layer" (allocation policy, portfolio view) needs standing *computed* state no prompt can supply, and the incident log has been moving judgment into code all year. Recommendation: decide before A8; pilot the RSVP flow; Synthesizer stays an agent. Full record: `archive/plans/code_vs_agent_architecture_2026-08-22_discussion.md` | **nothing — discussion only** |
| 08-21 | **ZDR: "verified" became verified — the abuse-monitoring exception is obtainable on this account shape, and the default is conditional logging, not blanket retention.** Google's published terms, read under a scoped, since-reverted WebFetch lift: the opt-out form serves exactly self-serve GCP-ToS customers; flagged-only prompt logging ≤90 days, never training; `cacheConfig` governs only the latency cache (handoff caution resolved); Search grounding keeps query logs 3 days with no opt-out. Evidence + proposed amendment: `archive/security/zdr_terms_evidence_2026-08-20.md`; status authority: `docs/INFRASTRUCTURE.md` § Vertex AI credentials. Form + § Section 0 ruling pending with Mike | **nothing — docs only** |
| 08-20 | **The Vertex bill reconciled — the cost that stopped the VM is one no per-call meter could see.** Context-cache **storage bills per wall-clock hour** ($4.50/1M/hr on Pro), so `spend_guard` read **$2.63 against a $6.12 bill** and was working as designed. Three defects: caches **abandoned on every restart** (5 server + 5 scheduler = 10 Pro caches billing at once), **midnight-UTC expiry chosen for config-freshness with no cost figure beside it**, and the guard blind to storage. **Fable's review inverted the plan's priority** — the 10-minute TTL is the fix; the orphan sweep is a ~$0.14/day tidy-up, because Vertex reaps at `expire_time`. It also caught an unlocked registry, a streaming path that never evicts, and that Step 6 splits by model class (the compat path exists to dodge the `thought_signature` bug). **Three of my own claims were wrong and measurement killed each**: that caching never ran on the VM (the logs just don't capture it), that the residual was storage alone (**creation is metered too — proved by probe**), and that caching "costs more than it saves" before hit rate was measured (**15 hits against 65 Pro calls**). `[DB-0820-05]` filed: all-Pro routing is ~$3.11/day against today's $6.12. Global `CLAUDE.md` gained **§ Costs**. **Then the session's largest finding, and it is not about cost: `ROADMAP.md` § Section 0 has authorised sensitive-tier data on the VM since 2026-06-18 on "verified ZDR" — never verified, and not in force.** No org parent, self-serve billing account, zero org policies, no exception on record. Only "no training use" of its three claims holds. Recorded as a dated correction beneath the original text, **not a rewrite**; whether the permission continues is left explicitly undecided. Mike overrode filing-and-verifying-later — the check took four commands and overturned a two-month premise. Also fixed: all three Vertex call sites defaulted to a region that does not serve Gemini 3.x | **`6a96fc4`…`01495ec`; `175809e` owes a deploy but is inert on the VM** |
| 08-20 | **Inbound intake: mail swept hourly, classified in Python, queued per domain, taught by correction.** An interest sieve, not a filing tool — Mike's rulings: disposition ⊥ domain, no dispatch on arrival, no mailbox writes, digest as training surface. Model tier wired but **double-gated OFF** (`[DB-0820-03]` holds the gate; `[DB-0820-04]` the injection row). Mike's `/code-review high` returned **10 findings, 3 severe** (digest swallowed by the Coordinator; weekly digest would have fired daily; thread siblings re-surfacing) — all fixed, suite 21/21. `tone_profiler` runs bare, `[DB-0819-02]` closed. **Dark until Mike's VM edits**; inbox primed 08-21 | `b417e98` — **deployed** |
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

**Vertex note:** AI Studio uses `models/gemini-*` prefix; Vertex drops the prefix. The orchestrator strips it automatically when `GOOGLE_CLOUD_PROJECT` is set.

---

## Key design decisions

**The only list is [CLAUDE.md](CLAUDE.md) → Key Design Decisions.** *(Why this file no longer
carries a second: `archive/PROJECT_LOG.md` § 2026-08-03.)*
