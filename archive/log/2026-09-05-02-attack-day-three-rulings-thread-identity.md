### 2026-09-05, second (attack day — deploy confirmed, three rulings, thread identity built, the confidence lever spent) — `tools/context_tracker.py`, `tests/{test_thread_identity,test_open_thread_expiry,run_intake_eval}.py`, `DEV_BACKLOG.md`, `ROADMAP.md`, `archive/backlog_closed_2026-09.md` — `dddd7fe`, `a4b64b5`, `33dd624` + this close-out — **NOT deployed: `tools/context_tracker.py` and the eval-runner guard detection owe `./deploy.sh`**

**Mike cleared the two-session deploy debt at 09:03**, confirmed independently: VM HEAD
`3a01894` (everything committable; only the archive-only `33711e3` behind), both services
restarted, `/health` ok, 3.8 Flash in all six routing slots. The scp-drift state is gone.

**`/backlog attack` found `## Now` unattackable** — all four items built 09-03 and `@waiting`
on dated live confirms (09-10/09-12). The day's work came from `## Later` with Mike's explicit
word; the departure from "`Now` is cleared first" was flagged, not silent. No parallel clusters
either, and that was the finding: the workable items were Red-tier (not delegated), VM-bound
(workers cannot SSH), or decision-gated.

**Three rulings from Mike, one batch:**
1. **Duplicate horizon appointments `[DB-0903-01]` — accept.** Closed, no build. Rejected:
   title-token matching (the `[DB-0827-07]` semantic-guessing class; a wrong merge deletes a
   finding) and require-venue (discards a third of real findings).
2. **`quick` reaching the clinical agents on the bulk tier — leave as-is, accepted risk.**
   Reaffirms 2026-08-09 with the consequence now explicit. Rejected: router inversion (my
   recommendation) and explicit marking. Recorded in the closed file and ROADMAP § A7 check 8.
3. **Thread identity `[DB-0814-02]` — Metatron's own rewording preserves a thread's birthdate;
   rewording driven by user conversation or flagging refreshes it.** Sharper than either option
   offered; it extends the grace design's who-said-it principle to identity.

**Ruling 3 was built same day** by an Opus worker in a worktree, merged `33dd624`: bounded
anchor-token key (identical sets or ≥2 shared anchors — a count, not a ratio, which loosens
exactly on short generic threads), over-merge chosen deliberately as the recoverable failure,
audit line gains a fourth field `reworded`, and the old test asserting the bug was inverted
with its reasoning kept. 16 new checks; suites green post-merge. Live confirm after deploy:
birthdates surviving rewording within days, first real expiries ~09-15.

**The confidence sweep spent its lever `[DB-0820-03]`** (Opus worker, `dddd7fe`): the lowest
gate-passing threshold is 0.95, which demotes 28/33 (85%) to `unclear` — every affordable
threshold still silences an obligation on the worst run, and the killer case reports the same
0.80 confidence wrong as the correct calls do right. `unclear` came up 0/33 in all five runs,
confirming Mike's validity objection literally. Extractor stays OFF, now on evidence. The
direction question (teach `rules:` / grow the corpus / stronger tier) is `@session`.

**Corrections — things believed true that were not:**
- The "spend guard trigger" Mike saw was the **rate** guard reading the eval's per-call session
  counting as a runaway loop; real money was $0.11 (Mac) / $0.04 (VM).
- **Three of five sweep runs were void and looked perfect**: the in-process 60/hour stop refused
  them wholesale, `extract()` scored refusals as `unclear`, and `unclear` passes the gate — so
  the runner printed 0 misses on runs the model never saw. This retro-invalidates 09-04's
  "run 3 collapsed, transient call failure" reading. The runner now returns a distinct INVALID.
- `[DB-0904-01]`'s "buildable now" premise was a day stale — built in `effa68a` (verified before
  clustering; the standing re-open rule paid again).
- The "model omits confidence 39% of the time" figure was wrong: 0/160 clean answers omit it;
  the four apparent omissions were guard refusals.

**Worker economics:** sweep estimated ~80k, actual 90,392 (+13%); thread-identity 116,924
(judgement-work band, unestimated — dispatched on Mike's blanket Opus instruction).

*Outgoing handoff context folded: the 09-04 paragraph's deploy-owed clause resolved today; the
3.8 adoption narrative lives in the 09-04 fragments.*
