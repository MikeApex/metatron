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
import os
import re

from tools.intake import Envelope

logger = logging.getLogger(__name__)

# Kept in lockstep with config/templates/intake.yaml and the agent file. A category
# the model invents is not a category.
VALID_CATEGORIES = frozenset({
    "action_required", "correspondence", "booking_confirmation", "bill_statement",
    "invitation", "announcement", "promotion", "notification", "unclear",
})

# The second axis, added 2026-09-03 (Mike's ruling: a triplet {domain, category,
# importance} of independently-expandable axes). config/templates/intake.yaml has
# claimed since 2026-08-19 that disposition and domain are independent, but the code
# derived domain from the category one-to-one — so `action_required` always meant
# logistics, a bill needing payment could not reach finance, and work correspondence
# could not reach work_vocation. Found by labelling the real corpus, three times in
# one sitting.
#
# THE ENUM IS BOUNDED BY WHO CAN READ THE QUEUE, NOT BY WHO EXISTS. A domain here
# whose agent lacks `read_intake_queue` is a queue nobody drains — messages filed
# correctly and never seen, which is worse than misfiling them somewhere read. Every
# name below is grant-checked in both routing files; adding one means granting the
# tool in the same commit (.claude/rules/agent-files.md § a named tool is a
# specification).
#
# `null` is legal and means "record only, queue nothing" — the row in records.jsonl
# is the whole outcome.
VALID_DOMAINS = frozenset({
    "logistics", "finance", "relationships", "recreation", "work_vocation",
})

_JSON_RE = re.compile(r"\{.*?\}", re.DOTALL)

# Sentinel: the model expressed no domain opinion, so the category default stands.
# Distinct from `None`, which is the model saying "queue this nowhere". A plain None
# for both would silently turn every unanswered domain into a dropped queue entry.
_UNRESOLVED = object()


def _confidence_threshold(persona: str | None = None) -> float:
    """`extractor.confidence_threshold` from the persona's intake.yaml. 0 = off."""
    try:
        from tools.intake import load_config
        return float((load_config(persona).get("extractor") or {})
                     .get("confidence_threshold", 0) or 0)
    except Exception:
        return 0.0


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
    """The model's answer, or the unclear floor. Never raises.

    The three axes fail independently, and deliberately so: a model that picks a good
    category and invents a domain should keep its category. Collapsing the whole
    result on a bad domain would turn a routing miss into a surfaced `unclear`, which
    is a worse answer than the one it already had.
    """
    fallback = {"category": "unclear", "domain": _UNRESOLVED,
                "confidence": None, "important": False}
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

    # Domain: absent means "no opinion, use the category default"; an explicit null
    # means "queue nothing" and is a real answer. The two are distinguishable here and
    # must stay so — `_UNRESOLVED` is what lets the caller tell them apart.
    domain = _UNRESOLVED
    if "domain" in data:
        raw_domain = data.get("domain")
        if raw_domain is None or str(raw_domain).strip().lower() in ("null", "none", ""):
            domain = None
        else:
            candidate = str(raw_domain).strip().lower()
            if candidate in VALID_DOMAINS:
                domain = candidate
            else:
                logger.warning(f"[intake] extractor returned unknown domain "
                               f"{candidate!r} — falling back to the category default")

    # Confidence, added 2026-09-04. The model self-reports 0.0–1.0; Python decides what
    # to do about it. THE DECISION IS IN CODE ON PURPOSE — measured 2026-09-03, this
    # stage answered `unclear` zero times in 33 real messages despite an agent file that
    # explicitly encourages it, and a second, sharper instruction pass moved it to one.
    # A behaviour obtainable only by asking nicely is not a behaviour you have; the same
    # reasoning already governs `_effective_disposition()` and `filter_output()`.
    #
    # Absent key or unparseable value means "not reported", never zero — reading a
    # missing confidence as no-confidence would demote every answer from a model that
    # simply did not supply the field.
    confidence = None
    if "confidence" in data:
        try:
            confidence = max(0.0, min(1.0, float(data.get("confidence"))))
        except (TypeError, ValueError):
            logger.warning("[intake] extractor returned unparseable confidence "
                           f"{data.get('confidence')!r}")

    return {"category": category, "domain": domain, "confidence": confidence,
            "important": bool(data.get("important", False))}


def apply_confidence_floor(result: dict, threshold: float) -> dict:
    """Demote a low-confidence answer to `unclear`, which surfaces to the user.

    `threshold <= 0` is off, and is the default — the floor stays inert until a run of
    the eval corpus has been used to pick a number. Picking one by intuition would set
    the surface/silence dial blind, and that dial is the whole product: too low and
    obligations are silenced, too high and the user's inbox is handed back to them.

    A result carrying no confidence is never demoted. `unclear` keeps its domain, so a
    demoted message still reaches the right specialist's queue.
    """
    if threshold <= 0:
        return result
    confidence = result.get("confidence")
    if confidence is None or confidence >= threshold:
        return result
    demoted = dict(result)
    demoted["category"] = "unclear"
    demoted["demoted_from"] = result.get("category")
    return demoted


def extract(env: Envelope, persona: str | None = None) -> dict:
    """Classify one message with the intake_extractor agent.

    Returns {"category": ..., "domain": ..., "important": bool}. `domain` is either a
    name from VALID_DOMAINS, `None` (queue nothing), or `_UNRESOLVED` — use
    `resolved_domain()` rather than reading it raw.

    Any failure — model error, junk output, unknown category — is `unclear`, never an
    exception: one bad message must not cost the sweep the rest of its batch.
    """
    from core.orchestrator import run_session

    # The agent file is overridable for A/B runs of the eval only (--variant). It is an
    # env var rather than an argument so the sweep's call site cannot accidentally
    # select a variant in production: nothing sets this outside tests.
    agent = os.environ.get("METATRON_INTAKE_EXTRACTOR_AGENT") or "intake_extractor"

    try:
        raw = run_session(
            agent,
            user_input=_build_input(env),
            persona=persona,
            complexity="quick",   # Flash-Lite tier — bounded, mechanical
            bare=True,            # agent file only; no personal context, by design
        )
    except Exception as exc:
        logger.warning(f"[intake] extractor call failed for {env.id}: {exc}")
        return {"category": "unclear", "domain": _UNRESOLVED,
                "confidence": None, "important": False}
    return apply_confidence_floor(_parse(raw), _confidence_threshold(persona))


def has_domain_opinion(result: dict) -> bool:
    """True when the model actually answered the domain axis."""
    return result.get("domain", _UNRESOLVED) is not _UNRESOLVED


def extract_category(env: Envelope, persona: str | None = None) -> str:
    """Category alone — the eval harness's entry point."""
    return extract(env, persona)["category"]
