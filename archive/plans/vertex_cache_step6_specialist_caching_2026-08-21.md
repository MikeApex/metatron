# Step 6 — should the specialists be cached? Investigation, not a build

**2026-08-21. REVISED the same day — the first version's recommendation was wrong and is
corrected below.** It charged cache creation once per *session*, which assumed specialist
invocations do not cluster. They cluster heavily. Mike caught it: *"they'll likely be invoked
more than once once they're invoked the first time."* Measured, `physical_health` is invoked
74 times and needs **10** cache creations under a ten-minute TTL. Amortising creation across a
burst is the whole economics of this question, and getting it wrong turned a clear build into a
recommendation to skip.

Step 6 of `archive/plans/vertex_cache_cost_control_2026-08-20_plan.md`,
run after Steps 1–4 landed. **Nothing was built and nothing changed in routing.** The plan
asked for two gates to be tested before a build; this measures both, plus a third it did not
name.

---

## What a user would see

Nothing either way. This is a bill question.

---

## The finding, in one line

**Cache `mental_wellbeing` and `physical_health`: +$0.17/day, which is more than the head-layer
caching already in production earns.** The Flash-Lite six are positive but negligible
(+$0.008/day) and can ride along or not. The constraint the plan expected to sink the build,
Vertex's `thought_signature` bug, **did not appear once in 333 traced sessions**. The real cost
is that the two agents worth caching are the two carrying clinical hard-fails, so the change
buys an A4 regression run.

**And the creation-SKU question no longer gates this.** Amortised across bursts, creation costs
$0.12 across 26 days on both Pro agents combined — the gap between the $2.00/M and $0.20/M
readings is **$0.004/day**. Step 5 still matters for `spend_guard`'s accuracy; it decides
nothing here.

---

## Measured, not assumed

From every local trace file (`data/personas/*/traces/*.jsonl`, 2026-06-26 → 08-18; the VM
holds more, so treat volumes as a lower bound and the per-session shapes as representative):

| agent | model | sessions | median turns | max | median first-turn input | turns with parallel tool calls |
|---|---|---|---:|---:|---:|---:|
| coordinator | flash-lite | 101 | 1 | 1 | 6,752 | 0 |
| synthesizer | **pro** | 101 | 1 | 3 | 18,840 | **1** |
| physical_health | **pro** | 74 | 3 | 7 | 6,239 | 0 |
| mental_wellbeing | **pro** | 63 | 3 | 6 | 7,304 | 0 |
| diarist | flash-lite | 40 | 2 | 4 | 2,269 | 0 |
| work_vocation | flash-lite | 19 | 4 | 4 | 6,617 | 0 |
| relationships | flash-lite | 17 | 3 | 8 | 7,208 | 0 |
| logistics | flash-lite | 11 | 4 | 8 | 11,774 | 0 |
| recreation_hobbies | flash-lite | 5 | 2 | 3 | 4,876 | 0 |
| finance | flash-lite | 2 | 4 | 4 | 4,181 | 0 |

**Three things fall out of this table. The first retracts a claim the first version of this
document made against the plan, and it was the wrong way round.**

1. **The plan's "~10k prompt, 8 turns" was CONSERVATIVE, not optimistic, and its conclusion —
   *"positive regardless of the creation rate"* — was correct.** The first version of this
   document argued the plan overstated the prize because the measured median session is 3 turns
   at ~6.2k tokens rather than 8 at 10k. That compares the wrong units. The plan's 8 turns is
   turns *per cache*, and a cache serves a whole burst: measured, `physical_health` gets **24
   turns per creation** across 7.4 invocations. The plan under-counted reads by 3x. Nothing in
   its Step 6 arithmetic needed correcting.
2. **Three specialist prompts sit UNDER the 4,096-token cache floor and would be padded** —
   and the first version of this document said the opposite, because it measured first-turn
   *input* (which includes the Coordinator's directive) instead of the cacheable system prefix.
   The prefix is the agent file plus `goals.yaml`, nothing else: the clock line was deliberately
   put in the user message to keep it stable, so the hash does repeat across invocations.

   | agent | prefix tokens | padded to |
   |---|---:|---:|
   | relationships | 7,564 | — |
   | logistics | 7,514 | — |
   | mental_wellbeing | 5,813 | 6,064 |
   | recreation_hobbies | 4,555 | 6,148 |
   | work_vocation | 4,288 | 6,165 |
   | **physical_health** | **3,698** | **6,208** |
   | learning_growth | 3,720 | 6,207 |
   | finance | 3,541 | 6,214 |

   **40% of what would be stored and billed for `physical_health` is inert padding.** It is
   still net positive by a wide margin, but it is a real cost and it is invisible in the agent
   file's own size.

3. **`mike`'s `goals.yaml` is currently empty (0 chars)**, so today every specialist prefix is
   the agent file alone. When goals land (the A5b/A9a gate), prefixes grow, padding disappears
   for the small agents, and every figure here moves **up**. This estimate is a floor.

---

## Gate 1 — the economics, amortised across bursts

Invocations are grouped into bursts by a 10-minute gap, matching the TTL: one creation per
burst, storage for the burst span plus a 10-minute tail, and **every turn** reads at the cached
rate. `hi`/`lo` are the unresolved creation SKU ($2.00/M standard input vs $0.20/M caching).

| agent | model | cached tok | invocations | creations | turns | save | creation hi | storage | **net worst** | **net best** |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| physical_health | pro | 6,208 | 74 | 10 | 242 | 2.7042 | 0.1242 | 0.0920 | **+2.4880** | +2.5997 |
| mental_wellbeing | pro | 6,064 | 63 | 10 | 196 | 2.1394 | 0.1213 | 0.0843 | **+1.9338** | +2.0429 |
| relationships | flash | 7,564 | 17 | 6 | 56 | 0.0953 | 0.0113 | 0.0113 | +0.0727 | +0.0829 |
| work_vocation | flash | 6,165 | 19 | 7 | 63 | 0.0874 | 0.0108 | 0.0108 | +0.0658 | +0.0755 |
| logistics | flash | 7,514 | 11 | 6 | 44 | 0.0744 | 0.0113 | 0.0086 | +0.0546 | +0.0647 |
| finance | flash | 6,214 | 2 | 1 | 5 | 0.0070 | 0.0016 | 0.0017 | +0.0037 | +0.0051 |
| recreation_hobbies | flash | 6,148 | 5 | 4 | 9 | 0.0124 | 0.0061 | 0.0042 | +0.0021 | +0.0077 |

Over the 26 traced days: **+$4.62 worst case, +$4.88 best** — **$0.178/day**, of which the two
Pro agents are **$0.170/day** and all six Flash-Lite agents together are **$0.008/day**.

**Three things follow, and the first is the one that matters.**

1. **Creation has stopped being the deciding term.** 137 Pro invocations need 20 creations. At
   the worst-case SKU that is $0.12 over 26 days. The first version of this document had
   creation at 137× that and concluded the margin was thin; it is not thin, it is ~20× the
   creation cost.
2. **Caching these two is worth more than the caching already in production.** The deployed
   head-layer cache saves a measured $0.0288 per Synthesizer turn — about **$0.11/day** at
   101 turns over the traced window. `mental_wellbeing` + `physical_health` are **$0.17/day**.
   The system's best remaining caching opportunity is the one that is not built.
3. **Flash-Lite is positive, not negative** — the first version's two negative rows were an
   artifact of per-session creation. But $0.008/day across six agents is noise, and it should
   ride on the Pro decision rather than justify one.

## Gate 2 — the `thought_signature` exposure is not there

Specialists run the OpenAI-compat path *because* it carries the workaround for Vertex's
parallel-function-call `thought_signature` defect (`run_session_gemini` docstring). Caching
requires the native loop, which has only a fallback. The plan called this the constraint most
likely to sink the build, on the reasoning that specialists are the heaviest tool users in the
system.

**They are the heaviest tool users and they do not make parallel calls.** Across 333 traced
sessions and 478 tool-calling turns, exactly **one** turn emitted more than one function call
in a single response — and it was the `synthesizer`, which already runs the native loop and
did not fail. Every specialist: **zero**.

That is the difference between a blocker and a fallback path. The native loop already degrades
to compat on any exception, so the residual exposure is one extra round-trip on an event that
has occurred once in three months.

**Do not read this as "the bug is gone."** It is a statement about how these twelve instruction
files behave, not about Vertex. A specialist rewritten to fan out its tool calls — which is
exactly what `ROADMAP.md`'s D2 latency work proposes for the Coordinator — would move this
number, and the check would need re-running.

---

## Gate 3 — the one the plan did not name, and it is now the binding one

**The two specialists worth caching are `mental_wellbeing` and `physical_health`** — the two
agents in the system carrying clinical hard-fails (`MUST_SURFACE`, `CLINICAL_CONCERN`,
`MEDICATION_MISSED_CRITICAL`). Caching them means moving them from `_openai_compat_loop` to
`_run_gemini_native_loop`: a different loop, a different tool-call parser, a different history
representation, and a system prompt that arrives as `cached_content` rather than as a system
message.

`ROADMAP.md` § A7's pre-sign-off gate exists because a *prompt-assembly reorder* was considered
enough to require re-running the A4 hard-fails. This is a larger change than that reorder, on
the same two agents.

**So the real price of the Pro half is not the ~50 lines of routing. It is
`python tests/run_a4_safety.py` — clinical and pipeline suites, both complexity tiers — as a
gate, against a measured prize of $0.78–$2.44 per 137 sessions.** At roughly 10 specialist
sessions a day that is **$0.05–$0.18/day**.

---

## Recommendation

**Build the Pro half. This reverses the first version of this document.**

1. **`mental_wellbeing` and `physical_health` — build it.** +$0.17/day, ~$5/month, more than the
   head-layer caching already earns, and the figure is a floor because `mike`'s goals are not
   loaded yet. Implementation is a set-membership change: add them to the branch at
   `orchestrator.py:4019` that already routes the head layer to `run_session_gemini_cached`.
   **The work is not the routing, it is the gate** — `python tests/run_a4_safety.py` clinical
   and pipeline suites, both complexity tiers, because this moves the two clinical-flag agents
   from `_openai_compat_loop` to `_run_gemini_native_loop`, a larger change than the
   prompt-assembly reorder A7's pre-sign-off gate already demanded a re-run for.
2. **Flash-Lite six — include them only if the A4 run passes and the diff is genuinely the same
   line.** Worth $0.008/day: not a reason to do anything, and not a reason to add a second
   change to a commit that has a safety gate on it. Defensible either way; do not spend
   thinking on it.
3. **Do not wait for Step 5.** The creation SKU moves this by $0.004/day. It was a real gate on
   the first version's arithmetic and is not one on this version's.
4. **Re-check the padding when goals land.** `physical_health` is 40% padding today. That is
   priced in above and it gets better, not worse — but if a future prompt-slimming pass pushes
   an agent further under the floor, it pays storage for filler.

**What made this cheap to answer, and the lesson that outlives it:** every number came from
trace files that were already being written — the `is_proactive`/`ToolCallRecord` instrumentation
built for A9 answered a cost question it was not designed for. **And the first pass still got it
wrong**, because the model of *how often a cache is created* was wrong, not the rates. Both
versions used identical, correct per-token prices. The error was one line of arithmetic about
clustering, and it inverted the recommendation.
