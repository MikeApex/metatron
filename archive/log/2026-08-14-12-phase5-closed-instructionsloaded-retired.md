### 2026-08-14 (Phase 5 closed: both open questions answered, InstructionsLoaded retired)

Continuation of the same day's `b07f5da` tail. The prompt at
`~/.claude/plans/context_phase5_close_prompt_2026-08-14.md` left two questions open; both are
now answered from real log entries, and the disposable instrumentation is retired per its own
header's retirement condition.

**1. Does a Grep-*tool* survey trigger `path_glob_match`? Answer: question dissolves — no Grep
tool exists in this Claude Code install.** Checked via `ToolSearch` in two independent sessions
(this VS Code-extension session, and a separate terminal CLI session) — neither exposes a
distinct Grep or Glob tool, deferred or otherwise; only Bash is available for text search in
either harness surface. So every grep-based survey in this install — Bash `grep`, an Explore
subagent, a `/backlog attack` worker — necessarily goes through Bash, which was already shown
2026-08-14 not to trigger `path_glob_match`. **The premise the question was built on (a Grep tool
distinct from Bash grep, used by survey-style sessions) does not hold here.** Mike's call on
filing: since this doesn't add a new actionable gap beyond the already-known Bash-grep result,
it is recorded here rather than filed to `DEV_BACKLOG.md` `## Now` — "if it doesn't exist it
shouldn't interfere with the plan build out."

**2. Do rules load in a worktree session? Answer: yes, confirmed.** Used the native
`EnterWorktree` tool (this harness's mechanism — differs from the plan's assumed
`scripts/new_worktree.sh` CLI flow) to create a worktree, then read `config/agents/logistics.md`
inside it. `.claude/rules/agent-files.md` delivered in full (visible in context, and logged with
`load_reason: path_glob_match`). **Worktree sessions do get rule delivery** — the concern in
`hook_context_gate.py`'s correction 2 (worktree edits bypassing the *briefing*) is a distinct
mechanism from rule delivery via `.claude/rules/*.md`, and this measures only the latter.

**Secondary finding, not one of the two questions: the hook's own log write is worktree-scoped,
not project-scoped.** `hook_instructions_loaded.py` resolves its root via `git rev-parse
--show-toplevel` from cwd (deliberately, to see worktree sessions at all — see its header) — but
inside a worktree that returns the worktree's own path, so the entry landed in
`.claude/worktrees/<name>/.claude/instructions_loaded.jsonl`, a separate gitignored file, not
the main tree's log. Harmless here since the instrument is being retired in this same session,
but worth knowing if similar per-file logging is ever built again: worktree-root resolution and
"write where the main session can see it" are in tension unless the path is chosen deliberately.

**Retirement, per the script's own stated condition and `.claude/rules/deploy.md`'s standing
rule against unretired machinery:**
- Deleted the `InstructionsLoaded` block from `.claude/settings.json`.
- Deleted `scripts/hook_instructions_loaded.py`.
- Deleted `.claude/instructions_loaded.jsonl` (confirmed gitignored and untracked via `git
  status --short` before removal).
- `qa_sweep.sh` — 9/9 pass after the edit.

**Phase 5 is now fully closed.** Nothing else changes: `CODEBASE_INDEX.md` retirement still
held, Phase 4 (ROADMAP split) still deferred, nothing deployed (`core/`/`config/` untouched).
Next work is product: `[DB-0810-13]`.
