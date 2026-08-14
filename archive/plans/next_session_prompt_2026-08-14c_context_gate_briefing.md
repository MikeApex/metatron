# Next-session prompt — context-gate briefing + regrowth branch

*Written 2026-08-14. Approved scope only. Full plan and its reasoning:
`~/.claude/plans/create-a-plan-to-sequential-bachman.md`.*

---

## Paste this to start

> Run `/metatron-code`, then build the approved minimal scope from
> `~/.claude/plans/create-a-plan-to-sequential-bachman.md` — **Phase 1 and the regrowth branch
> only.** Do not build Phases 2–5; they are deferred by decision, not oversight.
>
> **Run verification step 1 BEFORE writing any code.** Confirm by hand that a fragment-only
> grep of `archive/log/` fails to surface the `get_weather` history for
> `config/agents/logistics.md`, and that `archive/log/_history.md` holds it (4 hits). That
> failing result is the design input for the history channel — not a check to run afterwards.
>
> **Two things in this plan are older than your session.** Re-verify before acting on either:
> that `hook_context_gate.py` still returns `None` for paths outside the main tree
> (lines ~160-163), and that `hook_agent_tools.py` is still registered `PostToolUse` on
> `Write|Edit` in `.claude/settings.json`. The plan's own thesis is that a stale premise argues
> persuasively for the wrong thing.
>
> Work solo — do not spawn workers. Show me diffs before applying them to
> `scripts/hook_context_gate.py`. Nothing here deploys.

---

## What is being built

**1. Rewrite `scripts/hook_context_gate.py`** — replace its single generic warning with a
per-file briefing emitted as `additionalContext` on `PreToolUse` `Write|Edit`:

- `git log -5 --format='%ad %s' --date=short -- <file>`
- `archive/log/` hits **including `_history.md`**, as nearest enclosing `### ` heading + ~5-line excerpt
- open `DEV_BACKLOG.md` items naming the file
- Red/Denied tier from `.claude/settings.json`
- the governing area, always — this is what survives `/compact`
- the existing SESSION.md/ROADMAP.md warning, kept

Constraints: warn, never block. Under the documented 10,000-char cap, truncate oldest-first.
Once per file per session, not once per session.

**Resolve the project root from the target path** (`git -C <dir> rev-parse --show-toplevel`),
not `CLAUDE_PROJECT_DIR`. This is the worktree fix and it is the highest-value line in the
build — worktree edits bypass the gate entirely today, which means `/backlog attack` workers
get no gate at all.

**Special-case a `Write` to a file that does not exist yet** in a governed area: emit the
governing area rather than nothing.

**2. Add a ~15-line branch to `scripts/hook_agent_tools.py`** — when the edited file is
`CLAUDE.md` or `.claude/rules/*.md`, emit the post-edit line count against ceiling plus the
router question: *"is this binding-everywhere, or area-specific — and which rule file is the
area?"* Import `CEILINGS` from `scripts/check_claude_md_claims.py`; **do not copy the numbers.**

---

## Verification — all same-session

1. **History channel** (run first, see above) — briefing surfaces `get_weather` for `logistics.md`.
2. **Worktree** — `scripts/new_worktree.sh`, edit a governed file inside it, briefing fires. `scripts/rm_worktree.sh` after.
3. **New file** — `Write` a non-existent `config/agents/scratch_probe.md`, confirm the no-history branch names the area. Delete after.
4. **Regrowth branch** — edit `CLAUDE.md`, confirm count-vs-ceiling and the router question appear.
5. **No regressions** — `bash scripts/qa_sweep.sh` (9 checks, ~6.6s); `python3 scripts/check_claude_md_claims.py` stays **36/36**.

Also: under 10,000 chars, and it warns rather than blocks.

---

## Context worth carrying

- **Recommended model: Sonnet 5.** Mechanical Python against a documented hook contract; the judgement calls are already settled in the plan. ~65k tokens, ~1h.
- **Nothing deploys.** Dev-harness only; `core/` and `config/` runtime untouched.
- **This is the last procedural block before product work.** Next up is
  `[DB-0810-13]` — specialists reporting actions they never took, so anything the system says
  it did (email, calendar, scheduling) is unverified. Do not find a 26th process improvement
  while doing this one.
- **Standing rule adopted with this plan:** no new standing harness script or hook without
  naming what it retires, or the build that will retire it.
