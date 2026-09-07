#!/usr/bin/env python3
"""
scripts/check_confirm_executors.py — every gated action can actually be carried out.

A confirmation-gated tool is split across two registries that nothing compares:
`confirm.request(action, ...)` inside the tool raises the approval card, and
`confirm._EXECUTORS` is what the server consults when the user approves it. Ship
one without the other and the failure surfaces only in production, *after* the
user has approved — as "Nothing here knows how to carry out 'X'".

That is not hypothetical. `send_calendar_invite` shipped on 2026-09-07 with 16/16
of its own tests passing, because those tests drove `consume()` directly and
nothing exercised `execute()`. Mike approved a real invitation to a real person
and it silently did nothing.

Same shape as the `get_weather` grant/documentation split that `check_agent_tools.py`
exists for: two halves, a single commit, and nothing re-checking them against each
other. A rule you have to remember is not a control.

Stdlib only, zero model tokens. Exit 1 on a gated action with no executor.

Run: python3 scripts/check_confirm_executors.py
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"

# Raised by code on the user's behalf rather than by a tool the model calls, so
# the action name never appears in a request() call this scanner can see. Keep
# this list short and justified — every entry is a check that stops running.
# Empty on purpose. `add_zone` was listed here on the first draft, wrongly: it IS
# raised by a literal request() in tools/location.py, and the scanner was simply
# missing that file, which imports confirm as a module rather than by name. An
# exemption that covers a scanner blind spot is worse than no check at all — it
# silences the one finding that would have revealed the blind spot.
_NOT_MODEL_RAISED: set[str] = set()


def _imports_confirm_request(tree: ast.AST) -> bool:
    """True if this module pulls `request` in from tools.confirm.

    The import is the discriminator, and it has to be: `requests.request("REPORT", ...)`
    is a real CalDAV call in tools/caldav.py, and a bare name check reported it as a
    gated action called "REPORT" on the first run of this script.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").endswith("confirm"):
            if any(a.name == "request" for a in node.names):
                return True
        # `from tools import confirm as _confirm` — the style tools/location.py uses.
        if isinstance(node, ast.Import):
            if any((a.name or "").endswith("confirm") for a in node.names):
                return True
        if isinstance(node, ast.ImportFrom) and (node.module or "") == "tools":
            if any(a.name == "confirm" for a in node.names):
                return True
    return False


def _requested_actions() -> dict[str, set[str]]:
    """Every literal action name passed to confirm.request(), by file."""
    found: dict[str, set[str]] = {}
    for path in sorted(TOOLS.glob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        if not _imports_confirm_request(tree):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            # Both call styles are used: bare `request(...)` after a from-import, and
            # `_confirm.request(...)` after a module import. Accept both, but reject an
            # attribute call rooted at `requests` — `requests.request("REPORT", ...)` is
            # a real CalDAV call and the first version of this script reported it as a
            # gated action named "REPORT".
            if isinstance(fn, ast.Name):
                if fn.id != "request":
                    continue
            elif isinstance(fn, ast.Attribute):
                root = fn.value
                root_name = root.id if isinstance(root, ast.Name) else ""
                if fn.attr != "request" or root_name.startswith("requests"):
                    continue
            else:
                continue
            if not node.args:
                continue
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                found.setdefault(first.value, set()).add(path.name)
    return found


def main() -> int:
    sys.path.insert(0, str(ROOT))
    from tools.confirm import _EXECUTORS

    requested = _requested_actions()
    executors = set(_EXECUTORS)

    missing = {a: f for a, f in requested.items() if a not in executors}
    orphans = executors - set(requested) - _NOT_MODEL_RAISED

    for action, files in sorted(missing.items()):
        print(f"MISSING EXECUTOR: '{action}' is gated in {', '.join(sorted(files))} "
              f"but absent from confirm._EXECUTORS — the user's approval will come "
              f"back \"Nothing here knows how to carry out '{action}'\".")

    # A warning, not a failure: an executor with no visible request() may be raised
    # by Python rather than by a model, which is legitimate (see _NOT_MODEL_RAISED).
    for action in sorted(orphans):
        print(f"note: executor '{action}' has no literal confirm.request() in tools/ — "
              f"either it is raised by code (add it to _NOT_MODEL_RAISED with the "
              f"reason) or the grant is dead.")

    if missing:
        print(f"\n{len(missing)} gated action(s) cannot be carried out.")
        return 1
    print(f"check_confirm_executors: {len(requested)} gated actions, all executable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
