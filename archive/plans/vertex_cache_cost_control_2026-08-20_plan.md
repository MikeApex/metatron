# Vertex context-cache cost control — plan

**2026-08-20.** Written after reconciling the 17–19 August Vertex bills ($1.93 / $17.31 / $6.12)
against Cloud Monitoring token metrics and the Cloud Billing SKU catalogue. **Revised 2026-08-20
after review (Fable 5): step priority inverted, ownership model specified, builder constraints
folded into the steps.** Prior text at commit `6a96fc4`.

---

## What a user would see

Nothing, from here on — the assistant behaves identically before and after. But this stopped
being a cost line this morning: **the GCP soft cap tripped at 10:36 on 08-20 and stopped the VM
mid-deploy**, with this defect as the diagnosed cause. The caps were raised to **$150/$250
temporarily** (`5836561`) to buy time; the revert is `[DB-0820-01]`, due 2026-09-01, and it
should not happen until this plan has landed and one clean day has been measured. So the stake
is **the removal of a cause of outage**, plus roughly **$100/month** of bill, plus the spend
guard telling the truth again.

---

## The finding

Prompt caching went live on 2026-08-18 (`81be0f7`, `46f31b5`). The per-turn saving it bought was
measured and is real — `SESSION.md` records $0.0685 → $0.0397 per Synthesizer turn. **The cost of
*holding* the cache was never counted**, and it is larger than the saving.

Three separate defects, in descending order of cost:

1. **Expiry is midnight UTC, not a TTL** (`core/orchestrator.py:2294`). A cache created at 06:19
   bills for 17.7 hours whether or not it is read again. This is the primary defect: it is what
   converts every abandonment into hours of storage billing.
2. **Caches are abandoned on restart, never deleted.** The registry
   (`core/orchestrator.py:90`) is in-process. A restart loses the handle; the cache object keeps
   billing until it expires. Ten restarts on 08-19 left ten Pro caches billing in parallel —
   **but only because of defect 1**: with a 10-minute TTL, an orphan bills ≤10 more minutes
   (~$0.014 for the Pro cache), because Vertex deletes caches server-side at `expire_time`.
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
| Cache location | `locations/global` — the VM's `.env` sets `GOOGLE_CLOUD_LOCATION=global`, overriding the `us-central1` default at `orchestrator.py:2207` | `us-central1/cachedContents` returns `{}`; `global` lists both live caches, verified 08-20 |

**Unresolved:** whether creation meters at $2.00/M (standard input) or $0.20/M (the caching SKU).
The catalogue has no creation SKU, so it lands on one of those two. Also unresolved, same method:
**whether `cachedContents.patch` (the TTL refresh) meters anything.** It should not re-ingest
tokens; "should not" is what the creation probe existed to test. Both are why Step 5 exists, and
the second is why Step 1 minimises refresh calls rather than assuming they are free.

### Economics as they stand

- Storage, 08-19: **~$3.4–3.9**
- Savings, 08-19: 15 hits × $0.0326 = **$0.51**
- **Net: about −$3/day**

Break-even for a permanently-held Pro cache is **60 hits/day**. We get 15.

### Why 10 minutes is the right TTL

Fifteen days of per-minute call data: **median burst 2 minutes, ~16–18 calls; p90 burst 10
minutes; 8–10 bursts/day, separated by 30+ minute gaps.** 100% of calls fall inside a burst.

Break-even is *independent of prompt size* — the token count cancels. **The constant is
per-model**, because it is (storage $/M/min) ÷ (read saving $/M):

> hits needed beyond the first = **0.0417 × TTL_minutes** (Pro: 0.075 ÷ 1.80)
> hits needed beyond the first = **0.074 × TTL_minutes** (Flash-Lite: 0.0167 ÷ 0.225)

At 10 min that is 0.42 extra hits (Pro) / 0.74 (Flash-Lite). Adding creation at the conservative
$2.00/M rate raises the Pro figure to ~1.5 calls. Since bursts are 2 minutes long, **10 minutes
covers the median burst five times over and the p90 exactly. Beyond that, cost accrues against
idle time and buys nothing.**

---

## Steps

**Ship order — the smallest change that stops the bleeding goes first.** Step 1 alone removes
the wall-clock accrual that tripped the cap; it deploys on its own, ahead of everything else.
Steps 2–4 follow in a second pass. Step 5 is a Console click Mike can do today, in parallel.
Step 6 is investigation only. Available immediately with no code at all: **delete the live
caches by hand** — they recreate on the next call with midnight expiry, so this trims hours of
storage per day until Step 1 lands, without fixing anything.

### 1. Sliding 10-minute TTL — *the fix; everything else is trim*
`core/orchestrator.py`, inside the `_vertex_*` helpers only (see A8 note). Replace the
midnight-UTC `expire_time` with a 10-minute expiry, extended while the cache is in use, plus a
best-effort `atexit` delete of caches this process created. Once this lands, Vertex itself
garbage-collects every abandoned cache within 10 minutes — **server-side expiry is the primary
reaper; the sweep in Step 2 and the `atexit` handler only trim the ≤10-minute tail.** Do not
build as though `atexit` were the correctness mechanism: systemd stops with SIGTERM and nothing
runs it on OOM-kill or crash.

Binding constraints for the builder:

1. **Refresh lazily, after the response, never per-call.** Extend the expiry (via
   `caches.update`) only when the remaining TTL is under 5 minutes, and after the generate call
   returns, not before it. A synchronous pre-call round-trip is a latency tax on a voice-first
   system, and the median burst (2 min) then needs **zero** refresh calls. This also caps
   exposure if Step 5 finds the patch call is metered.
2. **Update the registry tuple on every refresh.** The 60s-margin validity check at
   `orchestrator.py:2287` reads the stored `expire_time`; a refresh that pushes the server-side
   expiry without updating the tuple makes the check judge a live cache expired and silently
   re-create it — a metered creation per burst.
3. **Lock the registry.** `_vertex_cache_registry` is mutated from FastAPI request threads and
   the parallel-tool `ThreadPoolExecutor` with no lock. Two concurrent first-turns both create;
   the loser's cache object leaks and its registry write is clobbered. Guard get-or-create and
   refresh with a lock (pattern: `spend_guard._lock`).
4. **Evict on the streaming path too.** `run_session_gemini_cached_stream` (~:3100–3160) falls
   back to compat on any pre-emission error **without** calling `_evict_vertex_cache`; the
   blocking path does (~:2745). A 10-minute TTL makes expiry races ~150× more frequent than
   midnight expiry did; add `_is_cache_not_found` → evict to the stream path's failure handler.
   Treat a failed refresh the same way: evict and recreate, never raise.
5. **Fix the comments that state the midnight scheme** — the registry header at
   `orchestrator.py:83-85` and the `run_session_gemini_cached` docstring (~:2712) — in the same
   change, or the next session inherits a false claim.

### 2. Ownership-tagged startup sweep — *demoted: a tidy-up, not the fix*
Two-plus processes always share the Vertex project: `metatron-server` and `metatron-scheduler`
are separate systemd units with separate in-process registries (08-19: 5 + 5 restarts = the ten
cache pairs), and the Mac shares the project too. **A naive "delete everything matching our
models" sweep has each process destroying the others' live caches on every restart.** Rules:

1. **Tag every cache at creation** with a `display_name` identifying the creating process as
   **(host, service role)** — `vm:server`, `vm:scheduler`, `mac:dev`. **Never include the PID**:
   a PID-keyed identity means a restarted process matches nothing and the sweep reaps nothing.
2. **Sweep only own-identity caches, and only those whose `expireTime` is past or within one
   TTL of now.** Under the sliding scheme a cache the owner is still using always carries a
   freshly pushed expiry; one whose owner died stops being refreshed and ages out. This is also
   the guard against same-identity concurrency (overlapping restart drain, two dev CLI runs) —
   a plain creation-time age floor cannot protect a long-lived refreshed cache.
3. **List in the location the client is actually configured for** — read
   `GOOGLE_CLOUD_LOCATION` from the environment (this deployment runs `global`); never hardcode
   either the region or the default.
4. **One-time deploy action:** delete **all** existing caches in the project once at rollout.
   Pre-change caches carry no `display_name`; no owner will ever match them, and they bill
   until their midnight expiry.

### 3. Teach `spend_guard` about storage
`core/spend_guard.py`, `config/modules/spend_guard.yaml`. Add the two storage rates to the
pricing table and accrue storage into the daily total. Binding constraints:

1. **Charge at grant time, not at delete.** `spend_guard` has no clock — it runs only when a
   call happens — and the crash that orphans a cache is exactly the event that would skip a
   delete-time record. Accrue the full TTL window at creation (`tokens × rate × 10/60`) and
   again at each refresh. Slight overestimate, never under, crash-safe, no timer.
2. **Plumb the cached-token count.** Honouring the $0.20/M cached-read rate needs a
   `tokens_cached` parameter on `record_tokens()` (default 0) fed from the native loop's usage
   metadata; only then may the config comment claiming the table "ignores cached-input
   discounts" be dropped. If the plumbing is deferred, the comment stays.
3. Storage accrual raises the guard's estimate against unchanged thresholds ($6 alert / $15
   stop). Post-fix storage is ~$0.15/day — noise; do not re-tune thresholds over it.

### 4. Kill switch for development
`VERTEX_CACHE_DISABLED=1` in the Mac's `.env`, honoured **inside `_get_or_create_vertex_cache`**
by returning `None` — both call sites (~:2729, ~:3140) already handle `None` by running
uncached, so one gate covers the blocking and streaming paths. Development restarts constantly
and gets roughly one hit per run; it should not cache at all.

### 5. Enable the BigQuery billing export — **Mike, Console**
The `billing_export` dataset was created 2026-08-09 and is **still empty**; the export itself was
never switched on, which is why this reconciliation had to be reconstructed from Monitoring plus
the SKU catalogue. Enabling it resolves **two** open rates permanently — cache creation ($2.00/M
vs $0.20/M) and whether the TTL-refresh patch call meters anything — and makes the next bill
self-explaining. Not retroactive — the sooner the better. **Step 6's Flash-Lite half is gated on
the creation answer.**

### 6. Extend caching to the specialists — *investigate, do not build yet; two gates, not one*
`ROADMAP.md` records that the multi-turn cost sits **inside the specialists** (`logistics` at 8
turns); only the head layer is cached today. A specialist session pays creation once and reads
many times — the strongest caching shape in the codebase. But the decision splits by model:

- **Pro specialists** (~10k prompt, 8 turns): creation ≤ $0.02 even at the worst-case $2.00/M;
  reads save ~8 × 10k × $1.80/M ≈ $0.144. **Positive regardless of the creation rate.** Gate:
  Steps 1–2 landed, nothing more.
- **Flash-Lite specialists** (most of `routing_cloud.yaml`): reads save ~$0.018/session;
  creation at $2.00/M costs ~$0.020. **The unresolved creation rate flips the sign.** Gate:
  Step 5's billing export answers the creation SKU first.

**The investigation must also cover the thought_signature bug**, and this is the constraint most
likely to sink the build: specialists run the OpenAI-compat path *because* it carries the
workaround for Vertex's parallel-function-call `thought_signature` defect
(`run_session_gemini` docstring, :2317–2322); the cached path requires the native loop, which
only has a fallback (~:3163). Specialists are the heaviest tool users in the system. No
specialist moves to the native path without that exposure being measured.

---

## What this is worth

| | now | after Steps 1–2 |
|---|---|---|
| Pro storage | $3.4–3.9/day | ~$0.15/day |
| Savings | $0.51/day | $0.49/day |
| **Net** | **−$3/day** | **+$0.01 to +$0.31/day** |

**The prize is removing a cause of outage, not the caching — and Step 1 alone removes it.** The
bleed this table prices is what tripped the soft cap on 08-20 and stopped the VM mid-deploy; the
$150/$250 caps are a tourniquet with a revert date (`[DB-0820-01]`, 2026-09-01). At current
volume the caching feature itself is roughly break-even either way. It becomes clearly worth
having when hits-per-cache rises — the Pro half of Step 6 — or when sustained load passes 60 Pro
hits/day.

---

## Budget and model

| Step | Scope | Est. tokens |
|---|---|---|
| 1 | ~50 lines (TTL, lazy refresh, lock, stream eviction, comments) + tests | 35–50k |
| 2 | ~30 lines (tagging, own-identity sweep) + one-time cleanup | 20–30k |
| 3 | ~50 lines across two files (incl. `tokens_cached` plumbing) | 30–40k |
| 4 | ~10 lines + `.env` | 5k |
| 6 | investigation only | 20–30k |

**Total ~110–155k tokens, roughly $4–6.** Step 5 is a Console click and costs nothing.

**Model:** build in **Opus 5**, review in **Fable 5** — Mike's 2026-08-18 split. Steps 1–2 touch
`core/orchestrator.py` (Red tier), so they are not delegated to a subagent; the judgement about
concurrency and what is safe to delete *is* the work. Steps 3–4 are Amber and mechanical.

**Note for A8:** `_get_or_create_vertex_cache` and the `_vertex_*` helpers are scheduled to move
to `core/providers.py` under the A8 module split (`ROADMAP.md` line 224). All changes — including
the registry lock and the kill switch — stay inside those functions so the relocation remains a
clean move.

---

## Test that closes this

Delete **all** caches in the project (legacy ones are unowned — Step 2.4), deploy Steps 1–3,
then compare the next day's Vertex bill against `data/diagnostics/spend_2026-08-21.json`.
**Pass:** the gap between billed and estimated collapses from ~2.3× to under 1.2×. That single
comparison confirms both the diagnosis and the fix — and one clean day at the collapsed gap is
the evidence `[DB-0820-01]` needs before the caps come back down.

Interim check, available immediately (location per this deployment's env,
`GOOGLE_CLOUD_LOCATION=global`):

```
GET https://aiplatform.googleapis.com/v1/projects/metatron-ai-499810/locations/global/cachedContents
```

**Pass:** never more than one cache per model, every entry carries an owning `displayName`, and
no `expireTime` lies more than 10 minutes in the future. (Last-use time is not exposed by the
list API; `expireTime` under the sliding scheme is the verifiable proxy.)
