### 2026-08-13 (§10a substrate pre-flight — seven defects, every one only by running)

Ran the throughput plan's §10 pre-flight before phases 8 and 5. It did the job it was scoped
for: **it killed the expensive run before it was paid for.** Seven defects, four fixed
(`8ebc5a4`, `75fee3a`, `7d196df`), three left open with reasons. **Not one was found by
reading.** That is now 12 for 12 across two sessions on this plan — every component of this
system has failed only under execution, having passed careful static reasoning first.

**§10 was split, on Mike's challenge, and he was right.** He asked why a massive integration
test was running mid-build rather than against the finished mechanism. It now reads §10a
(substrate — does the ground the build stands on work) and **§10b (the full two-window
rehearsal, runs 1–3), moved to after phases 8 and 5.** §10a could not wait, because phases 5
and 8 both *build on* the worker substrate: phase 5 dispatches workers, and phase 8 would have
documented a worker loop that was silently 11 commits stale.

**What was confirmed, worst first.**

- **H1 — the `SubagentStop` gate swept the session's tree, not the worker's.** Confirmed live:
  a probe worker sat in `.claude/worktrees/agent-a3e98cda5` while the gate swept the main tree.
  It was passing workers whose worktree was broken and failing them for the main tree's state —
  assurance it did not have.
- **H6 — new, unhypothesised, and worse.** `isolation: "worktree"` checks workers out from
  **`origin/main`, not local `HEAD`.** Two probes landed on `53f99f7` while local main was
  `983f50c` — 11 commits, six hours — and a third landed on the new HEAD immediately after a
  push, which pins the base exactly. `origin/main` only moves when something pushes. So a
  worker's tree had **no `qa_sweep.sh` at all** (the gate could never sweep it), its diff was
  written against a stale base, and it read rules retired that afternoon — at `53f99f7`,
  `PROJECT_LOG.md` was still hand-edited and `.claude/backlog_inbox/` did not exist.
- **H2 — the deploy lock is blind across worktrees.** A worktree carries its own tracked
  `deploy.sh`, so `LOCK_DIR` computes a different path; both `mkdir`s succeed, both push, both
  SSH the same VM. The 2026-08-09 interleave, reintroduced by the worktree system. **Open —
  Red-tier, not made inline.**
- **`METATRON_COMMIT_GUARD=off` was inoperative.** The escape hatch named in `CLAUDE.md`,
  `/fix.md` and the guard's own block message. It read `os.environ` only, but runs as a separate
  process spawned with the *session's* environment, so an inline `VAR=off git commit` prefix was
  never visible to it. **The guard blocked, printed the remedy, and blocked the remedy.** Any
  earlier session hitting a false positive had no way past it.
- **The gate's own new ledger logged to the tree it had just swept** — and an
  `isolation: "worktree"` tree is deleted the moment a worker finishes unchanged. So it kept the
  runs where the gate *fell back* and lost the runs where it *worked*: exactly backwards. Found
  by running it, one hour after writing it.
- **The Denied permission tier is not enforced against `Write`.** `claude config list` says so
  plainly: only `Edit(path)` rules match file permission checks. `config/constitution.md` —
  Tier 0, documented as blocked — is reachable by `Write`. **Open.**
- **`/archive`'s push is never verified and silently did not happen for 11 commits.** `983f50c`
  is itself an `Archive:` commit that never reached GitHub. Two costs: the offsite backup was
  six hours stale on the day the repo gained five components, and **H6's blast radius depended
  on it**, since worker freshness keys off `origin/main`. **Open.**

**The decision, and the option rejected.** H6 had two remedies. *Keep `origin/main` current* was
**rejected** — Mike ruled that a standing habit is anathema (the plan's premise is mechanism over
memory), and investigation confirmed no configuration knob exists to automate it. It was also
wrong on its merits: it makes worker freshness a reason to **push**, and push is the irreversible
step guarded by a review window that exists because `git add -A` once swept 41 files of journals
and clinical logs to GitHub (this log, 2026-07-29). Publication must not be coupled to wanting a
worker. So `/fix` now creates the tree with `new_worktree.sh` (local `HEAD`) and dispatches by
absolute path, **no isolation flag**.

**That option needed one re-check, and the re-check found the trap.** A worker **cannot
persistently `cd`** — the shell resets between calls — so a worker told to work in a worktree
edits by absolute path while `payload.cwd` stays pinned to the main tree. Measured: the gate
swept the main tree, passed, and the worker's change sat unswept. **Preferring `payload.cwd`
would have reintroduced H1 in a new costume.** Fixed by having the gate **ask git rather than be
told** — it sweeps the reported tree plus every registered worktree carrying uncommitted work,
covering both dispatch styles with no worker cooperation and no ID to correlate. Verified by
breaking a *tracked* file in a worktree the payload never named.

**Believed true earlier, wrong:** that the pre-flight was two cheap probes. H1 and H2 were, but
they exposed H6, which was the real finding and cost three worker spawns.

**A second bin was created, deliberately.** `HARNESS_BACKLOG.md` — defects in the tooling we
build *with*, which have no Metatron content and would have diluted `DEV_BACKLOG.md`'s line
ceiling and its `now`/`later` counts. Mike caught this as the items were about to be filed into
the wrong file. Its contract is written in: **reconciled within the build that opened it, never
carried**, because a harness backlog that outlives its build has become the permanent second bin
that "one home per rule class" exists to prevent. `CLAUDE.md`'s table records the exception, so
the next session does not merge the two back together.

**Cost calibration, which the plan needed.** Estimates ran 2× over, and the whole miss is one
line item: a **cold worker costs a flat ~32k tokens before it does anything**. Three probes cost
96k of ~170k total. The 1.3–1.5× multiplier does not apply to worker spawns — the flat 32k is
added first, then the multiplier.

Commits `8ebc5a4`, `75fee3a`, `b2c310d`, `7d196df`, `6e1fc75`. **Nothing deployed** — no runtime
code changed. `origin/main` pushed current (which is itself one of the findings above).
