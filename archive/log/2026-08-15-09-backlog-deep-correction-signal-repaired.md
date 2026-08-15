### 2026-08-15, ninth (`/backlog deep` — the correction signal was measuring itself wrong twice over) — `6e57c73`, `97b777c`, `2fa8cd6`, `704e79b`, `214a547`, `19cfd12` — **deployed by Mike**

Ran `/backlog deep`. **The sweep's own instrument turned out to be the largest finding**: the
`⚠ machine:` line Mike reads at every session start was wrong in two independent ways, and both
were only visible by measuring the live VM rather than reading the file.

**Fault A — 93 of 174 `USER_CORRECTION` events carried no information.** The literal strings
`"None"`, `"N/A"`, `"[N/A - the user's message is a shift in intent...]"`. They passed the
2026-08-10 blank-detail guard because they are not blank, and collapsed into `None. ×90` — the
loudest signature in the line. **The cause is a template, not a careless caller:**
`coordinator.md:88` carries `USER_CORRECTION:` as a slot in a fixed output block annotated *"omit
if not applicable"*, and a model filling a structured template answers the slot rather than
deleting it. **The agent file was deliberately not touched** — its instruction is already correct
and already ignored, which is the project's own argument for enforcing in Python. Mike's reaction
was the useful check: *"I don't think I've corrected the tool 90 times."* He had not; he had
corrected it ~84 times fewer than the line claimed.

**Fault B — a `×N` was a chain length, not a repeat count.** `SIMILARITY_THRESHOLD` was 0.15 over
Dice content words, and `merge()` **replaces the displayed line with each new member's text**, so
matching runs against the last link rather than the original. Adjacent pairs cleared 0.15 while
endpoints were unrelated. Proven by replaying the live events: the entry reported as *"scheduled
calendar events imply completion ×16"* began as **Heathrow travel corrections** and drifted across
five links into calendar-completion. Mike: *"agreed, those are unrelated entirely."* Fixed with
threshold 0.45 **and** correction-boilerplate stopwords — **neither alone splits the chain**,
because the shared words *were* the correction vocabulary. Replay now separates them and the top
real signature is a genuine ×4.

**Both faults are one root cause, and it now has three instances: a field that looks required gets
filled with something plausible rather than left out.** The `None` corrections, the invented
`eva@example.com`, and the 2026-08-10 `research_agent` source fabrication. That framing is what
made Mike's *"just invented email addresses, or any invented contact information more generally?"*
answerable: generalise to a **placeholder registry** (`555-01xx`, `123 Main St`, `@username`,
`John Doe`) — **not** to invented data in general, which cannot be detected without a source of
truth. The limit is stated inside `[DB-0815-06]` so the item is not mistaken for something bigger.

**Historical events are filtered at READ time, never deleted** — archive-on-merge. The stored
machine log was regenerated from the VM source, since the sync only ever processes new events and
the bad clusters would otherwise have persisted forever.

**CRM work, dispatched to one worker and merged** (`97b777c`, `2fa8cd6`): `merge_contacts` with
archive-on-merge and a `merged_into` pointer that `read_contact`/`search_contacts` follow (the
first implementation of that standing rule in the CRM), write-path dedup surfacing near-matches as
evidence, RFC 2606 placeholder-email refusal, and a narrow third-party-correction guard on
`write_profile`. **The worker flagged what it could not do rather than doing it silently** —
`core/orchestrator.py` was outside its manifest, so `merge_contacts` was unregistered.

**Registration was not enough, and only Mike's question surfaced that.** Registered in `704e79b`,
but the tool was in **no agent's `allowed_tools`**, so the per-agent schema filter hid it and
`relationships` could never have called it. **Registered-but-ungranted is the same shape as
`[DB-0810-17](1)`'s built-but-unregistered `read_google_contacts`** — a tool that exists and is
unreachable, in a codebase that has now produced the fault twice in one day.
`check_agent_tools.py` caught it within one edit.

**Corrections — things believed true earlier in this session that were not:**

- **Told Mike the voice item was "blocked twice."** Bulgarian speech-out had **shipped the day
  before** (`_EDGE_VOICE_BY_LANG`, `core/server.py:866`). It was invisible because the language
  session wrote its `archive/log/` fragment and never ran `build_project_log.py`, so the closure
  never reached the generated log. **A closure recorded only in an unfolded fragment is unreadable
  to everyone downstream.** Found only because `qa_sweep.sh`'s `project-log` check was failing.
- **Described the `×16` as a "similarity cluster of 16 different events"** before isolating the
  mechanism. Directionally right, specifically wrong: it is a *chain* with transitive drift, and
  `merge()` takes the **first** matching line in file order rather than the best-matching one.
- **`[DB-0815-04]` candidate (c) — eliminated by Mike's VM grep**, after this session had promoted
  it to most-likely. No transliteration line exists in `mike.md` or `mike/*.md`. *(A first grep
  used `mike/mike.md`; the real path is `config/personas/mike.md`, a **sibling** of the directory —
  `core/persona.py:255`.)* Left a residual worth its own item: a `SELF_APPLIED` event was recorded
  for a change that left no trace — `[DB-0815-11]`, and it is the **second wrong self-applied
  preference in four days**, both silent.

**Rejected:** fanning `/backlog deep`'s verify step out to three workers — three of the four
checkable `## Now` items shared two files, so inline verification cost less than one worker
briefing (~180k saved). The skill prescribes fan-out; the prescription assumes items are
independent, and these were not.

**Built at Mike's request — `@waiting:` / `@session:` / `@kind:` markers** (`[DB-0815-10]`), so an
item declares whether it can be picked up. **The `@` sigil cost two attempts**: bare `session:`
matched prose, and line-anchoring *also* failed because prose **wraps** onto a line beginning with
the word. Same trap `DUE_RE` documents, which escaped it only because a date is a strict value
shape. Markers ride inside items rather than forming a section, so an item keeps its rank in
`## Now` while saying it is blocked.

**Machine-log entries were counted nowhere** — 109 of them invisible beside 40 curated items, which
is why the line could not answer *"how much work is actually sitting here"*. Now counted apart and
**never folded into `later`**: they are the runtime reporting on itself, not tasks. Added the
derived `workable` (`now + later` minus parked). **Kind counts are suppressed until half the items
are tagged** — a partial tally reads as a breakdown when it is a floor.

**Threshold confusion worth recording:** Mike asked whether machine promotion was at ×5. It is
**×3** (`ESCALATE_AT`, and his own 2026-08-10 rule), and there are two thresholds people conflate —
×3 gets a `⚠` **automatically**, promotion into `## Now` is **always** a human decision at a
`/backlog` pass. Nothing auto-promotes. Note that **the ×3 bar only became trustworthy today**;
before Fault B was fixed it was firing on merge artifacts.

`## Now` re-ranked to 9: three promotions (the dead `OPENAI_API_KEY` silently costing a voice in
every multi-model round, the read-only half of Level 3 web access, venue discovery near a named
address), the shipped language feature demoted, and its A4 clinical-flag gap split out to Safety
as `[DB-0810-14]` rather than left buried in a finished item. `[DB-0815-12]` split from
`[DB-0808-04]` because two halves of one id break `qa_sweep.sh`'s backlog-ids check.

Also cut ~99 lines of superseded history from three live entries into
`archive/backlog_closed_2026-08.md`, verbatim — kept because in every case an earlier confident
diagnosis was overturned. **Net line change was only −3**, the trim having paid for the sweep's own
findings; Mike waived the line ceiling and made the design point that a backlog ceiling should key
on **item count, not lines**, filed into `[DB-0810-06]`.

**Two process gaps closed at Mike's prompting, both found because he asked why something was still
on screen rather than because anything failed.**

1. **The machine log had no removal step.** `/backlog deep` said *sweep* and *promote*; nothing
   anywhere said *delete an addressed entry*. So a signature whose cause had shipped kept its ⚠
   and kept leading the session-start line — Mike: *"you didn't clean up things that were already
   addressed like 'Contact name Eva'... or don't they and I have to ask for them?"* He did have to
   ask. Rule written into the `## Machine log` preamble: **an entry is deleted once its signal is
   promoted or its cause is fixed, leaving a pointer.** Applied: 22 entries cleared, 109 → 87, and
   **8 ⚠ → 3**. The three survivors are genuinely unaddressed and were filed as Inbox fragments
   rather than cleared — a deadline Mike has already stated being ignored (×4), an assumed-low
   energy baseline (×3), and his own email address being mis-transcribed (×3).
   *Recorded with the rule:* `.dev_backlog_seen` is what makes deletion safe, and **regenerating
   the section from the VM source bypasses that ledger and resurrects pruned entries** — which is
   what this session's own regeneration did, so the clearing had to follow it.
2. **The fragment filing route silently miscounted.** `fold_fragments()`'s docstring asks for
   "the same bullet form `## Inbox` already uses"; three fragments written this session did not,
   folded in as prose, and `_items()` reported **0 inbox** while three real items sat in the file.
   A filing route whose correctness depends on the writer remembering a format does not hold —
   `fold_fragments()` now coerces to a bullet. Verified by probe: a prose fragment counts, then was
   removed. **`/archive` step 4 writes fragments every session**, so this would have recurred
   indefinitely and only ever shown up as a number being quietly wrong.

**Threshold answer, since it was asked and the file did not make it obvious:** promotion is **×3**,
not ×5 — `ESCALATE_AT`, and Mike's own 2026-08-10 rule. The confusion is that **two thresholds are
conflated**: ×3 earns a ⚠ automatically; promotion into `## Now` is *always* a human decision at a
`/backlog` pass. Nothing auto-promotes.

`tests/test_null_ish_events.py` 43/43 (including that the two `is_null_ish` copies agree — the
stdlib-only constraint forces a second copy, so drift must fail a test); `tests/test_crm_dedup_guards.py`
18/18; `qa_sweep.sh` 9/9.

