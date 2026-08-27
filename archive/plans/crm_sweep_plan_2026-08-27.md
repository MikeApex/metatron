# CRM Sweep — Design Plan

*Planned 2026-08-22/27 in Fable (Opus 5 harness), from the handoff
`archive/handoffs/2026-08-22-crm-sweep-planning-prompt.md`. **Accepted by Mike 2026-08-27, with
the instruction that this plan is REVIEWED WITH HIM AGAIN BEFORE ANY BUILD SESSION STARTS** —
tracked as `[DB-0827-03]`. Backlog and code state re-verified 2026-08-27.*

---

## The problem (measured 2026-08-19 — re-take at build step 0)

200 traces, 786 tool calls: `write_log` 172, `write_journal` 53, **`log_interaction` 1**,
`list_contacts` 0. Information about people is captured constantly into prose nobody can query;
the CRM starves beside it. The gap is capture, not schema — 22 of 23 `write_contact` fields are
already exposed. Root cause: `write_contact`/`log_interaction` are granted to `relationships`
alone, which is dispatched only when a turn is *about* a person — but people are *mentioned* in
turns about everything else.

## Decisions already made (not re-litigated)

- **Inline capture rejected** (Mike, 2026-08-19) — latency, and a mid-answer judgement on the
  class that failed twice that week. The sweep is an off-critical-path daily batch that sees a
  whole day, so recurrence is visible.
- **BINDING: the sweep proposes, it never writes.** The review step is the feature.
- **No merges proposed, ever, in this build.** `merge_contacts` is now confirm-gated and
  reversible (`fd0aed1`/`158cebe`; the Steven incident `[DB-0822-03]`/`[DB-0822-04]` is closed),
  but the sweep stays additive regardless — merging remains a conversational act behind its own
  gate.
- **Scope — Mike, 2026-08-22:** propose "anything that can rightly belong in a CRM — facts from
  history, and inferences the user can correct — **so long as they are reviewed**." Both
  interaction entries and field fills, under the additive-only constraints below.
- **Review channel — Mike, 2026-08-22:** part of the morning brief, kept quiet — the first
  message of the day must not "jump down the user's throat."
- **Apply gate — Mike, 2026-08-22:** one batch confirm tap, **toggleable** via config so it can
  be switched off conversationally if it becomes a nuisance.

## Design

**One sentence:** a nightly function job runs a bare, tool-less Flash-Lite extractor over
yesterday's conversation log + journal, files validated proposals into an append-only per-persona
ledger, parks a ranked digest for the morning brief; Mike accepts/declines conversationally; a
Python apply step executes accepted proposals **from the ledger, by id** — the model relays ids,
never content.

### 1. Input

`data/personas/{p}/conversations/YYYY-MM-DD.jsonl` (primary) + `journal/YYYY-MM-DD.json`. Not
`logs/` in this build (structured specialist writes, low people-signal). Window: a cursor state
file (`crm/sweep_state.json`) — "since last successful run," normally yesterday; catches up after
VM downtime. `tools/pattern_miner.py:52–65` is the read-a-window precedent.

**Declined-proposal memory:** every proposal lives forever in `crm/proposals.jsonl` with a
content fingerprint (contact + normalized fact); the sweep suppresses anything matching a
declined or already-accepted proposal. Declined stays suppressed permanently in this build — a
declined proposal that returns tomorrow is how a review queue becomes noise and then

rubber-stamped.

### 2. Extraction

New agent `config/agents/crm_sweep.md` on the **extractor pattern** (`intake_extractor` /
`tone_profiler`): Flash-Lite, `allowed_tools: []`, `run_session(..., bare=True)` — empty grant
*and* bare dispatch, so the Gemini path advertises no tool schemas and the agent cannot act on
what it reads. Output is a closed JSON list:

```json
[{"name": "...", "kind": "interaction|field_fill|new_contact",
  "date": "...", "type": "...", "summary": "...", "follow_up": "...",
  "field": "...", "value": "...",
  "evidence": [{"seq": "007", "quote": "..."}]}]
```

`tools/crm_sweep.py` validates in Python: schema-closed, per-kind required keys, date within
window, contact resolved via existing `_find_by_name`/`search_contacts`. **Ambiguous or
near-match resolution is never made by the sweep** — the ambiguity is carried into the proposal
and shown as a question (the two-Stevens lesson: the failure mode is silent resolution, and this
pipeline proposes that operation class at volume). Daily cap ~10, recurrence-weighted; overflow
noted in the digest, not silently dropped.

**Why not WISDOM_PROPOSAL:** its transferable principle is kept (Python parses structured relay;
the model never re-keys content) but `_file_wisdom_proposals()` writes straight into the live
store with **no review queue** — the exact thing this sweep is forbidden to do.

### 3. Proposals, review, apply

- **Ledger:** `crm/proposals.jsonl`, append-only; status transitions appended, never edited
  (intake `records.jsonl` + cursors idiom). The ledger row carries the evidence quotes — it is
  the provenance record.
- **Review:** the parked-digest pattern (`digest_job()` → `context_block()` → next coordinator
  load). The morning brief surfaces **one low-key line** ("a few contact updates to review when
  you have a moment"); the full ranked list appears only when Mike engages. Unreviewed proposals
  stay pending and do not nag daily. Delivery is **code-side injection, not a `synthesizer.md`
  rule** — consistent with the `[DB-0822-05]`–`[DB-0822-09]` finding that the agent file's
  length→adherence problem is the failure mode, not missing instructions.
- **Apply:** new tool `apply_crm_proposals(accept_ids, decline_ids)` granted to `relationships`.
  It executes each accepted proposal **from the ledger row verbatim** (`tools/confirm.py`'s
  replay principle) — the model maps Mike's words to ids only. One batch confirm via
  `tools/confirm.py` showing the accepted list — one tap per batch, not per item.
  `apply_confirm: true` default in the sweep's per-persona config, flippable through the existing
  gated `write_config` path.

### 4. Trigger

`_DEFAULT_JOBS` function entry (~05:45, after the 05:30–05:40 maintenance block):
`tools.crm_sweep.sweep`, gated by a per-persona `crm_sweep.enabled: false` default (intake's
exact pattern — silent no-op until enabled). Never raises (`rollup_yesterday` precedent).
`--persona mike` trap: same single-persona limitation as analytics; multi-user resolution
deferred to the same A9a / § Section 0 transition decision.

### 5. Model tier

Flash-Lite, empty grant, bare dispatch. The "judgement class that failed twice" concern is
answered structurally, not by tier: the sweep sees the whole day, decides nothing, and its error
rate is measured (§ 8). If acceptance is poor, escalating the extractor to Pro is a routing
one-liner.

### 6. Privacy

Sensitive tier: whole-day personal log → Vertex Gemini on the VM, the path `relationships`
already reads this data on — governed by the **§ Section 0 ruling of 2026-08-26** (Vertex
continues under flagged-only-logging / ≤90-day / no-training terms; single-user expiry). No
open-tier cloud call anywhere in the pipeline. Nothing new to rule on; the ruling is not
re-opened by this build.

### 7. What may be proposed

Both **interaction_log entries** and **field fills**, plus **new contacts**, under:

- **Additive only.** Fills target empty scalars and appendable collections (`tags`,
  `important_dates`); a non-empty field is never overwritten. Where the sweep believes an
  existing value is *wrong*, that surfaces in the digest as information, not a proposal.
  **`notes` is never a target** (overwritten wholesale by `write_contact`'s `_str_fields` loop —
  structurally not an accumulator).
- **New contacts:** a proposal whose name near-matches an existing contact is presented as a
  question, never resolved by the sweep; the apply path goes through `write_contact`, whose
  near-match confirm gate backstops it.
- **Why this does not wait on `[DB-0818-08]` (the handoff's sequencing demand):** the review step
  *is* the provenance mechanism here — a sweep inference Mike explicitly accepts has been stated
  by the user, a tier an unreviewed write could never claim; and the ledger row preserves full
  provenance (evidence + acceptance) for every applied value, reconstructable when the
  DB-0818-08 tier field lands. The tier build stays DB-0818-08's own item; sweep-applied values
  backfill from the ledger when it ships.
- Applied interaction entries carry `"source": "sweep"` (additive to the entry dict — provenance
  seed + dedup key).
- **Two `crm.py` guards ship with the build** (both hazards verified live 2026-08-27,
  `tools/crm.py:1113–1200`): `log_interaction` dedup (same date+summary fingerprint appends a
  duplicate today) and `last_contact` advance-only (a backdated entry currently *regresses* it
  unconditionally).

### 8. Success metric

The ledger is the metric store, content-free-derivable: proposed / accepted / declined per day
from the first run. Baseline: 1 `log_interaction` per 200 traces (2026-08-19 — re-measure at
build step 0). After a month: median ≥1 accepted proposal per active day; acceptance ≥~60%.
Below → extractor precision problem; ~100% acceptance at high volume → rubber-stamp check
(spot-audit a sample). Counts can ride the analytics rollup later; not in this build.

## Not in this build (recorded gates)

1. **Merges** — never proposed (see Decisions).
2. **Overwrites of any non-empty field.**
3. **Field promotion from notes** — `[DB-0827-04]`; fires when notes are rich, and the sweep
   never writes notes, so richness will come from conversational writes.
4. **LinkedIn / public-profile enrichment** — `[DB-0826-02]`, its own item; privacy ruled
   2026-08-26 (per-contact toggle is the gate). Separate build.

## Build dependency

**`[DB-0827-01]`** (declining a confirmation does nothing — `POST /confirm` is approve-only)
should land before or with the batch confirm tap, or a declined batch has no exit until TTL.

## Build plan and tiers

One Opus session (Mike's 2026-08-18 split: build in Opus, review in Fable):

| Piece | Tier |
|---|---|
| `config/agents/crm_sweep.md` (new) | **Red — prompts** |
| `config/modules/routing_cloud.yaml` entry (Flash-Lite, `allowed_tools: []`) | **Red — prompts** |
| `tools/crm_sweep.py` (sweep, ledger, digest park, `apply_crm_proposals`) | Green/Amber |
| `core/scheduler.py` `_DEFAULT_JOBS` entry | Green/Amber (mechanical) |
| Two `tools/crm.py` guards | Green/Amber |
| Tests | Green |

Everything targets the VM → **`./deploy.sh` is Denied; hand Mike the commit.**

## Test plan

1. **Step 0:** re-take the 2026-08-19 measurements (`/monitor/traces` tool-call counts) before
   relying on them.
2. **Unit:** extractor JSON contract (malformed / ambiguous / empty), fingerprint suppression of
   declined proposals, both `crm.py` guards, apply-replays-ledger-verbatim.
3. **End-to-end on `danny_park`** (has local `conversations/`): seed a day with known mentions →
   `tools.crm_sweep.sweep` → digest parks → accept via a real morning-brief exchange → only
   accepted rows applied; declined suppressed on the next run.
4. **Adversarial:** an injection payload inside the conversation day must come out as (at most)
   an inert proposal, never a tool effect — the empty-grant/bare pattern is the control; add a
   case to the B1b thinking.
5. **Metric:** acceptance-rate counts appear in the ledger from the first run.

## Budget (four classes)

- **Build:** one Opus session — agent file, routing entry, `tools/crm_sweep.py`, scheduler
  entry, two guards, tests. Comparable to the intake-extractor build.
- **Run:** one Flash-Lite call/day, input ≈ one day of conversation+journal (order 10–50K
  tokens) → order **$0.01–0.05/day** at current Flash-Lite rates (read the live price at build
  time, never from this doc); the digest adds a few hundred tokens to one morning-brief turn.
- **Ancillary:** local files only — ledger + state, ~KB/day; owner is the sweep; restart-safe.
- **Unseen:** none — nothing bills by wall-clock, no cache is created, every cost lands on the
  existing Vertex per-call meter.
