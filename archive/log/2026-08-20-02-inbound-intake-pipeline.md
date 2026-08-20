### 2026-08-20, second (inbound intake: mail triaged in code, queued per domain, taught by correction) — `b417e98`, **deployed by Mike**

**Three sessions in one thread (08-18 idea → 08-19 plan review in Fable → 08-20 build in Opus).**
What shipped: an hourly scheduler sweep reads mail (headers-only when idle, quiet-hours aware,
structurally unable to notify), classifies in Python — taught rules → learned sender ledger →
transport headers — and files substance into per-domain queues that specialists drain on their own
next run (`read_intake_queue`). Every message keeps a permanent record row; the mailbox is never
written. The model tier (`intake_extractor`: Flash-Lite, empty grant, dispatched `bare=True`) is
wired but double-gated OFF behind `extractor.enabled` and an eval gate. `teach_intake`
(Synthesizer, confirm-gated, in `_EXECUTORS`) writes standing rules from stated corrections.
21/21 pipeline suite, 10/10 provenance, guard clean.

**Design rulings from Mike, all binding:** it is an *interest sieve, not a filing tool* —
disposition and domain are independent axes (a silenced promotion still reaches Recreation to
judge); intake never dispatches an agent on arrival (the obligations argument, applied to a
higher-volume stream); no mailbox writes — importance/outstanding flags live in `records.jsonl`;
digest is a *training surface* with `include_silent` wheels; chains suppress redundancy before the
user sees anything.

**Wrong earlier, corrected:** (1) first draft sent `promotion` to `domain: null` — would have
discarded the exact concert-announcement case that motivated the feature. (2) First draft filed
through domain tools on arrival — Mike's queue ruling replaced it. (3) `tone_profiler` was cited
as the context-free precedent; it wasn't — it carried `goals.yaml` beside attacker-writable text
(`[DB-0819-02]`, closed this session with `bare=True` after verifying its agent file references no
personal context). (4) A miskeyed plan approval started the build early; three files survived as
keep-and-correct. (5) I placed `[DB-0820-03]`/`[DB-0820-04]` before Mike had approved them —
sequence was explain → his call → place; he let both stay.

**The `/code-review high` earned its cost — 10 findings, 3 severe:** the parked digest was popped
by the Coordinator's context load and never reached the Synthesizer (fixed: 30-min delivery
window); `days: sunday` fell through to the daily branch so the weekly digest would have fired
every morning (fixed: singular `day`); collapsed thread siblings were never marked seen, so
threads re-surfaced every sweep. Plus: unwrapped attacker text in `context_block` (now
`wrap_untrusted`), full-body re-downloads hourly (now header-first fetch with a skip predicate,
oldest-unseen-first so backlogs drain), explicit `domain: null` in rules silently inert (sentinel),
cadence in two homes (scheduler owns it), N+1 record reads, duplicated quiet-hours logic (imports
`time_in_quiet_hours`).

**Rejected:** IMAP folder filing (a mis-filed message is invisible where the user would look;
seen-set already gives read-once); a second full review pre-commit (everything unreviewed is
gated; the review is bought at the extractor flip instead, folded into `[DB-0820-03]`);
per-message extractor batching (small models mis-attribute fields across batched messages).

**Merge wrinkle worth remembering:** the parallel session's `5684d27` took `synthesizer.md`
wholesale and carried my `teach_intake` bullet to the VM days before the tool existed there —
instructed-but-unbuilt, live, narrow trigger. Cured by this deploy. Commit guard fired on
`core/orchestrator.py` (other writer in history); all outstanding hunks verified mine by eye,
overridden deliberately.

**Open next:** Mike primes the inbox; VM edits are his (`enabled: true`, delete `mike.md`'s
six-hour inbox line if present). `[DB-0820-03]` = corpus → eval (zero `action_required` false
negatives) → scoped review → flip. `[DB-0820-04]` = extractor injection row, advances B1b.
`[DB-0819-01]` = subscriptions-as-inputs design conversation.
