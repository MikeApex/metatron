# Coordinator model probe — gemini-3.1-flash-lite vs gemini-3.1-pro-preview

*Run 2026-08-28 · offline probe for `[DB-0820-05]` (should the Coordinator move to Pro) · persona `danny_park` · no routing file touched.*

## What this is evidence for

Whether moving the Coordinator from Flash-Lite to Pro fixes the referent-resolution class (`[DB-0826-01]` — a short turn like *"undo that merge"* routed against the wrong conversation), and what a Pro Coordinator would add to the wait before every single reply. **The flip itself is Red-tier and Mike's; this file recommends no routing change.**

## Method

- `tests/run_coord_model_probe.py` drives `_run_single_agent("coordinator", …, model_override=…)` directly — no Synthesizer, no specialist dispatch, no routing edit. The Coordinator's tool grant is empty, so nothing is written.
- **Cached path — a deliberate divergence from the `[DB-0820-05]` entry text.** The entry says *"both models on the uncached path for like-for-like timing"*; Mike's 2026-08-28 run instruction supersedes it. The live Coordinator runs cached, and the question is what a live flip costs, so both models run cached here. **The first call per model is a cache warm-up, run explicitly and excluded from every latency and quality statistic below** — it pays the CachedContent creation round-trip, which a live Coordinator pays once per 10-minute TTL window and never on a turn inside one.
- Suite A: 15 representative turns × both models. Suite B: the four recovered `ROUTING_MISS` referent failures × both models, clean. Suite B-hard: the same four with the competing referent restored, ×3 runs per cell.
- Over-dispatch is not scored as a failure unless the case names the specialist as forbidden. `coordinator.md` keeps over-dispatch dominant on purpose (under-dispatch loses a user's record), so penalising surplus specialists would score the model against a rule the agent file does not hold.
- Persona `danny_park` — the git-tracked test persona. `mike` was not touched.

**The cached path was confirmed exercised, not assumed:** a mean of 6046 of 6190.61 input tokens per call were served from the Vertex context cache (98%). This is measurable only because `core/trace.py` now stores `cached_tokens` on the turn record — it previously accepted the figure, forwarded it to the spend guard and discarded it, so no trace or test could distinguish a cache hit from a miss.

## Step 0 — does the Vertex cache honour `model_override`?

**PASS — no code change needed.** `_get_or_create_vertex_cache` hashes `model_name` into its cache key and issues `caches.create(model=model_name)`, and `model_override` reaches it unmodified through `_run_single_agent` → `run_session_gemini_cached`. A Pro call therefore builds its own CachedContent instead of reusing the Flash-Lite entry or silently running uncached — which is what the live flip needs anyway.

| Check | Result |
|---|---|
| flash cache created | PASS |
| pro cache created (not None — no silent uncached fallback) | PASS |
| pro did NOT reuse the flash cache | PASS |
| second flash call reused the first cache | PASS |
| creation was issued against each model id | PASS |
| padding kept the prompt over the 4,096-token floor | PASS |

## Suite A — 15 representative turns

| Turn | gemini-3.1-flash-lite verdict | gemini-3.1-flash-lite latency | gemini-3.1-pro-preview verdict | gemini-3.1-pro-preview latency |
|---|---|---|---|---|
| A1 | PASS | 1.99s | PASS | 18.33s |
| A2 | PASS | 1.56s | PASS | 9.75s |
| A3 | PASS | 1.49s | PASS | 12.3s |
| A4 | PASS | 1.31s | PASS | 8.97s |
| A5 | PASS | 2.15s | PASS | 13.9s |
| A6 | PASS | 1.57s | PASS | 10.03s |
| A7 | PASS | 2.12s | PASS | 14.75s |
| A8 | PASS | 1.45s | PASS | 9.42s |
| A9 | PASS | 2.25s | PASS | 11.57s |
| A10 | PASS | 2.36s | PASS | 12.49s |
| A11 | PASS | 1.82s | PASS | 16.71s |
| A12 | PASS | 2.15s | PASS | 14.66s |
| A13 | PASS | 1.32s | PASS | 11.2s |
| A14 | PASS | 1.8s | PASS | 14.13s |
| A15 | PASS | 2.81s | PASS | 13.69s |

### Per-turn detail

**A1 — "I slept about four hours and I'm wrecked today."**  
- `gemini-3.1-flash-lite` — **PASS** (1.99s, in 6162 / cached 6046 / out 348 / think 0): got ['diarist', 'mental_wellbeing', 'physical_health']
  - RESOLVED_INTENT: The user is reporting poor sleep (4 hours) and physical/mental exhaustion, seeking recognition and potential support.
- `gemini-3.1-pro-preview` — **PASS** (18.33s, in 6162 / cached 6046 / out 370 / think 1880): got ['diarist', 'mental_wellbeing', 'physical_health']
  - RESOLVED_INTENT: The user is reporting severe physical and mental exhaustion due to getting only four hours of sleep last night.

**A2 — 'Book me a dentist appointment for sometime next Tuesday afternoon.'**  
- `gemini-3.1-flash-lite` — **PASS** (1.56s, in 6161 / cached 6046 / out 278 / think 0): got ['diarist', 'logistics', 'physical_health']
  - RESOLVED_INTENT: The user wants to schedule a dentist appointment for the afternoon of Tuesday, September 1, 2026.
- `gemini-3.1-pro-preview` — **PASS** (9.75s, in 6161 / cached 6046 / out 304 / think 839): got ['diarist', 'logistics', 'physical_health']
  - RESOLVED_INTENT: The user is requesting to schedule a dental appointment for next Tuesday afternoon (September 1, 2026).

**A3 — 'Log that I went for a 5k run this morning and it felt good.'**  
- `gemini-3.1-flash-lite` — **PASS** (1.49s, in 6167 / cached 6046 / out 256 / think 0): got ['diarist', 'physical_health']
  - RESOLVED_INTENT: The user is reporting a 5km run from this morning and expressing a positive physical and mental state resulting from it.
- `gemini-3.1-pro-preview` — **PASS** (12.3s, in 6167 / cached 6046 / out 243 / think 1170): got ['diarist', 'physical_health']
  - RESOLVED_INTENT: The user is recording a 5k run from this morning and noting that it was a positive physical experience.

**A4 — 'What time is my first meeting tomorrow?'**  
- `gemini-3.1-flash-lite` — **PASS** (1.31s, in 6158 / cached 6046 / out 212 / think 0): got ['logistics']
  - RESOLVED_INTENT: The user wants to know the time of their first scheduled meeting on Saturday, August 29, 2026.
- `gemini-3.1-pro-preview` — **PASS** (8.97s, in 6158 / cached 6046 / out 241 / think 755): got ['diarist', 'logistics']
  - RESOLVED_INTENT: The user is asking for the time of their first scheduled meeting or event for tomorrow (Saturday, August 29, 2026).

**A5 — "I'm exhausted but I can't stop working and I snapped at Priya today."**  
- `gemini-3.1-flash-lite` — **PASS** (2.15s, in 6168 / cached 6046 / out 452 / think 0): got ['diarist', 'mental_wellbeing', 'physical_health', 'relationships', 'work_vocation']
  - RESOLVED_INTENT: The user reports significant fatigue, difficulty setting boundaries with work, and interpersonal conflict following an outburst at Priya.
- `gemini-3.1-pro-preview` — **PASS** (13.9s, in 6168 / cached 6046 / out 602 / think 995): got ['diarist', 'mental_wellbeing', 'physical_health', 'relationships', 'work_vocation']
  - RESOLVED_INTENT: User is experiencing acute burnout and exhaustion, struggling to enforce work boundaries, and dealing with the relational fallout of an irritable outburst.

**A6 — 'How many contacts do we have on file?'**  
- `gemini-3.1-flash-lite` — **PASS** (1.57s, in 6159 / cached 6046 / out 159 / think 0): got ['relationships']
  - RESOLVED_INTENT: The user wants to know the total number of contacts currently in the contact list.
- `gemini-3.1-pro-preview` — **PASS** (10.03s, in 6159 / cached 6046 / out 192 / think 795): got ['diarist', 'relationships']
  - RESOLVED_INTENT: The user is asking for the total number of contacts currently stored in the system.

**A7 — "I'm thinking about leaving my job at the end of the quarter."**  
- `gemini-3.1-flash-lite` — **PASS** (2.12s, in 6165 / cached 6046 / out 422 / think 0): got ['diarist', 'finance', 'mental_wellbeing', 'work_vocation']
  - RESOLVED_INTENT: The user is considering resigning from their position by the end of the current quarter and needs to discuss the implications and potential next steps.
- `gemini-3.1-pro-preview` — **PASS** (14.75s, in 6165 / cached 6046 / out 492 / think 1307): got ['diarist', 'finance', 'mental_wellbeing', 'work_vocation']
  - RESOLVED_INTENT: User is contemplating resigning from his job at the end of the quarter, a major life decision that will heavily impact his vocational path, financial goals, and emotional state.

**A8 — "What's the going rate for a plumber in Dublin right now?"**  
- `gemini-3.1-flash-lite` — **PASS** (1.45s, in 6164 / cached 6046 / out 235 / think 0): got ['diarist', 'research_agent']
  - RESOLVED_INTENT: User is inquiring about current market pricing for plumbing services in Dublin, likely to assess costs for a potential repair or maintenance task.
- `gemini-3.1-pro-preview` — **PASS** (9.42s, in 6164 / cached 6046 / out 247 / think 662): got ['diarist', 'research_agent']
  - RESOLVED_INTENT: The user is asking for the current standard market rate for plumbing services in Dublin.

**A9 — 'Move the Thursday call to Friday and tell Marcus about it.'**  
- `gemini-3.1-flash-lite` — **PASS** (2.25s, in 6162 / cached 6046 / out 383 / think 0): got ['diarist', 'logistics', 'relationships']
  - RESOLVED_INTENT: Reschedule a planned call with Marcus from Thursday to Friday and notify him of the change.
- `gemini-3.1-pro-preview` — **PASS** (11.57s, in 6162 / cached 6046 / out 330 / think 965): got ['diarist', 'logistics', 'relationships']
  - RESOLVED_INTENT: The user wants to reschedule an upcoming Thursday call to Friday and send a message to Marcus to inform him of the change.

**A10 — 'Good morning.'**  
- `gemini-3.1-flash-lite` — **PASS** (2.36s, in 6153 / cached 6046 / out 411 / think 0): got ['diarist', 'logistics', 'mental_wellbeing', 'physical_health']
  - RESOLVED_INTENT: The user is initiating a morning check-in/briefing session.
- `gemini-3.1-pro-preview` — **PASS** (12.49s, in 6153 / cached 6046 / out 294 / think 1240): got ['diarist', 'mental_wellbeing', 'physical_health']
  - RESOLVED_INTENT: The user is initiating a new session with a morning greeting, though the system clock indicates it is late afternoon.

**A11 — 'The invoice from the Apex job finally cleared.'**  
- `gemini-3.1-flash-lite` — **PASS** (1.82s, in 6159 / cached 6046 / out 286 / think 0): got ['diarist', 'finance']
  - RESOLVED_INTENT: User is reporting that a long-awaited payment has been received, which directly impacts their financial goal of paying down debt.
- `gemini-3.1-pro-preview` — **PASS** (16.71s, in 6159 / cached 6046 / out 399 / think 1487): got ['diarist', 'finance', 'work_vocation']
  - RESOLVED_INTENT: The user is reporting that a delayed payment for a work project (the Apex job) has successfully arrived.

**A12 — 'I want to start reading properly again in the evenings.'**  
- `gemini-3.1-flash-lite` — **PASS** (2.15s, in 6161 / cached 6046 / out 333 / think 0): got ['diarist', 'learning_growth', 'mental_wellbeing']
  - RESOLVED_INTENT: The user wants to re-establish a habit of evening reading, likely to address the "w1" goal (1 hour of non-screen reading) which is currently marked as at-risk.
- `gemini-3.1-pro-preview` — **PASS** (14.66s, in 6161 / cached 6046 / out 435 / think 1237): got ['diarist', 'learning_growth', 'logistics']
  - RESOLVED_INTENT: User wants to re-establish an evening reading habit, which directly addresses their currently at-risk weekly goal of reading off-screen for an hour.

**A13 — 'Thanks.'**  
- `gemini-3.1-flash-lite` — **PASS** (1.32s, in 6152 / cached 6046 / out 142 / think 0): got ['diarist']
  - RESOLVED_INTENT: The user is acknowledging the previous interaction and closing the current conversational turn.
- `gemini-3.1-pro-preview` — **PASS** (11.2s, in 6152 / cached 6046 / out 215 / think 1005): got ['diarist']
  - RESOLVED_INTENT: The user is sending a brief acknowledgement, checking in after a 20-day gap in communication.

**A14 — 'Add milk and coffee to the shopping list, and remind me to call the bank about the overdraft.'**  
- `gemini-3.1-flash-lite` — **PASS** (1.8s, in 6170 / cached 6046 / out 277 / think 0): got ['diarist', 'finance', 'logistics']
  - RESOLVED_INTENT: Update shopping list with specific items and request a reminder for a financial task.
- `gemini-3.1-pro-preview` — **PASS** (14.13s, in 6170 / cached 6046 / out 363 / think 1214): got ['diarist', 'finance', 'logistics']
  - RESOLVED_INTENT: The user wants to update their shopping list with milk and coffee, and needs a reminder to contact their bank regarding an account overdraft.

**A15 — "I've been feeling flat for about two weeks now and I don't really know why."**  
- `gemini-3.1-flash-lite` — **PASS** (2.81s, in 6170 / cached 6046 / out 387 / think 0): got ['diarist', 'mental_wellbeing', 'physical_health']
  - RESOLVED_INTENT: The user is reporting a persistent low/flat mood over the last fortnight and is seeking perspective or support.
- `gemini-3.1-pro-preview` — **PASS** (13.69s, in 6170 / cached 6046 / out 370 / think 1235): got ['diarist', 'mental_wellbeing', 'physical_health']
  - RESOLVED_INTENT: The user is reporting a persistent low mood and lack of energy over the past two weeks with no obvious trigger.

### Aggregate

| Model | turns | PASS | PARTIAL | CLARIFIED | FAIL | ERROR | mean latency | median | max | mean in | mean cached | mean out | mean thinking |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gemini-3.1-flash-lite | 15 | 15 | 0 | 0 | 0 | 0 | 1.88s | 1.82s | 2.81s | 6162.07 | 6046 | 305.4 | 0 |
| gemini-3.1-pro-preview | 15 | 15 | 0 | 0 | 0 | 0 | 12.79s | 12.49s | 18.33s | 6162.07 | 6046 | 339.8 | 1119.07 |

## Suite B — the four referent failures, replayed clean

**Provenance: faithful reproductions built from the DEV_BACKLOG [DB-0826-01] descriptions, not the verbatim live turns — the originals are in `mike`'s `quality_events.json` on the VM and `data/personas/` is gitignored, so nothing replayable exists on this machine. A pass is therefore evidence about the CLASS, not proof the exact live turn now works.**

A `CLARIFIED` verdict is a third outcome, not a failure: `coordinator.md` § *Clarify, don't assume* mandates a `CLARIFICATION_NEEDED` flag for a pronoun with no clear referent, so a model that asks has obeyed the agent file without resolving the referent.

| Turn | gemini-3.1-flash-lite verdict | gemini-3.1-flash-lite latency | gemini-3.1-pro-preview verdict | gemini-3.1-pro-preview latency |
|---|---|---|---|---|
| B1 | PASS | 1.78s | PASS | 11.47s |
| B2 | PASS | 1.59s | PASS | 11.82s |
| B3 | PASS | 1.6s | PASS | 8.55s |
| B4 | FAIL | 1.56s | PASS | 14.87s |

### Per-turn detail

**B1 — 'Undo that merge.'**  
*08-26 "Undo that merge" one turn after a contact merge*  
*Live failure: routed to work_vocation, which searched memory for 'Prudential Apex project merge'*  
- `gemini-3.1-flash-lite` — **PASS** (1.78s, in 6179 / cached 6046 / out 256 / think 0): got ['diarist', 'relationships']
  - RESOLVED_INTENT: The user wants to reverse the recent action of merging duplicate "Marcus Delgado" contact records.
- `gemini-3.1-pro-preview` — **PASS** (11.47s, in 6179 / cached 6046 / out 286 / think 1023): got ['diarist', 'relationships']
  - RESOLVED_INTENT: The user wants to reverse the action taken in the previous turn and unmerge the two contact records for Marcus Delgado.

**B2 — 'Read that back to me again.'**  
*08-18 "Read that back to me again" after a food log*  
*Live failure: resolved to Prudential scheduling instead of the previous turn's food data*  
- `gemini-3.1-flash-lite` — **PASS** (1.59s, in 6209 / cached 6046 / out 211 / think 0): got ['diarist', 'physical_health']
  - RESOLVED_INTENT: The user wants me to reiterate the information they just provided in the previous message regarding their food intake today.
- `gemini-3.1-pro-preview` — **PASS** (11.82s, in 6209 / cached 6046 / out 166 / think 1173): got ['diarist']
  - RESOLVED_INTENT: The user is asking to repeat the food log from the immediately preceding message.

**B3 — 'Cancel my previous request.'**  
*08-10 "previous request" resolved to an older item*  
*Live failure: resolved to an older lunch instead of the immediately prior turn*  
- `gemini-3.1-flash-lite` — **PASS** (1.6s, in 6187 / cached 6046 / out 178 / think 0): got ['diarist', 'logistics']; intent names ['thursday', '12:30']
  - RESOLVED_INTENT: The user wishes to cancel the restaurant booking made in the previous turn for Thursday at 12:30.
- `gemini-3.1-pro-preview` — **PASS** (8.55s, in 6187 / cached 6046 / out 225 / think 687): got ['diarist', 'logistics']; intent names ['fumbally', 'thursday', '12:30', 'table']
  - RESOLVED_INTENT: The user wants to cancel the hold just placed for a table at Fumbally for Thursday at 12:30.

**B4 — 'Approved.'**  
*08-15 "Approved" resolved to the wrong pending action*  
*Live failure: resolved to the wrong pending action and wrongly closed an obligation*  
- `gemini-3.1-flash-lite` — **FAIL** (1.56s, in 6188 / cached 6046 / out 197 / think 0): none of ['relationships'] dispatched; got ['logistics']
  - RESOLVED_INTENT: The user is confirming the draft email regarding the boiler issue is ready to be sent or reviewed.
- `gemini-3.1-pro-preview` — **PASS** (14.87s, in 6188 / cached 6046 / out 271 / think 1495): got ['diarist', 'logistics', 'relationships']; intent names ['landlord', 'boiler', 'email', 'draft']
  - RESOLVED_INTENT: The user is approving the previously drafted email to the landlord regarding the boiler and authorizing it to be sent.

### Aggregate

| Model | turns | PASS | PARTIAL | CLARIFIED | FAIL | ERROR | mean latency | median | max | mean in | mean cached | mean out | mean thinking |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gemini-3.1-flash-lite | 4 | 3 | 0 | 0 | 1 | 0 | 1.63s | 1.6s | 1.78s | 6190.75 | 6046 | 210.5 | 0 |
| gemini-3.1-pro-preview | 4 | 4 | 0 | 0 | 0 | 0 | 11.68s | 11.64s | 14.87s | 6190.75 | 6046 | 237 | 1094.5 |

## Suite B-hard — the same four, with the competing referent restored

**This is the half that can discriminate.** Suite B gives the referring turn a clean two-turn history, so there is nothing for either model to get wrong — and the live failures did not happen in that condition. Each case here puts the competing referent the live session actually had (the Prudential Apex *branch* merge, the Prudential *schedule*, an older lunch booking, a second pending approval) two turns back, so the short referring turn genuinely points at two things.

**Provenance: faithful reproductions built from the DEV_BACKLOG [DB-0826-01] descriptions, not the verbatim live turns — the originals are in `mike`'s `quality_events.json` on the VM and `data/personas/` is gitignored, so nothing replayable exists on this machine. A pass is therefore evidence about the CLASS, not proof the exact live turn now works.**

A `CLARIFIED` verdict is a third outcome, not a failure: `coordinator.md` § *Clarify, don't assume* mandates a `CLARIFICATION_NEEDED` flag for a pronoun with no clear referent, so a model that asks has obeyed the agent file without resolving the referent.

*Each cell is 3 independent runs — Flash-Lite's routing is not deterministic, and a single run per cell cannot tell a real difference from one sample of noise.*

| Turn | gemini-3.1-flash-lite verdict | gemini-3.1-flash-lite latency | gemini-3.1-pro-preview verdict | gemini-3.1-pro-preview latency |
|---|---|---|---|---|
| B1h | 3/3 ok | 1.67s | 3/3 ok | 10.32s |
| B2h | **0/3 ok** | 1.46s | 3/3 ok | 11.37s |
| B3h | 3/3 ok | 1.44s | 3/3 ok | 8.34s |
| B4h | **0/3 ok** | 1.56s | 3/3 ok | 18.47s |

### Per-turn detail

**B1h — 'Undo that merge.'**  
*08-26 "Undo that merge" one turn after a contact merge — WITH a competing referent two turns back*  
*Live failure: routed to work_vocation, which searched memory for 'Prudential Apex project merge'*  
- `gemini-3.1-flash-lite` — **PASS** (1.59s, in 6215 / cached 6046 / out 204 / think 0): got ['diarist', 'relationships']
  - RESOLVED_INTENT: The user wants to revert the merge of the two Marcus Delgado contact entries performed in the previous interaction.
- `gemini-3.1-flash-lite` — **PASS** (1.16s, in 6215 / cached 6046 / out 205 / think 0): got ['diarist', 'relationships']
  - RESOLVED_INTENT: The user wants to reverse the recent action of merging the two Marcus Delgado contact records.
- `gemini-3.1-flash-lite` — **PASS** (2.25s, in 6215 / cached 6046 / out 248 / think 0): got ['diarist', 'relationships']
  - RESOLVED_INTENT: The user wants to revert the recent merge of two "Marcus Delgado" contact records.
- `gemini-3.1-pro-preview` — **PASS** (9.39s, in 6215 / cached 6046 / out 215 / think 770): got ['diarist', 'relationships']
  - RESOLVED_INTENT: The user wants to reverse the previous action of merging the two contact records for Marcus Delgado.
- `gemini-3.1-pro-preview` — **PASS** (11.31s, in 6215 / cached 6046 / out 249 / think 1081): got ['diarist', 'relationships']
  - RESOLVED_INTENT: The user wants to reverse the immediately preceding action that merged the two contact records for Marcus Delgado.
- `gemini-3.1-pro-preview` — **PASS** (10.25s, in 6215 / cached 6046 / out 219 / think 910): got ['diarist', 'relationships']
  - RESOLVED_INTENT: The user wants to reverse the immediately preceding action and un-merge the contact records for Marcus Delgado.

**B2h — 'Read that back to me again.'**  
*08-18 "Read that back to me again" after a food log — WITH a competing referent two turns back*  
*Live failure: resolved to Prudential scheduling instead of the previous turn's food data*  
- `gemini-3.1-flash-lite` — **FAIL** (1.81s, in 6249 / cached 6046 / out 178 / think 0): reproduced the live failure — dispatched ['logistics']
  - RESOLVED_INTENT: The user is requesting a recap of the information provided in the previous turn (the Prudential schedule for next week).
- `gemini-3.1-flash-lite` — **FAIL** (1.14s, in 6249 / cached 6046 / out 186 / think 0): reproduced the live failure — dispatched ['logistics']
  - RESOLVED_INTENT: The user wants me to reiterate the schedule for the "Prudential" events that were retrieved in the previous turn (Monday 10:00 review, Wednesday 14:00 handover, Friday 09:00 retro).
- `gemini-3.1-flash-lite` — **FAIL** (1.43s, in 6249 / cached 6046 / out 211 / think 0): none of ['physical_health', 'diarist'] dispatched; got ['work_vocation']
  - RESOLVED_INTENT: The user is requesting a restatement of their upcoming Prudential schedule for the week of August 31, 2026.
- `gemini-3.1-pro-preview` — **PASS** (10.86s, in 6249 / cached 6046 / out 183 / think 951): CLARIFICATION_NEEDED: Whether "that" refers to the food log just recorded or the Prudential schedule provided prior to it.
  - RESOLVED_INTENT: The user is asking to hear a recent piece of information repeated, but it is unclear whether they mean the food log just entered or the Prudential schedule from the previous exchange.
- `gemini-3.1-pro-preview` — **PASS** (10.85s, in 6249 / cached 6046 / out 171 / think 999): CLARIFICATION_NEEDED: Whether the user wants the Prudential schedule repeated or the recent food log repeated.
  - RESOLVED_INTENT: The user is asking to have information repeated, but it is unclear whether they are referring to the Prudential schedule or the food log from the preceding exchanges.
- `gemini-3.1-pro-preview` — **PASS** (12.39s, in 6249 / cached 6046 / out 175 / think 1270): CLARIFICATION_NEEDED: Whether "that" refers to the Prudential schedule or the food log.
  - RESOLVED_INTENT: The user wants a previous piece of information repeated, but it is ambiguous whether "that" refers to the Prudential schedule or the recently logged food entries.

**B3h — 'Cancel my previous request.'**  
*08-10 "previous request" resolved to an older item — WITH a competing referent two turns back*  
*Live failure: resolved to an older lunch instead of the immediately prior turn*  
- `gemini-3.1-flash-lite` — **PASS** (1.69s, in 6218 / cached 6046 / out 245 / think 0): got ['diarist', 'logistics']; intent names ['fumbally', 'thursday', '12:30']
  - RESOLVED_INTENT: The user wants to cancel the lunch reservation at Fumbally scheduled for next Thursday at 12:30 PM.
- `gemini-3.1-flash-lite` — **PASS** (1.39s, in 6218 / cached 6046 / out 208 / think 0): got ['diarist', 'logistics']; intent names ['fumbally', 'thursday', '12:30', 'table']
  - RESOLVED_INTENT: The user wants to cancel the table reservation for Fumbally on Thursday at 12:30.
- `gemini-3.1-flash-lite` — **PASS** (1.23s, in 6218 / cached 6046 / out 190 / think 0): got ['diarist', 'logistics']; intent names ['fumbally', 'thursday', '12:30']
  - RESOLVED_INTENT: The user wants to cancel the lunch booking at Fumbally for Thursday at 12:30.
- `gemini-3.1-pro-preview` — **PASS** (8.91s, in 6218 / cached 6046 / out 242 / think 795): got ['diarist', 'logistics']; intent names ['fumbally', 'thursday', '12:30', 'table']
  - RESOLVED_INTENT: The user wants to cancel the table booking at Fumbally for Thursday at 12:30 that they requested in the immediately preceding message.
- `gemini-3.1-pro-preview` — **PASS** (7.37s, in 6218 / cached 6046 / out 232 / think 601): got ['diarist', 'logistics']; intent names ['fumbally', 'thursday', '12:30', 'table']
  - RESOLVED_INTENT: The user wants to cancel the immediately preceding booking request for a table at Fumbally on Thursday at 12:30.
- `gemini-3.1-pro-preview` — **PASS** (8.75s, in 6218 / cached 6046 / out 268 / think 735): got ['diarist', 'logistics']; intent names ['fumbally', 'thursday', '12:30', 'table']
  - RESOLVED_INTENT: The user is cancelling their immediately preceding request to book a table at Fumbally for Thursday at 12:30.

**B4h — 'Approved.'**  
*08-15 "Approved" resolved to the wrong pending action — WITH a competing referent two turns back*  
*Live failure: resolved to the wrong pending action and wrongly closed an obligation*  
- `gemini-3.1-flash-lite` — **FAIL** (1.8s, in 6223 / cached 6046 / out 260 / think 0): none of ['relationships'] dispatched; got ['diarist', 'logistics']
  - RESOLVED_INTENT: The user is confirming the previous pending drafts (Apex quarterly review invite and landlord boiler email) for finalization/action.
- `gemini-3.1-flash-lite` — **FAIL** (1.33s, in 6223 / cached 6046 / out 270 / think 0): none of ['relationships'] dispatched; got ['diarist', 'logistics']
  - RESOLVED_INTENT: The user is providing authorization to send the previously drafted emails: the quarterly review invite for the Apex team and the email to the landlord regarding the boiler.
- `gemini-3.1-flash-lite` — **FAIL** (1.54s, in 6223 / cached 6046 / out 258 / think 0): none of ['relationships'] dispatched; got ['diarist', 'logistics']
  - RESOLVED_INTENT: The user is providing authorization to send the previously drafted communications: the quarterly review invite for the Apex team and the email to the landlord regarding the boiler.
- `gemini-3.1-pro-preview` — **PASS** (18.33s, in 6223 / cached 6046 / out 320 / think 1804): got ['diarist', 'logistics', 'relationships']; intent names ['landlord', 'boiler', 'email', 'draft']
  - RESOLVED_INTENT: User is approving the pending drafted communication(s) to be sent, most directly the email to the landlord about the boiler, but potentially also the Apex team quarterly review invite.
- `gemini-3.1-pro-preview` — **PASS** (22.64s, in 6223 / cached 6046 / out 230 / think 2468): got ['diarist', 'relationships']; intent names ['landlord', 'boiler', 'email', 'draft']
  - RESOLVED_INTENT: The user is approving the sending of the recently drafted email to the landlord regarding the boiler.
- `gemini-3.1-pro-preview` — **PASS** (14.44s, in 6223 / cached 6046 / out 263 / think 1324): got ['diarist', 'logistics', 'relationships']; intent names ['landlord', 'boiler', 'email', 'draft']
  - RESOLVED_INTENT: The user is approving the release of the drafted email to the landlord regarding the boiler.

### Aggregate

| Model | turns | PASS | PARTIAL | CLARIFIED | FAIL | ERROR | mean latency | median | max | mean in | mean cached | mean out | mean thinking |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gemini-3.1-flash-lite | 12 | 6 | 0 | 0 | 6 | 0 | 1.53s | 1.48s | 2.25s | 6226.25 | 6046 | 221.92 | 0 |
| gemini-3.1-pro-preview | 12 | 12 | 0 | 0 | 0 | 0 | 12.12s | 10.86s | 22.64s | 6226.25 | 6046 | 230.58 | 1142.33 |

## Warm-up calls (excluded from every figure above)

| Model | latency | input | cached | output |
|---|---|---|---|---|
| gemini-3.1-flash-lite | 4.4s | 6160 | 6046 | 343 |
| gemini-3.1-pro-preview | 16.28s | 6160 | 6046 | 257 |

## Bottom line — for the Red-tier flip decision

- **Yes — Pro resolved referents that Flash-Lite got wrong.** With the competing referent present, Flash-Lite failed 6/12 runs and Pro 0/12. The cases Flash-Lite broke on: B2h, B4h. This is the direct evidence the flip decision was waiting on.
- **referent class WITH a competing referent (Suite B-hard) — the discriminating test:** `gemini-3.1-flash-lite` 6/12 pass, 0 clarified, 6 fail; `gemini-3.1-pro-preview` 12/12 pass, 0 clarified, 0 fail
- **referent class, clean two-turn setup (Suite B):** `gemini-3.1-flash-lite` 3/4 pass, 0 clarified, 1 fail; `gemini-3.1-pro-preview` 4/4 pass, 0 clarified, 0 fail
- **ordinary routing (Suite A):** `gemini-3.1-flash-lite` 15/15 pass, 0 clarified, 0 fail; `gemini-3.1-pro-preview` 15/15 pass, 0 clarified, 0 fail
- **Per-reply latency cost:** the Coordinator is on the critical path ahead of every reply, so this is added to *every* turn — mean 1.88s → 12.79s, **+10.91s per reply** (median 1.82s → 12.49s; worst case 2.81s → 18.33s).
- **The latency is thinking tokens, not the model being slow.** Pro spends a mean 1119.07 thinking tokens per routing call on a task whose output is a fixed-shape context package. Flash-Lite spends none. That matters because the cost is not fixed: `_SYNTH_THINKING_BUDGET` is the existing precedent for capping it on an agent that does not need it, and the same lever exists here. **Three options, and they are Mike's to pick:** (1) flip as measured and accept ~+11s on every reply — the safest routing, the worst voice experience; (2) flip with a thinking budget capped, which needs one more probe run to show the referent fix survives the cap — cheap, and the only option that might get both; (3) do not flip, and fix the referent class in `coordinator.md` instead, since Pro's winning behaviour on B2h was to raise `CLARIFICATION_NEEDED` — a rule the agent file already states and Flash-Lite did not follow. **Option 2 first** — it is one run, and it is the only one that has not been ruled in or out by evidence already in hand.
- **No routing change is proposed here.** `config/modules/routing_cloud.yaml` is untouched. If Mike flips `coordinator` to Pro, the `[DB-0820-05]` disposition already requires the revert condition to travel with the flip so a trial cannot quietly become permanent.

---

*Raw results: `tests/coord_model_probe_2026-08-28_flashlite_vs_pro.json`. Regenerate with `python tests/run_coord_model_probe.py`.*
