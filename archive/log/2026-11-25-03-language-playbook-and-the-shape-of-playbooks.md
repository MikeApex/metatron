### 2026-11-25 (The language playbook, the shape of every playbook, and Build's return agenda)

**What changed (`29a61f0`, not deployed).** `config/playbooks/language_learning.md` landed on Mike's
yes — the last item of goal network phase 3 part A. It started as an A0→B1 draft; Mike sent it back:
"needs to go further than B1 … through fluency … specialized vocabulary or creative writing", for
learners not necessarily at the novice stage. The landed file runs pre-A1 (new script) → C2: seven
rungs as checkable outcomes, hours for four FSI distance rows, placement (incl. uneven skills and
heritage speakers), practice by rung with evidence-graded techniques, six tracks, graduation
options. `tools/goal_talk.py`: the talk reads a playbook whole (`_PLAYBOOK_MAX` 16k guard; ~$0.03 a
talk) — the 2,400 cap had no recorded reason and halved even the taxes file (Mike: "lift the cap
now"); the fallback lookup stays at 2,400 (outside content). Tests 42/42 + 31/31.

**Research.** Two rounds, each three decontextualised grounded Research Agent calls + Claude via
`ask_claude` as a second voice + one grounded fact-check (Mike approved the questions; he added
spaced repetition, Pimsleur, vocabulary targets, placement for prior exposure, subscription and
AI-made resources; protocols were asked for with "what the evidence does NOT support" to avoid
leading). 26 of 28 claims confirmed. **Wrong, caught:** Claude put FSI hours at ILR 2 (it is ILR
3); Claude's Cambridge B2–C2 hours ran ~20% high; "Suk 2017" is a single study, not the
meta-analysis (Jeon & Day 2016); "C1 fluency returns in 2–4 weeks" has no source (dropped). No
evidence exists on tutor cadence at A1–A2 — the file says so. `ask_claude` answers on Sonnet 4.6,
not Opus, and timed out once replaying history (reset fixed it). Total research ~$0.25–0.35.
`/build-inquiry` was run outside a Build job at Mike's request: 30 questions for a language
teacher, saved in `archive/plans/`; it split the capability into curriculum, material engine and
nudging, and named nudging's risk (a chosen pleasure turned obligation).

**Decided — the shape of every playbook (plan § 4.4, each argued for and against):** two
properties (`ends:`, `recurs:`) not two kinds; three required sections, the rest optional with
fixed names code can cut by; graduation as conversation-starter options, not a re-vet trigger
(Mike); one file per subject, a separate file only for a branch with more than one parent —
size is not a reason, since sections are addressable; the habit hand-off keyed to the habit row,
not to Learning & Growth (Mike: it may not survive the reshuffle); protocols one line, evidence
only; ceiling 12k (Mike, from 10k).

**Rejected:** splitting by level (titles never say a level); a `language_specialty.md` (creative
writing serves native writers too, and size alone no longer justifies a file); a separate
creative-writing file now (no general half yet — it moves out when one exists).

**Corrected in Mike's model of the system:** not every goal gets an interview (S/M/L); there is no
goal "document" — the talk writes seven fields onto `goals.yaml` and the plan lives in
`projects.json` + ledger rows; the Interviewer does not plan, the project planner does; no playbook
is built when none exists (one generic lookup instead); Synth is out of the loop during a talk;
`plan_project`'s planner is unrelated to Build's Planner; Build starts from a capability gap, not a
goal, and Inquiry never assists the Interviewer. **Recorded for Build's return** (agenda atop
`build_vertical_plan_2026-09-24.md`): playbooks written as a matter of course behind a
distinct-user threshold and a § 0 ruling; a goal-driven Build.

