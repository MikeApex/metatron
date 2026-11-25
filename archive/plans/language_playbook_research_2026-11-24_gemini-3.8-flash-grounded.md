# Language-learning playbook — research, 2026-11-24

Raw answers behind `config/playbooks/language_learning.md`. Three decontextualised grounded
Research Agent calls (gemini-3.8-flash, Google Search grounding; no language named, no personal
context), then one grounded fact-check. Claude (claude-sonnet-4-6 via the ask_claude MCP, training
knowledge) answered the combined question as a second voice; its answer is in the session
transcript (`archive/transcripts/`, file starting "2026-11-24 — 2026-11-24-language-playbook-prompt").
Where they differed: Claude put FSI hours at ILR 2 (wrong — ILR 3, confirmed); self-study
multiplier 1.5–2× (Claude) vs 1.2–1.5× (grounded; both synthesis); tutor at A1 weekly (Claude) vs
every 1–2 weeks (grounded; no published evidence either way). Grounding redirect URLs removed.

## A_stages

**Question:** An adult learning a new language from beginner to everyday conversational level, studying alone with an occasional tutor. (1) The stages from beginner to everyday conversational level, with typical hours of study for each and where each sits on the CEFR scale (A1, A2, B1). (2) How those hours differ for a language close to English versus distant from it — e.g. the US Foreign Service Institute's language categories and their published hours. (3) For each stage, observable outcomes a learner can check they can now do (can-do statements), not hours logged or chapters finished. (4) How a learner who already has some exposure can place themselves — self-assessment grids, placement tests — so earlier stages can be skipped. (5) How to maintain the language once conversational level is reached. Cite sources.

### 1. Stages from Beginner to Everyday Conversational Level (CEFR Alignment and Hours)

The Common European Framework of Reference for Languages (CEFR) defines language proficiency across six levels (A1 to C2). For an adult learner, **"everyday conversational level"** corresponds functionally to **CEFR B1 (Threshold)**, though a learner begins participating in basic exchanges at **A2 (Waystage)**.

| CEFR Level | Stage Name | Cumulative Guided Learning Hours (Cambridge English Guidelines) | Independent Learner Reality (Total Study Hours) | Primary Conversational Function |
| :--- | :--- | :--- | :--- | :--- |
| **A1** | Breakthrough | **90–100 hours** | **100–150 hours** | Survival phrases, basic introductions, requesting simple items. Interlocutor must speak slowly and assist. |
| **A2** | Waystage | **180–200 hours** | **200–300 hours** | Routine social exchanges, basic transactions (ordering, shopping, travel logistics), simple descriptions of self and immediate environment. |
| **B1** | Threshold *(Everyday Conversational)* | **350–400 hours** | **400–600 hours** | Unrehearsed conversation on familiar topics, narrating past events, describing plans/opinions, navigating unexpected travel disruptions independently. |

*Note on "Guided Learning Hours" (GLH):* Cambridge English and Council of Europe estimates define a guided hour as formal instruction plus assigned independent work. Independent adult learners studying alone with an occasional tutor typically experience an efficiency penalty (due to trial-and-error curriculum design, self-correction delays, and gaps in spaced reinforcement), requiring roughly **1.2× to 1.5× the guided hours** to reach equivalent output proficiency.

---

### 2. How Hours Differ by Language Distance (FSI Categories)

The Foreign Service Institute (FSI) of the U.S. Department of State categorizes languages based on the time required for a native English speaker to achieve **General Professional Proficiency** (ILR Level 3, roughly equivalent to CEFR B2/C1). 

Because reaching everyday conversational ability (CEFR B1 / ILR Level 1+ to 2) requires roughly **40% to 50% of the effort** needed for full professional proficiency, the structural distance of the language heavily dictates the timeline:

| FSI Category | Distance from English | Representative Languages | FSI Class Hours to Professional Working (ILR 3 / ~B2–C1) | Estimated Hours to Conversational (B1) for Independent Adult |
| :--- | :--- | :--- | :--- | :--- |
| **Category I** | Closely related (Romance, Scandinavian, Germanic cousins) | Spanish, French, Italian, Portuguese, Dutch, Swedish, Norwegian | 600–750 hours | **300–450 hours** |
| **Category II** | Similar to English with added formal complexity | German, Indonesian, Swahili, Malay | ~900 hours (German: ~750–900 hrs) | **450–550 hours** |
| **Category III** | Significant linguistic/cultural differences (Hard) | Russian, Greek, Hindi, Polish, Turkish, Persian/Farsi, Vietnamese | ~1,100 hours | **650–850 hours** |
| **Category IV** | Exceptionally difficult for English speakers (Super-hard) | Mandarin Chinese, Cantonese, Japanese, Korean, Arabic | ~2,200 hours | **1,200–1,500+ hours** |

#### Why the Gap Exists
1. **Cognate Vocabulary:** Category I languages share thousands of Latin/Germanic roots with English. Learners acquire reading and receptive vocabulary rapidly. In Category IV, nearly every word must be memorized from scratch.
2. **Grammatical Distance:** Ergative structures, non-Indo-European case systems (e.g., Russian's six cases), agglutinative morphology (e.g., Turkish, Hungarian), or honorific systems (e.g., Japanese, Korean) require learners to build entirely new mental models of sentence construction.
3. **Phonetics and Writing Systems:** Tones (Mandarin, Vietnamese), non-Latin scripts (Cyrillic, Arabic, Devanagari), or logographic systems (Chinese Hanzi / Japanese Kanji) consume hundreds of hours before basic literacy and clear pronunciation are internalized.

---

### 3. Observable "Can-Do" Outcomes by Stage

Rather than counting chapters or apps completed, proficiency is measured by functional communicative acts derived from the *Council of Europe CEFR Companion Volume* (2020) and *ACTFL Proficiency Guidelines*:

#### Stage 1: A1 (Breakthrough / Formulaic Communication)
* **Listening:** Can recognize familiar words and basic phrases concerning themselves, family, and concrete surroundings when people speak slowly and distinctly.
* **Spoken Interaction:** 
  * Can answer simple questions with isolated words or stock phrases: *"Where do you live?"*, *"What time is it?"*, *"How much does this cost?"*
  * Can order coffee or food by pointing and using polite formulas (e.g., *"Please," "Thank you," "I want this"*).
  * *Constraint:* Conversation breaks down immediately if the other person uses unscripted idioms, rapid speech, or compound sentence structures.
* **Spoken Production:** Can state name, nationality, age, profession, and basic likes/dislikes using single clauses (e.g., *"I live in Madrid. I am an engineer. I like tea."*).

#### Stage 2: A2 (Waystage / Routine Social Navigation)
* **Listening:** Can understand the main idea in short, clear commercial announcements (e.g., train arrivals, store closing announcements, weather summaries).
* **Spoken Interaction:** 
  * Can handle complete service encounters: booking a hotel room, buying transit tickets, asking for directions, or asking for a different size/color in a store.
  * Can participate in short social chats (weather, plans for the weekend, family details), though relies on pauses, rephrasing, and repair strategies (e.g., asking *"Can you repeat that?"*).
* **Spoken Production:** 
  * Can string together simple phrases using coordinating conjunctions (*and*, *but*, *because*).
  * Can describe past activities simply (e.g., *"Last weekend I visited my family and we cooked pasta"*), though may mix up irregular verbs or tenses without completely breaking comprehension.

#### Stage 3: B1 (Threshold / Conversational Independence)
* **Listening:** Can understand the main points of standard speech on familiar topics encountered in work, hobbies, or current events, provided speech is relatively clear.
* **Spoken Interaction:** 
  * **The Unplanned Social Interaction:** Can hold an unrehearsed 15-to-30-minute conversation with a native speaker on everyday topics (work, travel, family, daily routines) without the speaker needing to dramatically simplify their grammar.
  * **Handling the Unexpected:** Can deal with common travel and logistical mishaps without English (e.g., explaining that a luggage bag is missing, disputing a restaurant bill politely, returning a defective purchase).
  * **Circumlocution:** When a specific noun or verb is missing, the learner can talk around it using descriptions (e.g., saying *"the machine that keeps food cold"* instead of *"refrigerator"*).
* **Spoken Production:** 
  * Can connect phrases smoothly into a coherent narrative.
  * Can express and justify opinions, hopes, and ambitions (e.g., *"I think remote work is better because..."*, *"I hope to move abroad next year because..."*).

---

### 4. Self-Placement and Diagnostic Strategies

A learner with past classroom exposure or informal contact should determine their baseline before starting to avoid repeating foundational grammar unnecessarily:

1. **The CEFR Self-Assessment Grid (Council of Europe):**
   * The official CEFR self-assessment rubric breaks down skills into Listening, Reading, Spoken Interaction, Spoken Production, and Writing across levels A1–C2. 
   * Learners read the descriptor columns: if they can perform 80%+ of the tasks in a level under realistic conditions, that level is considered consolidated.
2. **Standardized Diagnostic Assessments (Free / Publicly Available):**
   * **DIALANG:** Developed by European universities with European Commission support, this is an open-source, non-commercial diagnostic tool providing testing aligned to CEFR levels across 14 European languages (evaluating reading, listening, grammar, and vocabulary).
   * **Institutional Level Checks:** Major cultural institutes offer calibrated online placement quizzes: *Cervantes Institute AVE test* (Spanish), *Goethe-Institut Einstufungstest* (German), *Alliance Française / TV5Monde* (French), or *Dante Alighieri* (Italian).
3. **The "Tutor Ceiling Probe" (Single 45-Minute Session):**
   * Rather than booking a lesson to learn, an adult should book an initial conversational tutor explicitly requesting a **diagnostic ceiling test** (modeled on the ACTFL Oral Proficiency Interview format).
   * *The protocol:*
     * **Minutes 0–10 (A1/A2 Check):** Tutor prompts present-tense descriptions (daily routine, home, job).
     * **Minutes 10–25 (A2/B1 Transition):** Tutor asks for past narratives (*"What did you do last weekend?"*) and future plans (*"What are your plans for the summer?"*). If the learner cannot control past/future aspects, their ceiling is A2.
     * **Minutes 25–40 (B1 Check):** Tutor introduces an abstract or opinion question (*"Why do you think people prefer city life to country life?"*) or a simulated problem (*"Call me as a hotel receptionist and explain that your room has no hot water"*).
     * The point where communication breaks down or reverts to single-word utterances defines the exact starting curriculum.

---

### 5. Maintaining Language Proficiency Post-B1

Second-language attrition research (e.g., Monika Schmid, Kees de Bot) demonstrates that intermediate proficiency (B1/B2) reaches a "critical mass" where receptive vocabulary decays significantly more slowly than at beginner levels, provided continuous low-friction maintenance is implemented.

1. **The Receptive Anchor (Comprehensible Input / Stephen Krashen):**
   * **Narrow Listening/Reading:** Focus on 1–2 content verticals rather than broad media. Following a specific daily news podcast or a single YouTuber speaking about a personal hobby (e.g., cooking, gaming, tech) activates specialized recurring vocabulary, preventing cognitive overload.
   * **Graded Audio & Readers:** Listen to B1–B2 podcasts aimed at learners (e.g., *InnerFrench*, *Hoy Hablamos*, *Easy German*) played at 1.0× speed during commutes.
2. **Active Maintenance / Low-Frequency High-Value Output:**
   * **Bi-Weekly Tutoring:** Maintain one 45-minute unstructured conversational session every 14 days (e.g., via italki or Preply) dedicated entirely to discussing news articles or personal events, requiring the tutor to correct grammar notes in writing rather than interrupting flow.
   * **Self-Talk / Voice Journaling:** Record a 2-minute daily audio memo summarizing the day's events or describing a task. This forces the brain to retrieve active syntax and conjugations without requiring an external conversation partner.
3. **Spaced Retrieval for Fragile Lexicon:**
   * Maintain an SRS deck (e.g., Anki) strictly capped at 5–10 cards per day (under 5 minutes). Focus exclusively on collocations, prepositions with verbs, and idioms that do not naturally occur in everyday English-thought translations.

---

### Sources
* **Council of Europe (2001, 2020):** *Common European Framework of Reference for Languages: Learning, teaching, assessment* & *CEFR Companion Volume with New Descriptors*.
* **Foreign Service Institute (FSI), U.S. Department of State:** *Foreign Language Training Difficulty Rankings and Approximate Learning Hours* (School of Language Studies).
* **Cambridge University Press & Assessment:** *Introductory Guide to the CEFR* & Research reports on Guided Learning Hours (GLH) for language attainment.
* **European Commission / Lancaster University:** *DIALANG Language Diagnostic Assessment Project*.
* **Schmid, M. S., & de Bot, K. (2004):** *Language Attrition: Theoretical perspectives and empirical findings*.

FLAGS:
CONTEXT_NEEDED: The specific target language, the learner's native language, and the target weekly study time (to compute a calendar timeline).

SOURCES (7 retrieved):

## B_method

**Question:** An adult learning a new language from beginner to everyday conversational level, studying alone with an occasional tutor. (1) What a good weekly routine looks like: the split of time between speaking, listening, vocabulary review and grammar, and how that split changes by stage. (2) How often sessions with a tutor pay off at each stage. (3) Spaced repetition: what the research shows, sensible daily review load, and its limits. (4) The Pimsleur method (graduated-interval recall, audio-first): what it does well and badly, and where it fits. (5) Vocabulary targets: how many words or word families each CEFR level typically needs, and frequency-based word lists. Cite sources.

### 1. Weekly Routine Architecture and Stage Progression

Second Language Acquisition (SLA) research establishes that language acquisition requires balancing multiple distinct cognitive processes rather than relying solely on exposure or explicit study. The standard pedagogical framework is **Paul Nation’s "Four Strands" model** (2007, 2014), which demonstrates that a balanced curriculum must distribute time across:
1. **Meaning-focused input:** Receptive listening and reading where $\ge 95\text{--}98\%$ of vocabulary is understood.
2. **Meaning-focused output:** Productive speaking and writing to convey communicative intent.
3. **Language-focused learning:** Explicit study of pronunciation, grammar rules, and vocabulary retrieval.
4. **Fluency development:** Processing and producing already-known language with increasing speed and automaticity (e.g., timed speaking, repeated listening).

While Nation posits an equal $25\%$ split across a full educational trajectory, the practical time allocation must shift across proficiency stages for an adult self-directed learner targeting an everyday conversational level (CEFR B1).

#### Stage Breakdown for a 7–10 Hour Study Week

| Component | Beginner Stage (CEFR A1–A2) | Intermediate / Conversational Stage (CEFR B1) |
| :--- | :--- | :--- |
| **Language-Focused Learning** (Grammar & SRS Vocabulary) | **$40\%$ (~3–4 hrs/wk)**<br>High explicit study: syntactic rules, morphology, foundational phonetics, high-frequency word decks. | **$15\text{--}20\%$ (~1.5 hrs/wk)**<br>Targeted review: grammar nuances, error-pattern remediation, niche/collocational vocabulary cards. |
| **Meaning-Focused Input** (Listening & Reading) | **$35\%$ (~2.5–3.5 hrs/wk)**<br>Graded audio/dialogues, learner podcasts, textbook transcripts with $90\text{--}95\%$ known words. | **$40\%$ (~3–4 hrs/wk)**<br>Native-speaker content for learners, natural unscripted podcasts, dual-language materials, graded readers. |
| **Meaning-Focused Output** (Speaking & Writing) | **$15\%$ (~1–1.5 hrs/wk)**<br>Constrained output: scripted shadowing, sentence transformation drills, guided tutor production. | **$25\text{--}30\%$ (~2–2.5 hrs/wk)**<br>Free production: conversational exchange with a tutor, self-recording, unscripted journaling. |
| **Fluency Development** (Speed & Automaticity) | **$10\%$ (~1 hr/wk)**<br>Repetitive drills: fast reading of familiar simple text, 4/3/2 speaking drills on basic prompts. | **$15\%$ (~1.5 hrs/wk)**<br>Real-time conversational repair, rapid retrieval drills, repeated unassisted listening to known recordings. |

*Rationale for the shift:* At A1–A2, learners lack the receptive lexical inventory to sustain meaningful output; forcing extensive unguided free conversation early yields high frustration and fossilized errors (Ellis, 2005). At B1, the "lexical foundation" is established, and the bottleneck shifts to proceduralization (Anderson’s ACT-R framework, 1993), which requires shifting time away from explicit grammar mechanics toward real-time input and output processing.

---

### 2. Tutoring Frequency and Return on Investment (ROI)

The communicative value of a 1-on-1 native or near-native tutor depends heavily on how the session is structured and the learner's current developmental stage:

* **Stage A1–A2 (Low Frequency: 30–45 minutes every 7–14 days)**
  * **ROI Assessment:** Low-to-moderate. Paying an interactive tutor to explain grammar rules or introduce basic vocabulary is inefficient; this declarative knowledge is acquired more cheaply and faster via self-paced instruction, grammar texts, and audio courses.
  * **Optimal Use of Tutor Time:** Pronunciation/phonetic auditing (detecting and fixing L1 phonological interference before it fossilizes), question-and-answer verification, and basic task-based speaking checks (ordering food, asking directions).
* **Stage B1 (Moderate Frequency: 1–2 sessions of 45–60 minutes per week)**
  * **ROI Assessment:** Highest. At this threshold, Swain’s **Output Hypothesis** (1985, 1995) and Long’s **Interaction Hypothesis** (1996) take effect. Learners notice gaps between what they want to say and what they can say, negotiate meaning during breakdowns, and receive immediate corrective feedback.
  * **Optimal Use of Tutor Time:** Unscripted, topic-focused discussions; conversational repair; error-log reviews (using sentences the learner stumbled on during self-study); and practicing communicative strategies (paraphrasing unknown terms, asking for clarification).

---

### 3. Spaced Repetition Systems (SRS): Science, Load, and Limits

#### Empirical Basis
Spaced repetition leverages the **spacing effect** (Ebbinghaus, 1885; Cepeda et al., 2006, 2008) and the **testing/retrieval effect** (Roediger & Karpicke, 2006). Distributing retrieval practice over expanding intervals yields significantly higher delayed recall than massed practice (cramming). A meta-analysis of 48 L2 vocabulary experiments by Kim & Webb (2022) found that spaced retrieval produced a medium effect on immediate tests ($g = 0.58$) and a large effect on delayed tests ($g = 0.80$) compared to massed review.

#### Sensible Daily Load
* **New Cards:** **10 to 15 new words/cards per day**.
* **Review Volume:** Once an SRS deck stabilizes (after 30–60 days), a rate of 10–15 new cards/day generates approximately **70 to 120 reviews per day**.
* **Time Commitment:** **15 to 25 minutes daily**. 
* *Failure Mode (The "Review Avalanche"):* Introducing 30–50 cards daily quickly pushes review queues above 250–350 cards/day. This causes cognitive fatigue, mechanical clicking without retrieval effort, and eventual abandonment of the system.

#### Theoretical and Practical Limits
1. **Isolated Cued Recall vs. Procedural Fluency:** SRS builds declarative memory (explicit recall of form-meaning pairings). It does not proceduralize that knowledge into rapid, subconscious speech production under conversational time constraints (Anderson, 1993; Ullman's Declarative/Procedural model, 2001).
2. **Lack of Collocational and Pragmatic Context:** Words learned solely as isolated card pairs frequently lead to "dictionary translation errors" because cards fail to capture syntactic valency, idiomatic register, and subtle semantic prosody (Schmitt, 2008, 2010).
3. **Decontextualization:** Without concurrent exposure to rich, meaning-focused input (reading and listening), items in an SRS decay rapidly from active usage even if they remain recognizable on flashcards. SRS is a maintenance mechanism, not an acquisition engine on its own.

---

### 4. The Pimsleur Method: Evaluation and Placement

#### Pedagogical Mechanism
Developed by Dr. Paul Pimsleur (1967, "A Memory Schedule"), the method is built on two core pillars:
1. **Graduated-Interval Recall:** Expanding rehearsal intervals applied within audio lessons (e.g., testing a newly introduced phrase at 5 seconds, 25 seconds, 2 minutes, 10 minutes, etc.).
2. **The Anticipation Technique (Audio Prompt-Response):** The recording poses an English or target-language prompt, introduces a pause for the learner to produce the target utterance aloud, and then confirms with native audio.

#### Strengths
* **Phonological Loop Activation & Accent Training:** Because it bypasses orthography (written text), learners do not map target language letters to their native language's spelling/phonetic biases (Pimsleur, 1980/2012).
* **Proceduralization of Structural Chunks:** The strict pause requires active oral retrieval under slight time pressure, building rudimentary automaticity for core syntactic patterns (e.g., negative structures, polite requests, basic verb conjugations).
* **Low Friction & High Compliance:** Audio-only execution allows integration into passive slots (driving, walking, daily chores).

#### Weaknesses
* **Extremely Low Vocabulary Density:** A standard 30-lesson level (15 hours of audio) introduces only ~300 to 400 distinct words. Reaching a conversational B1 threshold solely via Pimsleur would require hundreds of hours of listening.
* **Absence of Literacy:** The deliberate exclusion of text deprives adult learners of orthographic anchoring, which is a key cognitive reinforcer for reading comprehension and visual memory.
* **Artificial Discourse Structure:** Utterances are predictable and rigid; they do not prepare the learner for the erratic pacing, overlaps, and dialectal variations of natural speech.

#### Optimal Role
Pimsleur functions best as an **A0–A1 onboarding auxiliary** during the first 4 to 8 weeks. Completing 1 to 2 units (30–60 lessons) serves to establish phonemic confidence, train oral cadence, and break initial speaking inhibition. Beyond early A2, its pedagogical efficiency drops sharply relative to graded listening, structured grammar/lexicon study, and live conversation.

---

### 5. Vocabulary Targets, CEFR Levels, and Word Frequency Lists

#### Counting Units: Lemmas vs. Word Families
* **Lemma:** A base word plus its inflections (e.g., *sing*, *sings*, *singing*, *sang*, *sung*).
* **Word Family:** A base word, its inflections, plus its common transparent transparent derivations (e.g., *govern*, *government*, *governor*, *governable*, *misgovern*).
* *Note:* 1 word family corresponds roughly to 1.4 to 1.8 lemmas at beginner/intermediate stages.

#### CEFR Vocabulary Size Targets
Compiled from empirical lexical profiling research (Milton, 2010; Milton & Alexiou, 2009, 2020; Laufer, 1992, 2020; Nation, 2006):

| CEFR Level | Primary Communicative Capability | Receptive Vocabulary (Lemmas) | Receptive Vocabulary (Word Families) |
| :--- | :--- | :--- | :--- |
| **A1** | Basic survival phrases, basic personal info, introductions | $< 1,500$ (typically ~800–1,000) | ~500–700 |
| **A2** | Routine social exchanges, simple predictable tasks | $1,500\text{--}2,500$ | $1,000\text{--}1,500$ |
| **B1** (Everyday Conversational) | Unscripted discussion of familiar topics, travel independence, expressing opinions | **$2,750\text{--}3,250$** | **$2,000\text{--}3,000$** |
| **B2** | Fluent spontaneous interaction, nuanced abstract topics | $3,250\text{--}3,750$ | $3,500\text{--}4,500$ |

#### The Lexical Coverage Curve (Zipf’s Law)
Word frequency follows a power-law distribution. According to foundational corpus research by Nation (2006) and Adolphs & Schmitt (2003):
* The most frequent **1,000 word families** account for approximately **$75\text{--}80\%$** of running words in spoken discourse.
* The top **2,000 to 3,000 word families** account for **$\sim 90\text{--}95\%$** of running words in everyday spoken interaction.
* Laufer & Ravenhorst-Kalovski (2010) identified $95\%$ text coverage as the minimum threshold for general unassisted comprehension. This makes the **2,000 to 3,000 word family tier the natural target for functional B1 everyday conversation**.

#### Utility and Limits of Frequency-Based Lists (e.g., GSL, NGSL)
* **General Service List (GSL; West, 1953) / New General Service List (NGSL; Browne, Culligan, & Phillips, 2013):** These corpora identify the highest-yield lexical units across general communication.
* **The High Utility Zone:** The first 1,000 to 2,000 words in any language provide unmatched communicative leverage. Explicitly learning these via SRS provides the immediate scaffolding needed to comprehend graded input.
* **The Frequency Fallacy (Where lists fail conversation):** Frequency lists are dominated by abstract nouns, grammatical function words, and administrative/media terms. Concrete everyday terms (e.g., *fork*, *blanket*, *sprain*, *landlord*, *spicy*) often rank between the 4,000th and 8,000th frequency bands despite being essential to daily domestic conversation.
* **Curricular Implication:** Systematic frequency-list study should be used for the first **1,000 to 1,500 core words**, after which the learner should transition to **thematic/situational vocabulary** ("islands of fluency") tailored to their specific daily life, routines, and conversational goals.

SOURCES (17 retrieved):

## C_resources

**Question:** An adult learning a new language from beginner to everyday conversational level, studying alone with an occasional tutor. (1) Types of resources available by software or web subscription — audio courses, spaced-repetition apps, tutor marketplaces, conversation-exchange apps, graded readers, podcasts — with what each type is good for and at what stage; well-known examples of each, with typical prices. (2) What study resources a generic AI language model can usefully create for a learner (vocabulary lists, dialogues, graded texts, quizzes, conversation practice), and its known weaknesses for this use. (3) The common reasons adults stall or quit, especially at the intermediate plateau, and what evidence says gets them moving again. Cite sources.

### 1. Landscape of Subscription & Web Resources

| Resource Type | What It Is Good For | Optimal Stage | Well-Known Examples | Typical Pricing |
| :--- | :--- | :--- | :--- | :--- |
| **Audio Courses** | Developing basic phonology, early sentence frames, listening comprehension, and confidence in early oral production without text dependency. | **Absolute Beginner (A0) to Elementary (A2)** | Pimsleur, Michel Thomas | • **Pimsleur:** ~$15–$21/month (app subscription) or $120–$150 per 30-lesson level outright.<br>• **Michel Thomas:** ~$12–$15/month (app) or $75–$135 per multi-hour course pack. |
| **Spaced-Repetition Systems (SRS)** | Efficient long-term retention of vocabulary, collocations, and grammatical patterns through active recall and algorithmic spacing. | **All stages** (Foundation at A1–A2; specialized/low-frequency lexis at B1–B2) | Anki (open-source), Memrise, Clozemaster | • **Anki:** Free on desktop/web/Android; one-time $25 iOS fee.<br>• **Memrise:** Free tier; Pro ~$10–$15/month or ~$60–$90/year.<br>• **Clozemaster:** Free tier; Pro ~$8/month or ~$60/year. |
| **Tutor Marketplaces** | Live, personalized 1-on-1 instruction, targeted pronunciation correction, guided conversation, and immediate corrective feedback. | **Late Beginner (A2) through Advanced (C1)** | iTalki, Preply, Verbling | Pay-per-lesson (no mandatory subscription):<br>• Community tutors: ~$8–$18/hour.<br>• Professional/certified teachers: ~$18–$40+/hour. |
| **Conversation-Exchange Apps** | Low-stakes text/voice chatting with native speakers, casual pragmatic practice, and cultural exposure. | **Intermediate (B1+)** (requires sufficient vocabulary to hold a basic conversation) | Tandem, HelloTalk | Free core model (ad-supported); Premium options for unlimited translations and search filters at ~$7–$12/month or ~$40–$60/year. |
| **Graded Readers & Reading Platforms** | Contextual vocabulary acquisition, exposure to sentence syntax, and building reading stamina without dictionary overload. | **A2 to Upper-Intermediate (B2)** | LingQ, Beelinguapp, Readlang | • **LingQ:** Free tier (limited); Premium ~$13/month or ~$108/year.<br>• **Beelinguapp:** Free tier; Premium ~$4–$8/month.<br>• **Readlang:** Free core; Premium $5/month. |
| **Podcasts & Comprehensible Input** | Training auditory processing at variable speeds; transitioning from teacher-talk to natural speech cadence and idioms. | **A2 through C1** (Learner podcasts at A2–B1; native topical podcasts at B2+) | Coffee Break Languages, LanguagePod101, Easy Languages (Patreon) | • Audio streams are generally free on podcast platforms.<br>• Accompanying transcripts/lesson guides: ~$8–$25/month. |

---

### 2. Capabilities and Weaknesses of Generic AI Language Models

A standard, text- or voice-enabled large language model (LLM) acts as an on-demand, infinitely patient instructional designer and conversational partner.

#### High-Utility Resources an LLM Can Create
* **Frequency-Targeted Vocabulary & Collocation Decks:** LLMs can extract high-frequency vocabulary based on CEFR bands (A1–B2) or domain-specific needs (e.g., medical, commercial). Crucially, they can generate native-like collocations (e.g., pairing nouns with their natural verbs rather than literal translations) formatted directly for SRS import (e.g., CSV format with sentence context and target cloze deletions).
* **Calibrated Graded Texts & Parallel Stories:** An LLM can generate fictional narratives, dialogues, or current event summaries constrained to specific grammatical structures (e.g., "write a 300-word passage in Spanish using only present and imperfect past tenses, targeting B1 level") along with an inline vocabulary gloss.
* **Functional Roleplay Dialogues:** It can script realistic dialogues for specific scenarios (e.g., negotiating a lease, returning an item at a train station), highlighting colloquial register, filler words, and pragmatic conventions.
* **Diagnostic Quizzes & Cloze Exercises:** LLMs can quickly produce fill-in-the-blank exercises, error-correction drills, and sentence-transformation tasks targeting a learner’s specific problem areas (such as prepositions or case endings).
* **Asynchronous or Voice-Based Roleplay:** With modern voice and chat interfaces, learners can conduct low-stakes turn-taking practice, requesting the model to respond in character while privately noting grammatical errors and idiomatic alternatives after each exchange.

#### Known Weaknesses and Failure Modes
* **Inaccurate Nuance and Low-Resource Hallucination:** While LLMs are highly reliable in high-resource languages (English, Spanish, French, German, Mandarin), performance degrades significantly in low-resource or agglutinative languages, leading to unnatural syntax, fabricated vocabulary, or incorrect grammatical case usage.
* **Instructional Sycophancy & Unreliable Error Correction:** Models default to being conversational and agreeable. Unless explicitly instructed with strict system prompts, they frequently overlook grammatical mistakes, phonological errors (in voice mode), and subtle unnatural phrasing as long as the semantic meaning is understandable. Conversely, when prompted to correct, they can over-correct natural colloquial expressions into stiff, hyper-formal prose.
* **Sociopragmatic Drift:** LLMs often default to an overly neutral, formal, or textbook register. They may struggle to maintain consistent dialectal consistency (e.g., mixing peninsular and Latin American Spanish idioms) without explicit guardrails.
* **Lack of Spoken Acoustic Feedback:** Text-based LLMs cannot analyze articulatory mechanics or vocal prosody. Even multimodal voice models focus on conversational understanding rather than acoustic-phonetic diagnostic feedback (e.g., identifying whether a learner is using an aspirated versus unaspirated consonant).
* **Curricular Amnesia:** Without a human tutor or an external syllabus, an LLM cannot independently track a learner's interlanguage trajectory over months, risking unstructured, repetitive practice rather than progressive linguistic development.

---

### 3. The Intermediate Plateau: Causes and Evidence-Based Solutions

The "intermediate plateau" (typically spanning CEFR B1 into B2) represents the stage where rapid initial progress flatlines, leading many adult independent learners to abandon study.

#### Why Adults Stall or Quit

1. **The Asymptote of Vocabulary Utility (Zipf’s Law & Lexical Breadth):**
   * *The Problem:* According to corpus linguistics research by Paul Nation (2001, 2014), the most frequent 1,000 to 2,000 word families cover roughly 80% to 90% of everyday spoken communication. In the beginner phase (A0–A2), learning a few hundred high-frequency words yields immediate, noticeable communicative power. Reaching B2/C1, however, requires expanding to 6,000–9,000 word families, where individual words occur far less frequently in daily life. The learner faces exponential increases in effort for incremental gains in comprehension, eroding visible markers of progress.
2. **The "Good Enough" Trap and Interlanguage Fossilization:**
   * *The Problem:* Larry Selinker (1972) introduced the concept of *interlanguage* and *fossilization*—the stabilization of incorrect or simplified linguistic forms that resist correction. Jack C. Richards (2008) observed that intermediate learners achieve basic functional communicative competence: native speakers understand them, and communication succeeds despite structural errors. Because communicative breakdown no longer occurs, the communicative necessity that drove early learning disappears, and errors become habitual.
3. **Receptive vs. Productive Divergence:**
   * *The Problem:* Richards (2008) documented a widening gap between what intermediate learners understand (receptive competence) and what they can express (productive competence). Adults can often follow media or conversation gist through contextual and semantic guessing, but attempting to express nuanced, adult thoughts results in grammatical breakdowns and simplistic vocabulary. This disparity creates psychological frustration and feelings of regression.
4. **Motivational Shift:**
   * *The Problem:* Zoltán Dörnyei’s (2005, 2009) *L2 Motivational Self System* shows that early language acquisition is frequently propelled by instrumental motivation or the novelty of initial milestones. Moving past B1 requires long-term intrinsic and "Ideal L2 Self" alignment—a sustained shift from viewing language as a subject to study toward integrating it into one's daily life and identity. Without this shift, the loss of quick wins leads to demotivation.

#### Evidence-Based Strategies to Overcome the Plateau

* **Pushed Output and Hypothesis Testing:**
   * *The Evidence:* Merrill Swain’s (1985, 1995) *Comprehensible Output Hypothesis* demonstrated that passive input alone is insufficient for grammatical accuracy and syntactic maturity. Swain showed that producing language under communicative pressure ("pushed output") forces learners to shift from semantic processing (getting the general meaning) to syntactic processing (assembling precise grammar and morphology).
   * *Application:* Learners should engage in structured speaking/writing tasks with tutors or language models that require defending opinions, discussing abstract topics, and receiving immediate corrective recasts.
* **Noticing the Gap:**
   * *The Evidence:* Richard Schmidt’s (1990, 2001) *Noticing Hypothesis* posits that learners do not acquire grammatical features from input unless they consciously notice the gap between their own output and target native forms.
   * *Application:* Comparative transcription exercises (recording oneself attempting a topic, then comparing against or having a tutor provide native rephrasings) force awareness of unnatural collocations and persistent fossilized mistakes.
* **Extensive Reading and Narrow Listening:**
   * *The Evidence:* Paul Nation (2014) and Stephen Krashen (1982, 1989) show that low-frequency vocabulary requires 12 to 15+ meaningful encounters across varied contexts to shift from passive recognition to active availability.
   * *Application:* Rather than brief, disconnected textbook extracts, learners at B1–B2 benefit from "narrow input"—reading multiple books by the same author or listening to a series of podcasts on a single topic, which concentrates recurring topical vocabulary and idiomatic collocations.
* **Fluency Development Drills (The 4/3/2 Technique):**
   * *The Evidence:* Developed by Keith Maurice (1983) and extensively validated by Nation (1989), the 4/3/2 technique requires a learner to deliver the same short, unscripted talk to different listeners (or recording devices) in four minutes, then three, then two.
   * *Application:* Successive delivery under tight time constraints forces automaticity, reduces hesitations, and bridges the gap between receptive vocabulary and real-time retrieval.

---

### References
* **Dörnyei, Z.** (2005). *The Psychology of the Language Learner: Individual Differences in Second Language Acquisition.* Lawrence Erlbaum.
* **Dörnyei, Z.** (2009). The L2 Motivational Self System. In Z. Dörnyei & E. Ushioda (Eds.), *Motivation, Language Identity and the L2 Self* (pp. 9–42). Multilingual Matters.
* **Krashen, S.** (1982). *Principles and Practice in Second Language Acquisition.* Pergamon Press.
* **Maurice, K.** (1983). The 4/3/2 technique for improving fluency. *English Teaching Forum*, 21(4), 7–9.
* **Nation, I. S. P.** (1989). Improving speaking fluency. *System*, 17(3), 377–384.
* **Nation, I. S. P.** (2001, 2014). *Learning Vocabulary in Another Language.* Cambridge University Press.
* **Richards, J. C.** (2008). *Moving Beyond the Plateau: From Intermediate to Advanced Proficiency in Language Learning.* Cambridge University Press.
* **Schmidt, R.** (1990). The role of consciousness in second language learning. *Applied Linguistics*, 11(2), 129–158.
* **Selinker, L.** (1972). Interlanguage. *International Review of Applied Linguistics in Language Teaching*, 10(3), 209–231.
* **Swain, M.** (1985). Communicative competence: Some roles of comprehensible input and comprehensible output in its development. In S. Gass & C. Madden (Eds.), *Input in Second Language Acquisition* (pp. 235–253). Newbury House.

SOURCES (21 retrieved):

## Fact-check (grounded)

1. **CONFIRMED** — FSI hours target ILR Level 3 ("Professional Working Proficiency" / General Professional Proficiency, historically S-3/R-3; recent State Department updates cite an integrated Speaking/Listening 3, with class hours listed as 552–690 for Cat I, 828 for Cat II, 1,012 for Cat III, and 2,200 for Cat IV based on a 23-hour class week).
2. **CONFIRMED** — The US State Department / FSI lists Bulgarian, Polish, Greek, Russian, and Turkish in Category III (~44 weeks / ~1,012–1,100 class hours) and German in Category II (~36 weeks / 828–900 class hours; historically 750–900 hours).
3. **CONFIRMED** — Cambridge English Guided Learning Hours specify ~90–100 hours for A1, ~180–200 hours for A2, and ~350–400 cumulative hours for B1 (with B2 at ~500–600).
4. **CONFIRMED** — Kim & Webb (2022, *Language Learning*) found overall effect sizes for spaced vs. massed L2 vocabulary practice of Hedges' *g* = 0.58 on immediate posttests and *g* = 0.80 on delayed posttests.
5. **CONFIRMED** — Laufer & Ravenhorst-Kalovski (2010, *Reading in a Foreign Language*) established a 95% lexical coverage threshold (~4,000–5,000 word families) for minimal comprehension and 98% (~8,000 word families) for optimal/unassisted comprehension.
6. **CONFIRMED** — Milton (2010) and Milton & Alexiou (2009) map B1 competence to approximately 2,500–3,250 words from the 5,000 frequency band, commonly cited as roughly 2,000–3,000 word families.
7. **CONFIRMED** — Paul Pimsleur introduced and modeled "graduated interval recall" in "A Memory Schedule" (*The Modern Language Journal*, Vol. 51, No. 2, 1967, pp. 73–75).
8. **CONFIRMED** — Each standard Pimsleur level consists of 30 daily 30-minute lessons (~15 audio hours) and covers an active functional vocabulary of roughly 250–500 words.
9. **CONFIRMED** — The 4/3/2 timed speaking technique originated with Keith Maurice (1983, *TESOL Newsletter*) and was empirically investigated for fluency and accuracy gains by Paul Nation (1989, *System*).
10. **CONFIRMED** — Paul Nation's Four Strands framework (*Teaching ESL/EFL Reading and Writing*) specifies that curriculum should allocate roughly 25% of time each to meaning-focused input, meaning-focused output, language-focused learning, and fluency development.
11. **CONFIRMED** — Jack C. Richards authored *Moving Beyond the Plateau: From Intermediate to Advanced Levels in Language Learning* (Cambridge University Press, 2008), analyzing the intermediate/upper-intermediate plateau.
12. **CONFIRMED** — The Council of Europe publishes the standard CEFR Self-Assessment Grid, and the EU Socrates-Lingua–funded DIALANG diagnostic assessment suite is freely available across 14 European languages.
13. **UNVERIFIABLE (NO PUBLISHED EVIDENCE FOUND)** — A systematic search identified no published empirical Second Language Acquisition (SLA) trials comparing tutoring session cadence (e.g., weekly vs. every two weeks) specifically for adult independent learners at A1–A2; tutoring frequency research is largely confined to K–12 high-dosage academic remediation (which emphasizes ≥3 sessions/week) rather than adult foreign language self-study.

SOURCES (27 retrieved):
