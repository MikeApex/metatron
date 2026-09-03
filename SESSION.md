# Session Primer — Personal AI Life Manager

*Updated: 2026-09-03 (**Session ⑦ ran — THE CAPSTONE IS CLOSED, and it is deployed and
VM-verified** (`18d6923`; suite **72/72 on the VM**, both units active). All three remaining
items worked; the cluster's remaining investment is spent. **Nothing owes a commit or a
deploy.** **One config line is owed by Mike — see the ⚠ below; without it the clinical review
never runs.**
**Where a fact came from is now recorded `[DB-0818-08]`** — a contact detail read from a real
artefact is no longer silently replaced by a guessed one, and an inferred fact reaches the model
as a sentence about the inference rather than a fact with a "be tentative" note beside it.
**A flagged health concern now alerts something `[DB-0808-06]`** — tier-2 threads land in a
development-side inbox that will one day route to next of kin or physicians, and close through a
code-raised card past a 14-day dwell. **A failure now says what it cost the user `[DB-0804-02]`**
— a raw exception was reaching the composing layer verbatim.
**The theme worth carrying: two of the three items had EXPIRED PREMISES** — the blocker each
described, and that `ROADMAP.md` repeated, had already been removed by unrelated work and nothing
noticed. The re-open-against-current-code rule caught both and changed what got built each time.
Detail: `archive/PROJECT_LOG.md` § 2026-09-03 and the capstone tracker's close-out.)*

***Next: the (M)-walkthrough** (Fable — corpus labelling due 09-09, wisdom review, Darwin key,
zones+APK+ping, BigQuery, Restic); prompt in `archive/handoffs/2026-09-02-*`. **Sessions ⑤, ⑥ and
⑦ are all done and the capstone is closed** — it is no longer the read-first for backlog work;
`DEV_BACKLOG.md` is. **A4's re-run stays off the close path** (before-Alpha only, ROADMAP § 0
pt 8), so clinical flags remain unverified on `gemini-3.7-flash` by decision. `CLAUDE.md` is now
**298/300** (the four-tier hierarchy moved to `.claude/rules/personas.md`);
**`.claude/rules/deploy.md` is 131/100 and still owes a pass.***

*⚠ **OWED BY MIKE, one line, and the feature is half-inert without it.** The weekly clinical
review job is in `config/templates/scheduler.yaml` but not in the live
`config/personas/mike/scheduler.yaml` — a VM-owned, Denied path the deploy correctly does not
overwrite. Until it is added, **a tier-2 health flag is recorded but nothing ever offers to
close it.** Add under `schedules:` — `weekly_clinical_review: {enabled: true, time: "11:00",
days: sunday, function: tools.escalation.review_clinical_escalations, notification: none}`.
**`days:` must be the full lowercase day name** — it shipped as `sun` first, which matches
nothing on any day; fixed in the template with a regression test.*

*⚠ **Two things left open by ⑦, both small.** B4's **max-chain-depth** message cannot be written
until the 3-round limit exists in code rather than only in `synthesizer.md` — re-homed to Track B
with the E1-gated B1b rows and B3, inside `[DB-0804-02]`. And `[DB-0903-01]`, the horizon dedupe
fork, still closes on one answer (recommendation: accept the known limit). `[DB-0902-01]`'s
week-long clock stands. **Standing fact:** the intake queue is empty by construction until
`[DB-0820-03]`'s corpus labelling runs (due 09-09).*

*⚠ **A tripped soft cap is the control working, not an outage** — recovery is a 60s VM start.
Cap numbers: `docs/INFRASTRUCTURE.md` § Billing protection, the only copy — which also carries
the server address, already; ⑦ misread a wrong hostname as an outage. Both owed (M)s (BigQuery
export, `VERTEX_CACHE_DISABLED`) are items 5 and 7 of the (M)-walkthrough.*

*⚠ **No off-machine backup copy** — daily backup live-verified (fragment 2026-08-29-03); the
Restic external-drive job is not installed. Mike's call, deliberately unfiled.*

*⛔ **Two rulings that are settled — do not re-open either; both live in `ROADMAP.md` § Section
0.** (1) **A4 safety testing is SUSPENDED** (Mike, 09-01), re-run **off** the capstone close path
(09-02); **before-Alpha** is the only clock (pt 8, amended). (2) **ZDR is refused**, incl.
Amendment 2026-08-28. Still owed against these: the `[DB-0818-06]` wisdom-store proposal review
(Mike's), and the CRM sweep's first live morning digest as its confirm (built and deployed).*

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
**the Coordinator's view of the previous turn (`[DB-0826-01]`), the session-⑥ record-honesty
fixes (2026-09-03), and the session-⑦ capstone remainder — fact provenance, the degradation
wording, and the clinical escalation inbox (2026-09-03, BUILT AND UNDEPLOYED)**.
*Dates and reasoning for all of it: [archive/PROJECT_LOG.md](archive/PROJECT_LOG.md).*

### In progress / next

**A7 — Phase 5 sign-off — BLOCKED on B1 alone.** A1–A6 complete, Track B2 built. **Checks 10
and 12 are SKIPPED** (Mike, 2026-09-02 — both fold into Mark 2) and **A8 is CANCELLED** (same
ruling; `ROADMAP.md` § A8 still reads as live, Mike updates it manually — do not start it).
What is genuinely left: **B1b's calendar, web-page and CardDAV rows, gated on Track E**, plus
**A5b/A5c** (re-run `write_aspirational_baseline` with A5 mission-level data; A5c preference
activation recorded "unknown"). B1a passes (102/0). The attached-files row passed one manual
probe on 08-20 — **one case, not a suite**. **B4 is now partially built** — see
`[DB-0804-02]`. Per-item detail and the standing evidence live in
[ROADMAP.md](ROADMAP.md) § Track A/B, which owns them; this line is the status, not the record.

**A9 — Product analytics — built and deployed 2026-08-18, review deferred to `2026-10-01`.**
Alpha gate requirement; the core metric is absorbed work, not engagement. Spec and the five
provisional parts: [ROADMAP.md](ROADMAP.md) § A9a, the single home. `@waiting` on real use.

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
