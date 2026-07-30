# Client and App Audit — Cost Finding, Programme Parked
**Date:** 2026-07-30
**Type:** Investigation + planning. **No code changed.**

---

## What prompted this

Five reported symptoms across the Android app and web PWA:
1. Tailscale on the phone keeps falling silent, needs manual restart
2. App haphazard — populates history on first load after install, blank on fresh open; "failed to fetch" during transcription
3. Transcription slow
4. Web tool often doesn't load on the phone
5. Messages populate at the top rather than the bottom

Asked to review both clients for these *and* for deeper construction errors, then produce a plan.

---

## The finding that reframes everything: the server was off

Mid-investigation, `gcloud compute ssh` failed — **billing disabled, VM offline, last seen 1h ago.** The $30 budget cap had tripped again.

**This is arithmetic, not anomaly:**

| Component | ~Cost/month |
|---|---|
| e2-medium, 24/7, us-central1 | $24.50 |
| In-use external IPv4 | $2.90 |
| Persistent disk | $1.00 |
| **Infrastructure subtotal** | **~$29** |

**~95% of a $30 budget before a single AI token.** The cap was never protecting against runaway AI spend — it was tripping on the VM existing. It went twice in three days, each time disabling billing and taking the server down.

User raised the budget to $40 manually during the session. Billing relink + VM restore was handled in a **parallel chat**, not here.

**Consequence for the diagnosis:** "web app doesn't load", "failed to fetch", and much of "Tailscale falls silent" are all consistent with a dead server. Recorded as an explicit precondition in both `SESSION.md` and the parked plan: **re-test against a live server before building any fix.**

Could not produce a daily spend breakdown — no BigQuery billing export is configured, and Cloud Billing reports are console-only. Enabling that export is in the parked plan (it is **not retroactive**, so enabling early matters).

---

## Two symptoms were misdiagnosed

**"Messages stay at the top" is not an ordering bug.** DOM order is correct: `appendChild` only, no `prepend`/`insertBefore` anywhere in the file, and the server already reverses to oldest-first (`ORDER BY id DESC` then `reversed(rows)`). The symptom is pure CSS — `#conversation` (`static/index.html:30-37`) is `display:flex; flex-direction:column` with no bottom alignment, so content shorter than the viewport stacks from the top of a tall column. Fix is one line, but use `margin-top: auto` on an inner wrapper — **not** `justify-content: flex-end`, which clips overflowing content at the top and jumps scroll in Chromium.

**"Tailscale falling silent" is largely the client.** There is no `case 'ping'`, no `visibilitychange`, no `online`/`offline`/`pageshow` listener anywhere in `static/index.html`. The server sends `{"type":"ping"}` every 30s and the client's `switch` has no case for it and no `default` — the frame is silently dropped. Android freezes the WebView on background; the socket dies half-open; `readyState` stays `OPEN` so `sendViaWebSocket` sends into a void with no response timeout. **Restarting Tailscale forces a network-change event that finally kills the socket and triggers the 3s reconnect** — which is exactly why Tailscale looked guilty.

---

## Real defects found (documented, not fixed)

- **Blank screen on 2nd+ launch.** Auto-login (`index.html:911-914`) calls `enterApp` synchronously at script-parse time. `enterApp` (L343-353) hides the login screen **first**, then calls `requestMicPermission()`, `initPush()`, `connectWebSocket()` with no `try/catch`. `new WebSocket()` throws synchronously on a bad URL → `ws` stays `null`, `onclose` never fires, and **no reconnect path exists**. History arrives *only* via the WS `history` frame — there is no HTTP fallback — so no WS means a permanently blank screen with no error shown. There is no `ws.onerror`, no `window.onerror`, no `unhandledrejection` handler.
- **`/transcribe` and `/tts` block the event loop.** Both are `async def` but run `subprocess.run` and `_transcribe()` inline (`server.py:597-646`, `561-594`). While a transcription runs, the WS chunk-relay loop, the 30s heartbeat, `/active`, `/health` and `/monitor/stream` are all frozen. The correct `run_in_executor` pattern is already used at `server.py:252/311/425` — this is an inconsistency, not a design choice.
- **Whisper untuned and never warmed.** `base.en`, `compute_type="auto"` (→ float32 on CPU), `beam_size=5`, no `vad_filter`, `condition_on_previous_text` defaulting True. Lazily loaded and cached, but nothing warms it at startup — so the first `/transcribe` after every `systemctl restart` pays model construction *on the event loop*, and `deploy.sh` restarts on every deploy.
- **`deploy.sh`'s drain is decorative.** `/active` counts only `_active_streams`, incremented solely in `session_stream` — and `POST /session/stream` has **no client at all** (the client moved to WebSocket). So the drain always reads 0 and **every deploy kills in-flight WebSocket exchanges.**
- **No auth anywhere.** `allow_origins=["*"]`; `server.py:671-672` says outright "No auth: access is gated by the Tailscale VPN." `/monitor/file` and `/monitor/history` read arbitrary paths under `data/` (and `/monitor/history` lacks even the weak `..` check `/monitor/file` has). **Tailscale is the entire security model** — which is what makes the Cloudflare Tunnel a much bigger job than the roadmap implies.
- **`shownIds` eviction cliff.** `renderHistory` L567 clears *after* adding the ids it just rendered, unlike the hardened L590. When an in-flight own exchange id is evicted, `done` takes the wrong branch → `ownBubble` never nulled → mic stuck on "Thinking…" forever; and `chunk` routes to `foreignBubbles.get()` → undefined → **response text silently dropped.**
- **Catch-up wipes the conversation.** Server answers a `catchup` with `type:"history"`, and the client routes all `history` frames through `renderHistory`, which starts `conversation.innerHTML = ...` — so a reconnect renders full history then replaces it with just the delta.
- **No offline shell.** `static/sw.js` has **no `fetch` handler** and caches nothing; `/` is served `Cache-Control: no-store`, which forbids caching outright. No `manifest.json`. The SW is registered only inside the notification path, so devices that declined notifications run different code.
- **Android:** `POST_NOTIFICATIONS` missing from the manifest with `targetSdk 36` (OS-blocks notifications on 13+), and the Push API doesn't exist in an Android WebView at all, so push is simply off in the app. `capacitor.plugins.json` is `[]`.
- Tailscale certs are 90-day with **no renewal automation** (no crontab, no timer) — another latent "went silent" mode.

---

## Outcome

The full five-phase programme (server unblocking → client resilience → auth → Cloudflare Tunnel → PWA shell) was **approved and archived, not executed**: [archive/plans/client_auth_tunnel_programme_2026-07-30.md](../plans/client_auth_tunnel_programme_2026-07-30.md).

User's reasoning, which was right: if the symptoms were largely "the server was off," building a five-phase programme on that diagnosis is premature. Restore, use it, see what survives.

**Explicit gate recorded in the plan header and `SESSION.md`:** do not start Phase 1 until the system has been used against a live server and the list of surviving symptoms exists.

### Decisions taken during planning
- Cloudflare Tunnel **and** auth in the same pass when it happens — a tunnel without auth would put the conversation corpus on the open internet.
- Whisper: int8 + `beam_size=1` + VAD + warm-load, **and benchmark `distil-small.en`** against `base.en` on real clips (real audio already exists in `data/audio/` with transcript sidecars).
- App keeps its bundled `index.html`; **exactly one APK rebuild**, at the Phase 4 cutover. Phase 2 therefore gets validated in desktop Chrome against the live server, with the phone as final verification rather than the dev loop.

### Domain question — recommended against `apexgmat.com`
User has that domain on Cloudflare already. Advised a **separate personal domain** (~$10/yr) instead, for four reasons: one Cloudflare account means a shared blast radius between a business site and a host holding journals/clinical flags/finances; `metatron.apexgmat.com` would be published permanently to public Certificate Transparency logs, associating a personal endpoint with a business entity; domain-wide cookies on `.apexgmat.com` reach every subdomain; and later Cloudflare Access would couple personal-data access to business SSO. Not blocking — nothing before Phase 4 depends on it.

### Cost levers recorded (not applied)
- **Gate check-ins on user activity** — largest lever. The pathological case *is* the current state: ~12 full multi-specialist pipelines/day while the app was broken, i.e. the VM talking to itself.
- Stop the VM overnight via a GCE instance schedule (~$8–9/mo, native feature, no code).
- `companion_checkin` 90 → 180 min.
- Hold off on a 1-year CUD until Whisper sizing is settled.
- Make uncached Vertex the deliberate default; check `usageMetadata.cachedContentTokenCount` first, since implicit caching may already be discounting for free.

---

## Housekeeping
Left `CLAUDE.md` and `scripts/metatron-resume.sh` uncommitted — they were being edited by the parallel chat handling service restoration. Commit `cf59318` contains only `SESSION.md` and the archived plan.

## Prediction for the re-test (for calibration)
CSS symptom persists (unrelated to connectivity). Backgrounding symptom persists (no `visibilitychange` handling exists). "Doesn't load" / "failed to fetch" should largely disappear.
