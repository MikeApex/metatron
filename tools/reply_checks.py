"""
tools/reply_checks.py — detection-only checks over the Synthesizer's finished reply.

Stage 5 M19 (archive/plans/instructions_to_code_stage5_one_channel_plan_2026-11-23.md § 1 M19):
`check_filler(reply)` counts a reply that opens a sentence with a listed filler phrase ("Enjoy the
museum."). The rule is the Synthesizer's (config/agents/synthesizer.md); this only counts when it
slips, because a count is what can show the rule is or is not holding. Nothing here changes what
the user sees. Called beside `check_false_action_claims` on both pipeline twins.

The list is config/modules/filler_phrases.yaml, re-read when its mtime changes. A missing or
broken file means no check — logged, never raised.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_PATH = Path(__file__).resolve().parent.parent / "config" / "modules" / "filler_phrases.yaml"
_CACHE: dict = {"mtime": None, "re": None}
# A sentence start: the start of the text or a line, or after . ! ? (and any closing quote),
# allowing an opening quote, bullet or bracket before the first word.
_START = r"(?:^|(?<=[.!?])[\"'”’)]*\s+|\n)[\s\"'“‘(*•-]*"


def _pattern() -> re.Pattern | None:
    try:
        mtime = _PATH.stat().st_mtime
    except OSError:
        return None
    if _CACHE["mtime"] != mtime:
        try:
            data = yaml.safe_load(_PATH.read_text()) or {}
            starts = [str(s) for s in data.get("sentence_starts") or [] if str(s).strip()]
            _CACHE["re"] = (re.compile(_START + "(?P<p>" + "|".join(f"(?:{s})" for s in starts)
                                       + ")", re.I) if starts else None)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[reply_checks] filler list unreadable: {exc}")
            _CACHE["re"] = None
        _CACHE["mtime"] = mtime
    return _CACHE["re"]


def _sentence_at(text: str, pos: int) -> str:
    end = re.search(r"[.!?\n]", text[pos:])
    s = text[pos:pos + end.end()] if end else text[pos:]
    return re.sub(r"\s+", " ", s).strip(" \"'“”‘’*•-")[:120]


def check_filler(reply: str) -> str | None:
    """The first sentence in `reply` that opens with a listed filler phrase, or None. Writes at
    most one FILLER_PHRASE quality event for the reply. Never raises; never changes `reply`."""
    try:
        pat = _pattern()
        if pat is None or not reply:
            return None
        m = pat.search(reply)
        if not m:
            return None
        sentence = _sentence_at(reply, m.start("p"))
        try:
            from tools.logger import write_quality_event
            write_quality_event(event_type="FILLER_PHRASE", source_agent="synthesizer",
                                detail=sentence)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[reply_checks] filler event not written: {type(exc).__name__}")
        return sentence
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[reply_checks] filler check failed: {type(exc).__name__}")
        return None
