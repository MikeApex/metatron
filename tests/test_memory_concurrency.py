"""
tests/test_memory_concurrency.py — cross-process race regression test for core/memory.py.

Reproduces the failure that took search_memory down on 2026-08-04:
`json.JSONDecodeError: Extra data` on data/personas/{p}/memory/metadata.json, caused by the
server (tools/logger.py) and the scheduler (tools/diarist.py) both calling index_entry() with
a non-atomic, unlocked read-modify-write of the index + metadata pair.

The test spawns real OS processes, not threads — the single-worker pool in core/background.py
already serialised threads within one process, which is exactly why the bug was invisible for
so long. A thread-only test would pass against the broken code.

Run:  python3 tests/test_memory_concurrency.py
Exit: 0 all pass, 1 on any failure.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

PERSONA = "memtest_concurrency"
WRITERS = 4
ENTRIES_PER_WRITER = 12


def _writer(worker_id: int) -> None:
    """One process's share of the writes. Mirrors what logger.py / diarist.py each do."""
    os.environ["METATRON_PERSONA"] = PERSONA
    from core.memory import index_entry

    for n in range(ENTRIES_PER_WRITER):
        index_entry(
            text=f"worker {worker_id} entry {n} — the quick brown fox jumps over the lazy dog",
            source="log" if worker_id % 2 else "journal",
            entry_date="2026-08-08",
        )


def main() -> int:
    from core.persona import persona_data_dir, persona_scope

    with persona_scope(PERSONA):
        mem_dir = persona_data_dir() / "memory"

    if mem_dir.exists():
        shutil.rmtree(mem_dir)

    expected = WRITERS * ENTRIES_PER_WRITER
    failures: list[str] = []

    ctx = mp.get_context("spawn")
    procs = [
        ctx.Process(target=_writer, args=(i,), daemon=False)
        for i in range(WRITERS)
    ]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=600)

    bad_exit = [p.exitcode for p in procs if p.exitcode != 0]
    if bad_exit:
        failures.append(f"writer process(es) exited non-zero: {bad_exit}")

    with persona_scope(PERSONA):
        meta_path = persona_data_dir() / "memory" / "metadata.json"

        # 1. metadata.json parses cleanly — this is the assertion that failed before the fix.
        try:
            metadata = json.loads(meta_path.read_text())
        except json.JSONDecodeError as exc:
            failures.append(f"metadata.json corrupt: {exc}")
            metadata = None

        if metadata is not None:
            # 2. No writes were lost — every process's append survived.
            if len(metadata) != expected:
                failures.append(
                    f"lost writes: metadata has {len(metadata)} entries, expected {expected}"
                )

            # 3. Index and metadata agree, so search_memory returns the right text per hit.
            from core.memory import _load_index, search_memory

            index, loaded_meta = _load_index()
            if index.ntotal != len(metadata):
                failures.append(
                    f"index/metadata desync: {index.ntotal} vectors vs {len(metadata)} entries"
                )

            # 4. The public read path works end to end.
            try:
                results = search_memory("quick brown fox", k=5)
                if not results:
                    failures.append("search_memory returned no results for an indexed phrase")
            except Exception as exc:  # noqa: BLE001 — any raise here is the failure
                failures.append(f"search_memory raised: {exc.__class__.__name__}: {exc}")

        # 5. Permissions still 600 after the atomic-rename rewrite.
        mode = oct(meta_path.stat().st_mode & 0o777)
        if mode != "0o600":
            failures.append(f"metadata.json mode is {mode}, expected 0o600")

        shutil.rmtree(persona_data_dir(), ignore_errors=True)

    print(f"\n{WRITERS} processes x {ENTRIES_PER_WRITER} entries = {expected} expected\n")
    if failures:
        for f in failures:
            print(f"  FAIL  {f}")
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("  PASS  metadata parses, no lost writes, index in sync, search works, mode 600")
    return 0


if __name__ == "__main__":
    sys.exit(main())
