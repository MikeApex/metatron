# Project Status — Phase Handoff

*Read this at the start of each new session, alongside CLAUDE.md.*

---

## Current Phase: 3 (ready to begin)

**Phase 0 is complete. Phase 1 is complete** (pending goals interview redesign and sandbox calendar — both deferred by design). Phase 2 is ready to begin.

**Provider note:** OpenAI (`--provider openai`) is the active provider for development. Anthropic API key needs credits added before switching back to `--provider anthropic` (default).

---

## What Phase 0 Produced

All files listed in the Phase 0 plan exist and are working:

| File | Status | Notes |
|---|---|---|
| `core/orchestrator.py` | Complete | Full agentic loop: config loading, Claude API call, tool dispatch, interactive REPL |
| `tools/logger.py` | Complete | `write_log` + `read_log`, both registered as Claude API tool schemas |
| `config/constitution.md` | Complete | Full Tier 0 text from Revision 3.1 |
| `config/prime_directive.md` | Stub | Blank — filled at goals interview |
| `config/mission.md` | Stub | Blank — filled at goals interview |
| `config/goals.yaml` | Schema ready | Full schema with `private_why`/`shareable_what`/`id`/`parent_goal` — filled at goals interview |
| `config/agents/time_director.md` | Complete | Full instruction file |
| `config/agents/diarist.md` | Complete | Full instruction file |
| `config/templates/daily_checkin.md` | Complete | Full 4-phase template with log schema |
| `data/logs/2026-04-11.json` | Exists | Written during Phase 0 verification |
| All other `core/` files | Stubs | `scheduler.py`, `memory.py`, `voice_pipeline.py`, `server.py` — placeholder only |

**Verification passed:** `python core/orchestrator.py --input "test"` calls the Claude API, dispatches tools, writes a log file.

**.venv** is at the project root, using Python 3.14. Runtime dependencies: `anthropic`, `pyyaml`, and transitive deps.

---

## Phase 1 Progress

| Task | Status | Notes |
|---|---|---|
| `tools/logger.py` — chmod 600 on write | Done | Log files now written with 600 permissions |
| `tools/goals.py` — read/write goals + 600 permissions | Done | `read_goals` + `write_goals` tools registered |
| `config/goals.yaml` — schema designed | Done | `id`, `private_why`, `shareable_what`, `parent_goal`, `essential`, `context` fields |
| `config/templates/daily_checkin.md` | Done | 4-phase template with log schema |
| `config/personas/pepys.md` | Done | Samuel Pepys — richly ordinary life, competing pleasures/duties |
| `config/personas/nin.md` | Done | Anaïs Nin — creative life, relational complexity, emotional weather |
| `config/personas/aurelius.md` | Done | Marcus Aurelius — duty-heavy, no slack, lifetime-scale values |
| **Sandbox calendar setup** | **Pending — user action** | Create a dedicated Google account or isolated sub-calendar for dev. No CalDAV coding yet. Share read-only when wired up in a later phase. |
| **Goals interview** | **Redesign needed** | Interview flow must start from concrete goals → values, not abstract value questions. See feedback memory. |
| **pyyaml dependency** | Done | Already installed in .venv |
| **Verification** | Done | Check-in against Pepys persona passed; write_log confirmed (600 perms, correct JSON) |

---

## Dependency Note

`tools/goals.py` uses `pyyaml`. Install before running any session that may call goals tools:

```bash
cd /Users/md-homefolder/Desktop/multi-model-mcp
source .venv/bin/activate
pip install pyyaml
```

---

## What Phase 1 Still Requires

1. **Sandbox calendar setup (user action):** Create a dedicated Google account or isolated sub-calendar. No real calendar data in development. Share read-only when CalDAV is wired up (later phase).
2. **Install pyyaml** (see above)
3. **Goals interview:** Discovery → Visioning → Detailing (~20 min). Populates the three stub config files.
4. **Verification:** Run a full check-in session against a persona or the real config. Confirm log is written, goals are loadable, directed plan is produced.

---

## Key Decisions Already Made (don't re-open without cause)

- Orchestrator calls Claude API directly — not Claude Code at runtime. Stateless between sessions.
- Tools are Python functions + JSON schemas registered in `orchestrator.register_tools()`. No separate MCP server processes.
- Sensitive data never passes to a cloud LLM — enforced at the Python tool layer, not in prompts. (Phase 3: local LLM routing for analysis.)
- Local file permissions (600) are the protection mechanism until `age` encryption in Phase 6.
- FAISS for memory (Phase 3). No vector DB until then.
- All integrations are MCP tools in this repo. No third-party plugins.
- Calendar sandbox = isolated dev account/calendar, read-only. No write access during development.

---

## Phase 2 Progress

| Task | Status | Notes |
|---|---|---|
| `core/voice_pipeline.py` | Done | faster-whisper STT + macOS `say` TTS; `run_voice_session()` interactive loop |
| `core/server.py` | Done | FastAPI; `/session` endpoint; serves PWA |
| `static/index.html` | Done | Mobile PWA; Web Speech API STT+TTS; provider/agent selectors |
| **Verification** | Done | Laptop voice verified (Whisper + edge-tts). All 4 providers confirmed: OpenAI, Gemini, Ollama (qwen3:14b), Anthropic (pending credits). Phone pending — Android/Chrome needs HTTPS for mic. |

**To verify:**
1. `source ~/.zprofile && source .venv/bin/activate`
2. `PYTHONPATH=. python core/server.py --provider openai`
3. Find your IP: `ipconfig getifaddr en0`
4. Open `http://<ip>:8000` on phone (same WiFi)

**iOS note:** Web Speech API requires Safari on iOS and HTTPS for full mic access — if `http://` blocks the mic, see HTTPS workaround note below.

---

## Session Notes — 2026-05-12

- Reviewed all pending uncommitted changes — all correct, ready to commit
- Goals interview deferred to next session (post OS update)
- Local LLM and model flexibility discussed — see sections below

---

## Local LLM — Decision Pending (raised 2026-05-12)

The privacy architecture always assumed a local LLM for sensitive-tier data (Phase 3). The question to resolve before wiring it in:

**Role options:**
1. Strictly the sensitive-data processor — `private_why`, health, finances never leave local
2. A fourth peer model alongside Claude/GPT/Gemini for all queries
3. Both — peer for general use AND the enforced route for sensitive data

**Recommendation:** Ollama on macOS — OpenAI-compatible API at `localhost:11434`, easy model swaps, integrates cleanly with the existing orchestrator routing pattern.

Decide the role before building the routing logic.

---

## Open Questions Deferred to Phase 1+

- Goals interview structure — follow the plan but adapt to the conversation
- Whether Work & Vocation becomes one module or two (decide at Phase 5)
- Module priority order (finalize after goals interview)
- Local LLM role (see above)
- Model flexibility: only `run_session()` in `core/orchestrator.py` is Anthropic-coupled — tool schemas (input_schema vs parameters), SDK client, response block parsing. Fix is ~50–80 lines (two session functions + sensitivity-tier router). Config files and tool functions are fully model-agnostic.

---

## How to Pick Up

```bash
cd /Users/md-homefolder/Desktop/multi-model-mcp
source .venv/bin/activate
pip install pyyaml          # if not already installed
python core/orchestrator.py   # verify it still runs
```

Then either:
- **Conduct the goals interview** — interactive session with the Time Director agent
- **Test against a persona** — load a persona config manually and run a check-in
