# 2026-06-26 — Troubleshooting Prompts and Interchange ID Design

## What this session covered

Short meta/planning session following the pipeline debugging + latency work session. No code changes. Produced two reusable prompts and a design recommendation.

---

## Items

### 1. TTS phrase-by-phrase note — confirmed present

Verified the future TODO for phrase-by-phrase TTS (option 2: stream sentence-by-sentence with meaningful pauses) is recorded in three places:
- `static/index.html`: inline `// TODO future: phrase-by-phrase TTS with meaningful pauses between sentences.` comment inside `sendStreaming`
- Session archive: `2026-06-26 — Pipeline Debugging and First Response.md`
- `SESSION.md`: under the latency work entry

---

### 2. Troubleshooting prompt — latency / routing / eval

General-purpose prompt for a future chat to diagnose a specific exchange. Covers:
- How to pull VM logs for a time window
- Latency breakdown by component (Coordinator → specialists → Synthesizer)
- What to look for: cache failures, high turn counts, native loop failures, dispatch errors
- Routing evaluation: were the right specialists called, were directives targeted, was RESOLVED_INTENT correct
- What should have happened vs what did: read COORD PACKAGE + `data/conversations/YYYY-MM-DD.jsonl`, compare

Prompt text is in the chat transcript. To reuse: paste the prompt block into a new chat, fill in the time window, and read the architecture files listed before investigating.

---

### 3. Interchange ID — recommendation and implementation prompt

**Question:** Do timestamps suffice, or should each exchange have a shorthand ID for human reference?

**Recommendation:** Timestamps are sufficient for log correlation but poor for human conversation ("the one at 14:23" is awkward). A zero-padded daily sequence number (`001`, `002`, `003`…) written to the conversation JSONL as a `seq` field is the right minimal addition. Resets per day. Shorthand: "exchange 14" or "#014".

**Decision deferred to implementer.** Implementation prompt written (in chat transcript) covering:
- `core/server.py` — `_log_conversation`: count existing entries to determine next seq, write `"seq": "003"` to the log entry; handle threading safely (reference: `write_log` lock pattern in `tools/logger.py`)
- `/monitor/conversations` — pass `seq` through automatically (it comes from the JSONL)
- `tools/metatron_monitor.py` — Column 1: display `#003  14:23` format; omit seq chip for old entries without the field

---

## What's next

- Implement interchange ID (from prompt above) — or defer if other priorities take precedence
- Specialist token reduction (plan Steps 3–5) — biggest remaining latency lever; specialists still running 5–8 tool-call turns
- B1 / Check 10 / Check 12 → A7 sign-off
