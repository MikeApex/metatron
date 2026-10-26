*Plan reviewed: `archive/plans/day_planner_plan_2026-10-24.md` § 18 (Stage A round 2).*
*Reviewer: Fable (adversarial-reviewer), effort medium, 2026-10-26.*

## STRUCTURAL

1. [§ 18.3 "Per-event answers", § 18.2 ruling 2, R2-5, R2-11] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/scheduling.py:_instances; /Users/md-homefolder/Desktop/multi-model-mcp/tools/day_plan.py:_normalise]
Wrong: `event_answers.json` is keyed `{uid: {…, scope: series | this_one}}`, but every occurrence of a recurring series carries the same `uid` (`_instances` copies `**ev`; `_normalise` has to mint `key = uid@start` to tell them apart), so one uid slot cannot hold a `this_one` answer without overwriting the series answer, or two `this_one` answers for different weeks.
Fails: the first "just this Gan, not every Gan" answer either silently becomes a series rule or is lost on the next occurrence, and R2-5's "stored answer" step reads the wrong one.
Costs: a persisted data shape that Stage B's `answer_event` tool and the three-agree rule proposal are built on, and that must be migrated once a recurring event is answered — exactly the cost § 18.6 says this review exists to prevent — high.

2. [R2-4, R2-5, § 18.3 `protected … allows`, § 5.5 V2/V6] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/day_plan.py:validate; tools/day_plan.py:_may_protect]
Wrong: Round 2 places non-essential `household`/`health`/`errands` tasks inside protected family windows and hides `noise` events and leaves unanswered family events as "?" rows rather than blocks, while § 5.5 is left standing — and in code V6 fails any non-essential task overlapping a `protected` block (`:920-923`) and V2 fails any snapshot event with no `event`/`own` block (`:896-905`).
Fails: every plan that contains a second Stretching in family time, a hidden promotion or an unanswered family event is rejected by the validator the plan says runs on every build, so the round-2 rules never reach the panel.
Costs: the watch-day acceptance cannot pass on the rules as written and the validator rewrite it forces touches the fill, the gate's "repair that dropped an essential item" classification and the Stage B model contract — high.

3. [§ 18.2 ruling 2, § 18.3 `calendars`, R2-5 "role → rule → stored answer → question"] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/caldav.py:_calendar_set; tools/day_plan.py:_normalise]
Wrong: the plan defines three calendar roles and an order in which role resolves first, but never says what answer `mine` yields — and if `mine` resolves to *there* (the only reading under which "every calendar defaults to the user's" means anything), no `event_rules` entry can ever fire on the user's own calendar.
Fails: a promotion on "Main" (§ 18.1's Happy Hour, which § 18.4 lists on no other calendar) is *there* by role before any noise rule is consulted and blocks 09:00–12:15 again on the watch day.
Costs: the triage step's shape is undecided while R2-5, R2-7, R2-12's fixture and Stage B's `answer_event` are all written against it, and the 10-25 failure the section opens with is reproduced — medium.

4. [R2-10 D3 "last chance the 15th", R2-3, R2-9] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/obligations.py:_on_todays_list; tools/obligations.py:_view_core]
Wrong: a monthly bill is modelled as a habit with a day-of-month window, and a habit has no overdue state — `_on_todays_list` admits a quota only when `planned` or `at_risk` (`:2292-2295`), never `behind`, and R2-9 lists only "essential items due today or overdue".
Fails: a Chase bill not paid by the 15th is neither planned, at-risk nor overdue from the 16th on, so it drops off the plan and the Today list for the rest of the month and resurfaces only as a period-end `missed`/`unconfirmed`.
Costs: the one task class D3 was added for is silently unplanned for half of every month, and the fix decides whether D3 is a habit window or a recurring deadline, which changes R2-3, R2-9, the score table and the test fixture — medium.

## LOCAL

5. [§ 18.2 ruling 3 (D1), R2-5 "a new calendar is listed as a question while its events count as the user's"] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/caldav.py:_calendar_set]
Wrong: Mike's ruling says a calendar that appears later is asked about *before the plan uses it*; R2-5 uses its events as the user's own commitments immediately and asks in parallel.
Fails: a newly subscribed feed or shared calendar blocks the day as *there* events from its first poll until the question is answered — in round 2, with no `answer_event`, until Stage B.
Costs: builds past a ruling recorded in the same section, reproducing the "every calendar read as the user's own" failure for every calendar added after setup — medium.

6. [§ 18.4 "Calibration, 10-25", § 18.3 "Per-event answers … written in Stage B", R2-2, R2-5, § 18.5 acceptance] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/day_shape.py:set_day_shape]
Wrong: round 2 has no writer for `event_answers.json` — the setup command applies day-shape sections only and `answer_event` is Stage B — so the calibration answers § 18.4 records have no home, and every family-calendar event not matched by an `event_rules` word is a "?" row that blocks nothing.
Fails: a real childcare duty on "Shared with Mike" with no standing rule (Iva voting is the recorded case) is planned over with admin and focus for the whole of round 2, and the acceptance line "every unknown a question rather than a block" reads that as a pass.
Costs: the watch day inverts 10-25's failure (false commitments) into false free time without saying so, so a passing watch day does not establish that the triage works — medium.

7. [§ 18.3 `routines` "A calendar event overlapping it replaces it that day", R2-5, R2-6, R2-7] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/day_plan.py:_skeleton]
Wrong: routine replacement is stated against any overlapping calendar event, with no ordering against triage, so a `noise` event, a `someone_else` context line or an unanswered "?" row overlapping the 12:00 routine displaces it and its travel.
Fails: § 18.1's own data has Happy Hour ending 12:15 and family events covering 12:00–14:00 — both overlap the mon–fri lunch routine — so the routine, its travel and its `covers: lunch` vanish on exactly the fixture day R2-12 encodes.
Costs: the lunch routine with travel both ways is the acceptance's named check and would fail or pass by accident depending on an unspecified rule order — medium.

8. [§ 18.4 `windows` "Admin at weekends 'when I'm free from childcare' — the same windows, with duties blocking", § 18.3 `children_home` default] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/day_shape.py:shape_for]
Wrong: the baseline transcribes Mike's weekend condition as the weekday windows plus calendar duties, but duties exist only as `needs_me` calendar events and `children_home` is unanswered, so a Saturday with no events is read as 10:00–17:30 of strong admin/focus time.
Fails: the first weekend plan fills the day with work the user said is conditional on being free of childcare, and the acceptance (one ordinary weekday) never sees it.
Costs: the first stored baseline for the only live user misstates his week in a way the universal defaults cannot catch, and it is the template every future user's answers are said to fit — speculative.

9. [R2-10 "`update_task(action=\"set_days\")` … exposed now … a deliberate, stated exception to R1-1", § 4.1, § 11.1] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/obligations.py:update_task (`:1433-1434`); /Users/md-homefolder/Desktop/multi-model-mcp/tests/test_day_plan_ledger.py:"flag OFF: the schemas models see are byte-identical"]
Wrong: challenging the stated acceptance — the exception re-hashes the pin that is R1-1's whole mechanism, and ships a write that changes when a habit is planned into the prompts of every agent granted `update_task` with no conduct and no stated user-turn gate, whereas the sibling writers the plan built are gated.
Fails: a model told by `:1481` to "change its days" now can, on any turn including scheduled ones, and the test that proved "flag off = today's schemas" proves only "flag off = this build's schemas".
Costs: habit days in the live ledger become model-writable in Stage A, the thing R1-1 was accepted to prevent, with the pin no longer evidence — medium.

## VERIFY — 2026-10-26

F1. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/day_plan.py:_normalise] `uid` and `key = uid@start` are both already emitted per occurrence (`:278-279`), so the two maps (`series`, `occurrences`) key on values the snapshot carries; the single-slot shape is gone.

F2. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/day_plan.py:validate] V2 (`:896-905`) and V6 (`:920-923`) still reject hidden noise, "?" rows and allowed non-essential tasks in protected time, and the plan now names R2-13 as the rewrite of both in the same change plus the gate's `displaced_protected` read (`:860-864`, `:972`); the § 5.5 vs R2-4/R2-5 contradiction is removed and the code work is enumerated rather than assumed.

F3. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/caldav.py:_calendar_set `:396`, `:417`] order is now answer → rule → role → question with each role's answer stated (`mine` → there, `family` → question, `feed` → noise), so a noise rule on the writable (`mine: True`) calendar fires before the role; the Happy Hour case no longer survives by construction.

F4. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/obligations.py:_on_todays_list `:2288`; tools/obligations.py:is_essential `:1253`] `overdue` is already admitted to the Today list, and R2-10 now defines a windowed habit past its last day as `overdue` through period end and extends `is_essential`'s deadline clause (currently `kind == "deadline"` only) to it; the `_score` `vital` change (`day_plan.py:560`) is implied work.

F5. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/day_plan.py:_normalise; tools/caldav.py:_merge_group `:581`] the snapshot keeps `calendars` and a calendar absent from the roster is not planned; the ruling-3 contradiction is gone. (Introduces N1 below.)

F6. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/day_plan.py:_fill `:758`, `:814`] a "?" row becomes a protected mask with the family `allows` filter rather than free time; calibration answers are declared fixture expectations, not stored data with no writer.

F7. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/day_plan.py:_skeleton] routine replacement is limited to *there* events and *needs_me* duties; noise, context and "?" rows no longer displace the routine or its travel.

F8. PARTIAL (NEW SHAPE) — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/day_shape.py:set_day_shape `:292-325`; tools/day_shape.py:FIELDS] the weekend windows still place 10:00–17:30 of admin/focus on sat/sun; each row now carries the condition as a question, but nothing in round 2 or Stage B can answer it — `set_day_shape` (even revised to "a section and an entry") writes standing entries only, and no per-day override writer exists for "unless the user notes otherwise for a day" or "the weekend morning brief settles it". The defect moved from silent planning to a question no tool can record the answer to.

F9. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/obligations.py:update_task `:1433-1434`; /Users/md-homefolder/Desktop/multi-model-mcp/tests/test_day_plan_ledger.py "flag OFF … byte-identical" `:291-299`] `set_days` joins `_PLAN_ACTIONS` behind `ledger_fields`, so the flag-off hashes stand; the user-turn gate is the one `set_day_shape` already applies (`:298-301`); the exception is withdrawn.

### NEW — STRUCTURAL

none

### NEW — LOCAL

N1. [§ 18.3 `calendars` "a calendar not in the roster is *new* — its events are not planned", § 18.4 "Main → mine", R2-5 (F5 fix)] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/caldav.py:_calendar_set `:393-396`; tools/caldav.py:_discover_calendars `:343-358`]
Wrong: the roster is keyed by display name, but the writable calendar's name is whatever discovery returns and falls back to the literal `"Main calendar"` when discovery fails or is off (`discovered, status = [], "off"` → `own_name = "" or "Main calendar"`), so the name setup records and the name a later poll sees are not guaranteed to be the same string.
Fails: on any run where discovery fails (a transient PROPFIND error) or after a Google-side rename, the user's own calendar is "new since setup", its events are not planned, and the day builds as empty with one note — the F5 fix converts a naming hiccup into a blank plan, where before F5 it cost nothing.
Costs: the most common failure of an unattended CalDAV reader now zeroes the day's commitments rather than degrading, and the roster key is what Stage B's `set_day_shape` entries and every future user's answers will be written against — medium.
