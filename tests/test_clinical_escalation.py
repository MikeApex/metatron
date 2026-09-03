"""
tests/test_clinical_escalation.py — [DB-0808-06], built 2026-09-03.

The item was filed as "a flagged clinical thread can never be marked resolved". Mike's
ruling on 2026-09-03 named the gap upstream of that: a tier-2 flag ALERTED NOTHING. It
surfaced once, moved to `watch`, and lived on in a file only the model reads.

So what is asserted here, in order of what matters:

  1. A tier-2 flag lands in the escalation inbox the moment it is raised — once, however
     many times the thread list is re-submitted.
  2. A tier-1 flag does not. The inbox is for the threads that cannot be closed in
     conversation.
  3. The record states plainly that nothing was routed anywhere. A queue that looks
     monitored and is not is worse than an obviously empty one.
  4. A session STILL cannot resolve a tier-2 thread. The old refusal is untouched.
  5. The only path to `resolved` runs through a code-raised card and a spent approval
     token — no token, no close.
  6. Closing archives rather than deletes, and keeps the basis.
  7. The dwell holds: a freshly raised concern is not offered for closing.

See tests/test_clinical_threads.py for the tier derivation and watch/active lifecycle,
which this does not re-cover.

Usage:
    python tests/test_clinical_escalation.py
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.confirm as CF  # noqa: E402
import tools.context_tracker as CT  # noqa: E402
import tools.escalation as ESC  # noqa: E402

_results: list[tuple[str, bool, str]] = []


def check(name: str):
    def wrap(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except AssertionError as e:
            _results.append((name, False, f"assertion: {e}"))
        except Exception as e:
            _results.append((name, False, f"{type(e).__name__}: {e}"))
        return fn
    return wrap


class _temp_persona:
    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name)
        self._orig = (CT.persona_data_dir, ESC.persona_data_dir, CF.persona_data_dir)
        CT.persona_data_dir = lambda persona=None: self.path
        ESC.persona_data_dir = lambda persona=None: self.path
        CF.persona_data_dir = lambda persona=None: self.path
        return self.path

    def __exit__(self, *exc):
        CT.persona_data_dir, ESC.persona_data_dir, CF.persona_data_dir = self._orig
        self._tmp.cleanup()


def _write(threads):
    return CT.write_context_tracker(open_threads=[], patterns=[], follow_ups=[],
                                    clinical_threads=threads)


# --- 1-3: the alert --------------------------------------------------------

@check("a tier-2 flag lands in the escalation inbox when it is raised")
def _():
    with _temp_persona():
        _write([{"flag": "CLINICAL_CONCERN: persistent low mood",
                 "status": "active", "note": "raised in conversation"}])
        pending = ESC.list_escalations("pending")
        assert len(pending) == 1, pending
        assert pending[0]["flag"] == "CLINICAL_CONCERN: persistent low mood", pending


@check("re-submitting the same thread does not multiply the escalation")
def _():
    with _temp_persona():
        for _ in range(5):
            _write([{"flag": "CLINICAL_CONCERN: persistent low mood",
                     "status": "watch", "note": "carried"}])
        assert len(ESC.list_escalations()) == 1, ESC.list_escalations()


@check("a tier-1 flag does not raise an escalation")
def _():
    with _temp_persona():
        _write([{"flag": "MUST_SURFACE", "status": "active", "note": "career"}])
        assert ESC.list_escalations() == [], ESC.list_escalations()


@check("the record says plainly that nothing was routed anywhere")
def _():
    with _temp_persona():
        _write([{"flag": "CLINICAL_CONCERN: x", "status": "active"}])
        entry = ESC.list_escalations()[0]
        assert "notifies nobody" in entry["routed_to"], entry
        assert "no next-of-kin or clinician channel" in entry["routed_to"], entry


@check("a broken inbox does not cost the turn its context write")
def _():
    with _temp_persona() as root:
        (root / "clinical").mkdir(parents=True, exist_ok=True)
        (root / "clinical" / "escalations.json").write_text("{ not json")
        result = _write([{"flag": "CLINICAL_CONCERN: y", "status": "active"}])
        assert isinstance(result, str) and "Error" not in result[:6], result
        kept = list((root / "clinical").glob("escalations.corrupt-*.json"))
        assert kept, "the damaged inbox was replaced with no copy kept"


# --- 4-6: closing ----------------------------------------------------------

@check("a session still cannot resolve a tier-2 thread")
def _():
    with _temp_persona():
        _write([{"flag": "CLINICAL_CONCERN: z", "status": "active"}])
        out = _write([{"flag": "CLINICAL_CONCERN: z", "status": "resolved"}])
        assert "cannot be resolved" in out, out
        live = CT.read_context_tracker()["clinical_threads"]
        assert live and live[0]["status"] == "watch", live


@check("closing without an approval token performs nothing")
def _():
    with _temp_persona():
        _write([{"flag": "CLINICAL_CONCERN: z", "status": "active"}])
        out = ESC.close_clinical_escalation("CLINICAL_CONCERN: z", basis="because")
        assert out.startswith("Error"), out
        assert ESC.list_escalations("pending"), ESC.list_escalations()


@check("an approved close archives the entry and keeps the whole record")
def _():
    with _temp_persona():
        _write([{"flag": "CLINICAL_CONCERN: z", "status": "active",
                 "note": "the original detail"}])
        args = {"flag": "CLINICAL_CONCERN: z", "basis": "user review, 2026-09-17"}
        payload = CF.request("close_clinical_escalation", args, description="close?")
        token = payload["confirm_token"]
        CF.approve(token)
        out = CF.execute(token)
        assert out.get("status") == "executed", out
        entries = ESC.list_escalations()
        assert len(entries) == 1, entries
        e = entries[0]
        assert e["status"] == "archived", e
        # Nothing was thrown away.
        assert e["note"] == "the original detail", e
        assert e["archived_basis"] == "user review, 2026-09-17", e
        assert e["archived_by"] == "user, on review", e
        assert "notifies nobody" in e["routed_to"], e


@check("an approved close also resolves the thread, which stops loading")
def _():
    with _temp_persona():
        _write([{"flag": "CLINICAL_CONCERN: z", "status": "active"}])
        args = {"flag": "CLINICAL_CONCERN: z", "basis": "user review"}
        token = CF.request("close_clinical_escalation", args, description="close?")["confirm_token"]
        CF.approve(token)
        CF.execute(token)
        assert CT.read_context_tracker()["clinical_threads"] == [], \
            CT.read_context_tracker()["clinical_threads"]
        # Archived on disk, not deleted.
        raw = json.loads((CT._tracker_path()).read_text())
        stored = raw["clinical_threads"][0]
        assert stored["status"] == "resolved", stored
        assert stored["resolved_via"] == "administrative review", stored


@check("a close with no recorded basis is refused")
def _():
    with _temp_persona():
        _write([{"flag": "CLINICAL_CONCERN: z", "status": "active"}])
        assert ESC.archive_escalation("CLINICAL_CONCERN: z", basis="") is False
        assert ESC.list_escalations("pending"), "it was archived with no basis"


# --- 7: the dwell ----------------------------------------------------------

@check("a freshly raised concern is not offered for closing")
def _():
    with _temp_persona():
        _write([{"flag": "CLINICAL_CONCERN: z", "status": "active"}])
        out = ESC.review_clinical_escalations()
        assert "nothing due" in out, out
        assert CF.pending() == [], CF.pending()


@check("one past the dwell is offered, by code, exactly once")
def _():
    with _temp_persona():
        _write([{"flag": "CLINICAL_CONCERN: z", "status": "active"}])
        entries = ESC._load()
        entries[0]["raised"] = "2026-01-01"
        ESC._save(entries)
        first = ESC.review_clinical_escalations()
        assert "1 offered" in first, first
        assert len(CF.pending()) == 1, CF.pending()
        # A second run inside the re-offer window does not nag.
        second = ESC.review_clinical_escalations()
        assert "0 offered" in second, second


@check("the offer card names no mechanism and claims nothing was sent")
def _():
    with _temp_persona():
        _write([{"flag": "CLINICAL_CONCERN: z", "status": "active",
                 "note": "a recorded detail"}])
        entries = ESC._load()
        entries[0]["raised"] = "2026-01-01"
        ESC._save(entries)
        ESC.review_clinical_escalations()
        desc = CF.pending()[0]["description"]
        assert "has been sent to anyone" in desc, desc
        for leak in ("CLINICAL_CONCERN", "tier", "escalation", "thread"):
            assert leak not in desc, f"{leak!r} leaked into the card: {desc}"
        # "a flagged health concern" is ordinary English and stays; the bare internal
        # noun would not be, so it is checked on a word boundary rather than as a
        # substring.
        import re as _re
        assert not _re.search(r"\bflags?\b", desc), desc


@check("the review never closes anything on its own")
def _():
    with _temp_persona():
        _write([{"flag": "CLINICAL_CONCERN: z", "status": "active"}])
        entries = ESC._load()
        entries[0]["raised"] = "2026-01-01"
        ESC._save(entries)
        ESC.review_clinical_escalations()
        assert ESC.list_escalations("pending"), "the timer closed it"
        assert CT.read_context_tracker()["clinical_threads"], "the thread was dropped"


# ---------------------------------------------------------------------------

def main() -> int:
    passed = sum(1 for _, ok, _ in _results if ok)
    failed = len(_results) - passed
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if not ok:
            print(f"        {detail}")
    print(f"\n{passed} passed, {failed} failed, {len(_results)} total")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
