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

- **[instruction change]** Silence 'nothing found' reports for scheduled inbox checks. The system should only notify the user when new actionable mail arrives that requires their triage. Specifically, stop surfacing that pending emails (like the Prudential follow-up) have not arrived.  
  `2026-08-12T08:27:42.379965Z`

- **[needs building]** Stop assuming passed calendar events are completed. Implement a reconciliation loop to check back on scheduled blocks and actively alert/push the user in the right direction based on calendar intent versus actual reality.  
  `2026-08-12T08:25:16.368492Z`

- **[needs building]** Bug fix: Evening close scheduler fired 3 repetitive messages; restrict follow-up prompts to a single line. Feature request: Build a mechanism to automatically age out stale state/context (like 'post-travel recovery' lingering for two weeks) to keep live context relevant.  
  `2026-08-12T08:23:28.940968Z`

- **[needs building]** User requested stopping the read-back of triaged emails (applied to persona) and requested implementing a ticket-based system for managing the mailbox more effectively (needs building).  
  `2026-08-11T08:36:03.236643Z`

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

- **1. [DB-0810-13] Specialists report actions they never took, and the Synthesizer relays it to
  Mike as fact.** Three instances on 2026-08-10, one of them a real business email. **Email:** he
  asked for a test message to Kathaleen sent to himself; the system said it had scheduled it for
  Thursday, then that it had moved the send up, then *"That's sent."* Trace `b095aa33` shows
  `relationships` called only `search_contacts`, `logistics` only `list_obligations`, and the
  **Synthesizer made zero tool calls**. `send_email` appears in no trace; three days of journal
  contain no SMTP line. **Calendar:** 15:11:45 `ROUTING_MISS | logistics` — *"received scheduling
  directives but only returned a log write confirmation instead of taking the calendar actions."*
  **Invented capability:** scheduled sending does not exist — `send_email` has no `send_at` and
  nothing wires a scheduler job to a pending draft, so the "Thursday, August 13th" was fabricated
  two turns before the false confirmation. **Cause, recorded by the system 90 minutes earlier and
  never read:** 16:30:58 `ROUTING_MISS | relationships` — *"failed to send an email to the
  explicitly provided address because it attempted a CRM lookup for the user."* The specialist
  aborted on the lookup and returned; nothing checked that the action happened. **Do not scope
  this to `send_email`** — Mike's call was to treat the class. Two halves: the specialists must
  not report success for an unexecuted action, and the Synthesizer must not assert completion it
  cannot evidence. Note seq 033 refers to an earlier Prudential email with the same symptom, so
  this has fired at least twice. Also note `logistics` calls `send_email` without holding the
  grant (only `relationships` has it) and the dispatcher runs it anyway — enforcing allowlists
  would break email outright; see `[DB-0810-03]`.
  *filed 2026-08-10 by Mike, via a bug report the system wrote incorrectly against itself ·
  verified against traces, journal and conversations the same night · Mike ranked it Now #1*

- **2. [DB-0810-09] 158 quality events have been written and never read — `USER_CORRECTION`
  (139), `ROUTING_MISS` (12), `CALENDAR_DUPLICATE` (7).** `tools/logger.py`'s
  `write_quality_event` appends to `data/personas/{p}/logs/quality_events.json`;
  `scripts/sync_dev_backlog.py` reads it through a hardcoded `WANTED = USER_TYPES |
  MACHINE_TYPES`. Anything not on that list is silently discarded. `USER_CORRECTION` — the user
  telling the system it got something wrong, and by volume the largest signal in the file — has
  **never once** reached this backlog, despite `write_quality_event`'s own docstring naming it a
  canonical type. **Do not fix with a one-line allowlist edit**; that was attempted 2026-08-10
  and correctly stopped. Three reasons it is wrong: (a) `ed92acf` restructured this file into
  Now/Later/Machine log specifically to separate machine noise from user requests, and dumping
  139 corrections into the Inbox defeats that — the right home may be a digest or a new section,
  not `MACHINE_TYPES`; (b) `CALENDAR_DUPLICATE` needs a stable signature keyed on the event-uid
  pair before it is collected, because `signature()`'s prose fallback at
  `SIMILARITY_THRESHOLD = 0.15` will collapse distinct duplicate pairs into one `×N` entry, the
  detail strings being mostly shared boilerplate (`DENIAL_RE` is the precedent to copy);
  (c) `ROUTING_MISS` may be legacy — grep the emitters before deciding. **The actual deliverable
  is structural:** nothing reconciles emitters against the consumer, so every future audit
  inherits this by default. Options — a shared registry both sides import, a startup
  reconciliation warning, or a test asserting every emitted `event_type` is either collected or
  explicitly listed as intentionally dropped. Also: `data/personas/mike/logs/.calendar_dedup_seen`
  holds all 7 calendar findings, so they stay suppressed until it is cleared — confirm before
  deleting a ledger on the VM. Those 7 are unreviewed and likely include the original Jonas
  triplication.
  **A sixth collected type was added 2026-08-10: `MODEL_CALL_FAILED`**, emitted by
  `_log_api_failure()`. One more entry the structural fix must absorb — *not* a precedent for the
  allowlist edit this item forbids: it was new, so both sides shipped in one commit, and it arrives
  with the stable key reason (b) demands, ~5/fortnight volume, and no legacy question. When the
  registry lands it registers there and its `MACHINE_TYPES` line comes out.
  **PREREQUISITE, found 2026-08-10 — fix before building the consumer: 20 of 28 `USER_CORRECTION`
  events that day carry `detail: None`.** The largest signal in the file is ~70% empty, so a
  consumer built against it now would satisfy this item and surface nothing. Fix the emitter first.
  **What this item is worth, concretely:** on 2026-08-10 a `ROUTING_MISS` at 16:30:58 recorded the
  exact cause of `[DB-0810-13]` — the system's worst live failure that day — 90 minutes before the
  model guessed at it, wrongly, in front of Mike. The diagnosis was on disk and nothing read it.
  *filed 2026-08-10 by Mike via dev session · counts re-read live off the VM 2026-08-10 ·
  full reasoning in `archive/PROJECT_LOG.md` § 2026-08-10 (Calendar conflict detection) and
  § 2026-08-10, last*

- **3. [DB-0810-12] Vertex rejects a tool-call turn for a missing `thought_signature` and the
  exchange is lost — five times 08-04→08-09, plus uncounted web-app hits.** *(Title corrected
  2026-08-10: only **one** of the five was `run_subagent`; three were `write_quality_event`, one
  `write_persona` — positions 12, 12, 12, 12, 14. Reading it as a `run_subagent` fault narrows the
  search wrongly.)* Mike sees a raw SDK 400 and the message is never recorded, on both apps.
  **Observability shipped (`8ae1ff9`); the fix did not. Verified 2026-08-10: no occurrence since —
  so the `loop=`/`msgs=` fields it was built to produce have not fired, and the hold stands.**
  *Do not act until a post-`8ae1ff9` occurrence is in hand*; the first diagnosis without them was
  wrong. Two candidates, both held deliberately. **(a) The compat round-trip** — `_openai_compat_loop`
  has the tc0-only workaround, yet *"position 12"* matches `system(0) + 10 history + user(11) +
  assistant(12)` exactly, so the signature is likely lost re-serialising the returned
  `ChatCompletionMessage` into `messages` rather than never issued. Unproven, and at ~5 firings a
  fortnight a guess would pass every test you could run. **(b) `_run_gemini_native_loop` has no
  workaround at all** — real but masked, since `run_session_gemini_cached`'s `except Exception`
  falls back to compat. **Porting the compat version verbatim would be a regression**: it runs only
  `tc0` and re-requests the rest, turning that loop's parallel `ThreadPoolExecutor` dispatch into N
  sequential turns on a path already logging `cumulative_input=60744`. Guard it to fire only when
  parts are genuinely unsigned. **Re-derive from the log line, not from this description.**
  **UNBLOCKED 2026-08-13 — four post-`8ae1ff9` occurrences are in hand, and they answer the
  question the observability commit was built to answer.** All four: `write_quality_event`,
  **position 12**, agent `synthesizer` on `gemini-3.1-pro-preview`. Attribution is
  **`loop=openai_compat_stream`** — so it is **(a), the compat family, not (b) the native loop**,
  which can now be de-prioritised. Two refinements the item did not have:
  **(i) It is the *streaming* variant `_openai_compat_stream`, not `_openai_compat_loop`.** The
  cause is upstream of re-serialisation: **stream deltas do not carry `thought_signature` at all**
  (the function's own comment says so), so a message reconstructed from deltas is unsigned by
  construction. There is already a mitigation — replay the turn blocking to obtain a real signed
  Vertex message — so the bug is in when that mitigation does *not* apply.
  **(ii) The label is bare `loop=openai_compat_stream`, never `openai_compat_stream:replay[...]`.**
  That distinction was built in deliberately, and it rules the replay out: the 400 hits the *main
  stream call*, meaning an unsigned assistant message from an **earlier** turn is already sitting
  in `messages`. **Leading hypothesis, not proven:** the `else` branch where the blocking replay
  returns no tool calls falls back to the delta-reconstructed message with no signature — the one
  path that writes an unsigned message — and the next stream request 400s. Its own comment calls
  that divergence "rare", which matches ~4/fortnight. **Verify by instrumenting that branch before
  fixing it**; do not assume, the first two diagnoses here were both wrong.
  *filed 2026-08-10 · **unblocked 2026-08-13**, occurrences and loop attribution read live off the
  VM · full reasoning in `archive/PROJECT_LOG.md` § 2026-08-10, later still*
- **4. [DB-0809-02] Do proactive sessions actually stay focused? — mechanism fixed and deployed;
  the guidance half is unproven.** The original premise was wrong: the openings were already
  1–2 sentences, and the "restatements" were the Synthesizer reading its *own* scheduler prompt as
  Mike's voice. Fixed in `82d394b` (deployed) — `_frame_proactive()` labels scheduler input as a
  directive in both pipeline copies, and the repeated-instruction protocol now requires the *user*
  to have repeated it. A ≤2-sentence cap was **rejected**; focus is the target, length only its
  symptom, so `config/agents/synthesizer.md` § Scheduled session conduct carries guidance instead.
  **Evidence corrected 2026-08-10 — this entry previously claimed "zero quality events of any kind
  logged all day", which is false: 38 fired that day** (24 `USER_CORRECTION`, 7 `FEATURE_REQUEST`,
  4 `ROUTING_MISS`, 3 `TOOL_DENIED`). The events file keys on **`timestamp`, not `ts`**; a read
  against `ts` returns nothing and looks like a clean day — this sweep made the same misread before
  catching it. The narrow conclusion survives: **no `INSTRUCTION_CHANGE_REQUEST` fired**, which is
  what the old bug produced every time, and both 07:20/07:30 firings recorded `is_proactive: true`.
  **What remains: read a week of traces.** Still day 1 of 7. Do not re-word anything before then.
  *filed 2026-08-09 · rewritten 2026-08-09 after measurement inverted it · **evidence corrected
  2026-08-10** — see `archive/PROJECT_LOG.md` § 2026-08-10, last*

- **5. [DB-0809-21] Three of four verification steps done and passed; one is genuinely time-gated.**
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

- **6. [DB-0810-05] The tone-profile pipeline has never touched a real mailbox.** Built and
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

- **7. [DB-0810-15] Voice transcription is English-only in two places, so Bulgarian cannot work.**
  Mike tested it live (seq 031, *"I'm wondering if you can understand me if I speak in Bulgaria"*)
  and asked for multi-language support or a toggle. **Not a config flip — it is blocked twice:**
  (1) [core/voice_pipeline.py:177](core/voice_pipeline.py#L177) passes `language="en"` hardcoded;
  (2) [core/voice_pipeline.py:49](core/voice_pipeline.py#L49) loads `base.en`, an **English-only
  model** that cannot transcribe Bulgarian at any setting. Multilingual requires `base`, which
  reopens the sizing constraint documented at [core/voice_pipeline.py:31](core/voice_pipeline.py#L31):
  STT runs on a **single-worker pool on 2 vCPU**, and `small.en` was already measured and rejected
  at RTF 2.23 (transcribes slower than audio arrives, so a second concurrent request queues).
  **Benchmark `base` on the VM before choosing** — `python3 tests/bench_whisper_stt.py`, run there,
  not on the Mac. Then decide auto-detect vs. an explicit UI toggle; auto-detect costs accuracy on
  short utterances, which is most of what voice sends.
  *filed 2026-08-10 by Mike, live during feature testing · both blockers verified in code same day*

- **8. [DB-0810-17] "How many contacts do we have?" — and the answer was more wrong than it
  looked.** At seq 009 Mike asked for a route *and* a CRM contact count; the system replied it had
  *"no connection to your external CRM to pull a contact count"*. **That is only half true and it
  should not have declined.** Metatron has its own contact store — `list_contacts`,
  `search_contacts`, `read_contact`, `write_contact` in [tools/crm.py](tools/crm.py) — and
  `relationships` is **already granted all of them**. It could have answered the count from data it
  holds. So there are two separable pieces, and the cheap one is not a build:
  **(a) Answer from the existing store** — instruction/routing only, no new code. A contact-count
  question should reach `relationships` and be answered from `list_contacts`.
  **(b) An external CRM bridge** — a genuine integration, and the one Mike means by "should be
  built". Blocked on a decision this entry cannot make for him: *which* CRM, and whether contacts
  sync in, out, or both. Sensitive-tier either way.
  *filed 2026-08-10 by Mike · **(a) verified present and granted 2026-08-10** — the capability
  exists and went unused, which makes this partly the same class as `[DB-0810-13]`*

## Later

Real, not prioritised. One or two lines each — detail lives in the code, the log, or
`archive/backlog_closed_2026-08.md`.

**Two standing rules, both Mike's (2026-08-10):** an item promotes to `## Now` once its error
has been **recorded three times** (the ×3 threshold the machine log uses — count before
promoting); and **`Now` is cleared before `Later` is started**, so this is not a parallel track
to pick from when a `Now` item is time-gated.

**Safety and test gaps**
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
  `CLAUDE.md` § Security Architecture — correct the lists, verify, *then* enforce.
  *filed 2026-08-10 by the machine-log sweep · **(b) closed 2026-08-10**, (c) added the same day
  from the guard's first full run · two denials added by the 08-10 `deep` sweep*
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
- **[DB-0810-06]** Every context-file ceiling is measured in lines, and lines stopped tracking the
  cost. `SESSION.md` hit 200/200 with **5.6 KB of its 17.9 KB on five lines** — rows that grew
  **wide, not numerous**, so a line ceiling could not see them. Instance fixed (`2e3e6e4`); the
  metric is still line-based everywhere it is stated (`CLAUDE.md` § *Which File Holds What* plus
  each file's footer). **Check before acting:** whether a byte/token measure earns its complexity,
  or whether the one-line-per-row rule already added is sufficient. *filed 2026-08-10*
- **[DB-0805-05]** **A session cannot tell its own edits from a parallel window's** — the git
  collisions and the `/archive` dirty-check are one cause, not two. `git add <file>` does **not**
  protect you: the collision is line-granular inside a file the committer legitimately owns
  (2026-08-08). `/archive` step 0 flags dirty files but cannot say whose — advisory, not
  protective, and **do not remove it**; a prompt to look beats no prompt. **Fix:** a
  start-of-session commit to diff against, or record touched files as the session goes.
  *merged 2026-08-10 (absorbed `[DB-0809-17]`) · **×3, the bar is met** — recurred twice more on
  08-10, once nearly reusing an id another window had taken minutes earlier · `/archive` step 5
  currently depends on this being unsolved*
- **[DB-0809-11]** Docs record values the system changes underneath them and nothing checks.
  Mitigation in force (don't write down short-half-life values); the stronger fix is a smoke
  script running CLAUDE.md's executable claims. `deploy.sh`'s HEAD assertion is the model.
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

- **[already applied by the tool]** Updated interaction preferences: evening check-ins (13 Franklin virtues + 1 food log) will now be delivered as a single consolidated message rather than item-by-item, allowing the user to highlight only the exceptions.  
  `2026-08-12T08:21:14.706181Z`

- ⚠ **[same rule in two places]** This preference may already be covered by a rule that applies to everyone. Preference: config/personas/mike.md:14 — Check inbox every six hours in the background. Candidate rule(s) it may restate: (1.00) [wording only] config/personas/mike/scheduler.yaml:43 — Check in. (1.00) [wording only] config/templates/scheduler.yaml:40 — Check in. Candidates are ranked by wording overlap, which is weak at this scale — the flagged preference is the reliable part, the partner is a starting point. If the preference says nothing the shared rule does not, delete it. If it is a genuine personal refinement, keep it and reword it so the difference is all it states.  ×4  
  `2026-08-11T04:30:15.629388Z`

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
