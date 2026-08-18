# Follow-up session prompt — continue working the backlog down

Paste the block below into a fresh session.

---

```
/metatron-code

Continue working the backlog down. Previous session (2026-08-18, `/backlog deep` + one
attack round) shipped six Green-tier fixes and merged them; everything I verified is
already done, so this session needs a fresh verification pass before anything can be built.

Read `archive/handoffs/2026-08-18-backlog-deep-and-attack.md` first — it has the full state.

Priorities, in order:

1. **Travel and transit — the largest actionable cluster, and none of it is filed yet.**
   Three separate problems, all Green tier:
   (a) There is no National Rail / Southeastern integration at all. `get_tfl_status` covers
       TfL modes plus named National Rail *operators*, never stations — so Greenwich-line
       and Southeastern queries return nothing. This is why transit looks operational when
       it isn't: TfL works, National Rail was never built.
   (b) The tool assumes Mike is travelling when he is dropping someone off (~6 machine-log
       entries, twice on flight BA 892). This is an inference failure about *who* is
       travelling, not a data-feed gap — different fix, do not merge it with (a).
   (c) The research agent returns blank or `NoneType` for live web queries (TfL, weather),
       so a transit question silently returns nothing.
   Open backlog items for each, then verify (c) against current code before building — it
   may be the shared root of (a) and the empty Southeastern results.

2. **Verify a fresh batch from `## Later` before building anything.** The standing rule is
   that no item is acted on from its own description; a 2026-08-05 sweep found a third of
   checked items stale, and this session found one Inbox item whose described bug did not
   exist in the code at all. Fan out to at most 3 workers, `model: "sonnet"`, no isolation
   flag, ~78k median each. Good candidates, all Green:
   - `[DB-0810-07]` The Book's new fields have never run against a real exchange
   - `[DB-0810-14]` A4 clinical suite has never run with a response language set
   - `[DB-0810-10]` The calendar conflict build has never had a live scheduling exchange
   - `[DB-0810-11](a)` Contact name matching is naive substring — Jon/Jonathan/Jonathan
     Whitfield become three records
   - `[DB-0815-08]` One cheap check: can Gemini reasoning content reach `text_parts` on the
     streaming path? If yes, the Synthesizer's instruction leak is a plumbing fault.

3. **Two runs are owed and both are cheap.** Neither needs a build:
   - `python tests/run_a4_safety.py --persona sarah_chen --provider gemini --suite clinical
     --complexity quick` — approx $0.02, closes `[DB-0808-17]`. The flag shipped; the run
     did not.
   - `python3 scripts/check_agent_tools.py` **on the VM** — closes the persona-file half of
     `[DB-0810-03]`. A Mac run proves nothing: `config/personas/mike/` is gitignored and
     VM-only, and the guard now says so itself when `mike` is absent.

4. **Red tier, if Mike wants it worked:** `[DB-0810-03](c)` — 39 tool-grant decisions
   (35 named-but-not-granted, 4 new denials). Judgement per grant, not delegable to a
   worker, blocks A7 check 10.

Reporting rules for this session, all corrected the hard way on 2026-08-18:
- **Lead with WHAT the tool does differently for a user, then a little of the how.**
- **Name a defect by what a user sees**, not its mechanism. "Answers appeared twice", not
  "a reconnect leaves two sockets open."
- **Cluster at the ITEM level** — group `DB-` to-dos by feature so a feature can be retired.
  Never cluster machine-log signatures; those are evidence a problem is real, not work.
- **Omit anything `@waiting:` or `@session:`.** The point of a backlog pass is what can be
  done now.
```

---

## What the next session must NOT redo

- **Cluster A (standing preferences not sticking)** — parked deliberately. The last user
  correction predates the fix by three days and the whole machine log went quiet in that
  window while the VM was OOM-killing itself, so the silence proves nothing either way. It
  needs a week of normal use, not investigation.
- **The TfL "station-to-line-ID mapping" Inbox item** — verified as mis-triaged; that bug
  does not exist in the code. The real event is the empty research-agent search, item 1(c)
  above.
- **`[DB-0808-16]`** — closed, already fixed by `7c70cd9` back on 08-08.
- **`_WORLD_AFFECTING` in `tools/analytics.py`** — left untouched on purpose. Whether a
  contact merge counts as absorbed work sets the headline metric and is Mike's call per
  `ROADMAP.md` § A9a.
