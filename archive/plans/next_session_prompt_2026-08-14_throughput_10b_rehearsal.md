# Next-session prompt — §10b, the two-window rehearsal, and nothing else

*Written 2026-08-14 at the close of the H7 session. Supersedes
`next_session_prompt_2026-08-13b_throughput_10b_and_backlog.md`, whose tasks 1, 2 and 4 are all
done. **Only §10b remains of the entire development-throughput plan.***

**What changed since that prompt.**

- **Task 1 — `[H7]` — CLOSED, and the defect was narrower than it was filed as.** See below; this
  is the one finding that changes how you work in this window.
- **Task 2 — `/backlog` triage — DONE.** Inbox 4 → 0. `## Now` is **10 — at cap.** Two entries
  were not what they said (details below).
- **Task 4 — retire `HARNESS_BACKLOG.md` — DONE.** Deleted, `e123c39`. Eleven opened, eleven
  resolved. **Do not recreate it.** Its one unfixed item is deferred on the record, not lost.
- **§10b is unchanged in shape, and is now the only remaining work.**

---

## THE H7 FINDING — read this before you run anything

**`ask` permission rules split by TOOL FAMILY in this harness, not by whether a session is
interactive.** Measured by hand, same rule and command, both harnesses, minutes apart:

| | `Edit(…)` ask rules | `Bash(…)` ask rules |
|---|---|---|
| iTerm `claude` REPL | prompts | **prompts**, and names the rule |
| VS Code chat panel | **prompts and blocks** | **silently allows** |

So the nine Red-tier `Edit` rules — `config/agents/*.md`, both routing files,
`core/{router,persona,scheduler,spend_guard}.py` — have teeth here and always have. Only
`./deploy.sh` and `git push` were ever ungated.

**Applied:** `./deploy.sh` is now in **`deny`**, six forms (bare, `bash`-, `sh`-prefixed, each
exact and glob — the old `ask` rule was exact-match-only, so `./deploy.sh --anything` escaped it).
**`git push` stays `ask` and stays inert here, knowingly** — denying it breaks `/archive` step 5,
which pushes and asserts the push landed.

> ### ⚠️ THIS CHANGES §10b RUN 2. Read before dispatching it.
>
> Run 2's third leg is *"both windows attempt `./deploy.sh`"*. **That command is now denied in
> this harness.** You have two options and must pick one deliberately:
>
> 1. **Re-scope the leg to a decoy** — a `probe_deploy.sh` carrying `deploy.sh`'s **verbatim** lock
>    block and nothing else, run from both windows. This tests the property that matters (mutual
>    exclusion across trees) and touches no VM. **Recommended.** `scripts/check_deploy_lock.sh`
>    already extracts that block by `sed` range; reuse its approach rather than hand-copying.
> 2. **Lift the deny for the run.** Only if you specifically want to observe the real script
>    refusing. It really deploys twice to production if the lock fails, which is the thing under
>    test. Restore the deny in the same session.
>
> **Never test a `Bash` permission rule by running the real command.** It only reaches execution in
> the branch where the rule *fails*, so a negative result is the damage, not the measurement. This
> nearly happened here: the drafted probe was `./deploy.sh --help`, and **`deploy.sh` has no
> argument parsing at all** — no `case`, no `getopts`, no `$1` in 269 lines. It ignores unknown
> flags and proceeds to push, SSH, pull, `pip install` and restart both units.

---

START HERE:
1. `/metatron-code`
2. `./scripts/qa_sweep.sh` — **9 checks, ~6.6s, zero tokens.**
3. `git log --oneline -6`.
4. Plan §10 in `~/.claude/plans/jaunty-kindling-clarke.md` (hypotheses table, the three runs) and
   the Verification table beneath it. **Do not re-plan §10.** §10a is done; §10b's shape is fixed.

STATE: phases 0–2, 3a, 3b, 4, 5, 6, 8, §10a, **all of `[H8]` and `[H7]`** are done and committed.
H1, H2, H5, H6 closed. **21 defects across this plan, every one found by running, none by
reading.** Nothing is deployed; no runtime code has changed in three sessions.

---

## THE WORK — §10b, three runs. Full shape in plan §10.

**Do them in the order below, which is NOT the order they are numbered in the plan.** Run 3 needs
only a worker and delivers the more valuable of the two never-observed checks; run 2 needs a second
live window and is the most expensive thing here.

### Run 3 FIRST — deliberate failure injection. Highest value per token.

Two injections:
1. **A worker that leaves a `py_compile` error.** *Pass:* the `SubagentStop` gate blocks the "done"
   report. Check 11. Verified once against an injected fault but **never from inside a worktree**,
   which is the case H1 was about.
2. **A `/fix` whose fix lands in `routing_cloud.yaml`.** *Pass:* the worker **stops and reports
   rather than editing.** This is **check 10, and it has never been observed.** It is the single
   highest-value observation available in this whole plan.

### Run 1 — single-window happy path. The Green item is chosen and approved.

**`[DB-0813-01]` — surface a `⚠ due:` marker in the sync count line.** Mike approved it as run 1's
fuel. It stays in `## Later`; using it as rehearsal does not promote it.

- **Target:** [scripts/sync_dev_backlog.py:571-573](../../scripts/sync_dev_backlog.py#L571-L573).
  The `⚠ machine:` branch is already built there — this is a parallel branch in the same function.
- **Why this one:** `scripts/`, Green tier, no runtime, no deploy, no VM. And it has live value —
  **two items are due right now**: `[DB-0809-02]`'s week of traces (from 08-10, so ~08-17) and
  `[DB-0809-21]`'s calendar check.
- `/fix` → worker spawns into a worktree via `./scripts/new_worktree.sh` → change → `SubagentStop`
  fires → review → commit → `rm_worktree.sh`. *Watch:* does the worktree carry what the worker
  needs; does the gate run against the **worktree**; does teardown leave residue.

### Run 2 LAST — the collision. Two live windows. Read the H7 box above first.

Both windows on `tools/obligations.py`; both writing a log fragment; both filing a backlog
fragment; both attempting a deploy (**see the two options above — do not just run `./deploy.sh`**).

*Pass:* guard blocks the second commit **naming the file** (check 4, **also never observed**) ·
both log fragments survive and `build_project_log.py` orders them · both backlog fragments fold ·
second deploy refuses, **naming the first**.

**Check 4 and check 10 are the two failures this entire plan exists to make impossible, and
NEITHER HAS EVER BEEN OBSERVED.** Everything else here is confirmation.

**Check 1 ("ordinary inspection → zero prompts") is untestable in this panel** — `Bash` ask rules
do not prompt here at all, so a zero-prompt result proves nothing. Run it in **iTerm** or not at all.

---

> ### ⚠️ BUDGET — READ THIS BEFORE QUOTING ANY NUMBER
>
> **Three different quantities are all called "tokens" in this project. Do not convert between
> them.**
>
> | Figure | What it counts | Where from |
> |---|---|---|
> | **`subagent_tokens`** | one harness-emitted field, cumulative across a worker's turns | `scripts/worker_ledger.py` |
> | **raw total** | every token through the API, summed flat — ~98% cache reads, billing at 0.1× | `Stop` hook, trailing figure |
> | **weighted** | the same usage in **input-token equivalents** (reads ×0.1, writes ×2.0, output ×5) | `Stop` hook, leading figure |
>
> **§10b's ~165k budget is in `subagent_tokens`.** The `Stop` hook reports weighted and raw.
> **Reporting the hook's figure against the 165k would look like a catastrophic overrun and mean
> nothing.** Report the hook's two figures labelled as its own; compare worker figures to 165k
> separately. **Do not hand-estimate** — the `Stop` hook reports the actual automatically.

---

## BACKLOG STATE — triaged 2026-08-14, do not re-triage

`## Now` is **10 — at cap.** Anything new displaces something. Two new entries, both Mike's, both
verified against code before filing:

- **#9 `[DB-0814-01]`** — the inbox check reports "nothing found" six times a day
  (`check_interval_minutes: 240`). Instruction/config change, not a build.
- **#10 `[DB-0814-02]`** — nothing ages out stale context. **Structurally impossible today:**
  `open_threads` is a bare `list[str]` with no timestamps, so the first deliverable is a timestamp,
  not an expiry policy.

**Merged, and it is the sharpest thing in the triage:** `[DB-0809-02]` gained a **post-fix
recurrence**. `82d394b` fixed the proactive-repetition bug on **2026-08-09**; Mike reported evening
close firing 3 repetitive messages on **08-12**. The fix did not hold, or the cause is different.
**Read the 08-12 `evening_close` trace specifically** — a recurrence with a known date beats
sampling a week. Do not re-apply the ≤2-sentence cap; it was rejected deliberately.

**Two closed at triage, recorded in `archive/backlog_closed_2026-08.md` with evidence.** The
calendar-reconciliation request was **already built** (`daily_calendar_reconcile`, 05:40 daily) and
its "alert/push" half was **deliberately rejected in code** — the job comment says a crude text
match cannot support the claim that anything was missed. **Do not re-file it; it is
`[DB-0809-21]`(3) in different words.**

**Standing, from Mike 2026-08-14:** *most of what he states as a preference is him authoring the
general design, not describing a deviation.* **Default to the agent layer**; a persona-level
deviation is the exception and he will normally flag it. Promotion deletes the original.

**⚠ `DEV_BACKLOG.md` is 577 lines against its ~450 ceiling** — it was already over before this
session. Not urgent, but it is the signal that `## Later` is accumulating narrative. A `deep` pass
would be the right response, **after** §10b.

**⚠ The `⚠ machine: ×5` is still unactioned.** `mike.md:13`'s consolidated-evening-check-in
preference is flagged as possibly restating a universal rule. The flagged preference is the
reliable part; the named partner (`"Check in."` at 1.00 wording overlap) is noise. By the standing
rule above this is **design** and belongs in `synthesizer.md`, with the `mike.md` copy deleted in
the same pass. `mike.md` is VM-owned — pull it down, do not reconstruct it on the Mac.

---

## STANDING RULES

- **`./scripts/qa_sweep.sh` is 9 checks, ~6.6s, zero tokens. A green sweep is not a test** —
  `py_compile` parses without executing.
- `scripts/check_claude_md_claims.py` fails when a permission rule parses but cannot match, a hook
  points at a deleted script, or `CLAUDE.md` names a path that no longer exists. It reads a
  **backticked** path as a claim the file is live — mark a planned file without backticks.
  `scripts/check_deploy_lock.sh` runs `deploy.sh`'s **verbatim** lock block from a throwaway
  worktree and asserts one path; it trips on a restructure by design. **Re-point its `sed` range
  rather than deleting it** — H2 was two trees deploying to the same VM at once.
- `archive/PROJECT_LOG.md` is GENERATED from `archive/log/` fragments by
  `scripts/build_project_log.py`. **NEVER hand-edit it.** Each fragment owns its trailing blank line.
- Metatron defects → `.claude/backlog_inbox/`. **There is no harness backlog any more** — a harness
  defect goes in the log fragment for the session that found it.
- **NEVER use `isolation: "worktree"`** — it checks workers out from `origin/main`, not local
  `HEAD`. Use `./scripts/new_worktree.sh <slug>` and pass the ABSOLUTE PATH; a worker cannot
  persistently `cd`.
- `METATRON_COMMIT_GUARD=off` is the documented override for the known false-positive class (any
  file written by a script rather than `Edit`/`Write`, and a pathless `--amend`). **The narrowing
  is deferred, not forgotten** — revisit only when a case appears the override does not clear.
- Check `git show --stat` after committing, not just the exit code.
- **Use `git commit -F <file>` for any message containing backticks.**
- `/archive` asserts its own push. If it reports `OFFSITE FAILED`, that is real.
- **When two windows are live, one owns `/archive`**, and **diff every file before staging it.**
- **`claude config list` is not a command.** It is parsed as a prompt and costs a nested agent turn.
- **Always name the machine and use full paths** in any terminal instruction.

## CONSTRAINTS

- Open every work block with a gate: what runs, workers/model/concurrency, file manifest, token
  estimate WITH its basis. Close by reporting the **`Stop` hook's actual**, not an estimate.
- Caps: 3 workers, 10 items per verify, 1 task per `/fix`.
- COST: a cold worker costs **~50–64k `subagent_tokens`** by measurement. Delegate nothing smaller
  than the briefing.
- **ACTUALLY RUN THE THING. 21 for 21.** Static reasoning has never once caught a defect in this
  system before execution did. The H7 session added the newest: a decision table whose rows were
  coarser than the defect, which would have moved twelve permission rules when two were wrong.

MODEL: Opus. §10b is live workers, two windows, and judgement about what a failure means.
