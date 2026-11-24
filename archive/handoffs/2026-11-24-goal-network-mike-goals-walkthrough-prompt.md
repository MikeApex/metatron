Model: Opus 5.5 — guiding Mike live through his own goals and judging whether each talk was a real trade-off conversation is judgement work; nothing here is built.

# `mike`'s goals walkthrough — every goal talked through, and Bulgarian made plannable (§ 4.6)

**Mike-gated: a walkthrough, not a wait** (CLAUDE.md § Mike-gated work). Mike talks to his
Metatron in the app; you prepare each step, read the VM through what Mike pastes (`config/personas/**`
is VM-owned and Denied here — never write it from the Mac), and judge each step against its pass
line. ~60–90 min with Mike, in one sitting or two.

Plan: `archive/plans/goal_task_network_plan_2026-11-18.md` § 4.6 (the walkthrough), § 11 (`mike`'s
live goals, read 11-18), § 17 (part A), § 18 (part B — the goal talk this walkthrough uses).

## Read first

1. `SESSION.md` — is part B deployed, and which flags are on?
2. Plan § 11 and § 18.
3. `archive/handoffs/2026-11-24-goal-network-phase-3a-live-check-prompt.md` § Stage 2 — this
   walkthrough is what makes its step 1 true.

## Preconditions — stop if any is not met

1. **Parts A and B are on the VM.** Mike deploys (`./deploy.sh` is his). Confirm the VM's HEAD
   includes both commits (§ 17 and § 18 name them).
2. **The language playbook has landed** (its own Mike-led chat,
   `archive/handoffs/2026-11-24-language-playbook-prompt.md`). Without it the Bulgarian talk starts
   from a public lookup instead — it still works, but Mike ruled the playbook comes before
   Bulgarian is planned for real. If it is not there, do steps 1–3 now and step 4 after it lands.
3. **Flags.** Mike sets `goal_talk: true` in `config/modules/day_plan.yaml`, commits, deploys.
   `rolling_wave` stays as part A's live check has it (off until its Stage 2). With it off, the
   verdict still records the full pass; the plan is made on the first tick after it is flipped.
   `satisfaction_gap` stays off — it is not part of this walkthrough.

## Step 1 — what is there now (Mike runs on the VM, pastes the output)

```
cd ~/multi-model-mcp && .venv/bin/python - <<'EOF'
import yaml; from pathlib import Path
g = yaml.safe_load(Path("config/personas/mike/goals.yaml").read_text()) or {}
for h, items in g.items():
    for x in items or []:
        if isinstance(x, dict):
            v = x.get("vetted") or {}
            print(h, x.get("id"), "|", x.get("title"), "|", x.get("status", "active"), "|",
                  x.get("size"), "| pass:", v.get("pass"), "| parent:", x.get("parent_goal"))
EOF
```

**Expect (§ 11):** 13 goals across daily, weekly, quarterly (and `long` if anything moved there);
every one has an id (the four given ids on 11-18 included); `q4` Bulgarian, `q5` UK taxes, `q6`
the insurance review; `q2` is "Metatron work this quarter". Anything missing, duplicated or
without an id: note it, and fix it in step 2 through Metatron, never from here.

## Step 2 — each existing goal, talked through with Synth (ordinary chat)

Mike opens with something like *"Let's go through my goals one at a time — is each still right?"*
For each goal, in order (daily, weekly, quarterly), Synth should settle in a turn or two: still
wanted, what has changed, its size (S/M/L), and its status. Mike supplies any new goals as they
come up.

Give particular attention to:
1. **`q2` "Metatron work this quarter"** — its four outcomes are Claude Code's draft (§ 11). Mike
   confirms, edits or replaces them through Synth.
2. **`d1` Bulgarian Vocabulary** — stays a daily habit under `q4` (`parent_goal: q4`); it is the
   practice, not a step.
3. **`q5` taxes and `q6` insurance** — M obligations, already under phase 2's planner; only the
   date and the ranking are checked, never whether he wants to.
4. **Any goal Synth sizes L** — Synth offers a proper talk ("now, or whenever you say?"). For any
   goal but Bulgarian, Mike chooses "later": its talk task appears on a later day, and that is
   the check that the offer and the task work.

**Pass, per goal:** the change Mike states is recorded in the turn (Step 5 shows it); Synth asks
at most one question per goal; nothing internal is said (no "vet", "size L", "full pass").

## Step 3 — Bulgarian: the talk

Mike says *"Let's talk Bulgarian through properly — now."* (If `q4` has no size yet, Synth sizes it
L first and offers the talk; Mike says yes.)

**Pass, all of:**
1. Synth answers in one line that they'll talk it through now, and **the next message is the
   Interviewer's opening** — Mike does not have to prompt it.
2. The talk stays on Bulgarian and covers, in Mike's words: what "better" means when done; where
   he is now; why now; what it takes from a real week, named against his week ("which evening
   goes?"); minutes a week; by when, if there is a date; one "want, or should want?" check.
3. **Realism:** the talk names stages and the effort they usually take (from the language
   playbook, or the looked-up guide); if his minutes do not reach his date, that is put to him as
   a question with the choice — more time, a later date, or a smaller "done".
4. About 8–15 turns (the verdict is refused before 4 of Mike's own messages). If more is needed,
   it offers to carry on now or another day; a day he picks brings the talk task back that day.
5. It ends with a sentence on what happens next, and **Mike's next message goes back to the usual
   conversation**.
6. Never said: "full pass", "vetted", "re-interview", "goal talk", any tool or agent name.

## Step 4 — the VM read: `q4` became plannable (Mike runs, pastes)

```
cd ~/multi-model-mcp && .venv/bin/python - <<'EOF'
import json, yaml; from pathlib import Path
g = yaml.safe_load(Path("config/personas/mike/goals.yaml").read_text()) or {}
q4 = next(x for v in g.values() if isinstance(v, list) for x in v
          if isinstance(x, dict) and x.get("id") == "q4")
print({k: q4.get(k) for k in ("status", "size", "weekly_minutes", "due", "done_means",
                              "starting_point", "effort_hours")})
print("vetted:", q4.get("vetted"))
d = Path("data/personas/mike")
t = json.loads((d / "interview/goal_talk.json").read_text())
print("talk now:", t.get("talk"))
last = (t.get("past") or [{}])[-1]
print("last talk:", {k: last.get(k) for k in ("goal_id", "verdict", "turns", "ended_at")},
      "| started from:", (last.get("shape") or {}).get("source"))
tasks = yaml.safe_load((d / "tasks.yaml").read_text()) or {}
for x in tasks.get("tasks") or []:
    if str(x.get("source_id", "")).startswith("goal_talk:q4"):
        print("talk task:", x.get("status"), x.get("evidence"))
pj = d / "day_plan/projects.json"
r = (json.loads(pj.read_text()).get("requests") or {}).get("q4") if pj.exists() else None
print("plan request:", None if not r else {k: r.get(k) for k in ("status", "size",
      "weekly_minutes", "by")}, "| milestones:", len((r or {}).get("milestones") or []))
for line in (d / "day_plan/log.jsonl").read_text().splitlines()[-400:]:
    if '"GOAL_TALK' in line:
        print(line)
EOF
```

**Pass:** `status: active`, `size: L`, `weekly_minutes` and `done_means` set; `vetted.pass: full`
with `by: goals_interviewer`; `talk now: None`; last talk `goal_id: q4`, `verdict: active`, started
from `playbook` (or `research` if the playbook had not landed); the talk task `done`, evidence
"talked through…"; log rows `GOAL_TALK_TASK` → `GOAL_TALK_START` → `GOAL_TALK_RESEARCH` (only when
no playbook) → `GOAL_TALK_DONE`. **Plan request:** with `rolling_wave` off, `None` — expected; with it
on, `queued` (by `sweep`) on the next daily tick, then `planned` with milestones. **Fail** if
`pass` is `short` (the verdict did not come from the talk) or the talk is still active.

## Close

1. Record what was settled per goal and each pass/fail in a log fragment (`archive/log/`), with
   what was read and when. A miss is fixed in its own build, not here.
2. Hand on to part A's live check, Stage 2 (Bulgarian in waves): its step 1 is now true.
3. `/archive`.
