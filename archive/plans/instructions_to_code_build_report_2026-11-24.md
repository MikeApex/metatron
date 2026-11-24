# Instructions → code build: final report (2026-11-24)

*Driver: Opus 5.5, from `archive/handoffs/2026-11-23-instructions-to-code-build-driver-prompt.md`.
Every stage was planned, reviewed by Fable, revised, built in a worktree, diff-reviewed by Fable,
fixed and confirmed by Fable, then landed on `main` and pushed. **Nothing was deployed.** The
decision trail is in `instructions_to_code_plan_review_stop_2026-11-23.md` §§ 5–6.*

## 1. What a user will notice, by stage

Nothing below changes until Mike deploys.

**Stage 0: records** (`8cd3be3`)
- The founding principle now reads "config owns judgement and policy; code owns procedure,
  evidence and anything a rule can decide exactly" (D3).
- The rebuild notebook is closed (D2).
- CLAUDE.md trap 6 names every agent on the cached path.

**Stage 1: the goals bug** (`8ecec86`, `b9745ae`)
- Work & Vocation and Finance stop advising against goals the user has declined or parked.

**Stage 2: session shape.** This first landed inside another chat's commit, `080bba1`; residual
fixes are in `8690391` and `3afc077`.
- Scheduled briefs and check-ins stop filing false "you corrected me" events. Scheduled
  routing misses are tagged and kept out of the backlog sync and Build's three-strikes count.
- The morning brief and evening close always hear from Physical Health and get a tone line from
  Mental Wellbeing. Neither writes records on a turn the user didn't speak.
- Pattern Miner's weekly run can no longer wipe the follow-ups and held items.
- Open threads are capped at 5 without dropping live ones.
- A reply that hits the Synthesizer's round limit says what is still unchecked.
- Clarification holds run in shadow only (measured, never holding).
- The Coordinator stops re-typing the user's whole message.

**Stage 3: hard-fail domains** (`05a381d`; the medication-thread exemption is in `e1e1de9`)
- **A missed required medicine is flagged by code on every Physical Health run**, after any
  dose reported that turn is recorded, so saying you took it never draws the alarm.
- Code may add the flag; nothing clears it.
- On a scheduled session the flag can now open and escalate its own clinical thread (Mike's
  ruling).
- Money figures are summed by code from what was logged. A corrected purchase replaces the
  original instead of doubling, and two identical coffees count as two.
- A suicide disclosure always gets the crisis line for the user's country, from
  `config/modules/crisis_lines.yaml`.
- A clinical flag that arrives without its must-surface line or journal record gets them added.
- The first interview has a scripted safety test, run offline.

**Stage 4: evidence handed in** (`3afc077`, `53c9762`, `c1608f1`)
- The eight personal specialists start with their predictable reads already done by code,
  carried in the user message; the cached prefix is untouched. That saves one or two model
  turns on the slowest specialists.
- Sleep, energy, food, exercise and substance use are counted by code from the user's own logs.
  Cessation is shown only as "last logged use", never as days clean.
- Skill practice is a ledger habit with real streaks.
- Named contacts are matched exactly; nobody is merged or created by code.
- The reply reads newly saved contact details back to the user.
- Before a draft, Relationships is shown what is on file about the recipient.
- Logistics' day log is written from what actually ran.
- **The weekly Pattern Miner report saves again.** It had saved none for 12 Sundays.
- Held-back items are dated and shown as "held N days".

**Stage 5: one channel per signal** (`82c490e`)
- A research lookup carrying a known name, email, phone or address (the user's or a contact's)
  is refused before it leaves. This also covers the public-fact lookup and the new goal talk.
- Specialists' consult, lookup and profile-question requests reach the Synthesizer in one block,
  with at most one profile question a turn; clinical lines are never moved.
- Recreation's finds are filed as horizon items.
- Closed venues are listed separately.
- One preference can be added without re-typing the rest.
- Travel checks report disruptions only.
- Filler phrases ("enjoy …") are counted, never rewritten.
- Task lengths are estimated and recorded, and the user is asked only when there is no basis.
- `ESCALATION` now stops an "over and out" skip.

**Red rounds.** Round 1, opening: `8ecec86`, `b9745ae`. Round 2, closing: `8eae8c9`, plus the
final commit (Stage 5's edits and the fixes from the review of all Red diffs). One Fable review
covered every Red diff together; its eight wording findings are fixed.

## 2. Mike's deploy list

1. **Check the VM first.** Stage 2 may already be live, because it rode `080bba1`. On the VM:
   `git -C ~/multi-model-mcp log --oneline -1`.
2. Run `./deploy.sh` from the latest `main`.
3. Live checks, one per stage. Each reads traces or files on the VM; none needs a model run.
   1. **Stage 1.** After a day of use, no `read_goals` call by `work_vocation` or `finance`
      appears in `/monitor/traces`. Fail: any such call.
   2. **Stage 2.** Tomorrow's morning brief trace dispatches `physical_health` and
      `mental_wellbeing`. No `USER_CORRECTION` event is timestamped on the brief, and any
      `ROUTING_MISS` there carries `scheduled`.
   3. **Stage 3.** This is offline only, because the live runs were skipped. Before Alpha, run
      `METATRON_LIVE=1 python3 tests/run_a4_safety.py --persona sarah_chen --provider gemini
      --suite clinical`, about $4. Pass: PH-MED, PH-MED-UNLINKED and the new PH-MED-TAKEN
      scenarios report the code line.
   4. **Stage 4.** By Monday 11-30 a new file is in `data/personas/mike/insights/` dated Sunday.
      A specialist trace shows a `[PREFETCHED` block in the user message, and turn-1
      `cached_tokens` is non-zero.
   5. **Stage 5.** A research request naming a contact's full name shows `refused` in the trace,
      with nothing sent. A brief whose specialists asked for anything shows a FROM THE
      SPECIALISTS block in the Synthesizer input.
4. **For Mike only (Denied files).** Remove any "How are you feeling this morning?" opening and
   any task-length ask or estimate line from `config/personas/mike.md` and `mike/scheduler.yaml`.
   On the VM, `scripts/check_rule_overlap.py --persona mike` finds them.

## 3. Dropped or held back, and why

No finding or miss was dropped at plan review. Held back:

- **#3, the forced Diarist.** Waits for capture fidelity (D13).
- **M15.** Skipped by Mike earlier.
- **#9, quick mode, and sub-build 4f.** Not wired. D6 needs a live pass of the medication check
  first, and the live runs were skipped. Logistics' quick-mode text (C33) stays.
- **Physical Health's own medication check (X1–X4) and its sleep, energy and food flag-setting
  (C20–C22).** Left in place. The code only adds flags.
- **The Coordinator's clarification-hold text (D1–D2).** M7 ships in shadow. The go-live
  figures come from `scripts/session_shape_baseline.py` on the VM.
- **17a, employer scrubbing.** Dropped: under refuse-not-rewrite it would block research about
  the employer.
- **Held-items amendment 1.** Reversed. The Synthesizer signals "raised" by omitting an item.
- **The final-round text-similarity logic.** Reverted. Code must not guess whether text
  repeats, so a capped reply can still end on a preamble, as it could before this build.

## 4. Open items found along the way, not this build's to fix

1. **`tools/ranking_review.py`** has the same two defects that were fixed in `lookup_guard`: a
   dead organisation skip, and `referred_to_as` read as one string.
2. **`test_action_provenance` fails on `main`.** `note_expectation`, from `eb07241`, is not
   classified in `core/actions.py`.
3. **`write_log` and `read_log` default to the server's date, not the user's.** The counters work
   around this; the defaults are unchanged.
4. **M13 does not log `delete_calendar_event`.**
5. **The Coordinator still gets the full latest Pattern Miner report of any age.** The 14-day
   staleness rule applies only to the headline.

## 5. Spend

- **Build:** about 8M raw subagent tokens.
  - Planning and plan reviews: about 3.3M.
  - Builds: about 2.8M.
  - Diff reviews and confirms: about 2M.
  - The driver: extra.
- **Budget:** 1.8–2.1M weighted. The raw figure is mostly cache reads, but the real cost is still
  well over budget. The build ran three review rounds per stage, not one, because Mike asked for
  no gaps.
- **Live A4:** $0, as Mike chose to skip the runs.
- **Run (after deploy):** #2 about $0.05 per day per user. Prefetch adds about $0.02–0.04 per day
  per user. Pattern Miner's weekly run is about $0.10–0.35. Gemini prices double on 2027-01-01.
