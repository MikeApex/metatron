### 2026-09-07 (both new sessions verified firing on live schedule — and a fourth silent-success mechanism found) — no code changes; `SESSION.md` correction only — **VM at `471373a` + persona config; `origin/main` at `4db2640`**

Mike reported that *"some of the commands don't fire — Manny school didn't occur this week."*
**Both new sessions had in fact fired correctly.** Recording it because the premise was wrong in
an instructive way, and because the investigation turned up a fourth instance of this week's
recurring pattern.

#### What the evidence showed

- `Sep 06 16:00:03 — [scheduler] [mike] firing manny_school (coordinator)`. The session produced
  a correct, complete reply — *"There are no outstanding school forms, fees, or calendar
  deadlines on file for Manny this week, Mike. How is he getting on?"* — recorded as seq 006 in
  `data/personas/mike/conversations/2026-09-06.jsonl`. That is `manny_school_ritual.md`'s
  nothing-outstanding fallback working verbatim, **including the closing question**.
- `Sep 07 07:30:57` — the Monday `morning_brief` carried the week: *"For commitments across the
  next seven days: today is the mailing deadline for the Allied Mover damages claim… On Saturday,
  the Children's Service for Rosh Hashana… On Sunday night, Jimmy Carr at the London Palladium."*
  `weekly_review_on: monday` and `week_block()` are live and correct.

`manny_school: sunday at 16:00` registered at the 18:05 restart on 09-05 and fired the next day.
**No config change was needed and none was made.**

#### The likely reason it read as a no-show

The school check-in **had nothing to report**, so it said one unremarkable line. A session that
correctly finds nothing outstanding is indistinguishable, from the outside, from a session that
never ran. Not a defect — but worth knowing that the first firing of a new proactive session is
its least visible one, so "did it fire" should be answered from the scheduler log, not from
memory of what arrived on the phone.

#### Corrections to what this project believed before today

- **`SESSION.md` said the persona pastes were "still undone — verified absent on the VM", and
  that the weekly and school sessions "cannot fire yet."** True when written on 09-05; false by
  09-06. Mike pasted them the same evening. Corrected in the primer this session — the sole
  reason this archive ran at all.
- **A claim made mid-session and withdrawn within the hour:** that the school session "never
  reached" Mike. Push was then tested directly and returned `{'sent': 18, 'errors': []}`.
  Push works; the reply was delivered.

#### Fourth silent-success mechanism this week — found, not fixed, not filed

`core/push.py send_push()` **returns** `{"sent": N, "errors": [...]}` and does not raise.
`core/scheduler.py _notify_push()` discards that return and logs only exceptions. So a push
reaching **nobody** — no VAPID key, no subscriptions, every endpoint dead — is indistinguishable
from one reaching everybody, and **nothing is written to any log either way**. It happened to
work today; nothing would have said so had it not.

Same shape as the three found on 09-05 (the calendar delete that succeeded on the wrong event,
the redundancy guard citing a line that held no rule, the Diarist reporting a journal write that
landed 159 days back). **Mike was offered the one-line fix and closed out instead — deliberately
not filed**, per the standing rule against filing what he did not ask for.

**Also observed, unresolved:** 18 push subscriptions on file, all `web.push.apple.com`, all live
— they accumulate as the PWA re-registers and are only pruned on a 404/410. Every notification
may therefore be delivered up to 18 times. Not investigated further.

**Still true and unchanged:** the 2:44 quiet check-in still drops its closing question — seq 007
on 09-06, *"All quiet on this end, Mike."* Thirty-nine minutes after the school session obeyed
an equivalent instruction. **The difference is specificity: `manny_school_ritual.md` names the
question to ask; the general conduct buries it as a subordinate clause called "the fallback, not
the usual shape."** That is a useful data point for the structural gate Mike deferred on 09-05.

