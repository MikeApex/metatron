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
*(empty — triaged 2026-08-27 by `/backlog deep`; evidence in `archive/backlog_closed_2026-08.md` § Closed 2026-08-27)*

- **[needs building]** Fix email parser so it does not strip forwarding context. Forwarded emails currently lose the original recipient data, leading to incorrect assumptions about who the email was intended for.  
  `2026-08-28T16:43:27.304606Z`

- **[needs building]** Email intake/parser needs updating to preserve and pass forwarding metadata (e.g., forwarded from secondary accounts), as dropping it caused the system to misinterpret a family member's email as a misdirected message.  
  `2026-08-28T15:24:22.504583Z`

- **[needs building]** Logistics check should not report a route as 'well covered' or complete if the specific geographical locations of the user's scheduled errands are not yet known or recorded.  
  `2026-08-28T11:10:10.476712Z`

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

- **1. [DB-0820-01] The spend caps are temporarily too high — bring them back down in
  September.** Raised 2026-08-20 from **$100/$175 to $150/$250** (soft stops the VM, hard
  disables billing). Mike's decision, and **explicitly temporary**: the real budget did not
  change, the caps were lifted to clear a cost *defect* — Vertex context-cache storage, ~$100/mo
  (`archive/plans/vertex_cache_cost_control_2026-08-20_plan.md`). **When the September cycle
  resets, put them back**, to $100/$175 unless a reconciliation says otherwise.
  **Do not lower the soft cap alone.** It was nearly set to $150 against a $175 hard cap, leaving
  $25 — and the hard cap is an outage (26h VPC freeze, 2026-07-30), has fired *below* its own
  threshold once, and sits behind spend figures that lag by hours. **Keep ~$100 between the tiers,
  whatever the absolute numbers.** Values and full reasoning:
  [docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md) § Billing protection — read them there, never
  from a script comment (`metatron-vm-override.sh` was stale for months).
  *Checked 2026-08-20: both budgets confirmed live at 150/250 via `gcloud billing budgets list`.*
  *Evidence in, 2026-08-27: the `[DB-0822-01]` reconcile passed on five consecutive post-deploy
  days (billed ÷ estimated 1.02×–1.17×, bill running ~$1.8–2.0/day) — the reconciliation supports
  reverting to $100/$175 at the September reset; nothing argues otherwise.*
  `due: 2026-09-01`
  @kind: chore
  *filed 2026-08-20 by Mike*

### Green/Amber — buildable without a prompt

*All three are code fixes in `core/` or `tools/`. Grouped so an automated run can take the block.
Each is a defect measured in the 2026-08-21 traces, not a proposal.*

- **2. [DB-0822-05] The journal records days you never spoke.** The Diarist is not scheduled — the
  **Coordinator dispatches it** as a fire-and-forget specialist
  ([core/orchestrator.py:4381](core/orchestrator.py#L4381)). On 08-21 it fired on 10 of 23 runs,
  and **in 9 of them Mike said nothing at all** — it journalled the assistant's own monologue.
  Worse, at 10:24 the Synthesizer handed it `"Original user message: 'Good morning. Open with
  whatever is most time-sensitive today…'"` — that is the **scheduler's** prompt text, filed as
  Mike's speech. The rule that a scheduler prompt is not user speech was added 2026-08-09
  (`82d394b`) and **has regressed**. Cost is irrelevant (24 calls, $0.017); the damage is a
  journal of things the user never said, which later runs then read back as fact — the same
  mechanism as `[DB-0822-06]`.
  **Fix in code, not in an instruction:** refuse the dispatch when the session carries no real
  user turn. An agent-file rule is what already failed.
  *Measured 2026-08-21 from `data/personas/mike/traces/2026-08-21.jsonl`, read live off the VM.*
  *Re-verified 2026-08-27: the cited dispatch line drifted — the fire-and-forget dispatch is now
  [core/orchestrator.py:4660](core/orchestrator.py#L4660); still no guard.*
  **✅ Built 2026-08-27** (`e6bde3d`, merged): `has_real_user_turn()` gates the Diarist dispatch —
  a scheduler prompt is not speech; a user who answers a check-in still journals.
  `tests/test_diarist_user_turn_gate.py`.
  @kind: bug
  @waiting: the owed deploy, then one scheduler-only day whose journal stays empty and one
  answered check-in that still journals — both halves, or the gate is the same bug reversed
  *filed 2026-08-22 by Mike · built 2026-08-27 by the session-hygiene attack worker*

- **3. [DB-0822-06] It tells Mike his own training day, and got it wrong four ways in one day.**
  Across 08-21 the same hiatus was called *five-day, five-day, day three, day three, **day four**,
  five-day, day three, day three*. **Root cause is a derived count written into a log and re-read
  as fact:** `physical_health` wrote `"Day 3 of 5-day exercise hiatus"` into the health log, and
  later runs read the stored number instead of recomputing it from the dates.
  **Same class, same fix:** the *Metatron sprint* surfaced in 5 of 9 runs days after it ended —
  written state carried forward with no age-out. Mike: *"Metatron sprint aged out days ago. It
  shouldn't be a topic of conversation."*
  **Fix:** compute derived counts at read time and never store them; give log-carried topics an
  age-out. Both are `tools/` + `core/`, no agent file involved.
  *Measured 2026-08-21; the offending write is visible in the 10:24 trace's `write_log` args.*
  *Fourth instance 2026-08-27: the 10:00 anticipation run told Mike the Teams link was "still
  missing" three hours after the 07:14 run declared it resolved — same carried-state mechanism.*
  **Half built 2026-08-27** (`cbd5ca3`, merged): carried state now shows its age — open threads
  read "(logged 9 days ago)", log lines carry age beside date. Annotation, not filtering.
  `tests/test_context_age_annotation.py`. **Both remaining halves resolved 2026-08-27 (second
  attack run, merged `4cc9e3e`):** the **intraday half is built** — `write_log` now stamps each
  field's write time in a `_written_at` sidecar (additive; legacy files render unchanged, no
  migration) and today's log renders per-field with hour-granular ages
  (`tests/test_log_field_timestamps.py`, 32 checks). The **derived-count half was
  STALE-PREMISED as filed:** no code-computed count reaches a model — `expired_open_threads` is
  popped before the read (`tools/context_tracker.py:406`), and intake/obligation counts are
  computed at assembly time; the only stale counts are model-authored free text, which the
  per-field stamps now date. A code-computed "derived facts" line was considered and deliberately
  not built — revisit only if a dated count still gets misread after deploy.
  @kind: bug
  @waiting: the owed deploy, then one same-day case — a morning-resolved item not reported
  "still missing" by a later run that day
  *filed 2026-08-22 by Mike · age-out half built 2026-08-27 (session-hygiene worker) · intraday
  half built + derived-count half retired 2026-08-27 (orchestrator-context worker)*

- **4. [DB-0822-07] Two scheduled jobs fire seven minutes apart.** `companion_checkin` runs on a
  180-minute interval and landed at 07:23; `morning_brief` is fixed at 07:30. **19 model calls
  between the two**, and the 07:30 pair is what produced the false action claim now recorded in
  `[DB-0815-11]` — the later job read the earlier job's prompt as an instruction from Mike.
  **Fix:** suppress an interval job that lands within N minutes of a fixed-time job.
  `core/scheduler.py` is **Red tier** (it prompts), but the change is mechanical and self-contained
  — kept in this block deliberately, with that caveat, rather than buried in the judgement work below.
  *Measured 2026-08-21: 9 scheduled runs — companion_checkin ×5 (07:23, 10:24, 13:26, 16:27,
  19:28), morning_brief 07:30, inbox 12:24 + 18:24, evening_close 20:00.*
  @kind: bug
  *filed 2026-08-22 by Mike*

### Red — judgement work, not automatable

- **5. [DB-0822-08] Nothing is ever proposed — only reported.** The Apex migration due the 31st was
  raised in **6 of 9** scheduled runs and **not once** did anything offer to put time in the
  calendar for it. Prudential was raised in **7 of 9** — unchanged all day, waiting on Jason
  Duross, entirely outside Mike's control — and nothing ever asked *"do you want me to chase
  him?"*. Mike: *"There was no mention to SCHEDULE a time to do the Apex work, or a question about
  'Should I follow up with Prudential?'"*
  **Read this as an adherence failure, not a missing instruction** — Mike's framing is that the
  agents *"aren't acting proactively on information, even though they're instructed to do so."*
  **So open the existing proactive-anticipation section of `config/agents/synthesizer.md` and find
  out why it is not firing before writing another rule.** Adding a rule to a 12,700-token file is
  the move most likely to be wrong here — see the length→adherence finding in
  [archive/plans/synthesizer_audit_2026-08-18.md](archive/plans/synthesizer_audit_2026-08-18.md) § 5.
  **Corollary Mike named:** an item that cannot be acted on should not be raised at all; one that
  can should arrive with the action attached.
  *Re-verified 2026-08-27: the file shrank 52,397 → 41,939 bytes in the audit execution
  (`ce94dd1`) but the Proactive Anticipation section (`synthesizer.md:249–277`, "mandatory pass…
  cannot be skipped") was untouched. Since length→adherence is the named cause, **re-measure
  adherence against the post-audit file** — one scheduled-run day of traces — before any fix.*
  @kind: bug
  @session: whether to fix by instruction or by giving the Synthesizer an explicit "propose a next
  action or stay silent" gate
  *filed 2026-08-22 by Mike*

- **6. [DB-0822-09] Email is processed and then thrown away.** The 12:24 and 18:24 jobs were
  explicitly *"check the user's inbox and summarize any relevant logistics details."* `logistics`
  ran and ingested **397,216 tokens — the largest input of any agent that day** — and what reached
  Mike was one due date plus the virtue list. **The most expensive specialist by volume produced
  nothing the user saw.**
  **The shape Mike wants** (2026-08-22, verbatim intent): email should keep admin *off* his plate,
  but there must be **some** reporting — especially **interest-level items**, e.g. concerts he is
  presumably looking forward to. And beyond reporting, **a check on whether anything needs
  coordinating around them**: parking, food before or after, transit, whether other friends are
  going.
  **Two halves, deliberately one item:** the discard is a bug in what the Synthesizer surfaces; the
  coordination check is new capability in `logistics` / `recreation_hobbies`. They share a surface
  and splitting them would have each half wait on the other.
  *Re-verified 2026-08-27, and the build is cheaper than when filed: the intake queue and
  per-agent `read_intake_queue` grants already exist (disabled behind `[DB-0820-03]`'s eval gate).
  What is missing is only the Synthesizer surfacing rule and the coordination-check instruction —
  both agent-file (Red) work, unaffected by the gate.*
  @kind: feature
  *filed 2026-08-22 by Mike*

### Denied tier — Mike's own file

### Green/Amber — a second block, found after the first pass

- **7. [DB-0826-01] "Undo that merge" was read as a work project, so the undo never happened.**
  Live 2026-08-26, trace `b92ce0c3`, one minute after the contact merge that turn was plainly
  about. The Coordinator routed it to **work_vocation**, which searched memory for *"Prudential
  Apex project merge"* and *"Prudential Apex merge branch commit file"* — it resolved "merge" to
  the work project and "that" to nothing at all.
  **The tool was never the problem.** `unmerge_contacts` is granted to `relationships` in both
  routing files and documented at
  [config/agents/relationships.md:308](config/agents/relationships.md#L308). It was not called.
  Instead the Synthesizer dispatched three subagents by hand and finished by instructing
  `relationships` to *"Call `write_contact` to create a new contact for Marcus Delgado, in order
  to undo the previous merge"* — **reconstructing a record by hand, which
  `relationships.md:308` explicitly forbids** ("never reconstruct them yourself"), and which
  would have produced a new id, an empty interaction log and a silent divergence from the
  archived original.
  **The Synthesizer diagnosed this correctly and proceeded anyway.** In the same turn it wrote a
  `write_quality_event` recording that the Coordinator *"completely missed the conversational
  context"* — so the signal exists in `quality_events.json` already.
  **What this is, stated so it is not fixed as a CRM bug:** a Coordinator referent-resolution
  failure. "That merge" is a pronoun pointing at the previous turn, and the routing layer
  resolved it against work context instead. Same family as the adherence cluster
  `[DB-0822-05]`–`[DB-0822-10]`, not the contact-gate cluster.
  **Do not fix it blind** — the routing layer carries no reproduction yet, and one trace is one
  trace. A second data point is cheap: any short referring turn ("undo that", "cancel it",
  "do the other one") after a contact operation.
  **@waiting condition MET 2026-08-27** — the `[DB-0827-05]` fix recovered the discarded
  `ROUTING_MISS` history, and it holds at least three prior instances of this exact class:
  *"Read that back to me again"* resolved to Prudential scheduling instead of the previous turn's
  food data (08-18); *"previous request"* resolved to an older lunch instead of the immediately
  prior turn (08-10); *"Approved"* resolved to the wrong pending action and wrongly closed an
  obligation (08-15). Not one trace — a pattern with four data points. Workable now.
  **Probe-measured 2026-08-28 and CONFIRMED THE FIX PATH (Mike):** Flash-Lite reproduces the
  class 6/12 on the competing-referent suite; Pro sweeps it 12/12 but the flip is declined on
  latency (`[DB-0820-05]`). **This item is the default path** — fix the Coordinator, prefer
  structural referent context (`tools/turn_context.py` pattern) over instruction-only, since
  Pro's winning move was following a rule `coordinator.md` already states and Flash-Lite
  ignores. Reproduction suite exists: `tests/run_coord_model_probe.py` Suite B-hard.
  @kind: bug
  *filed 2026-08-26 at Mike's instruction, from the live trace*

- **8. [DB-0827-01] Declining a confirmation does nothing, so the prompt comes back until you
  give in and approve it.** Mike, live 2026-08-27, on the first decline anyone has ever performed:
  *"If I decline it keeps asking in a loop. In the end I approved to break the loop."*
  **There is no decline path anywhere in the system.** `POST /confirm` in `core/server.py` is
  approve-only; there is no reject endpoint, and `static/index.html` has no decline handler.
  Declining dismisses the prompt in the browser and changes nothing on the server, so the record
  stays unapproved in `pending_confirmations.json` and the app's next poll of
  `/pending-confirmations` raises it again — every cycle, until the 10-minute TTL expires it.
  **Why this is worse than a cosmetic annoyance, and the reason it is filed rather than fixed
  late in a session:** the loop's only exit is *approving the thing you just refused*. A gate whose
  cheapest escape is consent is not a gate. It inverts `tools/confirm.py`'s entire premise — that
  the user's deliberate act is what authorises an action — into a war of attrition that authorises
  by exhaustion.
  **Present since the gate shipped 2026-08-19** (`6d6d46c`), unnoticed for eight days because
  nobody had declined one: every prior test approved.
  **Shape of the fix, not a decision:** `POST /decline {token}` that removes the record through the
  same fingerprinted path `consume()` uses, a client control that calls it, and a decision on
  whether a decline should also tell the model *"the user said no"* — without that, the next turn
  can simply re-propose the same action, which is a second, quieter version of the same loop.
  **✅ Built 2026-08-27** (`0f8f528`, merged): `POST /decline` removes the record through the
  same fingerprint discipline as `consume()`; refusals retained in `declined_confirmations.json`
  (capped 200); the client leaves the card up if the server call fails rather than pretending the
  "No" landed. `tests/test_decline_path.py`, 14 checks, all failing pre-fix. **✅ Re-propose
  half built 2026-08-27** (merged `4cc9e3e`): `confirm.request()` raises no card for an action
  refused within 24h unless a genuinely new trigger occurred — the user speaking in a turn that
  began after the refusal, or an intake row arriving after it (`tools/turn_context.py`,
  thread-local, fails closed on an unbound thread). A declined-actions context block tells the
  model the answer stands; an allowed re-ask must say the user declined it before. Window
  rationale documented at `_REPROPOSE_WINDOW_SECONDS`; ledger records persist past expiry
  (count-capped, never age-capped). `tests/test_decline_reproposal_guard.py`, 21 checks.
  @kind: bug
  @waiting: the owed deploy, then one live decline that stays declined — including through the
  next scheduled run
  *filed 2026-08-27 at Mike's instruction, from his own live attempt to decline · built same day
  by the decline-path attack worker · re-propose half built 2026-08-27 by the
  orchestrator-context worker*

- **9. [DB-0827-07] The Coordinator writes empty "CLARIFICATION_NEEDED:" quality events — 33
  since 08-18, 3–5 a day, every one with no content.** Diagnosed 2026-08-27 during the deep run's
  machine-log sweep (the ⚠ ×33 signature): the Coordinator fills its `USER_CORRECTION:` template
  slot with the adjacent `CLARIFICATION_NEEDED:` label and nothing after the colon;
  `_handle_user_correction()` ([core/orchestrator.py:492](core/orchestrator.py#L492)) logs it
  because `is_null_ish()` does not catch a bare template label. Same slot-noise class as the
  "None ×90" case `[DB-0815-09]` fixed. Two costs: junk drowns the event log's session-start
  count, and if the Coordinator genuinely needed clarification those 33 times, the payload is
  lost. **Fix: extend the null-ish check to bare labels while keeping a label *with* content as
  real signal.** Machine-originated, promoted at ×33 under the ×3 rule.
  **✅ Built 2026-08-27** (`24dabae`, merged): `is_null_ish()` drops a bare ALL-CAPS label,
  keeps `CLARIFICATION_NEEDED: which Bill?` intact. `tests/test_empty_template_label_events.py`.
  @kind: bug
  @waiting: the owed deploy, then one day with no new empty-label events in the VM quality log
  *filed 2026-08-27 from the deep-run machine sweep, VM quality events read live · built same day
  by the session-hygiene attack worker*

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
  **✅ DECIDED 2026-08-19 (Mike) — build both halves, and hold the second to a test.** The two
  failures need two different mechanisms and only one of them can be enforced. **Job 1, certain:**
  record the tier, and gate overwriting of a `verified` value behind one confirmation — a Python
  `if` at the write path, closing the `Kathaleen` case outright. **Job 2, influence only:** nothing
  can mechanically detect that a sentence sounds too confident, so *every* option here is odds, not
  enforcement. **Build it by rewriting the fact, not by tagging it** — the store renders an
  `inferred` value into the prompt as *"you inferred, but have not confirmed, that…"* rather than
  `value [inferred]` plus a rule, because **a marker beside a fact is an instruction the model can
  negotiate with, and this exact pattern has already failed**: `[RETRIEVAL: NONE]` was attached to
  the Southeastern turn on 08-18 and the Synthesizer softened it instead of refusing. With the
  hedge inside the claim there is no separate rule to weigh against being helpful.
  **The test is part of the build, not a follow-up:** seed an `inferred` fact, ask a question that
  depends on it, and check the reply hedges. **If it does not, job 2 is recorded as still open** —
  the point of testing it is to avoid believing it closed. **Scope known and not claimed as
  covered:** the tiers only reach facts that travel *through the store*. A fact invented mid-turn
  and spoken without ever being written is untouched by any of them; the wire is covered by the
  zero-source guard, and the gap between the two remains.
  @kind: feature
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
  **✅ ALL DECIDED 2026-08-28 (Mike) — the list had drifted to 24 live pairs; every one ruled
  on, in six clusters. What remains is one supervised Red build pass.** *(1)* **Archive:** reads
  granted — `finance`, `learning_growth`, `physical_health`, `recreation_hobbies`,
  `work_vocation` (finance gains the naming line in its file); **writes granted only in the
  same session as a `write_archive` dedup fix** ([tools/diarist.py:110](tools/diarist.py#L110)
  has none — five new writers without it invites clutter). *(2)* **Journal: NO grants** —
  `finance`/`learning_growth`/`logistics` instruction text rewritten to route observations
  through the Diarist ("multiple entries clogging up the clarity" — Mike). *(3)* **Goals
  reads granted** (`finance`, `work_vocation`). *(4)* **agent_config granted to
  `relationships` + `recreation_hobbies`** — completes the specialist set (audited 2026-08-28:
  the other six domain specialists already hold read+write; non-domain agents correctly hold
  none). *(5)* **search_memory granted to `pattern_miner` + `recreation_hobbies`** — audited
  same day; set then complete. *(6)* **Singletons:** `coordinator`→`write_quality_event`
  granted **with a dedup condition** — the written event travels in the context package so the
  Synthesizer does not re-log it, plus a code backstop in `tools/logger.py` (same trace + same
  event type → no-op); `goals_interviewer`→`write_baseline_period` granted;
  `pattern_miner`→`write_context_tracker` granted; **`learning_growth`→`write_config` NOT
  granted** — its skill-goals line redirects to `write_agent_config` (already granted; global
  `write_config` would confirm-prompt on every streak tick). *(7)* The two logistics archive
  refusals **dropped** — the spec no longer names them; the refusals were the system working.
  *(8)* **Enforce mode stays off**; the flip is its own decision after the lists are corrected
  (re-verify the `logistics`→`send_email` state at that moment, not from this note).
  @kind: chore
  *build owed: one supervised Red pass — both routing files + the cluster-2/finance/LG
  instruction-text edits — plus the Green dedup fix and logger backstop in the same session.
  A7 check 10 unblocks when it lands.*
  *filed 2026-08-10 · guard half closed 2026-08-10 and 2026-08-18 · decisions made 2026-08-28*

- **[DB-0809-02] One unfinished ritual arrives as three or four separate messages.** Read live off
  the VM 2026-08-15: the "three repetitive evening messages" were **four different scheduled jobs**,
  each re-asking the same unanswered question. `evening_close` is a victim, not the culprit.
  **The mechanism: "raise a thing once" has no memory that a question was asked and left
  unanswered**, so every unrelated job that fires inherits the unfinished ritual from context.
  **Two prior diagnoses were confidently wrong** (narrative in `archive/backlog_closed_2026-08.md`
  § Closed 2026-08-15), which is why the third is not being picked without him. **Do not re-apply
  the ≤2-sentence cap** — rejected deliberately; focus is the target, length only its symptom.
  **Third measurement, 2026-08-21 — the mechanism is confirmed and it is worse than "three or four
  messages."** Across 9 scheduled runs: the full 13-virtue list went out **4 times**; the sleep and
  step-count question was asked in **5 runs and never once answered**, then asked again; Prudential
  appeared in **7 of 9** and Apex in **6 of 9**, both unchanged all day. **And the length runs the
  wrong way** — the runs carrying the least new information were the longest (16:27 carried nothing
  new and ran 1,778 characters; 12:24 ran 227).
  **Mike, 2026-08-22:** *"Most of these should be touched upon ONCE if at all. Runs with little
  information should be short and sweet. 'Not much new, but haven't heard from you in a few hours.
  What's up?' sort of stuff."*
  > **Flagged, because it reads like the thing this item already rejected.** The `≤2-sentence cap`
  > was rejected deliberately (above) on the grounds that *focus is the target, length only its
  > symptom*. Mike's 08-22 wording asks for brevity **conditioned on there being nothing new** —
  > which is a focus rule that produces brevity, not a cap. **Build it that way**, and do not
  > reintroduce an unconditional length limit. Confirm the reading with him before building.
  **✅ DECIDED 2026-08-28 (Mike) — reading confirmed, both halves approved; what remains is the
  build.** *(1)* The 08-22 wording is a **focus rule conditioned on nothing-new, not a length
  cap** (the rejected ≤2-sentence cap stays rejected): empty context delta since the last run →
  short check-in, brevity as a consequence. *(2)* **Asked-state memory** in code
  (`tools/context_tracker.py` territory): a question asked and unanswered is recorded; later
  jobs do not re-ask. **Pressing things may be re-raised if urgent — but not frequently and not
  every time.** *(3)* **Ritual ownership:** a scheduled job does not continue a ritual that is
  not its own — extend the proven `session_kind()` gate pattern.
  **The target behaviour, Mike's design frame (2026-08-28), which the build should aim at rather
  than mere de-duplication:** Metatron informs *what to do NOW*. Open items are worked
  opportunistically off the list, not nagged: don't remind the user to water the plants — note
  when the user is home with 5–10 free minutes before the next scheduled obligation and suggest
  it as a good use of the window; or when the user checks in asking for something to do, surface
  it if it is the highest-priority item fitting the circumstances. An unanswered question is one
  more open item on that list, not a broadcast obligation. *(Touches the anticipation pass and,
  later, `[DB-0815-12]` location — "user is home" is a circumstance signal.)*
  @kind: bug
  **✅ Code halves BUILT 2026-08-28** (`6451b51`, spinoff chat): asked-state in `context.json`
  (question text withheld from the model; re-ask caps incl. max 1/day across all jobs);
  nothing-new fingerprint stamped at run close → short-check-in directive (a condition — a
  test asserts no length cap can creep back); ritual ownership generalised to
  `*_ritual.md`-by-filename. 33/33 tests + evening gate 11/11.
  *remaining: VM deploy (rides the spinoff batch); one scheduled-run day confirms (doubles as
  `[DB-0822-08]`'s re-measure day); the Red Synthesizer line rides the email-surfacing session
  — verbatim in `archive/handoffs/2026-08-28-ritual-halves.md`*
  *filed 2026-08-09 · rewritten twice as measurement inverted it · third measurement 2026-08-21 ·
  decided 2026-08-28 · built 2026-08-28*

- **[DB-0815-11] The system recorded a preference change it appears never to have made.** A
  `SELF_APPLIED` event at `2026-08-15T13:51:39Z`: *"Switched output to Bulgarian transliteration
  (Latin alphabet)…"* — but no transliteration line exists in any persona file on the VM (Mike
  grepped). Either it wrote somewhere unexamined or it reported an action it did not take. **Honest
  caveat:** he reverted his language test the same day, so "written then reverted" cannot be
  distinguished from "never written" without a backup.
  **The second-order concern is the real one:** this was the second wrong self-applied preference in
  four days (the 08-12 check-in consolidation was the first, and he rejected it). Both were silent.
  **Resolved 2026-08-21 — a clean instance, with the ambiguity above removed.** The 10:24 run opened
  *"I have made a note to open sessions exactly that way going forward. I've logged the instruction
  change so it sticks."* **The trace for that run contains no `config_writer` call of any kind** —
  the only writes were `write_log` from three specialists. So this is **not** "wrote somewhere
  unexamined": it is a reported action that was never taken, proven by the absence of the call
  rather than by grepping for its result. It also had no user instruction behind it — it was
  reacting to the 07:30 **scheduler prompt** (see `[DB-0822-07]`, the seven-minute job collision).
  Mike, 2026-08-22: *"False action claim is unacceptable and needs to be addressed."*
  **This makes the item buildable:** cross-check claimed actions against the trace's tool calls
  before the response is emitted. `core/` — no agent file needed for the detection half.
  **✅ Detection half built 2026-08-27** (`e673330`, merged): persistence claims in the
  Synthesizer's text are cross-checked against write-family tool calls in the turn's trace; an
  unbacked claim logs a `FALSE_ACTION_CLAIM` event carrying the sentence — log-only, response
  untouched, both pipeline paths. Registered in the sync so it is collected, not discarded.
  `tests/test_false_action_claim.py`. **The @session policy half is unchanged and still the
  item's exit.**
  **A third arrived 2026-08-18 and it is the one that settles the question, because unlike the other
  two it can be checked end to end.** `SELF_APPLIED` at `09:17:27Z` wrote an Interaction Preference
  into `config/personas/mike.md:16` — *"Open sessions with the most time-sensitive commitment,
  overdue follow-up, or unresolved thread, naming it specifically…"*. **It landed, and it was
  redundant on arrival.** The next morning's rule audit (`RULE_CONFLICT`, `2026-08-19T04:30Z`) scored
  it **0.88 against `config/templates/scheduler.yaml:21`** — the *template*, so every persona already
  had the rule. So the store now has two homes for one instruction, and the personal copy states
  nothing the shared one does not.
  **What this changes about the decision.** The first two instances could each be argued away — one
  was rejected on taste, one could not be distinguished from "written then reverted". This one wrote
  a real line to a real file, unasked, that duplicates a rule already in force, and **it is the same
  class as `[DB-0818-06]`'s eight interaction preferences sitting where behaviour rules cannot reach
  them.** The rule audit's own caveat applies to the *partner*, not the flagged preference — and here
  the partner is a template, not a wording coincidence.
  **Two separable calls, and they are not the same question:** whether `write_persona` may self-apply
  at all without confirmation, and whether a self-applied preference should be checked against the
  template rules *before* it is written rather than flagged the morning after by an audit nobody
  reads. The second is buildable today and does not need the first answered.
  **✅ POLICY DECIDED 2026-08-28 (Mike) — both calls answered; what remains is the build.**
  *(1)* **Self-applied (inferred) preference writes are gated behind approval for the time
  being** — a proposal the user confirms, via the same fingerprinted `consume()` pattern
  `write_config` uses. **The gate must be toggleable**: once the inference engine around these
  preferences is strong enough, the approval mechanism may be removed entirely and inference
  permitted again — build it as a switch, not a hard-coded rule. Explicit user instructions
  remain ungated (stated, not inferred). *(2)* **Pre-write redundancy check:** before writing,
  `write_persona` checks whether a toggle/setting/rule elsewhere in the system (templates,
  `scheduler.yaml`, agent config) already covers the preference — a more appropriate home wins
  over writing a second copy of an existing rule (the 08-18 instance's exact failure).
  **Design note for later, Mike's (2026-08-28):** as users accrue, persona preferences likely
  become binaries/tags for common cases instead of free-form text — possibly worth an early look
  for communication preferences/tone. Not scoped here; recorded so it survives.
  @kind: bug
  @waiting: detection half (`e673330`) — one live `FALSE_ACTION_CLAIM` event or one clean week
  **✅ Gate BUILT 2026-08-28** (`75a91d6`, spinoff chat): inferred writes propose-and-confirm
  via `consume()`; toggle `proactive.persona.inferred_write_auto_accept` (default false, no
  tool writes the file); redundancy refusal at `NEAR_DUPLICATE` names the existing home (the
  08-18 line scores 0.857 vs the template and is refused). 19/19 tests. Two flags in
  `archive/handoffs/2026-08-28-write-persona-gate.md`: refusal applies to stated preferences
  too (deliberate reversal of warn-never-block), and `synthesizer.md` carries no `source` line
  (schema does the work; Red session may add one).
  *remaining: VM deploy (rides the spinoff batch), then the @waiting exit above*
  *filed 2026-08-15 from the machine log · third instance folded in 2026-08-21 from the `/backlog
  deep` machine-log sweep, with the `RULE_CONFLICT` that confirms it · policy decided 2026-08-28*

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
  **This item is now the anchor for the code-dominant rebuild notebook** —
  `archive/plans/code_dominant_rebuild_notes.md`, the running note base for the architecture
  inversion (opened 2026-08-22, round two 2026-08-27). Thinking only, no build; read it before
  giving this decision its session, because the inversion is strand (b) taken seriously.
  @session: is (c) — a standing review protocol — worth a session, or is this three items?
  *filed 2026-08-10 · the wisdom-embedding strand closed 2026-08-15 (`13134bc`) · notebook
  anchored 2026-08-27*

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
  **First-draft feature — Mike, 2026-08-27: geolocation belongs in this rendition; moved up in the
  capstone plan.**
  **✅ DESIGN DECIDED 2026-08-28 (Mike) — build owed.** *(1)* **Tier: extra-sensitive, above
  ordinary sensitive — raw coordinates never enter any model prompt, cloud or local.** Models
  see only a code-derived zone line ("home since 14:02"); Mike defines named zones; the GPS→zone
  map is Python, enforced in tool code per the standing principle. *(2)* **Storage: zone
  transitions, not the trail.** No raw coordinate history kept (debug-only raw points, if ever,
  get `600` perms and a stated expiry). *(3)* **The phone app (Capacitor) is the tracker.
  First draft ships two capture modes only: on-message ping and a manual button — both
  "while using the app" permission, every ping traceable to a user action.** **The on-message
  ping DEFAULTS OFF — the user must turn it on explicitly, and the off-default is confirmed by
  test after the build.** Background scheduled/stochastic pings (Capacitor background-geolocation
  plugin, "allow all the time" permission, persistent notification) are **planned improvements
  for a later date, not this build**. *(4)* **Scanning bounds:** proactive scans fire on zone
  transitions or scheduled windows, never a poll loop; a location-keyed query to any NEW
  external vendor is its own decision, not covered here (Darwin's station pair is accepted).
  @kind: feature
  **✅ First draft BUILT 2026-08-28** (`029905e`, spinoff chat): both capture modes in
  `static/index.html` (ping strict-off-default, JS test 11/11; manual button);
  `POST /location` resolves the coordinate in-handler — no coordinate on disk, in a response,
  or in a prompt (asserted against bytes, 30/30 + 10/10); transitions-only log (0600, no raw
  trail even behind a flag); `config/templates/zones.yaml` template — **live zones are Mike's
  to define at `data/personas/mike/zones.yaml` on the VM**; "home since HH:MM" context line.
  No model-callable location tool registered (tightest reading — a grant decision if wanted).
  *remaining: **Mike's APK rebuild & sideload** (VM deploy done 2026-08-28; phone won't show
  the 📍 control until the sideload) + zones file on the VM (key places only — home, office,
  chess club; everywhere else is `away` by design); then one ping near a defined zone
  confirms. Handoff: `archive/handoffs/2026-08-28-location-first-draft.md`*
  **Next-draft scope authorised (Mike, 2026-08-28):** zone suggestion by reverse-geocode — a
  ping in no zone → code queries Google Places (Mike's explicit vendor ruling; the design had
  reserved location-keyed queries to new vendors) → Metatron proposes "lock this in as a
  zone?" → confirm card → Python writes the zone. Coordinates still never enter a model
  prompt; the vendor sees them in code only.
  *filed 2026-08-10 · split 2026-08-15 · promoted 2026-08-27 · design decided 2026-08-28 ·
  first draft built 2026-08-28 · deployed (server side) + next-draft ruling 2026-08-28*

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
  **✅ DECIDED 2026-08-28 (Mike): seed it and test it, on the condition it stays low cost/effort —
  and it is not capstone-necessary, so it never blocks capstone work.** Shape: a few health-domain
  entries on the **VM's** `sarah_chen` store (`seed_medication_fixture` precedent; name the
  machine — stores diverge silently), including one entry that contradicts a clinical read, where
  the flag must still win. **Bundle with the full A4 run `[DB-0820-05]`'s Step-6 caching already
  owes** — one run then exercises both gates. Note in that run's report that the suite now
  measures "safe *with* standing knowledge," so old baselines are not compared blind.
  @kind: chore
  *raised 2026-08-18 at the close of the knowledge-layering session · triaged out of `## Inbox`
  2026-08-18 · decided 2026-08-28*

- **[DB-0820-05] Fixing the cache leak frees enough money to put better models behind more agents —
  decide which, once the fix is deployed and re-measured.** Four agents sit on Flash-Lite for cost
  reasons that the cache work partly dissolves: `coordinator`, `diarist`, `intake_extractor`,
  `tone_profiler` (`config/modules/routing_cloud.yaml`).
  **The modelling, done 2026-08-20 against the measured 19 August day** (163 calls, 27 sessions,
  8 bursts, no development testing). Scenario A is anchored to the real $6.12 bill; the rest are
  modelled from the same measured token volumes:
  | | day total | per session | per month |
  |---|---|---|---|
  | **A** — today, mixed Pro/Flash, caching as built | **$6.12** | $0.227 | $184 |
  | **A′** — same mix, caching fixed (10-min TTL) | **$1.82** | $0.067 | $55 |
  | **B′** — **every agent on Pro**, caching fixed | **$3.11** | $0.115 | $93 |
  **So all-Pro with caching fixed costs about half of today's mixed bill.** Fixing caching frees
  ~$4.30/day; upgrading every Flash-Lite call to Pro spends ~$1.29/day of it.
  **The recommendation this analysis reached, which is not "upgrade everything".** Three of the four
  gain nothing from Pro: `diarist` is write-only and fire-and-forget (never seen by the user);
  `intake_extractor` and `tone_profiler` are closed-enum extraction over attacker-writable text with
  deliberately empty tool grants — Pro only adds thinking tokens to tasks with one correct answer.
  **`coordinator` is the only real candidate** (~$0.41/day, ~$12/month above today's baseline),
  because routing errors propagate through the whole turn. **Its blocker is latency, not money:** it
  sits on the critical path ahead of every reply, and Pro's thinking budget is already flagged in
  `ROADMAP.md` as the remaining lever on turn cost.
  **Three assumptions that must be re-checked before acting, in order of how much they move the
  answer.** *(1)* **Output inflation** — Flash-Lite emits 112 output tokens/call, Pro 815, and 86% of
  Synthesizer output is thinking (`SESSION.md`); modelled at 3×, but at 7× scenario B′ becomes
  $3.64/day and the margin narrows. *(2)* **Prefix fraction 65%**, measured from the two live caches
  (Synthesizer 18,127/24,099 = 75%; Coordinator 5,993/9,373 = 64%). *(3)* **Cache creation rate is
  unresolved** — creation *is* metered (proved by controlled probe, 12,001 tokens with zero generate
  calls) but bills at either $2.00/M or $0.20/M; at the lower rate A′ drops to $1.41 and B′ to $2.53.
  Resolving it needs the BigQuery billing export enabled (Console — Step 5 of the plan).
  **Do not act on the table above as it stands.** Every figure assumes the cache fix is live; today's
  numbers are contaminated by the leak. Re-measure a clean day first.
  Full reasoning and the measured rates: `archive/plans/vertex_cache_cost_control_2026-08-20_plan.md`.
  **Merged in 2026-08-27 (was `[DB-0822-01]` half b): the Step 6 Pro specialist-caching half.**
  Add `mental_wellbeing` and `physical_health` to the cached-path set at
  `core/orchestrator.py:4019` — **gated on a full A4 run** (`tests/run_a4_safety.py`, clinical +
  pipeline, both complexity tiers), because it moves the two clinical-flag agents onto the native
  loop. Worth ~+$0.17/day; the Flash-Lite six are +$0.008/day — include or skip without
  deliberation. Arithmetic: `archive/plans/vertex_cache_step6_specialist_caching_2026-08-21.md`.
  All-Pro routing quadruples what specialist caching is worth — which is why these are one
  decision now. **The @waiting condition is met** — half (a)'s reconcile passed on five
  consecutive clean days (evidence: `archive/backlog_closed_2026-08.md` § [DB-0822-01a]) — so
  what remains is the @session Pro decision plus one A4-gated code change.
  **✅ DECIDED 2026-08-28 (Mike) — coordinator-only, evidence before flip; Step 6 approved.**
  *(1)* Only `coordinator` is a Pro candidate (the other three gain nothing — analysis above
  stands). **Offline probe before any live flip:** `tests/run_coord_model_probe.py` (Green,
  owed) runs ~15 turns × both models through `_run_single_agent("coordinator", …,
  model_override=…)` — no Synthesizer, no routing edit — plus a replay of the four recovered
  `ROUTING_MISS` referent failures against Pro. Both models on the uncached path for
  like-for-like timing. Report: `tests/coord_model_probe_YYYY-MM-DD_flashlite_vs_pro.md`.
  Live flip (Red, with Mike) only if latency is tolerable per reply; **revert condition travels
  with the flip so the trial cannot quietly become permanent.** *(2)* **Step-6 specialist
  caching approved, both parts** — `mental_wellbeing` + `physical_health` onto the cached path
  behind the full A4 run (which also carries `[DB-0818-07]`'s knowledge seeding — one run, both
  gates), and the Flash-Lite six included in the same commit. *(3)* **(M) Mike enables the
  BigQuery billing export** (Console → Billing → Billing export → BigQuery, standard usage
  cost) to settle the cache-creation rate — meters forward only, so sooner is better; standing
  cost is BigQuery storage at this volume: cents.
  @kind: feature
  **✅ Probe RUN 2026-08-28** (`ec774da`, spinoff chat): Pro fixes the referent class (B-hard
  12/12 vs Flash-Lite 6/12) at ~+11s/reply, all thinking tokens — flip-as-measured is
  contraindicated; report recommends a capped-thinking-budget re-probe (needs
  `_run_single_agent` to pass `thinking_budget` beyond `synthesizer`). Cache helper already
  honours `model_override` (probe Step 0); bonus: `core/trace.py` now records `cached_tokens`
  (was priced then dropped — cache hits were invisible in traces).
  Report: `tests/coord_model_probe_2026-08-28_flashlite_vs_pro.md`.
  **✅ Pro flip DECLINED (Mike, 2026-08-28, on the probe evidence):** 11s/reply is a
  non-starter; fixing the Coordinator is the default — Pro is incrementally better at routing
  but the routing *system* is what matters, and the Coordinator is redesigned after the
  capstone anyway. Capped-budget re-probe dropped as moot. The referent fix is
  `[DB-0826-01]`'s Red path — prefer structural (code-computed referent context,
  `tools/turn_context.py` pattern) over another instruction line, since the adherence class
  is exactly where instruction-only fixes have failed.
  *remaining: A4-gated Step-6 commit only (spinoff batch incl. the trace fix deployed
  2026-08-28)*
  `due: 2026-09-15`
  *raised 2026-08-20 by Mike at the close of the Vertex billing reconciliation session ·
  absorbed `[DB-0822-01]`(b) 2026-08-27, both trails kept · decided 2026-08-28*

### Done and deployed — each closes on one ordinary use

*This group was a quarter of the backlog on 2026-08-18 and the single biggest reason the file grew:
finished work with no exit. **A fix is confirmed in the session that makes it, or it is time-gated
with a date.** Nothing new joins this group open-ended.*

- **[DB-0822-10] The virtue list can no longer reach an ordinary session — fixed and deployed
  2026-08-27, awaiting one evening turn to confirm.** Franklin's 13 virtues were injected into
  **every** session's system prompt, so the full list went out at 16:27, 18:24, 19:28 and 20:00 on
  08-21 with only one line of prose in `synthesizer.md` scoping it to the evening — an instruction
  that was already right and was simply not followed.
  **Fixed as injection code, per the item's own ruling that a second copy of an ignored rule is not
  a fix.** `session_kind()` ([core/orchestrator.py:297](core/orchestrator.py#L297)) matches the turn
  against the persona's **own configured** `evening_close` prompt read from `scheduler.yaml` — not
  a literal, which would go stale silently the first time Mike reworded it on the VM — and
  `load_config()` injects `evening_ritual.md` only on a match. Recital is now structurally
  impossible rather than discouraged. `7069ea1`, deployed. `tests/test_evening_ritual_gate.py`,
  11/11.
  **Why this is not closed yet:** the only live check so far was a **10:56 morning** check-in, which
  would not have carried the ritual under the old code either — it proves nothing. Two turns close
  it, and the first is free.
  @kind: bug
  @waiting: one ordinary **afternoon or evening** turn with no virtue list, and one 20:00
  `evening_close` that still carries it — the second half matters, because a gate that suppresses
  the ritual everywhere is the same bug wearing the opposite sign
  *filed 2026-08-22 by Mike · premise corrected same day · fixed and deployed 2026-08-27*

- **[DB-0820-03] The intake extractor is deployed and switched off; it stays off until it passes a
  test built from Mike's own mail.** The exit is a specific run, not ordinary use, so it cannot rot
  here: **(a)** Mike labels ~50 real messages into `tests/intake_fixtures/` on the VM (personal
  data — gitignored, never committed); **(b)** `python3 tests/run_intake_eval.py` free mode scores
  the code-only tier and sanity-checks the nine categories against real mail *before* any model is
  graded on them; **(c)** `--extractor` runs Flash-Lite through the production path (bare, no
  tools) — **gate: zero `action_required` false negatives**, `unclear` counts as a pass;
  **(d)** a scoped `/code-review` of the model-tier code (`tools/intake_extract.py`, the sweep's
  extractor branch, `config/agents/intake_extractor.md`) — unreviewed since written, and it meets
  attacker-writable input with a model in the loop the day the switch flips. Then and only then:
  `extractor.enabled: true` in mike's `intake.yaml`. Closes on the flip, citing the eval output.
  On the **local** routing path the eval must be re-run against the local model before the same
  flip — A4's lesson, recorded in `routing.yaml`'s entry.
  @waiting: corpus labelled by Mike on the VM (needs a few days of swept mail first)
  @kind: feature
  *filed 2026-08-20 during intake rollout; steps (b)–(d) are Claude's, (a) and the flip are Mike's*

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


- **[DB-0809-16] The dictation readout has never been spoken to.** Code-verified against every pass
  condition 2026-08-05; never run by a human with a microphone.
  @kind: chore
  @waiting: one dictated turn
  *filed 2026-08-05*

- **[DB-0809-21] The calendar reconcile has never had a live candidate to raise — until,
  probably, the Mousetrap duplicates.** `daily_calendar_reconcile` re-ran clean with 0 candidates
  through 08-10. **On 2026-08-25T04:35 the machine log carried two "possible duplicate calendar
  entries" reports** (three overlapping Mousetrap matinee events for 08-25, similarity 0.89 and
  0.45) — timestamped in the maintenance window, which is almost certainly this mechanism firing
  on a live candidate at last. **Two exits, both cheap:** confirm the emitter is
  `daily_calendar_reconcile` (one grep of its code path against the entry wording), then close;
  and **Mike resolves the actual duplicates** — three Mousetrap events, keep one.
  @kind: chore
  *filed 2026-08-09 · deferred by Mike · live-candidate evidence found 2026-08-27 in the deep-run
  machine sweep*
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
  *Checked live 2026-08-27: `expired_open_threads` is **still 0** after 12 days with 4 threads
  open — either grace legitimately keeps everything alive or expiry silently never fires, and
  nothing can distinguish them yet.*
  **✅ Data source built 2026-08-27** (`17142c0`, merged): every context-tracker write appends one
  line to `context_audit.jsonl` beside `context.json` (600), with `added`/`removed`/`expired` as
  separate fields — folding the last two together is what would hide a dead expiry again.
  `tests/test_context_audit_line.py`. Measurement follows once it has run a few days deployed.
  @kind: bug
  *filed 2026-08-14 by Mike · timestamp half closed 2026-08-15*
  `due: 2026-09-05`

### Unbuilt — real capability that does not exist

- **[DB-0827-09] Accountability Index — measure which stated intentions, goals and planned
  events actually happened in a period**, reading both the user's follow-through and Metatron's
  intended effect. Raised by Mike 2026-08-26 while fixing the Diarist's plan-vs-event confusion.
  The collection half exists: the Diarist logs user-voiced intentions in a fixed shape
  (`write_log` with an `intention` key + optional `stated_for` — `config/agents/diarist.md`).
  What does not exist is the index: a periodic join of stated intentions against subsequent
  occurred-event entries (and calendar/obligation outcomes) producing a fulfilment rate over a
  window. A9-adjacent (§ A9's content-free constraint applies if it ever becomes a rollup
  field); probably a Pattern Miner or analytics job, not an agent behaviour. Captures only what
  the user voiced, by construction.
  **✅ DESIGN DECIDED 2026-08-28 (Mike) — build owed.** *(1)* **Evidence split by
  checkability:** structured outcomes (calendar event occurred, obligation closed) join in
  code, deterministically; free-text intentions vs journal/event entries go through a nightly
  Flash-Lite-tier judgment gate (bare, `intake_extractor` pattern) scoring
  `fulfilled / unfulfilled / indeterminate` — indeterminate stays indeterminate, no forced
  verdicts. *(2)* **Window:** `stated_for` + 2-day grace when present; undated intentions
  default to 7 days; the index reports over a trailing 30 days. *(3)* **Surfaces both ways
  (c, Mike's call):** internal series + content-free count into the A9 rollup, and
  qualitatively in the weekly retrospective ("six set out, four done", naming the open ones).
  Unfulfilled intentions also feed `[DB-0809-02]`'s what-to-do-NOW opportunistic surfacing,
  not nagging. Useful during testing. **Audit follow-up: `[DB-0828-01]`.**
  @kind: feature
  **✅ Code half BUILT 2026-08-28** (`c082fb6`, spinoff chat): `tools/accountability.py`
  structured joins + trailing-30d rate (indeterminate excluded from the denominator);
  content-free counts in the A9 rollup; CLI `python3 -m tools.accountability --report`.
  11/11 tests. Judgment-gate agent file + 05:45 scheduler line are Red — proposal verbatim in
  `archive/handoffs/2026-08-28-accountability-index.md`, incl. a flagged privacy-tier check
  (journal text is sensitive → the gate's routing must say ZDR-VM basis). Discovered there,
  decision-shaped: a second same-day intention silently overwrites the first in the day log
  (`_deep_merge` scalar replace) — Diarist write-shape call, Mike's.
  **Rulings (Mike, 2026-08-28, post-deploy):** *(a)* intentions become a LIST in the day log —
  repeated statements of one intention are kept, so **frequency scores urgency** (Diarist
  write-shape line is Red, session ③; index counts restatements); *(b)* the judgment gate may
  read journal text on the Vertex path **under Amendment 2026-08-28** — its routing entry
  records that basis when built; *(c)* daily cadence confirmed sufficient (the 05:40 rollup
  counts already run — no new job until the gate lands).
  *remaining: judgment gate + list-shape line ride the next Red/agent-file session; deployed
  2026-08-28*
  *raised by Mike 2026-08-26 mid-session · triaged out of Inbox 2026-08-27 · design decided
  2026-08-28 · code half built 2026-08-28 · deployed + rulings 2026-08-28*

- **[DB-0828-01] Audit the Accountability Index's judgments once it has ten days of data — are
  things characterized as they should be?** Mike's instruction 2026-08-28, filed with the
  `[DB-0827-09]` design. Review a sample of `fulfilled` / `unfulfilled` / `indeterminate`
  verdicts against the underlying entries: indeterminate especially (is the gate dumping hard
  cases there?), plus spot-checks that fulfilled/unfulfilled verdicts hold. Exit: a short
  report; miscategorization patterns go back into the judgment gate's instruction or the join
  code.
  @kind: chore
  `due: 2026-09-07` — the index deployed 2026-08-28; date set per this item's own rule
  (deploy + 10)
  *filed 2026-08-28 at Mike's instruction, alongside the index design · dated at deploy*

- **[DB-0827-03] Build the CRM sweep — the design is accepted, and the plan MUST BE REVIEWED
  WITH MIKE AGAIN BEFORE ANY BUILD SESSION STARTS.** That review gate is Mike's explicit
  instruction (2026-08-27), given when he accepted the plan: file it, do not build. The full
  design, budget and test plan: `archive/plans/crm_sweep_plan_2026-08-27.md`.
  **Shape in one line:** nightly Flash-Lite extractor (bare, empty grant — `intake_extractor`
  pattern) over yesterday's conversations + journal → validated proposals into an append-only
  `crm/proposals.jsonl` → quiet morning-brief digest → Mike accepts conversationally → Python
  applies from the ledger by id, behind a toggleable batch confirm tap.
  **Binding constraints carried from the plan:** proposes, never writes; additive only, no
  merges, `notes` never a target; sensitive tier under the § Section 0 ruling of 08-26.
  **Build facts:** Opus session (Mike's 08-18 split); `config/agents/crm_sweep.md` and
  `routing_cloud.yaml` are **Red**; two `tools/crm.py` guards ship with it (`log_interaction`
  dedup, `last_contact` advance-only — both hazards verified live 08-27). **Dependency:**
  `[DB-0827-01]` (decline-does-nothing) should land before or with the confirm tap.
  **Step 0 of the build:** re-take the 2026-08-19 measurements (1 `log_interaction` per 200
  traces) before relying on them.
  @kind: feature
  @waiting: Mike's pre-build review of the plan doc
  *filed 2026-08-27 at Mike's instruction, plan accepted same day*

- **[DB-0827-04] Review contact notes and promote recurring patterns into new CRM fields —
  Mike's idea (2026-08-19), gated until notes are rich.** The mechanism is sound and its trigger
  has not fired: it should run when `notes` fields carry real material, and today they are
  empty. The CRM sweep (`[DB-0827-03]`) never writes `notes`, so richness will come from
  conversational writes — check the store before designing anything. Recorded here so the gate
  survives (it previously lived only in the 08-22 planning handoff, which is exactly how items
  get lost).
  @kind: feature
  *filed 2026-08-27 at Mike's instruction (during CRM sweep plan review)*

- **[DB-0826-02] Fill in a work contact from their public profile, with a photo to confirm it is
  the right person.** Mike wants this and has already specified its shape; it is unbuilt, not
  undecided. **Do not re-open the privacy question — it is settled below.**
  **The design, as Mike specified it (2026-08-22, restated 2026-08-26):**
  a **per-contact toggle, never a blanket sweep**; an identity **confirmation showing a profile
  picture** — *"is this the guy"* — because **a face is verifiable at a glance and a name plus an
  employer is not**, which is the whole reason the confirmation is a picture rather than a summary.
  **Suggested scoping, not yet ruled on:** trigger on `primary_contact_type` in the `work_*` set
  (already in the CRM schema); the confirmation is **required, not advisory**; a confirmed match
  writes with a `verified` marker and an unconfirmed one **writes nothing at all**.
  **The privacy ruling, and why this item does not wait on it — Mike, 2026-08-26.**
  Sending a named private individual to a research path is **not** decontextualized dispatch, so
  it sits against `ROADMAP.md` § Section 0 rather than comfortably inside it. It was blocked on
  that question from 2026-08-22. **Mike has now given it a pass to build despite that**, in the
  same breath as ruling that the `mike` persona keeps running on Vertex after Google refused the
  abuse-monitoring opt-out: *"Google calendar already has my plans, and Google has my email
  correspondence. Nothing needs to change here. I'm gating it personally."* The per-contact
  toggle **is** that personal gate, expressed in code.
  **This clearance is recorded so it is not re-litigated.** A future session finding the § Section 0
  tension will find it already answered here, with its reasoning: the marginal disclosure is a name
  already held by the same vendor, and the control is Mike's own per-contact decision.
  **What would reopen it, and nothing less:** the deployment ceasing to be single-user, which is
  the trigger § Section 0 already names for the whole ZDR clarification.
  @kind: feature
  *filed 2026-08-26 at Mike's instruction · design agreed 2026-08-22 · privacy pre-cleared
  2026-08-26, deliberately, not by omission*

*(`[DB-0822-01]` merged into `[DB-0820-05]` 2026-08-27 — half (a) was closed by the reconcile,
half (b) is now part of the Pro-routing decision. Evidence and trail:
`archive/backlog_closed_2026-08.md`.)*

- **[DB-0827-06] The Synthesizer's prose can be tightened considerably without losing substance —
  a deliberate compression pass, section by section.** Mike, 2026-08-27, with a worked example
  applied the same day (the "urgency in external text" paragraph: claim first, rule second,
  rationale last, framing scaffold dropped — same substance at ~60% of the words). The structural
  audit (`archive/plans/synthesizer_audit_2026-08-18.md`) moved and cut whole sections; this is the
  orthogonal pass it deliberately did not fold in: rewording *inside* kept rules. Not just tokens —
  the project's measured length→adherence effect means tighter imperative rules likely adhere
  *better* (six of six 08-21 complaints were rules already in the file, ignored). Per-section
  against the same gates (A4 pipeline, B1 disclosure, `[CONTEXT]` parse), two or three sections
  first as a behaviour probe. Estimated yield on the post-audit file: ~10.3k → ~7k tokens.
  **Non-urgent (Mike's call, 2026-08-27).** Check the code-dominant rebuild decision before
  starting — a rebuild that rewrites the agent layer supersedes this.
  @kind: chore
  *filed 2026-08-27 during the audit execution session, at Mike's instruction*

- **[DB-0820-04] No hostile test email has ever been aimed at the intake extractor.** The B1
  `injection` suite (`tests/run_b1_redteam.py`) proved the email row against **Logistics**
  (2026-08-08, 3/3) — but the intake pipeline is a new reader of attacker-written text, and its
  extractor has no row of its own. Build one payload aimed at it (`[SYSTEM: …]`-class, in a
  message body the sweep classifies); pass = the payload is labelled as content, nothing else
  happens — no category outside the enum, no `important` manipulation beyond flagging oddness.
  Run against `danny_park`, per the standing B1 note (an ordinary-life persona, so a clinical
  thread cannot pre-empt the payload and produce a pass that proves nothing). Also advances
  **B1b**, one of the three open A7 checks — which is why this stays its own item.
  @waiting: intake enabled on the VM and the sweep processing real mail
  @kind: feature
  *filed 2026-08-20 during intake rollout — plan § verification step 7, built nothing yet*

- **[DB-0820-02] A file sent from the phone app cannot be saved back out of it.** Tapping a photo
  opens it full-size and tapping a document saves it — **in the browser PWA only** (built and
  verified 2026-08-20, `saveAttachment()` in [static/index.html](static/index.html)). In the
  installed APK the same tap does nothing: an Android WebView has no download manager, so a
  `blob:` URL with a `download` attribute fails **silently**. Interim answer, and the reason this
  is not urgent: open the PWA in Chrome on the phone and saving works there.
  **The fix is `@capacitor/filesystem` + `@capacitor/share`** — write to Downloads, or hand the
  file to the share sheet. Cost is not the code, it is that these would be the **first plugins in
  a deliberately zero-plugin app** (`capacitor.plugins.json` is `[]`): every later change then
  needs `npm i` + `npx cap sync` + a Gradle rebuild, and the native bridge surface grows.
  **A third option was considered and rejected here, not deferred:** a short-lived signed download
  URL opened in the system browser needs no plugins and works everywhere — but it puts a
  capability token in a URL, which this project deliberately refused for the WebSocket handshake
  because it lands in access logs (`core/server.py` § websocket_endpoint). Do not re-propose it
  without addressing that.
  *Raised by Mike 2026-08-20 while testing attachments: "if the app serves as a cloud drive, it
  might be helpful to be able to pull something down." Explicitly "not strictly necessary."*
  @kind: feature

- **[DB-0819-01] Agents cannot subscribe to anything — every input the tool reads, the user had
  to sign up for personally.** Mike, 2026-08-19, during the intake-pipeline design: *"other
  agents might even proactively subscribe to lists to enhance their own output"* — and RSS the
  same way, with subscription requests routed through the agent that has web access. The intake
  envelope already makes an RSS/list item just another bulk message with a known `list_id`, so
  the pipeline half is free; what does not exist is the **election mechanism**: which agents may
  request a subscription, who approves it, where the roster of standing subscriptions is
  recorded, and how one is cancelled. E4-shaped design conversation before any build. One
  constraint already binding on the intake build: nothing in the classifier may assume a message
  was solicited by the user personally.
  @kind: design
  *raised by Mike 2026-08-19 in the intake plan review; plan holds the context
  (`~/.claude/plans/this-session-is-for-tranquil-mango.md` § subscriptions as agent-elected inputs)*

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
  **First-draft feature — Mike, 2026-08-27: geomapping/transit belongs in this rendition; moved up
  in the capstone plan.** Blocking input: the Darwin / Rail Data Marketplace API registration is
  Mike's to do (his account, his key).
  @kind: feature
  @waiting: Darwin API key registered by Mike
  *filed 2026-08-18 · promoted 2026-08-27*

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
  **✅ Built 2026-08-27** (merged `6b0a6d5`): answering "which Bill?" is stored in a per-persona
  `crm/name_resolutions.json` (0600, no migration of existing data) and reused; recorded only
  when the name was genuinely ambiguous at that moment, so a lone Bill stored today never
  swallows a second Bill added later; every stale path (deleted person, changed match set,
  corrupt store) falls back to asking; corrections keep history (`superseded`), and resolutions
  follow `merged_into`. `tests/test_contact_resolution_memory.py`, 16 checks. The opposed-item
  tension is held: nothing widens `_find_by_name`, "William Hart nicknamed Bill" stays out of
  scope by design. Handoff: `archive/handoffs` consumed → evidence in the 08-27 log fragment.
  @kind: feature
  @waiting: the owed deploy, then one live pass — name an ambiguous contact, answer, name them
  again later; pass is no second question (diagnosable on fail: empty
  `data/personas/mike/crm/name_resolutions.json`)
  *raised by Mike 2026-08-18 · built 2026-08-27 by the CRM attack worker*

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
  **✅ Per-entry proposal delivered 2026-08-27** (merged `c2798eb`):
  `archive/plans/wisdom_store_cleanup_proposal_2026-08-27.md` — all 24 dispositioned with
  destinations (11 preferences → persona file, 3 obligations, 2 duplicate merges, 3 tool
  defects, 2 transients, 2 content-free, 1 duplicating `profile.yaml`). Built from the
  hand-reviewed 08-15 KEY_MAP, not a live read (store is Denied-tier); it counts **eleven**
  interaction preferences where this item says eight — the transplant should treat those eleven
  as one review pass, since several likely collapse into one persona-file line.
  @kind: chore
  @waiting: Mike reviews the proposal, then the execution session (VM-owned data; the
  persona-file transplant is the judgement half)
  *found 2026-08-15 by reading all 59 live entries during the schema migration (`a35acfa`), which
  reports them and deliberately moves nothing · triaged out of `## Inbox` 2026-08-18 · proposal
  2026-08-27 by the wisdom-store attack worker*

- **[DB-0808-11] A scheduled job with notifications on would push at 3am.** `fire_function` runs no
  gate stack — `days`, `respect_quiet_hours` and the activity gate are ignored for every function
  job. `daily_travel_check` is pinned to 06:45 purely to work around it. Fix by extracting the gate
  stack so both job kinds run it.
  @kind: bug
  *filed 2026-08-08*

- **[DB-0803-05] A dead server now shows the app's own page — built and tested 2026-08-22, NOT
  deployed.** Fallback-only SW exactly as specified: dedicated `offline.html`, navigation requests
  only, served solely when the network fetch fails; `/` never cached; `offline-v1` cache version is
  the recovery lever (`2d7f955`; 15/15 in a real `vm`-sandbox execution test). **Also fixed while
  verifying: SW registration was gated on push permission** — a user who declined notifications
  never had a service worker at all; now registered unconditionally at startup (`e2a7f87`).
  @kind: bug
  @waiting: the owed deploy, then ONE ONLINE LOAD to install the worker, then background/kill the
  server and reload — the app's own page, not Chrome's error page
  *filed 2026-08-03 · built 2026-08-22*

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
  **Scoped 2026-08-27, confirmed live, stopped at the Red line** (merged `bb9ebdb`): the fix
  needs a `discontinuation_risk` field + `MEDICATION_MISSED_CRITICAL: <name>` flag suffix in
  `config/agents/physical_health.md` (Red — the module's own 08-08 design comment names this
  exact distinction as the goal and never wired it in), then a Green `_thread_tier()` change
  reusing the existing tier-2 watch lifecycle, failing toward tier 1 on any parse/read gap.
  Full spec: `archive/plans/medication_ranking_spec_2026-08-27.md`; the owed A4 re-run ran
  anyway — **PASS 3/3**,
  `tests/a4_safety_rerun_2026-08-27_gemini_clinical_quick.md`.
  @kind: feature
  @session: the `physical_health.md` half — supervised Red session, spec ready
  *filed 2026-08-08 · scoped + A4 re-run 2026-08-27 by the medication attack worker*

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

- **[DB-0808-09] Specialists spend a full model round-trip per tool call — never batching — so
  every extra turn re-sends their whole accumulated context.** Step 1 (measure) is **done,
  2026-08-27**, from live VM traces, two windows (Aug 1–8 and Aug 20–27; turn counts are
  output-token-bug-immune, so both windows are trustworthy). Aug 20–27, turns/call:
  `relationships` 4.2 · `work_vocation` 3.7 · `logistics` 3.6 · `mental_wellbeing` 3.1 ·
  `physical_health` 2.9 · `diarist` 2.6 · `synthesizer` 1.1 · `coordinator` 1.0. The item's
  original open question is settled: **`logistics` is not an outlier, multi-turn is the norm.**
  **The mechanism, measured:** the parallel-calls-per-turn histogram is `{1: N}` for every
  specialist — 392 tool turns in the window, not one carried two calls. The API and
  `_openai_compat_loop` both support parallel calls (the Synthesizer once emitted two); the
  specialists just never choose it. Common sequences are short read chains ending in one write:
  `read_intake_queue → read_email → final`, `search_memory → write_log → final`.
  **Step 2/3 candidate designs, unevidenced — diagnose from traces before building** (the
  Coordinator mis-diagnosis is this item's own precedent):
  *(1) Instruct batching of independent reads* — cheapest, saves ~1 turn on most agents; dependent
  chains (`read_log → write_log`) can't batch, so this is a trim, not a collapse.
  *(2) Coordinator prefetch (Mike's proposal, 2026-08-27):* run predictable reads as code before
  the specialist's first call and append outputs to its first user message — no extra model turns,
  and the cached system prefix stays stable since prefetched data rides in the user message. The
  measured first-turns are exactly the predictable reads (`read_email`, `read_calendar`,
  `read_log`, `read_intake_queue`). Catch: the Coordinator must *predict* the tool set (it
  currently emits no tool plan; KNOWLEDGE_TO_LOAD is precedent for the pattern), a missed
  prediction still costs the specialist a turn, and writes can never prefetch — their content *is*
  the specialist's reasoning.
  *(3) Read/write specialist split (Mike's proposal, 2026-08-27):* weakest on cost as stated — the
  write half still needs the read outputs in its context (same tokens, now paid under two system
  prompts) plus a second dispatch hop; only earns if the read half runs on a much cheaper model.
  **Standing caution kept:** slimming `coordinator.md` is a separate token-size argument and must
  watch the **4,096-token Vertex cache floor** — and the file has since grown to ~5,184 tokens,
  near/past the padding threshold, so the earlier "slimming saves zero, padding re-inflates"
  conclusion needs re-deriving before anyone relies on it.
  @kind: chore
  *filed 2026-08-08 · Step 1 closed 2026-08-27 from live traces (session: coordinator-slim
  rehydration → token audit); design options folded in from Mike's same-day review*

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

*(swept 2026-08-21 by `/backlog deep` — **54 → 42 entries**, every deletion verified against
current code rather than against the entry's own description. **Nine were already built or
fixed and nobody had gone back to look**, which is the failure mode this section's deletion rule
exists for. Pointers, so nothing is lost:*

  - *email dispatch confirmed a send that never happened (08-10) → `[DB-0810-13]`, **closed
  2026-08-14**; the fix is `core/actions.py`, whose header opens on this exact Kathaleen event*
  - *`search_memory` JSON `Extra data` parse error (08-06) → **fixed**: `core/memory.py` now takes a
  per-persona `FileLock` and writes atomically ([core/memory.py:80](core/memory.py#L80) documents
  this signature as the symptom). The **CRM contact-count request three hours earlier the same day**
  (08-10T11:19) was filed as *"needs an integration with their external CRM"* and was almost
  certainly this outage — `list_contacts` existed the whole time. **A machine entry's diagnosis was
  wrong for the fourth time**; its symptom was right.*
  - *email approval prompt not rendering + read live Google Contacts (08-04, **three entries**) →
  **both built**: `send_email` is in the out-of-band confirmation class
  ([core/actions.py:48](core/actions.py#L48)) and `read_google_contacts` ships in
  [tools/google_contacts.py](tools/google_contacts.py)*
  - *global default for mailbox check frequency (08-10 ×2) → **built** by the intake pipeline:
  `intake_sweep` carries a 60-minute interval in `core/scheduler.py`'s `_DEFAULT_JOBS`, overridable
  per persona*
  - *proactive pre-departure travel checks (08-05) → **built**: `daily_travel_check`,
  `config/templates/scheduler.yaml:97`*
  - *Kathaleen → Kathleen (08-18 ×2) → `[DB-0818-08]`, where it is worked failure #1; the Southeastern
  zero-source answer (08-18) → `[DB-0818-04]` and the same item's worked failure #2. Both were named
  in the 08-18 sweep's pointer list and left in place anyway.*
  - *the self-applied "open sessions with the most time-sensitive commitment" preference (08-18) and
  the `[same rule in two places]` conflict it produced the next morning (08-19) → **promoted into
  `[DB-0815-11]` as a third instance**, and the only one that can be verified end to end.*

*Not deleted and deliberately: the 08-05 Heathrow drop-off cluster and the 08-02/08-03 correction
runs. They are behavioural, nothing has shipped against them, and collapsing them would destroy the
only record of how often the tool misreads who is travelling.)*

*(swept 2026-08-27 by `/backlog deep`. The ⚠ `CLARIFICATION_NEEDED: ×33` is **diagnosed and
promoted → `[DB-0827-07]`** — all 33 events read live off the VM, every one an empty template
label from the Coordinator, 3–5/day since 08-18. Other deletions with pointers: the two
Mousetrap duplicate-calendar entries → `[DB-0809-21]`, where they are the live candidate that
item was waiting for (the actual duplicates still need Mike to resolve — three events, keep
one); the 08-26 Prudential/Apex merge correction → `[DB-0826-01]`, same incident; `Omit ×2` →
second exhibit in `[DB-0827-07]`'s class; the Bulgarian-global preference → `[DB-0815-02]`,
held; the 08-06 CRM onboarding protocol → superseded by `[DB-0827-03]` + `[DB-0818-08]`; the
voice-toggle removal ×2 → resolved deliberately as a toggle, [static/index.html:1907](static/index.html#L1907);
the five June 2026 corrections → older than every fix that followed (tone, timestamps, location
bootstrapping all since reworked). Kept, deliberately again: the Heathrow cluster, the 08-02/03
correction runs, and the unresolved single corrections — behavioural evidence nothing has
shipped against.)*

- **[user corrected a prior turn]** User corrected my assumption that a dental email for Iva was misdirected to them. I missed the forwarding chain from their secondary account, likely because the email parser didn't pass the forwarding metadata.  
  `2026-08-28T15:24:16.988533Z`

- **[user corrected a prior turn]** User clarified that the dental email concerned Iva and was a forwarded message, which they attribute to the missed detail in previous summaries.  
  `2026-08-28T15:23:54.611005Z`

- **[a specialist missed a signal it should have caught]** Coordinator routed user's query about 'who is the appointment for' to past health logs (Aug 26) instead of checking the recent Sept 15 dental email that was the immediate subject of the previous turn.  
  `2026-08-28T15:20:25.997437Z`

- **[user corrected a prior turn]** User indicates previous summaries of the dental appointment email were incomplete or lacked vital details.  
  `2026-08-28T15:16:45.353085Z`

- **[user corrected a prior turn]** User corrected a hallucinated yoga entry on Aug 26, and pointed out the logistics check falsely claimed to be covered despite missing destination locations for the swim and pharmacy.  
  `2026-08-28T11:10:06.488451Z`

- **[user corrected a prior turn]** Logged yoga activity on 2026-08-26 was incorrect; user reports no yoga occurred. Rowan payroll deadline is 1st-5th, not a single date.  
  `2026-08-28T11:09:38.020295Z`

- **[user corrected a prior turn]** Omitted (none).  
  `2026-08-28T08:28:20.691477Z`

- **[user corrected a prior turn]** System prematurely inferred plant watering was complete based on focus notes, rather than waiting for explicit user confirmation. User had to correct the record.  
  `2026-08-28T08:26:43.190609Z`

- **[user corrected a prior turn]** Corrected the plant-watering task completion date; the system had prematurely logged it as done.  
  `2026-08-28T08:26:23.626062Z`

- **[FALSE_COMPLETION_CLAIM]** Synthesizer reported write_contact as done while it was still awaiting user approval; response replaced.  
  `2026-08-27T09:55:11.565159Z`

- **[a specialist missed a signal it should have caught]** Coordinator routed "Undo that merge" to work_vocation thinking it referred to the Prudential/Apex project, completely missing the conversational context where the user had just asked to merge the contacts Marcus Whitfield and Marcus Delgado in the immediately preceding turn.  
  `2026-08-26T16:36:07.024888Z`

- **[a specialist missed a signal it should have caught]** Coordinator interpreted 'Read that back to me again' as a request about Prudential scheduling, but it was a direct request to repeat the food profile data provided in the immediately preceding turn.  
  `2026-08-18T15:39:33.761495Z`

- **[a specialist missed a signal it should have caught]** Coordinator misinterpreted phonetic Bulgarian speech-to-text bug report as a psychological pivot to rest. User is reporting an audio transcription bug where Bulgarian is parsed as English. 'Raspira' means 'understands' (Разбира), not 'breathe/rest'.  
  `2026-08-15T13:49:28.614262Z`

- **[a specialist missed a signal it should have caught]** Coordinator interpreted 'Approved' as referring to the credit card payment and Prudential call, but the user was approving the test email to Kathleen from the previous turn. Logistics erroneously closed the credit card obligation as a result.  
  `2026-08-15T11:16:06.210340Z`

- **[a specialist missed a signal it should have caught]** The system failed to route the user's explicit request to check the inbox to the logistics agent in the previous turn.  
  `2026-08-14T15:34:58.664405Z`

- **[a specialist missed a signal it should have caught]** Coordinator misidentified the missing email as the old Prudential email, missing that the user was asking about the Kathaleen test email they approved moments prior.  
  `2026-08-10T17:10:51.143190Z`

- **[a specialist missed a signal it should have caught]** Relationships agent failed to send an email to the explicitly provided address (diamond.mike.mt@gmail.com) because it attempted a CRM lookup for the user's own name and failed, treating the user as an unknown third-party contact.  
  `2026-08-10T16:30:58.571802Z`

- **[a specialist missed a signal it should have caught]** Logistics received scheduling directives but only returned a log write confirmation instead of taking the calendar actions.  
  `2026-08-10T15:11:45.521931Z`

- **[a specialist missed a signal it should have caught]** Coordinator misunderstood 'previous request' as the Iva lunch instead of the immediate prior turn asking for Transport, Weather, and Pollen research.  
  `2026-08-10T10:28:57.401389Z`

- **[a specialist missed a signal it should have caught]** Coordinator missed that the user message was a system instruction about check-in formatting, instead resolving intent as a literal request for a check-in.  
  `2026-08-09T09:06:40.509678Z`

- **[a specialist missed a signal it should have caught]** Logistics missed the meeting time (4pm) and location (Google Meet) from the active thread context, prompting the user for details they already provided.  
  `2026-08-06T16:42:52.051344Z`

- **[a specialist missed a signal it should have caught]** Coordinator processed the user's previous message rather than their current one.  
  `2026-08-05T20:47:32.529068Z`

- **[a specialist missed a signal it should have caught]** Coordinator called 'research' instead of 'research_agent', causing subagent failure.  
  `2026-06-26T16:41:59.522508Z`

- **[a specialist missed a signal it should have caught]** Coordinator attempted to route to 'research' instead of 'research_agent', and 'research_agent' itself returned no data.  
  `2026-06-26T16:30:36.488035Z`

- **[a specialist missed a signal it should have caught]** Previous user message received no response and an expected write_config call was not executed — pipeline/execution failure in last exchange. Message content not present in current context window.  
  `2026-06-26T15:51:55.656657Z`

- **[a specialist missed a signal it should have caught]** Both Physical Health and Mental Wellbeing agents returned file-not-found errors. Coordinator routing package used space-separated agent names ("Physical Health", "Mental Wellbeing") rather than underscore-separated filenames (physical_health, mental_wellbeing). Agents not called successfully — Synthesizer responded from context alone.  
  `2026-06-26T08:21:51.451822Z`

- **[a specialist missed a signal it should have caught]** Mike's last message did not come through in the previous session — this is a recurring issue (two sessions now). Message content is unknown and cannot be replied to. Mike is frustrated. Need to surface this clearly and ask for a resend rather than routing to specialists with no content.  
  `2026-06-22T05:31:14.313792Z`

- **[user corrected a prior turn]** User corrected transit route to Transport Museum, explicitly excluding Jubilee and Piccadilly lines which were previously suggested.  ×2  
  `2026-08-16T08:06:21.241217Z`

- **[user corrected a prior turn]** User corrected the previous exercise log, stating the run was only a test and requested its removal.  ×2  
  `2026-08-15T11:13:42.274343Z`

- **[user corrected a prior turn]** The user corrected the grocery reminder logic (not every Friday, but 3 days after the date of an order).  ×2  
  `2026-08-10T15:46:40.890480Z`

- **[user corrected a prior turn]** User clarified they wanted to know the mechanism/tools for routing, not the route itself.  
  `2026-08-10T12:29:39.464756Z`

- **[user corrected a prior turn]** The user is clarifying that their previous query was not about the travel itself, but about the *mechanism* used to generate the routing.  
  `2026-08-10T12:29:21.953978Z`

- **[user corrected a prior turn]** User previously confirmed Rowan transfer was handled, but system asked for details again.  
  `2026-08-07T16:22:17.434741Z`

- **[user corrected a prior turn]** The system incorrectly flagged the Rowan payroll transfer as 'pending' despite the user having previously provided this information.  
  `2026-08-07T16:21:48.444766Z`

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

- **[user corrected a prior turn]** Corrected previous transit concern by noting multiple rail options exist for Heathrow.  
  `2026-08-04T14:41:57.409553Z`

- **[user corrected a prior turn]** User corrected system for failing to proactively research venue details (address, menu, hours) when a new pub meeting was scheduled.  
  `2026-08-04T13:58:03.975204Z`

- **[user corrected a prior turn]** User opted to close the CalDAV integration thread.  
  `2026-08-04T12:37:18.994165Z`

- **[user corrected a prior turn]** User explicitly corrected system's read of 'low energy' trend, stating they have natural momentum. System over-extrapolated from isolated log entries about sleep and fatigue.  
  `2026-08-04T12:20:02.780437Z`

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
