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
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import core.trace as _tr

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

# Vertex context cache registry — in-process singleton, keyed by content hash.
# Populated on first request; survives for the process lifetime.
# Caches expire at midnight UTC; rebuild happens automatically on the next miss.
_vertex_native_client: object | None = None
_vertex_cache_registry: dict[str, str] = {}  # sha256[:16] of (model+prompt) → CachedContent.name
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


def load_goals(persona: str | None = None) -> str:
    """Load only goals.yaml — for specialist agents that don't need full config."""
    if persona:
        goals_path = CONFIG_DIR / "personas" / persona / "goals.yaml"
    else:
        goals_path = CONFIG_DIR / "goals.yaml"
    if goals_path.exists():
        content = goals_path.read_text().strip()
        if content:
            return f"## Current Goals\n\n```yaml\n{content}\n```"
    return ""


def _load_coordinator_context(persona: str | None = None) -> str:
    """Pre-load Pattern Miner insights — the one context source not already in the system prompt."""
    persona_str = os.environ.get("AI_TEST_PERSONA") or persona or ""
    try:
        from tools.pattern_miner import read_recent_insights
        insights = read_recent_insights(n=1, persona=persona_str)
        if insights:
            return f"## Pattern Miner Report (most recent)\n{json.dumps(insights[0], indent=2, ensure_ascii=False)}"
    except Exception as e:
        logger.warning(f"[PIPELINE] Failed to pre-load Pattern Miner insights: {e}")
    return ""


def _handle_user_correction(coord_output: str) -> None:
    """Extract USER_CORRECTION from Coordinator output and log it via write_quality_event."""
    import re as _re
    match = _re.search(r'^USER_CORRECTION:\s*(.+)$', coord_output, _re.MULTILINE)
    if match:
        try:
            from tools.logger import write_quality_event
            write_quality_event("USER_CORRECTION", "coordinator", match.group(1).strip())
        except Exception as e:
            logger.warning(f"[PIPELINE] USER_CORRECTION log failed: {e}")


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


def _clean_schema_for_gemini(schema: dict) -> dict:
    """Recursively clean a JSON Schema dict for Gemini API compatibility.
    Gemini rejects empty-string enum values; strip them before passing to FunctionDeclaration.
    """
    result = {}
    for k, v in schema.items():
        if k == "enum" and isinstance(v, list):
            cleaned = [e for e in v if e != ""]
            if cleaned:
                result[k] = cleaned
        elif isinstance(v, dict):
            result[k] = _clean_schema_for_gemini(v)
        else:
            result[k] = v
    return result


def _to_gemini_tools(anthropic_schemas: list[dict]) -> list:
    """Translate Anthropic tool schemas to google-genai types.Tool format."""
    from google.genai import types
    declarations = [
        types.FunctionDeclaration(
            name=s["name"],
            description=s.get("description", ""),
            parameters=_clean_schema_for_gemini(s["input_schema"]),
        )
        for s in anthropic_schemas
    ]
    return [types.Tool(function_declarations=declarations)]


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

def dispatch_tool(name: str, inputs: dict, handlers: dict,
                  _agent_rec=None, _turn_num: int = 1) -> str:
    """Execute a tool call and return the result as a string."""
    if name not in handlers:
        return f"Error: unknown tool '{name}'"
    _trace(f"  [TOOL] {name}")
    t0 = time.monotonic()
    try:
        result = handlers[name](**inputs)
        if isinstance(result, dict):
            result = json.dumps(result, indent=2)
        else:
            result = str(result)
    except Exception as e:
        result = f"Error running tool '{name}': {e}"
    duration_ms = int((time.monotonic() - t0) * 1000)
    rec = _agent_rec or _tr.get_current_agent()
    _tr.record_tool_call(rec, _turn_num, name, inputs, result, duration_ms)
    return result


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
            system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
            tools=tool_schemas,
            messages=messages,
        )

        turn_num += 1
        _in_tok = response.usage.input_tokens
        _out_tok = response.usage.output_tokens
        _cache_write = getattr(response.usage, "cache_creation_input_tokens", 0) or 0
        _cache_read = getattr(response.usage, "cache_read_input_tokens", 0) or 0
        cumulative_input_tokens += _in_tok
        _cache_suffix = f" cache_write={_cache_write} cache_read={_cache_read}" if (_cache_write or _cache_read) else ""
        if cumulative_input_tokens > 8000:
            logger.warning(f"[token_budget] OVER_8K turn={turn_num} cumulative_input={cumulative_input_tokens}{_cache_suffix}")
            _trace(f"[TOKEN] turn={turn_num} input={_in_tok} cumulative={cumulative_input_tokens}{_cache_suffix} ⚠ OVER_8K")
        else:
            logger.info(f"[token_budget] turn={turn_num} cumulative_input={cumulative_input_tokens}{_cache_suffix}")
            _trace(f"[TOKEN] turn={turn_num} input={_in_tok} cumulative={cumulative_input_tokens}{_cache_suffix}")
        _tr.record_turn_tokens(_tr.get_current_agent(), turn_num, _in_tok, _out_tok)

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
                result = dispatch_tool(tc.name, tc.input, tool_handlers, _turn_num=turn_num)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": result,
                })

        if parallel_calls:
            _parent_trace = _tr.get_trace()
            _parent_agent = _tr.get_current_agent()
            def _make_dispatch(name, inputs, handlers, turn):
                def _worker():
                    _tr.set_trace(_parent_trace)
                    _tr._set_current_agent(_parent_agent)
                    return dispatch_tool(name, inputs, handlers, _agent_rec=_parent_agent, _turn_num=turn)
                return _worker
            with ThreadPoolExecutor() as executor:
                future_to_tc = {
                    executor.submit(_make_dispatch(tc.name, tc.input, tool_handlers, turn_num)): tc
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


def _anthropic_stream(
    system_prompt: str, user_input: str,
    tool_schemas: list[dict], tool_handlers: dict,
    model: str | None = None,
    max_iterations: int = 8,
) -> Iterator[str]:
    """Streaming agentic loop for Anthropic.

    Streams every turn. Text from tool-call turns is buffered but not yielded
    (it is internal pre-tool reasoning). Text from the final text turn is yielded
    in real-time as chunks arrive.

    NOTE: Only the Synthesizer uses this function at runtime — it never calls tools,
    so the first turn always goes directly to the yield-and-return path.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set.")

    client = anthropic.Anthropic(api_key=api_key)
    messages: list[dict] = [{"role": "user", "content": user_input}]
    _model = model or ANTHROPIC_MODEL

    for turn_num in range(1, max_iterations + 1):
        _trace(f"[API] anthropic/{_model}  turn={turn_num}  streaming...")
        text_parts: list[str] = []

        with client.messages.stream(
            model=_model,
            max_tokens=4096,
            system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
            tools=tool_schemas,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                text_parts.append(text)
            final = stream.get_final_message()

        if final.usage:
            pts = final.usage.input_tokens
            ots = final.usage.output_tokens
            _cache_write = getattr(final.usage, "cache_creation_input_tokens", 0) or 0
            _cache_read = getattr(final.usage, "cache_read_input_tokens", 0) or 0
            _cache_suffix = f" cache_write={_cache_write} cache_read={_cache_read}" if (_cache_write or _cache_read) else ""
            if pts > 8000:
                logger.warning(f"[token_budget] OVER_8K turn={turn_num} input={pts}{_cache_suffix}")
                _trace(f"[TOKEN] turn={turn_num} input={pts}{_cache_suffix} ⚠ OVER_8K")
            else:
                logger.info(f"[token_budget] turn={turn_num} input={pts}{_cache_suffix}")
                _trace(f"[TOKEN] turn={turn_num} input={pts}{_cache_suffix}")
            _tr.record_turn_tokens(_tr.get_current_agent(), turn_num, pts, ots)

        tool_calls = [block for block in final.content if block.type == "tool_use"]

        if not tool_calls:
            # Final text turn — yield chunks (already accumulated from stream)
            for chunk in text_parts:
                yield chunk
            return

        # Tool-call turn — dispatch and continue; don't yield text_parts
        messages.append({"role": "assistant", "content": final.content})
        tool_results = []
        parallel_calls = [tc for tc in tool_calls if tc.name in _PARALLEL_TOOLS]
        sequential_calls = [tc for tc in tool_calls if tc.name not in _PARALLEL_TOOLS]

        for tc in sequential_calls:
            result = dispatch_tool(tc.name, tc.input, tool_handlers, _turn_num=turn_num)
            tool_results.append({"type": "tool_result", "tool_use_id": tc.id, "content": result})

        if parallel_calls:
            _parent_trace = _tr.get_trace()
            _parent_agent = _tr.get_current_agent()
            def _make_dispatch(name, inputs, handlers, turn):
                def _worker():
                    _tr.set_trace(_parent_trace)
                    _tr._set_current_agent(_parent_agent)
                    return dispatch_tool(name, inputs, handlers, _agent_rec=_parent_agent, _turn_num=turn)
                return _worker
            with ThreadPoolExecutor() as executor:
                future_to_tc = {
                    executor.submit(_make_dispatch(tc.name, tc.input, tool_handlers, turn_num)): tc
                    for tc in parallel_calls
                }
                for future in as_completed(future_to_tc):
                    tc = future_to_tc[future]
                    try:
                        result = future.result()
                    except Exception as e:
                        result = f"Error: {e}"
                    tool_results.append({"type": "tool_result", "tool_use_id": tc.id, "content": result})

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
            eval_tokens = getattr(final_chunk, "eval_count", None) or 0
            if prompt_tokens:
                if prompt_tokens > 8000:
                    logger.warning(f"[token_budget] OVER_8K turn={_turn} input={prompt_tokens}")
                    _trace(f"[TOKEN] turn={_turn} input={prompt_tokens} ⚠ OVER_8K")
                else:
                    logger.info(f"[token_budget] turn={_turn} input={prompt_tokens}")
                    _trace(f"[TOKEN] turn={_turn} input={prompt_tokens}")
            _tr.record_turn_tokens(_tr.get_current_agent(), _turn, prompt_tokens, eval_tokens)

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


def _get_vertex_bearer_token() -> str:
    """Get OAuth2 access token for Vertex AI from Application Default Credentials."""
    import google.auth
    import google.auth.transport.requests
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    credentials.refresh(google.auth.transport.requests.Request())
    return credentials.token


def _vertex_openai_base_url(project: str, location: str) -> str:
    """Return the Vertex AI OpenAI-compatible base URL."""
    if location == "global":
        return f"https://aiplatform.googleapis.com/v1beta1/projects/{project}/locations/global/endpoints/openapi/"
    return f"https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project}/locations/{location}/endpoints/openapi/"


def _vertex_model_name(model: str) -> str:
    """Convert a Gemini model ID to Vertex AI OpenAI-compat format: google/{model}."""
    if model.startswith("models/"):
        model = model[len("models/"):]
    if not model.startswith("google/"):
        model = f"google/{model}"
    return model


def _resolve_gemini_credentials(model: str | None = None) -> tuple[str, str, str]:
    """Return (api_key, base_url, model_name) for the Gemini OpenAI-compat endpoint.

    Used by _openai_compat_stream() for Synthesizer streaming. Routes to Vertex AI
    OpenAI-compat when GOOGLE_CLOUD_PROJECT is set, else AI Studio's OpenAI-compat URL.
    """
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    if project:
        api_key = _get_vertex_bearer_token()
        base_url = _vertex_openai_base_url(project, location)
        model_name = _vertex_model_name(model or GEMINI_PRO_MODEL)
    else:
        api_key = os.environ.get("GEMINI_API_KEY") or ""
        if not api_key:
            raise EnvironmentError("GEMINI_API_KEY or GOOGLE_CLOUD_PROJECT must be set.")
        base_url = GEMINI_BASE_URL
        model_name = model or GEMINI_MODEL
    return api_key, base_url, model_name


def _get_vertex_native_client():
    """Return (or create) the singleton native genai.Client for Vertex AI."""
    global _vertex_native_client
    if _vertex_native_client is None:
        import datetime
        from google import genai
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not project:
            return None
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        _vertex_native_client = genai.Client(vertexai=True, project=project, location=location)
    return _vertex_native_client


def _get_or_create_vertex_cache(client, system_prompt: str, model_name: str) -> str | None:
    """
    Return the Vertex CachedContent name for this system prompt, creating it if needed.

    Expire time: midnight UTC tonight — matches the "once per day" config change cadence.
    Returns None on any failure (model doesn't support caching, content too short, etc.).
    The caller falls back to uncached generation.
    """
    import datetime
    import hashlib
    from google.genai import types

    content_hash = hashlib.sha256(f"{model_name}:{system_prompt}".encode()).hexdigest()[:16]
    if content_hash in _vertex_cache_registry:
        return _vertex_cache_registry[content_hash]

    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        midnight = (now + datetime.timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        cache = client.caches.create(
            model=model_name,
            config=types.CreateCachedContentConfig(
                system_instruction=system_prompt,
                expire_time=midnight,
            ),
        )
        _vertex_cache_registry[content_hash] = cache.name
        _trace(f"[VERTEX_CACHE] created {cache.name} expires={midnight.isoformat()}")
        logger.info(f"[vertex_cache] created model={model_name} hash={content_hash} expires={midnight.isoformat()}")
        return cache.name
    except Exception as e:
        logger.warning(f"[vertex_cache] creation failed ({e}) — running uncached")
        return None


def run_session_gemini(system_prompt: str, user_input: str,
                       tool_schemas: list[dict], tool_handlers: dict,
                       model: str | None = None,
                       history: list[dict] | None = None) -> str:
    """Agentic loop via Vertex AI OpenAI-compat endpoint (or AI Studio OpenAI-compat).

    Uses _openai_compat_loop rather than the native genai SDK to avoid Vertex's
    thought_signature bug: when the model makes parallel function calls, the native SDK
    only assigns a thought_signature to the first Part, and Vertex rejects the multi-turn
    request. The thought_signature workaround lives in _openai_compat_loop.
    """
    api_key, base_url, model_name = _resolve_gemini_credentials(model)
    return _openai_compat_loop(
        system_prompt, user_input, tool_schemas, tool_handlers,
        api_key=api_key, base_url=base_url, model=model_name,
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
        output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
        if input_tokens > 8000:
            logger.warning(f"[token_budget] OVER_8K turn=1 cumulative_input={input_tokens}")
        else:
            logger.info(f"[token_budget] turn=1 cumulative_input={input_tokens}")
        _tr.record_turn_tokens(_tr.get_current_agent(), 1, input_tokens, output_tokens)

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


def run_session_gemini_cached(system_prompt: str, user_input: str,
                               tool_schemas: list[dict], tool_handlers: dict,
                               model: str | None = None,
                               history: list[dict] | None = None) -> str:
    """
    Gemini session with Vertex context caching via the native SDK.

    On the first call for a given system prompt, creates a Vertex CachedContent object
    (expires midnight UTC) and stores the name in _vertex_cache_registry. Subsequent
    calls for the same prompt hit the cache — the system prompt tokens are not re-billed
    or re-processed at full cost.

    Falls back to run_session_gemini (OpenAI-compat, uncached) when:
    - GOOGLE_CLOUD_PROJECT is not set (not on Vertex)
    - Cache creation fails (model doesn't support caching, content below minimum, etc.)
    - Native loop raises (e.g. thought_signature bug on rare parallel-tool escalations)
    """
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        return run_session_gemini(system_prompt, user_input, tool_schemas, tool_handlers, model, history)

    model_name = model or GEMINI_PRO_MODEL
    if model_name.startswith("models/"):
        model_name = model_name[len("models/"):]

    client = _get_vertex_native_client()
    if client is None:
        return run_session_gemini(system_prompt, user_input, tool_schemas, tool_handlers, model, history)

    cached_content_name = _get_or_create_vertex_cache(client, system_prompt, model_name)

    try:
        return _run_gemini_native_loop(
            client, model_name, system_prompt, user_input,
            tool_schemas, tool_handlers,
            history=history,
            cached_content=cached_content_name,
        )
    except Exception as e:
        logger.warning(f"[vertex_cache] native loop failed ({e}) — falling back to compat")
        return run_session_gemini(system_prompt, user_input, tool_schemas, tool_handlers, model, history)


def _run_gemini_native_loop(client, model_name: str,
                             system_prompt: str, user_input: str,
                             tool_schemas: list[dict], tool_handlers: dict,
                             history: list[dict] | None = None,
                             max_iterations: int = 8,
                             cached_content: str | None = None) -> str:
    """
    Agentic loop using the google-genai native SDK.

    Replicates _openai_compat_loop behaviour for the Gemini path: multi-turn
    contents list, tool dispatch (sequential + parallel for _PARALLEL_TOOLS),
    token budget logging, and AI_TRACE markers.

    cached_content: Vertex CachedContent resource name. When provided, the system
    prompt is served from cache — system_instruction is omitted from GenerateContentConfig.
    """
    from google.genai import types

    gemini_tools = _to_gemini_tools(tool_schemas)
    if cached_content:
        config = types.GenerateContentConfig(
            cached_content=cached_content,
            tools=gemini_tools,
            max_output_tokens=4096,
        )
    else:
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=gemini_tools,
            max_output_tokens=4096,
        )

    contents: list = []
    if history:
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))
    contents.append(types.Content(role="user", parts=[types.Part(text=user_input)]))

    cumulative_input_tokens = 0
    result = ""

    for turn_num in range(1, max_iterations + 1):
        _trace(f"[API] gemini-native/{model_name}  turn={turn_num}  waiting...")
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=config,
        )

        if hasattr(response, "usage_metadata") and response.usage_metadata:
            input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
            output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
            cache_read = getattr(response.usage_metadata, "cached_content_token_count", 0) or 0
            cumulative_input_tokens += input_tokens
            _cache_suffix = f" cache_read={cache_read}" if cache_read else ""
            if cumulative_input_tokens > 8000:
                logger.warning(f"[token_budget] OVER_8K turn={turn_num} cumulative_input={cumulative_input_tokens}{_cache_suffix}")
                _trace(f"[TOKEN] turn={turn_num} input={input_tokens} cumulative={cumulative_input_tokens}{_cache_suffix} ⚠ OVER_8K")
            else:
                logger.info(f"[token_budget] turn={turn_num} cumulative_input={cumulative_input_tokens}{_cache_suffix}")
                _trace(f"[TOKEN] turn={turn_num} input={input_tokens} cumulative={cumulative_input_tokens}{_cache_suffix}")
            _tr.record_turn_tokens(_tr.get_current_agent(), turn_num, input_tokens, output_tokens)

        model_content = response.candidates[0].content
        contents.append(model_content)

        function_calls = []
        text_parts = []
        for part in model_content.parts:
            if part.function_call:
                function_calls.append(part.function_call)
            elif part.text:
                text_parts.append(part.text)

        # Capture text even when tool calls are also present — Gemini can emit text
        # and function_call in the same response. Without this, the user-facing text
        # from a "write_context_tracker + respond" turn gets silently discarded.
        if text_parts:
            result = "\n".join(text_parts)

        if not function_calls:
            if history is not None:
                history.append({"role": "user", "content": user_input})
                history.append({"role": "assistant", "content": result})
            return result

        result_parts = []
        parallel_calls = []
        for fc in function_calls:
            if fc.name in _PARALLEL_TOOLS:
                parallel_calls.append(fc)
            else:
                res = dispatch_tool(fc.name, fc.args, tool_handlers)
                result_parts.append(
                    types.Part.from_function_response(name=fc.name, response={"result": res})
                )

        if parallel_calls:
            with ThreadPoolExecutor() as executor:
                future_to_fc = {
                    executor.submit(dispatch_tool, fc.name, fc.args, tool_handlers): fc
                    for fc in parallel_calls
                }
                for future in as_completed(future_to_fc):
                    fc = future_to_fc[future]
                    try:
                        res = future.result()
                    except Exception as e:
                        res = f"Error: {e}"
                    result_parts.append(
                        types.Part.from_function_response(name=fc.name, response={"result": res})
                    )

        contents.append(types.Content(role="user", parts=result_parts))

    if history is not None:
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": result})
    return result


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
    result = ""  # accumulated text; may be set in a tool-call turn if model mixes text+tools

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
            _in_tok = response.usage.prompt_tokens
            _out_tok = getattr(response.usage, "completion_tokens", 0) or 0
            cumulative_input_tokens += _in_tok
            if cumulative_input_tokens > 8000:
                logger.warning(f"[token_budget] OVER_8K turn={turn_num} cumulative_input={cumulative_input_tokens}")
                _trace(f"[TOKEN] turn={turn_num} input={_in_tok} cumulative={cumulative_input_tokens} ⚠ OVER_8K")
            else:
                logger.info(f"[token_budget] turn={turn_num} cumulative_input={cumulative_input_tokens}")
                _trace(f"[TOKEN] turn={turn_num} input={_in_tok} cumulative={cumulative_input_tokens}")
            _tr.record_turn_tokens(_tr.get_current_agent(), turn_num, _in_tok, _out_tok)

        choice = response.choices[0]
        message = choice.message

        # Capture any text content now — Gemini can emit text + tool_call in the same turn.
        # Without this, the user-facing response text gets discarded when the loop continues
        # to execute the tool call, and the model returns nothing on the following turn.
        if message.content:
            result = message.content

        # Return on any non-tool-call finish
        if choice.finish_reason != "tool_calls" or not message.tool_calls:
            messages.append(message)
            if history is not None:
                history.append({"role": "user", "content": user_input_display or user_input})
                history.append({"role": "assistant", "content": result})
            return result

        if len(message.tool_calls) == 1:
            # Single tool call — use Vertex's message as-is (valid thought_signature in extra_content)
            messages.append(message)
            tc = message.tool_calls[0]
            inputs = json.loads(tc.function.arguments)
            result = dispatch_tool(tc.function.name, inputs, tool_handlers, _turn_num=turn_num)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
        else:
            # Vertex bug: parallel tool calls only sign tc0 in extra_content.google.thought_signature.
            # Sending the full multi-call Vertex message back causes a 400 — Vertex validates
            # signatures on its own prior responses and rejects unsigned tc1+.
            #
            # Workaround: execute only tc0 (which has a valid signature). Use model_copy() to
            # create a single-tool-call version of the original Vertex message, preserving all
            # internal SDK metadata (including thought_signature). The model re-calls tc1+ on
            # subsequent turns as individual signed calls.
            # Cost: N parallel calls become N sequential turns. Acceptable for Vertex workaround.
            tc0 = message.tool_calls[0]
            inputs = json.loads(tc0.function.arguments)
            result = dispatch_tool(tc0.function.name, inputs, tool_handlers, _turn_num=turn_num)
            # model_copy preserves all internal SDK state (including Vertex's extra_content with
            # thought_signature) while reducing tool_calls to only tc0 (the signed call).
            messages.append(message.model_copy(update={"tool_calls": [tc0]}))
            messages.append({"role": "tool", "tool_call_id": tc0.id, "content": result})

    # Fallback if max iterations reached — return whatever content we have
    result = messages[-1].get("content") or ""
    if history is not None:
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": result})
    return result


def _openai_compat_stream(
    system_prompt: str, user_input: str,
    tool_schemas: list[dict], tool_handlers: dict,
    api_key: str, base_url: str | None, model: str,
    max_iterations: int = 8,
    extra_body: dict | None = None,
    history: list[dict] | None = None,
    user_input_display: str | None = None,
) -> Iterator[str]:
    """Streaming agentic loop for OpenAI-compatible APIs (Gemini, OpenAI, Ollama).

    Yields text chunks from the final (non-tool-call) response turn in real-time.
    Tool-call intermediate turns run blocking (stream=False) before the streaming turn.

    NOTE: Only the Synthesizer uses this function at runtime — it never calls tools,
    so only the final-turn streaming path is exercised in practice.
    """
    client = openai.OpenAI(api_key=api_key, base_url=base_url or None)
    oai_tools = _to_openai_tools(tool_schemas)
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_input})

    for turn_num in range(1, max_iterations + 1):
        _trace(f"[API] {base_url or 'openai'}/{model}  turn={turn_num}  streaming...")
        token_kwarg = "max_completion_tokens" if model.startswith("o") else "max_tokens"

        stream = client.chat.completions.create(
            model=model,
            **{token_kwarg: 4096},
            tools=oai_tools,
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
            **({"extra_body": extra_body} if extra_body else {}),
        )

        text_parts: list[str] = []
        tool_calls_raw: dict[int, dict] = {}  # delta index → accumulated data
        finish_reason: str | None = None

        for chunk in stream:
            if not chunk.choices:
                # Usage-only trailing chunk (include_usage=True)
                if hasattr(chunk, "usage") and chunk.usage:
                    pts = chunk.usage.prompt_tokens or 0
                    ots = getattr(chunk.usage, "completion_tokens", 0) or 0
                    if pts > 8000:
                        logger.warning(f"[token_budget] OVER_8K turn={turn_num} cumulative_input={pts}")
                        _trace(f"[TOKEN] turn={turn_num} input={pts} ⚠ OVER_8K")
                    else:
                        logger.info(f"[token_budget] turn={turn_num} cumulative_input={pts}")
                        _trace(f"[TOKEN] turn={turn_num} input={pts}")
                    _tr.record_turn_tokens(_tr.get_current_agent(), turn_num, pts, ots)
                continue

            choice = chunk.choices[0]
            if choice.finish_reason:
                finish_reason = choice.finish_reason
            delta = choice.delta

            if delta.content:
                text_parts.append(delta.content)
                yield delta.content

            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in tool_calls_raw:
                        tool_calls_raw[idx] = {"id": "", "name": "", "arguments": ""}
                    if tc_delta.id:
                        tool_calls_raw[idx]["id"] = tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            tool_calls_raw[idx]["name"] = tc_delta.function.name
                        if tc_delta.function.arguments:
                            tool_calls_raw[idx]["arguments"] += tc_delta.function.arguments

        if finish_reason != "tool_calls" or not tool_calls_raw:
            result = "".join(text_parts)
            if history is not None:
                history.append({"role": "user", "content": user_input_display or user_input})
                history.append({"role": "assistant", "content": result})
            return

        # Tool-call turn — reconstruct and dispatch, then continue the loop
        reconstructed = [
            {
                "id": tool_calls_raw[i]["id"],
                "type": "function",
                "function": {
                    "name": tool_calls_raw[i]["name"],
                    "arguments": tool_calls_raw[i]["arguments"],
                },
            }
            for i in sorted(tool_calls_raw)
        ]
        messages.append({
            "role": "assistant",
            "content": "".join(text_parts) or None,
            "tool_calls": reconstructed,
        })

        parallel_calls = []
        for tc in reconstructed:
            name = tc["function"]["name"]
            inputs = json.loads(tc["function"]["arguments"])
            if name in _PARALLEL_TOOLS:
                parallel_calls.append((tc, inputs))
            else:
                result = dispatch_tool(name, inputs, tool_handlers, _turn_num=turn_num)
                messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})

        if parallel_calls:
            _parent_trace = _tr.get_trace()
            _parent_agent = _tr.get_current_agent()
            def _make_dispatch(name, inputs, handlers, turn):
                def _worker():
                    _tr.set_trace(_parent_trace)
                    _tr._set_current_agent(_parent_agent)
                    return dispatch_tool(name, inputs, handlers, _agent_rec=_parent_agent, _turn_num=turn)
                return _worker
            with ThreadPoolExecutor() as executor:
                future_to_tc = {
                    executor.submit(_make_dispatch(tc["function"]["name"], inputs, tool_handlers, turn_num)): tc
                    for tc, inputs in parallel_calls
                }
                for future in as_completed(future_to_tc):
                    tc = future_to_tc[future]
                    try:
                        result = future.result()
                    except Exception as e:
                        result = f"Error: {e}"
                    messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})

    # Fallback: max iterations reached
    if history is not None:
        history.append({"role": "user", "content": user_input_display or user_input})
        history.append({"role": "assistant", "content": ""})


# Head-layer agents receive full config + recent context.
# All other agents (specialists) receive goals.yaml only; context arrives via directive.
_HEAD_LAYER_AGENTS = {"synthesizer"}
_ROUTING_LAYER_AGENTS = {"coordinator"}  # goals + recent context; no constitution/prime_directive


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
    config, no recent logs. Used for token-pressure diagnostics and research_agent.
    """
    from core.router import get_allowed_tools
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
        # No personal config or context — decontextualized / diagnostic mode.
        system_prompt = f"## Your Role for This Session\n\n{agent}"
        augmented_input = user_input
        context_sections = {"agent_file": agent}
    elif agent_name in _HEAD_LAYER_AGENTS:
        # Full config (constitution → prime_directive → mission → goals) + recent context.
        config = load_config(persona=persona)
        recent = load_recent_context(persona=persona)
        system_prompt = f"## Your Role for This Session\n\n{agent}\n\n---\n\n{config}"
        augmented_input = f"[Recent context]\n{recent}\n\n---\n\n{user_input}" if recent else user_input
        context_sections = {"agent_file": agent, "config": config, "recent_context": recent}
    elif agent_name in _ROUTING_LAYER_AGENTS:
        # Routing layer: goals.yaml + recent context. No constitution/prime_directive —
        # values are enforced by the Synthesizer; Coordinator needs domain and context only.
        goals = load_goals(persona=persona)
        recent = load_recent_context(persona=persona)
        system_prompt = (
            f"## Your Role for This Session\n\n{agent}\n\n---\n\n{goals}"
            if goals else f"## Your Role for This Session\n\n{agent}"
        )
        augmented_input = f"[Recent context]\n{recent}\n\n---\n\n{user_input}" if recent else user_input
        context_sections = {"agent_file": agent, "goals": goals, "recent_context": recent}
    else:
        # Specialists: goals.yaml only. Context arrives via the Coordinator directive.
        goals = load_goals(persona=persona)
        system_prompt = (
            f"## Your Role for This Session\n\n{agent}\n\n---\n\n{goals}"
            if goals else f"## Your Role for This Session\n\n{agent}"
        )
        augmented_input = user_input
        context_sections = {"agent_file": agent, "goals": goals}

    tool_schemas, tool_handlers = register_tools()

    # Apply per-agent schema whitelist — only advertise tools the agent can call.
    allowed = get_allowed_tools(agent_name)
    if allowed is not None:  # None = allow all; [] = allow none
        allowed_set = set(allowed)
        tool_schemas = [s for s in tool_schemas if s["name"] in allowed_set]

    _agent_rec = _tr.push_agent(agent_name, provider or "", model_override or "", context_sections)
    try:
        if provider == "openai":
            result = run_session_openai(system_prompt, augmented_input, tool_schemas, tool_handlers,
                                        model=model_override, history=history)
        elif provider == "ollama":
            result = run_session_ollama(system_prompt, augmented_input, tool_schemas, tool_handlers,
                                        model=model_override, base_url=base_url_override,
                                        history=history)
        elif provider == "gemini":
            if agent_name == "research_agent":
                result = run_session_gemini_grounded(system_prompt, augmented_input, model=model_override)
            elif agent_name in (_HEAD_LAYER_AGENTS | _ROUTING_LAYER_AGENTS):
                result = run_session_gemini_cached(system_prompt, augmented_input, tool_schemas,
                                                   tool_handlers, model=model_override, history=history)
            else:
                result = run_session_gemini(system_prompt, augmented_input, tool_schemas, tool_handlers,
                                            model=model_override, history=history)
        else:
            result = run_session_anthropic(system_prompt, augmented_input, tool_schemas, tool_handlers,
                                           model=model_override)
    finally:
        _tr.pop_agent(_agent_rec)
    return result


def _dispatch_from_coordinator(
    coord_output: str,
    persona: str | None = None,
    provider: str | None = None,
) -> dict:
    """
    Parse SPECIALISTS_TO_CALL from Coordinator output and dispatch agents.
    Returns {agent_name: output} for blocking agents.
    Fire-and-forget agents (Diarist) run in background daemon threads.
    """
    import re as _re
    import threading

    match = _re.search(r'SPECIALISTS_TO_CALL:\s*```json\s*(.*?)```', coord_output, _re.DOTALL)
    if not match:
        match = _re.search(r'SPECIALISTS_TO_CALL:\s*(\[.*?\])\s*(?:\n\n|\Z)', coord_output, _re.DOTALL)
    if not match:
        _trace("[PIPELINE] SPECIALISTS_TO_CALL not found — no specialists dispatched")
        return {}

    try:
        specialists: list = json.loads(match.group(1).strip())
    except json.JSONDecodeError as e:
        logger.warning(f"[PIPELINE] SPECIALISTS_TO_CALL JSON parse error: {e}")
        return {}

    outputs: dict = {}
    blocking: list = []

    for spec in specialists:
        agent = spec.get("agent", "")
        directive = spec.get("directive", "")
        mode = spec.get("mode", "")
        is_ff = spec.get("fire_and_forget", False) or agent == "diarist"
        complexity: str | None = mode if mode in ("quick", "deep") else None

        if not agent or not directive:
            continue

        if is_ff:
            def _bg(a: str = agent, d: str = directive, c: str | None = complexity) -> None:
                try:
                    run_session(a, user_input=d, persona=persona, complexity=c)
                except Exception as exc:
                    logger.warning(f"[fire_and_forget] {a} failed: {exc}")
            threading.Thread(target=_bg, daemon=True).start()
            outputs[agent] = f"{agent}: dispatched (async)"
        else:
            blocking.append((agent, directive, complexity))

    if blocking:
        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(_run_single_agent, a, d, persona, provider, None, c): a
                for a, d, c in blocking
            }
            for future in as_completed(futures):
                a = futures[future]
                try:
                    outputs[a] = future.result()
                except Exception as exc:
                    outputs[a] = f"[Subagent error — {exc}]"
                    logger.warning(f"[PIPELINE] {a} failed: {exc}")

    return outputs


def run_pipeline_session(user_input: str,
                         persona: str | None = None,
                         provider: str | None = None) -> str:
    """
    Run the two-pass Coordinator → Synthesizer pipeline.

    Pass 1 (Coordinator): receives pre-loaded context, resolves intent, returns
    SPECIALISTS_TO_CALL directives in a single response (no tool calls needed).
    Python dispatches specialists in parallel from the Coordinator's output.

    Pass 2 (Synthesizer): receives original message + Coordinator routing package
    + specialist outputs, integrates, responds to user.
    """
    _tr.start_request_trace(user_input, persona)
    try:
        # Pre-load Pattern Miner insights (the one context source not in the system prompt).
        coord_context = _load_coordinator_context(persona)
        coord_input = (
            f"{user_input}\n\n---\n\n[Pre-loaded context]\n{coord_context}"
            if coord_context else user_input
        )

        # Pass 1: Coordinator — single-pass routing directive assembly
        _trace("[PIPELINE] coordinator  starting")
        coord_output = _run_single_agent(
            "coordinator", coord_input, persona=persona, provider=provider
        )
        _trace(f"[PIPELINE] coordinator  done  ({len(coord_output)} chars)")
        print(f"\n--- COORD PACKAGE ---\n{coord_output}\n--- END COORD PACKAGE ---\n", file=sys.stderr)  # dev

        # Handle any USER_CORRECTION flag in Coordinator output
        _handle_user_correction(coord_output)

        # Dispatch specialists from Python based on Coordinator's SPECIALISTS_TO_CALL
        _trace("[PIPELINE] dispatching specialists")
        specialist_outputs = _dispatch_from_coordinator(
            coord_output, persona=persona, provider=provider
        )

        # Bundle specialist outputs for Synthesizer (exclude async fire-and-forget)
        spec_text = "\n\n".join(
            f"--- {agent} ---\n{output}"
            for agent, output in specialist_outputs.items()
            if "dispatched (async)" not in output
        )

        # Pass 2: Synthesizer — integration and user-facing response
        synthesizer_input = (
            f"ORIGINAL USER MESSAGE:\n{user_input}\n\n"
            f"COORDINATOR ROUTING PACKAGE:\n{coord_output}"
            + (f"\n\nSPECIALIST OUTPUTS:\n{spec_text}" if spec_text else "")
        )
        _trace("[PIPELINE] synthesizer  starting")
        synth_result = _run_single_agent(
            "synthesizer", synthesizer_input, persona=persona, provider=provider
        )
        _trace(f"[PIPELINE] synthesizer  done  ({len(synth_result)} chars)")
        filtered = filter_output(synth_result, "synthesizer")
    except Exception:
        _tr.set_trace(None)
        raise
    _tr.finish_request_trace(filtered)
    return filtered


def run_pipeline_session_stream(
    user_input: str,
    persona: str | None = None,
    provider: str | None = None,
) -> Iterator[str]:
    """
    Streaming variant of run_pipeline_session().

    Pass 1 (Coordinator): runs blocking, identical to run_pipeline_session().
    Pass 2 (Synthesizer): streams output as text chunks, yielding each in real-time.

    Yields text chunks during generation, then exactly one control token:
      "[DONE]"    — generation complete, filter passed
      "[RETRACT]" — filter caught a confidential term; client should discard received text
    """
    _tr.start_request_trace(user_input, persona)

    # Pass 1: Coordinator — single-pass routing directive assembly (blocking)
    _trace("[PIPELINE] coordinator  starting")
    coord_context = _load_coordinator_context(persona)
    coord_input = (
        f"{user_input}\n\n---\n\n[Pre-loaded context]\n{coord_context}"
        if coord_context else user_input
    )
    coord_output = _run_single_agent("coordinator", coord_input, persona=persona, provider=provider)
    _trace(f"[PIPELINE] coordinator  done  ({len(coord_output)} chars) → dispatching specialists")
    _handle_user_correction(coord_output)
    specialist_outputs = _dispatch_from_coordinator(coord_output, persona=persona, provider=provider)
    spec_text = "\n\n".join(
        f"--- {agent} ---\n{output}"
        for agent, output in specialist_outputs.items()
        if "dispatched (async)" not in output
    )
    _trace("[PIPELINE] synthesizer  streaming")

    # Build Synthesizer input
    synthesizer_input = (
        f"ORIGINAL USER MESSAGE:\n{user_input}\n\n"
        f"COORDINATOR ROUTING PACKAGE:\n{coord_output}"
        + (f"\n\nSPECIALIST OUTPUTS:\n{spec_text}" if spec_text else "")
    )

    # Load Synthesizer prompt — mirrors _run_single_agent internals
    agent_instructions = load_agent("synthesizer")
    config = load_config(persona=persona)
    recent = load_recent_context(persona=persona)
    system_prompt = f"## Your Role for This Session\n\n{agent_instructions}\n\n---\n\n{config}"
    augmented_input = (
        f"[Recent context]\n{recent}\n\n---\n\n{synthesizer_input}" if recent else synthesizer_input
    )
    tool_schemas, tool_handlers = register_tools()

    # Resolve Synthesizer provider/model — explicit provider arg overrides router
    if provider is not None:
        synth_provider = provider
        synth_model: str | None = None
        synth_base_url: str | None = None
    else:
        from core.router import resolve_model
        model_cfg = resolve_model("synthesizer")
        synth_provider = model_cfg.provider
        synth_model = model_cfg.model
        synth_base_url = model_cfg.base_url

    _trace(f"[PIPELINE] synthesizer  provider={synth_provider}  model={synth_model}  streaming")

    # Register synthesizer in the trace (mirrors _run_single_agent)
    _synth_rec = _tr.push_agent(
        "synthesizer", synth_provider, synth_model or "",
        {
            "agent_file": agent_instructions,
            "config": config,
            "recent_context": recent,
        },
    )

    # Dispatch to streaming variant
    # STREAMING NOTE: All four providers stream here. If you add a new provider,
    # add a streaming branch below before routing the Synthesizer to it.
    if synth_provider == "gemini":
        api_key, base_url, model_name = _resolve_gemini_credentials(synth_model)
        gen = _openai_compat_stream(
            system_prompt, augmented_input, tool_schemas, tool_handlers,
            api_key=api_key, base_url=base_url, model=model_name,
        )
    elif synth_provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "")
        gen = _openai_compat_stream(
            system_prompt, augmented_input, tool_schemas, tool_handlers,
            api_key=api_key, base_url=None, model=synth_model or OPENAI_MODEL,
        )
    elif synth_provider == "ollama":
        gen = _openai_compat_stream(
            system_prompt, augmented_input, tool_schemas, tool_handlers,
            api_key="ollama", base_url=synth_base_url or OLLAMA_BASE_URL,
            model=synth_model or OLLAMA_MODEL,
        )
    elif synth_provider == "anthropic":
        gen = _anthropic_stream(
            system_prompt, augmented_input, tool_schemas, tool_handlers,
            model=synth_model or ANTHROPIC_MODEL,
        )
    else:
        raise NotImplementedError(f"No streaming implementation for provider: {synth_provider}")

    # Yield chunks and accumulate for post-stream filter check
    buffer: list[str] = []
    for chunk in gen:
        buffer.append(chunk)
        yield chunk

    complete = "".join(buffer)
    _tr.pop_agent(_synth_rec)
    filtered = filter_output(complete, "synthesizer")
    if filtered != complete:
        yield "[RETRACT]"
    else:
        yield "[DONE]"

    _trace(f"[PIPELINE] synthesizer  done  ({len(complete)} chars)")
    _tr.finish_request_trace(filtered if filtered == complete else "")


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
