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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.orchestrator import run_session

app = FastAPI(title="Life Manager")

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
    agent: str = "time_director"
    persona: str | None = None
    provider: str = "anthropic"


class SessionResponse(BaseModel):
    response: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post("/session", response_model=SessionResponse)
async def session(req: SessionRequest) -> SessionResponse:
    """Run a single orchestrator turn and return the text response."""
    if not req.input.strip():
        raise HTTPException(status_code=400, detail="Input is empty.")
    try:
        response = run_session(
            req.agent,
            req.input,
            persona=req.persona,
            provider=req.provider,
        )
        return SessionResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


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
    parser.add_argument("--provider", default="anthropic", choices=["anthropic", "openai"],
                        help="Default provider (can be overridden per request)")
    args = parser.parse_args()

    print(f"\nLife Manager server starting on http://0.0.0.0:{args.port}")
    print("Find your local IP: run `ipconfig getifaddr en0` in a new terminal")
    print("Then open http://<your-ip>:{args.port} on your phone (same WiFi)\n")

    uvicorn.run("core.server:app", host=args.host, port=args.port, reload=False)
