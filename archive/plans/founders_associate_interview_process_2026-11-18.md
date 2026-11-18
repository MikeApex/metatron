# Founder's Associate: Internal Interview Process

2026-11-18. **Internal only. Never sent to candidates or referrers.** The public summary of the process lives in [founders_associate_brief_2026-11-18.md](founders_associate_brief_2026-11-18.md) § How to nominate someone.

## Principle

Every requirement in the brief is verified by **at least two stages, at least one of them supervised** (live, observed, or reproduced live). No claim on a CV and no unsupervised deliverable counts on its own. Written work is accepted only when the candidate can reproduce or extend it live.

## Coverage matrix: what each stage verifies

| Requirement / trait | 1 Written | 2 Conversation | 3a Quant test | 3b Tech test | 4 Live interview | 5 Paid project | 6 Final |
|---|---|---|---|---|---|---|---|
| Numeracy | | | **S** | ● | | ● | |
| Technical floor (code + data end to end) | | | | **S** | | ● | |
| Behavioral science | ● | **S** | ● | | | ● | |
| Interpersonal strength | | **S** | | | **S** | ● | ● |
| Curiosity over credentials | ● | **S** | | | | ● | |
| Breadth, broadly read | ● | **S** | | | | | ● |
| Care for user over metric | | ● | ● | | | ● | **S** |
| Executor, not planner | | | | ● | | **S** | |
| Comfort without structure | | | | | | **S** | ● |
| Intellectual honesty | ● | | | | | ● | **S** |

**S** = verified under supervision. ● = evidence contributes.

## Stages

### Stage 1: Written response and CV (unpaid, ~1 hour for candidate)

**Task:** the brief's prompt: *a belief you held about how some group of people behaved, how you found out you were wrong, what you did next.*

**Pass signals:** a specific belief, not a platitude. The evidence that changed their mind is concrete. "What I did next" is an action, not a reflection.
**Fail signals:** a story where they were secretly right all along. A moral lesson in place of evidence. Generic prose that reads as AI-generated with no specific detail (this is probed in stage 2).

**Also verify:** any shipped project on the CV has a link (repository, live product, paper). A claimed project with no artefact is flagged for stage 2.

### Stage 2: Initial conversation (45 min, founder)

1. **Written response, probed.** Ask for two details the essay left out. Someone who lived the story produces them instantly.
2. **The referrer question, live.** *Something you investigated purely because you wanted to know.* Follow it three levels down. Did they change their mind partway?
3. **Shipped project walkthrough.** Screen-share the artefact from the CV. Ask them to explain one decision they would make differently now.
4. **Reading.** *What have you read outside your field that changed how you think about people?* Follow up on one claim from it. This tests breadth and whether the reading actually lodged.
5. **Behavioral science.** *Why do people so often fail to do what they say they value?* Look for mechanisms (present bias, habit, identity, social context), not a single buzzword.
6. **Interpersonal read.** Note whether they ask you anything, and whether they let a pause sit.

**Advance if:** stages 2.1 and 2.3 hold up (authenticity), and at least two of 2.2, 2.4 and 2.5 show genuine depth.

### Stage 3a: Quantitative and measurement test (90 min, proctored on camera, closed AI)

Written answers, shared screen, calculator and notes allowed, AI tools not allowed. Five items, each rubric-scored 0–3:

1. **Base rates.** A screening-style probability problem in which the intuitive answer is wrong.
2. **Sample size.** "We interviewed 8 people and 6 liked feature X." What can and can't be concluded? What would be needed to conclude more?
3. **Confound spotting.** A short, deliberately flawed study (for example, "users who used the app daily reported higher life satisfaction"). List the alternative explanations and design a test that separates them.
4. **Measurement design (the central item).** *Design a way to tell whether a product made its users' lives better, more fulfilled or more connected over 3 months, without using time-in-app as the measure, and without collecting more personal data than needed.* Assess: a validated or defensible outcome measure, a comparison condition, attrition and self-report bias acknowledged, and privacy treated as a design constraint rather than an afterthought.
5. **Goodhart.** Name a metric that would look good while the product made users' lives worse.

**Pass:** at least 10/15, and at least 2/3 on item 4.

### Stage 3b: Technical test (take-home ≤ 3 h, then a 45-min live extension)

**Take-home:** a **synthetic** dataset (never real user data) of messy, timestamped behavioral logs plus a short self-report survey. Clean it, answer two stated questions, and produce one chart and one paragraph of findings, in the language named in the brief. AI assistance is permitted if declared.

**Live extension (supervised, which is what makes the take-home count):** the candidate shares their screen and, in their own code:
1. explains one cleaning decision and its alternatives;
2. answers a new question the founder poses on the spot, which requires modifying the code;
3. fixes a bug the founder points to, or one introduced on the spot.

**Pass:** the code runs; the findings don't overclaim; the live changes are made fluently in their own code. A candidate who can't navigate their own submission fails, whatever its quality.

### Stage 4: Live research exercise (60 min, founder observes, camera on)

**Setup:** the founder recruits a volunteer the candidate has never met (not the founder, and nobody from the product's user base). Topic: *how you spend an ordinary week, and the relationships and activities that matter most to you.* Nothing about the product is disclosed.

**Candidate task:**
- 10 minutes of preparation, with their interview guide shared beforehand;
- a 30-minute interview while the founder observes silently;
- a written findings memo within 24 hours: three findings, the evidence for each, one surprise, and one thing they'd ask differently.

**Score on:** open versus leading questions; follow-ups that reach actual behavior rather than stated intentions; comfort with silence; whether the volunteer ended up saying something candid; whether the memo separates what was said from what was inferred.
**Volunteer debrief (2 questions, after the candidate leaves):** *Did you feel listened to? Did you say anything you didn't expect to?*

### Stage 5: Paid supervised project (3–4 days, paid at the contract rate)

**Engagement:** a short paid agreement with confidentiality and IP assignment, signed before the project starts. **No access to the product, the codebase or any user data.** The project is designed to be done without them.

**Brief (example, rewrite per cohort):**
> Choose one candidate first-adopter group for a personal companion product focused on wellbeing, fulfillment and relationships. Recruit and interview 3–5 people from that group yourself. Deliver: (a) a recommendation on whether this group should be first, with the evidence; (b) what result would have changed your recommendation; (c) one positioning line that you tested on at least two of them, and how they reacted; (d) a one-page plan for measuring whether the product helped this group.

**Supervision:**
- a 15-minute kickoff, after which no further specification is given (this tests comfort without structure);
- a 15-minute check-in each day: what they did, what they found, what changed;
- one **mid-project redirect**: on day 2, the founder changes the priority (for example, "drop the positioning line and go deeper on the measurement"). This tests how they handle reallocated work;
- a 45-minute final readout with founder questions.

**Verifiable outputs:** interview notes with dates and anonymized participant descriptors; consent recorded for each interview; the positioning reactions as reported; the deliverable itself.

**Score on:** did they recruit real strangers on time (execution); did the recommendation follow from the evidence; did they report evidence against their own pick (honesty); how they handled the redirect; the quality of the measurement plan (a cross-check against stage 3a item 4).

### Stage 6: Final discussion and references (60 min + references)

1. **Disagreement test.** The founder states a plausible but flawed conclusion about the candidate's own stage 5 findings and pushes it. Does the candidate hold their ground with evidence, or fold? Both folding and stubbornness without evidence are fails.
2. **Values.** *A feature would double how often people open the product, but you suspect it would make them a little less content. What do you do?* Look for reasoning, not the "right" answer.
3. **Working terms.** Commitment, hours of overlap with London, milestones, and conversion terms, discussed openly as the brief promises.
4. **References, two:** one academic and one from somewhere they built or shipped something. Ask each referee for a specific time the candidate changed their mind, and a time they pushed back on someone senior.

## Scoring and decision

Each trait in the matrix is scored 1–4 on its **supervised** evidence:

| Score | Meaning |
|---|---|
| 1 | Absent or contradicted under supervision |
| 2 | Present but shallow; needs direction |
| 3 | Solid; meets what the brief demands |
| 4 | Exceptional; would raise the bar of the role |

**Offer rule:** no trait at 1; Numeracy, Technical floor, Interpersonal strength and Intellectual honesty each at 3 or above; and at least one 4 among Curiosity, Breadth or Executor. Write the scores down **before** the final discussion, so the final conversation can't retroactively rescue or sink a candidate on charm.

## Discretion rules for the process

1. No candidate sees the product, its internals or any user data before signing the contract. Stage 5 is designed to be done without them.
2. Every dataset is synthetic. Every interview volunteer is outside the user base.
3. The interview questions and rubrics in this document are never shared with candidates or referrers.

## Cost budget (per candidate who reaches each stage)

| Stage | Founder time | Cash |
|---|---|---|
| 1 Written + CV | ~15 min | — |
| 2 Conversation | ~1 h | — |
| 3a + 3b | ~2.5 h (proctoring, review, live extension) | — |
| 4 Live interview | ~1.5 h, plus recruiting one volunteer | [PLACEHOLDER: volunteer thank-you, if any] |
| 5 Paid project | ~3 h (kickoff, check-ins, readout, review) | 3–4 days × contract day rate |
| 6 Final + references | ~2 h | — |

The one-off preparation before the first cohort (synthetic dataset, quant test items with model answers, stage 5 brief) is roughly 1–2 days of founder time, and it is reused across candidates. Funnel planning: if ~10 candidates reach stage 2, expect ~4 at stage 3, ~2–3 at stage 5. That is ~20–25 founder-hours plus 2–3 paid projects per hire.

## Open items (founder)

- [ ] Contract day rate, which sets the stage 5 cost
- [ ] The language(s) for stage 3b, matching the brief's technical floor
- [ ] Build the synthetic dataset and the 3a items with model answers
- [ ] Source of stage 4 volunteers
- [ ] Confidentiality/IP template for the stage 5 paid agreement
