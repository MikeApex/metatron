### 2026-11-04 (Whole-codebase Fable review — prompt written, reviewer agent created, not yet run)

**What changed.** No runtime code. Two files, both development-side:
`archive/handoffs/2026-11-04-whole-codebase-review-prompt.md` (the paste-ready prompt for a
fresh Fable 5.1 session) and `.claude/agents/codebase-reviewer.md` (a read-only area reviewer:
`model: fable`, tools Read/Grep/Glob only). Nothing to deploy.

**How the prompt was built.** First drafted codebase-agnostic, after an interview with Mike on
optional items. His picks: cost (all four classes), test adequacy, operational/deploy risk, and
his own addition, **loose ends** — everything that should be wired is, or has a plan, and
nothing obsolete lingers. Settled decisions: challenge only with evidence. Execution: fan out
by area plus adversarial verify. Output: findings with fixes, plus token budget and programmer
time for Red-tier fixes. The draft was then checked against the real codebase (`/metatron-code`)
and redrafted with 22 changes, chiefly:

- an explicit accepted-risks list that is never a finding (A4 suspended, no off-machine backup,
  quick→clinical routing, no ZDR, ROADMAP's A8 text, check 8's wording) — without it the top
  findings would have been the rulings Mike already made;
- review committed HEAD in a pinned worktree; WhatsApp reader and the 10-26 clean-room
  transcripts excluded; no live runners (meters, fixture dirt); no VM; nothing off-machine;
- eight fixed areas sized from the code, each reviewing its own tests; one verifier per area
  (17 agents total), not one per finding;
- second-user isolation as its own high-importance sub-dimension, flagged "before a second
  user goes live";
- Red-tier estimates priced as a main-session Opus build plus Mike's approve/deploy/live-check
  time; Denied-tier fixes shown separately.

**Believed true, turned out wrong.**
- The draft's 3M-token cap was below the codebase: the committed surface is ~1.7M tokens to
  read once (code ~1.0M, agent/config ~0.17M, test code ~0.5M), so the 80% stop would have
  fired mid-area and halved coverage. Re-estimated at ~$180 (range $120–300) on Fable 5.1
  rates; cap set at $250.
- `docs/WORKFLOW.md` says `DEV_BACKLOG.md` costs ~4k tokens to read; it is 232 KB, ~58k.
- `CODEBASE_INDEX.md` (09-10) and ROADMAP A8 describe a 1,870-line orchestrator with
  `run_pipeline_session` at line 621; `core/orchestrator.py` is 7,873 lines.
- Found while redrafting: `scripts/hook_subagent_gate.py` blocks any subagent from reporting
  until `qa_sweep.sh` passes on its tree, so a HEAD that already fails the sweep would strand
  every read-only reviewer. The prompt now runs the sweep first and stops to tell Mike.

**Rejected.** `/code-review ultra` as a substitute (bundles code to the cloud). `Explore` as
the reviewer type (locates, does not audit). Area reviewers on Opus 5.5 (~$100) — kept Fable
throughout under the "review in Fable" rule.

**Commits:** the archive commit for this session. Not deployed — nothing deployable.

