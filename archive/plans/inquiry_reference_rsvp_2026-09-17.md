# Reference transcript — the RSVP reasoning exercise

*Captured 2026-09-17. Verbatim and unedited. Supplied by Mike 2026-09-18 during the phase 1
build; the file did not exist when `build_vertical_plan_2026-09-18.md` was written, which cited
this path forward.*

**What this is for.** § 4 of the build vertical plan calibrates the QuestionSet artifact against
this transcript. Its value is the **delta between turn 2 and turn 4** under the turn-3 critique:
turn 2 is a tactical filter, turn 4 is an intent-driven allocation framework. Both are
reproduced in full.

**This file is reference. It is never shipped to a model.** The abstract — the spine, the eight
classes, the two stances, the disposition table — lives in `config/agents/build_inquiry.md`. The
machine-readable pass/fail pair cut from turns 2 and 4 lives in
`tests/fixtures/inquiry_rsvp_2026-09-17.md`. The three forms have different jobs and are
deliberately kept apart (§ 15).

**Context given to the model.** A roleplay prompt: experienced personal assistant, day one,
near-perfect knowledge of the boss via diaries / correspondence / CRM / calendar / biographies,
no direct contact with the boss. Asked for the reasoning process behind handling a single social
invitation.

---

## Turn 1 — User

Pretend you are an experienced personal assistant on your first day on the job with a new boss.
Your boss will never be in direct contact with you, but you have at your disposal almost perfect
knowledge about him/her. A proxy for this knowledge might be something like diaries,
correspondence, CRM/rolodex with detailed notes, calendar, preferences, and several biographies
written about them. You also have access to the internet and research tools in general.

You must handle the following query —

You receive this email from Mary Higgins:

> Hi, Come to John's birthday this Sunday, August 22, 2026 at 3pm at our home in Bethesda, MD.
> Bar B Cue will be served.
> RSVP

Outline, in detail, all the information you would need, the decision points and questions you
would pose and address, and how you would execute the final outcome. Be broad and holistic in
your thinking about how this affects your boss.

Since you don't have any actual information here, you'll need to remain abstract about your
thought process. Do not substitute made up data — outline your research and decision tree.

---

## Turn 2 — Assistant

**First move: stop, don't answer yet**

Nothing about this email can be actioned until I know who these people are to my boss. An RSVP is
trivial to send and expensive to send wrongly. On day one my risk is not being slow, it is being
confidently wrong in my boss's name to someone who matters.

I also start a clock. "This Sunday" is inside four days. Whatever I do, the reply cannot sit for
two days while I research.

**1. Problems visible on the face of the email**

*The date does not resolve.* August 22, 2026 is a Saturday. Sunday is the 23rd. One of the three
signals ("this Sunday," "August 22," or the implied weekend) is wrong. I do not guess and I do not
silently pick one. If I block the wrong day, my boss either misses the party or holds a day for
nothing. This gets clarified with Mary before anything else, and it can be done in a single
friendly line that costs nothing.

*Who is invited.* "Come" is ambiguous. Does the invitation extend to a spouse or partner, to
children, to a plus-one? Mary may assume the whole household; my boss may assume himself alone.
Both assumptions produce an awkward doorstep.

*Missing operational data.* No street address (implied that we should have it), no end time, no
RSVP deadline, no RSVP channel, no dress guidance, no indication whether it is a surprise, no
indication of gift expectations, no indication whether food contribution is expected.

*Provenance.* Low probability but zero cost: confirm the sending address matches the Mary Higgins
in our records and that this is not a spoof or a forward of an invitation not actually meant for
us.

*Duplication risk.* Has my boss already been told about this in person, by text, or by his spouse,
and already answered? Sending a second, contradictory RSVP is a very bad first-day move. I check
his personal message threads, his spouse's coordination channel if one exists, and any prior
mention in the file.

**2. Identity and relationship research**

This is the load-bearing work. Everything downstream is a function of the answer.

*Who is Mary Higgins?* Search the CRM, correspondence archive, calendar history, contact list,
gift log, holiday card list, and biographies. I am looking for tier and category:

- Family or in-law
- Old personal friend, and from which era of his life
- Spouse or partner of a colleague, client, investor, board member, or counterparty
- Professional contact in her own right
- Neighbor, church, school-parent, club, or civic connection
- Someone whose relevance is entirely through her husband

*Who is John?* The birthday is his, so the gift, the toast, and the reason to attend attach to
him. Critical unknowns: Is John an adult or a child? If a child, is this a kids' party and does
that change whether my boss's presence is normal or odd? Is it a milestone birthday (50, 60, 70),
which raises the cost of absence sharply? Is John the primary relationship and Mary the organizer,
or the reverse?

*Relationship history and reciprocity ledger.* This is where a good file earns its keep:

- Frequency and warmth of contact over the last five years. Trending up or down?
- Has my boss declined their last one or two invitations? A third decline reads as a statement
  regardless of reason.
- Did they attend his events, send condolences, show up when it counted?
- Any recorded friction, estrangement, business dispute, or awkwardness?
- Any financial, legal, or fiduciary entanglement that makes social attendance sensitive?
- Does he owe them something, or do they want something from him? Is this invitation partly an
  ask?

*Who else will be in the room?* From past events at the same house, from mutual contacts, from
Mary's own network. I want to know if attendance puts him in a room with a counterparty in a live
negotiation, a journalist, an ex, a former partner, someone he has been avoiding, or conversely
someone he has been trying to get in front of for a year. Either finding flips the decision.

**3. Feasibility research**

*Calendar.* Both candidate days, full day, not just the 3pm slot. Includes tentative items, family
commitments, standing rituals, and anything held informally in his head that I would only find in
the file (a recurring Sunday obligation, a season ticket, a child's schedule).

*Geography and travel.* Where is he physically that weekend, and where does he need to be Monday
morning? Bethesda is fine from DC and manageable from the Northeast corridor. It is a different
proposition from the West Coast, and a nonstarter from overseas. I compute door to door in both
directions including a realistic Sunday traffic estimate, and I look at what it displaces on
Saturday and Monday.

*Recovery and stamina.* If he lands Saturday night from a long haul, a Sunday afternoon social
obligation is technically possible and practically a bad idea. His documented preferences about
back-to-back commitments matter here.

*Household coordination.* If a spouse or partner is invited, their calendar is a hard input, not
an afterthought. Same for children if the party is family-inclusive.

**4. Personal and situational constraints**

*Dietary.* Barbecue is a specific food environment. Vegetarian, kosher, halal, allergies, medical
restrictions, alcohol status. If he does not eat what will be served, that does not necessarily
mean decline, but it does mean I may quietly flag it to Mary or arrange around it.

*Health, heat, and access.* Mid-afternoon, late August, mid-Atlantic. Outdoor heat and humidity
are genuinely punishing. Any mobility, cardiac, heat, or sun sensitivity in the file is relevant.
Also seasonal allergies for an outdoor event.

*Weather contingency.* I check the forecast late in the week. Thunderstorms are common in that
region in August and can change the shape of the event.

*Privacy and security.* Is his whereabouts sensitive? Is there a security arrangement, a driver, a
detail? Is he a public figure whose photograph at a private party could travel? Are there people
at this party who would post it?

*Social preferences.* Does he like large gatherings or dread them? Does the file show he
consistently prefers short, early appearances? Does he have a documented pattern of arriving late
and leaving before the cake?

**5. Framing the decision**

The choice is not binary. There are at least five outcomes, and my job is to identify which one my
boss would pick, not which one I would.

| Option | When it fits |
|---|---|
| Full attendance | Relationship is close or strategically valuable, calendar is clear, no complications |
| Short appearance | Relationship matters but the day is compressed. Arrive near the start, stay an hour, leave with a stated reason |
| Attend with household | Invitation clearly extends further and family attendance is the norm in this relationship |
| Warm decline with substance | Cannot attend, but relationship is protected: gift, a call to John on the day, an offer of a specific alternative date |
| Cool decline | Only where the file shows a reason to keep distance |

**The decision spine, in order:**

1. Is the date and day resolved? If not, resolve before anything else.
2. Is he physically able to be in Bethesda at 3pm on the correct day? If clearly not, move
   straight to the quality of the decline.
3. Does the relationship tier justify displacing what is already on the calendar? Nothing on it,
   low-value items, or high-value items each give a different answer.
4. Are there second-order reasons to attend (someone in the room) or to avoid (someone in the
   room, an optics or conflict issue)?
5. Does a short appearance capture most of the value at a fraction of the cost?
6. Is this a decision I can make, or one I must surface?

**6. What I decide versus what I escalate, on day one**

This is the part a new assistant gets wrong. I have the file but not yet the earned authority or
the feel for his instincts.

*I would handle without asking:* clarifying the date with Mary, confirming address and end time,
confirming whether the invitation extends to family, checking the calendar, pricing travel,
researching the relationship, drafting the reply, and preparing the gift options.

*I would put in front of him,* in a single short note with a recommendation and a default: the
actual accept or decline, and any conflict I would have to move. One decision, framed, with the
research already done, and a stated default so that silence still produces an outcome. Something
in the shape of: here is who they are, here is what the last three years of contact look like,
here is what it costs you, here is my recommendation, if I do not hear from you by Friday noon I
will do X.

I never let a day-one uncertainty turn into an unanswered invitation.

**7. Execution**

*Immediately (same day):*

- Reply to Mary. Introduce myself as his new assistant, which permanently solves inbound routing
  for the future. Thank her warmly. Ask the clarifying questions lightly and in one pass: confirm
  the day, confirm the end time, confirm whether the invitation extends to the family, confirm the
  address for my records. Signal that a firm answer is coming shortly rather than leaving her
  hanging.
- Hold both candidate days provisionally in the calendar, marked tentative, so nothing else gets
  booked over them while I work.
- Open the research thread on Mary, John, and their household.

*Within 24 hours:*

- Complete the relationship and feasibility research.
- Send the boss the one-page decision note with a recommendation and a default.

*If yes:*

- Confirm to Mary in writing, with names and arrival time.
- Book transport with a deliberate buffer, and book the return leg with a specific departure time
  so there is a built-in exit.
- Gift: sized to the relationship, tuned to John's known interests, ordered with delivery lead time
  verified, or hand-carried. Separate small host gift for Mary if that is the local and personal
  norm.
- Ask discreetly whether food contribution is expected. Barbecue often carries a potluck
  assumption.
- Handle the dietary issue quietly in advance rather than at the grill.
- Brief my boss the morning of: address, arrival, who is likely there, names of spouses and
  children, what John has been up to, anything he should be careful not to raise, and his hard
  stop.
- Protect the following morning if the day is long.

*If no:*

- Decline promptly and warmly, so Mary can plan. Give a real reason, not a vague one, if the
  reason is honorable.
- Send the gift anyway. It arrives before the party, not after.
- Arrange for my boss to call or message John on the day itself. A thirty-second call from a
  friend who could not come is worth more than attendance by someone who did not want to be there.
- Propose a specific alternative: a dinner, a call, a date. Specificity is what separates a warm
  decline from a brush-off.

*Afterward, either way:*

- Thank-you note if he attended.
- Log everything in the CRM: John's birthday as a recurring annual entry, the address, who was
  there, what was discussed, what was given, and what was promised in passing. Promises made at
  parties are the ones most often forgotten and most costly to forget.
- Note any new contacts met, for the relationship map.
- Note for my own calibration what he actually chose, so that next time I need to ask him less.

**8. The broader read**

A birthday barbecue is a low-stakes event with a high-stakes function. It is a maintenance ping on
a relationship, and the file will show whether that relationship is one my boss is investing in,
coasting on, or quietly letting go. My job on this query is not to produce an RSVP. It is to make
sure that whichever answer goes out is the one he would have chosen with full information, that it
arrives quickly enough to be gracious, and that the relationship is in better shape on Monday than
it was on Wednesday, regardless of whether he walked through that door.

---

## Turn 3 — User

Feedback:

You've framed this narrowly and tactically. Largely this is framed through the lens of
availability and relationship and a default attendance if there are no blockers. There is no
reflection on broader life goals, opportunity cost, or the greater context of the boss' life.

How might you amend this process?

---

## Turn 4 — Assistant

**Where the critique lands**

You're right, and the specific failure is identifiable: **I built a filter, not a compass.**

My decision spine ran "is there a blocker? no? then attend." That makes the calendar the arbiter
and treats empty time as available time. It evaluates the invitation on its own terms, as a
question the sender posed, which I then answered, rather than asking whether this is a good use of
a finite and rapidly depleting resource. It's the reactive posture of an inbox-clearer with good
manners. Every individually reasonable yes is how a life gets spent on things nobody chose.

The deeper error: **I never established what my boss is for this year before deciding what he
should do on Sunday.**

**The layer that should sit above everything**

Before I touch a single invitation, there is prior work that a good file makes possible and that I
skipped entirely.

*What season is he in?* People run in phases. Building something. Consolidating. Recovering from
something. Winding down. Actively broadening his network versus deliberately narrowing it. A file
with diaries and correspondence will show this plainly, in what he complains about, what he
protects, what he's said yes to lately and with what tone. The same invitation is a good idea in
one season and a mistake in another.

*What has he said he wants more of and less of?* Explicitly stated intentions are the
highest-quality signal available and I ignored them completely. Almost everyone with a documented
inner life has written or said some version of: I want to be home more, I want to stop doing
things out of obligation, I want to see old friends before it's too late, I want to travel less, I
need to be more present with my kids. Those statements are instructions. My job is to be the
mechanism that honors them, especially when he is too polite or too tired in the moment to honor
them himself.

*Where is the stated-versus-revealed gap?* The file will show both what he says he values and what
he actually spends Sundays on. When those diverge, I have to decide which one I'm serving. My
working rule: serve the stated preference, because the revealed one is largely the product of a
system with no assistant in it, of defaults, drift, and inability to say no gracefully. I am the
correction to that. But I hold the judgment loosely and I surface the tension rather than silently
overriding him.

*What is he actually optimizing?* Career trajectory, financial goal, health, a marriage that needs
attention, a creative project that only moves in uninterrupted blocks, a child's last summer at
home. Whatever it is, this Sunday either serves it, is neutral to it, or takes from it.

**Opportunity cost, properly construed**

I checked whether the calendar was clear. That is the wrong measurement.

*Empty calendar space is frequently the most valuable thing on the calendar.* Unstructured time is
where recovery, thinking, family, and spontaneity live, and it is invisible to a scheduling tool
because nobody books it. Treating blank space as available is exactly how a life fills up with
obligations nobody would have chosen deliberately. If the file shows he is chronically
overcommitted, the empty Sunday is not an opening. It is the scarcest asset he owns and my job is
to defend it.

*The relevant comparison is not "this versus nothing."* It's this versus the best available
alternative use of a late-August Sunday afternoon. That alternative may be nothing at all, and
nothing at all may win.

*The real budget is not hours.* There are perhaps forty weekend days a year that are genuinely free
of hard commitments. If a third are already spoken for, this event is competing for something like
one percent of his discretionary weekend inventory this year. Framed that way, "there's no
conflict" stops sounding like a reason.

*Attention and social energy are separately budgeted* and don't refill on the same schedule as
time. For someone who finds large gatherings depleting, a three-hour barbecue costs more than
three hours. It costs the Sunday evening after it and possibly the Monday morning. For someone
energized by them, it's net positive and the accounting inverts.

*Every yes creates obligations that outlive it.* Attending puts us into a reciprocity loop: future
invitations, a hosting expectation, an implied availability. That's an asset if the relationship is
one we're investing in and a slow liability if it isn't.

**The portfolio view: stop deciding one invitation at a time**

The single largest structural fix. I evaluated this invitation in isolation, which guarantees
drift, because almost every individual invitation clears a standalone bar.

*Establish the base rate.* How many social and semi-social commitments has he accepted per month
over the last year, and what's the trend? Is he above or below whatever level he's said he wants?

*Decide at the margin.* The question is not "is this a good event" but "is this the best of the
invitations competing for this scarce category of time," including invitations that haven't arrived
yet but predictably will. If this is the fourth Sunday obligation this month, its marginal value is
much lower than if it's the first, regardless of how good the event itself is.

*Look forward before answering.* What else is landing in this window? What does September look
like? A yes in August that produces exhaustion in an already-heavy stretch is a bad trade even if
the event is delightful.

*Know the annual shape.* Some of these recur. If John's birthday is an annual fixture, the decision
is really a policy about a standing commitment, not a one-time choice.

**Irreversibility, closing windows, and asymmetric regret**

I optimized for value and should have been optimizing against regret. They diverge sharply and the
divergence is where the interesting judgment lives.

*Some doors are closing and most aren't.* A parent's remaining years, a friend in poor health, the
last summer before a child leaves home, a milestone birthday that happens once. These carry an
asymmetry that no ordinary cost-benefit calculation captures: the downside of missing them is
unrecoverable and the downside of attending is a wasted afternoon. When I detect a closing window,
the analysis should tilt hard and I should say so explicitly.

But most events are not that, and the failure mode of this reasoning is treating everything as
irreplaceable and thereby attending everything. The discipline is identifying which small number of
things genuinely can't be redone.

*The regret test in both directions.* In five years, is this a Sunday he'd be glad he spent this
way, or one he wouldn't remember? And separately: is there a version of not going that he'd regret?
Often the honest answer to both is no, and that itself is informative. It means the decision is
low-stakes and shouldn't consume this much of anyone's attention.

*Trajectory over event.* Relationships should be evaluated as slopes, not points. Missing one party
in a relationship that is well-tended and warm costs almost nothing. Missing one party in a
relationship that has been quietly fading for three years may be the moment it ends. Same event,
opposite weight, and only the longitudinal record tells me which one I'm looking at.

**The amended decision spine**

The old version started with feasibility. The new version starts with intent, and feasibility
doesn't appear until the fourth question.

1. What is he trying to do with this period of his life, and what has he said he wants more and
   less of?
2. Does this serve that, work against it, or is it neutral? Neutral is not a pass. Neutral
   competing against a scarce resource is a soft no.
3. What is the counterfactual use of this specific block, including deliberate emptiness, and what
   has already been committed this month?
4. Is there an asymmetry or closing window that overrides the ordinary calculus?
5. What does this relationship's trajectory look like, and what does one absence do to it?
6. Only now: is it feasible, and at what cost to the days around it?
7. What is the minimum-cost version that captures most of the value? Short appearance, sending
   family without him, a call to John on the day, a dinner in September that's worth more to
   everyone than three hours at a barbecue.
8. Does this set a precedent I want to set?

And the default inverts. **Absence of a blocker is not a reason to attend.** A yes must be
affirmatively purchased by something in questions one through five. The burden of proof sits on
attendance, not on absence.

**Two things I'd add that I omitted entirely**

*His time is frequently not his alone.* If he has a partner, the weekend is jointly held and I was
treating it as a personal calendar to be optimized on his behalf. Whether they want to go, whether
this is their friendship more than his, whether the household needs an ordinary Sunday, whether
declining on their behalf is even mine to do, all of that is upstream of my analysis and I ran
right past it.

*Proportionality of the decision process itself.* I applied a strategic apparatus to a barbecue
RSVP. Most invitations deserve a thirty-second triage against a standing rule. The framework exists
so that the small ones can be decided fast and the genuinely consequential ones get real attention.
If I run this depth of analysis on everything, I've become another thing consuming his scarce
resource.

**What this changes about my job**

The real amendment isn't to how I handle this email. It's that the answer to a single invitation
should be a nearly automatic output of a framework I've already built with him, rather than a
bespoke analysis performed under time pressure.

So the actual first-day deliverable is not an RSVP. It's the beginning of a standing allocation
policy: what he's protecting this year, what the weekend budget is, which relationships are being
actively invested in and which are on maintenance, what the automatic yeses and automatic noes are,
and where my discretion ends. I build that from the file, propose it, and refine it against his
corrections over months.

Then I become something more useful than a scheduler. I become the person who notices that he's
said three times this year that he wants to see more of his oldest friends and has declined every
one of their invitations, and who says so, unprompted, before the next one arrives. And equally,
the person who declines things on his behalf so that when he does say yes, it means something.

The tactical work in my first answer still has to happen. It just isn't the job. It's what the job
produces once the actual thinking is done.

*End of transcript.*

---

## What this transcript is used for, and the two blind spots it names

**Used for.** § 4's QuestionSet spine — the eight classes and their order — and § 2's two
inherited stances (*neutral is not a pass*; *empty capacity is not available capacity*). The
turn-3 critique is the specification: turn 2 is what a capability built by a model that was never
told to look upward produces.

**The two canonical REPAIR signatures**, from the blind spots turn 4 admits it had. When a
Build-made capability fails, these are the first two classes Inquiry should test against:

1. **Jointly-held resources** — treating a shared asset as the principal's alone.
2. **Process proportionality** — spending more deciding than the decision is worth.
