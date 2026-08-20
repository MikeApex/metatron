---
paths:
  - "scripts/**"
  - "deploy.sh"
  - ".claude/settings.json"
  - ".claude/hooks/**"
---

# Deploy and harness scripts

Relocated from `CLAUDE.md` on 2026-08-14, in full.

**`./deploy.sh` is Denied-tier** in `.claude/settings.json` — blocked, and lifted only by explicit
decision (Mike, 2026-08-14). It was the only ungated irreversible action: it pushes, SSHs the VM,
pulls, installs and restarts both units. The Denied row of the change-tier table is in `CLAUDE.md`
and stays there; this file is what you need once you are actually editing the scripts.

---

## Four rules bought with real incidents

1. **`py_compile` cannot catch a `NameError`.** A stale `_SCHEDULER_CONFIG` reference passed
   compile and then crash-looped the scheduler after deploy. When you remove a symbol, grep for
   it, and **actually run the daemon** — not just import it.
2. **Never add a config key before the code that gates it is deployed.** `interval_minutes: 30`
   shipped without its gate stack is a check-in every thirty minutes, on a live user. Config and
   its guard deploy together, guard first.
3. **`daemon-reload` before the deploy, not after** — `deploy.sh` restarts services, so an
   edited-but-unreloaded unit applies at the worst possible moment.
4. **Staging by filename does not protect you from another session's lines *inside* that file.
   `git diff <file>` before you stage it.** Two chats often run against this one working tree, and
   `git add <path>` stages the file's whole current content — including edits another session has
   not committed yet. On 2026-08-09 a commit titled "Obligation store and passed-event
   reconciliation" carried a second session's `send_email` grant transfer in `routing*.yaml`, and
   `./deploy.sh` put it on the VM: the grant went live while the agent instructions and Coordinator
   routing that governed it sat uncommitted, so email sending was **dead in production**. Staging
   by explicit filename was the discipline in force and it did not help; the check was at file
   granularity against a line-granularity collision. Diff every file before staging it, or use
   `git add -p`. When two sessions are live, also: one owns the deploy, and one runs `/archive` —
   see `.claude/commands/backlog.md` § attack.

> **Rule 4's sharpest form: untracked files are the landmines; modified tracked files are not.**
> A tracked file already exists on the VM, so a `git pull` merely updates it. An **untracked** one
> does not exist there at all — so committing a tracked file that *imports* an untracked one
> deploys an `ImportError`. On 2026-08-20 `core/orchestrator.py` held two sessions' uncommitted
> work and **each half imported a module the other had not committed** (`core/attachments.py` at
> module level, `tools/intake.py` inside `register_tools()`); whichever committed the file wholesale
> first would have taken the app down. Fix when the regions are disjoint: stage *only your own
> hunks*, then **export `HEAD` to a clean directory and import it there** — the only check that
> proves what the VM will actually pull. Pushing first is the kinder order; it leaves the other
> session able to stage wholesale. Method: `archive/PROJECT_LOG.md` § 2026-08-20.

> **Rule 4 is now also enforced mechanically** by `scripts/hook_commit_guard.py`, which hashes each
> file this session writes and blocks when one changed underneath it. Two things the old wording
> *"blocks a commit"* got loose, both observed 2026-08-14: it fires at **stage time** — `git add`
> as well as `git commit`/`git stash` — so a session watching only the commit watches the wrong
> window; and it blocks the **first** writer, not the sweeper. The later writer re-hashed the file
> after both sets of lines had landed, so it stages clean and commits, while the earlier session is
> stopped. The rule above still stands: the guard covers *uncommitted* overlap on the main tree,
> not a worktree merge or a file a script wrote. Override with `METATRON_COMMIT_GUARD=off`.

---

## Probing a permission rule

**`ask` is honoured for `Edit` rules and ignored for `Bash` ones** (measured in both harnesses by
hand, 2026-08-14). The split is by **tool family**, not by whether a session is interactive — an
earlier note said the latter and was too broad. `deny` is enforced for both families.

**`git push` stays Red and stays inert here, knowingly:** denying it would break `/archive`'s
push-and-assert step every run, for a gate on a private-repo push.

Two consequences worth carrying:

- **Anything that must never happen unattended belongs in the Denied row.**
- **Probe a permission rule per tool family, never once.** This harness has produced two
  tool-family matcher splits (`Edit` vs `Write`, `Edit` vs `Bash`), and in both the working family
  made the broken one look fine.

**Never test a `Bash` permission rule by running the real command.** The test only reaches
execution in the branch where the rule fails, so a negative result *is* the damage. Use an inert
decoy with the same rule shape.

---

## The standing rule on new machinery

> **No new standing harness script or hook without naming what it retires, or the build that will
> retire it.**

Adopted 2026-08-14, generalised from the `HARNESS_BACKLOG.md` precedent — the one consolidation
mechanism already proven to work here. Roughly 12 of 34 scripts and 4 of 6 hooks manage the record
keeping and dev process rather than the product; that ratio is why this rule exists.

**`bash scripts/qa_sweep.sh`** is free (9 checks, ~3s) and is the right thing to run after any
harness edit. It parses; it does not execute — run the thing you changed.
