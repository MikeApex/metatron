### 2026-11-25 (the goals walkthrough's misses fixed and deployed — goals on hold come back, false hold claims replaced, the talk needs the user's own figure; three modules that had not loaded on the VM since 11-11 load again; part A Stage 1 on)

**What changed.** One build from `archive/handoffs/2026-11-25-goal-walkthrough-misses-fix-build-prompt.md`
(Opus 5.5; Fable 5.2 review + verify), `26042b1`, **deployed by Mike 11-25** (VM HEAD read as
`26042b1`; server and both schedulers active). Full record: `goal_task_network_plan_2026-11-18.md`
§ 19. Parked goals are one line under "On hold" in every goals view and come back once on their
date; `starts_on` keeps a goal taken on but unplanned, uncounted, unchecked and unalerted until its
day; a goal-hold or goal-completion claim the goal's state contradicts is replaced by a fixed line
(new `tools/goal_claims.py`, after the pending receipt in both Synth twins and in talk turns); in a
talk the weekly time must be the user's own and the rate said before an `active` verdict; ids out of
replies; a practice (`parent_goal`) moves with its goal. `projected_finish` and `revet` ON (part A
Stage 1, Mike: "as rec"). Read on the VM after deploy: Bulgarian, bricklaying and `d1` under "On hold".

**Mike's rulings:** 1 a parked goal shows and is asked once; 2 `starts_on`; 3 his words decide —
"on hold until X" = `starts_on`, "park/revisit" = parked (stretching is its own daily goal, `w5`
becomes "Strength training"); 4 sentence-level replacement — and the user's latest word always wins;
5 the figure is code-checked against his turns, 5b parking needs no weekly time; 6 a sentence plus a
logged count; 7 fix the three load failures now. **Rejected:** a separate `/fix` deploy for #7
(a second deploy the same day); upgrading the VM's Python inside this build (Mike asked; the cleaner
fix for Mac-3.14 vs VM-3.11 drift, but an infra job with its own rollback — offered as a walkthrough,
not filed); auto-hiding a held goal's tasks (Mike's 037 trainer question was right to ask; a habit
cannot be hidden without missed days); the turn-diff design for claims (below).

**Believed true earlier that turned out wrong.**
1. **The claim check's first design was wrong, and Fable's review blocked it.** "Did this turn change
   the goal?" replaced true sentences in every domain ("I've paused your morning routine"), called a
   true recap the next turn false, and garbled a goal's own "it's back" line. Rebuilt on the goal's
   *state*; the verify pass then caught an over-correction (advice, third-party news and "I haven't…"
   replaced) — fixed by requiring Metatron's own claim.
2. **Seq 015 was not a goal fault:** a Vertex 429 after a 75 s timeout, one retry allowed.
3. **Its diagnosis found three modules dead on the VM since `968a8a0` (11-11):** calendar reconcile,
   the travel check, the calendar audit — one f-string line each that 3.12 accepts and 3.11 refuses.
   `ast.parse(feature_version=(3, 11))` does not catch it on 3.14; a token scan in the suite does.
4. The prompt said Synth had a one-question rule; it had none.
5. Seq 032's hold *was* written — to the fitness notes, not the goals (the stale note is for Mike to
   delete in the app).

**Tests.** New suite 37/37; part A 42, part B 31 (fixtures now give the user's figure and the rate),
phases 1–2 38/36, ranking 58/21, ledger 15 (schema pin moved); 48 related suites, only the two known
clean-HEAD failures; QA sweep 12/12.

**Not done / next (M, tomorrow):** `archive/handoffs/2026-11-26-goal-walkthrough-fixes-live-tests-prompt.md`
— exercise hold re-said, `w5` renamed, stretching goal, "Perform morning stretches" (linked to `d1`
by mistake) moved, the stale fitness note deleted; Bulgarian completed (`active`, `starts_on`
2027-01-15); the step 4 read; Stage 1's reads. Open: fragment 04's miss 10 (Synth lost its place
after Bulgarian; Healthier Diet never taken) was not in this build.

