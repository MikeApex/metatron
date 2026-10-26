# Day planner — Synth runs the user's day from a plan that code keeps current

*Plan, 2026-10-24. Author: Opus 5.5 (Claude Code). Review: Fable 5.1 via `/adversarial-review`
(Mike: "Make the plan, review, and once resolved build as much as you can before red tier is
required. Keep to as few red tier sessions as possible."). Build: Opus 5.5 by hand — Stage A
(Amber/Green) after the review resolves; Stage B is **one** Red session with Mike present.*

**INTERNAL.** Names the persona and live data shapes.

---

## 1. The need

Mike, 2026-10-24: *"Metatron's primary mission via Synth is telling the user what to do at any
given moment. This requires a dynamic process to update an ideal calendar based upon existing
appointments, task deadlines, user preferences for when rest, work, or personal time is best
scheduled throughout the day, and logistical mindfulnesses for travel, food, bathroom breaks and
such."* Window: through end of day, with tomorrow in view in the evening. A hybrid code + agent
process restructures it behind the scenes; a cheap check runs before any full reshuffle, because
"many times the user will simply be on schedule or inactive"; Synth reads the result on every turn
rather than asking for it, and asks for an update only in extraordinary circumstances. It serves
the user's long-term priorities and fulfilment; the constitution need not be invoked.

**What exists today (surveyed 2026-10-24, HEAD `3a9bd02`):**

1. **No plan exists anywhere.** Synth re-derives "what now" on every turn; the morning brief's
   "Direct the day … propose a sequence" (`config/modules/synthesizer_scheduled_sessions.md:33`)
   lives only in that one reply. The Time Director was retired into Synth on 2026-05-28.
2. **Synth cannot see the calendar.** No calendar block in its context, no calendar grant
   (`routing_cloud.yaml:81`); events arrive only when Logistics is dispatched.
   `logistics.md:58` says "Synthesizer owns all time-blocking decisions" — synthesizer.md never
   mentions time-blocking.
3. **Inputs that exist:** the task ledger (`tools/obligations.py`) with durations since `e5f3dad`
   ("the scheduling build-out reads it"); every calendar the account exposes (`_query_events(...,
   calendars="all")`, `tools/caldav.py:608`); Google Routes travel time (`tools/routing.py:53`);
   weather; the last zone the phone reported (`tools/location.current_zone`); minutes since the
   user's last message (`core/scheduler.py:144`).
4. **Inputs that do not:** task priority, deadline stakes, goal links; any structured day shape
   (wake, bed, work hours, meals, rest); a "last seen" time for location (only zone *arrival* is
   stored); wearables (deferred by Mike).
5. **The cheap-gate pattern exists**: the quiet check-in fingerprints context in code
   (`tools/context_tracker.py:784-922`) — a precedent, not a component to reuse (it fingerprints
   conversational state and spends the re-ask budget).

---

## 2. Mike's decisions — binding (three rounds, 2026-10-24)

| # | Mike | What it fixes in this plan |
|---|---|---|
| — | "This process should work with the Task Ledger so that there's no additional copy." | The plan stores **placements only** — ledger occurrence ids and calendar uids, never task state (§ 4.3). |
| — | Priority "SHOULD exist via goals and subagents … in one place with the task ledger" | Priority and stakes are **ledger fields** (§ 4.1). |
| Q1 | (c) — show the plan in the app **while building/testing**, move to (a) Synth-only when done. "This is for Synth, not for user." | Today-panel plan view behind a server flag (§ 9). |
| Q2 | (c) — the morning brief proposes the day and invites pushback; later replans are silent. | Conduct module (§ 6.2). |
| Q3 | Plan-driven nudges, **early after production**. "The existing check ins are a placeholder. If it's an empty day, a few check ins should happen, after a given lag since last interaction." | § 7; fixed check-in yields to the plan (§ 7.3). |
| Q4/F7 | Design rules (meals, breaks, buffers, wind-down) are agent-layer; the user's hours are per-persona. "These questions should be part of the first interview." Inference proposes changes, never applies them. | § 4.2, § 8. |
| Q5 | Explicit priority **as a baseline** reflecting longer-term goals; deadline pressure as the dynamic part; "some deadlines are vital, others can be missed in preference of life quality." | § 5.2, the life-quality rule § 5.4. |
| Q6/F5 | Reserve time for goals with no task, informed by specialists **once**, stored in data, re-consulted only when the goal changes; weekly cadence. "Specialists will soon be replaced by narrower agents." | Goal time is ledger habit tasks; never names a specialist (§ 6.6). |
| Q7/F1 | Mike's app sends location with messages. New users: location **opt-out through the interview**. Mike is aware this reverses the 2026-08-28 default. | § 8.2. |
| Q8 | "No assumptions. … the nudges should check completion if it's not explicitly stated or inferrable." | § 5.9. |
| Q9 | Two modes: repair (code) and reshuffle (model). | § 5.6. |
| Q10 | "Repair in the same reply; let user know if an imminent reshuffle is coming — at least while we're testing." | § 6.3. |
| Q11 | "Code does as much as possible." Model fitness to be checked. "This should not make Synth meaningfully heavier aside from the directives surrounding its existence." | § 5, § 6.1. |
| Q12 | Now, Mark 1. | — |
| Q13 | Day boundary default midnight; "adjustable on command or Metatron observation of daily rhythms." | § 8.3. |
| R2 | "Synth should probably get the whole day, including completed/missed items. Nudges are Synth's decision, but should be noted in the plan. Similarly checks are suggested in the plan, Synth does them. Synth should be primed that running the day is a core responsibility." | § 6.1, § 6.2, § 7.2. |
| F2 | "Tap works for now." Location inference counts as evidence. "Non-essential tasks don't need checks. We don't want users being bogged down with notifications." | § 5.9. The tap is in the app — see § 7.4 on why not on a notification. |
| F4 | Goals, mission and the top-tier files are managed by Metatron; "Synth, for now, would mediate. Some deadline priorities can be inferred — taxes for example." | § 4.1 (`stakes_source: inferred`). |
| F6 | Empty-day check-ins mirror today's setup (3 h lag, ≥3 h apart, ≤3/day, waking hours). | § 7.3. |
| F8 | "A shorter test just to ensure everything is working and then use real usage via mike persona as our determinant." | § 11.3. |
| F9 | (a) wake-and-decide: Synth is woken at plan-marked points and either speaks or holds; skips the Coordinator. | § 7.2. |
| F10 | Non-essential = not linked to an essential goal and no vital deadline; medication always essential. No notification check; one line at the evening close; anything unanswered ends the day **unconfirmed** — never raised as overdue, never triggers make-ups. | § 4.1, § 6.6. |
| — | Wearables: deferred, being researched offline. | § 15. |

---

## 3. The shape

```
calendar (commitments)  ─┐
ledger (tasks + priority, stakes, goal links) ─┤   code: snapshot → fingerprint → GATE
day shape (design defaults + user's hours) ───┤           │ none / repair / reshuffle
location zone, travel times (cached) ─────────┘           ▼
                                   code skeleton → code fill ──► validator ──► plan file
                                   (reshuffle: model refines the fill; code validates;
                                    failure keeps the code plan)
                                                          │
                     Synth package (both pipeline twins) ◄┘  whole day, now/next,
                     + conduct module                         suggested nudges & checks
                                                          │
                     scheduler tick → due nudge/check → wake Synth (no Coordinator)
                                                          → speak, or [HOLD]
```

**Three owners, no copies.** The ledger owns what must be done and whether it was; the calendar
owns commitments; the plan owns *when*, and only that. A plan block carries a ref
(`ob_…@2026-10-24` or a calendar uid or a generated id like `meal:lunch`), a time, and a derived
status computed from the ledger at render time. **Nothing in the plan can re-raise a task the
ledger has closed**, because the plan never holds task state to go stale — the six-stores failure
the ledger plan measured (§ 1 there) is the thing this structure rules out.

---

## 4. Data — what lives where, and what deletes it

### 4.1 Ledger additions (`tools/obligations.py`, Amber)

| Field | On | Values | Set by | Default when absent |
|---|---|---|---|---|
| `goal_id` | any task | a goal id from the persona's `goals.yaml` (`q1`, `w2`…) | `open_task` / `update_task(action="link_goal")` | none |
| `priority` | any task | `high` / `normal` / `low` + `priority_source: stated|inferred` | `update_task(action="set_priority")`; Synth mediates (F4) | derived from the goal (§ 5.2) |
| `stakes` | deadline | `vital` / `missable` + `stakes_source: stated|inferred` | `open_task` / `update_task(action="set_stakes")` | **treated as vital** (fail-safe: a missed tax deadline costs more than a lost evening) |
| `zone` | any task | a zone name from `zones.yaml` ("gym") | `open_task` / `update_task(action="set_zone")` | none — no location evidence possible |

The stated-never-overwritten-by-inferred rule already used for `minutes` (`_set_minutes`,
`:1081`) applies to `priority` and `stakes`. All four go through the **existing** `open_task` /
`update_task` tools — new actions and parameters on schemas already granted to `synthesizer`,
`finance` and `logistics`, so **no new grant**.

**Exposed only from Stage B** *(review R1-1)*. A tool schema's description is in the prompt of
every agent granted it, so shipping the new actions in Stage A would let Synth write priority,
stakes and goal links into the live ledger with no conduct telling it when — and those are the
fields the Stage B behaviour keys on. The handlers accept the new arguments from Stage A (tests
need them), but the schemas are built by `task_schemas()` / `goal_schemas()`, which add the new
actions and parameters **only when `day_plan.yaml` `ledger_fields` is on**. `register_tools()`
rebuilds schemas on every agent call (`orchestrator.py:5354`, `6841`), so the flag is read live; a
snapshot test pins the flag-off schemas **byte-identical to today's**. The Vertex cache key hashes
tool *names* only (`orchestrator.py:3598-3599`), so a flip reaches the cached Synth within the
10-minute cache TTL — acceptable, and stated so nobody reads the lag as a failure.

**`essential` is derived in code, never stored** (`is_essential(task, goals)`):
linked to a goal with `essential: true`; OR `priority == "high"`; OR a deadline whose stakes are
vital or unknown; OR **medication** — a code net over `what`/`note` (medication, meds, pill(s),
tablet(s), dose, inhaler, insulin, prescription…) that errs toward essential, because the model
being asked to mark medication is a safety flag no test has exercised (the 2026-08-04 lesson).
The net is a backstop, not the definition; a false positive costs one check.

**`update_goal` gains `essential`** (`tools/goals.py` `_EDITABLE`, schema) — today only
`write_goals` can set it, so Synth could not mediate goal importance as F4 requires. Granted to
Synth already; exposed behind the same `ledger_fields` flag (R1-1).

**The unconfirmed rule (F10), behind flag `unconfirmed_rule` (off in Stage A):**
- *Habits*: at period end (`_finalize_periods`, `:1967`), a **non-essential** habit period with
  `done < target` and not skipped records `state: "unconfirmed"` instead of `"missed"`. Essential
  habits record `missed` exactly as now. During the period, a non-essential weekly quota gets **no
  make-up note** (`_view_core`'s `behind` branch, `:910-913`).
- *One-offs*: a non-essential deadline past its date shows as `lapsed` — not under **Now**, not
  "overdue", counted under Later as "past their date, unconfirmed". It stays open (Mike's ledger
  decision 4 — "overdue until done or dismissed" — now applies to essential deadlines; F10
  refines it for the rest). `moot_after` still applies.
- *Adherence*: `adherence()` counts an unconfirmed period in the denominator exactly as `missed`
  is today (the rate does not improve by not asking), reported as its own `unconfirmed` count.
  `daily_task_counts` gains `tasks_unconfirmed` (A9 rows are append-only; older rows lack the key).
- **Medication is essential by the code net, so it never becomes unconfirmed** — the before-Alpha
  `MEDICATION_MISSED_CRITICAL` decision (ROADMAP § 0 clause 8, added `75ad88b`) is unaffected.

**The day boundary** — `day_starts`, exactly as designed in
`archive/plans/reply_latency_plan_2026-10-24.md` § 6.4 (one `_ledger_day(dt)` used by every date
consumer, enumerated by grep, each pinned by a test at 01:30 with `day_starts: "04:00"`; set via
`update_task(task_id="settings", action="day_starts", note="04:00")`; default `"00:00"`, identical
to today). **This plan claims that item** — the 10-25 handoff lists it as an undated session of its
own; building it here removes it from that list. The planner's day key is `_ledger_day(now)`.

### 4.2 Day shape (`tools/day_shape.py`, new, Amber)

- **Design defaults** (agent layer, every user): `config/modules/day_shape.yaml` — meal windows and
  lengths (breakfast within 90 min of wake, 15 min; lunch 12:00–14:00, 30 min; dinner 18:00–20:30,
  45 min), a 10-minute break after 90 minutes of consecutive task blocks, a 5-minute transition
  between task blocks, a 10-minute buffer before any departure, wind-down (no work or deadline
  blocks in the last 60 minutes before bed). **Comfort breaks are the break rule**, not a block
  type. Values are tuning knobs — config is the product.
- **The user's hours** (persona data): `data/personas/{p}/day_shape.yaml` — `wake`, `bed` (with
  optional weekend variants), `work_days`, `work_start`, `work_end`, `focus` (windows), `personal`
  (protected windows), meal overrides, `travel_mode` (default `transit`), `location_sharing`.
- **Until set**: wake and bed come from the persona's `scheduler.yaml` `quiet_hours` end and start —
  the only structured window that exists today. No work hours are assumed.
- **Writer**: `set_day_shape(field, value, evidence)` — validated per field, the user's words as
  `evidence`, **refused on a scheduled turn** (the close gate's turn fields, as the ritual-pause
  build reuses them: Mike's "limited scope to change things that they otherwise didn't initiate").
  Registered in `register_tools()` and classified in `core/actions.py` in Stage A; **granted** to
  `synthesizer` and `goals_interviewer` in Stage B (Red).

### 4.3 Plan state (`data/personas/{p}/day_plan/`, written by code only)

| File | Holds | Deleted by |
|---|---|---|
| `plan_YYYY-MM-DD.json` | the day's blocks, unplaced items, suggestions, the input fingerprint, `built_at`, `mode` (`code`/`model`) | the builder prunes files older than 3 days (yesterday's is read by the evening-close and boundary logic) |
| `state.json` | calendar snapshot + its age, reshuffle request `{reason, at, force}`, per-day counters (reshuffles, travel lookups), handled nudge/check ids, rhythm-suggestion stamp, schedule-impact notes (today only) | overwritten in place; per-day keys roll at the day boundary |
| `log.jsonl` | one row per build and per nudge decision: trigger, mode, validator failures by rule, churn vs previous plan (moved/added/dropped counts), placed/unplaced counts, model tokens and latency, outcome (`sent`/`held`) — **ids and counts only, no task words** | the builder prunes rows older than 90 days |
| `travel_cache.json` | `(origin, destination, mode, date, hour) → minutes` | entries expire at the day boundary |

Cross-process: the server (turn-time repair) and the scheduler (ticks) both write. Writes take an
`fcntl.flock` on `day_plan/.lock` and replace atomically (temp + `os.replace`, 0600) — the ledger's
`threading.RLock` (`:171`) is in-process only and is **not** sufficient here. The lock is held for
file I/O only, never across a network or model call, and the reply path takes it non-blocking
(§ 7.1).

### 4.4 The three persistence questions (global cost rules)

1. **Unit of standing cost**: disk only — a few KB/day, ~5 MB/year of log. No billed resource
   persists between calls: no cache on Vertex (the planner is deliberately **not** on the cached
   path; caching a few calls a day is pure storage cost — `orchestrator.py:5238-5249`), no warm pool.
2. **What deletes it, and restart**: the pruning above, run by the builder. On restart every file
   survives; a plan whose day key is not today's is stale by construction and the gate rebuilds it.
3. **Which meter reports it**: none needed for disk. Travel lookups and model calls are counted in
   `state.json`/`log.jsonl` (§ 12) because the spend guard does not see Routes at all.

---

## 5. The engine (`tools/day_plan.py`, new, Amber)

### 5.1 Inputs and the snapshot

- **Calendar: all calendars, read-only.** `_query_events(today, tomorrow, calendars="all")` — the
  mode that expands recurring series (`occurs_in_range`) and returns local-naive times
  (`caldav.py:703-713`). **This widens an unattended reader, which the caldav comment
  (`:285-291`) calls "a decision, not a default"** — taken here because the planner's whole job is
  the real day: planning over the account's own calendar and "Shared with Mike" as though they were
  empty would be wrong in a way the user would see. It reads; it never writes. All-day events are
  context (deadline markers, UK holidays), never time blocks — detected as calendar_reconcile does
  (`:256-257`, 00:00 start and ≥ 23 h), since no `all_day` field exists. Events whose titles match
  `calendar_reconcile.yaml`'s `ignore_titles` (lunch, commute, focus time, break, travel) are read
  as the user's own blocks of that type, not as meetings — a calendar "Lunch" replaces the lunch
  meal block. Event text is untrusted (it reaches a model at reshuffle): it is passed inside
  `wrap_untrusted`, as `accountability.py:765-779` does.
- **Snapshot age, and the reply path** *(review R1-8, verify NEW-1)*. One rule decides where a
  calendar fetch may run, in both stages:
  1. **A background refresh**, started by any reader that finds the snapshot older than 10 minutes
     (or absent): one worker thread, single-flight (a second stale read while one is running starts
     nothing), never awaited. **Every thread this module spawns resolves the persona in the
     spawning thread and binds `persona_scope(persona)` itself as its first act** *(verify-2 N1)* —
     identity is thread-local and fail-closed (`core/persona.py`), so an unbound worker would die on
     its first `persona_data_dir()` and the snapshot would never land. One helper,
     `_spawn_bound(fn)`, is the only way the module starts a thread (refresh and reshuffle alike), and
     a worker failure is written to `log.jsonl` as `refresh_failed`, not only to the server log. The reader renders what is stored now — with its age — and the next
     read gets the rebuilt plan. **In Stage A this is the only producer**, and the Today panel's
     30-second poll (`/plan/today`) is what drives it, so the snapshot is as fresh as the panel is
     used; the very first read builds a calendar-less plan marked *"reading your calendar…"* and the
     next poll has it. In Stage B the refresh tick also starts it every 5 minutes.
  2. **A synchronous, time-boxed fetch (3 s)** only when Metatron itself wrote the calendar during
     this turn (`tools/caldav.py`'s write, update and delete paths call
     `day_plan.note_calendar_write()` — one line each): that is the "my 3pm got cancelled" case and
     the point of same-reply repair. On timeout the stale snapshot is used and a background refresh
     is started.
  3. **Nowhere else.** A reply or a poll never waits on a CalDAV REPORT. Tests: a stale read starts
     exactly one background refresh and returns without waiting, **and the snapshot is then on disk
     for that persona** (the refresh ran bound — a test that only counts starts would pass with a
     dead worker); a reply turn that wrote nothing makes zero synchronous CalDAV calls; a turn that
     wrote the calendar re-fetches inside the box.
- **Ledger**: `_load()` + `_view()` for today (and tomorrow in the evening window); `minutes`, the
  new fields, `is_essential`.
- **Location**: `current_zone()`; zones' `lat,lon` from `zones.yaml`. The transitions log stores
  client stamps as UTC `Z` strings verbatim and server stamps local-naive
  (`tools/location.py:224`) — **the planner normalises both to local** before comparing.
- **Travel**: `get_travel_time(origin, destination, mode, arrive_by)`. Origin = the previous located
  block's location, else the current zone if entered today, else the `home` zone, else no travel
  block (noted). Cached per § 4.3; **capped at 60 lookups/day**; on cap, error or no key, assume
  30 minutes and mark the block `travel: estimated`. **Fix in this build**: `routing.py:101-102`
  labels a naive local `arrive_by` as UTC — an hour wrong for transit under BST. Convert with the
  persona timezone; test it. (Dormant from 2026-10-25 to March, when the UK is on GMT — fixed now
  so it is not rediscovered then.)

### 5.2 Candidates and the score

Candidates: today's actionable occurrences (overdue, due today, daily habits, planned or at-risk
quota days, due intervals, deadlines inside the lead window when there is room), each with
`minutes` (default 30, flagged `length unknown` so Synth asks once — the existing `minutes` conduct).
`waiting` items are never placed — someone else's move.

Score (all weights in `config/modules/day_plan.yaml`):
- **Baseline (Q5 "A")**: explicit `priority` high 30 / normal 20 / low 10; absent → derived from the
  goal: essential goal 30, other goal 20, no goal 15.
- **Dynamic (Q5 "B")**: vital deadline overdue +40, due today +30, tomorrow +15, inside lead +5;
  missable due today +10, lapsed +0; habit planned day +10, at risk +15; daily habit +10; due
  interval +15; medication +50.
- Ties: earlier due, then shorter.

### 5.3 Skeleton

**Windows are datetimes anchored on the ledger day, never same-date times** *(review R1-7)*. For
ledger day D: `wake_dt = D + wake`; `bed_dt = D + bed`, **plus one day when `bed ≤ wake`** (a 01:30
bedtime, or the 22:00–07:00 quiet-hours fallback read the other way round); the ledger day itself
runs `D + day_starts` → `D + 1 + day_starts`. The plan for D covers `[max(now, wake_dt), bed_dt]`.
At 00:45 with `day_starts: "04:00"` and bed 01:30, the current plan is still D's and its blocks
until 01:30 are valid. Every comparison in the engine and the validator is on these datetimes.

Fixed blocks: timed calendar events.
Travel blocks before located events (and back, when the next block is elsewhere or home). Meal
blocks placed in the largest gap inside each window, or skipped when a calendar block covers it.
Wind-down. Protected `personal` windows reserved. Breaks and transitions are inserted during fill.

### 5.4 Fill (code), and the life-quality rule

Greedy by score into the earliest gap that fits; long items prefer `focus` windows when defined.
**A missable item is never placed in a protected window, sleep or wind-down. A vital one may take
protected time — and the block carries `displaced_protected: true`, which Synth is told to say out
loud** ("this eats your evening because the return is due tomorrow"). What does not fit goes to
`unplaced` with a reason (`no room`, `outside waking hours`, `not yet eligible`).

### 5.5 Validator (runs on every plan, code or model)

Hard rules — a failure rejects the plan: **V1** no overlaps among non-buffer blocks; **V2** every
fixed event present and unmoved; **V3** every ref resolves to an open ledger occurrence or a
snapshot uid (a model cannot invent a ref); **V4** placed length ≥ `minutes`; **V5** inside the
waking window as § 5.3 defines it (datetimes, possibly crossing midnight) and not in the past; **V6** no missable item in protected time; **V7** every vital
deadline due today or overdue is placed or listed `unplaced: no room`; **V8** a located fixed event
is preceded by travel ≥ its minutes when known; **V9** no duplicate refs (a habit with `times > 1`
excepted). Soft rules, logged: churn above 3 blocks on a reshuffle; a lower-scored item placed
before a higher one with room.

### 5.6 Repair, reshuffle, and the gate

*(Rewritten for review R1-3: a single hash says that something changed, never what — and the
table below needs to know what.)*

**What the plan stores to diff against — digests, not task state.** For each candidate ref: an
opaque digest (sha256 over its status, done-count, due, minutes, priority, stakes, goal link) and
the **score** it was placed with. For each fixed calendar uid: a digest over start, end, location,
status. Plus the day-shape file's digest, the zone and the ledger day. A digest cannot render a
status, cannot be read back as a task and cannot re-raise anything; the score is the plan's own
derived number. **Every classification below reads the live ledger and snapshot, never a stored
copy** — so Mike's "no additional copy" holds.

**The gate**: recompute the digests; diff them against the stored ones; classify.

| What the diff shows (classified against the LIVE ledger) | Mode |
|---|---|
| nothing, and no block boundary crossed | **none** — the stored plan is rendered |
| a block boundary crossed; a ref now terminal, or its done-count rose; a ref removed (dismissed, rescheduled out); minutes, due or notes changed with the score moving < 10; a fixed uid moved, added or removed | **repair** — code: rebuild the skeleton, keep the placed order, shift flexible blocks into the next gaps, drop the lowest score to `unplaced` if needed |
| a ref **added** to the candidate set; a ref's **score moved ≥ 10** (priority, stakes, a deadline crossing into "today"); an essential block passed undone; a repair that dropped or displaced an essential item; a `major` schedule impact; Synth's `request_replan`; the first build of the waking day; the evening look-ahead | **reshuffle** — requested; runs off the scheduler loop (§ 7.1) |

So the ordinary ledger write — a task done, a length recorded, a note — is a repair, and only a
change to *what the day contains or how much something matters* spends a reshuffle against the cap.

Repair is synchronous wherever the plan is read — it is code over a cached snapshot, milliseconds.
**Before Stage B there is no model and no tick**, so a "reshuffle" is a code rebuild done
synchronously on read; that is also the fallback whenever the model is off, refused or invalid.
Debounce: model reshuffles ≥ 15 minutes apart unless forced; **≤ 12 per day** (the cost bound, § 12).

### 5.7 The reshuffle (model) contract — Stage B

- Agent `day_planner` (new `config/agents/day_planner.md`, Red), called as the precedents are —
  `run_session("day_planner", input, persona, bare=True)` — **without `complexity="quick"`**, which
  would silently route it to Flash-Lite (`router.py:112-121`). Model: Gemini 3.8 Flash (judgement
  over the user's history; `core/build/gates.check_tier()` refuses that on the bulk tier for Build
  for the reason ROADMAP § D2 records).
- `bare=True` gives no clock (`orchestrator.py:5285-5301`): the input carries today's date, the time
  and the timezone.
- Input JSON: waking window, fixed and protected blocks, meals, candidates (`ref`, `what`,
  `minutes`, `score`, `essential`, `stakes`, `due`, `domain`, the goal's `title`/`shareable_what` —
  **never `private_why`**), the current plan, today's schedule-impact notes (the user's own words,
  ≤ 3). Calendar text wrapped as untrusted.
- Output: `{"placements": [{"ref","start","end"}], "drop": [{"ref","reason"}], "note": "…"}`, parsed
  with a balanced-brace JSON extract (not `intake_extract.py`'s non-greedy `\{.*?\}`, which breaks
  on nesting), merged onto the skeleton, validated. **Any failure keeps the code plan** and logs why.
- **Spend refusal**: `run_session` returns the spend guard's refusal as prose, not an exception
  (`orchestrator.py:7101-7104`), and the two nightly gates store a wrong result when that happens.
  The runner calls `check_before_session()` first and treats a non-JSON reply as failure — it never
  writes or advances state on one.
- **Thinking is unbounded on this path** (the compat loop has no thinking cap;
  `orchestrator.py:4124-4126`, `4773`), billed as output. Bounded by the daily cap; measured in the
  smoke test (§ 11.3); a per-agent cap added if Vertex's OpenAI-compatible endpoint honours one
  (verify `reasoning_effort` / `extra_body` thinking config live — not assumed).
- Traced with `is_proactive=True` (a new `proactive` kwarg on `run_session` → `start_request_trace`),
  so A9 does not count planner calls as user sessions (`tools/analytics.py:141-149` counts any
  non-proactive trace as one; the judge and CRM sweep inflate it today — § 14).
- Privacy: the routing entry carries the same tier statement the judge's does
  (`routing_cloud.yaml:102-116` — Sensitive tier on Vertex, valid on the Amendment 2026-08-28
  basis); `allowed_tools: []`; `local: true` in `routing.yaml` (fail-closed).

### 5.8 Stability

Blocks starting within 20 minutes keep their slot unless their fixed anchor moved. The model is
given the current plan and told minimal change is preferred; churn is logged. A plan that thrashes
is worse than one slightly suboptimal (Mike's 08-19 consistency concern, which F8's live use
measures through the churn column).

### 5.9 Nudge and check suggestions — derived in code, decided by Synth

- **Nudges**: leave-now for travel (`depart_at − buffer`); the start of an essential block; a
  `displaced_protected` block. Non-essential blocks get none.
- **Checks**: at the end of an **essential** block whose occurrence has no outcome. **None** for
  non-essential blocks (F2), and none when completion is inferable: the user's words already closed
  it, or **location evidence**.
- **Location evidence is presence, never duration** *(review R1-4)*. The transitions log holds only
  `(zone, entered_at)` on a zone change, written when the app pings on a message or a tap
  (`tools/location.py:211-242`) — it cannot say how long anyone stayed, and the plan does not
  pretend it can. The rule: a task with a `zone`, and a transition **into that zone** whose
  `entered_at` (normalised to local, § 5.1) falls in `[block start − 60 min, block end]`. Its text
  says exactly that — *"at the gym at 18:05"* — and nothing about how long.
- **What the evidence does**: it suppresses the check and files a **"Mark done?" proposal**. It
  never records a completion — the close gate (`4f88d19`) allows only the user's words, a tap or an
  approved suggestion — so a false positive costs one declined tap, not a wrong record.
- **The proposal model is reworked to carry it** *(review R1-5)*. Today it cannot: `add_proposal`
  refuses anything not a one-off (`:1768`), dedupes and hashes on `envelope_id` (`:1771-1773`),
  `resolve_proposal` closes with the hard-coded `_CORRESPONDENCE_EVIDENCE` (`:1757`, `:1826-1827`),
  and the server and app render every proposal as an email (`server.py:1383-1401`,
  `index.html:3826-3828`). Rework, scoped as A2b: proposals gain `source` (`correspondence` |
  `location`); a location proposal may target a habit or interval **occurrence** and carries its
  date; the dedupe key is `envelope_id` for correspondence and `zone@date` for location, and the
  proposal id hashes over `(task, source, key)`; acceptance closes with source-specific evidence
  (`"location evidence, approved in the app"`) and, for a habit, records `done` with `on_date`;
  `pending_proposals` returns `source` and `basis`; `_proposals_for_display` reads intake records
  for correspondence only and passes `basis` through for location; `renderProposal` branches on
  `source` (*"Mark 'Gym' done? You were at the gym at 18:05."*). Existing correspondence proposals
  have no `source` and read as `correspondence` — no migration. **Suppression and the proposal ship
  together or not at all** *(verify NEW-2)*: location evidence suppresses a check only when it has
  filed the proposal that replaces it. If A2b slips past Stage A, location evidence does nothing —
  the check happens as for any essential block — so an essential located task the user did do
  always gets either a check or a "Mark done?" card, never neither.
- Each suggestion has a stable id (`nudge:<ref>@<HH:MM>`), so it is handled once.

### 5.10 Also built by the engine

- **Tomorrow's draft**: in the evening window (from the persona's `evening_close` time, else 19:00),
  a code-only plan for tomorrow, rendered as a short "Tomorrow (draft)" section on evening turns.
- **Rhythm suggestion (Q13)**: from non-proactive conversation timestamps, when the user is active
  after midnight on ≥ 9 of the last 14 days, the block offers Synth one line: *the user's day seems
  to run to ~01:30 — offer once to end their day later*; stamped so it is offered once a fortnight.
- **Goal-allocation gaps (Q6/F5)**: active goals with no linked habit task, or whose record changed
  since the linked task was opened (a `goal_hash` stored on the task when linked), listed on
  weekly-review turns only.

---

## 6. Synth

### 6.1 The plan block — both pipeline twins

`_day_plan_block(persona, kind, is_proactive)` in `core/orchestrator.py`, placed beside
`_horizon_block` in **both** `run_pipeline_session` (`:6577-6591`) and
`_run_pipeline_session_stream_inner` (`:6808-6822`) — after the specialists have written, so a
calendar change made this turn is repaired **in the same reply** (Q10). It is in the Synthesizer
package only: the `load_recent_context` loop (`:1258-1270`) reaches the Coordinator too, which
does not need it.

Contents (target ≤ 1,000 tokens; measured in tests on a full fixture day):

```
TODAY'S PLAN — kept by code from the calendar, the tasks and the user's day shape. Authoritative
for timing. Running the day is yours: say what to do now and next.
Now (14:05): Deep work — Apex migration plan `ob_…` (until 15:30)
Done: 07:40 stretching ✓ · 09:00 stand-up (calendar) ✓
Unconfirmed: 12:30 groceries (non-essential — evening close only)
Next: 15:40 leave for physio (25 min, transit) → 16:15 Physio (calendar)
Later: 18:30 dinner · 19:30 call Mum `ob_…` · 22:00 wind-down
Not placed: Chase dispute letter (no room — due Friday)
Suggested: 15:30 nudge — leave for physio · 15:30 check — Apex block (essential)
[A fuller rework of the rest of today is under way — say so in one line.]   ← testing only
```

Statuses are derived from the ledger at render time, never stored. On `evening_close` turns it adds
"Unconfirmed today (non-essential)" for the one-line ask and "Tomorrow (draft)"; on weekly-review
turns, goal-allocation gaps.

### 6.2 Conduct — a module, plus one line in synthesizer.md

- `config/modules/synthesizer_day_plan.md` (Amber), injected by `_synth_conditional_sections`
  (`:398-427`) **whenever the plan block is present** — the code-conditional pattern ROADMAP § D2
  endorses for Synth slimming. Static text, so the Vertex cache key changes only with the flag, not
  per turn. It carries: how to use the plan; Q2's morning proposal and silent replans; nudge and
  check decisions, batching, and holding; the testing heads-up; when to set `minutes`, `stakes`,
  `priority`, `goal_id`, `zone` (ask once, infer the obvious — taxes are vital); the evening
  one-line ask; the weekly goal allocation; `day_starts` on command; the rhythm offer;
  `request_replan` only for the extraordinary. **Mike reviews this text in Stage B** even though it
  is not Red by `settings.json` — it carries behaviour.
- `config/agents/synthesizer.md` (Red, Stage B): **one** line in § Role — *running the user's day,
  knowing what they should be doing now and next, is a core responsibility; the day plan section is
  how* — and the two new tools in § Tools. Everything else is the module, so synthesizer.md grows
  by a few lines (Q11: no meaningful weight beyond its directives).

### 6.3 The testing heads-up and the output filter

The filter suppresses machinery narration (`orchestrator.py:1740-1780`). Measured against its
patterns: "plan", "planner", "reshuffle", "rework your afternoon" match nothing; **"the tools" alone
suppresses a whole reply** (`:1771`), and "the underlying system" does (`:1778`). The module words
the heads-up as life — *"I'll rework the rest of your afternoon around that"* — and forbids
machinery words. A test runs the module's example sentences through `filter_output`.

### 6.4 Tools

| Tool | New? | Granted to (Stage B, Red) | Purpose |
|---|---|---|---|
| `set_day_shape(field, value, evidence)` | new | synthesizer, goals_interviewer | § 4.2 |
| `request_replan(reason)` | new | synthesizer | the extraordinary case: force a reshuffle (within the daily cap); returns "a fuller rework will land within a few minutes" |
| `open_task` / `update_task` | existing, new params/actions | already granted | § 4.1 |
| `update_goal` | existing, `essential` added | already granted | § 4.1 |

Both new tools are registered in `register_tools()` with 8-space handler lines
(`tests/test_action_provenance.py`'s regex), classified in `core/actions.py`, and appear under
§ Tools in the agent files that are granted them, so `scripts/check_agent_tools.py` stays clean.

### 6.5 The Coordinator's schedule-impact line (Stage B, Red)

`coordinator.md`'s routing package gains: `SCHEDULE_IMPACT: [none | minor | major] — [what changed
about the user's day, in their words; omit if none]`. Code parses it after the Coordinator runs
(both twins, beside `_handle_misheard`): `minor` → noted for the next reshuffle's input; `major`
("my afternoon got cancelled", "I'm off sick") → reshuffle requested and the heads-up shown. The
parser ships in Stage A as a no-op; the line starts appearing when coordinator.md changes. This is
the routine path; `request_replan` stays for what the Coordinator could not see.

### 6.6 Evening close and weekly review

- **Evening close**: the block lists today's unconfirmed non-essential items; the module says ask
  about them **in one line, once**, and record what the user says (`done`/`skipped`); anything
  unanswered is left — the boundary records it unconfirmed (§ 4.1).
- **Weekly review**: for each goal-allocation gap, Synth consults whoever owns the domain through
  its existing `run_subagent` (the plan never names a specialist, so narrower agents replace them
  without touching this), proposes standing time, and records it as a habit task with `goal_id`
  (e.g. 3×45 min/week). Stored once; revisited only when the goal changes (`goal_hash`) — F5.

---

## 7. Nudges and check-ins

### 7.1 The ticks (Stage B registers them; Stage A builds and tests the functions)

| Job (`_DEFAULT_JOBS`, `core/scheduler.py`, Red) | Cadence | Function | Speaks? |
|---|---|---|---|
| `day_plan_refresh` | every 5 min | `tools.day_plan.refresh_tick` — snapshot if > 10 min old, gate, repair, run a requested reshuffle, build tomorrow's draft in the evening, prune | never; returns a string |
| `day_plan_nudge` | every 5 min | `tools.day_plan.nudge_tick` — due suggestions and empty-day check-ins → wake Synth | returns `{"notify": True, …}` only when Synth spoke |

Both set `respect_quiet_hours: False` — `tests/test_scheduler_gates.py:261-264` requires it of every
default job — and `nudge_tick` **gates quiet hours itself**, the `intake_sweep` precedent
(`scheduler.py:722-735`), reading `time_in_quiet_hours` so there is one implementation. It also
skips while the user is mid-conversation (last message < 10 min ago) — the live turn's plan block
already shows what is due. `scripts/check_scheduler_functions.py` must resolve both paths with no
import side effects (anything from `core.scheduler` is imported inside the function).

**The fixed-session shield applies to nudges** *(review R1-6)*. `_near_fixed_job_blocks` returns
`None` for any job without `agent` (`scheduler.py:308-309`), so a function job is never shielded —
left alone, a nudge could wake Synth at 07:23 ahead of the 07:30 brief, the [DB-0822-07]
back-to-back incident. Stage B extracts the scan in `_near_fixed_job_blocks` into
`near_fixed_session(cfg, now) -> str | None` (one implementation, both callers), and `nudge_tick`
calls it: anything due inside the 30-minute window is **not woken** — it is marked `carried` and
appears in that fixed session's plan block under DUE NOW, so the brief or close says it instead.

**Reshuffles run off the scheduler loop** *(review R1-8)*. The daemon runs jobs one at a time on
its main thread (`schedule.run_pending()`, `scheduler.py:1071`), so a 20–60 s model call inside
`refresh_tick` would delay the snapshot refresh, `nudge_tick` and every other job. `refresh_tick`
does the fast work inline — snapshot, gate, repair — and starts a requested reshuffle on a worker
thread bound with `persona_scope`; the next tick picks up its result.

**No lock is held across a model call** *(verify NEW-3)*. The plan lock (`fcntl.flock`) guards file
reads and writes only — milliseconds. The worker (1) takes the lock, copies its inputs and writes a
`reshuffle_inflight {gen, started_at}` marker to `state.json`, releases; (2) calls the model with no
lock; (3) re-takes the lock, re-validates the result against the **current** skeleton and ledger —
if they moved meanwhile, it re-merges and re-validates, and on conflict discards the result and
re-requests — writes, clears the marker, releases. Single-flight is the marker, not the lock: a new
reshuffle does not start while a marker younger than 180 s exists. Python cannot kill a hung thread
(the model client's own timeout is 300 s, `orchestrator.py:4144`), so a worker whose `gen` has been
superseded discards its result when it finally returns. **The reply path takes the lock
non-blocking** (`LOCK_NB`, retried up to 200 ms); if it cannot get it, it renders the stored plan
and writes nothing. Test: with a worker parked mid-call, a turn-time repair completes in < 200 ms.

### 7.2 Wake-and-decide (F9 a)

1. `nudge_tick` collects everything due now (nudges whose time has come, checks past their block
   end, an empty-day check-in) **into one wake** — batching is F2's ask.
2. It calls `send_one(persona, directive, nudge=True)` (`core/remote_client.py`, new kwarg → a
   `"nudge": true` field on the existing `send` frame).
3. **Server, nudge mode** (`core/server.py` WS handler, `:924-1069`): no `stream_start` broadcast and
   no chunk broadcast — chunks go to the sender only; the reply is buffered. On completion: a reply
   that is exactly `[HOLD]` saves nothing, logs nothing, broadcasts nothing, and sends
   `{"type": "held"}` to the sender; anything else is saved (`_save_exchange`, `_log_conversation`,
   `proactive=True`) and broadcast as one `message` frame **with `"proactive": true`** — which the
   client renders as a Metatron bubble and alerts on (`index.html:1864-1868`, `1925-1933`).
   *That key is missing from the ordinary `message` broadcast today (`server.py:1061-1069`), so a
   device that missed `stream_start` renders a scheduler prompt as user speech; added for every
   turn here.*
4. **Pipeline, nudge mode** (a `nudge` kwarg on `run_pipeline_session_stream`, built into the
   existing function — not a new path, so `filter_output`, the `[CONTEXT]` split,
   `persist_context_block` and `_close_turn_bookkeeping` all still run): the Coordinator and
   specialists are skipped and replaced by a fixed minimal package; the plan block carries a
   **DUE NOW** section listing the batched items; the directive tells Synth to speak about what is
   worth it or reply exactly `[HOLD]`. A held turn is not appended to the session history.
   **A due-item nudge binds no scheduled-run kind** *(review R1-2)*. `close_scheduled_run` stamps a
   single `scheduled_runs.last` slot shared by every kind (`tools/context_tracker.py:827-851`), and
   `note_scheduled_run` compares against it regardless of kind (`:882`) — so a nudge that stamped it
   would make the next morning brief or evening close read "nothing new" and carry the
   quiet-check-in directive beside the plan's "say what to do now and next". So the nudge passes
   `kind=None` to `_close_turn_bookkeeping` (no stamp) and gets no focus block. Nothing it needs is
   lost: the ledger's raise-once keys on `user_turn`, not `kind` (`obligations.py:1474-1475`), and
   the day-plan module is injected on the plan block's presence. An **empty-day check-in** binds
   `kind = "companion_checkin"` — the job it replaces — so its slot behaviour is today's, exactly.
   **And the quiet directive is never applied to `morning_brief` or `evening_close`** — one guard in
   `_scheduled_focus_block` (`orchestrator.py:486-489`). Those are the fixed points the module calls
   "not interruptible", and Q2's proposal and F10's evening line live in them. *This changes an
   existing session, not only new ones — today a quiet late-afternoon check-in can already demote
   that evening's close to a light check-in (§ 14).*
5. `nudge_tick` marks each id handled with its outcome and returns the notify dict, so the existing
   web push to browser subscriptions fires as check-ins do today.

Cost per wake: Synth only — no Coordinator, no specialists.

### 7.3 Empty-day check-ins replace the fixed check-in

On a day with no flexible blocks left, `nudge_tick` offers a check-in when the user has been idle
≥ 180 min, the last one was ≥ 180 min ago, fewer than 3 today, inside waking hours — the current
`companion_checkin` numbers (template `config/templates/scheduler.yaml:36-54`). The fixed job
yields: `fire_session` (Red) skips any job named in `day_plan.yaml`'s `replaces_jobs:
[companion_checkin]` while `owns_checkins` is on. Name-listed, not "every interval session job", so
agent-written standing check-ins (`schedules.yaml`) are untouched. Mike's live job name is checked
on the VM (`scripts/vm_read.py`) before the flag flips. Turning the flag off restores today's
behaviour exactly.

### 7.4 Delivery to the phone — the constraint this plan cannot fix by itself

**The APK has no push.** Push is Web Push/VAPID (`core/push.py`); the APK ships no push plugin
(`capacitor.plugins.json` is `[]`; no Firebase; `MainActivity.java:60-63` "zero Capacitor
plugins"), and Android's WebView does not implement the Push API. A scheduled message reaches the
phone only over the app's WebSocket while the app process is alive, as an in-app tone/vibration
(`maybeAlert`). **That is how today's check-ins arrive too** — so Stage B's nudges are exactly as
reliable as the current check-ins, no less. But a leave-now nudge that lands only when the app is
open is a weaker product than the vision, and "tap" on a notification (F2) is not possible: the
tap is in the Today panel. **Decision D1 (§ 14).**

---

## 8. Interview, location, day boundary

### 8.1 The first interview (Stage B, Red)

`goals_interviewer.md` Phase 1 already asks working hours, a typical day, when the user is at their
best, sleep, eating and exercise (`:77-94`). Phase 1 gains the missing day-shape items — wake and
bed, protected personal time, usual meal times, how they travel — plus the location question
(§ 8.2), and Phase 8's write-back records them with `set_day_shape` (granted then). **Mike's own day
shape** is seeded in a ~15-minute walkthrough in Stage B: questions prepared in advance, Mike answers
in the app, Synth records them — the (M) walkthrough rule.

### 8.2 Location opt-out for new users (F1)

`location_sharing` in day shape; the interview asks, framed toward yes. `GET /settings/location`
returns `{"on_send": true | false | null}`. The client (`index.html:3385-3471`): when the
`metatron_location_onsend` key is **unset** and the server says `true`, it stores `'on'`; `null`,
`false` or any error leaves it off; a stored local choice always wins. This keeps the 08-28
property that no default can be arrived at by accident — the user's interview answer is the act.
`tests/test_location_onsend_default.js` is extended with exactly those four cases. Mike is
unaffected (his key is already `'on'`). Built in Stage A, inert until a persona has the setting.

### 8.3 Day boundary on command and by observation

Command: `update_task(task_id="settings", action="day_starts", …)` — existing tool, no grant.
Observation: § 5.10's rhythm suggestion; Synth offers, the user agrees, the same call records it.

---

## 9. The Today panel — the testing view (Q1)

`GET /plan/today` (`core/server.py`) returns the plan's blocks when `day_plan.yaml` `show_in_app` is
on, `{}` otherwise. In Stage A its poll is also what starts the background calendar refresh (§ 5.1
rule 1) — it never waits on one. `#tasks-panel` (`index.html:833`) renders a "Plan" section above the task rows
only when blocks arrive — so moving to Q1 (a) is turning the flag off, no client change. The page is
bundled in the APK (`capacitor.config.json` `webDir: static`), so this needs **an APK rebuild by
Mike**. It reuses the panel's 30-second poll; the endpoint renders the stored plan after a gate
check — no rebuild per poll.

---

## 10. Stages, files and tiers

### Stage A — Amber/Green, built after the review resolves (this session or the next)

Flags in `config/modules/day_plan.yaml`: `build: true`, `show_in_app: true`, and **off**:
`ledger_fields`, `synth_reads_plan`, `unconfirmed_rule`, `reshuffle_model`, `nudges`,
`owns_checkins`. **Deployed, Stage A changes nothing Synth sees or does, with two deliberate
exceptions**: the transit `arrive_by` correction (§ 5.1), which makes Logistics' travel answers
right; and the quiet-directive guard on `morning_brief`/`evening_close` (§ 7.2). Every new tool
action and parameter is hidden behind `ledger_fields` (R1-1); the new tools are registered but
granted to no one; the plan block and module are behind `synth_reads_plan`. Mike watches the
code-built plan in his Today panel for a few days first.

| # | Work | Files |
|---|---|---|
| A1 | Day boundary (§ 4.1) | `tools/obligations.py`, tests |
| A2 | Ledger fields (schemas behind `ledger_fields`), `is_essential`, unconfirmed rule (flagged), adherence/analytics counts, `update_goal.essential` | `tools/obligations.py`, `tools/goals.py`, `tools/analytics.py`, tests |
| A2b | The proposal rework for location evidence (§ 5.9) — **last; may slip to Stage B** | `tools/obligations.py`, `core/server.py`, `static/index.html`, tests |
| A3 | `arrive_by` timezone fix | `tools/routing.py`, test |
| A4 | Day shape module + `set_day_shape` (registered, not granted) | `tools/day_shape.py`, `config/modules/day_shape.yaml`, `core/orchestrator.py` (`register_tools`), `core/actions.py`, tests |
| A5 | The engine: snapshot, candidates, score, skeleton, fill, validator, repair, gate, files, log, travel cache + cap, suggestions, tomorrow draft, rhythm, allocation gaps; `note_calendar_write` hooks | `tools/day_plan.py`, `config/modules/day_plan.yaml`, `tools/caldav.py` (3 lines), tests |
| A6 | Reshuffle runner (model injectable; inactive until the agent exists) + `run_session(proactive=)` | `tools/day_plan.py`, `core/orchestrator.py`, tests |
| A7 | Plan block in both twins, conditional module injection, SCHEDULE_IMPACT parser (no-op), pipeline nudge mode + `[HOLD]` with no scheduled-run stamp; the quiet-directive guard on the two fixed sessions; `request_replan` registered | `core/orchestrator.py`, tests (both twins) |
| A8 | Server nudge mode, `proactive` on `message` broadcasts, `/plan/today`, `/settings/location`; `send_one(nudge=)` | `core/server.py`, `core/remote_client.py`, tests |
| A9 | Client: Plan section; location default from server | `static/index.html`, `tests/test_location_onsend_default.js` |
| A10 | The conduct module text (inactive) | `config/modules/synthesizer_day_plan.md` |
| A11 | **Stage B's Red diffs, drafted and ready to apply** — the new agent file, both routing entries, the synthesizer/coordinator/interviewer lines, the two `_DEFAULT_JOBS` entries and the `fire_session` yield — so the Red session is review-and-apply | `archive/handoffs/<date>-day-planner-stage-b.md` |

Built in a git worktree off `main`; another window has uncommitted work in this tree, and the
10-25 ritual-pause session will touch `synthesizer.md` and both routing files (§ 16). Every file is
`git diff`-ed before staging. Mike deploys; Mike rebuilds the APK.

### Stage B — one Red session, Mike present (not delegated)

1. Apply A11: `config/agents/day_planner.md` (new); `day_planner` in both routing files; grants for
   `set_day_shape` and `request_replan`; the synthesizer.md Role and Tools lines; the coordinator.md
   SCHEDULE_IMPACT line; the goals_interviewer.md Phase 1/8 additions; in `core/scheduler.py` the
   two `_DEFAULT_JOBS` entries, the `fire_session` yield and the `near_fixed_session` extraction
   (R1-6). Run `scripts/check_agent_tools.py`.
2. Mike reviews `synthesizer_day_plan.md`.
3. Smoke test (§ 11.3).
4. Mike's day-shape walkthrough (§ 8.1).
5. Flip `ledger_fields`, `synth_reads_plan`, `unconfirmed_rule`, `reshuffle_model`; deploy; then
   `nudges` and `owns_checkins` once a day of plan-reading looks right (Q3: "early after
   production"). **The latency criterion lives here, where the plan first reaches the reply path**
   (R1-8): the plan block's build time is logged per turn — p95 ≤ 150 ms on turns that wrote no
   calendar — and Synth's reply wall-clock from traces is compared over two days either side of
   the flip.

---

## 11. Tests

### 11.1 Unit (synthetic persona, **every live meter stubbed** — CalDAV, Routes, model, push; the standing rule)

- Ledger: `day_starts` at 01:30 for every date consumer; each new field and action; stated beats
  inferred; `is_essential` incl. the medication net; unconfirmed vs missed with the flag on and off;
  lapsed one-offs; adherence and `daily_task_counts`; **flag-off schemas byte-identical to today's**
  (R1-1); location proposals on a habit occurrence and a one-off, deduped on `zone@date`, closed
  only through `resolve_proposal` under `_user_act` with location evidence; a correspondence
  proposal with no `source` still renders and closes as today (R1-5).
- Engine: a fixture day (fixed meetings, a located appointment, a recurring event via
  `occurs_in_range`, an all-day holiday, a calendar "Lunch", vital/missable/medication tasks,
  a weekly quota, a protected window) → expected blocks; each validator rule with a crafted
  violating plan; repair after a moved event; gate outcomes for every row of § 5.6, including that
  a task done, a length recorded and a note are **repairs** and only an added ref or a ≥ 10 score
  move requests a reshuffle (R1-3); the plan file contains no task field (only digests and scores);
  a midnight-crossing day — `day_starts: "04:00"`, bed 01:30, now 00:45 — keeps its post-midnight
  blocks through V5 (R1-7); location evidence fires on an arrival inside the window and not on one
  outside it, and never states a duration (R1-4); a user turn with a stale snapshot makes **zero
  CalDAV calls**, and a turn that wrote the calendar re-fetches inside the 3 s box (R1-8); travel
  cache hit/miss/cap; tomorrow draft; rhythm threshold; pruning; the flock under two processes; a
  reshuffle runs on a worker thread and a hung one is abandoned at 180 s with the code plan intact.
- Reshuffle runner: valid JSON, invalid JSON, invented ref, overlap, spend refusal (no state
  written), nested JSON.
- Pipeline: the plan block present in **both** twins; module injected only when present; filter
  run over the module's example sentences; nudge mode skips the Coordinator, `[HOLD]` produces no
  record, a spoken nudge produces one proactive record; **a due-item nudge between two scheduled
  runs leaves `scheduled_runs.last` unchanged, and `morning_brief`/`evening_close` never receive the
  quiet directive** (R1-2).
- Scheduler (Stage B): a nudge due at 07:23 with a 07:30 brief is not woken, is marked `carried`,
  and appears in the brief's DUE NOW (R1-6); `near_fixed_session` gives the same answers as the old
  scan for every existing `test_scheduler_gates.py` case.
- Server: nudge mode holds and speaks; `message` carries `proactive`; `/plan/today` honours the
  flag; `/settings/location` shapes.
- Client: the four location-default cases (JS harness, real extracted code).
- Existing suites stay green: `tests/test_task_ledger*.py`, `test_scheduler_gates.py`,
  `test_action_provenance.py`, `scripts/check_scheduler_functions.py`, `scripts/check_agent_tools.py`,
  `scripts/qa_sweep.sh`.

### 11.2 Stage A acceptance (Mike, a few days of ordinary use)

The Plan section matches his real day: meetings in place, travel before located ones, meals where
there is room, tasks ordered sensibly, nothing invented, and it follows the day as it changes
(repairs visible within a poll). Nothing about replies is measured here — the plan is not on the
reply path in Stage A; that criterion is Stage B's (§ 10, step 5).

### 11.3 Stage B smoke test (F8 — short, then live use decides)

On the VM, `METATRON_LIVE=1 python3 -m tools.day_plan --persona mike --reshuffle --dry-run` three
times against the real day: pass = validator clean each run, churn between runs ≤ 3 blocks, cost and
latency per call recorded, thinking tokens measured. Then live: the log's validator-failure,
churn, held/sent and correction columns over the first week are the evidence for keeping 3.8 Flash
or moving tier.

---

## 12. Cost

**Build.** Stage A: ~4–7M Opus 5.5 tokens on the subscription (mostly cache reads); a Fable 5.1
plan review and a diff review, ~1–1.5M together. Stage B: ~1–2M Opus, plus ~60–90 Mike-minutes
including the walkthrough. Mike-minutes for Stage A: a deploy and an APK rebuild (~20 min).

**Run (per day, at today's 3.8 Flash introductory price; ×2 if it ends — `[DB-0901-02]`).**
- Gate, repair, code fill, snapshot, suggestions: **$0** (code).
- Reshuffles: ~15k in / ~3–6k out each ≈ **$0.02–0.04**. Expected 4–8/day → **$0.10–0.30/day
  (~$3–9/month)**; the cap of 12 bounds it at ~$0.50/day before thinking is measured.
- Nudge wakes: Synth only, ~$0.01–0.03 each; 4–8/day → $0.05–0.25/day. They **replace** the fixed
  check-in, which today runs the full Coordinator + Synth pipeline every 180 minutes — so this line
  is roughly neutral or a saving.
- The plan block: ~800–1,000 tokens per Synth turn, uncached (per-turn content) ≈ $0.02/day.
- Smoke test: ~$0.10 once.

**Ancillary.** One CalDAV REPORT every ~10 min in waking hours (free; Google CalDAV). Disk only for
state (§ 4.4).

**Unseen — no existing meter reports these.**
1. **Google Routes is billed per request by Google Maps Platform and the spend guard does not see
   it.** Counted in `state.json`, logged, and **capped at 60/day**; caching keeps the real number
   well below. (No per-request price is quoted here — it was not verifiable from this machine.)
2. **Unbounded thinking on the compat path** (§ 5.7) — bounded only by the daily cap until measured.
3. Spend-guard attribution is per host/day, not per job: the planner's spend is visible only in
   `log.jsonl` and traces.

---

## 13. Models

| Work | Model | Why |
|---|---|---|
| This plan | Opus 5.5 | Mike, 2026-09-24: plan in Opus |
| Plan review, Stage A diff review | Fable 5.1 | independence — a different model reads it |
| Stage A build | Opus 5.5, by hand | judgement-heavy; Amber/Green |
| Stage B | Opus 5.5 with Mike | Red is never delegated |
| Reshuffle at runtime | Gemini 3.8 Flash | judgement over the user's history; F8's live use decides whether to move it |

---

## 14. Decisions for Mike, and risks stated so they are not discovered later

**D1 — Phone delivery (needed before nudges are relied on, not before Stage A or B).**
(a) Leave as is: nudges arrive when the app is alive, exactly like today's check-ins. (b) A native
push channel: a Firebase project, a content-free data-only ping from the VM (the message text stays
on the VM; the app fetches it), a native notification with Done / Not yet / Skipped actions that
call `/tasks/act` (the `MetatronHeadsetService` notification action is the in-repo precedent) — an
APK build and a server sender, its own stage. (c) A foreground service holding the socket open — a
permanent notification and battery cost. **Recommendation: (a) for Stage B, (b) as Stage C once a
week of plan-reading is trusted.** (b) puts a content-free ping through Google's FCM — the same
vendor that already holds the calendar, under the 08-26 reasoning.

**Taken in this plan, open to veto:**
1. The planner reads **all** calendars, read-only (§ 5.1).
2. Non-essential habits are recorded `unconfirmed`, never `missed`, once the flag is on; missable
   deadlines past their date stop showing as overdue (§ 4.1). Adherence rates do not improve by it.
3. The fixed check-in yields to the plan once `owns_checkins` is on (§ 7.3).
4. Stakes default to vital, so existing deadlines are essential (and checkable) until Synth infers
   or asks — noise falls as stakes are filled in.
5. **The quiet-check-in directive stops applying to the morning brief and the evening close** (§ 7.2,
   R1-2) — a change to two existing sessions, made because the plan's morning proposal (Q2) and
   evening one-line ask (F10) live there. The exposure exists today without this plan: one shared
   "last scheduled run" stamp means a quiet late-afternoon check-in can already make that evening's
   close read "nothing new" and open as a light check-in.

**Found while surveying, outside this plan (not filed — Mike decides):**
5. **A reply that has to be amended because a confirmation is still waiting crashes for any persona
   without a response language.** `core/orchestrator.py:7039` does `code, name = _out_lang` in the
   amended branch with no `None` check (`_out_lang` is `None` when no language is set, `:6952-6958`),
   so the turn ends in an error instead of the corrected message. A `/fix`.
6. Background model jobs (accountability judge, CRM sweep) are traced as non-proactive, so A9 counts
   each as a user session. The planner avoids it (§ 5.7); the two existing jobs could adopt the same
   kwarg.
7. A filter-suppressed scheduled turn still pushes a blank notification ("New message") —
   `fire_session` dispatches `""` (`scheduler.py:476`).

---

## 15. Not in this plan

Wearables (Mike, offline research); background location (needs "allow all the time" and a
permanent notification — the same conversation as D1); native push (D1 b); Google Calendar API /
guest management (Mark 2, settled); writing plan blocks to the calendar (Q1 rules it out).

---

## 16. Coordination

- **Ritual-pause session** (`archive/handoffs/2026-10-25-ritual-pause-and-ledger-followups-prompt.md`)
  adds a line to synthesizer.md § Tools, three grants in both routing files, and handlers in
  `register_tools()` / `core/actions.py`. Whichever lands second rebases; Stage B's drafted diffs
  are re-applied against the current files, never pasted blind.
- That handoff's undated "user-adjustable day boundary" item is **built here** (A1).
- `tools/rituals.py` is an untracked draft in the main tree belonging to that session — untouched.

---

## 17. Review rounds

### Round 1 — Fable, high effort, 2026-10-24: eight findings (3 structural, 5 local), all accepted

Report verbatim: `archive/plans/adversarial_review_day_planner_plan_2026-10-24.md`. Each was
checked against the code before it was accepted; every one held.

| # | Finding | Resolution |
|---|---|---|
| R1-1 | Stage A's new actions sit on tools Synth already holds, so Synth could write priority/stakes/goal links before any conduct exists | Schemas built by `task_schemas()`/`goal_schemas()`, new parts only behind `ledger_fields` (Stage B); flag-off schemas pinned byte-identical (§ 4.1, § 10, § 11) |
| R1-2 | A nudge's `close_scheduled_run` overwrites the one shared scheduled-run slot and demotes the next brief/close to a quiet check-in | Due-item nudges bind no kind and get no focus block; empty-day check-ins bind `companion_checkin` (today's behaviour); the quiet directive never applies to the two fixed sessions (§ 7.2, § 14.5) |
| R1-3 | A hash cannot tell the gate *what* changed; diffing needs either a task-state copy or rebuild-on-everything | Per-ref digests + placed score, classified against the live ledger; ordinary writes are repairs (§ 5.6) |
| R1-4 | The transitions log cannot measure presence duration | Evidence is presence only — an arrival in the task's zone inside the block window — and never claims a duration (§ 5.9) |
| R1-5 | The proposal path is one-off-only, keyed to email envelopes, closes as correspondence and renders as an email | Proposal rework scoped as A2b: `source`, habit occurrences, per-source keys and evidence, display by source (§ 5.9, § 10) |
| R1-6 | Function jobs get no fixed-session shield; a nudge could land minutes before the brief | `near_fixed_session` extracted (Stage B, Red) and applied by `nudge_tick`; items in the window are carried by the fixed session (§ 7.1) |
| R1-7 | Same-date waking windows break for post-midnight bedtimes — the case the day boundary exists for | Windows are datetimes anchored on the ledger day; `bed ≤ wake` rolls to the next date (§ 5.3, V5) |
| R1-8 | The Stage A latency criterion cannot fail, Stage B has none, and a lagging tick could put a CalDAV fetch inside a reply | No network on the reply path except a 3 s-boxed re-fetch after a calendar write this turn; reshuffles on a worker thread; latency criterion moved to Stage B step 5 (§ 5.1, § 7.1, § 10, § 11) |

### Verify 1 — 2026-10-24: 7 closed, R1-8 partial, three new

| # | Finding | Resolution |
|---|---|---|
| V1-N1 | Moving fetches to the Stage B tick left Stage A with no calendar producer at all | One fetch rule for both stages: a single-flight background refresh started by any stale read (in Stage A, the panel poll), a 3 s-boxed sync fetch only after a calendar write this turn, nowhere else (§ 5.1, § 9) |
| V1-N2 | Location evidence could suppress a check before A2b's proposal exists, leaving an essential task with neither | Suppression and the proposal ship together or not at all (§ 5.9) |
| V1-N3 | "Guarded by the plan lock" read as a flock held across a 20–60 s model call, stalling turn-time repair | The lock covers file I/O only; single-flight is an `inflight` marker with a generation id; the reply path takes the lock non-blocking within 200 ms (§ 4.3, § 7.1) |

### Verify 2 — 2026-10-24: R1-8 and all three Verify-1 items closed; no structural; one local

| # | Finding | Resolution |
|---|---|---|
| V2-N1 | The background refresh thread would start with no persona bound (identity is thread-local, fail-closed) and die silently, leaving Stage A calendar-less | Every spawned thread binds `persona_scope` first, through one `_spawn_bound` helper; failures logged to `log.jsonl`; the test asserts the snapshot lands, not merely that a refresh started (§ 5.1) |

### Verify 3 — 2026-10-24: V2-N1 closed; no new findings. **Review resolved — 12 findings across three rounds, all closed.**

---

## 18. Stage A, watch day 1 (2026-10-25) — what failed, and the round-2 design

*Status: **BUILT 2026-10-26** (Mike: "Run the plan past a Fable review … then proceed"; review and
verify in § 18.7, build notes in § 18.8). Owed: commit, deploy (Mike), the setup command with
Mike's baseline (Mike, guided), one watch weekday. No APK rebuild — the panel renders the new rows
as it renders the old ones. Evidence for § 18.1: the live `plan_2026-10-25.json`, `state.json`,
`log.jsonl`, the ledger and the 10-25 traces, read from the VM.*

### 18.1 What the watch found

| Mike's check | Result | Cause |
|---|---|---|
| Real events at the right times | partly | Every calendar read as the user's own. A promotion ("Happy Hour") and a family-calendar event ("Iva to vote") blocked 09:00–12:15 as his commitments. `tools/caldav.py` returns each event's `calendars` and `shared`; `_normalise` drops both |
| Leave for / home from | untested — and would have failed 10-26 | No event on 10-25 carried a place. "Lunch with Victoria" (West India Quay) matched `ignore_titles` "lunch" by prefix, became `own`, and own blocks are excluded from travel (`_skeleton` takes `kind == "event"` only) |
| Meals in the gaps | lunch dropped | 12:00–14:00 was covered by family events → a "no room for lunch" note; never asked |
| Today's tasks, sensibly | failed | `_candidates` takes the head layer's `actionable` — the two-day lead, undated one-offs, a monthly quota on an ordinary day — not `_on_todays_list`, the rule Mike set for the Today list on 10-24. Hence Schwab and the job post (due Monday), the Chase bill (monthly), the TfL check (undated) |
| Nothing duplicated or invented | pass | — |

"Not placed" also carried the second Stretching (no room once false commitments had taken the
morning), lunch, and the undated TfL task. Bed was 22:00, read from quiet hours.

**Not the planner, found on the way.** At 08:35 on 10-25 the reply said the Chase bill "is set to
surface between the 10th and 15th", and Rowan's payroll between the 1st and 5th. Nothing was
written: a monthly habit has no day-of-month field, and `update_task` has no action that changes a
habit's days — while its own reschedule error tells the model to "change its days".

**Why Mike's correction did not move the panel:** the ledger already said Monday; the planner's lead
window put the two tasks on Sunday; and in Stage A the Synthesizer cannot see the plan, so it
answered from the ledger.

### 18.2 Mike's rulings (2026-10-25 and 10-26)

1. **A dated task is *for* its date** — "these are FOR Monday, or at least for working hours".
   Never pulled earlier.
2. **Events get one of four answers** (accepted): *there*; *needs me* (a duty — childcare, a
   drop-off); *someone else's*; *noise*. Resolved most specific first — a stored answer, a
   standing rule, the calendar's role, else a question (order corrected by review F3; Mike accepted
   the four sources, the order is the review's). **Code working out duties itself — who is home,
   schools, ages — is a future Family-mode feature**: deferred, not rejected, and not built here.
3. **D1:** every calendar defaults to the user's; a calendar that appears later is asked about
   before the plan uses it — its events are not planned until it has a role (review F5).
4. **Health outranks noise** — "the second stretching should likely fit … Happy Hour is just a sales
   promotion. This is the judgment line."
5. A social event over a mealtime (the Lottie playdate) is **asked about as the meal**.
6. **Baselines are per-user variables over universal defaults, and dynamic.** No assumed
   weekday/weekend split; no single "working hours" — strong or preferred hours per kind of
   activity: admin, busy work, focus, creativity, entertainment, family time and the like.
7. 1am was anomalous: plan from baselines, not from last night.
8. **D2:** set Mike's baseline now (not in Stage B). **D3:** the monthly window now.
9. **Built for every user, not for Mike** (2026-10-26: "Confirm we are building to accommodate
   answers to these questions from other users"). Nothing in code names Mike's hours, calendars,
   people or rules: the structures and their defaults are universal (config), and his answers are
   one persona's data. Any user's answers to the same questions fit the same sections — through
   the setup command now, and through the first interview and `set_day_shape` in Stage B.
10. **What may share family time** (Mike, 2026-10-26, stated "as a rule"): "light household and
    personal tasks that are not computer oriented can happen with the kids. Anything that requires
    electronic devices or heavy concentration are out. Errands can usually be done with the kids."
    Stretching may happen in family time.

### 18.3 The variable model (replaces § 4.2's per-user field list)

Every entry is scoped to a set of days — any of mon…sun, or `all` — never a weekday/weekend pair.
Universal defaults live in `config/modules/day_shape.yaml` (design layer, every user); the user's
entries in `data/personas/{p}/day_shape.yaml` override them section by section.

| Section | Entry | Universal default |
|---|---|---|
| `day` | `{days, wake, bed}` | 07:00 / 23:00 (quiet hours until stated, as now) |
| `windows` | `{activity, days, from, to, strength, allows?, condition?}` — `protected`: only meals, that activity and what `allows` matches, unless the user notes otherwise for a day; `strong`: that activity goes only here; `preferred`: tried first. `condition` is the user's words for when the window holds ("when I'm free from childcare") — a block placed in it shows the condition as a question on its row (review F8) | none |
| `routines` | `{what, days, from, to, place?, covers?}` — a standing block on no calendar. A place gets travel both ways; `covers: lunch` stands in for the meal. Only an event triaged *there*, or a *needs_me* duty, overlapping it replaces it that day — context, noise and "?" rows never do (review F7) | none |
| `meals` | `{name, days, at, latest?, minutes, when?}` — a target, how late it may slide, and a condition for a conditional meal | as now: breakfast within 90 min of waking, lunch 12:00–14:00, dinner 18:00–20:30 |
| `calendars` | `{collection id: {name, role: mine \| family \| feed}}` — keyed by the calendar's collection id, never its display name, which can change or fall back to "Main calendar" when discovery fails (verify N1); the name is a label. `mine` → *there*; `family` → a question unless an answer or rule settles it; `feed` → *noise*. **The writable calendar (`calendar_url`) is always `mine`**, roster or not. An event on several calendars takes its most-owned role (any `mine` copy makes it the user's) | before setup (no roster): every calendar `mine`. After setup: a calendar not in the roster is *new* — its events are not planned, one note names it and asks (D1, review F5) — **but only on a poll where discovery succeeded**; a failed discovery classes nothing new (N1) |
| `day_overrides` | `{date, what: window condition \| family time \| …, holds: yes \| no, evidence}` — one day's exception to a standing entry ("I'm free of childcare today", "working tonight"). Expires with its day (verify F8) | none. **Read in round 2; written in Stage B** by `set_day_shape` with a `date` — round 2 shows the condition as a question and nothing can answer it yet |
| `event_rules` | `{match: [words], answer: there \| needs_me \| someone_else \| noise, duty?, load?: full \| partial}` | none |
| `children_home` | windows when anyone in the user's care is home and awake; a childcare duty blocks only inside them | none — a childcare duty blocks the whole event |
| `travel_mode`, `location_sharing` | unchanged | transit; asked at the interview |

**Activities** are a universal vocabulary in config, extensible: `focus`, `creative`, `admin`
(finance, key business decisions), `busy` (shallow work), `errands`, `household`, `personal`,
`health`, `family`, `social`, `entertainment`, `rest`. **Every task has one**: stated on the task — a
new ledger field `activity`, exposed with the other planner fields behind `ledger_fields` — else
derived from its domain by a config table (finance → admin, work → focus, logistics → admin,
physical_health → health, none → personal).

**Each activity carries two attributes in config — `device` (needs a screen) and `concentration`
(`heavy` | `light`)** — and a `protected` window admits, besides meals and its own activity, the
activities its `allows` filter matches. The universal default for a `family` window is Mike's rule
(ruling 10): `allows: {device: false, concentration: light}` — so `household`, `personal`, `health`
and `errands` may share it; `focus`, `creative`, `admin` and `busy` may not. A user may override the
filter per window, or a task may override its attributes (a phone call that needs concentration).
So "protected" means *kept clear of what does not fit there*, not *empty*.

**Per-event answers** live in `data/personas/{p}/day_plan/event_answers.json` as two maps
(review F1 — every occurrence of a series shares its uid): `series: {uid: answer}` and
`occurrences: {"uid@start": answer}`, each answer `{answer, duty, load, at, evidence}`. Lookup reads
the occurrence first, then the series. Written in Stage B by a new tool, `answer_event`, on the
user's word only. Questions are asked in one line at the morning brief (today) or the evening close
(tomorrow), never as a separate nudge. When three answers about distinct events agree, the plan
block offers a standing rule as a proposal — never applied on inference (Q4/F7).

**An unanswered family event holds its time for family-compatible activities only** (review F6):
it is shown as a "?" row and treated, for placement, as a protected window with the family `allows`
filter — so if it turns out to be childcare, no screen work or heavy concentration was planned over
it, and if not, little was lost. Neither false commitments (10-25) nor false free time.

### 18.4 Mike's baseline (interview, 2026-10-26 — written on the VM by the setup command)

- **day**: all days — wake 07:00, bed 23:00.
- **windows**: `family` protected, all days, 07:00–10:00 and 17:30–20:30 ("unless otherwise noted"),
  with the universal family filter (stretching, chores, errands fit; screens and heavy work do not);
  `focus`, `creative`, `admin` preferred all days 10:00–15:00 and strong 10:00–17:30 ("some days
  extend to late afternoon"). On sat and sun the same two windows carry `condition: "when I'm free
  from childcare"` (review F8), so weekend work rows read as a question until Stage B's weekend
  morning brief settles it.
- **routine**: lunch with Iva, mon–fri 12:00–13:00, Canary Wharf, covers lunch, travel both ways
  ("right now").
- **meals**: breakfast 08:30; lunch 12:00, may slide to 15:00 on high-productivity days; a
  meal-level snack 16:00–17:00 when lunch ended by 13:30; dinner 19:00.
- **calendars**: Main → mine; Shared with Mike → family (Iva and Mike are its only authors). Any
  other calendar the account sees is listed by the setup command for a role.
- **event_rules**: GMAT, GRE → there; admissions → needs_me, childcare; Gan → there ("me with both
  boys"). The rest "as cases arise".
- **children_home**: childcare applies "only if the boys aren't at their respective schools and not
  asleep" — **the windows are an open question to Mike**; until answered, a childcare duty blocks
  the whole event.
- **Calibration, 10-25**: Iva voting → needs_me, childcare; Lottie playdate → there, partial (an
  hour of work got done during it); a GMAT session → there. **These are the test fixture's expected
  answers, not stored data** (review F6) — round 2 has no answer writer; Stage B's `answer_event`
  is the first.

### 18.5 Round-2 work — Stage A, Amber and Green; nothing Red; no APK rebuild

| # | Work | Files |
|---|---|---|
| R2-1 | The variable model, its validator and universal defaults. No persona has a `day_shape.yaml` yet, so the old flat fields are read as entries rather than migrated | `tools/day_shape.py`, `config/modules/day_shape.yaml` |
| R2-2 | Setup command: lists every calendar the account sees with its role, then applies a baseline file entry by entry through the same validator, evidence "stated by the user in setup" | `tools/day_shape.py` (`python3 -m tools.day_shape`) |
| R2-3 | Candidates = `_on_todays_list`: dated tasks on their date; undated never; weekly and monthly quotas on a planned day or their last chance | `tools/day_plan.py` |
| R2-4 | Placement by activity: a protected window admits only what its `allows` filter matches (an essential item that does not match may still take one when nothing else fits — displaced and said aloud, § 5.4); strong = only there; preferred first. Activity attributes and the domain → activity table in config | `tools/day_plan.py`, `config/modules/day_plan.yaml`, `config/modules/day_shape.yaml` |
| R2-5 | Event triage — stored answer → rule → calendar role → question (review F3). *there* blocks and gets travel; *needs_me* places a duty block (clipped to `children_home` when known); *partial* shows without closing the time to tasks; *someone_else* is one context line; *noise* is hidden; an unanswered family event is a "?" row holding its time for family-compatible tasks (F6); a calendar new since setup is not planned, and one note asks about it (F5) — only when discovery succeeded (N1). The snapshot keeps each event's calendar ids and names; `tools/caldav.py` adds `calendar_ids` beside `calendars` on merged events (additive — no existing reader changes) | `tools/day_plan.py`, `tools/caldav.py` |
| R2-6 | Routines as fixed blocks with travel both ways; replaced only by a *there* event or a *needs_me* duty (F7) | `tools/day_plan.py` |
| R2-7 | An event with a place, or titled "with <someone>", is an appointment (travel) that also covers an overlapping meal; `ignore_titles` makes an own block on an exact title only | `tools/day_plan.py` |
| R2-8 | Meals: target time, slide to `latest`, the conditional snack; a meal with no gap, or under a social event, becomes an ask row at its time — never a "not placed" note | `tools/day_plan.py` |
| R2-9 | "Not placed" holds only essential items due today or overdue that did not fit | `tools/day_plan.py` |
| R2-10 | D3: monthly habits take day-of-month `on_days` (10–15 → planned the 10th to the 15th, due by the 15th). **Past its last day undone, a windowed habit is `overdue`** — actionable and on the Today list until the period ends — and counts as a deadline for essentiality (stakes, default vital), so "Not placed" carries it (review F4). `update_task(action="set_days")` for any habit, **behind `ledger_fields` with the other planner fields** — the flag-off pin stays byte-identical — and refused on a turn with no words from the user, as `set_day_shape` is (review F9; the "exposed now" exception is withdrawn). The reschedule error stops naming an action that does not exist while the flag is off. Chase and Rowan's windows are recorded once Stage B turns the flag on; until then R2-3 keeps the Chase bill off October's plan (its first period is partial) | `tools/obligations.py`, tests |
| R2-11 | Stage B drafts revised: `set_day_shape` takes a section and an entry, and a `date` for a one-day override (F8); `answer_event` (new, a Red grant); conduct for the one-line ask, the weekend-condition question and rule proposals; `activity` and `set_days` behind `ledger_fields`; `day_planner.md` and its payload carry each protected window's `allows` filter and the "?" holds (F2) | `archive/handoffs/2026-10-24-day-planner-stage-b-prompt.md` |
| R2-13 | **The validator, in the same change** (review F2): V2 becomes "every timed event is accounted for at its time in its triaged form — a block (*there*, own, duty), a context row, a "?" row, or recorded as hidden noise"; V6 becomes "a task in a protected window or a "?" hold matches its `allows` filter, or is essential and marked displaced". The gate's "a repair displaced an essential item" reads the same flag | `tools/day_plan.py`, tests |
| R2-12 | Tests: a synthetic fixture with 10-25's shape — overlapping family events, a promotion, a weekday routine, a located "Lunch with …", a twice-daily habit, tasks due tomorrow, an undated one, a monthly bill — to an expected plan; one check per R2 rule; existing suites green | `tests/` |

**Acceptance for round 2** (replaces § 11.2's first pass): Mike runs setup, then watches one
ordinary weekday — a located appointment and the lunch routine with travel, family time clear of
screens and heavy work, admin in the daytime, nothing that is not today's, and every unknown family
event shown as a question with its time held from screen work (not a block, not free time — F6).

### 18.6 Cost

- **Build**: ~3–5M Opus 5.5 tokens on the subscription. A Fable 5.1 review of this section first,
  ~0.5M: the variable model is what the interview, the Synthesizer's tool and every future user's
  baseline rest on, and a wrong shape is a data migration later.
- **Run**: $0 — code only. Stage B's questions ride the brief and close that already run.
- **Ancillary / unseen**: the weekday lunch routine adds two Google Routes lookups a day (cached by
  hour, inside the 60-a-day cap). The spend guard does not see Routes (§ 12).
- **Mike**: a deploy, setup (~5 min), one watch day.

### 18.7 Review — Fable, medium, 2026-10-26: nine findings (4 structural, 5 local), all accepted

Report verbatim: `archive/plans/adversarial_review_day_planner_plan_2026-10-26.md`. F2's two code
claims were checked by hand (`validate` V6 `:920-923`, V2 `:896-905`) before acceptance.

| # | Finding | Resolution |
|---|---|---|
| F1 | One uid slot cannot hold a this-occurrence answer beside a series answer | Two maps, `series` and `occurrences` (`uid@start`), occurrence read first (§ 18.3) |
| F2 | The validator rejects stretching in family time, hidden noise and "?" rows | R2-13: V2 and V6 rewritten in the same change; Stage B contract carries the filters (R2-11) |
| F3 | With role first, no rule can fire on the user's own calendar | Most specific first: answer → rule → role → question; each role's answer stated (§ 18.2, § 18.3) |
| F4 | A windowed monthly habit has no overdue state and vanishes after its last day | Overdue past the last window day, through the period end; counts as a deadline for essentiality (R2-10) |
| F5 | A new calendar's events were used before the user was asked, against D1 | Not planned until it has a role; one note asks (§ 18.3, R2-5) |
| F6 | Unanswered family events became false free time; calibration answers had no home | "?" rows hold their time for family-compatible tasks; calibration is fixture data (§ 18.3, § 18.4, acceptance) |
| F7 | Any overlapping event could displace the lunch routine | Only *there* events and *needs_me* duties replace a routine (R2-6) |
| F8 | Weekend work windows ignored "when I'm free from childcare" | Windows take a `condition`, shown as a question on the rows placed in them (§ 18.3, § 18.4) |
| F9 | Exposing `set_days` now broke the R1-1 pin and ungated a model write | Behind `ledger_fields`, user-turn gated; exception withdrawn (R2-10) |

**Verify, 2026-10-26: F1–F7 and F9 CLOSED with code anchors; F8 PARTIAL; one new local, N1; no new
structural.** Appended verbatim to the review file.

| # | Finding | Resolution |
|---|---|---|
| F8 (partial) | The weekend condition became a question no tool could record the answer to | `day_overrides` — one day's exception, read by round 2, written in Stage B by `set_day_shape` with a `date` (§ 18.3, R2-11) |
| N1 | A roster keyed by display name turns a discovery failure or a rename into a blank day | Keyed by collection id; the writable calendar is always `mine`; nothing is classed new on a poll whose discovery failed (§ 18.3, R2-5) |

Not sent for a second verify: both resolutions are local and stated against the code the reviewer
anchored them to. The build's tests carry them (a discovery-failure poll; a renamed calendar; an
override on a conditional window).

### 18.8 Build notes — 2026-10-26 (Opus 5.5)

**Tests:** `tests/test_day_plan_round2.py`, 24 checks (every R2 item, F1–F9, N1, the validator's
V2/V6, setup, the writers); the existing suites unchanged and green — engine 36, ledger 15, wiring
19 (three example sentences added to the filter check), task ledger 62, provenance 10, scheduler
gates 23; `qa_sweep` 12/12. Flag-off schemas still byte-identical.

**Replayed against real data** (the VM's 10-25 and 10-26 calendar and the live ledger, in a scratch
directory, with Mike's baseline): 10-25 shows no Monday tasks, no Chase bill, no TfL check, both
stretches in family time, the three shared events as questions, lunch asked against the playdate;
10-26 places Schwab and the job post in the daytime admin window, travel to and from Lunch with
Victoria (which replaces the Iva lunch routine that day), and asks about dinner under Karate.

**Changed by the replay, beyond the reviewed plan — stated so they are not read as reviewed:**
1. **`solo` — a third activity attribute, and `exercise`.** "Gym workout session" (domain
   physical_health → light, screen-free) was planned into family time at 07:00. The family filter
   now also requires `solo: false`; `activity_words` in `config/modules/day_shape.yaml` (gym,
   workout, swim …) mark exercise from the title when the task states no activity. A net, not
   the definition — a stated `activity` wins.
2. A meal under an unanswered event is asked against the event it sits most inside (the playdate,
   not the vote ending 15 minutes into lunch); a meal under a hard event is worded for any event
   ("covers it — eat during it, or when?"), since a GMAT session is not a lunch.
3. CalDAV TEXT escaping is undone in locations ("The Ledger Building\, West India Quay").
4. **`answer_event` is built and tested but not registered** — `register_tools()` is shared with
   the ritual-pause session, so registration lands in Stage B with the grant (handoff § B).
5. The ledger's `activity` field (§ 18.3) is in: `open_task(activity=)`, `set_activity`, both
   behind `ledger_fields`.

**Seen, not changed:** "Take out the trash" is a one-hour event Metatron wrote on its own calendar;
it holds 19:00–20:00 and turns dinner into a question. Not a planner defect — the event is an
hour long. Raised with Mike.
