# 2026-08-08 — Pollen Tool, Travel Trigger, Scheduler Defaults

Four pre-verified items. Three shipped, one blocked by tooling. A fifth piece of work
(scheduler defaults) came out of a question Mike asked mid-session and turned out to be the
most consequential thing in it.

**Commits:** `8d798a8`, `be1d79e` — plus items 2–4's code, which was swept into another
window's `7c70cd9` before it could be committed here. VM-side config edits carry no commit
(gitignored by design).

---

## 1. `/archive` collision guard — NOT DONE

Adding a check-and-stop-if-dirty step to `.claude/commands/archive.md`, per `[DB-0805-05]`.

**Blocked: the file cannot be edited while `/archive` is a loaded skill in the session.**
Four attempts, all rejected.

Diagnosed by probe rather than guesswork:

| Edit | Target | A skill at the time? | Result |
|---|---|---|---|
| 1 | `scratchpad/edit_probe_plain.md` | no | ✅ |
| 2 | `.claude/commands/zz_edit_probe.md` | no — created seconds earlier | ✅ |
| 3 | same file, after it registered | **yes** | ❌ |

Ruled out first: no `PreToolUse` hooks at any level, no `deny` rules, file mode 644, no
`uchg` flag. Being open in VS Code doesn't lock a file.

- **I got this wrong twice before diagnosing it.** First assumed a wording/structure
  objection and asked Mike to pick a shape — he picked the one already tried. Then concluded
  the approval prompt was being mis-dismissed. Both wrong; the block is mechanical.
- Filed as `[DB-0808-13]` with the complete agreed spec (new numbered step 4, renumber 4/5/6
  → 5/6/7, update the "Steps 4 and 5" warning). Needs a session that hasn't loaded `/archive`.
- `[DB-0805-05]` stays open.

## 2. Coordinator turn-reduction — rescoped

- Static plan line 519 assumed 6–7 Coordinator turns. **Measured: 1 turn** (2026-07-29,
  re-measured 2026-08-02). Real cost is per-specialist internal turns, `logistics` at 8.
- Added a dated `SUPERSEDED 2026-08-08` note beneath the item, original text untouched —
  matching the convention already at line 38 of that file. Did **not** edit the dated plan
  in place.
- Rewrote the live entry as `[DB-0808-09]`: leads with a measurement sweep across five
  specialists, sets **no target number** deliberately.
- Instruction-slimming half of the item is unaffected — token size, not turn count.

## 3. Google Pollen API — built and live

- [tools/pollen.py](../../tools/pollen.py) → `get_pollen_forecast(location, days)`, 1–5 day
  grass/tree/weed on the 0–5 Universal Pollen Index. Registered; granted to `research_agent`
  in both routing files.
- **The GPS blocker never applied.** `[DB-0807-02]` had Pollen blocked alongside Places on the
  missing location signal. Pollen needs a lat/lon, which the wttr.in geocode already provides
  from a city name. The two items were filed together and inherited each other's blocker.
- Kept distinct from the Open-Meteo air-quality call — different exposure, different time
  shape. Reasoning is in the module docstring.
- **Key created later in the session:** `pollen.googleapis.com` enabled, key `pollen-forecast`
  restricted to that service at creation, loaded into VM `.env` over stdin (never echoed).
  First live call returned real London data — weed Moderate/in season.
- **Cost: 5,000 free calls/month, then $10/1,000** (SKU `6CDF-1930-8F86`). Checked against
  Google's live pricing list; two other pricing pages didn't carry per-SKU figures.

## 4. Proactive travel trigger — built

[tools/travel_watch.py](../../tools/travel_watch.py) + `daily_travel_check` function job.

- **Two-signal detection.** A flight-number regex alone matches "Q4 2026" / "Room B12";
  `get_flight_status` runs on 600 units/month at 1 req/s. A number is believed only when the
  event also carries travel context (airport, terminal, "flight").
- **Silent on a clean result.** On-time flight + Good Service = no notification. Each finding
  reported once, keyed on event *and* status, so a worsening re-alerts but a standing delay
  doesn't nag.
- **`fire_function` gained a notification path** — `{"notify": True, …}` dispatches;
  string-returning jobs unchanged. Lets the check cost zero tokens on a quiet day.
- Tested: 11/11 detection cases, notify/suppress/report-once/re-alert, and backwards
  compatibility across all three existing function jobs.
- Live dry-run on mike's real calendar: "no travel found in the next 24h" — correct.

## 5. Scheduler defaults — every persona, from code

Triggered by Mike's question *"shouldn't the dedup be active for every user?"*

- **Found:** `daily_calendar_dedup_audit` shipped 2026-08-05 and had **never run for mike** —
  live in repo and template, inert in production for three days, nothing reporting it.
- **Cause:** `scripts/new_persona.sh` copies the template **once, at persona creation**. No
  propagation, no drift report.
- **Fix:** the three silent maintenance jobs (`ambient_refresh`, `daily_rule_audit`,
  `daily_calendar_dedup_audit`) register from `_DEFAULT_JOBS` in `core/scheduler.py` for every
  persona. Persona config still wins outright, including `enabled: false`. Merge is per-key,
  not deep.
- **Rejected: drift-check script alone** — still needs a human to notice and apply per
  persona, the exact step that failed. Kept as a secondary check for preference jobs
  (`check_personas.py`).
- **Line:** scheduler owns mechanism, never content. A job with a prompt or notification is a
  preference and stays per-persona — which is why `daily_travel_check` stayed in mike's file.
- Removed the three from the template **and** mike's live file — leaving copies would pin him
  to stale values and re-create the bug.
- First dedup run: **7 real duplicate pairs** found on mike's calendar.

---

## Mistakes

1. **Fired live agent sessions by accident.** A check called `job_func()` on all nine
   registered jobs having stubbed only `fire_function`; `companion_checkin`, `evening_close`
   and `weekly_pattern_miner` ran for real against `sarah_chen` until a timeout. ~$0.10–0.50,
   no tracked files changed. Redone with both firing paths stubbed.
2. **Called a health check "failed" when it was a 401** — `/health` is behind the B2 shared
   secret and my curl carried no token. Server was fine.

## Concurrency — `[DB-0805-05]` live, three times

Several windows in this repo all session:
1. `7c70cd9` (another window) swept up this session's whole code diff — items 2–4 sit under a
   commit message describing unrelated work. Nothing lost; every file verified in `HEAD`.
2. `[DB-0808-06]` claimed by another window between read and write → renumbered to `09`.
3. `DEV_BACKLOG.md` committed by another window between my `git add` and `git commit`, making
   that commit a no-op.

All three are the failure the blocked guard exists to prevent — on the file the guard was
going into, which itself had 41 lines of another window's uncommitted changes at the time.

## Deferred

- `[DB-0808-11]` — `fire_function` runs no gate stack (`days`, `respect_quiet_hours`, activity
  gate live only in `fire_session`). Worked around by pinning to 06:45; proper fix is
  extracting the gate stack so both call it.
- `[DB-0808-09]` — the specialist turn-measurement sweep itself.
- `[DB-0808-13]` — the `/archive` guard.
- `[DB-0807-02]` — Google Places, still genuinely blocked on a location signal.
