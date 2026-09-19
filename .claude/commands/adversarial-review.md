---
description: Adversarial review of a plan against the real codebase — spawns a read-only reviewer, returns ranked structural and local defects
---

# /adversarial-review — find what will break before building it

**Input:** a plan file. **Output:** two ranked blocks of defects, and a file you can
hand to a different chat. The reviewer does not improve the plan, endorse it, or
soften anything. Fire it after `ExitPlanMode`, before writing a line of code.

```
/adversarial-review [plan-path] [model] [effort]
/adversarial-review verify [what changed]
```

Tokens are recognised by vocabulary, not position, so any order works:

| Token | Meaning | Default |
|---|---|---|
| a path | the plan to review | the plan file from this session's plan mode |
| `fable` `opus` `sonnet` `haiku` | which model reviews | **`fable`** |
| `low` `medium` `high` | how much of the code gets verified | **`medium`** |
| `verify` | resume the existing reviewer against the revised plan | — |

**Model selection is by family only.** The spawn parameter takes `fable`, `opus`,
`sonnet` or `haiku` — there is no way to pin a version from here. If a specific
version matters, say so and it becomes a manual spawn, not this command.

---

## 1. Resolve the plan, or stop

The plan must exist as a file. Plan mode writes one, so after `ExitPlanMode` there
is a path — use it. If the plan exists only as chat text, **copy it to
`archive/plans/{slug}_{YYYY-MM-DD}.md` first and review that**: a subagent inherits
none of this conversation, and a plan described to it second-hand is a plan it
cannot verify claims against.

Say which file is being reviewed, in one line, before spawning.

## 2. Spawn the reviewer

`subagent_type: adversarial-reviewer`, `run_in_background: true`, `model:` only when
a non-default was named. The prompt is three things and nothing more:

- the absolute path to the plan file
- the effort level, verbatim (`low` / `medium` / `high`)
- the repo root, `/Users/md-homefolder/Desktop/multi-model-mcp`

Everything else is in the agent definition. **Do not summarise the plan, explain its
intent, name its author, or say what you think of it** — every one of those
contaminates Pass 1, which is the pass the whole design exists to protect.

**Background, always.** The review takes minutes and Mike can keep working. Report
the spawn line the hook hands you, then stop and wait.

## 3. Land the report

When it returns, write its final message **verbatim** to
`archive/plans/adversarial_review_{plan-slug}_{YYYY-MM-DD}.md`, with a two-line
header naming the plan reviewed, the model, the effort level and the date. No
editing, no reordering, no softening. That file is the only part of the review that
survives this chat.

Then relay to Mike: the rank-1 finding in full, the count in each block, and the
link. Not the whole report — he can open it.

## 4. Revise, then `verify`

Mike revises the plan file; `/adversarial-review verify` resumes **the same
reviewer** via `SendMessage`, with its Pass 1 and Pass 2 context intact, so the
second round costs a fraction of the first. Name the findings the revision claims to
close. Append its verdict lines to the same review file under a dated `## VERIFY`
heading.

**The reviewer is not neutral about its own findings.** It wrote them; it is the
reader most likely to accept a revision that gestures at one. The agent definition
requires re-anchoring to code rather than to the revision's prose — if a `CLOSED`
verdict arrives without a `path:symbol`, it has not verified, and the finding still
holds.

---

## The rules

1. **Nothing gets built between the spawn and the report.** Exiting plan mode
   normally means execute; here it means review first. Waiting is the point.
2. **The reviewer is read-only by construction** — `Read`, `Grep`, `Glob`, no write
   tools at all. It never runs `/metatron-code`, because that syncs the backlog and
   writes to disk; it reads `SESSION.md`, the roadmap and `CODEBASE_INDEX.md`
   directly, between the two passes.
3. **Reviewing is not building, so the Red-tier no-delegation rule does not apply.**
   A reviewer that writes nothing cannot make a Red-tier change. Judgement about
   what to *do* with a finding stays here.
4. **The reviewer lives in this chat only.** Close the session and it is gone; a new
   chat gets a fresh reviewer with no memory of round one. The file from step 3 is
   what carries across — give it to the new chat alongside the plan.
5. **Fewer findings is a result, not a failure.** Do not ask for more, do not ask it
   to reconsider a clean pass, and do not re-run at a higher effort hoping for a
   longer list. A manufactured finding costs more than a missed one, because it
   gets acted on.

## Cost

One `medium` pass on a multi-phase plan is roughly a `/backlog deep`: the plan, the
three orientation files, and targeted reads of the files the plan touches. `low`
roughly halves it; `high` can double it, because it walks call sites. The `verify`
round is cheap — the reviewer's context is already warm.

**Effort is the cost lever.** Default `medium`. Reach for `high` when the plan
migrates data, renames something public, or is the last gate before a deploy.
