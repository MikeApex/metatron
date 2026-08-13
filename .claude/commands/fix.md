# /fix — make one change, return one reviewed diff

**Input:** a description, a `DB-` id, or a finding handed over from
`/metatron-troubleshoot`. **Output:** one diff, approved once, at the end.

Fire it whenever you would otherwise say *"can you fix X."* There is no ceremony
and no cost to using it for something small. Claude invokes it on itself when
about to do mechanical work rather than doing it inline.

**The standing rule comes first: if it is a one-liner you are already looking at,
fix it and file nothing.** Most findings are. `/fix` is for work big enough to be
worth a briefing, not for everything.

---

## How it relates to `/metatron-troubleshoot`

Different questions, and they chain.

| | Answers | Input | Ends with |
|---|---|---|---|
| `/metatron-troubleshoot` | **what went wrong** | a DATE + SEQ | fixed inline (most cases), or `→ /fix` |
| `/fix` | **make this change** | a description, a `DB-` id, or a troubleshoot finding | one reviewed diff |

`troubleshoot` gathers evidence — conversation record, server logs, pipeline
trace, one SSH round-trip. `/fix` gathers none. It classifies, verifies the
premise, dispatches.

---

## The five steps

### 1. Classify against the tier table — one line, tier and why

`CLAUDE.md` § Change tiers, and `.claude/settings.json` is the authority.

| Tier | Roughly | Who builds it |
|---|---|---|
| Green | `tests/`, `scripts/`, `docs/`, `archive/`, comments, logging | Sonnet worker |
| Amber | `tools/*.py`, `core/*.py` (non-red), `static/`, non-routing `config/modules/*.yaml` | Sonnet worker, Opus reviews |
| **Red** | `config/agents/*.md`, `routing*.yaml`, `core/{router,persona,scheduler,spend_guard}.py`, `./deploy.sh`, `git push` | **Opus, here. Never delegated** |
| Denied | `config/constitution.md`, `config/personas/mike*`, `data/personas/**`, `.env` | nobody, until lifted explicitly |

Red is not delegated because **there the judgement is the work** — and a
contractor without the project's history decides wrong, confidently.

### 2. Verify the premise against current code — before touching anything

**A stale premise argues for the wrong fix, persuasively.** A 2026-08-05 sweep
found roughly a third of checked backlog items stale: causes already fixed, cited
functions gone, line numbers hundreds of lines out. One produced a well-reasoned
recommendation to hold a tool grant pending work that had shipped two days
earlier.

Open the file. Confirm the thing described is still true. If it is not, say so and
stop — that is a complete and useful outcome, not a failed `/fix`.

### 3. Dispatch

**Green / Amber** → one worker, explicitly named:

```
Agent(model: "sonnet", isolation: "worktree", subagent_type: "general-purpose")
```

The brief must carry, because a worker starts cold and inherits none of this
conversation:

- what to change and what "done" looks like
- **the hard stop: if the fix requires a Red-tier file, report and do not edit it**
- that `config/personas/mike*` is VM-owned and the Mac copy is not authoritative
- that a tool named in an agent file is a *specification*, not a bug to delete
- whether it needs `./scripts/new_worktree.sh <slug> --with-personas` (it does if
  it runs the A4 or B1 suites — without the flag the fixture trees are hollow, not
  absent, so a suite will run against incomplete data rather than fail loudly)

**Red** → built here on Opus. No worker.

**One task per `/fix`.** There is no `/fix-all` and this file does not add one.

### 4. Review what comes back

Read the diff — actually read it, not the worker's summary of it. Then:

```bash
./scripts/qa_sweep.sh
```

The `SubagentStop` gate already ran this before the worker was allowed to report,
so a worker that reports done has passed it. Run it again after review anyway: the
gate saw the worker's tree, and this is yours.

> **A green sweep is not a test.** `py_compile` parses without executing. It
> passed the `NameError` that crash-looped the scheduler after deploy, and one in
> the commit guard. **Run the thing that changed**, and say in the report what you
> ran.

### 5. One consolidated diff, approved once

State plainly: what changed, what was verified and how, what is still open, and
**actual token cost against the estimate**. Without that last part the estimates
never calibrate.

---

## Committing — one commit, one reason

**Not "one commit, one file."** Where behaviour is emergent across components the
smallest *correct* unit is not the smallest possible one: the 2026-08-10
observability work only made sense as one change across five model-call sites, and
`[DB-0808-09]` is the cautionary case — a fix scoped to the Coordinator would have
"passed" atomically while the real cost sat untouched in the specialists.

What is not acceptable is **a commit with two reasons in it**. That is the
2026-08-09 failure: a commit titled for one thing carried another session's
routing grant, and `./deploy.sh` put it live while its governing instructions sat
uncommitted.

So:

- `git diff <file>` **before** staging it — `git add <path>` stages the file's
  whole current content, including another session's uncommitted lines. Staging by
  filename was the discipline in force in 2026-08-09 and it did not help, because
  the check was at file granularity against a line-granularity collision.
- `scripts/hook_commit_guard.py` blocks a commit carrying a file that changed
  underneath this session. `METATRON_COMMIT_GUARD=off` overrides it deliberately.
- **Check `git show --stat` after committing, not just the exit code.**
  `git add A B C` aborts entirely if one path is bad, and a following commit then
  captures whatever was staged before.
- Where a fix looks systemic, **measure which scale the cost is actually at before
  fixing at the scale you assumed.**

**`/fix` never deploys.** Deploy is a separate, deliberate decision — *"never add
a config key before the code that gates it is deployed"* is a judgement no command
should make on its own.
