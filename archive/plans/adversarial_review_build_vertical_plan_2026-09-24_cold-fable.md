# Adversarial review — `archive/plans/build_vertical_plan_2026-09-24.md` (Build plan v4.3→v4.7, cold read)
**Reviewer:** Fable 5 (`adversarial-reviewer`, fresh — no memory of the Opus rounds), effort `high`, 2026-09-24. Started on v4.3; the file reached v4.7 during the read. Verbatim; unedited.

## STRUCTURAL

1. [§3 N12, §3 N13, §12 "Sandbox and patch", §12 "End to end"] [scripts/new_worktree.sh (branches from local HEAD at creation); scripts/hook_commit_guard.py:_attribute; .claude/rules/deploy.md rule 4; SESSION.md handoff — "the same tree carries the headset-mode chat's uncommitted changes"]
Wrong: N13 applies a `git diff HEAD` patch from the sandbox to the main tree as if that tree were clean and still at the worktree's base commit, when the project's own record says two chats run against it with uncommitted edits in the same files (`core/orchestrator.py`, `core/server.py` are dirty right now) and HEAD moves between worktree creation and N13.
Fails: `git apply` refuses or mis-applies on any context drift in a touched file, the "one `git diff` shows exactly `files[]`" criterion cannot hold on a tree carrying another session's hunks, and a park at the wiring gate leaves Build's applied-but-unstaged hunks in the shared tree where the guard's attribution places them in WARN — so another window's `git add core/orchestrator.py` sweeps half a capability into an unrelated commit, the 2026-08-09 shape.
Costs: a build that cannot land, or a partial capability deployed under someone else's commit title; high.

2. [§3 N11 partition, §3 N12 "gates and sweep", §3 N13 wiring gate, §6 "re-run by check_build_registration.py in the sweep", §10 rewrite, §12 "Wiring gate"/"Registration check"] [scripts/qa_sweep.sh check 11 → scripts/check_build_registration.py; scripts/hook_subagent_gate.py:_dirty_worktrees (sweeps the implementer's worktree at its stop); scripts/check_build_registration.py assertion 6 (landed row must carry a run line)]
Wrong: The same rewritten `check_build_registration.py` — asserting routing parity, the Coordinator directory entry, the agent file and the registry row's run line — must pass at N12 in a worktree that by the tier partition can never contain the routing entries, the agent file or the Coordinator line, and must fail at N13 in the main tree when exactly those are missing, and the plan never says how one script distinguishes the two trees.
Fails: either every `kind: agent` build fails N12 (one return to N11, then a park) because its registry row has no wiring beside it and no run line yet, or the check is written tolerant and the N13 catch of the `time_director` shape rests on `check_agent_tools.py` alone rather than the assertion §3 N13 claims.
Costs: a pipeline that cannot pass its own gate for the capability kind run 1 is, or a wiring gate weaker than the plan sells it as; medium-high.

3. [§2 "request_build (tool: Coordinator)", §14 Phase E "request_build grant", §16 Phase F run 1] [config/modules/routing.yaml, config/modules/routing_cloud.yaml — no `request_build` grant; config/agents/coordinator.md — never names `request_build`, only `ROUTING_MISS`; scripts/check_agent_tools.py (granted-but-never-named class); SESSION.md — the grant "had no owner", assigned to phase 5, which this plan deletes]
Wrong: The trigger of the whole vertical — the Coordinator's `request_build` grant in both routing files plus the instruction text saying when to file a gap instead of a `ROUTING_MISS` — is Red-tier work that appears only as a word on the Phase E deploy line, with no phase, no model, no cost line and no §12 test.
Fails: phases A–D land nothing that makes the Coordinator file a ticket, so Phase F's run 1 starts from a tool the Coordinator has never been told exists, and a grant added at deploy time without instruction text is exactly the class `check_agent_tools.py` flags.
Costs: run 1 cannot start, or starts on an unreviewed Red edit made during a deploy; high.

## LOCAL

4. [§3 N11 "in a sandbox worktree", §3 N12 three channels, §7 build-implementer "worktree only", §12 "Implementer boundary", header "Named residue accepted"] [scripts/hook_commit_guard.py:_command_anchor ("Its payload cwd is still the MAIN tree"); .claude/commands/fix.md § 3 (workers must edit by absolute path); .claude/settings.json allow: Edit/Write]
Wrong: The plan accepts only a `python3 …` grant as able to write outside both trees, but the implementer's Edit/Write tools are not confined to the worktree — a subagent's cwd is the main tree, so any relative-path write lands there, Amber paths need no prompt, and none of the three channels looks at the main tree's porcelain.
Fails: a file the implementer wrote to the main tree by mistake is absent from the worktree diff, absent from the patch's path-set check, and already sitting unstaged in the main tree when the patch is applied, so "the patch is the only thing that crossed from the sandbox" is false in the most likely failure mode.
Costs: the worktree tests pass on a tree missing the file (or fail inexplicably), and Mike's single diff carries content no gate saw; high.

5. [§5 "BLD-MMDD-NN ids allocated by replaying the day", §5 "Mac — data/build/jobs/BLD-…/", ruling 12 acceptance on a fixture persona] [core/build/ids.py:next_job_id (replays `ledger_path(persona)`); core/build/jobs.py:ledger_path — `data/personas/{p}/build/`]
Wrong: Ticket ids are allocated per persona ledger while the Mac job directory, the registry's ticket reference and `/build BLD-…` are keyed by id alone, and the plan gives the fixture persona's Coordinator the same `request_build` grant during acceptance.
Fails: two personas filing on the same day produce the same `BLD-MMDD-NN`, and `/build BLD-…` fetches from an unnamed persona's ticket file.
Costs: a job directory and registry row that point at two tickets, and a fixture persona's gap built as Mike's; medium.

6. [§3 N12 "worktree left in place", §3 N12 removal "after N13", §7 the five Build subagents] [scripts/hook_subagent_gate.py:_dirty_worktrees, MAX_TREES = 4]
Wrong: The plan leaves the implementer's dirty worktree registered until Mike removes it, without naming that the SubagentStop gate sweeps every registered dirty worktree at every subagent's stop in every window — including Build's own tool-less Inquiry and Planner, which are handed "fix what the sweep names" as a continue-reason.
Fails: a parked worktree with a failing sweep blocks once every worker in every session until it is deleted, and a no-tools subagent receiving a sweep failure as its stop reason continues past its finished artifact.
Costs: cross-window worker stalls and a second, unplanned handback from Build's judgement nodes; medium.

7. [§3 N12 "a refusal parks the job with the worktree left in place", §12 "Gates" — "refused with the worktree discarded"]
Wrong: The behaviour and its test assert opposite fates for the worktree on a deny-list refusal.
Fails: the test as written either fails against the specified behaviour or is written to the test and leaves a worktree holding a credential-path write beside the main tree.
Costs: one of the two is silently changed at implementation time, and the deny-list case is the one where it matters; medium.

*Note by the session: finding 7 was already closed in v4.7 by the Opus reviewer's round 6 before this report arrived — the cold read began on v4.3.*

## VERIFY — 2026-09-24, round 1 (plan revised to v4.8; same cold reviewer)

1. NEW SHAPE — [scripts/hook_commit_guard.py:_WRITING (watches add/commit/stash only — `git apply --3way` implies `--index` and stages unwatched); .claude/settings.json deny `Bash(git checkout .)`; config/modules/routing.yaml:coordinator.allowed_tools] The clean-path precondition covers only "every path the patch touches", so the Red half's targets (`routing*.yaml`, `coordinator.md`) can carry another chat's uncommitted lines when the main session writes into them — the exact 2026-08-09 file — and in the moved-HEAD branch `--3way` stages the applied paths, so the printed revert `git checkout -- <path>` restores from the index (the applied content), not HEAD, leaving Build's hunks in the shared tree on a park.
2. CLOSED — [scripts/check_build_registration.py:_findings_run_lines (already skips rows whose state is not `landed`, the pattern the rewrite extends to wiring); scripts/check_agent_tools.py `--agent` (line 364, exists); scripts/qa_sweep.sh check 11] `status: staged` at N11 / `landed` at N13 gives one script a tree-independent discriminator, and N12 no longer claims the wiring check.
3. CLOSED — [config/agents/coordinator.md § "Tools available" (line 214, exists); config/modules/routing.yaml:coordinator.allowed_tools `[write_quality_event]` (grant absent today, so the phase is real work); scripts/check_agent_tools.py `--agent coordinator`] Phase B-Red, § 10 fresh list, § 12 Trigger row and § 14 cost line give the trigger a home, a tier, a model and a falsifiable test.
4. CLOSED — [scripts/hook_commit_guard.py:_command_anchor (cwd pinned to main tree — the mechanism (d) is built against); .claude/settings.json allow Edit/Write (why (d) is a diff of porcelain rather than a prompt)] Channel (d) sees the main tree, and a newly dirty `files[]` path refuses; the residue (a stray write outside `files[]`) is reported, not shipped, since the patch is built from the sandbox only.
5. CLOSED — [core/build/ids.py:next_job_id (replays `ledger_path(persona)`); core/build/jobs.py:build_dir (`data/personas/{p}/build/`)] Persona-qualified job directory, `--persona` on `/build` defaulting to `mike`, a `persona` field on the registry row, and the § 12 row that mints the same id in two ledgers.
6. CLOSED — [scripts/hook_subagent_gate.py:_dirty_worktrees (the only place a registered worktree enters the sweep; a prefix skip there is sufficient because `_candidate_roots` uses payload.cwd = main tree); scripts/new_worktree.sh DEST `metatron-wt-$SLUG` (the `build-` prefix fits the slug regex)] The sandbox is excluded from every other window's stop gate; the driver's own N12 sweep replaces it.
7. CLOSED — [scripts/rm_worktree.sh `--force` (the only removal path, Mike's hand); § 3 N12 and § 12 Gates row now agree on "left in place, byte-identical"] The contradiction is gone; no code claim was involved.

### NEW (round 1)

1. [§3 N13 "applies with `--3way` if it has moved", "applies the patch (unstaged)", "the exact per-file revert command … `git checkout -- <path>`"] [scripts/hook_commit_guard.py:_WRITING — `apply` is not a watched verb; .claude/settings.json deny `Bash(git checkout .)` — the reason the per-file form is used]
Wrong: `git apply --3way` implies `--index`, so on the moved-HEAD branch the applied paths are staged, not unstaged as N13 states, and `git checkout -- <path>` then restores from the index — the applied content — rather than from HEAD.
Fails: the one-line revert printed on a red wiring gate or a 3-way conflict is a no-op for every patch-applied path in exactly the case it was added for, and the staged hunks sit in the shared tree past the commit guard, which watches `add`/`commit`/`stash` and never `apply`.
Costs: the "never with Build's hunks left in the shared tree" guarantee is false in the moved-HEAD branch, and the revert Mike is told to run does not revert; high.

2. [§3 N12 channel (a) "`git status --porcelain` in the worktree for tracked and untracked paths", channel (d) "the set of dirty paths in the main tree (`git status --porcelain`)"] [scripts/hook_commit_guard.py:_status — "`-uall` matters: without it git collapses untracked files in a new directory to a single `newdir/` entry … which is why this went unnoticed until `.claude/rules/` was created and blocked its own commit"]
Wrong: Both channels compare porcelain output to `files[]` without `-uall`, so a new file in a new directory appears as `dir/`, which is a path in neither `files[]` nor the deny list.
Fails: channel (a) refuses a legitimate new package (`tools/<newcap>/…`) as "outside `files[]`" and parks the job, while channel (d) fails to match a stray relative-path write in a new directory against `files[]` and does not refuse it.
Costs: a false park on the first capability that adds a directory, and a hole in the channel added to close finding 4, both already recorded in this repo's own hook history; medium.

## VERIFY — 2026-09-24, round 2 (plan revised to v4.9; same cold reviewer)

1. CLOSED — [.claude/settings.json deny list (`Bash(git reset --hard *)`, `Bash(git checkout .)` — neither `git reset -q -- <paths>` nor `git checkout HEAD -- <path>` matches, so the driver's forms run); scripts/hook_commit_guard.py:_WRITING (`reset`/`checkout` unwatched, so nothing blocks the revert either)] The precondition now covers `files[]` both halves including the Red targets, `git reset -q -- <paths>` after `--3way` returns the index to HEAD, and the revert reads from HEAD rather than the index; the § 12 row asserts `git diff --cached` empty after apply and porcelain empty after the revert.
2. CLOSED — [scripts/hook_commit_guard.py:_status (the `-uall` lesson the channels now copy)] Channels (a) and (d) read `git status --porcelain -uall`, so a new file in a new directory is matched by path against `files[]` and the deny list instead of collapsing to `dir/`.

### NEW (round 2)

1. [§3 N13 "A 3-way conflict parks the job with the patch's own paths restored from HEAD (`git checkout HEAD -- <path>`, then `git reset -q -- <paths>`)"; §12 Landing pre-checks "a planted conflict parks the job with the patch's paths byte-identical to HEAD afterwards"] [scripts/hook_commit_guard.py:_status (`-uall` — a leftover new file is exactly what the assertion would show)]
Wrong: `git apply --3way` is not atomic — cleanly merging hunks, including every new file, are applied before a conflicting one stops it — and the conflict-park restore uses only `git checkout HEAD -- <path>`, which errors on a path that does not exist at HEAD and removes nothing.
Fails: after a 3-way conflict every new file the patch added stays on disk (and, via `--index`, in the index until the reset), so the park leaves Build's new files in the shared tree while the wiring-gate revert line two paragraphs later already carries the correct `rm` form for exactly this case.
Costs: the § 12 "byte-identical to HEAD" assertion fails for any patch with a new file, and the conflict branch reopens the residue v4.8/v4.9 were written to close; medium.

## VERIFY — 2026-09-24, round 3 (plan revised to v4.10; same cold reviewer)

1. CLOSED — [.claude/settings.json deny list (`Bash(rm -rf *)`, `Bash(rm -fr *)`, `Bash(git reset --hard *)`, `Bash(git checkout .)` — the per-path `rm <path>`, `git checkout HEAD -- <path>` and `git reset -q -- <paths>` forms match none of them, so `revert_landing` runs in this harness); scripts/hook_commit_guard.py:_WRITING (none of the three verbs is watched, so the revert is never itself blocked)] The conflict park and the wiring-gate revert now share one function that partitions by existence at HEAD — checkout for paths HEAD has, `rm` for paths the patch added, `reset -q` over all — and the § 12 row plants a conflict in a patch that also adds a file and asserts `git status --porcelain -uall -- <files[]>` empty afterwards, which is the assertion that failed under v4.9.

### NEW (round 3)

none

**Clean pass at round 3.** Cold read on v4.3 → seven findings (one already closed); three verify rounds. Together with the Opus reviewer's seven rounds (`adversarial_review_build_vertical_plan_2026-09-24.md`), the plan at v4.10 has a clean pass from two reviewers of different model families.
