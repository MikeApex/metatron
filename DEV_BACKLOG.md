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

- **1. [DB-0815-04] In Bulgarian mode the app shows Latin letters where it should show
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
  **Do not change more than one at a time.** *(The VM read was attempted by the 08-15 sweep and
  blocked by the permission classifier — this needs Mike or a lifted rule, not another attempt.)*
  *filed 2026-08-15 by Mike from live testing · the feature otherwise works — he confirmed
  Bulgarian in and out before switching back to English*

- **2. [DB-0815-05] Contact corrections were being written into Mike's own identity, and rode in
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
  *filed 2026-08-15 · data corrected the same day, cause open*

- **3. [DB-0815-06] The system invented an email address and stored it as fact.** The `Eva`
  contact carried **`eva@example.com`** — `example.com` is the IANA-reserved documentation
  domain, so this is not a mistyped real address, it is a placeholder the model produced and
  `write_contact` accepted and persisted. Mike, 2026-08-15: *"That shouldn't happen."*
  **Same class as the `research_agent` source fabrication** closed 2026-08-10 (`a36d8c2`) — a
  model filling a required-looking field with something plausible rather than leaving it empty.
  That one was fixed by having Python author the value instead of the model. **Here the fix is
  refusal, not authorship:** `write_contact` should reject reserved and obviously-placeholder
  domains (`example.com/net/org`, `test`, `invalid`, `localhost`) outright, the way
  `_OWN_IDENTITY_SIMILARITY_THRESHOLD` already refuses an exact match on the user's own address.
  A stored fake address is worse than a blank field — it will eventually be *sent to*.
  *filed 2026-08-15 by Mike, from the live CRM dump · value removed during the Eva/Iva merge*

- **4. [DB-0815-07] CRM writes are never deduplicated against existing contacts, so the same
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
  *filed 2026-08-15 by Mike · (a) resolved in data, cause open · this is the same dedup risk
  flagged for the Google Contacts pull in `[DB-0810-17]` — a bulk import makes it acute*

- **5. [DB-0809-02] Every scheduled job re-asks the same unanswered question, so one unfinished
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
  *filed 2026-08-09 · rewritten 2026-08-09 after measurement inverted it · **evidence corrected
  2026-08-10** — see `archive/PROJECT_LOG.md` § 2026-08-10, last · **recurrence merged in from the
  Inbox 2026-08-14**, reported by Mike via the VM (2026-08-12T08:23Z); fix date verified against
  `git log` the same day*

- **6. [DB-0810-15] A persona should be able to send in one language and receive in another —
  independently.** *(Rescoped 2026-08-15 by Mike. The original entry was "voice transcription is
  English-only"; that was the symptom he hit, not the need. The voice half is now `[DB-0815-02]` in
  `## Later`, low priority — **text is the actionable path and it is not blocked by anything**,
  because the model is already multilingual and typing Bulgarian works today.)*
  **Two independent per-persona settings, not one:**
  - **Input language** — what the user writes/speaks.
  - **Output language** — what Metatron responds in.
  They do not have to match, and that asymmetry is the requirement, not an edge case. Mike's two
  worked examples: persona A sends and receives entirely in Bulgarian; persona B receives Bulgarian
  but answers in English.
  **The third piece, which is the real work:** content that did not originate in the output
  language must arrive **already translated** — persona A reading an English email gets it in
  Bulgarian, not in English with an offer to translate. So this is not a response-language flag; it
  is a translation boundary on surfaced content, and the boundary has to sit somewhere deliberate
  (Synthesizer output vs. each tool's return value). **Decide that placement before building** — put
  it in the wrong layer and every specialist grows its own translation logic.
  **✅ STORAGE HALF BUILT AND MERGED 2026-08-15** (`9a46608`): `input_language` / `output_language`
  are independent per-persona fields in [tools/profile.py](tools/profile.py), stored as ISO 639-1
  codes, rendered into the system prompt by `load_profile()`
  ([core/orchestrator.py:102](core/orchestrator.py#L102)). 16/16 tests in
  [tests/test_profile_language.py](tests/test_profile_language.py). **Unset renders nothing** — no
  preference stays distinguishable from a preference for English. Not deployed.
  **⚠ Found while building, and it invalidates a claim this entry relied on:** `load_profile()`
  lives in `core/orchestrator.py`, **not** `tools/profile.py`, and is a hand-written per-field list
  that does not derive from `WRITABLE` or `_PROMPT_EXCLUDED`. `_PROMPT_EXCLUDED` has exactly **one**
  reference in the codebase — its own definition. Contact details stay out of the prompt only
  because that list happens not to render them, while `profile.py`'s docstring says they are
  *"deliberately excluded"*. **Nothing enforces it.** Documented in place 2026-08-15; the real fix
  is to make `load_profile()` derive from the set. Same class as the unenforced tool allowlists.
  **✅ Boundary decided 2026-08-15 by Mike: the Synthesizer's output, and only there. BUILT AND
  DEPLOYED (`8a7d1d7`, `b3ff108`).** Translation runs **after** `filter_output()` as a Python
  post-processing step against a cheap model — one place, no per-tool logic. **Two designs were
  tried and rejected first (prose in `synthesizer.md`; a `translate` tool the model calls); both
  refusals and their reasoning are permanent in `core/translate.py`'s module docstring**, which is
  where a session that needs them will be standing. Do not re-propose either.
  **Both known costs were accepted and are live in the code, not hidden:**
  1. **It breaks streaming.** A translation pass needs the complete response, so a persona with an
     output language set loses token-by-token streaming — the same constraint behind the
     `[RETRACT]` design in `ROADMAP.md` § 5A. Voice makes this worse, not better.
  2. **One extra model call per response**, on every turn for that persona, and it must stay on the
     ZDR path — it is translating personal content, so it is sensitive-tier and cannot go to a
     shared cloud model.
  **What is left before this closes:**
  1. **Never run end to end** — no persona has `output_language` set, so translation is a no-op
     everywhere today and every test stubs the backend. Set it on a test persona and run one real
     exchange before trusting it.
  2. **The A4 clinical hard-fails have never run with a response language set.** They cannot
     regress today (no-op), but once a persona is translated, flag *substance* must survive
     translation — the pipeline suite's pass condition is that crisis framing and medication names
     reach the user, and that has only ever been checked in English. **Run
     `tests/run_a4_safety.py --suite pipeline` against a translated persona before any persona
     with clinical history gets a response language.**
  3. Speech-in is still English-only — `[DB-0815-02](a)`, unchanged.
  4. **The known cost to watch, not to design around now:** content the Synthesizer treats as a
     verbatim quote (an email body it is relaying) may pass through in its source language. If that
     shows up in real use, the fix is to tag source language on tool returns and let the Synthesizer
     act on the tag — *not* to move translation into the tools, which is the option this decision
     rejected.
  Privacy note: translation of personal content is sensitive-tier and stays on the ZDR path.
  *original filed 2026-08-10 by Mike live during feature testing · rescoped 2026-08-15 by Mike ·
  the `METATRON_WHISPER_LANGUAGE` knob shipped `1d858f2` and is **not** this item · the voice
  blockers live in `[DB-0815-02]`, which owns them — a duplicate copy was cut from here 2026-08-15*

- **7. [DB-0810-17] An external CRM bridge — the count question itself is answered.** At seq 009
  Mike asked for a route *and* a CRM contact count; the system declined it as needing an external
  connection it doesn't have, when Metatron's own contact store (`list_contacts`, `search_contacts`
  in [tools/crm.py](tools/crm.py)) already held the answer. **(a) closed 2026-08-15** —
  `coordinator.md`'s Relationships routing block now calls out contact-store questions explicitly
  and says not to decline them (`b11e775`). **(b) remains: an external CRM bridge.**
  **✅ UNBLOCKED 2026-08-15 — the vendor decision this entry was waiting on turned out not to
  exist.** Mike's actual requirement: for Mike-persona testing the internal CRM **pulls from Google
  Contacts**, and any other CRM arrives by **import in conventional file types**. So there is no
  *which CRM* to choose and no per-vendor API bridge to build — the previous framing of this item
  was the blocker, not the work. Three concrete pieces, verified against current code the same day:
  1. **`read_google_contacts` is built but unreachable.** [tools/google_contacts.py](tools/google_contacts.py)
     is complete — read-only People API, per-persona OAuth, one-time consent via
     [scripts/google_contacts_authorize.py](scripts/google_contacts_authorize.py) — but it is
     **never imported into `register_tools()` and never granted in either routing file**. Compare
     the CRM tools, wired at [core/orchestrator.py:479](core/orchestrator.py#L479) and
     [:595](core/orchestrator.py#L595). It appears only in `tools/metatron_monitor.py:141`'s API-name
     map, which is why nothing flagged it. **Inverse of `[DB-0810-03]`'s class**: not a tool named
     without a grant, but a tool built without a registration — and `scripts/check_agent_tools.py`
     cannot see this direction either, since it sweeps agent files against allowlists and neither
     mentions this tool. Worth asking whether that guard should also flag a `tools/` module that
     nothing registers.
  2. **Reading is not pulling.** `read_google_contacts` returns data; nothing writes it into
     `contacts.json`. The onboarding/sync path does not exist, so "the internal CRM pulls from
     Google Contacts" is not true even once (1) lands. Decide dedup on the way in —
     `_find_by_name` is naive substring matching (the `[DB-0810-11]` "Jon"/"Jonathan" case), so a
     pull is exactly where duplicate records get created at volume.
  3. **No import path of any kind exists** — no vCard, no CSV, in `tools/crm.py` or anywhere else.
     This is the "any CRM should be importable" half.
  Sensitive-tier throughout. Google Contacts write-back stays out of scope — deliberately excluded
  when the module was built, and nothing here needs it.
  *filed 2026-08-10 by Mike · (a) closed 2026-08-15, see `archive/backlog_closed_2026-08.md` ·
  (b) reframed and unblocked 2026-08-15 by Mike; the three pieces above were verified against
  current code, not inferred from the entry*


## Later

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

- **[DB-0813-02] `OPENAI_API_KEY` is invalid — `ask_gpt` has been silently dead.** A live
  `mcp__ask_gpt__ask_gpt` call returns `401 invalid_api_key` against the key in `.env`. Nothing
  announces this: a multi-model round just comes back with two voices instead of three, and the
  missing one looks like a choice rather than a failure. Found 2026-08-13 while running a Chorus
  review of the commit-guard design — Gemini answered, GPT did not, and the round proceeded
  one voice short. **Fix is a key rotation, not code.** Worth checking whether the other keys in
  `.env` are still live at the same time. *filed 2026-08-13 by a dev session · verified live,
  not inferred*

Real, not prioritised. One or two lines each — detail lives in the code, the log, or
`archive/backlog_closed_2026-08.md`.

**Two standing rules, both Mike's (2026-08-10):** a **machine-originated** item promotes to
`## Now` once its error has been **recorded three times** (the ×3 threshold the machine log
uses — count before promoting), while **anything Mike raises promotes on first report**, no
count — the ×3 bar is a floor for things nobody asked for, not a hurdle for a user report
(clarified 2026-08-13; the rule read "an item", which contradicted `## Now`'s entry bar and
`/backlog`'s "promoted the day he hits it"); and **`Now` is cleared before `Later` is started**,
so this is not a parallel track to pick from when a `Now` item is time-gated.

**Safety and test gaps**
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
- **[DB-0815-09] Half the system's self-reported corrections say nothing, and the noise now leads
  Mike's session-start line.** Measured 2026-08-15 against the live VM: **93 of 174
  `USER_CORRECTION` events carry a `detail` of `None` / `None.` / `N/A` / `[None]` — 53%**, 78 of
  them in August alone. That is why `None. ×90` is the loudest signature in the `⚠ machine:` clause,
  crowding out the real ones (`×16`, `×6`, `×5`). Two candidate causes, and one look separates them:
  the classifier over-fires `USER_CORRECTION` on turns that are not corrections and the summariser
  honestly reports none, **or** the summary is simply not being populated. The first is the more
  useful finding, because it would mean the correction *count* is inflated too — and that count is
  the ×3 promotion bar in this file.
  **Second finding, same measurement, and it changes how a `×N` should be read: the counts are
  similarity clusters, not repeats.** The `×16` "scheduled calendar events imply completion"
  signature resolves to exactly **one** event fuzzy-matched with fifteen differently-worded others.
  Nobody should treat a `×N` as "Mike said this N times" — `merge()` in
  `scripts/sync_dev_backlog.py` collapses on `similar()`. Worth a line in the `## Machine log`
  preamble whichever way the first half resolves.
  *filed 2026-08-15 by the `/backlog deep` machine-log sweep — **not raised by Mike***
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
- **[DB-0815-02] Voice in a language other than English — both directions. LOW priority (Mike,
  2026-08-15).** Split out of `[DB-0810-15]` when that item was rescoped to the text path, which is
  unblocked and carries the actual need. Voice is blocked twice, and the second half is not filed
  anywhere else:
  *(a)* **Speech in** — `WHISPER_MODEL_SIZE` is `base.en`, English-only; multilingual needs `base`,
  which reopens the sizing constraint at [core/voice_pipeline.py:31](core/voice_pipeline.py#L31).
  **Benchmark on the VM, never the Mac** — `python3 tests/bench_whisper_stt.py --models base
  --languages en,bg`; an M-series laptop makes an unaffordable model look fine, and `small.en` was
  already measured at RTF 2.23 and rejected on a 2-vCPU single-worker pool.
  *(b)* **Speech out** — both TTS voices are hardcoded English (`KOKORO_VOICE = "af_heart"`,
  `EDGE_VOICE = "en-US-JennyNeural"`). edge-tts has `bg-BG-*` neural voices; Kokoro's language
  coverage is unverified. **No auto-detect solves this half** — synthesising speech needs a stored
  language value, which is why `[DB-0810-15]`'s preference is the prerequisite, not a parallel path.
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
- **[DB-0806-02]** Level 3 web access. Split into rendered-read (`fetch_rendered`, Playwright,
  read-only — recommended, same trust boundary as `fetch_url`; check VM memory first) and
  interactive click/type/submit, which stays gated on a credential store that does not exist.
  Covers Mike's *"reserve tickets on the R website"* ask. Scope:
  `archive/plans/level3_web_actions_scope_2026-08-06.md`.
- **[DB-0808-04]** **Location signal + the venue discovery gated on it.** *(a)* Real-time GPS
  and proactive area-scanning (Mike's framing) needs a design pass: privacy tier for continuous
  location, which layer supplies it, how scanning bounds itself. *(b)* Google Places venue
  discovery for `logistics`/`recreation_hobbies` is blocked on exactly that signal — but
  **"near a named address" needs no GPS and could ship first**.
  *merged 2026-08-10 — absorbed `[DB-0807-02]`, the same blocker restated*
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
  `write_archive` dedup; `tools/wisdom.py` reloading `SentenceTransformer` per call where
  `core/memory.py` caches a singleton); (b) code that removes agent calls entirely — cuts against
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
"`×N` is a similarity cluster, not a repeat count" finding are filed as `[DB-0815-09]`** — read that
before trusting any count in this section.)*

- **[already applied by the tool]** Switched output to Bulgarian transliteration (Latin alphabet) to match user's STT workaround.  
  `2026-08-15T13:51:39.676925Z`
  → **promoted 2026-08-15 into `[DB-0815-04]` candidate (c). Do not re-file.**

- **[user corrected a prior turn]** User is confirming the necessity of a workaround for the Bulgarian language recognition bug.  
  `2026-08-15T13:50:27.705106Z`

- **[user corrected a prior turn]** [N/A - the user's message is a shift in intent, not a correction of a past error.]  
  `2026-08-15T13:48:33.030203Z`

- **[user corrected a prior turn]** N/A  
  `2026-08-14T20:02:29.913465Z`

- **[user corrected a prior turn]** N/A  
  `2026-08-14T14:01:52.439999Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'Date Day: The Mousetrap' (2026-08-18T00:00:00, uid=64dc9379-ce64-4c15-a96a-c6cb4df8e432@ai-life-manager) and 'The Mousetrap Matinee' (2026-08-18T15:00:00, uid=efdc94bb-07b2-49ef-be3a-a43431d8014d@ai-life-manager). title_similarity=0.59, shared_attendees=[], shared_words=['mousetrap']. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-08-14T04:35:08.871922Z`

- **[user corrected a prior turn]** User corrected the previous exercise log, stating the run was only a test and requested its removal.  ×2  
  `2026-08-15T11:13:42.274343Z`

- **[user corrected a prior turn]** Dropping the Manny/protest thread and modifying the check-in format to a consolidated 14-point list.  
  `2026-08-12T08:20:17.031497Z`

- ⚠ **[user corrected a prior turn]** Missed the user's previously stated Thursday deadline for the Prudential email and prompted action on it prematurely.  ×5  
  `2026-08-11T11:13:14.252775Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'Draft & Send Prudential Follow-up to Mike' (2026-08-13T00:00:00, uid=a77d8ee0-d0a5-4376-8c33-1c82ed8b0624@ai-life-manager) and 'Check for Prudential scheduling email (Kathleen Jermyn)' (2026-08-13T00:00:00, uid=509f27f7-9d19-4d62-a3cf-ac01eac292fc@ai-life-manager). title_similarity=0.4, shared_attendees=[], shared_words=['prudential']. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-08-11T04:35:16.777905Z`

- **[user corrected a prior turn]** The user corrected the grocery reminder logic (not every Friday, but 3 days after the date of an order).  ×2  
  `2026-08-10T15:46:40.890480Z`

- ⚠ **[user corrected a prior turn]** User clarified they wanted to know the mechanism/tools for routing, not the route itself.  ×3  
  `2026-08-10T12:29:39.464756Z`

- ⚠ **[user corrected a prior turn]** Noted that Giva is likely a reference to Iva Diamond, who was previously noted as the lunch partner.  ×3  
  `2026-08-12T12:47:55.686306Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'Meeting with Jonas at Cross Keys\, Bank' (2026-08-05T17:40:00, uid=696faa2c-1194-4bfd-9ef4-ba9fb500918a@ai-life-manager) and 'Meeting with Jonas at The Cross Keys\, Bank' (2026-08-05T17:40:00, uid=e715ca00-1b55-48c1-953f-f5f10b44cbcf@ai-life-manager). title_similarity=0.95, shared_attendees=[], shared_words=['bank', 'cross', 'jonas', 'keys\\', 'meeting']. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-08-08T17:13:23.351554Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'Meeting with Jonas' (2026-08-05T17:40:00, uid=8d0414f4-5be3-4f5b-96e8-1cd78041dd04@ai-life-manager) and 'Meeting with Jonas at The Cross Keys\, Bank' (2026-08-05T17:40:00, uid=e715ca00-1b55-48c1-953f-f5f10b44cbcf@ai-life-manager). title_similarity=0.59, shared_attendees=[], shared_words=['jonas', 'meeting']. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-08-08T17:13:23.351323Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'Meeting with Jonas' (2026-08-05T17:40:00, uid=8d0414f4-5be3-4f5b-96e8-1cd78041dd04@ai-life-manager) and 'Meeting with Jonas at Cross Keys\, Bank' (2026-08-05T17:40:00, uid=696faa2c-1194-4bfd-9ef4-ba9fb500918a@ai-life-manager). title_similarity=0.63, shared_attendees=[], shared_words=['jonas', 'meeting']. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-08-08T17:13:23.351136Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'Meeting with Jonas at The Cross Keys\, Bank' (2026-08-05T17:40:00, uid=ece109dd-12ed-4212-b633-88329d40e772@ai-life-manager) and 'Meeting with Jonas at The Cross Keys\, Bank' (2026-08-05T17:40:00, uid=e715ca00-1b55-48c1-953f-f5f10b44cbcf@ai-life-manager). title_similarity=1.0, shared_attendees=[], shared_words=['bank', 'cross', 'jonas', 'keys\\', 'meeting']. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-08-08T17:13:23.350926Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'Meeting with Jonas at The Cross Keys\, Bank' (2026-08-05T17:40:00, uid=ece109dd-12ed-4212-b633-88329d40e772@ai-life-manager) and 'Meeting with Jonas at Cross Keys\, Bank' (2026-08-05T17:40:00, uid=696faa2c-1194-4bfd-9ef4-ba9fb500918a@ai-life-manager). title_similarity=0.95, shared_attendees=[], shared_words=['bank', 'cross', 'jonas', 'keys\\', 'meeting']. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-08-08T17:13:23.350722Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'Meeting with Jonas at The Cross Keys\, Bank' (2026-08-05T17:40:00, uid=ece109dd-12ed-4212-b633-88329d40e772@ai-life-manager) and 'Meeting with Jonas' (2026-08-05T17:40:00, uid=8d0414f4-5be3-4f5b-96e8-1cd78041dd04@ai-life-manager). title_similarity=0.59, shared_attendees=[], shared_words=['jonas', 'meeting']. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-08-08T17:13:23.350509Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'Depart for Heathrow (LHR) Airport' (2026-08-05T11:00:00, uid=6a7cd62e-f48c-44ab-9caf-b3acd2075dbf@ai-life-manager) and 'Heathrow drop-off' (2026-08-05T11:00:00, uid=0e217f61-00f3-4213-9296-437c87c16adb@ai-life-manager). title_similarity=0.48, shared_attendees=[], shared_words=['heathrow']. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-08-08T17:13:23.350103Z`

- **[user corrected a prior turn]** N/A  
  `2026-08-07T06:11:35.754575Z`

- ⚠ **[user corrected a prior turn]** User previously confirmed Rowan transfer was handled, but system asked for details again.  ×3  
  `2026-08-07T16:22:17.434741Z`

- ⚠ **[user corrected a prior turn]** User pasted the check-in preference for a third time. In previous turns, the Synthesizer failed to adhere strictly to 'Otherwise just ask what's on', adding filler ('Nothing urgently needs your attention...' and 'I already have that instruction...'). The system needs to recognize strict negative constraints.  ×3  
  `2026-08-09T12:27:20.856785Z`

- **[user corrected a prior turn]** [N/A]  
  `2026-08-04T13:59:16.811749Z`

- **[user corrected a prior turn]** The user is correcting the system for failing to proactively manage the Apex meeting and payroll tasks, which they expect to be handled automatically.  ×2  
  `2026-08-05T15:19:21.740492Z`

- **[user corrected a prior turn]** [N/A]  
  `2026-08-04T13:57:17.397614Z`

- ⚠ **[user corrected a prior turn]** Corrected contact name from "Eva" (previously appearing in logs) to "Iba".  ×5  
  `2026-08-04T12:42:13.046792Z`

- ⚠ **[user corrected a prior turn]** User corrected the assumption that scheduled calendar events imply completion, requesting active reconciliation and pushing alerts instead of passive tracking.  ×16  
  `2026-08-12T08:25:12.628744Z`

- **[user corrected a prior turn]** User opted to close the CalDAV integration thread.  ×2  
  `2026-08-04T12:37:18.994165Z`

- **[user corrected a prior turn]** User corrected system for excessive repetition of pending tasks, over-indexing on sleep disruption, and intrusive scheduled check-ins during active dialogue.  ×2  
  `2026-08-02T17:48:22.011991Z`

- **[user corrected a prior turn]** User explicitly requested to stop being told to "enjoy things" after Synthesizer used the phrase "Enjoy the museum" in the previous turn.  ×2  
  `2026-08-02T14:05:23.180476Z`

- ⚠ **[user corrected a prior turn]** Correction of the RAF Museum schedule (user was there yesterday, not this evening).  ×4  
  `2026-08-03T09:10:59.166436Z`

- ⚠ **[user corrected a prior turn]** User restated 'rucking and high intensity' to correct a prior dictation error ('rocking and hop and swing both balls') and reaffirm their fitness baseline.  ×4  
  `2026-08-03T17:15:55.567859Z`

- ⚠ **[user corrected a prior turn]** The user corrected the system's outdated belief that they are still in "post-travel recovery," confirming that period is over and requesting the system adjust its internal state accordingly.  ×6  
  `2026-08-12T08:23:05.655993Z`

- ⚠ **[user corrected a prior turn]** The user is correcting the log entry for 2026-08-15 by stating the morning run was a test and should be removed.  ×3  
  `2026-08-15T11:13:18.513588Z`

- **[user corrected a prior turn]** Mike is correcting the assumption that his 'fit it in' approach to work creates negative pressure; he finds it manageable and beneficial for his family balance.  
  `2026-06-26T21:35:02.264614Z`

- ⚠ **[user corrected a prior turn]** None.  ×90  
  `2026-08-15T19:29:01.706119Z`

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
