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
