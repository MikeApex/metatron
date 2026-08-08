---
description: Score open DEV_BACKLOG.md items and produce three independent, single-session work prompts
---

Metatron — Backlog Attack Plan

Score the open `DEV_BACKLOG.md` items and produce three independent, single-session work
prompts. This is planning only — do not fix anything in this pass. Output is a scored list plus
three ready-to-hand-off prompts; implementation is a separate, later session.

## 0. Load context first

Run `/metatron-code` before anything else in this command — read `SESSION.md`, the active
roadmap it points to, and `CODEBASE_INDEX.md` if needed. Do not skip this: importance scoring
in step 2 depends on knowing current phase gates and freeze states, and file-ownership checks in
step 4 depend on knowing which files/tracks are live vs. frozen.

## 1. Load the backlog

Read `DEV_BACKLOG.md` in full (not just the sync counts). Work from `## Open` items — anything
still in `## Inbox` is untriaged and out of scope for this pass; note the untriaged count but
don't score those items.

## 2. Quick score, not a deep audit

For each open item, assign two numbers:

- **Importance (1–100)** — weight relative to the *whole project*, not just the backlog. Higher
  = more important. Use the roadmap's phase gates and named hard-fail criteria (Finance
  accuracy, Mental Wellbeing clinical flags) as an importance signal — items blocking those
  score higher.
- **Difficulty (1–10), inverted** — 10 = easiest, 1 = hardest. A one-file, well-scoped fix is a
  9 or 10; anything touching routing, persona identity, or the scheduler gate stack is a 3 or
  below regardless of line count.

`task_score = importance × difficulty`. Rank descending. This pass should take minutes, not
a deep read of each item — score from the entry text and a fast skim, don't open every file.

## 3. Verify only the shortlist

Per the standing backlog rule — **no item is acted on, or re-filed, on the strength of its own
description** — before an item is allowed into a final cluster (step 4), open it against the
current code: confirm the cited file/function/line still exists and the symptom is still
plausible. Only do this for candidates actually in contention for the top slots, not all open
items. Drop or re-score anything that turns out stale; note what you found.

## 4. Cluster into 3 independent prompts

Pick the highest-scoring items that together are completable in one normal session, then split
them into exactly 3 groups such that:

- Each group is a few (2–4) related items.
- **No two groups touch the same file, directory, or deploy target.** Check this explicitly —
  e.g. two items both editing `core/orchestrator.py`, or both in `config/agents/`, cannot go in
  different groups even if their scores are both high.
- Note per group whether it requires `./deploy.sh` afterward (anything under `core/`, `config/`,
  `tools/`) so the three can genuinely run in parallel without stepping on each other or on a
  shared deploy.
- If VM-owned files (`config/personas/**`) are involved, flag that explicitly — those need the
  Mac→VM scp discipline, not a normal edit.

## 5. Output

1. A numbered table of scored items (id, one-line summary, importance, difficulty, score),
   highest first — per the numbered-list convention, for easy reference ("on item 3...").
2. The 3 cluster groupings with their combined rationale (why these items, why they don't
   overlap).
3. Three standalone prompts, one per cluster, each self-contained enough to hand to a fresh
   session or subagent with no other context: state the goal, list the specific `DB-####-##`
   ids and files involved, and note the verification already done in step 3 so the receiving
   session doesn't repeat it.

Do not start implementing. Stop after presenting the three prompts and ask which (if any) to
run now.
