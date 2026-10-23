# Task ledger — post-deploy verification and (M) walkthrough (launch prompt)

Model: Opus 5.5. Verification against live traces, with small fixes possible in the code it
reads (`tools/obligations.py` and the consult points) — build work, which `docs/WORKFLOW.md`
puts in Opus; Mike executes the (M) steps live with guidance.

**Budget:** ~60–90 Mike-minutes; ~0.5–1.5M Opus tokens on the subscription, mostly cache reads.
Run-cost delta of anything here: zero (no new model calls; the nightly sweep is token-free).
Splittable — items 1–3 first; the time-gated checks in item 5 leave with dates, not on a list.

**Why this session exists:** the task ledger was built, reviewed by Fable 5.1 over three rounds
and committed on 2026-10-23 (`27c570f`) — 57 new checks green, qa_sweep 12/12 — but it has never
met a real model. Everything below is what proves it does what it was built for, plus the steps
only Mike can take.

---

/metatron-code Post-deploy session for the task ledger, Mike present. Read first, in this order:
`archive/plans/task_ledger_plan_2026-10-23.md` (§ 1 the evidence, § 3–§ 6 the design, § 13 the
review), then `tools/obligations.py`'s module docstring. For each item below: present the steps,
guide Mike through any he runs, verify each result from a trace or a file before moving on, and
report pass/fail with the evidence. Read the VM only through the existing read paths (the
`/monitor/*` endpoints `scripts/sync_dev_backlog.py` uses); never write to the VM — persona data
is Mike's, and `data/personas/**` is Denied here.

1. **Confirm the deploy landed.** VM HEAD contains `27c570f`. On the VM:
   `data/personas/mike/tasks.yaml` exists with the 43 imported records (ids `ob_…` unchanged) and
   `obligations.yaml` is still present and unmodified since the import. The housekeeping Mike sent
   on 10-23 (Bupa twin and Schwab RSVP closed, Apex re-dated to 2026-11-15, plant and
   `check_inbox_recurring` jobs deleted) shows in it. `daily_task_sweep` is in the scheduler's job
   list. Any deviation is a stop-and-diagnose, not a note.

2. **APK rebuild and sideload — (M), guided.** The app bundles `static/index.html`, so the
   **✓ Today** button and the suggestion bar exist only in a new build. Steps:
   `docs/INFRASTRUCTURE.md` § APK (build, `scripts/check_apk_sync.sh`, serve, install). Pass: the
   header shows `✓ Today (n)` and tapping it lists today's tasks.

3. **The setup prompt — Mike pastes this into Metatron** (he fills in the watering date and
   confirms the medication list and times when asked):

   ```
   Set up my recurring tasks so they're tracked from now on:
   1. Gym three times a week, preferably Monday, Wednesday and Friday — a missed day can be made up later in the week.
   2. Stretching every day.
   3. Water the plants every 3 days; I last watered them on [EDIT: date]. Water sooner in hot weather.
   4. My medications as daily tasks, one per medication at the times I take them — confirm the list and times with me first.
   5. Move everything in your recurring-obligation inventory into tasks, monthly bills included, and tell me what you moved.
   Then show me today's list.
   ```

   Verify from the trace: `open_task` calls with the right kinds (`habit` every=week times=3
   on_days mon/wed/fri; `habit` every=day; `interval` interval_days=3 with `last_done`; one habit
   per medication); no `write_schedule` call; nothing refused as a duplicate that should not be.

4. **Live checks — each with its pass/fail signal, read from the trace's context sections and
   tool calls:**
   a. **Spoken completion.** Mike says "I watered the plants." Pass: the Synthesizer input carries
      a `TASK NOTE` naming the plants task; `update_task(…, "done")` is called with his words; the
      next turn's Tasks block lists it under *Closed recently*, not *Now*.
   b. **Tap completion.** Mike taps **Done** on Stretching in ✓ Today. Pass: the row disappears;
      the next turn's block shows "Stretching — logged today"; the task's evidence reads
      "marked in the app".
   c. **Raise once.** After a scheduled session mentions an item, the next companion check-in's
      context shows "N more already raised today" and the reply does not raise it. Pass both.
   d. **Ambiguous completion asks.** Mike says something that matches two tasks loosely. Pass: the
      reply asks which, and nothing is closed.
   e. **Stale copy contradicted.** Find a day-log line or thread that names a closed task; pass if
      the rendered context carries `[looks like task … done …]` beside it.

5. **Time-gated — each leaves today with a date in `DEV_BACKLOG.md`, not as a hope:**
   a. **The nightly sweep ran.** First run 00:15 after deploy. Pass: `task_history.jsonl` has rows
      for yesterday's daily habits (done or missed), and a repeat run appends nothing. Check the
      morning after deploy.
   b. **Interval comes back.** The plants are due again exactly 3 days after the watering in 4a,
      not before. Check that date.
   c. **A correspondence suggestion fires.** Needs a real email answering an open `waiting` or
      `deadline` task (the S.A.R. e-file confirmation is the likeliest). Pass: the suggestion bar
      shows it; **Mark done** closes it with evidence "correspondence evidence, approved in the
      app"; nothing from the email's subject appears in any context section. Gate: two weeks, then
      re-scope if nothing has arrived.
   d. **A week of adherence.** After seven days, `python3 -m tools.obligations mike --report` on
      the VM shows gym as completions/target with the first partial week excluded.

6. **Two decisions owed to Mike — put each with its recommendation, then act on the answer:**
   a. **Where the medication safety flag lives.** Mike: build medication tasks universally, flag
      before production. Recorded today only in the plan (§ 9). Recommendation: add one line to the
      before-Alpha A4 re-run note in `ROADMAP.md` § 0 clause 8 — that is already the clock for every
      clinical check, so the flag cannot lapse unseen. The clinical path itself is unchanged.
   b. **The remaining inbox job.** `check_inbox_6h` (Logistics, every 6h) was kept on 10-23; its
      twin was deleted. `logistics.md` already says standing triage is the intake sweep's job, not
      Logistics', so this job may now be redundant too (~67 runs a month at ~96k tokens each on
      the bulk tier). Recommendation: watch one week of task creation from mail; if every task it
      files also arrives through the intake queue, delete it.

7. **Known limits — confirm none is biting, file only what Mike would notice:** the hint can
   over-fire when another party is the subject ("Chase called about the card") — it asks, never
   closes; recurring calendar series are annotated, never ✓-marked; the plant-watering weather
   condition is a note, not code; Relationships follow-ups stay outside the ledger.

8. **Housekeeping from 10-23:** the scratch copies of VM data pulled for the audit (~78 MB of
   conversations and traces) are in the 10-23 session's scratchpad under
   `/private/tmp/claude-501/-Users-md-homefolder-Desktop-multi-model-mcp/88f4f145-0c2b-4927-96bd-7a5ec579afa0/scratchpad/`
   (`pull/`, `dryrun/`). Ask Mike to delete them, or delete them on his say-so — `rm -rf` is
   Denied in this project's settings, so the deletion is his command or his explicit approval.

Close with `/archive`. Anything that did not pass is a backlog item with the evidence that failed.
