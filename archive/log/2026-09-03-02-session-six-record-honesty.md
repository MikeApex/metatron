### 2026-09-03 (Session ⑥ — three bugs about the system reporting what it did not do)

Session ⑥ of the staged Mark 1 four, built to the 2026-09-02 handoff: `[DB-0829-01]`,
`[DB-0902-01]`, `[DB-0902-02]`, plus `[DB-0822-06]`'s derived-facts rider and `[DB-0822-09]`'s
surfacing diagnosis. Commit `54073b6`, deployed and VM-verified the same day.

The three bugs turned out to share a shape worth naming: **each is the system reporting a state
it never checked.** A gated action reported as completed, a routing success filed as a routing
miss, an empty queue reported as an empty inbox. In all three the honest answer was already
available in code and nothing was reading it.

**Three filed premises were wrong, and the corrections are the durable part.**

**1. `[DB-0829-01]` — the false email record did not come from where the item said.** The item
held that "the Coordinator dispatched a log write recording the send as fact". The 2026-08-29
trace splits that into two writes with opposite outcomes. The `relationships` specialist ran
`search_contacts → get_tone_shape → send_email` (returning `PENDING_CONFIRMATION`) `→ write_log`
in one agent, and its log content was **correct**: *"Initiated outreach to Iva Diamond... Pending
user approval in the app."* The agent that watched the gate fire got it right. The false record —
*"Sent an email to Iva Diamond to coordinate a call for next week."* — came from the
**fire-and-forget Diarist**, on its own thread and its own trace, dispatched at 13:00:12, **1.6
seconds into the turn and before the blocking specialist ever called `send_email`**. The
Coordinator had written its directive in the optimistic past tense of an action it expected to
succeed, and the Diarist had no relay by which anything could contradict it. Mike declined the
send at 13:05.

So the fix is dispatch **ordering**, not a log-write filter. Fire-and-forget agents are now
collected during the dispatch loop and started after the blocking specialists return, which is
the first moment the confirmation store is authoritative. `pending_directive_note()` then appends
a system-generated block naming the pending action and its description. Considered and rejected:
**suppressing** the dispatch when the directive asserts a gated action as done. It would also
discard everything else the turn asked to be journalled — a lost breakfast is a worse trade than
a corrected sentence — so the directive is corrected and the assertion is recorded as a
`FALSE_COMPLETION_CLAIM` quality event instead, which makes the residual risk measurable.

Two further defects fell out of the same trace, neither of them filed. `core/actions.py` had
**two** outcomes, completed and failed, and a gated call is neither: it reported `send_email —
completed` to the Synthesizer *and* to the journal (journalctl 13:00:18). And the live reply
*"That's sent to Iva."* matched **none** of `_COMPLETION_CLAIM_RES` — the `that's <verb>` pattern
covered only `done|sorted|taken care of` — so `enforce_pending_receipt()` took its *append*
branch and the user was shown the false claim and its correction stacked together. The item had
recorded that half as working correctly.

**2. `[DB-0902-01]` — it is the model, and the instruction gap the model exposed.** Filed as 5
instances; the live count is **15 since 09-01 and still firing on 09-03**. The handoff offered a
fork — template misuse by 3.7 Flash (Red) versus a slot code can sanity-check (Green) — and the
measurement says **both**, with the Red half being the primary cause.

Across all 34 ROUTING_MISS events in the live log: **19 before 2026-09-01, of which 0 are noise;
15 from 09-01 on, of which 13 are.** Three clean months, then a break exactly at the fleet
migration, with no code change in between. The pre-09-01 events are genuine and valuable —
several became work, including the referent fix built in session ⑤ the day before. The gap:
`config/agents/coordinator.md` defines `USER_CORRECTION` at length and **never defines
`ROUTING_MISS` at all**; line 208 lists it as an available event type and nothing says what one
is. The only definition in the repo is in `synthesizer.md`. `gemini-3.1-pro-preview` inferred it
for three months; `gemini-3.7-flash` fills the slot with a description of what it just did —
the same reflex already documented in `is_null_ish`'s docstring, that a field which looks
required gets filled with something plausible.

An early structural theory — *the Coordinator runs before the specialists, so it can never
observe a routing miss* — was **wrong and abandoned on the evidence**: the pre-09-01 events are
self-diagnoses of prior-turn misroutes, revealed by a correction in the current message, and
they are exactly the events worth keeping.

The Green half built is `asserts_routing_success()`: a ROUTING_MISS whose detail claims the
routing went right and names nothing that went wrong is self-contradictory with its own type.
Tuned for **precision, not recall**, because the two errors cost differently — dropping a noise
event costs nothing, dropping a real routing fault costs the signal the type exists to carry.
Measured on the full live corpus: **0 of 21 genuine misses rejected, 8 of 13 noise rejected.**
Negation handling is load-bearing and was found by measurement: the 2026-06-26 event *"Agents
not called successfully"* is a real miss that a naive keyword rule eats. A first, broader rule
did exactly that and was discarded rather than shipped. The five noise events it deliberately
lets through assert nothing about success and are merely descriptive (*"Coordinator test run
check"*); separating those from a real report needs the semantic guessing `[DB-0827-07]` was
closed to avoid, so they wait on the coordinator.md proposal.

**3. `[DB-0902-02]` — the queue was never filled, not drained.** The 08-30 14:45 pair, same
agent, same minute: the pipeline job called `read_intake_queue("logistics")`, got `count: 0`,
and said *"I've checked the inbox, and there are no new messages"*; the direct job called
`read_email` 26 seconds later and found ten unread. The suspect named in the item (intake queue
vs raw inbox) was right; the assumed mechanism was not. `read_intake_queue` advances a cursor on
read, so a drained queue was the obvious hypothesis — but the cursors file has **never had a
`logistics` key**. The real cause: **24 of 25 records in the live intake store carry
`domain: null` and `category: "unclear"`**, because the extractor is off behind `[DB-0820-03]`'s
eval gate, the persona has zero `rules:`, and `unclear` maps to a null domain. Under that
configuration the queue returns zero for **every** domain, permanently, whatever is in the inbox.

Nothing in the old return value said so — `"(nothing new for this domain)"` is true and reads as
"the inbox is empty". The empty answer now carries its reason, computed from config and the
store, and explicitly forbids the sentence Mike heard. Two independent fact-gathering paths,
because a first version put both in one `try` and a config read that raised swallowed the record
count as well; and a clause is added only when it was actually established, never assumed —
saying "the extractor is disabled" because the config could not be read would be the function
inventing the explanation it exists to supply.

**Diagnosis returned: `[DB-0822-09]`'s surfacing miss is NOT this split.** Asked directly by the
handoff, and the answer is no. On 2026-09-02 **both** runs called `read_email(count=15)` — the
same source. In the 11:36 pipeline run `logistics` produced a 536-token package and the
Synthesizer received 21,630 input tokens and emitted **177**: *"Your focus window remains clear
for the Apex migration delivery, Mike."* The Death Cab and Jimmy Carr items were in front of it
and were dropped. The remaining fix is Synthesizer-side, now confirmed rather than suspected,
and staged as a Red proposal with a recommendation to make HORIZON_ITEMS **structural** rather
than attempt a third instruction — the same reasoning `enforce_pending_receipt` records for
taking the report away from the model.

**Rider — `[DB-0822-06]`'s derived-count half, built after being twice declined.** The 08-27
session considered a code-computed derived-facts line and deliberately did not build it, with
the condition *"revisit only if a dated count still gets misread after deploy"*. The age
annotations shipped and the count was misread anyway on 08-30, 08-31 and 09-02 — three wrong
states across three days, spanning the model migration. The condition fired. Dating a sentence
("logged 9 days ago") is not the same as correcting the number inside it.

`derived_facts()` recomputes counts by subtraction from the date each line was written, on the
principle that **a count is only ever a claim about a date**, so given the date the count today
follows by arithmetic and nothing has to be believed. It validates against reality: *"Day 3"*
written 2026-08-21 puts day 1 at 2026-08-19 and a 5-day period ending **2026-08-23**, which is
exactly the date Mike's journal records the hiatus ending — and the same start and end are
derived independently from the separately-written 08-22 entry. Run against the four real log
files carrying such counts, all four periods are correctly reported as ended.

Kept deliberately narrow: two forms only (`day N of an M-day X`, `N days since X`), both pure
arithmetic over a stored date. Nothing requiring a judgement about whether a thing is still
true — that is the filtering this item has now twice decided against. It lands in
`augmented_input`, not the cached system prompt, so the Vertex prefix cache is undisturbed, and
returns "" when nothing parses, so a persona with no derived counts pays nothing.

**Regression.** Full suite 67 pass, 1 fail. The failure — `test_persona_resolver.py`,
*"list_personas finds mike"* — is pre-existing and **environmental**: `mike` lives only on the
VM, which owns live persona config, so the check can only pass there. Confirmed by stashing all
changes (identical failure on HEAD) and by running the suite on the VM, where it passes. Each
new suite was confirmed failing on HEAD before being counted: `test_pending_action_record.py`
fails 9 of 13, including the live *"That's sent to Iva."* text verbatim. A4 not run — suspended
and off the capstone close path (`ROADMAP.md` § Section 0 pt 8, amended 2026-09-02).

