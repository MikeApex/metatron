# Phase 4 Testing Plan — Pattern Miner + Proactive Initiation

*Intent-driven. Tests whether the phase achieved its purpose, not just whether the code runs.*

---

## Phase Intent

The tool stops waiting to be asked. The scheduler initiates sessions on its own rhythm. The Pattern Miner extracts genuine signal from accumulated data. By the end of this phase, the tool is proactive — it finds things the user didn't know to ask about and surfaces them without prompting.

---

## Prerequisites Check

| Prerequisite | Check |
|---|---|
| FAISS memory working (Phase 3) | Multi-session recall passes Phase 3 Check 1 |
| At least 14 days of log data | `data/logs/` or persona logs contain 14+ entries |
| Scheduler config exists | `config/modules/scheduler.yaml` present and non-empty |
| Push infrastructure working | `core/push.py` exists; VAPID keys generated |
| Pattern Miner agent exists | `config/agents/pattern_miner.md` non-empty |
| Routing layer built | `core/router.py` exists; `config/modules/routing.yaml` has agent entries |

---

## Intent Checks

### 1. Scheduler fires on schedule
- Start `core/scheduler.py`; wait for a scheduled trigger
- **Pass:** Session fires at the configured time; log entry or push notification is produced without user initiation
- **Fail:** Scheduler does not fire, fires at wrong time, or fires but produces no output

### 2. Pattern Miner surfaces genuine evidence-backed findings
- Run Pattern Miner at 7-day and 30-day scales against real or synthetic data
- **Pass:** Every finding includes a direct quote or data reference from the logs; no unsupported assertions; confidence annotations match data volume
- **Fail:** Findings are generic, unsupported, or repeat the input without synthesis

### 3. Push notification reaches the phone
- Trigger a push notification manually or via scheduler
- **Pass:** Notification appears on the phone without the PWA being open
- **Fail:** Notification only appears in-app, or not at all

### 4. Sensitive routing is logged
- Run a Diarist and Pattern Miner session with `local_enabled: false`
- **Pass:** Both sessions appear in `data/logs/routing_fallbacks.json` with correct agent name and fallback reason
- **Fail:** Fallbacks are silent; no log entry produced

### 5. Scheduler sessions don't require user initiation
- Reboot the machine; confirm scheduler auto-starts or has a documented start procedure
- **Pass:** Scheduled sessions fire without manual intervention after setup
- **Fail:** Scheduler requires a manual `python core/scheduler.py` each session

### 6. Proactive Diarist functions (from Phase 3 carry-over)
- Confirm scheduler triggers an EOD Diarist session
- **Pass:** Diarist session fires at configured EOD time; produces a log entry without user input
- **Fail:** EOD Diarist never fires or fires but writes nothing

---

## Known Gaps (from Phase audit)

- **Pattern Miner routes to cloud (o3).** Designed for local LLM; currently using OpenAI o3 due to `local_enabled: false`. Pattern Miner sessions contain analytical inference over sensitive behavioral data — this is the most privacy-critical gap in the system.
- **Scheduler sessions are flat.** Each scheduled session runs one agent with no coordination. A Diarist session triggered by the scheduler cannot escalate to the Time Director or Pattern Miner without a separate scheduled trigger.
- **Goals interview still not run.** Pattern Miner and Time Director are operating without `prime_directive.md` or `mission.md` context. All insights are decontextualized from the user's values.

---

## Sign-off

Phase 4 is complete when: scheduler fires unprompted (Check 1), Pattern Miner produces evidence-backed findings (Check 2), push reaches phone (Check 3), and fallbacks are logged (Check 4). The local LLM routing gap must be resolved before any sensitive specialist module in Phase 5 goes into production use.
