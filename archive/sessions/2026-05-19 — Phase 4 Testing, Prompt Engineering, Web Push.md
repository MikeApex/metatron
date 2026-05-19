# 2026-05-19 — Phase 4 Testing, Prompt Engineering, Web Push

## What was built

### Phase 4 complete
- Pattern Miner agent, baseline period tools, sensitive routing toggle, scheduler daemon, Web Push
- 23 tools registered in orchestrator (was 14)
- Baseline period tools: write/read/retrospective/context — user-defined reference periods with time-dilation layer
- `get_log_window` max_entries cap added to prevent token rate limit on large windows

### Four-way Pattern Miner test (Sonnet 4.6, Gemini Flash, Gemini Pro, GPT-4o)
Reports at `tests/phase4_report_*`

**Before prompt fix:**
- Sonnet 4.6: full structured analysis, verbatim quotes, graded confidence — best by a wide margin
- Gemini Pro: process summary ("here's what I did"), no evidence quoted
- Gemini Flash: thin findings summary, no structure
- GPT-4o: weakest — generic summary, no evidence, no format compliance

**Root cause diagnosis (polled all three models):**
Gap was prompt compliance, not capability. Models defaulted to "helpful assistant reporting back" mode. Gemini identified: Sonnet treats complex system prompts as a *procedural contract to fulfill completely*; GPT-4o and Gemini default to *conversational intent* (summarise helpfully).

**Prompt fix applied to pattern_miner.md:**
- Evidence-first output format (write `[EVIDENCE]` before `[OBSERVATION]` — anchors on data before generalising)
- Anti-meta directive at end of file: "Do not summarise what you did. Your output IS the report. Begin immediately with the first [EVIDENCE] block."

**After prompt fix:**
- Gemini Pro: fully transformed — comparable to Sonnet, 4 structured observations per scale, verbatim quotes
- GPT-4o: no improvement — ignored all new instructions. Needs one-shot example + "Data Extraction Pipeline" persona framing to go further. Written off for structured analytical agents for now.

### Privacy architecture note
FAISS matrices can't be sent to external models (not tokens; inversion attacks exist). Statistical pre-aggregation is the right privacy layer: run FAISS + log retrieval locally → extract aggregate statistics → send only numbers to external model. Added to `research/pm_future.md`.

### Web Push (Android, Tailscale)
Confirmed working. Issues fixed along the way:
- VAPID key was malformed PKCS8 — regenerated as EC PEM; push.py converts to DER base64url for py_vapid
- `/sw.js` had no server route — added explicit route with correct MIME type and Service-Worker-Allowed header
- Notification permission prompt requires user gesture on Android Chrome — added "Enable notifications" button
- `Cache-Control: no-store` on index.html prevents stale PWA serving
- subscribePush now unsubscribes existing before re-subscribing (handles VAPID key rotation)
- Service worker updated with skipWaiting + clients.claim for immediate activation

**Remaining limitation:** Web push on Android doesn't show banner popup (heads-up notification). Sound + notification shade works. Full banner control requires native Android app — deferred to Phase 6.

## Key decisions

- **Routing unchanged:** o3 remains Pattern Miner target (untested); Sonnet fallback; Gemini Pro now viable secondary fallback after prompt fix
- **GPT-4o written off** for structured analytical agents until one-shot example treatment tested
- **Notification banner** — web push limitation accepted; revisit with native app in Phase 6
- **Gemini MCP set to 3.1 Pro** as default for dev sessions

## What's next
- Phase 5 planning (user research session needed first per project_revision_notes)
- o3 Pattern Miner test (pending — ~$4-8 estimated)
- GPT-4o one-shot prompt fix (optional)
- Backup setup: Restic to external drives (deferred from Phase 4)
- Ollama setup when capable local model available — flips routing.yaml local_enabled to true
