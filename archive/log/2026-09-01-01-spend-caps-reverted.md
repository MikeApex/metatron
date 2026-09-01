### 2026-09-01 (the spend caps come back down, and three files stop restating them) — `b33498f`, **not deployed**

**The caps are back at $100 soft / $175 hard**, reverted on the September calendar reset exactly
as `[DB-0820-01]` specified. Both GCP budgets on billing account `013F3D-66B5CD-955A3A` were
updated by `gcloud billing budgets update` and then **re-read from GCP** — 100 and 175 — rather
than assumed from the command exiting 0.

**The order was the interesting decision.** Soft first, so the intermediate state was $100/$250
and never $150/$175. The item's standing warning is *"do not lower the soft cap alone… keep ~$100
between the tiers"*, and it is written as a warning about **choosing** numbers; it is equally a
warning about the **order of a reduction**, which can squeeze the gap to $25 in passing while both
endpoints are correct. The hard cap is an outage — 26h VPC freeze, 2026-07-30, and it has fired
*below* its own threshold once — so a transient thin gap is not a cosmetic concern. That reading is
now recorded in `docs/INFRASTRUCTURE.md` so the next revert does not rediscover it.

**The gate condition was checked, not assumed.** The item permitted $100/$175 "unless a
reconciliation says otherwise". Two said the opposite: `[DB-0822-01]` passed five consecutive
post-deploy days at billed ÷ estimated 1.02×–1.17× (2026-08-27), and the 2026-08-29 breakdown put
real `mike`-persona use at ~$1.50–2.00/day, with the alarming 08-27/08-28 totals (~$9.5/~$8.7)
traced to development test suites — one hour of A4 + red-team runs cost $6.47.

**Consequence recorded so it is not later read as a regression:** a heavy testing day can still
trip the $100 soft cap. That is the control working; recovery is a ~60-second VM start. The cap
pressure is test runs, not the product.

**Scope widened by one thing, deliberately.** `[DB-0820-01]` warns to read the values from
`docs/INFRASTRUCTURE.md` and *"never from a script comment (`metatron-vm-override.sh` was stale for
months)"*. Three live files were doing exactly that, stale at `$70/$150` through two raises **and**
this revert: `core/spend_guard.py` (Red tier, built here on Opus, comment only),
`config/modules/spend_guard.yaml`, `infra/stop-vm/main.py`. **None of them reads those numbers —
each merely restated them**, so the fix is to stop restating: each now names the cap by what it
does and points at the source of truth. The two sub-headings *inside*
`docs/INFRASTRUCTURE.md` § Billing protection had drifted the same way and got the same treatment,
so the table is now the only copy of the numbers in the section that owns them. **One commit,
because it is one reason** — the caps are $100/$175 and no live file should assert otherwise.

**Rejected:** renumbering `## Now` after item 1 was removed. A gap already existed at 4, so the
file tolerates gaps, and rewriting five entries risks colliding with the parallel window against
this tree. That is a `/backlog` job, not an archive one.

**Corrected mid-session:** the first backlog removal also swallowed the
`### Green/Amber — buildable without a prompt` heading, which belongs to items 2–3, not to the
closed item above it. Caught by reading the diff rather than the summary of it, and restored.

**Found, not fixed, and pre-existing:** `qa_sweep.sh` fails its `project-log` check —
`archive/PROJECT_LOG.md` does not match its fragments, while both are clean in the working tree.
A previously committed fragment was never rebuilt. Rebuilt in this session's step 2.

**Outgoing handoff.** Nothing is owed a deploy: the two `spend_guard` files changed comments only,
so the VM's behaviour is identical and `./deploy.sh` can wait for whatever ships next. The
remaining `⚠ due` items are the calendar dedupe (`[DB-0809-21]`, already ruled — keep either, delete
the rest) and `[DB-0810-05]`. Red session ④ is still the next block, prompt staged and Mike-bound at
`archive/handoffs/2026-08-30-red-session-four-prompt.md`.

