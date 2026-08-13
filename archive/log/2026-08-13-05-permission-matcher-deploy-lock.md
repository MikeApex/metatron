### 2026-08-13 (the permission matcher, the deploy lock, and a Red tier that never prompted)

Throughput §1 revisited, from the window started specifically because **a session cannot verify
its own permission-mode change**. Three defects went in as two; a third came out that is worse
than either. No runtime code, nothing deployed (`502e560`). The parallel window ran §8/§5 and
the `/backlog` ceiling throughout; it committed `daf314d` and `b4abdde` while this was open.

**H5 — `defaultMode: "auto"` was never in effect, and the plan's headline number had therefore
never been observed.** The value parsed cleanly and then did nothing: the `PreToolUse` gate
reported *"requests 'auto', running 'default'"* on this session's first `Write`, as it had on
every session since the setting landed. So Phase 1's measured **85–88% prompt reduction was
unrealised for the life of the file** — the plan's stated payoff, never once delivered.
Replaced with `allow: ["Bash", "Read", "Edit", "Write"]`. **Blanket, not an enumerated
safe-command list** (Mike's call, offered three ways): 201 of the 1,185 backtested prompts were
unclassifiable compounds, and an enumerated list is incomplete by construction, so everything
omitted keeps prompting — which is the failure being fixed. Residual risk unchanged from the
plan: a destructive command nobody thought to deny.

**H2 — the deploy lock was blind across worktrees.** `LOCK_DIR` was `BASH_SOURCE`-relative and
each worktree carries its own tracked `deploy.sh`, so both `mkdir` calls succeeded and two
deploys could push and SSH the same VM: the 2026-08-09 interleave, reintroduced by the worktree
system. Now from `git rev-parse --git-common-dir`, resolved **relative to the script, not the
caller** — the raw output is the bare string `.git` at a repo top level, which would otherwise
put the lock wherever the caller happened to be standing.

**The `Write` deny hole, and the audit it asked for.** `claude config list` had been naming five
silently-ignored rules to nobody: every `Write(path)` entry, because only `Edit(path)` matches
file edits. `config/constitution.md` — Tier 0 — was blocked against `Edit` and **reachable by
`Write`**. Fixed by *deleting* the `Write` entries rather than keeping them alongside, since a
rule that does not match is indistinguishable from one that does. The audit found a sixth:
`Bash(./deploy.sh)` was **exact-match**, so `./deploy.sh --anything` escaped the Red tier
entirely.

**What was believed and turned out wrong.** Two things. (1) The item said the Write hole's fix
was "mechanical" — it was, but only after the `Edit`-covers-`Write` claim was *tested on a decoy
file*, because the whole point of the finding is that documented matcher behaviour had already
been wrong once. (2) Far more important: **`ask` rules do not gate at all in this harness.**
`git push --dry-run origin main` reached GitHub with no prompt. In the VS Code / Agent-SDK
harness a prompt that cannot be shown is auto-**approved**; `deny` is enforced and hot-reloads
without a restart. A plain-CLI `claude -p` session auto-**denies** the same prompt — the two
harnesses fail in opposite directions from identical settings. So the entire Red tier —
`./deploy.sh`, `git push`, agent-file and router/scheduler edits — **is ungated in any
unattended session**, and has been. Filed as **H7** with the deny-vs-ask decision left open;
`CLAUDE.md`'s change-tier table now says so at the point a reader would trust the "prompts every
time" column. Not a regression from the blanket allow: precedence was tested with
`allow: ["Bash"]` in force and both `deny` and `ask` still outranked it.

**Everything above was found by running.** The static reading of `settings.json` is what had
been done before and it produced the wrong answer three times: `auto` looked valid (it is a
valid `--permission-mode` value — it is just not honoured as a `defaultMode`), the deny list
looked enforced, and the ask list looked enforced. The confirming runs also exposed a trap in
the *method*: early scratch tests were silently meaningless because **project `allow` entries
are ignored in an untrusted workspace**, and because `echo` is in a built-in read-only set that
never prompts in any mode, so the first three probes discriminated nothing.

**Rejected: hunk attribution for shared-tree commits.** Splitting this session's `CLAUDE.md`
hunk from the parallel window's was the most laborious part of the close-out, but that is the
fingerprinting design the Chorus round already killed for a fatal false negative on a shared
tree. The mechanism for that problem exists and is `scripts/new_worktree.sh`. Filed instead as
**H8**: three checks this build enforces by memory that belong in code — permission-rule
liveness into `qa_sweep.sh` (highest value; the Write hole was found *incidentally* and nothing
else would have found it), session token accounting as a `Stop` hook, and the deploy-lock
invariant as a sweep check.

**Gate discipline, reported honestly:** the work block estimated 45–60k tokens and cost **438k**
non-cache-read — a 7× miss, because the estimate measured context growth rather than billed
total across ~40 round-trips. H8's second item exists to stop that being a judgement call.

`HARNESS_BACKLOG.md` now stands at **three open** (H6, H7, H8; the commit-guard item deferred
with a reason by the parallel window) and **six closed**.
