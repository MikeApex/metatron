Model: Opus 5.5. This is a coordinating window: it re-verifies, shows the cluster plan, spawns the workers, and owns every write to the records. Workers build on Opus too, per Mike's 2026-09-24 rule (build in Opus), because each one makes design calls inside its file. A Fable review of the merged diff is optional: worth it only for cluster A, which touches auth.

# Backlog attack: Sign out, calendar event text, and the forwarding trail (paste into a fresh chat)

/metatron-code /backlog attack

**Run this after Mike's `/backlog deep`.** That sweep may merge, close or re-rank items. Before
doing anything else, re-read `## Now` in `DEV_BACKLOG.md` and confirm that items 4–6 below are
still there, still open, and still Amber. If the sweep changed any of them, adjust the plan to
what the file now says and tell Mike before spawning.

## The three items (`## Now` 4, 5, 6 as of 2026-10-29; all raised by Mike)

**Standing rule:** none of these is built on the strength of its own description. Each was
re-checked against the code on 2026-10-29. Every worker re-checks its item first, with
`file:line` evidence, and reports if the premise has gone stale.

**A. The app has no way to sign out `[DB-1029-11]`.** Tapping the name opens only the sign-in
screen. The previous user's sign-in stays stored, and a failed sign-in as someone else leaves the
first person signed in after a refresh (`static/index.html:1328`, `:4519`). The sign-in is an
HttpOnly cookie, so a server route has to clear it. Today `core/server.py` has only
`/push/fcm/unregister` (`:2163`), which stops a phone's pings. **Shape:** a server route that
clears the cookie and unregisters the device's push token; a client Sign out action that calls it,
clears stored sign-in state, and returns to the sign-in screen. **Manifest:** `core/server.py`,
`static/index.html`, a new `tests/test_sign_out.py` (plus a JS test if the client logic warrants
one). **Then Mike rebuilds the APK.** Auth surface: read `core/auth.py` and
`.claude/rules/orchestrator.md` first. Don't weaken any check; a signed-out client must get 401
afterwards.

**B. Calendar events Metatron writes put the place in the title and call Mike "user"
`[DB-1029-10]`.** For example, on 10-27 the event "Benny and user at Canary Wharf" had an empty
`location`, so the day planner planned no "leave for" row. Logistics also once passed uid `"..."`
to `update_calendar_event`. **Code half only (Amber), in `tools/caldav.py`
`write_calendar_event` (`:976`) / `update_calendar_event` (`:1244`):**
- refuse or repair internal vocabulary ("user", "the user") in titles and descriptions, using the
  user's own name from the profile, or dropping the word;
- when `location` is empty and the title carries " at <Place>", move the place into `location`;
- refuse a placeholder uid (`"..."`, empty, non-uid shapes) with an error that names the fix.

The conduct half ("a place the user names goes in `location`") is a `logistics.md` line and is
**Red**. Propose its exact wording in the handoff; the coordinator puts it to Mike. **Manifest:**
`tools/caldav.py` and a new `tests/test_calendar_event_text.py`.

**C. Forwarded email loses who it was originally for `[DB-0902-05]`.** On 08-28 a family
member's email, forwarded from a secondary account, arrived without its original-recipient data,
and the system read it as misdirected. Nothing in `tools/mail.py`, `tools/intake_email.py` or
`tools/intake_forward.py` keeps `Delivered-To`, `X-Forwarded-To` or the original `To:`. The
self-forward unwrap (`intake_forward.py:212`) recovers only the original *sender*. **Shape:** carry
the original recipient through to what `read_email` and the intake envelope report, so a reader
can see "forwarded from <secondary>, originally to <person>". **These headers are
attacker-writable**: they are display and routing only, never a learning signal and never a
permission, the same discipline as the forward unwrap's `ledger_safe=False`. **Manifest:**
`tools/mail.py`, `tools/intake_email.py` (`tools/intake_forward.py` only if needed, declared before
starting), and a new `tests/test_forward_recipient_trail.py`. Re-run `tests/test_intake_forward.py`
and `tests/run_intake_redteam.py` afterwards.

The three manifests are disjoint. Check that again before spawning: if the deep sweep or another
chat touched these files, re-check with `git status` and `git log -5 -- <file>`.

## Dispatch

Exactly as `/backlog attack` says: one worktree per cluster via
`./scripts/new_worktree.sh <slug>`, no `isolation` flag, absolute path in the brief, the worker
protocol verbatim, and the full item text above in each brief. Workers commit only their manifest
in their worktree; the coordinator merges.

**Budget:** about 100–150k Opus tokens per worker, so ~350–450k across the three, plus ~40k
here. Today's build workers ran 45–80% over estimate. Record the actuals with
`python3 scripts/worker_ledger.py`. **Run cost:** none. Nothing persistent is created, and
Sign out adds one route.

## Close

Merge, then run every touched suite plus `scripts/qa_sweep.sh`. Then `/archive` once, folding
each handoff in, giving each item a dated closes-on check, and deleting the consumed handoffs.
**Mike runs `./deploy.sh` and the APK rebuild.** The Red `logistics.md` line from B goes to him
in one batch.
