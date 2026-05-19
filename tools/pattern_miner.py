"""
tools/pattern_miner.py — Pattern Miner tools.

Provides bulk log retrieval, insight report read/write, and
the get_log_window helper for time-windowed analysis.

Persona-scoped when AI_TEST_PERSONA is set.
All paths are local-only, sensitive-tier.
"""

import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path

_ROOT = Path(__file__).parent.parent


def _persona_dir(persona: str | None = None) -> Path:
    p = persona or os.environ.get("AI_TEST_PERSONA")
    if p:
        return _ROOT / "data" / "personas" / p
    return _ROOT / "data"


# ---------------------------------------------------------------------------
# Log window retrieval
# ---------------------------------------------------------------------------

def get_log_window(
    start_date: str,
    end_date: str,
    persona: str = "",
    max_entries: int = 0,
) -> list[dict]:
    """
    Return daily log entries between start_date and end_date inclusive.

    Args:
        start_date:  ISO date string (YYYY-MM-DD), start of window.
        end_date:    ISO date string (YYYY-MM-DD), end of window.
        persona:     Persona name for scoped testing. Defaults to env var.
        max_entries: Cap on entries returned (0 = no limit). When the window
                     exceeds the cap, the most recent entries are returned so
                     the Pattern Miner always has the freshest data. Use
                     multiple calls with different windows to cover the full
                     range without hitting token limits.

    Returns:
        List of dicts, each with a 'date' key and the log fields.
        Empty list if no logs exist in the window.
    """
    logs_dir = _persona_dir(persona or None) / "logs"
    if not logs_dir.exists():
        return []

    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError:
        return []

    results = []
    current = start
    while current <= end:
        log_path = logs_dir / f"{current.isoformat()}.json"
        if log_path.exists():
            try:
                entry = json.loads(log_path.read_text())
                entry.setdefault("date", current.isoformat())
                results.append(entry)
            except Exception:
                pass
        current += timedelta(days=1)

    if max_entries and len(results) > max_entries:
        results = results[-max_entries:]

    return results


# ---------------------------------------------------------------------------
# Insight reports
# ---------------------------------------------------------------------------

def write_insight_report(date_str: str, content: dict, persona: str = "") -> str:
    """
    Write a Pattern Miner analysis report.

    Args:
        date_str: ISO date string for this report (YYYY-MM-DD).
        content:  Dict containing the structured report. Recommended keys:
                  scale, observations (list), duplicates_flagged, baseline_used.
        persona:  Persona name for scoped testing.

    Returns:
        Confirmation string with file path.
    """
    if not date_str:
        date_str = date.today().isoformat()

    insights_dir = _persona_dir(persona or None) / "insights"
    insights_dir.mkdir(parents=True, exist_ok=True)

    if not isinstance(content, dict):
        content = {"notes": str(content)}

    content.setdefault("generated_at", datetime.now().isoformat())
    content.setdefault("date", date_str)

    report_path = insights_dir / f"{date_str}.json"
    with open(report_path, "w") as f:
        json.dump(content, f, indent=2)

    os.chmod(report_path, 0o600)
    return f"Insight report written: {report_path}"


def read_recent_insights(n: int = 5, persona: str = "") -> list[dict]:
    """
    Return the N most recent insight reports, newest first.

    Args:
        n:       Number of reports to return (default 5).
        persona: Persona name for scoped testing.

    Returns:
        List of report dicts. Empty list if no reports exist.
    """
    insights_dir = _persona_dir(persona or None) / "insights"
    if not insights_dir.exists():
        return []

    report_files = sorted(insights_dir.glob("*.json"), reverse=True)[:n]
    results = []
    for path in report_files:
        try:
            results.append(json.loads(path.read_text()))
        except Exception:
            pass
    return results


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

GET_LOG_WINDOW_SCHEMA = {
    "name": "get_log_window",
    "description": (
        "Retrieve all daily log entries between two dates for pattern analysis. "
        "Use this to pull raw log data for a time window — the bulk of the "
        "Pattern Miner's quantitative analysis (energy, mood, sleep, tasks) "
        "comes from these structured records."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "start_date": {
                "type": "string",
                "description": "Start of the window, ISO format (YYYY-MM-DD).",
            },
            "end_date": {
                "type": "string",
                "description": "End of the window, ISO format (YYYY-MM-DD).",
            },
            "persona": {
                "type": "string",
                "description": "Persona name for dev testing. Leave empty for real user data.",
            },
            "max_entries": {
                "type": "integer",
                "description": (
                    "Cap on entries returned (0 = no limit, default). When the window "
                    "is large, set this to 30–45 to stay within token limits. Most-recent "
                    "entries are kept. Call twice with split windows to cover the full range."
                ),
            },
        },
        "required": ["start_date", "end_date"],
    },
}

WRITE_INSIGHT_REPORT_SCHEMA = {
    "name": "write_insight_report",
    "description": (
        "Write a completed Pattern Miner analysis report to disk. "
        "Call this after all FAISS queries and log-window analysis are complete "
        "and you have synthesized your findings into structured observations. "
        "Each observation must include evidence, hypothesis, confidence level, "
        "and a suggested follow-up action for the Diarist."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "date_str": {
                "type": "string",
                "description": "Report date in ISO format (YYYY-MM-DD). Defaults to today.",
            },
            "content": {
                "type": "object",
                "description": (
                    "Structured report dict. Recommended shape: "
                    "{ scale: string, observations: [{observation, evidence, "
                    "hypothesis, confidence, action}], duplicates_flagged: [], "
                    "baseline_used: string, data_window: string }"
                ),
            },
            "persona": {
                "type": "string",
                "description": "Persona name for dev testing. Leave empty for real user data.",
            },
        },
        "required": ["date_str", "content"],
    },
}

READ_RECENT_INSIGHTS_SCHEMA = {
    "name": "read_recent_insights",
    "description": (
        "Read the N most recent Pattern Miner insight reports. "
        "Call this at the start of every analysis session to avoid surfacing "
        "findings that have already been noted — or to check whether new data "
        "confirms, refines, or contradicts prior observations."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "n": {
                "type": "integer",
                "description": "Number of recent reports to return. Default 5.",
            },
            "persona": {
                "type": "string",
                "description": "Persona name for dev testing. Leave empty for real user data.",
            },
        },
        "required": [],
    },
}
