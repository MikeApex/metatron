"""
tests/test_grants_dedup.py — the two code halves of the 2026-08-28 grants pass
([DB-0810-03]).

1. write_archive dedup (tools/diarist.py). Five specialists gained write_archive
   in one pass; an append-only store with six writers accumulates near-identical
   rows (the same book filed at mention and again at completion). A row matching
   on the natural key (title/name/text/description, case-insensitive) is UPDATED
   — new non-empty fields win, nothing is deleted — instead of appended twice.

2. write_quality_event same-trace/same-type no-op (tools/logger.py). The
   Coordinator can now write an event directly AND the program layer writes
   template-slot events from its output; the Synthesizer is a third writer for
   ROUTING_MISS. One detected signal must produce one stored event per turn.

Run: python3 tests/test_grants_dedup.py
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools import diarist, logger  # noqa: E402
from core import trace as trace_mod  # noqa: E402

_results: list[tuple[bool, str]] = []


def check(label: str, condition: bool) -> None:
    _results.append((condition, label))
    print(f"  {'PASS' if condition else 'FAIL'}  {label}")


def part1() -> None:
    print("write_archive dedup — one entry per real-world item")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        with mock.patch.object(diarist, "_archive_dir", return_value=tmp):
            # The canonical clutter case: filed as to-read, filed again as read.
            diarist.write_archive("books", {"title": "Dune", "status": "to-read",
                                            "author": "Herbert"})
            msg = diarist.write_archive("books", {"title": "dune", "status": "read"})
            rows = json.loads((tmp / "books.json").read_text())
            check("second write of the same title does not append a twin",
                  len(rows) == 1)
            check("the update wins: status moved to-read -> read",
                  rows[0]["status"] == "read")
            check("fields the update did not carry are kept (author)",
                  rows[0].get("author") == "Herbert")
            check("original date_added survives the update",
                  "date_added" in rows[0] and rows[0].get("date_updated"))
            check("the return message says updated, not added",
                  "Updated" in msg)

            # Distinct items still append.
            diarist.write_archive("books", {"title": "Solaris"})
            rows = json.loads((tmp / "books.json").read_text())
            check("a different title appends normally", len(rows) == 2)

            # Same title in a different category is a different thing.
            diarist.write_archive("films", {"title": "Dune"})
            films = json.loads((tmp / "films.json").read_text())
            check("same title in another category is its own entry",
                  len(films) == 1 and "date_added" in films[0])

            # Entries with no identity field keep pure append behaviour.
            diarist.write_archive("ideas", {"notes": "untitled thought"})
            diarist.write_archive("ideas", {"notes": "untitled thought"})
            ideas = json.loads((tmp / "ideas.json").read_text())
            check("no identity field -> append as before (no false merge)",
                  len(ideas) == 2)

            # String shorthand goes through the same key.
            diarist.write_archive("music", "Kind of Blue")
            diarist.write_archive("music", "kind of blue")
            music = json.loads((tmp / "music.json").read_text())
            check("string-shorthand items dedup on title too", len(music) == 1)


def part2() -> None:
    print("\nwrite_quality_event — one event per type per trace")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        with mock.patch.object(logger, "_logs_dir", return_value=tmp):
            # Inside a trace: same type twice -> one stored line.
            t = trace_mod.RequestTrace("probe", "danny_park")
            trace_mod.set_trace(t)
            try:
                r1 = logger.write_quality_event("USER_CORRECTION", "coordinator",
                                                "user corrected the venue name")
                r2 = logger.write_quality_event("USER_CORRECTION", "synthesizer",
                                                "same correction, re-detected")
                r3 = logger.write_quality_event("ROUTING_MISS", "logistics",
                                                "different type, same trace")
            finally:
                trace_mod.set_trace(None)
            lines = (tmp / "quality_events.json").read_text().strip().splitlines()
            check("first write lands", "logged" in r1)
            check("second write of the same type no-ops", "skipped" in r2)
            check("a different event type still writes", "logged" in r3)
            check("exactly two events stored for the three calls", len(lines) == 2)

        # Outside any trace (tests, scripts, scheduler functions): never deduped.
        with mock.patch.object(logger, "_logs_dir", return_value=tmp):
            logger.write_quality_event("USER_CORRECTION", "x", "no trace, call 1")
            logger.write_quality_event("USER_CORRECTION", "x", "no trace, call 2")
            lines = (tmp / "quality_events.json").read_text().strip().splitlines()
            check("no trace -> no dedup (both stored)", len(lines) == 4)

        # A new trace starts clean.
        with mock.patch.object(logger, "_logs_dir", return_value=tmp):
            t2 = trace_mod.RequestTrace("probe2", "danny_park")
            trace_mod.set_trace(t2)
            try:
                r = logger.write_quality_event("USER_CORRECTION", "coordinator",
                                               "fresh trace, fresh event")
            finally:
                trace_mod.set_trace(None)
            check("the dedup state dies with the trace", "logged" in r)


def main() -> int:
    part1()
    part2()
    print()
    failed = [label for ok, label in _results if not ok]
    if failed:
        print(f"{len(failed)} check(s) FAILED:")
        for label in failed:
            print(f"  - {label}")
        return 1
    print(f"All {len(_results)} grants-pass dedup checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
