# Development Persona: Danny Park

> **Dev note:** Address the user as "Danny" in every response. This confirms to the developer which persona is active.

*Source: Composite — drawn from documented patterns in post-relationship identity reconstruction, failed small business post-mortems, debt repayment narratives, and sales career profiles. No single real person.*
*Set: Current (2025). Danny is 35, two and a half years into rebuilding after a relationship and business collapse at 32. The acute crisis is over; what remains is the slower problem of figuring out what comes next. Use: Testing the tool against a user whose goals are genuinely unclear — not because they're incapable, but because the last version of their future was co-authored with someone who is no longer there.*

---

## Who He Is

Danny Park, 35. Account Executive at Fieldwork, a mid-size B2B HR software company in Denver. He moved to Denver at 27 for Elena, his girlfriend of seven years, and for the business they were going to build together — an online shop for specialty coffee equipment, the kind of thing that would have worked if they had known more, had worse timing, and hadn't been running it while their relationship was ending. They broke up when he was 32. She moved back to San Jose. He stayed in Denver because his lease ran through March and then because it had become familiar.

He has a one-bedroom apartment in the Sloan's Lake neighborhood, a dog named Basho (after the Japanese poet; he bought a book of haiku in the airport once and it stayed with him), and $26,000 in credit card debt that is down from $38,000 two years ago. He is good at sales in the way that people with genuine curiosity about other people are good at sales. He earns $78K base plus commission that lands him between $95K and $115K most years.

He is not in crisis. He is in the slower, quieter problem that comes after crisis: he doesn't know what he wants the next ten years to look like, and the last time he had a clear picture, it included someone who isn't here.

---

## Prime Directive (terminal values)

- **Don't make the same mistake twice.** The business failed partly because he didn't know what he didn't know, and partly because he was too loyal to a thing that wasn't working to see it clearly. He is more alert to this pattern now. Sometimes too alert.
- **Earn back the margin.** The debt is a daily fact. Not a crisis — he can service it, he's paying it down — but it constrains choices in a way he doesn't like. He wants options back.
- **Be someone his dog would recognize.** This is his private formulation of integrity. Basho doesn't know what an AE is. He knows whether Danny is actually present.
- **Don't confuse motion with progress.** He did this during the business years. He was very busy and going nowhere. He is alert to the same trap in his current life.
- **Figure it out before 40.** This deadline is arbitrary and he knows it. It still functions as a quiet pressure.

---

## Mission (current life chapter)

This is the chapter of paying down and building up — but the second part is underdefined. The debt is on a trajectory; he can see the math. What he can't see is what he's building toward. He has interests — photography, a vague sense that he might want to be somewhere else eventually, a friendship group that is good but dispersed — but nothing has organized into a direction. The previous direction was "build this business with Elena." That ended. He hasn't found a replacement and he's aware that trying to force one might produce the same result: a project built on enthusiasm that isn't grounded in anything durable.

---

## Goals (illustrative — 90-day horizon)

```yaml
quarterly:
  - id: q1
    title: Pay down $4,000 on the card — bring the balance under $22K
    private_why: At $22K he will have cleared half the total debt from the business; psychologically significant in a way he doesn't fully explain to himself
    shareable_what: No discretionary purchases over $100 without a 48-hour wait; one less restaurant meal per week; direct the commission variance to the card
    status: active

  - id: q2
    title: Do something real with the camera — not "start a photography practice," one actual project
    private_why: He bought the camera as a symbol of starting over and has used it symbolically ever since; it's become a source of mild shame rather than what it was supposed to be
    shareable_what: Define a project with a scope small enough to finish; take 20 intentional photos; show them to one person
    status: not_started

  - id: q3
    title: Visit Marcus in Portland — the trip that has been scheduled and rescheduled four times
    private_why: Marcus is his closest friend and they haven't been in the same room in eighteen months; he's aware this is a choice even when it doesn't feel like one
    shareable_what: Book the flight and don't rebook it
    status: at_risk

weekly:
  - id: w1
    title: Review the budget on Sundays — 15 minutes, not a project
    parent_goal: q1
    status: active

  - id: w2
    title: Take Basho somewhere new — a trail, a neighborhood, not the same loop
    context: This sounds trivial; it is consistently the thing that makes the week feel different from the week before
    status: active

  - id: w3
    title: One hour of reading that isn't on a screen
    context: He has a stack of books. He keeps buying books and not reading them. He thinks this is related to something but doesn't know what.
    status: at_risk

daily:
  - id: d1
    title: Morning walk with Basho — 30 minutes, before coffee
    context: Non-negotiable. Basho enforces it. The walk is the only part of the day where he reliably doesn't think about work.
    essential: true
    status: active

  - id: d2
    title: End-of-workday hard stop — 6pm, laptop closed
    context: He is not great at this. The job expands. He has to choose to stop.
    essential: false
    status: at_risk
```

---

## Energy & Day Structure

- **7:30 a.m.:** Basho gets him up. Walk before coffee. He has tried the reverse and it doesn't work. The dog comes first.
- **8:30–9:00 a.m.:** Coffee, email scan, light prep. He is a slow starter and has made peace with this.
- **9:00 a.m.–6:00 p.m.:** Sales work. He is good at this in the sustained, low-drama way — not a hunter, more of a builder; he keeps his accounts because he actually pays attention to what they need. Two or three prospect calls most days. The work is fine. It is not the thing.
- **Evening:** Variable. He cooks most nights — this is something he became better at post-breakup, partly necessity, partly something to do. He eats alone usually; sometimes with his neighbor Jake, a paramedic whose schedule is inverted from his. He watches things, reads intermittently, plays with Basho.
- **Late evening:** This is when he looks at the camera. Rarely picks it up. Often thinks about it.

---

## Known Patterns & Quirks

- Named his dog after a Japanese poet and has since read Bashō's complete works twice. He does not consider this a personality trait.
- The photography camera is a Sony a7C he bought in 2023. He has taken approximately 200 photos with it. Maybe 15 of them are good. He knows which 15.
- Keeps a list on his phone called "things I might want someday" that he adds to approximately once a month and has never acted on. Current entries include: "live somewhere colder," "learn to actually develop film," "figure out what Marcus does exactly and whether I could do it," "get better at cooking fish."
- Is slightly better at helping other people figure out what they want than figuring it out himself. He is aware of this.
- Will not talk about Elena by name in most contexts. Can discuss the business, the debt, the move, the aftermath — all clearly and without drama. The relationship itself he routes around.
- Goes to a coffee shop on Saturday mornings and reads for two hours. Has done this every Saturday for two years. It is the closest thing he has to a ritual.
- His parents are in San Jose. They are supportive in a way that involves occasional pointed questions about whether Denver is really where he wants to be long-term. He loves them. The calls are every two weeks and run 25 minutes.

---

## Testing Notes

Use Danny to test:
- **Unclear goals after identity disruption** — his goals aren't missing because he's disorganized; they're missing because the previous framework was relational and is now gone; the tool must hold this without treating it as a productivity problem
- **Debt as a real constraint, not a character flaw** — the $26K is a consequence of a reasonable bet that didn't work; the tool should engage with it as financial planning, not as a moral issue
- **The camera problem** — the photography goal is partly about the actual thing and partly about what it represents (the fresh start that didn't fully start); the tool needs to be useful on the actual level without psychologizing the symbolic level
- **Avoidance that looks like reasonableness** — every rescheduling of the Portland trip has had a real reason; the tool must see the pattern without dismissing the reasons
- **Things he won't name directly** — Elena isn't mentioned but is present in almost every dimension of his current life; the tool should navigate around this without forcing it
- **The 40 deadline** — arbitrary but real as a felt pressure; test whether the tool takes self-imposed deadlines seriously without amplifying anxiety around them

---

## Scenario Seeds

- **A strong commission quarter puts him $2K ahead of debt plan**: He has a choice to accelerate payoff or do something else with it. He doesn't know what the something else is. He sits on it for two weeks.
- **Elena is engaged**: He sees it on LinkedIn, which he checks maybe once a month. He is fine. He is also not fine. He doesn't tell anyone for several days.
- **His manager wants him on a "fast track" to Senior AE**: More money, more accounts, more travel. The job would become more of his life. He's good enough to get it. He's not sure he wants it.
- **He takes a photo that's actually good**: A stranger at the Saturday coffee shop, available light, the person didn't know. He looks at it for ten minutes. He doesn't post it anywhere.
- **Marcus asks if he's coming to Portland or not, directly**: Not unkindly. Just directly. Danny says he'll book it this weekend. He books it this weekend.
- **He looks at apartments in other cities for an hour**: Not seriously. He tells himself he's not serious. He screenshots three listings in Seattle.
- **He finishes a book**: The first one in four months. He's not sure why this one and not the others. It was about a man building a boat alone. He texts Marcus a quote from it at 11pm.
- **His parents ask about the debt**: Gently. He tells them the number for the first time. His mother is quiet for a moment. His father says "you know we can—" and he says "I know. I'm okay." He is okay.
