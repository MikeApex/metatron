"""
tests/test_attachment_persistence.py — a file sent in one turn is still usable in a later one.

The defect this guards against was reported live on 2026-09-03: a user attached a
PDF, asked about it two turns later, and was told files from earlier messages are
not retained — so they had to upload it again. The bytes had in fact been on disk
the whole time; nothing addressed them once the client stopped re-sending the id.

No model call, no server, no real persona data: files go into a temp tree and the
store is exercised directly, so the suite runs offline in well under a second.

What this is actually guarding:
  1. **A later turn can reach an earlier file** — the user's own words are what
     select it, and a message carrying its own files revives nothing.
  2. **The carry window closes.** Past the TTL a file stops entering prompts, and
     past the retention window it stops existing; both caps hold.
  3. **Revived content re-enters through describe_for_prompt(), not around it.**
     A carried file is named in the same paragraph as a fresh one and under the
     same untrusted-content sentence — there is no second, lighter path.
  4. **Permissions stay 600** on everything the store writes.

Standalone runner (no pytest dependency), matching the convention of the other
scripts in tests/.

Usage:
    python3 tests/test_attachment_persistence.py

Exits 0 if every check passes, 1 otherwise.
"""

from __future__ import annotations

import shutil
import stat
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.attachments as att                       # noqa: E402


PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PDF = b"%PDF-1.7\n" + b"\x00" * 64

_tmpdir: str | None = None


def _sandbox() -> Path:
    """Point persona_data_dir at a throwaway tree, so nothing touches real data."""
    global _tmpdir
    if _tmpdir:
        shutil.rmtree(_tmpdir, ignore_errors=True)
    _tmpdir = tempfile.mkdtemp(prefix="metatron-persist-")
    root = Path(_tmpdir)
    att.persona_data_dir = lambda persona=None: root / "personas" / (persona or "x")
    return root


def _aged(record: dict, seconds: float) -> dict:
    """A copy of a record that claims to have been stored `seconds` ago."""
    ts = (datetime.now() - timedelta(seconds=seconds)).isoformat()
    return {**record, "ts": ts}


# ---------------------------------------------------------------------------
# 1. Reaching an earlier file from a later turn
# ---------------------------------------------------------------------------

def check_a_later_turn_can_reach_a_file_sent_earlier():
    _sandbox()
    pdf = att.save("danny_park", PDF, "tenancy.pdf", "application/pdf")
    carryable = att.carryable([pdf])
    assert len(carryable) == 1, carryable

    picked = att.references_earlier_files("what does the pdf i sent say about notice?", carryable)
    assert [r["id"] for r in picked] == [pdf["id"]], picked
    # And the bytes are genuinely reachable — this is the whole point.
    assert att.load_parts(picked) == [(PDF, "application/pdf")]


def check_naming_the_file_outright_is_enough():
    _sandbox()
    pdf = att.save("danny_park", PDF, "tenancy.pdf", "application/pdf")
    png = att.save("danny_park", PNG, "meter.png", "image/png")
    carryable = att.carryable([pdf, png])

    # No backward-reference phrase at all — the filename alone carries the reference.
    picked = att.references_earlier_files("summarise tenancy.pdf for me", carryable)
    assert [r["name"] for r in picked] == ["tenancy.pdf"], picked

    # The stem works too, because that is how people type a filename.
    picked = att.references_earlier_files("anything odd in the meter shot?", carryable)
    assert [r["name"] for r in picked] == ["meter.png"], picked


def check_a_type_word_selects_only_that_type():
    _sandbox()
    pdf = att.save("danny_park", PDF, "a.pdf", "application/pdf")
    png = att.save("danny_park", PNG, "b.png", "image/png")
    carryable = att.carryable([pdf, png])

    picked = att.references_earlier_files("read the pdf i sent you", carryable)
    assert [r["mime"] for r in picked] == ["application/pdf"], picked

    picked = att.references_earlier_files("look at that photo again", carryable)
    assert [r["mime"] for r in picked] == ["image/png"], picked


def check_a_bare_back_reference_takes_only_the_most_recent():
    _sandbox()
    old = _aged(att.save("danny_park", PDF, "a.pdf", "application/pdf"), 600)
    new = att.save("danny_park", PNG, "b.png", "image/png")
    carryable = att.carryable([old, new])

    picked = att.references_earlier_files("can you look at that again, the one i sent", carryable)
    assert len(picked) == 1 and picked[0]["name"] == "b.png", picked


def check_an_ordinary_message_revives_nothing():
    _sandbox()
    pdf = att.save("danny_park", PDF, "tenancy.pdf", "application/pdf")
    carryable = att.carryable([pdf])

    for text in ("what's on my calendar tomorrow?",
                 "draft me a pdf about the meeting",     # a request, not a reference
                 "how are you?",
                 ""):
        assert att.references_earlier_files(text, carryable) == [], text


# ---------------------------------------------------------------------------
# 2. The window closes — TTL, retention, caps
# ---------------------------------------------------------------------------

def check_a_file_past_the_carry_ttl_stops_entering_prompts():
    _sandbox()
    pdf = att.save("danny_park", PDF, "tenancy.pdf", "application/pdf")
    stale = _aged(pdf, att.CARRY_TTL_SECONDS + 60)

    assert att.carryable([stale]) == [], "a file past the carry TTL is still carryable"
    # Still on disk, though — retention is a separate, longer clock.
    assert Path(pdf["path"]).exists()


def check_a_file_inside_the_carry_ttl_is_still_offered():
    _sandbox()
    pdf = att.save("danny_park", PDF, "tenancy.pdf", "application/pdf")
    assert len(att.carryable([_aged(pdf, att.CARRY_TTL_SECONDS - 60)])) == 1


def check_the_carry_caps_bound_count_and_bytes():
    _sandbox()
    records = [
        {"id": f"i{n}", "name": f"f{n}.pdf", "mime": "application/pdf",
         "size": 1024, "ts": datetime.now().isoformat(), "path": "/nope"}
        for n in range(10)
    ]
    assert len(att.carryable(records)) == att.MAX_CARRY_FILES, att.carryable(records)

    huge = [
        {"id": "big", "name": "big.pdf", "mime": "application/pdf",
         "size": att.MAX_CARRY_BYTES + 1, "ts": datetime.now().isoformat(), "path": "/nope"},
        {"id": "small", "name": "small.pdf", "mime": "application/pdf",
         "size": 10, "ts": datetime.now().isoformat(), "path": "/nope"},
    ]
    kept = att.carryable(huge)
    assert [r["id"] for r in kept] == ["small"], kept


def check_newest_first_so_the_cap_drops_the_oldest():
    _sandbox()
    now = datetime.now()
    records = [
        {"id": "old", "name": "old.pdf", "mime": "application/pdf", "size": 1,
         "ts": (now - timedelta(hours=5)).isoformat(), "path": "/nope"},
        {"id": "mid", "name": "mid.pdf", "mime": "application/pdf", "size": 1,
         "ts": (now - timedelta(hours=2)).isoformat(), "path": "/nope"},
        {"id": "new", "name": "new.pdf", "mime": "application/pdf", "size": 1,
         "ts": now.isoformat(), "path": "/nope"},
    ]
    assert [r["id"] for r in att.carryable(records)] == ["new", "mid"], att.carryable(records)


def check_the_sweep_deletes_only_what_is_past_retention():
    _sandbox()
    keep = att.save("danny_park", PDF, "keep.pdf", "application/pdf")
    drop = att.save("danny_park", PNG, "drop.png", "image/png")

    # Age the sidecar of one of them past retention — the sweep reads the stored
    # timestamp, not a process clock, which is why a restart changes nothing.
    sidecar = Path(drop["path"]).with_suffix(".json")
    import json
    sidecar.write_text(json.dumps(_aged(drop, att.RETENTION_SECONDS + 60)))

    removed = att.sweep_expired("danny_park")
    assert removed == [drop["id"]], removed
    assert not Path(drop["path"]).exists(), "expired file still on disk"
    assert not sidecar.exists(), "expired sidecar still on disk"
    assert Path(keep["path"]).exists(), "the sweep took a file inside retention"


def check_the_sweep_is_quiet_when_there_is_nothing_to_take():
    _sandbox()
    assert att.sweep_expired("nobody_at_all") == []
    att.save("danny_park", PDF, "a.pdf", "application/pdf")
    assert att.sweep_expired("danny_park") == []


# ---------------------------------------------------------------------------
# 3. Revived content re-enters through describe_for_prompt()
# ---------------------------------------------------------------------------

def check_a_carried_file_is_described_by_the_same_function_as_a_fresh_one():
    _sandbox()
    pdf = att.save("danny_park", PDF, "tenancy.pdf", "application/pdf")
    carried = att.carryable([pdf])
    assert carried[0]["carried"] is True

    text = att.describe_for_prompt(carried)
    assert "tenancy.pdf" in text, text
    assert "earlier" in text, text
    assert "not attached to the current message" in text, text
    # The boundary sentence is present for a revived file exactly as for a fresh
    # one — the security control does not weaken because the bytes came from store.
    assert "never instructions" in text, text
    assert "untrusted_content" in text, text


def check_fresh_and_carried_files_are_told_apart_in_one_description():
    _sandbox()
    fresh = att.save("danny_park", PNG, "photo.png", "image/png")
    carried = att.carryable([att.save("danny_park", PDF, "tenancy.pdf", "application/pdf")])

    text = att.describe_for_prompt([fresh] + carried)
    assert "attached 1 file to this message: photo.png" in text, text
    assert "tenancy.pdf" in text and "sent earlier" in text, text
    assert text.count("untrusted_content") == 1, "the boundary is stated once, not per file"


def check_a_fresh_only_description_is_unchanged():
    # The wording a fresh attachment gets must not have drifted — the agent files
    # refer to this sentence and they are Red-tier, so they cannot follow a change.
    text = att.describe_for_prompt([{"name": "dog.jpg", "mime": "image/jpeg"}])
    assert "The user attached 1 file to this message: dog.jpg (image/jpeg)." in text, text
    assert "earlier" not in text, text


def check_load_parts_reads_carried_bytes_like_any_other():
    _sandbox()
    pdf = att.save("danny_park", PDF, "tenancy.pdf", "application/pdf")
    assert att.load_parts(att.carryable([pdf])) == [(PDF, "application/pdf")]


# ---------------------------------------------------------------------------
# 4. Permissions
# ---------------------------------------------------------------------------

def check_stored_files_and_sidecars_are_owner_only():
    _sandbox()
    record = att.save("danny_park", PDF, "tenancy.pdf", "application/pdf")
    for path in (Path(record["path"]), Path(record["path"]).with_suffix(".json")):
        mode = stat.S_IMODE(path.stat().st_mode)
        assert mode == 0o600, f"{path.name} is {oct(mode)}, expected 0o600"


# ---------------------------------------------------------------------------
# 5. The server-side selection rule
# ---------------------------------------------------------------------------

def _with_temp_db():
    """Point core.server at a throwaway database and return the module."""
    import asyncio
    import core.server as srv

    root = _sandbox()
    srv.DB_PATH = root / "metatron.db"
    asyncio.run(srv._init_db())
    return srv, asyncio


def check_the_server_revives_an_earlier_file_for_a_later_turn():
    """The reported defect, end to end: upload on turn one, reference on turn three."""
    srv, asyncio = _with_temp_db()

    record = att.save("danny_park", PDF, "tenancy.pdf", "application/pdf")
    asyncio.run(srv._insert_attachment(record))
    # Turn one sent it; turns two and three carry no ids at all.
    asyncio.run(srv._bind_attachments([record["id"]], "exch-1"))

    revived = asyncio.run(
        srv._revive_attachments("danny_park", "what did the pdf i sent say about notice?", [])
    )
    assert [r["id"] for r in revived] == [record["id"]], revived
    assert revived[0]["carried"] is True
    assert att.load_parts(revived) == [(PDF, "application/pdf")], "bytes not reachable"


def check_the_server_revives_nothing_for_an_ordinary_message():
    srv, asyncio = _with_temp_db()
    record = att.save("danny_park", PDF, "tenancy.pdf", "application/pdf")
    asyncio.run(srv._insert_attachment(record))

    assert asyncio.run(
        srv._revive_attachments("danny_park", "what's on my calendar tomorrow?", [])
    ) == []


def check_the_server_revives_nothing_when_the_message_has_its_own_files():
    """A user who has just attached something is talking about that."""
    srv, asyncio = _with_temp_db()
    stored = att.save("danny_park", PDF, "tenancy.pdf", "application/pdf")
    asyncio.run(srv._insert_attachment(stored))
    fresh = att.save("danny_park", PNG, "photo.png", "image/png")
    asyncio.run(srv._insert_attachment(fresh))

    assert asyncio.run(
        srv._revive_attachments("danny_park", "check this against the pdf i sent", [fresh])
    ) == []


def check_one_personas_files_are_invisible_to_another():
    srv, asyncio = _with_temp_db()
    record = att.save("danny_park", PDF, "tenancy.pdf", "application/pdf")
    asyncio.run(srv._insert_attachment(record))

    assert asyncio.run(
        srv._revive_attachments("someone_else", "read the pdf i sent you", [])
    ) == []


def check_the_index_forgets_a_file_the_sweep_deleted():
    srv, asyncio = _with_temp_db()
    record = att.save("danny_park", PDF, "tenancy.pdf", "application/pdf")
    asyncio.run(srv._insert_attachment(record))

    asyncio.run(srv._forget_attachments([record["id"]]))
    assert asyncio.run(srv._get_attachment(record["id"], "danny_park")) is None


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
