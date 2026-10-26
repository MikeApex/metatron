### 2026-10-26, fifth (a routine the user asks to drop now stays dropped — the Franklin virtues paused until 2027-01-26) — `tools/routines.py` (new), `core/{orchestrator,scheduler,actions}.py`, both `config/modules/routing*.yaml`, `config/agents/synthesizer.md`, `config/modules/synthesizer_scheduled_sessions.md`, `tests/test_routine_pause.py` (new), `archive/plans/routine_pause_plan_2026-10-26.md` (new) — `4e16f3c` — **committed, deployed by Mike in-session, live-verified**

**Outgoing handoff carried:** day-planner watch day 2 then Stage B; the ritual-pause handoff
(`archive/handoffs/2026-10-25-ritual-pause-and-ledger-followups-prompt.md`) — this session ran its
item 1, extended. Items 2–4 (10-24 follow-ups) untouched.

**The report (Mike):** the evening close keeps carrying the Franklin virtues though he has asked
several times to drop them; remove them for now with a prompt to revisit in three months, and
fix why a normal request could not turn them off — any user should be able to toggle a routine.

**Why it could not be turned off — confirmed, unchanged from 10-24.** An ability gap, not
adherence: `evening_ritual.md` is injected by `_owned_rituals()` into every evening close and no
tool could change that, so each "skip it" lived one reply. **Wider than the 10-24 diagnosis:**
the user's own `scheduler.yaml` check-ins had the same gap — `delete_schedule` reaches only
agent-written jobs. Mike's ritual file is only the virtue review + its morning catch-up, so a
pause removes exactly that; the evening close still runs.

**Built.** `pause_routine` / `resume_routine` / `list_routines`, Synthesizer only. **Scope (Mike's
ruling this session): rituals + check-ins that talk to the user** — enabled `agent:` jobs that
push. Not pausable: function jobs (clinical review, travel), terminal-only analyses, every
`_DEFAULT_JOBS` key. Pause/resume only, nothing edited; refused on a turn with no user speech;
the user's real words stored as `user_said`. Optional revisit date: asked once, on the morning
brief or evening close, and spent only when the reply reached the user. Every scheduled run is
told what is paused. Paused check-ins are held at `_gates_block` (Red).

**Rejected:** every scheduler.yaml job pausable (lets a user switch off safety machinery,
against Mike's 10-24 "limited scope" instruction); rituals only (left the general gap half open).

**Believed true, wrong — found by Fable's plan review, before code:** that the morning catch-up
lived only in the ritual file. `synthesizer_scheduled_sessions.md` told every morning brief to
offer it when yesterday's log lacked the entry, so a file-only pause would have brought the
review back at breakfast. Also: the close-gate turn fields exist on the streaming twin only, so
the gate keys on `user_turn`. **Diff review found two more:** the check-back was stamped before
`filter_output()`, so a suppressed reply would have spent it unseen; and pausing both fixed
points would have meant it was never asked. All nine findings fixed; 37 checks, five fail on the
previous HEAD.

**Process correction (Mike):** I proceeded from the plan review into code without reporting its
findings first, and the review was not visibly labelled as Fable. Reviews are now named at
launch and reported before acting.

**Live:** Mike sent "Pause the Franklin virtue review for three months." → trace shows
`pause_routine("evening_ritual", revisit="2027-01-26")`; VM store correct. **Owed:** the 10-27
morning brief offers no catch-up and the 10-27 evening close carries no virtue list.

