#!/usr/bin/env python3
"""
Assert every scheduled function job actually RESOLVES. Check 12 of qa_sweep.sh.

THE FAILURE THIS CATCHES, AND WHY NOTHING ELSE DOES.

`_DEFAULT_JOBS` in core/scheduler.py names each maintenance job by a DOTTED
STRING — "core.build.tick.build_tick". `fire_function()` resolves that string at
fire time inside a `try`, prints the failure to the scheduler log, and moves on.
So a job whose module was renamed or deleted does not crash anything: it just
stops happening, every thirty minutes, for as long as nobody reads the log.

py_compile cannot see it, because a string is a valid string. `grep` cannot see
it, because the module name only exists as text. The REPAIR counter going dark
is exactly this shape, and the v4 rebuild moves `build_tick` from one module to
another — which is precisely when this check earns its place (plan section 10,
finding 4).

WHAT IT DOES: imports every module named in `_DEFAULT_JOBS` and in every
persona's `scheduler.yaml`, and looks the attribute up. It does NOT call
anything — a maintenance job that ran on every sweep would be a sweep with side
effects, and several of these write files.

Stdlib only. Zero model tokens. Exit 1 on any dangling path.

Usage:
    python3 scripts/check_scheduler_functions.py
    python3 scripts/check_scheduler_functions.py --verbose
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _yaml_function_paths() -> list[tuple[str, str]]:
    """(where, dotted path) for every `function:` in a tracked scheduler.yaml."""
    import yaml
    out: list[tuple[str, str]] = []
    candidates = [ROOT / "config" / "modules" / "scheduler.yaml"]
    candidates += sorted((ROOT / "config" / "personas").glob("*/scheduler.yaml"))
    candidates += sorted((ROOT / "config" / "templates").glob("scheduler.yaml"))
    for path in candidates:
        if not path.exists():
            continue
        try:
            cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            out.append((str(path.relative_to(ROOT)), f"__unreadable__:{exc}"))
            continue
        for name, entry in (cfg.get("schedules") or {}).items():
            if isinstance(entry, dict) and entry.get("function"):
                out.append((f"{path.relative_to(ROOT)}:{name}",
                            str(entry["function"])))
    return out


def _default_job_paths() -> list[tuple[str, str]]:
    from core.scheduler import _DEFAULT_JOBS
    return [(f"_DEFAULT_JOBS:{name}", str(entry["function"]))
            for name, entry in _DEFAULT_JOBS.items()
            if isinstance(entry, dict) and entry.get("function")]


def resolve(dotted: str) -> str:
    """"" when the path resolves to a callable, else the reason it does not."""
    if dotted.startswith("__unreadable__:"):
        return dotted.split(":", 1)[1]
    if "." not in dotted:
        return f"{dotted!r} is not a dotted path"
    module_path, fn_name = dotted.rsplit(".", 1)
    try:
        module = importlib.import_module(module_path)
    except Exception as exc:
        return f"cannot import {module_path!r}: {type(exc).__name__}: {exc}"
    fn = getattr(module, fn_name, None)
    if fn is None:
        return f"{module_path!r} has no attribute {fn_name!r}"
    if not callable(fn):
        return f"{dotted!r} is not callable"
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verbose", action="store_true",
                    help="print every path checked, not only the failures")
    args = ap.parse_args()

    try:
        entries = _default_job_paths() + _yaml_function_paths()
    except Exception as exc:
        print(f"  ! could not read the schedule definitions: {exc}")
        return 1

    findings: list[str] = []
    for where, dotted in entries:
        reason = resolve(dotted)
        if reason:
            findings.append(
                f"{where} -> {dotted} — {reason}. fire_function() swallows this "
                "every 30 minutes; the job simply stops happening")
        elif args.verbose:
            print(f"  ok  {where} -> {dotted}")

    for finding in findings:
        print(f"  ! {finding}")
    print(f"\nscheduler-functions: {len(findings)} finding(s) — "
          f"{len(entries)} function job(s) checked.")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
