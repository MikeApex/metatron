# Harness Backlog — defects in the development tooling itself

**This is not Metatron work.** Everything here is about the machinery we *build with* —
Claude Code hooks, git worktrees, the permission matcher, `deploy.sh`'s lock, the `/fix`
pipeline. None of it touches the orchestrator, agents, personas, routing or the VM. It is
kept out of `DEV_BACKLOG.md` deliberately: that file has a line ceiling and a reader looking
for product work, and its `now / later` counts stop meaning anything if harness items are
mixed in.

> **This list is reconciled within the build that opened it — it is not carried.**
> It exists because the development-throughput plan
> (`~/.claude/plans/jaunty-kindling-clarke.md`) found defects in its own components faster
> than they could be fixed in place. Every item closes, or is explicitly and datedly
> deferred with a reason, before that plan is called done. A harness backlog that outlives
> its build becomes a second permanent bin, which is the thing `CLAUDE.md`'s "one home per
> rule class" rule exists to prevent.

**Source of most entries:** the §10 pre-flight, 2026-08-13. Its whole finding is that this
system's components were each built and tested against the **main tree** while the point of
the system is **worktrees**, and that every defect so far appeared only when something was
actually run. Items below are marked *confirmed* only where they were reproduced live.

---

## Open

- **[H2] The deploy lock is blind across worktrees — two deploys can still interleave.**
  *Confirmed live 2026-08-13.* `deploy.sh` computes
  `LOCK_DIR="$(dirname "${BASH_SOURCE[0]}")/.deploy.lock"`, and a worktree carries its own
  tracked copy of `deploy.sh`, so it computes `metatron-wt-<slug>/.deploy.lock` — a
  different path. Both `mkdir` calls succeed, then both `git push origin main` and both SSH
  the same VM. This is precisely the 2026-08-09 interleave the lock was built to prevent,
  reintroduced by the worktree system.
  **Fix is Red-tier** (`deploy.sh`), so it was not made inline. The lock needs a path shared
  by every worktree; `git rev-parse --git-common-dir` resolves to the main tree's `.git`
  from inside any worktree and is the obvious candidate. Note the refusal message already
  prints `$LOCK_DIR` — this was visible to anyone who read it.

- **[H6] Workers spawned with `isolation: "worktree"` check out `origin/main`, not local
  `HEAD`.** *Confirmed live 2026-08-13.* Two probe workers landed on `53f99f7` while local
  main was `983f50c` — 11 commits and six hours behind — and a third landed on the new HEAD
  immediately after a push, which pins the base to `origin/main` exactly. `origin/main` only
  advances when something pushes, and the convention here is commit-locally-often,
  deploy-rarely, so **workers are stale by default**. Three consequences:
  1. A worker's tree had no `scripts/qa_sweep.sh` at all, so the `SubagentStop` gate could
     never sweep it and fell back to the main tree 100% of the time.
  2. A worker's diff is written against a stale base and can revert newer work when merged.
  3. Workers read **retired rules** — at `53f99f7`, `PROJECT_LOG.md` was still hand-edited
     and `.claude/backlog_inbox/` did not exist, so a worker would confidently violate both
     rules that shipped that afternoon.

  **No configuration knob exists.** `--worktree` is a session flag; nothing in the settings
  schema covers the subagent base; the CLI binary is a packed bundle with no extractable
  strings. So the remedy is a design choice, and it is **open**:
  - *Keep `origin/main` current.* **Rejected as a standing habit** — the plan's premise is
    mechanism over memory, and a rule you have to remember is not a control. Viable only if
    something enforces it.
  - *Stop using `isolation: "worktree"` in `/fix`* and dispatch into a
    `scripts/new_worktree.sh` tree, which correctly branches from local `HEAD`. Structural,
    but changes how the worker is addressed and needs the gate's `payload.cwd` path
    re-checked against it.

- **The Denied permission tier is not enforced against `Write` — only `Edit` rules match.**
  `claude config list` says so plainly: *"Permission deny rule
  (`.claude/settings.json`): `Write(./config/constitution.md)` is not matched by file
  permission checks — only `Edit(path)` rules are."* The same warning fires for
  `config/personas/mike.md`, `config/personas/mike/**`, `data/personas/**`, and the *ask*
  rule on `config/agents/*.md`. So the paths `CLAUDE.md` documents as *"blocked; must be
  lifted explicitly"* — including `config/constitution.md`, which is Tier 0 — are blocked
  against `Edit` and reachable by `Write`, and the Red-tier prompt on agent files can be
  sidestepped the same way. Found incidentally 2026-08-13; nothing was written to any of
  those paths.
  Fix is mechanical (`Edit(path)` covers all file-editing tools), but `.claude/settings.json`
  is the authority for the whole change-tier table, so it wants its own gate.
  **While in there: check whether any other rule in that file is expressed in a form the
  matcher silently ignores** — a deny rule that does not match is indistinguishable from one
  that does until someone tests it.

- **`defaultMode: auto` is not in effect; sessions run `default`.** Phase 1's measured
  85–88% prompt reduction is therefore unrealised — the plan's headline outcome has never
  been observed (plan §10, hypothesis H5). Detected by `scripts/hook_context_gate.py`'s
  fallback detector. Likely fix is an explicit `permissions.allow` list rather than
  `defaultMode`, since compound commands are matched per-subcommand and an allowlist reaches
  the same coverage. *(Also filed in `DEV_BACKLOG.md` Inbox before this file existed — close
  it there when this closes.)*

---

## Closed in this build

- **[H1] The `SubagentStop` gate swept the session's tree, not the worker's.** *Confirmed
  live, then fixed —* `8ebc5a4`. The gate resolved its root from `CLAUDE_PROJECT_DIR`, the
  tree the *session* started in, while the worker sat in `.claude/worktrees/agent-…`. It
  passed workers whose worktree was broken and failed them for the main tree's state:
  assurance it did not have. The payload carries `cwd` and it is the worker's tree, so `cwd`
  now wins, each candidate is checked for `qa_sweep.sh` before being swept, and every run
  logs which tree it chose. **Note H6 still blocks the payoff** — until a worker's tree
  actually contains `qa_sweep.sh`, the gate correctly falls back and now says so.

- **The gate's own ledger logged to the tree it had just swept.** *Fixed — `75fee3a`.* An
  `isolation: "worktree"` worktree is deleted the moment a worker finishes without changes,
  taking its `.claude/` with it, so the ledger survived only when the gate **fell back** and
  vanished whenever it did the right thing — exactly backwards. Observed across three probe
  workers before it was understood.

- **`METATRON_COMMIT_GUARD=off` did not work.** *Fixed — `75fee3a`.* The documented escape
  hatch — named in `CLAUDE.md`, `.claude/commands/fix.md`, and the guard's own block message
  — was inoperative. The guard read `os.environ` only, but it runs as a separate process
  spawned with the *session's* environment; an inline `VAR=off git commit` prefix lives in
  the command string it is handed and is applied to `git` afterwards, so the guard never saw
  it. It blocked, told the reader to use the override, and blocked that too. Now parsed from
  the command string as well as the environment. Verified in both directions on a real
  payload: a plain commit still blocks, the same commit with the override proceeds.

---

## Known limits of the guards themselves

Recorded so nobody over-trusts a clean run.

- **The commit guard false-positives on any file written by a script rather than
  `Edit`/`Write`.** Its `PostToolUse` recorder never hashes those writes, so the file looks
  changed-underneath. Hit twice on 2026-08-13 (a `python3` heredoc edit, and
  `sync_dev_backlog.py`'s own write to `DEV_BACKLOG.md`). `CLAUDE.md` already documents the
  shape — *"not a file a script wrote"* — and the override is the intended answer, which is
  why the override being broken mattered.
- **`qa_sweep.sh` is static.** `py_compile` parses without executing; it passed the
  `NameError` that crash-looped the scheduler after deploy, and one in the commit guard. A
  green sweep is not a test.
