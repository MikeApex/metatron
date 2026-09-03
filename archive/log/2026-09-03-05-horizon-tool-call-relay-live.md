### 2026-09-03 (the horizon relay becomes a tool call, and files for the first time)

Third iteration of `[DB-0822-09]`'s delivery half, built after the second was live-tested and
found inert. Commit `1dbd9f0`.

**Why the template slot was abandoned.** The 2026-09-03 test of the JSON-schema version passed
on the reply and failed on the ledger: every item reached Mike, and
`data/personas/mike/horizon/ledger.json` did not exist. `logistics` had emitted no
`HORIZON_ITEMS:` line at all — conversational markdown with none of its documented output
format — having emitted the full structured block the previous day on the same model. **A
template slot is not a channel; it is a request.**

**What replaced it.** `record_horizon_item(title, date, venue, kind, detail)`, registered in
`core/orchestrator.py`, granted to `logistics` in both routing files, named in `logistics.md`.
A tool call is structured by construction: it cannot be quietly replaced by prose, its
arguments cannot be malformed and silently ignored, and a refusal is visible. This is already
the codebase's answer wherever a relay must not be lost (`write_quality_event`,
`open_obligation`).

Three decisions inside it:

- **One call per finding, not a list.** A model assembling a JSON array is back to emitting a
  structure it can get wrong, which is the failure being routed around.
- **The schema tells the specialist not to pre-filter on what feels already-raised.** That check
  belongs to the ledger, and an agent making it removes the only chance the ledger has to
  decide — the exact way a finding goes missing entirely.
- **A bad date is refused with a correction rather than coerced.** The ledger turns on dates
  being real; guessing one on the model's behalf would poison the record this exists to keep
  trustworthy.

The prose parser is **kept** as a second channel rather than removed: one substring check per
specialist output, and a run that does emit the block should not lose its findings for using
the older route. Both land in the same ledger and `record()` dedupes by key.

**Live results, in order.**

1. **Pipeline run, inbox directive — still filed nothing.** `logistics` called
   `read_intake_queue`, `read_email`, `write_log`, and not `record_horizon_item`, though the
   tool was granted and offered (33 tools in its live allowlist, verified through
   `get_allowed_tools`). So a granted tool is not automatically a used one.
2. **Direct run naming the horizon scan — filed five findings.** `record_horizon_item` fired
   and the ledger was created: the mover's claim and Rowan's payroll (both 09-05), the Maria
   meeting at Novotel London West, the Rosh Hashana children's service, and Iva's dental
   consultation. A direct agent run does not pass through `_file_horizon_items`, so those
   entries can only have come from the tool — which is what makes this decisive rather than
   suggestive.
3. **Next pipeline session delivered all five**, unprompted, to a bare *"How is my week shaping
   up?"* — including the two 09-05 deadlines and the events out to the 15th.
4. **Offer accounting is correct live:** `offers=1` after that session, not 2, so the window
   collapsed the Coordinator's and Synthesizer's separate context loads into a single charge as
   designed.

5. **The gap that appeared here was closed, and it was the whole point.** Filing was happening
   only when the directive named the horizon scan. On the *inbox-summarize* directive — the one
   that produced the 09-02 failure — `logistics` read the mail, answered well, and filed
   nothing, though `logistics.md` claimed the scan "runs every session". Two places still said
   *surface as `HORIZON_ITEMS`*: the horizon-scan header and the intake-queue interest-level
   rule, which is the one the Death Cab email actually travels through. Both now say *file with
   `record_horizon_item`* (`7aa1f2a`).
6. **The 09-02 case then closed on its own terms.** The same failing directive filed four new
   findings — **Death Cab for Cutie @ Troxy, 2026-09-26**, Jimmy Carr, the Bupa dental
   appointment, the George School social — and the reply carried all of them. The earlier batch
   moved to `offers=2` in the same run, so the count increments across sessions and exhausts on
   the next, which is the non-repetition guarantee observed live rather than only unit-tested.

**`[DB-0822-09]` is closed** — evidence in `archive/backlog_closed_2026-09.md`.

**Known limit carried out of the close deliberately.** An item filed *without* a venue does not
dedupe against the same item filed *with* one: the closing test left *"Dental surgeon
consultation - Iva Diamond"* (no venue) and *"Dental Appointment (John Doran)"* (Bupa Dental
Care Crossrail) as two entries for one 09-15 appointment, because the first keyed on title and
the second on venue. Bounded — one duplicate mention, each capped at two offers — and not the
failure this item was about. Widening the key to match a venue-less item against a venued one by
title similarity is the semantic guessing `[DB-0827-07]` was closed to keep out, so the limit is
recorded rather than papered over. Raised with Mike; not filed as an item because he did not ask
for one.

**On the cost of finding this out.** Six live sessions, 412,620 input tokens (271,049 of them
cached) and 4,734 output — **under $0.14 priced at the reasoning tier for all of it**, so
genuinely less. The expensive part was not money: a first attempt at the non-repetition check
scheduled two sessions either side of a 320-second wait, purely to let the `_OFFER_WINDOW_SECONDS`
constant expire, and would have spent twelve minutes re-verifying exhaustion that
`tests/test_horizon_ledger.py` already covers. Mike stopped it. **The live value was in the
things a test cannot see — that the ledger fills at all, that the Synthesizer delivers, that the
accounting is right — and all three were already in hand.** The ordinary run of sessions supplied
the offer increment for free.
