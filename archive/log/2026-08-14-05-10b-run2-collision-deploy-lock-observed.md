### 2026-08-14 (§10b run 2 — the two-window collision; the deploy lock observed refusing)

The last run in the development-throughput plan. Window A is this session; window B was opened
from a terminal and briefed as **ordinary work, not a test** — a worker told it is being tested
stops for the wrong reason and proves nothing.

**The unfinished step from the previous session, done first.** `[DB-0809-02]` now carries
`due: 2026-08-17`, and the marker was verified on both sides of its boundary rather than on the
day it fires: `--today 2026-08-16` prints no clause, `--today 2026-08-17` names it.

**Defect 24, and it came out of running the verification rather than reading it.** The first
`--today 2026-08-17` run named **two** items. `DB-0813-01` — the item that *built* the feature —
matched its own body text, which read *"Remaining: add `due: 2026-08-17` to `[DB-0809-02]`"*.
`DUE_RE`'s colon anchor (`scripts/sync_dev_backlog.py:149-155`) was chosen so a prose date
(*"due 2026-08-11, do not check before then"*) would not match, and it does that correctly. What
it cannot distinguish is prose that **quotes the marker verbatim** — which is what any item
documenting the convention necessarily contains.

**No code change was made, deliberately.** The obvious fix — ignore markers inside backticks —
is worse than the bug: every real marker is backticked too, so it would disable the feature
outright. This is the standing *"ask what the fix costs in the failure direction"* rule landing
on a live case for the second time in two sessions. The false positive was self-limiting — it
existed only while an item was open *about* the convention — and closing `[DB-0813-01]` removed
it. The class is recorded in `archive/backlog_closed_2026-08.md` so the next occurrence is
recognised rather than re-diagnosed; an item that must quote the marker should drop the colon.

`[DB-0813-01]` closed on the tag landing (`## Later` 32 → 31).

**Check 4 — OBSERVED. It was the last unobserved check in the plan, and the plan describes it
backwards.**

A wrote a comment on `_new_id`; B then wrote one on `_find`; A staged. The guard refused, naming
`tools/obligations.py`, and left nothing staged. Two corrections fall out, both found by running:

1. **It fires at `git add`, not at `git commit`.** The plan's wording is *"B stages and commits →
   guard blocks"*. Staging was enough — the index never got dirty. That is better than specified,
   but a session watching for the block at commit time would conclude the guard had not fired.
2. **It blocks the FIRST writer, not the second.** The plan reads *"Window A edits it; window B
   edits it; **B** stages and commits → guard blocks."* That is the wrong window. The guard keys
   on *"a file I wrote changed underneath me"*, so B — holding the freshest hash — committed with
   no refusal at all (`688b53f`), while A held the stale hash and was stopped. The asymmetry was
   predicted in B's brief and confirmed. **A session following the plan literally would watch B,
   see it sail through, and record a false negative on the one check the whole plan exists for.**

Neither is a defect in `hook_commit_guard.py`; both are defects in the description of it. No code
was changed. The same imprecision is live in `CLAUDE.md` § Deploy safety rule 4, which says the
guard *"blocks a commit when one changed underneath it"* — loose on both counts. **Not corrected
in this session**: `CLAUDE.md` was carrying a parallel window's uncommitted edit throughout, and
adding lines on top of it would have rebuilt the 2026-08-09 shape while writing up the check that
catches it. Owed as a two-line edit once that diff lands.

**Check 5 — the override — was deliberately NOT taken at the moment it would have been easiest.**
When the guard blocked A, `tools/obligations.py` still held B's five uncommitted lines. Overriding
then would have swept B's work into A's commit — precisely the damage the guard had just
prevented. **Passing a test by causing the failure it tests for is not a pass.** The override was
taken only after `688b53f` put B's lines safely in history, at which point the guard's complaint
was the documented false-positive class and the override was the correct call.

**Check 13 — pass.** Both windows wrote fragments to `archive/log/` concurrently; both survived
and `build_project_log.py` ordered them newest-first (`-06` above `-05`). This is the append
collision having been designed out rather than handled: neither window ever opened the generated
file. Both backlog fragments folded on the next sync (`2 new`).

**Check 8 — observed, twice, and the second way is the one that mattered.**

`./deploy.sh` is in `deny` and stayed there. The probe is `scripts/probe_deploy.sh`, which
extracts deploy.sh's lock block **verbatim at run time** by `sed` range — the same approach as
`scripts/check_deploy_lock.sh`, and for the same reason: a hand-copied lock keeps passing after
someone edits the original, which is precisely the defect that made the first lock probe
worthless on 2026-08-13.

- Two concurrent processes, main tree: the second **refused**, naming holder PID 4599, exit 1,
  nothing pushed.
- Main-tree holder vs **a detached worktree**: the worktree resolved to the main tree's
  `.git/.deploy.lock` and was refused naming the holder. This is H2's fixed state observed live
  rather than inferred — `check_deploy_lock.sh` asserts the two trees compute the *same path*,
  which does not by itself establish that the lock *excludes* a second holder. Path agreement and
  mutual exclusion are different claims and the sweep only ever checked the first.

The probe carries a hard abort if its `sed` range ever captures a line matching
`git push|gcloud|ssh |systemctl|pip install`. Without it, widening the range — or restructuring
`deploy.sh` so the range runs long — would silently `eval` a real deploy, which is the exact
shape of failure the decoy exists to prevent. `deploy.sh` has **no argument parsing at all** in
269 lines, so there is no harmless flag; the decoy is the only safe way to exercise this.

**Deviation, stated rather than buried:** check 8 was observed with two concurrent *processes*,
not two Claude windows. The lock is process-level `mkdir`; a second window exercises the identical
code path. The cross-worktree leg is the stronger evidence and it is genuine.

**A permission rule fired correctly mid-run and is worth recording as a positive.** A `rm -rf` in
the worktree cleanup was **denied outright** — check 3's rule doing its job against this session's
own convenience. Re-run without it.

**Housekeeping observed, not acted on:** `CLAUDE.md` was modified in the working tree throughout
by a parallel window (the `HARNESS_BACKLOG` condensation). It was never staged. Mike confirmed
that window was in plan mode, so the diff was static for the duration.

**What window B found that window A had got wrong.** B's brief — written by A — said `_find`'s
`None` is what *"open/close/reopen"* branch on. `open_obligation` never calls `_find`; it takes no
id and runs its own near-duplicate scan over `what`. B opened the code instead of trusting the
instruction and wrote the comment naming the two real callers. **The premise-checking rule caught
its author**, which is the most useful direction for it to fire in, and it is the reason B was
briefed as ordinary work rather than as a test.

B also recorded a staging hazard worth carrying: `git add -p` is unavailable in this harness, and
`git apply --cached --unidiff-zero` **printed `APPLIED OK` while placing the hunk inside a loop
body**, staging syntactically invalid Python. Only diffing the index caught it. The working tree
was never wrong. Treat `--unidiff-zero` as unsafe for splitting a hunk into the index; build the
blob from `HEAD` and `hash-object`/`update-index` instead.

**Also found, not fixed:** the inbox fold pastes fragment bodies into `## Inbox` back-to-back with
no separator, so two notes filed in one cycle run together as one block of prose. Cosmetic, reads
fine, below the filing bar — noted only so the next reader knows it is the fold and not a lost
delimiter. And B's own finding is a real one: `context_block()` sorts by
`str(it.get("due") or "9999")`, so a vague `due` phrase sorts *after* the no-due sentinel and is
the first thing dropped from the context block — while `OPEN_OBLIGATION_SCHEMA` explicitly invites
that phrasing. It is in the Inbox as user-noticeable.

`qa_sweep.sh` 9/9 throughout. **Not deployed — no runtime code changed.**

