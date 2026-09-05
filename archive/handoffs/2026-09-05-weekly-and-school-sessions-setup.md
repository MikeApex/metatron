# Persona config to add on the VM — 2026-09-05

**`config/personas/mike*` is `Denied`-tier and VM-owned; the Mac copy is not authoritative.**
Everything here is a command to run **on the VM**, ready to paste. The tool-side half is built,
committed and inert until these land: `session_kind()` matches a turn against the persona's
**configured prompts**, so an absent entry cannot fire. Code first, config second.

Origin: Mike's correction in exchange `004`, 2026-09-05 — *"Evening wrap up is where tomorrow's
horizon should lie. Weekly meeting should go over the week's coming obligations. Meet about
Manny's school would cover those things specifically school and Manny related."*

Mike's two rulings that shaped the build: the **weekly check-in is tool-level**, the **school
check-in is persona-level**. And the weekly is a **setting, not a fixed session** — it can ride
a brief he already has rather than adding a proactive interruption to his week.

---

## 1. The weekly review — one line, no new session (recommended)

`weekly_review_on: <weekday>` on **any** schedule entry makes that session carry the week-ahead
digest on that day and no other. The recommended shape adds nothing to Mike's week:

```bash
cd ~/multi-model-mcp
cp config/personas/mike/scheduler.yaml \
   config/personas/mike/scheduler.yaml.bak-$(date +%Y%m%d-%H%M%S)

python3 - <<'PY'
import re, pathlib
p = pathlib.Path("config/personas/mike/scheduler.yaml")
s = p.read_text()
assert "weekly_review_on" not in s, "already set — nothing to do"
# Insert the key into the existing morning_brief entry, right after its `enabled:` line.
s = re.sub(r"(?m)^(  morning_brief:\n(?:.*\n)*?    enabled: .*\n)",
           r"\1    weekly_review_on: monday   # week-ahead digest rides Monday's brief\n",
           s, count=1)
assert "weekly_review_on" in s, "morning_brief entry not found — insert by hand"
p.write_text(s)
print(s[s.index("  morning_brief:"):][:400])
PY

sudo systemctl restart metatron-scheduler
```

**What it does:** on Mondays the morning brief also carries the coming seven days —
already-raised items included, since it is a review. The other six mornings are unchanged.

**The alternative, if a standalone slot is preferred later.** Add this instead; the same code
serves it, and `weekly_review` needs no `weekly_review_on` key because the session key alone is
enough:

```yaml
  weekly_review:
    enabled: true
    day: monday
    time: "08:30"
    agent: coordinator
    prompt: "Weekly review. Go through the week ahead — what is committed, what is due, and anything that needs something done first. Cover the whole week, including things already mentioned."
    notification: push
```

If that route is taken, keep it clear of 07:30 (`morning_brief`) — scheduled sessions are
non-interruptible, and two proactive turns thirty minutes apart every Monday would grate. That
adjacency is the whole reason the setting exists.

---

## 2. Manny's school check-in — Sunday afternoon, persona-level, no tool code

Two files. Sunday 16:00 is clear of the 09:00 pattern-miner and 09:30 physical review.

```bash
cd ~/multi-model-mcp
cp config/personas/mike/scheduler.yaml \
   config/personas/mike/scheduler.yaml.bak-$(date +%Y%m%d-%H%M%S)

cat >> config/personas/mike/scheduler.yaml <<'YAML'
  manny_school:
    enabled: true
    day: sunday             # monday | tuesday | ... | sunday
    time: "16:00"
    agent: coordinator
    prompt: "Manny's school check-in. Go through anything school or Manny related that is coming up or outstanding — forms, dates, fees, clubs, appointments, things needing a decision."
    notification: push
YAML

cat > config/personas/mike/manny_school_ritual.md <<'MD'
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

**It is Sunday afternoon, so the week ahead is the natural frame.** What lands this coming week
comes first; anything further out is worth a line only if something has to be done about it
now.

**Raise things here whether or not they have come up elsewhere.** This is a review of a
subject, so repetition within it is the point. Outside this session the ordinary rule holds and
nothing changes: a school item near enough or urgent enough still surfaces on any turn, so
nothing waits on this check-in to be heard. This session guarantees coverage; it does not hold
anything back. *(Mike's decision, 2026-09-05: guarantee, do not suppress — a form due tomorrow
must never sit silent waiting for Sunday.)*

**End on what needs a decision from Mike**, and ask it plainly. One or two things, not a list.
If genuinely nothing is outstanding, say so in a line and ask how Manny is getting on — that is
the fallback, not the usual shape.
MD

sudo systemctl restart metatron-scheduler
```

**Nothing needs registering.** `core/orchestrator._owned_rituals()` binds `X_ritual.md` to
schedule key `X`, so `manny_school_ritual.md` is injected into the `manny_school` session and
into no other — exactly as `evening_ritual.md` is today.

---

## Verify

```bash
cd ~/multi-model-mcp
python3 -c "
import yaml
c = yaml.safe_load(open('config/personas/mike/scheduler.yaml'))
for k, v in c['schedules'].items():
    print(f\"{k:24} day={v.get('day') or v.get('days')!s:10} time={v.get('time')!s:8} weekly={v.get('weekly_review_on')}\")
"
sudo systemctl status metatron-scheduler --no-pager | head -5
```

`day:` is validated since 2026-09-05 (`[DB-0903-02]`), so a mistyped weekday now fails loudly
rather than silently never firing.

**First real firing is the proof — none of this can be verified from the Mac.** Sunday 16:00 and
Monday 07:30 are the two to watch.

---

## The known limit of the school session

**Nothing tags a horizon finding as school-related.** `record_horizon_item()` carries `title`,
`date`, `venue`, `kind`, `detail` and the two precursor fields — no topic. A `topic` field
filled by Logistics was proposed and **withdrawn on Mike's ruling that the school half is
persona-level, not a tool concern.**

So this session scopes itself by its prompt and conduct: the model picks school material out of
context it already has. That is a model judgement, and it will occasionally miss something
worded without an obvious school cue.

**Low-risk, because of the guarantee-don't-suppress decision.** A school item missed here is not
lost — it still surfaces on an ordinary turn when it comes near or its precursor falls due. Had
suppression been chosen, this would have been serious rather than cosmetic.

If it does miss things in practice the fix is the `topic` field, and it is small: one optional
argument on `record_horizon_item`, one line in `logistics.md`, one predicate in
`tools/horizon.py`.
