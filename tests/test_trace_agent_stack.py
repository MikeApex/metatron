"""
tests/test_trace_agent_stack.py — push_agent/pop_agent restore the parent.

[DB-0810-02]. `pop_agent()` used to stamp the duration and stop, leaving the
thread-local `current_agent` pointing at the child that had just returned. Every
tool call made *after* a nested `run_subagent` came back was therefore recorded
against the subagent instead of the agent that actually made it, and The Book
rendered it that way. Nothing tested this, which is why it survived.

The tests below are all synchronous and single-threaded on purpose: that is the
path the bug was on. The parallel dispatch sites in core/orchestrator.py seed a
*worker thread's* fresh thread-local from the parent and are a different
mechanism — pop cannot cross a thread boundary, so those must keep doing it.

Run: python3 tests/test_trace_agent_stack.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.trace as _tr  # noqa: E402

_results: list[tuple[bool, str]] = []


def check(label: str, condition: bool) -> None:
    _results.append((bool(condition), label))
    print(f"  {'PASS' if condition else 'FAIL'}  {label}")


def main() -> int:
    # --- the regression this fix exists for ---------------------------------
    _tr.set_trace(None)
    _tr._set_current_agent(None)
    _tr.start_request_trace("what's on today?", persona=None)

    coord = _tr.push_agent("coordinator", "gemini", "test-model")
    check("push sets the pushed agent as current", _tr.get_current_agent() is coord)

    spec = _tr.push_agent("logistics", "gemini", "test-model")
    check("a nested push makes the child current", _tr.get_current_agent() is spec)

    _tr.pop_agent(spec)
    check("THE FIX — popping the child restores the parent as current",
          _tr.get_current_agent() is coord)

    _tr.pop_agent(coord)
    check("popping the top-level agent restores None",
          _tr.get_current_agent() is None)

    # --- depth: three levels unwind in order --------------------------------
    a = _tr.push_agent("coordinator", "gemini", "m")
    b = _tr.push_agent("research_agent", "gemini", "m")
    c = _tr.push_agent("diarist", "ollama", "m")
    _tr.pop_agent(c)
    check("three-deep unwind: after the innermost pop, the middle is current",
          _tr.get_current_agent() is b)
    _tr.pop_agent(b)
    check("three-deep unwind: then the outermost", _tr.get_current_agent() is a)
    _tr.pop_agent(a)
    check("three-deep unwind: then None", _tr.get_current_agent() is None)

    # --- a tool call after a nested subagent returns is attributed correctly --
    # This is the user-visible symptom, expressed against the record itself
    # rather than against the thread-local.
    parent = _tr.push_agent("coordinator", "gemini", "m")
    child = _tr.push_agent("logistics", "gemini", "m")
    _tr.record_tool_call(_tr.get_current_agent(), 1, "write_log", {}, "ok", 1.0)
    _tr.pop_agent(child)
    _tr.record_tool_call(_tr.get_current_agent(), 1, "read_goals", {}, "ok", 1.0)
    _tr.pop_agent(parent)

    parent_tools = [tc.name for t in parent.turns for tc in t.tool_calls]
    child_tools = [tc.name for t in child.turns for tc in t.tool_calls]
    check("the post-return tool call lands on the parent", parent_tools == ["read_goals"])
    check("the in-subagent tool call stays on the child", child_tools == ["write_log"])

    # --- an agent that raises must not pin the thread-local ------------------
    outer = _tr.push_agent("coordinator", "gemini", "m")
    inner = _tr.push_agent("finance", "gemini", "m")
    try:
        raise RuntimeError("specialist blew up")
    except RuntimeError:
        _tr.pop_agent(inner)          # what the orchestrator's `finally` does
    check("a pop after an exception still restores the parent",
          _tr.get_current_agent() is outer)
    _tr.pop_agent(outer)

    # --- the parent link must never reach the trace file ---------------------
    top = _tr.push_agent("coordinator", "gemini", "m")
    nested = _tr.push_agent("logistics", "gemini", "m")
    _tr.pop_agent(nested)
    _tr.pop_agent(top)
    d = _tr._agent_to_dict(top)
    check("the parent back-reference is not serialised", "parent" not in d)

    _tr.set_trace(None)
    _tr._set_current_agent(None)

    print()
    failed = [label for ok, label in _results if not ok]
    if failed:
        print(f"{len(failed)} check(s) FAILED:")
        for label in failed:
            print(f"  - {label}")
        return 1
    print("All trace agent-stack checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
