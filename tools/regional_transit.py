"""
tools/regional_transit.py — lookup against the shared regional-transit-tool library.

`get_travel_time` (tools/routing.py, Google Maps) is always the default router, for every
city. This module answers a narrower question: does *this specific city* also have a
dedicated status tool worth cross-checking a Maps route against, and how should it be
used? The library itself is `config/modules/regional_transit.yaml` — shared across every
persona, not user data, so a persona traveling to a listed city gets the same entry a
resident would. Resolution happens per-query, against whatever city is actually relevant
right now (a calendar event's location, "I'm in Paris next week") — never cached against
a persona's home city, which would silently break the moment they travel.

No API call, no key — this is a local file read, same cost every time regardless of how
often it's called.
"""

from __future__ import annotations

from pathlib import Path

import yaml

_LIBRARY_PATH = Path(__file__).parent.parent / "config" / "modules" / "regional_transit.yaml"


def _load_library() -> dict:
    if not _LIBRARY_PATH.exists():
        return {}
    try:
        return yaml.safe_load(_LIBRARY_PATH.read_text()) or {}
    except yaml.YAMLError:
        return {}


def get_regional_transit_info(city: str) -> dict:
    """
    Look up whether a city has a dedicated regional transit-status tool worth using
    alongside get_travel_time.

    Args:
        city: City name, e.g. "London". Matched case-insensitively against the library.

    Returns:
        {"tool": "...", "use_for": "..."} if the city has an entry, or
        {"configured": False} if it doesn't — which is the expected, common answer for
        most cities. Absence is not a gap to report to the user; it just means
        get_travel_time alone is the complete answer for that city.
    """
    if not city or not city.strip():
        return {"error": "No city given."}

    library = _load_library()
    key = city.strip().lower()
    for name, entry in library.items():
        if name.strip().lower() == key:
            return {"tool": entry.get("tool"), "use_for": (entry.get("use_for") or "").strip()}

    return {"configured": False}


GET_REGIONAL_TRANSIT_INFO_SCHEMA = {
    "name": "get_regional_transit_info",
    "description": (
        "Check whether a city has a dedicated transit-status tool worth cross-checking "
        "against a get_travel_time route — for disruption awareness or longer-range "
        "transit planning, never as a substitute for get_travel_time itself. Resolve the "
        "city from whatever's actually relevant right now (a calendar event's location, "
        "something the user said about where they are or are headed) — not from where the "
        "user normally lives, which would give the wrong answer while they're traveling. "
        "Most cities have no entry — that's the expected common case, not a gap to "
        "mention to the user; it just means the Maps route is the complete answer."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City name, e.g. 'London'."},
        },
        "required": ["city"],
    },
}
