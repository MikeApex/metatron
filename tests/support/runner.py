"""
tests/support/runner.py — the standalone check harness the Build suites share.

No pytest dependency, matching the tests/ convention: every suite here is `python3
tests/test_x.py` and exits 0 or 1. Shared so six suites cannot each evolve a
slightly different idea of what a failure looks like.
"""

from __future__ import annotations

import sys


class Suite:
    def __init__(self, title: str):
        self.title = title
        self.results: list[tuple[str, bool, str]] = []

    def check(self, name: str):
        def wrap(fn):
            try:
                fn()
                self.results.append((name, True, ""))
            except AssertionError as exc:
                self.results.append((name, False, f"assertion: {exc}"))
            except Exception as exc:
                self.results.append((name, False, f"{type(exc).__name__}: {exc}"))
            return fn
        return wrap

    def report(self) -> int:
        passed = 0
        for name, ok, detail in self.results:
            print(f"{'PASS' if ok else 'FAIL'}  {name}"
                  + (f"  — {detail}" if detail else ""))
            passed += ok
        print(f"\n{passed}/{len(self.results)} passed")
        return 0 if passed == len(self.results) else 1

    def exit(self) -> None:
        sys.exit(self.report())


def hit(defects: list[str], fragment: str) -> bool:
    """True when some defect names `fragment`. Substring, deliberately —
    asserting an exact message would make every wording improvement a test
    failure, and the wording is where the reasoning lives."""
    return any(fragment in str(d) for d in defects)


def only(defects: list[str], fragment: str) -> bool:
    """Every defect names `fragment` — 'it fails, and ONLY on that ground'."""
    return bool(defects) and all(fragment in str(d) for d in defects)
