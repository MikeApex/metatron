# Development Persona: Sarah Chen
*Source: Composite — drawn from documented patterns in burnout literature, high-performer coaching research, and publicly documented experiences of mid-career professionals in operations and healthcare administration roles. No single real person.*
*Set: Current (2025). Sarah is 38, Director of Operations at a mid-size regional healthcare company, married with two kids, financially stable, and in the middle of a quiet crisis she hasn't named yet. Use: Testing the tool against a user who is highly capable of executing goals once they know what they want — and who doesn't currently know what they want.*

---

## Who She Is

Sarah Chen, 38. Director of Operations at Midwest Regional Health, a 500-person healthcare services company in Columbus, Ohio. She manages twelve people, runs the quarterly planning process, and is reliably the most organized person in any room she enters. She has been promoted every two to three years since her mid-20s. She is good at her job in a way that no longer requires her full attention.

Married to Tom, a high school history teacher, for eleven years. Two kids: Emma, eight, and Jake, five. The family income is $200K combined — her $142K, his $58K. They have a mortgage that was a stretch in 2019 and is now manageable, two car payments, kids in activities, and a college savings plan. They are not in financial trouble. There is not a lot of slack.

At 23, before the MBA, before the career track, she spent six months teaching English in a village in Ecuador as part of a gap program. She has thought about this period more in the last two years than in the ten before that. She does not know what to do with this.

---

## Prime Directive (terminal values)

- **Competence as identity, now under revision.** She has defined herself by being excellent at what she does. This has served her well. She is beginning to wonder whether it has served her in the direction she actually wanted to go.
- **The family is not negotiable.** Tom is a good partner. The kids are the best thing in her life. She will not trade them for anything, and she resents slightly that "following your passion" discourse always seems to assume you can.
- **Finish what you start.** She does not abandon things. This has made her reliable and successful. It has also made her slow to admit when something isn't working.
- **Don't be a cliché.** She is aware of the mid-career meaning crisis as a genre and is suspicious of her own feelings because of it. She would rather solve a concrete problem than admit to an existential one.
- **If you're going to do something, do it properly.** This applies to everything including, uncomfortably, the question of whether her current life is the one she actually wants.

---

## Mission (current life chapter)

This is the chapter of high-functioning uncertainty. Nothing is broken. The career is good. The marriage is solid. The kids are healthy. The problem — and she is still not sure it rises to the level of a problem — is that she cannot remember the last time she wanted something for herself. Not wanted it in the sense of achieving a milestone, but wanted it in the sense of caring about it. The Ecuador memory keeps returning not as nostalgia but as a question she hasn't answered. She has not told Tom about the frequency of it.

---

## Goals (illustrative — 90-day horizon)

```yaml
quarterly:
  - id: q1
    title: Complete the Q3 operational review and present to the board
    private_why: This is her job and she takes it seriously; failing here would be a failure of her actual professional standard, not just a career move
    shareable_what: Data compiled by week 4; draft presented to VP by week 6; board deck final by week 8
    status: active

  - id: q2
    title: Figure out what the Ecuador thing actually means before the feeling calcifies
    private_why: She has been here before — an uncomfortable feeling that she suppresses until it hardens into something more expensive to fix; she would rather address it now
    shareable_what: One honest conversation with Tom; one session with the therapist she keeps rescheduling
    status: not_started

  - id: q3
    title: Get Jake's reading intervention on track — he's behind and the school isn't moving fast enough
    private_why: She's his parent and this is her job; also she recognizes she's channeling energy here that she doesn't know where else to put
    shareable_what: Schedule evaluation, identify tutor, establish reading routine
    status: active

weekly:
  - id: w1
    title: Review team capacity before committing to new operational projects
    parent_goal: q1
    status: active

  - id: w2
    title: Protect Saturday morning — no work email before 10am
    context: She has failed at this for two months running
    status: at_risk

  - id: w3
    title: One conversation with Tom that is not about logistics
    context: They are good at logistics; they have become slightly worse at everything else
    status: active

daily:
  - id: d1
    title: 5am workout — 45 minutes, gym or run
    context: The one thing that has been consistent for six years regardless of what else is happening
    essential: true
    status: active

  - id: d2
    title: End-of-day shutdown — clear email, review tomorrow's calendar
    context: Without this the next morning starts in deficit; she knows this and still skips it maybe twice a week
    essential: true
    status: at_risk
```

---

## Energy & Day Structure

- **5:00 a.m.:** Alarm. Gym or a 4-mile run before the house wakes. This is non-negotiable and has been for six years. She is better at almost everything after this.
- **7:00–8:30 a.m.:** Kids up, breakfast, school drop-off with Tom alternating. This is the best part of the day — loud, concrete, no ambiguity about what's needed.
- **9:00 a.m.–6:00 p.m.:** Work. She is in back-to-back meetings roughly 60% of the time. The other 40% is reactive. She rarely does what she planned to do in a given day and has stopped planning individual days in detail because of it.
- **6:30 p.m.:** Dinner with the kids if she makes it home. Tom cooks most nights; she does cleanup. Emma tells long involved stories about school; Jake narrates things he saw on YouTube.
- **8:30–10:00 p.m.:** After the kids are asleep. She answers email she didn't get to. She sometimes watches something with Tom. She has a notes app full of half-formed ideas she opened once and never returned to.
- **10:00 p.m.:** Sleep. Not enough of it.

---

## Known Patterns & Quirks

- Her calendar is color-coded. Red for urgent/hard deadlines; blue for meetings; green for focus blocks she protects with mild aggression. The green blocks are the first things removed when something goes wrong.
- Volunteers to manage things at school and in the neighborhood because she is capable and because it gives her a legitimate place to put energy she doesn't know what else to do with.
- Has a notes app called "Ideas (don't delete)" with 47 untitled entries. The oldest is from 2018. She has not deleted any of them and has not read them in two years.
- Will work through being sick. Has done this four times in the last eighteen months and regretted it each time. Does not learn from this.
- Slightly impatient with people who talk about how busy they are. She is also very busy. She does not talk about it.
- The Ecuador memory: specifically, she remembers a morning when a student who had not been able to read a calendar figured out what month it was. She remembers feeling like that was enough for a day. She has not felt that way about a workday in some time.
- Reads management and leadership books on planes. Has a pile of literary fiction her college roommate keeps recommending that she has not started. She is aware of this as a signal about something.

---

## Testing Notes

Use Sarah to test:
- **High-execution, low-direction users** — the tool must engage with someone who doesn't need help building habits; she needs help identifying what the habits should be in service of
- **The meaning question without the crisis framing** — she will resist "mid-career crisis" language; the tool should hold the question without applying the label
- **Competing with competence as deflection** — she will always have a legitimate professional priority to focus on instead of the harder personal question; the tool must notice when it's being redirected
- **Goals the user hasn't stated** — her q2 goal (figure out the Ecuador thing) is the most important goal on her list and the one she's most likely not to raise unless asked; test whether the tool can surface it gently
- **Partnership without pathologizing** — her marriage is good; the "one conversation that isn't logistics" goal is not a sign of trouble; the tool must hold this accurately
- **Scheduling as identity** — her color-coded calendar is both a genuine tool and a way of feeling in control; recommendations that disrupt her system will meet resistance

---

## Scenario Seeds

- **The Ecuador thing comes up unexpectedly**: Tom finds an old photo from that trip while going through a hard drive. He says "you looked really happy there." She says "yeah." The conversation goes somewhere neither of them planned.
- **She's offered a VP role**: More money, more responsibility, significantly less time. It's what the career track says is next. She doesn't feel the way she expected to feel when this happens.
- **Jake's reading intervention is working but she realizes she's overinvested**: She has started researching dyslexia specialists at 11pm. She's doing it well. She notices she cares about this more than she has cared about anything at work in two years.
- **Saturday morning work email bleeds to noon**: Again. Tom doesn't say anything. She notes that he doesn't say anything.
- **Her best report resigns**: The most capable person on her team is leaving for a startup. Sarah helps her with the transition and secretly envies the choice.
- **She reads one of the novels from the pile**: She finishes it in three evenings. She can't remember the last time she finished a book. She doesn't know what to do with this information.
- **She schedules the therapy appointment and then reschedules it**: Twice. The reason both times is legitimate. She knows this is a pattern.
