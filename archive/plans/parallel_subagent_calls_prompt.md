# Parallel Subagent Dispatch — Implementation Prompt
*Use this to open a new Claude Code session for this task.*

---

You are Claude Code implementing a specific, well-scoped change to a personal AI life manager.
Working directory: ~/Desktop/multi-model-mcp

Read these files before doing anything else:
- `CLAUDE.md` — architecture and conventions
- `core/orchestrator.py` — the runtime (focus on `run_session_anthropic`, `_openai_compat_loop`, `dispatch_tool`)
- `tools/subagent.py` — `run_subagent` and `run_model_conference`
- `tools/logger.py` — `write_log` (read-modify-write pattern, race condition risk)

---

## What this task is

The orchestrator currently runs all tool calls from a model response **sequentially**. When the Coordinator fans out to 3-4 specialists via `run_subagent`, each API call waits for the previous one to complete. With each specialist taking ~10s, a 4-specialist exchange takes ~40s.

The fix: **parallelize `run_subagent` and `run_model_conference` tool calls** within a single response batch using `concurrent.futures.ThreadPoolExecutor`. All other tool calls remain sequential.

This is purely a latency optimization. The behavior is otherwise identical — results are collected and returned to the model in the same format, matched to their tool IDs.

---

## Why only `run_subagent` and `run_model_conference`?

`run_subagent` and `run_model_conference` each spawn full agent sessions with their own API calls — they are I/O-bound and take 5-15 seconds each. All other tools (write_log, search_memory, write_journal, etc.) are fast local operations. The benefit of parallelizing fast local tools is near zero, and it adds complexity.

There is also a **race condition risk**: `write_log` uses a read-modify-write pattern (reads existing JSON, merges new fields, writes back). Specialists called in parallel each call `write_log` internally. If those writes overlap on the same file, data can be lost. This must be fixed before parallelizing.

---

## Scope of changes

### 1. `tools/logger.py` — add a module-level threading lock to `write_log`

Add a `threading.Lock` that wraps the read-modify-write block in `write_log`. This prevents data loss when parallel specialist sessions write to the same daily log file simultaneously.

```python
import threading
_WRITE_LOG_LOCK = threading.Lock()
```

Inside `write_log`, wrap the read-modify-write block:

```python
with _WRITE_LOG_LOCK:
    existing = {}
    if log_path.exists():
        with open(log_path) as f:
            existing = json.load(f)
    existing.update(content)
    existing["date"] = log_date
    with open(log_path, "w") as f:
        json.dump(existing, f, indent=2)
    os.chmod(log_path, 0o600)
```

The memory indexing call that follows can remain outside the lock (it writes to a separate FAISS index, not the log file).

### 2. `core/orchestrator.py` — parallelize subagent tool dispatch in both loops

**In `run_session_anthropic`:**

In the tool dispatch section (currently a sequential `for tc in tool_calls` loop), split calls into two groups: subagent calls and everything else.

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

_PARALLEL_TOOLS = {"run_subagent", "run_model_conference"}

# Dispatch non-parallel tools first (sequential, fast)
tool_results = []
parallel_calls = []
for tc in tool_calls:
    if tc.name in _PARALLEL_TOOLS:
        parallel_calls.append(tc)
    else:
        result = dispatch_tool(tc.name, tc.input, tool_handlers)
        tool_results.append({
            "type": "tool_result",
            "tool_use_id": tc.id,
            "content": result,
        })

# Dispatch subagent/conference calls in parallel
if parallel_calls:
    with ThreadPoolExecutor() as executor:
        future_to_tc = {
            executor.submit(dispatch_tool, tc.name, tc.input, tool_handlers): tc
            for tc in parallel_calls
        }
        for future in as_completed(future_to_tc):
            tc = future_to_tc[future]
            try:
                result = future.result()
            except Exception as e:
                result = f"Error: {e}"
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc.id,
                "content": result,
            })
```

**In `_openai_compat_loop`:**

Apply the same pattern to the `for tc in message.tool_calls` dispatch loop. The result format is slightly different (uses `tool_call_id` instead of `tool_use_id`):

```python
parallel_calls = []
for tc in message.tool_calls:
    inputs = json.loads(tc.function.arguments)
    if tc.function.name in _PARALLEL_TOOLS:
        parallel_calls.append((tc, inputs))
    else:
        result = dispatch_tool(tc.function.name, inputs, tool_handlers)
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": result,
        })

if parallel_calls:
    with ThreadPoolExecutor() as executor:
        future_to_tc = {
            executor.submit(dispatch_tool, tc.function.name, inputs, tool_handlers): tc
            for tc, inputs in parallel_calls
        }
        for future in as_completed(future_to_tc):
            tc = future_to_tc[future]
            try:
                result = future.result()
            except Exception as e:
                result = f"Error: {e}"
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })
```

Define `_PARALLEL_TOOLS` as a module-level constant near the top of `orchestrator.py`.

---

## What NOT to do

- Do not change `dispatch_tool` itself — keep it a simple synchronous function
- Do not parallelize all tools — only `run_subagent` and `run_model_conference`
- Do not change `run_subagent` or `run_model_conference` in `tools/subagent.py`
- Do not change the pipeline flow in `run_pipeline_session`
- Do not change routing, config loading, or agent files
- Do not add async/await — threading is the right approach here (I/O-bound, not CPU-bound)

---

## Verification

1. **Lock test**: Run two concurrent `write_log` calls in a Python test script targeting the same log file. Confirm both field sets appear in the output with no data lost.

2. **Parallel dispatch test**: Run a quick orchestrator session with `--agent coordinator` and a message likely to trigger 2+ specialist calls (e.g. "I'm feeling tired and behind on work"). Confirm:
   - Both specialists are called (check their output appears in the Synthesizer's context)
   - Total elapsed time is less than the sum of individual specialist times
   - No file corruption in `data/logs/`

3. **Single-specialist test**: Confirm that sessions routing to only one specialist still work correctly.

4. **Error handling**: Confirm that a failed parallel call (e.g., API error in one specialist) does not crash the whole exchange — the error is returned as the tool result and the model handles it.

---

## Notes

- `_PARALLEL_TOOLS` is a module-level constant — add it near the top of orchestrator.py after the existing constants
- The `as_completed` approach means parallel results may arrive in a different order than the original tool call list. This is fine — results are matched to tool IDs, and the Anthropic/OpenAI APIs match by ID, not position
- ThreadPoolExecutor with default `max_workers` is fine — Python will allocate one thread per future, and typical specialist fan-out is 2-5 calls
- Do not add any user-visible output about parallelism
