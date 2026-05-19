"""
core/orchestrator.py — the runtime brain.

Loads config files (constitution → prime_directive → mission → goals → agent),
builds the system prompt, calls the model API, and handles tool dispatch.

This is the RUNTIME system. It is separate from Claude Code (the development assistant).
CLAUDE.md is for the development context; this file is what runs the life manager.

Usage:
    python core/orchestrator.py                                    # interactive, time_director agent
    python core/orchestrator.py --agent diarist                    # use a specific agent
    python core/orchestrator.py --provider openai                  # use OpenAI instead of Anthropic
    python core/orchestrator.py --persona pepys                    # load a dev persona
    python core/orchestrator.py --input "how am I doing?"         # single-shot input
"""

import argparse
import json
import os
import sys
from pathlib import Path

import anthropic
import openai
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent.parent
CONFIG_DIR = ROOT / "config"
AGENTS_DIR = CONFIG_DIR / "agents"

ANTHROPIC_MODEL = "claude-sonnet-4-6"
OPENAI_MODEL = "o3"
OLLAMA_BASE_URL = "http://localhost:11434/v1"
OLLAMA_MODEL = "qwen3:14b"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_MODEL = "models/gemini-3.1-flash-lite-preview"   # flash default; use GEMINI_PRO_MODEL for full Pro
GEMINI_PRO_MODEL = "models/gemini-3.1-pro-preview"


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def load_config(persona: str | None = None) -> str:
    """
    Build the system prompt from the four-tier config hierarchy.
    Loads: constitution → prime_directive → mission → goals.
    If persona is given, loads config/personas/{persona}.md instead of the
    prime_directive/mission/goals stubs — for development testing only.
    Returns a single string for use as the system prompt.
    """
    sections = []

    constitution_path = CONFIG_DIR / "constitution.md"
    if constitution_path.exists():
        content = constitution_path.read_text().strip()
        if content:
            sections.append(f"## Tool Constitution\n\n{content}")

    if persona:
        persona_path = CONFIG_DIR / "personas" / f"{persona}.md"
        if not persona_path.exists():
            raise FileNotFoundError(f"Persona not found: {persona_path}")
        sections.append(f"## Development Persona\n\n{persona_path.read_text().strip()}")
        return "\n\n---\n\n".join(sections)

    files = [
        ("Prime Directive", CONFIG_DIR / "prime_directive.md"),
        ("Mission", CONFIG_DIR / "mission.md"),
    ]

    for label, path in files:
        if path.exists():
            content = path.read_text().strip()
            if content:
                sections.append(f"## {label}\n\n{content}")

    goals_path = CONFIG_DIR / "goals.yaml"
    if goals_path.exists():
        goals_content = goals_path.read_text().strip()
        if goals_content:
            sections.append(f"## Current Goals\n\n```yaml\n{goals_content}\n```")

    return "\n\n---\n\n".join(sections)


def load_agent(name: str) -> str:
    """Load a sub-agent instruction file from config/agents/{name}.md."""
    agent_path = AGENTS_DIR / f"{name}.md"
    if not agent_path.exists():
        raise FileNotFoundError(f"Agent not found: {agent_path}")
    return agent_path.read_text().strip()


def load_recent_context(persona: str | None = None, days: int = 5) -> str:
    """
    Load the last N days of logs and the context tracker into a string
    for injection into the system prompt as short-term memory.

    Returns empty string if no recent data exists.
    """
    import json as _json
    from datetime import date, timedelta
    from pathlib import Path

    persona_env = os.environ.get("AI_TEST_PERSONA") or persona

    if persona_env:
        logs_dir = ROOT / "data" / "personas" / persona_env / "logs"
        tracker_path = ROOT / "data" / "personas" / persona_env / "context.json"
    else:
        logs_dir = ROOT / "data" / "logs"
        tracker_path = ROOT / "data" / "context.json"

    sections = []

    # Context tracker (mid-term: open threads, patterns, follow-ups)
    if tracker_path.exists():
        try:
            tracker = _json.loads(tracker_path.read_text())
            lines = [f"## Session Context (last session: {tracker.get('last_session', 'unknown')})"]
            if tracker.get("open_threads"):
                lines.append("**Open threads:** " + " | ".join(tracker["open_threads"]))
            if tracker.get("patterns"):
                lines.append("**Patterns noted:** " + " | ".join(tracker["patterns"]))
            if tracker.get("follow_ups"):
                lines.append("**Follow up on:** " + " | ".join(tracker["follow_ups"]))
            sections.append("\n".join(lines))
        except Exception:
            pass

    # Recent logs (short-term: last N days)
    today = date.today()
    recent_entries = []
    for i in range(days):
        d = (today - timedelta(days=i)).isoformat()
        log_path = logs_dir / f"{d}.json"
        if log_path.exists():
            try:
                entry = _json.loads(log_path.read_text())
                recent_entries.append(f"  {d}: {_json.dumps(entry, ensure_ascii=False)}")
            except Exception:
                pass

    if recent_entries:
        sections.append("## Recent Logs (last 5 days)\n" + "\n".join(recent_entries))

    return "\n\n---\n\n".join(sections)


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

def register_tools() -> tuple[list[dict], dict]:
    """
    Register all available tools.

    Returns:
        schemas: Anthropic-format tool schemas (translated for OpenAI when needed).
        handlers: Dict mapping tool name → Python function.
    """
    from tools.logger import write_log, read_log, WRITE_LOG_SCHEMA, READ_LOG_SCHEMA
    from tools.goals import read_goals, write_goals, READ_GOALS_SCHEMA, WRITE_GOALS_SCHEMA
    from tools.config_writer import write_config, WRITE_CONFIG_SCHEMA
    from tools.diarist import (
        write_journal, read_journal, WRITE_JOURNAL_SCHEMA, READ_JOURNAL_SCHEMA,
        write_archive, read_archive, WRITE_ARCHIVE_SCHEMA, READ_ARCHIVE_SCHEMA,
    )
    from tools.wisdom import (
        write_wisdom, read_wisdom, WRITE_WISDOM_SCHEMA, READ_WISDOM_SCHEMA,
        find_duplicate_wisdom, merge_wisdom_entries,
        FIND_DUPLICATE_WISDOM_SCHEMA, MERGE_WISDOM_ENTRIES_SCHEMA,
    )
    from tools.pattern_miner import (
        get_log_window, write_insight_report, read_recent_insights,
        GET_LOG_WINDOW_SCHEMA, WRITE_INSIGHT_REPORT_SCHEMA, READ_RECENT_INSIGHTS_SCHEMA,
    )
    from tools.baselines import (
        write_baseline_period, read_baseline_periods,
        write_retrospective, get_baseline_context,
        WRITE_BASELINE_PERIOD_SCHEMA, READ_BASELINE_PERIODS_SCHEMA,
        WRITE_RETROSPECTIVE_SCHEMA, GET_BASELINE_CONTEXT_SCHEMA,
    )
    from tools.memory_tool import search_memory, SEARCH_MEMORY_SCHEMA
    from tools.context_tracker import (
        read_context_tracker, write_context_tracker,
        READ_CONTEXT_TRACKER_SCHEMA, WRITE_CONTEXT_TRACKER_SCHEMA,
    )

    schemas = [
        WRITE_LOG_SCHEMA, READ_LOG_SCHEMA,
        READ_GOALS_SCHEMA, WRITE_GOALS_SCHEMA,
        WRITE_CONFIG_SCHEMA,
        WRITE_JOURNAL_SCHEMA, READ_JOURNAL_SCHEMA,
        WRITE_ARCHIVE_SCHEMA, READ_ARCHIVE_SCHEMA,
        WRITE_WISDOM_SCHEMA, READ_WISDOM_SCHEMA,
        FIND_DUPLICATE_WISDOM_SCHEMA, MERGE_WISDOM_ENTRIES_SCHEMA,
        SEARCH_MEMORY_SCHEMA,
        READ_CONTEXT_TRACKER_SCHEMA, WRITE_CONTEXT_TRACKER_SCHEMA,
        GET_LOG_WINDOW_SCHEMA, WRITE_INSIGHT_REPORT_SCHEMA, READ_RECENT_INSIGHTS_SCHEMA,
        WRITE_BASELINE_PERIOD_SCHEMA, READ_BASELINE_PERIODS_SCHEMA,
        WRITE_RETROSPECTIVE_SCHEMA, GET_BASELINE_CONTEXT_SCHEMA,
    ]
    handlers = {
        "write_log": write_log,
        "read_log": read_log,
        "read_goals": read_goals,
        "write_goals": write_goals,
        "write_config": write_config,
        "write_journal": write_journal,
        "read_journal": read_journal,
        "write_archive": write_archive,
        "read_archive": read_archive,
        "write_wisdom": write_wisdom,
        "read_wisdom": read_wisdom,
        "find_duplicate_wisdom": find_duplicate_wisdom,
        "merge_wisdom_entries": merge_wisdom_entries,
        "search_memory": search_memory,
        "read_context_tracker": read_context_tracker,
        "write_context_tracker": write_context_tracker,
        "get_log_window": get_log_window,
        "write_insight_report": write_insight_report,
        "read_recent_insights": read_recent_insights,
        "write_baseline_period": write_baseline_period,
        "read_baseline_periods": read_baseline_periods,
        "write_retrospective": write_retrospective,
        "get_baseline_context": get_baseline_context,
    }

    return schemas, handlers


def _to_openai_tools(anthropic_schemas: list[dict]) -> list[dict]:
    """Translate Anthropic tool schemas to OpenAI function-calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": s["name"],
                "description": s.get("description", ""),
                "parameters": s["input_schema"],
            },
        }
        for s in anthropic_schemas
    ]


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------

def dispatch_tool(name: str, inputs: dict, handlers: dict) -> str:
    """Execute a tool call and return the result as a string."""
    if name not in handlers:
        return f"Error: unknown tool '{name}'"
    try:
        result = handlers[name](**inputs)
        if isinstance(result, dict):
            return json.dumps(result, indent=2)
        return str(result)
    except Exception as e:
        return f"Error running tool '{name}': {e}"


# ---------------------------------------------------------------------------
# Session runners
# ---------------------------------------------------------------------------

def run_session_anthropic(system_prompt: str, user_input: str,
                           tool_schemas: list[dict], tool_handlers: dict,
                           model: str | None = None) -> str:
    """Agentic loop using the Anthropic API."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set.")

    client = anthropic.Anthropic(api_key=api_key)
    messages = [{"role": "user", "content": user_input}]

    while True:
        response = client.messages.create(
            model=model or ANTHROPIC_MODEL,
            max_tokens=4096,
            system=system_prompt,
            tools=tool_schemas,
            messages=messages,
        )

        text_parts = []
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(block)

        if not tool_calls:
            return "\n".join(text_parts)

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tc in tool_calls:
            result = dispatch_tool(tc.name, tc.input, tool_handlers)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc.id,
                "content": result,
            })

        messages.append({"role": "user", "content": tool_results})


def run_session_openai(system_prompt: str, user_input: str,
                        tool_schemas: list[dict], tool_handlers: dict,
                        model: str | None = None) -> str:
    """Agentic loop using the OpenAI API."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY is not set.")
    return _openai_compat_loop(
        system_prompt, user_input, tool_schemas, tool_handlers,
        api_key=api_key, base_url=None, model=model or OPENAI_MODEL,
    )


def run_session_ollama(system_prompt: str, user_input: str,
                       tool_schemas: list[dict], tool_handlers: dict,
                       model: str | None = None, base_url: str | None = None) -> str:
    """Agentic loop using a local Ollama model via its OpenAI-compatible API."""
    return _openai_compat_loop(
        system_prompt, user_input, tool_schemas, tool_handlers,
        api_key="ollama",
        base_url=base_url or OLLAMA_BASE_URL,
        model=model or OLLAMA_MODEL,
    )


def run_session_gemini(system_prompt: str, user_input: str,
                       tool_schemas: list[dict], tool_handlers: dict,
                       model: str | None = None) -> str:
    """Agentic loop using Gemini via Google's OpenAI-compatible endpoint."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY is not set.")
    return _openai_compat_loop(
        system_prompt, user_input, tool_schemas, tool_handlers,
        api_key=api_key,
        base_url=GEMINI_BASE_URL,
        model=model or GEMINI_MODEL,
    )


def _openai_compat_loop(system_prompt: str, user_input: str,
                         tool_schemas: list[dict], tool_handlers: dict,
                         api_key: str, base_url: str | None, model: str,
                         max_iterations: int = 8) -> str:
    """Shared agentic loop for OpenAI-compatible APIs (OpenAI, Ollama, Gemini)."""
    client = openai.OpenAI(api_key=api_key, base_url=base_url or None)
    oai_tools = _to_openai_tools(tool_schemas)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]

    for _ in range(max_iterations):
        token_kwarg = "max_completion_tokens" if model.startswith("o") else "max_tokens"
        response = client.chat.completions.create(
            model=model,
            **{token_kwarg: 4096},
            tools=oai_tools,
            messages=messages,
        )

        choice = response.choices[0]
        message = choice.message
        messages.append(message)

        # Return on any non-tool-call finish, or if content exists alongside tool calls
        if choice.finish_reason != "tool_calls" or not message.tool_calls:
            return message.content or ""

        for tc in message.tool_calls:
            inputs = json.loads(tc.function.arguments)
            result = dispatch_tool(tc.function.name, inputs, tool_handlers)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    # Fallback if max iterations reached — return whatever content we have
    return messages[-1].get("content") or ""


def run_session(agent_name: str, user_input: str,
                persona: str | None = None, provider: str | None = None) -> str:
    """
    Run a single conversation session.

    Args:
        agent_name: Agent to use (e.g. "time_director", "diarist", "pattern_miner").
        user_input: The user's message.
        persona: Optional dev persona (e.g. "pepys").
        provider: Force a specific provider ("anthropic", "openai", "ollama", "gemini").
                  When None, the router resolves the provider from routing.yaml.
    """
    if persona:
        os.environ["AI_TEST_PERSONA"] = persona
    else:
        os.environ.pop("AI_TEST_PERSONA", None)

    # Resolve provider via router unless explicitly overridden (e.g. CLI --provider flag).
    if provider is None:
        from core.router import resolve_model
        model_cfg = resolve_model(agent_name)
        provider = model_cfg.provider
        model_override = model_cfg.model
        base_url_override = model_cfg.base_url
    else:
        model_override = None
        base_url_override = None

    config = load_config(persona=persona)
    agent = load_agent(agent_name)
    recent = load_recent_context(persona=persona)
    context_block = f"\n\n---\n\n{recent}" if recent else ""
    system_prompt = f"{config}{context_block}\n\n---\n\n## Your Role for This Session\n\n{agent}"
    tool_schemas, tool_handlers = register_tools()

    if provider == "openai":
        return run_session_openai(system_prompt, user_input, tool_schemas, tool_handlers,
                                  model=model_override)
    if provider == "ollama":
        return run_session_ollama(system_prompt, user_input, tool_schemas, tool_handlers,
                                  model=model_override, base_url=base_url_override)
    if provider == "gemini":
        return run_session_gemini(system_prompt, user_input, tool_schemas, tool_handlers,
                                  model=model_override)
    return run_session_anthropic(system_prompt, user_input, tool_schemas, tool_handlers,
                                 model=model_override)


# ---------------------------------------------------------------------------
# Interactive REPL
# ---------------------------------------------------------------------------

def run_interactive(agent_name: str, persona: str | None = None,
                    provider: str = "anthropic") -> None:
    """Run an interactive session in the terminal."""
    label = agent_name.replace('_', ' ').title()
    if persona:
        label += f" [{persona} persona]"
    label += f" [{provider}]"
    print(f"\nLife Manager — {label}")
    print("Type your message and press Enter. Ctrl+C to exit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye.")
            break

        if not user_input:
            continue

        try:
            response = run_session(agent_name, user_input, persona=persona, provider=provider)
            print(f"\nAssistant: {response}\n")
        except Exception as e:
            print(f"\nError: {e}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Personal AI Life Manager — Runtime Orchestrator")
    parser.add_argument("--agent", default="time_director", help="Agent to use (default: time_director)")
    parser.add_argument("--persona", help="Dev persona to load (e.g. pepys, nin, aurelius)")
    parser.add_argument("--provider", default=None, choices=["anthropic", "openai", "ollama", "gemini"],
                        help="Force a model provider (default: auto-routed via routing.yaml)")
    parser.add_argument("--input", help="Single-shot input (skips interactive mode)")
    args = parser.parse_args()

    if args.input:
        result = run_session(args.agent, args.input, persona=args.persona, provider=args.provider)
        print(result)
    else:
        run_interactive(args.agent, persona=args.persona, provider=args.provider)
