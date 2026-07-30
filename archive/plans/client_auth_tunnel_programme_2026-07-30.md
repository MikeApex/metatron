# Metatron client, transcription, auth + tunnel — fix programme

> **Status: APPROVED — PARKED FOR LATER EXECUTION (2026-07-30).**
> The VM has been offline (budget cap tripped, billing disabled), so several reported symptoms may be the outage rather than client defects. Agreed order: restore service, use the system against a working server, then pull forward only what still reproduces. This document is the approved programme, archived so its findings — which took two full audits to establish — are not re-derived later.
>
> **Immediate actions on approval (not the programme itself):**
> 1. Restore service — `./scripts/metatron-billing-override.sh 6`, relink billing, `./scripts/metatron-resume.sh`. **Order matters:** after a budget raise GCP emits stale notifications carrying the old amount for 10+ minutes, each re-disabling billing right after a relink (this is what happened 2026-07-27). Budget is already raised to $40; billing itself is still disabled.
> 2. ~~Archive this file~~ — done, this is the archived copy.
> 3. ~~Update `SESSION.md`~~ — done 2026-07-30.
> 4. **Next:** use the system normally and note which of the five symptoms survive. That list drives what gets pulled forward — do not start Phase 1 before it exists.
>
> **Service restoration was handled in a parallel chat**, not by the session that wrote this.

## Context

Five user-reported symptoms across the Android app and web PWA. Investigation found that **three of the five are not what they appear to be**, and that a sixth problem — cost — is why the system was offline during testing.

| Reported | Actual cause |
|---|---|
| "Tailscale keeps falling silent" | Mostly the client. No `case 'ping'`, no `visibilitychange`/`online` listeners anywhere. Android freezes the WebView on background; the socket dies half-open; `readyState` stays `OPEN` so sends vanish with no timeout. Restarting Tailscale forces a network-change event that finally kills the socket — which makes Tailscale *look* guilty. |
| "App blank on fresh open" | Auto-login (`index.html:911`) runs `enterApp` at script-parse time; `enterApp` hides the login screen **first**, then calls three things with no `try/catch`. `new WebSocket()` throws synchronously on a bad URL → `ws` stays `null`, `onclose` never fires, **no reconnect path exists**. History arrives *only* via the WS `history` frame — no WS means permanently blank, with no error shown. |
| "Failed to fetch" on transcribe | Server down (below), plus `/transcribe` has no timeout/retry and the server blocks its own event loop for the whole of ffmpeg + Whisper. |
| "Web app doesn't load on phone" | Server down. Also `sw.js` has **no `fetch` handler** and caches nothing, and `/` is served `no-store` — so there is no offline shell at all. |
| "Messages stay at the top" | **Not an ordering bug.** DOM order is correct (`appendChild` only; server returns oldest-first). `#conversation` is a flex column with no bottom alignment, so short content stacks at the top of a tall column. One-line CSS fix. |

**Why nothing worked during testing:** the $30 budget cap tripped, billing was disabled, the VM went offline. Infrastructure alone (e2-medium 24/7 ≈ $24.50 + external IPv4 ≈ $2.90 + disk ≈ $1) is **~$29/mo — about 95% of a $30 budget before a single AI token.** The cap was never protecting against runaway AI spend; it was tripping on the VM existing.

## Decisions taken
- **Cloudflare Tunnel + auth in the same pass**, not deferred.
- Whisper: int8 + `beam_size=1` + VAD + warm-load, **and benchmark `distil-small.en`** against `base.en` on real clips.
- **App keeps its bundled copy** of `index.html`; **exactly one APK rebuild**, at the Phase 4 cutover. Consequence: Phase 2 is validated in **desktop Chrome against the live server**, with the phone as final verification rather than the development loop.
- **Domain — revised recommendation: use a separate personal domain, not `apexgmat.com`.** Not dangerous per se, but four real couplings: one Cloudflare account means a shared blast radius between the business site and a host holding journals/clinical flags/finances; `metatron.apexgmat.com` is published permanently to public Certificate Transparency logs, associating a personal endpoint with a business entity; domain-wide cookies on `.apexgmat.com` reach every subdomain; and later Cloudflare Access would couple personal-data access to business SSO. ~$10/yr buys clean separation. Nothing before Phase 4 depends on this.

## Sequencing rationale
Error surfacing comes before every other client fix, because today a failure is a black screen carrying zero information. Server work precedes the tunnel because **Cloudflare's ~100s WebSocket idle timeout is covered only by the server's 30s ping — and that ping is an `asyncio.sleep` on the event loop that `/transcribe` currently blocks.** Auth precedes the tunnel so an unauthenticated origin is never exposed, and so an auth failure has exactly one variable.

---

## Phase 0 — Restore service, understand cost (ops only)

1. Override → relink → resume, in that order (see header).
2. Budget raised to $40. Set 50%/90% thresholds alert-only; only 100% disables.
3. **Enable BigQuery billing export** — the only route to per-SKU daily attribution. Not retroactive, 24–48h latency. For the retrospective "what burned $80", use Billing → Reports grouped by Service then SKU.

**Cost levers, ranked:**

| Lever | Saving | Note |
|---|---|---|
| **Gate check-ins on user activity** — skip if no user-originated exchange since the last one | Largest | Removes the pathological case, *which is the current state*: the VM has been running ~12 full multi-specialist pipelines/day talking to itself while the app was broken. Check `exchanges` for `proactive=0` since last check-in. |
| Stop the VM overnight (GCE instance schedule, e.g. 22:15–07:00) | ~$8–9/mo | Native feature, no code. Tradeoff: app dead overnight; `morning_brief` needs boot to land first. |
| `companion_checkin` 90 → 180 min | ~half of ~10/day | Quiet hours already cap it at ~10/day, ~12 pipelines/day total. |
| 1-yr CUD on e2-medium | ~$9/mo | **Wait** until after Phase 1 — don't commit to a machine shape while Whisper sizing is open. |

**Vertex caching: make uncached the deliberate default.** A stale-cache 404 loop ran everything uncached for weeks and the system worked — caching is an optimization with a proven failure mode, not a dependency. Before re-enabling, log `usageMetadata.cachedContentTokenCount` to check whether implicit caching is already discounting you for free.

---

## Phase 1 — Server-side (deploy only, no APK). Hard prerequisite for Phase 4.

- **Dedicated single-worker executors** in `core/server.py` — `_STT_EXECUTOR`, `_TTS_EXECUTOR`, `_ARCHIVE_EXECUTOR`. **Not `run_in_executor(None, …)`**: the default pool is shared with the LLM producer threads, and ~6 workers each spawning CTranslate2 pools on 2 vCPUs is worse than serial. Add `asyncio.Semaphore(1)` on STT so a concurrent request gets a fast **503** rather than queueing invisibly.
- **`/transcribe` (`server.py:597-646`)** — extract `_transcribe_blocking(bytes) -> str` for everything at L610-644. ffmpeg via `-i pipe:0` (no disk round-trip). Archiving moves to `_ARCHIVE_EXECUTOR` off the hot path. Record trimmed-vs-original duration in the sidecar (needed to catch VAD over-trimming).
- **Real exceptions** — replace `except FileNotFoundError` (L630): `TimeoutExpired` → 504, ffmpeg-nonzero → 422, missing binary → 500. Every path returns a JSON `{"detail": …}` body so the client's `(await res.json())` can't throw on a 502.
- **`/tts` (`server.py:561-594`)** — same executor treatment; fix the `wav_tmp` leak on the Kokoro-failure path.
- **Whisper (`core/voice_pipeline.py`)** — `device="cpu"`, `compute_type` and model size **env-overridable** (default `int8`, `base.en`), `cpu_threads=2`, `num_workers=1`; `beam_size=1`, `vad_filter=True`, `condition_on_previous_text=False`. Env-overridable matters: int8 + greedy is an *accuracy* change, so revert must be a VM env change, not a deploy.
- **Warm-load** in `_startup()` — background task, **not awaited, non-fatal**, or a bad model id turns every restart into a boot hang.
- **Benchmark harness** — walk `data/audio/*/*.webm` using existing `.json` sidecars as reference; compare current vs int8/greedy/VAD vs `distil-small.en`. Run **with the server stopped** (4GB RAM) and **verify the CT2 repo id resolves** before it becomes a default.
- **`/active` counts WebSocket exchanges**, not just SSE. Today `deploy.sh`'s drain is decorative — `_active_streams` only increments in `session_stream`, which has no client — so **every deploy kills in-flight exchanges.**
- Add `{"type":"ping"}` → `pong` handling and `X-Accel-Buffering: no` on `/session/stream`.
- **`POST /client-log`** — rate-limited JSON lines to `data/logs/client/<date>.jsonl`. Highest-leverage single addition: logcat is unreadable from a sideloaded APK mid-conversation, so "the app is blank" currently carries no information.

**Verify:** transcribe in background while hammering `/health` — max `time_total` must stay <0.2s. A WS client asserting a ping arrives within 35s **while a transcribe is in flight**. First vs second `/transcribe` after restart should match.

---

## Phase 2 — Client (`static/index.html`)

**Ship `SERVER` as runtime-configurable first** — `localStorage.getItem('metatron_server') || <compiled default>`, plus a login-screen field. ~5 lines that permanently delete the biggest risk here ("URL changes, APK isn't rebuilt, app breaks silently").

**2a — Error surfacing (first; makes everything after it diagnosable).** `window.onerror` + `unhandledrejection` → on-screen `#diag` line **and** `POST /client-log`. **`enterApp`: hide the login screen LAST**, wrap the body in try/catch. `ws.onerror`, plus **try/catch around `new WebSocket()`** — that constructor throw is the literal blank-screen bug. Replace the six silent `catch {}` (L404, 754, 793, 799, 817, 892). Guard `Notification.permission` (L856) behind `'Notification' in window` — it throws in the Android WebView on the auto-login path, an independent blank-screen candidate. `crypto.randomUUID` fallback (L589).

**2b — One connection state machine.** Single `connect()` that detaches handlers and closes the old socket before assigning a new one, with a monotonic `generation` counter captured in each closure — this is what kills the duplicate-bubble/multi-socket behaviour. Backoff with jitter, capped 30s, **reset on a successful `history` frame, not `onopen`** (which fires for sockets that die immediately). `case 'ping'` + `default:`; track `lastPingAt`; watchdog force-closes past 75s. `visibilitychange`/`pageshow`/`online`/`offline` → on resume, reconnect or probe. **This is the real fix for "restarting Tailscale makes it work."** On auth-rejection close (1008) **do not reconnect** — stop and show login, or a bad token becomes a reconnect storm through Cloudflare.

**2c — History correctness (the data-loss bugs).**
- Server emits **`type:"catchup"`** (`server.py:487-493`) instead of reusing `history`; client *appends* it. Makes the conversation-wipe structurally impossible.
- `renderHistory`: clear `shownIds` **and** `foreignBubbles` **before** the loop; **delete the eviction entirely**, use a bounded FIFO that never evicts an in-flight id. Moving `clear()` earlier (as done at L590) narrows the window; it doesn't close it.
- `lastSeenId`: reorder `_save_exchange` **before** the `done` broadcast and put `id` in the `done` payload.
- Batch render into a `DocumentFragment`; one `scrollTop` write at the end (currently ~40 reflows per render).

**2d — Send safety.** Don't clear `textField.value` until the frame is handed to an OPEN socket; single-slot outbox, flush on reconnect. Per-exchange response timeout (~180s) → mark stalled, force reconnect + catch-up.

**2e — Layout + dead code.** **Not `justify-content: flex-end`** — with `overflow-y: auto` that clips overflowing content at the top and jumps scroll in Chromium. Use `#conversation-inner { margin-top: auto }`. Delete `sendBlocking` (L607-629) and the `#agent-select` branch.

**Verify:** cold launch ×3; server stopped → login screen **with a visible error, not black**; `systemctl restart` with app foregrounded → reconnects, **history intact rather than replaced by the delta**; background 5 min → never a permanent spinner; airplane-mode toggle ×3 → no duplicate bubbles. Eviction won't reproduce naturally — test in desktop Chrome with the cap temporarily at 3.

---

## Phase 3 — Auth (still on Tailscale)

- **`METATRON_AUTH_TOKEN` in `.env`** — gitignored, already loaded via `core/orchestrator.py:56`. Compare with `secrets.compare_digest`.
- **Two tokens.** Add `METATRON_MONITOR_TOKEN`. The app token rides in localStorage on a device you carry; `/monitor/*` can read the entire diary/finance/wellbeing corpus through an arbitrary-path reader.
- **One `@app.middleware("http")`**, not per-route dependencies — new routes are then protected by default. Exempt only `/health`, `OPTIONS`, `/`, `/sw.js`, `/static/*`. Distinct 401 body so it's distinguishable from a Cloudflare 403.
- **WebSocket auth via subprotocol** — `new WebSocket(url, ['metatron.v1','token.'+t])`. Not query param (lands in access *and* Cloudflare logs); not first-frame (**breaks `core/remote_client.py:269`**, which does `await ws.recv()` expecting history immediately). Server **must** echo the accepted subprotocol or browsers fail the handshake. Validate **before** `manager.connect()`; close 1008 without accepting.
- **Make the login password field real** (currently ignored) → `POST /auth/verify` → store token. Route all six bare fetches through an `api()` wrapper; on 401 clear token and show login.
- **Harden `/monitor/*`** — replace the `".." not in path` string check with `resolve()` + `is_relative_to()`, which also handles symlinks. Apply to **both** `/monitor/history` (L890, currently weaker) and `/monitor/file` (L932).
- **CORS** `allow_origins=["*"]` → explicit list.
- **Update all four clients:** `deploy.sh` (read the token from the VM's own `.env` *inside* the remote heredoc — never interpolate from the Mac); `tools/metatron_monitor.py` (four `httpx` sites, flip `verify=False` → `True` after Phase 4); `core/remote_client.py` (subprotocol in `_run` and `_send_one`). **Point `DEFAULT_SERVER` at `localhost`** — the scheduler currently makes the VM loop out through Tailscale to reach itself, so a tunnel hiccup silently kills check-ins into an unread error log.

**Rollout — the outage risk.** `METATRON_AUTH_MODE = off|warn|enforce`. Deploy in `warn` (validate, log, still serve) → the caller list becomes empirical → update clients one at a time until the warn log is clean → flip to `enforce` only after **a full day** (weekly jobs won't appear within an hour). Revert is ~5 seconds.

---

## Phase 4 — Cloudflare Tunnel cutover

**Named** tunnel as a systemd unit — not a quick tunnel, whose URL changes on restart. Ingress → `https://localhost:8001` with `noTLSVerify: true`. Hostname on whichever domain is chosen (see Decisions).

**Cloudflare settings that will bite:** WebSockets on (default). **Disable Rocket Loader and Auto Minify on this hostname** — the entire app is one inline `<script>` and they rewrite it. Bot Fight Mode may 403 the WebView UA. The ~100s idle timeout is not configurable on free; the 30s ping is the only cover — hence Phase 1.

**Cloudflare Access on `/monitor/*` only, not the app.** Access in front of the app needs interactive SSO inside a Capacitor WebView — high risk of recreating the blank-screen class just fixed. The monitor is a Python TUI that can use a service token with no interactive flow.

**Cutover order:** tunnel up **alongside** Tailscale → verify from the Mac with phone Tailscale off → **the one APK rebuild** carrying all of Phase 2 + token login + tunnel URL as compiled default → verify **with Tailscale still up** → turn Tailscale off → **keep the Tailscale origin working two weeks** before decommissioning.

**Also here — kill the cert time bomb.** Tailscale certs are 90-day with no renewal automation. Rather than automate renewal, once cloudflared uses `noTLSVerify`, bind uvicorn to `127.0.0.1` plain HTTP and let Cloudflare own public TLS. Deletes the failure mode instead of scheduling around it — as a small step *after* the cutover settles.

**Verify:** the combined regression test — a WS client through the tunnel idle for 150s asserting ≥4 pings and no close, **run while a `/transcribe` is in flight.** Proves Phases 1 and 4 together, and would have caught the original misdiagnosis.

---

## Phase 5 — PWA shell, offline, notifications (lowest priority)

`manifest.json` + `<link rel="manifest">`; **register the SW unconditionally** (currently only inside the notification path, so two devices run different code). Add a cache-first `fetch` handler to `sw.js` — and change `/` from `Cache-Control: no-store` to `no-cache`, because **`no-store` forbids caching outright, so the offline shell cannot work until that changes.**

Notifications: `POST_NOTIFICATIONS` is missing from the manifest (Android 13+ blocks without it), but Web Push doesn't exist in the Android WebView at all, so adding it alone changes nothing. **For one user, skip FCM entirely** — deliver check-ins over the already-open WebSocket and raise a *local* notification via `@capacitor/local-notifications`.

---

## Risks
1. **Auth rollout = total outage.** Mitigated by `warn` → per-client verification → `enforce`.
2. **The scheduler is the caller you'll forget** — a WebSocket client on the VM that fails into a JSON file nobody reads (189 identical failures once needed a live reproduction to find).
3. **Every deploy currently kills in-flight WS exchanges.** Fix in Phase 1 first.
4. **`vad_filter=True` will silently swallow quiet speech**, stacking with client-side silence detection to produce "No speech detected" where it used to work — hence logging trimmed-vs-original duration.
5. **Warm-loading turns a model-id typo into a boot failure** — non-fatal, non-awaited, verify the distil CT2 repo id first.
6. **4GB RAM** — benchmark with the server stopped, or on the Mac.
7. **Gitignored config doesn't travel with `./deploy.sh`** — `config/personas/mike/scheduler.yaml` and `.env` need manual scp. "Works locally, not on the VM" is almost always this.

**Revert:** Phase 1 `git revert` + deploy · Phase 2 reinstall previous APK · Phase 3 `METATRON_AUTH_MODE=off` + restart (~5s) · Phase 4 edit `localStorage.metatron_server` back, stop `cloudflared` · Phase 5 unregister SW.

## Roadmap alignment
Phase 3 implements roadmap **B2** auth ("shared secret / token, not Tailscale ACL"). Phase 4 implements the Section 5A **Cloudflare Tunnel** pre-Alpha item. Nothing here touches frozen `config/agents/*.md` or the constitution. `core/server.py` changes sit in the parts A8 keeps, not the `/monitor/*` block it will extract.
