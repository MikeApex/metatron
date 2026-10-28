"""
tests/test_spend_guard_multiprocess.py — the spend meter's day file across processes
(archive/plans/multi_user_accounts_plan_2026-10-26.md § 4.6, § 6.1.8).

The server and every user's scheduler write the same day file. Under the old
thread-only lock two processes interleave read-modify-write and an increment is lost —
the guard under-counts, and an under-counting guard is read as safety.

1. Two processes increment concurrently: nothing is lost (calls and usd both exact).
2. A reader polling without the lock (check_before_session's shape) never sees the day
   go backwards — the write is atomic, so a torn file can never parse as a blank day.
3. No temp files are left behind.
4. Control, reported not asserted: the same run under the old thread-only lock, to show
   this test can see a lost update at all.

No model is called; estimate_usd is stubbed and the state dir is a temp dir.

Run: python3 tests/test_spend_guard_multiprocess.py
"""

import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

REPO = Path(__file__).parent.parent
N = 400

_WRITER = textwrap.dedent("""
    import sys
    sys.path.insert(0, {repo!r})
    from pathlib import Path
    from core import spend_guard as sg
    sg._STATE_DIR = Path({state!r})
    sg._config = {{"enabled": True}}
    sg.estimate_usd = lambda *a, **k: 0.001
    if {old_lock}:
        sg._state_lock = lambda: sg._lock          # the pre-Stage-3 thread-only lock
    for _ in range({n}):
        sg.record_tokens("m", 10, 1)
""")

_READER = textwrap.dedent("""
    import sys, time
    sys.path.insert(0, {repo!r})
    from pathlib import Path
    from core import spend_guard as sg
    sg._STATE_DIR = Path({state!r})
    last, backwards, reads = 0, 0, 0
    end = time.time() + 30
    while time.time() < end:
        calls = sg._read_state().get("calls", 0)
        reads += 1
        if calls < last:
            backwards += 1
        last = max(last, calls)
        if last >= {target}:
            break
    print(backwards, reads, flush=True)
""")

_results: list[tuple[bool, str]] = []


def check(label: str, condition: bool) -> None:
    _results.append((condition, label))
    print(f"  {'PASS' if condition else 'FAIL'}  {label}")


def _run(state: Path, old_lock: bool, with_reader: bool):
    code = _WRITER.format(repo=str(REPO), state=str(state), n=N, old_lock=old_lock)
    reader = None
    if with_reader:
        reader = subprocess.Popen(
            [sys.executable, "-c",
             _READER.format(repo=str(REPO), state=str(state), target=2 * N)],
            stdout=subprocess.PIPE, text=True)
    writers = [subprocess.Popen([sys.executable, "-c", code]) for _ in range(2)]
    for w in writers:
        w.wait(timeout=120)
    reader_out = reader.communicate(timeout=60)[0].split() if reader else None
    day = next(state.glob("spend_*.json"))
    return json.loads(day.read_text()), reader_out


def main() -> int:
    print(f"Two processes × {N} increments")
    with tempfile.TemporaryDirectory() as td:
        state, reader = _run(Path(td), old_lock=False, with_reader=True)
        check(f"no increment lost: calls == {2 * N} (got {state['calls']})",
              state["calls"] == 2 * N)
        check(f"usd exact: {2 * N * 0.001:.3f} (got {state['usd']:.3f})",
              round(state["usd"], 6) == round(2 * N * 0.001, 6))
        backwards, reads = int(reader[0]), int(reader[1])
        check(f"an unlocked reader never saw the day go backwards ({reads} reads)",
              backwards == 0 and reads > 0)
        leftovers = [p.name for p in Path(td).iterdir() if p.name.startswith(".spend.")]
        check("no temp files left behind", not leftovers)

    with tempfile.TemporaryDirectory() as td:
        state, _ = _run(Path(td), old_lock=True, with_reader=False)
        lost = 2 * N - state["calls"]
        print(f"  INFO  control, old thread-only lock: {lost} of {2 * N} increments lost")

    failed = [label for ok, label in _results if not ok]
    print(f"\n{len(_results) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
