# Next-session prompt — H7 (interactive), backlog triage, then §10b

*Written 2026-08-13 at the close of the code-not-rules build. Supersedes
`next_session_prompt_2026-08-13_throughput_10b.md`, whose tasks 3 and 4 are done and whose
`[H8].1` specification was found to be **unbuildable as written** (see below).*

**What changed since that prompt.** Its task 3 (`[H8]`, code-not-rules) is **complete and
committed** — three checks built, every one verified by injecting the fault it exists to catch.
Its task 1 (backlog triage) was **not started**. Its task 2 (`[H7]`) is unchanged and still needs
an interactive window. §10b is unchanged and still last.

**The finding that matters most, because it retires an instruction the last prompt gave.**
`[H8].1` said to grep `claude config list` for *"is not matched by file permission checks"*.
**There is no `config` subcommand** — not in the native install (2.1.226) nor the npm-global one
(2.1.170) still present at `/usr/local/bin/claude`. The CLI parses `claude config list` as a
**prompt** and spends a nested agent turn answering it. A check written to that spec would have
grepped an agent's prose for a string no tool emits, and passed forever. The mechanism was
replaced with a static shape linter that needs no CLI; the finding underneath (the `Write(path)`
deny hole) was always independently proven on a decoy probe, so it stands.
**Do not restore the `claude config list` approach.**

---

Finish the development throughput plan. Two things remain, and one of them cannot be done in a
non-interactive window.

START HERE:
1. `/metatron-code`
2. `./scripts/qa_sweep.sh` — **now 9 checks, ~6.6s, zero tokens.** Two are new; if either fails,
   read its output before anything else, because both encode invariants that were violated
   silently before they existed.
3. Read `HARNESS_BACKLOG.md` — `[H8]` is closed with evidence; `[H7]` and the commit-guard
   narrowing remain open, each for a stated reason.
4. `git log --oneline -8`.
5. Plan §10 in `~/.claude/plans/jaunty-kindling-clarke.md` (hypotheses table, the three runs) and
   the Verification table beneath it. **Do not re-plan §10.** §10a is done; §10b's shape is fixed.

STATE: phases 0–2, 3a, 3b, 4, 5, 6, 8, §10a and **all of `[H8]`** are done and committed. H1, H2,
H5, H6 closed. **20 defects across this plan, every one found by running, none by reading** — the
four newest were in the checks built to prevent defects, and the worst was a **false pass**: the
deploy-lock check first reported `ok` on two empty strings that compared equal, because
`BASH_SOURCE` cannot be assigned and `set -u` aborted the eval on both sides identically.
**A guard that fails identically on both sides looks like agreement.**

---

## TASKS, in order

### 1. `[H7]` — INTERACTIVE WINDOW ONLY. Do this first; it gates run 2.

**This cannot be tested from a non-interactive session.** `ask` auto-approves there, so a missing
prompt is the expected null result whether the mechanism works or not. Running the test here
proves nothing and burns the window.

The whole Red tier — `./deploy.sh`, `git push`, agent-file and
`router/persona/scheduler/spend_guard` edits — is **ungated in a non-interactive session**, which
is the one place nobody is watching. A plain-CLI `claude -p` session fails the opposite way and
auto-DENIES. No settings edit is needed to test: `Bash(git push *)` is already an `ask` rule.

**Run these two, in order, and record which prompted.**

**Test A — iTerm (the clean control).** In iTerm:

```
cd /Users/md-homefolder/Desktop/multi-model-mcp && claude
```

Plain `claude` (no `-p`) opens the interactive REPL. Then send:

```
Run: git push --dry-run origin main
```

`--dry-run` does the full negotiation with GitHub and writes nothing — no commits move, no branch
updates. Watch for a permission prompt **before** it runs.

**Test B — the VS Code extension chat panel** (not its integrated terminal — the terminal is the
CLI again, and the extension is the harness actually under test). Same request, typed by a human.

**Why iTerm rather than VS Code's terminal:** the CLI detects it is running inside VS Code and
auto-enables the IDE integration, which routes some UI through the extension — muddying the exact
boundary being measured.

**How the result resolves the decision:**

| iTerm | VS Code panel | Meaning | Decision |
|---|---|---|---|
| Prompt | Prompt | defect is **unattended sessions only** | leave `ask`; treat unattended runs as the exception |
| Prompt | No prompt | defect is **the extension specifically** | move `./deploy.sh` + `git push` to `deny`, or stop doing Red work in the panel |
| No prompt | No prompt | `ask` is **dead everywhere** | `deny` is the only real gate; the Red tier must move |

**This is Mike's decision, not a fix to apply.** Record the outcome in `HARNESS_BACKLOG.md` § H7
and close it. **§10b run 2 must not proceed until this is settled** — that leg attempts
`./deploy.sh` from both windows, and per H7 it would really deploy to the VM, ungated, twice.

### 2. `/backlog` — a triage pass. (Carried unchanged; still not started.)

4 inbox · 8 now · 32 later. Triage the Inbox — all four entries are Metatron runtime items
(scheduler repetition, stale-context ageing, mailbox ticketing, silencing empty inbox reports).
**`[H5]` needs no action**: the Inbox note already records it closed in `HARNESS_BACKLOG.md`.

**Come out of this with the Green-tier item run 1 will use.** None of the eight `## Now` items is
trivial — they are all live runtime defects — so **hunt `## Later` for something genuinely small
in `tools/` or `scripts/`.** The point is exercising the loop, not the fix.

### 3. §10b — THE TWO-WINDOW REHEARSAL. Full shape in plan §10.

Three runs: (1) single-window happy path through `/fix` on the Green item from task 2;
(2) **THE COLLISION** — two windows on `tools/obligations.py`, both writing log fragments, both
filing backlog fragments, both attempting `./deploy.sh`; (3) deliberate failure injection — a
worker leaving a `py_compile` error, and a `/fix` whose fix lands in `routing_cloud.yaml`.

**Checks 4 and 10 are the two failures this whole plan exists to make impossible and NEITHER HAS
EVER BEEN OBSERVED.** Check 10 needs only a worker — run 3 delivers it without a second window,
so it is the highest value per token here. Check 4 needs two live windows and cannot be faked.
**Check 1 ("ordinary inspection → zero prompts") is untestable in a non-interactive session** —
run it in the interactive window during task 1, or not at all.

> ### ⚠️ BUDGET — READ THIS BEFORE QUOTING ANY NUMBER
>
> **Three different quantities are all called "tokens" in this project, and comparing two of
> them is what produced the original 7× miss. Do not convert between them.**
>
> | Figure | What it counts | Where from |
> |---|---|---|
> | **`subagent_tokens`** | one harness-emitted field, cumulative across a worker's turns | `scripts/worker_ledger.py` |
> | **raw total** | every token through the API, summed flat — ~98% cache reads, which bill at 0.1× | `Stop` hook, trailing figure |
> | **weighted** | the same usage in **input-token equivalents** (reads ×0.1, writes ×2.0, output ×5) — the cost-shaped number | `Stop` hook, leading figure |
>
> **§10b's "~165k" budget is in `subagent_tokens` units.** The `Stop` hook reports weighted and
> raw. **Reporting the hook's figure against the 165k would look like a catastrophic overrun and
> mean nothing.** Report the hook's two figures labelled as its own, and compare the worker
> figures to 165k separately. For calibration: the session that wrote this prompt measured
> **3,423k weighted / 23,934k raw over 87 requests** — roughly $17 at Opus 5's input rate.
>
> A model estimating its own context growth is not measuring the billed total. **Do not
> hand-estimate; the `Stop` hook now reports the actual automatically at the end of every turn.**

### 4. RETIRE `HARNESS_BACKLOG.md`.

`[H8]` is closed. Task 1 closes `[H7]`. The commit-guard narrowing stays deferred on the record as
ergonomics — revisit only when a case appears the override does not clear. Once H7 lands, the file
has done its job and should not outlive this build.

---

## STANDING RULES

- **`./scripts/qa_sweep.sh` is 9 checks, ~6.6s, zero tokens. A green sweep is not a test** —
  `py_compile` parses without executing.
- **The two new checks and what trips them:**
  `scripts/check_claude_md_claims.py` fails when a permission rule parses but cannot match, a hook
  points at a deleted script, or CLAUDE.md names a path that no longer exists. It reads a
  **backticked** path as a claim the file is live — mark a planned file without backticks (see the
  `config/frameworks.md` note in CLAUDE.md, which had never existed in any commit).
  `scripts/check_deploy_lock.sh` runs `deploy.sh`'s **verbatim** lock block from a throwaway
  worktree and asserts one path; it trips on a restructure by design. **Re-point its `sed` range
  rather than deleting it** — H2 was two trees deploying to the same VM at once.
- `archive/PROJECT_LOG.md` is GENERATED from `archive/log/` fragments by
  `scripts/build_project_log.py`. **NEVER hand-edit it.** Each fragment owns its trailing blank line.
- Harness defects → `HARNESS_BACKLOG.md`. Metatron defects → `.claude/backlog_inbox/`.
- **NEVER use `isolation: "worktree"`** — it checks workers out from `origin/main`, not local
  `HEAD`. Use `./scripts/new_worktree.sh <slug>` and pass the ABSOLUTE PATH; a worker cannot
  persistently `cd`.
- `METATRON_COMMIT_GUARD=off` is the documented override for the known false-positive class (any
  file written by a script rather than `Edit`/`Write`, and a pathless `--amend`).
- Check `git show --stat` after committing, not just the exit code.
- **Use `git commit -F <file>` for any message containing backticks.**
- `/archive` asserts its own push. If it reports `OFFSITE FAILED`, that is real.
- **When two windows are live, one owns `/archive`**, and **diff every file before staging it**.
- **`claude config list` is not a command.** It is parsed as a prompt and costs a nested agent
  turn. The listed subcommands are `agents auth auto-mode doctor gateway import install mcp
  plugin project setup-token ultrareview update`.
- **Always name the machine and use full paths** in any terminal instruction.

## CONSTRAINTS

- Open every work block with a gate: what runs, workers/model/concurrency, file manifest, token
  estimate WITH its basis. Close by reporting the **`Stop` hook's actual**, not an estimate.
- Caps: 3 workers, 10 items per verify, 1 task per `/fix`.
- COST: a cold worker costs **~50–64k `subagent_tokens`** by measurement. Delegate nothing smaller
  than the briefing.
- **ACTUALLY RUN THE THING. 20 for 20.** Static reasoning has never once caught a defect in this
  system before execution did — including four times in the session that wrote this prompt, all
  four inside the checks built to catch defects, one of them a check that reported success while
  measuring nothing.

MODEL: Opus. §10b is live workers, two windows, and judgement about what a failure means.
