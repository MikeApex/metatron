### 2026-08-15 (`/archive` gets a lean path, and step 4 stops editing ranked sections) — `859ec3a`, docs/scripts only, **not deployed**

Mike asked which parts of `/archive` are superseded by `/fix`, `/metatron-troubleshoot` or the
`/backlog` cluster — and when a leaner close-out is the right call instead. The audit read all
five command files against `docs/WORKFLOW.md`.

**Most of `/archive` is not contested.** Steps 1–3 have no overlap: nothing else captures a
transcript, writes an `archive/log/` fragment, or touches `SESSION.md`. Step 5's `git push` is
the one people miss — **`/fix` commits but never pushes**, so `/archive` is the only offsite
path in the workflow. A day of `/fix` runs with no close-out leaves everything local, which is
the 2026-08-13 eleven-commit gap the step's own assertion block exists to catch.

**Two real faults, both fixed here.**

**1. Step 4 had drifted behind its own machinery.** It said to mint `DB-MMDD-NN` and write
straight into `## Now`/`## Later`, with a `## Now` entry put to Mike for ranking. But
`.claude/backlog_inbox/<slug>.md` has existed since 08-14 and `sync_dev_backlog.py:576` folds
those fragments into `## Inbox` — the route `docs/WORKFLOW.md` § Standing conventions and
`SESSION.md` both already state. Step 4 now files a fragment. This restores the collision
property step 2 already had and step 4 lacked: two windows closing out at once cannot mint the
same id or edit the same ranked section. Ranking moves to `/backlog`, which is the right place
on its own merits — ranking an item at close-out asks Mike to weigh it against nine items
nobody currently has open.

**2. `/archive` was mandated unconditionally for sessions where three of its five steps are
no-ops.** `docs/WORKFLOW.md` says "every session, without exception," but a session that only
read — a question answered, a `/metatron-troubleshoot` that diagnosed nothing, a `/backlog`
pass that only proposed — has nothing true to put in a fragment, and step 3 pays to re-decide a
handoff paragraph that is still correct. Step 0 gained a first check: clean tree *and* no
commits → run step 1, report, stop.

**Rejected: a separate leaner `/close` command.** It would be a second standing skill needing
sync with `/archive`, which is the *One Home Per Rule Class* failure and is also barred by the
standing "no new machinery without naming what it retires" rule. Making the lean path an
outcome of step 0 keeps "run `/archive` every session" literally true — worth preserving,
because the step that would get skipped by an unwritten exception is the transcript, the only
irrecoverable one.

**Ceiling raised 100 → 150** (Mike's decision, asked for directly). The file had been over
continuously since 08-13 — 124, then 140, then 147 — a standing WARN nobody could clear, which
is exactly the "teaches the reader to skip the output" failure the `CLAUDE.md` ceiling note
already describes and the reason `CLAUDE.md` itself went to 300. The alternative offered was
moving step 5's incident narrative (the eleven-commits-behind story, ~15 lines) to `archive/log/`
and keeping the assertion block; Mike chose the ceiling. `archive.md`'s footer now points at
`CEILINGS` rather than restating a number, which is how it went stale before — it cited "~100
lines (`CLAUDE.md`)" while `CLAUDE.md` no longer carried the figure.

**Believed true earlier, wrong:** that `/archive` step 4 and `/backlog` merely overlapped in
scope. They had diverged in *mechanism* — one wrote a file the other's sync was already
generating — and the drift was invisible because both descriptions were individually coherent.

**Not acted on:** `[DB-0810-06]` (ceilings measured in lines have stopped tracking cost) sits in
`## Later` and is directly upstream of this ceiling change; surfaced by the write-time briefing,
left open deliberately. `DEV_BACKLOG.md` remains over its own ceiling at 792/450 — pre-existing,
and a `/backlog deep` sweep of `## Machine log` is still owed.

