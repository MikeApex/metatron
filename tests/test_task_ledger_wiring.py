"""
tests/test_task_ledger_wiring.py — the orchestrator hooks the task ledger depends on, on BOTH
pipeline twins. A feature wired into one twin only is live in tests and dead in production, or
the reverse (core/orchestrator.py says so where the twins are built).

    python3 tests/test_task_ledger_wiring.py
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.orchestrator as orch  # noqa: E402
import tools.obligations as O  # noqa: E402
import tools.turn_context as TC  # noqa: E402
from core.persona import persona_data_dir, persona_scope  # noqa: E402

SRC = Path(orch.__file__).read_text()
PERSONA = "task_ledger_wiring_test"
_results: list[tuple[str, bool, str]] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    _results.append((name, bool(cond), detail))


def _body(fn_name: str) -> str:
    m = re.search(rf"\ndef {fn_name}\(.*?(?=\ndef |\Z)", SRC, re.S)
    return m.group(0) if m else ""


twins = [_body("run_pipeline_session"), _body("_run_pipeline_session_stream_inner")]
for label, body in zip(("non-streaming", "streaming"), twins):
    check(f"{label} twin binds the session kind right after resolving it",
          # `None if nudge else` (2026-10-24): a day-plan nudge binds no scheduled-run kind —
          # archive/plans/day_planner_plan_2026-10-24.md § 7.2. Still bound right after resolving.
          re.search(r"kind = (?:None if nudge else )?session_kind\(user_input, persona\)\n"
                    r"\s+_bind_turn_kind\(kind, persona\)", body) is not None)
    check(f"{label} twin builds the task hint and puts it in the Synthesizer input",
          "task_hint = _task_hint_block(user_input, is_proactive, history, persona)" in body
          and '+ (f"\\n\\n{task_hint}" if task_hint else "")' in body)
    check(f"{label} twin closes the turn through _close_turn_bookkeeping",
          "_close_turn_bookkeeping(visible, user_input, is_proactive, kind)" in body)

check("_close_turn_bookkeeping stamps what the reply raised",
      "note_raised(visible)" in _body("_close_turn_bookkeeping"))

with persona_scope(PERSONA):
    d = persona_data_dir()
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    try:
        tid = O.open_task("Pay Chase credit card bill", kind="deadline").split()[1]
        note = orch._task_hint_block("I paid the Chase bill", False, [], PERSONA)
        check("a user turn reporting a task done gets a TASK NOTE naming its id",
              tid in note and note.startswith("TASK NOTE"), note)
        check("a scheduler directive never gets one",
              orch._task_hint_block("I paid the Chase bill", True, [], PERSONA) == "")
        prev = [{"role": "user", "content": "morning"},
                {"role": "assistant", "content": "Is the Chase credit card bill paid yet?"}]
        check("a bare 'yes, done' is read against the previous reply",
              tid in orch._task_hint_block("yes, done", False, prev, PERSONA))
        with TC.turn_scope(user_turn=False) as turn:
            orch._bind_turn_kind("evening_close", PERSONA)
            check("_bind_turn_kind writes the kind into the bound turn",
                  turn.get("kind") == "evening_close" and turn.get("weekly_review") is False,
                  str(turn))
        orch._bind_turn_kind("morning_brief", PERSONA)   # unbound: must not raise
        check("_bind_turn_kind with no bound turn is a no-op", True)
    finally:
        shutil.rmtree(d, ignore_errors=True)

passed = sum(1 for _, ok, _ in _results if ok)
for name, ok, detail in _results:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if detail and not ok else ""))
print(f"\n{passed} passed, {len(_results) - passed} failed, {len(_results)} total")
sys.exit(0 if passed == len(_results) else 1)
