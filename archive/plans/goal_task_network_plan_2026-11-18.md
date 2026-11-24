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

**After the deploy (2026-11-22, live checks 1–3).** 1 passed (16 tasks judged in one pass, ~$0.01;
stale chores off the top, none closed). 2 passed (*"The taxes are high priority — they're an
obligation"* re-vetted q5 as an obligation at `high`; all 9 steps vital + high at once). 3 half:
Synth saw the sign-in step and closed the right id, but the close gate tied it with *"Log in to
HMRC and complete the tailoring questions"* — a step still waiting on it — on the one word
"hmrc", so Synth asked the obvious. Fixed: a blocked or not-yet-eligible task is no rival.

**Mike's further rulings, the same day — for Part B:**
6. A task's shape is probed **when it is mentioned**: *"their shape and edges should be figured out
   by Synth in communications"* — the real deadline behind the stated one (*"the GS donation needs
   to be done before the donations for this year's annual fund close out at the end of
   November"*), a decay window (*"potting plants might have a window of two weeks before the
   plants die"*), an emotional component *"yet unearthed"*.
7. *"Urgency and importance are two different vectors that are being consolidated into a single
   score."* Part A's score folds both into one number; Part B separates them.
8. *"Disappointing a parent is likely vital, not missable"* (social cost); *"Personal trainer is a
   goal step"*; the brokerage backup and the insurance review confirmed vital. Recorded through
   the back-burner walkthrough (check 4), so the corrections land as Mike's own (`stated`).

## 17. Phase 3, part A built — large goals in waves, finish dates watched, goals re-checked (2026-11-24)

Built in one Opus 5.5 session from `archive/handoffs/2026-11-23-goal-network-phase-3a-build-prompt.md`.
**Every new behaviour is behind its own flag, all OFF; nothing deployed.** Fable 5.2 reviewed the
diff (six structural, eleven local findings, all reproduced or reasoned against the code, all
fixed — table below).

**Mike's rulings this session (2026-11-24):**
1. **Where a re-vet lands:** one line in the weekly look back, at most one goal a week (option a).
   *"As rec, but let's move the cap on the weekly to 5 questions."* — `ranking.yaml`
   `weekly.questions_max` 2 → 5, which also lets more of the ranking's slipping questions through.
   It had been 2 since the ranking's Fable review (#7: five questions in a first look back reads as
   being managed); Mike ruled with the cap named.
2. **When an L goal is planned:** *"Wait for full pass. 2 questions isn't nearly enough for an L
   goal."* — rolling wave plans only an L goal whose `vetted.pass` is `full`, which only the Goals
   Interviewer writes (read from the call trace) and only while `rolling_wave` is on. **Part B's
   re-interview is the only path that will write it; until then rolling waves are inert for every
   real goal**, and `rolling_wave` must not be switched on before part B lands.
3. **The language playbook** is left to the end, with Mike involved — the end of this chat or a
   new one. No dependency was missed: rolling waves plan without a playbook, and the attaching
   code (`applies_when`) is built and tested against a stand-in.

**Built.**
1. **Rolling wave** (`rolling_wave`; `tools/project_plan.py`). `plan_project` accepts size L for a
   fully vetted goal with weekly time (argument, or `weekly_minutes` on the goal). The planner
   (Red: `project_planner.md` § A large goal) returns `milestones` — outcomes, each a window and a
   total estimate, no 90-minute cap — and steps for the first only. **Deviation: outlines live on
   the plan record (`projects.json` → `requests.<id>.milestones`), not as hidden `part_of` rows**,
   so no task-list reader can place, show, judge, park or dedupe against one (the R7 leak class);
   only the current milestone's steps are rows, as § 8 Ancillary asks. `advance_waves` (every tick)
   queues the next expansion on the same queue, worker and daily cap when the current milestone's
   last step closes with at least one done; with none done it is **stalled** (no more steps for a
   user ignoring these; the re-vet asks), and steps closed by the goal's own parking re-plan the
   milestone on re-activation. An expansion is said to no one. A failed expansion retries the next
   day (3 tries), then is said as "the next stage". A late milestone keeps its length (its window is
   moved and recorded). `read_plan` lists the outlines. An L goal keeps its weekly time
   (`allocation_gaps`) while planned. The sweep plans a fully vetted L goal once.
2. **Projected finish** (`projected_finish`; `tools/goal_network.py`). Daily: open steps in
   prerequisite order, then outlines, one at a time at the weekly time given (else 150, then the
   pace actually kept once two steps are done — estimated minutes of done steps per week since the
   plan began; **not for L**, whose milestone minutes include practice no step records). Waiting
   (`eligible_from`) and prerequisites respected. Said once, as an Important line in the day plan
   block, when it crosses the goal's live date; said again only when the work grew or the pace fell
   AND it moved later by more than `finish_margin_days` (M 3, L 14), at most twice a crossing; an
   undated L goal only on such a slip. One fix: minutes a week, or a date when waiting alone runs
   past it, when no extra time is needed, or when the need is implausible. Never said on a
   `default` pace. Stamped said only inside the 15-minute offer window, naming the goal and carrying
   the date or the fix.
3. **Re-vet triggers 1 and 2** (`revet`; `tools/goal_network.py`, `tools/ranking_review.py`).
   Trigger 1: a goal's steps slipped (the day planner's slip record, which now keeps its recent
   dates), were dismissed, got "not yet" (the tap log now carries the task id), or a matching
   intention was judged unfulfilled by the Accountability Index — on 4 distinct days in 7 (the
   basement-plants evidence, § 4.2) — or a milestone stalled. Quiet until answered or 28 days.
   Trigger 2: L goals at 14 and 42 days from when they were **taken on** (`taken_on`, not moved by a
   "keep"), then every 91. Obligations never get trigger 2, and trigger 1 asks only about their
   date and what would help. Each fires once per checkpoint; one goal a week goes into the look
   back as `GOAL CHECK`, first among its questions, replacing a guarded question about one of that
   goal's own tasks; a show counts once per week; let go after 3 weekly reviews unsaid. The answer
   is `update_goal vet` (or a new `due` for an obligation). `revet_asked` / `revet_answer` rows go
   to `ranking_signals.jsonl` (`source: goal_network`, ids and counts only), behind
   `ranking_signals`. Conduct: one sentence in `synthesizer_scheduled_sessions.md` § Weekly review.
4. **The playbook matcher:** `applies_when: a, b | c, d` — a word (or a phrase with a space) from
   every group — so one language playbook covers every language; "public speaking" and "Bulgarian
   taxes" do not match.

**Config home:** a `goal_network:` block in `config/modules/day_plan.yaml`, beside the project
planner's limits — one file the loader already re-reads on change, not a new one.

**Tests.** `tests/test_goal_network_phase3.py` 41/41 (fixture personas, every meter stubbed; one
check per review and verify finding). Phase 1 38/38, phase 2 36/36, `test_ranking_v2.py` 58/58 (the cap check
now pins its cap at 2 to test the mechanism, and asserts 5 ships), `test_task_ranking.py` 21/21,
the fixture runner 7/7, QA sweep 12/12. Known clean-HEAD failures unchanged: round-2 F8,
`task_ledger_consult`'s dated event, the multi-user push `KeyError`. **Live planner pass**
(`METATRON_LIVE_WAVE=1`, two reasoning-tier calls on a fixture goal, ~$0.05): a first wave of five
outcome milestones and six steps, then an expansion of seven steps inside the second milestone's
window — both valid.

**Fable 5.2 diff review — all accepted and fixed:**

| # | What a user would see | Fix |
|---|---|---|
| S1 | Two steps of a large goal done, and next day "it has slipped by months" | L pace is the weekly time given, never step minutes |
| S2 | A finish alert recorded as said when the reply never said it ("we can look at the garden later") | offer window; title word plus a date or the fix; generic words dropped |
| S3 | Moving the date — the alert's own advice — did not stop the alert | the end state's live date, read daily and in the planner's payload |
| S4 | An untouched late plan re-alerted every 4 days, asking for 1,425 more minutes a week | a re-alert needs more work or a slower pace, at most twice a crossing; implausible needs become a date |
| S5a | Planning a stalled L goal again erased its milestone map | an existing map is kept; the stuck milestone is expanded |
| S5b | A failed expansion said "could not be broken into steps" about a goal already under way, and froze | retried next day, three times; then said as the next stage |
| S6 | One "keep" pushed the next check-in from six weeks to most of a year | anchored to `taken_on`, which a keep does not move |
| L1 | A new crossing never shown after an earlier unsaid alert; a stale alert read out after recovery | offers reset per crossing; back on time withdraws it |
| L2 | A tight plan with no weekly time given alerted on day one with an invented history | no alert on a default pace; no "more minutes" when none are needed |
| L3 | Re-taking a parked L goal asked "none of its steps got done?"; parking dropped the full pass | park-closed steps re-plan the milestone; the pass is carried through |
| L4 | A milestone's steps could appear weeks before it starts | step `eligible_from` ≥ the milestone's |
| L5 | One slip this week plus three six weeks ago read as "4 of the last 7 days" | the slip record keeps its dates; an old count is a run only if it fits |
| L6 | An `at_risk` goal was never asked about | `goals.CURRENT` |
| L7 | The goal check vanished after one review rendered it three times | one show per week |
| L8 | Re-vet rows written with `ranking_signals` off | gated |
| L9 | Three flag-off differences from phase 2 | `allocation_gaps` and the `full` marker gated on `rolling_wave`; the cap is Mike's ruling |
| L10 | The weekly conduct asked an obligation whether it still fits; a new date never recorded as the answer | conduct carries the exception; a `due` change answers it |
| L11 | Checks whose names claimed more than they proved | each finding has its own check, the plants now through the real slip recorder |

**Fable verify pass (same reviewer, re-ran its reproductions):** 17 of 19 fixed. Found and fixed:
(N1) the L2 fix silenced every alert on a default pace, so an ignored M plan with no weekly time was
never told even past its date — now said once on hard facts only (the date passed, a step past its
own date, or the waiting alone runs past it), with a new date as the fix and no pace claim; (N2)
"maybe", "decide" and "mark" still read as month names — an alert now counts as said only with its
OWN new date (weekday in full, or day number with its month) or the fix's words; (N3) `plan_project`
in the minutes before a tick could re-plan a finished milestone — it now closes it and plans the
next; (N4) `read_plan`'s header showed the queued date — now the live one.

**Tier note:** agent files left the Red tier on 2026-11-24 (Mike, another chat, `10000b5`), so the
`project_planner.md` edit is Amber; it was still made in the main session, never delegated.

**Inert with every flag off, but not byte-identical to phase 2:** the slip record gains `recent`;
the "not yet" log row gains `ref` (an id); `vet_goal` writes `taken_on`; `applies_when` is read if
a playbook carries it (none does). Nothing reads any of them with the flags off.

**Costs.**
- *Build:* this session (Opus 5.5, high) plus the Fable review and verify — within the prompt's
  ~$40–80 + ~$15–30.
- *Run:* rolling wave — one reasoning-tier planner call per milestone (~$0.02–0.04; a retry at
  most doubles one), a few a month per L goal, under the existing `project_plans_per_day` (6).
  Projected finish and re-vet detection — code, zero tokens. A finish alert adds ~60 tokens to a
  brief; a goal check ~100 to a weekly-review turn the user already has.
- *Ancillary:* a few hundred bytes per plan on `projects.json`, rewritten daily; the slip record's
  14 dates per slipping task; a few signal rows a month. The cap at 5 lets up to three more
  questions into a weekly review.
- *Unseen:* a false "late" or an unwanted goal check costs the user's attention, which no meter
  reports — bounded by one alert per crossing (two re-alerts at most), no alert on an invented
  pace, one goal a week, and let-go after three reviews.
- *What persists:* milestone outlines, finish state and re-vet records on the plan record, owned by
  their plan request and inert when the flags are off; nothing bills by time.

**Not verified, for the live check** (`archive/handoffs/2026-11-24-goal-network-phase-3a-live-check-prompt.md`):
whether Synth says a finish alert once and in its own words; whether a goal check is put as a
question; the real pace on `mike`'s tax plan; and, after part B, a real L goal over two weeks.
**Not built (part B):** the Goals Interviewer's re-interview, trigger 3, the `mike` goals
walkthrough — `archive/handoffs/2026-11-24-goal-network-phase-3b-build-prompt.md`.

## 18. Phase 3, part B built — a large goal talked through properly, and how things turn out against how they were looked forward to (2026-11-24)

Built in one Opus 5.5 session from `archive/handoffs/2026-11-24-goal-network-phase-3b-build-prompt.md`.
**Both new behaviours are behind their own flag, OFF; nothing deployed.**

**Mike's rulings this session (2026-11-24), asked before any code:**
1. **How a talk starts:** *"As rec. The talk itself is the first task within the project."* Synth
   offers it once when a goal is sized L ("now, or whenever you say?"); a yes starts it in the turn.
   The talk is a task under the goal, placed and nudged like any step — so a "later" is never lost,
   and no scheduled job is used (six-job cap).
2. **What the talk records:** *"Five fields is a good start, but the facts can't all be user
   generated. The goal itself should be developed and research by Metatron so that the rendering of
   the goal is realistic."* Then, on the design: *"the goal might already have a shape within
   Metatron (taxes, language learning) to start from."* So: `displaces`, `priority`,
   `weekly_minutes`, optional `due`, `done_means`, plus `starting_point` and `effort_hours`; the
   talk starts from a playbook when one applies, else one guarded public lookup; code does the
   arithmetic.
3. **Depth:** *"Focused to start. If more is needed then a continuation can be offered, or a second
   talk scheduled with user."* About 8–15 turns; a second talk is the same task re-dated to the day
   the user picks.
4. **Trigger 3:** *"This isn't just a long term metric. Example: someone whose spending is out of
   control can benefit from the realization that the anticipation of buying something, even if only
   an hour, and the let down after receiving it are a mismatch. This needs to be a holistic, and
   targeted approach that is both metric for Metatron and occasionally lesson for the user - good or
   bad."* And: *"Spending was just an example, and sits first and foremost with Finance and Synth."*
   — no wellbeing routing. *"Proceed as written."*

**Built.**
1. **The talk task** (`goal_talk`; `tools/goal_talk.py`). A goal sized L by Synth (add, update or
   its short-pass vet) gets one task under it — *"Talk through: <goal>"*: `part_of` the goal, 30 min,
   flexible, due in 14 days, `missable`, `source_id: goal_talk:<id>`. The daily sweep (inside
   `sweep_unplanned`) gives an existing L goal its task once (`mike`'s `q4` predates the build); a
   skipped one is not reopened. **A Done tap or a "done" never closes it** — its verdict does, in
   code (`tools/obligations.py`); skipping still works. The one exception to phase 2's "a proposed
   goal is never decomposed" is this task: the talk is the vetting.
2. **The talk** (`update_goal action=talk`, Synth). State in `data/personas/{p}/interview/goal_talk.json`,
   apart from the first interview's `state.json`, so nothing that reads that file sees it. While
   active, the user's own messages on `/ws` go to the Goals Interviewer with that talk's turns as
   history (`core/server.py`, channel `goal_talk:<talk id>`); right after Synth's one-line hand-over
   the Interviewer opens it as a proactive turn. Scheduled sessions run as usual. One talk at a time;
   a second goal's talk pauses the first. `pause_interview()` pauses a talk (the Safety section and
   "let's stop" reach it with no new grant); a talk quiet for 6 h lapses on read; saying yes again
   resumes the same talk. Each turn carries a code-built **GOAL TALK** block: the goal, what is
   recorded, what is still to settle, the arithmetic, the user's week (aspirational baseline, day
   shape windows and routines), and what the talk started from.
3. **Realistic** — the starting shape, made once per talk: the playbook when `_playbook` matches,
   else one lookup through `tools/lookup_guard.py` `ask_public` (now the one guarded path, shared
   with `lookup_public_fact` — same guard, same 5-a-day cap), asking only a generic subject code
   picks from fixed lists — never the user's words (review S5). **Arithmetic is code** (`realism`): the effort
   at the weekly time, and the minutes a week the date needs.
4. **The verdict** (`vet_goal`). In a talk, the Interviewer's `active` needs `weekly_minutes` and
   `done_means` and at least 4 of the user's own messages in the talk (review S2); it stores them
   with `starting_point`, `effort_hours` and `due`, writes `pass: full` (the talk alone licenses
   it, whatever `rolling_wave` is), ends the talk and closes its task done. Parked or declined
   carries the old pass. Synth's vet
   never writes `full`, even mid-talk. The planner's payload gains `done_means`, `starting_point`,
   `effort_hours` and, when no playbook, the looked-up text as `researched`
   (`config/agents/project_planner.md`, one bullet). Then part A's sweep plans it in waves.
5. **Anticipated vs experienced** (`satisfaction_gap` and `ranking_signals`; `tools/satisfaction.py`,
   tool `note_expectation`, granted to the synthesizer in both routing files). Classes: purchase,
   outing, trip, social, activity, commitment. **Heard first**: what the user volunteers is kept at
   no cost. **Asked rarely**: one question a week across both kinds, only for a targeted class — one a
   current goal's title names, purchases while a budget is over, or a class whose pairs already
   lean; "how was it?" the day after (a purchase 3 days after), offered on two days at most. **Metric**:
   per class, n, average before/after, gap, consistency — in the tool's result as evidence from 3
   pairs, and to Finance beside its figures for purchases (`HOW PURCHASES LAND`). **Lesson**: at 4
   consistent pairs (gap ≥ 1 point), when the next one in that class comes up, Synth puts it once as
   a question, good or bad; at most once every 30 days. Rows: `satisfaction_anticipated`,
   `satisfaction_experienced`, `satisfaction_lesson` in `ranking_signals.jsonl`, `source:
   goal_network` — ids, class, scores and the user's own words only.

**Agent files** (all edited in this session, none delegated): `goals_interviewer.md` § Talking one
goal through (new) and two tool lines; `synthesizer.md` — the L row's offer sentence and one tool
bullet; `project_planner.md` — one bullet. Routing (Red): `note_expectation` to the synthesizer,
both files.

**Config:** `goal_talk` and `satisfaction_gap` flags; `goal_network.talk` and
`goal_network.satisfaction` tuning in `config/modules/day_plan.yaml` (code carries the same
defaults).

**Tests.** `tests/test_goal_network_phase3b.py` 31/31 after review and verify (fixture personas; the Interviewer's model,
the lookup, the planner and every other meter stubbed). Part A 41/41, phase 1 38/38, phase 2 36/36,
`test_ranking_v2.py` 58/58, `test_task_ranking.py` 21/21, the fixture runner 7/7, QA sweep 12/12.
Known clean-HEAD failures unchanged: round-2 F8, `task_ledger_consult`'s dated event, the
multi-user push `KeyError`. **Not tested offline:** the `/ws` routing and the proactive opening in
`core/server.py` (exercised by the walkthrough's step 3).

**Costs.**
- *Build:* this session (Opus 5.5, high) ~$50–90, a little over the prompt's $40–80 for the research
  step and the broader trigger 3; the Fable review and verify ~$15–30.
- *Run:* a talk — one Interviewer session per L goal, ~8–15 reasoning-tier turns (~$0.05–0.15), plus
  at most one grounded lookup (~$0.01–0.04, inside the existing 5-a-day cap; none when a playbook
  applies); rare. Trigger 3 — zero model calls; its block adds ~40–90 tokens to Synth's input while
  on, the purchase line ~40 to Finance's.
- *Ancillary:* one small state file per user per feature; one task row per L goal; a few signal rows
  a week.
- *Unseen:* attention — a talk is long by design (bounded: one offer, a skippable task, one goal,
  focus); trigger 3's questions (bounded: one a week, targeted, a lesson a month at most). No meter
  reports either.
- *What persists:* `goal_talk.json` (finished talks move to `past`, capped at 20) and
  `satisfaction_state.json` (offer days, the last lesson date) — both owned by their module, inert
  with the flags off, nothing billed by time.

**Inert with both flags off, but not byte-identical to part A:** `lookup_public_fact`'s wrap now
reads its source from a parameter (same value); `pause_interview`'s schema description names a goal
talk; `vet_goal` and `update_goal` take new optional parameters that are ignored while off.

**Fable 5.2 diff review — 8 structural, 12 local; all checked against the code, all accepted and
fixed** (13 reproduced by the reviewer, 7 reasoned; one check per finding in
`tests/test_goal_network_phase3b.py`, now 26/26):

| # | What a user would see | Fix |
|---|---|---|
| S1 | Saying yes to a talk got no opening, then every message came back as an error for up to six hours — the server's threads bind no persona | every talk read binds the persona; a check runs a turn on an unbound thread |
| S2 | A large goal planned onto their days without being talked through — a talk parked at its first message, or an Interviewer "yes" in the opening line, wrote the full pass | `full` only on `active` in an active talk after `min_user_turns` (4) of the user's own messages; parked/declined carry the old pass |
| S3 | Held in a talk about a goal that no longer exists; a scheduled turn could start a talk with no yes | a talk ends when its goal is closed, removed or made smaller; `talk` needs the user's own turn |
| S4 | The goal's weekly time vanished, "is this still wanted?" within a week (the talk task cannot be ticked off, so it "slipped" daily), and a goal resized to M could never be planned | the talk task is not a plan step to `has_plan`, the sweep, adoption or trigger 1; a goal that stops being one to talk through closes it; the Done refusal is flag-gated |
| S5 | The user's own goal wording went to search grounding ("…before my daughter's wedding" passes the identifier guard) | the lookup asks a generic subject code picks from fixed lists (a language, an instrument, a few kinds of training) — nothing else is looked up |
| S6 | Flags off, Synth could still spend a tool round on a tool that only says "not switched on" | the tool's description confines it to turns carrying the block, which exists only while on (schema kept registered: the grant check requires it — `lookup_public_fact` is the precedent); `pause_interview`'s schema is part A's when off |
| S7 | "We'll carry on Thursday" and nothing happened Thursday | `pause_interview(resume_on)` brings the talk task back that day |
| S8 | "One question a week" held only if the user answered and the model labelled it | invitations stamped by day on the user's own turns; after 2 days in a week, listen only |
| L1 | A quick reply after the yes got two Interviewer answers and two paid lookups | the opening is claimed atomically; the shape is claimed before the lookup |
| L2 | Starting a second goal's talk wiped the first | paused talks are kept per goal and resumed with their history |
| L3 | Tapping Done showed a tool name in the app | user-worded refusal; the talk row has no Done button |
| L4 | Synth told to offer the talk on every result | offered only when the task first appears |
| L5 | A long lookup lost its closing outside-content tag, leaving the user's message inside it | cut before wrapping |
| L6 | "10,000 hours" read as 10 — "weeks away" | separators, ranges and hour units parsed |
| L7 | "How it turned out" paired with the wrong thing (one shared word, another class, a future trip) | same class, already happened, most distinctive words; else kept unpaired |
| L8 | The Interviewer waited for a shortfall line that never came | the arithmetic says whether their time reaches their date |
| L9 | Flags off, one result sentence differed from part A | gated |
| L10 | "Let's stop" in the first interview could pause a goal talk instead | the first interview is checked first |
| L11 | Messages over REST during a talk went to Synth | 409 while a talk is active |
| L12 | A due "how did it turn out?" could expire unasked, stamped by a scheduled build | stamped only on user turns |

**Fable verify pass (same reviewer, re-ran its reproductions):** 16 of 20 fixed, 4 partly, 5 new
from the fixes — all fixed except where stated:

| # | What a user would see | Fix |
|---|---|---|
| S2′ | Mid-talk, the Interviewer vetting a *different* L goal gave it the full pass (rolling wave on) | while `goal_talk` is on, the talk is the only route to `full` |
| S8′/N3 | The ask budget was spent on the first chat days of each week, so a purchase's "how was it?" waited five days; or a question could repeat on the first day | only a specific "how did it turn out?" spends the budget (by day, user turns only); the standing "you may ask when one comes up" line spends nothing |
| L1′ | A message typed while the opening was generating got a reply that ignored the opening | talk turns are serialised per user; the later one is given the opening as history |
| N1 | The looked-up guidance about the wrong thing ("Polish my CV" → learning Polish; "run my own business" → marathon training) | a subject only as the object of a learning verb or in a fixed phrase; "English speaker" dropped |
| N2 | Bulgarian's swept talk task sat on the list with nobody offering the talk | Synth offers it when a *Talk through: …* task comes up in the day |
| N4 | A momentary unreadable goals file ended a talk for good | goals written atomically; an empty or unreadable read is "unknown", never "removed" |
| N5 | "3–4 months at 5 hours a week" read as 3–4 hours of effort | a range counts only in hours or alone; hours *a week* is a pace, not effort |

**Accepted as residual (prompt-level, recorded):** `note_expectation` stays in Synth's tool list
with the flags off — the grant check requires a registered schema for a granted tool, as for
`lookup_public_fact` — confined by its own description to turns carrying the block, which exists
only while on; the agent-file edits are unconditional text that applies only when its block or
result is present. The standing "you may ask" line's cap is the recorded asks plus the
instruction. Tests: `tests/test_goal_network_phase3b.py` 31/31; every other suite and the QA sweep
unchanged.

**Not built:** the language playbook (its own Mike-led chat); the `mike` goals walkthrough is
prepared, not run — `archive/handoffs/2026-11-24-goal-network-mike-goals-walkthrough-prompt.md`.
