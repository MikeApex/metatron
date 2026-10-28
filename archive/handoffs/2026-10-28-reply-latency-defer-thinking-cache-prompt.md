Model: Opus 5.5 to plan and build; Fable 5.1 to review the plan and the diff. The work touches the reply path every user message takes and `config/agents/synthesizer.md` (Red tier), so the judgement is the work: not delegated.

# Reply latency: do after the reply what the reply doesn't need, then thinking and cache (paste into a fresh chat)

**Budget:** planning ~300–500k Opus tokens, Fable review ~150k, build ~400–700k. Live probes on the
VM ~$1–3 (Synthesizer calls at ~$0.04–0.07 each). **Mike:** ~30 min approving the plan, ~20 min
judging the thinking A/B replies blind, a deploy. **Run cost to estimate in the plan:** a deferred
pass may add a model call per turn, or save one if the bookkeeping moves to a smaller prompt.
Name the figure per 1,000 turns against today's (`spend_guard.yaml` prices; never quote from memory).

---

/metatron-code Plan reply-latency work. Plan first, and get it approved before building. Read
`archive/plans/reply_latency_plan_2026-10-24.md` in full and `archive/PROJECT_LOG.md` § 2026-10-24
(the reply-latency build) and § 2026-10-26 third (the shared output ceiling) before proposing anything.

## The need (Mike, 2026-10-28)

On the second user's trial accounts an ordinary message is answered in **20–25 s**, and an
interview turn in 3–15 s. Mike's own messages take **median 54 s, p90 142 s** (96 user turns,
10-04 → 10-28). He wants his everyday replies closer to the trial's speed. His ruling:
**"pushing off anything that the response doesn't require is a no brainer"**. That includes work that
may be needed conversationally later, but not in the next immediate reply. Do all three of the
items below.

## What was measured on 2026-10-28 (re-measure; don't build on these numbers alone)

From `/monitor/traces` (service token, `scripts/mint_token.py`):
- **The model generates ~10 s per 1,000 tokens (thinking + reply) on `gemini-3.8-flash`**, Vertex
  `global`. The 10-24 entry measured ~8 s. Latency is driven by generated tokens and the number of
  model calls, not prompt size.
- **Synthesizer, one call: 10–17 s for Mike, ~12 s on a trial account.** Mike's prompt is ~31k
  tokens (config 12.5k chars, recent_context ~20k chars), the trial's ~24k; both are ~75% cached.
- **Each extra Synthesizer call adds ~20–30 s.** Two calls ~42 s, three ~44 s, four ~91–114 s.
  Extra calls come from tool use inside the reply. Mike's most frequent Synthesizer tools:
  `update_task` 16, `write_wisdom` 10, `close_obligation` 10, `run_subagent` 7, `list_tasks` 6,
  `write_persona` 4, `write_quality_event` 4, `open_task` 3, `list_obligations` 3.
- **Thinking:** Mike's Synthesizer median 2.2k, up to ~5k in multi-call turns; the trials 0.6–1k.
- **Cache misses:** e.g. 10-28 10:18, `cached=0`, 54 s on one call. One 10-27 13:04 call ran 113 s
  and produced nothing (`turns=0`).
- **The pipeline outside the Synthesizer:** Coordinator 3–6 s, specialists 3–10 s each.
  Unexplained: total minus (Coordinator + slowest specialist + Synthesizer) is ~10–13 s on Mike's
  turns. Find out what it is.

## 1. Do after the reply what the reply doesn't need (first, the biggest win)

**This was rejected on 2026-10-24, for three reasons. They are the design constraints now, not
grounds to reject it again:**
1. **Confirm-gated tools return `PENDING_CONFIRMATION`.** The reply has to tell the user there is a card
   to tap, so any confirm-gated action stays in the reply path.
2. **The truth check keys on tool names.** The check that a reply doesn't claim a write that never
   happened (`synthesizer.md` + the code check) must keep working once writes run later.
3. **`done` closes the bubble** in `static/index.html`. Whatever runs afterwards must not reopen
   or edit the reply the user has already read. If it fails, the user must hear about it on a
   later turn, not see silence.

Design to settle in the plan:
- **The split, per tool:** reads the reply needs, and confirm-gated actions, stay; bookkeeping
  goes after the reply: task/obligation updates, wisdom, persona notes, quality events, logging.
- **Who runs the deferred part, and its cost:** code only, a second lighter call, or the existing
  fire-and-forget Diarist path. A second call on a smaller prompt may be cheaper; name the figure.
- **Ordering and persona safety:** the next message may arrive before the deferred work finishes.
  There is no per-persona lock (10-24: why a hard ceiling was rejected).
- **"Needed conversationally, but not in the next reply"** (Mike) is deferrable, e.g. a
  `list_tasks` re-read for a follow-up nobody asked for yet.

## 2. Cap the Synthesizer's thinking, as a quality experiment

**History to reconcile before proposing a number:**
- 08-27: a latency cap of 1,024–1,536 was **rejected for now**, because it would touch 60–85% of
  replies (`archive/plans/synthesizer_thinking_probe_2026-08-27.md`).
- 10-26: on the native path **`thinking_budget` is a target, not a bound** (a budget of 1,024 thought
  2,664). Its 08-27 "clips nothing" reading was wrong; don't cite it.
- 08-18: `thinking_budget: 0` was rejected for the Synthesizer as "the wrong trade", because it disables
  thinking altogether.
- **10-28, new:** on the day planner's path (`run_session` → compat), a cap of 1,024 gave thinking
  0, and thinking 0 **beat** thinking 6,000 on a real day (2/3 vs 0/3, 4–9 s vs 43–84 s). Mike set
  the day planner to 0 (`6a3fd86`). Which path does the Synthesizer use, and does a cap bind there?

Plan an A/B on real recent prompts (no writes): e.g. current vs a bound that actually binds vs 0,
3+ runs each. Mike judges the replies **blind**. Report latency, thinking and cost beside his verdict.

## 3. Why the cache misses

Find what makes `cached=0` happen (expiry, a prefix change, cache creation capped at 30 s since
10-26) and how often it happens in the last month. Fix it if it's cheap. Persisting things
between calls is a cost decision: see the global `CLAUDE.md` § Costs on cache lifetime.

## Constraints

- **Not concurrent with the held deploy.** `main` carries Stage C and the second-user Stage 5
  fixes, waiting for one deploy + APK. Start after it lands, or plan in a worktree and say so.
- **The Vertex tail is not this work.** 10-24: stalls are shared Google load. Mike's decision there
  was retry only, so don't reopen the Developer API fallback.
- `run_subagent` from the Synthesizer: is it reply-required? Decide per call site, don't assume.
- Tests: the stream-limits suite, the filter suites, `test_interview_mode.py`,
  `scripts/qa_sweep.sh`. Any live run stubs every meter it ends in.

Close with `/archive`.
