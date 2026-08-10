---
description: Close out a session — verbatim transcript, one project-log entry, SESSION.md refresh, backlog close-and-file
---

Metatron — Archive This Session

Five steps, in order — minutes, not a work block. Verbatim capture first (the only
irreplaceable one), `SESSION.md` after the log entry it depends on, commit last.

## 0. Two checks before you start

- **`git status --short SESSION.md ROADMAP.md archive/PROJECT_LOG.md`** — if any is dirty from
  another window, stop and ask. `SESSION.md` is *replaced*, so rewriting over a concurrent
  edit discards real work silently.
- **`ls archive/handoffs/`** — if it holds files dated today you are in a `/backlog attack` run.
  Coordinator: consume them in steps 2–4, then delete them. Worker: **stop here** — run step 1
  only and write your handoff instead. Protocol: [backlog.md](backlog.md).

## 1. Verbatim transcript

```bash
python3 ~/.claude/tools/archive_chats.py
```

Idempotent; writes to `archive/transcripts/`. Report what it produced and move on. **Say
nothing about the tail** — this captures everything up to now, which is the intended result;
Mike has that reminder already and it fires on every run, so it distinguishes nothing.

## 2. **Append** one entry to `archive/PROJECT_LOG.md`

**At the top of the file** — directly under `## Dated history` (~line 23), above the current
newest entry. One `### <date> (<short title>)` section, ~20–40 lines:

- what changed and **why** — the reasoning, not the diff
- decisions made, and **options rejected with the reason**
- **anything believed true earlier that turned out wrong** — corrections are the highest-value
  content in this file
- commit hashes, and whether it deployed

Carry the outgoing `SESSION.md` handoff paragraph into this entry so the narrative stays
unbroken. **This file is only ever appended to.**

## 3. **Replace** the changed parts of `SESSION.md`

A snapshot, not a ledger. Rewrite the rolling handoff paragraph (~150 words — do not stack a
new one above the old). Move finished items out rather than marking them done. Add one row to
`## Recent sessions` and let the oldest drop. Delete what is now superseded.

**Ceiling: 200 lines.** A new blocker earning a line is fine; crossing 200 means dated detail
is accumulating here instead of in the log.

**Same pass:** if this session completed, split, or superseded anything `ROADMAP.md` tracks
(A7's checks, B1–B4, Track D), mark it there now — inline ✅ or a short note, not a rewrite.
Updating `SESSION.md` is not enough; that has been missed before.

## 4. `DEV_BACKLOG.md` — close, then file

**Close first.** List what this session touched (`git status --porcelain`, `git diff
--name-only` over its commits), grep the backlog for those filenames and for the symptom in
Mike's words, and read the surrounding item — an entry naming a file is often about a different
fault in it. Fully done → move it to `archive/backlog_closed_2026-08.md` with the commit or
`file:line` that closed it. Partly done → **stays open**, retitled to state what is left (built
but undeployed is open). Untouched → leave it alone; do not re-word an item because you read it.

**Then file — but only what clears the bar: a user would notice, or the roadmap is blocked.**
An incidental code nit is fixed on the spot or dropped, not filed. This is the whole reason the
list used to grow every session and shrink in none. New items get `DB-MMDD-NN` (derive the next
free number by grepping at write time, never reserve one) and a one-line provenance naming who
raised it.

Anything **Mike** asked for that was not done goes in `## Now`; everything else goes in
`## Later`, including a real bug this session found and could not fix. `## Now` is ranked, so
an item entering it is **put to Mike with a recommended position and the reasoning** — he makes
the call before the file is written, rather than it being appended and re-sorted later.

Then close with the count, and only the count:

```bash
python3 scripts/sync_dev_backlog.py
```

**Do not triage here.** `/archive` runs every session, and a bulk chore attached to it is how a
list stops being read. The count is the signal; `/backlog` is where a pass happens.

## 5. Commit the close-out

Stage an explicit manifest: `SESSION.md`, `archive/PROJECT_LOG.md`, `DEV_BACKLOG.md`,
`archive/backlog_closed_2026-08.md`, plus `ROADMAP.md` if step 3 touched it. Never `git add -A`,
never a glob. **`git diff` each file before staging** — two windows run against this tree, and
`git add <path>` stages that file's whole current content, a parallel session's uncommitted
lines included (CLAUDE.md § Deploy safety, rule 4). Then `git push origin main` — the offsite
backup, not a release. **Never `./deploy.sh` here.** A rejected push stops the step and gets
reported; pulling or merging to clear it entangles two sessions' work.

**Lines this session did not write stop the commit.** Name them, stage nothing: you cannot tell
your own edits from a parallel window's (`[DB-0805-05]`, open), so raising it is the step.

---

*Procedure only — incident history lives in `archive/PROJECT_LOG.md`. Ceiling ~100 lines (`CLAUDE.md`).*
