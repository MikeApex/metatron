# Session Primer — Personal AI Life Manager

*Updated: 2026-11-23 (log § 11-23 sixteenth, phase 2 deployed, its checks filed; § fifteenth, lookup switched on; § thirteenth, ranking Part B phase 2 built in shadow; § 11-23 eleventh, the user's own logs phase 2 live + medication record + no real details in code; § 11-23 ninth, ranking Part B phase 1 built in shadow; § 11-23 seventh, ranking Part B planned; § 11-23 fifth, agent instructions → code sweep; § 11-23 fourth, Iva's onboarding prerequisites; log § 11-22 first, goal network phase 2 + ranking Part A; § 11-22 second, the user's own logs phase 1). **VM at `95c3ce7` (Mike, 11-23).** **Agent instructions → code: swept, reviewed, ruled, not built.** Findings and Mike's rulings D1–D13 are in `archive/plans/agent_instructions_to_code_sweep_2026-11-23.md` § 6. The build runs from `archive/handoffs/2026-11-23-instructions-to-code-build-driver-prompt.md` (Opus, high): one chat, two Red rounds, the review's misses included (18 of 19), stops at commit and push. **Unblocked 11-23:** "Medication taken today" is live (`95c3ce7`) — the build's missed-dose step (#8) calls `tools.obligations.medication_taken(persona=p)` and keys on each row's `missed`. `[DB-0810-11]` is closed. **Capture fidelity SWITCHED ON in `f878ead` — DEPLOYED 11-21 with `52a1c8b`: ordinary turns in shadow, first interviews show the note; precision 87% vs a 90% floor, accepted by Mike (plan § 10). After deploy and a day of use, VM: `cd ~/multi-model-mcp && .venv/bin/python -m tools.capture --report --persona mike` — pass: "extractor ran on N of N", `held_out_*` only; Iva's first interview, same with her persona. Before the Synthesizer goes `on`: an "already held" check for the new kinds. **The user's own logs — phases 1–2 LIVE** (`custom_logs_and_places_plan_2026-11-21.md`; log §§ 11-22 second, 11-23 eleventh): start/add/read/change/archive a log; **entries now file themselves** (derived writer ON, M4 28/28 as built), new lists are noticed and offered on a card, meals get a time by rule, one entry per thing, `remove_entry`/`restore_entry`; templates Podcasts, Gift ideas (linked to the contact), Notable experiences, and read-only **Medication taken today** (one dose record per medicine, `missed` computed in code, PH's `MEDICATION_TAKEN:` recorded by code; A4 4/4 PASS incl. PH-MED-UNLINKED; mike's two optional supplements wired). **Owed:** after a week of use, VM `.venv/bin/python -m tools.noticed_logs --report --persona mike` — noticed-list yes rate and derived entries. **Next: phase 3, Places** (no prompt yet; M3 seeds mike's three places) — after the instructions-to-code build. Places key checked 11-21: set, in the live server, a real lookup returned OK. The 08-28 location ruling is amended (plan R24, R33). **Goal–task network phases 1–2 and ranking Part A are LIVE** (plan §§ 14–16; log § 11-22 first): a goal stated in chat is checked in one question and planned out of sight (the taxes: 9 steps, sign-in done); every task is weighed — by its opener, else `task_judge` (16 judged on deploy) — unjudged past 60 min reads vital; plan steps are never missable; deadlines climb (`ramp_days` 14). Live checks 1–4 passed 11-22. **Deployed 11-22 with the logs follow-ups:** `e6a661c` (a waiting step no longer blocks "I did X"), `deed121` (a goal link takes the goal's priority), `d1aaa01` (Drop on a step others wait on names what it stops and asks "Drop anyway" — the "on purpose?" check, after three live turns showed Synth never asks it afterwards); Update… and Drop anyway are on Mike's phone since 11-23 (the waprobe build bundles the current page). **Owed by 11-24:** see Drop anyway once in the browser; note whether tomorrow's brief asks the blue-box test question; then remove the test tasks (backlog). Revert: flags `project_planner`/`task_judge`/`prep_tasks`/`horizon_cap` off, `ramp_days: 0`. **Ranking Part B phase 1 — BUILT and DEPLOYED in shadow (`05f3110`, 11-23)** (log § 11-23 ninth; plan `archive/plans/ranking_values_plan_2026-11-23.md` § 11a). `cost_record` is live (the judge recorded 21/21 at 14:06); `ranking_v2` is off and each build writes the regret-of-delay order beside Part A's. **The three-morning comparison is in the backlog (Mike, 11-23: build on)** — it gates only the flip; read three mornings in one sitting with `--day` by ~12-07 (14 days kept), walkthrough `archive/handoffs/2026-11-23-ranking-phase-1-shadow-comparison-walkthrough.md`. **Phase 2 — BUILT and DEPLOYED in shadow (`e134948`, Mike 11-23; log § 11-23 thirteenth, plan § 11b):** protected time given up only on the user's `answer_ask` yes; "behind" (quick wins lead; a slip raised twice, then the weekly list; 3 prompts a day); passions (tied to mission/goals); `enjoyed`; probe at mention. Flags `protected_v2`/`behind_v2` off, inert until `ranking_v2`. **`lookup_public_fact` ON** (`129f3fb`; $14/1,000 queries, 5,000 free a month; figures refused; 5 a day; revert `lookups.enabled: false`; re-check the price at Gemini's 2027-01-01 change). **Its three checks are in the backlog Inbox (Mike, 11-23):** the protected-time and behind shadows (three days each, by ~12-07), and the live check — which starts by confirming the VM has `129f3fb` and carries the passion-tie confirmation. **Next: phase 3** — `archive/handoffs/2026-11-23-ranking-part-b-phase-3-build-prompt.md` (Opus, high). **The 11-05 review's High and Medium findings are fixed and DEPLOYED** (VM at
`968a8a0`; plan with Mike's Phase 1 calls at its end: `archive/plans/codebase_review_fixes_plan_2026-11-11.md`;
log § 11-11). 5 of 7 Highs closed. **Held by Mike, recorded only in that plan:** #5 (a nudge due near
a fixed session is dropped — **fixed in `98f158f` + travel nudges in `52a1c8b`, live**), #9 (Build cannot land — fix before the next `/build` run), #10, #33.
**Iva's prerequisites are DONE and DEPLOYED (`ca7d05c`, log § 11-23 fourth):** #40, #41, the sync reads every active account, the first interview gathers people and practicalities (#11 ruled 11-18). Skipped:
#29. Lows wait for the next review. **Iva has not signed up yet; APK built 11-23 (sha `4352d3c6`, served on the Mac's :8889).** Caps stay $100/$175 — watch spend once she joins (est. above the soft cap; Gemini doubles 2027-01-01).
**Mike (optional): delete `~/multi-model-mcp/.env.bak-2026-11-11` on the VM (holds the removed API
key); check a moved event keeps its reminder.** **Synth now/next (`547c446`) went live with it** —
live-checked on the VM 11-18: three misses (plan § 12) — M2 and M3 now built in phase 1, M1 left as is (Mike). `mike`'s goals updated
on the VM 11-18 (ids + Bulgarian/taxes/Prudential). **Next: Iva's onboarding walkthrough** (M, with Iva, ~1½–2 h)
(`archive/handoffs/2026-11-23-iva-onboarding-walkthrough-prompt.md`, Opus; supersedes 10-29); M3 restarts on her approval day; `/backlog deep`, then
`archive/handoffs/2026-10-30-backlog-attack-signout-calendar-text-forward-trail-prompt.md`;
reply latency (with `[DB-1029-09]`); Sign out; security `[DB-1029-20]`;
**WhatsApp:** Phase 1 (VM side) deployed 11-23, channel off; **Phase 2 planned, reviewed and ruled 11-23** (Step 0 passed on real data); next the build (`archive/handoffs/2026-11-23-whatsapp-phase-2-build-driver-prompt.md`, concurrent workers), then Mike's walkthrough and M4 (§ Current state);
day-planner live checks `[DB-1029-01]` (due 10-31; the check script is already on the VM — no deploy needed); nine fixes' closes-on checks (11-12). **The
meals habit still doesn't exist** — Mike re-asks as "open a daily habit…". **Still owed:** the
boys' school hours/bedtimes → `children_home`; the "over and out" live check; Mike's calendar live
check (week of 9 Nov); `[DB-0901-02]`, due 12-15. **Non-Metatron, paused mid-chat 11-18:** Founder's Associate hiring brief + internal interview process in `archive/plans/founders_associate_*_2026-11-18.md` (log § 11-18 fourth); next is drafting the test materials with Mike. **Cardiac log:** health notes no longer overwrite (`23f1e59`, deployed); log rebuilt to `archive/cardiac_events` — re-run 11-18, remove the routing line 11-21, `[DB-1113-01]`.*

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
| **Mark 2 is ENDED; Mark 1 continues and takes new features** (Mike, 11-18). The 09-02 "Mark 1 bugfix-only" freeze and every "deferred/folded into Mark 2" are void. Items that were parked there — calendar guest management (OAuth), the Darwin key `[DB-0818-04]`, A7 checks 10/12, A8, the Goals Interviewer overhaul — need a Mark 1 home; none waits on Mark 2 | banner on `archive/plans/mark2_endeavour_plan_2026-09-02.md` |
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

A voice-first personal AI life manager — a director and companion for a human life, not a scheduler or task manager. Built on a thin Python harness (`core/orchestrator.py`) with judgement and policy in editable config files. Config owns judgement and policy; code owns procedure, evidence and anything a rule can decide exactly (D3, 2026-11-23).

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
[archive/PROJECT_LOG.md](archive/PROJECT_LOG.md). VM at `968a8a0` (11-11) — HEAD at that date.

### In progress / next

**A7 — Phase 5 sign-off — BLOCKED on B1 alone.** A1–A6 complete, B2 built, B1a passing. Checks 10
and 12 SKIPPED, A8 CANCELLED (Mike, 09-02 — both folded into Mark 2, **which ended 11-18**; where
they now sit in Mark 1 is Mike's call, not yet made — do not start A8 on this line alone). Left: B1b's calendar, web-page and
CardDAV rows (gated on Track E), A5b/A5c, `[DB-0804-02]`. **[ROADMAP.md](ROADMAP.md) § Track A/B
owns the per-item detail and the standing evidence.**

**DAY PLANNER — every switch on (2026-10-29); live checks owed, `[DB-1029-01]`.** Synth runs the
user's day from a plan code keeps current. Stage C delivers it as native FCM push with the app
closed (D1 b), through a separate Firebase project `metatron-push`, with Done / Not yet / Skipped
on each task. Step 2 turned on `nudges` and `owns_checkins`; either off restores the fixed
check-ins exactly. **R2 amended 2026-10-30:** Synth sees now/next/free/Important, not the whole
day (`547c446`). Reshuffle thinking is 0. Plan: [day_planner_plan_2026-10-24.md](archive/plans/day_planner_plan_2026-10-24.md)
(§ 18 round 2); Stage B: `archive/PROJECT_LOG.md` § 2026-10-27; Stage C and step 2: § 2026-10-29.

**WHATSAPP INPUT — Phase 1, VM side, BUILT and DEPLOYED (`e45c7cd`, Mike: "as rec", 11-23);
the channel is OFF for every user.** What the VM does with a message (§ 0), Mike's rulings A–D,
and the endpoint contract Phase 2 builds to (§ 2.2):
[whatsapp_phase1_build_plan_2026-11-23.md](archive/plans/whatsapp_phase1_build_plan_2026-11-23.md);
log § 11-23 eighth. **DEPLOYED 11-23 13:27** (by another chat; VM at `388a91c`, which includes
`e45c7cd`; deps installed, both units active). **Post-deploy intake sweep checked: PASS** (VM 15:01, "2 new — 2 unclear", no warnings).
**Interval jobs now keep to the clock** (`core/scheduler.py`, Fable-reviewed and verified): polling
cadences under 6 h run on a grid from midnight, so a deploy no longer delays them — reminders keep
their old timing; **deploys with the next routine one**. **M2 DROPPED as the gate (Mike, 11-23):
real use is the baseline**, tuned from what he sees (plan § 4; log § 11-23 tenth). **Phone reader
reviewed and hardened 11-23; met real data in Phase 2 Step 0** (9/9 increments, windows 547/362).
**PHASE 2 PLANNED, REVIEWED (Fable, all closed) AND RULED 11-23** (log § 11-23 fourteenth; plan
`archive/plans/whatsapp_phase2_build_plan_2026-11-23.md` § 5): one APK for every user, nothing
active until the VM reports consent; the VM extended; replies by photo/voice/document count.
**Next: the build** — `archive/handoffs/2026-11-23-whatsapp-phase-2-build-driver-prompt.md` (Opus,
high; concurrent worktree workers; stops at commit); **then (M) a ~40-min walkthrough:** deploy →
seed `mike`'s consent only → sideload `debug`, pair, key, chats → read the dry run → rest of M4.
Mike's phone runs `waprobe` until then (`docs/INFRASTRUCTURE.md` § APK). Clean room still binds:
no transcripts; WhatsApp log entries only 10-30-02 and fragments titled "clean-room"; never the
other phrase in a clean-room fragment's first heading (the write-time briefing fails closed).

**A9 — built and deployed 2026-08-18; `@waiting` on real use, review `2026-10-01`.** Spec, the
five provisional parts and the date: [ROADMAP.md](ROADMAP.md) § A9a, the single home.

**BUILD — paused for Mike to revisit or revise (11-18: "not sure I'm happy with it"); the goal–task
network does not depend on it.** State unchanged since 09-26: F1 run 1 stopped on two defects
(`archive/handoffs/2026-09-26-build-phase-F1.md`), and review finding 9 says no capability can land
as coded. Plan and reasoning: [build_vertical_plan_2026-09-24.md](archive/plans/build_vertical_plan_2026-09-24.md),
`archive/PROJECT_LOG.md` § 2026-09-24 → 09-26. **If resumed: `omitClaudeMd: true` is SILENTLY
IGNORED below Claude Code 2.1.271** — bench test 2 (`archive/plans/inquiry_rewrite_2026-09-26.md`) would measure nothing.

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
