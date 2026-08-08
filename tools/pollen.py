"""
tools/pollen.py — 1–5 day pollen forecast (Google Pollen API).

Distinct from the air-quality call in `tools/ambient.py`, and the distinction is not
cosmetic. `get_environmental_snapshot` returns *current* particulate air quality
(PM2.5/PM10, European AQI) from Open-Meteo — a general "is the air bad today" signal.
Pollen is a different exposure with a different time shape: it is allergenic rather than
particulate, it is species-specific (grass vs. tree vs. weed matter separately to a
sufferer), and it is **forecast** rather than instantaneous — the useful question is
"what are the next few days going to be like", which air quality here does not answer.
Neither tool substitutes for the other; an agent reasoning about a sore throat or
seasonal symptoms wants this one.

Routing was already in place before the data source existed:
`config/agents/coordinator.md` carries "I have a sore throat" → Physical Health; then
Synthesizer may chain to Research (pollen?) → Logistics (medicine). This file supplies
the missing leg. The tool is granted to `research_agent`, which is the decontextualized
hop in that chain.

**Location comes from a city name, not GPS.** `[DB-0808-04]` (real-time GPS + proactive
area-scanning) is unblocked-by-design here: this reuses the wttr.in geocode already used
by `get_environmental_snapshot` for air quality, so a named city is enough and no
continuous location signal is required. The GPS item remains blocked on its own terms.

**API key.** Requires `GOOGLE_POLLEN_API_KEY` in `.env`. It is deliberately *not* the same
key as `GOOGLE_MAPS_API_KEY`: that key was restricted to `routes.googleapis.com` only at
creation so a leak can't be spent on other Maps Platform SKUs (see `tools/routing.py`), and
it will return 403 here. Either mint a second key restricted to `pollen.googleapis.com`, or
widen the existing one — the error path below says so rather than failing opaquely. Pollen
enables on the same `metatron-ai-499810` GCP project already running Vertex AI, so no new
vendor account is involved.

Cloud-safe: only a city name and the coordinates derived from it leave the machine.
"""

from __future__ import annotations

import os

import requests

TIMEOUT_SECONDS = 15
_POLLEN_BASE = "https://pollen.googleapis.com/v1/forecast:lookup"

# Google's Universal Pollen Index is 0–5. The API returns its own category strings, but
# it omits the block entirely when a pollen type is out of season — so a local table is
# needed to say "None" rather than leaving a gap the model fills with a guess.
_UPI_CATEGORY = {
    0: "None",
    1: "Very Low",
    2: "Low",
    3: "Moderate",
    4: "High",
    5: "Very High",
}

# Ordered worst-first so a caller can rank without knowing the scale.
_TYPE_ORDER = ["GRASS", "TREE", "WEED"]


def _api_key() -> str | None:
    return os.environ.get("GOOGLE_POLLEN_API_KEY")


def _resolve_coords(location: str) -> tuple[float, float, str] | dict:
    """
    Turn a city name into (lat, lon, resolved_city).

    Reuses ambient.py's wttr.in geocode rather than adding a second geocoding
    dependency — and, more importantly, so pollen and air quality are talking about
    the same point on the map for the same city string.

    Returns a dict with "error" on failure, so the caller can pass it straight back.
    """
    from tools.ambient import _wttr, _coords, _get_home_city

    city = (location or "").strip() or _get_home_city()
    if not city:
        return {"error": "No location given and no home city set in profile.yaml."}

    try:
        payload = _wttr(city)
    except Exception as e:
        return {"error": f"Could not resolve location '{city}': {e}"}

    coords = _coords(payload)
    if not coords:
        return {"error": f"Could not determine coordinates for '{city}'."}
    return coords[0], coords[1], city


def _index_block(type_info: dict) -> dict:
    """
    Flatten one pollenTypeInfo entry.

    `indexInfo` is absent when the type is out of season, which is meaningful data
    rather than missing data — it becomes an explicit 0/None instead of a null.
    """
    index_info = type_info.get("indexInfo") or {}
    value = index_info.get("value")
    in_season = bool(type_info.get("inSeason", False))

    if value is None:
        value = 0
        category = "None" if not in_season else "Unknown"
    else:
        category = index_info.get("category") or _UPI_CATEGORY.get(value, "Unknown")

    return {
        "type": type_info.get("code", "UNKNOWN"),
        "display_name": type_info.get("displayName", type_info.get("code", "Unknown")),
        "index": value,
        "category": category,
        "in_season": in_season,
    }


def get_pollen_forecast(location: str = "", days: int = 3) -> dict:
    """
    Pollen forecast for a location — grass, tree and weed, 1 to 5 days ahead.

    Use when symptoms or an outdoor plan might turn on pollen: seasonal allergy
    questions, a sore throat or congestion with no obvious cause, whether to
    exercise outdoors, or whether the next few days are getting better or worse.
    Air quality (`get_environmental_snapshot`) answers a different question and is
    not a substitute.

    Args:
        location: City name. Defaults to the persona's home city.
        days:     Forecast days, 1-5. Defaults to 3. Google caps this at 5.

    Returns:
        Dict with location, daily_forecast (per-day per-type index and category),
        peak, and health_recommendations — or {"error": ...}. Never fabricates an
        index for a lookup that failed.
    """
    key = _api_key()
    if not key:
        return {
            "error": (
                "Pollen forecast requires GOOGLE_POLLEN_API_KEY, which is not configured. "
                "Note that GOOGLE_MAPS_API_KEY will not work: it is restricted to "
                "routes.googleapis.com and returns 403 for pollen.googleapis.com."
            )
        }

    resolved = _resolve_coords(location)
    if isinstance(resolved, dict):
        return resolved
    lat, lon, city = resolved

    try:
        days = max(1, min(int(days), 5))
    except (TypeError, ValueError):
        days = 3

    try:
        resp = requests.get(
            _POLLEN_BASE,
            params={
                "key": key,
                "location.latitude": lat,
                "location.longitude": lon,
                "days": days,
                "plantsDescription": False,
            },
            timeout=TIMEOUT_SECONDS,
        )
        if resp.status_code == 403:
            return {
                "error": (
                    f"Pollen API returned 403 for '{city}'. The API key is likely restricted "
                    "to other Google APIs — it needs pollen.googleapis.com enabled and allowed."
                )
            }
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        return {"error": f"Pollen lookup failed for '{city}': {e}"}

    daily_forecast = []
    recommendations: list[str] = []
    peak = {"index": -1, "type": None, "category": "None", "date": None}

    for day in payload.get("dailyInfo", []) or []:
        date = day.get("date") or {}
        try:
            date_str = f"{date['year']:04d}-{date['month']:02d}-{date['day']:02d}"
        except (KeyError, TypeError, ValueError):
            date_str = None

        types = [_index_block(t) for t in (day.get("pollenTypeInfo") or [])]
        types.sort(key=lambda t: _TYPE_ORDER.index(t["type"]) if t["type"] in _TYPE_ORDER else 99)

        for t in types:
            if t["index"] > peak["index"]:
                peak = {
                    "index": t["index"],
                    "type": t["display_name"],
                    "category": t["category"],
                    "date": date_str,
                }

        # Google attaches recommendations per type per day; the same advice repeats
        # across types and days, so collect unique lines rather than a wall of duplicates.
        for type_info in (day.get("pollenTypeInfo") or []):
            for line in (type_info.get("healthRecommendations") or []):
                if line not in recommendations:
                    recommendations.append(line)

        daily_forecast.append({
            "date": date_str,
            "types": [
                {k: t[k] for k in ("type", "display_name", "index", "category", "in_season")}
                for t in types
            ],
        })

    if not daily_forecast:
        return {
            "error": (
                f"Pollen API returned no forecast for '{city}'. Coverage is not global — "
                "the location may be outside the supported region."
            )
        }

    if peak["index"] < 0:
        peak = {"index": 0, "type": None, "category": "None", "date": None}

    return {
        "location": city,
        "days": len(daily_forecast),
        "daily_forecast": daily_forecast,
        "peak": peak,
        "health_recommendations": recommendations[:5],
        "scale_note": "Universal Pollen Index 0-5: 0 None, 1 Very Low, 2 Low, 3 Moderate, 4 High, 5 Very High.",
    }


GET_POLLEN_FORECAST_SCHEMA = {
    "name": "get_pollen_forecast",
    "description": (
        "Pollen forecast for a location — grass, tree and weed levels, 1 to 5 days ahead, "
        "on the Universal Pollen Index (0-5). Use when symptoms or an outdoor plan might "
        "turn on pollen: seasonal allergy questions, a sore throat or congestion with no "
        "obvious cause, whether to exercise outdoors, or whether the next few days are "
        "improving or worsening. This is a forecast of allergenic pollen and is NOT the "
        "same as air quality — 'get_environmental_snapshot' returns current particulate "
        "air quality (PM2.5/PM10) and does not answer pollen questions. Coverage is not "
        "global; returns an explicit error rather than a guess where unsupported. "
        "Defaults to the user's home city if no location is given."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "City name (e.g. 'London'). Omit for the user's home city.",
            },
            "days": {
                "type": "integer",
                "description": "Forecast days to include, 1-5. Defaults to 3.",
            },
        },
        "required": [],
    },
}
