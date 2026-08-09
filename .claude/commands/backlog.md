---
description: Work DEV_BACKLOG.md — triage the Inbox and pick work; `deep` for a clustering sweep, `attack` for parallel work prompts
---

Metatron — Work the Development Backlog

Three modes. Default is a triage pass; `$ARGUMENTS` selects the others.

| Mode | When |
|---|---|
| *(default)* | Picking up work, triaging the Inbox, answering "what's actually outstanding" |
| `deep` | Counts creeping, items overlapping, machine log unswept — occasional, not scheduled |
| `attack` | A day of parallel capacity: cluster `## Now` into independent single-session prompts |

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

**3. Verify only what is about to be worked.**

> **No item is acted on, or re-filed, on the strength of its own description.**

Open it against current code. On 2026-08-05 roughly a third of what was checked did not survive
— causes already fixed, cited functions gone, line numbers hundreds of lines stale. Verdicts:
**fixed** → move to `archive/backlog_closed_2026-08.md` with the commit or `file:line`;
**real** → note what you checked and when; **drifted** → repoint at today's location, never
carry a stale line number forward; **needs a decision** → collect and ask once.

**Runtime claims need the journal, not the code.** "Fails on every scheduler job", "fires twice
a day" cannot be settled by reading — one SSH round-trip answers several at once:

```bash
gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 \
  --tunnel-through-iap --command="sudo journalctl -u metatron-server -u metatron-scheduler \
  --since '7 days ago' --no-pager | grep -c 'PATTERN'"
```

Beware near-misses: eleven `[vertex_cache]` warnings once looked like a filed 404 bug and were
`NameResolutionError` from an unrelated outage.

**4. Close out.** Re-run the sync and confirm the count moved the way you expect. Check for
duplicate ids — expect nothing:

```bash
grep -o "^- \*\*\[DB-[0-9-]*\]" DEV_BACKLOG.md | grep -o "DB-[0-9-]*" | sort | uniq -d
```

If code changed, note whether it needs `./deploy.sh` (`core/`, `config/`, `tools/`).

---

## `deep` — the periodic sweep

Everything above, plus the maintenance a default pass deliberately skips:

- **Cluster and merge.** Read `## Later` for items describing the same underlying thing and
  merge them into one, keeping both reasoning trails. Overlapping entries are how a list gets
  argued over twice — three merges happened in the 2026-08-09 rebuild alone.
- **Verify every `## Now` item**, not just the ones about to be worked.
- **Sweep `## Machine log`.** Promote anything user-impacting; leave the rest collapsed.
- **Roll closed items** into `archive/backlog_closed_YYYY-MM.md`, starting a new file each month.
- **Check the shape:** `DEV_BACKLOG.md`'s ceiling is ~250 lines (the `CLAUDE.md` figure). Past
  it, narrative is accumulating again — the detail belongs in the code, the log, or the archive.

---

## `attack` — parallel work prompts

Planning only. Produce a scored list and up to three independent single-session prompts; do not
fix anything in this pass.

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

**Then hand out prompts carrying this protocol verbatim, because the collisions were never in
the code — they were in the close-out:**

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

Stop after presenting the prompts and ask which to run.

---

*Procedure only — under ~130 lines (the `CLAUDE.md` ceiling). What each collision cost and why
the protocol looks like this: `archive/PROJECT_LOG.md` § 2026-08-08 and § 2026-08-09.*
