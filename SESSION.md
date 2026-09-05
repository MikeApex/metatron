# Session Primer — Personal AI Life Manager

*Updated: 2026-09-05, second (**attack day: the deploy debt cleared, three rulings, thread
identity built, the confidence lever spent**). Mike redeployed at 09:03 — VM verified on
`3a01894`, 3.8 Flash live in all six slots, scp-drift gone. `/backlog attack` found all four
`## Now` items `@waiting` on dated confirms, so the day ran from `## Later` on Mike's word, via
two Opus workers. **Thread identity `[DB-0814-02]` is built and merged (`33dd624`) under Mike's
ruling** — Metatron's own rewording preserves a thread's birthdate; user engagement refreshes it
— **and owes `./deploy.sh`** (`tools/context_tracker.py`). **The confidence sweep spent its
lever:** no viable threshold exists for the extractor gate, so it stays off on evidence, and
three of five original runs turned out void (spend-guard refusals scored as `unclear` = gate
pass — 09-04's "run 3 collapse" retro-explained). Detail: `archive/PROJECT_LOG.md`
§ 2026-09-05, second.*

***Next, all Mike:*** **(1)** `./deploy.sh` for the thread-identity build and the eval runner's
INVALID detection; **(2)** the extractor **direction** decision `[DB-0820-03]` — teach `rules:`
(live mailbox already 9/33 with five), grow the corpus, or a stronger tier; the flip question
itself is answered (no flip); **(3)** the Red-tier prompt for scheduler day-name validation
`[DB-0903-02]`, delivered in the 09-05 chat, ready to paste.

*⚠ **The intake extractor stays off — now on measured evidence, not just the gate.** The lowest
zero-false-negative threshold (0.95) demotes 85% of the corpus to `unclear`; every affordable
threshold silences an obligation on the worst run, and with the floor off the model said
`unclear` 0/33 in all five runs — Mike's validity objection confirmed literally. **Direction
ruled 2026-09-05: teach `rules:`** — a rules-teaching walkthrough is the proposed next sitting;
the three variant agent files moved to `archive/agent_variants/`. **Full evidence:
`DEV_BACKLOG.md` `[DB-0820-03]`; do not re-derive it here.***

*✅ **The wisdom store's three intake classes are closed, and one is not.** Corroboration (an
`observed` fact waits for a second sighting in 14 days — the sender ledger's own bar, one file
away), the user's recorded word (`record_wisdom_response`; a denial does **not** delete the entry
and agreement does **not** promote `observed` to `stated`), and an absence-of-evidence self-check
in the six writers. **Still open, and the largest class: a preference recorded as a discovery when
it was already policy** — five of eleven cleared this session were describing behaviour already
instructed in `config/modules/synthesizer_scheduled_sessions.md`. The redundancy guard catches
this on the persona path only, not the wisdom path.*

*⚠ **Test artifacts to delete when the confidence question closes:** the three
`config/agents/intake_extractor_{counterargue,confidence,both}.md` variants, which have no routing
entry. **`## Machine log` grew 90 → 118+** from this session's own eval traffic — artifacts, not
production signal.*

*⚠ **No off-machine backup — Mike declined a date twice; a recorded acceptance of a named risk,
not an unfiled worry. Do not re-raise it.** `VERTEX_CACHE_DISABLED` was flipped ON on the Mac
2026-09-05 (billing export: net **+$0.94**/14d, the 08-21 net-negative finding having reversed).*

*⛔ **Two settled rulings — do not re-open; both in `ROADMAP.md` § Section 0.** A4 safety testing
is SUSPENDED (before-Alpha is the only clock); ZDR is refused.*

*⚠ **The inversion is decided: Alpha ships on Mark 2 (Mike, 2026-09-02).** Architecture thinking
stays in **`archive/plans/code_dominant_rebuild_notes.md`**; sequencing, gates and cost in
**`archive/plans/mark2_endeavour_plan_2026-09-02.md`**. **The Darwin API key `[DB-0818-04]` was
deferred into Mark 2 by Mike on 09-04** — do not re-propose it as a standalone (M).
**`ROADMAP.md` is deliberately NOT updated and still reads as though A8 is live work** — Mike
handles that and the Mark 1 decommission condition manually. Known, not an oversight.*

*⚠ **Thread expiry is fixed in code, not yet in production.** Mike's 09-05 ruling (Metatron
rewording preserves the birthdate; user engagement refreshes) is built and merged; after deploy,
confirm birthdates survive rewording in `context_audit.jsonl` (new fourth field `reworded`) and
expect first real expiries ~09-15 — status in `[DB-0814-02]`. Also open: B4's max-chain-depth
needs the 3-round limit in code first (`[DB-0804-02]`); `[DB-0902-01]`'s week clock runs to
09-12; the other three `## Now` confirms fall due 09-10. Closed 09-05, do not re-raise:
`[DB-0903-01]` (duplicates accepted) and the clinical-agents-via-`quick` Inbox item (accepted
risk, reaffirming 08-09 — noted at ROADMAP § A7 check 8). `CLAUDE.md` is **298/300**;
**`.claude/rules/deploy.md` is 131/100 and still owes a pass.***

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
fixes, the session-⑦ capstone remainder — fact provenance, the degradation wording, the
clinical escalation inbox — and cross-turn attachment persistence (all 2026-09-03, deployed)**.
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
