"""
tests/test_turn_referent.py — the [DB-0826-01] referent block says what HAPPENED.

The failure: a short referring turn — "undo that merge", "approved", "now set it back to
Iva" — resolved against the wrong thing, five times between 2026-08-10 and 2026-08-29.
The cause, measured 2026-09-03: the Coordinator was never given the conversation, so
"that merge" was matched against the only merge-shaped thing in its context, which on
2026-08-26 was a Prudential Apex branch merge sitting in the day logs.

tools/turn_referent.py is the half of the fix that a transcript cannot supply. On
2026-08-29 the assistant's own text said the email to Iva was sent; it was pending, and
the user then declined it. So the tests below are ordered by what actually matters:

  1. It FAILS OPEN. Missing directory, torn JSON, unparseable timestamp, stale turn,
     ledgers raising — every one returns "" and none raises. This is the opposite of
     tools/turn_context.py's fail-closed rule, and the two are easy to confuse: that
     module decides whether a refused action may come back, where being wrong re-opens
     a loop the user escaped. This one only adds evidence to a prompt, so a missing
     trace file must never cost the user their turn.
  2. Pending and declined override the reply text. The 2026-08-29 case.
  3. Classification comes from core/actions.py, not a second prefix list of its own —
     otherwise this block and the ACTIONS line the Synthesizer receives can disagree
     about what ran.

Standalone runner (no pytest dependency), matching tests/test_pending_receipt.py.

Usage:
    python tests/test_turn_referent.py

Exits 0 if every test passes, 1 otherwise.
"""

import json
import shutil
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools import turn_referent as tr  # noqa: E402

_results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    _results.append((name, bool(ok), detail))


def _write_trace(root: Path, *, ts: datetime, user_input="", synth_response="",
                 tool_calls=(), is_proactive=False) -> None:
    traces = root / "traces"
    if traces.exists():
        shutil.rmtree(traces)
    traces.mkdir(parents=True, exist_ok=True)
    rec = {
        "trace_id": "t1", "ts": ts.isoformat(), "persona": "p",
        "user_input": user_input, "synth_response": synth_response,
        "is_proactive": is_proactive,
        # Nested one level: a specialist's tool calls live in `subagents`, and reading
        # only the top level would miss every action the Coordinator dispatched.
        "pipeline": [{"agent": "coordinator", "turns": [], "subagents": [
            {"agent": "relationships", "subagents": [],
             "turns": [{"turn": 1, "tool_calls": list(tool_calls)}]}]}],
    }
    (traces / f"{ts.date().isoformat()}.jsonl").write_text(json.dumps(rec) + "\n")


def _bind(root: Path, pending=(), declined=()) -> None:
    """Point the module at a tmp tree. Never data/personas/ — danny_park is git-tracked."""
    tr.persona_data_dir = lambda persona=None: root
    tr._pending_and_declined = lambda persona: (list(pending), list(declined))


def _run() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="turn_referent_test_"))
    real_dir, real_ledgers = tr.persona_data_dir, tr._pending_and_declined
    try:
        # --- 1. fail open -----------------------------------------------------------
        empty = tmp / "no_traces_here"
        empty.mkdir()
        _bind(empty)
        check("a persona with no traces directory yields no block and does not raise",
              tr.context_block("p") == "")

        root = tmp / "p"
        root.mkdir()
        _bind(root)

        _write_trace(root, ts=datetime.now(),
                     user_input="Marcus Delgado is in there twice, merge those two contacts.")
        path = next((root / "traces").glob("*.jsonl"))
        path.write_text(path.read_text() + '{"trace_id": "half\n')
        check("a torn final line falls back to the last complete record",
              "merge those two contacts" in tr.context_block("p"))

        _write_trace(root, ts=datetime.now(), user_input="hello")
        path = next((root / "traces").glob("*.jsonl"))
        rec = json.loads(path.read_text())
        rec["ts"] = "not a date"
        path.write_text(json.dumps(rec) + "\n")
        check("an unparseable timestamp is treated as stale, not as 'just now'",
              tr.context_block("p") == "")

        # A pronoun points at the exchange the user is still in. Offering a referent from
        # hours ago would invent the failure this block exists to prevent.
        _write_trace(root, ts=datetime.now() - timedelta(hours=5),
                     user_input="merge those two contacts")
        check("a turn older than the window is not offered as a referent",
              tr.context_block("p") == "")

        _write_trace(root, ts=datetime.now(), user_input="merge those two contacts")
        tr.persona_data_dir = lambda persona=None: root
        tr._pending_and_declined = real_ledgers      # the real one, with confirm broken

        class _Boom:
            @staticmethod
            def pending(p):
                raise RuntimeError("ledger on fire")

            @staticmethod
            def declined(w, p):
                raise RuntimeError("ledger on fire")

        sys.modules["tools.confirm"] = _Boom
        try:
            check("confirm ledgers raising does not take the block down",
                  "merge those two contacts" in tr.context_block("p"))
        finally:
            del sys.modules["tools.confirm"]

        # --- 2. what happened beats what was said -----------------------------------
        # 2026-08-29: the reply said sent, the card said waiting, the user then declined.
        _bind(root, pending=["Send an email to Iva Diamond about a call"])
        _write_trace(root, ts=datetime.now(),
                     user_input="email Iva about setting up a call",
                     synth_response="That's sent to Iva.",
                     tool_calls=[{"name": "send_email",
                                  "args": {"to": "iva@example.com", "subject": "A call"},
                                  "ok": True}])
        block = tr.context_block("p")
        check("a pending action is named as still waiting, contradicting a reply that "
              "claims it was sent",
              "STILL WAITING" in block and "not done" in block, block)
        check("the block states outright that it overrides the reply text",
              "THESE lines are correct" in block, block)

        _bind(root, declined=["Send an email to Iva Diamond"])
        _write_trace(root, ts=datetime.now(), user_input="now set it back to Iva")
        block = tr.context_block("p")
        check("a declined action is named as refused, and says not to revive it",
              "REFUSED by the user" in block and "reviving it" in block, block)

        # --- 3. which tool calls count ----------------------------------------------
        _bind(root)
        _write_trace(root, ts=datetime.now(),
                     user_input="Marcus Delgado is in there twice, merge those two contacts.",
                     synth_response="Done — the duplicates are merged into one contact.",
                     tool_calls=[{"name": "merge_contacts",
                                  "args": {"primary_id": "c_88", "duplicate_id": "c_91"},
                                  "ok": True}])
        block = tr.context_block("p")
        check("the action is reported with the object it acted on",
              "merge_contacts" in block and "c_88" in block and "completed" in block, block)

        _write_trace(root, ts=datetime.now(), user_input="what did I eat today",
                     tool_calls=[{"name": "list_obligations", "args": {}, "ok": True},
                                 {"name": "search_memory", "args": {"query": "food"},
                                  "ok": True}])
        block = tr.context_block("p")
        check("reads are not reported as the action — pointing the referent at a lookup "
              "is the mistake core/trace.py:107 documents for is_grounded()",
              "search_memory" not in block and "list_obligations" not in block
              and "nothing — no action was taken" in block, block)

        _write_trace(root, ts=datetime.now(), user_input="send it",
                     tool_calls=[{"name": "send_email", "args": {"to": "iva"}, "ok": True}])
        check("classification comes from core/actions.py, not a local prefix list",
              "send_email" in tr.context_block("p"))

        _write_trace(root, ts=datetime.now(), user_input="do the thing",
                     tool_calls=[{"name": "unmerge_contacts", "args": {"contact_id": "c_91"},
                                  "ok": True}])
        check("an unrecognised tool is included rather than dropped — omitting a real "
              "action costs the referent, a surplus line costs tokens",
              "unmerge_contacts" in tr.context_block("p"))

        _write_trace(root, ts=datetime.now(), user_input="book the table",
                     tool_calls=[{"name": "write_calendar_event", "args": {"title": "Fumbally"},
                                  "ok": False}])
        block = tr.context_block("p")
        check("a failed call is not reported as completed",
              "FAILED" in block and "completed" not in block, block)

        # core/actions.py:_failed — ok=True with an "Error:" body is still a failure, and
        # two readers of the same trace must not disagree about whether the action worked.
        _write_trace(root, ts=datetime.now(), user_input="merge them",
                     tool_calls=[{"name": "merge_contacts", "args": {"primary_id": "c_1"},
                                  "ok": True,
                                  "result_preview": "Error: no such contact"}])
        block = tr.context_block("p")
        check("a tool returning an Error string is not reported as completed either",
              "FAILED" in block and "completed" not in block, block)

        _write_trace(root, ts=datetime.now(), is_proactive=True,
                     user_input="[morning check-in]",
                     tool_calls=[{"name": "write_log", "args": {"kind": "morning"},
                                  "ok": True}])
        block = tr.context_block("p")
        check("a scheduled run does not claim the user spoke",
              "scheduled run" in block and "The user said" not in block, block)

        _write_trace(root, ts=datetime.now(), user_input="log it",
                     tool_calls=[{"name": "write_log",
                                  "args": {"content": {"body": "x" * 5000}, "kind": "food"},
                                  "ok": True}])
        block = tr.context_block("p")
        check("a long payload is summarised to its object, never pasted into the prompt",
              "xxxx" not in block and "kind=food" in block, block[:200])
    finally:
        tr.persona_data_dir, tr._pending_and_declined = real_dir, real_ledgers
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    _run()
    passed = sum(1 for _, ok, _ in _results if ok)
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if not ok and detail:
            print(f"        {detail}")
    total = len(_results)
    print(f"\n{passed} passed, {total - passed} failed, {total} total")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
