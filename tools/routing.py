"""
tools/routing.py — generic route planning: real travel time between two places.

Deliberately not `tools/google_routing.py` or similar. The interface (origin,
destination, mode, arrive_by) and the output shape are provider-agnostic on purpose —
Metatron is not a single-city tool, and a persona anywhere in the world should be able to
call `get_travel_time` without the name or schema betraying which backend answered it.

**Google Maps Routes API is the sole backend, and the default for all routing,
everywhere — including inside London.** This is a deliberate correction: an earlier
version of this file tried TfL's Journey Planner first for London transit/walking. That
was the wrong split. TfL's actual job is narrower and lives elsewhere:
`tools/tfl_status.py` (`get_tfl_status`) for live London line/route disruption checks, and
`tools/regional_transit.py` (`get_regional_transit_info`) for telling an agent *when* a
regional status tool like that is worth cross-checking against a Maps route — never as
this function's default router. See `archive/PROJECT_LOG.md` 2026-08-07 for the reasoning.

Chosen over Citymapper (developer API fully discontinued 2023) and picked specifically
because it enables on the `metatron-ai-499810` GCP project already running Vertex AI — no
new vendor account. Key restricted to `routes.googleapis.com` only at creation, so a leak
can't be spent on other Maps Platform SKUs. Requires `GOOGLE_MAPS_API_KEY` in `.env`.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

import requests

TIMEOUT_SECONDS = 10
_GOOGLE_BASE = "https://routes.googleapis.com/directions/v2:computeRoutes"

_GOOGLE_MODE = {"driving": "DRIVE", "walking": "WALK", "cycling": "BICYCLE", "transit": "TRANSIT"}


def _google_key() -> str | None:
    return os.environ.get("GOOGLE_MAPS_API_KEY")


def _google_endpoint(place: str) -> dict:
    """lat,lon parses as coordinates; anything else is passed through as a free-text address."""
    parts = place.split(",")
    if len(parts) == 2:
        try:
            lat, lon = float(parts[0]), float(parts[1])
            return {"location": {"latLng": {"latitude": lat, "longitude": lon}}}
        except ValueError:
            pass
    return {"address": place}


def get_travel_time(origin: str, destination: str, mode: str = "transit", arrive_by: str = "") -> dict:
    """
    Real travel time and route between two places — not a stub, an actual computed route.

    Args:
        origin: Address or "lat,lon" for the starting point.
        destination: Address or "lat,lon" for the destination.
        mode: "transit" (default), "walking", "driving", or "cycling".
        arrive_by: Optional "YYYY-MM-DDTHH:MM" — plan to arrive by this time rather than
            leave now. Honored exactly for transit; driving/walking/cycling durations
            don't depend on time of day the way transit schedules do, so arrive_by is
            applied as a simple subtraction from the computed duration for those modes.

    Returns:
        {"journeys": [{"duration_minutes", "distance_meters", "depart_at", "arrive_at",
        "legs": [...]}]} (up to 3 options, best first), or {"error": ...} — including an
        honest error when `GOOGLE_MAPS_API_KEY` isn't configured or no route exists.
        Never fabricates a duration for a route it can't actually plan. For a city with a
        dedicated regional status tool (e.g. London), check `get_regional_transit_info`
        to see whether the route this returns is worth cross-checking against it.
    """
    origin = (origin or "").strip()
    destination = (destination or "").strip()
    if not origin or not destination:
        return {"error": "Both an origin and a destination are required."}

    google_mode = _GOOGLE_MODE.get(mode)
    if google_mode is None:
        return {"error": f"'{mode}' is not a recognized mode. Use transit, walking, driving, or cycling."}

    key = _google_key()
    if not key:
        return {"error": "Routing requires GOOGLE_MAPS_API_KEY, which is not configured."}

    body = {
        "origin": _google_endpoint(origin),
        "destination": _google_endpoint(destination),
        "travelMode": google_mode,
    }
    if google_mode == "DRIVE":
        body["routingPreference"] = "TRAFFIC_AWARE"
    if arrive_by:
        # Routes API takes an absolute RFC3339 timestamp, and only honors it for TRANSIT
        # (arriveTime) — DRIVE/WALK/BICYCLE durations are always "if you left now" or
        # "if you left at departureTime", so an arrive_by request in those modes is
        # answered with a plain duration and the caller does its own subtraction.
        try:
            dt = datetime.fromisoformat(arrive_by)
            if google_mode == "TRANSIT":
                body["arrivalTime"] = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            pass

    field_mask = "routes.duration,routes.distanceMeters,routes.legs.steps.travelMode"
    try:
        resp = requests.post(
            _GOOGLE_BASE,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": key,
                "X-Goog-FieldMask": field_mask,
            },
            json=body,
            timeout=TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        return {"error": f"Route lookup failed: {e}"}
    except ValueError:
        return {"error": "Route lookup returned an unparseable response."}

    routes = data.get("routes") or []
    if not routes:
        return {"error": "No route found between those two places."}

    now = datetime.now()
    journeys = []
    for r in routes[:3]:
        duration_s = int(str(r.get("duration", "0s")).rstrip("s") or 0)
        duration_min = round(duration_s / 60)
        if arrive_by:
            try:
                arrive_dt = datetime.fromisoformat(arrive_by)
                depart_dt = arrive_dt - timedelta(seconds=duration_s)
            except ValueError:
                depart_dt, arrive_dt = now, now + timedelta(seconds=duration_s)
        else:
            depart_dt, arrive_dt = now, now + timedelta(seconds=duration_s)

        journeys.append({
            "duration_minutes": duration_min,
            "distance_meters": r.get("distanceMeters"),
            "depart_at": depart_dt.strftime("%Y-%m-%dT%H:%M"),
            "arrive_at": arrive_dt.strftime("%Y-%m-%dT%H:%M"),
            "legs": [{"mode": mode, "from": origin, "to": destination, "duration_minutes": duration_min}],
        })

    return {"journeys": journeys}


GET_TRAVEL_TIME_SCHEMA = {
    "name": "get_travel_time",
    "description": (
        "Compute a real route and travel time between two places via Google Maps — not "
        "an estimate, an actual planned journey with minute-level durations, traffic-aware "
        "for driving. Use this to check whether the gap between two calendar events is "
        "actually enough time, or to answer 'how long will it take to get there'. This is "
        "the default router everywhere, for every mode. Some cities also have a dedicated "
        "status tool worth cross-checking a route against (see get_regional_transit_info) "
        "— but this is always the first call for 'how do I get there' or 'how long'. "
        "Never estimate a travel time yourself when this tool is available; call it."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "origin": {"type": "string", "description": "Starting address, place name, or 'lat,lon'."},
            "destination": {"type": "string", "description": "Destination address, place name, or 'lat,lon'."},
            "mode": {
                "type": "string",
                "description": "'transit' (default), 'walking', 'driving', or 'cycling'.",
                "enum": ["transit", "walking", "driving", "cycling"],
            },
            "arrive_by": {
                "type": "string",
                "description": "Optional 'YYYY-MM-DDTHH:MM' — plan to arrive by this time. Omit to plan from now.",
            },
        },
        "required": ["origin", "destination"],
    },
}
