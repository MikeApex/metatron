# Language teacher — Build Question Set (build-inquiry), 2026-11-24

Run outside a Build job, at Mike's request, to see what a language-teacher capability would have
to answer. Inquiry works in a vacuum: it was given only the generic gap (no language, no user).
Ideas input for a future goal-driven Build (agenda: top of `build_vertical_plan_2026-09-24.md`);
not a job artifact. Effort: low (pinned in the agent file).

```json
{
 "schema": "question_set/1",
 "mode": "construct",
 "request": "Build a standing capability that acts as a language teacher for the employer's self-set, long-term goal (roughly beginner to everyday conversational level). It would assess their current level, plan stages, choose each week's practice, supply or generate material (vocabulary, dialogues, listening, spaced-repetition review), notice when they stall, and keep them moving. It has to work alongside self-study and an occasional paid tutor.",
 "depth": "deep",
 "generalizes_to": "Standing coaching for a long-term personal skill goal: an ongoing curriculum, generated material and progress monitoring for something the principal learns, done alongside a human expert.",
 "framing_note": "SPLIT. This is at least three requests wearing one coat. (a) A curriculum and assessment function: find the current level, plan stages, choose the weekly focus. (b) A material and spaced-repetition engine: make and schedule content, which is a standing data store with its own upkeep. (c) A stall-detection and nudging function that touches the calendar and the principal's attention. Each has a different cost and a different failure mode. Nudging is the one that can do the harm it exists to prevent, by turning a chosen pleasure into an obligation. The tutor already does part of (a), so the boundary with the tutor is a fourth question running across all three. The pieces should be asked about separately and could be built separately. The material engine may already exist as a tool they use.",
 "declined_to_ask": [
  "Which teaching method is best for this language: a judgement for a later stage, not a fact anyone could supply.",
  "How many hours a week they should study: a target someone would have to choose, not a fact.",
  "Whether they will reach conversational level by a given date: a prediction.",
  "What the tutor privately thinks of their progress: unknowable unless the tutor says it, which is covered by the question asking for the tutor's written feedback."
 ],
 "spine": [
  {
   "id": "q1",
   "class": "integrity",
   "text": "Which language is it, and is it named the same way everywhere it appears (diary, correspondence, calendar, tutor bookings)? Is there a regional variety or script choice (for example European or Brazilian Portuguese, Simplified or Traditional characters)?",
   "why_it_matters": "The material, listening sources and assessment scales all depend on the exact language and variety.",
   "blocks": "design",
   "expected_answer_shape": "The language name plus its variety or script, with any mismatches between sources noted."
  },
  {
   "id": "q2",
   "class": "integrity",
   "text": "Is their current level actually beginner, as described? Have they recorded any past study, courses taken, test scores or time living where the language is spoken?",
   "why_it_matters": "'Roughly beginner' may not match the record, and the starting stage depends on which is true.",
   "blocks": "design",
   "expected_answer_shape": "A list of past exposure with dates, plus any scores or certificates."
  },
  {
   "id": "q3",
   "class": "integrity",
   "text": "Does the request ask both for a teacher that 'decides' what to practise and for one that 'keeps them moving', and has the principal said anything elsewhere about wanting to direct their own learning?",
   "why_it_matters": "A teacher who directs and a learner who wants autonomy pull against each other, and a design built on either would break.",
   "blocks": "design",
   "expected_answer_shape": "Quotes or notes on whether they prefer to be directed or self-directed, specific to learning if possible."
  },
  {
   "id": "q4",
   "class": "intent",
   "text": "What is the language for? Is there a named trip, relocation, partner or family, colleagues, heritage, or a stated wish for the pleasure of it, and where is that reason written down?",
   "why_it_matters": "The purpose decides which vocabulary, scenarios and skills (speaking, reading, listening) come first, and whether there is a date.",
   "blocks": "design",
   "expected_answer_shape": "The stated reason(s) with source and date; any related event with its date."
  },
  {
   "id": "q5",
   "class": "intent",
   "text": "How have they defined 'everyday conversational' in their own words: specific situations, a framework level such as CEFR B1, or a test?",
   "why_it_matters": "The end state determines the stages and whether 'done' can be recognised.",
   "blocks": "design",
   "expected_answer_shape": "Their own definition or a named level or test, or a note that none is recorded."
  },
  {
   "id": "q6",
   "class": "intent",
   "text": "What have they said they want more of and less of in their life generally, especially about screen time, notifications, structured obligations and leisure? Does this goal sit in the 'more' list?",
   "why_it_matters": "A teacher that sends daily reviews and nudges may cut against stated wishes for less screen time or fewer obligations.",
   "blocks": "design",
   "expected_answer_shape": "Quoted statements with dates from the preferences, diary or biographies."
  },
  {
   "id": "q7",
   "class": "intent",
   "text": "What is their revealed pattern with past self-set learning goals (other languages, instruments, courses)? Were they started, sustained or dropped, and what do the diaries say about why?",
   "why_it_matters": "The stated wish and the past behaviour may diverge, and stall handling should be built on how they actually behave.",
   "blocks": "design",
   "expected_answer_shape": "A list of past goals with start and end dates and their recorded reasons for continuing or stopping."
  },
  {
   "id": "q8",
   "class": "intent",
   "text": "Have they said how they like to be held accountable, or how they react to reminders and nudges? Is there any record of them turning nudges off or resenting them?",
   "why_it_matters": "This decides whether stall detection should prompt them, report to them, or stay silent.",
   "blocks": "behaviour",
   "expected_answer_shape": "Quotes or observed instances: reminders they kept, reminders they disabled, complaints."
  },
  {
   "id": "q9",
   "class": "intent",
   "text": "Do their diaries say which parts of studying they enjoy and which they avoid (for example speaking, flashcards, grammar, listening)?",
   "why_it_matters": "Weekly choices that ignore enjoyment drive the drop-off this capability is meant to prevent.",
   "blocks": "behaviour",
   "expected_answer_shape": "Liked and disliked activities, each with source excerpts."
  },
  {
   "id": "q10",
   "class": "cost",
   "text": "How much time do they currently spend studying each week? What does the calendar record for study blocks, and how often are those blocks kept versus moved or skipped?",
   "why_it_matters": "This sets the base rate. A plan sized beyond actual practice will stall from the start.",
   "blocks": "design",
   "expected_answer_shape": "Scheduled hours per week versus attended hours over the last few months."
  },
  {
   "id": "q11",
   "class": "cost",
   "text": "How many other standing goals, habits or recurring commitments do they currently have tracked, and how many of those are being kept up?",
   "why_it_matters": "A new standing obligation competes with existing ones, and the share actually kept shows how much room there really is.",
   "blocks": "design",
   "expected_answer_shape": "A count of active goals or habits, with a rough kept-versus-lapsed status for each."
  },
  {
   "id": "q12",
   "class": "cost",
   "text": "What does the tutor currently cost per session, how often are sessions held, and who books and pays?",
   "why_it_matters": "This is a money cost already in place, and whether the tutor arrangement changes shapes the overlap.",
   "blocks": "design",
   "expected_answer_shape": "Rate, frequency, booking method and payment method."
  },
  {
   "id": "q13",
   "class": "cost",
   "text": "Which apps, subscriptions, textbooks or course materials for this language do they already own or pay for, and which are actually used?",
   "why_it_matters": "These are existing costs, and possibly existing spaced-repetition decks that already work.",
   "blocks": "design",
   "expected_answer_shape": "A list of items, each with cost and the date it was last used."
  },
  {
   "id": "q14",
   "class": "cost",
   "text": "On which days, and at which times of day, do they have attention to spare? Which periods are protected unstructured time that they have said they want to keep free?",
   "why_it_matters": "Empty calendar slots are not available capacity, and placing practice in protected time does harm.",
   "blocks": "behaviour",
   "expected_answer_shape": "Named protected periods with source, and times they have actually studied."
  },
  {
   "id": "q15",
   "class": "asymmetry",
   "text": "Is there a dated, closing event tied to the goal (a trip, a move, a family event, an exam), and when is it?",
   "why_it_matters": "A fixed date makes slippage irreversible and changes how hard the plan pushes.",
   "blocks": "design",
   "expected_answer_shape": "The event and date, or confirmation that none is recorded."
  },
  {
   "id": "q16",
   "class": "asymmetry",
   "text": "Is there existing study history that could not be recreated if lost, such as a spaced-repetition review history, tutor notes or their own notebooks? Where is it held?",
   "why_it_matters": "Migrating or replacing a tool could wipe review intervals or records that can't be rebuilt.",
   "blocks": "design",
   "expected_answer_shape": "Each item with its location, format and size."
  },
  {
   "id": "q17",
   "class": "asymmetry",
   "text": "Is there any record that pressure or tracking has turned a hobby into a chore for them before, after which they quit it?",
   "why_it_matters": "This is the way the capability could cause the very lapse it is built to prevent.",
   "blocks": "behaviour",
   "expected_answer_shape": "Instances from the diaries, or a note that none were found."
  },
  {
   "id": "q18",
   "class": "feasibility",
   "text": "Are good audio, dialogue and graded-reading sources available for this language and variety, and can generated material be checked by a native speaker or by the tutor?",
   "why_it_matters": "Generated material in a language with few resources may contain errors that a beginner can't catch.",
   "blocks": "design",
   "expected_answer_shape": "Named resource types that exist for the language, plus who could check generated material, if anyone."
  },
  {
   "id": "q19",
   "class": "feasibility",
   "text": "On which devices and channels do they actually study or would study (phone, paper, desktop, audio while commuting), and which channels can the assistant reach?",
   "why_it_matters": "Material and reviews have to arrive where practice actually happens.",
   "blocks": "design",
   "expected_answer_shape": "A list of devices and contexts, each marked by how often it is used."
  },
  {
   "id": "q20",
   "class": "feasibility",
   "text": "What evidence of performance could the assistant actually see: app statistics, recordings, tutor reports, self-reports?",
   "why_it_matters": "Assessment and stall detection need observable signals, otherwise they are guesses.",
   "blocks": "design",
   "expected_answer_shape": "A list of data sources, with access status for each."
  },
  {
   "id": "q21",
   "class": "surface",
   "text": "What does the tutor already do: assessment, syllabus, homework, material? Do they keep notes or a plan, and how are those shared?",
   "why_it_matters": "Two teachers setting different plans would conflict, so it has to be known what already operates on the learning.",
   "blocks": "design",
   "expected_answer_shape": "The tutor's role, the artefacts they produce, and how those reach the principal."
  },
  {
   "id": "q22",
   "class": "surface",
   "text": "What existing system schedules their study time in the calendar today, and what moves or deletes those blocks when the week changes?",
   "why_it_matters": "The weekly plan must reconcile with whatever already schedules study time, or each will overwrite the other.",
   "blocks": "design",
   "expected_answer_shape": "The named component or habit that creates the blocks and its rules for rescheduling."
  },
  {
   "id": "q23",
   "class": "surface",
   "text": "Who keeps the record of their level up to date as they progress (the tutor, an app's placement, the principal), and how often has it been updated?",
   "why_it_matters": "The level estimate goes stale, so someone has to keep it true.",
   "blocks": "behaviour",
   "expected_answer_shape": "The owner and the update frequency, or a note that no such record exists."
  },
  {
   "id": "q24",
   "class": "surface",
   "text": "If they already have vocabulary decks or lists, where are they, are there duplicates across tools, and are cards ever retired?",
   "why_it_matters": "Generated cards would need deduping and merging against existing ones.",
   "blocks": "design",
   "expected_answer_shape": "Deck locations with approximate card counts and any existing cleanup practice."
  },
  {
   "id": "q25",
   "class": "surface",
   "text": "During known breaks (travel, illness, busy work seasons), what currently happens to their study, and is anything paused or expired?",
   "why_it_matters": "Review backlogs pile up during breaks, and the pause behaviour has to be known.",
   "blocks": "behaviour",
   "expected_answer_shape": "Examples of past breaks and what happened to the backlog."
  },
  {
   "id": "q26",
   "class": "minimum_version",
   "text": "Have they asked anywhere for something smaller, such as a weekly topic suggestion, a word list, or help preparing for tutor sessions?",
   "why_it_matters": "The smallest version they have actually asked for is the natural starting point.",
   "blocks": "design",
   "expected_answer_shape": "Quotes of specific small asks, with dates."
  },
  {
   "id": "q27",
   "class": "minimum_version",
   "text": "How long does it take them by hand today to pick what to study, find material and prepare for tutor sessions?",
   "why_it_matters": "This shows what manual cost the capability would actually remove.",
   "blocks": "design",
   "expected_answer_shape": "Minutes per week per activity, from observation or their own account."
  },
  {
   "id": "q28",
   "class": "authority",
   "text": "Which choices have they said the assistant may make alone (booking or moving study blocks, choosing weekly content, changing tutor bookings), and which must be shown to them first?",
   "why_it_matters": "This separates what is decided from what is only surfaced, especially anything involving the tutor's time or money.",
   "blocks": "behaviour",
   "expected_answer_shape": "A list of permitted and must-ask actions, with source."
  },
  {
   "id": "q29",
   "class": "authority",
   "text": "What is their stated default when a stall goes unanswered: do nothing, send a single note, or tell the tutor? Have they said whether the tutor may be contacted on their behalf?",
   "why_it_matters": "Silence has to produce a known outcome, and contacting a third party needs explicit permission.",
   "blocks": "behaviour",
   "expected_answer_shape": "A stated default action and a yes or no on contacting the tutor, with source."
  },
  {
   "id": "q30",
   "class": "authority",
   "text": "Have they said whether, when the plan and the tutor disagree, the tutor's syllabus should take precedence?",
   "why_it_matters": "This settles in advance who wins a conflict between the two teachers.",
   "blocks": "behaviour",
   "expected_answer_shape": "A stated precedence, or a note that none is recorded."
  }
 ]
}
```
