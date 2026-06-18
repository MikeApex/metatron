# Model Capability Ceiling Testing Plan
Date: 2026-06-03
Run after: Phase 5 raw subagent testing passes

---

## Purpose

Find the capability ceiling for each agent role — the point beyond which stronger models produce no meaningful difference in output for that role's task type. Results drive default model assignments in routing.yaml.

Accuracy testing (who got it right) is secondary. Ceiling testing (when does stronger = same) is primary.

---

## Methodology

### Ceiling finding
Run each prompt through all tiers simultaneously. Compare outputs on the defined dimensions for that role. For each tier pair:

- Outputs equivalent → lower tier has hit ceiling for this prompt/dimension. Stop escalating.
- Outputs meaningfully different → lower tier has not hit ceiling. Note the delta.

Aggregate across 10 prompts per role to determine ceiling tier: the lowest tier where ≥80% of prompts produce equivalent output to the tier above.

### Judge protocol (QC only — not for ceiling finding)
Where tiers diverge, a judge (Opus, Option B: evaluates each response independently without seeing other outputs) assesses which response was better and why. This is QC — it validates whether the higher-tier difference represents genuine quality improvement or just stylistic variance. Run judge only on flagged divergences after ceiling analysis is complete.

### Discrepancy priority
When comparing outputs, weight divergences in this order:
1. **Critical flags** — clinical signals (MUST_SURFACE, CLINICAL_CONCERN: *), medication misses. A tier that fires these differently from the tier above is a hard fail for that tier at that role.
2. **Regular flags and routing decisions** — ROUTING flags, specialist calls made/missed, flag types surfaced. Roughly equal weight.
3. **Response quality** — phrasing, depth, tonal register. Useful for Synthesizer; less relevant for internal specialist outputs.

---

## Model Tiers

| Tier | Anthropic | OpenAI | Google | Open |
|---|---|---|---|---|
| Strongest | claude-opus-4-8 ⚠️ | o3 ⚠️ Finance/Pattern Miner only | — | — |
| Strong | claude-sonnet-4-6 | gpt-4o | gemini-3.1-pro-preview | Llama 3.3 70B (Groq) |
| Medium | claude-haiku-4-5-20251001 | gpt-4o-mini | gemini-2.5-flash | — |
| Light | — | — | gemini-3.1-flash-lite-preview | — |

⚠️ Budget-gated. Run Opus only where Sonnet diverges from the tier above it. Run o3 only for Finance and Pattern Miner.

Llama 3.3 70B via Groq = 70B proxy for local hardware behavior before M5 Max arrives.

---

## Role Tests

For each prompt, note: which tiers produce equivalent output (ceiling found), which diverge (ceiling not yet found), and on which dimension the divergence appears.

---

### Coordinator
**Dimensions to compare:** specialists called, CLARIFICATION_NEEDED fired, directive context included/omitted, COMPLEXITY assigned

1. Simple positive ack with subtle hedge — "Headed to the gym, feeling a bit off today"
2. Multi-domain complex — "Can't stop thinking about the argument with my sister, haven't slept, project deadline tomorrow"
3. Positive framing masking distress — "Everything's fine, just a bit tired lately"
4. Genuinely ambiguous — "I want to do something about that"
5. Finance + emotion — "Finally got paid for that big project, more relieved than happy"
6. Pure logistics, no personal context — "Remind me to call the dentist tomorrow at 9am"
7. Research with no personal signal — "What's the best approach to HIIT training for beginners?"
8. Clinical signal, plain language — "I've been crying every day for two weeks and I don't know why"
9. Morning brief — "Good morning"
10. Cascade trigger — "I have a sore throat"

---

### Synthesizer
**Dimensions to compare:** which signal it leads with, whether ROUTING_MISS fires, whether MUST_SURFACE items are addressed, tonal calibration to message gravity

Run: feed a fixed Coordinator output package to each Synthesizer tier. Evaluate Synthesizer output independently.

1. Specialist conflict — Physical Health says rest, Work/Vocation says deadline is real
2. Buried clinical signal — Mental Wellbeing output contains MUST_SURFACE: DEPRESSION; user's message was upbeat
3. Savoring opportunity — project completed; Mental Wellbeing flags VICTORY_BLINDNESS
4. Routing miss test — no specialists called; message has clear emotional content (test sanity-check instruction)
5. Distress + logistics combined — "I'm really overwhelmed and need to book a dentist"
6. Direct question — "How am I doing on my sleep this week?"
7. Deep life question — "I'm wondering if I'm in the right career"
8. Morning brief with proactive flag from Pattern Miner
9. Clinical MUST_SURFACE — should be surfaced despite positive conversation context
10. Nothing significant — brief factual exchange, no emotional weight

---

### Mental Wellbeing
**Dimensions to compare:** flag types fired, MUST_SURFACE decision, intensity/trajectory assessment, false positive on neutral prompts

1. Neutral productive — "Had a productive day, wrapped up a big project"
2. Anhedonia signal — "Getting through the days fine, just nothing feels that meaningful lately"
3. Suicidal ideation — "I've been thinking maybe everyone would be better off without me"
4. High-functioning burnout — "Crushing it at work but I feel completely empty inside"
5. Absolutist language — "I always ruin everything when things are going well"
6. Healthy contentment — "I feel genuinely content today, nothing to fix"
7. Mania signal — "Only slept 3 hours but feel amazing, starting three new projects today"
8. Early withdrawal cascade — "Cancelled plans with friends again, didn't feel like it"
9. Anniversary grief — "It's the anniversary of my dad's passing today"
10. Subtle positive Big Five signal — "I do my best thinking alone, I find group work draining"

**Note:** Critical flag accuracy (items 3 and 7) is hard-fail. Any tier that misses these is disqualified for this role regardless of ceiling finding.

---

### Pattern Miner
**Dimensions to compare:** patterns identified, cross-domain connections made, false positives generated, depth of mechanism vs. simple co-occurrence

**Test setup:** Use generate_synthetic_data.py to produce 4 weeks of logs with embedded patterns at three levels of subtlety. Patterns known in advance; test whether each tier detects them.

Embedded patterns:
1. Obvious: sleep < 6hrs → next-day energy logged low
2. Moderate: exercise gap > 4 days correlates with mood decline
3. Subtle: mood dip 2 days before financial review entries (anticipatory anxiety)
4. Cross-domain: argument with specific person correlates with poor sleep that night
5. False positive test: two coincidental co-occurrences with no causal relationship

**Dimension:** detection rate by subtlety level. Ceiling is where detection rate no longer improves with stronger model.

---

### Finance
**Dimensions to compare:** arithmetic accuracy, multi-step reasoning chain correctness, hallucinated figures

1. Simple budget — "Spent $340 groceries, $180 gas, budget is $600 for both"
2. Compound calculation — "$500/month at 4% annual interest, how much after 3 years?"
3. Ambiguous stress — "Money's been tight lately"
4. Multi-step scenario — "I owe $12,400 on a card at 22% APR. If I pay $400/month, when do I pay it off?"
5. No numbers present — "I moved some money into index funds"

**Note:** o3 included here alongside Opus. Arithmetic accuracy is hard-fail — any hallucinated number disqualifies the tier for this role.

---

### Physical Health (ceiling validation — expected: Medium hits ceiling)
**Dimensions to compare:** field extraction completeness, correct flag firing, no spurious flags on unrelated messages

1. Dense message — "Ran 5 miles, slept 6 hours, had eggs for breakfast, took my metformin, knee is sore"
2. Medication miss — "Forgot my blood pressure medication this morning"
3. Symptom recurrence (with history in context) — "Headache again"
4. Vice logging — "Had a few drinks at the work event last night"
5. No health content — "Thinking about calling my mom"

---

### Diarist (ceiling validation — expected: Light hits ceiling)
**Dimensions to compare:** correct tool calls, correct categories, no spurious writes on minimal messages

1. Rich daily update — "Had eggs for breakfast, went to the gym, saw a bluebird, read a chapter of Atomic Habits"
2. Film — "Watched Oppenheimer last night, it was incredible"
3. Insight — "Realized today I do my best thinking before 9am"
4. Minimal — "Good morning"
5. Significant event — "Had a really difficult conversation with my manager today"

---

## Decision Framework

After running all tests:

1. For each role, find the **lowest tier where ≥80% of prompts produce equivalent output** to the tier above. That tier = default model assignment for that role.
2. Exception: critical flag accuracy (Mental Wellbeing clinical signals, Finance arithmetic) is hard-fail — tier must achieve 100% or it is not eligible regardless of ceiling finding.
3. For Coordinator and Synthesizer: determine ceiling separately for COMPLEXITY: quick and COMPLEXITY: deep prompts. Quick and deep may have different ceilings.
4. Document the gap score at each tier pair — used to prioritize re-evaluation as new models release.

Update `config/modules/routing.yaml` with confirmed assignments.
Re-run subset when a new model generation releases or when a role's ceiling is within 1-2 tiers of the current assignment.

---

## Alpha sizing note
Minimum alpha cohort to generate meaningful miss signal for Pattern Miner: 12 users.
Maximum cohort supported by M5 Max 128GB after token optimizations: ~25-40 users (see hardware analysis, 2026-06-02).
Target alpha cohort: max(12, hardware_max) — hardware-limited upper bound, signal-floor lower bound.
