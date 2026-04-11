# Personal AI Life Manager — Developer Context

This file is loaded into every Claude Code session. It describes the project architecture, conventions, and key design principles for the developer (Claude Code). It is NOT the runtime system — that is `core/orchestrator.py`.

---

## What This Project Is

A voice-first personal AI life manager. A director and companion for a human life, not a scheduler or task manager. Built on a thin Python harness with all behavior living in editable config files.

**Core principle:** Config files are the product. Code is infrastructure. If changing behavior requires a code change, that is a design failure.

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
  orchestrator.py   Claude API loop, config loading, tool dispatch
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
| Open | Research, general queries | Cloud OK | Cloud LLM |
| Semi-sensitive | Instrumental goals (`shareable_what`), activity logs | Local primary | Cloud summaries only |
| Sensitive | Core goals (`private_why`), health, finances, prime directive | Local only | Local LLM only |

Sensitive data is **never** passed to a cloud LLM. Enforce at the tool layer, not in prompts.

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

## Coding Conventions

- Python 3.11+
- No frameworks beyond what's needed (FastAPI for server, FAISS for memory, anthropic SDK)
- Flat, readable functions — no premature abstraction
- Type hints on all public functions
- Config files: Markdown for narrative content, YAML for structured settings, JSON for data records
- All sensitive data paths must be enforced in Python tool code, never in prompts

---

## Key Design Decisions (don't revisit without good reason)

- Orchestrator calls Claude API directly (not Claude Code sessions at runtime)
- Tools are Python functions registered as Claude API tool schemas — no separate MCP server processes at runtime
- Scheduler daemon invokes orchestrator sessions; orchestrator itself is stateless between sessions
- FAISS for memory — prevents context window limits from degrading long-term recall
- `age` encryption in Phase 6 — not before real sensitive data accumulates
