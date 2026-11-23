# Ranking, Part B — rank by the regret of delay, weighed by the user's values — plan, 2026-11-23

Model: Opus 5.5 plans and builds; Fable 5.1 reviews this plan and each phase's diff
(docs/WORKFLOW.md, Mike 2026-09-24). Red work is done in-session, never delegated.

**Status: plan, not authorisation.** Written after an eight-topic interview with Mike on
2026-11-22/23 (this session). Successor to `goal_task_network_plan_2026-11-18.md` § 16 (Part A,
built in `fda9d80`, `e6a661c`, `deed121` — all committed; the working tree's ranking files match
HEAD). Adjacent to that plan's § 5 phase 3 (large goals): **re-vetting and the satisfaction
mismatch are its own; this plan shares their signals (§ 4.13) and builds neither.**

---

## 1. The need, in Mike's words

From 2026-11-22 (plan § 16, rulings 1–8):

> *"Tasks should be scored always, and if not vital should have a weaker score and be relegated to
> back burner … Metatron should check new tasks against user goals and core values to ensure
> appropriate ranking. If someone is a passionate gardener, repotting the plants is likely more
> important than for the weekend warrior."*
>
> *"Sometimes even an urgent deadline is less important if the underlying task gets in the way of,
> say, family time."* · *"Taxes might not align with mission, but still are high priority."* ·
> *"Urgency and importance are two different vectors that are being consolidated into a single
> score."* · *"Metatron's mission is to emphasize what will lead to long term happiness, not
> managing a to do list."*

From the interview (2026-11-23), the sentence the design is built on:

> *"Urgency is largely defined by consequence, so consequence as a cost must be compared to the
> value of doing something else with that time. Regret is a useful concept here … The cost is
> stagnant for the credit card (or maybe it becomes more financially costly each day it is late),
> but the costs DEFINITELY accrue for each day Dad isn't called. $30 for a day's delay might be
> ok, $30*365 days vs not speaking to Dad for a year is unacceptable. There's the convexity."*

And the bar it must clear: *"Managed or nagged is a cardinal sin for users. Same for lists running
life. Using Metatron should feel effortful, but with payoff, and this should be supported by
Metatron making the non-user essential tasks effortless."*

**Done** looks like: Metatron decides what the user does next by asking which delay they would
regret more — weighed by the user's own values, with protected time defended by the same
comparison — and puts to the user only what is genuinely theirs to decide, once a week and when
a clash arises.

---

## 2. Mike's rulings, 2026-11-23

**All are design (every user) unless marked.** None was marked personal. Placeholders are named
as placeholders; each is a config value refined by research and then by evidence.

| # | Topic | Ruling |
|---|---|---|
| B1 | Costs | Dimensions: **financial, legal, health, social, psychological/existential.** Two modifiers: **reversibility** ("a strong vector") and **who bears it**. |
| B2 | Costs | **The worst cost sets the floor; further real costs compound above it.** No formula given — this plan proposes one (§ 4.2) and the live check tests it. |
| B3 | Costs | **Who bears it:** a cost to the user's intimates ≈ the same cost to the user. A cost falling mainly on an organisation weighs less than the same cost to the user — *"the self would be prioritized."* |
| B4 | Costs | **Users see the cost grades and can correct them — "for now."** A per-user setting, default on. |
| B5 | Model | **Rank by the regret of delay:** the cost of one more day not doing it, against the value of doing something else with that time. Costs accrue in shapes, some convex. Metatron starts from **researched defaults** (e.g. relationships against financial hardship), shifted by the user's values; until the research exists, placeholders. |
| B6 | Model | **Four shapes** — step, accruing, neglect (convex), cliff — "a great start for now." |
| B7 | Model | **Cost of delay per unit of attention.** Every task costs at least one **attention block** — a researched default in the 5–15 min range, "the base cost, not how many picoseconds a task takes." Applies only when the user will actually do both; **when both fit, the harder thing goes first by default.** |
| B8 | Model | **Neglect curves for relationships and upkeep; reserved time stays for building goals** (a language). |
| B9 | Model | **A neglect clock starts from the user's stated wish, asked** — *"history does not show desire but habit"* — and history informs the conversation. |
| B10 | Protected | **Protected time has a convex intrusion cost** — "a framework for emergencies or acceptable interruptions while still protecting the time." |
| B11 | Protected | **No absolutes.** Defaults protected for anyone: sleep, family/partner time, the user's own rest, meals, exercise. *A text about a family member's medical emergency would interrupt sleep.* |
| B12 | Protected | **Ask first** before any deadline enters protected time. |
| B13 | Protected | **Balance is Metatron's responsibility, not a ledger of loans** — it holds the balance the user cannot or will not hold alone, or takes the judgement over so they need not carry it. |
| B14 | Sequencing | **Rewards are sequenced to build habits:** something the user loves goes after something they want to do but find hard (the protein shake after the workout, not at breakfast, absent a nutritional reason). **Never framed as a reward** — noticed, or asked about without saying why. |
| B15 | Values | **A passion can outrank an obligation** when the regret comparison says so — "as a baseline. We'll then iterate towards a balance." |
| B16 | Values | **Stated is primary; behaviour supports.** Behaviour raises a question, never settles one. |
| B17 | Values | **Passion is an ongoing conversation** — an observation may be raised again when there is reason. |
| B18 | Principle | **Metatron provides what the user didn't know they needed and didn't realise they hadn't asked for** — *"the muffin arrives in hand 10 minutes before the hunger kicks into consciousness."* Recorded here as design; this plan builds only its ranking-side instance (B14). |
| B19 | Probing | **No task is probe-free by category** — milk for the kids can matter. Salience is judged in context; infer what context settles, ask only what it cannot and what would change the outcome. |
| B20 | Probing | **At most one question at mention**, in conversation, never a form. |
| B21 | Probing | **Emotional weight may be read from how a task is mentioned**, confirmed when necessary; what the user says sets the baseline. *Metatron gets to "know" the user as they use it* — fewer questions over time. |
| B22 | Probing | **Look up before asking.** *"A google search without truly personal details is innocuous."* |
| B23 | Climb | **Assume the user starts late, then verify from evidence.** Mike's guess: a 30% buffer; research the starting point. Learned per user. |
| B24 | Climb | **Raise once** when a placed task is skipped twice, or when its slack drops below what it needs. **Balance done against overwhelm:** when the user is already behind, raising more harms — **lead with small, easy wins** to build momentum toward the most urgent and salient. (So: hard-first when on track, easy-wins-first when behind — B7 refined.) |
| B25 | Climb | **A promise with no date gets an implied one** from context (default ~a week). |
| B26 | Back burner | **Trivia that never rises and is never mentioned for 30 days moves quietly to an archive** — never deleted, visible on request, revived by a fresh mention. |
| B27 | Back burner | **Guards:** nothing with a dated step or cliff expires before its date; anything naming a person or of an obligation type (taxes, bills, legal, health) is asked about once instead of expiring; grades stay visible. |
| B28 | Reconcile | **A weekly priorities conversation** (option a). |
| B29 | Reconcile | **A clash is put as one question carrying Metatron's recommendation**, never an open choice. |
| B30 | Signals | **Stated regret** — powerful, "but only short term." **Forward momentum** on goals and the most meaningful things (relationships) for the long term. **Solicited input woven naturally** (never a survey) **and unsolicited input. Task completion.** **Overrides are not a success signal** — they can be the user's own misjudgement putting the urgent over the meaningful. **Fewer intrusions** = compliance and the system working as intended, which does not mean the developer side needs no adjustment. **Missed obligations. Attention spent.** |
| B31 | Signals | **Cardinal sins: the user feeling managed or nagged; the list running their life.** Effort belongs on the meaningful, with visible payoff; Metatron makes the rest effortless. *Build note — binds every phase.* |
| B32 | Signals | **A monthly review of the signals with Mike.** |

**B31's reading confirmed by Mike (2026-11-23):** *"effortful, but with payoff"* is deliberate —
effort spent on what only the user can do — not a slip for "effortless."

---

## 3. What exists, and what each piece becomes

Surveyed against HEAD, 2026-11-23.

| Exists | Where | Becomes |
|---|---|---|
| Additive score: base (priority/goal 10–30) + urgency (vital overdue 40) | `day_plan._score`, `day_plan.yaml score:` | **replaced** behind a flag by the regret score (§ 4.4); kept intact as the flag-off path |
| Linear climb over ≤ 14 days | `day_plan._ramp`, `score.ramp_days` | **replaced** by slack (§ 4.3); `ramp_days` read only on the flag-off path |
| `stakes` vital/missable, `priority`, `stakes_why`; the judging rule's one home | `obligations._PLAN_FIELD_PROPS` | **extended** with the cost record (§ 4.1); `stakes` becomes **derived** from it, so every reader of `stakes` (`is_essential`, nudges, the close gate) keeps working |
| `task_judge` — judges unjudged deadlines off the tick, capped | `tools/task_judge.py`, `config/agents/task_judge.md` | **extended** to return the cost record and shape; also judges `interval` tasks for the neglect shape |
| Steps inherit their end state's weight | `_end_weight`, `_step_weight` | inherit the end's **cost record** (a step of a severe end carries it) |
| `interval` kind: `interval_days`, `last_done`, due/overdue | `obligations.py` (`_interval_due`) | **the neglect shape's host** — a due date becomes a convex curve over days since `last_done` |
| Contacts: `contact_frequency_preference` (daily…quarterly), `last_contact`, an overdue filter | `tools/crm.py` | **the source of people's neglect clocks** (B9) — offered to the user once as an interval task |
| Protected windows; `_may_protect` = "essential may intrude when nothing else fits"; `displaced_protected` nudge | `day_plan._fill`, `_may_protect` | **replaced** by the convex intrusion cost and ask-first (§ 4.5) |
| The plan's asks (answered from the app or in chat) | `day_plan` asks, `answer_event` | **carries the intrusion question** (B12, B29) — no new channel |
| Accountability Index (intentions vs outcomes, nightly) | `tools/accountability.py` | evidence for the start-late buffer and "behind" (§ 4.10) |
| Research Agent: grounded search, decontextualised **by instruction only** | `routing_cloud.yaml` `research_agent`; Synth reaches it via `run_subagent` | **the look-up-first path** (B22) — **with a new code check on what the query carries** (§ 4.7); none exists today |
| `profile.yaml`, schema-bounded writer | `tools/profile.py` `WRITABLE` | gains **`passions`** (§ 4.8) |
| `write_schedule` (Synth; recurring proactive sessions, 6-job cap) | synthesizer tools | **creates the weekly conversation** at the time the user picks (§ 4.12) — no VM-side scheduler edit |
| Scheduled-session conduct | `config/modules/synthesizer_scheduled_sessions.md` | the weekly conversation's conduct (§ 4.12) |
| Daily analytics rollup (absorbed work, attention) | ROADMAP § A9 | the attention signal (B30) — read, not rebuilt |

---

## 4. Design

> **Amended by § 10 (Fable adversarial review, reconciled 2026-11-23).** Where § 10 and §§ 4–8
> differ, § 10 governs.

### 4.1 The cost record — on every task

New optional fields beside `stakes`/`priority` in `_PLAN_FIELD_PROPS` (the one home for the
judging rule, A3 of § 16):

| Field | Values | Meaning |
|---|---|---|
| `costs` | `{financial, legal, health, social, psychological}` → `minor \| major \| severe` | only the dimensions that apply |
| `bears` | `self \| close \| others \| org` | who mainly bears the cost (B3; `close` = intimates) |
| `shape` | `step \| accruing \| neglect \| cliff` | how the cost of delay grows (B6) |
| `real_due` | date | the date behind the stated one (the annual fund's close), when known |
| `costs_source` | `stated \| inferred` | as `stakes_source`; a stated record is never replaced by an inferred one |
| `costs_why` | ≤ 120 chars | supersedes `stakes_why` (kept as an alias on read) |

- **`stakes` becomes derived**: `vital` ⇔ the bearer-weighted floor grade (§ 4.2) is ≥ `major`.
  Written on every cost-record write, so the dozen readers of `stakes` change nothing. A task with
  `stakes` but no record (all of Part A's) reads `vital` → `{floor: major, shape: step}`,
  `missable` → `{floor: minor, shape: step}`.
- **Reversibility is carried by the shape**, not a separate field: `cliff` is the irreversible one;
  `step`/`accruing` are recoverable at a price; `neglect` compounds.
- **Default shape when the judge cannot tell:** `step` for a deadline, `neglect` for an interval.

### 4.2 Importance — the floor, the compounding, the bearer (B1–B3, B15)

All numbers in a new `config/modules/ranking.yaml`, **placeholders** until § 4.14's research:

- **Grade ladder, geometric so the floor dominates:** `minor 10, major 30, severe 90`.
- **Bearer weight** on each cost: `self 1.0, close 1.0, others 0.7, org 0.5`.
- **Floor** `F` = the largest bearer-weighted grade. **Compounding:** `+ 0.25 ×` each other
  dimension at `major`+ (bearer-weighted), **capped at the next grade up** — two majors never
  equal a severe. This is B2's "worst sets the floor, then synergistic effects can compound" as
  the smallest formula that honours both halves; the live check tests it on real tasks.
- **A stated passion** (§ 4.8) raises the grade of `psychological` and `social` costs on a task
  that serves it by one step. B15: it can therefore outrank an obligation through the regret
  comparison; no obligation floor is added — iterate from evidence.

### 4.3 Cost of delay — the four shapes, read through slack (B5, B6, B23)

**Slack** `s` = days to `real_due` (else `due`) minus the days the task needs, where *needed* =
lead days (known lead times, e.g. processing) + the task's minutes × (1 + buffer) spread over the
user's typical free time for its activity. The **buffer** starts at the start-late default
(§ 4.10) and is learned per user.

The cost of one more day's delay, `CoD`, for importance `G` (§ 4.2):

| Shape | `CoD` today | Example |
|---|---|---|
| **step** | `G × r(s)` before the date, where `r` rises from 0 to 1 as `s` falls from `S` to 0 (`S` = the climb window, § 4.10); after the date, a residual (config, default 0.2 × G) | late fee; RSVP |
| **accruing** | as step before the date; after it, `G × (1 + a × days_late)` | interest; a growing backlog |
| **neglect** | `G × (t / T)^k`, `t` = days since `last_done`, `T` = wished cadence, `k` = convexity (placeholder **2**) | Dad; exercise; the house |
| **cliff** | as step, × a **reversibility weight** (placeholder **2**); after the date the task is moot | GS donation by 30 Nov; plants in two weeks |

Dad at three weeks on a weekly wish: `G=90 (severe, close) × (21/7)^2 = 810`. The parking permit
due tomorrow: `G=10 (minor, self) × 1 = 10`. Dad wins *because* three weeks accrued — Mike's
example, reproduced as a test (§ 6). At day 2 of 7, Dad is `90 × 0.08 ≈ 7` and the permit wins.

### 4.4 The rank — selection, then sequence (B7, B24)

Two stages, because Mike ruled two things:

1. **Selection** — what gets into the day when room is short: **rank = `CoD` ÷ attention blocks**,
   blocks = `max(1, ceil(minutes / attention_block))`, `attention_block` a placeholder **10 min**
   (§ 4.14). The day planner fills by this order. Medication keeps its fixed lift (unchanged).
2. **Sequence** — the order within what fits: **harder first** (longest, or `activity` focus/admin)
   by default; **easy wins first when the user is behind** (§ 4.10). "Will the user actually do
   both" is read from their record: if most evenings close with one task done, the evening is one
   slot and selection alone decides.

The rank is scaled to the existing integer range so `reshuffle_delta` and the Important line keep
their meaning (scale factor in `ranking.yaml`, chosen in the build against the fixtures).

**Flag `ranking_v2`** (in `day_plan.yaml` flags). Off = Part A exactly: `_score`, `_ramp`,
`_may_protect` untouched. Phase 1 runs it in **shadow**: both scores computed, the v2 order
written to the day-plan trace, the v1 order used.

### 4.5 Protected time — a convex intrusion cost, asked first (B10–B13)

- Each protected window class has an intrusion cost `I = base × (1 + n)^k`, `n` = intrusions into
  that class in the last 7 days, `k` as § 4.3. Bases in `ranking.yaml`, placeholders: **sleep 500,
  family 120, own time 60, meals 40, exercise 40** — sleep very high, never infinite (B11).
- A task may enter a protected window only when its `CoD > I`. **It is then never placed
  silently**: it becomes an ask on the plan, carrying Metatron's recommendation (B12, B29) —
  *"The return needs two hours. I'd keep tonight for the family and do it Saturday morning — OK?"*
  — answered from the app or in chat via `answer_event`. Unanswered by the window's start, the
  window stays protected.
- **Balance** (B13): because `n` decays over seven days, each intrusion raises the bar for the
  next; nothing is "repaid," the bar simply stays high until the week has recovered.
- Emergencies reaching the user (a message at night) are delivery, not ranking — out of scope; the
  framework only guarantees that no *task* enters sleep without passing the same comparison.

### 4.6 Neglect clocks (B8, B9)

- An `interval` task with `shape: neglect` scores by § 4.3 instead of jumping at `next_due`.
  `interval_days` is `T`, the **stated** wish.
- **People:** a contact with a wished frequency and an intimate `relationship_type` is **offered
  once** as a clock — *"Do you want me to help you keep in touch with your dad — about weekly?"* —
  and on yes becomes an interval task `{what: "Be in touch with Dad", shape: neglect,
  bears: close}`, `last_done` seeded from `last_contact`. History informs the question (*"it's
  been about every two weeks lately"*); it never sets `T` by itself (B9).
- **Reserved time** stays for building goals: `allocation_gaps` is unchanged (B8).

### 4.7 Probing a task's shape at mention (B19–B22)

**Synthesizer conduct (Red), one paragraph, at the point a task is opened:**
infer the cost record from context (household, goals, what the user said and *how* they said it —
B21's emotional weight is an inferred `psychological` cost); **ask at most one question, and only
when its answer would change the rank or the date** (B19, B20); in the user's register, woven into
the reply. Examples it carries: the real date behind the stated one, a decay window, who it is for.

**Look up first (B22):** where the missing edge is a public fact (a fund's close date, passport
processing time), Synth calls `run_subagent("research_agent", …)` before asking.
**New code check, `tools/lookup_guard.py`, applied in `run_subagent` when the target is
`research_agent` on this path:** the outgoing message must not contain the user's name, any
contact's name, an address, an account, an email or phone, or a health/financial figure from the
user's records. A hit strips the term if the question survives without it, else refuses the
lookup (the probe then asks). Org names and public places pass — *"a google search without truly
personal details is innocuous"* (Mike). Capped per persona per day (`lookups_per_day`, 5).

The answer writes the cost record via `update_task` with `costs_source: stated` (the user said it)
or `inferred` (Synth or the lookup).

### 4.8 Passions (B15–B17)

- **Home: `profile.yaml` `passions`** — a list of `{what, source: stated|inferred, since}` —
  added to `tools/profile.py` `WRITABLE`. Stable facts about the user is that file's job; the
  one-line summary already reaches the head layer.
- **Stated is primary** (B16): Synth writes `stated` when the user says it. An `inferred` passion is
  only a reason to ask; it never lifts a grade (§ 4.2 reads `stated` only).
- **Ongoing** (B17): behaviour that contradicts or newly suggests a passion (repeated unprompted
  time, energy in how it is spoken of) may raise it again — at most once per passion per month,
  and never in a week the user is behind (B24).
- The task judge receives `passions` (stated only) beside goals and mission.

### 4.9 Rewards, never named (B14, B18)

- An `enjoyed: true` marker on a habit or task, **inferred from what the user mentions** or from
  a question that does not say why (*"what do you look forward to most in a day?"* is not asked;
  noticing comes first).
- The fill places an `enjoyed` item with no fixed time **directly after** an effortful item the
  user wants to do (a workout, a focus block) on the same day, unless the item has a time or a
  `nutrition`-style constraint. Nothing in any output says "reward."

### 4.10 The climb, raising, and "behind" (B23–B25)

- **Start-late buffer:** default from § 4.14's research (**placeholder 50%** — Mike's guess was
  30%; the planning-fallacy literature, recalled and to be verified, runs higher). Learned per
  user: the median of (actual close − planned start) ÷ planned duration, over closed deadlines,
  once ≥ 10 exist; until then the default. State in `data/personas/{p}/day_plan/ranking_state.json`.
- **Climb window `S`** = needed days × (1 + buffer), floored at 1, capped at `ramp_days` (kept, 14).
- **Raising** (said once, as Important): a placed task skipped twice, **or** slack < 0 (it cannot
  now be done in time without an intrusion). Never more than one raise a day per user.
- **Behind** = ≥ 3 overdue vital tasks, or ≥ 3 skips in the last 3 days. While behind: no new
  raises except slack < 0 on a severe grade; the sequence leads with the two smallest selected
  tasks; the next raise waits for one of them to close.
- **Implied dates** (B25): a promise to a person with no date gets `due` = mention + 7 days
  (`implied_promise_days`), `due_source: implied`, revised by anything the user says.

### 4.11 The back burner (B26, B27)

- **Archive rule (daily, code):** an open task with `CoD` < a floor (`back_burner_cod`) for 30
  days **and** no mention in that time (no `update_task`, no Synth reference recorded) closes as
  `moot` with reason `back_burner`. Archive-on-merge: the row stays, `history` records it.
- **Guards:** not before a dated `step`/`cliff`'s date; never silently for a task with a person
  (`bears: close|others`, or a contact named) or an obligation type (`costs.legal|financial ≥
  major`, health) — those become one line in the weekly conversation instead (§ 4.12).
- **Revival:** `open_task` matching an archived `back_burner` row reopens it rather than duplicating.

### 4.12 The weekly priorities conversation (B28, B29)

- **Created by Synth with `write_schedule`** at a time the user picks, offered once after phase 3
  ships. ~5 minutes, skippable; counts against the 6-job cap.
- **Conduct** in `config/modules/synthesizer_scheduled_sessions.md` (one home): (1) what Metatron
  moved and why, at most three lines; (2) any clash held, each as one question with a
  recommendation; (3) what is slipping or about to be archived, guarded items first; (4) one
  relationship/upkeep clock; (5) **the regret question** — *"anything you wish you'd got to this
  week?"*; (6) at most one naturally woven check on how things feel (B30). It never reads out a
  list (B31).
- Each answer is recorded (§ 4.13).

### 4.13 Signals and the monthly review (B30–B32)

Recorded to `data/personas/{p}/ranking_signals.jsonl`, one row per event, kept forever (ROADMAP
§ A9 rule 2):

| Signal | Source |
|---|---|
| stated regret (short-term) | weekly answer (5) |
| forward momentum — goal steps closed vs planned; neglect clocks within `T` | ledger, daily |
| solicited (woven) and unsolicited input on how things feel | weekly (6); Synth on any unprompted remark about overload, nagging or satisfaction |
| completion | ledger, daily |
| intrusions into protected time (count, class, asked/accepted) | § 4.5 |
| missed obligations (a `legal`/`financial` ≥ major past date, open) | ledger, daily |
| attention: questions asked by this plan's paths per week | probes, raises, asks |
| overrides — **recorded, not scored** (B30) | reorders and grade corrections |

**Shared, not duplicated:** goal network phase 3's satisfaction mismatch (anticipated vs
experienced) writes its own rows; this file reads them. `scripts/ranking_report.py --persona P`
prints the month. **The monthly review is a Mike walkthrough** (§ 7.2).

### 4.14 Research — the placeholders' sources

Three defaults need literature, none needs personal data: (1) the **attention block** (task-switch
and resumption cost — e.g. Mark, Gudith & Klocke 2008; Leroy 2009 on attention residue);
(2) the **start-late buffer** (planning fallacy — Buehler, Griffin & Ross 1994: theses took ~55
days against ~34 predicted); (3) **relationships vs financial cost** (inaction regrets loom larger
over time — Gilovich & Medvec 1995; Roese & Summerville 2005; the Harvard Study of Adult
Development). **All recalled from memory, unverified.**

**Decided (Mike, 2026-11-23): Mike runs the research himself in a regular Claude chat**, from
`archive/handoffs/2026-11-23-ranking-research-prompt.md` — ten topics covering every placeholder
in §§ 4.2–4.11 (attention block, buffer, relationship vs financial weight and neglect curve,
contact cadences, intrusion bases and convexity, reward ordering, "behind" and quick wins,
question load, abandonment days, promise days, the grade ladder and bearer weight). The prompt
carries no personal or project detail. The result lands as
`archive/plans/ranking_research_2026-11-23_<model>.md`; **phase 1 sets `ranking.yaml` from it**,
each value citing its section, and any value the research cannot support stays a labelled
placeholder.

### 4.15 Where each new rule lives — One Home Per Rule Class

| Rule | Home | Not also in |
|---|---|---|
| how to judge a cost record | `_PLAN_FIELD_PROPS` descriptions | `task_judge.md` says "the field descriptions are the rule" + the obligation line it already carries (§ 16's known pair) |
| every weight, base, ladder, cap, default | `config/modules/ranking.yaml` | nowhere in code |
| per-user learned values (buffer, behind) | `ranking_state.json` | — |
| passions | `profile.yaml` | not `{persona}.md` |
| probe conduct, clash phrasing | `synthesizer.md` | not `coordinator.md` |
| weekly conversation conduct | `synthesizer_scheduled_sessions.md` | not `synthesizer.md` |
| what a lookup may carry | `tools/lookup_guard.py` | not instructions (privacy in Python) |

**Per-user config, as config:** a user's deviations from `ranking.yaml` (a different bearer
weight, a protected base) live in `config/personas/{p}/ranking.yaml`, merged over the module file.
None is written by this plan; the file exists so a later "this matters more to me" has a home
that is not code.

### 4.16 Privacy basis

Everything here reads sensitive-tier data (tasks, goals, mission, contacts, profile, behaviour) on
the dedicated VM under **ROADMAP § Section 0**: the 2026-06-18 amendment and its 2026-08-09
clarification (single-user default, new sensitive paths of the same shape pre-cleared), extended to
a second user by the 2026-10-26 and 2026-11-18 amendments, gated by each user's consent record. The
task judge stays a bare call with no private_why. **The only path leaving that boundary is the
look-up-first query**, which goes to the decontextualised Research Agent with a **code** check
(§ 4.7) — Section 0's clause 5 enforced in Python, as the orchestrator rules require.

---

## 5. Phases — each ends in a live check with Mike

**Phase 1 — the regret model, in shadow, then live.** §§ 4.1–4.4, 4.6 (interval neglect + the
people offer), 4.10 (buffer, climb, implied dates), `ranking.yaml`, the judge extended, grades
visible on request in chat. Research per § 4.14. *Live check:* three days in shadow — each morning
Mike sees v1 and v2's top 10 side by side (`scripts/ranking_report.py --compare`), says which is
right and why; then the flag flips. Pass: Mike prefers v2 on ≥ 2 of 3 days and no obligation he
calls real sits below the cut.

**Phase 2 — the conversation at mention, and protected time.** §§ 4.5, 4.7 (incl.
`lookup_guard.py`), 4.8, 4.9, raising and behind (§ 4.10). *Live check:* Mike mentions five real
new tasks in a day — each gets ≤ 1 question, one gets a lookup instead of a question, the GS-style
real date lands in `real_due`; a deadline that wants family time comes as one question with a
recommendation; over the week, no nagging (Mike's word is the test).

**Phase 3 — reconciliation and signals.** §§ 4.11 (archive runs in **dry-run** for its first week,
listing what it would archive), 4.12, 4.13. *Live check:* two weekly conversations; the dry-run
list reviewed with Mike before archiving goes live; the first monthly review.

---

## 6. Tests

`tests/test_ranking_v2.py`, fixture personas only, every live meter stubbed (standing rule):

1. **Dad vs the permit:** day 21 of 7 — Dad first; day 2 — the permit first.
2. **Floor and compounding:** two majors < one severe; a major + major > a lone major; the cap holds.
3. **Bearer:** an org-borne major < the same self-borne major; `close` = `self`.
4. **Shapes:** step/accruing/neglect/cliff `CoD` over a 30-day sweep, asserted at the exact points.
5. **Attention block:** a 2-minute and a 10-minute task of equal `CoD` rank equal.
6. **Sequence:** hard-first when on track; two smallest first when behind.
7. **Protected:** a `CoD` below `I` never enters; above it, an ask, never a placement; the second
   intrusion in a week needs a higher `CoD` than the first.
8. **Derived stakes:** every Part A reader (`is_essential`, nudges, close gate) gives the same
   answer for a Part A task with and without the flag.
9. **Flag off = Part A exactly:** the existing `tests/test_task_ranking.py` 18/18 untouched and green
   with the flag off.
10. **lookup_guard:** the user's name, a contact's name, an address, an account number are each
    stripped or refused; "Grace School annual fund deadline" passes.
11. **Passions:** an inferred passion never lifts a grade; a stated one lifts by exactly one step.
12. **Back burner:** a 30-day silent trivia task archives; a person-task, a dated cliff and a
    `legal` major never do; a re-mention reopens.
13. **Buffer learning:** < 10 closed deadlines → default; ≥ 10 → the median.

---

## 7. Red edits, and what only Mike can do

### 7.1 Red edits this build will prompt for

1. `config/agents/synthesizer.md` — probe-at-mention paragraph (§ 4.7), clash phrasing (§ 4.5),
   passions write (§ 4.8). Phase 2.
2. `config/agents/task_judge.md` — the cost-record output; it defers to the field descriptions.
   Phase 1.
3. `config/modules/routing_cloud.yaml` — `task_judge` max output tokens if the record outgrows the
   current cap. Phase 1, only if measured.

No edit to `config/personas/**` (Denied; VM-owned), the constitution, or `core/{router,persona,
scheduler,spend_guard}.py`. Deploy is Mike's.

### 7.2 Mike-gated — each a walkthrough, not a line

1. **The research run** (§ 4.14) — Mike pastes the prompt into a regular Claude chat and saves the
   reply to `archive/plans/`. Before phase 1; no session needed beyond handing the file over.
2. **Phase 1 shadow comparison** — three mornings, ~5 minutes each: the build session prepares
   `--compare` output; Mike reads it on the VM with guidance.
3. **The monthly review** — the first at the end of phase 3: `ranking_report.py` prepared, Mike
   reads it with the session, decisions go to `ranking.yaml` or the persona file.

---

## 8. Budget

**Build (estimates, not measured; scaled from the 11-18 plan's actuals):**

| Phase | Work | Sessions | Rough cost |
|---|---|---|---|
| Plan review | Fable adversarial review of this file | 1 | ~$15–30 |
| 1 | model, fields, judge, shapes, clocks, climb, shadow, research; Fable diff review | 1–2 Opus | ~$50–90 |
| 2 | probe at mention, lookup guard, protected intrusion, passions, rewards, raising; Fable diff review | 2 Opus | ~$60–110 |
| 3 | back burner, weekly conversation, signals, report; Fable diff review | 1 Opus | ~$30–60 |

**Run (per persona, per day, at today's prices):**
- The ranking, slack, shapes, intrusion, back burner and signals are **code — zero tokens**.
- `task_judge`: the cost record adds ~40% output → ~$0.014 a call, still capped at 6/day →
  **≤ ~$0.08/day**; typical is a few calls a week after the re-judge on deploy.
- Probing at mention: one sentence inside a reply the user already triggered — **~0**.
- Lookups: a Research Agent call ~$0.005–0.01 in tokens, ≤ 5/day → **≤ ~$0.05/day**, typical
  well under one a day.
- Weekly conversation: one scheduled Synth session, ~$0.02–0.05 → **~$0.005/day**.
- **Total ceiling ~$0.14/day; typical ~$0.02/day.**

**Ancillary:**
1. **Neglect curves move every day**, so day plans change more often; a move ≥ `reshuffle_delta`
   makes the next build a day_planner reshuffle — bounded by `reshuffles_per_day`, not this plan.
   Phase 1's shadow measures how often v2 would have triggered one.
2. **Re-judging on deploy:** every open task gets a cost record — one pass of ≤ 25 per 10 min under
   the existing cap; for `mike` ~2–3 calls on deploy day (~$0.04).
3. Asks for intrusions are user attention — counted (§ 4.13).

**Unseen — no meter reports these:**
1. **Grounded search is billed per query on top of tokens, and `spend_guard` does not meter
   grounding** (checked: no `ground` in `spend_guard.yaml` or `core/spend_guard.py`). The
   `lookups_per_day` cap is the only bound — name the per-query rate beside the cap in the build.
2. **A wrong curve misranks silently.** Guards: visible grades (B4), the weekly conversation's
   "what I moved and why", the monthly review.
3. **Questions cost attention** — the core metric's denominator. Bounded by B20 and the raise caps;
   measured by the attention signal.

**What persists between calls:** `ranking_state.json` (bytes, per persona, owned by the persona —
deleted with it, survives restarts by design), `ranking_signals.jsonl` (append-only, kept forever,
a few hundred bytes a day), the weekly schedule (one of 6 jobs; deleted by `delete_schedule` or
when the user declines it), and the lookup cap counter (per day, expires itself). Nothing bills by
wall-clock time.

**Model:** build Opus 5.5 (high) — the scoring maths and the conduct text are judgement-heavy;
review each phase's diff with Fable 5.1. Runtime: the judge and lookups stay on the reasoning
tier as routed today (`routing_cloud.yaml` is the authority).

---

## 9. Not in this plan

1. Goal network phase 3 (L vetting, re-vetting, satisfaction mismatch) — shares § 4.13's signals.
2. B18 beyond rewards — anticipatory provision as a general capability.
3. Emergency delivery at night — delivery, not ranking.
4. Learning `T` or passions from behaviour without asking — ruled out (B9, B16).
5. Showing grades in the Android app's task view — phase 1 shows them on request in chat; the app
   view waits for the next APK rebuild cycle Mike schedules.

---

## 10. Fable adversarial review and reconciliation (2026-11-23)

Review: `archive/plans/adversarial_review_ranking_values_plan_2026-11-23.md` (Fable, medium) —
4 structural, 5 local. Findings 3, 5 and 7 were re-checked against the code before reconciling
(`_candidates` admits only Today-list, `lapsed` and `in_window`; `_EVENT_ANSWERS` is the four
event meanings; `run_subagent(agent_name, message, complexity, …)` has no path marker) — all hold.
**All nine accepted.**

| # | Finding (what a user would see) | Resolution |
|---|---|---|
| R1 | Turning the new ranking off would not have restored the old one: cost-record writes overwrote the stored `stakes` the old path reads, a user's stated value included, and an org-borne step of the tax plan could have turned missable | **The cost record never writes `stakes`.** It lives in its own fields. Under `ranking_v2` the readers call a new `stakes_v2(t)`, derived at read time; flag-off reads the stored `stakes` exactly as Part A. **Derived vital uses the unweighted floor** (bearer weight acts only in `CoD`), and **a required plan step stays vital by Part A's rule** whatever its record says. **Recording:** a separate judge pass, `unrecorded()`, selects open tasks with no cost record (not "no stakes"), writes only cost fields, never replaces a `stated` record, and runs under its own flag `cost_record` (phase 1, on from day one, so the shadow has data). § 4.1's fallback mapping is read only while a task awaits that pass. § 8 Ancillary 2 is right; § 4.1's "written on every cost-record write" is withdrawn. |
| R2 | What may enter family time could go live undefined or unshadowed, because one flag carried three phases | **One flag per phase, each shadowed for three days before it goes on.** `ranking_v2` (phase 1) = selection and sequence only. Protected time under it is **Part A's `_may_protect`**, reading `is_essential` with `stakes_v2`. Sequence is **hard-first only** (no "behind" yet). `protected_v2` (phase 2) = § 4.5's intrusion cost and the ask. `behind_v2` (phase 2) = § 4.10's behind state, easy wins and the raising rules. Each phase's shadow writes its would-be decisions to the day-plan trace. |
| R3 | Most dated tasks would still appear only on their due day, so the start-late buffer and slack could not bring anything forward | **Candidacy widens by one rule: a task that must start today to be done in time is a task for today** — slack ≤ 0 with the buffer applied (`needed days` includes lead times). This is the present-focus ruling applied to effort rather than date: a ten-minute task for Monday still doesn't show on Sunday; a four-hour one due Tuesday, with two evenings free, shows on Sunday. **Ruled by Mike (2026-11-23), and broader:** *"There's no reason that if there are no active tasks that advance work can't be suggested. Ideally 'work' and meaningful goal pursuit are all the same, so the time should be filled with something, or intentionally with nothing."* This **amends the 10-24/25 "one definition of today"** in three tiers. (a) Today's list plus must-start-today are the musts. (b) **When room remains after them, advance work is suggested**: upcoming tasks and the current steps of active goals, by `CoD` per block. Suggested, never a must: it nudges nothing, and lapsing it costs nothing. (c) **Time left unfilled is labelled as deliberate** — the user's own time — never left as an unexplained gap. Advance work below a `CoD` floor (`advance_floor`) is not suggested, so the time is "intentionally nothing" rather than filled with trivia. **Neglect:** candidacy stays at `next_due`, and the convex curve governs rank once a clock is due (Dad at day 21 of 7 is overdue anyway). § 4.6's "instead of jumping at `next_due`" is withdrawn. Test 1's "day 2" case becomes "Dad not yet due, so the permit is the only candidate". |
| R4 | A severe deadline due today could not even ask for family time, while a neglected clock beat sleep — the numbers lived on different scales | **One unit, the grade.** Neglect saturates: `CoD = G × min(M, (t/T)^k)`, `M` = 3 (placeholder), so a long-neglected severe clock weighs like a severe cliff (180), never more than 270. **Intrusion bases move into grade units:** own time = minor (10), family = major (30), exercise and meals = minor, sleep = 2 × severe (180). A severe deadline due today (90) then clears family once in a week and not twice (n = 1 → 30 × 4 = 120 > 90), which is the 30 December case. **`reshuffle_delta` gets its own v2 value** in `ranking.yaml`, measured in the shadow, not shared with v1. The trace records each task's `G`, shape factor and blocks separately, so the shadow can isolate which term moved a rank. All of these are placeholders until the research (§ 4.14). |
| R5 | The "may this take family time?" question had nowhere to go — the only answer tool takes calendar meanings | **A new ask kind `intrusion`** in `_asks`, carrying `{task_id, window, recommendation}`, **and a new tool `answer_ask(ask_id, answer: yes\|no\|other_time, when?)`** in `tools/day_plan.py`. It is granted to the Synthesizer in `routing_cloud.yaml` and `routing.yaml` (Red), and its conduct goes in `synthesizer.md` (Red). **Phase 2 answers in chat only**: the ask reaches the user as a push and a Synth turn, as other asks do. A one-tap app control waits for the next APK rebuild Mike schedules (§ 9). Added to § 7.1 and the phase 2 budget. |
| R6 | Sleep and meals cannot be "intruded on" — the planner has no slots there | **Phase 2's intrusion cost acts on the protected windows the day shape actually has** (family, own time, any activity window marked protected), keyed by the window's first activity name, which is the class. **Sleep stays outside the grid: no task enters it, by construction.** That is stricter than B11's letter for tasks only. B11's own example — an emergency message at night — is delivery, which this plan does not touch. **Meals stay hard blocks** that slide within their range, as today. § 4.5's sleep/meal bases are withdrawn and the sleep claim struck. *If Mike wants a task able to ask for a later bedtime, that is a grid change for a later plan.* (Put to Mike 2026-11-23; no objection raised.) |
| R7 | The privacy check on look-ups could not tell this path from any other research call, and would have stripped "Grace" from "Grace School" | **A dedicated tool, `lookup_public_fact(question)`, granted to the Synthesizer (Red: routing files + `synthesizer.md`), is the only look-up-first path.** It runs `lookup_guard` in code, always, then calls the Research Agent itself; its daily cap is its own. Existing `run_subagent("research_agent", …)` traffic is unchanged (its code check stays roadmap B2's). **The guard refuses only full personal identifiers**: the user's or a contact's full name, an email, phone, street address, account or reference number, a health or financial figure from the user's records. A first name alone and an organisation or place name pass — Mike's "without truly personal details." Test 10 adds "Grace School" with a contact named Grace (passes) and "Grace Hopper" as a contact's full name (refused). |
| R8 | Phase 1's people offer, grade display and implied dates, and phase 3's recorded answers, had no conduct text or tool behind them | **The Red list is per phase now (§ 7.1, amended below).** Implied promise dates are **code**, in `open_task`: a task with `bears: close\|others` and no `due` gets mention + 7 days, `due_source: implied`; the rule's text sits in `_PLAN_FIELD_PROPS`. Grade display and correction use the exposed `update_task` fields, plus one `synthesizer.md` sentence (phase 1). The people offer is one `synthesizer.md` paragraph (phase 1). `enjoyed` is a `_PLAN_FIELD_PROPS` field (phase 2). **Signals:** ledger-derived rows (completion, momentum, missed obligations, intrusions, questions asked) are written by code in the daily tick. Spoken answers (regret, how things feel, unprompted remarks) go through a new tool, `record_signal(kind, text)`, granted to the Synthesizer (phase 3, Red). |
| R9 | On a short day, ten-minute chores would fill the time before a two-hour vital task | **Selection has two tiers.** First, the **musts** — vital and overdue, due today, or slack ≤ 0 — are placed by absolute `CoD`, largest first. Then the remaining room fills by `CoD` per attention block. The ratio decides among the optional, never against a must. **Mike (2026-11-23): "This should be up to Synth, but broadly correct unless circumstance dictates otherwise."** So the two tiers are the code default, and the Synthesizer may override them for the moment when circumstance dictates (ten minutes before leaving, do the quick one) through the existing `request_replan(reason)`. The override is recorded as an override (§ 4.13: recorded, not scored); one `synthesizer.md` sentence, phase 1. Test 9 (new): a two-hour severe task due today and six ten-minute minors on a day with two hours free — the severe task is placed. |

**§ 7.1, amended — Red edits by phase:**
1. *Phase 1:* `config/agents/task_judge.md` (the cost-record pass); `config/agents/synthesizer.md` (grades on request, the people-clock offer, advance work offered as a suggestion, the R9 override); `routing_cloud.yaml` `task_judge` output cap, only if measured.
2. *Phase 2:* `synthesizer.md` (probe at mention, the intrusion ask and `answer_ask`, `lookup_public_fact`, passions); `routing_cloud.yaml` + `routing.yaml` (grant `answer_ask`, `lookup_public_fact`).
3. *Phase 3:* `synthesizer.md` (offering the weekly conversation); `routing_cloud.yaml` + `routing.yaml` (grant `record_signal`). The weekly conduct itself is in `synthesizer_scheduled_sessions.md` (Amber).

**Budget delta:** phase 2 gains two tools, their grants and conduct (~+$15–25); phase 3 gains
`record_signal` (~+$5–10). Run cost is unchanged — both tools are code, and `lookup_public_fact`
is the same capped Research call. **Revised build total ~$175–325** including the plan review.
