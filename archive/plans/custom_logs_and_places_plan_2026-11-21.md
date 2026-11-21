# User data objects and places — plan (2026-11-21)

Planning session 2026-11-21 (Opus 5.5), from
`archive/handoffs/2026-11-21-custom-logs-and-places-planning-prompt.md`. Interview → edges →
plan; **no code or config was changed in the session.** Every ruling below is Mike's, given in
that session, unless marked **plan's choice** — those are mine, made to fill a gap the rulings
leave, and are the first things the adversarial review should attack.

Verbatim transcript: `archive/transcripts/` (2026-11-21). Background read: 
`archive/plans/capture_labels_notes_2026-11-18.md`, `capture_fidelity_plan_2026-11-18.md` § 10,
`archive/log/2026-11-16-01-health-notes-kept-and-cardiac-log-rebuilt.md`, `tools/location.py`,
`tools/places.py`, `tools/diarist.py`, `core/orchestrator.py` `_knowledge_manifest()`.

---

## 1. The need, and what a user experiences

**The prompt said "custom logs"; Mike widened it on purpose** — *"that's the initial
intention."* The subject is **user data objects**: every list, log and record Metatron keeps
about a user, the existing ones included. Two needs:

1. **Data objects.** A user says *"I'm going to give you some information over the week that I
   need logged as a separate file — date, time and a reason"*, and Metatron creates the object,
   files every entry in it, lets them change entries, and reads it back. Metatron also notices
   when something the user keeps saying has no home, **creates the object and says so**. Fields
   are the user's to extend (a films list gains *genre*, *who to recommend it to*). Every agent
   an object matters to knows it exists the moment it is created and can query it. Objects that
   many users invent become a default every user has.
2. **Places.** Every place has a position, compared with where the user is and where they are
   planned to be, and carries the user's verdict and **the occasion it is for** — *Bianco 43:
   our go-to pizza, raise it the next time pizza comes up near home*; *108 Brasserie: try if
   we're in that neighbourhood, pricey — only when a meal is being planned*; *Clipstone: went,
   not again — raise it to steer away*. Places the user goes, routine ones included, are logged
   as visits as a matter of course; recurring unnamed spots become a question (*"you've been at
   the same place three Tuesday evenings — what is it?"*).

**What it is for (Mike):** *"Largely these objects are for Metatron to use to do its job."*
Viewing screens and file export may become premium features. Unprompted use is **essential**,
not tolerated: *"Metatron should be opportunistic in finding geospatial synergies"* — interests,
errands, and (later) other users nearby.

**What would make a user turn it off** (Mike's ranking): an object nobody wanted, or a wrong
verdict, **must not happen**, and the design builds around them. Too-frequent mentions are a
setting, not a failure. Something revealed in front of another person is the user's risk, as with
any other app. History the user may not like is **kept**: *"the trick here is Metatron having a
good filter when speaking to the user, not ignoring the data. The conflicts like these are where
the insights lie."*

### What exists today (verified 2026-11-21)

| Thing | State |
|---|---|
| Archive store (`tools/diarist.py` `write_archive`/`read_archive`) | per-user `data/personas/{p}/archive/{category}.json`; any new category name accepted; rows with the same title/name/text/description are **merged**; no field definitions, no registry, no list of categories; granted to ~15 agents (write) / ~11 (read); the Diarist can write but not read |
| Media | `books` (status reading/read/abandoned), `films`, `music` as archive categories — no "recommended" / "want to see", no viewings |
| Food, sleep, exercise | one value per day on the daily log (`tools/logger.py`) — a second meal or workout replaces the first |
| Day shape | its own store (`tools/day_shape.py`), written by the interviewer, read by the day planner |
| Knowledge manifest | `_knowledge_manifest()` names the wisdom subjects that hold entries — **derived by enumeration, never hand-written, contents never shown**. The precedent this plan generalises |
| Location | `tools/location.py`: coordinate → named zone, discarded inside `record_position()`; only zone **transitions** stored; no trail; nothing polls. Positions arrive only when the user sends a message with location on, or taps share |
| Place lookup | `tools/places.py`: `find_places` (Logistics, Recreation's category) and `geocode_place_name` — **by name only**, so the vendor never learns the user's position (Mike, 2026-08-28). Results are used once and discarded. Needs `GOOGLE_PLACES_API_KEY` on the VM — **set and working, checked 2026-11-21** (§ 9, M1) |
| Capture | `other` kind + `capture/uncategorised.jsonl` + `raise_new_categories` (5 in 30 days → a developer Inbox alert). `KIND_HOMES["place"]` = archive, contacts, agent config, profile |
| Pattern Miner | no grant on the archive store, places or location history |
| Who else is present | nothing in the system knows — ruled the user's risk (R15) |

---

## 2. Rulings — Mike, 2026-11-21

### The interview

1. **R1 — One concept: "data objects."** *"Lists and logs are not separate things. All of it
   falls under 'data objects'. Form follows function."* Media lists, health logs, day shape,
   food/sleep/exercise are all examples.
2. **R2 — Fields are the user's.** Users can add custom fields (genre, who to recommend to);
   where fields are not comprehensive, a free-text notes blob per entry, pulled by agent query.
3. **R3 — Writes land just after the reply.** *"Overnight is too much delay for something
   that's infrequent enough to not be batched."* Immediate is ideal only if it adds no latency.
4. **R4 — The restriction beyond the Alpha guards cost and quality** — not privacy, not a paid
   tier. Iva has the feature now, as `mike` does (assumed in-session, not contradicted).
5. **R5 — Unasked objects: create, and tell the user.** *"User can always push back."* Undone
   objects are **archived out of view, never deleted.**
6. **R6 — Promotion means "present by default."** A promoted object becomes a template every
   user has, empty, found by agents through the registry. Code wiring comes only when a feature
   proves fundamental — *"this is more for information."*
7. **R7 — Place sources:** what the user says (*been to*, *going to*), the calendar, the user's
   lists, and location reports. *"The Boots pharmacy in Greenwich can be looked up by Metatron
   to populate where it is."* Visited **and mentioned** places go into one place log with notes.
8. **R8 — Retention, option (a):** only named or known places are recorded as places. Metatron
   **asks about unnamed places that keep arising — both in conversation and in location
   reports.**
9. **R9 — Background location: built in, optional per user, default OFF.**
10. **R10 — Unprompted mention is essential** (*"essential to Metatron being anticipatory"*), and
    **"not again" places are raised to steer away**, never left unmentioned.
11. **R11 — No hard cap on mentions; relevance is the gate.** Quiet hours and focus blocks need
    no special rule (the user is at a known place then). Metatron cross-references places for
    interests, errands and other users nearby.
12. **R12 — Routine places are logged as visits.** *"The more data the better, especially for the
    pattern miner."* Metatron decides what is routine or exceptional.
13. **R13 — Visits are kept forever.** Places centred on the children are the account holder's
    places (*"Mike goes to these locations, so they're his"*).
14. **R14 — Viewing:** read aloud, an in-app screen, a file — all three, possibly premium.
15. **R15 — Failure guards:** mention frequency is adjustable; **unwanted objects and wrong
    verdicts must not happen**; someone else reading the screen is **the user's risk, like any
    other app**; uncomfortable history is kept, and the guard is on what Metatron says.
16. **R16 — Pattern Miner gets access to all user data and logs** — *"we haven't touched Pattern
    Miner in a long time."*

### The edges

17. **R17 — An object nobody wanted (edge 1):** its entries **move to where they belong**
    (`merged_into` pointer, archive-on-merge) when relevant; otherwise archive out of view. **The
    creation bar is that no reasonable home already exists.** Creation will be frequent in a
    user's first weeks and rare once the base objects cover common use.
18. **R18 — Name drift (edge 2):** one name, aliases, a one-line description; code resolves;
    ambiguous → ask, and the answer becomes an alias; never a second object for a close match.
    **Every name the user uses for an object is tracked.**
19. **R19 — Shape drift (edge 3):** fields optional; adding one never rewrites old entries;
    removing one hides it, never deletes values.
20. **R20 — Merge vs append (edge 4): relational.** A thing (a film) and its occurrences (each
    viewing) are both recorded, so *"how many different movies have I seen"* and *"how many
    times have I watched a movie"* are both answerable. *"Recording the data is the important
    thing. It can always be curated according to need."* **Data is never needlessly deleted.**
21. **R21 — Promotion across users (edge 5):** a **central place where names are compared and
    frequent ones recognised and promoted** — a developer-only report on the VM; analytics rows
    stay content-free (`ROADMAP.md` § A9). Rejected: a model judging similarity across users'
    content (mingles two users in one prompt).
22. **R22 — Reverse geocoding (edge 6): never, for now.** An unnamed spot is described relative
    to known places and times, and the user names it. Nothing about the user's position leaves
    the machine. A VM-hosted offline lookup is parked (§ Later builds).
23. **R23 — Background location consent (edge 7):** a versioned record in
    `data/personas/{p}/consents.json`, like `correspondence_read`; no record → the server refuses
    background reports, **for every user, `mike` included.**
24. **R24 — The 2026-08-28 location ruling is amended (edges 7–8),** in exactly these terms:
    - visits to named places are logged — already true for zones;
    - recurring **unnamed** spots are held as a point rounded to ~100 m, a visit count and visit
      times, after a minimum stay;
    - background reports are accepted when the user has switched them on;
    - **coordinates still never enter a model prompt** — code computes *"Bianco 43 is 400 m
      away"* and the model sees only that.

    An unnamed spot the user declines to name is **kept, but hidden**. Marking anything
    **private** removes it from day-to-day mention; **Pattern Miner still sees it.**
25. **R25 — Proximity (edge 9): relevance, not nearness.** *"108 Brasserie is only good if
    scheduling a meal, shouldn't be mentioned otherwise."* Places near where the user is or will
    be are **searched or filtered by the Synthesizer** for the situation at hand.
26. **R26 — Agent relevance (edge 10):** at creation, an object is tagged with the agents it
    matters to, and each agent is given its linked list of object names so it can query them
    immediately (*favourite bike trails → Physical Health, Logistics, Recreation*). **The reverse
    check runs when an agent is created.** A health-classed object is therefore readable by the
    health agents, and its clinical-safety review is owed at the before-Alpha A4 re-run
    (`ROADMAP.md` § 0; same deferral as capture's `health` kind, 11-20).
27. **R27 — All user data is treated the same (edge 11).** Not one merged store: every store —
    lists, wisdom, contacts, places/zones, day shape and the rest — is user data, registered and
    reachable the same way. **Nothing is moved or changed now.** *"We don't want a general
    procedure co-opting the specialty procedures that are more nuanced. General procedure is
    default only if there's no specialty governance."*
28. **R28 — Capture's homes (edge 12):** the data-object write becomes a home for `place`,
    `event`, `health` and `other`; `other` alerts become candidates for new objects.
29. **R29 — Limits (edge 8):** set high now, while the generic set is built from real use;
    restrict significantly once user testing has established baseline objects. **When an object
    is made universal, the code/procedure that should go with it is addressed at the same time.**
30. **R30 — The object list's prompt placement (edge 14):** in the per-turn part, never the
    cached prefix; *"a borderline case; a user won't be creating new data objects all the time."*
31. **R31 — Taste-shaped research (edge 15):** both — a generic search filtered on the VM, and a
    search carrying genres or titles, have a place.

### After the adversarial review (Mike, 2026-11-21)

33. **R33 — One rounded last position may be kept** (review finding 2, option b). A single
    row — the latest report's point rounded to ~100 m and its time — **overwritten by every
    report, never appended**, so there is still no trail. It is what `places_near` measures
    from when the user is `away`, and what times a stay across a restart. Never in a prompt.
    A further amendment to the 08-28 ruling, alongside R24.
34. **R34 — While only development users are involved, Metatron ASKS before creating an
    unasked object** (review finding 4): *"Want me to start a list of the places you've
    mentioned wanting to try?"* — created only on yes. The yes/no answers are the measure;
    R5's create-and-tell becomes the default once the yes rate shows the offers are reliable.
    The developer alert is unchanged. Rejected: a shadow period with a review list (Mike chose
    asking, which measures and serves at once).

### Later builds

32. **R32 — Recorded, not built**, and parked in `archive/plans/future_phases.md` § Family Mode
    and Cross-User Coordination so Family mode picks them up:
    - **agent-to-agent matching between mutual contacts** — agents compare notes without
      either user authorising first, and the users are told only when both would want to meet;
    - **Family mode location and activity sharing** — *Iva running late shifts dinner to Mike*;
    - the offline map lookup, and separating user data from system state in the persona folder.

---

## 3. The design

### 3.1 One registry, every store

**`tools/data_objects.py` (new)** owns a per-user registry:
`data/personas/{p}/data_objects.json` — in the user's folder beside the archive, **not inside
it** (review finding 10: every filename in `archive/` is a category, so `read_archive` /
`write_archive` — ~15 agents and `core/build/manifest.py` — would read or rewrite a registry
kept there). `read_archive`/`write_archive` also refuse category names starting with `_`.

Each entry:

```yaml
id: cardiac_events            # stable, never reused
name: Cardiac events
aliases: [heart log, cardiac log, the log]   # R18 — every name the user has used
description: Times the heart monitor recorded something, with the reason.   # one line
store: archive                # archive | wisdom | contacts | places | day_shape | tasks | profile | agent_config | log | goals | calendar
identity: occurrence          # thing | occurrence | thing+occurrences  (R20)
fields: {at: datetime, reason: text, notes: text}   # all optional (R19); `notes` always present (R2)
relevant_agents: [physical_health]                  # R26
class: health                 # optional; health → both health agents (R26)
status: active                # active | archived | private  — never deleted (R5, R24)
merged_into: null             # R17
origin: asked                 # asked | noticed | template:<id>
created: 2026-11-21
```

- **Existing stores are registered, not moved (R27).** Wisdom, contacts, day shape, tasks,
  profile, each agent's config, the daily log, goals and the calendar each get an entry with
  `store:` set. Reads go through the common read tool; **writes are handed to that store's own
  tool**, which keeps its protections (contacts' placeholder refusal and duplicate gate, the
  location tier, the guarded medication profile). The general procedure applies only where
  `store: archive`.
- **Templates are config, not code** — `config/data_objects/*.yaml` (films, books, music,
  places, meals, sleep, exercise, health events). A template is "present by default" (R6): every
  user's registry lists it from day one, empty. Promotion = adding a template file after
  Mike reads the cross-user report (§ 3.6), **plus** whatever code the object then needs (R29).
- **Limits** — `config/modules/data_objects.yaml`: active objects listed to an agent (start
  high, e.g. 60), detection threshold, visit dwell, rounding. Tightening = a config edit;
  nothing is deleted when it tightens — the least-used objects drop out of the lists and stay
  queryable (R29).

### 3.2 Things, occurrences, and edits that keep history

The archive store's whole-file JSON stays; a category with a registry entry gains:

- `identity: thing` — today's merge behaviour (same title updates the row);
- `identity: occurrence` — **always append** (cardiac; fixes the merge that is wrong for events);
- `identity: thing+occurrences` — one row per film, and each viewing appended to its
  `occurrences` list with date and notes (R20).

**A repeat `write_archive` call keeps today's meaning — "the same thing", merged — for every
category, templated or not** (review finding 1). Today's merge is what absorbs agents filing the
same book at mention and again at completion; reinterpreting a repeat as a second reading would
turn that habit into false data, in a store nothing is deleted from. **An occurrence is recorded
only by an explicit occurrence write** (`write_data_object` with `occurrence: {at, notes}` — "watched
it", "read it again"), never inferred from a repeat. `identity: occurrence` objects (cardiac) are
the exception: there every write is an entry, because that is the object's declared shape. **No
conversion of existing rows:** a flat row in `films.json` / `places.json` reads as a thing with no
occurrences.

**Edits never overwrite.** An amended entry keeps `previous: [{value, changed_at}]`. **Plan's
choice** — the cheapest form of "never needlessly deleted" that still lets a reader show the
current value. Categories with no registry entry behave exactly as today.

**The cardiac log** (`archive/cardiac_events.json`) is registered `identity: occurrence`,
`class: health` — the first real object.

### 3.3 Tools

| Tool | Does | Notes |
|---|---|---|
| `list_data_objects` | names + descriptions of the user's active objects | read-only |
| `read_data_object` | an object's entries, filtered by field/date, or a count (distinct things vs occurrences) | resolves aliases (R18); **waits briefly for a pending write to that object** (§ 3.4) |
| `write_data_object` | create, add an entry, add a field | hands off to the store's own tool when `store ≠ archive` (R27); refuses to create when an existing object matches closely, returning the match instead (R18) |
| `amend_data_object` | change an entry (keeps history), rename, add an alias, archive, mark private, merge into another (R17) | — |

`write_archive` / `read_archive` keep working, with the identity rule from § 3.2, so no
existing grant has to change for behaviour to improve.

**The common read tool does not widen any agent's reach** (review finding 7). `read_data_object`
serves a registered non-archive store **only to an agent that already holds that store's own
read tool** (checked in code against the caller's allowlist, independent of
`METATRON_TOOL_PERMISSIONS`), and it returns content through the same `tools/untrusted.py`
wrapping that store's own tool applies (calendar, contacts, intake). Otherwise it refuses,
naming the store. `relevant_agents` decides what an agent is *told about*; the allowlist decides
what it may *read* — the manifest never lists an object the agent cannot read.

**Stores with no model-callable read tool** (verify finding NEW 1) — places/zones/visits and day
shape today, and every `store: archive` object — are served to the agents in that object's
`relevant_agents`, and to nobody else. Location-tier stores return **names, counts, times and
code-computed distances only** — never a coordinate (the visit summary of § 3.9).
**Pattern Miner (R16) is the one standing exception: it is in every object's `relevant_agents`
by rule**, and phase 5 grants it the native read tool of every store that has one — `read_contact`,
`read_calendar`, `read_goals`, `read_profile`, `read_log`, `list_tasks`, `read_archive`,
`read_agent_config` (it already holds `read_wisdom`). Those grants are listed in § 4 and made
with Mike.

### 3.4 Who writes, and when (R3, R5)

- **Asked for ("log this separately").** The Coordinator resolves the object against the
  registry in code before the Synthesizer speaks, so the reply can say *"I've started a heart
  log"* / *"added to the heart log"*. The write itself goes to the **Diarist, which is already
  fire-and-forget** (code-enforced in `tools/subagent.py`) — **zero added latency, lands seconds
  after the reply** (R3). A per-object pending marker lets `read_data_object` wait out the
  seconds-long window when the user asks to read it straight back.
  **The write is verified, not assumed** (review finding 3): the pending marker names the object
  and the turn; when the Diarist's thread ends, code checks that an entry for that turn landed
  in **that** object. If not — the run failed, used `write_archive`, or filed elsewhere — one
  retry runs **on the reasoning tier** (a different model from the one that just failed, verify
  finding 3), and if that also fails the user is told **without waiting for another turn** — a
  push through the existing FCM path (day planner Stage C) carrying *"that entry for the heart
  log didn't save — want me to try again?"*, and the same note on the next reply. A marker that
  expires unverified raises the same, never silence. The failure is also a quality event, so it
  reaches the backlog sync. **The reply's wording matches what is true at reply time** —
  *"adding that to your heart log"*, not *"added"* (an instruction line in `synthesizer.md`,
  Red, with Mike).
- **Noticed (unasked) — ASK, for now (R34).** Capture's `other` facts are already counted per
  user by category, with no model. **Capture is the detector**: when one user's category reaches
  **3 in 30 days** (config), the candidate is checked against every registered object's name,
  aliases **and description** by one bulk-tier call (not by the label's string — the extractor's
  category names are known to vary, review finding 4), so a match becomes an alias proposal, not
  a new object. A survivor becomes **a code-raised confirmation card** (`tools/confirm.py`
  `request("create_data_object", …)`, the same mechanism the zone suggestion uses), announced in
  the **next reply**: *"Want me to start a list of the places you've mentioned wanting to try?"*
  **The answer is the card, not the reply's wording** (verify finding NEW 3 — the redo question
  was lost to signal-word matching): Yes → `POST /confirm` creates it server-side
  (`origin: noticed`) with the held facts filed in; No → recorded in
  `declined_confirmations.json`, and that category is not offered again unless its count
  doubles; unanswered → expires like any card and counts as neither. **"That belongs in my X
  list" is said in conversation** and handled by `amend_data_object` (alias + move), which also
  declines the card. The yes rate R34 relies on is computed from card outcomes only. The yes rate is reported per user; when it
  shows the offers are reliable, Mike switches the config to create-and-tell (R5).
  > The question arrives on the reply **after** detection, because detection runs after a reply
  > (R3). Asking needs no same-reply timing, which settles the earlier deviation.
- **Derived (meals, sleep, films watched).** **Plan's choice, gated:** the capture extractor
  (already reading every ordinary turn, bulk tier) proposes an `entry` against an existing
  object; code writes it marked `derived` with the source turn. **This writer is built in
  shadow and switched on only after a labelled score**, the capture method — because the
  extractor's worst measured error is inventing values (precision 87%), and R15 says wrong
  entries must not happen.

### 3.5 Agents learn what exists (R26, R30)

- **The manifest.** `_knowledge_manifest()` names wisdom subjects; a sibling
  `_data_object_manifest(agent)` lists **only that agent's relevant objects**, names and
  one-line descriptions, **in the per-turn user message**, never the cached system prompt (R30;
  the 4,096-token floor is untouched). Contents never appear. Derived by reading the registry,
  never hand-written.
- **Relevance at creation.** One bulk-tier call: the object's name, description and fields
  against a one-line remit per agent (read from routing config, not hand-copied) → the
  `relevant_agents` list. Creation is rare, so the cost is negligible. `class: health` always
  adds both health agents.
- **Reverse check.** `scripts/check_data_object_relevance.py` runs the same call for one agent
  across every persona's registry; run when an agent file is added (`docs/CONVENTIONS.md`
  § adding a module gains the step).
- **The Coordinator's pre-fetch.** It already selects wisdom subjects (`KNOWLEDGE_TO_LOAD`);
  data objects ride the same path, so the right specialist receives the entries without an extra
  tool round — R1's *"code or very light models under the hood."*

### 3.6 Promotion (R6, R21, R29)

- `tools/analytics.py`'s daily row gains **counts only**: objects per user, by origin
  (asked / noticed / template), fields added. No names.
- `scripts/data_object_report.py` (VM, developer-only, prints to the terminal, writes nothing
  tracked): every user's invented object names, aliases and field names side by side, grouped
  lexically. Mike reads it and decides what becomes a template. Covers both current users under
  their recorded consent; **a further user without the same consent is excluded by code.**

### 3.7 Places

- **A places object** (template, `identity: thing+occurrences`): name, kind, **verdict**,
  **occasion** (*"pizza near home"*, *"a meal out in this neighbourhood"*, *"avoid"*), notes,
  public coordinates + radius, source (said / calendar / list / location / zone), `confirmed`,
  `private`. Occurrences are visits and mentions.
- **Looked up by name when said** (R7) — `geocode_place_name`, already ruled acceptable.
  **Plan's choice for an ambiguous name** ("Boots, Greenwich"): take the result nearest the
  stated area, mark `confirmed: false` until a visit or the user confirms it — a wrong branch is
  a wrong place (R15).
- **Zones stay as they are** (R27): `zones.yaml`, its one confirm-gated write path, and the
  location tier are unchanged. `zone_for()` additionally matches places that have coordinates,
  so a visit to Bianco 43 is a transition like a visit to home. Home, school and the Wharf are
  registered as places through the zone entries.
  **One lookup for "a known place's coordinates"** (review finding 9): `location.known_places()`
  returns zones and coordinate-bearing places together, and **every reader that resolves a
  zone name today switches to it** — `tools/day_plan.py` `_zone_coords()` / `_start_point()` and
  the `load_zones()` name check in `tools/obligations.py` (~2168). Otherwise a user who arrived
  at a place would have the day planner fall back silently to `home` as the start point, and
  travel times and "leave now" would be computed from the wrong place. Test 4 pins it.
- **The last position (R33):** `location_last.json` — one row, the latest report's point rounded
  to ~100 m and its time, **overwritten** by `record_position()` on every report. It is what
  `places_near` measures from when the current zone is `away`, and what dwell timing starts
  from. Never in a prompt; code returns distances only.
- **Unnamed spots (R8, R22, R24) — built in phase 4, with the background feed** (review
  finding 6: message-time reports alone cannot establish a stay or three visits).
  `location_candidates.jsonl` — a point rounded to ~100 m, a count and visit times, never readable
  by a model. **A stay is measured at departure, not by two reports at one point** (verify
  finding NEW 2 — the background feed fires on movement, so a stationary phone sends nothing):
  when a report arrives that is more than ~200 m from `location_last.json`, the gap between that
  row's time and now is the stay at the previous point. A stay of at least the minimum (**plan's
  choice: 10 minutes**) at an `away` point is a visit. **A visit joins an existing candidate
  within ~150 m**, not only one in the same rounding cell, so two fixes at one real spot that
  round to neighbouring cells still count as one place. The movement feed's threshold is set so
  departure is reported (Android's significant-motion trigger plus a coarse distance filter). At **3 visits**
  (config), code raises a question described relative to known places and times — no reverse
  lookup. Named → it becomes a place, its visits carried over. Declined or ignored → kept,
  `hidden`. **Phase 3 covers unnamed places that keep arising in conversation** (R8's other
  half): capture's `place` facts with no matching place, three mentions → the same question.
  > The rounded points are coordinates the 08-28 ruling said would never be stored. R24 and R33
  > are the amendment; `tools/location.py`'s module docstring is rewritten to state them, so the
  > code's own account of its tier stays true.
- **Mentions (R10, R11, R25).** A code-only first pass, no model:
  `places_near(where, occasion)` — *where* is the current zone, the last report, or a planned
  location from the day plan; it returns names, distance (computed in code), verdict and
  occasion, filtered by occasion match, open-now where known, and `private`. The Synthesizer
  calls it, or receives its result, when an occasion arises: planning a meal, a free slot, an
  errand. **"Avoid" places are returned whenever their occasion matches.** A small
  `place_mentions.jsonl` records each raise and the user's response, so a declined suggestion
  waits until the occasion or verdict changes (**plan's choice** — R11 sets no cap; this is
  memory, not a cap).
- **Errands.** A task gains an optional `place` reference, so *"you're near Boots and the
  prescription is ready"* is a join in code (`tools/obligations.py`).

### 3.8 Background location (R9, R23)

- **Android:** OFF by default; switching it on shows the versioned consent text
  (`config/consent/location_history_v1.md`). Two feeds, **plan's choice**:
  1. **Geofences for known places** (Android's geofencing API): the phone holds the public
     coordinates of the user's nearest ~100 places and reports **"entered Bianco 43"**, never a
     coordinate — the cheapest feed and the closest to the 08-28 tier;
  2. **Significant-movement reports** (not a timer) for unnamed-spot detection and `places_near`,
     sent to `POST /location` with a `background` flag and handled by `record_position()` like
     any other report.
- **Server — one gate, both feeds** (review finding 8). A geofence report carries a place id,
  not a coordinate, so it cannot pass through `LocationPing` (required `lat`/`lon`) or
  `record_position()`. It gets **its own endpoint**, `POST /location/visit` (`{place_id, event:
  enter|exit, ts}`), which records the transition by name. **Both** it and `POST /location` with
  `background: true` call one check, `consent.require(persona, "location_history")`, and refuse
  without a current record — fail-closed, every user, `mike` included (R23).
- **Consent scope:** `core/consent.py` gains `location_history` in `CURRENT_VERSIONS` and
  `APP_SCOPES`, so the app can grant and withdraw it like `correspondence_read`.
- **Place coordinates to the phone:** `GET /location/geofences` returns the public coordinates
  and radius of the user's nearest ~100 non-private places, behind the same consent check. The
  phone re-fetches it when it reports a significant move. These are places' positions, never the
  user's.

### 3.9 Pattern Miner (R16, R24)

Granted the common read tool and a code-built visit summary (visits by place, day and duration —
never coordinates). It sees `private` entries. **A grant and agent-file change: Red.**

### 3.10 Capture (R28)

`KIND_HOMES`: `place` gains `write_data_object`; `event`, `health` and the new `entry` likewise.
`raise_new_categories` keeps its developer alert, and gains the per-user creation path in § 3.4.

---

## 4. Files by change tier (`.claude/settings.json` is the authority)

**Collision warning, checked 2026-11-21:** 22 files are uncommitted in the working tree from
another chat (goal–task network phase 2) — including `core/orchestrator.py`,
`tools/subagent.py`, `tools/obligations.py`, `config/agents/coordinator.md`, `synthesizer.md`
and both routing files — plus WhatsApp work in `android/`. **The build starts after those land**
and re-reads each file then. Check `archive/plans/parallel_chats_index_*.md` for ownership.

| Tier | Files |
|---|---|
| **Denied** (Mike makes the change) | `data/personas/{p}/…` — registering the cardiac log, the seeded registry, the consent record — run on the VM by Mike through a script, as the cardiac rebuild was |
| **Red** (prompts; not delegated) | `config/modules/routing.yaml`, `routing_cloud.yaml` (new tools to the agents that need them; Diarist read; **phase 5: Pattern Miner gains `read_contact`, `read_calendar`, `read_goals`, `read_profile`, `read_log`, `list_tasks`, `read_archive`, `read_agent_config` and `read_data_object`**) · `config/agents/coordinator.md` (resolve and pre-fetch objects), `synthesizer.md` (announce creation; use `places_near`; avoid-places), `diarist.md` (write data objects), `pattern_miner.md`, `capture_extractor.md` (the `entry` kind) · `core/scheduler.py` **only if** a job is needed — **plan's choice: avoid it**; detection rides the existing `capture_weekly_rollup` job and the per-turn capture stage |
| **Amber / Green** | `tools/data_objects.py` (new) · `tools/diarist.py` (identity rule, history) · `tools/capture.py` · `tools/location.py` (places in `zone_for`, `known_places()`, `location_last.json`, candidates, docstring) · `tools/places.py` (`places_near`) · `tools/obligations.py` (task → place; zone-name check → `known_places()`) · `tools/day_plan.py` (`_zone_coords` / `_start_point` → `known_places()`) · `tools/analytics.py` · `core/orchestrator.py` (manifest, pre-fetch — check the A8 claim first; both new helpers belong beside `_knowledge_manifest` / `_resolve_knowledge`) · `core/server.py` (background flag, `POST /location/visit`, `GET /location/geofences`, the consent check) · `core/consent.py` (`location_history` scope) · `config/data_objects/*.yaml`, `config/modules/data_objects.yaml`, `config/consent/location_history_v1.md` · `android/…` (geofencing, background reports) · `static/index.html` (the switch) · `scripts/data_object_report.py`, `scripts/check_data_object_relevance.py` · `docs/CONVENTIONS.md` · tests |

---

## 5. Build order

Each phase ships, is checked live, and leaves the next optional. **Phases 1–2 deliver need 1;
3–4 need 2.**

1. **Registry, the general store, and the asked-for path end to end** (review finding 5 — the
   live check needs the writer and the tagging, so both are here) — `tools/data_objects.py`,
   the registry file outside `archive/`, identity rules and edit history, the four tools with
   the read-reach rule, templates, the seeded registry (existing stores registered), the cardiac
   log registered, **relevance tagging at creation**, the per-agent manifest, the Coordinator's
   resolution and pre-fetch, **the Diarist write with verification and retry**. All grants for
   this path made once (Red, with Mike). *Live check: "start a log of …", add three entries,
   "read me the … log" straight away, change one, archive it — on `mike`.*
2. **Noticing and promotion** — capture as detector, **asking** (R34); the reverse-check
   script; cross-user report and analytics counts. Then the **derived writer in shadow**,
   scored on labelled turns before it writes for real.
3. **Places** — the places object, lookup-by-name, places in `zone_for`, **`known_places()` and
   its three readers**, `location_last.json`, `places_near` and the mentions memory, unnamed
   places that recur **in conversation**, task → place, the `location.py` docstring amendment.
   Seed `mike`'s three named places with Mike.
4. **Background location** — consent scope, text and record; the one gate on both endpoints;
   the geofence list endpoint; Android geofences and movement reports; the switch; **unnamed
   spots from location reports** (moved here, review finding 6). Built against the Android tree
   once WhatsApp's work has landed.
5. **Pattern Miner** — the grant and the visit summary (Red).

**Not in this plan:** a Media Concierge agent (R31 and the films/goal example make it possible;
a new agent is a design of its own), viewing screens and export (R14, possibly premium), the
later builds (R32).

---

## 6. Tests — every live meter stubbed

Model calls (relevance check, extractor), the Places API, CalDAV and FCM are stubbed in every
suite; one opt-in live eval per model-judged step.

1. `tests/test_data_objects.py` — create/append/read/amend/archive/merge; `occurrence` never
   merges; `thing+occurrences` counts distinct vs total; an amend keeps `previous`; nothing is
   ever removed from a file (assert line/row counts never fall); alias resolution and the
   close-match refusal; a contact write handed to `write_contact` (its placeholder refusal
   still fires); unregistered archive categories behave byte-identically to HEAD; **a repeat
   `write_archive` of the same film or book merges and adds no occurrence, templated or not**;
   **`read_archive("_…")` / `write_archive("_…")` refuse, and the registry file is outside
   `archive/`**; **`read_data_object` refuses a store whose own read tool the caller lacks, and
   wraps calendar/contact content exactly as their own tools do.**
2. **Manifest** — lists only the agent's relevant objects; lands in the user message, **not**
   the system prompt (assert the cached prefix is unchanged by creating an object).
3. **Writers** — pending-write wait on read-back; **a Diarist run that fails, uses
   `write_archive`, or files to another object is retried once and then queues the "didn't
   save" note; an expired marker queues it too**; the detector **asks** at 3 in 30 days, turns a
   description match into an alias proposal, and does not re-offer a declined category; the
   derived writer writes nothing while in shadow.
4. **Location** — **both** `POST /location` (background) and `POST /location/visit`, and
   `GET /location/geofences`, refused without the consent record and accepted with it;
   `zone_for` matches a place; **`_start_point()` resolves a place the user arrived at today, not
   `home`**; `location_last.json` is one row, overwritten, rounded; candidates rounded and
   dwell-gated; **no coordinate appears in any string reaching a prompt** (extend the existing
   location tier test to every new path); `places_near` filters by occasion and `private`,
   returns avoid-places.
5. **Promotion** — the analytics row contains no object name (assert against every field); the
   report excludes a user without consent.
6. **Regression** — `tests/run_knowledge_routing.py --persona danny_park`, the capture suite,
   `test_health_notes_feed.py`; `scripts/check_agent_tools.py` after the grants.

**Live checks after deploy (Mike, guided):** the phase 1 log walk-through; a place said aloud
gains coordinates; a meal being planned near home raises Bianco 43 and nothing raises 108
Brasserie on a walk past; background location stays off until switched on.

---

## 7. Cost

Prices are from `config/modules/spend_guard.yaml`: bulk `gemini-3.5-flash-lite` $0.30 / $2.50 per
M tokens; reasoning `gemini-3.8-flash` $0.75 / $3.75. **Token counts are estimates.**

- **Build** (Opus tokens): phase 1 ~0.7–1.0M · phase 2 ~0.5–0.7M (+ labelling the derived
  writer, ~25 min of Mike) · phase 3 ~0.6–0.9M · phase 4 ~0.5–0.8M (Android) · phase 5 ~0.2M.
  **~2.5–3.6M Opus** in total, plus ~0.15M Fable per review: this plan, then each phase's diff.
- **Run, per user per day:**
  - manifest: ~20 tokens per listed object; at 20 objects to the Synthesizer, ~400 input tokens
    per turn on the reasoning tier ≈ $0.0003; **at 20–50 turns ≈ $0.006–0.015/day**;
  - relevance check at creation: one bulk call (~1,500 tokens) ≈ $0.0005 per object, a few
    dozen in a user's first weeks, then near zero;
  - explicit entries: the Diarist is already dispatched for log-worthy turns — the marginal cost
    is one tool round on its tier, under $0.001 per entry;
  - derived entries: added extractor output only (~50 tokens/turn on the bulk tier) ≈
    $0.0001/turn, **≈ $0.005/day**;
  - places: `places_near` and the visit logic are code, **$0**; lookups by name are a Places API
    call per new place name (price **not checked** — read the Places pricing page, Essentials
    field mask); background reports cost server CPU only, **no model call per report** (R25's
    code-first pass);
  - **total ≈ $0.01–0.03/day per user**, ~1–2% of Mike's $1.50–2.00/day.
- **Ancillary:** Pattern Miner's scheduled runs grow with the data it is now granted — measure
  its input tokens before and after phase 5; the Synthesizer's input grows with `places_near`
  results on the turns they appear; disk is kilobytes (registry, mentions) to low megabytes a
  year (visits, candidates).
- **Unseen:**
  1. **A dead detector reads as "no new objects needed."** The capture report prints how many
     categories crossed the threshold and how many objects were created.
  2. **Android stopping background reports** (battery optimisation, a revoked permission) reads
     as "stayed home." The location report shows the last background report time per user.
  3. **A missing Places key silently disables lookup by name** — it is set and working as of 2026-11-21, but nothing would report it lapsing; the
     check in § 9 M1 is the re-run.
  4. The manifest's per-turn tokens show in the A9 rows; **no meter flags growth** — the cap
     (R29) is the bound.
- **Things that persist** (the three questions):
  - **Registry and data objects** — (1) bytes, kilobytes per user; (2) nothing deletes them, by
    ruling (R5, R20); a restart leaves them intact; (3) no meter, none needed at this size.
  - **Visits (`location_transitions.jsonl`) and candidates** — (1) bytes, ~60–100 per visit, low
    MB a year; (2) kept forever by ruling (R13); restart-safe; (3) no meter.
  - **Pending-write markers** — (1) bytes, one per in-flight write; (2) deleted by the write
    being verified, and expired by timestamp after 2 minutes — an expiry raises the "didn't
    save" note, so a crash mid-write leaves nothing that waits forever or fails silently; (3)
    the failure is a quality event, so the backlog sync reports it.
  - **`location_last.json`** — (1) bytes, one row per user; (2) overwritten by each report,
    never appended; a restart keeps it (that is its purpose, R33); (3) no meter, none needed.
  - **The per-name geocode cache** — in memory; a restart empties it and costs re-lookups. **Plan's
    choice:** store the coordinates on the place itself, so the cache matters only for names not
    yet saved.

---

## 8. Model for execution, and review

- **Build in Opus 5.5, high effort.** Every phase touches the head layer's prompt assembly or a
  privacy boundary, and the Red files (grants, Coordinator, Synthesizer, Diarist, Pattern Miner,
  the extractor) are done with Mike present — **Red work is not delegated.**
- **Review in Fable:** this plan now (`/adversarial-review`), and each phase's diff before deploy.
  The split earns its cost here: the plan's choices (§ 3, marked) are exactly where a second
  read not anchored on mine pays.

---

## 9. Mike-gated items — each gets a walkthrough session

1. **M1 — DONE 2026-11-21 (Mike, guided):** `GOOGLE_PLACES_API_KEY` is in the VM's `.env`, in
   the running server's environment, and a live `geocode_place_name` of a public landmark
   returned a position. Lookup by name (R7) works today.
2. **M2 — Settled at the review (R33, R34).** The remaining plan's choices stand unless the
   verify round or the build finds otherwise.
3. **M3 — The VM data steps** (registry seed, the cardiac log's registration) — Denied tier, run
   by Mike from a prepared script, as the cardiac rebuild was.
4. **M4 — Labelling the derived writer's shadow sample** (phase 2), ~25 minutes.
5. **M5 — Background location on the phone** (phase 4): switch on, walk to a known place, see
   the visit logged; **stay 10+ minutes at one unnamed spot on three separate days and see the
   naming question arrive** (shortened thresholds on a test config are fine for the first run);
   switch off and confirm reports stop.

---

## 10. Next

1. ~~`/adversarial-review` of this plan (Fable)~~ — done 2026-11-21: 6 structural + 4 local,
   all addressed in this revision
   (`archive/plans/adversarial_review_custom_logs_and_places_plan_2026-11-21.md`). Verify round:
   8 CLOSED, 2 reshaped, 3 new — all five revised the same day and **not re-verified**; the
   phase 1 diff review re-checks the write verification, the read rule and the confirmation card
   against the built code, and the phase 4 diff review re-checks stay detection.
2. A build prompt for phase 1, written after the review's findings are ruled on.
3. `/archive` to close this session.
