### 2026-11-23, nineteenth (ranking phase 3 made deploy-ready — the weekly look back and signals switched on, the back burner left as a dry run; its four checks filed) — `bbd3897` — **committed; Mike deploys**

**Incoming handoff:** § 11-23 eighteenth. Phase 3 was built and committed (`e2578d6`) with every
flag off, and one decision was put to Mike: should `ranking_signals` be on at the deploy?

**Mike: "include everything in the deploy."** Read as:
- **on:** `weekly_priorities` and `ranking_signals`, both in the committed
  `config/modules/day_plan.yaml`;
- **off:** `back_burner`.

Why `back_burner` stays off: off is the dry run, which lists what it would park and closes
nothing. The plan and the dry-run walkthrough put parking behind a review of that list, and
switching it on without the review would park real tasks unseen. Rejected: turning it on too
(the literal reading of "everything").

What the deploy starts:
- the weekly review opens with the look back;
- the daily signal rows begin;
- the back burner's would-park list begins.

The flag test was updated to match (`test_ranking_v2` 58/58, Part A 21/21).

**Filed at his ask** (four inbox fragments, folded by the sync):
1. the back-burner dry-run review, due ~12-01;
2. the weekly look back's live check over two weekly reviews, due ~12-08;
3. the first monthly signals review, due ~12-31;
4. the passion double-count re-count, waiting on the phase 2 live check.

**Wrong in passing:** a commit command that also appended to the plan through the shell was
stopped by the commit guard. The guard cannot account for a file a shell redirect wrote. The note
went in through the Edit tool, then staging and commit ran as separate steps.

