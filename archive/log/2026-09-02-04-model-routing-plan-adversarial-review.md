### 2026-09-02 (Model/effort routing build plan — adversarial review; build shelved)

A hunt-only adversarial review (Fable 5, no-verdict brief supplied by Mike) of
`archive/plans/model_routing_build_plan_2026-09-02.md` — the dev-environment model/effort
routing plan drafted in a parallel chat. Full findings:
`archive/plans/model_routing_build_plan_review_2026-09-02_fable-5.md` — 5 WILL BREAK,
9 MIGHT BREAK, 6 cannot-be-answered gaps. Checkable claims were verified against live
artifacts, not just the document: line counts (global CLAUDE.md 194, project 307 — both as
the plan stated), `.claude/settings.json`, `scripts/hook_agent_spawn.py`, `~/.claude` not
being a git repo. The sharpest findings: the plan's task 4 (`effortLevel: "medium"`
persisted) silently degrades the plan's own mandated Fable-at-`high` review with nothing
that would notice; its commit step has no repository for the three `~/.claude` artifacts;
its cost budget's "nothing persists" claim is contradicted by the spawn-ledger its own
task-6 host hook already writes (`.claude/.session_state/*.spawns.log`, no owner, no expiry).

**Decisions.** Mike shelved the build ("not pursuing for now") after the review; a
complementary plan is expected from another chat and will land in `archive/plans/`.
"Create an artifact for the review" was fulfilled as a file in `archive/plans/`, not an
Artifact publish — rejected because Artifact is Denied on this project (nothing leaves the
machine, 2026-08-18) and a file is the standing convention.

**Not done, deliberately:** `/archive` step 0 pattern-matched the four
`archive/handoffs/2026-09-02-*` files as a `/backlog attack` in progress ("consume then
delete"). They are the staged session-⑤–⑦/walkthrough launch prompts from commit 3dad094,
not worker handoffs — consumed nothing, deleted nothing. The plan file itself and the two
older untracked spec packets in `archive/plans/` were left uncommitted for their author
sessions. No code, config, or roadmap touched; no commits before close-out; nothing owes
a deploy. Fragment 2026-09-02-03 (Mark 2 endeavour plan) remains the day's other entry.
