"""
core/build/condense.py — range reads, reduced to evidence a judgment can sit on.

N3, second half. A Librarian that can only fetch a named key is a lookup
service. Research means range reads over 61 journal files and 44 days of
conversation, distilled.

THE DIVISION OF LABOUR, which is the whole point:

    code   fetches the range          (probe.py, with a code-written window)
    cheap  condenses it to evidence   (a small model, injected by the runner)
    Librarian works over THE EVIDENCE, never over the raw range

MAKING A RANGE READABLE IS THE JOB. LIMITING THE LIBRARIAN IS NOT (Mike,
2026-09-18). The Librarian's aim is to establish which questions have answers
and WHERE IN THE USER'S DATA those answers live, and it reads as much as it
needs to do that. So `DEFAULT_MAX_CHARS` is a default for ONE condensation
call, never a budget on a Librarian pass, and nothing downstream may turn it
into one. The cost control is the per-job tripwire in core/build/cost.py.

An earlier draft of this docstring said the point was keeping the judgment on a
small input. That framing was overruled and is recorded in
archive/plans/build_librarian_planner_parameters_2026-09-18.md, because a stale
design intent in a docstring is what a later session acts on.

THE SUMMARISER IS INJECTED, NOT IMPORTED. `condense()` takes a callable and
defaults to a deterministic extractive reduction that needs no model at all.
Three reasons, in order of weight: this module is testable without a model or a
network; a summariser failure degrades to the extractive pass rather than
failing the node; and the cheap-tier model is named in routing config, which
is where a model choice belongs — not hardcoded in a module that would then
have to be edited every time the tier moves (it moved twice in four days this
month).

The runner (phase 4) injects the real pass once `build_librarian` exists.
"""

from __future__ import annotations

import re
from typing import Any, Callable

# A condensed block is sized so that a whole Answer Ledger's worth of evidence
# still leaves the Librarian's judgment as the dominant cost, not the reading.
DEFAULT_MAX_CHARS = 1_200
DEFAULT_MAX_ITEMS = 12

Summariser = Callable[[str, str], str]


def condense(raw: Any, question: str = "",
             summariser: Summariser | None = None,
             max_chars: int = DEFAULT_MAX_CHARS,
             max_items: int = DEFAULT_MAX_ITEMS) -> dict:
    """
    Reduce one source's raw return to an evidence block.

    Returns {text, condensed_from, method, truncated}. `condensed_from` is the
    number of records the block stands for, and it travels into the ledger row
    so a reader can tell a distillation of 61 files from a distillation of one.
    """
    items = _to_items(raw)
    total = len(items)
    if total == 0:
        return {"text": "", "condensed_from": 0, "method": "empty",
                "truncated": False}

    if summariser is not None:
        joined = _join(items, max_chars * 8)
        try:
            text = str(summariser(joined, question) or "").strip()
            if text:
                return {"text": text[:max_chars], "condensed_from": total,
                        "method": "model", "truncated": len(text) > max_chars}
        except Exception:
            # Degrade to the extractive pass. A condenser failure must not fail
            # the node — the evidence gets cruder, not absent.
            pass

    return _extractive(items, question, total, max_chars, max_items)


def _extractive(items: list[str], question: str, total: int,
                max_chars: int, max_items: int) -> dict:
    """
    No model. Rank by overlap with the question's terms, keep the best few,
    and say plainly how many records were dropped.

    Crude on purpose: its job is to be a floor that always works, not to
    compete with the model pass.
    """
    terms = _terms(question)
    if terms:
        ranked = sorted(
            items, key=lambda item: -len(terms & _terms(item)))
    else:
        ranked = items[-max_items:][::-1]   # newest first when nothing to rank on

    kept = [item for item in ranked[:max_items] if item.strip()]
    text = _join(kept, max_chars)
    return {
        "text": text,
        "condensed_from": total,
        "method": "extractive",
        "truncated": total > len(kept) or len(_join(kept, 10 ** 9)) > max_chars,
    }


def _to_items(raw: Any) -> list[str]:
    """Flatten a tool return into comparable units. One unit is one record."""
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        return [_stringify(item) for item in raw if _stringify(item).strip()]
    if isinstance(raw, dict):
        return [f"{k}: {_stringify(v)}" for k, v in raw.items()
                if _stringify(v).strip()]
    text = str(raw).strip()
    if not text:
        return []
    # Blank-line-separated blocks where they exist, otherwise lines. Journal
    # and log returns use blank lines between entries; list returns do not.
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    if len(blocks) > 1:
        return blocks
    return [line.strip() for line in text.splitlines() if line.strip()]


def _stringify(value: Any) -> str:
    if isinstance(value, dict):
        return " · ".join(f"{k}={v}" for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return " · ".join(str(v) for v in value)
    return str(value if value is not None else "")


def _join(items: list[str], max_chars: int) -> str:
    out: list[str] = []
    used = 0
    for item in items:
        if used + len(item) > max_chars:
            break
        out.append(item)
        used += len(item) + 1
    return "\n".join(out)


_WORD_RE = re.compile(r"[a-z0-9]{3,}")
_STOP = frozenset("""
the and for what where when how does did are was with this that from into
you your his her their been have has had not but can could should would
""".split())


def _terms(text: str) -> frozenset[str]:
    return frozenset(
        w for w in _WORD_RE.findall(str(text or "").lower()) if w not in _STOP
    )


def condense_evidence(records: list[dict], question: str = "",
                      summariser: Summariser | None = None) -> list[dict]:
    """
    Condense a probe's raw payloads in place, for the records that carry one.

    probe.probe() does not retain the raw return — it counts and discards, so a
    probe sweep costs no memory. The condenser is called with the raw payload
    by whoever re-fetched it for a question that needs the content, which keeps
    "how many rows are there" and "what do they say" as two separately priced
    questions.
    """
    out: list[dict] = []
    for record in records:
        raw = record.get("raw")
        if raw is None:
            out.append(record)
            continue
        block = condense(raw, question, summariser)
        trimmed = {k: v for k, v in record.items() if k != "raw"}
        out.append({**trimmed,
                    "condensed": block["text"],
                    "condensed_from": block["condensed_from"],
                    "condense_method": block["method"]})
    return out
