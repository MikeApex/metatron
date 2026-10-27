"""
tests/test_tts_worker.py — the Kokoro helper process (core/tts_worker.py).

Plan: archive/plans/multi_user_accounts_plan_2026-10-26.md § 4.12.2 (design), § 6.1 item 17
(these tests). Kokoro is never needed: every helper here runs with the TEST-ONLY `--fake` engine,
which is stubbed INSIDE the helper process only — the calling process runs the production code
path unchanged. Every test that starts a helper stops it in teardown; `_live_helpers` is a final
net that SIGKILLs any pid a test recorded and is still alive.

Run:  .venv/bin/python -m pytest -q tests/test_tts_worker.py
  or  .venv/bin/python tests/test_tts_worker.py
"""
from __future__ import annotations

import importlib
import json
import os
import signal
import subprocess
import sys
import textwrap
import threading
import time
import wave
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core import tts_worker  # noqa: E402
from core.tts_worker import TTSWorker, TTSWorkerError, split_sentences  # noqa: E402

IS_LINUX = sys.platform.startswith("linux")
_live_helpers: set[int] = set()


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _wait_gone(pid: int, timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _alive(pid):
            return True
        time.sleep(0.05)
    return False


def _read_wav(path: str) -> tuple[int, int, list[int]]:
    """(rate, channels, int16 samples) — via the stdlib, so 'valid wav' is not soundfile's opinion."""
    with wave.open(path, "rb") as w:
        rate, channels, width, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        assert width == 2, f"expected 16-bit PCM, got {width * 8}-bit"
        raw = w.readframes(n)
    samples = [int.from_bytes(raw[i:i + 2], "little", signed=True) for i in range(0, len(raw), 2)]
    return rate, channels, samples


def _runs(samples: list[int]) -> list[tuple[int, int]]:
    """Collapse samples into (value, run length) pairs."""
    out: list[tuple[int, int]] = []
    for s in samples:
        if out and out[-1][0] == s:
            out[-1] = (s, out[-1][1] + 1)
        else:
            out.append((s, 1))
    return out


def _speak(worker: TTSWorker, text: str) -> str:
    path = worker.synthesize(text)
    if worker.pid:
        _live_helpers.add(worker.pid)
    return path


@pytest.fixture
def worker():
    w = TTSWorker(idle_timeout_seconds=30, request_timeout_seconds=20, cold_start_extra_seconds=20,
                  fake_engine=True)
    yield w
    w.shutdown()


@pytest.fixture(autouse=True)
def _reap_strays():
    yield
    for pid in list(_live_helpers):
        if _alive(pid):
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        _live_helpers.discard(pid)


# --------------------------------------------------------------------------
# The server never imports kokoro
# --------------------------------------------------------------------------

def test_engine_check_and_synthesis_never_import_kokoro(worker):
    tts_worker.kokoro_installed()
    path = _speak(worker, "Hello there. How are you?")
    Path(path).unlink()
    assert "kokoro" not in sys.modules


def test_engine_check_finds_an_installed_kokoro_without_importing_it(tmp_path, monkeypatch):
    # A planted `kokoro` package that would record its own import: find_spec must see it
    # (True) and must not execute it — the § 4.12.4 fix, proven where kokoro IS installed.
    pkg = tmp_path / "kokoro"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("import os\nos.environ['KOKORO_WAS_IMPORTED'] = '1'\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()
    monkeypatch.delenv("KOKORO_WAS_IMPORTED", raising=False)
    assert tts_worker.kokoro_installed() is True
    assert "kokoro" not in sys.modules
    assert "KOKORO_WAS_IMPORTED" not in os.environ


# --------------------------------------------------------------------------
# Lifecycle: start once, reuse, idle exit, crash recovery, timeout
# --------------------------------------------------------------------------

def test_first_call_starts_one_helper_and_the_second_reuses_it(worker):
    assert worker.pid is None
    p1 = _speak(worker, "One.")
    pid1 = worker.pid
    p2 = _speak(worker, "Two.")
    assert pid1 is not None and worker.pid == pid1
    for p in (p1, p2):
        Path(p).unlink()


def test_helper_exits_after_idle_timeout_and_next_call_starts_fresh():
    w = TTSWorker(idle_timeout_seconds=1, fake_engine=True)
    try:
        Path(_speak(w, "Warm.")).unlink()
        pid1 = w.pid
        assert pid1 is not None
        # The helper must leave on ITS OWN timer — the point is memory returned with nobody
        # calling it. (w.pid polls, which also reaps the exited child.)
        deadline = time.monotonic() + 10
        while w.pid is not None and time.monotonic() < deadline:
            time.sleep(0.1)
        assert w.pid is None, "helper did not exit after its idle timeout"
        Path(_speak(w, "Cold again.")).unlink()
        assert w.pid is not None and w.pid != pid1
    finally:
        w.shutdown()


def test_helper_killed_mid_reply_fails_that_reply_and_next_call_recovers():
    w = TTSWorker(idle_timeout_seconds=30, request_timeout_seconds=30, fake_engine=True,
                  fake_sentence_delay=0.5)
    killed: list[int] = []

    def _kill_when_busy():
        deadline = time.monotonic() + 10
        while w.pid is None and time.monotonic() < deadline:
            time.sleep(0.02)
        time.sleep(0.6)  # inside the 10-sentence, 5 s synthesis
        pid = w.pid
        if pid:
            killed.append(pid)
            os.kill(pid, signal.SIGKILL)  # what the OOM killer does

    try:
        t = threading.Thread(target=_kill_when_busy)
        t.start()
        with pytest.raises(TTSWorkerError, match="died mid-reply"):
            _speak(w, " ".join(f"Sentence {i}." for i in range(10)))
        t.join()
        assert killed, "the helper was never seen running"
        Path(_speak(w, "Back again.")).unlink()
        assert w.pid is not None and w.pid != killed[0]
    finally:
        w.shutdown()


def test_wedged_helper_times_out_is_killed_and_next_call_recovers():
    w = TTSWorker(idle_timeout_seconds=30, request_timeout_seconds=1, cold_start_extra_seconds=0,
                  fake_engine=True, fake_sentence_delay=4)
    try:
        t0 = time.monotonic()
        with pytest.raises(TTSWorkerError, match="no reply within"):
            _speak(w, "This one hangs.")
        assert time.monotonic() - t0 < 3.5, "the timeout did not bound the call"
        assert w.pid is None, "a timed-out helper must be killed, not left holding memory"
        w.fake_sentence_delay = 0.0
        w.request_timeout = 20
        Path(_speak(w, "Fine now.")).unlink()
    finally:
        w.shutdown()


def test_shutdown_stops_the_helper(worker):
    Path(_speak(worker, "Hi.")).unlink()
    pid = worker.pid
    worker.shutdown()
    assert worker.pid is None
    assert _wait_gone(pid)
    worker.shutdown()  # idempotent


def test_module_level_api_uses_the_default_worker(monkeypatch):
    w = TTSWorker(idle_timeout_seconds=30, fake_engine=True)
    monkeypatch.setattr(tts_worker, "_default_worker", w)
    try:
        path = tts_worker.synthesize("Through the module.")
        _live_helpers.add(w.pid)
        assert Path(path).exists()
        Path(path).unlink()
    finally:
        tts_worker.shutdown()
    assert w.pid is None


def test_empty_text_is_refused_without_starting_a_helper(worker):
    with pytest.raises(TTSWorkerError, match="empty"):
        worker.synthesize("   \n ")
    assert worker.pid is None


# --------------------------------------------------------------------------
# The helper dies with the server
# --------------------------------------------------------------------------

_PARENT_SCRIPT = textwrap.dedent("""
    import sys, time
    sys.path.insert(0, {root!r})
    from pathlib import Path
    from core.tts_worker import TTSWorker
    w = TTSWorker(idle_timeout_seconds=60, request_timeout_seconds=60, fake_engine=True,
                  fake_sentence_delay={delay})
    if {busy}:
        import threading
        threading.Thread(target=lambda: w.synthesize("A. B. C. D. E. F. G. H."), daemon=True).start()
        while w.pid is None:
            time.sleep(0.02)
        time.sleep(0.5)
    else:
        Path(w.synthesize("Hello.")).unlink()
    print(w.pid, flush=True)
    time.sleep(120)
""")


def _helper_of_killed_parent(busy: bool, delay: float) -> int:
    script = _PARENT_SCRIPT.format(root=str(REPO_ROOT), busy=busy, delay=delay)
    parent = subprocess.Popen([sys.executable, "-c", script], stdout=subprocess.PIPE, text=True)
    try:
        pid = int(parent.stdout.readline().strip())
        _live_helpers.add(pid)
        assert _alive(pid)
    finally:
        parent.kill()  # SIGKILL: no cleanup code runs — the server crashing or being OOM-killed
        parent.wait()
        parent.stdout.close()
    return pid


def test_idle_helper_exits_when_the_server_is_killed():
    # Covered by EOF on the helper's stdin on every platform (and PDEATHSIG on Linux).
    pid = _helper_of_killed_parent(busy=False, delay=0.0)
    assert _wait_gone(pid, 10), "helper outlived its server"


@pytest.mark.skipif(not IS_LINUX, reason="PR_SET_PDEATHSIG is Linux-only; on macOS a BUSY helper "
                    "exits only when its current reply ends. Verified on the VM.")
def test_busy_helper_is_signalled_when_the_server_is_killed():
    # 8 sentences x 3 s: without the death signal it would live ~20 s more.
    pid = _helper_of_killed_parent(busy=True, delay=3.0)
    assert _wait_gone(pid, 3), "busy helper was not signalled when its server died"


# --------------------------------------------------------------------------
# OOM priority
# --------------------------------------------------------------------------

@pytest.mark.skipif(not IS_LINUX, reason="/proc/<pid>/oom_score_adj exists only on Linux — macOS "
                    "has no OOM killer to rank against. Verified on the VM.")
def test_helper_is_first_in_line_for_the_oom_killer(worker):
    Path(_speak(worker, "Rank me.")).unlink()
    assert Path(f"/proc/{worker.pid}/oom_score_adj").read_text().strip() == "1000"
    assert Path("/proc/self/oom_score_adj").read_text().strip() != "1000"  # never the server


# --------------------------------------------------------------------------
# Sentence by sentence, joined in order, valid wav
# --------------------------------------------------------------------------

def test_multi_sentence_reply_is_synthesised_per_sentence_and_joined_in_order(worker):
    text = ("Good morning. Your first meeting is at nine!\nAfter that, lunch with Ana? "
            "Then the gym at six… Sleep well.")
    sentences = split_sentences(text)
    assert len(sentences) == 5, sentences
    path = _speak(worker, text)
    try:
        rate, channels, samples = _read_wav(path)
    finally:
        Path(path).unlink()
    assert (rate, channels) == (24000, 1)
    # The fake engine writes sentence i as (1000 + len) samples of (i+1)/64 → int16 512*(i+1).
    assert _runs(samples) == [(512 * (i + 1), 1000 + len(s)) for i, s in enumerate(sentences)]


def test_returned_file_is_a_valid_24khz_mono_wav(worker):
    path = _speak(worker, "Just one line.")
    try:
        assert Path(path).suffix == ".wav"
        rate, channels, samples = _read_wav(path)
        assert (rate, channels) == (24000, 1) and len(samples) > 0
    finally:
        Path(path).unlink()


def test_helper_error_reply_is_reported_and_the_helper_survives():
    # The helper's request handler, run directly: an unwritable output is an error REPLY, not a
    # crash, so one bad reply never costs a cold start.
    state = {"engine": None, "fake": True, "fake_delay": 0.0}
    reply = tts_worker._handle(
        json.dumps({"id": 3, "text": "Hi.", "out": "/nonexistent-dir/x.wav"}).encode(), state)
    assert reply["id"] == 3 and reply["ok"] is False and reply["error"]
    assert "kokoro" not in sys.modules


# --------------------------------------------------------------------------
# The splitter
# --------------------------------------------------------------------------

def test_splitter_is_deterministic_and_keeps_decimals_whole():
    text = "It is 3.5 km away. Leave at 8.30! Okay?"
    assert split_sentences(text) == ["It is 3.5 km away.", "Leave at 8.30!", "Okay?"]
    assert split_sentences(text) == split_sentences(text)


def test_splitter_bounds_long_unpunctuated_text():
    run_on = " ".join(["word"] * 400)  # 1,999 chars, no sentence end
    pieces = split_sentences(run_on, max_chars=250)
    assert all(len(p) <= 250 for p in pieces)
    assert " ".join(pieces) == run_on  # nothing lost or reordered
    no_spaces = "x" * 600
    pieces = split_sentences(no_spaces, max_chars=250)
    assert [len(p) for p in pieces] == [250, 250, 100]


def test_splitter_prefers_a_clause_break():
    text = "a" * 150 + ", " + "b" * 150
    assert split_sentences(text, max_chars=250) == ["a" * 150 + ",", "b" * 150]


def test_config_supplies_the_ten_minute_idle_timeout():
    assert tts_worker.load_config()["helper_idle_timeout_minutes"] == 10
    assert TTSWorker().idle_timeout == 600


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
