"""
tools/places.py — generic venue discovery: find places of a given kind near a named address.

Deliberately not `tools/google_places.py`. The interface (query, near, max_results) and
the output shape are provider-agnostic on purpose — same reasoning as `tools/routing.py`.
A persona anywhere in the world should be able to call `find_places` without the name or
the schema betraying which backend answered it, and the backend should be swappable
without touching the agent files that grant the tool.

**No personal context leaves the machine.** This is decontextualized cloud work in the
sense of `CLAUDE.md` § Data Privacy Tiers: the request carries a kind of venue ("café")
and a public address or landmark, and nothing about who is asking or why. Same framing as
`tools/regional_transit.py` — the question "what is near this street" has the same answer
for every persona, so it is not sensitive-tier data and a cloud API is permitted.

**Needs its own key: `GOOGLE_PLACES_API_KEY` in `.env`, NOT `GOOGLE_MAPS_API_KEY`.**
That is deliberate, not an oversight. The routing key is restricted to
`routes.googleapis.com` at creation so a leak can't be spent on other Maps Platform SKUs;
a Places call on it fails. The second key is restricted the same way to the Places API
only, which keeps the leak-containment property intact for both — one key, one SKU.

**Cost control lives in the FieldMask.** The Places API (New) bills by which fields you
ask for (Essentials / Pro / Enterprise tiers), not by the call alone. `_FIELD_MASK` below
is pinned to basic and Pro fields; adding an Enterprise field (reviews, editorial summary,
opening-hours detail beyond `openNow`) raises the per-call price silently. Change it only
with the new SKU tier named.

Text Search is used rather than Nearby Search plus a geocoding call: "café near {address}"
resolves the address inside the one request, which is both cheaper and the honest fit for
"near a named address" when there is no GPS fix to work from.
"""

from __future__ import annotations

import os

import requests

TIMEOUT_SECONDS = 10
_PLACES_BASE = "https://places.googleapis.com/v1/places:searchText"

# Basic + Pro fields only — this header is what selects the billing SKU. See module
# docstring: anything beyond this list moves the call to a more expensive tier.
_FIELD_MASK = (
    "places.displayName,places.formattedAddress,places.rating,"
    "places.userRatingCount,places.priceLevel,"
    "places.currentOpeningHours.openNow,places.location"
)

_MAX_RESULTS_CAP = 10

# The API returns an enum; the model prompt wants something readable and short.
_PRICE_LEVEL = {
    "PRICE_LEVEL_FREE": "free",
    "PRICE_LEVEL_INEXPENSIVE": "inexpensive",
    "PRICE_LEVEL_MODERATE": "moderate",
    "PRICE_LEVEL_EXPENSIVE": "expensive",
    "PRICE_LEVEL_VERY_EXPENSIVE": "very expensive",
}


def _places_key() -> str | None:
    return os.environ.get("GOOGLE_PLACES_API_KEY")


def _summarize(place: dict) -> dict:
    """One API place record reduced to the compact shape that feeds a model prompt."""
    summary: dict = {
        "name": (place.get("displayName") or {}).get("text") or "Unnamed place",
        "address": place.get("formattedAddress"),
    }
    rating = place.get("rating")
    if rating is not None:
        summary["rating"] = rating
        summary["rating_count"] = place.get("userRatingCount")
    open_now = (place.get("currentOpeningHours") or {}).get("openNow")
    if open_now is not None:
        summary["open_now"] = open_now
    price = place.get("priceLevel")
    if price:
        summary["price_level"] = _PRICE_LEVEL.get(price, price)
    loc = place.get("location") or {}
    if loc.get("latitude") is not None and loc.get("longitude") is not None:
        # Carried so a result can be handed straight to get_travel_time as "lat,lon".
        summary["location"] = f"{loc['latitude']},{loc['longitude']}"
    return summary


def find_places(query: str, near: str, max_results: int = 5) -> dict:
    """
    Find real venues of a given kind near a named address or landmark.

    Args:
        query: The kind of place wanted — "café", "pharmacy", "quiet pub", "hardware shop".
        near: A named address, postcode, or landmark to search around. No GPS needed.
        max_results: How many venues to return, 1–10 (default 5, capped at 10).

    Returns:
        {"places": [{"name", "address", "rating", "rating_count", "open_now",
        "price_level", "location"}, ...]} — fields other than name and address appear
        only when the source has them. On failure returns {"error": ...}, including an
        honest error when `GOOGLE_PLACES_API_KEY` isn't configured and when the search
        genuinely found nothing. Never returns an empty list, because an empty structure
        reads as "the tool worked" and invites the model to fill the gap itself.
    """
    query = (query or "").strip()
    near = (near or "").strip()
    if not query:
        return {"error": "A kind of place to look for is required."}
    if not near:
        return {"error": "An address or landmark to search near is required."}

    try:
        max_results = int(max_results)
    except (TypeError, ValueError):
        max_results = 5
    max_results = max(1, min(max_results, _MAX_RESULTS_CAP))

    key = _places_key()
    if not key:
        return {"error": "Venue search requires GOOGLE_PLACES_API_KEY, which is not configured."}

    body = {"textQuery": f"{query} near {near}", "maxResultCount": max_results}

    try:
        resp = requests.post(
            _PLACES_BASE,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": key,
                "X-Goog-FieldMask": _FIELD_MASK,
            },
            json=body,
            timeout=TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        return {"error": f"Venue search failed: {e}"}
    except ValueError:
        return {"error": "Venue search returned an unparseable response."}

    places = data.get("places") or []
    if not places:
        return {"error": f"No {query} found near {near}."}

    return {"places": [_summarize(p) for p in places[:max_results]]}


FIND_PLACES_SCHEMA = {
    "name": "find_places",
    "description": (
        "Find real venues — cafés, restaurants, shops, pharmacies, pubs, gyms — near a "
        "named address, postcode, or landmark. Returns actual named places with their "
        "addresses, ratings and whether they are open now; it does not need the user's "
        "live location, just somewhere to search around (a home or work address, a "
        "station, a calendar event's location). Use it whenever the answer would be a "
        "suggestion of somewhere to go. Never invent a venue name or guess whether "
        "somewhere exists when this tool is available; call it. Pair it with "
        "get_travel_time to check how long it takes to reach one of the results."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The kind of place wanted, e.g. 'café', 'pharmacy', 'quiet pub'.",
            },
            "near": {
                "type": "string",
                "description": "Address, postcode, or landmark to search around.",
            },
            "max_results": {
                "type": "integer",
                "description": "How many venues to return, 1-10. Default 5.",
            },
        },
        "required": ["query", "near"],
    },
}
