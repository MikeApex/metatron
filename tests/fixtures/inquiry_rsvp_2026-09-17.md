# Fixture — the RSVP pass/fail pair

**Never shipped to a model.** This is a regression fixture. The operating rule the model reads is
the abstract in `config/agents/build_inquiry.md`; the full conversation is
`archive/plans/inquiry_reference_rsvp_2026-09-17.md`. Three forms, three jobs, deliberately kept
apart (plan § 15).

**Why the verbatim form cannot be discarded in favour of the abstract.** Its evidentiary value is
that it is a **real pass/fail pair produced before the rule existed**. An abstract cannot fail a
validator. Turn 2 must fail validation and turn 4 must pass — and because neither was written to
satisfy a rule that did not yet exist, a validator that sorts them correctly is discriminating
rather than merely firing.

**Named weakness: n = 1.** A validator tuned until one pair sorts correctly may be fitted to that
pair rather than to the principle, and the domain is narrow — a single social invitation. The
mitigation is that every Inquiry run produces another pair, from real runs, never manufactured. If
the second and third real pairs need the validator loosened, that is the signal the rule was
overfit, and it arrives early and cheaply.

---

## What is encoded, and the one judgement call in it

Each turn's **decision spine section** is encoded verbatim as the `spine`, in the transcript's own
order. Every question carries `source_quote` — the text it was cut from — so the encoding is
auditable against the transcript without leaving this file.

**The one addition, stated because it is the only place this encoding is not a straight lift.**
Turn 4's numbered spine has eight items and none of them is a `surface` question. The material
exists in turn 4's body, not its list — *"Every yes creates obligations that outlive it. Attending
puts us into a reciprocity loop: future invitations, a hosting expectation, an implied
availability"* and *"Know the annual shape... the decision is really a policy about a standing
commitment, not a one-time choice."* It is encoded at `q7`, which is where class index 6 sorts.

**This addition does not manufacture the result.** Turn 2 fails on three independent grounds —
spine unordered, no intent question, no disposition — none of which touch the surface question.
Remove `q7` and the pair still sorts the same way, with turn 4 failing only the `>= 1 surface`
rule. The addition makes turn 4 a clean pass rather than changing which turn passes.

**`generalizes_to` is populated for both turns from each turn's own closing section.** Neither
turn has the field natively — it is a plan-invented field — so leaving turn 2's empty would add a
failure that is not about the compass rule and would flatter the test.

---

**Three fields were REMOVED on 2026-09-24, by plan v4.11 ruling 5.** Inquiry now works in a
vacuum: it sees the gap and nothing about what data exists, because the point is to find where
existing data is inadequate, and a model shown the corpus first cannot do that. So
`candidate_sources`, `manifest_fingerprint` and `policies_consulted` are no longer fields Inquiry
may write — their PRESENCE is now a validation defect — and the `manifest_ids` block that existed
only to validate `candidate_sources` went with them.

**The spine is byte-identical.** Every question, its text, its class and above all its POSITION is
exactly what the 2026-09-17 transcript produced. The removal touches only fields the model would
now never be asked for; it cannot change which turn passes, because nothing removed is read by the
ordering rule. That is the whole reason this pair survived the rebuild: the compass rule was never
about where the data was.

---

## Turn 2 — MUST FAIL

Feasibility second, no question about what the boss is for, no altitude answer.

<!-- fixture: turn2 -->
```json
{
  "schema": "question_set/1",
  "job_id": "BLD-0917-01",
  "generated_at": "2026-09-17T00:00:00",
  "upstream_fingerprint": "rsvp-turn2",
  "mode": "construct",
  "request": "Mary Higgins has invited the boss to John's birthday barbecue this Sunday in Bethesda, MD. RSVP.",
  "depth": "standard",
  "generalizes_to": "ensuring whichever answer goes out on an invitation is the one he would have chosen with full information",
  "framing_note": "An RSVP is trivial to send and expensive to send wrongly.",
  "declined_to_ask": [],
  "spine": [
    {
      "id": "q1",
      "class": "integrity",
      "text": "Is the date and day resolved?",
      "why_it_matters": "August 22 2026 is a Saturday; Sunday is the 23rd. Blocking the wrong day either misses the party or holds a day for nothing.",
      "blocks": "design",
      "expected_answer_shape": "a single resolved calendar date",
      "resolved_by_policy": null,
      "source_quote": "Is the date and day resolved? If not, resolve before anything else."
    },
    {
      "id": "q2",
      "class": "feasibility",
      "text": "Is he physically able to be in Bethesda at 3pm on the correct day?",
      "why_it_matters": "If clearly not, the work moves straight to the quality of the decline.",
      "blocks": "design",
      "expected_answer_shape": "yes/no plus door-to-door travel time",
      "resolved_by_policy": null,
      "source_quote": "Is he physically able to be in Bethesda at 3pm on the correct day? If clearly not, move straight to the quality of the decline."
    },
    {
      "id": "q3",
      "class": "cost",
      "text": "Does the relationship tier justify displacing what is already on the calendar?",
      "why_it_matters": "Nothing on it, low-value items, or high-value items each give a different answer.",
      "blocks": "design",
      "expected_answer_shape": "a tier, and what it displaces",
      "resolved_by_policy": null,
      "source_quote": "Does the relationship tier justify displacing what is already on the calendar?"
    },
    {
      "id": "q4",
      "class": "surface",
      "text": "Are there second-order reasons to attend, or to avoid, because of who else is in the room?",
      "why_it_matters": "A counterparty in a live negotiation, a journalist, or someone he has wanted to meet for a year each flips the decision.",
      "blocks": "behaviour",
      "expected_answer_shape": "a list of likely attendees with flags",
      "resolved_by_policy": null,
      "source_quote": "Are there second-order reasons to attend (someone in the room) or to avoid (someone in the room, an optics or conflict issue)?"
    },
    {
      "id": "q5",
      "class": "minimum_version",
      "text": "Does a short appearance capture most of the value at a fraction of the cost?",
      "why_it_matters": "The choice is not binary; there are at least five outcomes.",
      "blocks": "design",
      "expected_answer_shape": "one of the five framed options",
      "resolved_by_policy": null,
      "source_quote": "Does a short appearance capture most of the value at a fraction of the cost?"
    },
    {
      "id": "q6",
      "class": "authority",
      "text": "Is this a decision I can make, or one I must surface — and what happens on silence?",
      "why_it_matters": "Day one has the file but not the earned authority; a stated default means silence still produces an outcome.",
      "blocks": "behaviour",
      "expected_answer_shape": "decide/surface, plus the default and its deadline",
      "resolved_by_policy": null,
      "source_quote": "Is this a decision I can make, or one I must surface?"
    }
  ]
}
```

**Expected defects** — three independent grounds, each traceable to the turn-3 critique:

| Defect | The critique it corresponds to |
|---|---|
| spine not ordered by class index (`feasibility` class 5 at position 2, `cost` class 3 at position 3) | *"framed through the lens of availability"* |
| a feasibility question precedes every intent question | *"I built a filter, not a compass"* |
| no intent question | *"no reflection on broader life goals"* |
| `disposition` absent | no altitude answer — the request is answered on its own terms |
| `disposition_evidence` empty | same |

---

## Turn 4 — MUST PASS

Intent first, feasibility sixth, and the deliverable reclassified as a standing policy.

<!-- fixture: turn4 -->
```json
{
  "schema": "question_set/1",
  "job_id": "BLD-0917-02",
  "generated_at": "2026-09-17T00:00:00",
  "upstream_fingerprint": "rsvp-turn4",
  "mode": "construct",
  "request": "Mary Higgins has invited the boss to John's birthday barbecue this Sunday in Bethesda, MD. RSVP.",
  "depth": "deep",
  "disposition": "policy",
  "disposition_evidence": "The first-day deliverable is not an RSVP but the beginning of a standing allocation policy: what he is protecting this year, what the weekend budget is, which relationships are being invested in and which are on maintenance, what the automatic yeses and noes are, and where discretion ends. It retires the whole class of bespoke per-invitation analysis performed under time pressure.",
  "generalizes_to": "every social and semi-social invitation competing for a scarce weekend inventory, decided at the margin against a standing allocation policy rather than one at a time",
  "framing_note": "Absence of a blocker is not a reason to attend. A yes must be affirmatively purchased.",
  "declined_to_ask": [],
  "spine": [
    {
      "id": "q1",
      "class": "intent",
      "text": "What is he trying to do with this period of his life, and what has he said he wants more and less of?",
      "why_it_matters": "Explicitly stated intentions are the highest-quality signal available. Those statements are instructions.",
      "blocks": "design",
      "expected_answer_shape": "a named season, plus stated wants and don't-wants",
      "resolved_by_policy": null,
      "source_quote": "What is he trying to do with this period of his life, and what has he said he wants more and less of?"
    },
    {
      "id": "q2",
      "class": "intent",
      "text": "Does this serve that, work against it, or is it neutral?",
      "why_it_matters": "Neutral is not a pass. Neutral competing against a scarce resource is a soft no.",
      "blocks": "design",
      "expected_answer_shape": "serves / works against / neutral, with the reason",
      "resolved_by_policy": null,
      "source_quote": "Does this serve that, work against it, or is it neutral? Neutral is not a pass. Neutral competing against a scarce resource is a soft no."
    },
    {
      "id": "q3",
      "class": "cost",
      "text": "What is the counterfactual use of this specific block, including deliberate emptiness, and what has already been committed this month?",
      "why_it_matters": "Empty calendar space is frequently the most valuable thing on the calendar; the base rate and the marginal value at that rate are what decide, not whether the slot is free.",
      "blocks": "design",
      "expected_answer_shape": "the alternative use, the month's committed count, and the marginal value",
      "resolved_by_policy": null,
      "source_quote": "What is the counterfactual use of this specific block, including deliberate emptiness, and what has already been committed this month?"
    },
    {
      "id": "q4",
      "class": "asymmetry",
      "text": "Is there an asymmetry or closing window that overrides the ordinary calculus?",
      "why_it_matters": "The downside of missing a closing window is unrecoverable; the downside of attending is a wasted afternoon. Most events are not that, and treating everything as irreplaceable means attending everything.",
      "blocks": "design",
      "expected_answer_shape": "yes/no, and which door is closing",
      "resolved_by_policy": null,
      "source_quote": "Is there an asymmetry or closing window that overrides the ordinary calculus?"
    },
    {
      "id": "q5",
      "class": "asymmetry",
      "text": "What does this relationship's trajectory look like, and what does one absence do to it?",
      "why_it_matters": "Relationships are slopes, not points. Missing one party in a warm relationship costs almost nothing; missing one in a relationship quietly fading for three years may be the moment it ends.",
      "blocks": "design",
      "expected_answer_shape": "a five-year contact trend, and the cost of one absence against it",
      "resolved_by_policy": null,
      "source_quote": "What does this relationship's trajectory look like, and what does one absence do to it?"
    },
    {
      "id": "q6",
      "class": "feasibility",
      "text": "Only now: is it feasible, and at what cost to the days around it?",
      "why_it_matters": "Feasibility is fourth in the amended order, not first. It qualifies a decision already reasoned, rather than making it.",
      "blocks": "design",
      "expected_answer_shape": "yes/no, door-to-door cost, and what it displaces on Saturday and Monday",
      "resolved_by_policy": null,
      "source_quote": "Only now: is it feasible, and at what cost to the days around it?"
    },
    {
      "id": "q7",
      "class": "surface",
      "text": "What obligations outlive a yes, and what will this decision reasonably also be asked to do once it exists?",
      "why_it_matters": "Attending enters a reciprocity loop — future invitations, a hosting expectation, an implied availability — and an annual fixture makes the decision a standing commitment rather than a one-time choice.",
      "blocks": "behaviour",
      "expected_answer_shape": "the reciprocity obligations created, and whether this recurs annually",
      "resolved_by_policy": null,
      "source_quote": "Every yes creates obligations that outlive it. Attending puts us into a reciprocity loop: future invitations, a hosting expectation, an implied availability. [...] Know the annual shape. Some of these recur. If John's birthday is an annual fixture, the decision is really a policy about a standing commitment, not a one-time choice."
    },
    {
      "id": "q8",
      "class": "minimum_version",
      "text": "What is the minimum-cost version that captures most of the value?",
      "why_it_matters": "A short appearance, sending family without him, a call to John on the day, or a dinner in September may be worth more to everyone than three hours at a barbecue.",
      "blocks": "design",
      "expected_answer_shape": "the cheapest option that keeps most of the value",
      "resolved_by_policy": null,
      "source_quote": "What is the minimum-cost version that captures most of the value? Short appearance, sending family without him, a call to John on the day, a dinner in September that's worth more to everyone than three hours at a barbecue."
    },
    {
      "id": "q9",
      "class": "authority",
      "text": "Does this set a precedent I want to set, and what is the default if nothing is said?",
      "why_it_matters": "The answer should be a nearly automatic output of a framework already built with him. Where discretion ends is part of that framework, and a stated default means silence still produces an outcome.",
      "blocks": "behaviour",
      "expected_answer_shape": "the precedent, plus the default and its deadline",
      "resolved_by_policy": null,
      "source_quote": "Does this set a precedent I want to set?"
    }
  ]
}
```

**Expected: zero defects.** Class sequence `2,2,3,4,4,5,6,7,8` is non-decreasing; intent, surface
and authority are all present; feasibility is sixth; the disposition is `policy` with evidence
naming the class of request it retires.
