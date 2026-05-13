"""
core/orchestrator.py — the runtime brain.

Loads config files (constitution → prime_directive → mission → goals → agent),
builds the system prompt, calls the Claude API, and handles tool dispatch.

This is the RUNTIME system. It is separate from Claude Code (the development assistant).
CLAUDE.md is for the development context; this file is what runs the life manager.

Usage:
    python core/orchestrator.py                        # interactive session, time_director agent
    python core/orchestrator.py --agent diarist        # use a specific agent
    python core/orchestrator.py --input "how am I doing?" # single-shot input
"""

import argparse
import json
import os
import sys
from pathlib import Path

import anthropic

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent.parent
CONFIG_DIR = ROOT / "config"
AGENTS_DIR = CONFIG_DIR / "agents"


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def load_config() -> str:
    """
    Build the system prompt from the four-tier config hierarchy.
    Loads: constitution → prime_directive → mission → goals.
    Returns a single string for use as the Claude API system prompt.
    """
    sections = []

    files = [
        ("Tool Constitution", CONFIG_DIR / "constitution.md"),
        ("Prime Directive", CONFIG_DIR / "prime_directive.md"),
        ("Mission", CONFIG_DIR / "mission.md"),
    ]

    for label, path in files:
        if path.exists():
            content = path.read_text().strip()
            if content:
                sections.append(f"## {label}\n\n{content}")

    # Goals — YAML, read as raw text for now (structured parsing in Phase 1+)
    goals_path = CONFIG_DIR / "goals.yaml"
    if goals_path.exists():
        goals_content = goals_path.read_text().strip()
        if goals_content:
            sections.append(f"## Current Goals\n\n```yaml\n{goals_content}\n```")

    return "\n\n---\n\n".join(sections)


def load_agent(name: str) -> str:
    """
    Load a sub-agent instruction file from config/agents/{name}.md.
    Returns the file contents as a string.
    """
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
        schemas: List of tool schemas for the Claude API `tools` parameter.
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


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------

def dispatch_tool(name: str, inputs: dict, handlers: dict) -> str:
    """
    Execute a tool call returned by the Claude API.

    Args:
        name: Tool name as returned in the tool_use block.
        inputs: Tool input arguments.
        handlers: Dict of tool name → function.

    Returns:
        Tool result as a string.
    """
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
# Session runner
# ---------------------------------------------------------------------------

def run_session(agent_name: str, user_input: str) -> str:
    """
    Run a single conversation session with the given agent and user input.

    Loads config + agent instructions, calls the Claude API, handles any
    tool_use blocks, and returns the final text response.

    Args:
        agent_name: Name of the agent to use (e.g. "time_director").
        user_input: The user's message.

    Returns:
        The assistant's final text response.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY environment variable is not set.")

    client = anthropic.Anthropic(api_key=api_key)

    # Build system prompt: config hierarchy + agent instructions
    config = load_config()
    agent = load_agent(agent_name)
    system_prompt = f"{config}\n\n---\n\n## Your Role for This Session\n\n{agent}"

    # Register tools
    tool_schemas, tool_handlers = register_tools()

    # Initial message
    messages = [{"role": "user", "content": user_input}]

    # Agentic loop — keeps running until the model stops calling tools
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system_prompt,
            tools=tool_schemas,
            messages=messages,
        )

        # Collect text from this response turn
        text_parts = []
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(block)

        # If no tool calls, we're done
        if not tool_calls:
            return "\n".join(text_parts)

        # Append assistant turn to message history
        messages.append({"role": "assistant", "content": response.content})

        # Execute each tool call and collect results
        tool_results = []
        for tool_call in tool_calls:
            result = dispatch_tool(tool_call.name, tool_call.input, tool_handlers)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_call.id,
                "content": result,
            })

        # Append tool results as user turn
        messages.append({"role": "user", "content": tool_results})

        # Loop continues — model will process tool results and respond


# ---------------------------------------------------------------------------
# Interactive REPL
# ---------------------------------------------------------------------------

def run_interactive(agent_name: str) -> None:
    """Run an interactive session in the terminal."""
    print(f"\nLife Manager — {agent_name.replace('_', ' ').title()}")
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
            response = run_session(agent_name, user_input)
            print(f"\nAssistant: {response}\n")
        except Exception as e:
            print(f"\nError: {e}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Personal AI Life Manager — Runtime Orchestrator")
    parser.add_argument("--agent", default="time_director", help="Agent to use (default: time_director)")
    parser.add_argument("--input", help="Single-shot input (skips interactive mode)")
    args = parser.parse_args()

    if args.input:
        result = run_session(args.agent, args.input)
        print(result)
    else:
        run_interactive(args.agent)
