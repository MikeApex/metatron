"""
tests/test_one_model_copy.py — one copy of each model on the whole VM (plan § 4.12.3, § 6.1.18).

What a per-user scheduler must never do is load the embedding model (~0.9 GB, kept for the
life of the process — review M1). This covers the client side of that:

1. `tools/baselines.py` and `core/memory.py` hand back the SAME model object in one process —
   baselines used to keep a second copy.
2. With METATRON_NO_LOCAL_MODELS=1, `index_entry` goes to `/internal/index` and `search_memory`
   to `/internal/search`, carrying the persona resolved on the calling thread, and
   `_get_model()` raises instead of loading — including from the `_local` functions the
   server's routes call, so a misconfigured server fails rather than calling itself.
3. Without the variable, index and search run locally exactly as before and never touch HTTP.
4. `run_internal_session` posts the right body to `/internal/session` with a service token and
   raises on anything but 200.

No network and no real model: `sentence_transformers` is replaced in `sys.modules` by a stub
whose constructor is counted, and `urllib.request.urlopen` / `post_internal` are stubbed.
The server-side routes are the lead session's (core/server.py) and are not exercised here.

Run:
    python -m pytest tests/test_one_model_copy.py -q
    python tests/test_one_model_copy.py            # standalone, no pytest needed
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import ssl
import sys
import tempfile
import threading
import types
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Before any core import: core.auth derives its signing key from this and loads .env only
# with setdefault, so the test value wins over whatever the checkout's .env holds.
os.environ["METATRON_AUTH_PASSWORD"] = "test-password-not-the-real-one"

import numpy as np  # noqa: E402

from core import auth, memory, remote_client  # noqa: E402
from core.persona import PersonaError, persona_scope  # noqa: E402
from tools import baselines  # noqa: E402

PERSONA = "danny_park"   # a tracked synthetic persona; nothing here writes to its data dir
DIM = 384


# --- stubs ------------------------------------------------------------------

class _StubSentenceTransformer:
    """Stands in for the real model. Counts constructions; encodes deterministically."""
    constructed = 0

    def __init__(self, name: str) -> None:
        type(self).constructed += 1
        self.name = name

    def encode(self, texts, convert_to_numpy=True, normalize_embeddings=True):
        out = np.zeros((len(texts), DIM), dtype="float32")
        for i, t in enumerate(texts):
            out[i, sum(map(ord, t)) % DIM] = 1.0   # unit vector: identical text → score 1.0
        return out


_stub_module = types.ModuleType("sentence_transformers")
_stub_module.SentenceTransformer = _StubSentenceTransformer
sys.modules["sentence_transformers"] = _stub_module


@contextlib.contextmanager
def _env(**values):
    """Set (str) or remove (None) environment variables for the block."""
    saved = {k: os.environ.get(k) for k in values}
    try:
        for k, v in values.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@contextlib.contextmanager
def _patch(obj, name, value):
    saved = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, saved)


def _fresh_model_state():
    memory._model = None
    _StubSentenceTransformer.constructed = 0


def _no_local():
    return _env(**{memory.NO_LOCAL_MODELS_ENV: "1"})


def _local():
    return _env(**{memory.NO_LOCAL_MODELS_ENV: None})


class _Recorder:
    """Stands in for remote_client.post_internal."""

    def __init__(self, reply=None):
        self.calls: list[dict] = []
        self.reply = reply if reply is not None else {"ok": True}

    def __call__(self, path, body, timeout, server=None, insecure=True):
        self.calls.append({"path": path, "body": body, "timeout": timeout,
                           "thread": threading.current_thread().name})
        return self.reply


def _refuse_http(*_a, **_k):
    raise AssertionError("HTTP was called in a process that should have run locally")


def _refuse_local(*_a, **_k):
    raise AssertionError("the local FAISS files were touched in a model-free process")


# --- 1. one embedder per process --------------------------------------------

def test_baselines_and_memory_share_one_model_object():
    with _local():
        _fresh_model_state()
        a = memory._get_model()
        b = baselines._get_model()
        assert a is b, "tools/baselines.py holds a second copy of the embedding model"
        assert _StubSentenceTransformer.constructed == 1
        assert a.name == memory._MODEL_NAME
        # baselines' own embed path goes through the shared object too.
        vec = baselines._embed("rest day")
        assert len(vec) == DIM and _StubSentenceTransformer.constructed == 1


def test_baselines_has_no_private_model_slot():
    """The old module-level `_model` is gone, so nothing can quietly repopulate it."""
    assert not hasattr(baselines, "_model")


# --- 2. a model-free process ------------------------------------------------

def test_get_model_raises_when_models_disabled():
    with _no_local():
        _fresh_model_state()
        for fn in (memory._get_model, baselines._get_model):
            try:
                fn()
            except RuntimeError as exc:
                assert memory.NO_LOCAL_MODELS_ENV in str(exc)
            else:
                raise AssertionError(f"{fn.__module__}._get_model loaded a model")
        assert _StubSentenceTransformer.constructed == 0
        assert memory._model is None


def test_get_model_raises_even_if_already_loaded():
    """The guard is the env, not the cache: a process that set it late still refuses."""
    with _local():
        _fresh_model_state()
        memory._get_model()
    with _no_local():
        try:
            memory._get_model()
        except RuntimeError:
            pass
        else:
            raise AssertionError("_get_model returned a model with the variable set")


def test_index_entry_delegates_with_persona_and_payload():
    rec = _Recorder()
    with _no_local(), _patch(remote_client, "post_internal", rec), \
            _patch(memory, "_memory_lock", _refuse_local), \
            _patch(memory, "_load_index", _refuse_local):
        _fresh_model_state()
        with persona_scope(PERSONA):
            memory.index_entry(text="slept 7h, ran 5k", source="log", entry_date="2026-10-27")
    assert len(rec.calls) == 1
    call = rec.calls[0]
    assert call["path"] == "/internal/index"
    assert call["body"] == {"persona": PERSONA, "text": "slept 7h, ran 5k",
                            "source": "log", "entry_date": "2026-10-27"}
    assert call["timeout"] == memory._REMOTE_INDEX_TIMEOUT_SECONDS
    assert json.loads(json.dumps(call["body"])) == call["body"]   # plain JSON
    assert _StubSentenceTransformer.constructed == 0


def test_index_entry_resolves_date_and_persona_on_the_calling_thread():
    """
    The real call site: tools/logger.py's worker thread, inside persona_scope. The persona
    must come from THAT thread's binding, and an empty date becomes the caller's today.
    """
    from datetime import date
    rec = _Recorder()
    errors: list[BaseException] = []

    def _worker():
        try:
            with persona_scope(PERSONA):
                memory.index_entry(text="journal line", source="journal")
        except BaseException as exc:   # surfaced below
            errors.append(exc)

    with _no_local(), _patch(remote_client, "post_internal", rec):
        t = threading.Thread(target=_worker, name="background_0")
        t.start()
        t.join(10)
    assert not errors, errors
    assert rec.calls[0]["thread"] == "background_0"
    assert rec.calls[0]["body"]["persona"] == PERSONA
    assert rec.calls[0]["body"]["entry_date"] == date.today().isoformat()


def test_index_entry_skips_empty_text_without_a_call():
    rec = _Recorder()
    with _no_local(), _patch(remote_client, "post_internal", rec):
        with persona_scope(PERSONA):
            memory.index_entry(text="   ", source="log")
    assert rec.calls == []


def test_unresolvable_persona_fails_closed_before_any_call():
    import core.persona as persona_mod
    rec = _Recorder()

    def _no_persona(*_a, **_k):
        raise PersonaError("no persona bound")

    with _no_local(), _patch(remote_client, "post_internal", rec), \
            _patch(persona_mod, "resolve_persona", _no_persona):
        for call in (lambda: memory.index_entry("x", "log", "2026-10-27"),
                     lambda: memory.search_memory("x")):
            try:
                call()
            except PersonaError:
                pass
            else:
                raise AssertionError("delegated with no persona")
    assert rec.calls == []


def test_search_memory_delegates_and_returns_results():
    hits = [{"text": "ran 5k", "source": "log", "date": "2026-10-20", "score": 0.83}]
    rec = _Recorder(reply={"results": hits})
    with _no_local(), _patch(remote_client, "post_internal", rec), \
            _patch(memory, "_memory_lock", _refuse_local):
        _fresh_model_state()
        with persona_scope(PERSONA):
            got = memory.search_memory("running", k=3)
    assert got == hits
    call = rec.calls[0]
    assert call["path"] == "/internal/search"
    assert call["body"] == {"persona": PERSONA, "query": "running", "k": 3}
    assert call["timeout"] == memory._REMOTE_SEARCH_TIMEOUT_SECONDS
    assert _StubSentenceTransformer.constructed == 0


def test_search_memory_tool_wrapper_also_delegates():
    """tools/memory_tool.py is what the orchestrator actually dispatches."""
    from tools import memory_tool
    rec = _Recorder(reply={"results": []})
    with _no_local(), _patch(remote_client, "post_internal", rec):
        with persona_scope(PERSONA):
            assert memory_tool.search_memory("anything", k=2) == []
    assert rec.calls[0]["path"] == "/internal/search"


def test_search_memory_rejects_a_malformed_reply():
    rec = _Recorder(reply={"response": "not results"})
    with _no_local(), _patch(remote_client, "post_internal", rec):
        with persona_scope(PERSONA):
            try:
                memory.search_memory("q")
            except remote_client.InternalCallError as exc:
                assert exc.path == "/internal/search"
            else:
                raise AssertionError("a reply with no results list was accepted")


def test_local_functions_never_delegate():
    """
    What the server's routes call. Under the variable they must raise (no model) rather
    than POST to /internal/* — a server that called itself would hold a thread per hop.
    """
    rec = _Recorder()
    with _no_local(), _patch(remote_client, "post_internal", rec):
        _fresh_model_state()
        with tempfile.TemporaryDirectory() as tmp, \
                _patch(memory, "_memory_dir", lambda: Path(tmp)):
            for call in (lambda: memory.index_entry_local("x", "log", "2026-10-27"),
                         lambda: _seed_and_search(Path(tmp))):
                try:
                    call()
                except RuntimeError as exc:
                    assert memory.NO_LOCAL_MODELS_ENV in str(exc)
                else:
                    raise AssertionError("a _local function ran without a model")
    assert rec.calls == []


def _seed_and_search(mem_dir: Path):
    """search_memory_local only embeds when the index is non-empty — seed one entry."""
    faiss = memory._get_faiss()
    index = faiss.IndexFlatIP(DIM)
    index.add(np.ones((1, DIM), dtype="float32") / np.sqrt(DIM))
    with _local():
        memory._save_index(index, [{"text": "seed", "source": "log", "date": "2026-10-01"}])
    return memory.search_memory_local("seed", k=1)


# --- 3. without the variable nothing changes ---------------------------------

def test_without_the_variable_index_and_search_run_locally():
    with _local(), _patch(remote_client, "post_internal", _refuse_http), \
            tempfile.TemporaryDirectory() as tmp, \
            _patch(memory, "_memory_dir", lambda: Path(tmp)):
        _fresh_model_state()
        memory.index_entry(text="long walk by the river", source="log", entry_date="2026-10-26")
        memory.index_entry(text="quarterly taxes filed", source="journal", entry_date="2026-10-27")
        got = memory.search_memory("long walk by the river", k=1)
        assert got and got[0]["text"] == "long walk by the river"
        assert got[0]["source"] == "log" and got[0]["date"] == "2026-10-26"
        assert abs(got[0]["score"] - 1.0) < 1e-5
        assert (Path(tmp) / "metadata.json").exists() and (Path(tmp) / "index.faiss").exists()
        assert _StubSentenceTransformer.constructed == 1


def test_flag_values():
    for v, want in (("1", True), ("true", True), ("yes", True),
                    ("0", False), ("", False), (None, False)):
        with _env(**{memory.NO_LOCAL_MODELS_ENV: v}):
            assert memory.models_disabled_here() is want, v


# --- 4. the /internal/session client -----------------------------------------

class _FakeResponse:
    def __init__(self, body: dict, status: int = 200):
        self._raw = json.dumps(body).encode()
        self.status = status

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _UrlopenRecorder:
    def __init__(self, result):
        self.result = result
        self.requests: list = []

    def __call__(self, req, timeout=None, context=None):
        self.requests.append({"req": req, "timeout": timeout, "context": context})
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


def test_internal_session_sends_body_and_service_auth():
    fake = _UrlopenRecorder(_FakeResponse({"response": "Weekly patterns: sleep is up."}))
    with _patch(urllib.request, "urlopen", fake):
        out = remote_client.run_internal_session("pattern_miner", "Run the weekly review.",
                                                 PERSONA)
    assert out == "Weekly patterns: sleep is up."
    sent = fake.requests[0]
    req = sent["req"]
    assert req.get_method() == "POST"
    assert req.full_url == remote_client.DEFAULT_SERVER.rstrip("/") + "/internal/session"
    assert json.loads(req.data) == {"agent": "pattern_miner", "input": "Run the weekly review.",
                                    "persona": PERSONA, "proactive": True}
    assert req.get_header("Content-type") == "application/json"
    bearer = req.get_header("Authorization")
    assert bearer and bearer.startswith("Bearer ")
    identity = auth.decode_token(bearer[len("Bearer "):])
    assert identity is not None and identity.role == "service" and identity.persona is None
    assert sent["timeout"] == remote_client.INTERNAL_SESSION_TIMEOUT_SECONDS == 900.0
    # Same TLS handling as send_one: Tailscale cert, not verified by hostname.
    assert isinstance(sent["context"], ssl.SSLContext)
    assert sent["context"].verify_mode == ssl.CERT_NONE


def _http_error(code: int, detail: str):
    return urllib.error.HTTPError(
        "https://x/internal/session", code, "err", {},
        io.BytesIO(json.dumps({"detail": detail}).encode()),
    )


def test_internal_session_raises_on_non_200():
    for code in (400, 403, 500, 503):
        fake = _UrlopenRecorder(_http_error(code, f"boom {code}"))
        with _patch(urllib.request, "urlopen", fake):
            try:
                remote_client.run_internal_session("physical_health", "review", PERSONA)
            except remote_client.InternalCallError as exc:
                assert exc.status == code and exc.path == "/internal/session"
                assert f"boom {code}" in str(exc)
            else:
                raise AssertionError(f"HTTP {code} did not raise")


def test_internal_session_raises_when_server_unreachable():
    fake = _UrlopenRecorder(urllib.error.URLError("connection refused"))
    with _patch(urllib.request, "urlopen", fake):
        try:
            remote_client.run_internal_session("pattern_miner", "go", PERSONA)
        except remote_client.InternalCallError as exc:
            assert exc.status == 0
        else:
            raise AssertionError("an unreachable server did not raise")


def test_internal_session_raises_on_a_reply_without_text():
    fake = _UrlopenRecorder(_FakeResponse({"detail": "odd"}))
    with _patch(urllib.request, "urlopen", fake):
        try:
            remote_client.run_internal_session("pattern_miner", "go", PERSONA)
        except remote_client.InternalCallError:
            pass
        else:
            raise AssertionError("a reply with no response text was accepted")


def test_post_internal_carries_index_and_search_bodies_over_https():
    """End to end through the real post_internal, not the stub: route, auth, timeout."""
    fake = _UrlopenRecorder(_FakeResponse({"results": []}))
    with _no_local(), _patch(urllib.request, "urlopen", fake):
        with persona_scope(PERSONA):
            memory.search_memory("q", k=4)
            fake.result = _FakeResponse({"ok": True})
            memory.index_entry("t", "log", "2026-10-27")
    paths = [r["req"].full_url.rsplit(":8001", 1)[-1] for r in fake.requests]
    assert paths == ["/internal/search", "/internal/index"]
    assert [r["timeout"] for r in fake.requests] == [
        memory._REMOTE_SEARCH_TIMEOUT_SECONDS, memory._REMOTE_INDEX_TIMEOUT_SECONDS]
    for r in fake.requests:
        assert auth.decode_token(r["req"].get_header("Authorization")[7:]).role == "service"
        assert json.loads(r["req"].data)["persona"] == PERSONA


if __name__ == "__main__":
    failures = []
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except Exception as exc:
                failures.append((name, exc))
                print(f"  FAIL  {name}: {exc!r}")
    print()
    if failures:
        print(f"{len(failures)} failed")
        sys.exit(1)
    print("all passed")
