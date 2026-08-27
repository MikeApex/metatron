# Handoff — the orchestrator context pair: intraday staleness [DB-0822-06] and the standing refusal [DB-0827-01]

**Worker 1, parallel attack run, 2026-08-27. Both items designed, reviewed by the assigning
session, then built. Green/Amber only — nothing Red was touched and nothing needed to be.**

Branch: `worktree-agent-af979bb1750ab6696`. The worktree the run assigned did not exist on
disk; it was created on its own branch before any edit, so nothing was written to `main`.

---

## 1. What changed, by what a user would notice

| Commit | What a user would notice |
|---|---|
| `451460e` | The 10:00 run stops calling a thing "still missing" three hours after the 07:14 run resolved it, and stops repeating a hiatus count someone wrote days ago as if it were today's number. |
| `1908547` | Declining something means it is not asked again — not by the next scheduled run, not tomorrow morning — unless the user raises it or something new arrives. |

Mechanism, briefly. `451460e`: `tools/logger.py` records when each log field was last written,
in one flat `_written_at` map at the top of the day file, and today's log is rendered field by
field with that time (`notes="…" (recorded 3 hours ago)`). `1908547`: a confirmation request
matching an action refused in the last 24 hours raises no card unless
`tools/turn_context.py` reports a genuinely new trigger — the user speaking in a turn that
began after the refusal, or an intake row that arrived after it.

**Files:** `tools/logger.py`, `tools/pattern_miner.py`, `tools/confirm.py`,
`tools/turn_context.py` (new), `core/orchestrator.py`, and two new tests.

---

## 2. Backlog items to close, and the evidence

### `[DB-0822-06]` — carried state read as current fact

**The intraday half closes. The "stale derived counts" half does not close as built — it was
stale-premised as filed, and that needs recording rather than ticking.**

- **Intraday half — BUILT (`451460e`).** Evidence: `tests/test_log_field_timestamps.py`,
  32 checks, covering that two fields written three hours apart in the same merged day-file are
  now dated apart — which one merged date could never do. `tests/test_context_age_annotation.py`
  re-run green as the regression gate.
- **Derived-counts half — STALE-PREMISED, cannot be closed as "built".** The item asks to
  *"compute derived counts at read time and never store them"* and names `expired_open_threads`.
  Verified against current code:
  - **`expired_open_threads` never reaches any model.** `tools/context_tracker.py:406` pops it
    from `read_context_tracker()`'s return, and `core/orchestrator.py` `load_recent_context()`
    reads `context.json` directly but renders only `open_threads`, `patterns` and `follow_ups`.
    The `expired_open_threads: 0` phrase in the backlog comes from `_append_audit`'s docstring,
    which describes reading the **file on disk** during the 2026-08-14 audit — a diagnostic, not
    carried context.
  - **Every count the code computes is already computed at assembly time**, from stored
    timestamps, so it cannot go stale: intake queue counts and oldest-item age
    (`tools/intake.py:788`, `_age_days` off `seen_at`), obligations' `+N more`
    (`tools/obligations.py:309`, counted off the freshly filtered list), and the log-line ages
    from `cbd5ca3`.
  - **The only stale count is model-authored free text.** `physical_health` wrote
    `"Day 3 of 5-day exercise hiatus"` into a `write_log` field; `write_log` takes an arbitrary
    dict. There is no code-computed carried count anywhere to intercept — the prior worker's
    "no clean code interception" verdict is right, and stronger than it looked.

  So a stale count is a stale *field*, which is the same problem as the Teams link and is now
  dated by the same mechanism. Whether dating it is *enough* is a live question, not a closed
  one: the code still does not compute the true number.

- **`@waiting` on this item after deploy:** one multi-write day where two fields written hours
  apart show different ages in the same log line. If a dated count is still misread after that,
  the remaining option is a code-computed derived-facts line ("days since a log recorded
  exercise: 4"). **Deliberately not filed** — which facts qualify is Mike's judgement about what
  he wants tracked, and it should not become a backlog item until the evidence asks for it.

### `[DB-0827-01]` — a decline that does not stop the next proposal

**The open half closes.** `0f8f528` left `confirm.declined()` readable with **zero callers**
anywhere in `core/` or `tools/` — verified by grep before building. Two now read it: the guard in
`request()`, which is what actually stops the re-proposal, and `context_block()`, which tells the
session so it does not spend a turn on a proposal that will not be raised or read the silence as
licence to ask in prose instead.

Evidence: `tests/test_decline_reproposal_guard.py`, 21 checks — including that a scheduled run
re-reading the same context raises nothing, that the user asking again is never blocked, that a
turn which began *before* the refusal is not new evidence, that an intake row arriving after the
refusal reopens it while one predating it does not, that a different action to the same person
still goes through, and that a tampered ledger record suppresses nothing. `test_decline_path`,
`test_confirmation_gate`, `test_action_provenance`, `test_false_action_claim` and
`test_contact_dedup_gate` all re-run green.

**`@waiting` after deploy:** one decline that is not raised again by the following scheduled run,
and one action the user asks for again in the same day that *is* raised — both halves, or the
guard is the original bug reversed.

---

## 3. The two parameters set here, and what they cost

Per the house rule that a lifetime, size or cadence chosen without a named figure is a cost
decision made by accident:

1. **`_REPROPOSE_WINDOW_SECONDS = 24 hours`** (`tools/confirm.py`). Chosen as the span over
   which the *same* context is carried: `load_recent_context` reads the tracker and the last five
   days of logs, and the scheduler completes a daily cycle, so every run inside a day re-reads
   the material the first proposal came from. Shorter than a day leaves tomorrow morning's
   scheduled run free to raise the identical card off identical context — the loop. Materially
   longer starts suppressing proposals whose grounds have genuinely moved on, silently.
   - **Standing cost: none.** No process, no timer, no warm resource, no new stored state beyond
     the ledger entry `decline()` already writes. One read of a small local JSON file per
     confirmation request. Nothing is billed by wall-clock time, so no meter needs to watch it —
     which is stated here precisely because a cost billed by time is the kind no per-request
     meter would report.
   - **At expiry, nothing is deleted or altered.** The ledger record persists — capped by count
     at `_DECLINED_LIMIT = 200`, never by age — so "was this refused?" stays answerable
     afterwards. Only the automatic suppression lapses. Archive-on-merge: the refusal is kept, it
     simply stops being enforced.
   - **Restart/redeploy:** the ledger is a file on the persona's data volume, so it survives
     both. Nothing is orphaned, because nothing outlives a process.

2. **`_CONTEXT_MAX_DECLINED = 10`** (`tools/confirm.py`). How many refusals the context block
   shows, not how many are kept. Enough for a day of them without a bad afternoon crowding the
   head layer's input. The block returns `""` when nothing was declined, so a user who has never
   said no pays nothing.

**Token cost of the pair.** Both additions land in `augmented_input`, not the system prompt — 
verified at all three `load_recent_context` call sites — so **the Vertex prefix cache is not
disturbed and the 4,096-token cache floor is not in play.** Per-field rendering is confined to
*today's* log; the other four days keep the single-line dump they have now, because a day-old
value has nothing more to say than "yesterday".

---

## 4. Must be carried by another owner

1. **Deploy — Mike's, and nothing here is live without it.** All five changed files are
   `core/orchestrator.py` and `tools/`, which run on the VM. `./deploy.sh` is Denied to sessions
   by decision; this needs Mike to run it. Both `@waiting` confirmations above are gated on that
   deploy.
2. **The two live confirmations in § 2** — neither can be closed from here, and both are one
   ordinary day of use rather than a test to write.
3. **Backlog close-and-file at `/archive`.** `[DB-0827-01]` closes. `[DB-0822-06]` closes on its
   intraday half only; its derived-counts half must be recorded as **stale-premised as filed**,
   with the `tools/context_tracker.py:406` and `tools/intake.py:788` evidence above — it cannot
   be ticked as built, and it should not silently disappear either.
4. **Nothing was filed to `DEV_BACKLOG.md` by this worker**, per the standing rule against
   unrequested filing. The one possible follow-up (a code-computed derived-facts line) is
   described in § 2 and deliberately left unfiled pending evidence.
5. **A8 overlap.** `load_recent_context` and the confirmation path both sit in the module-split
   scope. The new code is additive and confined to functions that already exist, but the A8 owner
   should know `tools/turn_context.py` is a new module the orchestrator imports at top level.
