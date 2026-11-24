"""
tests/test_open_thread_cap.py — open threads stop piling up past five, and the cap never drops
something held back or a clinical thread (Stage 2 #4, review S7.1 and L6, build-time
amendment 2).

Tmp persona dir; no model, no network.

Run:  python3 tests/test_open_thread_cap.py   (or pytest)
"""

from __future__ import annotations

import json
import sys
import tempfile
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.context_tracker as ct  # noqa: E402

TODAY = date.today().isoformat()


def _ago(days: int) -> str:
    return (date.today() - timedelta(days=days)).isoformat()


# Distinct subjects, so no two share two anchor tokens.
SUBJECTS = ["plumber quote", "bookstore ledger", "violin lesson", "passport renewal",
            "garden fence", "dentist appointment", "insurance claim", "museum tickets"]


@contextmanager
def tracker(seed: dict | None = None):
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        path = tmp_path / "context.json"
        if seed is not None:
            path.write_text(json.dumps(seed))
        with mock.patch.object(ct, "persona_data_dir", lambda *a, **k: tmp_path), \
                mock.patch("tools.obligations.consult_index", lambda *a, **k: []):
            yield path


def _seed_threads(n: int) -> list[dict]:
    # SUBJECTS[0] oldest (6 days), each next one a day younger; all inside the expiry window.
    return [{"text": SUBJECTS[i], "added": _ago(6 - i)} for i in range(n)]


def _write(threads, user_text=None, **kw):
    return ct.write_context_tracker(open_threads=threads, patterns=kw.get("patterns", []),
                                    follow_ups=kw.get("follow_ups", []),
                                    held_items=kw.get("held_items"),
                                    clinical_threads=kw.get("clinical_threads"),
                                    user_text=user_text)


def test_case1_newest_five_kept_oldest_archived():
    seed = {"open_threads": _seed_threads(7)}
    with tracker(seed) as path:
        _write(SUBJECTS[:7])
        data = json.loads(path.read_text())
    assert [t["text"] for t in data["open_threads"]] == SUBJECTS[2:7]
    capped = [t for t in data["expired_open_threads"] if t.get("reason") == "cap"]
    assert [t["text"] for t in capped] == SUBJECTS[:2]
    assert all(t["capped_on"] == TODAY for t in capped)


def test_case2_capped_resend_not_readmitted():
    seed = {"open_threads": _seed_threads(7)}
    with tracker(seed) as path:
        _write(SUBJECTS[:7])
        _write(SUBJECTS[:7], user_text="nothing relevant at all here today")
        data = json.loads(path.read_text())
    texts = [t["text"] for t in data["open_threads"]]
    assert SUBJECTS[0] not in texts and SUBJECTS[1] not in texts


def test_case3_engaged_capped_thread_readmitted_today():
    seed = {"open_threads": _seed_threads(7)}
    with tracker(seed) as path:
        _write(SUBJECTS[:7])
        _write([SUBJECTS[0]], user_text="any news on the plumber quote?")
        data = json.loads(path.read_text())
    assert data["open_threads"] == [{"text": SUBJECTS[0], "added": TODAY}]


def test_case3b_engaged_oldest_is_exempt():
    seed = {"open_threads": _seed_threads(6)}
    with tracker(seed) as path:
        _write(SUBJECTS[:6], user_text="the plumber quote came in high")
        data = json.loads(path.read_text())
    texts = [t["text"] for t in data["open_threads"]]
    assert SUBJECTS[0] in texts                       # engaged, kept
    assert SUBJECTS[1] not in texts                   # next-oldest capped instead
    kept = next(t for t in data["open_threads"] if t["text"] == SUBJECTS[0])
    assert kept["added"] == _ago(6)                   # its stored date is untouched


def test_case3c_old_cap_entry_inert_expiry_entry_still_blocks():
    seed = {
        "open_threads": [],
        "expired_open_threads": [
            {"text": "garden fence panels", "added": _ago(20), "expired_on": _ago(8),
             "capped_on": _ago(8), "reason": "cap"},
            {"text": "museum tickets booking", "added": _ago(20), "expired_on": _ago(8)},
        ],
    }
    with tracker(seed) as path:
        _write(["garden fence panels", "garden fence panels repaint",
                "museum tickets booking"])
        data = json.loads(path.read_text())
    texts = [t["text"] for t in data["open_threads"]]
    assert "garden fence panels" in texts             # re-send of an old cap entry
    assert "garden fence panels repaint" in texts     # new lookalike
    assert "museum tickets booking" not in texts      # expiry-archived: unchanged


def test_amendment2_sibling_of_capped_thread_survives():
    # Two related open threads (share "violin" and "lesson"); the older one is capped.
    seed = {"open_threads": [
        {"text": "violin lesson fee", "added": _ago(6)},
        {"text": SUBJECTS[0], "added": _ago(5)},
        {"text": SUBJECTS[1], "added": _ago(5)},
        {"text": SUBJECTS[3], "added": _ago(4)},
        {"text": SUBJECTS[4], "added": _ago(3)},
        {"text": "violin lesson time change", "added": _ago(2)},
    ]}
    incoming = [t["text"] for t in seed["open_threads"]]
    with tracker(seed) as path:
        _write(incoming)
        first = json.loads(path.read_text())
        assert "violin lesson fee" not in [t["text"] for t in first["open_threads"]]
        _write([t["text"] for t in first["open_threads"]], user_text="hello")
        data = json.loads(path.read_text())
    assert "violin lesson time change" in [t["text"] for t in data["open_threads"]]


def _sibling_seed():
    return {"open_threads": [
        {"text": "violin lesson fee", "added": _ago(6)},
        {"text": SUBJECTS[0], "added": _ago(5)},
        {"text": SUBJECTS[1], "added": _ago(5)},
        {"text": SUBJECTS[3], "added": _ago(4)},
        {"text": SUBJECTS[4], "added": _ago(3)},
        {"text": "violin lesson time change", "added": _ago(2)},
    ]}


def test_review_reworded_sibling_of_capped_thread_survives():
    seed = _sibling_seed()
    with tracker(seed) as path:
        _write([t["text"] for t in seed["open_threads"]])
        first = json.loads(path.read_text())
        kept = [t["text"] for t in first["open_threads"]]
        assert "violin lesson fee" not in kept and "violin lesson time change" in kept
        # Y re-sent REWORDED, no user engagement.
        resend = [("violin lesson time moved again" if t == "violin lesson time change" else t)
                  for t in kept]
        _write(resend, user_text="hello")
        data = json.loads(path.read_text())
    threads = {t["text"]: t["added"] for t in data["open_threads"]}
    assert threads.get("violin lesson time moved again") == _ago(2), threads   # Y's own date
    archived = [t["text"] for t in data["expired_open_threads"]]
    assert "violin lesson time moved again" not in archived
    assert archived.count("violin lesson fee") == 1


def test_review_exact_resend_of_capped_thread_still_blocked_beside_open_sibling():
    seed = _sibling_seed()
    with tracker(seed) as path:
        _write([t["text"] for t in seed["open_threads"]])
        kept = [t["text"] for t in json.loads(path.read_text())["open_threads"]]
        _write(kept + ["violin lesson fee"], user_text="hello")
        data = json.loads(path.read_text())
    texts = [t["text"] for t in data["open_threads"]]
    assert "violin lesson fee" not in texts and "violin lesson time change" in texts


def test_case4_other_categories_never_capped():
    held = [f"Held: item {i}" for i in range(4)] + [
        {"text": f"Held: dict item {i}", "held_since": _ago(3)} for i in range(4)]
    clinical = [{"flag": f"MUST_SURFACE: TEST_{i}", "status": "watch"} for i in range(7)]
    with tracker({"open_threads": []}) as path:
        _write([], patterns=[f"p{i}" for i in range(8)],
               follow_ups=[f"f{i}" for i in range(8)], held_items=held,
               clinical_threads=clinical)
        data = json.loads(path.read_text())
    # Stage 4 M4: held items are stored dated ({"text", "held_since"}); a new bare string is
    # stamped today and a dated one keeps its date. All eight survive — none is capped.
    assert [h["text"] for h in data["held_items"]] == [
        h if isinstance(h, str) else h["text"] for h in held]
    assert [h["held_since"] for h in data["held_items"][4:]] == [_ago(3)] * 4
    assert len(data["clinical_threads"]) == 7
    assert len(data["patterns"]) == 8 and len(data["follow_ups"]) == 8


def test_case5_audit_capped_not_removed():
    seed = {"open_threads": _seed_threads(7)}
    with tracker(seed) as path:
        _write(SUBJECTS[:7])
        line = json.loads((path.parent / "context_audit.jsonl").read_text().splitlines()[-1])
    assert line["capped"] == sorted(SUBJECTS[:2])
    assert not set(SUBJECTS[:2]) & set(line["removed"])
    assert line["open_count"] == 5


def test_case6_exactly_five_untouched():
    seed = {"open_threads": _seed_threads(5)}
    with tracker(seed) as path:
        _write(SUBJECTS[:5])
        data = json.loads(path.read_text())
    assert [t["text"] for t in data["open_threads"]] == SUBJECTS[:5]
    assert not data["expired_open_threads"]


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except Exception as exc:  # noqa: BLE001
                failures += 1
                print(f"  FAIL  {name} — {type(exc).__name__}: {exc}")
    print(f"\n{'all passed' if not failures else f'{failures} failed'}")
    sys.exit(1 if failures else 0)
