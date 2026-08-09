# Development Workflow — which command, when

Four commands. This page says which one to fire and what it costs. Read once; come back when
something feels like it needs a ritual and you can't remember which.

**The bias, stated once because everything below follows from it:** Metatron is being built as
fast as possible. Mike's bugs and requests outrank machine-generated findings, which outrank
things a development session noticed in passing. Process work that doesn't change what the user
experiences is not work.

---

## "I want to…"

| …start any session | `/metatron-code` |
| :--- | :--- |
| …diagnose a bad Metatron reply | `/metatron-troubleshoot DATE SEQ "what went wrong"` |
| …know what's outstanding, or pick something up | `/backlog` |
| …tidy a list that's drifting | `/backlog deep` |
| …use a day of parallel capacity | `/backlog attack` |
| …close a session | `/archive` |

Nothing else is a ritual. Ordinary coding is: `/metatron-code`, do the work, `/archive`.

---

## The commands

**`/metatron-code`** — the loader. Syncs the backlog (writes to disk, costs no context), then
reads `SESSION.md`, `ROADMAP.md`, and `CODEBASE_INDEX.md` if needed. Prints one count line and
nothing else. ~15k tokens. *The rule: it never opens `DEV_BACKLOG.md`. The count is the signal.*

**`/metatron-troubleshoot`** — one exchange, diagnosed. Takes a date and a SEQ, pulls the
conversation record, server logs and pipeline trace in a single SSH round-trip, and reports what
failed and what it meant for Mike. Cheap. *The rule: fix it here if you can and file nothing.*

**`/backlog`** — reads `DEV_BACKLOG.md` in full (~4k tokens), triages the Inbox into `Now` /
`Later` with Mike setting the tiers, and verifies anything about to be worked against current
code. *The rule: no item is acted on, or re-filed, on the strength of its own description.*

> **`## Now` is ranked — position is priority**, and each item is ranked **as it arrives**: put
> to Mike with a recommended position and the reasoning for it (who raised it, what it blocks,
> what it costs while it sits), and he makes the call. A bare "where does this go?" is as
> unhelpful as silently appending it — he assesses the recommendation, so there has to be one.
>
> **The entry bar is that Mike raised it** — a dev session finding a genuine user-visible bug
> files it to `## Later` however good the find is, and it is promoted the day Mike hits it. One
> exception, deliberately narrow: a live credential exposure or data-loss risk enters regardless
> of who found it. That asymmetry is what stops the list growing faster than it shrinks — a good
> find is not the same thing as a priority.

**`/backlog deep`** — the above plus merging overlapping items, verifying all of `Now`, sweeping
the machine log, and rolling closed items into `archive/backlog_closed_YYYY-MM.md`. Run when
counts creep or the file feels messy. Occasional; never scheduled.

**`/backlog attack`** — scores `Now`, clusters the top items into up to three groups with
**exclusive file manifests**, and emits a worker prompt per group. Planning only. *The rule:
workers never touch shared state and never deploy; this window consolidates.*

**`/archive`** — transcript, one `PROJECT_LOG.md` entry, `SESSION.md` refresh, backlog
close-and-file. Minutes, not a work block. *The rule: close before you file, and file only what
a user would notice or what blocks the roadmap.*

---

## What each file is for

| File | Holds | Written | Read |
|---|---|---|---|
| `SESSION.md` | current state, nothing dated | **replaced** | every session |
| `ROADMAP.md` | live phase gates and tracked items | edited inline | every session |
| `DEV_BACKLOG.md` | work outside the roadmap, in priority order | curated | `/backlog` only |
| `archive/PROJECT_LOG.md` | dated history, reasoning, rejected options, corrections | **appended** | on demand |
| `archive/backlog_closed_*.md` | closed items with their evidence | appended, monthly | on demand |
| `archive/transcripts/` | verbatim chat | by script | never |

The append/replace split is the whole point. History goes in the log; state goes in
`SESSION.md`; work goes in `DEV_BACKLOG.md`.

---

## A week that works

**Monday — ordinary session.** `/metatron-code` prints `0 new · 2 inbox · 9 now · 24 later`. Two
Inbox entries is not worth a pass. Build the feature Mike asked for in conversation. `/archive`:
transcript, one log entry, the handoff paragraph rewritten, the backlog item closed with its
commit. Five minutes. *Nothing was filed — the two nits found along the way were fixed on the
spot.*

**Tuesday — triage, then work.** Inbox is at five. `/backlog`: read the file, pull the two
user-reported entries back to the conversations they came from, propose tiers for all five in
one table. Mike says "1 and 3 to Now, kill 4, rest Later." Rewrite them into place, then verify
and work the top `Now` item. `/archive` at close.

**Wednesday — parallel day.** `/backlog attack` scores `Now` and produces three clusters:
app-client fixes, a scheduler gate-stack fix, and a test-suite gap. Manifests are disjoint —
`static/index.html`, `core/scheduler.py`, `tests/` — so all three can run. Three windows open,
each with its prompt. Workers ship, run the transcript script, and write
`archive/handoffs/2026-08-12-app-client.md` and friends. This window then runs `/archive` once,
folds all three handoffs into a single log entry and a single `SESSION.md` refresh, closes the
backlog items, and deploys **once**. *Nobody else touched a shared file, and nobody else
deployed — that is the entire protocol.*

**Thursday — something misbehaved.** The morning check-in listed four pending items again.
`/metatron-troubleshoot 2026-08-13 007 "check-in ignored the brevity rule"` pulls the trace and
shows the preference never reached the Synthesizer's prompt. One-file fix, deployed, backlog
item closed. **Filed nothing** — the fix exists, so there is nothing to remember.

**Friday — sweep.** Counts have drifted to `1 inbox · 11 now · 31 later` and the sync line
carries `⚠ machine: finance/search_memory ×4`. `/backlog deep`: merge two `Later` items that
were describing the same thing, verify all of `Now` and drop one that turned out to be fixed
weeks ago, promote the ×4 denial into `Later` (four attempts means the agent's instruction file
genuinely expects that tool), and roll eight closed items into the monthly archive. Back to
`0 inbox · 10 now · 26 later`.

---

## Three failure modes, and what stops each

**The list grows faster than it shrinks.** Cause: every session filed everything it noticed.
Stopped by `/archive` step 4 — close before you file, and the bar for filing is *a user would
notice, or the roadmap is blocked.*

**Machine noise crowds out Mike.** Cause: tool denials and rule conflicts landed in the same
Inbox as his requests, five copies of one complaint reading as five items. Stopped by routing:
runtime signals go to `## Machine log`, repeats collapse to `×N`, and a signature reaching ×3
escalates itself into the count line.

**Parallel windows collide.** Cause: disjoint code, shared close-out — every window ran
`/archive` and edited the same three files, and once a window's commit swept up another's
uncommitted work. Stopped by the coordinator/worker split: one window owns shared state and the
deploy; workers write a handoff file. `/archive` step 0 checks for both dirty shared files and
today's handoffs before it does anything.

---

## Standing conventions

- **Command files carry procedure, not history.** An incident lesson goes to
  `archive/PROJECT_LOG.md`, not into the command that hit it. `/archive` reached 196 lines that
  way, most of it scar tissue nobody needed at close-out time.
- **Closed without evidence is not closed** — a commit, a `file:line`, or a named test.
- **Never reserve a backlog ID.** Grep for the next free `DB-MMDD-NN` at the moment of writing;
  two windows have minted the same one more than once.
- **Report counts as a before/after diff**, not a bare number. With two windows open, any single
  count is a snapshot of an unknown moment — a real 53 → 48 once read as a regression to 48.
