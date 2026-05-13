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
OPENAI_MODEL = "gpt-4o"


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

    schemas = [WRITE_LOG_SCHEMA, READ_LOG_SCHEMA, READ_GOALS_SCHEMA, WRITE_GOALS_SCHEMA]
    handlers = {
        "write_log": write_log,
        "read_log": read_log,
        "read_goals": read_goals,
        "write_goals": write_goals,
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
                           tool_schemas: list[dict], tool_handlers: dict) -> str:
    """Agentic loop using the Anthropic API."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set.")

    client = anthropic.Anthropic(api_key=api_key)
    messages = [{"role": "user", "content": user_input}]

    while True:
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
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
                        tool_schemas: list[dict], tool_handlers: dict) -> str:
    """Agentic loop using the OpenAI API (also compatible with Ollama)."""
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")  # set to Ollama endpoint when switching
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY is not set.")

    client = openai.OpenAI(api_key=api_key, base_url=base_url or None)
    oai_tools = _to_openai_tools(tool_schemas)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]

    while True:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            max_tokens=4096,
            tools=oai_tools,
            messages=messages,
        )

        choice = response.choices[0]
        message = choice.message
        messages.append(message)

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


def run_session(agent_name: str, user_input: str,
                persona: str | None = None, provider: str = "anthropic") -> str:
    """
    Run a single conversation session.

    Args:
        agent_name: Agent to use (e.g. "time_director").
        user_input: The user's message.
        persona: Optional dev persona (e.g. "pepys").
        provider: "anthropic" or "openai".
    """
    config = load_config(persona=persona)
    agent = load_agent(agent_name)
    system_prompt = f"{config}\n\n---\n\n## Your Role for This Session\n\n{agent}"
    tool_schemas, tool_handlers = register_tools()

    if provider == "openai":
        return run_session_openai(system_prompt, user_input, tool_schemas, tool_handlers)
    return run_session_anthropic(system_prompt, user_input, tool_schemas, tool_handlers)


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
    parser.add_argument("--provider", default="anthropic", choices=["anthropic", "openai"],
                        help="Model provider (default: anthropic)")
    parser.add_argument("--input", help="Single-shot input (skips interactive mode)")
    args = parser.parse_args()

    if args.input:
        result = run_session(args.agent, args.input, persona=args.persona, provider=args.provider)
        print(result)
    else:
        run_interactive(args.agent, persona=args.persona, provider=args.provider)
