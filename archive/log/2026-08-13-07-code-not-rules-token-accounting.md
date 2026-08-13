### 2026-08-13 (code-not-rules: token accounting, claims smoke, deploy-lock invariant)

`[H8]` built and closed in full — the three rules the throughput build enforced by memory now
have scripts. `qa_sweep.sh` goes 7 → 9 checks, ~6.0s → ~6.6s, still zero model tokens. No runtime
code, nothing deployed. **Four defects, all four inside the checks built to prevent defects, all
four found by running them.**

**`[H8].1` could not be built as specified, and the specification was the defect.** It said to
grep `claude config list` for *"is not matched by file permission checks"*. **There is no
`config` subcommand** — not in the native install (2.1.226) nor the npm-global 2.1.170 still at
`/usr/local/bin/claude`. The CLI parses `claude config list` as a **prompt** and spends a nested
agent turn answering it; that is how this was found, by running it and getting a chat reply.
A check written to that spec would have grepped an agent's prose for a string no tool emits and
passed forever — the same shape as the H5 detector whose silence looked like success.
**Where the string came from is unresolved** and no longer matters: the finding underneath (the
`Write(path)` deny hole leaving Tier-0 `constitution.md` reachable) was proven on a decoy probe,
not on that string. Mechanism replaced with a static shape linter over `settings.json` that needs
no CLI. **Rejected: restoring the CLI approach on a hypothetical older binary** — neither binary
present has it, and a check that depends on an absent tool version is worse than none.

**Merged `[H8].1` with `[DB-0809-11]`** ("docs record values the system changes underneath them
and nothing checks"), as the harness backlog instructed — one script, not two.
`scripts/check_claude_md_claims.py` asserts permission-rule liveness (no `Write(path)`-class rule
that parses and never matches; every bare-executable `Bash` rule has a ` *` sibling; the Denied
tier still names constitution/persona/`.env`), that every hook target exists, and that every
backticked path in `CLAUDE.md` exists. Line ceilings **warn** rather than fail, matching how the
prose states them. All five fault classes verified by injection in an isolated tree, exit codes
checked in both directions.

**Two live defects it found on first run.** `config/frameworks.md` — referenced in `CLAUDE.md`
as holding "the theoretical literature" — **has never existed in any commit**. Marked *planned,
not present* rather than deleted, per this repo's own rule that a named thing is a specification;
the backticks were removed because the check reads a backticked path as a claim the file is live,
and that convention is now documented at the site. And `.claude/show_phase_progress.py`, a `Stop`
hook in `settings.local.json`, reads a `STATUS.md` deleted months ago — a silent no-op on every
turn since. Left for Mike; it is his personal settings file.

**Three of its first six findings were the script's own bugs** — absolute hook paths mangled by a
`lstrip("./")`, a dated filename template read as a real path, and VM-only persona paths (absent
on the Mac **by design**) reported as missing. The last is the instructive one: a report whose
loudest finding is correct behaviour is a report nobody reads twice.

**`[H8].2` — session token accounting as a `Stop` hook — and two things a naive version gets
wrong.** First, **dedup by `requestId` is load-bearing, not tidiness**: the transcript writes one
assistant record per content block, so a turn with text plus a tool call carries the *same* usage
object twice. Measured on this session's own JSONL: 41 records against 25 real requests, and a
flat per-record sum reported 3,496,735 tokens against a true 2,006,891 — **1.74× over**. That is
the `worker_ledger.py` failure class exactly, so it was checked rather than assumed (19 of 19
duplicate pairs confirmed byte-identical). Second, **a raw sum of the four billed fields is not a
usable number**: 98% of it is cache *reads*, billed at 0.1×. Reporting one would have reproduced
the very miss `[H8].2` exists to fix, in a new costume. The hook now reports **weighted
input-token equivalents** — reads ×0.1, writes ×1.25/×2.0 chosen per record from the
`cache_creation` TTL breakdown, output ×5 — with the raw sum trailing so the gap stays visible.
**Ratios, not dollar prices, deliberately**: ratios are a property of the caching design, prices
have a short half-life (`CLAUDE.md`'s standing rule, applied one layer up).

**A third unit was found while checking this, and it retires a comparison the next-session prompt
would have made.** `worker_ledger.py` reports `subagent_tokens`, a single harness-emitted field.
**§10b's "corrected budget of ~165k" is in those units and cannot be compared to the hook's
figure.** Three quantities are all called "tokens" here; the corrected prompt now tabulates them
and forbids conversion.

**`[H8].3` — the deploy-lock invariant — produced the worst defect of the day: a false pass.**
The check executes `deploy.sh`'s **verbatim** lock block (extracted by `sed` at run time, so a
later "simplification" trips it) from a throwaway `--detach` worktree and from the main tree, and
asserts one path. The first version pointed the block at each copy by assigning `BASH_SOURCE`.
**Bash resets `BASH_SOURCE` on assignment**, so `${BASH_SOURCE[0]}` was an unset array element,
`set -u` aborted the eval mid-subshell, both sides returned the empty string — and two empty
strings compare equal, so it printed `ok`. **A guard that fails identically on both sides looks
like agreement.** Fixed by substituting the path textually and asserting non-empty on each side
separately. Then made to speak: both regression shapes were injected — dropping `--git-common-dir`
outright, and the subtler one that keeps that line while making the resulting path
worktree-local — and each was caught with a distinct message. `deploy.sh` restored byte-clean.

**Estimate vs actual, which is the point of the whole item.** Opening gate estimated ~110k;
the hook measured **3,423k weighted / 23,934k raw over 87 requests** (~$17 at Opus 5 input
rates). Not 30× wrong about the work — **wrong about the quantity**: a model estimating its own
context growth is measuring what it can feel, while the bill is driven by re-reading that context
on every request, which compounds. That is exactly what stops being guesswork now.

**Deliberately not done:** the backlog triage (task 1 of the previous prompt) — untouched, and
carried forward. **`[H7]` remains open and cannot be closed from here**: `ask` auto-approves in a
non-interactive session, so testing it here returns the expected null result whether the mechanism
works or not. The successor prompt makes it task 1 and specifies iTerm (clean control) before the
VS Code panel (the harness actually under test), with the decision table for each outcome.

Successor prompt: `archive/plans/next_session_prompt_2026-08-13b_throughput_10b_and_backlog.md`.

