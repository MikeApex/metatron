"""The write-time briefing's clean-room fence (scripts/hook_context_gate.py).

`_log_hits` must never surface a reference-reading fragment — fenced by fixed
filename or by a first heading saying "reference-reading" — and must still
surface a fragment that merely mentions WhatsApp in passing. Synthetic
fragments only; no real archive/log/ file is read.

Run: python3 -m pytest tests/test_hook_context_gate_fence.py -q
"""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "hook_context_gate", ROOT / "scripts" / "hook_context_gate.py")
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)

TARGET = "archive/plans/example_plan_2026-01-01.md"
FENCED_NAME = "2026-10-26-04-whatsapp-input-explored-planned-phase-0a.md"


def _fragment(heading: str, body: str = "") -> str:
    return f"### {heading}\n\n{body}Edited `{TARGET}` here.\n"


class FenceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.log = self.root / "archive" / "log"
        self.log.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, name: str, text: str) -> None:
        (self.log / name).write_text(text)

    def _sources(self) -> set[str]:
        return {src for src, _heading, _excerpt in gate._log_hits(self.root, TARGET)}

    def test_fixed_name_is_fenced(self):
        self._write(FENCED_NAME, _fragment("2026-10-26, fourth (planned)"))
        self.assertEqual(self._sources(), set())

    def test_reference_reading_heading_is_fenced(self):
        self._write("2026-12-01-01-phase-0a-prime.md",
                    _fragment("2026-12-01 (WhatsApp increments — Reference-Reading)"))
        self._write("2026-12-02-01-spaced.md",
                    _fragment("2026-12-02 (increments, reference reading)"))
        self.assertEqual(self._sources(), set())

    def test_passing_mention_of_whatsapp_is_still_shown(self):
        name = "2026-11-11-01-codebase-review-fixes.md"
        self._write(name, _fragment(
            "2026-11-11 (codebase review — High and Medium fixes)",
            "Also touched the WhatsApp input plan in passing; WhatsApp is not the subject.\n"))
        self.assertEqual(self._sources(), {name})

    def test_clean_room_fragment_is_shown(self):
        name = "2026-11-22-05-whatsapp-probe-build-clean-room.md"
        self._write(name, _fragment("2026-11-22 (WhatsApp probe build — clean-room)"))
        self.assertEqual(self._sources(), {name})

    def test_reference_reading_below_first_heading_does_not_fence(self):
        # Only the FIRST heading counts; a later section naming it is not a title.
        name = "2026-12-03-01-two-headings.md"
        self._write(name, _fragment("2026-12-03 (backlog attack)")
                    + "\n### Note: the next session is reference-reading\n")
        self.assertEqual(self._sources(), {name})

    def test_typographic_variants_and_bom_are_fenced(self):
        for i, h in enumerate(["reference_reading", "reference  reading",
                               "reference\u2011reading", "reference\u2013reading"]):
            self._write(f"2026-12-1{i}-01-variant.md", _fragment(f"2026-12-1{i} ({h})"))
        self._write("2026-12-20-01-bom.md", "\ufeff" + _fragment("2026-12-20 (reference-reading)"))
        self.assertEqual(self._sources(), set())

    def test_heading_that_merely_mentions_the_phrase_is_fenced_by_design(self):
        # Fails closed (see the comment on _FENCED_FRAGMENTS): hidden, not shown.
        self._write("2026-12-21-01-meta.md",
                    _fragment("2026-12-21 (probe build — clean-room, no reference reading)"))
        self.assertEqual(self._sources(), set())

    def test_fixed_name_is_never_read(self):
        self._write(FENCED_NAME, _fragment("2026-10-26, fourth"))
        real = Path.read_text

        def guarded(path, *a, **kw):
            if path.name == FENCED_NAME:
                raise AssertionError("the fenced fragment was opened")
            return real(path, *a, **kw)

        with mock.patch.object(Path, "read_text", guarded):
            self.assertEqual(self._sources(), set())

    def test_history_blob_is_searched_whatever_its_first_heading(self):
        # _history.md is one frozen blob of many sessions; a heading check would hide all of it.
        self._write("_history.md", _fragment("2026-08-01 (reference-reading)"))
        self.assertEqual(self._sources(), {"_history.md"})

    def test_mixed_directory_keeps_only_the_unfenced(self):
        self._write(FENCED_NAME, _fragment("2026-10-26, fourth"))
        self._write("2026-12-01-01-ref.md", _fragment("2026-12-01 (reference-reading)"))
        self._write("2026-11-05-01-review.md",
                    _fragment("2026-11-05 (whole-codebase review)", "mentions WhatsApp once\n"))
        self.assertEqual(self._sources(), {"2026-11-05-01-review.md"})


if __name__ == "__main__":
    unittest.main()
