# Stage 4 (C2): hand each specialist its evidence — plan, 2026-11-23

*Planner: Opus 5.5. Read-only: nothing was edited, built, deployed or called on a model. Sources:
the sweep § 6 rulings and rows #6, #9, #12, #14, #15, #20, #22; the Fable review (S1, S3, S7.2, S10;
LOCAL 4, 5, 8, 9, 10; M1–M4, M12–M14, M16); the driver § Stage 4; `[DB-0808-09]`, `[DB-1029-09]`;
the code at **HEAD `8cd3be3`**, exported to a scratch copy because another chat has uncommitted
edits in the working tree. Stage 2's and Stage 3's plans did not exist when this was written, so
every place they meet this one is in § 5. **Read them before 4a starts.***

*Revised 2026-11-23 against **HEAD `8ef2edf`**. The ranking chat's `e134948` and `129f3fb` are
committed. A new set of uncommitted edits from other chats has since appeared in
`core/orchestrator.py`, both routing files, `synthesizer.md` and four tool files; where they sit
against this plan's hunks is § 5 item 1. Line numbers below are HEAD `8ef2edf`.*

---

## Revision 1 (2026-11-23)

Inputs:
- [the Fable 5.2 review](instructions_to_code_stage4_evidence_plan_review_2026-11-23_fable-5-2.md);
- the driver's dispositions and Mike's rulings in
  [the plan-review stop](instructions_to_code_plan_review_stop_2026-11-23.md) §§ 1–3, with § 5
  binding;
- the revised Stage 2, 3 and 5 plans.

**Decisions, all ruled.** 4-1 never · 4-2 yes, read-only · 4-3 yes, #16 built here, in the
shape Stage 5's plan specified and Mike ruled "as the plan says" (§ 3 item 20) · 4-4 evidence ·
4-5 yes · 4-6 actions only · **4-7 no: a read never writes** · 4-8 yes. No decision is left
open in this plan.

| Review finding | Resolution |
|---|---|
| **S1.** The A4 quick gate never sends `mode: quick`. | **Resolved.** A new helper, `_specialist_directive(agent, directive, complexity, *, code_added=False)` in `core/orchestrator.py`, is the only place the prefix is made. `_dispatch_from_coordinator` calls it, and so does `tests/run_a4_safety.py run_one`, before `_run_single_agent`, whenever `--complexity quick`. An offline test asserts the runner hands the specialist a directive that starts `mode: quick`. The gate order is now: helper and runner first; then the clinical-quick suite **with** the prefix (≈$3–4, stated first); dispatch is wired only after it passes; then the pipeline suite (≈$3–4). § 1 #9. |
| **S5.** M17 was built by neither stage. | **Resolved: 4b builds it.** Per substance `type` in `health.substances_logged` it reports "last logged use: <date>; days with a health log since: N". It never reports "N days clean". The `CESSATION_SUPPORT` closing edit is C25 in § 3. § 1 #14. |
| **S6.** `read_calendar` would start writing to the calendar. | **Resolved: 4-7 = no.** Nothing writes. Prefetch reads, and its calendar block says "N events still unverified". The re-check is the read-only `check_calendar_conflicts`. It runs only when **Logistics itself** calls `read_calendar` (never from prefetch, the speculative read or another caller), at most 2 events, once per event per request. Its result is attached to the event in the read result. Clearing `[VERIFY]` stays Logistics' own `update_calendar_event`. § 1 M14. |
| **L2.** `PROACTIVE_FLAGS` and the headline reached the cloud Research Agent. | **Resolved.** `research_agent`, and every agent in `_UNTRUSTED_OUTPUT_AGENTS` or run `bare`, gets neither block and no prefetch. Tested. § 1 #6. |
| **L3.** Prefetched calendar text escaped the untrusted-read taint. | **Resolved.** A prefetch that includes content from a tool in `_UNTRUSTED_READ_TOOLS` (HEAD :6482) sets `trace.prefetched_untrusted = True`. `_file_wisdom_proposals` (:6490) ORs it into `read_untrusted`. It is not done by faking tool-call records: `_failed_tool_calls` would then report a failed prefetch read as a failed action. Tested. § 1 #22. |
| **L4.** On exhaustion the Pattern Miner's loop returns a raw tool result. | **Resolved.** `_openai_compat_loop` (:5154) gains `final_round: bool = False`. When it is True and the rounds are spent, it makes one tools-off call with `_FINAL_REPLY_PROMPT` (:4522), mirroring `_openai_compat_stream`. Only `pattern_miner` sets it, through `run_session_gemini`. A report is written **only from a valid final reply**: at least one parsed block with `[EVIDENCE]`, `[OBSERVATION]` and `[CONFIDENCE]`, and not a tool-result body. Anything else writes nothing, keeps the last real report, and logs a warning plus a quality event. Also found while checking: this loop runs only the **first** of parallel calls (the Vertex signature workaround, :5240–5257), which is why the Pattern Miner makes one call per round. § 1 #20. |
| **L7.** `FOOD_NOT_LOGGED` read the wrong store and claimed to stand. | **Resolved: evidence, not a flag.** It reads today's `meals` data-object entries and `health.food_logged`. It states that it was taken before this turn's diary write (the Diarist starts after the blocking specialists, :7121–7190). § 1 #14. |
| **L8.** Common words resolved as contact names. | **Resolved.** A single token resolves only if it is **capitalised in the source and not sentence-initial** (the `heard_names._candidates` rule). It matches `first_name`, `nickname` or a one-word `name`, **never `last_name` alone**. Otherwise a **two-token** match is needed (first + last, or a multi-word `referred_to_as` phrase, which may be lower-case). Tests use contacts named Will, Mark, Bill and Rose, and a shared surname. § 1 #12. |
| **L9.** An omitted `held_items` key erased them. | **Resolved.** In `write_context_tracker`, `held_items is None` (key omitted, which is what `persist_context_block` passes, :2767) **keeps** the stored items with their `held_since`. An explicit `[]` clears them. This matches Stage 2's `merge_pattern_findings`, which leaves `held_items` exactly as on disk. Tested. § 1 M4. |
| **L10.** M13's lists replaced earlier runs. | **Resolved.** Code writes to a code-owned sub-dict, `logistics.recorded_by_code`, which the model's own `logistics` writes never name. `_deep_merge` (`tools/logger.py:169`) recurses into dicts, so it survives them. Each list is **appended and de-duplicated** by (tool, uid or title, start). Tests run twice in one day with a model write in between. § 1 M13. |

**Interfaces adopted from the sibling plans.**
- **Stage 2.**
  - M6 maps the `write_context_tracker` tool to `merge_pattern_findings`. The Pattern Miner's
    step 7 therefore stays a model call and is safe; code's fallback for a code-written report
    calls `merge_pattern_findings` directly.
  - #4 caps `open_threads` only.
  - The D4 guard refuses the five MW/PH record writers on a bound no-user-words turn.
  - Stage 2 forces `deep` for MW/PH on the two sessions, and 4f's code-added rule keeps it so.
- **Stage 3.**
  - `_after_specialists(outputs, persona, user_input, user_turn)` is the post-return wrapper in
    both twins and the A4 runner. 4b's counted-signals step goes inside it, after #13, so the
    runner tests it too.
  - #8 also runs at Physical Health's return in `_run_single_agent`.
  - M17 is Stage 4's (4b).
- **Stage 5.** #16 has moved here and its Relationships text is Stage 4's to word (C14).

**Counts after revision:** opening round **9** Red edits; closing round **33** Red edits
(§§ 2–3). Sub-build order unchanged: 4a → 4b → 4c → 4d → 4e → 4f.

---

## 0. Step 0: measurement (done, read-only, 14 days, `mike`)

**Method.** `scripts/vm_read.py` exposes persona data, not traces. The trace door is the same
server's `GET /monitor/traces` (`core/server.py:2744`), which is admin-only and read-only and
accepts the same locally minted bearer (`core.auth.bearer_header`) that `vm_read.py` uses.
Three scratch scripts printed **counts only, with no message content**: tool names, argument
keys (values only for dates and filters), token deltas and durations. Window: 2026-11-09 →
11-23, 1,977 traces, 1,732 of them proactive. Log-field presence was read through the read door
(`get_log_window`), printing keys only.

**What the measurement says.**

| Specialist | calls (user / scheduled) | turns/call (Aug → now) | first-turn tools (top) | model time per turn |
|---|---|---|---|---|
| logistics | 41 / 58 | 3.6 → **4.75** | `read_calendar` 29, `read_email` 29, `list_tasks` 9, a 3-read batch 6 | 1.4 s |
| physical_health | 18 / 30 | 2.9 → 2.77 | `read_log` 27, `write_log` 13 | 1.9 s |
| mental_wellbeing | 5 / 21 | 3.1 → 3.0 | `write_log` 11, `read_log` 7 | 1.7 s |
| relationships | 11 / 3 | 4.2 → 4.5 | `read_agent_config` 4, `search_contacts` 3 (+6 on turn 2) | 1.3 s |
| work_vocation | 7 / 0 | 3.7 → 2.57 | `read_agent_config` 4 | 1.6 s |
| finance | 7 / 0 | — → 3.0 | `list_tasks` 3 | 1.2 s |
| recreation / learning | 3 / 2 | — | nothing predictable | — |
| pattern_miner | 0 / 2 | **8.0 (the cap)** | `read_recent_insights` → `read_wisdom` → `read_baseline_periods` → … | — |
| coordinator | 119 / 43 | 1.36 | `write_quality_event` 68; no reads | — |
| synthesizer | 119 / 204 | 1.23 | writes first (`update_task`, `amend_data_object`); `read_day_plan` 7, `list_tasks` 7 | — |

Six further findings bear on the design:

1. **Logistics is the critical path.** It was the slowest specialist on 36 of the 57 user turns
   that dispatched any specialist. Its median duration is 9.7 s (p90 18 s).
2. **Specialists now batch sometimes** (Logistics 44 of 381 tool turns carried 2–7 calls). The
   August finding of "0 of 392" no longer holds.
3. **Per-read token cost** (median turn-1 to turn-2 input growth): `read_email` **19,571**
   (p90 27,979); `read_calendar` 2,083 (p90 4,448, and 2.3 s of CalDAV time); `list_tasks`
   944 for Logistics, 5,109 for Finance (`include_closed: true`); `read_log` 870 (PH) and
   1,437 (MW); `read_agent_config` 468 (W&V) and 48 (Relationships); `search_contacts` 968.
4. **Dispatch modes:** 93% of specialist dispatches are `quick` (Logistics 56/60, PH 30/32,
   MW 15/19). `PROACTIVE_FLAGS` appears in 75 of 162 Coordinator outputs, about one line each.
5. **Log fields actually written (15 days):** `health.sleep_hours` on **3 of 15** days,
   `food_logged` 12/15, `exercise` 11/15, `energy` 7/15, `wellbeing.mood` 15/15. **No
   `learning` or `recreation` field on any day.** `medications_logged` was never set (the medication
   data object is now the home).
6. **The weekly Pattern Miner has written no report for twelve weeks.** Every Sunday run from
   09-06 to 11-22 (12 of 12) hit the 8-round limit of the plain Gemini loop before
   `write_insight_report`. *(Corrected in Revision 1, review L4.)* The loop it runs,
   `_openai_compat_loop`, has **no** tools-off final round: on exhaustion it returns the last
   message, which is the eighth tool result, and that goes only to a terminal notification. The
   same loop also executes only the first of any parallel calls (:5240), so one call per round
   is forced, not chosen. The Coordinator's "Pattern Miner report (most recent)" is therefore at
   least three months old (the VM holds one insights file). This is a **live silent defect**, not
   a turn saving, and it makes #20 the highest-value item in the stage. It also makes M6
   (Stage 2) a hard prerequisite: a fixed Pattern Miner would start replacing the tracker weekly.

**Measurement verdict: measured.** Re-measure after each sub-build with the same three scripts;
they are kept in the session scratchpad only, by design (`.claude/rules/deploy.md`: no new
standing scripts).

---

## 1. Items

Conventions for every item: **new or changed text reaches a model only in the user message**,
never in a cached system prefix. Code may **add** a flag but never clears one. `MUST_SURFACE`,
`CLINICAL_CONCERN` and `MEDICATION_MISSED_CRITICAL` are never computed, cleared or suppressed
by anything in this stage. Real user turn means `has_real_user_turn()` /
`turn_context.current()["user_turn"]`. Examples and fixtures use generic names only.

### #22: per-agent prefetch into the user message

**What a user notices.** Replies that involve the calendar, tasks or a specialist's saved
settings come back about 1.4–2 s sooner. Logistics, the slowest step on most such turns, loses
one model round on about half its calls and two on some. Against a 54 s median that is about 4%,
in line with LOCAL 9. The bulk of the latency belongs to `[DB-1029-09]`, which covers
Synthesizer thinking, not prefetch.

**Mechanism.**
- New `core/prefetch.py` (Amber). `build(agent, directive, user_text, persona, user_turn) -> str`
  runs that agent's reads concurrently (thread pool, persona bound in each worker, a 4 s budget
  per read). It returns one block:
  `[PREFETCHED — read by code before your first turn, as of HH:MM. Use these; call a tool only
  for something not here.]`, with one sub-heading per read naming the tool and arguments it
  stands for.
- A read that fails or times out becomes one line, "(not read in advance: call `<tool>`)". It
  never fails the dispatch.
- **Every read goes through the registered handler for a tool the agent is granted**
  (`get_allowed_tools`). The handler is called directly, not through `dispatch_tool`, so it
  leaves no tool-call record (see Taint below) and triggers no M14 re-check. An ungranted entry
  is refused at load and logged; prefetch must never widen a grant. Calendar and email content keep their `<untrusted_content>` wrapping because the
  handler applies it.
- **Taint (review L3).** When a prefetched read's content comes from a tool in
  `_UNTRUSTED_READ_TOOLS` (HEAD :6482: `read_email`, `fetch_url`, `fetch_rendered`,
  `read_intake_queue`, `read_calendar`), prefetch sets `prefetched_untrusted = True` on the
  request trace, under the trace's lock. `_file_wisdom_proposals` (:6490) computes
  `read_untrusted = <the existing tool-call scan> or getattr(_t, "prefetched_untrusted", False)`.
  The intake **count** carries no outsider text and does not set the flag; the calendar block
  does.
- **Prefetch never runs** for `research_agent`, any agent in `_UNTRUSTED_OUTPUT_AGENTS`, or a
  `bare` run (review L2).
- **Unverified events (review S6).** The calendar block shows the events as read, plus one line
  when any carries `conflict_check_status == "FAILED"`: "N events still unverified (`[VERIFY]`)
  — call `read_calendar` for this range to re-check them." Prefetch never re-checks and never
  writes.
- Each read is capped (default 6,000 chars). An over-cap config is replaced by its key list plus
  "call `read_agent_config(key=…)`".
- The list is policy, so it lives in config: new `config/modules/prefetch.yaml` (Amber). From
  the measurement:

| Agent | Fixed reads |
|---|---|
| logistics | `read_agent_config(logistics)`, `list_tasks()` (open), `read_calendar(today, tomorrow)`, intake count for `logistics` (count and a one-line pointer, not the items) |
| physical_health | today's log `health` field; "Medication taken today" via `read_data_object`; `read_agent_config(physical_health)`; #14 evidence |
| mental_wellbeing | today's log `wellbeing` field; `read_agent_config(mental_wellbeing)`; #14 evidence |
| relationships | `read_agent_config(relationships)`; #12/M2/M3 (4c) |
| work_vocation | `read_agent_config(work_vocation)`; today's logged `wellbeing` and `health` fields (#6, the flow cross-check) |
| finance | `read_agent_config(finance)`; `list_tasks()` open only (not `include_closed`, which is 5k tokens); intake count for `finance`; Stage 3's #13 totals if Stage 3 put them anywhere else (§ 5) |
| recreation_hobbies, learning_growth | own `read_agent_config`; #14 evidence; L&G also #15 skill habits |
| pattern_miner | #20 (4e) |
| coordinator, synthesizer, diarist | **none.** Measured: the Coordinator's only tool is `write_quality_event`, and the Synthesizer averages 1.23 turns and opens with writes. The Diarist is write-only. |

- **Wiring.** `_run_single_agent(..., prefetch: str | None = None)` appends the block to
  `augmented_input` in the specialist branch, after the clock line and the data-object manifest,
  and records it as `context_sections["prefetch"]` for The Book. `_dispatch_from_coordinator`
  calls `build()` inside each specialist's worker, so prefetch runs in parallel with the other
  specialists and has the user's text. When `prefetch is None` (the `/internal/session` path, i.e.
  scheduled single-agent jobs and `run_subagent`), `_run_single_agent` calls `build()` itself with
  no user text.

**Cache floor.** The system prefix is byte-identical with and without prefetch (tested, below).
Nothing in Stage 4 shrinks the Coordinator or Synthesizer prefix beyond the three-line Coordinator
honesty edit (§ 2). The Coordinator caches ~8k tokens against a 5,320-token pad target; the
Synthesizer caches ~25k. The specialists' closing-round deletions shrink cached prefixes that
`_pad_for_vertex_cache` already pads (16 KB `physical_health.md` is under the floor today; LOCAL
10). **Check after deploy:** every cached specialist's turn-1 `cached_tokens` is still non-zero
in the trace.

**Files and tier.** `core/prefetch.py` (new, Amber); `config/modules/prefetch.yaml` (new, Amber);
`core/orchestrator.py` (`_run_single_agent` signature and specialist branch; one call in the
dispatch worker; Amber).

**Tests (offline, every tool stubbed).** `tests/test_prefetch.py`:
1. Each agent gets exactly its yaml list.
2. An ungranted yaml entry is refused.
3. A raising or slow read becomes the omission line and the dispatch still runs.
4. The persona is bound in the worker threads (a mismatch raises).
5. The cap and the key-list fallback apply.
6. **The system prompt passed to `run_session_gemini_cached` is identical with and without
   prefetch.**
7. Head-layer agents and the Diarist get nothing.
8. The `/internal/session` path prefetches with empty user text.
9. Calendar output still carries `<untrusted_content>`.
10. A Logistics prefetch that includes the calendar sets `prefetched_untrusted`, and a
    `WISDOM_PROPOSAL` with `provenance: stated` from that turn is filed as `observed`.
11. The intake count alone does not set it.
12. `research_agent` and bare runs get no prefetch.
13. A fixture event with `X-CONFLICT-CHECK-STATUS: FAILED` gives the "1 event still unverified"
    line, and no CalDAV write or `check_calendar_conflicts` call happens (both stubbed and
    asserted uncalled).
14. The speculative calendar read (4-2) is discarded when Logistics is not dispatched, and makes
    no write.

**Cost.**
- **Run:** Logistics block ≈ 4–5k tokens, re-sent on each remaining turn (uncached user
  message): +≈$0.004 per call where the reads would not have happened, against ≈$0.0015 saved per
  removed turn. PH and MW ≈ 1.5k each (≈$0.0034 per call on 3.8 Flash; $0.0068 from 2027-01-01).
  Net across ~12 specialist calls/day ≈ **+$0.02–0.04/day/user**.
- **Ancillary:** a calendar read on the ~28% of Logistics calls that did not read it adds 2.3 s
  of CalDAV time. That is a latency regression on those calls; see DECISION 4-2.
- **Unseen:** none; no state outlives the request.

**Risks.**
1. A prefetched snapshot goes stale within the turn, e.g. a calendar event written on turn 2 is
   absent from the prefetch on turn 3. Mitigation: the block is stamped "as of HH:MM", and the
   tool remains callable.
2. The model calls the tool anyway (duplication, not harm). Re-measure turns/call.

**DECISION 4-1, RULED (never).** Email is not prefetched. It is 19.6k tokens (p90 28k), and 26
of 29 reads were on scheduled turns, where the saving buys no user-visible latency.

**DECISION 4-2, RULED (yes, read-only).** `read_calendar(today, tomorrow)` starts concurrently
with the Coordinator on every pipeline turn and is held on the request. At dispatch it is used
for Logistics' block, or discarded. It removes the 2.3 s regression above, costs a CalDAV read on
turns with no Logistics dispatch (no money), and leaves nothing that persists. It goes through
the same handler as any read, so it carries the same wrapping and the same taint rule, and it
never re-checks or writes (S6). The wiring is one `ThreadPoolExecutor` submit in each pipeline
twin, before the Coordinator call; `_dispatch_from_coordinator` receives the future.

### #12: exact-match contact resolution at Relationships dispatch (with M2, M3 and #16)

**What a user notices.** Fewer duplicate contacts. When you mention someone you know, the
Relationships specialist starts with their actual record rather than searching by name. Its 4.5
turns/call drop by one to two.

**Mechanism (in `core/prefetch.py`, a `relationships_people` provider; new
`tools/contact_resolution.py`, Amber).**
- **Candidates** are tokens and phrases from the Coordinator's directive (which carries its
  corrected names) plus the user's words on a real user turn.
- **Exact resolution (revised for review L8).** Whole-word match against live contacts, in this
  order:
  1. **Two-token matches, any position and any case:** `first_name` + `last_name`, a multi-word
     `name`, or a multi-word `referred_to_as` phrase ("my brother", "the plumber").
  2. **Single tokens, only when capitalised in the source text and not sentence-initial**, by
     the same rule as `tools/heard_names._candidates` (:296; the colon and abbreviation
     handling included). They are matched against `first_name`, `nickname`, a one-word `name`,
     or a one-word `referred_to_as`. **Never `last_name` alone**, because a shared surname is not
     a person.
  3. `_NOT_NAMES` and a 3-character minimum apply to single tokens.

  The accepted cost is the same as the Name note's: a lone first name at the start of a
  sentence is not resolved.
- **Ambiguity.** A word that matches more than one contact first goes through the remembered
  answer (`crm._apply_resolution`). If there is none, the record is listed as "Sam matches N
  contacts — ask which" with `crm._disambiguation_entry` rows, capped at 5.
- **Nickname-prefix signal** (parked in `[DB-0810-11]`). A candidate of 3 or more letters that is
  not a known contact word, and is a prefix of a contact's first name ("Jon" / "Jonathan"), is
  listed as "possibly Jonathan Hale (name prefix): read the record before writing a new contact".
  It is **never resolved**. Near-matches by sound or spelling stay with the model and
  `write_contact`'s existing evidence. The CRM write gate already scores the prefix at 0.75
  (`tools/crm.py:62`); this puts the same signal in front of the model before it writes.
- **Handed over, per resolved person (max 3):** a compact projection with id, names, relationship
  type and quality, `last_contact`, frequency preference, `important_dates`, `contact_info`,
  `notes` (300 chars) and the last 3 interactions. Never the full `interaction_log`. Gift ideas
  and other `for_them_in_your_lists` entries go in #16's block, so they are not shown twice. All
  of it passes through `crm._gate_tone_shape`.
- **Overdue list:** `list_contacts(overdue_only=True)` logic, rendered as
  `name · id · last_contact · N days past <frequency>`, the 8 most overdue. The store holds 988
  contacts, so a raw dump is ruled out.
- **M2: tone shape.** For a resolved person, the **stored** `tone_shape` if permitted, or "none
  stored; call `get_tone_shape` before drafting to them". **Never call `get_tone_shape` from
  prefetch.** With no profile it starts a background mailbox sweep and a model call, so
  prefetching it would seed a profile for every name mentioned (ancillary cost, and a privacy
  read nobody asked for).
- **M3: upcoming dates.** Contacts with an `important_dates` entry in the next N days (N in
  `config/modules/prefetch.yaml`, default 14; `MM-DD` and `YYYY-MM-DD` both handled, wrapping at
  the year end, with 29 Feb shown on 28 Feb in a non-leap year). Max 8, with the overdue list.
- **#16 (DECISION 4-3, RULED: built here, in the shape Stage 5 specified and Mike ruled "as the
  plan says").** New `tools/recipient_context.py`. `on_file_block(resolved) -> str` gathers, for
  each resolved person (cap 3 people, 6 lines each, 160 characters a line):
  1. `tools.data_objects.entries_for_contact(contact)`: gift ideas and any `for`-linked log;
  2. open ledger tasks whose title or notes name them, read through `tools/obligations.py` view
     functions, read-only;
  3. knowledge-store entries naming them;
  4. up to 3 `core.memory` hits from `search_memory(<name>)` that **contain the name
     literally** (local FAISS, no model).

  Heading: `ON FILE ABOUT PEOPLE NAMED HERE (from code — before anything addressed to one of
  them, check whether they are its subject)`.
  - **No keyword filter, and no draft/send trigger.** The word-list trigger in the first draft
    is withdrawn: it was a fuzzy relevance test, and the ruled shape runs on every Relationships
    call that resolves someone.
  - Empty means nothing is appended. Any error gives "". It is a hint and never costs a turn.
  - It covers both doors, because `build()` runs both on Coordinator dispatch and on the
    `prefetch is None` path the Synthesizer's `run_subagent` follow-ups take.
- **M1 snapshot.** The resolved records are kept on the request for M1 (below).

**Files.** `tools/contact_resolution.py` (new); `tools/recipient_context.py` (new, #16);
`core/prefetch.py`. Read only: `tools/crm.py`, `tools/heard_names.py`,
`tools/data_objects.py`, `tools/obligations.py`, `tools/wisdom.py`.

**Tests.** `tests/test_contact_resolution.py`, with generic fixture names:
1. Exact match on full name, a mid-sentence first name, a nickname and a `referred_to_as`
   phrase.
2. Two-token resolution at sentence start ("Will Turner called"); a lone first name at sentence
   start is **not** resolved.
3. **Common-word names (review L8):** with contacts named Will, Mark, Bill and Rose, nobody is
   resolved from "Will it rain", "I will call", "mark the date", "pay the bill" or "a rose
   bush". They are resolved from "call Will tomorrow" and "ask Mark about it".
4. A shared surname alone ("the Turners", "ask Turner") resolves no one.
5. A non-name capital ("Tomorrow") is not a candidate.
6. Multi-match: a remembered answer is used when present; otherwise the ask-which list, capped.
7. A prefix is offered but never resolved, and 2-letter prefixes are refused.
8. A merged-away name follows `merged_into`.
9. The overdue cap and ordering.
10. M3 date window, including `12-30` seen from 12-20 to 01-03, and 29 Feb.
11. M2 returns stored-only, and `get_tone_shape` is asserted **never called**.
12. `not_permitted` gating.
13. #16 (`tests/test_recipient_context.py`, Stage 5's list):
    1. a gift idea for "Sam" appears when the directive names Sam;
    2. no block when there are no hits;
    3. a memory hit without the literal name is dropped;
    4. the caps hold;
    5. a broken contacts file gives "";
    6. the `prefetch is None` door (a `run_subagent` follow-up) carries the block.
14. Nothing on a non-user turn reads the user's words.

**Cost.** **Run:** block ≈ 0.5–3k tokens on Flash-Lite, ≈$0.001–0.003 per call against
1–2 turns saved. Relationships made 14 calls in 14 days, so ≈$0.002/day. #16: one local FAISS
search per resolved person (~0.5 s, run in parallel with the other reads), plus ≈400 tokens re-sent
over ~4 turns, ≈$0.0004 per call that has hits (Stage 5's figure). **Ancillary:** loading 988 contacts per dispatch,
~50 ms. **Unseen:** none.

**Risks.** A common first name hands over the wrong person's record. Mitigation: more than one
match always produces the ask-which list, never a pick.

**DECISION 4-3, RULED: build #16 here,** in the shape above.

### M1: "newly saved, read back in one clause" line for the Synthesizer

**What a user notices.** When you dictate a phone number, email, address or new name, the reply
reads it back ("got that as Catherine with a C, 07700 900123: right?"). A misheard detail is then
caught before it sits in the contact book.

**Mechanism (4c).**
- After dispatch, on a real user turn only, code reads **this request's trace** for `write_contact`
  and `write_profile` calls that succeeded.
- From their **actual arguments** it takes names, `contact_info` email, phone, address and
  handles, and profile address, postcode and employer.
- It keeps only values absent from the pre-dispatch snapshot (#12's resolved records; for
  `write_profile`, `load_profile()` taken at dispatch). A brand-new contact counts as all new.
- It builds `NEWLY SAVED — read each back in one clause (spell names and emails, group the
  digits): …`, max 6 items, appended to `synthesizer_input` in **both** pipeline twins.
- New `_readback_block()` in `tools/contact_resolution.py`. It does not edit `tools/profile.py`,
  which the other chat has modified.

**Tests.**
1. Fake trace with a new contact: all fields are listed.
2. An existing contact with an unchanged email is not listed.
3. A failed or refused write is not listed.
4. A scheduled turn produces nothing.
5. Both twins carry the block (string assert).

**Cost.** **Run:** about 60 tokens on the turns that save details. 0 otherwise.

### #14: domain counters, handed in as evidence (with M17, built here)

**What a user notices.** Sleep and energy prompts fire on the actual count ("under 6 h two
nights running") rather than on a model's reading of five days of logs. A prompt is not drawn
from logs the system wrote itself during a scheduled check-in. "You haven't mentioned eating"
is no longer said on a day whose meals are in the meals log.

**Timing (S3), decided.** Split by what this turn can change:
- **Pre-dispatch (to the specialist, in prefetch): completed days only**, from yesterday back 14
  days (30 for the "last logged" lines, 90 for cessation). Nothing in the current message can
  contradict that.
- **Post-return (to the Synthesizer): today's thresholds**, computed after the blocking
  specialists return, from a **re-read** of today's log. A night's sleep or an energy level the
  specialist recorded this turn therefore counts.
  - **Placement:** step 6 of Stage 3's `_after_specialists(outputs, persona, user_input,
    user_turn)` wrapper, after #13. It returns the block as one more bundle line. Both twins and
    the A4 runner therefore run it with no extra call site.
  - **The Diarist lag (review L7):** the Diarist starts only after the blocking specialists
    (HEAD :7121–7190), so anything it records this turn (most meals) is **not** visible
    post-return. That is why every today-reading that the Diarist mostly writes is evidence
    worded "as of before this turn's diary write", never a flag.
  - Block: `COUNTED SIGNALS (computed by code from the logs after the specialists' writes this
    turn; the diary entry for this turn is written after this — flags here stand even if no
    specialist raised them, evidence lines do not)`.
- This block is computed only for specialists that **ran this turn**, so a sleep count does not
  ride every reply. That matters because of Mike's standing "don't over-weight sleep" rule.

**Provenance ("records written on real user turns").**
- `write_log` gains a `_written_on` map beside the existing `_written_at` (`tools/logger.py`).
  Each leaf path gets `user` / `scheduled` / `unknown`, from `turn_context.current()`.
- **The Diarist counts as `user`.** Its dispatch is refused on non-user turns (`[DB-0822-05]`),
  but its background thread binds no turn. The builder detects it by the current trace agent or
  a thread-local set in `_bg`, and must not bind a turn there (the decline guard in
  `tools/confirm.py` depends on that).
- **Counters read only `user` leaves.** Leaves written before this deploy are unstamped and
  excluded, so the evidence says "counting from <date>" until the window has passed. The weekly
  Physical Health review (`/internal/session`, no turn) writes `unknown` and is excluded.
- Data-object rows (meals) are read through `tools/data_objects.read_entries` for today. Those
  rows have their own writers and stores, so the `_written_on` stamp does not apply to them.
- This is independent of Stage 2's D4 write guard, which refuses the MW/PH record writers on a
  bound no-user-words turn, and survives whatever scope that guard takes.

**Counters** (new `tools/domain_counters.py`, Amber; thresholds and windows in new
`config/modules/counters.yaml`, Amber). Each counter declares its owner agent, its fields and a
pure `compute(days, today, now)`.

| Counter | Kind | Rule |
|---|---|---|
| `SLEEP_POOR` | **flag** | `sleep_hours < 6` or `sleep_quality == poor` on 2+ consecutive **logged** nights (an unlogged night breaks the run) |
| `SLEEP_ACUTE` | **flag** | `sleep_hours < 4` in the latest night (today's record) |
| `ENERGY_CRASH` | **flag** | `energy == low` on 2+ consecutive logged days |
| `FOOD_NOT_LOGGED` | **evidence (L7)** | only when persona-local time ≥ cut-off (`counters.yaml`, default 14:00, from the `tools.ambient` local clock): "no meal in the meals log today and `food_logged` not set — as of before this turn's diary write; a meal mentioned this turn is still being recorded". Silent when either store has today's food |
| `SLEEP_MISSING` | evidence (4-4) | "sleep last logged N days ago (file threshold 2)" |
| `EXERCISE_GAP` | evidence (4-4) | "exercise last logged N days ago (threshold 5 if exercise is a goal)". The goal condition stays the model's, against the goals already in its prompt; goals carry no domain field, so code cannot decide it exactly |
| `LEISURE_GAP`, `HOBBY_LAPSE` | evidence (4-4, S7.2) | "leisure last logged N days ago; this is recorded only when the leisure specialist was consulted" |
| `LEARNING_GAP`, `PRACTICE_GAP` (L&G) | evidence (4-4) | as above; skill habits from the ledger (#15) give the real practice dates |
| `PRACTICE_LAPSE` (MW) | evidence (S7.2) | per practice in `practices_active`: "last listed N days ago" |
| MW `SLEEP_CONCERN` | evidence | the same night series as `SLEEP_POOR` |
| MW mood duration | evidence | "mood logged low on N of the last 14 days" (judgement stays the model's) |
| **`CESSATION` (M17, review S5)** | evidence, Physical Health | per `type` in `health.substances_logged` (alcohol, tobacco, nicotine, other) seen in the last 90 days: "**last logged use**: <date> (N days ago); days with a health log since: M". **Never "N days clean", "streak" or "abstinent"**: absence of a log is not evidence of abstinence (`physical_health.md` § Proposing a standing fact, `:204`). A type with no entry in 90 days gives no line. Measured: `substances_logged` was null on all 15 days, so this is silent for `mike` today |

`SYMPTOM_RECURRENCE` stays judgement. Counters never emit or touch a clinical token.
**DECISION 4-4, RULED (evidence)** for `SLEEP_MISSING`, `EXERCISE_GAP`, `LEISURE_GAP` and
`LEARNING_GAP`, and by review L7 for `FOOD_NOT_LOGGED`. Code sets only `SLEEP_POOR`,
`SLEEP_ACUTE` and `ENERGY_CRASH`, whose inputs Physical Health writes in the same turn.

**Files.** `tools/domain_counters.py` (new); `config/modules/counters.yaml` (new);
`tools/logger.py` (the `_written_on` stamp in `write_log` only); `core/prefetch.py` (the
pre-dispatch evidence provider); `core/orchestrator.py` (step 6 inside Stage 3's
`_after_specialists`, plus its bundle line in both twins' `synthesizer_input`). If Stage 3 has
not landed `_after_specialists` when 4b starts, **stop**: do not add a parallel hook.

**Tests.** `tests/test_domain_counters.py`, plus additions to `tests/test_log_field_timestamps.py`:
1. Each flag at threshold −1, at threshold and at threshold +1.
2. An unlogged night breaks `SLEEP_POOR`.
3. `FOOD_NOT_LOGGED` evidence:
   1. silent when the meals object has a row for today **or** `food_logged` is true;
   2. silent before the cut-off;
   3. the cut-off holds on both sides of midnight UTC versus local (injected clock);
   4. it is never in the flags line.
4. **The S3 case:** `sleep_hours` written by Physical Health during its run is seen post-return.
5. `scheduled` and `unknown` leaves are excluded, and the Diarist's writes are `user`.
6. The pre-dispatch block contains no today data.
7. Add-only: a model's `SLEEP_POOR` in the PH output with code disagreeing leaves the output
   untouched.
8. No `MUST_SURFACE`, `CLINICAL_CONCERN` or `MEDICATION_MISSED_CRITICAL` string is ever produced.
9. The block is absent when the owner did not run.
10. **M17:**
    1. alcohol logged 10 days ago, with 7 health-log days since, gives exactly "last logged use:
       <date> (10 days ago); days with a health log since: 7";
    2. no type entry in 90 days gives no line;
    3. the output never contains "clean", "streak", "sober" or "abstinent" (string assert over
       every fixture);
    4. `scheduled` leaves are excluded.
11. Through `_after_specialists`: the A4 runner path carries the block when Physical Health ran.

**Cost.** **Run:** reading 14–90 small local JSON files per owner dispatch, ~150–300 tokens in
and ~100 out per block, ≈$0. **Ancillary:** `_written_on` adds ~1 line per leaf to each day
file. **Unseen:** none.

**Risks.**
1. Counters start empty for up to the window after deploy. This is stated in the block.
2. Measured `sleep_hours` is present on only 3 of 15 days, so `SLEEP_POOR` and `SLEEP_ACUTE`
   will rarely fire. That is honest, not a defect.

### #15: skill practice becomes task-ledger `habit` rows

**What a user notices.** A language or instrument you practise has a real streak and a "missed
since Tuesday", with made-up sessions counted. Nothing like `"last_practiced": "today"` is stored
and read as true next week.

**Mechanism.** Mostly Red, and **none of it depends on new code** (the ledger exists), so it
moves to the **opening round** (§ 2):
- grant `open_task`, `update_task` and `list_tasks` to Learning & Growth in both routing files;
- rewrite the skill-tracking text to habit rows, and drop the three streak fields from the
  `learning` log schema.

The code half, in 4b, is evidence: the L&G prefetch lists open `habit` rows with `domain:
learning`, or linked to a learning goal, showing target, done this period, last done and missed
periods. These come from `tools/obligations.py` view functions, **read only**, because that file
carries the other chat's uncommitted edits.

**Not done in code:** stripping the streak fields in `write_log`. Until a habit row exists for a
skill, that field is its only record, so the schema edit does the work instead.

**Tests.** `tests/test_prefetch.py`: the L&G block lists a fixture habit's adherence. Routing
parity is covered by `check_agent_tools`.

**Cost.** **Run:** ~200 tokens per L&G call (2 calls in 14 days). ≈$0.

**DECISION 4-5, RULED (Learning & Growth owns skill-practice habits; Mike, § 5 item 8).** The
grants (O1, O2), the routing line moved off `coordinator.md:239` (O4) and the instruction edits
(O5–O9) are all opening-round. The ledger's duplicate refusal covers any overlap with Logistics
during the transition.

### #6: the Coordinator's `PROACTIVE_FLAGS` and the Pattern Miner headline, passed into directives

**What a user notices.** The "noticed something you didn't mention" observations rest on signals
the specialist actually received, instead of being instructed to scan inputs it never had.

**Mechanism.**
- **4a:** parse the `PROACTIVE_FLAGS:` section of `coord_output` (lines starting `- ` up to the
  next blank line or header; capped at 5 lines and 600 chars) and append it to each **blocking
  personal specialist's** directive. **Never** `research_agent`, any agent in
  `_UNTRUSTED_OUTPUT_AGENTS`, the Diarist or a code-only agent (review L2: the Research Agent's
  directive becomes web queries on the grounded path). The rule is an allow-list,
  `_EVIDENCE_AGENTS` = the eight `_CACHED_SPECIALISTS` (HEAD :5661). The block is appended as
  `COORDINATOR PROACTIVE FLAGS (signals noticed this turn — weigh them; do not repeat them
  verbatim)`. It is in the user message by construction, since the directive is the user
  message.
- **4e, after #20 makes reports exist:** a **Pattern Miner headline**. Up to 3 observations of
  confidence moderate or strong from the latest report, each ≤ 60 words, with the report date. It
  is passed **only if the report is ≤ 14 days old**, because a stale report is how a
  pattern-from-nothing happens. It goes to each agent in `_EVIDENCE_AGENTS` that is dispatched
  (the same allow-list, so never the Research Agent), and once into `synthesizer_input` (the
  eighth site, `synthesizer.md:312`; LOCAL 8).
- When #9 lands (4f), both blocks go to non-quick dispatches only, because quick mode skips the
  scan that reads them.
- **W&V's flow cross-check** (`work_vocation.md:63–70`) needs MW and PH output it can never see,
  since all three run in parallel. It now reads today's logged `wellbeing` and `health` fields
  from its prefetch. The instruction edit is in the closing round.
- The Coordinator's false "Prime Directive and Mission in your system prompt" claim: § 2,
  opening round.

**Files.** `core/orchestrator.py` (one parse helper; one append in the dispatch loop);
`core/prefetch.py` (the headline provider).

**Tests.**
1. Flags are present in `coord_output`: every `_EVIDENCE_AGENTS` directive carries them, and
   the Diarist, fire-and-forget agents and **`research_agent`** do not (the Research Agent's
   directive is asserted byte-identical to the Coordinator's).
2. Flags absent: nothing added.
3. A malformed section is ignored.
4. Headline omitted when the report is older than 14 days, missing or shapeless.

**Cost.** **Run:** ~40 tokens on 46% of dispatches, plus ~150 tokens headline × ~3 turns, ≈
$0.0002 per call. ≈$0.

### #20 and M16: the Pattern Miner's fixed steps run as code, and code writes its report

**What a user notices.** The weekly pattern analysis starts reaching the Coordinator again; it
has been silently missing for twelve weeks (§ 0). Observations drawn from it are current, not
three months old.

**Mechanism (4e; hard prerequisite: Stage 2's M6 merge has landed).**
- **Prefetch for `pattern_miner`** (the `/internal/session` path):
  1. step 1: `read_recent_insights(n=2)`;
  2. step 2: `read_wisdom()`, capped;
  3. step 3b: `get_log_window` for 7, 30 and 90 days (`max_entries` 45). Entries dated before
     2026-08-09 lose their free-text bands (`wellbeing.mood`, `wellbeing.intensity`,
     `health.energy`) and keep `sleep_hours`, per `pattern_miner.md`'s own rule;
  4. step 4: `find_duplicate_wisdom()` groups;
  5. **M16:** the data span (the first and last log dates on file) maps to the baseline-table
     row. That is exact, and is the selection the file does by hand at `:54–61`. Code also runs
     `get_baseline_context` and `read_baseline_periods` for each window. The statistical tools
     (`shuffled_null_score`, `score_against_anchors`, `create_semantic_anchor`) stay
     model-called: choosing what to test is judgement.
- **A real final round (review L4).** `_openai_compat_loop` (HEAD :5154) gains
  `final_round: bool = False, final_prompt: str = _FINAL_REPLY_PROMPT`, and
  `run_session_gemini` (:3917) passes both through.
  - When it is True and `max_iterations` is spent with the last message a tool result, the loop
    makes **one tools-off call**: `tools` omitted, a final prompt appended as a user message,
    mirroring `_openai_compat_stream`'s round (:5631). It returns that reply.
  - The prompt is a Pattern-Miner-specific `_PM_FINAL_PROMPT` ("Your tool budget is spent.
    Write the report now, in the output format, from what you have read."), passed as
    `final_prompt`. `_FINAL_REPLY_PROMPT` (:4522) says "reply to the user", and this run has no
    user.
  - `_run_single_agent` sets `final_round=True` for `pattern_miner` only. Every other caller's
    behaviour is unchanged: the default is False, and a test pins it.
- **Code writes the report only from a valid final reply** (`tools/pattern_report.py`), and only
  if the run did not call `write_insight_report` itself.
  - **Valid** means at least one block with `[EVIDENCE]`, `[OBSERVATION]` and `[CONFIDENCE]`
    present, and the text is not a tool-result body: not parseable as a JSON object or list, and
    not starting with "Error" or "Log written".
  - A valid reply is parsed into `{"date", "scale", "baseline_used", "observations": [{"evidence",
    "observation", "hypothesis", "confidence", "action"}]}` and written with
    `tools.pattern_miner.write_insight_report`.
  - **Invalid means no write.** The last real report stays the "most recent". Code logs a
    warning and writes a `PATTERN_REPORT_MISSING` quality event, so a failing Sunday reaches the
    machine log instead of vanishing again.
- **Tracker.** Step 7 stays a model call: Stage 2's M6 maps the `write_context_tracker` tool to
  `merge_pattern_findings`, which writes only `patterns`. When code wrote the report, code calls
  `merge_pattern_findings(patterns=[<up to 3 observation sentences>])` itself. **Never the
  replace-semantics writer.**
- The 8-round limit stays. Prefetch removes the 5 fixed rounds the run spends today (12 of 12
  measured runs reached them).

**Files.** `core/prefetch.py`; new `tools/pattern_report.py` (validate, parse and write, Amber);
`core/orchestrator.py`, Amber: `_openai_compat_loop` and `run_session_gemini` get the
`final_round` kwarg, and `_run_single_agent` gets a post-run hook for `pattern_miner` only.
`tools/pattern_miner.py`, `tools/baselines.py` and `tools/context_tracker.py` are read only;
`merge_pattern_findings` is Stage 2's.

**Tests.** `tests/test_pattern_report.py`:
1. A fixture final reply with three blocks gives a parsed report written once.
2. When the run already called the tool, there is no second write.
3. **Exhaustion (L4):** a stubbed client that returns tool calls for all 8 rounds gets exactly
   one more call with no `tools` and the final prompt, and its reply is returned. With
   `final_round=False` the old return is unchanged (a pin for every other caller).
4. **An invalid reply writes nothing:** a JSON tool-result body, an "Error…" string, and prose
   with no `[EVIDENCE]` block. The previous report file is unchanged and one
   `PATTERN_REPORT_MISSING` event is written.
5. Bands before 08-09 are stripped and `sleep_hours` is kept.
6. Span-to-baseline-row mapping at each table boundary.
7. The tracker path calls `merge_pattern_findings` and leaves `follow_ups` and `held_items`
   untouched.

**Cost.**
- **Run:** turn-1 input ≈ 40–60k tokens on 3.8 Flash, uncached, over about 3–4 turns ≈
  **$0.10–0.18/week**, $0.20–0.36 from 2027-01-01. Today it spends 8 turns producing nothing.
- **Ancillary:** `find_duplicate_wisdom` loads the embedder on the server (it already does
  mid-run).

**Risks.** Report parsing depends on the format the file mandates. Mitigation (revised): an
unparseable reply is **not** stored. It raises the quality event, so a format drift is seen
within a week.

### M4: held items get a date and are shown back

**What a user notices.** Something the assistant chose to hold back ("mention the sleep pattern
when you're less stressed") is eventually raised or consciously dropped, instead of vanishing.

**Finding while planning.** The premise is worse than the review stated. `held_items` is written
(replace semantics) and **never rendered into any prompt**. `load_recent_context` shows open
threads, patterns and follow-ups only. So the Synthesizer cannot re-send what it held, and each
write erases the last.

**Mechanism (4e, after Stage 2's tracker changes).**
- Store each entry as `{"text", "held_since"}`. Old bare strings are normalised on read, as
  `_normalize_open_threads` does.
- **An omitted key keeps them (review L9).** Today `write_context_tracker` writes
  `"held_items": held_items or []` (`tools/context_tracker.py:1526`), and `persist_context_block`
  passes `ctx.get("held_items")` (`core/orchestrator.py:2767`). A `[CONTEXT]` block without the
  key therefore erases every item. Revised:
  - `held_items is None` (key omitted, a partial salvage, a short reply) keeps the stored list
    exactly, `held_since` included;
  - an explicit `[]` clears it, because that is the Synthesizer dismissing them;
  - a list replaces it, with dates carried as below.

  This matches Stage 2's `merge_pattern_findings`, which leaves `held_items` as on disk, and
  Stage 2's #4 cap, which never touches `held_items`.
- On write, carry `held_since` forward by exact text, then by `_same_thread` anchor identity
  (the open-thread rule), or stamp today.
- Render for `audience == "synthesizer"` only:
  `**Held back (not yet raised):** <text> (held N days) | …`. All entries are shown, with no cap
  (S7.1).
- Update `_context_fingerprint` for the dict shape.

**Files.** `tools/context_tracker.py` (`write_context_tracker` held-items path; read
normalisation); `core/orchestrator.py` (`load_recent_context`, about 6 lines).

**Tests.** Additions to the tracker tests:
1. Re-sent text keeps `held_since`; reworded text keeps it; new text is stamped today.
2. A legacy string is normalised.
3. Rendered for the Synthesizer only.
4. Fingerprint stability.
5. **Omitted key (L9):** `persist_context_block({"open_threads": [...], "follow_ups": [...]})`
   with no `held_items` leaves the stored items and dates unchanged. `{"held_items": []}` clears
   them.
6. After Stage 2: a `merge_pattern_findings` call leaves dated held items byte-identical.

**Cost.** **Run:** ~30 tokens per held item on each Synthesizer turn (3.8 Flash, uncached), a few
items ≈ $0.0001/turn.

### M12: pending confirmations live as ledger `waiting` rows only

**What a user notices.** "Still waiting on the booking confirmation" is raised once when it is
due for a check, not re-stated from three stores.

**Mechanism.** Mostly Red (closing). Code part (4d): M13's code-written sub-dict carries no
`pending_items`, and the Logistics prefetch's `list_tasks` already shows `waiting` rows,
which the ledger surfaces once at `check_back`. That **is** the `PENDING_AGED` count, already in
code. Items that need **the user's** decision are asked in this turn's output and stored nowhere.
There is no migration of any old "pending" entries in Logistics' agent config: the presence door
cannot read that store to size it, and the closing-round text tells Logistics to open a `waiting`
row for any it meets.

**Tests.** Covered by M13's (no `pending_items` key written).

### M13: code writes Logistics' log entry from the actions that ran

**What a user notices.** Nothing directly, but Logistics drops one model round on about 57% of
its calls: it wrote its own log entry 57 times in 99 calls, measured.

**Mechanism (4d).** After a Logistics run, from **its own agent record's** successful tool calls,
code writes a **code-owned** sub-dict, `logistics.recorded_by_code` (review L10):
- `events_scheduled`: `write_calendar_event` and `update_calendar_event` title and start;
- `reminders_set`: `write_schedule`;
- `horizon_items`: `record_horizon_item` title and date;
- `coordination_opportunities`: parsed from the output's `COORDINATION_OPPORTUNITIES:` line.

**Append, never replace.** `_deep_merge` (`tools/logger.py:169`) replaces lists wholesale but
recurses into dicts.
- Code reads today's `logistics.recorded_by_code`, appends this run's entries, de-duplicates by
  (tool, uid or title, start), and writes the whole sub-dict back through `write_log`, so stamps
  and provenance apply.
- The model's own `logistics` writes never name `recorded_by_code`, so the deep merge keeps it
  across them. Earlier runs' actions survive both a later code write and a model write.
- Placement: `_run_single_agent`, after the run, `logistics` only. The model's own `logistics`
  write still lands until the closing round (C6), and stays harmless beside the sub-dict.

**DECISION 4-6, RULED (actions only on scheduled turns).** Action-derived lists are written on
any turn. The prose-derived `coordination_opportunities` is written on real user turns only:
an event that was scheduled is a fact in the world whoever started the turn, and the 10-29
self-re-raising failure came from model prose.

**Tests.**
1. A fake agent record with two writes and one failed write gives only the two.
2. No `pending_items` key.
3. A scheduled turn writes no `coordination_opportunities`.
4. A non-Logistics agent writes nothing.
5. **Two runs in one day (L10):** run 1 records event A; a model `write_log({"logistics":
   {"events_scheduled": ["X"]}})` follows; run 2 records event B. `recorded_by_code` then holds
   A and B, and the model's list holds X.
6. The same action seen twice is recorded once.

**Cost.** −1 Flash-Lite round on ~57% of Logistics calls (≈1.4 s, ≈$0.0015 each).

### M14: `[VERIFY]` calendar events re-checked when Logistics reads the calendar

**What a user notices.** An event saved while the conflict check was down no longer sits
unverified with nobody looking: the next time Logistics reads that day, the check is re-run and
a clash it hid is reported. Nothing is written to the user's calendar by a read (4-7 = no).

**Mechanism (4d, revised for review S6).**
- **Where:** in `dispatch_tool` (`core/orchestrator.py:2908`), after the call, when the tool is
  `read_calendar` and the **calling agent is `logistics`**. That is the same caller test Stage
  2's write guard uses there. It is not inside `tools/caldav.read_calendar`. Prefetch and the
  speculative read (4-2) call the handler directly, never through `dispatch_tool`, and so does
  the data-object reader (`tools/data_objects.py`). So the re-check runs only when Logistics
  itself asks, which is the ruling.
- **What:** for events in the result with `conflict_check_status == "FAILED"` that end in the
  future, at most 2, code runs **`tools.scheduling.check_calendar_conflicts(start, end, title,
  location=…, exclude_uid=uid)`**. That function only reads: it reports what is around a time
  and writes nothing. Its result is attached to the event in the returned read as `reverify`.
- **Once:** a uid already re-checked in this request (a set on the request trace) is not
  re-checked; the earlier `reverify` is reused.
- **Never written:** no `update_calendar_event`, no description note, no
  `note_calendar_write()`. Clearing `[VERIFY]` stays Logistics' own `update_calendar_event` call,
  made on the evidence (closing edit C7).
- **Prefetch** only counts: "N events still unverified" (§ 1 #22).

**DECISION 4-7, RULED (no): a read never writes.**

**Tests.** Stubbed CalDAV and `check_calendar_conflicts`:
1. Logistics' `read_calendar` through `dispatch_tool` with one FAILED future event gives one
   check call, and `reverify` is attached.
2. **No write:** the CalDAV PUT, `update_calendar_event` and `note_calendar_write` stubs are
   asserted uncalled in every test.
3. Another agent's `read_calendar`, a prefetch read and a direct `read_calendar()` call make no
   check call.
4. A second read in the same request reuses `reverify` (still one check call).
5. Cap of 2 respected.
6. A past event is ignored.

**Cost.** **Run:** one local conflict query per unverified event (CalDAV read, ≈1–2 s), only
on a Logistics read while such events exist. Frequency unmeasured (the calendar is outside the
read doors); expected rare.

### #9: quick mode wired (last, gated)

**What a user notices.** Routine messages ("had a coffee", "ran 5k") are handled faster and
without unrequested proactive observations. The medication check still runs on every Physical
Health dispatch, because it is code now.

**One function makes the prefix (review S1).** New
`_specialist_directive(agent, directive, complexity, *, code_added=False) -> str` in
`core/orchestrator.py`. It returns `"mode: quick\n\n" + directive` when `complexity == "quick"`,
`agent in QUICK_MODE_AGENTS` and `not code_added`; otherwise the directive unchanged.
`QUICK_MODE_AGENTS` = `physical_health`, `mental_wellbeing`, `relationships`, `work_vocation`,
`finance`, `recreation_hobbies`, `learning_growth`.
- `_dispatch_from_coordinator` calls it for every spec. A spec that code added (Stage 2's #2
  brief dispatches, which are `deep` anyway; the existing `delegated` data-object dispatch,
  whose `mode: "quick"` picks the model tier only) carries `code_added=True` and never gets the
  line (S6).
- **`tests/run_a4_safety.py run_one` (:465) calls it too.** When `--complexity quick`, the
  scenario prompt goes through `_specialist_directive(scenario["agent"], scenario["prompt"],
  complexity)` before `_run_single_agent`. The gate therefore sends exactly the text dispatch
  will send. `run_one_pipeline` is unchanged: there the Coordinator picks the mode, and the
  prefix now arrives through dispatch.
- **Logistics is excluded** (DECISION 4-8, RULED yes), and its quick section is deleted in the
  closing round (C33).
- The clinical veto: no clinical output path is removed. MW's quick section keeps all clinical
  rules by its own text. PH's `MEDICATION_MISSED_CRITICAL` is computed in code at its return
  (Stage 3 #8, in `_after_specialists` and `_run_single_agent`), in every mode.
- When this lands, #6's flags and headline go to non-quick dispatches only, since quick mode
  skips the scan that reads them.

**Gate, in this order (4f):**
1. Stage 3's #8 and 4b's counters have landed and passed.
2. Build `_specialist_directive` and the runner change. **Dispatch does not call the helper
   yet.** An offline test asserts the runner hands `_run_single_agent` a prompt starting
   `mode: quick` for a PH scenario under `--complexity quick`, and the unchanged prompt under
   `deep`.
3. **Live:** the clinical-quick suite (Mental Wellbeing and Physical Health) with the prefix,
   ≈$3–4, **stated to Mike before running**. Pass: every clinical-flag and
   `MEDICATION_MISSED_CRITICAL` scenario fires as on deep.
4. Only then wire `_dispatch_from_coordinator` to the helper.
5. **Live:** the pipeline suite (the Coordinator chooses quick; the prefix comes through
   dispatch), plus Stage 3's Finance fixtures under `--complexity quick`, ≈$3–4, stated first.

**Tests.** `tests/test_a4_complexity_threading.py` additions:
1. A quick directive to each of the 7 starts with `mode: quick`.
2. Logistics, `code_added` specs and deep dispatches do not.
3. The runner test in gate step 2.
4. `_specialist_directive` is the only producer of the string (a grep test over `core/` and
   `tests/run_a4_safety.py`).

**Cost.** **Run:** saves the scan's reasoning and rounds on 93% of dispatches. The size is
unmeasured until after; re-measure turns/call by mode with the § 0 scripts. **Build:** 2 A4 runs,
≈$6–8.

### Drops and reshapes found at plan time

1. **#22 prefetch for the Coordinator and Synthesizer: DROP.** Measured, there is nothing to
   prefetch: the Coordinator calls only `write_quality_event`, and the Synthesizer averages 1.23
   turns and opens with writes. So #22 adds no cache-floor exposure for either.
2. **M2 reshaped:** the stored tone shape only; never `get_tone_shape`, which seeds a background
   mailbox sweep and a model call.
3. **M16 reshaped:** the granted baseline tools do not pick a baseline row; `get_baseline_context`
   only finds labelled periods. Code computes the row from the data span (exact) and runs the
   context and period reads. The statistical tests stay with the model.
4. **#14 `PRACTICE_LAPSE`, `HOBBY_LAPSE`, `EXERCISE_GAP`:** evidence, not flags (S7.2, and
   goals carry no domain field).
5. **Not dropped, but bigger than stated:** M4 (held items never rendered) and #20 (the Pattern
   Miner writes nothing).
6. **Withdrawn in Revision 1:**
   - #16's draft/send word trigger (replaced by the ruled Stage 5 shape);
   - M14's write path (4-7 = no);
   - `FOOD_NOT_LOGGED` as a code flag (review L7).
7. **Rejected review findings:** none. All ten were checked against HEAD `8ef2edf` and held.

---

## 2. Red edits: OPENING round (final; none depends on new code)

Exact against **HEAD `8ef2edf`**; every line below was re-read there. Stage 1's `read_goals`
removals touch the same two routing files, so make all routing edits in one pass. **Both
routing files now also carry another chat's uncommitted Synthesizer grant line (:52 / :78).**
O1/O2 are disjoint from it, but the files cannot be staged wholesale: see § 5 item 1 (wait, or
`git add -p`).
4-5 is ruled, so nothing here is conditional.

**O1. `config/modules/routing.yaml:214`** (`learning_growth`)
- Current: `    allowed_tools: [read_log, write_log, search_memory, read_agent_config, write_agent_config, read_wisdom, read_data_object, write_archive, request_build]`
- Replacement (the comment goes on the line above):
  ```
      # open_task/update_task/list_tasks granted 2026-11-23 (instructions-to-code Stage 4, #15):
      # skill practice is a task-ledger habit, which computes streaks and misses. Parity.
      allowed_tools: [read_log, write_log, search_memory, read_agent_config, write_agent_config, read_wisdom, read_data_object, write_archive, open_task, update_task, list_tasks, request_build]
  ```
- Reason: #15 (LOCAL 4). Without the grant, Learning & Growth cannot open or mark a habit.

**O2. `config/modules/routing_cloud.yaml:384`.** The identical change and comment (parity).

**O3. `config/agents/coordinator.md:24–26`**
- Current:
  ```
  - **Prime Directive, Mission, Goals** — in your system prompt
  - **Recent logs** (last 5 days) and **session context** (open threads, follow-ups, held items) — in your system prompt
  - **Pattern Miner report** (most recent) — provided in the `[Pre-loaded context]` section of your input message
  ```
- Replacement:
  ```
  - **Goals and the user's profile** — in your system prompt. The Prime Directive and Mission are not loaded for you; weighing values is the Synthesizer's job.
  - **Recent logs** (last 5 days) and **session context** (open threads, patterns, follow-ups) — under `[Recent context]` at the head of your input message
  - **Pattern Miner report** (most recent) — in the `[Pre-loaded context]` section of your input message
  ```
- Reason: the honesty half of #6.
  - `_ROUTING_LAYER_AGENTS` loads goals and profile only (`_run_single_agent`, HEAD :5668).
  - Recent context rides the user message.
  - Held items are rendered to no one (M4 renders them to the Synthesizer only).
  - Prefix change is about +20 tokens against about 8k cached.

**O4. `config/agents/coordinator.md:239`**
- Current, end of the line: `Also call for any user-defined recurring habit or practice that should be tracked or prompted (workout, language practice, instrument, medication).`
- Replacement: `Also call for any user-defined recurring habit that should be tracked or prompted (workout, medication). Skill practice — a language, an instrument, a craft — goes to Learning & Growth, which keeps it as a habit on the task ledger.`
- Reason: one agent opens skill habits (4-5).

**O5. `config/agents/learning_growth.md:72`**
- Current: `2. **Track active skill goals.** Any capability requiring regular practice — a language, an instrument, a craft, a coding skill, a physical technique — needs frequency tracking, not just logging. For each active goal, note: last practice date, current streak or frequency, stated target, and whether the pace is on track. Flag when practice has gone quiet; skills with a maintenance requirement atrophy.`
- Replacement: ``2. **Track active skill goals on the task ledger.** A capability that needs regular practice — a language, an instrument, a craft, a coding skill, a physical technique — is a `habit` task (`open_task` with `every`/`times`/`on_days`, `domain: learning`). A practice the user reports is `update_task` done, with their words as evidence. The ledger keeps the streak, the misses and made-up sessions; read them from `list_tasks`, never keep your own count. Flag when practice has gone quiet; skills with a maintenance requirement atrophy.``
- Reason: #15. A relative date in a stored record is the class `tools/record_rules.py` exists to
  stop.

**O6. `config/agents/learning_growth.md:76`**
- Current, end of the line: `Has the user been here before?intellectual`
- Replacement: `Has the user been here before?`
- Reason: typo (sweep § 3).

**O7. `config/agents/learning_growth.md:149–155`**
- Current:
  ```
      "skill_goals": [
        {
          "skill": "Spanish",
          "last_practiced": "today",
          "frequency_recent": "daily",
          "on_track": true
        }
  ```
- Replacement:
  ```
      "skill_goals": [
        {
          "skill": "Spanish",
          "minutes": 20
        }
  ```
- Also insert one line after the closing fence at `:159`: `Streaks and dates live on the skill's ledger habit, not in the log.`
- Reason: #15, "drop the streak fields from `write_log`".

**O8. `config/agents/learning_growth.md:169–171`**
- Current:
  ```
  - Maintain a running record of active skill goals via `write_agent_config` (`agent_name: "learning_growth"`) or `write_archive` (`category: skills`)
  - For each goal: target frequency, last practiced date, current streak, milestone markers
  - A goal not practiced in its maintenance window is flagged with `PRACTICE_GAP`
  ```
- Replacement:
  ```
  - Each active skill goal is a ledger habit (see What you do, step 2); keep its milestone markers and study plan in `write_agent_config` (`agent_name: "learning_growth"`)
  - A habit the ledger shows missed past its maintenance window is flagged `PRACTICE_GAP`, with the days since it was last done
  ```
- Reason: #15, one home for the streak.

**O9. `config/agents/learning_growth.md`, after `:216`** (the `read_agent_config` bullet, the
last bullet of § Tools available)
- Insert:
  ```
  - `open_task` — open a skill-practice habit (`kind: habit`, `every`, `times`, `on_days`, `domain: learning`) when the user sets a skill goal they want to practise regularly.
  - `update_task` — mark a practice done (`action: done`, the user's words as `evidence`).
  - `list_tasks` — the ledger, including your skill habits with their streaks and misses.
  ```
- Reason: a grant must be named, or `check_agent_tools` reports it as granted-but-never-named.

**Opening-round count: 9 edits** (5 files). Afterwards run `python3 scripts/check_agent_tools.py`:
expect exit 0, with the three Learning & Growth tools named and granted.

---

## 3. Red edits: CLOSING round (final; each deletes or rewrites text the Stage 4 code now carries)

The current text is **HEAD `8ef2edf`**. The opening round (O-edits above, and the other stages')
will shift line numbers, so each edit is anchored by its quoted current text, which is unique in
its file. Re-read before editing. **Stage 3's closing edits X1–X4 also touch
`physical_health.md`'s medication text**; C24 is written so it touches only the "read at session
start" clause. Apply Stage 3's first if they overlap.

| # | File · HEAD line | Current text (exact) | Replacement | Carried by |
|---|---|---|---|---|
| C1 | `logistics.md:176` | `1. **Load active context.** Call \`read_agent_config\` at session start to load execution preferences, active plans, and open pending items, and \`list_tasks\` for the obligations — recurring and one-off.` | `1. **Start from what is handed to you.** Your settings, open tasks (the obligations, recurring and one-off), today's and tomorrow's calendar and the intake count are in \`PREFETCHED\` at the head of your input. Call a tool only for what is not there.` | 4a |
| C2 | `logistics.md:76` | `Read today's and tomorrow's calendar for where the user will physically be, then scan what could be satisfied *there*, unasked.` | `Today's and tomorrow's calendar are in \`PREFETCHED\`: read them for where the user will physically be, then scan what could be satisfied *there*, unasked.` | 4a |
| C3 | `logistics.md:73` | the whole line, from `2. **Pending confirmations that have aged.**` to `not on a fixed check cadence.` | `2. **Waiting on someone else.** Something blocked on another person's move — an awaited email, a booking to confirm — is a ledger \`waiting\` row (\`open_task\` with \`kind: waiting\` and \`check_back\`). The ledger raises it once when it is due. Re-checking it on any session is fine; re-stating an unchanged one is not — surface it only when something changed.` | 4d (M12) |
| C4 | `logistics.md:182` | `Flag these as \`PENDING_CONFIRMATION\` — do not guess or assume.` | `Flag these as \`PENDING_CONFIRMATION\` — do not guess or assume. One blocked on someone else's move also gets a \`waiting\` row; one that needs the user's decision is asked now and stored nowhere else.` | 4d (M12) |
| C5 | `logistics.md:222` | `- **PENDING_AGED** — a \`PENDING_CONFIRMATION\` item has gone unaddressed across multiple sessions` | delete the line (the ledger raises a `waiting` row at `check_back`) | 4d (M12) |
| C6 | `logistics.md:240–252` | from `Write to \`write_log\` under the \`logistics\` field:` through the closing fence of the JSON block (the block holds \`events_scheduled\`, \`reminders_set\`, \`pending_items\`, \`horizon_items\`, \`coordination_opportunities\`) | `Code writes your log entry from the calls you made (events, reminders, horizon items) and from your \`COORDINATION_OPPORTUNITIES:\` line. Do not call \`write_log\` to record them.` | 4d (M13) |
| C7 | `logistics.md:286` | `when you see one, re-run \`check_calendar_conflicts\` on it and clear your own uncertainty about it, don't leave it silently unverified.` | `when you read that day with \`read_calendar\`, the check is re-run for you and attached to the event as \`reverify\`. If it is clear, retitle the event without \`[VERIFY]\` with \`update_calendar_event\`; if it shows a conflict, judge it like any other.` | 4d (M14) |
| C8 | `relationships.md:203` | `1. **Load active context.** Call \`read_agent_config\` at session start to load the user's social energy profile, communication style notes, and any active relationship priorities or commitments noted in previous sessions.` | `1. **Start from what is handed to you.** Your settings (social energy profile, style notes, active priorities) are in \`PREFETCHED\` at the head of your input.` | 4a |
| C9 | `relationships.md:211` | `When a person is mentioned, check if they exist in the CRM via \`read_contact\`. If not, create a record via \`write_contact\`. Log the interaction via \`log_interaction\`. Periodically call \`list_contacts(overdue_only=true)\` to surface who is due for contact.` | `People named in the message who match a contact exactly arrive with their records, with the overdue and upcoming-dates lists. Look up only a name not resolved there; a "possibly X (name prefix)" line means read X before creating anyone. If no record exists, create one via \`write_contact\`. Log the interaction via \`log_interaction\`.` | 4c (#12, M3) |
| C10 | `relationships.md:59` | `Given the contact database and upcoming dates, surface outreach moments proactively:` | `Given the overdue and upcoming-dates lists handed to you, surface outreach moments proactively:` | 4c (M3) |
| C11 | `relationships.md:163` | `**Before drafting to a saved contact, call \`get_tone_shape\`.**` | `**Before drafting to a saved contact, use their tone shape.** A resolved recipient's stored shape arrives with their record; call \`get_tone_shape\` only when it says none is stored.` | 4c (M2) |
| C12 | `relationships.md:323` | `**Call it before drafting any message to a saved contact.**` | `**Call it before drafting to a saved contact whose record arrived without a stored shape.**` | 4c (M2) |
| C13 | `relationships.md:313` | the whole paragraph, from `**Read back every new name, email, physical address, handle, or phone number` to `not as settled the moment it's saved.` | `**You never speak to the user, so you do not read details back.** The reply reads back every new name, email, address, handle and number you saved, built by code from your call's arguments. Your part is to save exactly what was said — and the near-match judgement below.` | 4c (M1) |
| C14 | `relationships.md:111–112` | `…the failure case is precisely the one nobody` / `thought to flag.` (a hard line break; `thought to flag.` is unique in the file) | append: ` What is on file naming the people in this turn arrives as \`ON FILE ABOUT PEOPLE NAMED HERE\`; check it, and search further only for someone not listed there.` | 4c (#16) |
| C15 | `work_vocation.md:108` | `1. **Load active context.** Call \`read_agent_config\` at session start to load any active career plan, project list, or professional goals stored from previous sessions.` | `1. **Start from what is handed to you.** Your stored career plan, projects and professional goals are in \`PREFETCHED\` at the head of your input.` | 4a |
| C16 | `work_vocation.md:215` | `Call at session start for ongoing projects.` | delete the sentence (prefetched) | 4a |
| C17 | `work_vocation.md:70` | `Include a \`CROSS_DOMAIN_SIGNAL\` note in your output when MW or PH data either reinforces or complicates a flow finding.` | `Mental Wellbeing and Physical Health run beside you, so you never see their output: use today's logged wellbeing and health fields in \`PREFETCHED\`. Include a \`CROSS_DOMAIN_SIGNAL\` note when they either reinforce or complicate a flow finding.` | 4a (#6) |
| C18 | `recreation_hobbies.md:116` | `1. **Load active context.** Call \`read_agent_config\` at session start to load known leisure preferences, active hobby goals, and any noted patterns about how this user rests and recovers.` | `1. **Start from what is handed to you.** Your stored leisure preferences, hobby goals and recovery patterns are in \`PREFETCHED\` at the head of your input.` | 4a |
| C19 | `recreation_hobbies.md:169`, `:171` | `- **LEISURE_GAP** — no chosen activity mentioned in 5+ days` · `- **HOBBY_LAPSE** — a hobby the user has mentioned enjoying hasn't come up in a long time` | `- **LEISURE_GAP** — no chosen activity in 5+ days: the counted evidence gives the days since leisure was last logged, recorded only when you were consulted; judge the flag from that` · `- **HOBBY_LAPSE** — a hobby the user enjoys has gone quiet: the evidence gives the days since each was last logged; you judge how long is "a long time"` | 4b |
| C20 | `physical_health.md:77` | `4. **Flag what's missing or concerning.** No food logged today? Poor sleep two nights running? Exercise not logged in a week? Flag it for the Synthesizer.` | `4. **Flag what's missing or concerning.** The counted evidence gives the days since sleep, exercise, food and any substance use were last logged; code sets SLEEP_POOR, SLEEP_ACUTE and ENERGY_CRASH itself after you reply. Flag the rest from the evidence.` | 4b |
| C21 | `physical_health.md:107` | `- **FOOD_NOT_LOGGED** — no eating recorded today; pass to Synthesizer: "I don't think you mentioned eating today — have you had anything?"` | `- **FOOD_NOT_LOGGED** — after the day's cut-off, no meal in the meals log and no food logged today (the counted evidence says so); pass to Synthesizer: "I don't think you mentioned eating today — have you had anything?" A meal the user mentions this turn is being recorded — do not flag then.` | 4b |
| C22 | `physical_health.md:108`, `:109`, `:114` | the `SLEEP_POOR`, `SLEEP_ACUTE` and `ENERGY_CRASH` lines, each beginning `- **SLEEP_POOR** —`, `- **SLEEP_ACUTE** —`, `- **ENERGY_CRASH** —` | each line keeps its definition and gains, after the flag name: `**set by code after your reply — do not set it yourself.**` | 4b |
| C23 | `physical_health.md:110`, `:111` | `- **SLEEP_MISSING** — no sleep data for 2+ days` · `- **EXERCISE_GAP** — no exercise logged in 5+ days (if exercise is part of user's goals)` | `- **SLEEP_MISSING** — no sleep data for 2+ days, from the counted evidence` · `- **EXERCISE_GAP** — no exercise logged in 5+ days, from the counted evidence (if exercise is part of user's goals)` | 4b |
| C24 | `physical_health.md:142`, `:206` | `Read it at session start to inform medication checks.` · `at session start` (in the `read_agent_config` bullet: `…or any structured physical health plan at session start.`) | `It is in \`PREFETCHED\`, with "Medication taken today".` · delete `at session start` | 4a |
| C25 | `physical_health.md:122` | `- **CESSATION_SUPPORT** — user is on an active cessation program; check streak and offer support if relevant` | `- **CESSATION_SUPPORT** — user is on an active cessation program. The counted evidence gives the last logged use and how many days have a health log since; never read that gap as days clean — no log is not abstinence. Offer support if relevant.` | 4b (M17) |
| C26 | `mental_wellbeing.md:245` | `Call at session start if relevant.` | delete the sentence (prefetched) | 4a |
| C27 | `mental_wellbeing.md:153`, `:154` | `- **PRACTICE_LAPSE** — a meaningful mental health practice (meditation, journaling, therapy, exercise) has gone quiet; specify what and how long` · `- **SLEEP_CONCERN** — sleep logged as poor or disrupted for 2+ days (downstream wellbeing signal, not primary domain)` | `…has gone quiet; the counted evidence gives the days since each practice was last listed — specify what and how long` · `…for 2+ days, from the counted night series (downstream wellbeing signal, not primary domain)` | 4b |
| C28 | `learning_growth.md:216`, `:102`, `:108` | `Call at session start when skills requiring frequency tracking are in progress.` · `specify days since last logged practice` · `- **LEARNING_GAP** — no learning or growth activity of any kind mentioned in 2+ weeks, if growth is a stated priority` | delete the sentence (prefetched) · `specify the days since it was last done, from your skill habits in \`PREFETCHED\`` · `…in 2+ weeks, from the counted evidence (recorded only when you were consulted), if growth is a stated priority` | 4a, 4b |
| C29 | `finance.md:229` | `- \`read_agent_config\` — read back stored budget structure, financial plan, or tax notes at session start. Use \`agent_name: "finance"\`.` | `- \`read_agent_config\` — your stored budget structure, financial plan and tax notes are in \`PREFETCHED\`; call it for a specific key. Use \`agent_name: "finance"\`.` | 4a |
| C30 | `pattern_miner.md:99–108` | steps `1.` (`read_recent_insights`), `2.` (`read_wisdom`), `3b.` (`get_log_window`), `4.` (the `find_duplicate_wisdom` half) and `6.` (`write_insight_report`) | the protocol opens: `Already in your input: the two most recent reports, the wisdom store, the logs for each window (bands before 2026-08-09 removed), the duplicate groups, your baseline row for the data span, and any labelled baseline periods.` Steps 1, 2 and 3b are deleted. Step 4 becomes `consolidate each duplicate group handed to you with \`merge_wisdom_entries\`…`. Step 6 becomes `Your report text is written to the insights store for you; do not call \`write_insight_report\`.` Steps 3a, 3c, 3d, 5 and 7 are unchanged; step 7's tool is now Stage 2's merge-only handler. | 4e |
| C31 | `pattern_miner.md:52` | `Select the most sophisticated baseline the available data supports.` | `Your baseline row for the data span is handed to you; use it and state it.` (the table stays as reference) | 4e (M16) |
| C32 | `synthesizer.md:265` | `An item held across multiple sessions without surfacing should be escalated: either find the right moment to surface it, or consciously dismiss it with a note.` | `Each held item shows how many days it has been held; past a week, either find the right moment to surface it or dismiss it with a note. Leaving \`held_items\` out of the block keeps them; an empty list dismisses them all.` | 4e (M4) |
| C33 | `logistics.md:12–16` | the `## Quick mode` section: heading, the line `If the Coordinator directive includes \`mode: quick\`: … Skip the horizon scan. Do not proceed to Deep mode.`, and its trailing `---` | delete the section (4-8: Logistics never receives the quick line) | 4f |

**Closing-round count: 33 edits** (9 files).
- `logistics.md` 8 (C1–C7, C33);
- `relationships.md` 7 (C8–C14);
- `work_vocation.md` 3;
- `recreation_hobbies.md` 2;
- `physical_health.md` 6 (C20–C25);
- `mental_wellbeing.md` 2;
- `learning_growth.md` 1 row with 3 hunks (C28);
- `finance.md` 1;
- `pattern_miner.md` 2;
- `synthesizer.md` 1.

Not an edit, on purpose: **Logistics keeps `write_log`.** It still logs non-action notes.

**Cache floor.** C20–C25 and C26–C27 shrink the Physical Health and Mental Wellbeing prefixes,
which `_pad_for_vertex_cache` pads. C32 adds about 15 tokens to the Synthesizer's prefix (about
25k cached). Nothing in this round touches the Coordinator. Check after deploy: every cached
specialist's turn-1 `cached_tokens` is non-zero in the trace.

---

## 4. Builder briefs (each: `general-purpose`, `isolation: "worktree"` from HEAD, commits nothing)

**Order: 4a → 4b → 4c → 4d → 4e → 4f.**
- 4c and 4d are independent of each other and could share one builder run.
- **4b needs Stage 3's `_after_specialists` landed.**
- **4e needs Stage 2's M6 (`merge_pattern_findings`) and #4 landed.**
- 4f waits on its gates.

One model for all: **build with Opus 5.5 and review each diff with Fable 5.1** (driver rule).

Common to every brief:
- work from HEAD;
- never touch `config/agents/*.md`, `config/modules/routing*.yaml` or
  `core/{router,persona,scheduler,spend_guard}.py`;
- make no live model call: stub `_run_single_agent`, `run_session`, the OpenAI client and every
  meter;
- use tmp persona dirs only, and generic names in code, comments and tests.

**4a: prefetch engine, `PROACTIVE_FLAGS`, speculative calendar** (#22, #6 flags half, 4-2,
the taint, the unverified count).
- `core/prefetch.py` (new); `config/modules/prefetch.yaml` (new).
- `core/orchestrator.py`, Amber:
  - the `_run_single_agent` `prefetch` kwarg and specialist-branch append (HEAD :5668);
  - `build()` in the dispatch worker (`_dispatch_from_coordinator`, :6925);
  - the `PROACTIVE_FLAGS` parse and append, with the `_EVIDENCE_AGENTS` allow-list;
  - the speculative calendar submit in both twins (`run_pipeline_session` :7766 and
    `_run_pipeline_session_stream_inner` :8093, the streaming body; :8026 is only its wrapper);
  - the `prefetched_untrusted` OR in `_file_wisdom_proposals` (:6490).
- Tests: `tests/test_prefetch.py` items 1–14, plus the #6 tests 1–4.
- *Build ≈110k.*

**4b: counters, M17 and skill habits** (#14, M17, #15 evidence).
- `tools/domain_counters.py` (new); `config/modules/counters.yaml` (new).
- `tools/logger.py`: `_written_on` in `write_log` only. Stage 2's #1 is in
  `write_quality_event`, the same file.
- `core/prefetch.py`: the evidence and habit providers.
- `core/orchestrator.py`: step 6 inside Stage 3's `_after_specialists`, and its bundle line in
  both twins.
- **If `_after_specialists` is absent, stop and report; do not add a parallel hook.**
- Tests: `tests/test_domain_counters.py` items 1–11, additions to
  `tests/test_log_field_timestamps.py`, and the L&G habit test.
- *≈80k.*

**4c: Relationships at dispatch** (#12, M2, M3, M1, #16).
- `tools/contact_resolution.py` (new); `tools/recipient_context.py` (new);
  `core/prefetch.py` (providers).
- `core/orchestrator.py`: `_readback_block` in both twins, and a request-scoped snapshot.
- Read only: `tools/crm.py`, `tools/heard_names.py`, `tools/tone.py`, `tools/data_objects.py`,
  `tools/obligations.py`, `tools/wisdom.py`, `tools/profile.py`.
- Tests: `tests/test_contact_resolution.py` items 1–14 (including #16's six in
  `tests/test_recipient_context.py`), and M1's 1–5.
- *≈85k.*

**4d: Logistics' own records** (M13, M12 code half, M14).
- `core/orchestrator.py`:
  - a post-run hook for `logistics` in `_run_single_agent`;
  - the read-only `read_calendar` re-check in `dispatch_tool` (:2908), for caller `logistics`
    only.
- New `tools/logistics_log.py` (the `recorded_by_code` append).
- `tools/scheduling.py` and `tools/caldav.py` are read only; **no calendar write path is
  added**.
- Tests: M13's 1–6 and M14's 1–6.
- *≈45k.*

**4e: Pattern Miner, its headline, held items** (#20, M16, #6 headline half, M4).
- `core/prefetch.py`; `tools/pattern_report.py` (new).
- `core/orchestrator.py`:
  - the `final_round`/`final_prompt` kwargs on `_openai_compat_loop` (:5154) and
    `run_session_gemini` (:3917);
  - the `pattern_miner` post-run hook;
  - the headline into directives and `synthesizer_input`;
  - the `load_recent_context` held-items render (:1174).
- `tools/context_tracker.py`: held items and the omitted-key rule. This comes after Stage 2's M6
  and #4 in the same file.
- Tests: `tests/test_pattern_report.py` items 1–7, the tracker additions 1–6, and the headline
  tests.
- *≈80k.*

**4f: quick mode** (#9).
- `core/orchestrator.py`: `_specialist_directive`, then the dispatch loop.
- `tests/run_a4_safety.py` (Green): `run_one` calls the helper.
- Tests: `tests/test_a4_complexity_threading.py` 1–4; live per the gate order.
- *≈25k, plus ≈$6–8 live.*

**Stage total:** ≈425k build tokens (Revision 1 adds about 40k: M17, #16 at full shape, the
final round, the runner helper), plus ≈160k for Fable diff reviews, plus ≈$6–8 of live A4.

Cost classes:
- **Run:** ≈ +$0.02–0.04/day/user (prefetch), plus $0.10–0.18/week (Pattern Miner), minus one
  Flash-Lite round on most Logistics and Relationships calls.
- **Ancillary:** CalDAV reads (4-2, M14) and `_written_on` bytes.
- **Unseen:** none. Nothing created here persists between calls except the log stamps and
  `recorded_by_code`, which live in the day files they describe. The speculative read, the
  snapshot and the re-checked-uid set all die with the request.

---

## 5. Collision notes

1. **The other chats: plan against HEAD `8ef2edf`.** A **new** set of uncommitted edits, from
   other chats, appeared after the revision began (the ranking Part B phase 3 work and the
   WhatsApp work). Hunks read with `git diff HEAD`, and where they sit against Stage 4's:

   | File | Their hunks (HEAD lines) | Stage 4's hunks | Near? |
   |---|---|---|---|
   | `core/orchestrator.py` | `session_kind` :362–380; `register_tools` :1519, :1590, :1697; `_record_reported_doses`/`_horizon_block` :6659–6720 (a `user_turn` kwarg plus the weekly-priorities block); `_close_turn_bookkeeping` :7678; **the `_horizon_block(...)` call just before `synthesizer_input` in both twins, :7932 and :8225** | `load_recent_context` :1174 (4e); `dispatch_tool` :2908 (4d); `_openai_compat_loop` :5154 and `run_session_gemini` :3917 (4e); `_run_single_agent` :5668 (4a, 4d, 4e); `_file_wisdom_proposals` :6490 (4a); `_dispatch_from_coordinator` :6925 (4a, 4f); Stage 3's `_after_specialists` after :6637 (4b); **the `synthesizer_input` builds in both twins, :7934–7950 and :8229–8245 (4b, 4c, 4e bundle lines)**; the speculative calendar submit before the Coordinator call in both twins (4a) | **Yes, twice.** (1) Our `synthesizer_input` lines are 2–10 lines below their `_horizon_block` edit in both twins. (2) Stage 3's wrapper, which hosts 4b, goes directly above their `_horizon_block` hunk at :6659. The rest are ≥150 lines apart. |
   | `config/modules/routing.yaml` / `routing_cloud.yaml` | the Synthesizer's `allowed_tools`, :52 / :78 | **O1/O2**, Learning & Growth's `allowed_tools`, :214 / :384 | Same files, disjoint hunks (≈160 / ≈300 lines apart). **The opening round cannot stage these files wholesale.** Wait for that chat to commit (the precedent ruling), or stage O1/O2 with `git add -p` plus the HEAD export-and-import check. Under the driver's rule this is a stop-and-ask. |
   | `config/agents/synthesizer.md` | :407 (one added line) | C32 at :265 (closing round) | No (≈140 lines apart). Same file, so diff before staging. |
   | `tools/schedule.py` | `write_schedule` :47–180, :246–306, schema :380 | none; **M13 only reads `write_schedule`'s trace args and result** for `reminders_set` | No edit overlap. **Re-read `write_schedule`'s argument and result shape when 4d starts**: their hunks change it. |
   | `core/actions.py` | `ACTION_TOOLS` :78 (`record_signal`) | none (read only) | No. |
   | `tools/obligations.py` | :1369, :1911 (`open_task`), :2997, :3427, :4138 (`consult_index`) | none; read only (4b and 4c view functions) | No edit overlap. **4b/4c read the view functions after that chat commits.** |
   | `tools/day_plan.py`, `tools/ranking.py`, `tools/day_plan_config.py`, `config/modules/{day_plan,ranking}.yaml` | theirs | none | No. |
   | `core/server.py`, `tools/intake_whatsapp.py`, `static/index.html`, two tests, `android/` | WhatsApp chat | none (Step 0 only **called** `/monitor/traces`) | No. |

   Before staging any file, `git diff` it (deploy rule 4). The untracked `tools/ranking_review.py`
   that their `_horizon_block` hunk imports is theirs; Stage 4 must not commit `core/orchestrator.py`
   wholesale while their hunks are in it.
2. **Stage 2.**
   - `tools/context_tracker.py`: M6 (`merge_pattern_findings`, which leaves `held_items` as on
     disk) and #4 (a cap on `open_threads` only) land first. M4's omitted-key rule and
     `held_since` stamping are in `write_context_tracker`'s held-items lines only and agree
     with both. **#20 must not land before M6.**
   - `persist_context_block` (:2747): Stage 2 adds `routing_miss` (M11). M4 needs no change
     there, because the omitted key already arrives as `None`.
   - `dispatch_tool` (:2908): Stage 2's write guard (before the call) and 4d's `read_calendar`
     re-check (after the call) sit in the same function. They are separate hunks with the same
     caller test.
   - `tools/logger.py`: Stage 2's #1 edits `write_quality_event`; 4b edits `write_log`.
   - Stage 2 forces `deep` for MW/PH on the two sessions; 4f's `code_added` rule keeps quick
     off them.
3. **Stage 3.**
   - `_after_specialists` hosts 4b's counted-signals step (step 6, after #13).
   - The A4 runner calls that wrapper, and 4f adds `_specialist_directive` to `run_one`. Both
     are `tests/run_a4_safety.py` hunks; apply Stage 3's first.
   - Stage 3's #8 also runs at Physical Health's return in `_run_single_agent`. 4a's prefetch
     append and 4d/4e's post-run hooks sit in the same function, as separate `agent_name`
     branches.
   - `physical_health.md` closing edits X1–X4 (Stage 3) and C20–C25 (here) are in the same
     file. C24 is limited to the "read at session start" clause.
   - M17 is built here (4b).
   - If #13's Finance totals reach Finance through the wrapper's bundle line, 4a's Finance
     prefetch does not repeat them.
4. **Stage 1.** The same two routing files in the opening round: one pass.
5. **Stage 5.**
   - #16 is built here, in Stage 5's ruled shape; Stage 5 builds nothing for it.
   - #19/D7's `FROM THE SPECIALISTS` block also parses specialist output after dispatch; keep it
     separate from `COUNTED SIGNALS`.
   - #7 touches `logistics.md`, as C1–C7 and C33 do. Apply in one pass at the closing round.
   - Stage 5's research scrub runs on the Research dispatch, which receives neither prefetch
     nor flags from this stage.
6. **`[DB-1029-09]` (reply latency).** Its plan covers Synthesizer thinking and deferral, not
   prefetch. The shared surface is the pipeline twins; coordinate if it is live at the same
   time.
7. **A8 (pending refactor).** The new code lives in new modules (`core/prefetch.py`, `tools/*`),
   so the orchestrator gains only hook calls and two kwargs. A8 places `_specialist_directive`,
   `_readback_block` and the post-run hooks as pipeline concerns beside
   `_dispatch_from_coordinator`, and the `final_round` kwarg with `_openai_compat_loop` in
   `core/providers.py`.

---

## 6. Test suites to re-run (every sub-build)

Offline:
```
python3 -m pytest tests/test_prefetch.py tests/test_domain_counters.py tests/test_contact_resolution.py \
  tests/test_recipient_context.py tests/test_pattern_report.py tests/test_heard_names.py \
  tests/test_crm_dedup_guards.py tests/test_crm_merge_guard.py tests/test_crm_contact_info_merge.py \
  tests/test_crm_placeholders.py tests/test_tone_own_copies.py tests/test_log_field_timestamps.py \
  tests/test_medication_taken.py tests/test_medication_tier.py tests/test_context_tracker_multiprocess.py \
  tests/test_task_ledger.py tests/test_task_ledger_wiring.py tests/test_task_ledger_consult.py \
  tests/test_horizon_ledger.py tests/test_data_objects.py tests/test_caldav_multi_calendar.py \
  tests/test_calendar_update_in_place.py tests/test_review_2026_11_05_orchestrator.py \
  tests/test_a4_complexity_threading.py tests/test_intake_pipeline.py
python3 scripts/check_agent_tools.py      # after each Red round: L&G grants named and granted
python3 scripts/check_claude_md_claims.py
bash scripts/qa_sweep.sh
```
Also:
- Stage 2's tracker suites (its § 6 list) after 4e, because M4 edits the same writer.
- Stage 3's `tests/test_medication_check.py` after 4b and 4f.
- The deploy-rule-4 check: export HEAD to a clean directory and import `core.orchestrator`
  there, because the new modules are untracked until committed.

Live (stated before running):
- 4f, gate step 3: clinical-quick **with** the `mode: quick` prefix via `_specialist_directive`,
  ≈$3–4.
- 4f, gate step 5: the pipeline suite plus the Finance fixtures on quick, ≈$3–4.
- A8's gate, `tests/run_knowledge_routing.py --persona danny_park`, once at stage end (small,
  under $1).

**Mike's live checks after deploy** (for the driver's deploy list):
1. **4a.** Ask about tomorrow's plans. In The Book, Logistics' first turn is not
   `read_calendar`. Pass: turns/call on the § 0 script below 4.0 over a week.
2. **4b.** After 14:00 on a day with a lunch in the meals log, ask anything Physical Health
   answers. Pass: no `FOOD_NOT_LOGGED` line in `COUNTED SIGNALS`.
3. **4c.** Name a known contact mid-sentence. Pass: no `search_contacts` call by Relationships
   for that name.
4. **4d.** Schedule two events in separate messages the same day. Pass: the day's log
   `logistics.recorded_by_code.events_scheduled` carries both.
5. **4e.** Next Sunday 09:00. Pass: `vm_read.py presence insights` reports a count of 2, a new
   dated report, and no `PATTERN_REPORT_MISSING` event.
6. **4f.** A routine "ran 5k". Pass: the PH directive starts `mode: quick` and the medication
   flag still fires on the A4 fixture.

---

## Build-time amendments (driver, 2026-11-23, from the Fable re-check of Revision 1)

The re-check found nothing structural and confirmed closures 1, 2, 3, 4, 5, 8 and 10. The builder
applies these four local fixes; each is part of the sub-build's acceptance.

1. **M4, held items are merged, never replaced (4e).** An incoming `held_items` list is *added*
   to the stored list (deduplicated by text, each keeping its first `held_since`). An item leaves
   only when the Synthesizer names it in an explicit `held_dropped` list, or raises it. `[]` and
   an omitted key both change nothing. C32 is rewritten to describe `held_dropped`, not
   omit-versus-empty. Tests cover `[]`, `[new]` on top of two stored items, and `held_dropped`.
2. **FOOD_NOT_LOGGED, one source of truth (4b).** Physical Health's pre-dispatch evidence carries
   "food logged today: yes/no", computed by code from `health.food_logged` **and** today's
   `meals` data object. C21 tells Physical Health to raise `FOOD_NOT_LOGGED` only when that line
   says no and the user's message does not mention eating. Code's post-return `COUNTED SIGNALS`
   uses the same function. A test covers a meal in the meals log, nothing in `health`, and no
   flag from either.
3. **#14 counters run wherever Physical Health (and each counted specialist) returns (4b).**
   They sit at the same `_run_single_agent` post-return hook as Stage 3's #8, not only in
   `_after_specialists`, so `run_subagent` follow-ups, the weekly review and fire-and-forget runs
   get them. Writes on those paths are stamped from the trace's real-user-turn status, not
   `unknown`. C22 lands only after a test of every path, the same rule as Stage 3's X1–X4.
4. **M14 reads structured events, never the wrapped string (4d).** `read_calendar` returns
   `events` as one `<untrusted_content>` string. The re-check and prefetch's "N events still
   unverified" line come from a new read-only helper in `tools/caldav.py`, which returns the
   structured rows (`conflict_check_status`, `end`, `uid`) from the same fetch path before
   wrapping. `read_calendar` itself does not change, and nothing parses text out of the wrapper.
   This is the only addition to `caldav.py`. It is Amber and read-only.
