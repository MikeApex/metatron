"""
core/persona.py — single source of truth for "which persona am I serving?"

Every persona (the real user, or any other) owns a complete universe:
    config/personas/{name}.md          identity + interaction preferences
    config/personas/{name}/            prime_directive, mission, goals, settings
    data/personas/{name}/              logs, journal, memory, traces, everything written

There is no "test persona" tier. Every session is real. Code that needs to know
who it is serving calls resolve_persona() — it never reads an environment
variable directly and never falls back to a shared global path.

Fail-closed: if no persona can be resolved, raise. A silent fallback to a shared
directory is what previously split one user's history across two trees and let
one persona's data land in another's files.

Resolution order:
    1. explicit argument
    2. thread-local (set by persona_scope)
    3. METATRON_PERSONA environment variable
    4. AI_TEST_PERSONA environment variable (deprecated; warns)
    5. fail

Transition safety — audit mode:
    METATRON_PERSONA_STRICT=0 plus METATRON_PERSONA_FALLBACK=<name> makes an
    unresolved lookup log the offending call stack to
    data/diagnostics/persona_audit.jsonl and return the fallback, instead of
    raising. This exists so the remaining un-converted code paths can be found
    from real traffic without taking the system down. Both variables are
    required together: setting STRICT=0 without a fallback still raises, so a
    half-configured deployment cannot silently write to the wrong persona.

    Strict is the default. Deployments opt out explicitly, never implicitly.

Sensitive-tier: persona names appear in file paths, never in cloud payloads.
"""

from __future__ import annotations

import json
import os
import re
import threading
import traceback
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

_ROOT = Path(__file__).parent.parent

ENV_PRIMARY = "METATRON_PERSONA"
ENV_LEGACY = "AI_TEST_PERSONA"          # deprecated; still read during transition
ENV_STRICT = "METATRON_PERSONA_STRICT"
ENV_FALLBACK = "METATRON_PERSONA_FALLBACK"

_AUDIT_LOG = _ROOT / "data" / "diagnostics" / "persona_audit.jsonl"

# Persona names become path components. Anything outside this alphabet is
# rejected rather than sanitised — a name that needs cleaning is a bug upstream,
# and quietly rewriting it would mask the caller sending it.
_VALID_NAME = re.compile(r"^[a-z0-9][a-z0-9_]{0,39}$")

_state = threading.local()
_audit_lock = threading.Lock()
_legacy_warned = False


class PersonaError(RuntimeError):
    """No persona could be resolved, or the name supplied was not usable."""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_persona_name(name: str) -> str:
    """
    Return name unchanged if it is a usable persona identifier, else raise.

    Guards the path-traversal surface: persona arrives in an HTTP request body
    and is interpolated straight into filesystem paths, so "../../etc" must not
    survive this function.
    """
    if not isinstance(name, str):
        raise PersonaError(f"Persona must be a string, got {type(name).__name__}")
    cleaned = name.strip()
    if not cleaned:
        raise PersonaError("Persona name is empty")
    if not _VALID_NAME.match(cleaned):
        raise PersonaError(
            f"Invalid persona name {cleaned!r} — must match {_VALID_NAME.pattern} "
            "(lowercase letters, digits and underscores; max 40 chars)"
        )
    return cleaned


# ---------------------------------------------------------------------------
# Audit mode
# ---------------------------------------------------------------------------

def is_strict() -> bool:
    """True when an unresolved persona should raise. Default is True."""
    return os.environ.get(ENV_STRICT, "1").strip().lower() not in ("0", "false", "no")


def _audit_fallback() -> str | None:
    raw = os.environ.get(ENV_FALLBACK, "").strip()
    if not raw:
        return None
    try:
        return validate_persona_name(raw)
    except PersonaError:
        return None


def _record_audit(reason: str, fallback: str) -> None:
    """Append one line describing an unresolved lookup. Never raises."""
    try:
        frames = [
            f"{f.filename}:{f.lineno} in {f.name}"
            for f in traceback.extract_stack()[:-2][-6:]
        ]
        record = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "reason": reason,
            "fallback_used": fallback,
            "thread": threading.current_thread().name,
            "stack": frames,
        }
        with _audit_lock:
            _AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(_AUDIT_LOG, "a") as f:
                f.write(json.dumps(record) + "\n")
    except Exception:
        pass  # diagnostics must never break a session


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------

def resolve_persona(explicit: str | None = None) -> str:
    """
    Return the persona this call is serving.

    Raises PersonaError when none can be determined, unless audit mode is
    configured (see module docstring).
    """
    if explicit:
        return validate_persona_name(explicit)

    from_thread = getattr(_state, "persona", None)
    if from_thread:
        return from_thread

    from_env = os.environ.get(ENV_PRIMARY, "").strip()
    if from_env:
        return validate_persona_name(from_env)

    legacy = os.environ.get(ENV_LEGACY, "").strip()
    if legacy:
        global _legacy_warned
        if not _legacy_warned:
            _legacy_warned = True
            print(
                f"[persona] {ENV_LEGACY} is deprecated — set {ENV_PRIMARY} instead.",
                flush=True,
            )
        return validate_persona_name(legacy)

    if not is_strict():
        fallback = _audit_fallback()
        if fallback:
            _record_audit("no persona in argument, thread-local or environment", fallback)
            return fallback
        raise PersonaError(
            f"No persona resolved. {ENV_STRICT}=0 is set but {ENV_FALLBACK} is missing "
            "or invalid — audit mode requires both, so that a half-configured "
            "deployment cannot silently write to the wrong persona."
        )

    raise PersonaError(
        "No persona resolved. Every session must name the persona it serves — "
        f"pass one explicitly, wrap the call in persona_scope(), or set {ENV_PRIMARY}. "
        "Entry points supply this via --persona."
    )


@contextmanager
def persona_scope(persona: str) -> Iterator[str]:
    """
    Bind a persona for the duration of the block, on this thread.

    Thread-local rather than process-global because sessions run on a pooled
    executor thread and specialists fan out across further threads; a
    process-wide variable lets concurrent requests read each other's identity.

    The environment variables are mirrored so that any code not yet converted to
    resolve_persona() still sees the right persona. Both are restored on exit,
    including when the block raises.
    """
    validated = validate_persona_name(persona)

    prev_thread = getattr(_state, "persona", None)
    prev_primary = os.environ.get(ENV_PRIMARY)
    prev_legacy = os.environ.get(ENV_LEGACY)

    _state.persona = validated
    os.environ[ENV_PRIMARY] = validated
    os.environ[ENV_LEGACY] = validated

    try:
        yield validated
    finally:
        if prev_thread is None:
            _state.persona = None
        else:
            _state.persona = prev_thread
        _restore_env(ENV_PRIMARY, prev_primary)
        _restore_env(ENV_LEGACY, prev_legacy)


def _restore_env(key: str, previous: str | None) -> None:
    if previous is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = previous


def current_persona() -> str | None:
    """The bound persona, or None. Does not raise — for logging and diagnostics."""
    try:
        return resolve_persona()
    except PersonaError:
        return None


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def persona_config_dir(persona: str | None = None) -> Path:
    """config/personas/{persona}/ — tier 1-3 config and per-persona settings."""
    return _ROOT / "config" / "personas" / resolve_persona(persona)


def persona_data_dir(persona: str | None = None) -> Path:
    """data/personas/{persona}/ — everything the system writes for this persona."""
    return _ROOT / "data" / "personas" / resolve_persona(persona)


def persona_md(persona: str | None = None) -> Path:
    """config/personas/{persona}.md — identity and interaction preferences."""
    return _ROOT / "config" / "personas" / f"{resolve_persona(persona)}.md"


def list_personas() -> list[str]:
    """
    Persona names that have an identity file, sorted.

    Names that fail validation are skipped rather than raising — the directory
    can contain stray files, and scripts/check_personas.py is what reports them.
    """
    root = _ROOT / "config" / "personas"
    if not root.is_dir():
        return []
    found = []
    for path in root.glob("*.md"):
        try:
            found.append(validate_persona_name(path.stem))
        except PersonaError:
            continue
    return sorted(found)
