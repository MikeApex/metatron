# Build v4.11 phase C — coherence review brief

*Written 2026-09-24 by the coordinating window, for an independent reviewer with no memory of the
session that produced the work under review.*

---

## READ THIS TREE, NOT THE DEFAULT ONE

**Every file named below lives in the worktree at
`/Users/md-homefolder/Desktop/metatron-wt-v4c-command`, not in
`/Users/md-homefolder/Desktop/multi-model-mcp`.** The work is uncommitted. The main tree still holds
the previous versions of the `core/build/` files, so reading it will show you code that is not under
review and will make the command look inconsistent with it for the wrong reason.

---

## The question, and it is narrow

**Do these four layers say the same thing?**

1. **`.claude/commands/build.md`** — the command a session follows to run a Build job.
2. **`.claude/agents/build-{inquiry,librarian,planner,implementer,coherence}.md`** — the five
   subagent definitions the command spawns.
3. **`core/build/*.py`** — the code that is meant to *enforce* what the command describes.
   Changed in this pass: `driver.py`, `gates.py`, `schemas.py`, `registry.py`, `tick.py`,
   `tickets.py`, `verify.py`, plus `tools/build.py`.
4. **The suites** — `tests/test_build_*.py`, `tests/support/build_fixtures.py`.

The three failure shapes worth hunting, in order:

- **The command promises behaviour the code does not enforce.** The governing rule of this design is
  that the command is *not* the runner — `core/build/driver.py` is — and that a model reading the
  command cannot skip a step, because the driver will not name it. Anywhere the command describes a
  sequence, a bound, a park or a refusal that exists **only as prose**, the rule is broken. This is
  the defect class the previous round found eight times; the claim under review is that all eight are
  now code.
- **A subagent definition claims a tool, a capability or an input it does not have** — or the command
  hands it something its `tools:` frontmatter cannot act on.
- **A suite asserts the old behaviour, or asserts nothing where the behaviour changed.** An
  assertion that passes because it no longer tests the thing is worse than a missing one.

---

## Second task: adjudicate the previous round's own claims

Three review rounds already ran against this work, in the same session that wrote it. They are on
disk in the worktree:

```
archive/plans/adversarial_review_build_command_2026-09-24_r1.md
archive/plans/adversarial_review_build_command_2026-09-24_r2.md
archive/plans/adversarial_review_build_command_2026-09-24_r3.md
```

**Read them, and check whether what they say was fixed actually is.** The author adjudicated its own
review — it decided which findings were addressed and which it refused — and nothing independent has
checked that judgement. A finding recorded as closed that is not closed in the code is the highest
value thing you can return.

Two claims from the author that are worth testing specifically, because both are the author's own
account of a limit rather than a fix:

- **`file_ticket` is said to refuse any caller that is not one of two named VM-side writers**, while
  conceding nothing in-process distinguishes the Mac from the VM. Is the refusal real, and is the
  concession the whole of the gap or only part of it?
- **One pre-existing assertion is said to now guard a backstop rather than a trigger** — "a SECOND
  send-back parks the job" — on the grounds that a rejection count parks first. Is the new trigger
  actually reached before the old one, and is `MAX_SEND_BACKS` genuinely derived from
  `MAX_PLAN_VERSIONS` such that they cannot drift?

---

## Off the table — do not review these

- **`archive/plans/build_vertical_plan_2026-09-24.md` and its § 0 rulings.** The plan is settled.
  Thirteen rulings are the project owner's decisions, not design proposals. Read the plan as the
  *specification you are checking the code against*, never as something to critique.
- **The two plan reviews** (`adversarial_review_build_vertical_plan_2026-09-24.md` and
  `..._cold-fable.md`). Both reached a clean pass across ten rounds. Their closed findings are closed.
- **Anything already landed and committed in earlier phases** except where the layers above disagree
  about it.

A finding that re-proposes a settled ruling, or re-opens a closed finding, is not useful here.

---

## What you return

Errors and inconsistencies. Nothing else — do not amend, do not plan, do not propose a
implementation, do not endorse. You have no write tools and that is deliberate. **The author of this
work corrects it**, from your findings, and is standing by to do so.
