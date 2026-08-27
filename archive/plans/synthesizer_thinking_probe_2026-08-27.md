# Synthesizer thinking-token probe — 2026-08-27

*The measurement `[DB-0827-02]` (thinking cap) and `[DB-0820-05]` (all-Pro routing) both name as
their prerequisite. Pulled from the live VM (`/monitor/traces?persona=mike`), 226 traces
2026-08-19 → 2026-08-27 — the clean window after the Option A caching/streaming fix (`46f31b5`)
deployed. 105 contain a Synthesizer step. Model throughout: `gemini-3.1-pro-preview`.*

## Distribution per reply

| Thinking tokens | n | min | median | p75 | p90 | p95 | p99 | max | mean |
|---|---|---|---|---|---|---|---|---|---|
| Interactive (`is_proactive: false`) | 28 | 0 | 1,063 | 1,532 | 2,094 | 2,523 | 2,871 | 2,871 | 1,191 |
| Proactive (scheduled) | 77 | 0 | 1,889 | 2,647 | 3,109 | 3,807 | 3,930 | 3,930 | 2,102 |
| **All** | 105 | 0 | 1,702 | 2,484 | 2,985 | 3,217 | 3,930 | 3,930 | 1,859 |

| Visible output tokens | n | median | p90 | p95 | max |
|---|---|---|---|---|---|
| All | 105 | 238 | 566 | 583 | 629 |

**Thinking share of generated tokens: 86.1%** (195,196 of 226,678) — confirms the recorded
figure on fresh post-fix data.

## What a budget would clip (9-day window, $12/M output rate)

| `thinking_budget` | Replies clipped | Think-tokens saved | $ saved / 9 days |
|---|---|---|---|
| 4,096 | 0 / 105 (0%) | 0 | $0.00 |
| 3,072 (~p90) | 10 (10%) | 3,901 | $0.05 |
| 2,048 | 37 (35%) | 27,279 | $0.33 |
| 1,536 | 65 (62%) | 52,034 | $0.62 |
| 1,024 | 89 (85%) | 92,315 | $1.11 |
| 512 | 103 (98%) | 142,460 | $1.71 |

## Findings

1. **There is no tail.** Max observed (3,930) sits barely above p95 (3,217). The "generous cap
   clips the expensive outliers" theory fails on this data — there are no expensive outliers.
   Every dollar a cap recovers comes out of the distribution's body, which is the quality-risk
   zone.
2. **The whole exposure is ~$0.26/day.** 195k thinking tokens over 9 days = $2.34. Against the
   measured ~$1.82–3/day bill (post cache fix), a cost-motivated cap is not worth a config edit,
   let alone a safety gate run. `[DB-0827-02]`'s "unbounded" is true in code and bounded in
   practice.
3. **Proactive turns think hardest and dominate volume** — 77 of 105 replies, median 1,889 vs
   1,063 interactive. The latency motive (time-to-first-word, ~15s of a ~20s reply) applies only
   to the 28 interactive turns; the longest thinkers have nobody waiting on them.
4. **`[DB-0820-05]` assumption 1 (output inflation) moves in the reassuring direction.** Modelled
   at 3× with a 7× worst case; the live Pro agent's generation is compact and stable across the
   window. The B′ (all-Pro) arithmetic does not degrade on this evidence.

## Recommendation carried to the decisions session

- **Cap at 4,096 as insurance, not economy.** Clips nothing today, costs quality nothing,
  converts "no cap anywhere in the codebase" into "bounded at observed-max +4%". Run the A4
  pipeline gate once after the change — the Synthesizer carries clinical flags, so any
  `thinking_config` change is safety-adjacent by definition (`[DB-0827-02]`).
- **Do not cap for cost.** The money is not there (finding 2).
- **A latency-motivated cap (1,024–1,536) is a separate, deliberate experiment** — it touches
  60–85% of replies, so it needs quality probes beyond the A4 gate. If run, consider capping
  interactive turns only: `thinking_config` is per-request and does not touch the prompt cache
  key, and `is_proactive` is available at the call site, so a split policy is mechanically free.
  Proactive replies (push-notification content) keep full budget; nobody is waiting on them
  anyway — but note that inverts finding 3's cost logic, which is why this stays an experiment,
  not the recommendation.

## Caveats

- n=105 over 9 days of single-user use; includes whatever development testing ran in the window.
- Trace turn records in this window carry no cache-read field, so cache effectiveness was not
  re-verified here — this probe measures generation only.
- The observed max (3,930) may reflect an implicit provider ceiling rather than the model's
  natural range; the probe cannot distinguish those. Irrelevant to the recommendation either way.
