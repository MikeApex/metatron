### 2026-09-07, second (an invitation that was never sent, then three reasons it still was not) — `8c512b5`, `c1ed1d0`, `45c9260`, `b2b1dc7`, deployed after each

Incoming handoff: nothing owed, VM at `4db2640`, both new scheduled sessions verified firing.

Mike reported that Metatron kept saying Iva had been invited via Google Calendar and nothing
ever appeared. It took four commits, and **three of the four were my own errors, each found
only after Mike re-tested** — the sequence is the point of this entry.

**1. The premise, verified: it had never been possible.** `attendees` on `write_calendar_event`
takes *names, not addresses*, and is written as `X-ATTENDEE-NAMES`, a private label used for
duplicate and conflict matching. No standard `ATTENDEE` line existed anywhere in the codebase.
So no CalDAV server ever had anything to act on: not intermittent, not a Google auth problem —
the capability had never existed, and the tool's bare `success: true` was being read back as an
invitation delivered. `8c512b5` makes both write paths return `invitations_sent: false` and a
note. **The return value is the load-bearing part**: a schema description is read once when the
call is composed; the result is what is in front of the model when the answer is written.

**2. Three routes considered; the middle one built.** *Rejected — leave it as a label*: honest
but does not do the job. *Rejected — put a real `ATTENDEE` line on the stored event and let the
calendar server mail people*: fewest moving parts, but it creates an outbound message to a third
party on the calendar-write path, around `send_email`'s confirmation gate and CRM recipient
allowlist; a model hallucinating an attendee would mail a real person with no preview. *Built* —
`send_calendar_invite`, a `METHOD:REQUEST` iCalendar part on an ordinary approved email
(`c1ed1d0`). Carries the event's real UID so a later change supersedes rather than duplicates.

**3. Wrong: "16/16 tests pass" did not mean it worked.** It failed in production on the first
try. A gated tool lives in **two** registries — `confirm.request()` raises the card,
`confirm._EXECUTORS` tells the server what to run on approval — and I shipped only the first.
Mike approved a real invitation and got *"Nothing here knows how to carry out
'send_calendar_invite'"* (seq 010). Every one of my tests drove `consume()`; the app drives
`execute()`. Two further registries were also missed: analytics' `_WORLD_AFFECTING` and the
monitor's resource labels. Fixed in `45c9260`, with the suite extended to drive the app's path —
verified by removing the fix and watching it fail 16/19, exactly the 16 that had passed before.

**4. Fixed the class, not the instance.** `scripts/check_confirm_executors.py` compares the two
registries statically; check 1b in `qa_sweep`. Same shape as the `get_weather` grant/doc split
that `check_agent_tools.py` exists for. **Its own first run was wrong twice**: it reported
`requests.request("REPORT", ...)` in `caldav.py` as a gated action named `REPORT`, and its first
exemption list excused `add_zone` — which was really the scanner failing to read one import
style. An exemption covering a scanner blind spot silences the finding that would reveal it. The
list is now empty and stays that way.

**5. Wrong again, and this one was a design error, not a missing line.** After deploy Mike asked
three more times and was told each time that inviting needed building. The seq 013 trace: the
Coordinator routes *"invite Iva to the events we've been discussing"* to **logistics** — it is a
calendar request — and `relationships`, the only holder of the tool, was never dispatched. I had
also written into `logistics.md` that inviting happens elsewhere and it should not report on it,
so it correctly did nothing. **I had reasoned from the 2026-08-09/10 single-owner-for-outbound
rule and not checked the routing.** `b2b1dc7` grants the tool to `logistics` as well.

**Why that is not an erosion of the August consolidation.** That rule governs who *authors*
outbound prose, which is where disclosure discretion lives; an invitation's payload is an event
that already exists. The controls that actually protect the send — the confirmation gate and the
CRM recipient allowlist — are enforced in Python, apply to both agents, and were untouched.
Relationships keeps its grant for person-centred conversations. Also recorded: relationships
holds no calendar tool, so it *cannot* enumerate the events it would be inviting anyone to —
the practical half of why the original call was wrong.

**Checked on the VM before the last change, to avoid a fifth round trip:** HEAD was `45c9260`
(both prior fixes live), and `_known_recipients()` resolves `iva.stod@gmail.com` from her CRM
record — so the allowlist was never the blocker. Her record holds work and personal addresses
under different keys and only the personal one is in the allowlist, which is correct here but
worth knowing.

**Open, not filed:** inviting to N events is N approval cards. `logistics.md` now says to state
how many are coming rather than doing one and describing it as all of them. Batching them into a
single approval is a real change and was not made. Mike's standing-rule request from this morning
(auto-invite Iva to external events) is still untriaged in the Inbox and is now buildable.

