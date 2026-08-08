# 2026-08-05 — ROADMAP Gap Fix and Archive Six-Step

Short, direct follow-on to the B1a red-team session's own `/archive` run. Triggered by a premise
check from the user: "we've moved the B stuff out of dev_backlog and made note of it on overall
project progress, right?"

Full reasoning: [archive/PROJECT_LOG.md](../PROJECT_LOG.md) § 2026-08-05 (ROADMAP.md gap closed;
/archive gets a sixth step).

---

## What the premise check found

- **Nothing moved out of `DEV_BACKLOG.md`.** The B1a session only added entries — the completion
  record, the MUST_SURFACE finding, the stale `research_agent` correction.
- **`SESSION.md` and `PROJECT_LOG.md` were correct.** Both reflected B1a's completion.
- **`ROADMAP.md` was not touched at all.** Its B1 section still read as pure future work — no
  mention that the disclosure suite, output-filter suite, or confused-deputy test had already
  run and passed. Confirmed by grep, not assumed.

## Root cause

`.claude/commands/archive.md` never mentioned `ROADMAP.md`. Five steps covered the transcript,
`PROJECT_LOG.md`, the session writeup, `SESSION.md`, and `DEV_BACKLOG.md` — nothing asked whether
a roadmap-tracked item had changed status. The two files that got updated did so because the
ritual named them explicitly.

## What was built

1. **`.claude/commands/archive.md`** — five steps → six. New step 5 between `SESSION.md` and
   `DEV_BACKLOG.md`: "Update `ROADMAP.md` if this session touched anything it tracks." The exact
   failure mode (B1a's roadmap gap) is named as a worked example in a blockquote at the top of
   the file, read before step 4 starts. Explicit trigger: check this especially when something is
   being marked done or removed from `DEV_BACKLOG.md`.
2. **`ROADMAP.md` §B1** — ✅ status blockquote under the B1 heading, matching the inline-note
   style A7's pre-sign-off gate already uses on the same page. States B1a done, links the report
   and log entry, states B1b and B1-as-a-whole are still open.

## Decision rejected

Considered striking through B1's build instructions now that B1a is done. Rejected — B1b still
needs the same instructions to run its own suite; a status note above live instructions, not a
strikethrough, is the right shape.

## Deploy status

Nothing deployed. Two markdown files edited, no code touched.
