"""
tools/baselines.py — User-defined baseline periods.

Stores named periods the user has identified as meaningful reference points:
fulfilled periods, difficult periods, transitional periods. These become
the most personally resonant baselines for pattern comparison.

Each period carries:
  - A user memory narrative (what the user says about it)
  - Date bounds (if the user can place it in time)
  - A fulfillment score (user's retrospective assessment)
  - Retrospective layers — the user's reassessment at later dates

The retrospective layer captures time dilation of memory: how a period
is understood changes over time. A period that felt great at the time
may be reassessed differently at 6 months or 1 year's distance.

Persona-scoped when AI_TEST_PERSONA is set. Sensitive-tier, local-only.
"""

import json
import os
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).parent.parent


def _baselines_path() -> Path:
    persona = os.environ.get("AI_TEST_PERSONA")
    if persona:
        return _ROOT / "data" / "personas" / persona / "baselines.json"
    return _ROOT / "data" / "baselines.json"


def _load() -> list[dict]:
    p = _baselines_path()
    if not p.exists():
        return []
    with open(p) as f:
        return json.load(f)


def _save(periods: list[dict]) -> None:
    p = _baselines_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(periods, f, indent=2)
    os.chmod(p, 0o600)


def write_baseline_period(
    name: str,
    user_memory: str,
    fulfillment_score: int = 0,
    start_date: str = "",
    end_date: str = "",
    tags: list[str] | None = None,
) -> str:
    """
    Record a named baseline period.

    Args:
        name:              Short identifier (e.g. "summer_2022_flow_state",
                           "pre_kids_creative_peak", "year_of_the_column").
        user_memory:       The user's narrative about this period — what was
                           happening, why it felt significant. Captured verbatim;
                           the user's own vocabulary has higher salience than
                           a model paraphrase.
        fulfillment_score: User's assessment 1–10 (10 = deeply fulfilled).
                           0 means not yet scored.
        start_date:        ISO date, if the period can be placed in time.
        end_date:          ISO date. Leave empty if open-ended or undated.
        tags:              Optional labels (e.g. ["fulfilled", "creative",
                           "high_output", "difficult"]).

    Returns:
        Confirmation string.
    """
    periods = _load()
    existing = {p["name"]: i for i, p in enumerate(periods)}

    today = date.today().isoformat()
    entry = {
        "name": name,
        "user_memory": user_memory,
        "fulfillment_score": fulfillment_score,
        "start_date": start_date,
        "end_date": end_date,
        "tags": tags or [],
        "retrospectives": [],
        "created": today,
        "updated": today,
    }

    if name in existing:
        entry["retrospectives"] = periods[existing[name]].get("retrospectives", [])
        entry["created"] = periods[existing[name]].get("created", today)
        periods[existing[name]] = entry
        action = "updated"
    else:
        periods.append(entry)
        action = "created"

    _save(periods)
    return f"Baseline period '{name}' {action}."


def read_baseline_periods(tag: str = "") -> list[dict]:
    """
    Return all defined baseline periods, optionally filtered by tag.

    Args:
        tag: If given, return only periods with this tag. Leave empty for all.

    Returns:
        List of baseline period dicts.
    """
    periods = _load()
    if tag:
        periods = [p for p in periods if tag in p.get("tags", [])]
    return periods


def write_retrospective(
    period_name: str,
    assessment: str,
    revised_score: int = 0,
) -> str:
    """
    Add a retrospective assessment to a baseline period.

    Called when the user revisits how they remember a past period — days,
    months, or years later. Memory of a period changes over time; capturing
    multiple retrospectives creates a time-dilation layer that the Pattern
    Miner can use to distinguish in-the-moment assessments from longer-term
    pattern understanding.

    Args:
        period_name:    Name of the baseline period to annotate.
        assessment:     The user's current view of this period, in their words.
        revised_score:  Updated fulfillment score (1–10). 0 = not revised.

    Returns:
        Confirmation string.
    """
    periods = _load()
    today = date.today().isoformat()

    for period in periods:
        if period["name"] == period_name:
            period.setdefault("retrospectives", []).append({
                "date": today,
                "assessment": assessment,
                "revised_score": revised_score,
            })
            if revised_score:
                period["fulfillment_score"] = revised_score
            period["updated"] = today
            _save(periods)
            return f"Retrospective added to '{period_name}' ({today})."

    return f"Baseline period '{period_name}' not found."


def get_baseline_context(start_date: str, end_date: str) -> list[dict]:
    """
    Return any baseline periods that overlap with a date range.

    Used by the Pattern Miner to check whether the target analysis window
    coincides with a user-defined baseline period — which would make it
    a reference point rather than something to compare against one.

    Args:
        start_date: ISO date (YYYY-MM-DD).
        end_date:   ISO date (YYYY-MM-DD).

    Returns:
        List of matching baseline period dicts (may be empty).
    """
    periods = _load()
    if not periods:
        return []

    try:
        query_start = date.fromisoformat(start_date)
        query_end = date.fromisoformat(end_date)
    except ValueError:
        return []

    matches = []
    for period in periods:
        ps = period.get("start_date")
        pe = period.get("end_date")
        if not ps:
            continue
        try:
            p_start = date.fromisoformat(ps)
            p_end = date.fromisoformat(pe) if pe else date.today()
            if p_start <= query_end and p_end >= query_start:
                matches.append(period)
        except ValueError:
            continue

    return matches


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

WRITE_BASELINE_PERIOD_SCHEMA = {
    "name": "write_baseline_period",
    "description": (
        "Record a named reference period that can serve as a baseline for pattern comparison. "
        "Use for periods the user identifies as meaningful: a time of genuine fulfillment, "
        "a difficult stretch, a creative peak, or a transitional phase. "
        "Capture the user's own words — their internal vocabulary carries more meaning "
        "than a paraphrase. The baseline interview should surface these memories."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Short slug identifier (e.g. 'summer_2022_flow_state').",
            },
            "user_memory": {
                "type": "string",
                "description": "The user's narrative about this period, in their own words.",
            },
            "fulfillment_score": {
                "type": "integer",
                "description": "User's assessment 1–10 (10 = deeply fulfilled). 0 if not scored.",
            },
            "start_date": {
                "type": "string",
                "description": "ISO date if the period can be placed in time (YYYY-MM-DD).",
            },
            "end_date": {
                "type": "string",
                "description": "ISO date. Leave empty if open-ended or the user can't place it.",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Labels e.g. ['fulfilled', 'creative', 'high_output', 'difficult'].",
            },
        },
        "required": ["name", "user_memory"],
    },
}

READ_BASELINE_PERIODS_SCHEMA = {
    "name": "read_baseline_periods",
    "description": (
        "Retrieve user-defined baseline periods. Call at the start of a pattern analysis "
        "session to understand what reference points the user has already identified. "
        "If the analysis window overlaps with a baseline period, note it — that period "
        "may be the right comparison point rather than a generic trailing window."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "tag": {
                "type": "string",
                "description": "Filter by tag (e.g. 'fulfilled'). Leave empty to return all.",
            },
        },
        "required": [],
    },
}

WRITE_RETROSPECTIVE_SCHEMA = {
    "name": "write_retrospective",
    "description": (
        "Add a retrospective assessment to a baseline period. "
        "Memory of a past period changes over time — a stretch that felt great in the moment "
        "may be understood differently at 6 months or a year's distance. "
        "Capturing multiple retrospectives at different time distances creates a time-dilation "
        "layer the Pattern Miner can use to distinguish in-the-moment from long-term assessments."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "period_name": {
                "type": "string",
                "description": "Name of the baseline period to annotate.",
            },
            "assessment": {
                "type": "string",
                "description": "The user's current view of this period, in their own words.",
            },
            "revised_score": {
                "type": "integer",
                "description": "Updated fulfillment score 1–10. 0 if unchanged.",
            },
        },
        "required": ["period_name", "assessment"],
    },
}

GET_BASELINE_CONTEXT_SCHEMA = {
    "name": "get_baseline_context",
    "description": (
        "Check whether a date range overlaps with any user-defined baseline periods. "
        "Call before running pattern analysis to see if the target window is itself "
        "a reference period — which changes how findings should be framed."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "start_date": {"type": "string", "description": "ISO date (YYYY-MM-DD)."},
            "end_date": {"type": "string", "description": "ISO date (YYYY-MM-DD)."},
        },
        "required": ["start_date", "end_date"],
    },
}
