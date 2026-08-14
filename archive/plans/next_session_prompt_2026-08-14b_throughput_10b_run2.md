# Next-session prompt — §10b run 2, the two-window collision, and nothing else

*Written 2026-08-14 at the close of the runs-3-and-1 session. Supersedes
`next_session_prompt_2026-08-14_throughput_10b_rehearsal.md`, whose runs 3 and 1 are both done.
**Run 2 is the last thing in the entire development-throughput plan.***

---

## WHAT CHANGED — read before dispatching anything

- **Run 3 — DONE. Checks 10 and 11 both observed.** Check 10 had never been observed before.
- **Run 1 — DONE.** `[DB-0813-01]` shipped as `20ad1ff`. **One step deliberately left — see below.**
- **Two defects fixed** (`9316284`, `7d7e349`). **Nothing deployed; no runtime code touched.**
- **`SESSION.md` was NOT rewritten and `/archive` was NOT run this session** — a second window was
  mid-rewrite and one window owns `/archive`. The session's history is in
  `archive/log/2026-08-14-03-10b-runs-3-and-1-checks-10-11-observed.md`. **`SESSION.md` is therefore
  stale on §10b** — it still says runs 3 and 1 are pending. Fix it when you close out.

### ⚠ THE ONE UNFINISHED STEP — do this early, it is one line

**`[DB-0809-02]` still needs its `due: 2026-08-17` marker.** Run 1's feature is live but has
nothing to display until an item carries a marker. Add `due: 2026-08-17` inline to
`[DB-0809-02]`'s entry in `DEV_BACKLOG.md`, then verify:

```
python3 scripts/sync_dev_backlog.py --today 2026-08-16   # expect NO ⚠ due: clause
python3 scripts/sync_dev_backlog.py --today 2026-08-17   # expect ⚠ due: DB-0809-02
```

**Do NOT tag `[DB-0809-21]`.** The previous brief called it due; it is **event-gated, not
date-gated** — it needs a real unreferenced calendar event to exist, so no date will ever make it
due. A `due:` marker on it would fire forever and be wrong.

---

START HERE:
1. `/metatron-code`
2. `./scripts/qa_sweep.sh` — **9 checks, ~6.6s, zero tokens.**
3. `git log --oneline -6`
4. Plan §10 in `~/.claude/plans/jaunty-kindling-clarke.md` — run 2's shape and the Verification
   table. **Do not re-plan it.**

STATE: phases 0–2, 3a, 3b, 4, 5, 6, 8, §10a, `[H7]`, `[H8]`, **§10b runs 1 and 3** are done and
committed. **23 defects across this plan, every one found by running, none by reading.**

---

## THE WORK — run 2, and only run 2

Two live windows, both on `tools/obligations.py`; both writing a log fragment; both filing a
backlog fragment; both attempting a deploy.

**Pass:** the commit guard blocks the second commit **naming the file** (**check 4 — still never
observed, and it is the last unobserved check in the plan**) · both log fragments survive and
`build_project_log.py` orders them (check 13) · both backlog fragments fold · the second deploy
refuses, **naming the first** (check 8).

### The deploy leg — DECIDED: use a decoy, do not lift the deny

`./deploy.sh` is in `deny` and **stays there**. Build `probe_deploy.sh` carrying `deploy.sh`'s
**verbatim** lock block and nothing else, run from both windows.
`scripts/check_deploy_lock.sh` already extracts that block by `sed` range — **reuse its approach
rather than hand-copying**, or the probe tests a lock that is not the real one, which is the exact
defect that made the original lock probe worthless.

> **Never test a `Bash` permission rule by running the real command.** It only reaches execution in
> the branch where the rule *fails*, so a negative result **is** the damage. `deploy.sh` has **no
> argument parsing whatsoever** — no `case`, no `getopts`, no `$1` in 269 lines — so there is no
> "harmless flag". It ignores unknown arguments and proceeds to push, SSH, pull, `pip install` and
> restart both units.

### Two things measured this session that change how you run it

1. **Check H2 across a worktree, not just two main-tree windows.** The lock passes on two main-tree
   windows; `LOCK_DIR` derives from `dirname "$0"`, so a worktree may compute a different lock.
2. **The commit guard fails closed on shell it cannot parse** — a trailing `echo "exit=$?"` after
   `git commit` blocks the commit. Account for it or the run reads as a pass for the wrong reason.

---

## COST — estimate by task shape, not by worker count

**The ~50–64k per-worker figure does not transfer to build work.** Measured this session:

| Worker | Task shape | `subagent_tokens` | Tool uses |
|---|---|---|---|
| compile-fault injection | edit and report | 46,439 | 3 |
| Red-tier injection (wasted, stale premise) | verify and stop | 46,462 | 3 |
| Red-tier injection (real) | verify and stop | 49,923 | 6 |
| run 1 build | build, test, report | **76,612** | **24** |

219,436 total against §10b's ~165k. Run 2 is mostly two *live windows*, not workers, so its cost
lands in the `Stop` hook's figures rather than `subagent_tokens`.

> **Three quantities are called "tokens" here. Never convert between them.** `subagent_tokens`
> (per-worker, the table above) · **raw** (every token through the API, ~98% cache reads) ·
> **weighted** (input-token equivalents). The `Stop` hook reports the last two. **Reporting the
> hook's figure against the 165k would look like a catastrophic overrun and mean nothing.**

---

## STANDING RULES

- **ACTUALLY RUN THE THING. 23 for 23.** Static reasoning has never once caught a defect here
  before execution did. This session added two: a `CLAUDE.md` worked example four days stale that
  argued a whole test into the wrong shape, and a worktree ledger gap that only appeared when a
  sync was actually run inside a worktree.
- **Verify a premise against current code before acting on it — including a premise from
  `CLAUDE.md` or from a prompt like this one.** Both of this session's wasted work items came from
  trusting a written premise. **This file is not exempt.**
- **The obvious fix is sometimes worse than the bug.** `link_back ".dev_backlog_seen"` would have
  turned a noisy duplicate into a silently lost change request. Ask what the fix costs in the
  failure direction before taking it.
- **Brief a worker as ordinary work, not as a test**, when testing whether it stops. A worker told
  it is being tested stops for the wrong reason and proves nothing.
- `./scripts/qa_sweep.sh` is 9 checks, ~6.6s, zero tokens. **A green sweep is not a test** —
  `py_compile` parses without executing.
- `archive/PROJECT_LOG.md` is **GENERATED** from `archive/log/` fragments by
  `scripts/build_project_log.py`. **NEVER hand-edit it.** Each fragment owns its trailing blank line.
- **A fragment is the collision-safe half of `/archive`.** When two windows are live, one owns
  `/archive`; the other writes a fragment and leaves `SESSION.md` alone. That is what this session
  did and it worked.
- Metatron defects → `.claude/backlog_inbox/`. **A harness defect goes in the log fragment**, not a
  harness backlog — there is no longer one, and it must not be recreated.
- **A tool named in an agent file is a specification, not a bug to delete.** `check_agent_tools.py`
  reports 66 not-granted findings; that is a development signal, deliberately kept out of
  `DEV_BACKLOG.md` and the quality-event stream because volume teaches a reader to skip it. **Do
  not file them.**
- **NEVER use `isolation: "worktree"`** — it checks workers out from `origin/main`, not local
  `HEAD`. Use `./scripts/new_worktree.sh <slug>` and pass the ABSOLUTE PATH; a worker cannot
  persistently `cd`.
- `METATRON_COMMIT_GUARD=off` is the documented override for the known false-positive class.
- **Check `git show --stat` after committing, not just the exit code.**
- **Use `git commit -F <file>` for any message containing backticks.**
- **`git diff <file>` before staging it**, and stage by explicit path — a second window is often
  live in this tree. This session found five files modified underneath it mid-run.
- **One commit, one reason.** "Found in the same session" is not a reason.
- **Always name the machine and use full paths** in any terminal instruction.

## CONSTRAINTS

- Open every work block with a gate: what runs, workers/model/concurrency, file manifest, token
  estimate WITH its basis. Close by reporting the **`Stop` hook's actual**.
- Caps: 3 workers, 10 items per verify, 1 task per `/fix`.

## AFTER RUN 2 — the plan is finished

`DEV_BACKLOG.md` is **577 lines against its ~450 ceiling**, the signal that `## Later` is
accumulating narrative. A `/backlog deep` pass is the right next thing. The `⚠ machine: ×5`
(`mike.md:13`'s consolidated-evening-check-in preference) is still unactioned; by the standing rule
it is **design**, belongs in `synthesizer.md`, and the `mike.md` copy is deleted in the same pass —
`mike.md` is **VM-owned**, so pull it down, never reconstruct it on the Mac.

MODEL: Opus. Run 2 is two live windows and judgement about what a failure means.
