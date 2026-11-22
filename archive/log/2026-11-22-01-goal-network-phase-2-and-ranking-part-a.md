### 2026-11-22 (goal–task network phase 2 built and live-checked; ranking Part A — every task weighed, plan steps never missable, deadlines that climb) — `9ad7a6c`, `d772968`, `0c9aa46`, `3b7c32a`, `c1e097a`, `fda9d80`, `e6a661c`, `9cf1215`, `deed121` — **deployed by Mike through `fda9d80` (VM at the data-objects chat's `9542e34`); `e6a661c`, `deed121` undeployed**

**Incoming handoff:** log § 11-21 third — phase 1 live; the redo question asked but not recorded
(`note_said` signal words too narrow), handed here with the phase 2 build prompt (Opus, high).

**Phase 2 (`d772968`, plan § 15).** A goal stated in chat is recorded `proposed`, Synth sizes it
S/M/L and checks an M in one question, `plan_project` queues it, the project_planner agent plans it
off the tick (single flight, 6/day ≈ $0.12/day), code validates and writes it in one locked
`open_plan`. Skip judgement gate built light (Mike: a later step done counts its required earlier
steps done; "on purpose?" asked once). The redo-question defect went in its own commit (`9ad7a6c`).
First playbook, UK Self Assessment: researched by Metatron's own grounded Research Agent, then
fact-checked — GPT 5.4 mini and Gemini Flash-Lite both admitted answering from training data, so a
second grounded call was the real check: 15/17 confirmed, the UTR lead time corrected (15 days, 21
abroad), Flash-Lite's "29 December" rejected. Fable diff review: 10 findings, all fixed.

**Phase 2 live check (11-21/22) found five things the tests could not:** (1) Synth asked two
interview questions before the check question — an older NEW_GOAL paragraph contradicted the new
one-question rule (`0c9aa46`); (2) it said "vetted" and "planned out of sight" — words it copied
from tool results (`3b7c32a`); (3) two specialists opened twin tax tasks on one "yes" — the planner
adopted two, one duplicate was dismissed on the VM at Mike's request (backup beside it); (4) **the
planner's first step never reached the day**; (5) "I checked my HMRC sign-in" closed nothing.

**(4) and (5) were the ranking, which Mike then redesigned (rulings 1–8, plan § 16).** Nine stale
chores with no stakes scored 55 each because F10 read unknown stakes as vital; the plan's early
steps were `missable` (R5) at 20; nothing climbed before the last two days; the 6-line cap hid the
step from Synth. **Believed true and wrong:** that R5's two-day margin was a safe economy — it made
every early required step lapse silently, stalling the chain behind it.

**Part A (`fda9d80`).** Unjudged = back burner; the judging rule (costs of missing it; obligations
vital whatever the mission) lives once, in open_task's schema; `task_judge` weighs what the opener
missed (≤ ~$0.06/day); required steps inherit their end's weight; a linear climb (`ramp_days` 14);
vet priority high/normal/low. **Fable diff review, 16 findings, all fixed** — the serious one: a
failing judge would have hidden an overdue bill all day, so anything unjudged past 60 minutes now
reads vital again (a broken judge degrades to F10, never to a hidden bill). Built in a tree shared
with the data-objects chat: six files held both chats' lines, so the commit staged HEAD-plus-mine
blobs, proven standalone in a worktree first.

**Live checks 1–4 (11-22): pass**, after two more fixes — the close gate tied the sign-in step with
a step still waiting on it (`e6a661c`), and a goal link kept the judge's priority (`deed121`).
"Let's go through my tasks" gave the afternoon plan, not a review: no back-burner review exists.

**Decided / rejected:** runtime-authored playbooks stay out (one user's details would reach every
user); the Drop button stays as is (Mike); "Done, but…" became **Update…**, sent to Synth as a chat
message rather than a new router (`c1e097a`, phone on the next APK). Values-weighted ranking was
NOT guessed: Part B interviews Mike first (prompt `archive/handoffs/2026-11-22-ranking-part-b-interview-prompt.md`).

