"""
tools/tfl_status.py — London public transport line status via Transport for London's
Unified API (api.tfl.gov.uk). Deliberately named for TfL specifically, not "transit" —
this only ever covers Greater London; see tools/routing.py for the provider-agnostic
route-planning tool, which currently uses TfL as its one backend but is named so a
non-London backend can be added later without an agent-facing rename.

Unauthenticated public endpoint — no API key required at this call volume, same
posture as tools/ambient.py's wttr.in weather call. Cloud-safe: a line ID
("dlr", "elizabeth", "victoria") carries no personal data.

Built for the pre-departure travel check: Logistics needs to know before the user
does whether a line they usually take is disrupted on a travel day.
"""

from __future__ import annotations

import requests

TIMEOUT_SECONDS = 8
_BASE = "https://api.tfl.gov.uk/Line"

# Canonical TfL line IDs for the names a user would actually say.
_LINE_ALIASES = {
    "dlr": "dlr",
    "elizabeth": "elizabeth",
    "elizabeth line": "elizabeth",
    "crossrail": "elizabeth",
    "overground": "london-overground",
    "london overground": "london-overground",
    "national rail": "national-rail",
}


def _canonical(line: str) -> str:
    key = line.strip().lower()
    return _LINE_ALIASES.get(key, key)


def get_tfl_status(lines: list[str]) -> dict:
    """
    Current TfL status for one or more lines — tube, DLR, Elizabeth line, Overground.

    Args:
        lines: Line names, e.g. ["dlr", "elizabeth", "victoria"]. Case-insensitive;
            common aliases like "elizabeth line" and "crossrail" are recognized.

    Returns:
        {"lines": [{"name", "status", "disrupted", "detail"}], ...} or {"error": ...}.
        `disrupted` is False for "Good Service" and True for anything else — check it
        before deciding whether to say anything to the user; a clean status on every
        requested line is not worth a message.
    """
    if not lines:
        return {"error": "No lines given."}

    ids = ",".join(_canonical(l) for l in lines if l.strip())
    if not ids:
        return {"error": "No valid line names given."}

    try:
        resp = requests.get(f"{_BASE}/{ids}/Status", timeout=TIMEOUT_SECONDS)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        return {"error": f"TfL status lookup failed: {e}"}
    except ValueError:
        return {"error": "TfL returned an unparseable response."}

    if isinstance(data, dict) and "httpStatusCode" in data:
        # TfL's own error shape, e.g. an unrecognized line id.
        return {"error": data.get("message", "TfL rejected the request — check line names.")}

    out = []
    for line in data:
        statuses = line.get("lineStatuses") or []
        worst = min(statuses, key=lambda s: s.get("statusSeverity", 10), default=None)
        desc = (worst or {}).get("statusSeverityDescription", "Unknown")
        out.append({
            "name": line.get("name", "?"),
            "status": desc,
            "disrupted": desc != "Good Service",
            "detail": (worst or {}).get("reason", ""),
        })
    return {"lines": out}


GET_TFL_STATUS_SCHEMA = {
    "name": "get_tfl_status",
    "description": (
        "Current TfL service status for one or more London lines — tube, DLR, "
        "Elizabeth line, Overground. Use ahead of a travel day to check the lines "
        "the user usually takes, before they'd have to ask. No API key needed. "
        "Only worth surfacing to the user when a line comes back disrupted — a "
        "clean 'Good Service' result on every line checked does not need a message."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "lines": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Line names, e.g. ['dlr', 'elizabeth', 'victoria'].",
            },
        },
        "required": ["lines"],
    },
}
