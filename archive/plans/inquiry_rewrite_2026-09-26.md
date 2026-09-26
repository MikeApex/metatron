# Inquiry — rewrite working draft

*2026-09-26. **Edit this file directly.** Working draft only — nothing here is live. Once every
chunk is approved, it is assembled into `.claude/agents/build-inquiry.md` in one edit.*

**How to use it:** the `CURRENT` block under each chunk is quoted for reference — don't edit it.
Edit the `PROPOSED` block freely; it is plain prose, not fenced, so it behaves like any other
text in VS Code. Answer each decision after its `→`. Add `[MT: ...]` anywhere for a comment.

**Target:** 153 lines → roughly 55. Source of the role framing: Mike's original prompt, 2026-09-26.

**Settled already:** the requirement that `disposition_evidence` *"must name an existing
specialist"* is removed. It is the root cause of the Time Director invention — a stage with no
tools was required to name a member of a list it was never shown. Removing it also touches
`core/build/schemas.py` (`_check_disposition` enforces the same thing for a `new` disposition),
plus `test_build_schemas.py`. Not a one-file change.

---

## Chunk 1 — the opening: identity and stance

### CURRENT — lines 19–32, 14 lines

> # BUILD — INQUIRY
>
> Something arrived that no existing capability owns. Your job is to write down the questions that
> have to be answered before anyone builds the thing that would own it.
>
> **You work in a vacuum. You have no tools and this is deliberate.** You are handed the gap, the
> trigger that filed it, the mode, and in REPAIR the dossier. You are shown no manifest, no corpus,
> no policy and no data, because the point is to find where the existing data is **inadequate** —
> and a model shown the corpus first asks only what the corpus can already answer. Someone else
> finds out what exists. That is not your question and you must not guess at it.
>
> Do not ask who produced the gap or what they hope you will say.

### PROPOSED — 9 lines

# BUILD — INQUIRY

You are an experienced executive assistant on your first day with a new employer. You will never speak to them directly, but almost perfect knowledge about them is available to you: diaries, correspondence, a contact book with detailed notes, a calendar, stated preferences, and several biographies. You also have access to external research tools.

A request has arrived that nothing currently handles. Your job is to write down everything you would need to know before acting on it.

**You have not read any of it yet, and that is deliberate.** Those sources describe what could be known about this person, not what you have in front of you — so name what you would need from them, and what you would go and research. Someone else finds it. **Never invent a fact, a source, a preference, or a part of the system.** Where knowing something matters, that is a question, not an assumption.

**Build a compass, not a filter.** Do not only frame this narrowly or tactically. Think about the whole of the person's life: broader life goals, opportunity costs and what this request displaces.

### Decisions — RESOLVED 2026-09-26

**1 & 2 — the source list is scaffolding, not a possession (Mike).** *"The records and tools that
are suggested are reasonable frameworks so that it can direct its question in a grounded reality
(executive assistant), and still answer a priori."*

So the apparent contradiction — paragraph 1 grants research tools, paragraph 3 said "you hold no
tools" — is resolved in **paragraph 3, not paragraph 1**. The sources stay concrete and unhedged
because their job is to ground the *kind* of question an assistant would ask; what changes is that
paragraph 3 no longer denies holding tools. It says the sources describe what could be known rather
than what is in hand, and asks the model to name what it would need from them. True, and no longer
self-contradicting.

**The separate "aim at what a record would not already answer" line is NOT added.** The grounding
does that work: naming the record types is what tells the model which questions are answerable and
therefore worth asking. One fewer line. *(Flagged in case this reads the ruling too broadly — say
so and it goes back in.)*

**3 — `"Do not ask who produced the gap or what they hope you will say"` is DROPPED** (Mike: "fine").
In the assistant framing there is no requester separate from the employer, so the line would have
read as "don't ask about your employer".

**4 — the two stances move to chunk 2** (Mike: "we'll get to that in the next section"). Not folded
into chunk 1.

---

## Chunk 2 — the question classes, the ordering rule, and the two stances

### What the code enforces — `core/build/schemas.py`, not negotiable

| Enforced | Where |
|---|---|
| Class must be one of the eight names | `SPINE_CLASSES`, line 52 |
| Class index **non-decreasing** across the spine | `_check_spine_order` |
| **No `feasibility` before the first `intent`** — its own check, its own message | same |
| At least one `intent`, one `surface`, one `authority` (`authority` exempt at `triage`) | `_check_required_classes` |
| `integrity`, `cost`, `asymmetry`, `minimum_version` are **optional** | by omission — never stated in the agent file until now |
| Quality of a question | **deliberately not checked.** The code's own note: it can tell that intent was reached for before feasibility, and nothing more |

The validator's message for the inversion is *"it makes the calendar the arbiter and treats empty
capacity as available capacity"* — so stance 2 below is already the recorded reason the ordering
rule exists. They are one topic, not two.

### CURRENT — lines 59–95, 37 lines

*The eight-row table, the ordering rule stated twice, a `## Two stances` section, and a
`## Ask freely` section. Quoted in full in `.claude/agents/build-inquiry.md`; not repeated here
because the table below is deliberately near-verbatim.*

### PROPOSED — 22 lines

## The eight classes, in order

Ask in this order. A question placed before another had to be **thought of first**, and position cannot be faked the way a label can.

| # | class | Asks |
|---|---|---|
| 1 | `integrity` | What on the face of this request does not cohere? |
| 2 | `intent` | What is this in service of? What have they said they want more and less of — and where do stated and revealed preferences diverge? |
| 3 | `cost` | What does acting consume that nothing meters — empty time, attention, social energy, a reciprocity obligation that outlives the act? What is the base rate, and the marginal value at that rate? |
| 4 | `asymmetry` | Is anything here irreversible or closing? Is there regret in **both** directions? |
| 5 | `feasibility` | Can it be done, and at what cost to what surrounds it? |
| 6 | `surface` | What else operates on this once it exists — move, delete, dedupe, merge, expire, reconcile? What will it reasonably also be asked to do? What breaks if it exists and nothing else changes? |
| 7 | `minimum_version` | What captures most of the value at a fraction of the cost? |
| 8 | `authority` | What is decided here versus surfaced — and what is the **stated default, so that silence still produces an outcome**? |

**`intent`, `surface` and `authority` are required** — `authority` except at `triage`. The other five are yours to use or skip.

**No `feasibility` question may precede every `intent` question.** That single inversion is the difference between a filter and a compass: it makes the calendar the arbiter, and it treats empty capacity as available capacity. Two stances follow from it, and every question you write inherits them:

- **Neutral is not a pass.** The absence of an obstacle is not a reason to act. The burden of proof sits on doing something.
- **Empty capacity is not available capacity.** Unstructured time, unspent attention and unclaimed budget are assets to defend, not gaps to fill.

**Ask freely.** The cost is in adjudicating, not in asking — around 25 is a comfortable ceiling, and a short set is fine too. What you decide *not* to ask goes in `declined_to_ask[]` with the reason; that list is read, and an empty one on a complex request reads as not having considered the edges.

### Decisions

**1. What do we call the employer in the class table?** The table currently says *"what has **the
user** said they want"*. `the user` is this project's house term and appears in every other agent
file — but chunk 1 established *"a new employer"* and *"the person's life"*, so mixing them is
sloppy. I have used **"they/them"** throughout, which reads naturally in the assistant voice and
avoids both "user" and "boss". Confirm, or force "the user" for consistency with the rest of the
project.

→

**2. The ordering rule is now stated once, not twice.** The current file says *"It is the one
ordering rule worth stating twice"* and does so. I kept the full rationale — filter versus compass,
the calendar as arbiter — and dropped the repetition. Your brevity instruction argues for once; the
original author thought it earned twice.

→

**3. I added a line saying four of the eight classes are optional.** The code has always allowed
this and the file has never said it. It is new information to the model, not a cut — and it may
change behaviour, probably toward shorter sets. Wanted, or should the file stay silent and let it
assume all eight?

→

**4. Anything else on chunk 2.**

→

## Chunk 3 — depth, and what is dropped

*Not drafted yet. `depth`/`proposed_depth` as the cost control; the fate of `disposition`,
`generalizes_to` and `declined_to_ask`.*

## Chunk 4 — the output contract

*Not drafted yet. The JSON shape and the hard constraints, which must match what
`core/build/schemas.py` checks.*

## Chunk 5 — REPAIR mode

*Not drafted yet. The dossier section, compressed.*

---

## Bench test 1 — the rewrite, WITH the injections still leaking (2026-09-26)

Run on Claude Code **2.1.233**, so `omitClaudeMd` was not yet available. Identical prompt to the
first live run — three lines, `mode` / gap / trigger — so the two are comparable.

**Result: VALID, zero defects.** 23 questions, all eight classes, no `disposition`, no
`proposed_depth`. The agent file and `schemas.py` agree.

### Fixed

1. **It invented nothing.** No Time Director, no named specialist, no claimed architecture. Where
   it needed to know what exists it *asked* — q3: *"is there an existing recurring mechanism — a
   scheduler run, a daily or weekly check-in — that this should have landed in and didn't?"* Same
   territory as the first run's false claim, posed as a question instead of asserted as fact.
2. **The size judgement landed in `framing_note`** as instructed: *"Broaden — but only by one step,
   and deliberately not further"*, with an explicit statement of what it refuses to fold in.
3. **The questions are markedly more assistant-shaped.** New and good: **q11** is any plant
   irreplaceable (a gift, an inheritance) — the only fact that makes the downside truly
   irreversible; **q5** is the real ask delegation rather than a better-timed prompt; **q8**
   over-watering kills houseplants as reliably as drought, so a blind fixed-interval reminder can
   cause the harm it was built to prevent; **q19/q20** build nothing, add one line to a surface he
   already reads, ask him one question.

### NOT fixed — and this is the measurement that justifies the upgrade

**Better instructions did not stop the paygrade drift. The injection is the cause.** Six of 23
questions still reason about the machinery, now quoting the project's own files verbatim:

| Question | What it quotes |
|---|---|
| q6 | *"a director and companion for a human life, not a scheduler or task manager"* — `CLAUDE.md`, word for word |
| q9 | *"a cadence chosen without a cost figure beside it is a cost decision made by accident"* — global `~/.claude/CLAUDE.md` § Costs, word for word |
| q20 | *"config is the product and needing code is a design failure"* — `CLAUDE.md`, word for word |
| q15 | data tiers, and what they rule out for storage and processing |
| q18 | *"two config homes… two personas"* |
| q21 | *"does the destination sit in a tier that requires his approval"* |

**The sharpest single demonstration: it calls the employer "he" throughout.** The prompt carried no
name and no gender. It learned that from the injected files.

**Conclusion.** The rewrite did the work an instruction can do — it stopped the *invention*. It
cannot stop the *knowledge*. That is a harness problem, not a prompt problem.

Validation script: `inquiry_v2.py` in this session's scratchpad (not preserved — re-transcribe from
the transcript if bench test 2 needs a baseline comparison).

---

## NEXT SESSION — bench test 2, with the vacuum actually sealed

**Do this in order.**

1. **`claude update`** on Mikes-MacBook-Air. Native install at `~/.local/bin/claude` →
   `~/.local/share/claude/versions/`. There is also a stale npm copy at 2.1.170 that is NOT on
   PATH — ignore it.
2. **`claude --version` must be ≥ 2.1.271.** Below that, `omitClaudeMd` is silently ignored and
   bench test 2 measures nothing. This is the one check that must not be skipped.
3. **`omitClaudeMd: true` is already in `.claude/agents/build-inquiry.md`'s frontmatter** — added
   2026-09-26, with the reasoning as comments beside it. Nothing to do.
4. **Re-run the bench test**, same three-line prompt, verbatim:

   ```
   mode: construct

   gap: The user asked to be reminded when the plants at home need watering, and nothing does that.

   trigger: phase F1 run 1, hand-filed; user asked for a reminder to water the plants at home
   ```

   Spawn `build-inquiry` directly — **not through `/build`**. The driver will not hand out Inquiry
   for `BLD-0926-02` because `question_set.json` already exists, and hand-deleting a landed
   artifact to force it is the off-piste move the command file warns against.

5. **Check these four things in the output, which is the whole point of the test:**
   - Are the six system-shaped questions above gone, or do they survive?
   - Does it still say **"he"**? If yes, something is still leaking and the source needs finding.
   - Does `MEMORY.md` still reach it? The docs say auto memory is *never* loaded into a subagent;
     ours received it on 2.1.233 and quoted it exactly. If it persists on ≥ 2.1.271, that is a
     reportable Claude Code bug, not a config problem.
   - Does the output still validate? Run `S.validate_question_set(qs, known_capabilities=None)`.

6. **If the drift survives a sealed vacuum**, it is structural, and the open decision is the one
   deferred on 2026-09-26: remove `feasibility` and `surface` from Inquiry's spine and push both to
   the Planner. **That breaks two things and they must be handled, not discovered:** the validator
   requires at least one `surface` question, and the compass fixture
   (`tests/test_build_spine.py`, *turn 2 fails / turn 4 passes*) exists precisely to stop
   `feasibility` preceding `intent` — take feasibility out and that test loses its subject.

**Still open on the rewrite itself:** chunks 3–5 (the output contract, the hard constraints, REPAIR
mode) are uncompressed. The file is 141 lines against a ~55 target, and the remaining cuts are all
in those three sections.
