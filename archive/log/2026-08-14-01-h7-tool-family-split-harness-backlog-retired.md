### 2026-08-14 (H7 closed: `ask` splits by tool family; `HARNESS_BACKLOG.md` retired)

`[H7]` closed, and with it the development-throughput build's harness backlog — **eleven items
opened, eleven resolved**, one of them deferred with a stated reason rather than fixed. No runtime
code, nothing deployed.

**The defect was not what it was filed as.** H7 said *"`permissions.ask` does not gate in the VS
Code / Agent-SDK harness"* and attributed it to non-interactivity: a prompt that cannot be shown
resolves to allow. Both halves were too broad. Measured by hand in both harnesses, same rule, same
command, same `settings.json`, minutes apart:

- **iTerm, `claude` interactive REPL — prompt fired**, and named the rule that produced it:
  *"Permission rule `Bash(git push *)` requires confirmation for this command."* So the matcher
  resolved the glob, selected `ask`, and rendered it, end to end. Declined; nothing ran.
- **VS Code chat panel, human-typed, same command — no prompt, it just ran.**

That kills the unattended-sessions reading: a human was sitting in the window watching for the box
and there was no box. But the *real* scope only appeared on a third probe, which the original
brief did not call for. A throwaway `Edit(./probe_target.txt)` ask rule against a scratch file:
**the box appeared, was declined, the tool call aborted, and the file was left byte-unchanged.**

**So the split is by TOOL FAMILY, not by harness alone.** `Edit(…)` ask rules prompt and block
here; `Bash(…)` ask rules resolve to allow. Nine of the twelve Red-tier rules — `config/agents/*.md`,
both routing files, `core/{router,persona,scheduler,spend_guard}.py` — **have been gating correctly
all along.** The ungated surface was `./deploy.sh` and `git push`, and nothing else.

**This vindicates §10 Verification check 2** (*`Edit` on `config/agents/logistics.md` → prompt
fires, observed 2026-08-13*), which had looked like a flat contradiction of H7. It was a true
observation that simply does not generalise across tool families, and nothing recorded at the time
claimed it did.

**Why the narrowing mattered.** H7's decision table framed every outcome as the Red tier passing
or failing *as one thing* — its bottom row read "the Red tier must move". Applied on the `git push`
evidence alone it would have moved twelve rules to `deny`, breaking agent-file and core-module
editing for no reason. **A decision table whose rows are coarser than the defect will overshoot,
confidently.**

**Decision (Mike, 2026-08-14): `./deploy.sh` → `deny`; `git push` stays `ask` and stays inert.**
Six deny entries, not the three that were in `ask` — bare, `bash`- and `sh`-prefixed, each in
exact-match and ` *` glob form. The original `Bash(./deploy.sh)` was exact-match-only, so
`./deploy.sh --anything` escaped the Red tier entirely; there was no reason to reproduce that hole
in a `deny`. Lifting the deny is the gate now: one deliberate settings edit per real deploy.

**`git push` left knowingly ungated in this panel** — *rejected: denying it.* That would break
`/archive` step 5, which pushes and then asserts the push landed, an assertion added three commits
earlier *because* 11 commits once sat unpushed for six hours. Trading a working close-out ritual
for a gate on a private-repo push was the wrong exchange. It gates normally in the iTerm REPL.

**A hazard found while planning the tests, worth more than the tests.** The drafted third probe was
`./deploy.sh --help`, to exercise a second `Bash` rule "without touching the VM". **`deploy.sh` has
no argument parsing at all** — no `case`, no `getopts`, no `$1` in 269 lines — so it ignores unknown
flags and proceeds to push, SSH, pull, `pip install` and restart both units. And the probe only
*reaches* execution in the branch where `ask` is dead, which was the hypothesis under test: working
gate → harmless prompt; broken gate → **a real unattended production deploy.** Not run.
**Generalised rule, now in `CLAUDE.md`: never test a `Bash` permission rule by running the real
command — a negative result is the damage. Use an inert decoy of the same rule shape.**

The deny itself was verified that way rather than on `deploy.sh`: a `probe_deploy.sh` that only
echoes, temporarily denied in `settings.local.json`. Both `./probe_deploy.sh --help` and the bare
form were refused and the echo never printed. Rule and script removed; `settings.local.json` byte-
identical afterwards. This leans on `Bash` `deny` already being proven live here twice on
2026-08-13; what the decoy adds is that these *rule strings* match a `./script.sh --flag` call.

**The finding that outlives the file.** This harness produced **two tool-family matcher splits in a
single build** — `Edit` vs `Write` in the deny list (Tier-0 `constitution.md` blocked against
`Edit`, reachable by `Write`), and `Edit` vs `Bash` here. In both cases one family gated, the other
silently resolved to allow, and **the working family made the broken one look fine.** The rule —
*probe a permission rule per tool family, never once* — is recorded in `.claude/settings.json`'s
`_comment_ask`, where someone editing the rules will be looking, and in `CLAUDE.md` § Change tiers.

**`HARNESS_BACKLOG.md` deleted, per its own contract** — *"reconciled within the build that opened
it, never carried"*, because a harness backlog that outlives its build becomes a second permanent
bin. Its eleven items and their evidence are in this fragment and the six before it; the row in
`CLAUDE.md` § Which File Holds What is removed in the same commit. **The one item not fixed is
recorded as deferred, not closed:** the commit guard's false positives on shell it cannot parse
(a trailing `echo` after `git commit`, a pathless `--amend`, any file written by a script rather
than `Edit`/`Write`) stay deferred as ergonomics now that `METATRON_COMMIT_GUARD=off` works —
revisit when a case appears the override does not clear. Filing it back into `DEV_BACKLOG.md` was
**rejected**: it is harness, not Metatron, and that file's `now`/`later` counts stop meaning
anything if harness items are mixed in.

