"""
core/server.py — FastAPI server for the phone PWA.

Exposes the orchestrator over HTTP on the local network.
The PWA (static/index.html) uses Web Speech API for STT/TTS on the phone
and calls this server for the actual model inference.

Run:
    python core/server.py
    python core/server.py --provider openai --port 8000

Then open http://<your-laptop-ip>:8000 on your phone (same WiFi network).
Find your IP: System Settings → Wi-Fi → Details, or run `ipconfig getifaddr en0`.
"""

import argparse
import asyncio
import os
import sys
import tempfile
import threading
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import aiosqlite
import edge_tts
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.orchestrator import run_pipeline_session_stream, run_session

KOKORO_VOICE = "af_heart"
KOKORO_SPEAK = Path(__file__).parent.parent / "tools" / "kokoro" / "speak.py"
KOKORO_PYTHON = Path(__file__).parent.parent / ".venv" / "bin" / "python"
EDGE_VOICE = "en-US-JennyNeural"

app = FastAPI(title="Life Manager")

# Read at module import time from env var set before uvicorn.run()
DEFAULT_PERSONA: str | None = os.environ.get("SERVER_PERSONA") or None

DB_PATH = Path(__file__).parent.parent / "data" / "conversations" / "metatron.db"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # local network only — no auth needed at this stage
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent.parent / "static"


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


class ConnectionManager:
    def __init__(self) -> None:
        self.active: dict[str, set[WebSocket]] = {}

    async def connect(self, ws: WebSocket, persona: str) -> None:
        await ws.accept()
        self.active.setdefault(persona, set()).add(ws)

    def disconnect(self, ws: WebSocket, persona: str) -> None:
        self.active.get(persona, set()).discard(ws)

    async def broadcast(self, persona: str, payload: dict, exclude: WebSocket | None = None) -> None:
        for ws in list(self.active.get(persona, set())):
            if ws is exclude:
                continue
            try:
                await ws.send_json(payload)
            except Exception:
                self.active.get(persona, set()).discard(ws)


manager = ConnectionManager()


def _log_conversation(user_input: str, response: str, agent: str, persona: str | None) -> None:
    """Append a verbatim exchange to the daily conversation log."""
    import json as _json
    from datetime import datetime
    log_dir = Path(__file__).parent.parent / "data" / "conversations"
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


async def _get_recent_exchanges(persona: str, limit: int = 20) -> list[dict]:
    """Return last `limit` exchanges as dicts for WS history message."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, exchange_id, user, assistant, ts FROM exchanges "
            "WHERE persona=? ORDER BY id DESC LIMIT ?",
            (persona, limit),
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(r) for r in reversed(rows)]


async def _catchup_since(persona: str, since_id: int) -> list[dict]:
    """Return exchanges with id > since_id, oldest first."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, exchange_id, user, assistant, ts FROM exchanges "
            "WHERE persona=? AND id > ? ORDER BY id ASC",
            (persona, since_id),
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def _save_exchange(persona: str, exchange_id: str, user: str, assistant: str) -> int:
    """Persist a completed exchange. Returns the new row id."""
    ts = datetime.utcnow().isoformat() + "Z"
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT OR IGNORE INTO exchanges (exchange_id, persona, user, assistant, ts) "
            "VALUES (?,?,?,?,?)",
            (exchange_id, persona, user, assistant, ts),
        )
        await db.commit()
        return cursor.lastrowid or 0


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
      data: [ERROR] ...\\n\\n     — server exception

    NOTE: The sync generator runs inline in this async handler — acceptable for
    single-user local deployment. For multi-user, wrap with run_in_executor().
    """
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
                    req.input, persona=persona, provider=req.provider, history=history
                ):
                    asyncio.run_coroutine_threadsafe(queue.put(chunk), loop).result()
            except NotImplementedError:
                # Provider has no streaming variant — fall back to single blocking call
                response = run_session(req.agent, req.input, persona=persona, provider=req.provider)
                asyncio.run_coroutine_threadsafe(queue.put(response), loop).result()
                asyncio.run_coroutine_threadsafe(queue.put("[DONE]"), loop).result()
            except Exception as e:
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
      {type: "send", exchange_id, input, provider}  — submit a prompt
      {type: "catchup", since_id}                   — fetch missed exchanges on reconnect

    Server → client message types:
      {type: "history", messages, last_id}           — initial history / catch-up response
      {type: "stream_start", exchange_id, user}      — foreign exchange starting (not this device)
      {type: "chunk", exchange_id, text}             — token from the LLM (own or foreign)
      {type: "done", exchange_id}                    — exchange complete; commit text
      {type: "retract", exchange_id}                 — output filtered; discard buffered text
      {type: "message", id, exchange_id, user, assistant, ts}  — completed record for catch-up
      {type: "error", exchange_id, text?}            — error (text only on sender)
      {type: "ping"}                                 — 30-second heartbeat
    """
    persona_orch = persona or DEFAULT_PERSONA
    persona_key = persona_orch or "__default__"
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
            msg_type = data.get("type")

            if msg_type == "send":
                exchange_id = data.get("exchange_id") or str(uuid.uuid4())
                user_input = data.get("input", "").strip()
                if not user_input:
                    continue
                provider = data.get("provider") or None
                history = _session_history.setdefault(persona_key, [])

                # Notify other devices that a new exchange is starting
                await manager.broadcast(persona_key, {
                    "type": "stream_start",
                    "exchange_id": exchange_id,
                    "user": user_input,
                }, exclude=websocket)

                loop = asyncio.get_running_loop()
                queue: asyncio.Queue = asyncio.Queue()
                accumulated: list[str] = []
                retracted = False
                errored = False

                def _produce() -> None:
                    try:
                        for chunk in run_pipeline_session_stream(
                            user_input, persona=persona_orch, provider=provider, history=history
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

                while True:
                    item = await queue.get()
                    if item is None:
                        break
                    if item == "[DONE]":
                        break
                    elif item == "[RETRACT]":
                        retracted = True
                        break
                    elif item.startswith("[ERROR] "):
                        errored = True
                        await websocket.send_json({
                            "type": "error", "exchange_id": exchange_id, "text": item[8:],
                        })
                        await manager.broadcast(persona_key, {
                            "type": "error", "exchange_id": exchange_id,
                        }, exclude=websocket)
                        break
                    else:
                        accumulated.append(item)
                        chunk_payload = {"type": "chunk", "exchange_id": exchange_id, "text": item}
                        await websocket.send_json(chunk_payload)
                        await manager.broadcast(persona_key, chunk_payload, exclude=websocket)

                await asyncio.wrap_future(producer)

                if retracted:
                    retract_payload = {"type": "retract", "exchange_id": exchange_id}
                    await websocket.send_json(retract_payload)
                    await manager.broadcast(persona_key, retract_payload, exclude=websocket)
                elif not errored:
                    full_response = "".join(accumulated)
                    done_payload = {"type": "done", "exchange_id": exchange_id}
                    await websocket.send_json(done_payload)
                    await manager.broadcast(persona_key, done_payload, exclude=websocket)
                    new_id = await _save_exchange(persona_key, exchange_id, user_input, full_response)
                    _log_conversation(user_input, full_response, "coordinator", persona_orch)
                    await manager.broadcast(persona_key, {
                        "type": "message",
                        "id": new_id,
                        "exchange_id": exchange_id,
                        "user": user_input,
                        "assistant": full_response,
                        "ts": datetime.utcnow().isoformat() + "Z",
                    }, exclude=websocket)

            elif msg_type == "catchup":
                since_id = int(data.get("since_id", 0))
                rows = await _catchup_since(persona_key, since_id)
                if rows:
                    await websocket.send_json({
                        "type": "history",
                        "messages": rows,
                        "last_id": rows[-1]["id"],
                    })

    except WebSocketDisconnect:
        pass
    finally:
        hb_task.cancel()
        manager.disconnect(websocket, persona_key)


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

@app.post("/tts")
async def tts(req: TTSRequest):
    """Generate speech audio — Kokoro af_heart primary, edge-tts fallback."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text is empty.")
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp.close()
    try:
        if KOKORO_PYTHON.exists():
            import subprocess
            wav_tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            wav_tmp.close()
            result = subprocess.run(
                [str(KOKORO_PYTHON), str(KOKORO_SPEAK), "--voice", KOKORO_VOICE, "--output", wav_tmp.name],
                input=req.text, capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr)
            media_type = "audio/wav"
            audio_path = wav_tmp.name
        else:
            communicate = edge_tts.Communicate(req.text, EDGE_VOICE)
            await communicate.save(tmp.name)
            media_type = "audio/mpeg"
            audio_path = tmp.name

        def iterfile():
            with open(audio_path, "rb") as f:
                yield from f
            Path(audio_path).unlink(missing_ok=True)
        return StreamingResponse(iterfile(), media_type=media_type)
    except Exception as e:
        Path(tmp.name).unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)) -> dict:
    """
    Receive a raw audio blob from the PWA, transcribe with Whisper (local),
    and archive both the audio file and its transcript to data/audio/.

    Returns {"transcript": "..."} — the text is then sent to /session by the client.
    Audio never leaves this machine; Web Speech API (Google) is not used.
    """
    import json as _json
    import subprocess as _subprocess
    import numpy as _np

    ts = datetime.now().strftime("%H-%M-%S")
    date_dir = Path(__file__).parent.parent / "data" / "audio" / datetime.now().strftime("%Y-%m-%d")
    date_dir.mkdir(parents=True, exist_ok=True)

    # Save raw audio (WebM/Opus from MediaRecorder)
    audio_path = date_dir / f"{ts}.webm"
    audio_bytes = await audio.read()
    with open(audio_path, "wb") as f:
        f.write(audio_bytes)

    # Decode to float32 PCM at 16kHz via ffmpeg (Whisper expects this format)
    try:
        result = _subprocess.run(
            ["ffmpeg", "-i", str(audio_path), "-ar", "16000", "-ac", "1",
             "-f", "f32le", "-"],
            capture_output=True, timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg: {result.stderr.decode()[:200]}")
        audio_array = _np.frombuffer(result.stdout, dtype=_np.float32)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="ffmpeg not found — install with: brew install ffmpeg")

    # Transcribe locally with faster-whisper
    from core.voice_pipeline import transcribe as _transcribe
    transcript = _transcribe(audio_array)

    # Archive transcript alongside audio
    meta_path = date_dir / f"{ts}.json"
    with open(meta_path, "w") as f:
        _json.dump({
            "ts": datetime.now().isoformat(),
            "audio_file": str(audio_path),
            "transcript": transcript,
        }, f, ensure_ascii=False, indent=2)

    return {"transcript": transcript}


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
