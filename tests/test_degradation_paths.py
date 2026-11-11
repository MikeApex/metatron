"""
tests/test_degradation_paths.py — B4's buildable-now degradation paths, [DB-0804-02],
built 2026-09-03.

Two paths, both keyed to what the USER experiences rather than to what broke:

  1. A specialist fails mid-pipeline. The user is told what cannot be done, in the
     Synthesizer's own voice, and is told nothing about why. Before this, the raw
     exception went into the Synthesizer's context as `[Subagent error — ...]` — the
     live instance Mike named on 2026-08-18 was `'NoneType' object is not iterable`,
     and he got no reason at all.

  2. The context tracker is unreadable. It must not read as "nothing is outstanding",
     and the damaged file must not be silently replaced by the next write — clinical
     threads live on that file and are carried forward precisely because they must not
     be deletable.

The third path in B4's list, max chain depth, is NOT covered here and is not built: the
3-round limit is instruction-only in `config/agents/synthesizer.md` and no code can
detect the condition, so there is no moment at which a message could be produced. See
the item for the re-homing.

Usage:
    python tests/test_degradation_paths.py
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.context_tracker as CT  # noqa: E402
from core.orchestrator import _UNAVAILABLE_CONSEQUENCE, _unavailable_notice  # noqa: E402

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


class _temp_tracker:
    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name)
        self._orig = CT.persona_data_dir
        CT.persona_data_dir = lambda persona=None: self.path
        return self.path

    def __exit__(self, *exc):
        CT.persona_data_dir = self._orig
        self._tmp.cleanup()


# --- Path 1: a specialist fails --------------------------------------------

@check("a failed specialist yields a consequence, never an exception")
def _():
    notice = _unavailable_notice("logistics")
    assert "calendar" in notice, notice
    assert "UNAVAILABLE" in notice, notice


@check("no notice names an agent, a tool, or the machinery")
def _():
    leaks = ("subagent", "specialist", "agent", "exception", "error", "traceback",
             "model", "api", "timeout", "orchestrat")
    for name in list(_UNAVAILABLE_CONSEQUENCE) + ["some_future_agent"]:
        notice = _unavailable_notice(name).lower()
        assert name.lower() not in notice, f"{name} named in its own notice"
        for leak in leaks:
            assert leak not in notice, f"{leak!r} leaked in {name}'s notice: {notice}"


@check("an unmapped specialist degrades to something vague, not to its name")
def _():
    notice = _unavailable_notice("a_brand_new_specialist")
    assert "a_brand_new_specialist" not in notice, notice
    assert "UNAVAILABLE" in notice, notice
    # No dangling "to ." from the empty consequence.
    assert " to ." not in notice and "get to ." not in notice, notice


@check("every notice forbids inventing the missing value")
def _():
    for name in _UNAVAILABLE_CONSEQUENCE:
        notice = _unavailable_notice(name)
        assert "do not guess" in notice.lower(), notice
        assert "do not invent" in notice.lower(), notice


@check("every notice forbids explaining why")
def _():
    for name in _UNAVAILABLE_CONSEQUENCE:
        assert "do not explain why" in _unavailable_notice(name).lower()


# --- Path 2: the tracker is unreadable -------------------------------------

@check("an unreadable tracker does not raise")
def _():
    with _temp_tracker():
        path = CT._tracker_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{ this is not json")
        data = CT.read_context_tracker()
        assert isinstance(data, dict), data


@check("an unreadable tracker does not read as 'nothing outstanding'")
def _():
    with _temp_tracker():
        path = CT._tracker_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{ truncated")
        data = CT.read_context_tracker()
        assert "_unavailable" in data, data
        assert "nothing outstanding" in data["_unavailable"], data["_unavailable"]


@check("a genuinely empty tracker carries no unavailable notice")
def _():
    with _temp_tracker():
        data = CT.read_context_tracker()
        assert "_unavailable" not in data, data
        assert data["open_threads"] == [], data


@check("the unavailable notice reveals no mechanism")
def _():
    with _temp_tracker():
        path = CT._tracker_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("nope")
        notice = CT.read_context_tracker()["_unavailable"].lower()
        for leak in ("json", "file", "tracker", "parse", "corrupt", "disk", "decode"):
            assert leak not in notice, f"{leak!r} leaked: {notice}"


@check("a damaged tracker is preserved before anything overwrites it")
def _():
    with _temp_tracker() as root:
        path = CT._tracker_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"clinical_threads": [{"flag": "CLINICAL_CONCERN"')  # truncated
        CT.read_context_tracker()
        kept = list(path.parent.glob(f"{path.stem}.corrupt-*{path.suffix}"))
        assert kept, f"nothing preserved in {list(path.parent.iterdir())}"
        assert "CLINICAL_CONCERN" in kept[0].read_text(), kept[0].read_text()


_CLINICAL = {"flag": "CLINICAL_CONCERN: SUICIDAL_IDEATION", "status": "watch",
             "note": "mentioned twice this week", "raised": "2026-11-01"}
_ASKED = [{"text": "Did the GP call back?", "first_asked": "2026-11-09T07:30:00",
           "last_asked": "2026-11-09T07:30:00", "ask_count": 1}]


def _seed_with_lastgood(path: Path) -> None:
    """A tracker carrying a clinical thread, then one ordinary write — so `.lastgood` exists
    the way it would on the VM, produced by the real write path rather than planted."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"open_threads": [], "clinical_threads": [_CLINICAL],
                                "asked_questions": _ASKED}))
    CT.close_scheduled_run("morning_brief")


def _assert_carried(path: Path) -> None:
    live = json.loads(path.read_text())
    flags = [t.get("flag") for t in live.get("clinical_threads") or []]
    assert _CLINICAL["flag"] in flags, f"clinical thread erased: {live}"
    texts = [q.get("text") for q in live.get("asked_questions") or []]
    assert _ASKED[0]["text"] in texts, f"asked-state erased: {live}"


def _tear(path: Path, how: str) -> None:
    if how == "zero-length":
        path.write_text("")
    elif how == "half-written":
        path.write_text(path.read_text()[:40])
    elif how == "missing":
        path.unlink()


@check("the write path also preserves before replacing a damaged file")
def _():
    with _temp_tracker():
        path = CT._tracker_path()
        _seed_with_lastgood(path)
        path.write_text('{"open_threads": ["the roof quote"')  # truncated
        CT.write_context_tracker(open_threads=["a fresh thread"],
                                 patterns=[], follow_ups=[])
        kept = list(path.parent.glob(f"{path.stem}.corrupt-*{path.suffix}"))
        assert kept, "the damaged file was replaced with no copy kept"
        assert "the roof quote" in kept[0].read_text(), kept[0].read_text()
        # And the new write did land.
        assert "a fresh thread" in path.read_text(), path.read_text()
        # Review 2026-11-05, finding 22: a copy kept aside is not survival. The clinical thread
        # and the asked-state must still be on the LIVE tracker after the write.
        _assert_carried(path)


# --- Finding 22: what is carried survives a torn, empty or missing tracker ----------

for _how in ("zero-length", "half-written", "missing"):
    @check(f"a {_how} tracker + close_scheduled_run: clinical threads survive")
    def _(how=_how):
        with _temp_tracker():
            path = CT._tracker_path()
            _seed_with_lastgood(path)
            _tear(path, how)
            CT.close_scheduled_run("evening_close")
            _assert_carried(path)

    @check(f"a {_how} tracker + write_context_tracker: clinical threads survive")
    def _(how=_how):
        with _temp_tracker():
            path = CT._tracker_path()
            _seed_with_lastgood(path)
            _tear(path, how)
            CT.write_context_tracker(open_threads=["new"], patterns=[], follow_ups=[])
            _assert_carried(path)
            assert any(t.get("flag") == _CLINICAL["flag"]
                       for t in CT.read_context_tracker()["clinical_threads"])


@check("a brand-new persona (no tracker, no .lastgood) still starts empty")
def _():
    with _temp_tracker():
        path = CT._tracker_path()
        CT.close_scheduled_run("morning_brief")
        live = json.loads(path.read_text())
        assert set(live) == {"scheduled_runs"}, live
        assert not CT._lastgood_path().exists(), "a first write has no outgoing tracker to keep"
        data = CT.read_context_tracker()
        assert data["clinical_threads"] == [] and data["open_threads"] == [], data


@check(".lastgood is a copy of the outgoing tracker; the tracker itself is never moved")
def _():
    with _temp_tracker():
        path = CT._tracker_path()
        _seed_with_lastgood(path)
        before = path.read_text()
        CT.close_scheduled_run("evening_close")
        assert path.exists() and json.loads(path.read_text()), "tracker absent after a write"
        assert CT._lastgood_path().read_text() == before, "lastgood is not the outgoing tracker"
        leftovers = [p.name for p in path.parent.iterdir() if p.name.endswith(".tmp")]
        assert not leftovers, f"temp files left behind: {leftovers}"


@check("a damaged tracker never overwrites a good .lastgood")
def _():
    with _temp_tracker():
        path = CT._tracker_path()
        _seed_with_lastgood(path)
        good = CT._lastgood_path().read_text()
        path.write_text("{ torn")
        CT.close_scheduled_run("evening_close")
        assert CT._lastgood_path().read_text() == good, "a torn tracker was kept as last-good"


@check("a readable tracker is never preserved-as-corrupt")
def _():
    with _temp_tracker():
        path = CT._tracker_path()
        CT.write_context_tracker(open_threads=["ordinary"],
                                 patterns=[], follow_ups=[])
        CT.read_context_tracker()
        kept = list(path.parent.glob(f"{path.stem}.corrupt-*{path.suffix}"))
        assert not kept, f"a healthy tracker was copied aside: {kept}"


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
