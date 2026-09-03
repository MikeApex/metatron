"""
core/server.py — FastAPI server for the phone PWA.

Exposes the orchestrator over HTTPS when a cert is present in certs/, HTTP otherwise
(see __main__ below). The PWA (static/index.html) uses Web Speech API for STT/TTS on
the phone and calls this server for the actual model inference.

Run:
    python core/server.py --persona <name>
    python core/server.py --persona <name> --provider openai --port 8000

In production the VM serves HTTPS on 8001 behind a Tailscale cert:
    https://metatron-vm.tail0acc5d.ts.net:8001

For local dev without a cert, open http://<your-laptop-ip>:8000 on your phone (same
WiFi network). Find your IP: System Settings → Wi-Fi → Details, or `ipconfig getifaddr en0`.
Note Android Chrome blocks the mic on plain HTTP — see the cert hint printed at startup.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import tempfile
import threading
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import aiosqlite
import edge_tts
from fastapi import (FastAPI, File, HTTPException, Request, Response, UploadFile, WebSocket,
                     WebSocketDisconnect)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core import attachments as attachments_mod
from core import auth
from core.orchestrator import run_pipeline_session_stream, run_session
from core.persona import persona_data_dir

KOKORO_VOICE = "af_heart"
KOKORO_SPEAK = Path(__file__).parent.parent / "tools" / "kokoro" / "speak.py"
KOKORO_PYTHON = Path(__file__).parent.parent / ".venv" / "bin" / "python"
EDGE_VOICE = "en-US-JennyNeural"

logger = logging.getLogger(__name__)

app = FastAPI(title="Life Manager")

# Read at module import time from env var set before uvicorn.run()
DEFAULT_PERSONA: str | None = os.environ.get("SERVER_PERSONA") or None

DB_PATH = Path(__file__).parent.parent / "data" / "conversations" / "metatron.db"

# Refuse to start unauthenticated. Module level rather than __main__, so the guard holds
# however the app is launched (uvicorn core.server:app, a test import, anything).
auth.require_configured()

# Origins allowed to call this server cross-origin. The PWA is served same-origin and
# needs none of this; the Android app is the reason it exists — Capacitor serves the
# WebView from https://localhost and calls the VM cross-origin.
#
# allow_origins=["*"] is gone: a wildcard is incompatible with allow_credentials=True
# (browsers reject the combination outright), and "local network only" stopped being
# true the day the VM went up.
_DEFAULT_ORIGINS = [
    "https://localhost",
    "http://localhost",
    "capacitor://localhost",
    "https://metatron-vm.tail0acc5d.ts.net:8001",
]
ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get("METATRON_ALLOWED_ORIGINS", "").split(",") if o.strip()
] or _DEFAULT_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent.parent / "static"


@app.middleware("http")
async def require_auth(request: Request, call_next):
    """
    Gate every HTTP endpoint except the app shell and /auth/login.

    Deliberately a middleware rather than a per-endpoint dependency: the failure mode
    being closed off is an endpoint that nobody remembered to protect, and a middleware
    is the only version of this that cannot be forgotten when the next route is added.

    Does NOT cover /ws — Starlette never runs HTTP middleware for a WebSocket
    handshake. That path is gated inside the endpoint; see websocket_endpoint().
    """
    # CORS preflight carries no credentials by design; let CORSMiddleware answer it.
    if request.method == "OPTIONS" or auth.is_open_path(request.url.path):
        return await call_next(request)

    token = auth.credential_from_headers(
        request.headers.get("authorization"),
        request.cookies.get(auth.COOKIE_NAME),
    )
    if not auth.verify_token(token):
        return JSONResponse({"detail": "Authentication required."}, status_code=401)
    return await call_next(request)


class LoginRequest(BaseModel):
    password: str


@app.post("/auth/login")
async def auth_login(req: LoginRequest, response: Response) -> dict:
    """
    Exchange the shared password for a session token.

    Returns the token in the body *and* sets it as a cookie. Both carry the same value:
    the cookie serves the same-origin browser, the body serves the Android app, which is
    cross-origin and so never receives a SameSite=Lax cookie.
    """
    if not auth.check_password(req.password):
        # Awaited here rather than inside check_password so the delay never blocks the
        # event loop for other requests.
        delay = auth.failure_delay()
        if delay:
            await asyncio.sleep(delay)
        raise HTTPException(status_code=401, detail="Incorrect password.")

    token = auth.issue_token()
    response.set_cookie(
        auth.COOKIE_NAME, token,
        httponly=True,      # unreachable from JS, so an XSS in the PWA cannot lift it
        secure=True,        # HTTPS only — the VM serves behind a Tailscale cert
        samesite="lax",
        max_age=auth.TOKEN_TTL_SECONDS,
        path="/",
    )
    return {"token": token, "expires_in": auth.TOKEN_TTL_SECONDS}


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class SessionRequest(BaseModel):
    input: str
    agent: str = "coordinator"
    persona: str | None = None
    provider: str | None = None   # None = auto-routed via routing.yaml


class SessionResponse(BaseModel):
    response: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

_CONV_LOCK = threading.Lock()
# Per-persona rolling conversation history — last 5 turns (10 entries) for Synthesizer context.
_session_history: dict[str, list[dict]] = {}

_active_lock = threading.Lock()
_active_streams: int = 0

# Dedicated single-worker pools, deliberately NOT run_in_executor(None, ...).
# The default pool is shared with the LLM producer threads; speech work spawning
# its own native thread pools alongside them on 2 vCPUs is worse than
# serialising. One worker each also means a long job cannot starve the other.
_STT_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="stt")
_TTS_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tts")
_STT_SEMAPHORE = asyncio.Semaphore(1)
# Memory indexing is best-effort and nothing waits on its result, but it ran
# synchronously inside write_log/write_journal — on the user's critical path.
_INDEX_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="index")


# --------------------------------------------------------------------------
# TEMPORARY DIAGNOSTIC — the doubled reply, [DB-0810-01], reopened 2026-08-18.
#
# Mike sees one bubble with the text repeated, copies identical, intermittently,
# clearing on an app restart. FOUR causal explanations have been proposed and all
# four are dead — two devices rendering, a superseded socket rendering (every
# client handler carries `sock !== ws`), the `exclude=websocket` identity check
# (measured synthetically: two sockets, one message, exactly one chunk each), and
# leftover accumulated text (that yields two DIFFERENT texts; his are identical).
# Do not add a fifth theory.
#
# This answers one question and it is the decisive one: DID THE SERVER SEND IT
# TWICE? Every outbound frame is logged with the socket it went to and which of
# the two emit paths sent it — `_send_to_sender` (the socket that asked) or
# `broadcast` (every other socket for that persona). If a real turn shows one
# chunk run, the fault is client-side and half the search space is gone. If it
# shows two, it is found.
#
# Deliberately server-side rather than in static/index.html: a client-side buffer
# would ship an architecture-disclosure surface to every user in the product
# itself, which is what filter_output and the B1 disclosure suite exist to
# prevent. Mike's call, 2026-08-19. The one thing this cannot see is a fault
# inside the Android WebView; if the server provably sent one copy and the bug
# persists, that is when client visibility becomes worth its cost — as a debug
# build, not the shipped page.
#
# Content-free by construction: socket id, frame type, exchange id, and for a
# chunk its LENGTH. No message text. Same discipline as tools/analytics.py.
#
# REMOVE once the bug is diagnosed. Read it at /monitor/ws_frames.
_WS_FRAME_LOG: deque = deque(maxlen=2000)
_ws_socket_ids: dict[int, int] = {}
_ws_socket_seq = 0


def _ws_sock_id(ws: WebSocket) -> int:
    """Stable small integer per socket, so a frame can be attributed to one."""
    global _ws_socket_seq
    key = id(ws)
    if key not in _ws_socket_ids:
        _ws_socket_seq += 1
        _ws_socket_ids[key] = _ws_socket_seq
    return _ws_socket_ids[key]


def _log_ws_frame(ws: WebSocket, path: str, payload: dict) -> None:
    text = payload.get("text")
    _WS_FRAME_LOG.append({
        "t": datetime.now().isoformat(timespec="milliseconds"),
        "sock": _ws_sock_id(ws),
        "path": path,                       # "sender" | "broadcast"
        "type": payload.get("type", "?"),
        "exchange_id": payload.get("exchange_id", ""),
        "len": len(text) if isinstance(text, str) else None,
    })


class ConnectionManager:
    def __init__(self) -> None:
        self.active: dict[str, set[WebSocket]] = {}

    async def connect(self, ws: WebSocket, persona: str) -> None:
        """
        Join an already-accepted socket to a persona's broadcast group.

        The caller accepts the socket, not this method: the auth handshake has to
        exchange frames before the connection is trusted, and a socket must be accepted
        before it can carry a frame. Registering here — after that check — is what keeps
        an unauthenticated socket out of the broadcast group.
        """
        self.active.setdefault(persona, set()).add(ws)

    def disconnect(self, ws: WebSocket, persona: str) -> None:
        self.active.get(persona, set()).discard(ws)

    async def broadcast(self, persona: str, payload: dict, exclude: WebSocket | None = None) -> None:
        for ws in list(self.active.get(persona, set())):
            if ws is exclude:
                continue
            try:
                _log_ws_frame(ws, "broadcast", payload)   # TEMPORARY — [DB-0810-01]
                await ws.send_json(payload)
            except Exception:
                self.active.get(persona, set()).discard(ws)


manager = ConnectionManager()


def _log_conversation(user_input: str, response: str, agent: str, persona: str | None,
                      proactive: bool = False) -> None:
    """Append a verbatim exchange to the daily conversation log."""
    import json as _json
    from datetime import datetime
    # Per-persona: matches what _conversation_dir() (the monitoring reader) has
    # always expected. Previously writes went to a shared data/conversations/
    # that nothing read, so The Book fell back to the global path.
    log_dir = persona_data_dir(persona) / "conversations"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"
    with _CONV_LOCK:
        # Count existing entries to assign a per-day sequential ID (1-indexed)
        existing = 0
        if log_file.exists():
            with open(log_file) as _f:
                for line in _f:
                    if line.strip():
                        existing += 1
        seq = f"{existing + 1:03d}"
        entry = {
            "ts": datetime.now().isoformat(),
            "seq": seq,
            "agent": agent,
            "persona": persona,
            "proactive": proactive,
            "user": user_input,
            "response": response,
        }
        with open(log_file, "a") as f:
            f.write(_json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# SQLite persistence — shared conversation history across devices
# ---------------------------------------------------------------------------

async def _init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS exchanges (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                exchange_id TEXT UNIQUE NOT NULL,
                persona     TEXT NOT NULL,
                user        TEXT NOT NULL,
                assistant   TEXT NOT NULL,
                ts          TEXT NOT NULL
            )
        """)
        # Added after the table shipped, so tolerate an existing DB.
        try:
            await db.execute("ALTER TABLE exchanges ADD COLUMN proactive INTEGER DEFAULT 0")
        except Exception:
            pass  # column already present
        # JSON metadata for files the user attached to this turn, so history and
        # catch-up can redraw their chips without opening the files.
        try:
            await db.execute("ALTER TABLE exchanges ADD COLUMN attachments TEXT")
        except Exception:
            pass  # column already present

        # The index of stored files. The JSON sidecar written beside each file is the
        # human-readable record; this is what makes an id lookup O(1) at send time and
        # on download, instead of a walk over every dated directory.
        await db.execute("""
            CREATE TABLE IF NOT EXISTS attachments (
                id          TEXT PRIMARY KEY,
                persona     TEXT NOT NULL,
                path        TEXT NOT NULL,
                mime        TEXT NOT NULL,
                name        TEXT NOT NULL,
                size        INTEGER NOT NULL,
                ts          TEXT NOT NULL,
                exchange_id TEXT
            )
        """)
        await db.commit()


async def _load_history_from_db(persona: str) -> list[dict]:
    """Return last 10 exchanges as {role, content} pairs for orchestrator context."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT user, assistant FROM exchanges WHERE persona=? ORDER BY id DESC LIMIT 10",
            (persona,),
        ) as cursor:
            rows = await cursor.fetchall()
    pairs: list[dict] = []
    for row in reversed(rows):
        pairs.append({"role": "user", "content": row["user"]})
        pairs.append({"role": "assistant", "content": row["assistant"]})
    return pairs


def _row_with_attachments(row) -> dict:
    """Decode an exchange row's attachment JSON into the list the client expects."""
    out = dict(row)
    raw = out.pop("attachments", None)
    try:
        out["attachments"] = json.loads(raw) if raw else []
    except (TypeError, ValueError):
        out["attachments"] = []
    return out


async def _get_recent_exchanges(persona: str, limit: int = 20) -> list[dict]:
    """Return last `limit` exchanges as dicts for WS history message."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, exchange_id, user, assistant, ts, attachments, "
            "COALESCE(proactive,0) AS proactive FROM exchanges "
            "WHERE persona=? ORDER BY id DESC LIMIT ?",
            (persona, limit),
        ) as cursor:
            rows = await cursor.fetchall()
    return [_row_with_attachments(r) for r in reversed(rows)]


async def _catchup_since(persona: str, since_id: int) -> list[dict]:
    """Return exchanges with id > since_id, oldest first."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, exchange_id, user, assistant, ts, attachments, "
            "COALESCE(proactive,0) AS proactive FROM exchanges "
            "WHERE persona=? AND id > ? ORDER BY id ASC",
            (persona, since_id),
        ) as cursor:
            rows = await cursor.fetchall()
    return [_row_with_attachments(r) for r in rows]


async def _save_exchange(persona: str, exchange_id: str, user: str, assistant: str,
                         proactive: bool = False,
                         attachments: list[dict] | None = None) -> int:
    """Persist a completed exchange. Returns the new row id."""
    ts = datetime.utcnow().isoformat() + "Z"
    meta = json.dumps(_public_attachments(attachments)) if attachments else None
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT OR IGNORE INTO exchanges "
            "(exchange_id, persona, user, assistant, ts, proactive, attachments) "
            "VALUES (?,?,?,?,?,?,?)",
            (exchange_id, persona, user, assistant, ts, 1 if proactive else 0, meta),
        )
        await db.commit()
        return cursor.lastrowid or 0


# ---------------------------------------------------------------------------
# Attachments — user-supplied photos and documents
# ---------------------------------------------------------------------------

def _public_attachments(records: list[dict] | None) -> list[dict]:
    """
    Strip a stored record down to what a client may see.

    The on-disk path never crosses the wire. Downloads resolve the id against the
    database instead, so the filesystem layout is not something a client can name.
    """
    return [
        {"id": r["id"], "mime": r["mime"], "name": r["name"], "size": r["size"]}
        for r in (records or [])
    ]


async def _insert_attachment(record: dict) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO attachments "
            "(id, persona, path, mime, name, size, ts, exchange_id) "
            "VALUES (?,?,?,?,?,?,?,NULL)",
            (record["id"], record["persona"], record["path"], record["mime"],
             record["name"], record["size"], record["ts"]),
        )
        await db.commit()


async def _get_attachment(attachment_id: str, persona: str) -> dict | None:
    """
    Look up one stored file, scoped to the persona that uploaded it.

    Scoping is the access check: personas are separate users' universes, so an id
    from one is simply not found in another rather than being refused informatively.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM attachments WHERE id=? AND persona=?",
            (attachment_id, persona),
        ) as cursor:
            row = await cursor.fetchone()
    return dict(row) if row else None


async def _resolve_attachments(ids: list, persona: str) -> list[dict]:
    """
    Turn the ids in a `send` frame into stored records, dropping anything unknown.

    Silently dropping rather than erroring: an id that does not resolve is either a
    stale client or someone guessing, and in both cases the useful behaviour is to
    answer the text of the message rather than fail the whole turn.
    """
    resolved: list[dict] = []
    for raw in list(ids)[:attachments_mod.MAX_FILES_PER_MESSAGE]:
        if not isinstance(raw, str):
            continue
        record = await _get_attachment(raw, persona)
        if record:
            resolved.append(record)
    # Count is not the binding limit — total bytes is, against the model's inline
    # request ceiling. See core/attachments.cap_for_message().
    return attachments_mod.cap_for_message(resolved)


async def _recent_attachments(persona: str, exclude_ids: set[str]) -> list[dict]:
    """
    The persona's stored files that a later turn could still refer back to.

    Scoped to the persona rather than to a conversation id because this server has
    no such id: `_session_history` is one running conversation per persona, so the
    persona *is* the conversation and the carry TTL is what bounds the window.

    Ordered newest first and read only a few rows deep — `attachments_mod.carryable()`
    applies the TTL and the caps, so the query has to do no more than avoid dragging
    the whole table into memory to find the last two files.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM attachments WHERE persona=? ORDER BY ts DESC LIMIT 20",
            (persona,),
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(r) for r in rows if r["id"] not in exclude_ids]


async def _revive_attachments(persona: str, user_input: str,
                              fresh: list[dict]) -> list[dict]:
    """
    Files the user sent earlier and is now referring to, ready to re-enter the turn.

    This is the answer to "use the PDF I gave you": the bytes were always on disk,
    but nothing addressed them once the client stopped re-sending their ids. The
    match is made on the user's own words (core/attachments.references_earlier_files),
    and the result joins the same attachment list a fresh upload uses — one path into
    the prompt, one description, one trust boundary.

    Nothing is revived for a message that carries its own files: a user who has just
    attached something is talking about that, and pulling yesterday's photograph in
    alongside it would answer a question nobody asked.
    """
    if fresh or not (user_input or "").strip():
        return []
    candidates = await _recent_attachments(persona, {a["id"] for a in fresh})
    if not candidates:
        return []
    return attachments_mod.references_earlier_files(
        user_input, attachments_mod.carryable(candidates)
    )


async def _forget_attachments(ids: list[str]) -> None:
    """Drop index rows for files the disk sweep has already deleted."""
    if not ids:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany("DELETE FROM attachments WHERE id=?", [(i,) for i in ids])
        await db.commit()


async def _bind_attachments(ids: list[str], exchange_id: str) -> None:
    """Record which exchange each file was sent with, once that exchange exists."""
    if not ids:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany(
            "UPDATE attachments SET exchange_id=? WHERE id=?",
            [(exchange_id, i) for i in ids],
        )
        await db.commit()


@app.on_event("startup")
async def _startup() -> None:
    await _init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT DISTINCT persona FROM exchanges") as cursor:
            personas = [row["persona"] async for row in cursor]
    for persona in personas:
        pairs = await _load_history_from_db(persona)
        if pairs:
            _session_history[persona] = pairs

    # Warm the models that would otherwise load lazily inside a user's session.
    # The embedding model takes ~10s to load; without this, the first log or
    # journal write after every restart paid that cost mid-response — i.e. after
    # every deploy. Runs in the background so startup is not delayed, and stays
    # best-effort: a warm-up failure must never stop the server booting.
    async def _warm() -> None:
        loop = asyncio.get_running_loop()

        def _load_embedder() -> None:
            from core.memory import _get_model
            _get_model()

        def _load_whisper() -> None:
            from core.voice_pipeline import _get_whisper
            _get_whisper()

        def _load_kokoro() -> None:
            if _kokoro_available():
                _get_kokoro()

        for name, fn, executor in (
            ("embedding", _load_embedder, _INDEX_EXECUTOR),
            ("whisper", _load_whisper, _STT_EXECUTOR),
            ("kokoro", _load_kokoro, _TTS_EXECUTOR),
        ):
            try:
                t0 = datetime.now()
                await loop.run_in_executor(executor, fn)
                secs = (datetime.now() - t0).total_seconds()
                print(f"[warmup] {name} model ready ({secs:.1f}s)", flush=True)
            except Exception as exc:
                print(f"[warmup] {name} model failed ({exc}) — will load on first use",
                      flush=True)

    asyncio.create_task(_warm())


@app.post("/session", response_model=SessionResponse)
async def session(req: SessionRequest) -> SessionResponse:
    """Run a single orchestrator turn and return the text response."""
    if not req.input.strip():
        raise HTTPException(status_code=400, detail="Input is empty.")
    try:
        agent = req.agent
        persona = req.persona or DEFAULT_PERSONA
        history = _session_history.setdefault(persona or "__default__", []) if agent == "coordinator" else None
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None, lambda: run_session(agent, req.input, persona=persona, provider=req.provider, history=history)
        )
        _log_conversation(req.input, response, agent, persona)
        return SessionResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/session/stream")
async def session_stream(req: SessionRequest):
    """
    Streaming variant of /session — Synthesizer output arrives as Server-Sent Events.

    Only supports agent="coordinator" (the full pipeline). Other agents 400.

    SSE event format:
      data: {text chunk}\\n\\n   — live text from Synthesizer
      data: [DONE]\\n\\n          — generation complete, filter passed; client commits text
      data: [RETRACT]\\n\\n       — filter hit; client should discard received text
      data: [RETRACT_WITH]{text} — discard received text and show {text} instead
      data: [ERROR] ...\\n\\n     — server exception

    [RETRACT_WITH] carries its replacement in the SAME event rather than following
    [RETRACT] with chunks: [RETRACT] is terminal on both transports, so anything sent
    after it is dropped. Used when a confirmation was raised mid-turn and the reply
    has to be corrected rather than withdrawn — see orchestrator.enforce_pending_receipt.

    NOTE: The sync generator runs inline in this async handler — acceptable for
    single-user local deployment. For multi-user, wrap with run_in_executor().
    """
    received_at = datetime.now(timezone.utc)
    if not req.input.strip():
        raise HTTPException(status_code=400, detail="Input is empty.")
    if req.agent != "coordinator":
        raise HTTPException(status_code=400, detail="Streaming only supported for agent=coordinator.")

    persona = req.persona or DEFAULT_PERSONA
    history = _session_history.setdefault(persona or "__default__", [])

    async def sse_generator():
        global _active_streams
        accumulated: list[str] = []
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        with _active_lock:
            _active_streams += 1

        def _produce() -> None:
            try:
                for chunk in run_pipeline_session_stream(
                    req.input, persona=persona, provider=req.provider, history=history,
                    received_at=received_at,
                ):
                    asyncio.run_coroutine_threadsafe(queue.put(chunk), loop).result()
            except NotImplementedError:
                # Provider has no streaming variant — fall back to single blocking call
                response = run_session(req.agent, req.input, persona=persona, provider=req.provider)
                asyncio.run_coroutine_threadsafe(queue.put(response), loop).result()
                asyncio.run_coroutine_threadsafe(queue.put("[DONE]"), loop).result()
            except Exception as e:
                # Log before handing it to the client. This branch returned the raw
                # exception text to the browser and wrote nothing server-side, so a
                # web-app failure existed only in the message the user was looking
                # at — five Vertex thought_signature 400s were diagnosed from the
                # scheduler's copies because the web ones left no trace at all.
                logger.exception(
                    f"[sse_error] persona={persona} agent={req.agent} error={e}"
                )
                asyncio.run_coroutine_threadsafe(queue.put(f"[ERROR] {e}"), loop).result()
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop).result()

        try:
            producer = loop.run_in_executor(None, _produce)

            while True:
                item = await queue.get()
                if item is None:
                    break
                if item in ("[DONE]", "[RETRACT]"):
                    yield f"data: {item}\n\n"
                elif item.startswith("[RETRACT_WITH]"):
                    # The replacement travels inside the marker; see the docstring.
                    # `accumulated` is reset so the conversation log records what the
                    # user was actually shown, not the withdrawn text.
                    replacement = item[len("[RETRACT_WITH]"):]
                    accumulated.clear()
                    accumulated.append(replacement)
                    safe = replacement.replace('\r', '').replace('\n', r'\n')
                    yield f"data: [RETRACT_WITH]{safe}\n\n"
                elif item.startswith("[ERROR] "):
                    yield f"data: {item}\n\n"
                    return
                else:
                    accumulated.append(item)
                    safe = item.replace('\r', '').replace('\n', r'\n')
                    yield f"data: {safe}\n\n"

            await asyncio.wrap_future(producer)
            _log_conversation(req.input, "".join(accumulated), req.agent, persona)
        finally:
            with _active_lock:
                _active_streams -= 1

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, persona: str | None = None) -> None:
    """
    WebSocket endpoint for real-time cross-device conversation sync.

    Query param: ?persona=X  (same values as the HTTP endpoints)

    Client → server message types:
      {type: "send", exchange_id, input, provider, attachments}  — submit a prompt.
          `attachments` is a list of ids returned by POST /upload; files themselves
          never travel over this socket. Unknown ids are dropped, not rejected.
      {type: "catchup", since_id}                   — fetch missed exchanges on reconnect

    Server → client message types:
      {type: "history", messages, last_id}           — initial full history on connect (wipes and rebuilds)
      {type: "catchup", messages, last_id}           — delta since_id response (appends only — DB-0809-06)
      {type: "stream_start", exchange_id, user, attachments}  — foreign exchange starting (not this device)
      {type: "chunk", exchange_id, text}             — token from the LLM (own or foreign)
      {type: "done", exchange_id}                    — exchange complete; commit text
      {type: "retract", exchange_id}                 — output filtered; discard buffered text
      {type: "message", id, exchange_id, user, assistant, ts, attachments}  — completed record for catch-up
      {type: "error", exchange_id, text?}            — error (text only on sender)
      {type: "ping"}                                 — 30-second heartbeat
    """
    global _active_streams
    persona_orch = persona or DEFAULT_PERSONA
    persona_key = persona_orch or "__default__"

    # --- Authentication ---------------------------------------------------
    # HTTP middleware does not run for a WebSocket handshake, so this endpoint is
    # gated here or not at all.
    #
    # The client's first frame must be {"type": "auth", "token": "<token>"}. A cookie
    # would work for the same-origin browser but not for the Android app, which is
    # cross-origin and never receives one; a ?token= query parameter would work for
    # both but writes the secret into URLs and therefore into access logs. The
    # handshake is the only option that is uniform across both clients and leaks
    # nothing.
    #
    # The connection is accepted before the check because a WebSocket cannot carry a
    # frame until it is open. It is registered with the manager only after the check
    # passes, so an unauthenticated socket never joins a broadcast group.
    await websocket.accept()
    try:
        opening = await asyncio.wait_for(websocket.receive_json(), timeout=10)
    except Exception:
        # Timeout, malformed JSON, or a client that hung up. All the same answer:
        # a socket that has not authenticated within 10s does not get to linger.
        await websocket.close(code=1008)
        return
    if opening.get("type") != "auth" or not auth.verify_token(opening.get("token")):
        await websocket.send_json({"type": "auth_failed"})
        await websocket.close(code=1008)
        return
    await websocket.send_json({"type": "auth_ok"})
    # ----------------------------------------------------------------------

    await manager.connect(websocket, persona_key)

    recent = await _get_recent_exchanges(persona_key)
    last_id = recent[-1]["id"] if recent else 0
    await websocket.send_json({"type": "history", "messages": recent, "last_id": last_id})

    async def _heartbeat() -> None:
        while True:
            await asyncio.sleep(30)
            try:
                await websocket.send_json({"type": "ping"})
            except Exception:
                return

    hb_task = asyncio.create_task(_heartbeat())

    try:
        while True:
            data = await websocket.receive_json()
            received_at = datetime.now(timezone.utc)
            msg_type = data.get("type")

            if msg_type == "send":
                exchange_id = data.get("exchange_id") or str(uuid.uuid4())
                user_input = data.get("input", "").strip()
                attached = await _resolve_attachments(
                    data.get("attachments") or [], persona_key
                )
                # A message carrying files needs no words: "here, look at this" is a
                # complete instruction when a photograph is attached to it.
                if not user_input and not attached:
                    continue
                provider = data.get("provider") or None
                # Scheduler-initiated exchanges are flagged so traces record that
                # Metatron opened the conversation rather than the user.
                proactive = bool(data.get("proactive"))
                # Files the user sent in an earlier turn and is now pointing back at.
                # These go to the model but not to the client or the exchange row:
                # the user did not attach them to this message, so a chip under it
                # would misreport what they did, and re-binding them here would
                # rewrite which turn they arrived in.
                #
                # Never on a proactive turn: that prompt is written by the scheduler,
                # so its words are not a user referring to anything, and a phrase like
                # "the photo" in a job's text would silently bill for a file.
                revived = [] if proactive else await _revive_attachments(
                    persona_key, user_input, attached
                )
                pipeline_attachments = attached + revived
                history = _session_history.setdefault(persona_key, [])

                # Notify other devices that a new exchange is starting
                await manager.broadcast(persona_key, {
                    "type": "stream_start",
                    "exchange_id": exchange_id,
                    "user": user_input,
                    # Clients must not render the prompt of a proactive exchange as
                    # something the user said — Metatron opened this one.
                    "proactive": proactive,
                    "attachments": _public_attachments(attached),
                }, exclude=websocket)

                loop = asyncio.get_running_loop()
                queue: asyncio.Queue = asyncio.Queue()
                accumulated: list[str] = []
                retracted = False
                retract_text = ""
                errored = False

                def _produce() -> None:
                    try:
                        for chunk in run_pipeline_session_stream(
                            user_input, persona=persona_orch, provider=provider,
                            history=history, is_proactive=proactive,
                            received_at=received_at, attachments=pipeline_attachments,
                        ):
                            asyncio.run_coroutine_threadsafe(queue.put(chunk), loop).result()
                    except NotImplementedError:
                        response = run_session(
                            "coordinator", user_input, persona=persona_orch, provider=provider
                        )
                        asyncio.run_coroutine_threadsafe(queue.put(response), loop).result()
                        asyncio.run_coroutine_threadsafe(queue.put("[DONE]"), loop).result()
                    except Exception as e:
                        asyncio.run_coroutine_threadsafe(queue.put(f"[ERROR] {e}"), loop).result()
                    finally:
                        asyncio.run_coroutine_threadsafe(queue.put(None), loop).result()

                producer = loop.run_in_executor(None, _produce)
                sender_alive = True  # track whether the initiating WS is still connected

                async def _send_to_sender(payload: dict) -> None:
                    nonlocal sender_alive
                    if not sender_alive:
                        return
                    try:
                        _log_ws_frame(websocket, "sender", payload)   # TEMPORARY — [DB-0810-01]
                        await websocket.send_json(payload)
                    except Exception:
                        sender_alive = False

                # Counts in-flight exchanges (not connections) so deploy.sh's drain
                # gate — which polls /active — actually waits for this exchange to
                # finish instead of always reading 0 while an always-connected
                # client sits idle. Mirrors the SSE path's _active_lock usage above.
                with _active_lock:
                    _active_streams += 1
                try:
                    while True:
                        item = await queue.get()
                        if item is None:
                            break
                        if item == "[DONE]":
                            break
                        elif item.startswith("[RETRACT_WITH]"):
                            # Withdraw what was streamed and show the replacement in
                            # its place. Carried on the retract payload itself because
                            # the client nulls the bubble on retract, so a following
                            # chunk has nothing to append to — measured live 2026-08-27.
                            retracted = True
                            retract_text = item[len("[RETRACT_WITH]"):]
                            accumulated.clear()
                            accumulated.append(retract_text)
                            break
                        elif item == "[RETRACT]":
                            retracted = True
                            break
                        elif item.startswith("[ERROR] "):
                            errored = True
                            await _send_to_sender({
                                "type": "error", "exchange_id": exchange_id, "text": item[8:],
                            })
                            await manager.broadcast(persona_key, {
                                "type": "error", "exchange_id": exchange_id,
                            }, exclude=websocket)
                            break
                        else:
                            accumulated.append(item)
                            chunk_payload = {"type": "chunk", "exchange_id": exchange_id, "text": item}
                            await _send_to_sender(chunk_payload)
                            await manager.broadcast(persona_key, chunk_payload, exclude=websocket)

                    await asyncio.wrap_future(producer)

                    if retracted:
                        # `text` present only for [RETRACT_WITH]; the client falls back
                        # to its canned line when it is absent, so a plain filter
                        # suppression is unchanged.
                        retract_payload = {"type": "retract", "exchange_id": exchange_id}
                        if retract_text:
                            retract_payload["text"] = retract_text
                        await _send_to_sender(retract_payload)
                        await manager.broadcast(persona_key, retract_payload, exclude=websocket)
                    elif not errored:
                        full_response = "".join(accumulated)
                        done_payload = {"type": "done", "exchange_id": exchange_id}
                        await _send_to_sender(done_payload)
                        await manager.broadcast(persona_key, done_payload, exclude=websocket)
                        new_id = await _save_exchange(persona_key, exchange_id, user_input,
                                                      full_response, proactive=proactive,
                                                      attachments=attached)
                        await _bind_attachments([a["id"] for a in attached], exchange_id)
                        _log_conversation(user_input, full_response, "coordinator", persona_orch,
                                          proactive=proactive)
                        await manager.broadcast(persona_key, {
                            "type": "message",
                            "id": new_id,
                            "exchange_id": exchange_id,
                            "user": user_input,
                            "assistant": full_response,
                            "ts": datetime.utcnow().isoformat() + "Z",
                            "attachments": _public_attachments(attached),
                        }, exclude=websocket)
                finally:
                    with _active_lock:
                        _active_streams -= 1

            elif msg_type == "catchup":
                # Deliberately a distinct type from the initial "history" load below.
                # Both used to share "history", and the client's handler for that type
                # wipes the whole conversation and rebuilds from only what it's given
                # ([DB-0809-06]) — correct for a fresh page load's full history, wrong
                # for a delta: everything not in this catch-up window vanished until a
                # manual reload restored it. "catchup" rows are applied one at a time
                # through the same append-only path as a live "message" broadcast.
                since_id = int(data.get("since_id", 0))
                rows = await _catchup_since(persona_key, since_id)
                if rows:
                    await websocket.send_json({
                        "type": "catchup",
                        "messages": rows,
                        "last_id": rows[-1]["id"],
                    })

    except WebSocketDisconnect:
        pass
    finally:
        hb_task.cancel()
        manager.disconnect(websocket, persona_key)


class ConfirmRequest(BaseModel):
    token: str
    persona: str | None = None


@app.get("/pending-confirmations")
async def pending_confirmations(persona: str | None = None) -> dict:
    """Actions awaiting the user's approval. The app polls this to render its prompt."""
    from core.persona import persona_scope
    from tools.confirm import pending
    with persona_scope(persona or DEFAULT_PERSONA):
        return {"pending": pending()}


def _approve_and_execute(token: str, persona: str) -> dict | None:
    """Record the approval and carry the action out. Returns None if the token is unknown.

    Runs on a worker thread — it does real network and disk I/O (an SMTP send, a config
    write) and must not sit on the event loop. Identity resolution is thread-local and
    fail-closed, so `persona_scope` is entered *inside* the thread that does the work;
    wrapping the `to_thread` call instead would leave this thread unscoped.
    """
    from core.persona import persona_scope
    from tools.confirm import approve, execute
    with persona_scope(persona):
        if not approve(token):
            return None
        return execute(token)


@app.post("/confirm")
async def confirm_action(req: ConfirmRequest) -> dict:
    """
    Record the user's approval of a pending action — and carry it out.

    **This endpoint is the whole point of the design.** Approval is recorded here, from a
    deliberate tap in the app, and never by the model saying the user agreed. A model that
    a hostile email has talked into acting is exactly the model whose claim of consent
    cannot be trusted — so it is not in this path at all. It may propose; only the user,
    through this endpoint, may approve.

    **It also executes, since 2026-08-15 (`[DB-0815-03]`).** Recording the approval and
    stopping was the bug: the second tool call the design assumed would follow could never
    happen, because the token lives in a tool result the model no longer has by the next
    turn. Mike approved a real email and was told it was still waiting for him. The consent
    property is unchanged — the model still cannot approve, and `execute()` spends the
    approval through the same fingerprint-checked `consume()` a model call would have hit.

    The outcome is written to the conversation as an ordinary exchange and broadcast, so
    every connected client shows what actually happened rather than inferring it.

    Authenticated like every other endpoint, so the tap has to come from a signed-in
    client rather than anything that can reach the port.
    """
    persona_key = req.persona or DEFAULT_PERSONA
    outcome = await asyncio.to_thread(_approve_and_execute, req.token, persona_key)
    if outcome is None:
        raise HTTPException(status_code=404,
                            detail="No such pending action, or it has expired.")

    # The description's first line names the action in the user's own terms — it is what
    # they read on the approval card, so echoing it is what makes the outcome legible.
    headline = (outcome.get("description") or "").strip().splitlines()
    headline = headline[0] if headline else "the action you approved"
    if outcome.get("status") == "executed":
        line = f"✅ Done — {headline}"
    else:
        line = f"⚠️ Not done — {headline}\n\n{outcome.get('message', 'It did not go through.')}"

    # Not derived from the token: the exchange id is broadcast to every client, and the
    # token has no business travelling anywhere it was not already going. A repeat tap
    # cannot duplicate this row anyway — the record is gone, so the second call 404s.
    exchange_id = f"confirm-{uuid.uuid4().hex[:12]}"
    user_side = "(approved in the app)"
    new_id = await _save_exchange(persona_key, exchange_id, user_side, line, proactive=True)
    _log_conversation(user_side, line, "confirm", persona_key, proactive=True)
    await manager.broadcast(persona_key, {
        "type": "message",
        "id": new_id,
        "exchange_id": exchange_id,
        "user": user_side,
        "assistant": line,
        "ts": datetime.utcnow().isoformat() + "Z",
    })

    return {"status": outcome.get("status", "approved"), "message": line}


def _decline(token: str, persona: str) -> dict | None:
    """Record the refusal. Returns None if the token is unknown. See `_approve_and_execute`
    for why the persona scope is entered inside the worker thread rather than around it."""
    from core.persona import persona_scope
    from tools.confirm import decline
    with persona_scope(persona):
        return decline(token)


@app.post("/decline")
async def decline_action(req: ConfirmRequest) -> dict:
    """
    Record the user's refusal of a pending action, and stop it being asked again.

    **Declining used to be a no-op** (`[DB-0827-01]`). The app dismissed the card locally
    and left the record pending, so `/pending-confirmations` handed the same prompt back on
    the next five-second poll, and kept doing so until the TTL. Mike, first decline ever
    performed: *"If I decline it keeps asking in a loop. In the end I approved to break the
    loop."* A gate whose cheapest escape is approval authorises by exhaustion — the exact
    property `tools/confirm.py` exists to prevent.

    Symmetrical with /confirm and deliberately so: same auth, same out-of-band principle
    (only a tap here decides; the model is in neither path), same fingerprint discipline,
    and the same conversation row so the refusal is visible to every connected client
    rather than inferred. That row is also what keeps a decline in front of the model on
    the next turn — the conversation is context, so "declined" is at least present, even
    though nothing yet reads the declined ledger itself.
    """
    persona_key = req.persona or DEFAULT_PERSONA
    record = await asyncio.to_thread(_decline, req.token, persona_key)
    if record is None:
        raise HTTPException(status_code=404,
                            detail="No such pending action, or it has expired.")

    headline = (record.get("description") or "").strip().splitlines()
    headline = headline[0] if headline else "that action"
    line = f"🚫 Declined — {headline}\n\nNothing was done, and I won't ask about it again."

    exchange_id = f"decline-{uuid.uuid4().hex[:12]}"
    user_side = "(declined in the app)"
    new_id = await _save_exchange(persona_key, exchange_id, user_side, line, proactive=True)
    _log_conversation(user_side, line, "decline", persona_key, proactive=True)
    await manager.broadcast(persona_key, {
        "type": "message",
        "id": new_id,
        "exchange_id": exchange_id,
        "user": user_side,
        "assistant": line,
        "ts": datetime.utcnow().isoformat() + "Z",
    })

    return {"status": "declined", "message": line}


# ---------------------------------------------------------------------------
# Location  [DB-0815-12]
# ---------------------------------------------------------------------------

class LocationPing(BaseModel):
    lat: float
    lon: float
    accuracy: float | None = None
    ts: str | None = None          # the client's reading time, ISO 8601
    persona: str | None = None


def _record_location(lat: float, lon: float, accuracy: float | None,
                     ts: str | None, persona: str) -> dict:
    """Resolve the coordinate to a zone and record a change. Runs on a worker thread —
    it reads and appends files, and persona scoping is thread-local and fail-closed, so
    the scope is entered inside the thread that does the work."""
    from core.persona import persona_scope
    from tools.location import record_position
    with persona_scope(persona):
        return record_position(lat, lon, accuracy=accuracy, ts=ts)


@app.post("/location")
async def location_ping(req: LocationPing) -> dict:
    """
    Take one GPS reading from the app and give back the name of the place it is in.

    **The coordinate stops here.** Location is extra-sensitive — above ordinary sensitive
    (Mike, 2026-08-28) — so raw GPS never enters a model prompt, cloud or local, and no
    coordinate history is kept anywhere. `record_position()` maps the reading to one of the
    user's named zones and returns that name; `lat`, `lon` and `accuracy` are never written to
    disk, never added to the conversation, and never reach `_log_conversation`. What persists
    is a line in the zone transitions log saying the user arrived somewhere at a time.

    That placement is the enforcement, not a convention: the mapping is Python in
    `tools/location.py`, per the standing rule that sensitive data paths are enforced in code
    and never in prompts. Nothing downstream of this handler is in a position to leak a
    coordinate, because nothing downstream is ever given one.

    Unlike /confirm and /decline this writes **no conversation row and broadcasts nothing**.
    A ping is not something the user said, and a stream of "you are at home" messages would
    turn a background signal into a conversation the user did not start. The zone reaches the
    model as one context line on the next turn — `tools.location.context_block`.

    Two callers, both a deliberate user act (`[DB-0815-12]` design point 3): sending a message
    with the on-message ping switched on, and the share-location button. Nothing polls, and
    the endpoint holds no state between calls that could keep running if the app went away.

    Returns `{"zone", "entered_at", "changed"}`. An unknown coordinate is `zone: "away"`, not
    an error — a user who has not written a zones file gets a working endpoint that knows
    nothing, which is the truth.
    """
    persona_key = req.persona or DEFAULT_PERSONA
    try:
        return await asyncio.to_thread(
            _record_location, req.lat, req.lon, req.accuracy, req.ts, persona_key)
    except Exception as e:
        # Deliberately does not echo the request: the detail string is the one place a
        # coordinate could travel back out of this handler, and an exception message can
        # carry its arguments.
        logger.warning(f"[location] ping failed: {type(e).__name__}")
        raise HTTPException(status_code=500, detail="Could not record the location.")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/active")
async def active() -> dict:
    return {"active_streams": _active_streams}


# ---------------------------------------------------------------------------
# Web Push
# ---------------------------------------------------------------------------

class PushSubscription(BaseModel):
    endpoint: str
    keys: dict


@app.get("/vapid-public-key")
async def vapid_public_key() -> dict:
    """Return the VAPID public key so the PWA can subscribe to push."""
    from core.push import get_vapid_public_key
    return {"publicKey": get_vapid_public_key()}


@app.post("/subscribe")
async def subscribe(sub: PushSubscription) -> dict:
    """Register a browser push subscription from the PWA."""
    from core.push import save_subscription
    result = save_subscription(sub.dict())
    return {"status": result}


@app.post("/push/test")
async def push_test() -> dict:
    """Dev endpoint — send a test push to all registered subscriptions."""
    from core.push import send_push
    result = send_push(title="Life Manager", body="Push notifications are working.")
    return result


@app.post("/feedback")
async def feedback() -> dict:
    """PWA tap — record a USER_CORRECTION quality event."""
    from tools.logger import write_quality_event
    from datetime import datetime
    result = write_quality_event(
        event_type="USER_CORRECTION",
        source_agent="pwa_tap",
        detail="User tapped missed-the-mark affordance",
        session_id=datetime.utcnow().strftime("%Y-%m-%dT%H"),
    )
    return {"status": result}


class TTSRequest(BaseModel):
    text: str


# [DB-0810-15] / [DB-0815-02] Speech-out for a non-English response language.
#
# Kokoro is the primary engine and CANNOT do Bulgarian: its pipeline is built per language code
# and it ships American/British English, Spanish, French, Hindi, Italian, Japanese, Portuguese
# and Chinese — there is no Bulgarian model to select. edge-tts does have bg-BG neural voices,
# so a non-Kokoro language must fall through to edge-tts rather than being spoken by an English
# voice reading foreign words phonetically, which is worse than useless on a voice-first product.
#
# Only languages actually verified as available are listed. An unlisted language deliberately
# falls back to the English voice and text still works — the alternative, refusing to speak at
# all, would break voice for a persona whose text path is fine.
_EDGE_VOICE_BY_LANG = {
    "bg": "bg-BG-KalinaNeural",
}

# Language codes Kokoro can serve, so the engine choice is derived from one list rather than
# hardcoded per branch. English maps to the existing default and changes nothing.
_KOKORO_LANGS = {"en"}

_kokoro_pipeline = None
_kokoro_lock = threading.Lock()


def _kokoro_available() -> bool:
    try:
        import kokoro  # noqa: F401
        return True
    except Exception:
        return False


def _get_kokoro():
    """
    Build the Kokoro pipeline once and keep it.

    It used to run as a subprocess per request, which meant importing kokoro
    (~7s) and constructing KPipeline (~3s) every single call — about 10s of the
    measured 15s per request, repeated forever, while actual synthesis was only
    ~3s. speak.py even caches the pipeline in a module global, but a fresh
    process each time made that cache useless.

    The subprocess existed because Kokoro once lived in its own venv with
    conflicting dependencies. It was installed into the main venv on the VM on
    2026-06-27, so the isolation is obsolete.
    """
    global _kokoro_pipeline
    with _kokoro_lock:
        if _kokoro_pipeline is None:
            from kokoro import KPipeline
            _kokoro_pipeline = KPipeline(lang_code="a")
        return _kokoro_pipeline


def _kokoro_blocking(text: str) -> str:
    """Synthesise to a wav and return its path. Blocking — never on the loop."""
    import numpy as _np
    import soundfile as _sf

    wav_tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    wav_tmp.close()
    try:
        pipeline = _get_kokoro()
        chunks = [audio for _gs, _ps, audio in pipeline(text, voice=KOKORO_VOICE)]
        if not chunks:
            raise RuntimeError("Kokoro produced no audio")
        _sf.write(wav_tmp.name, _np.concatenate(chunks), 24000)
        return wav_tmp.name
    except Exception:
        # Previously only the mp3 temp file was cleaned up on failure, so every
        # Kokoro error leaked a wav.
        Path(wav_tmp.name).unlink(missing_ok=True)
        raise


@app.post("/tts")
async def tts(req: TTSRequest):
    """
    Generate speech audio — Kokoro af_heart primary, edge-tts fallback.

    Kokoro runs on its own executor. It used to run inline in this async
    function, freezing the whole server for up to 120s: no HTTP responses, no
    WebSocket pings, nothing.
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text is empty.")

    # [DB-0810-15] Pick the engine from the persona's response language, not from availability
    # alone. Kokoro is preferred where it can serve the language; where it cannot (Bulgarian) an
    # English Kokoro voice would read the text phonetically, so edge-tts wins instead.
    edge_voice = EDGE_VOICE
    lang_code = ""
    try:
        from core.translate import response_language
        lang = response_language()
        if lang is not None:
            lang_code = lang[0]
            edge_voice = _EDGE_VOICE_BY_LANG.get(lang_code, EDGE_VOICE)
    except Exception:
        logger.warning("[tts] could not resolve response language — using the default voice")

    kokoro_can_serve = (not lang_code) or lang_code in _KOKORO_LANGS

    try:
        if _kokoro_available() and kokoro_can_serve:
            loop = asyncio.get_running_loop()
            audio_path = await loop.run_in_executor(_TTS_EXECUTOR, _kokoro_blocking, req.text)
            media_type = "audio/wav"
        else:
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            tmp.close()
            # edge_tts is already async — it does not block the loop.
            communicate = edge_tts.Communicate(req.text, edge_voice)
            await communicate.save(tmp.name)
            media_type = "audio/mpeg"
            audio_path = tmp.name

        def iterfile():
            try:
                with open(audio_path, "rb") as f:
                    yield from f
            finally:
                Path(audio_path).unlink(missing_ok=True)

        return StreamingResponse(iterfile(), media_type=media_type)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Speech synthesis failed: {e}")


def _transcribe_blocking(audio_bytes: bytes, persona: str | None = None) -> dict:
    """
    ffmpeg decode + Whisper. Blocking — must run off the event loop.

    All of this used to run inside `async def transcribe_audio`, so the server
    was frozen for the whole of ffmpeg + Whisper: no HTTP responses, no
    WebSocket pings. A second voice message sent during the first transcription
    got "Failed to fetch" from a server that was running but unable to answer.
    """
    import json as _json
    import subprocess as _subprocess
    import numpy as _np

    ts = datetime.now().strftime("%H-%M-%S")
    date_dir = Path(__file__).parent.parent / "data" / "audio" / datetime.now().strftime("%Y-%m-%d")
    date_dir.mkdir(parents=True, exist_ok=True)

    audio_path = date_dir / f"{ts}.webm"
    with open(audio_path, "wb") as f:
        f.write(audio_bytes)

    # Decode from the bytes already in memory — no disk round-trip.
    try:
        result = _subprocess.run(
            ["ffmpeg", "-i", "pipe:0", "-ar", "16000", "-ac", "1", "-f", "f32le", "-"],
            input=audio_bytes, capture_output=True, timeout=120,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="ffmpeg not found on the server")
    except _subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Audio decoding timed out")

    if result.returncode != 0:
        raise HTTPException(
            status_code=422,
            detail=f"Could not decode audio: {result.stderr.decode(errors='replace')[:200]}",
        )

    audio_array = _np.frombuffer(result.stdout, dtype=_np.float32)
    if audio_array.size == 0:
        raise HTTPException(status_code=422, detail="Recording contained no audio")

    from core.voice_pipeline import correct_known_addresses, transcribe as _transcribe
    transcript = _transcribe(audio_array)

    if persona and transcript:
        # Snap a mis-transcribed dictated email address to the closest known
        # one (the user's own, or a saved contact). Never raises into the
        # response — a correction failure should degrade to the raw
        # transcript, not break transcription.
        try:
            transcript = correct_known_addresses(transcript, persona)
        except Exception as e:
            print(f"[transcribe] address correction skipped: {e}")

    meta_path = date_dir / f"{ts}.json"
    with open(meta_path, "w") as f:
        _json.dump({
            "ts": datetime.now().isoformat(),
            "audio_file": str(audio_path),
            "transcript": transcript,
        }, f, ensure_ascii=False, indent=2)

    return {"transcript": transcript}


@app.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...), persona: str | None = None) -> dict:
    """
    Transcribe a voice recording with Whisper, locally. Audio never leaves this
    machine; the Web Speech API is deliberately not used.

    Runs on a dedicated executor. The semaphore returns a fast 503 on a
    concurrent request rather than queueing it invisibly until the client gives
    up — which previously surfaced as "Failed to fetch".

    `persona` is optional: transcription itself needs no persona, only the
    known-address correction pass does. Omit it and the raw Whisper output
    is returned uncorrected, same as before this parameter existed.
    """
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=422, detail="Empty audio upload")

    if _STT_SEMAPHORE.locked():
        raise HTTPException(
            status_code=503,
            detail="Still transcribing the previous recording — try again in a moment",
        )

    async with _STT_SEMAPHORE:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            _STT_EXECUTOR, _transcribe_blocking, audio_bytes, persona
        )


@app.post("/upload")
async def upload_attachment(file: UploadFile = File(...), persona: str | None = None) -> dict:
    """
    Store one photo or document for the persona, ready to be sent with a message.

    Upload and send are separate steps because the WebSocket carries JSON frames: a
    10 MB file base64'd into a socket frame would block every other frame on that
    connection, including the heartbeat the client uses to decide the socket is
    alive. The file goes over HTTP; the send frame carries only its id.

    The type is decided by sniffing the bytes, not by the Content-Type the browser
    asserts — see core/attachments.validate().
    """
    persona_key = persona or DEFAULT_PERSONA or "__default__"
    data = await file.read()

    try:
        mime = attachments_mod.validate(data)
    except attachments_mod.AttachmentRejected as e:
        raise HTTPException(status_code=415, detail=str(e))

    loop = asyncio.get_running_loop()
    record = await loop.run_in_executor(
        None, attachments_mod.save, persona_key, data, file.filename or "", mime
    )
    await _insert_attachment(record)

    # Expire the store on the way past. This is the only thing that deletes an
    # attachment, and it runs here — at a write — rather than as a scheduled job:
    # the moment the store grows is the moment a sweep has something to collect,
    # and it needs no new daily job to be registered or kept alive.
    expired = await loop.run_in_executor(None, attachments_mod.sweep_expired, persona_key)
    await _forget_attachments(expired)

    return _public_attachments([record])[0]


@app.get("/attachments/{attachment_id}")
async def get_attachment(attachment_id: str, persona: str | None = None):
    """
    Serve a stored file back to the client that owns it.

    The path comes from the database row, never from the URL, so there is no
    traversal surface — an id either resolves to a row for this persona or 404s.
    """
    persona_key = persona or DEFAULT_PERSONA or "__default__"
    record = await _get_attachment(attachment_id, persona_key)
    if not record:
        raise HTTPException(status_code=404, detail="No such attachment")

    path = Path(record["path"])
    if not path.exists():
        raise HTTPException(status_code=410, detail="That file is no longer stored")

    return FileResponse(
        path,
        media_type=record["mime"],
        filename=record["name"],
        headers={"Cache-Control": "no-store"},
    )


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "index.html",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/sw.js")
async def service_worker() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "sw.js",
        media_type="application/javascript",
        headers={
            "Cache-Control": "no-store",
            "Service-Worker-Allowed": "/",
        },
    )


# ---------------------------------------------------------------------------
# Monitor API — The Book
# Read-only endpoints for the Mac monitoring tool. No auth: access is gated
# by the Tailscale VPN. Add a shared-secret header at Alpha.
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent.parent / "data"


def _all_personas() -> list[str]:
    """Return all known persona identifiers — dev personas + root user."""
    personas = set()
    personas_data = DATA_DIR / "personas"
    if personas_data.exists():
        for p in personas_data.iterdir():
            if p.is_dir():
                personas.add(p.name)
    # Root user (mike) may not have a personas/ subdir if they predate the layout
    if (DATA_DIR / "logs").exists() or (DATA_DIR / "context.json").exists():
        personas.add("mike")
    return sorted(personas)


def _conversation_files(persona: str | None) -> list[Path]:
    if persona:
        conv_dir = DATA_DIR / "personas" / persona / "conversations"
    else:
        conv_dir = DATA_DIR / "conversations"
    if not conv_dir.exists():
        # Fall back to shared conversations dir, filtered by persona field
        conv_dir = DATA_DIR / "conversations"
    if not conv_dir.exists():
        return []
    return sorted(conv_dir.glob("*.jsonl"))


def _trace_files(persona: str | None) -> list[Path]:
    if persona:
        trace_dir = DATA_DIR / "personas" / persona / "traces"
    else:
        trace_dir = DATA_DIR / "traces"
    if not trace_dir.exists():
        return []
    return sorted(trace_dir.glob("*.jsonl"))


def _read_jsonl(path: Path) -> list[dict]:
    import json as _json
    lines = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        lines.append(_json.loads(line))
                    except Exception:
                        pass
    except Exception:
        pass
    return lines


@app.get("/monitor/personas")
async def monitor_personas() -> dict:
    """List all persona identifiers known to the system."""
    return {"personas": _all_personas()}


@app.get("/monitor/conversations")
async def monitor_conversations(
    persona: str | None = None,
    since: str | None = None,
    limit: int | None = None,
) -> dict:
    """
    Return conversation entries. Filtered by persona and optional ISO datetime
    lower-bound (since). Returns the `limit` most recent entries, sorted newest-first.
    """
    from datetime import datetime as _dt
    since_dt = _dt.fromisoformat(since) if since else None
    entries = []
    for f in _conversation_files(persona):
        for entry in _read_jsonl(f):
            if persona is not None and entry.get("persona") != persona:
                continue
            if since_dt:
                try:
                    if _dt.fromisoformat(entry.get("ts", "")[:19]) < since_dt:
                        continue
                except (ValueError, TypeError):
                    pass
            entries.append(entry)
    entries.sort(key=lambda e: e.get("ts", ""), reverse=True)
    if limit is not None:
        entries = entries[:limit]
    return {"entries": entries}


@app.get("/monitor/traces")
async def monitor_traces(
    persona: str | None = None,
    trace_id: str | None = None,
    since: str | None = None,
    limit: int | None = None,
) -> dict:
    """
    Return trace records. If trace_id given, return just that one record.
    Otherwise return traces filtered by since/limit, newest-first.
    """
    from datetime import datetime as _dt
    since_dt = _dt.fromisoformat(since) if since else None
    traces = []
    for f in _trace_files(persona):
        for t in _read_jsonl(f):
            if trace_id is not None and t.get("trace_id") != trace_id:
                continue
            if since_dt and trace_id is None:
                try:
                    if _dt.fromisoformat(t.get("ts", "")[:19]) < since_dt:
                        continue
                except (ValueError, TypeError):
                    pass
            traces.append(t)
    if trace_id is None:
        traces.sort(key=lambda t: t.get("ts", ""), reverse=True)
        if limit is not None:
            traces = traces[:limit]
    return {"traces": traces}


@app.get("/monitor/model_errors")
async def monitor_model_errors(since: str | None = None, limit: int | None = None) -> dict:
    """
    Return whole-model-call failures logged by core.router.log_model_error()
    (data/diagnostics/model_errors.json) — API exceptions, as opposed to
    tool-call failures, which travel with the trace itself.
    """
    import json as _json
    from datetime import datetime as _dt
    path = DATA_DIR / "diagnostics" / "model_errors.json"
    entries: list = []
    if path.exists():
        try:
            with open(path) as f:
                entries = _json.load(f)
        except Exception:
            entries = []
    since_dt = _dt.fromisoformat(since) if since else None
    if since_dt:
        filtered = []
        for e in entries:
            try:
                if _dt.fromisoformat(e.get("timestamp", "")[:19]) >= since_dt:
                    filtered.append(e)
            except (ValueError, TypeError):
                filtered.append(e)
        entries = filtered
    entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    if limit is not None:
        entries = entries[:limit]
    return {"entries": entries}


@app.get("/monitor/ws_frames")
async def monitor_ws_frames(exchange_id: str | None = None, limit: int = 300) -> dict:
    """
    TEMPORARY DIAGNOSTIC — every outbound WebSocket frame, for [DB-0810-01].

    Answers the one question four dead theories could not: did the server send
    the reply twice? Each entry names the socket and which emit path sent it —
    "sender" (the socket that asked) or "broadcast" (every other socket on that
    persona). Two chunk runs for one exchange_id is the server duplicating; one
    run means the fault is client-side.

    Content-free: no message text, only its length. Remove with _WS_FRAME_LOG.
    """
    entries = list(_WS_FRAME_LOG)
    if exchange_id:
        entries = [e for e in entries if e.get("exchange_id") == exchange_id]
    entries = entries[-limit:]
    # Per-exchange chunk counts by socket — the shape the answer is read from,
    # so nobody has to tally 300 rows by eye to see a doubled run.
    summary: dict = {}
    for e in entries:
        if e.get("type") != "chunk":
            continue
        key = f"{e.get('exchange_id', '')[-8:]}/sock{e['sock']}/{e['path']}"
        s = summary.setdefault(key, {"chunks": 0, "chars": 0})
        s["chunks"] += 1
        s["chars"] += e.get("len") or 0
    return {"count": len(entries), "chunk_runs": summary, "entries": entries}


@app.get("/monitor/stream")
async def monitor_stream(persona: str | None = None, since: str | None = None):
    """
    SSE stream that emits new conversation+trace pairs in real time.

    since: ISO datetime string. Traces older than this are skipped on the
    initial scan (their positions are still tracked so they are not re-sent).
    Pass the time load_data started so historical backfill doesn't corrupt
    the client's filtered view.

    Format: text/event-stream, each message: "data: {json}\\n\\n"
    """
    import asyncio
    import json as _json
    from datetime import datetime as _dt

    since_dt = _dt.fromisoformat(since) if since else None

    def _seq_for(trace_entry: dict) -> str:
        """
        Find the seq of the conversation record matching this trace.

        seq is assigned by _log_conversation() and lives only in the
        conversation JSONL; traces have no seq of their own. Without this
        lookup, exchanges that arrive live are unnumbered in the monitor while
        exchanges already on disk at load time are numbered — the same
        exchange, displayed two different ways depending on timing.

        Matched on the user text, taking the newest match: the trace is written
        at pipeline completion and the conversation record immediately after, so
        the correct record is the last one with that text.
        """
        user_text = (trace_entry.get("user_input") or "").strip()
        if not user_text:
            return ""
        try:
            for conv_file in reversed(_conversation_files(persona)):
                for record in reversed(_read_jsonl(conv_file)):
                    if (record.get("user") or "").strip() == user_text:
                        return record.get("seq", "")
        except Exception:
            pass
        return ""

    async def _generate():
        # Track how many lines we've already sent from the current trace file.
        # On first pass, skip (but count) lines older than since_dt.
        seen: dict[str, int] = {}
        first_pass = True

        while True:
            files = _trace_files(persona)
            if not files:
                yield "data: {\"type\": \"heartbeat\"}\n\n"
                await asyncio.sleep(1)
                first_pass = False
                continue

            for f in files:
                key = str(f)
                prev = seen.get(key, 0)
                lines = _read_jsonl(f)
                new_lines = lines[prev:]
                for entry in new_lines:
                    if first_pass and since_dt:
                        try:
                            entry_ts = _dt.fromisoformat(entry.get("ts", "")[:26])
                            if entry_ts < since_dt:
                                continue  # count position but don't emit
                        except (ValueError, TypeError):
                            pass
                    if not entry.get("seq"):
                        seq = _seq_for(entry)
                        if seq:
                            entry = {**entry, "seq": seq}
                    payload = _json.dumps({"type": "trace", "data": entry}, ensure_ascii=False)
                    yield f"data: {payload}\n\n"
                seen[key] = len(lines)

            yield "data: {\"type\": \"heartbeat\"}\n\n"
            await asyncio.sleep(1)
            first_pass = False

    return StreamingResponse(_generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


_PROJECT_ROOT = Path(__file__).parent.parent


@app.get("/monitor/history")
async def monitor_history(path: str) -> dict:
    """
    Return the full contents of the directory containing `path`, sorted by
    filename (which equals date for YYYY-MM-DD.json files).  Each entry is
    separated by a divider.  The `current` key tells the caller which entry
    is the one that was just written so the viewer can scroll to it.

    path must be a relative data/ path, e.g. data/logs/2026-06-22.json
    """
    import json as _json

    if not path.startswith("data/") or ".." in path:
        raise HTTPException(status_code=400, detail="Invalid path")

    full = _PROJECT_ROOT / path
    if not full.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    parent = full.parent
    suffix = full.suffix
    siblings = sorted(p for p in parent.iterdir() if p.is_file() and p.suffix == suffix)

    sections = []
    for p in siblings:
        raw = p.read_text(errors="replace")
        if suffix == ".json":
            try:
                raw = _json.dumps(_json.loads(raw), indent=2, ensure_ascii=False)
            except Exception:
                pass
        sections.append({"filename": p.name, "stem": p.stem, "content": raw})

    return {"path": path, "current": full.name, "sections": sections}


@app.get("/monitor/file")
async def monitor_file(path: str) -> dict:
    """
    Read a file from the project data directory and return its content.

    path must be a relative path starting with 'data/' — no traversal allowed.
    Returns {path, content, size_bytes}.
    """
    import json as _json

    if not path.startswith("data/") or ".." in path or path != Path(path).as_posix():
        raise HTTPException(status_code=400, detail="Invalid path — must be relative data/ path")

    full = _PROJECT_ROOT / path
    if not full.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    if not full.is_file():
        raise HTTPException(status_code=400, detail="Not a file")

    raw = full.read_text(errors="replace")

    # Pretty-print JSON for readability in the viewer
    if path.endswith(".json"):
        try:
            raw = _json.dumps(_json.loads(raw), indent=2, ensure_ascii=False)
        except Exception:
            pass

    return {"path": path, "content": raw, "size_bytes": full.stat().st_size}


# Serve static assets (CSS, JS if we add them later)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser(description="Life Manager — PWA Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (0.0.0.0 = all interfaces)")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--provider", default="gemini", choices=["anthropic", "openai", "ollama", "gemini"],
                        help="Default provider (can be overridden per request)")
    parser.add_argument("--persona", default=None,
                        help="Default dev persona for all sessions (e.g. pepys). Omit for real user context.")
    args = parser.parse_args()

    if args.persona:
        os.environ["SERVER_PERSONA"] = args.persona
        print(f"  Dev persona: {args.persona} (all sessions will use this persona)")

    certs_dir = Path(__file__).parent.parent / "certs"
    # Prefer Tailscale cert (.crt/.key) over mkcert (.pem) — Tailscale certs are publicly trusted
    cert_file = next(certs_dir.glob("*.crt"), None) if certs_dir.exists() else None
    key_file = next(certs_dir.glob("*.key"), None) if certs_dir.exists() else None
    if not cert_file:
        cert_file = next((f for f in certs_dir.glob("*.pem") if "-key" not in f.name), None)
        key_file = next(certs_dir.glob("*-key.pem"), None)

    if cert_file and key_file:
        protocol = "https"
        ssl_kwargs = {"ssl_certfile": str(cert_file), "ssl_keyfile": str(key_file)}
    else:
        protocol = "http"
        ssl_kwargs = {}
        print("  No certs found in certs/ — running HTTP (mic blocked on Android Chrome).")
        print("  Run: tailscale cert <hostname>  or  mkcert <your-ip> localhost 127.0.0.1")

    tailscale_host = "mikes-macbook-air.tail0acc5d.ts.net"
    print(f"\nLife Manager server → {protocol}://0.0.0.0:{args.port}")
    print(f"Open on phone (Tailscale): {protocol}://{tailscale_host}:{args.port}")
    if protocol == "https":
        print("No CA install needed — Tailscale cert is publicly trusted.")
        print("  Settings → Security → Install certificate → CA certificate\n")

    uvicorn.run("core.server:app", host=args.host, port=args.port, reload=False,
                timeout_graceful_shutdown=150, **ssl_kwargs)
