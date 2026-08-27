---
description: Close out a session — verbatim transcript, one project-log entry, SESSION.md refresh, backlog close-and-file
---

Metatron — Archive This Session

Five steps, in order — minutes, not a work block. Verbatim capture first (the only
irreplaceable one), `SESSION.md` after the log entry it depends on, commit last.

## 0. Three checks before you start

- **Did this session change anything?** If `git status --porcelain` is clean of tracked files
  *and* this session made no commits, run **step 1 only**, report the transcript, and stop.
  Steps 2–5 have nothing true to say about a read-only session, and step 1 is never skipped
  with them — the transcript is the only step that cannot be recovered afterwards.
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

## 2. Write **one fragment**, then regenerate `archive/PROJECT_LOG.md`

**Never hand-edit `archive/PROJECT_LOG.md` — it is GENERATED** by
`scripts/build_project_log.py` from `archive/log/`, and an edit there is silently discarded by
the next build. *(This step said "append at the top of the file" until 2026-08-14, three
sessions after the file became generated.)* Write:

```
archive/log/YYYY-MM-DD-NN-<slug>.md      # NN = next free number that date
python3 scripts/build_project_log.py     # regenerate; qa_sweep runs --check
```

One `### <date> (<short title>)` heading, ~20–40 lines, and **the fragment owns its trailing
blank line**:

- what changed and **why** — the reasoning, not the diff
- decisions made, and **options rejected with the reason**
- **anything believed true earlier that turned out wrong** — corrections are the highest-value
  content in this file
- commit hashes, and whether it deployed

Carry the outgoing `SESSION.md` handoff paragraph into the fragment so the narrative stays
unbroken. **One file per session is the whole point** — unique filenames cannot collide, so two
windows closing out at once produce two fragments rather than one merge conflict.

## 3. **Replace** the changed parts of `SESSION.md`

A snapshot, not a ledger. Rewrite the rolling handoff paragraph (~150 words — do not stack a
new one above the old). Move finished items out rather than marking them done. Delete what is
now superseded. **Do not recreate `## Recent sessions`** — removed 2026-08-26; step 2 covers it.

**Edit the volatile sections only** — the handoff paragraph and `## Current state`. `## Read
these`, `## Useful context`, `## Quick start` and `## Model IDs` are reference: leave them
closed unless this session made one of them *wrong*. Re-deciding static content every run is
what made this step expensive.

**A rule that has been promoted does not stay here** — once something is written into
`CLAUDE.md`, `ROADMAP.md` or a `docs/` file, cut it and leave the pointer. Same rule `CLAUDE.md`
applies to persona files, turned on the primer. Likewise anything with a `[DB-…]` id: carry the
id and a one-line status, never the evidence, which `DEV_BACKLOG.md` holds in full.

**Ceiling: 200 lines — but the number to watch is the volatile part.** Both come from
`python3 scripts/check_claude_md_claims.py`, run it directly: these are warnings, and
`qa_sweep.sh` prints a passing check's output only under `--verbose`. A primer pinned at its
ceiling is not stable, it is one where each session pays to argue a line out to let a line in.
Crossing either budget means move a *section* out, not trim a sentence. *(Why, and the 08-14
pass that set it: `archive/PROJECT_LOG.md`.)*

**Same pass:** if this session completed, split, or superseded anything `ROADMAP.md` tracks
(A7's checks, B1–B4, Track D), mark it there now — inline ✅ or a short note, not a rewrite.
Updating `SESSION.md` is not enough; that has been missed before.

## 4. `DEV_BACKLOG.md` — close, then file

**Close first, and run the scan — do not do this by grep:**

```bash
python3 scripts/backlog_close_scan.py
```

It ranks `## Now`/`## Later` against this session's diff and prints the evidence. **Read every
candidate against the diff** — the scan only decides what to read; an entry naming a file is often
about a different fault in it. Fully done → move to `archive/backlog_closed_2026-08.md` with the
commit or `file:line`. Partly done → **stays open**, retitled to what is left (built but undeployed
is open). Untouched → leave it; do not re-word an item because you read it. *(Replaced a filename
grep 2026-08-18 — it only found items that *name a file*, missing incidental closures entirely.
Worked example: the script's docstring.)*

**Then file — but only what clears the bar: a user would notice, or the roadmap is blocked.**
An incidental code nit is fixed on the spot or dropped, not filed. This is the whole reason the
list used to grow every session and shrink in none.

**File as a fragment: `.claude/backlog_inbox/<slug>.md`**, with a one-line provenance naming who
raised it. The sync folds it into `## Inbox`, so no id is minted here and no ranked section is
edited — two windows closing out cannot collide, the same reason step 2 writes a fragment.
Whether **Mike** raised it is the note that decides `## Now` versus `## Later` — but **`/backlog`
makes that call, with the list open.** Ranking here asks him to weigh an entry against nine items
nobody is currently looking at.

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

**Then assert the push landed — do not infer it from the command having run:**

```bash
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] && echo "offsite: ok" || \
  echo "OFFSITE FAILED — local ahead of origin/main by $(git rev-list --count origin/main..HEAD)"
```

*"I ran the push"* and *"the commits are offsite"* are not the same claim, and only the loud
failure was ever handled — `origin/main` once sat 11 commits behind local, one of them an
`Archive:` commit, so this step had silently lost its push more than once. Full cost:
`archive/PROJECT_LOG.md` § 2026-08-13.

**Lines this session did not write stop the commit.** Name them, stage nothing: you cannot tell
your own edits from a parallel window's (`[DB-0805-05]`, open), so raising it is the step.

---

*Procedure only — incident history lives in `archive/PROJECT_LOG.md`. Ceiling: `CEILINGS` in
`scripts/check_claude_md_claims.py` (150 as of 2026-08-15), which is the authority — do not
restate the number anywhere else.*
