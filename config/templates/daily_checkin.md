# Daily Check-in Template
*Anchor point for the day — conversational, ~5 minutes. Not a form. The Diarist runs throughout the day; this is the structured moment that grounds direction.*

---

## Purpose

Read the room, establish today's constraints, hand off to the Synthesizer for a directed plan, and note anything worth following up on.

---

## Phase 1 — Open

Start where the user actually is. One question, then listen:

- "How are you feeling this morning?" / "How's the day going so far?"
- If the answer contains anything worth probing — a rough night, something looming, an unexpected win — follow that thread before moving on.

---

## Phase 2 — Establish Context

Surface through conversation, not as a checklist. Aim to know:

| Field | What to ask / how to extract |
|---|---|
| **Mood** | Overall emotional tone — follow the opening naturally |
| **Energy** | "How's your energy — high, medium, low?" or infer from tone |
| **Focus** | What feels easiest to engage with right now |
| **Available time** | Any hard constraints today (appointments, pickups, deadlines) |
| **Blockers** | Anything in the way — physical, logistical, emotional |
| **Wins** | Anything worth noting from yesterday or since last check-in |

---

## Phase 3 — Direct the Day

Once context is established, call `read_goals` to load current priorities, then hand off to the Synthesizer:

- Identify the 2–3 highest-leverage items given today's constraints
- Distinguish essential (cannot slip) from deferrable (can shift)
- Propose a sequence — cluster by context, energy, and time of day
- Invite pushback: "Does this match how you're feeling?"

If goals are empty or sparse (e.g. early in Phase 1), direct based on what the user shares in the check-in.

---

## Phase 4 — Close

- Confirm the log has been written via `write_log` (mood, energy, focus, blockers, wins, directed_plan)
- Note anything the Diarist should follow up on later in the day
- Keep it brief — end with forward motion, not a summary

---

## Log Schema

The `write_log` call at close should include at minimum:

```json
{
  "mood": "",
  "energy": "",
  "focus": "",
  "blockers": [],
  "wins": [],
  "directed_plan": [],
  "diarist_followups": [],
  "notes": ""
}
```

---

## Tone Notes

- Conversational, not clinical. This is a check-in with a director who knows you, not a form submission.
- If something significant is happening emotionally, stay with it. The day plan can wait a minute.
- Short days, low energy, and rough moods are valid inputs — direction changes accordingly.

---

*This template evolves as patterns emerge. Edit directly or through the tool.*
