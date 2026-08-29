### 2026-08-29 (What 08-27 and 08-28 actually cost, and the budget that forked per worktree)

Mike asked why the 08-27/08-28 Vertex bill looked high given the caching fix, and specifically
what the **mike-persona** share was — the number that decides whether the product is expensive
or the development is.

**Answer: development, on both days, and the caching fix was not yet live on either.** Step 6
(`d9b4843`) landed 22:15 on 08-28, after essentially all of the traffic.

| | 08-27 | 08-28 |
|---|---|---|
| Billed (Cloud Monitoring, priced at the yaml table) | ~$9.51 | ~$8.66 |
| **Mike persona (VM traces)** | **$1.79 (19%)** | **$3.09 (36%)** |
| Development / testing | ~$7.7 | ~$5.6 |

Attribution came from the per-agent trace records rather than the guard's totals: the VM's
`data/personas/mike/traces/*.jsonl` pulled over the existing `/monitor/file` endpoint, walked
including subagents, priced per turn. On 08-27 the traced turn count matched the guard's `calls`
exactly (164 = 164) — **that day the VM ran zero test traffic**, so the persona figure is not an
estimate. The development spend is identifiable by the hour: 08-27 15:00–16:00Z cost **$6.47 in
one hour** (the A4 pipeline rerun plus the redteam disclosure suite) — one hour of suites costing
4x Mike's entire day. Caching now works: 08-29 hit rates run 58–88% per agent, per-exchange cost
$0.042 against $0.058 on both prior days, and the same traffic priced uncached would be $0.73
against the $0.38 actually incurred.

**Two findings the analysis produced, both fixed in `398c575` (deployed by Mike).**

1. **The daily budget forked per git worktree.** `_STATE_DIR` resolved from `__file__`, so every
   worktree got its own. On 08-28 the coordinator model probe ran in
   `.claude/worktrees/agent-a53d4604ec183981e` and booked **$1.94 / 196 calls / 169,609 output
   tokens** into a file the main checkout has never read — three independent budgets on one
   machine, each individually reading as a quiet day. This is exactly the failure the module
   header already described for two *hosts*, reproduced inside one host, and worse: the header's
   mitigation (thresholds sized with two hosts in mind) cannot be sized against a worktree count
   that changes per session. `_budget_root()` follows a worktree's `.git` pointer back to the main
   tree. Rejected the obvious alternative — a shared counter — for hosts, for the reason the header
   already gives (no shared filesystem, and a network round-trip inside a guard whose first rule is
   never to cause an outage). Worktrees *do* share a filesystem, so here it is free.
2. **`unmetered_uplift` was reading high, and I first reported the opposite.** My initial pass
   called it "running low, ~1.4x". That was wrong, and wrong in a specific way worth recording:
   it compared Monitoring against **one** state file, so the worktree's metered traffic was scored
   as unmetered. Re-derived over ten days (08-19..08-28) summing every state file: call ratio
   median 1.176, input tokens 1.124, output 1.09. The uplift multiplies **dollars**, so it tracks
   the token ratio, not the call ratio — an uncounted cache-creation ingest is one extra "call"
   carrying a large slug of cheap input, and pricing it as an average call is what read high.
   **1.25 -> 1.20**, still rounded up from the worst observed day so it fails safe. The comment
   blocks in both files now say COUNT EVERY STATE FILE, because the singular phrasing is what let
   the figure drift in the first place.

**Thresholds deliberately unchanged** ($6 alert / $15 stop). Replaying 08-28 aggregated gives
$3.23; the heaviest correctly-summed day in the ten-day window was ~$8.40. The alert will now fire
on heavy development days that previously stayed silent — that is the signal the fix buys, and
moving the threshold now would trade it straight back.

**Left standing on purpose:** the stale worktree state file for 08-28. It is inert (the guard only
reads today's date) and it is the evidence for the fix; quietly rewriting a historical spend record
was not mine to do.

**Verification.** `tests/test_vertex_cache_ttl.py` 33/33 PASS. `_budget_root()` checked against all
four real worktree shapes on this machine plus a no-git path — all four collapse onto the main
checkout, the no-git case falls open. On the VM the new branch never executes (`.git` is a real
directory), so byte-identical behaviour there is the expected result, and the post-deploy read
confirmed the file intact at the right path. **Not yet confirmed: the counter advancing past the
deploy** — that needs one read after the next pipeline session fires.

**Process notes.** Mike deployed before the commit existed; `deploy.sh` pushes and the VM pulls, so
that run carried none of it and a second deploy was needed. And a Mac-side check was handed over
with the VM's path (`~/multi-model-mcp` vs `~/Desktop/multi-model-mcp`) — the standing
machine-and-full-path rule, broken in the one place it exists for.

**Open cost items surfaced, not filed** (none clears the "a user would notice" bar; recorded here
so they are not lost): synthesizer *output* on Pro is now the largest single line and caching
cannot touch it; the Diarist gets no cache at all; cache-storage share rose from 11% of token cost
on 08-28 to 24% on 08-29 as eight specialists each took their own 10-minute window — worth
re-measuring before the September cap reset.

