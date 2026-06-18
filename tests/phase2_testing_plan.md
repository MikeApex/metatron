# Phase 2 Testing Plan — Voice Pipeline + Phone

*Intent-driven. Tests whether the phase achieved its purpose, not just whether the code runs.*

---

## Phase Intent

Bring the phone online as a full interaction surface. A user should be able to conduct a complete check-in by voice from their phone with acceptable latency — the tool is no longer laptop-only.

---

## Prerequisites Check

| Prerequisite | Check |
|---|---|
| Orchestrator working (Phase 0) | Returns a response |
| TLS certificate in `certs/` | At least one `.crt`/`.key` or `.pem`/`-key.pem` pair exists |
| Tailscale running | `tailscale status` shows connected |
| Phone on same Tailscale network | Ping the Tailscale hostname from phone browser |
| Whisper model downloaded | `core/voice_pipeline.py` WHISPER_MODEL_SIZE matches a downloaded model |

---

## Intent Checks

### 1. Full voice round-trip on phone
- From the phone browser, speak a message
- **Pass:** Speech is transcribed, Orchestrator responds, response is spoken aloud — end-to-end latency under 10 seconds
- **Fail:** Any leg (STT, API call, TTS) fails or latency exceeds 10 seconds

### 2. HTTPS enforced — mic access works
- Open the PWA on phone over Tailscale
- **Pass:** Browser requests microphone permission; mic works after granting
- **Fail:** Browser blocks mic due to non-HTTPS context

### 3. Provider switching works from phone
- Switch provider via the UI dropdown; send a message
- **Pass:** Response comes from the selected provider (verify via response style or logs)
- **Fail:** Provider selection has no effect; requests always route to default

### 4. Phone is not just a mirror of laptop
- Send a message from phone while laptop browser is closed
- **Pass:** Session works independently; no laptop dependency
- **Fail:** Phone requires laptop browser to be open or warm

---

## Known Gaps (from Phase audit)

- **PWA locked to a single agent.** The `/session` endpoint accepts an `agent` field, and the PWA sends it — but the UI only offers agents that were known at Phase 2 build time. Agents added in Phase 3+ (Diarist, Pattern Miner) require either a UI update or sub-agent dispatch to be reachable from the phone. This is a structural gap: the phone has been architecturally stranded from Phase 3 agents.
- **No `persona` field in PWA requests.** The server accepts `persona` but the PWA does not send it. Testing always uses real user context unless the server is restarted with a `--persona` default.

---

## Sign-off

Phase 2 is complete when a full voice check-in runs end-to-end on the phone over Tailscale with latency under 10 seconds.
