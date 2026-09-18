# Worked Inquiry run — `home_care`, by hand

*2026-09-18. The plan's § 15 item: "a worked Inquiry run by hand on a real Metatron gap — the
cheapest check that the spine's shape is right. A schema that survives one real pass is worth
more than one that survives review."*

**Run against the live validator, not reviewed by eye.** `validate_question_set()` with the real
manifest ids and the real capability names: **zero defects**, class sequence
`[1, 2, 2, 3, 3, 4, 5, 6, 7, 8]`, feasibility at position 7 of 10.

**This is the second real Inquiry pass in existence.** The first is the RSVP transcript's turn 4.
Per § 15's mitigation for the n=1 weakness, it becomes a fixture once run 2's REPAIR reports what
was missing from it — a pass-only example until then, deliberately not promoted to
`tests/fixtures/`.

---

## The gap

Mike filed it twice on 2026-09-08, verbatim from `DEV_BACKLOG.md` § Inbox:

> **[needs building]** Plant watering tracking check must integrate localized home weather
> (precipitation in London) to account for outdoor watering, and resolve the sync failure where
> user-reported waterings failed to update the last-watered baseline date. `2026-09-08T08:54:16Z`

> **[instruction change]** Plant watering checks failed to reflect Mike's recorded watering logs,
> remaining stuck on August 4, and failed to check home-location weather to recognise that current
> rainfall in London treats outdoor plants as watered. `2026-09-08T08:53:11Z`

The machine log carries three runs of the scheduled prompt *after* that filing — 09-11, 09-14,
09-15 — with **no specialist dispatched** on any of them.

**Depth: `standard`.** Not `deep`: nothing here is irreversible or cross-cutting. Being the first
Build run is a property of the programme, not of the capability, and treating it as `deep` on
those grounds would be the process-proportionality failure turn 4 names.

**Disposition: `new`.** Evidence, as the validator requires it to name the capability checked:

> Checked logistics, which lists watering as an obligation type and holds get_log_window,
> read_wisdom and get_weather — but it owns actions (calendar, email, bookings), not a standing
> check that reads a log and decides. On none of the three recorded runs (09-11, 09-14, 09-15)
> did the Coordinator route the prompt to logistics or to any other specialist; the 09-11 entry
> shows the Coordinator doing the arithmetic itself. So there is no evidence logistics performs
> this judgement and positive evidence that nothing does. Also checked physical_health, which
> reads no home-domain data at all.

**Generalizes to:** every recurring home obligation that has a last-done date and an interval — a cadence judgement over a last-done date, which no specialist performs for any obligation.

---

## The spine

| id | class | question | candidate sources |
|---|---|---|---|
| q1 | `integrity` | The check asserts 'Last watered Aug 4' while waterings are logged after that date — which of the two is the record, and where does the August 4 figure come from? | `log`, `context_tracker`, `wisdom` |
| q2 | `intent` | What is the household-upkeep check in service of, and what has Mike said he wants more and less of from domestic admin? | `journal`, `conversations`, `wisdom`, `goals` |
| q3 | `intent` | Does an unprompted overdue nudge serve that, work against it, or is it neutral? | `journal`, `conversations` |
| q4 | `cost` | What does a wrong or unnecessary watering nudge consume that nothing meters? | `log`, `conversations` |
| q5 | `cost` | What is the base rate — how often does a watering actually fall overdue — and what is the marginal value of a nudge at that rate? | `log`, `weather` |
| q6 | `asymmetry` | Is anything here irreversible or closing, and is there regret in both directions? | `log`, `wisdom` |
| q7 | `feasibility` | Can days-since-last-watering be computed at read time from the log, and is days_since_rain actually available for London? | `log`, `weather` |
| q8 | `surface` | What else operates on a household obligation once this exists — marking one done, snoozing it, retiring a plant, adding a second, a seasonal change of interval? | `wisdom`, `obligations`, `schedules` |
| q9 | `minimum_version` | What captures most of the value at a fraction of the cost — one obligation, one interval, one rainfall rule? | `log`, `wisdom` |
| q10 | `authority` | Does this capability act, or surface — and what is the stated default so that silence still produces an outcome? | `wisdom`, `user` |

**Declined to ask:**

- *Which plants does Mike own, and where are they?* — an inventory question, not a design question — it is data the capability reads, and asking it here would fix the design to today's plants
- *Should the check use a different scheduler cadence?* — the cadence already exists and fires correctly; the defect is what happens when it fires, so cadence is out of scope for this build

---

## What the exercise actually found

**1. The ordering changed the answer, on a real gap, not just in the transcript.** The request as
filed is a sync bug. Writing the two `intent` questions before the `feasibility` one forced the
framing note that is now in the artifact: *the class underneath the request is that nobody owns
"is this household thing overdue, given what was logged and what the weather did."* Starting at
feasibility — *can we read the log? yes → fix the sync* — produces a working sync fix and leaves
the class unowned, which is precisely the filter failure. **The compass rule earned its keep on
its second outing, against a gap nobody wrote it for.**

**2. `cost` split into two questions with different shapes, and that is correct.** Class 3 asks
both *"what does acting consume that nothing meters"* and *"what is the base rate and the marginal
value at that rate."* Those wanted separate questions (q4, q5). Two questions at one class index
is legal — the rule is non-decreasing, not strictly increasing — and it happened without being
planned. **A class is a bucket, not a slot**, which is worth knowing before the agent file is
written in phase 5.

**3. `declined_to_ask` did real work on its first use.** Both declined questions are ones a model
would plausibly ask and that would have fixed the design to today's plants. Having somewhere to
put them is what stops them being asked.

**4. THE FINDING THAT MATTERS — every compass question in this set is currently unanswerable.**
Checked against the live manifest:

| question | class | status |
|---|---|---|
| q2 *what has he said he wants more and less of* | `intent` | **needs_tool** — `search_conversations` |
| q3 *does a nudge serve that* | `intent` | **needs_tool** — `search_conversations` |
| q4 *what does a wrong nudge consume unmetered* | `cost` | **needs_tool** — `search_conversations` |
| q1, q5–q10 | all others | answerable today |

The plan says the § 9 briefs are needed because *"the Librarian's first research question — how
does Mike record a watering, and where — is unanswerable without them."* **This is sharper than
that, and it is a stronger argument for the same sequencing:** it is not one research question, it
is the whole `intent` section plus the unmetered-cost question. Stated intentions live in
conversation and journal prose, across weeks, and `read_journal` takes one date.

**The consequence, stated plainly: run 1 executed before phase 6 lands would produce a question
set whose entire compass section settles to `needs_tool`** — a capability built on feasibility and
surface alone. That is a filter, arrived at through the substrate rather than through the design,
and the spine would have been followed correctly the whole way. **Phase 6 is not a convenience
ahead of run 1; it is what stops run 1 rebuilding turn 2.**

**5. `read_journal_range` did not show as a gap, and that was a defect — now fixed.** `journal`
read as *available* because `read_journal` is registered; that it takes a single date and is
useless across 61 files was invisible. A pattern question against it would have returned one day
and settled as `no_data` — *"there is nothing recorded"* — when the truth was *"this tool cannot
be asked that."*

**The probe gained a fourth state the same day (Mike: "yes build it").** A source may now declare
which *shape* of question its tool can serve (`answers` in `manifest.py`), checked **before** the
call so a misleading row count is never produced. `journal` declares `single_point` only. The same
check re-run against this question set:

| question | class | before | after |
|---|---|---|---|
| q2, q3 *stated intentions* | `intent` | `needs_tool` (conversations) | `needs_tool` — **and `journal` now flagged `unaskable`** |
| q4 *unmetered cost* | `cost` | `needs_tool` | unchanged |
| q1, q5–q10 | — | answerable | unchanged |

`unaskable` folds into `needs_tool` for routing — both resolve as a brief Mike builds — but is
reported separately, because *"write this tool"* and *"widen this tool"* are different pieces of
work and the brief has to say which. An unregistered source is **not** reported as unaskable; they
are different problems with different fixes.

**The inference is imperfect and its error direction was chosen.** A single-date question naming
`journal` will read as behavioural and report `unaskable`, costing one unnecessary brief Mike can
see and reject. The opposite error is silent and builds a capability on a false premise. A visible
false positive beats a silent false negative — the same trade the three original probe states rest
on. Tests: `tests/test_build_probe.py` (6 checks), `tests/test_build_manifest.py` (3).
