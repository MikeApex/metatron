Metatron — Work the Development Backlog

`DEV_BACKLOG.md` is the single bin for everything that arises outside the roadmap. Two feeds
reach it: Mike in conversation (recorded by the Synthesizer on the VM, pulled down by the sync
script) and development sessions filing what they find. This command is how the bin gets
emptied.

Run it when picking up backlog work, triaging the Inbox, or answering "what's actually
outstanding." Not needed for ordinary coding — there the task comes from the user, not the list.

---

## 1. Sync

```bash
python3 scripts/sync_dev_backlog.py
```

Reports `N new · N untriaged · N open`. Writes to disk, costs no context. Exits 0 silently when
the VM is stopped — expected, not a failure.

**The three numbers mean different things.** *New* arrived this run. *Untriaged* is sitting in
`## Inbox` — machine-written, never hand-edited, and it is a queue, not a backlog. *Open* is
curated work below Inbox. A rising untriaged count means the bin is filling faster than it is
emptied; a rising open count means real work is accumulating. They are not interchangeable and
the script no longer conflates them.

## 2. Read the file

Read `DEV_BACKLOG.md` in full. It is deliberately outside the default session load, so this is
the point at which it enters context.

## 3. Triage the Inbox

Every `## Inbox` entry goes somewhere. Do not leave a queue behind.

Machine-written entries carry a type. `TOOL_DENIED` means an agent reached for a tool it was not
granted — **read the agent's instruction file before deciding**, because the file is a
specification written ahead of the tools and an attempt is usually evidence of designed intent,
not overreach. Group by (agent, tool); nine entries have collapsed to six cases before now.

**For anything user-reported, find the exchange it came from.** The denial or request text says
*what* was blocked, never *what the agent or user was trying to do*, and the difference has
inverted a decision at least once. The timestamp is in the entry; conversations are on the VM:

```bash
# /monitor/conversations?persona=mike&since=ISO&limit=N — see scripts/sync_dev_backlog.py
# for the auth pattern (core.auth.bearer_header, stdlib only).
```

Note the offset: quality-event timestamps are **UTC**, conversation `ts` is **VM-local**.

Rewrite the entry properly into an Open section or into `## Done`, and delete it from Inbox.

## 4. Verify before re-filing — this is the part that matters

> **No item keeps its place on the strength of its own description.**

Open every item against the current code before deciding it is real. On 2026-08-05 roughly a
third of what was checked did not survive: causes already fixed, cited functions that no longer
exist, line numbers several hundred lines stale. Two entries in this file's own history were
written from a plausible re-reading and had to be withdrawn.

A stale premise does not merely waste the time spent on it — **it argues for the wrong decision,
persuasively.** On 2026-08-05 a stale line ("no tool to add a scheduler job", true until
2026-08-03) produced a well-reasoned recommendation to hold a grant pending work that had
already shipped two days earlier.

Four verdicts:

| Verdict | Action |
|---|---|
| **Fixed** | Move to `## Done` **with the commit or `file:line` that closed it**. Closed without one is not closed. Never delete — an item that resurfaces must show it was checked once. |
| **Real** | Keep. Add the evidence it is still real: what you checked, where, today. |
| **Drifted** | Symptom may survive, cited code has moved. Keep, but repoint at today's location or mark `needs re-derivation` and say what to reproduce. **Never carry a stale line number forward.** |
| **Needs a decision** | Collect into one place and ask once, rather than interrupting per item. |

**Runtime claims need the journal, not the code.** "Fails on every scheduler job", "fires twice
a day", "falls back on every request" cannot be settled by reading — an error can persist
despite correct-looking code, and code can look broken while nothing hits the path. One SSH
round-trip answers several at once:

```bash
gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 \
  --tunnel-through-iap --command="sudo journalctl -u metatron-server -u metatron-scheduler \
  --since '7 days ago' --no-pager | grep -c 'PATTERN'"
```

Beware near-misses: on 2026-08-05 eleven `[vertex_cache]` warnings looked like a filed 404 bug
and were `NameResolutionError` from an unrelated outage.

## 5. ID and provenance

Every curated item carries an ID and a provenance line:

```markdown
- **[DB-0803-07] ⚠ `deploy.sh`'s drain is decorative**
  *filed 2026-07-30 by dev session (client/app audit) · recovered from SESSION.md:317
  2026-08-03 · verified 2026-08-05 against core/server.py:433,600,721*
```

- **`DB-MMDD-NN`** — dated from filing, sequential within that date, **never reused**, kept by
  closed items. Positional references (`#7`, `#19`) are not usable across chat windows: they
  shift the moment anything is added or triaged, and have already caused ambiguity.
- **filed … by …** — `Mike via Synthesizer`, `warn-mode tool denial`, `daily rule audit`, or
  `dev session (Claude Code)` with a clause on what was being done at the time. This is the
  field that answers "why did the list grow" later.
- **origin SEQ** — the per-day conversation id, which `/metatron-troubleshoot` takes, so a
  conversation-sourced item is re-openable against the exchange that produced it. `—` if it did
  not come from a conversation.
- **verified** — date plus what was checked. Where no filing date is recorded, say so rather
  than inventing one.

## 6. Close out

Re-run the sync and confirm the count moved the way you expect. Then check:

```bash
# Duplicate ids — expect nothing. Anchored to the leading bullet so that a
# cross-reference to another item ("see [DB-0805-01]") is not read as a second
# definition of it; the unanchored form false-positives on every cross-reference.
grep -o "^- \*\*\[DB-[0-9-]*\]" DEV_BACKLOG.md | grep -o "DB-[0-9-]*" | sort | uniq -d
```

If code changed, note whether it needs `./deploy.sh` (anything under `core/`, `config/`,
`tools/`) and whether a parallel window owns the file.

---

## What this command does not do

It does not work the whole backlog. Triage a batch, or the Inbox, or one item — the count at
session start and close is the signal for when a pass is worth it, and that decision is Mike's.
`/metatron-code` and `/archive` report the count and nothing more, deliberately: a recurring
bulk chore is how a list stops being read at all.
