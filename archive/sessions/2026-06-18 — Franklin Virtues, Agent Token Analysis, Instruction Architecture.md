# Session: Franklin Virtues, Agent Token Analysis, Instruction Architecture
*2026-06-18*

---

## What was built / changed

### 1. Franklin virtue review added to `config/agents/synthesizer.md`

New section: **"Scheduled session conduct"** inserted after "Onboarding and domain baseline interviews".

Covers both check-in types, in the same file, because the Synthesizer is the user-facing agent — the Coordinator routes and packages, the Synthesizer conducts the conversation.

**Morning check-in (morning_brief session):**
- 4 phases: Open → Establish context (mood, energy, focus, time, blockers, wins) → Direct the day (2–3 highest-leverage items, sequence, invite pushback) → Close
- If yesterday's `franklin_virtues` log is absent: offer quick catch-up before directing the day

**Evening close (evening_close session):**
- 3 phases: Day reflection → Franklin virtue review (all 13 in sequence, conversational) → Close
- After review: call `write_log` with `franklin_virtues: { temperance: "...", ... }`
- All 13 virtues from Franklin's *Autobiography* embedded verbatim

**Franklin's 13 virtues:**
Temperance, Silence, Order, Resolution, Frugality, Industry, Sincerity, Justice, Moderation, Cleanliness, Tranquility, Chastity, Humility.

Note: Franklin's method is 13 virtues, not 14 as sometimes cited.

---

### 2. Agent token budget added to roadmap Section 4

`archive/plans/phase5_to_future_roadmap_2026-06-10.md` — Section 4 now includes a full token count table for all 16 agent files with target ranges and review approach.

**Target ranges:** specialists 1,500–2,500 tokens; Synthesizer and Coordinator 3,500–5,000.

**Over target (flagged for D2 review):**
- `synthesizer.md` ~7,200
- `mental_wellbeing.md` ~6,100
- `relationships.md` ~5,730

---

### 3. Context-file architecture (Option 2) added to D2

`archive/plans/phase5_to_future_roadmap_2026-06-10.md` — D2 "Prompt structure optimization" block now includes a named deliverable for agent instruction file slimming via the context-file pattern:

- Over-budget agents audit their content into: (a) behavioral rules (stay in file), (b) domain data (move to `config/modules/{agent}_*.yaml`, loaded on demand via `read_agent_config`)
- No code changes required — `read_agent_config` is already registered
- Regression gate: A4 clinical-flag hard-fail scenarios must pass before and after each agent slim

---

## Decisions made

**Where check-in conduct lives:** Synthesizer, not Coordinator. Coordinator routes and packages; Synthesizer conducts. Both morning and evening in the same file.

**Templates folder:** Not wired into the runtime at all. `config/templates/daily_checkin.md` is a reference document only — never loaded by the orchestrator. No new template files needed.

**Instruction granularity architecture:** Option 2 (on-demand context files via `read_agent_config`) preferred over third-level sub-agents. Deferred — test agents as-is first, then slim at D2.

**Where to revisit:** D2 (Encryption + model validation + cost analysis) — already contains prompt structure optimization and output compression work; agent slimming is a natural fit there.

---

## Deferred

- Agent token review and slimming: deferred to D2
- Paring down from all-13 evening virtue review: after testing with current setup
