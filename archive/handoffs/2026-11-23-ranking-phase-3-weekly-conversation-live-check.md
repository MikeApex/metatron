Model: Sonnet 5.5 — two scheduled sessions read back with Mike; the judgement on "nagged" and "a list" is his, the session reads the VM and records.

# Ranking Part B, phase 3 — the weekly priorities conversation, two sessions (live check)

**Who runs it:** Mike, in the app, through two weekly reviews. Then a Claude Code session reads
the VM (~15 minutes in all, after the second).

**What it checks:** the weekly review now opens with a short look back, then goes on to the week
ahead. The look back covers, skipping anything that is empty:
1. what Metatron moved and why;
2. any clash it is holding, as one question with a recommendation;
3. what is slipping or about to be parked (people, money and health first), plus "keep,
   reschedule or drop?" for things raised twice with nothing new;
4. one keep-in-touch or upkeep clock;
5. "anything you wish you'd got to this week?";
6. at most one check on how things feel.

It never reads out a list. (`archive/plans/ranking_values_plan_2026-11-23.md` § 4.12, § 11c;
Mike 2026-11-23: it rides the existing weekly review.)

**Before the first session (the deploy chat, or this one):**
1. The VM carries phase 3. Check with `git log --oneline -5` on the VM.
2. `weekly_priorities: true` in `config/modules/day_plan.yaml`, deployed by Mike. Also
   `ranking_signals: true`, so the answers are kept.
3. Which session carries the weekly review for `mike`. Check on the VM:
   ```
   cd ~/multi-model-mcp && grep -n "weekly_review" config/personas/mike/scheduler.yaml; .venv/bin/python -c "from core.persona import persona_scope; from tools.schedule import list_schedules
   with persona_scope('mike'): print(list_schedules())"
   ```
   - If a `weekly_review_on:` day rides a brief (e.g. Monday's `morning_brief`), that brief is the
     session.
   - If there is none, the next ordinary chat offers one once. Say yes and pick a day and time, then
     confirm `list_schedules` shows `every <day> at <time>`.

**Pass**, over the two sessions:
1. Each opened with the look back, at most a few minutes, and moved on to the week ahead.
2. Nothing was read out as a list. Slipping items came guarded first, each as one question.
3. The regret question was asked, and your answer kept (check 2 below).
4. Nothing felt nagging. Your word is the test.

---

## After the second session — the read-back (a Claude Code session, counts only)

Over `/monitor/file` (no task text printed):
1. **The material reached the model.** That day's `data/personas/mike/day_plan/ranking_state.json`
   has a `weekly_offered` entry stamped during the session.
2. **Answers kept.** `data/personas/mike/ranking_signals.jsonl` has a `"source": "user"` row of kind
   `regret` (and `feel`, if asked) dated that day. The words are yours, not a paraphrase. Show them
   to Mike and ask.
3. **What was said is stamped.**
   - Each back-burner item the reply named has `noticed` set in `ranking_state.json`
     `back_burner.seen`. This only applies with `back_burner: true`.
   - Each "keep, reschedule or drop?" item it named has `said` set in `weekly`.
4. **No double session:** one weekly review that week, not two.

**If it fails:**
- **Conduct** (it read a list, ran long, missed the regret question): the fix is in
  `config/modules/synthesizer_scheduled_sessions.md` § Weekly review.
- **Material** (wrong items, missing clock, wrong order): `tools/ranking_review.py`
  `weekly_material`.
- **Never offered or never recognised:** `session_kind` and `write_schedule`.

Record the outcome in the plan, § 11c.
