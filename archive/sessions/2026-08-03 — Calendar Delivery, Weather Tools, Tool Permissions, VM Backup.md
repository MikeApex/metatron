# 2026-08-03 — Calendar Delivery, Weather Tools, Warn-Mode Tool Permissions, VM Backup

Continuation of the 2026-08-02 SEQ 021 session (see [SEQ 021 Logistics Turn Burn](2026-08-02%20—%20SEQ%20021%20Logistics%20Turn%20Burn,%20Clock%20Injection,%20Tool%20Error%20Hints.md)). That session diagnosed why a recurring reminder request burned six turns and saved nothing. This one built the missing capability.

**Deployed:** Phases 0, 1, 3 (commits `cfcd212`, `6865058`).
**Written, not committed:** Phase 4 (scheduler write access) — one step from complete.

---

## What was built

### Phase 0 — identity, backup, cleanup

- **All `mike` integrations moved to `diamond.mike.mt@gmail.com`** (purpose-built account). `CLAUDE.md`, `profile.yaml` (`account_email`), and `.env` `VAPID_CLAIMS_SUB` on both Mac and VM. Historical archives left as written.
- **`scripts/metatron-backup.sh` (new)** — nothing on the VM was captured by git. `data/personas/` is gitignored and `config/personas/mike/` is hand-copied, so neither travels through the repo; the 2026-07-31 VPC rebuild preserved 12MB of real data only because the disk was deliberately detached first. Pulls VM state to the Mac, **verifies the archive before pruning anything**, hardlinks a stable `latest.tgz`.
  - Reuses the existing chain rather than duplicating it: `daily-backup.sh` now runs the pull first (best-effort — a paused VM must not stop a local backup) and includes only `latest.tgz`, so the daily archive carries live server state without compounding every previous pull into every future backup. Restic (external drives) picks up the whole `backups/` tree.
  - **First run caught real drift**: `profile.yaml` had been edited on the Mac only. Exactly what it exists to find.
- **`.gitignore`**: `.env.*` was unignored — the `.env.bak` files created during the identity switch would have been committable with every API key in them. Confirmed never in history. Also added `data/diagnostics/` and `backups/`.
- Stale pre-unification `data/traces/` (ended 2026-07-27) archived to the Mac, removed from the VM.

### Phase 1 — the calendar actually delivers

- **`write_calendar_event` gained `recurrence` (RRULE), `alarm_minutes_before` (VALARM) and `all_day`.** This was the real blocker: the builder emitted a bare one-off `VEVENT` with no alert, so enabling CalDAV alone would have produced a *silent single event* — the same false-success shape as the original bug.
  - All-day `DTEND` is exclusive per RFC 5545, so a same-date range is advanced by a day rather than rejected.
  - RRULE and TRIGGER deliberately bypass `_esc()`: escaping the semicolons would break the rule.
  - Schema teaches the RRULE format with a worked example — the model has to emit valid syntax.
- **CalDAV live on Mac and VM.** Two corrections needed:
  - The URL supplied was the **read-only iCal feed** (`.../basic.ics`); the calendar ID was extracted from it.
  - `apidata.googleusercontent.com/caldav/v2` **requires OAuth 2.0 and 401s on app passwords** — verified against four URL variants. The legacy `www.google.com/calendar/dav/` endpoint accepts basic auth (207). Corrected in the persona config, `config/templates/caldav.yaml`, and inline comments. The app password itself is valid — proven by a successful IMAP login, which also de-risks Phase 5.
- **`get_weather` and `get_environmental_snapshot` built** in `tools/ambient.py`, registered, tested live.
  - `get_weather` adds **recent rainfall** from Open-Meteo with a computed `days_since_rain` — the decisions that turn on rain are backward-looking, and wttr.in only forecasts.
  - A bare `null` for `days_since_rain` is indistinguishable from a failed lookup, so the result also carries `rained_in_window` and a plain-language `summary`. Caught by testing, not by review.
  - `get_environmental_snapshot` adds UV and AQI. UV is free from the same wttr.in call; **AQI is not in wttr.in at all** and comes from Open-Meteo (free, no key), **failing soft** so losing it never takes down a health session.
  - Coordinates reused from wttr.in's `nearest_area` — no separate geocoding call.
- **Supersedes roadmap decision 16** ("environmental monitoring weather-only, ships with E1") by explicit user decision.

### Phase 3 — tool permissions in warn mode

`dispatch_tool` now checks the calling agent's grant. Two things were previously true and both invisible:

1. The whitelist filtered the schemas an agent was **shown** but dispatch looked up handlers **unfiltered** — so an agent that knew a tool's name from its instruction file could call anything, and did.
2. Because the call simply succeeded, nothing recorded that an agent wanted a capability it lacked.

**(2) is the more valuable.** The agent files are a specification of intended capability written *ahead* of the tools, so an attempted call is design signal. Enforcing silently would destroy that signal; stripping the references would destroy it just as thoroughly.

- Ships in **warn mode** — records, does not block. Flips to enforce once the log is reviewed, before integrations open the injection surface B2 gates E1 behind.
- Emits a **`TOOL_DENIED` quality event**, deduplicated per (agent, tool) at source, which `sync_dev_backlog.py` now pulls into `DEV_BACKLOG.md` as *"agent wanted a tool it lacks."*
- The permission set is derived from the schemas each runner was already handed, so the check and the advertisement **cannot drift apart**. Threaded through all 12 call sites across 6 runners.

---

## Corrections made during the session

Recorded because each one changed a decision:

1. **My removal analysis was wrong.** A scan matched tool names without reading the surrounding sentence. All eight `run_subagent` mentions read *"do not call `run_subagent` directly"* — they are the **guardrail**, not a false claim. Applying the proposed table would have deleted the instruction preventing the behaviour. **Net removals applied: zero.**
2. **The proposed fix direction was backwards.** The 2026-06-24 token work established the narrow `allowed_tools` lists as deliberate and load-bearing (~95,000t → ~30,000t, *"highest-leverage single change"*), with unfiltered handlers a conscious reversibility choice. Widening the lists to match the files would have reversed the highest-leverage optimisation in the project.
3. **The backlog token argument does not survive measurement.** ~130 tokens across 9 agents (~14 per call). Not worth moving for cost — worth mirroring for **discoverability**, which was the real problem.
4. **Files were stale in the opposite direction too.** `logistics.md` and `research_agent.md` listed `read_calendar`, `write_calendar_event` and `get_weather` as "Future — Deliverable 6" on the day all three shipped; `research_agent.md` still called for `web_search` to be built although grounding already provides it.
5. **`get_weather` was missed by the first phantom scan** — the backticks contained `get_weather(location)` and the regex required the whole tick-span to match.

---

## Standing practice adopted

Recorded in [capability_gap_gameplan_2026-08-03.md](../plans/capability_gap_gameplan_2026-08-03.md):

1. **The denial audit runs continuously.** Grant on demonstrated need, never blanket. A denial means grant it, build it, or drop the instruction.
2. **`DEV_BACKLOG.md` is the single intake** — user requests, tool denials, and items found while working. Reviewed at session start.
3. **Every development is backchecked against the plan** for cohesiveness. Denial findings will keep pulling later-phase features forward; amend the plan rather than diverging quietly.

All nine agent `## Enhancement backlog` sections **mirrored** (not moved) into `DEV_BACKLOG.md`. Strike in both places when built.

---

## Open — carried forward

**Phase 4 is one step from done.** Written and compiling, not committed:
- `tools/schedule.py` — `write_schedule` / `list_schedules` / `delete_schedule`; caps of 6 recurring agent jobs, 6h minimum interval, 10 concurrent user-facing; provenance (`created_by`, `created_at`, `reason`) on every entry; one-off support.
- `core/scheduler.py` — merges agent jobs at registration (user's `scheduler.yaml` wins on name collision), **30s mtime reload** so a job set at 09:00 for 10:00 actually arms, one-off firing that **deletes before running** so a 20–70s session cannot double-fire on the next 30s tick.
- Registered in `core/orchestrator.py`. **Remaining:** grant the three tools to Synthesizer and Logistics in both routing configs. A first attempt silently no-opped — the parallel session added `read_profile`/`write_profile` to those same lines mid-edit, so the matched string no longer existed. Rewritten line-based.

**The tier-editability inversion (found, not fixed).** Asked whether the architecture reflects "mission/prime directive editable but rarely; goals rewritten continuously." It does not — it is inverted both ways:
- `write_config` (→ `mission.md`, `prime_directive.md`) is held by the **Synthesizer**, which runs on *every exchange*. Least-changed files, most-invoked agent, no confirmation step.
- `write_goals` is held by **`goals_interviewer` alone**, which only runs as a formal interview. In ordinary conversation **nobody can update goals** — telling the tool a goal is achieved has no path to being recorded.
- `write_goals` merges only at top level: *"A key present in content replaces the existing value entirely."* Adding one daily goal means resending the whole `daily` list, and **any omitted goal is silently deleted** — the wrong shape for an ongoing add/complete cycle.

**Also open:**
- Location sharing — phone app permission plus calendar-derived inference as fallback. Agreed that GPS is a categorically stronger identifier than a city name and should be sensitive-tier, local-only, probably coarsened.
- Phase 5 — server auth (currently none, `allow_origins=["*"]`), `<untrusted_content>` injection defense (documented, unbuilt), `read_email`; `send_email` deliberately deferred.
- `write_config` exposure warn mode does not close: a specialist rewriting Tier 1 `prime_directive.md` would succeed and merely be logged. Not a regression — equally possible before — but the one place "log, don't block" leaves something real open.
- Archive script derives transcript titles from the first message; this session produced `2026-08-02 — local-command-caveatCaveat The messages below were genera.md`. Renaming does not stick (dedup keys on `raw/{uuid}.jsonl`), so the fix is in the title logic.

---

## Process notes

- **Parallel-session file collisions, twice in one day.** `core/orchestrator.py`, `routing.yaml` and `routing_cloud.yaml` are all being edited from both sides. No damage either time — the parallel session committed my Phase 0–1 work into `6601479` and named it — but the second collision silently no-opped an edit, which is the more dangerous failure mode.
- A live credential was pasted into chat. Written only to the gitignored `caldav.yaml`; deliberately kept out of every archive file, since `archive/sessions/` **is** committed to GitHub. Worth rotating.
- `.claude/commands/` is now tracked, closing the backup gap raised against the troubleshoot command.
