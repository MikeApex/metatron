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
from fastapi import (BackgroundTasks, FastAPI, File, HTTPException, Request, Response,
                     UploadFile, WebSocket, WebSocketDisconnect)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core import attachments as attachments_mod
from core import auth
from core import interview as interview_mod
from core import tts_worker
from core.orchestrator import run_pipeline_session_stream, run_session
from core.persona import PersonaError, persona_data_dir, persona_scope, validate_persona_name

EDGE_VOICE = "en-US-JennyNeural"

logger = logging.getLogger(__name__)

app = FastAPI(title="Life Manager")

# There is no default persona. Until 2026-10-27 a request that named nobody was served as
# whoever `--persona` named (Mike), and the request's own claim decided the rest — fine with
# one user, and the root of every isolation defect with two (plan § 3.1-3.2). Every route now
# takes its persona from the caller's token through `bound_persona()`, and nothing else.

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


@app.exception_handler(RequestValidationError)
async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    A malformed request gets the names of the fields that failed — never what was sent.

    FastAPI's default 422 body carries an `input` field holding the submitted value, and
    for a missing field that is the whole body (plan § 4.10, review C2). Three routes take
    a password — /auth/login, /auth/register and, from Stage 2, /connections/google — and a
    default 422 would show it back on screen. App-wide so a route added later is covered.
    """
    fields = sorted({".".join(str(x) for x in err.get("loc", ()) if x != "body")
                     for err in exc.errors()})
    return JSONResponse(status_code=422,
                        content={"detail": "Some fields are missing or invalid.",
                                 "fields": [f for f in fields if f]})


@app.middleware("http")
async def require_auth(request: Request, call_next):
    """
    Gate every HTTP endpoint except the app shell and /auth/login.

    Deliberately a middleware rather than a per-endpoint dependency: the failure mode
    being closed off is an endpoint that nobody remembered to protect, and a middleware
    is the only version of this that cannot be forgotten when the next route is added.

    Does NOT cover /ws — Starlette never runs HTTP middleware for a WebSocket
    handshake. That path is gated inside the endpoint; see websocket_endpoint().

    It also decides the two things no route may get wrong by forgetting (plan § 4.3):
    the caller's identity is put on `request.state.identity` for `bound_persona()`, and
    The Book (`/monitor/*`) and the server-to-server routes (`/internal/*`) refuse an
    account user's token outright.
    """
    # CORS preflight carries no credentials by design; let CORSMiddleware answer it.
    if request.method == "OPTIONS" or auth.is_open_path(request.url.path):
        return await call_next(request)

    token = auth.credential_from_headers(
        request.headers.get("authorization"),
        request.cookies.get(auth.COOKIE_NAME),
    )
    identity = auth.decode_token(token)
    if identity is None:
        return JSONResponse({"detail": "Authentication required."}, status_code=401)
    path = request.url.path
    if (path.startswith("/monitor/") or path in _ADMIN_ONLY_PATHS) and not identity.is_admin_or_service:
        return JSONResponse({"detail": "Not available to this account."}, status_code=403)
    if path.startswith("/internal/") and identity.role != "service":
        return JSONResponse({"detail": "Not available to this account."}, status_code=403)
    request.state.identity = identity
    return await call_next(request)


# FastAPI's generated API docs list every route, /internal/* included — Mike's, not hers.
_ADMIN_ONLY_PATHS = frozenset({"/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json"})


def bound_persona(identity: "auth.Identity", named: str | None) -> str:
    """
    The persona a request is for. **The one place this is decided** (plan § 4.3).

    - A `user` or `admin` token is bound to one persona. A request that names a different
      one is refused (403) — never quietly served as either.
    - A `service` token is the internal clients' (scheduler, The Book, scripts). It names
      the persona per request, and one that names none is refused (400): there is no
      default to fall back to, by design.
    """
    named = (named or "").strip() or None
    if identity.role in ("user", "admin"):
        if named and named != identity.persona:
            raise HTTPException(status_code=403, detail="That isn't your account.")
        return identity.persona
    if not named:
        raise HTTPException(status_code=400, detail="This request must name a persona.")
    try:
        return validate_persona_name(named)
    except PersonaError as e:
        raise HTTPException(status_code=400, detail=str(e))


def request_persona(request: Request, named: str | None = None) -> str:
    """`bound_persona()` for an HTTP route — the identity the middleware attached."""
    return bound_persona(request.state.identity, named)


class LoginRequest(BaseModel):
    username: str = ""
    password: str


def _persona_exists(name: str) -> bool:
    """A persona Mike can sign in as with the admin password: one with an identity file."""
    from core.persona import persona_md
    try:
        return persona_md(name).exists()
    except PersonaError:
        return False


async def _refuse_login(detail: str = "Incorrect username or password.",
                        status_code: int = 401):
    # Awaited here rather than in core.auth so the delay never blocks the event loop.
    auth.note_login_failure()
    delay = auth.failure_delay()
    if delay:
        await asyncio.sleep(delay)
    raise HTTPException(status_code=status_code, detail=detail)


# A fixed hash for the timing-equaliser in auth_login — never matches anything real.
_DUMMY_HASH = ("scrypt$16384$8$1$AAAAAAAAAAAAAAAAAAAAAA==$"
               "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
_MAX_PASSWORD_LENGTH = 256   # scrypt over a multi-MB body is a cheap DoS (review F8)

# Said only after a correct password, so a wrong guess never learns whether a name waits.
_STATUS_REFUSALS = {
    "pending": "Your account is waiting for approval.",
    "rejected": "This request wasn't approved.",
    "disabled": "This account is switched off.",
}


@app.post("/auth/login")
async def auth_login(req: LoginRequest, response: Response) -> dict:
    """
    Exchange a username and password for a session token bound to that one persona.

    Two kinds of sign-in (plan § 4.1):
      - an **account** (`core/accounts.py`) with its own password → a `user` token for
        that account. The admin password never opens an account (D1): Mike reads an
        account user's history through The Book, but cannot write into it as her.
      - the **admin password** with the name of an existing persona that is not an
        account (`mike`, the test personas) → an `admin` token for that persona.

    Returns the token in the body *and* sets it as a cookie. Both carry the same value:
    the cookie serves the same-origin browser, the body serves the Android app, which is
    cross-origin and so never receives a SameSite=Lax cookie.
    """
    username = (req.username or "").strip().lower()
    if not username or not req.password or len(req.password) > _MAX_PASSWORD_LENGTH:
        await _refuse_login()

    from core import accounts as accounts_mod
    try:
        account = accounts_mod.get(username)
    except Exception:
        logger.exception("[auth] account store unreadable at login")
        raise HTTPException(status_code=503, detail="Sign-in is unavailable right now.")

    if account is not None:
        entry = await asyncio.to_thread(accounts_mod.authenticate, username, req.password)
        if entry is None:
            await _refuse_login()
        if entry.get("status") != "active":
            auth.note_login_success()   # the password was right; this is not a guess
            raise HTTPException(status_code=403,
                                detail=_STATUS_REFUSALS.get(entry.get("status"),
                                                            "This account can't sign in."))
        token = auth.issue_token(persona=username, role="user",
                                 cred_version=int(entry.get("cred_version") or 0))
        role = "user"
    elif auth.is_admin_password(req.password) and _persona_exists(username):
        token = auth.issue_token(persona=username, role="admin")
        role = "admin"
    else:
        # Spend the same scrypt an account check would, so a refusal's timing does not
        # say whether the name is an account (review F4).
        await asyncio.to_thread(accounts_mod.verify_password, req.password, _DUMMY_HASH)
        await _refuse_login()

    auth.note_login_success()
    response.set_cookie(
        auth.COOKIE_NAME, token,
        httponly=True,      # unreachable from JS, so an XSS in the PWA cannot lift it
        secure=True,        # HTTPS only — the VM serves behind a Tailscale cert
        samesite="lax",
        max_age=auth.TOKEN_TTL_SECONDS,
        path="/",
    )
    return {"token": token, "expires_in": auth.TOKEN_TTL_SECONDS,
            "persona": username, "role": role}


@app.get("/auth/notice")
async def auth_notice() -> dict:
    """The sign-up notice (D11) — open, because it is read before an account exists. The
    version travels back in the sign-up request, so the record names the text she saw."""
    from core.consent import current_text
    version, text = current_text("base_configuration")
    return {"scope": "base_configuration", "text_version": version, "text": text}


class RegisterRequest(BaseModel):
    username: str
    display_name: str
    password: str
    timezone: str = ""
    city: str = ""
    consent: dict = {}


# Sign-up is the one open route that writes. Bounded per server process (plan § 4.4):
# at most 10 attempts an hour, and the same escalating delay as a failed sign-in after a
# run of refusals. MAX_PENDING in core/accounts.py caps what can be waiting at once.
_REGISTER_WINDOW_SECONDS = 3600
_REGISTER_MAX_PER_WINDOW = 10
_register_attempts: deque = deque()
_register_failures = 0


@app.post("/auth/register")
async def auth_register(req: RegisterRequest) -> dict:
    """
    Ask for an account. Creates a `pending` entry and nothing else — no persona, no
    token, no scheduler. Mike approves it on the VM (`scripts/accounts.py approve`).

    The request must carry the sign-up permission the app's notice records (D11):
    `consent: {"scope": "base_configuration", "text_version": "<shown>"}`.
    """
    global _register_failures
    now = datetime.now(timezone.utc).timestamp()
    while _register_attempts and now - _register_attempts[0] > _REGISTER_WINDOW_SECONDS:
        _register_attempts.popleft()
    if len(_register_attempts) >= _REGISTER_MAX_PER_WINDOW:
        raise HTTPException(status_code=429, detail="Try again later.")
    _register_attempts.append(now)

    from core import accounts as accounts_mod
    from core.consent import CURRENT_VERSIONS
    # The record must name a text she could actually have been shown — the current one.
    if (req.consent or {}).get("text_version") != CURRENT_VERSIONS["base_configuration"]:
        req.consent = {}   # register() refuses with the plain "read and accept" message
    try:
        await asyncio.to_thread(
            accounts_mod.register, req.username, req.display_name, req.password,
            req.timezone, req.consent, req.city)
    except accounts_mod.AccountError as e:
        _register_failures += 1
        if _register_failures > 1:
            await asyncio.sleep(min(0.25 * (2 ** min(_register_failures - 1, 5)), 5.0))
        status = {"taken": 409, "limit": 429}.get(e.code, 400)
        raise HTTPException(status_code=status, detail=str(e))
    _register_failures = 0
    return {"status": "pending",
            "message": "Request sent. You can sign in once it's approved."}


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
        # Which conversation an exchange belongs to. NULL is the ordinary pipeline;
        # 'interview' marks the first interview's turns (multi-user plan § 4.7), so its
        # whole transcript can be handed back to the interviewer as history.
        try:
            await db.execute("ALTER TABLE exchanges ADD COLUMN channel TEXT")
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


_APP_STARTED_TURN = "(The app started this turn.)"


async def _interview_history(persona: str) -> list[dict]:
    """
    The whole interview so far as {role, content} pairs — what the interviewer gets as
    history (plan § 4.7), not the pipeline's five turns. The opening and a resume were
    started by the app, so their stored user side is empty; the model is shown the prompt
    that started them instead.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT user, assistant FROM exchanges WHERE persona=? AND channel='interview' "
            "ORDER BY id ASC", (persona,),
        ) as cursor:
            rows = await cursor.fetchall()
    pairs: list[dict] = []
    for row in rows:
        pairs.append({"role": "user", "content": row["user"] or _APP_STARTED_TURN})
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


# The turn origins the trace is allowed to record. Deliberately a closed set, not
# whatever the client sends: the field is written into every trace row and a client
# could otherwise put arbitrary text there.
_TURN_SOURCES = {"ui", "headset"}


def normalise_turn_source(value) -> str:
    """
    Map a client-supplied turn origin onto the closed set, defaulting to "ui".

    Only "headset" is distinguished from ordinary use, and for one reason: a headset
    press is the only way a turn can start without the user meaning it — in a pocket,
    at a median ~26k input tokens of Coordinator, specialists and Synthesizer. Nothing
    else in a trace separates a stray press from a real question, and it cannot be
    worked out afterwards, which is why the field is recorded from the first line
    rather than derived later.
    """
    # isinstance first, not just membership: receive_json accepts any JSON, so a
    # client can send {"source": {...}} or a list, and `x in <set>` raises TypeError
    # on an unhashable value — inside the WebSocket loop, which would drop the socket.
    # Found by tests/test_turn_source_marker.py rather than by a user losing a session.
    if isinstance(value, str) and value in _TURN_SOURCES:
        return value
    return "ui"


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


async def _get_exchange(persona: str, exchange_id: str) -> dict | None:
    """The stored exchange with this id, or None if it was never completed."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, exchange_id, user, assistant, ts, attachments, "
            "COALESCE(proactive,0) AS proactive FROM exchanges "
            "WHERE persona=? AND exchange_id=?",
            (persona, exchange_id),
        ) as cursor:
            row = await cursor.fetchone()
    return _row_with_attachments(row) if row else None


async def _save_exchange(persona: str, exchange_id: str, user: str, assistant: str,
                         proactive: bool = False,
                         attachments: list[dict] | None = None,
                         channel: str | None = None) -> int:
    """Persist a completed exchange. Returns the new row id."""
    ts = datetime.utcnow().isoformat() + "Z"
    meta = json.dumps(_public_attachments(attachments)) if attachments else None
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT OR IGNORE INTO exchanges "
            "(exchange_id, persona, user, assistant, ts, proactive, attachments, channel) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (exchange_id, persona, user, assistant, ts, 1 if proactive else 0, meta, channel),
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

        for name, fn, executor in (
            ("embedding", _load_embedder, _INDEX_EXECUTOR),
            ("whisper", _load_whisper, _STT_EXECUTOR),
            # Not Kokoro, on purpose (plan § 4.12.2, D14): the voice model is the server's
            # memory growth, so it loads only in core/tts_worker.py's helper process, on the
            # first spoken reply, and leaves with that process after 10 idle minutes.
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


@app.on_event("shutdown")
async def _shutdown() -> None:
    # Belt and braces: the helper also exits on its parent-death signal and when its pipe
    # closes, but a clean stop should not wait on either.
    tts_worker.shutdown()


def _refuse_side_door(request: Request, persona: str, agent: str) -> None:
    """
    /session and /session/stream predate accounts and take any agent name. For an account
    user they are not a way round the app's own rules (Stage 2 review F2): only the ordinary
    pipeline, and not while her interview is running — that conversation goes through /ws,
    where it is recorded as the interview. Admin and service callers are unchanged.
    """
    if request.state.identity.role != "user":
        return
    if agent != "coordinator":
        raise HTTPException(status_code=403, detail="Not available to this account.")
    if interview_mod.status(persona) == "active":
        raise HTTPException(status_code=409, detail="Finish or pause setting up first.")


# Background tasks the server starts and nobody awaits. asyncio keeps only a weak reference to
# a task, so one held nowhere can be collected mid-run (Stage 2 review F5).
_BG_TASKS: set = set()


def _spawn(coro) -> None:
    task = asyncio.create_task(coro)
    _BG_TASKS.add(task)
    task.add_done_callback(_BG_TASKS.discard)


@app.post("/session", response_model=SessionResponse)
async def session(req: SessionRequest, request: Request) -> SessionResponse:
    """Run a single orchestrator turn and return the text response."""
    if not req.input.strip():
        raise HTTPException(status_code=400, detail="Input is empty.")
    persona = request_persona(request, req.persona)
    _refuse_side_door(request, persona, req.agent)
    try:
        agent = req.agent
        history = _session_history.setdefault(persona, []) if agent == "coordinator" else None
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None, lambda: run_session(agent, req.input, persona=persona, provider=req.provider, history=history)
        )
        _log_conversation(req.input, response, agent, persona)
        return SessionResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/session/stream")
async def session_stream(req: SessionRequest, request: Request):
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

    persona = request_persona(request, req.persona)
    _refuse_side_door(request, persona, req.agent)
    history = _session_history.setdefault(persona, [])

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


# A `send` is answered at most once per exchange_id. The client keeps every message
# until its reply arrives and resends what is unconfirmed after a reconnect — that is
# what stops a message typed into a dead connection from vanishing. Without this guard
# each resend would run the whole pipeline again (a median ~26k input tokens) and the
# second reply would be dropped by _save_exchange's INSERT OR IGNORE, so the duplicate
# would be paid for and never seen.
#
# Memory only, deliberately. A turn in flight dies with the process, so after a restart
# a resend SHOULD run; nothing here needs to outlive the server that created it.
_inflight_exchanges: set[tuple[str, str]] = set()
# A retracted reply is never saved, so the table cannot answer for it — and re-running
# a filtered turn because its retract was lost in a dropped socket would be re-rolling
# against the output filter. Bounded; the oldest are forgotten first.
_retracted_exchanges: dict[tuple[str, str], dict] = {}
_RETRACTED_KEEP = 200


def _after_interview_turn(persona: str, user: str, reply: str) -> None:
    """Keep the pipeline's short history current, so that once she leaves the interview the
    pipeline's recent turns include its last ones ("as we were saying…" works)."""
    history = _session_history.setdefault(persona, [])
    history.extend([{"role": "user", "content": user or _APP_STARTED_TURN},
                    {"role": "assistant", "content": reply}])
    del history[:-10]


async def _broadcast_interview_status(persona: str) -> None:
    """Every device of hers learns the interview's state — the chips follow it."""
    status = interview_mod.status(persona)
    if status is not None:
        await manager.broadcast(persona, {"type": "interview", "status": status})


async def _interview_proactive_turn(persona: str, prompt: str, opening: bool = False) -> None:
    """
    An interviewer turn the app started — the opening, or picking up after *Continue setting
    up*. Saved and broadcast as a proactive exchange with an empty user side, so no device
    renders the prompt as something she said.
    """
    loop = asyncio.get_running_loop()
    try:
        history = await _interview_history(persona)
        reply = await loop.run_in_executor(
            None, interview_mod.run_turn, persona, prompt, history)
    except Exception:
        logger.exception(f"[interview] proactive turn failed for {persona}")
        if opening:
            # Her next connection claims it again and retries (Stage 2 review F4) — and every
            # device hears it, or the chip would keep offering "Finish later" (verify).
            interview_mod.release_start(persona)
            await _broadcast_interview_status(persona)
        return
    exchange_id = f"interview-{uuid.uuid4().hex[:12]}"
    new_id = await _save_exchange(persona, exchange_id, "", reply, proactive=True,
                                  channel="interview")
    _log_conversation("", reply, interview_mod.AGENT, persona, proactive=True)
    _after_interview_turn(persona, "", reply)
    await manager.broadcast(persona, {
        "type": "message", "id": new_id, "exchange_id": exchange_id, "user": "",
        "assistant": reply, "ts": datetime.utcnow().isoformat() + "Z", "attachments": [],
        "proactive": True,
    })
    await _broadcast_interview_status(persona)


class InterviewRequest(BaseModel):
    persona: str | None = None


@app.get("/interview")
async def interview_status(request: Request, persona: str | None = None) -> dict:
    """The interview's state for the app's chips. `null` for anyone without an interview."""
    return {"status": interview_mod.status(request_persona(request, persona))}


@app.post("/interview/pause")
async def interview_pause(req: InterviewRequest, request: Request) -> dict:
    """*Finish later*: her next message goes to Metatron as usual; nothing is lost."""
    persona = request_persona(request, req.persona)
    if not interview_mod.pause(persona):
        raise HTTPException(status_code=409, detail="There is no active interview to pause.")
    await _broadcast_interview_status(persona)
    return {"status": "paused"}


@app.post("/interview/resume")
async def interview_resume(req: InterviewRequest, request: Request,
                           background: BackgroundTasks) -> dict:
    """*Continue setting up*: active again, and the interviewer picks up where coverage says
    things stand — it speaks first, so she is not left wondering what to say."""
    persona = request_persona(request, req.persona)
    if not interview_mod.resume(persona):
        raise HTTPException(status_code=409, detail="There is no paused interview to resume.")
    await _broadcast_interview_status(persona)
    # After the response, not a loose task: the chip answers at once, and the turn is owned
    # by the request's lifecycle rather than left for the loop to drop.
    background.add_task(_interview_proactive_turn, persona,
                        "(She has come back to continue setting up. Pick up where things stand.)")
    return {"status": "active"}


# ---------------------------------------------------------------------------
# Her permissions and her Google connection (plan § 4.10, § 4.11 — D9, Mike 2026-10-27:
# "She should be notified through the app and provide permission herself.")
#
# Every route here is bound to the caller's own persona. The permission records are the
# enforcement, in Python: Connect refuses without `correspondence_read`, tone profiling
# refuses without `tone_profile` (tools/tone.py), and withdrawing acts at once.
# ---------------------------------------------------------------------------

class ConsentGrant(BaseModel):
    text_version: str
    persona: str | None = None


def _consent_view(persona: str) -> dict:
    from core import consent
    out = {}
    for scope in consent.APP_SCOPES:
        rec = consent.current(scope, persona)
        version, text = consent.current_text(scope)
        out[scope] = {"granted": rec is not None,
                      "granted_at": rec.get("granted_at") if rec else None,
                      "text_version": version, "text": text}
    return out


@app.get("/consents")
async def consents_get(request: Request, persona: str | None = None) -> dict:
    """Her permissions and the exact text of each — what the Connections panel shows."""
    persona_key = request_persona(request, persona)
    return {"consents": await asyncio.to_thread(_consent_view, persona_key)}


@app.post("/consents/{scope}")
async def consents_grant(scope: str, req: ConsentGrant, request: Request) -> dict:
    """Her tap on a permission screen. The record names the text version she was shown."""
    from core import consent
    persona_key = request_persona(request, req.persona)
    # Her permission is hers to give (D9): a record says SHE tapped, so an admin or service
    # token — Mike signed in as her persona — cannot write one (Stage 2 review F6). Withdrawing
    # stays open to every bound caller; refusing a withdrawal could only keep data flowing.
    if request.state.identity.role != "user":
        raise HTTPException(status_code=403, detail="Only the account holder can give this.")
    if scope not in consent.APP_SCOPES:
        raise HTTPException(status_code=404, detail="No such permission.")
    if req.text_version != consent.CURRENT_VERSIONS[scope]:
        raise HTTPException(status_code=409, detail="That notice has changed — please read it again.")
    rec = await asyncio.to_thread(consent.grant, scope, persona_key, req.text_version)
    return {"scope": scope, "granted_at": rec["granted_at"]}


def _withdraw_blocking(scope: str, persona: str) -> dict:
    from core import consent
    withdrew = consent.withdraw(scope, persona)
    effect: dict = {"withdrawn": withdrew}
    with persona_scope(persona):
        if scope == "correspondence_read":
            # Reading her mail and calendar was what connecting allowed — so it ends here.
            from core.connections import disconnect_google
            effect["disconnected"] = bool(disconnect_google(persona))
        elif scope == "tone_profile":
            # Review P2: withdrawal removes what was learned, not just future learning.
            from tools.tone import forget_tone_profiles
            effect["profiles_removed"] = forget_tone_profiles(persona)
    return effect


@app.delete("/consents/{scope}")
async def consents_withdraw(scope: str, request: Request, persona: str | None = None) -> dict:
    from core import consent
    persona_key = request_persona(request, persona)
    if scope not in consent.APP_SCOPES:
        raise HTTPException(status_code=404, detail="No such permission.")
    return await asyncio.to_thread(_withdraw_blocking, scope, persona_key)


class GoogleConnectRequest(BaseModel):
    address: str
    app_password: str
    persona: str | None = None


@app.get("/connections")
async def connections_get(request: Request, persona: str | None = None) -> dict:
    """Connection status — the address, calendars found and when checked. Never the password."""
    from core.connections import status
    persona_key = request_persona(request, persona)
    return {"google": await asyncio.to_thread(status, persona_key)}


@app.post("/connections/google")
async def connections_google(req: GoogleConnectRequest, request: Request) -> dict:
    """
    Test the Google address and app password, and only if both CalDAV and IMAP work, write
    her calendar and mail settings — the password to credentials.yaml alone (§ 4.10).

    It is an HTTP route, not a chat message, so the password never reaches a model, a
    conversation log, a trace or a quality event; the app-wide 422 handler never echoes it.
    """
    from core import consent
    from core.connections import connect_google
    persona_key = request_persona(request, req.persona)
    if len(req.app_password) > 256 or len(req.address) > 320:
        raise HTTPException(status_code=400, detail="That doesn't look like a Google address and app password.")
    if not consent.is_granted("correspondence_read", persona_key):
        raise HTTPException(status_code=403,
                            detail="Please read and accept the permission screen first.")
    return await asyncio.to_thread(connect_google, persona_key, req.address, req.app_password)


@app.delete("/connections/google")
async def connections_google_delete(request: Request, persona: str | None = None) -> dict:
    from core.connections import disconnect_google
    persona_key = request_persona(request, persona)
    return await asyncio.to_thread(disconnect_google, persona_key)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, persona: str | None = None) -> None:
    """
    WebSocket endpoint for real-time cross-device conversation sync.

    Query param: ?persona=X — required for a service token (the scheduler, the terminal
    client); for a signed-in user it may be omitted, and naming anyone else is refused.

    Client → server message types:
      {type: "send", exchange_id, input, provider, attachments}  — submit a prompt.
          `attachments` is a list of ids returned by POST /upload; files themselves
          never travel over this socket. Unknown ids are dropped, not rejected.
          Idempotent on exchange_id: a resend is acknowledged, never run twice.
      {type: "catchup", since_id}                   — fetch missed exchanges on reconnect

    Server → client message types:
      {type: "accepted", exchange_id}                — the send was received (sender only)
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
    identity = auth.decode_token(opening.get("token")) if opening.get("type") == "auth" else None
    if identity is None:
        await websocket.send_json({"type": "auth_failed"})
        await websocket.close(code=1008)
        return
    # The socket's persona comes from the credential, after it is verified — never from the
    # URL alone (plan § 3.7). Same rule as every HTTP route: bound_persona().
    try:
        persona_key = bound_persona(identity, persona)
    except HTTPException as e:
        await websocket.send_json({"type": "auth_failed", "reason": e.detail})
        await websocket.close(code=1008)
        return
    persona_orch = persona_key
    await websocket.send_json({"type": "auth_ok", "persona": persona_key})
    # ----------------------------------------------------------------------

    await manager.connect(websocket, persona_key)

    recent = await _get_recent_exchanges(persona_key)
    last_id = recent[-1]["id"] if recent else 0
    await websocket.send_json({"type": "history", "messages": recent, "last_id": last_id})

    # The first interview (plan § 4.7). `status` is None for every persona without a state
    # file — Mike and the test personas — and nothing below runs for them. A user's FIRST
    # signed-in connection claims the start atomically (a reconnect cannot start it twice)
    # and the opening is generated in the background, arriving like any proactive message.
    istatus = interview_mod.status(persona_key)
    if istatus is not None:
        await websocket.send_json({"type": "interview", "status": istatus})
    if (istatus == "not_started" and identity.role == "user"
            and interview_mod.claim_start(persona_key)):
        _spawn(_interview_proactive_turn(persona_key, interview_mod.OPENING_PROMPT,
                                         opening=True))

    async def _heartbeat() -> None:
        while True:
            await asyncio.sleep(30)
            try:
                await websocket.send_json({"type": "ping"})
            except Exception:
                return

    hb_task = asyncio.create_task(_heartbeat())
    # Every exchange this socket has claimed in _inflight_exchanges. A socket that dies
    # between claiming a message and finishing it releases the claim on the way out,
    # so the message can still run when the client resends it.
    claimed: set[tuple[str, str]] = set()

    try:
        while True:
            data = await websocket.receive_json()
            received_at = datetime.now(timezone.utc)
            msg_type = data.get("type")
            # Revocation reaches an open socket too (review F1): `disable` and a password
            # reset bump cred_version, and a socket kept alive by heartbeats would otherwise
            # keep serving the account until it happened to reconnect. The store read is
            # cached by mtime, so this is a stat per frame.
            if msg_type in ("send", "catchup") and auth.decode_token(opening.get("token")) is None:
                try:
                    await websocket.send_json({"type": "auth_failed"})
                    await websocket.close(code=1008)
                except Exception:
                    pass
                return

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

                # Claimed before the first await below, so two sockets resending the
                # same message at once cannot both get past this check.
                inflight_key = (persona_key, exchange_id)
                if inflight_key in _inflight_exchanges:
                    # Still running for a socket that has since died. Its chunks are
                    # broadcast to every other socket, this one included, so the
                    # acknowledgement is all this socket needs.
                    await websocket.send_json({"type": "accepted", "exchange_id": exchange_id})
                    continue
                _inflight_exchanges.add(inflight_key)
                claimed.add(inflight_key)
                if inflight_key in _retracted_exchanges:
                    _inflight_exchanges.discard(inflight_key)
                    claimed.discard(inflight_key)
                    await websocket.send_json({"type": "accepted", "exchange_id": exchange_id})
                    await websocket.send_json(_retracted_exchanges[inflight_key])
                    continue
                stored = await _get_exchange(persona_key, exchange_id)
                if stored:
                    # Answered already; the reply was lost on the way back. Replayed as
                    # one chunk and a done, the frames the client already handles.
                    _inflight_exchanges.discard(inflight_key)
                    claimed.discard(inflight_key)
                    await websocket.send_json({"type": "accepted", "exchange_id": exchange_id})
                    await websocket.send_json({"type": "chunk", "exchange_id": exchange_id,
                                               "text": stored["assistant"]})
                    await websocket.send_json({"type": "done", "exchange_id": exchange_id})
                    continue
                # Not allowed to stop the turn. Another socket may already have been told
                # this id is in flight and be waiting on its broadcast; a dead sender is
                # tolerated the same way _send_to_sender tolerates one mid-turn.
                try:
                    await websocket.send_json({"type": "accepted", "exchange_id": exchange_id})
                except Exception:
                    pass

                provider = data.get("provider") or None
                # Scheduler-initiated exchanges are flagged so traces record that
                # Metatron opened the conversation rather than the user.
                proactive = bool(data.get("proactive"))
                # D2 backstop (Stage 3 review S1): no proactive turn opens while a new user's
                # first interview holds — whichever caller forgot its own check. `held` is
                # the frame send_one already reads as "nothing to say"; nothing is recorded
                # or broadcast. The scheduler and nudge_tick check first, so this is quiet.
                if proactive and interview_mod.holds_proactive(persona_key):
                    _inflight_exchanges.discard(inflight_key)
                    claimed.discard(inflight_key)
                    await websocket.send_json({"type": "held", "exchange_id": exchange_id})
                    continue
                # A day-plan nudge (tools/day_plan.py nudge_tick): the Synthesizer decides whether
                # to speak at all, so nothing reaches any device until it has — no stream_start,
                # no chunk broadcast — and a reply of exactly [HOLD] is recorded nowhere.
                nudge = proactive and bool(data.get("nudge"))
                source = normalise_turn_source(data.get("source"))
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
                # While her interview is active her own messages go to the interviewer,
                # with the whole interview as history — never a proactive turn, which the
                # scheduler's hold gate keeps away while the interview runs.
                interview_mode = (not proactive
                                  and interview_mod.status(persona_key) == "active")
                interview_history = (await _interview_history(persona_key)
                                     if interview_mode else None)

                # Notify other devices that a new exchange is starting
                if not nudge:
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
                        if interview_mode:
                            # Not streamed: one agent, one reply. Filtered and pending-
                            # receipt-checked inside run_turn before it gets here.
                            reply = interview_mod.run_turn(persona_orch, user_input,
                                                           interview_history)
                            asyncio.run_coroutine_threadsafe(queue.put(reply), loop).result()
                            return
                        for chunk in run_pipeline_session_stream(
                            user_input, persona=persona_orch, provider=provider,
                            history=history, is_proactive=proactive,
                            received_at=received_at, attachments=pipeline_attachments,
                            source=source, nudge=nudge,
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
                            if not nudge:
                                await manager.broadcast(persona_key, chunk_payload, exclude=websocket)

                    await asyncio.wrap_future(producer)

                    if retracted:
                        # `text` present only for [RETRACT_WITH]; the client falls back
                        # to its canned line when it is absent, so a plain filter
                        # suppression is unchanged.
                        retract_payload = {"type": "retract", "exchange_id": exchange_id}
                        if retract_text:
                            retract_payload["text"] = retract_text
                        _retracted_exchanges[inflight_key] = retract_payload
                        while len(_retracted_exchanges) > _RETRACTED_KEEP:
                            del _retracted_exchanges[next(iter(_retracted_exchanges))]
                        await _send_to_sender(retract_payload)
                        await manager.broadcast(persona_key, retract_payload, exclude=websocket)
                    elif nudge and "".join(accumulated).strip() == "[HOLD]":
                        # Held: the Synthesizer chose not to speak. No row, no log line, no
                        # broadcast, and the held turn leaves the session history it never
                        # belonged in (the pipeline appended it like any turn).
                        if (len(history) >= 2 and history[-1].get("role") == "assistant"
                                and str(history[-1].get("content") or "").strip() == "[HOLD]"):
                            del history[-2:]
                        await _send_to_sender({"type": "held", "exchange_id": exchange_id})
                    elif not errored:
                        full_response = "".join(accumulated)
                        done_payload = {"type": "done", "exchange_id": exchange_id}
                        await _send_to_sender(done_payload)
                        await manager.broadcast(persona_key, done_payload, exclude=websocket)
                        new_id = await _save_exchange(persona_key, exchange_id, user_input,
                                                      full_response, proactive=proactive,
                                                      attachments=attached,
                                                      channel="interview" if interview_mode else None)
                        await _bind_attachments([a["id"] for a in attached], exchange_id)
                        _log_conversation(user_input, full_response,
                                          interview_mod.AGENT if interview_mode else "coordinator",
                                          persona_orch, proactive=proactive)
                        if interview_mode:
                            _after_interview_turn(persona_key, user_input, full_response)
                            await _broadcast_interview_status(persona_key)
                        await manager.broadcast(persona_key, {
                            "type": "message",
                            "id": new_id,
                            "exchange_id": exchange_id,
                            "user": user_input,
                            "assistant": full_response,
                            "ts": datetime.utcnow().isoformat() + "Z",
                            "attachments": _public_attachments(attached),
                            # Without this, a device that missed stream_start — and every
                            # device on a nudge, which sends none — renders a scheduler
                            # prompt as something the user said (index.html applyCatchupRow).
                            "proactive": proactive,
                        }, exclude=websocket)
                finally:
                    with _active_lock:
                        _active_streams -= 1
                    _inflight_exchanges.discard(inflight_key)
                    claimed.discard(inflight_key)

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
        _inflight_exchanges.difference_update(claimed)
        manager.disconnect(websocket, persona_key)


class ConfirmRequest(BaseModel):
    token: str
    persona: str | None = None


@app.get("/pending-confirmations")
async def pending_confirmations(request: Request, persona: str | None = None) -> dict:
    """Actions awaiting the user's approval. The app polls this to render its prompt."""
    from tools.confirm import pending
    with persona_scope(request_persona(request, persona)):
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
async def confirm_action(req: ConfirmRequest, request: Request) -> dict:
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
    persona_key = request_persona(request, req.persona)
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
async def decline_action(req: ConfirmRequest, request: Request) -> dict:
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
    persona_key = request_persona(request, req.persona)
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
async def location_ping(req: LocationPing, request: Request) -> dict:
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
    persona_key = request_persona(request, req.persona)
    try:
        return await asyncio.to_thread(
            _record_location, req.lat, req.lon, req.accuracy, req.ts, persona_key)
    except Exception as e:
        # Deliberately does not echo the request: the detail string is the one place a
        # coordinate could travel back out of this handler, and an exception message can
        # carry its arguments.
        logger.warning(f"[location] ping failed: {type(e).__name__}")
        raise HTTPException(status_code=500, detail="Could not record the location.")


# --- The task ledger's two taps (archive/plans/task_ledger_plan_2026-10-23.md § 6) ----------
#
# The Today panel lists what is outstanding and records a tap as done / skipped / dismissed;
# the proposal bar offers a close that an arriving message suggested. Both are the user's own
# act, recorded out of band — the model is not in the path. Like /location, neither writes a
# conversation row nor broadcasts: the head layer learns of a tap from the Tasks block on its
# next turn, which is where it reads task state anyway.
#
# Proposals deliberately do NOT go through tools/confirm.py. A card raised outside a turn is
# misattributed by the pending-receipt diff both pipeline twins take at turn start, and a
# confirm description is written into the conversation and re-rendered to the model — which
# would carry an email's attacker-written subject into the head-layer prompt. The subject and
# sender are joined here, at request time, for the user's eyes only.

class TaskActRequest(BaseModel):
    task_id: str = ""
    action: str = "done"
    proposal_id: str | None = None
    persona: str | None = None
    # Optional so the shipped app, which sends neither, keeps working until the APK that
    # asks for them is installed (reply latency plan § 6.3).
    reason: str | None = None
    followup: str | None = None


class ProposalDeclineRequest(BaseModel):
    proposal_id: str
    persona: str | None = None


def _task_call(persona: str, fn, *args, **kwargs):
    """Run a ledger call on a worker thread with the persona bound inside it — identity is
    thread-local and fail-closed, the same reasoning as `_approve_and_execute`."""
    from core.persona import persona_scope
    with persona_scope(persona):
        return fn(*args, **kwargs)


def _task_result(message: str) -> dict:
    """An `error:` result from the ledger is a failure the app must show as one — a rejected
    close reported as done is the exact failure tools/confirm.py was built to prevent."""
    if isinstance(message, str) and message.lstrip().lower().startswith("error"):
        raise HTTPException(status_code=400, detail=message)
    return {"status": "ok", "message": message}


@app.get("/tasks/today")
async def tasks_today(request: Request, persona: str | None = None, followup: int = 0) -> dict:
    """What is outstanding today, for the Today panel.

    `followup=1` is sent only by an app that can ask for the loose end; an older APK would draw
    the raw action name as a button and post it without one, so it is not offered there."""
    from tools.obligations import today_items
    items = await asyncio.to_thread(_task_call, request_persona(request, persona), today_items)
    if not followup:
        for item in items:
            item["actions"] = [a for a in item.get("actions", []) if a != "done_with_followup"]
    return {"items": items}


@app.get("/plan/today")
async def plan_today(request: Request, persona: str | None = None) -> dict:
    """The day plan, for the Today panel while it is being tested (archive/plans/
    day_planner_plan_2026-10-24.md § 9). `{}` when `show_in_app` is off — the move to
    "Synth only" is that flag, no client change. Polled with /tasks/today; it renders the stored
    plan after the gate's check and never waits on the calendar (a stale snapshot starts a
    background refresh, so the next poll has it)."""
    from tools.day_plan import today_view
    persona_key = request_persona(request, persona)
    try:
        return await asyncio.to_thread(_task_call, persona_key, today_view)
    except Exception:  # noqa: BLE001 — the panel shows tasks without a plan, never an error
        logger.warning("[day_plan] /plan/today failed", exc_info=True)
        return {}


@app.get("/settings/location")
async def settings_location(request: Request, persona: str | None = None) -> dict:
    """The persona's answer to "send your place with messages?" from the first interview:
    true, false, or null when never asked. The app uses it only to set a default it has not
    stored — a stored local choice always wins, and anything but true leaves it off
    (plan § 8.2; tests/test_location_onsend_default.js)."""
    from tools.day_shape import location_sharing
    persona_key = request_persona(request, persona)
    try:
        value = await asyncio.to_thread(_task_call, persona_key, location_sharing)
    except Exception:  # noqa: BLE001
        value = None
    return {"on_send": value}


@app.post("/tasks/act")
async def tasks_act(req: TaskActRequest, request: Request) -> dict:
    """A tap: done / skipped / dismissed on a task, or accepting a correspondence proposal."""
    from tools.obligations import act_from_app, resolve_proposal
    persona_key = request_persona(request, req.persona)
    if req.proposal_id:
        result = await asyncio.to_thread(_task_call, persona_key, resolve_proposal,
                                         req.proposal_id, True)
    else:
        result = await asyncio.to_thread(_task_call, persona_key, act_from_app,
                                         req.task_id, req.action,
                                         reason=req.reason, followup=req.followup)
    return _task_result(result)


def _proposals_for_display() -> list[dict]:
    from tools.intake import read_records
    from tools.obligations import pending_proposals
    props = pending_proposals()
    if not props:
        return []
    # Intake records are read for correspondence proposals only; a location proposal carries its
    # own basis ("You were at the gym at 18:05"), written by code, never by a stranger.
    wanted = {p["envelope_id"] for p in props
              if p.get("source", "correspondence") == "correspondence" and p.get("envelope_id")}
    records = ({r.get("id"): r for r in read_records() if r.get("id") in wanted}
               if wanted else {})
    out = []
    for p in props:
        if p.get("source") == "location":
            out.append({"proposal_id": p["proposal_id"], "task_id": p["task_id"],
                        "what": p["what"], "source": "location",
                        "basis": str(p.get("basis") or "")[:120],
                        "received": str(p.get("created") or "")[:25]})
            continue
        rec = records.get(p["envelope_id"]) or {}
        out.append({
            "proposal_id": p["proposal_id"], "task_id": p["task_id"], "what": p["what"],
            # Shown to the user only. Never stored on the task, never sent to a model.
            "sender": str(rec.get("sender_display") or rec.get("sender") or "")[:120],
            "subject": str(rec.get("subject") or "")[:200],
            "received": str(rec.get("received") or p.get("received") or "")[:25],
        })
    return out


@app.get("/tasks/proposals")
async def tasks_proposals(request: Request, persona: str | None = None) -> dict:
    """Pending correspondence proposals, oldest first. Read-only: no side effect, no card."""
    items = await asyncio.to_thread(_task_call, request_persona(request, persona),
                                    _proposals_for_display)
    return {"proposals": items}


@app.post("/tasks/proposals/decline")
async def tasks_proposal_decline(req: ProposalDeclineRequest, request: Request) -> dict:
    """"Not now": the task stays open and that message is never offered again for it."""
    from tools.obligations import resolve_proposal
    result = await asyncio.to_thread(_task_call, request_persona(request, req.persona),
                                     resolve_proposal, req.proposal_id, False)
    return _task_result(result)


# ---------------------------------------------------------------------------
# Server-to-server routes — one copy of each model on the VM (plan § 4.12.3)
#
# The per-user schedulers run with METATRON_NO_LOCAL_MODELS=1 and never load a model: the
# embedder (~0.9 GB) would otherwise land in every scheduler after its first weekly review,
# and two of them would undo the memory the voice helper frees. So their non-coordinator
# sessions, memory writes and memory searches run HERE, where the models already live.
# `service` tokens only — the middleware refuses any other role on /internal/*.
# ---------------------------------------------------------------------------

class InternalSessionRequest(BaseModel):
    agent: str
    input: str
    persona: str | None = None
    proactive: bool = True


@app.post("/internal/session")
async def internal_session(req: InternalSessionRequest, request: Request) -> dict:
    """
    A scheduled single-agent session (the weekly pattern-miner and physical reviews, …),
    run exactly as the scheduler ran it in-process: `run_session(..., proactive=True)` —
    traced as scheduled, spend-gated, no history.

    **Writes no conversation record** (review M1-N1): the in-process run never produced one,
    and the nightly CRM sweep reads every conversation row as something the user said. The
    coordinator is refused here: its scheduled turns ARE conversation and go over /ws.
    """
    persona = request_persona(request, req.persona)
    if not req.input.strip():
        raise HTTPException(status_code=400, detail="Input is empty.")
    if req.agent == "coordinator":
        raise HTTPException(status_code=400,
                            detail="Coordinator sessions are conversation — use /ws.")
    loop = asyncio.get_running_loop()
    try:
        # The default pool, not _INDEX_EXECUTOR: a multi-minute review must not hold up
        # every user's memory writes behind it.
        response = await loop.run_in_executor(
            None, lambda: run_session(req.agent, req.input, persona=persona, proactive=True))
    except Exception as e:
        logger.exception(f"[internal_session] persona={persona} agent={req.agent}")
        raise HTTPException(status_code=500, detail=str(e))
    return {"response": response}


class InternalIndexRequest(BaseModel):
    persona: str | None = None
    text: str
    source: str
    entry_date: str = ""


class InternalSearchRequest(BaseModel):
    persona: str | None = None
    query: str
    k: int = 5


def _scoped(persona: str, fn, *args):
    """Run on an executor thread with the persona bound INSIDE it — identity is
    thread-local and fail-closed, so binding around the executor call binds nothing."""
    with persona_scope(persona):
        return fn(*args)


@app.post("/internal/index")
async def internal_index(req: InternalIndexRequest, request: Request) -> dict:
    """Embed and store one memory entry for a scheduler process that holds no model."""
    from core import memory
    persona = request_persona(request, req.persona)
    if not req.text.strip():
        return {"ok": True}
    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(_INDEX_EXECUTOR, _scoped, persona, memory.index_entry_local,
                                   req.text, req.source, req.entry_date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True}


@app.post("/internal/search")
async def internal_search(req: InternalSearchRequest, request: Request) -> dict:
    """Search one persona's memory for a scheduler process that holds no model."""
    from core import memory
    persona = request_persona(request, req.persona)
    if req.k < 1 or req.k > 50:
        raise HTTPException(status_code=400, detail="k must be between 1 and 50.")
    loop = asyncio.get_running_loop()
    try:
        results = await loop.run_in_executor(_INDEX_EXECUTOR, _scoped, persona,
                                             memory.search_memory_local, req.query, req.k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"results": results}


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
async def subscribe(sub: PushSubscription, request: Request, persona: str | None = None) -> dict:
    """Register this browser's push subscription for the signed-in persona only."""
    from core.push import save_subscription
    result = save_subscription(sub.dict(), request_persona(request, persona))
    return {"status": result}


@app.post("/push/test")
async def push_test(request: Request, persona: str | None = None) -> dict:
    """Dev endpoint — a test push to the signed-in persona's own subscriptions."""
    from core.push import send_push
    return await asyncio.to_thread(send_push, title="Life Manager",
                                   body="Push notifications are working.",
                                   persona=request_persona(request, persona))


class FcmToken(BaseModel):
    token: str
    persona: str | None = None


@app.post("/push/fcm/register")
async def push_fcm_register(req: FcmToken, request: Request) -> dict:
    """The Android app's FCM token, for the signed-in persona only (day planner Stage C)."""
    from core.push import save_fcm_token
    return {"status": await asyncio.to_thread(save_fcm_token, req.token,
                                              request_persona(request, req.persona))}


@app.post("/push/fcm/unregister")
async def push_fcm_unregister(req: FcmToken, request: Request) -> dict:
    """Sign-out on the phone: its pings for this persona stop."""
    from core.push import remove_fcm_token
    return {"status": await asyncio.to_thread(remove_fcm_token, req.token,
                                              request_persona(request, req.persona))}


@app.get("/push/message/{msg_id}")
async def push_message(msg_id: str, request: Request, persona: str | None = None) -> dict:
    """The text behind an FCM ping — the ping itself carries only this id, so the message never
    travels through Google. Another persona's id reads exactly as an unknown one."""
    from core.push import fetch_message
    msg = await asyncio.to_thread(fetch_message, msg_id[:64], request_persona(request, persona))
    if msg is None:
        raise HTTPException(status_code=404, detail="No such message.")
    return msg


class RemindRequest(BaseModel):
    task_id: str
    minutes: int = 0
    when: str | None = None        # "tomorrow"
    persona: str | None = None


@app.post("/tasks/remind")
async def tasks_remind(req: RemindRequest, request: Request) -> dict:
    """'Not yet' → 'remind me in …' on a notification: the plan re-raises the task then."""
    from tools.day_plan import remind_later
    persona_key = request_persona(request, req.persona)
    result = await asyncio.to_thread(remind_later, req.task_id, req.minutes, persona_key,
                                     req.when)
    return _task_result(result)


def _feedback_blocking(persona: str) -> str:
    from tools.logger import write_quality_event
    with persona_scope(persona):
        return write_quality_event(
            event_type="USER_CORRECTION",
            source_agent="pwa_tap",
            detail="User tapped missed-the-mark affordance",
            session_id=datetime.utcnow().strftime("%Y-%m-%dT%H"),
        )


@app.post("/feedback")
async def feedback(request: Request, persona: str | None = None) -> dict:
    """PWA tap — record a USER_CORRECTION quality event, in the signed-in persona's tree.

    It used to name no persona and resolve whatever identity another thread happened to be
    serving (plan § 3.3) — a tap could be filed against the wrong person."""
    result = await asyncio.to_thread(_feedback_blocking, request_persona(request, persona))
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

@app.post("/tts")
async def tts(req: TTSRequest, request: Request, persona: str | None = None):
    """
    Generate speech audio — Kokoro af_heart primary, edge-tts fallback.

    Kokoro runs in its own helper process (core/tts_worker.py) since 2026-10-27, driven from
    the single TTS executor thread. It used to run inline in this async
    function, freezing the whole server for up to 120s: no HTTP responses, no
    WebSocket pings, nothing.
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text is empty.")
    persona_key = request_persona(request, persona)

    # [DB-0810-15] Pick the engine from the persona's response language, not from availability
    # alone. Kokoro is preferred where it can serve the language; where it cannot (Bulgarian) an
    # English Kokoro voice would read the text phonetically, so edge-tts wins instead.
    edge_voice = EDGE_VOICE
    lang_code = ""
    try:
        from core.translate import response_language
        lang = response_language(persona_key)
        if lang is not None:
            lang_code = lang[0]
            edge_voice = _EDGE_VOICE_BY_LANG.get(lang_code, EDGE_VOICE)
    except Exception:
        logger.warning("[tts] could not resolve response language — using the default voice")

    kokoro_can_serve = (not lang_code) or lang_code in _KOKORO_LANGS

    try:
        # find_spec, never `import kokoro`: importing it here would pull the voice model's
        # code into the server the helper exists to protect (review M2).
        if tts_worker.kokoro_installed() and kokoro_can_serve:
            loop = asyncio.get_running_loop()
            audio_path = await loop.run_in_executor(_TTS_EXECUTOR, tts_worker.synthesize, req.text)
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


def _transcribe_blocking(audio_bytes: bytes, persona: str) -> dict:
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
    # Each persona's recordings in its own tree (plan § 4.3). Mike's older recordings stay
    # in the global data/audio/ they were written to — nothing reads that folder, and
    # nothing here deletes them.
    date_dir = persona_data_dir(persona) / "audio" / datetime.now().strftime("%Y-%m-%d")
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
    # The persona selects whose contacts' names Whisper is primed with, when that is on.
    transcript = _transcribe(audio_array, persona)

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
async def transcribe_audio(request: Request, audio: UploadFile = File(...),
                           persona: str | None = None) -> dict:
    """
    Transcribe a voice recording with Whisper, locally. Audio never leaves this
    machine; the Web Speech API is deliberately not used.

    Runs on a dedicated executor. The semaphore returns a fast 503 on a
    concurrent request rather than queueing it invisibly until the client gives
    up — which previously surfaced as "Failed to fetch".

    The recording is filed under the signed-in persona, which also selects whose saved
    addresses the correction pass snaps to.
    """
    persona_key = request_persona(request, persona)
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
            _STT_EXECUTOR, _transcribe_blocking, audio_bytes, persona_key
        )


@app.post("/upload")
async def upload_attachment(request: Request, file: UploadFile = File(...),
                            persona: str | None = None) -> dict:
    """
    Store one photo or document for the persona, ready to be sent with a message.

    Upload and send are separate steps because the WebSocket carries JSON frames: a
    10 MB file base64'd into a socket frame would block every other frame on that
    connection, including the heartbeat the client uses to decide the socket is
    alive. The file goes over HTTP; the send frame carries only its id.

    The type is decided by sniffing the bytes, not by the Content-Type the browser
    asserts — see core/attachments.validate().
    """
    persona_key = request_persona(request, persona)
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
async def get_attachment(attachment_id: str, request: Request, persona: str | None = None):
    """
    Serve a stored file back to the client that owns it.

    The path comes from the database row, never from the URL, so there is no
    traversal surface — an id either resolves to a row for this persona or 404s.
    """
    persona_key = request_persona(request, persona)
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


@app.get("/monitor/accounts")
async def monitor_accounts() -> dict:
    """
    Every account and its status — never a password hash (plan § 4.4).

    Admin and service tokens, like every /monitor route: its only caller is
    scripts/sync_dev_backlog.py, which holds a service token and turns the pending count
    into the session-start line that tells Mike a request is waiting (review L8).
    """
    from core import accounts as accounts_mod
    rows = await asyncio.to_thread(accounts_mod.list_accounts)
    keep = ("username", "display_name", "status", "created_at", "decided_at", "decided_by")
    return {"accounts": [{k: r.get(k) for k in keep} for r in rows]}


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
# Never served by /monitor/file or /monitor/history: the account store carries password
# hashes, which /monitor/accounts deliberately leaves out (review F5).
_UNREADABLE_DATA = ("data/accounts/",)


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
    if path.startswith(_UNREADABLE_DATA):
        raise HTTPException(status_code=403, detail="Not readable through The Book.")

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
    if path.startswith(_UNREADABLE_DATA):
        raise HTTPException(status_code=403, detail="Not readable through The Book.")

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


@app.get("/monitor/tool")
async def monitor_tool(
    persona: str | None = None,
    presence: str | None = None,
    name: str | None = None,
    args: str | None = None,
) -> dict:
    """
    The Build read doors — the Mac names, the VM reads, only results cross.

    Plan: archive/plans/build_vertical_plan_2026-09-24.md section 6, ruling 11.
    The rules, the allowlist and the per-tool schemas are all in
    `core/build/doors.py`; this endpoint is the socket they sit behind.

        GET /monitor/tool?persona=mike&presence=log
            the presence check. A SOURCE ID, not arguments: the server runs the
            fixed, code-chosen call from manifest._SOURCES and returns
            {state, count, window} with NO CONTENT. The model names a source;
            code chooses the call.

        GET /monitor/tool?persona=mike&name=read_wisdom&args={"domains":["home"]}
            a research read. The name must be in the Librarian's read set minus
            the seven live feeds — no outbound tool sits behind a door — and the
            arguments are validated server-side against a per-tool schema with
            caps. Anything outside it is a 400 carrying the schema.

    Auth and reach are the monitor API's, not this endpoint's: `require_auth`
    gates every path outside the app shell, so a request with no bearer or a bad
    one never arrives here, and the route is Tailscale-only like every other
    /monitor route. Persona comes from the QUERY and from nowhere else — the
    call runs inside `persona_scope()` and no schema admits a `persona`
    argument, so a door bound to one persona cannot read another's data.

    `core.build.doors` is imported HERE rather than at module level on purpose.
    It asserts its own safety invariant at import and fails closed; at module
    level that would stop the server booting, and a wrong Build allowlist must
    take down the door, not the user's sessions.
    """
    from core.build import doors
    from core.persona import PersonaError, validate_persona_name

    if bool(presence) == bool(name):
        raise HTTPException(status_code=400, detail={
            "error": "supply exactly one of ?presence=<source_id> or ?name=<tool>",
            "reason": "mode",
        })

    if not persona:
        raise HTTPException(status_code=400, detail={
            "error": "persona is required — a door is bound to one persona",
            "reason": "no_persona",
        })
    try:
        persona_key = validate_persona_name(persona)
    except PersonaError as exc:
        raise HTTPException(status_code=400, detail={
            "error": str(exc), "reason": "bad_persona",
        })

    if presence:
        def _run() -> dict:
            return doors.presence(presence, persona_key)
    else:
        try:
            parsed = json.loads(args) if args else {}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail={
                "error": f"args is not valid JSON: {exc}", "reason": "bad_args",
            })
        if not isinstance(parsed, dict):
            raise HTTPException(status_code=400, detail={
                "error": "args must be a JSON object", "reason": "bad_args",
            })

        def _run() -> dict:
            return doors.research_read(name, parsed, persona_key)

    # Off the event loop: every handler behind a door does blocking file IO, and
    # search_memory loads an embedding model on first use.
    try:
        return await asyncio.to_thread(_run)
    except doors.DoorRefused as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail)


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
    # Accepted for the systemd unit's sake and otherwise ignored: since 2026-10-27 every
    # request's persona comes from its token (bound_persona), never from a server default.
    parser.add_argument("--persona", default=None,
                        help="Ignored — each request's persona comes from its sign-in.")
    args = parser.parse_args()

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
