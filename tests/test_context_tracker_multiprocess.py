"""
tests/test_context_tracker_multiprocess.py — the context tracker across processes.

Review 2026-11-05, finding 22. The server (a user turn's asked-state bookkeeping, the
Synthesizer's write_context_tracker) and each persona's scheduler (close_scheduled_run at the
end of every job) read-modify-write the same `context.json`. It was written with
open("w") + json.dump and no lock: a reader in the other process could see it empty or
half-written, and a writer that read it torn wrote back nothing but its own key — clinical
threads included in what was erased.

1. An unlocked reader polling the file (read_context_tracker's shape) never sees it unparseable.
2. No update is lost: two processes × N asks of the same question end at ask_count == 2N.
3. The clinical thread seeded before the race is still on the tracker after it.
4. No temp files are left behind.

No model is called; the persona directory is a temp dir patched into tools.context_tracker.

Run: python3 tests/test_context_tracker_multiprocess.py
"""

import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

REPO = Path(__file__).parent.parent
N = 150
QUESTION = "Did the GP call back?"
FLAG = "CLINICAL_CONCERN: SUICIDAL_IDEATION"

_WRITER = textwrap.dedent("""
    import sys
    sys.path.insert(0, {repo!r})
    from pathlib import Path
    import tools.context_tracker as CT
    CT.persona_data_dir = lambda persona=None: Path({root!r})
    for i in range({n}):
        CT.record_asked_questions([{question!r}], kind="probe")
        CT.close_scheduled_run("probe")
""")

_READER = textwrap.dedent("""
    import json, sys, time
    from pathlib import Path
    path = Path({root!r}) / "context.json"
    torn, reads = 0, 0
    end = time.time() + 60
    while time.time() < end:
        try:
            text = path.read_text()
        except FileNotFoundError:
            torn += 1          # the tracker must never be absent once it exists
            continue
        reads += 1
        try:
            json.loads(text)
        except ValueError:
            torn += 1
        if Path({done!r}).exists():
            break
    print(torn, reads, flush=True)
""")

_results: list[tuple[bool, str]] = []


def check(label: str, condition: bool) -> None:
    _results.append((condition, label))
    print(f"  {'PASS' if condition else 'FAIL'}  {label}")


def main() -> int:
    print(f"Two processes × {N} read-modify-writes, one unlocked reader")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        tracker = root / "context.json"
        tracker.write_text(json.dumps({"open_threads": [], "clinical_threads": [
            {"flag": FLAG, "status": "watch", "note": "n", "raised": "2026-11-01"}]}))
        done = root / "done"

        reader = subprocess.Popen(
            [sys.executable, "-c", _READER.format(root=str(root), done=str(done))],
            stdout=subprocess.PIPE, text=True)
        code = _WRITER.format(repo=str(REPO), root=str(root), n=N, question=QUESTION)
        writers = [subprocess.Popen([sys.executable, "-c", code],
                                    stderr=subprocess.DEVNULL) for _ in range(2)]
        for w in writers:
            w.wait(timeout=300)
        done.write_text("")
        torn, reads = (int(x) for x in reader.communicate(timeout=120)[0].split())

        check(f"an unlocked reader never saw a torn or absent tracker "
              f"({torn} of {reads} reads torn)", torn == 0 and reads > 0)

        live = json.loads(tracker.read_text())
        asked = [q for q in live.get("asked_questions") or [] if q.get("text") == QUESTION]
        count = asked[0].get("ask_count") if asked else 0
        check(f"no update lost: ask_count == {2 * N} (got {count})", count == 2 * N)
        flags = [t.get("flag") for t in live.get("clinical_threads") or []]
        check("the clinical thread survived the race", FLAG in flags)
        leftovers = [p.name for p in root.iterdir() if p.name.endswith(".tmp")]
        check("no temp files left behind", not leftovers)

    failed = [label for ok, label in _results if not ok]
    print(f"\n{len(_results) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
