# Session Primer — Personal AI Life Manager

*Updated: 2026-08-10, later still (The Book: thinking-token breakout, ungrounded-answer flag) —
`cb9f459`, **deployed, VM HEAD verified**. Mike asked why the Book showed input tokens but not
output/thinking tokens, and why chat #007's tool calls weren't evident. Both turned out to have
real causes, found by pulling `data/personas/mike/traces/2026-08-10.jsonl` from the VM rather than
trusting the (stale, pre-07-29) local checkout: (1) Gemini/Vertex already return a separate
thinking-token figure but it was folded into `output_tokens` before saving — now split in
`core/trace.py`/`core/orchestrator.py` and rendered in the Book. (2) chat #007's flight/weather
answers genuinely had **zero tool calls** — `research_agent` hit the `run_subagent` recursion guard
(`tools/subagent.py:38-46`) and answered anyway; the Book was accurate, just not visible enough. Added
a `grounded` flag + `⚠ no tool calls` tag so this is visible without SSHing in. One suspected
`push_agent()` nesting pattern was checked and ruled out (guard-blocked, no fix needed) — does
**not** clear `[DB-0810-02]`, a different still-open bug in the same pair, untouched this
session. **Not filed:** whether flight/weather/transport need a real tool — a design question
for Mike, not yet a backlog item. **Side effect worth flagging:**
`./deploy.sh` for this change also carried the previously-undeployed outbound-messaging/tone-profile
work (`9eb5ac4`, `88957e6`) since deploy pushes all of `main` — **`[DB-0810-05]`'s deploy
prerequisite is now met**, which means `get_tone_shape` can now self-seed unattended on the first
draft to any profile-less contact. The IMAP half is still entirely unexercised against a real
mailbox — **the first live send should still be a deliberate `refresh=true` on one contact**,
not an incidental first draft. `[DB-0804-01]`'s count is due **08-11 — tomorrow**. Full detail:
[archive/PROJECT_LOG.md](archive/PROJECT_LOG.md).*

> **This file is replaced, not appended to.** Each session rewrites the paragraph above and
> updates the state below; the detail goes to [archive/PROJECT_LOG.md](archive/PROJECT_LOG.md).
> **Ceiling: 200 lines.** Growing a little is fine — a new blocker is worth a line. Crossing 200
> means history is accumulating here instead of in the log; see `CLAUDE.md` → **Which File Holds What**.

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
`fetch_url`, `read_email`, and the `<untrusted_content>` boundary (2026-08-04)**.
*Dates and reasoning for all of it: [archive/PROJECT_LOG.md](archive/PROJECT_LOG.md).*

### In progress / next

**A7 — Phase 5 sign-off — BLOCKED.** A1–A6 complete; Track B2 fully built. The 2026-08-05
pre-sign-off gate cleared the *regression* gate on the cloud path (6/6 + pipeline 3/3), **not A7**.
Three checks still open:

- **B1** — red team. **B1a passed** (re-run 2026-08-08 post-filter-upgrade: 102 pass, 0 error,
  `tests/security_redteam_2026-08-08.md`). **B1b not closed** — email row covered (`injection`,
  3/3 vs `danny_park`); calendar, web and CardDAV rows untouched, gated on Track E.
- **Check 10** — agent behavioural audits (12 specialists; Coordinator/Synthesizer via pipeline probes)
- **Check 12** — constitution alignment review
- **A5b/A5c** — re-run `write_aspirational_baseline` with A5 mission-level data (A3 baseline is still a placeholder); A5c preference activation recorded "unknown, confirm if needed."

**A8 — Pre-Alpha code refactor** — gated on A7. Module extraction from
`core/orchestrator.py` and `core/server.py`. **Full spec, including the regression gate, is in
[ROADMAP.md](ROADMAP.md) § A8** — not restated here, it was a duplicate copy.

**`[DB-0804-01]` still open** — check-ins fixed/deployed (`10bf194`), but no end-to-end
scheduled fire directly observed yet. One-week count due 2026-08-11 — do not check before then.

**Outbound messaging is Relationships' alone** (`9eb5ac4`). Logistics keeps `read_email`; Coordinator
routes any message-to-a-person to Relationships, which holds three-level disclosure discretion and
the communication-style baseline. `send_email`'s `disclosure_note` is **outside the confirm
fingerprint** by design — do not move it into `args`. **The ZDR clarification is project-wide**
(`ROADMAP.md` § Section 0).

**Tone profiles built, not deployed, never run live** (`88957e6`) — `tools/tone.py`,
`config/agents/tone_profiler.md`, `search_correspondence`, `tone_shape` on the contact record.
`tone_shape` is accepted by `write_contact` but **deliberately absent from its schema**: only
`tone.py` writes it, because the source is attacker-writable mail and the field is read back as
trusted prompt text. The fixed JSON key set reassembled in Python is that defence — the injection
check is only a backstop. Gate is **`[DB-0810-05]`**: the IMAP half is entirely unexercised.

**Obligations are data, not jobs.** `tools/obligations.py` + `data/personas/{p}/obligations.yaml`;
closure is inferred, `close_obligation` **requires** evidence. The reconcile sweep **never
notifies** — it writes candidates; a model session judges.

**Scheduler jobs split two ways (2026-08-08):** silent maintenance jobs register from
`_DEFAULT_JOBS` in `core/scheduler.py` for every persona; jobs with a prompt/notification stay
in per-persona `scheduler.yaml`. **Do not re-add a maintenance job to a persona file.** Reasoning:
`archive/PROJECT_LOG.md`.

**The backlog is the bin for everything outside this roadmap**; live counts come from the sync
line, not here. Work it with **`/backlog`** (`deep` = clustering, `attack` = parallel prompts) —
which command and when: [docs/WORKFLOW.md](docs/WORKFLOW.md); its three rules: `CLAUDE.md`.

**`[DB-0808-17]`** (A4 clinical hard-fails never run on Flash-Lite) exposes a wording gap in
`ROADMAP.md` § A7 check 8 — routing stays as-is by decision; the test gap is the open item.

---

## Recent sessions

Newest first. Full detail for every entry — and everything older — is in
[archive/PROJECT_LOG.md](archive/PROJECT_LOG.md).

| Date | What | Deployed |
|---|---|---|
| 08-10 | **The Book: thinking-token breakout, ungrounded-answer flag** — split Gemini/Vertex's already-returned reasoning-token figure out of `output_tokens` (was folded in before saving) and rendered it in the Book. Real finding from pulling the live VM trace for chat #007: flight/weather answers had **zero tool calls** — `research_agent` hit the `run_subagent` recursion guard and answered anyway; added a `grounded` flag + UI tag so this is visible without SSHing in. Ruled out one suspected subagent-nesting pattern (guard-blocked, no fix needed) — does not clear `[DB-0810-02]`, a different still-open bug in the same `push_agent`/`pop_agent` pair, untouched this session. This deploy also carried the previously-pending outbound-messaging/tone work, clearing `[DB-0810-05]`'s deploy prerequisite | `cb9f459` — deployed, VM verified |
| 08-10 | **Outbound communication got one owner; per-contact tone profiles built** — the design question ("a public-facing comms agent, or the existing suite?") reversed twice, both times on code rather than reasoning. Final: **Relationships owns every message to a person**, because `_known_recipients()` already limits every recipient to a saved CRM contact — sending was always a person-graph operation. The old split had Relationships generating all outreach with no send tool and Logistics holding `send_email` with no way to resolve a name; `_resolve_attendees()` had already patched around that seam in Python. **Rejected a dedicated Comms agent** — it would still need the CRM, recreating the boundary one step over. `send_email` gained `disclosure_note`, kept **out of `args`** so a forgotten note on the retry cannot fail the send. Tone profiles distil real correspondence through a **fixed JSON key set reassembled in Python** — the trust-laundering defence, since the source is attacker-writable mail and the destination is read back as trusted prompt text. **Two corrections:** I called `[DB-0805-02]` a blocker on its title alone when SESSION.md already had it verified-stale; and the comms baseline was headed for the persona template until the pre-edit check caught `CLAUDE.md` § *Two kinds of preference*. **Plan deviation:** skipped the specified `_SUBAGENT_DEPTH=99` — `run_session()` never reads it and `os.environ` is process-global, so it would race concurrent sessions; the empty tool grant is the real control | `9eb5ac4`, `cae31df`, `88957e6` — **not deployed**, gated on `[DB-0810-05]` |
| 08-10 | **`/backlog deep` — two items closed on premises that had stopped being true, a live grant gap shipped** — `[DB-0809-15]` closed stale: the confirm-gate wiring it asked for already existed (`config_writer.py:43`, `agent_config.py:76`), and the surviving question was already open as `[DB-0805-01]` — **the same question filed twice, once falsely**. `[DB-0809-19]` closed by re-running B1's `DEPUTY-STRUCT` standalone (no model call): PASS after `82d394b`. `[DB-0809-21]` corrected 2-of-4 → **3 of 4** — its `companion_checkin` check had passed that morning and only the entry lagged. Merged `[DB-0807-02]`→`[DB-0808-04]`, `[DB-0809-17]`→`[DB-0805-05]`. Machine log exposed **3 specialists instructed to use `search_memory` holding none of it**; granted `relationships`+`finance` with denials cited, **`recreation_hobbies` withheld** — never denied it, so it would be the file's first speculative grant. Filed `[DB-0810-03]`, `[DB-0810-04]` (`/archive` has no commit step). **Two windows in one tree both diagnosed the same crash independently** → `[DB-0805-05]` at 2 occurrences | `a96a3b3`, `a431472` — deployed, VM verified |
| 08-10 | **`/metatron-troubleshoot` seq 005 — research_agent grounded-search crash found and fixed** — `getattr(gm, "grounding_chunks", [])`'s default only covers a missing attribute, not Gemini's None-valued one; broke TfL/weather/pollen and every other grounded query hitting that response shape, both direct dispatch and Synthesizer's `run_subagent` retries. Reproduced on the VM before and after the fix. Also noted (not fixed): `core/trace.py`'s `pop_agent()` doesn't restore the prior thread-local `current_agent`, so nested `run_subagent` tool-call records can misattribute to the child agent in The Book | `bc1a552` — deployed, VM verified, no crash loop |
| 08-10 | **Sonnet cluster closed 9→2; a live WebSocket race found, corrected once, filed** — `[DB-0803-01]` half two fixed by tuning Silero's VAD against all 108 retained audio files (98.07% avg recovered, 0 hallucination markers) rather than disabling it. `[DB-0809-03]` closed with no build — its citation was wrong; the real fix shipped 2026-08-05. `[DB-0809-06]` fixed both causes (catch-up wiped the transcript on reconnect; hidden tabs never checked liveness). `[DB-0808-18]`'s key rotation reached three systems, not one — caught a regression before it shipped (deleting the old `~/.zshrc` export would have broken `ask_gpt` globally). `[DB-0805-02]` closed live against a real phone. **The correction:** doubled text looked install-specific until it recurred 12 minutes later with no install involved — real cause is `ws.close()` not synchronously closing, leaving two sockets briefly live during a reconnect; filed as `[DB-0810-01]`, not fixed, since the two real defenses are a genuine design choice | nine commits, all deployed and verified against the VM + a real phone session |
---

## Useful context to pull as needed

| Question | Where to look |
|---|---|
| What does each agent do? | `config/agents/` |
| What tools exist and what they do | `tools/` — all registered in `core/orchestrator.py → register_tools()` |
| What's the security posture? | `archive/security/threat_model_2026-06-04.md`, `archive/security/security_backlog_2026-06-04.md` |
| What are the test criteria for this phase? | `tests/phase5_testing_plan.md` |
| What's parked for later phases? | `archive/plans/future_phases.md` |
| Agent enhancement backlogs | `## Enhancement backlog` at the bottom of each `config/agents/*.md` — **the only copy**; the `DEV_BACKLOG.md` and roadmap mirrors were deleted 2026-08-03 |
| Why was this built this way? | [archive/PROJECT_LOG.md](archive/PROJECT_LOG.md) — dated history, reasoning, corrections |
| Deploy / recovery / rebuild detail | [docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md) |
| Session history | [archive/PROJECT_LOG.md](archive/PROJECT_LOG.md) — one entry per session, newest first (`archive/sessions/` is pre-08-09 only) |
| Which command to fire, and when | [docs/WORKFLOW.md](docs/WORKFLOW.md) |
| Model routing assignments | `config/modules/routing.yaml` |
| How to run the system | See Quick Start below |

---

## Quick start

> **⚠ Switching to local Mac routing (Ollama)?** Two things must be activated first:
> 1. `sudo pmset -a sleep 0 disksleep 0` — prevent Mac sleep
> 2. `launchctl load ~/Library/LaunchAgents/com.metatron.server.plist` — keep server alive (create plist first if not done — see `archive/sessions/2026-06-20 — VM Provisioning, GitHub, Deploy Pipeline.md`)
> Reverse with: `sudo pmset -a sleep 10 disksleep 10` and `launchctl unload ~/Library/LaunchAgents/com.metatron.server.plist`

```bash
cd ~/Desktop/multi-model-mcp
source .venv/bin/activate

# Start the PWA server (Vertex cloud routing — default as of 2026-06-19)
# No Ollama needed — DEPLOYMENT_MODE=cloud in .env routes all agents to Vertex
python core/server.py --persona mike --port 8001

# Kill a stuck server on port 8001 and restart
lsof -ti :8001 | xargs kill -9 && python core/server.py --persona mike --port 8001

# Run a specific agent directly
python core/orchestrator.py --agent research_agent --provider gemini

# Run the scheduler daemon
python core/scheduler.py
```

**Deployment mode:** `DEPLOYMENT_MODE=cloud` is set in `.env` — loads `config/modules/routing_cloud.yaml` (all agents → Vertex Gemini 3.1 Pro). To use local Ollama instead, remove or unset `DEPLOYMENT_MODE`.

**Vertex credentials:** ADC configured via gcloud on this machine. GCP project: `metatron-ai-499810`, location: `global`.

**If using local Ollama:** `ollama serve` at `localhost:11434`, model `qwen3:14b`.

---

## Model IDs (updated 2026-07-27)

| Provider | Model | ID | Notes |
|---|---|---|---|
| Anthropic | Sonnet 5 (orchestrator fallback) | `claude-sonnet-5` | Only used inside `run_model_conference`'s unused `anthropic` branch — not on the live routing path (cloud/local routing is all Gemini/Ollama). Bumped 2026-07-27 from `claude-sonnet-4-6`. |
| Anthropic | Opus 5 (`ask_claude` MCP alias `opus`) | `claude-opus-5` | Added 2026-07-27 — new Anthropic release, matches Fable-5-tier capability at half price. `opus-4-8`/`opus-4-7` kept as pinned aliases in `~/.claude/mcp_servers/ask_claude.py`. |
| OpenAI | o3 | `o3` | |
| Gemini | Flash-Lite | `gemini-3.1-flash-lite` | ✓ confirmed on Vertex (no `models/` prefix on Vertex) |
| Gemini | Pro | `gemini-3.1-pro-preview` | ✓ confirmed on Vertex |
| Ollama | Local 14B | `qwen3:14b` | local only |

**Vertex note:** AI Studio uses `models/gemini-*` prefix; Vertex drops the prefix. The orchestrator strips it automatically when `GOOGLE_CLOUD_PROJECT` is set.

---

## Key design decisions

**Moved to [CLAUDE.md](CLAUDE.md) → Key Design Decisions.** This file carried a second list
under an almost identical heading, with different contents, so whichever you found first looked
like the whole set. The two unique entries here — the 2026-06-18 ZDR amendment and
archive-on-merge — were merged into that list, which is now the only one.
