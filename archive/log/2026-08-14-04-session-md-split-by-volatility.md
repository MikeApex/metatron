### 2026-08-14 (`SESSION.md` split by volatility, not topic)

Mike asked whether `/archive`'s `SESSION.md` step could be cheaper — batch edits, or a staleness
pass rather than waiting for the 200-line ceiling. The first answer given was generic
(diff-editing, a periodic sweep, a cheaper model) and was produced **without reading the file**.
Reading it changed the diagnosis, so the delivered work is not what was first proposed.

**The measurement that reframed it.** `SESSION.md` had sat at 195–205 lines for its last twenty
commits (08-10 → 08-14). It was not drifting toward the ceiling, it was **pinned to it**: every
close-out was a zero-sum negotiation where a new line had to argue an old line out. That is the
cost, and it is paid regardless of how much actually changed that session. A "wait until it
exceeds 200" sweep was therefore moot — a pass already ran every time.

**Cause: the file mixed volatility tiers.** Roughly 82 of 200 lines were static reference —
Quick start, Model IDs, the lookup table, Read-these-first — interleaved with genuinely hot
state, so every run re-read and re-decided all of it to change perhaps 40 lines.

**What was done.** Quick start's four run commands moved to `docs/INFRASTRUCTURE.md` § Local dev
mode (the pmset/launchd and `DEPLOYMENT_MODE` halves were already there verbatim — duplicates,
not a move); the `## Useful context` table collapsed to a pointer at `CODEBASE_INDEX.md`, which
already indexed eleven of its twelve rows; the handoff paragraph lost the permission-matcher
findings and the token rule, both of which `CLAUDE.md` § Change tiers already carried word for
word. **200 → 178 lines, volatile part 105.**

**Options rejected, with the reason:**

- **Moving Model IDs to `docs/CONVENTIONS.md` — killed.** `CONVENTIONS.md:143` deliberately
  points *at* `SESSION.md` for the live values, on the stated ground that a second copy goes
  stale. Reversing a documented decision silently is the failure this project keeps paying for.
  Its premise is nonetheless false — the table reads *updated 2026-07-27*, so the primer is not
  in fact rewriting it every session. Raised for Mike, not acted on.
- **A deferred staleness sweep gated on a trigger — rejected.** That is exactly the mechanism
  that failed for `DEV_BACKLOG.md`, which grew 197 → 1,658 lines *while three sweeps ran*.
  Structure that prevents staleness beats a sweep that removes it.
- **Inline `[STALE]` tagging during the session — rejected.** Needs mid-session discipline; this
  project's own principle is that a rule you have to remember is not a control.
- **Routing the edit to a cheaper model — rejected.** Deciding what is superseded *is* the
  judgement. The saving comes from having less to judge.
- **A tenth `qa_sweep.sh` check — rejected** in favour of extending
  `check_claude_md_claims.py`, which already owned line ceilings.

**Believed true earlier, wrong:** that the 200-line ceiling measured the right thing. It cannot
distinguish 120 static lines from 80 live ones, so it pressures a session to cut live state —
the valuable part. The new volatile budget (handoff + `## Current state` + `## Recent sessions`)
was set to **120 against a measured 105**, deliberately not to the measured value: a check that
warns on the day it ships is one a reader learns to skip, which is why `check_agent_tools.py`
was kept out of the quality stream.

**Also found, not fixed:** `DEV_BACKLOG.md:133` says `[DB-0810-12]` has had no occurrence and
the hold stands; `SESSION.md` says it is unblocked with four. The primer is newer and is the
only copy — the backlog item needs the update, but rewriting a live runtime status on one
session's reading is not this step's job. And `.claude/commands/archive.md` is 140 lines against
a ~100 ceiling; it was 124 before this session and gained 16 here.

Ceiling warnings are invisible in a normal `qa_sweep.sh` run — `run_check` prints a passing
check's output only under `--verbose` — so `/archive` § 3 now names
`python3 scripts/check_claude_md_claims.py` directly rather than claiming the sweep reports it.

A parallel window was live in this tree throughout (`44c3cf9`, then `9316284`, `7d7e349`,
`ab1f71e`) and its uncommitted `CLAUDE.md` edit was visible in `git diff` mid-session. Nothing
of it was staged; it committed on its own. Verified before committing that those commits never
touched `SESSION.md`, so this session's restructure reverted none of their work.

`qa_sweep.sh` 9/9. **Not deployed — docs, one command file and one check script.**

