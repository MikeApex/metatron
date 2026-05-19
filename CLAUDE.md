# Personal AI Life Manager — Developer Context

This file is loaded into every Claude Code session. It describes the project architecture, conventions, and key design principles for the developer (Claude Code). It is NOT the runtime system — that is `core/orchestrator.py`.

---

## What This Project Is

A voice-first personal AI life manager. A director and companion for a human life, not a scheduler or task manager. Built on a thin Python harness with all behavior living in editable config files.

**Core principle:** Config files are the product. Code is infrastructure. If changing behavior requires a code change, that is a design failure.

---

## Terminology

Use precise names. Avoid pronouns and generic terms.

| Term | Meaning |
|---|---|
| **Claude Code** | The development interface — the CLI/IDE tool used to build this project. Not the runtime. |
| **Orchestrator** | `core/orchestrator.py` — the runtime brain. Loads config, calls a model API, dispatches tools. |
| **[Model name]** | The specific AI model called at runtime. Always refer to models by name: Sonnet 4.6, Haiku 4.5, qwen3:14b, gemini-2.5-flash, gpt-4o. Never use "Claude" as a generic runtime label. |
| **[Agent name]** | The instruction file loaded for a session. Always use the agent's name: Time Director, Goals Interviewer, Diarist. Not "the agent" generically. |
| **Anthropic API** | Cloud API for Anthropic models (Sonnet 4.6, Haiku 4.5, etc.). |
| **OpenAI API** | Cloud API for OpenAI models (gpt-4o, etc.). |
| **Ollama** | Local model server at `localhost:11434`. Runs models like qwen3:14b locally. |
| **Gemini API** | Google's API for Gemini models (gemini-2.5-flash, etc.). |

The `--provider` flag in the Orchestrator CLI is a code-level routing argument. In documentation and comments, name the specific API or model instead.

---

## Four-Tier Goal Hierarchy

| Tier | File | Owned by | Changes |
|---|---|---|---|
| 0 — Tool Constitution | `config/constitution.md` | The tool | Never |
| 1 — Prime Directive | `config/prime_directive.md` | User | Rarely |
| 2 — Mission | `config/mission.md` | User | At life transitions |
| 3 — Goals | `config/goals.yaml` | User | Frequently |

Always load in this order. The Constitution is the root context for every agent.

---

## Directory Layout

```
core/               Runtime Python — the harness. Rarely changes.
  orchestrator.py   The Orchestrator: config loading, model API calls, tool dispatch, REPL
  scheduler.py      Proactive initiation daemon (Phase 4)
  memory.py         FAISS vector memory (Phase 3)
  voice_pipeline.py Whisper STT + TTS (Phase 2)
  server.py         FastAPI server for PWA (Phase 2)

config/             Config files — the product. Edit these to change behavior.
  constitution.md   Tier 0: tool philosophy (read-only at runtime)
  prime_directive.md Tier 1: user terminal values
  mission.md        Tier 2: current life chapter
  goals.yaml        Tier 3: 90-day / weekly / daily goals
  agents/           Sub-agent instruction files (Markdown)
  templates/        Check-in and interaction templates (Markdown)
  modules/          Per-module YAML settings
  personas/         Development test personas (Markdown)
  research/         Per-feature research archives (Markdown) — informational, not prescriptive

data/               User data — append-only, sensitive-tier local-only
  logs/             Daily check-in records (JSON, YYYY-MM-DD.json)
  journal/          Free-form journal entries
  wisdom/           Life Wisdom Depot (YAML/JSON)
  archive/          Movies, books, experiences, ideas
  memory/           FAISS index files

tools/              MCP tool implementations (Python)
  logger.py         write_log(), read_log()

archive/plans/      Historical plan revisions — for reference only
```

---

## Data Privacy Tiers

| Tier | Examples | Storage | Analysis |
|---|---|---|---|
| Open | Research, general queries with no personal context | Cloud OK | Cloud LLM |
| Sensitive | All goal data (`private_why`, `shareable_what`), activity logs, health, finances, prime directive, mission | Local only | Local LLM only |

The semi-sensitive tier has been collapsed into sensitive. Empirical testing showed that `shareable_what` (instrumental goals) carries sufficient inferential signal to reconstruct `private_why` when combined with behavioral patterns — the privacy boundary between them does not hold in practice. All personal context is now sensitive-tier by default.

Cloud LLMs are used only for fully decontextualized tasks: generic research, writing, or advice with no personal context attached. Enforce at the tool layer, not in prompts.

---

## Adding a New Module

1. Create `config/agents/{module_name}.md` — agent instruction file
2. Add tools to `tools/{module_name}.py` — Python functions + JSON schemas
3. Add `config/modules/{module_name}.yaml` — settings if needed
4. Register tools in `core/orchestrator.py` → `register_tools()`

No other code changes required.

---

## Tool Pattern

Every tool follows this pattern in `tools/`:

```python
def my_tool(param: str) -> str:
    """Does the thing."""
    # implementation
    return result

MY_TOOL_SCHEMA = {
    "name": "my_tool",
    "description": "Does the thing.",
    "input_schema": {
        "type": "object",
        "properties": {
            "param": {"type": "string", "description": "What param does"}
        },
        "required": ["param"]
    }
}
```

Register by adding `(my_tool, MY_TOOL_SCHEMA)` to the list in `orchestrator.register_tools()`.

---

## Design Principles

**Discretion between layers.** Users see output, not process. When building agents, interviews, or inter-model features: the methodology is infrastructure. Never surface which model was called, which framework shaped a question, or how a recommendation was derived — unless that transparency is an explicit design goal of the feature. This applies to agent config files, tool implementations, and orchestrator routing alike.

**Privacy between layers.** Sensitive data routing (local vs. cloud LLMs) is enforced in Python tool code and is never narrated, leaked across agents, or exposed in user-facing output. Agents must not reference their own model identity, data tier, or routing decisions in responses. The system enforces privacy silently.

**The tool surfaces hypotheses, not verdicts.** Interviews, check-ins, and audits produce a working hypothesis about who the user is and what they want — a first draft that gets verified or falsified through daily use and regular re-interviews. Build features with this in mind: output should invite correction, not foreclose it. This framing is internal to the development context and is never surfaced to users.

See `config/constitution.md` for the runtime expression of these principles. See `config/frameworks.md` for the theoretical literature informing them.

---

## Coding Conventions

- Python 3.11+
- No frameworks beyond what's needed (FastAPI for server, FAISS for memory, anthropic SDK)
- Flat, readable functions — no premature abstraction
- Type hints on all public functions
- Config files: Markdown for narrative content, YAML for structured settings, JSON for data records
- All sensitive data paths must be enforced in Python tool code, never in prompts

---

## Per-System Configuration (new machine checklist)

These items are hardcoded for the current dev machine and will need adaptation on any new system. A proper setup/onboarding flow is deferred to a later phase — for now, find and update these manually:

| What | Where | How to find the right value |
|---|---|---|
| TTS voice name | `core/voice_pipeline.py` → `speak()` default arg | Run `say -v '?'` in terminal; download Premium voices via System Settings → Accessibility → Spoken Content |
| `OPENAI_API_KEY` | `~/.zprofile` (exported) or `.env` in project root | console.openai.com |
| `ANTHROPIC_API_KEY` | `.env` in project root | console.anthropic.com (needs credits) |
| `GEMINI_API_KEY` | `.env` in project root | aistudio.google.com/apikey |
| Whisper model size | `core/voice_pipeline.py` → `WHISPER_MODEL_SIZE` | `"base.en"` (fast), `"small.en"` (more accurate), `"medium.en"` (best quality) |
| Local LLM model | TBD — Phase 3 | Ollama: `ollama list` to see installed models |
| TLS cert for phone | `certs/` (gitignored) | `brew install mkcert && mkcert -install && cd certs && mkcert <local-ip> localhost 127.0.0.1` |

---

## Model Version Maintenance

Model IDs in `core/orchestrator.py` and `config/modules/routing.yaml` drift as providers release new versions. Check and update at the start of each new phase, or when a provider announces a new model in a session:

| What to check | Where | How |
|---|---|---|
| Anthropic models | `ANTHROPIC_MODEL`, `routing.yaml` cloud_deep | console.anthropic.com/docs/models |
| OpenAI models | `OPENAI_MODEL` | platform.openai.com/docs/models |
| Gemini models | `GEMINI_MODEL`, `GEMINI_PRO_MODEL`, `routing.yaml` cloud_fast/cloud_deep | aistudio.google.com / Gemini API docs |
| MCP ask_gemini | session-level via `mcp__ask_gemini__set_model` | MCP tool description lists available options |
| Ollama | `OLLAMA_MODEL` | `ollama list` on the local machine |

Current model IDs (updated 2026-05-19): Sonnet 4.6, o3, gemini-3.1-flash-lite-preview (flash), gemini-3.1-pro-preview (pro).

---

## Key Design Decisions (don't revisit without good reason)

- Orchestrator calls Claude API directly (not Claude Code sessions at runtime)
- Tools are Python functions registered as Claude API tool schemas — no separate MCP server processes at runtime
- Scheduler daemon invokes orchestrator sessions; orchestrator itself is stateless between sessions
- FAISS for memory — prevents context window limits from degrading long-term recall
- `age` encryption in Phase 6 — not before real sensitive data accumulates
