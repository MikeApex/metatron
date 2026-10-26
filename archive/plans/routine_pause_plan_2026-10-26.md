# Routine pause — plan, 2026-10-26

Model: Opus 5.5 builds; Fable 5.1 reviews this plan before code, and the diff before commit.

## The need

Mike has asked several times for the Franklin virtue review to be dropped from the evening close
"for the time being". Each time Metatron agreed and the review came back the next evening.
**Mike's instruction today:** remove it for now, with a prompt to revisit in three months
(**2027-01-26**), and fix the general gap — *users should be able to toggle routines they set up.*

## Why it could not be turned off

An ability gap, not adherence (diagnosed 2026-10-24, `archive/log/2026-10-24-04-…`, re-verified
today). `config/personas/mike/evening_ritual.md` (VM-owned) is injected by
`core/orchestrator.py` `_owned_rituals()` into every `evening_close` session; no tool can change
that, so a model's "I'll skip it" lived for one reply. The same gap covers the user's own
scheduled check-ins in `config/personas/{p}/scheduler.yaml` — no tool can pause them
(`tools/schedule.py` `delete_schedule` reaches only agent-written jobs in
`data/personas/{p}/schedules.yaml`).

Mike's evening ritual file is **only** the virtue review plus its morning catch-up clause, so
pausing it removes exactly what he asked and nothing else; the evening close still runs.

## Scope (Mike's ruling today: rituals + check-ins that talk to the user)

Binding constraint from 10-24: *"ensure users have limited scope to change things that they
otherwise didn't initiate and that Metatron did."*

Pausable:
1. **Rituals** — every `config/personas/{p}/*_ritual.md`. Id = file stem (`evening_ritual`,
   `manny_school_ritual`); `evening` resolves to `evening_ritual` as a fallback. Stem, not owner,
   because `manny_school` is both a ritual owner and a schedule key.
2. **User-facing check-ins** — keys in the persona's `scheduler.yaml` `schedules:` that are
   enabled, run an `agent:` (not `function:`), notify the user (`notification: push|both`), and
   are **not** `_DEFAULT_JOBS` keys. For Mike: morning_brief, companion_checkin, evening_close,
   location_anticipation, manny_school.

Not pausable (Metatron's machinery): function jobs (weekly_clinical_review, daily_travel_check),
terminal-only analyses (weekly_pattern_miner, weekly_physical_review), every `_DEFAULT_JOBS`
maintenance job. Agent-written jobs already have `delete_schedule`.

## Mechanism

**`tools/routines.py`** (renames the untracked 10-24 draft `tools/rituals.py`; never deployed).
Store `data/personas/{p}/routine_pauses.yaml`, 0600, atomic replace, RLock:
`{paused: {<id>: {kind: ritual|checkin, at, evidence, user_said, revisit, revisit_raised}}}`.

Tools — `pause_routine(routine, evidence, revisit="")`, `resume_routine(routine, evidence)`,
`list_routines()`:
- **Pause/resume only.** Nothing edits, rewrites or deletes a ritual file or `scheduler.yaml`; a
  pause is a separate record, so resume restores the routine exactly.
- **Only the user's words.** Reuses the task ledger close gate's turn fields
  (`tools/turn_context.current()` → `close_gate`, `user_turn`, `user_text`): a pipeline turn with
  no user speech (scheduled) is refused; no bound turn (direct/CLI call) is allowed. `evidence`
  required; the turn's real `user_text` (first 300 chars) is stored beside it as `user_said`, so
  provenance is what the user said, not the model's paraphrase.
- **Only routines that exist and are pausable**; anything else refused with the real list.
- `revisit` optional ISO date, must be after today. Re-pausing a paused routine moves its revisit
  date and clears `revisit_raised` (this is how "keep it off for now" is answered).
- `list_routines` shows each id, kind, a one-line description (ritual: first line of its file;
  check-in: when it runs + start of its prompt) and paused state, so "the virtue review" maps to
  `evening_ritual`.

Wiring:
1. `core/orchestrator.py` `_owned_rituals(config_dir, kind, paused=frozenset())` skips paused
   stems; `load_config` passes `paused_routines(resolved)` (only when `kind` is set).
2. `core/orchestrator.py` `_scheduled_focus_block(kind)`: when `kind` is a pausable check-in and
   a pause's `revisit` date has arrived and `revisit_raised` is unset, add a block — *"on {at} the
   user paused {desc} ("{evidence}") and asked to revisit around {revisit}. Ask once, briefly,
   whether to bring it back (resume_routine) or keep it off (pause_routine with a new revisit
   date). If they don't answer, leave it paused."* — and stamp `revisit_raised`. Stamped here
   because the focus block is built once per pipeline (both twins); `load_config` runs per
   head-layer agent and would stamp before the Synthesizer saw it.
3. **Red** `core/scheduler.py` `_gates_block`: after `disabled`, `return "paused by the user"`
   when the job is a paused check-in. Read per fire, so a pause takes effect next tick, no reload.
4. `register_tools()`: three schemas + handlers. `core/actions.py`: pause/resume in
   `ACTION_TOOLS`, list in `READ_TOOLS` (`tests/test_action_provenance.py`).
5. **Red** both `config/modules/routing*.yaml`: grant all three to `synthesizer` only.
6. **Red** `config/agents/synthesizer.md` § Tools, one entry: when the user asks to drop, skip or
   stop part of a check-in or a check-in itself for a while, call `pause_routine` — never promise
   to skip it without calling it. Named period → revisit at its end; "for now / for a while" →
   revisit about three months out; "for good" → no revisit. Then `scripts/check_agent_tools.py`.

## Tests (synthetic persona, live meters stubbed)

Pause hides `evening_ritual` from an `evening_close` config and leaves `manny_school_ritual`;
resume restores the config byte-identical; ritual file and scheduler.yaml unmodified; a scheduled
turn's pause refused; unknown and non-pausable ids (weekly_clinical_review) refused; paused
check-in blocked by `_gates_block`, unpaused not; revisit block appears once on/after the date,
never before, never twice; re-pause clears the stamp. Existing: `test_evening_ritual_gate`,
`test_ritual_focus_gate`, `test_synth_module_injection`, `test_action_provenance`.

## Live close (after Mike deploys)

Mike says in the app "drop the virtue review for three months" → trace shows
`pause_routine("evening_ritual", …, revisit="2027-01-26")`; that evening's close has no virtue
list; next morning no catch-up. Fallback if he would rather not: one VM command calling
`pause_routine` directly (no bound turn = allowed) with today's request as evidence.

## Budget

Build ~1.5–2.5M Opus tokens (subscription, mostly cache) + two Fable passes (~0.4M each).
Run: no model calls; one small YAML read per session and per scheduler fire. Ancillary: ~400
tokens of schemas in every Synthesizer prompt on the cached path (~$0.005/day). Unseen: one
persistent file per persona; deleted by resume; nothing billed by time.

## Overlap

Day-planner Stage B edits the same Red files (routing*.yaml, synthesizer.md) — whichever lands
second re-applies its lines. A8: `_owned_rituals` moves to `core/config.py`, the focus-block
addition stays in `core/orchestrator.py`.

## Fable 5.1 plan review, 2026-10-26 — four findings, all accepted

1. **The morning catch-up has a second home** (structural). `config/modules/synthesizer_scheduled_sessions.md:36`
   tells every morning brief to offer a catch-up when "the user has an evening ritual defined and
   yesterday's log is missing its entry"; the 5-day log window and the asked-questions tracker
   (`may_reask`) also carry the virtues forward. Pausing the file alone would leave the morning
   offer. **Resolution:** on every scheduled run, `_scheduled_focus_block` names each paused
   routine as *paused by the user — do not run, offer, catch up on, or mention it*; and the module
   line reads "an evening ritual **is in effect** (not paused)". Test: a morning_brief focus block
   carries the paused line.
2. **Revisit stamped before the run** could lose the one question on a failed or blank reply.
   **Resolution:** the focus block only *reads* due revisits; `_close_turn_bookkeeping` (already
   the end-of-turn hook on both twins) stamps them, and only when a non-empty, non-error reply
   was delivered. Raised only on morning_brief/evening_close where the persona has one enabled
   (any user-facing check-in otherwise), so the quiet check-in's "nothing new" directive cannot
   swallow it.
3. **Re-pause with no revisit** would leave a past date and re-ask every run. **Resolution:**
   re-pause always *replaces* the revisit — empty clears it (for good), a date sets it — and
   clears the stamp. Tested both ways.
4. **The non-streaming twin binds no `close_gate`/`user_text`.** **Resolution:** the routine
   gate keys on `user_turn`, which both twins bind: a bound turn with `user_turn` false is
   refused; no bound turn (direct/CLI) is allowed. `user_said` is stored when `user_text` exists.
   The ledger's close gate is not touched.
