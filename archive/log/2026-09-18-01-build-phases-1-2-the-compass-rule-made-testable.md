### 2026-09-18 (Build phases 1–2 — the compass rule made testable, and what the worked run found)

Built § 16 phases 1 and 2 of `archive/plans/build_vertical_plan_2026-09-18.md`: the three Build
artifacts and their validators, the job ledger, and the substrate Inquiry and the Librarian stand
on. **104 checks across five new suites, all passing; `qa_sweep.sh` 10/10.** Nothing is deployed
and nothing is user-visible — phases 1–6 reach the VM as one deploy, and the first thing Mike sees
is phase 7 run 1.

**New:** `core/build/{__init__,ids,jobs,schemas,manifest,probe,condense,settle,policy,index,cost}.py`,
`tests/test_build_{schemas,spine,jobs,manifest,probe}.py`,
`tests/fixtures/inquiry_rsvp_2026-09-17.md`. **Modified:** `core/trace.py` — one call site, a
no-op unless a Build job is bound on the thread.

**The compass rule now has evidence, and it discriminated on the first run with no tuning.** The
reference transcript the plan cites — `archive/plans/inquiry_reference_rsvp_2026-09-17.md` — **did
not exist**; the plan wrote the path as a forward reference and nobody created the file. Mike
supplied the transcript mid-session. Encoded as a machine-readable pass/fail pair, turn 2 fails
validation on three independent grounds (spine unordered by class index, no `intent` question, no
disposition) and turn 4 passes clean. **Neither half was written to satisfy a rule that did not
yet exist**, which is the whole evidentiary value and the reason the verbatim form was not
collapsed into the abstract.

One judgement call in the encoding, documented in the fixture rather than buried: turn 4's
numbered spine has no `surface` question, and the material was cut from its body instead
(*"every yes creates obligations that outlive it"*). A test asserts this addition is **not**
load-bearing — remove it and the pair still sorts the same way, with turn 4 failing on that one
ground. Considered and rejected: reconstructing the pair from the plan's description of it, which
would have validated the validator against my own reading of the plan. § 15's named weakness
(n=1) says the fixture set is *"never manufactured"*, and manufacturing the first one would have
made the whole test circular.

**The worked Inquiry run found something that changes phase 6's status, and it is the session's
most useful output.** Run by hand on run 1's own gap (the plant-watering check stuck on August 4,
filed twice by Mike on 09-08), validated clean against the live validator: 10 questions, class
sequence `1,2,2,3,3,4,5,6,7,8`, feasibility at position 7. Checked against the live manifest,
**every compass question in it is currently unanswerable** — both `intent` questions and the
unmetered-cost question need `search_conversations`, which is not built. The plan justifies the
§ 9 briefs on one research question; **this is stronger and is the same conclusion: run 1 executed
before phase 6 would produce a capability built on feasibility and surface alone — a filter,
arrived at through the substrate while following the spine correctly the whole way.** Phase 6 is
not a convenience ahead of run 1; it is what stops run 1 rebuilding turn 2. Written up at
`archive/plans/build_worked_inquiry_home_care_2026-09-18.md`.

Two smaller findings from the same run: a spine **class is a bucket, not a slot** — `cost` split
naturally into two questions with different shapes and two questions at one class index is legal,
worth knowing before the agent file is written in phase 5. And `read_journal_range`'s absence does
**not** show as a gap, because `read_journal` is registered and reads one date — a source whose
tool exists but cannot answer the shape of question asked is a fourth probe state that does not
exist yet and will currently read as `no_data`. Filed in the worked-run document for phase 6.

**The § 15 Librarian/Planner interview ran, and Mike overruled three of four recommendations.**
Full text and per-phase consequences: `archive/plans/build_librarian_planner_parameters_2026-09-18.md`.

1. **The Librarian is a LOCATOR and reads as much as it needs** — its aim is establishing which
   questions have answers and *where in user data those answers live*. This kills the proposed
   per-question reading budget. The plan supports Mike over the question: the Answer Ledger's
   fields are overwhelmingly about *whether* and *where*, not *what*. `condense.py`'s docstring
   said the point was keeping the judgment on a small input; corrected in place, because a stale
   design intent in a docstring is what a later session acts on. **Consequence stated rather than
   swallowed: the per-job budget tripwire is now the only cost control, and its $2.50 default is
   a placeholder I invented.** Recommendation carried into the record — meter the Librarian's
   reading per run from run 1 and set the figure from three runs of evidence.
2. **A broken lookup is triaged, not stopped** — the Librarian troubleshoots the error first; if
   the data is a poison pill for plan construction Mike is alerted; otherwise the plan carries a
   **placeholder that retrieves it later**. None of the three options offered. This adds a
   *deferred data binding* to the BuildPlan, which the plan document does not describe — phase 3
   owns it, and it needs a resolver, a retry owner and a meantime behaviour stated when built.
   The three-state probe built this session is exactly what makes the triage possible.
3. **The Planner sees questions AND answers, and is forced to cite both.** This answers the
   traceability objection rather than accepting it — the proposal protected traceability by
   *withholding* input; Mike keeps the richer input and makes citation checkable by code. Strictly
   better, and recorded as such.
4. **The Planner plans; it does not create.** Same conclusion as recommended, better reason:
   argued from role boundaries (Inquiry creates questions, the Librarian creates options, the
   Planner arranges) rather than from traceability, so a later session can re-derive it.

**Design decisions worth keeping.** The job ledger has no status file — state is replayed, copying
`tools/crm_sweep.py:276-297` and its reasoning. `blocked` is a flag on the row, not a state,
following `DEV_BACKLOG.md`'s `@waiting:` convention. The restart test is a **real `kill -9`
against a real child process**, not a simulation: the property under test is that a process dying
between a node's write and its ledger row resumes correctly, and only an actual SIGKILL produces
that state. Rung 1's coercion table deliberately has **no entry for `class`** — there is no safe
spine class, so an unclassed question is quarantined to `declined_to_ask[]` rather than guessed,
because guessing its class would guess its *position*, which is the compass rule itself.

**The manifest privacy proof was made structural rather than a grep.** The plan's test is "grep
the manifest for every string value in `profile.yaml`" — but no persona tree exists on the Mac
(they live on the VM), so that grep would pass vacuously. Added a stronger form: **every string in
the manifest must be traceable to a literal in `manifest.py`, a `config/agents/*.md` filename, or
a policy's declared fields.** That holds for data which does not exist on this machine and for
data nobody has written yet — it proves there is nowhere for a corpus value to come from. A
companion check asserts the grep detector actually fires, so an empty profile cannot look like a
pass.

**Pre-existing and not caused here:** `tests/test_action_provenance.py` is 9/10 —
`record_wisdom_response` and `send_calendar_invite` are registered but classified in neither
`ACTION_TOOLS` nor `READ_TOOLS` in `core/actions.py`. Confirmed identical at `7bca654` with this
session's work stashed. Not filed; Mike's call.

**Not run, and named so they do not read as skipped:** § 12's Budget row needs `runner.py`
(phase 4) and its Trace-contract row needs a job that actually runs. Both belong to later phases.

**Outgoing handoff carried forward:** two commits still owe one deploy — `0e154b9` (09-09
invitation wording) and the 09-10 `tools/` change; the VM is at `b2b1dc7`. Build phases 1–2 add
nothing to that debt, since phases 1–6 deploy together.

**Deployed: NO.** Commit: this close-out.
