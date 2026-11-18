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
