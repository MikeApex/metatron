# Metatron Android App — End-to-End Test Session
*Use this prompt to open a fresh chat for post-build testing.*

---

## Context

The Metatron Android app was rebuilt today (2026-06-20). Read SESSION.md before doing anything. Key changes in this build:

- **Server moved to GCP VM** — Tailscale IP `100.64.226.49`, port 8001. Mac is no longer the server host.
- **Login/persona screen** — appears on first launch; auto-logins on return via localStorage. Persona chip in header to switch.
- **New mem icon** — parchment/brushwork Phoenician mem glyph. Adaptive icon XMLs removed; Android uses PNG directly.
- **All agents on Vertex AI** via Vertex OpenAI-compat endpoint (`DEPLOYMENT_MODE=cloud`).

The app is sideloaded on the phone. The VM server is running as a systemd service and should be up.

---

## Your job in this session

Walk the user through each test below in order. For each one: tell them what to do, what a pass looks like, and help diagnose if something fails. Monitor server logs on the VM when needed (see commands below).

---

## Test checklist

### 1. Server health
**Mac tab:**
```bash
curl http://100.64.226.49:8001/health
```
**Pass:** `{"status":"ok"}`
**Fail:** connection refused → check `sudo systemctl status metatron-server` on VM

### 2. App icon
- Look at the Metatron icon on the Android home screen
- **Pass:** parchment-colored brushwork mem glyph on dark background
- **Fail:** old icon still showing → uninstall, reinstall APK

### 3. Login screen (first launch)
- Uninstall and reinstall the app to clear localStorage, OR clear app storage in Android Settings
- Open the app
- **Pass:** login screen appears with persona dropdown and password field
- **Fail:** goes straight to chat → localStorage not cleared

### 4. Persona selection
- Select `mike` from the dropdown, tap Enter
- **Pass:** login screen dismisses, chat UI appears, `mike` chip visible in header top-right
- **Fail:** nothing happens → check browser console via `chrome://inspect`

### 5. Auto-login on return
- Close and reopen the app
- **Pass:** goes straight to chat (no login screen)
- **Fail:** login screen shows again → localStorage not persisting

### 6. Persona switch
- Tap the `mike` chip in the header
- **Pass:** login screen reappears, can select a different persona
- **Fail:** nothing happens

### 7. Text input → response
- Type a simple message: "Hello, what's today's date?"
- Tap Send
- **Pass:** user message appears, "Thinking..." shows, response appears within 30s
- **Fail:** error message → check server logs

### 8. Voice input → transcription → response
- Tap the mic button, speak clearly: "What are my goals for today?"
- Wait for silence detection to stop recording
- **Pass:** transcript appears briefly, then response appears
- **Fail at transcription:** "Transcription failed" → check `/transcribe` endpoint
- **Fail at response:** error → check `/session` endpoint

### 9. TTS playback
- After a response appears, audio should play automatically
- **Pass:** voice speaks the response
- **Fail:** silent → check `/tts` endpoint; Kokoro may not be installed on VM (edge-tts fallback should kick in)

### 10. Full pipeline latency
- Note the time from Send/mic-stop to response appearing
- **Expected:** 16–20s for a simple message, up to 75s for a complex multi-specialist query
- Flag if consistently >90s

---

## VM monitoring commands

**SSH to VM:**
```bash
gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810
```

**Watch live server logs:**
```bash
sudo journalctl -u metatron-server -f
```

**Check service status:**
```bash
sudo systemctl status metatron-server metatron-scheduler --no-pager
```

**Restart server if needed:**
```bash
sudo systemctl restart metatron-server
```

---

## Known gaps / expected issues

- **Kokoro TTS not installed on VM** — edge-tts fallback will be used. Voice quality will differ from Mac. This is expected.
- **Whisper model cold-start** — first transcription may take 10–15s while the model loads into memory. Subsequent ones are fast.
- **60–75s latency on complex queries** — normal for multi-specialist Gemini 3.1 Pro pipeline.
- **Persona data** — `mike` persona data lives on the Mac, not the VM. Responses may be generic until Goals Interview is run on the VM (D1 item).
