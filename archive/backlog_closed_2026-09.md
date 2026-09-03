# Closed Backlog Archive — 2026-09

**Items closed in September 2026, with the evidence that closed them.** Rolls monthly;
the previous file is [`backlog_closed_2026-08.md`](backlog_closed_2026-08.md).

**Search this before re-filing anything.** A closed item is removed from
[`../DEV_BACKLOG.md`](../DEV_BACKLOG.md) entirely — this is where its proof lives, and roughly a
third of what has looked open in the past turned out to be already fixed.

---

## ✅ [DB-0822-09] Email was processed and then thrown away — closed 2026-09-03

**Closed 2026-09-03, on live evidence, after three iterations in one day.** The most expensive
specialist by input volume was producing nothing the user saw: on 2026-08-22 `logistics`
ingested 397,216 tokens across two inbox jobs and what reached Mike was one due date. The
coordination half was built 2026-08-29; the **surfacing** half failed its first live test on
09-02 and is what closed here.

### The 09-02 failure, and what it was not

A genuinely interest-level email — Death Cab for Cutie, Troxy, 26 September — arrived. The
11:37 `logistics` run built exactly the right package: `HORIZON_ITEMS` carried it,
`COORDINATION_OPPORTUNITIES` attached real legs. **The user-facing 11:36 run said only** *"Your
focus window remains clear for the Apex migration delivery."*

This was suspected of being the `[DB-0902-02]` intake-queue split. **It was not**, and ruling
that out mattered: both runs called `read_email(count=15)` — the same source. `logistics`
produced a 536-token package, the Synthesizer received 21,630 input tokens including it, and
emitted 177 words about something else. The loss was entirely downstream.

### Three iterations, because the first two were live-tested and found wanting

1. **An injected must-deliver block, no ledger — killed before it was built.** Mike's question
   (*"how would the code know whether something is of interest?"*) forced the scoping that
   found it. Code never decides interest — `logistics` does, and across the three runs where
   specialist output survives in traces that judgement is sound (8 findings, 0 junk). But
   Jimmy Carr appears in **all three** of those runs and the dental appointment in two, so
   guaranteed delivery with no record of what was already said would have told Mike about the
   same comedy show daily until 13 September. That is `[DB-0822-06]`'s carried-state failure
   through a new channel, and **worse than the silent drop it replaces** — the Synthesizer's
   dropping was doing double duty as the fault *and* the noise filter.
2. **`HORIZON_ITEMS` as a JSON template slot — built, deployed, and inert.** The live test
   passed on the reply and failed on the ledger: every item reached Mike and
   `data/personas/mike/horizon/ledger.json` did not exist. `logistics` had emitted no
   `HORIZON_ITEMS:` line at all — conversational markdown with none of its documented output
   format — having emitted the full block the previous day on the same model. **Output-format
   adherence varies run to run: a template slot is not a channel, it is a request.**
   *Recorded because it very nearly closed on the wrong evidence — the reply contained every
   item the backlog named, and only a missing file contradicted it.*
3. **`record_horizon_item` as a tool call — what shipped.** Structured by construction: it
   cannot be replaced by prose, its arguments cannot be malformed and silently ignored, and a
   refusal is visible. Already the codebase's answer wherever a relay must not be lost
   (`write_quality_event`, `open_obligation`).

### The evidence that closed it

All on the VM, 2026-09-03, after deploy:

- **The tool fires and the ledger fills.** A direct `--agent logistics` run filed five findings.
  A direct run does not pass through `_file_horizon_items`, so those entries **can only** have
  come from the tool call — which is what made this decisive rather than suggestive.
- **The Synthesizer delivers them unprompted.** A bare *"How is my week shaping up?"* returned
  all five: both 09-05 deadlines, the Maria meeting, Rosh Hashana, the dental consultation.
- **Offer accounting is correct.** `offers=1` after that session, not 2 — the window collapsed
  the Coordinator's and Synthesizer's separate context loads into one charge, as designed. A
  later session took the same batch to `offers=2`, so the count increments across sessions and
  the batch exhausts next time it would be shown.
- **The 09-02 case itself now files and lands.** A plain *"Check my inbox and summarize any
  relevant logistics details"* — the exact failing directive — filed four new findings
  including **Death Cab for Cutie @ Troxy, 2026-09-26**, and the reply carried all of them.
  This needed one more fix to get there: filing was happening only when the directive named
  the horizon scan, so `logistics.md` now files on **every** directive (`7aa1f2a`).

### Built

`tools/horizon.py` (ledger, `(date, venue)` identity, context block, `record_horizon_item`),
the parser and both pipeline wirings in `core/orchestrator.py`, grants in both routing files,
`logistics.md`. `tests/test_horizon_ledger.py` — 29 checks.

**Two placement decisions the tests pin against source**, because neither is visible in
behaviour until a finding has already been lost: the offer is charged **where the block is
served**, not once per turn from the close-out (a finding filed mid-turn was never in the block
that turn built); and the block is built **after** the sign-off veto (on "over and out" the
Synthesizer never runs).

**The dedupe key is a sorted token set, and that was found by test, not review.** The first
version normalised the venue to a string, so `"The London Palladium"` and
`"the london palladium, London"` did not match — the exact case the design exists for.

### Known limit, carried out of the close deliberately

**An item filed without a venue does not dedupe against the same item filed with one.** Seen
live in the closing test: *"Dental surgeon consultation - Iva Diamond"* (2026-09-15, no venue)
and *"Dental Appointment (John Doran)"* (2026-09-15, Bupa Dental Care Crossrail) are one
appointment held as two entries, because the first keyed on its title and the second on its
venue. Cost is bounded — Mike may hear about one real appointment twice, each capped at two
offers — and it is not the failure this item was about. **Closing anyway rather than widening
the key**, because matching a venue-less item against a venued one by title similarity is the
semantic guessing `[DB-0827-07]` was closed to keep out of this codebase. **Filed at Mike's
instruction as `[DB-0903-01]`** (Later § Decisions) — a three-way fork with a recommendation to
accept it, closing on his answer rather than on a build.

---

## ✅ [DB-0820-01] The spend caps are temporarily too high — brought back down on 2026-09-01

**Closed 2026-09-01.** The GCP budgets were reverted from the temporary **$150/$250** to
**$100/$175** at the September calendar reset, exactly as the item specified.

**What was done, and verified live:**

- `gcloud billing budgets update` on both budgets on billing account `013F3D-66B5CD-955A3A`:
  *Metatron Soft Cap (stops VM)* `150 → 100`, *Metatron & Multi-Model Budget* (hard,
  disables billing) `250 → 175`.
- **The soft cap was lowered first**, so the intermediate state was $100/$250 — a wide gap —
  rather than $150/$175, a $25 gap. The item's "do not lower the soft cap alone" warning is
  about the *gap*, and the gap can be squeezed by the order of a reduction just as easily as
  by a bad choice of numbers.
- Re-read from GCP after the change: `175` and `100` USD. Confirmed, not assumed.

**The condition the revert was gated on was met.** The item said "$100/$175 unless a
reconciliation says otherwise". Two reconciliations said the opposite of otherwise: the
`[DB-0822-01]` reconcile passed five consecutive post-deploy days at billed ÷ estimated
1.02×–1.17× (2026-08-27), and the 2026-08-29 breakdown showed real `mike`-persona use at
~$1.50–2.00/day, with the alarming 08-27/08-28 totals (~$9.5/~$8.7) driven by development test
suites — one hour of A4 + red-team runs cost $6.47.

**The live consequence to expect, stated so it is not read as a regression:** a heavy testing
day can still trip the $100 soft cap. That is the control working as designed, and recovery is
`gcloud compute instances start metatron-vm` — about 60 seconds. The product itself has ample
headroom.

**Also fixed in the same pass, because it is the same defect the item warns about.** The item
says to read the values from `docs/INFRASTRUCTURE.md`, "never from a script comment
(`metatron-vm-override.sh` was stale for months)". Three live files were still asserting
`$70/$150` — stale through two raises *and* this revert:
[core/spend_guard.py](../core/spend_guard.py) (Red tier, comment only),
[config/modules/spend_guard.yaml](../config/modules/spend_guard.yaml), and
[infra/stop-vm/main.py](../infra/stop-vm/main.py). None of them *read* the numbers; all three
merely restated them. **The fix is to stop restating: each now names the cap by what it does
and points at the source of truth.** The two sub-headings inside
`docs/INFRASTRUCTURE.md` § Billing protection did the same thing and got the same treatment —
the table is now the only copy of the numbers in the section that owns them.

*Filed 2026-08-20 by Mike. Closed 2026-09-01 via `/fix`.*

## ✅ [DB-0822-08] Nothing is ever proposed — only reported — closed on the re-measure, Mike's ruling 2026-09-02

**Closed 2026-09-02 (Red session ④, Mike present), on the one-scheduled-run-day re-measure the
item itself demanded.** Baseline (2026-08-22): Apex raised 6-of-9 runs, Prudential 7-of-9,
**zero proposals attached all day**. Re-measured over all 9 scheduled runs of 2026-08-29 —
the first full day on the post-audit `synthesizer.md` (`6451b51`, deployed 08-28 evening):

- **Repetition collapsed:** Apex raised substantively in 2 runs; Prudential raised **zero**
  times (resolved — the corollary "an item that cannot be acted on is not raised" held).
- **Proposals attached in 3 of 4 substantive raises:** 15:13 *"did you want to map out those
  mornings for the mover's claim and payroll next week?"*; 18:14 *"Did you want to tee anything
  up for [the Apex migration] tonight?"*; 21:15 the rest/admin-masking observation with a direct
  question. The one miss: 20:43 named Apex "most time-sensitive" and offered nothing.
- **No fix was written.** Option 3 of the 08-29 handoff ("if the post-audit file now proposes,
  close on the evidence and write nothing") is what Mike ruled. The instruction-fix option was
  recommended against on the item's own reasoning; the structural per-run gate design remains
  written in `archive/handoffs/2026-08-29-re-measure-and-0822-08-decision.md` if ever needed.

**Named residual:** the measured day ran on `gemini-3.1-*`; the fleet moved to 3.7 Flash /
3.5 Flash-Lite on 09-01. Adherence on the new models is unmeasured — if proposal behaviour
degrades, one scheduled-run day re-scores it against these numbers.

*Filed 2026-08-22 by Mike · re-measure specified 2026-08-27 · measured and closed 2026-09-02.*

## ✅ [DB-0809-02] One unfinished ritual arrives as three or four separate messages — confirmed dead on the 08-29 scheduled-run day

**Closed 2026-09-02.** All three decided halves (focus-rule-on-nothing-new, asked-state memory,
ritual ownership — built `6451b51`, 33/33 tests) plus the Red Synthesizer line
(live at `config/agents/synthesizer.md:72`) were confirmed against the full 08-29 scheduled-run
day, and held through 08-30 → 09-01:

- **Empty-delta runs short:** all four low-delta runs (07:01, 10:00, 10:31, 10:32) were 1–2
  sentences. Baseline's emptiest run was its longest at 1,778 chars.
- **Same unanswered question once:** sleep/steps asked 07:01, answered by Mike 10:33, never
  re-asked in between (baseline: asked in 5 runs, never answered).
- **Virtues once, in the right place:** full 13-virtue list exactly once per day, at the 20:00
  `evening_close`, on every day read (08-29/30/31, 09-01). Baseline: 4×/day.

**One gray instance, logged as a watch, not a reopen:** the 08-29 20:43 email-check run chased
the evening ritual (*"we still have your food log and the 13 virtues to capture"*) — within the
built max-1/day re-ask cap, but a scheduled job continuing a ritual not its own. It did not
recite the list; it recurred nowhere in four days read.

*Filed 2026-08-09 · rewritten twice as measurement inverted it · decided 2026-08-28 · built
2026-08-28 · confirmed on live traces and closed 2026-09-02.*

## ✅ [DB-0822-05] The journal records days you never spoke — both confirm halves landed

**Closed 2026-09-02.** `has_real_user_turn()` (built `e6bde3d` 2026-08-27) gates the Diarist
dispatch. Both halves of the @waiting condition, verified live off the VM:

- **Scheduler-only days journal nothing:** 08-30 and 08-31 ran 15–16 traces each, none of them
  real Mike speech — `data/personas/mike/journal/` holds **no file for either day** (listing
  jumps 2026-08-29 → 2026-09-01).
- **An answered check-in still journals:** Mike answered the 08-29 07:01 check-in at 10:33; the
  08-29 journal carries that entry (walk with Iva, family breakfast) and only real user
  statements — no scheduler prompt text, no assistant monologue.

*Filed 2026-08-22 by Mike · built 2026-08-27 · both halves confirmed live 2026-09-02.*

## ✅ [DB-0827-07] Empty "CLARIFICATION_NEEDED:" quality events — clean since the deploy

**Closed 2026-09-02.** The `is_null_ish()` bare-label fix (built `24dabae` 2026-08-27, deployed
2026-08-29) needed one day with no new empty-label events. It got four: 11 quality events
landed 08-30 → 09-02 (read live from `data/personas/mike/logs/quality_events.json`, 354 lines
total) and **none is an empty template label** — the class produced 33 junk events at 3–5/day
before the fix. *(The 11 include ROUTING_MISS entries whose detail describes successes — a
different noise flavour, reported to Mike in-session rather than filed, per the filing rule.)*

*Filed 2026-08-27 from the deep-run machine sweep · built same day · clean-day confirm ×4
2026-09-02.*

## ✅ [DB-0827-01] Declining a confirmation does nothing — the 08-29 live decline stayed declined

**Closed 2026-09-02.** The decline path (`0f8f528`) and re-propose guard (`4cc9e3e`) passed
their first live exercise end-to-end:

- The declined Iva email sits in `declined_confirmations.json` (`declined_at` = 2026-08-29
  13:05:53, matching the live decline); `pending_confirmations.json` is `{}`.
- **Nothing re-raised it through the next scheduled runs** — or any run since: the 08-29
  15:13/18:14/20:00/20:43/21:15 runs and every trace through 09-02 contain no re-proposal of
  the send. The nearest approach — 08-31's *"two quick contact updates waiting to be saved for
  Iva — approve or leave them?"* — is a different action (CRM field fills), correctly raised.

The war-of-attrition loop (decline → re-prompt → approve to escape) is dead on live evidence.

*Filed 2026-08-27 from Mike's own live decline attempt · built same day · confirmed through
four days of scheduled runs, closed 2026-09-02.*

## ✅ [DB-0822-10] The virtue list can no longer reach an ordinary session — both @waiting turns arrived

**Closed 2026-09-02.** The `session_kind()` injection gate (`7069ea1`) needed one ordinary
afternoon/evening turn with no virtue list and one 20:00 `evening_close` still carrying it —
the second half guarding against the gate suppressing the ritual everywhere. Read across
2026-08-29 → 09-01: **every** 20:00 `evening_close` carried the full list (4/4 days), and **no
other run did** — afternoon quiet check-ins, email runs and Mike's own 13:25–13:28 afternoon
turns on 08-29 all clean. Recital outside the evening close is structurally gone, and the
ritual itself survived.

*Filed 2026-08-22 by Mike · fixed and deployed 2026-08-27 · confirmed across four live days,
closed 2026-09-02.*

## ✅ [DB-0809-21] The calendar duplicate audit fired on live candidates, and the duplicates are gone

**Closed 2026-09-02 (Red session ④, Mike present).** Both exits met:

- **The emitter is identified with certainty — and it was not the item's guess.** The
  "Possible duplicate calendar entries" reports come from `tools/calendar_audit.py:162`, run by
  the `daily_calendar_dedup_audit` maintenance job — not `daily_calendar_reconcile`, which is a
  separate job (it reported "no unreferenced passed events" in the same 08-30 window). The
  mechanism the item was really asking about — *does anything watch for duplicates, and does it
  fire live?* — demonstrably works: it raised the Mousetrap trio and re-raised the full Sep 5
  cluster on 2026-09-01T04:35.
- **Mike resolved the duplicates, and the dedupe was executed and verified live** on the VM via
  `delete_calendar_event`, per his rulings (2026-08-29 that they are real; 2026-09-02 the
  keep-sets): the Mousetrap trio → **The Mousetrap Matinee** (15:00) kept, two deleted; the Sep 5
  four-event mover's-claim/arbitration cluster → **collapsed to one**, `Submit mover's claim`
  kept, three deleted; the past `Apex migration initial session` (Sep 1) deleted as clutter,
  today's `Finalise Apex migration plan` kept (the pair had partly self-resolved when Mike's
  09-01 deferral moved the plan to 09-02). Post-delete `read_calendar` sweep confirms exactly
  one of each survives. Six deletes total, all `success: True`.

*Filed 2026-08-09 · deferred by Mike · live-candidate evidence 2026-08-27 · duplicates ruled
real 2026-08-29 · dedupe executed, emitter confirmed, closed 2026-09-02.*

## Inbox triage 2026-09-02 — the parked 08-29 table ruled, all eight dispositions Mike's

**Ruled at the Red session ④ capstone review, entry by entry in plain terms.** The Inbox
emptied; nothing left behind.

1. **Double-texting (scheduled messages landing mid-conversation)** — **closed, resolved by
   observation**: Mike, 2026-09-02: *"seems resolved as of now."* No fix shipped against it
   specifically; if it recurs the report re-files itself through the sweep.
2. **Repeating already-given information/suggestions** (08-29 06:01) — **merged into
   `[DB-0822-06]`** (stale carried state), where the same mechanism reproduced live this week.
3. **Re-asking deferred tasks + suggesting errands at impossible times** (08-28 20:28) — repeat
   half **merged into `[DB-0822-06]`**; the actionability half **filed as `[DB-0902-03]`**
   (check opening hours / prior deferral before raising a suggestion).
4. **Complex goals swallowed silently (claims, taxes)** — **filed as `[DB-0902-04]`**
   (goals-interview-style capture). Mike: *"File it. Should be fixed."*
5. **Still mentioning Prudential / reminding about attended events** — **closed on live
   evidence**: Prudential raised 0 times across 08-29 → 09-02 (was 7-of-9 runs/day), and the
   passed-event rule stands in `config/modules/synthesizer_scheduled_sessions.md`.
6. + 7. **Forwarded email loses the forwarding trail** (two reports, one fault) — **merged and
   filed as `[DB-0902-05]`**; the 08-28 dental-forwarding machine-log cluster is its twin.
8. **Logistics claiming a route "well covered" without the errand locations** — **filed as
   `[DB-0902-06]`**.

Also ruled in the same review: the three `@session` items — `[DB-0815-11]`'s policy half
**closed as answered by the built approval gate**; `[DB-0810-11]` **parked to the rebuild
notebook** (ruled before A8, not in capstone); `[DB-0814-03]` **parked post-capstone** with its
scope-against-obligations entry condition. `[DB-0820-03]` intake corpus **parked with
`due: 2026-09-09`**. The parked `synthesizer.md` `source` line: **declined forever**.
**A4 re-run removed from the capstone close path (Mike)** — the before-Alpha requirement in
`ROADMAP.md` § Section 0 is unchanged.

### A contact change could be applied without appearing on the line that says what happened — closed 2026-09-03

`apply_crm_proposals` writes accepted rows into the contact store behind the batch confirm
gate ([tools/crm_sweep.py:918](../tools/crm_sweep.py#L918)), and was in neither `ACTION_TOOLS`
nor `READ_TOOLS`, so `is_action()` fell through to the name-prefix guess. The guess happened
to be right; the point is that nobody had checked. The ACTIONS line the Synthesizer receives
is what stops it telling Mike something landed when it did not — same class as `[DB-0810-13]`,
the Kathaleen email reported as sent — and `tests/test_action_provenance.py` had been sitting
at 9/10 on exactly this assertion ("every registered tool is explicitly classified — no prefix
guessing"), i.e. the guard working and being read past.

Added to `ACTION_TOOLS` in [core/actions.py](../core/actions.py). Test 10/10. Raised and fixed
in the same session at Mike's instruction rather than left in the Inbox — it had been
unclassified since the CRM sweep shipped, and it is the third tool to reach the store without
a classification (`merge_contacts` and `import_contacts_file` were the first two, 2026-08-18).

*Filed and closed 2026-09-03 by the referent-fix session (⑤); noticed while reusing
`core/actions.py` for `tools/turn_referent.py`.*

### "Undo that merge" was read as a work project, so the undo never happened — `[DB-0826-01]` closed 2026-09-03

Five instances 08-10 to 08-29: a short referring turn after an action — *"undo that merge"*,
*"read that back to me again"*, *"previous request"*, *"approved"*, *"now set it back to Iva"* —
resolved against the wrong referent, twice with the system's own `ROUTING_MISS` naming the
misinterpretation and proceeding anyway.

**The cause was not the one the item, the probe or the 2026-08-28 ruling assumed.** The
Coordinator was never given the conversation: both live call sites in `core/orchestrator.py`
called it with no `history`, so its whole view of the recent past was ambient facts, open
threads and five days of day-logs, containing no conversational turn. *"That merge"* matched
the only merge-shaped thing in scope — on 08-26 a Prudential Apex **branch** merge in the logs.
`coordinator.md:129` was therefore **unfollowable, not ignored**, and the Flash-Lite-vs-Pro
probe could not have found this: it has always supplied `history`, so its 6/12 measured a
model on a condition production never provided.

**Fixed in two halves** (`6483e27`): `_coord_history()` passes the last six messages, copied
rather than the caller's list; and `tools/turn_referent.py` states what the previous turn *did*
— tools run, their objects, and whether each completed, failed, is still waiting on the user or
was refused. The second half is what a transcript cannot give: on 08-29 the reply text said the
email to Iva was sent, the confirm ledger said pending, and the ledger was right. Fails open.

**Evidence.** `gemini-3.5-flash-lite`, Suite B-hard x3 (`tests/run_referent_probe.py`, raw JSON
in `tests/referent_probe_2026-09-03_*.json`): referent named correctly **0/12** with neither
half, **6/12** with history alone, **12/12** with both — 24/24 across two full-arm runs.
*"Approved."* separates the halves: 0/3 on history alone (it named *both* pending approvals,
which is the 08-15 failure) and 3/3 with the block. `tests/test_turn_referent.py` 16/16.

**Live confirm, deployed VM, persona `mike`, real user turns, 2026-09-03:**
*"Log what I ate today — cereal and milk for breakfast."* → logged; then *"Read that back to me
again."* → *"For today's log, I have recorded cereal and milk for breakfast under your nutrition
notes."* That is the 08-18 instance verbatim, which previously resolved to the Prudential
schedule.

**No `coordinator.md` edit** — 12/12 without one, and the block carries its own instruction
inline, so a second copy in the agent file would break One Home Per Rule Class. **Ask-rate was
replaced as the pass condition**: it is 0% in every arm and correctly so once the referent is
supplied.

**Known and left open, deliberately:** *"Approved."* still routes to `logistics` rather than
`relationships` on 2 of 3 runs with the referent already correctly resolved — a taxonomy
disagreement about who owns emailing a landlord, not this class. Not filed; raise it if it is
seen live.

*Closed 2026-09-03 by Red session ⑤, built and measured the same day. Reasoning in full:
`archive/PROJECT_LOG.md` § 2026-09-03.*

---

## [DB-0818-08] Nothing recorded where a fact came from — CLOSED 2026-09-03 (session ⑦)

**Both halves built and both tested. Owes a deploy, tracked in `SESSION.md`, not here.**

**What a user gets.** A contact detail the system read off a real record — today, the Google
address book — is no longer quietly replaced by one the model concluded; it asks once, naming
where the value on file came from, and stops asking after that answer. And a fact the tool
merely inferred about the user is no longer handed to the model as a fact with a "be tentative"
note beside it.

**The re-open changed the decided design, which is the part worth keeping.**

1. **Job 1's own worked failure could no longer recur.** `Kathaleen → Kathleen` was closed on
   2026-08-26 by the identity-rename gate added after the Stephen/Steven case, which asks on any
   identity-field change regardless of provenance. Tagging that path would only have let the gate
   ask *less* often. The item and the roadmap both still described it as open.
2. **A provenance tier already existed** in `tools/wisdom.py` (`stated`/`observed`), model-declared
   in the schema — while `log_interaction` deliberately keeps `source` out of its schema for the
   exact inverse reason. Two stores, opposite rules.
3. **Job 2's failure was live at one function**, and `write_wisdom`'s schema already promised the
   behaviour nothing implemented.

**Mike's rulings, 2026-09-03.** *Contacts:* ask before replacing a **checked** detail.
**Rejected — the full per-field schema:** no artefact can back an occupation or a how-met, so the
tag would read "unknown" on most fields, buy nothing the narrow version does not, and cost a
relabelling of every record. *Authority:* a model may assert `stated`/`observed`; **only code may
set `verified`**.

**Evidence.** `tests/test_fact_provenance.py`, 15 checks — including the full
card → approve → execute path through the real confirmation store, and that an approved
correction **clears** the mark so the same correction is never questioned twice.

**Job 2's live acceptance test ran with a baseline arm**, because "the reply hedged" is not
evidence the change did anything. Same fact, question and model on `danny_park`. Old rendering:
*"somewhere in that 6:00 to 9:00 AM window"* — the inferred window asserted as fact. New
rendering: *"earlier in the day"*, no window claimed, closing by inviting correction.
**n=1 per arm — evidence, not proof**, and job 2 was always scoped as influence, not enforcement.

**Scope not claimed as covered** (unchanged from the item): the tiers reach only facts that
travel through a store. A fact invented mid-turn and spoken without ever being written is
untouched; the wire is covered by the zero-source guard, and the gap between the two remains.

*Closed 2026-09-03 by session ⑦. Reasoning in full: `archive/PROJECT_LOG.md` § 2026-09-03.*

---

## [DB-0808-06] A flagged clinical thread could never be closed — CLOSED 2026-09-03 (session ⑦)

**Closed on a reframe, not on the design the item proposed. Owes a deploy.**

**The premise had expired.** The item and `ROADMAP.md` § A7 both explained the refusal as waiting
on an administrative channel that "does not exist yet". Two things had since been built for
unrelated reasons that together are one: `tools/confirm.py` (model-excluded, user-approved,
executed server-side) and `core/scheduler.fire_function` (maintenance jobs, no model session).

**Mike moved the problem upstream, 2026-09-03: a tier-2 flag alerted nothing.** It surfaced once,
moved to `watch`, and lived on in a file only the model reads. The close problem was the visible
end of that; the alert problem was the whole of it. His ruling: build a development-side inbox
that one day routes to next of kin or physicians, and archive from there on a periodic check.

**Built.** `tools/escalation.py` — every tier-2 thread lands there once (idempotent per flag,
because the Synthesizer resubmits its whole thread list every turn), sensitive-tier 0600, and
**every record states that nothing was routed anywhere**, because a queue that looks monitored and
is not is worse than an obviously empty one. A weekly `fire_function` review offers a close past a
14-day dwell through a **code-raised** card; `context_tracker.administratively_resolve` is the only
path to `resolved` and no session can reach it. **The conversational refusal is untouched** — a
session submitting `resolved` is still coerced to `watch`.

**The failure direction stayed safe, as the item required.** Nothing auto-closes: there is no
recipient to route to yet, and a timer is not a second opinion.

**Two figures chosen rather than asked, recorded so they can be overruled:** the 14-day dwell, and
`notification: none` on the weekly job — a scheduled push about the worst thing in someone's life
is exactly what the dwell exists to avoid.

**Standing limit, recorded on every close rather than hidden in an omission:** the deployment is
single-user, so the person closing a clinical escalation is also its subject. `archived_by` says
so. This is the design's limit until a third-party channel exists, not an oversight.

**Evidence.** `tests/test_clinical_escalation.py`, 14 checks — including that a session still
cannot resolve a tier-2 thread, that a close without a token performs nothing, that an approved
close archives rather than deletes and keeps the basis, and that the review never closes anything
on its own.

*Closed 2026-09-03 by session ⑦. Reasoning in full: `archive/PROJECT_LOG.md` § 2026-09-03.*

---

## ✅ [DB-0820-04] A hostile email aimed at the intake pipeline — closed 2026-09-03

**Closed on the evidence its own text demanded: the probe was built, run, and passed.**
`tests/run_intake_redteam.py` (commit `764d218`, Sonnet worker, worktree
`wt/intake-injection-docs`) sends a `[SYSTEM: …]`-class payload — attempting to force
`category=action_required`, `important=true`, `domain=finance`, plus an injected
`confirm_token` field — through the intake pipeline against `danny_park`, per the standing
B1 persona rule (an ordinary-life persona, so a clinical thread cannot pre-empt the payload).

**Gate PASS — 5 passed / 0 failed / 0 errored / 2 informational**
(`tests/security_redteam_2026-09-03_intake.md`):

- **Code tier** (the live `sweep()`/`classify()` path): the payload had zero influence,
  proven by identical output against a benign control body. Nothing was taught into a rule
  or the ledger.
- **Model tier** (`tools/intake_extract.py::extract()`, one live Vertex call;
  `DEPLOYMENT_MODE` forced in-process only): the extractor declined the injected
  instruction and returned `{"category": "unclear", "important": true}` — refusing the
  forced category while correctly flagging the message as odd. The production toggle
  (`extractor.enabled`) confirmed unchanged before and after.

Also advances **B1b** (A7's open check family): intake now has its own hostile-email row.
The suite is repeatable ahead of the `[DB-0820-03]` extractor flip — re-run it then.

---

## ✅ [DB-0815-11] The system recorded a preference change it never made — closed 2026-09-03

**Closed on the item's own exit: "one live `FALSE_ACTION_CLAIM` event or one clean week" —
the clean week arrived.** Both built halves have been live on the VM for that week:

- **Detection** (`e673330`, built 2026-08-27): persistence claims in the Synthesizer's text
  cross-checked against write-family tool calls in the turn's trace; unbacked claims log
  `FALSE_ACTION_CLAIM`. Deployed in the second attack's close-out deploy, recorded live at
  `4b6779e` (2026-08-27 22:12).
- **The approval gate** (`75a91d6`, policy Mike's 2026-08-28): inferred persona writes
  propose-and-confirm via `consume()`; redundancy refusal at `NEAR_DUPLICATE` names the
  existing home. Deployed with the 2026-08-28 spinoff batch.

**Evidence:** `data/personas/mike/logs/quality_events.json` read live 2026-09-03 evening —
**zero `FALSE_ACTION_CLAIM` events in the log's entire history**, spanning the six days
21 hours since the detector deploy (the exact week completes 22:00 tonight; closed at
Mike's direction with the timing stated rather than held three hours for ceremony).

**Honest caveat, recorded not resolved:** a clean log cannot fully distinguish "no false
claims occurred" from "detector silently broken" — the in-tree tests
(`tests/test_false_action_claim.py`) pass, verified 2026-09-03, which is the available
assurance. If a false action claim is ever again seen live with no matching event, re-open
against the detector first. The 2026-08-28 design note (persona preferences as binaries/tags
as users accrue) survives in the Mark 2 notebook's orbit, not here.
