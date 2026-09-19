### 2026-09-19 (A plan can now be handed to a reviewer whose job is to break it)

Mike brought a written adversarial-review prompt and asked, before anything was built, what was
wrong with turning it into a slash command. Ten issues; four changed the design. Built as
`/adversarial-review` — `.claude/commands/adversarial-review.md` plus the reviewer itself at
`.claude/agents/adversarial-reviewer.md`, registered in `docs/WORKFLOW.md`.

**What it does.** After `ExitPlanMode`, `/adversarial-review [plan] [model] [effort]` spawns a
background reviewer that reads the plan cold, then verifies its claims against real paths and
symbols, and returns defects ranked by cost-if-wrong — split into the ones that change the plan's
shape and the ones that change one step. `verify` resumes the same reviewer against the revised
plan. Defaults: Fable, `medium`.

**Four corrections to the original prompt, each because the harness works differently than
assumed.**

1. *The plan can't be "in chat."* A subagent inherits no conversation. Plan mode writes a plan
   file, so the path exists — this turned out cheaper than feared, but the command still stops
   rather than paraphrasing a plan to a reviewer that must verify it.
2. *The prompt specified `/metatron-code` between the passes; it can't run.* Step 1 of that
   command SSHes to the VM and writes `DEV_BACKLOG.md`, which a read-only reviewer must not do.
   **Rejected**: exempting the sync, or running the command and tolerating the write. **Chosen**:
   inline the three reads (`SESSION.md`, roadmap, `CODEBASE_INDEX.md`) and drop the backlog
   telemetry, which a reviewer has no use for. This earned something unplanned — the reviewer now
   treats a plan that re-proposes a settled or deferred ruling as a finding.
3. *Read-only was prose; now it is structural.* The agent has `Read, Grep, Glob` and no write
   tools. **Rejected**: granting `Write` scoped by prose to one output path — unenforceable. The
   command writes the report verbatim to `archive/plans/`, so nothing between reviewer and reader
   paraphrases.
4. *The `discarded-candidates.md` block was dropped, not relocated.* Its guarantee was that
   discards do not influence the report; in the same response, composed in the same breath, that
   cannot hold. A weaker version filed under a flag would have looked like the original.

**The verify round has a bias the original didn't account for.** The reviewer authored the
findings, so it is the reader most likely to accept a revision that gestures at one. Verify mode
therefore requires re-anchoring to `path:symbol` — a `CLOSED` verdict without one does not count —
and carries `NEW SHAPE` for a fix that moved a defect rather than removing it.

**Renamed from `/fable-review` at Mike's call** — a model name in an invocation is a short
half-life value in a place that outlives it, the standing rule applied to a command name. Model is
now an argument. **Known limit, stated in the command rather than papered over:** the spawn
parameter takes a family (`fable`/`opus`/`sonnet`/`haiku`), not a version. Pinning Fable 5.1 over
Fable 5 is not possible from a slash command.

**A bug caught by the close-out diff, not by use.** `.gitignore` admits `.claude/commands/` and
`.claude/rules/` by allowlist; `.claude/agents/` was not admitted, so the command would have been
committed without the agent it spawns and `/adversarial-review` would have failed in every
worktree and every fresh clone — the same failure mode the `.claude/rules/` admission note warns
about from 2026-08-14, recurring because the note was about one directory rather than the pattern.
Admitted with the same three-line shape.

`qa_sweep` 11/11. No deploy — Claude Code tooling only, nothing the VM runs.

