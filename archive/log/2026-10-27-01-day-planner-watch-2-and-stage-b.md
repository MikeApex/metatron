### 2026-10-27 (day-planner watch day 2, then Stage B built, deployed and switched on) — `tools/day_plan.py`, `tools/obligations.py`, `config/modules/{day_shape,day_plan}.yaml`, `config/modules/{synthesizer_day_plan,synthesizer_scheduled_sessions}.md`, `config/agents/{day_planner,coordinator,goals_interviewer,synthesizer}.md`, both routing files, `core/{orchestrator,scheduler,actions}.py`, tests — `8082016`, `9f2eeac`, `5252661`, `d38efc7`, `46038c8`, `e3a85b9` — **all deployed by Mike in-session; step 1 flags live**

**Outgoing handoff carried:** `archive/handoffs/2026-10-27-day-planner-watch-2-and-stage-b-prompt.md`
— watch day 2, then Stage B A–K. **Consumed** except K2 (nudges/owns_checkins) and J2/J3.

**Watch day 2: 4 of 8 checks failed, every failure a thing Mike had said that nothing could
record.** "Handle mover claims" (no domain → `personal`, family-compatible) planned into family
time three times after Mike said admin waits for school drop-off; Iva's Bancone lunch on the
Metatron account counted as his, with travel; the Synthesizer opened a duplicate undated "Mover
claims admin" instead of correcting the task; four "over the next week" tasks written undated, so
never planned; "dinner prep queued for 16:30" claimed and not written; the Canary Wharf event
written with its place only in the title and "user" in it; Marta's dinner read as two entries.

**Fixed before Stage B (`8082016`):** unknown activity defaults to `busy` (screen work — F6's
direction); title words checked admin-first (so "look up swim lessons" is not a swim), household
and errands before the domain table; a meal asked about inside an event is one row on the panel.

**Stage B (`9f2eeac`)** — A–F as drafted, plus, at Mike's request: a "sometime by" window
(`flexible` + `after` on a deadline, `set_window`; a candidate every day of its window, essential
only on its last day, listed on the panel only on a day the plan placed it); task lengths
code-raised (`length_ask`, each task once ever, two a day); salience in the brief and close
(Mike: "a question of what is salient, as opposed to raising everything" — **not** a reversal of
"Tomorrow, in full"); corrections change the task. Coordinator's misheard-name example no longer
names Mike's sons — "it's Manny, not Benny" primed it to hear a real child as a mishearing.
**Benny is real** (Benjamin; a live contact; no Benny→Manny correction stored) — the SESSION.md
"phantom" item is closed.

**Found building it:** a kept slot outranked a must-do — a morning nice-to-have held its place and
a task due today came out "not placed". Fill now re-runs keeping only frozen or ≥-score slots.

**Believed true, wrong, twice (then fixed):** that 8,192 was enough for the day planner. Smoke run 1 failed
3/3 at the plain path's fixed 4,096 (the 10-26 fix widened only the cached path) → `5252661`
gave it 8,192 → smoke passed 3/3 (churn 0/0/2, thinking 3.1k–6.9k) → **both live reshuffles that
afternoon came back unparseable at ~7,800 thinking + output = 8,188.** The code plan stands, so
no user harm; ~$0.03 wasted each. Mike chose not to switch it off yet (unanswered); a thinking
cap on the compat path is unverified.

**Live (`d38efc7` step 1 on):** plan block and conduct confirmed in the Synthesizer's input (the
length-ask stamp); "what should I do now?" answered from the plan. A kept admin slot at 21:30
survived its task's reclassification → `46038c8` releases kept slots outside a strong window.
Mike's item-13 message hit a Vertex **429** (Google capacity — no day-planner call was in flight)
after Logistics had written durations, windows and the dismissal; Logistics opened another
duplicate and skipped `set_days` → `e3a85b9` puts the correction rule in the task tool's own
description and refuses a task sharing two identifying words with an open one (soft;
`new_instance` passes; sourced tasks exempt). Follow-up message: all recorded, incl. the first
live `answer_event`. **Seen, not fixed:** Logistics, Finance and the Synthesizer wrote the same
`set_days` in parallel; Finance's was `["10","15"]` (two days) — right only because a correct
write landed last.

**After the first close-out (`08ee9d0`, `d698019`, `b04989a`, `d1f9017`):** Mike chose more room
over a thinking cap → day_planner 16,384. Smoke: 3/3 parseable and valid, thinking 9,927 /
11,557 / 13,225, latency 80 / 203 / 69 s, churn 0 / 4 / 0 (run 2 failed only the churn rule — an
equally valid arrangement from the same seed). **In every run the model fitted mover claims, the
essential the code plan had left "not placed", by moving lower items** — the rearrangement the
code fill cannot make, so the model earns its ~$0.04–0.05 a call (~$0.20–0.40/day, a little over
plan § 12). Keep-as-is recommended; **Mike had not decided at close.** Backlog: the plants-interval
check passed and closed; nothing else this session finished.

**Decisions (Mike):** D1 = (b) native push with the app closed → Stage C. Order: second-user
build next, Stage C after it (lands on per-user push), then step 2. Stage C and the second-user
build are **not** concurrent — same push, server-route, scheduler-notify and APK files.

