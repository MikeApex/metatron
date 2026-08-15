"""
tests/test_action_provenance.py — the ACTIONS line the Synthesizer receives says
what actually ran ([DB-0810-13]).

Two things are checked, and the first matters more than the second:

1. **Every registered tool is explicitly classified** as an action or a read in
   core/actions.py. Without this, a tool added next month is classified by a name
   prefix — and a state-changing tool that guesses wrong is invisible in the
   line, which is exactly the silent failure that let "That's sent" through on
   2026-08-10. The guard has to be a test, because nothing at runtime notices.
2. **The line itself**: reads excluded, failures visible, none-case explicit.

The registered tool names are read by grepping core/orchestrator.py's handlers
dict rather than calling register_tools(), which imports FAISS, CalDAV and the
mail stack. Same trade-off, and the same limit, as
tests/test_quality_event_reconciliation.py: if the handlers dict is ever built
somewhere other than that literal, this stops covering it.

Standalone runner (no pytest dependency), matching the convention of the other
scripts in tests/.

Usage:
    python3 tests/test_action_provenance.py

Exits 0 if every check passes, 1 otherwise.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.actions import (  # noqa: E402
    ACTION_TOOLS, READ_TOOLS, action_provenance_block, is_action, is_classified,
)
from core.trace import AgentRecord, RequestTrace, ToolCallRecord, TurnRecord  # noqa: E402

_results: list[tuple[str, bool, str]] = []


def check(name: str):
    """Decorator: run a test function, record pass/fail rather than aborting."""
    def wrap(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except AssertionError as e:
            _results.append((name, False, f"assertion: {e}"))
        except Exception as e:
            _results.append((name, False, f"{type(e).__name__}: {e}"))
        return fn
    return wrap


_HANDLER_RE = re.compile(r'^\s{8}"([a-z_]+)":\s*[a-z_]+,\s*$', re.MULTILINE)


def _registered_tool_names() -> set[str]:
    text = (ROOT / "core" / "orchestrator.py").read_text(encoding="utf-8")
    body = text.split("    handlers = {", 1)[1].split("\n    }", 1)[0]
    return set(_HANDLER_RE.findall(body))


def _trace_with(calls: list[tuple[str, bool]], nested: bool = False) -> RequestTrace:
    """A trace carrying (tool_name, ok) calls on one agent, optionally nested."""
    t = RequestTrace("test", None)
    turn = TurnRecord(turn=1)
    for name, ok in calls:
        turn.tool_calls.append(ToolCallRecord(
            name=name, args={}, result_preview="" if ok else "Error: nope",
            duration_ms=1.0, ok=ok,
        ))
    rec = AgentRecord(agent="relationships", provider="gemini", model="m")
    rec.turns.append(turn)
    coord = AgentRecord(agent="coordinator", provider="gemini", model="m")
    if nested:
        coord.subagents.append(rec)
        t.pipeline.append(coord)
    else:
        t.pipeline.append(rec)
    return t


# ---------------------------------------------------------------------------

@check("every registered tool is explicitly classified — no prefix guessing")
def _():
    registered = _registered_tool_names()
    assert len(registered) > 50, f"handlers-dict scan found only {len(registered)} tools — scan is broken"
    unclassified = {n for n in registered if not is_classified(n)}
    assert not unclassified, (
        f"{sorted(unclassified)} are registered tools but appear in neither "
        f"ACTION_TOOLS nor READ_TOOLS in core/actions.py. Add each one: it is an "
        f"ACTION if calling it changes stored state or reaches the outside world, "
        f"a READ if it only looks something up. Leaving it out means a "
        f"state-changing tool can run without appearing on the ACTIONS line, "
        f"which is the [DB-0810-13] failure."
    )


@check("the two sets are disjoint")
def _():
    both = ACTION_TOOLS & READ_TOOLS
    assert not both, f"{sorted(both)} are classified as both action and read"


@check("the Kathaleen shape: lookups alone report NONE")
def _():
    block = action_provenance_block(_trace_with([("search_contacts", True),
                                                 ("list_obligations", True)]))
    assert "NONE" in block, block
    assert "search_contacts" not in block, "a read reached the ACTIONS line"


@check("no trace and an empty trace both report NONE, never silence")
def _():
    assert "NONE" in action_provenance_block(None)
    assert "NONE" in action_provenance_block(RequestTrace("test", None))


@check("a failed action is visible and not reported as done")
def _():
    block = action_provenance_block(_trace_with([("send_email", False)]))
    assert "send_email" in block
    assert "FAILED" in block, block
    assert "NONE" not in block


@check("a tool returning an Error string counts as failed even when ok=True")
def _():
    # dispatch_tool only sets ok=False when it raises or the args will not bind;
    # a tool that returns "Error: ..." from its own body records ok=True.
    t = _trace_with([("write_calendar_event", True)])
    t.pipeline[0].turns[0].tool_calls[0].result_preview = "Error: CalDAV rejected the event"
    block = action_provenance_block(t)
    assert "FAILED" in block, block


@check("successes are counted, and repeats collapse to one row")
def _():
    block = action_provenance_block(_trace_with([("write_calendar_event", True),
                                                 ("write_calendar_event", True),
                                                 ("write_log", True)]))
    assert "write_calendar_event — completed x2" in block, block
    assert "write_log — completed" in block


@check("actions inside a dispatched specialist are counted (nested records)")
def _():
    block = action_provenance_block(_trace_with([("send_email", True)], nested=True))
    assert "send_email — completed" in block, block


@check("failures sort above successes")
def _():
    block = action_provenance_block(_trace_with([("write_log", True),
                                                 ("send_email", False)]))
    lines = [ln for ln in block.splitlines() if ln.startswith("- ")]
    assert lines[0].startswith("- send_email"), lines


@check("an unknown tool is reported as an action, not dropped")
def _():
    assert is_action("blow_up_the_moon")
    assert not is_action("read_something_new")
    block = action_provenance_block(_trace_with([("blow_up_the_moon", True)]))
    assert "unrecognised tool" in block, block


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    failed = 0
    for name, ok, detail in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}{'' if ok else '  — ' + detail}")
        failed += 0 if ok else 1
    print(f"\n{len(_results) - failed}/{len(_results)} passed")
    sys.exit(1 if failed else 0)
