Model: Opus 5.5, high effort — a code archive that must never silently close a real obligation, a new scheduled-session conduct, and two Red rounds; Fable reviews the diff before commit.

# Ranking Part B, phase 3 — the back burner, the weekly conversation, and signals

You are building phase 3 of `archive/plans/ranking_values_plan_2026-11-23.md`. **§ 11 governs the
values, § 10 the design wherever it differs from §§ 4–8, and §§ 11a and 11b record what phases 1
and 2 built, deviated on and left open.** The archive ships in **dry-run** for its first week (§ 5
phase 3): it lists what it would archive and closes nothing. Each new behaviour ships behind its
own flag, off. No flag is flipped in this session.

**Precondition — check it, don't assume it.** Phase 2 is `e134948`: committed, not deployed when
this prompt was written. Read § 11b and `SESSION.md` for:
- whether it is deployed;
- what the protected-time, behind and lookup walkthroughs found
  (`archive/handoffs/2026-11-23-ranking-phase-2-*-walkthrough.md`);
- whether `ranking_v2` has flipped.

Phase 3 does not wait on any of these. Its archive and signals read the ledger and the phase 2
trace whichever flags are on. If a walkthrough failed and Mike named values to change, change
those first.

## Read first, in order

1. `SESSION.md`, then `ROADMAP.md` (the mandatory pre-edit context check).
2. The plan:
   - § 2: B26–B32;
   - §§ 4.11, 4.12, 4.13;
   - § 10: R8, the signals paragraph;
   - § 11: row 13 (the weekly list) and row 15 (back burner: **21 days**, mentioned once in the
     weekly conversation the week before);
   - §§ 11a and 11b in full.
3. `archive/plans/ranking_research_2026-11-23_claude-chat.md` § 8 (and § 7 for the weekly cadence).
   Cite each new value beside it in `ranking.yaml`.
4. The code as it is now:
   - `tools/ranking.py`: `raise_candidates`, `to_weekly`, `keep_trace`, `behind_state`;
   - `tools/day_plan.py`: `_keep_ranking`, `_phase2_trace`, `refresh_tick`, the ledger sweep on a
     day change;
   - `tools/obligations.py`: `open_task`'s duplicate match, `_TERMINAL`, `moot`;
   - `tools/schedule.py` `write_schedule` (the 6-job cap);
   - `config/modules/synthesizer_scheduled_sessions.md`;
   - `config/agents/synthesizer.md` § Tools available;
   - both routing files' `synthesizer` grants;
   - `scripts/ranking_report.py`.

**Other chats commit to `synthesizer.md`, `day_plan.py` and `obligations.py`.** Re-read each file
before editing it, and **`git diff` every file before staging it**; read
`git diff --cached --stat` on its own before committing.

## Build — phase 3 scope

1. **The back burner** (§ 4.11, row 15), behind a `back_burner` flag in `day_plan.yaml`, in
   **dry-run** first (`back_burner_dry_run: true`).
   - **The rule (daily, code):** an open task whose cost of delay stays below `back_burner_cod`
     for 21 days, with no mention in that time, is archived as `moot`, reason `back_burner`. The row
     and its history stay (archive-on-merge).
   - **Guards:** never before a dated step's or cliff's date. Never silently for a task with a
     person (`bears: close|others`, or a contact named), or an obligation (`legal`/`financial` ≥
     major, or health). Those become one line in the weekly conversation instead. Never a plan
     step, a prep, a medication habit, or anything on `ranking_state.weekly`.
   - **Notice:** each task is mentioned once in the weekly conversation the week before it is
     archived.
   - **Revival:** `open_task` matching an archived `back_burner` row reopens it rather than opening
     a duplicate.
   - Dry-run writes the would-archive list to the trace and to `ranking_report.py --back-burner`.
   - "No mention" needs a definition that holds. Find what already records a mention
     (`note_raised`, history events) and say in § 11c what you used.
2. **The weekly priorities conversation** (§ 4.12).
   - **Conduct**, its one home, in `config/modules/synthesizer_scheduled_sessions.md`:
     1. what Metatron moved and why, at most three lines;
     2. any clash held, as one question with a recommendation;
     3. what is slipping or about to be archived, guarded items first, **plus
        `ranking_state.weekly`'s "keep, reschedule or drop?" items** (§ 11 row 13);
     4. one relationship or upkeep clock;
     5. the regret question;
     6. at most one woven check on how things feel.
   - It never reads out a list.
   - Code assembles the session's material into its package. The model chooses nothing to fetch.
   - **Red:** one `synthesizer.md` sentence — offer the weekly conversation once, at a time the
     user picks, created with `write_schedule`, mindful of the 6-job cap.
3. **Signals** (§ 4.13), to `data/personas/{p}/ranking_signals.jsonl`, append-only, kept forever.
   - **Ledger-derived rows**, written by code in the daily tick: completion, momentum, missed
     obligations, intrusions (from `ranking_state.intrusions` and `trace.intrusions`), and questions
     asked by this plan's paths (`ranking_state.prompts`).
   - **Spoken answers** go through a new tool, `record_signal(kind, text)`: regret, how things
     feel, unprompted remarks about overload, nagging or satisfaction.
   - Overrides are recorded, not scored (B30).
   - **Red:** grant `record_signal` to the Synthesizer in `routing_cloud.yaml` and `routing.yaml`,
     classify it in `core/actions.py`, and add its conduct to the weekly module and one
     `synthesizer.md` sentence.
   - The monthly review is a walkthrough (§ 7.2): `ranking_report.py --signals --persona P
     [--month]` prints the month.
   - Goal network phase 3's satisfaction rows are read here, never duplicated.
4. **Two items § 11b left open.** Close either one only on evidence:
   1. *A model reshuffle can undo the behind lead* (Fable #4). If the behind walkthrough found
      `behind.led` false after the flip, make the lead survive `_build_from`.
   2. *A record the judge wrote under the old "keen gardener … major" wording may count a
      passion twice* (Fable #12). Measure it on the VM's records first.
5. **Tests** extend `tests/test_ranking_v2.py`:
   - plan § 6 test 12: a 21-day silent trivia task archives; a person-task, a dated cliff and a
     `legal` major never do; a re-mention reopens;
   - the dry-run closes nothing;
   - the weekly list reaches the weekly package;
   - signals rows are appended and never rewritten;
   - `record_signal` is refused outside a user turn.

   Keep `tests/test_task_ranking.py` 21/21 with every new flag off, and the phase 2 tests green.

**Not in this phase:** goal network phase 3 (L vetting, re-vetting, the satisfaction mismatch). It
shares the signals file and builds neither.

## Close

1. Spawn a Fable diff review and reconcile every finding in a new plan section, § 11c.
2. Commit with a message that leads with what a user would notice. **Do not deploy.**
3. Prepare:
   - the dry-run walkthrough: a week's would-archive list, reviewed with Mike before archiving
     goes live;
   - the weekly conversation's live check: two sessions;
   - the first monthly signals review.

   Each goes in `archive/handoffs/`, model line first, as in phases 1 and 2.
4. `/archive`.

## Rules that bind this chat

- **Red edits are made in this session, never delegated:** `synthesizer.md` and both routing files.
- Nothing leaves this machine: no Artifact, WebFetch or WebSearch.
- All personal data is sensitive-tier; § 4.16 is the privacy basis. The signals file holds the
  user's own words. It is per persona and deleted with it.
- `config/personas/**` is VM-owned; deploying is Mike's.
- Don't file backlog items Mike didn't ask for. Number every list, and never write a backlog id bare.
- **Budget** (plan § 8, phase 3): ~$30–60 build, plus ~$5–10 for `record_signal` and its Red
  round. Run cost: code only, zero model tokens, apart from the weekly session itself: one
  scheduled Synthesizer turn a week, on the existing session's price. Name its figure in § 11c.
