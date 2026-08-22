### 2026-08-22 (The 21st reconciled: caching earns, and the scheduler eats the day)

**Question asked:** was 2026-08-21 billed properly, and did the cache fix work? Both yes — but
every premise underneath the question turned out to need correcting, including two of mine.

**The bill reconciles.** Reconstructed from Cloud Monitoring token counts plus the VM's
`spend_guard` state (read over Tailscale via `/monitor/file`, since SSH was refused): expected
**$2.51–$2.71** against 08-19's $6.12. Method validated by reproducing 08-19's known storage gap
to the dollar ($3.46 derived vs $3.4–3.9 measured in the cache plan). **Cache storage fell from
~$3.46/day to $0.14994** — the sliding-TTL fix (`9de2836`) is live on the VM and landed on its
predicted ~$0.15/day.

**Caching is net-positive for the first time, and barely:** 265,200 cached tokens saved $0.477
against $0.15 storage plus $0.02–$0.23 creation — **net +$0.10 to +$0.31/day**, roughly 1–1.5
reads per cache window, sitting on the break-even the plan computed. Keep it (it removed a ~$3/day
loss); do not expect it to earn at head-layer volumes. This strengthens the case for Step 6
(specialists), where creation is paid once and read many times.

**Mike's premise corrected: the 21st was not a light day.** 160 invocations against 156 on the
20th and 123 on the 19th — the busiest of the three. It only looks light beside the 18th (698).
The low bill is the fix, not a quiet day.

**What ate the invocations — the scheduler, not the user.** 23 pipeline runs → 130 traced calls:
9 scheduled runs (92 calls), 10 Diarist runs trailing them by 2–4s (24 calls), **4 genuinely
interactive runs (14 calls)**. 89% automated. Cost concentrated hard: **the Synthesizer's 11 calls
cost more than the other 119 combined** (47%), while `logistics` ingested the most tokens of any
agent (397,216) for $0.10 because it is on Flash-Lite — the routing works; Pro on the head layer
is where the money is.

**Fixed: `spend_guard` was reading ~23% low.** Cloud Monitoring saw 160 invocations to the guard's
130 (reproduced 08-22: 32 vs 26). The pipeline itself is perfectly metered — traces 130 = guard
130 — so the gap is entirely non-pipeline traffic: context-cache *creation* (confirmed by the
08-20 probe: `calls: 0, cache_grants: 1` against 1 invocation / 12,001 tokens) plus retried and
fallback attempts, which Vertex bills and the trace has no field to count.
**Rejected: metering creation exactly.** It is easy, but it fixes only half and leaves a residual
that cannot be sized without the billing export — two changes, one unmeasurable. **Chosen:** a
single measured `unmetered_uplift: 1.25` in `config/modules/spend_guard.yaml`. `usd` stays the raw
observed sum so it remains auditable against the pricing table; a new `usd_billed_est` carries the
uplift and **is what the alert and stop now judge**. Clamped never below 1.0. Validated: 08-21
reads $1.4567 → $1.8209, landing on the top of the independently-derived $1.60–$1.81 range. All 23
checks in `tests/test_vertex_cache_ttl.py` pass. Side effect, accepted: the $6 alert now trips at
$4.80 observed — this restores the intent of the 2026-08-08 re-baselining, which set the
thresholds against Monitoring actuals the guard has been under-reading ever since.

**Two things I asserted that were wrong, both caught before anything was built on them.**
*(1)* I reported the **BigQuery billing export as dead since 08-12** and told Mike to re-enable it
in the Console. Wrong: `[DB-0822-01]` already recorded it as on and backfilled, and it advanced
from 08-12 to 08-14 (+2,103 rows) during the session — it is **backfilling forward, not broken**.
No Console action needed. The note in `spend_guard.yaml` still says "dark since 2026-08-12" and
needs correcting.
*(2)* I reported the Franklin virtue review as **clock-triggered and therefore Mike's to fix in a
Denied-tier persona file**. Both halves wrong, and both inference rather than measurement: there is
no clock trigger anywhere, and `config/personas/mike/evening_ritual.md` does not exist in the repo
at all (the VM owns live persona config). `[DB-0822-10]` was rewritten before build.

**The finding that reframes the rest: these are adherence failures, not missing instructions.**
Reading `config/agents/synthesizer.md` against Mike's complaints, **six for six are already written
there** — "raise a thing once" (:187), open on one thing (:181), nothing-new → one line + "what's
on" (:181, almost verbatim his wording), length follows focus with no word cap (:183), obligations
drawn on but never listed (:187), and the ritual scoped to the `evening_close` prompt (:209). All
ignored on 08-21. The file is 52,397 bytes / ~12,700 tokens and its own audit named length→adherence
as the cause. **Consequence carried into every item filed: do not fix these by adding a seventh
rule.** For the virtue dump specifically the mechanism is `core/orchestrator.py:352-356`, which
injects the whole ritual into *every* session's system prompt unconditionally — the fix is
injection code, not prose.

**Filed to `## Now`** (directly, at Mike's instruction, and reviewed by him in-chat rather than via
`.claude/backlog_inbox/`): `[DB-0822-05]` Diarist journalling days the user never spoke;
`[DB-0822-06]` derived counts stored in logs, giving four contradictory training-day claims in one
day; `[DB-0822-07]` two scheduled jobs 7 minutes apart; `[DB-0822-08]` nothing ever proposed, only
reported; `[DB-0822-09]` email processed then discarded; `[DB-0822-10]` the virtue dump. Grouped
Green/Amber before Red at Mike's request so automated runs can take the top block.
**Two complaints were already filed and took evidence rather than duplicates:** `[DB-0809-02]`
(repetition — third measurement, plus a flag that Mike's "short and sweet" must be built as
brevity *conditioned on nothing being new*, not the ≤2-sentence cap this item already rejected) and
`[DB-0815-11]` (false action claims — now has a clean instance: the 10:24 run claimed *"I've logged
the instruction change so it sticks"* with **no `config_writer` call anywhere in its trace**).

**Not deployed.** `core/spend_guard.py` and `config/modules/spend_guard.yaml` need `./deploy.sh`,
which is Mike's. Until then the VM keeps metering ~23% low — nothing breaks.

