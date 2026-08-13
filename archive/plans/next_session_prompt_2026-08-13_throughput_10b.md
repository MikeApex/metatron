# Next-session prompt — backlog, code-not-rules, then §10b

*Written 2026-08-13 at the close of the throughput build; **reordered the same day** on Mike's
challenge. Paste the block below the rule as the opening message of the next session.*

**Why the order changed.** The first draft put §10b first, matching plan §10's own instruction
to run the integration test *before* building more. Mike asked whether the backlog and the
code-not-rules work should come first. They should, for three reasons — one of them a safety
issue rather than a preference:

1. **§10b run 2 attempts `./deploy.sh` from both windows.** Per `[H7]`, `ask` resolves to ALLOW
   in a non-interactive session, so that leg would really deploy to the VM, ungated, twice.
   H7 has to be settled *before* run 2, not after.
2. **Two of the three `[H8]` items are instruments §10b needs to report its own result.** Token
   accounting as a `Stop` hook is the direct fix for why §10b was deferred at all — its budget
   was a guess (45–60k estimated against 438k actual, a 7× miss). The deploy-lock invariant
   check gives run 2's deploy leg a deterministic oracle rather than a hand-run comparison.
3. **Run 1 needs a real Green-tier item**, which comes from a triage pass.

**The counter-argument, kept rather than buried:** §10's premise is that five components
produced five defects and reading found none of them, so building more before integration
testing is the mistake it exists to correct. It resolves because H8's items are **checks on
mechanisms that already exist** — they add no new surface for §10b to integrate. If any of them
grows into a new component, that argument lapses and §10b goes first.

---

Finish the development throughput plan. §10b is the last phase, but three things come before it.

START HERE:
1. `/metatron-code`
2. Read `HARNESS_BACKLOG.md` in full — a reconciliation-status block at the top, three open
   items (`[H7]`, the commit-guard narrowing, `[H8]`). Its contract is that it is reconciled
   within the build that opened it; that build is this one, and it did **not** retire on
   2026-08-13.
3. `git log --oneline -12` — the last day closed eight harness defects across two windows.
4. Read `~/.claude/plans/jaunty-kindling-clarke.md` §10 (hypotheses table, the three runs) and
   the Verification table beneath it. **Do not re-plan §10.** §10a is done; §10b's shape is
   fixed. **Its stated ~40–60k budget is stale — see task 4.**

STATE: phases 0–2, 3a, 3b, 4, 5, 6, 8 and §10a are done and committed. **H1, H2, H5 and H6 are
closed.** H2 was verified by running the lock block from a real worktree and from the main tree
and confirming one path, then confirming mutual exclusion. `defaultMode: auto` never took effect
and is gone, replaced by an explicit `allow` list the matcher honours. **16 defects across this
plan, every one found by running, none by reading.** The two most recent are worth carrying
because both looked like successes: `worker_ledger.py` reported 3 worker runs out of a real 13
with a clean table and sensible aggregates, because the records were never where the regex was
looking; and the H5 fallback detector stayed silent for a reason that was **not** success —
a briefing said its absence proved H5 had landed, and it had merely stopped being able to fire.

TASKS, in order. 4 is the main event and 1–3 exist to make it safe and measurable.

1. **`/backlog` — a triage pass.** 4 inbox · 8 now · 32 later at close of 2026-08-13. Triage the
   Inbox, and **close what the last build closed** — `[H5]` was filed in the Inbox before
   `HARNESS_BACKLOG.md` existed and its entry says to close it there when H5 closes; H5 is now
   closed. **Come out of this with the Green-tier item run 1 will use** (task 4). Prefer a
   genuinely trivial one: the point is exercising the loop, not the fix.

2. **`[H7]` — settle it before anything attempts a deploy.** The whole Red tier —
   `./deploy.sh`, `git push`, agent-file and `router/persona/scheduler/spend_guard` edits — is
   **ungated in a non-interactive session**, which is the one place nobody is watching. A plain
   CLI `claude -p` session fails the opposite way and auto-DENIES. **Cheap test first, decision
   second:** in an *interactive* VS Code session run `git push --dry-run origin main` and see
   whether it prompts. If it does, the defect is scoped to unattended sessions and the decision
   narrows a lot. Then decide whether `./deploy.sh` and `git push` move from `ask` to `deny`,
   lifted explicitly per deploy. **This is Mike's decision, not a fix to apply.**
   *Do not try to test this from a non-interactive window — `ask` auto-approves there, so a
   missing prompt is the expected null result whether the mechanism works or not.*

3. **THE CODE-NOT-RULES AUDIT — `[H8]`.** Three rules the last build enforced by memory that a
   script should enforce instead. All three are zero-token and deterministic.
   1. **Permission-rule liveness into `scripts/qa_sweep.sh`** — *highest value.* The `Write`
      deny hole was found incidentally, while `claude config list` had been printing
      *"is not matched by file permission checks"* for five rules, to nobody, for as long as
      they existed. A string match and an exit code closes the class, including the next
      well-intentioned `Write(path)` addition.
   2. **Session token accounting as a `Stop` hook** — four lines of arithmetic over the JSONL.
      Removes the estimate-vs-actual step from guesswork and gives the work-block gate something
      to be checked against. **Do this one before task 4**, which is a budget-sensitive run.
   3. **The deploy-lock invariant as a sweep check** — run `deploy.sh`'s lock block from a temp
      worktree, assert it resolves to the same path as from the main tree. Nothing currently
      stops a later session "simplifying" `--git-common-dir` back to something worktree-local,
      which is exactly how H2 arrived.

   **Build item 1 together with `[DB-0809-11]`** — it is the harness-side instance of the same
   thing ("docs record values the system changes underneath them and nothing checks"), and its
   stated fix is a smoke script running `CLAUDE.md`'s executable claims. One thing, not two.
   **Explicitly rejected, do not revive:** hunk attribution for shared-tree commits. That is the
   fingerprinting design the Chorus round killed for a fatal false negative on a shared tree.
   The mechanism for that problem exists and is `scripts/new_worktree.sh`.

4. **§10b — THE TWO-WINDOW REHEARSAL.** Full shape in plan §10.
   **Budget ~165k, not the plan's 40–60k.** Basis: measured medians from
   `python3 scripts/worker_ledger.py` — sonnet 58,879 (n=1), inherited median 64,081 (n=8),
   floor 30,023. Three cold workers. The plan's figure assumed a flat 32k retired 2026-08-13.
   Do not re-derive it from the plan text; it is stale there. **If task 3.2 landed, report the
   actual from the `Stop` hook rather than estimating it.**
   Three runs: (1) single-window happy path through `/fix` on the Green item from task 1;
   (2) **THE COLLISION** — two windows on `tools/obligations.py`, both writing log fragments,
   both filing backlog fragments, both attempting `./deploy.sh`; (3) deliberate failure
   injection — a worker leaving a `py_compile` error, and a `/fix` whose fix lands in
   `routing_cloud.yaml`.
   **Checks 4 and 10 are the two failures this whole plan exists to make impossible and NEITHER
   HAS EVER BEEN OBSERVED.** That is the point of §10b. **Check 10 needs only a worker** — run 3
   delivers it without a second window, so it is the highest value per token here. Check 4 needs
   two live windows and cannot be faked.
   **Check 1 ("ordinary inspection → zero prompts") is untestable in a non-interactive session**
   — it moved from blocked-by-H5 to blocked-by-H7. Run it in an interactive window or not at all.
   **Run 2's deploy leg is only safe once task 2 is settled.** See H7.

5. **RETIRE `HARNESS_BACKLOG.md`.** Every item closes or is explicitly and datedly deferred
   before this plan is called done. A harness backlog that outlives its build becomes a second
   permanent bin, which is what it exists to avoid. Tasks 2 and 3 close the two substantive open
   items; the commit-guard narrowing is deferred on the record as ergonomics, revisit only when
   a case appears the override does not clear.

STANDING RULES:
- `archive/PROJECT_LOG.md` is GENERATED from `archive/log/` fragments by
  `scripts/build_project_log.py`. **NEVER hand-edit it.** Each fragment owns its trailing blank
  line.
- Harness defects → `HARNESS_BACKLOG.md`. Metatron defects → `.claude/backlog_inbox/`.
- `./scripts/qa_sweep.sh` is 7 checks, ~6s, zero tokens. A green sweep is not a test —
  `py_compile` parses without executing.
- **NEVER use `isolation: "worktree"`** — it checks workers out from `origin/main`, not local
  `HEAD`. Use `./scripts/new_worktree.sh <slug>` and pass the ABSOLUTE PATH; a worker cannot
  persistently `cd`.
- `METATRON_COMMIT_GUARD=off` is the documented override for the known false-positive class
  (any file written by a script rather than `Edit`/`Write`, and a pathless `--amend`).
- Check `git show --stat` after committing, not just the exit code.
- **Use `git commit -F <file>` for any message containing backticks** — zsh ate a backticked
  word out of a commit message and the sentence lost its verb.
- `/archive` now asserts its own push. If it reports `OFFSITE FAILED`, that is real.
- **When two windows are live, one owns `/archive`.** On 2026-08-13 both reached it; the second
  stopped at step 1 rather than replacing a `SESSION.md` the first was rewriting. Step 0 is that
  check — obey it. Likewise **diff every file before staging**: that day one window's `H8` and
  another's `CLAUDE.md` hunk each sat uncommitted inside a file the other needed to commit.

CONSTRAINTS:
- Open every work block with a gate: what runs, workers/model/concurrency, file manifest, token
  estimate WITH its basis. Close by reporting actual vs estimate.
- Caps: 3 workers, 10 items per verify, 1 task per `/fix`.
- COST: a cold worker costs **~50–64k** by measurement, not the 32k this plan assumed for most
  of its life. `python3 scripts/worker_ledger.py` reports real per-model medians for free.
  Delegate nothing smaller than the briefing.
- **ACTUALLY RUN THE THING. 16 for 16.** Static reasoning has never once caught a defect in this
  system before execution did — including twice in the session that wrote this prompt, where a
  regex looked right and a detector's silence looked like success.

MODEL: Opus. §10b is live workers, two windows, and judgement about what a failure means.
