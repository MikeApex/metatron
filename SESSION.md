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

*✅ **The cache fix is deployed and now measured against a real day.** 08-21 reconciled from Cloud
Monitoring + the VM's `spend_guard`: **storage fell $3.46/day → $0.14994**, and caching is
**net-positive for the first time** (+$0.10 to +$0.31/day — ~1–1.5 reads per window, sitting on
break-even). Expected bill **$2.51–$2.71** against 08-19's $6.12 for *more* usage. Method validated
by reproducing 08-19's known gap to the dollar. **The export is backfilling forward, not broken** —
it advanced 08-12 → 08-14 during the session; `[DB-0822-01]` (`due: 2026-08-25`) still waits on
rows passing 08-21, which is also what `[DB-0820-01]`'s cap revert needs.*

*✅ **`spend_guard`'s ~23% undercount is closed and deployed** (`b4dcb0e`, live with the 08-26
deploy): `unmetered_uplift: 1.25`, alert/stop judge `usd_billed_est`, so the $6 alert trips at
$4.80 observed. One unverified remainder: its config comment ("export dark since 08-12") was to
be corrected on deploy — check it was. Reasoning: `archive/PROJECT_LOG.md` § 2026-08-22.*

*⚠ **Intake is still dark until Mike's VM edits** — `enabled: true` in mike's `intake.yaml`, and
delete `mike.md`'s "check inbox every six hours" line if still present. `[DB-0820-03]` holds the
model-tier switch-on gate, `[DB-0820-04]` owes the extractor its own injection row (advances B1b).*

*⚠ **The 08-21 traces say the Synthesizer's failures are ADHERENCE, not missing rules.** 89% of the
day was automated (116 of 130 calls; 4 interactive runs). **Six of Mike's six complaints are already
written in `config/agents/synthesizer.md`** — raise-once and obligations-never-listed (:187), open on
one thing and nothing-new→one line (:181), length-follows-focus (:183), ritual scoped to
`evening_close` (:209) — and all six were ignored. **Do not fix `[DB-0822-05]`–`[DB-0822-10]` by
adding another rule;** the file is 52,397 bytes and its own audit named length→adherence as the
cause. The virtue dump is context-injection code (`core/orchestrator.py:352-356`), not prose.*

*⚠ **Caps are temporarily $150/$250, back down in September** — `[DB-0820-01]`, `due: 2026-09-01`;
keep ~$100 between tiers (`CLAUDE.md` § Infrastructure traps 3).*

*✅ **A near-match contact is no longer created silently** (`6d6d46c`, deployed; `[DB-0815-07]`
closed). The gate should become unnecessary as models improve — the judgement-consistency test
that decides that is `ROADMAP.md` § D2's row. `b980b93` fixed the crashes-only monitoring flag;
`[DB-0810-07]` open.*

*✅ **Venue discovery is live and closed** (`[DB-0808-04]`, trace `bac9d794`): "suggest a place to
eat near X" now routes to Logistics, calls `find_places`, travel-checks results. Key on the VM as
`GOOGLE_PLACES_API_KEY` (Places API (New) — the console steers to the legacy product; both
enablement and key restriction had to be repointed). **Two live checks remain from the 08-22
batch, each carried by its item:** the merge confirmation card (`[DB-0822-03]`; unmerge is
forward-only — Steven's repair stays manual, `[DB-0822-04]`) and the offline shell
(`[DB-0803-05]`; one online load first). **New 2026-08-26 (`bec3952`, deployed): Logistics scans
locations unasked** — horizon item 5 + daily 10:00 `location_anticipation` job (template AND
mike's VM scheduler.yaml by hand; first firing 08-27, observation filed). **Diarist logs events,
never plans; voiced intentions get a fixed `intention` key** — probed on the VM, both pass;
Accountability Index filed.*

***Next:** `[DB-0820-05]` — with storage fixed, all-Pro routing is **~$3.11/day against today's
$6.12**, so the Flash-Lite tiers are worth revisiting once a clean day is measured; `coordinator`
is the only candidate and its blocker is latency, not money. **Deploys current through `1d77bd0`**
(the 08-22 batch, spend_guard uplift and today's config all live). **`[DB-0822-01]` came due
08-25** — the cache-plan reconcile, gating `[DB-0820-01]`'s September cap revert.*

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
| 08-26 | **Venue discovery goes live and `[DB-0808-04]` closes on trace evidence — after the Places key path hit the same trap twice** (legacy "Places API" vs Places API (New): both the enablement and the key restriction had to be repointed). Venue questions route to Logistics; a daily 10:00 anticipation pass scans where the user will be (meals, errands, nearby contacts by area, downtime); the Diarist stops logging plans as events and records voiced intentions in a fixed key — both probed passing on the VM. **A first trace read wrongly said "zero tool calls"** — per-turn nesting; corrected, and the reply was grounded all along | `bec3952` `1d77bd0` `449c0a7` — **deployed** |
| 08-22 | **`/backlog attack`: three clusters shipped by parallel Opus workers, reviewed in Fable.** A dead server now shows the app's own page (SW registration was push-gated — a user who declined notifications never had the shell); a merge asks first, shows both people, and is reversible via pre-merge snapshots (pre-08-22 merges refuse honestly); "find a café near X" is answerable (`find_places`, needs its own Places-restricted key — the Maps key is routes-locked). Coordinator caught the "same key" premise error and the push-gated registration; worker B nearly doubled the ~64k median (118k) | `2d7f955` `e2a7f87` `fd0aed1` `8754222` `158cebe` — **not deployed** |
| 08-22 | **The 21st reconciled: the bill is right, caching earns for the first time, and the scheduler — not Mike — ate the day.** Storage $3.46/day → **$0.14994**; caching net **+$0.10 to +$0.31/day**, sitting on break-even. Expected bill **$2.51–$2.71** vs 08-19's $6.12 for *more* usage; method validated by reproducing 08-19's gap to the dollar. **89% of the day was automated** (9 scheduled + 10 trailing Diarist runs = 116 of 130 calls; 4 interactive), and the Synthesizer's 11 calls cost more than the other 119 combined. **`spend_guard` read 23% low** — cache creation and retries are invisible to the turn path; closed with a measured `unmetered_uplift: 1.25`, raw `usd` kept auditable. **Two of my own claims were wrong and corrected before build:** the billing export is backfilling forward, not dead, and the virtue dump is injection code, not a clock trigger in a Denied-tier file. **The reframe: six of six complaints are already rules in `synthesizer.md` and all six were ignored** — adherence, not absence. Six items filed `[DB-0822-05]`–`[DB-0822-10]`, Amber before Red | `spend_guard` **not deployed** |
| 08-22 | **The contact dedup gate ships; its first live merge takes the wrong Steven.** `write_contact` now saves nothing on a near-match and asks — neither cheaper answer survived measurement (score **cannot** separate same-person from different: Stephen/Steven 0.77 is one, Dave/Dan Bennett 0.87 is two; the agent asked once then asserted 4 min later). **Gate carries a standing note that it should become unnecessary**; § D2 owes a judgement-consistency test. The monitoring flag saw **crashes only** — 786 calls, one `ok:false`, graceful failures all green. **Then `merge_contacts`' first production run corrupted a real contact** on an ambiguous *"keeping Steven"* across three Stevens — no unmerge. An app-side frame log was **stopped by Mike before deploy**: it printed internals as the assistant | `a192821`, `b980b93`, `6d6d46c`, `4c05b8b` — **deployed** |
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
