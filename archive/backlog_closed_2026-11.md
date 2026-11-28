# Closed Backlog Archive — 2026-11

**Items closed in November 2026, with the evidence that closed them.** Rolls monthly;
the previous file is [`backlog_closed_2026-10.md`](backlog_closed_2026-10.md).

**Search this before re-filing anything.** A closed item is removed from
[`../DEV_BACKLOG.md`](../DEV_BACKLOG.md) entirely — this is where its proof lives.

---

## ✅ [DB-0810-11] Where should code replace model judgment? — closed 2026-11-23

**Closed into a document, by Mike's ruling D1:**
[`plans/agent_instructions_to_code_sweep_2026-11-23.md`](plans/agent_instructions_to_code_sweep_2026-11-23.md).
That sweep read every runtime agent instruction file against the code that loads it, at medium
effort. It found 25 moves (bins A–C) and 6 One Home contradictions. A Fable review
([`plans/agent_instructions_to_code_sweep_review_2026-11-23_fable-5-1.md`](plans/agent_instructions_to_code_sweep_review_2026-11-23_fable-5-1.md))
confirmed 21 of the 25 rows and added 19 misses. Mike ruled D1–D13 in § 6 of the sweep document.
The build runs from `handoffs/2026-11-23-instructions-to-code-build-driver-prompt.md`, held until
the data-object project finishes.

**Where each strand went:**
- **(a) Lookups feeding agents evidence:** the sweep's cluster C2. Contact-name matching is done.
  The nickname-prefix signal (`Jon` / `Jonathan` scoring 0.545 against a 0.6 bar) goes to finding
  #12.
- **(b) Code removing agent calls:** clusters C1 and C3.
- **(c) A standing review protocol:** the sweep's method (four bins, silent first) becomes one
  lens of the next codebase review. It is not a standing backlog item.
- **`write_archive` dedup:** built. `tools/diarist.py:324` (`[DB-0810-03]` grants ruling,
  2026-08-28).
- **`temperature`, not plumbed through any provider path:** its own inbox line, per the review
  (filed 2026-11-23).

**The item as it stood when closed:**

- **[DB-0810-11] Where should code replace model judgment?** Raised by Mike 2026-08-05, never
  given its own session. Three strands: (a) deterministic lookups feeding agents evidence instead
  of asking them to recall it, with `tools/scheduling.py` as the worked example; (b) code that
  removes agent calls entirely; (c) a standing code/agent review protocol. Also parked here:
  `temperature`. Parked to the rebuild notebook by Mike on 2026-09-02, then left without a home
  when Mark 2 ended on 2026-11-18. *Filed 2026-08-10.*

---

## `/backlog deep`, 2026-11-26: closed on evidence read from the VM and the tree

*Each was read on 2026-11-26, from the VM's journal, traces and data files (read-only SSH) or
from the code at HEAD `2293026`. The approval was Mike's ("proceed as rec", 2026-11-26).*

### ✅ [DB-1026-01] Replies came back cut short, blank or leaking prompt text
**Evidence:** the journal since 11-01 has 10 lines reading `[reply_limits] round 1 cut at
MAX_TOKENS — replaced`, among them 11-15 07:48, 11-22 16:24 and 11-23 07:31. Each is followed by
`final reply round answered`. The replacement (`d3f610b`) fires live and the cut text never
reached the user. The thinking spread behind it belongs to the reply-latency build
`[DB-1029-09]`.

### ✅ [DB-1029-16] The empty-day check-in said "nothing urgent requires your attention"
**Evidence:** at 21:51 on 11-25 the empty-day check-in replied "Mike, I have your UK tax return
tracked for December 31. What's on your mind tonight?", which asks a question as `226a0c2`
intended.

### ✅ [DB-1029-17] False "it's queued / set to surface" claims are now logged
**Evidence:** three `FALSE_ACTION_CLAIM` events since 10-29. Two of them (11-22 16:48 and 16:49,
"I've updated the entry in your … log") coincide with Mike correcting the same entry three times
(machine-log ⚠×3 "corrected the date of the grey feather entry"), so they are real catches.
**Noted, not filed:** that day a log edit was claimed and not made, and Mike was told.

### ✅ [DB-1029-01] The day plan decides when Metatron nudges and checks in
**Evidence:** `scripts/check_day_plan_step2.py --since 2026-10-29T10:50` on the VM reported:
- 2: PASS (10 held nudges, none with a proactive row)
- 3: PASS (0 fixed check-ins fired, 733 skipped as owned)
- 4: PASS (four empty-day check-ins sent)
- 5: PASS (0 sends and 0 pings in quiet hours)
- 1: FAIL (on 11-24 a leave-now nudge fell back to the generic notice). On 11-25 one fetched
  correctly.

The behaviour of step 2 is confirmed. The failure is delivery: 181 of 228 pings since 10-29 fell
back, with the phone reporting `UnknownHostException`. Per this item's own fail branch, that
became a delivery item of its own, `[DB-1126-01]` (`## Now` 1). The check script can be deleted
with that item's fix.

### ✅ [DB-0808-09] Specialists spend a model round-trip per tool call
**Evidence:** candidate (2), Coordinator prefetch, was built in `360eb23` (Stage 4 4a+4b,
11-24):
- `core/prefetch.py` (`build()` at `:510`) and `config/modules/prefetch.yaml` cover eight
  specialists plus Pattern Miner's weekly run.
- The prefetch rides in the user message, so the cached prefix is unchanged.
- It is wired at `core/orchestrator.py:6147` and `:8342`.
- Instructions say "start from what is handed to you" (`8eae8c9`).

Candidates (1), batching independent reads, and (3), the read/write split, were not built. No
re-measure of turns per call was recorded; file one only if latency work asks for it.

### ✅ [DB-1029-04] When Mike states a standing rule, Metatron saves it and then says it can't
**Evidence:** November had two "change on my side" replies, 11-13 13:51 and 11-25 10:28. Both
answered requests that genuinely needed a code or routing change: the cardiac-log routing
(implemented as a dated profile line, `[DB-1113-01]`) and the task-block sizing (now `## Now`
3). No reply in the four weeks since the 10-29 fix both saved a rule and said it needed a change.
The follow-up half (whether a stored person-specific rule is consulted when scheduling) was
never observed. It is not refiled.

### ✅ Inbox, 11-23: removing list items with the wrong tool left them visible (Films)
**Evidence:** `remove_entry` exists at `tools/data_objects.py:1554-1583`. Every read skips removed
rows (`:873`, `:925`, `:984`, `:1386`). `change_entry` is refused on a removed row (`:1543`), and
`config/agents/synthesizer.md:411` says to use `remove_entry`, "never a status like 'removed'".

### ✅ Inbox, 11-01: a dedicated tracker for films with seen-status and thoughts
**Evidence:** the user's own logs (phases 1–2, live) make a Films list a user-made log. The
11-23 comments at `tools/data_objects.py:1555-1557` name that list.

### ✅ Inbox, 10-24: check by 11-07 that a correspondence suggestion fires
**Closed as not seen, per its own rule** ("if nothing has arrived by 11-07, re-scope rather than
extend"). On 11-26 no task in the VM's `tasks.yaml` carried the correspondence-evidence close.
The feature is built (`tools/obligations.py:3651`). If a suggestion misfires, that is a new
report.

### ✅ Inbox, 10-24: check 11-02 that a week of gym adherence reads right
**Evidence:** `python3 -m tools.obligations mike --report` runs on the VM and prints per-habit
completions over target, for example "Stretching 6/60 over 30 periods". The gym habit itself had
been retired by Mike (10-26).

### ✅ Inbox, 10-24: are Vertex reply stalls still happening?
**Merged into `[DB-1029-09]`** (reply latency), which owns the stall tail. Since 11-10 the journal
shows only isolated `[reply_limits] round 1 capacity failure (The read operation timed out) —
retrying once` lines (11-23, 11-25).

### ✅ Inbox, 11-23: the multi-user isolation suite is red (push `KeyError('persona')`)
**Fixed in `46fe856`.** `core/push.py:112` counted with `s['persona']`, so registering any device
raised while an ownerless pre-11-23 subscription remained in the file. It now uses `.get`. The
test still asserted the old "legacy is Mike's" rule, which `388a91c` reversed; it now asserts an
unowned subscription reaches nobody. `tests/test_multi_user_isolation.py` passes 29/29 (was
28/29).

### ✅ Inbox, 11-24: `note_expectation` is registered but unclassified in `core/actions.py`
**Fixed in `595ec01`.** It is classed as an action, on the same reading as `record_signal`.
`tests/test_action_provenance.py` passes 10/10 (was 9/10).

### ✅ Inbox, 11-23: "I'm free today" doesn't clear "(when free of childcare?)"
**Fixed on `wt/dayplan-capture` `521d864`, merged 11-26.** `set_day_shape` pruned `day_overrides`
entries more than 7 days old by the real clock, in the same write that recorded them. An override
for such a date said "recorded" and then vanished. F8 simulates 2026-11-01, so it began failing
around 11-08 with no code change. The entry being written is never pruned now.
`tests/test_day_plan_round2.py` passes 30/30. In live use this only affects overrides dated more
than a week back.

### ✅ Inbox, 11-24: the weekly-review ranking code refuses ordinary text and misses aliases
**Fixed on `wt/mail-ranking` `571bee9`, merged 11-26.** `_person_names` in
`tools/ranking_review.py` now reads contacts by `tools/lookup_guard.py`'s rules:
- the strict store loader
- each alias on its own
- only a capitalised alias counts as a name
- note annotations stripped

The dead `_ORG_TYPES` skip is gone. Tests: `tests/test_ranking_review_aliases.py` 8/8,
`tests/test_ranking_v2.py` 58/58, `tests/test_research_check.py` 21/21.

### ✅ Merged, not closed (each now lives in the item named)
- **Inbox 11-17, twice: live GPS to infer what was done / geolocation on consecutive messages** →
  `[DB-1029-06]`. The live location is phase 4 of the data-objects build.
- **Inbox 11-13: routine cardiac logging shouldn't prompt for symptoms or go to Physical Health**
  → `[DB-1113-01]`, which is its implementation.
- **Inbox 10-29: automated meal and snack logging three times a day** → `[DB-1029-03]`.
- **`[DB-0902-06]` Logistics claims a route is "well covered" without knowing where the errands
  are** → `[DB-1029-06]`. `git grep "well covered"` over `config/ core/ tools/` finds nothing.
  Phase 3 places supply the known locations the guard needs.
- **`[DB-1029-12]` barge-in never tried on the device, and `[DB-1029-13]` the "I'm here" cue
  voice** → `[DB-0919-01]`, now one headset-mode item. None of the three has a code change since
  09-24 (`git log -S` on `stopSpeaking`, `cue`, `mediaSession`).

### ✅ `[DB-1113-01]` Mike's week-long cardiac log kept skipping Physical Health past its end — closed 2026-11-28
Mike, on the VM: `diff` showed only the dated `other:` entry; `profile.yaml` restored from
`profile.yaml.bak-2026-11-13` and the backup deleted (mtime 05:56:57). Read back: `other: []`.
The no-symptom-questions line in `mike.md` is a separate standing preference and stays.

### ✅ Inbox, 11-27: the Friday swim class kept planning in the morning → `[DB-1128-01]` (Now 4)
Read on the VM 11-28: a stale weekly CalDAV series, and a correction that stopped at
`write_wisdom`. Triaged into the schedule-change routing item; Mike fixed the stale
`logistics.json` `intention_goals` line by hand the same morning.

### ✅ `[DB-1126-04]` The ~15-minute walkthrough that closes eight owed checks — run 2026-11-28
Run mostly by Claude Code sending as Mike (authorised), plus Mike's VM edits; log § 2026-11-28.
- **Passed:**
  - cardiac line removed (`[DB-1113-01]` closed);
  - `check_inbox_6h` disabled;
  - shopping + "over and out";
  - meal habit created (its close stays on `[DB-1029-03]`);
  - Drop anyway;
  - no repeated blue-box question;
  - overlap script (only `mike.md:18`, which agrees with Synth).
- **Failed, each carried by its own item:**
  - defer, contact note and the false failure reply → `[DB-1128-02]`;
  - contact `social.work_email` left in place → `[DB-1029-02]`;
  - ambiguous name → `[DB-0818-05]`;
  - quiet-hours card → `[DB-1029-18]`.
