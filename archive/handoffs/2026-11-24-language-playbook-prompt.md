Model: Opus 5.5 — a short, Mike-led session: one research call, a draft, his review; no code unless the review asks for it.

# The language-learning playbook — researched, drafted with Mike, landed on his yes

**Mike asked to be involved (2026-11-24).** This is the last item of goal network phase 3 part A
(`archive/plans/goal_task_network_plan_2026-11-18.md` § 17, commit `12c8463`). Everything else in
part A is built; this file is the method the project planner reads when it plans a language goal.

## Read first

1. `SESSION.md`, then `ROADMAP.md` (the pre-edit context check).
2. Plan § 4.4 (playbooks: method only, researched by the Research Agent, Mike reviews before it
   lands) and § 17 (the `applies_when` matcher).
3. `config/playbooks/taxes_uk_self_assessment.md` — the shape to copy: an HTML comment saying
   method only and how it was researched; `applies_to:` / `applies_when:`; stages with own-effort
   and elapsed time; planning notes in the planner's terms (`eligible_from` gaps, steps of at most
   90 minutes); common failure points.
4. `config/agents/project_planner.md` § A large goal — what the planner does with a playbook for an
   L goal: milestones as outcomes, steps only for the next one, recurring practice is NOT a step.
5. How the taxes playbook was researched and fact-checked: `archive/log/2026-11-22-01-goal-network-phase-2-and-ranking-part-a.md`
   (the Research Agent's own grounded call, then a second grounded call as the real check — two
   models answering from training data was not one).

## Steps — Mike live

1. **Put the research question to Mike for approval before running it.** Decontextualised: no
   language named, nothing about him. Draft: *"Best practice for an adult learning a new language
   from beginner to everyday conversational level, studying alone with an occasional tutor: the
   stages (with typical hours of study for each, and how they differ for a language close to or
   distant from English), what a good weekly routine looks like, which milestones are observable
   outcomes, and the common reasons adults stall or quit."* Ask him what he would add — he knows
   what he wants from Bulgarian, but the question must stay generic.
2. **Run it through the Research Agent** (cloud, decontextualised — ROADMAP § Section 0 item 5),
   then one grounded fact-check call. ~$0.02–0.05 in all, not metered by the spend guard; name the
   figure. No Artifact, WebFetch or WebSearch from this session.
3. **Draft `config/playbooks/language_learning.md`** from the answer, in the taxes shape:
   - `applies_when: speak, speaking, learn, learning, fluent, fluency, conversational, practise,
     practice, improve | <language names, one word each; phrases with a space are matched as
     written, e.g. sign language>` — so "Become better at speaking Bulgarian" matches with no
     Bulgarian file, and "public speaking" or "Bulgarian taxes" do not. Check the list with Mike.
   - Stages as **outcomes** the planner can turn into milestones (introduce yourself and order;
     a ten-minute conversation about your day; …), each with typical study hours and how distance
     from English changes them.
   - Planning notes: recurring practice is the user's weekly time, never a step; steps are the
     things that move them to the next outcome (book a tutor, finish a unit, a first real
     conversation); a milestone's `minutes` is its whole estimate at their weekly time.
   - Common failure points (stalling at intermediate, no speaking practice, too much at once…).
   - **Method only — no user content, ever** (the file is shared by every persona).
4. **Put the draft to Mike.** It lands only on his yes. Then check it attaches:
   `.venv/bin/python -c "import tools.project_plan as P; print(bool(P._playbook('Become better at speaking Bulgarian')), P._playbook('Practise public speaking'))"`
   → `True None`. Add a check to `tests/test_goal_network_phase3.py` that the real file attaches to
   a language goal and not to "public speaking"; keep the suite green (41/41 before this).
5. **Commit** (message leads with what a user would notice — a language goal is planned from a
   researched method); **no deploy**. Update plan § 17's playbook line. `/archive`.

## Rules

- Nothing about Mike or his goals enters the research question or the file.
- `config/personas/**` is VM-owned; deploying is Mike's.
- Don't file backlog items Mike didn't ask for. Number every list; never a bare backlog id.
- **Budget:** ~$5–15 for the session; the research ~$0.02–0.05. **Run cost:** none — a playbook is
  config, read by the planner on calls it already makes (it adds a few hundred input tokens to a
  language goal's planning call, ~$0.0005).
