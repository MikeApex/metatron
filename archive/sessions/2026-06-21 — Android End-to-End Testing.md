# 2026-06-21 — Android End-to-End Testing

## What happened

Ran the 10-test Android end-to-end test plan (`archive/plans/android_test_prompt_2026-06-20.md`) against the VM-hosted Metatron server. All 10 tests passed after a series of fixes.

---

## Fixes applied

| # | Problem | Fix |
|---|---|---|
| 1 | Mike persona missing from VM | `gcloud compute scp` of `config/personas/mike/` and `mike.md` |
| 2 | Vertex key (`vertex-key.json`) missing from VM | Deployed from `~/Downloads/metatron-ai-499810-a8c2e32e3612.json` |
| 3 | `/transcribe` crashing: `PortAudio library not found` | `sounddevice` import made lazy — moved inside the local-recording function in `core/voice_pipeline.py` |
| 4 | Server running HTTP — mic blocked on Android Chrome | Provisioned Tailscale TLS cert: `tailscale cert metatron-vm.tail0acc5d.ts.net` → `certs/server.crt` + `certs/server.key`; server now runs HTTPS |
| 5 | Whisper not installed on VM | `pip install openai-whisper` in venv |
| 6 | Provider dropdown defaulted to `ollama` → errno 111 | Changed default option to `value=""` (auto-route via server's `DEPLOYMENT_MODE`) |
| 7 | Send button off to the right | `#text-input` changed to `flex-direction: column`; `#send-btn` set to `width: 100%` |
| 8 | Mic permission not auto-prompting | `MainActivity.java` fixed: moved `WebChromeClient` to `onCreate()`, added `ActivityCompat.requestPermissions()` for `RECORD_AUDIO` on first launch |
| 9 | Audio not playing after response | Added `AudioContext` unlock on first user tap; `play()` rejection now caught with fallback to `SpeechSynthesisUtterance` |
| 10 | `SERVER` URL hardcoded to `http://100.64.226.49:8001` | Updated to `https://metatron-vm.tail0acc5d.ts.net:8001` |

---

## Test results

All 10 tests from the test plan: **PASS**

1. Server health — PASS
2. App icon — PASS
3. Login screen (first launch) — PASS
4. Persona selection — PASS
5. Auto-login on return — PASS
6. Persona switch — PASS
7. Text input → response — PASS
8. Voice → transcription → response — PASS
9. TTS playback — PASS
10. Pipeline latency (~20s simple, ~70s complex) — PASS

---

## Decisions / notes

- **Cloudflare Tunnel added to roadmap as pre-alpha requirement** — current setup requires Tailscale on the user's phone; Cloudflare Tunnel removes that dependency for other users. Added to `archive/plans/phase5_to_future_roadmap_2026-06-10.md` under "Pre-Alpha".
- **Goals Interview not yet run on VM** — `BASELINE_INCOMPLETE` flag appears in every session. D1 item: run `python core/orchestrator.py --agent goals_interviewer --provider gemini` on the VM before next real-use session.
- **Provider routing** — client-supplied `provider` field overrides server's `DEPLOYMENT_MODE`. Fixed by defaulting to empty string. Switching back to Ollama: set `DEPLOYMENT_MODE` in VM `.env` (no APK rebuild needed).
- **Tailscale cert renewal** — Tailscale certs are valid 90 days, auto-renewable via `tailscale cert`.

## Next

- Run Goals Interview on VM (CLI, not app — agent selector is hidden)
- Token trimming to reduce latency
- A7 Phase 5 sign-off (after B1/Check10/Check12 resume)
