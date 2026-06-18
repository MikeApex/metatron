# Phase 1 Testing Plan — Goals Interview + Personas + Time Director

*Intent-driven. Tests whether the phase achieved its purpose, not just whether the code runs.*

---

## Phase Intent

Capture the user's terminal values and current life mission through a structured interview, populate the four-tier goal hierarchy, and verify that the Time Director can produce a grounded daily direction based on real user context — not stubs. Personas are created for design validation throughout all subsequent phases.

---

## Prerequisites Check

| Prerequisite | Check |
|---|---|
| Orchestrator working (Phase 0) | `python core/orchestrator.py --input "hello"` returns a response |
| `config/prime_directive.md` is a blank stub (not pre-filled) | File exists, contains no substantive content |
| `config/mission.md` is a blank stub | File exists, contains no substantive content |
| Goals interview agent exists | `config/agents/goals_interviewer.md` exists and is non-empty |
| Goals tools registered | `read_goals` and `write_goals` callable from orchestrator |
| 2+ development personas exist | `config/personas/` contains at least pepys.md and one other |

---

## Intent Checks

### 1. Goals interview produces real output
- Run the Goals Interviewer against the user
- **Pass:** `config/prime_directive.md`, `config/mission.md`, and `config/goals.yaml` are all populated with substantive, non-placeholder content after the interview
- **Fail:** Any file remains blank, or contains generic/speculative content not sourced from the interview

### 2. Time Director uses the captured context
- Run a Time Director session after the interview
- **Pass:** The Time Director's response references specific goals or values from the populated config — it is grounded, not generic
- **Fail:** Response is generic life-management advice with no connection to the user's actual prime directive or mission

### 3. Personas are distinct and testable
- Run the orchestrator with `--persona pepys` and `--persona nin`
- **Pass:** Each persona produces meaningfully different responses to the same prompt; logs write to `data/personas/{name}/logs/`
- **Fail:** Personas produce indistinguishable outputs, or log to the wrong location

### 4. Goals data is sensitivity-enforced
- Confirm `config/goals.yaml` contains `private_why` fields
- **Pass:** Goals data is stored locally only; no tool sends goal content to a cloud API without stripping PII
- **Fail:** `private_why` fields appear in cloud API request payloads

---

## Known Gaps (from Phase audit)

- **Goals interview was never run against the real user.** `prime_directive.md` and `mission.md` remain blank stubs as of Phase 4 completion. This is the single most load-bearing gap — every agent loads these files as core context. Phase 1 is not complete by its own intent criteria.
- **Verification criterion was unachievable.** "Diarist initiates at least one unprompted follow-up" requires the scheduler daemon (Phase 4). This criterion should be moved to Phase 4's testing plan.
- **Calendar sandbox.** Listed as a Phase 1 prerequisite but CalDAV integration was never built in any phase.

---

## Sign-off

Phase 1 is complete when: goals interview has been run, all three config files are populated, Time Director produces grounded output, and personas are verified. The goals interview must happen before Phase 5 begins.
