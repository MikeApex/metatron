# 2026-06-26 — SEQ 031 Troubleshoot and Context Tracker Refactor

## What this session covered

Three-part session: a single-exchange post-mortem (SEQ 031), follow-on fixes from its findings, and a full architectural redesign of how the context tracker is written.

---

## Part 1 — SEQ 031 Post-Mortem

**Exchange:** Mike said "I'd like to update your preferences for how we interact. I don't need commendation and validation for everything I share." — user received "I can't help with that right now."

**Root causes identified (three):**

1. **Output filter false positive.** Synthesizer's response included the phrase "fatherhood and daily logistics." The word `logistics` matched the output filter's banned-terms list as a substring, suppressing the entire response. The conversation log records the pre-filter response (logged before `filter_output()` runs), which is why the tracker showed a coherent response but the user saw the fallback.

2. **Preference not durably stored.** The Synthesizer correctly captured the communication preference in `write_context_tracker` → `data/personas/mike/context.json`. But the context tracker is session-level state; `config/personas/mike.md` (the durable persona file) was not updated. The preference would not survive a context tracker reset.

3. **Double-turn token overhead.** Two turns visible in trace for every Synthesizer exchange: turn 1 calls `write_context_tracker` (tool call), turn 2 produces the actual text response. The second turn re-sends the full context window (~8,500 input tokens at Pro pricing). Avg overhead: ~$0.066/exchange. At 300 exchanges/month, nearly the entire $20 billing cap.

**Also diagnosed:** `config/personas/mike.md` was not visible in VSCode because it is in `.gitignore` (real user persona config — sensitive). File exists locally but VS Code's file explorer respects gitignore.

---

## Part 2 — Fixes Deployed

### Output filter — two-tier whitelist

`filter_output()` in `core/orchestrator.py` refactored:

- **`_ALWAYS_CONFIDENTIAL`** — code identifiers (anything with underscores or slashes). Always flagged on substring match. No change to behavior for these.
- **`_CONTEXT_SENSITIVE`** — common English words that are also internal names: `relationships`, `finance`, `logistics`, `diarist`, `coordinator`, `synthesizer`, `orchestrator`. These are only flagged when architecture vocabulary (`agent`, `specialist`, `routing`, `pipeline`, `module`, `dispatch`, `tool call`, `system prompt`, `subagent`) appears in the same sentence. "Daily logistics" no longer triggers the filter. "Call the logistics agent" still does.
- Helper `_sentence_bounds()` extracts the sentence containing a match for context checking.

Committed `4984f48`.

### mike.md updated

`config/personas/mike.md` updated with:
- Goals interview completed 2026-06-26 (removed "not yet completed" note)
- **Interaction Preferences section:** No commendation or validation. When following up, build into something new or ask a question that permits deeper knowledge — do not summarise or confirm.

File is gitignored — pushed directly to VM via `gcloud compute scp`.

### write_persona tool (new)

`tools/persona.py` — `write_persona(section, content)` tool for the Synthesizer. Adds or replaces a named section in `config/personas/{persona}.md`. Synthesizer calls this when a user explicitly states an interaction preference, alongside the `[CONTEXT]` block (not instead of it).

Registered in `core/orchestrator.py`. Added to Synthesizer `allowed_tools` in both `routing_cloud.yaml` and `routing.yaml`. Instruction added to `config/agents/synthesizer.md`.

Note: `write_persona` was already present in `synthesizer.md` HEAD from a prior session — the routing config registration was the actual missing piece.

---

## Part 3 — Context Tracker Architectural Refactor

### The problem

`write_context_tracker` was the Synthesizer's most expensive tool call: it added a full second API turn to every exchange (the tool call JSON in turn 1 forces a turn 2 to produce the actual text response). For exchanges also using `run_subagent`, this created 3-turn sequences. The Synthesizer instruction to "call both in the same turn" is impossible at the API level — the model must receive the tool result before writing text.

Real numbers from 35 traced exchanges:
- Avg extra input per 2-turn exchange: **8,500 tokens at Pro pricing = $0.066**
- At 300 exchanges/month: **$19.67 saved** — nearly the entire billing cap

### Design decision: invisible [CONTEXT] block

Instead of a tool call, Synth now appends a structured block after its visible response:

```
[visible response to user]

[CONTEXT]
{"open_threads": [...], "patterns": [...], "follow_ups": [...], "held_items": [...]}
[/CONTEXT]
```

The orchestrator streaming parser intercepts `[CONTEXT]` before it reaches the client, parses the JSON, and calls `write_context_tracker()` directly (Python function call, no LLM turn). Synth focuses on responding; the tracker write is invisible infrastructure.

**Why this approach:**
- **Held item fidelity:** Synth authors held items in the same generation pass as its visible response — it knows what it held and why. A post-hoc background call can't reconstruct suppressed editorial decisions.
- **One turn for simple exchanges, always** (two for exchanges with `run_subagent`).
- **No background threading, no race conditions.** Parse and write happen synchronously after stream ends, before `[DONE]` is sent.
- **Filter safety:** `[CONTEXT]` block is stripped before `filter_output()` runs, before conversation history is updated, before conversation log is written. Filter only sees the visible portion — no false positives on agent names inside the context block.

**Alternatives considered and rejected:**
- Background Flash-Lite thread: loses held item fidelity (can't reconstruct what Synth suppressed)
- Diarist consolidation: same fidelity problem
- Batch every N: arbitrary frequency, staleness risk
- Conditional write only: removes subtler context, "more is more" when processing is cheap

### Streaming parser implementation

`run_pipeline_session_stream()` in `core/orchestrator.py`:

- Lookahead window (`len("[CONTEXT]") - 1` chars) held in `pending` buffer
- When `[CONTEXT]` is detected: flush everything before it to the client, switch to buffer-only mode
- If delimiter splits across chunks, lookahead window prevents partial `[C` from reaching client
- After stream: partition on `[CONTEXT]`, strip `[/CONTEXT]` closing tag, parse JSON, call `write_context_tracker()`
- Fallback: if block absent or JSON malformed, logs `WARNING: [context_block] ...` and continues
- `AI_TEST_PERSONA` now set at the start of `run_pipeline_session_stream()` (previously only set in `run_session()` — direct tool calls in the streaming path were using a stale env var)

### Config changes

- `write_context_tracker` removed from Synthesizer `allowed_tools` in both routing configs
- Synthesizer instruction section "Internal note to Coordinator" replaced with "Response format — mandatory" specifying the `[CONTEXT]` block format
- **Recency bias guard** added to instruction: "Before writing each item, ask: is this genuinely new information, or am I re-listing something that already exists in the prior context? A pattern already noted should only reappear if it was directly reinforced or contradicted this exchange."
- `write_context_tracker` removed from the Tools section of `synthesizer.md`

Committed `5df05aa`, deployed via `./deploy.sh`.

### Test result

Live exchange on VM (post-deploy):

- **Visible response:** "With the sleep deficit cleared, the hold on higher-intensity exercise is lifted. Looking ahead to Monday, what are your expectations for the conference with Miss Ruby?" — clean, no `[CONTEXT]` leaked
- **Control token:** `[DONE]`
- **`[CONTEXT]` in client output:** `False`
- **Synthesizer turns:** 1 (was 2-3). `turn1: in=11,336 out=187 tools=[]`
- **context.json written correctly**, including held item: *"Mental Wellbeing's observation connecting sleep to cognitive function: Held to respect zero-validation preference; Mike already explicitly made the connection himself."*

All three verification points pass.

---

## Commits this session

| Hash | Description |
|---|---|
| `4984f48` | Output filter: context-sensitive whitelist; add write_persona tool |
| `5df05aa` | Synthesizer: replace write_context_tracker tool with inline [CONTEXT] block |

---

## Open / follow-up

- Conversation log write for the test exchange was not captured (test client closed connection before server ran `_log_conversation` — expected for a raw Python test client; not a production issue)
- `write_calendar_event` real calendar integration still unverified (carried from prior session)
- A7 Phase 5 sign-off still pending (B1, Check 10, Check 12 on hold)
