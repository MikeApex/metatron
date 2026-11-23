# Instructions → code build — Red round 1 (opening), 2026-11-23

*Every Red edit that depends on no new code, from all five stages, for Mike's approval. The exact
current and replacement text for each edit is in the stage plan section named. Each plan was
re-checked by Fable after revision, and every anchor was verified at HEAD `8ef2edf`.*

**Total: 36 Red edits in 11 files, plus 1 Amber.** Of these, **27 can be applied now**. **9 wait
for the other chat to commit**, because their files carry its uncommitted lines: both routing
files, `config/agents/synthesizer.md` and `config/modules/synthesizer_scheduled_sessions.md`.

## Stage 1 — the goals bug (driver; § 0 of the stop file)
1. **Work & Vocation and Finance stop reading the raw goals file**, which brought back declined
   and parked goals. Both already get the filtered goals in their prompt.
   - Remove `read_goals` from `work_vocation` and `finance` `allowed_tools` in
     `config/modules/routing.yaml` and `routing_cloud.yaml`, and add a dated comment. *(4 edits —
     wait: routing files.)*
   - `work_vocation.md:112`: drop "Also call `read_goals` to check current professional goals
     for alignment assessment", and say the goals are in context.
   - `work_vocation.md:207` and `finance.md:223`: delete the `read_goals` tool bullet. *(3
     edits — now.)*

## Stage 2 — session shape (`…stage2_session_shape_plan…` § 2)
2. **The Coordinator stops re-typing the user's whole message every turn** (M10).
   - O1, `coordinator.md:113–114`: delete `ORIGINAL_MESSAGE`. *(now)*
   - O2, `coordinator.md:42`: two in-line references to it removed. *(now)*
   - O3, `synthesizer.md:272–274`: the sanity check points at the user's own message as code
     labels it. On a scheduled session there is none. *(wait: synthesizer.md)*

## Stage 3 — hard-fail domains (`…stage3_hard_fail_plan…` § 2)
3. **An anxiety-disorder concern also gets its journal record**, matching the file's own rule at
   `:14`. O1, `mental_wellbeing.md:175`. *(now)*
4. **Finance writes budgets in a shape code can total against** (ruling D). O2,
   `finance.md:228`. *(now)*

## Stage 4 — evidence handed in (`…stage4_evidence_plan…` § 2)
5. **Learning & Growth can keep skill practice as a ledger habit** (ruling 4-5): grant
   `open_task`, `update_task` and `list_tasks`. O1/O2, both routing files. *(wait: routing
   files)*
6. **The Coordinator stops claiming it holds the Prime Directive and Mission** (#6 honesty).
   O3, `coordinator.md:24–26`. *(now)*
7. **Skill practice routes to Learning & Growth, not Logistics.** O4, `coordinator.md:239`.
   *(now)*
8. **Learning & Growth's streaks move onto the ledger habit.** No more "last_practiced:
   today" in logs. O5–O9, `learning_growth.md` ×5: the habit instruction, a typo, the log
   example, the tracking bullets, and the three tools named. *(now)*

## Stage 5 — one channel per signal (`…stage5_one_channel_plan…` § 2)
9. **Logistics' horizon instructions stop saying something false** (#7; both channels stay,
   D5). O1/O1b, `logistics.md` ×2. *(now)*
10. **Recreation's two output instructions no longer contradict each other** (§ 2b.5), and it
    emits `HORIZON_ITEMS` while keeping `follow_up` (#11, ruling 11). O2/O3,
    `recreation_hobbies.md` ×2. *(now)*
11. **Finance stops narrating a routing rule that is false** (§ 2b.6), and stops a redundant
    pre-check (#23). O4/O5, `finance.md` ×2. *(now)*
12. **Research and the Synthesizer stop referring to an `intensive` tier that doesn't exist.**
    It is kept as "planned, not built" (#24). O6/O7, `research_agent.md` ×2. *(now)* O8,
    `synthesizer.md:123`. *(wait: synthesizer.md)*
13. **The morning brief has one opening rule** (§ 2b.1). O9,
    `synthesizer_scheduled_sessions.md:31`, Amber. *(wait)*
14. **New goals: specialists return questions, not a plan, and the Synthesizer chooses** (§ 2b.4).
    O12, one identical paragraph in six agent files. *(now)*

## After applying
`python3 scripts/check_agent_tools.py` exits 0, and `python3 scripts/check_claude_md_claims.py`
holds. The routing grant parity check passes. One commit, staged by explicit file list after
`git diff` on each file.

## Mike's to make (Denied tier), once the closing round is live on the VM
- Remove any "How are you feeling this morning?" opening and any task-length ask/estimate line
  from `config/personas/mike.md` and `config/personas/mike/scheduler.yaml`.
  `scripts/check_rule_overlap.py --persona mike` on the VM finds them.
