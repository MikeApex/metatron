#!/usr/bin/env python3
"""
Acceptance test for the persona-file scan in `scripts/check_agent_tools.py`
(`[DB-0810-03]`). Read-only and offline — the guard makes no model calls and
writes nothing, so this costs nothing to run.

WHY A FIXTURE AND NOT THE REAL FILES
------------------------------------
The defect this closes is real and lives in `config/personas/mike/`: commit
`6913ad7` moved the evening ritual — which instructs a `write_log` call — out of
`config/agents/synthesizer.md`, and the guard's `write_log` finding vanished
without the grant ever being added. But `config/personas/mike.md` and
`config/personas/mike/` are gitignored and VM-only (`.gitignore:134-135`), so no
Mac checkout or worktree can see them, and the synthetic personas that *are*
present name no tools at all. Running the guard here and getting a clean report
therefore proves nothing — which is precisely the failure mode under test.

So this builds a throwaway persona tree that reproduces the shape of the real one
and points the guard at it with `--personas-root`. Four assertions:

  1. A tool named in a persona subject file is reported (class 2) against the
     agent that loads persona text, with the persona file named in the finding.
  2. The same run with `--no-personas` does NOT report it — i.e. the assertion
     above is testing the new code path and not something incidental.
  3. An empty persona root prints the zero-files warning rather than "None.",
     because a silent zero-file scan is the original defect wearing a clean shirt.
  4. `synthesizer` genuinely lacks the `write_log` grant in both routing files,
     so the finding the guard now surfaces is a live defect, not a stale example.

Run:  python3 tests/test_check_agent_tools_personas.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUARD = ROOT / "scripts" / "check_agent_tools.py"

FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if condition else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
    if not condition:
        FAILURES.append(label)


def run_guard(*extra: str) -> str:
    proc = subprocess.run([sys.executable, str(GUARD), *extra],
                          capture_output=True, text=True, cwd=str(ROOT), timeout=300)
    return proc.stdout + proc.stderr


def build_fixture(tmp: Path) -> Path:
    """A persona tree shaped like the real one, including the file that caused this."""
    root = tmp / "personas"
    (root / "fixture_user").mkdir(parents=True)
    (root / "fixture_user.md").write_text(
        "# Fixture user\n\nA synthetic persona used only by this test.\n")
    # The real shape: a subject file instructing a tool call in live prose.
    (root / "fixture_user" / "evening_ritual.md").write_text(
        "# Evening ritual\n\n"
        "At the close of the day, walk the virtue review, then call `write_log` to\n"
        "record the result. Use `read_log` to check what was recorded yesterday.\n")
    # goals.yaml must be ignored — data, not instruction prose.
    (root / "fixture_user" / "goals.yaml").write_text("goals:\n  - id: fake_goal\n")
    return root


def main() -> int:
    print("Persona-file scan acceptance test (offline, read-only)")

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        fixture = build_fixture(tmp)

        print("\n1. a tool named in a persona subject file is reported")
        out = run_guard("--personas-root", str(fixture), "--quiet")
        check("write_log surfaces as a finding",
              "`write_log`" in out,
              "not found in guard output" if "`write_log`" not in out else "")
        check("the finding names the persona file, not an agent file",
              "evening_ritual.md" in out)
        check("it is attributed to synthesizer",
              "[synthesizer]" in out)
        check("both routing files are reported",
              out.count("evening_ritual.md") >= 2, "expected a cloud and a local row")
        check("goals.yaml is not scanned as instruction prose",
              "goals.yaml" not in out)

        print("\n2. --no-personas does not report it (the path under test is the new one)")
        out_off = run_guard("--personas-root", str(fixture), "--no-personas", "--quiet")
        check("write_log finding absent when the persona scan is disabled",
              "evening_ritual.md" not in out_off)
        check("the disabled scan says so", "DISABLED by --no-personas" in out_off)

        print("\n3. an empty persona root is announced, not reported clean")
        empty = tmp / "empty_personas"
        empty.mkdir()
        out_empty = run_guard("--personas-root", str(empty), "--quiet")
        check("zero-file scan is stated loudly",
              "PERSONA SCAN READ ZERO FILES" in out_empty)
        check("it says the VM run is what closes this",
              "VM" in out_empty)

    print("\n4. a real run that cannot see `mike` says so")
    out_real = run_guard("--quiet")
    check("names the personas actually scanned", "personas seen:" in out_real)
    check("flags `mike` as absent on a checkout that cannot see him",
          "`mike` NOT among them" in out_real or "mike" in out_real.split("personas seen:")[1].split("\n")[0],
          "expected either the warning or mike present in the scanned list")

    print("\n5. the finding is a live defect: synthesizer has no write_log grant")
    import yaml  # noqa: PLC0415 — only needed for this check
    for name in ("routing.yaml", "routing_cloud.yaml"):
        cfg = yaml.safe_load((ROOT / "config" / "modules" / name).read_text()) or {}
        allowed = ((cfg.get("agents") or {}).get("synthesizer") or {}).get("allowed_tools")
        granted = allowed is None or "write_log" in allowed
        check(f"{name}: synthesizer still lacks write_log", not granted)

    print()
    if FAILURES:
        print(f"RESULT: FAIL — {len(FAILURES)} check(s) failed:")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("RESULT: PASS — persona files are scanned, attributed, and a zero-file scan is loud.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
