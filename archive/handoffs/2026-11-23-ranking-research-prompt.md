Model: Opus 5.5 with web search on (Research mode if available) — a literature synthesis where checking each citation against its source is the work.

# Research brief: evidence-based defaults for a personal task-ranking model

I'm designing the ranking logic for a personal assistant that decides which of a person's tasks
to put first each day. It ranks by **the regret of delay**: for each task, what one more day of not
doing it would cost, against what else that time could be used for. Every number below is
currently a placeholder. I need a research-grounded **starting default** for each, which the
system will then adjust per person from their own evidence.

For each topic below, please:

1. Find the strongest evidence: meta-analyses and well-replicated studies first, then
   single studies. Say which is which.
2. **Recommend a default value, with a plausible range**, in the units I give, and explain how you
   got from the evidence to the number. If the literature can't support a number, say so plainly
   and give the most defensible heuristic instead, labelled as a heuristic.
3. Give full citations (authors, year, title, venue) with the specific finding and effect size.
   **Verify every citation against the source.** Several below are recalled from memory and may be
   wrong in detail. Correct anything I've misremembered.
4. Rate your confidence (high / medium / low) and name the main caveats: populations studied, lab
   vs field, replication status.

## Topics

### 1. The minimum attention cost of a task
Every discrete task should cost at least one "attention block", meaning the overhead of switching
to it, setting up, and re-engaging afterwards, however short the task itself is. **Default wanted:
minutes per task (my prior: 5–15).** Look at task-switching costs beyond the millisecond lab
paradigm: resumption lag after interruption, "attention residue" (Leroy 2009?), the cost of
interruptions at work (Mark, Gudith & Klocke 2008, often quoted as ~23 minutes to resume?), and
setup costs for small personal admin tasks.

### 2. The planning fallacy: how late people start and finish
The system assumes people start late and underestimate, then corrects per person. **Default
wanted: a buffer as a percentage added to estimated time (my guess was 30%; I suspect the
literature says more).** Cover Buehler, Griffin & Ross 1994 (theses ~55 days actual vs ~34
predicted?). Then: how the bias varies by task type (personal vs work, short vs long, one-off vs
recurring), how much procrastination adds on top of underestimation, whether people's bias is
stable enough per person to learn from about 10 observations, and reference-class forecasting as
a correction.

### 3. Relationship neglect against financial cost
The model has to weigh, for example, not calling a parent against a small late-payment fee.
**Defaults wanted: (a) a relative weight for a "severe" relationship cost against a "severe"
financial cost; (b) whether, and how fast, the cost of not being in touch grows over time, ideally
as a curve shape (linear, convex, its exponent).** Cover:
- regret research: action vs inaction regret over time (Gilovich & Medvec 1995?), what people
  regret most (Roese & Summerville 2005?);
- relationships and long-term wellbeing (the Harvard Study of Adult Development);
- wellbeing-valuation estimates of social contact in money terms (e.g. Powdthavee 2008, "Putting
  a price tag on friends, relatives, and neighbours"?);
- how emotional closeness decays without contact (e.g. Roberts & Dunbar 2011?) and typical
  contact frequencies by closeness layer (Dunbar's layers).

Also give a **default "wished contact cadence"** per closeness level (intimate family, close
friends, wider friends) for the system to suggest when someone hasn't said one.

### 4. The cost of intruding on protected time
Family time, sleep, rest, meals and exercise are protected. A task may intrude only if its cost
of delay exceeds an intrusion cost that **rises with each intrusion in the same week**.
**Defaults wanted: (a) the relative base cost of intruding on sleep, family/partner time, personal
rest, meals and exercise, as ratios; (b) the shape of the increase with repeated intrusions within
a week (my placeholder: convex, exponent 2); (c) how long recovery takes (my placeholder: 7
days).** Cover cumulative sleep restriction (Van Dongen et al. 2003?), recovery from work during
leisure (Sonnentag), work–family conflict and its effects, and the effects of repeated evening
work.

### 5. Ordering a reward after an effortful task
The system places something the person enjoys directly after something they want to do but find
hard (a liked drink after a workout), **without ever framing it as a reward**. Is that supported?
Cover temptation bundling (Milkman, Minson & Volpp 2014), the Premack principle, habit formation
(Lally et al. 2010; Wood), and the risk that rewards undermine intrinsic motivation
(overjustification). **Defaults wanted: is the ordering effective, how close in time should the
pair be, and does it work when the person isn't told it's a reward?**

### 6. When someone is behind: easy wins first or hardest first?
The current rule is hardest task first when the person is on track, and the smallest, easiest
wins first when they're behind, to build momentum. Cover the progress principle (Amabile & Kramer),
goal-gradient effects, research on task selection and completion order (e.g. KC, Staats et al.,
"easy first" choices), and overwhelm and avoidance. **Defaults wanted: (a) a threshold for
"behind" (overdue items, or recent skips); (b) how many quick wins before returning to the hard
thing.**

### 7. How much asking is too much
The system asks at most one clarifying question when a task is mentioned, raises a slipping task
at most once a day, and holds a five-minute weekly review. Cover interruption cost and
attention-sensitive alerting (Horvitz and colleagues), notification fatigue, burden in
experience-sampling studies, and "nagging" in reminder and coaching apps. **Defaults wanted:
questions or prompts per day and per week before response quality or engagement drops, and the
point at which reminders turn counterproductive.**

### 8. When a forgotten task is effectively abandoned
Low-stakes tasks that never rise and are never mentioned are archived after a period (my
placeholder: 30 days). Is there evidence on to-do list abandonment rates, and on when a task left
undone is effectively dropped (Zeigarnik and Masicampo & Baumeister 2011 on unfinished tasks;
any to-do-app usage data)? **Default wanted: days.**

### 9. Casual promises with no date
"I'll send you the photos." **Default wanted: days before an unfulfilled casual promise starts to
cost trust (my placeholder: 7).** Cover any evidence on promise-keeping, reciprocity timing, and
response-time expectations in personal relationships. If the evidence is thin, say so.

### 10. Combining several harms into one importance score
Each task records which harms apply (financial, legal, health, social, psychological), each graded
minor, major or severe. **The worst harm sets the floor, and further harms compound above it.**
My placeholder is a geometric ladder (minor 10, major 30, severe 90) plus 25% of each further
major-or-worse harm, capped at the next grade. Is there decision-science or risk-assessment
evidence on combining ordinal severities (risk-matrix critiques, multi-attribute utility,
cumulative stress or allostatic load)? **Defaults wanted: a ladder ratio and a compounding rule.**
Also: how much less a harm that falls mainly on an organisation should weigh than the same harm to
the person or their intimates (my placeholder: 0.5 against 1.0).

## Output

One markdown document, **one section per topic in the order above**, each ending in a box:

```
Default: <value> (range <low–high>) · Confidence: <high|medium|low>
Basis: <one line>
```

End with a **summary table**: topic, my placeholder, your recommended default, confidence. Then
list every citation I gave that was wrong or unverifiable, and what is correct.
