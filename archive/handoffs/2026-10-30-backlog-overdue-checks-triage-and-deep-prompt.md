Model: Opus 5.5. This is a coordinating session: it adjudicates verdicts, puts rulings to Mike and owns every write. Any fan-out workers run on Sonnet.

/metatron-code /backlog

You are clearing old and overdue items out of `DEV_BACKLOG.md`. Work in this order. Pause at each table for Mike's rulings before you write anything.

**Standing rule:** no item is closed, kept or re-filed on the strength of its own description. Open it against the current code, or the VM, first. Each verdict needs a commit, a `file:line`, a named test or a VM read. Closed items go to `archive/backlog_closed_2026-10.md`, or `_2026-11.md` from November on, with that evidence. Name every item by its plain-language problem first, then its id.

**Context, so you don't re-derive it.** Between 10-21 and 10-29 the scheduler and task layer were rebuilt:
- the task ledger (`tools/obligations.py`)
- the day planner (`tools/day_plan.py`), which owns check-ins and nudges since 10-29
- all-calendars read (`fccbc1e`)
- task `defer`/undefer, and quiet-hours follow-ups with an approval card (`97f9f09`…`9e57655`, deployed 10-29)

The 10-29 session found that about a third of the checked items had already been fixed or superseded by that work. Expect the same here. Log: `archive/PROJECT_LOG.md` § 2026-10-29 third.

## Step 1: the overdue checks (read-only VM reads, done in this window)

These need traces, the journal or VM data, so do not hand them to workers. Use `scripts/vm_read.py`, or one `gcloud compute ssh … --tunnel-through-iap --command=…` round-trip per batch. The pattern is in `docs/INFRASTRUCTURE.md` § "Counting a runtime signature from the Mac".

1. **The virtue review was paused but might still come back (Inbox, due 10-28).** Read the 10-27 07:30 morning brief and the 20:00 evening close in `data/personas/mike/traces/2026-10-27.jsonl`. If neither mentions virtues, close the item; if either does, reopen it with the reply text.
2. Every item on the sync's `⚠ due:` line, currently:
   - **writing tone never learned from a real mailbox** `[DB-0810-05]`
   - **old threads expire, but the signals that keep one alive are unchecked** `[DB-0814-02]`
   - **replies cut short or blank** `[DB-1026-01]`
   - **the Accountability Index** `[DB-0827-09]`, whose join was verified intact against the new ledger on 10-29 and is still waiting on a real 05:45 verdict and a Sunday retrospective
   - **the audit of its judgements** `[DB-0828-01]`, overdue since 09-07

   For each one, read what its `Closes on:` / `@waiting:` line asks for and check it on the VM. Then close it, give it a new date with a stated reason, or say what's blocking it.
3. The other dated Inbox checks whose date has passed when you run this (10-31 Vertex stalls and `check_inbox_6h`, 11-02 gym adherence and "over and out", 11-07 correspondence suggestion). Same treatment.

Give Mike one numbered table: item, what you read, verdict, proposed action.

## Step 2: triage the 10 untriaged Inbox entries (the default `/backlog` pass)

These are the machine-written `[needs building]` / `[instruction change]` entries. Six date from 09-07 to 10-15 and have never been looked at. For any that Mike raised, find the exchange it came from before proposing a tier (`/monitor/conversations` on the VM; the auth pattern is in `scripts/sync_dev_backlog.py`; quality-event times are UTC, conversation `ts` is VM-local). These four look superseded or mergeable; check them, don't assume:
- **Business matters wait until Monday (Duross, 09-12):** may already be a persona rule on the VM.
- **CRM updates overwriting existing emails (09-07):** check `tools/crm.py`.
- **Venue hours checked before recommending (09-08):** probably merges into the unactionable-suggestions item `[DB-0902-03]`, whose opening-hours half is still real.
- **Daily steps/sleep/diet cadence (10-26):** may already be habits in the VM's `data/personas/mike/tasks.yaml`.

Propose `## Now` / `## Later` / close for all 10 in one numbered table. The `## Now` entry bar is that Mike raised the item, so state who raised each one. Then rewrite each entry into its section and delete it from the Inbox.

## Step 3 (carry-on): the `/backlog deep` sweep of `## Later`, only on or after 2026-11-05

**Gate:** first re-count the routing-miss noise `[DB-0902-01]`, due 11-05. That's `ROUTING_MISS` events from scheduler-opened sessions since 10-29 in the VM's `data/personas/mike/logs/quality_events.json`. The planner took over check-ins on 10-29, which should have removed most of them. If they're gone, the machine log's biggest recurring signature has gone with them, and the sweep below won't be fighting noise that is already switching off. If it's before 11-05 when you reach this step, stop and say so instead.

Then run `/backlog deep`: verify all 31 `## Later` items against current code. Fan out to at most three Sonnet workers, read-only, with the full text of each item in the brief and an estimate of about 60k tokens each. Merge overlapping items, sweep the 18 recurring machine-log signatures, and roll closed items over. Most of the stale items should be among those filed in August and September against code since rebuilt, e.g.:
- nothing measures missed opportunities `[DB-0809-08]`
- semantic retrieval within a knowledge domain `[DB-0815-13]`
- one model round-trip per tool call `[DB-0808-09]`
- asking about the same Bill twice `[DB-0818-05]`
- a route called "well covered" without known locations `[DB-0902-06]`

Record actual cost against the estimate with `python3 scripts/worker_ledger.py`. On 10-29 the build workers ran 45–80% over their estimates.

## Rules for this session

- **Another chat may be committing to the same working tree.** Run `git diff` on every file before staging it, stage by name, and never `git add -A`. Check `git log origin/main..HEAD` before any push. If it holds a commit that isn't yours, ask Mike before pushing.
- Red tier (`config/agents/*.md`, `core/scheduler.py` and the rest in `.claude/settings.json`) is edited only here, with Mike's approval, never by a worker. Workers in this session are read-only.
- Don't file new backlog items Mike didn't ask for.
- Close with `/archive`. Mike runs the deploy, if any code changed.

**Budget:**
- Steps 1–2: about 80k tokens in this window.
- Step 3: about 180k for workers, plus about 40k here.
- No run cost: nothing persistent is created.
