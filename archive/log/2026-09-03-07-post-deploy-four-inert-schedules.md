### 2026-09-03 (Post-deploy: the same job shipped inert four times, and a defect that was not one)

Session ⑦'s work was deployed by Mike and verified on the VM (`18d6923`; suite **72/72** there,
both units active). `[DB-0818-08]` and `[DB-0804-02]`'s slice were live and correct on arrival.
`[DB-0808-06]` was not, and finding out why took four separate discoveries — each of which
passed every test in the suite.

**The four ways one scheduled job failed to exist.**

1. **Wrong file.** The job was added to `config/templates/scheduler.yaml`. The daemon reads
   `config/personas/mike/scheduler.yaml`, which `deploy.sh` correctly leaves alone because it
   holds Mike's quiet hours. The template only seeds *new* personas.
2. **`days: sun` matched nothing.** `_is_active_day` compares `strftime("%A").lower()`, so the
   abbreviation never matches, on any day, permanently. No error, no warning.
3. **No `day:` key, so it registered daily.** `_register_schedules` takes its weekly branch only
   on `"time" in job and "day" in job`. The journal line after the first restart read
   `weekly_clinical_review: daily at 11:00`, which is what exposed this.
4. **The daemon never re-reads `scheduler.yaml` at all.** Its loop watches
   `data/personas/{p}/schedules.yaml` (agent-written) and re-registers only on that or a DST
   change — so a config edit does nothing until `systemctl restart metatron-scheduler`.
   `core/scheduler.py`'s own comment describes this failure as *"the user told it was set,
   nothing happening, no error anywhere."*

Fixed on the live VM config (Mike authorised the Denied, VM-owned edit; the method is the one
`.claude/rules/personas.md` already sanctions — *"edit on the VM directly"* — and it was backed
up first). Registered line now reads `weekly_clinical_review: sunday at 11:00`, and the function
was executed against live `mike` data returning `nothing due`, which is correct.

**THE CORRECTION THAT MATTERS: `day:` is not ignored, and I reported that it was before testing
it.** The claim went to Mike, into the capstone note and into a filed backlog item, all on the
strength of reading `_gates_block` and stopping there. The two keys drive **different layers**:
`day:` is read at *registration* (`schedule.every().<day>.at(t)`); `days:` is read by the
*firing gate* (`_is_active_day`). So `weekly_pattern_miner` and `weekly_physical_review`, which
set only `day:`, are correct — their gate defaults open, but registration only ever invokes them
on Sunday. **They have not been running daily.** Confirmed by reading the daemon's own
registration lines after a restart, which is what should have happened before filing anything.

The Inbox item was rewritten to the residual defect, which is real but far narrower: **a typo in
`days:` fails silently and permanently**, and a job setting only `days:` registers daily and is
then gated six days a week. Recommended fix is to validate scheduling keys at config load and
refuse an unrecognised day value loudly, plus document the two-layer split — it is in no doc and
had to be derived from log lines.

**What caught it, and what did not.** Nothing in the suite asked whether a schedule was
*reachable*; it only tested the code the schedule would call. The regression test now covers
both layers and asserts the two keys agree — and it immediately caught its own author, failing
the moment `day:` was added, because it had encoded the wrong understanding.

**The capstone status table was 13/24 wrong.** Mike opened the file and asked why there were so
many empty boxes. `⬜` is a deliberate "open" marker, not a font failure — but six sessions,
this one included, had appended dated notes *below* the table rather than updating it, so the
summary drifted while the narrative under it stayed correct. Refreshed to 14 closed / 4 awaiting
confirmation / 6 open, verified row-by-row against `DEV_BACKLOG.md` with zero mismatches. A
first audit pass said 14 stale and was wrong — its pattern missed numbered entries in `## Now`
and would have marked the still-open `[DB-0822-06]` closed.

Also filed this session: `quick_override` reaching the clinical agents on the bulk tier, carried
unfiled in `SESSION.md` since ⑥ — one primer rewrite from being lost.

Commits `8b24802`, `c24efe4`, `18a8f6b`. Nothing owes a deploy: all three are template, tests
and docs, and the live config was edited in place (gitignored, so no future pull can clash).
