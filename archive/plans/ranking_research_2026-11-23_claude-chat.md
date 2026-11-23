<!-- Research report for ranking_values_plan_2026-11-23.md § 4.14, run by Mike in a regular Claude chat from archive/handoffs/2026-11-23-ranking-research-prompt.md. Saved verbatim 2026-11-23; the model used was not stated. -->

# Evidence-based defaults for a regret-of-delay task-ranking model

Research synthesis, November 2026. One section per topic in the order of the brief. Each ends with a default box. A summary table and a list of citation corrections are at the end.

**How to read this document**

- **Evidence tiers.** Each source is tagged **[MA]** meta-analysis or systematic review, **[REP]** a finding replicated across independent studies or a very large field dataset, **[SS]** a single study, **[PP]** a preprint not yet peer reviewed, or **[POP]** a secondary or popular account (interview, press release, book).
- **Verification.** I checked every citation against an abstract, the full text, a publisher or indexing record, or (where marked) a secondary account during this session. A few canonical references I cite from standard knowledge without re-opening them are marked **†**. Page ranges marked † are from memory.
- **Heuristics.** If no study supports a number, the box says **Heuristic**, and the reasoning is given so you can change the assumption rather than the number.
- **One framing point that matters for several topics.** Many of the headline numbers in this literature measure something nearby, not the thing your model needs. The "23 minutes" is time until people return to a task, not time lost. The planning-fallacy "55 vs 34 days" is calendar time, not effort. Regret rankings count how often a domain is named, not how bad a regret is. Each section says what the number actually measures.

---

## 1. The minimum attention cost of a task

### Evidence

**Lab resumption lag (seconds, not minutes).** In the lab, the cost of resuming after an interruption is measured as *resumption lag*, the time from the end of the interruption until the person re-engages with the primary task. Typical values are a few seconds. An Applied Ergonomics meta-analysis of interventions (2021) found that cues and similar interventions cut resumption lag (SMD = −0.51) and raised primary-task accuracy (SMD = 1.03) **[MA]**. This confirms the cost is real and reducible, but its scale does not carry over to a "block" of minutes. The theory behind it is Altmann & Trafton's (2002) memory-for-goals model: a suspended goal decays and has to be retrieved again.

**Field resumption (tens of minutes, but mostly filled with other work).**
- Iqbal & Horvitz (2007) logged 27 Microsoft employees for about two weeks (2,267 hours of activity) **[SS, field]**. People spent nearly 10 minutes on switches and diversions caused by alerts. After answering an email straight away, it took about 16.5 minutes on average to get back to the suspended task (about 11 minutes after instant messages). 27% of alert-driven suspensions led to more than two hours before the user went back.
- Mark, Gonzalez & Harris (2005, CHI) shadowed information workers **[SS, field; checked via a secondary account]**. About 77% of interrupted work was resumed the same day, after an average delay of roughly 25 minutes, with a very large spread (SD near 55 minutes). The widely quoted "23 minutes 15 seconds" is a rounded figure Mark gave in interviews. It comes from this research programme, **not** from Mark, Gudith & Klocke (2008).
- Mark, Gudith & Klocke (2008) is a lab experiment with a different finding: interrupted participants finished faster and at similar quality, but reported more stress, frustration, time pressure and effort **[SS, lab]**. The cost it shows is strain, not minutes.

**Attention residue.** Leroy (2009) found in two experiments that people perform worse on a new task when their attention is still on an unfinished previous one **[SS ×2, lab]**. Finishing the prior task helped, but only if it was finished under time pressure. Leroy & Schmidt (2016) extended this to interruptions. Neither study gives a duration.

**Setup cost of small personal admin tasks.** I found no study that measures this directly.

### From evidence to number

The field figures (10 to 25 minutes) mostly measure *time until return*, and that time is filled with other work. Charging 23 minutes per small task would double-count. Your "attention block" is the overhead of a *planned* switch: finding the materials, signing in, loading context, and the residue afterwards. For a planned switch between two tasks, the lab and residue evidence points to a few minutes. For a task that *breaks into* a focused block, Iqbal & Horvitz's ~10 minutes of diversion plus a slower return is the better reference. So I recommend two values, not one.

Note also that Ibanez et al. (2018) found that grouping similar tasks *assigned from outside* raised productivity, while people grouping tasks themselves did not (topic 6). This supports letting batched admin tasks share a single block.

> **Default: 5 min per task when slotted between tasks; 15 min when it breaks a focus block (range 2–20) · Confidence: low**
> **Basis:** Heuristic, bounded by lab resumption-lag and attention-residue evidence (lower end) and field diversion and return times (upper end). Let similar small tasks in one batch share one block.

---

## 2. The planning fallacy: how late people start and finish

### Evidence

- **Buehler, Griffin & Ross (1994)**, JPSP 67(3), 366–381 **[SS series; the pattern is widely replicated]**. Honours students (n = 37) predicted 33.9 days to finish their theses and took 55.5 days, a **64% overrun**. Their average "worst case" (48.6 days) was still short of the actual time, and only about 30% finished by their own predicted date. Your recollection is correct. Note that this is **calendar completion time**, so it includes late starts, procrastination and competing work, not only effort.
- **Halkjelsvik & Jørgensen (2012)**, Psychological Bulletin 138(2), 238–271 **[MA / integrative review]**. Across psychology and engineering, underestimation was more common than overestimation in engineering and management studies, but not across the psychology literature as a whole. Bias depends on task size and on how the prediction is asked for.
- **Task size.** Roy, Christenfeld & McKenzie (2005), Psychological Bulletin 131(5), 738–756 **[review]**: longer tasks tend to be underestimated and shorter ones overestimated. Roy & Christenfeld (2008), Psychonomic Bulletin & Review 15(1), 202–207 **[SS]**: tasks under about 2 minutes were overestimated and longer ones underestimated, for both remembered and predicted durations. A reanalysis of the tasks in Roy et al. (2005) found underestimation in 55% of short tasks (under an hour) and 85% of long ones. Roy et al. argue the root cause is biased memory of past durations, which matters for correction (below).
- **Work tasks.** Moløkken-Østvold & Jørgensen (2003), review of software estimation surveys **[MA-style review]**: average effort overrun of **30–40%**; 60–80% of projects overrun. (The Standish "89%/189%" figures are methodologically flawed.)
- **Procrastination on top.** Steel (2007), Psychological Bulletin 133(1), 65–94 **[MA, 691 correlations]**: chronic procrastination affects roughly 15–20% of adults (80–95% of students procrastinate to some degree). The strongest predictors are task aversiveness, task delay, low self-efficacy, impulsiveness and low conscientiousness. This explains why calendar overruns (Buehler) exceed effort overruns (software): late starts add delay on top of misjudged effort.
- **Stability per person.** Buehler et al. deliberately studied processes common to most people, not individual differences. Personality predictors are weak (some conscientiousness effects). I found no study that tests whether a person's bias ratio is stable enough to learn from about 10 observations. That makes the per-person correction a statistics question (below).
- **Reference-class forecasting.** Flyvbjerg (2006), Project Management Journal 37(3), 5–15, and Flyvbjerg (2008), European Planning Studies 16(1), 3–21: forecast from the distribution of outcomes in comparable past cases (the "outside view") **[field practice; mixed evaluations]**. Themsen (2019, Financial Accountability & Management) found it did *not* make Danish megaproject estimates more accurate. For a personal assistant, the relevant reference class is the person's own history, which is the correction you already plan. Roy et al.'s finding that people misremember past durations is the reason the system, not the person, should hold that history.

### From evidence to number

One buffer is the wrong shape. The evidence supports a buffer that grows with task size and with whether you are predicting effort or completion date:

| Prediction type | Evidence anchor | Buffer |
|---|---|---|
| Effort, < 15 min | Short tasks overestimated (Roy & Christenfeld) | 0% |
| Effort, 15 min – 4 h | Software effort overrun 30–40% | +35% |
| Calendar completion, multi-day | Buehler thesis study +64% | +65% |
| Calendar completion, one-off, aversive or high-stakes | Procrastination predictors (Steel) | +100% |

**Learning the per-person correction (heuristic statistics).** Model the log of the actual-to-estimated ratio for each task class. Assume a within-person spread of σ ≈ 0.5 on the log scale and a between-person spread of τ ≈ 0.25; both are assumptions to replace with your own data. After 10 observations, the standard error of a person's mean bias is 0.5/√10 ≈ 0.16, which is about ±17% on the multiplier. Shrink towards the population prior with weight n/σ² ÷ (n/σ² + 1/τ²): that is 0.43 at 3 observations, 0.56 at 5, 0.71 at 10 and 0.83 at 20. So 10 observations are enough to move most of the way to the person's own bias, but only if they are pooled across task classes in a hierarchical model. Ten observations split over four classes is too few for each class to stand alone.

> **Default: tiered buffer of 0% (< 15 min effort), 35% (15 min – 4 h), 65% (multi-day completion); single fallback 40% (range 20–100%) · Confidence: medium**
> **Basis:** Buehler 1994 (+64%, calendar), software estimation surveys (+30–40%, effort), short-task overestimation (Roy et al.); per-person shrinkage weight ≈ 0.7 after 10 observations (heuristic σ, τ).

---

## 3. Relationship neglect against financial cost

### Evidence

**Regret.**
- **Gilovich & Medvec (1995)**, Psychological Review 102(2), 379–395, is a theoretical review. The empirical temporal-pattern studies are **Gilovich & Medvec (1994)**, JPSP 67(3), 357–365: actions are regretted more in the short term, inactions more in the long run. In the original study 5 (n = 32), 84% named an inaction as their biggest lifetime regret.
- **Replication: Richardson & Gilovich (2023)**, Royal Society Open Science, n = 2,600 museum visitors **[large replication]**. The interaction held, but the long-term inaction dominance did **not**: 51% named an action and 49% an inaction for "life to this point". For the past few days, 58% named an action. So "neglect regret grows with time" is weaker than the classic account suggests.
- **Roese & Summerville (2005)**, PSPB 31(9), 1273–1285 **[MA of 11 regret-ranking studies]**. The top six regret domains were education (32.2%), career (22.3%), romance (14.8%), parenting (10.2%), self (5.5%) and leisure (2.5%). Finance (2.5%), family (2.3%) and friends (1.5%) were low. Mostly student and convenience samples. These are **frequencies of naming**, not intensity.
- **Morrison & Roese (2011)**, Social Psychological and Personality Science 2(6), 576–583 **[SS, nationally representative, n ≈ 370]**. Romance was the most common regret (18.1%), followed by education (13.1%), career (12.2%), finance (9.9%) and parenting (9%). Inaction regrets lasted longer than action regrets.

**Relationships and long-term outcomes.**
- **Holt-Lunstad, Smith & Layton (2010)**, PLoS Medicine 7(7), e1000316 **[MA, 148 studies, 308,849 participants]**: stronger social relationships were associated with a 50% higher likelihood of survival (OR = 1.50, 95% CI 1.42–1.59), comparable to established risk factors such as smoking. This is the strongest single anchor in this section.
- **Harvard Study of Adult Development** (724 men recruited from 1938, plus descendants) **[long cohort; checked via the study director's published summaries, not a primary paper]**: relationship satisfaction at age 50 predicted health at 80 better than cholesterol did (Waldinger & Schulz, *The Good Life*, 2023 †; Harvard Gazette 2017 and 2023).

**Money value of social contact.**
- **Powdthavee (2008)**, Journal of Socio-Economics 37(4), 1459–1480 (journal since renamed Journal of Behavioral and Experimental Economics) **[SS, British Household Panel Survey]**: increasing how often one sees friends and relatives was worth up to about £85,000 a year in life-satisfaction terms; talking to neighbours on most days, about £37,000. Caveat: life-satisfaction "shadow prices" are inflated because income has a small estimated effect on life satisfaction. Treat this as evidence of *order of magnitude* (social contact is large next to modest money), not as an exchange rate.

**How closeness decays without contact.**
- **Roberts & Dunbar (2011)**, "The costs of family and friends: an 18-month longitudinal study of relationship maintenance and decay", Evolution and Human Behavior 32(3), 186–197 **[SS, n = 25 school leavers]**: the emotional intensity of *friendships* was more sensitive to reduced contact and fewer shared activities than that of *kin* relationships. Friendships cost much more to maintain.
- **Roberts & Dunbar (2015)**, Human Nature 26(4), 426–450 **[SS]**: more effort slowed friendship decline. More talking prevented decline most for women, more shared activities for men.
- **Hall (2019; online 2018)**, Journal of Social and Personal Relationships 36(4), 1278–1296 † pages **[SS ×2]**: about 50 hours together to go from acquaintance to casual friend, about 90 to friend, and over 200 to close friend. This shows the stock that neglect wears down is costly to rebuild.

**Contact frequency by layer (Dunbar).** Dunbar's layers of roughly 5, 15, 50 and 150 people (Dunbar 2018, Trends in Cognitive Sciences 22(1), 32–51) correspond to typical contact of **at least weekly** (5), **at least monthly** (15), **about every six months** (50) and **at least yearly** (150) **[REP across phone-log and survey data; layer frequencies checked via secondary summaries]**. The 15 closest people take about 60% of social effort. These figures are *descriptive* (what people do), not *normative* (what people wish).

### From evidence to number

(a) **Weight.** No study gives a ratio between a "severe" relationship cost and a "severe" financial cost. Three lines of evidence point the same way: health effects on the scale of smoking, life-satisfaction values far above income changes, and relationship domains that rank at or above finance in representative regret data. So at an equal severity grade, relationship harm should weigh at least as much as financial harm. Pushing much past 2:1 would let a single missed call outrank, for example, a severe financial event, which itself damages wellbeing. **Heuristic: 1.5 : 1.**

(b) **Curve.** Closeness decays with lack of contact, faster for friends than for kin, and the cost of letting it go is asymmetric (about 200 hours to rebuild a close friendship). A plausible shape is: no cost until the person's wished cadence has passed, then a convex rise with an "overdue ratio" *r* = days since contact ÷ cadence. Cost ∝ (r − 1)^1.5 for friends and (r − 1)^1.0 for kin, capped at the relationship's severity grade. The exponents are heuristics; there are no decay-curve fits in the literature to support specific exponents.

> **Default: relationship-to-financial weight 1.5 : 1 at equal grade (range 1 : 1 – 3 : 1); cost of being out of touch = 0 until the cadence is passed, then ∝ (r − 1)^1.5 for friends, (r − 1)^1.0 for kin, capped at grade · Confidence: low**
> **Basis:** Holt-Lunstad 2010 (OR 1.50), Powdthavee 2008 (order of magnitude), Morrison & Roese 2011 (regret frequency); decay asymmetry from Roberts & Dunbar 2011. Exponents are heuristic.

**Default wished-contact cadence** (suggest these when someone has not set one; descriptive Dunbar-layer norms, rounded):

| Closeness level | Cadence default | Range |
|---|---|---|
| Intimate family / partner-level (inner ~5) | 7 days | 2–10 days |
| Close friends (~15) | 30 days | 14–45 days |
| Wider friends (~50) | 120 days | 60–180 days |
| Wider network (~150) | 365 days | 180–365 days |

---

## 4. The cost of intruding on protected time

### Evidence

**Sleep.**
- **Van Dongen, Maislin, Mullington & Dinges (2003)**, Sleep 26(2), 117–126 **[SS, lab, n = 48, highly cited and consistent with later work]**. Restricting sleep to 4 or 6 hours a night for 14 days caused cumulative, dose-dependent cognitive deficits. Six hours or less a night produced deficits equivalent to up to two nights of total sleep deprivation, while subjective sleepiness barely rose. People did not notice they were getting worse.
- **Recovery.** Belenky et al. (2003), Journal of Sleep Research 12(1), 1–12: some aspects of performance did not return to baseline after three nights of 8-hour recovery sleep. Banks et al. (2010), Sleep 33(8), 1013–1026: after five nights of 4 hours, one night of up to 10 hours in bed left some deficits. Yamazaki et al. (2021) †: residual deficits remained after four recovery nights **[REP, lab]**.

**Recovery from work in leisure (Sonnentag's programme).**
- **Bennett, Bakker & Field (2018)**, Journal of Organizational Behavior 39(3), 262–275 **[MA, 54 samples, N = 26,592]**: of four recovery experiences, psychological detachment after work had the strongest negative relationship with fatigue.
- **Wendsche & Lohmann-Haislah (2017)**, Frontiers in Psychology 7, 2072 **[MA, 91 samples, N = 38,124]**: doing work-related activities in non-work time had a medium-sized negative relationship with detachment.
- **de Bloom et al. (2009)**, Journal of Occupational Health 51(1), 13–25 **[MA, 7 studies]**: vacations improve health and wellbeing (d = 0.43), but the gains fade soon after returning to work (d = −0.38). An updated meta-analysis (European Psychologist 28(4), 2023, 13 studies) found d = 0.25. Recovery gains decay in days to weeks.

**Evening work and work–family conflict.**
- **Lanaj, Johnson & Barnes (2014)**, OBHDP 124(1), 11–23 **[SS ×2, experience sampling, 82 managers + 161 employees]**: using a smartphone for work at night cut sleep, which raised depletion the next morning and lowered engagement at work that day.
- **Amstad, Meier, Fasel, Elfering & Semmer (2011)**, Journal of Occupational Health Psychology 16(2), 151–169 † pages **[MA, 427 effect sizes]**: work interfering with family, and family with work, were both related to work, family and general outcomes, most strongly in the same domain. Time spent at work moderated the link between work-to-family conflict and family outcomes.

**Exercise.** Lally et al. (2010) (topic 5) found that missing a single opportunity did not materially affect habit formation. A single missed session is cheap; repeated misses are what break routines.

### From evidence to number

(a) **Base ratios (heuristic).** Sleep ranks highest: deficits accumulate, the person does not notice them, recovery takes several nights, and next-day function degrades across the board. Family and partner time is next, because it combines relationship cost (topic 3) with work–family conflict. Personal rest is protected by the detachment literature, but each instance matters less. One missed exercise session is low-cost. Solo meals are lowest; a *shared family meal* should be scored as family time.

(b) **Shape.** For sleep, Van Dongen's deficits rise roughly in proportion to accumulated excess wakefulness, which argues for close to linear (exponent ≈ 1–1.25), not squared. For family and rest, no study measures an exponent; convexity is plausible (each intrusion shrinks the remaining recovery opportunity), but exponent 2 is steep: the fourth intrusion would cost 16 times the first, against 8 times at exponent 1.5.

(c) **Recovery.** A hard 7-day reset fits poorly with multi-night sleep recovery and vacation fade-out. An exponentially decaying intrusion count behaves better: with a 3.5-day half-life, an intrusion keeps 25% of its weight after 7 days and about 14% after 10.

> **Default: base ratios sleep 3.0 : family/partner 2.5 : rest 1.5 : exercise 1.0 : solo meals 0.75; k-th intrusion in the week costs base × k^1.5 (sleep k^1.0–1.25; range 1.0–2.0); intrusion count decays with half-life 3.5 days (range 2–7) instead of a 7-day reset · Confidence: low (ratios, exponent); medium (sleep needs multi-night recovery)**
> **Basis:** Van Dongen 2003 and recovery studies for sleep; Bennett 2018 and Wendsche 2017 for detachment; de Bloom 2009 for fade-out; ratios and exponents are heuristic.

---

## 5. Ordering a reward after an effortful task

### Evidence

- **Temptation bundling. Milkman, Minson & Volpp (2014)**, Management Science 60(2), 283–299 **[SS RCT, N = 226]**: participants who could listen to tempting audiobooks *only at the gym* visited 51% more often at first than controls; those merely encouraged to keep them for the gym visited 29% more often. The effects faded over time, especially after Thanksgiving.
- **Kirgios, Mandel, Park, Milkman, Gromet, Kay & Duckworth (2020)**, OBHDP 161, 20–35 **[large RCT, N = 6,792]**: giving people an audiobook and encouraging temptation bundling raised the chance of a weekly workout by 10–14%, lasting up to 17 weeks after the programme. Compared with giving the audiobook alone, *teaching* the bundling idea added only a modest benefit.
- **Important distinction.** Temptation bundling is *concurrent* pairing (enjoying the want only *during* the should). Your design is *sequential*, with the treat *after* the effort. That is closer to the **Premack principle** (Premack 1959, Psychological Review 66(4), 219–233 †): access to a more-preferred activity reinforces a less-preferred one that comes before it. Most Premack evidence is from animal work and applied behaviour analysis with children, not adult self-management field trials.
- **Immediate rewards. Woolley & Fishbach (2016)**, Journal of Consumer Research 42(6), 952–966, and **(2017)**, PSPB 43(2), 151–162 **[SS series]**: immediate rewards (enjoyment during or right after) predicted persistence at long-term goals better than delayed ones, partly by raising intrinsic motivation.
- **Order in routines. Judah, Gardner & Aunger (2013)**, British Journal of Health Psychology 18(2), 338–353 **[SS, N = 50, exploratory]**: people told to floss *after* brushing formed stronger flossing habits than those told to floss before, and flossed more often at 8 months. Placing the new behaviour right after an established one helps.
- **Habit formation. Lally, van Jaarsveld, Potts & Wardle (2010)**, European Journal of Social Psychology 40(6) †, 998–1009 **[SS, N = 96]**: median 66 days to plateau of automaticity (range 18–254); missing one opportunity did not materially affect habit formation. Wood & Rünger (2016), Annual Review of Psychology 67, 289–314 †: habits form through context-cued repetition; rewards help early, then the cue takes over.
- **Overjustification. Deci, Koestner & Ryan (1999)**, Psychological Bulletin 125(6), 627–668 **[MA, 128 studies]**: *expected*, tangible rewards contingent on engagement, completion or performance reduced free-choice intrinsic motivation (d = −0.40, −0.36, −0.28). Unexpected rewards did not; positive feedback *raised* it (d ≈ 0.33). Cameron & Pierce (1994) dispute the size of the effect. Undermining matters for activities that are *already* intrinsically interesting, and the effortful task here usually is not.

### From evidence to number

Pairing an enjoyable activity with an effortful one has good field support (two RCTs, one large). The *sequential* "treat after" version is supported by theory (Premack, immediate rewards) and by order effects in habit formation, but has weaker direct evidence in adults. Kirgios et al. suggest that explicit framing adds little over just arranging the pairing, so not calling it a reward should not cost much effectiveness. It also keeps the overjustification risk low, because a reward that isn't expected or controlling isn't one the meta-analysis found harmful. Once the person spots the pattern it becomes expected, but it is self-chosen and not controlling, which is the case with the least undermining. For timing, reinforcement depends on closeness in time, so the treat should follow directly.

> **Default: yes, place the liked item directly after the effortful one; gap ≤ 15 min (range 0–60); works unframed; where possible offer the liked item *during* the effort too (concurrent bundling has the stronger evidence) · Confidence: medium (pairing helps); low (sequential "after" specifically)**
> **Basis:** Milkman 2014 and Kirgios 2020 RCTs; Woolley & Fishbach on immediate rewards; Judah 2013 on order; Deci 1999 on low undermining risk for unexpected, non-controlling rewards.

---

## 6. When someone is behind: easy wins first or hardest first?

### Evidence

- **KC, Staats, Kouchaki & Gino (2020)**, "Task selection and workload: A focus on completing easy tasks hurts performance", Management Science 66(10), 4397–4416 **[SS, six years of emergency department data + lab]**: under higher workload, physicians chose easier tasks ("task completion preference"). This raised short-term throughput but hurt longer-term productivity. The lab study traced the choice to fatigue and the sense of progress from finishing. (Earlier working paper title: "... Hurts Long-Term Performance".)
- **Ibanez, Clark, Huckman & Staats (2018)**, Management Science 64(9), 4389–4407 **[SS, 2.4 million radiology reads]**: doctors who departed from first-in-first-out to do the shortest tasks first lost productivity; shortest-first was especially harmful.
- **Amabile & Kramer (2011)**, *The Progress Principle* (Harvard Business Review Press) **[SS, about 12,000 daily diaries from 238 people in 7 companies; correlational]**: making progress on *meaningful* work was the strongest contributor to a good working day; setbacks marked the worst days. Small wins worked nearly as well as big ones.
- **Gal & McShane (2012)**, Journal of Marketing Research 49(4), 487–501 **[SS, observational, about 6,000 debt-settlement clients]**: closing individual small accounts predicted paying off all debt, independent of dollars repaid. On the other side, Amar, Ariely, Ayal, Cryder & Rick (2011), JMR 48 (special issue) † found people pay off small debts first even when it costs them more.
- **Kivetz, Urminsky & Zheng (2006)**, JMR 43(1), 39–58 **[SS, field experiments]**: effort speeds up as people approach a goal, and even illusory early progress (a 12-stamp card with two free stamps) speeds completion.
- **Avoidance.** Steel (2007): task aversiveness is one of the strongest predictors of procrastination.

### From evidence to number

The evidence fits your rule if easy-first is a **bounded on-ramp**, not a mode. Quick wins help a stalled person get going (progress, goal gradient, debt snowball), but as a standing policy under load they cost long-run output (KC et al., Ibanez et al.). The best quick win is a small first step *of the hard task itself*. That gives progress on meaningful work (Amabile) without crowding the hard task out.

> **Default: "behind" = 3 or more overdue items, or the top-ranked task skipped on 2 of the last 3 days (heuristic); then 1–2 quick wins (max 3, ≤ 20 min total), the first ideally a ≤ 10-min first step of the hard task, then the hard task · Confidence: low (thresholds); medium (easy-first as a standing policy hurts)**
> **Basis:** KC et al. 2020 and Ibanez et al. 2018 (cost of easy-first); Amabile & Kramer, Gal & McShane, Kivetz et al. (motivational benefit of early progress). Thresholds are heuristic.

---

## 7. How much asking is too much

### Evidence

- **Horvitz and colleagues.** Horvitz, Jacobs & Hovel (1999), "Attention-sensitive alerting", UAI; Horvitz, Kadie, Paek & Hovel (2003), Communications of the ACM 46(3), 52–59; Horvitz & Apacible (2003), ICMI **[framework + models]**. The principle is decision-theoretic: interrupt only when the expected cost of *delaying* the information exceeds the expected cost of *interrupting* now, with the interruption cost inferred from context. This is the same regret-of-delay logic as your ranking model, so the system can rank its own questions as tasks. It gives no fixed caps.
- **Batching.** Fitz, Kushlev, Jagannathan, Lewis, Paliwal & Ariely (2019), Computers in Human Behavior 101, 84–94 **[SS RCT, n = 237]**: getting notifications in batches three times a day made people feel more attentive, productive, in better mood and in more control of their phones than normal delivery.
- **Experience-sampling burden.** Wrzus & Neubauer (2023), Assessment 30(3), 825–846 **[MA, 477 articles, N = 677,536]**: the number of prompts per day did *not* predict compliance or dropout. Eisele et al. (2022), Assessment **[SS, n = 163]**: longer questionnaires (60 vs 30 items) increased burden; 3, 6 or 9 prompts a day did not show clear harm. A reanalysis (Ulitzsch et al., 2025, Psychological Assessment 37(8), 347–359) found *more frequent* prompting increased careless responding. In short: length hurts more than frequency, but frequency erodes answer quality.
- **Repeated reminders. Ancker et al. (2017)**, BMC Medical Informatics and Decision Making 17, 36 **[SS, 112 clinicians, 3.5 years of records]**: acceptance of a reminder fell 30% for each extra reminder in the same encounter, and 10% for each 5-point rise in the share of repeated reminders. Repeats for the same case were the main driver; total workload was not.
- **Novelty decay. Klasnja et al. (2019)**, HeartSteps micro-randomised trial, Annals of Behavioral Medicine 53(6), 573–582 **[SS MRT, 6 weeks]**: a walking suggestion raised step count over the next 30 minutes by 24% on average, but by 107% at the start of the study, declining over time.

### From evidence to number

The evidence does not support a hard daily cap from burden alone (ESM compliance is robust to frequency), but it does support three things: keep each ask *short*, *batch* asks into a few predictable slots, and **never repeat the same nudge without new information**, because repeats are where acceptance collapses. Your current rules (one question per mention, a slipping task at most once a day, a five-minute weekly review) are consistent with this. The main change is to stop daily re-raises of the *same* item after the second time.

> **Default: ≤ 1 clarifying question per task mention; ≤ 3 system-initiated prompts per day, delivered in ≤ 3 batches at natural breakpoints; a slipping task raised at most once a day and at most twice in total without new information, then moved to the weekly review as "keep, reschedule or drop?"; weekly review ≤ 5 min · Confidence: medium (repeats are the main harm); low (exact daily caps)**
> **Basis:** Ancker 2017 (−30% per extra reminder), Klasnja 2019 (effects decay), Fitz 2019 (3 batches a day), Wrzus & Neubauer 2023 (frequency alone not decisive), Horvitz (expected-cost framing).

---

## 8. When a forgotten task is effectively abandoned

### Evidence

- **Zeigarnik (1927)**, Psychologische Forschung 9, 1–85 †. **Ghibellini & Meier (2025)**, "Interruption, recall and resumption: a meta-analysis of the Zeigarnik and Ovsiankina effects", Humanities and Social Sciences Communications 12, 962 **[MA, 59 publications]**: interrupted tasks show **no** reliable memory advantage (recall ratio of interrupted to finished ≈ 0.99). The *Ovsiankina* effect, the tendency to resume interrupted tasks, does hold: about 67% of interrupted tasks were resumed, against 50% by chance. The authors warn that the resumption figures come from small, varied studies.
- **Masicampo & Baumeister (2011)**, JPSP 101(4), 667–683 **[SS series]**: unfinished goals caused intrusive thoughts and interference, and making a specific plan for them removed these effects, even without carrying the plan out. Implication: the cost of an open low-stakes task is mostly mental clutter, and capturing it with a plan, or parking it explicitly, removes most of that cost.
- **To-do app data. Halder, Zimmermann, Körte, Mehlig, Schmiedmayer & Grüning (2026)**, "How do people plan digitally: An in-the-wild investigation of task planning through a smartphone app", arXiv 2609.15904 **[PP, 957 users, 24,265 tasks, 6 weeks, Structured planner app]**: 49.5% of tasks were completed, 32.0% abandoned (neither completed nor carried forward) and 18.5% still open. Completed tasks were done a median of 0.5 days after creation. By day 10, cumulative completion was 55.8% and abandonment 42.4%, and abandonment barely rose after day 10. The authors note abandonment may be overstated because some done tasks were never ticked.
- **Iqbal & Horvitz (2007)** (topic 1): 27% of alert-suspended tasks waited over two hours, and some were never resumed in the window.
- **The often-quoted "41% of to-do items are never completed"** is attributed to iDoneThis company data. I could not find a primary source, and the Zapier article usually cited for it contains no such data. Treat it as unverifiable.

### From evidence to number

The best behavioural data (one app, a preprint) says tasks get done fast or not at all, and that the fate of most tasks is settled within about 10 days. For tasks that are low-stakes, never mentioned and never rising, 30 days is longer than the data suggest is needed. Masicampo & Baumeister suggest the archive step should *park the task with an explicit "not now"*, not delete it silently, so it neither nags nor is lost.

> **Default: offer the task in the weekly review at ~14 days ("keep or drop?"); auto-archive at 21 days if there is no reply (range 14–30); archive as "parked" and retrievable, not deleted · Confidence: low–medium**
> **Basis:** Halder et al. 2026 (abandonment flat after day 10; median completion 0.5 days); Ghibellini & Meier 2025 (open tasks are not reliably better remembered); Masicampo & Baumeister 2011 (parking with a plan removes intrusion).

---

## 9. Casual promises with no date

### Evidence

The evidence here is **thin**, and no study measures when an undated casual promise starts to cost trust.

- **Gneezy & Epley (2014)**, "Worth keeping but not exceeding: Asymmetric consequences of breaking versus exceeding promises", Social Psychological and Personality Science 5(7) † pages **[SS ×3, imagined, recalled and real promises]**: breaking a promise lowered how people felt about the promiser, while exceeding it added almost nothing. There is no reward for being early, only a cost for failing.
- **Flynn (2003)**, "What have you done for me lately? Temporal adjustments to favor evaluations", OBHDP 91(1), 38–50 **[SS ×2, lab + field]**: recipients valued a favour most right after it was done, and less over time, while givers valued it more over time. A late fulfilment is worth less to the recipient than a prompt one.
- **Response-time norms. Kooti, Aiello, Grbovic, Lerman & Mantrach (2015)**, WWW 2015 **[large log study, 2 million users, 16 billion emails]**: the most likely reply time was two minutes, half of replies came within 47 minutes, and about 90% within a day; younger users replied faster. These norms concern replies, not promised favours, but they set expectations for anything digital and quick.

### From evidence to number

"I'll send you the photos" is a digital, low-effort promise in a culture where most replies come within a day. Recipients' valuation decays over time (Flynn), and early delivery earns nothing extra (Gneezy & Epley). A 7-day grace period fits effortful or physical favours better than quick digital ones. Recommend splitting by effort.

> **Default: 3 days for quick digital promises (photos, links, intros); 7 days for effortful or physical ones (range 1–10); cost then rises with delay · Confidence: low (heuristic; evidence thin)**
> **Basis:** Gneezy & Epley 2014 (only breaking costs), Flynn 2003 (recipient value decays), Kooti 2015 (most replies within a day); no direct study of undated promises.

---

## 10. Combining several harms into one importance score

### Evidence

- **Risk-matrix critique. Cox (2008)**, "What's wrong with risk matrices?", Risk Analysis 28(2), 497–512 **[analytical]**: ordinal severity ratings have poor resolution, can give identical ratings to very different risks ("range compression"), and can rank smaller risks above larger ones. Arithmetic on ordinal labels needs explicit, cardinal scaling, which your geometric ladder provides.
- **Multi-attribute utility.** Keeney & Raiffa (1976), *Decisions with Multiple Objectives* (Wiley) †: combining attributes needs a cardinal scale for each and a combination rule. The multiplicative form is the standard alternative when attributes are not simply additive.
- **Combining harms that occur together (comorbidity).** The Global Burden of Disease combines disability weights multiplicatively: combined = 1 − ∏(1 − DWᵢ). **Flanagan et al. (2006)**, Population Health Metrics 4, 13 **[SS, Canadian health survey]** tested this against people with two or three conditions; best fit was essentially the plain multiplicative model (s = 0.99). This is the closest empirical test of "worst harm sets the floor, extra harms add less and less, total is bounded" that I found.
- **Cumulative stress. Evans, Li & Whipple (2013)**, Psychological Bulletin 139(6), 1342–1396 **[review/MA]**: exposure to several risk factors does more harm than any single one. Most work uses a simple count of risks, a cruder form of compounding.
- **Diminishing sensitivity to losses.** Tversky & Kahneman (1992), Journal of Risk and Uncertainty 5, 297–323 †: the value function for losses is concave (α ≈ 0.88), so felt harm grows less than proportionally with objective harm. This supports a bounded, less-than-additive combination.
- **Harm to others. Jones & Rachlin (2006)**, "Social discounting", Psychological Science **[SS]**: what a person would give up to benefit someone else falls off hyperbolically with social distance; Rachlin & Jones (2008) found relatives are valued above non-relatives at the same distance. No study I found measures weight for *organisations*.

### From evidence to number

**Ladder.** Your geometric ladder with ratio 3 (10 / 30 / 90 on a 100 scale) is defensible: it turns ordinal labels into a ratio scale, as Cox asks, and a ratio near 3 is a reasonable heuristic step between grades. Keep it unless your own data say otherwise.

**Compounding.** I recommend replacing the "+25% of each further harm, capped" rule with the tested multiplicative rule: treat each harm as a share of the maximum (minor 0.1, major 0.3, severe 0.9), then score = 100 × [1 − ∏(1 − sᵢ)]. Worked values: major + major = 51; major + minor = 37; three majors = 65.7; severe + major = 93; severe + severe = 99; minor + minor = 19. Properties: the worst harm sets the floor, each extra harm adds less, the cap at 100 is built in, minors compound slightly instead of not at all, and it takes about seven majors to reach "severe". Your current rule gives major + major = 37.5, which undervalues two independent major harms compared with the comorbidity evidence.

**Organisational weight.** 0.5 is a reasonable *heuristic* for an employer, as long as harms that rebound on the person (reputation, job, legal exposure) are recorded as separate personal harms, not baked into the organisational weight. One important exception: for a sole founder or owner, harm to the business is largely personal financial harm, and should weigh close to 1.0.

> **Default: ladder ratio 3 (10 / 30 / 90; range 3–10); combine with score = 100 × [1 − ∏(1 − sᵢ)] using s = 0.1 / 0.3 / 0.9; organisational harm weight 0.5 (range 0.3–0.7), close to 1.0 where the person owns the organisation, with rebound harms scored separately as personal · Confidence: medium (multiplicative compounding); low (ladder ratio, organisational weight)**
> **Basis:** Cox 2008 (ordinal labels need cardinal scaling); GBD multiplicative model validated by Flanagan et al. 2006; Tversky & Kahneman 1992 (diminishing sensitivity); Jones & Rachlin 2006 (social discounting). Organisational weight is heuristic.

---

## Summary table

| # | Topic | Your placeholder | Recommended default | Confidence |
|---|---|---|---|---|
| 1 | Minimum attention cost | 5–15 min | 5 min between tasks; 15 min if it breaks a focus block | Low |
| 2 | Planning-fallacy buffer | 30% | Tiered: 0% (< 15 min), 35% (15 min – 4 h), 65% (multi-day); fallback 40%; shrinkage weight ≈ 0.7 after 10 obs | Medium |
| 3a | Relationship vs financial weight | n/a | 1.5 : 1 at equal grade | Low |
| 3b | Out-of-touch cost curve | n/a | 0 until cadence passed, then ∝ (r − 1)^1.5 friends, ^1.0 kin, capped | Low |
| 3c | Wished cadence | n/a | 7 / 30 / 120 / 365 days by layer | Medium-low |
| 4a | Protected-time base ratios | n/a | Sleep 3.0, family 2.5, rest 1.5, exercise 1.0, solo meals 0.75 | Low |
| 4b | Repeated-intrusion shape | Convex, exponent 2 | Exponent 1.5 (sleep 1.0–1.25) | Low |
| 4c | Recovery | 7 days | Exponential decay, half-life 3.5 days | Low-medium |
| 5 | Reward after effort | n/a | Yes; ≤ 15 min gap; unframed is fine; prefer concurrent pairing when possible | Medium / low |
| 6 | Behind threshold; quick wins | Behind → easy wins | ≥ 3 overdue or top task skipped 2 of 3 days; 1–2 wins ≤ 20 min, then the hard task | Low |
| 7 | Prompt limits | 1 question; 1 raise/day; 5-min weekly | Same, plus ≤ 3 prompts/day in ≤ 3 batches; max 2 raises per item without new info | Medium / low |
| 8 | Archive forgotten task | 30 days | Review at 14 days, archive at 21; park, don't delete | Low-medium |
| 9 | Casual promise grace | 7 days | 3 days digital/quick; 7 days effortful/physical | Low |
| 10 | Ladder and compounding | 10/30/90 + 25% per extra, capped; org 0.5 | Keep 10/30/90; multiplicative 1 − ∏(1 − s); org 0.5 (≈ 1.0 if owner) | Medium / low |

---

## Citations in the brief that were wrong, incomplete or unverifiable

1. **Mark, Gudith & Klocke (2008), "~23 minutes to resume".** *Misattributed.* The 2008 CHI paper ("The cost of interrupted work: More speed and stress", pp. 107–110) is a lab experiment: interrupted people finished *faster* with similar quality but more stress. The 23-minute figure comes from Mark, Gonzalez & Harris (2005), "No task left behind? Examining the nature of fragmented work" (CHI 2005), and Mark's interviews. There, interrupted work resumed the same day was picked up after about 25 minutes on average, with very wide spread. It measures time until return, not time lost.
2. **Gilovich & Medvec (1995).** *Correct citation, wrong study for the data.* The 1995 Psychological Review paper is the review. The temporal-pattern data are Gilovich & Medvec (1994), JPSP 67(3), 357–365. The long-term inaction effect **did not replicate** in Richardson & Gilovich (2023), Royal Society Open Science (n = 2,600).
3. **Roese & Summerville (2005).** *Correct* (PSPB 31(9), 1273–1285). Note the finding: the top regrets are education, career and romance; finance, family and friends ranked low in that meta-analysis. In the representative sample (Morrison & Roese 2011), romance was top.
4. **Roberts & Dunbar (2011).** *Ambiguous.* There are two 2011 papers. The one on decay without contact is "The costs of family and friends: an 18-month longitudinal study of relationship maintenance and decay", Evolution and Human Behavior 32(3), 186–197 (n = 25). The other, "Communication in social networks: Effects of kinship, network size, and emotional closeness" (Personal Relationships 18(3), 439–452 †), is cross-sectional. I did not open it this session.
5. **"KC, Staats et al."** *Incomplete.* KC, Staats, Kouchaki & Gino (2020), Management Science 66(10), 4397–4416. One co-author (Gino) was found by Harvard to have committed misconduct in *other* papers; I found no sign that this paper is affected, but I did not check specifically. Ibanez et al. (2018) shows the same result independently.
6. **Powdthavee (2008).** *Correct* (Journal of Socio-Economics 37(4), 1459–1480; journal since renamed Journal of Behavioral and Experimental Economics). The headline is "up to £85,000 a year" for more frequent contact with friends and relatives.
7. **Leroy (2009).** *Correct* (OBHDP 109(2), 168–181). No duration estimate; it shows a performance effect.
8. **Buehler, Griffin & Ross (1994).** *Correct* (JPSP 67(3), 366–381): 33.9 days predicted vs 55.5 actual. This is calendar time.
9. **Van Dongen et al. (2003).** *Correct* (Sleep 26(2), 117–126).
10. **Milkman, Minson & Volpp (2014).** *Correct* (Management Science 60(2), 283–299). Note that it tests concurrent bundling, not a reward afterwards.
11. **Lally et al. (2010).** *Correct* (EJSP 40, 998–1009): median 66 days, range 18–254.
12. **Masicampo & Baumeister (2011).** *Correct* (JPSP 101(4), 667–683).
13. **Zeigarnik.** *Original is 1927; the effect is not reliable.* Ghibellini & Meier's (2025) meta-analysis finds no memory advantage for unfinished tasks; the resumption (Ovsiankina) effect holds.
14. **"Sonnentag".** *Too general to verify.* The usual anchor is Sonnentag & Fritz (2007), Journal of Occupational Health Psychology 12(3), 204–221 † (Recovery Experience Questionnaire), which I did not open. I used Bennett, Bakker & Field (2018) and Wendsche & Lohmann-Haislah (2017), both verified.
15. **"Horvitz and colleagues".** *Verified:* Horvitz, Jacobs & Hovel (1999), UAI; Horvitz, Kadie, Paek & Hovel (2003), CACM 46(3), 52–59; Iqbal & Horvitz (2007), CHI, 677–686.
16. **Harvard Study of Adult Development.** *Verified only through the director's summaries* (book and Harvard Gazette), not a primary paper. The "satisfaction at 50 predicts health at 80" claim should be cited to a primary paper before use in anything published.
17. **Dunbar's layers and contact frequencies.** Layer sizes are verified (Dunbar 2018, TICS 22(1), 32–51); the per-layer contact frequencies I checked only through secondary summaries of Dunbar's work.
18. **"41% of to-do items are never completed" (iDoneThis).** Not in your brief but widely quoted on this topic: *unverifiable*. Use Halder et al. (2026) instead, which is a preprint.
19. **Amabile & Kramer, Wood, Premack, overjustification.** No errors. Premack (1959) and Wood & Rünger (2016) are standard references cited from knowledge (†), not re-opened.
