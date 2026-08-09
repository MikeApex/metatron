# Calendar reconciliation & open obligations — design

**Date:** 2026-08-09 · **Backlog item:** `[DB-0809-05]` (rank 6) · **Status:** designed, not built

Mike's ask, verbatim from the Inbox (2026-08-05T15:19Z): detect a calendar event that passed
without happening and prompt to reschedule; keep financial tasks (payroll) prominent in daily
proactive checks until explicitly closed. Verified 2026-08-09: neither half exists.

---

## The reframe that shapes everything below

**The system cannot detect that something did not happen.** A passed event is not evidence of a
miss — most events happen and nobody reports it. What is detectable is *absence of evidence*,
which is a far weaker claim and can only ever be a question.

So: nothing in this feature asserts a miss. It asks, or it stays silent. Any wording that tells
the user an event "was missed" is a bug, not a phrasing preference.

## Binding prior decision — found, not invented

[tools/schedule.py:28](../../tools/schedule.py) § *Why obligations are not jobs*: twenty
obligations each polling themselves daily would be ~$15/month and twenty interruptions, so the
intended shape is **"a small number of sweeps that read all tracked obligations at once, with
individual obligations living as data."**

The position is settled. The store it assumes was never built — that is the actual gap. Do not
create one scheduler job per obligation; `MAX_AGENT_JOBS = 6` and `MIN_INTERVAL_MINUTES = 360`
exist to make that impossible.

---

## Two capabilities, conflated in the item

### A — Open obligations (the payroll half)

Commitments that stay open until closed. **This half already has a proven failure**: on
2026-08-07 at 17:22 Mike said *"I thought I already told you that the Rowan transfer was handled.
That is completed."* Something was re-raising it and nothing could close it.

Today's nearest mechanism is `held_items` in [tools/context_tracker.py](../../tools/context_tracker.py)
— ephemeral session state, not durable commitment state. Hence the store.

### B — Passed-event reconciliation (the calendar half)

An event's window has passed and nothing in the record references it → *consider* asking.

---

## The layer split that makes B affordable

> **A function job may gather but must not judge. A model session may judge but must not poll.**

B runs as a `function:` job on [tools/travel_watch.py](../../tools/travel_watch.py)'s proven
shape: seen-set, report-once, returns falsy when clean, so a quiet day costs no model tokens.

But a function job has no model. It can only do crude text matching to decide whether the day's
log or conversation references an event, and that *will* produce false "no evidence" hits. So
**B must not notify.** It writes candidates; the morning session — which has judgement and
already has the context loaded — decides whether any is worth raising.

**Fixed time, not an interval.** `[DB-0808-11]` is open: `fire_function` runs no gate stack at
all, so `days`, `respect_quiet_hours` and the activity gate are ignored for every function job.
`daily_travel_check` is pinned to 06:45 for exactly this reason. Since B's output is consumed by
the morning brief rather than pushed, a fixed time costs nothing.

> **This is the second workaround around the same missing gate stack.** Decision below is to pin
> and move on, but the third one is the one that pushes at 3am. `[DB-0808-11]` should not be
> allowed to accumulate a fourth dependent.

---

## Decisions — Mike, 2026-08-09

1. **B's scope: every passed event**, not only ones tied to an obligation. A toggle for
   obligations-only is wanted later as a calibration knob — build the scope so that narrowing it
   is a config flag, not a rewrite. Still capped and report-once, and **surfaced only through the
   morning brief, never pushed** (pushing recreates the six-times-in-one-day problem).
2. **Closure is inferred**, not an explicit user action — *"in a dialogue these things will come
   up naturally."* Write the close immediately on inference, store the user's own words as its
   evidence, and make it reversible. Rationale: the 08-07 failure was that he *did* say it and
   nothing recorded it. Mirrors the backlog's own rule that closed-without-evidence is not closed.
3. **Pin to a fixed time; do not fix `[DB-0808-11]` first.** This feature does not need the gate
   stack.

---

## Implementation shape

Not yet built. Sketch only — verify against current code before starting (standing backlog rule).

| Piece | Where | Notes |
|---|---|---|
| Obligation store | `data/personas/{p}/obligations.yaml` | data, not jobs; `open`/`closed`, `closed_at`, `evidence` (user's words), reversible |
| Tools | `tools/obligations.py` | open / close / list; `close` records evidence. Register in `orchestrator.register_tools()` |
| Reconcile sweep | `tools/calendar_reconcile.py` | `function:` job, travel_watch shape, seen-set, returns candidates — **never** `{"notify": True}` |
| Scheduler entry | `config/personas/mike/scheduler.yaml` + `config/templates/scheduler.yaml` | fixed time before 07:30; template too, or new personas never get it |
| Surfacing | `config/agents/synthesizer.md` § Scheduled session conduct + `logistics.md` | morning brief reads candidates and decides; obligations resurface until closed |

**Watch:** the morning brief must not turn into a status report — the 2026-08-09 focus guidance
(one thing, length is a symptom of focus) governs. Obligations resurfacing "until closed" and
"open on one thing" pull against each other; the obligation store is what the session *may* draw
on, not a list it recites.
