### 2026-10-26, second (the day plan keeps to today, asks about shared events, and fits each task to the kind of time it needs — day planner round 2) — `8d5993a`, `4ffd9e8`, `9ae787a`, `1a32687` — **deployed by Mike; his baseline written on the VM by the setup command**

**Outgoing handoff carried:** Stage A (`45739a2`) owed a deploy and one watched day before Stage B;
the ritual-pause session is next in its own window. Mike deployed and watched 10-25.

**Watch day 1 failed four of five checks — read from the VM, not reasoned.** (1) A promotion and
Iva's voting, on shared calendars, blocked 09:00–12:15 as Mike's commitments: `caldav.py` returns
each event's calendars and `_normalise` dropped them. (2) No travel — no event carried a place; it
would have failed 10-26, because "Lunch with Victoria" matched the `ignore_titles` "lunch" prefix
and own blocks get no travel. (3) Lunch dropped into a note. (4) Schwab and the job post (due
Monday), the Chase bill and the undated TfL check placed on Sunday: `_candidates` used the head
layer's Now (two-day lead, undated one-offs), not `_on_todays_list`, **the rule Mike set for the
Today list on 10-24**. His correction could not move the panel — the ledger already said Monday,
and in Stage A the Synthesizer cannot see the plan. **Not the planner:** the 10-25 08:35 reply
said the Chase and Rowan windows were "set"; nothing was written — no field existed, and
`update_task`'s own error sent models to an action that did not exist.

**Mike's rulings (plan § 18.2, 11 of them):** a dated task is *for* its date; events get four
answers (there / needs me / someone else's / noise) resolved answer → rule → calendar role →
question; **code inferring duties is a future Family mode, not rejected**; D1 every calendar is the
user's, a later one asked about first; health outranks noise; a meal under a social event is asked;
**baselines are dynamic variables** — activity windows (protected / strong / preferred) on any set
of days, no weekday/weekend split, no single "working hours"; family time admits light,
screen-free tasks; built for every user; D2/D3 now; **ruling 11: an essential task never expires.**

**Built:** `tools/day_shape.py` sections + setup command; triage, routines with travel, meals that
slide and ask, placement by activity, the validator's V2/V6, today-only candidates; monthly
day-of-month windows overdue after their last day; `set_days` and task `activity` behind
`ledger_fields`; `answer_event` built, unregistered (Stage B). 25 round-2 checks; suites green.

**Fable review** (medium): 9 findings, verify 7 closed + F8 partial + N1 — all resolved. Worth
remembering: **the validator would have rejected every round-2 plan** (F2); role-first triage meant
no noise rule could fire on the user's own calendar (F3); a roster keyed by display name turns one
discovery failure into a blank day (N1 — keyed by collection id); the "expose `set_days` now"
exception was withdrawn (F9).

**Corrections — believed, then wrong:** I proposed ruling code-inferred duties out (Mike: Family
mode). My first R2-5 used a new calendar's events at once, against D1 (F5). I assumed Mike's "Main"
calendar was visible — it is not; the account sees Metatron, diamond.mike.mt@gmail.com, UK Holidays
and Shared with Mike, so setup's first apply refused (and printed its plan as if written —
`4ffd9e8`). My first conduct draft named Iva in a universal module. Replaying the real 10-26 day
put the gym into family time at 07:00 — `solo`/`exercise` added, beyond the reviewed plan, § 18.8.
Found live after setup: a dose recorded off-plan made the next show ✓ (`9ae787a`); Schwab and the
job post expired after one re-placement → ruling 11 (`1a32687`).

**Rejected:** inferring duties from a household model now (facts nobody stated); an unanswered
family event as a block (10-25's failure) or as free time (F6) — it holds its time for
family-compatible tasks only.

**Open → `archive/handoffs/2026-10-27-day-planner-watch-2-and-stage-b-prompt.md`:** watch day 2,
then Stage B; the boys' school hours (`children_home`); Mike's own appointments sit on the family
calendar and show as questions; the one-hour "Take out the trash" event; the false-claim phrasing.

