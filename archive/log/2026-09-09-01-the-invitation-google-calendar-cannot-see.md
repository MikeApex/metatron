### 2026-09-09 (the invitation Google Calendar cannot see) — `0e154b9`, needs deploy

Continues 2026-09-07's invitation work, which had been archived as resolved. It was not.
Mike reported that Google Calendar still showed no invitations, and **he was right — but not
for any of the reasons the previous four commits addressed.**

**What was actually true.** The seven invitations *were* sent, at 12:32–12:33 on 09-07: real
messages in Sent Mail to `iva.stod@gmail.com`, valid `METHOD:REQUEST` payloads with correct
`ORGANIZER`, `ATTENDEE` and the events' true UIDs, **zero bounces**. Seven `POST /confirm`
returned 200. Delivery was never the problem. What Mike was looking at — his own calendar —
had no guest on any event and no record that anything had been sent, because the invitation
goes out **beside** the calendar rather than through it. Under the shipped design that is
permanent, and it is exactly what "not sent according to Google Calendar" means.

**The correction that matters, because I nearly shipped a fix on it.** I probed Google's CalDAV
endpoint with a throwaway event carrying a real `ATTENDEE` line: it returned `201`, stored the
line, and echoed it back **normalised, with a `CN` added**. I read that as proof the route I had
originally rejected would work, and proposed it. Mike ran the same change against one real event
(the 13 Sep Jimmy Carr booking, his own address as guest, backed up first) and reported: **no
guest shown, no invitation sent.** So Google's CalDAV interface *stores* attendee data and
ignores it entirely. **Accepting a property and honouring it are different things, and the probe
only ever tested the first.** Reverted from the backup.

That kills the fix outright. There is no way to make Google Calendar show a guest or send an
invitation over CalDAV with an app password. It is a limit of the interface the whole calendar
integration sits on, not a defect in what was built.

**Also corrected: my original rejection reasoning was wrong for a different reason.** On 09-07 I
rejected the calendar route because it would "bypass the confirmation gate". That conflated the
gate with the protocol — the gate is the confirmation step and would have held regardless of
which write performed the action. The route was still wrong, but not for the stated reason, and
the stated reason would have argued against the right answer in a different situation.

**What shipped instead: the failure stops looking like a failure.** `logistics.md` now says never
to send the user to their calendar to confirm an invitation, and `send_calendar_invite` returns
`visible_on_calendar: false` with the reason. The return value carries it because that is what
the model reads when it writes its answer — the same reasoning as `8c512b5`, and the third time
this session that placing a fact in the *result* rather than the *schema* was the load-bearing
choice.

**Deferred to Mark 2 by Mike (2026-09-09), filed.** Real guest management needs the Google
Calendar API over OAuth with `sendUpdates=all`, which runs into the 7-day refresh-token expiry
under Testing publishing status — the same wall that reversed the Google Contacts integration on
2026-08-08, same account and GCP project. An integration change with a verification
prerequisite, not a patch. **Do not re-propose it against the Mark 1 CalDAV path.**

**Process note worth keeping.** The 09-07 session archived this as resolved on the strength of
"✅ Done" confirmations and Mike's own "seems resolved". Seven approvals reported success and the
user-visible outcome was still absent, because success was measured at the send and the user was
measuring at the calendar. **A confirmation that the action completed is not evidence that the
user got what they asked for**, and the two were three days apart here.

