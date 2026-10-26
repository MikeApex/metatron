Model: Opus 5.5 — the watch review needs the round-2 context, and Stage B is Red tier, built by hand with Mike present (Red is never delegated).

# Day planner — watch day 2 (round 2), then Stage B (continuation prompt)

**Budget:** watch review ~15 Mike-minutes, ~0.3–0.5M Opus tokens on the subscription. Stage B as
its handoff states (~60–90 Mike-minutes, ~1–2M Opus). Run cost once Stage B's flags are on: plan
§ 12 (~$0.10–0.30/day reshuffles, nudge wakes roughly neutral); round 2 itself added ~2 Google
Routes lookups/day (the weekday lunch routine), inside the 60/day cap, which no spend meter sees.

**Where things stand (2026-10-26, all deployed by Mike):** watch day 1 (10-25) failed four of
five checks; round 2 (plan § 18) rebuilt the planner around a dynamic per-user day shape, event
triage and placement by activity; Fable reviewed it (9 findings + 1 on verify, all resolved);
Mike's baseline was written on the VM with the setup command and confirmed landed (20 entries;
calendars: Metatron, diamond.mike.mt@gmail.com and UK Holidays → mine, Shared with Mike → family).
Commits: `8d5993a` (round 2), `4ffd9e8`, `9ae787a`, `1a32687` (an essential task no longer
expires — Mike's ruling 11). Record: `archive/PROJECT_LOG.md` § 2026-10-26.

---

/metatron-code Day planner: watch day 2, then Stage B with Mike present. Read first, in full:
`archive/plans/day_planner_plan_2026-10-24.md` § 18 (rulings, the variable model, R2 items, the
review table, build notes), then `archive/handoffs/2026-10-24-day-planner-stage-b-prompt.md`
(revised 2026-10-26 — every draft in it was updated for round 2).

## 1. Watch day 2 — Tuesday 2026-10-27 (plan § 18.5 acceptance)

Ask Mike what he saw first, then verify on the VM — read-only, never write there. There is no
script for reading VM data files; this is the pattern used on 10-26 (the `/monitor/file`
endpoint, a token minted locally exactly as `scripts/sync_dev_backlog.py` does):

```python
import sys, json, urllib.request, urllib.parse
sys.path.insert(0, "/Users/md-homefolder/Desktop/multi-model-mcp")
from core.auth import bearer_header
S = "https://metatron-vm.tail0acc5d.ts.net:8001"
def vm(path):
    url = f"{S}/monitor/file?" + urllib.parse.urlencode({"path": path})
    with urllib.request.urlopen(urllib.request.Request(url, headers=bearer_header(ttl_seconds=300)), timeout=20) as r:
        return json.loads(r.read()).get("content")
# vm("data/personas/mike/day_plan/plan_2026-10-27.json"), ".../state.json", ".../log.jsonl",
# vm("data/personas/mike/day_shape.yaml"), vm("data/personas/mike/tasks.yaml")
```
`GET /plan/today?persona=mike` with the same header returns what the panel shows — and, like the
panel's poll, triggers a rebuild if one is due.

The checks, each against the plan file and the snapshot (which now records every event's
calendars):
1. Family time 07:00–10:00 and 17:30–20:30 holds only light, screen-free tasks (stretching,
   chores, errands); no admin, focus or exercise in it.
2. The weekday lunch with Iva 12:00–13:00 is there, with "leave for" and "home from" rows.
3. Admin and focused work sit between 10:00 and 17:30.
4. Only Tuesday's tasks — nothing due later, nothing undated, no monthly bill on an ordinary day.
5. Shared-calendar events ("Marta and kids over for dinner" 17:30–21:30, anything else on Shared
   with Mike) show as "— anything needed from you?", their time held from screen work; dinner is
   placed inside with "is that also dinner?".
6. An essential task whose slot passed unconfirmed is moved, not dropped, and shows once
   (ruling 11). Check 10-26 as well: Schwab and the job post should have been re-placed into the
   afternoon admin window from the 12:00 rebuild on (`plan_2026-10-26.json` is kept 3 days).
7. `log.jsonl`: every build `failures: 0`; note any `fail_rules`.
8. Stretching (twice daily) shows the right status on each block (the `9ae787a` fix).

**Anything wrong is fixed (Amber) before Stage B** — Stage B's prerequisite 2. Run
`tests/test_day_plan_round2.py`, `tests/test_day_plan_engine.py` and `scripts/qa_sweep.sh`
after any change; `git diff` every file before staging — other windows share this tree.

## 2. Stage B — the one Red session

Follow `archive/handoffs/2026-10-24-day-planner-stage-b-prompt.md` A–K, against the files as they
are now. Before applying, check whether the ritual-pause session
(`archive/handoffs/2026-10-25-ritual-pause-and-ledger-followups-prompt.md`; `tools/rituals.py` was
still an untracked draft on 10-26) has landed — it edits the same Red files (`synthesizer.md`
§ Tools, both routing files, `register_tools()`), and whichever lands second re-applies.

Two Stage B additions from 10-26, already in the handoff but easy to miss:
- **`answer_event` is built, not registered** — handoff § B gives the three Amber lines
  (`core/orchestrator.py` import + handler, `core/actions.py`) that go in with its Red grant.
- **After K1 turns `ledger_fields` on, Mike re-states two monthly windows in the app** so they are
  actually recorded with `set_days`: the Chase card bill (deal with it from the 10th, pay by the
  15th) and Rowan's payroll transfer (after the 1st, by the 5th). On 10-25 a reply told Mike both
  were "set" — nothing was written, because no field or action for it existed then. Check the
  ledger afterwards that both carry `on_days`.

**Decision D1 (plan § 14) is still Mike's:** phone delivery — recommendation (a) for now, native
push as Stage C once a week of plan-reading is trusted.

## 3. Outstanding from the 10-25/26 chat — put each to Mike; file nothing he did not ask for

1. **The boys' school days and hours, and their bedtimes → `children_home`.** Until given, a
   childcare duty blocks the whole event, even while the boys are at school — e.g. a weekday
   admissions session would take Mike's best work hours. One setup entry, or leave it to Family
   mode and answer case by case. Recommend asking now; it is two numbers per child.
2. **Mike's own appointments on the family calendar show as questions.** Bupa (10-26), Marta's
   dinner and "Pay nursery" are only on Shared with Mike; Lunch with Victoria is also on the
   Metatron account's calendar, so it counted as his. Decide from watch day 2: keep (answer each
   once via `answer_event` in Stage B — and three alike answers offer a standing rule), or share
   his Main calendar with diamond.mike.mt@gmail.com, tick it at
   calendar.google.com/calendar/syncselect for that account, and re-run setup with
   `"Main": mine` (it will appear as a new calendar and be left out until then).
3. **"Take out the trash" is a one-hour event on the Metatron calendar** — it holds 19:00–20:00
   and turns dinner into a question. Recommend Mike shortens it to 10 minutes.
4. **The weekly grocery habit is off the plan in its first, partial week** — the Today list's rule
   (a part-week does not nag). Mike did not object; confirm it reads right once a full week starts.
5. **The false "set" claim (10-25 08:35)** — the reply said the Chase and Rowan windows were set
   when nothing was written; the action-claim check did not catch "is set to surface". The
   capability now exists (Stage B), but whether the claim check should catch that phrasing is a
   separate question — Mike decides whether it is worth a backlog item.
6. **Evidence for SESSION.md's "the 'Benny' contact may be a phantom" item:** the ledger holds
   "Look up swim lessons at Wavelengths Pool for Manny and Benny", and Mike spoke of "both boys"
   on 10-26 — suggesting Benny is real. Put it to Mike; do not act on it.
7. **Family mode** (code working out duties from who is home) is a planned future feature —
   recorded in memory and plan § 18.2; nothing to do now.

Close with `/archive`. Anything that did not pass is a backlog item with the evidence that failed.
