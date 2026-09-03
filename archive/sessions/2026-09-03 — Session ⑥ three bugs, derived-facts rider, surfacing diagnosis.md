# 2026-09-03 — Session ⑥: three bugs, the derived-facts rider, the surfacing diagnosis

Model: Opus 5 (build). Green/Amber only; agent-file findings staged as proposals, not edited.

## Scope

| # | Item | Status |
|---|---|---|
| 1 | `[DB-0829-01]` log recorded an email as sent while awaiting approval | in progress |
| 2 | `[DB-0902-01]` ROUTING_MISS events record successes | pending |
| 3 | `[DB-0902-02]` the two inbox jobs disagree about the same inbox | pending |
| R | `[DB-0822-06]` derived-facts line (rider) | pending |
| D | `[DB-0822-09]` surfacing-half diagnosis | pending |

## Evidence pulled

VM traces copied to scratchpad over IAP: `2026-08-29.jsonl`, `2026-08-30.jsonl`,
`2026-09-02.jsonl`, `logs/quality_events.json`.

## Item 1 — the filed premise was half wrong, corrected from the trace

The backlog says "the Coordinator dispatched a log write recording the send as fact". The
trace splits that into two writes with **opposite** outcomes:

- **Record 14, 13:00:10 — the `relationships` specialist.** Sequence in one agent:
  `search_contacts` → `get_tone_shape` → `send_email` (returns `PENDING_CONFIRMATION`) →
  `write_log`. Its log content was **correct**: *"Initiated outreach to Iva Diamond regarding
  a call next week. Pending user approval in the app."* The agent that saw the gate fire got
  it right.
- **Record 13, 13:00:12 — the fire-and-forget Diarist**, on its own thread and its own trace,
  dispatched with the Coordinator-authored directive *"Log that user sent an email to Iva
  Diamond to coordinate a call for next week."* It wrote **"Sent an email to Iva Diamond to
  coordinate a call for next week."** — the false record.

So the offender is the **Diarist**, and the cause is dispatch ordering: the fire-and-forget
thread starts ~1.6 s into the turn, *before* the blocking specialist calls `send_email`, so
the Diarist can never see that the gate fired. The Coordinator wrote the directive in the
future tense of an action it expected to succeed.

Second, independent finding from the same record: the Synthesizer's *"That's sent to Iva."*
**did not match** `_COMPLETION_CLAIM_RES`, so `enforce_pending_receipt()` took the *append*
branch, not the replace branch. The user saw the claim and the correction stacked together.
`that's <verb>` only covers `done|sorted|taken care of`.

Third: `core/actions.py` has two states (completed / ATTEMPTED AND FAILED). A gated call is
neither, so `send_email` was reported `completed` — to the Synthesizer and to the journal.

### What was built for item 1

1. **`core/actions.py` — a third outcome.** `_gated()` reads `PENDING_CONFIRMATION` /
   `DECLINED_RECENTLY` from the tool's own returned status on the trace record. The line
   now reads `send_email — AWAITING THE USER'S APPROVAL: NOT performed`, and gated rows
   sort above completions. Same change fixes the journal line, which is generated from
   the same block.
2. **`core/orchestrator.py` — fire-and-forget dispatch deferred.** FF agents are now
   collected during the dispatch loop and started *after* the blocking specialists
   return, so the confirmation store is authoritative when the directive is handed over.
   `pending_directive_note()` appends a system-generated PENDING block naming the action
   and its description, and flags (as a `FALSE_COMPLETION_CLAIM` quality event) a
   directive that asserted a gated action done. Appends rather than suppresses: losing
   the turn's other content is the worse trade.
3. **`_COMPLETION_CLAIM_RES` widened** so `that's <verb>` covers sent/merged/added/etc.

`tests/test_pending_action_record.py` — 13 checks, **9 failed on HEAD** including the
live *"That's sent to Iva."* text verbatim.

## Item 2 — `[DB-0902-01]`, worse than filed, and the fork resolves to "both"

Filed as 5 instances. Live count is **15 since 09-01, still firing on 09-03**.

The break is exactly dated and the cause is not what the fork's first branch assumed:

| Period | ROUTING_MISS events | Noise |
|---|---|---|
| 2026-06-22 → 2026-08-29 | 19 | 0 |
| 2026-09-01 → 2026-09-03 | 15 | 13 |

Three clean months, then the 09-01 fleet migration, with no code change between. The
pre-09-01 events are genuine and valuable — several became work, including session ⑤'s
referent fix. `coordinator.md` **never defines ROUTING_MISS**; only `synthesizer.md`
does. 3.1 Pro inferred it, 3.7 Flash does not.

**Built (Green):** `tools/logger.py` `asserts_routing_success()` refuses a ROUTING_MISS
whose detail claims the routing worked and names nothing that went wrong. Tuned for
precision because the two errors cost differently — dropping noise costs nothing,
dropping a real fault costs the signal. Measured on all 34 live events: **0 of 21
genuine rejected, 8 of 13 noise rejected.** Negation handling is load-bearing: *"Agents
not called successfully"* (2026-06-26) is a real miss that a naive keyword rule eats.

**Staged (Red):** the coordinator.md definition that would close the remaining five —
`archive/plans/red_proposals_2026-09-03_session_six.md`.

## Item 3 — `[DB-0902-02]`, the suspect was right, the mechanism was not

The 08-30 14:45 pair, same agent, same minute, different tools:

- **14:45:03 (pipeline)** → `read_intake_queue("logistics")` → `count: 0` → *"I've
  checked the inbox, and there are no new messages."*
- **14:45:29 (direct)** → `read_email(unread_only=true, count=10)` → ten unread.

The queue was **never filled, not drained**. The live store: **24 of 25 intake records
carry `domain: null`, `category: "unclear"`** — the extractor is off behind
`[DB-0820-03]`'s eval gate, the persona has zero `rules:`, and `unclear` maps to a null
domain. Under this configuration `read_intake_queue` returns zero for every domain
permanently, whatever is in the inbox. The cursors file confirms it: no `logistics` key
has ever been written.

**Built:** `tools/intake.py` `_empty_queue()` — the empty answer now carries its reason,
computed from config and the store, and explicitly forbids the sentence Mike heard. Two
independent fact-gathering paths, because a config read that raised was swallowing the
record count, and a clause is only added when it was actually established rather than
assumed. `read_records()` is now read once per call, not twice (the store is append-only
forever). `tests/test_intake_queue_empty.py`, 10 checks.

## Diagnosis — `[DB-0822-09]`'s surfacing half is NOT this split

Asked directly by the handoff. **Answer: no.** On 09-02 both runs called
`read_email(count=15)` — same source. The 11:36 Synthesizer received 21,630 input tokens
including `logistics`' 536-token package carrying the Death Cab and Jimmy Carr
HORIZON_ITEMS, and emitted 177: *"Your focus window remains clear."* The miss is
downstream, in the Synthesizer, and is confirmed rather than suspected. Staged as a Red
proposal with a recommendation (make it structural, not another instruction).

## Rider — `[DB-0822-06]` derived facts, built

The half deliberately not built on 08-27, whose own re-open condition then fired.
`derived_facts()` / `derived_facts_block()` in `core/orchestrator.py` recompute
date-derived counts by subtraction from the date each line was written.

**Validated against reality:** "Day 3" written 2026-08-21 puts day 1 at 2026-08-19, so a
5-day period ends **2026-08-23** — exactly the date Mike's journal records. Two
independently-written counts (08-21 and 08-22) derive the same start and end, which is
internal cross-validation. Run against the four real live log files, all four periods are
correctly reported as ended.

Narrow by design: two forms only (`day N of an M-day X`, `N days since X`), both pure
arithmetic over a stored date. Nothing that needs a judgement about whether a thing is
still true — that is the filtering this item has twice decided against. Feeds from both
recent logs and open threads; returns "" when nothing parses, so a persona with no
derived counts pays nothing. Lands in `augmented_input`, not the cached system prompt, so
the Vertex prefix cache is undisturbed. `tests/test_derived_facts.py`, 15 checks.

## Regression

Full suite: **67 pass, 1 fail**. The failure — `test_persona_resolver.py`,
*"list_personas finds mike"* — is **pre-existing and environmental**: `mike` lives only
on the VM, which owns live persona config, so that check can only pass there. Identical
failure on HEAD with all changes stashed.

A4 not run — suspended, and off the capstone close path (ROADMAP § 0 pt 8, amended
2026-09-02).

## Deferred / not done

- Both Red proposals above — Mike's call, staged not applied.
- The five descriptive-but-not-self-contradicting ROUTING_MISS events: code cannot
  separate them from real reports without semantic guessing. Closes with proposal 1.

---

# Addendum — both Red proposals built the same day (commit `a4a9364`)

Mike approved both in-session. The second changed shape during scoping.

## Proposal 1 — `coordinator.md` ROUTING_MISS definition

Applied as written. Cache-safe by direction (the file grew).

## Proposal 2 — the question that reshaped it

Mike asked: *"How would the code know whether something is of interest?"*

**It doesn't, and shouldn't.** `logistics` makes that judgement and it stays there; code only
guarantees the relay — `_file_wisdom_proposals`' precedent, whose docstring generalises it:
*structured relay in this pipeline means Python parses it.* Across the three runs where
specialist output survives in traces, that judgement is sound: 8 findings, 0 junk.

**But the second-order answer nearly inverted the recommendation.** Jimmy Carr appears in all
three of those runs, the dental appointment in two. Guaranteed delivery with no record of what
was already said would have repeated the same show daily until Sept 13 — `[DB-0822-06]`'s
carried-state failure through a new channel, worse than the drop it replaces. **The
Synthesizer's dropping was doing double duty: the fault and the noise filter.** This killed the
cheaper no-ledger option outright.

**So the Red edit became a format change, not an instruction.** Identity is `(date, venue)` —
a key, not a similarity judgement. Prose could not carry it: the same show was written with no
title string in common across two runs. `logistics.md` now emits JSON.

### Found by the tests, not by review

The first key normalised the venue to a string, so `"The London Palladium"` and
`"the london palladium, London"` did not match — the exact case the design exists for. The key
is now a sorted token **set**: both are `{london, palladium}`, while `{troxy, london}` stays
distinct from `{london}`.

### Two placement decisions, each worth one of a finding's two chances

1. The offer is charged **where the block is served**, not once per turn — a finding filed
   mid-turn was never in the block that turn built.
2. The block is built **after the sign-off veto** — on "over and out" the Synthesizer never
   runs, so an earlier build burns a chance on a reply never produced.

Both asserted against source in `tests/test_horizon_ledger.py` (22 checks), because neither is
visible in behaviour until a finding has already been lost.

### A Red-file contract was updated rather than left to drift

`logistics.md` said *"whether the user hears about it is Synth's call."* Now: *how and when*
are Synth's call, *whether* is not. Leaving that line in place is how code and instruction
drift apart.

## State

Suite 69 files: 68 pass, 1 pre-existing environmental fail. qa_sweep 9/9. A4 not run.
Both items time-gated to 2026-09-12 — `[DB-0822-09]`'s confirm needs delivery **and**
non-repetition, since the second is the risk this build introduced.

**Owes a deploy** (`config/` and `core/` changed).

---

# Live test after deploy — the build works and its input never arrives

Two runs on the VM with the 09-02 directive.

**Read as a pass.** The reply carried Death Cab (Troxy, Sep 26), Jimmy Carr, Iva's dental
appointment and the George School social — exactly the set dropped on 09-02 — and additionally
flagged that SE10 Sukkot falls the same afternoon as the concert.

**Was not a pass.** `data/personas/mike/horizon/ledger.json` does not exist. Nothing was filed.
The items arrived through the Synthesizer's own compliance — the channel that failed on 09-02.

**Cause.** `logistics` emitted no `HORIZON_ITEMS:` line at all. A direct run returned
conversational markdown with none of its documented output format — no `ACTIONS TAKEN:`, no
`FLAGS:`. On 09-02 the same agent on the same model emitted the full structured block. Adherence
varies run to run.

**What this says about the fix.** The Red edit made the *schema* precise — correct, since a
dedupe key cannot be extracted from prose — but left the *emission of the block* resting on the
model filling a template slot. Same class of failure as everything else in this cluster, one
level further out than anyone had looked.

**What closes it.** `record_horizon_item(title, date, venue, kind, detail)` as a tool call
rather than a template slot: structured by construction, cannot be replaced by prose, cannot be
malformed and ignored. The codebase's existing answer for relay that must not be lost. Ledger,
dedupe key, context block and both placement decisions are built and tested — only the input
path changes. One tool (Green), a grant in both routing files (Red), one line in `logistics.md`
(Red).

**How nearly this was filed as a success.** The reply contained every item the backlog entry
named. Only a missing file contradicted it. The confirm as written would have been marked
half-satisfied on the reading alone.

**Positive, recorded as a signal not a confirm.** Three post-deploy sessions produced no
ROUTING_MISS at all; the only quality event was a genuine USER_CORRECTION.

---

# `[DB-0822-09]` closed — the relay becomes a tool call

Third iteration, after the second was live-tested and found inert.

**What shipped.** `record_horizon_item(title, date, venue, kind, detail)` — registered, granted
to `logistics` in both routing files, named in `logistics.md`. A tool call is structured by
construction: it cannot be replaced by prose, its arguments cannot be malformed and silently
ignored, and a refusal is visible.

**Live evidence, in order:**

1. Pipeline run on the inbox directive — **still filed nothing**, though the tool was granted
   and offered (33 tools in the live allowlist). A granted tool is not a used one.
2. Direct run naming the horizon scan — **filed five findings**. A direct run bypasses
   `_file_horizon_items`, so those entries can only have come from the tool.
3. Next pipeline session — **delivered all five unprompted** to a bare "How is my week shaping
   up?".
4. Offer accounting correct: `offers=1`, not 2 — the window collapsed the two head-layer
   context loads into one charge.
5. Gap found and closed: filing happened only when the directive named the horizon scan. Two
   places still said *surface as HORIZON_ITEMS* — the scan header and the intake-queue
   interest-level rule, which is the one the Death Cab email travels through. Both now say
   *file with `record_horizon_item`* (`7aa1f2a`).
6. **The 09-02 case closed on its own terms:** the same failing directive filed Death Cab @
   Troxy, Jimmy Carr, the Bupa dental appointment and the George School social; the reply
   carried all of them; the earlier batch moved to `offers=2`, so non-repetition was observed
   live rather than only unit-tested.

**Known limit, carried out of the close deliberately.** An item filed without a venue does not
dedupe against the same item filed with one — one 09-15 dental appointment is held as two
entries. Bounded, not the failure this item was about, and widening the key means the
similarity-matching `[DB-0827-07]` was closed to keep out. Mike's call, unfiled.

**Cost.** Six live sessions, 412,620 input tokens (271,049 cached), 4,734 output — **under
$0.14** priced at the reasoning tier throughout, so genuinely less. The waste was time, not
money: a first attempt scheduled two sessions either side of a 320-second wait purely to let my
own `_OFFER_WINDOW_SECONDS` expire, re-verifying exhaustion the unit tests already cover. Mike
stopped it. The live value was in what tests cannot see — the ledger filling, the Synthesizer
delivering, the accounting — and the ordinary run of sessions supplied the offer increment for
free.
