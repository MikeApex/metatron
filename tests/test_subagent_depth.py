"""
tests/test_subagent_depth.py — run_subagent's delegation depth is per request, not per process
(Stage 3 review S2, 2026-10-28).

Until 2026-10-28 the depth lived in os.environ["_SUBAGENT_DEPTH"] — shared by every thread
in the server. With two users served at once, one user's nested specialist (depth 2) made the
other user's Coordinator refuse to delegate ("cannot be called at delegation depth 2 …
Perform this task directly"), and a `finally` reset the other request's depth to its own.

1. The chain Coordinator → category agent → specialist is admitted; one more level refused.
2. Two concurrent requests: while A is two levels deep, B at the top delegates normally, and
   A's unwinding never changes B's depth.
3. A fire-and-forget child runs one level deeper than its caller, on its own thread.
4. Every orchestrator worker that adopts the parent's trace adopts its depth too (a cheap
   structural guard against a future fan-out site forgetting it).

run_session is stubbed — no model is called.

Run: python3 tests/test_subagent_depth.py
"""

import re
import sys
import threading
import time
from pathlib import Path
from unittest import mock

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

from core import trace as tr  # noqa: E402
from core.persona import persona_scope  # noqa: E402
from tools import subagent  # noqa: E402

_results: list[tuple[bool, str]] = []


def check(label: str, condition: bool) -> None:
    _results.append((condition, label))
    print(f"  {'PASS' if condition else 'FAIL'}  {label}")


def part_chain() -> None:
    print("The chain admits two levels and refuses a third")
    seen = []

    def fake_run_session(agent, user_input="", persona=None, complexity=None):
        seen.append((agent, tr.get_subagent_depth()))
        if agent == "logistics":           # a category agent delegating on
            return subagent.run_subagent("research_agent", "x")
        if agent == "research_agent":      # a specialist trying to go one further
            return subagent.run_subagent("finance", "x")
        return "ok"

    with persona_scope("danny_park"), \
         mock.patch("core.orchestrator.run_session", side_effect=fake_run_session):
        out = subagent.run_subagent("logistics", "x")
    check("category agent runs at depth 1, specialist at depth 2",
          seen == [("logistics", 1), ("research_agent", 2)])
    check("a third level is refused with the depth error",
          "delegation depth 2" in out)
    check("depth is back to 0 on the calling thread afterwards", tr.get_subagent_depth() == 0)


def part_concurrent() -> None:
    print("Two requests at once do not see each other's depth")
    a_deep, b_done = threading.Event(), threading.Event()
    b_result: dict = {}

    def fake_run_session(agent, user_input="", persona=None, complexity=None):
        if agent == "logistics":
            return subagent.run_subagent("research_agent", "x")
        if agent == "research_agent":          # A is now at depth 2; hold it there
            a_deep.set()
            b_done.wait(timeout=10)
            return "a-done"
        if agent == "relationships":           # B's ordinary delegation
            return f"b-ran-at-{tr.get_subagent_depth()}"
        return "ok"

    def request_a():
        with persona_scope("danny_park"):
            subagent.run_subagent("logistics", "x")

    def request_b():
        a_deep.wait(timeout=10)
        with persona_scope("maya_torres"):
            b_result["out"] = subagent.run_subagent("relationships", "x")
            b_result["after"] = tr.get_subagent_depth()
        b_done.set()

    with mock.patch("core.orchestrator.run_session", side_effect=fake_run_session):
        ta, tb = threading.Thread(target=request_a), threading.Thread(target=request_b)
        ta.start(); tb.start()
        ta.join(timeout=15); tb.join(timeout=15)
    check("B delegates normally while A is two levels deep",
          b_result.get("out") == "b-ran-at-1")
    check("B's depth is its own afterwards (0)", b_result.get("after") == 0)


def part_fire_and_forget() -> None:
    print("A fire-and-forget child runs one level deeper, on its own thread")
    got, done = [], threading.Event()

    def fake_run_session(agent, user_input="", persona=None, complexity=None):
        got.append((threading.current_thread() is not main_thread, tr.get_subagent_depth()))
        done.set()
        return "ok"

    main_thread = threading.current_thread()
    with persona_scope("danny_park"), \
         mock.patch("core.orchestrator.run_session", side_effect=fake_run_session):
        tr.set_subagent_depth(1)
        try:
            subagent.run_subagent("diarist", "log this")
            done.wait(timeout=5)
        finally:
            tr.set_subagent_depth(0)
    check("the diarist ran on another thread at depth 2", got == [(True, 2)])


def part_structural() -> None:
    print("Every worker that adopts the parent trace adopts its depth")
    src = (REPO / "core" / "orchestrator.py").read_text().splitlines()
    sites = [i for i, line in enumerate(src)
             if re.search(r"_tr\.set_trace\(_(parent|fan)_trace\)", line)]
    missing = [i + 1 for i in sites
               if not any("set_subagent_depth" in l for l in src[i:i + 3])]
    check(f"{len(sites)} fan-out workers found", len(sites) >= 5)
    check("each sets the subagent depth beside the trace", not missing)
    if missing:
        print(f"        missing at core/orchestrator.py lines {missing}")
    check("nothing in core/ or tools/ reads the old _SUBAGENT_DEPTH env var",
          not any("_SUBAGENT_DEPTH\"" in p.read_text() or "'_SUBAGENT_DEPTH'" in p.read_text()
                  for d in ("core", "tools") for p in (REPO / d).rglob("*.py")))


def main() -> int:
    part_chain()
    part_concurrent()
    part_fire_and_forget()
    part_structural()
    failed = [label for ok, label in _results if not ok]
    print(f"\n{len(_results) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
