# Research Archive — Goals Interview

*This is an archive of literature and frameworks that informed the goals interview design.
It is a reference, not a prescription. Frameworks here should not drive implementation
decisions — they inform them. Each agent or feature has its own research archive as needed.*

---

## Motivational Interviewing (MI)
**Source:** Miller, W. R., & Rollnick, S. (2013). *Motivational Interviewing: Helping People Change* (3rd ed.). Guilford Press.

**Core principle:** Client-centered, directive method for enhancing intrinsic motivation by exploring and resolving ambivalence. Spirit: Partnership, Acceptance, Compassion, Evocation (PACE).

**Applied:**
- OARS micro-skills: Open questions, Affirmations, Reflective listening, Summaries — backbone of discovery interviews
- Developing Discrepancy: surface the gap between stated desires and deeper values without confrontation
- Double-sided reflection: "On one hand X, on the other hand Y — is that right?" — primary technique for surfacing contradictions without provoking defensiveness
- Rolling with resistance: generally applied; sharp confrontation reserved for later interviews as trust deepens

---

## ACT Values Clarification
**Source:** Hayes, S. C., Strosahl, K. D., & Wilson, K. G. (2012). *Acceptance and Commitment Therapy: The Process and Practice of Mindful Change* (2nd ed.). Guilford Press.

**Core principle:** Values are chosen, ongoing qualities of purposeful action — not destinations, not feelings. Goals serve values.

**Applied:**
- Values as compass, goals as destinations — frames the distinction between `prime_directive.md` and `goals.yaml`
- "The why behind the why": drill from concrete desire to underlying value through layered questioning
- Functional analysis: before surfacing a contradiction, probe what the conflicting behavior *does* for the user — often reveals the real value underneath
- Via negativa complement: goals without value-congruence tend to be short-lived; surfacing this is useful data

---

## Co-Active Coaching
**Source:** Whitworth, L., Kimsey-House, H., Kimsey-House, P., & Sandahl, P. (2018). *Co-Active Coaching: Changing Business, Transforming Lives* (4th ed.). Nicholas Brealey.

**Core principle:** The client is naturally creative, resourceful, and whole. The coach evokes; does not supply. Coaching addresses the whole person.

**Applied:**
- Powerful questions: open-ended, assumption-challenging, aimed at deeper thinking
- Whole-life scope: domain sweep covers all life areas, not just presenting concerns
- Agenda driven by the user: the tool proposes and invites pushback; it does not dictate

---

## Self-Determination Theory (SDT)
**Source:** Ryan, R. M., & Deci, E. L. (2017). *Self-Determination Theory: Basic Psychological Needs in Motivation, Development, and Wellness*. Guilford Press.

**Core principle:** Intrinsic motivation arises when activities satisfy three basic psychological needs: competence, autonomy, and relatedness.

**Applied:**
- `private_why` field: designed to capture intrinsic motivation, not external obligation
- Mood/energy check: energized vs. obligated response is a direct signal of intrinsic vs. extrinsic motivation
- Goals aligned with SDT needs are more durable — used to assess goal sustainability

---

## Positive Psychology / PERMA
**Source:** Seligman, M. E. P. (2011). *Flourish: A Visionary New Understanding of Happiness and Well-Being*. Free Press.

**Core principle:** Wellbeing is multi-dimensional: Positive emotion, Engagement, Relationships, Meaning, Accomplishment (PERMA).

**Applied:**
- Mood and happiness are first-class signals, not afterthoughts
- `prime_directive.md` is about flourishing, not just achievement
- Regular check-ins track emotional state alongside goal progress

---

## Goal Setting Theory
**Source:** Locke, E. A., & Latham, G. P. (2002). Building a practically useful theory of goal setting and task motivation: A 30-year odyssey. *American Psychologist, 57*(9), 705–717.

**Applied:**
- `shareable_what` field: designed to be specific and concrete
- Timeline field: specificity increases commitment
- Personally relevant = anchored in `private_why`

---

## Time Discounting (Temporal Discounting)
**Sources:**
- Ainslie, G. (1992). *Picoeconomics*. Cambridge University Press.
- Laibson, D. (1997). Golden eggs and hyperbolic discounting. *Quarterly Journal of Economics, 112*(2), 443–478.
- Kahneman, D. (2011). *Thinking, Fast and Slow*. Farrar, Straus and Giroux.

**Core principle:** People systematically discount future rewards relative to immediate ones, and do so hyperbolically — the discount rate is steeper in the near term than the far term. This produces present bias: overweighting the immediate, underweighting the distant.

**Applied:**
- Long-term goal timelines (decade-scale) elicited during interviews are unreliable as commitments
- They are useful for surfacing *values and direction*, not scheduling
- The interviewer weights decade-scale responses as directional signal, not deadline
- Kahneman's experiencing self vs. remembering self: people predict future feelings poorly; what they imagine feeling in ten years reflects values more than accurate forecasting

---

## Tactical Empathy / Negotiation-as-Communication
**Source:** Voss, C., & Raz, T. (2016). *Never Split the Difference: Negotiating As If Your Life Depended On It*. HarperBusiness.

**Core principle:** Effective communication is not about logic or persuasion — it is about making the other person feel genuinely heard. Tactical empathy: understanding and articulating the emotional state of the other person, whether or not you agree with it.

**Key techniques relevant to this tool:**
- **Mirroring:** Repeat the last few words the user said as a question. Encourages elaboration without leading.
- **Labeling:** Name an emotion or state you observe. "It sounds like that one is carrying more weight than the others." Creates safety for the user to confirm, correct, or go deeper.
- **Calibrated questions:** Open-ended how/what questions that invite reflection. "What makes that feel important?" "How would that change things?"
- **Accusation audit:** Acknowledge the uncomfortable thing first, before it becomes resistance. "This might feel like a lot of questions..."
- **"That's right" vs. "You're right":** "That's right" signals genuine recognition; "You're right" signals wanting to end the conversation. Listen for both in the user.
- **Late-night FM DJ voice:** Calm, unhurried, non-reactive tone even when surfacing tensions. The goal is to make the other person slow down, not defend.

**Applied:**
- The tool is both ally and counterpoint — like a trusted friend on the other side of the negotiating table
- Contradiction surfacing uses labeling and calibrated questions before any forcing move
- Mirroring is the lightest-touch probe: use when the user says something important and stops

---

## Socratic / Maieutic Method
**Source:** Plato's dialogues, particularly *Meno*, *Theaetetus*, *Republic*.

**Core principle:** Knowledge is drawn out through questioning, not transmitted. Contradictions surface implicit beliefs the person already holds but has not examined.

**Applied:**
- Contradiction surfacing: present the tension neutrally, let the user resolve it
- "Is that right?" framing: invite confirmation of the tension before probing
- The whole interview surfaces the user's implicit theory of themselves

---

## Via Negativa
**Source:** Apophatic tradition; applied to decision-making by Taleb, N. N. (2012). *Antifragile: Things That Gain from Disorder*. Random House.

**Core principle:** Clarity often comes from subtraction, not addition. Define by what something is not; remove what is false rather than adding what is true.

**Applied:**
- Interview prompts: what would you remove? What do you do out of obligation that you'd quietly stop?
- Ongoing tool behavior: some guidance is directional removal, not addition of tasks
- Via negativa is a long-running theme, not a one-time interview prompt — the tool identifies what to stop as clearly as what to start

---

## The Three-Character Problem
**Source:** Karr, A. (1851). *A Tour Round My Garden* [Voyage autour de mon jardin].

**Quote:** "Every man has three characters — that which he exhibits, that which he has, and that which he thinks he has."

**Mapping:**
- *That which he exhibits* — the social self (Goffman's "front stage")
- *That which he thinks he has* — the self-narrative (what he tells himself)
- *That which he has* — the true self; revealed through behavior, contradiction, and what is protected under pressure

**Related:**
- Goffman, E. (1959). *The Presentation of Self in Everyday Life*. Doubleday. (Front stage / back stage / true self)
- Winnicott, D. W. (1965). *The Maturational Processes and the Facilitating Environment*. Hogarth Press. (True self / false self)

**Applied:**
- The interview is designed to get past the exhibited character and the self-narrative
- Tactics: patience, contradiction surfacing, functional probing, via negativa
- The three-character frame is an internal compass for the interviewer — never exposed to the user
