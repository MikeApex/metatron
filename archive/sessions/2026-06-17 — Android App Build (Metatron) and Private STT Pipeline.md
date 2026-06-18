# Session: Android App Build (Metatron) and Private STT Pipeline
*2026-06-17*

## What was built

### 1. Private STT pipeline (server-side Whisper)
- **Problem:** Web Speech API (used by old PWA) sends audio to Google's cloud before the text reaches the Mac — a privacy gap.
- **Fix:** Added `/transcribe` endpoint to `core/server.py`. Receives raw WebM audio from the phone, decodes with ffmpeg, transcribes locally with `faster-whisper`, archives both audio (`.webm`) and transcript (`.json`) to `data/audio/YYYY-MM-DD/`.
- **Old `/upload-audio` endpoint replaced** — it archived audio but never transcribed.
- **`static/index.html` updated:** Web Speech API removed entirely. New flow: MediaRecorder captures audio → POST blob to `/transcribe` → text returned → sent to `/session`. Silence detection via Web Audio API AnalyserNode (auto-stops after 2.5s of quiet post-speech).
- **ffmpeg installed** via Homebrew — required to decode WebM/Opus to float32 PCM for Whisper.
- **`python-multipart` installed** in venv — required by FastAPI for file upload handling.

### 2. Metatron Android app (Capacitor)
- `npm init` + `@capacitor/core`, `@capacitor/cli`, `@capacitor/android` installed.
- `npx cap init "Metatron" "com.mike.metatron" --web-dir static`
- `npx cap add android`
- Android Studio Quail 1 installed (free).
- APK built and sideloaded via local HTTP file server (`python3 -m http.server 9999`). No Play Store needed for personal use.

### 3. Networking — Tailscale
- Tailscale not installed on Mac at start of session — installed during session.
- Two stale Tailscale Mac entries existed (`mikes-macbook-air` offline + `mikes-macbook-air-1` active). Cleaned up via admin.tailscale.com: removed old entry, renamed current to `mikes-macbook-air`.
- Fresh Tailscale cert obtained for renamed host, placed in `certs/`.
- **Resolution:** Tailscale DNS wasn't resolving the hostname on the phone (MagicDNS issue). Workaround: switched to direct Tailscale IP (`100.70.67.45`) in capacitor.config.json.
- Server running HTTP on port 8001 (no TLS) — Tailscale provides WireGuard encryption at VPN layer, so HTTP inside tunnel is acceptable for privacy.

### 4. Capacitor configuration decisions
- `server.url` removed — app loads from bundled assets (`https://localhost`) so `getUserMedia()` works as a secure context.
- All fetch calls prefixed with `SERVER` constant: `window.location.hostname === 'localhost' ? 'http://100.70.67.45:8001' : ''`.
- `allowMixedContent: true` — needed for HTTPS-origin (`https://localhost`) calling HTTP backend.
- Network security config added (`res/xml/network_security_config.xml`) — cleartext permitted.
- `RECORD_AUDIO` + `MODIFY_AUDIO_SETTINGS` permissions added to `AndroidManifest.xml`.
- `MainActivity.java` extended to grant WebView mic permission via `onPermissionRequest`.
- Provider/agent dropdowns hidden — hardcoded to ollama/coordinator.
- Fetch timeout set to 10 minutes (`AbortSignal.timeout(600000)`) — qwen3:14b on CPU takes several minutes for first turn with full context (11k+ tokens).

### 5. Server startup
- Certs backed up to `certs_backup/` — server runs HTTP on port 8001.
- Server started with `--persona mike --port 8001`.
- Mike persona file already existed at `config/personas/mike.md`.

### 6. App icon
- Phoenician/early Hebrew letter mem: three upward peaks (W shape) with descending tail (y stem).
- Colors: buff/parchment background (`#d2be9b`), dark burnt-umber ink (`#5a3214`).
- Generator script: `tools/gen_icon.py` — renders at 512px, scales to all Android mipmap sizes (48/72/96/144/192px).
- Writes `ic_launcher.png`, `ic_launcher_round.png`, `ic_launcher_foreground.png` at each density.

## Key decisions
- HTTP over Tailscale (not HTTPS) for the Capacitor app — VPN provides transport encryption; avoids cert trust issues in Android WebView.
- Bundled assets (not `server.url`) so microphone is in a secure context.
- Direct Tailscale IP as workaround for MagicDNS not resolving hostname in WebView.
- 10-minute fetch timeout to handle slow local LLM inference.

## Deferred / next session
1. **Tailscale on same network vs. remote** — does direct WiFi IP work faster? What happens when off-network?
2. **Mac "always on"** — prevent sleep, keep Ollama warm (keep-alive ping or launchd daemon).
3. **Login feature** — phone app lets user select their profile before connecting (multi-user support).

## Files changed this session
- `core/server.py` — `/transcribe` endpoint, tailscale hostname updated
- `static/index.html` — STT pipeline, SERVER constant, fetch timeout, dropdowns hidden
- `capacitor.config.json` — server IP, cleartext, allowMixedContent
- `android/app/src/main/AndroidManifest.xml` — permissions, network security config
- `android/app/src/main/res/xml/network_security_config.xml` — new
- `android/app/src/main/java/com/mike/metatron/MainActivity.java` — mic permission grant
- `tools/gen_icon.py` — new icon generator
- `package.json` — new (npm init)
- All Android mipmap icon files regenerated
