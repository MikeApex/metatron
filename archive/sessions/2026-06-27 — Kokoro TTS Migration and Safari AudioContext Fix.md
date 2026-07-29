# 2026-06-27 — Kokoro TTS Migration and Safari AudioContext Fix

## What was built / changed

### Safari PWA voice playing generic macOS TTS instead of Kokoro

**Root cause investigation:**
- User noticed voice differed between Android app and Safari MacBook PWA
- Android app was playing Kokoro `af_heart` (server audio); Safari was playing macOS built-in TTS
- Safari blocks `new Audio().play()` autoplay even after user gesture; the `.catch()` fallback fired and handed off to `window.speechSynthesis`
- Separately confirmed: Kokoro venv was missing on VM entirely — server was falling back to edge-tts `en-US-JennyNeural` even for Android

**Fix 1 — AudioContext playback in `static/index.html`:**
- Replaced `new Audio(url).play()` path with `AudioContext.decodeAudioData()` + `BufferSourceNode` — this path respects the `resume()` call made by `unlockAudio()` and is not blocked by Safari
- Shared `AudioContext` (`audioCtxShared`) created on first gesture and reused
- `currentSource` (BufferSourceNode) replaces `currentAudio` (Audio element) for interrupt-on-new-response
- `res.arrayBuffer()` instead of `res.blob()` — AudioContext needs raw bytes

**Fix 2 — Kokoro installed on VM:**
- Kokoro venv was Mac-only (`/opt/homebrew/bin/python3.12` path) — never migrated to VM
- Python 3.12 not available in Debian 12 apt; torch already in main `.venv` for faster-whisper
- Solution: installed `espeak-ng` via apt, then `kokoro soundfile` into main `.venv` (reusing existing torch — saves ~2 GB)
- Pip cache (5.6 GB) cleared to make room before install
- `KOKORO_PYTHON` path updated in `core/server.py` and `core/voice_pipeline.py` from `tools/kokoro/venv/bin/python` → `.venv/bin/python`
- Kokoro subprocess timeout raised from 30s → 120s (model downloads on first cold-start run)

**Other issues discovered and fixed during deploy:**
- `aiosqlite` missing from `requirements.txt` — server crashed on startup after deploy (ModuleNotFoundError). Added and committed.
- Login form Enter key missing — `#login-password` had no `keydown` handler; pressing Enter on the password field did nothing. Added handler mirroring the Enter button click.
- Multiple deploys showed "Everything up-to-date" because edits weren't committed before running `./deploy.sh` — reminder: always commit first.

### VM migration gap audit

Spawned a subagent to scan phase 1–5 session archives for features built on Mac that might not have migrated to VM. Results:

| Item | Status |
|---|---|
| Kokoro TTS venv | **Was missing — fixed this session** |
| faster-whisper | ✓ installed |
| python-multipart | ✓ installed |
| edge-tts | ✓ installed |
| faiss-cpu + sentence-transformers | ✓ installed |
| Whisper model weights (base.en) | ✓ cached |
| all-MiniLM-L6-v2 weights | ✓ cached |
| ffmpeg | ✓ installed |
| VAPID keys | ✓ in .env |
| data/ directories | ✓ exist |
| Ollama + qwen3:14b | intentionally absent (VM uses cloud routing) |
| FAISS user data index | empty by design |

### Disk / infrastructure note
- VM disk: 20 GB total, 13 GB used, 6.2 GB free (67% full) after cleanup
- Main `.venv` is 6.1 GB (ML dependencies dominate)
- Pip cache cleared (was 5.6 GB) — safe to clear anytime, auto-rebuilds
- If disk fills: GCP Console → disk → Edit → resize (no downtime); then `sudo resize2fs /dev/sda1` on VM. Next tier ~50 GB (about $2/month extra on pd-standard)

## Commits this session

- `4302ef8` — TTS: install Kokoro in main venv; fix AudioContext playback in Safari
- `e2566c8` — Add aiosqlite to requirements.txt
- `d74c9ce` — Login: add Enter key handler on password field
- `87cffc8` — TTS: increase Kokoro subprocess timeout to 120s for cold start

## Outcome

Kokoro `af_heart` voice confirmed working in Safari PWA after final deploy.

## Deferred / open

- `tools/kokoro/setup.sh` still references `/opt/homebrew/bin/python3.12` — Mac-only script, not needed on VM, but could be updated to document the Linux install path for future reference
- First Kokoro call after server restart still takes a few extra seconds while Torch loads model weights into memory — could pre-warm at server startup if latency becomes noticeable
