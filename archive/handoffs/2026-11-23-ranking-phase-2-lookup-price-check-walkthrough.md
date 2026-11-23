Model: Sonnet 5.5 — Mike reads one page and answers one question; the session edits one line.

# Ranking Part B, phase 2 — switching on the public-fact lookup (walkthrough, ~10 minutes)

**Who:** Mike, at a browser (5 minutes), then a Claude Code session (5 minutes).
**What it decides:** whether `lookup_public_fact` goes on. With it on, before asking you about a
task, Metatron can look up a public fact it turns on: a fund's closing date, how long a renewal
takes. It ships **off** (`config/modules/ranking.yaml` → `lookups.enabled: false`), because each
lookup is a Google Search grounding call that no spend meter sees
(`archive/plans/ranking_values_plan_2026-11-23.md` § 8 Unseen 1, § 11b).

## 1. The price (Mike, 5 minutes)

1. Open the Vertex AI generative AI pricing page in your browser and find **Grounding with Google
   Search** for the Gemini model the Research Agent uses (`research_agent` in
   `config/modules/routing_cloud.yaml`).
2. Note the price and its unit: per 1,000 *search queries* or per 1,000 *grounded requests*, and
   any free allowance.
3. The figure written beside the cap was **recalled, not verified**: ≈ $14 per 1,000 queries for
   Gemini 3-series, ≈ $35 per 1,000 requests for 2-series. That puts the worst case at 5 lookups a
   day × ~3 queries ≈ **$0.21 a day per user**. Say whether the real figure differs.

## 2. Figures in a question (Mike, one answer)

The guard reads the outgoing question before anything leaves. It cannot tell your £640 brake
quote from a public £15 charge, or your 52 bpm from a textbook one.
1. **Refuse them (built, recommended).** The Synthesizer rephrases without the number ("typical
   cost of brakes on a 2019 Golf") and compares your figure itself, in chat. A refused question
   costs nothing and does not use up a lookup.
2. **Let them through.** Your real quotes, balances and readings then go into Google searches.

## 3. The session (5 minutes)

1. Writes the verified price, with its date, beside the cap in `ranking.yaml` (replacing
   "recalled, not verified").
2. If the price is close to the figure above, sets `lookups.enabled: true`, and
   `refuse_figures` to your answer.
3. Commits for your next deploy. Revert is `enabled: false`.
