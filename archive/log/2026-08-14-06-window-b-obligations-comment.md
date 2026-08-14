### 2026-08-14 (window B — `_find`'s None return documented as a signal)

A comment-only change to `tools/obligations.py`. No behaviour changed, nothing deployed.

`_find()` linear-scans the store and returns `None` on a miss. That return is load-bearing:
`close_obligation` and `reopen_obligation` both branch on it to emit `no obligation with id ...`,
which is what tells a session it has quoted an id that does not exist instead of silently doing
nothing. Read quickly, the bare `return None` looks like an unfinished lookup, and the obvious
"improvements" — raising, or returning an empty dict — each delete that message. The comment says
so at the definition, where someone tidying it will be standing.

**The brief named three callers; there are two.** `open_obligation` does not use `_find` — it
never takes an id, and its near-duplicate check is its own scan over `what` text. The comment
names `close_obligation` and `reopen_obligation` only, because a comment that lists a caller that
does not exist is the same stale-premise failure `CLAUDE.md` already records twice: it survives
until someone acts on it.

**Written as a fragment, not committed through `/archive`.** A second window was live in this
tree for the duration, which is the case fragments exist for. `archive/PROJECT_LOG.md` has **not**
been rebuilt — `scripts/build_project_log.py` is owed before `qa_sweep.sh`'s `--check` will pass.

**Collision handled, and it was live rather than hypothetical.** `tools/obligations.py` already
carried an uncommitted three-line comment on `_new_id` from the other window when this session
opened it. `git add tools/obligations.py` would have swept it into this commit — the exact
file-granularity-versus-line-granularity gap in `CLAUDE.md` § Deploy safety rule 4, which is
recorded there because staging by explicit filename did not prevent it on 2026-08-09. Staged with
`git apply --cached` against a single-hunk patch instead; the other window's lines stayed
unstaged in the working tree.

One observation filed to `.claude/backlog_inbox/`: `context_block`'s due-date sort ranks a vague
`due` phrase behind obligations with no due date at all.

