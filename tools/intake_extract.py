"""
tools/intake_extract.py — the model stage of intake classification.

Everything the code stages (rules, ledger, headers) leave `unclear` lands here: one
message, one small-model call, one category from a closed enum. This module owns the
dispatch and the parse; the judgement lives in config/agents/intake_extractor.md.

THE POSTURE IS THE POINT. The extractor reads nothing but attacker-writable text, so
it runs with the smallest window this codebase can grant:

- **`bare=True`** — agent file only. No constitution, no goals, no profile, no recent
  context (core/orchestrator.py `_run_single_agent`). There is nothing personal in its
  context to exfiltrate. `research_agent` and `diarist` already run this way;
  `tone_profiler` should and does not ([DB-0819-02]).
- **`allowed_tools: []`** — zero schemas reach the provider call, and the Gemini path
  omits the `tools` param entirely when the list is empty (`_to_gemini_tools` returns
  [] and `_tools_kwarg` drops it), so the model cannot emit a structured tool call at
  all. Verified against the code 2026-08-19.
- **`complexity="quick"`** — Flash-Lite tier. Bounded, mechanical, strict-schema:
  the same shape as tone_profiler, which is the production precedent.

THE PARSE IS DEFENSIVE, AND `unclear` IS THE FLOOR. Whatever the model returns — junk,
prose, an injection payload echoed back, a category not in the enum — the result
collapses to `unclear`, which surfaces to the user. A small model forced to always
pick will pick confidently and wrongly; giving it a legal "I don't know" that routes
to a human is what makes zero false negatives on `action_required` achievable.

GATED TWICE BEFORE IT RUNS ON REAL MAIL:
1. `extractor.enabled: false` in config/templates/intake.yaml — flipped per persona.
2. The eval gate: `python3 tests/run_intake_eval.py --extractor` must show zero
   `action_required` false negatives on the hand-labelled corpus first (intake plan,
   verification § 1–3).
"""

from __future__ import annotations

import json
import logging
import re

from tools.intake import Envelope

logger = logging.getLogger(__name__)

# Kept in lockstep with config/templates/intake.yaml and the agent file. A category
# the model invents is not a category.
VALID_CATEGORIES = frozenset({
    "action_required", "correspondence", "booking_confirmation", "bill_statement",
    "invitation", "announcement", "promotion", "notification", "unclear",
})

_JSON_RE = re.compile(r"\{.*?\}", re.DOTALL)


def _build_input(env: Envelope) -> str:
    """One message, wrapped. The framing is ours; every quoted field is theirs."""
    from tools.untrusted import UNTRUSTED_CONTENT_INSTRUCTION, wrap_untrusted

    payload = json.dumps({
        "channel": env.channel,
        "from": f"{env.sender_display} <{env.sender_address}>",
        "subject": env.subject,
        "bulk_signals": {k: v for k, v in (env.signals or {}).items() if v},
        "body": env.body,
    }, indent=2, ensure_ascii=False)
    return (
        f"{UNTRUSTED_CONTENT_INSTRUCTION}\n\n"
        f"Classify this message. Return only the JSON object described in your "
        f"instructions.\n\n{wrap_untrusted(payload, source='intake message')}"
    )


def _parse(raw: str) -> dict:
    """The model's answer, or the unclear floor. Never raises."""
    fallback = {"category": "unclear", "important": False}
    if not isinstance(raw, str) or not raw.strip():
        return fallback
    match = _JSON_RE.search(raw)
    if not match:
        return fallback
    try:
        data = json.loads(match.group(0))
    except Exception:
        return fallback
    category = str(data.get("category", "")).strip().lower()
    if category not in VALID_CATEGORIES:
        logger.warning(f"[intake] extractor returned unknown category {category!r}")
        return fallback
    return {"category": category, "important": bool(data.get("important", False))}


def extract(env: Envelope, persona: str | None = None) -> dict:
    """Classify one message with the intake_extractor agent.

    Returns {"category": ..., "important": bool}. Any failure — model error, junk
    output, unknown category — is `unclear`, never an exception: one bad message must
    not cost the sweep the rest of its batch.
    """
    from core.orchestrator import run_session

    try:
        raw = run_session(
            "intake_extractor",
            user_input=_build_input(env),
            persona=persona,
            complexity="quick",   # Flash-Lite tier — bounded, mechanical
            bare=True,            # agent file only; no personal context, by design
        )
    except Exception as exc:
        logger.warning(f"[intake] extractor call failed for {env.id}: {exc}")
        return {"category": "unclear", "important": False}
    return _parse(raw)


def extract_category(env: Envelope, persona: str | None = None) -> str:
    """Category alone — the eval harness's entry point."""
    return extract(env, persona)["category"]
