### 2026-08-26 (venue discovery goes live; venue routing, the anticipation pass, and the Diarist's plan/event line) — `bec3952`, `1d77bd0`, `449c0a7` + VM-side edits — **deployed by Mike**

**Carrying the 08-22 close-out:** three clusters built and merged, one deploy owed, Places key
owed. Both arrived today.

**The Places key path took three corrections, all the same root cause: Google ships two
near-identical products.** The console steered Mike to legacy "Places API" twice — the project
had the legacy service enabled while `tools/places.py` calls Places API (New), and the key's
restriction was ticked against the legacy product because the restriction dropdown only lists
*enabled* APIs. Fixed with `gcloud services enable places.googleapis.com` and
`api-keys update --api-target=service=places.googleapis.com`. Also settled at key creation:
**Application restrictions = None** (an IP pin would silently die on the next VM stop/start —
the external IP reassigns; § Infrastructure traps 1–2), and **no service-account auth** (the
tool speaks `X-Goog-Api-Key`, not OAuth). Key lives in the VM `.env` as
`GOOGLE_PLACES_API_KEY`, provenance comment attached.

**A trace read was wrong before it was right, and the wrong read nearly shaped a fix.** The
first live venue turn (Monday's Charing Cross ask) genuinely had no `find_places` call — only
the Diarist ran, and the Synthesizer answered from memory, which also produced the Diarist
logging a dinner that never happened. But the *second* live turn (post-routing-fix, trace
`bac9d794`) was initially reported as "Logistics ran, zero tool calls" — **a shallow trace walk
that missed per-turn nesting.** The correct read: `find_places` fired (ok=True), three results
walked through `get_travel_time`, the reply's venues match the API by address. The missing
ratings were the Synthesizer's presentation choice, not missing data. A 3× direct-probe
confirmed 3/3 tool-call reliability. **`[DB-0808-04]` closed** (`449c0a7`), filed 08-08.

**Mike's three directives, all built (`bec3952`):**
- **Venue questions route to Logistics** — one coordinator.md line; the head layer is barred
  from answering venue questions from general knowledge.
- **Logistics anticipates locations unasked** — horizon-scan item 5 (Mike widened it from meals
  to errands, nearby contacts, downtime fills; contacts flagged by *area* since Logistics
  cannot read the contact store). New `location_anticipation` job daily at 10:00 (Mike moved it
  from my 16:00), template + VM live copy by hand — the template copies once at creation, which
  is why the VM edit is mandatory, and why this job is template-class not `_DEFAULT_JOBS`
  (prompted + notifying, not silent infrastructure). Cost named: ~$0.07–0.23/day. Risk named:
  widens `[DB-0809-02]`'s inherited-ritual surface.
- **Diarist records events, never plans** — rejected first draft lacked the intention half;
  Mike's version: a *user-voiced* intention IS logged, in a fixed machine-findable shape
  (`write_log` `{"intention": …, "stated_for": …}`), explicitly excluding system-created
  calendar obligations; fulfilment is its own entry, never pre-written. **Probed on the VM
  against `danny_park`, both directions pass:** the Monday failure shape produced zero writes;
  a voiced intention produced the exact shape.

**Filed:** Accountability Index (join intentions vs outcomes; A9-adjacent, content-free
constraint applies) and the anticipation pass's first-firing observation (2026-08-27 10:00) —
both as inbox fragments at Mike's instruction. **Open live checks, already carried by their
items:** merge confirmation card (`[DB-0822-03]`), offline shell (`[DB-0803-05]`).
`[DB-0822-01]` came due 08-25 — flagged to Mike, deliberately not bundled into today.
