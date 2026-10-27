"""
core/tts_worker.py — spoken replies (Kokoro) in a helper process, never in the server.

Why this exists (plan: archive/plans/multi_user_accounts_plan_2026-10-26.md § 3.12, § 4.12.2):
Kokoro loaded in the server process held ~1.5 GB and grew it ~115 MB per spoken reply — memory a
running Python process frees is not reliably returned to the OS — until the kernel OOM-killed the
server on the 4 GB VM, dropping whatever reply was in flight. So:

  - the server never imports `kokoro` — `kokoro_installed()` asks whether it is installed via
    `find_spec`, which does not import it (§ 4.12.4: the old check was `import kokoro` on every
    /tts, which would have pulled it straight back in);
  - the first spoken reply starts a helper process (`python -m core.tts_worker --serve`); later
    replies reuse it; after `helper_idle_timeout_minutes` (config/modules/voice.yaml) with no reply
    it exits, and a process that exits returns everything it held;
  - the helper makes itself the kernel's first OOM victim (`oom_score_adj` 1000) so a reply too
    big for the machine costs that one reply, never the server; and it dies with the server
    (`PR_SET_PDEATHSIG`, plus EOF on its stdin) so a restart never orphans 1.5 GB;
  - it synthesises a sentence at a time and joins the audio, bounding the per-reply peak that
    killed a 1.9 GB-capped test on its first long reply.

Protocol — one JSON object per line over the helper's stdin/stdout. `json.dumps` escapes every
newline inside the text, so a line is always exactly one message; both ends read raw bytes into a
buffer and split on b"\\n", so a partial read is just "not complete yet", never a torn message.
    request:  {"id": 7, "text": "...", "out": "/tmp/tmpab12.wav"}
    reply:    {"id": 7, "ok": true, "path": "/tmp/tmpab12.wav"}
              {"id": 7, "ok": false, "error": "RuntimeError: Kokoro produced no audio"}
The CALLER creates the temp wav and owns it on every path (as /tts did before): the helper only
writes into it, so a helper killed mid-reply cannot leak a file the server does not know about.
In the helper, fd 1 is re-pointed at stderr after the protocol pipe is dup'ed away, so a stray
print or warning from Kokoro/PyTorch lands in the journal instead of corrupting the protocol.

Server-side use: `synthesize(text) -> wav path` and `shutdown()`. Calls are serialised by a lock
(and /tts already runs them on its single `_TTS_EXECUTOR` worker).
"""
from __future__ import annotations

import argparse
import ctypes
import importlib.util
import json
import logging
import os
import re
import select
import signal
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "modules" / "voice.yaml"

# Exactly what core/server.py used before the move: voice af_heart, American English pipeline,
# 24 kHz wav.
KOKORO_VOICE = "af_heart"
KOKORO_LANG_CODE = "a"
SAMPLE_RATE = 24000

# A sentence longer than this is split further (clause break, else word break, else hard cut).
# The point is the per-call peak: a ≤160-word reply in ONE call pushed Kokoro over 440 MB past its
# load size (§ 3.12). ~250 characters is ~40 words — a normal long sentence passes whole.
MAX_SENTENCE_CHARS = 250

# What a missing config file or key means. config/modules/voice.yaml is the product; see it for
# why each value is what it is.
_DEFAULTS = {
    "helper_idle_timeout_minutes": 10,
    "request_timeout_seconds": 60,
    "cold_start_extra_seconds": 60,
}


class TTSWorkerError(RuntimeError):
    """A spoken reply could not be produced. The server turns this into a 500 for that reply."""


# --------------------------------------------------------------------------
# Shared by both sides
# --------------------------------------------------------------------------

def kokoro_installed() -> bool:
    """True if the `kokoro` package is installed — WITHOUT importing it (§ 4.12.4)."""
    try:
        return importlib.util.find_spec("kokoro") is not None
    except (ImportError, ValueError):
        return False


def load_config(path: Path = CONFIG_PATH) -> dict:
    """voice.yaml merged over the defaults. A broken file falls back to defaults, loudly."""
    cfg = dict(_DEFAULTS)
    try:
        import yaml
        data = yaml.safe_load(path.read_text()) or {}
        if isinstance(data, dict):
            cfg.update({k: v for k, v in data.items() if k in _DEFAULTS and v is not None})
    except FileNotFoundError:
        pass
    except Exception as exc:  # noqa: BLE001 — speech must not break on a config typo
        logger.warning("[tts] could not read %s (%s) — using defaults", path, exc)
    return cfg


_SENTENCE_BREAK = re.compile(r"(?<=[.!?…])\s+|\s*\n\s*")


def split_sentences(text: str, max_chars: int = MAX_SENTENCE_CHARS) -> list[str]:
    """
    Deterministic split into sentences, each at most `max_chars` long.

    Breaks after . ! ? … followed by whitespace, and at newlines. "3.5" and "e.g.x" do not split
    (no whitespace after the dot). Over-long pieces — a run-on reply with no punctuation — are cut
    at the last clause break (", " "; " ": ") in the back half of the window, else the last space,
    else hard at `max_chars`, so no single synthesis call is unbounded.
    """
    out: list[str] = []
    for piece in _SENTENCE_BREAK.split(text):
        piece = piece.strip()
        while len(piece) > max_chars:
            window = piece[: max_chars + 1]
            cut = max(window.rfind(", "), window.rfind("; "), window.rfind(": "))
            if cut >= max_chars // 2:
                cut += 1  # keep the punctuation with the left half
            else:
                cut = window.rfind(" ")
                if cut <= 0:
                    cut = max_chars
            head, piece = piece[:cut].strip(), piece[cut:].strip()
            if head:
                out.append(head)
        if piece:
            out.append(piece)
    return out


# --------------------------------------------------------------------------
# Server side
# --------------------------------------------------------------------------

# PR_SET_PDEATHSIG fires when the THREAD that forked the child exits, not the process (prctl(2)).
# If the helper were spawned from a short-lived thread it would be SIGTERMed the moment that
# thread finished. So every spawn goes through this one long-lived thread: ThreadPoolExecutor
# workers live until interpreter shutdown, i.e. as long as the server.
_SPAWN_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tts-helper-spawn")


class TTSWorker:
    """
    One helper process, started on demand and reused. Thread-safe; calls are serialised.

    Lifecycle: started by the first `synthesize`; reused while it lives; replaced if it died (a
    crash or an OOM kill costs the reply in flight an error — the NEXT call starts a fresh one);
    exits on its own after `idle_timeout_seconds` with no request; stopped by `shutdown()`.

    `fake_engine` (TEST-ONLY) makes the helper synthesise tones instead of importing kokoro, so
    the lifecycle can be tested on a machine without Kokoro — the stub lives only inside the
    helper; this process is the same code path production runs.
    """

    def __init__(
        self,
        idle_timeout_seconds: float | None = None,
        request_timeout_seconds: float | None = None,
        cold_start_extra_seconds: float | None = None,
        *,
        fake_engine: bool = False,
        fake_sentence_delay: float = 0.0,
    ) -> None:
        cfg = load_config()
        self.idle_timeout = float(
            idle_timeout_seconds if idle_timeout_seconds is not None
            else cfg["helper_idle_timeout_minutes"] * 60
        )
        self.request_timeout = float(
            request_timeout_seconds if request_timeout_seconds is not None
            else cfg["request_timeout_seconds"]
        )
        self.cold_start_extra = float(
            cold_start_extra_seconds if cold_start_extra_seconds is not None
            else cfg["cold_start_extra_seconds"]
        )
        self.fake_engine = fake_engine
        self.fake_sentence_delay = fake_sentence_delay
        self._lock = threading.Lock()
        self._proc: subprocess.Popen | None = None
        self._rbuf = b""
        self._last_used = 0.0
        self._next_id = 0

    @property
    def pid(self) -> int | None:
        """The live helper's pid, or None if there is none (never started, exited, or killed)."""
        proc = self._proc
        if proc is None or proc.poll() is not None:
            return None
        return proc.pid

    def synthesize(self, text: str) -> str:
        """
        Speak `text` to a 24 kHz wav and return its path. The caller deletes the file.

        Raises TTSWorkerError on any failure — empty text, an engine error, the helper dying
        mid-reply, or no reply within the timeout (the helper is then killed, so a wedged one
        cannot hold the single /tts worker; the next call starts fresh).
        """
        if not text or not text.strip():
            raise TTSWorkerError("Text is empty")
        with self._lock:
            cold = self._ensure_helper()
            timeout = self.request_timeout + (self.cold_start_extra if cold else 0.0)
            deadline = time.monotonic() + timeout

            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp.close()
            self._next_id += 1
            rid = self._next_id
            request = json.dumps({"id": rid, "text": text, "out": tmp.name}).encode() + b"\n"
            try:
                self._send(request, deadline)
                reply = json.loads(self._recv_line(deadline))
            except TimeoutError:
                self._stop(kill=True)
                Path(tmp.name).unlink(missing_ok=True)
                raise TTSWorkerError(
                    f"voice helper gave no reply within {timeout:.0f}s — stopped it; "
                    f"the next spoken reply starts a fresh one"
                ) from None
            except (EOFError, OSError, ValueError) as exc:
                rc = self._stop(kill=True)
                Path(tmp.name).unlink(missing_ok=True)
                raise TTSWorkerError(
                    f"voice helper died mid-reply ({_describe_exit(rc)}; {type(exc).__name__}) — "
                    f"the next spoken reply starts a fresh one"
                ) from None

            self._last_used = time.monotonic()  # the helper's idle clock restarted too
            if not isinstance(reply, dict) or reply.get("id") != rid:
                self._stop(kill=True)
                Path(tmp.name).unlink(missing_ok=True)
                raise TTSWorkerError(f"voice helper answered out of turn: {reply!r:.200}")
            if not reply.get("ok"):
                Path(tmp.name).unlink(missing_ok=True)
                raise TTSWorkerError(f"Kokoro failed: {reply.get('error', 'unknown error')}")
            return tmp.name

    def shutdown(self) -> None:
        """Stop the helper if one is running. Safe to call repeatedly."""
        with self._lock:
            self._stop(kill=False)

    # -- internals (all called with self._lock held) --------------------------------------------

    def _ensure_helper(self) -> bool:
        """Make sure a usable helper is running. True if one had to be started (a cold reply)."""
        proc = self._proc
        if proc is not None and proc.poll() is None:
            # The helper exits on its own idle timer, measured from just before our _last_used.
            # Reusing it in the last moments of that timer would race its exit and lose the reply,
            # so a helper that close to expiry is replaced instead. The grace is tiny next to a
            # 10-minute timeout; the helper's timer starts first, so ours never runs past it.
            grace = min(5.0, self.idle_timeout / 2)
            if time.monotonic() - self._last_used < self.idle_timeout - grace:
                return False
        if proc is not None:
            self._stop(kill=False)  # reap the one that exited, or retire the one about to
        self._start()
        return True

    def _start(self) -> None:
        cmd = [
            sys.executable, "-m", "core.tts_worker", "--serve",
            "--parent-pid", str(os.getpid()),
            "--idle-timeout", str(self.idle_timeout),
        ]
        if self.fake_engine:
            cmd += ["--fake", "--fake-sentence-delay", str(self.fake_sentence_delay)]

        def _spawn() -> subprocess.Popen:
            return subprocess.Popen(
                cmd, cwd=str(REPO_ROOT), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=None,  # inherit: the helper's log lines land in the server's journal
                bufsize=0, close_fds=True,
            )

        proc = _SPAWN_EXECUTOR.submit(_spawn).result()
        # Non-blocking pipes so a wedged helper (full pipe, no reader) cannot block the write or
        # the read past the deadline — select() bounds both.
        os.set_blocking(proc.stdin.fileno(), False)
        os.set_blocking(proc.stdout.fileno(), False)
        self._proc = proc
        self._rbuf = b""
        self._last_used = time.monotonic()
        logger.info("[tts] voice helper started (pid %d)", proc.pid)

    def _stop(self, kill: bool) -> int | None:
        """Stop and reap the helper; return its exit code (negative = killed by that signal)."""
        proc, self._proc = self._proc, None
        self._rbuf = b""
        if proc is None:
            return None
        try:
            if proc.poll() is None:
                if kill:
                    proc.kill()
                else:
                    proc.stdin.close()  # EOF: an idle helper exits cleanly at once
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=3)
        finally:
            for f in (proc.stdin, proc.stdout):
                try:
                    f.close()
                except OSError:
                    pass
        logger.info("[tts] voice helper stopped (pid %d, %s)", proc.pid,
                    _describe_exit(proc.returncode))
        return proc.returncode

    def _send(self, data: bytes, deadline: float) -> None:
        fd = self._proc.stdin.fileno()
        view = memoryview(data)
        while view:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            _, writable, _ = select.select([], [fd], [], remaining)
            if not writable:
                continue
            try:
                view = view[os.write(fd, view):]
            except BlockingIOError:
                continue

    def _recv_line(self, deadline: float) -> bytes:
        fd = self._proc.stdout.fileno()
        while b"\n" not in self._rbuf:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            readable, _, _ = select.select([fd], [], [], remaining)
            if not readable:
                continue
            try:
                chunk = os.read(fd, 65536)
            except BlockingIOError:
                continue
            if not chunk:
                raise EOFError("helper closed its output")
            self._rbuf += chunk
        line, _, self._rbuf = self._rbuf.partition(b"\n")
        return line


def _describe_exit(rc: int | None) -> str:
    if rc is None:
        return "still running"
    if rc < 0:
        name = signal.Signals(-rc).name if -rc in signal.valid_signals() else str(-rc)
        hint = " — on the VM most likely the OOM killer" if -rc == signal.SIGKILL else ""
        return f"killed by {name}{hint}"
    return f"exit code {rc}"


# The server's one worker. Built on first use so importing this module reads no config and starts
# nothing. Tests swap it: `monkeypatch.setattr(tts_worker, "_default_worker", TTSWorker(fake_engine=True))`.
_default_worker: TTSWorker | None = None
_default_lock = threading.Lock()


def _get_default() -> TTSWorker:
    global _default_worker
    with _default_lock:
        if _default_worker is None:
            _default_worker = TTSWorker()
        return _default_worker


def synthesize(text: str) -> str:
    """Server entry point: `text` → wav path (caller deletes it). Raises TTSWorkerError."""
    return _get_default().synthesize(text)


def shutdown() -> None:
    """Stop the server's helper, if any (server shutdown, tests)."""
    with _default_lock:
        worker = _default_worker
    if worker is not None:
        worker.shutdown()


# --------------------------------------------------------------------------
# Helper side (`python -m core.tts_worker --serve`) — the only place kokoro is imported
# --------------------------------------------------------------------------

def _harden(parent_pid: int) -> None:
    """First thing the helper does: become the OOM victim of choice and die with the server."""
    signal.signal(signal.SIGINT, signal.SIG_DFL)  # Ctrl-C on a foreground server: die quietly
    if sys.platform.startswith("linux"):
        # 1000 = "kill me first". Raising one's own score needs no privilege. § 4.12.2 item 3.
        try:
            Path("/proc/self/oom_score_adj").write_text("1000")
        except OSError as exc:
            print(f"[tts-helper] could not set oom_score_adj: {exc}", file=sys.stderr, flush=True)
        # SIGTERM when the server goes, even if this helper is busy synthesising and not reading
        # stdin (an idle helper also sees EOF). PR_SET_PDEATHSIG = 1.
        try:
            libc = ctypes.CDLL(None, use_errno=True)
            if libc.prctl(1, int(signal.SIGTERM), 0, 0, 0) != 0:
                raise OSError(ctypes.get_errno(), "prctl(PR_SET_PDEATHSIG) failed")
        except (OSError, AttributeError) as exc:
            print(f"[tts-helper] could not set the death signal: {exc}", file=sys.stderr, flush=True)
    # The server may have died between fork and the prctl above, in which case the signal will
    # never come: we have already been re-parented. Exit rather than idle for 10 minutes.
    if os.getppid() != parent_pid:
        sys.exit(0)


def _kokoro_engine():
    """Load Kokoro (~10 s, ~1.5 GB) and return engine(index, sentence) -> float32 audio."""
    import numpy as np
    from kokoro import KPipeline

    pipeline = KPipeline(lang_code=KOKORO_LANG_CODE)

    def engine(_index: int, sentence: str):
        chunks = [np.asarray(audio, dtype=np.float32)
                  for _gs, _ps, audio in pipeline(sentence, voice=KOKORO_VOICE)]
        return np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)

    return engine


def _fake_engine(sentence_delay: float):
    """
    TEST-ONLY stand-in for Kokoro (`--fake`). Sentence i becomes (1000 + len(sentence)) samples
    of the constant (i + 1) / 64 — exact in 16-bit PCM — so a test can read the wav back and check
    every sentence arrived, in order, at its length. Never imports kokoro.
    """
    import numpy as np

    def engine(index: int, sentence: str):
        if sentence_delay:
            time.sleep(sentence_delay)
        return np.full(1000 + len(sentence), (index + 1) / 64, dtype=np.float32)

    return engine


def _handle(line: bytes, state: dict) -> dict:
    rid = None
    try:
        req = json.loads(line)
        rid = req.get("id")
        text, out = req["text"], req["out"]
        sentences = split_sentences(text)
        if not sentences:
            raise ValueError("no text to speak")
        if state["engine"] is None:
            state["engine"] = (_fake_engine(state["fake_delay"]) if state["fake"]
                               else _kokoro_engine())

        import numpy as np
        import soundfile as sf

        # One sentence per engine call, joined in order: the per-call peak is one sentence's
        # working memory, not the whole reply's (§ 4.12.2 item 4).
        chunks = []
        for i, sentence in enumerate(sentences):
            audio = state["engine"](i, sentence)
            if audio.size:
                chunks.append(audio)
        if not chunks:
            raise RuntimeError("Kokoro produced no audio")
        sf.write(out, np.concatenate(chunks), SAMPLE_RATE)
        return {"id": rid, "ok": True, "path": out}
    except Exception as exc:  # noqa: BLE001 — one bad reply must not end the helper
        return {"id": rid, "ok": False, "error": f"{type(exc).__name__}: {exc}"}


def _serve(parent_pid: int, idle_timeout: float, fake: bool, fake_delay: float) -> int:
    # Take the protocol pipe for ourselves, then point fd 1 at stderr: anything Kokoro, PyTorch or
    # a warning prints to stdout now goes to the journal and can never corrupt a reply line.
    proto_fd = os.dup(1)
    os.dup2(2, 1)
    _harden(parent_pid)

    state = {"engine": None, "fake": fake, "fake_delay": fake_delay}
    buf = b""
    while True:
        while b"\n" not in buf:
            readable, _, _ = select.select([0], [], [], idle_timeout)
            if not readable:
                return 0  # idle: exit, and every byte goes back to the OS
            chunk = os.read(0, 65536)
            if not chunk:
                return 0  # the server closed our stdin, or died
            buf += chunk
        line, _, buf = buf.partition(b"\n")
        reply = json.dumps(_handle(line, state)).encode() + b"\n"
        view = memoryview(reply)
        try:
            while view:
                view = view[os.write(proto_fd, view):]
        except BrokenPipeError:
            return 0  # the server is gone


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Kokoro speech helper (started by the server).")
    parser.add_argument("--serve", action="store_true", required=True)
    parser.add_argument("--parent-pid", type=int, required=True)
    parser.add_argument("--idle-timeout", type=float, required=True, help="seconds")
    parser.add_argument("--fake", action="store_true", help="TEST-ONLY: tones instead of Kokoro")
    parser.add_argument("--fake-sentence-delay", type=float, default=0.0, help="TEST-ONLY")
    args = parser.parse_args(argv)
    return _serve(args.parent_pid, args.idle_timeout, args.fake, args.fake_sentence_delay)


if __name__ == "__main__":
    sys.exit(main())
