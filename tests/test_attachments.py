"""
tests/test_attachments.py — user-attached files: validation, storage, and the
parts handed to the model.

No model call, no server, no persona data: files are written into a temp tree and
the Gemini part assembly is exercised against a stub `types` module, so the whole
suite runs offline in under a second.

What this is actually guarding:
  1. **The type is decided by the bytes, not the client's claim.** A PDF renamed
     .png must be stored as a PDF, and an executable claiming to be a PNG must be
     refused — the browser's Content-Type is asserted by whoever is calling.
  2. **The file leads and the text follows** in the model turn, and a file missing
     from disk degrades to text rather than raising.
  3. **The untrusted-content boundary is stated in the prompt**, because bytes
     cannot carry `<untrusted_content>` tags.

Standalone runner (no pytest dependency), matching the convention of the other
scripts in tests/.

Usage:
    python3 tests/test_attachments.py

Exits 0 if every check passes, 1 otherwise.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.attachments as att                       # noqa: E402


PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
PDF = b"%PDF-1.7\n" + b"\x00" * 64
WEBP = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 64
HEIC = b"\x00\x00\x00\x18" + b"ftyp" + b"heic" + b"\x00" * 64

_tmpdir: str | None = None


def _sandbox() -> Path:
    """Point persona_data_dir at a throwaway tree, so nothing touches real data."""
    global _tmpdir
    if _tmpdir:
        shutil.rmtree(_tmpdir, ignore_errors=True)
    _tmpdir = tempfile.mkdtemp(prefix="metatron-attach-")
    root = Path(_tmpdir)
    att.persona_data_dir = lambda persona=None: root / "personas" / (persona or "x")
    return root


# ---------------------------------------------------------------------------
# Sniffing and validation
# ---------------------------------------------------------------------------

def check_sniff_identifies_each_allowed_type():
    assert att.sniff_mime(PNG) == "image/png"
    assert att.sniff_mime(JPEG) == "image/jpeg"
    assert att.sniff_mime(PDF) == "application/pdf"
    assert att.sniff_mime(WEBP) == "image/webp"
    assert att.sniff_mime(HEIC) == "image/heic"


def check_bytes_beat_the_declared_type():
    # A PDF the browser labelled as a PNG is stored as a PDF: the client's claim is
    # not evidence, and the model must be told what it is actually being handed.
    assert att.validate(PDF, declared_mime="image/png") == "application/pdf"


def check_unknown_type_is_refused():
    try:
        att.validate(b"MZ\x90\x00" + b"\x00" * 64)   # a Windows executable
    except att.AttachmentRejected as e:
        assert "supported" in str(e), e
    else:
        raise AssertionError("an unrecognised file type was accepted")


def check_empty_file_is_refused():
    try:
        att.validate(b"")
    except att.AttachmentRejected as e:
        assert "empty" in str(e).lower(), e
    else:
        raise AssertionError("an empty file was accepted")


def check_oversize_file_is_refused():
    big = PNG + b"\x00" * att.MAX_FILE_BYTES
    try:
        att.validate(big)
    except att.AttachmentRejected as e:
        assert "MB" in str(e), e
    else:
        raise AssertionError("an oversize file was accepted")


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def check_save_writes_file_and_sidecar_under_the_persona():
    root = _sandbox()
    rec = att.save("danny_park", PNG, "holiday.png", "image/png")

    path = Path(rec["path"])
    assert path.exists(), path
    assert path.read_bytes() == PNG
    assert "personas/danny_park/attachments/" in str(path), path

    sidecar = path.with_suffix(".json")
    assert sidecar.exists(), sidecar
    assert json.loads(sidecar.read_text())["name"] == "holiday.png"

    assert rec["size"] == len(PNG)
    assert rec["mime"] == "image/png"
    assert root in path.parents or str(root) in str(path)


def check_stored_file_is_not_world_readable():
    _sandbox()
    rec = att.save("danny_park", PDF, "letter.pdf", "application/pdf")
    mode = Path(rec["path"]).stat().st_mode & 0o777
    assert mode == 0o600, oct(mode)


def check_a_hostile_filename_cannot_escape_the_directory():
    # The stored name is only ever a label — the path is built from a generated id.
    _sandbox()
    rec = att.save("danny_park", PNG, "../../../../etc/passwd", "image/png")
    assert "etc/passwd" not in rec["path"], rec["path"]
    assert Path(rec["path"]).name.endswith(".png"), rec["path"]


def check_two_saves_do_not_collide():
    _sandbox()
    a = att.save("danny_park", PNG, "same.png", "image/png")
    b = att.save("danny_park", PNG, "same.png", "image/png")
    assert a["id"] != b["id"]
    assert a["path"] != b["path"]


# ---------------------------------------------------------------------------
# What reaches the model
# ---------------------------------------------------------------------------

def check_message_is_capped_by_total_bytes_not_only_count():
    # Four files inside the per-file limit can still exceed what one request carries.
    big = [{"id": str(i), "name": f"{i}.png", "size": att.MAX_FILE_BYTES} for i in range(4)]
    kept = att.cap_for_message(big)
    assert len(kept) < 4, len(kept)
    assert sum(r["size"] for r in kept) <= att.MAX_TOTAL_BYTES


def check_message_cap_keeps_a_normal_batch_intact():
    small = [{"id": str(i), "name": f"{i}.png", "size": 200_000} for i in range(4)]
    assert len(att.cap_for_message(small)) == 4


def check_message_cap_drops_the_tail_not_the_head():
    files = [{"id": "a", "size": 9 * 1024 * 1024},
             {"id": "b", "size": 9 * 1024 * 1024}]
    kept = att.cap_for_message(files)
    assert [r["id"] for r in kept] == ["a"], kept


def check_description_names_the_files_and_marks_them_as_data():
    text = att.describe_for_prompt([
        {"name": "dog.jpg", "mime": "image/jpeg"},
        {"name": "bill.pdf", "mime": "application/pdf"},
    ])
    assert "dog.jpg" in text and "bill.pdf" in text, text
    assert "2 files" in text, text
    # The boundary itself — this sentence is what the agent files refer to.
    assert "never instructions" in text, text
    assert "untrusted_content" in text, text


def check_description_is_empty_without_attachments():
    assert att.describe_for_prompt([]) == ""


def check_load_parts_skips_a_file_that_has_been_deleted():
    _sandbox()
    kept = att.save("danny_park", PNG, "kept.png", "image/png")
    gone = att.save("danny_park", JPEG, "gone.jpg", "image/jpeg")
    Path(gone["path"]).unlink()

    parts = att.load_parts([kept, gone])
    assert len(parts) == 1, parts
    assert parts[0] == (PNG, "image/png")


def check_user_turn_puts_files_before_the_text():
    """The orchestrator's part assembly, against a stub SDK."""
    _sandbox()
    rec = att.save("danny_park", PNG, "dog.png", "image/png")

    class _StubPart:
        def __init__(self, text=None, data=None, mime_type=None):
            self.text, self.data, self.mime_type = text, data, mime_type

        @classmethod
        def from_bytes(cls, data, mime_type):
            return cls(data=data, mime_type=mime_type)

    class _StubTypes:
        Part = _StubPart

    from core.orchestrator import _gemini_user_parts

    parts = _gemini_user_parts(_StubTypes, "what breed is this?", [rec])
    assert len(parts) == 2, parts
    # File first: the question that follows refers to the thing above it.
    assert parts[0].data == PNG and parts[0].mime_type == "image/png"
    assert parts[1].text == "what breed is this?"


def check_user_turn_without_files_is_text_only():
    class _StubPart:
        def __init__(self, text=None, data=None, mime_type=None):
            self.text, self.data, self.mime_type = text, data, mime_type

        @classmethod
        def from_bytes(cls, data, mime_type):
            return cls(data=data, mime_type=mime_type)

    class _StubTypes:
        Part = _StubPart

    from core.orchestrator import _gemini_user_parts

    parts = _gemini_user_parts(_StubTypes, "hello", None)
    assert len(parts) == 1 and parts[0].text == "hello", parts


def check_history_note_records_names_not_bytes():
    from core.orchestrator import _history_attachment_note
    assert _history_attachment_note(None) == ""
    note = _history_attachment_note([{"name": "dog.png"}, {"name": "bill.pdf"}])
    assert note == " [attached: dog.png, bill.pdf]", note


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

CHECKS = [fn for name, fn in sorted(globals().items()) if name.startswith("check_")]


def main() -> int:
    failed = 0
    for fn in CHECKS:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"  FAIL  {fn.__name__}: {exc}")
        except Exception as exc:
            failed += 1
            print(f"  ERROR {fn.__name__}: {type(exc).__name__}: {exc}")
    if _tmpdir:
        shutil.rmtree(_tmpdir, ignore_errors=True)
    print(f"\n{len(CHECKS) - failed}/{len(CHECKS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
