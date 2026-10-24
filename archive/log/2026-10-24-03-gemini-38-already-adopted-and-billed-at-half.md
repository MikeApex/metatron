### 2026-10-24, third (the "new" Gemini Flash was already ours, and the bill confirms half price) — `DEV_BACKLOG.md`, `archive/backlog_closed_2026-10.md` — **no code or routing changed; nothing to deploy**

**Prompt:** Mike reported a new Gemini Flash release ("3.8 I think") and asked for a review of the
model-selection docs, especially costs, so we could decide whether to change any defaults.

**Premise corrected:** `gemini-3.8-flash` was adopted on **2026-09-04**, the day a launch email
arrived (`archive/log/2026-09-04-02-gemini-38-adoption.md`). It already serves all six
reasoning slots in `routing_cloud.yaml`, is the `ask_gemini` MCP default, and is priced in
`spend_guard.yaml`. `scripts/check_model_availability.py` run today: **nothing newer is
callable on `global`**. It checked 23 ids, covering 3.9–3.12 and 4.x for Flash and Flash-Lite.
`--all` mode lists *older* callable models under its "NEWER" heading. That heading is misleading
in `--all` mode only; the default mode's verdict is the one to read. `[DB-0901-01]` was **six
weeks overdue**: its weekly date had not been pushed since 09-04. Pushed to 10-31.

**Costs — `[DB-0904-02]` closed from the BigQuery billing export (09-04 → 10-24):**
- 3.8 Flash list rates: $1.50 / $7.50 / $0.15 per 1M, plus $1.00/1M/hour for cache storage.
  Every SKU carries a `DISCOUNT` credit, "Gemini 3.8 Flash Price Promotion - 50% off". The
  effective rates are **$0.75 / $3.75 / $0.075**, which are exactly the guard's figures.
  Net $22.49 over 50 days, about $0.45/day.
- **Correction:** the yaml comment saying cache storage "does NOT double in 2027" is wrong about
  the *net* rate. The promotion halves storage too, to $0.50 net. The guard's $1.00
  over-reports storage 2x, which is the safe direction. **Left unchanged on purpose:** it is
  correct the day the promotion ends.
- **The promotion's end date is still unknown.** The export does not carry one. The
  `from: "2027-01-01"` block is still copied from 3.7; `[DB-0901-02]` (due 12-15) owns it.

**Decision (Mike): no default changes.** Option priced and **rejected**: moving the bulk tier
(13 slots on `gemini-3.5-flash-lite`, ~$0.37/day) to 3.8 Flash. That would cost about
+$14/month on the promotion and about +$37/month after it ends. The quality benefit is
unmeasured, and it would be the third model change in a row without re-running the clinical
safety tests.

