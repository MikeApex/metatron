# Session Primer — Personal AI Life Manager
*Updated: 2026-08-03 (4th window, close) — **doc drift reconciled, and the drift rule generalised.** The previous window's HTTPS correction is confirmed correct **against the live VM**, not just internally: `https://.../health` → `{"status":"ok"}`, `http://` → empty reply. Two things it missed, both now fixed: (1) `core/server.py`'s docstring still said "over HTTP" while `__main__` serves HTTPS whenever a Tailscale cert is present — **fixing the prose in CLAUDE.md did not prompt anyone to check the code comment saying the same wrong thing**; (2) the VM's **ephemeral external IP was recorded in four places with three different values**, none wrong when written, live being a third address — the literal is now removed everywhere in favour of a `gcloud describe` lookup, because the IP reassigns on every stop/start and there is an active pause/resume workflow. **New standing rule: do not write down values with a short half-life.** Backlog entry filed as the pattern, not the two bugs — this drift class is invisible to reading and only fails on execution; a smoke script over CLAUDE.md's executable claims is scoped but unbuilt. **`deploy.sh`'s HEAD assertion exercised its match path on a real deploy for the first time** (previously simulation-tested only) — `Verified: VM HEAD matches.` Deployed `b83f283`.*
*Updated: 2026-08-03 (3rd window, close) — **`./deploy.sh` now verifies itself.** It captures HEAD after the push, re-SSHes after the restart, and **exits non-zero if the VM is not running what was just pushed** — because the failure mode here is silence, not an error (two false "deployed" records on 2026-08-02, both caught only by a human happening to look). An unreadable remote HEAD reports **unverified**, deliberately distinct from success or failure. Failure paths are simulation-tested only; the next real deploy exercises the match path. Four loose items filed into `DEV_BACKLOG.md`, including **two corrections to what was believed done:** (1) **check-in activity gating is only half solved** — the gates shipped this morning stop check-ins interrupting a live conversation, but nothing stops them firing on a day the user never spoke, which was the actual cost case; (2) **roadmap D2 item 5 is mis-scoped** — it targets the Coordinator assuming ~7 turns, but measurement shows Coordinator = 1 turn and `logistics` = 8. Pushed through `9799ba3`. Note the new assertion tells you *what* is live, not *who* deployed it — with parallel windows open, either window's deploy ships whatever both have committed.*

*Updated: 2026-08-03 (2nd window, close) — **Rule Redundancy done: every behavioural rule now has one home, checked at three speeds.** The five duplicated preferences are gone from the live `mike.md` (5 audit findings → 1). `write_persona` warns at write time; `daily_rule_audit` sweeps at 05:30 as a `function:` job costing **zero model tokens**, reporting each finding once into `DEV_BACKLOG.md`. Layer-ownership table in CLAUDE.md → **One Home Per Rule Class**. Morning/evening sessions are **not interruptible** — they redirect openly rather than folding in. Deployed through `a03ed7e`. Earlier this window: check-in restraint live (60m quiet / 180m floor); the VM formally owns persona config — `deploy.sh` must never push it; `write_profile`/`read_profile` capture biographical facts with contact details kept out of every prompt.*

*Updated: 2026-08-03 — **the calendar now delivers.** CalDAV live with recurrence, alarms and all-day events; `get_weather` + `get_environmental_snapshot` built; tool permissions shipped in warn mode with denials feeding `DEV_BACKLOG.md`; VM backup closes a real single point of failure. Deployed `cfcd212`, `6865058`. **Phase 4 (scheduler write access) is written but uncommitted — one step from done.** The SEQ 021 fixes noted below as undeployed have since shipped in `6601479`. Earlier: spend guard + rate limiter live; GCP verified clean and `default` VPC unfrozen; Synthesizer recap and timestamp fixes deployed. Update this file at the close of every chat so the next chat — or any parallel chat window — starts from current state.*

---

## What this is

A voice-first personal AI life manager — a director and companion for a human life, not a scheduler or task manager. Built on a thin Python harness (`core/orchestrator.py`) with all behavior living in editable config files. Config files are the product; code is infrastructure.

---

## Read these before doing anything

1. **[CLAUDE.md](CLAUDE.md)** — architecture, conventions, terminology, design principles. Auto-loaded into every session but read actively on first session.
2. **[archive/plans/phase5_to_future_roadmap_2026-06-10.md](archive/plans/phase5_to_future_roadmap_2026-06-10.md)** — the current execution plan (supersedes the 2026-06-09 draft in full). Six parallel tracks (A–F) with embedded test criteria, phase gates, agent backlogs, and the binding privacy ruling in Section 0. Start here for any planning or build work.
3. **[~/.claude/projects/-Users-md-homefolder-Desktop-multi-model-mcp/memory/MEMORY.md](~/.claude/projects/-Users-md-homefolder-Desktop-multi-model-mcp/memory/MEMORY.md)** — working preferences and project memory index. Read to understand decisions already made and how to collaborate.

If you need to find a specific file, tool, or planning document: **[CODEBASE_INDEX.md](CODEBASE_INDEX.md)**.

---

## Current state — Phase 5 (close)

**Phase 5 intent:** Coordinator Agent + Specialist Modules

### Done
- Coordinator-Synthesizer two-pass pipeline (`core/orchestrator.py:621`)
- All 14 specialist agent files (coordinator, synthesizer, diarist, mental_wellbeing, physical_health, work_vocation, relationships, learning_growth, finance, recreation_hobbies, research_agent, logistics, pattern_miner, goals_interviewer) — **all received deep passes**
- **Phase 5 agent review complete (2026-06-13):** All 14 agents done. Flag consistency audit complete. Research Agent extended: grounded Gemini search implemented in orchestrator (`run_session_gemini_grounded`), decontextualization hardened (constitution stripped from Research system prompt, intent/circumstance stripping added to Coord + Synth). `google-genai` v2.8.0 installed in venv.
- CRM tools (`tools/crm.py`), Wishes shell (`tools/wishes.py`), CalDAV (`tools/caldav.py`)
- Parallel subagent dispatch, write_log threading lock, agent_config tool
- Security: threat model + security backlog complete (`archive/security/`)

### In progress / next (numbering per 2026-06-10 roadmap — note: renumbered from the 2026-06-09 draft)

**Parallel chats (2026-06-11 batch) — status as of 2026-06-19:** A1, A2, A3, A4+A6 all complete. B1 (red team), Check 10 (agent audits), and Check 12 (constitution review) on hold — see below. See [archive/plans/parallel_chats_index_2026-06-11.md](archive/plans/parallel_chats_index_2026-06-11.md) for prompt files and file-ownership rules.

**Active priority (2026-06-19):** streamline agent flow to reduce response latency — get the tool functionally usable before completing sign-off work. B1/Check10/Check12 resume after latency work stabilises the pipeline.

**Latency work done (2026-06-19):**
- Model tiering: coordinator + 6 specialists → Flash; coordinator reverted to Pro (Flash skips tool calls unreliably); 6 specialists remain on Flash
- Diarist fire-and-forget: code-enforced in `tools/subagent.py` — confirmed working; excluded from SPECIALIST_OUTPUTS
- quick_override added to `routing_cloud.yaml` (Flash) — diarist routes correctly via quick_override path
- Prefix caching: recent context moved to user message in `_run_single_agent()` — system prompt stable per agent
- Output compression: Recreation → compact JSON confirmed working; Logistics / Work/Vocation next
- **Native SDK migration:** reverted — `run_session_gemini` now routes through `_openai_compat_loop` + `_resolve_gemini_credentials` (Vertex OpenAI-compat endpoint). The native genai SDK (`_run_gemini_native_loop`) is retained but unused; migration was abandoned due to an unworkable Vertex thought_signature bug (see below).
- **Streaming:** complete. `POST /session/stream` SSE endpoint live. Anthropic streaming confirmed working. Gemini streaming via `_openai_compat_stream` wired up. PWA client-side SSE consumption deferred.
- **Vertex thought_signature bug — fixed:** When Vertex returns N parallel tool calls, only tc0 gets a cryptographically valid `thought_signature` in `extra_content`. Fix in `_openai_compat_loop`: `message.model_copy(update={"tool_calls": [tc0]})` — trim to single signed call, execute it, let model re-call tc1+ individually. Cost: parallel calls become sequential turns. No 400 errors in testing (turn=6+ confirmed).
- **HF_TOKEN:** read-only token added to `.env` ✓
- Coordinator slimming: handed off to new chat — target ≤3 turns, ≤40K tokens (currently 6 turns, 88K)
- Coord package debug print active in `core/orchestrator.py` (dev — remove before Beta)
- Baseline: 16–20s simple session, 65–74s complex multi-specialist. Was 60–90s.

- ~~**A1** Compliance curve design conversation~~ — **done 2026-06-18.** All four design questions resolved. Shared principle + Synthesizer integrator (Q1); user-reported cold-start, ratchet research-gated (Q2); Synthesizer level only (Q3); nothing activates at A5c, produces plan only (Q4). Decision doc: `archive/plans/compliance_curve_decision_2026-06-13.md`. Agent file edits queued (apply when A2 chat closes). MCP server updates: o3+o1+auto-discovery added to ask_gpt; auto-discovery added to ask_gemini; Opus timeout fixed (600s) in ask_claude.
- ~~**A2** Logging Layer~~ — **done 2026-06-13.** `write_quality_event` in `tools/logger.py`, ROUTING_MISS wired in synthesizer.md, USER_CORRECTION in coordinator.md, PWA tap (`·` dot → `/feedback`). Tests deferred to Alpha launch (`tests/phase5_testing_plan.md` → Known gaps).
- ~~**A3** Cold-start baselines~~ — **done 2026-06-18.** 4 new functions in `tools/baselines.py`: `create_semantic_anchor`, `write_aspirational_baseline`, `shuffled_null_score`, `score_against_anchors`. All 8 canonical anchors written to `data/baselines/semantic_anchors.json`. All 3 roadmap tests pass. Truncated Goals Interview run-guide in `archive/sessions/2026-06-18 — A3 Cold-Start Baselines.md`. A5b re-run pending (after full Goals Interview).
- ~~**A4** Local routing enforcement~~ — **done 2026-06-13.** `local_enabled: true`, fail-closed sensitive routing (no cloud fallbacks), head layer + Learning & Growth + Recreation + Logistics re-tiered local, quick_override guard. MW mania hard-fail: PASS (front-loaded critical instructions). Finance arithmetic: FAIL/deferred D1. Session archive: `2026-06-13 — A4 A6 Local Routing and Token Budget.md`.
- ~~**A5** Goals Interview with real user~~ — **done.** A5b: re-run `write_aspirational_baseline` with existing A5 interview data (replaces A3 placeholder; required for A7 gate — run before A7). A5c preference activation status unknown — confirm if needed. **D1 note:** once VM is provisioned and new features are live, run a fresh Goals Interview + A5b re-run as first-use onboarding on the VM (new D1 item, separate from this A5b).
- ~~**A6** Token budget logging~~ — **done** (all four session paths; 8K warning threshold)
- **A7** Phase 5 sign-off — **blocked** (B1, Check 10, Check 12 on hold pending latency work; A1–A6 all complete). Resume when pipeline is stable.
- **A8** Pre-Alpha code refactor (full program) — **new (added 2026-06-25, scoped 2026-06-26).** Gate: A7 complete. Full module extraction, not just Phase 5 cleanup. `core/orchestrator.py` (1870 lines, 5 concerns) → `core/config.py` + `core/providers.py` + `core/tools.py` + slimmed `core/orchestrator.py`. `core/server.py` → split monitoring endpoints into `core/monitor_api.py`. Remove COORD PACKAGE debug print (line 1616). Update import paths in server, scheduler, subagent, router. Regression gate: A4 clinical-flag scenarios + server startup + full pipeline session + The Book SSE. Note: `run_session_*` functions and `_run_gemini_native_loop` are active switches, not legacy — they stay in `core/providers.py`.
- **B1** Red team — **on hold** (independent of Alpha Gate, but deprioritised — resumes after latency work)
- **Check 10** Agent behavioral audits — **on hold**
- **Check 12** Constitution alignment review — **on hold**

### Also done 2026-08-03 (outage chat closeout — ✅ `networks/default` HAS THAWED; two items carried into the backlog) — `48e17da`, docs only

Full writeup: [archive/sessions/2026-08-03 — Outage Chat Closeout, default Network Thawed, Backlog Carryover.md](archive/sessions/2026-08-03%20—%20Outage%20Chat%20Closeout,%20default%20Network%20Thawed,%20Backlog%20Carryover.md)

**✅ `networks/default` is no longer frozen.** Probe-tested: an instance created on `default` came up `RUNNING` on `10.128.0.4`, then deleted. Google restored it between 07-31 and 08-03, past their own 3–5 business day estimate but without further intervention. The 26-hour outage is fully closed and the support case can be closed. **`CLAUDE.md:339` is now stale** — it still warns future sessions off a network that works. `metatron-vm` stays on `metatron-net`; moving back would mean another rebuild for no gain.

**Two items carried into `DEV_BACKLOG.md`, closing out the 07-30 → 08-03 chat:**

1. **"Unsurfaced opportunities" instrumentation** — new entry under *needs building* › *Troubleshooting signal*. It had lived only as prose in this file since 07-29 and was never carried across when the backlog became the single change-request list on 08-02 — which made it the one item at real risk of aging out silently. Records why the obvious approach fails (**you cannot diff against a ground truth nobody wrote down**) plus three routes: reason-code on the `·` dot, retrospective sweep, and closing the loop on `open_threads`/`follow_ups`. Recommended 1 + 3.
2. **Roadmap D2 item 5** — amended, not duplicated; the existing entry was already correct. What was missing: the roadmap *itself* still says *"6-turn / 88K cumulative token loop"* and still prescribes a `coordinator.md` change, so anyone reading the plan without the backlog gets a fix aimed at the wrong component. The roadmap body was deliberately left alone — it is a dated snapshot, and rewriting it would erase what was believed at the time.

**⚠ Correction carried in from the 5th window: the external-IP saving is withdrawn.** My 07-31 recommendation to drop the VM's "unused" external IP was wrong — it is the only egress path (no Cloud NAT, Private Google Access `False`), so removing it would kill Vertex AI, Tailscale and deploys. The error was reasoning from *"nothing connects inbound"* to *"unused"* without checking egress.

**Generalisable:** when a tracking convention changes, items recorded under the old one do not migrate themselves. Worth sweeping this file's prose for other open items predating 08-02 that were never carried over.

### Also done 2026-08-03 (calendar delivers, weather tools, warn-mode tool permissions, VM backup) — **deployed `cfcd212`, `6865058`**

Full writeup: [archive/sessions/2026-08-03 — Calendar Delivery, Weather Tools, Tool Permissions, VM Backup.md](archive/sessions/2026-08-03%20—%20Calendar%20Delivery,%20Weather%20Tools,%20Tool%20Permissions,%20VM%20Backup.md) · Plan: [capability_gap_gameplan_2026-08-03.md](archive/plans/capability_gap_gameplan_2026-08-03.md)

**The reminder problem is solved.** `write_calendar_event` gained `recurrence` (RRULE), `alarm_minutes_before` (VALARM) and `all_day`. This was the real blocker — the builder emitted a bare one-off `VEVENT` with no alert, so enabling CalDAV alone would have produced a *silent single event*, the same false-success shape as SEQ 021. Credit-card bills now exist as a recurring all-day deadline on a dedicated Metatron calendar.

**CalDAV gotcha, recorded so it is not rediscovered:** `apidata.googleusercontent.com/caldav/v2` **requires OAuth 2.0 and 401s on app passwords** (verified against four URL variants). Use the legacy `https://www.google.com/calendar/dav/{CALENDAR_ID}/events`, which accepts basic auth. A calendar's `.../basic.ics` address is **read-only** — only the ID inside it is useful. Corrected in `config/templates/caldav.yaml`. The same app password authenticates IMAP, which de-risks Phase 5.

**Framework adopted — three kinds of time-bound thing.** *Appointment* (fixed time, should interrupt) → calendar event + alarm. *Deadline* (a day, no time) → all-day event, no alarm, Synth folds it into that day. *Condition* (needs judgement — "water the plants if it hasn't rained") → scheduler job. Prefer the calendar wherever it suffices: no AI at fire time, no cost, visible in the user's own app.

**`get_weather` + `get_environmental_snapshot`** built in `tools/ambient.py`, registered, tested live. `get_weather` adds **recent rainfall** with a computed `days_since_rain` (Open-Meteo — wttr.in only forecasts, but rain decisions are backward-looking). UV is free from the existing wttr.in call; **AQI is not in wttr.in** and comes from Open-Meteo, failing soft. Coordinates reused from `nearest_area` — no geocoding call. **Supersedes roadmap decision 16** (weather-only at E1) by explicit user decision.

**Tool permissions live in WARN mode.** `dispatch_tool` now checks the calling agent's grant. Previously the whitelist filtered what an agent was *shown* but handlers were looked up unfiltered, so any agent could call anything — and because it silently succeeded, nothing recorded that an agent wanted a capability it lacked. Denials emit a **`TOOL_DENIED`** quality event (deduped per agent+tool) which `sync_dev_backlog.py` pulls into `DEV_BACKLOG.md`. Nothing is blocked; flip to `METATRON_TOOL_PERMISSIONS=enforce` once the log is reviewed — required before E1 integrations.

**Standing practice adopted:** (1) the denial audit runs continuously — grant on demonstrated need, never blanket; (2) `DEV_BACKLOG.md` is the single intake; (3) every development is backchecked against the plan for cohesiveness. All nine agent `## Enhancement backlog` sections **mirrored** (not moved) into `DEV_BACKLOG.md`.

**`scripts/metatron-backup.sh` (new)** — nothing on the VM was captured by git; 12MB of real data survived the July rebuild only because the disk was deliberately detached. Pulls VM state to the Mac, verifies before pruning, hardlinks `latest.tgz`; `daily-backup.sh` runs it first and includes only the latest. **Caught real Mac↔VM drift on its first run.** Also fixed: `.env.*` was unignored, so `.env.bak` files would have been committable with every API key.

**Corrections worth carrying:** an audit intended to strip stale tool references found the eight `run_subagent` mentions are *guardrails* reading "do not call `run_subagent` directly" — applying the proposed removals would have deleted the instruction preventing the behaviour. **Net removals: zero.** Separately, the 2026-06-24 token work established the narrow `allowed_tools` lists as deliberate (~95,000t → ~30,000t); widening them to match the agent files would have reversed the project's highest-leverage optimisation. And the agent-backlog token cost measures ~130 tokens total — not worth moving for cost, only for discoverability.

**Phase 4 (scheduler write access) and the tier-editability inversion are both closed** — see the next section.

### Also done 2026-08-03 (Phase 4 scheduler grants · `update_goal` · Tier 1–2 backup) — **deployed `2f74cd2`, `8e2983f`**

**Phase 4 complete.** `write_schedule` / `list_schedules` / `delete_schedule` granted to Synthesizer and Logistics in both routing configs. The tools had shipped registered but allowlisted to nobody, so nothing could call them. Verified on the VM. Tested before deploy: every cap refuses with a message naming what to drop; a one-off created *after* the daemon started armed within one 30s tick, fired once and self-deleted; a name collision with the user's `scheduler.yaml` resolves in the user's favour.

**Two agent instructions named an impossible action.** `synthesizer.md` and `logistics.md` both said to create recurring reminders with `write_config` — which permits only `prime_directive.md` and `mission.md`, so the call returns an error the user never sees. The SEQ 021 failure shape, sitting unfired because nothing had asked for a recurring reminder since. Both now point at `write_schedule`. `synthesizer.md` also claimed every specialist tool was available to it directly — false under the whitelist, and in warn mode it produces a denial rather than a refusal the model can act on.

**Tier-editability inversion — CLOSED.** New `update_goal(action, ...)` adds / updates / completes / removes **one** goal and touches nothing else; `write_goals` replaces a whole horizon, so any omitted goal was silently deleted. `complete` keeps the goal with a `completed_on` date; `remove` is for abandoned or mistaken entries only. Granted to the **Synthesizer** (where a goal is actually finished or taken on — mid-conversation) and to `goals_interviewer`, which already holds the stronger tool. `write_goals` stays with the interviewer alone, its schema now warning that omission deletes. Separately, **`write_config` now keeps the previous `prime_directive.md` / `mission.md` before overwriting** — held by the agent that runs every exchange, and a full replacement, so an unasked-for rewrite was unrecoverable. Backups are gitignored (`config/personas/*/*.bak`) — Tier 1–2 content.

**Doc drift corrected:** the server has been serving **HTTPS** on 8001 with a publicly trusted Tailscale cert (`metatron-vm.tail0acc5d.ts.net`), while `CLAUDE.md` documented plain HTTP in five places including the recreate-from-scratch checklist. Found because a health check against `http://` failed.

**Phase 2 of the capability-gap plan (agent-file reconciliation) is CLOSED, not done** — by explicit user decision 2026-08-03. Net removals were already zero, and the remaining question ("what should each agent legitimately hold?") is now answered continuously by the warn-mode denial log rather than in a batch. Handled in real time through `DEV_BACKLOG.md`; nothing further is owed to that plan.

**Still open:** location sharing (phone permission + calendar-derived inference; GPS agreed sensitive-tier, local-only, coarsened); Phase 5 — see [phase5_prompt_2026-08-03_security_web_email.md](archive/plans/phase5_prompt_2026-08-03_security_web_email.md).

### Also done 2026-08-03 (check-in restraint · persona config ownership · biographical capture)

Full writeup: [archive/sessions/2026-08-03 — Check-in Restraint, Persona Config Ownership, Profile Capture.md](archive/sessions/2026-08-03%20—%20Check-in%20Restraint,%20Persona%20Config%20Ownership,%20Profile%20Capture.md) · deployed through `35e53ee`.

**1. Check-in restraint — the cause was not an agent file.** `companion_checkin`'s *own prompt* said "lead with the most useful outstanding item… be specific about which one and why it matters now", every 180 min, all day — so an unresolved calendar item was correctly surfaced six times. Fixed at `config/templates/scheduler.yaml` (the baseline all new personas inherit, which also hardcoded "Mike" in a provisioning template) plus mike's copy. Two opt-in gates added to `core/scheduler.py`: `quiet_after_user_minutes: 60` and `min_gap_minutes: 180`; `interval_minutes` is now the *poll* rate. **Cost strictly lower** — polling is local reads with no model call and the gap preserves the old ~5/day ceiling. Five rules added to `synthesizer.md` (raise a thing once · explain first time not every time · never say "enjoy" · beware the loudest available signal · ask for missing data when the record is thin).

⚠ **Gate keys must never be added before the gate code is deployed** — `interval_minutes: 30` without the gates is a check-in every 30 minutes.

**2. `deploy.sh` MUST NOT push persona config.** `write_persona()` and `write_config()` edit `config/personas/{p}.md`, `prime_directive.md` and `mission.md` **on the VM at runtime**. Verified 2026-08-03: the VM's `mike.md` held five preferences recorded that morning the Mac copy had never seen — a push would have erased them. Stale Mac copies moved to `backups/`; only git-tracked dev personas remain there. Direction is Mac→VM by deliberate one-off `scp`, VM→Mac by `scripts/metatron-backup.sh`. Documented in CLAUDE.md and in a comment block in `deploy.sh` at the point of temptation.

**3. Biographical capture — `tools/profile.py`.** Contact details the user gave while asking for a booking had been filed into `mike.md` and rode in every prompt; moved to `profile.yaml`. A first attempt restricted `write_persona` and **broke the requirement** — users give biographical data in conversation and the tool must capture it — so it was reverted (`8659c4d`) and replaced with `write_profile`/`read_profile` (`35e53ee`). Read is separate from write on purpose: `load_profile()` renders a summary into every head-layer prompt but **excludes the contact block**; agents call `read_profile` at the point of use. Granted to synthesizer, logistics, physical_health, relationships, work_vocation, finance in *both* routing files.

**4. `.claude/commands/*.md` is now tracked** (needs `.claude/*`, not `.claude/` — git will not descend into an excluded directory). **A `.env` backup with live keys was sitting in the repo** (moved to `~/.metatron-secrets-backup`) and `.env` was mode 0644, now 0600.

**5. Ten legacy requests recovered** from `data/personas/mike/conversations/2026-08-0{1,2,3}.jsonl` into `DEV_BACKLOG.md`, predating automatic capture.

### Also done 2026-08-03 (Rule Redundancy — one home per rule class) — **deployed `0077a63`, `a03ed7e`**

Full writeup: [archive/sessions/2026-08-03 — Rule Redundancy: One Home Per Rule Class.md](archive/sessions/2026-08-03%20—%20Rule%20Redundancy:%20One%20Home%20Per%20Rule%20Class.md). All four items of the plan agreed above are **done**. Layer-ownership table: **CLAUDE.md → One Home Per Rule Class**.

**1. The debt is cleared.** All five duplicates removed from the VM's `config/personas/mike.md` (backups at `~/metatron-backups/mike.md.pre-dedup*`); the file is down to two genuinely personal preferences and the live audit went **5 findings → 1**. Each removal was made **only after confirming the replacement was live on the VM**, not merely committed on the Mac — that check caught that the fifth rule was only half-rehomed.

**2. Detection is class-based, not text similarity — and this is the part not to re-derive.** *"Stop repetitive reminders for pending tasks"* and *"Raise a thing once…"* are the same instruction **with almost no words in common**; a word-overlap threshold sweep found 0/5 at 0.45 and 1/5 at 0.25. [`core/rule_classes.py`](core/rule_classes.py) sorts rules into classes, each with an owning layer; similarity only *ranks* candidates within a class. Patterns must match **the complaint, not the instruction** — the first pass missed *"Stop bringing up the same task over and over"* for exactly that reason.

**3. Three checks.** Write time — `write_persona` → `check_new_rule()`, which **warns and never blocks** (refusing a write to keep a file tidy discards what the user actually said; that error was already made and reverted earlier the same day). Daily — `daily_rule_audit` at 05:30, a `function:` job costing **zero model tokens**, findings → `RULE_CONFLICT` → `DEV_BACKLOG.md`, each reported **once**. On demand — `scripts/check_rule_overlap.py`.

> **The daily sweep is the load-bearing one.** The write-time check only sees what Synth writes. *The five duplicates were written by hand, in a development session* — no write-time guard could ever have caught them.

**4. Measured, so a clean report isn't mistaken for proof.** Against the real set: **5/5** recall on which preference is duplicated, **0** false positives across eleven novel preferences, but the *partner* named was wrong **3 times in 5**. The flagged preference is the reliable output. `CLASSES` is incomplete by construction — add one when a duplicate slips through.

**5. Cut deliberately:** agent-vs-agent comparison. The specialist files carry intentional parallel boilerplate (*"Mandatory pass. Runs every session"*, *"Voice mode:"*) that scores near-identical because it is, on purpose — it drowned the real findings. Still available via `check_rule_overlap.py --all-pairs`.

**6. Morning/evening sessions are not interruptible** (user decision, mid-session): they fire on the clock regardless of an active conversation and **redirect openly** — *"Now let's turn to the evening close"* — rather than folding in silently. Only `companion_checkin` yields. Note `_activity_gate_blocks` **skips, it does not defer**: a `time:`-anchored job that blocks is gone for the day, which is why the fixed-time sessions carry no gate.

**7. `data/personas/sarah_chen/` gitignored** — it is the validation-probe persona, so every run writes into that tree. The three seed logs stay tracked; a new fixture needs `git add -f`. Plus never-fixture rules for all personas: `traces/`, `config/`, `schedules.yaml`, `logs/quality_events.json`.

> **Concurrency note.** The parallel window held uncommitted edits to `synthesizer.md`/`logistics.md`/routing files throughout. Handled with surgical `Edit` calls in distant regions, per-file staging, and never `git add -A`. Their `2f74cd2` then swept up both of my `synthesizer.md` rules — **verified present in the deployed file on the VM** rather than inferred from the commit graph, which corrected a backlog entry that wrongly claimed they were pending.

### Also done 2026-08-02 (Synth self-development awareness + `DEV_BACKLOG.md` — the single change-request list)

Full writeup: [archive/sessions/2026-08-02 — Synth Self-Development Awareness and Dev Backlog.md](archive/sessions/2026-08-02%20—%20Synth%20Self-Development%20Awareness%20and%20Dev%20Backlog.md)

**Problem:** Mike is both user and builder, but when he asked for a change mid-conversation it evaporated — no frame for what kind of change it was, and nowhere durable for it to land.

**Now:** the Synthesizer triages a change request into three routes and says which plainly — *handle now* / *needs a change outside this conversation* / *needs building* — then records it. Requests land in **[DEV_BACKLOG.md](DEV_BACKLOG.md)** at the project root, git-tracked and visible in the file tree: `## Inbox` is machine-written, everything below hand-curated.

- **`config/personas/mike/self_development.md`** (new, gitignored, `0600`) — the triage instruction, ~700 tokens. Loaded by `load_config()` only when present, so **no other persona's behaviour changes**.
- **`_persist_dev_request()`** in `core/orchestrator.py` — reads a `dev_request` key off the `[CONTEXT]` block the Synthesizer already emits and calls `write_quality_event()` directly. **Zero extra turns:** a tool call would have cost a second Pro turn (~13.4K input, +$0.017, +3–8s) — exactly the overhead SEQ 031 removed.
- **`scripts/sync_dev_backlog.py`** — stdlib-only, pulls the VM's quality events through the existing `/monitor/file` endpoint over Tailscale, filters to the three request types, dedups on timestamp. 3s timeout, **exits 0 silently when the VM is paused**. Wired into `/metatron-code`.
- **`config/agents/synthesizer.md`** — one pointer line. Freeze lifted on explicit instruction, same exception as SEQ 002/008.

**Cost:** under $0.50/month, no measurable latency change on a normal exchange.

**Plan assumption proved stale, in our favour:** the plan budgeted extracting the `[CONTEXT]` parser into a shared helper. `split_context_block()` / `persist_context_block()` already exist and are already called from **both** pipeline paths — so **SESSION.md backlog item 4 below is stale** and the change collapsed to ~35 lines.

**Two failures found by live testing, both fixed:**
1. **Route 3 recorded nothing.** The instruction said to name the gap *"as you already do for capability gaps"*, which pointed the Synthesizer at the pre-existing `TOOL_NOT_BUILT` open-thread and it skipped `dev_request` entirely — perfect-looking response, empty backlog. Fixed by making the requirement unconditional.
2. **Confidentiality beat self-development.** Asked *"will those changes stick?"*, it emitted the canned *"I'm here to help you manage your life"* — self-generated, not the output filter. A legitimate question about the user's own request got stonewalled. Fixed by carving the boundary explicitly: whether a change stuck is about *his request*, not how the tool is built.

All four probes pass against `sarah_chen` on the real Vertex pipeline. Test artifacts removed afterwards to keep her a clean subject.

**Auto-sync: `SessionStart` hook, added 2026-08-03** (`.claude/settings.local.json`, alongside the existing `Stop` hook). Fires on opening a Claude Code chat in VS Code — and on resume/clear/compact/fork — so `DEV_BACKLOG.md` is current without anyone running the sync. Measured cost: **0.99s reachable, 0.11s with the VM down**, no lingering process. launchd was offered and declined in favour of this, on the grounds of not adding background processes. `/metatron-code` also runs it, for sessions where the hook is off. **Note `.claude/` is gitignored entirely — this hook reaches neither the VM nor GitHub and has no backup.**

**Legacy requests recovered 2026-08-03.** Crawled `data/personas/mike/conversations/2026-08-0{1,2,3}.jsonl` and the `quality_events` stream for asks made before automatic capture existed — **10 recovered into `DEV_BACKLOG.md`** (now 15 open). Notable: check-ins firing during live dialogue (*"only need be done if there's not an ongoing dialogue — otherwise fold them into the conversation"*, SEQ 020) is both the user's request **and** the largest cost lever on record; repetition of pending items (*"you've repeated the calendar thing about six times today"*); over-indexing on one disrupted night (*"once again"* — already raised before); transcription timeouts and dictated-email errors; calendar delivery (corroborates capability-gap Finding 3); and a request to act on an external website, which carries a real security surface since the same message handed over email, postal address and phone number. The 2026-08-01 timestamp request turned out to have been closed by the SEQ 008 fix the next day — filed under Done, not Open.

**Deployed and verified** (commits `6601479` + `dc0d85c`; `6601479` also carries the parallel session's SEQ 021 fixes, since both sat in `core/orchestrator.py`). `NRestarts=0`, both services active. `self_development.md` `scp`'d separately — gitignored, so `deploy.sh` cannot carry it. Post-deploy probe on `mike` over `/session/stream` returned *"held and will carry forward"* and terminated `[DONE]`, not `[RETRACT]`.

**Third bug, caught only at deploy time:** the sync script defaulted to `http://` on the raw Tailscale IP. **The server runs HTTPS** behind a Tailscale cert, and the IP form also fails hostname verification. Since the script fails silent by design it would have reported `0 new` forever instead of erroring. Fixed to `https://metatron-vm.tail0acc5d.ts.net:8001`, matching the orchestrator CLI default.

**⚠ Staging note for future sessions:** `data/personas/sarah_chen/` (and the other synthetic personas) are **not** gitignored — only `mike`, `pepys`, `test_a3` and parts of `ryan_holiday`. A `git add -A` in this tree repeats the 2026-07-29 incident. Everything here was staged by explicit path. **Worth adding gitignore rules for the synthetic persona data trees.**

**Two new backlog entries found in passing:** the `write_config`/`scheduler.yaml` discrepancy (`synthesizer.md:355` promises a capability `tools/config_writer.py:16` forbids — corroborated live by a Logistics tool failure in a tracker held-item), and **silent `[CONTEXT]` data loss** when the model emits malformed JSON (`split_context_block` logs and returns `None`, losing both the tracker write and the `dev_request`).

### Also done 2026-08-02 (SEQ 021 — specialist clock, tool-error hints, failure reporting; capability gap survey) — **DEPLOYED `6601479`**

Full writeup: [archive/sessions/2026-08-02 — SEQ 021 Logistics Turn Burn, Clock Injection, Tool Error Hints.md](archive/sessions/2026-08-02%20—%20SEQ%20021%20Logistics%20Turn%20Burn,%20Clock%20Injection,%20Tool%20Error%20Hints.md)

**Bug:** user asked for a recurring monthly credit-card reminder (`mike`, SEQ 021). Routing was correct — Coordinator 1 turn. **Logistics burned 6 turns, 4 wasted**, saved nothing, and the Synthesizer told the user *"The reminder for the 15th is set."* It was not.

**Three root causes, all confirmed from the trace:**
1. Logistics guessed `write_agent_config`'s parameters three times (`content`, `recurring_obligations`, `data`) and never tried the real `key`/`value`. `dispatch_tool()` returned the bare Python `TypeError`, which says the guess was wrong but not what is right.
2. The three failures never reached the Synthesizer, so it confirmed a save that never happened.
3. **Specialists receive no system clock** — Coordinator/Synthesizer get `recent_context`; specialists get `agent_file` + `goals` only. Logistics invented `log_date: 2025-05-22`, filing the note 14 months in the past.

**Four fixes written and validated locally against `sarah_chen` (full pipeline, real Vertex):**
1. `tools/ambient.py → current_clock_line()` + `core/orchestrator.py → clock_line()`, injected into the specialist branch of `_run_single_agent()` **via the user message** so the cacheable system prefix stays stable.
2. `dispatch_tool()` binds with `inspect.signature().bind()` before calling and returns `Correct usage: write_agent_config(required: agent_name, key, value)`. **Measured:** the same request that previously failed 3× and gave up now self-corrects on attempt 2 and saves.
3. `_failed_tool_calls()` appends `[TOOL FAILURES — these actions did NOT complete]` to specialist output. Excludes head/routing layer, and excludes any tool that later succeeded on retry (or a recovered error would produce a false "it didn't save").
4. Hallucinated `data/personas/mike/logs/2025-05-22.json` moved to `data/diagnostics/bogus_logs/` **on the VM**. No real data lost.

**Resolved 2026-08-03 — committed and deployed.** These fixes were held briefly because `core/orchestrator.py` also carried a parallel chat's uncommitted work; that chat committed both sets together in `6601479` and the VM now runs them. No action outstanding.

**Deliverable — [archive/plans/agent_capability_gap_2026-08-02.md](archive/plans/agent_capability_gap_2026-08-02.md).** Written instead of reconciling `logistics.md` downward, at user's direction, since a calendar is arriving shortly. Headlines:
- **Finding 0 (security):** the per-agent tool whitelist filters `tool_schemas` but **not** `tool_handlers`, and `dispatch_tool()` does no whitelist check — **any agent can invoke any of the 43 tools.** Proven live: `logistics` is not granted `write_agent_config` yet called it three times in production and the dispatcher executed each. **Implication: every "told-but-not-offered" capability currently works by accident, so closing this (Track B / B2 PoLP) without first fixing the allowlists breaks them all at once. Fix the lists, then enforce.**
- **Finding 1:** all 13 agents name at least one tool they are not advertised (`logistics` 8, `finance` 7, `recreation_hobbies` 7). `run_subagent` appears in nine specialist files despite a hard recursion guard — dead instructions.
- **Finding 2:** `physical_health.md` names `get_environmental_snapshot`, which does not exist.
- **Finding 3 (behind the original complaint): nothing in the system can actually set a reminder.** CalDAV `enabled: false` with empty password; `scheduler.yaml` jobs are static with no tool to add one; `write_config` allowlisted to `mission.md`/`prime_directive.md`. A reminder can be *recorded* but never *delivered*. Build order: enable CalDAV → grant Logistics its config tools → `write_schedule`/`list_schedules`/`delete_schedule` → store delivery preference.
- **Finding 4:** `WRITE_AGENT_CONFIG_SCHEMA` still documents the pre-persona path `data/config/{agent_name}.json`.

Four agent-file edits **proposed, not applied** — `config/agents/*.md` frozen post-review.

**`/metatron-troubleshoot` rewritten and verified** (`.claude/commands/`, gitignored — Mac-local, no commit/deploy). Fixed six defects after the third consecutive session where its stale paths broke the first data pull: persona-scoped conversation path; persona parameterised (was hardcoded `mike`, nine personas exist); `--tunnel-through-iap`; argument substitution (a real invocation produced `DATE = 2`, `SEQ = $2`); zero-padded SEQ matching with available-values listing on a miss; native ±2-min trace window replacing the exact-minute match. **Added `context_sections` output** — the decisive evidence in this diagnosis, previously needing a separate hand-written query. Tested against live data plus all three error paths. **Note: `.claude/` is gitignored entirely, so this file has no backup and reaches neither the VM nor GitHub — the original was already lost once.**

**Open from this session:** `[background] index log 2025-05-22 failed: Extra data: line 557 column 2 (char 82852)` fired twice against a 276-byte file — offset doesn't match, so the memory indexer is likely reading a different/concatenated source. Unexamined. Pre-2026 logs (`2025-01-24`, `2025-05-13`–`16`) remain in `data/personas/mike/logs/` — believed genuine early-dev data, worth confirming none are further hallucinations.

### Also done 2026-08-02 (Synthesizer timestamp-authority fix — SEQ 008 diagnosis, fix, deploy, verified)

Full writeup: [archive/sessions/2026-08-02 — SEQ 008 Timestamp Fix, Deploy, Pepys Test.md](archive/sessions/2026-08-02%20—%20SEQ%20008%20Timestamp%20Fix%2C%20Deploy%2C%20Pepys%20Test.md) · Commit `b184d92`, deployed.

**Bug:** Synthesizer echoed a user-claimed timestamp instead of checking the actual system clock (2026-08-01, SEQ 008, `mike` persona — "953" boundary test). Diagnosed via `/metatron-troubleshoot`.

**Fix (three parts, all landed):**
1. `tools/ambient.py` — ambient date/time now second-precision, labeled "authoritative" in context.
2. `config/agents/coordinator.md` + `synthesizer.md` — explicit instruction to trust the system clock over user-claimed times. **These files are frozen post-review** — edited on explicit user instruction ("fix this now") for this specific bug, not a general exception to the freeze.
3. `core/server.py` + `core/orchestrator.py` — WebSocket/SSE handlers now stamp the actual message-receipt time and thread it into both Coordinator and Synthesizer input (`run_pipeline_session_stream` → `_run_pipeline_session_stream_inner`). This mattered most: pipeline latency (this trace ~30s end-to-end) means "current time" at generation-time is already stale relative to actual arrival. Non-streaming `run_session()` (scheduler/CLI/proactive) intentionally untouched.

**Verified against `pepys` (non-Mike persona)** post-deploy: replayed the original bug pattern via `/session/stream` — user falsely claimed "3:00pm exactly," Synthesizer correctly responded "I received that message at exactly 9:24:41 AM" instead of echoing the claim.

**Known stale artifact, not yet fixed:** `/metatron-troubleshoot` command template still points at pre-persona-scoping paths (bare `data/conversations/`, `data/personas/mike/traces/` hardcoded to mike) — corrected inline this session but not on disk. Low priority, flag for a future pass.

### Also done 2026-08-02 (spend guard, GCP verification, scroll root-cause)

Full writeup: [archive/sessions/2026-07-28 — Persona Unification Complete (Phases 0-8, Strict Mode Live).md](archive/sessions/2026-07-28%20—%20Persona%20Unification%20Complete%20(Phases%200-8,%20Strict%20Mode%20Live).md) (2026-08-02 section at the end).

**GCP account verified genuinely clean.** Created a throwaway instance **on `default`** — the exact operation that failed with `networks/default … is not ready` on 2026-07-30. It reached RUNNING, so Google's thaw did eventually complete. Probe deleted. Billing enabled; hard cap **armed** (the override expired 2026-07-31 — its leftover marker was removed, since it read as "hard cap disarmed"); no orphaned disks or static IPs. Only leftover is the pre-unfreeze snapshot (8.5GB, ~$0.22/mo).

**Spend guard live** (`core/spend_guard.py` + `config/modules/spend_guard.yaml`). GCP budget data lags hours, so the $70/$150 caps cannot catch a loop. Two in-process guards, hooked into `trace.record_turn_tokens` (the one point every provider already reports through):
- **Rate limit** — sessions per rolling hour, alert 20 / stop 60. Needs no pricing data, so it survives a stale rate table. **This is the guard that actually catches a loop.**
- **Spend limit** — token counts × rates, alert $5/day / stop $10/day.

Refusal returns plain user-facing text, not an exception. Both fail **open** on internal error — a bug in cost accounting must never take down a working assistant. Rate-limiter state is in-memory, so it resets on restart (acceptable: a restart breaks a loop).

**Costing bug caught by user challenge — reported figure was 8x too high.** Pricing keys were unprefixed but traces record `models/gemini-3.1-flash-lite`, so every lookup missed and fell through to `default`, set to Pro rates. All the Flash-Lite traffic — the bulk of every exchange — was priced at ~12x. Corrected: an exchange is **~$0.025, not $0.20**; a scheduled day **~$0.18, not $1.41**. Fixed with prefix normalisation, prefix-match fallback, and a warning on unknown models rather than silent defaulting.

**Measured token economics** (real): one exchange = 82,360 input tokens across coordinator (Flash-Lite, 1 turn), logistics (Flash-Lite, **8 turns**, 39,810t), physical_health (Flash-Lite, 5 turns), synthesizer (**Pro**, 1 turn, 12,989t). **The synthesizer is 71% of cost on 16% of tokens**, being the only agent on Pro — so it, not the Flash-Lite specialists, is the cost lever. Reconfirms the coordinator does 1 turn while specialists do 5-8: roadmap D2 item 5 is **mis-scoped** and needs re-measuring before any work.

**Conversation scroll — earlier fix was a no-op.** `body` used `min-height:100dvh`, so it grew past the viewport and `#conversation` (`flex:1`) expanded to fit content instead of being capped — it was never a scroll container, making `overflow-y`, `margin-top:auto` and `scrollTop` all inert. Fixed with `height:100dvh` + `overflow:hidden` on body and `min-height:0` on the flex child. **Testable in a desktop browser without installing the APK.**

**Open:** pricing rates are unverified estimates marked VERIFY (fine for order-of-magnitude runaway, not for accounting); activity-gating for check-ins; sentence-chunked TTS; browser live-refresh bug; turn-reduction re-scoping.

### Also done 2026-08-02 (Synthesizer recap fix — SEQ 002 diagnosis, fix, local validation — **NOW DEPLOYED**)

Full writeup: [archive/sessions/2026-08-02 — SEQ 002 Single Exchange Troubleshoot.md](archive/sessions/2026-08-02%20—%20SEQ%20002%20Single%20Exchange%20Troubleshoot.md)

**Bug:** Synthesizer opened a response by restating specific facts the user had just given (dinosaurs, hedge maze, Sainsbury's meal deal — `mike` persona, SEQ 002) instead of acknowledging their meaning. No pipeline failure — correct routing, no filter hits — pure content-quality gap. Diagnosed via `/metatron-troubleshoot` (same stale-path issue as SEQ 008 above: had to fall back to `data/personas/mike/conversations/` and `--tunnel-through-iap` for SSH).

**Fix:** One sentence added to `config/agents/synthesizer.md` under "Direction and prioritization": *"Acknowledge, don't recap. Do not restate specific facts the user just gave you... as a summary opener... They already know what they told you; repeating it adds no value and reads as filler."* Frozen post-review file — **freeze lifted on explicit user instruction** for this fix, not a general exception. A longer first draft was cut per user direction — keep agent instruction files token-light.

**Validated locally; DEPLOYED 2026-08-02** (commit `799aa3f` went out with the spend-guard deploys from the parallel session — VM confirmed to carry the line). Original note follows:

**Validated locally, not yet deployed:** 3 iterations against `sarah_chen` (non-Mike dev persona) via `python3 core/orchestrator.py --persona sarah_chen --input "..."` (local Mac, `DEPLOYMENT_MODE=cloud` → real Vertex/Gemini pipeline). All 3 messages carried specific facts (museum/planetarium/pizza; skipped breakfast/coffee/sandwich/dentist; river run/stir fry) — no readback in any response. **`./deploy.sh` still needed** to push this to metatron-vm before it affects the live Mike sessions.

### Also done 2026-07-31 (⚠ 26-HOUR OUTAGE — VPC frozen by billing disable; VM rebuilt on a new network; cost control restructured)

Full writeup: [archive/sessions/2026-07-31 — Billing Cap Trip, VPC Freeze Recovery, Two-Tier Cost Control.md](archive/sessions/2026-07-31%20—%20Billing%20Cap%20Trip,%20VPC%20Freeze%20Recovery,%20Two-Tier%20Cost%20Control.md) · Commit `571f9bc`, deployed.

**⚠ ~~`networks/default` IN THIS PROJECT IS STILL FROZEN.~~ SUPERSEDED 2026-08-02 — `default` is UNFROZEN, verified by creating a live instance on it (the exact operation that failed on 2026-07-30). Google's thaw did eventually run. The VM stays on `metatron-net` by choice, not necessity.** The VM now runs on a new VPC, `metatron-net` / `metatron-subnet` (`10.10.0.0/24`). Anything that assumes `default` exists will fail. Google support case left open to get `default` restored; tech team estimate was 3–5 business days.

**What happened.** `stop-billing` disabled billing at ~$31 against a budget already raised to $40, acting on a stale notification. Disabling billing froze the project VPC. Billing was relinked within hours, but Google's asynchronous thaw **never ran** — 25+ hours of `nic0 is frozen`. Recovered by building a new VPC and rebuilding `metatron-vm` on it from the existing boot disk. Tailscale reclaimed the same node identity, so `100.64.226.49` is unchanged and **no client changes were needed**.

**Cost control restructured** — the hard cap is now a firebreak, not a routine control. Distinction is recovery cost, not dollars:

| Tier | Amount | Action | Recovery |
|---|---|---|---|
| Soft | $70 | `stop-vm` stops the VM | ~60s |
| Hard | $150 | `stop-billing` disables billing | Days, plus a frozen VPC |

New `stop-vm` function source is tracked at [infra/stop-vm/](infra/stop-vm/) — deployed, ACTIVE, tested. Override at `scripts/metatron-vm-override.sh` writes a *separate* marker from the billing override so silencing one cannot silence the other.

**This sits directly on top of the 2026-07-30 arithmetic below:** if infrastructure alone is ~$29/mo, a $70 soft cap leaves ~$40/mo of genuine AI headroom before anything stops.

**Bugs fixed:** `metatron-resume.sh` wrote the billing override *before* relinking — but the marker lives in a bucket inside the disabled project, so the write always 403'd and `set -e` aborted before the relink. **That recovery path had never once completed.** Also `deploy.sh` + resume now need `--tunnel-through-iap`, since `metatron-net` has no public SSH ingress (verified with a real deploy).

~~**Check when convenient:** the rebuilt VM has an unused ephemeral external IP; removing it saves ~$2.90/mo.~~ **Withdrawn 2026-08-03 — do not act on this.** The IP is unused for *inbound* but is the VM's **only egress path**: there is no Cloud NAT (`routers list` → 0) and Private Google Access is `False`, so removing it kills Vertex AI, Tailscale bootstrap, deploys and every outbound call. Cloud NAT needs a public IP at the *same* $0.005/hr and adds gateway + data charges, so it costs strictly more. The real figure is ~$3.65/mo (catalog rate $0.005/hr, not the $0.004 assumed), and it stops accruing while paused. See DEV_BACKLOG → housekeeping. The address itself is deliberately not recorded — it changes on every stop/start, and the value written here on 2026-07-31 was stale by 2026-08-03.

Also: check-in cadence 90 → 180 minutes (`config/personas/mike/scheduler.yaml`, gitignored — hand-copied to VM, scheduler restarted).

### Also done 2026-07-30 (client/app audit — ⚠ COST FINDING, and symptoms need re-testing)

Investigation into five reported app/PWA bugs. **No code changed** — one approved programme, parked. Full findings: [archive/plans/client_auth_tunnel_programme_2026-07-30.md](archive/plans/client_auth_tunnel_programme_2026-07-30.md) · Session archive: [archive/sessions/2026-07-30 — Client and App Audit, Cost Finding, Programme Parked.md](archive/sessions/2026-07-30%20—%20Client%20and%20App%20Audit,%20Cost%20Finding,%20Programme%20Parked.md)

**⚠ THE $30 BUDGET WAS NEVER VIABLE — this is arithmetic, not anomaly.** e2-medium 24/7 ≈ $24.50/mo + in-use external IPv4 ≈ $2.90 + disk ≈ $1 = **~$29/mo of infrastructure before a single AI token.** The cap wasn't protecting against runaway AI spend; it was tripping on the VM existing. It tripped twice in three days, disabling billing and taking the VM offline both times. Budget raised to $40 manually by the user on 2026-07-30; **service restoration was handled in a parallel chat.**

**⚠ THE REPORTED SYMPTOMS ARE PARTLY THE OUTAGE — re-test before fixing anything.** "Web app doesn't load", "failed to fetch", and much of "Tailscale keeps falling silent" are all consistent with a dead server. **Do not start Phase 1 of the parked programme until the system has been used against a live server and we know which symptoms actually survive.**

**Two symptoms were misdiagnosed and are worth knowing regardless:**
1. **"Messages stay at the top" is not an ordering bug.** DOM order is correct — `appendChild` only, no prepend anywhere, and the server already reverses to oldest-first. `#conversation` (`static/index.html:30-37`) is a flex column with no bottom alignment, so short content stacks at the top of a tall column. One-line CSS fix (use `margin-top: auto` on an inner wrapper, **not** `justify-content: flex-end`, which clips overflow in Chromium).
2. **"Tailscale falling silent" is largely the client.** There is no `case 'ping'`, no `visibilitychange`/`online`/`pageshow` listener anywhere in `static/index.html`. Android freezes the WebView on background; the socket dies half-open; `readyState` stays `OPEN` so sends vanish with no timeout. Restarting Tailscale forces a network-change event that finally kills the socket — which is why Tailscale *looks* guilty.

**Real defects found (documented, not fixed):**
- **Blank screen on 2nd+ launch:** auto-login (`index.html:911`) runs `enterApp` at script-parse time; `enterApp` hides the login screen **first**, then calls three functions with no `try/catch`. `new WebSocket()` throws synchronously on a bad URL → `ws` stays `null`, `onclose` never fires, **no reconnect path exists**. History arrives *only* via the WS frame, so no WS = permanently blank with no error shown.
- **`/transcribe` and `/tts` block the event loop** (`server.py:597-646`, `561-594`) — no `run_in_executor`, freezing the WS chunk relay, heartbeats and `/active` for the whole of ffmpeg + Whisper. The correct pattern is already used at `server.py:252/311/425`.
- **Whisper is untuned:** `base.en` at float32, `beam_size=5`, no VAD, `condition_on_previous_text` defaulting True, never warm-loaded — so the first call after every restart pays model construction *on the event loop*.
- **`deploy.sh`'s drain is decorative** — `/active` counts only SSE streams, and `/session/stream` has no client at all, so **every deploy kills in-flight WebSocket exchanges.**
- **No auth anywhere** (`allow_origins=["*"]`); Tailscale is the entire security model. `/monitor/file` and `/monitor/history` read arbitrary paths under `data/`. This is what makes the Cloudflare Tunnel a bigger job than the roadmap implies.
- `shownIds` eviction cliff at `index.html:567` (clears *after* adding, unlike the hardened L590); catch-up reuses `type:"history"` so a reconnect wipes the conversation and re-renders only the delta.
- `sw.js` has **no `fetch` handler** and caches nothing, and `/` is served `no-store` — there is no offline shell, so an unreachable server is a browser error page.

**Cost levers (recorded, not applied):** gate check-ins on user activity (largest — the pathological case *is* the current state: ~12 full pipelines/day talking to itself while the app was broken); stop the VM overnight via a GCE instance schedule (~$8–9/mo, native, no code); `companion_checkin` 90 → 180 min; hold off on a CUD until Whisper sizing settles. Enable BigQuery billing export for per-SKU daily attribution — **not retroactive**, so enabling early matters.

**Domain recommendation:** user has `apexgmat.com` on Cloudflare, but I'd advise a **separate personal domain** for the tunnel — one Cloudflare account means a shared blast radius between a business site and a host holding journals/clinical flags/finances, and `metatron.apexgmat.com` would be published permanently to public Certificate Transparency logs, associating a personal endpoint with a business entity. ~$10/yr. Nothing before Phase 4 depends on it.

### Also done 2026-07-29 (SessionStart hook removed after compliance-gap testing)

- **Hook confirmed firing correctly, but model non-compliant on trivial questions:** traced a live test through raw JSONL — `SessionStart:clear` ran `session_context_primer.py` successfully and correctly injected the "mandatory, no exceptions" Read instruction. On the next turn ("what is the capital of France?"), the model answered "Paris." with zero tool calls — no `Read` on SESSION.md or the roadmap at all. Not a hook-plumbing bug: the model's own relevance judgment silently overrode the procedural "no exceptions" instruction.
- **Reworded instruction drafted but not adopted** — shifting from a procedural mandate ("read these files first") to an epistemic one ("these files are truth for this session, even overriding obvious facts") was discussed as directionally stronger, then narrowed to scope authority to project-specific facts only (avoid coopting general common sense). User judged the tuning cycle wasn't worth it relative to the value delivered.
- **Decision: rolled back entirely.** Removed the `SessionStart` hook block from `.claude/settings.local.json` (the `Stop` hook / `show_phase_progress.py` untouched) and deleted `.claude/session_context_primer.py`. Both files are gitignored — no git history affected.
- **Replacement: `/metatron-code` slash command** (new) — `.claude/commands/metatron-code.md`. User-triggered (not automatic): reads SESSION.md, resolves + reads the current roadmap from SESSION.md's own link, and CODEBASE_INDEX.md if needed. Same content the hook used to inject, but explicit per-invocation instead of firing on every session start — avoids the compliance-gap failure mode since there's no relevance judgment to override on an unrelated turn.
- Session archive: [archive/sessions/2026-07-29 — SessionStart Hook Removal After Compliance Gap Found.md](archive/sessions/2026-07-29 — SessionStart Hook Removal After Compliance Gap Found.md)

### Also done 2026-07-29 (live multi-surface testing — 7 bugs found and fixed)

Continuation of the persona unification session, driven by real use across browser, Android app and terminal. Same session archive: [archive/sessions/2026-07-28 — Persona Unification Complete (Phases 0-8, Strict Mode Live).md](archive/sessions/2026-07-28%20—%20Persona%20Unification%20Complete%20(Phases%200-8,%20Strict%20Mode%20Live).md)

**⚠ IMPORTANT CORRECTION — the coordinator does NOT run 7 turns.** With trace instrumentation fixed, a specialist-heavy session records `coordinator turns=[1]`, `physical_health turns=[1..8]`, `synthesizer turns=[1]`. The multi-turn sequence is a **specialist** doing 8 internal tool-call turns; the interleaved `turn=2`×3 / `turn=3`×3 pattern in logs was three specialists running **concurrently** — parallel fan-out already works. This contradicts roadmap D2 item 5 ("the coordinator makes multiple sequential specialist calls... target ≤3 turns"), which the coordinator already meets. **Re-scope that item against measured data before starting it** — the real cost driver is per-specialist internal turns.

**Fixed this stretch:**
1. **Terminal was building a second history** — `orchestrator.py` ran the pipeline in-process, writing to whichever machine ran it, never touching the shared DB or broadcasting. New `core/remote_client.py` connects to the server WebSocket; remote is now the **default** for interactive coordinator sessions, `--local` opts out with a warning. WebSocket not SSE, because only the WS path calls `_save_exchange()` and `manager.broadcast()`.
2. **Orchestrator CLI was broken** (pre-existing since `c66ed03`) — `import core.trace` at line 28, `sys.path` fix at line 57. `--persona` now required.
3. **Proactive check-ins were invisible** — the scheduler ran in-process, so check-ins produced a trace and a push notification but no conversation record and no DB row. Coordinator jobs now route through the server via `send_one()`.
4. **Proactive check-ins faked a user message** — the prompt was stored/rendered as if the user typed it, so Synth appeared to answer itself. New `proactive` flag through table, reads, persistence, broadcast and log; all three client render paths skip the user bubble. Prompt deliberately stays in *model* history (strict user/assistant alternation; empty user turn risks provider rejection) — display and model context separated.
5. **Specialists absent from all traces** — trace context is thread-local and the fan-out propagated persona but not trace, so every `push_agent()` landed on an empty context. This is what made the coordinator look multi-turn.
6. **The Book didn't number live exchanges** — two feeds: `/monitor/conversations` (JSONL, has seq) vs `/monitor/stream` (traces, no seq). Server now attaches seq by matching user text; the monitor was also discarding it, so both halves were needed.
7. **VM ran `Etc/UTC` while user is Europe/London** — not cosmetic: `scheduler.yaml` times are wall clock, so `morning_brief 07:30` fired at 08:30 BST, `evening_close 20:00` at 21:00, quiet hours 22:00–07:00 were really 23:00–08:00. Set to `Europe/London`. **DST contingency added**: the `schedule` library computes `next_run` once at registration and this daemon runs for weeks, so the main loop now detects a UTC-offset change and re-registers — no manual step at the October/March transitions.

**Also:** check-in prompts rewritten to lead with a specific outstanding item from the context tracker (which already held `open_threads`/`follow_ups` — nothing told the Coordinator to use them) and to stop rather than manufacture a topic. Terminal client gained reconnect-with-backoff (a deploy restart killed a live session). Android APK rebuilt twice — the installed build was from Jun 21, missing five weeks of client fixes including the WS hang.

**Git history rewrite (user-approved):** `git add -A` swept 41 files of journals/clinical logs/conversations into a commit that reached GitHub. Rewritten via soft-reset (offending commit was `HEAD~1`, so `filter-repo`'s clone-and-swap was unnecessary risk against live gitignored data). Verified against a fresh clone: path in zero commits, GitHub refuses both orphaned SHAs, zero matching objects. Caveat recorded: proves unreachability by any client, not that GitHub gc'd its storage.

**Confirmed working:** sync across browser, app and terminal; strict mode; caching. **Still open:** browser appears to need a manual refresh to show foreign messages (client-side bug in `static/index.html`).

**Next per user:** simulate regular use, troubleshoot each exchange for missed routing / unsurfaced opportunities / token overspend / useless calls. Note only 3 of those 4 have instrumentation — **"unsurfaced opportunities" has no signal by definition**; the `·` feedback dot is the nearest hook. Capture a per-exchange turns/tokens baseline before history accumulates.

### Also done 2026-07-28 (PERSONA UNIFICATION — architecture change, strict mode live)

**One mechanism, no test/real distinction, every session real.** Started as CalDAV setup; became an architecture fix after finding the persona system was half-implemented.

**What was wrong:** 20 code sites each read `AI_TEST_PERSONA` independently and silently fell back to a shared global path when unset. Consequences, all verified: the user's history split across two trees (VM global tree held ~8x more journal content than `personas/mike/`); Pepys test data sat in the same directory as real clinical logs; three tools (`caldav`, `agent_config`, `wishes`) were persona-blind entirely; `load_profile()` fell back to root so **every synthetic persona was being told it was "Mike, London"**; the prompt header said `## Development Persona` on real sessions; and `persona` went unvalidated from the HTTP body into filesystem paths.

**Root cause of the split — a process boundary, not a date cutover:** `metatron-server.service` ran `--persona mike`; `metatron-scheduler.service` had **no `--persona` flag at all**, so every scheduled session wrote globally. Compounded by a thread race: `run_session` set then *popped* a process-global env var while the Diarist ran fire-and-forget on a daemon thread.

**Now:**
- **`core/persona.py`** — single fail-closed resolver. Explicit arg -> thread-local -> `METATRON_PERSONA` -> raise. Thread-local, not process-global (sessions run on a pooled executor thread; specialists fan out further). Names validated `^[a-z0-9][a-z0-9_]{0,39}$`.
- All 20 sites converted; 4 thread boundaries bound; `PersonaError` re-raised rather than swallowed in best-effort blocks.
- `profile.yaml` / `scheduler.yaml` / `caldav.yaml` now per-persona under `config/personas/{p}/` (gitignored). Templates in `config/templates/`.
- `scripts/new_persona.sh` + `scripts/check_personas.py` (read-only linter, exits 0).
- **Security:** `write_calendar_event` no longer accepts a model-supplied `calendar_url` — it overrode config and let the model pick the destination server for a tool shipping event text.
- **Constitution (Tier 0, user-approved):** `## Development Note` removed — it made discretion conditional on a development/production distinction the model cannot observe, and contradicted `filter_output()`. Proposal doc: `archive/plans/constitution_development_note_proposal_2026-07-28.md`.
- **Roadmap Section 0:** the carve-out permitting persona data on cloud models is **superseded** — nothing at runtime distinguishes synthetic from real any more. All persona data is sensitive-tier.
- **Data reset:** global trees moved aside to `data/_pre_reset_2026-07-28/` on both machines, VM with a full manifest. `metatron.db` (Android chat history), `push_subscriptions.json` and `data/baselines/` deliberately preserved.
- **STRICT MODE IS LIVE.** Exercised all 21 persona-dependent paths first; audit log stayed empty. Verified with a real session: writes land in `data/personas/mike/`, global tree gets nothing, no `PersonaError`.

**Commits:** `82e583a` (resolver + 20 sites), `92b51f7` (tools + settings + security), scheduler crash fix, `af32b5f` (provisioning + linter + rename), constitution, docs. Rollback tag: `pre-persona-unification` (`814e6c3`). VM backup: `~/metatron-backups/pre-persona-unification-2026-07-28-*.tar.gz` (verified restore).

**Two process lessons recorded:** (1) `deploy.sh` restarts services, so systemd unit edits need `daemon-reload` **before** the deploy — a near-miss briefly ran production fail-closed. (2) `py_compile` cannot catch a `NameError`; a stale `_SCHEDULER_CONFIG` reference crash-looped the scheduler after deploy. Grep for removed symbols, and actually run the daemon.

Session archive: [archive/sessions/2026-07-28 — Persona Unification Plan and Phase 0.md](archive/sessions/2026-07-28%20—%20Persona%20Unification%20Plan%20and%20Phase%200.md)

### Backlog found this session (pre-existing, not fixed)
1. **`companion_checkin` errors on every fire** (07:35, 09:05, 10:35, 12:05) — error logged ~90 min after firing, suggesting a timeout. A core proactive feature failing silently. **Highest priority.**
2. `Object of type AgentRecord is not JSON serializable` — trace serialization, every scheduler job.
3. `[vertex_cache] 404 cached content metadata` — stale cache ID reused after expiry, falling back to compat on every call.
4. `/session` (non-streaming) leaks the `[CONTEXT]{...}[/CONTEXT]` block into the response body and never writes the context tracker — the parser lives only in the streaming path. No user impact (app uses WebSocket/SSE).
5. `## Prime Directive` / `## Mission` appear once each now, but the underlying cause remains: `write_config()` stores the Goals Interviewer's text verbatim including its own heading. `_titled()` dedups at load time.

### Also done 2026-07-28 (SessionStart context hook + troubleshoot slash command)

- **Problem:** chats overstep because SESSION.md/roadmap/ownership context isn't loaded before basic queries or edits — the CLAUDE.md "Mandatory Pre-Edit Context Check" is an instruction the model has to remember, not a forced load (see 2026-07-27 revert incident below).
- **`.claude/session_context_primer.py`** (new) — `SessionStart` hook wired into `.claude/settings.local.json` (alongside the existing `Stop` hook, untouched). Fires on session start/resume/clear/compact/fork; injects full `SESSION.md` + the currently-active roadmap (resolved dynamically from SESSION.md's link, not hardcoded — won't go stale when the roadmap is next revised) + `CODEBASE_INDEX.md` (~1,560 lines / ~15–18K tokens). CLAUDE.md deliberately not duplicated — Claude Code auto-loads it already. Output uses the documented JSON `additionalContext` hook format (confirmed via `claude-code-guide` research); first line is a literal `Default Hook Fired` marker so firing is visually confirmable, and each file section echoes its resolved path.
- **`.claude/commands/metatron-troubleshoot.md`** (new) — callable slash command, `/metatron-troubleshoot <DATE> <SEQ> <ISSUE>`. Reconstructed from the single-exchange troubleshoot prompt referenced in `archive/sessions/2026-06-26 — Troubleshooting Prompts and Interchange ID Design.md` (original was only "in the chat transcript," never saved — user supplied the text this session). Pulls conversation record + server logs + pipeline trace for one exchange via one SSH round-trip. Confirmed working by user.
- **Not yet confirmed:** live in-session firing of the SessionStart hook — `SessionStart` doesn't fire on ordinary turns within an already-running session (only on the five sources above), so an in-session test came back empty as expected, not a bug. Next session (or a `/clear`) should confirm `Default Hook Fired` appears and no `Bash`/`grep` fallback is needed for a roadmap question.
- Session archive: [archive/sessions/2026-07-28 — SessionStart Context Hook and Troubleshoot Slash Command.md](archive/sessions/2026-07-28 — SessionStart Context Hook and Troubleshoot Slash Command.md)

### Also done 2026-07-28 (rehydrated 2026-06-26 pipeline audit session; write_config filter fix attempted and reverted)

- Context-recovery task: located and read both transcript copies of the 2026-06-26 "Context: this is the Metatron..." session, summarized findings, cross-checked against current state.
- **Correction on re-check:** of the 5 bugs from that original audit, 4 were confirmed resolved directly in code (ambient context, Research Agent normalization, uncached Coordinator prompt — accepted structural cost, graceful shutdown SIGKILL). The 5th — `write_config` output-filter false positive — was *not* actually fixed; the SEQ 031 session's two-tier filter only covered common-English-word terms (`logistics`, `finance`), not tool names like `write_config`, which stayed in `_ALWAYS_CONFIDENTIAL`.
- **Fix attempted, then reverted after security review.** First pass exempted any term already present in the user's own message from suppression. User asked for a review against this file and the roadmap before accepting it — that surfaced a real regression: the roadmap's B1 red-team plan tests a "Direct tool inquiry" category (e.g. "What tools do you have?") expecting a canned response; the fix let a message like "What does `write_config` do?" disable the filter's own backstop for exactly that probe, since the term was "already said." Reverted in full — `filter_output()` and all three call sites back to original always-suppress behavior; net diff is docstring-only.
- **Known gap, correctly recorded (not a regression):** the `write_config` / `_ALWAYS_CONFIDENTIAL` false positive from Exchange 027 remains open. Fixing it without weakening the backstop belongs to the already-planned **Track B / B2 "Output filter upgrade"** (regex+semantic matching) — see roadmap.
- Session archives: [archive/sessions/2026-07-28 — Rehydrate Metatron Pipeline Audit Session.md](archive/sessions/2026-07-28 — Rehydrate Metatron Pipeline Audit Session.md) (rehydration + fix attempt), [archive/sessions/2026-07-28 — Chat Rehydration, write_config Filter Fix Attempt and Revert.md](archive/sessions/2026-07-28 — Chat Rehydration, write_config Filter Fix Attempt and Revert.md) (full session close, including the revert)

### Also done 2026-07-28 (lost chat recovery + ask_claude MCP resume)
- No code/config changes. User couldn't find an open `ask_claude` chat ("write product description...") that hadn't rehydrated after a restart — `list_conversations` showed the MCP tool's own archive empty, so it was gone from that tool's state. Located the content via file search in `archive/transcripts/` instead (2026-06-19 "Bill Hopkins Proposal" session — capital-raise product description for a corporate/enterprise variant of Metatron). Manually resumed by re-feeding the prior draft + six flagged research gaps into a new `ask_claude` prompt; got a full multi-model pass back (competitive differentiation, agency trade-off framing, beachhead segment, revenue model, AI/human accountability, regulatory surface — see session archive for the findings).
- Ran `python3 tools/archive_chats.py` twice — cleared a backlog of 12 unarchived sessions going back to 2026-07-14, then captured this session's own transcript incrementally.
- Session archive: [archive/sessions/2026-07-28 — Lost Chat Recovery and ask_claude MCP Resume.md](archive/sessions/2026-07-28 — Lost Chat Recovery and ask_claude MCP Resume.md)

### Also done 2026-07-27 (SEQ 041 routing miss diagnosis and fixes)

- **Root cause:** Coordinator dispatched zero specialists for "I'm not sure. Do you have some suggestions?" (Bulgarian vocabulary follow-up) — treated as conversational follow-up, not a domain query. Synthesizer received no Learning output and responded from general knowledge.
- **Synthesizer catch also failed:** existing sanity-check rule did not trigger `run_subagent` despite absent Learning output for a Learning domain query.
- **Diarist evaluated:** fire-and-forget (no user latency), 3-turn pattern is Vertex parallel tool call bug (not worth fixing — background agent, no user impact). OVER_8K warnings at turn=2/3 are from Diarist running in parallel; Synthesizer's turn=1 warning is logged at API return time, not start time.
- **Four fixes deployed (commit `814e6c3`):**
  1. `config/agents/coordinator.md` — routing rule: advice/suggestion requests route to relevant domain specialist regardless of COMPLEXITY
  2. `config/agents/synthesizer.md` — domain query catch-up covering all 8 domains (generalizes existing Logistics-only catch)
  3. `core/orchestrator.py` — Diarist added to bare-mode set; strips goals.yaml (~500–1000 tokens/turn saved)
  4. `config/modules/routing_cloud.yaml` — `write_log` and `write_wisdom` added to Diarist allowed_tools
- Session archive: [archive/sessions/2026-07-27 — SEQ 041 Pipeline Routing Diagnosis and Routing Miss Fixes.md](archive/sessions/2026-07-27 — SEQ 041 Pipeline Routing Diagnosis and Routing Miss Fixes.md)

### Also done 2026-07-27 (Vertex cache padding fix, pause/resume tooling, billing incident)
- **Vertex cache padding fixed:** `_pad_for_vertex_cache()` added to `core/orchestrator.py` — the 2026-06-24 token-reduction work had shrunk Coordinator/Synthesizer prompts under Vertex's 4096-token cache-creation floor, silently failing cache creation on every call. Verified live: cache now creates successfully and reads confirmed (`cache_read=12281` on a real session).
- **VM pause/resume tooling added:** `scripts/metatron-pause.sh`, `scripts/metatron-resume.sh` — stop/start `metatron-vm` for cost control during dev downtime.
- **Billing incident + fix:** the $20 budget cap had tripped and fully unlinked the billing account days earlier. Budget raised to $30. Found and fixed a re-fire loop in `stop-billing` (Cloud Function) caused by GCP's budget-notification propagation lag re-disabling billing on every relink attempt — added a manual-override marker mechanism (`gs://metatron-billing-state/override.json`, `scripts/metatron-billing-override.sh`), wired into `metatron-resume.sh` to trigger only when it finds billing actually disabled.
- **Known issue documented:** Tailscale DNS relay came up unhealthy after VM stop/start, blocking all outbound API calls until `tailscale set --accept-dns=false`. Root cause not identified.
- **Monitoring note added** below (June 24 token-reduction entry) — watch cache padding on any future prompt-shrinking pass to Coordinator/Synthesizer.
- Session archive: `archive/sessions/2026-07-27 — GCP Billing Investigation, Cache Padding Fix, and Pause-Resume Tooling.md`

### Also done 2026-06-22 (The Book SSE reconnect)
- `_sse_loop` now auto-reconnects with exponential backoff (2s→30s) on any connection failure. Column 1 updates in real time without re-selecting the persona.
- Session archive: `archive/sessions/2026-06-22 — The Book SSE Reconnect.md`

### Also done 2026-06-26 (SSE streaming newline fix)

- **Root cause:** LLM stream chunks containing literal `\n` were embedded directly in SSE `data:` lines. Client's `split('\n')` parser dropped all text after the newline, causing truncated responses and mid-word splicing.
- **Fix:** Server escapes `\r`/`\n` in text chunks before SSE emission (`core/server.py`); client unescapes `\\n` when accumulating (`static/index.html`). Control tokens unaffected.
- Committed `ba84c6d`, deployed to VM. Hard reload required on client.

Session archive: [archive/sessions/2026-06-26 — SSE Streaming Newline Fix.md](archive/sessions/2026-06-26 — SSE Streaming Newline Fix.md)

### Also done 2026-06-26 (seq in conversation logging)

- **`core/server.py`** — `_log_conversation` now writes `"seq": "003"` (1-indexed, zero-padded, per-day) to each JSONL entry. Thread-safe: `_CONV_LOCK` wraps the read-count-then-write atomically.
- **`tools/metatron_monitor.py`** — Column 1 shows `#003 14:23` prefix when seq present; falls back to full timestamp for old entries.
- No changes to `/monitor/conversations` — seq passes through from JSONL automatically.
- Committed `9fcd802`, deployed to VM.

Session archive: [archive/sessions/2026-06-26 — Sequential Exchange ID (seq) in Conversation Logging.md](archive/sessions/2026-06-26 — Sequential Exchange ID (seq) in Conversation Logging.md)

### Also done 2026-06-26 (Gemini routing fix)

- **Root cause 1:** `core/router.py` silently defaulted unknown agents to `provider="anthropic"`. Fixed: raises `RuntimeError` + logs to `data/logs/routing_fallbacks.json`.
- **Root cause 2:** Browser sends `provider=""` (empty string from Auto dropdown); `if provider is None` check didn't catch it. Fixed: both sites in orchestrator changed to `if not provider`.
- **Error tracking added:** `log_model_error()` in `router.py` writes API failures to `data/logs/model_errors.json` (agent, provider, model, error). Wired into `_openai_compat_loop`, `run_session_gemini_grounded`, `run_session_gemini_cached`, and the unrecognised-provider branch.
- **Other defaults cleaned:** `run_interactive()` + server CLI `--provider` both changed from `"anthropic"` to `"gemini"`.
- Deployed `config/profile.yaml` and `tools/ambient.py` (were missing from VM, causing warning).
- Confirmed working via SSH test and browser.

Session archive: [archive/sessions/2026-06-26 — Gemini Routing Fix and Deploy Audit.md](archive/sessions/2026-06-26 — Gemini Routing Fix and Deploy Audit.md)

### Also done 2026-06-26 (Synthesizer conversation history)

- **Rolling 5-turn history** (10 entries) added to the Coordinator → Synthesizer pipeline. Synth no longer cold-starts each turn — prior user/assistant exchanges are prepended to its messages.
- **`core/orchestrator.py`:** `_anthropic_stream` — added `history` param. `run_pipeline_session` + `run_pipeline_session_stream` — both accept `history`, pass a `list(history[-10:])` snapshot copy to Synth, update history in-place after each turn, trim to 10. `run_session` — threads history through to pipeline (previously dropped on the floor).
- **`core/server.py`:** `_session_history: dict[str, list[dict]]` — per-persona in-memory history. Both `/session` and `/session/stream` look up the right list and pass it to the pipeline each request.
- **Side fix:** streaming pipeline was not applying Synth's `allowed_tools` whitelist — Synth was receiving all ~20 tool schemas instead of its 8. Now matches `_run_single_agent` behavior. This also addressed the "context file not registering" observation.
- Deployed to VM. Confirmed working.

Session archive: [archive/sessions/2026-06-26 — Synthesizer Conversation History.md](archive/sessions/2026-06-26 — Synthesizer Conversation History.md)

### Also done 2026-06-27 (Kokoro TTS migration + Safari AudioContext fix)

- **Kokoro `af_heart` now running on VM.** Venv was Mac-only and never migrated. Installed `espeak-ng` via apt + `kokoro soundfile` into main `.venv` (reuses existing torch). `KOKORO_PYTHON` path updated in `core/server.py` and `core/voice_pipeline.py`. Subprocess timeout raised 30s → 120s.
- **Safari AudioContext fix** (`static/index.html`): replaced `new Audio().play()` with `AudioContext.decodeAudioData()` + `BufferSourceNode` — Safari blocks the former even after user gesture; the latter is always allowed after `ctx.resume()`. Shared `audioCtxShared` context created on first tap.
- **`aiosqlite` added to `requirements.txt`** — was missing, caused server crash on startup after deploy.
- **Login Enter key** — `#login-password` now has a `keydown` handler; Enter submits the login form.
- **VM gap audit complete** — all other expected packages/models confirmed present on VM. Only Kokoro was missing.
- Session archive: [archive/sessions/2026-06-27 — Kokoro TTS Migration and Safari AudioContext Fix.md](archive/sessions/2026-06-27 — Kokoro TTS Migration and Safari AudioContext Fix.md)

### Also done 2026-06-26 (pipeline audit + Research Agent normalization fix)

- **Pipeline audit** across 2 hours of live traffic (15:28–16:47): 5 bugs identified. See session archive for full latency profile and failure pattern catalog.
- **Research Agent normalization fix (two-part):**
  - `core/orchestrator.py` — 9 single-word abbreviation entries added to `_AGENT_NAME_MAP` (`"research"` → `"research_agent"`, `"mental"` → `"mental_wellbeing"`, etc.). Covers Flash-Lite's tendency to shorten multi-word agent names on cold starts.
  - `config/agents/coordinator.md` — explicit "Valid agent values" line added before the format template, listing all 12 agent strings verbatim.
- **Root cause of exchange 027:** Coordinator output `"Research"` (not `"Research Agent"`) → normalized to `"research"` → `research.md` not found → Synthesizer streamed "minor snag" then called `run_subagent` as recovery → weather data returned but too late to retract already-streamed text.
- **Single-exchange troubleshoot prompt** written — two inputs (DATE, SEQ), one SSH command, pulls conversation record + server logs + pipeline trace in one round-trip.
- **Pending deploy:** both normalization fixes are committed locally but not yet pushed to VM.
- **Bugs identified but not fixed this session:** (1) `tools.ambient` missing on VM, (2) output filter false positive on `write_config`.
- **(3) graceful shutdown 90s SIGKILL cycle — fixed 2026-06-26:** `timeout_graceful_shutdown=150` added to `uvicorn.run()`; `_active_streams` counter + `GET /active` endpoint added to `core/server.py`; `deploy.sh` restructured to drain active SSE streams (up to 180s) before restarting metatron-server. Full Fix 3 (drain gate + client reconnect + `/result/{date}/{seq}` endpoint) scoped in `archive/plans/future_phases.md`. Session archive: [archive/sessions/2026-06-26 — SEQ 032 Troubleshoot and Graceful Shutdown Fixes.md](archive/sessions/2026-06-26 — SEQ 032 Troubleshoot and Graceful Shutdown Fixes.md)

Session archive: [archive/sessions/2026-06-26 — Pipeline Audit and Research Agent Fix.md](archive/sessions/2026-06-26 — Pipeline Audit and Research Agent Fix.md)

### Also done 2026-06-26 (user profile + ambient world context)

- **`config/profile.yaml`** (new) — stable biographical profile injected into Synthesizer and Coordinator. Filled in: name Mike, London, UK, Europe/London. Age/occupation/household left to fill. Includes `ambient.markets: true` flag.
- **`tools/ambient.py`** (new) — 3-hour scheduler job fetches weather (wttr.in/London), headlines (BBC + CNN interleaved, 8 total), and 7 market indices (S&P 500, FTSE, DAX, Nikkei, Hang Seng, Gold, WTI Oil) via Yahoo Finance v8 chart endpoint. Writes `data/ambient_context.json`. `load_ambient_context()` always injects live date/time from system clock; weather/news/markets from last refresh.
- **`core/orchestrator.py`** — `load_profile()` added; injected into `load_config()` (Synthesizer) and Coordinator system prompt. Ambient context prepended to `load_recent_context()` so both agents always see it.
- **`core/scheduler.py`** — `function:` job type added; calls Python callables directly without an LLM session.
- **`config/modules/scheduler.yaml`** — `ambient_refresh` job: every 180 minutes, calls `tools.ambient.refresh_ambient_context`.

Session archive: [archive/sessions/2026-06-26 — User Profile and Ambient World Context.md](archive/sessions/2026-06-26 — User Profile and Ambient World Context.md)

### Also done 2026-06-26 (The Book: SSE backfill fix, load menu, ordering)

Root-cause fix for two related issues: (1) Load menu filter (24h / max 10) appeared broken because `/monitor/stream` replayed all historical traces on connection, backfilling old conversations to the top of Column 1 past the filtered 10. Fixed: `/monitor/stream` accepts `since` param; skips old traces on initial scan only. Monitor records `_sse_since = now()` at `load_data()` start and passes it to the SSE endpoint. (2) Uncommitted changes from prior session meant VM was running old server code with no `since`/`limit` support — deploy was a no-op. Committed and deployed. (3) Max entries Input → Select dropdown (10/20/50/All). Client-side descending sort added as defensive measure.

Session archive: [archive/sessions/2026-06-26 — The Book Load Menu, Ordering, and SSE Backfill Fix.md](archive/sessions/2026-06-26 — The Book Load Menu, Ordering, and SSE Backfill Fix.md)

### Also done 2026-06-26 (Book: Synth token counts + conversation history)

- **Synth tokens showing 0:** `_openai_compat_stream` only captured usage from the trailing choices-empty chunk (OpenAI pattern). Vertex AI embeds usage in the final content chunk (`finish_reason="stop"`, choices non-empty). Added second capture path guarded by `_usage_recorded` flag. Confirmed working.
- **Conversation history not in Column 3:** `recent_history` was fed to the model but not stored in `context_sections`. Now serialized as `USER:/ASSISTANT:` text and added as `"conversation_history"` key. The Book's Column 3 shows it in a new "Conversation History (fed to Synth)" collapsible. Appears from the second exchange onward (first message after restart has no prior history — expected).
- Deployed `e1a12d2`.

Session archive: [archive/sessions/2026-06-26 — Book Synth Token Counts and Conversation History.md](archive/sessions/2026-06-26 — Book Synth Token Counts and Conversation History.md)

### Also done 2026-06-26 (SEQ 031 troubleshoot + context tracker refactor)

Root-caused SEQ 031: "I can't help with that right now" response despite coherent tracker entry. Three findings:

1. **Output filter false positive** on `logistics` in "daily logistics" — common English word matched banned agent name. Fixed: two-tier filter. `_ALWAYS_CONFIDENTIAL` (code identifiers, always flagged) vs. `_CONTEXT_SENSITIVE` (`logistics`, `finance`, `relationships`, `coordinator`, `synthesizer`, `orchestrator`, `diarist`) — only flagged when architecture vocabulary appears in the same sentence.
2. **Preference not durable** — `write_context_tracker` is session-level state; `config/personas/mike.md` was not updated. Fixed: `write_persona` tool added (`tools/persona.py`), registered in orchestrator + both routing configs. `mike.md` updated with goals interview complete + Interaction Preferences section (no validation/commendation, direct follow-up questions only). File pushed directly to VM via `gcloud compute scp` (gitignored).
3. **Context tracker double-turn overhead** — `write_context_tracker` tool call forced 2–3 Synthesizer turns per exchange (~$0.066/exchange at Pro pricing; ~$20/month at 300 exchanges).

**Fix 3 — [CONTEXT] inline block:** Synth now appends `[CONTEXT]{json}[/CONTEXT]` after its visible response instead of calling the tool. Streaming parser in `run_pipeline_session_stream()` intercepts the block before it reaches the client, parses JSON, calls `write_context_tracker()` as a direct Python function call. Synth is now 1 turn for simple exchanges (2 for `run_subagent` exchanges). Held item fidelity preserved — Synth authors them in the same generation pass. Recency bias guard added to instruction. Tested live: clean visible response, `[CONTEXT]` not leaked, tracker written with correct held item. Commits `4984f48`, `5df05aa`.

Session archive: [archive/sessions/2026-06-26 — SEQ 031 Troubleshoot and Context Tracker Refactor.md](archive/sessions/2026-06-26 — SEQ 031 Troubleshoot and Context Tracker Refactor.md)

### Also done 2026-06-26 (single exchange troubleshoot — SEQ 026 / Logistics routing)

Root-caused why "Delayed until Monday at 5:30." (SEQ 026, 16:28:23) did not trigger a scheduling action. Coordinator dispatched zero specialists; Synthesizer absorbed it conversationally. Three fixes deployed:

1. **`config/agents/coordinator.md`** — Logistics entry broadened: added explicit "also call when user defers or postpones anything to a named time" rule; added deferral signal words (delayed, postponed, rescheduled, moved to, pushed to, bumped, put off, defer, reschedule, changed to, updated to) and temporal commitment triggers (tomorrow, next week, this weekend, next month, end of month/week, next year, by [day name], on [day name], [day] at [time]).
2. **`config/agents/synthesizer.md`** — `write_config` scope clarified (recurring proactive sessions only; one-off deferrals → Logistics). Catch-up rule added: if user message contains a temporal commitment signal and no Logistics output in context package, call `run_subagent("logistics")` before responding, log `ROUTING_MISS: Logistics`, call `write_quality_event`.
3. **`tools/subagent.py`** — Diarist removed from Synthesizer's `run_subagent` schema (Coordinator always dispatches it fire-and-forget; Synth has no use case for calling it directly). Confirmed: Coordinator dispatches Diarist via `_dispatch_from_coordinator` text parsing, not tool calls — schema change has no effect on Coordinator.

**Clarifications established:**
- No "Scheduler agent" exists. Scheduling = Logistics (`write_calendar_event`) for one-off events/deferrals; `write_config` for recurring Metatron session entries (habits, standing check-ins). These are distinct.
- Pattern Miner and Goals Interviewer should not be in Synth's callable agent list — PM runs on schedule, Goals runs at first-instance onboarding only.
- Coordinator model upgrade is not the right fix for routing misses; missing rules are the cause.
- Synth token tracking (in=0 out=0) was broken before ~17:05 on 2026-06-26; confirmed working from 17:05 onwards. No code change needed.

**Open:** (1) Test Coordinator fix with a deferral message in app, verify Logistics in trace. (2) Verify `write_calendar_event` actually connects to a real calendar, not just flat file logging.

Commits: `e477c76`, `5f21800`, `5a7c6ff`. Session archive: [archive/sessions/2026-06-26 — Single Exchange Troubleshoot SEQ 026 Logistics Routing.md](archive/sessions/2026-06-26 — Single Exchange Troubleshoot SEQ 026 Logistics Routing.md)

### Also done 2026-06-26 (The Book: call timing, tokens, load menu, server fixes)

Seven fixes across `core/trace.py`, `core/orchestrator.py`, `core/server.py`, `tools/metatron_monitor.py`:

1. **Tool call timing:** `duration_ms` changed to float (`round(..., 1)`); `ToolCallRecord` now stores 1-decimal ms precision. 0ms sub-millisecond ops now show e.g. `0.3ms`.
2. **Token counts per call:** `ToolCallRecord` extended with `input_tokens`/`output_tokens`. For `run_subagent`, tokens pulled from subagent `AgentRecord` at dispatch time and shown on collapsible title in Column 3.
3. **`run_subagent` not recorded (Gemini native parallel path):** `_run_gemini_native_loop` parallel branch now propagates thread-local trace context (same pattern as Anthropic path). Previously all Coordinator subagent calls were silently dropped from traces.
4. **Server blocking event loop:** `session_stream` iterated a sync generator inline in `async def`, blocking uvicorn for 10–30s — no monitor requests could be served during a pipeline run. Fixed: `_produce()` runs in `run_in_executor`; chunks queued via `asyncio.Queue` + `run_coroutine_threadsafe`. `/session` non-streaming also fixed with `run_in_executor`. Zero latency impact.
5. **Personas not loading on launch:** `load_personas()` now retries 4× with exponential backoff. R key now also retries persona load when no persona is selected.
6. **Freezing on persona switch:** SSE worker cancel moved to top of `load_data()` (was deferred until after HTTP requests — caused old-persona SSE to write to new-persona's list mid-load).
7. **Load menu + most-recent-first:** New `#load-bar` in The Book with Range presets (1h/6h/24h/7d/30d/All) and Max count input. Default: 24h, 10 messages. Server `/monitor/conversations` and `/monitor/traces` now accept `since` + `limit` and return newest-first. Column 1 now shows most recent messages at top; SSE live messages prepend to top.

Session archive: [archive/sessions/2026-06-26 — The Book Call Timing, Token Counts, Load Menu, and Server Fixes.md](archive/sessions/2026-06-26 — The Book Call Timing, Token Counts, Load Menu, and Server Fixes.md)

---

### Also done 2026-06-26 (pipeline debugging + latency work)

Phase 1 — Three root-cause bugs fixed. First live response confirmed via browser (see session archive for details).

Phase 2 — Latency reduction. Warm-cache second-message latency: ~40s → **~20s**. Streaming text now appears word-by-word in UI.

Key changes:
1. **Agent name normalization** — `_normalize_agent()` in `_dispatch_from_coordinator`. All casing/spacing variants ("Physical Health", "Logistics", etc.) now resolve to correct filenames. MW, PH, and other specialists were silently dropping on every session.
2. **Coordinator: Pro → Flash-Lite** — single-pass routing directive, no tools. Saves ~3–5s.
3. **Vertex cache fix** — tools now baked into `CreateCachedContentConfig`. Eliminates guaranteed native-loop-fail + compat-fallback double round-trip on every tool-bearing agent (Synthesizer, specialists). `cache_read=12000+` visible in logs.
4. **trace.py committed** — `ToolCallRecord.input_tokens`/`output_tokens` had been applied locally but never committed; old VM version crashed native loop.
5. **Streaming client** (`static/index.html`) — coordinator uses `/session/stream` (SSE). Text streams into bubble word-by-word (`▍` cursor). TTS fires on `[DONE]`. TODO (future): phrase-by-phrase TTS with pauses.
6. **Streaming thought_signature fix** (`_openai_compat_stream`) — when Synthesizer emits text + `write_context_tracker` in one streaming turn, stream deltas lack Vertex's `thought_signature`. Fix: replay that turn blocking using pre-turn message snapshot; apply `model_copy()` workaround. Already-yielded text is correct; replay used only for signed message construction.

**Next:** specialist token reduction (plan Steps 3–5) — specialists still running 5–8 tool-call turns; this is the biggest remaining latency lever. Then B1/Check10/Check12 for A7 sign-off.

Session archive: [archive/sessions/2026-06-26 — Pipeline Debugging and First Response.md](archive/sessions/2026-06-26 — Pipeline Debugging and First Response.md)

### Also done 2026-06-26 (troubleshooting prompts + interchange ID design)

Meta/planning block — no code changes. Three deliverables:

1. **TTS phrase-by-phrase note confirmed recorded** — `// TODO future: phrase-by-phrase TTS` in `static/index.html` (`sendStreaming`), session archive, and SESSION.md.
2. **Latency troubleshooting prompt written** — general-purpose prompt for diagnosing a specific exchange: pull VM logs for a time window, break down latency by component, evaluate Coordinator routing and RESOLVED_INTENT, compare what happened vs. what should have happened. Text in chat transcript; reuse by pasting into a new chat with a target time window.
3. **Interchange ID design recommendation** — daily zero-padded sequential counter (`001`, `002`…) as `seq` field in `data/conversations/YYYY-MM-DD.jsonl`. Display as `#003  14:23` in Column 1. Implementation prompt written (two steps: `_log_conversation` in `core/server.py` + Column 1 display in `tools/metatron_monitor.py`). Not yet implemented.

Session archive: [archive/sessions/2026-06-26 — Troubleshooting Prompts and Interchange ID Design.md](archive/sessions/2026-06-26 — Troubleshooting Prompts and Interchange ID Design.md)

### Also done 2026-06-24 (token reduction — Steps 1–5)

**Token reduction implementation complete (Steps 1–5 of 6).** Projected ~3× reduction (Steps 1–5); ~5× with Step 6.

- **Step 1:** `git tag v0.5-pre-refactor` — snapshot before any changes.
- **Step 2:** Per-agent tool schema whitelists. `allowed_tools` added to `routing_cloud.yaml` and `routing.yaml` for all agents; `core/router.py` — `ModelConfig.allowed_tools` field + `get_allowed_tools()` function; `core/orchestrator.py` — schema filter in `_run_single_agent()`. Only advertised schemas go to the LLM; Python functions stay registered. (~15,000t saved)
- **Step 3:** Strip constitution/prime_directive from specialist system prompts. Three-branch context loading in `_run_single_agent()`: bare (research_agent), head layer (full config + recent context), specialists (goals.yaml only). `_HEAD_LAYER_AGENTS = {"coordinator", "synthesizer"}`. `load_goals()` function added. (~5,000t saved)
- **Step 4:** Specialists no longer call `load_recent_context()` independently. Context arrives via Coordinator directive. (~3,000t saved)
- **Step 5:** Quick/deep behavioral sections added to all 8 specialist agent files (mental_wellbeing, physical_health, work_vocation, relationships, finance, learning_growth, recreation_hobbies, logistics). Existing language preserved exactly; Quick mode is a gate only. MW clinical detection active in all modes without exception.
- **Step 6 (deferred):** Coordinator restructure — single-pass directive assembly replaces 3-turn session. Do after Steps 1–5 stable. (~15,000t saved from Coordinator alone)

Session archive: [archive/sessions/2026-06-24 — Token Reduction Architecture and Implementation.md](archive/sessions/2026-06-24 — Token Reduction Architecture and Implementation.md)

**Monitor: Vertex cache padding (2026-07-27).** Steps 2–5 above shrank Coordinator/Synthesizer system prompts enough that at least one (Physical Health-adjacent context, 4051t) fell under Vertex's 4096-token cache-creation floor — every cache attempt silently failed and ran uncached until fixed in `_pad_for_vertex_cache()` (`core/orchestrator.py`). Any future token-reduction pass on `coordinator`/`synthesizer` (the only two agents on the cached path — `_HEAD_LAYER_AGENTS`/`_ROUTING_LAYER_AGENTS`) should re-check real prompt sizes stay comfortably clear of that floor, or confirm the padding logic is still absorbing the gap. Currently routed to Gemini only — the dormant Anthropic `cache_control` path (1024t floor, fails silently rather than erroring) doesn't need the same watch unless Anthropic routing comes back.

### Also done 2026-06-22 (token economics analysis)
- **Pipeline token cost traced end-to-end:** ~95,000 input tokens for a 70-token user message (~13× overhead). Coordinator (3 turns): ~22,000t. 5 sync specialists (2 turns each): ~49,000t. Synthesizer (2 turns): ~14,790t.
- **Three waste sources identified:**
  1. Tool schemas (~2,000t) paid 9× across all invocations — each agent/specialist receives all 30 schemas regardless of which 2–3 it uses. Synthesizer pays for schemas it never calls (streaming path confirmed no-tool in code comments).
  2. Shared config (constitution + prime_directive + mission + goals, ~1,400t) paid 9× — no cross-agent caching.
  3. Recent context (~600t) loaded independently 8× — each specialist calls `load_recent_context()` even though Coordinator already has it and constructs their directive from it.
- **Three fixes without architectural change** would cut to ~55,000t: (1) route tool schemas per agent, (2) pass recent context in the directive rather than reloading in specialists, (3) strip constitution from specialist system prompts (mirrors existing research_agent pattern).
- **Architectural question raised:** should all specialist calls live in Synthesizer, with Coordinator being a cheap single-turn router only? Coordinator currently costs ~22,000t; as lightweight classifier it would cost ~1,000t. Synthesizer already does secondary chains (ReAct, up to 3 rounds per its agent file). No decision made — deferred.
- Session archive: `archive/sessions/2026-06-22 — Token Economics and Pipeline Architecture Analysis.md`

### Also done 2026-06-22 (The Book — monitoring tool iteration)
- **The Book** (`tools/metatron_monitor.py`) — substantial iteration on the monitoring TUI.
- **Bug fixes:** persona bleed in Column 1 (conversations endpoint now always filters by persona), subagent name showing as `run_subagent(?)` (arg key is `agent_name`), SSE disconnect on ID collision (list items no longer use IDs; SSE loop is append-only), snapshot crash (`s` key priority binding), chat "no response" (dropped `streaming_json`, now uses `--output-format text` via temp file + shell redirect).
- **Column 1:** datestamps added; each message block is now a `Collapsible` — collapsed shows truncated preview, expanded shows full user + Metatron text.
- **Column 3:** turns flattened to Static dividers with tool calls as top-level Collapsibles; `run_subagent` now resolves to the actual subagent record (provider/model/tokens/output files) instead of raw args.
- **Diary/file history viewer:** clicking a file link opens all entries in that directory, sorted by date, with the current entry marked `← current` in green. New `GET /monitor/history` endpoint on server.
- **Output file tracking:** `core/trace.py` now scans tool call args and results for `data/...` paths; stores as `output_files` on `AgentRecord`; included in JSONL serialization and shown as clickable buttons in Column 3.
- **Snapshot (`s` key):** writes `data/book_snapshot.md` to Mac project dir with current Book state — bridge to Claude Code in VSCode.
- **Chat panel (`c` key):** bottom panel with Input, Send, Clear, token counter. Sends messages to `claude -p --output-format text` via temp file; builds recursive context (full `Human:/Assistant:` history prepended each turn). Chat panel still unconfirmed working — under investigation.
- **New server endpoints:** `GET /monitor/history`, `GET /monitor/file`.
- Session archive: `archive/sessions/2026-06-22 — The Book Iteration and Chat Panel.md`

### Also done 2026-06-21 (Android end-to-end testing)
- **All 10 Android tests pass.** App fully functional on VM.
- Mike persona synced to VM; Vertex key deployed; Whisper installed.
- Server migrated to HTTPS via Tailscale cert (`metatron-vm.tail0acc5d.ts.net:8001`).
- Fixed: PortAudio crash (lazy sounddevice import), provider defaulting to ollama (now auto-route), send button layout, mic auto-prompt (MainActivity.java), audio autoplay on Android (AudioContext unlock).
- **Cloudflare Tunnel** added to roadmap as pre-alpha requirement (removes Tailscale from phone).
- **D1 open:** Run Goals Interview on VM — `BASELINE_INCOMPLETE` on every session until done. Run via CLI: `python core/orchestrator.py --agent goals_interviewer --provider gemini`
- Session archive: `archive/sessions/2026-06-21 — Android End-to-End Testing.md`

### Also done 2026-06-21 (CLAUDE.md deployment infrastructure)
- **CLAUDE.md updated:** "Per-System Configuration" replaced with comprehensive "Deployment Infrastructure" section covering topology diagram, GCP VM, Vertex AI, billing protection, Tailscale, systemd unit files (verbatim), GitHub/deploy pipeline, Python env, all environment variables, routing/deployment mode, Android app build steps, local dev mode, and a 10-step recreate-from-scratch checklist.
- **Model version note** in CLAUDE.md updated (2026-05-19 → 2026-06-21; Flash-Lite ID corrected to non-preview).
- Session archive: `archive/sessions/2026-06-21 — CLAUDE.md Deployment Infrastructure Section.md`

### Also done 2026-06-20 (VM provisioning, GitHub, deploy pipeline)
- **GCP VM provisioned:** `metatron-vm`, `e2-medium`, Debian 12, `us-central1-a`. Python 3.11, ffmpeg, all deps installed.
- **Tailscale on VM:** joined tailnet. **VM Tailscale IP: `100.64.226.49`** — phone connects here (not the Mac). Health check confirmed via Tailscale.
- **Vertex credentials on VM:** service account `metatron-vertex@metatron-ai-499810.iam.gserviceaccount.com` with `roles/aiplatform.user`. Key at `~/multi-model-mcp/vertex-key.json`, `GOOGLE_APPLICATION_CREDENTIALS` in `.env`.
- **systemd services:** `metatron-server.service` (port 8001, `--persona mike`) + `metatron-scheduler.service` — both enabled and `active (running)`.
- **GitHub repo:** `github.com/MikeApex/metatron` (private). SSH key `~/.ssh/github_mikeapex` on Mac, deploy key `metatron-vm` on VM.
- **Deploy pipeline:** `./deploy.sh` — pushes to GitHub, VM pulls, restarts services. Post-commit hook reminds to deploy after every commit.
- **Always-on Mac backup:** not yet implemented — deferred until needed (VM is primary). When needed: `pmset` for sleep prevention + launchd plist (see notes below).
- **Login/profile screen:** added to `static/index.html`. Shows on first launch; auto-logins on return via `localStorage`. Persona dropdown (mike + all test personas grouped). Password field (placeholder, not enforced). Persona chip in header — tap to switch.
- **APK rebuilt and sideloaded:** new VM Tailscale IP (`100.64.226.49`), login screen, new mem icon. Java 21 installed via Homebrew. Adaptive icon XMLs removed — Android now uses PNG directly (fixes home screen icon caching issue). APK served via `python3 -m http.server 8888` on Mac Tailscale IP.
- **GitHub:** `github.com/MikeApex/metatron` (private). SSH key `~/.ssh/github_mikeapex`. Deploy key `metatron-vm` on VM. `./deploy.sh` pushes to GitHub + restarts VM services. Post-commit hook reminds to deploy.
- **requirements.txt** generated from venv (95 packages) and committed.

### Also done 2026-06-19 (Vertex AI setup session)
- **GCP project created:** `metatron-ai-499810`, billing linked, Vertex AI API enabled, ADC configured.
- **Billing hard-cap at $20:** Pub/Sub topic `billing-cap` + Cloud Function `stop-billing` (Python 3.11, Gen2) auto-disables billing when budget fires. IAM grants in place.
- **Vertex AI migration:** `run_session_gemini_grounded()` now uses Vertex native SDK (`genai.Client(vertexai=True)`). Vertex requires `location=global` for Gemini 3.x models. `.env` updated with `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION=global`, `DEPLOYMENT_MODE=cloud`.
- **`routing_cloud.yaml` created:** all 14 agents on `gemini-3.1-pro-preview` via Vertex. `DEPLOYMENT_MODE` toggle in `router.py` (evaluated at call time, not import time — fixes `.env` load order bug).
- **Flash model ID updated:** `gemini-3.1-flash-lite-preview` → `gemini-3.1-flash-lite` (old preview discontinues July 9).
- **sys.path fix:** orchestrator now inserts project root so `tools/` resolves correctly when running `python core/orchestrator.py`.
- **Smoke test:** Research Agent via Vertex returned valid grounded response. Full pipeline: 60–90s latency (multiple sequential Gemini 3.1 Pro calls via AI Studio — see open item below).
- **Repo cleanup:** .gitignore expanded; all previously untracked files committed (108 files).
- **Vertex native SDK migration complete (2026-06-19):** `run_session_gemini()` now uses `_run_gemini_native_loop()` via `genai.Client(vertexai=True)` — same client setup as `run_session_gemini_grounded()`. All Gemini agents (coordinator, synthesizer, all specialists) are now on the native SDK. `_openai_compat_loop()` retained for OpenAI/Ollama paths only. One fix required: Gemini API rejects empty-string enum values; handled in `_clean_schema_for_gemini()` at conversion time. Tested: single-shot full pipeline + two-turn interactive history threading. Session archive: `2026-06-19 — Native SDK Migration (Gemini).md`.
- **Next sessions ready:** efficiency prompt + Android app prompt both written and in this archive.

### Also done 2026-06-17 (Metatron Android app session)
- **Metatron Android app built and working** — Capacitor wrapper, sideloaded APK, voice end-to-end confirmed.
- **Private STT pipeline** — Web Speech API (Google cloud) replaced with server-side Whisper via `/transcribe` endpoint. Audio archived to `data/audio/`. ffmpeg installed.
- **Server running HTTP on port 8001** (no TLS) — Tailscale WireGuard provides transport encryption. Certs backed up to `certs_backup/`.
- **Capacitor config:** bundled assets (secure context for mic), `SERVER` constant for API calls, `allowMixedContent: true`, 10-minute fetch timeout, dropdowns hidden, mike persona active.
- **Tailscale cleanup:** old stale device removed, host renamed to `mikes-macbook-air` in admin.tailscale.com. Direct IP `100.70.67.45` used in app (DNS not resolving in WebView).
- **Mem icon:** Phoenician/early Hebrew mem glyph, parchment+brown, generated by `tools/gen_icon.py`.
- **Next (on hold):** (1) Tailscale same-network vs. remote behaviour, (2) Mac always-on + Ollama warm, (3) login/profile selection in app.
- **⚠ HOLD (2026-06-17):** All Metatron / infrastructure work paused pending decision on whether to migrate hosting to Google Vertex VM. Decision resolves the architecture (local Mac vs. cloud VM as the LLM host) before further build work proceeds.

### Also done 2026-06-16 (continuation of A4/A6 session)
- **Synthesizer CRITICAL block** added — mandatory surface rules for `CLINICAL_CONCERN` and `MUST_SURFACE` flags; cannot be held or deferred; front-loaded after Confidentiality section (same pattern as MW fix). Covers mania, suicidal ideation, depression, missed critical medication.
- **CONSULT_NEEDED routing logic** added to Track E in roadmap — named deferred item with B2 dependency documented. Previously only mentioned verbally.
- **Prompt structure front-loading audit complete** — all 9 specialist agents assessed; only Synthesizer required immediate fix; Physical Health noted for D2 pass.

---

### Decisions resolved 2026-06-10
- **Binding privacy ruling:** sensitive data never reaches a cloud model — no fallbacks, no deferrals. Drove new A4 and re-tiering of routing.yaml (to be implemented at A4; current routing.yaml cloud fallbacks are stale).
- Check 7 vs. D2 conflict: resolved — assumptions documented now + safety hard-fails run on the local model at A4; full validation at Phase 6 / D2.
- E3 removed from Phase 6 close gate (circular dependency); Stage 2 builds single-user, Stage 3 automation gated on multi-user cohort.
- o3 Pattern Miner production test retired — Pattern Miner is local-only.
- Time Director carries no test obligations; testing plan amended.

---

## Useful context to pull as needed

| Question | Where to look |
|---|---|
| What does each agent do? | `config/agents/` |
| What tools exist and what they do | `tools/` — all registered in `core/orchestrator.py → register_tools()` |
| What's the security posture? | `archive/security/threat_model_2026-06-04.md`, `archive/security/security_backlog_2026-06-04.md` |
| What are the test criteria for this phase? | `tests/phase5_testing_plan.md` |
| What's parked for later phases? | `archive/plans/future_phases.md` |
| Agent enhancement backlogs | Roadmap Section 4, or `## Enhancement backlog` at the bottom of each agent file |
| Session history | `archive/sessions/` — sorted by date |
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

**Vertex note:** AI Studio uses `models/gemini-*` prefix; Vertex drops the prefix. The orchestrator strips it automatically when `GOOGLE_CLOUD_PROJECT` is set. Flash-Lite preview ID discontinues July 9 — already updated to non-preview ID.

**2026-07-27 session note:** Reviewed a Google email about GCE Guest Environment Packages moving to regional rollout (Sept 3, 2026) — no action needed, single-VM/single-region deployment isn't affected. Reviewed Anthropic's Claude Opus 5 announcement and updated model aliases (see table above). Future refactor/security-audit work flagged as a candidate for Claude Fable 5 (`ask_claude` alias `fable`) or Opus 5 — decide when that work starts.

**2026-07-27 session note (2nd session, later same day):** Design discussion on whether archive/wisdom tooling covers open-ended user data (expenses, watchlists, ideas) escalated into an implementation attempt (`update_archive_item` in `tools/diarist.py`, new `tools/finance_summary.py`, wiring in `core/orchestrator.py`, whitelist fixes in both `routing*.yaml`, a doc line in `finance.md`) made without checking `SESSION.md`/the roadmap/file-ownership rules first. This violated the frozen-specialist-file rule and the `core/orchestrator.py` ownership/A8-refactor plan already on record — **all of it was reverted** (verified clean via `git diff`). New standing rule added to `CLAUDE.md`: **"Mandatory Pre-Edit Context Check"** — no edit without first reading SESSION.md + active roadmap + ownership rules. Also saved as memory `feedback_pre_edit_context_check.md`. The one change that did land: `archive/plans/phase5_to_future_roadmap_2026-06-10.md` Section 4 now notes both gaps (Finance transaction aggregation; archive item lifecycle/update-in-place) as unscoped "Now tier" placeholders for future work — see that doc for details, and `archive/sessions/2026-07-27 — Data Management Gaps Discussion and Pre-Edit Context Rule.md` for the full session log.

**2026-07-27 session note (3rd session — chat rehydration + persona goals audit):** Located the one never-archived "Metatron — Single Exchange Troubleshoot" chat (of five same-titled transcripts) — session `f37f081a-693d-4b82-bdcb-b7d6d163b392`, SEQ 026 duplicate, left open mid-thread on CalDAV setup (which service Mike uses; timezone needs `America/New_York` → `Europe/London` in `config/modules/caldav.yaml`, currently `enabled: false` with empty credentials). Discussed blank vs. duplicate Google account for a London base — recommended blank, import contacts only, skip calendar/email history (works against the "hypothesis not verdict" design principle; Goals Interview is the intended onboarding mechanism, not account data mining). **New gap surfaced:** `config/goals.yaml` (Tier 3 structured store) is still empty despite `config/personas/mike.md` flagging "Goals interview completed 2026-06-26" — the interview's actual output landed in `data/baselines/aspirational_baseline.json` (good/hard week, peak/floor days narrative; also has an untagged `"persona": ""` bug) and the ephemeral `data/personas/mike/context.json` tracker instead of durable `goals.yaml`. No edits made — analysis only. Deferred to user: whether to draft `goals.yaml` entries from existing baseline/context data; account creation is a manual user step. Session archive: [archive/sessions/2026-07-27 — SEQ 026 Chat Rehydration and Persona Goals Gap Audit.md](archive/sessions/2026-07-27 — SEQ 026 Chat Rehydration and Persona Goals Gap Audit.md)

**2026-07-27 session note (4th session — coordinator-slim chat rehydration):** Found and rehydrated the 2026-06-19 "slim coordinator.md" proposal chat on request. Confirmed it was never implemented: `config/modules/coordinator_routing.yaml` / `data/config/coordinator_routing.json` don't exist, no "Parallel dispatch" block is in `coordinator.md`, and the file has grown to 2,279 words (from 2,160 at proposal time) with new content the old proposal doesn't account for (deferral/rescheduling signal words, agent-name normalization). Still open per the roadmap (D2 latency item 5). No edits made — user confirmed they only wanted the context back, not implementation. If resumed later, needs a fresh audit against current file content, not the stale 2026-06-19 draft, and should re-check the Vertex 4096-token cache-padding floor (Section 4 monitor) before landing any reduction. Session archive: [archive/sessions/2026-07-27 — Coordinator Slim Chat Rehydration and Archive Runs.md](archive/sessions/2026-07-27 — Coordinator Slim Chat Rehydration and Archive Runs.md)

**2026-07-27 session note (4th session — cross-device WS sync bug fix + deploy):** User was trying to relocate a "Synch" chat; traced it to [archive/sessions/2026-06-26 — Synthesizer Conversation History.md](archive/sessions/2026-06-26%20—%20Synthesizer%20Conversation%20History.md), which undersold its own follow-through — same-night commit `4302ef8` actually shipped full SQLite-backed, real-time cross-device WS sync (`core/server.py` `ConnectionManager` + `exchanges` table), never verified against two real devices and never fully documented (`dc8f031` has no session log entry). Found and fixed a real bug in `static/index.html` `sendViaWebSocket()`: `shownIds.clear()` ran after adding the new exchange ID instead of before, so once the client-side set exceeded 100 entries the in-flight exchange's own ID got wiped, causing the response bubble to hang forever with no error. Fixed (commit `eea3faf`), deployed via `./deploy.sh` (GCP billing had auto-disabled on the $20 cap mid-session, user re-enabled, deploy succeeded on retry). **Confirmed 2026-07-28/29:** user tested on real devices — "Synching seems to be occurring." **>100-exchange edge case force-tested 2026-07-29:** 300-iteration logic simulation (pre-fix fails at #101/#202, fixed order 0 failures) plus a live end-to-end WS test against the real production server on persona `cal_newport` (dev persona, not mike) — one real Vertex call, exchange correctly recognized as own through the fix, persisted to SQLite under the right persona, mike's data untouched (11 rows, unchanged). Fix fully confirmed at both logic and live-system level — see [archive/sessions/2026-07-27 — Cross-Device WS Sync Bug Fix and Deploy.md](archive/sessions/2026-07-27%20—%20Cross-Device%20WS%20Sync%20Bug%20Fix%20and%20Deploy.md) for remaining open items (duplicate "4th session" label, undocumented `dc8f031`).

---

## Key design decisions (don't revisit without cause)

- Config files are the product. Code is infrastructure. Behavior changes = config edits.
- All personal context is sensitive-tier. Cloud LLMs receive only fully decontextualized requests.
- **Sensitive data never reaches shared cloud infrastructure — fail-closed, no fallbacks (binding ruling 2026-06-10).** Head layer and all personal-data specialists run local. Ollama down = hard error, never a cloud call. **Amendment 2026-06-18:** a dedicated VM with verified Zero Data Retention (e.g., Vertex AI ZDR) is acceptable during testing — contractual sequestration is a distinct threat model from shared cloud. North star is still architectural security on private hardware (local/A100/H100); VM path is explicitly temporary.
- Discretion: users never see which agent was called, which model ran, or how data was routed.
- The tool surfaces hypotheses, not verdicts. Output invites correction; doesn't foreclose it.
- Archive-on-merge: data is never deleted; moved to archive with a merged_into pointer.
- `age` encryption deferred to Phase 6. Until then, file permissions (600) are the protection.
