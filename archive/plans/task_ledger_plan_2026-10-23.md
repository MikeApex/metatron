# Task ledger — completion recorded by code, not re-inferred by models

*Plan, 2026-10-23. Author: Opus 5.5 (Claude Code). Review: Fable 5.1 (Mike's instruction —
"have a Fable review and then proceed once you're both in agreement"). Build: this session,
by hand — Mike: "Don't worry about Build. I want to do this now, manually."*

---

## 1. The need, and what the history shows

Mike: tasks and reminders are completed, Metatron does not fully register it, and raises them
again. Measured on live VM data, 2026-09-20 → 10-23 (433 conversation records, 619 traces,
the live `obligations.yaml`, `schedules.yaml`, `context.json`):

- **16 items raised after they were done, decided or moot — ~85 stale raises.**
- By type: 7 one-off deadlines, 4 follow-ups / waiting-on-someone, 2 calendar events, 2 other,
  1 recurring habit (plant watering — **27 raises on its own**, from a schedule prompt with
  "last watered Aug 4" frozen into its text).
- By cause: in 7 the completion **was recorded** and the surfacing path did not consult it;
  in 5 duplicates contributed; in 3 completion happened outside Metatron (email) and nothing
  used the evidence; 2 were never recorded; 3 other (lapsed items that never expire, a
  waiting item given a due date as if it were Mike's job).
- **One item lives in up to six stores with no shared id** — obligation, all-day calendar
  event, context-tracker thread, Diarist log fields, horizon item, a schedule prompt. Closing
  one leaves the others alive and they re-raise or re-mint it. Chase bill: two obligations
  closed 10-15; calendar entry + tracker thread survived; Finance opened a fresh obligation the
  next evening; raised 5 more times.
- **Nothing expires.** Schwab RSVP due 09-24 (event 10-01) still open, raised 10 times;
  "Finalise Apex migration plan" due 08-31 still in every turn's context.
- **Two model inbox jobs** (`check_inbox_recurring` → Coordinator, `check_inbox_6h` → Logistics,
  both 360 min) read the same mail and both mint obligations → twin records.
- **Inbox evidence of completion** (CPA receipt 10-12, Bupa booking 10-19) was announced to
  Mike and closed nothing.
- Reverse failure: 10-22 the Diarist logged "Home stretches completed" from the day's *plan*.

No store toggles an item to done in code. The only real done-state (obligations) is closed only
by a model tool call. Recurring items have no per-occurrence record and no missed state.

## 2. Mike's decisions (2026-10-23) — binding on this plan

1. **Extend** `tools/obligations.py` into the ledger; do not build a parallel store.
2. Completion: **(b) tap-to-complete in the app AND (c) inbox/correspondence evidence offering a
   close through a confirm card, plus explicit asks from the Synthesizer for ambiguous items.**
   Inference from conversation remains (08-09 ruling: no gesture is ever *required*).
3. Calendar deadlines stay — **the calendar is an essential repository**, used by future
   scheduler build-out. Linked to the ledger; code marks them done (✓ prefix).
4. **Overdue until done or manually dismissed** is a good default category. **Non-daily habits
   can be made up** — M/W/F workouts are really 3×/week. **Tasks can be rescheduled** to a new
   deadline (Apex: missed deadline re-formed as a new one) with the history kept.
5. **All of it, including medication** — built universally; **a safety flag goes up at review
   before production** (see § 9).
6. **"Must update all the places where the obligation sits or gets triggered, or each place
   should consult the central ledger."** § 5 is that inventory.
7. **Waiting-on-someone** items mostly expect an update **from correspondence** (email, chat),
   not from the user — not universal.

## 3. The model

**Task** (the definition) → **occurrences** (instances). Every occurrence has a stable id,
`<task_id>@<period>` — e.g. `ob_261023_a1b2c3@2026-10-23` (daily), `…@2026-W43` (weekly quota),
`…@2026-10-26` (interval/deadline instance). Existing `ob_YYMMDD_hex` ids are kept; new tasks
use the same shape.

| Kind | Example | Occurrence | If not done |
|---|---|---|---|
| `deadline` | pay Chase by 10-17; book physio | one (the task itself) | **overdue until done or dismissed** (default); `moot` after `moot_after` when set (event-bound: RSVP) |
| `habit` | stretching daily · gym 3×/week (pref. M/W/F) · meds 2×/day | one per period (`every: day/week/month`, `times: N`) | period ends short → `missed` with `done_count/target`; within a non-daily period a missed preferred day is **made up** any later day |
| `interval` | water plants every 3 days | next one created when the last is done (`due = done_on + N`) | carries until done |
| `waiting` | Sirva to call; S.A.R. e-file confirmation | one | never "overdue" — surfaced once at `check_back`; closed by correspondence evidence or the user |

`eligible_from` (any kind) keeps a task **dormant** until that date — the "begin once eligible"
case. Undated one-offs are allowed (as today).

**States.** Stored: `open` · `done` · `skipped` · `missed` · `moot` · `dismissed`. Derived at read
time from `as_of`: `dormant`, `due_today`, `overdue`, `upcoming`, `waiting`. Terminal states never
reach a model except in the short "closed recently" list (§ 4). **Skipped ≠ missed** (Medtronic:
"I'm going to pass" is a decision). **Planned ≠ done** — only the user (words, tap, or an approved
evidence card) moves an occurrence to done.

**Derivation is pure** (`state(task, as_of)`), so the block is right even if the nightly sweep
never ran (VM asleep). The sweep only **persists** finished periods to history.

**The clock (R6).** Every date in the ledger is the **persona-local** date from
`tools/ambient._now_local()` (profile timezone — the same clock line the models are shown),
never bare `date.today()`. Day = local date; week = ISO week, Monday–Sunday local; month =
calendar month. **First period:** a task has a `start` (default: its local creation date); a
period that began before `start` is persisted with `partial: true` and **excluded from
adherence denominators** — a quota created on a Friday does not record `missed 0/3` for that
week. **Idempotency:** history rows are keyed by occurrence id; the sweep reads the keys already
on file and appends only missing ones. **Catch-up:** each task carries `swept_through`; a run
after downtime processes every ended period since then (bounded at 60 days).

**Store (R1 — no in-place migration).** The ledger lives in a **new file**,
`data/personas/{p}/tasks.yaml` (`{"version": 2, "tasks": [...]}`). On first load, if it is absent
and `obligations.yaml` exists, the v1 records are **imported** into it — and `obligations.yaml` is
**never written by new code again**. A rollback deploy therefore finds the v1 file intact as of
the import (stale, never destroyed), and the v2 file survives for the roll-forward. Roll-forward
safety: `tasks.yaml` records `imported_at` and the v1 file's mtime; if `obligations.yaml` is newer
on a later load (old code wrote during a rollback), ids not yet imported are added and newer v1
closes applied — v1 may add ids and may close an item v2 still has open; it can never reopen or
overwrite a v2 terminal state. Two consequences, stated so they are not rediscovered: a
`reopen_obligation` performed on old code during a rollback window is **dropped** on
roll-forward (v2's terminal state wins); and ids minted on v1 during the window pass the § 4.5
dedupe on import — a near-duplicate of an open v2 task is skipped and logged rather than
imported as a twin. Legacy `closed` → `done`; legacy `due` kept only if it parses as ISO, otherwise
moved into `note` (the v1 schema invited vague phrases). Finished occurrences of recurring tasks
are appended to `data/personas/{p}/task_history.jsonl` (0600, append-only, never rewritten) — the
adherence asset. The yaml holds only definitions + current/open occurrences, so it stays small.

**Reschedule** keeps history: `{"event": "rescheduled", "from": "2026-08-31", "to":
"2026-11-15", "reason": …}`. Adherence counts the original deadline as late.

## 4. What code owns vs what a model owns

**Code:**
1. Creating occurrences; eligibility; overdue; missed at period end; moot past `moot_after`.
2. **What reaches the head layer** — `context_block()` renders `## Tasks`:
   - *Now*: overdue, due today, today's habit progress where it matters (a preferred day, or the
     quota is at risk: remaining days in the period ≤ remaining count), interval tasks due,
     waiting tasks at/after `check_back` ("nothing seen yet from X").
   - *Closed recently (do not raise)*: done / dismissed / moot in the last 3 days, one line each —
     so a stale line in a log or thread is contradicted by a fact the model can see.
   - *Later*: a count only.
   Every line carries its id. Capped (today's `_CONTEXT_MAX` = 6 for *Now*).
   **The task matcher (R4).** Thread identity (`context_tracker._anchor_tokens`) is the wrong
   tool here: its generic list strips "chase" and its stemmer leaves "pay"/"paid" apart, so
   "paid the Chase bill" shares one anchor with "Pay Chase bill". The ledger gets its own
   `_task_tokens()`: content words, stopwords out, an irregular-verb map (paid→pay, sent→send,
   did/done→do, bought→buy, got→get, came→come, went→go, made→make, took→take, wrote→write,
   met→meet, brought→bring, told→tell…), `context_tracker._stem` for regular suffixes, and a
   **to-do generic list** — the verbs that are the *shape* of a task (pay, send, book, call, check,
   submit, finish, do, make, get, buy, sort, handle, complete, arrange, schedule, review, confirm,
   follow, remind, need, go, take, set, plan, finalise) plus time words. Brand and object nouns
   (chase, bill, card, physio, plants) stay anchors. **Match = ≥ 2 shared anchors, or identical
   sets.** For the hint (§ 4.4) and raise-once only, a task whose anchor set is a single token
   ("Stretching", "Gym") also matches when that token is shared — a false positive there costs one
   question or one suppressed repeat. Annotation (§ 5) never uses the single-token relaxation.
   Tests are written from the real phrasing of the § 1 cases.
3. **Raise-once per occurrence per day, in code.** After a **proactive** reply, occurrences the
   reply mentions (anchor match against `what`; ids never reach the user) are stamped
   `raised_on = today`. Later proactive turns that day render them as a count ("2 more already
   raised today"), **except** when the session is an `evening_close` **or
   `carries_weekly_review()` is true** (R9 — the weekly review rides another session kind, e.g. a
   Monday `morning_brief`), because that module deliberately suspends raise-once
   (`synthesizer_scheduled_sessions.md` :45, :51, :56). User-initiated turns always see the full
   *Now* list — the user may be asking. **Stamping hook:** `_close_turn_bookkeeping` receives the
   reply on both pipeline twins (core/orchestrator.py:6309, :6666). **Render hook (R2-9):** the
   block is built inside `load_recent_context(persona)`, which has no `kind`. Both twins already
   resolve `kind` before the Coordinator runs (:6207, :6434) and bind a thread-local turn
   (`tools/turn_context`, adopted into fan-out workers by reference); right after `kind` is
   resolved they write `turn["kind"]` and `turn["weekly_review"] =
   carries_weekly_review(kind, persona)` into it. `context_block` reads `turn_context.current()`;
   **no bound turn → nothing hidden** (raised items shown with their "raised today" mark), so an
   unbound path errs toward visibility.
4. **Possible-completion hint, on user turns.** If the user's message anchor-matches an open task
   AND carries a completion marker ("done", "did", "paid", "sent", "booked", "submitted",
   "handled", "sorted", "finished", "came", "arrived", "already") and no negation ("not yet",
   "haven't", "still need"), code adds one line naming the id: *"The user's message may report
   `ob_…` (Pay Chase bill) done — if it does, record it with update_task and their words; if you
   cannot tell, ask them once."* That is the code gate for Mike's "explicit asks for ambiguous
   items".
5. **Dedupe at creation.** (a) same `source_id` (intake envelope / thread) as an existing task,
   open **or closed within 30 days** → refused, names the existing id; (b) text near-duplicate of an
   open task → refused (today's guard); (c) text match (anchor identity) of a task **closed within
   14 days** → refused unless `new_instance: true` — the Chase re-mint.
6. **Consult points** — § 5.
7. **Adherence** counts — § 7.

**Model:** recognising that a user's words close a specific task, and calling
`update_task(task_id, "done", evidence=<their words>)`. Code cannot do that part without a tap.

## 5. Every place a to-do sits or triggers — and how it consults the ledger

Two match strengths, used everywhere text written by a model has to be checked:
- **Linked** — the copy carries the task id (the model sees ids in the block and is told to
  include them; code-written copies always do) or a stored link (calendar UID, source id).
  Deterministic.
- **Matched** — anchor-token identity reused from `tools/context_tracker.py`
  (`_anchor_tokens` / `_same_thread`: identical anchor set, or ≥ 2 shared distinctive anchors —
  a count, not a ratio, because a ratio loosens on short texts, which is where the recorded false
  positive lives).

**Policy: linked copies are acted on; matched copies are annotated, never deleted.** An annotation
is visible to the model and to anyone reading a trace, so a false match costs a question, not a
silently hidden commitment. Mike asked how aggressive suppression should be — this is the
proposal: aggressive only where the link is exact.

| # | Place | Writer | Treatment |
|---|---|---|---|
| 1 | Obligations block | code | becomes `## Tasks` (§ 4) |
| 2 | Calendar all-day deadline events | Logistics (`write_calendar_event`) | linked by UID: `open_task(calendar_uid=…)`, plus auto-link in `write_calendar_event` **only on an exact link** — an all-day event on the task's due date whose normalised title *equals* the task's `what` (R-§5: a merely matched copy is never promoted to linked and then mutated). On done → `update_calendar_event` title `✓ …`; on reschedule → event moved; best-effort, never fails the completion. Recurring series are **not** mutated in v1 (would need RECURRENCE-ID overrides). `read_calendar` annotates any event linked to a task with its ledger state (covers series occurrences too); matched-but-unlinked events get the read-only annotation and nothing else |
| 3 | Context-tracker `open_threads` / `follow_ups` | Synthesizer | **render** (`load_recent_context`): matched-to-closed → `"(done 10-15 · ob_…)"`; matched-to-open → `"(tracked as ob_…)"`. **write** (`_merge_open_threads`): a thread *linked* (carries the id) to a terminal task is dropped and logged as `removed: task closed` |
| 4 | Day-log fields `logistics.pending_items`, `reminders_set`, `horizon_items`, `events_scheduled`, top-level `intentions`, `tasks_completed` | Diarist / specialists | **render only** (logs are records, never rewritten): matching list entries get the same annotation, in both the per-field today rendering and the JSON dump of earlier days |
| 5 | Horizon ledger | Logistics → code | `record()`: an item matching a task closed within 14 days is not filed (counted `known`) — the chiropractor re-file. `_undelivered()`: skip items linked/matched to an **open** task (the Tasks block carries it — no double surfacing) or a terminal one |
| 6 | Calendar-reconcile candidates | code | skip events linked/matched to a terminal task (the question "did X happen?" is already answered) |
| 7 | Agent schedules (`write_schedule`) | Synthesizer / Logistics | **warn, never refuse (R8)**, keyed on *arguments*, not prose: a **recurring** job (`interval_minutes` set, no `at`) gets a warning naming `open_task` (habit/interval) as the home for a reminder that tracks whether something was done. One-off `at=` reminders are untouched — they are the only timed push path, and the ledger has no time-of-day delivery. Existing jobs are untouched by code; the Metatron fix prompt deletes the two named ones |
| 8 | Logistics' recurring-obligation inventory (`write_agent_config`) | Logistics | **One Home Per Rule Class rewrite**, not a one-liner: every line that places the inventory in `write_agent_config` moves to the ledger — `logistics.md` :41, :45, :70, :74, :176, :190, :220-221, :256, :267, :292 (Red batch) and `tools/schedule.py` :28-34 + its schema text (Amber, P2). Agent config keeps preferences. The existing blob is moved by the post-deploy prompt |
| 9 | Finance `write_archive` `category: bills` | Finance | recurring bills are ledger tasks (monthly habit or deadline); the archive keeps history |
| 10 | Physical Health medication / workout | Physical Health | medication schedules and workout quotas are ledger habits. **`medications_logged` and `MEDICATION_MISSED_CRITICAL` are unchanged** — the clinical flag path is not touched (§ 9) |
| 11 | Diarist intentions | Diarist | unchanged (Accountability input). Diarist line added: a plan for today is not `tasks_completed` |
| 12 | Intake / inbox | code + Logistics | tasks opened from a queue row carry `source_id` (envelope id) → dedupe (§ 4.5) and evidence (§ 6) |
| 13 | Relationships follow-ups / `PLANNED_CONTACT_PENDING` | Relationships | **out of v1** — contact-cadence metadata, not a commitment store; a stated commitment to contact someone becomes a task via the Synthesizer/Logistics. Named so it is a decision, not an omission |
| 14 | Goals (`update_goal complete`) | Synthesizer | out of scope — a goal is not a task |

## 6. Completion paths

1. **Conversation (existing, sharpened).** Synthesizer calls `update_task(id, "done", evidence)`,
   prompted by the block's ids and the § 4.4 hint; asks once when the hint fires but the words are
   ambiguous.
2. **Tap (b).** `GET /tasks/today` → actionable occurrences; `POST /tasks/act {task_id, action:
   done|skipped|dismissed}` records evidence `"marked in the app"`. UI: a ✓ button in `#controls`
   opening a panel (same pattern as `#loc-settings`) listing *Now* items with Done / Skip (and
   Dismiss for one-offs). No conversation row (like `/location`). **The APK bundles
   `static/index.html`, so this needs an APK rebuild + sideload — an (M) step, § 10.**
3. **Correspondence evidence (c).** In `tools/intake.sweep` (code, hourly), after classification,
   each processed envelope is matched against open `deadline`/`waiting` tasks:
   - same thread as the task's `source_id`, or
   - sender matches the task's `expect_from` (address, domain, or display name), or
   - subject task-matches `what` (§ 4 matcher, ≥ 2 anchors) AND carries a completion marker
     ("received", "confirmed", "confirmation", "receipt", "booked", "scheduled", "complete").

   A match parks a **proposal** on the task: `{proposal_id, envelope_id, basis, received}` —
   **ids and dates only; no subject, no sender text is stored on the task** (R3).

   **Delivered through the app's existing approval bar, but NOT through `tools/confirm.py`**
   (R2, R3, R7). Raising a confirm card from a timer collides with the pending-receipt diff both
   pipeline twins take at turn start (core/orchestrator.py:6197, :6421 → `enforce_pending_receipt`
   would attach "waiting for your approval" to an unrelated reply); a confirm card's description is
   written into the conversation on approve/decline (core/server.py:1163-1176, :1223-1230) and
   rendered unwrapped by `confirm.context_block` — both paths would carry attacker-written subject
   text into the head-layer prompt; and `execute()`'s error contract does not match this module's
   `error:` convention. So instead:
   - `GET /tasks/proposals` (read-only, no side effect) returns pending proposals, each joined at
     request time to its intake record for the sender and subject **shown to the user only**.
   - **Its own bar, not the confirm bar (R2-NEW1).** The confirm bar's Approve posts whatever the
     global `pendingToken` holds at click time (static/index.html:3539-3548), so sharing it would
     let a confirm card that arrives between polls be approved by a tap aimed at a proposal — an
     irreversible send approved as "mark done". A separate `#task-proposal-bar` with its own
     buttons: *"Mark 'S.A.R. e-file confirmation' done? An email from <sender> on <date>:
     '<subject>'"* — **Mark done** / **Not now**. Each handler sends the `proposal_id` it rendered,
     captured in a closure at render, never a shared global; the bar is hidden whenever the confirm
     bar is shown, and real cards always take precedence.
   - Mark done → `POST /tasks/act {task_id, action: "done", proposal_id}`; evidence stored is
     `"correspondence evidence, approved in the app"` + the envelope id — no attacker text.
     Not now → `POST /tasks/proposals/decline` → never re-offered for that envelope.
   - **`/tasks/act` maps an `error:` result from `update_task` to a 4xx**, and the panel and bar
     show it as a failure — a rejected close is never reported as done (R7, one layer over).
   - **No conversation row is written** (like `/location`). The Tasks block's *closed recently*
     line ("done 10-24 · approved from correspondence") is how the head layer learns of it; while
     pending, the block says only *"a close for `ob_…` is waiting for the user's tap"*.
   - Proposals expire after 14 days (sweep). Same consent property as a confirm card — the tap is
     out of band and the model is not in the path — without borrowing machinery built for
     irreversible actions.

## 7. Adherence

`task_history.jsonl` rows: `{task_id, occurrence, kind, period_start, period_end, target,
done_count, state, closed_at, late}` — content-free apart from the id. From them:
- per habit/interval: done ÷ target over a window; **skipped excluded from the denominator and
  counted separately**; per-period missed list;
- per deadline: met (done ≤ due), late, rescheduled, dismissed, moot.
- **A9 rollup** gains content-free daily counts (`tasks_done`, `tasks_missed`, `tasks_skipped`,
  `habit_target`, `habit_done`, `deadlines_met`, `deadlines_late`).
- **`_WORLD_AFFECTING`** (tools/analytics.py:59-65) **keeps the old obligation names as
  historical labels** and adds `open_task` / `update_task` — the `spend_guard.yaml` precedent for
  retired model ids (SESSION.md § Model IDs). Old traces carry old names, so no re-derivation of
  history is triggered (ROADMAP.md § A9a item 1 applies only to a definition change, and this
  is a rename with identical meaning).
- **Accountability Index**: `_fetch_obligations` reads the new store through an adapter (closed
  one-offs + done occurrences in the old `{what, status, closed_at}` shape), so intention joins
  keep working and recurring completions now count as structured evidence. CLI
  `python3 -m tools.obligations --report`.

## 8. Tools and grants

Replace the four obligation tools with three (old names removed, not aliased — a replaced mechanism
is removed, Mike 2026-09-24):

- `open_task(what, kind, due, eligible_from, moot_after, every, times, on_days, interval_days,
  waiting_on, expect_from, check_back, domain, note, source_id, calendar_uid, new_instance)`
- `update_task(task_id, action, evidence, new_due, note)` — `done | skipped | dismissed | reopen |
  reschedule | note`; recurring `done`/`skipped` apply to the current occurrence, `dismissed` ends
  the task.
- `list_tasks(include_closed)`

Granted to exactly the agents that hold the obligation tools today — `synthesizer`, `finance`,
`logistics` — in **both** routing files (Red). `scripts/check_agent_tools.py` must stay clean.

**Code that names the old tools (R5) — changed in step with the rename:**
- `core/actions.py` :73, :138 — classify `open_task`/`update_task` (action) and `list_tasks`
  (read) **in P1**, beside the old names; old names removed in the Red batch.
  `tests/test_action_provenance.py` fails on any registered-but-unclassified tool, which is the
  guard that makes this ordering necessary.
- `core/build/manifest.py` :154 — Build's `obligations` read door moves `list_obligations` →
  `list_tasks` in the same batch that unregisters the old name, or the door silently reports
  `available: False`.
- `tests/test_false_action_claim.py` :109-111 — asserts on `close_obligation`; updated to
  `update_task` in that batch.
- `tools/obligations.py`'s old functions stay as thin wrappers over the new store until the Red
  batch, so every suite stays green at every phase.

## 9. Medication — built universally, flagged before production

Mike: build it all including medication; put a safety flag up before production. The ledger
supports medication habits (`every: day, times: N`). **Nothing in the clinical path changes**:
`MEDICATION_MISSED_CRITICAL` stays a Physical Health classification from `medication_profile`;
the ledger neither raises nor suppresses it. **Before production:** review whether a ledger-missed
medication occurrence should feed the clinical flag, and run `tests/run_a4_safety.py` — the flag
must fire identically with ledger medication tasks present. This line is the record of that flag;
where it is filed at close-out is Mike's call.

## 10. File-by-file, tier, order

| Phase | Files | Tier |
|---|---|---|
| P1 ledger core | `tools/obligations.py` (new `tasks.yaml` store + import, derivation on the local clock, history, tools, block, matcher, hints, raise-once, dedupe), `core/orchestrator.py` (registration, hint + raise-once hooks), `core/actions.py` (classify new names), tests | Amber |
| P2 consult points | `core/orchestrator.py` (thread/log annotation), `tools/context_tracker.py`, `tools/horizon.py`, `tools/calendar_reconcile.py`, `tools/caldav.py` (exact link, ✓, annotate), `tools/schedule.py` (warn on recurring reminder; inventory text), tests | Amber |
| P3 completion paths | `tools/intake.py` (proposals), `core/server.py` (`/tasks/today`, `/tasks/act`, `/tasks/proposals`, `/tasks/proposals/decline`), `static/index.html` (Today panel; proposals in the approval bar when no card is pending), tests | Amber |
| P4 wiring | `tools/accountability.py`, `tools/analytics.py`, `config/modules/synthesizer_scheduled_sessions.md` | Amber |
| P5 **Red batch — last, in one sitting** (Mike, 2026-10-23: *"Leave the red tier edits to the very end of the work so that we can do them in a batch"*) | `core/scheduler.py` (`daily_task_sweep`, 00:15, silent, token-free, **`respect_quiet_hours: False`** — R10: 00:15 is inside quiet hours and `fire_function` skips rather than defers), `config/agents/{synthesizer,logistics,finance,diarist,coordinator}.md`, `config/modules/routing.yaml` + `routing_cloud.yaml`. Same sitting, Amber but bound to the rename: unregister the old tools in `core/orchestrator.py`, drop old names from `core/actions.py`, move Build's door in `core/build/manifest.py`, update `tests/test_false_action_claim.py` | Red (prompts Mike) |
| P6 | full regression, diff review | — |

Until P5 lands, the new tools are registered but granted to no agent, so the Amber phases cannot
change live behaviour mid-build; the old obligation tools stay in place until the same batch
removes them.

**Recent work checked:** today's three commits touched `core/server.py`, `static/index.html`
(client outbox, 842 lines), `core/orchestrator.py` and `coordinator.md`/`synthesizer.md` (misheard
names). This plan builds on HEAD; the panel is additive to the outbox code, and the agent-file
edits do not touch the heard-names lines.

**Not touched:** `config/constitution.md`, persona data (`data/personas/**` is Denied — the VM owns
it; the migration runs as code on the VM), `deploy.sh` (Denied — Mike deploys).

**Mike's steps after the build:** review the diff; commit; `./deploy.sh`; rebuild + sideload the
APK (`docs/INFRASTRUCTURE.md` § APK); paste the post-deploy setup prompt (gym 3×/week,
stretching, plant watering every 3 days, medication schedule, Logistics' recurring inventory) —
offered as a guided walkthrough.

## 11. Tests

Synthetic fixtures only (no persona data in tests). One test per failure class in § 1:
Chase re-mint after close refused; twin from the same source refused; RSVP moot after its event;
plant interval due from last done, not a frozen date; waiting item never overdue and surfaced at
check-back; 3×/week quota with a Monday make-up on Tuesday and `missed 2/3` at week end; daily habit
missed at midnight; reschedule keeps history and counts late; stretching plan not marked done;
thread/log annotation (linked vs matched); horizon refusal; reconcile skip; hint fires on
"paid the Chase bill", not on "still need to pay Chase" (against the § 4 task matcher, with the
real phrasing of the § 1 cases as the table); raise-once hides on a second check-in but not on
`evening_close` nor on a morning brief carrying the weekly review; import of a v1 store (legacy
closed, vague due) **leaves `obligations.yaml` byte-identical**, and a newer v1 file re-merges on
roll-forward; first-period `partial` excluded from adherence; a repeated sweep appends nothing;
persona-local date across a midnight that differs from UTC; tap endpoint; evidence proposal →
`/tasks/proposals` → `/tasks/act` → done, with **no subject/sender text in the task record, the
conversation, or any context block**; decline never re-offers; a pending confirm card always
outranks a proposal in the bar; `write_schedule` warns on a recurring reminder and is silent on a
one-off `at=` reminder. Existing suites re-run: `test_obligation_due_sort`, `test_accountability*`,
`test_tool_error_flag`, `test_turn_referent`, `test_ritual_focus_gate`, `test_action_provenance`,
`test_false_action_claim`, `test_client_outbox.js`, `scripts/check_agent_tools.py`.

## 12. Cost

- **Build:** this session, Opus 5.5 on the subscription — roughly 2–4M tokens, most of it cache
  reads; one or two Fable 5.1 review passes, ~0.3–0.6M each.
- **Run:** **no new model calls.** The sweep is token-free; evidence matching is CPU in an existing
  hourly job. The Tasks block replaces the obligations block (similar size; +≤ 3 "closed recently"
  lines; − the stale items that sit in every turn today). Deleting the duplicate
  `check_inbox_recurring` job saves ~**$2.8/month** (measured: 103 runs / 34 days, ~14.4M tokens at
  `spend_guard.yaml` list rates).
- **Ancillary:** one CalDAV update per completion of a linked event; `task_history.jsonl` grows a
  few hundred rows a year per habit (tens of KB).
- **Unseen / persistent:** `task_history.jsonl` — owner `tools/obligations.py`, never deleted (same
  standing as A9 rows; the adherence asset), no meter needed at KB scale. Evidence proposals —
  expire at 14 days via the sweep. `raised_on` stamps — overwritten daily. Nothing billed by
  wall-clock is created.

## 13. Review round 1 — Fable 5.1, 2026-10-23: ten findings, all accepted

| # | Finding (what would have broken) | Resolution, and where |
|---|---|---|
| R1 | A rollback after the in-place migration would erase the v2 store on old code's first write — unrecoverable, no backup | New file `tasks.yaml`; `obligations.yaml` imported, never written again; roll-forward re-merge (§ 3) |
| R2 | A card raised from the 5 s poll is misattributed to whatever turn is running → "waiting for your approval" on an unrelated reply | Proposals never enter `confirm.py`; separate read-only feed shown in the bar only when no card is pending (§ 6.3) |
| R3 | Email subject/sender would reach the head-layer prompt via the confirm conversation row, `confirm.context_block`, and stored evidence | No attacker text stored on the task or written to the conversation; shown to the user only, joined at request time (§ 6.3) |
| R4 | The reused thread matcher misses "paid the Chase bill" ("chase" is generic there; pay/paid unstemmed) | Ledger-specific `_task_tokens` with irregular verbs and a to-do generic list (§ 4) |
| R5 | Old tool names are load-bearing in `core/actions.py`, Build's manifest, `test_false_action_claim` | Classified in P1, removed with the grants in the Red batch (§ 8, § 10) |
| R6 | Clock, first partial period and re-run idempotency unstated for a permanent file | Persona-local clock, `partial` periods excluded, history keyed by occurrence id, `swept_through` catch-up (§ 3) |
| R7 | `confirm.execute()`'s error contract would report a failed close as "✅ Done" | Moot — no executor (§ 6.3); new tools keep the `error:` prefix `test_tool_error_flag` pins |
| R8 | Refusing reminder-shaped schedules kills one-off `at=` reminders, the only timed push | Warn only, keyed on recurring arguments (§ 5 row 7) |
| R9 | Raise-once exemption missed the weekly review riding a morning brief | Exempt on `carries_weekly_review()` too (§ 4.3) |
| R10 | 00:15 sweep sits in quiet hours and would never run, silently | `respect_quiet_hours: False` (§ 10) |

Also taken: § 5 row 2's auto-link restricted to an exact link; § 5 row 8 rewritten as a full
One-Home-Per-Rule-Class move with every line named; `_WORLD_AFFECTING` keeps the old names as
historical labels (§ 7).

**Round 2 (Fable 5.1):** R1–R8 and R10 closed; § 3, § 5, § 7–§ 12 AGREE. Two remaining, both
accepted: **R2-9** — raise-once needs `kind` at the render site → written into the thread-local
turn by both twins (§ 4.3); **R2-NEW1** — a shared approval bar lets a confirm card be approved by
a tap aimed at a proposal → its own bar, proposal id captured per render (§ 6.3). Also written in:
the two roll-forward consequences (§ 3) and `/tasks/act` failure mapping (§ 6.3).

**Round 3 (Fable 5.1): § 4 AGREE, § 6 AGREE, nothing newly broken — every section § 3–§ 12 now
AGREE.** One non-blocking note: `carries_weekly_review()` reads the weekday off the system clock
(core/orchestrator.py:395) while the ledger runs on the persona-local clock; they disagree only in
the hours around midnight, when no brief fires.

The reviewer's adjudication of the former open questions: annotation at ≥ 2 anchors is safe —
the risk was under-matching, fixed by R4; lazy raising from the poll was unsound (R2); warn, not
refuse (R8); anchor match is the right strength for raise-once once the matcher is fixed.
