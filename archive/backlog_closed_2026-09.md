# Closed Backlog Archive — 2026-09

**Items closed in September 2026, with the evidence that closed them.** Rolls monthly;
the previous file is [`backlog_closed_2026-08.md`](backlog_closed_2026-08.md).

**Search this before re-filing anything.** A closed item is removed from
[`../DEV_BACKLOG.md`](../DEV_BACKLOG.md) entirely — this is where its proof lives, and roughly a
third of what has looked open in the past turned out to be already fixed.

---

## ✅ [DB-0820-01] The spend caps are temporarily too high — brought back down on 2026-09-01

**Closed 2026-09-01.** The GCP budgets were reverted from the temporary **$150/$250** to
**$100/$175** at the September calendar reset, exactly as the item specified.

**What was done, and verified live:**

- `gcloud billing budgets update` on both budgets on billing account `013F3D-66B5CD-955A3A`:
  *Metatron Soft Cap (stops VM)* `150 → 100`, *Metatron & Multi-Model Budget* (hard,
  disables billing) `250 → 175`.
- **The soft cap was lowered first**, so the intermediate state was $100/$250 — a wide gap —
  rather than $150/$175, a $25 gap. The item's "do not lower the soft cap alone" warning is
  about the *gap*, and the gap can be squeezed by the order of a reduction just as easily as
  by a bad choice of numbers.
- Re-read from GCP after the change: `175` and `100` USD. Confirmed, not assumed.

**The condition the revert was gated on was met.** The item said "$100/$175 unless a
reconciliation says otherwise". Two reconciliations said the opposite of otherwise: the
`[DB-0822-01]` reconcile passed five consecutive post-deploy days at billed ÷ estimated
1.02×–1.17× (2026-08-27), and the 2026-08-29 breakdown showed real `mike`-persona use at
~$1.50–2.00/day, with the alarming 08-27/08-28 totals (~$9.5/~$8.7) driven by development test
suites — one hour of A4 + red-team runs cost $6.47.

**The live consequence to expect, stated so it is not read as a regression:** a heavy testing
day can still trip the $100 soft cap. That is the control working as designed, and recovery is
`gcloud compute instances start metatron-vm` — about 60 seconds. The product itself has ample
headroom.

**Also fixed in the same pass, because it is the same defect the item warns about.** The item
says to read the values from `docs/INFRASTRUCTURE.md`, "never from a script comment
(`metatron-vm-override.sh` was stale for months)". Three live files were still asserting
`$70/$150` — stale through two raises *and* this revert:
[core/spend_guard.py](../core/spend_guard.py) (Red tier, comment only),
[config/modules/spend_guard.yaml](../config/modules/spend_guard.yaml), and
[infra/stop-vm/main.py](../infra/stop-vm/main.py). None of them *read* the numbers; all three
merely restated them. **The fix is to stop restating: each now names the cap by what it does
and points at the source of truth.** The two sub-headings inside
`docs/INFRASTRUCTURE.md` § Billing protection did the same thing and got the same treatment —
the table is now the only copy of the numbers in the section that owns them.

*Filed 2026-08-20 by Mike. Closed 2026-09-01 via `/fix`.*
