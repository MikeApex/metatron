# Synth says now and next, not the day — plan, 2026-10-30

Model: Opus 5.5 builds; Fable 5.1 reviews the plan and the diff (Mike, 2026-10-30).

## 1. The need

Mike (2026-10-30): *"Metatron's responsibility is to ensure you keep on schedule and REMOVE the
need to be aware of the schedule. Synth should be telling the user what to do right now, or the
single item that is coming next."* The Today panel shows the whole day; the voice should not.

**Evidence (mike, 10-28 → 10-30, conversations on the VM):**
- Morning brief 10-28 001 and 10-30 001: the whole day, item by item (10 items on 10-30).
- Evening close 10-28 015: *"Looking at tomorrow in full…"*, four items with their paperwork.
- User turns 10-28 006/008/009/010 and 10-29 007: a 3–4 item tail ("Right now X, followed by Y,
  then Z at 11:00") on messages about something else.
- Riders on most replies: *"I have estimated 30 minutes for X — let me know"* (6× in two days);
  *"eats into family time"* repeated for the same item.
- Day-plan nudges since 10-29 are close to right — one item — but add "Up next is …".

**Cause.** `synthesizer_day_plan.md` has said *"never recite it"* and *"the morning brief and the
evening close are not a rundown"* since 10-27 (`9f2eeac`); it did not hold. Two things in code
outweigh it:
1. `render_block()` (`tools/day_plan.py:1835`) hands Synth the whole day on every turn — Earlier
   (8), Now, Next (2), **every** Later block, and at the evening close a 10-item tomorrow draft.
   That was Mike's ruling R2 (10-24, `day_planner_plan_2026-10-24.md` § 0): *"Synth should
   probably get the whole day."*
2. `tools/horizon.py review_block()` at the evening close: *"Go through all of these with the
   user"* — Mike's ruling of 2026-09-05, *"Daily wrap up should run through all of tomorrow's
   events whether previously stated or not."*

## 2. Mike's rulings, 2026-10-30 (this session)

| # | Ruling |
|---|---|
| S1 | **Morning brief:** now and next, plus anything important. Some days have nothing important. Synth's/Planner's discretion. |
| S2 | **Evening close:** tonight, first thing tomorrow, and anything over the same "important" threshold. **Supersedes the 2026-09-05 "run through all of tomorrow" ruling.** |
| S3 | **User turns:** mention the schedule only when there is something new to do, or to announce free time — *"I'm home → great. Your next meeting is two hours from now. Water the plants now and then have some personal time."* |
| S4 | **Fix in code.** Try it; revert if it does not work. |
| S5 | **Free time:** tasks suggested as appropriate. A task due in two weeks versus rest now is weighed by the user's preferences. Longer term, as Metatron learns the user, free time is itself scheduled and protected (§ 7, not this build). |
| S6 | Build in this session. Fable reviews the plan and reconciles before the build. |

**R2 is amended, not withdrawn:** nudges remain Synth's decision and Synth remains primed to run
the day. What changes is that Synth no longer *holds* the whole day; it gets what it should say,
and fetches the rest when the user asks.

## 3. The change

> **Amended by § 8 (Fable review, reconciled 2026-10-30).** Where § 8 and this section differ,
> § 8 governs.

### 3.1 `render_block()` — Synth sees only what it should say (`tools/day_plan.py`, Amber)

Replace the Earlier / Now / Next(2) / Later timeline with:

- **Now (HH:MM):** the current block, with its status — unchanged.
- **Next:** **one** block, not two.
- **Free:** when the gap from now (or the end of Now) to the next *fixed* block — event, own, duty,
  hold, travel, routine — is ≥ `free_min_minutes` (config, default 45): `Free until HH:MM (next:
  <fixed item>)`, then what the plan already placed inside the gap (≤ 2 tasks, with length and
  due date), or "nothing placed — the user's own time". **Code does not choose a task here; the
  planner's placement already weighed it (S5).** Synth decides whether to offer it or to call the
  time free.
- **Important:** candidates for S1/S2, flagged by code, for Synth to pick from (often none). For the
  rest of today:
  - calendar events the user attends (`event`/`own`/`duty`) **other than Now and Next**;
  - deadlines that are vital and due today or tomorrow;
  - a block that `takes the user's own time`.
  Habits, meals, routines, travel, chores and "someone else's" are never Important.
- **Asks** (unchanged content, collected from the whole day rather than from the visible
  timeline): `?` holds; `no word yet` essentials; conditional tasks; the meal questions; "Not placed",
  "Notes", standing-answer proposals, waking-hours, rhythm and length asks.
- **Evening close:** the unconfirmed-non-essential line stays. The 10-item `Tomorrow (draft)` line
  becomes **Tonight** (what is left before bed), **First thing tomorrow** (the first non-meal,
  non-routine block of the draft), and **Important tomorrow** (the same rule, on the draft).
- **Suggested** and **DUE NOW** stay as they are.

The header line changes from "say what to do now and next" to: *"What to do now, and the one thing
after it. The user sees the whole day in the app — fetch it with `read_day_plan` only when they ask
about their schedule."*

A `_listed()`-equivalent full render is kept as `render_full()`, for the tool (3.3).

### 3.2 Evening close — `review_block()` stops re-reading tomorrow (`tools/horizon.py`, Amber)

Removed from `_horizon_block()` at `evening_close` (S2 supersedes 09-05). Tomorrow's undelivered
findings still arrive once through `context_block()`, and anything important tomorrow arrives
through 3.1. `week_block()` (the Monday review, Mike 09-05) is untouched: it is the counterweight
to `_due_now()` holding anything **past** tomorrow, which this change does not affect. Per the
standing rule (remove, don't keep as a fallback), `review_block` is deleted, not left unwired, and
its tests are reworked to assert the evening close no longer carries it.

### 3.3 `read_day_plan` — the day on request (`tools/day_plan.py` Amber; grant Red)

A read-only tool returning `render_full()` for today (and `day: "tomorrow"` → the draft). It is
registered beside `request_replan` and `answer_event` in `core/orchestrator.py` (~1444, 1606).
**Granted to `synthesizer` in both `config/modules/routing_cloud.yaml` and `routing.yaml` (Red —
Mike approves the edit).** `scripts/check_agent_tools.py` must stay clean.

### 3.4 `synthesizer_day_plan.md` — cut to match (`config/modules/`, Amber)

- "Raise what is salient…" → one sentence: the block already holds only what is worth saying, and
  Important is a candidate list — say none of it when none of it matters.
- "The morning brief proposes the day… two or three things" → "now, next, and whatever in Important
  matters today; invite pushback."
- "The evening close… For tomorrow, raise what is salient" → "tonight, first thing tomorrow, and
  whatever in Important tomorrow matters."
- **New, short:** on the user's own turn, speak about the schedule only when their message changes
  what is next, or frees time — then Free is the line to use. Otherwise nothing about the schedule.
- **New, short:** a task length you estimated is recorded with `set_minutes` and not announced.
  (The ask-once-for-length rule stays.) "Takes the user's own time" is said once per task per day.
- "When you are woken for something due": one item; no "up next".

Net: shorter than today's 1,444 words.

## 4. Not changed

- The planner, its scoring, nudge and check timing, reshuffle.
- `context_block()` (findings not yet raised), `week_block()`.
- The scheduled prompts (`config/templates/scheduler.yaml`; the live copies are VM-owned persona
  config and are Denied here). The morning prompt asks for the most time-sensitive thing, which is
  compatible.
- `synthesizer.md` itself — see § 6.

## 5. Tests

Extend `tests/test_day_plan_engine.py` / `test_day_plan_round2.py`; rework the
`test_horizon_ledger.py` review-block checks:

1. Ordinary turn: block has Now, exactly one Next, **no "Later:" and no "Earlier:"**; a `?` hold
   at 16:00 still appears under Asks.
2. Free: a 2-hour gap before a 14:00 event with one 15-min task placed → `Free until 14:00`, the
   task named; with nothing placed → "the user's own time"; a 20-min gap → no Free line.
3. Important: a vital deadline due today and a later calendar event appear; a habit, a meal and a
   routine do not; an empty day → no Important line.
4. Evening close: Tonight, First thing tomorrow and Important tomorrow present; no 10-item draft;
   `_horizon_block(..., "evening_close")` carries no TOMORROW review.
5. `read_day_plan` returns the full day, including Earlier and Later.
6. Size: the ordinary-turn block ≤ 1,200 chars on the existing fixture (was ≤ 4,000).
7. Existing suites green: `test_day_plan_*`, `test_horizon_ledger`, `test_not_connected_integrations`,
   `test_synth_module_injection`, `scripts/check_agent_tools.py`, `qa_sweep`.

**Live check (Mike, after deploy):** the next morning brief and evening close, and one "I'm home"
message. Pass: no rundown; at most now + next + one or two important items; "I'm home" either says
nothing about the schedule or gives the free window.

## 6. Cost, revert, and what it unlocks

- **Build:** one Opus session, ~2–3 h; Fable plan review + diff review.
- **Run:** the plan block drops from ~1,000 to ~250 tokens on every Synth turn — a small saving.
  `read_day_plan` costs one extra model round on schedule questions only. The block is per-turn
  dynamic context, outside the cached system prompt (`core/orchestrator.py:6130`), so the Vertex
  4,096-token cache floor is not touched — the build confirms this rather than assumes it.
- **Ancillary / unseen:** none; nothing new persists.
- **Revert:** a single commit; `git revert` restores R2 behaviour.
- **What it unlocks (Mike asked):** if a week of live use holds, the conduct prose in
  `synthesizer_day_plan.md` that exists to stop recitation can go further — the "Reading the plan"
  legend shrinks to what the new block still shows — and the evening-review language in
  `synthesizer_scheduled_sessions.md` can be checked for the same. The lesson generalises: **a rule
  that tells a model not to use data it is given is weaker than not giving it the data**, which is
  the code-dominant direction (`archive/plans/code_dominant_rebuild_notes.md`).

## 7. Deferred (S5, not this build)

**Lead follow-up (Mike, 2026-10-30, on F3): the planner anticipates prerequisites.** *"Flagging
the red book as something to prepare in the evening for a morning event is important, and planner
(working with code/Logistics/whomever) needs to anticipate when prerequisites need to be done."*
This build only **surfaces** a filed prerequisite (evening close, morning brief). The follow-up has
the planner **place** the prep as a task — "pack Benny's Red Book, 20:30" — the evening before,
from a finding's `precursor_by`/`detail`, with Logistics identifying prerequisites the finding does
not carry. **Folded into this build as its final stage (Mike, 2026-10-30, "at the end")** —
designed after §§ 3/8 are built and green, and reviewed by Fable before it is built.

Scheduled and protected free time, learned from the user, with the planner weighing a far-off
task against rest by the user's preference. Today the planner already keeps `protected` windows
from the day shape; learning them is new planner work. **Not filed** — Mike decides whether it
becomes a backlog item.

## 8. Fable review and reconciliation (2026-10-30)

Fable 5.1 adversarial review of §§ 1–7: three structural and five local findings, **all eight
verified against the code and accepted.** Each amendment below replaces the § 3 text it names.

| # | Finding (what Mike would have seen) | Verified at | Amendment |
|---|---|---|---|
| F1 | **The evening close would still review all of tomorrow**: the scheduled-session conduct says *"Tomorrow, in full — go through everything tomorrow holds"*, and the morning says *"Identify the 2–3 highest-leverage items… Propose a sequence"*, and the new tool would let it fetch exactly that | `config/modules/synthesizer_scheduled_sessions.md` § Morning brief 3, § Evening close 3 | **In scope.** Morning phase 3 → "Direct the day: now, next, and whatever in Important matters; invite pushback." Evening phase 3 → "Tomorrow: tonight, first thing tomorrow, and whatever in Important tomorrow matters" — **S2 supersedes the 09-05 "in full" ruling, stated in the file.** `read_day_plan` is for the user's question, never for a scheduled session's own review. |
| F2 | **"Important" was the Later list renamed** — every attended event re-handed with "pick from these", so on a four-meeting day the brief recites again | `tools/day_plan.py` `_skeleton` (every attended event → `event`/`own`) | **Important is narrow and capped at 2, ranked by code.** It includes only: (a) a task with `stakes == "vital"` (set by `set_stakes`, never inferred from an unset field) due today/tomorrow; (b) a block that `takes the user's own time`; (c) a horizon finding for the day that needs something done first (`precursor_by` today/tomorrow, or a `deadline` finding, or a `detail` line); (d) an essential that is `no word yet`. **Calendar events are never Important by being on the calendar** — they reach the user as Next or as a nudge at their time. Empty is the normal case. |
| F3 | **Tomorrow's paperwork would vanish from the evening close** — the 10-28 "Red Book, birth certificate…" lines are horizon findings, which the day-plan draft never holds, and `review_block` was the only re-read past the 2-offer cap | `tools/horizon.py` `_MAX_OFFERS = 2`, `_undelivered`, `_digest` | **`review_block` is narrowed, not deleted**: tomorrow's findings that need something done first (deadline, precursor, or `detail`), delivered or not, read-only as today. Its header changes from "go through all of these" to "raise any that need something done tonight or first thing; the rest the user already has." It feeds the evening close's Important tomorrow. Tests in `test_horizon_ledger.py` are reworked to assert a plain tomorrow event is no longer re-read and a precursor/detail one is. |
| F4 | **"Vital deadline" could not be computed from the plan**, and if computed from candidates it fires on every dated one-off | `_fill` persists no `vital`/`due`/`stakes`; `_candidates` `vital` is true when `stakes` is unset | `_fill` adds `stakes` and `due` to task blocks (additive; a plan built before the deploy lacks them → treated as not vital until the next rebuild, which happens within the snapshot cycle). Important tests `stakes == "vital"` only. |
| F5 | **"Free until 18:30" across lunch and family time** — the plan's fixed set omitted meals and protected windows and counted partial events | `_is_hard`, `_is_protected`, `_listed` | **Free ends at the first block after now that is `_is_hard` and not a task or break, or `_is_protected`**, read from `plan["blocks"]` (not `_listed`, which strips protected). Partial events are not boundaries. Tests cover lunch and a protected window as boundaries. |
| F6 | **"What's on tomorrow?" at 10:00 would answer "nothing"** — the draft exists only after the evening window | `tomorrow_draft` returns None without `build`; never builds in a reply | `read_day_plan(day="tomorrow")` never builds. With no draft it returns, explicitly, *"Tomorrow is not planned yet (it is drafted after HH:MM). Calendar for tomorrow: …"* from the snapshot (`_events_for`), or *"not read — do not describe tomorrow as free"* when there is none. |
| F7 | **The single "Next" could be a break, someone else's event, or an unanswered hold** | `render_block` takes any `_listed` kind | Next skips `break`, `context`, `protected`, `wind_down` and `hold` (holds go to Asks). First thing tomorrow additionally skips `meal` and `routine`. Tests for each. |
| F8 | **The tool would be granted but undocumented** — the checker's class 3 reads `config/agents/` only, and the model would learn of it only on turns carrying a plan | `scripts/check_agent_tools.py` classes 2–3; `config/agents/synthesizer.md` tool list | **`config/agents/synthesizer.md` gains one tool line for `read_day_plan` (Red — Mike approves the edit when prompted).** Grants in both routing files (Red). `check_agent_tools.py` must report nothing new. |

**Unchanged by the review:** the cache-floor claim (block is per-turn dynamic context), the
revert path, the cost.

**Red edits this build will prompt for:** `config/agents/synthesizer.md` (one tool line),
`config/modules/routing_cloud.yaml` and `routing.yaml` (one grant each). Red work is done in this
session, not delegated.

## 9. Stage 2 — the planner places the prep (Mike, 2026-10-30: "fold … into this build", "at the end")

**Status of stage 1 (§§ 3, 8): built, all eight affected suites green, `qa_sweep` 12/12.**

**What the user sees.** A finding that needs something done first becomes a task on the plan, at
the right time, without anyone asking: the evening before Benny's 09:30 settling-in session, the
plan holds *"Gather paperwork, Red Book, birth certificate, passport, and proof of address"* at a
time that fits, the Synthesizer nudges it ("Time to pack Benny's Red Book for tomorrow"), and the
check asks whether it happened. It shows in the Today panel with Done / Not yet / Skipped.

**Where the prerequisite comes from.** Logistics already files it: `record_horizon_item` takes
`precursor` and `precursor_by` (measured on mike's ledger 2026-10-30 — the 10-29 nursery finding
carries *"gather paperwork, Red Book…"*, by 2026-10-29). Code converts; no model is called.

**The rule (code, `tools/horizon.py open_prep_tasks(persona)`):**
1. For each finding with a real `precursor` (not empty/"none"), event date `E` (may be absent),
   `precursor_by` `B` (may be absent):
   - `due = B` when `B` is before `E` (a form posted Monday for a deadline Friday);
   - otherwise **the evening before**: `due = E − 1`, `after = evening start` (`_evening_start`) —
     "by the day itself" for a dated event means ready before it starts;
   - `due` never earlier than today; a finding whose `E` has passed is skipped.
2. Only when `due ≤ today + 2` — the near window, so the ledger is not filled months ahead (the
   weekly review and `context_block` still raise far precursors as findings).
3. `open_task(what=<precursor, first letter capitalised>, kind="deadline", due, after,
   domain="logistics", minutes=15, minutes_source="estimated", note="Before <title> on <E>",
   source_id="horizon-prep:<item_key>")`. A deadline with unset stakes is essential
   (`is_essential`), so it gets a nudge and one check — the Red Book should.
4. **Idempotent and deduplicated:** `source_id` stops a second open from the same finding
   (`_source_duplicate`, which also covers a recently closed one); before opening, the prep text is
   consulted against open tasks (`_ledger_hit`), so the three near-duplicate nursery findings on
   mike's ledger open one task, not three. The row records `prep_task_id`.
5. `prep_items` skips a row that has `prep_task_id` — the plan carries it now, and Important would
   repeat it.

**Trigger:** `refresh_tick` (every 5 minutes, code only), after the snapshot and before
`current()`, so a new task is placed in the same tick. Behind a flag `prep_tasks` in
`config/modules/day_plan.yaml` — off restores stage 1 exactly.

**Tests:** the evening-before rule; `B < E`; the near window; idempotence across two ticks; three
near-duplicate findings → one task; "none" → no task; flag off → nothing; `prep_items` skips a
converted row; the opened task is placed by the planner in the evening.

**Cost.** Zero model tokens; one ledger write per prerequisite. **Unseen cost:** tasks the user did
not ask for appear on their list — bounded by the near window, dismissible with a reason, and each
traces to a finding Logistics filed. **Revert:** flag off.

**Not in this stage:** Logistics inferring prerequisites a finding does not carry (that is an agent
file change — Red — and the measured ledger shows Logistics already fills `precursor`); learning
how long prep takes (`minutes` stays estimated until the user says).

## 10. Fable review 2 — stage 1 diff and stage 2 design (2026-10-30)

**Stage 1 diff: no structural findings; three local, all verified and FIXED** (tests added;
eight suites green, `qa_sweep` 12/12):
- B1 "What's on tomorrow?" read today's events as tomorrow's — `_events_for` returns the three-day
  snapshot; now filtered to tomorrow's date.
- B2 Free time was announced in the middle of family time already under way — no Free line while
  inside a protected window, hold or wind-down.
- B3 The cap of 2 cut the Red Book first — prerequisites now rank just under a vital deadline due
  today.

**Stage 2 design: three structural, six local — the design as written is not built.**

| # | What would have gone wrong | Fix it needs |
|---|---|---|
| A1 | A finding filed the morning of a 09:30 session put the prep **tonight, after the event** | same-day branch: due today, no `after`, placed before the event |
| A2 | The scheduler would write the horizon ledger while the server writes it too; the only guard is an in-process lock → lost offer counts / re-raised findings | convert in the **server** process at filing time (`record()`), not in `refresh_tick` |
| A3 | "Flag off restores stage 1" was false: stamped rows stay suppressed, opened tasks keep nudging | flag gates the `prep_items` skip too; state plainly that opened tasks remain until dismissed |
| A4/A7 | `_ledger_hit` does not read the precursor, and `source_id` disables the ledger's near-duplicate guard → three tasks for the three nursery findings, or an unrelated nursery task suppressing the prep; siblings left unstamped repeat under Important | dedup on event date + precursor text, stamp every sibling |
| A5 | Each opened task is a reshuffle → a day_planner model call, sharing the user's 12/day cap | count it in the cost; consider placing by code only |
| A6 | "Evening" was the evening-close job's clock time, so prep collided with family time and got the "takes your own time" rider | place from the day shape (light, screen-free task in family time is allowed), no `after` pin |
| A8 | A refused open (recently closed twin) loops every 5 minutes and never places the prep | stamp the refusal |
| A9 | A moved event leaves the old prep task on the wrong night | re-filing moves the open prep task's `due` |
