# Phase 3 Testing Plan — Diarist + Life Wisdom + FAISS

*Intent-driven. Tests whether the phase achieved its purpose, not just whether the code runs.*

---

## Phase Intent

The tool becomes a continuous presence, not just a check-in endpoint. The Diarist captures the texture of daily life across sessions; FAISS gives the system long-term memory that survives context window limits; the Life Wisdom Depot accumulates durable personal patterns. By the end of this phase, the tool should know things about the user that persist across weeks.

---

## Prerequisites Check

| Prerequisite | Check |
|---|---|
| Voice pipeline working (Phase 2) | Full voice round-trip on phone passes |
| Diarist agent file exists | `config/agents/diarist.md` non-empty |
| FAISS memory module built | `core/memory.py` exists; `data/memory/` directory writable |
| Wisdom tools registered | `write_wisdom`, `read_wisdom` callable from orchestrator |
| At least 5 days of log data | `data/logs/` or `data/personas/{name}/logs/` contains 5+ entries |
| Embedding model downloaded | `all-MiniLM-L6-v2` (or equivalent) available locally |

---

## Intent Checks

### 1. Diarist persists across sessions
- Conduct two Diarist sessions on different days; mention something specific in session 1
- **Pass:** Session 2 references or acknowledges the detail from session 1 (via FAISS retrieval or context tracker)
- **Fail:** Session 2 has no knowledge of session 1's content

### 2. Life Wisdom Depot accumulates and surfaces
- After several sessions, check `data/wisdom/`
- **Pass:** Wisdom entries exist; at least one was written by the Diarist autonomously (not prompted); `read_wisdom` returns them correctly
- **Fail:** Wisdom directory is empty after multiple sessions, or entries were only written when explicitly instructed

### 3. FAISS retrieval is semantically meaningful
- Embed several log entries; query with a related but non-identical phrase
- **Pass:** Retrieved entries are topically relevant to the query; not just keyword matches
- **Fail:** Retrieval returns unrelated entries or fails silently

### 4. Sensitive data routing
- Check `data/logs/routing_fallbacks.json` after a Diarist session
- **Pass:** If `local_enabled: false`, fallbacks are logged but sensitive data is not silently routed to cloud without the developer knowing
- **Fail:** Sensitive sessions route to cloud with no logging or warning

### 5. Diarist is reachable conversationally
- From the Time Director, say "I'd like to make a diary entry"
- **Pass:** Diarist is invoked (via sub-agent dispatch or explicit agent switch); entry is persisted
- **Fail:** Time Director handles the request itself without invoking the Diarist, OR request falls through with no persistence

---

## Known Gaps (from Phase audit)

- **Sub-agent dispatch does not exist.** Intent Check 5 cannot pass until the MAIN coordinator is built (Phase 5 prerequisite). The Diarist is only reachable by directly specifying `agent=diarist` in the request.
- **Sensitive routing not enforced.** `local_enabled: false` means all Diarist sessions route to Anthropic cloud. The privacy architecture is designed but not live.
- **Phase 3 verification criteria required Phase 4 features.** "Diarist initiates meaningful unprompted conversations daily" requires the scheduler daemon (Phase 4). This criterion belongs in Phase 4's plan.
- **"Weekly check-in surfaces a data-backed observation"** requires the Pattern Miner (Phase 4). Also belongs in Phase 4.

---

## Sign-off

Phase 3 is complete when: multi-session memory works (Check 1), Wisdom Depot accumulates (Check 2), FAISS retrieval is semantically correct (Check 3). Checks 4 and 5 are Phase 4/5 dependencies and do not block Phase 3 sign-off — but must be tracked.
