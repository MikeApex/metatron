### 2026-08-13, last (development throughput phases 3a/3b/6/4 — worktrees, shared-state fragments, the QA sweep, `/fix`) — `ef3499b`, `dd237e1`, `fcac265`, `65b96a5`, **not deployed**

*Continuation of the throughput session earlier the same day (phases 0–2). No Metatron runtime
code touched. A parallel window was working `DEV_BACKLOG.md` throughout and committed `f31838a`
between two of these — the coordination that made that safe is recorded below.*

**The finding that outranks everything else built here: five components, five defects that only
appeared when the thing was actually run.** Each had passed careful static reasoning first. That
is the base rate this entry exists to record, because it is the argument for the integration test
now recommended before phase 5.

1. `new_worktree.sh` — `cp -R "$src" "$dst"` with `$dst` already existing nests it as
   `data/personas/<name>/<name>`. Written on the assumption the target was absent.
2. `.gitignore` said `.venv/` and `certs/`. **A trailing slash matches a directory but not a
   symlink to one**, so every worktree began permanently dirty, which made `rm_worktree.sh`'s
   "would this lose work?" check refuse *every* removal — training `--force` as the routine path
   and destroying the check.
3. `qa_sweep.sh` — three separate scoping faults, below.
4. `check_agent_tools.py` exited 1 on a clean tree over four false positives.
5. The stale-lock probe **silently tested the wrong lock** — it resolved `LOCK_DIR` from `/tmp`,
   its own location, acquired a fresh lock there, and "passed" while measuring nothing. Caught
   only by checking the PID file afterwards.

---

**Phase 3a — worktrees (`ef3499b`).** `./scripts/new_worktree.sh <slug> [--with-personas]` creates
`../metatron-wt-<slug>` on branch `wt/<slug>`, symlinking the gitignored runtime deps a fresh
checkout lacks. `rm_worktree.sh` refuses when the tree holds uncommitted changes or commits not
reachable from `main`, keeps the branch when commits are unmerged, deletes it when merged.

**The plan's premise here was wrong and the correction matters more than the scripts.** It said
`data/personas/*/` is gitignored wholesale, so a worktree lacks the synthetic fixtures.
**`.gitignore` does not untrack**, and the seed fixtures were committed before the rule landed. A
worktree therefore gets a *hollow* fixture tree, not an absent one — `sarah_chen` is 3 tracked
files against 26 on disk, `ryan_holiday` 20 against 133. **That is worse than absent.** An absent
fixture fails loudly on first open; a hollow one lets an A4 or B1 suite run far enough to produce
a result against incomplete data. `mike` is genuinely absent at 0 tracked files, so the one tree
that must never appear does not. Verification check 7 in the plan (`ls .../data/personas/` →
absent) is therefore testing the wrong thing and needs rewriting.

`--with-personas` **copies rather than symlinks** — 9.3 MB, cheap — because three concurrent
workers sharing one `context.json` is the exact collision class worktrees exist to remove.

**Phase 3b — shared state (`dd237e1`).** `archive/PROJECT_LOG.md` is now **generated** by
`scripts/build_project_log.py` from `archive/log/`. Append-only was never the property that saved
it: both windows append at the *top* of a newest-first file and land on the same lines. One file
per write is what cannot collide.

**Deliberate deviation from the plan**, which called for splitting the whole file into one
fragment per entry. That split is not mechanically reliable — of 93 `###` headings only 44 are
date-prefixed; entry headings and sub-headings *within* entries are both H3 with nothing to
distinguish them (`### Deploy verification — 2026-08-03` is a sub-heading, `### Also done
2026-08-03 (...)` is an entry); and there are two separate `## Dated history` sections. Splitting
on `^### ` shreds entries, splitting on `^### 2026` misses half. **The migration also buys
nothing** — historical entries are never edited again, so they never collide; all the risk is in
new entries. So the history is frozen verbatim in `archive/log/_history.md` and only new entries
are fragments, which makes the result **provable** in a way a heuristic split could not be:
`--check` with zero fragments reproduces the file byte-for-byte, verified by SHA-256 either side.

`DEV_BACKLOG.md`'s `## Inbox` gains `.claude/backlog_inbox/<slug>.md` fragments, folded in by the
sync and deleted **only after the write succeeds** — a fragment deleted before a failed write is a
silently lost change request. Fragments are gitignored and transient. This also kills "never
reserve an ID" as a rule anyone has to remember. First version appended *past* the `---` closing
the section, putting new items visually outside the Inbox.

`./deploy.sh` takes a lock before pushing. **`mkdir`, not `flock` — `flock` is util-linux and does
not exist on macOS**, which is where the script runs. It refuses loudly, naming the holder's PID
and start time, because a lock that blocks silently teaches nothing. A dead holder's lock is taken
over with a warning. **The trap is installed only after acquisition**, so a refused process cannot
delete the holder's lock — the subtle way to get this wrong, confirmed by the lock surviving a
refusal. All three paths exercised; `deploy.sh` was only ever run in its refusing configuration,
so nothing was pushed or deployed.

**Phases 6 and 4, committed together (`65b96a5`)** — because 4's `SubagentStop` gate shells out to
6's script, and registering a hook before its script exists is the failure CLAUDE.md deploy rule 2
names.

`scripts/qa_sweep.sh` chains seven checks that already existed and were fired only by memory:
agent-tools, personas, rule-overlap, project-log drift, `py_compile`, duplicate backlog IDs, dev
markers. Zero model tokens, ~6 s. **Three of the seven had to be corrected before the sweep was
usable at all, and all three failed the same way — scoped by PATH rather than by what is ours:**

1. `py_compile` over "`core/` + `tools/`" as the plan specified is **11,247 files**, not the few
   dozen it sounds like: `tools/kokoro` is a vendored TTS venv of 11,183 `.py` files, 3 tracked.
   That version took ~25 minutes and read as a hang. Now `git ls-files`, which is also the right
   boundary on principle and stays correct when the next vendored dependency lands.
2. The dev-marker grep returned torch, spacy, pip and jinja2's own comments from inside that same
   venv, and matched `# dev persona mode` in `scheduler.py`'s usage block, which is documentation.
3. The duplicate-backlog-ID check reported **47 duplicates on a healthy backlog**, because an ID
   legitimately appears inline whenever one item references another and again in the closed
   archive. Now only IDs in *defining* position count.

**Each of those three would have failed or stalled on every clean run — the failure mode that
teaches a reader to skip the output.** That is the third distinct instance of the theme
`/code-review high` found across the commit guard on 2026-08-13: silent passes on risky paths,
noisy blocks on routine ones.

`check_agent_tools.py` gained four entries in `_NOT_TOOLS`: `open_threads`, `follow_ups` and
`held_items` are context-tracker **field definitions** in `synthesizer.md`; `overdue_only` is a
**parameter** of `list_contacts()` in `relationships.md`. They were the entire reason the check
exited 1 on a clean tree, and they are exactly the bullet-leading JSON-key false-positive class
CLAUDE.md already predicts. **Nothing was deleted from an agent file to clear them** — that would
have been the wrong fix on a file whose tool references are specifications.

`scripts/hook_subagent_gate.py` blocks a worker from reporting done while the sweep fails, because
a worker *told* to run checks sometimes does not and then reports success. It **fails open** if
the sweep cannot run — stranding finished work over the gate's own breakage is the worse failure,
the same reasoning as `hook_context_gate.py` — but a sweep that runs and fails does block. Honours
`stop_hook_active` so a blocked worker cannot loop. Verified by injecting a syntax error, a
hand-edited `PROJECT_LOG.md` and a dev marker.

`.claude/commands/fix.md` carries the tier table, the premise check, explicit worker dispatch and
**one commit, one reason** (not one commit, one file). `metatron-troubleshoot.md` gained the
reciprocal handoff line so the two do not drift.

---

**Coordination, which worked and is worth recording as the pattern.** A parallel window asked
mid-session whether it could edit `DEV_BACKLOG.md`. The answer was "not yet" — this session held
it uncommitted — then "clear" thirty seconds later after `fcac265`. That window's `f31838a` landed
between two of this session's commits with no collision. **The operative fact was the clean
working tree, not any session's self-report**: a cross-session message sent to
`multi-model-mcp-4b` was answered by the VS Code keybinding session, which is what that name now
addresses; the coordinator session that had been committing that morning had already closed.
Session names are not stable identifiers for the work they once did.

**Two dev-workflow findings filed (`fcac265`), through the new fragment path rather than by hand
— its first real exercise.** (1) `.claude/settings.json` requests `defaultMode: auto` but sessions
run `default`, so **phase 1's measured 85–88 % prompt reduction is not actually in effect** —
caught by `hook_context_gate.py`'s own fallback detector. (2) `hook_commit_guard.py` refused a
commit over a trailing `echo "exit=$?"`, read as an unaccountable path expression; failing closed
is correct by design but this is a routine-path block.

**Estimates ran 1.3–1.5× over the plan's figures on all three work blocks** (3a: 12–16k → ~28k;
3b: 22–28k → ~34k; 6+4: 42–50k → ~55k). The cause was the same every time — rework from defects
that only surfaced on execution. Future blocks should carry the multiplier rather than the plan's
original numbers.

**Recommended next, and it reorders the plan: a non-atomic integration test before phase 5.**
Every component so far has been tested in isolation, against the main tree, while the entire point
of the system is that work happens in worktrees. Named untested interactions, worst first: the
`SubagentStop` gate runs `qa_sweep` in `$CLAUDE_PROJECT_DIR` and **may be checking the main tree
rather than the worker's worktree**, which would make it actively worse than no gate; the deploy
lock derives its path from `dirname "$0"` so a worktree computes a *different* lock and two
windows can still deploy at once; `PROJECT_LOG.md` is now generated and two windows can both
regenerate it; the commit guard's behaviour against a worktree commit is undefined. The plan's
phase 9 should be folded into that test rather than run separately — its checks are atomic
restatements, and three of them are already known-wrong.

