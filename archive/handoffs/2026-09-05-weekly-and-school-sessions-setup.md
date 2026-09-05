# Two sessions to add to Mike's persona config — 2026-09-05

**These are `Denied`-tier edits: `config/personas/mike*` is VM-owned and Claude Code cannot
write them.** Everything below is prepared to paste. The tool-side half is already built,
committed and inert until these land — `session_kind()` matches a turn against the persona's
**configured prompts**, so an absent entry means the new block simply never fires. Code first,
config second, which is the standing rule.

Origin: Mike's correction in exchange `004`, 2026-09-05 — *"Evening wrap up is where tomorrow's
horizon should lie. Weekly meeting should go over the week's coming obligations. Meet about
Manny's school would cover those things specifically school and Manny related."* The evening
half shipped. These are the other two.

**Mike's ruling on where each belongs, 2026-09-05:** the weekly check-in is a **tool-level**
concern; the school check-in is **persona-level**. That split is why only one of them has code
behind it.

---

## 1. `weekly_review` — tool-level behaviour, persona-level schedule

Paste into `~/multi-model-mcp/config/personas/mike/scheduler.yaml` under `schedules:`.

```yaml
  weekly_review:
    enabled: true
    day: monday             # monday | tuesday | ... | sunday
    time: "08:30"
    agent: coordinator
    prompt: "Weekly review. Go through the week ahead — what is committed, what is due, and anything that needs something done first. Cover the whole week, including things already mentioned."
    notification: push
    # The counterweight to the horizon proximity gate: ordinary turns hold anything
    # past tomorrow, so a Friday commitment is seen here or not until it is nearly due.
```

**On the time — the one thing worth a second's thought before pasting.** `morning_brief` runs
07:30 daily, and the scheduled-session conduct says morning and evening sessions are *not
interruptible*. 08:30 puts an hour between them; anything tighter risks two proactive sessions
treading on each other every Monday. Move it later freely — the behaviour does not depend on
the hour. **Do not move it to Sunday 09:00 or 09:30**, which are the pattern-miner and physical
review.

**What is already built and will start working the moment this entry exists:**

- `week_block()` in `tools/horizon.py` — the coming seven days, **including findings already
  delivered**, read-only (charges no offer, marks nothing delivered).
- Dispatch in `core/orchestrator._horizon_block()` on `session == "weekly_review"`.
- Conduct in `config/modules/synthesizer_scheduled_sessions.md` § Weekly review — three phases,
  opening on the week's *shape* before any item.

`day:` is validated since 2026-09-05 (`[DB-0903-02]`), so a mistyped day name now fails loudly
rather than silently never firing. That was worth having for exactly this.

---

## 2. `manny_school` — persona-level, no tool code at all

Two files, both in `~/multi-model-mcp/config/personas/mike/`.

### 2a. The schedule entry

```yaml
  manny_school:
    enabled: true
    day: wednesday          # CADENCE IS YOURS TO SET — see below
    time: "19:30"
    agent: coordinator
    prompt: "Manny's school check-in. Go through anything school or Manny related that is coming up or outstanding — forms, dates, fees, clubs, appointments, things needing a decision."
    notification: push
```

**The cadence is the one thing I could not derive, so it is marked rather than guessed.**
Options, with a recommendation:

1. **Weekly, term-time evening (recommended)** — Wednesday 19:30 as written. School admin
   arrives on a weekly rhythm and a week is short enough that nothing dated goes stale between
   check-ins. Costs one proactive session a week.
2. **Fortnightly** — halves the interruption, but a form that arrives the day after one
   check-in waits nearly two weeks for its session. Safe only because of the decision below.
3. **Termly** — matches how school milestones actually cluster, but far too coarse for
   anything dated; it becomes a planning conversation, not a check-in.

I would take (1) and drop to (2) if it proves quiet.

### 2b. `manny_school_ritual.md`

The ownership rule in `core/orchestrator._owned_rituals()` is **`X_ritual.md` belongs to
schedule key `X`** — so this filename binds the content to the `manny_school` session and to
nothing else. It is injected into that session and no other, exactly as `evening_ritual.md` is
today. Nothing needs to be registered.

```markdown
# Manny's school check-in

This session covers one subject: Manny and his schooling. Everything else waits.

**Go through what is actually outstanding, not a survey of school in general.** Forms to
return, dates to put in the calendar, fees or payments due, clubs and activities needing a
decision, appointments to make, anything a teacher or the school has asked for. If something
has a date on it, say the date.

**Lead with whatever needs doing first, not whatever happens first.** A permission slip due
Friday outranks a trip in three weeks, even though the trip is the larger thing. Where
something needs a step before it can happen — a payment, a booking, a form — that step is the
item, and its deadline is the one that matters.

**Raise things here whether or not they have come up elsewhere.** This is a review of a
subject, so repetition within it is the point. Outside this session the ordinary rule holds
and nothing changes: a school item near enough or urgent enough still surfaces on any turn, so
nothing waits on this check-in to be heard. This session guarantees coverage; it does not hold
anything back. *(Mike's decision, 2026-09-05: guarantee, do not suppress — a form due tomorrow
must never sit silent waiting for a Wednesday.)*

**End on what needs a decision from Mike**, and ask it plainly. One or two things, not a list.
If genuinely nothing is outstanding, say so in a line and ask how Manny is getting on — that is
the fallback, not the usual shape.
```

---

## The known limit of the school session, stated so it is not discovered later

**Nothing tags a horizon finding as school-related.** `record_horizon_item()` carries `title`,
`date`, `venue`, `kind`, `detail` and the two new precursor fields — there is no topic. A
`topic` field filled by Logistics was proposed and **withdrawn on Mike's ruling that the school
half is persona-level, not a tool concern.**

The consequence: this session scopes itself by its *prompt and conduct*, so the model picks
school material out of the context it already has. That is a model judgement, and it will
occasionally miss something worded without an obvious school cue, or pull in something
adjacent. It is cheap and correctable, and it costs no tool surface.

**It is also low-risk, because of the guarantee-don't-suppress decision.** A school item missed
by this session is not lost — it still surfaces on an ordinary turn when it comes near or its
precursor falls due, like anything else. Had suppression been chosen, this limitation would
have been serious rather than cosmetic.

If it does prove to miss things in practice, the fix is the `topic` field, and it is a small
build: one optional argument on `record_horizon_item`, one line in `logistics.md`, one
predicate in `tools/horizon.py`.

---

## After pasting

1. `sudo systemctl restart metatron-scheduler` on the VM — the scheduler reads `scheduler.yaml`
   at start.
2. Confirm the entries parsed: the day-name validator will refuse a bad `day:` loudly.
3. First real firing is the proof. Nothing here can be verified from the Mac.
