# Instructions → code build — plan-review stop (2026-11-23)

*Driver: Opus 5.5. The driver prompt's stop conditions fired: every stage plan has a structural
review finding, and spend has passed 60% of the budget before Stage 4. Nothing beyond Stage 0
is built. This file is the single place to rule from.*

**Inputs:** stage plans `instructions_to_code_stage{2,3,4,5}_*_plan_2026-11-23.md` (Opus 5.5,
planned against HEAD `8cd3be3`). Each was reviewed adversarially by Fable 5.2. The reviews are
summarised here; full text is in the session transcript.

## 0. Where the run stands

1. **Stage 0 is done and pushed (`8cd3be3`).** D3 is amended in all three copies plus
   SESSION.md's copy, D2 closes the notebook, and trap 6 is corrected. CLAUDE.md is at 300/300.
2. **Stage 1 is ready and not applied.** It removes the `read_goals` grant from Work & Vocation
   and Finance in both routing files, and the three agent lines (`work_vocation.md:112`, `:207`,
   `finance.md:223`). It is Red, so it waits for the opening round. The filtered goals are
   already in every specialist's prompt (`_run_single_agent` → `load_goals`).
3. **Collision.** Since this run began, the other chat has uncommitted lines in **both routing
   files** (Synthesizer grants `answer_ask`, `lookup_public_fact`), in `config/agents/synthesizer.md`,
   `core/orchestrator.py`, `tools/obligations.py`, `tools/day_plan.py`, `tools/profile.py`,
   `tools/task_judge.py`, and an untracked `tools/lookup_guard.py` that its orchestrator edits
   import. Every stage touches at least one of these files.
4. **Spend.** Subagent tokens so far: planners ≈ 1.07M (249k / 253k / 269k / 303k, against
   ~100k each budgeted), Fable reviews ≈ 0.9M. That is ≈ 2.0M raw, plus driver overhead. The
   budget, 1.8–2.1M *weighted* input for the whole run, cannot be compared exactly from here,
   because cache reads are most of the raw figure and are weighted at a tenth. Planning alone
   has still used most of it. Live A4 runs: $0 so far.
5. **New silent failure found while measuring (Stage 4 Step 0).** The weekly Pattern Miner has
   written **no report for 12 straight Sundays** (09-06 → 11-22). Every run hits the 8-round
   limit before it saves. #20 fixes this, and Stage 4's review adds a precondition (§ 2, S4-L4).

## 1. Structural findings, and what I propose for each

Each finding names what a user would see, then the fix. "Rev" means the plan revision makes
that change.

### Stage 2 — session shape
1. **M7 could make ordinary turns ask a question and record nothing.** The null-ish filter is
   a whole-value match, so "Not needed" counts as a real value. The fill-rate measurement comes
   only after the closing round. **Rev:** M7 ships in *shadow* (code logs "would hold" and holds
   nothing). Its two Coordinator closing-round edits leave this run. The decision to go live is
   made from the shadow figures.
2. **A held turn still writes, one hop later.** The Synthesizer is told to re-dispatch any
   missing specialist. **Rev:** while a hold is on (live, later), code refuses the Synthesizer's
   `run_subagent` to the held writers and its write tools for that request, and refuses an M11
   `routing_miss` on a held turn.
3. **#10 was framed on a wrong picture of today.** The production Synthesizer path already stops
   at 4 rounds (`_SYNTH_MAX_ROUNDS`) and answers from what it has. **Rev:** #10 becomes "record
   `CHAIN_LIMIT_REACHED` when the existing cap ends a chain, and give the user B4's consequence
   wording". No new counter. **D-S2-3 is withdrawn.** Mental Wellbeing and Physical Health
   follow-ups are never the call that gets refused.
4. **A past disclosure could be re-raised in every morning brief and day close.** #2 forces
   Mental Wellbeing onto turns where the user has not spoken. Code strips its flag lines but not
   its narrative. **Rev:** a code-added scheduled dispatch to Mental Wellbeing carries a fixed
   directive (the user has not spoken; give tone context only from the user's own recent
   entries; raise no clinical history). An A4 fixture checks that a disclosure on file is not
   re-raised on a brief. *(The review rates this speculative; the fixture is cheap.)*
5. **The consent claim was false.** No consent gate exists in `_run_single_agent`. **Rev:** the
   plan stops claiming one, and a test covers the code-added dispatch for a second persona.

### Stage 3 — the hard-fail domains
1. **Physical Health runs outside the pipeline would lose the medication check.** That covers
   the Synthesizer's follow-ups and the weekly Physical Health review. **Rev:** the check runs
   wherever Physical Health returns (`_run_single_agent` post-return for `physical_health`),
   not only in the two pipeline twins. The closing-round deletions X1–X4 wait on a test of
   every path.
2. **Decision A's 18:00 cut-off would clear a flag that fires today.** A required morning
   medicine would flag 12 hours late, or not at all. **Rev: A = (d), leave the view alone.**
   An evening-only *unlinked* required medicine keeps today's morning alarm. Linking it gives
   exact timing (`after`), and `MEDICATION_NEEDS_LINK` already asks for the link.
3. **The transaction merge (Decision E) would inflate totals, then label them exact.** Rows
   carry no id, so a restated transaction is kept twice. **Rev: E = (b), no merge this run.** The
   totals say "from what is logged", not "authoritative". The same-day overwrite stays an open
   defect, reported to Mike with an id-based fix and not filed. *(Your call whether to file it.)*
4. **Stage 3's live gates came only at the very end of the run.** **Rev:** run the clinical and
   finance A4 suites as soon as Stage 3 is built, before anything builds on it. At the end, only
   the clinical suite re-runs. Same total, earlier.

### Stage 4 — evidence handed in
1. **The quick-mode gate cannot see quick mode.** The A4 quick suite calls the specialist
   directly, without the `mode: quick` prefix. **Rev:** the runner injects the same prefix
   through the same function as dispatch.
2. **Cessation streaks (M17) were built by neither stage.** **Rev:** 4b builds it, from
   `health.substances_logged`, worded "last logged use", never "N days clean".
3. **Reads of the user's calendar would start writing to it.** M14 + 4-7 make `read_calendar`
   re-check `[VERIFY]` events, and prefetch runs it on every Logistics dispatch. **Rev: 4-7 =
   no.** Prefetch only reads and surfaces "N events still unverified". The re-check runs only
   when Logistics itself calls the tool, and writes its note once.

### Stage 5 — one channel per signal
1. **A web search could carry the user's identifiers when a store is unreadable.** The plan
   reuses `lookup_guard._full_names`, which returns `[]` on error. **Rev:** its own reader
   refuses the research dispatch on an unreadable profile or contacts store (fail closed).
   17c = no import.
2. **D12's opening edits would contradict the plan block every turn.** They need a
   `tools/day_plan.py` string the other chat is editing. **Rev:** O10/O11 move to the closing
   round, beside the code change.
3. **Recreation's finds could be lost with nothing counting them.** The block would be its only
   channel, and a missing line or a JSON-key form is never seen. **Rev:** #11 *adds*
   `HORIZON_ITEMS` and keeps the `follow_up` route (D5's "both channels" applied to Recreation).
   The parser also accepts the JSON-key form, and a parse failure writes a quality event.
4. **`CLARIFICATION_NEEDED` would reach the Synthesizer twice, with opposite force.** **Rev:**
   M7 owns it and #19's block leaves it out.
5. *(Local, rated high.)* **Lifting request lines could take a clinical token out of the
   sign-off veto's view.** **Rev:** the veto scans the unmodified text before any lift, clinical
   tokens are never lifted, and fixtures cover token order.

## 2. Local findings — folded into the revisions (no ruling needed unless you object)

1. S2: the open-thread cap could archive the thread being discussed. Engagement re-stamps it,
   and archived entries expire.
2. S2: capture-fidelity scoring on held turns is a no-op while M7 is in shadow.
3. S2: M6's remap kept the clinical-thread write path. `merge_pattern_findings` refuses
   `clinical_threads`, and clinical writes keep their own path.
4. S3: the crisis line was appended when a flag was *re-raised*. It is now appended only for a
   flag not already in an open clinical thread.
5. S3: L4 could not observe the crisis line. The runner now asserts the configured number, on
   the streaming twin too.
6. S3: a fire-and-forget Physical Health dropped the code flag. The medication note is its own
   bundle line, independent of Physical Health's output.
7. S3: C1 widened the flag to link-broken and criticality-less rows. Now it covers `required`
   rows plus a linked row whose profile entry has no criticality. `link_broken` keeps its own
   flag.
8. S3: G = (a1). The interviewer keeps its support numbers until every entry path carries the
   code block.
9. S4: PROACTIVE_FLAGS reached the cloud Research Agent. `research_agent` is excluded.
10. S4: prefetched calendar text escaped the untrusted-read taint. Prefetch marks
    `read_untrusted`.
11. S4: on exhaustion the Pattern Miner returns a raw tool-result blob. #20 adds a tools-off
    final round to `_openai_compat_loop` for Pattern Miner, and writes the report only from a
    valid final reply.
12. S4: FOOD_NOT_LOGGED read the wrong store. It also reads the `meals` data object, and is
    evidence, not a flag.
13. S4: names matched as common words ("will", "mark"). Exact resolution requires a capitalised
    token not at sentence start, or a two-token match.
14. S4: a `[CONTEXT]` block without `held_items` erased them all. An omitted key keeps them.
15. S4: M13's code-written lists replaced earlier runs' lists. They append.
16. S5: the scrub silently rewrote public terms. It refuses with a reason, like `lookup_guard`,
    and normalises phone and postcode formats.
17. S5: `write_persona` defaulting to "add" kept corrected preferences beside their
    replacements. The default stays "replace" and "add" is explicit.
18. S5: the tone check dropped the profiled contact's own name through a duplicate record.
    Namesakes and duplicates of the same person are excluded.
19. S5: one `PROFILE_GAP` per turn by alphabet starved health gaps. Losers are queued and
    rotate.

## 3. Decisions the plans need (my recommendation in bold, adjusted for the reviews)

**Stage 2**
1. D-S2-1: on a turn with no user words, refuse USER_CORRECTION, INSTRUCTION_CHANGE_REQUEST,
   ROUTING_MISS, FEATURE_REQUEST and SELF_APPLIED. **Yes.** This closes `[DB-0902-01]` on the
   build.
2. D-S2-2: the write guard covers all five record writers for Mental Wellbeing and Physical
   Health on a no-user-word turn, and both run `deep` on the two sessions. **Yes.**
3. D-S2-4: M7. **Shadow first** (§ 1, Stage 2 item 1).

**Stage 3**
4. A, the unlinked evening medicine: **(d) leave the view.**
5. B, turns with no Physical Health dispatch: **(a) no new path**, now that the check runs on
   every Physical Health return.
6. C: **required, plus a linked row with no criticality; drop the "mentioned" carve-out**. The
   code note tells the Synthesizer to record and confirm if the user says they took it.
7. D, the `budget_structure` shape: **(a) a shape check plus one Finance line.**
8. E, the transaction merge: **(b) not this run.**
9. F, the crisis line: **(a) `config/modules/crisis_lines.yaml` by country.**
10. G: **(a1) keep the interviewer's numbers.**

**Stage 4**
11. 4-1, email prefetch: **never.**
12. 4-2, read the calendar alongside the Coordinator: **yes, read-only.**
13. 4-3, #16 built in Stage 4: **yes.**
14. 4-4, gaps as "last logged N days ago" evidence rather than flags: **evidence.**
15. 4-5, Learning & Growth owns skill habits (two Red grants): **yes.**
16. 4-6, Logistics' code-written log on scheduled turns: **actions only.**
17. 4-7, a read may clear `[VERIFY]`: **no.**
18. 4-8, Logistics excluded from quick mode: **yes.**

**Stage 5**
19. 11: **keep both channels for Recreation**, plus a quality event on a parse failure.
20. 16: what Relationships is handed (gift ideas, open tasks, standing facts, literal-name memory
    hits): **as the plan says.**
21. 17a: add an `employer` profile field and scrub it: **yes.**
22. 17b: don't strip a lone contact first name: **yes.**
23. 17c: **own fail-closed reader.**
24. 19: no live A4 for the requests block: **yes**, with token-order fixtures.
25. 25: closed venues in a separate `closed_then` list: **yes.**

## 4. How to proceed — the ruling this stop needs

- **(a) Full run as written.** Revise all four plans, with one short Fable confirm on Stage 3's
  revision, then the opening Red round and Stages 1→5. **Build:** roughly 2–3M more raw tokens
  (revisions ≈ 0.4M; builds ≈ 1.2M at the planners' measured rate, not the budget's; diff
  reviews ≈ 0.6M). **Live:** 3–4 A4 runs, about $12–16. Roughly double the stated budget.
- **(b) Stages 1–3 in this run; 4–5 in a second driver run. (Recommended.)** The items that are
  silent and hard-fail are in 1–3: the goals bug, the Pattern Miner data loss (M6), the
  scheduled-turn noise, #8 medication, Finance totals, M8/M9, and D8, the interview safety test
  that must precede Iva's first interview. Revise plans 2 and 3 now. Fold the Stage 4/5 review
  findings into those plans as a recorded revision list (§§ 1–2 above), for a second driver
  prompt. **This run's two Red rounds then cover Stages 1–3 only, and the second run gets its
  own two.** That departs from "two rounds for the whole build", which is why it is put to you.
  **Build:** ≈ 0.9–1.1M more. **Live:** 2 A4 runs, about $7–8.
- **(c) Stop here.** Commit the plans and this file, and write the second-run prompt.

**The collision** applies to (a) and (b) alike. Options: **(i) wait for the other chat to commit
(recommended)**, since its files are the ones every stage edits; (ii) stage only my hunks with
`git apply --cached` and an export-and-import check of HEAD (rule 4's method). That is allowed
when regions are disjoint, but the driver says stop and ask, and `lookup_guard.py`'s import
makes a half-commit of `core/orchestrator.py` dangerous.

## 5. Mike's rulings (2026-11-23, in chat)

- **Scope: the whole run, Stages 1–5, at once.** Mike asked: "Is there any real reason that
  doing it in phases will prevent an error that otherwise can't be fixed after the fact? If not
  do it all at once." There is none. Nothing deploys before the run ends; Red edits revert; no
  stage writes real user data; one run keeps "two Red rounds for the whole build". **Every
  revised plan gets a narrow Fable re-check before it is built.** D8 is built first (it must
  precede the second user's first interview); #9 is still wired last.
- **Collision: wait for the other chat.** It was the ranking Part B phase 2 build. It committed
  (`e134948`, `129f3fb`, close-out `8ef2edf`), and the stage files are clean. The plans are
  revised against the new HEAD.
- **The eight judgement calls:**
  1. A, the unlinked evening medicine: **keep the alarm** (= (d), leave the view).
  2. C2, drop the "mentioned" carve-out: **as rec.**
  3. D4, Mental Wellbeing on scheduled sessions with a fixed tone-only directive: **as rec.**
  4. D-S2-1: **option 3.** Refuse USER_CORRECTION and INSTRUCTION_CHANGE_REQUEST on a turn with
     no user words. Keep ROUTING_MISS there, but tag it `scheduled`, and keep tagged events out
     of the backlog sync and the Build three-strikes count. (FEATURE_REQUEST and SELF_APPLIED:
     as the plan's recommendation, refused.)
  5. M7, shadow first: **as rec.**
  6. Finance's same-day transaction loss: **fix it now.** The review showed the multiset merge
     is wrong, so the fix must not double a restated transaction (e.g. code-assigned ids).
  7. Crisis lines in `config/modules/crisis_lines.yaml` by country: **as rec.**
  8. Learning & Growth owns skill-practice habits (two Red grants): **as rec.**
- **The other 17 decisions in § 3: as recommended**, unless Mike says otherwise. The opening
  Red round is still shown to him before it is applied.

## 6. Mike's rulings, round 2 (2026-11-23, 22:xx)
- **Red round 1 approved in full** (`instructions_to_code_red_round_1_opening_2026-11-23.md`):
  27 edits applied now; 9 wait for the other chat's commit (routing files, `synthesizer.md`,
  `synthesizer_scheduled_sessions.md`).
- **Live A4 runs: "Skip the runs for now."** Fixtures are built and run offline. Two consequences
  follow from gates that needed a live pass:
  1. **#9 quick mode (4f) is not wired this run.** D6 requires a live pass of the medication check
     first.
  2. **Closing-round deletions of clinical instruction text leave this run.** These are Stage 3
     X1–X4 and Stage 4's C20–C22 for the clinical and sleep flags. Instruction and code both stay,
     and the code only adds flags.
