# Fable 5.2 adversarial review — stage3 hard fail plan (2026-11-23)

*Verbatim reviewer output; the driver's dispositions are in `instructions_to_code_plan_review_stop_2026-11-23.md`.*

## STRUCTURAL

1. [§ 1.1 Trigger / Consult path, § 3 X1–X4, X6–X7, Decision B] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/subagent.py:143 `run_subagent` → `run_session`; /Users/md-homefolder/Desktop/multi-model-mcp/config/templates/scheduler.yaml:97-102 `weekly_physical_review` (agent: physical_health, "medication adherence"); /Users/md-homefolder/Desktop/multi-model-mcp/core/orchestrator.py:8575 `run_session` → `_run_single_agent` (working tree; HEAD is 15 lines earlier throughout this region); /Users/md-homefolder/Desktop/multi-model-mcp/config/agents/synthesizer.md:143, :393]
Wrong: The closing round deletes Physical Health's own medication check ("Do not work out a miss yourself") and points Finance at "FINANCE FIGURES in your directive", but the code that replaces them runs only inside the two pipeline twins.
Fails: A Physical Health or Finance call made by the Synthesizer through `run_subagent`, and the weekly single-agent Physical Health review, go through `run_session` → `_run_single_agent` with no `_after_specialists` and no dispatch block, so after X1–X4 neither model nor code computes a miss there; Decision B describes the residual gap as "unlinked on an ordinary turn" and does not count these paths, which carry the check today.
Costs: A missed required dose is silently unflagged on every non-pipeline Physical Health run once the Red deletions land, which is the exact gap the driver's closing-round rule exists to prevent. high

2. [§ 1.1 Decision A option (a), Decision B option (a), § 1.6 `clock: "21:00"`] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/obligations.py:4957-4973 `_unlinked_row` (working tree; HEAD :4900); /Users/md-homefolder/Desktop/multi-model-mcp/config/templates/scheduler.yaml:31, :67 (brief 07:30, close 20:00); /Users/md-homefolder/Desktop/multi-model-mcp/tests/run_a4_safety.py:145-158 PH-MED-UNLINKED]
Wrong: Challenging the acceptance of A(a): the 18:00 cut-off is written into the view itself, so `missed` reads False (not unknown) for an unlinked required medicine until evening, which removes a `MEDICATION_MISSED_CRITICAL` that fires today at any hour.
Fails: Every reader of the view, the model included, loses the flag before 18:00, and with B(a) the only guaranteed code check after the cut-off is the 20:00 close on a scheduled turn; the plan has to pin PH-MED-UNLINKED to 21:00 to keep an existing A4 pass passing, and the view reads today only, so a skipped close means the miss is never raised.
Costs: A required morning medicine with abrupt-stop risk (the A4 fixture case) goes from flagged at the morning brief to flagged twelve hours later or not at all, against the standing rule that code adds flags and never clears one. high

3. [§ 1.2 Decision E option (a) `_merge_transactions`, `finance_figures_note` tail "these are right"] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/logger.py:187-197 `_deep_merge`, :523-524 `write_log`; /Users/md-homefolder/Desktop/multi-model-mcp/config/agents/finance.md:165-178 (transaction schema: no id, no time), :87 ("exact or approximate"), :218]
Wrong: The multiset merge identifies a transaction by exact `(description, amount, category, type)`, and transactions carry no id, so any restated entry that differs in one character or one field is kept beside the original.
Fails: Finance reads the day's log and rewrites it; a reworded description, a corrected amount or a recategorisation (`dining_out` → `dining`) now adds a second entry instead of replacing the first, and list-replace, the only way a wrong transaction could be corrected or removed, is gone.
Costs: Period totals inflate permanently in the stored logs and are then handed to the Synthesizer labelled exact and authoritative over Finance's own figures, producing a false "overspent" in the Finance hard-fail domain. medium

4. [§ 6 live table L2–L4 "After the closing round", § 2 O1, § 3 last paragraph] [/Users/md-homefolder/Desktop/multi-model-mcp/archive/handoffs/2026-11-23-instructions-to-code-build-driver-prompt.md:37-43 (closing round after every stage; skipped if the run stops early), :58-59 (commit and push per stage), :71-74, :165-167 (#9 only once #8 passes)]
Wrong: Every live clinical, finance and pipeline gate for Stage 3 is placed after the closing round, which the driver runs once after Stage 5, so Stage 3's hard-fail code is committed, pushed and built upon with only offline tests and L1.
Fails: Stage 4 wires quick mode on the condition that "#8 passes" with no live evidence it does, the opening-round clinical edit O1 waits for the same end-of-run gate, and if the run stops early the closing round and therefore L2–L4 never run at all.
Costs: A regression in flag handling introduced by the wrapper, the appended blocks or the runner changes is discovered after two further stages sit on it, or is pushed ungated. medium

## LOCAL

5. [§ 1.5 Trigger: "The flag fired on the user's own words this turn; the 10-29 rule already removes it on any other turn"; § 1.4 step 2] [/Users/md-homefolder/Desktop/multi-model-mcp/core/orchestrator.py:6833-6837 `_drop_unprompted_clinical_flags` (working tree; HEAD :6818); /Users/md-homefolder/Desktop/multi-model-mcp/tools/context_tracker.py:37; /Users/md-homefolder/Desktop/multi-model-mcp/config/agents/synthesizer.md:38]
Wrong: The 10-29 rule drops Mental Wellbeing's flags only on turns with no user words; on a real user turn it returns the output untouched, so "the flag is present on a user turn" is not "the user disclosed this turn".
Fails: When Mental Wellbeing re-raises `SUICIDAL_IDEATION` from its own earlier log entries or an open thread while the user asks about something else, code appends the crisis line (and M8 writes a journal entry quoting the unrelated message) on every such reply, overriding the Synthesizer rule that an earlier flag is not evidence about this message.
Costs: The repeated crisis-block recital that the 10-29 and 08-08 fixes removed returns on user turns, now enforced by code. medium

6. [§ 6 L4 and "L4 is the only check that the appended crisis line reaches the user's screen"; § 1.6] [/Users/md-homefolder/Desktop/multi-model-mcp/tests/run_a4_safety.py:216-219 `surface_expect_any`, :588 `run_pipeline_session`; /Users/md-homefolder/Desktop/multi-model-mcp/core/server.py:988, :1498 `run_pipeline_session_stream`]
Wrong: L4 cannot observe M9: MW-3-PIPE passes on "crisis", "professional" or "reach out" with no line present, the plan does not change that check, and the suite drives the non-streaming twin while the app is served by the streaming one.
Fails: A reply with no crisis number, and a broken append or `[RETRACT_WITH]` delivery in the streaming twin, both pass L4.
Costs: The one live check budgeted to prove the crisis line reaches the user proves nothing about it, and the non-streaming wiring is covered offline only by a source-text assertion. high

7. [§ 1.1 Trigger "every turn where `physical_health` is a key of `outputs`", Wiring] [/Users/md-homefolder/Desktop/multi-model-mcp/core/orchestrator.py:7028, :7077-7080 (`is_ff` → `outputs[agent] = "… dispatched (async)"`), :7890-7894 and :8187-8191 (`spec_text` excludes any output containing "dispatched (async)")]
Wrong: When the Coordinator marks Physical Health fire-and-forget, its `outputs` value is the async placeholder, and the code block is appended to a string that the bundle then filters out.
Fails: The check runs, finds the miss, and the flag reaches neither `_signoff_skip` nor the Synthesizer in either twin; the specialist also has not run yet, so no dose was recorded before the read.
Costs: A code-computed `MEDICATION_MISSED_CRITICAL` is silently discarded on that turn. medium

8. [§ 0 point 1 "never raises a false alarm", § 1.1 "An unlinked dose is Physical Health's own `write_log` … already on disk", Decision C2, § 1.6 PH-MED-TAKEN (`med_state: linked` only)] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/obligations.py:4921-4966 `_logged_entries`/`_unlinked_row`, :5096-5135 `_TAKEN_LINE_RE`/`record_reported_doses`; /Users/md-homefolder/Desktop/multi-model-mcp/core/orchestrator.py:6645-6649]
Wrong: The same-turn guarantee rests on the model: a linked dose counts only if Physical Health emits `MEDICATION_TAKEN:` with the exact profile name, and an unlinked dose only if it also calls `write_log` with a matching `medications_logged` entry in that turn.
Fails: If either is omitted, code reads the row as missed and adds `MUST_SURFACE` on the turn the user said they took it, the carve-out that used to cover this is dropped by C2, and no offline or live test covers the unlinked case or the omitted-line case.
Costs: A false critical medication alarm in reply to "I took it", untested for unlinked medicines. medium

9. [§ 1.1 Decision C1 "critical = `criticality not in ("as_needed", "optional")`", emission table row 1] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/obligations.py:4963-4973 (unlinked: empty criticality → `missed = not took`), :5036-5043 (linked, `entry is None` → criticality None, `link_broken`); /Users/md-homefolder/Desktop/multi-model-mcp/config/agents/physical_health.md:48, :52, :119]
Wrong: C1 widens the critical flag from `required` rows to every row whose criticality is absent, which includes a habit linked to a medicine the profile no longer holds and any profile entry written without the field.
Fails: A discontinued medicine whose habit was left open, or a criticality-less supplement, emits `MEDICATION_MISSED_CRITICAL` plus `MUST_SURFACE` on every Physical Health dispatch, where today's instruction gives those rows `MEDICATION_LINK_BROKEN` or nothing.
Costs: A daily must-surface false alarm that leads replies and vetoes the sign-off skip. medium

10. [§ 1.5 Decision G option (a2), § 3 X5] [/Users/md-homefolder/Desktop/multi-model-mcp/core/interview.py:296-327 `coverage_block`, :410-412 `run_turn`; /Users/md-homefolder/Desktop/multi-model-mcp/core/server.py:937 (`/session` runs any named agent through `run_session`); /Users/md-homefolder/Desktop/multi-model-mcp/core/orchestrator.py:926-936 `_AGENT_NAME_MAP` ("goals" → `goals_interviewer`); /Users/md-homefolder/Desktop/multi-model-mcp/config/agents/goals_interviewer.md:25]
Wrong: X5 removes the support numbers from the interviewer's instruction and replaces them with "the support lines in your context", which only `run_turn`'s coverage block supplies.
Fails: The interviewer reached through `run_session` or a Coordinator dispatch gets no SUPPORT LINES block, so on a disclosure it has no numbers to give, and GI-SAFETY exercises only the `run_turn` path.
Costs: A suicide disclosure answered with no, or invented, support lines on the non-interview entry paths. speculative
