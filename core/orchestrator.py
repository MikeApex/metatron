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
import atexit
import inspect
import json
import logging
import os
import sys
import threading
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
from core import attachments as attachments_mod
from core.persona import (
    PersonaError,
    current_persona,
    persona_config_dir,
    persona_data_dir,
    persona_md,
    persona_scope,
    resolve_persona,
)
from tools import turn_context as _turn

ANTHROPIC_MODEL = "claude-sonnet-5"
_PARALLEL_TOOLS = {"run_subagent", "run_model_conference"}

# Vertex context cache registry — in-process singleton, keyed by content hash.
# Populated on first request; survives for the process lifetime.
#
# Caches carry a SLIDING _VERTEX_CACHE_TTL_MINUTES expiry, pushed back lazily
# while a burst of calls is in flight and left to lapse once it stops. Cache
# STORAGE is billed per wall-clock hour ($4.50/1M tokens/hour on Pro) whether or
# not anything reads it, so a long expiry buys idle time nobody uses: the
# previous midnight-UTC scheme billed a 06:19 cache for 17.7 hours to serve a
# median 2-minute burst. Vertex deleting the cache at expire_time is what
# reaps orphans — a process that dies takes its registry with it, and nothing
# else on this machine knows the cache exists.
_vertex_native_client: object | None = None
# sha256[:16] of (model+prompt+tools) → (CachedContent.name, expire_time).
# The expiry is stored because Vertex deletes the cache at that moment; without
# it the registry keeps handing out a dead name and every call 404s.
_vertex_cache_registry: dict[str, tuple[str, "datetime.datetime"]] = {}
# Guards get-or-create, refresh and evict. Mutated from FastAPI request threads
# and from the parallel-tool ThreadPoolExecutor: without it two concurrent first
# turns both create a cache, and the loser's registry write is clobbered while
# its cache object keeps billing with no handle left to delete it.
_vertex_cache_lock = threading.RLock()
OPENAI_MODEL = "o3"
OLLAMA_BASE_URL = "http://localhost:11434/v1"
OLLAMA_MODEL = "qwen3:14b"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_MODEL = "models/gemini-3.1-flash-lite"   # flash default; use GEMINI_PRO_MODEL for full Pro
GEMINI_PRO_MODEL = "models/gemini-3.1-pro-preview"


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def _knowledge_manifest(persona: str | None = None) -> str:
    """
    Name the wisdom-store subjects that hold at least one entry — and nothing more.

    ~20 tokens standing in for a store that would cost thousands to broadcast. The whole
    design of the knowledge layer rests on this: an agent that knows a subject EXISTS will
    fetch it when the conversation turns that way, and will not invent it or ask the user to
    repeat something they already said. Contents never appear here.

    DERIVED BY ENUMERATION, NEVER HAND-WRITTEN. A second hand-maintained list of domains
    would drift from the store the first time one was added — which is precisely how
    `_PROMPT_EXCLUDED` came to document an exclusion it did not enforce (fixed 2026-08-15,
    `f9ffd2a`). There is no list to drift: `domains_present()` reads the file.

    HOW TO REACH IT IS DELIBERATELY ABSENT. The Coordinator selects domains via
    KNOWLEDGE_TO_LOAD and the Synthesizer calls `read_wisdom`; those are two mechanisms for
    two agents, and stating either here would put procedure in a string both of them load
    (.claude/rules/agent-files.md § One Home Per Rule Class). The manifest states a fact; the
    agent files state what to do about it.

    CACHE NOTE: this lands in the head-layer *system* prompt, so the first write into a
    previously-empty domain changes the cached prefix and invalidates both head-layer Vertex
    caches. Bounded at 11 occurrences ever per persona — acceptable, but not surprising when
    it shows up as a one-off cache miss.

    Never raises: a knowledge layer that can break a session is worse than no manifest.
    """
    try:
        from tools.wisdom import domains_present

        with persona_scope(resolve_persona(persona)):
            present = domains_present()
    except Exception as exc:
        logger.warning(f"[knowledge] manifest unavailable: {exc}")
        return ""

    if not present:
        return ""

    return (
        "## What you have on file about the user\n\n"
        f"Standing knowledge — facts and habits that stay true past today — is recorded "
        f"under these subjects: {', '.join(present)}.\n"
        "You are not shown the contents. Do not guess at what they contain, and do not "
        "assume a subject is empty because you cannot see it here."
    )


def load_profile(persona: str | None = None) -> str:
    """
    Load config/profile.yaml (or persona override) and format as a system prompt section,
    followed by the knowledge-store manifest.

    Sensitive-tier: injected only into agents that run on local/sensitive-routed models.
    In practice that is the head layer (via load_config) and the Coordinator — exactly the
    two that need the manifest. Specialists get load_goals() only: they receive the knowledge
    payload in their directive, so a manifest would tell them about a store they are not the
    ones selecting from.

    Returns the manifest alone when there is no profile, and "" when there is neither.
    """
    import yaml as _yaml

    manifest = _knowledge_manifest(persona)

    # No root fallback. A persona without a profile gets no profile — inheriting
    # another persona's name, city and timezone is worse than having none, and
    # that fallback was silently telling every persona it was the real user.
    profile_path = persona_config_dir(persona) / "profile.yaml"

    if not profile_path.exists():
        return manifest

    try:
        profile = _yaml.safe_load(profile_path.read_text()) or {}
    except Exception:
        return manifest

    # Fields tools/profile.py marks as retrieved-on-demand are skipped here rather than being
    # excluded by this function happening not to mention them. Until 2026-08-15 _PROMPT_EXCLUDED
    # was documentary only and this list was the real, unstated policy — so the two could drift
    # silently, and a new render line was all it took to leak a contact detail into every
    # head-layer prompt. `_show()` is the enforcement.
    from tools.profile import _PROMPT_EXCLUDED

    def _show(field: str):
        return None if field in _PROMPT_EXCLUDED else profile.get(field)

    lines = []

    if _show("name"):
        lines.append(f"Name: {profile['name']}")

    loc = profile.get("location") or {}
    loc_parts = [v for v in [loc.get("city"), loc.get("country")] if v]
    if loc_parts:
        lines.append(f"Home location: {', '.join(loc_parts)}")
    if loc.get("timezone"):
        lines.append(f"Timezone: {loc['timezone']}")

    age = _show("age")
    birth_year = _show("birth_year")
    if age:
        lines.append(f"Age: {age}")
    elif birth_year:
        from datetime import date as _date
        computed_age = _date.today().year - int(birth_year)
        lines.append(f"Age: ~{computed_age} (born {birth_year})")

    # [DB-0810-15]: rendered separately, and only when set, because the two are independent —
    # a persona may be written to in one language and answered in another, so collapsing them
    # into one "Language:" line would state something false for exactly the asymmetric case
    # this feature exists to serve. Unset renders nothing at all rather than defaulting to
    # English: no preference must stay distinguishable from a preference for English.
    from tools.profile import language_name

    if _show("input_language"):
        lines.append(f"The user writes and speaks to you in: {language_name(profile['input_language'])}")
    if _show("output_language"):
        lines.append(f"Respond to the user in: {language_name(profile['output_language'])}")

    if _show("occupation"):
        lines.append(f"Occupation: {profile['occupation']}")
    if _show("household"):
        lines.append(f"Household: {profile['household']}")

    for item in (profile.get("other") or []):
        if item:
            lines.append(str(item))

    if not lines:
        return manifest

    profile_section = "## User Profile\n\n" + "\n".join(lines)
    return f"{profile_section}\n\n{manifest}" if manifest else profile_section


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


def session_kind(user_input: str, persona: str | None = None) -> str | None:
    """
    Which scheduled session, if any, opened this turn — the matching key from the
    persona's scheduler.yaml `schedules:` (e.g. "evening_close", "morning_brief"),
    or None for a user-typed turn.

    [DB-0822-10]. The evening ritual was injected into every session's system prompt
    unconditionally, and on 2026-08-21 the full 13-item virtue list went out at 16:27,
    18:24, 19:28 and 20:00; only 20:00 was the evening job. The single thing standing
    between the injected text and recital was one line of prose in
    config/agents/synthesizer.md, which already scopes the ritual correctly and was
    simply not followed. A second copy of an ignored instruction is not a fix, so the
    injection is gated here instead — recital becomes structurally impossible rather
    than discouraged. Generalised 2026-08-27 from evening_close-only to every
    configured schedule, so scheduled-session conduct can ride the same gate
    (_synth_conditional_sections below) instead of every interactive turn's prompt.

    Matched against the persona's OWN configured prompts rather than against
    hard-coded prose: the wording lives in scheduler.yaml, the VM owns the live
    copy, and a literal here would go stale the first time Mike reworded it — silently,
    by un-gating the ritual again. Whitespace- and case-insensitive, because the prompt
    makes a round trip through the scheduler and the app before it arrives. Where two
    prompts both appear in the turn, the longest match wins. Prompts under 20
    normalised characters never match: a short one ("Check in.") is a substring of
    ordinary user speech, and a false positive here silently changes the prompt.

    Returns None for every user-typed turn, which is the common case and the one the
    2026-08-21 recitals were polluting.
    """
    if not user_input:
        return None
    try:
        import yaml
        path = persona_config_dir(persona) / "scheduler.yaml"
        if not path.exists():
            return None
        with open(path) as f:
            cfg = yaml.safe_load(f) or {}
    except (OSError, ValueError, yaml.YAMLError):
        # A missing or malformed schedule must not take the session down. Returning
        # None fails toward the quieter prompt — the ritual is omitted, not recited.
        return None

    norm = lambda s: " ".join(str(s).split()).casefold()
    turn = norm(user_input)
    best: tuple[str, int] | None = None
    for key, entry in ((cfg.get("schedules") or {}).items()):
        prompt = norm((entry or {}).get("prompt") or "")
        if not prompt:
            continue
        # Substring match needs the 20-char floor; a turn that IS the configured
        # prompt, verbatim, is the scheduler at any length ("Check in." — mike's
        # companion_checkin is 9 chars and would otherwise never match).
        if prompt == turn or (len(prompt) >= 20 and prompt in turn):
            if best is None or len(prompt) > best[1]:
                best = (str(key), len(prompt))
    return best[0] if best else None


def _synth_conditional_sections(kind: str | None, package_text: str) -> str:
    """
    Prompt sections the Synthesizer gets only when their trigger is present this
    turn, so ordinary turns do not carry them — the same structural gate as the
    evening ritual above ([DB-0822-10]): text that is not injected cannot leak into
    a session it does not belong to, whatever the model decides.

    Delivered by code, not by a model-initiated tool call, deliberately: the model
    cannot forget to load what it never has to ask for, and no extra model round is
    spent (2026-08-27 audit — read_agent_config reads the per-persona data store
    and has never read config/modules/; this injection is the mechanism ROADMAP
    § D2's context-file pattern assumed existed).
    """
    parts = []
    modules_dir = CONFIG_DIR / "modules"
    triggers = [
        # Scheduled-session conduct: any scheduler-originated turn.
        (kind is not None, "synthesizer_scheduled_sessions.md"),
        # Baseline-interview conduct: a specialist flagged an empty domain baseline.
        ("BASELINE_INCOMPLETE" in (package_text or ""), "synthesizer_onboarding.md"),
    ]
    for fired, filename in triggers:
        if not fired:
            continue
        path = modules_dir / filename
        if path.exists():
            content = path.read_text().strip()
            if content:
                parts.append(content)
    return "\n\n---\n\n".join(parts)


_QUIET_CHECKIN_DIRECTIVE = (
    "NOTHING NEW SINCE THE LAST SCHEDULED RUN{since}. Nothing has come in — no new logs, no "
    "new threads, no change to what was already open. This run is a light check-in: open on "
    "not having heard from him for a while and leave the floor to him. Do not re-open the "
    "day, do not re-list what is already open, and do not manufacture a topic out of "
    "unchanged context."
)

_SCHEDULED_FOCUS_HEADER = "SCHEDULED RUN — FOCUS FOR THIS RUN"

_RITUAL_OWNERSHIP_LINE = (
    "This is the `{kind}` run. Any ritual it owns is in your context above; if none is, this "
    "run has none. Do not continue or complete a ritual belonging to another scheduled job, "
    "however visible its earlier output is in the context you have been given."
)


def _scheduled_focus_block(kind: str | None) -> str:
    """
    The code-computed directive for one scheduled run: ritual ownership, whether anything is
    actually new, and which already-asked questions are off limits. Empty string for every
    user-typed turn, so ordinary conversation is untouched.

    [DB-0809-02] Measured 2026-08-27: four scheduled jobs each re-asked the same unanswered
    question — five asks, no answer — the 13-virtue list went out four times, and the runs with
    the least new information were the LONGEST. Two of those three are conditions no instruction
    can evaluate, because the model cannot see what a previous job asked or whether anything has
    changed since. So the condition is computed in Python and the conclusion is injected, the
    same structural gate as _synth_conditional_sections() above: a question whose text is never
    put in front of the model cannot be re-asked from context.

    NOT A LENGTH CAP. The rejected proposal was "scheduled runs are at most two sentences",
    which would truncate the run that genuinely has something to say. What is capped is the
    *occasion*: a run with nothing new becomes a check-in. A run with something new is as long
    as it needs to be.

    No persona argument: the asked-state lives in the persona-scoped tracker, resolved from the
    thread-local binding the caller already holds — the same way persist_context_block() reaches
    it. Passing one here would be a second, ignorable source of truth for identity.

    Fails open and silent: any error here costs the run its focus directive, never its response.

    A8 placement: this is pipeline conduct and stays in core/orchestrator.py beside
    _synth_conditional_sections(); _owned_rituals() below is config loading and travels with
    load_config() into core/config.py.
    """
    if not kind:
        return ""
    lines = [_SCHEDULED_FOCUS_HEADER, "", _RITUAL_OWNERSHIP_LINE.format(kind=kind)]
    try:
        from tools.context_tracker import note_scheduled_run
        state = note_scheduled_run(kind)
    except Exception as exc:
        logger.warning(f"[scheduled_focus] asked-state unavailable: {exc}")
        return "\n".join(lines)

    if state.get("nothing_new"):
        hours = state.get("hours_since")
        since = f" ({hours}h ago)" if hours is not None else ""
        lines += ["", _QUIET_CHECKIN_DIRECTIVE.format(since=since)]

    open_qs = state.get("open_questions") or []
    if open_qs:
        may = set(state.get("may_reask") or [])
        held = [q for q in open_qs if q["text"] not in may]
        if held:
            lines += ["", "ALREADY ASKED AND STILL UNANSWERED — DO NOT ASK THESE AGAIN:"]
            lines += [
                f"  - \"{q['text']}\" (first asked {q.get('first_asked', 'unknown')}, "
                f"asked {q.get('ask_count', 1)}×)"
                for q in held
            ]
            lines += [
                "These are open items, not obligations. Carry them silently; pick one up only "
                "if the user's own words this turn lead there."
            ]
        if may:
            lines += ["", "MAY BE RAISED ONCE MORE, IF IT IS GENUINELY PRESSING — otherwise "
                          "leave it alone:"]
            lines += [f"  - \"{text}\"" for text in state["may_reask"]]
    return "\n".join(lines)


def _owned_rituals(config_dir: Path, kind: str | None) -> list[tuple[str, str]]:
    """
    The ritual sections this session owns, as (heading, text). Empty for every session that
    owns none — which is every user-typed turn and every scheduled job but one.

    [DB-0809-02] A scheduled job does not continue a ritual that is not its own. The evening
    gate ([DB-0822-10]) proved the mechanism on one file with the owning key written into the
    code; this generalises it so a second ritual cannot arrive un-gated, and so the ownership is
    declared where the content is — by the filename.

    OWNERSHIP RULE: `X_ritual.md` belongs to the schedule key `X`, or to any key that starts
    `X_`. So `evening_ritual.md` is owned by `evening_close`, exactly as before, and a persona
    that adds `morning_ritual.md` gets it in `morning_brief` and nowhere else. Matching the
    filename against the key needs no read of scheduler.yaml and nothing hard-coded here, so
    there is no second copy of the schedule names to go stale — the standing objection to
    literals in session_kind() above.

    The rituals still live in config/personas/{p}/ rather than config/agents/synthesizer.md,
    because the content belongs to one user and that file is loaded by every persona
    (.claude/rules/agent-files.md § One Home Per Rule Class).
    """
    if not kind:
        return []
    out: list[tuple[str, str]] = []
    try:
        paths = sorted(config_dir.glob("*_ritual.md"))
    except OSError:
        return []
    for path in paths:
        owner = path.name[: -len("_ritual.md")]
        if not (kind == owner or kind.startswith(f"{owner}_")):
            continue
        text = path.read_text().strip()
        if text:
            out.append((f"{owner.replace('_', ' ').capitalize()} ritual", text))
    return out


def load_config(persona: str | None = None, kind: str | None = None) -> str:
    """
    Build the system prompt from the four-tier config hierarchy for one persona.
    Loads: constitution -> identity -> prime_directive -> mission -> goals -> profile.

    Tier 0 (the Constitution) is shared by every persona. Tiers 1-3 and the
    profile are per-persona, under config/personas/{persona}/. There is no
    root-level fallback: a session always belongs to exactly one persona.

    `kind` is the session kind from session_kind() above. A ritual is injected only
    into the scheduled job that owns it (`_owned_rituals`); every other session gets
    a prompt ~2KB shorter and no virtue list to recite. Defaults to None — a caller
    that does not know the session kind gets the quieter prompt, not the ritual.
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
    #
    # [DB-0822-10] Injected ONLY into the evening_close session. Until 2026-08-26 this
    # was unconditional, and the full virtue list was recited at 16:27, 18:24, 19:28
    # and 20:00 on 08-21 — three of the four being ordinary turns that had no business
    # carrying it. See session_kind() for why this is gated in code rather than by
    # another line of instruction.
    #
    # [DB-0809-02] Generalised 2026-08-28 from evening_ritual.md alone to every `*_ritual.md`
    # in the persona's config, each owned by the schedule its filename names — see
    # `_owned_rituals()`. A scheduled job does not continue a ritual that is not its own.
    for label, text in _owned_rituals(config_dir, kind):
        sections.append(_titled(label, text))

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
    """
    Extract USER_CORRECTION from Coordinator output and log it via write_quality_event.

    [DB-0815-09] A null-ish payload means "no correction happened" and must not become an
    event. `coordinator.md:88` carries this as a slot in a fixed output template annotated
    "omit if not applicable", and a model filling a template answers the slot rather than
    deleting it — so 93 of 174 live events on 2026-08-15 said "None" / "N/A". They collapsed
    into one `None. ×90` entry that drowned the real signatures in Mike's session-start line.
    Dropping them here rather than at the display layer keeps the *count* honest too, which
    matters because a machine item's ×3 promotion bar is read off these events.
    """
    import re as _re
    match = _re.search(r'^USER_CORRECTION:\s*(.+)$', coord_output, _re.MULTILINE)
    if match:
        try:
            from tools.logger import write_quality_event, is_null_ish
            detail = match.group(1).strip()
            if is_null_ish(detail):
                return
            write_quality_event("USER_CORRECTION", "coordinator", detail)
        except Exception as e:
            logger.warning(f"[PIPELINE] USER_CORRECTION log failed: {e}")


def load_agent(name: str) -> str:
    """Load a sub-agent instruction file from config/agents/{name}.md."""
    agent_path = AGENTS_DIR / f"{name}.md"
    if not agent_path.exists():
        raise FileNotFoundError(f"Agent not found: {agent_path}")
    return agent_path.read_text().strip()


def _relative_age(days_ago: int) -> str:
    """"today" / "yesterday" / "N days ago" — the age phrase used throughout the context."""
    if days_ago <= 0:
        return "today"
    if days_ago == 1:
        return "yesterday"
    return f"{days_ago} days ago"


def _age_annotated(text: str, added: str | None) -> str:
    """
    `text` with the age of the record behind it, when that age is known.

    [DB-0822-06] Stored state was being carried forward as fact indefinitely: on 2026-08-21
    the same exercise hiatus was described five different ways in one day, and the finished
    "Metatron sprint" surfaced in 5 of 9 runs days after it ended. Nothing in the assembled
    context said how old any of it was, so there was nothing for the model to weigh.

    This makes staleness *visible* rather than trying to make code decide what is still true
    — which is the reason it is an annotation and not a filter. Expiry (7 days, in
    tools/context_tracker.py) remains the thing that actually removes a thread; an entry
    with no `added` date is legacy data with no age to state, and is left alone.
    """
    from datetime import date as _date

    if not text or not added:
        return text
    try:
        age = (_date.today() - _date.fromisoformat(str(added))).days
    except ValueError:
        return text
    return f"{text} (logged {_relative_age(age)})"


def _intraday_age(written_at: str | None) -> str:
    """
    "just now" / "N minutes ago" / "N hours ago" for a timestamp earlier today, else "".

    [DB-0822-06] Day granularity cannot separate a three-hour-old fact from a three-minute-old
    one, and on 2026-08-27 that was the whole failure: the 07:14 run resolved the Teams link
    and the 10:00 run reported it "still missing". Both writes carry the same date. Only
    today's log needs this — for any earlier day the day count is the honest resolution.
    """
    from datetime import datetime as _dt

    if not written_at:
        return ""
    try:
        when = _dt.fromisoformat(str(written_at))
    except (TypeError, ValueError):
        return ""
    minutes = (_dt.now() - when).total_seconds() / 60
    if minutes < 0:
        return ""
    if minutes < 2:
        return "just now"
    if minutes < 90:
        return f"{int(minutes)} minutes ago"
    return f"{int(minutes // 60)} hours ago"


# `re` is imported as `_re` further down the file, after this block runs at import
# time. Bound here so the patterns below can compile where they are defined rather
# than being deferred into the function that uses them.
import re as _re  # noqa: E402

_WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fourteen": 14,
    "a": 1, "an": 1,
}

_NUM = r"(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fourteen)"

# "Day 3 of 5-day exercise hiatus", "day three of a 5 day break", "day 2 of the 7-day cycle".
_DAY_N_OF_M_RE = _re.compile(
    rf"\bday\s+{_NUM}\s+of\s+(?:an?\s+|the\s+)?{_NUM}[-\s]day\b", _re.IGNORECASE)

# "3 days since the last session", "five days since he called".
_DAYS_SINCE_RE = _re.compile(rf"\b{_NUM}\s+days?\s+since\b", _re.IGNORECASE)


def _as_int(token: str) -> int | None:
    token = (token or "").strip().lower()
    if token.isdigit():
        return int(token)
    return _WORD_NUMBERS.get(token)


def derived_facts(text: str, written_on: str, today=None) -> list[str]:
    """Recompute every date-derived count in `text` as of today.

    [DB-0822-06], the half that was deliberately not built on 2026-08-27 and whose own
    re-open condition then fired. `physical_health` wrote *"Day 3 of 5-day exercise
    hiatus"* into the health log on 2026-08-21. The hiatus ended 2026-08-23 — Mike's own
    journal entry — and later runs kept reading the stored number as if it were current:
    08-30 *"day three of your scheduled exercise hiatus"*, 08-31 *"officially over"* (a
    week late), 09-02 *"officially wraps up today"*. Three wrong states across three days,
    spanning the 09-01 model migration, so this is the carried state and not the model.

    The age annotations built in `cbd5ca3`/`4cc9e3e` date the *line* — "(logged 9 days
    ago)" — and the model repeated the stale count anyway. Dating a sentence is not the
    same as correcting the number inside it. This does the arithmetic instead: a count is
    only ever a claim about a date, so given the date the line was written, the count
    today follows by subtraction and nothing has to be believed.

    Worked on the real case: "Day 3" written on 2026-08-21 puts day 1 at 2026-08-19, so a
    5-day period ran to 2026-08-23 — which is exactly the date Mike's journal records it
    ending. Read on 08-30 this returns "ended 2026-08-23, 7 days ago".

    Deliberately narrow. Only two forms are recognised, both of which are pure arithmetic
    over a stored date: "day N of an M-day X" and "N days since X". Anything needing a
    judgement about whether the thing is still true is not here — that is the filtering
    this item has twice decided against. Returns [] when nothing parses, which is the
    common case and costs one regex scan.
    """
    from datetime import date as _date, timedelta as _td

    if not text or not written_on:
        return []
    try:
        written = _date.fromisoformat(str(written_on)[:10])
    except ValueError:
        return []
    today = today or _date.today()
    if today < written:
        return []

    facts: list[str] = []

    for m in _DAY_N_OF_M_RE.finditer(text):
        n, total = _as_int(m.group(1)), _as_int(m.group(2))
        if not n or not total or n > total:
            continue
        start = written - _td(days=n - 1)
        end = start + _td(days=total - 1)
        position = (today - start).days + 1
        if position > total:
            over = (today - end).days
            facts.append(
                f'"{m.group(0)}" was written on {written.isoformat()}, which puts day 1 '
                f'at {start.isoformat()}. That {total}-day period ENDED on '
                f'{end.isoformat()} — {_relative_age(over)}. It is not running now.')
        else:
            facts.append(
                f'"{m.group(0)}" was written on {written.isoformat()}. As of today it is '
                f'day {position} of {total}, ending {end.isoformat()}.')

    for m in _DAYS_SINCE_RE.finditer(text):
        n = _as_int(m.group(1))
        if n is None:
            continue
        event = written - _td(days=n)
        facts.append(
            f'"{m.group(0)}..." was written on {written.isoformat()}, which puts the '
            f'event on {event.isoformat()}. As of today it is {(today - event).days} '
            f'days since, not {n}.')

    return facts


_DERIVED_HEADER = (
    "[DERIVED FACTS — computed by the system just now, by subtraction from the date each "
    "line was written. These are arithmetic, not anyone's recollection: where one "
    "contradicts a count written in the text above, the line below is correct and the "
    "text is stale. Do not repeat a superseded count to the user.]"
)


def derived_facts_block(entries: list[tuple[str, str]]) -> str:
    """One block for the whole context, from (date_written, text) pairs. "" when nothing
    parses — a persona whose logs carry no derived counts pays nothing for this."""
    lines: list[str] = []
    for written_on, text in entries:
        try:
            lines.extend(derived_facts(text, written_on))
        except Exception as exc:  # noqa: BLE001
            # Context assembly must never fail because a count would not parse.
            logger.warning(f"[context] derived facts failed for {written_on}: {exc}")
    if not lines:
        return ""
    # Same fact written on several days collapses to one line.
    seen: set[str] = set()
    unique = [ln for ln in lines if not (ln in seen or seen.add(ln))]
    return _DERIVED_HEADER + "\n" + "\n".join(f"- {ln}" for ln in unique)


def _render_today_log(entry: dict) -> str:
    """
    Today's log field by field, each with the time it was actually asserted.

    Older days stay a single JSON dump with their day count (shipped in `cbd5ca3`) — the
    extra tokens buy nothing once a value is a day old, and the whole shape change is
    confined here for that reason.

    A field with no recorded write time renders bare, which is what every log file written
    before tools/logger.py started stamping will do. No migration, no missing-data branch
    at any other reader.
    """
    import json as _json

    from tools.logger import _WRITTEN_AT_KEY, _leaf_paths

    stamps = entry.get(_WRITTEN_AT_KEY) or {}
    parts = []
    for path in _leaf_paths(entry):
        value = entry
        for key in path.split("."):
            value = value.get(key) if isinstance(value, dict) else None
        age = _intraday_age(stamps.get(path))
        rendered = _json.dumps(value, ensure_ascii=False)
        parts.append(f"{path}={rendered}" + (f" (recorded {age})" if age else ""))
    return " | ".join(parts)


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
    # (date the text was written, text) — everything a derived count could be hiding in.
    # Open threads are included as well as logs: the thread text is model-authored and
    # carries counts of exactly the same kind.
    derived_sources: list[tuple[str, str]] = []

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
                    _age_annotated(
                        t.get("text", "") if isinstance(t, dict) else str(t),
                        t.get("added") if isinstance(t, dict) else None,
                    )
                    for t in tracker["open_threads"]
                ]
                lines.append("**Open threads:** " + " | ".join(thread_texts))
                for t in tracker["open_threads"]:
                    if isinstance(t, dict) and t.get("added"):
                        derived_sources.append((t["added"], t.get("text", "")))
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
                # [DB-0822-06] The date alone is not age. A log line reads as current state
                # unless something says when it was written, which is how "Day 3 of a 5-day
                # hiatus" written on the 18th was still being read as true on the 21st.
                #
                # Today's log is rendered field by field with the time each value was
                # asserted; every earlier day keeps the single-line dump and its day count.
                # A day-old value has nothing more to say than "yesterday", and the intraday
                # detail on four extra days is tokens on every head-layer call for nothing.
                if i == 0 and entry.get("_written_at"):
                    body = _render_today_log(entry)
                else:
                    entry.pop("_written_at", None)
                    body = _json.dumps(entry, ensure_ascii=False)
                recent_entries.append(f"  {d} ({_relative_age(i)}): {body}")
                derived_sources.append((d, body))
            except Exception:
                pass

    if recent_entries:
        sections.append(
            "## Recent Logs (last 5 days — each line is what was recorded on that date, "
            "not necessarily what is true now)\n" + "\n".join(recent_entries)
        )

    # [DB-0822-06] The line above dates each record; this one corrects the counts inside
    # them. Both are needed — the age annotations went live on 2026-08-27 and the stale
    # "day three of your exercise hiatus" was still being read back on 08-30, 08-31 and
    # 09-02, which is the re-open condition that put this here. Placed after the logs so
    # it reads as a correction to text the model has just seen.
    derived = derived_facts_block(derived_sources)
    if derived:
        sections.append(derived)

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
    # tools.intake added 2026-08-19: queue counts/ages, surface items, and the parked
    # weekly digest. Same contract as the other two — returns "" when quiet, and the
    # digest is delivered exactly once (the block clears it on read). A8 places all
    # three together.
    # tools.confirm added 2026-08-27 [DB-0827-01]: what the user has refused, so the session
    # does not spend a turn arriving at a proposal that tools/confirm.py will not raise, and
    # does not read the absence of a card as licence to ask in prose instead.
    # tools.location added 2026-08-28 [DB-0815-12]: one line naming where the user last
    # reported being — "home since 14:02". It is derived in tools/location.py from the zone
    # transitions log, which has never held a coordinate; raw GPS is extra-sensitive and
    # never enters a prompt, cloud or local. Empty until the user turns the ping on.
    # tools.accountability added 2026-08-29 [DB-0827-09]: the trailing-7d intention
    # follow-through, parked by the Sunday judgment gate and delivered once — counts plus
    # the user's own words for the weekly retrospective to voice, empty every other day.
    # tools.crm_sweep added 2026-08-29 [DB-0827-03]: the nightly capture sweep's pending
    # contact suggestions, with their ledger ids. Empty unless the persona has the sweep
    # on AND a run filed something new, so a quiet night says nothing. The block carries
    # its own delivery instruction — one low-key line, list only on request — because
    # this must fire reliably and the [DB-0822-05]..[DB-0822-09] finding is that an
    # agent file long enough to hold it is an agent file that stops being followed.
    # tools.horizon added 2026-09-03 [DB-0822-09]: findings logistics judged worth the
    # user's attention and the user has NOT yet been told about. The ledger, not this list,
    # is what makes the block safe to deliver unconditionally — see tools/horizon.py on why
    # guaranteed delivery without a record of what was already said is worse than the silent
    # drop it replaces. Empty once everything on file has been raised, which is most turns.
    # tools.turn_referent added 2026-09-03 [DB-0826-01]: what the previous exchange
    # actually did, so a short referring turn has something true to point at. LAST in the
    # list on purpose — it is the most recent thing in the context and must read as more
    # salient than the day logs above it, which is where "undo that merge" went instead.
    # Empty outside a live conversation, so a quiet morning pays nothing.
    for _block_source in ("tools.obligations", "tools.calendar_reconcile", "tools.intake",
                          "tools.confirm", "tools.location", "tools.accountability",
                          "tools.crm_sweep", "tools.horizon", "tools.turn_referent"):
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
        merge_contacts, unmerge_contacts,
        WRITE_CONTACT_SCHEMA, READ_CONTACT_SCHEMA, LIST_CONTACTS_SCHEMA,
        LOG_INTERACTION_SCHEMA, SEARCH_CONTACTS_SCHEMA, MERGE_CONTACTS_SCHEMA,
        UNMERGE_CONTACTS_SCHEMA,
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
    from tools.places import find_places, FIND_PLACES_SCHEMA
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
    from tools.web import fetch_url, FETCH_URL_SCHEMA, fetch_rendered, FETCH_RENDERED_SCHEMA
    # File-based contact import only. import_google_contacts is deliberately NOT
    # registered: the Google Contacts OAuth path was reversed on 2026-08-08 at Mike's
    # direction (7-day refresh-token expiry under Testing publishing status, and the
    # real bug was local validation, not a missing integration). people.googleapis.com
    # is still disabled on the project, so the pull cannot run regardless. The module
    # keeps the function so the path is revivable, not so it is reachable.
    from tools.contacts_import import import_contacts_file, IMPORT_CONTACTS_FILE_SCHEMA
    from tools.mail import read_email, send_email, READ_EMAIL_SCHEMA, SEND_EMAIL_SCHEMA
    # Inbound triage. read_intake_queue is a specialist's view of what intake filed to
    # its domain; teach_intake is the user's correction path, confirmation-gated.
    from tools.intake import (read_intake_queue, teach_intake,
                              READ_INTAKE_QUEUE_SCHEMA, TEACH_INTAKE_SCHEMA)
    # The apply half of the nightly CRM sweep [DB-0827-03]. The sweep itself holds no
    # tools and is not registered here — it is a scheduler job. This is the one tool the
    # pipeline gets: it turns the user's yes/no on parked suggestions into writes, taking
    # ids only, so what lands in the CRM is the row the user read and not a re-statement
    # of it. Granted to `relationships` alone in both routing files.
    from tools.crm_sweep import apply_crm_proposals, APPLY_CRM_PROPOSALS_SCHEMA
    from tools.horizon import record_horizon_item, RECORD_HORIZON_ITEM_SCHEMA

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
        LOG_INTERACTION_SCHEMA, SEARCH_CONTACTS_SCHEMA, MERGE_CONTACTS_SCHEMA,
        UNMERGE_CONTACTS_SCHEMA,
        GET_TONE_SHAPE_SCHEMA,
        WRITE_AGENT_CONFIG_SCHEMA, READ_AGENT_CONFIG_SCHEMA,
        WRITE_WISHES_SCHEMA, READ_WISHES_SCHEMA, GENERATE_EMERGENCY_CARD_SCHEMA,
        OPEN_OBLIGATION_SCHEMA, CLOSE_OBLIGATION_SCHEMA,
        REOPEN_OBLIGATION_SCHEMA, LIST_OBLIGATIONS_SCHEMA,
        READ_INTAKE_QUEUE_SCHEMA, TEACH_INTAKE_SCHEMA,
        READ_CALENDAR_SCHEMA, WRITE_CALENDAR_EVENT_SCHEMA,
        UPDATE_CALENDAR_EVENT_SCHEMA, DELETE_CALENDAR_EVENT_SCHEMA,
        CHECK_CALENDAR_CONFLICTS_SCHEMA,
        GET_WEATHER_SCHEMA, GET_ENVIRONMENTAL_SNAPSHOT_SCHEMA,
        GET_POLLEN_FORECAST_SCHEMA,
        GET_TFL_STATUS_SCHEMA,
        GET_FLIGHT_STATUS_SCHEMA,
        GET_TRAVEL_TIME_SCHEMA,
        GET_REGIONAL_TRANSIT_INFO_SCHEMA,
        FIND_PLACES_SCHEMA,
        WRITE_SCHEDULE_SCHEMA, LIST_SCHEDULES_SCHEMA, DELETE_SCHEDULE_SCHEMA,
        WRITE_QUALITY_EVENT_SCHEMA,
        FETCH_URL_SCHEMA, FETCH_RENDERED_SCHEMA, READ_EMAIL_SCHEMA, SEND_EMAIL_SCHEMA,
        IMPORT_CONTACTS_FILE_SCHEMA,
        APPLY_CRM_PROPOSALS_SCHEMA,
        RECORD_HORIZON_ITEM_SCHEMA,
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
        "apply_crm_proposals": apply_crm_proposals,
        "search_contacts": search_contacts,
        "merge_contacts": merge_contacts,
        "unmerge_contacts": unmerge_contacts,
        "get_tone_shape": get_tone_shape,
        "write_agent_config": write_agent_config,
        "read_agent_config": read_agent_config,
        "fetch_url": fetch_url,
        "fetch_rendered": fetch_rendered,
        "import_contacts_file": import_contacts_file,
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
        "find_places": find_places,
        "write_schedule": write_schedule,
        "list_schedules": list_schedules,
        "delete_schedule": delete_schedule,
        "open_obligation": open_obligation,
        "close_obligation": close_obligation,
        "reopen_obligation": reopen_obligation,
        "list_obligations": list_obligations,
        "read_intake_queue": read_intake_queue,
        "teach_intake": teach_intake,
        "write_quality_event": write_quality_event,
        "record_horizon_item": record_horizon_item,
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


# Tier 4 — verbatim reproduction of the agent's own instructions.
#
# WHY THIS EXISTS. On 2026-08-12 at 00:14 the Synthesizer's entire stored response
# to Mike was its own deliberation, quoting `synthesizer.md` back at him verbatim
# ("An open item that you have already surfaced, and the user has heard, is not
# raised again in later exchanges...") and cut off mid-sentence. All three tiers
# above passed it, correctly by their own logic: they hunt architecture
# *vocabulary* — tool names, agent names, narration frames — and instruction prose
# contains none. It is the system prompt read aloud, which is the most complete
# disclosure this system can make, and it was the one shape nothing looked for.
#
# The signal used here is exactness, not vocabulary: a contiguous run of
# _INSTRUCTION_NGRAM words reproduced verbatim from the agent's own instruction
# file or the constitution is not something a response arrives at by coincidence.
# That makes this tier precise without needing any guess about what leaked prose
# looks like — the failure mode of tier 2, stated in its own docstring.
#
# Scope is deliberately the agent file plus the constitution, and NOT the persona
# files: those carry the user's own words, and quoting the user back to himself is
# ordinary, legitimate behaviour. Including them would fire on correct responses.
_INSTRUCTION_NGRAM = 10

# Tier 5. A response that opens by announcing its own reasoning, e.g.
# "**Step-by-Step Reasoning:**", "My thought process:", "Reasoning:", "Analysis:".
# Optional leading markdown emphasis/heading marks, then the phrase, then a colon —
# the colon is required, because it is what makes this a *header* rather than a
# sentence that happens to begin with the word ("Analysis of your spending suggests…"
# must survive). Anchored at the start of the response by the caller.
_DELIBERATION_OPENER_RE = _re.compile(
    r'^[#*_\s]{0,6}'
    r'(?:step[-\s]?by[-\s]?step\s+)?'
    r'(?:reasoning|analysis|thought\s+process|my\s+thought\s+process|'
    r'internal\s+(?:reasoning|monologue|deliberation)|deliberation|'
    r'thinking\s+(?:it\s+)?through|chain\s+of\s+thought)'
    r'[*_\s]{0,4}:',
    _re.IGNORECASE,
)

# A tool signalling failure in its RETURNED STRING rather than by raising. Anchored to
# the start and requiring the colon, so it matches the convention eight tool files
# already use ("Error: no contact found with id …") and not prose that merely mentions
# an error. See the note beside its use in dispatch_tool().
_TOOL_ERROR_PREFIX_RE = _re.compile(r'^\s*error\s*:', _re.IGNORECASE)


@lru_cache(maxsize=32)
def _instruction_ngrams(agent_name: str) -> frozenset:
    """
    Word n-grams of everything this agent is instructed with, for tier 4.

    Cached per agent: the shingling is O(file) and the files are static for the
    life of the process, so it runs once rather than per response. A missing
    source is skipped rather than raised — an unreadable instruction file must
    narrow this tier's coverage, never break a response on its way to the user.
    The constitution is read for every agent, so a missing agent file still
    leaves that half of the coverage in place.
    """
    grams: set[tuple[str, ...]] = set()
    sources = [ROOT / "config" / "agents" / f"{agent_name}.md",
               ROOT / "config" / "constitution.md"]
    for path in sources:
        try:
            words = _re.findall(r'[0-9a-z]+', _normalise_for_filter(path.read_text()))
        except OSError:
            continue
        for i in range(len(words) - _INSTRUCTION_NGRAM + 1):
            grams.add(tuple(words[i:i + _INSTRUCTION_NGRAM]))
    return frozenset(grams)


def _user_typed_terms(user_text: str | None) -> frozenset:
    """Confidential identifiers the user themselves typed on *this* turn.

    Scope is deliberately three ways narrow, because each widening would hand a
    prober a way to switch off the backstop by asking about it:

    1. **`_ALWAYS_CONFIDENTIAL` only.** `_CONTEXT_SENSITIVE` entries are ordinary
       English words ("relationships", "finance"), so a user mentioning their
       relationships would exempt the term for the whole reply — and tier 3 is
       the only thing standing between "your relationships are improving" and
       "the relationships agent said". Never exempted.
    2. **Tight form only** (`_TIGHT_JOINER`) — the user must have typed the
       identifier, `write_config` or `write-config` or `writeconfig`, not the two
       ordinary words "write config". Spaced prose cannot buy an exemption.
    3. **This turn's user text only.** Nothing is remembered; passing the next
       turn's input recomputes the set from scratch, so an exemption cannot
       outlive the message that earned it.
    """
    if not user_text:
        return frozenset()
    norm = _normalise_for_filter(user_text)
    return frozenset(
        term for term in _ALWAYS_CONFIDENTIAL
        if _term_regex(term, _TIGHT_JOINER).search(norm)
    )


# A reply claiming an action is already done. Deliberately narrow: each pattern needs
# a first-person subject and a completed-action verb, so "I can merge them" and "shall
# I send it?" do not match while "I've merged the records" and "that's done" do. A
# looser pattern would fire on ordinary prose and cost the user a whole reply.
_COMPLETION_CLAIM_RES = [
    _re.compile(p, _re.IGNORECASE) for p in (
        r"\b(?:i(?:'ve| have)|we(?:'ve| have))\s+(?:now\s+)?"
        r"(?:merged|added|created|sent|deleted|removed|updated|saved|renamed|"
        r"unmerged|closed|booked|scheduled)\b",
        # "sent|merged|..." added 2026-09-03: on 2026-08-29 the live reply *"That's
        # sent to Iva."* matched none of these four patterns, so enforce_pending_receipt
        # took the append branch and the user was shown the false claim and its
        # correction stacked together, rather than the correction alone. [DB-0829-01].
        r"\bthat(?:'s| is)\s+(?:all\s+)?(?:done|sorted|taken care of|sent|merged|"
        r"added|created|deleted|removed|updated|saved|booked|scheduled)\b",
        r"\b(?:it(?:'s| is)|they(?:'re| are))\s+(?:now\s+)?"
        r"(?:merged|added|created|sent|deleted|removed|updated|saved|renamed)\b",
        r"\b(?:done|all set)\b[.!]",
    )
]


def _pending_tokens(persona: str | None = None) -> set:
    """Tokens currently awaiting the user's decision. Never raises: a confirmation
    store that cannot be read must not take the session down, and an empty set means
    'nothing new was raised', which leaves the reply exactly as the model wrote it."""
    try:
        from tools.confirm import pending
        return {p["token"] for p in pending(persona)}
    except Exception:  # noqa: BLE001
        return set()


def _pending_raised_since(before: set, persona: str | None = None) -> list[dict]:
    """Confirmations that appeared during this turn — server state, not the model's
    account of what it did."""
    try:
        from tools.confirm import pending
        return [p for p in pending(persona) if p["token"] not in (before or set())]
    except Exception:  # noqa: BLE001
        return []


def enforce_pending_receipt(text: str, new_pending: list[dict]) -> str:
    """
    Stop a reply from reporting a gated action as finished when it is not.

    [DB-0822-03, live 2026-08-26]. `merge_contacts` returned PENDING_CONFIRMATION and
    merged nothing — the gate worked exactly as designed — and the Synthesizer told
    Mike *"That's done. I've merged the records and kept Marcus Whitfield."* five
    seconds later. He believed the merge had happened before he had approved anything.

    That is the mirror of the failure tools/confirm.py calls the worst available
    outcome: a user told an action landed has no reason to approve it, so the approval
    expires unspent at the ten-minute TTL and the action never happens at all. It is
    also the same ask-vs-assert shape as every other item in this cluster, one layer
    up — the model is out of the CONSENT path and was still narrating the RESULT.

    So the report is taken away from it too. `new_pending` is computed by comparing the
    confirmation store before and after the turn, which is server state rather than
    anything the model said, and:

      * a reply that claims completion is REPLACED, on the filter_output precedent —
        a false completion claim is not a cosmetic flaw, it is the user's decision
        being made for them;
      * every other reply keeps its text and gains one deterministic line, so the
        pending action is always visible even when the model forgot to mention it.

    Deliberately NOT an instruction in synthesizer.md: that file is 52KB, its own audit
    named length→adherence as the cause, and six existing rules were ignored on 08-21.
    """
    if not new_pending:
        return text

    actions = ", ".join(sorted({p.get("action", "an action") for p in new_pending}))
    waiting = (f"Waiting for your approval in the app before this happens "
               f"({actions}). Nothing has been changed yet.")

    if any(r.search(text or "") for r in _COMPLETION_CLAIM_RES):
        logger.warning(
            "[pending_receipt] response claimed completion while %s awaited approval "
            "— replaced", actions)
        try:
            from tools.logger import write_quality_event
            write_quality_event(
                event_type="FALSE_COMPLETION_CLAIM",
                detail=f"Synthesizer reported {actions} as done while it was still "
                       f"awaiting user approval; response replaced.",
            )
        except Exception:  # noqa: BLE001
            # Instrumentation must never cost the user the corrected reply.
            pass
        return waiting

    return f"{text.rstrip()}\n\n{waiting}" if text and text.strip() else waiting


# Words a write-only agent would use to record each gated action as having happened.
# Deliberately a closed map keyed on the action name, not a general past-tense
# detector: a phrase is only looked for when THAT action is, at this moment, sitting
# unapproved in the confirmation store. "Sent" in a directive is unremarkable; "sent"
# in a directive while `send_email` is awaiting approval is the [DB-0829-01] failure
# verbatim. Scoping it this way is what keeps it out of the semantic guessing that
# [DB-0827-07] was closed to avoid.
_ACTION_DONE_WORDS: dict[str, tuple[str, ...]] = {
    "send_email": ("sent", "emailed", "has been sent", "was sent"),
    "merge_contacts": ("merged",),
    "unmerge_contacts": ("unmerged", "split"),
    "import_contacts_file": ("imported",),
    "apply_crm_proposals": ("applied", "updated"),
    "write_calendar_event": ("booked", "scheduled", "added to the calendar"),
    "update_calendar_event": ("moved", "rescheduled", "updated"),
    "delete_calendar_event": ("cancelled", "canceled", "deleted", "removed"),
    "teach_intake": ("taught", "added the rule"),
    "write_schedule": ("scheduled",),
    "delete_schedule": ("unscheduled", "deleted", "removed"),
}


def pending_directive_note(directive: str, new_pending: list[dict]) -> tuple[str, bool]:
    """Correct a dispatch directive that describes a gated action as already done.

    [DB-0829-01], live 2026-08-29 and read off the trace on 2026-09-03. Mike asked for
    an email to Iva Diamond at 13:00. `send_email` raised the confirm gate and sent
    nothing; the `relationships` specialist, which watched that happen, logged it
    correctly as *"Initiated outreach ... Pending user approval in the app."* But the
    fire-and-forget Diarist had been dispatched 1.6 seconds into the turn — BEFORE the
    blocking specialist ever called `send_email` — carrying a Coordinator-authored
    directive that read *"Log that user sent an email to Iva Diamond."* It wrote exactly
    that into the day log. Mike declined the send five minutes later.

    So the durable record said an email was sent that never was, and later runs read a
    day log back as fact — the carried-state poison of [DB-0822-06], one layer earlier.

    The Diarist could not have known better: it runs on its own thread with its own
    trace and has no relay back, so nothing it sees contradicts its directive. The
    signal it needs already exists — the confirmation store, which is server state and
    not any model's account of itself. This function is how that signal reaches it.

    Returns `(amended_directive, asserted_done)`. The note is appended in every case, so
    the true state is present whether or not the directive was wrong. `asserted_done`
    reports the narrower fact that the directive actively described a gated action as
    finished; the caller records that as a quality event rather than suppressing the
    dispatch, because suppression would also discard everything ELSE the turn asked to
    be logged, and a lost breakfast is a worse trade than a corrected sentence.
    """
    if not new_pending:
        return directive, False

    lowered = (directive or "").lower()
    asserted = any(
        w in lowered
        for p in new_pending
        for w in _ACTION_DONE_WORDS.get(p.get("action", ""), ())
    )

    described = "; ".join(
        f"{p.get('action', 'an action')} ({p.get('description', '') or 'no description'})"
        for p in new_pending
    )
    note = (
        "\n\n[SYSTEM RECORD — generated from the confirmation store, not by any agent. "
        "The following was requested during this turn and has NOT happened: "
        f"{described}. It is waiting for the user to approve it in the app and they may "
        "still decline it. Nothing has been performed. If anything above describes it as "
        "done, that is wrong: record it as proposed and awaiting the user's approval, "
        "never as completed.]"
    )
    return f"{directive.rstrip()}{note}", asserted


def filter_output(text: str, agent_name: str, user_text: str | None = None) -> str:
    """
    Scan final user-facing output for leaked architecture terms.
    Logs a warning and returns a safe fallback if any are found.
    Only applied to the Synthesizer (user-facing); Coordinator output is
    internal (context package) and does not need filtering.

    Five-tier check (tiers 1 and 3 rebuilt 2026-08-08, roadmap B2 "Output
    filter upgrade — move from keyword matching to regex+semantic"; tier 4
    added 2026-08-15 after a live leak the first three could not see):

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
    4. Verbatim instruction reproduction — a contiguous run of
       _INSTRUCTION_NGRAM words lifted straight from this agent's own
       instruction file or the constitution. Catches the system prompt being
       read aloud, which carries no architecture vocabulary at all and so was
       invisible to tiers 1–3. Always suppressed.

    Detection runs on a normalised copy; the original text is what is returned
    when it passes.

    **Known limits, so nobody over-trusts this.** Tier 2 is pattern-based, not
    a model: a paraphrase phrased outside these frames passes. Intra-token
    spacing (`w r i t e _ c o n f i g`) is not caught — the joiner sits between
    tokens, not inside them — because a matcher loose enough to catch it fires
    on ordinary spaced prose. This filter is the last backstop, not the
    control: the agent confidentiality instructions are.

    **`user_text` — the echo exemption (2026-08-18, `[DB-0808-05]`).** Passing
    the user's own turn lets tier 1 repeat back an identifier *the user typed
    first*. Without it, Exchange 027 (2026-06-26) happened: Mike wrote "I'm
    frustrated that write_config didn't save my preferences" and got the canned
    deflection — the worst possible reply, since a complaint about the system is
    exactly when a real answer is owed, and the identifier was already his.

    The earlier docstring here declined to fix this because "a direct probing
    question would disable its own backstop." That risk is real and is why the
    exemption is scoped as tightly as it is, rather than as a "user asked about
    the system" flag:

    - **Tier 1 only.** Tiers 2, 3 and 4 are untouched. So the reply may name the
      term back; the moment it explains what the term *does* — architecture
      narration, the identifier alongside architecture vocabulary in one
      sentence, or instruction prose quoted verbatim — it is suppressed as
      before. "What does write_config do?" therefore still gets nothing, because
      any answer to it trips tier 2 or tier 3.
    - **Per term**, never a blanket pass: typing one identifier exempts that
      identifier and nothing else.
    - **Single turn.** `user_text` is this turn's input; nothing is stored.

    Omitting `user_text` (the default) reproduces the pre-2026-08-18 behaviour
    exactly, so every existing caller and test is unaffected.
    """
    if agent_name != "synthesizer":
        return text

    exempt = _user_typed_terms(user_text)

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
    # `exempt` holds only identifiers the user typed on this turn; echoing one
    # back is not a disclosure. Tiers 2-4 below still see the whole text.
    for term in _ALWAYS_CONFIDENTIAL:
        if term in exempt:
            continue
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

    # Tier 4 — verbatim instruction reproduction. See _instruction_ngrams above
    # for the 2026-08-12 leak this was built against.
    grams = _instruction_ngrams(agent_name)
    if grams:
        words = _re.findall(r'[0-9a-z]+', norm)
        for i in range(len(words) - _INSTRUCTION_NGRAM + 1):
            span = tuple(words[i:i + _INSTRUCTION_NGRAM])
            if span in grams:
                return _suppress(
                    f"verbatim instruction text {' '.join(span)!r} reproduced"
                )

    # Tier 5 — the response OPENS with a deliberation header.
    #
    # Measured against the live Vertex endpoint 2026-08-18, and it retires the
    # "plumbing fault" hypothesis rather than confirming it. When the model
    # deliberates in prose, that prose arrives in `delta.content` like any other
    # text — the only extra field on the stream is an opaque `thought_signature`.
    # There is no separate reasoning channel being dropped, so **no amount of
    # plumbing upstream can separate deliberation from the answer**; by the time
    # anything can see it, it is the same string. `include_thoughts: False` was
    # tried and does not change it. `thinking_budget: 0` does, by disabling
    # thinking altogether — rejected, because degrading the reasoning of the one
    # user-facing agent to fix a formatting leak is the wrong trade.
    #
    # Tiers 1–4 catch this only by luck: they fire on architecture *vocabulary*,
    # and generic deliberation names nothing. Verified — "**Step-by-Step
    # Reasoning:** 1. Analyze the request... " passes all four untouched and
    # reaches the user. What makes it recognisable is its shape, not its words.
    #
    # Anchored to the *start* deliberately, and matched only as a heading. A
    # numbered list mid-answer is ordinary and legitimate ("here are three
    # options"); a reply that opens by announcing its own reasoning is not
    # something a companion ever has cause to say. That anchoring is what keeps
    # this from suppressing real answers, which is the expensive failure — the
    # user loses their reply entirely.
    if _DELIBERATION_OPENER_RE.match(norm.lstrip()):
        return _suppress("response opens with a deliberation header")

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


def persist_context_block(ctx: dict | None, user_text: str | None = None) -> None:
    """
    Write a parsed [CONTEXT] block to the tracker. Best-effort; never blocks a response.

    `user_text` is the user's own turn, and it is what keeps an open thread alive.
    The Synthesizer re-emits the entire `open_threads` list on every response, so
    its resending a thread says nothing about whether the thread still matters —
    "post-travel recovery" survived two weeks on exactly that. Thread expiry
    therefore keys on the *user* engaging a thread, the same correction `82d394b`
    made to the repeated-instruction protocol: the system's own output is not
    evidence of the user's intent.
    """
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
            user_text=user_text,
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
    # A tool that FAILS GRACEFULLY is still a failure, and until 2026-08-19 the trace
    # recorded it as a success. `ok` was set False in exactly one place — the except
    # above — so it saw crashes and nothing else. Measured on the VM that day: 786
    # tool calls, ONE ok:false, and that one was a missing required argument. Every
    # ordinary failure a user actually hits ("Error: no contact found with id …",
    # "error: no obligation with id …") returned a string and rendered green in the
    # monitoring view. The flag was reporting programming faults while the failures
    # worth watching went unmarked.
    #
    # Found while trying to TEST the flag ([DB-0810-07]): no phrasing turns it red,
    # because every tool checked handles invalid input gracefully by design. That is
    # the tools being well written; it was the flag that was reading the wrong signal.
    #
    # Keyed on the leading token only, and only with the colon attached, because eight
    # tool files already share that convention (grep 'return f?"[Ee]rror' tools/). A
    # looser match — "error" anywhere — would fire on a Research answer that merely
    # discusses one, and a false red is worse than a missed one: it sends someone
    # debugging a call that worked.
    if ok and isinstance(result, str) and _TOOL_ERROR_PREFIX_RE.match(result):
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
            # [DB-0827-01] Thread-local like the trace, and propagated for the same reason:
            # the decline guard fails closed on a thread with no turn, so a worker without
            # this would suppress a re-proposal the user themselves asked for.
            _parent_turn = _turn.current()
            _parent_agent = _tr.get_current_agent()
            _parent_persona = current_persona()
            def _make_dispatch(name, inputs, handlers, turn):
                def _worker():
                    _tr.set_trace(_parent_trace)
                    _tr._set_current_agent(_parent_agent)
                    _turn.adopt(_parent_turn)
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
            # [DB-0827-01] Thread-local like the trace, and propagated for the same reason:
            # the decline guard fails closed on a thread with no turn, so a worker without
            # this would suppress a re-proposal the user themselves asked for.
            _parent_turn = _turn.current()
            _parent_agent = _tr.get_current_agent()
            _parent_persona = current_persona()
            def _make_dispatch(name, inputs, handlers, turn):
                def _worker():
                    _tr.set_trace(_parent_trace)
                    _tr._set_current_agent(_parent_agent)
                    _turn.adopt(_parent_turn)
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


_vertex_location_warned = False


def _vertex_location() -> str:
    """
    Return the Vertex AI location, defaulting to "global".

    The default is deliberately NOT `us-central1`, which is what all three call
    sites defaulted to until 2026-08-20. Gemini 3.x is served only from the global
    endpoint — `docs/INFRASTRUCTURE.md` § Vertex AI credentials records this as
    "us-central1 does not work" — so the old default pointed an unset
    GOOGLE_CLOUD_LOCATION at an endpoint that does not serve the models this project
    runs, and would have failed at call time rather than at startup.

    It never fired, because both hosts set the variable; it was a trap waiting for a
    fresh checkout. Note the value is unrelated to the VM's own `us-central1-a` zone
    and to the two Cloud Functions, which really are regional — the confusion between
    those two layers is why this is a named helper and not an inline default.

    Warns once when unset, because defaulting silently is how a wrong region would go
    unnoticed a second time.
    """
    global _vertex_location_warned
    location = os.environ.get("GOOGLE_CLOUD_LOCATION")
    if location:
        return location
    if not _vertex_location_warned:
        _vertex_location_warned = True
        logger.warning(
            "[vertex] GOOGLE_CLOUD_LOCATION unset — defaulting to 'global'. Set it in "
            ".env: Gemini 3.x is not served from regional endpoints."
        )
    return "global"


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
    location = _vertex_location()
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
    """
    Return (or create) the singleton native genai.Client for Vertex AI.

    Creating it also kicks off the one-shot orphan sweep, on a background thread.
    Hanging the sweep here rather than on each service's startup keeps every
    cache concern inside the _vertex_* helpers, which move to core/providers.py
    together under the A8 split — and covers the dev CLI, which has no startup
    hook at all.
    """
    global _vertex_native_client
    if _vertex_native_client is None:
        from google import genai
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not project:
            return None
        location = _vertex_location()
        _vertex_native_client = genai.Client(vertexai=True, project=project, location=location)
        _start_vertex_cache_sweep(_vertex_native_client)
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


# How long a freshly created or refreshed cache lives. The window is set by the BURST
# SHAPE, not by price: 15 days of call data show bursts of ~16 calls over a median 2
# minutes, p90 10 minutes, separated by 30+ minute gaps. Ten minutes covers the p90
# burst exactly. Price only has to confirm that holding it that long is worth it.
#
# RE-DERIVED 2026-09-01 for the 3.7 Flash / 3.5 Flash-Lite fleet, because the previous
# justification was computed for a Pro cache and Pro left the fleet. Break-even is
# (storage $/M/min) / (read saving $/M), where read saving = input - cached_input:
#
#   3.1 Pro        (was)  0.0417 hits/min   0.417 hits to pay off a 10-min hold
#   3.7 Flash      (now)  0.0247 hits/min   0.247   ← reasoning tier
#   3.7 Flash from 2027   0.0123 hits/min   0.123   ← read price doubles, storage does not
#   3.5 Flash-Lite (now)  0.0617 hits/min   0.617   ← bulk tier
#
# So 10 minutes still pays for itself at well under one cache hit on every model, and
# the reasoning tier got cheaper to hold than it was on Pro. Note the asymmetry that
# makes Flash-Lite the worst row: cache storage is a flat $1.00/1M/hour across every
# Flash-class model, so the cheaper the model's input, the smaller the saving that flat
# fee has to be earned back from. A future move to a still-cheaper bulk model shrinks
# the read saving without shrinking storage — re-run this table before assuming the
# window survives. Rates and the 2027 step live in config/modules/spend_guard.yaml.
_VERTEX_CACHE_TTL_MINUTES = 10
# Refresh only when this much or less is left — so a median burst needs zero
# refresh calls, and a sustained one needs at most one per five minutes.
_VERTEX_CACHE_REFRESH_MARGIN_MINUTES = 5


@lru_cache(maxsize=1)
def _vertex_cache_owner() -> str:
    """
    Identity stamped into every cache's display_name: (host, service role).

    Several processes share one Vertex project — metatron-server and
    metatron-scheduler are separate systemd units with separate registries, and
    a dev machine points at the same project — so a cache has to say who owns it
    before anything is allowed to delete it.

    Deliberately carries NO PID: a PID-keyed identity means a restarted process
    matches nothing it created, which is precisely the orphan the ownership tag
    exists to let a later process reap.
    """
    import socket
    host = socket.gethostname().split(".")[0]
    stem = Path(sys.argv[0]).stem if sys.argv and sys.argv[0] else ""
    role = stem if stem in ("server", "scheduler") else "dev"
    return f"metatron:{host}:{role}"


def _vertex_cache_expiry(now=None):
    """Expiry for a cache created or refreshed at `now` — one full TTL ahead."""
    import datetime
    now = now or datetime.datetime.now(datetime.timezone.utc)
    return now + datetime.timedelta(minutes=_VERTEX_CACHE_TTL_MINUTES)


def _is_cache_not_found(exc: Exception) -> bool:
    """True when an exception is Vertex reporting a missing cached_content."""
    text = str(exc).lower()
    return "not_found" in text or ("404" in text and "cach" in text)


def _evict_vertex_cache(cache_name: str) -> None:
    """Remove a cache name from the registry so the next call rebuilds it."""
    with _vertex_cache_lock:
        for key, (name, _exp) in list(_vertex_cache_registry.items()):
            if name == cache_name:
                _vertex_cache_registry.pop(key, None)


def _refresh_vertex_cache(client, cache_name: str | None, model_name: str = "") -> None:
    """
    Slide a live cache's expiry forward by a full TTL — lazily, after the response.

    Called AFTER a generate call returns and only when the remaining TTL is under
    _VERTEX_CACHE_REFRESH_MARGIN_MINUTES. Refreshing before the call would add a
    synchronous round-trip to every turn of a voice-first system, for a cache
    that in the median burst never needs one.

    The registry tuple is rewritten with the new expiry. Pushing the server-side
    expiry without updating it would leave the validity check in
    _get_or_create_vertex_cache judging a live cache expired and creating a
    second one — a metered creation on every burst, which is the cost this whole
    change exists to remove.

    Any failure evicts instead of raising: a cache that cannot be extended is
    treated exactly like one that vanished, and the next call creates a fresh one.
    """
    if client is None or not cache_name:
        return
    import datetime
    from google.genai import types

    with _vertex_cache_lock:
        entry = next(
            ((k, v[1]) for k, v in _vertex_cache_registry.items() if v[0] == cache_name),
            None,
        )
        if entry is None:
            return
        key, expires_at = entry
        now = datetime.datetime.now(datetime.timezone.utc)
        margin = datetime.timedelta(minutes=_VERTEX_CACHE_REFRESH_MARGIN_MINUTES)
        if now < expires_at - margin:
            return

        new_expiry = _vertex_cache_expiry(now)
        try:
            refreshed = client.caches.update(
                name=cache_name,
                config=types.UpdateCachedContentConfig(expire_time=new_expiry),
            )
        except Exception as e:
            _vertex_cache_registry.pop(key, None)
            logger.info(f"[vertex_cache] refresh failed for {cache_name} ({e}) — evicted, rebuilding on next call")
            return

        _vertex_cache_registry[key] = (cache_name, new_expiry)
        _record_cache_storage(model_name, refreshed, _VERTEX_CACHE_TTL_MINUTES)
        logger.info(f"[vertex_cache] refreshed hash={key} expires={new_expiry.isoformat()}")


def _delete_owned_vertex_caches() -> None:
    """
    Best-effort delete, at interpreter exit, of every cache this process created.

    A TRIM, NOT THE REAPER. systemd stops units with SIGTERM and nothing runs an
    atexit handler on an OOM-kill, a SIGKILL or a hard crash — the exact events
    that orphaned ten Pro caches on 2026-08-19. Correctness rests on the TTL:
    Vertex deletes at expire_time regardless, so the worst an unrun handler costs
    is the tail of one _VERTEX_CACHE_TTL_MINUTES window.
    """
    with _vertex_cache_lock:
        names = [name for name, _exp in _vertex_cache_registry.values()]
        _vertex_cache_registry.clear()
    if not names:
        return
    try:
        client = _get_vertex_native_client()
    except Exception:
        return
    if client is None:
        return
    for name in names:
        try:
            client.caches.delete(name=name)
            logger.info(f"[vertex_cache] deleted {name} at exit")
        except Exception as e:
            logger.info(f"[vertex_cache] exit delete failed for {name} ({e}) — expires within TTL anyway")


def _record_cache_storage(model_name: str, cache, minutes: int) -> None:
    """
    Report a granted storage window to the spend guard. Never raises.

    The token count comes from the cache object Vertex returns rather than from
    a local estimate — the padding added by _pad_for_vertex_cache is part of what
    is stored and therefore part of what is billed.
    """
    try:
        tokens = getattr(getattr(cache, "usage_metadata", None), "total_token_count", 0) or 0
        if not tokens:
            return
        from core.spend_guard import record_cache_storage
        record_cache_storage(model_name, tokens, minutes)
    except Exception as e:
        logger.info(f"[vertex_cache] storage not recorded ({e})")


atexit.register(_delete_owned_vertex_caches)

_vertex_sweep_started = False


def _sweep_orphaned_vertex_caches(client) -> int:
    """
    Delete caches this identity created and then lost the handle to. Returns the count.

    A TIDY-UP, NOT THE FIX. Vertex reaps every cache at expire_time, so the most
    this recovers is the tail of one TTL window on an orphan — worth about
    $0.14/day. The fix is the sliding TTL itself.

    Two rules make it safe, and both matter:

    1. **Own identity only.** metatron-server, metatron-scheduler and any dev
       machine share one Vertex project. A sweep that deleted everything matching
       "our models" would have each process destroying the others' live caches on
       every restart — turning a cost tidy-up into a permanent source of metered
       re-creations.
    2. **Only caches with less than the refresh margin left.** Under the sliding
       scheme a cache whose owner is alive is refreshed back to a full TTL before
       it drops below that margin; one whose owner died stops being refreshed and
       decays. Age since creation cannot make this distinction — a long-lived
       refreshed cache looks old and is in use — which is why the expiry is what
       is read. The cost of being wrong is one metered re-creation, never a
       user-visible failure.

    Listing happens in whatever location the client was configured for, which
    this deployment sets to `global` via GOOGLE_CLOUD_LOCATION — never a
    hardcoded region. Caches created before this change carry no display_name,
    so no owner matches them and they are left alone; the one-time cleanup for
    those is `scripts/vertex_cache_admin.py --delete-all`, run once at rollout.
    """
    import datetime

    owner = _vertex_cache_owner()
    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff = now + datetime.timedelta(minutes=_VERTEX_CACHE_REFRESH_MARGIN_MINUTES)
    with _vertex_cache_lock:
        live = {name for name, _exp in _vertex_cache_registry.values()}

    deleted = 0
    try:
        entries = list(client.caches.list())
    except Exception as e:
        logger.info(f"[vertex_cache] sweep could not list caches ({e}) — skipped")
        return 0

    for entry in entries:
        name = getattr(entry, "name", None)
        if not name or name in live:
            continue
        if getattr(entry, "display_name", None) != owner:
            continue
        expire_time = getattr(entry, "expire_time", None)
        if expire_time is not None and expire_time > cutoff:
            continue
        try:
            client.caches.delete(name=name)
            deleted += 1
            logger.info(f"[vertex_cache] swept orphan {name} (owner={owner})")
        except Exception as e:
            logger.info(f"[vertex_cache] sweep could not delete {name} ({e})")
    return deleted


def _start_vertex_cache_sweep(client) -> None:
    """
    Run the orphan sweep once per process, off the request path.

    On a background thread because it is a list plus N deletes against Vertex,
    and the caller is a session about to talk to the user — a tidy-up worth
    cents may not add a round-trip to a voice turn.
    """
    global _vertex_sweep_started
    with _vertex_cache_lock:
        if _vertex_sweep_started:
            return
        _vertex_sweep_started = True

    def _run() -> None:
        try:
            _sweep_orphaned_vertex_caches(client)
        except Exception as e:
            logger.info(f"[vertex_cache] sweep failed ({e}) — caches still expire on their own")

    threading.Thread(target=_run, name="vertex-cache-sweep", daemon=True).start()


def _get_or_create_vertex_cache(
    client, system_prompt: str, model_name: str,
    tool_schemas: list[dict] | None = None,
) -> str | None:
    """
    Return the Vertex CachedContent name for this (system_prompt, tools) pair.

    Tools are baked into the cache so the request body can stay clean — Vertex
    rejects requests that include both cached_content and tools/system_instruction.
    The cache key includes tool names so different tool sets get separate caches.

    Expire time: a sliding _VERTEX_CACHE_TTL_MINUTES window, extended by
    _refresh_vertex_cache after a response when little of it is left. Storage is
    billed per wall-clock hour, so the window is sized to a burst of calls, not
    to the config-change cadence it used to match.

    Returns None on any failure (model doesn't support caching, content too short, etc.).
    The caller falls back to uncached generation.

    Held under _vertex_cache_lock end to end: the creation call takes seconds, and
    a second thread arriving inside that window must wait for the name rather than
    create a duplicate that nothing will ever delete.
    """
    import datetime
    import hashlib
    from google.genai import types

    # Kill switch for development. A dev machine restarts constantly and gets
    # roughly one hit per run, so it pays creation and a storage window for a
    # cache that is read once — the worst shape caching has. Gated here rather
    # than at the call sites because both of them already treat None as "run
    # uncached", so one gate covers the blocking and the streaming paths.
    if os.environ.get("VERTEX_CACHE_DISABLED", "").strip().lower() in ("1", "true", "yes"):
        return None

    tool_key = ":".join(s["name"] for s in (tool_schemas or []))
    content_hash = hashlib.sha256(f"{model_name}:{system_prompt}:{tool_key}".encode()).hexdigest()[:16]

    with _vertex_cache_lock:
        entry = _vertex_cache_registry.get(content_hash)
        if entry is not None:
            cached_name, expires_at = entry
            # 60s margin so a cache cannot expire between this check and the request.
            if datetime.datetime.now(datetime.timezone.utc) < expires_at - datetime.timedelta(seconds=60):
                return cached_name
            _vertex_cache_registry.pop(content_hash, None)
            logger.info(f"[vertex_cache] expired hash={content_hash} — recreating")

        try:
            expires_at = _vertex_cache_expiry()
            gemini_tools = _to_gemini_tools(tool_schemas or [])
            cache_config = types.CreateCachedContentConfig(
                system_instruction=_pad_for_vertex_cache(system_prompt),
                expire_time=expires_at,
                display_name=_vertex_cache_owner(),
                **({"tools": gemini_tools} if gemini_tools else {}),
            )
            cache = client.caches.create(model=model_name, config=cache_config)
            _vertex_cache_registry[content_hash] = (cache.name, expires_at)
            _record_cache_storage(model_name, cache, _VERTEX_CACHE_TTL_MINUTES)
            _trace(f"[VERTEX_CACHE] created {cache.name} expires={expires_at.isoformat()}")
            logger.info(f"[vertex_cache] created model={model_name} hash={content_hash} expires={expires_at.isoformat()}")
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
    location = _vertex_location()
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
    elif search_queries:
        # The model searched and got nothing back, then answered anyway. WITHHOLD the
        # answer — do not merely label it.
        #
        # Labelling was the 2026-08-10 fix and it is not enough, proven live on
        # 2026-08-18: asked for the Southeastern line into London Bridge, two searches
        # returned zero sources, and this function handed the Synthesizer a fabricated
        # "good service overall" carrying the [RETRIEVAL: NONE] marker below. The
        # Synthesizer read the marker and *softened* rather than refused — "though I
        # don't have live confirmation on that right this minute" — which reads as a
        # caveat about staleness, implying a real status exists. Mike would have walked
        # to the station. A marker in prose is a suggestion to a model; the standing rule
        # here is that a guarantee lives in Python, so the body does not survive.
        #
        # SCOPED ON `search_queries`, DELIBERATELY, and this is the load-bearing part.
        # Zero sources with zero queries is a general-knowledge question the model
        # correctly answered from what it knows ("how should I structure a budget") —
        # untouched, because suppressing that would gut Research for no safety gain. A
        # query having been issued is the model's own judgement that the question needed
        # live checking; failing that check is what makes its answer inadmissible.
        # That distinction is already why _log_ungrounded_answer() counts the two apart.
        #
        # The replacement is a DIRECTIVE, not prose to be paraphrased: there is no
        # fabricated content left to soften, so the Synthesizer has nothing to hedge
        # with. It also supplies the refusal wording Mike asked for on 2026-08-18 —
        # say what he cannot have and why, without naming any mechanism
        # (CLAUDE.md § Discretion). ROADMAP.md § B4 owns the general case.
        _q = len(search_queries)
        logger.warning(
            f"[research_grounding] WITHHELD an unsourced answer — {_q} search(es), 0 sources. "
            f"Query: {user_input[:120]}"
        )
        _trace(f"[RESEARCH] withheld: {_q} search(es) returned no sources")
        text = (
            "RETRIEVAL FAILED — NO ANSWER IS AVAILABLE.\n"
            f"{_q} live search(es) were issued for this question and returned no usable "
            "sources, so there is nothing to report and nothing below to summarise.\n\n"
            "Tell the user plainly that you could not get current information on this, "
            "and what that means for them — that they will need to check it themselves. "
            "Do NOT state, estimate, hedge, or imply any answer to the original question: "
            "no status, no figure, no 'it appears', no 'as of my last information'. "
            "A softened guess is the failure this replaces. Name no mechanism, no tool "
            "and no source — say what is unavailable, not why in architectural terms."
        )
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
                               history: list[dict] | None = None,
                               attachments: list[dict] | None = None,
                               thinking_budget: int | None = None) -> str:
    """
    Gemini session with Vertex context caching via the native SDK.

    On the first call for a given system prompt, creates a Vertex CachedContent object
    on a sliding _VERTEX_CACHE_TTL_MINUTES expiry and stores the name in
    _vertex_cache_registry. Subsequent calls for the same prompt hit the cache — the
    system prompt tokens are not re-billed or re-processed at full cost — and the expiry
    is slid forward after the response, never before it (_refresh_vertex_cache).

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
        result = _run_gemini_native_loop(
            client, model_name, system_prompt, user_input,
            tool_schemas, tool_handlers,
            history=history,
            cached_content=cached_content_name,
            attachments=attachments,
            thinking_budget=thinking_budget,
        )
        _refresh_vertex_cache(client, cached_content_name, model_name)
        return result
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
                result = _run_gemini_native_loop(
                    client, model_name, system_prompt, user_input,
                    tool_schemas, tool_handlers,
                    history=history,
                    cached_content=fresh,
                    attachments=attachments,
                )
                _refresh_vertex_cache(client, fresh, model_name)
                return result
            except Exception as retry_exc:
                e = retry_exc

        logger.warning(f"[vertex_cache] native loop failed ({e}) — falling back to compat")
        log_model_error(_agent, "gemini-cached", model_name, f"native loop failed, fell back to compat: {e}")
        return run_session_gemini(system_prompt, user_input, tool_schemas, tool_handlers, model, history)


def _history_attachment_note(attachments: list[dict] | None) -> str:
    """The trace of an attachment that survives into later turns — its name, not its bytes."""
    if not attachments:
        return ""
    return " [attached: " + ", ".join(a["name"] for a in attachments) + "]"


def _gemini_user_parts(types, user_input: str, attachments: list[dict] | None) -> list:
    """
    Build the parts of the user's turn: attached file bytes first, then the text.

    Files lead deliberately. The instruction that accompanies them is nearly always
    *about* them ("what is this?", "read this and tell me the date"), and a question
    placed after the thing it refers to needs no antecedent resolving.

    Attachments ride in the per-turn content, never in the cached content — the
    Vertex cache is keyed on the system prompt and tool schemas, so a file here
    cannot disturb it (see _get_or_create_vertex_cache).
    """
    parts = [
        types.Part.from_bytes(data=data, mime_type=mime)
        for data, mime in attachments_mod.load_parts(attachments or [])
    ]
    parts.append(types.Part(text=user_input))
    return parts


# Thinking cap for the Synthesizer — insurance, not economy ([DB-0827-02], decided
# 2026-08-27). The probe (archive/plans/synthesizer_thinking_probe_2026-08-27.md)
# measured 105 live replies: max observed thinking was 3,930 tokens with no tail
# above it, so 4096 clips nothing today and costs quality nothing. What it buys is
# a bound: before this, no thinking_config existed anywhere in the codebase and
# max_output_tokens does NOT limit thinking on Gemini — a regression toward
# runaway thinking would have billed silently at $12/M. Do not lower this for
# cost; the probe measured the whole exposure at ~$0.26/day. A latency-motivated
# cap (1,024–1,536) would touch 60–85% of replies and is a quality experiment,
# not a config edit.
_SYNTH_THINKING_BUDGET = 4096


def _note_thinking_cap_hit(thinking_budget: int | None, thinking_tokens: int,
                           turn_num: int) -> None:
    """
    Record a quality event when a reply's thinking lands at the cap.

    The probe said the tail does not exist — so a cap hit is exactly the case
    worth a record: either the distribution moved or a pathological reply was
    clipped, and both deserve a human look. The 64-token margin exists because a
    clipped run reports a count at or just under the budget, not exactly on it.
    Never raises: a telemetry write must not take down a live reply.
    """
    if not thinking_budget or thinking_tokens < thinking_budget - 64:
        return
    try:
        from tools.logger import write_quality_event
        rec = _tr.get_current_agent()
        agent = getattr(rec, "agent", "") or "unknown"
        write_quality_event(
            "THINKING_CAP_HIT",
            source_agent=agent,
            detail=(f"thinking hit the {thinking_budget}-token budget "
                    f"(reported {thinking_tokens}, turn {turn_num}). The 2026-08-27 "
                    f"probe found no replies above 3,930 — a cap hit means the "
                    f"distribution moved or a reply was clipped; check its quality."),
        )
        logger.warning(f"[thinking_cap] {agent} hit budget={thinking_budget} "
                       f"reported={thinking_tokens} turn={turn_num}")
    except Exception:
        logger.warning("[thinking_cap] failed to record cap-hit quality event", exc_info=True)


def _run_gemini_native_loop(client, model_name: str,
                             system_prompt: str, user_input: str,
                             tool_schemas: list[dict], tool_handlers: dict,
                             history: list[dict] | None = None,
                             max_iterations: int = 8,
                             cached_content: str | None = None,
                             attachments: list[dict] | None = None,
                             thinking_budget: int | None = None) -> str:
    """
    Agentic loop using the google-genai native SDK.

    Replicates _openai_compat_loop behaviour for the Gemini path: multi-turn
    contents list, tool dispatch (sequential + parallel for _PARALLEL_TOOLS),
    token budget logging, and AI_TRACE markers.

    cached_content: Vertex CachedContent resource name. When provided, the system
    prompt is served from cache — system_instruction is omitted from GenerateContentConfig.

    thinking_budget: per-request thinking-token cap (types.ThinkingConfig). Rides
    the request, not the cache — it cannot split or invalidate a cache entry.
    """

    # The schemas handed to this runner are already filtered to what this
    # agent was granted, so they double as the permission set — no separate
    # lookup, and no way for the two to drift apart.
    _allowed_names = {s['name'] for s in tool_schemas} if tool_schemas else set()
    from google.genai import types

    gemini_tools = _to_gemini_tools(tool_schemas)
    _tools_kwarg = {"tools": gemini_tools} if gemini_tools else {}
    # Per-request generation setting — unlike tools/system_instruction it is NOT
    # baked into the cache, so it applies identically on both branches below.
    _think_kwarg = (
        {"thinking_config": types.ThinkingConfig(thinking_budget=thinking_budget)}
        if thinking_budget is not None else {}
    )
    if cached_content:
        # Tools and system_instruction are baked into the cache — must not repeat them here.
        config = types.GenerateContentConfig(
            cached_content=cached_content,
            max_output_tokens=4096,
            **_think_kwarg,
        )
    else:
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=4096,
            **_tools_kwarg,
            **_think_kwarg,
        )

    contents: list = []
    if history:
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))
    contents.append(types.Content(role="user", parts=_gemini_user_parts(types, user_input, attachments)))

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
            _note_thinking_cap_hit(thinking_budget, thinking_tokens, turn_num)
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
                                   output_text="\n".join(text_parts), cached_tokens=cache_read)

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
            # [DB-0827-01] Thread-local like the trace, and propagated for the same reason:
            # the decline guard fails closed on a thread with no turn, so a worker without
            # this would suppress a re-proposal the user themselves asked for.
            _parent_turn = _turn.current()
            _parent_agent = _tr.get_current_agent()
            _parent_persona = current_persona()
            def _make_gemini_dispatch(fc_name, fc_args, handlers, turn):
                def _worker():
                    _tr.set_trace(_parent_trace)
                    _tr._set_current_agent(_parent_agent)
                    _turn.adopt(_parent_turn)
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


def _run_gemini_native_stream(client, model_name: str,
                              system_prompt: str, user_input: str,
                              tool_schemas: list[dict], tool_handlers: dict,
                              history: list[dict] | None = None,
                              max_iterations: int = 8,
                              cached_content: str | None = None,
                              attachments: list[dict] | None = None,
                              thinking_budget: int | None = None) -> Iterator[str]:
    """
    Streaming sibling of _run_gemini_native_loop — Option A of the 2026-08-18 caching fix.

    Yields text as it arrives while keeping `cached_content`, which is the combination
    the interactive path could not previously have: it streamed by opting out of the
    cache, or cached by giving up the stream.

    **No blocking replay, unlike _openai_compat_stream — measured, not assumed.**
    That function re-issues each tool turn non-streaming purely to obtain a Vertex
    `thought_signature`, because OpenAI-compat stream deltas carry none. The native
    SDK does: a streamed `function_call` part arrives with its signature attached
    (probed 2026-08-18, 6,330 bytes on a live call), so the accumulated turn is
    appended directly and the extra round trip does not exist here. **If a
    thought_signature 400 ever appears on this path, that premise is what broke** —
    check the parts being appended before looking anywhere else.

    Two behaviours deliberately match _openai_compat_stream rather than
    _run_gemini_native_loop, because this replaces the former on the user's path:
    text from a tool-call turn is yielded as it arrives (the blocking loop discards
    all but the final turn's text, which a stream cannot do — nothing can be
    un-yielded), and the caller sees one concatenated stream.

    Time-to-first-token is dominated by thinking, not by this function: 14.89s of a
    19.78s generation elapsed before the first delta on a live probe. Streaming
    shortens no silence; it lets the answer arrive progressively once it starts.
    """
    _allowed_names = {s['name'] for s in tool_schemas} if tool_schemas else set()
    from google.genai import types

    gemini_tools = _to_gemini_tools(tool_schemas)
    # Per-request setting, not part of the cache — see _run_gemini_native_loop.
    _think_kwarg = (
        {"thinking_config": types.ThinkingConfig(thinking_budget=thinking_budget)}
        if thinking_budget is not None else {}
    )
    if cached_content:
        # Tools and system_instruction are baked into the cache — must not repeat them.
        config = types.GenerateContentConfig(
            cached_content=cached_content,
            max_output_tokens=4096,
            **_think_kwarg,
        )
    else:
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=4096,
            **({"tools": gemini_tools} if gemini_tools else {}),
            **_think_kwarg,
        )

    contents: list = []
    if history:
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))
    contents.append(types.Content(role="user", parts=_gemini_user_parts(types, user_input, attachments)))

    cumulative_input_tokens = 0
    result = ""

    for turn_num in range(1, max_iterations + 1):
        _trace(f"[API] gemini-native-stream/{model_name}  turn={turn_num}  streaming...")

        function_calls = []
        fc_parts: list = []
        text_parts: list[str] = []
        usage = None

        for chunk in client.models.generate_content_stream(
            model=model_name, contents=contents, config=config,
        ):
            if getattr(chunk, "usage_metadata", None):
                usage = chunk.usage_metadata
            if not chunk.candidates:
                continue
            cand_content = chunk.candidates[0].content
            if cand_content is None or not cand_content.parts:
                continue
            for part in cand_content.parts:
                if getattr(part, "function_call", None):
                    function_calls.append(part.function_call)
                    fc_parts.append(part)   # keep the ORIGINAL part — it carries the signature
                elif getattr(part, "text", None):
                    text_parts.append(part.text)
                    yield part.text

        if usage is not None:
            input_tokens = getattr(usage, "prompt_token_count", 0) or 0
            output_tokens = getattr(usage, "candidates_token_count", 0) or 0
            thinking_tokens = _thinking_tokens_gemini(usage)
            _note_thinking_cap_hit(thinking_budget, thinking_tokens, turn_num)
            cache_read = getattr(usage, "cached_content_token_count", 0) or 0
            cumulative_input_tokens += input_tokens
            _cache_suffix = f" cache_read={cache_read}" if cache_read else ""
            if cumulative_input_tokens > 8000:
                logger.warning(f"[token_budget] OVER_8K turn={turn_num} cumulative_input={cumulative_input_tokens}{_cache_suffix}")
                _trace(f"[TOKEN] turn={turn_num} input={input_tokens} cumulative={cumulative_input_tokens}{_cache_suffix} ⚠ OVER_8K")
            else:
                logger.info(f"[token_budget] turn={turn_num} cumulative_input={cumulative_input_tokens}{_cache_suffix}")
                _trace(f"[TOKEN] turn={turn_num} input={input_tokens} cumulative={cumulative_input_tokens}{_cache_suffix}")
            _tr.record_turn_tokens(_tr.get_current_agent(), turn_num, input_tokens, output_tokens,
                                   thinking_tokens, output_text="".join(text_parts),
                                   cached_tokens=cache_read)

        if text_parts:
            result = "".join(text_parts)

        if not function_calls:
            if history is not None:
                history.append({"role": "user", "content": user_input})
                history.append({"role": "assistant", "content": result})
            return

        # Rebuild the assistant turn: original function-call parts (signatures intact),
        # plus the streamed text collapsed into one part.
        model_parts = ([types.Part(text="".join(text_parts))] if text_parts else []) + fc_parts
        contents.append(types.Content(role="model", parts=model_parts))

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
            # [DB-0827-01] Thread-local like the trace, and propagated for the same reason:
            # the decline guard fails closed on a thread with no turn, so a worker without
            # this would suppress a re-proposal the user themselves asked for.
            _parent_turn = _turn.current()
            _parent_agent = _tr.get_current_agent()
            _parent_persona = current_persona()
            def _make_gemini_dispatch(fc_name, fc_args, handlers, turn):
                def _worker():
                    _tr.set_trace(_parent_trace)
                    _tr._set_current_agent(_parent_agent)
                    _turn.adopt(_parent_turn)
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


def run_session_gemini_cached_stream(system_prompt: str, user_input: str,
                                     tool_schemas: list[dict], tool_handlers: dict,
                                     model: str | None = None,
                                     history: list[dict] | None = None,
                                     attachments: list[dict] | None = None,
                                     thinking_budget: int | None = None) -> Iterator[str]:
    """
    Streaming entry point for the cached Vertex path — mirrors run_session_gemini_cached.

    Falls back to the uncached OpenAI-compat stream when not on Vertex, when the native
    client is unavailable, or when the native stream fails **before yielding anything**.

    **A fallback loses the attached files, and that is the intended degradation.** The
    compat path takes text only, but the description of the attachments is part of the
    text (core/attachments.describe_for_prompt), so the model knows files were sent and
    can say it could not open them — which beats both a crash and a confident answer
    about a picture nothing looked at.

    **The fallback is deliberately not attempted once a chunk has been emitted.** A
    replay after partial delivery would repeat text the user has already seen and re-run
    any tool whose side effect had landed — the failure mode the non-streaming path
    accepts (it replays a whole turn) but which a stream cannot, because the first half
    is already gone. Past that point the exception propagates and the caller's normal
    error handling takes it.
    """
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    client = _get_vertex_native_client() if project else None
    if client is None:
        api_key, base_url, model_name = _resolve_gemini_credentials(model)
        yield from _openai_compat_stream(
            system_prompt, user_input, tool_schemas, tool_handlers,
            api_key=api_key, base_url=base_url, model=model_name, history=history,
        )
        return

    model_name = (model or GEMINI_PRO_MODEL)
    if model_name.startswith("models/"):
        model_name = model_name[len("models/"):]

    cached_content_name = _get_or_create_vertex_cache(client, system_prompt, model_name, tool_schemas)

    emitted = False
    try:
        for chunk in _run_gemini_native_stream(
            client, model_name, system_prompt, user_input,
            tool_schemas, tool_handlers,
            history=history, cached_content=cached_content_name,
            attachments=attachments,
            thinking_budget=thinking_budget,
        ):
            emitted = True
            yield chunk
        _refresh_vertex_cache(client, cached_content_name, model_name)
    except Exception as e:
        # A cache can vanish before its recorded expiry, and under a sliding
        # ten-minute TTL that race is ~150x more likely than it was under the
        # midnight scheme. The blocking path has always evicted here; this one
        # did not, so a dead name stayed in the registry and every later call
        # fell through to the uncached compat path for the process lifetime.
        if cached_content_name and _is_cache_not_found(e):
            _evict_vertex_cache(cached_content_name)
            logger.info(f"[vertex_cache] {cached_content_name} not found on stream — evicted, rebuilding next call")
        if emitted:
            raise
        from core.router import log_model_error
        _agent = _tr.get_current_agent() or "unknown"
        logger.warning(f"[vertex_cache] native stream failed before first chunk ({e}) — falling back to compat")
        log_model_error(_agent, "gemini-cached-stream", model_name,
                        f"native stream failed pre-emission, fell back to compat: {e}")
        api_key, base_url, compat_model = _resolve_gemini_credentials(model)
        yield from _openai_compat_stream(
            system_prompt, user_input, tool_schemas, tool_handlers,
            api_key=api_key, base_url=base_url, model=compat_model, history=history,
        )


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

    # Vertex (and AI Studio) validate a thought_signature on the function-call
    # parts of their *own* prior assistant turns and 400 the whole request when one
    # is missing. OpenAI and Ollama do not, and an unsigned tool-call message has
    # always been valid there. The guard below therefore fires on the Google
    # endpoints only, so the two paths that never had the bug keep byte-identical
    # behaviour. Same predicate as _openai_compat_loop's _provider_label.
    _signature_required = bool(base_url and "googleapis" in base_url)

    # DB-0810-12 instrumentation. Every assistant tool-call message this loop puts
    # into `messages` without a Vertex thought_signature is recorded here as
    # "pos=<index>:turn=<n>:src=<branch>:tools=<names>". Vertex's 400 names the
    # *position* of the offending message (position 12 in all four captured
    # occurrences), so position is the correlating key — the ledger is replayed
    # into the failure log below, which lets one future occurrence say whether the
    # message Vertex rejected is one this loop wrote unsigned, and from which branch.
    #
    # A `:neutralized` suffix on a src means the branch was reached but the turn was
    # written signature-free instead (see _record_unsignable_turn) — so no
    # function-call part exists at that position and a Vertex 400 quoting it is
    # *not* this loop's doing. The ledger entry is kept precisely so that stays
    # observable rather than assumed: the branch is rare, and deleting its only
    # record the moment it stopped being fatal would make the next occurrence
    # unattributable all over again.
    _unsigned_appends: list[str] = []

    def _note_unsigned(src: str, pos: int, turn: int, names) -> None:
        entry = (f"pos={pos}:turn={turn}:src={src}"
                 f":tools={','.join(sorted(n for n in names if n)) or 'none'}")
        _unsigned_appends.append(entry)
        # WARNING, not INFO: this is the branch under investigation and it is rare
        # by construction, so it cannot flood a live conversation's logs.
        #
        # The agent's NAME, never the record. Interpolating the AgentRecord itself
        # prints its dataclass repr, and `context_sections` inside it holds the
        # fully assembled system prompt — the agent file, the constitution and the
        # persona config. One occurrence on 2026-08-15 wrote all of it to
        # journalctl in plain text, where it is retained by systemd and readable by
        # anyone with journal access. Sensitive-tier content does not go to logs.
        _probe_rec = _tr.get_current_agent()
        logger.warning(f"[signature_probe] unsigned_assistant_appended {entry} "
                       f"agent={getattr(_probe_rec, 'agent', 'unknown')} model={model}")

    def _record_unsignable_turn(text: str, ran: list[str]) -> None:
        """Write a tool-call turn into `messages` with no function-call parts.

        DB-0810-12's remedy. Two branches below can end up holding tool calls that
        Vertex has not signed — a message rebuilt from stream deltas (which carry no
        signature at all) and, in principle, a blocking replay that hands back
        unsigned calls. Sending either back produces the 400 that loses the user's
        whole exchange, which is the reported harm.

        The signature is only ever demanded of *function-call content blocks*. So
        the turn is recorded as ordinary text instead: an assistant message with no
        `tool_calls`, then a user message naming the tools that already ran. There is
        nothing left for Vertex to validate, the conversation continues to its final
        turn, and the user gets an answer.

        Three alternatives were weighed and rejected:
          * porting `_openai_compat_loop`'s tc0-only workaround — it re-requests the
            remaining calls one per turn, which serialises this loop's parallel
            dispatch and is a documented regression;
          * dropping the turn from `messages` — the model re-issues the same calls
            and the side effects run again, up to max_iterations times;
          * retrying the blocking call — speculative, costs a full round trip, and
            the divergence that caused it is not known to be transient.

        No fidelity is lost relative to what this loop already did: every tool
        result it appends is `content: ""`, so the model has never seen tool output
        on this path — only the fact that the calls happened, which is preserved.
        """
        messages.append({
            "role": "assistant",
            "content": text or "(Requested the listed tools; awaiting their results.)",
        })
        messages.append({
            "role": "user",
            "content": ("[tool results]\n"
                        + "\n".join(f"- {n}: done" for n in ran or ["(none)"])
                        + "\n\nThese have already run. Do not request them again — "
                          "continue and give your answer."),
        })

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
            else:
                # model_copy preserves Vertex's signed extra_content while reducing
                # tool_calls to tc0 — the only one the parallel-call bug signs.
                _signed = blocking_msg.model_copy(update={"tool_calls": [blocking_msg.tool_calls[0]]})
            # Judge the message that will *actually be appended*, not the raw response: in
            # the parallel case only tc0 is signed (the known Vertex bug) and the copy
            # is reduced to tc0, so the raw response would read "signed=1/2" every time
            # and bury the real signal in expected noise.
            #
            # The check now runs *before* the append rather than after it. The replay
            # is the mitigation itself, and nothing had ever verified that it returns
            # signed calls — so on the endpoints that demand a signature, an unsigned
            # replay takes the same signature-free route as the delta fallback instead
            # of being appended and merely noted. (Ordering only: `dispatch_tool` never
            # reads `messages`, so moving the append past it changes nothing observable.)
            _sig_state = _thought_signature_state(_signed)
            _unsignable = _signature_required and _sig_state != "signed"
            if _sig_state != "signed":
                _note_unsigned(f"blocking_replay[{_sig_state}]"
                               + (":neutralized" if _unsignable else ""),
                               len(messages), turn_num,
                               [tc.function.name for tc in _signed.tool_calls])
            _ran: list[str] = []
            for tc in _signed.tool_calls:
                inputs = json.loads(tc.function.arguments)
                dispatch_tool(tc.function.name, inputs, tool_handlers, _turn_num=turn_num, _allowed=_allowed_names)
                _ran.append(tc.function.name)
            if _unsignable:
                _record_unsignable_turn(blocking_msg.content or "".join(text_parts), _ran)
            else:
                messages.append(_signed)
                messages.append({"role": "tool", "tool_call_id": _signed.tool_calls[0].id, "content": ""})
        else:
            # Blocking replay didn't produce tool calls — fall back to the stream-based
            # reconstruction (rare; means the two calls diverged).
            reconstructed = [
                {"id": tool_calls_raw[i]["id"], "type": "function",
                 "function": {"name": tool_calls_raw[i]["name"], "arguments": tool_calls_raw[i]["arguments"]}}
                for i in sorted(tool_calls_raw)
            ]
            # DB-0810-12, evidenced 2026-08-15 (`src=stream_delta_fallback`, pos=12):
            # this is the branch that lost the exchange. The dict is unsigned by
            # construction — stream deltas carry no thought_signature and the replay
            # produced nothing to take one from — so where a signature is demanded the
            # turn is recorded signature-free instead of being sent back as a
            # function-call part. Elsewhere (OpenAI, Ollama) the original reconstruction
            # is still valid and still used.
            _unsignable = _signature_required
            _note_unsigned("stream_delta_fallback" + (":neutralized" if _unsignable else ""),
                           len(messages), turn_num,
                           [t.get("name") for t in tool_calls_raw.values()])
            if not _unsignable:
                messages.append({"role": "assistant", "content": "".join(text_parts) or None,
                                 "tool_calls": reconstructed})
            _ran = []
            for tc in reconstructed:
                inputs = json.loads(tc["function"]["arguments"])
                dispatch_tool(tc["function"]["name"], inputs, tool_handlers, _turn_num=turn_num, _allowed=_allowed_names)
                _ran.append(tc["function"]["name"])
                if not _unsignable:
                    messages.append({"role": "tool", "tool_call_id": tc["id"], "content": ""})
            if _unsignable:
                _record_unsignable_turn("".join(text_parts), _ran)

    # Fallback: max iterations reached
    if history is not None:
        history.append({"role": "user", "content": user_input_display or user_input})
        history.append({"role": "assistant", "content": ""})


# Head-layer agents receive full config + recent context.
# All other agents (specialists) receive goals.yaml only; context arrives via directive.
_HEAD_LAYER_AGENTS = {"synthesizer"}
_ROUTING_LAYER_AGENTS = {"coordinator"}  # goals + recent context; no constitution/prime_directive

# Specialists on the cached Vertex path (Step 6, [DB-0820-05], approved 2026-08-28).
# mental_wellbeing + physical_health are the prize (+$0.17/day, more than the deployed
# head-layer cache earns); the Flash-Lite six ride along (+$0.008/day — included because
# the A4 gate passed and the diff is the same line, per the Step-6 plan's rule 2).
# GATED CHANGE: this moves the two clinical-flag agents from _openai_compat_loop to
# _run_gemini_native_loop — a larger change than the prompt-assembly reorder that A7's
# pre-sign-off gate demanded an A4 re-run for. The gate runs: 2026-08-28, VM store,
# clinical deep 3/3 + clinical quick 3/3 + pipeline 3/3, plus a post-change clinical
# re-run on the native loop (tests/a4_safety_rerun_2026-08-28_*). Any future change to
# this set owes the same gate. Cache creation pads under the 4,096-token Vertex floor
# (_pad_for_vertex_cache, applied inside _get_or_create_vertex_cache for every caller).
_CACHED_SPECIALISTS = {
    "mental_wellbeing", "physical_health",          # Pro — the measured prize
    "work_vocation", "relationships", "finance",    # Flash-Lite six — ride-along
    "learning_growth", "recreation_hobbies", "logistics",
}


def _run_single_agent(agent_name: str, user_input: str,
                      persona: str | None = None, provider: str | None = None,
                      model_override: str | None = None,
                      complexity: str | None = None,
                      history: list[dict] | None = None,
                      bare: bool = False,
                      attachments: list[dict] | None = None) -> str:
    """
    Run one agent pass and return its raw output (no filter applied).
    Used internally by run_session and run_pipeline_session.

    bare=True: load only the agent instruction file — no constitution, no personal
    config, no recent logs. Used for token-pressure diagnostics and research_agent.

    attachments: files the user sent with this message, passed to the model as
    inline parts. Only the cached Vertex path carries them — every other provider
    here is text-only, and the accompanying description in the input text is what
    tells those models a file existed.
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
        kind = session_kind(user_input, persona)
        config = load_config(persona=persona, kind=kind)
        recent = load_recent_context(persona=persona)
        system_prompt = f"## Your Role for This Session\n\n{agent}\n\n---\n\n{config}"
        # Conduct sections gated on this turn's triggers — scheduled-session conduct
        # and baseline-interview conduct live in config/modules/, not in the agent
        # file, so ordinary turns never carry them (2026-08-27 audit).
        extras = _synth_conditional_sections(kind, user_input)
        if extras:
            system_prompt = f"{system_prompt}\n\n---\n\n{extras}"
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
            elif agent_name in (_HEAD_LAYER_AGENTS | _ROUTING_LAYER_AGENTS
                                | _CACHED_SPECIALISTS):
                result = run_session_gemini_cached(system_prompt, augmented_input, tool_schemas,
                                                   tool_handlers, model=model_override, history=history,
                                                   attachments=attachments,
                                                   thinking_budget=_SYNTH_THINKING_BUDGET
                                                   if agent_name == "synthesizer" else None)
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


def _action_block() -> str:
    """The ACTIONS provenance block for the Synthesizer — evidence, not a claim.

    Called after _dispatch_from_coordinator() returns, which is the first moment
    every blocking specialist has finished and its tool calls are on the trace.
    Two things follow from reading the trace here rather than inside the dispatch
    loop, and both are deliberate:

    - It is **request-scoped**, per Mike's 2026-08-15 decision. That decision was
      taken while per-agent attribution was also broken — [DB-0810-02],
      `pop_agent()` not restoring the previous `current_agent`. **That bug was
      fixed 2026-08-18**, so the technical blocker is gone; request scope now
      stands on Mike's decision alone. Widening it to per-agent is a product
      choice to put to him, not a repair.
    - The fire-and-forget Diarist is excluded automatically: it runs on its own
      thread with a fresh trace (see trace.push_agent), so its journal write is
      not on this one. Good — it is still running when this is read, and a line
      whose contents depended on thread timing would not be evidence of anything.

    Classification of which tools count lives in core/actions.py, in one place.
    """
    from core.actions import action_provenance_block
    block = action_provenance_block(_tr.get_trace())
    # Also emitted to the journal, at INFO on its own logger for the reason given
    # at _dev_request_log: the module logger is pinned to WARNING and _trace() is
    # a no-op in the service. This is what makes the line checkable in production
    # without reading a trace file — "did the system know an action ran" is then
    # answered by grep, not by asking a model.
    _actions_log.info("[actions] " + " | ".join(
        ln.lstrip("- ") for ln in block.splitlines()[1:]
    ))
    return block


_actions_log = logging.getLogger("metatron.actions")
_actions_log.setLevel(logging.INFO)


def _resolve_knowledge(coord_output: str, persona: str | None = None) -> list[dict]:
    """
    Parse KNOWLEDGE_TO_LOAD from Coordinator output and fetch those wisdom entries.

    The Coordinator sees only the manifest — subject names, never contents — and names the
    subjects this turn needs. Selection therefore costs nothing: it happens inside a
    Flash-Lite turn that already runs, so a casual food question reaches the user's standing
    breakfast composition without dispatching Physical Health at all. That case is the whole
    reason this layer exists.

    THREE WAYS THE BLOCK CAN BE WRONG, AND ALL THREE ARE TOLERATED. Absent (the common case —
    most turns need no standing knowledge), malformed, and — the one easily missed —
    **hallucinated**: a domain name that does not exist. `_AGENT_NAME_MAP` below is the
    standing proof that Flash-Lite emits variant strings for enumerated values, so names go
    through the alias map first and are then intersected against domains that actually hold
    entries. Anything left over is dropped and traced, never queried.

    A name that falls through the alias map to the overflow queue is NOT accepted as `other`:
    resolve_domain() returns "other" for anything it does not recognise, so treating that as a
    hit would turn every hallucinated subject into a read of the unclassified bucket.

    Returns entries newest-first, capped per domain by read_wisdom. Never raises.
    """
    import re as _re

    match = _re.search(r'KNOWLEDGE_TO_LOAD:\s*```json\s*(.*?)```', coord_output, _re.DOTALL)
    if not match:
        match = _re.search(r'KNOWLEDGE_TO_LOAD:\s*(\[.*?\])', coord_output, _re.DOTALL)
    if not match:
        return []

    try:
        requested = json.loads(match.group(1).strip())
    except json.JSONDecodeError as exc:
        logger.warning(f"[knowledge] KNOWLEDGE_TO_LOAD JSON parse error: {exc}")
        return []
    if not isinstance(requested, list):
        return []

    try:
        from tools.wisdom import domains_present, read_wisdom, resolve_domain

        with persona_scope(resolve_persona(persona)):
            present = set(domains_present())

            wanted: list[str] = []
            dropped: list[str] = []
            for raw in requested:
                resolved, proposed = resolve_domain(str(raw))
                if proposed or resolved not in present:
                    dropped.append(str(raw))
                elif resolved not in wanted:
                    wanted.append(resolved)

            if dropped:
                _trace(f"[KNOWLEDGE] dropped unknown/empty domains: {dropped}")
            if not wanted:
                return []

            # One read per domain, not one read across all of them. The cap is per domain by
            # design: the Coordinator is told to select adjacent body domains together
            # ("sleep" with "fitness" and "health"), and a single shared cap would let one
            # crowded domain return 15 entries and starve the other two entirely.
            entries: list[dict] = []
            for domain in wanted:
                for entry in read_wisdom(domains=[domain]):
                    if entry.get("key") == "_truncated":
                        continue
                    entries.append({**entry, "domain": entry.get("domain") or domain})
    except Exception as exc:
        logger.warning(f"[knowledge] fetch failed: {exc}")
        return []

    _trace(f"[KNOWLEDGE] loaded {len(entries)} entries from {wanted}")
    return entries


def _knowledge_block(entries: list[dict], domains: list[str] | None = None) -> str:
    """
    Render fetched wisdom entries for a model's input.

    `provenance` governs how the fact is put back to the user — the constitution's
    hypotheses-not-verdicts rule. An observed pattern stated to the user as established
    fact is the failure this field exists to prevent.

    THE HEDGE IS INSIDE THE CLAIM, NOT BESIDE IT ([DB-0818-08], 2026-09-03). Until now
    this rendered `key (observed): value` and appended a rule — "put those back
    tentatively". That is a marker beside a fact, which is an instruction a model can
    weigh against being helpful, and THIS EXACT PATTERN HAS ALREADY FAILED HERE: on
    2026-08-18 a `[RETRIEVAL: NONE]` marker was attached to a turn with zero retrieved
    sources and the Synthesizer softened it rather than refusing, answering an invented
    train incident as fact.

    So an observed entry is no longer rendered as a fact at all. Its sentence is about
    the inference — "you inferred this, and have not confirmed it" — so a model copying
    the line into its answer copies the hedge with it, and there is no separate rule left
    to negotiate with. A stated entry renders bare, because the user said it and the tool
    is not entitled to be tentative about his own account of his life.

    The value itself is never rewritten, only prefixed: case surgery on a string opening
    with a proper noun is how a hedge turns into a visible mangling.

    `domains` optionally narrows to the subset one specialist should see.
    """
    if domains is not None:
        entries = [e for e in entries if e.get("domain") in domains]
    if not entries:
        return ""

    lines = []
    for e in entries:
        prefix = f"- [{e.get('domain', 'other')}] {e.get('key', '')}: "
        value = e.get("value", "")
        if e.get("provenance", "observed") == "stated":
            lines.append(prefix + str(value))
        else:
            lines.append(
                prefix + "you inferred this, and have not confirmed it with the user "
                f"— {value}"
            )
    return (
        "KNOWLEDGE ON FILE (standing facts about the user, already recorded — treat as "
        "known, do not ask the user to repeat them):\n" + "\n".join(lines)
    )


_WISDOM_PROPOSAL_RE = _re.compile(
    # Bare form has no trailing anchor on purpose: agent files specify a one-line block, and
    # requiring a blank line after it would silently miss every proposal a model emitted
    # mid-output. Non-greedy stops at the first closing bracket — the schema is flat, so there
    # is nothing to nest.
    r'WISDOM_PROPOSAL:\s*(?:```(?:json)?\s*(?P<fenced>.*?)```|(?P<bare>\[.*?\]|\{.*?\}))',
    _re.DOTALL,
)


def _file_wisdom_proposals(outputs: dict, persona: str | None = None) -> dict:
    """
    File WISDOM_PROPOSAL blocks emitted by specialists, and strip them from what the
    Synthesizer sees. Returns the cleaned outputs.

    WHY PYTHON PARSES THIS AND NO MODEL RELAYS IT. Specialist output reaches the Synthesizer
    as one opaque prose blob. A "propose a fact" field carried inside that blob would need
    Flash-Lite to emit it, Pro to notice it amid everything else, and Pro to re-key it
    faithfully into a tool call — three lossy hops for a fact whose entire purpose is that the
    user never has to say it twice. `SPECIALISTS_TO_CALL` is the standing proof of the
    alternative: structured relay in this pipeline means Python parses it.

    This is also what makes "propose only" mean something for the seven specialists that read
    the store and must not write to it. Until B2 closes the allowlist gap (`dispatch_tool()`
    checks nothing), a withheld grant is not enforcement — so the real control is that those
    agents are given a channel that lands here, where every write is attributable and capped
    by the schema rather than by an instruction they might not follow.

    Stripped before synthesis on the discretion principle: a proposal is the system's own
    bookkeeping, and a Synthesizer that can see it can narrate it.
    """
    if not outputs:
        return outputs

    from tools.wisdom import write_wisdom

    cleaned: dict = {}
    for agent, text in outputs.items():
        if not isinstance(text, str) or "WISDOM_PROPOSAL:" not in text:
            cleaned[agent] = text
            continue

        proposals: list = []
        for match in _WISDOM_PROPOSAL_RE.finditer(text):
            raw = (match.group("fenced") or match.group("bare") or "").strip()
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                logger.warning(f"[knowledge] {agent} WISDOM_PROPOSAL parse error: {exc}")
                continue
            proposals.extend(parsed if isinstance(parsed, list) else [parsed])

        with persona_scope(resolve_persona(persona)):
            for prop in proposals:
                if not isinstance(prop, dict):
                    continue
                key, value = prop.get("key", ""), prop.get("value", "")
                if not key or not value:
                    continue
                try:
                    result = write_wisdom(
                        key=key,
                        value=value,
                        domain=prop.get("domain", ""),
                        provenance=prop.get("provenance", ""),
                    )
                    _trace(f"[KNOWLEDGE] proposal from {agent}: {result}")
                except Exception as exc:
                    logger.warning(f"[knowledge] {agent} proposal '{key}' failed: {exc}")

        cleaned[agent] = _WISDOM_PROPOSAL_RE.sub("", text).strip()

    return cleaned


_HORIZON_ITEMS_RE = _re.compile(
    # Same two forms as WISDOM_PROPOSAL: a fenced block, or a bare JSON array on the line.
    # The bare form is non-greedy to the first closing bracket — the schema is flat, so
    # there is nothing to nest, and an item's own `detail` cannot contain one unescaped.
    r'HORIZON_ITEMS:\s*(?:```(?:json)?\s*(?P<fenced>.*?)```|(?P<bare>\[.*?\]))',
    _re.DOTALL,
)


def _file_horizon_items(outputs: dict, persona: str | None = None) -> dict:
    """File HORIZON_ITEMS emitted by specialists, and strip them from what the Synthesizer
    sees. Returns the cleaned outputs.

    [DB-0822-09]. The findings do not go to the Synthesizer as part of a specialist's prose
    any more — that is the channel that lost the Death Cab item on 2026-09-02, where a
    536-token package reached a Synthesizer that emitted 177 words about something else.
    They go to tools/horizon.py, which drops anything the user has already been told about,
    and come back through `context_block()` as their own block with their own delivery
    instruction. Same shape and same reasoning as `_file_wisdom_proposals` above: structured
    relay in this pipeline means Python parses it, because the alternative is three lossy
    hops through models that each have something else to attend to.

    Stripped rather than left in place so there is exactly one channel. Leaving them would
    put every finding in front of the Synthesizer twice — once raw, including the ones the
    ledger has deliberately suppressed as already-said, which is the repetition this whole
    mechanism exists to prevent.
    """
    if not outputs:
        return outputs

    from tools.horizon import record

    cleaned: dict = {}
    for agent, text in outputs.items():
        if not isinstance(text, str) or "HORIZON_ITEMS:" not in text:
            cleaned[agent] = text
            continue

        items: list = []
        for match in _HORIZON_ITEMS_RE.finditer(text):
            raw = (match.group("fenced") or match.group("bare") or "").strip()
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                # A specialist that wrote prose instead of JSON is a real regression in its
                # agent file, not a user-visible fault — logged loudly, never raised.
                logger.warning(f"[horizon] {agent} HORIZON_ITEMS parse error: {exc}")
                continue
            items.extend(parsed if isinstance(parsed, list) else [parsed])

        if items:
            try:
                with persona_scope(resolve_persona(persona)):
                    tally = record(items, persona)
                _trace(f"[HORIZON] {agent}: {tally['new']} new, {tally['known']} known, "
                       f"{tally['invalid']} invalid")
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"[horizon] {agent} filing failed: {exc}")

        cleaned[agent] = _HORIZON_ITEMS_RE.sub("", text).strip()

    return cleaned


def _horizon_block(persona: str | None = None) -> str:
    """This turn's horizon block, for the Synthesizer bundle. "" when nothing is waiting.

    Called after `_file_horizon_items()` and before the Synthesizer runs, so a finding
    discovered *this* turn is put to the user in the exchange that found it. Without this the
    delivery would always lag by a session — and an inbox-summarize job that reads the mail,
    finds a concert and says nothing about it until tomorrow is the [DB-0822-09] complaint
    almost exactly.

    The same block is also served from `load_recent_context()` at the start of every session,
    which is what gives an undelivered finding its second chance. Both routes call the same
    function, and its offer window collapses the repeats inside one exchange into a single
    charge — so wiring it in twice costs the finding nothing.
    """
    try:
        from tools.horizon import context_block
        with persona_scope(resolve_persona(persona)):
            return context_block(persona)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[horizon] block failed: {exc}")
        return ""


def has_real_user_turn(user_input: str,
                       is_proactive: bool,
                       attachments: list[dict] | None = None) -> bool:
    """
    Did the user actually say something this turn?

    [DB-0822-05] A scheduled session's opening text is written by scheduler.yaml, so on a
    proactive turn `user_input` is the system's own prompt sitting in the slot user speech
    normally occupies. Anything that treats that text as the user's — the journal being the
    worst case — is recording the system talking to itself. `is_proactive` is therefore
    decisive on its own: a proactive turn has no user speech in it *by construction*, and a
    user who then replies arrives as a separate, non-proactive turn through core/server.py,
    which is why answering a check-in still gets journalled.

    Attachments count: "here, look at this" with a photograph attached and no words is a
    real user turn, and core/server.py already admits it as one.
    """
    if is_proactive:
        return False
    return bool((user_input or "").strip()) or bool(attachments)


# WHAT THE USER LOSES WHEN A SPECIALIST FAILS — B4's first degradation path, built
# 2026-09-03 ([DB-0804-02]). One line per area, phrased as the CONSEQUENCE the user can
# feel, never as the part of the system that produced it.
#
# The wording is Mike's ask of 2026-08-18: on a failure he should be told "I can't do
# that now because xyz", not shown an error. The live instance he named — research_agent
# returning `'NoneType' object is not iterable` — reached the Synthesizer verbatim as
# `[Subagent error — ...]`, which is architecture-revealing on its face and tells the
# user nothing. He got no reason at all.
#
# An area with no entry falls back to a bare statement rather than to the agent's name,
# because the name IS the architecture. A new specialist added without a line here
# therefore degrades to something vague and safe, not to a leak.
_UNAVAILABLE_CONSEQUENCE = {
    "logistics": "their calendar, travel and day-to-day arrangements",
    "time_director": "their schedule and the shape of the day",
    "relationships": "what is on file about the people in their life",
    "finance": "their spending and money picture",
    "physical_health": "their training, sleep and medication record",
    "mental_wellbeing": "the standing picture of how they have been",
    "work_vocation": "their work and career context",
    "learning_growth": "what they are learning and working on",
    "recreation_hobbies": "their interests and downtime",
    "research_agent": "anything that has to be looked up outside their own records",
}


def _unavailable_notice(agent_name: str) -> str:
    """
    What the Synthesizer is told in place of a failed specialist's output.

    NOT the user-facing sentence. Python cannot write that one: the reply is composed in
    the Synthesizer's voice, in the middle of a conversation whose shape it alone holds,
    and a fixed string dropped into it would read as a system message in a product whose
    whole premise is that there is no system to see. So this states the consequence and
    the posture, and the Synthesizer says it in its own words.

    Three things it deliberately does not carry: the exception, the agent's name, and the
    reason. The first two are architecture (`CLAUDE.md` § Discretion). The third is too —
    "the model timed out" and "the calendar service refused" are both facts about
    machinery the user has never been told exists. The consequence is the only part of a
    failure that belongs to them.

    The real exception is not lost; it is logged by the caller and surfaces in
    /monitor/model_errors, which is where it is actionable.
    """
    what = _UNAVAILABLE_CONSEQUENCE.get(agent_name)
    lost = f" to {what}" if what else ""
    return (
        f"[UNAVAILABLE THIS TURN — you could not get{lost}. "
        f"Answer with what you do have. If the missing part is what the user actually "
        f"asked for, tell them plainly that you cannot get to it right now and offer to "
        f"come back to it. Do not guess at it, do not invent a value for it, do not "
        f"explain why it is missing, and do not dwell on it.]"
    )


def _dispatch_from_coordinator(
    coord_output: str,
    persona: str | None = None,
    provider: str | None = None,
    knowledge: list[dict] | None = None,
    user_turn: bool = True,
) -> dict:
    """
    Parse SPECIALISTS_TO_CALL from Coordinator output and dispatch agents.
    Returns {agent_name: output} for blocking agents.
    Fire-and-forget agents (Diarist) run in background daemon threads.

    `knowledge`: entries from _resolve_knowledge(). Each dispatched specialist receives the
    subset of them whose domain names that agent in config/modules/knowledge_domains.yaml —
    so Physical Health gets the food entries on a diet turn and Finance does not.

    `user_turn`: False when this session carries no user speech — see has_real_user_turn().
    The Diarist is refused in that case. It journals a day from the session it is dispatched
    on, and on 2026-08-21 it fired on 10 of 23 runs with the user silent in 9 of them, once
    filing the scheduler's own "Good morning..." prompt as something Mike said. The agent-file
    rule against this (`82d394b`, 2026-08-09) was already in place and already ignored, which
    is why the refusal is here in Python.
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
    fire_and_forget: list = []

    # Confirmations outstanding BEFORE any specialist runs. Anything new by the end of
    # the blocking loop was raised by this dispatch, which is the signal
    # pending_directive_note() needs. Captured here rather than passed in from the two
    # callers so the two paths cannot drift — the streaming twin is the one that
    # matters in production.
    _pending_at_dispatch = _pending_tokens(persona)

    # Invert the domain->agents map once, into agent->domains. Built even when no knowledge
    # was fetched so the lookup below is unconditional and cheap; the file is tiny and cached.
    _agent_domains: dict[str, list[str]] = {}
    if knowledge:
        from tools.wisdom import domain_agent_map

        for _domain, _agents in domain_agent_map().items():
            for _agent in _agents:
                _agent_domains.setdefault(_agent, []).append(_domain)

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

        # [DB-0822-05] No user speech this session, no journal entry. See the `user_turn`
        # note in the docstring: the alternative is a diary of the assistant's own monologue.
        if agent == "diarist" and not user_turn:
            logger.debug(
                "[PIPELINE] diarist dispatch suppressed — no real user turn in this session"
            )
            _trace("[PIPELINE] diarist suppressed (no user turn)")
            continue

        # Append the standing facts this specialist reads, if any were fetched. The
        # Diarist is included deliberately: it is the highest-volume writer and the one
        # agent with no relay back, so knowing what is already on file is what stops it
        # writing a fourth near-duplicate of a fact recorded three times already.
        if knowledge:
            block = _knowledge_block(knowledge, domains=_agent_domains.get(agent, []))
            if block:
                directive = f"{directive}\n\n{block}"

        if is_ff:
            # Collected, NOT started — see the deferral note below the blocking loop.
            fire_and_forget.append((agent, directive, complexity))
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
            _fan_turn = _turn.current()

            def _make_specialist(agent_name, directive, cx):
                def _worker():
                    _tr.set_trace(_fan_trace)
                    _tr._set_current_agent(_fan_agent)
                    _turn.adopt(_fan_turn)
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
                    outputs[a] = _unavailable_notice(a)
                    logger.warning(f"[PIPELINE] {a} failed: {exc}")

    # Fire-and-forget agents start HERE, after the blocking specialists have finished,
    # and not in the loop above where they used to. [DB-0829-01]: the Diarist was
    # starting ~1.6s into the turn, before the specialist that would call `send_email`
    # had called it, so a directive written in the Coordinator's optimistic past tense
    # ("user sent an email to Iva Diamond") could never be contradicted by the gate that
    # then refused the send. Deferring the start is what makes the confirmation store
    # authoritative at the moment the directive is handed over.
    #
    # This costs nothing the user can see. These agents are fire-and-forget precisely
    # because no reply waits on them, and the reply itself cannot be produced until the
    # blocking specialists return anyway — so the Diarist now starts at the moment the
    # Synthesizer does, rather than racing it.
    if fire_and_forget:
        new_pending = _pending_raised_since(_pending_at_dispatch, persona)
        for agent, directive, complexity in fire_and_forget:
            directive, asserted_done = pending_directive_note(directive, new_pending)
            if asserted_done:
                actions = ", ".join(sorted({p.get("action", "an action")
                                            for p in new_pending}))
                logger.warning(
                    "[pending_receipt] %s directive described %s as done while it "
                    "awaited approval — corrected before dispatch", agent, actions)
                try:
                    from tools.logger import write_quality_event
                    write_quality_event(
                        event_type="FALSE_COMPLETION_CLAIM",
                        detail=(f"Coordinator directive to {agent} described {actions} "
                                f"as already done while it was still awaiting user "
                                f"approval; directive corrected before dispatch."),
                    )
                except Exception:  # noqa: BLE001
                    # Instrumentation must never cost the corrected dispatch.
                    pass

            def _bg(a: str = agent, d: str = directive, c: str | None = complexity) -> None:
                try:
                    run_session(a, user_input=d, persona=persona, complexity=c)
                except Exception as exc:
                    logger.warning(f"[fire_and_forget] {a} failed: {exc}")
            threading.Thread(target=_bg, daemon=True).start()

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


# --- "Over and out" sign-off: skip the Synthesizer when the user has closed the
# exchange (Mike's decision, 2026-08-27). The phrase is detected HERE, in Python,
# and never by a model: it is an exact-matchable string, and routing it through
# Coordinator judgment would add a Flash-Lite failure mode (silent when you did
# not sign off, chatty when you did) to a decision that needs none. The
# Coordinator and specialists still run — a sign-off ends the conversation, not
# the work (the diary write, the calendar entry still land). Only the Pro-tier
# Synthesizer pass is skipped, unless a specialist raised a safety flag, in which
# case the veto below forces the normal path. The veto is code, not instruction,
# per CLAUDE.md: a mishandled clinical flag is a hard fail regardless of how the
# turn was classified.
#
# Known, accepted gap: a skipped turn writes no [CONTEXT] block, so the context
# tracker does not see this exchange. A sign-off turn carries no new content by
# definition — the substance was in the turns before it.
_SIGNOFF_FLAG_TOKENS = ("MUST_SURFACE", "CLINICAL_CONCERN", "MEDICATION_MISSED_CRITICAL")
# A natural phrase, not an emoji — Mike's call 2026-08-27, after the pre-deploy
# Synthesizer coincidentally replied "Received. Talk to you later." to a sign-off
# and it read exactly right. A fixed string: no model call, no translation pass
# (this path returns before _translate_for_user by design), safe for TTS.
_SIGNOFF_ACK = "Received — talk to you later."


def _levenshtein(a: str, b: str) -> int:
    """
    Damerau edit distance (optimal string alignment) — transposition counts as
    ONE edit, because "adn" for "and" is the most common real typo and plain
    Levenshtein prices it at 2, which would reject exactly the misspelling this
    exists to tolerate. Two short words; no need for a dependency.
    """
    rows = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        rows[i][0] = i
    for j in range(len(b) + 1):
        rows[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cost = a[i - 1] != b[j - 1]
            rows[i][j] = min(rows[i - 1][j] + 1, rows[i][j - 1] + 1, rows[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                rows[i][j] = min(rows[i][j], rows[i - 2][j - 2] + 1)
    return rows[-1][-1]


def _is_signoff(user_text: str) -> bool:
    """
    True when the message ENDS with "over and out", tolerating slight misspelling.

    Tuned to never false-positive rather than to catch every variant:
    - The three words must be the message's final tokens — nothing after them but
      punctuation. "Over and out" mid-sentence is conversation, not a sign-off.
    - Each word tolerates at most one edit, at most two across the phrase
      ("over adn out", "ovr and out" pass; "down and out", "over and above",
      "in and out" are all ≥2 edits on a single word and fail).
    - "&" is accepted for "and".
    - A message whose raw text ends with "?" is never a sign-off — someone asking
      about the phrase is not using it.
    """
    raw = user_text.strip()
    if not raw or raw.endswith("?"):
        return False
    words = _re.findall(r"[a-z&']+", raw.lower())
    if len(words) < 3:
        return False
    last3 = list(words[-3:])
    if last3[1] == "&":
        last3[1] = "and"
    total = 0
    for word, target in zip(last3, ("over", "and", "out")):
        d = _levenshtein(word, target)
        if d > 1:
            return False
        total += d
    return total <= 2


def _signoff_skip(spec_text: str, user_input: str, is_proactive: bool) -> bool:
    """The full skip decision: user sign-off, real turn, and no safety flag raised."""
    if is_proactive or not _is_signoff(user_input):
        return False
    if any(tok in spec_text for tok in _SIGNOFF_FLAG_TOKENS):
        logger.warning("[signoff] safety flag present in specialist output — "
                       "sign-off overridden, Synthesizer runs")
        return False
    _trace("[PIPELINE] sign-off detected — synthesizer skipped")
    return True


# [DB-0815-11] The system claims actions it never took. Third confirmed instance
# 2026-08-21: "I have made a note to open sessions exactly that way going forward. I've
# logged the instruction change so it sticks" — and the trace for that run contains no
# config write of any kind. Mike: "False action claim is unacceptable."
#
# This is the DETECTION half only, and it is deliberately log-only: it never suppresses or
# edits a response. A pattern set aimed at the user's screen would have to be right every
# time; one aimed at a quality log only has to be right often enough to count, and a wrong
# suppression is a worse failure than a wrong log line.
#
# Precision over recall throughout. Each pattern requires a first-person claim about
# something being *persisted* — a promise ("I'll keep that in mind") is not a claim, and a
# statement about the user's own action ("you logged it yesterday") is not one either.
_PERSISTENCE_CLAIM_PATTERNS = [
    r"\bI(?:'ve|’ve| have) (?:made|taken) (?:a )?note\b",
    r"\bI(?:'ve|’ve| have) (?:logged|recorded|saved|stored|noted (?:it|that|this) down)\b",
    r"\bI(?:'ve|’ve| have) (?:updated|amended) (?:your|the)\b",
    r"\bI(?:'ve|’ve| have) (?:added|written|put) (?:it|that|this)\s+(?:in|into|to|down)\b",
    r"\bI(?:'ll|’ll| will) (?:make a note|log|record|save|note) (?:of |that|it|this)\b",
    r"\bso it sticks\b",
    r"\bit(?:'s|’s| is| has been) (?:now )?(?:logged|recorded|saved|on file)\b",
    r"\bthat(?:'s|’s| is| has been) (?:now )?(?:logged|recorded|saved|on file)\b",
]

# A tool call that actually persists something. Prefix-matched because the naming
# convention is consistent and a new writer should be covered the day it is registered,
# not the day someone remembers to extend a list.
_WRITE_TOOL_PREFIXES = ("write_", "update_", "create_", "merge_", "unmerge_", "delete_",
                        "import_", "log_", "teach_", "close_", "open_", "reopen_")
_WRITE_TOOL_NAMES = {"send_email"}


def find_persistence_claims(text: str) -> list[str]:
    """
    Return the sentences in `text` that claim something was written down or remembered.

    Sentence-level so the quality event carries the claim in the user's own reading of it,
    which is what makes the log readable months later. Empty list is the normal case.
    """
    import re as _re

    claims: list[str] = []
    for sentence in _re.split(r"(?<=[.!?])\s+|\n+", text or ""):
        s = sentence.strip()
        if not s:
            continue
        if any(_re.search(p, s, _re.IGNORECASE) for p in _PERSISTENCE_CLAIM_PATTERNS):
            claims.append(s)
    return claims


def _is_write_tool(name: str) -> bool:
    return name in _WRITE_TOOL_NAMES or name.startswith(_WRITE_TOOL_PREFIXES)


def _trace_tool_names(trace: object | None = None) -> set[str]:
    """Every tool called anywhere in this turn's trace, including inside subagents."""
    tr = trace if trace is not None else _tr.get_trace()
    names: set[str] = set()
    if tr is None:
        return names

    def _walk(rec) -> None:
        for turn in getattr(rec, "turns", []):
            for call in getattr(turn, "tool_calls", []):
                names.add(getattr(call, "name", ""))
        for sub in getattr(rec, "subagents", []):
            _walk(sub)

    for rec in getattr(tr, "pipeline", []):
        _walk(rec)
    return names


def check_false_action_claims(response: str,
                              tool_names: set[str] | None = None) -> list[str]:
    """
    Log a FALSE_ACTION_CLAIM quality event for each persistence claim with no write behind it.

    Returns the claims that were flagged, so callers and tests can see the decision. The
    response itself is never touched — see the note above `_PERSISTENCE_CLAIM_PATTERNS`.

    Known residual: the Diarist runs fire-and-forget on a daemon thread with no trace of its
    own, so a claim that only the journal satisfies can still be flagged. That is a wrong
    line in a quality log, not a wrong word to the user, which is the trade this half accepts.
    """
    claims = find_persistence_claims(response)
    if not claims:
        return []
    names = _trace_tool_names() if tool_names is None else tool_names
    if any(_is_write_tool(n) for n in names):
        return []
    for claim in claims:
        try:
            from tools.logger import write_quality_event
            write_quality_event("FALSE_ACTION_CLAIM", "synthesizer", claim)
        except Exception as e:
            logger.warning(f"[PIPELINE] FALSE_ACTION_CLAIM log failed: {e}")
    logger.warning(
        f"[PIPELINE] {len(claims)} action claim(s) with no write in this turn: {claims[0][:120]}"
    )
    return claims


def _close_turn_bookkeeping(visible: str, user_input: str, is_proactive: bool,
                            kind: str | None) -> None:
    """
    Close the asked-state loop, and stamp the scheduled run, at the end of one turn
    ([DB-0809-02]).

    A scheduled run's questions are recorded as asked-and-unanswered, so the next job does not
    put them again; a real user turn clears whatever it answered. Both directions are keyed on
    who produced the text — the scheduler prompt is the system talking to itself, and the
    Synthesizer re-asking is not the user answering. Same distinction `82d394b` drew for the
    repeated-instruction protocol and `_expire_open_threads` draws for thread grace.

    The scheduled run is stamped HERE rather than at the top of the pipeline, and that placement
    is load-bearing: see close_scheduled_run() — a stamp taken before the run would record the
    run's own writes as new information and no run could ever read as quiet.

    Best effort throughout: bookkeeping never breaks a delivered response.
    """
    try:
        from tools.context_tracker import (
            clear_answered_questions, close_scheduled_run, extract_questions,
            record_asked_questions,
        )
        if is_proactive:
            questions = extract_questions(visible)
            if questions:
                record_asked_questions(questions, kind=kind)
        else:
            clear_answered_questions(user_input)
        if kind:
            close_scheduled_run(kind)
    except Exception as exc:
        logger.warning(f"[asked_state] not updated: {exc}")

    # [DB-0822-09] Horizon findings, on the same who-produced-the-text distinction the
    # function already turns on. `mark_engaged` is given the user's own words only: a
    # scheduler prompt that happens to mention a concert must not discharge the finding
    # about that concert, which is the [DB-0822-05] confusion one layer over. Counting the
    # delivery ATTEMPT is deliberately not done here — tools/horizon.py charges it at the
    # point the block is actually served, because a finding filed mid-turn was never in the
    # block this turn built and must not be charged for it.
    try:
        from tools.horizon import mark_engaged
        if not is_proactive:
            mark_engaged(user_input)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[horizon] turn bookkeeping not updated: {exc}")


def _frame_proactive(user_input: str, is_proactive: bool) -> tuple[str, str]:
    """
    Return (coordinator_prefix, synthesizer_label) for one pipeline run.

    The label is load-bearing: calling scheduler text "ORIGINAL USER MESSAGE" is the
    specific thing that made it indistinguishable from user speech.
    """
    if not is_proactive:
        return "", "ORIGINAL USER MESSAGE"
    return f"{_PROACTIVE_FRAME}\n\n", "SCHEDULER DIRECTIVE (the user has not spoken yet)"


# How much of the conversation the Coordinator is shown. [DB-0826-01], 2026-09-03.
#
# It was shown NONE of it until this line existed. Both call sites below invoked
# _run_single_agent("coordinator", ...) with no `history` at all, so every referring turn
# — "undo that merge", "approved", "cancel my previous request" — was routed by an agent
# that could not see what it referred to, against a context holding only day logs and open
# threads. That is the whole of [DB-0826-01]. Measured 2026-09-03 on gemini-3.5-flash-lite,
# Suite B-hard x3: the Coordinator named the right referent in 0 of 12 referring turns with
# neither half of the fix, 6 of 12 with history alone, and 12 of 12 with history plus
# tools/turn_referent.py — which is why both halves shipped together.
#
# Six messages, not the Synthesizer's ten. Three exchanges reaches past the competing
# referent in every recorded instance (the furthest, 2026-08-26, was two exchanges back)
# and costs roughly 300-600 input tokens per turn on the bulk tier — under a cent a day at
# any plausible volume. It goes in the user message, so the cached system prefix is
# unchanged and the Vertex 4,096-token floor is not approached from either side.
#
# COPIED, never the caller's list. Every model loop in this file appends its own turn to
# the `history` object it is handed; passing the live list would splice the Coordinator's
# raw routing package into the conversation the Synthesizer then reads.
_COORD_HISTORY_MESSAGES = 6


def _coord_history(history: list[dict] | None) -> list[dict] | None:
    return [dict(h) for h in history[-_COORD_HISTORY_MESSAGES:]] if history else None


def run_pipeline_session(user_input: str,
                         persona: str | None = None,
                         provider: str | None = None,
                         history: list[dict] | None = None,
                         received_at: datetime | None = None,
                         is_proactive: bool = False,
                         attachments: list[dict] | None = None) -> str:
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
    # [DB-0827-01] What kind of turn this is, for the decline guard in tools/confirm.py:
    # a refused action may come back on a new trigger and never from carried context, and
    # inside the tool the two are indistinguishable without this. Cleared in the `finally`
    # below — a session runs on a pooled thread, and a turn left bound would let the NEXT
    # session inherit "the user spoke" from this one.
    _turn.adopt({"user_turn": has_real_user_turn(user_input, is_proactive, attachments),
                 "started_at": time.time()})
    try:
        # Tokens outstanding BEFORE this turn. Anything new by the end of it was raised
        # by this turn's tool calls, which is how enforce_pending_receipt() knows what
        # the reply must not claim to have finished. Compared by token rather than by
        # timestamp so a pending request left over from an earlier turn is not
        # re-announced on every subsequent reply.
        _pending_before = _pending_tokens(persona)
        receipt_line = ""
        if received_at is not None:
            from tools.ambient import format_receipt_time
            receipt_line = f"[This message received at: {format_receipt_time(received_at)}]\n\n"

        proactive_prefix, synth_label = _frame_proactive(user_input, is_proactive)
        # [DB-0809-02] Which scheduled job this is, and what it may say — see
        # _scheduled_focus_block(). Empty on every user-typed turn. Computed here, before the
        # Coordinator runs, so both twins stamp the run at the same point.
        kind = session_kind(user_input, persona)
        focus_block = _scheduled_focus_block(kind)

        # Pre-load Pattern Miner insights (the one context source not in the system prompt).
        coord_context = _load_coordinator_context(persona)
        # Kept identical to the streaming twin below — a feature wired into only one
        # of the two is live in tests and dead in production, or the reverse.
        attach_note = attachments_mod.describe_for_prompt(attachments or [])
        coord_input = (
            f"{proactive_prefix}{receipt_line}{user_input}{attach_note}\n\n---\n\n[Pre-loaded context]\n{coord_context}"
            if coord_context else f"{proactive_prefix}{receipt_line}{user_input}{attach_note}"
        )

        # Pass 1: Coordinator — single-pass routing directive assembly
        _trace("[PIPELINE] coordinator  starting")
        coord_output = _run_single_agent(
            "coordinator", coord_input, persona=persona, provider=provider,
            attachments=attachments, history=_coord_history(history),
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

        # Fetch the standing knowledge the Coordinator selected, before dispatch — the
        # specialists that read those subjects get them appended to their directives.
        knowledge = _resolve_knowledge(coord_output, persona=persona)

        # Dispatch specialists from Python based on Coordinator's SPECIALISTS_TO_CALL
        _trace("[PIPELINE] dispatching specialists")
        specialist_outputs = _dispatch_from_coordinator(
            coord_output, persona=persona, provider=provider, knowledge=knowledge,
            user_turn=has_real_user_turn(user_input, is_proactive, attachments),
        )
        specialist_outputs = _file_wisdom_proposals(specialist_outputs, persona=persona)
        specialist_outputs = _file_horizon_items(specialist_outputs, persona=persona)

        # Bundle specialist outputs for Synthesizer (exclude async fire-and-forget)
        spec_text = "\n\n".join(
            f"--- {agent} ---\n{output}"
            for agent, output in specialist_outputs.items()
            if "dispatched (async)" not in output
        )

        # User signed off ("over and out") and nothing pressing came back from the
        # specialists: the work is done, rest without the Pro-tier Synthesizer pass.
        if _signoff_skip(spec_text, user_input, is_proactive):
            if history is not None:
                history.append({"role": "user", "content": user_input})
                history.append({"role": "assistant", "content": _SIGNOFF_ACK})
                del history[:-10]
            _tr.finish_request_trace(_SIGNOFF_ACK)
            return _SIGNOFF_ACK

        # Pass 2: Synthesizer — integration and user-facing response.
        # The ACTIONS block goes last, closest to the response, and is always
        # present: see _action_block().
        know_text = _knowledge_block(knowledge)
        # [DB-0822-09] Built HERE, after the sign-off veto above: a finding must not be
        # charged an offer on a turn where the Synthesizer never runs.
        horizon_text = _horizon_block(persona)
        synthesizer_input = (
            f"{proactive_prefix}{receipt_line}{synth_label}:\n{user_input}{attach_note}\n\n"
            f"COORDINATOR ROUTING PACKAGE:\n{coord_output}"
            + (f"\n\n{know_text}" if know_text else "")
            + (f"\n\nSPECIALIST OUTPUTS:\n{spec_text}" if spec_text else "")
            + (f"\n\n{horizon_text}" if horizon_text else "")
            + (f"\n\n{focus_block}" if focus_block else "")
            + f"\n\n{_action_block()}"
        )
        _trace("[PIPELINE] synthesizer  starting")
        recent_history = list(history[-10:]) if history else None
        # Files go to the Synthesizer as well as the Coordinator — see the streaming
        # twin for why a routing package is not a substitute for the picture.
        synth_result = _run_single_agent(
            "synthesizer", synthesizer_input, persona=persona, provider=provider,
            history=recent_history, attachments=attachments,
        )
        _trace(f"[PIPELINE] synthesizer  done  ({len(synth_result)} chars)")
        # Strip the internal [CONTEXT] block before the response leaves the
        # pipeline. Without this it reaches push notifications, the scheduler's
        # terminal output and the non-streaming /session endpoint verbatim, and
        # the context tracker is never updated for proactive sessions.
        visible, _ctx = split_context_block(synth_result)
        # [DB-0815-11] Detection only, before anything else touches the text and while the
        # trace is still open — nothing here changes what the user sees.
        check_false_action_claims(visible)
        # Only a real user turn keeps a thread alive. On a proactive session
        # `user_input` is the scheduler's own prompt, and passing that would
        # let the system grant its own threads a reprieve — the same mistake
        # `82d394b` fixed in the repeated-instruction protocol.
        persist_context_block(_ctx, user_text=None if is_proactive else user_input)
        # [DB-0809-02] Record what this scheduled run asked, or clear what this user turn
        # answered. Mirrors the streaming twin exactly.
        _close_turn_bookkeeping(visible, user_input, is_proactive, kind)
        # Same `is_proactive` gate, and for the same reason: only a real user turn
        # can exempt a term it named. A scheduler prompt is the system's own text,
        # so letting it grant exemptions would let the system unlock its own filter.
        filtered = filter_output(visible, "synthesizer",
                                 user_text=None if is_proactive else user_input)
        # After the confidentiality filter, not before: a suppressed reply has already
        # lost its text, and the pending line still needs to reach the user.
        filtered = enforce_pending_receipt(
            filtered, _pending_raised_since(_pending_before, persona))
        if history is not None:
            history.append({"role": "user",
                            "content": user_input + _history_attachment_note(attachments)})
            history.append({"role": "assistant", "content": filtered})
            del history[:-10]
    except Exception:
        _tr.set_trace(None)
        raise
    finally:
        _turn.adopt(None)
    _tr.finish_request_trace(filtered)
    # [DB-0810-15] Translation is the last thing that happens, after the trace and after
    # `history` above have both taken the English text. That is deliberate: the model's own
    # context and the debugging record stay in one language, and only the string handed to the
    # user changes. Running this earlier would feed translated text back as conversation
    # history and drift the Synthesizer's working language turn by turn.
    return _translate_for_user(filtered, persona)


def _translate_for_user(text: str, persona: str | None) -> str:
    """
    Render `text` in the persona's response language, if one is set. See core/translate.py.

    A no-op for every persona without `output_language` — which is all of them by default, so
    this cannot change existing behaviour. Never raises: `translate()` fails open.
    """
    from core.translate import response_language, translate

    lang = response_language(persona)
    if lang is None:
        return text
    code, name = lang
    return translate(text, code, name)


def run_pipeline_session_stream(
    user_input: str,
    persona: str | None = None,
    provider: str | None = None,
    history: list[dict] | None = None,
    is_proactive: bool = False,
    received_at: datetime | None = None,
    attachments: list[dict] | None = None,
) -> Iterator[str]:
    """
    Streaming variant of run_pipeline_session().

    Thin wrapper that binds the persona for the whole generator. The binding is
    thread-local and is entered on the thread that iterates the generator — which
    is the executor thread in core/server.py, not the event loop — so concurrent
    requests for different personas cannot observe each other's identity.

    [DB-0827-01] The turn is bound here for the same reason and on the same thread: it is
    what tells the decline guard in tools/confirm.py whether a proposal came from the user
    or from the model re-reading carried context. A generator's `with` unbinds on exhaustion
    or on close, so an abandoned stream does not leave the turn behind.
    """
    with persona_scope(resolve_persona(persona)) as bound, _turn.turn_scope(
        user_turn=has_real_user_turn(user_input, is_proactive, attachments)
    ):
        yield from _run_pipeline_session_stream_inner(
            user_input, persona=bound, provider=provider, history=history,
            is_proactive=is_proactive, received_at=received_at,
            attachments=attachments,
        )


def _run_pipeline_session_stream_inner(
    user_input: str,
    persona: str | None = None,
    provider: str | None = None,
    history: list[dict] | None = None,
    is_proactive: bool = False,
    received_at: datetime | None = None,
    attachments: list[dict] | None = None,
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

    # See the non-streaming path: the token set before the turn is what makes a
    # confirmation raised BY this turn distinguishable from one already outstanding.
    _pending_before = _pending_tokens(persona)
    receipt_line = ""
    if received_at is not None:
        from tools.ambient import format_receipt_time
        receipt_line = f"[This message received at: {format_receipt_time(received_at)}]\n\n"

    # Pass 1: Coordinator — single-pass routing directive assembly (blocking)
    _trace("[PIPELINE] coordinator  starting")
    coord_context = _load_coordinator_context(persona)
    proactive_prefix, synth_label = _frame_proactive(user_input, is_proactive)
    # [DB-0809-02] Mirrors the non-streaming twin: which scheduled job this is, and the
    # focus directive computed for it. Keyed on the user's own turn — see the note at the
    # load_config() call below for why the Synthesizer package cannot be used for this.
    kind = session_kind(user_input, persona)
    focus_block = _scheduled_focus_block(kind)
    # Names the files and states that their contents are data, never instructions —
    # the <untrusted_content> boundary applied to bytes, which cannot carry tags.
    attach_note = attachments_mod.describe_for_prompt(attachments or [])
    coord_input = (
        f"{proactive_prefix}{receipt_line}{user_input}{attach_note}\n\n---\n\n[Pre-loaded context]\n{coord_context}"
        if coord_context else f"{proactive_prefix}{receipt_line}{user_input}{attach_note}"
    )
    coord_output = _run_single_agent("coordinator", coord_input, persona=persona, provider=provider,
                                     attachments=attachments, history=_coord_history(history))
    _trace(f"[PIPELINE] coordinator  done  ({len(coord_output)} chars) → dispatching specialists")
    _handle_user_correction(coord_output)
    # Knowledge fetch mirrors run_pipeline_session() exactly. THIS IS THE PATH THAT MATTERS:
    # the server streams, so a feature wired only into the non-streaming function is live in
    # tests and dead in production. Any change to the knowledge wiring changes both.
    knowledge = _resolve_knowledge(coord_output, persona=persona)
    specialist_outputs = _dispatch_from_coordinator(
        coord_output, persona=persona, provider=provider, knowledge=knowledge,
        user_turn=has_real_user_turn(user_input, is_proactive, attachments),
    )
    specialist_outputs = _file_wisdom_proposals(specialist_outputs, persona=persona)
    specialist_outputs = _file_horizon_items(specialist_outputs, persona=persona)
    spec_text = "\n\n".join(
        f"--- {agent} ---\n{output}"
        for agent, output in specialist_outputs.items()
        if "dispatched (async)" not in output
    )
    # Sign-off skip — mirrors the non-streaming branch above; same veto, same ack.
    if _signoff_skip(spec_text, user_input, is_proactive):
        if history is not None:
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": _SIGNOFF_ACK})
            del history[:-10]
        yield _SIGNOFF_ACK
        yield "[DONE]"
        _tr.finish_request_trace(_SIGNOFF_ACK)
        return

    _trace("[PIPELINE] synthesizer  streaming")

    # Build Synthesizer input — ACTIONS block last and unconditional, as above.
    know_text = _knowledge_block(knowledge)
    # [DB-0822-09] After the sign-off veto, as in the non-streaming twin above.
    horizon_text = _horizon_block(persona)
    synthesizer_input = (
        f"{proactive_prefix}{receipt_line}{synth_label}:\n{user_input}{attach_note}\n\n"
        f"COORDINATOR ROUTING PACKAGE:\n{coord_output}"
        + (f"\n\n{know_text}" if know_text else "")
        + (f"\n\nSPECIALIST OUTPUTS:\n{spec_text}" if spec_text else "")
        + (f"\n\n{horizon_text}" if horizon_text else "")
        + (f"\n\n{focus_block}" if focus_block else "")
        + f"\n\n{_action_block()}"
    )

    # Load Synthesizer prompt — mirrors _run_single_agent internals
    agent_instructions = load_agent("synthesizer")
    # `kind` was resolved above from the user's own turn, not from synthesizer_input: the
    # latter carries the Coordinator package and specialist output, so the evening prompt's
    # words can appear in it on any turn that merely discusses the evening.
    config = load_config(persona=persona, kind=kind)
    recent = load_recent_context(persona=persona)
    system_prompt = f"## Your Role for This Session\n\n{agent_instructions}\n\n---\n\n{config}"
    # Conduct sections gated on this turn's triggers (mirrors _run_single_agent).
    # kind keys on the user's turn per the note above; the BASELINE_INCOMPLETE
    # trigger keys on the package, because that is where a specialist raises it.
    extras = _synth_conditional_sections(kind, synthesizer_input)
    if extras:
        system_prompt = f"{system_prompt}\n\n---\n\n{extras}"
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
        # Cached AND streaming (Option A, 2026-08-18). This branch previously had to
        # choose: it streamed by never reaching _get_or_create_vertex_cache, which
        # re-billed the ~19k-token system prompt on every message Mike sent, and the
        # brief Option B fix bought the cache back by giving up the stream. The native
        # SDK does both, so neither trade is live any more.
        #
        # What streaming does NOT fix, so nobody re-measures it hoping otherwise:
        # time-to-first-token is dominated by thinking, not delivery. Probed live —
        # 14.89s of a 19.78s generation elapsed before the first delta, and 86% of what
        # the Synthesizer generates is thinking (18 real turns). The dead air Mike
        # reported is the thinking budget; this only lets the answer arrive progressively
        # once it starts, which is what makes sentence-chunked TTS possible.
        #
        # The Synthesizer gets the files too, not only the Coordinator's package.
        # The Coordinator is a router: its output is a routing decision, not a
        # transcription, so "what breed is this dog" would reach the writer of the
        # reply as prose about a dog it never saw. A second pass over an image costs
        # a few hundred tokens against a turn that costs cents, and every visual
        # follow-up ("the one on the left") depends on it.
        gen = run_session_gemini_cached_stream(
            system_prompt, augmented_input, tool_schemas, tool_handlers,
            model=synth_model, history=recent_history, attachments=attachments,
            thinking_budget=_SYNTH_THINKING_BUDGET,   # this path is the Synthesizer, always
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

    # [DB-0810-15] A persona with a response language cannot be streamed token by token:
    # translation needs a complete message, so there is nothing correct to emit mid-generation.
    # Streaming English chunks and replacing them afterwards was considered and rejected — the
    # user would watch a language they did not ask for arrive and then vanish, and on the voice
    # path TTS would already have spoken it. So for these personas the text is withheld and
    # delivered once, translated, below. Everyone else streams exactly as before.
    #
    # This is the known cost of the feature, recorded rather than hidden: response latency for
    # a translated persona becomes generation + one translation call. Sentence-chunked
    # translation would recover most of the streaming feel and pairs naturally with
    # [DB-0809-13] (sentence-chunked TTS); it is not built here because correctness first.
    _out_lang = None
    try:
        from core.translate import response_language
        _out_lang = response_language(persona)
    except Exception:   # never let a profile read break a response
        logger.warning("[translate] could not resolve response language — streaming untranslated")
    _stream_to_client = _out_lang is None

    buffer: list[str] = []
    pending: str = ""          # buffered but not yet yielded (delimiter lookahead window)
    context_started: bool = False

    for chunk in gen:
        buffer.append(chunk)
        if not context_started:
            pending += chunk
            if _CONTEXT_OPEN in pending:
                idx = pending.index(_CONTEXT_OPEN)
                if idx > 0 and _stream_to_client:
                    yield pending[:idx]   # flush everything before the delimiter
                context_started = True
                pending = ""
            elif len(pending) > _LOOKAHEAD:
                safe = len(pending) - _LOOKAHEAD
                if _stream_to_client:
                    yield pending[:safe]
                pending = pending[safe:]

    # Flush any remaining visible text if the delimiter was never seen
    if not context_started and pending and _stream_to_client:
        yield pending

    complete = "".join(buffer)

    # Same splitting logic as the non-streaming pipeline — one implementation so
    # the two paths cannot drift apart again.
    visible, _ctx = split_context_block(complete)
    if _ctx is None and _CONTEXT_OPEN not in complete:
        logger.warning("[context_block] no [CONTEXT] block in Synthesizer response")
    # [DB-0815-11] Same detection as the non-streaming twin. The text has already reached
    # the user by this point on this path, which is exactly why it only logs.
    check_false_action_claims(visible)
    # See the note at the non-streaming call site: a scheduler prompt is not
    # the user speaking, so it must not grace an open thread.
    persist_context_block(_ctx, user_text=None if is_proactive else user_input)
    # [DB-0809-02] Same asked-state bookkeeping as the non-streaming twin — a feature wired
    # into only one of the two is live in tests and dead in production.
    _close_turn_bookkeeping(visible, user_input, is_proactive, kind)

    _tr.pop_agent(_synth_rec)
    # See the non-streaming call site: a scheduler prompt is not the user speaking,
    # so it grants no echo exemption either.
    filtered = filter_output(visible, "synthesizer",
                             user_text=None if is_proactive else user_input)
    # Suppression by the confidentiality filter and amendment by the pending-receipt
    # check are different outcomes with different delivery rules, so they are tracked
    # separately rather than both inferred from `filtered != visible`.
    _suppressed = filtered != visible
    _final = filtered if _suppressed else enforce_pending_receipt(
        filtered, _pending_raised_since(_pending_before, persona))
    if history is not None:
        # History is text, so the file itself does not survive into later turns —
        # only the note that one was sent. A follow-up question about the picture
        # therefore needs the picture attached again; recording the names at least
        # stops the model contradicting a conversation that plainly had files in it.
        history.append({"role": "user", "content": user_input + _history_attachment_note(attachments)})
        history.append({"role": "assistant", "content": _final if _suppressed is False else ""})
        del history[:-10]
    if _suppressed:
        # Suppressed. Nothing is delivered in either mode, so there is nothing to translate —
        # and the canned fallback must not be translated by a model call that could itself
        # leak, which is why this branch returns before the translation step below.
        yield "[RETRACT]"
    elif _final != filtered:
        # A confirmation was raised during this turn and the reply had to be amended —
        # see enforce_pending_receipt(). On the streaming path the original text is
        # already on the user's screen, so the amendment cannot be appended: what was
        # shown has to be withdrawn and the corrected message delivered in its place.
        #
        # It is ONE marker carrying its own replacement, not `[RETRACT]` followed by
        # text. Live 2026-08-27 that first shape delivered nothing: `[RETRACT]` is
        # terminal on both server paths — core/server.py breaks its read loop on it —
        # and the client nulls the bubble, so every chunk after it was discarded and
        # the user saw the canned "I can't help with that right now" in place of a
        # correct answer to a legitimate request. A refusal is the worst possible
        # rendering of this particular message, which exists to tell the user their
        # action is still waiting on them.
        code, name = _out_lang
        from core.translate import translate
        yield f"[RETRACT_WITH]{translate(_final, code, name)}"
        yield "[DONE]"
    else:
        if not _stream_to_client:
            # Withheld above; deliver the whole translated message as one chunk. Translation
            # runs after filter_output on purpose — see core/translate.py § ORDER IS
            # LOAD-BEARING. If it fails it returns the English text, so the user still gets
            # their answer.
            code, name = _out_lang
            from core.translate import translate
            yield translate(_final, code, name)
        yield "[DONE]"

    _trace(f"[PIPELINE] synthesizer  done  ({len(visible)} chars visible)")
    _tr.finish_request_trace("" if _suppressed else _final)


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
            # `user_input` is this entry point's own argument — the message being
            # answered. The filter only acts on the Synthesizer at all, and the
            # pipeline's proactive gate is applied at its own two call sites.
            _out = filter_output(result, agent_name, user_text=user_input)
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
