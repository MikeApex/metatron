"""
tests/support/live_gate.py — a script that spends money must be started on purpose.

Ten scripts under tests/ call live models (or write to a live calendar) when run, and
sit beside ~80 offline suites with the same `python tests/<name>.py` shape. On
2026-10-24 a Claude Code session looped over every tests/*.py file that mentioned the
calendar to run "the existing suites", and started run_coord_model_probe.py with it:
~9 minutes, 62 Vertex calls, ~$0.72, stopped by hand. Nothing ran away — the script did
exactly its job, at an ordinary rate — so no spend threshold could tell it from a
deliberate run. The only difference was intent, and intent is what this asks for.

THE RULE: from an interactive terminal, nothing changes — every documented command
works as written. From anything non-interactive (an agent's shell, a loop, a pipe into
stdin), the script refuses with exit 2 unless METATRON_LIVE=1 is set. Exit 2, not 0,
so a sweep reports it as not-run rather than passed. Offline modes a script already
has (--dry-run, --report-only) are never gated.

Retires nothing and adds no standing process: it is a check at script start.
"""
import os
import sys


def require_live(offline_flags: tuple[str, ...] = ()) -> None:
    """Call first thing under `if __name__ == "__main__":` in a script that spends."""
    if any(flag in sys.argv[1:] for flag in offline_flags):
        return
    if os.environ.get("METATRON_LIVE") == "1" or sys.stdin.isatty():
        return
    name = os.path.basename(sys.argv[0])
    print(
        f"{name}: NOT RUN — this script calls live models (or a live service) and "
        f"spends real money.\n"
        f"Started non-interactively, so it needs an explicit go: "
        f"METATRON_LIVE=1 python3 tests/{name} ..."
        + (f"\nOffline mode needs no go: {' / '.join(offline_flags)}" if offline_flags else ""),
        file=sys.stderr,
    )
    sys.exit(2)
