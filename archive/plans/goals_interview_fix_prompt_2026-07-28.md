# Goals Interview Fix — Session Prompt

*Paste this into a new chat to run the fix session. Written 2026-07-28.*

---

Metatron's Goals Interview is supposed to be the onboarding conversation that fills in a user's real goals, values, and mission — the data everything else in the tool (Coordinator routing, Synthesizer responses, Pattern Miner baselines) is supposed to be grounded in. For Mike's real account, it doesn't work yet: an interview was run and marked complete, but `config/goals.yaml`, `config/mission.md`, and `config/prime_directive.md` are all still empty.

## What's actually broken

The interview agent is `config/agents/goals_interviewer.md`. It walks through several stages of conversation — baseline reality check, goal collection, a domain sweep, timeline/mood questions, surfacing contradictions, a values/mission thread — and only at the very end does it save anything to disk, via `write_goals`, `write_config`, and `write_baseline_period`.

Two concrete problems:

1. **Nothing is saved until the very end, and only after a confirmation step.** If the conversation runs long, gets interrupted, ends early, or the confirmation gets missed, none of it is written — not even the parts that were fully covered. This is almost certainly what happened to Mike's real interview: the values/mission stage was never reached, and it looks like even the goals collected earlier never made it to `goals.yaml` either.
2. **The interview always starts cold.** It doesn't load anything the system might already know about the user (existing baseline data, prior partial interviews, persona notes) before asking its questions — so re-interviews and any future second user both start from zero, producing generic questions instead of sharper, more personal ones.

A smaller, related bug: `data/baselines/aspirational_baseline.json` has real content (from a separate, earlier tool call, `write_aspirational_baseline`) but its `persona` field is blank — it's not actually tagged to Mike.

## What "fixed" looks like

- The interview saves progress as it goes — each completed section gets written to disk when it's confirmed, not just once at the very end. A conversation that gets cut short should still leave behind whatever was genuinely covered.
- The interview reliably reaches and saves the values/mission questions, not just the goals list.
- The interview ends with an explicit, plain-language summary of exactly what got saved — so it's obvious if something was skipped, instead of silently marking itself "complete."
- Re-running the interview (or running it for a brand-new second user) loads whatever already exists first, instead of starting cold every time.
- None of this is specific to Mike — the fix has to work the same way for any future persona or user.
- `data/baselines/aspirational_baseline.json`'s blank persona tag gets fixed as part of the same pass.

## Where to look

- `config/agents/goals_interviewer.md` — the interview agent itself (this file is under the specialist-agent freeze; propose edits in a document rather than editing it directly, unless the freeze is explicitly lifted for this work)
- `config/agents/goals_interview_reference.md` — the full domain list and output schema it references
- `tools/baselines.py` — `write_aspirational_baseline`, `write_baseline_period`, and related functions
- `core/orchestrator.py` — how `write_goals`/`write_config` get dispatched and confirmed
- Current (empty) state: `config/goals.yaml`, `config/mission.md`, `config/prime_directive.md`
- Current (populated but untagged) state: `data/baselines/aspirational_baseline.json`

## What to produce

A document proposing specific edits to `config/agents/goals_interviewer.md`'s save/write-back behavior and its interview-start behavior, plus a decision on when to actually re-run the real interview against Mike's account once the fix is agreed. Read `SESSION.md` and the active roadmap first, per the project's standing pre-edit rule — this touches a frozen agent file and real user data.
