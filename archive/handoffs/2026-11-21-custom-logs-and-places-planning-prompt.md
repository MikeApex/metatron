Model: Opus 5.5 — interview-led planning across two features with privacy, cost and multi-user edges; review the finished plan in Fable.

# Custom logs and places — interview, find the edges, then plan (paste into a fresh chat)

/metatron-code This is a **planning session, and planning comes last.** First interview me, then
map every edge of both ideas with me, and only then write the plan. Do not write or edit any code
or config in this session. Do not propose a design before the interview is done — if you catch
yourself recommending an approach in the first half, stop and ask the next question instead.

## The two needs, in my words

**1. Custom logs.** When I say "I'm going to give you some information over the week that I need
logged as a separate file — date, time and a reason", Metatron should create that log, keep every
entry I give it in the same place, let me change it later, and read it back. It must also
**recognise when a new data object is needed without my asking for one** — a pattern of things I
keep telling it that has nowhere to live. Logs that many users create should become general user
fields. **Built in, available to all users from now on, but restricted as the user pool expands
beyond the Alpha.**

**2. Places.** Every place has a **GPS entry**, compared by proximity with where I am now and
where I'm planned to be. Places carry my verdict: Clipstone ("went, not again"), Bianco 43 ("our
go-to pizza — bring it up the next time pizza comes up near home"), 108 Brasserie ("try if we're
in that neighbourhood; pricey"). It should also **log the places I go, and go often, as a matter
of course** — not only the ones I name.

## What exists today — verified 2026-11-21, re-check before relying on it

Read these first, in order:

1. `archive/plans/capture_labels_notes_2026-11-18.md` — where these needs surfaced (labelling the
   capture-fidelity backfill), including the second pass's notes.
2. `archive/plans/capture_fidelity_plan_2026-11-18.md` § 10 — the capture stage's `other` kind and
   its once-per-category backlog alert. **This is already a mechanism for noticing facts with no
   home**; decide with me whether it is the detector for "a new data object is needed".
3. `archive/log/2026-11-16-01-health-notes-kept-and-cardiac-log-rebuilt.md` — how the one custom
   log that exists (cardiac events) was actually made: **by hand, in development sessions, not by
   the runtime.** A dedicated tool was rejected then; read why.

A survey on 2026-11-21 found, against the six things a custom log needs:

| Capability | State | Where |
|---|---|---|
| Recognise the request | missing | no agent treats "log this separately" as a new record type |
| Create it | partial | `write_archive` accepts a new category name (`tools/diarist.py` ~459) — no field definition, no registry of categories |
| Write consistently | unreliable | each turn must re-guess the name; rows sharing a title/name/text are **merged** (`tools/diarist.py` ~312–331) — wrong for an event log; the Diarist can write archives but not read them |
| Amend it | missing | nothing to edit |
| Read it back | partial | `read_archive` needs the exact name; nothing lists categories |
| Promote across users | missing | nothing counts custom lists across personas |

For places: `write_archive` already lists `places` as a built-in category, with no coordinates.
`tools/location.py` and `location_sharing` in day shape exist — **read them to learn what location
data actually arrives and how often.** The day planner (`archive/plans/day_planner_plan_2026-10-24.md`)
knows planned locations. The Build vertical (`request_build`) only files a ticket for a developer
session; it cannot create anything at runtime.

## Part 1 — interview me (before anything else)

One or two questions at a time, plain language, and wait for my answer. Cover at least these, and
add what my answers open up:

- **Custom logs:** what logs I'd actually want beyond cardiac (and what Iva might); how I'd want to
  start one, see one, change one, end one; what "restricted beyond the Alpha" means to me (per-user
  switch? a cap? my approval? paid tier?); how sure Metatron must be before it creates a log I
  didn't ask for — create, offer, or just tell me; what a "general user field" means once promoted.
- **Places:** where my location comes from today and how often; what counts as "a place I go" (how
  long there, how many times); what I want said when I'm near a place, and when I don't want
  anything said; home, school, the Wharf — places that are routine versus places worth a mention;
  how long location history is kept; Iva's places and the kids'.
- **Both:** what I'd consider a failure — the thing that would make me turn it off.

## Part 2 — map the edges with me

Find every edge, then go through them with me and record my ruling on each. Include at least:

1. **False creation** — a log or place nobody wanted, and how it is undone (data is never deleted
   here: archive-on-merge with a `merged_into` pointer — `CLAUDE.md` Key Design Decisions).
2. **Name drift** — "the cardiac log", "the heart log", "another one for the log" reaching one store.
3. **Shape drift** — fields added later; old entries without them.
4. **Merge versus append** — the archive store's dedup is right for books and wrong for events.
5. **Privacy** — every custom log and all location history is **sensitive tier**. Location history
   is among the most revealing data the system could hold. Cross-user promotion must be
   **content-free counts** (the A9 discipline, `ROADMAP.md` § A9).
6. **Leaving the machine** — **geocoding an address or reverse-geocoding coordinates is an outbound
   call** to a third-party service. `WebFetch` is Denied here and nothing leaves the machine without
   my say (`CLAUDE.md` § Change tiers). Surface the options and the trade-off; the ruling is mine.
7. **Second user** — Iva's consent records (`data/personas/{p}/consents.json`) gate correspondence
   and tone; decide with me whether location history needs its own record. (Her data otherwise has
   exactly `mike`'s clearances — `ROADMAP.md` § 0, amendment 2026-11-18.)
8. **The Alpha restriction** — the mechanism, and what happens to a user's logs if it tightens.
9. **Proximity noise** — how often a "you're near X" may fire, and quiet hours.
10. **Health logs** — a custom health log sits next to Physical Health's clinical flags; the
    before-Alpha safety re-run (`ROADMAP.md` § 0) is where its review is owed.
11. **Overlap with stores that exist** — the log's health notes, wisdom, archive lists, agent
    config, the calendar, contacts (a place can be a practice; a person can have a place).
12. **Capture fidelity** — once these exist, events/places/custom-log entries need homes in
    `KIND_HOMES` (`tools/capture.py`), and `other` alerts become candidates for new logs.

## Part 3 — then plan

Write `archive/plans/custom_logs_and_places_plan_2026-11-<dd>.md` with: the need and what a user
experiences, the rulings from Parts 1–2 (each attributed and dated), the design, files split by
change tier (`.claude/settings.json` is the authority; Red work is not delegated), build order,
tests (every live meter stubbed), and the standard close:

- **Cost budget, all four classes** (`~/.claude/CLAUDE.md` § Costs). A location history and a
  registry of custom logs both **persist**: for each, answer the three questions — the unit of its
  standing cost, what deletes it and what survives a restart, which meter reports it.
- **Model for execution**, and whether to split build and review.

Then propose an adversarial review (`/adversarial-review`) before any build, and close with `/archive`.
