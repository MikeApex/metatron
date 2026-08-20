# Vertex context-cache cost control — plan

**2026-08-20.** Written after reconciling the 17–19 August Vertex bills ($1.93 / $17.31 / $6.12)
against Cloud Monitoring token metrics and the Cloud Billing SKU catalogue.

---

## What a user would see

Nothing. This is entirely a cost defect: the assistant behaves identically before and after.
The bill drops by roughly **$100/month** at current volume, and the spend guard starts telling
the truth again.

---

## The finding

Prompt caching went live on 2026-08-18 (`81be0f7`, `46f31b5`). The per-turn saving it bought was
measured and is real — `SESSION.md` records $0.0685 → $0.0397 per Synthesizer turn. **The cost of
*holding* the cache was never counted**, and it is larger than the saving.

Three separate defects, in descending order of cost:

1. **Caches are abandoned on restart, never deleted.** The registry
   (`core/orchestrator.py:90`) is in-process. A restart loses the handle; the cache object keeps
   billing until it expires. Ten restarts on 08-19 left ten Pro caches billing in parallel.
2. **Expiry is midnight UTC, not a TTL** (`core/orchestrator.py:2294`). A cache created at 06:19
   bills for 17.7 hours whether or not it is read again.
3. **`spend_guard` cannot see any of it.** It records per-call tokens only, so storage is
   invisible. On 08-19 it read $2.63 against $6.12 billed.

### Measured, not assumed

| Fact | Value | How |
|---|---|---|
| Pro cache storage rate | **$4.50 / 1M tokens / hour** | Cloud Billing SKU catalogue |
| Flash-Lite cache storage rate | $1.00 / 1M / hour | same |
| Cached-read rate (Pro) | $0.20/M vs $2.00/M standard | same |
| Synthesizer cache size | **18,127 tokens** | live `cachedContents` |
| Coordinator cache size | **5,993 tokens** | live `cachedContents` |
| Pro cache hits, 08-19 | **15**, against 65 Pro calls | `journalctl` `cache_read=18127` |
| Cache creation is metered | **Yes — 12,001 tokens billed as input with zero generate calls** | controlled probe on `gemini-3.5-flash`, 12:03 UTC 08-20 |

**Unresolved:** whether creation meters at $2.00/M (standard input) or $0.20/M (the caching SKU).
The catalogue has no creation SKU, so it lands on one of those two. This changes the marginal case
but not the actions below — it is why Step 5 exists.

### Economics as they stand

- Storage, 08-19: **~$3.4–3.9**
- Savings, 08-19: 15 hits × $0.0326 = **$0.51**
- **Net: about −$3/day**

Break-even for a permanently-held Pro cache is **60 hits/day**. We get 15.

### Why 10 minutes is the right TTL

Fifteen days of per-minute call data: **median burst 2 minutes, ~16–18 calls; p90 burst 10
minutes; 8–10 bursts/day, separated by 30+ minute gaps.** 100% of calls fall inside a burst.

Break-even is *independent of prompt size* — the token count cancels:

> hits needed beyond the first = **0.0417 × TTL_minutes**

At 15 min that is 0.63 (a second call must happen ~63% of the time); at 10 min, 0.42. Adding
creation at the conservative $2.00/M rate raises it to ~1.5 calls at 10 min. Since bursts are
2 minutes long, **10 minutes covers the median burst five times over and the p90 exactly.
Beyond that, cost accrues against idle time and buys nothing.**

---

## Steps

### 1. Sweep orphans at startup — *the one that matters*
`core/orchestrator.py`. Before creating any cache, list `cachedContents` and delete every entry
matching our models. The registry is empty at process start, so anything live is by definition
abandoned. Removes defect 1 outright and is the only step that matters for development, where
restarts are constant.

### 2. Sliding 10-minute TTL, and delete on shutdown
Replace the midnight-UTC `expire_time` with a 10-minute expiry refreshed on each use, plus an
`atexit` handler deleting caches this process created. Removes defect 2.

### 3. Teach `spend_guard` about storage
`core/spend_guard.py`, `config/modules/spend_guard.yaml`. Record cache create/delete events and
accrue `tokens × rate × hours` into the daily total, so the $6 alert and $15 stop track the actual
bill. Add the two storage rates to the pricing table, and drop the config comment claiming the
table "ignores cached-input discounts" once it no longer does.

### 4. Kill switch for development
`VERTEX_CACHE_DISABLED=1` in the Mac's `.env`. Development restarts constantly and gets roughly one
hit per run; it should not cache at all. Steps 1–2 make this optional rather than urgent.

### 5. Enable the BigQuery billing export — **Mike, Console**
The `billing_export` dataset was created 2026-08-09 and is **still empty**; the export itself was
never switched on, which is why this reconciliation had to be reconstructed from Monitoring plus
the SKU catalogue rather than read off a line item. Enabling it resolves the creation-rate question
permanently and makes the next bill self-explaining. Not retroactive — the sooner the better.

### 6. Extend caching to the specialists — *investigate, do not build yet*
`ROADMAP.md` records that the multi-turn cost sits **inside the specialists** (`logistics` at 8
turns), and only the head layer is cached today (`run_session_gemini_cached` serves head-layer and
routing-layer agents; specialists run the OpenAI-compat path with no caching). A specialist session
of 8 turns on a ~10k prompt would pay creation once and read 8 times — the strongest caching case
in the codebase, worth roughly 70% of that session's input cost.

**This must land after Steps 1–2, never before.** Twelve more agents means twelve more cache
objects per process, and on today's code every one of them would be orphaned on restart and held
until midnight.

---

## What this is worth

| | now | after Steps 1–2 |
|---|---|---|
| Pro storage | $3.4–3.9/day | ~$0.15/day |
| Savings | $0.51/day | $0.49/day |
| **Net** | **−$3/day** | **+$0.01 to +$0.31/day** |

**The prize is stopping the bleed (~$100/month), not the caching.** At current volume the feature
itself is roughly break-even either way. It becomes clearly worth having when hits-per-cache rises
— which is Step 6 — or when sustained load passes 60 Pro hits/day.

---

## Budget and model

| Step | Scope | Est. tokens |
|---|---|---|
| 1–2 | ~60 lines, `core/orchestrator.py` + tests | 40–60k |
| 3 | ~40 lines across two files | 25–35k |
| 4 | ~10 lines + `.env` | 5k |
| 6 | investigation only | 20–30k |

**Total ~90–130k tokens, roughly $3–5.** Step 5 is a Console click and costs nothing.

**Model:** build in **Opus 5**, review in **Fable 5** — Mike's 2026-08-18 split. Steps 1–2 touch
`core/orchestrator.py` (Red tier), so they are not delegated to a subagent; the judgement about
what is safe to delete at startup *is* the work. Step 3 is Amber and mechanical.

**Note for A8:** `_get_or_create_vertex_cache` and the `_vertex_*` helpers are scheduled to move to
`core/providers.py` under the A8 module split (`ROADMAP.md` line 224). These changes should stay
inside those functions so the relocation remains a clean move.

---

## Test that closes this

Delete the two live caches, deploy Steps 1–2, then compare the next day's Vertex bill against
`data/diagnostics/spend_2026-08-21.json`. **Pass:** the gap between billed and estimated collapses
from ~2.3× to under 1.2×. That single comparison confirms both the diagnosis and the fix.

Interim check, available immediately: `GET .../locations/global/cachedContents` should never return
more than one cache per model, and none older than 10 minutes past its last use.
