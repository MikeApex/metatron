### 2026-09-18, second (four follow-ups — a fourth probe state, and two tools that could act unseen)

Four items Mike ruled on at the close of the phase 1–2 session, all four executed. **117 Build
checks (up from 104), `test_action_provenance` back to 10/10, `qa_sweep` 10/10.** Still not
deployed — phases 1–6 reach the VM as one deploy.

**1. The probe gained a fourth state, `unaskable`** (Mike: *"yes build it"*). *"The tool is
registered"* and *"the tool can answer this"* are different facts, and the gap between them was
invisible. `read_journal` is registered and takes ONE DATE, so the journal reported
`available: true` against the worked run's question *"how does he write about work stress"* across
61 files — a probe that returns one day or nothing, settling as `no_data`: **"there is nothing
recorded"**, when the truth is **"this tool cannot be asked that."** One means a FACT is missing,
the other means a TOOL is, and only the second earns a brief.

A source may now declare which shapes it serves (`answers` in `manifest.py`, opt-in so adding it
is a deliberate statement). Checked **before** the call, so the misleading row count is never
produced. `settle.py` derives the question's shape from its sources and passes it down.
`unaskable` folds into `needs_tool` for routing — both resolve as a Mac-side brief — but is
reported separately, because *"write this tool"* and *"widen this tool"* are different work. An
unregistered source is **not** reported as unaskable; different problem, different fix.

**The inference is imperfect and the error direction was chosen deliberately.** A single-date
question naming `journal` reads as behavioural and reports `unaskable`, costing one unnecessary
brief Mike can see and reject. The opposite error is silent and builds a capability on a false
premise. **A visible false positive beats a silent false negative** — the same trade the three
original states rest on. Re-running the worked Inquiry set now flags `journal` as unaskable on
both `intent` questions, which is the defect the run itself walked past hours earlier.

**2. The spend limit stays at $2.50 and now announces itself** (Mike: *"set to $2.50 now, with a
warning to show up BEFORE run 1 commences to announce this as a placeholder value"*).
`budget_notice()` returns the warning while the figure is unconfigured and **self-clears** the
moment `budget.per_job_usd` is set in `config/modules/build.yaml`, or a per-job limit is approved
— so it cannot decay into noise anyone learns to scroll past. It returns a string rather than
logging, deliberately: a log line is not a decision point, and the whole reason it exists is that
the number was chosen before anything had been measured. Three callers owe it, named in the
docstring: the phase-4 runner before a job's first node, `build_board.py`'s header, and the phase 7
walkthrough before run 1 starts. **Why it is a placeholder and not merely a default:** the
per-question reading ration was removed the same day under ruling 1 of the § 15 interview, so this
tripwire is now the only thing bounding a run's spend.

**3. Two tools could act without appearing on the ACTIONS line** (Mike: *"do it, test it, if it
fails revert"* — it did not fail). `send_calendar_invite` and `record_wisdom_response` were
registered and classified in neither `ACTION_TOOLS` nor `READ_TOOLS` in `core/actions.py`, so
`test_action_provenance.py` had been failing 9/10 since before this session — confirmed at
`7bca654` with the day's work stashed, so it was not introduced here. This is the `[DB-0810-13]`
class exactly, and the worse of the two is `send_calendar_invite`: it mails a real invitation to a
real attendee, cannot be recalled, and shipped unclassified on 2026-09-07. `record_wisdom_response`
persists the user's pushback verbatim and changes what the store says about them, so it is an
action on the same reading as `write_wisdom`. Both classified; 10/10. **Found by the test, not by
anyone reading the file** — which is the argument for the test.

**4. Four untracked plan documents committed** (Mike: *"commit it"*). `SESSION.md` links to
`build_vertical_plan_2026-09-18.md`, so leaving it untracked gave a fresh clone a dangling link.
Committed with its two adversarial reviews (Fable 5.1, Opus 5) and the 09-09 dependency flowchart.
Also committed: `CODEBASE_INDEX.md`'s 09-10 refresh and the Mark 2 plan's § 3a addition, both
dirty from earlier sessions and held back from the first commit under the rule that a session does
not stage lines it did not write. Mike released them explicitly.

**Deployed: NO.** Commits: `77566a4` (phases 1–2) and this close-out.
