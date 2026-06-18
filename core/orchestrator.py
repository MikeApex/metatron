"""
core/orchestrator.py — the runtime brain.

Loads config files (constitution → prime_directive → mission → goals → agent),
builds the system prompt, calls the model API, and handles tool dispatch.

This is the RUNTIME system. It is separate from Claude Code (the development assistant).
CLAUDE.md is for the development context; this file is what runs the life manager.

Usage:
    python core/orchestrator.py                                    # interactive, coordinator agent (pipeline)
    python core/orchestrator.py --agent diarist                    # use a specific agent
    python core/orchestrator.py --provider openai                  # use OpenAI instead of Anthropic
    python core/orchestrator.py --persona pepys                    # load a dev persona
    python core/orchestrator.py --input "how am I doing?"         # single-shot input
"""

import argparse
import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Trace helper — set AI_TRACE=1 to enable terminal progress output; off by default
# ---------------------------------------------------------------------------

def _trace(msg: str) -> None:
    if not os.environ.get("AI_TRACE"):
        return
    from datetime import datetime as _dt
    ts = _dt.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{ts}] {msg}", file=sys.stderr, flush=True)

import anthropic
import openai
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CONFIG_DIR = ROOT / "config"
AGENTS_DIR = CONFIG_DIR / "agents"

ANTHROPIC_MODEL = "claude-sonnet-4-6"
_PARALLEL_TOOLS = {"run_subagent", "run_model_conference"}
OPENAI_MODEL = "o3"
OLLAMA_BASE_URL = "http://localhost:11434/v1"
OLLAMA_MODEL = "qwen3:14b"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_MODEL = "models/gemini-3.1-flash-lite"   # flash default; use GEMINI_PRO_MODEL for full Pro
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

        persona_config_dir = CONFIG_DIR / "personas" / persona
        if persona_config_dir.is_dir():
            tier_files = [
                ("Prime Directive", persona_config_dir / "prime_directive.md"),
                ("Mission", persona_config_dir / "mission.md"),
            ]
            for label, path in tier_files:
                if path.exists():
                    content = path.read_text().strip()
                    if content:
                        sections.append(f"## {label}\n\n{content}")
            goals_path = persona_config_dir / "goals.yaml"
            if goals_path.exists():
                goals_content = goals_path.read_text().strip()
                if goals_content:
                    sections.append(f"## Current Goals\n\n```yaml\n{goals_content}\n```")

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
    from tools.logger import write_log, read_log, WRITE_LOG_SCHEMA, READ_LOG_SCHEMA, write_quality_event, WRITE_QUALITY_EVENT_SCHEMA
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
        create_semantic_anchor, write_aspirational_baseline,
        shuffled_null_score, score_against_anchors,
        CREATE_SEMANTIC_ANCHOR_SCHEMA, WRITE_ASPIRATIONAL_BASELINE_SCHEMA,
        SHUFFLED_NULL_SCORE_SCHEMA, SCORE_AGAINST_ANCHORS_SCHEMA,
    )
    from tools.memory_tool import search_memory, SEARCH_MEMORY_SCHEMA
    from tools.context_tracker import (
        read_context_tracker, write_context_tracker,
        READ_CONTEXT_TRACKER_SCHEMA, WRITE_CONTEXT_TRACKER_SCHEMA,
    )
    from tools.subagent import (
        run_subagent, RUN_SUBAGENT_SCHEMA,
        run_model_conference, RUN_MODEL_CONFERENCE_SCHEMA,
    )
    from tools.crm import (
        write_contact, read_contact, list_contacts, log_interaction, search_contacts,
        WRITE_CONTACT_SCHEMA, READ_CONTACT_SCHEMA, LIST_CONTACTS_SCHEMA,
        LOG_INTERACTION_SCHEMA, SEARCH_CONTACTS_SCHEMA,
    )
    from tools.agent_config import (
        write_agent_config, read_agent_config,
        WRITE_AGENT_CONFIG_SCHEMA, READ_AGENT_CONFIG_SCHEMA,
    )
    from tools.wishes import (
        write_wishes, read_wishes, generate_emergency_card,
        WRITE_WISHES_SCHEMA, READ_WISHES_SCHEMA, GENERATE_EMERGENCY_CARD_SCHEMA,
    )
    from tools.caldav import (
        read_calendar, write_calendar_event,
        READ_CALENDAR_SCHEMA, WRITE_CALENDAR_EVENT_SCHEMA,
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
        CREATE_SEMANTIC_ANCHOR_SCHEMA, WRITE_ASPIRATIONAL_BASELINE_SCHEMA,
        SHUFFLED_NULL_SCORE_SCHEMA, SCORE_AGAINST_ANCHORS_SCHEMA,
        RUN_SUBAGENT_SCHEMA,
        RUN_MODEL_CONFERENCE_SCHEMA,
        WRITE_CONTACT_SCHEMA, READ_CONTACT_SCHEMA, LIST_CONTACTS_SCHEMA,
        LOG_INTERACTION_SCHEMA, SEARCH_CONTACTS_SCHEMA,
        WRITE_AGENT_CONFIG_SCHEMA, READ_AGENT_CONFIG_SCHEMA,
        WRITE_WISHES_SCHEMA, READ_WISHES_SCHEMA, GENERATE_EMERGENCY_CARD_SCHEMA,
        READ_CALENDAR_SCHEMA, WRITE_CALENDAR_EVENT_SCHEMA,
        WRITE_QUALITY_EVENT_SCHEMA,
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
        "create_semantic_anchor": create_semantic_anchor,
        "write_aspirational_baseline": write_aspirational_baseline,
        "shuffled_null_score": shuffled_null_score,
        "score_against_anchors": score_against_anchors,
        "run_subagent": run_subagent,
        "run_model_conference": run_model_conference,
        "write_contact": write_contact,
        "read_contact": read_contact,
        "list_contacts": list_contacts,
        "log_interaction": log_interaction,
        "search_contacts": search_contacts,
        "write_agent_config": write_agent_config,
        "read_agent_config": read_agent_config,
        "write_wishes": write_wishes,
        "read_wishes": read_wishes,
        "generate_emergency_card": generate_emergency_card,
        "read_calendar": read_calendar,
        "write_calendar_event": write_calendar_event,
        "write_quality_event": write_quality_event,
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
# Output filter — strip architecture leaks before returning to user
# ---------------------------------------------------------------------------

# Names that must never appear in user-facing output.
_CONFIDENTIAL_TERMS = [
    # Agent names
    "mental_wellbeing", "physical_health", "work_vocation", "relationships",
    "learning_growth", "recreation_hobbies", "finance", "research_agent",
    "logistics", "time_director", "diarist", "pattern_miner", "goals_interviewer",
    "coordinator", "synthesizer",
    # Tool names
    "run_subagent", "run_model_conference", "write_log", "read_log",
    "write_journal", "read_journal", "write_archive", "read_archive",
    "write_wisdom", "read_wisdom", "search_memory", "write_config",
    "read_goals", "write_goals", "get_log_window", "write_insight_report",
    "read_recent_insights", "write_baseline_period", "read_baseline_periods",
    "write_retrospective", "get_baseline_context", "read_context_tracker",
    "write_context_tracker", "find_duplicate_wisdom", "merge_wisdom_entries",
    "write_contact", "read_contact", "list_contacts", "log_interaction", "search_contacts",
    # Routing / architecture terms
    "cloud_deep", "cloud_fast", "cloud_analytical", "routing.yaml",
    "orchestrator", "run_session", "config/agents",
]

_LEAK_MARKER = "[response filtered]"


def filter_output(text: str, agent_name: str) -> str:
    """
    Scan final user-facing output for leaked architecture terms.
    Logs a warning and returns a safe fallback if any are found.
    Only applied to the Synthesizer (user-facing); Coordinator output is
    internal (context package) and does not need filtering.
    """
    if agent_name != "synthesizer":
        return text

    lower = text.lower()
    for term in _CONFIDENTIAL_TERMS:
        if term.lower() in lower:
            import warnings
            warnings.warn(
                f"[SECURITY] Output filter: '{term}' found in Synthesizer response. "
                f"Response suppressed.",
                stacklevel=2,
            )
            return "I'm here to help you manage your life. What can I help you with today?"

    return text


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------

def dispatch_tool(name: str, inputs: dict, handlers: dict) -> str:
    """Execute a tool call and return the result as a string."""
    if name not in handlers:
        return f"Error: unknown tool '{name}'"
    _trace(f"  [TOOL] {name}")
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
    cumulative_input_tokens = 0
    turn_num = 0
    _model = model or ANTHROPIC_MODEL

    while True:
        _trace(f"[API] anthropic/{_model}  turn={turn_num + 1}  waiting...")
        response = client.messages.create(
            model=_model,
            max_tokens=4096,
            system=system_prompt,
            tools=tool_schemas,
            messages=messages,
        )

        turn_num += 1
        cumulative_input_tokens += response.usage.input_tokens
        if cumulative_input_tokens > 8000:
            logger.warning(f"[token_budget] OVER_8K turn={turn_num} cumulative_input={cumulative_input_tokens}")
            _trace(f"[TOKEN] turn={turn_num} input={response.usage.input_tokens} cumulative={cumulative_input_tokens} ⚠ OVER_8K")
        else:
            logger.info(f"[token_budget] turn={turn_num} cumulative_input={cumulative_input_tokens}")
            _trace(f"[TOKEN] turn={turn_num} input={response.usage.input_tokens} cumulative={cumulative_input_tokens}")

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
        parallel_calls = []
        for tc in tool_calls:
            if tc.name in _PARALLEL_TOOLS:
                parallel_calls.append(tc)
            else:
                result = dispatch_tool(tc.name, tc.input, tool_handlers)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": result,
                })

        if parallel_calls:
            with ThreadPoolExecutor() as executor:
                future_to_tc = {
                    executor.submit(dispatch_tool, tc.name, tc.input, tool_handlers): tc
                    for tc in parallel_calls
                }
                for future in as_completed(future_to_tc):
                    tc = future_to_tc[future]
                    try:
                        result = future.result()
                    except Exception as e:
                        result = f"Error: {e}"
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tc.id,
                        "content": result,
                    })

        messages.append({"role": "user", "content": tool_results})


def run_session_openai(system_prompt: str, user_input: str,
                        tool_schemas: list[dict], tool_handlers: dict,
                        model: str | None = None,
                        history: list[dict] | None = None) -> str:
    """Agentic loop using the OpenAI API."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY is not set.")
    return _openai_compat_loop(
        system_prompt, user_input, tool_schemas, tool_handlers,
        api_key=api_key, base_url=None, model=model or OPENAI_MODEL,
        history=history,
    )


def run_session_ollama(system_prompt: str, user_input: str,
                       tool_schemas: list[dict], tool_handlers: dict,
                       model: str | None = None, base_url: str | None = None,
                       history: list[dict] | None = None) -> str:
    """Agentic loop using the native Ollama Python SDK with streaming output.

    Streams tokens to stdout as they're generated so the terminal never appears
    frozen. Filters <think>...</think> blocks if thinking mode fires despite
    think=False. Returns empty string (output already printed); run_interactive
    checks for this and skips its own print.
    """
    import ollama as _ollama

    _model = model or OLLAMA_MODEL
    oai_tools = _to_openai_tools(tool_schemas)
    ollama_tools = [{"type": "function", "function": t["function"]} for t in oai_tools]

    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    # /no_think suppresses qwen3 extended reasoning; think=False is a belt-and-suspenders
    # API-level flag. Both are needed — think=False alone is unreliable in practice.
    messages.append({"role": "user", "content": f"/no_think {user_input}"})

    full_response = ""

    for _turn in range(1, 9):
        _trace(f"[API] ollama/{_model}  turn={_turn}  waiting...")
        stream = _ollama.chat(
            model=_model,
            messages=messages,
            tools=ollama_tools,
            think=False,
            options={"num_ctx": 16384},
            stream=True,
        )

        content_parts: list[str] = []
        tool_calls: list = []
        header_printed = False
        in_think = False
        think_buf = ""
        final_chunk = None

        for chunk in stream:
            final_chunk = chunk
            msg = chunk.message

            if msg.tool_calls:
                tool_calls.extend(msg.tool_calls)

            if msg.content:
                text = msg.content

                # Filter thinking blocks — buffer until we see the closing tag
                if in_think or "<think>" in text:
                    think_buf += text
                    if not in_think:
                        in_think = True
                    if "</think>" in think_buf:
                        after = think_buf[think_buf.index("</think>") + len("</think>"):]
                        think_buf = ""
                        in_think = False
                        text = after
                    else:
                        continue

                if text:
                    if not header_printed:
                        print("\nAssistant: ", end="", flush=True)
                        header_printed = True
                    print(text, end="", flush=True)
                    content_parts.append(text)

        # Token budget — final chunk carries usage counts in native Ollama SDK
        if final_chunk is not None:
            prompt_tokens = getattr(final_chunk, "prompt_eval_count", None) or 0
            if prompt_tokens:
                if prompt_tokens > 8000:
                    logger.warning(f"[token_budget] OVER_8K turn={_turn} input={prompt_tokens}")
                    _trace(f"[TOKEN] turn={_turn} input={prompt_tokens} ⚠ OVER_8K")
                else:
                    logger.info(f"[token_budget] turn={_turn} input={prompt_tokens}")
                    _trace(f"[TOKEN] turn={_turn} input={prompt_tokens}")

        if header_printed:
            print("\n", flush=True)

        full_content = "".join(content_parts)

        if not tool_calls:
            if history is not None:
                history.append({"role": "user", "content": user_input})
                history.append({"role": "assistant", "content": full_content})
            full_response = full_content
            return ""  # already printed to stdout

        # Tool call turn — show which tool is running, then continue the loop
        messages.append({
            "role": "assistant",
            "content": full_content,
            "tool_calls": [
                {"function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in tool_calls
            ],
        })
        for tc in tool_calls:
            args = tc.function.arguments if isinstance(tc.function.arguments, dict) \
                else json.loads(tc.function.arguments)
            _trace(f"  [TOOL] {tc.function.name}")
            if not os.environ.get("AI_TRACE"):
                print(f"  [calling {tc.function.name}]", flush=True)
            tool_result = dispatch_tool(tc.function.name, args, tool_handlers)
            messages.append({"role": "tool", "content": tool_result})

    if history is not None:
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": full_response})
    return result


def run_session_gemini(system_prompt: str, user_input: str,
                       tool_schemas: list[dict], tool_handlers: dict,
                       model: str | None = None,
                       history: list[dict] | None = None) -> str:
    """Agentic loop using Gemini via Google's OpenAI-compatible endpoint."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY is not set.")
    return _openai_compat_loop(
        system_prompt, user_input, tool_schemas, tool_handlers,
        api_key=api_key,
        base_url=GEMINI_BASE_URL,
        model=model or GEMINI_MODEL,
        history=history,
    )


def run_session_gemini_grounded(system_prompt: str, user_input: str,
                                model: str | None = None) -> str:
    """
    Single-call Gemini session using the native SDK with Google Search grounding.
    Used exclusively for the Research Agent — provides live web search with source
    citations. Not an agentic loop: Research Agent calls no tools of its own.
    Always appends a SOURCES: field to the response.
    """
    from google import genai
    from google.genai import types

    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    if project:
        client = genai.Client(vertexai=True, project=project, location=location)
    else:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError("GEMINI_API_KEY or GOOGLE_CLOUD_PROJECT must be set.")
        client = genai.Client(api_key=api_key)

    model_name = model or GEMINI_PRO_MODEL
    # Vertex AI does not accept the "models/" prefix — strip it if present.
    if project and model_name.startswith("models/"):
        model_name = model_name[len("models/"):]

    _trace(f"[API] gemini-grounded/{model_name}  turn=1  waiting...")
    response = client.models.generate_content(
        model=model_name,
        contents=user_input,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )

    text = response.text or ""

    # Token budget logging (native SDK field)
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
        if input_tokens > 8000:
            logger.warning(f"[token_budget] OVER_8K turn=1 cumulative_input={input_tokens}")
        else:
            logger.info(f"[token_budget] turn=1 cumulative_input={input_tokens}")

    # Extract source URLs from grounding metadata
    sources = []
    if response.candidates:
        gm = getattr(response.candidates[0], "grounding_metadata", None)
        if gm:
            for chunk in getattr(gm, "grounding_chunks", []):
                web = getattr(chunk, "web", None)
                if web and getattr(web, "uri", None):
                    sources.append(web.uri)

    if sources:
        sources_block = "\n".join(f"- {url}" for url in sources)
        text = f"{text}\n\nSOURCES:\n{sources_block}"
    else:
        text = f"{text}\n\nSOURCES: training knowledge"

    return text


def _openai_compat_loop(system_prompt: str, user_input: str,
                         tool_schemas: list[dict], tool_handlers: dict,
                         api_key: str, base_url: str | None, model: str,
                         max_iterations: int = 8,
                         extra_body: dict | None = None,
                         history: list[dict] | None = None,
                         user_input_display: str | None = None) -> str:
    """Shared agentic loop for OpenAI-compatible APIs (OpenAI, Ollama, Gemini).

    user_input_display: the clean version stored in history (omits control tokens
    prepended to user_input for model-specific behaviour, e.g. /no_think).
    """
    client = openai.OpenAI(api_key=api_key, base_url=base_url or None)
    oai_tools = _to_openai_tools(tool_schemas)
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_input})
    cumulative_input_tokens = 0

    for turn_num in range(1, max_iterations + 1):
        _trace(f"[API] {base_url or 'openai'}/{model}  turn={turn_num}  waiting...")
        token_kwarg = "max_completion_tokens" if model.startswith("o") else "max_tokens"
        response = client.chat.completions.create(
            model=model,
            **{token_kwarg: 4096},
            tools=oai_tools,
            messages=messages,
            **({"extra_body": extra_body} if extra_body else {}),
        )

        if response.usage:
            cumulative_input_tokens += response.usage.prompt_tokens
            if cumulative_input_tokens > 8000:
                logger.warning(f"[token_budget] OVER_8K turn={turn_num} cumulative_input={cumulative_input_tokens}")
                _trace(f"[TOKEN] turn={turn_num} input={response.usage.prompt_tokens} cumulative={cumulative_input_tokens} ⚠ OVER_8K")
            else:
                logger.info(f"[token_budget] turn={turn_num} cumulative_input={cumulative_input_tokens}")
                _trace(f"[TOKEN] turn={turn_num} input={response.usage.prompt_tokens} cumulative={cumulative_input_tokens}")

        choice = response.choices[0]
        message = choice.message
        messages.append(message)

        # Return on any non-tool-call finish, or if content exists alongside tool calls
        if choice.finish_reason != "tool_calls" or not message.tool_calls:
            result = message.content or ""
            if history is not None:
                history.append({"role": "user", "content": user_input_display or user_input})
                history.append({"role": "assistant", "content": result})
            return result

        parallel_calls = []
        for tc in message.tool_calls:
            inputs = json.loads(tc.function.arguments)
            if tc.function.name in _PARALLEL_TOOLS:
                parallel_calls.append((tc, inputs))
            else:
                result = dispatch_tool(tc.function.name, inputs, tool_handlers)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

        if parallel_calls:
            with ThreadPoolExecutor() as executor:
                future_to_tc = {
                    executor.submit(dispatch_tool, tc.function.name, inputs, tool_handlers): tc
                    for tc, inputs in parallel_calls
                }
                for future in as_completed(future_to_tc):
                    tc = future_to_tc[future]
                    try:
                        result = future.result()
                    except Exception as e:
                        result = f"Error: {e}"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })

    # Fallback if max iterations reached — return whatever content we have
    result = messages[-1].get("content") or ""
    if history is not None:
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": result})
    return result


def _run_single_agent(agent_name: str, user_input: str,
                      persona: str | None = None, provider: str | None = None,
                      model_override: str | None = None,
                      complexity: str | None = None,
                      history: list[dict] | None = None,
                      bare: bool = False) -> str:
    """
    Run one agent pass and return its raw output (no filter applied).
    Used internally by run_session and run_pipeline_session.

    bare=True: load only the agent instruction file — no constitution, no personal
    config, no recent logs. Used for token-pressure diagnostics.
    """
    base_url_override = None

    if provider is None:
        from core.router import resolve_model
        model_cfg = resolve_model(agent_name, complexity=complexity)
        provider = model_cfg.provider
        if model_override is None:
            model_override = model_cfg.model
        base_url_override = model_cfg.base_url

    _trace(f"[AGENT] {agent_name}  provider={provider}  model={model_override}{'  bare=True' if bare else ''}")
    agent = load_agent(agent_name)
    if bare or agent_name == "research_agent":
        # bare: token-pressure diagnostics — agent file only, no personal context.
        # research_agent: external-facing, never receives personal config.
        system_prompt = f"## Your Role for This Session\n\n{agent}"
    else:
        config = load_config(persona=persona)
        recent = load_recent_context(persona=persona)
        context_block = f"\n\n---\n\n{recent}" if recent else ""
        system_prompt = f"## Your Role for This Session\n\n{agent}\n\n---\n\n{config}{context_block}"
    tool_schemas, tool_handlers = register_tools()

    if provider == "openai":
        return run_session_openai(system_prompt, user_input, tool_schemas, tool_handlers,
                                  model=model_override, history=history)
    elif provider == "ollama":
        return run_session_ollama(system_prompt, user_input, tool_schemas, tool_handlers,
                                  model=model_override, base_url=base_url_override,
                                  history=history)
    elif provider == "gemini":
        if agent_name == "research_agent":
            return run_session_gemini_grounded(system_prompt, user_input, model=model_override)
        return run_session_gemini(system_prompt, user_input, tool_schemas, tool_handlers,
                                  model=model_override, history=history)
    else:
        return run_session_anthropic(system_prompt, user_input, tool_schemas, tool_handlers,
                                     model=model_override)


def run_pipeline_session(user_input: str,
                         persona: str | None = None,
                         provider: str | None = None) -> str:
    """
    Run the two-pass Coordinator → Synthesizer pipeline.

    Pass 1 (Coordinator): loads context, resolves intent, calls specialists,
    returns a structured context package (internal — not shown to user).

    Pass 2 (Synthesizer): receives original message + context package,
    integrates specialist outputs, reasons, responds to user.
    """
    # Pass 1: Coordinator — intake, context loading, specialist fan-out
    _trace("[PIPELINE] coordinator  starting")
    coord_package = _run_single_agent(
        "coordinator", user_input, persona=persona, provider=provider
    )
    _trace(f"[PIPELINE] coordinator  done  ({len(coord_package)} chars) → synthesizer starting")

    # Pass 2: Synthesizer — integration and user-facing response
    synthesizer_input = (
        f"ORIGINAL USER MESSAGE:\n{user_input}\n\n"
        f"COORDINATOR CONTEXT PACKAGE:\n{coord_package}"
    )
    synth_result = _run_single_agent(
        "synthesizer", synthesizer_input, persona=persona, provider=provider
    )
    _trace(f"[PIPELINE] synthesizer  done  ({len(synth_result)} chars)")

    return filter_output(synth_result, "synthesizer")


def run_session(agent_name: str, user_input: str,
                persona: str | None = None, provider: str | None = None,
                model_override: str | None = None,
                complexity: str | None = None,
                history: list[dict] | None = None,
                bare: bool = False) -> str:
    """
    Run a single conversation session.

    When agent_name is "coordinator", runs the full Coordinator → Synthesizer
    pipeline automatically. For all other agents, runs a single agent pass.

    Args:
        agent_name:     Agent to use. "coordinator" triggers the pipeline.
        user_input:     The user's message.
        persona:        Optional dev persona (e.g. "pepys").
        provider:       Force a specific provider ("anthropic", "openai", "ollama", "gemini").
                        When None, the router resolves the provider from routing.yaml.
        model_override: Explicit model ID, overrides both router and provider default.
        history:        Mutable list of prior turn dicts. Updated in-place each turn.
    """
    if persona:
        os.environ["AI_TEST_PERSONA"] = persona
    else:
        os.environ.pop("AI_TEST_PERSONA", None)

    # Coordinator triggers the two-pass pipeline (stateless — no history threading).
    if agent_name == "coordinator":
        return run_pipeline_session(user_input, persona=persona, provider=provider)

    result = _run_single_agent(
        agent_name, user_input,
        persona=persona, provider=provider,
        model_override=model_override, complexity=complexity,
        history=history, bare=bare,
    )
    return filter_output(result, agent_name)


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

    history: list[dict] = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye.")
            break

        if not user_input:
            continue

        try:
            response = run_session(agent_name, user_input, persona=persona, provider=provider,
                                   history=history)
            if response:  # empty means already printed by streaming
                print(f"\nAssistant: {response}\n")
        except Exception as e:
            print(f"\nError: {e}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Personal AI Life Manager — Runtime Orchestrator")
    parser.add_argument("--agent", default="coordinator", help="Agent to use (default: coordinator → runs full pipeline)")
    parser.add_argument("--persona", help="Dev persona to load (e.g. pepys, nin, aurelius)")
    parser.add_argument("--provider", default=None, choices=["anthropic", "openai", "ollama", "gemini"],
                        help="Force a model provider (default: auto-routed via routing.yaml)")
    parser.add_argument("--input", help="Single-shot input (skips interactive mode)")
    parser.add_argument("--bare", action="store_true",
                        help="Load agent file only — skip constitution/config/logs (token-pressure diagnostics)")
    args = parser.parse_args()

    if args.input:
        result = run_session(args.agent, args.input, persona=args.persona, provider=args.provider,
                             bare=args.bare)
        print(result)
    else:
        run_interactive(args.agent, persona=args.persona, provider=args.provider)
