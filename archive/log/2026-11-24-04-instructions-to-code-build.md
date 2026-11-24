### 2026-11-24, fourth (the agent-instructions-to-code build — all five stages built, reviewed and landed; two Red rounds; deployed by Mike) — `8cd3be3` → `36c5972` — **committed and pushed; DEPLOYED by Mike 11-24** (the VM was at `28c369c`, so all five stages went live together; Stage 2 had not ridden an earlier deploy)

**Incoming handoff:** `archive/handoffs/2026-11-23-instructions-to-code-build-driver-prompt.md`
(Opus, high): one driver chat, two Red rounds, the review's misses included (18 of 19).
Unblocked by "Medication taken today" (`95c3ce7`). Final report:
`archive/plans/instructions_to_code_build_report_2026-11-24.md`, which also holds Mike's deploy
list and the per-stage live checks.

**What landed.**
- **Stage 0:** D3 in all copies, the notebook closed, trap 6 (`8cd3be3`).
- **Stage 1:** the `read_goals` grant removed (`8ecec86`, `b9745ae`).
- **Stage 2:** session shape. **It first landed inside another window's commit, `080bba1`:** my
  `cherry-pick --no-commit` left 20 files staged in the shared index, and the WhatsApp close-out
  swept them in. Mike left that commit as it is.
- **Stage 3:** the medication check at Physical Health's return, Finance figures and transaction
  ids, crisis lines by country, and the interview safety test (`05a381d`).
- **Stage 4:** prefetch, counters, contact resolution, the Logistics log, and the Pattern Miner
  report with dated held items (`3afc077`, `53c9762`, `c1608f1`).
- **Stage 5:** the research identifier check, the specialists' request block, and the D12 code
  half (`82c490e`).
- **Red round 1:** `8ecec86`, `b9745ae`. **Red round 2:** `8eae8c9`, `36c5972`.

**Mike's rulings this session.**
- **Whole run, not phases.** No error was unfixable after the fact, because nothing deploys
  mid-run. Every revised plan was re-reviewed before it was built.
- **Wait for other chats to commit**, three times over.
- D-S2-1 is option 3: scheduled ROUTING_MISS events are tagged, not refused.
- Keep the unlinked-medicine alarm. Fix the same-day transaction loss.
- **No live A4 runs.** So #9/4f is not wired, and Physical Health's own medication and sleep
  text stays.
- Medication-missed may open its clinical thread on a scheduled turn.
- Both Red rounds approved in full.

**Rejected, with the reason.**
- **Phasing the build:** it would have needed four Red rounds and bought no safety.
- **A separate research identifier reader:** the committed `lookup_guard` already fails closed.
- **Scrubbing the employer:** refuse-not-rewrite would block research about the employer.
- **The final-round text-similarity logic:** reverted after three rounds of defects. Code must
  not guess whether text repeats.

**Believed true earlier, and wrong.**
1. **My held-items amendment 1** ("merge; leave only via `held_dropped`") was wrong. The
   Synthesizer signals "raised" by omitting an item. The fix was to reverse it, plus two
   synthesizer lines that still said "all keys present" and "no more than 5".
2. **The plan budgets ran about 3–4× low.** Each planner and builder used 250–500k tokens. The
   whole run was about 8M raw tokens against a 1.8–2.1M weighted budget.
3. **The weekly Pattern Miner had written no report since 09-06.** Every run hit the round limit
   first. This was found while measuring for Stage 4.
4. **The live public-fact guard (`129f3fb`) had a dead organisation skip and read aliases as one
   string.** Fixed in Stage 5. `tools/ranking_review.py` carries the same two defects and is not
   fixed.

**Lesson recorded:** land worktree builds by rebasing inside the worktree and fast-forwarding
`main`. Never stage through the shared index.

**Owed, all Mike's:**
- The five per-stage live checks in the report.
- The clinical A4 suite before Alpha, about $4.
- The persona-file cleanups (Denied).
- M7 go-live from `scripts/session_shape_baseline.py`.

