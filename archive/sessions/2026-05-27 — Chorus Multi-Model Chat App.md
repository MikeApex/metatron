# 2026-05-27 — Chorus Multi-Model Chat App

## Summary

Full build session for **Chorus**, a standalone multi-model chat app at `/Users/md-homefolder/Desktop/chat/`. Packaged as a native macOS `.app` (PyInstaller + pywebview/WKWebView).

---

## What Was Built

### Core App
- FastAPI + uvicorn server on a dynamic port
- pywebview (WKWebView) native window — no browser involved
- PyInstaller `.app` bundle (`chorus.spec`, `build_mac.sh`, `make_icon.py`)
- Installed to `/Applications/Chorus.app`
- API keys stored in `~/Library/Application Support/Chorus/config.json`

### UI (index.html)
- Sidebar with grouped chat history (Today / Yesterday / Last 7 days / Older)
- Panel mode as default; Single mode available
- Markdown rendering via marked.js
- System prompt toggle
- Budget controls
- Conflict mode toggle (⚡, amber)

### Panel Mode
- Arbitrator consults panel members via tool use (Anthropic) or function calling (OAI/Gemini)
- SSE streaming with progress events
- Usage tracking and cost display
- **Consensus** section now required in all arbitrator responses

### Conflict Mode (multi-round debate)
- **Round 1**: All models (including arbitrator) debate in parallel; each knows its opponents
- **Round 2**: Each model reads all Round 1 responses and rebuts directly
- **Verdict**: Arbitrator judges as "Arbitrator" (model name hidden); must evaluate itself fairly; includes **Consensus** section
- **Closing Statement**: Winner delivers Alito/PMQs-style closing (<120 words)
- All rounds stream to UI as they complete
- Conflict chats tagged ⚡ amber in sidebar

### Model-Specific Debate Prompts
Each model gets prompting tuned to its own advice (asked via MCP):
- **Claude**: devastating clarity, internal contradictions, no hedge words, end on force
- **GPT**: Achilles' heel finder, pithy, historical analogies, no literalism
- **Gemini**: intellectual provocateur, "magnificent jerk", logically merciless, no parliamentary formalism

### Chat Persistence
- Server-side storage: `~/Library/Application Support/Chorus/chats.json`
- `/chats` GET/POST/DELETE endpoints
- Survives WKWebView localStorage resets between app restarts
- Max 200 chats retained

### Spending Caps
- $5.00/24h, $1.25/6h — hardcoded, persistent across restarts
- Ledger: `~/Library/Application Support/Chorus/spend_ledger.json`

---

## Key Files

| File | Purpose |
|---|---|
| `server.py` | FastAPI app, all model logic, spending caps, chat storage |
| `static/index.html` | Full frontend SPA |
| `launch.py` | Entry point: port discovery, server thread, pywebview window |
| `config.py` | API key persistence via platformdirs |
| `chorus.spec` | PyInstaller build spec |
| `build_mac.sh` | Build script |
| `make_icon.py` | Generates chorus.icns from brand colors |

---

## Bugs Fixed This Session
- `import time` missing from server.py (`_SpendingLedger` crash)
- `_CONFLICT_MEMBER_SYSTEM` constant deleted but still referenced in `dispatch_fn`
- Arbitrator excluded from debate rounds (now participates as full contestant)
- Closing statement truncated (token limit raised, prompt trimmed)
- Chat history not persisting between app launches (moved to server-side storage)
- Gemini responses truncated (`max_tokens` raised to 4096 throughout)
- `_parse_winner` failing silently (made robust + fallback added)

---

## Pending / Known Gaps
- Closing statement reliability still being tested
- No Windows build tested
- No Gatekeeper signing (right-click → Open workaround documented)
- System prompt field UX could use a tooltip explaining its purpose
