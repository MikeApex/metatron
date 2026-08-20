### 2026-08-20, third (the Vertex bill reconciled, and "verified ZDR" was never verified) — `ROADMAP.md` § Section 0, `core/orchestrator.py`, `DEV_BACKLOG.md`, `archive/plans/`, `archive/handoffs/`, global `~/.claude/CLAUDE.md` — `6a96fc4`…`01495ec`, **not deployed**

**Mike asked why 18 August cost $17.31 and 19 August $6.12 against $1.93 on the 17th.** The answer
was not the development testing, though that explains the 18th's call volume. It is a cost class
the codebase has no instrument for: **Vertex context-cache storage, billed per wall-clock hour**
($4.50 per 1M tokens/hour on Pro, $1.00 on Flash-Lite), accruing whether or not the cache is read.

**Reconciliation, all from measurement rather than inference.** `data/diagnostics/spend_*.json` on
both hosts (the Mac's $6.31 on the 18th is invisible to the VM and was nearly missed again);
Cloud Monitoring `token_count` and `model_invocation_count` for actual metered volume; the Cloud
Billing SKU catalogue for authoritative rates. Token cost explains the 17th almost exactly
($2.31 modelled vs $1.93 billed) and only ~60% of the 18th, ~45% of the 19th. The residual is
storage.

**Three defects, and the first is the one that cost money.**
1. **Caches are abandoned on restart, never deleted.** The registry (`core/orchestrator.py:90`) is
   in-process; a restart loses the handle and the cache keeps billing to expiry. 5 server + 5
   scheduler restarts on the 19th left **10 Pro caches billing in parallel** — which the extra
   API-call count (19 against 10 expected pairs) independently confirms.
2. **Expiry is midnight UTC, not a TTL** (`core/orchestrator.py:2294`). A cache made at 06:19 bills
   17.7 hours. **The comment gives a freshness rationale — "matches the once-per-day config change
   cadence" — with no cost figure anywhere near it.** That is the whole failure in one line.
3. **`spend_guard` cannot see storage.** It read **$2.63 against a $6.12 bill** on the 19th and was
   working exactly as designed.

**The soft cap tripped at 10:36 today and stopped the VM mid-deploy.** A parallel window raised the
caps to $150/$250 (`5836561`) citing this diagnosis. So this is an outage cause, not a billing
curiosity — the priority moved accordingly.

**What was believed and turned out wrong.** *(1)* Read the VM journal and traces as showing caching
never ran there and said so; it was running, the logs simply do not capture it (units log WARNING+),
and the live `cachedContents` listing settled it. *(2)* Asserted the residual was storage alone —
**cache creation is also metered**, proved by a controlled probe (a 12,001-token cache on
`gemini-3.5-flash`, zero generate calls, 12,001 input tokens metered). *(3)* Said caching "costs
more than it saves" before measuring hit rate; the sharper truth is **15 Pro cache hits against 65
Pro calls** — the cache is read on a session's first turn only.

**Decisions.**
- **10-minute sliding TTL**, from measured burst structure: 15 days of per-minute data give a
  **median burst of 2 minutes carrying 16–18 calls, p90 of 10 minutes**, 8–10 bursts/day separated
  by 30+ minute gaps. Break-even is independent of prompt size — *hits needed beyond the first =
  0.0417 × TTL minutes* — so past 10 minutes the cost buys idle time. **Mike's own arithmetic
  (~3 calls/hour to maintain; a second call 50–60% of the time) checked out at 2.5/hour and 63%.**
- **Rejected: extending caching to the specialists now.** It is the strongest case in the codebase —
  `ROADMAP.md` records the multi-turn cost sits inside them (`logistics` at 8 turns), so one
  creation would serve ~8 reads — but twelve more agents means twelve more orphans per restart.
  Gated behind the fix, not sequenced beside it.
- **Rejected: "always be cost-sensitive" as a global rule.** Costs *were* considered on the caching
  work — the per-turn saving was measured ($0.0685 → $0.0397), `spend_guard` exists, a $1 test-cost
  convention exists. Mike's counter-argument corrected the framing and is the one recorded: **the
  right questions were never asked at the moment the parameter was chosen.** Global `~/.claude/CLAUDE.md`
  gained a merged **§ Costs** (build / run / ancillary / unseen) that fires when a lifetime, size or
  cadence is set — merged with the existing Plan Mode budget rule rather than added beside it, so
  cost keeps one home. 166 → 187 lines.
- **A defect in this session's own plan, found before the build:** Step 1's orphan sweep as written
  would have `metatron-server` and `metatron-scheduler` delete each other's live caches on every
  restart, and the Mac would delete production's. Needs process-ownership tagging. **This is why the
  plan went to Fable to rewrite rather than to review** — and on Mike's challenge, rewriting in the
  stronger model is his standing split ("plan and review in Fable, build in Opus"), which this
  session had quietly departed from by planning in Opus.
- **Modelled but not acted on:** all-Pro routing with caching fixed costs **~$3.11/day against
  today's $6.12** — half the current mixed bill. Filed as `[DB-0820-05]` with the assumptions that
  must be re-checked, because every figure assumes the fix is live.

**Open and owed.** The rate cache *creation* bills at is unresolved ($2.00/M vs $0.20/M); the
`billing_export` dataset created 2026-08-09 is **still empty** — the Console step was never done, which
is why this had to be reconstructed from Monitoring at all. Two caches were left live deliberately.
Nothing deployed. `6a96fc4` commits the plan as the baseline Fable is rewriting against.

**Then the session turned, on Mike's challenge to a detail.** Asked whether the Vertex endpoint was
really `global` — he recalled choosing `us-central1` — and both memories turned out right about
different layers. **The VM zone, the subnet and both Cloud Functions are `us-central1`; the model
endpoint is `global`**, documented in `docs/INFRASTRUCTURE.md` § Vertex AI credentials as *"required
for Gemini 3.x models — us-central1 does not work"*. So the cache location finding stood.

**The check found a live trap anyway.** All three call sites defaulted `GOOGLE_CLOUD_LOCATION` to
`us-central1` — an endpoint that does not serve the models this project runs. It had never fired
because both hosts set the variable; it was waiting for a fresh checkout, and would have failed at
call time rather than startup. Fixed as one named `_vertex_location()` helper defaulting to
`global`, warning once when unset, replacing the triplicated inline default (`175809e`). Verified
against all three branches: set-to-global, set-to-a-region (env respected, not overridden), and
unset (one warning, not two).

**The largest finding of the session came last, and it is not about cost.** Asked to look into how
ZDR interacts with jurisdictions, and the jurisdiction question turned out to be the lesser one.
**`ROADMAP.md` § Section 0 has authorised sensitive-tier personal data on the Vertex VM since
2026-06-18 on the strength of "verified Zero Data Retention." Nobody had ever verified it, and it is
not in force.** Checked directly: no organization parent, a self-serve *"My Billing Account"* with no
reseller or contract parent, zero org policies, and no record anywhere in the repo of an
abuse-monitoring exception being requested or granted. ZDR is not a default state on Vertex.

**Of the amendment's three claims, one survives.** *"No training use"* holds by default. *"Prompts/
responses cleared before logging"* does not — that is exactly what the exception buys. *"Contractual
sequestration"* holds only weakly. This does **not** breach the 2026-06-10 ruling as written, which
targets shared infrastructure where data mingles with other users' traffic — but the amendment's
premise was half wrong, and the amendment is what authorises the sensitive default. **The most
exposed path is the one the 2026-08-09 clarification named explicitly: `tone_profiler`, which reads
real correspondence written by other people.**

**Recorded as a dated correction beneath the original amendment, not a rewrite** (`01495ec`) —
rewriting it would destroy the evidence of what was believed when those paths were cleared, which is
what made this hard to spot. **Whether the permission continues on the corrected basis is left
explicitly undecided**: Mike directed the correction and the ZDR work, neither of which is a ruling
on whether work proceeds meanwhile. *"Verified ZDR"* is now banned in the repo until something
records a verification.

**Rejected: filing this as a backlog item and stopping.** Mike overrode the suggestion to file and
verify later — *"No, let's verify ZDR right now"* — which was right: the check took four commands
and overturned a two-month-old premise that a backlog entry would have carried unexamined for
longer.

**Why it went unchecked for two months, which is the transferable part.** `WebFetch`/`WebSearch` are
Denied on this project, so no session could read Google's terms; the assumption was therefore
uncheckable *from inside a session* and nobody said so out loud. That constraint is now the first
item in the handoff, framed as Mike's call with the trade-off stated rather than as a request.

**Handoff, not a backlog item:** `archive/handoffs/2026-08-20-zdr-verification-prompt.md` — research
and a decision, no code expected, Fable. It carries the five checks already done so they are not
redone, a caution against over-reading the `cacheConfig` probe (**it is not established that it
governs abuse-monitoring retention at all**), and plans for the likely branch — that ZDR is *not*
obtainable on a self-serve account with no organisation.

**State at close.** A parallel window is mid-build on the cache plan (295 insertions in
`core/orchestrator.py`, plus `scripts/vertex_cache_admin.py` and `tests/test_vertex_cache_ttl.py`) —
none of it staged here. `175809e` owes a deploy but changes nothing on the VM, which already sets the
variable. The two live caches were left running on Mike's instruction.
