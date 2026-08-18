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
`## Now` or `## Later`, rewritten properly, and **delete them from here, leaving nothing behind**.*

> **Triaging an entry out leaves no trace in this section — the evidence goes to
> `archive/backlog_closed_YYYY-MM.md`.** Six "(empty — triaged on date X)" notes had accumulated
> here by 2026-08-18, 30 lines recording that work had been *removed*. That is the mechanism by
> which this file grows while nothing is outstanding, and it is the one Mike named.
>
> **Three standing cautions, kept because they change what a triager does.** Harness/tooling
> defects are **not** Metatron work and do not belong in this file at all. A machine-filed entry
> can restate a report Mike already filed by hand the same day, because nothing checks for that.
> And **read a machine entry as a symptom, never as a diagnosis** — three had named a real problem
> and guessed its cause wrongly.
>
> **Check the date on the `×N` before you believe it.** A `×N` written before 2026-08-15 is a
> similarity **chain length**, not a repeat count (`SIMILARITY_THRESHOLD`'s comment in
> `scripts/sync_dev_backlog.py` has the worked example — sixteen unrelated corrections reported as
> one signature). All three machine entries triaged into this file on 2026-08-15 carried pre-fix
> counts, and all three were single events; every one of them was also **older than the code that
> fixed it**. They were removed on 2026-08-18. Confirm the count *and* compare the evidence date
> against `git log` before promoting anything from here.
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

- **1. [DB-0808-04] Suggest a café near a named address.** Google Places venue discovery for
  `logistics` / `recreation_hobbies`. **Needs no GPS** — it was parked for months behind the
  real-time location question, which is a different item (`[DB-0815-12]`) and always was.
  Ready to build; ranked first.
  @kind: feature
  *filed 2026-08-08 by Mike · promoted 2026-08-15*

- **2. [DB-0818-10] The reply lands in one lump after a long silence, so speech cannot start early.**
  @kind: feature
Mike, live at the app 2026-08-18: *"the entire bubble publishes at once, not word by word or phrase
by phrase."* Observed on two separate turns.

**Measured, not inferred.** The turn he watched: total **22.7s** — coordinator 2.2s, two specialists
7.1s, **synthesizer 11.4s on `gemini-3.1-pro-preview` for a 285-character reply**
(`/monitor/traces`, `persona=mike`, `2026-08-18T16:40:35`). A Pro-tier model emits 285 characters in
well under a second, so ~10s of that turn produced **no content deltas at all** — it is the thinking
phase — and the answer then arrives in a burst.

**The streaming code is correct and has nothing to stream, which is why no test caught this.**
`_openai_compat_stream` yields `delta.content` the moment it arrives
([core/orchestrator.py:3125](core/orchestrator.py#L3125)); the client appends each chunk and
repaints ([static/index.html:972](static/index.html#L972)). Both halves work. The gap is upstream:
a thinking model emits its reasoning as a separate token class that carries no `delta.content`, so
the stream is silent for the whole thinking phase. **Do not go looking for a bug in the streaming
path or the client — they were both read and both are right.**

**Why it matters more than it looks.** This is a voice-first product. TTS cannot begin until the
whole message lands (`speakResponse(ownAccumulated)` fires on `done`), so perceived latency is
generation **plus** synthesis, serially — and streaming, which exists precisely to hide that, buys
nothing today.

**This is the evidence `[DB-0809-13]` was waiting for, and it inverts that item's premise.** Kokoro's
2.8s per phrase was ruled *"do not build until voice has been used enough to say whether 2.8s
actually feels slow"* (closed 2026-08-18, `archive/backlog_closed_2026-08.md`). The measurement says
**2.8s was never the problem** — 11.4s of upstream silence is. Sentence-chunked TTS is now the
strongest of the three candidate fixes, because it is the only one that starts speech before
generation finishes.

**Three options, and they are not exclusive:** (a) sentence-chunk the Synthesizer's output so TTS
starts on the first complete sentence; (b) route the Synthesizer to a faster tier or reduce its
thinking budget — cheap, but it trades response quality on the user-facing voice, which
`ROADMAP.md` § 0 names as the dominant Alpha UX factor; (c) surface a "thinking" affordance so the
silence is legible rather than dead. **Do not pick one from this entry** — (b) is a quality trade
that is Mike's call.

**⚠ (c) IS ALREADY BUILT — checked against the client 2026-08-18, do not build it again.** While a
response is pending the mic button reads `Thinking...` and the status line `Waiting for response...`,
for the whole wait, on both the text and voice paths
([static/index.html:1153](static/index.html#L1153)). What is missing is only that the label is
**static**, so a long wait cannot be told from a hung one — an elapsed counter or animation is the
whole remaining scope, and it makes nothing faster. **The informative version is barred by design:**
naming the stage ("checking your calendar") is process narration, which `CLAUDE.md` § Discretion
forbids. So (c) is effectively spent, and the real levers are (a) and (b).

**⚠ The code under this item moved on 2026-08-18 (`81be0f7`) — read it before acting.** The Gemini
branch no longer calls `_openai_compat_stream` at all: it calls `run_session_gemini_cached()` and
yields the reply as **one chunk, deliberately** (Option B of the caching fix — the prompt cache was
worth more than a stream that was not streaming). **The symptom is unchanged and this item is not
closed**; the line references above still describe the OpenAI/Ollama path, not Gemini.

**⚠ Option A does NOT close this item, and an earlier line in this entry saying so was wrong
(corrected 2026-08-18, same day).** Measured across **18 real interactive Synthesizer turns**:
median **882 thinking tokens against 133 visible** — **86% of everything generated is thinking**.
The silence this item is about is therefore *the thinking phase*, which streaming cannot shorten;
Option A only lets the remaining ~14% arrive progressively. It is still the right end state and it
is the prerequisite for option (a), but on its own it recovers a small share of the dead air.
Option A is briefed in `archive/handoffs/2026-08-18-caching-fix-prompt.md`; its design constraint is
that tool turns run blocking and only the final turn streams.

**Option (b) is now the dominant lever on both axes, and it is cheap to try.** `thinking_budget`
exists in the installed SDK (`google-genai` 2.8.0, `types.ThinkingConfig`) and is **configured
nowhere in this project** — so the Synthesizer currently thinks unbounded. It is also the cost
lever: thinking is **86% of output spend** at $12/1M. Note `thinking_budget: 0` was tried and
rejected for a *different* purpose ([core/orchestrator.py:1202](core/orchestrator.py#L1202)) —
**disabling thinking is not the same as capping it**, and that rejection does not settle a cap.
Any cap must re-run the A4 clinical gate, since reasoning depth is what those flags rest on.
**Still Mike's call — it trades quality on the user-facing voice.**

*found 2026-08-18 during Phase 1 interactive testing — Mike reported the symptom unprompted while
confirming a different fix; the timings were pulled live off the VM the same minute*


## Later

**Three groups, and the group is the useful fact about an item.** *Decisions* are blocked on a
judgement only Mike can make. *Waiting on one use* is finished, deployed code that closes the
moment someone exercises it. *Unbuilt* is real capability that does not exist — that group is
allowed to sit, and it is not what makes this file grow.

**Two standing rules, both Mike's (2026-08-10):** a **machine-originated** item promotes to `## Now`
once its error has been recorded three times — **count it against the `×N` caveat in `## Inbox`
first** — while **anything Mike raises promotes on first report**. And **`Now` is cleared before
`Later` is started**, so this is not a parallel track to pick from.

**`due:` is a review date, not a deadline.** `due_now()` in `scripts/sync_dev_backlog.py` scans both
sections and surfaces them on the sync line at session start, so a time-gated item wakes itself. If
the condition has not arrived, push the date rather than closing the item.

### Decisions — each needs one answer from Mike, not effort

- **[DB-0818-08] Nothing records where a fact came from, so a checked value is overwritten by a
  guessed one — and an answer with no source is delivered as fact.** Mike, 2026-08-18: *"the CRM needs
  some sort of verification tag for data that will allow it to stick to its guns when an edit or
  contradictory information is incoming"*, scoped at his instruction to **a universal, not a CRM
  feature**.
  **Two live failures the same afternoon, and they look unrelated until the missing field is named.**
  *(1)* `Kathaleen Jermyn` was in the CRM off her own email signature; a dictated correction to
  `Kathleen` renamed the record in place — no near-match surfaced, no confirmation asked, and **the
  correct spelling is the one now gone.** *(2)* Asked for the Southeastern line, `research_agent` ran
  two web searches, retrieved **zero sources** (`grounded: False`, trace `2026-08-18T16:48`), and
  answered *"Southeastern services are reported as having a good service overall"* with an invented
  incident. One overwrote a sourced value with an unsourced one; the other presented an unsourced
  claim as sourced. **Same missing field.**
  **The shape: three tiers, the smallest set that separates those two.** `verified` — checked against
  an external artefact (email header, calendar invite, retrieved source) → **surface the conflict and
  ask**. `stated` — the user said it → overwrite freely; he is the authority on his own life.
  `inferred` — the model concluded it → overwrite freely, and **never present as fact without saying
  so**.
  **The constraint that must survive into the build, Mike's own words: "user instruction should
  generally be the winner."** The tag produces a **confirmation, never a refusal** — one question,
  once, not a veto and not a question every time. A tool that argues about how his family's names are
  spelled is worse than one that occasionally takes a wrong spelling.
  **Why it plausibly suppresses hallucination — his claim, recorded as a hypothesis, not a promise.**
  `inferred` is not a state anything can currently be in, so an answer assembled from nothing is
  shaped identically to one assembled from sources. Give it a tier and the refusal becomes mechanical
  rather than a matter of model judgment: **an answer with no `verified` or `stated` input cannot be
  phrased as fact.** Same control as the zero-source guard, applied to the store instead of the wire —
  **scope them together rather than building it twice.**
  **The hard part is not the schema, it is the capture.** Provenance has to be recorded by code that
  knows the source, and most write paths are model-called with no source argument at all: `read_email`
  and the CalDAV reader hold an artefact and know it, `write_contact` mid-conversation does not.
  **Scope the capture before the schema** — a tag defaulting to `verified` because nothing filled it
  in would claim a check the system never did, which is worse than no tag.
  @kind: feature
  @session: the three tiers, and whether `inferred` gates phrasing as well as overwriting
  *raised by Mike 2026-08-18 during Phase 1 testing, from two failures he produced himself in
  consecutive turns · scope against `[DB-0815-07]` (near-match on create — built, did not fire on this
  rename, a different path) and `[DB-0818-06]` (24 stored "facts", several inferred preferences
  recorded as observations — what an `inferred` tier catches at write time)*

- **[DB-0810-03] 39 tool-permission decisions, and they block the agent audit Phase 5 sign-off
  needs.** 35 named-but-not-granted, 4 refused in production
  (`learning_growth`→`write_archive`, `recreation_hobbies`→`write_agent_config`,
  `logistics`→`read_archive`/`write_archive`). Each is a separate grant/build/drop call.
  **The guard itself is finished** — `scripts/check_agent_tools.py` scans agent files *and* persona
  files, ran clean on the VM 2026-08-18 (17 + 17 files, `mike` seen, 0 named-as-live-but-unbuilt).
  **Do not switch to enforce mode before the lists are corrected:** `logistics` calls `send_email`
  without the grant and the dispatcher executes it, so enforcing today kills outbound email.
  @kind: chore
  @session: 39 grant decisions — its own run, not a side-task in a sweep
  *filed 2026-08-10 · guard half closed 2026-08-10 and 2026-08-18 · only the decisions remain*

- **[DB-0809-02] One unfinished ritual arrives as three or four separate messages.** Read live off
  the VM 2026-08-15: the "three repetitive evening messages" were **four different scheduled jobs**,
  each re-asking the same unanswered question. `evening_close` is a victim, not the culprit.
  **The mechanism: "raise a thing once" has no memory that a question was asked and left
  unanswered**, so every unrelated job that fires inherits the unfinished ritual from context.
  **Two prior diagnoses were confidently wrong** (narrative in `archive/backlog_closed_2026-08.md`
  § Closed 2026-08-15), which is why the third is not being picked without him. **Do not re-apply
  the ≤2-sentence cap** — rejected deliberately; focus is the target, length only its symptom.
  @kind: bug
  @session: give "raise a thing once" cross-session memory of an unanswered question, or forbid a
  job from continuing a ritual that is not its own
  *filed 2026-08-09 · rewritten twice as measurement inverted it*

- **[DB-0815-11] The system recorded a preference change it appears never to have made.** A
  `SELF_APPLIED` event at `2026-08-15T13:51:39Z`: *"Switched output to Bulgarian transliteration
  (Latin alphabet)…"* — but no transliteration line exists in any persona file on the VM (Mike
  grepped). Either it wrote somewhere unexamined or it reported an action it did not take. **Honest
  caveat:** he reverted his language test the same day, so "written then reverted" cannot be
  distinguished from "never written" without a backup.
  **The second-order concern is the real one:** this was the second wrong self-applied preference in
  four days (the 08-12 check-in consolidation was the first, and he rejected it). Both were silent.
  @kind: bug
  @session: whether `write_persona` may self-apply an inferred preference at all without confirmation
  *filed 2026-08-15 from the machine log*

- **[DB-0810-11] Where should code replace model judgment?** Raised by Mike 2026-08-05, never given
  its own session. Three strands: (a) deterministic lookups feeding agents evidence instead of asking
  them to recall — `tools/scheduling.py` is the worked example; (b) code that removes agent calls
  entirely, which cuts against the head-layer/specialist split and PoLP, so not free; (c) a standing
  code/agent review protocol. Also parked here: `temperature`, **not plumbed through any of the four
  provider paths**, most valuable for clinical flags and Finance arithmetic.
  **What is left of (a), measured 2026-08-18:** contact-name matching is done. `write_contact` scores
  similarity and flags near-matches, but **a nickname is a prefix, not a typo** — `Jon`/`Jonathan`
  scores 0.545 against a 0.6 bar and slips, and raising the bar starts merging different people, so
  that needs a separate prefix signal. **`write_archive` has no dedup of any kind**
  ([tools/diarist.py:110](tools/diarist.py#L110)) — untouched.
  @session: is (c) — a standing review protocol — worth a session, or is this three items?
  *filed 2026-08-10 · the wisdom-embedding strand closed 2026-08-15 (`13134bc`)*

- **[DB-0814-03] Manage the mailbox as tickets rather than as a stream**, so a thread has a state
  instead of being re-read each pass. Real and unbuilt. **Blocked on what a ticket *is*** (a thread,
  a sender, an obligation), where its state lives, and how it relates to two things that already
  overlap it: `tools/obligations.py` — which is most of a ticket lifecycle, already built — and the
  null-report silencing in `[DB-0814-01]`, arguably the same want expressed smaller.
  **Scope against obligations before designing anything new.**
  @kind: feature
  @session: what a ticket is, and whether obligations already are one
  *filed 2026-08-14 by Mike via the VM*

- **[DB-0815-12] Real-time location as a signal.** GPS and proactive area-scanning. Needs a design
  pass before anything is built on it: the privacy tier for **continuous** location, which layer
  supplies it, and how scanning bounds itself. Split out of `[DB-0808-04]` 2026-08-15 — keeping them
  as one entry hid a shippable feature behind an unmade decision for a week.
  @session: the continuous-location privacy tier
  *filed 2026-08-10 · split 2026-08-15*

- **[DB-0818-07] The safety regression passes without ever touching stored knowledge.**
  `run_a4_safety.py --suite pipeline` runs against `sarah_chen`, whose VM store holds **one** entry —
  a work-boundary pattern no clinical scenario touches. So no `KNOWLEDGE_TO_LOAD` fires and 3/3 PASS
  says nothing about whether standing knowledge interacts safely with clinical flags. That matters
  because the knowledge layer now injects fetched entries into `mental_wellbeing`'s directive: an
  entry contradicting a clinical read is exactly the case nothing exercises.
  **Coverage means health-domain entries on the VM's `sarah_chen`, which changes what the suite
  measures** — a decision, not a chore. `seed_medication_fixture` is the precedent if the answer is
  yes. Related trap: **Mac and VM copies of a persona store diverge silently** and `data/personas/*/`
  is gitignored — anything reasoning about a persona's data must name which machine it read.
  @kind: chore
  @session: seed clinical-adjacent knowledge into the test persona, or accept the gap
  *raised 2026-08-18 at the close of the knowledge-layering session · triaged out of `## Inbox` 2026-08-18*

### Done and deployed — each closes on one ordinary use

*This group was a quarter of the backlog on 2026-08-18 and the single biggest reason the file grew:
finished work with no exit. **A fix is confirmed in the session that makes it, or it is time-gated
with a date.** Nothing new joins this group open-ended.*

- **[DB-0810-01] Answers appeared twice when the connection dropped.** Fixed and deployed
  2026-08-18 (`fd273bf`): the client detaches the dying socket and waits for its real `close` before
  connecting, with a 1500 ms fallback. `tests/test_ws_reconnect_race.js` 5/5, **confirmed failing on
  HEAD first**. **Option (ii) was wrong and must not be revisited** — refusing a second connection
  per persona breaks the deliberate multi-device broadcast set (`core/server.py:748`).
  @kind: bug
  @waiting: one live reconnect — background the app past 45s, return, confirm a streaming reply
  renders once. Browser and Android WebView. **Do not close on "it works now"**: a restart previously
  looked like a fix and only showed the stored record was clean.
  *filed 2026-08-10 by Mike, live*

- **[DB-0815-05] Corrections about other people were rewriting who Mike is.** His `profile.yaml`
  `name` field literally read *"Contact name updated from Eva to Iva."*, and `load_profile()` put
  that sentence in every head-layer prompt as his name. Almost certainly the mechanism behind a
  correction he made five times. **Data fixed on the VM 2026-08-15**; guard built and deployed
  (`97b777c`, registered `704e79b`) — `write_profile` refuses a `name`/`other` value reading as a
  third-party correction and points the caller at `write_contact`. Narrow and conjunctive by design;
  verified not to refuse "Robert Smith Jr.".
  @kind: bug
  @waiting: one live turn where Mike corrects a contact name, then check `profile.yaml` is untouched
  — what is being tested is whether the *model* now picks the right tool, which is behaviour
  *filed 2026-08-15*

- **[DB-0815-07] The same person kept accumulating separate contact records.** `Eva` and
  `Iva Diamond` were one person and survived five corrections. **Built and deployed** (`97b777c`,
  `704e79b`): `merge_contacts` folds one record into another, unions list fields, and **archives
  rather than deletes** with a `merged_into` pointer that `read_contact`/`search_contacts` follow —
  the first implementation of the project's archive-on-merge rule here. `write_contact` surfaces
  near-matches as evidence before creating; Eva/Iva and Kathaleen/Kathleen both trip it.
  @kind: bug
  @waiting: one live near-duplicate surfaced, and an agent resolving it with `merge_contacts`
  *filed 2026-08-15 by Mike · same dedup risk applies to a bulk Google Contacts import*

- **[DB-0810-07] The monitoring view's newest fields have never seen live data.** The Book's
  thinking/output-text, tool-call ok flag and `/monitor/model_errors` (`ffaf7a7`, deployed) have had
  `py_compile` and a health check only; 19 commits have crossed these files without exercising them.
  Known and accepted at build time: the SSE path reuses the `model_errors` list from the last full
  load, so a live failure shows no red tag until refresh — **document that, do not fix it blind.**
  @kind: chore
  @waiting: three steps on the VM — one exchange with a tool call that succeeds; one with a
  deliberately bad tool argument (`ok:false` renders red); one forced API failure followed by a
  further exchange **without refreshing**
  *filed 2026-08-10*

- **[DB-0809-16] The dictation readout has never been spoken to.** Code-verified against every pass
  condition 2026-08-05; never run by a human with a microphone.
  @kind: chore
  @waiting: one dictated turn
  *filed 2026-08-05*

- **[DB-0809-21] The calendar reconcile has never had a live candidate to raise.**
  `daily_calendar_reconcile` re-ran clean with 0 candidates, so the mechanism works, but no real
  unreferenced calendar event has yet existed to watch it raise as a question. A forced one proves
  nothing. *(The other three verification steps passed 2026-08-10 and are closed.)*
  @kind: chore
  *filed 2026-08-09 · deferred by Mike*
  `due: 2026-09-01`

- **[DB-0810-05] Writing tone has never been learned from a real mailbox.** Built and committed
  (`88957e6`); **every test used stubs.** The distillation half is well covered. The IMAP half is
  not, and it is the part most likely to behave differently against live Gmail: `_sent_folder()`
  discovery, tier `SEARCH` term ordering, and batched `BODY.PEEK[]` parsing — **each fails silently
  by design**, so a partial parse looks like a thin mailbox rather than a bug.
  **One real instance already found and fixed** (2026-08-10): `[Gmail]/Sent Mail` was passed to
  `conn.select()` unquoted and threw on **every** sent-side query; `_imap_quote()` added, re-verified
  live. **The item's actual question is still unanswered** — nothing got past that select until then.
  **Blocked on data, not effort:** `diamond.mike.mt@gmail.com` holds 1 sent message and 6 inbox
  messages, so no contact has enough real correspondence to test against.
  @kind: chore
  @waiting: a contact with real back-and-forth in that mailbox, then `get_tone_shape(refresh=true)`.
  **Pass:** `sent_folder_found: true`, both counts non-zero, a `tone_shape` a human recognises.
  **Fail loudly on:** any life event, date or third-party name in the profile.
  *filed 2026-08-10 by Mike*
  `due: 2026-09-01`

- **[DB-0814-02] Old conversation threads now expire — but neither signal that keeps one alive has
  been measured.** Shipped and deployed (`37b0b03`, `eb01025`, `5cf0a5e`): threads auto-drop 7 days
  after their `added` date, archived to `expired_open_threads` rather than deleted. **Grace keys on
  the *user* engaging a thread**, not on the Synthesizer resending it — the Synthesizer rewrites the
  whole list every response, so its resending something says nothing. *(The first version keyed on
  exactly that and its tests passed because they modelled "resent" but never "resent by a caller that
  resends everything".)*
  **Two thresholds are reasoned, not measured:** word-overlap grace false-positives on short generic
  threads ("call the dentist" vs "call mom later" scores 0.5 against a 0.34 bar), and material-change
  grace rides on exact-text non-match, so **one changed character per turn defeats it**.
  **⚠ The stated close method does not work — checked live 2026-08-15.** `context.json` is
  overwritten in place (no write history), `expired_open_threads` cannot be non-empty before
  ~2026-08-22, and `write_context_tracker` does not appear in traces at all. **Give it a data source
  before dispatching anyone**: cheapest is an append-only audit line per write. **Do not dispatch a
  worker on the measurement half until one exists** — one was scoped at 150–190k and would have spent
  it discovering the above.
  @kind: bug
  *filed 2026-08-14 by Mike · timestamp half closed 2026-08-15*
  `due: 2026-08-22`

### Unbuilt — real capability that does not exist

- **[DB-0818-09] An implausible instruction is acted on without a murmur; only an impossible one
  is caught, and today that was luck.** Mike, 2026-08-18, after watching *"the 32nd of September"*
  be refused: *"Would it catch something more subtle — 4am vs 4pm, 'are you sure you meant 4am?'"*
  **No. Nothing checks plausibility anywhere.**
  **Two different classes, and only one is handled.** *Impossible* — the 32nd of September — has
  exactly one right answer and anything can catch it; the model happened to catch this one itself
  **before any tool ran**, so it was never validated in code either. *Implausible* — 4am for the
  park — is perfectly valid input. The calendar write path runs a mandatory conflict check for
  double-bookings and exact duplicates in Python before every write
  ([tools/caldav.py:385](tools/caldav.py#L385)) **and nothing else**. A 4am park visit is written
  silently.
  **Why it cannot be a rule, which is the whole difficulty.** 4am is wrong for the park and right
  for a Heathrow drop-off — Mike has done exactly that, and the machine log carries the correction
  where the system mis-read one. The signal is the *mismatch* between time, activity and his
  patterns, not the hour. So this is judgement, and today nothing is asked to exercise it: the
  impossible case belongs in code, the implausible case can only be the model, and neither is
  deliberate.
  **Where it must be scoped, not built blind.** A confirmation on every unusual-looking entry is
  worse than none — he flies at odd hours and rucks before dawn, so a system that queries every
  early time teaches him to dismiss it. **The bar is a single question, once, on a genuine
  mismatch.** Same constraint as `[DB-0818-08]`, and the two should be designed together: a
  confidence tier on a captured value is what makes "are you sure?" answerable rather than
  reflexive. Also a live instance of `[DB-0810-11]` — where code replaces model judgement.
  @kind: feature
  *raised by Mike 2026-08-18 from a passing test — he asked what the test would have missed, which
  is the finding*

- **[DB-0818-04] Ask about a Southeastern or Greenwich-line train and there is nothing to answer
  with.** No National Rail source was ever built. TfL works — tube, DLR, Elizabeth, Overground —
  which is why transit reads as operational. The one `"national rail"` alias in
  [tools/tfl_status.py](tools/tfl_status.py) maps to TfL's roll-up *mode* status, so operators and
  stations resolve to nothing and the question falls through to web search: on 2026-08-16 that ran
  two searches, returned zero sources, and **the user got a confident answer resting on nothing.**
  **Not a fix to `get_tfl_status`** — that file covers Greater London by design. This is a second
  backend (National Rail Darwin / Rail Data Marketplace) and the first transit source here needing an
  API key, so quota and key storage are part of the build.
  @kind: feature
  *filed 2026-08-18*

- **[DB-0818-05] The tool asks which Bill, then asks again about the same Bill.** Family and close
  friends resolve on frequency alone; the hard case is sparse — *"Bill Thompson from work"*, *"Bill
  the plumber"*, *"my friend William"* — four people, one spoken name, a shared surname inside the
  set. **✅ The dangerous half is fixed (2026-08-18):** the tool no longer picks one of four and
  writes to him; it refuses, offers what distinguishes them, and asks
  ([tests/test_contact_disambiguation.py](tests/test_contact_disambiguation.py)).
  **What remains is not to stop it asking** — asking is a legitimate answer and it does this well
  unprompted. It is to stop it asking **again** about someone already disambiguated, which needs
  somewhere to store the resolution and a distinguishing handle (relationship, role, employer) to ask
  *with*. **Related but opposed to `[DB-0815-07]`:** that is one person becoming several records,
  this is several people collapsing into one, and a fix aimed at either can worsen the other.
  @kind: feature
  *raised by Mike 2026-08-18*

- **[DB-0818-06] 24 of Mike's 59 stored "facts" are not facts about him.** The **writers are
  half-fixed, the store is not.** `write_wisdom`'s schema and `synthesizer.md` now separate an
  intention from a habit — a live run caught the Synthesizer writing *"wants to change breakfast"* as
  a standing fact twice in two turns, and the next run kept the observed pattern and dropped the
  intention. **The existing bad entries remain**, including intention-shaped ones written before the
  fix (`dietary_analysis_interest`, `lunch_options`).
  **Why a user notices:** eight are **interaction preferences sitting where behaviour rules cannot
  reach them** (`communication_style_preference`, `reduced_prompting_preference`,
  `avoid_travel_assumptions`, five more). A preference stored as a fact is retrieved only if
  something thinks to look it up; a preference in the persona file is in every prompt. Also
  `language_preference` duplicates `profile.yaml`'s real `output_language` field — two homes for one
  setting, and the copy can drift from the one the code reads.
  **The rest:** three tool defects filed against the user, two recurring obligations that belong in
  `open_obligation`, two near-duplicate pairs, one dated June observation, one content-free entry.
  **Do not bulk-move.** Persona data is VM-owned and each class needs a different destination:
  `merge_wisdom_entries` for duplicates (archive-on-merge), `write_persona` for the preferences, plain
  deletion for the tool defects. Per-entry assignment: `scripts/migrate_wisdom_schema.py` KEY_MAP.
  @kind: chore
  *found 2026-08-15 by reading all 59 live entries during the schema migration (`a35acfa`), which
  reports them and deliberately moves nothing · triaged out of `## Inbox` 2026-08-18*

- **[DB-0808-11] A scheduled job with notifications on would push at 3am.** `fire_function` runs no
  gate stack — `days`, `respect_quiet_hours` and the activity gate are ignored for every function
  job. `daily_travel_check` is pinned to 06:45 purely to work around it. Fix by extracting the gate
  stack so both job kinds run it.
  @kind: bug
  *filed 2026-08-08*

- **[DB-0803-05] A dead server shows the browser's error page instead of the app.** `sw.js`
  registers no `fetch` handler and `/` is served `no-store`, so there is no offline shell. Small, but
  a service-worker cache is sticky and hard to recover from if it is wrong — build it with a
  dedicated `offline.html` and a navigation-failure fallback, not by caching `/`.
  @kind: bug
  *filed 2026-08-03*

- **[DB-0808-06] A flagged clinical thread can never be marked resolved.** `resolved` exists and
  nothing can legitimately set it, so every tier-2 thread is permanent. **The failure direction is
  the safe one — do not fix by relaxing the refusal.** It needs a real administrative-close path,
  tied to an escalation mechanism that does not exist yet.
  @kind: feature
  *filed 2026-08-08*

- **[DB-0808-14] A missed statin and a missed anti-psychotic rank the same.** `_thread_tier()` reads
  only the flag string, so nothing distinguishes a psychiatric medication when deciding urgency. Fix:
  `psychiatric: true` on `medication_profile` entries, read by `_thread_tier()`. **Small but not
  cheap to confirm** — clinical tiering has named hard-fail criteria (`ROADMAP.md` § 0 clause 8), so
  the change owes an A4 re-run.
  @kind: feature
  *filed 2026-08-08*

- **[DB-0815-02] Speaking a language other than English does not work.** Speech **out** is built and
  shipped (`bg` → `bg-BG-KalinaNeural` via edge-tts, Kokoro has no Bulgarian model). Speech **in** is
  blocked with **no viable option**: `base.en` cannot emit Cyrillic at all; multilingual `base` gets
  the right script at **46.4% WER**; `small` gets 27.6% at an RTF of 0.967, leaving no queueing
  headroom on the 2-vCPU single-worker pool and regressing English 0.247 → 0.767.
  **Held indefinitely by Mike's decision** — revisit on a materially better local multilingual STT
  model or a hardware change, **not on a schedule**. Benchmark on the VM, never the Mac: an M-series
  laptop makes an unaffordable model look fine. Numbers: `tests/stt_bench_2026-08-15.json`.
  @kind: feature
  @waiting: a materially better local multilingual STT model, or different hardware
  *filed 2026-08-15 by Mike, low priority · benchmarked and rejected the same day*

- **[DB-0809-08] Nothing measures the opportunities the tool missed.** Every other troubleshooting
  category leaves a trace; this one is an **absence**, so no amount of richer tracing recovers it —
  it needs a method, not more logging. Recommended shape: a reason code on the `·` feedback dot, plus
  detecting `open_threads` that go quiet unresolved.
  @kind: feature
  *filed 2026-08-09*

- **[DB-0804-02] Security hardening remainder.** B4's five degradation paths, B2's confused-deputy
  regression test, and Wave 2 (B1b, B3) gated on Track E. Full scope in `ROADMAP.md` § Track B.
  **The half B4 under-specifies is the wording, and Mike asked for it directly (2026-08-18):** on
  failure the user should be told *"I can't do that now because xyz"*, not shown an error. The
  constraint that makes it hard is `CLAUDE.md` § Discretion — the message explains the *consequence*
  without revealing that a specialist was called or that an agent exists. *"I can't reach your
  calendar right now"* is allowed; anything naming the mechanism is not. Write the copy against real
  failures in `/monitor/model_errors`, one of which is already a live instance
  (`research_agent` returning `NoneType object is not iterable` — the user got nothing, not a reason).
  @kind: feature
  *filed 2026-08-04 · the refusal-wording half raised by Mike 2026-08-18 and folded in here, because
  it sat inside Track B reading as security hardening where nobody would look for it*

- **[DB-0815-13] Semantic retrieval *within* a knowledge domain.** `read_wisdom` returns a whole
  domain capped at 15 entries, which is correct while domains are small. **The cap being hit is the
  trigger** — at that point the choice is subdivide or retrieve, and retrieval is better because it
  matches on meaning rather than on the filer's guess about which sub-domain a fact belonged to.
  **Two load-bearing constraints, neither obvious from the code:** wisdom gets its **own FAISS
  namespace** (`knowledge.faiss`), never the log index — `core/memory.py` has no delete or update
  path, so a revised standing fact would leave both versions retrievable and ranked against each
  other, and revision semantics are the whole reason wisdom is not in the log index already. And it
  must route through `core/memory.py`'s cached `_get_model()` singleton, never instantiate
  `SentenceTransformer` inline (~80MB per call — the mistake `13134bc` just removed).
  @kind: feature
  @waiting: a domain read hits the 15-entry cap in real use
  *filed 2026-08-15 at Mike's explicit request, because it existed only in a plan narrative*

- **[DB-0808-09] Specialists take more internal turns than expected.** Coordinator is 1 (measured
  twice); `logistics` is 8; the rest are unmeasured. **Measure first, then diagnose from traces, then
  fix** — the previous version of this item rested on a measurement that was wrong. Slimming
  `coordinator.md` is a separate argument and must watch the **4,096-token Vertex cache floor**.
  @kind: chore
  *filed 2026-08-08*

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

*(swept 2026-08-18 by the clearing session — **91 → 49 entries, and the three `⚠` are gone.** Every
deletion is an entry whose signal was promoted or whose cause is fixed, which is what the rule at
the top of this section requires and what nobody had been doing. The pointers, so nothing is lost:
the Southeastern miss → `[DB-0818-04]`; Bulgarian STT and multi-language transcription →
`[DB-0815-02]`, held; ticket-based mailbox → `[DB-0814-03]`; `research_agent` returning blank →
`[DB-0804-02]`, where it is now the worked example for the refusal wording; all four tool denials →
`[DB-0810-03]`; text doubling → `[DB-0810-01]`, fixed `fd273bf`; the calendar-implies-completion
cluster → `daily_calendar_reconcile`, built; Eva/Iva → `[DB-0815-07]`, merged; the eleven-entry
check-in-brevity cluster → resolved 2026-08-15 by the evening-ritual move.*
*
**The three `⚠` deserve their own line, because all three were wrong in the same way.** Each was
triaged into `## Inbox` on 2026-08-15 as a repeat-count-cleared item; each was in fact **a single
event whose `×N` was a pre-fix chain length**; and each was **older than the code that addressed
it** — the email-transcription guard shipped 08-08 against 08-02 evidence, and the due-date sort
that plausibly dropped the Thursday deadline was fixed `fd273bf` on 08-18 against 08-11 evidence.
That is the third time an item's own description has argued persuasively for the wrong decision.
**Check the count's date and the evidence's date before promoting anything from here.**)*

- **[user corrected a prior turn]** CLARIFICATION_NEEDED:  
  `2026-08-18T18:26:12.726184Z`

- **[user corrected a prior turn]** User corrected spelling of contact name from 'Kathaleen' to 'Kathleen'.  ×2  
  `2026-08-18T16:18:04.822974Z`

- **[answered without retrieving anything]** Answered with nothing retrieved — 2 search(es) ran but returned no sources. Query: Check live status of the Southeastern Line into London Bridge. Are there any current delays or disruptions?  
  `2026-08-18T15:48:28.097541Z`

- **[already applied by the tool]** Updated Interaction Preferences to formalize the rule: Open sessions with the most time-sensitive commitment, overdue follow-up, or unresolved thread, naming it specifically. If genuinely nothing is outstanding, keep it to one line and ask what is on.  
  `2026-08-18T09:17:27.961459Z`

- **[user corrected a prior turn]** User corrected transit route to Transport Museum, explicitly excluding Jubilee and Piccadilly lines which were previously suggested.  ×2  
  `2026-08-16T08:06:21.241217Z`

- **[user corrected a prior turn]** User corrected the previous exercise log, stating the run was only a test and requested its removal.  ×2  
  `2026-08-15T11:13:42.274343Z`

- **[needs building]** Fix email dispatch silent failure: system confirms send to the user but the message does not reach the user's provider. Investigate why the tool is returning success without actual handoff.  
  `2026-08-10T17:10:55.511151Z`

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

- **[user corrected a prior turn]** User previously confirmed Rowan transfer was handled, but system asked for details again.  
  `2026-08-07T16:22:17.434741Z`

- **[user corrected a prior turn]** The system incorrectly flagged the Rowan payroll transfer as 'pending' despite the user having previously provided this information.  
  `2026-08-07T16:21:48.444766Z`

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

- **[user corrected a prior turn]** Corrected previous transit concern by noting multiple rail options exist for Heathrow.  
  `2026-08-04T14:41:57.409553Z`

- **[user corrected a prior turn]** User corrected system for failing to proactively research venue details (address, menu, hours) when a new pub meeting was scheduled.  
  `2026-08-04T13:58:03.975204Z`

- **[needs building]** User reported that the email permission prompt is not appearing (blocking testing) and requested the ability to read live Google Contacts. Both added to backlog.  
  `2026-08-04T13:51:08.510189Z`

- **[needs building]** Implement email permission prompt bubble for user approval before sending outbound emails, and enable Google Contacts live sync/read capability.  
  `2026-08-04T12:49:26.633029Z`

- **[needs building]** 1) The email approval permission prompt is failing to render in the user's app interface. 2) The system needs a tool to read live Google Contacts directly; currently it only checks internal profile records.  
  `2026-08-04T12:42:35.495275Z`

- **[user corrected a prior turn]** User opted to close the CalDAV integration thread.  
  `2026-08-04T12:37:18.994165Z`

- **[user corrected a prior turn]** User explicitly corrected system's read of 'low energy' trend, stating they have natural momentum. System over-extrapolated from isolated log entries about sleep and fatigue.  
  `2026-08-04T12:20:02.780437Z`

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
