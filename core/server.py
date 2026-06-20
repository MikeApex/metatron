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
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import edge_tts
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.orchestrator import run_pipeline_session_stream, run_session

KOKORO_VOICE = "af_heart"
KOKORO_SPEAK = Path(__file__).parent.parent / "tools" / "kokoro" / "speak.py"
KOKORO_PYTHON = Path(__file__).parent.parent / "tools" / "kokoro" / "venv" / "bin" / "python"
EDGE_VOICE = "en-US-JennyNeural"

app = FastAPI(title="Life Manager")

# Read at module import time from env var set before uvicorn.run()
DEFAULT_PERSONA: str | None = os.environ.get("SERVER_PERSONA") or None

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

def _log_conversation(user_input: str, response: str, agent: str, persona: str | None) -> None:
    """Append a verbatim exchange to the daily conversation log."""
    import json as _json
    from datetime import datetime
    log_dir = Path(__file__).parent.parent / "data" / "conversations"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"
    entry = {
        "ts": datetime.now().isoformat(),
        "agent": agent,
        "persona": persona,
        "user": user_input,
        "response": response,
    }
    with open(log_file, "a") as f:
        f.write(_json.dumps(entry, ensure_ascii=False) + "\n")


@app.post("/session", response_model=SessionResponse)
async def session(req: SessionRequest) -> SessionResponse:
    """Run a single orchestrator turn and return the text response."""
    if not req.input.strip():
        raise HTTPException(status_code=400, detail="Input is empty.")
    try:
        agent = req.agent
        persona = req.persona or DEFAULT_PERSONA
        response = run_session(agent, req.input, persona=persona, provider=req.provider)
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

    async def sse_generator():
        accumulated: list[str] = []
        try:
            for chunk in run_pipeline_session_stream(
                req.input, persona=persona, provider=req.provider
            ):
                if chunk in ("[DONE]", "[RETRACT]"):
                    yield f"data: {chunk}\n\n"
                else:
                    accumulated.append(chunk)
                    yield f"data: {chunk}\n\n"
        except NotImplementedError:
            # Provider has no streaming variant — fall back to single blocking chunk
            response = run_session(req.agent, req.input, persona=persona, provider=req.provider)
            accumulated = [response]
            yield f"data: {response}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: [ERROR] {e}\n\n"
            return

        _log_conversation(req.input, "".join(accumulated), req.agent, persona)

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


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
    parser.add_argument("--provider", default="anthropic", choices=["anthropic", "openai", "ollama", "gemini"],
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

    uvicorn.run("core.server:app", host=args.host, port=args.port, reload=False, **ssl_kwargs)
