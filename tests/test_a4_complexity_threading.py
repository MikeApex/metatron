#!/usr/bin/env python3
"""
Offline verification that `tests/run_a4_safety.py --complexity` actually reaches the
router — no live model calls, no spend.

WHY THIS EXISTS
---------------
`[DB-0808-17]`: the A4 clinical hard-fails had only ever run on the deep model, while
Flash-Lite served the large majority of Mental Wellbeing / Physical Health turns. The
fix was a `--complexity` flag on the runner. A flag that is *present* but silently
dropped somewhere between argparse and `resolve_model()` would leave the gap exactly
where it was while looking closed — which is the same failure mode as the gap itself.

So this asserts the wiring, not the safety behaviour:

  1. `run_one()` passes `complexity` through to `_run_single_agent()`.
  2. `resolve_model(agent, complexity="quick")` really does select `quick_override`
     for a non-sensitive agent — i.e. the flag lands on a different model.
  3. Sensitivity still beats speed: a `local: true` agent ignores complexity.
  4. `--complexity` with `--suite pipeline` is refused, not silently ignored.

Run:  python tests/test_a4_complexity_threading.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}" + (f" — {detail}" if detail else ""))
    if not condition:
        FAILURES.append(label)


# ---------------------------------------------------------------------------
# 1. run_one() threads complexity into _run_single_agent()
# ---------------------------------------------------------------------------
def test_run_one_threads_complexity() -> None:
    print("\n1. run_one() -> _run_single_agent(complexity=...)")
    import importlib.util

    import core.orchestrator as orch

    # Loaded by path, not import: tests/ has no __init__.py and the filename
    # starts with a digit-free but hyphen-free name only by luck — path loading
    # is the stable way in either case.
    spec = importlib.util.spec_from_file_location(
        "run_a4_safety_mod", ROOT / "tests" / "run_a4_safety.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    seen: dict = {}
    original = orch._run_single_agent

    def fake(agent_name, user_input, persona=None, provider=None,
             model_override=None, complexity=None, history=None, bare=False):
        seen["agent"] = agent_name
        seen["complexity"] = complexity
        return "CLINICAL_CONCERN MUST_SURFACE stub output"

    orch._run_single_agent = fake  # type: ignore[assignment]
    try:
        scenario = {"id": "T-1", "name": "threading probe",
                    "agent": "mental_wellbeing", "prompt": "stub",
                    "token_require": []}
        mod.run_one(scenario, "sarah_chen", None, "quick")
        check("complexity='quick' arrives at _run_single_agent",
              seen.get("complexity") == "quick", f"got {seen.get('complexity')!r}")

        seen.clear()
        mod.run_one(scenario, "sarah_chen", None, None)
        check("complexity=None stays None (routing default preserved)",
              seen.get("complexity") is None, f"got {seen.get('complexity')!r}")
    finally:
        orch._run_single_agent = original  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# 2 & 3. resolve_model() honours complexity, and sensitivity beats speed
# ---------------------------------------------------------------------------
def test_router_honours_complexity() -> None:
    print("\n2. resolve_model() selects a different model for complexity='quick'")
    from core.router import resolve_model, _load_routing

    cfg = _load_routing()
    quick_model = cfg.get("quick_override", {}).get("model")
    agents = cfg.get("agents", {})

    non_sensitive = next(
        (a for a in ("mental_wellbeing", "physical_health", "synthesizer", "coordinator")
         if a in agents and not agents[a].get("local")), None)

    if not non_sensitive:
        check("a non-sensitive agent exists in the active routing config", False,
              "all agents are local: true — cannot exercise quick_override here")
        return

    default = resolve_model(non_sensitive)
    quick = resolve_model(non_sensitive, complexity="quick")
    check(f"{non_sensitive}: quick resolves to quick_override model",
          quick.model == quick_model, f"{default.model} -> {quick.model}")
    check(f"{non_sensitive}: quick actually differs from the default tier",
          quick.model != default.model, f"{default.model} vs {quick.model}")

    print("\n3. sensitivity beats speed — local: true ignores complexity")
    local_agent = next((a for a, c in agents.items() if c.get("local")), None)
    if not local_agent:
        print("  [SKIP] no local: true agent in the active routing config "
              "(cloud mode) — the rule is asserted in core/router.py:81")
        return
    if not cfg.get("local_enabled", False):
        print(f"  [SKIP] local_enabled is false — resolve_model('{local_agent}') "
              "fails closed by design rather than returning a model")
        return
    check(f"{local_agent}: complexity='quick' does not leave Ollama",
          resolve_model(local_agent, complexity="quick").provider == "ollama")


# ---------------------------------------------------------------------------
# 4. --complexity with --suite pipeline is refused
# ---------------------------------------------------------------------------
def test_pipeline_combination_refused() -> None:
    print("\n4. --complexity + --suite pipeline is refused, not ignored")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tests" / "run_a4_safety.py"),
         "--persona", "sarah_chen", "--suite", "pipeline", "--complexity", "quick"],
        capture_output=True, text=True, cwd=str(ROOT), timeout=120)
    check("exits non-zero", proc.returncode == 2, f"rc={proc.returncode}")
    check("explains why on stderr", "REFUSED" in proc.stderr,
          proc.stderr.strip().splitlines()[0] if proc.stderr.strip() else "(no stderr)")


def main() -> int:
    print("A4 --complexity threading check (offline — no model calls)")
    test_run_one_threads_complexity()
    test_router_honours_complexity()
    test_pipeline_combination_refused()
    print()
    if FAILURES:
        print(f"RESULT: FAIL — {len(FAILURES)} check(s) failed:")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("RESULT: PASS — the flag reaches the router and the invalid combination is refused.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
