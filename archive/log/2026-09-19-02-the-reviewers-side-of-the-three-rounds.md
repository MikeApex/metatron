### 2026-09-19 (the reviewer's side of the three rounds — how twelve findings were reached, and two probe mistakes)

The § 14 second-model review of Build phase 3 ran in this session (Fable 5.1), three rounds.
The findings, their probe outputs and their closure are in
`archive/plans/build_phase3_writer_review_2026-09-19_fable-5.md` (Parts 1–3); the build side's
account and the fix decisions are the `2026-09-19-01` fragment. This entry records only what the
review file does not: how the findings were reached, and where the reviewer was wrong.

**Method, so it can be repeated.** Nothing was confirmed by reading. Each claim ran as code
against `tests/test_build_writer.py`'s real-git fixture — imported as a module, which builds
the fixture and leaves it in place, so a probe script reuses `reset()`, `edits_for()` and the
three ceilings without a second fixture that could drift. Round 1's probes then re-ran
**unchanged** after each fix (14/14, then 13/13 for round 2's), which is what "a fix did not
reopen something that held" actually means. The probe scripts lived in the session scratchpad
and were deliberately not added to the repo: each defect got a shipped `REVIEW` test in the fix
session, and a second copy of the same assertion outside `tests/` would be one more thing to
drift. The review file describes each probe's construction beside its result instead.

**Where the reviewer was wrong, both times by the same mechanism — the fixture is not the tree.**
- Round 1 reported the `find_places` condition as *holding* on first probe. It was refused for
  a different reason: the fixture's agent text names `get_log_window` and `get_weather`, so a
  grant of `find_places` alone failed the grant gate, not the condition. Re-run with text naming
  only `find_places`, it landed with no `risks[]` — the real defect. A refusal proves nothing
  until the refusal *reason* is read.
- Round 3's seam probe reported `Mental & Wellbeing` surfaced by seam 3. It was not: the seam
  reads tracked names from `writer._ROOT`, which the fixture points at a tree with no
  `mental_wellbeing.md`. Re-run with `_ROOT` on the real tree, only the double-space form
  surfaced — the one finding of that round. Filed as one, not two.

**Believed true earlier and wrong:** the first-pass report ranked defect 4 (prompt-bound record
fields) as closed after the fix session on the strength of `routing.yaml` and a model id being
refused. Tool names were not — the gate read the static confidential list, 37 of 78 registered
names — and that became round 2's N3. A gate is confirmed on the inputs it was probed with and
no others.

**Not filed to the backlog:** nothing. Every finding was fixed in the session that received it,
and `backlog_close_scan.py`'s twenty candidates against `origin/main..HEAD` are all the phase-3
build's own additions, none closed by a review document.

Commits: findings landed inside `12d7dd2` (Mike's, the whole phase) and `48de0cc` (the build
side's close-out); this fragment in this session's close-out. **Deployed: NO** — phases 1–6
deploy together.

