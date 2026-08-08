---
description: Close out a session — verbatim transcript, project-log entry, session writeup, SESSION.md refresh, ROADMAP.md refresh, backlog filing
---

Metatron — Archive This Session

Six steps. **Do all six.** The order matters: the verbatim capture runs first because it is
the only irreplaceable one, and `SESSION.md`/`ROADMAP.md` are rewritten last because they depend
on what the log entry says.

> **Steps 4 and 5 are two different documents — do not do one and assume it covers the other.**
> `SESSION.md` is a snapshot of *current state*; `ROADMAP.md` is the live tracker for *phase
> gates and tracked items* (A7's checks, Track B's B1–B4, Track D). A session can update one and
> leave the other describing finished work as if it hadn't started — this has already happened
> (2026-08-04: B1a ran and passed, `SESSION.md` and `DEV_BACKLOG.md` both said so, `ROADMAP.md`'s
> B1 section still read as if nothing had run). **Check both, every time, especially when
> something tracked in either one got completed, split, or superseded this session** — that's
> the case most likely to get skipped, because updating `DEV_BACKLOG.md` or `SESSION.md` already
> feels like "the update."

---

## 1. Verbatim transcript (irreplaceable — do this first)

```bash
python3 ~/.claude/tools/archive_chats.py
```

This is the canonical copy — it auto-detects the project root and writes to
`archive/transcripts/`. A second, older copy lived at `tools/archive_chats.py` until
2026-08-03; the two disagreed while writing to the same directory, so it was deleted. If you
find a `tools/archive_chats.py` again, something has been restored by mistake.

It is idempotent — already-archived sessions are skipped, and a session already captured is
re-emitted as `updated` if it has grown.

> **This cannot capture its own tail.** The current session's JSONL is live and incomplete
> until the session ends, so a run now produces a partial capture. That is expected, not a
> failure. Re-run after closing for the complete archive.

---

## 2. **Append** to `archive/PROJECT_LOG.md`

Newest first, directly under `## Dated history`. One `### <date> (<short title>)` section with:

- what changed, and **why** — the reasoning, not just the diff
- decisions made, and **options rejected with the reason** (this is the part nothing else records)
- **anything believed true earlier that turned out to be wrong** — corrections are the highest-value content in this file
- commit hashes and whether it deployed
- a link to the session writeup from step 3

Also move the outgoing rolling-handoff paragraph from `SESSION.md` into this entry, so the
narrative thread stays unbroken here.

**This file is only ever appended to.** Never rewrite or prune it.

---

## 3. Session writeup — `archive/sessions/YYYY-MM-DD — Title.md`

Create or update. The title must distinguish it from other sessions the same day — there are
often several. Scannable work log: what was built, decisions, deferred items. Not prose.

If you have been following the standing rule, this file already exists from early in the
session; update it rather than starting over.

---

## 4. **Replace** the changed parts of `SESSION.md`

`SESSION.md` is a **snapshot, not a ledger.**

- **Rewrite** the rolling handoff paragraph at the top. Do not stack a new one above the old.
  ~150 words. Carry forward what is mid-flight and any correction to what a previous session
  believed.
- **Update** the current-state section — move finished items out, not just mark them done.
- **Add one row** to the `## Recent sessions` table and let the oldest row drop off.
- **Delete** anything now superseded. The detail is in the log; leaving it here is what grew
  this file to 775 lines.

> **Check the line count: the ceiling is 200.** A session that adds a genuine new blocker *should*
> make this file slightly longer — do not pare it back to hit an arbitrary number. But if it is
> over 200, dated detail has accumulated here that belongs in the log.

---

## 5. Update `ROADMAP.md` if this session touched anything it tracks

`ROADMAP.md` is edited, not append-only (unlike `PROJECT_LOG.md`) and not a snapshot you rewrite
wholesale (unlike `SESSION.md`) — it's the live status of phase gates and tracked items: A7's
sign-off checks, Track B (B1–B4), Track D, and anything else the file currently carries in full.
**If this session completed, split, or superseded anything ROADMAP.md describes, update it
here — do not rely on `SESSION.md` or `DEV_BACKLOG.md` having said so being enough.** Ask
explicitly:

- Did a check, sub-item, or whole tracked item (e.g. one of A7's 12 checks, one of B1–B4) get
  completed, split into parts, or found to already be done this session?
- Does the roadmap's own wording still match reality, or does it read as if the work is still
  ahead when it isn't?

**Especially check this when something is being marked done or removed from `DEV_BACKLOG.md`** —
a completed backlog item that traces back to a roadmap-tracked item needs the roadmap updated in
the same pass, not left for a future session to notice the mismatch.

Mark status inline rather than rewriting the section — a ✅/short note/link to the session or log
entry, the way A7's pre-sign-off gate note already does elsewhere in this file. Keep the
roadmap's own abridgement discipline: dated reasoning belongs in `PROJECT_LOG.md`, not restated
here. If nothing this session touches is in `ROADMAP.md` at all, say so and move on — this step
is a check, not a mandatory edit.

---

## 6. File anything actionable into `DEV_BACKLOG.md`

Bugs found but not fixed, deferrals, capability gaps, and any change the user asked for that
was not done. Check it is not already listed before adding.

**An item recorded only in a session narrative will be lost.** That has already happened once —
the unsurfaced-opportunity instrumentation item lived only in `SESSION.md` prose and, in its own
words, "nearly aged out."

Give each new item an ID and a provenance line — `DB-MMDD-NN`, who filed it and how, the origin
SEQ if it came from a conversation. Format and rationale: [backlog.md](backlog.md).

Then close with the count, and **only** the count:

```bash
python3 scripts/sync_dev_backlog.py
```

Report the `N new · N untriaged · N open` line as-is. **Do not triage here** — `/archive` runs
every session and a bulk chore attached to it is how a list stops being read. The count is the
signal; `/backlog` is where a pass happens, when Mike decides one is worth it.

---

## Note on this file's backup status

Slash commands **are** version-controlled: `.gitignore` ignores `.claude/*` and
`.claude/commands/*` but then re-includes `!.claude/commands/*.md`, so this file and its
siblings are tracked and reach GitHub normally. Just remember to `git add` a new one.

Everything *else* under `.claude/` — `settings.local.json`, the hooks — is genuinely ignored and
has no backup. (Several older notes state that `.claude/` is ignored "entirely" and that these
commands are unbacked. That was true before the negation was added; it is not true now.)
