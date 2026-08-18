"""
tests/test_obligation_due_sort.py — DB-0814-04: a vague due date must not sort below
an obligation with no due date at all.

The defect this pins: `context_block()` sorted on `str(due or "9999")`, and "next
week" sorts lexically *after* "9999" because letters exceed digits in ASCII. With
`_CONTEXT_MAX = 6`, an obligation the user had given a soft deadline to was dropped
from session context before every undated one — the exact failure the store exists
to prevent. Run it, do not read it: the ordering is the whole assertion.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.obligations as O  # noqa: E402

_results = []


def check(name):
    def deco(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except Exception as exc:  # noqa: BLE001
            _results.append((name, False, f"{type(exc).__name__}: {exc}"))
        return fn
    return deco


def _ob(what: str, due=None) -> dict:
    it = {"id": "ob_" + what.replace(" ", "_"), "what": what, "status": "open"}
    if due is not None:
        it["due"] = due
    return it


def _order(items: list[dict]) -> list[str]:
    return [it["what"] for it in sorted(items, key=O._due_sort_key)]


@check("dated, then vague, then undated — the old key put vague last of all")
def _():
    got = _order([
        _ob("undated"),
        _ob("vague", "next week"),
        _ob("far", "2026-09-01"),
        _ob("soon", "2026-08-20"),
    ])
    assert got == ["soon", "far", "vague", "undated"], got


@check("the pre-fix lexical key really did rank a vague date below an undated one")
def _():
    # Guards against the fix being reverted to something that only looks equivalent.
    items = [_ob("vague", "next week"), _ob("undated")]
    old = [it["what"] for it in sorted(items, key=lambda i: str(i.get("due") or "9999"))]
    assert old == ["undated", "vague"], old
    assert _order(items) == ["vague", "undated"]


@check("a vague-dated obligation survives _CONTEXT_MAX truncation past undated ones")
def _(_ctx=[]):
    items = [_ob(f"undated {n}") for n in range(O._CONTEXT_MAX)] + [_ob("vague", "next week")]
    orig_load = O._load
    O._load = lambda persona=None: list(items)
    try:
        block = O.context_block("t")
    finally:
        O._load = orig_load
    assert "vague" in block, block
    assert block.count("\n- ") == O._CONTEXT_MAX + 1, block  # 6 shown + the "+N more" line


@check("empty, whitespace and non-string due values bucket as 'nothing stated'")
def _():
    for due in (None, "", "   ", 0):
        assert O._due_sort_key(_ob("x", due))[0] == 2, due


@check("ISO dates still sort chronologically among themselves")
def _():
    got = _order([_ob("c", "2026-12-01"), _ob("a", "2026-08-19"), _ob("b", "2026-09-30")])
    assert got == ["a", "b", "c"], got


if __name__ == "__main__":
    for n, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {n}")
        if not ok:
            print(f"        {detail}")
    failed = sum(1 for _, ok, _ in _results if not ok)
    print(f"\n{len(_results)-failed} passed, {failed} failed, {len(_results)} total")
    sys.exit(1 if failed else 0)
