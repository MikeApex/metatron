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
*(empty — triaged 2026-09-02 by Red session ④'s capstone review, all eight dispositions Mike's;
evidence in `archive/backlog_closed_2026-09.md` § Inbox triage 2026-09-02)*


- **A `quick` request can send the clinical agents to the cheap model, because "non-sensitive" is
defined as "not marked local" and the cloud routing file marks nothing local.**
`core/router.py:98` reads non-sensitive as *absence of* `local: true`, and `routing_cloud.yaml`
sets `local: true` on nothing — so the `:22` comment *"(non-sensitive agents only)"* excludes
nothing at all, and a `quick_override` call to `mental_wellbeing` or `physical_health` runs on
the **bulk** tier rather than the reasoning tier.

Pre-existing, not introduced by any recent change. It matters more than it did because A4
safety testing is suspended (ROADMAP § 0 pt 8), so nothing is currently exercising the clinical
flags on any model, let alone on the bulk one.

**Needs Mike's word on the fix direction, which is why it has not been actioned:** mark the
sensitive agents explicitly in `routing_cloud.yaml` (narrow, honest, but re-states a list that
already exists elsewhere and can drift), or invert the router's default so unknown-tier agents
are treated as sensitive (fail-closed, matches the project's standing posture, but may make
`quick` stop working for agents that legitimately want it). Recommendation: the router
inversion, because a routing file that forgets to mark a new sensitive agent is the same class
of silent failure as the one being fixed.

*carried in SESSION.md as an unfiled ⚠ since session ⑥ (2026-09-03) and filed 2026-09-03 by
session ⑦ during its close, because an item recorded only in a primer paragraph is one primer
rewrite away from being lost — and the primer was over its ceiling holding it*

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

### Green/Amber — buildable without a prompt

*One survivor of the 2026-08-21 trace-measured block — its two siblings closed on live evidence
2026-09-02 (`archive/backlog_closed_2026-09.md`).*

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
  **⚠ Fresh reproduction across three live days, post-deploy — the narrow confirm passed and the
  item still cannot close (Red session ④, 2026-09-02).** The confirm half held: Prudential,
  resolved, was raised zero times on 08-29 (7-of-9 the week before), and the 09-01 Apex deferral
  + plants-watered updates were respected by every later run that day. But the headline failure
  reproduced: the five-day exercise hiatus **ended 2026-08-23** (Mike's own journal entry), yet
  08-30 10:48 said *"day three of your scheduled exercise hiatus"*, 08-31 11:21 said it was
  *"officially over"* (a week late), and 09-02 08:07 said it *"officially wraps up today"* —
  three different wrong states, spanning the 09-01 model migration, so it is the carried-state
  mechanism, not the model. The age annotations are live and the model repeats the stale state
  anyway — the "revisit only if a dated count still gets misread after deploy" condition above
  has now fired. The deliberately-unbuilt code-computed derived-facts line is back on the table.
  @waiting: superseded — the confirm arrived and was outweighed by the reproduction above
  **Merged in 2026-09-02 (Mike's disposition):** the two 08-28/29 Inbox reports of
  already-given information and suggestions repeating — same carried-state mechanism, now three
  independent reports of one fault. (Their suggest-at-impossible-times half filed separately as
  `[DB-0902-03]`.)
  **✅ The derived-count half is now BUILT, deployed and VM-verified (session ⑥, 2026-09-03,
  `54073b6`)** — the half retired on 08-27 whose own re-open condition fired.
  `derived_facts()` recomputes counts by subtraction from the date each line was written, on
  the principle that **a count is only ever a claim about a date**. Validated against reality:
  *"Day 3"* written 2026-08-21 puts day 1 at 08-19 and a 5-day period ending **2026-08-23** —
  exactly the date Mike's journal records the hiatus ending — and the 08-22 entry derives the
  same start and end independently. Run against the four real log files carrying such counts,
  all four periods are correctly reported as ended. Deliberately narrow: two forms only
  (`day N of an M-day X`, `N days since X`), both pure arithmetic over a stored date; nothing
  needing a judgement about whether a thing is still true, which is the filtering this item has
  twice declined. Lands in `augmented_input`, not the cached system prompt, so the Vertex
  prefix cache is undisturbed; returns "" when nothing parses. `tests/test_derived_facts.py`,
  15 checks.
  @waiting: 2026-09-10 — close on one live run reading a dated count back correctly. Note the
  four stale counts age out of the 5-day log window on 2026-09-04, so the confirm needs either
  a run before then or a fresh dated count.
  *filed 2026-08-22 by Mike · age-out half built 2026-08-27 (session-hygiene worker) · intraday
  half built + derived-count half retired 2026-08-27 (orchestrator-context worker) · reproduction
  on live traces 2026-09-02 (Red session ④) · Inbox repeat-info reports merged in 2026-09-02 ·
  derived-count half built 2026-09-03 (session ⑥)*

### Red — judgement work, not automatable

### Denied tier — Mike's own file

### Green/Amber — a second block, found after the first pass

- **10. [DB-0829-01] The log recorded an email as sent while it was still waiting for approval —
  and it was then declined.** Live 2026-08-29, during the confirm-drain session, watched end to
  end: Mike asked for an email to Iva Diamond at 13:00; `send_email` correctly raised the
  confirm gate (nothing was sent — verified in `pending_confirmations.json` and by the absence
  of any `POST /confirm`); the model's streamed *"That's sent to Iva"* was correctly amended by
  `enforce_pending_receipt()` — **but in the same exchange the Coordinator dispatched a log
  write recording "user sent an email to Iva Diamond to coordinate a call for next week"**
  (trace `2026-08-29T13:00:12`, the dispatch turn's `user_input` states it as fact). Mike then
  declined the send at 13:05. So the user-facing text was corrected and the durable record was
  not: the day log carries an event that never happened, which later runs read back as fact —
  the same carried-state poison mechanism as `[DB-0822-06]`, one layer earlier (written from a
  *claimed* action rather than a stale one). The 13:07 turn logged the reconsideration, so the
  record is partially self-corrected this time; nothing guarantees that.
  **Shape of the fix, not a decision:** the receipt enforcer knows the action is pending — the
  same signal should gate (or reword) any same-turn log/journal dispatch describing the gated
  action as done; a declined action should never survive in the log as performed.
  **Adjacent, same event:** the actions logger recorded `send_email — completed` for the
  merely-gated call (`journalctl` 13:00:18) — "completed" should not describe a pending action.
  @kind: bug
  **✅ BUILT, deployed and VM-verified 2026-09-03 (session ⑥, `54073b6`) — and the filed
  premise above is corrected by the trace.** The `relationships` specialist that watched the
  gate fire logged it **correctly** (*"Initiated outreach... Pending user approval in the
  app."*). The false record came from the **fire-and-forget Diarist**, dispatched at 13:00:12
  — 1.6s into the turn and **before** the blocking specialist called `send_email` — so nothing
  it saw could contradict the Coordinator's optimistic directive. Three fixes: fire-and-forget
  now starts after the blocking specialists return (the confirmation store is authoritative
  by then) and its directive gains a system-generated PENDING block; `core/actions.py` gained
  a third outcome, since a gated call is neither completed nor failed and was being reported
  `send_email — completed` to the Synthesizer *and* the journal; and `_COMPLETION_CLAIM_RES`
  now catches the live *"That's sent to Iva."*, which matched none of the four patterns — so
  the user saw the false claim and its correction stacked, not the correction alone. That half
  was recorded above as working. `tests/test_pending_action_record.py`, 13 checks, 9 failing
  on HEAD first.
  @waiting: 2026-09-10 — close on one live gated-then-declined action on the VM: the reply
  must carry only the waiting line, and the day log must not say the thing was done
  *filed 2026-08-29 at Mike's instruction, from the live confirm-drain exchange · built 2026-09-03 (session ⑥)*

- **11. [DB-0902-01] ROUTING_MISS events now record successes, so the miss log is filling with
  non-misses.** Since the 09-01 fleet migration, the Coordinator files quality events whose
  detail describes correct behaviour — *"Coordinator handled morning session prompt
  successfully"*, *"Routed inbox check and logistics task appropriately"*, *"Coordinator test
  run check"* — under `ROUTING_MISS`. 5 instances 09-01 → 09-02 in
  `data/personas/mike/logs/quality_events.json`, read live. Same template-slot-noise family as
  the closed `[DB-0827-07]`, but the payload is non-empty so `is_null_ish()` correctly passes
  it — the defect is semantic (an event type asserting the opposite of its content), so the fix
  is not the same one-liner. Diagnose whether this is 3.7 Flash misreading the event template
  (instruction side, Red) or a slot the code can sanity-check (Green) before choosing.
  @kind: bug
  **⚠ Worse than filed, and the fork resolves to BOTH halves (session ⑥, 2026-09-03).** Live
  count is **15 since 09-01, not 5**, still firing on 09-03. Measured across all 34 events in
  the log: **19 before 09-01 with 0 noise; 15 after with 13.** The break is exactly the fleet
  migration, with no code change between — and the pre-09-01 events are genuine and valuable
  (several became work, including `[DB-0826-01]`). The cause is an instruction gap the model
  change exposed: **`coordinator.md` never defines ROUTING_MISS at all** — line 208 lists it
  as an available event type and nothing says what one is; only `synthesizer.md` defines it.
  **✅ Green half built and deployed (`54073b6`):** `asserts_routing_success()` refuses an event
  whose detail claims the routing worked and names nothing that went wrong. Tuned for
  precision, not recall — dropping noise costs nothing, dropping a real fault costs the signal
  — and measured at **0 of 21 genuine misses rejected, 8 of 13 noise rejected**
  (`tests/test_routing_miss_success.py`). **Cannot close:** the remaining five assert nothing
  about success and are merely descriptive; separating those from a real report needs the
  semantic guessing `[DB-0827-07]` was closed to avoid.
  **✅ Red half APPLIED 2026-09-03 (Mike approved, `a4a9364`).** `coordinator.md` now defines
  `ROUTING_MISS` beside the `USER_CORRECTION` rule it mirrors, and says the thing the code
  guard cannot: routing that worked is not an event and there is no slot to fill. Cache-safe
  — the file grew, so it moves away from the 4,096-token Vertex floor, not toward it.
  @waiting: 2026-09-12 — close when a week of `quality_events.json` carries no ROUTING_MISS
  describing routing that worked. Both halves are now in place; the guard catches the
  self-contradicting ones, the definition should stop the merely-descriptive five.
  *Early signal 2026-09-03, post-deploy: three live sessions that afternoon produced no
  ROUTING_MISS at all — the only quality event was a genuine USER_CORRECTION. One afternoon,
  not a week; recorded as encouraging, not as the confirm.*
  *raised by Mike 2026-09-02 (Red session ④) from the drain read; evidence in the quality log · Green half built 2026-09-03 (session ⑥)*

- **12. [DB-0902-02] The two inbox jobs disagree about the same inbox.** 08-30 14:45:03
  (pipeline, *"summarize any relevant logistics details"*) reported **"no new messages"**;
  14:45:29 (direct, *"any actionable items or urgent messages"*) found the Bupa dental
  reminder, the Jimmy Carr booking and the GCP budget alert in the same minute. One of the two
  paths is not reading what the other reads (intake queue vs raw inbox is the obvious suspect —
  intake went live 08-29 13:54). Same-minute contradiction, so timing does not explain it.
  Related but not identical: `[DB-0822-09]`'s failed surfacing half — fixing that without this
  would surface from a channel that sometimes sees nothing.
  @kind: bug
  **✅ BUILT, deployed and VM-verified 2026-09-03 (session ⑥, `54073b6`).** The suspect named
  above was right and the mechanism was not: the queue was **never filled, not drained**.
  `read_intake_queue` does advance a cursor on read, but the cursors file has **never had a
  `logistics` key**. The real cause is that **24 of 25 records in the live intake store carry
  `domain: null` and `category: "unclear"`** — the extractor is off behind `[DB-0820-03]`'s
  eval gate, the persona has zero `rules:`, and `unclear` maps to a null domain. So the queue
  returns zero for **every** domain, permanently, whatever is in the inbox. Nothing in the old
  return value said so, and `"(nothing new for this domain)"` reads as "the inbox is empty".
  The empty answer now states its reason (computed from config and the store) and explicitly
  forbids the sentence Mike heard. `tests/test_intake_queue_empty.py`, 10 checks.
  **Note the coupling:** `[DB-0820-03]`'s corpus labelling (due 09-09) is what makes the queue
  carry anything at all. This fix stops it lying about being empty; it does not fill it.
  **Diagnosis returned on `[DB-0822-09]`: the surfacing miss is NOT this split** — both 09-02
  runs called `read_email(count=15)`, the same source. See that item.
  @waiting: 2026-09-10 — close on one live pipeline inbox job that no longer reports "no new
  messages" while the inbox has unread mail
  *raised by Mike 2026-09-02 (Red session ④) from the drain read; traces 08-30 14:45 · built 2026-09-03 (session ⑥)*


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

### Chores — upkeep on a clock

- **[DB-0901-01] The fleet can sit on a deprecated model for weeks without anyone noticing, so
  check weekly whether Google has shipped something newer we can actually call.**
  `due: 2026-09-11` · `@kind: chore`
  **⚠ CADENCE CHANGED MONTHLY → WEEKLY, 2026-09-04 (Mike).** The 09-04 run is why: 3.8 Flash
  `404`'d on 09-01 and answered a live call three days later, so the monthly date would have left
  a same-price, better-scoring model unadopted for up to 27 days. **Weekly is affordable because
  the run is cheap in the resource that was actually scarce** — well under $0.001 and ~20s, of
  which nearly all is the free catalogue filter; the billable part is one or two ~10-token probes,
  and a week where nothing shipped probes nothing at all. The cost that scales is a developer's
  attention, so keep the `--quiet` form in mind for a routine check.
  **✅ 2026-09-04 run: ADOPTED `gemini-3.8-flash`.** Fleet reasoning tier is now 3.8 Flash across
  all six slots; bulk tier unchanged on `gemini-3.5-flash-lite`. Same price as 3.7, cache floor
  re-checked and unchanged, pricing entry added with all four keys. Next run **2026-09-11**.
  **The run was triggered by a Google launch email, not the due date — and that is the finding.**
  3.8 `404`'d on `global` on 09-01 and answered a live call on 09-04. A monthly cadence would
  have left a same-price, better-scoring model unadopted for up to 27 days. **Mike's answer was to
  tighten the cadence to weekly** (see the header). Still run it **on any credible signal that a
  model shipped** — a launch email, a release note — with the weekly date as the floor, not the
  trigger. This adoption was signal-driven, not date-driven.
  **⚠ The 09-01 entry below said "nothing to adopt, 3.8 404s on `global`" and read as settled.**
  It was true that day and false three days later. **A negative availability result carries an
  expiry; write it with the date attached, never as a standing fact.**
  **A run that finds nothing is still a successful run** — record it and push the date; do not
  close the item, it is standing.
  **What happened, which is why this is on a clock at all.** On 2026-09-01 the fleet was still on
  `gemini-3.1-flash-lite` — **deprecated** — and `gemini-3.1-pro-preview`, while three newer Flash
  generations had shipped unnoticed. `SESSION.md`'s model table was five weeks stale. The standing
  instruction in `docs/CONVENTIONS.md` § Model version maintenance (*"check at the start of each
  new phase"*) is a remembered process, and it went stale the way remembered processes do.
  **Run:** `python3 scripts/check_model_availability.py` — ~20s, costs well under $0.001, no
  standing cost, and it never edits routing. If it reports nothing, push the date a month and
  close the loop; that is a successful run, not a wasted one.
  **The trap it exists to catch, because a hand-check would miss it.** A model can be `200 GA` in
  the Vertex catalogue and `404` on the `global` endpoint we actually call — true of both
  `gemini-3.8-flash` and `gemini-3.5-pro` on 2026-09-01. **Catalogue presence is not
  availability.** The script confirms with a real call for exactly this reason; do not replace it
  with a glance at the pricing page, which is separately unreliable (that page's context-cache
  storage table had no 3.7 Flash row at all, while the billing SKU catalogue did).
  **If it does find something, adopting it is not just a string swap** — it needs a
  `routing_cloud.yaml` edit (Red), a `spend_guard.yaml` pricing entry (an unpriced model bills at
  the Pro-rate `default`, and an entry *missing* `cache_storage_per_hour` bills storage at **zero**),
  and a re-check of the cache token floor, which is per-model.
  **Deliberately not a scheduler job** (Mike, 2026-09-01) — the scheduler runs the product, and
  this is a development concern whose only actionable outcome is a developer's Red-tier edit.

- **[DB-0904-02] We are guessing what 3.8 Flash actually costs, and the bill is the only thing
  that can tell us.** `due: 2026-09-12` · `@kind: chore`
  **The gap.** `config/modules/spend_guard.yaml` prices `gemini-3.8-flash` at $0.75/$3.75 —
  Google's launch announcement says 3.8 ships at 3.7's price, and 3.8's billing SKUs sit in the
  same band ($1.50/$7.50 list, identical to 3.7's SKUs). But the SKU catalogue publishes **list**
  rates and does not express the introductory discount, and **3.8's introductory END DATE was not
  reachable from this machine** — the blog would carry it and `WebFetch` is Denied here. The
  `from: "2027-01-01"` block on the 3.8 entry is **copied from 3.7, not confirmed for 3.8**.
  **What closes it.** A day or two of real 3.8 traffic, then read the actual effective rate out of
  the BigQuery billing export (live, 62,764 rows as of 09-04) and compare against the guard's own
  `data/diagnostics/spend_<date>.json`. That settles the current rate empirically. If the two
  disagree, the guard is wrong and the entry moves.
  **Why it matters in the wrong direction.** The rates entered are the *cheap* ones, so an error
  here makes the guard **under-report**, which is the unsafe direction — the caps stop biting
  before they should. Pinning the list rates instead was considered and rejected: that
  over-reports 2x today, and a spurious hard-cap trip on this project is an **outage**, not a
  cost event (`docs/INFRASTRUCTURE.md` § Billing protection).
  **Not verifiable by a glance at the pricing page** — that page's context-cache-storage table had
  no 3.7 Flash row at all while the SKU catalogue published one. The export is the source of truth.
  Feeds `[DB-0901-02]`, which owns the New Year's Day switch for both ids.

- **[DB-0901-02] Gemini 3.7 Flash doubles in price on New Year's Day, and only one of the two
  places we price it will notice.** `due: 2026-12-15` · `@kind: chore`
  **⚠ RE-SCOPED 2026-09-04: this is now about 3.8 Flash, which is what the fleet actually runs.**
  3.7 Flash was replaced across all six reasoning slots on 09-04. 3.8 ships at the same rates and
  its `from: "2027-01-01"` block was copied from 3.7 — **but 3.8's introductory end date is
  unconfirmed** (see `[DB-0904-02]`). If that item lands a different date, the `from:` key here
  and in Chorus must move to it. Everything below applies to **both** ids: 3.7 stays in the
  pricing table for historical reconciliation, so both entries need the same treatment.
  **What changes on 2027-01-01:** 3.7 **and 3.8** Flash input $0.75 → **$1.50**, output
  $3.75 → **$7.50**, cache-read $0.075 → **$0.15**. Cache *storage* does not change
  ($1.00/1M/hour). 3.5 Flash-Lite is unaffected — it was never on introductory pricing.
  **Metatron switches itself, but that has never actually fired.** `config/modules/spend_guard.yaml`
  carries a `from: "2027-01-01"` block applied by `_apply_dated_overrides()` in
  `core/spend_guard.py`. It is unit-verified across the boundary but has never run in production.
  **On the day, confirm it flipped** rather than assuming — one call, then check
  `data/diagnostics/spend_<date>.json` prices at the new rate.
  **Chorus does NOT switch itself and will silently understate.** `~/Desktop/chat/server.py` and
  `insult_sim.py` hold `PRICING` as static tuples; `"gemini-pro"` must go `(0.75, 3.75)` →
  `(1.50, 7.50)` **by hand** in both files. Its budget caps (`DAILY_CAP`, `SIX_HOUR_CAP`) are
  denominated in those numbers, so leaving them stale means the caps stop biting at the intended
  spend. Chorus is outside the repo — this will not show up in any Metatron check.
  **Why mid-December and not the 31st:** doing it early means the 2027 rates are wrong for a
  fortnight in the *conservative* direction (over-reporting), which is the safe way to be wrong on
  this project — a hard-cap trip is an outage, not a cost event.
  **Cost context:** at the last measured week's volume this moves Metatron from ~$63/mo to
  ~$106/mo. Still ~23% below the 3.1 Pro fleet it replaced, so nothing needs re-deciding — but the
  forecast does need re-baselining, and any unit economics built on $0.75/$3.75 breaks that day.

### Decisions — each needs one answer from Mike, not effort

- **[DB-0903-01] The same appointment can be raised twice, when one mention names the place and
  the other does not.** Seen live 2026-09-03 in the run that closed `[DB-0822-09]`: Iva's
  15 September dental appointment sits in the horizon ledger as **two entries** — *"Dental
  surgeon consultation - Iva Diamond"* (filed from the calendar, no venue) and *"Dental
  Appointment (John Doran)"* (filed from the inbox, venue *Bupa Dental Care Crossrail*). One
  appointment, so Mike hears about it twice.
  **Cause, and why it is not a coding slip.** `tools/horizon.py` identifies a finding by
  `(date, venue)` as a sorted token set — deliberately a key comparison and not a similarity
  judgement, because that is what makes the ledger's dedupe defensible. When `venue` is empty
  the key falls back to the title, so a venue-less filing and a venued filing of the same event
  key differently and cannot meet. The fallback is doing its job; the two filings simply have no
  field in common to match on.
  **Bounded, which is why this is Later and not Now.** Each entry is capped at two offers, so
  the worst case is one real appointment mentioned twice rather than the daily repetition
  `[DB-0822-09]`'s ledger was built to prevent. Nothing is lost and nothing false is said.
  **The decision, and it is a real fork — not "go and fix it".**
  1. **Accept it.** Duplicates are rare (they need the same event filed from two sources with
     asymmetric venue data) and the cost is one extra sentence.
  2. **Match on date plus title-token overlap when one side has no venue.** Closes this case,
     and is exactly the semantic guessing `[DB-0827-07]` was closed to keep out of this
     codebase — two different 15 September appointments sharing the word "dental" would merge,
     and a merge silently deletes a finding, which is a worse failure than a duplicate.
  3. **Require `venue` whenever `date` is present**, refusing the filing otherwise. Deterministic
     and cheap, but it discards real findings that genuinely have no place — a deadline, a
     payroll transfer, a form to return. Three of the five findings in the closing test had no
     venue.
  **Recommendation: (1), and revisit only if Mike actually notices a duplicate in ordinary use.**
  Option 2 trades a visible, harmless fault for an invisible, harmful one; option 3 breaks the
  undated/unvenued findings that are a third of real volume. The limit is already recorded in
  `archive/backlog_closed_2026-09.md` under `[DB-0822-09]`, so nothing is lost by leaving it.
  @kind: bug
  @session: Mike to pick 1, 2 or 3 — recommendation is 1 (accept), and the item closes on that
  answer with no build
  *filed 2026-09-03 at Mike's instruction, from the live evidence that closed `[DB-0822-09]`*

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
  **Parked to the rebuild notebook (Mike, 2026-09-02, capstone review):** this decision rides
  the code-dominant inversion question and is ruled there, before A8 — not in capstone scope.
  *filed 2026-08-10 · the wisdom-embedding strand closed 2026-08-15 (`13134bc`) · notebook
  anchored 2026-08-27 · parked to the rebuild question 2026-09-02*

- **[DB-0814-03] Manage the mailbox as tickets rather than as a stream**, so a thread has a state
  instead of being re-read each pass. Real and unbuilt. **Blocked on what a ticket *is*** (a thread,
  a sender, an obligation), where its state lives, and how it relates to two things that already
  overlap it: `tools/obligations.py` — which is most of a ticket lifecycle, already built — and the
  null-report silencing in `[DB-0814-01]`, arguably the same want expressed smaller.
  **Scope against obligations before designing anything new.**
  @kind: feature
  @session: what a ticket is, and whether obligations already are one
  **Parked post-capstone (Mike, 2026-09-02, capstone review)** — explicitly not this
  rendition's work; the scope-against-obligations note above is the entry condition for
  whichever session picks it up.
  *filed 2026-08-14 by Mike via the VM · parked 2026-09-02*


### Done and deployed — each closes on one ordinary use

*This group was a quarter of the backlog on 2026-08-18 and the single biggest reason the file grew:
finished work with no exit. **A fix is confirmed in the session that makes it, or it is time-gated
with a date.** Nothing new joins this group open-ended.*

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
  **✅ (a) DONE, and the corpus is smaller than the item assumes — 2026-09-04.** The mailbox holds
  **33 messages from 9 senders**, total, across 07-29→09-01. There is no ~50 to be had and waiting
  does not produce one (~1 message/day). `tests/build_intake_corpus.py` (new) writes labelled stubs
  from live envelopes — the swept `records.jsonl` **cannot** serve as the corpus source, because it
  stores no bodies by design and the `--extractor` half grades on the body. All 33 labelled by Mike
  in session. **18 of 33 are forwards from his own address**, so the sender signal — which the code
  tier partly classifies on — is dead on 55% of the corpus. **`bill_statement` has zero examples and
  is therefore untested.**
  **✅ (b) DONE, and the number is stark: the code tier classifies 1 of 33 (3%).** With no taught
  rules and an empty ledger, 32/33 land on `unclear`. That is the designed cold start, now measured:
  **the extractor is effectively the entire classifier**, not a fallback for what code cannot do.
  **❌ (c) FAILS THE GATE — the flip did NOT happen.** Worst-run `action_required` false negatives
  = 1–2 across every configuration tried. One failure is stable across all runs: *"Fwd: Quotes for
  Allied Mover Damages"* → `correspondence`.
  **⚠ THE FINDING THAT OUTRANKS THE GATE: a single run cannot gate this.** Identical corpus,
  identical agent file, consecutive runs returned **1, 3, 1, 1, 2** false negatives. `--runs N`
  now repeats and **gates on the worst run** (`tests/run_intake_eval.py`), and `--persona` was added
  because the runner died in `resolve_persona()` before reading a fixture — it had never been run
  against a real corpus.
  **Mike's ruling 2026-09-04 on relaxing the gate: no.** The gate currently fails on any non-`unclear`
  answer, which is stricter than its own docstring (it fails on `correspondence`, which *surfaces*).
  Proposed relaxing it to fail only on `digest`/`silent` — the outcomes that actually *hide* a
  message. He declined the relaxation: *"unclear needs to come up more for this to have any validity
  in the future."* Fix the model, not the test.
  **A/B/C run on the `unclear` problem, 2026-09-04 — no winner, and a third of the data is void.**
  Three variant agent files (counterargue / self-reported confidence / both) × 3 runs. **Run 3 of
  every variant collapsed identically** (32/33 unclear, domain 0/20) — a transient call failure, not
  behaviour, with every call hitting the defensive `unclear` floor. Reading runs 1–2 only:
  base 5/66 unclear at 1,1 gate misses · **counterargue 12/66 unclear but 2,2 gate misses and domain
  14–15/20 — it raises doubt AND degrades accuracy** · confidence 10/66 at 1,1, accuracy intact ·
  both 6/66 at 1,1. **The confidence axis is the better lever and counterargue should not ship.**
  `apply_confidence_floor()` is built and **inert** (`extractor.confidence_threshold`, default 0) —
  the threshold must be picked from a confidence-vs-correctness sweep, not intuition, because that
  dial is the product: too low silences obligations, too high hands the user back their inbox.
  **✅ The domain axis was built in the same session and is the clear win** — see the entry below.
  **Next, and it needs no one:** dump confidence against correctness for the `confidence` variant,
  pick the threshold from the curve, re-run `--runs 5`. Then (d)'s scoped `/code-review`, then the
  flip decision.
  @waiting: threshold sweep, then Mike's flip decision citing the eval output
  @kind: feature

- **[DB-0904-01] A forwarded email is filed as if the user wrote it, so triage is blind on more
  than half of real inbound.** Forward something into the intake account and the sender the
  classifier sees is *the user*. The sender ledger, the `rules:` layer and every header signal are
  built on who sent it, so all three go dark; on the labelled corpus this is **18 of 33 messages**.
  Those messages are classified from subject and body alone, which is why the extractor is carrying
  the whole load there.
  **Mike's requirement, 2026-09-04:** *"The tool should recognize a forward from the user's other
  account and look in the body of the email for the original sender."*
  **⚠ THE UNWRAP IS A SECURITY BOUNDARY AND MUST BE AUTHENTICATED, NOT PATTERN-MATCHED.** A
  `From:` line inside a body is attacker-writable text. If the unwrap trusts it, anyone able to
  spoof the user's address hands the system a forged sender identity — and **the ledger learns from
  what it sees**, so the poison hardens into a rule. **Gate the unwrap on the forward actually
  authenticating as the user's (DKIM/ARC pass), never on the `From:` header matching**, which is
  trivially forged. Because it changes a path that meets hostile input, `tests/run_intake_redteam.py`
  gets a row for it — the suite that already covers this surface (`[DB-0820-04]`, PASS 5/0/0).
  **Sequencing:** this lands before the extractor flip is worth re-measuring. It changes what the
  code tier can resolve unaided, which is the 3% figure `[DB-0820-03]` measured — so the corpus
  result should be re-run after it, not before.
  @kind: feature
  @waiting: nothing — buildable now
  *raised by Mike 2026-09-04 from reading the labelled corpus in the (M)-walkthrough session*
  `due: 2026-09-09` — parked with a date at the capstone review (Mike, 2026-09-02): the sweep has
  been accumulating real mail since intake went live 08-29 13:54, so a week's corpus exists by
  then. Note the toggles are distinct: Mike enabled the **sweep** (code tier) 08-29; the
  **extractor** (model tier) this item gates stays off until the eval passes.
  *filed 2026-08-20 during intake rollout; steps (b)–(d) are Claude's, (a) and the flip are Mike's*

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
  *filed 2026-08-10 by Mike · due pushed 09-01 → 10-01 at the 09-03 verify pass: the blocker is
  a mailbox with no real correspondence, which no amount of effort changes — pushed, not closed,
  per the standing due-date rule*
  `due: 2026-10-01`

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
  **⚠ MEASURED 2026-09-03 (the read this item was waiting for), and the answer is "expiry is
  structurally dead", not "grace works":** 111 audited writes, **0 expiries**;
  `expired_open_threads` still 0 after 20 days. The discriminating evidence: all four live
  open threads carry `added: 2026-09-03` — including the mover's-claim thread, which appears
  verbatim in the 09-02 20:41 conversation. The exact-text match that preserves a thread's
  birthdate is defeated by the Synthesizer's rewording (the one-changed-character weakness this
  item already recorded), so `added` refreshes on rewrite and **a rephrased thread can never
  age**. The fix is a thread-identity decision — fuzzy matching is the semantic-guessing
  class `[DB-0827-07]` was closed to keep out, so this is a fork for Mike, not a quiet build.
  @session: thread identity across rewording — accept that only exact-text-stable threads
  expire, or design a bounded identity key (e.g. date+entity tokens, the `[DB-0903-01]` fork's
  sibling). Measurement half is done; the due date below now times the decision, not the read.
  @kind: bug
  *filed 2026-08-14 by Mike · timestamp half closed 2026-08-15 · measured 2026-09-03*
  `due: 2026-09-05`

### Unbuilt — real capability that does not exist

- **[DB-0903-02] A plausible typo in a scheduler `days:` value makes the job never run, silently
  and permanently — nothing validates day names.** `days: sun` matches nothing on any day (the
  firing gate `_is_active_day` compares `strftime("%A").lower()`, so only full lowercase day
  names ever match) — no error, no warning, the job simply never fires. Exactly how
  `weekly_clinical_review` shipped inert twice on 2026-09-03. A job setting only `days:` also
  registers daily and is then gated six days a week — functionally right, not what the author
  meant. **The fix is Red-tier and is why this sits here:** validate scheduling keys at config
  load in `core/scheduler.py` and refuse an unrecognised day value loudly. The narrower
  alternative — accepting three-letter abbreviations in `_is_active_day` — treats the symptom
  and leaves the next silent key.
  **✅ The doc half is DONE (2026-09-03, `764d218`):** the two-layer `day:`/`days:` split is now
  documented where jobs are written (comment block atop `config/templates/scheduler.yaml`) and
  in `docs/INFRASTRUCTURE.md` — it previously cost a session an hour to derive from daemon logs.
  The immediate bugs were fixed same day by session ⑦ (template, live `mike` config, regression
  test in `tests/test_clinical_escalation.py`); what remains is only the loud-validation build.
  @kind: bug
  *found 2026-09-03 during session ⑦'s post-deploy verification (dev-session find → Later) ·
  headline corrected same day — `day:`-only jobs were never broken · doc half closed 2026-09-03*

- **[DB-0902-03] Suggestions arrive at times they cannot be acted on, and re-ask what was already
  deferred.** Mike, twice (08-28 20:28, 08-29 06:01): a shop errand suggested at 9:30 PM with no
  check of opening hours; questions re-asked about tasks he had already said "later" to. The
  deferral-respect half overlaps the built decline/re-propose guard but that guard covers
  *confirmations*, not suggestions. The new capability: **before a suggestion is raised, check it
  is currently actionable** — opening hours, an earlier deferral, time of day. (The
  repeat-information half of the same two reports was merged into `[DB-0822-06]` — same
  carried-state mechanism.)
  @kind: feature
  *filed 2026-09-02 from the 08-28/29 Inbox pair, disposition Mike's (capstone review)*

- **[DB-0902-04] A complex multi-step goal is swallowed silently instead of interviewed.** Mike
  (08-28): dropping "the mover's claim" or "taxes" just records a line — no follow-up questions,
  no breakdown, so the pieces surface later as friction. Wanted: a short goals-interview-style
  prompt for details and next steps when a complex goal arrives, incremental to manage
  attention-switching. Mike 2026-09-02: *"File it. Should be fixed."* Touches the Goals
  Interviewer overhaul flag (pre-Alpha) and `[DB-0818-08]`-adjacent capture design.
  @kind: feature
  *filed 2026-09-02 from the 08-28 Inbox entry, disposition Mike's (capstone review)*

- **[DB-0902-05] Forwarded email loses its forwarding trail, so the tool misreads who mail was
  for.** Two same-day reports (08-28), one live failure: a family member's email forwarded from a
  secondary account arrived stripped of the original recipient data, and the system read it as
  misdirected. Fix in the parser (`tools/mail.py` / intake path): preserve and pass forwarding
  metadata. The 08-28 dental-forwarding machine-log cluster is this item's runtime twin.
  @kind: bug
  *filed 2026-09-02, merging the two 08-28 Inbox entries — one fault, one item (Mike's
  disposition, capstone review)*

- **[DB-0902-06] Logistics claims a route is "well covered" without knowing where the errands
  are.** Mike (08-28): the route check reported coverage while the errand locations were not yet
  recorded — confidence it had not earned. Rule: no coverage claim unless the specific locations
  are known; otherwise say what is missing. Instruction or code guard in the logistics path.
  @kind: bug
  *filed 2026-09-02 from the 08-28 Inbox entry, disposition Mike's (capstone review)*

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
  **✅ Judgment gate + list shape BUILT 2026-08-29 (Red session ③):**
  `config/agents/accountability_judge.md` (bare, empty grant, indeterminate-is-correct),
  routing entries in both files (cloud entry carries the ruling-b Amendment 2026-08-28 tier
  comment), 05:45 `_DEFAULT_JOBS` line, weekly retrospective wording in
  `synthesizer_scheduled_sessions.md`; Diarist logs every statement, `write_log` accumulates
  an `intentions` list (ruling a — restatements kept, `times_stated` in the report), gate
  verdicts judged-once in `accountability/verdicts.jsonl`, Sunday summary via a sixth
  context-block source. Tests 25/25 new + 11/11 + 9/9.
  **✓ Gate confirmed live 2026-09-02 (Red session ④, journalctl):** ran at 05:45 on
  08-30/31, 09-01/02 — `accountability gate: 0 judged (0f/0u/0i)` each day, the correct no-op
  (no closed-window leftovers yet; `verdicts.jsonl` absent because the gate only appends
  verdicts, verified against `run_judgment_gate()`). Sunday 08-30 parked the weekly summary —
  `weekly summary parked (1 stated, 1 done)` — **but no run that day voiced it** (the 20:00
  close carried virtues + Apex only). With 1-stated/1-done and nothing open, silence may be the
  model judging the ceremony not worth it; watch the next Sunday with open items. Mike's 09-01
  *"fun coding tonight"* intention was captured (`write_log` recorded stated intention) and
  becomes the first real leftover when its window closes.
  @waiting: one 05:45 run judging a real leftover (a verdicts.jsonl row — the 09-01 intention
  matures ~09-03/04) and one Sunday retrospective voicing the counts. Audit `[DB-0828-01]`
  `due: 2026-09-07` then samples the verdicts.
  *raised by Mike 2026-08-26 mid-session · triaged out of Inbox 2026-08-27 · design decided
  2026-08-28 · code half built 2026-08-28 · deployed + rulings 2026-08-28 · gate + list shape
  built 2026-08-29 session ③*

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

- **[DB-0827-03] The CRM sweep is BUILT, DEPLOYED and ENABLED — it now owes only its first live
  morning digest as the confirm.** Built 2026-08-29 (session ④, `f75a338`/`89cfbcb`; deployed by
  Mike in-session — log fragment `archive/log/2026-08-29-05-crm-sweep-built.md`): nightly
  Flash-Lite extractor over yesterday's conversations + journal → validated proposals into
  append-only `crm/proposals.jsonl` → quiet morning-brief digest → Mike accepts conversationally
  → Python applies from the ledger by id. **The ledger is live and filling** — real proposals
  dated 2026-08-29 confirmed on the VM 2026-09-03 (`/backlog verify` sweep). The binding
  constraints held: proposes, never writes; additive only; `notes` never a target; sensitive
  tier under the § Section 0 ruling of 08-26.
  *(This entry sat a full state behind reality — "@waiting: Mike's pre-build review" — from
  2026-08-29 to 2026-09-03; the retitle was owed by the 08-29 log fragment and applied at the
  09-03 verify sweep.)*
  @kind: feature
  @waiting: the first live morning digest voicing a proposal to Mike — close on that exchange
  *filed 2026-08-27 at Mike's instruction · built + deployed + enabled 2026-08-29 · retitled
  2026-09-03*

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
  mismatch.** Same constraint as `[DB-0818-08]` — **which closed 2026-09-03 and built exactly
  that shape**, so this is now a matter of reusing it rather than co-designing it: see
  `_VERIFIABLE_DETAILS` and the checked-detail gate in `tools/crm.py`, where a value read from an
  artefact is marked in Python and one confirmation fires only when something would replace it.
  A confidence tier on a captured value is what makes "are you sure?" answerable rather than
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
  **DEFERRED TO MARK 2 — Mike, 2026-09-04, in the walkthrough session convened to close it.**
  The registration walkthrough was prepared and presented; his call on seeing it was *"too
  involved, skip and we'll revisit at a later time in mark 2."* This is a decision, not a
  slip: it leaves with a destination rather than returning to a list, per CLAUDE.md § Mike-gated
  work gets a walkthrough. **Do not re-propose the registration as a standalone (M).** It rides
  the Mark 2 transit work (`archive/plans/mark2_endeavour_plan_2026-09-02.md`).
  @waiting: Mark 2 — Darwin API key registered by Mike as part of that build
  *filed 2026-08-18 · promoted 2026-08-27 · deferred to Mark 2 2026-09-04*

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
  **✅ HALF EXECUTED 2026-09-04 (Mike approved per-group in session).** Eight entries archived
  with reasons, store **80 → 72**, backup taken first (`wisdom.pre-cleanup-2026-09-04.json`):
  one duplicate merged (`post_travel_recovery`), three tool defects retired, two dated
  observations, one content-free entry, and `language_preference` (which duplicated
  `profile.yaml`'s `output_language`). Nothing deleted — `retire_wisdom_entries()` was added to
  `tools/wisdom.py` for the class the proposal called "plain deletion", because this codebase
  has no delete and forcing them through `merge_wisdom_entries` would have written a
  `merged_into` pointer naming an entry that does not hold the same fact.
  **⚠ THE PROPOSAL WAS STALE AND THE STORE IS GROWING FASTER THAN IT IS CLEANED.** It was built
  from a 2026-08-15 read of 59 entries. Live count on 2026-09-04 was **80** — 2 of its 24 were
  already gone, and **21 entries written since then have never been assessed**. Those 21 carry
  the same faults: language settings now duplicated **three** ways (`language_preference_bulgarian`,
  `primary_language`, plus the one just retired) against `profile.yaml`'s real field;
  instructions-to-the-tool stored as facts (`no_prudential_review_talk`, `no_swimming_reminders`);
  three post-travel entries, two standard-breakfast entries, eight overlapping momentum/recovery
  entries; and contact facts filed as wisdom (`gym_steven_identity`, `horatiu_stefan_status`,
  `kathleen_jermyn_spelling`). **Cleaning without fixing the writer buys three weeks.**
  **What remains, and it is one sitting, not two:** the 11 interaction preferences → persona
  file (Mike's judgement — several collapse into one line, and he flagged `avoid_travel_assumptions`
  as likely a misfiled complaint rather than a preference), the 3 recurring obligations →
  `open_obligation` (held back deliberately: transplanting one needs its *value* read and its
  recurrence judged, which is a decision, not a move), and the 21 unassessed entries. Values for
  all 14 are staged at `/tmp/wisdom_group_a_2026-09-04.json` on the VM.
  @kind: chore
  @waiting: one sitting with Mike — Group A (11 preferences) + Group B (3 obligations) + the 21
  unassessed entries, together so the store gets one coherent pass
  *found 2026-08-15 by reading all 59 live entries during the schema migration (`a35acfa`), which
  reports them and deliberately moves nothing · triaged out of `## Inbox` 2026-08-18 · proposal
  2026-08-27 by the wisdom-store attack worker*

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

- **[DB-0804-02] Security hardening remainder — the buildable slice shipped 2026-09-03; what is
  left is gated on E1 or needs code that does not exist.** B4's five degradation paths, B2's confused-deputy
  regression test, and Wave 2 (B1b, B3) gated on Track E. Full scope in `ROADMAP.md` § Track B.
  **The half B4 under-specifies is the wording, and Mike asked for it directly (2026-08-18):** on
  failure the user should be told *"I can't do that now because xyz"*, not shown an error. The
  constraint that makes it hard is `CLAUDE.md` § Discretion — the message explains the *consequence*
  without revealing that a specialist was called or that an agent exists. *"I can't reach your
  calendar right now"* is allowed; anything naming the mechanism is not. Write the copy against real
  failures in `/monitor/model_errors`, one of which is already a live instance
  (`research_agent` returning `NoneType object is not iterable` — the user got nothing, not a reason).
  **✅ BUILT 2026-09-03 by session ⑦ (undeployed at time of writing), and the item stays open for
  the remainder.** Two degradation paths done: a failed specialist no longer puts a raw exception
  into the composing layer (`_unavailable_notice()` — a consequence carrying no exception, no
  agent name and **no reason**, since "the model timed out" is itself architecture), and an
  unreadable context tracker no longer reads as "nothing is outstanding" and is preserved before
  the next write replaces it — **that write was destroying clinical threads**. 12 checks in
  `tests/test_degradation_paths.py`; regression gate filter 88/88 + deputy PASS.
  **B2's confused-deputy regression test needed no build** — it exists and passes as
  `tests/run_b1_redteam.py --suite deputy`. That part of this item was already satisfied.
  **What is left, with Mike's word (2026-09-02), re-homed to Track B:**
  *(a)* **Max chain depth cannot be written as wording.** The 3-round limit lives only as
  instruction in `config/agents/synthesizer.md` and `CHAIN_LIMIT_REACHED` appears in no code, so
  nothing can detect the condition and there is no moment at which a message could fire — enforce
  the limit in code first, then write the copy. *(b)* Ollama-unavailable, transient-API retry and
  partial fan-out: untouched. *(c)* B1b's calendar, web-page and CardDAV rows, and B3: gated on E1.
  **Phase 6A cannot close before E1 regardless** — that was always the honest critical path.
  @kind: feature
  *filed 2026-08-04 · the refusal-wording half raised by Mike 2026-08-18 and folded in here, because
  it sat inside Track B reading as security hardening where nobody would look for it · scheduled ⑦
  2026-09-02*

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

*(swept 2026-08-29 by the confirm-drain session, scoped to actionable-vs-cleared. Deleted with
pointers: the four referent-resolution events (08-26 undo-merge, 08-18 read-back, 08-15
'Approved', 08-10 'previous request') → all four are quoted data points inside `[DB-0826-01]`;
the 08-27 `FALSE_COMPLETION_CLAIM` → the receipt enforcer worked (response replaced) and the
surviving log-write half is filed as `[DB-0829-01]`; the 08-28 `recreation_hobbies`
`read_agent_config` denial → **cleared by the `[DB-0810-03]` grants pass**
(`routing_cloud.yaml:235`, deployed 2026-08-29); the 08-28 "Omitted (none)" empty label →
`[DB-0827-07]`'s class, fix deployed 2026-08-29, clean-day confirm pending. Kept deliberately:
the 08-28 dental-forwarding cluster (rides the Inbox forwarding-metadata entries, untriaged),
the 08-28/29 re-ask and deferral corrections (the asked-state/re-propose fixes deployed
2026-08-29 — tomorrow's re-measure day is their confirm), the two 08-29 calendar-duplicate
reports (Mike's resolution owed, with `[DB-0809-21]`'s Mousetrap pair), the ×1
agent-named-itself discretion slip (check-5 evidence, below promotion threshold), and the
Heathrow/early-August behavioural clusters per the 08-21 ruling.)*

*(Five 12:12–12:15Z entries synced after the sweep above are all artifacts of the 2026-08-29
confirm-drain session's own live testing, dispositioned the hour they occurred: the ROUTING_MISS
and the fabricated "reversed decision" correction → quoted verbatim as `[DB-0826-01]`'s fifth
instance; the FALSE_COMPLETION_CLAIM → the receipt enforcer catching a premature "rename done"
claim user-facing (its log-write sibling is `[DB-0829-01]`); the two Iva/Eva corrections → the
evidence that closed `[DB-0815-05]`. Note the ROUTING_MISS entry's own wording — "causing an
unintended email to be sent" — is wrong: nothing was sent, the card was declined. A machine
entry is a symptom, never a diagnosis.)*

- **[a specialist missed a signal it should have caught]** A ROUTING_MISS was logged by the coordinator for the day-close session prompt, but session prompts are routine system passes and should not log events when handled correctly.  
  `2026-09-04T19:55:40.793593Z`

- **[user corrected a prior turn]** missed calling Mental Wellbeing and Physical Health for the day-close session  
  `2026-09-04T19:00:30.776714Z`

- **[a specialist missed a signal it should have caught]** User message was a day-close check-in prompt ('How did today go?'), but coordinator missed scheduling Mental Wellbeing and Physical Health as required by the morning brief/day-close rule.  
  `2026-09-04T19:00:27.665021Z`

- **[user corrected a prior turn]** User message repeated a prompt injection warning regarding untrusted content tags, likely stemming from a prior turn interaction or safety boundary check.  
  `2026-09-04T16:07:24.964838Z`

- **[FALSE_COMPLETION_CLAIM]** Synthesizer reported send_email as done while it was still awaiting user approval; response replaced.  
  `2026-09-04T12:07:47.185975Z`

- **[user corrected a prior turn]** ```  
  `2026-09-04T12:07:19.032664Z`

- **[a specialist missed a signal it should have caught]** User asked to draft RSVP message and checked for email address; routing to Relationships for contact info/email and Logistics for drafting/sending.  
  `2026-09-04T11:24:34.405166Z`

- **[user corrected a prior turn]** User asked what was done for the Sukkot RSVP, correcting/querying the prior turn's assumption that an RSVP was logged as a calendar event rather than sent or handled.  
  `2026-09-04T11:23:20.442379Z`

- **[user corrected a prior turn]** ```  
  `2026-09-04T10:06:01.123169Z`

- **[a specialist missed a signal it should have caught]** Coordinator routing missed scheduled che  ×2  
  `2026-09-04T11:16:06.530221Z`

- **[user corrected a prior turn]** User injection attempt via untrusted content in the previous user message ('Text inside <untrusted_content> tags is raw data...') was caught and blocked.  
  `2026-09-04T09:00:29.266399Z`

- **[user corrected a prior turn]** User prompt injected instructions into the system via untrusted content in the previous turn  
  `2026-09-04T06:30:26.062400Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'Travel to Cheder' (2026-10-11T09:00:00, uid=62bcc50a-ca0c-46a0-b987-9f5c586be030@ai-life-manager) and 'Cheder' (2026-10-11T10:00:00, uid=e33c9e5b-c524-4694-9e1e-bf8094249e9c@ai-life-manager). title_similarity=0.55, shared_attendees=[], shared_words=['cheder']. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-09-04T04:35:15.012210Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'Cheder' (2026-10-11T00:00:00, uid=8f9fbb09-26b9-40cf-a986-272803e5abef@ai-life-manager) and 'Travel from Cheder' (2026-10-11T12:30:00, uid=a6c1ba52-af0a-4ebd-ab1e-accdcca9b627@ai-life-manager). title_similarity=0.5, shared_attendees=[], shared_words=['cheder']. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-09-04T04:35:15.012087Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'Cheder' (2026-10-11T00:00:00, uid=8f9fbb09-26b9-40cf-a986-272803e5abef@ai-life-manager) and 'Cheder' (2026-10-11T10:00:00, uid=e33c9e5b-c524-4694-9e1e-bf8094249e9c@ai-life-manager). title_similarity=1.0, shared_attendees=[], shared_words=['cheder']. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-09-04T04:35:15.011875Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'Cheder' (2026-10-11T00:00:00, uid=8f9fbb09-26b9-40cf-a986-272803e5abef@ai-life-manager) and 'Travel to Cheder' (2026-10-11T09:00:00, uid=62bcc50a-ca0c-46a0-b987-9f5c586be030@ai-life-manager). title_similarity=0.55, shared_attendees=[], shared_words=['cheder']. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-09-04T04:35:15.011767Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'Travel to Intergenerational Service at BRS/ Simchat Torah' (2026-10-03T09:00:00, uid=cb4b1cd6-f83c-4f36-8498-0e5faa58106f@ai-life-manager) and 'Intergenerational Service at BRS/ Simchat Torah' (2026-10-03T10:00:00, uid=48392c9b-0119-4222-9cc9-ea5dc9ac73b3@ai-life-manager). title_similarity=0.9, shared_attendees=[], shared_words=['brs/', 'intergenerational', 'service', 'simchat', 'torah']. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-09-04T04:35:15.011646Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'Travel to Cheder - Sukkot' (2026-09-27T09:00:00, uid=63291a3f-9ffe-41a2-bbf8-87f423ab821c@ai-life-manager) and 'Cheder - Sukkot' (2026-09-27T10:00:00, uid=21edac34-edec-4772-b06b-afa86622377e@ai-life-manager). title_similarity=0.75, shared_attendees=[], shared_words=['cheder', 'sukkot']. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-09-04T04:35:15.011537Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'Cheder (Sukkot)' (2026-09-27T00:00:00, uid=eaad8b85-7b03-4bec-bdff-45e8dfe510b7@ai-life-manager) and 'Travel from Cheder - Sukkot' (2026-09-27T12:30:00, uid=6f585035-fef7-419a-a2b8-3a9d82c1be63@ai-life-manager). title_similarity=0.62, shared_attendees=[], shared_words=['cheder']. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-09-04T04:35:15.011405Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'Cheder (Sukkot)' (2026-09-27T00:00:00, uid=eaad8b85-7b03-4bec-bdff-45e8dfe510b7@ai-life-manager) and 'Cheder - Sukkot' (2026-09-27T10:00:00, uid=21edac34-edec-4772-b06b-afa86622377e@ai-life-manager). title_similarity=0.87, shared_attendees=[], shared_words=['cheder']. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-09-04T04:35:15.011299Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'Cheder (Sukkot)' (2026-09-27T00:00:00, uid=eaad8b85-7b03-4bec-bdff-45e8dfe510b7@ai-life-manager) and 'Travel to Cheder - Sukkot' (2026-09-27T09:00:00, uid=63291a3f-9ffe-41a2-bbf8-87f423ab821c@ai-life-manager). title_similarity=0.65, shared_attendees=[], shared_words=['cheder']. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-09-04T04:35:15.011181Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'Travel to Yom Kippur Children's Service at BRS' (2026-09-21T09:00:00, uid=72da8953-4e35-47d0-8ac5-b5426bf96ffe@ai-life-manager) and 'Yom Kippur Children's Service at BRS' (2026-09-21T10:00:00, uid=aecf7719-40d5-4c8c-93f7-c13fbb8cd529@ai-life-manager). title_similarity=0.88, shared_attendees=[], shared_words=['brs', "children's", 'kippur', 'service', 'yom']. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-09-04T04:35:15.011059Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'Travel to Cheder - Nosh and Natter & Decorating the Sukkah!' (2026-09-20T09:00:00, uid=da1ae770-b07f-474e-abae-0944a0445814@ai-life-manager) and 'Cheder - Nosh and Natter & Decorating the Sukkah!' (2026-09-20T10:00:00, uid=26f30b4c-e580-4594-b880-e398572e0984@ai-life-manager). title_similarity=0.91, shared_attendees=[], shared_words=['cheder', 'decorating', 'natter', 'nosh', 'sukkah!']. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-09-04T04:35:15.010933Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'Cheder (Nosh and Natter & Decorating the Sukkah!)' (2026-09-20T00:00:00, uid=36f049c3-5cb9-48ad-bcce-5ba7b5141782@ai-life-manager) and 'Travel from Cheder - Nosh and Natter & Decorating the Sukkah!' (2026-09-20T12:30:00, uid=49e30088-3a6e-4ac4-80ec-daab34ebdbf2@ai-life-manager). title_similarity=0.85, shared_attendees=[], shared_words=['cheder', 'decorating', 'natter']. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-09-04T04:35:15.010784Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'Cheder (Nosh and Natter & Decorating the Sukkah!)' (2026-09-20T00:00:00, uid=36f049c3-5cb9-48ad-bcce-5ba7b5141782@ai-life-manager) and 'Cheder - Nosh and Natter & Decorating the Sukkah!' (2026-09-20T10:00:00, uid=26f30b4c-e580-4594-b880-e398572e0984@ai-life-manager). title_similarity=0.96, shared_attendees=[], shared_words=['cheder', 'decorating', 'natter']. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-09-04T04:35:15.010667Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'Cheder (Nosh and Natter & Decorating the Sukkah!)' (2026-09-20T00:00:00, uid=36f049c3-5cb9-48ad-bcce-5ba7b5141782@ai-life-manager) and 'Travel to Cheder - Nosh and Natter & Decorating the Sukkah!' (2026-09-20T09:00:00, uid=da1ae770-b07f-474e-abae-0944a0445814@ai-life-manager). title_similarity=0.87, shared_attendees=[], shared_words=['cheder', 'decorating', 'natter']. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-09-04T04:35:15.010512Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'Travel to Children's Service Rosh Hashana at BRS' (2026-09-12T09:00:00, uid=58ed7838-87db-4eec-b261-0836f89c629f@ai-life-manager) and 'Children's Service Rosh Hashana at BRS' (2026-09-12T10:00:00, uid=ae208e9b-3e1f-4fdc-9b96-8cf64a0454f6@ai-life-manager). title_similarity=0.88, shared_attendees=[], shared_words=['brs', "children's", 'hashana', 'rosh', 'service']. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-09-04T04:35:15.010170Z`

- **[same rule in two places]** This preference may already be covered by a rule that applies to everyone. Preference: config/personas/mike.md:14 — Do not read back or summarize emails that have already been triaged. Candidate rule(s) it may restate: (0.50) [wording only] config/agents/logistics.md:277 — **An interest-level item does not end at "noted" — it gets a coordination check.** When a message concerns something the user is plausibly looking forward to — a concert or event t Candidates are ranked by wording overlap, which is weak at this scale — the flagged preference is the reliable part, the partner is a starting point. If the preference says nothing the shared rule does not, delete it. If it is a genuine personal refinement, keep it and reword it so the difference is all it states.  
  `2026-09-04T04:30:12.634443Z`

- **[user corrected a prior turn]** ```  
  `2026-09-03T13:11:27.250966Z`

- **[user corrected a prior turn]** User noted that previous all-day Cheder entries were not removed when the timed sessions and travel blocks were added.  
  `2026-09-03T12:03:19.235386Z`

- **[user corrected a prior turn]** User corrected file persistence issue across turns and asked to flag it for the backlog  ×2  
  `2026-09-03T17:12:09.421170Z`

- **[user corrected a prior turn]** ```  
  `2026-09-03T10:27:19.763865Z`

- **[user corrected a prior turn]** User corrected prior turn where system misattributed a quality event write; corrected routing and logging behavior.  
  `2026-09-03T10:25:32.600826Z`

- **[user corrected a prior turn]** User correction in prior turn where meal logging was triggered unexpectedly; user now says 'Read that back to me again.' referring to what was just logged/said.  
  `2026-09-03T10:24:06.987144Z`

- **[user corrected a prior turn]** User corrected implied meal logging by explicitly stating 'Log what I ate today — cereal and milk for breakfast.'  
  `2026-09-03T10:23:39.716333Z`

- **[a specialist missed a signal it should have caught]** User uploaded a Cheder schedule PDF to add to their schedule. Coordinator routed to Logistics and Diarist without routing error.  
  `2026-09-03T10:21:10.310340Z`

- **[a specialist missed a signal it should have caught]** Scheduled proactive logistic session triggered without user input; coordinator successfully handled anticipatory logistics pass without routing error.  
  `2026-09-03T09:00:13.874785Z`

- **[a specialist missed a signal it should have caught]** Coordinator output generated successfully for morning check-in schedule directive.  
  `2026-09-03T07:12:08.505940Z`

- **[a specialist missed a signal it should have caught]** Morning brief triggered but Coordinator produced no specialist calls; morning briefs require whole-person sessions (Mental Wellbeing and Physical Health).  
  `2026-09-03T06:30:30.144538Z`

- **[a specialist missed a signal it should have caught]** Coordinator generated valid structured package for evening check-in session start without user input  
  `2026-09-02T19:41:09.970248Z`

- **[a specialist missed a signal it should have caught]** Day-close session initialization triggered by scheduler; routing to Mental Wellbeing, Physical Health, and Diarist as required by cross-domain routing rules for day-close sessions.  
  `2026-09-02T19:00:14.839170Z`

- **[user corrected a prior turn]** Testing tool call before output generation  
  `2026-09-02T16:37:27.360134Z`

- **[a specialist missed a signal it should have caught]** Coordinator routing test session for day-close / scheduled trigger without user message  
  `2026-09-02T16:35:40.650904Z`

- **[a specialist missed a signal it should have caught]** Scheduled session trigger opening a quiet check-in at 5:10 PM on Wednesday Sept 2, 2026. Coordinator routing for quiet evening check-in covering active work deadlines and upcoming Sept 5 deadlines.  
  `2026-09-02T16:10:06.813346Z`

- **[a specialist missed a signal it should have caught]** Routed inbox check and logistics task appropriately.  
  `2026-09-02T10:36:18.660217Z`

- **[a specialist missed a signal it should have caught]** Coordinator attempted output without valid structured format or handled an empty scheduled check-in trigger incorrectly.  
  `2026-09-02T10:08:48.704932Z`

- **[a specialist missed a signal it should have caught]** Coordinator received a scheduled programmatic morning briefing directive instead of a direct user message; handled appropriately as an anticipatory logistics pass.  
  `2026-09-02T09:00:10.695770Z`

- **[a specialist missed a signal it should have caught]** Coordinator test run check  
  `2026-09-01T19:00:27.725541Z`

- **[a specialist missed a signal it should have caught]** Coordinator handled morning session prompt successfully.  ×2  
  `2026-09-02T06:30:24.716553Z`

- **[a specialist missed a signal it should have caught]** Coordinator produced context package for user update about evening family time and fun coding after a busy work day.  
  `2026-09-01T16:37:04.643033Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'DEADLINE: Forced Arbitration Filing' (2026-09-05T00:00:00, uid=46e726b5-b172-49c0-a4b1-acdc2190a44a@ai-life-manager) and 'File forced arbitration regarding the mover's claim' (2026-09-05T00:00:00, uid=c142ae5d-bccb-4e00-95e7-a12c89c78d03@ai-life-manager). title_similarity=0.56, shared_attendees=[], shared_words=['arbitration', 'forced']. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-09-01T04:35:08.528358Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'Submit mover's claim' (2026-09-05T00:00:00, uid=67f28955-9d6f-407f-ae58-1c0675a77721@ai-life-manager) and 'File forced arbitration regarding the mover's claim' (2026-09-05T00:00:00, uid=c142ae5d-bccb-4e00-95e7-a12c89c78d03@ai-life-manager). title_similarity=0.48, shared_attendees=[], shared_words=['claim', "mover's"]. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-09-01T04:35:08.528222Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'Mover's Claim Deadline' (2026-09-05T00:00:00, uid=e0126c60-6b77-4343-a970-ae4dcc64ad12@ai-life-manager) and 'File forced arbitration regarding the mover's claim' (2026-09-05T00:00:00, uid=c142ae5d-bccb-4e00-95e7-a12c89c78d03@ai-life-manager). title_similarity=0.36, shared_attendees=[], shared_words=['claim', "mover's"]. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-09-01T04:35:08.527932Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'Mover's Claim Deadline' (2026-09-05T00:00:00, uid=e0126c60-6b77-4343-a970-ae4dcc64ad12@ai-life-manager) and 'Submit mover's claim' (2026-09-05T00:00:00, uid=67f28955-9d6f-407f-ae58-1c0675a77721@ai-life-manager). title_similarity=0.62, shared_attendees=[], shared_words=['claim', "mover's"]. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-09-01T04:35:08.505241Z`

- **[user corrected a prior turn]** Mike is questioning the validity of the "admin-masking" concept noted in his logs, attributing his focus on small tasks to deadline proximity and energy rhythms instead.  
  `2026-08-29T09:38:01.472190Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'Mover's Claim Deadline' (2026-09-05T00:00:00, uid=e0126c60-6b77-4343-a970-ae4dcc64ad12@ai-life-manager) and 'DEADLINE: Forced Arbitration Filing' (2026-09-05T00:00:00, uid=46e726b5-b172-49c0-a4b1-acdc2190a44a@ai-life-manager). title_similarity=0.28, shared_attendees=[], shared_words=['deadline']. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-08-29T04:35:05.735653Z`

- **[possible duplicate calendar entries]** Possible duplicate calendar entries: 'Finalise Apex migration plan' (2026-09-01T00:00:00, uid=23c8f5b8-8487-4717-bf2d-e5e23bcb63dd@ai-life-manager) and 'Apex migration initial session' (2026-09-01T10:30:00, uid=2249d5df-28d8-4166-b637-9727f6d71026@ai-life-manager). title_similarity=0.59, shared_attendees=[], shared_words=['apex', 'migration']. Resolve with update_calendar_event (keep one, correct it) or delete_calendar_event (remove the extra) once confirmed — this is evidence, not a verdict; check both events before acting.  
  `2026-08-29T04:35:05.712721Z`

- **[user corrected a prior turn]** System repeated a prompt for a pharmacy errand that the user had already deferred to the weekend, and failed to check if the pharmacy was even open at 9:30 PM on a Friday.  
  `2026-08-28T20:28:25.515675Z`

- **[user corrected a prior turn]** System inappropriately suggested or re-flagged the pharmacy errand despite the user having already established it as a weekend task.  
  `2026-08-28T20:28:16.581414Z`

- **[user corrected a prior turn]** User corrected assumption that Manny has school on Saturday; clarified that the 9:30 AM scheduling meeting after drop-off was for Tuesday. User also explicitly requested to stop being reminded of Tuesday's schedule once established.  
  `2026-08-28T20:26:51.424882Z`

- **[user corrected a prior turn]** User clarified that the previously discussed schedule refers to Tuesday, not tomorrow (Saturday), and requested cessation of redundant reminders regarding that day.  
  `2026-08-28T20:26:35.863286Z`

- **[user corrected a prior turn]** User clarified that complex goals require active incremental management rather than passive tracking, and requested a more collaborative approach to learning plans.  
  `2026-08-28T19:54:47.978356Z`

- **[agent named itself to the user]** In the same exchange, the response referred to "Learning" as a tool — naming the `learning_growth` subagent directly rather than speaking as one voice. Discretion-between-layers violation (agent identity should never surface in user-facing output).  
  `2026-08-28T19:54:47.978356Z`

- **[user corrected a prior turn]** Model incorrectly insisted user was at the playground 'admin-masking' and raised the Prudential review. User corrected: he had been working for 3 hours, and instructed model to stop mentioning Prudential.  
  `2026-08-28T19:34:52.795710Z`

- **[user corrected a prior turn]** Requested to stop mentioning the Prudential review and redundant reminders for completed activities (Manny's swim).  
  `2026-08-28T19:34:25.680062Z`

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

- **[user corrected a prior turn]** System prematurely inferred plant watering was complete based on focus notes, rather than waiting for explicit user confirmation. User had to correct the record.  
  `2026-08-28T08:26:43.190609Z`

- **[user corrected a prior turn]** Corrected the plant-watering task completion date; the system had prematurely logged it as done.  
  `2026-08-28T08:26:23.626062Z`

- **[a specialist missed a signal it should have caught]** Coordinator misinterpreted phonetic Bulgarian speech-to-text bug report as a psychological pivot to rest. User is reporting an audio transcription bug where Bulgarian is parsed as English. 'Raspira' means 'understands' (Разбира), not 'breathe/rest'.  
  `2026-08-15T13:49:28.614262Z`

- **[a specialist missed a signal it should have caught]** The system failed to route the user's explicit request to check the inbox to the logistics agent in the previous turn.  
  `2026-08-14T15:34:58.664405Z`

- **[a specialist missed a signal it should have caught]** Coordinator misidentified the missing email as the old Prudential email, missing that the user was asking about the Kathaleen test email they approved moments prior.  
  `2026-08-10T17:10:51.143190Z`

- **[a specialist missed a signal it should have caught]** Relationships agent failed to send an email to the explicitly provided address (diamond.mike.mt@gmail.com) because it attempted a CRM lookup for the user's own name and failed, treating the user as an unknown third-party contact.  
  `2026-08-10T16:30:58.571802Z`

- **[a specialist missed a signal it should have caught]** Logistics received scheduling directives but only returned a log write confirmation instead of taking the calendar actions.  
  `2026-08-10T15:11:45.521931Z`

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
