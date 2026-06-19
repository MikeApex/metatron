# Compliance Curve — Design Decisions
*A1 parallel track. Session started 2026-06-13; completed and updated 2026-06-18.*
*Governs A5c and all habit-formation features (Phase 6 / E4).*
*File ownership: this document + future_phases.md. Do not edit synthesizer.md, coordinator.md, orchestrator.py, routing.yaml, or constitution.md.*

**Research sources:** GPT-5.4 (OpenAI), GPT o3 (OpenAI), Gemini 3.1 Pro Preview (Google), Claude Sonnet 4.6 (adjudicator). Claude Opus 4.7 timed out on both queries; o3 and Gemini 3.1 runs added 2026-06-18. *Note: Gemini 2.5 Pro was used in the initial June 13 session due to a misconfiguration; 3.1 Pro is the correct default and was used for the updated run.*

---

## Summary of Decisions

| # | Question | Decision |
|---|---|---|
| Q1 | Which agent calibrates new behavior introduction? | Shared principle across all specialists; Synthesizer as final integrator |
| Q2 | What is the ratchet mechanism? | Cold-start: user-reported. Operating mode: research-gated (pending) |
| Q3 | Constitution or Synthesizer level? | Synthesizer level only |
| Q4 | Which preferences.yaml settings activate at A5c? | None. A5c produces a documented activation plan, not live activations |

---

## Q1 — Calibration Ownership

**Decision:** Shared principle.

All specialist agents calibrate new behavior introduction within their domain. Synthesizer exercises final judgment about cross-domain balance, sequencing, and whether the full set of introduced behaviors is manageable simultaneously.

**Rationale:**
- Synthesizer will not have space in every session to direct from every domain. Many sessions go directly to Logistics, Physical Health, or another specialist. If calibration responsibility lived only with Synthesizer, it would go unenforced in most interactions.
- Uptake rates differ between domains (sleep vs. exercise vs. finance) and between goals within a domain. Per-specialist calibration captures domain context.
- Synthesizer's role is judgment about what fits across the whole picture — not re-running calibration from scratch per session.

**Shared principle (exact proposed instruction text — to be added to each specialist agent file):**

> **Compliance calibration.** Before introducing a new behavior or raising an existing target, ask at least one diagnostic question that anchors the goal to what the user can actually do today — not what they aspire to or what they did historically at their peak. Ask what they could still manage on a bad, low-energy day. Set the first target at that level or below. Users can and should outperform their targets; there is no ceiling. The goal of the first rep is a successful first rep, not the right rep. Do not introduce more than one new behavior at a time without Synthesizer guidance.

**Synthesizer instruction addition (to be added to synthesizer.md when A2 chat closes):**

> **Cross-domain compliance balance.** When assessing what to introduce in a session, consider the cumulative load of any new behaviors already recently initiated across specialists. A user can only absorb so much new direction at once. Exercise judgment about sequencing — one behavior established before the next is introduced. If multiple specialists have recently introduced new targets, flag the accumulation and give the existing behaviors time to stabilize before adding more.

---

## Q2 — Ratchet Mechanism

**Decision (partial):** Cold-start is user-reported. Automated ratchet is research-gated.

### Cold-start (Alpha)
First calibration uses user-reported data only:
1. Ask the diagnostic question: "What could you still manage on a bad, low-energy day?"
2. Ask for prior history: have they done this before (novice / restarter / prior failures)?
3. **Dual diagnostic check** — both thresholds must pass:
   - **Confidence:** "On a scale of 1-10, how confident are you that you could do this every day this week, even on a bad day?" — Novice/restarter: ≥7. Prior failure history: ≥9 (AVE risk is higher; another failure compounds it). Gemini 3.1 frames this as the "Motivational Interviewing Confidence Ruler" and sets the threshold at ≥8 before scaling down; the ≥9 bar for failure-history users is the adjudicator's synthesis. *[GPT 5.4; o3; Gemini 3.1 / Marlatt & Gordon 1985]*
   - **Meaning:** "On a scale of 1-10, how meaningful would hitting this target feel?" — All users: ≥6. If below 6, the target is either too trivially small to feel real, or the goal framing needs re-anchoring to why it matters. Increase the target or re-frame before proceeding. *[GPT o3]*
4. If either check fails, reduce the target or re-frame and re-check.
5. Set a "minimum viable day" floor that stays constant even as the primary target grows.

### Operating mode ratchet (Phase 6 / research-gated)
How the tool detects readiness to step up, and how it steps back when compliance fails, is deferred pending:

1. Pattern Miner behavioral data (requires weeks of actual usage)
2. External research results on: optimal progression rates by behavior type, evidence-based ratchet algorithms from behavior change literature, and gamification mechanics for sustainable engagement

See Research Synthesis below for what has been gathered so far on ratchet design.

### What the evidence says about step-up timing (from Research Synthesis)
- Hold until ≥80% adherence over 2 weeks — not one great motivated week. *[GPT o3 / Buist 2008; Kaushal & Rhodes 2015]*
- Increase one dimension at a time: for exercise, frequency before duration before intensity. *[GPT 5.4; o3]*
- Increase ≤10–20% per step. The 10% rule has endurance-exercise injury-prevention evidence; it applies as a conservative upper bound across behavior types. *[GPT o3 / Buist 2008]*
- For users with prior failure history: require 14–21 consecutive successes (Gemini 3.1: 14 consecutive days of automaticity) before first escalation — longer stabilization window. *[GPT o3; Gemini 3.1]*
- After any increase, recheck both confidence and meaning. If either falls below threshold, the step was too large.
- Preserve the minimum viable day floor permanently — even at high operating level.

### What the evidence says about step-back (from Research Synthesis)
- One miss ≠ step-back. Normalize the miss. "One missed day is data, not failure."
- A pattern of misses (e.g., 3 of last 7 days) is the signal for recalibration, not an individual lapse.
- For users with prior failure history, a lapse triggers AVE risk. Proactive reframe immediately: "You've shown up X of the last Y days — that's the data we build from."
- Step-back is a reduction in the primary target only, not elimination of the behavior. The floor stays.

---

## Q3 — Constitution vs. Synthesizer Level

**Decision:** Synthesizer level only.

The Constitution already covers the relevant ground: the tool "never optimizes for short-term output at the expense of long-term wellbeing" and "earns greater trust and capability over time." Compliance calibration is tactical implementation of that principle, not a new principle. Adding it to the Constitution would conflate architecture levels.

---

## Q4 — A5c Preference Activation

**Decision:** Nothing activates at A5c launch. A5c is a design and documentation session that produces an activation plan for review.

**Rationale:**
- All `config/preferences.yaml` opt-ins are currently false. This is the correct default.
- Alpha users should not encounter autonomous expenditure, social outreach, or booking without explicit onboarding.
- A5c produces: (a) a written activation criteria document, (b) proposed order of opt-in introduction, (c) proposed instruction text for Synthesizer around how to propose activations to the user.

**Proposed A5c output:**
- `archive/plans/a5c_activation_plan_[date].md`
- Proposed order: bookings first (lowest social/financial risk), then expenditure with low threshold, then social outreach.
- Synthesizer instruction for offering opt-ins: only after a minimum of N sessions, and only when the user has demonstrated the relevant need organically (not proactively pitched).

---

## Research Synthesis

*Research conducted 2026-06-18. Models queried: GPT-5.4 (OpenAI), GPT o3 (OpenAI), Gemini 2.5 Pro (Google). Claude Sonnet 4.6 (Anthropic) adjudicating. Claude Opus 4.7 timed out on both queries. o3 run added same day.*

---

### Research 1 — Compliance Science: Optimal Starting Points

#### Core finding — convergence across all models

**Start well below current capability.** The relevant floor is not "best-day capability" but "bad-day capability" — what the user can still do on a low-energy, disrupted weekday. GPT o3 synthesizes Fogg and Locke/Latham into a specific band: first target at 10–25% above current reliable capacity. Gemini 3.1 frames this as less than 20% of perceived maximum capacity. Beyond that range, early-failure risk overtakes motivation gain. o3 cites an n=110 meta-analysis with d≈0.52 for moderate stretch vs. easy goals. *[GPT o3; Gemini 3.1 / Locke & Latham 2002; Locke & Latham 2006; ⚠ Locke et al. 1981 cited by o3 as n=110 meta-analysis, d≈0.52 — likely conflated with Tubbs 1986 or Mento et al. 1987; verify before citing]*

**Self-efficacy is the causal mechanism.** Early wins rebuild self-efficacy; early failures compound it in the wrong direction. Across physical activity, diet, smoking cessation, and other health behaviors, self-efficacy is among the strongest predictors of persistence. *[All models / Bandura 1997; Bandura 1977]*

**Fogg vs. Locke/Latham resolved.** Tiny Habits = process goal (build the routine). Locke/Latham challenging goal = outcome goal (aspirational target). Both are right at different stages. Gemini 3.1 adds: the Fogg/Locke tension resolves cleanly through SDT — start with Fogg to build competence, transition to Locke/Latham once automaticity is established. Critical caveat (GPT o3): tiny habit approaches achieve 80–90% 7-day adherence but only convert to larger behaviour if an explicit escalation plan is added at the outset. *[GPT o3; Gemini 3.1 / Fogg 2020; Locke & Latham 2002; ⚠ Maitland et al. 2020 RCT N=676 JMIR cited by o3 for 80–90% figure — cannot verify this specific paper]*

**Implementation intentions substantially improve enactment.** Specify when/where/if-then. A modest target with a strong if-then plan often outperforms a "better" target with vague timing. *[All models / Gollwitzer & Sheeran 2006, meta-analysis ds≈0.65; Bélanger-Gravel et al. 2013 (plausible — verify before academic use)]*

---

#### User type differentiation

**Novice (no prior experience)**
- Start at tiny-habit floor + ~10% stretch. Optimize for learning the routine, not performance.
- Identity framing: "you are becoming someone who does X." *[Gemini 2.5; 3.1 / Deci & Ryan 2000]*
- Anchor to a specific existing cue (implementation intention). *[All models / Gollwitzer 1999]*
- Metrics: frequency before volume. First goal is showing up, not dosage.

**Restarter (formerly sustained this habit)**
- Start at 50–70% of former peak, or current capacity +10–25%, whichever is lower. *[GPT o3]*
- Restarters carry procedural memory but often mismatch their current context against former conditions. Re-entry dose, not former dose. "Rebuild consistency before intensity."
- Leverage prior success as evidence of capability, not as baseline to resume immediately. *[Gemini Pro / Marlatt & Gordon 1985]*
- Calibration nuance: restarters often underestimate procedural memory, feel more rusty than they are, then overshoot when they realize they're capable. A 2-week progressive re-entry arc is safer than a fixed percentage rule. *[Adjudicator]*

**Repeat failer (tried and failed at this goal multiple times)**
- Most psychologically delicate. Self-efficacy is likely impaired; AVE risk is high — one failure can confirm "I never stick with this." *[All models / Marlatt & Gordon 1985]*
- Start conservatively, often below current confident capacity. Confidence check threshold rises to ≥9/10 for this population.
- Self-compassion exercises improve persistence (d=0.43) and resumption after lapse (d=0.57 on resumption latency). *[GPT o3 / ⚠ Turk & Rudolph 2022 — unverifiable, verify before use; Breines & Chen 2012, PSPB — cited by o3 as "2014, Self Identity," corrected to actual 2012 PSPB]*
- Wait 14–21 consecutive successes before first escalation — the stabilization window is longer. *[GPT o3]*
- Anti-all-or-nothing architecture required from session 1: minimum version, backup version, explicit lapse recovery rule pre-planned before the first lapse occurs.
- Frame: "We are testing a method, not testing your character."

---

#### Diagnostic questions

**When history is known:**
- "What could you still manage on a bad, low-energy day?" → calibration floor
- "At what point in previous attempts did it break?" → failure analysis (more diagnostic than "how many times have you tried?") *[Adjudicator]*
- "What was different when it worked vs. when it stopped?" → context factors
- Confidence check (≥7 novice/restarter, ≥9 failure history): "How confident are you you'll do this every day this week, even on a bad day?"
- Meaning check (≥6 all users): "How meaningful would hitting this feel?" *[GPT o3]*

**When history is unknown:**
- Start with a default tiny target and gauge the reaction. If they dismiss it as too easy, keep the minimum but add a recommended and stretch tier. *[Gemini 2.5; 3.1]*
- Gemini 3.1 adds the **Aversion Test**: "When you think about starting [Behavior X] at [Level Y], do you feel expansion (excitement) or contraction (dread/heaviness)?" Somatic markers of dread indicate the ghost of past failures — scale the goal down further. *[Gemini 3.1]*
- Use confidence and meaning checks as the primary calibration signal — they work without prior history.
- Frame as experiment: "Let's try this for 3 days — it's just a test to gather data." *[Gemini 2.5; 3.1]*

---

#### Escalation and progression

- Progress gate: ≥80% adherence over 2 weeks, not after a single motivated week. *[GPT o3 / Kaushal & Rhodes 2015]*
- Increase ≤10–20% per step; the 10% rule has injury-prevention evidence in endurance training and applies as a conservative upper bound across behaviors. *[GPT o3 / Buist 2008]*
- Increase one dimension at a time: frequency before duration before intensity.
- Recheck confidence and meaning after each increase. If either falls below threshold, the step was too large.
- Repeat-failer users: wait 14–21 consecutive successes before first escalation. *[GPT o3]*
- Preserve the minimum viable day floor permanently — it does not disappear as the primary target grows.

---

#### Failure modes

**Too hard:** immediate friction, missed reps, self-blame, avoidance, abandonment after minor lapses. Especially dangerous for failure-history users: AVE means one miss confirms "I knew I wouldn't stick with it." *[All models / Marlatt & Gordon 1985]*

**Too easy:** boredom, "checkboxing," low meaning score, no identity shift, dropout via low salience. Fix: keep the floor small, improve framing and connection to larger purpose, progress sooner, add standard/stretch tiers. *[GPT 5.4; o3]*

**Failure-history specific:** redemption overreach (start aggressively to "finally do it right" → rapid collapse); shame-triggered avoidance after one miss; reenacting the same failed architecture. The intervention must change the failure script, not just the behavior. *[GPT 5.4]*

---

#### Adjudicator additions

**1. The aspirational beginner gap.** A fourth user type not covered by any model: no track record, high self-assessed capability, unrealistic ambition. Presents like a novice but responds to first failure like a repeat-failer. Apply repeat-failer architecture preemptively. *[Adjudicator]*

**2. Failure-point analysis is the primary diagnostic for returning users.** "At what point did it break?" is more useful than "how many times have you tried?" A user who drops at Week 3 every time has a Week-3 problem — the intervention is different from a starting-point problem. *[Adjudicator]*

**3. Confidence and meaning thresholds are population-specific.** Gemini's ≥9-10 and GPT 5.4's ≥7 are both correct — for their respective populations. The population split (failure history = higher bar) matters for system design. *[Adjudicator]*

---

### Research 2 — App Uptake Mechanics

#### Novelty curve

Across mobile health and productivity apps, engagement follows a predictable negative exponential:
- Day-1 retention ≈ 40–55% → Day-7 ≈ 24–30% → Day-30 ≈ 12–18% → Day-60 ≈ 6–10%. *[GPT o3 / Mixpanel 2023; Prieto 2022]*
- The novelty/Hawthorne bump in digital health is quantified: d≈0.40 at week 1, declining to d≈0.09 by week 6. *[GPT o3 / Perski & Blandford 2017, meta-analysis N=38 RCTs]*

The design goal is not to prevent the drop but to convert a higher percentage of users into the stable cohort. The first 4–8 weeks are a closing window where scaffolds must convert extrinsic novelty energy into habit loops and internalised value. *[GPT 5.4; o3]*

---

#### What works, what backfires, longer-term effects

**Streaks**
- Streaks leverage loss aversion and add +11% 30-day retention when well-implemented. *[GPT o3; Gemini 3.1 / ⚠ Milkman et al. 2021, cited as Nature Comm — cannot verify this specific paper or journal; Milkman's verified 2021 work is on vaccine nudges in Nature/PNAS]*
- Backfire condition: hard reset after one miss triggers AVE for failure-history users, confirming the "I never stick with it" narrative. *[All models / Marlatt & Gordon 1985]*
- Fix: streak freeze tokens (Duolingo), rolling-window streaks ("X of last 7 days"), or "forgive one miss/week" mechanics. Gemini 3.1 cites RCT evidence that goals with built-in skip-days outperform rigid streaks. *[GPT o3; Gemini 3.1 / Sharif & Shu 2012 (plausible — verify before academic use)]*

**Notifications**
- 1/day personalised = 3× open rate vs. generic. *[GPT o3 / ⚠ Kim & Benyo 2020 CHI — cannot verify this specific paper]*
- >3/day doubles opt-out odds. *[GPT o3 / ⚠ Localytics 2022 — industry benchmark report, unverified]*
- Notifications delivered during motivation-ability mismatch (e.g., 6am to a night-owl) accelerate churn. *[Gemini 3.1 / Fogg 2009]*
- Best used as temporary scaffolds toward internal trigger formation, not permanent architecture. *[Gemini 2.5; 3.1]*

**Gamification (points, badges, leaderboards)**
- Progress bars and points: g=+0.27 short-term behavioural quantity. *[GPT o3 / ~ Mekler et al. 2017 — plausible, verify specific effect sizes]*
- Leaderboards: help top quartile, hurt bottom quartile (g=−0.15 for bottom performers). Use personal-record or cohort-matched comparisons. Gemini 3.1 example: Strava defaults to personal records rather than global rankings. *[GPT o3; Gemini 3.1 / ~ Mekler et al. 2017 — plausible, verify specific effect sizes]*
- Long-term risk: overjustification effect — extrinsic rewards undermine intrinsic motivation when they become the primary reason for engagement. *[Gemini 2.5; 3.1 / Deci, Koestner & Ryan 1999]*

**Monetary incentives**
- Short-term adherence lift, but 60% of users stop when cash incentives end. *[GPT o3 / ⚠ Chao 2021 — cannot verify; crowding-out effect itself is well-established: Deci, Koestner & Ryan 1999]*
- Use as ignition, not engine. Transition to competence feedback and self-endorsed goals before incentives end. *[GPT 5.4]*

**Social features**
- Small-group accountability and peer support outperform public leaderboards for sustained engagement. *[GPT 5.4; Gemini 3.1]*
- Forced or public sharing backfires. Gemini 3.1 example: Strava's success is partly because it defaults to personal-record framing, not pure global ranking. *[GPT o3; Gemini 3.1]*
- Social relatedness is one of the three SDT needs — relatedness-supporting features sustain engagement quality after novelty fades. *[All models / Ng et al. 2012]*
- Human coach: +29% D30 retention vs. bot (RCT). *[GPT o3 / ⚠ Chen 2020 — cannot verify this specific paper]*
- Forced public sharing backfires: Facebook health auto-posts caused −10% retention. *[GPT o3 / ⚠ Munson 2017, ACM CSCW — cannot verify this specific paper or figure]*

**Self-monitoring**
- One of the most consistently replicated behavior-change techniques across health domains. *[GPT 5.4 / Harkin et al. 2016]*
- Must be low-friction; high-burden tracking decays sharply. *[GPT 5.4]*

---

#### Bridging novelty to habit — what actually works

1. Stable cue-action structure (implementation intention in onboarding). *[All models / Gollwitzer & Sheeran 2006]*
2. Quick win in session 1: <60-second time-to-value predicts +8–12pp 7-day retention. *[GPT o3 / ⚠ App Annie 2021 — industry benchmark, no academic review process; finding consistent with Bandura 1997]*
3. Immediate felt reward (calm, completion, momentum, reduced anxiety). *[GPT 5.4; o3]*
4. Identity self-label at week 4: prompting "I'm a meditator" at the 4-week mark increases 12-week retention 1.4×. *[GPT o3 / ⚠ Headspace internal A/B data — proprietary, unverifiable; finding consistent with Deci & Ryan 2000]*
5. Lapse recovery design: lapse-forgiveness messaging halves churn following the first 5-day inactivity gap. Must fire during the gap, not after. *[GPT o3 / ⚠ Inkster 2020 — cannot verify this specific paper; finding consistent with Marlatt & Gordon 1985]*
6. Investment layer (Hooked model): stored personal data, history, and rapport create switching costs that outlast any gamification mechanic. *[Gemini Pro / Eyal 2014]*

**Week-by-week operational pattern** *[GPT 5.4]*:
- Weeks 1–2: friction reduction, single behavior, first win, implementation intention, one reminder
- Weeks 3–4: adaptive to real conditions, backup version, flexible consistency view
- Weeks 5–6: deepen value (trend insights, milestone reflection, optional accountability)
- Weeks 7–8: sustainable mode (reduce prompting, user-controlled structure, weekly review, preserve minimum floor)

**Maintenance mode:** Weekly check-in cadence reduces monthly active minutes only 15% but doubles 180-day survival rate vs. standard cadence. *[GPT o3 / ⚠ WW Digital 2019 — proprietary internal data, unverifiable]*

---

#### Adjudicator additions

**1. The proactive-initiation inversion.** All models assume the user initiates and the product provides triggers (Fogg's prompt). For a proactive life manager with Phase 4 scheduling, the tool initiates. The external-to-internal trigger transition is therefore inverted: the user needs to internalize not "I should check the app" but "I should be receptive when the tool reaches me." No analog exists in the standard behavior change literature — consumer apps do not proactively initiate at this level. This requires its own design consideration when specifying scheduler cadence and Synthesizer re-engagement behavior. *[Adjudicator]*

**2. Investment as the primary long-term moat for this product.** The standard Hooked investment mechanic applies here with unusual force. Every session adds to Pattern Miner baselines, journal depth, memory, and rapport. The longer someone uses it, the worse stopping becomes — not because of points, but because they would lose an increasingly accurate model of themselves. "Your coach now knows X things about you" is a more durable motivator than a streak counter. Design features should amplify this explicitly over time. *[Adjudicator / Eyal 2014]*

**3. The AI-novelty curve is different from standard app novelty.** The novelty for a life manager isn't just "new app" — it's "talking to something that seems to understand me." Users project more capability and rapport than the system currently delivers. The drop-off happens when the gap between projection and delivery becomes visible. Design implication: calibrate expectations early, deliver substantive value in session 1 (not presence alone), and design toward progressively deeper engagement. The goal is not to sustain the "wow" — it's to deliver real utility that replaces the wow. *[Adjudicator]*

**4. Lapse recovery is a tool capability here, not a UX mechanic.** Synthesizer will proactively notice lapses and can initiate re-engagement. The agent instruction needs to specify: how to detect lapse signal (Pattern Miner / missed check-ins), how to re-engage without triggering shame, and how to set a re-entry dose rather than resuming at the prior level. *[Adjudicator]*

---

#### Gemini 3.1 unique contributions

**1. IKEA Effect / Meaningful Friction in onboarding.** Counterintuitively, some upfront friction in onboarding increases retention. Long personalized quizzes (Noom, Superhuman) act as an Investment layer — triggering sunk-cost and increasing perceived product value. Related: "harvest high Day-1 motivation for one-time hard setup tasks" (sync calendar, connect health data) rather than spending it on UI explanation. *[Gemini 3.1 / Eyal 2014]*

**2. Emergency Reserves as a streak alternative.** Goals with built-in skip-days ("7 days/week with 2 emergency skips") outperform rigid goals and flexible "X of Y" streaks. The skip-day must cost something (a token, a public commitment) to maintain its psychological value. *[Gemini 3.1 / Sharif & Shu 2012 (plausible)]*

**3. Range goals over fixed goals in operating mode.** Once a behavior is established, switching to a range ("3 to 5 times a week") sustains engagement better than a fixed target. Reduces all-or-nothing pressure while preserving challenge. Relevant to Phase 6 ratchet design. *[Gemini 3.1]*

**4. Data-as-mirror at week 4+.** By week 4, the product holds enough personal data to shift from prescriptive instructions to personalized insights ("we noticed that on days you drink alcohol, your resting heart rate stays elevated"). This fulfills SDT Autonomy — the user draws their own conclusions rather than following instructions. Relevant to how Pattern Miner outputs feed into Synthesizer after sufficient baseline data. *[Gemini 3.1 / Deci & Ryan 2000]*

---

## Proposed Agent Instruction Text

### For all specialist agents (add to each specialist file)

> **Compliance calibration.** Before introducing a new behavior or raising an existing target, ask at least one diagnostic question that anchors the goal to what the user can actually do today — not what they aspire to or what they did at their historical peak. Ask: "What could you still manage on a bad, low-energy day?" That is the floor for the first target. Set the initial target at or below that level.
>
> Determine user type:
> - **Novice** (no prior experience): Focus on learning the routine. Anchor to a specific cue. Frame success as showing up, not performance.
> - **Restarter** (formerly sustained this habit): Use a re-entry dose — not the former peak, not the former maintenance level. Rebuild consistency before intensity.
> - **Prior failure history**: Start conservatively. Build in a backup version for hard days and an explicit lapse recovery rule ("one missed day is data, not failure"). Use the confidence check: target should rate ≥9/10 confidence for this population.
>
> **Dual diagnostic check** — both must pass before finalising any target:
> - *Confidence:* "On a scale of 1-10, how confident are you that you could do this for the next 7 days, even on a bad day?" Threshold: ≥7 for novice/restarter; ≥9 for users with prior failure history.
> - *Meaning:* "On a scale of 1-10, how meaningful would hitting this target feel?" Threshold: ≥6 for all users. Below 6, either the target is too small to feel real, or the goal needs re-anchoring to why it matters — increase the target or re-frame before proceeding.
> If either check fails, reduce or re-frame the target and re-check.
>
> Set a minimum viable day floor. This stays in place permanently, even as the main target grows. On hard days, the floor is the goal.
>
> Require an implementation intention before closing: when will this happen? Where? What if it gets disrupted?
>
> **Progression gate:** increase a target only after ≥80% adherence over 2 weeks. Increase ≤10–20% per step, one dimension at a time (frequency before duration before intensity). For users with prior failure history, wait for 14–21 consecutive successes before first escalation. After any increase, recheck both confidence and meaning.
>
> Users can and should outperform their targets. There is no ceiling on upward performance. The floor is a safety net, not a limit.
>
> Do not introduce more than one new behavior at a time without Synthesizer guidance.

### For Synthesizer (add to synthesizer.md)

> **Cross-domain compliance balance.** Consider the cumulative load of behaviors recently introduced across specialists. A user can absorb only so much new direction at once. When multiple specialists have recently introduced new targets, exercise judgment about sequencing — give existing behaviors time to stabilize before adding more. If cumulative load appears high, hold new introductions until the pattern is stable. Log a ROUTING_MISS if this judgment is made but a specialist has already introduced something that should have waited.

---

## A5c Activation Plan Guidance

At A5c, no settings in `config/preferences.yaml` activate. A5c produces:

1. A written document: `archive/plans/a5c_activation_plan_[date].md`
2. Proposed opt-in introduction order:
   - Phase 1: bookings (lowest risk — reversible, no financial/social exposure)
   - Phase 2: expenditure with low threshold (financial exposure but bounded)
   - Phase 3: social outreach (highest trust requirement, hardest to reverse)
3. Synthesizer instruction text for how to offer opt-ins organically (not proactively pitched; only surfaced after demonstrated need)
4. Criteria for when Synthesizer should suggest activating each setting

---

## Pending Research (Ratchet Mechanism — Phase 6)

The automated step-up/step-back mechanism is deferred. Research needed before building:

1. **Optimal progression rates by behavior type** — how fast to increase frequency, duration, intensity for different behavior classes. The evidence has domain-specific answers that differ significantly (exercise vs. meditation vs. dietary habits).
2. **Automated detection of compliance stability** — what signals (Pattern Miner) reliably indicate a behavior is habit-stable vs. compliance-fragile. Raw streak data is insufficient; need behavioral consistency signals.
3. **Lapse detection and re-engagement patterns** — what does a healthy vs. concerning lapse pattern look like? How to distinguish "life got busy for a week" from "losing traction."
4. **Reward and gamification integration** — what mechanics, if any, are appropriate for this tool given its constitution (companion, not director; intrinsic over extrinsic). This is the conversation deferred in `future_phases.md` — compliance development must be designed before building.

---

## File Edits Queued (apply when A2 chat closes)

1. **Each specialist agent file** — add the compliance calibration instruction block above.
   - Files: `config/agents/physical_health.md`, `config/agents/mental_wellbeing.md`, `config/agents/logistics.md`, `config/agents/finance.md`, `config/agents/learning_growth.md`, `config/agents/social.md`
   - Section: add after the agent's core instruction, before any tool listings

2. **`config/agents/synthesizer.md`** — add the cross-domain compliance balance instruction.
   - Section: under Proactive Anticipation or as new subsection "Compliance Balance"

3. **`archive/plans/future_phases.md`** — mark the compliance curve design questions block (lines 85-99) as resolved: prepend "RESOLVED — see archive/plans/compliance_curve_decision_2026-06-13.md"

---

## Bibliography

*Confidence ratings: ✓ verified · ~ plausible (verify before academic citation) · ⚠ probable error or hallucination (do not cite)*

### Verified academic sources

- ✓ Bandura, A. (1977). Self-efficacy: Toward a unifying theory of behavioral change. *Psychological Review, 84*(2), 191–215.
- ✓ Bandura, A. (1997). *Self-efficacy: The exercise of control.* W. H. Freeman.
- ✓ Breines, J. G., & Chen, S. (2012). Self-compassion increases self-improvement motivation. *Personality and Social Psychology Bulletin, 38*(9), 1133–1143. *(Cited by GPT o3 as "2014, Self Identity" — year and journal are wrong; correct citation above.)*
- ✓ Dai, H., Milkman, K. L., & Riis, J. (2014). The fresh start effect: Temporal landmarks motivate aspirational behavior. *Management Science, 60*(10), 2563–2582.
- ✓ Deci, E. L., Koestner, R., & Ryan, R. M. (1999). A meta-analytic review of experiments examining the effects of extrinsic rewards on intrinsic motivation. *Psychological Bulletin, 125*(6), 627–668.
- ✓ Deci, E. L., & Ryan, R. M. (2000). The "what" and "why" of goal pursuits: Human needs and the self-determination of behavior. *Psychological Inquiry, 11*(4), 227–268.
- ✓ Eyal, N. (2014). *Hooked: How to build habit-forming products.* Portfolio/Penguin.
- ✓ Fogg, B. J. (2009). A behavior model for persuasive design. *Proceedings of the 4th International Conference on Persuasive Technology* (Article 40).
- ✓ Fogg, B. J. (2020). *Tiny Habits: The small changes that change everything.* Houghton Mifflin Harcourt.
- ✓ Gollwitzer, P. M. (1999). Implementation intentions: Strong effects of simple plans. *American Psychologist, 54*(7), 493–503.
- ✓ Gollwitzer, P. M., & Sheeran, P. (2006). Implementation intentions and goal achievement: A meta-analysis of effects and processes. *Advances in Experimental Social Psychology, 38*, 69–119.
- ✓ Harkin, B., Webb, T. L., Chang, B. P. I., Prestwich, A., Conner, M., Kellar, I., Benn, Y., & Sheeran, P. (2016). Does monitoring goal progress promote goal attainment? A meta-analysis of the experimental evidence. *Psychological Bulletin, 142*(2), 198–229.
- ✓ Kahneman, D., & Tversky, A. (1979). Prospect theory: An analysis of decision under risk. *Econometrica, 47*(2), 263–291.
- ✓ Lally, P., van Jaarsveld, C. H. M., Potts, H. W. W., & Wardle, J. (2010). How are habits formed: Modelling habit formation in the real world. *European Journal of Social Psychology, 40*(6), 998–1009.
- ✓ Locke, E. A., & Latham, G. P. (2002). Building a practically useful theory of goal setting and task motivation: A 35-year odyssey. *American Psychologist, 57*(9), 705–717.
- ✓ Locke, E. A., & Latham, G. P. (2006). New directions in goal-setting theory. *Current Directions in Psychological Science, 15*(5), 265–268.
- ✓ Marlatt, G. A., & Gordon, J. R. (Eds.). (1985). *Relapse prevention: Maintenance strategies in the treatment of addictive behaviors.* Guilford Press.
- ✓ Ng, J. Y. Y., Ntoumanis, N., Thøgersen-Ntoumani, C., Deci, E. L., Ryan, R. M., Duda, J. L., & Williams, G. C. (2012). Self-determination theory applied to health contexts: A meta-analysis. *Perspectives on Psychological Science, 7*(4), 325–340.
- ✓ Ryan, R. M., & Deci, E. L. (2000). Self-determination theory and the facilitation of intrinsic motivation, social development, and well-being. *American Psychologist, 55*(1), 68–78.

### Plausible — verify before citing in academic work

- ~ Bélanger-Gravel, A., Godin, G., & Amireault, S. (2013). A meta-analytic review of the effect of implementation intentions on physical activity. *Health Psychology Review, 7*(1), 23–54.
- ~ Buist, I., et al. (2008). Gradual training load and injury risk. *American Journal of Sports Medicine.* *(Training load and injury prevention research is well-established; verify specific paper.)*
- ~ Cugelman, B. (2019). Gamification meta-analysis update. *Persuasive Technology.* *(Cugelman publishes in this area; verify year/venue.)*
- ~ Kaushal, N., & Rhodes, R. E. (2015). Habit formation in physical activity. *Health Psychology Review.* *(Author/topic match; verify specific paper.)*
- ~ Mekler, E. D., Brühlmann, F., Tuch, A. N., & Opwis, K. (2017). Towards understanding the effects of individual gamification elements on intrinsic motivation and performance. *Computers in Human Behavior* / CHI. *(Mekler publishes on gamification; verify specific effect sizes.)*
- ~ Perski, O., Blandford, A., West, R., & Michie, S. (2017). Conceptualising engagement with digital behaviour change interventions: A systematic review. *Translational Behavioral Medicine, 7*(2), 254–267. *(Consistent details across models; plausible.)*
- ~ Schwarzer, R. (2014). Self-efficacy in health behaviour change. *Health Psychology Review.* *(Schwarzer is the authority in this area; verify specific paper.)*
- ~ Sharif, M. A., & Shu, S. B. (2012). The benefits of emergency reserves: Greater preference and persistence for goals that have slack with a cost. *Journal of Marketing Research, 49*(6), 895–909.
- ~ Williams, D. M., & Rhodes, R. E. (2016). The confounded self-efficacy construct. *Health Psychology Review.* *(Author/topic plausible; verify.)*

### Industry data — may be real but proprietary/unverifiable

- App Annie (2021). Mobile app benchmarks. *(Industry report; no academic review process.)*
- Headspace internal A/B test data (2020). Referenced in product talks; not publicly available.
- Localytics (2022). Push notification benchmarks. *(Industry report.)*
- Mixpanel / Prieto (2022–2023). Mobile retention benchmarks. *(Industry report.)*
- WW Digital (2019). Internal engagement analysis. *(Proprietary.)*

### Probable hallucinations — do not cite

- ⚠ Chao (2021). Crowding-out of monetary incentives. *(Unverifiable. Use Deci, Koestner & Ryan 1999 for the underlying phenomenon.)*
- ⚠ Chen (2020). Human coach vs. bot RCT, +29% D30. *(Unverifiable specific paper; finding is plausible.)*
- ⚠ Inkster (2020). Lapse-forgiveness messaging halves churn. *(Unverifiable specific paper.)*
- ⚠ Kim & Benyo (2020). Notification timing, CHI. *(Unverifiable.)*
- ⚠ Locke et al. (1981) meta-analysis, n=110, d≈0.52. *(Locke et al. 1981 is real but a narrative review, not a meta-analysis with these statistics. Likely conflated with Tubbs 1986 or Mento et al. 1987. Use Locke & Latham 2002/2006 instead.)*
- ⚠ Maitland et al. (2020). Tiny Habits RCT, N=676, JMIR. *(Cannot verify this specific paper.)*
- ⚠ Milkman et al. (2021). Streak-based incentives, *Nature Communications.* *(Milkman's major 2021 work is on vaccine nudges, not streaks. Use Sharif & Shu 2012 for the streak/slack finding.)*
- ⚠ Turk & Rudolph (2022). Self-compassion and persistence, d=0.43. *(Unverifiable; Turk = pain psychology. Use Breines & Chen 2012 for self-compassion finding.)*
