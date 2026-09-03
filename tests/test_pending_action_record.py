"""
tests/test_pending_action_record.py — a gated action never enters the durable
record as something that happened ([DB-0829-01]).

The live failure, 2026-08-29, read off the VM trace on 2026-09-03. Mike asked for an
email to Iva Diamond at 13:00. `send_email` raised the confirm gate correctly and sent
nothing. Three separate things then reported it as done anyway:

1. **The ACTIONS provenance line** — `core/actions.py` had two outcomes, completed and
   failed, and a gated call is neither. It printed `send_email — completed`, to the
   Synthesizer and to the journal (journalctl 13:00:18).
2. **The fire-and-forget Diarist** — dispatched 1.6 s into the turn, BEFORE the blocking
   specialist called `send_email`, carrying the Coordinator's optimistic directive
   *"Log that user sent an email to Iva Diamond to coordinate a call for next week."*
   It wrote that into the day log verbatim. Mike declined the send at 13:05.
3. **The user-facing reply** — *"That's sent to Iva."* matched none of
   `_COMPLETION_CLAIM_RES`, so `enforce_pending_receipt()` appended its correction to
   the false claim instead of replacing it.

The specialist that watched the gate fire logged it correctly, which is the control
case here and is asserted too: the fix must not make correct behaviour noisier.

Standalone runner (no pytest dependency), matching the convention of the other
scripts in tests/.

Usage:
    python3 tests/test_pending_action_record.py

Exits 0 if every check passes, 1 otherwise.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.actions import action_provenance_block  # noqa: E402
from core.trace import AgentRecord, RequestTrace, ToolCallRecord, TurnRecord  # noqa: E402
import core.orchestrator as ORC  # noqa: E402

_results: list[tuple[str, bool, str]] = []


def check(name: str):
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


# The real payload tools/confirm.py returns instead of performing the action, and the
# real one from the 2026-08-29 trace — truncated by core/trace.py at 800 chars, which
# is why the status has to be findable in the first field.
_GATED = (
    '{\n  "status": "PENDING_CONFIRMATION",\n  "confirm_token": "lMNETmGhYrG-ss4Hv-iisw",'
    '\n  "description": "Send an email to Iva Diamond (iva.diamond@bp.com)\\nSubject: '
    'Catching up soon",\n  "expires_in_seconds": 600\n}'
)
_DECLINED = '{\n  "status": "DECLINED_RECENTLY",\n  "description": "Send an email"\n}'

_PENDING = [{"token": "t1", "action": "send_email",
             "description": "Send an email to Iva Diamond (iva.diamond@bp.com)"}]


def _trace_with(calls: list[tuple[str, str]]) -> RequestTrace:
    """A trace carrying (tool_name, result_preview) calls on one specialist."""
    t = RequestTrace("test", None)
    turn = TurnRecord(turn=1)
    for name, preview in calls:
        turn.tool_calls.append(ToolCallRecord(
            name=name, args={}, result_preview=preview, duration_ms=1.0, ok=True,
        ))
    rec = AgentRecord(agent="relationships", provider="gemini", model="m")
    rec.turns.append(turn)
    t.pipeline.append(rec)
    return t


# --- 1. the ACTIONS line ----------------------------------------------------

@check("the 2026-08-29 line no longer reads 'send_email — completed'")
def _():
    block = action_provenance_block(_trace_with([("send_email", _GATED)]))
    assert "send_email" in block, block
    assert "completed" not in block, (
        "a gated send is still reported as completed — this is the line that reached "
        f"the journal at 13:00:18:\n{block}")
    assert "AWAITING THE USER'S APPROVAL" in block, block
    assert "NOT performed" in block, block


@check("a declined action is not reported as completed either")
def _():
    block = action_provenance_block(_trace_with([("send_email", _DECLINED)]))
    assert "completed" not in block, block
    assert "NOT performed" in block, block


@check("a gated call is not reported as a failure — it did not fail")
def _():
    block = action_provenance_block(_trace_with([("send_email", _GATED)]))
    assert "FAILED" not in block, block


@check("a real completion is still reported as completed")
def _():
    block = action_provenance_block(_trace_with([("write_log", "Log written to /x.json")]))
    assert "write_log — completed" in block, block


@check("a real failure is still reported as a failure")
def _():
    block = action_provenance_block(_trace_with([("send_email", "Error: SMTP refused")]))
    assert "ATTEMPTED AND FAILED" in block, block


@check("gated and completed actions in one request are both stated, gated first")
def _():
    block = action_provenance_block(_trace_with([
        ("write_log", "Log written to /x.json"), ("send_email", _GATED)]))
    lines = [ln for ln in block.splitlines() if ln.startswith("- ")]
    assert len(lines) == 2, lines
    assert lines[0].startswith("- send_email"), lines
    assert "AWAITING" in lines[0], lines
    assert "write_log — completed" in lines[1], lines


# --- 2. the fire-and-forget directive ---------------------------------------

@check("the 2026-08-29 Diarist directive is corrected before it is dispatched")
def _():
    directive = ("Log that user sent an email to Iva Diamond to coordinate a call "
                 "for next week.")
    amended, asserted = ORC.pending_directive_note(directive, _PENDING)
    assert asserted, (
        "the directive says the user 'sent' an email while send_email is awaiting "
        "approval, and that was not detected")
    assert "has NOT happened" in amended, amended
    assert "never as completed" in amended, amended
    assert "Iva Diamond" in amended
    # The original text is kept: the note corrects it, it does not replace the turn.
    assert directive in amended, amended


@check("a directive with nothing pending is returned untouched")
def _():
    directive = "Log that user sent an email to Iva Diamond."
    amended, asserted = ORC.pending_directive_note(directive, [])
    assert amended == directive, amended
    assert not asserted


@check("an innocent directive still gains the true state, but is not flagged")
def _():
    directive = "Log that the user had breakfast with family."
    amended, asserted = ORC.pending_directive_note(directive, _PENDING)
    assert not asserted, "no completion word for send_email appears in this directive"
    assert "has NOT happened" in amended, (
        "the pending action must be stated even when the directive is innocent — "
        "otherwise the Diarist writes the day up as though nothing was proposed")
    assert directive in amended


@check("a completion word for a DIFFERENT action does not fire")
def _():
    # 'merged' is a merge_contacts word. Only send_email is pending, so the closed map
    # must not fire on it — this is what keeps the check out of semantic guessing.
    directive = "Log that the user merged two documents by hand."
    _, asserted = ORC.pending_directive_note(directive, _PENDING)
    assert not asserted


@check("the Diarist is dispatched AFTER the blocking specialists, not before")
def _():
    # The ordering IS the fix: a fire-and-forget thread started during the dispatch
    # loop cannot see a confirmation raised by a specialist that has not run yet.
    src = (ROOT / "core" / "orchestrator.py").read_text(encoding="utf-8")
    body = src.split("def _dispatch_from_coordinator(", 1)[1].split("\ndef ", 1)[0]
    assert "fire_and_forget.append" in body, (
        "fire-and-forget agents are no longer collected for deferred dispatch")
    collect = body.index("fire_and_forget.append")
    blocking_done = body.index("for future in as_completed(futures)")
    start = body.index("threading.Thread(target=_bg, daemon=True).start()")
    assert collect < blocking_done < start, (
        "the fire-and-forget thread starts before the blocking specialists finish — "
        "the [DB-0829-01] race is back")


# --- 3. the user-facing reply ------------------------------------------------

@check("the live reply \"That's sent to Iva.\" is replaced, not appended to")
def _():
    out = ORC.enforce_pending_receipt("That's sent to Iva. I'll leave you to it.",
                                      _PENDING)
    assert "That's sent" not in out, (
        f"the false claim survived alongside its own correction:\n{out}")
    assert "Waiting for your approval" in out, out


@check("ordinary uses of 'that sent' are not read as completion claims")
def _():
    for text in ("That sent me down a rabbit hole.", "That send is scheduled for later."):
        out = ORC.enforce_pending_receipt(text, _PENDING)
        assert text in out, f"false positive on: {text!r}\n{out}"


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    failed = 0
    for name, ok, detail in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}{'' if ok else '  — ' + detail}")
        failed += 0 if ok else 1
    print(f"\n{len(_results) - failed}/{len(_results)} passed")
    sys.exit(1 if failed else 0)
