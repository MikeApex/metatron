# Goals to tasks — one network, vetted, fed one step at a time — plan, 2026-11-18

Model: Opus 5.5 plans and builds; Fable 5.1 reviews this plan and each phase's diff
(docs/WORKFLOW.md, Mike 2026-09-24). Red work is done in-session, never delegated.

**Status: plan, not authorisation.** Written after a 4-question interview and Mike's answers in
the same session. Absorbs stage 2 of `synth_now_next_plan_2026-10-30.md` (the Red Book) as its
first case — that plan's § 11 points here.

## 1. The need, in Mike's words (2026-11-18)

> *"A single pipeline for all tasks a user must complete, as a network map with dependencies. The
> tasks should be accessed and managed by Metatron, not the user. When a new item is desired by
> the user be it one off, complex task or long term goal, or Metatron determines that something
> needs to be done, an agent should project manage the end state into modular tasks and
> dependencies. The user receives instructions at the single task level."*

**Done** (Mike): *any new desire, goal, or obligation that enters Metatron's ecosystem is vetted
for feasibility, priority, and seriousness, and then passing those gates is broken into subtasks
small enough to be handled by the user as one-off obligations — seamless and largely unseen.* The
user follows Metatron's directions and their goals happen, with no task management of their own.
**Metatron alerts when a step's deadline matters to the goal's deadline**, so the user's
expectation of the finish date is managed.

Three sizes, Mike's examples: **the Red Book** (one prep before one event), **filing taxes**
(gather documents → decide on an accountant → research → file), **learning a language** (months,
recurring time, the user's commitment is the risk).

**Scope rule (Mike):** build on existing infrastructure, modified as needed. Reuse orphaned or
unused parts before building new ones.

## 2. Mike's rulings, 2026-11-18

| # | Ruling |
|---|---|
| G1 | **One generic project-planner agent, plus per-goal-type playbooks** (option a). Playbooks hold method only, no user content. **Confirmed as the bridge** to "a tax planner or language teacher module with deeply researched best practices to assist all users" — § 4.4. |
| G2 | **Vetting accepted, with depth commensurate with the goal's size in the user's time.** Vetting is continual: re-vetting on **repeated non-compliance**, **across several durations** (a goal can lose its appeal with time), and on a **historical mismatch between anticipated and experienced satisfaction** ("buying concert tickets in advance vs feelings about going out the night of the actual concert"). |
| G3 | **The Goals Interviewer overhaul folds into this plan** (was Mark 2; Mark 2 ended today). |
| G4 | The user sees one task at a time; the whole map only on request. A step that slips far enough to move a goal's likely finish is said once, with the new date. Durations start estimated and are corrected by actuals. |
| G5 | One plan, reviewed as a whole; **built in three phases with a live check after each.** Review finding #5 (*a nudge due near a fixed session is dropped*) is fixed in phase 1. |
| G6 | Tested on the fixture personas first, then live on `mike` with Mike's feedback; **Iva vets it too if she has signed up in time.** Mike supplies more goals. |
| G7 | **Goals can be written from chat, once verified.** Not only the Interviewer: **Synth performs or hands off goal evaluation.** `mike`'s goals must be populated, or the existing ones verified and talked through with `mike`'s Metatron. |
| G8 | **Build (agent building) is out of scope** — "a time to revisit/revise Build". Nothing here depends on it. |

## 3. What exists, and what each piece becomes

Three read-only surveys, 2026-11-18. **No task links to another task anywhere.** Most of the rest
exists.

| Exists | Where | Status | Becomes |
|---|---|---|---|
| Task ledger, one per persona | `tools/obligations.py`, `tasks.yaml` | live | **the network** — every node is a task |
| `dormant` state from `eligible_from`: hidden from Today, the planner and Synth | `_view_core` `obligations.py:908` | live | **`blocked` sits beside it** — same hiding, everywhere, in one change |
| `later` state (> 2 days out shows only as a count) | `_view_core`, `_LEAD_DAYS` | live | unchanged; it already hides the far end of a plan |
| `done_with_followup` (closing A opens B, by hand) | `update_task` | live | generalised: B is pre-registered, blocked on A |
| `goal_id` / `goal_hash` on tasks; essential-goal weight in the planner | `obligations.py:1340`, `day_plan.py:510` | live | a goal's steps link to it; weight unchanged |
| `parent_goal` (quarterly → weekly → daily) | `config/goals.yaml` | live | kept; a longer horizon is added (§ 4.6) |
| `allocation_gaps` (a goal with no linked habit → propose time, weekly) | `day_plan.py:2282` | live | **generalised to "a verified goal with no plan"** → decomposition |
| Interviewer phases 4–5: timeline, energising vs "should", trade-off forcing → `essential` | `config/agents/goals_interviewer.md` | live only for new accounts, **never `mike`**; re-interviews never built | **the vetting method** for large goals and re-vetting (G3) |
| `NEW_GOAL` dispatch: specialist asks 2–3 domain questions before planning | `coordinator.md:164`, `synthesizer.md:180` | live, but answers go to agent notes, **not** `goals.yaml` | the entry point for a goal stated in chat |
| Synth's `update_goal` — *"Record it then"* | `synthesizer.md:375` | live | **changed: a goal from chat is written `proposed`, not active (G7)** |
| Goal capture from chat | `tools/capture.py`, `capture.yaml` | built, **off** (labels pending) | untouched here; when on, its goal suggestions also land as `proposed` |
| Day-planner reshuffle: a no-tools agent proposes, code validates, else the code plan stands | `day_plan.py:2422-2482` | live | **the pattern for the project planner** — same shape, same validator idea |
| Horizon findings with `precursor` / `precursor_by`, filed by Logistics | `tools/horizon.py` | live | the Red Book's source (phase 1) |
| Accountability Index (logged intentions vs what happened; nightly judge) | `tools/accountability.py` | live | **a non-compliance signal** for re-vetting |
| `write_aspirational_baseline` (good/hard weeks, peak/floor days) | `tools/baselines.py:320` | **orphaned** (written, read by nothing) | **read by vetting** — what the user said a good week holds is what a large goal must fit into |
| Unused goal fields `timeline`, `kpis`, `open_questions`, `retrospective_fit` | `config/goals.yaml` template | **orphaned** | `timeline` → the goal's deadline; `open_questions` → vetting's carry-over |
| Time Director (retired prioritisation prompt) | `config/agents/time_director.md` | **orphaned** | mined for the priority method; not revived as an agent |
| Research Agent (cloud, decontextualised by rule) | `routing_cloud.yaml:387` | live | **researches playbooks** — method only, no user context (§ 4.4) |
| Build `next_step()` (works out the next step from state on disk) | `core/build/driver.py:156` | live, dev-only | the idea only; Build itself is not used (G8) |

## 4. Design

> **Amended by § 10 (Fable review, reconciled 2026-11-18).** Where § 10 and §§ 4–8 differ, § 10
> governs.

### 4.1 The network: two fields and one state

- **`needs: [task_id, …]`** on a task: it cannot start until each is done (or dismissed —
  § 4.5). **`part_of: <goal id | task id>`**: the end state it serves. An obligation's end state
  is itself a task (*"File the 2026 return, due 31 Jan"*), with its steps `part_of` it; a goal's
  steps are `part_of` the goal.
- **`for_event: <calendar uid>`** on a prep task (the Red Book): due is **derived** from the
  event's start each time it is read. A moved event moves its prep (Fable A9) with no extra code.
- **New derived state `blocked`** in `_view_core`, checked beside `dormant`: an open task with an
  unfinished `needs` is not actionable. It flows to the Today list, `_candidates`, `context_block`
  and the app in one change, as `dormant` does.
- **`list_tasks` hides blocked steps by default** (today it lists every open task — the one leak
  in the hidden layer). `read_plan(part_of)` returns the whole map on request (G4), the way
  `read_day_plan` gives the whole day.
- Code validates every write: `needs` must exist and be acyclic; a task `part_of` a declined or
  completed goal is closed with that reason.

### 4.2 Intake and vetting — depth by size (G2, G7)

**Where items enter:** the user says it (chat, `NEW_GOAL`), Metatron finds it (Logistics
findings, mail, the calendar), or an interview. **Synth decides or hands off** (G7):

| Size — the user's time | Example | Vetting | Who |
|---|---|---|---|
| **S** — one sitting, ≤ ~1 h total | Red Book, book a table | none beyond the existing ledger rules | code |
| **M** — hours to days, one end date | taxes, renew a passport | feasible by the deadline? priority against what's open? one confirmation | Synth, in the turn |
| **L** — recurring time for weeks or more | a language, a fitness target | the Interviewer's trade-off forcing, at a size-matched depth: what it displaces in a real week (read against the aspirational baseline), why, by when, what "done" means | Synth for a short pass; **hands off to the Goals Interviewer** for a full one |

- A goal stated in chat is written **`status: proposed`**. **Only `active` goals are decomposed.**
  Vetting promotes it to `active`, `parked` (later, with a date to re-ask) or `declined` (kept,
  per archive-on-merge). The verdict is recorded on the goal: `vetted: {date, depth, displaces,
  priority, by}`.
- **Obligations skip the seriousness check** — nobody chooses whether to file taxes — and get only
  feasibility and timing.
- Size is estimated by the project planner (§ 4.3) from the total minutes and the weekly time the
  plan needs, so vetting depth is code-chosen, not a model's mood.

**Re-vetting, all detected by code; only the conversation is a model (G2):**
1. **Non-compliance:** a goal's steps skipped or "not yet" N times within a window (from the
   ledger and the Accountability Index). Today's evidence: *repot the two basement plants* was
   proposed at 07:30 on at least four mornings 11-12 → 11-18 and not done.
2. **Time:** checkpoints scaled to size (an L goal re-asked at about 2 weeks, 6 weeks, then each
   quarter). Phrased as a question, never a verdict (CLAUDE.md § hypotheses).
3. **Satisfaction mismatch:** a one-line anticipated value when a commitment is made, and a
   one-line experienced value after it. A consistent gap for one class (evening outings booked
   weeks ahead) is raised when the next one is proposed, and feeds that class's vetting. **This
   costs user attention, the denominator of the absorbed-work metric (ROADMAP § A9)**, so it is
   asked rarely, and only for commitments in a class with history.

### 4.3 Decomposition — one project planner

- **A new agent file, `config/agents/project_planner.md` (Red).** No tools, same as `day_planner`.
  Code calls it via a `plan_project(part_of)` tool Synth holds, or from the weekly
  "verified goal with no plan" sweep.
- **Input:** the end state, its deadline, the user's weekly time for it, and the playbook if one
  exists. **Output:** JSON steps `{what, minutes, needs, eligible_from?, due?}`.
- **Code validates** the output: acyclic; every step ≤ a size cap (config, ~90 min); dates inside
  the deadline. A failed validation re-asks once, then files the goal as "needs a plan", said
  once. Same pattern as the reshuffle.
- **Rolling wave for L goals:** the next milestone is planned in steps, later ones as one coarse
  node each, expanded when they come due. This keeps the ledger small and answers the
  future-phases Projects question (up-front vs incremental) with incremental.
- **Opening a step does not trigger a reshuffle model call** (Fable A5). Code places it; the 12/day
  cap is untouched.

### 4.4 Playbooks — the bridge to researched modules (G1)

- `config/playbooks/<type>.md`, e.g. `taxes_uk_self_assessment.md` or `language_learning.md`:
  stages, typical steps and durations, known prerequisites, common failure points. **Method only;
  a user's content never enters one.** Shared by every persona because it is config.
- **Researched by the Research Agent**, which may use cloud models because the question carries no
  personal context ("best practice for an adult learning Spanish to B1"). Written dev-side at
  first; Mike reviews each one before it lands.
- **Why it is the bridge:** a playbook *is* the "deeply researched best practices" half of a tax
  planner or language teacher module. The other half, behaviour that needs new code (a tutor
  running drills, a tax tool reading statements), is a capability. That is where a revised Build
  returns (G8). So playbooks replace Build for **knowledge**, not for new **behaviour**.
- **Not now:** Metatron writing a playbook at runtime from one user's goal. With one real user,
  every playbook would be distilled from that user, and one leaked detail reaches everyone's
  planner. It needs a ROADMAP § 0 ruling and a content-stripping check first.

### 4.5 Delivery and the finish date (G4)

- The planner sees only unblocked steps; Synth sees Now/Next as today; the app shows only what is
  actionable. **Closing a step unblocks the next in the same tick.**
- A **dismissed** step unblocks what needs it only if the step was optional. Otherwise the project
  planner is re-asked for a replacement, so a skipped "gather P60" cannot silently unblock
  "file the return".
- **Projected finish:** the remaining critical path, from step minutes and the weekly time the
  user gives the goal. When it crosses the deadline, or moves by more than a size-scaled margin,
  it is raised once as Important: *"At this pace the return is ready 6 Feb, after the 31 Jan
  deadline — two evenings this week would fix it."* Durations correct from actual close times.

### 4.6 Goals data (G7)

- Add `status: proposed | parked | declined`, and a **long** horizon above quarterly, since a
  language is not a 90-day goal. Use the orphaned `timeline`, `open_questions` and `vetted`
  fields. Done in `tools/goals.py` and the template; `allocation_gaps` reads only `active`.
- **`mike`'s goals are VM-owned persona config, Denied here** (`.claude/rules/personas.md`).
  Populating or verifying them is a **Mike-gated walkthrough session** after phase 2: Mike talks
  each existing goal through with his Metatron (a re-interview, built under G3), plus the new ones
  he supplies. Prepared steps, Mike live (CLAUDE.md § Mike-gated work).

### 4.7 The Red Book under this design — Fable's 10-30 findings answered

| # | Finding | Answered by |
|---|---|---|
| A1 | same-morning filing put the prep after the event | due derived from `for_event`; if the event is today, due today, placed before it |
| A2 | scheduler and server both write the horizon ledger | conversion runs in the **server**, at filing time (`record()`) and on the window sweep there; the scheduler only reads |
| A3 | "off" did not restore stage 1 | flag gates both the conversion and the `prep_items` skip; off closes open prep tasks with a reason, and `prep_items` says them again |
| A4/A7 | dedup missed the precursor; siblings unstamped | dedup key = event uid + normalised precursor; every sibling finding stamped |
| A5 | each task cost a reshuffle | § 4.3: placed by code, no model call |
| A6 | prep pinned to the evening-close clock | placed from the day shape; light, screen-free prep allowed in family time, a screen task not |
| A8 | refused open retried every 5 min | refusal stamped on the finding |
| A9 | moved event left prep on the wrong night | due derived from `for_event` at every read |

## 5. Phases — each ends in a live check with Mike

**Phase 1 — the network and the Red Book.** § 4.1, § 4.5 (unblocking, no finish-date yet), § 4.7,
and review finding #5. *Live check:* the next real event with a precursor gets a scheduled prep,
nudged and checked; Today shows only actionable steps; a two-step test project shows step 2 only
after step 1 is done.

**Phase 2 — intake, vetting S/M, the project planner, the first playbook (taxes).** § 4.2 S/M, the
`proposed` status, § 4.3, § 4.4 (one playbook), § 4.6 schema, the "verified goal with no plan"
sweep. *Live check:* Mike states a mid-sized obligation in chat. It is vetted in the turn, planned
unseen, and fed one step at a time.

**Phase 3 — large goals.** L vetting with the Interviewer re-interview (G3), rolling wave,
re-vetting triggers 1–3, projected-finish alerts, the language playbook. Then the **`mike` goals
walkthrough** (§ 4.6). *Live check:* one real L goal over two weeks, plus a deliberately ignored
step that triggers a re-vet.

## 6. Tests

- **Unit, per phase:** blocked hides everywhere (Today, `_candidates`, `context_block`,
  `list_tasks`); cycles refused; unblocking in the same tick; dismissed-required step re-plans;
  `for_event` follows a moved event; A1–A9 each a case; flag off restores stage 1; vetting depth
  by size; `proposed` goals never decomposed; validator rejects oversized steps and dates past
  the deadline; projected finish crosses the deadline → one alert, not one per tick.
- **New runner on the seven fixture personas** (`danny_park`, `sarah_chen`, `maya_torres`,
  `arthur_brooks`, `cal_newport`, `oliver_burkeman`, `ryan_holiday`): each seeded with an S, an M
  and an L item. Asserts across simulated days: only the next step is ever visible, a blocked
  step is never placed, the finish date holds or is alerted. Model calls stubbed (standing rule:
  every live meter stubbed); one opt-in `METATRON_LIVE=1` pass for the planner's real output.
- **Live:** `mike`, per phase; Iva if signed up (G6). Then `./scripts/qa_sweep.sh`.

## 7. Red edits this build will prompt for

`config/agents/project_planner.md` (new); `config/agents/synthesizer.md` (goal from chat →
`proposed`; vet or hand off; `plan_project`, `read_plan`); `config/agents/goals_interviewer.md`
(re-interview mode, G3); both routing files (the new agent; grants for `plan_project`,
`read_plan`); `config/agents/coordinator.md` (`NEW_GOAL` answers reach the goal record, not only
agent notes). `core/scheduler.py` only if the sweep cannot live in the existing `refresh_tick`.

## 8. Budget

**Build (estimates, not measured):**

| Phase | Work | Sessions | Rough cost |
|---|---|---|---|
| Plan review | Fable adversarial review of this file | 1 | ~$15–30 |
| 1 | network, Red Book, #5; Fable diff review | 1–2 Opus | ~$40–80 |
| 2 | vetting S/M, planner agent, schema, taxes playbook; Fable diff review | 2 Opus | ~$60–120 |
| 3 | L vetting, rolling wave, re-vetting, alerts, language playbook; Fable diff review; mike walkthrough | 2–3 Opus + 1 with Mike | ~$80–150 |

**Run** (*the phase 1 "zero" is corrected by § 10 R5*)**:** phase 1 costs zero model tokens. After that: one reasoning-tier call per new M/L item
and per milestone expansion. For one user that is a few calls a week; vetting is ordinary
conversation turns. Re-vetting detection is code. **Unblocking never calls a model** (no
reshuffle).

**Ancillary:** hidden steps make `tasks.yaml` bigger, and it is read every 5-minute tick. Rolling
wave keeps it to the next milestone per goal; closed steps go to history as today. Hidden steps
never enter a prompt, so context does not grow.

**Unseen — no meter reports these:**
1. Tasks the user never asked for, bounded by vetting (nothing is decomposed unverified) and by
   rolling wave.
2. A wrong playbook replicates to every user's plan. Every playbook passes Mike's review before
   it lands.
3. Satisfaction questions cost user attention, the denominator of the core metric. Asked rarely,
   class-gated.

**What persists between calls:** hidden steps and playbooks. Steps are owned by their `part_of`
end state and closed when it completes or is declined; they persist across restarts as ledger
rows (nothing is orphaned by a crash). Playbooks are config and cost nothing standing.

**Model:** plan and build Opus 5.5; review Fable 5.1. The runtime project planner runs on the
reasoning tier (`gemini-3.8-flash` in `routing_cloud.yaml` today; the routing file is the
authority).

## 9. Not in this plan

- Build and agent building (G8).
- Runtime-authored playbooks, and any cross-user flow of learned content (§ 4.4) — those need a
  § 0 ruling.
- Stage 1's three live-check misses (Monday's week-ahead rundown, uncapped new horizon items, the
  repeated "takes your own time"). Mike decides whether they are fixed; they are not folded in by
  default.
- A7 checks 10/12 and A8, whose Mark 2 home ended today. They go to the next `/backlog`.

## 10. Fable review and reconciliation (2026-11-18)

Fable 5.1 adversarial review of §§ 1–9: **four structural, six local findings. All ten were
checked against the code and accepted.** Each amendment below replaces the text it names.

| # | What would have gone wrong | Verified at | Amendment |
|---|---|---|---|
| R1 | **A "Done" tap or a planned step silently lost.** The server has no periodic job — every tick is in the scheduler — and the task ledger and horizon ledger are whole-file load-modify-save under **in-process** locks only, while the server writes them on user turns | `core/server.py` `_startup` (one warm-up task, no tick); `tools/obligations.py:171` `_LOCK = threading.RLock()`, `:476` `_with_store`; `tools/horizon.py:62` | **Phase 1, first change:** `_with_store` and the horizon ledger's save take an **`fcntl` file lock plus atomic rename** — the pattern already in `tools/day_plan.py:160-186` and `core/accounts.py`. With that, every sweep lives in the scheduler's `refresh_tick` and the "server window sweep" is dropped. This also closes a latent race that exists today (the scheduler's nudge/sweep writes vs a user tap). |
| R2 | **The Red Book prep could not follow its event** — a horizon finding has no calendar uid (title/date/venue only), and `_view_core` is pure over one row with no calendar | `tools/horizon.py:594-609`, `:132` `item_key` | **No `for_event` derived on read.** At conversion, the sweep matches the finding to the planner's calendar snapshot by date + venue/title tokens and stores the event's `calendar_uid` on the prep task. **`due` is stored**, and the sweep re-derives it each tick from the snapshot: event moved → due moves (A9); event deleted → prep closed `moot`, reason "event cancelled"; calendar unreadable or event outside the snapshot → left as is. A finding from mail with no calendar event → a plain dated prep, no auto-move. Dedup key = `item_key` + normalised precursor; siblings are findings on the same date whose title tokens match, and all are stamped (A4/A7). |
| R3 | **Vetting depth was chosen from a plan that may only be made after vetting** | `tools/goals.py:154-166` | **Size is Synth's call in the turn** (S/M/L, from what the user said: one sitting, one end date, or recurring time). The "code-chosen, not a model's mood" claim is withdrawn. Vetting runs at that depth; only then does the planner run. **If the planner's estimate lands a size above Synth's, nothing is written: the goal goes back for vetting at the larger depth first.** No planner call happens inside the user's turn (R8). |
| R4 | **An unblocked step was never shown** — undated (`open`) and future-dated (`upcoming`/`later`) one-offs are kept off Today and out of the planner's candidates; only `due_today`, `overdue` and `flexible` (`in_window`) are placed | `tools/obligations.py:2621-2636` `_on_todays_list`; `tools/day_plan.py:584-586` | **Every planner step is written `flexible: true` with a required `due`** (its latest date, scheduled backwards from the end state) and `eligible_from` (its earliest start), so it is `in_window` and the day planner places it on a day with room. Undated steps are refused by the validator. Projected finish is computed from the same windows. |
| R5 | **Each unblocked step cost up to three model calls**: a new candidate is classed "task(s) added" and triggers a reshuffle on the 12/day cap; every step is an unset-stakes deadline, so essential, so one nudge wake plus one check wake of the Synthesizer | `tools/day_plan.py:1387-1389` `_classify`; `tools/obligations.py:1383` `is_essential` | (a) `_classify` does not count as "added" a ref whose task carries `part_of` or `calendar_uid`-from-prep; code places those. (b) Steps carry explicit `stakes`: **prep for an event = essential** (nudge + check — the Red Book should get both); **project steps = `missable`** unless on the critical path within the size-scaled margin of the deadline, then essential. **§ 8 Run corrected:** phase 1 costs ~2 Synthesizer turns per prep (its nudge and its check) and no planner calls. |
| R6 | **A declined, parked or merely proposed goal appeared to every agent as a current goal**; a long-horizon goal was invisible to linking, weighting and sweeps | `core/orchestrator.py:613-617` pastes raw `goals.yaml` into prompts; `tools/obligations.py:1354` hard-codes three horizons; `update_goal` defaults to `active` | **Goals reach prompts through one filter**, in `load_config`/`load_goals`: active goals as now; proposed ones under a short "being considered" heading; parked and declined never; `vetted` records never. `_goal_index` reads `tools/goals.py` `HORIZONS`, which gains `long`. **`update_goal` add from Synth defaults to `proposed` in code**, and its schema lists the new statuses. |
| R7 | **Hidden steps leaked through paths that read raw rows** — the user's own new task refused as "already open as <hidden step>", the >12 one-offs soft cap counting hidden steps, a plan step refused mid-plan by a near-match, leaving later steps' `needs` dangling | `tools/obligations.py:724-762` dedupe guards, `:1272` `_SOFT_CAP`, `:395` `_remerge_v1`; `_view` single-row | (a) `blocked` is computed from a per-load set of open/closed ids passed to `_view` at its ~15 call sites, not inside the single row. (b) The user-facing dedupe guards and soft cap **skip rows with `part_of`**; steps dedupe only against their own plan. (c) **`open_plan(steps)`** writes a whole plan in one `_with_store`, ids minted first, guards per plan, all-or-nothing — a refused step aborts the plan, it is never half-written. |
| R8 | **The reshuffle pattern did not transfer** — that is a scheduler-process worker with single-flight, a daily count, a minimum gap and a locked write; `plan_project` was a tool call inside a user's turn | `tools/day_plan.py:2431-2566`; `core/spend_guard.py:446-480` | **`plan_project` only queues** (a request row on the end state) and returns at once; the project planner runs as a worker in the scheduler's tick, with the reshuffle's four controls: **single-flight per end state, a per-persona daily cap (config, default 6), a minimum gap, a locked write via `open_plan`.** The plan reaches the user as its first step, unseen; "it's planned" is said once, next turn. Re-plans after a dismissal and milestone expansions draw on the same cap. |
| R9 | **Phase 1's dismissal rule called a planner that does not exist until phase 2**, and "optional" was undefined | `tools/obligations.py:1856-1864` | Steps carry **`required` (default true)**. **Phase 1:** dismissing a required step closes what needs it `moot` with reason "its prerequisite was dismissed", and raises the end state once as Important ("X can't go ahead without Y — redo it?"). Dismissing an optional one unblocks. **Phase 2** replaces the close with a re-plan. Live check 1 adds a "Skipped" on step 1 of the test project. |
| R10 | **The dropped-nudge fix (#5) had no design**, and phase 1's live check could not tell fixed from unfixed | `tools/day_plan.py:2631-2692`; `archive/plans/codebase_review_fixes_plan_2026-11-11.md:64` | **Adopt the recorded design:** `_day_plan_block` passes `carried` entries not yet surfaced as DUE NOW and stamps them; the shield narrows to conversational jobs via `shield_jobs:` in `config/modules/day_plan.yaml`; **no change to `core/scheduler.py`**. Its own deterministic test: a prep nudge placed inside the evening close's shield window reaches the 20:00 close under DUE NOW. The live check stays an observation, not the proof. |

**Phase 1 now carries:** the file locks (R1), the network fields with a ledger-wide `blocked`
(R7a), `open_plan` (R7c), the Red Book conversion with stored, re-derived due (R2), placement
without reshuffle and explicit stakes (R5), the phase 1 dismissal rule (R9), and #5 (R10).
**Phase 2 adds:** Synth sizing (R3), the goal filter and `proposed` default (R6), the queued
project planner (R8) writing flexible, dated steps (R4).

**Unchanged by the review:** Mike's rulings (§ 2), the three phases, the playbook design, and the
build budget.

## 11. `mike`'s live goals (Mike, 2026-11-18)

**To be added, each needing definition from Synth through conversation with Mike** — not written
from here (persona config is VM-owned and Denied). They enter through Metatron as `proposed` and
are vetted there:

| Goal | Size | Phase it tests | Definition Synth must get from Mike |
|---|---|---|---|
| **Become better at speaking Bulgarian** | L, long horizon | 3 | what "better" means (a level, a conversation, a person to speak with), weekly time, what it displaces; becomes the parent of the existing daily `d1` Bulgarian Vocabulary |
| **File UK taxes by Dec 31** | M, obligation | 2 | which tax year and return; accountant or not; the documents involved. HMRC's online deadline is 31 Jan; **30 Dec** is the online deadline for having tax collected through a PAYE code, so Mike's date may be deliberate — confirm, don't assume |
| **Complete Prudential insurance review and decisions** | M | 2 | which policies, what decisions, any renewal or provider date |

**Read on the VM, 2026-11-18 (read-only):** 10 goals (daily 2, weekly 5, quarterly 3), all
`active`. Neither the taxes nor the Prudential goal is present. **Four goals have no `id`**
(Healthier Diet, Swim for Manny, Purpose-Driven Exercise, Strength and Flexibility Training), so
`_goal_index` skips them and no task can link to them. **`q2` "Metatron Mark 2 Transition" is
obsolete** (Mark 2 ended today). All of this is for the phase 3 walkthrough, where every existing
goal is talked through; nothing is changed before then.

**Timing:** the tax deadline falls about 6 weeks out, about when phase 2 would land. **Recommended
(Mike to rule):** Prudential is phase 2's live test. The tax steps open now as ordinary tasks
through Metatron, so the filing never waits on this build, and phase 2's `open_plan` adopts open
tasks into a plan (`part_of` on existing ids) when it lands. That adoption is a small addition
to R7c.

**Done 2026-11-18, on the VM, at Mike's instruction ("update those goals manually for mike from
here"):** ids given to the four goals that had none (Healthier Diet `d2`, Swim for Manny `q3`,
Purpose-Driven Exercise `w4`, Strength and Flexibility Training `w5`). The three goals above were
added as `q4`, `q5`, `q6`, each with a `context` line naming what Synth must ask Mike; Bulgarian
carries `timeline: long-term` and moves to the `long` horizon in phase 3. `d1` Bulgarian
Vocabulary now has `parent_goal: q4`. Backup: `config/personas/mike/goals.yaml.bak-2026-11-18`
on the VM. **`q2` converted (Mike, 11-18: "converted into Metatron work, with a specific set of
things to be achieved this quarter"):** now "Metatron work this quarter", due 2027-02-18. Its four
outcomes are a **draft by Claude Code**, flagged in `context` for Mike to confirm through Synth:
the network's three phases live; Iva signed up and using it; WhatsApp messages reaching Metatron;
Build revisited and decided. Second backup: `goals.yaml.bak-2026-11-18b`.

## 12. Stage 1's three live-check misses — cause and proposed fix (2026-11-18)

Read on the VM, 11-12 → 11-18 (synth plan § 11). **Mike's rulings, 2026-11-18:** M1 **leave as
is for the time being** (not built). M2 **"I'd need to see this to comment on it"** — the example
below is shown to him at the start of the phase 1 session; built only on his yes. M3 **revised by
Mike**: *"Tasks pushed day to day should continue to be raised — with recognition that they've
been missed — until completed or dismissed. Synth can prompt user on that."* That replaces the
"asked once after three days" proposal in the table.

**M2, what 11-18's 07:31 brief would have said under the cap** (actual: three new horizon
findings in a row, then 39 contact suggestions):
> *"Mike, Manny's Show and Tell is at 9:00. Right now it's repotting the basement plants, then the
> brokerage backup at 7:50 — that one takes your own time. Two things for today: your
> echocardiogram is tomorrow at 16:00, so travel needs sorting today, and Aisha's Thanksgiving
> invitation for the 26th needs an answer. There are 39 contact suggestions whenever you want
> them. Do Show and Tell and Iva being off from 9:30 need you?"*

The Teams seminar is held back, not dropped: it keeps both of its offers and comes up on a later
turn that day.

**M3 as ruled:** a task carried from one day to the next is raised again every day until it is
done or dismissed. Each time, it carries how many days it has slipped and since when, so Synth
says so ("the repotting has slipped four days — now, or drop it?") and offers dismissal. Code
counts the slips; Synth voices them. The "takes your own time" rider is said once per task, not
once per day (the part of M3 the ruling did not change).

| # | What Mike saw | Cause | Proposed fix |
|---|---|---|---|
| M1 | **Monday's brief (11-16) recited the whole week**, day by day | Working as written: `synthesizer_scheduled_sessions.md` § Weekly review phase 2 says *"go through the coming week's commitments — everything falling in the next seven days… repetition is the point"* (the 09-05 ruling), and `horizon.week_block` hands it the full week | Keep a Monday look-ahead, cut to **the week's shape in one sentence + the one to three things that need something done first or decided now** (phases 1 and 3; phase 2 goes). Done in code too, per stage 1's lesson that a model given data is not reliably stopped from reciting it: `week_block` returns per-day counts plus only items with a deadline, a precursor or a decision. Once phase 1 schedules prep as tasks, even this shrinks. **Supersedes 09-05's "everything in the next seven days" the way S2 superseded its evening-close twin.** |
| M2 | **11-18's brief carried five extras** — three new horizon findings, the 39 contact suggestions, Show and Tell | `horizon.context_block` has **no count cap** and tells Synth to *"put these to the user in this exchange"*, so every undelivered finding arrives at once. The contact-suggestion line is by design (one line, `crm_sweep`) | New findings join the **Important ranking (cap `important_max`, 2)** on the brief and close, ranked with prerequisites and vital deadlines; at most **one** on an ordinary turn. Offers are charged only for findings actually shown, so a held one keeps both its chances. The contact line stays as it is. |
| M3 | **"Takes your own time" repeated daily for the same task**; repotting proposed at 07:30 on four mornings, not done | The rider is "once per task **per day**" (`synthesizer_day_plan.md:11`), and an undone task that the planner has to put into protected time is re-placed there every day. Nothing notices that the same task keeps being carried | **Once per task, not per day.** Plus a task-level version of § 4.2's non-compliance trigger: **a task carried or not done three days running is asked about once** — keep, give it a fixed time, or drop it — instead of being proposed again. Code counts it; Synth asks. |

## 13. Phase 1 built — Fable 5.1 diff review and reconciliation (2026-11-18)

Built in one Opus 5.5 session; M2 on Mike's yes the same day, M3 as ruled, M1 not built. **Fable
5.1 reviewed the full diff: four structural, five local findings. All nine were checked against
the code and fixed before commit;** each has its own test in `tests/test_goal_network_phase1.py`.

| # | What would have gone wrong | Fix |
|---|---|---|
| F1 | A prep left undone the night before was placed after its event the next morning — `before` was set only when the event moved | `(due, before)` re-derived from the event start on every tick; a prep whose event has started closes moot |
| F2 | Slip questions on every turn, uncapped, and asked again after the user gave a time | Asked on the brief and close only, at most 2, once a day per task, only while actionable today; a task that did not fit (unplaced/dropped) counts as slipped |
| F3 | The shield is `abs(now − session) ≤ window`, so a nudge due after a session (07:50 after a 07:30 brief — Mike's 11-18 example) was carried into the past | Carried only while the session is ahead (the scheduler's own scan, called twice; no scheduler change). A carry no session surfaced is sent as itself after 45 min. Carried items are stored at carry time, since their block may have left the plan |
| F4 | On a busy day a same-day finding was held behind two higher-ranked items until it expired | A finding dated today/tomorrow always takes the last Important slot; if the plan block comes back empty, the horizon block delivers uncapped |
| F5 | The "redo it?" question was stamped asked the first time it rendered, as a skippable candidate | It is an Ask, and counts as asked only once a brief or close carried it |
| F6 | A prerequisite that went moot by date closed its plan with nobody told | Raised the same way, worded "ran out of time" |
| F7 | Rescheduling a dismissed step left its later steps closed; reopening a later step alone left it hidden forever | Reschedule restores the cascade; reopening a step stuck behind a closed required prerequisite is refused, naming the step to reopen |
| F8 | The uid GET read one calendar, assumed href = uid, returned a recurring series' first start, and repeated every tick on failure | A 60-day range query over every calendar; "gone" only on a good read; one-hour back-off after a failed read |
| F9 | `open_plan` accepted undated steps, which unblock and never appear (R4) | Every step needs a `due` now, not only in phase 2 |

**Found while building, not by the review:** a plan's end state carries no `part_of` but is hidden
while blocked, so the user-facing duplicate guard also skips blocked rows (R7b). `blocked` is derived
once per load in `_load_doc` rather than passed to each `_view` call site — every reader goes through
it, so none can be forgotten (R7a's intent).

**Not verified, for the live check:** `shield_jobs` ships as `[morning_brief, evening_close,
location_anticipation]` (the template's names). A conversational fixed job on `mike`'s VM under
another name would no longer shield at all.

## 14. Phase 1 live data, 11-18 → 11-21 — four misses fixed, Fable-reviewed (2026-11-21)

Read on the VM (read-only) after three live days. **Working:** three preps opened by themselves
at deploy (Bupa pre-authorisation, echo travel, Aisha's reply), placed and nudged before their
events and closed when the events started; a 07:00 and a 19:30 nudge were carried into the
07:30 brief and the 20:00 close; the 11-19 brief said "the George School donation has slipped
three days"; briefs carried one new finding, not a flood. Checks 2 and 4 replayed on a throwaway
copy of `mike`'s data with this code: 17/17 (two replay-script checks miscounted semicolons in the
line headers — the lines themselves were right). **Missed, and fixed:**

| # | What the user saw | Fix |
|---|---|---|
| L-A | The Bupa prep had no "before 15:30" on the appointment day (placed before it by luck) | `_prep_due` sets `before` on the event day even when the finding has its own `precursor_by` |
| L-B | 11-20: four slips marked asked, none said at the brief or close | Say-once items (slips, rider, redo question) are recorded as offered at render and stamped only when the reply names the task AND carries words of that question (`note_said`, `_SAID_SIGNALS`); offers are a list with a 15-min window; slips rotate least-recently-offered first |
| L-C | Two findings spent both offers across five nudge wakes, unsaid | No findings, redo questions or horizon block on a day-plan nudge wake |
| L-D | A 09:35 "leave now" for a 10:00 meeting was held for the 10:00 session and never said | A travel nudge is never held by the shield — it goes out on time; a carried one 20 min past its moment is dropped, never said late |
| L-E | `manny_school` (Sun 16:00) missing from `shield_jobs` | Any fixed `agent: coordinator` job shields; `shield_jobs` only adds names (now `[]`) |

**Fable 5.1 review of that fix:** two structural, four local. Accepted and fixed: a carried travel
nudge could be said after its meeting started (→ L-D's on-time rule); naming a task was counted as
asking about it (→ the signal words); unsaid slips blocked the rest (→ rotation); one shared offer
slot (→ the list). Noted, not fixed: the stamp is taken before the confidentiality filter, as
`note_raised`'s already is. Checked, no change: the shield now rests on each job's `agent` field —
all four of `mike`'s conversational jobs are `agent: coordinator` (read on the VM 11-21).

**Still owed live:** a prep following a moved event (no real event moved); Synth actually asking
the redo question at a brief.

## 15. Phase 2 built — Fable 5.1 diff review and reconciliation (2026-11-21)

Built in one Opus 5.5 session. **Mike's rulings that session:** taxes (not Prudential) is the live
test; the taxes playbook researched by the Research Agent (decontextualised question; a few cents, not metered) and
reviewed by Mike before it lands; the Red edits approved; and on dismissal — *"a check on whether
the skipped step was skipped intentionally or accidentally. If it's clear that the later step
couldn't have been completed without the earlier one, then both should be considered completed"*
— built light: a done later step closes its required prerequisites done, and the brief asks "on
purpose or by accident?". **R9's automatic re-plan on dismissal was not built** (Mike: only if it
does not overcomplicate the phase). Also built: a precursor stated in chat is linked to its event
and follows it, and a later finding adopts it (the 11-21 gap); the close gate hears "the prep",
and its refusal tells Synth never to explain itself (live finding 11-21). The redo-question stamp
defect from the live check was fixed separately (`9ad7a6c`).

**Fable 5.1 reviewed the full diff: four structural, six local. All ten were checked against the
code and fixed before commit;** each has its own check in `tests/test_goal_network_phase2.py`.

| # | What would have gone wrong | Fix |
|---|---|---|
| F1 | "I did the skipped step after all" could only be recorded by marking the END done — closing every step in between | Done on a dismissed step that stopped others is allowed: it closes done and its later steps come back; the question names each later step's id |
| F2 | Any deadline task sharing one word with an event in the next two days ("Buy Manny new shoes" beside "Manny swim") was re-dated and closed itself when the event started | A link needs two shared words, or one plus words pointing at an event ("to tomorrow's appointment"); a user's own note is never overwritten |
| F3 | A planner size-up left the goal active, M, vetted and unplannable — `vet` refused L, the sweep skipped it, a re-queue drew the same answer | Vetting it L (short pass) gives it weekly time; re-queuing it as M after a size-up is the user confirming the size, and is planned as M |
| F4 | Every recurring goal stated in chat stayed "being considered" with no path to current until phase 3 — a regression from today | § 4.2's L row: Synth's short pass (`displaces` + `priority`) takes it on as L, with weekly time, never steps; the Interviewer's full pass stays phase 3 |
| F5 | The part of a finding's precursor the adopted chat task did not say lived only in a note the event-day rewrite erased | Kept on `prep_for.also` and carried into every rewritten note |
| F6 | A failed model call (spend refusal, Vertex error) was filed as "couldn't plan" and never retried | Re-queued after an hour, up to three tries, before the user is told |
| F7 | "It's planned" was stamped said only when the reply used a word of the title — else re-said every turn for three days | The only notice on offer is stamped by the plan words alone; any notice is let go after three offers |
| F8 | An adopted task kept its own earlier date while taking the plan's later window — hidden, then back overdue | Its date stands only if it fits the window and its prerequisites; otherwise the plan's, with a history row |
| F9 | A worker past the stale window could write after a restart had taken over | The generation is re-checked under the lock before the write; stale window 300 → 600 s |
| F10 | The UK playbook attached to anything with "tax" in it (car tax, council tax) | Every word of an `applies_to` phrase must be present, matched as plain words; phrases are specific (`UK taxes`, `self assessment`, `SA100`) |

**Checked, no change:** the Synthesizer stays far above the 4,096-token cache floor (~11.7k
tokens; +~430 this phase, ~$0.01/day of cache storage). **Live planner pass (`METATRON_LIVE=1`,
~$0.02):** valid, M, eight 30–45-minute steps following the playbook, submission 28 Dec for a 30 Dec
date. **Not verified, for the live check:** the size Synth gives a real stated obligation, and
whether it calls `vet` then `plan_project` in the same turn.

## 16. Ranking — every task weighed, plan steps never missable, deadlines that climb (2026-11-22)

**What the live check found (11-22).** The tax plan was written well (9 steps, sign-in check first,
submission before the 30 Dec PAYE cutoff), but its first step never reached the day: 9 stale
overdue chores with no `stakes` scored 55 each (base 15 + vital-overdue 40), because F10 counted
unknown stakes as vital; the plan's early steps were `missable` (R5's two-day critical margin)
and scored 20; nothing climbed before the last two days; and the step was cut from Synth's Tasks
section by the 6-line cap, so *"I checked my HMRC sign-in, it works"* closed nothing.

**Mike's rulings, 2026-11-22 (verbatim where quoted):**
1. *"Tasks should be scored always, and if not vital should have a weaker score and be relegated
   to back burner. Many times user will add tasks that aren't important and quickly forgotten.
   That said, Metatron should check new tasks against user goals and core values to ensure
   appropriate ranking. If someone is a passionate gardener, repotting the plants is likely more
   important than for the weekend warrior."* — and it is the general picture, all task streams,
   not taxes.
2. *"I don't think any of the steps in filing the taxes are missable."*
3. The ramp — *"temporal dilation is a key part of how we can emphasize the right, or the wrong
   things. Sometimes even an urgent deadline is less important if the underlying task gets in the
   way of, say, family time. This will require a deeper interview conversation to do properly."*
4. Judging reflects *"general life realities. Taxes might not align with mission, but still are
   high priority."* Costs of missing a task — *"financial — easy to quantify, social — much
   harder, existential/psychological — harder still"* — inform the weighing.
5. *"Metatron should proactively manage tasks and prioritization with the user, as well as by
   itself on the backend. That reconciliation is a core strength of the intended tool. Metatron's
   mission is to emphasize what will lead to long term happiness, not managing a to do list."*

**Part A — built this session (mechanism; no weights invented):**

| | What | Where |
|---|---|---|
| A1 | Unjudged = back burner: `is_essential`, `_score`, the candidate `vital` flag read only `stakes == "vital"`. F10's "unknown counts as vital" is amended, its safety moved to A3/A4 | `obligations.is_essential`, `day_plan._score` |
| A2 | Required steps take the end state's weight (`_end_weight`): vital unless the end was judged missable or taken on at `low`; optional steps missable; priority inherited; R5's margin retired; code preps vital explicitly | `obligations._end_weight/_step_weight`, `open_plan` |
| A3 | The judging rule in ONE home — open_task's `stakes`/`priority` descriptions, read by every agent that opens a task — plus `stakes_why` | `_PLAN_FIELD_PROPS` |
| A4 | The net: `task_judge` judges unjudged deadlines off the tick (single flight, 6/day, 10-min gap, one locked write, never over a stated value or one judged meanwhile) | `tools/task_judge.py`, `config/agents/task_judge.md` |
| A5 | The ramp: a deadline climbs linearly from its window's start to its due-day weight over ≤ `ramp_days` (14) | `day_plan._ramp`, `day_plan.yaml score.ramp_days` |
| A6 | A plan's current step is never cut from Synth's Tasks section by the cap | `obligations.context_block` |
| A7 | `vet` priority is high/normal/low (free text refused; what it ranks above → `displaces`); `kind` recordable at vet | `goals.vet_goal`, synthesizer.md |
| A8 | Daily `reweigh_plan_steps` (and the first tick after deploy) migrates steps written under R5 | `refresh_tick` |

**Costs.** *Build:* one Opus session + Fable diff review. *Run:* the judge, ~$0.01 a call (≤25
tasks; 3.8 Flash, thinking capped 1,024), capped 6 answered calls a day → ≤ ~$0.06/day (~$0.12
after the intro price); typical is one call on deploy day, then rare. The ramp and reweigh are
code. *Ancillary:* (1) every required plan step is now vital. Inside its window it is not
essential, so nothing wakes early; from its last day, each day it stays open can wake the
Synthesizer twice (start nudge, end check), ~$0.01 a wake — an on-time step costs ~$0.02, a
neglected one ~$0.02 a day until done. R5 had avoided exactly this. (2) A verdict that moves a
score 10+ can make the next build a day_planner reshuffle, under `reshuffles_per_day`. *Unseen:*
a real obligation judged missable fades the way trivia should, silently. Guards: the obligation
rule in both the schema and the judge's file, and the back-burner review with Mike.

**Deploy-day transition.** Nothing disappears. A task with no stakes is back burner only while it
awaits the judge (`_JUDGE_GRACE`, 60 min from when it was opened); every existing task is older
than that, so each reads as vital — exactly as before — until the judge weighs it: the first
tick after deploy, 25 at a time, most urgent first, 10 minutes apart. The first tick also runs
the one-time `legacy` reweigh, moving the 11-21 tax plan's R5 values to the new rule. Its steps
become vital at once; the overdue ones may nudge that day.

**Part B — needs Mike's interview first (not built):** values-weighted ranking (passions raise
their tasks; protected time — family — outranks a deadline that would cut into it), the ramp's
shape per kind of thing, cost dimensions as recorded fields rather than one-line `why`, and
Metatron proactively reconciling priorities with the user (a recurring conversation) and alone
(the backend). Its planning chat's prompt: `archive/handoffs/2026-11-22-ranking-part-b-interview-prompt.md`.

**Fable 5.1 diff review (2026-11-22) — 16 findings, all accepted:**

| # | Finding (what a user would see) | Resolution |
|---|---|---|
| F1 | A failing judge (outage, spend stop) left a real overdue bill hidden all day; failures used up the cap; a garbled reply re-offered the same 25 forever | `stakes_of`: unjudged past `_JUDGE_GRACE` reads vital again; a failed call refunds the cap; an empty pass halves the next batch (≥5) |
| F2 | The daily reweigh undid what Synth recorded from the user ("that step doesn't matter much") | plan-set values carry source `plan`; only those move; R5's `inferred` values move once (`legacy`) |
| F3 | The judge's priority flattened a goal-linked task's edge | the judge never writes priority on a task linked to a known goal |
| F4 | The live tax steps ranked like errands (free-text vet priority read as none); `kind: obligation` ignored; `_score` never read a goal's vetted priority | `_goal_priority`: obligation → high; `_score` uses it for every goal-linked task |
| F5 | More than 6 steps re-hid the current step; "+N more" undercounted | per-plan allowance (3) beside the cap, in list order; every cut counted |
| F6 | Deploy-day backlog judged oldest-first | most urgent first |
| F7 | A judged-missable end left its steps vital until tomorrow | a judging pass, and a re-vet, reweigh at once |
| F8 | An unreadable store marked the reweigh done | stamped only on an int result |
| F9 | Nudge cost understated | corrected above |
| F10 | A verdict can cost a reshuffle, unnamed | named above and in `task_judge.py` |
| F11 | Judge input nearer 4–6k than 3k | immaterial at this tier; noted |
| F12–16 | Tests not proving their claims; missing cases | test 2 asserts the exact climb; new checks for the grace, refund, batch halving, urgency order, goal priority, month-window judging, per-plan cap and count, re-vet reweigh — `tests/test_task_ranking.py` 18/18 |
