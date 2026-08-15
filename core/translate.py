"""
core/translate.py — render the Synthesizer's visible response in the user's language.

WHY THIS EXISTS, AND WHY IT IS NOT A TOOL: [DB-0810-15]. A persona may be written to in one
language and answered in another, independently (`input_language` / `output_language` in
`tools/profile.py`). Two designs were tried and rejected before this one:

  1. **Translation rules as prose in `config/agents/synthesizer.md`** — rejected by Mike
     2026-08-15 on cost. That file loads on every head-layer call and the Synthesizer runs on
     the most expensive model in the fleet, so it is durable token spend on a setting that
     changes approximately never.
  2. **A `translate` tool the Synthesizer calls** — rejected because a tool call is a round
     trip *through* the model: emit call, run it, feed the result back, generate again. That
     costs an extra turn on the expensive model, which is more than the thing it was meant to
     save. It is also unreliable in a way this project has already paid for: the model decides
     whether to call it, and `.claude/rules/agent-files.md` documents three specialists told to
     use `search_memory` that never held it, plus `logistics` calling `write_agent_config`
     without a grant. A language guarantee that depends on a model remembering to invoke
     something fails intermittently and silently — the user just occasionally gets English.

So translation is **post-processing in Python**, the same shape as `filter_output()`. The model
is never asked to translate and never told it might be translated.

ORDER IS LOAD-BEARING — this runs AFTER `filter_output()`, never before.
`filter_output()`'s regexes and its tier-4 verbatim-span check are English. Run them against
translated text and the confidentiality backstop goes blind — a leak that would have been
caught in English sails through in Bulgarian. The pipeline therefore does:
strip [CONTEXT] -> persist -> filter_output(English) -> translate -> deliver.

WHAT IS TRANSLATED: the visible message only (Mike, 2026-08-15). Everything internal stays
English — the [CONTEXT] block, conversation history, traces, `open_threads`, clinical flags.
That is not a simplification to revisit later, it is a correctness requirement: `open_threads`
is matched by exact text in `_merge_open_threads` and by content-word overlap in
`_user_engages_thread`, so storing a translated thread would silently break the expiry and
grace logic built on 2026-08-15. Clinical flag tokens (`MUST_SURFACE`, `CLINICAL_CONCERN`)
would likewise be corrupted by translation, and they have named hard-fail criteria.

WHY A MODEL ON THE EXISTING PATH RATHER THAN A TRANSLATION API: privacy, not quality. The
Synthesizer's response is the most personal text the system produces. `ROADMAP.md` § Section 0's
2026-08-09 clarification pre-clears **new sensitive paths of the same shape** on the ZDR Vertex
VM without a separate ruling — a model call on the path already in use is exactly that. Google
Cloud Translation is a *different product* under different terms (it does not store or train on
submissions, checked 2026-08-15) and adopting it would need its own ruling. That is a decision
worth making deliberately if cost ever justifies it, not a default. Hence `_BACKENDS`: the
choice is swappable, so it can be settled by measurement instead of guessed at now.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Kept deliberately terse. This prompt is sent on every translated turn, so it is the one place
# in this module where tokens actually recur — the long reasoning lives in the docstring above,
# which costs nothing at runtime.
_SYSTEM_PROMPT = (
    "You are a translation engine. Translate the user's message into {language}. "
    "Preserve tone, register and meaning exactly — this is a personal assistant speaking to "
    "the person it works for, so keep warmth warm and brevity brief. "
    "Keep proper nouns, names, addresses, times, dates and numbers unchanged. "
    "Output ONLY the translation. Do not explain, comment, apologise, or add quotation marks. "
    "If the message is already in {language}, return it unchanged."
)


def _translate_vertex(text: str, language: str) -> str:
    """
    Translate via the model provider already serving this deployment.

    Imported inside the function, not at module scope: core/orchestrator.py imports this
    module, so a top-level import back into it would be circular.
    """
    from core.orchestrator import run_session_gemini

    return run_session_gemini(
        _SYSTEM_PROMPT.format(language=language),
        text,
        [],   # no tools — a translation turn must not be able to do anything
        {},
    ).strip()


# Swap-point for the Cloud Translation API option (see module docstring). A new backend must
# take (text, language) and return the translated string, and must raise rather than return a
# partial or apologetic string on failure — `translate()` below fails open, and it can only do
# that correctly if failure is an exception rather than a plausible-looking wrong answer.
_BACKENDS = {"model": _translate_vertex}
_BACKEND = "model"


def translate(text: str, language_code: str, language_name: str) -> str:
    """
    Translate `text` into the named language. Returns `text` unchanged on any failure.

    FAILS OPEN, DELIBERATELY. A response in the wrong language is a bad experience; no response
    at all is a broken product. This is the opposite of the fail-closed rule for sensitive
    *routing* — nothing here decides where data goes, so there is no privacy consequence to
    degrading. The failure is logged at warning level so it is visible in the journal rather
    than silent.

    Args:
        text: The visible response, already through `filter_output()`.
        language_code: ISO 639-1 code from the profile, e.g. "bg".
        language_name: Display name for the prompt, e.g. "Bulgarian".

    Returns:
        The translated text, or `text` unchanged if translation was unnecessary or failed.
    """
    if not text or not text.strip():
        return text
    if not language_code:
        return text

    try:
        out = _BACKENDS[_BACKEND](text, language_name)
    except Exception as exc:
        logger.warning("[translate] failed (%s: %s) — delivering untranslated", type(exc).__name__, exc)
        return text

    # An empty or whitespace return means the backend produced nothing usable. Delivering that
    # would replace a good English answer with silence, which is strictly worse than not
    # translating — so this is treated as a failure, not as a valid translation.
    if not out or not out.strip():
        logger.warning("[translate] backend returned empty output — delivering untranslated")
        return text

    # Stripped here rather than in each backend, so a backend added later cannot forget it and
    # leak leading whitespace into a spoken response — TTS renders that as a pause.
    return out.strip()


def response_language(persona: str | None = None) -> tuple[str, str] | None:
    """
    The persona's response language as (code, display name), or None if unset.

    None means "no preference" and must stay distinguishable from an explicit preference for
    English: an unset profile leaves the pipeline untouched, so a deployment that has never
    heard of this feature behaves exactly as it did before.
    """
    import yaml as _yaml

    from core.persona import persona_config_dir
    from tools.profile import language_name as _name

    path = persona_config_dir(persona) / "profile.yaml"
    if not path.exists():
        return None
    try:
        profile = _yaml.safe_load(path.read_text()) or {}
    except Exception:
        return None

    code = (profile.get("output_language") or "").strip()
    if not code:
        return None
    return code, _name(code)
