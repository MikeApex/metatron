# Closed Backlog Archive — 2026-09

**Items closed in September 2026, with the evidence that closed them.** Rolls monthly;
the previous file is [`backlog_closed_2026-08.md`](backlog_closed_2026-08.md).

**Search this before re-filing anything.** A closed item is removed from
[`../DEV_BACKLOG.md`](../DEV_BACKLOG.md) entirely — this is where its proof lives, and roughly a
third of what has looked open in the past turned out to be already fixed.

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
