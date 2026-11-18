### 2026-11-18, third (one network for every goal, obligation and task — planned, Fable-reviewed, reconciled; Mark 2 ended; stage 1 live-checked; mike's goals updated on the VM) — `cb890a9`, `74ba183` + this close-out — **nothing built, nothing deployed; mike's `goals.yaml` edited on the VM at Mike's instruction**

**Incoming handoff:** stage 2 (the planner schedules the Red Book prep), spec first, after its
10-30 draft failed Fable review (`archive/handoffs/2026-10-30-prep-tasks-stage-2-spec-prompt.md`).

**What changed in the need.** Mike widened stage 2 into *"a single pipeline for all tasks a user
must complete, as a network map with dependencies"*: every desire, goal or obligation is vetted
for feasibility, priority and seriousness, then broken into one-off steps the user is fed one at
a time. Built on existing parts, reusing orphans first. Plan:
`archive/plans/goal_task_network_plan_2026-11-18.md`. Rulings G1–G8 are in its § 2: one generic
project planner plus method-only playbooks (confirmed as the bridge to researched tax/language
modules — knowledge, not new behaviour); vetting depth by size, re-vetted on non-compliance, over
time, and on anticipated-vs-experienced satisfaction; the Interviewer overhaul folds in; Build is
out of scope ("a time to revisit"). Three phases, each with a live check. Stage 2 is phase 1's
first case.

**Rejected:** the full chain build in one go. Mike asked for it to be stress-tested; the
counter-argument (design whole, build in order) held, because the requirements that matter —
durations, decomposition depth, planning-session conduct — are only learnable from use.
Specialised per-goal agents through Build are also out: Build is dev-time by ruling and cannot
land anything (review #9). Runtime-authored playbooks need a § 0 ruling first: with one real user,
every playbook would be distilled from that user's data.

**Mark 2 ended (Mike):** *"We continue with Mark 1 until further notice. The Mark 2 restrictions…
can be removed project wide."* Recorded in a banner on its plan, the SESSION table, the A7 line,
two backlog items (calendar guest management back to triage; the Darwin key now an `@session`),
and a notebook round. A7 checks 10/12 and A8 still need a Mark 1 home.

**Fable review: 4 structural, 6 local, all verified and reconciled (plan § 10).** What was wrong:
- "the server sweep" had no host, and the ledgers have in-process locks only — a latent race
  exists today
- horizon findings carry no calendar uid, so "prep follows the event" had no source
- vetting depth depended on a plan made after vetting
- unblocked steps would never be shown, because undated and future one-offs aren't placed
- "zero model cost" was false (each step meant a reshuffle plus a nudge and a check)
- declined goals would have reached every prompt, since raw `goals.yaml` is pasted in
- hidden steps leaked through the dedupe guards
- the reshuffle pattern was mis-transferred
- phase 1's dismissal rule called a phase 2 planner
- the #5 fix was undesigned

**Believed true and wasn't:** that the server could host a periodic sweep. Also that
`private_why` "never goes to a cloud model": `goals.py`'s docstring says so, but the Synthesizer
gets the whole file on Vertex. That matches the 08-26 ruling; the docstring is stale.

**Stage 1 live check (read on the VM, 11-12 → 11-18):** ordinary briefs pass; the prep line works
(Show and Tell toy). Three misses, traced in plan § 12. Mike's rulings:
- M1, the Monday week rundown (working as the 09-05 conduct says): **leave as is**.
- M2, uncapped new horizon findings: **wants to see it first** (example in § 12).
- M3: **a slipping task is raised every day, with recognition it was missed, until done or
  dismissed** (replacing my "ask once after three days").

**mike's goals (VM, two backups `goals.yaml.bak-2026-11-18`, `-18b`):**
- ids for four id-less goals (`d2`, `q3`, `w4`, `w5`)
- added `q4` Bulgarian (long-term; `d1` under it), `q5` UK taxes by Dec 31, `q6` Prudential
  review, each with what Synth must ask
- `q2` Mark 2 Transition → "Metatron work this quarter", whose four outcomes are a Claude Code
  draft flagged for Mike to confirm

**Outgoing:** phase 1 build — `archive/handoffs/2026-11-18-goal-network-phase-1-build-prompt.md`.

