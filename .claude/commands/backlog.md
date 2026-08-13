---
description: Work DEV_BACKLOG.md — triage the Inbox and pick work; `verify` to re-check items against current code, `deep` for a clustering sweep, `attack` for parallel work
---

Metatron — Work the Development Backlog

Four modes. Default is a triage pass; `$ARGUMENTS` selects the others.

| Mode | When |
|---|---|
| *(default)* | Picking up work, triaging the Inbox, answering "what's actually outstanding" |
| `verify` | Re-checking items against current code — fanned out to workers, returns one verdict table |
| `deep` | Counts creeping, items overlapping, machine log unswept — occasional, not scheduled |
| `attack` | A day of parallel capacity: cluster `## Now` into independent workers |

Not needed for ordinary coding — there the task comes from Mike, not the list.

---

## Default pass

**1. Sync and read.** `python3 scripts/sync_dev_backlog.py`, then read `DEV_BACKLOG.md` in full
(it is deliberately outside the default session load). The count line is
`N new · N inbox · N now · N later`, plus `⚠ machine:` when a runtime signature has recurred
three times or more — that ⚠ is the only reason to open `## Machine log` on a default pass.

**2. Triage the Inbox — every entry goes somewhere.** For anything user-reported, find the
exchange it came from: the request text says *what* was asked, never *what Mike was trying to
do*, and that difference has inverted a decision at least once. Timestamps are in the entry;
conversations are on the VM (`/monitor/conversations?persona=mike&since=ISO&limit=N` — auth
pattern in `scripts/sync_dev_backlog.py`). Note the offset: quality-event timestamps are **UTC**,
conversation `ts` is **VM-local**.

**Propose a tier per entry in one numbered table — `## Now`, `## Later`, or close — and let Mike
set them.** One interaction for the batch, not one per item. Then rewrite each entry properly
into its section and delete it from Inbox.

`## Now` is capped at ~10 and **ranked: position is priority**. **When an item reaches `## Now`,
put it to Mike with a recommended rank and the reasoning for it** — how relevant it is against
what is already there: who raised it, what it blocks, what it costs the user while it sits. He
makes the assessment; the recommendation is what he assesses against, so a bare "where does this
go?" is as unhelpful as silently appending it. **The ranking is decided as each item arrives**,
not inferred later or left to sort itself out.

**The entry bar is that Mike raised it** — a dev-session find goes to `## Later` however good it
is, and is promoted the day he hits it. Narrow exception: a live credential exposure or
data-loss risk enters regardless of who found it. **State the reporter with every
recommendation** — "this is a real bug" is not the same claim as "Mike asked for this."

**3. Verify only what is about to be worked** — inline for one or two items, or run `verify`
below for a batch. Either way the rule and the verdicts are the same:

> **No item is acted on, or re-filed, on the strength of its own description.**

**4. Close out.** Re-run the sync and confirm the count moved the way you expect. Check for
duplicate ids — expect nothing:

```bash
grep -o "^- \*\*\[DB-[0-9-]*\]" DEV_BACKLOG.md | grep -o "DB-[0-9-]*" | sort | uniq -d
```

If code changed, note whether it needs `./deploy.sh` (`core/`, `config/`, `tools/`).

---

## `verify` — re-check items against current code

**The best fan-out target in the project**, because verification is read-only, self-contained,
and embarrassingly parallel. On 2026-08-05 roughly a third of what was checked did not survive —
causes already fixed, cited functions gone, line numbers hundreds of lines stale. **You see a
verdict table, not ten investigations.**

`$ARGUMENTS` names the items; bare `verify` takes all of `## Now`. **Cap: 10 items.**

**First screen for checkability, then split.** An item a worker *cannot* reach is not a small
item, it is an unanswerable one, and a worker handed it will flail — burning a full briefing to
report that it could not look. Keep in this window anything needing VM traces, journal output or
a live session (`[DB-0810-13]` is the standing example: specialists reporting actions they never
took, answerable only from traces on the VM). Split only what is settleable by reading the tree.

**Then scope each worker in advance, with a cost estimate.** The target is one optimal context
lifetime per worker: enough items that the briefing is amortised, few enough that it is not still
reading at 100k. Estimate from measured medians — `python3 scripts/worker_ledger.py` reports
them, and they are per-model:

| Model | Median run | n | Use for |
|---|---|---|---|
| `haiku` | ~32k | 4 | mechanical checks — does this symbol still exist, is this line number current |
| `sonnet` | ~59k | 1 | ordinary verification: read the code, form a verdict |
| *inherited* | ~64k | 8 | items needing judgement about what a failure means |

**Batch across at most 3 workers — do not spawn one per item.** The floor is ~30k before a
worker reads anything, so ten workers is ~300k spent on ten briefings. State the estimate per
worker before dispatching: *items × expected cost*, from the row you are actually dispatching.
The flat ~32k this section used to assert was wrong in both directions — it matched the
mechanical probes and nothing else, and the worst observed run is 108,792.

Dispatch: `Agent(model: "sonnet", subagent_type: "general-purpose")`, **no `isolation` flag** —
it checks workers out from `origin/main`, not local `HEAD`. Verification is read-only, so these
workers need no worktree; they read the main tree.

**After the run, record actual against estimate** — one line, so the medians calibrate instead of
ossifying: `python3 scripts/worker_ledger.py --session <id>`, then note the variance in the
close-out. An estimate never checked against an outcome is the flat-32k failure again, slower.

The brief must carry, because a worker starts cold:

- **the full text of each item it owns** — it cannot see `DEV_BACKLOG.md`'s context
- **read-only, and say it plainly: edit nothing, commit nothing, run nothing that writes.**
  Nothing enforces this — `qa_sweep.sh` checks seven specific things, not tree cleanliness, and
  the `SubagentStop` gate excludes the main tree from its dirty-worktree sweep. The prohibition
  in the brief is the whole control.
- per item, one of four verdicts **with its evidence**: **fixed** (commit or `file:line`) ·
  **real** (what was checked, and where) · **drifted** (today's location) · **needs a decision**
- that a tool named in an agent file is a *specification*, not a bug to delete

**Runtime claims need the journal, not the code** — "fails on every scheduler job", "fires twice
a day". Workers do not SSH; collect those and run one round-trip here — the invocation and its
near-miss warning are in [docs/INFRASTRUCTURE.md](../../docs/INFRASTRUCTURE.md) § Service
management.

**This window owns every write.** Workers report; you move items to
`archive/backlog_closed_2026-08.md` with their evidence, repoint drifted line numbers, and put
the decisions to Mike in one batch. A verdict without a `file:line`, commit or named test is a
description, and descriptions are what the standing rule distrusts — send it back rather than
recording it.

---

## `deep` — the periodic sweep

Everything above, plus the maintenance a default pass deliberately skips:

- **Cluster and merge.** Read `## Later` for items describing the same underlying thing and
  merge them into one, keeping both reasoning trails. Overlapping entries are how a list gets
  argued over twice — three merges happened in the 2026-08-09 rebuild alone.
- **Verify every `## Now` item**, not just the ones about to be worked — this is `verify` above,
  run over the whole list. Fanning it out is what makes `deep` cheap enough to run when counts
  drift, rather than a day of serial reading.
- **Sweep `## Machine log`.** Promote anything user-impacting; leave the rest collapsed.
- **Roll closed items** into `archive/backlog_closed_YYYY-MM.md`, starting a new file each month.
- **Check the shape:** `DEV_BACKLOG.md`'s ceiling is the figure in `CLAUDE.md` § *Which File
  Holds What* — read it there rather than trusting a number repeated here. Past
  it, narrative is accumulating again — the detail belongs in the code, the log, or the archive.

---

## `attack` — parallel work

Score, cluster, show Mike the plan, then **spawn the workers yourself** once he approves. Show
the cluster plan first — he still decides what runs — but do not make him the transport layer
for prompts you just wrote.

**Work `## Now` only, and take its order as given** — that ranking is Mike's, so do not re-derive
importance or reorder against your own judgement. Score each item for **ease only** (1–10, 10 =
easiest) to decide what fits one session: anything touching routing, persona identity, or the
scheduler gate stack is ≤3 regardless of line count. Where ease forces a departure from rank —
a top item too large to fit — **say so explicitly** rather than quietly promoting an easier one.
Then verify the shortlist against current code (step 3 above) before it may enter a cluster.

**Cluster into at most three groups, each with an exclusive file manifest.** Code, config *and*
test files, cross-checked across groups. **A cluster that cannot be given a disjoint manifest is
not parallelised** — it runs serially in this window instead. Flag any VM-owned files
(`config/personas/**`) explicitly; those need the scp discipline, not a normal edit.

**Then, per approved cluster: dispatch exactly as `/fix` step 3 does** — worktree first via
`./scripts/new_worktree.sh <slug>`, no `isolation` flag, absolute path in the brief. That step
owns the mechanics and the reasons behind each one; it is not restated here, because a rule kept
in two files is edited in one (`CLAUDE.md` § One Home Per Rule Class). The only addition for a
cluster is that **each worker gets its own worktree**, one per manifest.

**Each prompt carries this protocol verbatim, because the collisions were never in the code —
they were in the close-out:**

> You are a **worker**. Do not edit `SESSION.md`, `archive/PROJECT_LOG.md`, `DEV_BACKLOG.md`,
> `ROADMAP.md`, or `.claude/commands/*`. Do not run `/archive` and do not run `./deploy.sh`.
> Work only the files in your manifest. When done, run
> `python3 ~/.claude/tools/archive_chats.py`, then write `archive/handoffs/YYYY-MM-DD-<slug>.md`
> — about ten lines: what shipped, commits, which backlog items to close and with what evidence,
> and anything `SESSION.md` must carry. Commit only your manifest files, and check
> `git log --oneline -3` afterwards to confirm the commit was not a no-op.

**This window is the coordinator.** When the workers finish, run `/archive` once, folding every
handoff into the single log entry, the `SESSION.md` refresh, and the backlog close — then delete
the consumed handoffs. **One deploy, owned by you, after consolidation.**

Present the cluster plan and ask which to run. Then spawn them — the asking is the gate, not the
hand-off.

---

*Procedure only. **196 lines against the ~200 recorded in `CLAUDE.md`** — raised from ~130 on
2026-08-13, after the fourth mode (`verify`) and its scoping step. That is growth by capability,
not narrative creep: the same pass moved the dispatch block to `/fix` § 3 and the `journalctl`
invocation to `docs/INFRASTRUCTURE.md`, and the file still grew. What each collision cost and
why the protocol looks like this: `archive/PROJECT_LOG.md` § 2026-08-08 and § 2026-08-09.*
