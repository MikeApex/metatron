# Review — agent instructions → code sweep (2026-11-23)

*Independent read of [agent_instructions_to_code_sweep_2026-11-23.md](agent_instructions_to_code_sweep_2026-11-23.md).
Read-only: nothing edited, filed, deployed or called live. The brief names Fable 5.1; the session
reports itself as Fable 5.2. Read in full: Coordinator, Synthesizer, Logistics, Relationships,
Physical Health, Mental Wellbeing, the three `synthesizer_*.md` modules, the eight "nothing to
move" files and `tone_profiler`; the remaining specialists past their shared boilerplate;
Diarist, Pattern Miner, Research Agent. Skimmed: Goals Interviewer. Not opened:
`capture_extractor`, `intake_extractor`, `goals_interview_reference`. Code read:
`_run_single_agent`, `_dispatch_from_coordinator`, `_file_horizon_items`, `_handle_user_correction`,
`_goals_section`, `session_kind`, `has_real_user_turn`, `persist_context_block`,
`write_context_tracker`, `write_quality_event`, `resolve_model`, `run_subagent`, `read_goals`.
The machine log was recounted by script, with dates; `scripts/check_agent_tools.py` was run
(read-only, no tokens). No transcript was opened.*

**Verdict in one paragraph.** The table is mostly accurate at the line level: 21 of 25 rows
confirm against file and code. The sweep is weaker in three places. (1) Two of its moves would
cause harm as written: wiring quick mode switches off the medication check on most Physical
Health calls, and the goals fix as worded can delete parked and declined goals from the file.
(2) Its best-evidenced finding (#1) removes about a tenth of the noise it claims, because the
bulk is the event type it chooses to keep, and it duplicates an open Now item. (3) It missed a
class: rules that sit in an agent that cannot carry them out, and writes that replace a whole
record. 19 misses are listed below.

---

## STRUCTURAL

**S1. Wiring quick mode (#9, D6) switches off the medication check on most Physical Health
calls.** `physical_health.md:14` says quick mode skips the proactive scan. The medication check
is step 2 of that scan ([physical_health.md:47](../../config/agents/physical_health.md#L47)).
Today the section never triggers, so the check always runs. The sweep's trade-off carves out
Logistics' horizon filing and notes that Mental Wellbeing keeps its clinical rules; it does not
mention Physical Health. Quick is the normal case, not the exception:
`tests/run_a4_safety.py:44-48` records Mental Wellbeing at 43 quick against 5 deep and Physical
Health at 58 against 6. So D6(a) as written is a skip that `MEDICATION_MISSED_CRITICAL` must veto
and does not. **Correction:** #9 cannot land before #8 (the medication miss computed in code) and
#14; it needs a Physical Health carve-out; and it goes through the A4 path. That moves it out of
C2 or reorders C3 ahead of C2.

**S2. Finding #1 keeps the event type that makes up most of the noise, and repeats an open Now
item.** Recount of the machine log (549 dated entries; 544 correction/miss events, matching the
sweep): scheduled-turn events are about 56 `USER_CORRECTION` and about 155 `ROUTING_MISS`. The
move refuses the first and keeps the second, so it removes roughly 10% of volume, not "~⅓".
The subject is already filed as *the routing-miss log is mostly the Coordinator flagging its own
scheduled prompts* `[DB-0902-01]` (`DEV_BACKLOG.md:170`), which holds the open question the sweep
skips (mishandled or misfiled?), names the guard (`write_quality_event` can read `is_proactive`
off the trace) and was owed a re-count on 11-05. That re-count, done here by keyword over dated
entries: since 10-29, about 42 of 68 `ROUTING_MISS` and about 20 of 56 `USER_CORRECTION` events
concern a scheduled turn. The noise survived the 10-29 check-in change. **Correction:** fold #1
into `[DB-0902-01]`; once #2 makes the brief's routing code, the only real scheduled misses are
gone, so refuse all three types on a turn with no user speech, or tag them and keep them out of
the ×3 count.

**S3. The medication move (#8) raises a false critical flag on the turn the user reports taking
the dose.** The shape computes "required minus taken today" at dispatch and says the model may
never clear a computed flag. A message saying "took my meds" is not in the log until Physical
Health writes it, so code flags a miss that nobody may clear. **Correction:** compute after the
specialist returns, the way `_file_horizon_items` runs after dispatch: re-read the log, add the
flag only if the dose is still absent and the output lacks it. Add-only is preserved. Two more
gaps in the same row: the trigger "every Physical Health dispatch" leaves the case where
Physical Health is not called at all, and medication is also a task-ledger habit (Coordinator
`:239`, `day_planner.md:35` "a medicine twice a day"), so "taken today" has two stores. Which one
is authoritative is undecided (see missing decision D11). The same before-the-write timing
applies to every computed threshold in #14, `SLEEP_ACUTE` above all.

**S4. C3 requires a test path Mike has suspended.** A4 safety testing is suspended until
capstone close (`ROADMAP.md:42`; `SESSION.md` § Do not re-open). C3 says both hard-fail moves
"must go through `tests/run_a4_safety.py`" plus a live gate run, and D8 adds a scenario to the
same runner. The sweep never puts the conflict to Mike. Either the suspension is lifted for
these fixtures or C3 waits. This is a missing decision (D10), and it also decides whether S1's
re-ordering is possible.

**S5. The goals fix (#5) as worded can delete goals.** "Make `read_goals` return `prompt_view`
for every caller except `goals_interviewer`" reads as a change to the function.
`tools/goals.py:63`, `:162` and `:312` call `read_goals()` inside `write_goals` and
`update_goal`, which read the file, change it and write it back. A filtered read there drops
every parked and declined goal on the next write, against archive-on-merge. **Correction:** the
exact form of bin B is to remove the `read_goals` grant from Work & Vocation and Finance (both
routing files) and the two instruction lines. The goals are already in their prompt
(`_run_single_agent` loads `load_goals` for every specialist). No code change, and still
`/fix`-sized, but it is two Red routing edits.

**S6. Forcing Mental Wellbeing and Physical Health onto the two scheduled sessions (#2) makes
them write to the log with no user words.** Both files say "write structured fields to today's
log" on every call. A scheduled brief has no user speech. Code already drops Mental Wellbeing's
clinical items on such a turn (`_drop_unprompted_clinical_flags`) because on 10-29 it re-raised
a concern from log entries it had written itself. #2 restores that precondition twice a day, and
#14 then counts those fields as evidence ("low mood on 9 of the last 14 days"). **Correction:**
#2 needs the specialists' log and journal writes refused on a turn with no user speech, as the
Diarist's dispatch already is. Two smaller points: `session_kind()` is None for a user who types
"Good morning", so deleting `coordinator.md:174` loses that half of the rule; and the code-added
dispatch must state its mode, because a quick one runs on Flash-Lite and, after #9, skips the
scan the rule exists for.

**S7. Three A findings are approximations and should be split.**
1. **#4 cap at 5.** Code can count; it cannot choose. The instruction is "keep only the most
   actionable". A truncation silently drops a held item, and `held_items` is the only record of
   something deliberately not said. Make the cap oldest-first on `open_threads` only (they carry
   an `added` date), never on `held_items` or `clinical_threads`, or hand the count back to the
   Synthesizer instead of cutting.
2. **#14 `PRACTICE_LAPSE` and `HOBBY_LAPSE`.** Neither has a threshold in the file
   ([mental_wellbeing.md:153](../../config/agents/mental_wellbeing.md#L153): "gone quiet; specify
   what and how long"). Code can hand over "last logged N days ago"; the flag stays the model's.
   The gap flags are also only as true as the dispatch history: a recreation field is written
   only when Recreation was called.
3. **#3 Diarist on every user turn.** The trigger is exact but the directive is not equivalent.
   The Coordinator's directive carries the corrected names (`coordinator.md:42`: a mis-heard name
   passed on "gets saved as a new contact or event"). A code-added "The user said: …" carries the
   raw words. Pass `RESOLVED_INTENT` and any `MISHEARD` pair with it.

**S8. #3 overlaps capture fidelity, which is mid-measurement.** `tools/capture.py` already
compares what the user said with what the turn kept, and is in shadow on ordinary turns inside a
14-day window with a holdout. The sweep lists `capture_extractor` as "nothing to move" and never
relates it to #3. Landing #3 in C1 changes what that window measures, and leaves two mechanisms
answering "nothing said is lost". Order it after the window, or decide which one owns the job.

**S9. A missed class: the rule sits where it cannot be carried out.** The sweep sorted by "could
code decide this". It did not ask whether the agent holding the rule is able to act on it. Four
instances are in MISSES (M1, M4, M5, M8): a read-back rule in an agent that never speaks, an
"escalate after several sessions" rule with no date to count from, and two whole-record
replacing writes. These are silent by construction.

**S10. #16 is in the wrong place and cluster.** By the time `send_email` is called the draft
exists, and the Synthesizer is told not to call the tool again. Hits attached to the approval
card reach only the user. The lookup belongs at Relationships dispatch, with #12's name
resolution, so the drafter has it. Move #16 from C4 to C2.

---

## LOCAL

1. **#1, "Removes ~⅓ of machine-log volume".** Wrong for the stated move (see S2); about 10%.
   The quoted "×10" example is a `USER_CORRECTION`; most of the rest is not.
2. **#7 and D5, "checked for a week through the `[HORIZON] … new/known` trace line".** That line
   is `_trace()`, which prints only when `AI_TRACE` is set (`core/orchestrator.py:50`), and a
   comment near `:2755` says the service never sets it. The check as described has nothing to
   read. Use the horizon record itself.
3. **#7 and D5, the trade-off omits the tool's stated reason.** `tools/horizon.py:754`: one call
   per item "rather than a list: a model that has to assemble a JSON array is back to emitting a
   structure it can get wrong". A malformed block is logged and dropped
   (`_file_horizon_items`), which is a silent loss.
4. **#15 tier "Red file only".** Learning & Growth holds no `open_task`, `update_task` or
   `list_tasks` in either routing file. Either two Red routing grants are added, or the habit
   rows stay with Logistics (where `coordinator.md:239` already sends "language practice,
   instrument") and Learning & Growth is handed them as evidence.
5. **#22 cost, "+1–3k uncached input per call ≈ $0.0006".** That is one turn on Flash-Lite. The
   block rides the user message, which is re-sent every turn (2.9–4.2 turns), and Mental
   Wellbeing and Physical Health run on 3.8 Flash at $0.75/M, doubling in January: about $0.002
   per call on Flash-Lite and about $0.005 on 3.8 Flash. Still pennies. "Flash-Lite turn ≈
   $0.002" does not apply to those two.
6. **#25 move shape.** Omitting results with `open_at_time: false` hides the fact the model
   needs for a named place ([logistics.md:302](../../config/agents/logistics.md#L302): search its
   name with `at`). An empty result reads as "not found", not "closed then". Keep the result and
   mark or sort it; omit only on open discovery.
7. **#24 is narrower than the defect.** Research never receives the complexity word at all.
   `run_subagent` uses it only to pick a model (`tools/subagent.py:122`), so all of
   `research_agent.md:70-78` is the same dead text as #9, not only `intensive`.
8. **#6 has an eighth site.** [synthesizer.md:312](../../config/agents/synthesizer.md#L312)
   scans "Pattern Miner signals"; the report goes only into the Coordinator's input.
9. **Lead point 5, "bears directly on the minute-long replies".** Specialists run in parallel,
   so the gain is one or two turns of the slowest, 2–4 s against a 54 s median; that item's own
   analysis puts the weight on Synthesizer thinking. True, but about 5%.
10. **Line deletions save no tokens in the small cached files.** All eight personal specialists
    are on the cached path (`_CACHED_SPECIALISTS`, `core/orchestrator.py:5631`).
    `physical_health.md` is 16 KB, under the 4,096-token floor on its own, so padding re-inflates
    whatever is cut. Not a hazard, since the pad is applied to every cached call. `CLAUDE.md`
    trap 6 ("the only two agents on the cached path") has been stale since 08-28.
11. **#4 evidence is one day.** The three dropped-block events are all 2026-10-09. Confirmed,
    but thin for a rank of 4.
12. **#2, "`scheduler.yaml` evening_close comment"** was not checked: persona files were out of
    scope.

**Spot-check tally.** CONFIRMED: #2, #3, #4, #6, #7 (the "will not reach anyone" line is false),
#8, #9, #10, #11, #12, #13, #14, #16, #17, #18, #19, #20, #21, #22, #23, #24, and all six § 2b
items. WRONG in a figure or shape: #1, #5, #15, #25. STALE: none, though #1's count is cumulative
since August. Routing parity (24 and 24, identical grants) holds. The cluster budgets add up, and
the prices match `spend_guard.yaml`.

---

## MISSES

Each: where · bin · silent or loud · move shape.

1. **A new phone number or address is saved wrong and nobody is asked.**
   [relationships.md:313](../../config/agents/relationships.md#L313) tells Relationships to read
   back every new name, email, address and number. Relationships never speaks to the user. · A ·
   silent; observed as corrections after the fact (16 misheard or spelling events). · Code builds
   a "newly captured: confirm in one clause" line from `write_contact`'s actual arguments and
   hands it to the Synthesizer.
2. **A draft goes out in the wrong voice.**
   [relationships.md:163](../../config/agents/relationships.md#L163), `:323`: "before drafting to
   a saved contact, call `get_tone_shape`". · A ("always X before Y") · half loud (the user sees
   the draft). · Hand the tone shape over with #12's resolved recipient.
3. **A birthday or follow-up window passes unmentioned.**
   [relationships.md:59](../../config/agents/relationships.md#L59), `:75`. · A (dates) · silent. ·
   Code lists contacts with an `important_dates` entry in the next N days and hands it over with
   the overdue list.
4. **Something deliberately held back is never raised and never dropped.**
   [synthesizer.md:265](../../config/agents/synthesizer.md#L265): escalate an item "held across
   multiple sessions". `held_items` carries no date and is replaced on every write
   (`tools/context_tracker.py`, `"held_items": held_items or []`). · A · silent. · Stamp each
   held item with its first-held date, as `open_threads` already is, and show "held N days".
5. **Adding one preference can delete the others.**
   [synthesizer.md:407](../../config/agents/synthesizer.md#L407): "include all existing
   preferences… the write replaces the whole section". · A · silent. · An append mode in
   `write_persona`. The file gives the reason itself for CRM proposals: never re-type stored
   wording.
6. **The weekly Pattern Miner run can wipe the Synthesizer's follow-ups and held items.**
   [pattern_miner.md:109](../../config/agents/pattern_miner.md#L109) calls
   `write_context_tracker`, which replaces `patterns`, `follow_ups` and `held_items` wholesale. ·
   A · silent; mechanism verified, incident unevidenced. · Code merges the findings into
   `patterns` only. #20 touches this call without seeing it.
7. **A turn the Coordinator marked ambiguous is recorded anyway.**
   [coordinator.md:42](../../config/agents/coordinator.md#L42), `:52`, `:143`:
   `CLARIFICATION_NEEDED`, for when "the turn would record or send something". No code reads it,
   and every listed specialist still runs and writes. · C · silent. · When the line is present
   and not null-ish, hold the writing specialists and go to the Synthesizer. Mental Wellbeing and
   Physical Health are never held.
8. **A clinical flag arrives without its required companions.**
   [mental_wellbeing.md:14](../../config/agents/mental_wellbeing.md#L14) (flag, `MUST_SURFACE`
   and `write_journal` together), [physical_health.md:109](../../config/agents/physical_health.md#L109). ·
   A, add-only · silent. · If the flag is present and `MUST_SURFACE` is absent, code adds it; if
   no journal write is in the trace, code writes the dated record. Hard-fail domain.
9. **A suicide disclosure is answered without the crisis line.**
   [synthesizer.md:32](../../config/agents/synthesizer.md#L32),
   [mental_wellbeing.md:174](../../config/agents/mental_wellbeing.md#L174). No code checks the
   reply. · A, add-only (is the configured number in the reply?) · silent and highest stakes;
   unevidenced. · Only on a turn where the flag fired on the user's own words. Hard-fail domain.
10. **The Coordinator re-types the user's whole message every turn.**
    [coordinator.md:113](../../config/agents/coordinator.md#L113). Code already gives the
    Synthesizer the user's own text (`core/orchestrator.py:7862`). · B · loud (output tokens on
    the first hop of every reply), with a silent side: a truncated copy was observed 11-20, the
    cardiac entry. · Drop the field; point `synthesizer.md:272-274` at the user-message label.
11. **Reporting a routing miss costs the Synthesizer a tool round.**
    [synthesizer.md:36](../../config/agents/synthesizer.md#L36), `:273`, `:381`, `:409`. Change
    requests already ride the `[CONTEXT]` block to avoid exactly this (`_persist_dev_request`). ·
    C · loud (latency on the head model). · Add a `routing_miss` key to the block and parse it.
12. **Pending confirmations live in three places.** [logistics.md:73](../../config/agents/logistics.md#L73),
    `:176`, `:222`, `:248`: agent config, the daily log, and ledger `waiting` rows.
    "Unaddressed across multiple sessions" is a count no model holds. · A + One Home · silent. ·
    The ledger row is the home; drop the other two.
13. **Logistics spends a turn writing down what its own tool calls did.**
    [logistics.md:240](../../config/agents/logistics.md#L240)–252. Code already generates the
    actions line from what ran. · A · loud (one turn per call). · Code writes the log entry from
    the executed actions.
14. **A calendar event marked `[VERIFY]` stays unverified.**
    [logistics.md:286](../../config/agents/logistics.md#L286). · A · silent. · Code re-runs the
    failed conflict check on the next calendar read.
15. **The Synthesizer holds a read of the wishes store its own file says no agent may have.**
    [synthesizer.md:408](../../config/agents/synthesizer.md#L408) against the `read_wishes` and
    `generate_emergency_card` grants in both routing files. · B · silent. · Drop the grants or
    document them (Red).
16. **The Pattern Miner picks its statistical baseline by hand while holding tools that do it.**
    [pattern_miner.md:54](../../config/agents/pattern_miner.md#L54)–61 against seven granted,
    unnamed tools (`get_baseline_context`, `shuffled_null_score`, …). · A · silent. · Belongs in
    #20.
17. **Cessation streaks are counted by a model.**
    [physical_health.md:114](../../config/agents/physical_health.md#L114). · A · silent. · Add to
    #14 and #15.
18. **Flight and line status report "all fine" lines the agent is told to ignore.**
    [logistics.md:303](../../config/agents/logistics.md#L303), `:304`. · B, plus a code throttle
    for the one-request-a-second rule · loud, small.
19. **"Enjoy the museum" still gets said.** [synthesizer.md:101](../../config/agents/synthesizer.md#L101).
    · A for detection only (the listed phrases) · loud; observed ×2. · A quality event on a
    match, never a rewrite.

**The "nothing to move" files.** `task_judge`, `accountability_judge`, `day_planner`,
`project_planner`, `crm_sweep`, `data_object_matcher` and `data_object_tagger` were read in full
and hold nothing to move. `tone_profiler` holds only #21. `capture_extractor` was not opened.
**Considered and left as judgement:** the Coordinator's deferral word lists (`:238-241`) — a
word match is the fuzzy replacement the method warns against.

---

## DECISIONS

**D1 — close `[DB-0810-11]` into the document: agree, with one change.** `temperature` should
not ride into C3 as a side item. It touches all four provider paths, and for the two clinical
agents a path change is a gated change (`core/orchestrator.py:5624`). Give it its own line.

**D2 — retire the notebook: agree.** Its retirement condition cannot fire; one closing round
pointing here.

**D3 — amend the founding principle: agree, and before C1.** It also appears in
`.claude/rules/orchestrator.md` and `SESSION.md` § What this is; amend all three or the stale
copies keep arguing. Suggested test: config decides what to value and say; code decides what can
be counted, looked up or checked.

**D4 — enforce the whole-person rule: agree, conditionally.** Only with S6's write guard, an
explicit mode on the added dispatch, and the user-typed greeting left with the Coordinator. The
framing is slightly one-sided: option (b) is weaker than stated, since the misses are recent
(×7 on 11-16), but the cost side omits the log pollution, which is the real price.

**D5 — one horizon channel: disagree with the recommendation as written.** Keep the block as the
only channel only after a malformed block stops being a silent drop (a retry or a quality
event), and verify from the horizon record, not the trace line. Until then (c), both, is the
safe state; it costs a Flash-Lite turn per finding.

**D6 — quick mode: disagree.** Recommend (b), delete the eight sections now, and reconsider
wiring only after #8 and #14 are in code. "One line of code" is true and is the problem: it
changes about nine in ten clinical-specialist calls at once, on the bulk-tier model, with A4
suspended. The data the sweep says to wait for already exists (S1).

**D7 — collect the flags into one block: agree.** At most one `PROFILE_GAP` is an exact rule.
`CLARIFICATION_NEEDED` (M7) belongs in the same decision and is not in it.

**D8 — the interview safety test: agree with (a), and bring it forward.** It should run before
the second user's first interview, which is the next thing on the primer. Option (c) is framed
unfairly as "the kind the method warns against": the method warns against a fuzzy match
*replacing* a judgement, and this one only adds. I would still not build (c) before the test
shows a gap. Blocked by D10.

**D9 — order: disagree in part.** Recommend: the goals fix in S5's form now → C1 without #3,
folded into `[DB-0902-01]` → C3 (if D10 lifts the suspension) → C2 with #9 last or dropped →
C4. C3 before C2 is the sweep's own alternative; S1 makes it the required order if quick mode is
wired at all.

**Missing decisions.**

- **D10 — C3 against the A4 suspension.** Options: (a) lift it for the new fixtures only (about
  $3–4 a gate run); (b) build C3's code now and hold it undeployed; (c) defer C3 to capstone
  close. Recommend (a): a code-computed clinical flag never exercised by a test is the lesson
  `ROADMAP.md` already records.
- **D11 — where "medication taken today" lives.** The Physical Health log, or the task ledger's
  habit rows. Recommend the ledger: code already tracks completion per occurrence and the day
  plan already places the doses. The profile supplies criticality.
- **D12 — task lengths: ask, or estimate for approval.** § 2b.2 records Mike saying "estimate,
  don't ask" three times on 10-28 while two agent texts still say ask once, and files it as a
  tidy-up. It is a behaviour choice. Recommend estimate-and-record, ask only when the plan names
  a task it cannot estimate.
- **D13 — who owns "nothing said is lost"**: the forced Diarist (#3) or capture fidelity (S8).
  Recommend capture fidelity owns detection and #3 waits for its window to close.
