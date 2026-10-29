"""
tests/test_tool_error_dict.py — a tool that reports failure as {"error": ...} is a failure,
[DB-0910-02].

Live 2026-09-10 07:30: Logistics' `read_calendar` got CalDAV 401 and returned
{"error": "CalDAV request failed: 401 …"}. dispatch_tool() JSON-encoded it, so the result
began with "{" and neither the "Error:" prefix check nor _failed_tool_calls() saw it. The
trace recorded ok:true, no [TOOL FAILURES] marker reached the Synthesizer, and the reply stated
a remembered lecture as today's confirmed commitment. Eighteen tool files share this shape.

Standalone runner (no pytest dependency).

Usage:
    python3 tests/test_tool_error_dict.py

Exits 0 if every test passes, 1 otherwise.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.orchestrator import _failed_tool_calls, dispatch_tool  # noqa: E402
from core.trace import AgentRecord  # noqa: E402

_results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    _results.append((name, condition, detail))


def _calendar_401():
    return {"error": "CalDAV request failed: 401 Unauthorized"}


def _calendar_ok():
    return {"count": 0, "events": []}


def _null_error():
    return {"status": "ok", "error": None}


HANDLERS = {"read_calendar": _calendar_401, "read_calendar_ok": _calendar_ok,
            "null_error": _null_error}


def _run(name: str) -> AgentRecord:
    rec = AgentRecord(agent="logistics", provider="gemini", model="m")
    dispatch_tool(name, {}, HANDLERS, _agent_rec=rec, _turn_num=1)
    return rec


rec = _run("read_calendar")
tc = rec.turns[0].tool_calls[0]
check("a {'error': ...} result is recorded ok:false", tc.ok is False, repr(tc.result_preview[:80]))
failed = _failed_tool_calls(rec)
check("and is reported upward as a failed tool call",
      len(failed) == 1 and "read_calendar" in failed[0], repr(failed))

rec = _run("read_calendar_ok")
check("a dict without an error key stays ok", rec.turns[0].tool_calls[0].ok is True)
check("and is not reported as failed", _failed_tool_calls(rec) == [])

rec = _run("null_error")
check("a null error key is not a failure", rec.turns[0].tool_calls[0].ok is True)

rec = AgentRecord(agent="logistics", provider="gemini", model="m")
dispatch_tool("read_calendar", {}, HANDLERS, _agent_rec=rec, _turn_num=1)
HANDLERS["read_calendar"] = _calendar_ok
dispatch_tool("read_calendar", {}, HANDLERS, _agent_rec=rec, _turn_num=2)
check("a failure later retried successfully is not reported (the action did happen)",
      _failed_tool_calls(rec) == [], repr(_failed_tool_calls(rec)))


def main() -> int:
    passed = sum(1 for _, ok, _ in _results if ok)
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if not ok and detail else ""))
    print(f"\n{passed} passed, {len(_results) - passed} failed, {len(_results)} total")
    return 0 if passed == len(_results) else 1


if __name__ == "__main__":
    sys.exit(main())
