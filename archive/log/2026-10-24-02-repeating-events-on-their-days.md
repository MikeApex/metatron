### 2026-10-24, second (repeating events on the days they actually happen) — `bbc741b` — **committed; owes `./deploy.sh`**

**Found by Mike's live check of the multi-calendar build (`fccbc1e`, deployed `3515373`).** Asked
for the week of 9 Nov, Metatron got John Ball right (merged, once) and **left out all eight of that
week's repeating items** — Karate Mon, Carmit and swim Fri, Gan, trash, school-week review and two
credit-card entries Sun. **Cause, pre-existing and not introduced by the multi-calendar work:**
Google returns a series as its master VEVENT, dated at the FIRST occurrence (Gan: 2025-09-14), and
ignores CalDAV `<c:expand>` (probed: RRULEs intact, no instances). The model was left to compute
dates from the RRULE and did not. The write-time conflict check had the same blind spot: a booking
at Karate time on a Monday overlapped nothing, because the master is dated in September.

**First design, killed by Fable:** list each occurrence as its own row. Every row would carry the
series uid, and `update_calendar_event` on it rewrites the master — "move Monday's karate to 17:00"
would move the whole series and erase its history. That is the occurrence-vs-series gap Mike ruled
"skip, no backlog item" on 09-05; the design built past the ruling without naming it.

**Built instead:** a series stays one row with its series uid; it gains `occurs_in_range` — local
dates in the window, from `python-dateutil` (already pinned) in the series' own zone so wall clock
holds across DST; EXDATEs (incl. date-only on timed series) and rescheduled originals removed;
override rows stay their own rows as before; cap 60 + `occurs_in_range_truncated`. Anything
unreadable → `occurrences_unknown`, never a guess. "All" mode only (`read_calendar`, conflict
check); unattended jobs untouched. The conflict check runs every test once per occurrence —
overlaps, exact duplicate (still refused for a writable series), near-dups, **day digest and the
travel check** (Fable's second-round catch: those had still selected by master date).
`recurring_series_match` deduped per series.

**Review:** Fable on the plan (4 findings + 1 new, all taken) and on the code (no structural; one
local — unreadable EXDATE/RECURRENCE-ID was silently skipped, now marks the row unknown). 42 tests,
13 of the new ones failing on the deployed code first. Live in-memory run on the VM: all eight real
series land on the right dates; a Mon 18:45 booking now overlaps Karate.

