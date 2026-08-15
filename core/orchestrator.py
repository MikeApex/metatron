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
    python core/orchestrator.py --persona mike                     # interactive REPL
    python core/orchestrator.py --persona mike --input "how am I doing?"   # single-shot
"""

import argparse
import inspect
import json
import logging
import os
import sys
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from functools import lru_cache
from pathlib import Path

# Must precede any `core.*` / `tools.*` import. Running `python core/orchestrator.py`
# puts core/ on sys.path[0], not the project root, so `import core.trace` fails
# without this. core/server.py has always done the same thing before its imports.
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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

CONFIG_DIR = ROOT / "config"
AGENTS_DIR = CONFIG_DIR / "agents"

from contextlib import nullcontext
from core.persona import (
    PersonaError,
    current_persona,
    persona_config_dir,
    persona_data_dir,
    persona_md,
    persona_scope,
    resolve_persona,
)

ANTHROPIC_MODEL = "claude-sonnet-5"
_PARALLEL_TOOLS = {"run_subagent", "run_model_conference"}

# Vertex context cache registry — in-process singleton, keyed by content hash.
# Populated on first request; survives for the process lifetime.
# Caches expire at midnight UTC; rebuild happens automatically on the next miss.
_vertex_native_client: object | None = None
# sha256[:16] of (model+prompt+tools) → (CachedContent.name, expire_time).
# The expiry is stored because Vertex deletes the cache at that moment; without
# it the registry keeps handing out a dead name and every call 404s.
_vertex_cache_registry: dict[str, tuple[str, "datetime.datetime"]] = {}
OPENAI_MODEL = "o3"
OLLAMA_BASE_URL = "http://localhost:11434/v1"
OLLAMA_MODEL = "qwen3:14b"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_MODEL = "models/gemini-3.1-flash-lite"   # flash default; use GEMINI_PRO_MODEL for full Pro
GEMINI_PRO_MODEL = "models/gemini-3.1-pro-preview"


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def load_profile(persona: str | None = None) -> str:
    """
    Load config/profile.yaml (or persona override) and format as a system prompt section.
    Sensitive-tier: injected only into agents that run on local/sensitive-routed models.
    Returns empty string if file is missing or all fields are null.
    """
    import yaml as _yaml

    # No root fallback. A persona without a profile gets no profile — inheriting
    # another persona's name, city and timezone is worse than having none, and
    # that fallback was silently telling every persona it was the real user.
    profile_path = persona_config_dir(persona) / "profile.yaml"

    if not profile_path.exists():
        return ""

    try:
        profile = _yaml.safe_load(profile_path.read_text()) or {}
    except Exception:
        return ""

    lines = []

    if profile.get("name"):
        lines.append(f"Name: {profile['name']}")

    loc = profile.get("location") or {}
    loc_parts = [v for v in [loc.get("city"), loc.get("country")] if v]
    if loc_parts:
        lines.append(f"Home location: {', '.join(loc_parts)}")
    if loc.get("timezone"):
        lines.append(f"Timezone: {loc['timezone']}")

    age = profile.get("age")
    birth_year = profile.get("birth_year")
    if age:
        lines.append(f"Age: {age}")
    elif birth_year:
        from datetime import date as _date
        computed_age = _date.today().year - int(birth_year)
        lines.append(f"Age: ~{computed_age} (born {birth_year})")

    if profile.get("occupation"):
        lines.append(f"Occupation: {profile['occupation']}")
    if profile.get("household"):
        lines.append(f"Household: {profile['household']}")
    if profile.get("health_notes"):
        lines.append(f"Health notes: {profile['health_notes']}")

    for item in (profile.get("other") or []):
        if item:
            lines.append(str(item))

    if not lines:
        return ""

    return "## User Profile\n\n" + "\n".join(lines)


def _spend_gate() -> str | None:
    """
    Check the runaway guards before starting a session.

    Returns a user-facing message if the session must be refused, else None.
    A refusal is returned as ordinary text rather than raised: the user should
    see a plain explanation, not a stack trace, and the surrounding machinery
    should not treat a deliberate stop as a crash.
    """
    try:
        from core.spend_guard import SpendLimitExceeded, check_before_session, note_session_start
        try:
            check_before_session()
        except SpendLimitExceeded as exc:
            logger.warning(f"[spend_guard] session refused: {exc}")
            return (
                "I've paused myself for now — I've hit the daily usage limit set to "
                "catch runaway activity. Nothing is broken, and this resets tomorrow.\n\n"
                f"Detail: {exc}"
            )
        note_session_start()
    except Exception as exc:
        # Fail open — the guard must never be the reason a session cannot run.
        logger.warning(f"[spend_guard] gate error, allowing session: {exc}")
    return None


def _titled(label: str, content: str) -> str:
    """
    Wrap content in a '## {label}' heading, unless it already opens with one.

    The Goals Interviewer writes prime_directive.md and mission.md through
    write_config(), which stores the model's text verbatim — and the model
    includes its own '## Prime Directive' heading. Without this check the
    system prompt carries the heading twice with an empty section between.
    """
    first = content.lstrip().splitlines()[0].strip().lower() if content.strip() else ""
    if first == f"## {label}".lower():
        return content
    return f"## {label}\n\n{content}"


def load_config(persona: str | None = None) -> str:
    """
    Build the system prompt from the four-tier config hierarchy for one persona.
    Loads: constitution -> identity -> prime_directive -> mission -> goals -> profile.

    Tier 0 (the Constitution) is shared by every persona. Tiers 1-3 and the
    profile are per-persona, under config/personas/{persona}/. There is no
    root-level fallback: a session always belongs to exactly one persona.
    """
    resolved = resolve_persona(persona)
    sections = []

    constitution_path = CONFIG_DIR / "constitution.md"
    if constitution_path.exists():
        content = constitution_path.read_text().strip()
        if content:
            sections.append(f"## Tool Constitution\n\n{content}")

    identity_path = persona_md(resolved)
    if not identity_path.exists():
        raise FileNotFoundError(f"Persona not found: {identity_path}")
    sections.append(f"## User\n\n{identity_path.read_text().strip()}")

    config_dir = persona_config_dir(resolved)
    for label, filename in (
        ("Prime Directive", "prime_directive.md"),
        ("Mission", "mission.md"),
    ):
        path = config_dir / filename
        if path.exists():
            content = path.read_text().strip()
            if content:
                sections.append(_titled(label, content))

    goals_path = config_dir / "goals.yaml"
    if goals_path.exists():
        goals_content = goals_path.read_text().strip()
        if goals_content:
            sections.append(f"## Current Goals\n\n```yaml\n{goals_content}\n```")

    # Optional, per-persona: how to handle a request to change the tool itself.
    # Present only for personas whose user is also building Metatron — absent
    # for everyone else, so no other persona's behaviour changes.
    self_dev_path = config_dir / "self_development.md"
    if self_dev_path.exists():
        self_dev = self_dev_path.read_text().strip()
        if self_dev:
            sections.append(_titled("Working on Metatron", self_dev))

    # Optional, per-persona: a structured evening reflection ritual — the virtue
    # review, its delivery format, and what gets logged. The content belongs to
    # one user, so it must not sit in config/agents/synthesizer.md, which every
    # persona loads (.claude/rules/agent-files.md § One Home Per Rule Class).
    # Moving it here in 2026-08 was token-neutral for the persona that has one
    # and a saving for every persona that does not.
    evening_ritual_path = config_dir / "evening_ritual.md"
    if evening_ritual_path.exists():
        evening_ritual = evening_ritual_path.read_text().strip()
        if evening_ritual:
            sections.append(_titled("Evening ritual", evening_ritual))

    profile = load_profile(persona=resolved)
    if profile:
        sections.append(profile)

    return "\n\n---\n\n".join(sections)


def load_goals(persona: str | None = None) -> str:
    """Load only goals.yaml — for specialist agents that don't need full config."""
    goals_path = persona_config_dir(persona) / "goals.yaml"
    if goals_path.exists():
        content = goals_path.read_text().strip()
        if content:
            return f"## Current Goals\n\n```yaml\n{content}\n```"
    return ""


def _load_coordinator_context(persona: str | None = None) -> str:
    """Pre-load Pattern Miner insights — the one context source not already in the system prompt."""
    persona_str = resolve_persona(persona)
    try:
        from tools.pattern_miner import read_recent_insights
        insights = read_recent_insights(n=1, persona=persona_str)
        if insights:
            return f"## Pattern Miner Report (most recent)\n{json.dumps(insights[0], indent=2, ensure_ascii=False)}"
    except PersonaError:
        raise
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
    Load the last N days of logs, context tracker, and ambient world context
    (date/time, weather, news) into a string for injection into the system prompt.

    Returns empty string if no recent data exists.
    """
    import json as _json
    from datetime import date, timedelta
    from pathlib import Path

    data_dir = persona_data_dir(persona)
    logs_dir = data_dir / "logs"
    tracker_path = data_dir / "context.json"

    sections = []

    # Ambient world context — date/time always live; weather/news from last refresh
    try:
        from tools.ambient import load_ambient_context
        ambient = load_ambient_context()
        if ambient:
            sections.append(ambient)
    except PersonaError:
        raise
    except Exception as e:
        logger.warning(f"[context] ambient load failed: {e}")

    # Context tracker (mid-term: open threads, patterns, follow-ups)
    if tracker_path.exists():
        try:
            tracker = _json.loads(tracker_path.read_text())
            lines = [f"## Session Context (last session: {tracker.get('last_session', 'unknown')})"]
            if tracker.get("open_threads"):
                # Entries are {"text": ..., "added": <ISO date or None>} as of the
                # open_threads timestamp change — tolerate old bare-string entries too,
                # in case this reads a tracker file this session itself hasn't migrated yet.
                thread_texts = [
                    t.get("text", "") if isinstance(t, dict) else str(t)
                    for t in tracker["open_threads"]
                ]
                lines.append("**Open threads:** " + " | ".join(thread_texts))
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

    # Open obligations and passed-event candidates. In the context rather than behind a
    # tool because the whole point of the obligation store is that something outstanding
    # cannot be missed for want of the session thinking to look it up — the 2026-08-07
    # failure ("I thought I already told you that was handled") was a closure that left no
    # trace, and a tool the model has to remember to call reproduces the same class of gap.
    #
    # This lands in `augmented_input`, not the system prompt, at all three call sites — so
    # it costs input tokens but does not disturb the Vertex prefix cache.
    #
    # Both blocks return "" when empty, so a persona with nothing outstanding pays nothing.
    for _block_source in ("tools.obligations", "tools.calendar_reconcile"):
        try:
            import importlib
            block = importlib.import_module(_block_source).context_block(persona)
            if block:
                sections.append(block)
        except PersonaError:
            raise
        except Exception as e:
            logger.warning(f"[context] {_block_source} block failed: {e}")

    return "\n\n---\n\n".join(sections)


def clock_line() -> str:
    """
    Authoritative system-clock line for agents that get no recent context.

    Returns "" on failure — a missing clock degrades a specialist's dated writes,
    but raising here would take down the whole exchange.
    """
    try:
        from tools.ambient import current_clock_line
        return current_clock_line()
    except PersonaError:
        raise
    except Exception as e:
        logger.warning(f"[context] clock line failed: {e}")
        return ""


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
    from tools.goals import (
        read_goals, write_goals, update_goal,
        READ_GOALS_SCHEMA, WRITE_GOALS_SCHEMA, UPDATE_GOAL_SCHEMA,
    )
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
    from tools.persona import write_persona, WRITE_PERSONA_SCHEMA
    from tools.profile import (
        write_profile, WRITE_PROFILE_SCHEMA,
        read_profile, READ_PROFILE_SCHEMA,
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
    from tools.tone import get_tone_shape, GET_TONE_SHAPE_SCHEMA
    from tools.agent_config import (
        write_agent_config, read_agent_config,
        WRITE_AGENT_CONFIG_SCHEMA, READ_AGENT_CONFIG_SCHEMA,
    )
    from tools.wishes import (
        write_wishes, read_wishes, generate_emergency_card,
        WRITE_WISHES_SCHEMA, READ_WISHES_SCHEMA, GENERATE_EMERGENCY_CARD_SCHEMA,
    )
    from tools.caldav import (
        read_calendar, write_calendar_event, update_calendar_event, delete_calendar_event,
        READ_CALENDAR_SCHEMA, WRITE_CALENDAR_EVENT_SCHEMA,
        UPDATE_CALENDAR_EVENT_SCHEMA, DELETE_CALENDAR_EVENT_SCHEMA,
    )
    from tools.scheduling import check_calendar_conflicts, CHECK_CALENDAR_CONFLICTS_SCHEMA
    from tools.ambient import (
        get_weather, get_environmental_snapshot,
        GET_WEATHER_SCHEMA, GET_ENVIRONMENTAL_SNAPSHOT_SCHEMA,
    )
    from tools.pollen import get_pollen_forecast, GET_POLLEN_FORECAST_SCHEMA
    from tools.tfl_status import get_tfl_status, GET_TFL_STATUS_SCHEMA
    from tools.flights import get_flight_status, GET_FLIGHT_STATUS_SCHEMA
    from tools.routing import get_travel_time, GET_TRAVEL_TIME_SCHEMA
    from tools.regional_transit import get_regional_transit_info, GET_REGIONAL_TRANSIT_INFO_SCHEMA
    from tools.schedule import (
        write_schedule, list_schedules, delete_schedule,
        WRITE_SCHEDULE_SCHEMA, LIST_SCHEDULES_SCHEMA, DELETE_SCHEDULE_SCHEMA,
    )
    # Commitments that outlive a session. Data, not scheduler jobs — tools/schedule.py
    # § "Why obligations are not jobs" settled that, and tools/obligations.py is the store
    # that position assumed and nobody had written.
    from tools.obligations import (
        open_obligation, close_obligation, reopen_obligation, list_obligations,
        OPEN_OBLIGATION_SCHEMA, CLOSE_OBLIGATION_SCHEMA,
        REOPEN_OBLIGATION_SCHEMA, LIST_OBLIGATIONS_SCHEMA,
    )
    # External-content tools. Both return their payload wrapped by tools/untrusted.py —
    # a web page and an email body are written by strangers.
    from tools.web import fetch_url, FETCH_URL_SCHEMA
    from tools.mail import read_email, send_email, READ_EMAIL_SCHEMA, SEND_EMAIL_SCHEMA

    schemas = [
        WRITE_LOG_SCHEMA, READ_LOG_SCHEMA,
        READ_GOALS_SCHEMA, WRITE_GOALS_SCHEMA, UPDATE_GOAL_SCHEMA,
        WRITE_CONFIG_SCHEMA,
        WRITE_JOURNAL_SCHEMA, READ_JOURNAL_SCHEMA,
        WRITE_ARCHIVE_SCHEMA, READ_ARCHIVE_SCHEMA,
        WRITE_WISDOM_SCHEMA, READ_WISDOM_SCHEMA,
        FIND_DUPLICATE_WISDOM_SCHEMA, MERGE_WISDOM_ENTRIES_SCHEMA,
        SEARCH_MEMORY_SCHEMA,
        READ_CONTEXT_TRACKER_SCHEMA, WRITE_CONTEXT_TRACKER_SCHEMA,
        WRITE_PERSONA_SCHEMA,
        WRITE_PROFILE_SCHEMA,
        READ_PROFILE_SCHEMA,
        GET_LOG_WINDOW_SCHEMA, WRITE_INSIGHT_REPORT_SCHEMA, READ_RECENT_INSIGHTS_SCHEMA,
        WRITE_BASELINE_PERIOD_SCHEMA, READ_BASELINE_PERIODS_SCHEMA,
        WRITE_RETROSPECTIVE_SCHEMA, GET_BASELINE_CONTEXT_SCHEMA,
        CREATE_SEMANTIC_ANCHOR_SCHEMA, WRITE_ASPIRATIONAL_BASELINE_SCHEMA,
        SHUFFLED_NULL_SCORE_SCHEMA, SCORE_AGAINST_ANCHORS_SCHEMA,
        RUN_SUBAGENT_SCHEMA,
        RUN_MODEL_CONFERENCE_SCHEMA,
        WRITE_CONTACT_SCHEMA, READ_CONTACT_SCHEMA, LIST_CONTACTS_SCHEMA,
        LOG_INTERACTION_SCHEMA, SEARCH_CONTACTS_SCHEMA,
        GET_TONE_SHAPE_SCHEMA,
        WRITE_AGENT_CONFIG_SCHEMA, READ_AGENT_CONFIG_SCHEMA,
        WRITE_WISHES_SCHEMA, READ_WISHES_SCHEMA, GENERATE_EMERGENCY_CARD_SCHEMA,
        OPEN_OBLIGATION_SCHEMA, CLOSE_OBLIGATION_SCHEMA,
        REOPEN_OBLIGATION_SCHEMA, LIST_OBLIGATIONS_SCHEMA,
        READ_CALENDAR_SCHEMA, WRITE_CALENDAR_EVENT_SCHEMA,
        UPDATE_CALENDAR_EVENT_SCHEMA, DELETE_CALENDAR_EVENT_SCHEMA,
        CHECK_CALENDAR_CONFLICTS_SCHEMA,
        GET_WEATHER_SCHEMA, GET_ENVIRONMENTAL_SNAPSHOT_SCHEMA,
        GET_POLLEN_FORECAST_SCHEMA,
        GET_TFL_STATUS_SCHEMA,
        GET_FLIGHT_STATUS_SCHEMA,
        GET_TRAVEL_TIME_SCHEMA,
        GET_REGIONAL_TRANSIT_INFO_SCHEMA,
        WRITE_SCHEDULE_SCHEMA, LIST_SCHEDULES_SCHEMA, DELETE_SCHEDULE_SCHEMA,
        WRITE_QUALITY_EVENT_SCHEMA,
        FETCH_URL_SCHEMA, READ_EMAIL_SCHEMA, SEND_EMAIL_SCHEMA,
    ]
    handlers = {
        "write_log": write_log,
        "read_log": read_log,
        "read_goals": read_goals,
        "write_goals": write_goals,
        "update_goal": update_goal,
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
        "get_tone_shape": get_tone_shape,
        "write_agent_config": write_agent_config,
        "read_agent_config": read_agent_config,
        "fetch_url": fetch_url,
        "read_email": read_email,
        "send_email": send_email,
        "write_wishes": write_wishes,
        "read_wishes": read_wishes,
        "generate_emergency_card": generate_emergency_card,
        "read_calendar": read_calendar,
        "write_calendar_event": write_calendar_event,
        "update_calendar_event": update_calendar_event,
        "delete_calendar_event": delete_calendar_event,
        "check_calendar_conflicts": check_calendar_conflicts,
        "get_weather": get_weather,
        "get_environmental_snapshot": get_environmental_snapshot,
        "get_pollen_forecast": get_pollen_forecast,
        "get_tfl_status": get_tfl_status,
        "get_flight_status": get_flight_status,
        "get_travel_time": get_travel_time,
        "get_regional_transit_info": get_regional_transit_info,
        "write_schedule": write_schedule,
        "list_schedules": list_schedules,
        "delete_schedule": delete_schedule,
        "open_obligation": open_obligation,
        "close_obligation": close_obligation,
        "reopen_obligation": reopen_obligation,
        "list_obligations": list_obligations,
        "write_quality_event": write_quality_event,
        "write_persona": write_persona,
        "write_profile": write_profile,
        "read_profile": read_profile,
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
    """Translate Anthropic tool schemas to google-genai types.Tool format.
    Returns [] when no schemas are given — callers must omit the tools param in that case."""
    if not anthropic_schemas:
        return []
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

import re as _re

# Code identifiers: contain underscores, slashes, or are otherwise impossible
# in natural prose. Always flag on substring match.
_ALWAYS_CONFIDENTIAL = [
    # Agent names (underscore form)
    "mental_wellbeing", "physical_health", "work_vocation",
    "learning_growth", "recreation_hobbies", "research_agent",
    "time_director", "pattern_miner", "goals_interviewer",
    # Tool names
    "run_subagent", "run_model_conference", "write_log", "read_log",
    "write_journal", "read_journal", "write_archive", "read_archive",
    "write_wisdom", "read_wisdom", "search_memory", "write_config",
    "read_goals", "write_goals", "update_goal", "write_schedule",
    "list_schedules", "delete_schedule", "get_log_window", "write_insight_report",
    "read_recent_insights", "write_baseline_period", "read_baseline_periods",
    "write_retrospective", "get_baseline_context", "read_context_tracker",
    "write_context_tracker", "find_duplicate_wisdom", "merge_wisdom_entries",
    "write_contact", "read_contact", "list_contacts", "log_interaction",
    "search_contacts", "write_persona", "get_tone_shape", "tone_profiler",
    # Routing / architecture terms
    "cloud_deep", "cloud_fast", "cloud_analytical", "routing.yaml",
    "run_session", "config/agents",
]

# Common English words that are also internal names. Only flagged when the
# surrounding sentence contains architecture vocabulary — indicating an actual
# leak rather than ordinary usage (e.g. "daily logistics", "music synthesizer").
_CONTEXT_SENSITIVE = [
    "relationships", "finance", "logistics", "diarist",
    "coordinator", "synthesizer", "orchestrator",
]

# Vocabulary that, when appearing in the same sentence as a context-sensitive
# term, signals an architecture leak rather than ordinary prose.
#
# Widened 2026-08-08 (B2 "Output filter upgrade") beyond the original six terms.
# It now also covers first-person capability narration ("I called…", "I routed
# this to…") and the vocabulary of internals (handler, schema, endpoint, under
# the hood), because the loose/spaced term forms below are gated on this and a
# paraphrase rarely says "sub-agent" outright. Kept deliberately narrow on the
# ambiguous words: `prompt` only as `system prompt`, `call` only as `tool call`
# / `function call` — a bare `\bprompt\b` or `\bcall\b` fires on ordinary
# sentences like "that prompted a good conversation" or "a call with your
# sister", which is the FILTER-CLEAN corpus in tests/run_b1_redteam.py.
_ARCH_VOCAB_RE = _re.compile(
    r'\b(agent|specialist|sub-?agent|subagent|routing|routed|pipeline|module|'
    r'dispatch(?:ed|es)?|orchestrat\w+|handler|schema|endpoint|api|'
    r'allow-?list|white-?list|permission set|'
    r'tool\s*call|function\s*call|system\s*prompt|instruction\s*file|'
    r'back-?end|under\s+the\s+hood|behind\s+the\s+scenes|'
    r'i\s+(?:called|invoked|dispatched|routed|delegated|queried|ran)'
    r')\b',
    _re.IGNORECASE,
)

# Characters used purely to break up a term so a substring match misses it, and
# which carry no meaning in user-facing prose: zero-width spaces/joiners, soft
# hyphen, BOM, word joiner.
#
# Written as escapes rather than literals: a character class of literal
# zero-width characters is invisible in the source too, and the next person to
# edit this line cannot see what they are deleting.
_INVISIBLE_RE = _re.compile(
    '['
    '\u00ad'                  # soft hyphen
    '\u200b-\u200f'           # zero-width space/non-joiner/joiner, LTR/RTL marks
    '\u2028\u2029'            # line/paragraph separators
    '\u2060\u2061\u2062\u2063'  # word joiner, invisible operators
    '\ufeff'                  # BOM / zero-width no-break space
    ']'
)

# Joiners used when rebuilding a term as a regex. Both run against text that has
# already been lowercased, so `[^0-9a-z\s]` covers `_ - . · * | \ / +` and the
# unicode dashes without needing to enumerate them.
#
#   TIGHT — punctuation-joined or squashed: write_config, write-config,
#           write.config, write**config, writeconfig. Never a plain space, so
#           ordinary English ("your mental wellbeing") cannot match.
#   LOOSE — any non-alphanumeric run, including spaces: "write config",
#           "mental wellbeing". Ambiguous with real prose, so gated on
#           _ARCH_VOCAB_RE appearing in the same sentence.
_TIGHT_JOINER = r'(?:[ \t]*[^0-9a-z\s]{1,4}[ \t]*|)'
_LOOSE_JOINER = r'[^0-9a-z]{0,6}'


@lru_cache(maxsize=512)
def _term_regex(term: str, joiner: str) -> _re.Pattern:
    """
    Build an obfuscation-tolerant matcher for one confidential term.

    Cached: filter_output() rebuilds ~110 of these per response otherwise, on
    the user-facing path.

    The term is split into alphanumeric tokens and rejoined with `joiner`, so a
    single list entry covers every separator variant an attacker (or a model
    trying to be helpful about a term it has been told not to say) might use.
    Boundaries are lookarounds on alphanumerics rather than `\\b`, because `\\b`
    does not fire between `_` and a letter — `x_write_config` would slip past.
    """
    tokens = [t for t in _re.split(r'[^0-9a-z]+', term.lower()) if t]
    if not tokens:
        return _re.compile(r'(?!)')          # matches nothing
    body = joiner.join(_re.escape(t) for t in tokens)
    return _re.compile(rf'(?<![0-9a-z]){body}(?![0-9a-z])')


# Paraphrase detection: architecture narration that names nothing on either
# list. "I passed this to a specialist that handles your health" leaks the
# multi-agent structure without using a single confidential identifier, and the
# term-based tiers above are blind to it by construction.
#
# Every pattern here is written to need an internal-narration frame, not just a
# suggestive noun. `specialist` alone must stay legal — Physical Health telling
# the user to see a specialist about their knee is exactly the advice the tool
# exists to give.
_ARCH_NARRATION_RES = [_re.compile(p, _re.IGNORECASE) for p in [
    # System-prompt / instruction-file disclosure
    r'\bmy\s+(?:system\s*)?(?:prompt|instructions?|instruction file|'
    r'configuration|config file|agent file|guidelines document)\b',
    r'\b(?:the|my)\s+system\s*prompt\b',
    r'\bi\s+(?:was|am|have been)\s+(?:instructed|configured|programmed|'
    r'set\s*up|designed)\s+to\s+(?:respond|reply|answer|say|never say|'
    r'avoid|refuse|route|call|use)\b',
    r'\b(?:first|opening|last)\s+(?:sentence|line|paragraph)\s+of\s+my\s+'
    r'(?:instructions|prompt)\b',

    # Multi-agent structure described in the first person
    # Bare `agent` is deliberately absent from the noun list: "I sent your
    # reply to the agent" is a legitimate sentence about an estate agent. It is
    # still covered by tier 3, where `agent` is architecture vocabulary that
    # gates a context-sensitive term in the same sentence.
    r'\bi\s+(?:dispatched|routed|delegated|forwarded|handed|passed|sent|escalated)\s+'
    r'(?:\w+\s+){0,4}?(?:to|through)\s+(?:a|an|the|my|another)\s+'
    r'(?:sub-?agent|specialist|module|model|assistant)\b',
    r'\bi\s+(?:consulted|asked|queried)\s+(?:a|an|another|a different|a second)\s+'
    r'(?:model|ai|assistant|agent|specialist module)\b',
    r'\b(?:sub-?agents?|specialist\s+(?:agents?|modules?)|agent\s+(?:files?|modules?)|'
    r'routing\s+(?:layer|table|config\w*)|orchestration\s+layer|the\s+orchestrator)\b',
    r'\b(?:\d+|twelve|fourteen|several|multiple)\s+(?:specialist|specialised|specialized)\s+'
    r'(?:agents?|modules?|sub-?agents?)\b',

    # Tool/capability inventory. The lookahead keeps "I use tools like
    # journalling" — a normal thing to say about the user's own methods — legal.
    r'\bi\s+(?:have|use|used|call|called|invoked|ran|run|have access to)\s+'
    r'(?:a|an|the|my|several|multiple|various|these|the following)?\s*'
    r'(?:tool|function|api|sub-?agent|specialist module)s?\b(?!\s+(?:like|such as))',
    r'\b(?:my|the)\s+(?:available\s+)?tool(?:s|\s*set|\s*list|kit of functions)\b',
    r'\bthe\s+tools\s+(?:i|available to me)\b',

    # Model / provider disclosure
    r'\bi\s*(?:\'m|\s+am)?\s+(?:running on|powered by|built on|based on)\s+'
    r'(?:a|an|the)?\s*(?:gpt|gemini|claude|llama|qwen|mistral|sonnet|haiku|opus|'
    r'large language model|llm|language model)\b',
    r'\b(?:the\s+)?underlying\s+(?:model|llm|language model|system|architecture)\b',
    r'\bwhich\s+(?:model|llm)\s+i\s+(?:use|run on|am)\b',
]]


def _sentence_bounds(text: str, pos: int) -> tuple[int, int]:
    """Return (start, end) indices of the sentence containing position pos."""
    start = max(text.rfind('.', 0, pos), text.rfind('\n', 0, pos)) + 1
    end_dot = text.find('.', pos)
    end_nl = text.find('\n', pos)
    end = min(
        end_dot if end_dot >= 0 else len(text),
        end_nl if end_nl >= 0 else len(text),
    )
    return start, end if end > start else len(text)


_CANNED_FALLBACK = "I'm here to help you manage your life. What can I help you with today?"


def _normalise_for_filter(text: str) -> str:
    """
    Lowercase and strip invisible characters before matching.

    `w​rite_config` with a zero-width space after the w is the same leak as
    `write_config`, and reads identically to the user — it must not be the
    difference between suppressed and delivered.
    """
    return _INVISIBLE_RE.sub("", text).lower()


def filter_output(text: str, agent_name: str) -> str:
    """
    Scan final user-facing output for leaked architecture terms.
    Logs a warning and returns a safe fallback if any are found.
    Only applied to the Synthesizer (user-facing); Coordinator output is
    internal (context package) and does not need filtering.

    Four-tier check (tiers 1 and 3 rebuilt 2026-08-08, roadmap B2 "Output
    filter upgrade — move from keyword matching to regex+semantic"):

    1. _ALWAYS_CONFIDENTIAL, tight form — the code identifier however it is
       punctuated or squashed: `write_config`, `write-config`, `write.config`,
       `write**config`, `writeconfig`, and any of those with zero-width
       characters spliced in. Always suppressed.
    2. Architecture narration (_ARCH_NARRATION_RES) — paraphrases that leak the
       structure without naming anything: "I passed this to a specialist that
       handles your health", "my system prompt says", "I'm running on Gemini".
       The pre-upgrade filter was blind to all of these; a model told not to
       say `run_subagent` will happily describe what it does instead.
       Always suppressed.
    3. _ALWAYS_CONFIDENTIAL, loose form — the same identifiers spaced out
       ("write config", "run subagent"), plus _CONTEXT_SENSITIVE. Both are
       ambiguous with ordinary English, so both are suppressed only when
       architecture vocabulary appears in the same sentence. "Your mental
       wellbeing has improved" stays legal; "the mental wellbeing agent said"
       does not.

    Detection runs on a normalised copy; the original text is what is returned
    when it passes.

    **Known limits, so nobody over-trusts this.** Tier 2 is pattern-based, not
    a model: a paraphrase phrased outside these frames passes. Intra-token
    spacing (`w r i t e _ c o n f i g`) is not caught — the joiner sits between
    tokens, not inside them — because a matcher loose enough to catch it fires
    on ordinary spaced prose. This filter is the last backstop, not the
    control: the agent confidentiality instructions are.

    Deliberately does NOT exempt terms the user already typed themselves —
    that would let a direct probing question ("what does write_config do?")
    disable its own backstop. See B1 red-team category "Direct tool inquiry"
    in the roadmap. The resulting false positive (Exchange 027, 2026-06-26 —
    user mentioned "write_config" in a complaint, got the canned fallback
    instead of a real reply) is unchanged by this upgrade and remains an
    accepted risk: fixing it needs the user's own turn passed in for
    comparison, which is a call-signature change across three call sites, not
    a matching change. Filed rather than folded in here.
    """
    if agent_name != "synthesizer":
        return text

    import warnings

    def _suppress(reason: str) -> str:
        warnings.warn(
            f"[SECURITY] Output filter: {reason} in Synthesizer response. "
            f"Response suppressed.",
            stacklevel=3,
        )
        return _CANNED_FALLBACK

    norm = _normalise_for_filter(text)

    # Tier 1 — identifiers, punctuation-obfuscation tolerant.
    for term in _ALWAYS_CONFIDENTIAL:
        m = _term_regex(term, _TIGHT_JOINER).search(norm)
        if m:
            return _suppress(f"'{term}' (matched as {m.group(0)!r}) found")

    # Tier 2 — architecture narration, no confidential identifier required.
    for pattern in _ARCH_NARRATION_RES:
        m = pattern.search(norm)
        if m:
            return _suppress(f"architecture narration {m.group(0)!r} found")

    # Tier 3 — spaced identifiers and common-word agent names, sentence-gated.
    for term in list(_ALWAYS_CONFIDENTIAL) + list(_CONTEXT_SENSITIVE):
        rx = _term_regex(term, _LOOSE_JOINER)
        for m in rx.finditer(norm):
            start, end = _sentence_bounds(norm, m.start())
            if _ARCH_VOCAB_RE.search(norm[start:end]):
                return _suppress(
                    f"'{term}' (matched as {m.group(0)!r}) in architecture context found"
                )

    return text


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------

_CONTEXT_OPEN = "[CONTEXT]"
_CONTEXT_CLOSE = "[/CONTEXT]"


# Keys the salvage path knows how to rescue individually. **Add to this whenever a
# key is added to the [CONTEXT] block** — a key missing here is not an error, it is
# silently unsalvageable, which is the exact failure this repair layer exists to end.
# `clinical_threads` arrived from a parallel session on 2026-08-08; it is the one
# with a safety cost if dropped.
_CONTEXT_KEYS = ("open_threads", "patterns", "follow_ups", "held_items",
                 "clinical_threads", "dev_request")


def _strip_fences(raw: str) -> str:
    """Drop a ```json fence and any prose either side of the outermost JSON object."""
    raw = _re.sub(r'^\s*```(?:json|JSON)?\s*', '', raw.strip())
    raw = _re.sub(r'```\s*$', '', raw).strip()
    first, last = raw.find('{'), raw.rfind('}')
    if first >= 0 and last > first:
        return raw[first:last + 1]
    if first >= 0:
        return raw[first:]          # truncated mid-object — the balancer handles it
    return raw


def _balance(raw: str) -> str:
    """
    Close a truncated JSON object and drop mismatched closers.

    A block cut off by a token limit ends mid-array or mid-string. Closing an
    unterminated string first, then the open brackets in reverse order, recovers
    everything written before the cut instead of discarding all of it.

    A closer that does not match the open bracket is dropped rather than kept:
    `{"open_threads": ["a",}` — an array closed with a brace — is otherwise
    unrecoverable, and appending the right closers on top of the wrong one just
    moves the syntax error. Valid JSON never contains a mismatched closer, so
    this cannot damage a block that would have parsed anyway.
    """
    in_string = escaped = False
    stack: list[str] = []
    kept: list[str] = []
    for ch in raw:
        if in_string:
            kept.append(ch)
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in '{[':
            stack.append('}' if ch == '{' else ']')
        elif ch in '}]':
            if stack and stack[-1] == ch:
                stack.pop()
            else:
                continue          # wrong closer — drop it
        kept.append(ch)
    out = ''.join(kept)
    if in_string:
        out += '"'
    # A trailing comma or dangling `"key":` becomes invalid the moment we close
    # the bracket, so drop it before appending.
    out = _re.sub(r'(,|:\s*)\s*$', '', out)
    return out + ''.join(reversed(stack))


def _repair_context_json(raw: str) -> tuple[dict | None, str]:
    """
    Parse a [CONTEXT] payload, repairing the malformations models actually emit.

    Returns (parsed_or_None, how) where `how` names the step that succeeded —
    "clean" when no repair was needed, so the caller can log a repair without
    logging every ordinary block.

    Each step is additive and ordered cheapest-first. Nothing here guesses at
    *content*: every repair is structural (fences, truncation, trailing commas,
    quote style). A block that is structurally sound but semantically wrong is
    passed through to persist_context_block, which validates keys itself.
    """
    candidates: list[tuple[str, str]] = [("clean", raw.strip())]

    fenced = _strip_fences(raw)
    if fenced != raw.strip():
        candidates.append(("fences/prose stripped", fenced))

    no_trailing_commas = _re.sub(r',\s*([}\]])', r'\1', fenced)
    if no_trailing_commas != fenced:
        candidates.append(("trailing commas removed", no_trailing_commas))

    smart = (no_trailing_commas
             .replace('“', '"').replace('”', '"')
             .replace('‘', "'").replace('’', "'"))
    if smart != no_trailing_commas:
        candidates.append(("smart quotes normalised", smart))

    balanced = _balance(smart)
    if balanced != smart:
        candidates.append(("truncation closed", balanced))

    # Single-quoted JSON (a Python repr, essentially). Only attempted when there
    # is not a single double quote in the block — otherwise this corrupts a
    # legitimate apostrophe inside a string value, which is common in prose.
    if '"' not in balanced and "'" in balanced:
        candidates.append(("single quotes converted", balanced.replace("'", '"')))

    for how, candidate in candidates:
        if not candidate:
            continue
        try:
            # strict=False permits raw control characters (a literal \n typed into a
            # JSON string value, rather than an escaped \\n) instead of rejecting the
            # whole block — observed live 2026-08-02, where a single stray newline
            # silently dropped both the context-tracker update and the dev_request
            # in it.
            parsed = json.loads(candidate, strict=False)
        except Exception:
            continue
        if isinstance(parsed, dict):
            return parsed, how

    # Last resort: salvage the keys that are individually well-formed. A single
    # broken value in `patterns` should not cost the three open threads next to
    # it — partial recovery beats a total drop, and this is the case the
    # ladder above cannot reach because the object never parses as a whole.
    salvaged: dict = {}
    for key in _CONTEXT_KEYS:
        m = _re.search(rf'"{key}"\s*:\s*([\[{{"])', balanced)
        if not m:
            continue
        value = _extract_json_value(balanced, m.start(1))
        if value is None:
            continue
        try:
            salvaged[key] = json.loads(_balance(value), strict=False)
        except Exception:
            continue
    if salvaged:
        return salvaged, f"partial salvage ({', '.join(sorted(salvaged))})"

    return None, "unrecoverable"


def _extract_json_value(text: str, start: int) -> str | None:
    """Return the JSON value beginning at `start` (an opening `[`, `{` or `"`)."""
    opener = text[start]
    if opener == '"':
        i, escaped = start + 1, False
        while i < len(text):
            if escaped:
                escaped = False
            elif text[i] == '\\':
                escaped = True
            elif text[i] == '"':
                return text[start:i + 1]
            i += 1
        return text[start:]
    closer = ']' if opener == '[' else '}'
    depth, in_string, escaped = 0, False, False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return text[start:]


def _record_unparsed_context(raw: str, exc_detail: str) -> None:
    """
    Persist a [CONTEXT] block that survived neither parsing nor repair.

    There is no re-emit path from here: split_context_block runs after the
    Synthesizer's turn has completed, on the user-facing request, and asking the
    model again would cost a second Pro turn of latency on every malformation to
    fix a tracker update the user never sees. So the block is made *recoverable*
    instead of retried — written to the quality-event stream that already
    reaches DEV_BACKLOG.md via the existing sync, with the raw text attached.
    A dropped update then shows up as a backlog item with the evidence in it,
    rather than as a warning in a log nobody reads.
    """
    try:
        from tools.logger import write_quality_event as _wqe
        _wqe(
            event_type="CONTEXT_BLOCK_UNPARSED",
            source_agent="synthesizer",
            detail=(f"[CONTEXT] block dropped — no repair succeeded ({exc_detail}). "
                    f"Raw block (first 1500 chars): {raw.strip()[:1500]}"),
            session_id=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        )
    except PersonaError:
        raise
    except Exception as exc:
        logger.warning(f"[context_block] could not record unparsed block: {exc}")


def split_context_block(complete: str) -> tuple[str, dict | None]:
    """
    Split a Synthesizer response into visible text and its [CONTEXT] block.

    The Synthesizer appends [CONTEXT]{json}[/CONTEXT] after its visible answer
    instead of spending a tool-call turn on write_context_tracker. That block is
    internal — it must never reach a user, a push notification, or an API caller.

    A malformed block used to be a warning and a silent drop: the context-tracker
    update, and any dev_request riding along in it, were gone with no retry and
    no record. `strict=False` (2026-08-02) fixed the one malformation observed
    live — a literal newline inside a string value — but only that one. This now
    runs a structural repair ladder (`_repair_context_json`), falls back to
    salvaging whichever keys are individually well-formed, and if even that
    fails records the raw block as a quality event so the update is recoverable
    rather than lost.

    Returns (visible_text, parsed_context_or_None).
    """
    if _CONTEXT_OPEN not in complete:
        return complete, None
    visible = complete[:complete.index(_CONTEXT_OPEN)].strip()
    raw = complete[complete.index(_CONTEXT_OPEN) + len(_CONTEXT_OPEN):]
    if _CONTEXT_CLOSE in raw:
        raw = raw[:raw.index(_CONTEXT_CLOSE)]

    parsed, how = _repair_context_json(raw)
    if parsed is not None:
        if how != "clean":
            logger.warning(f"[context_block] repaired malformed block via {how}")
            _trace(f"[PIPELINE] context_block  repaired  ({how})")
        return visible, parsed

    logger.warning(f"[context_block] parse failed after repair — raw: {raw[:200]}")
    _record_unparsed_context(raw, "all repair steps exhausted")
    return visible, None


def persist_context_block(ctx: dict | None) -> None:
    """Write a parsed [CONTEXT] block to the tracker. Best-effort; never blocks a response."""
    if not ctx:
        return
    try:
        from tools.context_tracker import write_context_tracker as _write_ct
        _write_ct(
            open_threads=ctx.get("open_threads", []),
            patterns=ctx.get("patterns", []),
            follow_ups=ctx.get("follow_ups", []),
            held_items=ctx.get("held_items"),
            clinical_threads=ctx.get("clinical_threads"),
        )
        _trace("[PIPELINE] context_tracker  written  (inline block)")
    except PersonaError:
        raise
    except Exception as exc:
        logger.warning(f"[context_block] write failed: {exc}")

    _persist_dev_request(ctx.get("dev_request"))


_DEV_REQUEST_TYPES = {"SELF_APPLIED", "INSTRUCTION_CHANGE_REQUEST", "FEATURE_REQUEST"}

# Its own logger at INFO, because the module logger is pinned to WARNING (line 41)
# and _trace() is a no-op unless AI_TRACE is set — which the service never sets.
# Without this, the one confirmation that a user's change request was captured
# is invisible in production. Records propagate to the root handler, which has
# no level of its own, so they reach journalctl.
_dev_request_log = logging.getLogger("metatron.dev_request")
_dev_request_log.setLevel(logging.INFO)


def _persist_dev_request(req: dict | None) -> None:
    """
    Record a user-reported change request from the inline [CONTEXT] block.

    Mike is both the user and the builder, so requests to change the tool arrive
    mid-conversation. They ride along in the block the Synthesizer already emits
    rather than costing a second Pro turn on a tool call. Written to the same
    quality_events stream the self-improvement protocol already uses; the
    development-side reader filters on these event types.

    Separate try block from the context-tracker write above: neither failure
    should cost the other, and neither should ever affect the user's response.
    """
    if not isinstance(req, dict):
        return
    try:
        req_type = str(req.get("type", "")).strip().upper()
        detail = str(req.get("detail", "")).strip()
        if req_type not in _DEV_REQUEST_TYPES or not detail:
            logger.warning(f"[dev_request] discarded — type={req_type!r} detail={detail[:80]!r}")
            return
        from tools.logger import write_quality_event as _wqe
        _wqe(
            event_type=req_type,
            source_agent="synthesizer",
            detail=detail,
            session_id=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        )
        _dev_request_log.info(f"[dev_request] recorded {req_type}: {detail[:200]}")
    except PersonaError:
        raise
    except Exception as exc:
        logger.warning(f"[dev_request] write failed: {exc}")


def _signature_hint(fn) -> str:
    """Render a tool's real parameter list, for correcting a mis-shaped call."""
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return ""
    required, optional = [], []
    for p in sig.parameters.values():
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            continue
        (optional if p.default is not p.empty else required).append(p.name)
    parts = []
    if required:
        parts.append("required: " + ", ".join(required))
    if optional:
        parts.append("optional: " + ", ".join(optional))
    return f"{getattr(fn, '__name__', 'tool')}({'; '.join(parts)})" if parts else ""


# Per-agent tool permissions.
#
# Two things were true before this existed, and both were invisible:
#   1. The `allowed_tools` whitelist filtered the schemas an agent was SHOWN,
#      but `dispatch_tool` looked up handlers unfiltered — so an agent that
#      knew a tool's name from its instruction file could call anything, and
#      did. SEQ 021: Logistics called write_agent_config three times without
#      ever being advertised it.
#   2. Because the call simply succeeded, there was no signal anywhere that an
#      agent wanted a capability it had not been granted.
#
# (2) is the more valuable of the two. The agent instruction files are a
# specification of intended capability written ahead of the tools, so an
# attempted call is a design signal, not a bug. Enforcing silently would
# destroy that signal; removing the references from the files would destroy it
# just as thoroughly.
#
# So this starts in WARN mode: record the attempt, let it through. Denials land
# in the dev backlog as evidence of demonstrated need, and the mode flips to
# "enforce" once the log has been reviewed — before integrations open the
# indirect-injection surface (roadmap B2 gates E1).
TOOL_PERMISSION_MODE = os.environ.get("METATRON_TOOL_PERMISSIONS", "warn").lower()

# One backlog entry per (agent, tool). Budget alerts taught us what happens
# when a repeating condition writes a record every time it is observed.
_reported_denials: set[tuple[str, str]] = set()


def _record_tool_denial(agent: str, name: str, inputs: dict) -> None:
    """
    Record that an agent reached for a tool it was not granted.

    Feeds the dev backlog via the quality-event stream, so a capability the
    agents actually want surfaces as a development item rather than dying as a
    log line nobody reads.
    """
    key = (agent, name)
    if key in _reported_denials:
        return
    _reported_denials.add(key)

    logger.warning(
        f"[tool_permissions] {agent} called '{name}' without a grant "
        f"(mode={TOOL_PERMISSION_MODE})"
    )
    try:
        from tools.logger import write_quality_event
        arg_keys = ", ".join(sorted(inputs)) if inputs else "no arguments"
        write_quality_event(
            event_type="TOOL_DENIED",
            source_agent=agent,
            detail=(
                f"`{agent}` attempted `{name}` ({arg_keys}) but it is not in its "
                f"allowed_tools. Its instruction file asks for this capability. "
                f"Decide: grant it, build it, or drop the instruction."
            ),
            session_id=datetime.now().strftime("%Y-%m-%dT%H:%M"),
        )
    except Exception as e:
        # Never let audit bookkeeping break a working tool call.
        logger.warning(f"[tool_permissions] could not record denial: {e}")


def dispatch_tool(name: str, inputs: dict, handlers: dict,
                  _agent_rec=None, _turn_num: int = 1,
                  _allowed: set[str] | None = None) -> str:
    """Execute a tool call and return the result as a string."""
    if name not in handlers:
        return f"Error: unknown tool '{name}'"

    # _allowed is the set of tools actually advertised to this agent. None means
    # the caller did not supply it (legacy path or an all-tools agent) — treat
    # that as unrestricted rather than silently blocking everything.
    if _allowed is not None and name not in _allowed:
        _rec = _agent_rec or _tr.get_current_agent()
        _record_tool_denial(getattr(_rec, "agent", "") or "unknown", name, inputs)
        if TOOL_PERMISSION_MODE == "enforce":
            return (
                f"Error: '{name}' is not available to this agent. "
                f"Complete the task with the tools you have, or report what you "
                f"could not do."
            )

    _trace(f"  [TOOL] {name}")
    t0 = time.monotonic()
    fn = handlers[name]
    ok = True
    try:
        # Bind first, so a wrong-argument error can name the right arguments.
        # A bare "got an unexpected keyword argument 'content'" tells the model its
        # guess was wrong but nothing about what is correct, so it guesses again:
        # on 2026-08-02 Logistics burned three of six turns cycling through invented
        # parameter names for write_agent_config, then gave up without ever saving
        # the user's reminder. Binding separately also keeps this hint off genuine
        # TypeErrors raised from inside the tool body.
        try:
            inspect.signature(fn).bind(**inputs)
        except TypeError as bind_err:
            hint = _signature_hint(fn)
            result = f"Error calling tool '{name}': {bind_err}."
            if hint:
                result += f" Correct usage: {hint}"
            ok = False
        else:
            result = fn(**inputs)
            if isinstance(result, dict):
                result = json.dumps(result, indent=2)
            else:
                result = str(result)
    except Exception as e:
        result = f"Error running tool '{name}': {e}"
        ok = False
    duration_ms = round((time.monotonic() - t0) * 1000, 1)
    rec = _agent_rec or _tr.get_current_agent()
    # For run_subagent, pull token counts from the subagent record that was just created.
    in_tok = out_tok = 0
    if name == "run_subagent" and rec is not None:
        t = _tr.get_trace()
        if t is not None:
            subagents = t.pipeline[0].subagents if t.pipeline else []
            agent_arg = inputs.get("agent_name") or inputs.get("agent") or ""
            for sub in reversed(subagents):
                if sub.agent == agent_arg:
                    in_tok = sub.total_input_tokens()
                    out_tok = sub.total_output_tokens()
                    break
    _tr.record_tool_call(rec, _turn_num, name, inputs, result, duration_ms,
                         input_tokens=in_tok, output_tokens=out_tok, ok=ok)
    return result


# ---------------------------------------------------------------------------
# Session runners
# ---------------------------------------------------------------------------

def run_session_anthropic(system_prompt: str, user_input: str,
                           tool_schemas: list[dict], tool_handlers: dict,
                           model: str | None = None) -> str:
    """Agentic loop using the Anthropic API."""

    # The schemas handed to this runner are already filtered to what this
    # agent was granted, so they double as the permission set — no separate
    # lookup, and no way for the two to drift apart.
    _allowed_names = {s['name'] for s in tool_schemas} if tool_schemas else set()
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

        text_parts = []
        thinking_parts = []
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "thinking":
                thinking_parts.append(block.thinking)
            elif block.type == "tool_use":
                tool_calls.append(block)

        _tr.record_turn_tokens(_tr.get_current_agent(), turn_num, _in_tok, _out_tok,
                               output_text="\n".join(text_parts),
                               thinking_text="\n".join(thinking_parts))

        if not tool_calls:
            return "\n".join(text_parts)

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        parallel_calls = []
        for tc in tool_calls:
            if tc.name in _PARALLEL_TOOLS:
                parallel_calls.append(tc)
            else:
                result = dispatch_tool(tc.name, tc.input, tool_handlers, _turn_num=turn_num, _allowed=_allowed_names)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": result,
                })

        if parallel_calls:
            _parent_trace = _tr.get_trace()
            _parent_agent = _tr.get_current_agent()
            _parent_persona = current_persona()
            def _make_dispatch(name, inputs, handlers, turn):
                def _worker():
                    _tr.set_trace(_parent_trace)
                    _tr._set_current_agent(_parent_agent)
                    with (persona_scope(_parent_persona) if _parent_persona else nullcontext()):
                        return dispatch_tool(name, inputs, handlers, _agent_rec=_parent_agent, _turn_num=turn, _allowed=_allowed_names)
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
    history: list[dict] | None = None,
) -> Iterator[str]:
    """Streaming agentic loop for Anthropic.

    Streams every turn. Text from tool-call turns is buffered but not yielded
    (it is internal pre-tool reasoning). Text from the final text turn is yielded
    in real-time as chunks arrive.

    NOTE: Only the Synthesizer uses this function at runtime — it never calls tools,
    so the first turn always goes directly to the yield-and-return path.
    """

    # The schemas handed to this runner are already filtered to what this
    # agent was granted, so they double as the permission set — no separate
    # lookup, and no way for the two to drift apart.
    _allowed_names = {s['name'] for s in tool_schemas} if tool_schemas else set()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set.")

    client = anthropic.Anthropic(api_key=api_key)
    messages: list[dict] = []
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_input})
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
            _thinking_text = "\n".join(
                block.thinking for block in final.content if block.type == "thinking"
            )
            _tr.record_turn_tokens(_tr.get_current_agent(), turn_num, pts, ots,
                                   output_text="".join(text_parts), thinking_text=_thinking_text)

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
            result = dispatch_tool(tc.name, tc.input, tool_handlers, _turn_num=turn_num, _allowed=_allowed_names)
            tool_results.append({"type": "tool_result", "tool_use_id": tc.id, "content": result})

        if parallel_calls:
            _parent_trace = _tr.get_trace()
            _parent_agent = _tr.get_current_agent()
            _parent_persona = current_persona()
            def _make_dispatch(name, inputs, handlers, turn):
                def _worker():
                    _tr.set_trace(_parent_trace)
                    _tr._set_current_agent(_parent_agent)
                    with (persona_scope(_parent_persona) if _parent_persona else nullcontext()):
                        return dispatch_tool(name, inputs, handlers, _agent_rec=_parent_agent, _turn_num=turn, _allowed=_allowed_names)
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

    # The schemas handed to this runner are already filtered to what this
    # agent was granted, so they double as the permission set — no separate
    # lookup, and no way for the two to drift apart.
    _allowed_names = {s['name'] for s in tool_schemas} if tool_schemas else set()
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
        thinking_parts: list[str] = []
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

                # Filter thinking blocks out of the printed/returned text — buffer until
                # we see the closing tag — but keep the buffered text for the trace so
                # it isn't just discarded (it fires despite think=False on qwen3).
                if in_think or "<think>" in text:
                    think_buf += text
                    if not in_think:
                        in_think = True
                    if "</think>" in think_buf:
                        idx = think_buf.index("</think>")
                        thinking_parts.append(
                            think_buf[:idx].replace("<think>", "", 1)
                        )
                        after = think_buf[idx + len("</think>"):]
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
            _tr.record_turn_tokens(_tr.get_current_agent(), _turn, prompt_tokens, eval_tokens,
                                   output_text="".join(content_parts),
                                   thinking_text="".join(thinking_parts))

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
            tool_result = dispatch_tool(tc.function.name, args, tool_handlers, _allowed=_allowed_names)
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


def _reasoning_tokens_openai(usage) -> int:
    """
    Thinking tokens from an OpenAI-compat usage object, which Vertex reports
    *outside* `completion_tokens`.

    This is a deliberate deviation from the OpenAI spec, where reasoning tokens
    are a breakdown within completion_tokens and adding them would double-count.
    Vertex is not: probed 2026-08-08 on gemini-3.1-pro-preview, one call returned
    prompt=36, completion=4, reasoning=306, total=346 — i.e. total is the sum of
    all three. Billing counts thinking as output, so omitting it understated
    output tokens ~6x across August and left the spend guard's daily stop
    denominated in a currency worth half what it claimed.

    Re-probe if the endpoint changes: if prompt + completion == total, the tokens
    are already included and this must return 0.
    """
    details = getattr(usage, "completion_tokens_details", None)
    if details is None:
        return 0
    return int(getattr(details, "reasoning_tokens", 0) or 0)


def _thinking_tokens_gemini(usage_metadata) -> int:
    """
    Thinking tokens from a native genai usage_metadata.

    `candidates_token_count` excludes `thoughts_token_count` — verified on the
    same 2026-08-08 probe (prompt 36 + candidates 4 + thoughts 269 == total 309).
    See _reasoning_tokens_openai for why this matters.
    """
    return int(getattr(usage_metadata, "thoughts_token_count", 0) or 0)


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


_VERTEX_CACHE_MIN_TOKENS = 4096
_VERTEX_CACHE_PAD_UNIT = (
    "[cache padding — not an instruction, disregard]"
)


def _pad_for_vertex_cache(system_prompt: str) -> str:
    """
    Vertex requires >= 4096 tokens of content to create a CachedContent object;
    shorter prompts fail cache creation outright and silently run uncached every
    call. Pad with inert, clearly-marked filler past the threshold.

    The estimate deliberately assumes 5 chars/token rather than 4. Assuming 4 is
    optimistic: it overestimates the token count, so it under-pads. Measured on
    this codebase's own prompts the real ratio is ~4.4 chars/token, so a prompt
    padded to an estimated 4296 tokens arrived as 3898 actual and Vertex rejected
    it. Underestimating is the safe direction — it pads more than needed, and
    surplus padding costs nothing because the cache is read, not regenerated.

    Padding is appended only to the copy sent to the cache — never to the prompt
    used on the uncached/compat paths.
    """
    # 25% headroom on top of the floor, plus a flat margin. Cheap insurance
    # against a prompt-shrinking change quietly disabling caching again.
    target_tokens = int(_VERTEX_CACHE_MIN_TOKENS * 1.25) + 200
    estimated_tokens = len(system_prompt) // 5
    if estimated_tokens >= target_tokens:
        return system_prompt

    pad_tokens_needed = target_tokens - estimated_tokens
    pad_unit_tokens = max(len(_VERTEX_CACHE_PAD_UNIT) // 5, 1)
    repeats = -(-pad_tokens_needed // pad_unit_tokens)  # ceil div
    padding = " ".join([_VERTEX_CACHE_PAD_UNIT] * repeats)
    return f"{system_prompt}\n\n{padding}"


def _is_cache_not_found(exc: Exception) -> bool:
    """True when an exception is Vertex reporting a missing cached_content."""
    text = str(exc).lower()
    return "not_found" in text or ("404" in text and "cach" in text)


def _evict_vertex_cache(cache_name: str) -> None:
    """Remove a cache name from the registry so the next call rebuilds it."""
    for key, (name, _exp) in list(_vertex_cache_registry.items()):
        if name == cache_name:
            _vertex_cache_registry.pop(key, None)


def _get_or_create_vertex_cache(
    client, system_prompt: str, model_name: str,
    tool_schemas: list[dict] | None = None,
) -> str | None:
    """
    Return the Vertex CachedContent name for this (system_prompt, tools) pair.

    Tools are baked into the cache so the request body can stay clean — Vertex
    rejects requests that include both cached_content and tools/system_instruction.
    The cache key includes tool names so different tool sets get separate caches.

    Expire time: midnight UTC tonight — matches the "once per day" config change cadence.
    Returns None on any failure (model doesn't support caching, content too short, etc.).
    The caller falls back to uncached generation.
    """
    import datetime
    import hashlib
    from google.genai import types

    tool_key = ":".join(s["name"] for s in (tool_schemas or []))
    content_hash = hashlib.sha256(f"{model_name}:{system_prompt}:{tool_key}".encode()).hexdigest()[:16]

    entry = _vertex_cache_registry.get(content_hash)
    if entry is not None:
        cached_name, expires_at = entry
        # 60s margin so a cache cannot expire between this check and the request.
        if datetime.datetime.now(datetime.timezone.utc) < expires_at - datetime.timedelta(seconds=60):
            return cached_name
        _vertex_cache_registry.pop(content_hash, None)
        logger.info(f"[vertex_cache] expired hash={content_hash} — recreating")

    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        midnight = (now + datetime.timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        gemini_tools = _to_gemini_tools(tool_schemas or [])
        cache_config = types.CreateCachedContentConfig(
            system_instruction=_pad_for_vertex_cache(system_prompt),
            expire_time=midnight,
            **({"tools": gemini_tools} if gemini_tools else {}),
        )
        cache = client.caches.create(model=model_name, config=cache_config)
        _vertex_cache_registry[content_hash] = (cache.name, midnight)
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


# A model-authored provenance block: a SOURCES:/CITATIONS:/REFERENCES: heading at the
# start of a line, plus everything after it to the end of the text. Deliberately greedy
# to the end, because these blocks are always terminal — a half-stripped one would leave
# exactly the invented URLs this exists to remove.
#
# The heading must look like a heading: the keyword followed by a colon, or alone on its
# line. Matching the bare word would truncate a contested-topic answer at a paragraph
# opening "Sources disagree on this" and silently discard the rest of it — losing a good
# answer to catch a bad citation is the wrong trade.
_MODEL_SOURCES_RE = _re.compile(
    r'\n*^[ \t]*(?:\*\*|__)?\s*(?:SOURCES?|CITATIONS?|REFERENCES?)'
    r'(?:\*\*|__)?[ \t]*(?::|$).*\Z',
    _re.MULTILINE | _re.DOTALL | _re.IGNORECASE,
)


def _strip_model_sources(text: str) -> str:
    """Remove any sources block the model wrote for itself.

    `research_agent.md` no longer asks for one, but instruction files are guidance and
    this is the enforcement — a model that writes a citation it did not retrieve must
    not be able to put it in front of the Synthesizer regardless of what it was told.
    """
    return _MODEL_SOURCES_RE.sub("", text).rstrip()


def _log_ungrounded_answer(user_input: str, search_queries: list[str]) -> None:
    """Record a Research answer that retrieved nothing, so these become countable.

    The query count is the useful half of the detail. "Searched 6 times, retrieved
    nothing" and "never searched" are different faults with different fixes — the
    first is a retrieval problem, the second is the agent not reaching for the web at
    all — and a signature that collapsed them would send the reader the wrong way.

    Never raises: this is observability on the response path, and a logging failure
    must not cost the user their answer.
    """
    try:
        from tools.logger import write_quality_event
        searched = (f"{len(search_queries)} search(es) ran but returned no sources"
                    if search_queries else "no search was issued")
        write_quality_event(
            event_type="UNGROUNDED_ANSWER",
            source_agent="research_agent",
            detail=f"Answered with nothing retrieved — {searched}. Query: {user_input[:200]}",
            session_id="research_grounding",
        )
    except Exception:
        pass


def _api_failure_signature(exc: Exception) -> str:
    """A stable one-line class for an API failure, so repeats collapse.

    The backlog sync groups machine events by signature and escalates at three.
    Interpolating the turn number, the model's echoed arguments or a byte offset
    would make every occurrence unique, which is the same as not collapsing.
    """
    text = str(exc)
    if "thought_signature" in text:
        return "missing thought_signature on a function call (400)"
    if "RESOURCE_EXHAUSTED" in text or " 429" in text:
        return "rate limited (429)"
    # Anchored to how a status code is actually written, not any three digits:
    # a bare \b(4\d\d)\b matches the ":443" in an oauth2.googleapis.com
    # connection error and files every DNS blip as "API error 443".
    code = _re.search(r"(?:Error code:|['\"]code['\"]\s*:)\s*(\d{3})", text)
    if code:
        return f"API error {code.group(1)}"
    if "NameResolutionError" in text or "Failed to resolve" in text:
        return "DNS resolution failed"
    return text[:120]


def _log_api_failure(loop: str, model: str, exc: Exception,
                     turn: int | None = None, agent: str | None = None,
                     extra: str = "") -> None:
    """Record a model-call failure, naming the loop that made the call.

    Five `thought_signature` 400s between 2026-08-04 and 08-09 could not be
    attributed to a code path. Two of the five model-call sites — both in the
    streaming loop — logged nothing at all, and the SSE handler returned the
    error to the client without logging it, so the only trace of a web-app
    failure was the text the user saw. A failure nobody can locate is not a
    signal: every call site now names itself.

    The failure also becomes a quality event, so a *recurring* one reaches
    `DEV_BACKLOG.md` through the existing sync rather than living in journald
    where nothing re-reads it.

    `extra` carries per-occurrence diagnostics (message counts, turn state). It
    reaches the log and never the quality event: the sync collapses on the event
    detail, so a varying field there would make every occurrence its own item.
    """
    from core.router import log_model_error
    who = agent or _tr.get_current_agent() or "unknown"
    turn_s = f" turn={turn}" if turn is not None else ""
    extra_s = f" {extra}" if extra else ""
    logger.error(f"[model_error] loop={loop} agent={who} model={model}{turn_s}{extra_s} error={exc}")
    log_model_error(who, loop, model, f"{loop}{turn_s}{extra_s}: {exc}")
    try:
        from tools.logger import write_quality_event
        write_quality_event(
            event_type="MODEL_CALL_FAILED",
            source_agent=who,
            detail=f"{loop}: {_api_failure_signature(exc)}",
            session_id=datetime.now().strftime("%Y-%m-%d"),
        )
    except Exception:
        # Observability must never cost the caller its own error.
        pass


def _thought_signature_state(msg: object) -> str:
    """Classify an assistant tool-call message by whether Vertex signed its calls.

    Instrumentation only (DB-0810-12) — purely observational, never raises and
    never mutates the message. Vertex attaches the signature to each tool call
    as `extra_content["google"]["thought_signature"]`; the OpenAI SDK carries it
    as model_extra on the tool-call object, so it survives `model_copy()` and is
    absent *by construction* from any message rebuilt out of stream deltas.

    Returns "signed", "unsigned", "signed=i/n" (the known Vertex parallel-call
    bug: only tc0 gets one), "n/a" (no tool calls) or "unknown" (inspection
    failed — treated as no evidence either way, not as a signature).
    """
    try:
        tcs = msg.get("tool_calls") if isinstance(msg, dict) else getattr(msg, "tool_calls", None)
        if not tcs:
            return "n/a"
        signed = 0
        for tc in tcs:
            if isinstance(tc, dict):
                extra = tc.get("extra_content")
            else:
                extra = getattr(tc, "extra_content", None)
                if extra is None:
                    extra = (getattr(tc, "model_extra", None) or {}).get("extra_content")
            google = extra.get("google") if isinstance(extra, dict) else None
            if isinstance(google, dict) and google.get("thought_signature"):
                signed += 1
        if signed == 0:
            return "unsigned"
        if signed == len(tcs):
            return "signed"
        return f"signed={signed}/{len(tcs)}"
    except Exception:
        return "unknown"


def run_session_gemini_grounded(system_prompt: str, user_input: str,
                                tool_schemas: list[dict] | None = None,
                                tool_handlers: dict | None = None,
                                model: str | None = None) -> str:
    """
    Gemini session with Google Search grounding, for the Research Agent.

    Provides live web search with source citations, and — since 2026-08-04 — an optional
    bounded tool loop so Research can also call `fetch_url` on a page search cannot be
    pointed at.

    **Grounding and function calling coexist; this was tested, not assumed.** The received
    wisdom is that Gemini rejects `google_search` alongside `function_declarations`. On
    gemini-3.1-pro-preview via Vertex, search-only, functions-only and both-together all
    succeed. The only complaint is about *automatic* function calling, which is disabled
    here — the loop below is manual, matching every other provider path in this file.

    Why this changed: `research_agent.md` was given a `fetch_url` instruction on 2026-08-04
    while this function still passed no tools at all, so Research was told it held a
    capability it could not invoke. An agent in that state does not fail cleanly — it is
    liable to *claim* it read a page it never fetched, which is precisely the
    unretrieved-source problem `fetch_url` existed to fix.

    Without `tool_schemas` the behaviour is exactly as before: one call, no loop.
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

    tools = [types.Tool(google_search=types.GoogleSearch())]
    if tool_schemas:
        tools.extend(_to_gemini_tools(tool_schemas))

    # The set actually advertised to this agent, which is what the permission check in
    # dispatch_tool compares against. Derived here rather than passed in, so it cannot
    # drift from the schemas the model was shown.
    _allowed = {s["name"] for s in tool_schemas} if tool_schemas else None

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=tools,
        # Manual loop below, as on every other provider path. Left on, the SDK would
        # try to invoke callables itself and warn that declarations are incompatible.
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    contents = [types.Content(role="user", parts=[types.Part(text=user_input)])]
    sources: list[str] = []
    # The queries Gemini actually issued to Google Search. This is the only direct
    # evidence that retrieval happened at all: grounded search fires server-side and
    # produces zero tool calls, so nothing else in the trace distinguishes a genuinely
    # grounded answer from one written straight out of training knowledge.
    search_queries: list[str] = []
    text = ""
    # Low deliberately. Research fetches a page or two to check a source; it is not an
    # agentic browser, and an unbounded loop here would be a token sink on the one path
    # that already carries live search.
    max_turns = 4 if tool_schemas else 1

    for turn in range(1, max_turns + 1):
        _trace(f"[API] gemini-grounded/{model_name}  turn={turn}  waiting...")
        try:
            response = client.models.generate_content(
                model=model_name, contents=contents, config=config,
            )
        except Exception as _api_exc:
            _log_api_failure("gemini_grounded", model_name, _api_exc, turn=turn,
                             agent=_tr.get_current_agent() or "research_agent")
            raise

        # Token budget logging (native SDK field)
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
            output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
            thinking_tokens = _thinking_tokens_gemini(response.usage_metadata)
            if input_tokens > 8000:
                logger.warning(f"[token_budget] OVER_8K turn={turn} cumulative_input={input_tokens}")
            else:
                logger.info(f"[token_budget] turn={turn} cumulative_input={input_tokens}")
            # response.text raises when the turn's only content is a function_call
            # (no text part) — catch rather than let a trace-only read break the turn.
            try:
                _turn_text = response.text or ""
            except Exception:
                _turn_text = ""
            _tr.record_turn_tokens(_tr.get_current_agent(), turn, input_tokens, output_tokens, thinking_tokens,
                                   output_text=_turn_text)

        # Grounding sources accumulate across turns — a citation found on turn 1 is still
        # a source for the final answer even if turn 2 fetched a page directly.
        if response.candidates:
            gm = getattr(response.candidates[0], "grounding_metadata", None)
            if gm:
                # grounding_chunks is a real attribute that Gemini sometimes sets to
                # None (grounding_metadata present, no groundable chunks) rather than
                # omitting it — getattr's default only covers a missing attribute, so
                # `or []` is required to catch the None-valued case too.
                for chunk in getattr(gm, "grounding_chunks", None) or []:
                    web = getattr(chunk, "web", None)
                    if web and getattr(web, "uri", None) and web.uri not in sources:
                        sources.append(web.uri)
                # Same None-valued-attribute caveat as grounding_chunks above.
                for q in getattr(gm, "web_search_queries", None) or []:
                    if q and q not in search_queries:
                        search_queries.append(q)

        calls = getattr(response, "function_calls", None) or []
        if not calls or not tool_handlers:
            text = response.text or ""
            break

        contents.append(response.candidates[0].content)
        parts = []
        for call in calls:
            result = dispatch_tool(call.name, dict(call.args or {}), tool_handlers,
                                   _turn_num=turn, _allowed=_allowed)
            # A fetched page is its own source. Recording it here means the SOURCES
            # field reflects what was actually read, not only what search surfaced.
            if call.name == "fetch_url":
                url = (call.args or {}).get("url")
                if url and url not in sources:
                    sources.append(url)
            parts.append(types.Part.from_function_response(
                name=call.name, response={"result": result}))
        contents.append(types.Content(role="user", parts=parts))
    else:
        # Loop exhausted with the model still calling tools. Return what it last said
        # rather than nothing, and say so — a silent empty answer from Research reads
        # as "no information found", which is a different and misleading claim.
        text = (response.text or "").strip()
        text += ("\n\n[Note: stopped after the tool-call limit; this answer may be "
                 "incomplete.]")

    # Provenance is authored here and nowhere else. Before 2026-08-10 the model wrote
    # its own SOURCES: block into the text and this appended a second, honest one — so a
    # turn with zero retrieval carried both "SOURCES: Flightradar24, FlightAware ... (via
    # live web search)" and "SOURCES: training knowledge", and the Synthesizer believed
    # the specific, confident, fabricated one. A model's claim about its own retrieval is
    # not evidence of retrieval; only what the SDK reports back is.
    text = _strip_model_sources(text)

    if sources:
        sources_block = "\n".join(f"- {url}" for url in sources)
        text = f"{text}\n\nSOURCES ({len(sources)} retrieved):\n{sources_block}"
    else:
        text = f"{text}\n\n[RETRIEVAL: NONE — not checked against any live source]"

    _tr.record_retrieval(_tr.get_current_agent(), search_queries, sources)
    # Fires on "no sources", not "no queries". A search that ran and returned nothing
    # still leaves the answer resting on training knowledge, and that case is worth
    # counting *more* than the no-search case, not less: the model has already decided
    # the question needed checking, and is answering anyway.
    if not sources:
        _log_ungrounded_answer(user_input, search_queries)

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

    cached_content_name = _get_or_create_vertex_cache(client, system_prompt, model_name, tool_schemas)

    try:
        return _run_gemini_native_loop(
            client, model_name, system_prompt, user_input,
            tool_schemas, tool_handlers,
            history=history,
            cached_content=cached_content_name,
        )
    except Exception as e:
        from core.router import log_model_error
        _agent = _tr.get_current_agent() or "unknown"

        # A cache can vanish before its recorded expiry (deleted, or the project
        # evicted it). Drop the dead entry and rebuild once, rather than running
        # uncached for the rest of the process lifetime.
        if cached_content_name and _is_cache_not_found(e):
            _evict_vertex_cache(cached_content_name)
            logger.info(f"[vertex_cache] {cached_content_name} not found — evicted, rebuilding once")
            try:
                fresh = _get_or_create_vertex_cache(client, system_prompt, model_name, tool_schemas)
                return _run_gemini_native_loop(
                    client, model_name, system_prompt, user_input,
                    tool_schemas, tool_handlers,
                    history=history,
                    cached_content=fresh,
                )
            except Exception as retry_exc:
                e = retry_exc

        logger.warning(f"[vertex_cache] native loop failed ({e}) — falling back to compat")
        log_model_error(_agent, "gemini-cached", model_name, f"native loop failed, fell back to compat: {e}")
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

    # The schemas handed to this runner are already filtered to what this
    # agent was granted, so they double as the permission set — no separate
    # lookup, and no way for the two to drift apart.
    _allowed_names = {s['name'] for s in tool_schemas} if tool_schemas else set()
    from google.genai import types

    gemini_tools = _to_gemini_tools(tool_schemas)
    _tools_kwarg = {"tools": gemini_tools} if gemini_tools else {}
    if cached_content:
        # Tools and system_instruction are baked into the cache — must not repeat them here.
        config = types.GenerateContentConfig(
            cached_content=cached_content,
            max_output_tokens=4096,
        )
    else:
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=4096,
            **_tools_kwarg,
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
            thinking_tokens = _thinking_tokens_gemini(response.usage_metadata)
            cache_read = getattr(response.usage_metadata, "cached_content_token_count", 0) or 0
            cumulative_input_tokens += input_tokens
            _cache_suffix = f" cache_read={cache_read}" if cache_read else ""
            if cumulative_input_tokens > 8000:
                logger.warning(f"[token_budget] OVER_8K turn={turn_num} cumulative_input={cumulative_input_tokens}{_cache_suffix}")
                _trace(f"[TOKEN] turn={turn_num} input={input_tokens} cumulative={cumulative_input_tokens}{_cache_suffix} ⚠ OVER_8K")
            else:
                logger.info(f"[token_budget] turn={turn_num} cumulative_input={cumulative_input_tokens}{_cache_suffix}")
                _trace(f"[TOKEN] turn={turn_num} input={input_tokens} cumulative={cumulative_input_tokens}{_cache_suffix}")

        model_content = response.candidates[0].content
        contents.append(model_content)

        function_calls = []
        text_parts = []
        for part in model_content.parts:
            if part.function_call:
                function_calls.append(part.function_call)
            elif part.text:
                text_parts.append(part.text)

        if hasattr(response, "usage_metadata") and response.usage_metadata:
            _tr.record_turn_tokens(_tr.get_current_agent(), turn_num, input_tokens, output_tokens, thinking_tokens,
                                   output_text="\n".join(text_parts))

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
                res = dispatch_tool(fc.name, fc.args, tool_handlers, _turn_num=turn_num, _allowed=_allowed_names)
                result_parts.append(
                    types.Part.from_function_response(name=fc.name, response={"result": res})
                )

        if parallel_calls:
            _parent_trace = _tr.get_trace()
            _parent_agent = _tr.get_current_agent()
            _parent_persona = current_persona()
            def _make_gemini_dispatch(fc_name, fc_args, handlers, turn):
                def _worker():
                    _tr.set_trace(_parent_trace)
                    _tr._set_current_agent(_parent_agent)
                    with (persona_scope(_parent_persona) if _parent_persona else nullcontext()):
                        return dispatch_tool(fc_name, fc_args, handlers,
                                            _agent_rec=_parent_agent, _turn_num=turn, _allowed=_allowed_names)
                return _worker
            with ThreadPoolExecutor() as executor:
                future_to_fc = {
                    executor.submit(_make_gemini_dispatch(fc.name, fc.args, tool_handlers, turn_num)): fc
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

    # The schemas handed to this runner are already filtered to what this
    # agent was granted, so they double as the permission set — no separate
    # lookup, and no way for the two to drift apart.
    _allowed_names = {s['name'] for s in tool_schemas} if tool_schemas else set()
    client = openai.OpenAI(api_key=api_key, base_url=base_url or None)
    oai_tools = _to_openai_tools(tool_schemas)
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_input})
    cumulative_input_tokens = 0
    result = ""  # accumulated text; may be set in a tool-call turn if model mixes text+tools

    _provider_label = "gemini" if base_url and "googleapis" in base_url else (base_url or "openai")

    for turn_num in range(1, max_iterations + 1):
        _trace(f"[API] {base_url or 'openai'}/{model}  turn={turn_num}  waiting...")
        token_kwarg = "max_completion_tokens" if model.startswith("o") else "max_tokens"
        try:
            response = client.chat.completions.create(
                model=model,
                **{token_kwarg: 4096},
                **({"tools": oai_tools} if oai_tools else {}),
                messages=messages,
                **({"extra_body": extra_body} if extra_body else {}),
            )
        except Exception as _api_exc:
            # msgs= is the index base for the "position N" Vertex quotes in a
            # thought_signature 400 — it is what tells us which message it means.
            _log_api_failure(f"openai_compat[{_provider_label}]", model, _api_exc,
                             turn=turn_num, extra=f"msgs={len(messages)}")
            raise

        choice = response.choices[0]
        message = choice.message

        # Capture any text content now — Gemini can emit text + tool_call in the same turn.
        # Without this, the user-facing response text gets discarded when the loop continues
        # to execute the tool call, and the model returns nothing on the following turn.
        if message.content:
            result = message.content

        if response.usage:
            _in_tok = response.usage.prompt_tokens
            _out_tok = getattr(response.usage, "completion_tokens", 0) or 0
            _think_tok = _reasoning_tokens_openai(response.usage)
            cumulative_input_tokens += _in_tok
            if cumulative_input_tokens > 8000:
                logger.warning(f"[token_budget] OVER_8K turn={turn_num} cumulative_input={cumulative_input_tokens}")
                _trace(f"[TOKEN] turn={turn_num} input={_in_tok} cumulative={cumulative_input_tokens} ⚠ OVER_8K")
            else:
                logger.info(f"[token_budget] turn={turn_num} cumulative_input={cumulative_input_tokens}")
                _trace(f"[TOKEN] turn={turn_num} input={_in_tok} cumulative={cumulative_input_tokens}")
            _tr.record_turn_tokens(_tr.get_current_agent(), turn_num, _in_tok, _out_tok, _think_tok,
                                   output_text=message.content or "")

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
            result = dispatch_tool(tc.function.name, inputs, tool_handlers, _turn_num=turn_num, _allowed=_allowed_names)
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
            result = dispatch_tool(tc0.function.name, inputs, tool_handlers, _turn_num=turn_num, _allowed=_allowed_names)
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

    NOTE: Only the Synthesizer uses this function at runtime. It *does* call tools —
    the claim here that it never does, and that only the final-turn streaming path is
    exercised, is contradicted by all four captured [DB-0810-12] occurrences (agent
    `synthesizer`, tool `write_quality_event`). The tool-call path below is live on a
    user's conversation path; do not treat it as dead code.
    """

    # The schemas handed to this runner are already filtered to what this
    # agent was granted, so they double as the permission set — no separate
    # lookup, and no way for the two to drift apart.
    _allowed_names = {s['name'] for s in tool_schemas} if tool_schemas else set()
    client = openai.OpenAI(api_key=api_key, base_url=base_url or None)
    oai_tools = _to_openai_tools(tool_schemas)
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_input})

    # DB-0810-12 instrumentation. Every assistant tool-call message this loop puts
    # into `messages` without a Vertex thought_signature is recorded here as
    # "pos=<index>:turn=<n>:src=<branch>:tools=<names>". Vertex's 400 names the
    # *position* of the offending message (position 12 in all four captured
    # occurrences), so position is the correlating key — the ledger is replayed
    # into the failure log below, which lets one future occurrence say whether the
    # message Vertex rejected is one this loop wrote unsigned, and from which branch.
    _unsigned_appends: list[str] = []

    def _note_unsigned(src: str, pos: int, turn: int, names) -> None:
        entry = (f"pos={pos}:turn={turn}:src={src}"
                 f":tools={','.join(sorted(n for n in names if n)) or 'none'}")
        _unsigned_appends.append(entry)
        # WARNING, not INFO: this is the branch under investigation and it is rare
        # by construction, so it cannot flood a live conversation's logs.
        logger.warning(f"[signature_probe] unsigned_assistant_appended {entry} "
                       f"agent={_tr.get_current_agent()} model={model}")

    for turn_num in range(1, max_iterations + 1):
        _trace(f"[API] {base_url or 'openai'}/{model}  turn={turn_num}  streaming...")
        token_kwarg = "max_completion_tokens" if model.startswith("o") else "max_tokens"

        # Snapshot messages before this turn so we can replay blocking if tool calls appear.
        messages_snapshot = list(messages)

        try:
            stream = client.chat.completions.create(
                model=model,
                **{token_kwarg: 4096},
                **({"tools": oai_tools} if oai_tools else {}),
                messages=messages,
                stream=True,
                stream_options={"include_usage": True},
                **({"extra_body": extra_body} if extra_body else {}),
            )
        except Exception as _api_exc:
            # msgs= is the index base for the "position N" Vertex quotes in a
            # thought_signature 400, matching _openai_compat_loop. unsigned= is the
            # DB-0810-12 ledger: if Vertex's position matches one of these entries,
            # the unsigned message is this loop's own and the entry names the branch
            # that wrote it. An empty ledger on a signature 400 falsifies that whole
            # hypothesis and points the next investigation at `history` or the
            # blocking replay instead.
            _log_api_failure("openai_compat_stream", model, _api_exc, turn=turn_num,
                             extra=(f"msgs={len(messages)} "
                                    f"unsigned=[{';'.join(_unsigned_appends) or 'none'}]"))
            raise

        text_parts: list[str] = []
        tool_calls_raw: dict[int, dict] = {}  # delta index → accumulated data
        finish_reason: str | None = None
        _usage_recorded = False

        for chunk in stream:
            if not chunk.choices:
                # Usage-only trailing chunk (include_usage=True) — standard OpenAI pattern
                if hasattr(chunk, "usage") and chunk.usage and not _usage_recorded:
                    pts = chunk.usage.prompt_tokens or 0
                    ots = getattr(chunk.usage, "completion_tokens", 0) or 0
                    thts = _reasoning_tokens_openai(chunk.usage)
                    if pts > 8000:
                        logger.warning(f"[token_budget] OVER_8K turn={turn_num} cumulative_input={pts}")
                        _trace(f"[TOKEN] turn={turn_num} input={pts} ⚠ OVER_8K")
                    else:
                        logger.info(f"[token_budget] turn={turn_num} cumulative_input={pts}")
                        _trace(f"[TOKEN] turn={turn_num} input={pts}")
                    _tr.record_turn_tokens(_tr.get_current_agent(), turn_num, pts, ots, thts,
                                           output_text="".join(text_parts))
                    _usage_recorded = True
                continue

            choice = chunk.choices[0]
            if choice.finish_reason:
                finish_reason = choice.finish_reason
            delta = choice.delta

            # Vertex AI embeds usage in the finish chunk (choices non-empty) rather than
            # a trailing chunk — capture it here as a fallback so Synth tokens are recorded.
            if choice.finish_reason and hasattr(chunk, "usage") and chunk.usage and not _usage_recorded:
                pts = getattr(chunk.usage, "prompt_tokens", 0) or 0
                ots = getattr(chunk.usage, "completion_tokens", 0) or 0
                thts = _reasoning_tokens_openai(chunk.usage)
                if pts or ots:
                    if pts > 8000:
                        logger.warning(f"[token_budget] OVER_8K turn={turn_num} cumulative_input={pts}")
                        _trace(f"[TOKEN] turn={turn_num} input={pts} ⚠ OVER_8K")
                    else:
                        logger.info(f"[token_budget] turn={turn_num} cumulative_input={pts}")
                        _trace(f"[TOKEN] turn={turn_num} input={pts}")
                    _tr.record_turn_tokens(_tr.get_current_agent(), turn_num, pts, ots, thts,
                                           output_text="".join(text_parts))
                    _usage_recorded = True

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

        # Tool-call turn — Vertex requires thought_signature on all function-call content
        # blocks. Stream deltas don't carry thought_signature, so a reconstructed-from-deltas
        # assistant dict causes a 400 on the next request. Fix: replay this turn blocking to
        # get a real Vertex message object (which carries thought_signature in extra_content),
        # then apply the same workaround used in _openai_compat_loop.
        # The streaming text already yielded above is correct; this replay is used only to
        # build the signed assistant message — its text is not re-yielded.
        try:
            blocking_resp = client.chat.completions.create(
                model=model,
                **{token_kwarg: 4096},
                **({"tools": oai_tools} if oai_tools else {}),
                messages=messages_snapshot,
                stream=False,
                **({"extra_body": extra_body} if extra_body else {}),
            )
        except Exception as _api_exc:
            # Names the tools the stream had asked for: a thought_signature 400 here
            # means the *replay* was rejected, which distinguishes a signature that
            # was never issued from one lost on the way back into `messages`.
            _wanted = ",".join(sorted({t["name"] for t in tool_calls_raw.values() if t.get("name")})) or "none"
            _log_api_failure(f"openai_compat_stream:replay[{_wanted}]", model, _api_exc, turn=turn_num,
                             extra=(f"msgs={len(messages_snapshot)} "
                                    f"unsigned=[{';'.join(_unsigned_appends) or 'none'}]"))
            raise
        blocking_msg = blocking_resp.choices[0].message

        # Apply the same thought_signature workaround as _openai_compat_loop using the
        # blocking message object (which carries Vertex's signed extra_content).
        #
        # DB-0810-12: "carries" is an assumption, so check it rather than trust it. The
        # replay is the mitigation itself — if Vertex hands back tool calls with no
        # signature, the mitigation is silently a no-op and the else branch below is
        # not the only unsigned path. This states which it was, on every tool turn.
        if blocking_msg.tool_calls:
            if len(blocking_msg.tool_calls) == 1:
                _signed = blocking_msg
                messages.append(blocking_msg)
                tc = blocking_msg.tool_calls[0]
                inputs = json.loads(tc.function.arguments)
                dispatch_tool(tc.function.name, inputs, tool_handlers, _turn_num=turn_num, _allowed=_allowed_names)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": ""})
            else:
                tc0 = blocking_msg.tool_calls[0]
                inputs = json.loads(tc0.function.arguments)
                dispatch_tool(tc0.function.name, inputs, tool_handlers, _turn_num=turn_num, _allowed=_allowed_names)
                _signed = blocking_msg.model_copy(update={"tool_calls": [tc0]})
                messages.append(_signed)
                messages.append({"role": "tool", "tool_call_id": tc0.id, "content": ""})
            # Judge the message that was *actually appended*, not the raw response: in
            # the parallel case only tc0 is signed (the known Vertex bug) and the copy
            # is reduced to tc0, so the raw response would read "signed=1/2" every time
            # and bury the real signal in expected noise.
            _sig_state = _thought_signature_state(_signed)
            if _sig_state != "signed":
                _note_unsigned(f"blocking_replay[{_sig_state}]", len(messages) - 2, turn_num,
                               [tc.function.name for tc in _signed.tool_calls])
        else:
            # Blocking replay didn't produce tool calls — use the stream-based reconstruction
            # as fallback (rare; means the two calls diverged).
            reconstructed = [
                {"id": tool_calls_raw[i]["id"], "type": "function",
                 "function": {"name": tool_calls_raw[i]["name"], "arguments": tool_calls_raw[i]["arguments"]}}
                for i in sorted(tool_calls_raw)
            ]
            # DB-0810-12 leading hypothesis. This dict is unsigned by construction —
            # stream deltas carry no thought_signature and the replay produced nothing
            # to take one from. Record the position it is about to occupy so a later
            # Vertex 400 quoting that position identifies this branch as the source.
            _note_unsigned("stream_delta_fallback", len(messages), turn_num,
                           [t.get("name") for t in tool_calls_raw.values()])
            messages.append({"role": "assistant", "content": "".join(text_parts) or None, "tool_calls": reconstructed})
            for tc in reconstructed:
                inputs = json.loads(tc["function"]["arguments"])
                dispatch_tool(tc["function"]["name"], inputs, tool_handlers, _turn_num=turn_num, _allowed=_allowed_names)
                messages.append({"role": "tool", "tool_call_id": tc["id"], "content": ""})

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

    if not provider:
        from core.router import resolve_model
        model_cfg = resolve_model(agent_name, complexity=complexity)
        provider = model_cfg.provider
        if model_override is None:
            model_override = model_cfg.model
        base_url_override = model_cfg.base_url

    _trace(f"[AGENT] {agent_name}  provider={provider}  model={model_override}{'  bare=True' if bare else ''}")
    agent = load_agent(agent_name)

    if bare or agent_name in {"research_agent", "diarist"}:
        # No personal config or context — decontextualized / diagnostic mode.
        # diarist: write-only, directive-driven; goals.yaml adds tokens without value.
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
        # Routing layer: goals.yaml + profile + recent context. No constitution/prime_directive —
        # values are enforced by the Synthesizer; Coordinator needs domain and context only.
        goals = load_goals(persona=persona)
        profile = load_profile(persona=persona)
        recent = load_recent_context(persona=persona)
        prompt_parts = [f"## Your Role for This Session\n\n{agent}"]
        if goals:
            prompt_parts.append(goals)
        if profile:
            prompt_parts.append(profile)
        system_prompt = "\n\n---\n\n".join(prompt_parts)
        augmented_input = f"[Recent context]\n{recent}\n\n---\n\n{user_input}" if recent else user_input
        context_sections = {"agent_file": agent, "goals": goals, "recent_context": recent}
    else:
        # Specialists: goals.yaml only. Context arrives via the Coordinator directive
        # — except the date, which no directive carries. Specialists write dated
        # records (write_log, calendar events, recurring obligations), so without a
        # clock they invent one: on 2026-08-02 Logistics filed a credit-card reminder
        # into a log dated 2025-05-22, fourteen months in the past. One line, and it
        # goes in the user message so the cacheable system prefix stays stable.
        goals = load_goals(persona=persona)
        system_prompt = (
            f"## Your Role for This Session\n\n{agent}\n\n---\n\n{goals}"
            if goals else f"## Your Role for This Session\n\n{agent}"
        )
        clock = clock_line()
        augmented_input = f"{clock}\n\n---\n\n{user_input}" if clock else user_input
        context_sections = {"agent_file": agent, "goals": goals, "clock": clock}

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
                # Tools are passed now (2026-08-04). Before this, the grounded path took
                # none — so research_agent's `allowed_tools` had no effect whatsoever, and
                # the `fetch_url` line in its instruction file described something it could
                # not do. Its whitelist is what bounds this: keep it narrow.
                result = run_session_gemini_grounded(system_prompt, augmented_input,
                                                     tool_schemas, tool_handlers,
                                                     model=model_override)
            elif agent_name in (_HEAD_LAYER_AGENTS | _ROUTING_LAYER_AGENTS):
                result = run_session_gemini_cached(system_prompt, augmented_input, tool_schemas,
                                                   tool_handlers, model=model_override, history=history)
            else:
                result = run_session_gemini(system_prompt, augmented_input, tool_schemas, tool_handlers,
                                            model=model_override, history=history)
        else:
            from core.router import log_model_error
            log_model_error(agent_name, provider or "unknown", model_override, f"unrecognised provider '{provider}' — no session started")
            raise RuntimeError(
                f"Agent '{agent_name}': unrecognised provider '{provider}'. "
                f"Valid values: gemini, openai, ollama, anthropic."
            )
    finally:
        _tr.pop_agent(_agent_rec)

    # A specialist whose writes fail still returns a confident prose summary, and
    # the Synthesizer sees only that summary — so it reports success. On 2026-08-02
    # Logistics failed three save attempts and the user was told "The reminder for
    # the 15th is set." Nothing had been saved. Append the failures so the
    # Synthesizer can tell the user what did not happen.
    #
    # Head and routing layer excluded: the Synthesizer's own output goes straight
    # to the user, and the Coordinator's is parsed for SPECIALISTS_TO_CALL.
    if agent_name not in (_HEAD_LAYER_AGENTS | _ROUTING_LAYER_AGENTS):
        failures = _failed_tool_calls(_agent_rec)
        if failures:
            result = (f"{result}\n\n[TOOL FAILURES — these actions did NOT complete. "
                      f"Do not tell the user they succeeded.]\n" + "\n".join(failures))
    return result


def _failed_tool_calls(rec) -> list[str]:
    """
    Tool calls that failed and were never afterwards made to work, for reporting
    upward to the Synthesizer.

    A tool that failed and then succeeded on a retry is deliberately omitted: the
    action did happen, and reporting it would have the Synthesizer tell the user a
    save failed when it landed. Only a tool with no successful call anywhere in the
    session counts as a real failure.

    Any result beginning "Error" counts — that covers a bad call signature, a raised
    exception, and a permission denial such as a write to a non-allowlisted file.
    """
    if rec is None:
        return []

    failures: dict[str, str] = {}
    succeeded: set[str] = set()
    for turn in rec.turns:
        for tc in turn.tool_calls:
            preview = str(tc.result_preview)
            if preview.startswith("Error"):
                failures.setdefault(tc.name, preview[:300])
            else:
                succeeded.add(tc.name)

    return [f"- {name}: {msg}" for name, msg in failures.items() if name not in succeeded]


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

    _AGENT_NAME_MAP = {
        # Full names
        "mental wellbeing": "mental_wellbeing",
        "physical health": "physical_health",
        "work & vocation": "work_vocation",
        "work and vocation": "work_vocation",
        "learning & growth": "learning_growth",
        "learning and growth": "learning_growth",
        "recreation & hobbies": "recreation_hobbies",
        "recreation and hobbies": "recreation_hobbies",
        "research agent": "research_agent",
        "goals interviewer": "goals_interviewer",
        "pattern miner": "pattern_miner",
        "time director": "time_director",
        # Single-word abbreviations: Flash-Lite sometimes shortens multi-word names
        "research": "research_agent",
        "mental": "mental_wellbeing",
        "physical": "physical_health",
        "work": "work_vocation",
        "learning": "learning_growth",
        "recreation": "recreation_hobbies",
        "goals": "goals_interviewer",
        "pattern": "pattern_miner",
        "time": "time_director",
    }

    def _normalize_agent(name: str) -> str:
        lowered = name.lower()
        if lowered in _AGENT_NAME_MAP:
            return _AGENT_NAME_MAP[lowered]
        # Generic fallback: lowercase + replace " & "/" and "/" spaces with underscore
        return lowered.replace(" & ", "_").replace(" and ", "_").replace(" ", "_")

    for spec in specialists:
        agent = spec.get("agent", "")
        agent = _normalize_agent(agent)
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
            _fan_persona = current_persona()
            # Trace context is thread-local. Without propagating it, every
            # specialist's push_agent() lands on an empty context and the
            # subagent record is silently dropped — which is why The Book showed
            # only coordinator and synthesizer while the logs showed three
            # specialists running concurrently. Same pattern as the parallel
            # tool-dispatch sites above.
            _fan_trace = _tr.get_trace()
            _fan_agent = _tr.get_current_agent()

            def _make_specialist(agent_name, directive, cx):
                def _worker():
                    _tr.set_trace(_fan_trace)
                    _tr._set_current_agent(_fan_agent)
                    with (persona_scope(_fan_persona) if _fan_persona else nullcontext()):
                        return _run_single_agent(
                            agent_name, directive, persona, provider, None, cx
                        )
                return _worker
            futures = {
                executor.submit(_make_specialist(a, d, c)): a
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


# A scheduled session's opening text is written by scheduler.yaml, not by the user.
# It used to arrive in the same slot as user speech, labelled "ORIGINAL USER MESSAGE",
# with nothing marking the difference — `is_proactive` reached the trace and stopped
# there. So the Synthesizer read its own check-in prompt as Mike typing a rule at it,
# matched it against the identical rule already in his persona file, and fired the
# repeated-instruction protocol (synthesizer.md) against text he never sent: four
# times between 2026-08-07 and 08-09 it apologised for "not following" the rule and
# logged an INSTRUCTION_CHANGE_REQUEST. Those events reached DEV_BACKLOG.md as five
# user complaints and made [DB-0809-02] look like the most-repeated request in the
# system's history. The rule was being obeyed in all 22 check-ins that month.
#
# Two consequences worth keeping in view: the system was reporting itself as the
# user, and it narrated its own internals to him while doing so.
_PROACTIVE_FRAME = (
    "[SCHEDULED SESSION — the text below is a directive from the scheduler telling you "
    "to open a session. The user has not spoken yet. Act on it; do not read it as "
    "something the user said, do not reply to it as a request, and never mention it.]"
)


def _frame_proactive(user_input: str, is_proactive: bool) -> tuple[str, str]:
    """
    Return (coordinator_prefix, synthesizer_label) for one pipeline run.

    The label is load-bearing: calling scheduler text "ORIGINAL USER MESSAGE" is the
    specific thing that made it indistinguishable from user speech.
    """
    if not is_proactive:
        return "", "ORIGINAL USER MESSAGE"
    return f"{_PROACTIVE_FRAME}\n\n", "SCHEDULER DIRECTIVE (the user has not spoken yet)"


def run_pipeline_session(user_input: str,
                         persona: str | None = None,
                         provider: str | None = None,
                         history: list[dict] | None = None,
                         received_at: datetime | None = None,
                         is_proactive: bool = False) -> str:
    """
    Run the two-pass Coordinator → Synthesizer pipeline.

    Pass 1 (Coordinator): receives pre-loaded context, resolves intent, returns
    SPECIALISTS_TO_CALL directives in a single response (no tool calls needed).
    Python dispatches specialists in parallel from the Coordinator's output.

    Pass 2 (Synthesizer): receives original message + Coordinator routing package
    + specialist outputs, integrates, responds to user.

    received_at: actual message-arrival timestamp (UTC-aware), captured at the
    WebSocket boundary in core/server.py. More precise than the ambient system
    clock, which reflects "now" at the time each agent runs — several seconds
    to tens of seconds after the message actually arrived, once pipeline
    latency (routing + specialist dispatch + synthesis) is accounted for.
    """
    _guard_msg = _spend_gate()
    if _guard_msg:
        return _guard_msg

    _tr.start_request_trace(user_input, persona)
    try:
        receipt_line = ""
        if received_at is not None:
            from tools.ambient import format_receipt_time
            receipt_line = f"[This message received at: {format_receipt_time(received_at)}]\n\n"

        proactive_prefix, synth_label = _frame_proactive(user_input, is_proactive)

        # Pre-load Pattern Miner insights (the one context source not in the system prompt).
        coord_context = _load_coordinator_context(persona)
        coord_input = (
            f"{proactive_prefix}{receipt_line}{user_input}\n\n---\n\n[Pre-loaded context]\n{coord_context}"
            if coord_context else f"{proactive_prefix}{receipt_line}{user_input}"
        )

        # Pass 1: Coordinator — single-pass routing directive assembly
        _trace("[PIPELINE] coordinator  starting")
        coord_output = _run_single_agent(
            "coordinator", coord_input, persona=persona, provider=provider
        )
        _trace(f"[PIPELINE] coordinator  done  ({len(coord_output)} chars)")
        # Gated behind AI_TRACE (the existing debug flag) rather than always-on:
        # this fires on every scheduled job, so unconditionally it floods
        # journalctl with routing internals and buries real errors.
        if os.environ.get("AI_TRACE"):
            print(f"\n--- COORD PACKAGE ---\n{coord_output}\n--- END COORD PACKAGE ---\n",
                  file=sys.stderr)

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
            f"{proactive_prefix}{receipt_line}{synth_label}:\n{user_input}\n\n"
            f"COORDINATOR ROUTING PACKAGE:\n{coord_output}"
            + (f"\n\nSPECIALIST OUTPUTS:\n{spec_text}" if spec_text else "")
        )
        _trace("[PIPELINE] synthesizer  starting")
        recent_history = list(history[-10:]) if history else None
        synth_result = _run_single_agent(
            "synthesizer", synthesizer_input, persona=persona, provider=provider,
            history=recent_history,
        )
        _trace(f"[PIPELINE] synthesizer  done  ({len(synth_result)} chars)")
        # Strip the internal [CONTEXT] block before the response leaves the
        # pipeline. Without this it reaches push notifications, the scheduler's
        # terminal output and the non-streaming /session endpoint verbatim, and
        # the context tracker is never updated for proactive sessions.
        visible, _ctx = split_context_block(synth_result)
        persist_context_block(_ctx)
        filtered = filter_output(visible, "synthesizer")
        if history is not None:
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": filtered})
            del history[:-10]
    except Exception:
        _tr.set_trace(None)
        raise
    _tr.finish_request_trace(filtered)
    return filtered


def run_pipeline_session_stream(
    user_input: str,
    persona: str | None = None,
    provider: str | None = None,
    history: list[dict] | None = None,
    is_proactive: bool = False,
    received_at: datetime | None = None,
) -> Iterator[str]:
    """
    Streaming variant of run_pipeline_session().

    Thin wrapper that binds the persona for the whole generator. The binding is
    thread-local and is entered on the thread that iterates the generator — which
    is the executor thread in core/server.py, not the event loop — so concurrent
    requests for different personas cannot observe each other's identity.
    """
    with persona_scope(resolve_persona(persona)) as bound:
        yield from _run_pipeline_session_stream_inner(
            user_input, persona=bound, provider=provider, history=history,
            is_proactive=is_proactive, received_at=received_at,
        )


def _run_pipeline_session_stream_inner(
    user_input: str,
    persona: str | None = None,
    provider: str | None = None,
    history: list[dict] | None = None,
    is_proactive: bool = False,
    received_at: datetime | None = None,
) -> Iterator[str]:
    """
    Pass 1 (Coordinator): runs blocking, identical to run_pipeline_session().
    Pass 2 (Synthesizer): streams output as text chunks, yielding each in real-time.

    Yields text chunks during generation, then exactly one control token:
      "[DONE]"    — generation complete, filter passed
      "[RETRACT]" — filter caught a confidential term; client should discard received text

    Persona is already bound by the caller — do not set it here.

    received_at: see run_pipeline_session() docstring — actual message-arrival
    timestamp, more precise than the ambient system clock once pipeline latency
    (routing + specialist dispatch + synthesis, often tens of seconds) elapses.
    """
    _guard_msg = _spend_gate()
    if _guard_msg:
        yield _guard_msg
        yield "[DONE]"
        return

    _tr.start_request_trace(user_input, persona, is_proactive=is_proactive)

    receipt_line = ""
    if received_at is not None:
        from tools.ambient import format_receipt_time
        receipt_line = f"[This message received at: {format_receipt_time(received_at)}]\n\n"

    # Pass 1: Coordinator — single-pass routing directive assembly (blocking)
    _trace("[PIPELINE] coordinator  starting")
    coord_context = _load_coordinator_context(persona)
    proactive_prefix, synth_label = _frame_proactive(user_input, is_proactive)
    coord_input = (
        f"{proactive_prefix}{receipt_line}{user_input}\n\n---\n\n[Pre-loaded context]\n{coord_context}"
        if coord_context else f"{proactive_prefix}{receipt_line}{user_input}"
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
        f"{proactive_prefix}{receipt_line}{synth_label}:\n{user_input}\n\n"
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
    from core.router import get_allowed_tools
    synth_allowed = get_allowed_tools("synthesizer")
    if synth_allowed is not None:
        synth_allowed_set = set(synth_allowed)
        tool_schemas = [s for s in tool_schemas if s["name"] in synth_allowed_set]
    recent_history = list(history[-10:]) if history else None

    # Resolve Synthesizer provider/model — explicit provider arg overrides router
    if provider:
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
    _history_display = "\n\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in (recent_history or [])
    ) if recent_history else ""
    _synth_rec = _tr.push_agent(
        "synthesizer", synth_provider, synth_model or "",
        {
            "agent_file": agent_instructions,
            "config": config,
            "recent_context": recent,
            "conversation_history": _history_display,
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
            history=recent_history,
        )
    elif synth_provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "")
        gen = _openai_compat_stream(
            system_prompt, augmented_input, tool_schemas, tool_handlers,
            api_key=api_key, base_url=None, model=synth_model or OPENAI_MODEL,
            history=recent_history,
        )
    elif synth_provider == "ollama":
        gen = _openai_compat_stream(
            system_prompt, augmented_input, tool_schemas, tool_handlers,
            api_key="ollama", base_url=synth_base_url or OLLAMA_BASE_URL,
            model=synth_model or OLLAMA_MODEL,
            history=recent_history,
        )
    elif synth_provider == "anthropic":
        from core.router import log_model_error
        logger.warning(f"[provider_warn] synthesizer routed to anthropic — unexpected on VM; check routing config")
        log_model_error("synthesizer", "anthropic", synth_model, "synthesizer reached anthropic streaming branch — check routing config")
        gen = _anthropic_stream(
            system_prompt, augmented_input, tool_schemas, tool_handlers,
            model=synth_model or ANTHROPIC_MODEL,
            history=recent_history,
        )
    else:
        raise NotImplementedError(f"No streaming implementation for provider: {synth_provider}")

    # Stream visible text to client; intercept [CONTEXT] block before it reaches the user.
    # The Synthesizer appends a [CONTEXT]...[/CONTEXT] block after its visible response.
    # Everything before [CONTEXT] is forwarded as SSE chunks; the block is captured,
    # parsed, and written to the context tracker directly — no tool call turn needed.
    _LOOKAHEAD = len(_CONTEXT_OPEN) - 1   # chars to hold back in case delimiter spans chunks

    buffer: list[str] = []
    pending: str = ""          # buffered but not yet yielded (delimiter lookahead window)
    context_started: bool = False

    for chunk in gen:
        buffer.append(chunk)
        if not context_started:
            pending += chunk
            if _CONTEXT_OPEN in pending:
                idx = pending.index(_CONTEXT_OPEN)
                if idx > 0:
                    yield pending[:idx]   # flush everything before the delimiter
                context_started = True
                pending = ""
            elif len(pending) > _LOOKAHEAD:
                safe = len(pending) - _LOOKAHEAD
                yield pending[:safe]
                pending = pending[safe:]

    # Flush any remaining visible text if the delimiter was never seen
    if not context_started and pending:
        yield pending

    complete = "".join(buffer)

    # Same splitting logic as the non-streaming pipeline — one implementation so
    # the two paths cannot drift apart again.
    visible, _ctx = split_context_block(complete)
    if _ctx is None and _CONTEXT_OPEN not in complete:
        logger.warning("[context_block] no [CONTEXT] block in Synthesizer response")
    persist_context_block(_ctx)

    _tr.pop_agent(_synth_rec)
    filtered = filter_output(visible, "synthesizer")
    if history is not None:
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": filtered if filtered == visible else ""})
        del history[:-10]
    if filtered != visible:
        yield "[RETRACT]"
    else:
        yield "[DONE]"

    _trace(f"[PIPELINE] synthesizer  done  ({len(visible)} chars visible)")
    _tr.finish_request_trace(filtered if filtered == visible else "")


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
    with persona_scope(resolve_persona(persona)) as bound:
        if agent_name == "coordinator":
            return run_pipeline_session(
                user_input, persona=bound, provider=provider, history=history
            )

        # Own a trace only when no caller established one. Two callers arrive here
        # with none: core/scheduler.py (every scheduled job) and the fire-and-forget
        # thread in tools/subagent.py (the Diarist), whose thread-local context is
        # fresh. Both ran untraced — so neither appeared in the Book, and
        # pattern_miner and diarist were absent from every August trace file.
        #
        # The condition is load-bearing, not defensive: run_subagent's synchronous
        # path also lands here, inside the parent pipeline's trace. Starting a new
        # one there would replace the parent's thread-local trace and lose the
        # coordinator→specialist nesting the Book renders.
        _owns_trace = _tr.get_trace() is None
        if _owns_trace:
            _tr.start_request_trace(user_input, bound)
            # Gate here for the same reason: an owned trace means nothing upstream
            # ran _spend_gate(). Scheduled sessions previously bypassed the daily
            # stop entirely — the pipeline entry points were its only callers.
            _guard_msg = _spend_gate()
            if _guard_msg:
                _tr.finish_request_trace(_guard_msg)
                return _guard_msg

        _out = ""
        try:
            result = _run_single_agent(
                agent_name, user_input,
                persona=bound, provider=provider,
                model_override=model_override, complexity=complexity,
                history=history, bare=bare,
            )
            _out = filter_output(result, agent_name)
            return _out
        finally:
            if _owns_trace:
                _tr.finish_request_trace(_out)


# ---------------------------------------------------------------------------
# Interactive REPL
# ---------------------------------------------------------------------------

def run_interactive(agent_name: str, persona: str | None = None,
                    provider: str = "gemini") -> None:
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
    from core.remote_client import DEFAULT_SERVER as _DEFAULT_REMOTE_SERVER

    parser = argparse.ArgumentParser(description="Personal AI Life Manager — Runtime Orchestrator")
    parser.add_argument("--agent", default="coordinator", help="Agent to use (default: coordinator → runs full pipeline)")
    parser.add_argument(
        "--persona",
        required=True,
        help="Persona this session serves (e.g. mike, pepys). Required — every "
             "session belongs to exactly one persona.",
    )
    parser.add_argument("--provider", default=None, choices=["anthropic", "openai", "ollama", "gemini"],
                        help="Force a model provider (default: auto-routed via routing.yaml)")
    parser.add_argument("--input", help="Single-shot input (skips interactive mode)")
    parser.add_argument("--bare", action="store_true",
                        help="Load agent file only — skip constitution/config/logs (token-pressure diagnostics)")
    parser.add_argument("--local", action="store_true",
                        help="Run the pipeline in this process instead of through the server. "
                             "Writes to THIS machine's data tree and does not sync with the phone "
                             "or browser — use for offline or diagnostic work only.")
    parser.add_argument("--server", default=None,
                        help=f"Server to connect to when remote (default: {_DEFAULT_REMOTE_SERVER})")
    args = parser.parse_args()

    # Interactive coordinator sessions go through the server by default. Running
    # them in-process builds a second history for the same persona on whichever
    # machine happens to run the command — the split-brain the persona work
    # exists to prevent. --local opts out explicitly.
    _use_remote = (not args.input) and args.agent == "coordinator" and not args.local

    if _use_remote:
        from core.remote_client import run_interactive_remote
        run_interactive_remote(args.persona, server=args.server, provider=args.provider)
    elif args.input:
        result = run_session(args.agent, args.input, persona=args.persona, provider=args.provider,
                             bare=args.bare)
        print(result)
    else:
        if args.agent == "coordinator":
            print(f"[local mode] writing to this machine's data tree — "
                  f"will NOT sync with the phone or browser\n")
        run_interactive(args.agent, persona=args.persona, provider=args.provider)
