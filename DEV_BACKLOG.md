# Development Backlog

Work outside the roadmap, in priority order. **`## Now` is the list** — everything else is
staging or reference. Refresh with `python3 scripts/sync_dev_backlog.py`; how and when to work
it is [docs/WORKFLOW.md](docs/WORKFLOW.md).

> **The one standing rule: no item is acted on, or re-filed, on the strength of its own
> description.** Open it against the current code first. A 2026-08-05 sweep found roughly a
> third of checked items stale — and a stale premise does not merely waste the check, it argues
> for the wrong decision, persuasively.

**Priority is Mike's call.** Claude proposes a tier; Mike sets it. The ordering within `## Now`
is the priority order. Closed items move to `archive/backlog_closed_2026-08.md` with the commit
or `file:line` that closed them — closed without evidence is not closed.

## Markers — what an item declares about itself

Four inline markers, parsed by `scripts/sync_dev_backlog.py` and counted on the sync line at every
session start. **Each sits at the start of its own line, inside the item.** They are properties of
items already counted in `## Now` / `## Later`, never a new section — an item keeps its rank while
saying it cannot be picked up today.

| Marker | Means | Counted as |
|---|---|---|
| `@waiting: <condition>` | blocked on an **event** that has not happened | `N waiting` |
| `@session: <question>` | needs a **working session with Mike** — a decision, not a build | `N session` |
| `@kind: bug\|feature\|chore` | a defect vs. something requested vs. upkeep | `N bug`, `N feature` |
| `` `due: YYYY-MM-DD` `` | a **clock** review date — the older convention, unchanged | `⚠ due:` |

**The sync line reads: `N new · N inbox · N now · N later · N workable (…) · N machine (M ⚠)`.**
`workable` is `now + later` minus anything `@waiting:` or `@session:` — *how much work is actually
sitting here*, which is the question the raw counts could not answer. **`machine` is counted apart
and is never added to `later`**: machine-log entries are the runtime reporting on itself, not
tasks, and one only becomes work when its signature reaches ×3. Before 2026-08-15 they were
counted nowhere at all, so 109 of them were invisible beside 40 curated items.

**Kind counts are suppressed until at least half the items carry `@kind:`** — a partial tally
reads as a breakdown when it is a floor, and a misleading number is worse than none.

`@waiting:` and `due:` are different questions and an item may carry both: *blocked on this,
re-check on that date*.

> **The `@` is not decoration.** A bare `session:` matched prose — *"Fixed same session:"*,
> *"never given its own session:"* — and anchoring to line start did not fix it either, because
> prose **wraps** onto a line beginning with the word. Same trap `DUE_RE`'s comment documents;
> `due:` only escaped it because a date is a strict value shape. Do not drop the sigil.

**Coverage is partial and the counts are a floor.** Only items touched on 2026-08-15 carry markers;
back-tagging the rest is `[DB-0815-10]`.

---

## Inbox

*Machine-written from what Mike said on the VM. Do not hand-edit — triage entries out into
`## Now` or `## Later`, rewritten properly, and delete them from here.*

*(empty — triaged 2026-08-10 by `/backlog deep`. All five entries verified against VM traces,
journal and conversations before filing; one was a false report the system wrote about itself.)*

*(empty — triaged 2026-08-14. All four entries were opened against current code before filing,
and **two were not what their description said**: the calendar reconciliation loop already exists,
and the evening-close repetition is a post-fix recurrence rather than a new bug.)*
*(Two `[dev-workflow]` items — the commit guard blocking routine shell, and `defaultMode: auto`
not being in effect — were moved out to a `HARNESS_BACKLOG.md` on 2026-08-13, because they are
defects in the tooling we build with and carry no Metatron content. **That file was retired and
deleted on 2026-08-14** when the build that opened it closed: eleven items opened, eleven
resolved. `defaultMode` was fixed; **the commit-guard false positives are deferred, not fixed** —
the `METATRON_COMMIT_GUARD=off` override now works, so each is a one-token annoyance rather than a
block. Revisit only when a case appears the override does not clear. **Do not re-file it here** —
this file is Metatron work. Full record: `archive/PROJECT_LOG.md` § 2026-08-14; see also
`.claude/rules/docs-and-logs.md`.)*
*(empty — triaged 2026-08-14 at close-out. Two notes filed by the §10b run-2 windows: window B's
became `[DB-0814-04]` in `## Later`; window A's was a `sync_dev_backlog.py` observation that
deliberately fails the filing bar and is recorded in `archive/backlog_closed_2026-08.md`
§ Closed 2026-08-14 instead.)*
*(empty — triaged 2026-08-15 by the second `/backlog deep` sweep. Two entries, both filed out:
the machine-written Bulgarian STT report was a **duplicate of `[DB-0815-02](a)`**, which Mike had
filed by hand the same day — closed to `archive/backlog_closed_2026-08.md` rather than opened as a
second item. The dev-session deliberation-leak note went to `## Later` under Safety and test gaps,
by the standing reporter rule. **The duplicate is worth one line of attention:** nothing checks a
machine-filed Inbox entry against items Mike filed himself that day, so the machine can restate a
report he has already made.)*
- **[needs building]** TfL/National Rail API integration bug: Status checks are passing station names (e.g., 'Charing Cross') instead of valid line IDs to the transport feed, causing 404 errors and masking live engineering works. Needs robust station-to-line-ID mapping.  
  `2026-08-16T08:13:28.789371Z`

- **Mike's own email address keeps being transcribed wrong, and he keeps correcting it.**
Machine log ×3: *"corrected dictation error of their email address from diamond.mic@gmail.com"* —
the exact near-miss `tools/crm.py`'s `_OWN_IDENTITY_SIMILARITY_THRESHOLD` was built to warn about.

**Partly mitigated already, which is why this is a check rather than a build:** `relationships.md`
carries a standing read-back instruction for every captured contact detail (2026-08-08), and the
CRM warns on a near-match to the user's own address. It is still recurring, so one of those is not
firing on this path — plausibly because the value is being captured somewhere that is not
`write_contact`. Establish which path writes it before changing anything.

*filed 2026-08-15 by the `/backlog deep` machine-log sweep. **Mike-originated**, ×3.*
- **The system assumes Mike's energy is low and he has corrected it three times.**
Machine log ×3. Signature: *"User corrected the system's assumption of low energy, stating they
have strong natural energy."* A standing fact about him being re-derived wrongly each time rather
than read from a stored baseline.

Check first whether `profile.yaml` / the aspirational baseline has somewhere for this and it is
simply unset, versus the assumption being generated despite a stored value — those need different
fixes and the item should not guess. Note the 2026-08-15 finding that `load_profile()` renders a
hand-written field list: a stored value that nothing renders would look exactly like this.

*filed 2026-08-15 by the `/backlog deep` machine-log sweep. **Mike-originated**, ×3.*
- **A deadline Mike has already stated gets ignored, and he is prompted to act early anyway.**
Machine log ×4 — the highest genuine repeat count in the file after the 2026-08-15 clustering fix,
and the only one that survived the sweep unaddressed. Signature: *"Missed the user's previously
stated Thursday deadline for the Prudential email and prompted action on it prematurely."*

The system holds the deadline (he said it), then raises the task before it. Same family as
`[DB-0809-02]` (an unanswered question re-raised by every job) and `[DB-0814-02]` (context nothing
ages out), but distinct: here the context is **present and correct**, and the timing logic ignores
it. `tools/obligations.py` stores due dates and `[DB-0814-04]` already shows a vague due date sorts
*below* an undated one — worth checking whether that same sort is what drops the date here.

*filed 2026-08-15 by the `/backlog deep` machine-log sweep. **Mike-originated** — every one of the
four is him correcting the system — so it clears the entry bar on its own, and at ×4 it clears the
machine bar too.*
- **24 of Mike's 59 wisdom entries are not facts about him — the WRITERS are half-fixed, the
store is not.** ⚠ **Updated 2026-08-18:** this item's own "upstream question worth answering
first" is partly answered. Live runs caught the Synthesizer writing *intentions* ("wants to
change breakfast") as standing facts, twice in two turns; `write_wisdom`'s schema and
`synthesizer.md` now separate an intention from a habit, and the next run kept a real observed
pattern while dropping the intention. `oatmeal_formula` is resolved — merged into
`standard_breakfast` with an archive pointer when step 10 ran. **Still open:** the eight
interaction preferences needing `write_persona`, the three tool defects, the remaining
duplicate pairs — and Mike's store still holds intention-shaped entries written before the fix
(`dietary_analysis_interest`, `lunch_options`).
 Found by reading every entry during the 2026-08-15 schema migration
(`a35acfa`) — the migration reports them and deliberately moves nothing, because relocating user
data is a separate act.

**Why a user would notice, which is what clears the bar:**

1. **Eight are interaction preferences sitting where behaviour rules cannot reach them** —
   `communication_style_preference`, `conversational_preferences`,
   `user_preference_interaction_fluidity`, `reduced_prompting_preference`,
   `system_framing_preference`, `admin_comms_reduction`, `14_point_checkin_consolidation`,
   `service_style_anticipation`, plus `avoid_travel_assumptions` which is a direct instruction to
   the tool. These belong in `config/personas/mike.md` via `write_persona`. **A preference stored
   as a fact is retrieved only if something thinks to look it up; a preference in the persona file
   is in every prompt.** Plausibly connected to the standing `⚠ machine:` correction signatures
   (`user corrected the assumption that sched ×16`, `user restated 'rucking and high intensit' ×4`)
   — worth checking, not asserted.
2. **`language_preference` duplicates `profile.yaml output_language`**, the real field
   `[DB-0810-15]` shipped the same day. Two homes for one setting, and the wisdom copy can drift
   from the one the code actually reads.
3. **`oatmeal_formula` is an unfilled placeholder** — its value is literally *"[User needs to
   specify their formula details here, I will log the request to record it.]"*. This is the worked
   example the whole knowledge-layering track was designed around; the real composition was in
   `profile.yaml health_notes`.

**The rest:** three tool defects filed against the user (`voice_transcription_issues`,
`bulgarian_speech_to_text_issues`, `crm_update_friction`); two recurring obligations that belong
in `open_obligation` per `logistics.md:189` (`monthly_financial_reminder`,
`rowan_payroll_schedule`, plus `manny_swim_schedule` which is a calendar constraint); two
near-duplicate pairs (`manny_swim_schedule`/`manny_swim_class`,
`post_travel_recovery`/`post_travel_energy_recovery`); one dated June observation
(`sleep_debt_pattern_june_2026`); one content-free entry recording only *that* a correction
happened (`grocery_check_in_cycle`).

**Do not bulk-move.** Persona data is VM-owned and each class needs a different destination.
`merge_wisdom_entries` handles the duplicates (archive-on-merge, never deletes); the preferences
need `write_persona`; the tool defects are already tracked and should just be deleted from the
store.

**The upstream question worth answering first:** what wrote these? Eight interaction preferences
landing in a fact store suggests an agent instruction pointing at `write_wisdom` for material that
should go to `write_persona`. Fixing the writers matters more than cleaning the store, or it
refills.

*raised by Claude during the 2026-08-15 knowledge-layering session, from reading all 59 live
entries · full per-entry assignment and reasoning in `scripts/migrate_wisdom_schema.py` KEY_MAP*
- **The A4 safety regression passes without ever touching the knowledge layer.** `run_a4_safety.py
--suite pipeline` runs against `sarah_chen`, and her VM wisdom store holds **one** entry — a work
boundary pattern no clinical scenario touches. So the manifest renders one subject, no
`KNOWLEDGE_TO_LOAD` fires, and 3/3 PASS says nothing about whether standing knowledge interacts
safely with clinical flags. This matters because the knowledge layer now injects fetched entries
into specialist directives, including `mental_wellbeing`'s: an entry that contradicts a clinical
read is exactly the case nothing currently exercises.

Giving it coverage means health-domain entries on the **VM's** `sarah_chen` — either seeded
deliberately or accumulated through use. **Not done on purpose:** seeding a clinical-adjacent
fixture changes safety-test conditions, and that is a decision rather than a chore. A4's own
`seed_medication_fixture` is the precedent for how to do it if the answer is yes.

Related trap, found the same day: **the Mac and VM copies of a persona store diverge silently.**
`sarah_chen` held 38 entries on the Mac and 1 on the VM, and `data/personas/*/` is gitignored so
nothing reconciles them. That divergence produced a confidently wrong recommendation — "migrating
her makes A4 exercise the knowledge path" — which was true of the Mac copy and false of the one
A4 runs against. Anything reasoning about a persona's data has to name which machine it read.

*raised by Claude at the close of the 2026-08-18 knowledge-layering session, after A4 passed 3/3
twice against an empty manifest · both stores are now migrated; only the coverage gap remains*

---

## Now

**Ranked — position is priority.** Capped at ~10, so something enters by displacing something.
**The entry bar is that Mike raised it**, with one standing exception that must not widen: a live
credential exposure or data-loss risk enters regardless of who found it. Both rituals — ranking
each item as it arrives, and the reporter asymmetry — are in [docs/WORKFLOW.md](docs/WORKFLOW.md).

*Re-ranked 2026-08-10 by Mike after a `/backlog deep` sweep verified every entry against the VM
(traces, journal, conversations) and corrected three whose stated evidence did not survive.
Reasoning lives in `archive/PROJECT_LOG.md` § 2026-08-10, last. Every entry carries what was
checked and when; a verdict without that line is a description, and descriptions are what the
standing rule distrusts.*

- **1. [DB-0808-04] Finding a venue near a named address — no GPS required.**
  *(b) of this item only.* Google Places venue discovery for `logistics` / `recreation_hobbies`
  was filed as blocked on the real-time location signal in (a), but **"near a named address" needs
  no GPS and can ship on its own** — the entry says so itself and it went unread. *(a)* real-time
  GPS and proactive area-scanning still needs a design pass (privacy tier for continuous location,
  which layer supplies it, how scanning bounds itself) and stays in `## Later`.
  @kind: feature
  *filed 2026-08-08 by Mike · **(b) promoted 2026-08-15**, (a) stays parked*
  *No `@session:` marker: (a) became its own `## Later` entry on 2026-08-15, so the decision it
  was waiting on is not this item's. Carrying it here excluded a buildable item from the workable
  count — a marker scoped to half an item cannot be seen by the counter, which reads per item.*


## Later

### Moved out of `## Now` 2026-08-18 — not buildable, so not sitting in the list

**Mike's rule, stated 2026-08-18: anything not buildable moves to `## Later` and does not sit in
`## Now`.** `## Now` is what can be picked up; an item waiting on a live exchange, on a decision, or
on nothing-that-can-be-done is not that, however high it would rank if it were actionable. All four
below keep their full text and their `@waiting:`/`@session:` markers — they are parked, not
downgraded, and each says what would bring it back.

**On `[DB-0815-04]` specifically:** the transliteration-vs-Cyrillic *render* has a deployed fix
awaiting one live turn, but the item it is entangled with — Bulgarian speech-in, `[DB-0815-02](a)` —
**has no viable solution right now** and is held indefinitely by Mike's decision: `base.en` cannot
emit Cyrillic at all, multilingual `base` gets the right script at 46.4% WER, and `small` gets
27.6% WER at an RTF of 0.967 that leaves no queueing headroom on a single-worker pool. Neither
clears a usable bar. Revisit only on a materially better local multilingual STT model or a hardware
change — not on a schedule.

- **[DB-0815-04] In Bulgarian mode the app shows Latin letters where it should show
  Cyrillic.** Mike verified live 2026-08-15 with `output_language: bg` set on his own persona:
  **the agent receives Cyrillic and understands it correctly**, so input and comprehension are
  fine — what is wrong is what the app puts on screen. The response renders transliterated
  ("Dobro utro") instead of Cyrillic ("Добро утро").
  **Three candidates, and (c) was found 2026-08-15 by the `/backlog deep` machine-log sweep. It is
  the most likely of the three and it was not visible from the app at all:**
  *(a)* the translation backend is returning transliteration — `core/translate.py`'s prompt says
  "Translate the user's message into {language}" and does **not** say *in Cyrillic script*, which a
  model can satisfy with romanisation. **Confirmed present in the prompt, but it cannot be the whole
  story** — `core/translate.py` contains no transliteration logic anywhere, and it does not run at
  all for a persona with no `output_language` set.
  *(b)* the client mangles it — `static/index.html` serves both web and APK, so a font or encoding
  fault would show in both.
  *(c)* **the Synthesizer decided to answer in Latin script and wrote itself a rule saying so.** A
  `SELF_APPLIED` quality event at `2026-08-15T13:51:39Z` reads verbatim: *"Switched output to
  Bulgarian transliteration (Latin alphabet) to match user's STT workaround."* — two minutes after
  Mike's STT complaint at `13:49:35Z`. So the system read his Latin-script workaround (forced on him
  by the English-only STT model, `[DB-0815-02](a)`) as a standing preference and self-applied it.
  **This is the second wrong self-applied preference in four days** — the first was the evening
  check-in consolidation on 08-12 — and both were silent.
  **Check (c) first, and it is one look, not a test:** does `config/personas/mike/mike.md` or
  `profile.yaml` **on the VM** now carry a transliteration or Latin-script line? If yes, the Latin
  render is a stored preference, the fix is removing it *and* stopping `write_persona` self-applying
  script choices, and (a) becomes belt-and-braces. If no, fall back to (a) — call
  `translate("Good morning.", "bg", "Bulgarian")` on the VM and read the raw string; Cyrillic means
  the fault is client-side, Latin means it is the prompt and the fix is one line.
  **✅ (c) ELIMINATED 2026-08-15 — Mike grepped the VM.** `config/personas/mike.md` and
  `config/personas/mike/*.md` carry no transliteration, Latin-script or Cyrillic line. *(Note the
  path: `mike.md` is a **sibling** of the `mike/` directory — [core/persona.py:255](core/persona.py#L255)
  — and a first attempt grepped `mike/mike.md` and found nothing because nothing is there.)*
  **A residual worth its own attention, and it is not this item:** a `SELF_APPLIED` event was
  recorded for a preference change that left no trace in any persona file. Either it wrote
  somewhere unexamined or **it reported an action it did not take** — the class `[DB-0810-13]`
  closed on 08-15. Honest caveat: Mike reverted his language test the same day, so "written then
  reverted" cannot be distinguished from "never written" without a VM backup. Filed as
  `[DB-0815-11]`.
  **✅ (a) FIXED 2026-08-15, not yet verified live.** `_SYSTEM_PROMPT` in
  [core/translate.py](core/translate.py) now requires the standard native script and names the
  Bulgarian case concretely. **This item closes when Mike sets `output_language: bg` and sees
  Cyrillic** — if he still sees Latin, the answer is (b), the client, and the diagnosis is now
  down to one candidate.
  @kind: bug
  @waiting: one live exchange with `output_language: bg` after the next deploy
  *filed 2026-08-15 by Mike from live testing · the feature otherwise works — he confirmed
  Bulgarian in and out before switching back to English*

- **[DB-0815-05] Contact corrections were being written into Mike's own identity, and rode in
  every system prompt.** Found 2026-08-15 while verifying the language render on the VM. His
  `profile.yaml` `name` field contained **"Contact name updated from Eva to Iva."**, and the
  `other` list held six facts about *other people* (Iva Diamond, Horatiu Stefan, Eva's office
  availability). `load_profile()` renders all of it, so every head-layer call — every session,
  every scheduled job — was told the user's name was that sentence.
  **This is almost certainly the mechanism behind a correction Mike has made five times**: the
  machine log's `corrected contact name from "eva"` sits at ×5. Each correction appears to have
  landed in the profile rather than the contact record, so the system kept getting the name wrong
  *and* accreted the evidence of getting it wrong into its own view of who the user is.
  **Same class as the incident `tools/profile.py` was built for** (2026-08-02: email, postal
  address and phone landing in the persona preferences file and riding in every prompt) —
  recurred in a new direction, contact data into the profile rather than out of it.
  **Data corrected on the VM 2026-08-15** (`name` → `Mike`, `other` cleared, backup at
  `profile.yaml.bak-2026-08-15`). **The write path is NOT fixed and is the item**: nothing stops
  the next contact correction going to the same place. Find which tool call wrote it — `crm.py`'s
  `write_contact` and `profile.py`'s `write_profile` are both reachable from the same turn, and
  the model chose wrong. A schema-level fix (profile refuses text naming a third party) is
  cheaper than an instruction.
  **✅ BUILT AND DEPLOYED** (`97b777c`, registered `704e79b`): `write_profile` refuses a `name` or
  `other` value that reads as a third-party contact correction and points the caller at
  `write_contact`. Narrow and conjunctive by design — subject word **and** correction verb **and**
  a "from...to" span, or a `name` that is a long sentence; verified not to refuse "Robert Smith Jr."
  or an ordinary fact containing "from"/"to". **Not closed**, because what is being tested is
  whether the *model* now picks the right tool, and that is behaviour, not code.
  @kind: bug
  @waiting: one live turn where Mike corrects a contact name, then check `profile.yaml` is untouched
  *filed 2026-08-15 · data corrected the same day · guard built and deployed 2026-08-15*

- **[DB-0815-07] CRM writes are never deduplicated against existing contacts, so the same
  person accumulates records.** Three live instances in eight records, found 2026-08-15:
  *(a)* **`Eva` and `Iva Diamond` were one person** — Mike's family member, surname Diamond,
  first name spoken as "Eva". He corrected the name **five times** (machine log, ×5) and the
  correction never merged the records; both survived every correction. Merged by hand 2026-08-15,
  Eva archived with a `merged_into` pointer.
  *(b)* **`Kathaleen Jermyn` vs `Kathleen Jermyn`** — the spoken name did not match the spelling
  in the email. Mike: unimportant contact, **no action on this instance**, but it is the shape to
  catch.
  *(c)* `_find_by_name` is naive substring matching, so `Jon`/`Jonathan`/`Jonathan Whitfield`
  become three records — already noted under `[DB-0810-11]`.
  **Mike's requirement, 2026-08-15: "CRM entries should be intentionally deduplicated against
  existing entries, otherwise this will happen often."** So dedup is a write-path check, not a
  periodic sweep — `write_contact` should surface near-matches as evidence before creating, the
  same "evidence, not a verdict" pattern `tools/scheduling.py` and the calendar duplicate audit
  already use. Fuzzy matching must cover **speech-to-text near-misses** (Eva/Iva, Kathaleen/
  Kathleen), which is exactly what `difflib.SequenceMatcher` is already used for elsewhere in
  this same file.
  **Blocking prerequisite, found the same day: the CRM has no merge or archive tooling at all.**
  No `delete`, no merge, no `merged_into` support — the 2026-08-15 fix was hand-written JSON, and
  the project's standing **archive-on-merge** rule (data is never deleted, it moves to archive
  with a pointer) is therefore unimplemented here. Detecting a duplicate is useless without a
  supported way to resolve one. **Build the merge path first.**
  **✅ BUILT AND DEPLOYED** (`97b777c`, registered `704e79b`). `merge_contacts` folds one record
  into another, unions the list fields, keeps the more recent `last_contact`, and **archives rather
  than deletes** with a `merged_into` pointer that `read_contact` and `search_contacts` follow — so
  the old id *and* the old name keep resolving. `write_contact` now surfaces near-matches as
  evidence before creating; Eva/Iva and Kathaleen/Kathleen both trip it. **The archive-on-merge rule
  is implemented here for the first time.** **Not closed** for the same reason as item 2: whether an
  agent actually calls `merge_contacts` when shown a near-match is behaviour.
  @kind: bug
  @waiting: one live near-duplicate surfaced, and an agent resolving it with `merge_contacts`
  *filed 2026-08-15 by Mike · (a) resolved in data, tooling built and deployed 2026-08-15 · same
  dedup risk flagged for the Google Contacts pull in `[DB-0810-17]` — a bulk import makes it acute*

- **[DB-0809-02] Every scheduled job re-asks the same unanswered question, so one unfinished
  ritual arrives as three or four separate messages.** *(Retitled 2026-08-15 — the trace week is
  **answered three days early and all three prior hypotheses are wrong**. Read the finding below
  before the history; the history is kept because two earlier diagnoses were also confidently
  wrong.)*
  **The finding, read live off the VM 2026-08-15.** Mike's *"three separate, repetitive messages for
  the evening close out"* (reported 08-12, about the night of **08-11**) was **four different
  scheduled jobs**, each identifiable by its own prompt text: `companion_checkin` 16:46 opened the
  evening close and the virtue review; an inbox-check job 18:13 re-asked the same two questions;
  `companion_checkin` 19:48 re-asked them; `evening_close` 20:00 re-asked them a third time. He
  counted three because the first was the one he called *"fine"*.
  **So `evening_close` is a victim, not the culprit, and `_frame_proactive()` is working** — none of
  those responses read the scheduler prompt as Mike's voice. **The mechanism is that "raise a thing
  once" has no memory that a question was asked and left unanswered**, so every unrelated job that
  fires inherits the unfinished ritual from context and raises it again. Any fix belongs there —
  either that rule gains cross-session state, or jobs other than the ritual's own are forbidden from
  continuing it. **Do not re-apply the ≤2-sentence cap**; it was rejected deliberately, focus being
  the target and length only its symptom. Same family as `[DB-0814-02]` (stale context that nothing
  ages out), and worth scoping against it.
  *The 2026-08-17 due marker is spent (de-tagged 2026-08-15 so it cannot false-wake the sync) — the
  recurrence with a known date was worth more than seven ordinary days, exactly as the item
  predicted.*
  **The fix that is already in and must not be undone:** `82d394b` (deployed) —
  `_frame_proactive()` labels scheduler input as a directive in both pipeline copies
  ([core/orchestrator.py:3089](core/orchestrator.py#L3089), called at `:3134` and `:3264`), and the
  repeated-instruction protocol requires the *user* to have repeated it. It works; it just does not
  address this.
  **Two prior diagnoses were confidently wrong before this one — the narrative is in
  `archive/backlog_closed_2026-08.md` § Closed 2026-08-15, and it is worth reading before proposing
  a third.** The reusable trap: the quality-events file keys on **`timestamp`, not `ts`**, so a read
  against `ts` returns nothing and looks like a clean day.
  @kind: bug
  @session: which fix shape — give "raise a thing once" cross-session memory of an unanswered
  question, or forbid a job from continuing a ritual that is not its own. Two prior diagnoses were
  confidently wrong; the third should not be picked without Mike.
  *filed 2026-08-09 · rewritten 2026-08-09 after measurement inverted it · **evidence corrected
  2026-08-10** — see `archive/PROJECT_LOG.md` § 2026-08-10, last · **recurrence merged in from the
  Inbox 2026-08-14**, reported by Mike via the VM (2026-08-12T08:23Z); fix date verified against
  `git log` the same day*


**Time-gated — parked here deliberately, not deprioritised.** Each carries a `due:` marker, which
`due_now()` in `scripts/sync_dev_backlog.py` scans across **both** `## Now` and `## Later` and
surfaces as a `⚠ due:` clause on the sync line **at every session start** — so these wake
themselves without anyone running `/backlog deep`. The date is a **review date, not a deadline**:
for the two gated on a condition rather than a clock it means "re-check whether the condition has
arrived", and if it has not, push the date rather than closing the item.
**Promote back into `## Now` when the condition is met — that is Mike's call, not automatic.**
*(Convention introduced 2026-08-15 by Mike, after a `/backlog attack` found three of six `## Now`
items unworkable, which is what made the ranked list misleading: `## Now` must mean workable.)*

- **[DB-0809-21] Three of four verification steps done and passed; one is genuinely time-gated.**
  Ran at ~$0.08, under the $1.00 approval line (`docs/CONVENTIONS.md` § Testing Cost Convention).
  **Done:** (1) A4 `clinical` suite vs `sarah_chen`, 3/3 — confirms the regression gate held.
  (2) Three targeted Physical Health calls vs `danny_park`, which do assert `6330029`/`88b7614` —
  all passed, including the deep-merge behaviour that fix protected. (4) The first natural
  `companion_checkin` fired unforced at 07:20 on 08-10 and was clean *(its evidence line inherited
  the same "zero quality events" error corrected in `[DB-0809-02]` above — the surviving check is
  `is_proactive: true` plus no `INSTRUCTION_CHANGE_REQUEST`)*. Never forced against Mike's real
  persona, which would have written a synthetic exchange into his real history.
  **Open, time-gated:** (3) `daily_calendar_reconcile` re-ran clean with 0 candidates, so the
  mechanism works, but **no live candidate has yet existed** to observe being raised as a question.
  Needs a real unreferenced calendar event, not a forced one.
  *filed 2026-08-09 · **Mike deferred it explicitly** · 3 of 4 done 2026-08-10*
  `due: 2026-09-01`


- **[DB-0810-05] The tone-profile pipeline has never touched a real mailbox.** Built and
  committed `88957e6`; **every test used stubs.** The distillation half is well covered — a hostile
  fixture confirmed unknown keys dropped, values truncated, lists capped, injection caught and the
  write refused, plus five `_extract` paths (single-direction refusal, thin-sample skip, injection
  block, happy path, mailbox error). **What is entirely unexercised is the IMAP half**, which is
  the part most likely to behave differently against live Gmail:
  1. **`_sent_folder()` discovery** ([tools/mail.py](tools/mail.py)) — `conn.list()` parsing for the
     `\Sent` SPECIAL-USE attribute, with `[Gmail]/Sent Mail` and `Sent` as fallbacks. If this
     returns `None` the run refuses by design, so the *visible* failure is "nothing happened"; if it
     returns the **wrong** mailbox the profile is silently built from one direction, which is the
     failure the refusal exists to prevent.
  2. **Tier `SEARCH` syntax** — four `FROM`/`TO` + `BEFORE`/`SINCE` queries per direction. Date
     arithmetic and tier contiguity were verified offline (no gaps, no overlap, correct across year
     boundaries); what is untested is whether Gmail accepts the term ordering as constructed.
  3. **Batched `BODY.PEEK[]` parsing** in `_fetch_bodies()` — chunks of 50, tuple-shaped responses.
     Most likely single point of failure; a malformed chunk is skipped silently by design, so a
     partial parse would look like a thin mailbox rather than a bug.
  **Read 2026-08-10.** The unattended run (trace `f6d7efe5`, 21:52, the Iva invite) wrote
  `tone_shape: ""` — nothing leaked, but not for the reason this item was written to check.
  `_sample_direction()` passed the Gmail Sent folder name (`[Gmail]/Sent Mail`) to
  `conn.select()` **unquoted**; IMAP requires quoting for names with spaces, so the call threw
  `imaplib.IMAP4.error: BAD Could not parse command`, uncaught, before the model extractor ever
  ran. Confirmed by reproducing directly on the VM and by re-reading the (previously
  self-filtered-out) `journalctl` warning. This is not contact-specific — it fires on **every**
  sent-side query against this mailbox. **Fixed same session:** `_imap_quote()` added to
  [tools/mail.py](tools/mail.py), applied at all three `conn.select()` call sites; re-verified
  live against the same address post-fix — `sent_folder_found: true`, clean `counts` dict, no
  crash.
  **Still open — the item's real question is unanswered.** Point 1 above predicted this class of
  failure but not this exact shape; points 2 and 3 (SEARCH term ordering, batched body parsing)
  and the actual target — the model extractor running against real correspondence, schema
  reduction and injection-marker backstop holding under live data — have **never fired**, because
  nothing got past the Sent-folder select until now. Also found while investigating: the
  dedicated mailbox (`diamond.mike.mt@gmail.com`) has essentially no history yet — 1 Sent message
  (to self), 6 Inbox messages total — so **no contact currently has enough real correspondence to
  run the intended test against.** Re-run `get_tone_shape(refresh=true)` once a contact has real
  back-and-forth in that mailbox. **Pass:** `sent_folder_found: true`, both
  `counts.written_by_user` and `counts.received` non-zero, and a `tone_shape` a human recognises
  as accurate. **Fail loudly on:** any life event, date, or third-party name in the profile.
  *filed 2026-08-10 by Mike at the close of the build session · re-investigated 2026-08-10:
  IMAP quoting bug found and fixed, original pass/fail criteria still unmet — no long-history
  contact exists yet to test against*
  `due: 2026-09-01`


- **[DB-0814-02] Stale threads now expire — but neither signal that keeps one alive has been
  measured against real output.** *(Retitled 2026-08-15. The expiry policy is **built and
  deployed**; what is open is narrower and specific.)*
  **Shipped `37b0b03`, merged `eb01025`, plumbing `5cf0a5e`, deployed.** Open threads auto-drop 7
  days after their `added` date, archived to `expired_open_threads` (capped 50, never loaded into
  context) rather than deleted. **Grace — what keeps a thread alive — keys on the *user* engaging
  it**, not on the Synthesizer resending it: the Synthesizer rewrites the entire thread list on
  every response, so its resending something says nothing at all. That is the same correction
  `82d394b` made to the repeated-instruction protocol. The pipeline passes the user's turn only on
  real sessions (`None if is_proactive`), because a scheduler prompt is not the user speaking.
  **The first version of this was wrong and is worth remembering:** grace keyed on the thread being
  present in the model's output that turn — true of every live thread on every write, which would
  have granted "post-travel recovery" grace on all two weeks of writes. Its tests passed because
  they modelled *resent* but never *resent by a caller that resends everything*.
  **What is actually open, both flagged by the worker that built it:**
  1. **Word-overlap grace can false-positive on short, generic threads.** "call the dentist" against
     an unrelated "call mom later" shares one of two content words — overlap 0.5, clears the 0.34
     threshold. `_USER_ENGAGEMENT_OVERLAP` was reasoned, **not measured against real transcripts**.
  2. **Material-change grace is triggerable by a one-character diff**, since it rides on exact-text
     non-match. Nothing distinguishes genuine rework from cosmetic phrasing drift — close to a
     second copy of the bug this closes, needing one changed character per turn instead of zero.
     **If real Synthesizer output varies wording turn to turn, this is live**, and the fix is a
     similarity check over the exact-text merge (`core/rule_classes.py`'s `similarity()` is the
     model).
  **⚠ How it closes was checked against the VM on 2026-08-15 and the stated method does not work —
  the data it assumes does not exist.** "Read a week of real `context.json` writes" cannot be done:
  1. **`context.json` is overwritten in place.** It is one mutable file per persona, not a dated
     series like `data/logs/`, so there is no write history to read. The live file for `mike` was
     476 bytes — one open thread, `follow_ups: []`.
  2. **`expired_open_threads` is not in the live file at all.** Expiry deployed 2026-08-15 with a
     7-day cutoff, so nothing can have crossed it before **~2026-08-22**. Until then the archive
     that would evidence the expiry path is empty by construction.
  3. **Traces do not record the write.** `write_context_tracker` does not appear in
     `/monitor/traces` records at all (checked against `persona=mike`); a trace carries
     `user_input`/`synth_response`/`pipeline`, not tool arguments. The string `open_threads` does
     appear — inside prompt/response text — which is a false lead worth naming so the next session
     does not mistake it for the write being logged.
  **So this item is time-gated, in the same class as `[DB-0810-05]` and `[DB-0809-21]`, and that
  was not visible from the entry.** Before it can close, someone must give it a data source that
  will exist: the cheapest is to have `write_context_tracker` append a line per write to a dated
  audit file (cheap, and it is the same "instrument the absence" argument as `[DB-0809-08]`);
  otherwise it waits until after ~2026-08-22 and closes off `expired_open_threads` alone, which
  evidences expiry but **not** the two grace signals — those fire on threads that never expire, so
  the archive is silent about exactly the thing being measured.
  **Do not dispatch a worker on the measurement half until one of those exists** — a worker was
  scoped for it on 2026-08-15 at an estimated 150–190k and would have spent it discovering the
  above.
  *close condition invalidated 2026-08-15 by the coordinating window, checked live against the VM
  rather than inferred*
  *filed 2026-08-14 by Mike via the VM · timestamp half closed 2026-08-15 · expiry half built and
  deployed 2026-08-15, thresholds unvalidated*

  *The timestamp half (`d40e73c`) closed 2026-08-15 — narrative in
  `archive/backlog_closed_2026-08.md` § Closed 2026-08-15.*
  `due: 2026-08-22`


- **[DB-0814-04] An obligation with a *vague* due date is the first thing dropped from session
  context — the exact opposite of the intended priority.** `context_block()` in
  [tools/obligations.py](tools/obligations.py) sorts by `str(it.get("due") or "9999")`. The
  `"9999"` sentinel is meant to sink undated obligations to the bottom, and it does — but a
  vague phrase sorts **lexically after it**: `["2026-08-20", "2026-09-01", None, "next week"]`
  is the real order, verified by running it 2026-08-14. With `_CONTEXT_MAX = 6`, an obligation
  the user gave a soft deadline to therefore ranks below every undated one and is dropped first.
  **`OPEN_OBLIGATION_SCHEMA` explicitly invites the vague phrase** (*"or short phrase if
  genuinely vague"*), so this is the schema's own documented input hitting a lexical sort, not
  misuse. User-noticeable: the store silently stops surfacing a commitment that carries a
  deadline — which is the failure the obligation store was built for in the first place
  (see the module docstring's 2026-08-07 incident). Not fixed on the spot: the file was under a
  two-window collision at the time and that session was comment-only.
  *filed 2026-08-14 by the §10b run-2 window B, which verified the sort order by running it
  rather than reading it · not raised by Mike, so `## Later` by the standing rule*

Real, not prioritised. One or two lines each — detail lives in the code, the log, or
`archive/backlog_closed_2026-08.md`.

**Two standing rules, both Mike's (2026-08-10):** a **machine-originated** item promotes to
`## Now` once its error has been **recorded three times** (the ×3 threshold the machine log
uses — count before promoting), while **anything Mike raises promotes on first report**, no
count — the ×3 bar is a floor for things nobody asked for, not a hurdle for a user report
(clarified 2026-08-13; the rule read "an item", which contradicted `## Now`'s entry bar and
`/backlog`'s "promoted the day he hits it"); and **`Now` is cleared before `Later` is started**,
so this is not a parallel track to pick from when a `Now` item is time-gated.

- **[DB-0815-11] The system recorded a preference change it appears never to have made.** A
  `SELF_APPLIED` event at `2026-08-15T13:51:39Z` reads *"Switched output to Bulgarian
  transliteration (Latin alphabet) to match user's STT workaround."* Mike then grepped
  `config/personas/mike.md` and `mike/*.md` on the VM: **no transliteration, Latin-script or
  Cyrillic line exists anywhere.** So either the write landed somewhere unexamined, or the system
  reported an action it did not take — the class `[DB-0810-13]` closed on 2026-08-15 with action
  provenance, which makes a fresh instance worth understanding rather than assuming closed.
  **Honest caveat that must not be dropped:** Mike reverted his language test the same day, so
  "written then reverted" cannot be distinguished from "never written" without a VM backup. Check
  `profile.yaml.bak-2026-08-15` and any `mike.md` history before concluding.
  **The second-order concern is the one that matters:** this is the second wrong self-applied
  preference in four days (the 08-12 evening check-in consolidation was the first, and Mike
  rejected it). Both were silent. Whether `write_persona` should self-apply an inferred preference
  *at all* without confirmation is the real question, and it is his to answer.
  @kind: bug
  @session: whether a self-applied preference needs a confirmation gate
  *filed 2026-08-15 by the `/backlog deep` sweep, from the machine log*

- **[DB-0815-10] Backlog items now declare whether they can actually be picked up.** Mike,
  2026-08-15: a way to mark items *waiting for an event* or *needing a development session*, and to
  tell a **bug** from a **requested feature**, counted at session start. **BUILT** in
  `scripts/sync_dev_backlog.py`: `@waiting:`, `@session:`, `@kind: bug|feature|chore`, written at
  the start of a line inside the item, counted across `## Now` + `## Later`, and printed in
  parentheses so they never read as a fourth section.
  **The `@` sigil is load-bearing and cost two attempts.** A bare `session:` matched prose
  (*"Fixed same session:"*, *"never given its own session:"*), and anchoring to line start did not
  save it either, because prose **wraps** onto a line beginning "session:". Same trap `DUE_RE`
  documents; `DUE_RE` escaped it only because a date is a strict value shape. **What remains:**
  back-tag the rest of the file — only the items touched on 2026-08-15 carry markers, so the counts
  are currently a floor, not a total.
  @kind: feature
  *filed and built 2026-08-15 at Mike's request · `tests/test_null_ish_events.py` 43/43*

**Safety and test gaps**
- **[DB-0810-14] The A4 clinical hard-fails have never run with a response language set.**
  They cannot regress while no persona has `output_language` (translation is a no-op), but once one
  is translated, flag *substance* must survive translation — the pipeline suite's pass condition is
  that crisis framing and medication names reach the user, and that has only ever been checked in
  English. **Run `tests/run_a4_safety.py --suite pipeline` against a translated persona before any
  persona with clinical history gets a response language.** Bears on `ROADMAP.md` § 0 clause 8.
  @kind: chore
  *split out of `[DB-0810-15]` 2026-08-15 when that item was demoted — a safety gap should not be
  parked inside a shipped feature's entry, which is how it would have been lost*
- **[DB-0815-08] The Synthesizer quoted its own instruction file to Mike, and only the filter
  stopped it — nothing detects why it happened.** Tier 4 of `filter_output()` (`bbda875`) now
  suppresses a response reproducing 10+ verbatim words from the agent's instruction file or the
  constitution, built after the Synthesizer printed its own deliberation to Mike on 2026-08-12.
  **The filter is the backstop; the instruction layer is the control, and the instruction layer is
  what failed.** The leak was truncated mid-sentence, which suggests the response was cut off rather
  than completed — so the same shape can recur without tripping tier 4 at all if the quoted span is
  shorter or paraphrased. **One cheap check first:** whether Gemini reasoning content can reach
  `text_parts` on the streaming path. If it can, this is a plumbing fault, that is the real fix, and
  tier 4 is belt-and-braces. Bears on `ROADMAP.md` § A7 check 5, which has this on record as a live
  Fail. *filed 2026-08-15 by a dev session — **not raised by Mike**, who saw only the original leak,
  which is closed. Evidence: `/monitor/conversations` persona=mike ts=2026-08-12T00:14:57, 711
  chars, all deliberation, no `[CONTEXT]` block*
- **[DB-0810-10]** The calendar conflict build (`a20febe`, deployed 08-05) has **never had a
  live scheduling exchange run against it** — all 24 tests in
  `tests/run_calendar_conflict_tests.py` are mocked against CalDAV, so the refuse-on-exact-
  duplicate path, the `[VERIFY]` fail-open marker and `update`/`delete` have only ever run
  against fixtures. It is the write path for every calendar event Logistics creates.
  *filed 2026-08-10 · shipped and deployed but unexercised in production*
- **[DB-0808-17]** A4 clinical hard-fails have never run on Flash-Lite, which serves most MW/PH
  turns (43 vs 5, 58 vs 6, Aug 1–8). Routing stays as-is by Mike's decision; the *test* gap is
  the item. Add `--complexity quick` to the A4 suite. Bears on ROADMAP § A7 check 8's wording.
- **[DB-0808-16]** The `injection` suite needs an ordinary-life persona — a clinically-loaded
  one silently scores 3/3 on a pipeline that never read the payload. Docstring line + a guard
  that fails loudly when `read_email` was never called. Matters for the open B1b rows.
- **[DB-0808-06]** No administrative close for tier-2 clinical threads — `resolved` exists and
  nothing can legitimately set it, so every tier-2 thread is permanent. Correct failure
  direction; needs a real path eventually, tied to escalation that doesn't exist. **Do not fix
  by relaxing the refusal.**
- **[DB-0808-14]** `_thread_tier()` cannot tell a psychiatric medication from a cardiac one — a
  missed statin and a missed anti-psychotic are both tier 1. Fix: `psychiatric: true` on
  `medication_profile` entries, read by `_thread_tier()`.
- **[DB-0805-01]** `_GUARDED_KEYS` holds exactly one pair
  ([tools/agent_config.py:43-45](tools/agent_config.py#L43-L45)), so another flag growing the same
  dependency needs its key added by hand and nothing detects that it should. B2 decides the
  mechanism: hand-maintained guarded keys, or the confirm gate as default. **The wiring half is
  not open** — both writers already gate (`config_writer.py:43`, `agent_config.py:76`); that was
  `[DB-0809-15]`, closed as stale, do not re-file it. *verified 2026-08-10*
- **[DB-0804-02]** Track B remainder: B4's 5 degradation paths, B2's confused-deputy regression
  test, and Wave 2 (B1b, B3) gated on Track E. Detail in the archive file.

**Reliability**
- **[DB-0810-02]** `core/trace.py`'s `pop_agent()` doesn't restore the prior thread-local
  `current_agent`, so a synchronous nested `run_subagent` misattributes its tool-call record to the
  child it just finished. Compounded by depth>0 agents always nesting under `t.pipeline[0]`.
  Diagnostic only, but makes The Book **actively misleading** for nested calls — which is how it
  cost a wrong diagnosis once. Fix: `push_agent()` returns the previous value for `pop_agent()` to
  restore. *filed 2026-08-10 · full mechanism in `archive/PROJECT_LOG.md` § 2026-08-10*
- **[DB-0810-01]** A reconnect can leave two live WebSockets briefly open, doubling a streaming
  response into one bubble (`ws.close()` isn't synchronous). Live twice on 2026-08-10, the second
  mid-session — which ruled out the install-transition reading. **Data is never at risk. Do not
  close on "restart fixed it"** — that only showed the stored record was clean. Fix is a design
  choice: await the old socket's `onclose`, or refuse a second live connection per persona
  (more robust, bigger). *filed 2026-08-10 · Mike, live · diagnosis in `archive/PROJECT_LOG.md`*
- **[DB-0808-11]** `fire_function` runs no gate stack — `days`, `respect_quiet_hours` and the
  activity gate are ignored for every function job. Reachable since it gained a notification
  path: an `interval_minutes` job with `notification: push` would push at 3am.
  `daily_travel_check` is pinned to 06:45 to work around it. Fix by extracting the gate stack.
- **[DB-0809-07]** ⚠ The VM's guest lost all networking for ~4 hours on 2026-08-04 while GCE
  reported `RUNNING` — `network is unreachable` to the metadata server, so no route existed.
  Same signature as the 2026-07-31 `nic0 is frozen` incident **but with billing never
  disabled**, so either that root cause was misattributed or there are two paths in. Unresolved.
- **[DB-0809-09]** The scheduler can only skip a time-anchored job, never defer it — blocked
  means gone for the day. Current state is correct (`morning_brief`/`evening_close` carry no
  activity gate deliberately). Only pick up if a fixed-time session should ever wait for a lull.
- **[DB-0803-05]** `sw.js` registers no `fetch` handler and `/` is served `no-store` — no
  offline shell, so an unreachable server shows a browser error page instead of the app.
- **[DB-0808-05]** The output filter suppresses the whole reply when Mike names a tool himself
  (*"`write_config` didn't save my preferences"*) — the canned fallback lands exactly when a
  complaint about the system deserves an answer. Live once (Exchange 027), pinned `FILTER-EXCH027`.
  Fix: pass the user's turn into `filter_output()` and exempt **only the term he typed, only in the
  next turn** — not a blanket flag, or a probing question disables its own backstop. Grep
  `filter_output(` for the three call sites; line numbers have moved twice.
  **Dev-session find; promote if it recurs.**
- **[DB-0810-07]** The Book's thinking/output-text, tool-call ok flag and `/monitor/model_errors`
  fields (`ffaf7a7`, deployed) have only had `py_compile` and a health check — never a real
  exchange. Verify with one successful and one deliberately failing tool/model call. Known and
  accepted at build time: the SSE path (`_prepend_col1`) reuses the `model_errors` list from the
  last full Load, so a live API failure shows no red tag until refresh — **not a bug to fix blind.**
  *filed 2026-08-10 · built and deployed, not exercised against live data*

**Capability**
- **[DB-0815-13] Semantic retrieval *within* a knowledge domain — phase 2 of the wisdom layer.**
  Phase 1 (approved plan, `~/.claude/plans/to-be-clear-we-modular-knuth.md`) makes `read_wisdom`
  return a **whole domain, capped at 15 entries**. That is correct while domains are small. **The
  cap being hit is the trigger for this item** — at that point the choice is subdivide the domain
  or retrieve within it, and retrieval is the better answer because it matches on meaning rather
  than on the filer's guess about which sub-domain a fact belonged to.
  **Two constraints, both load-bearing, and neither is obvious from the code:**
  *(a)* Wisdom gets its **own FAISS namespace** — `data/personas/{p}/memory/knowledge.faiss` —
  **never the log index**. Standing facts must not compete with dated log entries for the same `k`
  slots, and [core/memory.py](core/memory.py)'s public API is `index_entry`/`search_memory` with
  **no delete or update path**, so a revised standing fact would leave both versions retrievable
  and ranked against each other. Revision semantics are the whole reason wisdom is not in the log
  index already.
  *(b)* Route through `core/memory.py`'s **cached `_get_model()` singleton**. `find_duplicate_wisdom`
  ([tools/wisdom.py](tools/wisdom.py)) instantiates `SentenceTransformer` inline on every call —
  an ~80MB reload per invocation. Fixing that is phase-1 step 12; this item must not reintroduce it.
  **Filed because it existed only in a plan narrative.** `[DB-0810-11]` records strand (b) — the
  per-call reload — as one clause inside a broad standing question, and records nothing at all about
  indexing wisdom for retrieval. An item recorded only in a session narrative is lost.
  @kind: feature
  @waiting: a domain read hits the 15-entry cap in real use
  *filed 2026-08-15 during the knowledge-layering design track, at Mike's explicit request to
  confirm the FAISS step was in the backlog — it was not*
- **[DB-0810-15] A persona can send in one language and receive in another.** **BUILT AND DEPLOYED 2026-08-15** (`8a7d1d7`, `b3ff108`) — demoted from `## Now` the same day: the feature works and what remained was two checks, not build work. The render defect is `[DB-0815-04]`; the A4 gap is `[DB-0810-14]`; speech-in is `[DB-0815-02]`. **Rejected designs are permanent in `core/translate.py`'s docstring** — do not re-propose prose in `synthesizer.md` or a model-called translate tool.
  @kind: feature
  *demoted 2026-08-15 by the `/backlog deep` sweep, Mike's call*
- **[DB-0815-02] Voice in a language other than English. LOW priority (Mike, 2026-08-15).**
  *(Retitled 2026-08-15 — it was "both directions" and **half of it had already shipped**. Speech
  **out** is built; only speech **in** is blocked. See (b).)* Split out of `[DB-0810-15]` when that
  item was rescoped to the text path.
  *(a)* **Speech in** — `WHISPER_MODEL_SIZE` is `base.en`, English-only; multilingual needs `base`,
  which reopens the sizing constraint at [core/voice_pipeline.py:31](core/voice_pipeline.py#L31).
  **Benchmark on the VM, never the Mac** — `python3 tests/bench_whisper_stt.py --models base
  --languages en,bg`; an M-series laptop makes an unaffordable model look fine, and `small.en` was
  already measured at RTF 2.23 and rejected on a 2-vCPU single-worker pool.
  **✅ Benchmarked 2026-08-15 on the VM — both candidates rejected, held indefinitely.** `base`
  (multilingual): RTF 0.305, WER 46.4% on `bg` (vs. 5.0% `en`) — right script, roughly half the
  words wrong. `small` (multilingual, config added to `_CONFIGS` in the same pass): RTF 0.967,
  WER 27.6% on `bg` — better accuracy but real-time RTF leaves almost no queueing headroom on the
  single-worker pool, and English RTF also regresses 0.247 → 0.767 if adopted unconditionally.
  Neither clears the bar Mike's willing to accept; **no per-language model-selection work was
  attempted** (`small` for `bg` only, `base.en` kept for `en`) because the WER floor itself —
  ~28% best case — was judged not worth the added complexity. **Decision: hold in `## Later`
  indefinitely; not scheduled to be revisited absent a materially better local multilingual model
  or hardware change.** Full numbers: `tests/stt_bench_2026-08-15.json` (VM-side, latest run
  overwrites prior).
  *(b)* **Speech out — ✅ BUILT, and this entry described it as open for a day after it shipped.**
  `_EDGE_VOICE_BY_LANG` at [core/server.py:866](core/server.py#L866) maps `bg` →
  `bg-BG-KalinaNeural` and is selected by language code at [:951](core/server.py#L951); Kokoro has
  no Bulgarian model, so edge-tts carries it. Shipped by the 2026-08-15 language session, which
  recorded the closure in its `archive/log/` fragment — **but that fragment was never folded into
  `archive/PROJECT_LOG.md`, so the closure was invisible to every reader of the generated log.**
  Found 2026-08-15 by the `/backlog deep` sweep only because `qa_sweep.sh`'s `project-log` check
  was failing and the unfolded fragment had to be opened to see why. *(Log rebuilt the same day;
  the sweep passes 9/9. **The reusable lesson: `/archive` writing a fragment without running
  `scripts/build_project_log.py` makes a shipped closure unreadable** — the fragment is the source
  of truth and nothing reads it directly.)*
  **The prerequisite framing below still holds for what remains** — synthesising speech needs a
  stored language value, which is why `[DB-0810-15]`'s preference was the prerequisite. It landed.
  The `METATRON_WHISPER_LANGUAGE` knob (`1d858f2`) is plumbing only and changes nothing until a
  multilingual model is adopted. One client (`static/index.html`) serves both web and APK, so
  neither half needs per-platform work.
  *filed 2026-08-15 by Mike as an explicit `## Later`, low priority*
- **[DB-0810-03]** **Tool allowlists are never audited against the instruction files, so an
  agent can be told to use a tool it does not hold.** *(Two of three grants shipped `a96a3b3`,
  deployed 2026-08-10 — `relationships` and `finance`. What remains is `recreation_hobbies` and
  the systemic half.)* The gap as found: three specialists were each instructed to
  use `search_memory` and none held it (named twice per file — a procedure step and their tool
  list; e.g. [relationships.md:196](config/agents/relationships.md#L196)). Only 5 of 14 agents are
  granted it, so these three silently lose recall mid-conversation. **Why it was missed:** grants
  in `routing*.yaml` are demand-driven, not audited — each carries a comment citing one observed
  denial, and nobody ever swept the instruction files against the allowlists. Denials so far:
  `relationships` 08-10T06:30, `finance` 08-05T15:21 — both now granted.
  ~~*(b)* **The systemic half — nothing sweeps `config/agents/*.md` against `allowed_tools`.**~~
  **Closed 2026-08-10** — `scripts/check_agent_tools.py` (`6cb077b`) plus a `PostToolUse` hook
  that runs it on every agent-file and routing-grant edit (`a3b43c5`). It found a live instance
  within a day: `get_weather` granted to `logistics` but documented only on `research_agent`
  (`924a66e`). Deliberately **not** wired to the quality-event stream — 70 fleet-wide findings
  as machine events would bury the Inbox (Mike's call).
  **Still open:** *(a)* `recreation_hobbies` has never been denied `search_memory`, so granting it
  would be the file's first speculative grant — it waits for a real denial. *(c)* **The sweep's
  backlog is unreviewed:** 35 named-but-not-granted and 35 granted-but-undocumented across the
  fleet, including `logistics.md:179` naming `write_journal` without holding it. Each needs a
  build/grant/defer decision. Worth a `/backlog` pass before A7 check 10, since check 10 requires
  no Fails and these are the same class as the Fail it just cleared.
  **Two more real denials arrived 2026-08-10T15:00, both verified as live-instruction (class 2),
  both waiting on a decision in (c):** `learning_growth` names `write_archive` four times without
  holding it ([learning_growth.md:195](config/agents/learning_growth.md#L195) lists it as a held
  tool; :74 and :130 make it a mandatory step), and `recreation_hobbies` names `write_agent_config`
  ([recreation_hobbies.md:231](config/agents/recreation_hobbies.md#L231)) while holding only
  `[read_log, write_log]`. Neither is speculative — both were denied in production.
  **Sharpest argument for enforcing the allowlists is also the argument for not doing it yet:**
  `logistics` calls `send_email` without the grant (only `relationships` holds it) and the
  dispatcher executes it, so switching to enforce mode today would kill outbound email. See
  `.claude/rules/agent-files.md` — correct the lists, verify, *then* enforce.
  **Fourth blind spot, found 2026-08-15 and created by that day's own change: the guard scans
  `config/agents/*.md` and never `config/personas/**`, so a tool named in a persona file is
  invisible to it.** `6913ad7` moved Mike's evening ritual — which instructs a `write_log` call —
  out of `synthesizer.md` into `config/personas/mike/evening_ritual.md`. The `write_log` finding
  **disappeared from the guard's output between two edits in one session**, and not because it was
  fixed: `synthesizer` still lacks the grant and still succeeds only because `dispatch_tool()` does
  not enforce. Per-persona subject files are a pattern `ROADMAP.md` § D2 actively encourages, so
  this widens every time one is added. **Do not fix by reverting the move** — extend the guard's
  scan to persona files, noting they are VM-only, so a Mac-side run cannot see the real ones and a
  clean local report proves nothing about `mike`.
  *filed 2026-08-10 by the machine-log sweep · **(b) closed 2026-08-10**, (c) added the same day
  from the guard's first full run · two denials added by the 08-10 `deep` sweep · fourth blind spot
  filed 2026-08-15 by the session that caused it*
- **[DB-0814-03]** **Ticket-based mailbox management.** Mike's framing: manage the mailbox as
  tickets rather than as a stream, so a thread has a state rather than being re-read each pass.
  Real and unbuilt. **Blocked on a design decision this entry cannot make** — what a ticket *is*
  (a thread, a sender, an obligation), where state lives, and how it relates to two things that
  already exist and overlap it: `tools/obligations.py` (obligations are data with inferred closure
  and evidence-required `close_obligation` — much of a ticket lifecycle, already built) and
  `[DB-0814-01]`'s null-report silencing, which is arguably the same want expressed smaller. **Scope
  against obligations before designing anything new.** *filed 2026-08-14 by Mike via the VM
  (2026-08-11T08:36Z)*
- **[DB-0815-12] Real-time location as a signal.** GPS and proactive area-scanning (Mike's
  framing) needs a design pass: privacy tier for continuous location, which layer supplies it, how
  scanning bounds itself. **Split out of `[DB-0808-04]` 2026-08-15** when the venue-discovery half
  was promoted to `## Now` — that half never needed this signal, and keeping them as one entry is
  what hid a shippable feature behind an unmade design decision for a week. Given its own id
  because two halves of one id break `qa_sweep.sh`'s backlog-ids check.
  @session: the continuous-location privacy tier
  *merged 2026-08-10 — absorbed `[DB-0807-02]`, the same blocker restated · split 2026-08-15*
- **[DB-0809-13]** Sentence-chunked TTS. Kokoro is at 2.8s/call. **Do not build before using
  voice enough to say whether 2.8s actually feels slow.**
- **[DB-0809-08]** "Unsurfaced opportunities" is the one troubleshooting category with no
  instrumentation — it is an absence, so no richer tracing recovers it. Recommended: a reason
  code on the `·` feedback dot, plus detecting `open_threads` that go quiet unresolved.

**Performance and cost**
- **[DB-0810-11]** Standing design question, raised by Mike 2026-08-05, never given its own
  session: **where should code replace LLM judgment**, for accuracy and token cost? Three strands —
  (a) deterministic lookups feeding agents evidence rather than asking them to recall
  (`tools/scheduling.py` is the worked example; unbuilt: CRM contact dedup, where `_find_by_name`
  is naive substring matching so "Jon"/"Jonathan"/"Jonathan Whitfield" become three records;
  `write_archive` dedup; ~~`tools/wisdom.py` reloading `SentenceTransformer` per call where
  `core/memory.py` caches a singleton~~ **— that one strand closed 2026-08-15 (`13134bc`),
  `find_duplicate_wisdom` now uses the cached singleton; the rest of (a) is untouched**); (b) code
  that removes agent calls entirely — cuts against
  the head-layer/specialist split and PoLP, so not free; (c) a standing code/agent review protocol.
  The argument for (c): `daily_calendar_dedup_audit` was correct, tested and deployed yet did
  nothing for 3 days (template never propagated, `8d798a8`), then had its output discarded for 5
  more by `[DB-0810-09]` — **neither failure was a code bug or catchable by unit tests.** Also
  parked here: embeddings for semantic similarity, and `temperature`, **not plumbed through any of
  the four provider paths**, most valuable for clinical flags and Finance arithmetic.
  *filed 2026-08-10 · a full session prompt exists in that day's transcript*
- **[DB-0808-09]** Per-specialist internal turn reduction. Coordinator is 1 turn (measured
  twice); `logistics` is 8; the other specialists are unmeasured. **Measure first, then diagnose
  from traces, then fix.** Absorbs the old "Coordinator restructure" entry. Slimming
  `coordinator.md` is a separate token-size argument — watch the 4,096-token Vertex cache floor.
- **[DB-0806-04]** Migrating the VM us-central1 → europe-west1: ~200–280ms off every voice turn
  for ~$2.60/mo. Priced live, not estimated. A deliberate trade, not a bug.
- **[DB-0806-03]** No BigQuery billing export, so cost anomalies can only be eyeballed against
  console lag. Not retroactive — turning it on now only helps the next anomaly.

**Housekeeping**
*(`[DB-0813-01]` — the due-date marker — closed 2026-08-14 once `[DB-0809-02]` carried its tag.
Its verification found a false-positive class worth knowing before anyone documents the convention
again: `archive/backlog_closed_2026-08.md` § Closed 2026-08-14.)*
- **[DB-0810-06]** Every context-file ceiling is measured in lines, and lines stopped tracking the
  cost. `SESSION.md` hit 200/200 with **5.6 KB of its 17.9 KB on five lines** — rows that grew
  **wide, not numerous**, so a line ceiling could not see them. Instance fixed (`2e3e6e4`); the
  metric is still line-based everywhere it is stated (`.claude/rules/docs-and-logs.md` § Ceilings plus
  each file's footer). **Check before acting:** whether a byte/token measure earns its complexity,
  or whether the one-line-per-row rule already added is sufficient. *filed 2026-08-10 ·
  **second blind spot found 2026-08-14, still open:** a whole-file line count also cannot tell
  static lines from volatile ones, so it pressures a session to cut live state while reference
  sits untouched. `SESSION.md` sat at 195–205 for twenty commits on that basis. Mitigated for
  this one file by a volatile-section budget in `check_claude_md_claims.py` — which is **still
  line-based**, so it narrows the item rather than closing it*
  **Third input, and it names a concrete replacement metric — Mike, 2026-08-15: a backlog's ceiling
  should probably be tied to the number of *items* in it, not its line count.** Raised while
  deciding a trim on a 922/450 file, and the reasoning is that the item count is what bounds the
  workload while the line count is what pressures a session to cut evidence out of well-documented
  entries. `DEV_BACKLOG.md` already half-agrees with him — `## Now`'s real cap is its 10-item limit.
  **This is the first Mike-raised strand in this item**, so the item is now promotable on his say-so
  rather than needing the ×3 machine bar; it stays in `## Later` until he wants it.
- **[DB-0805-05]** **A session cannot tell its own edits from a parallel window's** — the git
  collisions and the `/archive` dirty-check are one cause, not two. `git add <file>` does **not**
  protect you: the collision is line-granular inside a file the committer legitimately owns
  (2026-08-08). `/archive` step 0 flags dirty files but cannot say whose — advisory, not
  protective, and **do not remove it**; a prompt to look beats no prompt. **Fix:** a
  start-of-session commit to diff against, or record touched files as the session goes.
  *merged 2026-08-10 (absorbed `[DB-0809-17]`) · **×3, the bar is met** — recurred twice more on
  08-10, once nearly reusing an id another window had taken minutes earlier · `/archive` step 5
  currently depends on this being unsolved*
- **[DB-0809-10]** `CLASSES` in `core/rule_classes.py` is incomplete by construction, so a clean
  rule-overlap report is not proof. **Widen a class in the same pass as any duplicate found by
  hand** — that is the maintenance loop. **Second blind spot, found 2026-08-09:** nothing checks
  `config/templates/`, so a rule deleted from a persona survives in the file that seeds every new
  one. That is how the check-in rule reached four copies with only three flagged.
  **Third blind spot, found 2026-08-13 and the sharpest of the three: the audit reads rule/prose
  files and never settings files, so for a rule whose real counterpart is a *config key* it cannot
  name the partner at any score.** `mike.md:14` ("check inbox every six hours in the background")
  restated `check_interval_minutes: 240` in `config/templates/email.yaml`; the audit flagged the
  preference correctly ×4 and matched it to `"Check in."` in `scheduler.yaml` at 1.00 wording
  overlap — noise. The preference was removed 2026-08-13 (Mike kept four hours), so this is the
  *mechanism*, not an open instance. **The larger half is that reporting is not preventing:**
  `write_persona` writes to `mike.md` at runtime, so a layer decision enforced only in a config
  file is re-violated by the next such write — that is what happened here, four hours after
  `7e0e302` shipped `[DB-0810-16]` specifically to move this rule out of the persona layer. Any
  fix should cover the write-time check in `check_new_rule()`, not just the daily sweep.
  *third blind spot filed 2026-08-13 during `/archive`, from a live instance*
- **[DB-0809-14]** ROADMAP.md Track D is ~14 KB of a file loaded every `/metatron-code`, and
  parts have shipped. **Trim item-by-item against the log, never by line range.**
- **[DB-0809-16]** Live dictation test of the dismissable transcription readout — code-verified
  against every pass condition 2026-08-05, never run by a human with a microphone.
---

## Machine log

*Auto-appended runtime signals — tool denials, rule conflicts, self-applied changes. Collapsed
by signature. Nobody asked for these: they are the system reporting on itself, and they are
**not** part of an ordinary triage pass. A signature reaching ×3 gets a ⚠ and is surfaced in the
sync output line — repetition is the signal that a process event has become a real one. Promote
anything user-impacting into `## Now` or `## Later` like any other item; this is a holding pen,
not a blackhole. Swept during `/backlog deep`.*

> **An entry is DELETED once its signal is promoted or its cause is fixed — leave a pointer, not
> the entry.** This rule was missing until 2026-08-15 and its absence was the whole problem: the
> sweep step said *promote*, never *remove*, so an addressed signature kept its ⚠ and kept leading
> the session-start line. Mike had to ask why "Eva" was still there after the merge shipped. **The
> ⚠ is a prompt to look; an entry that has been looked at and acted on has no further job.**
>
> Two cautions bought the same day. **(1) `.dev_backlog_seen` is what makes deletion safe** — the
> sync will not re-add a deleted entry, because it keys on timestamps already pulled, not on what
> is in the file. **(2) Regenerating this section from the VM source bypasses that ledger and
> resurrects everything**, including entries a previous sweep pruned. That was done once, on
> 2026-08-15, to clear clusters built by the pre-fix similarity threshold; it was correct then and
> is not a routine operation. If it is ever needed again, expect to re-prune afterwards.

*(swept 2026-08-10 twice — the `search_memory` denials promoted to `[DB-0810-03]`, then both
`2026-08-10T15:00` denials verified and promoted into `[DB-0810-03](c)`, which is the decision
queue for this exact class. Nothing outstanding.)*

*(swept 2026-08-15 — the `mike.md:13` consolidated-evening-check-in preference (×5, first seen
2026-08-12T08:21Z) is resolved, but **not the way the design-by-default rule predicted, and the
correction is the useful part**. It was first read as design and written into
`config/agents/synthesizer.md`; **Mike rejected that** — the Franklin virtue review is his
personal ritual, not how Metatron should behave for anyone. The whole ritual therefore **left
`synthesizer.md` entirely** for a new per-persona subject file,
`config/personas/mike/evening_ritual.md`, loaded by `load_config()` exactly as the existing
optional `self_development.md` is. `synthesizer.md` § Evening close is now generic ("conduct the
user's evening ritual if one is defined"), as is its morning catch-up line, which had hardcoded
`franklin_virtues`.
**Two things worth carrying.** (1) The move was **token-neutral for Mike and a saving for every
other persona** — the 2,097-byte virtue block was in a global agent file every persona loaded, so
this removed it for everyone it never applied to. Per-persona subject files are the pattern
`ROADMAP.md` § D2 already prescribes, naming *"virtue lists"* verbatim. (2) The audit's candidate
partner (`scheduler.yaml:43` — *"Check in."*, 1.00 wording overlap) was **noise**, exactly as the
`⚠` entry's own caveat predicts: the flagged preference is the reliable half, the partner is not.
**Do not re-file this as a duplicate** — it never was one.
**One regression, deliberate and recorded:** the ritual's `write_log` call moved into a persona
file, which `scripts/check_agent_tools.py` does not scan — so `synthesizer`'s missing `write_log`
grant is now **invisible to the guard** while still working only by `dispatch_tool()`'s lack of
enforcement. Same class as `[DB-0810-03]`; the gap did not change, the ability to see it did.)*

*(swept again 2026-08-15 by the second `/backlog deep`, read live off the VM rather than off this
file. Three results. **(1) The transliteration `SELF_APPLIED` below is not a process event — it is
the likeliest cause of `## Now` #1**, and has been promoted into `[DB-0815-04]` as candidate (c);
it sat here for hours looking like housekeeping. **(2) No new `TOOL_DENIED` since
2026-08-10T15:00** — all 20 on record are the ones already promoted into `[DB-0810-03](c)`, so that
item's evidence is current and nothing new is waiting. **(3) The empty-detail finding and the
"`×N` is a similarity cluster, not a repeat count" finding were fixed the same day (`[DB-0815-09]`,
closed — `archive/backlog_closed_2026-08.md`). **A `×N` before 2026-08-15 was a chain length, not
a repeat count; entries above that date should be read with that in mind.**)*

- **[already applied by the tool]** Updated Interaction Preferences to formalize the rule: Open sessions with the most time-sensitive commitment, overdue follow-up, or unresolved thread, naming it specifically. If genuinely nothing is outstanding, keep it to one line and ask what is on.  
  `2026-08-18T09:17:27.961459Z`

- **[answered without retrieving anything]** Answered with nothing retrieved — 2 search(es) ran but returned no sources. Query: Check Southeastern railway status for Sunday August 16, 2026. Are there any engineering works affecting the Greenwich line to London Bridge or Charing Cross?  ×2  
  `2026-08-16T08:08:23.783712Z`

- **[user corrected a prior turn]** User corrected transit route to Transport Museum, explicitly excluding Jubilee and Piccadilly lines which were previously suggested.  ×2  
  `2026-08-16T08:06:21.241217Z`

- **[user corrected a prior turn]** The user is correcting the language setting; they want to communicate in Bulgarian, not English.  
  `2026-08-15T21:06:57.317908Z`

- **[user corrected a prior turn]** User is confirming the necessity of a workaround for the Bulgarian language recognition bug.  
  `2026-08-15T13:50:27.705106Z`

- **[needs building]** Fix speech-to-text for Bulgarian. When user speaks Bulgarian, the transcription model defaults to English and produces phonetic garbage/small English words instead of correct Bulgarian text.  
  `2026-08-15T13:49:35.728044Z`

- **[user corrected a prior turn]** User corrected the previous exercise log, stating the run was only a test and requested its removal.  ×2  
  `2026-08-15T11:13:42.274343Z`

- **[user corrected a prior turn]** The user refers to their companion as "Eve", which conflicts with established records of "Iva Diamond". The directive assumes the intent is for Iva Diamond.  
  `2026-08-12T08:30:54.115961Z`

- **[instruction change]** Silence 'nothing found' reports for scheduled inbox checks. The system should only notify the user when new actionable mail arrives that requires their triage. Specifically, stop surfacing that pending emails (like the Prudential follow-up) have not arrived.  
  `2026-08-12T08:27:42.379965Z`

- **[user corrected a prior turn]** The user corrected the communication flow regarding email monitoring, explicitly stating that they do not want to be notified when routine checks return no results.  
  `2026-08-12T08:26:35.580796Z`

- **[needs building]** Stop assuming passed calendar events are completed. Implement a reconciliation loop to check back on scheduled blocks and actively alert/push the user in the right direction based on calendar intent versus actual reality.  
  `2026-08-12T08:25:16.368492Z`

- **[user corrected a prior turn]** User corrected the assumption that scheduled calendar events imply completion, requesting active reconciliation and pushing alerts instead of passive tracking.  
  `2026-08-12T08:25:12.628744Z`

- **[user corrected a prior turn]** The user corrected the system's assumption that calendar events equate to completed actions.  
  `2026-08-12T08:24:40.201122Z`

- **[needs building]** Bug fix: Evening close scheduler fired 3 repetitive messages; restrict follow-up prompts to a single line. Feature request: Build a mechanism to automatically age out stale state/context (like 'post-travel recovery' lingering for two weeks) to keep live context relevant.  
  `2026-08-12T08:23:28.940968Z`

- **[user corrected a prior turn]** The user corrected the system's outdated belief that they are still in "post-travel recovery," confirming that period is over and requesting the system adjust its internal state accordingly.  
  `2026-08-12T08:23:05.655993Z`

- **[already applied by the tool]** Updated interaction preferences: evening check-ins (13 Franklin virtues + 1 food log) will now be delivered as a single consolidated message rather than item-by-item, allowing the user to highlight only the exceptions.  
  `2026-08-12T08:21:14.706181Z`

- **[user corrected a prior turn]** Dropping the Manny/protest thread and modifying the check-in format to a consolidated 14-point list.  
  `2026-08-12T08:20:17.031497Z`

- ⚠ **[user corrected a prior turn]** Missed the user's previously stated Thursday deadline for the Prudential email and prompted action on it prematurely.  ×4  
  `2026-08-11T11:13:14.252775Z`

- **[needs building]** User requested stopping the read-back of triaged emails (applied to persona) and requested implementing a ticket-based system for managing the mailbox more effectively (needs building).  
  `2026-08-11T08:36:03.236643Z`

- **[user corrected a prior turn]** The user corrected the expectation for email interaction, requesting that already-triaged emails no longer be read back.  
  `2026-08-11T08:35:01.218376Z`

- **[needs building]** Fix email dispatch silent failure: system confirms send to the user but the message does not reach the user's provider. Investigate why the tool is returning success without actual handoff.  
  `2026-08-10T17:10:55.511151Z`

- **[needs building]** Add multi-language support (English and Bulgarian) for voice transcription, or a UI setting to toggle between them. Current dictation forces English phonetic spelling on Bulgarian phrases.  
  `2026-08-10T16:43:28.455756Z`

- **[needs building]** Create a global default setting variable for mailbox check frequency to apply across all users.  ×2  
  `2026-08-10T15:51:17.112387Z`

- **[user corrected a prior turn]** The user corrected the grocery reminder logic (not every Friday, but 3 days after the date of an order).  ×2  
  `2026-08-10T15:46:40.890480Z`

- **[user corrected a prior turn]** User clarified they wanted to know the mechanism/tools for routing, not the route itself.  
  `2026-08-10T12:29:39.464756Z`

- **[user corrected a prior turn]** The user is clarifying that their previous query was not about the travel itself, but about the *mechanism* used to generate the routing.  
  `2026-08-10T12:29:21.953978Z`

- **[needs building]** User asked to look in CRM and get a total contact count. Needs an integration with their external CRM system.  
  `2026-08-10T11:19:18.354306Z`

- **[needs building]** Fix Research Agent returning blank results for live TfL transport queries (Bakerloo, Elizabeth, DLR).  
  `2026-08-10T11:10:27.325451Z`

- **[user corrected a prior turn]** The user is correcting the previous interaction where the Research query was missed by the coordinator/system.  
  `2026-08-10T11:09:53.973163Z`

- **[needs building]** research_agent fails with 'NoneType object is not iterable' or returns empty strings when queried for live web data (TfL status, weather, pollen) during user feature test.  
  `2026-08-10T10:04:30.084620Z`

- **[user corrected a prior turn]** User pasted the check-in preference for a third time. In previous turns, the Synthesizer failed to adhere strictly to 'Otherwise just ask what's on', adding filler ('Nothing urgently needs your attention...' and 'I already have that instruction...'). The system needs to recognize strict negative constraints.  
  `2026-08-09T12:27:20.856785Z`

- **[instruction change]** User reiterated existing check-in length instruction verbatim. Triggered repeated instruction protocol to flag that current check-ins are failing to adhere to the brevity rule.  
  `2026-08-09T09:06:43.932199Z`

- **[user corrected a prior turn]** Correction note: The user referred to the contact as "Eva" in the message, which conflicts with the pre-loaded profile update (Iva Diamond). The directive respects the user's current choice of "Eva" while maintaining the existing identity record.  
  `2026-08-08T20:07:44.342945Z`

- **[instruction change]** User has submitted the check-in rule multiple times in a row. The system must output strictly 'What  
  `2026-08-08T18:34:27.078188Z`

- **[instruction change]** Synthesizer is failing to adhere to the existing Interaction Preference for check-ins (max two sentences, name one urgent thing or ask what's on, no recaps). This preference needs to be enforced more strictly at the system/prompt level.  
  `2026-08-08T16:31:45.535165Z`

- **[instruction change]** User repeated the check-in brevity rule verbatim. It is already saved in Interaction Preferences but earlier responses failed to follow it. Need to ensure the system strictly enforces this preference over other dialogue generation.  
  `2026-08-08T12:19:24.143357Z`

- **[user corrected a prior turn]** User previously confirmed Rowan transfer was handled, but system asked for details again.  
  `2026-08-07T16:22:17.434741Z`

- **[user corrected a prior turn]** The system incorrectly flagged the Rowan payroll transfer as 'pending' despite the user having previously provided this information.  
  `2026-08-07T16:21:48.444766Z`

- **[instruction change]** User re-stated the strict check-in rule ('never list or recap pending items') because the previous response violated the existing persona config by listing two time-sensitive items. The persona constraint is present but failed to override the generic routing/integration behavior.  
  `2026-08-07T09:13:05.841606Z`

- **[user corrected a prior turn]** User repeated their standing check-in rule word-for-word, indicating my previous response failed to respect it.  
  `2026-08-07T06:12:15.702788Z`

- **[needs building]** search_memory tool is throwing a JSON parse error: 'Extra data: line 557 column 2 (char 82852)'. The memory file parser needs debugging to restore CRM read access, which is currently blocking contact verification.  
  `2026-08-06T16:49:21.836539Z`

- **[needs building]** Develop a stronger protocol for onboarding new contacts to the CRM or Google Contacts. Current handling resulted in misattributing the user's email to the contact and silent failures during retrieval.  
  `2026-08-06T16:47:08.029326Z`

- **[user corrected a prior turn]** The user corrected my assumption that the calendar event for the Horatiu Stefan meeting was fully prepared, noting that the guest was not added.  
  `2026-08-06T16:44:46.614240Z`

- **[user corrected a prior turn]** Corrected Heathrow event to drop-off rather than personal flight.  
  `2026-08-05T16:35:21.231662Z`

- **[user corrected a prior turn]** Assumed user was traveling to Sofia based on flight tracking; user corrected that it was just a drop-off.  
  `2026-08-05T16:16:27.045468Z`

- **[user corrected a prior turn]** Corrected the system's assumption that the user was the one traveling to Heathrow today.  
  `2026-08-05T16:15:41.116476Z`

- **[user corrected a prior turn]** User corrected the status of their Heathrow departure, stating it was today, August 5th, not tomorrow.  
  `2026-08-05T15:20:56.548406Z`

- **[needs building]** System must proactively detect when a scheduled calendar event passes without occurring, and automatically prompt the user to reschedule it. Financial tasks (like payroll) must remain prominently surfaced in daily proactive checks until explicitly closed.  
  `2026-08-05T15:19:45.254683Z`

- **[user corrected a prior turn]** The user is correcting the system for failing to proactively manage the Apex meeting and payroll tasks, which they expect to be handled automatically.  
  `2026-08-05T15:19:21.740492Z`

- **[user corrected a prior turn]** User is identifying a data discrepancy in the information provided (asserting Elizabeth Line status).  
  `2026-08-05T08:40:07.713758Z`

- **[user corrected a prior turn]** The user corrected the decision from the previous interaction regarding flight tracking (they are now asking to continue it, contradicting the previous note that it was no longer needed).  
  `2026-08-05T07:19:12.901025Z`

- **[user corrected a prior turn]** The user corrected my prior assumption that they were flying; they are merely dropping someone off at the airport. They also corrected the assumption that the flight tracking was no longer needed.  
  `2026-08-05T07:05:07.612613Z`

- **[user corrected a prior turn]** System incorrectly assumed user was traveling on flight BA 892 rather than just dropping someone off.  ×2  
  `2026-08-05T07:04:18.930017Z`

- **[instruction change]** Enable proactive pre-departure travel checks: autonomously look up flight status and relevant transit lines (e.g., DLR, Elizabeth line) before the user asks on travel days.  
  `2026-08-05T07:02:45.797954Z`

- **[user corrected a prior turn]** User copy-pasted the existing brief check-in rule verbatim, indicating previous turns failed to adhere to it.  
  `2026-08-05T06:10:40.922935Z`

- **[user corrected a prior turn]** Corrected previous transit concern by noting multiple rail options exist for Heathrow.  
  `2026-08-04T14:41:57.409553Z`

- **[user corrected a prior turn]** User corrected system for failing to proactively research venue details (address, menu, hours) when a new pub meeting was scheduled.  
  `2026-08-04T13:58:03.975204Z`

- **[needs building]** User reported that the email permission prompt is not appearing (blocking testing) and requested the ability to read live Google Contacts. Both added to backlog.  
  `2026-08-04T13:51:08.510189Z`

- **[agent wanted a tool it lacks]** `logistics` attempted `read_archive` (category) but it is not in its allowed_tools. Its instruction file asks for this capability. Decide: grant it, build it, or drop the instruction.  
  `2026-08-04T13:50:50.369416Z`

- **[needs building]** Implement email permission prompt bubble for user approval before sending outbound emails, and enable Google Contacts live sync/read capability.  
  `2026-08-04T12:49:26.633029Z`

- **[agent wanted a tool it lacks]** `logistics` attempted `write_archive` (category, content) but it is not in its allowed_tools. Its instruction file asks for this capability. Decide: grant it, build it, or drop the instruction.  
  `2026-08-04T12:48:56.486418Z`

- **[needs building]** 1) The email approval permission prompt is failing to render in the user's app interface. 2) The system needs a tool to read live Google Contacts directly; currently it only checks internal profile records.  
  `2026-08-04T12:42:35.495275Z`

- **[user corrected a prior turn]** User corrected contact name from Eva to Iva  ×2  
  `2026-08-04T12:38:53.028444Z`

- **[user corrected a prior turn]** User opted to close the CalDAV integration thread.  
  `2026-08-04T12:37:18.994165Z`

- **[user corrected a prior turn]** User explicitly corrected system's read of 'low energy' trend, stating they have natural momentum. System over-extrapolated from isolated log entries about sleep and fatigue.  
  `2026-08-04T12:20:02.780437Z`

- ⚠ **[user corrected a prior turn]** User corrected the system's assumption of low energy, stating they have strong natural momentum and do not need to force motivation.  ×3  
  `2026-08-04T12:22:27.850000Z`

- **[needs building]** Remove the voice activation toggle from the app interface, as the voice feature is causing interface friction and interrupting the user's ability to send messages.  ×2  
  `2026-08-04T07:57:18.076761Z`

- **[user corrected a prior turn]** User restated 'rucking and high intensity' to correct a prior dictation error ('rocking and hop and swing both balls') and reaffirm their fitness baseline.  
  `2026-08-03T17:15:55.567859Z`

- **[user corrected a prior turn]** User rejected the pivot to step-counting, clarifying they want to keep rucking and kettlebell/strength training active.  
  `2026-08-03T17:14:49.251718Z`

- **[user corrected a prior turn]** User clarified that they do not want to pivot to step-counting and prefers maintaining their established high-intensity and strength-based fitness goals.  ×2  
  `2026-08-03T17:15:08.995366Z`

- **[user corrected a prior turn]** Credit card thread is no longer a priority.  
  `2026-08-03T17:12:56.166021Z`

- **[needs building]** Fix interface bug causing text doubling/duplication and abruptly cutting off user input mid-sentence. Also prioritize fixing the live calendar connection so the system can read and write to the user's calendar.  
  `2026-08-03T17:12:02.492018Z`

- **[agent wanted a tool it lacks]** `finance` attempted `read_archive` (category) but it is not in its allowed_tools. Its instruction file asks for this capability. Decide: grant it, build it, or drop the instruction.  
  `2026-08-03T17:06:28.655802Z`

- **[instruction change]** For all check-ins: maximum two sentences. If exactly one item genuinely needs attention, name it and stop; otherwise just ask what is on. Never list or recap pending items, and never manufacture a topic.  
  `2026-08-03T15:12:14.933312Z`

- **[agent wanted a tool it lacks]** `physical_health` attempted `write_agent_config` (agent_name, config) but it is not in its allowed_tools. Its instruction file asks for this capability. Decide: grant it, build it, or drop the instruction.  
  `2026-08-03T15:11:50.265168Z`

- **[instruction change]** Update check-in logic and Synthesizer instructions so that proactive check-ins are very brief and do not include long summaries of pending tasks, especially when the user has not been actively responding.  
  `2026-08-03T09:11:56.763043Z`

- **[user corrected a prior turn]** Correction of the RAF Museum schedule (user was there yesterday, not this evening).  
  `2026-08-03T09:10:59.166436Z`

- **[user corrected a prior turn]** User corrected system for excessive repetition of pending tasks, over-indexing on sleep disruption, and intrusive scheduled check-ins during active dialogue.  
  `2026-08-02T17:48:22.011991Z`

- **[user corrected a prior turn]** Corrected previous system behavior regarding repetitive check-ins and calendar status reporting.  
  `2026-08-02T17:47:36.290155Z`

- **[user corrected a prior turn]** User explicitly requested to stop being told to "enjoy things" after Synthesizer used the phrase "Enjoy the museum" in the previous turn.  ×2  
  `2026-08-02T14:05:23.180476Z`

- **[user corrected a prior turn]** User clarified the timing of the museum visit is this evening, not tomorrow.  ×2  
  `2026-08-02T14:02:51.288826Z`

- **[user corrected a prior turn]** The user clarified that the task mentioned for "later" is intended for this evening, not the next day.  
  `2026-08-02T13:58:21.364287Z`

- ⚠ **[user corrected a prior turn]** User corrected dictation error of their email address from diamond.mic@gmail.com to diamond.mike@gmail.com  ×3  
  `2026-08-02T12:16:08.379690Z`

- **[user corrected a prior turn]** User corrected the system's perception of the timeline, noting the impossibility of having had a full day's experience within a 10-minute interval.  ×2  
  `2026-08-01T10:02:46.971124Z`

- **[user corrected a prior turn]** User noted the system echoed the user-provided time '953' for the 'banana' test rather than checking the actual message receipt log (9:52 AM).  ×2  
  `2026-08-01T08:53:41.172516Z`

- **[user corrected a prior turn]** Mike is correcting the assumption that his 'fit it in' approach to work creates negative pressure; he finds it manageable and beneficial for his family balance.  
  `2026-06-26T21:35:02.264614Z`

- **[user corrected a prior turn]** User is flagging that the previous exchange produced no response and that an expected write_config action was not executed — this is a pipeline/execution failure, not a content correction per se, but note that the prior turn's intended output did not reach the user and the write_config call was missed.  
  `2026-06-26T15:51:48.929810Z`

- **[user corrected a prior turn]** Mike corrected tone — too cheerful, parroting back what he says, cheerleading. Also corrected assumption that last night's sleep was unknown — he states it's already in context.  ×2  
  `2026-06-26T15:38:52.421775Z`

- **[user corrected a prior turn]** User implies a date was previously returned by the system as if it had real-time access — Synthesizer should clarify honestly how prior dates were produced (likely from context/logs, not live tool access) while delivering whatever the Research Agent returns.  
  `2026-06-26T14:32:21.391602Z`

- **[user corrected a prior turn]** Two corrections: (1) Location recorded as Brisbane — user is actually in London, UK. BOM weather advice from prior session is invalid. (2) Synthesizer implied sleep records were missing; user pushed back. Logs actually contain data through June 25 confirmed, June 26 ambiguous, June 27 onward absent.  ×2  
  `2026-06-26T14:30:23.078064Z`

- **[user corrected a prior turn]** Log entries were recorded with datestamp only — user corrected to require timestamp included on all future entries.  ×2  
  `2026-06-26T14:02:14.841386Z`

---
## Done

**Closed items live in [`archive/backlog_closed_2026-08.md`](archive/backlog_closed_2026-08.md)**,
with the commit or `file:line` that closed them. Rolls monthly. Nothing is ever deleted — an
item that resurfaces must be able to show it was checked once, and the withdrawn and
"not a bug" entries are the most valuable ones in there.

Closed by the 2026-08-09 workflow revamp itself: `[DB-0809-01]` (inflated open count — the
notation trap is gone by construction), `[DB-0808-13]` (`/archive` collision guard — now step 0),
`[DB-0808-15]` (parallel-window status collisions — coordinator/handoff protocol, with the git
half kept open as `[DB-0805-05]`).

Closed by the 2026-08-09 `/backlog deep` sweep: `[DB-0803-06]` (`shownIds` full-`clear()` →
oldest-first eviction, fixed by `c4ff279`; its "promote when Mike sees a doubled message"
condition had already been met by `[DB-0803-01]`, which now carries the remaining APK half).

---

## Agent-file enhancement backlogs

**These live in the agent files, and only there.** Each specialist's `## Enhancement backlog`
at the bottom of `config/agents/{name}.md` is the single copy. A mirror sat here for one day in
August 2026 — 32% of the file, and it made the backlog look three times its real size.

`grep -l "## Enhancement backlog" config/agents/*.md`
