# Next-session prompt — §10b rehearsal + the code-not-rules audit

*Written 2026-08-13 at the close of the throughput build. Paste the block below as the
opening message of the next session. Everything above the rule is context for Mike, not
for the next session.*

**Why this exists:** §10b was deferred with its budget corrected, not skipped for lack of
time. The plan's ~40–60k estimate rested on the flat-32k worker model that was retired the
same day; measured medians put it near 165k. That is a decision worth taking deliberately at
the start of a session rather than discovering two workers in.

---

Finish the development throughput plan. §10b is the only phase left, plus a code-not-rules
audit Mike asked for and three open harness items.

START HERE:
1. `/metatron-code`
2. Read `HARNESS_BACKLOG.md` in full — three open items (H7, the commit-guard narrowing, H8)
   and a reconciliation-status block at the top stating why each is open. Its contract is that
   it is reconciled within the build that opened it; that build is this one.
3. `git log --oneline -10` — the last session closed five harness defects across two windows.
4. Read `~/.claude/plans/jaunty-kindling-clarke.md` §10 (hypotheses table, the three runs) and
   the Verification table beneath it. **Do not re-plan §10.** §10a is done; §10b's shape is fixed.

STATE: phases 0–2, 3a, 3b, 4, 5, 6, 8 and §10a are done and committed. **H1, H2, H5 and H6 are
all closed** — H2 verified live by running the lock block from a real worktree and from the main
tree and confirming one path, then confirming mutual exclusion. `defaultMode: auto` never took
effect and is gone, replaced by an explicit `allow` list that the matcher actually honours.
**16 defects across this plan, every one found by running, none by reading.** The two most
recent: `worker_ledger.py` reporting 3 worker runs out of a real 13 — a clean table, sensible
aggregates, all wrong, because the records were never where the regex was looking; and the H5
fallback detector staying silent for a reason that was not success.

TASKS, in order. 1 is the main event; 2 is what Mike asked for at the close.

1. **§10b — THE TWO-WINDOW REHEARSAL.** Full shape in plan §10.
   **Budget ~165k, not the plan's 40–60k.** Basis: measured medians from
   `python3 scripts/worker_ledger.py` — sonnet 58,879 (n=1), inherited median 64,081 (n=8),
   floor 30,023. Three cold workers. The plan's figure assumed a flat 32k that was retired
   2026-08-13. Do not re-derive this from the plan text; it is stale there.
   Three runs: (1) single-window happy path through `/fix`; (2) **THE COLLISION** — two windows
   on `tools/obligations.py`, both writing log fragments, both filing backlog fragments, both
   attempting `./deploy.sh`; (3) deliberate failure injection — a worker leaving a `py_compile`
   error, and a `/fix` whose fix lands in `routing_cloud.yaml`.
   **Checks 4 and 10 are the two failures this whole plan exists to make impossible and NEITHER
   HAS EVER BEEN OBSERVED.** That is the point of §10b. Check 10 needs only a worker — run 3
   delivers it without a second window. Check 4 needs two live windows and cannot be faked.
   Use a throwaway Green-tier item so a failure costs nothing.

   **Two constraints the plan does not carry:**
   - **Check 1 ("ordinary inspection → zero prompts") is untestable in a non-interactive
     session.** It moved from blocked-by-H5 to blocked-by-H7: `ask` resolves to ALLOW in the
     VS Code / Agent-SDK harness, so nothing prompts and the count proves nothing. Run it in an
     **interactive** window or not at all.
   - **Run 2's deploy leg is now worth running** — H2 is fixed and verified, so it tests a live
     mechanism rather than a known defect. But see H7: `./deploy.sh` is **ungated** in a
     non-interactive session. Nothing will stop a real deploy to the VM.

2. **THE CODE-NOT-RULES AUDIT** — Mike's closing question, already answered in outline as
   `[H8]`. Three rules this build enforced by memory that a script should enforce instead:
   permission-rule liveness into `qa_sweep.sh` (**highest value** — the `Write` hole was found
   incidentally, and `claude config list` had been printing the warning to nobody for five
   rules); session token accounting as a `Stop` hook (the estimate was 45–60k, the actual 438k);
   and the deploy-lock invariant as a sweep check (nothing stops a future session "simplifying"
   `--git-common-dir` back, which is exactly how H2 arrived).
   **Build item 1 together with `[DB-0809-11]`** — it is the harness-side instance of the same
   thing, and its stated fix is a smoke script running `CLAUDE.md`'s executable claims. Build
   them as one thing, not twice.
   **Explicitly rejected, do not revive:** hunk attribution for shared-tree commits. That is the
   fingerprinting design the Chorus round killed for a fatal false negative on a shared tree.
   The mechanism for that problem exists and is `scripts/new_worktree.sh`.

3. **H7 — the open decision.** Whether `./deploy.sh` and `git push` move from `ask` to `deny`
   (lifted per deploy). **Test first, decide second:** does an *interactive* VS Code session
   honour `ask`? If it does, the defect is scoped to unattended sessions and the decision is
   much narrower than it looks. This is a decision for Mike, not a fix to apply.

4. **RETIRE `HARNESS_BACKLOG.md`.** Every item closes or is explicitly and datedly deferred
   before this plan is called done. It did not retire on 2026-08-13 and said so rather than
   closing three live items to make the rule come out even. A harness backlog that outlives its
   build becomes a second permanent bin, which is what it exists to avoid.

STANDING RULES:
- `archive/PROJECT_LOG.md` is GENERATED from `archive/log/` fragments. NEVER hand-edit it.
  Each fragment owns its own trailing blank line.
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
  word out of a commit message this session and the sentence lost its verb.
- `/archive` now asserts its own push. If it reports `OFFSITE FAILED`, that is real.
- **When two windows are live, one owns `/archive`.** On 2026-08-13 both reached it; the second
  stopped at step 1 rather than replacing a `SESSION.md` the first was rewriting. Step 0 of
  `/archive` is that check — obey it.

CONSTRAINTS:
- Open every work block with a gate: what runs, workers/model/concurrency, file manifest, token
  estimate WITH its basis. Close by reporting actual vs estimate.
- Caps: 3 workers, 10 items per verify, 1 task per `/fix`.
- COST: a cold worker costs **~50–64k** by measurement, not the 32k this plan assumed for most
  of its life. `python3 scripts/worker_ledger.py` reports real per-model medians for free.
  Delegate nothing smaller than the briefing.
- **ACTUALLY RUN THE THING. 16 for 16.** Static reasoning has never once caught a defect in this
  system before execution did — including twice in the session that wrote this prompt, where the
  regex looked right and the detector's silence looked like success.

MODEL: Opus. §10b is live workers, two windows, and judgement about what a failure means.
