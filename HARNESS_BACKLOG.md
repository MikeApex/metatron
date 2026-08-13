# Harness Backlog — defects in the development tooling itself

**This is not Metatron work.** Everything here is about the machinery we *build with* —
Claude Code hooks, git worktrees, the permission matcher, `deploy.sh`'s lock, the `/fix`
pipeline. None of it touches the orchestrator, agents, personas, routing or the VM. It is
kept out of `DEV_BACKLOG.md` deliberately: that file has a line ceiling and a reader looking
for product work, and its `now / later` counts stop meaning anything if harness items are
mixed in.

> **Reconciliation status, 2026-08-13 (end of the throughput build).** Eight items opened, five
> closed with evidence (H1, H2, H5, H6, the `Write` deny hole, the gate ledger, the broken
> override, `/archive`'s unverified push). **Three remain open, each deliberately and with a
> reason — none by drift:** **H7** needs a decision from Mike plus one test this harness cannot
> run on itself (whether an *interactive* VS Code session honours `ask`); **the commit-guard
> narrowing** is ergonomics, not correctness, now that the override works; **H8** is a proposal
> list filed today, and is the successor work rather than a defect of this build.
> **So this file does not retire today.** It is the one outcome its own contract calls a
> failure, and saying so is better than closing three live items to make a rule come out even.
> The contract still binds: whatever carries these three names the build that owns them.

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

- **[H7] `permissions.ask` does not gate in the VS Code / Agent-SDK harness — it resolves to
  ALLOW.** *Found and confirmed live 2026-08-13, while fixing H5.* A prompt that cannot be
  shown is auto-**approved** here, not auto-denied: `git push --dry-run origin main` reached
  GitHub with no prompt, and a throwaway `ask` rule on a novel harmless command
  (`Bash(sw_vers *)`, added to `settings.local.json` and removed after) allowed it. `deny`
  is enforced in the same session and hot-reloads without a restart (`git clean -n` blocked
  before and after the settings edit; a throwaway `Bash(uptime *)` deny blocked immediately).
  **So the entire Red tier — `./deploy.sh`, `git push`, agent-file and
  router/persona/scheduler/spend_guard edits — is ungated in a non-interactive session**,
  which is the one place nobody is watching. The session reported `permission_mode: default`
  in the hook payload, so this is not a deliberate mode switch.
  **The opposite failure in the other harness:** a plain-CLI `claude -p` session auto-DENIES
  the same prompt (verified in isolated scratch projects). The two harnesses fail in
  opposite directions from identical settings.
  **Not a regression from H5's blanket allow** — precedence was tested with `allow: ["Bash"]`
  in force and both `deny` and `ask` still outranked it. The Red tier was already ungated
  here before the allow list existed.
  **Open decision, deliberately not taken inline:** whether `./deploy.sh` and `git push`
  move from `ask` to `deny` (lifted explicitly per deploy) — the strongest guarantee, at the
  cost of a settings edit per deploy. **Untested and worth testing first: whether an
  *interactive* VS Code session honours `ask`.** If it does, the defect is scoped to
  unattended sessions and the decision is narrower than it looks.

- **The commit guard blocks routine shell it cannot parse, and the routine cases keep piling
  up.** Failing closed on unparseable input is correct by design (`a66a706`), but every instance
  so far has been a *routine* path, not a risky one — the "noisy blocks on routine ones" theme
  `/code-review high` already flagged across this guard. Three now: a trailing `echo "exit=$?"`
  after `git commit`; **`git commit --amend` with no path arguments** (reported as an
  unaccountable path expression, though an amend of the message touches nothing); and **any file
  written by a script rather than `Edit`/`Write`**, whose `PostToolUse` hash is never recorded so
  the file looks changed-underneath — hit twice on 2026-08-13, once from a `python3` heredoc and
  once from `sync_dev_backlog.py` writing `DEV_BACKLOG.md`. Suggested narrowing: ignore tokens
  following a `;` that contain no `/`, and treat a pathless `--amend` as message-only.
  **Note this was strictly worse until today** — the documented override did not work either, so
  each of these was an unconditional block. *(Filed 2026-08-13 from the throughput session; moved
  here from `DEV_BACKLOG.md` when this file was created.)*

  > **DEFERRED 2026-08-13, with a reason rather than by drift.** Two more instances landed the
  > same day (a `printf` append to a log fragment; the pathless `--amend` in this session), which
  > is evidence for the item, not new items. It stays open-but-deferred because the **override
  > now works** (`75fee3a`), so every case is a one-token annoyance rather than the unconditional
  > block it was this morning — and the narrowing touches the one guard whose failure mode is
  > *blocking commits*, which is not work to rush at the end of a build. **Revisit when a case
  > appears that the override does not clear.** Ergonomics, not correctness.

- **[H8] Three rules this build enforces by memory that a script should enforce instead.**
  *Filed 2026-08-13, from the observation that every defect here was found by running
  something rather than by anyone remembering to check.*
  1. **Permission-rule liveness, into `scripts/qa_sweep.sh`.** `claude config list` already
     prints *"is not matched by file permission checks"* for every silently-ignored rule — it
     printed it for five of them, to nobody, for as long as they existed. A string match and
     an exit code closes the whole class, including the next well-intentioned `Write(path)`
     addition. **Highest value of the three: the Write hole was found incidentally, and
     nothing would have found it otherwise.**
  2. **Session token accounting as a `Stop` hook.** The work-block gate requires an estimate
     and a close-out actual; on 2026-08-13 the estimate was 45–60k and the actual 438k, a 7×
     miss, because a model estimating its own context growth is not measuring the billed
     total. It is four lines of arithmetic over the JSONL. Making it mechanical also gives
     the estimate something to be checked against.
  3. **The deploy-lock invariant as a sweep check.** Run `deploy.sh`'s lock block from a
     temporary worktree and assert it resolves to the same path as from the main tree.
     Nothing currently stops a later session simplifying `--git-common-dir` back to something
     worktree-local — which is precisely how H2 arrived.

  **Item 1 is the harness-side instance of `[DB-0809-11]`** (*"docs record values the system
  changes underneath them and nothing checks"*, whose stated fix is a smoke script running
  `CLAUDE.md`'s executable claims). This session is a clean example: the change-tier table said
  Red *"prompts every time"* and that was false. Build them as one thing, not twice.

  **Deliberately NOT proposed: hunk attribution for shared-tree commits.** Splitting one
  window's hunk from another's inside a single file was the most laborious part of this
  session, but that is the fingerprinting design the Chorus round rejected for a fatal false
  negative on a shared tree. The mechanism for that problem already exists and is
  `scripts/new_worktree.sh`.

---

## Closed in this build

- **`/archive`'s push was never verified, and it silently did not happen for 11 commits.**
  *Fixed 2026-08-13.* Step 5 ended with `git push origin main` and handled only the loud case —
  *"a rejected push stops the step and gets reported"* — while nothing asserted the outcome. On
  2026-08-13 `origin/main` sat at `53f99f7` with local `main` at `983f50c`, **11 commits and six
  hours behind**, and `983f50c` is *itself* an `Archive:` commit, so the ritual ran and lost its
  own push more than once. Two costs, one invisible: the offsite backup was stale on the day the
  repo gained five components, and **H6's blast radius depended on this** — worker freshness
  keyed off `origin/main`, so an unpushed archive quietly staled every worker.
  `/archive` step 5 now asserts `git rev-parse HEAD == git rev-parse origin/main` and prints the
  commit count when it fails, the same pattern `deploy.sh` already used with `EXPECTED_SHA`.
  **Tested in both directions**, and its first real run reported a true failure: local was 4
  commits ahead at the time of writing.

- **[H6] Workers spawned with `isolation: "worktree"` checked out `origin/main`, not local
  `HEAD`.** *Confirmed live, then resolved — `7d196df`, 2026-08-13.* Two probe workers landed on `53f99f7` while local
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
    `scripts/new_worktree.sh` tree, which correctly branches from local `HEAD`.

  **RESOLVED 2026-08-13 — the second option, and the gate had to change with it.** Chosen
  because the first couples "I want to dispatch a worker" to "publish everything I have
  committed", and pushing is the irreversible step guarded by a review window that exists
  because `git add -A` once swept 41 files of journals and clinical logs to GitHub
  (`archive/PROJECT_LOG.md:4187`). Worker freshness must not be a reason to publish.

  The re-check that option needed found the trap: **a worker cannot persistently `cd`** —
  the shell resets between calls — so a worker dispatched into a worktree edits it by
  absolute path while `payload.cwd` stays pinned to the main tree. Measured live: the gate
  swept the main tree, passed, and the worker's real change sat unswept. Preferring
  `payload.cwd` would have reintroduced H1 in a new costume. Fixed by having the gate ask
  git rather than be told — it now sweeps every registered worktree carrying uncommitted
  work, which covers both dispatch styles without the worker cooperating. Verified by
  breaking a *tracked* file inside a worktree the payload never named: the gate blocked and
  labelled the failure with that worktree's path.

- **[H5] `defaultMode: auto` was never in effect; sessions ran `default`.** *Confirmed live,
  then fixed — 2026-08-13.* The value parsed cleanly and then silently did nothing, so Phase
  1's measured 85–88% prompt reduction had **never been observed**: the plan's headline
  outcome was unrealised for the life of the file. Reproduced in this session — the
  `PreToolUse` gate fired *"requests defaultMode 'auto' but this session is running
  'default'"* on the first `Write`.
  Replaced with `allow: ["Bash", "Read", "Edit", "Write"]`, which is the same policy the plan
  specified — *deny the destructive, ask the Red row, allow everything else* — stated in a
  form the matcher honours. **Blanket rather than an enumerated safe-command list**, because
  201 of the 1,185 backtested prompts were unclassifiable compounds and an enumerated list is
  incomplete by construction, so everything omitted keeps prompting.
  **Verified by running, four ways.** (1) The allow list is honoured: the edited file copied
  into an isolated trusted project ran a command that the identical file with `allow` removed
  refused — the only difference being that key. (2) `deny` still outranks it: `git clean -n`
  was blocked in the live session after the edit. (3) `ask` still outranks it, tested with
  `allow: ["Bash"]` in force. (4) Compound commands are matched per-subcommand, confirmed
  twice by accident — a `cp … ; git clean -n` compound was refused on its second subcommand.
  **The `_comment_*` keys inside `permissions` do not break parsing** — checked in the same
  isolated run, not assumed.
  *(Was also filed in `DEV_BACKLOG.md`'s Inbox before this file existed — close it there.)*

- **The Denied tier was not enforced against `Write` — only `Edit` rules matched.**
  *Confirmed, then fixed — 2026-08-13.* `claude config list` named five silently-ignored
  rules: `Write(./config/constitution.md)`, `Write(./config/personas/mike.md)`,
  `Write(./config/personas/mike/**)`, `Write(./data/personas/**)` and the *ask* rule
  `Write(./config/agents/*.md)`. So `config/constitution.md` — Tier 0 — was blocked against
  `Edit` and reachable by `Write`, and the Red-tier gate on agent files could be sidestepped
  the same way. Nothing had been written to any of those paths.
  Fixed by **deleting** the `Write(path)` entries rather than keeping them as belt-and-braces:
  `Edit(path)` covers every file-editing tool, and a rule that does not match is
  indistinguishable from one that does until someone tests it.
  **Verified by running, on a decoy first** — a `deny` of `Edit(./probe_target.txt)` refused a
  `Write` to that path and left the file byte-unchanged, so the semantics were proven before
  the constitution was left relying on them. `claude config list` now reports **zero**
  permission-rule warnings.
  **The audit the item asked for was done and found two more silently-broken rules:**
  `Bash(./deploy.sh)` was an *exact-match* rule, so `./deploy.sh --anything` escaped the Red
  tier entirely; `Bash(./deploy.sh *)` and `Bash(bash ./deploy.sh *)` now close it. It also
  turned up **[H7]**, which is worse than either defect this item names.

- **[H2] The deploy lock was blind across worktrees.** *Confirmed live, then fixed —
  2026-08-13.* `LOCK_DIR` was `BASH_SOURCE`-relative and a worktree carries its own tracked
  copy of `deploy.sh`, so each tree computed a different lock path, both `mkdir` calls
  succeeded, and both deploys pushed and SSH'd the same VM — the 2026-08-09 interleave,
  reintroduced by the worktree system.
  Now resolved from `git rev-parse --git-common-dir`, which points at the main tree's `.git`
  from inside any worktree. Resolved **relative to the script's own directory, not the
  caller's cwd**, and made absolute — the raw output is the bare string `.git` at a repo top
  level, which would otherwise put the lock wherever the caller happened to be standing.
  Falls back to the old path outside a repo or on a git too old for the flag.
  **Verified by running the script's verbatim lock block**, not by reading it: all four of
  main-tree, worktree-invoked-from-main, worktree-invoked-from-itself, and a non-git cwd
  resolve to the same `…/multi-model-mcp/.git/.deploy.lock`. Then the property itself — the
  main tree took the lock and held it while a real `new_worktree.sh` worktree's copy was run:
  **DEPLOY REFUSED, exit 1, naming the holding PID**. The lock was released cleanly on exit.

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
