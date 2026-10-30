Model: Opus 5.5 — spec and plan in Opus, adversarial review in Fable 5.1 (docs/WORKFLOW.md, Mike 2026-09-24). This is planner design where the last draft was wrong in four places, so the review round is not optional.

# Stage 2 — the planner schedules the prep: spec it out, review it, then build on Mike's go

Run `/metatron-code` first.

## What Mike wants

Mike, 2026-10-30: *"Flagging the red book as something to prepare in the evening for a morning
event is important, and planner (working with code/Logistics/whomever) needs to anticipate when
prerequisites need to be done."* Then: fold it into the build, at the end. Then: take it into a
new chat and **spec it out a little further** before building.

What the user should see: the evening before Benny's 09:30 nursery settling-in session, the day
plan already holds *"Gather paperwork, Red Book, birth certificate, passport, and proof of
address"* at a time that fits. The Synthesizer nudges it when it's due ("Time to pack Benny's Red
Book for tomorrow"), checks once whether it happened, and the Today panel shows it with Done /
Not yet / Skipped. Nobody had to ask for it.

## Where things stand

- **Stage 1 is committed (`547c446`), not deployed.** The Synthesizer says now / one next / free
  time / Important (≤ 2) instead of the whole day. `read_day_plan` gives the whole day on request.
  `tools/horizon.py prep_items()` surfaces findings with a `precursor` due by the day as Important
  at the evening close and morning brief. **So the Red Book is already *said*. Stage 2 makes it
  *scheduled*.**
- **Read first:** `archive/plans/synth_now_next_plan_2026-10-30.md`. § 2 has Mike's rulings
  S1–S6, § 7 the follow-up, § 9 the stage 2 draft, and **§ 10 Fable's review of that draft:
  three structural and six local findings, none fixed yet.** § 9 is the starting point, not the
  answer.
- **Data, measured on mike's VM ledger 2026-10-30:** Logistics already files prerequisites —
  `record_horizon_item` takes `precursor` and `precursor_by`. The 10-29 nursery finding carries
  *"gather paperwork, Red Book…"*, `precursor_by` 2026-10-29. The same event has **three
  near-identical findings**, worded differently. `detail` is on every finding, so it is no
  signal. Some precursors read `"none"`. Read the ledger through
  `data/personas/mike/horizon/ledger.json` on the VM (the `/metatron-troubleshoot` SSH pattern),
  read-only.

## The review's findings the spec must answer (plan § 10)

1. **A1:** a finding filed the morning of a 09:30 session must not put the prep tonight. It needs a same-day branch, and the event's time from the calendar.
2. **A2:** the scheduler and the server must not both write the horizon ledger. It has only an in-process lock. Convert at filing time in the server (`record()`), or add a cross-process lock.
3. **A3:** turning the flag off must actually restore stage 1. Gate the `prep_items` skip on the flag too, and decide what happens to prep tasks already opened.
4. **A4/A7:** dedup on event plus precursor, not `_ledger_hit` (which never reads the precursor). Remember `source_id` disables the ledger's near-duplicate guard. Stamp every sibling finding.
5. **A5:** each new task triggers a reshuffle, which is a day_planner model call sharing the user's 12/day cap. Price it, or place by code only.
6. **A6:** place the prep from the day shape, not the evening-close job's clock. A light, screen-free prep is allowed in family time; a screen task (booking a table) is not.
7. **A8:** a refused open (a recently closed twin) must not retry every 5 minutes.
8. **A9:** a moved event must move its open prep task.

## Interview Mike before writing the spec (his rule: interview, then fix together)

Ask a few short questions, each with options, a trade-off and a recommendation:
- **Which prerequisites become tasks.** All findings with a precursor, or only ones tied to an event with a time? Is the near window (due ≤ 2 days out) right?
- **When the prep goes.** The evening before by default? Same day if the event is after midday? Who decides how long prep takes?
- **Should Logistics also infer prerequisites the finding doesn't carry?** That is a `config/agents/logistics.md` change, Red tier. Measured: Logistics already fills `precursor` on most findings.
- **What "off" means** for prep tasks already open: leave them, or close them with a reason.

## Deliverables, in order — stop for Mike between each

1. The interview, then a **revised spec** written as § 11 of the plan file. Use targeted edits, not a rewrite. Include a budget (build / run / ancillary / unseen) and a model line.
2. **Fable adversarial review** (`adversarial-reviewer`, `model: fable`) of § 11 against the real code. Reconcile every finding in the file.
3. Build only on Mike's go. Red edits (`logistics.md`, routing files) need his approval at the prompt, and Red work is not delegated. Run the stage 1 suites plus new tests, then `./scripts/qa_sweep.sh`. A Fable diff review comes before the commit.
4. `/archive`. Deploying is Mike's (`./deploy.sh` is Denied).

## Constraints that bind this work

- `git diff` every file before staging. Other sessions' uncommitted work sits in this tree (android/, `.claude/agents/build-inquiry.md`, `.gitignore`, `archive/plans/inquiry_rewrite_2026-09-26.md`); don't stage it.
- A test that touches a real seam stubs every live meter (CalDAV, Routes, model calls). A live gate run dirties tracked `data/personas/danny_park/…` fixtures; `git checkout HEAD --` them.
- Don't file backlog items Mike didn't ask for.
- Stage 1's live check is owed by Mike after deploy. If it has happened, read the result first: the 07:31 brief, an "I'm home" reply and the 20:01 close, with no rundowns. If stage 1 failed live, that comes before stage 2.
