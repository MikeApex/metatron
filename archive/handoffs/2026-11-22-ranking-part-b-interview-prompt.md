Model: Opus 5.5, high effort — an interview and a design plan where the user's values are the input; judgement is the work. Fable 5.1 runs the adversarial review of the plan at the end (/adversarial-review).

# Ranking, Part B — interview Mike, then plan values-weighted ranking

You are planning, not building. This chat interviews Mike, then writes a plan. No code, no config
or agent-file edits, no deploy.

## Read first, in order

1. `SESSION.md`, then `ROADMAP.md` (the mandatory pre-edit context check applies even though you
   will not edit code).
2. `archive/plans/goal_task_network_plan_2026-11-18.md` § 16 — Mike's eight rulings of 2026-11-22
   verbatim (1–5, then 6–8 after the deploy), what Part A built, its costs, what the live checks
   found, and what was deliberately left for you. § 4–5 for the
   network it sits in (§ 5's phase 3, "large goals", is adjacent: share what it shares, don't
   duplicate it).
3. What Part A shipped, as the code really is (check `git log` for the ranking Part A commit; if it
   has not landed yet, read the working-tree versions and say so in the plan):
   `tools/day_plan.py` `_score` and `_ramp`; `config/modules/day_plan.yaml` `score:` (the weights,
   `ramp_days`); `tools/obligations.py` `is_essential`, `_end_weight`, `_PLAN_FIELD_PROPS`
   (`stakes`, `priority`, `stakes_why`); `tools/task_judge.py` and `config/agents/task_judge.md`.

## The need, in Mike's words (2026-11-22)

- *"Tasks should be scored always, and if not vital should have a weaker score and be relegated to
  back burner … Metatron should check new tasks against user goals and core values to ensure
  appropriate ranking. If someone is a passionate gardener, repotting the plants is likely more
  important than for the weekend warrior."*
- *"The temporal dilation is a key part of how we can emphasize the right, or the wrong things.
  Sometimes even an urgent deadline is less important if the underlying task gets in the way of,
  say, family time. This will require a deeper interview conversation to do properly."*
- *"Taxes might not align with mission, but still are high priority."* Costs of missing something —
  *"financial — easy to quantify, social — much harder, existential/psychological — harder
  still"* — should inform the weighing.
- *"For tasks in the future, their shape and edges should be figured out by Synth in
  communications. For example, the GS donation needs to be done before the donations for this
  year's annual fund close out at the end of November, or may have an emotional component yet
  unearthed. Potting plants might have a window of two weeks before the plants die, etc. These
  things should be probed at task mention."*
- *"Disappointing a parent is likely vital, not missable. Urgency and importance are two different
  vectors that are being consolidated into a single score."*
- *"Metatron should proactively manage tasks and prioritization with the user, as well as by
  itself on the backend. That reconciliation is a core strength of the intended tool. Metatron's
  mission is to emphasize what will lead to long term happiness, not managing a to do list."*

Part A built the mechanism with no weights invented: every task judged vital/missable plus a
priority (by the opening agent, else `task_judge`), plan steps inherit their end state's weight,
and a straight-line climb toward the due date. What it does not know is **Mike's** answer to what
should outweigh what, which is your job to get.

## The interview

Before you ask anything, propose the interview's shape in a few lines — the topics, in order, and
roughly how long — and let Mike reorder or cut it. Then one topic at a time, conversationally;
reflect back what you heard before moving on; his answer is design by default (how Metatron
should work for anyone) unless he says it is just him — ask when it is unclear.
Topics to cover (refine them; don't read them out as a list):

1. **Urgency and importance, apart.** Part A folds both into one score (`_score`): how near a
   date is, and how much it matters. What each axis is made of, how they combine to decide what
   is done first — and where a merely urgent task loses to an important one.
2. **Protected time.** Which parts of a life outrank a deadline that would cut into them (family
   time, sleep, health, rest), how strongly, and when a deadline may intrude anyway (a tax filing
   on 30 December).
3. **Values and passions.** How Metatron learns that someone is a keen gardener — from the
   mission, goals and profile it already holds, from behaviour, or by asking — and how much a
   passion should lift its tasks.
4. **The costs of missing something.** Financial, legal, health, social, psychological,
   existential: which to record per task, how to weigh the hard-to-quantify ones against the easy
   one (a parent let down is vital, Mike says).
5. **Probing a task's shape when it is mentioned.** The real deadline behind the stated one, a
   decay window, an unearthed emotional component — which tasks earn a question, how many, in
   whose words, and what it costs the user's attention (the denominator of the core metric).
6. **The climb.** How early different kinds of things should start rising (an obligation with
   lead times, a chore, a promise to a friend), and when rising turns into being raised.
7. **The back burner.** What becomes of unimportant tasks that are quietly forgotten — let them
   expire, review them now and then, ask once — and how a misjudged real obligation is caught.
8. **Reconciliation.** What Metatron settles alone in the background, what it brings to the user,
   how often (a weekly look at priorities?), and how a clash is put to them (an urgent deadline
   against family time).
9. **Long-term happiness as the aim.** What would tell either of you the ranking is serving it —
   framed as a working hypothesis to test in use, never a verdict.

## Deliverable

`archive/plans/ranking_values_plan_YYYY-MM-DD.md`: the need in his words; his answers as rulings;
the design (which weights move to per-user config — config is the product; One Home Per Rule
Class for every new rule); phases, each ending in a live check with Mike; tests; Red edits it will
prompt for; and a budget covering all four cost classes (build, run, ancillary, unseen) with a
recommended model for building and for review. Then run `/adversarial-review` on it (Fable),
reconcile every finding in the plan, and end with the phase 1 build prompt, its model line first.

## Rules that bind this chat

- Nothing leaves this machine (no Artifact, WebFetch or WebSearch); a shareable document is a file
  in `archive/plans/`.
- All personal data is sensitive tier; anything you design that reads it states its privacy basis
  (ROADMAP.md § Section 0).
- Don't file backlog items Mike didn't ask for.
- `config/personas/mike/**` is VM-owned — never edit it; deploying is Mike's.
- Number every list of options or findings; never write a backlog id bare.
- A Mike-only step gets a proposed walkthrough session, not a line on a list.
- Close with `/archive`.
