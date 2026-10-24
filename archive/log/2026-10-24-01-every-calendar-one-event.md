### 2026-10-24 (every calendar on the account, one event per event — and a live probe started by accident) — `fccbc1e` deployed by Mike, `a70ead7` (tests only) + this close-out

**Carried from the outgoing handoff:** the task ledger (`27c570f`) was committed 10-23 for Mike to
deploy; its post-deploy session is `archive/handoffs/2026-10-24-task-ledger-post-deploy-prompt.md`,
run in a separate window today and untouched here.

**The need.** A second Google calendar shared to the `mike` account ("Shared with Mike",
`3uf1n7vngca5hbi2u9ur06cklo@group.calendar.google.com`) was visible in Google Calendar and
invisible to Metatron. **Cause: `tools/caldav.py` read exactly one collection, `calendar_url`
(the "Metatron" group calendar).** The account's own primary calendar and UK holidays were
invisible too. Read-only probes on the VM: the app password reads the shared calendar directly
(87 events) — access was never the problem. Google's CalDAV listing is governed by
`calendar.google.com/calendar/syncselect`; the shared calendar appeared only after Mike ticked it
there. **That page is now the include/exclude control.** The complete list ("everything shared
with me") exists only in the Calendar API under OAuth — Mark 2, already settled.

**Overlap, measured (−60..+90 d):** one same-UID invite on primary + shared (differs only by a
VALARM); two Metatron copies of shared events with different UIDs — John Ball (identical) and
Jimmy Carr (21:15 London on Metatron vs 22:00 Europe/Budapest on shared = 21:00 London).

**Built (Mike chose discovery + `extra_calendars` fallback; ruled the Metatron copy wins).**
RFC 6764 discovery (principal → home-set → listing; Google answers the principal only at
`/calendar/dav/`), 10-min in-process cache of successes only, parallel REPORTs, cross-calendar
merge: same (UID, RECURRENCE-ID), or — one-offs only — equal normalised title + overlapping time.
Never merges within one calendar (`calendar_audit`'s job). Merged event: Metatron copy wins every
field, losing values under `discrepancies`, union of description/location/attendees, `calendars`,
`read_only` (not on the writable calendar), `shared` (on no calendar of the account's own).
**Only `read_calendar` and the write-time conflict check read "all"; every unattended job —
reconcile, travel watch, accountability, location, duplicate audit, ledger calendar link — stays
on the configured calendar,** so none starts alerting on or scoring against other people's events
and their uid-keyed seen-sets are untouched. Kill switch `discover_calendars: false` (config, no
deploy). Edits to a read-only event say so, calendar name wrapped as untrusted.

**Three latent bugs found and fixed, all reproduced on HEAD:** TZID discarded (foreign-zone times
read wrong); a VALARM's DESCRIPTION overwrote the event's; a UTC-stamped event in the conflict
window made `_compute_conflicts` raise `TypeError` out of every calendar write — live risk on the
single-calendar path already.

**Review.** Fable on the plan: 7 findings, all accepted — the decisive one was that "all" in the
shared data layer would feed other people's events to every proactive job; hence the
"own"/"all" split. Second round added UTC/naive crash and paid route lookups for others'
locations. Fable on the code: 4 more, all fixed — **believed wrong: "read-only" ≠ "someone
else's"**; the account's own calendar (where invites land, e.g. "Lunch with Victoria") was being
discounted. Also: failed discovery no longer cached; conflict results name `calendars_not_checked`;
the duplicate note no longer claims the user's app shows one entry. 26 tests
(`tests/test_caldav_multi_calendar.py`); live in-memory run on the VM before deploy: 4 calendars,
234 events, exactly the 3 real overlaps merged.

**Rejected:** manual list only (every new share a VM config edit); waiting for Mark 2 OAuth;
trusting CalDAV privilege sets for writability (Google reports write on Holidays); merging
recurring series by title (master DTSTART comparison is meaningless); a budget-watching daemon
(see below).

**Correction, mine: a loop over calendar-related `tests/*.py` started
`tests/run_coord_model_probe.py`, a live model probe** — ~9 min, 62 Vertex calls, ~$0.72, stopped
by hand, nothing written. Also broke the Testing Cost Convention (no projection). Mike asked about
a budget daemon; recommended against — nothing ran away, so no threshold distinguishes it, and it
would retire nothing. Instead `a70ead7`: `tests/support/live_gate.require_live()` at the top of the
ten live scripts — non-interactive starts exit 2 unless `METATRON_LIVE=1`; terminal use unchanged;
`--dry-run`/`--report-only` ungated; noted in `docs/CONVENTIONS.md` § Testing Cost. Mac/VM separate
spend budgets: Mike ruled not relevant.

**Open:** the two old Metatron copies (John Ball, Jimmy Carr) still show twice in Google Calendar —
delete only on Mike's say-so. `run_calendar_live_test.py` is VM-run over SSH (non-interactive):
it now needs `METATRON_LIVE=1`.

